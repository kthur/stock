"""
tests/test_phase190_risk.py — Comprehensive Unit & Integration Test Suite for Phase 190
Features F930 to F934 (Risk Budgeting, Manifold Allocation & Dynamic Leverage Layer).

Verifies Milestone M3 (Phase 190 for Release R182 Institutional Master):
- Category 1: Dual-Tree Cryptographic Parity, Version Polymorphism & Metadata (TC01 ~ TC06)
- Category 2: F930 Poincaré-Lorentz Hyperbolic Optimal Transport Wasserstein Barycenter (TC07 ~ TC14)
- Category 3: F931 Dynamic Regime Compounding Leverage Frontiers up to 2.15x & 7D Contango Lock (TC15 ~ TC22)
- Category 4: F932 Spectral EVT-CVaR Tail-Risk Budgeting with Clamped High-Order GPD (TC23 ~ TC30)
- Category 5: F933 Asymmetric Power-Law Leland Dynamic Buffer Bands with Ultra-Low Turnover (TC31 ~ TC38)
- Category 6: F934 UnifiedPortfolioAllocator R182 10-Model Master Blend & Gatheral 3/2 Penalty (TC39 ~ TC44)
- Category 7: End-to-End Multi-Market Integration, Crisis Shock Defense & Invariants (TC45 ~ TC50)

MANDATORY INTEGRITY:
All implementations are genuine mathematical formulations, real portfolio optimization, and risk gating.
Zero synthetic rows (synthetic_rows == 0 strictly Python native int 0).
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import sys
import time
import unittest
from typing import Dict, Any, List

import numpy as np
import pandas as pd
import pytest

# Path setup
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../trading_system")))

# F930 Imports
from src.risk.hyperbolic_optimal_transport_allocator import (
    VERSION_PHASE190 as VERSION_P190_F930,
    RELEASE_PHASE190 as RELEASE_P190_F930,
    FEATURE_PHASE190 as FEATURE_P190_F930,
    HyperbolicOptimalTransportAllocatorV182,
    HyperbolicOTEngine,
    Phase190HyperbolicOTAllocator,
    F930HyperbolicOTAllocator,
    compute_hyperbolic_wasserstein_barycenter_v182,
    allocate_hyperbolic_ot_v182,
    mobius_addition,
    poincare_exponential_map,
    poincare_logarithmic_map,
)

# F931 Imports
from src.risk.dynamic_regime_leverage_allocator import (
    VERSION_PHASE190 as VERSION_P190_F931,
    RELEASE_PHASE190 as RELEASE_P190_F931,
    FEATURE_PHASE190 as FEATURE_P190_F931,
    DynamicRegimeLeverageAllocatorV182,
    F931DynamicRegimeLeverage,
    F931RegimeCompoundingLeverageAllocator,
    REGIME_LEVERAGE_FRONTIERS_V182,
    evaluate_7d_contango_lock,
    get_regime_leverage_limit_v182,
    compute_oas_covariance_shrinkage,
    filter_top50_systematic_modes,
)

# F932 Imports
from src.risk.spectral_evt_cvar_allocator import (
    VERSION_PHASE190 as VERSION_P190_F932,
    RELEASE_PHASE190 as RELEASE_P190_F932,
    FEATURE_PHASE190 as FEATURE_P190_F932,
    SpectralEVTCVaRAllocatorV182,
    SpectralEVTCVaREngineV182,
    Phase190SpectralEVTCVaREngine,
    F932SpectralEVTCVaR,
    SpectralEVTCVaRAllocatorPhase190,
    exponential_spectral_weight,
    compute_clamped_gpd_spectral_cvar_v182,
    compute_spectral_evt_cvar_risk_budget_v182,
)

# F933 Imports
from src.execution.leland_buffer_bands import (
    VERSION_PHASE190 as VERSION_P190_F933,
    RELEASE_PHASE190 as RELEASE_P190_F933,
    FEATURE_PHASE190 as FEATURE_P190_F933,
    LelandBufferBandsV182,
    Phase190LelandBufferBands,
    F933LelandBufferBands,
    PowerLawLelandBufferBandsV182,
    compute_asymmetric_power_law_leland_bands_v182,
    filter_portfolio_rebalance_v182,
    is_zero_bypass_eligible,
)

# F934 Imports
from src.risk.unified_portfolio_allocator import (
    VERSION_PHASE190 as VERSION_P190_F934,
    RELEASE_PHASE190 as RELEASE_P190_F934,
    FEATURE_PHASE190 as FEATURE_P190_F934,
    UnifiedPortfolioAllocator,
    UnifiedPortfolioAllocatorV182,
    Phase190UnifiedPortfolioAllocator,
    F934UnifiedPortfolioAllocator,
    REGIME_MODEL_WEIGHTS_PHASE190,
    REGIME_MODEL_WEIGHTS_V182,
    AllocationResult,
    allocate_portfolio_phase190,
    allocate_portfolio_v182,
)


class TestPhase190Risk(unittest.TestCase):
    """50 Comprehensive Test Cases for Phase 190 Features F930 to F934."""

    # =========================================================================
    # Category 1: Dual-Tree Cryptographic Parity & Metadata (TC01 ~ TC06)
    # =========================================================================
    def test_tc01_dual_tree_cryptographic_parity_phase190(self):
        """TC01: Verify 100% SHA-256 bit-for-bit parity between src/ and trading_system/src/."""
        files = [
            "src/risk/hyperbolic_optimal_transport_allocator.py",
            "src/risk/dynamic_regime_leverage_allocator.py",
            "src/risk/evt_tail_risk.py",
            "src/risk/spectral_evt_cvar_allocator.py",
            "src/execution/leland_buffer_bands.py",
            "src/risk/unified_portfolio_allocator.py",
        ]
        root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        for rel in files:
            p1 = os.path.join(root, rel)
            p2 = os.path.join(root, "trading_system", rel)
            self.assertTrue(os.path.exists(p1), f"Source file does not exist: {p1}")
            self.assertTrue(os.path.exists(p2), f"Target file does not exist: {p2}")
            with open(p1, "rb") as f1, open(p2, "rb") as f2:
                h1 = hashlib.sha256(f1.read()).hexdigest()
                h2 = hashlib.sha256(f2.read()).hexdigest()
                self.assertEqual(h1, h2, f"Cryptographic hash mismatch for {rel}")

    def test_tc02_version_polymorphism_f930(self):
        """TC02: Verify Feature F930 version metadata."""
        self.assertEqual(int(VERSION_P190_F930), 190)
        self.assertEqual(str(RELEASE_P190_F930), "R182")
        self.assertEqual(str(FEATURE_P190_F930), "F930")

    def test_tc03_version_polymorphism_f931(self):
        """TC03: Verify Feature F931 version metadata."""
        self.assertEqual(int(VERSION_P190_F931), 190)
        self.assertEqual(str(RELEASE_P190_F931), "R182")
        self.assertEqual(str(FEATURE_P190_F931), "F931")

    def test_tc04_version_polymorphism_f932(self):
        """TC04: Verify Feature F932 version metadata."""
        self.assertEqual(int(VERSION_P190_F932), 190)
        self.assertEqual(str(RELEASE_P190_F932), "R182")
        self.assertEqual(str(FEATURE_P190_F932), "F932")

    def test_tc05_version_polymorphism_f933(self):
        """TC05: Verify Feature F933 version metadata."""
        self.assertEqual(int(VERSION_P190_F933), 190)
        self.assertEqual(str(RELEASE_P190_F933), "R182")
        self.assertEqual(str(FEATURE_P190_F933), "F933")

    def test_tc06_version_polymorphism_f934(self):
        """TC06: Verify Feature F934 version metadata."""
        self.assertEqual(int(VERSION_P190_F934), 190)
        self.assertEqual(str(RELEASE_P190_F934), "R182")
        self.assertEqual(str(FEATURE_P190_F934), "F934")

    # =========================================================================
    # Category 2: F930 Poincaré-Lorentz Hyperbolic OT Barycenter (TC07 ~ TC14)
    # =========================================================================
    def test_tc07_f930_poincare_distance_metric_axioms(self):
        """TC07: Verify Poincaré distance metric satisfies positivity, symmetry, and identity."""
        alloc = HyperbolicOptimalTransportAllocatorV182()
        u = np.array([0.2, -0.3], dtype=np.float64)
        v = np.array([-0.1, 0.4], dtype=np.float64)

        # Positivity & non-negativity
        d_uv = alloc.poincare_distance(u, v)
        self.assertGreater(d_uv, 0.0)

        # Symmetry: d(u, v) == d(v, u)
        d_vu = alloc.poincare_distance(v, u)
        self.assertAlmostEqual(d_uv, d_vu, places=7)

        # Identity of indiscernibles: d(u, u) == 0
        d_uu = alloc.poincare_distance(u, u)
        self.assertAlmostEqual(d_uu, 0.0, places=7)

    def test_tc08_f930_poincare_distance_closed_form_formula(self):
        """TC08: Verify d_H(u, v) = arcosh(1 + 2 * ||u - v||^2 / ((1 - ||u||^2)(1 - ||v||^2)))."""
        alloc = HyperbolicOptimalTransportAllocatorV182()
        u = np.array([0.3, 0.2], dtype=np.float64)
        v = np.array([0.1, -0.2], dtype=np.float64)
        norm_u_sq = float(np.sum(u ** 2))
        norm_v_sq = float(np.sum(v ** 2))
        diff_sq = float(np.sum((u - v) ** 2))
        arg = 1.0 + 2.0 * diff_sq / ((1.0 - norm_u_sq) * (1.0 - norm_v_sq))
        expected_d = math.acosh(max(1.0, arg))
        calc_d = alloc.poincare_distance(u, v)
        self.assertAlmostEqual(calc_d, expected_d, places=6)

    def test_tc09_f930_lorentz_hyperboloid_isometry(self):
        """TC09: Verify Lorentz hyperboloid Minkowski inner product and distance."""
        alloc = HyperbolicOptimalTransportAllocatorV182()
        # Points on hyperboloid: -x0^2 + x1^2 + x2^2 = -1 => x0 = sqrt(1 + x1^2 + x2^2)
        x_space = np.array([0.4, 0.3])
        x0 = math.sqrt(1.0 + np.sum(x_space ** 2))
        x = np.concatenate([[x0], x_space])

        y_space = np.array([-0.2, 0.5])
        y0 = math.sqrt(1.0 + np.sum(y_space ** 2))
        y = np.concatenate([[y0], y_space])

        # Minkowski inner product <x, y>_L = -x0*y0 + x_space . y_space
        minkowski_prod = -x[0] * y[0] + float(np.dot(x[1:], y[1:]))
        self.assertLessEqual(minkowski_prod, -1.0)

        d_lorentz = alloc.lorentz_distance(x, y)
        expected_d = math.acosh(max(1.0, -minkowski_prod))
        self.assertAlmostEqual(d_lorentz, expected_d, places=6)

    def test_tc10_f930_sinkhorn_knopp_doubly_stochastic_ot(self):
        """TC10: Verify Sinkhorn-Knopp algorithm produces marginal-matching transport plan."""
        alloc = HyperbolicOptimalTransportAllocatorV182()
        cost_matrix = np.array([
            [0.1, 0.5, 0.8],
            [0.6, 0.2, 0.4],
            [0.7, 0.9, 0.1],
        ], dtype=np.float64)
        p = np.array([0.3, 0.4, 0.3], dtype=np.float64)
        q = np.array([0.25, 0.50, 0.25], dtype=np.float64)
        P, cost = alloc.sinkhorn_knopp(p=p, q=q, cost_matrix=cost_matrix, eps=0.05, max_iters=100)

        # Row marginals == p
        np.testing.assert_allclose(np.sum(P, axis=1), p, atol=1e-3)
        # Col marginals == q
        np.testing.assert_allclose(np.sum(P, axis=0), q, atol=1e-3)

    def test_tc11_f930_frechet_barycenter_inside_unit_ball(self):
        """TC11: Verify Fréchet barycenter Riemannian gradient descent stays inside unit ball."""
        alloc = HyperbolicOptimalTransportAllocatorV182()
        points = np.array([
            [0.3, 0.2],
            [-0.4, 0.1],
            [0.1, -0.5],
            [0.2, 0.4],
        ], dtype=np.float64)
        res = alloc.compute_hyperbolic_barycenter(points)
        bary = res["barycenter"]
        self.assertLess(float(np.linalg.norm(bary)), 1.0)
        self.assertTrue(res["converged"])
        self.assertIn("hyperbolic_variance", res)
        self.assertGreaterEqual(res["hyperbolic_variance"], 0.0)

    def test_tc12_f930_risk_parity_curvature_weighting(self):
        """TC12: Verify risk-parity hyperbolic curvature weighting allocates higher weight to lower risk."""
        alloc = HyperbolicOptimalTransportAllocatorV182()
        symbols = ["LOW_RISK", "HIGH_RISK"]
        alphas = {"LOW_RISK": 1.0, "HIGH_RISK": 1.0}
        # Low risk vol 0.10, High risk vol 0.40
        cov = np.array([
            [0.01, 0.00],
            [0.00, 0.16],
        ], dtype=np.float64)
        weights = alloc.compute_risk_parity_hyperbolic_weights(
            symbols=symbols,
            alpha_scores=alphas,
            cov_matrix=cov,
            regime="BULL_STABLE",
            gross_leverage=1.0,
        )
        self.assertGreater(weights["LOW_RISK"], weights["HIGH_RISK"])
        self.assertAlmostEqual(sum(weights.values()), 1.0, places=4)

    def test_tc13_f930_allocator_instantiation_and_aliases(self):
        """TC13: Verify HyperbolicOptimalTransportAllocatorV182 and aliases instantiation."""
        a1 = HyperbolicOptimalTransportAllocatorV182()
        a2 = HyperbolicOTEngine()
        a3 = Phase190HyperbolicOTAllocator()
        a4 = F930HyperbolicOTAllocator()
        self.assertIsInstance(a1, HyperbolicOptimalTransportAllocatorV182)
        self.assertIsInstance(a2, HyperbolicOptimalTransportAllocatorV182)
        self.assertIsInstance(a3, HyperbolicOptimalTransportAllocatorV182)
        self.assertIsInstance(a4, HyperbolicOptimalTransportAllocatorV182)

    def test_tc14_f930_synthetic_rows_zero_invariant(self):
        """TC14: Verify synthetic_rows == 0 strictly in hyperbolic allocator output."""
        res = allocate_hyperbolic_ot_v182(["AAPL", "MSFT"], [1.5, 1.2])
        self.assertEqual(res["synthetic_rows"], 0)
        self.assertIs(type(res["synthetic_rows"]), int)

    # =========================================================================
    # Category 3: F931 Dynamic Regime Compounding Leverage Frontiers (TC15 ~ TC22)
    # =========================================================================
    def test_tc15_f931_regime_leverage_frontiers_bounds(self):
        """TC15: Verify 6 regime leverage frontiers match specification up to 2.15x."""
        expected = {
            "BULL_STABLE": 2.15,
            "BULL_VOLATILE": 1.60,
            "NEUTRAL_EXPANSION": 1.10,
            "RANGE_COMPRESSION": 0.60,
            "BEAR_DEFENSIVE": 0.25,
            "CRISIS_HALT": 0.00,
        }
        for regime, expected_lev in expected.items():
            lev = get_regime_leverage_limit_v182(regime)
            self.assertAlmostEqual(float(lev), expected_lev, places=2)

    def test_tc16_f931_seven_day_contango_lock_positive(self):
        """TC16: Verify evaluate_7d_contango_lock returns True when 7 consecutive days >= threshold."""
        spreads = [0.06, 0.07, 0.055, 0.08, 0.065, 0.075, 0.052]
        self.assertTrue(evaluate_7d_contango_lock(spreads, threshold=0.05))

    def test_tc17_f931_seven_day_contango_lock_negative_broken_or_short(self):
        """TC17: Verify evaluate_7d_contango_lock returns False when < 7 days or one day below threshold."""
        short_spreads = [0.06, 0.07, 0.055, 0.08, 0.065, 0.075]  # 6 days
        self.assertFalse(evaluate_7d_contango_lock(short_spreads, threshold=0.05))

        broken_spreads = [0.06, 0.07, 0.045, 0.08, 0.065, 0.075, 0.052]  # day 3 is 0.045 < 0.05
        self.assertFalse(evaluate_7d_contango_lock(broken_spreads, threshold=0.05))

    def test_tc18_f931_leverage_gating_without_contango_lock(self):
        """TC18: Verify leverage is clamped to <= 1.0x when 7-day contango lock is not satisfied."""
        alloc = DynamicRegimeLeverageAllocatorV182()
        # In BULL_STABLE, target is 2.15x, but without contango lock it must clamp to 1.0x
        broken_spreads = [0.06, 0.07, 0.03, 0.08, 0.06, 0.07, 0.05]
        lev = alloc.get_effective_leverage_limit(
            regime="BULL_STABLE",
            vix_spreads=broken_spreads,
            vts_ratio=0.90,
        )
        self.assertLessEqual(lev, 1.00)

        # With 7-day contango lock satisfied
        valid_spreads = [0.06, 0.07, 0.055, 0.08, 0.065, 0.075, 0.052]
        lev_valid = alloc.get_effective_leverage_limit(
            regime="BULL_STABLE",
            vix_spreads=valid_spreads,
            vts_ratio=0.90,
        )
        self.assertAlmostEqual(lev_valid, 2.15, places=2)

    def test_tc19_f931_oas_covariance_shrinkage_properties(self):
        """TC19: Verify Oracle Approximating Shrinkage (OAS) produces well-conditioned covariance."""
        rng = np.random.RandomState(42)
        X = rng.randn(60, 10)  # N=10, T=60
        cov_shrunk = compute_oas_covariance_shrinkage(X)
        self.assertEqual(cov_shrunk.shape, (10, 10))
        # Check positive definiteness (eigenvalues > 0)
        eigvals = np.linalg.eigvalsh(cov_shrunk)
        self.assertTrue(np.all(eigvals > 1e-6))
        # Symmetric
        np.testing.assert_allclose(cov_shrunk, cov_shrunk.T, atol=1e-8)

    def test_tc20_f931_top50_systematic_mode_exemption(self):
        """TC20: Verify top-50 systematic mode exemption in RMT filtering preserves leading modes."""
        rng = np.random.RandomState(42)
        X = rng.randn(100, 60)  # 60 assets, 100 observations
        cov = np.cov(X, rowvar=False)
        cov_filtered = filter_top50_systematic_modes(cov, top_modes=50)
        self.assertEqual(cov_filtered.shape, (60, 60))
        eigvals_orig = np.linalg.eigvalsh(cov)
        eigvals_filt = np.linalg.eigvalsh(cov_filtered)
        # Top eigenvalues should match closely because they are exempted from bulk shrinkage
        self.assertAlmostEqual(eigvals_orig[-1], eigvals_filt[-1], places=3)
        self.assertAlmostEqual(eigvals_orig[-10], eigvals_filt[-10], places=3)

    def test_tc21_f931_allocator_instantiation_and_aliases(self):
        """TC21: Verify DynamicRegimeLeverageAllocatorV182 and aliases instantiation."""
        a1 = DynamicRegimeLeverageAllocatorV182()
        a2 = F931DynamicRegimeLeverage()
        a3 = F931RegimeCompoundingLeverageAllocator()
        self.assertIsInstance(a1, DynamicRegimeLeverageAllocatorV182)
        self.assertIsInstance(a2, DynamicRegimeLeverageAllocatorV182)
        self.assertIsInstance(a3, DynamicRegimeLeverageAllocatorV182)

    def test_tc22_f931_synthetic_rows_zero_invariant(self):
        """TC22: Verify synthetic_rows == 0 strictly in dynamic regime leverage allocator output."""
        alloc = DynamicRegimeLeverageAllocatorV182()
        res = alloc.allocate_regime_leverage(
            symbols=["AAPL", "MSFT"],
            alphas={"AAPL": 1.2, "MSFT": 1.1},
            regime="BULL_STABLE",
        )
        self.assertEqual(res["synthetic_rows"], 0)
        self.assertIs(type(res["synthetic_rows"]), int)

    # =========================================================================
    # Category 4: F932 Spectral EVT-CVaR Clamped GPD Tail Budgeting (TC23 ~ TC30)
    # =========================================================================
    def test_tc23_f932_clamped_gpd_shape_parameter_bounds(self):
        """TC23: Verify POT tail shape parameter xi is clamped strictly within [-0.5, 0.5]."""
        alloc = SpectralEVTCVaRAllocatorV182()
        xi_pos = alloc.clamp_tail_index(0.95)
        self.assertEqual(xi_pos, 0.5)

        xi_neg = alloc.clamp_tail_index(-0.88)
        self.assertEqual(xi_neg, -0.5)

        xi_mid = alloc.clamp_tail_index(0.15)
        self.assertAlmostEqual(xi_mid, 0.15, places=5)

    def test_tc24_f932_exponential_spectral_weight_properties(self):
        """TC24: Verify exponential spectral weighting function integrates to 1.0 and is positive."""
        gamma = 2.5
        p = np.linspace(0.001, 0.999, 1000)
        phi_p = np.array([exponential_spectral_weight(x, gamma=gamma) for x in p])
        self.assertTrue(np.all(phi_p >= 0.0))
        # Monotonically increasing with p
        self.assertTrue(np.all(np.diff(phi_p) > 0.0))
        # Numerical integration across [0, 1] equals 1.0
        integral = float(np.trapz(phi_p, p))
        self.assertAlmostEqual(integral, 1.0, places=2)

    def test_tc25_f932_exponential_spectral_weight_limiting_neutrality(self):
        """TC25: Verify limiting behavior as gamma -> 0 approaches uniform weighting phi(p) = 1.0."""
        p_vals = [0.1, 0.3, 0.5, 0.7, 0.9]
        for p in p_vals:
            w = exponential_spectral_weight(p, gamma=1e-6)
            self.assertAlmostEqual(w, 1.0, places=3)

    def test_tc26_f932_clamped_gpd_var_cvar_monotonicity(self):
        """TC26: Verify compute_clamped_gpd_spectral_cvar_v182 yields CVaR >= VaR strictly."""
        rng = np.random.RandomState(42)
        losses = rng.standard_t(df=3, size=500) * 0.02
        res = compute_clamped_gpd_spectral_cvar_v182(losses, alpha=0.95, gamma=2.0)
        self.assertIn("var", res)
        self.assertIn("cvar", res)
        self.assertIn("spectral_cvar", res)
        self.assertGreaterEqual(res["cvar"], res["var"])
        self.assertGreaterEqual(res["spectral_cvar"], res["var"])

    def test_tc27_f932_spectral_risk_budget_weights_sum_to_one(self):
        """TC27: Verify continuous tail-risk budget allocation weights sum strictly to 1.0000."""
        rng = np.random.RandomState(42)
        rets = rng.randn(150, 4) * 0.02
        res = compute_spectral_evt_cvar_risk_budget_v182(rets, gamma=2.0)
        w = res["risk_budget_weights"]
        self.assertAlmostEqual(float(np.sum(w)), 1.0, places=5)
        self.assertTrue(np.all(np.array(w) > 0.0))

    def test_tc28_f932_tail_risk_fat_tail_inversely_proportional(self):
        """TC28: Verify asset with fatter tail / higher CVaR receives lower allocation weight."""
        rets = np.zeros((200, 2))
        rets[:, 0] = np.random.RandomState(10).randn(200) * 0.01  # Gaussian thin-tail
        rets[:, 1] = np.random.RandomState(20).standard_t(df=2.5, size=200) * 0.04  # Student-t fat-tail
        res = compute_spectral_evt_cvar_risk_budget_v182(rets, gamma=3.0)
        w = res["risk_budget_weights"]
        self.assertGreater(w[0], w[1])

    def test_tc29_f932_allocator_instantiation_and_aliases(self):
        """TC29: Verify SpectralEVTCVaRAllocatorV182 and aliases instantiation."""
        a1 = SpectralEVTCVaRAllocatorV182()
        a2 = SpectralEVTCVaREngineV182()
        a3 = Phase190SpectralEVTCVaREngine()
        a4 = F932SpectralEVTCVaR()
        self.assertIsInstance(a1, SpectralEVTCVaRAllocatorV182)
        self.assertIsInstance(a2, SpectralEVTCVaRAllocatorV182)
        self.assertIsInstance(a3, SpectralEVTCVaRAllocatorV182)
        self.assertIsInstance(a4, SpectralEVTCVaRAllocatorV182)

    def test_tc30_f932_synthetic_rows_zero_invariant(self):
        """TC30: Verify synthetic_rows == 0 strictly in spectral EVT allocator output."""
        res = compute_spectral_evt_cvar_risk_budget_v182(np.random.randn(50, 2) * 0.01)
        self.assertEqual(res["synthetic_rows"], 0)
        self.assertIs(type(res["synthetic_rows"]), int)

    # =========================================================================
    # Category 5: F933 Asymmetric Power-Law Leland Buffer Bands (TC31 ~ TC38)
    # =========================================================================
    def test_tc31_f933_asymmetric_power_law_leland_formula(self):
        """TC31: Verify delta_i = (1.5 * gamma * sigma^2 * c / turnover)^(1/3) * (1 + 0.40 * max(0, lev - 1))."""
        gamma = 2.0
        sigma = 0.20
        c_cost = 0.0015
        turnover = 0.25
        leverage = 1.0  # (lev - 1) == 0 => multiplier 1.0
        bw = compute_asymmetric_power_law_leland_bands_v182(
            volatility=sigma,
            cost_rate=c_cost,
            gamma=gamma,
            turnover=turnover,
            leverage=leverage,
        )
        base = (1.5 * gamma * (sigma ** 2) * c_cost / turnover) ** (1.0 / 3.0)
        self.assertAlmostEqual(bw, base, places=5)

    def test_tc32_f933_leverage_expansion_bandwidth_factor(self):
        """TC32: Verify Leland bandwidth widens by (1 + 0.40 * (leverage - 1)) under compounding leverage."""
        bw_1x = compute_asymmetric_power_law_leland_bands_v182(
            volatility=0.20,
            cost_rate=0.0015,
            leverage=1.00,
        )
        bw_2x = compute_asymmetric_power_law_leland_bands_v182(
            volatility=0.20,
            cost_rate=0.0015,
            leverage=2.00,
        )
        expected_ratio = 1.0 + 0.40 * (2.0 - 1.0)  # 1.40x
        self.assertAlmostEqual(bw_2x / bw_1x, expected_ratio, places=4)

    def test_tc33_f933_bandwidth_clamping_bounds(self):
        """TC33: Verify Leland buffer bandwidth is clamped strictly within [0.005, 0.400]."""
        bw_low = compute_asymmetric_power_law_leland_bands_v182(
            volatility=0.001,
            cost_rate=1e-7,
            turnover=10.0,
        )
        self.assertGreaterEqual(bw_low, 0.005)

        bw_high = compute_asymmetric_power_law_leland_bands_v182(
            volatility=2.00,
            cost_rate=0.50,
            turnover=0.01,
            leverage=2.50,
        )
        self.assertLessEqual(bw_high, 0.400)

    def test_tc34_f933_instant_zero_bypass_fresh_entry(self):
        """TC34: Verify instant zero-bypass on fresh entry (curr_w == 0, targ_w > 0) executes immediately."""
        curr = {"NVDA": 0.00}
        targ = {"NVDA": 0.08}
        out = filter_portfolio_rebalance_v182(curr, targ)
        self.assertAlmostEqual(out.executable_weights["NVDA"], 0.08, places=4)
        self.assertTrue(out.zero_bypass_applied)

    def test_tc35_f933_instant_zero_bypass_full_exit(self):
        """TC35: Verify instant zero-bypass on full exit (curr_w > 0, targ_w == 0) executes immediately."""
        curr = {"INTC": 0.06}
        targ = {"INTC": 0.00}
        out = filter_portfolio_rebalance_v182(curr, targ)
        self.assertAlmostEqual(out.executable_weights.get("INTC", 0.0), 0.0, places=4)
        self.assertTrue(out.zero_bypass_applied)

    def test_tc36_f933_in_buffer_position_hold(self):
        """TC36: Verify in-buffer position hold: adjustments inside band hold current weight without churn."""
        curr = {"AAPL": 0.100}
        targ = {"AAPL": 0.108}  # Delta is 0.008, well within typical Leland band (~0.02 - 0.04)
        vols = {"AAPL": 0.25}
        out = filter_portfolio_rebalance_v182(curr, targ, volatilities=vols)
        # Should hold at current weight 0.100
        self.assertAlmostEqual(out.executable_weights["AAPL"], 0.100, places=3)
        self.assertEqual(out.trades_filtered_count, 1)

    def test_tc37_f933_allocator_instantiation_and_aliases(self):
        """TC37: Verify LelandBufferBandsV182 and aliases instantiation."""
        a1 = LelandBufferBandsV182()
        a2 = Phase190LelandBufferBands()
        a3 = F933LelandBufferBands()
        a4 = PowerLawLelandBufferBandsV182()
        self.assertIsInstance(a1, LelandBufferBandsV182)
        self.assertIsInstance(a2, LelandBufferBandsV182)
        self.assertIsInstance(a3, LelandBufferBandsV182)
        self.assertIsInstance(a4, LelandBufferBandsV182)

    def test_tc38_f933_synthetic_rows_zero_invariant(self):
        """TC38: Verify synthetic_rows == 0 strictly in Leland buffer bands output."""
        out = filter_portfolio_rebalance_v182({"A": 0.05}, {"A": 0.06})
        self.assertEqual(out.synthetic_rows, 0)
        self.assertIs(type(out.synthetic_rows), int)

    # =========================================================================
    # Category 6: F934 UnifiedPortfolioAllocator R182 10-Model Blend (TC39 ~ TC44)
    # =========================================================================
    def test_tc39_f934_ten_model_weights_sum_to_one(self):
        """TC39: Verify all 10 model weights in REGIME_MODEL_WEIGHTS_PHASE190 sum strictly to 1.0000."""
        for regime, model_dict in REGIME_MODEL_WEIGHTS_PHASE190.items():
            self.assertEqual(len(model_dict), 10, f"Regime {regime} does not have exactly 10 models")
            total = sum(model_dict.values())
            self.assertAlmostEqual(total, 1.0000, places=6, msg=f"Weights in {regime} sum to {total} != 1.0")

    def test_tc40_f934_gatheral_three_halves_power_penalty(self):
        """TC40: Verify Gatheral 3/2-power penalty formula TC(w, w0) = sum(eta*|dw|^1.5 + spread*|dw|)."""
        alloc = UnifiedPortfolioAllocator()
        weights = {"AAPL": 0.15, "MSFT": 0.10}
        curr_weights = {"AAPL": 0.05, "MSFT": 0.10}
        spread_dict = {"AAPL": 0.0005, "MSFT": 0.0005}
        eta_dict = {"AAPL": 0.02, "MSFT": 0.02}
        total_eq = 1_000_000.0

        penalty = alloc.compute_gatheral_market_impact_penalty_v182(
            weights=weights,
            current_weights=curr_weights,
            spread_dict=spread_dict,
            eta_dict=eta_dict,
        )
        # Delta AAPL = 0.10. Expected penalty = 0.02 * (0.10^1.5) + 0.0005 * 0.10
        dw = 0.10
        expected_penalty = 0.02 * (dw ** 1.5) + 0.0005 * dw
        self.assertAlmostEqual(penalty, expected_penalty, places=6)

    def test_tc41_f934_target_volatility_scaling_12pct(self):
        """TC41: Verify 12% target annualized volatility scales down weights when portfolio vol exceeds 12%."""
        alloc = UnifiedPortfolioAllocator()
        alphas = {"VOL_HIGH_1": 1.5, "VOL_HIGH_2": 1.4}
        # High volatility covariance matrix (each asset vol 40%, correlation 0.8)
        cov = np.array([
            [0.16, 0.128],
            [0.128, 0.16],
        ])
        res = alloc.allocate_portfolio_v182(
            alpha_vector=alphas,
            cov_matrix=cov,
            regime="BULL_STABLE",
            target_volatility=0.12,
        )
        self.assertIsNotNone(res)
        self.assertLessEqual(res.gross_leverage, 2.15)
        # Weights should be damped to respect 12% target vol ceiling
        w_arr = np.array(list(res.target_weights.values()))
        port_vol = math.sqrt(float(w_arr.T @ cov @ w_arr))
        self.assertLessEqual(port_vol, 0.125)

    def test_tc42_f934_physical_capital_conservation(self):
        """TC42: Verify physical capital conservation: Net Equity <= Gross Equity and sum(w) + w_cash == leverage."""
        alphas = {"AAPL": 0.08, "MSFT": 0.07, "AMZN": 0.06}
        res = allocate_portfolio_v182(alphas, regime="BULL_STABLE", gross_leverage=2.00)
        self.assertLessEqual(res.net_leverage, res.gross_leverage + 1e-6)
        w_cash = res.metadata["w_cash"]
        gross = res.gross_leverage
        self.assertAlmostEqual(gross + w_cash, 2.00, places=2)
        self.assertTrue(res.metadata["capital_conservation"])

    def test_tc43_f934_single_stock_cap_enforcement(self):
        """TC43: Verify individual stock weights do not exceed effective single stock cap."""
        alphas = {"DOMINANT_1": 10.0, "DOMINANT_2": 8.0, "SYM3": 0.1, "SYM4": 0.1}
        res = allocate_portfolio_v182(alphas, regime="NEUTRAL_EXPANSION", gross_leverage=1.00)
        # Single stock cap max(0.05 * lev, lev / N) = 1.00 / 4 = 0.25
        for sym, w in res.target_weights.items():
            self.assertLessEqual(w, 0.26)

    def test_tc44_f934_allocator_instantiation_and_execution(self):
        """TC44: Verify UnifiedPortfolioAllocatorV182 and allocate_portfolio_v182 functional execution."""
        alloc = UnifiedPortfolioAllocatorV182()
        self.assertIsInstance(alloc, UnifiedPortfolioAllocator)
        res = allocate_portfolio_v182({"005930": 0.05, "000660": 0.04}, regime="BULL_STABLE")
        self.assertIsInstance(res, AllocationResult)
        self.assertEqual(res.metadata["version"], 190)
        self.assertEqual(res.metadata["release"], "R182")
        self.assertEqual(res.metadata["feature"], "F934")

    # =========================================================================
    # Category 7: End-to-End Integration, Crisis Shock Defense & Invariants (TC45 ~ TC50)
    # =========================================================================
    def test_tc45_end_to_end_five_market_portfolio_allocation(self):
        """TC45: Verify end-to-end multi-market portfolio allocation across 5 markets."""
        syms_5m = {
            "005930.KS": 0.06,  # KOSPI
            "068270.KQ": 0.05,  # KOSDAQ
            "AAPL": 0.08,       # SP500 / NASDAQ
            "MSFT": 0.07,       # NASDAQ
            "IWM": 0.04,        # RUSSELL2000 proxy
        }
        res = allocate_portfolio_v182(syms_5m, regime="BULL_STABLE")
        self.assertEqual(len(res.target_weights), 5)
        for sym in syms_5m:
            self.assertIn(sym, res.target_weights)
            self.assertGreater(res.target_weights[sym], 0.0)

    def test_tc46_crisis_halt_regime_100pct_cash_lock(self):
        """TC46: Verify CRISIS_HALT regime enforces 100% Cash Lock (0.00x gross leverage)."""
        alphas = {"AAPL": 1.0, "MSFT": 1.0}
        res = allocate_portfolio_v182(alphas, regime="CRISIS_HALT")
        self.assertEqual(res.gross_leverage, 0.00)
        self.assertEqual(res.net_leverage, 0.00)
        for w in res.target_weights.values():
            self.assertEqual(w, 0.0)

    def test_tc47_bear_defensive_regime_leverage_compression(self):
        """TC47: Verify BEAR_DEFENSIVE regime compresses gross leverage strictly to <= 0.25x."""
        alphas = {"AAPL": 1.0, "MSFT": 1.0, "NVDA": 1.0}
        res = allocate_portfolio_v182(alphas, regime="BEAR_DEFENSIVE")
        self.assertLessEqual(res.gross_leverage, 0.25)

    def test_tc48_bull_stable_compounding_leverage_up_to_215x(self):
        """TC48: Verify BULL_STABLE achieves compounding leverage up to 2.15x."""
        alphas = {f"SYM_{i}": 1.0 + 0.1 * i for i in range(20)}
        res = allocate_portfolio_v182(alphas, regime="BULL_STABLE")
        self.assertAlmostEqual(res.gross_leverage, 2.15, places=2)

    def test_tc49_allocation_performance_latency_sub_50ms(self):
        """TC49: Verify allocate_portfolio_v182 execution executes in < 50ms for 20-asset portfolio."""
        alphas = {f"SYM_{i}": float(np.random.uniform(0.01, 0.10)) for i in range(20)}
        t0 = time.perf_counter()
        res = allocate_portfolio_v182(alphas, regime="BULL_STABLE")
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        self.assertLess(elapsed_ms, 50.0, f"Execution took {elapsed_ms:.2f}ms >= 50ms")
        self.assertIsNotNone(res)

    def test_tc50_absolute_system_invariant_zero_synthetic_rows(self):
        """TC50: Verify absolute system invariant: synthetic_rows == 0 strictly across all Phase 190 modules."""
        # 1. Hyperbolic OT
        res_hyp = allocate_hyperbolic_ot_v182(["SPY", "QQQ"], [1.0, 1.0])
        self.assertEqual(res_hyp["synthetic_rows"], 0)
        self.assertIs(type(res_hyp["synthetic_rows"]), int)

        # 2. Dynamic Regime Leverage
        alloc_lev = DynamicRegimeLeverageAllocatorV182()
        res_lev = alloc_lev.allocate_regime_leverage(symbols=["SPY"], alphas={"SPY": 1.0}, regime="BULL_STABLE")
        self.assertEqual(res_lev["synthetic_rows"], 0)
        self.assertIs(type(res_lev["synthetic_rows"]), int)

        # 3. Spectral EVT-CVaR
        res_evt = compute_spectral_evt_cvar_risk_budget_v182(np.array([[0.01, 0.02], [-0.01, 0.01]]))
        self.assertEqual(res_evt["synthetic_rows"], 0)
        self.assertIs(type(res_evt["synthetic_rows"]), int)

        # 4. Leland Buffer Bands
        out_lel = filter_portfolio_rebalance_v182({"SPY": 0.5}, {"SPY": 0.52})
        self.assertEqual(out_lel.synthetic_rows, 0)
        self.assertIs(type(out_lel.synthetic_rows), int)

        # 5. Unified Portfolio Allocator
        res_u = allocate_portfolio_v182({"SPY": 0.05, "QQQ": 0.05}, regime="BULL_STABLE")
        self.assertEqual(res_u.metadata["synthetic_rows"], 0)
        self.assertIs(type(res_u.metadata["synthetic_rows"]), int)


if __name__ == "__main__":
    unittest.main()
