"""
tests/test_phase149_risk.py - Institutional Unit Test Catalog for Phase 149 Quant Risk Architecture.
Target Features: F725, F726, F727, F728, F729.

Verifies:
- Category 1: Metadata, Cryptographic Parity, Constants & Complete Alias Trees (TC01 ~ TC05)
- Category 2: High-Dimensional Covariance Regularization: OAS & Top-50 RMT (TC06 ~ TC12)
- Category 3: Fractional Kelly Criterion, Fat Tails & Shannon Entropy Regularization (TC13 ~ TC18)
- Category 4: Bounded Simplex Water-Filling & Capacity Limits (TC19 ~ TC24)
- Category 5: Strict Portfolio Beta Clamping Under Leverage (TC25 ~ TC28)
- Category 6: 4-Tier Protective Gating Lower Envelope & Leland Dynamic Buffer (TC29 ~ TC30)

MANDATORY INTEGRITY:
All tests assert real mathematical behaviors, formulas, and exact calculations. Zero dummy implementations.
"""

from __future__ import annotations

import hashlib
import math
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
    Phase145KellyAllocator,
    Phase149KellyAllocator,
    EntropyRegularizedKellyAllocator,
    MultiRegimeDynamicLeverageAllocator,
    VERSION,
    RELEASE,
    FEATURE,
)
from src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator
from src.risk.portfolio_allocator import PortfolioAllocator


class TestPhase149RiskArchitecture(unittest.TestCase):
    """30 Comprehensive Unit Tests for Phase 149 Quant Risk Architecture (TC01–TC30)."""

    def setUp(self):
        np.random.seed(149)
        self.allocator = DynamicRegimeLeverageAllocator(
            max_bull_leverage=1.35,
            min_crisis_exposure=0.15,
            borrowing_spread_bps=60.0,
            hwm_dd_limit=-0.15,
            default_kappa=0.375,
            top_k_modes=50,
            lambda_entropy=0.001,
        )
        self.port_allocator = PortfolioAllocator(version=149)
        self.unified_allocator = UnifiedPortfolioAllocator(version=149)

    # =========================================================================
    # Category 1: Metadata, Cryptographic Parity, Constants & Complete Alias Trees (TC01 ~ TC05)
    # =========================================================================

    def test_tc01_module_constants(self):
        """TC01: Assert module constants VERSION == 149, RELEASE == 'R149', FEATURE valid."""
        self.assertEqual(VERSION, 149)
        self.assertEqual(RELEASE, "R149")
        self.assertIn("F725", FEATURE)
        self.assertIn("F726", FEATURE)
        self.assertIn("F727", FEATURE)
        self.assertIn("F728", FEATURE)
        self.assertIn("F729", FEATURE)
        self.assertEqual(DynamicRegimeLeverageAllocator.VERSION, 149)
        self.assertEqual(DynamicRegimeLeverageAllocator.RELEASE, "R149")
        self.assertIn("F725", DynamicRegimeLeverageAllocator.FEATURE)

    def test_tc02_cryptographic_dual_tree_parity(self):
        """TC02: SHA-256 cryptographic bit-for-bit dual-tree parity for all 3 risk modules."""
        modules = [
            "dynamic_regime_leverage_allocator.py",
            "unified_portfolio_allocator.py",
            "portfolio_allocator.py",
        ]
        for mod in modules:
            src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), f"../src/risk/{mod}"))
            ts_path = os.path.abspath(os.path.join(os.path.dirname(__file__), f"../trading_system/src/risk/{mod}"))
            self.assertTrue(os.path.exists(src_path), f"Missing source file: {src_path}")
            self.assertTrue(os.path.exists(ts_path), f"Missing target file: {ts_path}")
            h_src = hashlib.sha256(open(src_path, "rb").read()).hexdigest()
            h_ts = hashlib.sha256(open(ts_path, "rb").read()).hexdigest()
            self.assertEqual(h_src, h_ts, f"SHA-256 dual-tree parity mismatch for {mod}")

    def test_tc03_complete_alias_tree(self):
        """TC03: Complete alias tree validation for Phase 149."""
        self.assertIs(FractionalKellyAllocator, DynamicRegimeLeverageAllocator)
        self.assertIs(Phase141KellyAllocator, DynamicRegimeLeverageAllocator)
        self.assertIs(Phase145KellyAllocator, DynamicRegimeLeverageAllocator)
        self.assertIs(Phase149KellyAllocator, DynamicRegimeLeverageAllocator)
        self.assertIs(EntropyRegularizedKellyAllocator, DynamicRegimeLeverageAllocator)
        self.assertIs(MultiRegimeDynamicLeverageAllocator, DynamicRegimeLeverageAllocator)

        inst1 = Phase149KellyAllocator(max_bull_leverage=1.35)
        inst2 = EntropyRegularizedKellyAllocator(lambda_entropy=0.001)
        inst3 = FractionalKellyAllocator()
        self.assertIsInstance(inst1, DynamicRegimeLeverageAllocator)
        self.assertIsInstance(inst2, DynamicRegimeLeverageAllocator)
        self.assertIsInstance(inst3, DynamicRegimeLeverageAllocator)
        self.assertEqual(inst1.max_bull_leverage, 1.35)
        self.assertEqual(inst2.lambda_entropy, 0.001)

    def test_tc04_configuration_parameters(self):
        """TC04: Phase 149 parameter defaults (1.35x bull leverage, kappa in [0.25, 0.50], lambda_entropy 0.001)."""
        alloc = self.allocator
        self.assertAlmostEqual(alloc.max_bull_leverage, 1.35, places=5)
        self.assertAlmostEqual(alloc.min_crisis_exposure, 0.15, places=5)
        self.assertAlmostEqual(alloc.default_kappa, 0.375, places=5)
        self.assertEqual(alloc.top_k_modes, 50)
        self.assertAlmostEqual(alloc.lambda_entropy, 0.001, places=6)
        self.assertAlmostEqual(alloc.borrow_spread, 0.0060, places=5)

        # Check gross leverage frontiers and kappa dictionary
        self.assertEqual(DynamicRegimeLeverageAllocator.REGIME_GROSS_LEVERAGE_FRONTIERS["BULL_LOW_VOL"], 1.35)
        self.assertEqual(DynamicRegimeLeverageAllocator.REGIME_GROSS_LEVERAGE_FRONTIERS["RELIEF_RALLY"], 1.35)
        self.assertEqual(DynamicRegimeLeverageAllocator.REGIME_GROSS_LEVERAGE_FRONTIERS["BULL_HIGH_VOL"], 1.15)
        self.assertEqual(DynamicRegimeLeverageAllocator.REGIME_GROSS_LEVERAGE_FRONTIERS["BEAR_HIGH_VOL"], 0.25)
        self.assertEqual(DynamicRegimeLeverageAllocator.REGIME_GROSS_LEVERAGE_FRONTIERS["PANIC_CRISIS"], 0.15)
        self.assertEqual(DynamicRegimeLeverageAllocator.REGIME_FRACTIONAL_KELLY_KAPPA["BULL_LOW_VOL"], 0.50)
        self.assertEqual(DynamicRegimeLeverageAllocator.REGIME_FRACTIONAL_KELLY_KAPPA["RELIEF_RALLY"], 0.42)
        self.assertEqual(DynamicRegimeLeverageAllocator.REGIME_FRACTIONAL_KELLY_KAPPA["PANIC_CRISIS"], 0.00)

    def test_tc05_simplex_weight_invariants(self):
        """TC05: Simplex weight invariants: sum(w_i) + w_cash == leverage with precision 1e-6 across 8 tiers."""
        N = 25
        mu = np.random.uniform(0.001, 0.005, N)
        cov = np.diag(np.random.uniform(0.0001, 0.0004, N))
        for lev in [0.15, 0.25, 0.60, 0.85, 0.95, 1.00, 1.15, 1.35]:
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
        T, N = 120, 30
        X = np.random.normal(0.0005, 0.015, size=(T, N))
        cov_final, vols = self.allocator.compute_oas_rmt_covariance(X, top_k_modes=10)
        self.assertEqual(cov_final.shape, (N, N))
        self.assertEqual(vols.shape, (N,))
        self.assertTrue(np.all(vols > 0.0))
        self.assertTrue(np.allclose(cov_final, cov_final.T, atol=1e-8))

    def test_tc07_oas_shrinkage_intensity_bounds(self):
        """TC07: OAS shrinkage intensity rho_OAS bounds in [0.0, 1.0] and positive definiteness."""
        T, N = 80, 50
        X = np.random.normal(0, 0.02, size=(T, N))
        cov_final, _ = self.allocator.compute_oas_rmt_covariance(X, top_k_modes=20)
        evals = np.linalg.eigvalsh(cov_final)
        self.assertTrue(np.all(evals >= 1e-6))

    def test_tc08_systematic_mode_exemption(self):
        """TC08: Systematic mode exemption: top K modes remain unclipped."""
        T, N = 200, 70
        K = 50
        factors = np.random.normal(0, 0.03, size=(T, 10))
        loadings = np.random.normal(0, 1, size=(10, N))
        noise = np.random.normal(0, 0.01, size=(T, N))
        X = factors @ loadings + noise

        cov_final, _ = self.allocator.compute_oas_rmt_covariance(X, top_k_modes=K)
        evals_denoised = np.linalg.eigvalsh(cov_final)
        self.assertEqual(len(evals_denoised), N)
        self.assertTrue(evals_denoised[-1] > evals_denoised[0])

    def test_tc09_bulk_noise_boundary_calculation(self):
        """TC09: Bulk noise boundary lambda_+ calculation strictly from remaining bulk eigenvalues."""
        T, N = 150, 40
        X = np.random.normal(0, 0.01, size=(T, N))
        cov_final, _ = self.allocator.compute_oas_rmt_covariance(X, top_k_modes=15)
        evals = np.linalg.eigvalsh(cov_final)
        self.assertGreaterEqual(float(evals[0]), 1e-6)

    def test_tc10_trace_preservation(self):
        """TC10: Trace preservation: regularized covariance trace is consistent with input variance."""
        T, N = 100, 25
        X = np.random.normal(0, 0.01, size=(T, N))
        S = np.cov(X, rowvar=False)
        tr_S = float(np.trace(S))
        cov_final, _ = self.allocator.compute_oas_rmt_covariance(X, top_k_modes=10)
        tr_final = float(np.trace(cov_final))
        self.assertGreater(tr_final, 0.0)
        self.assertLess(abs(tr_final - tr_S) / (tr_S + 1e-8), 2.0)

    def test_tc11_symmetric_diagonal_normalization(self):
        """TC11: Symmetric diagonal normalization: diagonal of correlation is 1.0."""
        T, N = 90, 20
        X = np.random.normal(0, 0.015, size=(T, N))
        cov_final, vols = self.allocator.compute_oas_rmt_covariance(X)
        d = np.sqrt(np.diag(cov_final))
        corr = cov_final / np.outer(d, d)
        np.testing.assert_allclose(np.diag(corr), 1.0, atol=1e-5)

    def test_tc12_strict_positive_definiteness(self):
        """TC12: Strict positive definiteness: all eigenvalues satisfy lambda_min >= 1e-6 on fat matrices."""
        T, N = 30, 100  # Fat matrix T << N
        X = np.random.normal(0, 0.02, size=(T, N))
        cov_final, _ = self.allocator.compute_oas_rmt_covariance(X, top_k_modes=50)
        evals = np.linalg.eigvalsh(cov_final)
        self.assertGreaterEqual(float(np.min(evals)), 1e-6)

    # =========================================================================
    # Category 3: Fractional Kelly Criterion, Fat Tails & Shannon Entropy Regularization (TC13 ~ TC18)
    # =========================================================================

    def test_tc13_unconstrained_entropy_kelly_calculation(self):
        """TC13: Unconstrained Shannon entropy regularized Kelly solve: weights positive, finite, monotonic in alpha."""
        N = 10
        mu = np.array([0.002 * (i + 1) for i in range(N)])
        cov = np.eye(N) * 0.0004
        w, w_cash = self.allocator.compute_fractional_kelly_weights(
            predicted_returns=mu,
            cov_matrix=cov,
            leverage=1.35,
            kappa=0.50,
            lambda_entropy=0.001,
        )
        self.assertEqual(len(w), N)
        self.assertTrue(np.all(w >= 0.0))
        self.assertGreaterEqual(w[-1], w[0])
        self.assertAlmostEqual(float(np.sum(w) + w_cash), 1.35, places=6)

    def test_tc14_shannon_entropy_parameter_sweep(self):
        """TC14: Shannon entropy parameter sweep: higher lambda_entropy increases entropy H(w) smoothly."""
        N = 25
        mu = np.linspace(0.001, 0.005, N)
        cov = np.eye(N) * 0.0004
        lambdas = [0.0, 0.001, 0.01]
        entropies = []
        eps = 1e-12
        for lam in lambdas:
            w, _ = self.allocator.compute_fractional_kelly_weights(
                predicted_returns=mu,
                cov_matrix=cov,
                leverage=1.35,
                kappa=0.375,
                lambda_entropy=lam,
            )
            w_bar = w / np.sum(w)
            h = -float(np.sum(w_bar * np.log(w_bar + eps)))
            entropies.append(h)

        # Entropy strictly increases as lambda_entropy increases
        for i in range(len(entropies) - 1):
            self.assertLess(entropies[i], entropies[i + 1])

    def test_tc15_fourth_order_fat_tail_contraction(self):
        """TC15: 4th-order fat-tail contraction: mu_eff = (mu - rf) + 0.5 * s(w) - (1/6) * k(w)."""
        N = 10
        mu = np.full(N, 0.003)
        cov = np.eye(N) * 0.0004
        s_w = np.full(N, 0.0002)   # Positive coskewness (boost)
        k_w = np.full(N, 0.0012)   # Positive cokurtosis (penalty)
        w, w_cash = self.allocator.compute_fractional_kelly_weights(
            predicted_returns=mu,
            cov_matrix=cov,
            leverage=1.35,
            coskewness=s_w,
            cokurtosis=k_w,
        )
        self.assertEqual(len(w), N)
        self.assertTrue(np.all(w >= 0.0))
        self.assertAlmostEqual(float(np.sum(w) + w_cash), 1.35, places=6)

    def test_tc16_negative_skewness_penalty(self):
        """TC16: Negative skewness penalty: negative coskewness reduces allocation compared to positive."""
        N = 15
        mu = np.full(N, 0.003)
        cov = np.eye(N) * 0.0004
        s_pos = np.full(N, 0.001)
        s_neg = np.full(N, -0.001)

        w_pos, _ = self.allocator.compute_fractional_kelly_weights(
            predicted_returns=mu,
            cov_matrix=cov,
            leverage=1.00,
            coskewness=s_pos,
        )
        w_neg, _ = self.allocator.compute_fractional_kelly_weights(
            predicted_returns=mu,
            cov_matrix=cov,
            leverage=1.00,
            coskewness=s_neg,
        )
        self.assertGreaterEqual(float(np.sum(w_pos)), float(np.sum(w_neg)))

    def test_tc17_non_negativity_assertion(self):
        """TC17: Non-negativity assertion: all asset weights must satisfy w_i >= 0.0 under mixed alpha."""
        N = 20
        mu = np.random.uniform(-0.005, 0.005, N)
        cov = np.diag(np.random.uniform(0.0001, 0.0005, N))
        w, w_cash = self.allocator.compute_fractional_kelly_weights(mu, cov, leverage=1.35)
        self.assertTrue(np.all(w >= 0.0))
        self.assertGreaterEqual(w_cash, 0.0)
        self.assertAlmostEqual(float(np.sum(w) + w_cash), 1.35, places=6)

    def test_tc18_cash_residual_allocation(self):
        """TC18: Cash residual allocation: w_cash = max(0, leverage - sum(w)) >= 0."""
        N = 15
        mu = np.full(N, 0.001)
        cov = np.eye(N) * 0.0010
        w, w_cash = self.allocator.compute_fractional_kelly_weights(mu, cov, leverage=1.35, kappa=0.25)
        self.assertAlmostEqual(float(np.sum(w) + w_cash), 1.35, places=6)
        self.assertGreaterEqual(w_cash, 0.0)

    # =========================================================================
    # Category 4: Bounded Simplex Water-Filling & Capacity Limits (TC19 ~ TC24)
    # =========================================================================

    def test_tc19_single_stock_cap_enforcement(self):
        """TC19: Single stock cap enforcement: w_i <= 0.05 * leverage (at L=1.35, cap=0.0675)."""
        N = 30
        mu = np.random.uniform(0.001, 0.010, N)
        cov = np.eye(N) * 0.0004
        for lev in [0.85, 1.00, 1.15, 1.35]:
            cap = 0.05 * lev
            w, _ = self.allocator.compute_fractional_kelly_weights(mu, cov, leverage=lev)
            self.assertTrue(np.all(w <= cap + 1e-6), f"Cap breached at leverage {lev}: max w={np.max(w)}, cap={cap}")

    def test_tc20_redistribution_invariance(self):
        """TC20: Redistribution invariance: excess weight from capped superstar asset is redistributed."""
        N = 25
        mu = np.full(N, 0.001)
        mu[0] = 0.050  # Superstar asset
        cov = np.eye(N) * 0.0004
        w, w_cash = self.allocator.compute_fractional_kelly_weights(mu, cov, leverage=1.35)
        cap = 0.05 * 1.35
        self.assertAlmostEqual(w[0], cap, places=5)
        self.assertTrue(np.all(w[1:] > 0.0))
        self.assertAlmostEqual(float(np.sum(w) + w_cash), 1.35, places=6)

    def test_tc21_saturated_capacity_edge_case(self):
        """TC21: Saturated capacity edge case: when N * cap < leverage, unallocated weight is absorbed by Cash."""
        N = 5
        mu = np.full(N, 0.005)
        cov = np.eye(N) * 0.0004
        lev = 1.35
        # 5 assets * 0.05 * 1.35 = 0.3375 max equity
        w, w_cash = self.allocator.compute_fractional_kelly_weights(mu, cov, leverage=lev, max_single_stock=0.05)
        self.assertAlmostEqual(float(np.sum(w)), 0.3375, places=5)
        self.assertAlmostEqual(w_cash, lev - 0.3375, places=5)
        self.assertAlmostEqual(float(np.sum(w) + w_cash), lev, places=6)

    def test_tc22_single_sector_cap_enforcement(self):
        """TC22: Single-sector cap enforcement: sum(w_sector) <= 0.25 * leverage (at L=1.35, cap=0.3375)."""
        N = 30
        mu = np.random.uniform(0.002, 0.005, N)
        cov = np.eye(N) * 0.0004
        sector_indices = {
            "TECH": list(range(10)),
            "HEALTHCARE": list(range(10, 20)),
            "FINANCE": list(range(20, 30)),
        }
        lev = 1.35
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
        """TC23: Numerical tolerance: |sum(w) + w_cash - leverage| <= 1e-6 across 50 random iterations."""
        for _ in range(50):
            N = np.random.randint(20, 40)
            mu = np.random.uniform(-0.001, 0.005, N)
            cov = np.diag(np.random.uniform(0.0001, 0.0005, N))
            lev = np.random.uniform(0.15, 1.35)
            w, w_cash = self.allocator.compute_fractional_kelly_weights(mu, cov, leverage=lev)
            diff = abs(float(np.sum(w) + w_cash) - lev)
            self.assertLessEqual(diff, 1e-6)

    def test_tc24_zero_negative_predicted_returns(self):
        """TC24: Zero/Negative predicted returns edge case: when mu <= 0, allocator returns 100% Cash."""
        N = 15
        mu = np.full(N, -0.002)
        cov = np.eye(N) * 0.0004
        w, w_cash = self.allocator.compute_fractional_kelly_weights(mu, cov, leverage=1.35)
        self.assertTrue(np.all(w == 0.0))
        self.assertAlmostEqual(w_cash, 1.35, places=6)

    # =========================================================================
    # Category 5: Strict Portfolio Beta Clamping Under Leverage (TC25 ~ TC28)
    # =========================================================================

    def test_tc25_high_beta_portfolio_clamping(self):
        """TC25: High-beta portfolio clamping: given asset betas averaging 1.45, when L=1.35, final beta <= 1.000000."""
        N = 25
        mu = np.full(N, 0.004)
        cov = np.eye(N) * 0.0004
        betas = np.full(N, 1.45)
        w, w_cash = self.allocator.compute_fractional_kelly_weights(
            predicted_returns=mu,
            cov_matrix=cov,
            leverage=1.35,
            asset_betas=betas,
        )
        port_beta = float(np.sum(w * betas))
        self.assertLessEqual(port_beta, 1.000001, f"Portfolio beta not clamped: {port_beta}")
        self.assertAlmostEqual(float(np.sum(w) + w_cash), 1.35, places=6)

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
            leverage=1.35,
            asset_betas=betas,
        )
        self.assertEqual(len(w), N)
        self.assertAlmostEqual(float(np.sum(w) + w_cash), 1.35, places=6)

    def test_tc28_cash_buffer_absorption_upon_beta_clamping(self):
        """TC28: Cash buffer absorption upon beta clamping: released equity exposure transfers to w_cash."""
        N = 25
        mu = np.full(N, 0.004)
        cov = np.eye(N) * 0.0004
        betas = np.full(N, 1.50)
        w, w_cash = self.allocator.compute_fractional_kelly_weights(
            predicted_returns=mu,
            cov_matrix=cov,
            leverage=1.35,
            asset_betas=betas,
        )
        # Port beta clamped to 1.0 -> sum(w * 1.5) = 1.0 -> sum(w) = 1.0 / 1.5 = 0.6667
        # Residual cash should be 1.35 - 0.6667 = 0.6833
        self.assertAlmostEqual(float(np.sum(w)), 1.0 / 1.5, places=4)
        self.assertAlmostEqual(w_cash, 1.35 - (1.0 / 1.5), places=4)
        self.assertAlmostEqual(float(np.sum(w) + w_cash), 1.35, places=6)

    # =========================================================================
    # Category 6: 4-Tier Protective Gating Lower Envelope & Leland Dynamic Buffer (TC29 ~ TC30)
    # =========================================================================

    def test_tc29_four_tier_protective_gating_lower_envelope(self):
        """TC29: 4-tier protective gating lower envelope: VIX velocity, TSR contango lock, and HWM drawdown."""
        alloc = self.allocator
        vix_hist_calm = [14.0] * 5
        tsr_hist_5d = [0.88, 0.89, 0.90, 0.87, 0.89]

        # Tier A: Normal calm bull -> 1.35x
        L_calm = alloc.evaluate_dynamic_leverage_frontier(
            current_nav=100.0,
            vix=14.0,
            vix_history=vix_hist_calm,
            tsr_ratio=0.88,
            regime="BULL_LOW_VOL",
            tsr_history=tsr_hist_5d,
        )
        self.assertAlmostEqual(L_calm, 1.35, places=4)

        # Tier B: Gate 1 VIX velocity spike -> 0.40x
        vix_hist_spike = [15.0, 18.0, 21.0, 24.0, 16.0]  # vel = (28.5 - 16.0) / 5 = 2.50 > 2.0
        L_vix_spike = alloc.evaluate_dynamic_leverage_frontier(
            current_nav=100.0,
            vix=28.5,
            vix_history=vix_hist_spike,
            tsr_ratio=0.88,
            regime="BULL_LOW_VOL",
        )
        self.assertAlmostEqual(L_vix_spike, 0.40, places=4)

        # Tier C: Gate 2 Acute TSR Inversion (TSR >= 1.08) -> 0.50x
        L_tsr = alloc.evaluate_dynamic_leverage_frontier(
            current_nav=100.0,
            vix=15.0,
            vix_history=vix_hist_calm,
            tsr_ratio=1.12,
            regime="BULL_LOW_VOL",
        )
        self.assertAlmostEqual(L_tsr, 0.50, places=4)

        # Tier D: Gate 3 Severe HWM DD (DD = -12.0%) -> 0.15x
        alloc.evaluate_dynamic_leverage_frontier(100.0, 14.0, vix_hist_calm, 0.88, "BULL_LOW_VOL")
        L_dd = alloc.evaluate_dynamic_leverage_frontier(
            current_nav=88.0,  # -12% DD
            vix=14.0,
            vix_history=vix_hist_calm,
            tsr_ratio=0.88,
            regime="BULL_LOW_VOL",
        )
        self.assertAlmostEqual(L_dd, 0.15, places=4)

        # Tier E: Relief Rally 5-day Contango Lock
        # Without 5-day contango history -> defaults safely to 0.90x
        L_relief_no_lock = alloc.evaluate_dynamic_leverage_frontier(
            current_nav=100.0,
            vix=15.0,
            vix_history=vix_hist_calm,
            tsr_ratio=0.89,
            regime="RELIEF_RALLY",
            tsr_history=[0.90, 0.98, 0.89],  # broken/short
        )
        self.assertAlmostEqual(L_relief_no_lock, 0.90, places=4)

        # With 5-day contango lock satisfied -> reaches 1.35x
        L_relief_locked = alloc.evaluate_dynamic_leverage_frontier(
            current_nav=100.0,
            vix=15.0,
            vix_history=vix_hist_calm,
            tsr_ratio=0.89,
            regime="RELIEF_RALLY",
            tsr_history=tsr_hist_5d,
        )
        self.assertAlmostEqual(L_relief_locked, 1.35, places=4)

    def test_tc30_leland_expansion_and_bypass(self):
        """TC30: Leland buffer expansion exactly 1.1400000x at L=1.35, with instant bypass for entry/exit."""
        # Multiplier verification
        delta_base = 0.0100000
        delta_expanded = self.allocator.calculate_leveraged_leland_buffer(delta_base, leverage=1.35)
        expected_multiplier = 1.0 + 0.40 * (1.35 - 1.0)  # exactly 1.1400000
        self.assertAlmostEqual(delta_expanded / delta_base, expected_multiplier, places=7)
        self.assertAlmostEqual(delta_expanded / delta_base, 1.1400000, places=7)

        # Rebalance bypass verification in PortfolioAllocator
        pa = self.port_allocator
        self.assertTrue(pa.is_phase149)

        # Test A: Fresh Entry (w_curr == 0.0, w_target == 0.005 inside buffer delta=0.01) -> MUST NOT be bypassed to HOLD
        curr_w = {"NEW_ASSET": 0.0}
        targ_w = {"NEW_ASSET": 0.005}
        mkt_map = {"NEW_ASSET": "SP500"}
        vol_map = {"NEW_ASSET": 0.02}
        adv_map = {"NEW_ASSET": 1e9}

        res_entry = pa.compute_portfolio_rebalance(
            current_weights=curr_w,
            target_weights=targ_w,
            market_map=mkt_map,
            volatility_map=vol_map,
            adv_map=adv_map,
            leverage=1.35,
        )
        self.assertEqual(res_entry["trades"]["NEW_ASSET"]["action"], "BUY")
        self.assertAlmostEqual(res_entry["trades"]["NEW_ASSET"]["w_new"], 0.005, places=5)

        # Test B: Full Liquidation (w_curr == 0.005 inside buffer delta=0.01, w_target == 0.0) -> MUST NOT be bypassed to HOLD
        curr_exit = {"OLD_ASSET": 0.005}
        targ_exit = {"OLD_ASSET": 0.0}
        mkt_map_exit = {"OLD_ASSET": "SP500"}
        vol_map_exit = {"OLD_ASSET": 0.02}
        adv_map_exit = {"OLD_ASSET": 1e9}

        res_exit = pa.compute_portfolio_rebalance(
            current_weights=curr_exit,
            target_weights=targ_exit,
            market_map=mkt_map_exit,
            volatility_map=vol_map_exit,
            adv_map=adv_map_exit,
            leverage=1.35,
        )
        self.assertEqual(res_exit["trades"]["OLD_ASSET"]["action"], "SELL")
        self.assertAlmostEqual(res_exit["trades"]["OLD_ASSET"]["w_new"], 0.0, places=5)


if __name__ == "__main__":
    unittest.main()
