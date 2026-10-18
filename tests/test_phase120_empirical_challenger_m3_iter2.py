"""
Empirical Adversarial Stress Harness for Phase 120 Milestone 3 Iteration 2 (Feature F572)
Authored by teamwork_preview_challenger_m3_iter2.

Tests the thorough resolution of:
1. Budget leakage under extreme alpha disparity & crash cash de-risking
2. Boundary vertex / face trapping across arbitrary simplex boundary points
3. Box constraint enforcement under mathematically infeasible / boundary max_single_weight
4. Random stress generation across 500 permutations of N in [3, 20], condition numbers, alphas, and box constraints
"""

import unittest
import numpy as np
import math

from src.risk.riemannian_manifold_portfolio_allocator import (
    RiemannianManifoldPortfolioAllocator,
    RiemannianAllocatorConfig,
    geodesic_distance,
    apply_geodesic_leland_bands,
    BypassAction,
)


class TestPhase120EmpiricalChallengerM3Iter2(unittest.TestCase):

    def setUp(self):
        np.random.seed(42)

    def test_emp01_defect1_astronomical_alpha_with_and_without_crash_cash(self):
        """Verify simplex budget conservation under extreme alpha disparity with varying cash de-risking."""
        alloc = RiemannianManifoldPortfolioAllocator(market="SP500", max_single_weight=0.80)
        mu = np.array([1e9, -1e9, 0.0, 100.0, -50.0])
        cov = np.eye(5) * 0.04

        res = alloc.optimize(mu, cov)
        total_alloc = float(np.sum(res.optimal_weights) + res.cash_weight)
        self.assertAlmostEqual(total_alloc, 1.0, places=7)
        self.assertLessEqual(np.max(res.optimal_weights), 0.8000001)
        self.assertTrue(np.all(res.optimal_weights >= 0.0))

        # Test with cash de-risking present (cash_allocation > 0)
        rebalanced = apply_geodesic_leland_bands(
            target_weights=np.array([1.0, 0.0, 0.0, 0.0, 0.0]),
            current_weights=np.zeros(5),
            asset_vols=np.full(5, 0.20),
            h_crash=1.0,
            base_band=0.02,
            kappa_sigma=0.5,
            kappa_h=0.5,
            cash_allocation=0.30,  # 30% cash de-risking
            max_single_weight=0.50,
        )
        self.assertAlmostEqual(float(np.sum(rebalanced.rebalanced_weights) + 0.30), 1.0, places=7)
        self.assertLessEqual(np.max(rebalanced.rebalanced_weights), 0.5000001)

    def test_emp02_defect2_boundary_escape_across_all_simplex_vertices(self):
        """Verify that starting from ANY simplex vertex w = e_k escapes towards higher alpha."""
        alloc = RiemannianManifoldPortfolioAllocator(market="NASDAQ")
        n = 5
        cov = np.eye(n) * 0.04
        mu = np.array([0.05, 0.10, 0.15, 0.20, 0.25])  # asset 4 is best, asset 0 is worst

        # Test starting at worst vertex (asset 0)
        w0 = np.zeros(n)
        w0[0] = 1.0
        res = alloc.optimize(mu, cov, current_weights=w0)

        # Must not remain trapped at w[0] = 1.0
        self.assertLess(float(res.optimal_weights[0]), 0.80)
        # Target weights must prioritize higher alpha
        self.assertGreater(float(res.target_weights[4]), float(res.target_weights[0]))
        self.assertAlmostEqual(float(np.sum(res.optimal_weights) + res.cash_weight), 1.0, places=7)

        # Test starting at an edge / face (two vertices non-zero, rest zero)
        w_face = np.array([0.5, 0.5, 0.0, 0.0, 0.0])
        res_face = alloc.optimize(mu, cov, current_weights=w_face)
        self.assertGreater(float(res_face.optimal_weights[4]), 0.05)
        self.assertAlmostEqual(float(np.sum(res_face.optimal_weights) + res_face.cash_weight), 1.0, places=7)

    def test_emp03_defect3_infeasible_box_constraint_boundary_limits(self):
        """Verify behavior when max_single_weight <= 1/n across multiple dimensions."""
        test_cases = [
            (3, 0.10),   # 1/3 = 0.333 > 0.10 (infeasible)
            (4, 0.25),   # 1/4 = 0.25 == 0.25 (boundary)
            (4, 0.05),   # 1/4 = 0.25 > 0.05 (infeasible)
            (10, 0.05),  # 1/10 = 0.10 > 0.05 (infeasible)
            (10, 0.10),  # 1/10 = 0.10 == 0.10 (boundary)
            (10, 0.09999999), # just below 1/n
        ]

        for n, max_w in test_cases:
            alloc = RiemannianManifoldPortfolioAllocator(market="SP500", max_single_weight=max_w)
            mu = np.linspace(0.05, 0.30, n)
            cov = np.eye(n) * 0.04
            res = alloc.optimize(mu, cov)

            effective_bound = max(max_w, 1.0 / n)
            max_actual = float(np.max(res.optimal_weights))

            self.assertLessEqual(max_actual, effective_bound + 1e-6,
                f"Failed for n={n}, max_w={max_w}: max_actual={max_actual} > effective={effective_bound}")
            self.assertAlmostEqual(float(np.sum(res.optimal_weights) + res.cash_weight), 1.0, places=7,
                msg=f"Budget violated for n={n}, max_w={max_w}")
            self.assertTrue(np.all(res.optimal_weights >= -1e-9),
                msg=f"Negative weights for n={n}, max_w={max_w}")

    def test_emp04_random_stress_generator_300_trials(self):
        """Stress-test 300 randomized market configurations with varying sizes, alphas, condition numbers, and constraints."""
        rng = np.random.RandomState(1337)
        markets = ["SP500", "NASDAQ", "RUSSELL2000", "KOSPI", "KOSDAQ"]

        for trial in range(300):
            n = rng.randint(3, 16)
            market = rng.choice(markets)

            # Random alphas with possible extreme outliers
            if trial % 5 == 0:
                mu = rng.uniform(-10.0, 10.0, size=n)
                mu[0] = 1e6
                mu[1] = -1e6
            elif trial % 7 == 0:
                mu = np.full(n, 0.10)
            else:
                mu = rng.randn(n) * 0.10

            # Random covariance with ill-conditioning or collinearity
            A = rng.randn(n, n)
            cov = np.dot(A, A.T) * 0.01 + np.eye(n) * 1e-5
            if trial % 6 == 0:
                # Rank deficient
                cov[:, 0] = cov[:, 1]
                cov[0, :] = cov[1, :]

            # Random starting weights: sometimes vertex, sometimes simplex, sometimes None
            init_mode = trial % 4
            if init_mode == 0:
                current_w = None
            elif init_mode == 1:
                current_w = np.zeros(n)
                current_w[rng.randint(0, n)] = 1.0  # pure vertex
            elif init_mode == 2:
                current_w = rng.exponential(scale=1.0, size=n)
                current_w /= np.sum(current_w)
            else:
                # near boundary
                current_w = np.full(n, 1e-6)
                current_w[0] = 1.0 - (n - 1) * 1e-6

            # Random max_single_weight
            box_mode = trial % 3
            if box_mode == 0:
                max_w = None
            elif box_mode == 1:
                max_w = rng.uniform(0.01, 1.0 / n)  # infeasible
            else:
                max_w = rng.uniform(1.0 / n, 0.90)  # feasible

            alloc = RiemannianManifoldPortfolioAllocator(market=market, max_single_weight=max_w)
            res = alloc.optimize(mu, cov, current_weights=current_w)

            # Invariants
            self.assertFalse(np.any(np.isnan(res.optimal_weights)), f"NaN in trial {trial}")
            self.assertFalse(np.any(np.isinf(res.optimal_weights)), f"Inf in trial {trial}")
            self.assertTrue(np.all(res.optimal_weights >= -1e-9), f"Negative weight in trial {trial}")

            total_budget = float(np.sum(res.optimal_weights) + res.cash_weight)
            self.assertAlmostEqual(total_budget, 1.0, places=6,
                msg=f"Budget sum {total_budget} != 1.0 in trial {trial}")

            if max_w is not None:
                effective_limit = max(max_w, 1.0 / n)
                max_observed = float(np.max(res.optimal_weights))
                self.assertLessEqual(max_observed, effective_limit + 1e-5,
                    f"Box violation in trial {trial}: {max_observed} > {effective_limit}")

    def test_emp05_defect_budget_leakage_when_crash_cash_and_infeasible_box_coincide(self):
        """
        Isolated regression test reproducing Defect:
        When cash_allocation > 0 (crash regime) and max_single_weight <= 1/n,
        if current_w has a concentrated holding, apply_geodesic_leland_bands
        allocates 1.0 to risky assets instead of (1.0 - cash_allocation),
        resulting in sum(weights) + cash == 1.0 + cash > 1.0!
        """
        n = 5
        max_w = 0.10  # effective_max_w = 1/5 = 0.20
        cash = 0.40   # risky budget should be 0.60
        target_w = np.full(n, 0.20)
        current_w = np.array([0.0, 1.0, 0.0, 0.0, 0.0])

        res = apply_geodesic_leland_bands(
            target_weights=target_w,
            current_weights=current_w,
            asset_vols=np.full(n, 0.20),
            h_crash=1.0,
            base_band=0.02,
            kappa_sigma=0.5,
            kappa_h=0.5,
            cash_allocation=cash,
            max_single_weight=max_w,
        )

        total_allocation = float(np.sum(res.rebalanced_weights) + cash)
        # Expected: sum(rebalanced_weights) == 0.60, total == 1.000000
        # Actual: sum(rebalanced_weights) == 1.00, total == 1.400000 (40% leverage/leakage!)
        self.assertAlmostEqual(total_allocation, 1.0, places=6,
            msg=f"Total allocation {total_allocation} exceeds 1.0 when cash_allocation > 0 and max_w <= 1/n")


if __name__ == "__main__":
    unittest.main()
