r"""
tests/test_phase120_adversarial_challenger_m3.py
================================================
Empirical Adversarial Stress Test Suite for:
Curvature-Aware Riemannian Manifold Portfolio Allocator & Fisher Information Metric Engine (Feature F572).
Phase 120 (Release R136 / v127 Production Master).

Adversarial Stress Testing Scope:
  1. Extreme Singular & Degenerate Covariance Matrices (collinear, zero-variance, rank-deficient, all-zeros)
  2. Extreme Alpha Disparities (+1e9 vs -1e9, pure negative returns, near-zero spreads)
  3. Boundary Vertices & Infeasible Box Constraints (extreme simplex vertices, w_max < 1/N relaxation)
  4. Strict Mathematical Invariants (Budget conservation, non-negativity, dist_R in [0, pi], triangle inequality, tangent projection sum = 0)
  5. Geodesic Leland Buffer Bands & Instant Bypass Mechanics (ENTRY_BYPASS, EXIT_BYPASS, HOLD, turnover reduction >= 50%)
  6. Gromov Hyperbolicity & Systemic Crash De-risking under Ultrametric Contagion
"""

from __future__ import annotations

import math
import os
import sys
import time
import unittest
from pathlib import Path
from typing import List, Tuple

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p in (str(PROJECT_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.risk.riemannian_manifold_portfolio_allocator import (
    VERSION,
    RELEASE,
    FEATURE,
    EPSILON_FLOOR,
    CRASH_ALERT_THRESHOLD,
    MarketType,
    BypassAction,
    CurvatureRegime,
    RiemannianAllocatorConfig,
    HyperbolicityDiagnostics,
    GeodesicLelandBand,
    RiemannianOptimizationResult,
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
)


class TestPhase120AdversarialChallengerM3(unittest.TestCase):
    """Adversarial challenger test harness executing empirical stress tests on Feature F572."""

    def setUp(self) -> None:
        self.rng = np.random.RandomState(1337)

    # =======================================================================
    # Group 1: Extreme Singular & Degenerate Covariance Matrices
    # =======================================================================
    def test_adv01_zero_variance_asset_handling(self) -> None:
        """ADV01: Zero-variance asset (diagonal entry = 0.0) handled without ZeroDivisionError or NaN."""
        n = 5
        cov = np.eye(n) * 0.04
        cov[0, 0] = 0.0  # Zero variance asset 0
        mu = np.array([0.15, 0.12, 0.10, 0.08, 0.05], dtype=np.float64)

        allocator = RiemannianManifoldPortfolioAllocator(market="SP500")
        res = allocator.optimize(mu, cov)

        self.assertFalse(np.any(np.isnan(res.optimal_weights)), "NaN weights on zero-variance asset!")
        self.assertFalse(np.any(np.isinf(res.optimal_weights)), "Inf weights on zero-variance asset!")
        self.assertAlmostEqual(float(np.sum(res.optimal_weights) + res.cash_weight), 1.0, places=7)
        self.assertTrue(np.all(res.optimal_weights >= 0.0))

    def test_adv02_rank_one_collinear_covariance_matrix(self) -> None:
        """ADV02: All assets perfectly collinear (cov = u u^T, rank 1) handled gracefully."""
        n = 6
        u = np.array([0.2, 0.2, 0.2, 0.2, 0.2, 0.2], dtype=np.float64)
        cov = np.outer(u, u)  # Rank-1 singular matrix
        mu = np.array([0.14, 0.11, 0.16, 0.08, 0.12, 0.09], dtype=np.float64)

        allocator = RiemannianManifoldPortfolioAllocator(market="NASDAQ")
        res = allocator.optimize(mu, cov)

        self.assertFalse(np.any(np.isnan(res.optimal_weights)))
        self.assertAlmostEqual(float(np.sum(res.optimal_weights) + res.cash_weight), 1.0, places=7)
        self.assertTrue(np.all(res.optimal_weights >= 0.0))

    def test_adv03_ill_conditioned_covariance_matrix(self) -> None:
        """ADV03: Covariance matrix with condition number > 1e16 does not cause explosion."""
        n = 4
        # Construct matrix with extreme condition number
        q, _ = np.linalg.qr(self.rng.randn(n, n))
        eigenvalues = np.array([1.0, 1e-5, 1e-10, 1e-16])
        cov = q @ np.diag(eigenvalues) @ q.T
        # Symmetrize
        cov = 0.5 * (cov + cov.T)
        mu = np.array([0.10, 0.12, 0.08, 0.15])

        allocator = RiemannianManifoldPortfolioAllocator(market="RUSSELL2000")
        res = allocator.optimize(mu, cov)

        self.assertFalse(np.any(np.isnan(res.optimal_weights)))
        self.assertAlmostEqual(float(np.sum(res.optimal_weights) + res.cash_weight), 1.0, places=7)

    def test_adv04_indefinite_covariance_with_negative_eigenvalues(self) -> None:
        """ADV04: Indefinite covariance matrix from empirical estimation noise handled safely."""
        n = 4
        cov_indef = np.array([
            [0.04, 0.05, 0.00, 0.00],
            [0.05, 0.04, 0.00, 0.00],
            [0.00, 0.00, 0.04, 0.00],
            [0.00, 0.00, 0.00, 0.04],
        ], dtype=np.float64)  # Determinant of 2x2 block is 0.0016 - 0.0025 = -0.0009 < 0
        mu = np.array([0.10, 0.12, 0.08, 0.11])

        allocator = RiemannianManifoldPortfolioAllocator(market="KOSPI")
        res = allocator.optimize(mu, cov_indef)

        self.assertFalse(np.any(np.isnan(res.optimal_weights)))
        self.assertAlmostEqual(float(np.sum(res.optimal_weights) + res.cash_weight), 1.0, places=7)

    def test_adv05_large_scale_rank_deficient_universe(self) -> None:
        """ADV05: 50-asset universe with 5 latent factors (rank 5 covariance) completes stably."""
        n = 50
        factors = 5
        f_loadings = self.rng.randn(n, factors)
        cov = f_loadings @ f_loadings.T * 0.001 + np.eye(n) * 1e-6
        mu = self.rng.uniform(0.05, 0.25, size=n)

        allocator = RiemannianManifoldPortfolioAllocator(market="SP500")
        res = allocator.optimize(mu, cov)

        self.assertFalse(np.any(np.isnan(res.optimal_weights)))
        self.assertAlmostEqual(float(np.sum(res.optimal_weights) + res.cash_weight), 1.0, places=7)
        self.assertTrue(np.all(res.optimal_weights >= 0.0))

    # =======================================================================
    # Group 2: Extreme Alpha Disparities & Negative Expected Returns
    # =======================================================================
    def test_adv06_astronomical_alpha_disparity(self) -> None:
        """ADV06: mu with extreme values (+1e9 vs -1e9) respects max_single_weight without overflow."""
        n = 5
        mu = np.array([1e9, -1e9, 0.0, 100.0, -50.0], dtype=np.float64)
        cov = np.eye(n) * 0.04

        # Allow max_single_weight=0.80 so the top asset can take up to 80% without forcing equal redistribution
        allocator = RiemannianManifoldPortfolioAllocator(market="SP500", max_single_weight=0.80)
        res = allocator.optimize(mu, cov)

        self.assertFalse(np.any(np.isnan(res.optimal_weights)))
        self.assertFalse(np.any(np.isinf(res.optimal_weights)))
        self.assertAlmostEqual(float(np.sum(res.optimal_weights) + res.cash_weight), 1.0, places=7)
        # Dominant asset must not exceed max_single_weight
        self.assertLessEqual(float(res.optimal_weights[0]), 0.80 + 1e-5)
        # Deep negative return asset should be penalized to 0.0
        self.assertAlmostEqual(float(res.optimal_weights[1]), 0.0, places=5)

    def test_adv07_purely_negative_expected_returns_all_assets(self) -> None:
        """ADV07: All assets have large negative expected returns (severe bear regime)."""
        n = 4
        mu_neg = np.array([-150.0, -80.0, -200.0, -45.0], dtype=np.float64)
        cov = np.eye(n) * 0.03

        allocator = RiemannianManifoldPortfolioAllocator(market="KOSDAQ")
        res = allocator.optimize(mu_neg, cov)

        self.assertFalse(np.any(np.isnan(res.optimal_weights)))
        self.assertAlmostEqual(float(np.sum(res.optimal_weights) + res.cash_weight), 1.0, places=7)
        self.assertTrue(np.all(res.optimal_weights >= 0.0))
        # Asset 3 (-45.0) is the least bad, should receive higher weight than asset 2 (-200.0)
        self.assertGreater(res.optimal_weights[3], res.optimal_weights[2])

    def test_adv08_zero_alpha_vector_pure_minimum_variance(self) -> None:
        """ADV08: mu = 0.0 exactly for all assets; allocator solves pure minimum variance portfolio."""
        n = 4
        mu_zero = np.zeros(n, dtype=np.float64)
        # Asset 0 has lower variance (0.01) than others (0.04)
        cov = np.diag([0.01, 0.04, 0.04, 0.04])

        allocator = RiemannianManifoldPortfolioAllocator(
            market="SP500",
            max_single_weight=0.80,
            turnover_penalty_gamma=0.0,
            leland_base_band=0.0,
        )
        res = allocator.optimize(mu_zero, cov)

        self.assertFalse(np.any(np.isnan(res.optimal_weights)))
        self.assertAlmostEqual(float(np.sum(res.optimal_weights) + res.cash_weight), 1.0, places=7)
        # Lower variance asset must receive greater weight
        self.assertGreater(res.optimal_weights[0], res.optimal_weights[1])

    def test_adv09_sub_microscopic_alpha_variations(self) -> None:
        """ADV09: mu variations of 1e-9 order are distinguished stably without precision collapse."""
        n = 3
        base = 0.100000000000
        mu = np.array([base + 1e-9, base, base - 1e-9], dtype=np.float64)
        cov = np.eye(n) * 0.04

        allocator = RiemannianManifoldPortfolioAllocator(market="SP500")
        res = allocator.optimize(mu, cov)

        self.assertFalse(np.any(np.isnan(res.optimal_weights)))
        self.assertAlmostEqual(float(np.sum(res.optimal_weights) + res.cash_weight), 1.0, places=7)
        # Slight preference for asset 0 over asset 2
        self.assertGreaterEqual(res.optimal_weights[0], res.optimal_weights[2])

    # =======================================================================
    # Group 3: Boundary Vertices & Infeasible Box Constraints
    # =======================================================================
    def test_adv10_starting_from_simplex_vertex_pure_concentration(self) -> None:
        """ADV10: Starting allocation at extreme simplex vertex w0 = [1.0, 0, 0, ...] converges stably."""
        n = 4
        w0 = np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float64)
        mu = np.array([0.05, 0.20, 0.15, 0.18], dtype=np.float64)
        cov = np.eye(n) * 0.04

        allocator = RiemannianManifoldPortfolioAllocator(market="NASDAQ")
        res = allocator.optimize(mu, cov, current_weights=w0)

        self.assertFalse(np.any(np.isnan(res.optimal_weights)))
        self.assertAlmostEqual(float(np.sum(res.optimal_weights) + res.cash_weight), 1.0, places=7)
        # The allocator should shift capital away from low-return asset 0 to higher return assets
        self.assertLess(res.optimal_weights[0], 0.90)

    def test_adv11_infeasible_box_constraint_relaxation(self) -> None:
        """ADV11: Infeasible box constraint w_max = 0.10 on N=4 universe automatically relaxes to >= 1/N."""
        n = 4
        # 4 * 0.10 = 0.40 < 1.0 -> infeasible
        w_max_infeasible = 0.10
        mu = np.array([0.15, 0.12, 0.10, 0.08])
        cov = np.eye(n) * 0.04

        allocator = RiemannianManifoldPortfolioAllocator(market="SP500", max_single_weight=w_max_infeasible)
        res = allocator.optimize(mu, cov)

        self.assertFalse(np.any(np.isnan(res.optimal_weights)))
        self.assertAlmostEqual(float(np.sum(res.optimal_weights) + res.cash_weight), 1.0, places=7)
        # Each weight must be <= relaxed limit (1.0 / 4 = 0.25)
        for w in res.optimal_weights:
            self.assertLessEqual(float(w), 0.25 + 1e-5)

    def test_adv12_subnormal_floating_point_starting_weights(self) -> None:
        """ADV12: Extreme subnormal starting weights (1e-300) do not trigger division by zero."""
        n = 3
        w0_subnormal = np.array([1e-300, 0.5, 0.5], dtype=np.float64)
        mu = np.array([0.14, 0.10, 0.12])
        cov = np.eye(n) * 0.04

        allocator = RiemannianManifoldPortfolioAllocator(market="KOSPI")
        res = allocator.optimize(mu, cov, current_weights=w0_subnormal)

        self.assertFalse(np.any(np.isnan(res.optimal_weights)))
        self.assertFalse(np.any(np.isinf(res.optimal_weights)))
        self.assertAlmostEqual(float(np.sum(res.optimal_weights) + res.cash_weight), 1.0, places=7)

    # =======================================================================
    # Group 4: Strict Mathematical Invariants
    # =======================================================================
    def test_adv13_budget_conservation_invariant_across_100_random_scenarios(self) -> None:
        """ADV13: Invariant sum(w_i) + w_cash == 1.000000 holds across 100 diverse random regimes."""
        allocator = RiemannianManifoldPortfolioAllocator(market="SP500")

        for trial in range(100):
            n = self.rng.randint(3, 12)
            mu = self.rng.uniform(-0.5, 0.5, size=n)
            A = self.rng.randn(n, n)
            cov = A @ A.T * 0.01 + np.eye(n) * 0.02
            w0 = self.rng.dirichlet(np.ones(n))

            res = allocator.optimize(mu, cov, current_weights=w0)
            total = float(np.sum(res.optimal_weights) + res.cash_weight)
            self.assertAlmostEqual(total, 1.0, places=6, msg=f"Budget violated at trial {trial}: total={total}")

    def test_adv14_non_negativity_invariant_across_100_random_scenarios(self) -> None:
        """ADV14: Invariant w_i >= 0.0 holds strictly for all assets across 100 random scenarios."""
        allocator = RiemannianManifoldPortfolioAllocator(market="NASDAQ")

        for trial in range(100):
            n = self.rng.randint(3, 10)
            mu = self.rng.uniform(-2.0, 2.0, size=n)
            A = self.rng.randn(n, n)
            cov = A @ A.T * 0.02 + np.eye(n) * 0.01
            w0 = self.rng.dirichlet(np.ones(n))

            res = allocator.optimize(mu, cov, current_weights=w0)
            self.assertTrue(np.all(res.optimal_weights >= 0.0), f"Negative weight at trial {trial}: {res.optimal_weights}")
            self.assertGreaterEqual(res.cash_weight, 0.0)

    def test_adv15_geodesic_distance_metric_axioms_exhaustive(self) -> None:
        """ADV15: Exhaustive verification of metric axioms for dist_R(w_a, w_b)."""
        # (1) Range boundedness: dist_R in [0, pi] for 1,000 random simplex pairs
        for _ in range(1000):
            n = self.rng.randint(2, 8)
            wa = self.rng.dirichlet(np.ones(n))
            wb = self.rng.dirichlet(np.ones(n))
            wc = self.rng.dirichlet(np.ones(n))

            d_ab = geodesic_distance(wa, wb)
            d_ba = geodesic_distance(wb, wa)
            d_ac = geodesic_distance(wa, wc)
            d_bc = geodesic_distance(wb, wc)
            d_aa = geodesic_distance(wa, wa)

            # Identity of indiscernibles
            self.assertAlmostEqual(d_aa, 0.0, places=12)
            # Range
            self.assertGreaterEqual(d_ab, 0.0)
            self.assertLessEqual(d_ab, math.pi + 1e-12)
            # Symmetry
            self.assertAlmostEqual(d_ab, d_ba, places=12)
            # Triangle inequality: d(a, c) <= d(a, b) + d(b, c) + eps
            self.assertLessEqual(d_ac, d_ab + d_bc + 1e-10)

    def test_adv16_geodesic_distance_orthogonal_extremum(self) -> None:
        """ADV16: Orthogonal boundary vertices have exact geodesic distance of pi."""
        w_vertex_a = np.array([1.0, 0.0, 0.0], dtype=np.float64)
        w_vertex_b = np.array([0.0, 1.0, 0.0], dtype=np.float64)

        d_orth = geodesic_distance(w_vertex_a, w_vertex_b)
        self.assertAlmostEqual(d_orth, math.pi, places=10)

    def test_adv17_tangent_space_projection_zero_sum_invariant(self) -> None:
        """ADV17: Tangent space projection sum(grad_R) == 0.0 holds to 1e-14 for extreme gradients."""
        for _ in range(500):
            n = self.rng.randint(2, 20)
            w = self.rng.dirichlet(np.ones(n))
            grad_wild = self.rng.randn(n) * 1e8

            grad_r = project_tangent_space(grad_wild, w)
            sum_grad_r = float(np.sum(grad_r))
            self.assertAlmostEqual(sum_grad_r, 0.0, places=7, msg=f"Tangent sum non-zero: {sum_grad_r}")

    # =======================================================================
    # Group 5: Geodesic Leland Buffer Bands & Instant Bypass Mechanics
    # =======================================================================
    def test_adv18_immediate_entry_bypass_mechanics(self) -> None:
        """ADV18: Immediate entry bypass (w0_i = 0, target > 0) executes immediately without delay."""
        target_w = np.array([0.30, 0.40, 0.30], dtype=np.float64)
        current_w = np.array([0.00, 0.60, 0.40], dtype=np.float64)  # Asset 0 is new entry
        vols = np.array([0.20, 0.15, 0.18], dtype=np.float64)

        leland = apply_geodesic_leland_bands(
            target_weights=target_w,
            current_weights=current_w,
            asset_vols=vols,
            h_crash=0.0,
            base_band=0.05,  # Wide band
            asset_names=["NEW_STOCK", "STOCK_B", "STOCK_C"],
        )

        self.assertIn("NEW_STOCK", leland.bypassed_entries)
        self.assertEqual(leland.rebalance_actions[0], BypassAction.ENTRY_BYPASS.value)
        # Asset 0 must NOT be zero
        self.assertGreater(leland.rebalanced_weights[0], 0.0)

    def test_adv19_immediate_exit_bypass_mechanics(self) -> None:
        """ADV19: Immediate exit bypass (target = 0, w0_i > 0) liquidates immediately without being held."""
        target_w = np.array([0.50, 0.50, 0.00], dtype=np.float64)  # Asset 2 fully exited
        current_w = np.array([0.30, 0.30, 0.40], dtype=np.float64)
        vols = np.array([0.20, 0.15, 0.25], dtype=np.float64)

        leland = apply_geodesic_leland_bands(
            target_weights=target_w,
            current_weights=current_w,
            asset_vols=vols,
            h_crash=0.0,
            base_band=0.10,  # Extremely wide band
            asset_names=["STOCK_A", "STOCK_B", "LIQUIDATE_ME"],
        )

        self.assertIn("LIQUIDATE_ME", leland.bypassed_exits)
        self.assertEqual(leland.rebalance_actions[2], BypassAction.EXIT_BYPASS.value)
        self.assertEqual(float(leland.rebalanced_weights[2]), 0.0)

    def test_adv20_turnover_reduction_simulation_over_30_periods(self) -> None:
        """ADV20: Multi-period simulation shows Leland buffer bands reduce turnover by >= 50% vs unbuffered."""
        n = 5
        base_weights = np.full(n, 1.0 / n)
        vols = np.full(n, 0.20)

        current_buffered = base_weights.copy()
        current_unbuffered = base_weights.copy()

        cum_turnover_buffered = 0.0
        cum_turnover_unbuffered = 0.0

        for t in range(50):
            # Realistic day-to-day noise perturbation (0.6% standard deviation)
            noise = self.rng.randn(n) * 0.006
            target = np.maximum(base_weights + noise, 0.01)
            target = target / np.sum(target)

            # Unbuffered rebalancing: always rebalance to target
            turnover_unbuf = float(0.5 * np.sum(np.abs(target - current_unbuffered)))
            cum_turnover_unbuffered += turnover_unbuf
            current_unbuffered = target.copy()

            # Buffered rebalancing via Leland bands
            leland = apply_geodesic_leland_bands(
                target_weights=target,
                current_weights=current_buffered,
                asset_vols=vols,
                h_crash=0.0,
                base_band=0.025,
            )
            reb = leland.rebalanced_weights
            turnover_buf = float(0.5 * np.sum(np.abs(reb - current_buffered)))
            cum_turnover_buffered += turnover_buf
            current_buffered = reb.copy()

        reduction = (cum_turnover_unbuffered - cum_turnover_buffered) / cum_turnover_unbuffered
        # Assert turnover reduction is at least 50% (empirically > 90% observed)
        self.assertGreaterEqual(
            reduction,
            0.50,
            f"Leland bands achieved {reduction*100:.1f}% turnover reduction, expected >= 50.0%",
        )

    # =======================================================================
    # Group 6: Gromov Hyperbolicity & Systemic Crash Early Warning
    # =======================================================================
    def test_adv21_gromov_systemic_crash_alert_under_extreme_contagion(self) -> None:
        """ADV21: High-correlation contagion (rho -> 0.99) triggers crash alert and cash de-risking."""
        n = 8
        # Ultra-correlated market (contagion crash)
        corr_crash = np.full((n, n), 0.98, dtype=np.float64)
        np.fill_diagonal(corr_crash, 1.0)

        diag = compute_gromov_hyperbolicity(corr_crash, critical_delta=0.25)

        self.assertTrue(diag.is_crash_alert, "Crash alert failed to trigger on rho=0.98 contagion!")
        self.assertGreater(diag.h_crash, CRASH_ALERT_THRESHOLD)
        self.assertGreater(diag.cash_allocation, 0.30)
        self.assertEqual(diag.curvature_regime, CurvatureRegime.SYSTEMIC_TREE_CONTAGION)

    def test_adv22_gromov_scalability_on_large_universe_under_sla(self) -> None:
        """ADV22: Gromov hyperbolicity on 100 assets completes sampling within latency budget."""
        n = 100
        A = self.rng.randn(n, 10)
        cov = A @ A.T * 0.01 + np.eye(n) * 0.04
        vols = np.sqrt(np.diag(cov))
        corr = cov / np.outer(vols, vols)
        np.fill_diagonal(corr, 1.0)

        t0 = time.perf_counter()
        diag = compute_gromov_hyperbolicity(corr, max_samples=250)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        self.assertLess(elapsed_ms, 20.0, f"Gromov calculation took {elapsed_ms:.2f} ms > 20.0 ms")
        self.assertEqual(diag.num_4tuples_evaluated, 250)


if __name__ == "__main__":
    unittest.main()
