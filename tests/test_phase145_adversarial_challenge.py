"""
tests/test_phase145_adversarial_challenge.py - Empirical Adversarial Stress Harness for Phase 145.
Author: Challenger 1 & 2 (Phase 145, Features F705-F709).

Empirically tests:
1. Degenerate / singular return covariance matrices:
   - T < N (high-dimensional rank deficiency)
   - Perfectly collinear assets
   - Zero-variance / constant assets
   - Non-invertible / singular covariance passed to fractional Kelly
2. Extreme fat-tail coskewness/cokurtosis inputs:
   - Massive negative coskewness & positive cokurtosis
   - Heavy-tailed Student-t / Cauchy distributions
   - Co-moment penalty directionality and risk reduction
3. Rapid VIX velocity jumps (> 3.0/day) and TSR inversions (TSR >= 1.08):
   - Sudden VIX spikes and multi-tier gating envelope
4. 5-day contango lock in RELIEF_RALLY:
   - Ensuring leverage does NOT expand to 1.30x until 5 full consecutive days of TSR < 0.95
   - Handling of missing, short, or interrupted history
5. High-Water Mark (HWM) drawdown ladder & circuit breaker:
   - Exact piece-wise thresholds (-4%, -7%, -10%, -12%)
6. UnifiedPortfolioAllocator integration and dynamic leverage enforcement (up to 1.30x).
7. Memory leak and numerical stability over repetitive allocations (using tracemalloc).
"""

from __future__ import annotations

import os
import sys
import tracemalloc
import unittest
import numpy as np
import pandas as pd

# Path setup
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../trading_system")))

from src.risk.dynamic_regime_leverage_allocator import DynamicRegimeLeverageAllocator
from src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator
from src.risk.portfolio_allocator import PortfolioAllocator


class TestPhase145AdversarialChallenge(unittest.TestCase):
    """Adversarial stress testing suite for DynamicRegimeLeverageAllocator and its integration."""

    def setUp(self):
        np.random.seed(1337)
        self.allocator = DynamicRegimeLeverageAllocator(
            max_bull_leverage=1.30,
            min_crisis_exposure=0.15,
            borrowing_spread_bps=60.0,
            hwm_dd_limit=-0.15,
            default_kappa=0.375,
            top_k_modes=50,
        )

    # =========================================================================
    # Section 1: Degenerate / Singular Return Covariance Matrices
    # =========================================================================

    def test_cov_high_dim_rank_deficiency_t_less_than_n(self):
        """Stress: T=20 samples, N=100 assets (T << N). Regularizer must guarantee positive definiteness."""
        T, N = 20, 100
        returns_raw = np.random.normal(0.0005, 0.02, size=(T, N))
        cov_final, vols = self.allocator.compute_oas_rmt_covariance(returns_raw, top_k_modes=10)

        self.assertEqual(cov_final.shape, (N, N))
        self.assertEqual(len(vols), N)
        self.assertTrue(np.all(np.isfinite(cov_final)))
        self.assertTrue(np.all(np.isfinite(vols)))

        # Symmetry check
        np.testing.assert_allclose(cov_final, cov_final.T, atol=1e-10)

        # Minimum eigenvalue must be strictly positive (positive definiteness)
        eigvals = np.linalg.eigvalsh(cov_final)
        self.assertGreater(float(np.min(eigvals)), 1e-7, "Covariance is not positive definite under T << N")

    def test_cov_perfectly_collinear_assets(self):
        """Stress: Multiple collinear assets (identical or scaled copies)."""
        T, N = 60, 10
        base_series = np.random.normal(0.001, 0.02, size=(T, 1))
        unique_series = np.random.normal(0.001, 0.02, size=(T, 5))
        collinear_copies = np.repeat(base_series, 5, axis=1)
        X = np.hstack([unique_series, collinear_copies])

        cov_final, vols = self.allocator.compute_oas_rmt_covariance(X, top_k_modes=3)
        self.assertEqual(cov_final.shape, (N, N))
        self.assertTrue(np.all(np.isfinite(cov_final)))

        eigvals = np.linalg.eigvalsh(cov_final)
        self.assertGreater(float(np.min(eigvals)), 1e-7, "Collinear matrix failed positive definiteness")

    def test_cov_zero_variance_assets(self):
        """Stress: Asset with exactly zero variance (flat price)."""
        T, N = 50, 8
        X = np.random.normal(0.001, 0.015, size=(T, N))
        X[:, 2] = 0.0  # Flat asset 2
        X[:, 5] = 0.0  # Flat asset 5

        cov_final, vols = self.allocator.compute_oas_rmt_covariance(X, top_k_modes=2)
        self.assertTrue(np.all(np.isfinite(cov_final)))
        self.assertTrue(np.all(np.isfinite(vols)))
        self.assertGreater(vols[2], 0.0)
        self.assertGreater(vols[5], 0.0)
        self.assertTrue(np.all(np.linalg.eigvalsh(cov_final) >= 1e-7))

    def test_kelly_with_singular_covariance_matrix(self):
        """Stress: Passing a completely non-invertible matrix to fractional Kelly solver."""
        N = 10
        # Rank-1 outer product matrix
        v = np.ones(N) * 0.02
        singular_cov = np.outer(v, v)
        mu = np.full(N, 0.002)

        w, w_cash = self.allocator.compute_fractional_kelly_weights(
            predicted_returns=mu,
            cov_matrix=singular_cov,
            leverage=1.30,
        )
        self.assertEqual(len(w), N)
        self.assertTrue(np.all(np.isfinite(w)))
        self.assertTrue(np.isfinite(w_cash))
        self.assertAlmostEqual(float(np.sum(w) + w_cash), 1.30, places=5)

    def test_kelly_all_negative_expected_returns(self):
        """Stress: All expected returns are negative or zero -> must allocate 100% Cash."""
        N = 20
        mu = np.random.uniform(-0.010, -0.0001, N)
        cov = np.eye(N) * 0.0004
        w, w_cash = self.allocator.compute_fractional_kelly_weights(
            predicted_returns=mu,
            cov_matrix=cov,
            leverage=1.30,
        )
        self.assertTrue(np.all(w == 0.0))
        self.assertAlmostEqual(w_cash, 1.30, places=6)

    # =========================================================================
    # Section 2: Extreme Fat-Tail Co-Moment Contraction (Feature F705)
    # =========================================================================

    def test_fat_tail_extreme_skew_kurtosis_contraction(self):
        """Stress: Extreme negative coskewness & explosive cokurtosis."""
        N = 5
        mu = np.full(N, 0.005)
        cov = np.eye(N) * 0.0004
        # Normal returns baseline
        w_norm, _ = self.allocator.compute_fractional_kelly_weights(mu, cov, leverage=1.30)

        # Extreme crash vulnerability: s_w << 0, k_w >> 0
        s_extreme = np.full(N, -0.010)
        k_extreme = np.full(N, 0.050)
        w_fat, w_cash_fat = self.allocator.compute_fractional_kelly_weights(
            mu, cov, leverage=1.30, coskewness=s_extreme, cokurtosis=k_extreme
        )
        # Fat-tail contraction must reduce equity allocation and boost cash
        self.assertLess(float(np.sum(w_fat)), float(np.sum(w_norm)))
        self.assertGreater(w_cash_fat, 0.0)

    def test_fat_tail_student_t_heavy_tailed_data(self):
        """Stress: Synthetic Student-t (df=3, heavy tails, infinite 4th moment risk)."""
        T, N = 250, 15
        np.random.seed(42)
        # Student-t with df=3
        heavy_returns = np.random.standard_t(df=3, size=(T, N)) * 0.02
        s_w, k_w = self.allocator.compute_higher_order_co_moments(heavy_returns)

        self.assertEqual(len(s_w), N)
        self.assertEqual(len(k_w), N)
        self.assertTrue(np.all(np.isfinite(s_w)))
        self.assertTrue(np.all(np.isfinite(k_w)))
        # Kurtosis is positive for heavy-tailed distribution
        self.assertTrue(np.mean(k_w) >= 0.0)

    # =========================================================================
    # Section 3: Rapid VIX Velocity & Term Structure Slope (Feature F707)
    # =========================================================================

    def test_vix_velocity_severe_jump_over_3_per_day(self):
        """Stress: VIX jumps from 15 to 35 in 5 days (vel = 4.0/day). Immediate defense."""
        vix_hist = [15.0, 17.0, 21.0, 28.0, 15.0]
        L = self.allocator.evaluate_dynamic_leverage_frontier(
            current_nav=100.0,
            vix=35.0,
            vix_history=vix_hist,
            tsr_ratio=0.90,
            regime="BULL_LOW_VOL",
        )
        self.assertLessEqual(L, 0.40)

    def test_vix_velocity_jump_with_low_absolute_vix(self):
        """Stress: Absolute VIX is moderate (19.0), but velocity is rapid (+1.2/day)."""
        vix_hist = [13.0, 13.0, 13.0, 13.0, 13.0]  # vel = (19 - 13) / 5 = 1.2 > 1.0
        L = self.allocator.evaluate_dynamic_leverage_frontier(
            current_nav=100.0,
            vix=19.0,
            vix_history=vix_hist,
            tsr_ratio=0.90,
            regime="BULL_LOW_VOL",
        )
        self.assertLessEqual(L, 0.75)

    def test_tsr_inversion_boundary_and_extreme(self):
        """Stress: TSR inversion at boundary (1.00) and severe backwardation (1.30)."""
        vix_hist = [15.0]*5
        # Mild inversion: TSR = 1.02 -> 0.80x
        L_mild = self.allocator.evaluate_dynamic_leverage_frontier(
            100.0, 16.0, vix_hist, 1.02, "BULL_LOW_VOL"
        )
        self.assertAlmostEqual(L_mild, 0.80, places=5)

        # Severe backwardation: TSR = 1.30 -> 0.50x
        L_sev = self.allocator.evaluate_dynamic_leverage_frontier(
            100.0, 16.0, vix_hist, 1.30, "BULL_LOW_VOL"
        )
        self.assertAlmostEqual(L_sev, 0.50, places=5)

    def test_simultaneous_vix_jump_and_tsr_inversion(self):
        """Stress: Dual shock: VIX velocity spike (vel=2.5) + TSR backwardation (1.20)."""
        vix_hist = [15.0]*5
        L = self.allocator.evaluate_dynamic_leverage_frontier(
            100.0, 27.5, vix_hist, 1.20, "BULL_LOW_VOL"
        )
        # Gate 1 caps at 0.40, Gate 2 caps at 0.50 -> Min envelope is 0.40
        self.assertAlmostEqual(L, 0.40, places=5)

    # =========================================================================
    # Section 4: RELIEF_RALLY 5-Day Contango Lock Hysteresis
    # =========================================================================

    def test_relief_rally_contango_lock_satisfied_5_full_days(self):
        """Ensure leverage expands to 1.30x ONLY when 5 full consecutive days < 0.95."""
        tsr_5d = [0.94, 0.93, 0.92, 0.90, 0.89]
        L = self.allocator.evaluate_dynamic_leverage_frontier(
            100.0, 16.0, [15.0]*5, 0.89, "RELIEF_RALLY", tsr_history=tsr_5d
        )
        self.assertAlmostEqual(L, 1.30, places=5)

    def test_relief_rally_contango_lock_interrupted(self):
        """Any day in past 5 days >= 0.95 locks leverage at 0.90x."""
        tsr_interrupted = [0.92, 0.91, 0.96, 0.90, 0.88]  # Day 3 breached
        L = self.allocator.evaluate_dynamic_leverage_frontier(
            100.0, 16.0, [15.0]*5, 0.88, "RELIEF_RALLY", tsr_history=tsr_interrupted
        )
        self.assertAlmostEqual(L, 0.90, places=5)

    def test_relief_rally_contango_lock_less_than_5_days(self):
        """Fewer than 5 days history defaults safely to 0.90x."""
        tsr_short = [0.90, 0.89, 0.91]
        L = self.allocator.evaluate_dynamic_leverage_frontier(
            100.0, 16.0, [15.0]*5, 0.89, "RELIEF_RALLY", tsr_history=tsr_short
        )
        self.assertAlmostEqual(L, 0.90, places=5)

    def test_relief_rally_missing_tsr_history(self):
        """None or empty history defaults safely to 0.90x."""
        L = self.allocator.evaluate_dynamic_leverage_frontier(
            100.0, 16.0, [15.0]*5, 0.89, "RELIEF_RALLY", tsr_history=None
        )
        self.assertAlmostEqual(L, 0.90, places=5)

    # =========================================================================
    # Section 5: High-Water Mark (HWM) Drawdown Ladder
    # =========================================================================

    def test_drawdown_ladder_exact_thresholds(self):
        """Assert exact drawdown thresholds: -4%, -7%, -10%, -12%."""
        alloc = DynamicRegimeLeverageAllocator(max_bull_leverage=1.30)
        vix_hist = [14.0]*5
        alloc.evaluate_dynamic_leverage_frontier(100.0, 14.0, vix_hist, 0.88, "BULL_LOW_VOL")

        # DD = -3.9% (>= -4.0%) -> 1.30x
        self.assertAlmostEqual(alloc.evaluate_dynamic_leverage_frontier(96.1, 14.0, vix_hist, 0.88, "BULL_LOW_VOL"), 1.30, places=4)

        # DD = -5.5% (midpoint of [-7%, -4%]) -> 1.15x
        self.assertAlmostEqual(alloc.evaluate_dynamic_leverage_frontier(94.5, 14.0, vix_hist, 0.88, "BULL_LOW_VOL"), 1.15, places=4)

        # DD = -7.0% -> 0.85x
        self.assertAlmostEqual(alloc.evaluate_dynamic_leverage_frontier(93.0, 14.0, vix_hist, 0.88, "BULL_LOW_VOL"), 0.85, places=4)

        # DD = -9.9% -> 0.85x
        self.assertAlmostEqual(alloc.evaluate_dynamic_leverage_frontier(90.1, 14.0, vix_hist, 0.88, "BULL_LOW_VOL"), 0.85, places=4)

        # DD = -10.0% -> 0.50x
        self.assertAlmostEqual(alloc.evaluate_dynamic_leverage_frontier(90.0, 14.0, vix_hist, 0.88, "BULL_LOW_VOL"), 0.50, places=4)

        # DD = -11.9% -> 0.50x
        self.assertAlmostEqual(alloc.evaluate_dynamic_leverage_frontier(88.1, 14.0, vix_hist, 0.88, "BULL_LOW_VOL"), 0.50, places=4)

        # DD = -12.0% -> 0.15x
        self.assertAlmostEqual(alloc.evaluate_dynamic_leverage_frontier(88.0, 14.0, vix_hist, 0.88, "BULL_LOW_VOL"), 0.15, places=4)

    # =========================================================================
    # Section 6: UnifiedPortfolioAllocator Phase 145 Integration
    # =========================================================================

    def test_unified_allocator_phase145_leverage_and_beta_clamping(self):
        """UnifiedPortfolioAllocator with version=145 scales leverage up to 1.30x in low-vol bull regime."""
        upa = UnifiedPortfolioAllocator(version=145)
        self.assertTrue(upa.is_phase145)
        self.assertTrue(upa.is_phase141)
        self.assertTrue(upa.enable_dynamic_regime_leverage)
        self.assertEqual(upa.regime_leverage_allocator.max_bull_leverage, 1.30)

        # Test apply_target_volatility_scaling with bull low-vol regime
        w = np.array([0.5, 0.5])
        cov = np.eye(2) * 0.00004
        scaled_w, effective_alloc = upa.apply_target_volatility_scaling(
            weights=w,
            cov_matrix=cov,
            regime="BULL_LOW_VOL",
            expected_returns=np.array([0.15, 0.15]),
        )
        self.assertAlmostEqual(effective_alloc, 1.30, places=2)
        self.assertAlmostEqual(float(np.sum(scaled_w)), 1.30, places=2)

        # Test beta clamping when port_beta > 1.00
        scaled_w_beta, _ = upa.apply_target_volatility_scaling(
            weights=w,
            cov_matrix=cov,
            regime="BULL_LOW_VOL",
            expected_returns=np.array([0.15, 0.15]),
            asset_betas=np.array([1.2, 1.2]),
        )
        port_beta = float(np.sum(scaled_w_beta * np.array([1.2, 1.2])))
        self.assertLessEqual(port_beta, 1.000001)

    def test_portfolio_allocator_dynamic_rebalance_with_leverage(self):
        """PortfolioAllocator with version=145 supports leverage=1.30 in compute_portfolio_rebalance."""
        pa = PortfolioAllocator(version=145)
        self.assertTrue(pa.is_phase145)
        curr_w = {"A": 0.0, "B": 0.0}
        tgt_w = {"A": 0.65, "B": 0.65}
        mkt_map = {"A": "SP500", "B": "SP500"}
        vol_map = {"A": 0.02, "B": 0.02}
        adv_map = {"A": 1e9, "B": 1e9}

        res = pa.compute_portfolio_rebalance(
            current_weights=curr_w,
            target_weights=tgt_w,
            market_map=mkt_map,
            volatility_map=vol_map,
            adv_map=adv_map,
            leverage=1.30,
        )
        total_alloc = res["summary"]["total_asset_weight"]
        self.assertAlmostEqual(total_alloc, 1.30, places=4)
        self.assertAlmostEqual(res["summary"]["cash_weight"], 0.0, places=4)

    # =========================================================================
    # Section 7: Memory Stability & Numerical Reproducibility (Tracemalloc)
    # =========================================================================

    def test_memory_stability_repetitive_allocations(self):
        """Stress: 100 consecutive allocations do not cause unbounded memory growth."""
        tracemalloc.start()
        snapshot1 = tracemalloc.take_snapshot()

        N = 30
        for _ in range(100):
            mu = np.random.uniform(0.001, 0.005, N)
            cov = np.eye(N) * 0.0004
            self.allocator.compute_fractional_kelly_weights(mu, cov, leverage=1.30)

        snapshot2 = tracemalloc.take_snapshot()
        tracemalloc.stop()

        top_stats = snapshot2.compare_to(snapshot1, 'lineno')
        total_growth_kb = sum(stat.size_diff for stat in top_stats) / 1024.0
        # Memory growth across 100 small solves should be modest (< 5000 KB)
        self.assertLess(total_growth_kb, 5000.0, f"Memory growth exceeded limit: {total_growth_kb} KB")


if __name__ == "__main__":
    unittest.main()
