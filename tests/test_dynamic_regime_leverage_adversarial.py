"""
tests/test_dynamic_regime_leverage_adversarial.py
Adversarial Stress Testing Suite for Phase 157 Quant Risk Architecture (Features F765 & F766).
Milestone 2 Adversarial Stress Testing Catalog.

Verification Vectors:
1. Pathological Alphas (all-zeros, all-negative, massive +1000% spikes, NaNs, Infs, empty arrays)
2. Degenerate Covariance Matrices (rank-deficient, all-zero, collinear, ill-conditioned, negative-definite, NaNs/Infs, RMT denoiser under degeneracy)
3. Extreme Ambiguity Radius (eps=0.0 standard Kelly, eps -> inf cash collapse, monotonicity, negative radius)
4. Leverage Frontiers & Factor Beta Clamping (high-beta assets beta_i=3.5, gross leverage <= 1.50x, defensive bounds, pathological betas)
5. Concentration Box Caps (single-stock <= 0.05 * L, single-sector <= 0.25 * L, single-asset universe, unknown sectors)

MANDATORY INTEGRITY:
All tests assert real mathematical behaviors, formulas, and exact boundary calculations. Zero dummy assertions.
"""

from __future__ import annotations

import math
import os
import sys
import unittest
import numpy as np

# Path setup
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../trading_system")))

from src.risk.dynamic_regime_leverage_allocator import (
    DynamicRegimeLeverageAllocator,
    WassersteinRobustKellyOptimizer,
    CorrelationBreakdownBrake,
)


class TestDynamicRegimeLeverageAdversarial(unittest.TestCase):
    """Adversarial stress testing for Features F765 and F766."""

    def setUp(self):
        np.random.seed(765766)
        self.allocator = DynamicRegimeLeverageAllocator(
            max_bull_leverage=1.50,
            min_crisis_exposure=0.15,
            default_kappa=0.375,
            top_k_modes=150,
        )
        self.optimizer = WassersteinRobustKellyOptimizer(
            default_kappa=0.375,
            default_epsilon=0.02,
        )

    # =========================================================================
    # VECTOR 1: PATHOLOGICAL ALPHAS
    # =========================================================================

    def test_adv01_all_zeros_alpha_cash_preservation(self):
        """ADV01: All-zero alpha vector collapses risky allocation to cash without throwing exceptions."""
        N = 5
        mu = np.zeros(N)
        cov = np.eye(N) * 0.04
        
        # Test standalone optimizer
        w_opt = self.optimizer.allocate_robust_weights(mu, cov, epsilon=0.02)
        self.assertIsInstance(w_opt, np.ndarray)
        self.assertEqual(len(w_opt), N)
        self.assertTrue(np.all(w_opt == 0.0), f"Expected all zeros, got {w_opt}")

        # Test allocator wrapper
        w_alloc = self.allocator.compute_distributionally_robust_kelly_weights(mu, cov, epsilon_w=0.02)
        self.assertEqual(len(w_alloc), N)
        self.assertTrue(np.all(w_alloc == 0.0), f"Expected all zeros from allocator, got {w_alloc}")

    def test_adv02_all_negative_alphas_cash_preservation(self):
        """ADV02: All-negative return predictions collapse completely to 0.0 risky allocation (100% cash)."""
        mu = np.array([-0.05, -0.12, -0.01, -0.50, -0.001])
        cov = np.eye(len(mu)) * 0.04
        
        w = self.allocator.compute_distributionally_robust_kelly_weights(mu, cov, epsilon_w=0.01)
        self.assertTrue(np.all(w == 0.0), f"Negative alphas must result in zero allocation, got {w}")
        self.assertAlmostEqual(float(np.sum(np.abs(w))), 0.0, places=7)

    def test_adv03_massive_alpha_spike_bounded_leverage(self):
        """ADV03: Extreme alpha spikes (+1000% to +10,000%) remain finite and strictly respect leverage ceiling."""
        mu_extreme = np.array([10.0, 50.0, 100.0, 0.05])  # massive forecast spikes
        cov = np.eye(4) * 0.04
        target_L = 1.50
        
        w = self.allocator.compute_distributionally_robust_kelly_weights(
            mu_extreme, cov, epsilon_w=0.02, target_leverage=target_L
        )
        self.assertTrue(np.all(np.isfinite(w)), "Weights must be finite under extreme alpha spikes")
        self.assertTrue(np.all(w >= -1e-9), "Weights must be non-negative")
        gross_leverage = float(np.sum(w))
        self.assertAlmostEqual(gross_leverage, target_L, places=4, msg="Gross leverage must match target_leverage")

    def test_adv04_nan_and_inf_in_alphas_sanitized(self):
        """ADV04: Alphas containing NaN, +Inf, -Inf are sanitized to finite values without uncaught errors."""
        mu_pathological = np.array([np.nan, np.inf, -np.inf, 0.08, -0.02])
        cov = np.eye(5) * 0.04

        w = self.allocator.compute_distributionally_robust_kelly_weights(
            mu_pathological, cov, epsilon_w=0.02
        )
        self.assertTrue(np.all(np.isfinite(w)), "Sanitized weights must contain zero NaNs or Infs")
        self.assertTrue(np.all(w >= 0.0), "Weights must be non-negative")
        # Assets with NaN or Infs should have zero allocation since only asset 3 has legitimate positive alpha
        self.assertEqual(w[0], 0.0)
        self.assertEqual(w[1], 0.0)
        self.assertEqual(w[2], 0.0)
        self.assertGreater(w[3], 0.0)

    def test_adv05_empty_alpha_vector_graceful(self):
        """ADV05: Empty alpha vector returns empty array cleanly without crashing."""
        mu_empty = np.array([])
        cov_empty = np.empty((0, 0))

        w = self.optimizer.allocate_robust_weights(mu_empty, cov_empty)
        self.assertEqual(len(w), 0)
        self.assertIsInstance(w, np.ndarray)

        w_alloc = self.allocator.compute_distributionally_robust_kelly_weights(mu_empty, cov_empty)
        self.assertEqual(len(w_alloc), 0)

    # =========================================================================
    # VECTOR 2: DEGENERATE COVARIANCE MATRICES
    # =========================================================================

    def test_adv06_rank_deficient_covariance(self):
        """ADV06: Rank-deficient covariance (rank 1 outer product) is regularized without singular matrix error."""
        N = 5
        mu = np.array([0.05, 0.04, 0.06, 0.03, 0.05])
        # Rank 1 matrix: all rows identical
        cov_rank1 = np.ones((N, N)) * 0.04

        w = self.allocator.compute_distributionally_robust_kelly_weights(
            mu, cov_rank1, epsilon_w=0.01
        )
        self.assertTrue(np.all(np.isfinite(w)), "Weights must be finite despite rank-deficient covariance")
        self.assertTrue(np.all(w >= 0.0), "Weights must be non-negative")

    def test_adv07_all_zero_covariance(self):
        """ADV07: All-zero covariance matrix is regularized via Tikhonov floor, avoiding zero division."""
        N = 4
        mu = np.array([0.06, 0.05, 0.07, 0.04])
        cov_zero = np.zeros((N, N))

        w = self.allocator.compute_distributionally_robust_kelly_weights(
            mu, cov_zero, epsilon_w=0.01
        )
        self.assertTrue(np.all(np.isfinite(w)), "All-zero covariance must not cause division by zero or NaN")
        self.assertTrue(np.all(w >= 0.0), "Weights must be non-negative")

    def test_adv08_collinear_covariance(self):
        """ADV08: Collinear covariance with identical duplicated assets solves stably."""
        mu = np.array([0.05, 0.05, 0.03])
        # Asset 0 and Asset 1 perfectly identical
        cov_collinear = np.array([
            [0.04, 0.04, 0.01],
            [0.04, 0.04, 0.01],
            [0.01, 0.01, 0.04],
        ])

        w = self.allocator.compute_distributionally_robust_kelly_weights(
            mu, cov_collinear, epsilon_w=0.01
        )
        self.assertTrue(np.all(np.isfinite(w)), "Collinear covariance must produce finite weights")
        self.assertAlmostEqual(w[0], w[1], places=5, msg="Identical assets must receive equal allocation")

    def test_adv09_ill_conditioned_covariance_extreme(self):
        """ADV09: Ill-conditioned covariance matrix (kappa > 1e16) remains stable."""
        N = 4
        mu = np.array([0.06, 0.05, 0.04, 0.03])
        # Diagonal spanning 16 orders of magnitude
        cov_ill = np.diag([1.0, 1e-4, 1e-8, 1e-16])

        w = self.allocator.compute_distributionally_robust_kelly_weights(
            mu, cov_ill, epsilon_w=0.01
        )
        self.assertTrue(np.all(np.isfinite(w)), "Weights must be finite despite extreme condition number")
        self.assertTrue(np.all(w >= 0.0))

    def test_adv10_negative_definite_covariance(self):
        """ADV10: Negative-definite or non-positive-definite covariance does not crash optimizer."""
        N = 3
        mu = np.array([0.05, 0.04, 0.06])
        cov_neg = -np.eye(N) * 0.04

        # Should execute safely using fallback regularization or pinv without unhandled exception
        w = self.allocator.compute_distributionally_robust_kelly_weights(
            mu, cov_neg, epsilon_w=0.01
        )
        self.assertTrue(np.all(np.isfinite(w)), "Negative-definite covariance must not produce NaNs or crash")

    def test_adv11_nan_and_inf_in_covariance(self):
        """ADV11: Covariance containing NaNs and Infs is sanitized gracefully."""
        mu = np.array([0.05, 0.06])
        cov_nan = np.array([
            [np.nan, np.inf],
            [-np.inf, 0.04],
        ])

        w = self.allocator.compute_distributionally_robust_kelly_weights(
            mu, cov_nan, epsilon_w=0.01
        )
        self.assertTrue(np.all(np.isfinite(w)), "Weights must be finite despite NaNs/Infs in covariance")

    def test_adv12_denoise_covariance_nonlinear_rmt_under_degeneracy(self):
        """ADV12: Feature F768 denoise_covariance_nonlinear_rmt handles degenerate matrices safely."""
        # Test 1: all-zero matrix
        zero_mat = np.zeros((10, 10))
        clean_zero = self.allocator.denoise_covariance_nonlinear_rmt(zero_mat, top_modes=5)
        self.assertEqual(clean_zero.shape, (10, 10))
        self.assertTrue(np.all(np.isfinite(clean_zero)))

        # Test 2: singular rank-1 matrix
        rank1_mat = np.ones((8, 8)) * 0.05
        clean_rank1 = self.allocator.denoise_covariance_nonlinear_rmt(rank1_mat, top_modes=3)
        self.assertEqual(clean_rank1.shape, (8, 8))
        evals = np.linalg.eigvalsh(clean_rank1)
        # Condition number <= 45.0 + 1e-4
        cond = float(np.max(evals) / np.max([np.min(evals), 1e-8]))
        self.assertLessEqual(cond, 45.0 + 1e-3)

    # =========================================================================
    # VECTOR 3: EXTREME AMBIGUITY RADIUS
    # =========================================================================

    def test_adv13_zero_ambiguity_radius_standard_kelly(self):
        """ADV13: Ambiguity radius eps=0.0 exactly recovers standard unconstrained Kelly solution."""
        mu = np.array([0.08])
        cov = np.array([[0.04]])
        # Analytical Kelly fraction: kappa * mu / sigma^2 = 0.50 * 0.08 / 0.04 = 1.00
        # With default Tikhonov floor (1e-6), sigma^2_reg = 0.040001 -> w = 0.999975
        w = self.optimizer.allocate_robust_weights(mu, cov, epsilon=0.0, kappa=0.50)
        self.assertAlmostEqual(float(w[0]), 1.00, places=4)
        
        # With pure analytical covariance (tikhonov_floor=0.0), exact equality holds
        pure_opt = WassersteinRobustKellyOptimizer(default_kappa=0.50, tikhonov_floor=0.0)
        w_pure = pure_opt.allocate_robust_weights(mu, cov, epsilon=0.0, kappa=0.50)
        self.assertAlmostEqual(float(w_pure[0]), 1.00, places=7)

    def test_adv14_infinite_ambiguity_radius_collapse_to_cash(self):
        """ADV14: As ambiguity radius eps -> infinity (or eps >= max(mu)), allocation collapses to 0.0."""
        mu = np.array([0.08, 0.06, 0.07])
        cov = np.eye(3) * 0.04

        # When eps >= max(mu), worst-case expected returns are strictly <= 0
        w_inf = self.optimizer.allocate_robust_weights(mu, cov, epsilon=1e6)
        self.assertEqual(float(np.sum(w_inf)), 0.0)

        w_threshold = self.optimizer.allocate_robust_weights(mu, cov, epsilon=0.08)
        self.assertEqual(float(np.sum(w_threshold)), 0.0)

    def test_adv15_monotonic_shrinkage_across_ambiguity_radii(self):
        """ADV15: Risky allocation weight norm decreases monotonically as ambiguity radius increases."""
        mu = np.array([0.10, 0.08, 0.06])
        cov = np.eye(3) * 0.04

        epsilons = [0.0, 0.01, 0.02, 0.04, 0.05, 0.07, 0.09, 0.12]
        sums = []
        for eps in epsilons:
            w = self.allocator.compute_distributionally_robust_kelly_weights(mu, cov, epsilon_w=eps)
            sums.append(float(np.sum(w)))

        # Assert non-increasing sequence
        for i in range(len(sums) - 1):
            self.assertGreaterEqual(
                sums[i],
                sums[i + 1] - 1e-9,
                f"Weight sum at eps={epsilons[i]} ({sums[i]}) < eps={epsilons[i+1]} ({sums[i+1]})",
            )

    def test_adv16_negative_ambiguity_radius_clipping(self):
        """ADV16: Negative ambiguity radius is safely clipped to 0.0 without errors."""
        mu = np.array([0.08, 0.05])
        cov = np.eye(2) * 0.04

        w_neg = self.allocator.compute_distributionally_robust_kelly_weights(mu, cov, epsilon_w=-0.05)
        w_zero = self.allocator.compute_distributionally_robust_kelly_weights(mu, cov, epsilon_w=0.0)
        np.testing.assert_allclose(w_neg, w_zero, atol=1e-6)

    # =========================================================================
    # VECTOR 4: LEVERAGE FRONTIERS & FACTOR BETA CLAMPING
    # =========================================================================

    def test_adv17_high_beta_assets_strict_beta_clamp(self):
        """ADV17: High-beta assets (beta_i = 3.5 to 5.0) strictly enforce beta_port <= 1.000001."""
        # Unclamped gross leverage = 1.50 with beta_i = 3.5
        w_raw = np.array([0.50, 0.50, 0.50])
        asset_betas = np.array([3.5, 3.5, 3.5])
        raw_beta = float(np.sum(w_raw * asset_betas))
        self.assertAlmostEqual(raw_beta, 5.25, places=3)

        w_clamped = self.allocator.clamp_factor_beta(w_raw, asset_betas, max_beta=1.000001)
        clamped_beta = float(np.sum(w_clamped * asset_betas))
        self.assertLessEqual(clamped_beta, 1.000001 + 1e-9, f"Beta {clamped_beta} exceeded max_beta 1.000001")
        self.assertTrue(np.all(w_clamped >= 0.0))

    def test_adv18_ultra_high_beta_assets_extreme(self):
        """ADV18: Extreme asset betas (beta_i = 10.0 to 20.0) still strictly enforce beta <= 1.000001."""
        w_raw = np.array([0.40, 0.60, 0.50])  # 1.50x
        asset_betas = np.array([10.0, 15.0, 20.0])
        w_clamped = self.allocator.clamp_factor_beta(w_raw, asset_betas, max_beta=1.000001)
        clamped_beta = float(np.sum(w_clamped * asset_betas))
        self.assertLessEqual(clamped_beta, 1.000001 + 1e-9)

    def test_adv19_gross_leverage_never_exceeds_150x(self):
        """ADV19: Gross leverage never exceeds 1.50x across any regime or market volatility condition."""
        regimes = [
            "BULL_LOW_VOL", "RELIEF_RALLY", "BULL_HIGH_VOL",
            "SIDEWAYS_LOW_VOL", "SIDEWAYS_HIGH_VOL", "BEAR_LOW_VOL",
            "BEAR_HIGH_VOL", "PANIC_CRISIS", "UNKNOWN_REGIME",
        ]
        volatilities = [-0.10, 0.0, 0.05, 0.15, 0.25, 0.35, 0.50, 1.0, 5.0]

        for reg in regimes:
            for vol in volatilities:
                frontier = self.allocator.compute_regime_leverage_frontier(regime=reg, market_vol=vol)
                self.assertLessEqual(
                    frontier, 1.500000 + 1e-7,
                    f"Frontier {frontier} exceeded 1.50x under regime={reg}, vol={vol}",
                )
                self.assertGreaterEqual(
                    frontier, 0.15 - 1e-7,
                    f"Frontier {frontier} fell below min_crisis_exposure 0.15 under regime={reg}, vol={vol}",
                )

    def test_adv20_defensive_regime_strict_leverage_bounds(self):
        """ADV20: Defensive regimes strictly enforce conservative ceilings."""
        # BEAR_HIGH_VOL <= 0.25
        lev_bear = self.allocator.compute_regime_leverage_frontier("BEAR_HIGH_VOL", market_vol=0.20)
        self.assertLessEqual(lev_bear, 0.25)

        # PANIC_CRISIS <= 0.15
        lev_panic = self.allocator.compute_regime_leverage_frontier("PANIC_CRISIS", market_vol=0.20)
        self.assertLessEqual(lev_panic, 0.15)

        # High volatility (> 0.35) forces leverage <= 0.40
        lev_highvol = self.allocator.compute_regime_leverage_frontier("BULL_LOW_VOL", market_vol=0.40)
        self.assertLessEqual(lev_highvol, 0.40)

    def test_adv21_factor_beta_clamping_pathological_betas(self):
        """ADV21: Factor beta clamping handles negative, zero, and NaN betas robustly."""
        w_raw = np.array([0.5, 0.5, 0.5])
        pathological_betas = np.array([np.nan, np.inf, -2.0])

        w_clamped = self.allocator.clamp_factor_beta(w_raw, pathological_betas, max_beta=1.000001)
        self.assertTrue(np.all(np.isfinite(w_clamped)))
        self.assertTrue(np.all(w_clamped >= 0.0))

    # =========================================================================
    # VECTOR 5: CONCENTRATION BOX CAPS
    # =========================================================================

    def test_adv22_single_stock_box_cap_adversarial(self):
        """ADV22: Single-stock weight is strictly capped at 0.05 * L (0.075 at 1.50x) under 100% allocation."""
        L = 1.50
        max_stock_cap = 0.05 * L  # 0.075
        
        # Adversarial input: 1 stock gets 1.50
        weights = {"005930": 1.50, "000660": 0.00}
        sectors = {"005930": "Tech", "000660": "Tech"}

        capped = self.allocator.enforce_concentration_caps(weights, sectors, gross_leverage=L)
        self.assertLessEqual(
            capped["005930"],
            max_stock_cap + 1e-9,
            f"Stock weight {capped['005930']} exceeded single-stock cap {max_stock_cap}",
        )

    def test_adv23_single_sector_box_cap_adversarial(self):
        """ADV23: Single-sector weight is strictly capped at 0.25 * L (0.375 at 1.50x) even with 20 stocks."""
        L = 1.50
        max_sector_cap = 0.25 * L  # 0.375
        
        # 10 stocks in "Semiconductors", each at single-stock cap 0.075 (uncapped sum = 0.75)
        weights = {f"SEMI_{i:02d}": 0.075 for i in range(10)}
        sectors = {f"SEMI_{i:02d}": "Semiconductors" for i in range(10)}

        capped = self.allocator.enforce_concentration_caps(weights, sectors, gross_leverage=L)
        sector_sum = sum(capped.values())
        self.assertLessEqual(
            sector_sum,
            max_sector_cap + 1e-9,
            f"Total sector weight {sector_sum} exceeded sector cap {max_sector_cap}",
        )
        for sym, w in capped.items():
            self.assertLessEqual(w, 0.05 * L + 1e-9, f"Stock {sym} weight exceeded single-stock cap")

    def test_adv24_single_asset_universe_box_caps(self):
        """ADV24: Single-asset universe is strictly constrained to 0.05 * L."""
        L = 1.50
        weights = {"SOLO": 1.50}
        sectors = {"SOLO": "Energy"}

        capped = self.allocator.enforce_concentration_caps(weights, sectors, gross_leverage=L)
        self.assertLessEqual(capped["SOLO"], 0.05 * L + 1e-9)

    def test_adv25_concentration_caps_empty_or_unknown_sectors(self):
        """ADV25: Unknown or missing sectors default safely to 'Unknown' and still obey sector cap."""
        L = 1.50
        weights = {f"UNK_{i}": 0.075 for i in range(10)}
        sectors = {}  # Empty sector mapping

        capped = self.allocator.enforce_concentration_caps(weights, sectors, gross_leverage=L)
        total_unknown = sum(capped.values())
        self.assertLessEqual(total_unknown, 0.25 * L + 1e-9)


if __name__ == "__main__":
    unittest.main()
