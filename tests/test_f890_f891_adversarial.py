"""
tests/test_f890_f891_adversarial.py
====================================
Adversarial Stress Test Suite for Release R180 Features F890 & F891.
Role: Code-Executing Adversarial Challenger (challenger_m3_1).

Challenges Under Empirical Stress:
1. Feature F890 (Poincaré-Lorentz Hyperbolic Optimal Transport Barycenter):
   - Poincaré disk metric boundary conditions: ||x|| -> 1.0, numerical stability, clamping, no NaNs/infs.
   - Sinkhorn-Knopp algorithm under degenerate cost matrices or uniform weights.
   - Total mass preservation: sum(w_barycenter) == sum(w_target).
   - Invariant: synthetic_rows == 0 strictly native Python int 0.
2. Feature F891 (Dynamic Regime Leverage Frontiers & 5D Contango Lock):
   - Contango lock edge cases: vts_ratio = 0.9200000 vs 0.9200001, contango_days = 4 vs 5.
   - Leverage limits: verify BULL_LOW_VOL scales to 1.95x ONLY when contango is locked.
     Under backwardation or breaking contango, ensure leverage does NOT exceed standard limit.
   - Crisis regimes: PANIC_CRISIS must strictly cap at 0.20x leverage.
   - Physical capital conservation: leverage multipliers never produce negative allocations or violate net equity constraints.
"""

from __future__ import annotations

import math
import unittest
import numpy as np
import pandas as pd

# Target module imports
from src.risk.hyperbolic_optimal_transport_allocator import (
    HyperbolicOptimalTransportAllocator,
    LorentzPoincareWassersteinAllocator,
    mobius_addition,
    poincare_exponential_map,
    poincare_logarithmic_map,
    compute_poincare_wasserstein_barycenter,
    compute_hyperbolic_wasserstein_barycenter,
    allocate_hyperbolic_barycenter_phase182,
)

from src.risk.poincare_barycenter_allocator import (
    compute_poincare_wasserstein_barycenter as pb_compute_barycenter,
    allocate_hyperbolic_barycenter_phase182 as pb_allocate_barycenter,
)

from src.risk.dynamic_regime_leverage_allocator import (
    DynamicRegimeLeverageAllocator,
    RegimeCompoundingLeverageAllocator,
    _LeverageFloat,
)

from src.risk.unified_portfolio_allocator import (
    allocate_portfolio_phase182,
)


class TestF890PoincareAdversarial(unittest.TestCase):
    """Adversarial stress harness for Feature F890 (Poincaré Hyperbolic OT Barycenter)."""

    def test_adv01_poincare_metric_boundary_clamping_and_extremes(self):
        """TC_ADV_01: Points at and beyond disk boundary ||x|| -> 1.0 / sqrt(c)."""
        c = 0.25
        max_valid_r = 1.0 / math.sqrt(c)  # 2.0 for c=0.25

        # Extreme radius probes: exactly at boundary, epsilon inside, outside, huge
        radii = [
            max_valid_r * 0.999999,
            max_valid_r * 0.999999999,
            max_valid_r * 1.0,
            max_valid_r * 1.00001,
            max_valid_r * 2.0,
            1e5,
            1e8,
        ]

        center = np.zeros(3, dtype=np.float64)

        for r in radii:
            # Unit vector in 3D
            x = np.array([r / math.sqrt(3), r / math.sqrt(3), r / math.sqrt(3)], dtype=np.float64)
            d = HyperbolicOptimalTransportAllocator.poincare_geodesic_distance(center, x, c=c)
            self.assertTrue(math.isfinite(d), f"Distance not finite for radius {r}: {d}")
            self.assertFalse(math.isnan(d), f"Distance is NaN for radius {r}")
            self.assertGreaterEqual(d, 0.0, f"Distance negative for radius {r}: {d}")

        # Opposite points at extreme boundary
        p1 = np.array([max_valid_r * 0.99999, 0.0], dtype=np.float64)
        p2 = np.array([-max_valid_r * 0.99999, 0.0], dtype=np.float64)
        d_diam = HyperbolicOptimalTransportAllocator.poincare_geodesic_distance(p1, p2, c=c)
        self.assertTrue(math.isfinite(d_diam))
        self.assertGreater(d_diam, 0.0)

        # Identical boundary points should have distance 0.0
        d_ident = HyperbolicOptimalTransportAllocator.poincare_geodesic_distance(p1, p1, c=c)
        self.assertAlmostEqual(d_ident, 0.0, places=9)

    def test_adv02_poincare_metric_symmetry_and_triangle_inequality(self):
        """TC_ADV_02: Metric axioms must hold under near-boundary conditions."""
        c = 0.50
        max_r = (1.0 / math.sqrt(c)) - 1e-4

        rng = np.random.RandomState(42)
        # Generate 20 points distributed near the boundary
        points = []
        for _ in range(20):
            vec = rng.randn(3)
            vec = vec / (np.linalg.norm(vec) + 1e-12)
            r = rng.uniform(0.85, 0.9999) * max_r
            points.append(vec * r)

        for i in range(len(points)):
            for j in range(len(points)):
                d_ij = HyperbolicOptimalTransportAllocator.poincare_geodesic_distance(points[i], points[j], c=c)
                d_ji = HyperbolicOptimalTransportAllocator.poincare_geodesic_distance(points[j], points[i], c=c)
                self.assertAlmostEqual(d_ij, d_ji, places=8, msg="Symmetry violation")

                if i == j:
                    self.assertAlmostEqual(d_ij, 0.0, places=9)

                # Triangle inequality check with third point
                k = (j + 1) % len(points)
                d_ik = HyperbolicOptimalTransportAllocator.poincare_geodesic_distance(points[i], points[k], c=c)
                d_jk = HyperbolicOptimalTransportAllocator.poincare_geodesic_distance(points[j], points[k], c=c)
                self.assertLessEqual(d_ik, d_ij + d_jk + 1e-6, "Triangle inequality violation")

    def test_adv03_mobius_addition_boundary_confinement(self):
        """TC_ADV_03: Möbius addition must confine results strictly within disk."""
        c = 0.25
        max_r = 1.0 / math.sqrt(c)

        # Probing close to boundary
        x = np.array([max_r * 0.999, 0.0], dtype=np.float64)
        y = np.array([0.0, max_r * 0.999], dtype=np.float64)

        res = mobius_addition(x, y, c=c)
        norm_res = float(np.linalg.norm(res))
        self.assertTrue(math.isfinite(norm_res))
        self.assertLess(norm_res, max_r, "Möbius addition escaped the Poincaré ball!")

        # Opposite directions near boundary
        y_opp = np.array([-max_r * 0.999, 0.0], dtype=np.float64)
        res_opp = mobius_addition(x, y_opp, c=c)
        self.assertTrue(math.isfinite(float(np.linalg.norm(res_opp))))
        self.assertLess(float(np.linalg.norm(res_opp)), max_r)

    def test_adv04_exp_and_log_maps_tangent_explosions(self):
        """TC_ADV_04: Riemannian exp and log maps with massive tangent vectors."""
        c = 0.25
        p = np.array([0.1, -0.2], dtype=np.float64)
        huge_v = np.array([1e6, -1e6], dtype=np.float64)

        # Huge tangent vector should map inside the ball via tanh saturation
        exp_res = poincare_exponential_map(p, huge_v, c=c)
        max_r = 1.0 / math.sqrt(c)
        norm_exp = float(np.linalg.norm(exp_res))
        self.assertTrue(math.isfinite(norm_exp))
        self.assertLess(norm_exp, max_r)

        # Extremely tiny tangent vector
        tiny_v = np.array([1e-15, 1e-15], dtype=np.float64)
        exp_tiny = poincare_exponential_map(p, tiny_v, c=c)
        np.testing.assert_allclose(exp_tiny, p, atol=1e-10)

        # Log map from point to itself
        log_self = poincare_logarithmic_map(p, p, c=c)
        np.testing.assert_allclose(log_self, np.zeros_like(p), atol=1e-10)

    def test_adv05_extreme_curvatures(self):
        """TC_ADV_05: Metric stability at extreme curvatures c=1e-6 and c=100.0."""
        x = np.array([0.05, 0.05])
        y = np.array([-0.05, 0.02])

        # Near zero curvature (flat)
        d_flat = HyperbolicOptimalTransportAllocator.poincare_geodesic_distance(x, y, c=1e-6)
        euclidean_d = float(np.linalg.norm(x - y))
        self.assertTrue(math.isfinite(d_flat))
        # At c -> 0, Poincaré metric approaches 2 * Euclidean distance
        self.assertAlmostEqual(d_flat, 2.0 * euclidean_d, delta=0.01)

        # High curvature
        d_high = HyperbolicOptimalTransportAllocator.poincare_geodesic_distance(x, y, c=100.0)
        self.assertTrue(math.isfinite(d_high))
        self.assertGreater(d_high, 0.0)

    def test_adv06_sinkhorn_degenerate_cost_matrices(self):
        """TC_ADV_06: Sinkhorn-Knopp under degenerate cost matrices (all zeros, all equal)."""
        alloc = HyperbolicOptimalTransportAllocator()
        p = np.array([0.2, 0.3, 0.5])
        q = np.array([0.4, 0.4, 0.2])

        # All zeros cost matrix
        cost_zero = np.zeros((3, 3))
        plan, w_dist = alloc.sinkhorn_optimal_transport(p, q, cost_zero, eps=0.05)
        self.assertTrue(np.all(np.isfinite(plan)))
        self.assertAlmostEqual(w_dist, 0.0, places=6)
        # Marginals must match
        np.testing.assert_allclose(np.sum(plan, axis=1), p, atol=1e-4)
        np.testing.assert_allclose(np.sum(plan, axis=0), q, atol=1e-4)

        # All equal large cost matrix
        cost_const = np.full((3, 3), 10.0)
        plan_c, _ = alloc.sinkhorn_optimal_transport(p, q, cost_const, eps=0.05)
        self.assertTrue(np.all(np.isfinite(plan_c)))
        np.testing.assert_allclose(np.sum(plan_c, axis=1), p, atol=1e-4)
        np.testing.assert_allclose(np.sum(plan_c, axis=0), q, atol=1e-4)

    def test_adv07_sinkhorn_dirac_delta_and_uniform_marginals(self):
        """TC_ADV_07: Sinkhorn-Knopp with one-hot concentrated marginals vs uniform."""
        alloc = HyperbolicOptimalTransportAllocator()
        p_dirac = np.array([1.0, 0.0, 0.0, 0.0])
        q_unif = np.array([0.25, 0.25, 0.25, 0.25])
        cost = np.array([
            [0.0, 1.0, 2.0, 3.0],
            [1.0, 0.0, 1.0, 2.0],
            [2.0, 1.0, 0.0, 1.0],
            [3.0, 2.0, 1.0, 0.0],
        ])

        plan, w_dist = alloc.sinkhorn_optimal_transport(p_dirac, q_unif, cost, eps=0.10)
        self.assertTrue(np.all(np.isfinite(plan)))
        self.assertGreater(w_dist, 0.0)
        # Row sums match p_dirac
        np.testing.assert_allclose(np.sum(plan, axis=1), p_dirac, atol=1e-4)
        np.testing.assert_allclose(np.sum(plan, axis=0), q_unif, atol=1e-4)

    def test_adv08_poincare_barycenter_total_mass_preservation_across_leverages(self):
        """TC_ADV_08: Verify strict mass preservation sum(w_barycenter) == sum(w_target)."""
        w_curr = np.array([0.1, 0.2, 0.3, 0.4], dtype=np.float64)

        test_masses = [0.15, 0.50, 1.00, 1.50, 1.85, 1.95, 2.50]
        for m in test_masses:
            w_target = np.array([0.25, 0.25, 0.25, 0.25], dtype=np.float64) * m
            res = compute_poincare_wasserstein_barycenter(w_curr, w_target, curvature=0.25, epsilon=0.05)
            w_bary = res["barycenter_weights"]

            self.assertTrue(np.all(np.isfinite(w_bary)))
            sum_bary = float(np.sum(w_bary))
            self.assertAlmostEqual(
                sum_bary,
                m,
                places=5,
                msg=f"Mass preservation failed for target mass {m}: got {sum_bary}"
            )
            self.assertEqual(res["synthetic_rows"], 0)
            self.assertIs(type(res["synthetic_rows"]), int)

    def test_adv09_barycenter_degenerate_and_empty_inputs(self):
        """TC_ADV_09: Empty inputs, single asset, and mismatched array lengths."""
        # Empty input
        res_empty = compute_poincare_wasserstein_barycenter(np.array([]), np.array([]))
        self.assertEqual(len(res_empty["w_barycenter"]), 0)
        self.assertEqual(res_empty["synthetic_rows"], 0)

        # Single asset
        res_single = compute_poincare_wasserstein_barycenter(np.array([0.5]), np.array([1.95]))
        self.assertEqual(len(res_single["w_barycenter"]), 1)
        self.assertAlmostEqual(float(res_single["w_barycenter"][0]), 1.95, places=5)
        self.assertEqual(res_single["synthetic_rows"], 0)

        # Mismatched lengths: curr has 2, target has 5
        res_mismatch = compute_poincare_wasserstein_barycenter(np.array([0.5, 0.5]), np.array([0.2, 0.2, 0.2, 0.2, 0.2]))
        self.assertEqual(len(res_mismatch["w_barycenter"]), 5)
        self.assertAlmostEqual(float(np.sum(res_mismatch["w_barycenter"])), 1.0, places=5)

    def test_adv10_high_dimensional_barycenter_scaling(self):
        """TC_ADV_10: Scale test with N=100 and N=250 assets."""
        rng = np.random.RandomState(180)
        for n_assets in (100, 250):
            w_c = rng.uniform(0.01, 1.0, n_assets)
            w_c /= np.sum(w_c)
            w_t = rng.uniform(0.01, 1.0, n_assets)
            w_t = (w_t / np.sum(w_t)) * 1.95

            res = compute_poincare_wasserstein_barycenter(w_c, w_t, curvature=0.25, epsilon=0.05, max_iter=50)
            w_bary = res["barycenter_weights"]

            self.assertEqual(len(w_bary), n_assets)
            self.assertAlmostEqual(float(np.sum(w_bary)), 1.95, places=4)
            self.assertTrue(np.all(w_bary >= 0.0))
            self.assertEqual(res["synthetic_rows"], 0)


class TestF891RegimeLeverageAdversarial(unittest.TestCase):
    """Adversarial stress harness for Feature F891 (Dynamic Regime Leverage Frontiers & Contango Lock)."""

    def setUp(self):
        self.alloc = DynamicRegimeLeverageAllocator()

    def test_adv11_contango_lock_strict_boundary_precision(self):
        """TC_ADV_11: Precise boundary comparison: 0.9200000 vs 0.9200001, days 4 vs 5."""
        # Exactly on boundary: VTS 0.9200000, 5 days -> TRUE
        self.assertTrue(self.alloc.check_contango_lock(contango_days=5, vts_ratio=0.9200000))

        # Precision breach: VTS 0.9200001, 5 days -> FALSE
        self.assertFalse(self.alloc.check_contango_lock(contango_days=5, vts_ratio=0.9200001))

        # Days breach: VTS 0.9200000, 4 days -> FALSE
        self.assertFalse(self.alloc.check_contango_lock(contango_days=4, vts_ratio=0.9200000))

        # Extreme deep contango but only 4 days -> FALSE
        self.assertFalse(self.alloc.check_contango_lock(contango_days=4, vts_ratio=0.7500000))

        # Negative / zero days -> FALSE
        self.assertFalse(self.alloc.check_contango_lock(contango_days=0, vts_ratio=0.85))
        self.assertFalse(self.alloc.check_contango_lock(contango_days=-3, vts_ratio=0.85))

    def test_adv12_bull_low_vol_requires_contango_lock_for_195(self):
        """TC_ADV_12: BULL_LOW_VOL leverage scales to 1.95x ONLY when contango is locked."""
        # Case A: Contango LOCKED (days=5, vts_ratio=0.90) with high momentum
        lev_locked = self.alloc.compute_regime_compounding_leverage(
            regime="BULL_LOW_VOL",
            contango_days=5,
            vts_ratio=0.90,
            trend_50d=0.30,
            vol_20d=0.10,
        )
        self.assertGreaterEqual(float(lev_locked), 1.85)
        self.assertLessEqual(float(lev_locked), 1.950001)

        # Case B: Contango NOT locked (days=4, vts_ratio=0.90) with identical high momentum
        lev_unlocked = self.alloc.compute_regime_compounding_leverage(
            regime="BULL_LOW_VOL",
            contango_days=4,
            vts_ratio=0.90,
            trend_50d=0.30,
            vol_20d=0.10,
        )
        # Must NOT reach 1.95x
        self.assertLessEqual(float(lev_unlocked), 1.850001)

        # Case C: Backwardation (days=5, vts_ratio=1.10) with high momentum
        lev_backwardation = self.alloc.compute_regime_compounding_leverage(
            regime="BULL_LOW_VOL",
            contango_days=5,
            vts_ratio=1.10,
            trend_50d=0.30,
            vol_20d=0.10,
        )
        # Must NOT reach 1.95x
        self.assertLessEqual(float(lev_backwardation), 1.850001)

    def test_adv13_backwardation_strict_leverage_compression_in_gating(self):
        """TC_ADV_13: Under backwardation (TSR > 1.00 / 1.08 / 1.25), leverage is severely capped."""
        # Normal BULL regime baseline without backwardation
        lev_normal = self.alloc.evaluate_dynamic_leverage_frontier(
            current_nav=1.0,
            vix=14.0,
            vix_history=[14.0] * 20,
            tsr_ratio=0.88,
            regime="BULL_LOW_VOL",
        )
        self.assertGreaterEqual(float(lev_normal), 1.50)

        # TSR = 1.02 (mild backwardation) -> tsr_cap = 0.80
        lev_mild_back = self.alloc.evaluate_dynamic_leverage_frontier(
            current_nav=1.0,
            vix=18.0,
            vix_history=[18.0] * 20,
            tsr_ratio=1.02,
            regime="BULL_LOW_VOL",
        )
        self.assertLessEqual(float(lev_mild_back), 0.800001)

        # TSR = 1.12 (strong backwardation) -> tsr_cap = 0.50
        lev_strong_back = self.alloc.evaluate_dynamic_leverage_frontier(
            current_nav=1.0,
            vix=25.0,
            vix_history=[22.0] * 20,
            tsr_ratio=1.12,
            regime="BULL_LOW_VOL",
        )
        self.assertLessEqual(float(lev_strong_back), 0.500001)

        # TSR = 1.30 (crisis backwardation) -> tsr_cap = min_crisis_exposure (0.15)
        lev_crisis_back = self.alloc.evaluate_dynamic_leverage_frontier(
            current_nav=1.0,
            vix=40.0,
            vix_history=[30.0] * 20,
            tsr_ratio=1.30,
            regime="BULL_LOW_VOL",
        )
        self.assertLessEqual(float(lev_crisis_back), 0.200001)

    def test_adv14_crisis_regimes_strictly_capped_at_020(self):
        """TC_ADV_14: Canonical PANIC_CRISIS and CRISIS must strictly cap at <= 0.20x leverage."""
        canonical_crisis_regimes = ["PANIC_CRISIS", "CRISIS", "panic_crisis", "crisis"]
        for reg in canonical_crisis_regimes:
            lim = self.alloc.get_regime_leverage_limit(reg)
            self.assertLessEqual(float(lim), 0.200001, f"Limit for canonical {reg} exceeded 0.20x: {lim}")

            comp_lev = self.alloc.compute_regime_compounding_leverage(
                regime=reg,
                contango_days=10,
                vts_ratio=0.80,
                trend_50d=0.50,
                vol_20d=0.08,
            )
            self.assertLessEqual(float(comp_lev), 0.200001, f"Compounding leverage for {reg} exceeded 0.20x: {comp_lev}")

        # Documenting informal non-canonical shorthand 'PANIC' behavior:
        # 'PANIC_CRISIS' and 'CRISIS' are the canonical enums. Non-canonical 'PANIC' falls back to default 1.0.
        self.assertAlmostEqual(float(self.alloc.get_regime_leverage_limit("PANIC_CRISIS")), 0.20, places=5)
        self.assertAlmostEqual(float(self.alloc.get_regime_leverage_limit("CRISIS")), 0.20, places=5)

    def test_adv15_mcsi_systemic_crash_override_clamp(self):
        """TC_ADV_15: MCSI >= 2.50 forces crisis emergency clamp <= 0.20x regardless of inputs."""
        extreme_mcsi_scores = [2.50, 2.50001, 3.0, 5.0, 10.0]
        for mcsi in extreme_mcsi_scores:
            lev = self.alloc.compute_regime_compounding_leverage(
                regime="BULL_LOW_VOL",
                contango_days=20,
                vts_ratio=0.75,
                trend_50d=1.0,
                vol_20d=0.05,
                mcsi_score=mcsi,
            )
            self.assertLessEqual(float(lev), 0.200001, f"MCSI {mcsi} did not clamp leverage to <= 0.20x: {lev}")

    def test_adv16_physical_capital_conservation_and_no_negative_allocations(self):
        """TC_ADV_16: Leverage multipliers never produce negative weights or violate Net Equity <= Gross Equity."""
        symbols = [f"SYM_{i}" for i in range(25)]
        # Mix of positive, negative, and zero alphas
        alphas = {sym: float(i - 12) for i, sym in enumerate(symbols)}

        # Run master portfolio allocation at 1.95x leverage
        res = allocate_portfolio_phase182(
            alpha_vector=alphas,
            regime="BULL_LOW_VOL",
            gross_leverage=1.95,
            contango_days=5,
            vts_ratio=0.90,
        )

        weights = res.target_weights
        self.assertGreater(len(weights), 0)

        # 1. No negative weights
        for s, w in weights.items():
            self.assertGreaterEqual(w, -1e-7, f"Asset {s} has negative weight {w}")

        # 2. Total allocation must not exceed gross leverage
        tot_weight = sum(weights.values())
        self.assertLessEqual(tot_weight, 1.95 + 1e-4)

        # 3. Capital conservation invariant
        self.assertLessEqual(res.net_leverage, res.gross_leverage + 1e-6)

        # 4. Zero synthetic rows invariant
        self.assertEqual(res.metadata["synthetic_rows"], 0)
        self.assertIs(type(res.metadata["synthetic_rows"]), int)

    def test_adv17_single_stock_concentration_cap_waterfilling(self):
        """TC_ADV_17: Verify 5% * gross_leverage concentration cap with N >= 20."""
        # 30 stocks with massive outlier alpha on one stock
        symbols = [f"STK_{i}" for i in range(30)]
        alpha_dict = {s: 1.0 for s in symbols}
        alpha_dict["STK_0"] = 100.0  # Massive outlier

        # F890 allocator directly
        alloc_f890 = LorentzPoincareWassersteinAllocator()
        weights_f890 = alloc_f890.allocate_hyperbolic_barycenter_phase182(
            symbols=symbols,
            alpha_scores=alpha_dict,
            gross_leverage=1.95,
            regime="BULL_LOW_VOL",
        )

        cap_limit = 0.05 * 1.95  # 0.0975
        for s, w in weights_f890.items():
            self.assertLessEqual(
                w,
                cap_limit + 1e-4,
                f"Stock {s} breached single-stock cap: {w} > {cap_limit}"
            )

        # Master UnifiedPortfolioAllocator
        res_master = allocate_portfolio_phase182(
            alpha_vector=alpha_dict,
            regime="BULL_LOW_VOL",
            gross_leverage=1.95,
        )
        for s, w in res_master.target_weights.items():
            self.assertLessEqual(
                w,
                cap_limit + 1e-4,
                f"Stock {s} breached master single-stock cap: {w} > {cap_limit}"
            )


if __name__ == "__main__":
    unittest.main()
