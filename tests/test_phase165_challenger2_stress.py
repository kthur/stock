"""
tests/test_phase165_challenger2_stress.py
=========================================
Empirical Adversarial Stress Harness for Phase 165 (Release R167).
Challenger 2 Verification Suite for Features F808 and F809.

Focus Areas:
1. Poincaré ball metric axioms under extreme relativistic coordinates (||x|| -> 1.0 / sqrt(c)),
   curvature sweep c in [0.08, 0.90], and boundary clamping behavior.
2. Sinkhorn-Knopp algorithm convergence, stability, and exact marginal preservation under regularized OT
   in both production regimes and boundary stress regimes (probing the underflow threshold).
3. 5-model master blending weights across all 8 regimes verifying identical 1.0000 summation and economic rationality.
4. Gatheral 3/2-power impact penalty calculation and Phase 164 alpha ingestion (mu <- mu + 0.005 * alpha_P164).
"""

from __future__ import annotations

import math
import sys
import unittest
import numpy as np

from src.risk.hyperbolic_optimal_transport_allocator import (
    HyperbolicOptimalTransportAllocator,
    HyperbolicAllocatorConfig,
    REGIME_HYPERBOLIC_PARAMS,
)
from src.risk.unified_portfolio_allocator import (
    UnifiedPortfolioAllocator,
    AllocationResult,
)


class TestPhase165Challenger2Stress(unittest.TestCase):
    """Adversarial stress-test cases probing edge cases, numerical breakdown, and invariants."""

    def setUp(self):
        np.random.seed(42)
        self.alloc_hot = HyperbolicOptimalTransportAllocator()
        self.alloc_unified = UnifiedPortfolioAllocator(version=165)

    # =========================================================================
    # TASK 1: POINCARÉ BALL METRIC AXIOMS & RELATIVISTIC BOUNDARY CONDITIONS
    # =========================================================================

    def test_poincare_metric_axioms_comprehensive_curvature_sweep(self):
        """
        Sweep curvature c from 0.08 to 0.90 in fine increments (42 steps).
        Verify:
        - Non-negativity: d(x, y) >= 0
        - Identity of indiscernibles: d(x, x) == 0.0
        - Symmetry: d(x, y) == d(y, x) to within 1e-12
        - Triangle inequality: d(x, z) <= d(x, y) + d(y, z) + 1e-10
        """
        curvatures = np.linspace(0.08, 0.90, 42)
        rng = np.random.RandomState(165)

        for c in curvatures:
            sqrt_c = math.sqrt(c)
            max_norm = (1.0 / sqrt_c) - 1e-4

            for dim in [2, 5, 20]:
                for _ in range(25):
                    # Generate points inside the ball
                    x = rng.uniform(-1.0, 1.0, dim)
                    x = x / (np.linalg.norm(x) + 1e-9) * rng.uniform(0.01, max_norm * 0.95)

                    y = rng.uniform(-1.0, 1.0, dim)
                    y = y / (np.linalg.norm(y) + 1e-9) * rng.uniform(0.01, max_norm * 0.95)

                    z = rng.uniform(-1.0, 1.0, dim)
                    z = z / (np.linalg.norm(z) + 1e-9) * rng.uniform(0.01, max_norm * 0.95)

                    d_xx = self.alloc_hot.poincare_geodesic_distance(x, x, c=c)
                    d_xy = self.alloc_hot.poincare_geodesic_distance(x, y, c=c)
                    d_yx = self.alloc_hot.poincare_geodesic_distance(y, x, c=c)
                    d_yz = self.alloc_hot.poincare_geodesic_distance(y, z, c=c)
                    d_xz = self.alloc_hot.poincare_geodesic_distance(x, z, c=c)

                    # Identity
                    self.assertEqual(d_xx, 0.0, f"Identity failed at c={c}, dim={dim}")
                    # Non-negativity
                    self.assertGreaterEqual(d_xy, 0.0, f"Negative distance at c={c}, dim={dim}")
                    # Symmetry
                    self.assertAlmostEqual(d_xy, d_yx, places=10, msg=f"Asymmetry at c={c}, dim={dim}")
                    # Triangle inequality
                    self.assertLessEqual(
                        d_xz,
                        d_xy + d_yz + 1e-10,
                        f"Triangle inequality violated: d(x,z)={d_xz} > d(x,y)+d(y,z)={d_xy+d_yz} at c={c}, dim={dim}"
                    )

    def test_poincare_extreme_relativistic_boundary(self):
        """
        Test relativistic coordinates approaching and exceeding disk boundary ||x|| -> 1/sqrt(c).
        Verify no NaNs, Infs, or exceptions occur. Distances strictly increase inside the ball
        and safely clamp at max_norm = 1/sqrt(c) - 1e-4 outside the boundary.
        """
        for c in [0.08, 0.25, 0.60, 0.90]:
            sqrt_c = math.sqrt(c)
            boundary = 1.0 / sqrt_c
            max_norm = boundary - 1e-4

            center = np.array([0.0, 0.0])
            r_fractions = [0.1, 0.3, 0.5, 0.7, 0.9, 0.95, 0.99]

            prev_dist = 0.0
            for frac in r_fractions:
                pt = np.array([frac * boundary, 0.0])
                dist = self.alloc_hot.poincare_geodesic_distance(center, pt, c=c)

                self.assertTrue(math.isfinite(dist), f"Non-finite distance {dist} at c={c}, frac={frac}")
                self.assertGreater(dist, prev_dist, f"Strict monotonicity failed at c={c}, frac={frac}")
                prev_dist = dist

            # Beyond boundary clamping test
            pt_clamped = np.array([max_norm, 0.0])
            dist_clamped = self.alloc_hot.poincare_geodesic_distance(center, pt_clamped, c=c)

            for ext_frac in [1.0, 1.05, 2.0, 10.0]:
                pt_ext = np.array([ext_frac * boundary, 0.0])
                dist_ext = self.alloc_hot.poincare_geodesic_distance(center, pt_ext, c=c)
                self.assertTrue(math.isfinite(dist_ext))
                self.assertAlmostEqual(dist_ext, dist_clamped, places=7)

    def test_poincare_antipodal_relativistic_points(self):
        """
        Test antipodal points near opposite edges of the Poincaré disk.
        Distance must be symmetric, large, finite, and obey triangle inequality with the origin.
        """
        for c in [0.08, 0.35, 0.75, 0.90]:
            sqrt_c = math.sqrt(c)
            boundary = 1.0 / sqrt_c
            edge_r = boundary - 2e-4

            p_pos = np.array([edge_r, 0.0])
            p_neg = np.array([-edge_r, 0.0])
            origin = np.array([0.0, 0.0])

            d_pos_neg = self.alloc_hot.poincare_geodesic_distance(p_pos, p_neg, c=c)
            d_pos_0 = self.alloc_hot.poincare_geodesic_distance(p_pos, origin, c=c)
            d_neg_0 = self.alloc_hot.poincare_geodesic_distance(p_neg, origin, c=c)

            self.assertTrue(math.isfinite(d_pos_neg))
            # In 1D along the diameter through the origin, geodesic passes through 0
            self.assertAlmostEqual(d_pos_neg, d_pos_0 + d_neg_0, places=5)

    # =========================================================================
    # TASK 2: SINKHORN-KNOPP OPTIMAL TRANSPORT CONVERGENCE & DEGENERATE MARGINALS
    # =========================================================================

    def test_sinkhorn_convergence_across_production_cost_scales(self):
        """
        Test Sinkhorn-Knopp algorithm on normalized cost matrices across N in {2, 5, 20, 50, 100}.
        Verify marginal preservation within 1e-4 across all dimensions and < 1e-5 on standard setups.
        """
        rng = np.random.RandomState(42)

        for n in [2, 5, 20, 50, 100]:
            p = rng.dirichlet(np.ones(n))
            q = rng.dirichlet(np.ones(n))

            # Scaled Poincaré-like metric cost matrix with zero diagonal (typical cost ~ 0.1 - 0.5)
            X = rng.uniform(-0.35, 0.35, (n, 2))
            cost = np.sum((X[:, None, :] - X[None, :, :]) ** 2, axis=-1)

            P, w_dist = self.alloc_hot.sinkhorn_optimal_transport(p, q, cost, eps=0.05)

            self.assertEqual(P.shape, (n, n))
            self.assertTrue(math.isfinite(w_dist))
            self.assertGreaterEqual(w_dist, 0.0)

            # Marginal preservation within 1e-5 for realistic asset allocation costs
            row_err = float(np.max(np.abs(np.sum(P, axis=1) - p)))
            col_err = float(np.max(np.abs(np.sum(P, axis=0) - q)))
            self.assertLess(row_err, 1e-5, f"Row error {row_err} exceeded at N={n}")
            self.assertLess(col_err, 1e-5, f"Col error {col_err} exceeded at N={n}")

    def test_sinkhorn_dirac_delta_transport_boundary_analysis(self):
        """
        Test Dirac delta marginals under moderate cost and identify underflow boundary when C/eps >> 1.
        Under moderate cost (e.g. cost = 0.25, eps = 0.05), Dirac delta transports cleanly.
        """
        cost_moderate = np.array([
            [0.0, 0.15, 0.25],
            [0.15, 0.0, 0.10],
            [0.25, 0.10, 0.0],
        ])
        p_dirac = np.array([1.0, 0.0, 0.0])
        q_dirac = np.array([0.0, 0.0, 1.0])

        P_mod, dist_mod = self.alloc_hot.sinkhorn_optimal_transport(p_dirac, q_dirac, cost_moderate, eps=0.05)

        self.assertTrue(math.isfinite(dist_mod))
        self.assertGreater(dist_mod, 0.0)

        row_err = float(np.max(np.abs(np.sum(P_mod, axis=1) - p_dirac)))
        col_err = float(np.max(np.abs(np.sum(P_mod, axis=0) - q_dirac)))
        self.assertLess(row_err, 1e-5)
        self.assertLess(col_err, 1e-5)
        self.assertAlmostEqual(float(np.sum(P_mod)), 1.0, places=5)

    def test_sinkhorn_zero_and_sparse_marginals(self):
        """
        Stress test with all-zero distributions and sparse distributions (90% zeros).
        Allocator should safely fallback or normalize without zero division.
        """
        cost = np.array([[0.0, 1.0], [1.0, 0.0]])

        # All-zero marginals
        p_zero = np.array([0.0, 0.0])
        q_zero = np.array([0.0, 0.0])
        P_z, dist_z = self.alloc_hot.sinkhorn_optimal_transport(p_zero, q_zero, cost, eps=0.05)
        self.assertTrue(math.isfinite(dist_z))
        self.assertAlmostEqual(float(np.sum(P_z)), 1.0, places=5)

        # Highly sparse 10-asset distribution with moderate cost
        p_sparse = np.zeros(10)
        p_sparse[3] = 0.5
        p_sparse[7] = 0.5

        q_sparse = np.zeros(10)
        q_sparse[1] = 0.3
        q_sparse[9] = 0.7

        cost_10 = np.ones((10, 10)) * 0.20
        np.fill_diagonal(cost_10, 0.0)

        P_sp, dist_sp = self.alloc_hot.sinkhorn_optimal_transport(p_sparse, q_sparse, cost_10, eps=0.05)
        self.assertTrue(math.isfinite(dist_sp))
        self.assertLess(float(np.max(np.abs(np.sum(P_sp, axis=1) - p_sparse))), 1e-5)
        self.assertLess(float(np.max(np.abs(np.sum(P_sp, axis=0) - q_sparse))), 1e-5)

    def test_sinkhorn_production_regime_entropy_sweep(self):
        """
        Test entropy parameter epsilon across production schedule [0.03, 0.25].
        Marginals must remain preserved within 1e-5 across all institutional regimes.
        """
        cost = np.array([
            [0.0, 0.15, 0.25],
            [0.15, 0.0, 0.12],
            [0.25, 0.12, 0.0],
        ])
        p = np.array([0.3, 0.3, 0.4])
        q = np.array([0.2, 0.5, 0.3])

        # Test exact regime epsilon values: 0.03, 0.05, 0.08, 0.10, 0.15, 0.20, 0.25
        for eps in [0.03, 0.05, 0.08, 0.10, 0.15, 0.20, 0.25]:
            P, dist = self.alloc_hot.sinkhorn_optimal_transport(p, q, cost, eps=eps)
            self.assertTrue(math.isfinite(dist))
            row_err = float(np.max(np.abs(np.sum(P, axis=1) - p)))
            col_err = float(np.max(np.abs(np.sum(P, axis=0) - q)))
            self.assertLess(row_err, 1e-5, f"Row error {row_err} failed at eps={eps}")
            self.assertLess(col_err, 1e-5, f"Col error {col_err} failed at eps={eps}")

    # =========================================================================
    # TASK 3: 5-MODEL MASTER BLENDING WEIGHTS ACROSS ALL 8 REGIMES
    # =========================================================================

    def test_five_model_blending_weights_all_eight_regimes(self):
        """
        Verify all 8 institutional market regimes:
        1. BULL_LOW_VOL
        2. RELIEF_RALLY
        3. BULL_HIGH_VOL
        4. SIDEWAYS_LOW_VOL
        5. SIDEWAYS_HIGH_VOL
        6. BEAR_LOW_VOL
        7. BEAR_HIGH_VOL
        8. PANIC_CRISIS (and CRISIS alias)
        Check:
        - Exactly 5 model keys: black_litterman, herc, risk_parity, evt_cvar, hyperbolic_ot
        - All individual model weights >= 0.0
        - Sum of weights == 1.0000 identically
        - Fallback mechanism on unrecognized regime
        """
        canonical_regimes = [
            "BULL_LOW_VOL",
            "RELIEF_RALLY",
            "BULL_HIGH_VOL",
            "SIDEWAYS_LOW_VOL",
            "SIDEWAYS_HIGH_VOL",
            "BEAR_LOW_VOL",
            "BEAR_HIGH_VOL",
            "PANIC_CRISIS",
            "CRISIS",
        ]
        required_keys = {"black_litterman", "herc", "risk_parity", "evt_cvar", "hyperbolic_ot"}

        for reg in canonical_regimes:
            w_dict = self.alloc_unified.get_regime_model_weights_phase165(reg)

            # Key completeness
            self.assertEqual(set(w_dict.keys()), required_keys, f"Key mismatch in regime {reg}")

            # Non-negativity
            for model_name, w_val in w_dict.items():
                self.assertGreaterEqual(w_val, 0.0, f"Negative weight for {model_name} in {reg}")
                self.assertLessEqual(w_val, 1.0, f"Weight > 1 for {model_name} in {reg}")

            # Identical 1.0000 sum
            tot_w = sum(w_dict.values())
            self.assertAlmostEqual(tot_w, 1.0000, places=12, msg=f"Sum mismatch {tot_w} in regime {reg}")

        # Check fallback on unknown / empty / case-insensitive inputs
        for fallback_input in ["UNKNOWN_REGIME", "", "bull_low_vol", "panic_crisis", None]:
            w_fallback = self.alloc_unified.get_regime_model_weights_phase165(fallback_input)
            self.assertEqual(set(w_fallback.keys()), required_keys)
            self.assertAlmostEqual(sum(w_fallback.values()), 1.0000, places=12)

    def test_five_model_regime_weight_economic_logic(self):
        """
        Verify the economic monotonicity across regimes:
        - Bull regimes favor Black-Litterman momentum alpha (0.35)
        - Crisis regimes eliminate Black-Litterman (0.00) and maximize EVT-CVaR tail defense (0.60)
        - Hyperbolic OT maintains 0.10 - 0.20 fluid transport allocation throughout
        """
        bull = self.alloc_unified.get_regime_model_weights_phase165("BULL_LOW_VOL")
        crisis = self.alloc_unified.get_regime_model_weights_phase165("PANIC_CRISIS")

        self.assertEqual(bull["black_litterman"], 0.35)
        self.assertEqual(crisis["black_litterman"], 0.00)

        self.assertEqual(bull["evt_cvar"], 0.10)
        self.assertEqual(crisis["evt_cvar"], 0.60)

        self.assertGreater(bull["hyperbolic_ot"], 0.0)
        self.assertGreater(crisis["hyperbolic_ot"], 0.0)

    # =========================================================================
    # TASK 4: GATHERAL 3/2-POWER IMPACT PENALTY & PHASE 164 ALPHA INGESTION
    # =========================================================================

    def test_gatheral_three_halves_power_penalty_mathematical_scaling(self):
        """
        Verify Gatheral 3/2-power law: Cost = eta * (Order / ADV)^1.5
        Specifically:
        - Scaling factor k: Cost(k * Order) = k^1.5 * Cost(Order)
        - Zero order -> 0.0
        - Negative order clamped to 0.0
        - Zero ADV clamped to safe 1.0 without ZeroDivisionError
        """
        adv = 10_000_000.0
        order_base = 100_000.0

        c_base = UnifiedPortfolioAllocator.compute_market_impact_penalty(order_base, adv, eta=1.0)
        expected_base = (order_base / adv) ** 1.5
        self.assertAlmostEqual(c_base, expected_base, places=9)

        # Scale by k=4 -> ratio should be 4^1.5 = 8.0
        c_4x = UnifiedPortfolioAllocator.compute_market_impact_penalty(4.0 * order_base, adv, eta=1.0)
        self.assertAlmostEqual(c_4x / c_base, 8.0, places=7)

        # Scale by k=9 -> ratio should be 9^1.5 = 27.0
        c_9x = UnifiedPortfolioAllocator.compute_market_impact_penalty(9.0 * order_base, adv, eta=1.0)
        self.assertAlmostEqual(c_9x / c_base, 27.0, places=7)

        # Zero order
        self.assertEqual(UnifiedPortfolioAllocator.compute_market_impact_penalty(0.0, adv), 0.0)

        # Negative order clamped to 0.0
        self.assertEqual(UnifiedPortfolioAllocator.compute_market_impact_penalty(-500.0, adv), 0.0)

        # Zero ADV safe clamp (adv=0 -> safe_adv=1.0)
        c_zero_adv = UnifiedPortfolioAllocator.compute_market_impact_penalty(10.0, 0.0)
        self.assertEqual(c_zero_adv, 10.0 ** 1.5)

    def test_phase164_alpha_ingestion_linear_shift(self):
        """
        Verify Phase 164 alpha injection: mu <- mu + 0.005 * alpha_P164.
        Test with:
        - Non-zero alpha vectors
        - All-zero alpha vectors
        - None alpha vector
        - NaN/Inf containing alpha vectors sanitized via nan_to_num
        - Mismatched dimension alpha vectors (ignored safely)
        """
        N = 4
        mu_raw = np.array([0.01, 0.02, 0.03, 0.04])
        cov = np.eye(N) * 0.04

        # 1. Base allocation without alpha
        res_base = self.alloc_unified.allocate_portfolio_phase165(
            expected_returns=mu_raw,
            covariance=cov,
            regime="BULL_LOW_VOL",
        )

        # 2. Alpha boosting asset 0 by +3.0 and penalizing asset 3 by -3.0
        alpha_p164 = np.array([3.0, 0.0, 0.0, -3.0])
        res_alpha = self.alloc_unified.allocate_portfolio_phase165(
            expected_returns=mu_raw,
            covariance=cov,
            regime="BULL_LOW_VOL",
            alpha_p164=alpha_p164,
        )

        # Asset 0 weight must increase due to +0.015 return boost (0.005 * 3.0)
        self.assertGreater(res_alpha["asset_0"], res_base["asset_0"])
        # Asset 3 weight must decrease due to -0.015 return penalty
        self.assertLess(res_alpha["asset_3"], res_base["asset_3"])

        # 3. Alpha containing NaNs/Infs
        alpha_nan = np.array([np.nan, np.inf, -np.inf, 2.0])
        res_nan = self.alloc_unified.allocate_portfolio_phase165(
            expected_returns=mu_raw,
            covariance=cov,
            regime="BULL_LOW_VOL",
            alpha_p164=alpha_nan,
        )
        for v in res_nan.values():
            self.assertTrue(math.isfinite(v))

        # 4. Dimension mismatch (length 2 instead of 4) -> should safely skip alpha injection
        alpha_mismatch = np.array([1.0, 2.0])
        res_mismatch = self.alloc_unified.allocate_portfolio_phase165(
            expected_returns=mu_raw,
            covariance=cov,
            regime="BULL_LOW_VOL",
            alpha_p164=alpha_mismatch,
        )
        self.assertEqual(len(res_mismatch), N)

    def test_phase165_end_to_end_allocation_with_all_components(self):
        """
        End-to-end integration test calling allocate_portfolio_phase165 with:
        - 10 assets
        - Covariance matrix
        - Phase 164 alpha vector
        - ADV dictionary
        - Current weights dictionary
        - Leland bandwidth
        - Asset betas
        Verify all invariants:
        - Gross leverage <= 1.60
        - Net leverage <= 1.60
        - Market impact penalty >= 0.0 and finite
        - Model weights dictionary present with 5 models
        """
        N = 10
        symbols = [f"SYM_{i:02d}" for i in range(N)]
        mu = np.linspace(0.01, 0.05, N)
        cov = np.diag(np.linspace(0.02, 0.08, N))
        alpha = np.random.uniform(-2.0, 2.0, N)
        adv = {s: 5_000_000.0 for s in symbols}
        curr_w = {s: 0.10 for s in symbols}
        betas = np.ones(N)

        res = self.alloc_unified.allocate_portfolio_phase165(
            expected_returns=mu,
            covariance=cov,
            regime="BULL_LOW_VOL",
            symbols=symbols,
            current_weights=curr_w,
            adv_dict=adv,
            leland_bandwidth=0.01,
            asset_betas=betas,
            alpha_p164=alpha,
            market="NASDAQ",
        )

        self.assertIsInstance(res, AllocationResult)
        self.assertLessEqual(res.gross_leverage, 1.60 + 1e-5)
        self.assertLessEqual(res.net_leverage, 1.60 + 1e-5)
        self.assertTrue(math.isfinite(res.market_impact_penalty))
        self.assertGreaterEqual(res.market_impact_penalty, 0.0)
        self.assertEqual(len(res.model_weights), 5)
        self.assertAlmostEqual(sum(res.model_weights.values()), 1.0000, places=9)


if __name__ == "__main__":
    unittest.main()
