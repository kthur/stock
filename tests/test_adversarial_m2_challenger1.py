"""
tests/test_adversarial_m2_challenger1.py - Adversarial Stress & Empirical Challenge Suite.
Milestone 2: Phase 141 Dynamic Regime Leverage & Kelly Allocator Architecture.

Challenger 1 Adversarial Dimensions:
1. Covariance Regularization Stress:
   - Degenerate returns matrices: singular matrices, zero-variance columns, all-NaN/constant returns.
   - Extreme rank deficiency: N=3,379 with T=30 (q = 112.63 > 100).
   - Collinear assets (correlation = 1.0).
   - Positive definiteness: all eigenvalues > 0, condition number bounded, exact unit diagonal (max error < 1e-12).
2. Fractional Kelly Simplex Stress:
   - Extreme returns (+/- 1000.0), all negative returns, zero returns, extreme fat tails.
   - Simplex constraint: sum(w) + w_cash == leverage within 1e-6.
   - Single stock cap: w_i <= 0.05 * leverage + 1e-6.
   - Sector cap: sum(w_sector) <= 0.25 * leverage + 1e-6.
   - Strict portfolio beta clamping: beta_port <= 1.000001 when leverage > 1.00 across 10,000 randomized beta scenarios.
"""

from __future__ import annotations

import os
import sys
import time
import unittest
import numpy as np
import pandas as pd

# Add project root and trading_system paths
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../trading_system")))

from src.risk.dynamic_regime_leverage_allocator import (
    DynamicRegimeLeverageAllocator,
    FractionalKellyAllocator,
    Phase141KellyAllocator,
    VERSION,
    RELEASE,
    FEATURE,
)


class TestAdversarialM2Challenger1(unittest.TestCase):
    """Adversarial Challenge & Empirical Stress Harness for Phase 141 Allocator."""

    def setUp(self):
        np.random.seed(42)
        self.allocator = DynamicRegimeLeverageAllocator()

    # =========================================================================
    # 1. COVARIANCE REGULARIZATION STRESS HARNESS
    # =========================================================================

    def test_adv01_singular_returns_matrix(self):
        """ADV-01: Singular returns matrix (rank 5 in N=50 dimensions)."""
        T, N = 80, 50
        # Generate rank 5 subspace
        factors = np.random.normal(0, 0.02, size=(T, 5))
        loadings = np.random.normal(0, 1, size=(5, N))
        X = factors @ loadings  # Exact rank <= 5
        
        cov, vols = self.allocator.compute_oas_rmt_covariance(X, top_k_modes=10)
        
        # Verify shape & symmetry
        self.assertEqual(cov.shape, (N, N))
        max_asymm = float(np.max(np.abs(cov - cov.T)))
        self.assertLess(max_asymm, 1e-12, f"Covariance asymmetry: {max_asymm}")

        # Verify positive definiteness
        evals = np.linalg.eigvalsh(cov)
        min_eval = float(np.min(evals))
        self.assertGreater(min_eval, 0.0, f"Non-positive eigenvalue: {min_eval}")
        self.assertGreaterEqual(min_eval, 1e-6, f"Eigenvalue below Tikhonov floor: {min_eval}")

        # Verify condition number bounded
        cond_num = float(np.linalg.cond(cov))
        self.assertLess(cond_num, 1e8, f"Condition number blown up: {cond_num}")

        # Verify exact unit correlation diagonal (max error < 1e-12)
        d = np.sqrt(np.diag(cov))
        corr = cov / np.outer(d, d)
        max_diag_err = float(np.max(np.abs(np.diag(corr) - 1.0)))
        self.assertLess(max_diag_err, 1e-12, f"Correlation diagonal error: {max_diag_err}")
        self.assertTrue(np.all(vols > 0.0))

    def test_adv02_zero_variance_columns(self):
        """ADV-02: Zero-variance columns (some assets constant 0.0, some constant 0.05)."""
        T, N = 100, 30
        X = np.random.normal(0.001, 0.02, size=(T, N))
        X[:, 0] = 0.0       # Constant zero
        X[:, 1] = 0.05      # Constant non-zero
        X[:, 2] = -0.02     # Another constant

        cov, vols = self.allocator.compute_oas_rmt_covariance(X)
        
        # Check no NaN
        self.assertFalse(np.any(np.isnan(cov)), "NaN found in cov")
        self.assertFalse(np.any(np.isnan(vols)), "NaN found in vols")

        # Positive definiteness
        evals = np.linalg.eigvalsh(cov)
        min_eval = float(np.min(evals))
        self.assertGreaterEqual(min_eval, 1e-6)

        # Condition number bounded
        cond_num = float(np.linalg.cond(cov))
        self.assertLess(cond_num, 1e8)

        # Exact unit diagonal on correlation
        d = np.sqrt(np.diag(cov))
        corr = cov / np.outer(d, d)
        max_diag_err = float(np.max(np.abs(np.diag(corr) - 1.0)))
        self.assertLess(max_diag_err, 1e-12, f"Unit diagonal error: {max_diag_err}")
        self.assertTrue(np.all(vols > 0.0))

    def test_adv03_all_nan_and_all_constant_returns(self):
        """ADV-03: All-NaN matrix and all-constant matrix degradation testing."""
        # 3a: All-NaN matrix
        X_nan = np.full((50, 20), np.nan)
        cov_nan, vols_nan = self.allocator.compute_oas_rmt_covariance(X_nan)
        self.assertFalse(np.any(np.isnan(cov_nan)))
        self.assertFalse(np.any(np.isnan(vols_nan)))
        evals_nan = np.linalg.eigvalsh(cov_nan)
        self.assertGreaterEqual(float(np.min(evals_nan)), 1e-6)
        d_nan = np.sqrt(np.diag(cov_nan))
        corr_nan = cov_nan / np.outer(d_nan, d_nan)
        self.assertLess(float(np.max(np.abs(np.diag(corr_nan) - 1.0))), 1e-12)

        # 3b: All-constant 0.0 matrix
        X_zero = np.zeros((50, 20))
        cov_zero, vols_zero = self.allocator.compute_oas_rmt_covariance(X_zero)
        evals_zero = np.linalg.eigvalsh(cov_zero)
        self.assertGreaterEqual(float(np.min(evals_zero)), 1e-6)
        d_zero = np.sqrt(np.diag(cov_zero))
        corr_zero = cov_zero / np.outer(d_zero, d_zero)
        self.assertLess(float(np.max(np.abs(np.diag(corr_zero) - 1.0))), 1e-12)

        # 3c: All-constant 0.03 matrix
        X_const = np.full((50, 20), 0.03)
        cov_const, vols_const = self.allocator.compute_oas_rmt_covariance(X_const)
        evals_const = np.linalg.eigvalsh(cov_const)
        self.assertGreaterEqual(float(np.min(evals_const)), 1e-6)
        d_const = np.sqrt(np.diag(cov_const))
        corr_const = cov_const / np.outer(d_const, d_const)
        self.assertLess(float(np.max(np.abs(np.diag(corr_const) - 1.0))), 1e-12)

    def test_adv04_collinear_assets_correlation_one(self):
        """ADV-04: Perfectly collinear assets (correlation = 1.0 between multiple pairs)."""
        T, N = 60, 25
        X = np.random.normal(0, 0.02, size=(T, N))
        # Make assets 1, 2, 3 exact duplicates of asset 0
        X[:, 1] = X[:, 0]
        X[:, 2] = X[:, 0] * 2.5
        X[:, 3] = -X[:, 0]  # Exact negative collinearity

        cov, vols = self.allocator.compute_oas_rmt_covariance(X)
        self.assertFalse(np.any(np.isnan(cov)))
        evals = np.linalg.eigvalsh(cov)
        self.assertGreaterEqual(float(np.min(evals)), 1e-6)
        self.assertLess(float(np.linalg.cond(cov)), 1e8)

        d = np.sqrt(np.diag(cov))
        corr = cov / np.outer(d, d)
        self.assertLess(float(np.max(np.abs(np.diag(corr) - 1.0))), 1e-12)

    def test_adv05_extreme_rank_deficiency_n3379_t30(self):
        """ADV-05: Institutional scale N=3,379 with T=30 (q = 112.63 > 100)."""
        T, N = 30, 3379
        q = N / T
        self.assertGreater(q, 100.0)

        # Generate institutional universe returns matrix with factor structure
        # Top 10 systematic factors + noise
        t0 = time.perf_counter()
        factors = np.random.normal(0, 0.02, size=(T, 10))
        loadings = np.random.normal(0, 0.5, size=(10, N))
        noise = np.random.normal(0, 0.01, size=(T, N))
        X = factors @ loadings + noise

        cov, vols = self.allocator.compute_oas_rmt_covariance(X, top_k_modes=50)
        elapsed = time.perf_counter() - t0

        # Performance assertion: high-dimensional spectral denoise finishes within sensible timeframe
        self.assertLess(elapsed, 30.0, f"N=3379 OAS-RMT took too long: {elapsed:.2f}s")
        self.assertEqual(cov.shape, (N, N))
        self.assertEqual(vols.shape, (N,))

        # Verify positive definiteness: all eigenvalues >= 1e-6
        evals = np.linalg.eigvalsh(cov)
        min_eval = float(np.min(evals))
        self.assertGreaterEqual(min_eval, 1e-6, f"Min eigenvalue below floor: {min_eval}")
        self.assertTrue(np.all(evals > 0.0))

        # Verify condition number bounded
        cond_num = float(np.max(evals) / min_eval)
        self.assertLess(cond_num, 1e8, f"Condition number too large: {cond_num}")

        # Verify unit diagonal on correlation
        d = np.sqrt(np.diag(cov))
        corr = cov / np.outer(d, d)
        max_diag_err = float(np.max(np.abs(np.diag(corr) - 1.0)))
        self.assertLess(max_diag_err, 1e-12, f"Correlation diagonal max error: {max_diag_err}")

    # =========================================================================
    # 2. FRACTIONAL KELLY SIMPLEX & RISK CONSTRAINT STRESS HARNESS
    # =========================================================================

    def test_adv06_extreme_returns_pos_neg_1000(self):
        """ADV-06: Extreme returns (returns = +/- 1000.0) stability and bounds."""
        N = 30
        mu = np.random.uniform(0.001, 0.005, N)
        mu[0] = 1000.0       # Extreme positive return
        mu[1] = -1000.0      # Extreme negative return
        mu[2] = 500.0
        mu[3] = -500.0

        cov = np.eye(N) * 0.0004
        for lev in [0.15, 0.60, 0.95, 1.00, 1.25]:
            w, w_cash = self.allocator.compute_fractional_kelly_weights(
                predicted_returns=mu,
                cov_matrix=cov,
                leverage=lev,
            )
            # Simplex constraint: sum(w) + w_cash == leverage within 1e-6
            self.assertAlmostEqual(float(np.sum(w) + w_cash), lev, places=6)
            # Long-only: w >= 0
            self.assertTrue(np.all(w >= -1e-12))
            # Single stock cap: w_i <= 0.05 * leverage
            cap_stock = 0.05 * lev
            self.assertLessEqual(float(np.max(w)), cap_stock + 1e-6)
            # Extreme negative return asset receives zero weight
            self.assertAlmostEqual(w[1], 0.0, places=6)
            self.assertAlmostEqual(w[3], 0.0, places=6)

    def test_adv07_all_negative_returns_100pct_cash(self):
        """ADV-07: All-negative returns guarantee 100% Cash preservation (zero equity exposure)."""
        N = 25
        for lev in [0.15, 0.50, 1.00, 1.25]:
            mu = np.random.uniform(-1000.0, -0.001, N)
            cov = np.eye(N) * 0.0004
            w, w_cash = self.allocator.compute_fractional_kelly_weights(mu, cov, leverage=lev)
            self.assertTrue(np.all(w == 0.0), f"Non-zero equity under all negative returns: {w}")
            self.assertAlmostEqual(w_cash, lev, places=6)
            self.assertAlmostEqual(float(np.sum(w) + w_cash), lev, places=6)

    def test_adv08_all_zero_returns_100pct_cash(self):
        """ADV-08: All-zero returns guarantee 100% Cash preservation."""
        N = 20
        for lev in [0.15, 0.85, 1.00, 1.25]:
            mu = np.zeros(N)
            cov = np.eye(N) * 0.0004
            w, w_cash = self.allocator.compute_fractional_kelly_weights(mu, cov, leverage=lev)
            self.assertTrue(np.all(w == 0.0))
            self.assertAlmostEqual(w_cash, lev, places=6)
            self.assertAlmostEqual(float(np.sum(w) + w_cash), lev, places=6)

    def test_adv09_extreme_fat_tails_co_moments(self):
        """ADV-09: Extreme fat tails: massive coskewness and cokurtosis co-moments."""
        N = 20
        mu = np.full(N, 0.005)
        cov = np.eye(N) * 0.0004
        
        # Asset 0: extreme positive coskewness (+100.0) -> higher return boost
        # Asset 1: extreme positive cokurtosis (+100.0) -> heavy tail risk penalty
        coskew = np.zeros(N)
        cokurt = np.zeros(N)
        coskew[0] = 100.0
        cokurt[1] = 100.0

        w, w_cash = self.allocator.compute_fractional_kelly_weights(
            predicted_returns=mu,
            cov_matrix=cov,
            leverage=1.25,
            coskewness=coskew,
            cokurtosis=cokurt,
        )
        self.assertAlmostEqual(float(np.sum(w) + w_cash), 1.25, places=6)
        self.assertLessEqual(float(np.max(w)), 0.05 * 1.25 + 1e-6)
        # Kurtosis penalized asset receives lower allocation than coskewness boosted asset
        self.assertLessEqual(w[1], w[0])

    def test_adv10_single_stock_cap_water_filling_varied_n(self):
        """ADV-10: Single-stock cap water-filling across varied N (N=5, 10, 20, 50, 100)."""
        for N in [5, 10, 20, 50, 100]:
            mu = np.linspace(0.001, 0.010, N)
            cov = np.eye(N) * 0.0004
            for lev in [0.30, 0.85, 1.00, 1.25]:
                cap_stock = 0.05 * lev
                w, w_cash = self.allocator.compute_fractional_kelly_weights(mu, cov, leverage=lev)
                
                # Assert single stock cap strictly respected
                max_w = float(np.max(w))
                self.assertLessEqual(max_w, cap_stock + 1e-6, f"N={N}, lev={lev}: max_w={max_w} > cap={cap_stock}")
                
                # Assert simplex equality
                self.assertAlmostEqual(float(np.sum(w) + w_cash), lev, places=6)
                
                # If N < 20, total equity cannot exceed N * cap_stock = N * 0.05 * lev
                if N < 20:
                    max_possible_equity = N * cap_stock
                    self.assertLessEqual(float(np.sum(w)), max_possible_equity + 1e-6)
                    self.assertGreaterEqual(w_cash, lev - max_possible_equity - 1e-6)

    def test_adv11_sector_cap_enforcement_and_redistribution(self):
        """ADV-11: Sector cap enforcement sum(w_sector) <= 0.25 * leverage across diverse sector maps."""
        N = 40
        mu = np.linspace(0.001, 0.008, N)
        cov = np.eye(N) * 0.0004
        # Sector 0 has 15 assets, Sector 1 has 15 assets, Sector 2 has 10 assets
        sector_indices = {
            "SEC_A": list(range(15)),
            "SEC_B": list(range(15, 30)),
            "SEC_C": list(range(30, 40)),
        }

        for lev in [0.50, 0.85, 1.00, 1.25]:
            cap_sector = 0.25 * lev
            cap_stock = 0.05 * lev
            w, w_cash = self.allocator.compute_fractional_kelly_weights(
                predicted_returns=mu,
                cov_matrix=cov,
                leverage=lev,
                sector_indices=sector_indices,
                max_sector_exposure=0.25,
            )
            # Check simplex
            self.assertAlmostEqual(float(np.sum(w) + w_cash), lev, places=6)

            # Check single stock cap
            self.assertLessEqual(float(np.max(w)), cap_stock + 1e-6)

            # Check sector caps
            for sec_name, idxs in sector_indices.items():
                sec_sum = float(np.sum(w[idxs]))
                self.assertLessEqual(
                    sec_sum,
                    cap_sector + 1e-6,
                    f"Sector {sec_name} exceeded cap: {sec_sum} > {cap_sector} (lev={lev})",
                )

    def test_adv12_strict_portfolio_beta_clamping_10000_scenarios(self):
        """ADV-12: Strict portfolio beta clamping: beta_port <= 1.000 across 10,000 randomized beta scenarios."""
        t0 = time.perf_counter()
        N = 25
        cov = np.eye(N) * 0.0004
        num_scenarios = 10000

        max_observed_beta = 0.0
        violations = []

        # Vectorized/batched loop testing 10,000 randomized asset beta vectors
        for i in range(num_scenarios):
            lev = 1.25 if (i % 2 == 0) else 1.10  # Leverage > 1.00
            mu = np.random.uniform(0.001, 0.006, N)
            # Generate aggressive betas between 0.8 and 2.5
            betas = np.random.uniform(0.8, 2.5, N)

            w, w_cash = self.allocator.compute_fractional_kelly_weights(
                predicted_returns=mu,
                cov_matrix=cov,
                leverage=lev,
                asset_betas=betas,
            )

            port_beta = float(np.sum(w * betas))
            if port_beta > max_observed_beta:
                max_observed_beta = port_beta

            # Tolerance check: beta_port <= 1.000001
            if port_beta > 1.000001:
                violations.append((i, lev, port_beta))

            # Simplex invariant check: sum(w) + w_cash == lev
            diff = abs(float(np.sum(w) + w_cash) - lev)
            if diff > 1e-6:
                self.fail(f"Scenario {i}: Simplex violated diff={diff}")

        elapsed = time.perf_counter() - t0
        print(f"\n[ADV-12] Tested {num_scenarios} randomized beta scenarios in {elapsed:.2f}s.")
        print(f"[ADV-12] Max observed portfolio beta: {max_observed_beta:.6f}")
        print(f"[ADV-12] Violations count: {len(violations)}")

        self.assertEqual(len(violations), 0, f"Beta clamping violations in {len(violations)} scenarios: {violations[:5]}")
        self.assertLessEqual(max_observed_beta, 1.000001)

    def test_adv13_simplex_invariants_across_all_8_regimes(self):
        """ADV-13: Simplex conservation across all 8 market regimes and frontiers."""
        N = 30
        mu = np.random.uniform(0.001, 0.004, N)
        cov = np.eye(N) * 0.0003
        
        regimes = [
            "BULL_LOW_VOL",
            "RELIEF_RALLY",
            "BULL_HIGH_VOL",
            "SIDEWAYS_LOW_VOL",
            "SIDEWAYS_HIGH_VOL",
            "BEAR_LOW_VOL",
            "BEAR_HIGH_VOL",
            "PANIC_CRISIS",
        ]

        for reg in regimes:
            # Evaluate leverage frontier
            lev = self.allocator.evaluate_dynamic_leverage_frontier(
                current_nav=100.0,
                vix=16.0,
                vix_history=[15.0] * 5,
                tsr_ratio=0.88,
                regime=reg,
                tsr_history=[0.88] * 5,
            )
            self.assertGreaterEqual(lev, 0.15)
            self.assertLessEqual(lev, 1.25)

            w, w_cash = self.allocator.compute_fractional_kelly_weights(
                predicted_returns=mu,
                cov_matrix=cov,
                leverage=lev,
                regime=reg,
            )
            # Simplex conservation
            total = float(np.sum(w) + w_cash)
            self.assertAlmostEqual(total, lev, places=6, msg=f"Regime {reg} failed simplex conservation")


if __name__ == "__main__":
    unittest.main()
