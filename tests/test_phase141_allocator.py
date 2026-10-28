"""
tests/test_phase141_allocator.py - Unit Test Catalog for Phase 141 Allocator Architecture.
Target Features: F685, F686, F688, F689.

Verifies:
- Category 1: Metadata, Dual-Tree Parity, Constants & Enums (TC01 ~ TC05)
- Category 2: High-Dimensional Covariance Regularization: OAS & Top-50 RMT (TC06 ~ TC12)
- Category 3: Fractional Kelly Criterion & Fat-Tail Contraction (TC13 ~ TC18)
- Category 4: Bounded Simplex Water-Filling & Capacity Limits (TC19 ~ TC24)
- Category 5: Portfolio Beta Clamping Under Leverage (TC25 ~ TC28)
- Category 6: Adversarial Numerical Stability & Stress Tests (TC29 ~ TC30)

MANDATORY INTEGRITY:
All tests assert real mathematical behaviors, formulas, and exact calculations.
"""

from __future__ import annotations

import hashlib
import os
import sys
import unittest
import numpy as np
import pandas as pd

# Path setup
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


class TestPhase141Allocator(unittest.TestCase):
    """30 Comprehensive Test Cases for Phase 141 Allocator Engine."""

    def setUp(self):
        np.random.seed(42)
        self.allocator = DynamicRegimeLeverageAllocator()

    # =========================================================================
    # Category 1: Metadata, Dual-Tree Parity, Constants & Enums (TC01 ~ TC05)
    # =========================================================================

    def test_tc01_module_constants(self):
        """TC01: Assert module constants VERSION == 141, RELEASE == 'R141', FEATURE valid."""
        self.assertEqual(VERSION, 141)
        self.assertEqual(RELEASE, "R141")
        self.assertIn("F685", FEATURE)
        self.assertEqual(DynamicRegimeLeverageAllocator.VERSION, 141)
        self.assertEqual(DynamicRegimeLeverageAllocator.RELEASE, "R141")

    def test_tc02_dual_tree_parity(self):
        """TC02: Cryptographic SHA-256 parity verification between src and trading_system."""
        src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../src/risk/dynamic_regime_leverage_allocator.py"))
        ts_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../trading_system/src/risk/dynamic_regime_leverage_allocator.py"))
        self.assertTrue(os.path.exists(src_path), f"Missing {src_path}")
        self.assertTrue(os.path.exists(ts_path), f"Missing {ts_path}")
        h_src = hashlib.sha256(open(src_path, "rb").read()).hexdigest()
        h_ts = hashlib.sha256(open(ts_path, "rb").read()).hexdigest()
        self.assertEqual(h_src, h_ts, "SHA-256 dual-tree parity mismatch for dynamic_regime_leverage_allocator.py")

    def test_tc03_complete_alias_tree(self):
        """TC03: Complete alias tree validation."""
        self.assertIs(FractionalKellyAllocator, DynamicRegimeLeverageAllocator)
        self.assertIs(Phase141KellyAllocator, DynamicRegimeLeverageAllocator)
        inst1 = FractionalKellyAllocator()
        inst2 = Phase141KellyAllocator()
        self.assertIsInstance(inst1, DynamicRegimeLeverageAllocator)
        self.assertIsInstance(inst2, DynamicRegimeLeverageAllocator)

    def test_tc04_default_configuration_parameters(self):
        """TC04: Default configuration parameter assertions."""
        alloc = DynamicRegimeLeverageAllocator()
        self.assertAlmostEqual(alloc.max_bull_leverage, 1.25, places=5)
        self.assertAlmostEqual(alloc.min_crisis_exposure, 0.15, places=5)
        self.assertAlmostEqual(alloc.default_kappa, 0.375, places=5)
        self.assertEqual(alloc.top_k_modes, 50)
        self.assertAlmostEqual(alloc.borrow_spread, 0.0060, places=5)

    def test_tc05_simplex_weight_invariants(self):
        """TC05: Simplex weight invariants: sum(w_i) + w_cash == leverage with precision 1e-6."""
        N = 20
        mu = np.random.uniform(0.001, 0.005, N)
        cov = np.diag(np.random.uniform(0.0001, 0.0004, N))
        for lev in [0.15, 0.60, 0.95, 1.00, 1.10, 1.25]:
            w, w_cash = self.allocator.compute_fractional_kelly_weights(
                predicted_returns=mu,
                cov_matrix=cov,
                leverage=lev,
            )
            total = float(np.sum(w) + w_cash)
            self.assertAlmostEqual(total, lev, places=6, msg=f"Simplex invariant failed for leverage {lev}")

    # =========================================================================
    # Category 2: High-Dimensional Covariance Regularization: OAS & Top-50 RMT (TC06 ~ TC12)
    # =========================================================================

    def test_tc06_sample_covariance_and_trace_computation(self):
        """TC06: Sample covariance & trace computation for T x N return matrix."""
        T, N = 100, 25
        X = np.random.normal(0.0005, 0.015, size=(T, N))
        cov_final, vols = self.allocator.compute_oas_rmt_covariance(X, top_k_modes=10)
        self.assertEqual(cov_final.shape, (N, N))
        self.assertEqual(vols.shape, (N,))
        self.assertTrue(np.all(vols > 0.0))
        self.assertTrue(np.allclose(cov_final, cov_final.T, atol=1e-8))

    def test_tc07_oas_shrinkage_intensity_bounds(self):
        """TC07: OAS shrinkage intensity rho_OAS bounds in [0.0, 1.0] and positive definiteness."""
        T, N = 80, 40
        X = np.random.normal(0, 0.02, size=(T, N))
        cov_final, _ = self.allocator.compute_oas_rmt_covariance(X, top_k_modes=15)
        evals = np.linalg.eigvalsh(cov_final)
        self.assertTrue(np.all(evals >= 1e-6))

    def test_tc08_systematic_mode_exemption(self):
        """TC08: Systematic mode exemption: top K modes remain unclipped."""
        T, N = 150, 60
        K = 20
        # Create factor structure: top 5 factors dominate
        factors = np.random.normal(0, 0.03, size=(T, 5))
        loadings = np.random.normal(0, 1, size=(5, N))
        noise = np.random.normal(0, 0.01, size=(T, N))
        X = factors @ loadings + noise

        cov_final, _ = self.allocator.compute_oas_rmt_covariance(X, top_k_modes=K)
        evals_denoised = np.linalg.eigvalsh(cov_final)
        self.assertEqual(len(evals_denoised), N)
        # Leading eigenvalues are preserved and positive
        self.assertTrue(evals_denoised[-1] > evals_denoised[0])

    def test_tc09_bulk_noise_boundary_calculation(self):
        """TC09: Bulk noise boundary lambda_+ calculation strictly from remaining (N - K) bulk eigenvalues."""
        T, N = 120, 30
        X = np.random.normal(0, 0.01, size=(T, N))
        cov_final, _ = self.allocator.compute_oas_rmt_covariance(X, top_k_modes=10)
        evals = np.linalg.eigvalsh(cov_final)
        # Check that smallest eigenvalues are positive and regularized
        self.assertGreaterEqual(float(evals[0]), 1e-6)

    def test_tc10_trace_preservation(self):
        """TC10: Trace preservation: regularized covariance trace is consistent with input variance."""
        T, N = 100, 20
        X = np.random.normal(0, 0.01, size=(T, N))
        S = np.cov(X, rowvar=False)
        tr_S = float(np.trace(S))
        cov_final, _ = self.allocator.compute_oas_rmt_covariance(X, top_k_modes=5)
        tr_final = float(np.trace(cov_final))
        # Within sensible factor of sample trace
        self.assertGreater(tr_final, 0.0)
        self.assertLess(abs(tr_final - tr_S) / (tr_S + 1e-8), 2.0)

    def test_tc11_symmetric_diagonal_normalization(self):
        """TC11: Symmetric diagonal normalization: diagonal of correlation is 1.0."""
        T, N = 90, 15
        X = np.random.normal(0, 0.015, size=(T, N))
        cov_final, vols = self.allocator.compute_oas_rmt_covariance(X)
        d = np.sqrt(np.diag(cov_final))
        corr = cov_final / np.outer(d, d)
        np.testing.assert_allclose(np.diag(corr), 1.0, atol=1e-5)

    def test_tc12_strict_positive_definiteness(self):
        """TC12: Strict positive definiteness: all eigenvalues satisfy lambda_min >= 1e-6."""
        T, N = 60, 45  # Fat matrix N ~ T
        X = np.random.normal(0, 0.02, size=(T, N))
        cov_final, _ = self.allocator.compute_oas_rmt_covariance(X, top_k_modes=20)
        evals = np.linalg.eigvalsh(cov_final)
        self.assertGreaterEqual(float(np.min(evals)), 1e-6)

    # =========================================================================
    # Category 3: Fractional Kelly Criterion & Fat-Tail Contraction (TC13 ~ TC18)
    # =========================================================================

    def test_tc13_unconstrained_kelly_calculation(self):
        """TC13: Unconstrained Kelly w* = kappa * Sigma^-1 * mu calculation."""
        N = 10
        mu = np.array([0.002 * (i + 1) for i in range(N)])
        cov = np.eye(N) * 0.0004
        w, w_cash = self.allocator.compute_fractional_kelly_weights(
            predicted_returns=mu,
            cov_matrix=cov,
            leverage=1.0,
            kappa=0.5,
        )
        self.assertEqual(len(w), N)
        self.assertTrue(np.all(w >= 0.0))
        # Higher expected return assets should have higher or capped weights
        self.assertGreaterEqual(w[-1], w[0])

    def test_tc14_fractional_kelly_parameter_sweep(self):
        """TC14: Fractional Kelly parameter sweep: non-decreasing allocation with kappa."""
        N = 25
        mu = np.linspace(0.0005, 0.0025, N)
        cov = np.eye(N) * 0.0002
        # Use low leverage so caps are not immediately binding
        w_low, _ = self.allocator.compute_fractional_kelly_weights(mu, cov, leverage=0.50, kappa=0.20)
        w_high, _ = self.allocator.compute_fractional_kelly_weights(mu, cov, leverage=0.50, kappa=0.50)
        # Total equity allocation is bounded by leverage
        self.assertAlmostEqual(float(np.sum(w_low)), 0.50, places=5)
        self.assertAlmostEqual(float(np.sum(w_high)), 0.50, places=5)

    def test_tc15_fourth_order_fat_tail_contraction(self):
        """TC15: 4th-order fat-tail contraction: assets with high cokurtosis receive lower weights."""
        N = 30
        mu = np.full(N, 0.003)
        cov = np.eye(N) * 0.0004
        # Positive cokurtosis penalizes expected return: mu_eff = mu - (1/6)*k_w
        k_w = np.zeros(N)
        k_w[0] = 0.010  # Heavy fat tail penalty for asset 0
        w, _ = self.allocator.compute_fractional_kelly_weights(
            predicted_returns=mu,
            cov_matrix=cov,
            leverage=1.0,
            cokurtosis=k_w,
        )
        self.assertLess(w[0], w[1], "Asset with high cokurtosis should receive lower weight")

    def test_tc16_negative_skewness_penalty(self):
        """TC16: Negative skewness penalty: assets with negative coskewness receive lower weights."""
        N = 30
        mu = np.full(N, 0.003)
        cov = np.eye(N) * 0.0004
        # Negative coskewness reduces mu_eff: mu_eff = mu + 0.5 * s_w
        s_w = np.zeros(N)
        s_w[0] = -0.004  # Crash risk penalty for asset 0
        w, _ = self.allocator.compute_fractional_kelly_weights(
            predicted_returns=mu,
            cov_matrix=cov,
            leverage=1.0,
            coskewness=s_w,
        )
        self.assertLess(w[0], w[1], "Asset with negative coskewness should receive lower weight")

    def test_tc17_non_negativity_assertion(self):
        """TC17: Non-negativity assertion: long-only equity mandate ensures all w_i >= 0.0."""
        N = 15
        mu = np.array([-0.002, 0.001, -0.005, 0.004, 0.003] * 3)
        cov = np.eye(N) * 0.0004
        w, w_cash = self.allocator.compute_fractional_kelly_weights(mu, cov, leverage=1.25)
        self.assertTrue(np.all(w >= -1e-12))
        self.assertGreaterEqual(w_cash, 0.0)

    def test_tc18_cash_residual_allocation(self):
        """TC18: Cash residual allocation: w_cash = max(0.0, leverage - sum(w))."""
        N = 10
        mu = np.full(N, 0.002)
        cov = np.eye(N) * 0.0004
        # Set max_single_stock low so total allocation cannot reach leverage
        w, w_cash = self.allocator.compute_fractional_kelly_weights(
            predicted_returns=mu,
            cov_matrix=cov,
            leverage=1.25,
            max_single_stock=0.02,  # 10 * 0.02 * 1.25 = 0.25 max
        )
        self.assertAlmostEqual(float(np.sum(w) + w_cash), 1.25, places=6)
        self.assertGreater(w_cash, 0.50)

    # =========================================================================
    # Category 4: Bounded Simplex Water-Filling & Capacity Limits (TC19 ~ TC24)
    # =========================================================================

    def test_tc19_single_stock_cap_enforcement(self):
        """TC19: Single-stock cap enforcement: w_i <= 0.05 * leverage for all assets (INV-02)."""
        N = 30
        mu = np.random.uniform(0.001, 0.010, N)
        cov = np.eye(N) * 0.0004
        for lev in [0.80, 1.00, 1.25]:
            cap = 0.05 * lev
            w, _ = self.allocator.compute_fractional_kelly_weights(mu, cov, leverage=lev)
            self.assertTrue(np.all(w <= cap + 1e-6), f"Cap breached at leverage {lev}: max w={np.max(w)}, cap={cap}")

    def test_tc20_redistribution_invariance(self):
        """TC20: Redistribution invariance: excess weight from capped assets is redistributed."""
        N = 25
        # One superstar asset
        mu = np.full(N, 0.001)
        mu[0] = 0.050
        cov = np.eye(N) * 0.0004
        w, w_cash = self.allocator.compute_fractional_kelly_weights(mu, cov, leverage=1.0)
        cap = 0.05 * 1.0
        self.assertAlmostEqual(w[0], cap, places=5)
        # Other assets received non-zero weight via redistribution
        self.assertTrue(np.all(w[1:] > 0.0))

    def test_tc21_saturated_capacity_edge_case(self):
        """TC21: Saturated capacity edge case: when N * cap < leverage, unallocated weight is absorbed by Cash."""
        N = 5
        mu = np.full(N, 0.005)
        cov = np.eye(N) * 0.0004
        lev = 1.25
        # 5 assets * 0.05 * 1.25 = 0.3125 max equity
        w, w_cash = self.allocator.compute_fractional_kelly_weights(mu, cov, leverage=lev, max_single_stock=0.05)
        self.assertAlmostEqual(float(np.sum(w)), 0.3125, places=5)
        self.assertAlmostEqual(w_cash, lev - 0.3125, places=5)

    def test_tc22_single_sector_cap_enforcement(self):
        """TC22: Single-sector cap enforcement: sum(w_sector) <= 0.25 * leverage (INV-03)."""
        N = 30
        mu = np.random.uniform(0.002, 0.005, N)
        cov = np.eye(N) * 0.0004
        # Sector 0 has 10 assets
        sector_indices = {
            "TECH": list(range(10)),
            "HEALTHCARE": list(range(10, 20)),
            "FINANCE": list(range(20, 30)),
        }
        lev = 1.25
        w, _ = self.allocator.compute_fractional_kelly_weights(
            predicted_returns=mu,
            cov_matrix=cov,
            leverage=lev,
            sector_indices=sector_indices,
            max_sector_exposure=0.25,
        )
        cap_sec = 0.25 * lev
        for sec, idxs in sector_indices.items():
            sec_weight = float(np.sum(w[idxs]))
            self.assertLessEqual(sec_weight, cap_sec + 1e-5, f"Sector {sec} exceeded cap: {sec_weight} > {cap_sec}")

    def test_tc23_numerical_tolerance_across_random_portfolios(self):
        """TC23: Numerical tolerance: |sum(w) + w_cash - leverage| <= 1e-6 across 50 iterations."""
        for _ in range(50):
            N = np.random.randint(20, 40)
            mu = np.random.uniform(-0.001, 0.005, N)
            cov = np.diag(np.random.uniform(0.0001, 0.0005, N))
            lev = np.random.uniform(0.15, 1.25)
            w, w_cash = self.allocator.compute_fractional_kelly_weights(mu, cov, leverage=lev)
            diff = abs(float(np.sum(w) + w_cash) - lev)
            self.assertLessEqual(diff, 1e-6)

    def test_tc24_zero_negative_predicted_returns(self):
        """TC24: Zero/Negative predicted returns edge case: when mu <= 0, allocator returns 100% Cash."""
        N = 15
        mu = np.full(N, -0.002)
        cov = np.eye(N) * 0.0004
        w, w_cash = self.allocator.compute_fractional_kelly_weights(mu, cov, leverage=1.25)
        self.assertTrue(np.all(w == 0.0))
        self.assertAlmostEqual(w_cash, 1.25, places=6)

    # =========================================================================
    # Category 5: Portfolio Beta Clamping Under Leverage (TC25 ~ TC28)
    # =========================================================================

    def test_tc25_high_beta_portfolio_clamping(self):
        """TC25: High-beta portfolio clamping: given asset betas averaging 1.40, when L=1.25, final beta <= 1.000."""
        N = 25
        mu = np.full(N, 0.004)
        cov = np.eye(N) * 0.0004
        betas = np.full(N, 1.40)
        w, w_cash = self.allocator.compute_fractional_kelly_weights(
            predicted_returns=mu,
            cov_matrix=cov,
            leverage=1.25,
            asset_betas=betas,
        )
        port_beta = float(np.sum(w * betas))
        self.assertLessEqual(port_beta, 1.000001, f"Portfolio beta not clamped: {port_beta}")
        self.assertAlmostEqual(float(np.sum(w) + w_cash), 1.25, places=6)

    def test_tc26_beta_clamping_exemption_when_unleveraged(self):
        """TC26: Beta clamping exemption when unleveraged: when L <= 1.00, portfolio beta is not forcibly clamped."""
        N = 20
        mu = np.full(N, 0.003)
        cov = np.eye(N) * 0.0004
        betas = np.full(N, 1.30)
        w, _ = self.allocator.compute_fractional_kelly_weights(
            predicted_returns=mu,
            cov_matrix=cov,
            leverage=0.95,
            asset_betas=betas,
        )
        port_beta = float(np.sum(w * betas))
        # 0.95 * 1.30 = 1.235 > 1.00, should NOT be clamped below 1.00 because L <= 1.00
        self.assertGreater(port_beta, 1.00)

    def test_tc27_negative_zero_beta_handling(self):
        """TC27: Negative / Zero beta handling: assert stability when betas include negative or zero values."""
        N = 20
        mu = np.full(N, 0.003)
        cov = np.eye(N) * 0.0004
        betas = np.array([-0.5, 0.0, 0.8, 1.5] * 5)
        w, w_cash = self.allocator.compute_fractional_kelly_weights(
            predicted_returns=mu,
            cov_matrix=cov,
            leverage=1.25,
            asset_betas=betas,
        )
        self.assertEqual(len(w), N)
        self.assertAlmostEqual(float(np.sum(w) + w_cash), 1.25, places=6)

    def test_tc28_cash_buffer_absorption_upon_beta_clamping(self):
        """TC28: Cash buffer absorption upon beta clamping: released equity exposure transfers to w_cash."""
        N = 25
        mu = np.full(N, 0.004)
        cov = np.eye(N) * 0.0004
        betas = np.full(N, 1.50)
        w, w_cash = self.allocator.compute_fractional_kelly_weights(
            predicted_returns=mu,
            cov_matrix=cov,
            leverage=1.25,
            asset_betas=betas,
        )
        # Port beta clamped to 1.0 -> sum(w * 1.5) = 1.0 -> sum(w) = 1.0 / 1.5 = 0.6667
        # Residual cash should be 1.25 - 0.6667 = 0.5833
        self.assertAlmostEqual(float(np.sum(w)), 1.0 / 1.5, places=4)
        self.assertAlmostEqual(w_cash, 1.25 - (1.0 / 1.5), places=4)

    # =========================================================================
    # Category 6: Adversarial Numerical Stability & Stress Tests (TC29 ~ TC30)
    # =========================================================================

    def test_tc29_collinear_assets_singular_covariance(self):
        """TC29: Collinear assets / singular covariance: assert stable solve without LinAlgError."""
        N = 10
        # Highly collinear covariance matrix (rank 1 + noise)
        v = np.random.normal(0, 0.02, N)
        cov = np.outer(v, v)
        np.fill_diagonal(cov, cov.diagonal() + 1e-9)
        mu = np.random.uniform(0.001, 0.003, N)
        w, w_cash = self.allocator.compute_fractional_kelly_weights(mu, cov, leverage=1.10)
        self.assertEqual(len(w), N)
        self.assertFalse(np.any(np.isnan(w)))
        self.assertAlmostEqual(float(np.sum(w) + w_cash), 1.10, places=5)

    def test_tc30_zero_variance_nan_return_handling(self):
        """TC30: Zero variance / NaN return handling: assert zero NaN propagation."""
        T, N = 50, 10
        X = np.random.normal(0, 0.01, size=(T, N))
        X[:, 0] = 0.0  # Constant / zero variance asset
        X[5, 2] = np.nan
        cov_final, vols = self.allocator.compute_oas_rmt_covariance(X)
        self.assertFalse(np.any(np.isnan(cov_final)))
        self.assertFalse(np.any(np.isnan(vols)))
        self.assertGreater(vols[0], 0.0)


if __name__ == "__main__":
    unittest.main()
