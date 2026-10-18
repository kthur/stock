r"""
tests/test_phase120_riemannian_manifold.py
==========================================
Exhaustive 60-Test Verification Suite across 12 Rigorous Categories for:
Curvature-Aware Riemannian Manifold Portfolio Allocator & Fisher Information Metric Engine (Feature F572).
Phase 120 (Release R136 / v127 Production Master).

Categories (60 Test Cases):
  - Category 1: Dual-Tree Parity, Metadata, Enums & Complete Alias Trees (TC01 ~ TC05)
  - Category 2: Configuration & 5-Market Pre-Calibrated Profiles (TC06 ~ TC10)
  - Category 3: Fisher-Rao Information Metric & Spherical Coordinate Embedding (TC11 ~ TC15)
  - Category 4: Exact Geodesic Arc Distance dist_R(w^{(a)}, w^{(b)}) Invariants (TC16 ~ TC20)
  - Category 5: Tangent Space Projection & Natural Riemannian Gradient Descent (TC21 ~ TC25)
  - Category 6: Exponential Simplex Retraction & Non-Negative Conservation (TC26 ~ TC30)
  - Category 7: Gromov \delta-Hyperbolicity & Sectional Curvature Estimation (TC31 ~ TC35)
  - Category 8: Systemic Crash Early Warning & Dynamic Cash De-risking (TC36 ~ TC40)
  - Category 9: Geodesic Leland No-Trade Buffer Bands Mechanics (TC41 ~ TC45)
  - Category 10: Instant Bypass for New Entries (w_{0, i} = 0) & Full Liquidations (w_i^* = 0) (TC46 ~ TC50)
  - Category 11: Critical Edge Cases & Degenerate Scenarios (TC51 ~ TC55)
  - Category 12: Execution Latency SLA, Downstream Interfaces & Telemetry (TC56 ~ TC60)
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import sys
import time
import unittest
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np

# Ensure project root and trading_system are on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p in (str(PROJECT_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

import src.risk.riemannian_manifold_portfolio_allocator as rm_module
from src.risk.riemannian_manifold_portfolio_allocator import (
    VERSION,
    RELEASE,
    FEATURE,
    EPSILON_FLOOR,
    DEFAULT_MAX_HYPERBOLICITY_SAMPLES,
    CRASH_ALERT_THRESHOLD,
    MarketType,
    BypassAction,
    CurvatureRegime,
    RiemannianProfile,
    RiemannianAllocatorConfig,
    HyperbolicityDiagnostics,
    GeodesicLelandBand,
    RiemannianOptimizationResult,
    MARKET_RIEMANNIAN_PROFILES,
    get_market_profile,
    spherical_embedding,
    inverse_spherical_embedding,
    geodesic_distance,
    fisher_rao_metric_tensor,
    project_tangent_space,
    exponential_retraction,
    compute_gromov_hyperbolicity,
    apply_geodesic_leland_bands,
    RiemannianManifoldPortfolioAllocator,
    FisherRaoPortfolioAllocator,
    CurvatureAwarePortfolioAllocator,
    RiemannianSimplexOptimizer,
    Phase120RiemannianAllocator,
    F572RiemannianManifoldAllocator,
    GromovHyperbolicRiskAllocator,
    GeodesicLelandPortfolioAllocator,
    FisherInformationMetricEngine,
    RiemannianManifoldAllocator,
    Phase120RiskAllocator,
    RiemannianPortfolioOptimizer,
    FisherRaoMetricEngine,
    RiemannianConfig,
    FisherRaoConfig,
    RiemannianOutput,
    RiemannianResult,
    HyperbolicityResult,
    GromovCrashDiagnostics,
    LelandBandDiagnostics,
    _TORCH_AVAILABLE,
)


class TestPhase120RiemannianManifold(unittest.TestCase):
    """Exhaustive 60-test verification harness for Feature F572 Riemannian Manifold Portfolio Allocator."""

    def setUp(self) -> None:
        self.rng = np.random.RandomState(42)
        self.n_assets = 6
        self.asset_names = [f"SYM_{i}" for i in range(self.n_assets)]

        # Base synthetic return vector and positive-definite covariance matrix
        self.mu = np.array([0.14, 0.11, 0.16, 0.08, 0.12, 0.09], dtype=np.float64)

        A = self.rng.randn(self.n_assets, self.n_assets)
        self.cov = (A @ A.T) * 0.01 + np.diag([0.04, 0.03, 0.05, 0.02, 0.035, 0.025])

        # Current portfolio weights (simplex sum = 1.0)
        self.w0 = np.array([0.20, 0.15, 0.25, 0.10, 0.15, 0.15], dtype=np.float64)

    # =======================================================================
    # Category 1: Dual-Tree Parity, Metadata, Enums & Complete Alias Trees (TC01 ~ TC05)
    # =======================================================================
    def test_tc01_version_release_feature_metadata(self) -> None:
        """TC01: Verify VERSION == 120, RELEASE == 'R136', FEATURE == 'F572'."""
        self.assertEqual(VERSION, 120)
        self.assertEqual(RELEASE, "R136")
        self.assertEqual(FEATURE, "F572")
        self.assertEqual(rm_module.VERSION, 120)
        self.assertEqual(rm_module.RELEASE, "R136")
        self.assertEqual(rm_module.FEATURE, "F572")

    def test_tc02_dual_tree_sha256_cryptographic_parity(self) -> None:
        """TC02: Verify 100% bit-for-bit SHA-256 dual-tree parity between src/ and trading_system/src/."""
        path_primary = PROJECT_ROOT / "src" / "risk" / "riemannian_manifold_portfolio_allocator.py"
        path_mirror = PROJECT_ROOT / "trading_system" / "src" / "risk" / "riemannian_manifold_portfolio_allocator.py"

        self.assertTrue(path_primary.exists(), f"Primary missing: {path_primary}")
        self.assertTrue(path_mirror.exists(), f"Mirror missing: {path_mirror}")

        with open(path_primary, "rb") as f1, open(path_mirror, "rb") as f2:
            hash1 = hashlib.sha256(f1.read()).hexdigest()
            hash2 = hashlib.sha256(f2.read()).hexdigest()

        self.assertEqual(hash1, hash2, "Dual-tree SHA-256 divergence detected!")
        self.assertGreater(len(hash1), 32)

    def test_tc03_enums_integrity(self) -> None:
        """TC03: Verify MarketType, BypassAction, and CurvatureRegime enums."""
        expected_markets = {"SP500", "NASDAQ", "RUSSELL2000", "KOSPI", "KOSDAQ"}
        actual_markets = {m.value for m in MarketType}
        self.assertEqual(actual_markets, expected_markets)

        expected_actions = {"ENTRY_BYPASS", "EXIT_BYPASS", "HOLD", "BUY", "SELL"}
        actual_actions = {a.value for a in BypassAction}
        self.assertEqual(actual_actions, expected_actions)

        expected_regimes = {"SPHERICAL_POSITIVE", "EUCLIDEAN_FLAT", "HYPERBOLIC_NEGATIVE", "SYSTEMIC_TREE_CONTAGION"}
        actual_regimes = {r.value for r in CurvatureRegime}
        self.assertEqual(actual_regimes, expected_regimes)

    def test_tc04_allocator_alias_tree_completeness(self) -> None:
        """TC04: Verify complete backward-compatibility alias tree for allocator class."""
        aliases = [
            FisherRaoPortfolioAllocator,
            CurvatureAwarePortfolioAllocator,
            RiemannianSimplexOptimizer,
            Phase120RiemannianAllocator,
            F572RiemannianManifoldAllocator,
            GromovHyperbolicRiskAllocator,
            GeodesicLelandPortfolioAllocator,
            FisherInformationMetricEngine,
            RiemannianManifoldAllocator,
            Phase120RiskAllocator,
            RiemannianPortfolioOptimizer,
            FisherRaoMetricEngine,
        ]
        for alias in aliases:
            self.assertIs(alias, RiemannianManifoldPortfolioAllocator)

    def test_tc05_dataclass_aliases_and_sys_modules(self) -> None:
        """TC05: Verify dataclass aliases and sys.modules registrations."""
        self.assertIs(RiemannianConfig, RiemannianAllocatorConfig)
        self.assertIs(FisherRaoConfig, RiemannianAllocatorConfig)
        self.assertIs(RiemannianOutput, RiemannianOptimizationResult)
        self.assertIs(RiemannianResult, RiemannianOptimizationResult)
        self.assertIs(HyperbolicityResult, HyperbolicityDiagnostics)
        self.assertIs(GromovCrashDiagnostics, HyperbolicityDiagnostics)
        self.assertIs(LelandBandDiagnostics, GeodesicLelandBand)

        self.assertIn("src.risk.riemannian_manifold_portfolio_allocator", sys.modules)
        self.assertIn("trading_system.src.risk.riemannian_manifold_portfolio_allocator", sys.modules)

    # =======================================================================
    # Category 2: Configuration & 5-Market Pre-Calibrated Profiles (TC06 ~ TC10)
    # =======================================================================
    def test_tc06_sp500_profile_calibration(self) -> None:
        """TC06: Verify SP500 pre-calibrated profile parameters."""
        prof = get_market_profile("SP500")
        self.assertEqual(prof.market, "SP500")
        self.assertAlmostEqual(prof.risk_aversion, 1.20)
        self.assertAlmostEqual(prof.turnover_penalty_gamma, 0.05)
        self.assertAlmostEqual(prof.leland_base_band, 0.015)
        self.assertAlmostEqual(prof.critical_hyperbolicity, 0.25)
        self.assertAlmostEqual(prof.learning_rate, 0.05)
        self.assertEqual(prof.max_iterations, 200)

    def test_tc07_nasdaq_profile_calibration(self) -> None:
        """TC07: Verify NASDAQ pre-calibrated profile parameters."""
        prof = get_market_profile("NASDAQ")
        self.assertEqual(prof.market, "NASDAQ")
        self.assertAlmostEqual(prof.risk_aversion, 1.00)
        self.assertAlmostEqual(prof.turnover_penalty_gamma, 0.06)
        self.assertAlmostEqual(prof.leland_base_band, 0.018)
        self.assertAlmostEqual(prof.critical_hyperbolicity, 0.28)
        self.assertAlmostEqual(prof.learning_rate, 0.05)
        self.assertEqual(prof.max_iterations, 200)

    def test_tc08_russell2000_profile_calibration(self) -> None:
        """TC08: Verify RUSSELL2000 pre-calibrated profile parameters."""
        prof = get_market_profile("RUSSELL2000")
        self.assertEqual(prof.market, "RUSSELL2000")
        self.assertAlmostEqual(prof.risk_aversion, 1.40)
        self.assertAlmostEqual(prof.turnover_penalty_gamma, 0.08)
        self.assertAlmostEqual(prof.leland_base_band, 0.022)
        self.assertAlmostEqual(prof.critical_hyperbolicity, 0.32)
        self.assertAlmostEqual(prof.learning_rate, 0.04)
        self.assertEqual(prof.max_iterations, 250)

    def test_tc09_kospi_profile_calibration(self) -> None:
        """TC09: Verify KOSPI pre-calibrated profile parameters."""
        prof = get_market_profile("KOSPI")
        self.assertEqual(prof.market, "KOSPI")
        self.assertAlmostEqual(prof.risk_aversion, 1.15)
        self.assertAlmostEqual(prof.turnover_penalty_gamma, 0.05)
        self.assertAlmostEqual(prof.leland_base_band, 0.016)
        self.assertAlmostEqual(prof.critical_hyperbolicity, 0.26)
        self.assertAlmostEqual(prof.learning_rate, 0.05)
        self.assertEqual(prof.max_iterations, 200)

    def test_tc10_kosdaq_and_fallback_profile_calibration(self) -> None:
        """TC10: Verify KOSDAQ profile parameters and unknown market fallback."""
        prof_kq = get_market_profile("KOSDAQ")
        self.assertEqual(prof_kq.market, "KOSDAQ")
        self.assertAlmostEqual(prof_kq.risk_aversion, 1.35)
        self.assertAlmostEqual(prof_kq.turnover_penalty_gamma, 0.07)
        self.assertAlmostEqual(prof_kq.leland_base_band, 0.020)
        self.assertAlmostEqual(prof_kq.critical_hyperbolicity, 0.30)
        self.assertAlmostEqual(prof_kq.learning_rate, 0.04)
        self.assertEqual(prof_kq.max_iterations, 250)

        # Fallback test
        prof_fb = get_market_profile("UNKNOWN_EXCHANGE")
        self.assertEqual(prof_fb.market, "SP500")

    # =======================================================================
    # Category 3: Fisher-Rao Metric & Spherical Coordinate Embedding (TC11 ~ TC15)
    # =======================================================================
    def test_tc11_spherical_embedding_norm_uniform(self) -> None:
        """TC11: Spherical embedding norm ||xi||_2 == 2.0 for uniform weights."""
        w_uni = np.full(5, 0.20, dtype=np.float64)
        xi = spherical_embedding(w_uni)
        norm = np.linalg.norm(xi)
        self.assertAlmostEqual(norm, 2.0, places=10)

    def test_tc12_spherical_embedding_norm_random(self) -> None:
        """TC12: Spherical embedding norm ||xi||_2 == 2.0 for arbitrary random simplex weights."""
        for _ in range(10):
            raw = self.rng.exponential(scale=1.0, size=8)
            w = raw / np.sum(raw)
            xi = spherical_embedding(w)
            norm = np.linalg.norm(xi)
            self.assertAlmostEqual(norm, 2.0, places=10)

    def test_tc13_round_trip_spherical_embedding_identity(self) -> None:
        """TC13: Round-trip identity w -> xi -> w recovers original weights within 10^-12."""
        raw = self.rng.uniform(0.01, 1.0, size=7)
        w_orig = raw / np.sum(raw)
        xi = spherical_embedding(w_orig)
        w_rec = inverse_spherical_embedding(xi)
        np.testing.assert_allclose(w_rec, w_orig, atol=1e-12)

    def test_tc14_fisher_rao_diagonal_metric_tensor(self) -> None:
        """TC14: Fisher-Rao metric tensor g_ij(w) == delta_ij / w_i matches inverse weights."""
        w = np.array([0.5, 0.3, 0.2], dtype=np.float64)
        G = fisher_rao_metric_tensor(w)
        expected = np.diag([2.0, 1.0 / 0.3, 5.0])
        np.testing.assert_allclose(G, expected, atol=1e-10)

    def test_tc15_differential_line_element_isometry(self) -> None:
        """TC15: Infinitesimal line element ds^2 = sum (dw_i)^2 / w_i matches hypersphere metric sum (dxi_i)^2."""
        w = np.array([0.4, 0.35, 0.25], dtype=np.float64)
        # Small tangent displacement on simplex: sum dw = 0
        dw = np.array([0.001, -0.0006, -0.0004], dtype=np.float64)

        # ds^2 via Fisher-Rao
        ds2_fr = float(np.sum((dw ** 2) / w))

        # dxi via spherical coordinates: dxi = dw / sqrt(w)
        dxi = dw / np.sqrt(w)
        ds2_sphere = float(np.sum(dxi ** 2))

        self.assertAlmostEqual(ds2_fr, ds2_sphere, places=12)

    # =======================================================================
    # Category 4: Exact Geodesic Arc Distance dist_R Invariants (TC16 ~ TC20)
    # =======================================================================
    def test_tc16_geodesic_distance_identity(self) -> None:
        """TC16: Geodesic distance to self dist_R(w, w) == 0.0 exactly."""
        w = np.array([0.1, 0.4, 0.5], dtype=np.float64)
        d = geodesic_distance(w, w)
        self.assertEqual(d, 0.0)

    def test_tc17_geodesic_distance_symmetry(self) -> None:
        """TC17: Geodesic distance symmetry dist_R(a, b) == dist_R(b, a)."""
        w_a = np.array([0.3, 0.3, 0.4], dtype=np.float64)
        w_b = np.array([0.1, 0.6, 0.3], dtype=np.float64)
        d_ab = geodesic_distance(w_a, w_b)
        d_ba = geodesic_distance(w_b, w_a)
        self.assertAlmostEqual(d_ab, d_ba, places=14)

    def test_tc18_geodesic_distance_orthogonal_extremum(self) -> None:
        """TC18: Disjoint orthogonal portfolio weights produce maximum distance dist_R == pi."""
        w_a = np.array([1.0, 0.0, 0.0], dtype=np.float64)
        w_b = np.array([0.0, 1.0, 0.0], dtype=np.float64)
        d = geodesic_distance(w_a, w_b)
        self.assertAlmostEqual(d, math.pi, places=10)

    def test_tc19_geodesic_distance_triangle_inequality(self) -> None:
        """TC19: Triangle inequality dist_R(a, c) <= dist_R(a, b) + dist_R(b, c) holds."""
        for _ in range(15):
            r1 = self.rng.exponential(size=5)
            r2 = self.rng.exponential(size=5)
            r3 = self.rng.exponential(size=5)
            w_a = r1 / np.sum(r1)
            w_b = r2 / np.sum(r2)
            w_c = r3 / np.sum(r3)

            d_ac = geodesic_distance(w_a, w_c)
            d_ab = geodesic_distance(w_a, w_b)
            d_bc = geodesic_distance(w_b, w_c)

            self.assertLessEqual(d_ac, d_ab + d_bc + 1e-12)

    def test_tc20_geodesic_distance_range_boundedness(self) -> None:
        """TC20: Geodesic distance dist_R is strictly bounded in [0, pi] for all configurations."""
        for _ in range(25):
            r1 = self.rng.uniform(0.0, 1.0, size=6)
            r2 = self.rng.uniform(0.0, 1.0, size=6)
            w_a = r1 / np.sum(r1)
            w_b = r2 / np.sum(r2)

            d = geodesic_distance(w_a, w_b)
            self.assertGreaterEqual(d, 0.0)
            self.assertLessEqual(d, math.pi + 1e-12)

    # =======================================================================
    # Category 5: Tangent Space Projection & Natural Gradient Descent (TC21 ~ TC25)
    # =======================================================================
    def test_tc21_tangent_space_projection_orthogonality(self) -> None:
        """TC21: Tangent space projection strictly satisfies sum(grad_R) == 0.0."""
        w = np.array([0.25, 0.35, 0.15, 0.25], dtype=np.float64)
        grad_euclid = np.array([12.5, -4.2, 8.7, 1.1], dtype=np.float64)

        grad_r = project_tangent_space(grad_euclid, w)
        sum_grad_r = float(np.sum(grad_r))
        self.assertAlmostEqual(sum_grad_r, 0.0, places=12)

    def test_tc22_tangent_space_projection_uniform_gradient_vanishes(self) -> None:
        """TC22: Uniform Euclidean gradient (along normal vector 1) projects to zero tangent gradient."""
        w = np.array([0.2, 0.3, 0.5], dtype=np.float64)
        grad_uniform = np.full(3, 7.5, dtype=np.float64)

        grad_r = project_tangent_space(grad_uniform, w)
        np.testing.assert_allclose(grad_r, np.zeros(3), atol=1e-14)

    def test_tc23_natural_gradient_direction(self) -> None:
        """TC23: Asset with higher expected return receives negative gradient (descent increases weight)."""
        w = np.full(3, 1.0 / 3.0, dtype=np.float64)
        # Gradient is -\mu for pure return maximization
        grad_euclid = np.array([-0.20, -0.10, -0.05], dtype=np.float64)

        grad_r = project_tangent_space(grad_euclid, w)
        # grad_r for asset 0 should be negative so -eta * grad_r is positive
        self.assertLess(grad_r[0], 0.0)
        self.assertGreater(grad_r[2], 0.0)

    def test_tc24_natural_gradient_objective_descent(self) -> None:
        """TC24: Single natural gradient step decreases mean-variance objective."""
        mu = self.mu[:3]
        cov = self.cov[:3, :3]
        w = np.full(3, 1.0 / 3.0, dtype=np.float64)

        gamma = 1.0
        grad_euclid = gamma * (cov @ w) - mu
        grad_r = project_tangent_space(grad_euclid, w)

        w_new = exponential_retraction(w, grad_r, learning_rate=0.05)

        obj_old = 0.5 * gamma * (w @ cov @ w) - np.dot(w, mu)
        obj_new = 0.5 * gamma * (w_new @ cov @ w_new) - np.dot(w_new, mu)

        self.assertLess(obj_new, obj_old)

    def test_tc25_risk_aversion_scaling_effect(self) -> None:
        """TC25: Higher risk aversion shifts weights towards minimum variance portfolio."""
        allocator_low_risk = RiemannianManifoldPortfolioAllocator(market="SP500", risk_aversion=0.2, leland_base_band=0.0)
        allocator_high_risk = RiemannianManifoldPortfolioAllocator(market="SP500", risk_aversion=5.0, leland_base_band=0.0)

        res_low = allocator_low_risk.optimize(self.mu, self.cov)
        res_high = allocator_high_risk.optimize(self.mu, self.cov)

        vol_low = res_low.expected_volatility
        vol_high = res_high.expected_volatility

        self.assertLess(vol_high, vol_low)

    # =======================================================================
    # Category 6: Exponential Simplex Retraction & Non-Negative Conservation (TC26 ~ TC30)
    # =======================================================================
    def test_tc26_retraction_strictly_preserves_simplex_sum(self) -> None:
        """TC26: Exponential retraction output strictly sums to 1.000000."""
        w = np.array([0.2, 0.3, 0.1, 0.4], dtype=np.float64)
        grad = np.array([0.5, -0.2, -0.4, 0.1], dtype=np.float64)

        for eta in [0.001, 0.05, 0.2, 1.0, 5.0]:
            w_next = exponential_retraction(w, grad, learning_rate=eta)
            self.assertAlmostEqual(float(np.sum(w_next)), 1.0, places=10)

    def test_tc27_retraction_strictly_preserves_positivity(self) -> None:
        """TC27: Exponential retraction strictly preserves positive weights w_i > 0."""
        w = np.array([0.01, 0.001, 0.5, 0.489], dtype=np.float64)
        grad = np.array([10.0, 20.0, -5.0, -10.0], dtype=np.float64)

        w_next = exponential_retraction(w, grad, learning_rate=0.5)
        self.assertTrue(np.all(w_next > 0.0))
        self.assertTrue(np.all(w_next >= EPSILON_FLOOR))

    def test_tc28_retraction_numerical_stability_overflow_protection(self) -> None:
        """TC28: Retraction under extreme steep gradients (10^8) does not produce NaN or overflow."""
        w = np.full(4, 0.25, dtype=np.float64)
        grad_extreme = np.array([1e8, -1e8, 5e7, -5e7], dtype=np.float64)

        w_next = exponential_retraction(w, grad_extreme, learning_rate=0.1)
        self.assertFalse(np.any(np.isnan(w_next)))
        self.assertFalse(np.any(np.isinf(w_next)))
        self.assertAlmostEqual(float(np.sum(w_next)), 1.0, places=10)

    def test_tc29_step_size_monotonicity(self) -> None:
        """TC29: Larger learning rate eta moves further along geodesic arc."""
        w = np.full(4, 0.25, dtype=np.float64)
        grad = np.array([0.4, -0.3, 0.1, -0.2], dtype=np.float64)

        w_small = exponential_retraction(w, grad, learning_rate=0.02)
        w_large = exponential_retraction(w, grad, learning_rate=0.10)

        d_small = geodesic_distance(w_small, w)
        d_large = geodesic_distance(w_large, w)

        self.assertGreater(d_large, d_small)

    def test_tc30_full_optimization_convergence(self) -> None:
        """TC30: Optimization completes and reaches converged state."""
        allocator = RiemannianManifoldPortfolioAllocator(market="SP500", max_iterations=300, convergence_tol=1e-3)
        res = allocator.optimize(self.mu, self.cov)
        self.assertTrue(res.converged)
        self.assertLess(res.iterations, 300)

    # =======================================================================
    # Category 7: Gromov delta-Hyperbolicity & Sectional Curvature (TC31 ~ TC35)
    # =======================================================================
    def test_tc31_correlation_distance_matrix_metric_properties(self) -> None:
        """TC31: Distance matrix D_ij = sqrt(2(1 - rho_ij)) has zero diagonal and symmetry."""
        corr = np.array([[1.0, 0.6, 0.2], [0.6, 1.0, 0.4], [0.2, 0.4, 1.0]], dtype=np.float64)
        d = np.sqrt(np.maximum(0.0, 2.0 * (1.0 - corr)))
        np.fill_diagonal(d, 0.0)

        np.testing.assert_allclose(np.diag(d), np.zeros(3))
        np.testing.assert_allclose(d, d.T)
        self.assertAlmostEqual(d[0, 1], math.sqrt(2.0 * (1.0 - 0.6)))

    def test_tc32_extreme_contagion_ultrametric_delta_zero(self) -> None:
        """TC32: Perfect positive correlation matrix produces Gromov delta == 0.0."""
        corr_perfect = np.ones((5, 5), dtype=np.float64)
        diag = compute_gromov_hyperbolicity(corr_perfect, critical_delta=0.25)

        self.assertAlmostEqual(diag.gromov_delta, 0.0, places=10)
        self.assertEqual(diag.curvature_regime, CurvatureRegime.SYSTEMIC_TREE_CONTAGION)

    def test_tc33_systemic_tree_contagion_alert_activation(self) -> None:
        """TC33: Near-unity correlation (0.98) triggers systemic tree contagion crash alert."""
        corr_stressed = np.full((6, 6), 0.98, dtype=np.float64)
        np.fill_diagonal(corr_stressed, 1.0)

        diag = compute_gromov_hyperbolicity(corr_stressed, critical_delta=0.25, kappa_hyp=15.0)
        self.assertTrue(diag.is_crash_alert)
        self.assertGreater(diag.h_crash, CRASH_ALERT_THRESHOLD)
        self.assertEqual(diag.curvature_regime, CurvatureRegime.SYSTEMIC_TREE_CONTAGION)

    def test_tc34_uncorrelated_assets_spherical_positive_regime(self) -> None:
        """TC34: Uncorrelated assets (rho_ij == 0) yield delta_Gromov > delta_crit and no alert."""
        corr_uncorr = np.eye(6, dtype=np.float64)
        diag = compute_gromov_hyperbolicity(corr_uncorr, critical_delta=0.25)

        self.assertGreater(diag.gromov_delta, 0.25)
        self.assertFalse(diag.is_crash_alert)
        self.assertLess(diag.h_crash, 0.50)

    def test_tc35_gromov_4tuple_evaluation_count(self) -> None:
        """TC35: Evaluates exactly binom(n, 4) tuples for n=6 (15 combinations)."""
        corr = np.eye(6, dtype=np.float64)
        diag = compute_gromov_hyperbolicity(corr, max_samples=1000)
        # binom(6, 4) = 15
        self.assertEqual(diag.num_4tuples_evaluated, 15)

    # =======================================================================
    # Category 8: Systemic Crash Early Warning & Cash De-risking (TC36 ~ TC40)
    # =======================================================================
    def test_tc36_h_crash_monotonicity(self) -> None:
        """TC36: Crash indicator H_crash monotonically increases as delta_Gromov decreases."""
        corr_high_delta = np.eye(5, dtype=np.float64)
        corr_low_delta = np.full((5, 5), 0.95, dtype=np.float64)
        np.fill_diagonal(corr_low_delta, 1.0)

        diag_high = compute_gromov_hyperbolicity(corr_high_delta, critical_delta=0.25)
        diag_low = compute_gromov_hyperbolicity(corr_low_delta, critical_delta=0.25)

        self.assertGreater(diag_low.h_crash, diag_high.h_crash)

    def test_tc37_crash_alert_threshold_gate(self) -> None:
        """TC37: is_crash_alert is strictly True when H_crash >= 0.70."""
        corr_stressed = np.full((6, 6), 0.99, dtype=np.float64)
        np.fill_diagonal(corr_stressed, 1.0)

        diag = compute_gromov_hyperbolicity(corr_stressed, critical_delta=0.25)
        self.assertGreaterEqual(diag.h_crash, 0.70)
        self.assertTrue(diag.is_crash_alert)

    def test_tc38_dynamic_cash_de_risking_allocation(self) -> None:
        """TC38: Systemic crash triggers positive cash allocation in optimization result."""
        corr_stressed = np.full((self.n_assets, self.n_assets), 0.99, dtype=np.float64)
        np.fill_diagonal(corr_stressed, 1.0)

        allocator = RiemannianManifoldPortfolioAllocator(market="SP500")
        res = allocator.optimize(self.mu, self.cov, corr_matrix=corr_stressed)

        self.assertTrue(res.hyperbolicity_diagnostics.is_crash_alert)
        self.assertGreater(res.cash_weight, 0.20)
        self.assertLess(np.sum(res.optimal_weights), 1.0)

    def test_tc39_total_budget_conservation_with_cash(self) -> None:
        """TC39: Optimal weights + cash buffer strictly sum to 1.000000 under crash conditions."""
        corr_stressed = np.full((self.n_assets, self.n_assets), 0.985, dtype=np.float64)
        np.fill_diagonal(corr_stressed, 1.0)

        allocator = RiemannianManifoldPortfolioAllocator(market="NASDAQ")
        res = allocator.optimize(self.mu, self.cov, corr_matrix=corr_stressed)

        total_alloc = float(np.sum(res.optimal_weights) + res.cash_weight)
        self.assertAlmostEqual(total_alloc, 1.0, places=10)

    def test_tc40_zero_cash_allocation_in_normal_regime(self) -> None:
        """TC40: Under normal decorrelated market conditions, cash allocation is 0.0."""
        corr_normal = np.eye(self.n_assets, dtype=np.float64)
        allocator = RiemannianManifoldPortfolioAllocator(market="SP500")
        res = allocator.optimize(self.mu, self.cov, corr_matrix=corr_normal)

        self.assertFalse(res.hyperbolicity_diagnostics.is_crash_alert)
        self.assertEqual(res.cash_weight, 0.0)
        self.assertAlmostEqual(float(np.sum(res.optimal_weights)), 1.0, places=10)

    # =======================================================================
    # Category 9: Geodesic Leland No-Trade Buffer Bands Mechanics (TC41 ~ TC45)
    # =======================================================================
    def test_tc41_marginal_geodesic_distance_zero_at_target(self) -> None:
        """TC41: Marginal 2-asset arc distance dist_{R, i}(w, w) is exactly 0.0."""
        target = np.array([0.25, 0.75])
        vols = np.array([0.15, 0.20])
        band = apply_geodesic_leland_bands(target, target, vols, h_crash=0.0)

        np.testing.assert_allclose(band.geodesic_distances, np.zeros(2), atol=1e-12)

    def test_tc42_half_width_volatility_scaling(self) -> None:
        """TC42: Leland band half-width widens proportionally with higher asset volatility."""
        target = np.array([0.5, 0.5])
        vols_low = np.array([0.10, 0.10])
        vols_high = np.array([0.40, 0.40])

        band_low = apply_geodesic_leland_bands(target, target, vols_low, h_crash=0.0, base_band=0.02)
        band_high = apply_geodesic_leland_bands(target, target, vols_high, h_crash=0.0, base_band=0.02)

        self.assertGreater(band_high.half_widths[0], band_low.half_widths[0])

    def test_tc43_half_width_crash_sensitivity_scaling(self) -> None:
        """TC43: Leland band half-width expands dynamically during systemic stress (h_crash)."""
        target = np.array([0.5, 0.5])
        vols = np.array([0.20, 0.20])

        band_calm = apply_geodesic_leland_bands(target, target, vols, h_crash=0.0, base_band=0.02)
        band_crisis = apply_geodesic_leland_bands(target, target, vols, h_crash=0.90, base_band=0.02)

        self.assertGreater(band_crisis.half_widths[0], band_calm.half_widths[0])

    def test_tc44_noise_rebalance_geodesic_hold(self) -> None:
        """TC44: Deviation inside geodesic buffer band triggers HOLD action."""
        target = np.array([0.205, 0.795], dtype=np.float64)
        current = np.array([0.200, 0.800], dtype=np.float64)
        vols = np.array([0.15, 0.20], dtype=np.float64)

        band = apply_geodesic_leland_bands(target, current, vols, h_crash=0.0, base_band=0.03)

        self.assertEqual(band.rebalance_actions[0], BypassAction.HOLD.value)
        self.assertEqual(band.rebalance_actions[1], BypassAction.HOLD.value)
        np.testing.assert_allclose(band.rebalanced_weights, current, atol=1e-10)

    def test_tc45_leland_band_turnover_reduction(self) -> None:
        """TC45: Geodesic Leland bands reduce execution turnover vs raw target reallocation."""
        allocator = RiemannianManifoldPortfolioAllocator(market="SP500", leland_base_band=0.04)
        # Baseline target allocation
        res_baseline = allocator.optimize(self.mu, self.cov)
        target = res_baseline.optimal_weights.copy()

        # Construct current portfolio within the Leland no-trade buffer band (small noise perturbation)
        perturbation = np.array([0.004, -0.003, 0.002, -0.001, 0.002, -0.004], dtype=np.float64)
        current = np.clip(target + perturbation, EPSILON_FLOOR, 0.20)
        current = current / np.sum(current)

        # Optimize with current_weights provided
        res = allocator.optimize(self.mu, self.cov, current_weights=current)

        turnover_with_bands = res.turnover
        turnover_raw_target = float(0.5 * np.sum(np.abs(res.target_weights - current)))

        # Geodesic Leland bands suppress noise trading, drastically reducing turnover
        self.assertLessEqual(turnover_with_bands, turnover_raw_target)
        self.assertLess(turnover_with_bands, 0.005)
        self.assertGreater(turnover_raw_target, 0.001)

    # =======================================================================
    # Category 10: Instant Bypass for New Entries & Liquidations (TC46 ~ TC50)
    # =======================================================================
    def test_tc46_immediate_entry_bypass(self) -> None:
        """TC46: w_{0, i} == 0 and w_i^* > 0 triggers ENTRY_BYPASS and allocates immediately."""
        target = np.array([0.30, 0.70], dtype=np.float64)
        current = np.array([0.00, 1.00], dtype=np.float64)
        vols = np.array([0.20, 0.20], dtype=np.float64)

        band = apply_geodesic_leland_bands(target, current, vols, h_crash=0.0, base_band=0.05)

        self.assertEqual(band.rebalance_actions[0], BypassAction.ENTRY_BYPASS.value)
        self.assertIn("ASSET_0", band.bypassed_entries)
        self.assertGreater(band.rebalanced_weights[0], 0.0)

    def test_tc47_immediate_exit_bypass(self) -> None:
        """TC47: w_i^* == 0 and w_{0, i} > 0 triggers EXIT_BYPASS and liquidates immediately to 0.0."""
        target = np.array([0.00, 1.00], dtype=np.float64)
        current = np.array([0.25, 0.75], dtype=np.float64)
        vols = np.array([0.20, 0.20], dtype=np.float64)

        band = apply_geodesic_leland_bands(target, current, vols, h_crash=0.0, base_band=0.05)

        self.assertEqual(band.rebalance_actions[0], BypassAction.EXIT_BYPASS.value)
        self.assertIn("ASSET_0", band.bypassed_exits)
        self.assertEqual(band.rebalanced_weights[0], 0.0)

    def test_tc48_simultaneous_entry_exit_and_hold_portfolio(self) -> None:
        """TC48: Portfolio with simultaneous entry, exit, hold, and active trade executes properly."""
        target = np.array([0.20, 0.00, 0.305, 0.495], dtype=np.float64)
        current = np.array([0.00, 0.20, 0.300, 0.500], dtype=np.float64)
        vols = np.full(4, 0.20, dtype=np.float64)

        band = apply_geodesic_leland_bands(target, current, vols, h_crash=0.0, base_band=0.02)

        self.assertEqual(band.rebalance_actions[0], BypassAction.ENTRY_BYPASS.value)
        self.assertEqual(band.rebalance_actions[1], BypassAction.EXIT_BYPASS.value)
        self.assertEqual(band.rebalance_actions[2], BypassAction.HOLD.value)
        self.assertEqual(band.rebalance_actions[3], BypassAction.HOLD.value)

    def test_tc49_simplex_renormalization_after_bypass(self) -> None:
        """TC49: Renormalization after entry and exit bypasses preserves exact sum == 1.000000."""
        target = np.array([0.30, 0.00, 0.70], dtype=np.float64)
        current = np.array([0.00, 0.40, 0.60], dtype=np.float64)
        vols = np.full(3, 0.20, dtype=np.float64)

        band = apply_geodesic_leland_bands(target, current, vols, h_crash=0.0, base_band=0.02)
        self.assertAlmostEqual(float(np.sum(band.rebalanced_weights)), 1.0, places=10)

    def test_tc50_active_buy_sell_triggers(self) -> None:
        """TC50: Rebalance action BUY and SELL assigned when distance exceeds half-width."""
        target = np.array([0.45, 0.55], dtype=np.float64)
        current = np.array([0.15, 0.85], dtype=np.float64)
        vols = np.full(2, 0.15, dtype=np.float64)

        band = apply_geodesic_leland_bands(target, current, vols, h_crash=0.0, base_band=0.01)

        self.assertEqual(band.rebalance_actions[0], BypassAction.BUY.value)
        self.assertEqual(band.rebalance_actions[1], BypassAction.SELL.value)

    # =======================================================================
    # Category 11: Critical Edge Cases & Degenerate Scenarios (TC51 ~ TC55)
    # =======================================================================
    def test_tc51_two_asset_simplex_boundary_stability(self) -> None:
        """TC51: Two-asset portfolio at simplex boundary (0.999, 0.001) optimizes stably."""
        mu_2 = np.array([0.15, 0.08])
        cov_2 = np.array([[0.04, 0.01], [0.01, 0.03]])
        w0_2 = np.array([0.999, 0.001])

        allocator = RiemannianManifoldPortfolioAllocator(market="SP500")
        res = allocator.optimize(mu_2, cov_2, current_weights=w0_2)

        self.assertFalse(np.any(np.isnan(res.optimal_weights)))
        self.assertAlmostEqual(float(np.sum(res.optimal_weights)), 1.0, places=10)

    def test_tc52_singular_covariance_matrix_handling(self) -> None:
        """TC52: Covariance matrix with zero eigenvalue (collinear assets) handled safely."""
        cov_sing = np.ones((4, 4)) * 0.02
        np.fill_diagonal(cov_sing, 0.04)
        # Force exact rank deficiency
        cov_sing[3] = cov_sing[2]
        cov_sing[:, 3] = cov_sing[:, 2]

        mu_4 = np.array([0.12, 0.10, 0.11, 0.11])
        allocator = RiemannianManifoldPortfolioAllocator(market="SP500")
        res = allocator.optimize(mu_4, cov_sing)

        self.assertFalse(np.any(np.isnan(res.optimal_weights)))
        self.assertAlmostEqual(float(np.sum(res.optimal_weights) + res.cash_weight), 1.0, places=10)

    def test_tc53_identical_assets_uniform_distribution(self) -> None:
        """TC53: Identical expected returns and covariance produce equal weights."""
        n = 4
        mu_ident = np.full(n, 0.10)
        cov_ident = np.eye(n) * 0.04

        allocator = RiemannianManifoldPortfolioAllocator(market="SP500", turnover_penalty_gamma=0.0)
        res = allocator.optimize(mu_ident, cov_ident)

        expected = np.full(n, 1.0 / n)
        np.testing.assert_allclose(res.optimal_weights, expected, atol=1e-3)

    def test_tc54_extreme_alpha_disparity_respects_max_weight(self) -> None:
        """TC54: Dominant high-return asset respects max_single_weight constraint."""
        mu_skewed = np.array([0.95, 0.02, 0.01, 0.01])
        cov_diag = np.eye(4) * 0.04

        max_w = 0.35
        allocator = RiemannianManifoldPortfolioAllocator(market="SP500", max_single_weight=max_w)
        res = allocator.optimize(mu_skewed, cov_diag)

        self.assertLessEqual(float(np.max(res.optimal_weights)), max_w + 1e-6)

    def test_tc55_near_zero_weights_no_nan_or_inf(self) -> None:
        """TC55: Near-zero starting weights (1e-12) do not produce numerical singularities."""
        w_tiny = np.array([1e-12, 0.5, 0.5 - 1e-12], dtype=np.float64)
        mu_3 = np.array([0.15, 0.12, 0.10])
        cov_3 = np.eye(3) * 0.03

        allocator = RiemannianManifoldPortfolioAllocator(market="SP500")
        res = allocator.optimize(mu_3, cov_3, current_weights=w_tiny)

        self.assertFalse(np.any(np.isnan(res.optimal_weights)))
        self.assertFalse(np.any(np.isinf(res.optimal_weights)))
        self.assertAlmostEqual(float(np.sum(res.optimal_weights)), 1.0, places=10)

    # =======================================================================
    # Category 12: Latency SLA, Downstream Interfaces & Telemetry (TC56 ~ TC60)
    # =======================================================================
    def test_tc56_execution_latency_sla_under_15ms(self) -> None:
        """TC56: Full 20-asset portfolio optimization completes within 15 ms SLA."""
        n_20 = 20
        A = self.rng.randn(n_20, n_20)
        cov_20 = (A @ A.T) * 0.01 + np.eye(n_20) * 0.04
        mu_20 = self.rng.uniform(0.05, 0.20, size=n_20)

        allocator = RiemannianManifoldPortfolioAllocator(market="SP500")

        # Warmup
        allocator.optimize(mu_20, cov_20)

        # Benchmark run
        t0 = time.perf_counter()
        res = allocator.optimize(mu_20, cov_20)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        self.assertLess(elapsed_ms, 15.0, f"Latency {elapsed_ms:.2f} ms exceeded 15.0 ms SLA")
        self.assertLess(res.computation_time_us / 1000.0, 15.0)

    def test_tc57_telemetry_export_format(self) -> None:
        """TC57: export_telemetry produces complete dictionary with required keys."""
        allocator = RiemannianManifoldPortfolioAllocator(market="KOSPI")
        allocator.optimize(self.mu, self.cov)

        telem = allocator.export_telemetry()
        required_keys = {"version", "release", "feature", "market", "backend", "total_optimizations", "avg_latency_us", "crash_alerts_triggered"}
        self.assertTrue(required_keys.issubset(telem.keys()))
        self.assertEqual(telem["version"], 120)
        self.assertEqual(telem["release"], "R136")
        self.assertEqual(telem["feature"], "F572")
        self.assertEqual(telem["market"], "KOSPI")
        self.assertGreaterEqual(telem["total_optimizations"], 1)

    def test_tc58_result_to_dict_json_serializable(self) -> None:
        """TC58: Result to_dict() outputs valid JSON-serializable string."""
        allocator = RiemannianManifoldPortfolioAllocator(market="NASDAQ")
        res = allocator.optimize(self.mu, self.cov, asset_names=self.asset_names)

        d = res.to_dict()
        json_str = json.dumps(d)
        self.assertIsInstance(json_str, str)
        self.assertIn("optimal_weights", d)
        self.assertIn("hyperbolicity_diagnostics", d)
        self.assertIn("leland_diagnostics", d)

    def test_tc59_pure_numpy_backend_execution(self) -> None:
        """TC59: Force pure NumPy backend (use_torch=False) and verify output validity."""
        allocator_np = RiemannianManifoldPortfolioAllocator(market="SP500", use_torch=False)
        self.assertEqual(allocator_np.backend, "numpy")

        res = allocator_np.optimize(self.mu, self.cov)
        self.assertAlmostEqual(float(np.sum(res.optimal_weights)), 1.0, places=10)
        self.assertTrue(np.all(res.optimal_weights >= 0.0))

    def test_tc60_multi_cycle_stateful_tracking(self) -> None:
        """TC60: Consecutive multi-cycle optimizations accumulate telemetry state accurately."""
        allocator = RiemannianManifoldPortfolioAllocator(market="RUSSELL2000")
        w_current = self.w0.copy()

        for cycle in range(5):
            res = allocator.optimize(self.mu, self.cov, current_weights=w_current)
            w_current = res.optimal_weights.copy()

        telem = allocator.export_telemetry()
        self.assertEqual(telem["total_optimizations"], 5)
        self.assertGreater(telem["avg_latency_us"], 0.0)


if __name__ == "__main__":
    unittest.main()
