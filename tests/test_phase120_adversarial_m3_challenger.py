"""
tests/test_phase120_adversarial_m3_challenger.py
================================================
Adversarial Stress Test Suite for Milestone 3 (Feature F572):
Curvature-Aware Riemannian Manifold Portfolio Allocator & Fisher Information Metric Engine.

Verification & Stress Test Dimensions:
1. Degenerate and Singular Covariance Matrices:
   - Rank-1 collinear covariance matrices
   - Near-zero variance matrices (1e-12 * I)
   - Zero-variance isolated assets (cov[i, i] == 0)
   - Ill-conditioned covariance matrices (cond ~ 1e14)
   - Completely all-zero covariance matrix
   - Singular covariance matrices with linear dependencies
2. 100% Correlation Spike (Systemic Contagion):
   - All-ones correlation matrix (rho_ij == 1.0)
   - Delta-Gromov zero collapse
   - Continuous crash indicator H_crash >= 0.70
   - Systemic tree contagion regime triggering
   - Dynamic cash de-risking and budget preservation
   - Block correlation spikes and negative correlation extremes
3. Extreme Negative Returns & Numerical Scaling:
   - Catastrophic uniform crash returns (mu = -10.0, -1000%)
   - Extreme alpha disparity (one asset -100.0, others +0.05)
   - Huge numerical return scaling (1e8, -1e8)
   - Zero returns (mu == 0)
4. Boundary Simplex Points & High Dimensionality:
   - Corner vertex starting points (w0 = [1.0, 0, 0, ...])
   - Microscopic weights (w_i = 1e-15)
   - Minimal 2-asset simplex boundary points
   - High-dimensional universe (N=100 assets)
5. Strict Mathematical Invariants:
   - Simplex sum sum(w_i) + w_cash == 1.000000
   - Strict non-negativity w_i >= 0.0, w_cash >= 0.0
   - Geodesic distance identity dist_R(w, w) == 0.0
   - Geodesic distance range dist_R in [0, pi]
   - Geodesic distance symmetry and metric triangle inequality
   - Tangent space projection orthogonality sum(grad_R) == 0.0
   - Spherical embedding norm ||xi||_2 == 2.0
6. Instant Entry & Exit Bypass Mechanics:
   - Immediate entry bypass (w_{0, i} == 0 -> w_i = w_i^*)
   - Immediate exit bypass (w_i^* == 0 -> w_i = 0.0)
   - Zero leakage to exited assets during simplex renormalization
   - Simultaneous entry/exit/hold with active cash de-risking
7. Dual-Tree Cryptographic Parity:
   - Bit-for-bit SHA-256 equivalence between src/ and trading_system/src/
"""

import hashlib
import math
import unittest
from pathlib import Path

import numpy as np

from src.risk.riemannian_manifold_portfolio_allocator import (
    CRASH_ALERT_THRESHOLD,
    DEFAULT_MAX_HYPERBOLICITY_SAMPLES,
    EPSILON_FLOOR,
    FEATURE,
    RELEASE,
    VERSION,
    BypassAction,
    CurvatureRegime,
    GeodesicLelandBand,
    HyperbolicityDiagnostics,
    RiemannianAllocatorConfig,
    RiemannianManifoldPortfolioAllocator,
    RiemannianOptimizationResult,
    apply_geodesic_leland_bands,
    compute_gromov_hyperbolicity,
    exponential_retraction,
    fisher_rao_metric_tensor,
    geodesic_distance,
    inverse_spherical_embedding,
    project_tangent_space,
    spherical_embedding,
)


class TestPhase120AdversarialM3Challenger(unittest.TestCase):
    """Adversarial stress test suite for Feature F572."""

    def setUp(self) -> None:
        np.random.seed(42)

    # =======================================================================
    # 1. Degenerate and Singular Covariance Matrices
    # =======================================================================
    def test_adv01_rank_deficient_rank1_covariance(self) -> None:
        """ADV-01: Rank-1 collinear covariance matrix converges with valid simplex weights."""
        n = 6
        v = np.array([0.15, 0.20, 0.25, 0.10, 0.30, 0.18], dtype=np.float64)
        cov_rank1 = np.outer(v, v)  # Rank 1 matrix, 5 zero eigenvalues
        mu = np.array([0.08, 0.12, 0.09, 0.05, 0.14, 0.11], dtype=np.float64)

        allocator = RiemannianManifoldPortfolioAllocator(market="SP500")
        res = allocator.optimize(mu, cov_rank1)

        self.assertTrue(np.all(np.isfinite(res.optimal_weights)))
        self.assertTrue(np.all(res.optimal_weights >= 0.0))
        self.assertAlmostEqual(float(np.sum(res.optimal_weights) + res.cash_weight), 1.0, places=9)
        self.assertTrue(np.isfinite(res.expected_volatility))
        self.assertTrue(np.isfinite(res.sharpe_ratio))

    def test_adv02_near_zero_variance_matrix(self) -> None:
        """ADV-02: Microscopic covariance (1e-12 * I) does not cause numerical division by zero."""
        n = 5
        cov_micro = 1e-12 * np.eye(n, dtype=np.float64)
        mu = np.array([0.05, 0.10, 0.15, 0.20, 0.25], dtype=np.float64)

        allocator = RiemannianManifoldPortfolioAllocator(market="SP500")
        res = allocator.optimize(mu, cov_micro)

        self.assertTrue(np.all(np.isfinite(res.optimal_weights)))
        self.assertTrue(np.all(res.optimal_weights >= 0.0))
        self.assertAlmostEqual(float(np.sum(res.optimal_weights) + res.cash_weight), 1.0, places=9)

    def test_adv03_isolated_zero_variance_assets(self) -> None:
        """ADV-03: Zero-variance diagonal elements (cov[i, i] == 0.0) are safely protected."""
        n = 5
        cov = np.diag([0.0, 0.04, 0.0, 0.09, 0.02]).astype(np.float64)
        mu = np.array([0.02, 0.08, 0.01, 0.12, 0.06], dtype=np.float64)

        allocator = RiemannianManifoldPortfolioAllocator(market="NASDAQ")
        res = allocator.optimize(mu, cov)

        self.assertTrue(np.all(np.isfinite(res.optimal_weights)))
        self.assertTrue(np.all(res.optimal_weights >= 0.0))
        self.assertAlmostEqual(float(np.sum(res.optimal_weights) + res.cash_weight), 1.0, places=9)

    def test_adv04_severely_ill_conditioned_covariance(self) -> None:
        """ADV-04: Covariance matrix with condition number > 1e14 remains numerically stable."""
        n = 5
        # Construct orthogonal Q and extreme eigenvalues from 1e6 to 1e-8
        q, _ = np.linalg.qr(np.random.randn(n, n))
        eigs = np.array([1e6, 1e3, 1.0, 1e-4, 1e-8], dtype=np.float64)
        cov_ill = q @ np.diag(eigs) @ q.T
        cov_ill = 0.5 * (cov_ill + cov_ill.T)  # Ensure exact symmetry
        mu = np.random.uniform(0.01, 0.20, size=n)

        allocator = RiemannianManifoldPortfolioAllocator(market="RUSSELL2000")
        res = allocator.optimize(mu, cov_ill)

        self.assertTrue(np.all(np.isfinite(res.optimal_weights)))
        self.assertTrue(np.all(res.optimal_weights >= 0.0))
        self.assertAlmostEqual(float(np.sum(res.optimal_weights) + res.cash_weight), 1.0, places=9)

    def test_adv05_all_zero_covariance_matrix(self) -> None:
        """ADV-05: Completely zero covariance matrix (pure alpha return optimization)."""
        n = 4
        cov_zero = np.zeros((n, n), dtype=np.float64)
        mu = np.array([0.05, 0.20, 0.10, 0.15], dtype=np.float64)

        allocator = RiemannianManifoldPortfolioAllocator(market="KOSPI")
        res = allocator.optimize(mu, cov_zero)

        self.assertTrue(np.all(np.isfinite(res.optimal_weights)))
        self.assertTrue(np.all(res.optimal_weights >= 0.0))
        self.assertAlmostEqual(float(np.sum(res.optimal_weights) + res.cash_weight), 1.0, places=9)
        # Highest alpha asset (index 1) should receive highest allocation
        self.assertEqual(int(np.argmax(res.optimal_weights)), 1)

    def test_adv06_singular_covariance_with_linear_dependency(self) -> None:
        """ADV-06: Linear dependency (asset 2 = 0.5 * asset 0 + 0.5 * asset 1)."""
        n = 4
        # Base independent factors for asset 0 and 1
        x = np.random.randn(100, 2)
        # Asset 2 is linear combination
        x2 = 0.5 * x[:, 0] + 0.5 * x[:, 1]
        x3 = np.random.randn(100)
        data = np.column_stack([x, x2, x3])
        cov_dep = np.cov(data, rowvar=False)
        mu = np.array([0.07, 0.09, 0.08, 0.06], dtype=np.float64)

        allocator = RiemannianManifoldPortfolioAllocator(market="KOSDAQ")
        res = allocator.optimize(mu, cov_dep)

        self.assertTrue(np.all(np.isfinite(res.optimal_weights)))
        self.assertTrue(np.all(res.optimal_weights >= 0.0))
        self.assertAlmostEqual(float(np.sum(res.optimal_weights) + res.cash_weight), 1.0, places=9)

    # =======================================================================
    # 2. 100% Correlation Spike (Systemic Contagion) & Curvature Extremes
    # =======================================================================
    def test_adv07_systemic_contagion_100_percent_correlation_spike(self) -> None:
        """ADV-07: 100% correlation spike (all rho_ij == 1.0) triggers systemic crash alert and cash buffer."""
        n = 6
        corr_spike = np.ones((n, n), dtype=np.float64)

        diag = compute_gromov_hyperbolicity(
            corr_spike,
            critical_delta=0.25,
            kappa_hyp=15.0,
            cash_de_risk_multiplier=0.50,
        )

        # In 100% correlation, all distance metric values are D_ij = 0.0 -> delta_Gromov = 0.0
        self.assertAlmostEqual(diag.gromov_delta, 0.0, places=6)
        self.assertGreaterEqual(diag.h_crash, 0.70)
        self.assertTrue(diag.is_crash_alert)
        self.assertEqual(diag.curvature_regime, CurvatureRegime.SYSTEMIC_TREE_CONTAGION)
        self.assertGreater(diag.cash_allocation, 0.40)

        # Test within full optimization workflow
        mu = np.full(n, 0.05, dtype=np.float64)
        vols = np.full(n, 0.20, dtype=np.float64)
        cov = np.outer(vols, vols)  # 100% correlated covariance

        allocator = RiemannianManifoldPortfolioAllocator(market="SP500", cash_de_risk_multiplier=0.50)
        res = allocator.optimize(mu, cov, corr_matrix=corr_spike)

        self.assertTrue(res.hyperbolicity_diagnostics.is_crash_alert)
        self.assertGreater(res.cash_weight, 0.40)
        self.assertAlmostEqual(float(np.sum(res.optimal_weights) + res.cash_weight), 1.0, places=9)

    def test_adv08_block_correlation_contagion_structure(self) -> None:
        """ADV-08: Block correlation structure (clique of 4 assets with rho=0.999)."""
        n = 8
        corr = np.eye(n, dtype=np.float64)
        # Block 1: Assets 0, 1, 2, 3 have near 100% correlation
        corr[0:4, 0:4] = 0.999
        np.fill_diagonal(corr, 1.0)

        diag = compute_gromov_hyperbolicity(corr, critical_delta=0.25, max_samples=5000)

        self.assertTrue(np.isfinite(diag.gromov_delta))
        self.assertTrue(np.isfinite(diag.h_crash))
        self.assertGreaterEqual(diag.h_crash, 0.0)
        self.assertLessEqual(diag.h_crash, 1.0)

    def test_adv09_extreme_negative_correlation_bounds(self) -> None:
        """ADV-09: Extreme negative correlation (-1 / (N - 1)) metric geometry."""
        n = 5
        # The lowest mathematically possible uniform off-diagonal correlation for PSD matrix is -1 / (N - 1)
        rho_min = -1.0 / (n - 1)
        corr_neg = np.full((n, n), rho_min, dtype=np.float64)
        np.fill_diagonal(corr_neg, 1.0)

        diag = compute_gromov_hyperbolicity(corr_neg, critical_delta=0.25)
        # In negatively correlated regimes, pairwise distances are large (D_ij = sqrt(2(1 - rho))),
        # yielding flat or spherical non-contagion geometry
        self.assertFalse(diag.is_crash_alert)
        self.assertEqual(diag.cash_allocation, 0.0)

    def test_adv10_small_universe_n2_n3_curvature_handling(self) -> None:
        """ADV-10: Small universes (N=2, 3) where 4-point Gromov condition cannot be formed."""
        for n in [2, 3]:
            corr = np.ones((n, n), dtype=np.float64)
            diag = compute_gromov_hyperbolicity(corr)
            self.assertFalse(diag.is_crash_alert)
            self.assertEqual(diag.cash_allocation, 0.0)
            self.assertEqual(diag.curvature_regime, CurvatureRegime.EUCLIDEAN_FLAT)

    # =======================================================================
    # 3. Extreme Negative Returns & Numerical Scaling
    # =======================================================================
    def test_adv11_catastrophic_uniform_negative_returns(self) -> None:
        """ADV-11: Catastrophic uniform market crash (mu = -10.0, i.e., -1000% returns)."""
        n = 5
        mu_crash = np.full(n, -10.0, dtype=np.float64)
        cov = np.eye(n, dtype=np.float64) * 0.04

        allocator = RiemannianManifoldPortfolioAllocator(market="SP500")
        res = allocator.optimize(mu_crash, cov)

        self.assertTrue(np.all(np.isfinite(res.optimal_weights)))
        self.assertTrue(np.all(res.optimal_weights >= 0.0))
        self.assertAlmostEqual(float(np.sum(res.optimal_weights) + res.cash_weight), 1.0, places=9)

    def test_adv12_extreme_alpha_disparity(self) -> None:
        """ADV-12: Severe alpha disparity (one asset at -100.0, others at +0.05)."""
        n = 5
        mu = np.array([-100.0, 0.05, 0.05, 0.05, 0.05], dtype=np.float64)
        cov = np.eye(n, dtype=np.float64) * 0.04

        allocator = RiemannianManifoldPortfolioAllocator(market="SP500")
        res = allocator.optimize(mu, cov)

        self.assertTrue(np.all(np.isfinite(res.optimal_weights)))
        self.assertTrue(np.all(res.optimal_weights >= 0.0))
        self.assertAlmostEqual(float(np.sum(res.optimal_weights) + res.cash_weight), 1.0, places=9)
        # Toxic asset 0 should be penalized to near-zero allocation
        self.assertLess(res.optimal_weights[0], 0.05)

    def test_adv13_massive_magnitude_returns(self) -> None:
        """ADV-13: Astronomical return magnitudes (1e8, -1e8) protected by log-sum-exp shift."""
        n = 4
        mu = np.array([1e8, -1e8, 1e7, -1e7], dtype=np.float64)
        cov = np.eye(n, dtype=np.float64) * 0.04

        allocator = RiemannianManifoldPortfolioAllocator(market="NASDAQ")
        res = allocator.optimize(mu, cov)

        self.assertTrue(np.all(np.isfinite(res.optimal_weights)))
        self.assertTrue(np.all(res.optimal_weights >= 0.0))
        self.assertAlmostEqual(float(np.sum(res.optimal_weights) + res.cash_weight), 1.0, places=9)

    def test_adv14_pure_zero_returns(self) -> None:
        """ADV-14: Exactly zero returns (mu == 0) performs pure risk-minimization."""
        n = 4
        mu_zero = np.zeros(n, dtype=np.float64)
        # Variances: 0.01, 0.04, 0.09, 0.16
        cov = np.diag([0.01, 0.04, 0.09, 0.16]).astype(np.float64)

        allocator = RiemannianManifoldPortfolioAllocator(market="SP500")
        res = allocator.optimize(mu_zero, cov)

        self.assertTrue(np.all(np.isfinite(res.optimal_weights)))
        self.assertTrue(np.all(res.optimal_weights >= 0.0))
        self.assertAlmostEqual(float(np.sum(res.optimal_weights) + res.cash_weight), 1.0, places=9)
        # Lowest variance asset (index 0) must have the highest weight
        self.assertGreater(res.optimal_weights[0], res.optimal_weights[1])
        self.assertGreater(res.optimal_weights[1], res.optimal_weights[2])
        self.assertGreater(res.optimal_weights[2], res.optimal_weights[3])

    def test_adv15_extreme_risk_aversion_values(self) -> None:
        """ADV-15: Risk aversion parameter at extreme boundaries (gamma=0.0 and gamma=1000.0)."""
        n = 4
        mu = np.array([0.15, 0.05, 0.08, 0.02], dtype=np.float64)
        cov = np.diag([0.16, 0.01, 0.04, 0.005]).astype(np.float64)

        # gamma = 0.0: Pure return chasing
        alloc_zero = RiemannianManifoldPortfolioAllocator(market="SP500", risk_aversion=0.0)
        res_zero = alloc_zero.optimize(mu, cov)
        self.assertAlmostEqual(float(np.sum(res_zero.optimal_weights) + res_zero.cash_weight), 1.0, places=9)

        # gamma = 1000.0: Extreme variance aversion
        alloc_high = RiemannianManifoldPortfolioAllocator(market="SP500", risk_aversion=1000.0)
        res_high = alloc_high.optimize(mu, cov)
        self.assertAlmostEqual(float(np.sum(res_high.optimal_weights) + res_high.cash_weight), 1.0, places=9)
        # Safest asset (index 3) should have highest allocation under gamma=1000.0
        self.assertEqual(int(np.argmax(res_high.optimal_weights)), 3)

    # =======================================================================
    # 4. Boundary Simplex Points & High Dimensionality
    # =======================================================================
    def test_adv16_corner_vertex_starting_allocation(self) -> None:
        """ADV-16: Optimization starting from a corner simplex vertex (w0 = [1.0, 0, 0, ...])."""
        n = 5
        w0_corner = np.array([1.0, 0.0, 0.0, 0.0, 0.0], dtype=np.float64)
        mu = np.array([0.02, 0.15, 0.12, 0.10, 0.08], dtype=np.float64)
        cov = np.eye(n, dtype=np.float64) * 0.04

        allocator = RiemannianManifoldPortfolioAllocator(market="SP500", turnover_penalty_gamma=0.05)
        res = allocator.optimize(mu, cov, current_weights=w0_corner)

        self.assertTrue(np.all(np.isfinite(res.optimal_weights)))
        self.assertTrue(np.all(res.optimal_weights >= 0.0))
        self.assertAlmostEqual(float(np.sum(res.optimal_weights) + res.cash_weight), 1.0, places=9)

    def test_adv17_microscopic_weights_numerical_floor(self) -> None:
        """ADV-17: Microscopic weights (1e-15) gracefully handled by EPSILON_FLOOR."""
        w_micro = np.array([1e-15, 1e-15, 1.0 - 4e-15, 1e-15, 1e-15], dtype=np.float64)
        xi = spherical_embedding(w_micro)
        self.assertTrue(np.all(np.isfinite(xi)))
        self.assertAlmostEqual(float(np.linalg.norm(xi)), 2.0, places=9)

        w_rec = inverse_spherical_embedding(xi)
        self.assertTrue(np.all(np.isfinite(w_rec)))
        self.assertAlmostEqual(float(np.sum(w_rec)), 1.0, places=9)

    def test_adv18_two_asset_simplex_boundary_extremes(self) -> None:
        """ADV-18: 2-asset simplex boundary points [0, 1] and [1, 0]."""
        allocator = RiemannianManifoldPortfolioAllocator(market="SP500")
        mu = np.array([0.10, 0.02], dtype=np.float64)
        cov = np.eye(2, dtype=np.float64) * 0.04

        res1 = allocator.optimize(mu, cov, current_weights=np.array([1.0, 0.0]))
        self.assertAlmostEqual(float(np.sum(res1.optimal_weights) + res1.cash_weight), 1.0, places=9)

        res2 = allocator.optimize(mu, cov, current_weights=np.array([0.0, 1.0]))
        self.assertAlmostEqual(float(np.sum(res2.optimal_weights) + res2.cash_weight), 1.0, places=9)

    def test_adv19_high_dimensional_universe_stress_n100(self) -> None:
        """ADV-19: High-dimensional 100-asset universe evaluates within latency bounds without OOM."""
        n = 100
        rng = np.random.RandomState(42)
        mu = rng.uniform(-0.05, 0.15, size=n)
        vols = rng.uniform(0.10, 0.40, size=n)
        corr = np.eye(n) + 0.10 * (np.ones((n, n)) - np.eye(n))
        cov = np.outer(vols, vols) * corr

        allocator = RiemannianManifoldPortfolioAllocator(
            market="SP500",
            max_hyperbolicity_samples=250,
            max_iterations=100,
        )
        res = allocator.optimize(mu, cov)

        self.assertEqual(len(res.optimal_weights), n)
        self.assertTrue(np.all(res.optimal_weights >= 0.0))
        self.assertAlmostEqual(float(np.sum(res.optimal_weights) + res.cash_weight), 1.0, places=8)

    # =======================================================================
    # 5. Strict Mathematical Invariants
    # =======================================================================
    def test_adv20_strict_simplex_sum_across_100_random_trials(self) -> None:
        """ADV-20: sum(w_i) + w_cash == 1.000000 holds across 100 diverse random test cases."""
        allocator = RiemannianManifoldPortfolioAllocator(market="SP500")
        rng = np.random.RandomState(12345)

        for trial in range(100):
            n = rng.randint(4, 15)
            mu = rng.uniform(-0.5, 0.5, size=n)
            a = rng.randn(n, n)
            cov = a @ a.T + 1e-4 * np.eye(n)
            w0 = rng.uniform(0.0, 1.0, size=n)
            w0 = w0 / np.sum(w0)

            res = allocator.optimize(mu, cov, current_weights=w0)
            total = float(np.sum(res.optimal_weights) + res.cash_weight)
            self.assertAlmostEqual(total, 1.0, places=9, msg=f"Trial {trial} failed simplex sum: {total}")
            self.assertTrue(np.all(res.optimal_weights >= -1e-12), msg=f"Trial {trial} negative weight")

    def test_adv21_geodesic_distance_mathematical_axioms(self) -> None:
        """ADV-21: Geodesic distance strictly satisfies all metric axioms (identity, symmetry, bounds, triangle inequality)."""
        rng = np.random.RandomState(999)
        n = 8

        # Orthogonal extreme distance test
        w_orth1 = np.array([1.0] + [0.0] * (n - 1), dtype=np.float64)
        w_orth2 = np.array([0.0, 1.0] + [0.0] * (n - 2), dtype=np.float64)
        d_orth = geodesic_distance(w_orth1, w_orth2)
        self.assertAlmostEqual(d_orth, math.pi, places=9)

        # 50 random triples for metric axioms
        for _ in range(50):
            a = rng.uniform(0.01, 1.0, size=n)
            a = a / np.sum(a)
            b = rng.uniform(0.01, 1.0, size=n)
            b = b / np.sum(b)
            c = rng.uniform(0.01, 1.0, size=n)
            c = c / np.sum(c)

            # Axiom 1: Identity
            self.assertEqual(geodesic_distance(a, a), 0.0)

            # Axiom 2: Range [0, pi]
            d_ab = geodesic_distance(a, b)
            self.assertGreaterEqual(d_ab, 0.0)
            self.assertLessEqual(d_ab, math.pi + 1e-12)

            # Axiom 3: Symmetry
            d_ba = geodesic_distance(b, a)
            self.assertAlmostEqual(d_ab, d_ba, places=12)

            # Axiom 4: Triangle Inequality: d(a, c) <= d(a, b) + d(b, c)
            d_ac = geodesic_distance(a, c)
            d_bc = geodesic_distance(b, c)
            self.assertLessEqual(d_ac, d_ab + d_bc + 1e-12)

    def test_adv22_tangent_space_projection_exact_zero_sum(self) -> None:
        """ADV-22: Riemannian gradient tangent space projection strictly satisfies sum(grad_R) == 0.0."""
        rng = np.random.RandomState(777)
        for _ in range(50):
            n = rng.randint(4, 20)
            w = rng.uniform(0.01, 1.0, size=n)
            w = w / np.sum(w)
            grad_euclid = rng.randn(n)

            grad_r = project_tangent_space(grad_euclid, w)
            sum_grad_r = float(np.sum(grad_r))
            self.assertAlmostEqual(sum_grad_r, 0.0, places=12)

    def test_adv23_spherical_embedding_exact_isometry(self) -> None:
        """ADV-23: Under xi_i = 2 * sqrt(w_i), ||xi||_2 == 2.00000000 strictly."""
        rng = np.random.RandomState(888)
        for _ in range(50):
            n = rng.randint(3, 25)
            w = rng.uniform(0.0, 1.0, size=n)
            w = w / np.sum(w)

            xi = spherical_embedding(w)
            norm_xi = float(np.linalg.norm(xi))
            self.assertAlmostEqual(norm_xi, 2.0, places=10)

    # =======================================================================
    # 6. Instant Entry & Exit Bypass Mechanics
    # =======================================================================
    def test_adv24_pure_immediate_entry_bypass(self) -> None:
        """ADV-24: Brand new positions (w_{0, i} == 0) trigger ENTRY_BYPASS and receive allocation."""
        target = np.array([0.25, 0.25, 0.25, 0.25], dtype=np.float64)
        current = np.array([0.00, 0.00, 0.00, 0.00], dtype=np.float64)
        vols = np.full(4, 0.20, dtype=np.float64)

        band = apply_geodesic_leland_bands(target, current, vols, h_crash=0.0, base_band=0.05)

        for i in range(4):
            self.assertEqual(band.rebalance_actions[i], BypassAction.ENTRY_BYPASS.value)
            self.assertGreater(band.rebalanced_weights[i], 0.20)
        self.assertAlmostEqual(float(np.sum(band.rebalanced_weights)), 1.0, places=9)

    def test_adv25_pure_immediate_exit_bypass_exact_zero_leakage(self) -> None:
        """ADV-25: Complete liquidation (w_i^* == 0) triggers EXIT_BYPASS and yields strictly 0.000000."""
        target = np.array([0.00, 0.50, 0.00, 0.50], dtype=np.float64)
        current = np.array([0.30, 0.20, 0.25, 0.25], dtype=np.float64)
        vols = np.full(4, 0.20, dtype=np.float64)

        band = apply_geodesic_leland_bands(target, current, vols, h_crash=0.0, base_band=0.05)

        self.assertEqual(band.rebalance_actions[0], BypassAction.EXIT_BYPASS.value)
        self.assertEqual(band.rebalance_actions[2], BypassAction.EXIT_BYPASS.value)
        # Liquidated positions must be strictly 0.0 with zero leaked residual
        self.assertEqual(band.rebalanced_weights[0], 0.0)
        self.assertEqual(band.rebalanced_weights[2], 0.0)
        self.assertAlmostEqual(float(np.sum(band.rebalanced_weights)), 1.0, places=9)

    def test_adv26_simultaneous_bypass_with_cash_de_risking(self) -> None:
        """ADV-26: Simultaneous entry, exit, hold, and active trade under 30% cash de-risking."""
        target = np.array([0.20, 0.00, 0.301, 0.499], dtype=np.float64)
        current = np.array([0.00, 0.20, 0.300, 0.500], dtype=np.float64)
        vols = np.full(4, 0.20, dtype=np.float64)
        cash_alloc = 0.30

        band = apply_geodesic_leland_bands(
            target, current, vols, h_crash=0.80, base_band=0.03, cash_allocation=cash_alloc
        )

        self.assertEqual(band.rebalance_actions[0], BypassAction.ENTRY_BYPASS.value)
        self.assertEqual(band.rebalance_actions[1], BypassAction.EXIT_BYPASS.value)
        self.assertEqual(band.rebalance_actions[2], BypassAction.HOLD.value)
        self.assertEqual(band.rebalance_actions[3], BypassAction.HOLD.value)

        # Exited asset must be exactly 0.0
        self.assertEqual(band.rebalanced_weights[1], 0.0)
        # Total portfolio budget (risky + cash) must equal 1.000000
        total_budget = float(np.sum(band.rebalanced_weights) + cash_alloc)
        self.assertAlmostEqual(total_budget, 1.0, places=9)

    # =======================================================================
    # 7. Dual-Tree Cryptographic Parity Verification
    # =======================================================================
    def test_adv27_dual_tree_sha256_cryptographic_parity(self) -> None:
        """ADV-27: Primary and mirrored allocator files exhibit bit-for-bit SHA-256 parity."""
        p_primary = Path("src/risk/riemannian_manifold_portfolio_allocator.py")
        p_mirror = Path("trading_system/src/risk/riemannian_manifold_portfolio_allocator.py")

        self.assertTrue(p_primary.exists(), f"Missing primary file: {p_primary}")
        self.assertTrue(p_mirror.exists(), f"Missing mirror file: {p_mirror}")

        hash_prim = hashlib.sha256(p_primary.read_bytes()).hexdigest()
        hash_mirr = hashlib.sha256(p_mirror.read_bytes()).hexdigest()

        self.assertEqual(hash_prim, hash_mirr, "Dual-tree SHA-256 hash mismatch!")


if __name__ == "__main__":
    unittest.main()
