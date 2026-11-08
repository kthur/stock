"""
tests/test_f890_f891_deep_adversarial_challenge.py
==================================================
Empirical Adversarial Stress Harness for Release R180 Features F890 & F891.
Role: Code-Executing Adversarial Challenger (challenger_m3_it2_1).

Empirical Challenge Objectives:
1. Curvature c modulation verification across c in [0.01, 0.99]:
   - Confirm curvature genuinely alters barycenter allocations (Euclidean facade elimination).
   - Confirm capital retention at origin / turnover contraction under increasing curvature.
   - Confirm total mass preservation: |sum(w_bary) - sum(w_target)| < 1e-5 across all c and leverages.
2. Poincaré geodesic distance metric axioms & Riemannian Wasserstein properties:
   - Non-negativity, symmetry, identity of indiscernibles, triangle inequality.
   - Wasserstein-2 RMS coupling distance behavior.
3. Contango Lock & 1.95x leverage frontiers:
   - Precise boundary testing at 0.9200000 vs 0.9200001, days 4 vs 5.
   - Leverage capping under unlock vs locked conditions.
   - Crisis / Backwardation / MCSI override clamps.
4. Edge cases & System Invariants:
   - Zero-mass vectors, Dirac deltas, N=500 high-dimensional scaling.
   - synthetic_rows == 0 native int across all outputs.
"""

import math
import unittest
import numpy as np
import pandas as pd

from src.risk.hyperbolic_optimal_transport_allocator import (
    HyperbolicOptimalTransportAllocator,
    LorentzPoincareWassersteinAllocator,
    compute_poincare_wasserstein_barycenter,
    mobius_addition,
    poincare_exponential_map,
    poincare_logarithmic_map,
)
from src.risk.dynamic_regime_leverage_allocator import (
    DynamicRegimeLeverageAllocator,
    RegimeCompoundingLeverageAllocator,
)
from src.risk.unified_portfolio_allocator import (
    UnifiedPortfolioAllocator,
    allocate_portfolio_phase182,
)


class TestF890DeepAdversarialChallenge(unittest.TestCase):
    """Deep adversarial verification of Feature F890."""

    def test_adv_curvature_sweep_genuine_modulation(self):
        """Verify that curvature c genuinely modulates allocations across c in [0.01, 0.99]."""
        w_curr = np.array([0.05, 0.15, 0.30, 0.50], dtype=np.float64)
        w_target = np.array([0.50, 0.30, 0.15, 0.05], dtype=np.float64)

        curvatures = [0.01, 0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.99]
        allocations = []
        turnovers = []

        for c in curvatures:
            res = compute_poincare_wasserstein_barycenter(w_curr, w_target, curvature=c, epsilon=0.05)
            w_bary = res["barycenter_weights"]
            allocations.append(w_bary)

            # Mass preservation check
            self.assertAlmostEqual(
                float(np.sum(w_bary)),
                float(np.sum(w_target)),
                places=5,
                msg=f"Mass preservation failed at c={c}"
            )
            self.assertEqual(res["synthetic_rows"], 0)
            self.assertIs(type(res["synthetic_rows"]), int)

            # Compute turnover relative to current portfolio: sum(|w_bary - w_curr|) / 2
            to_curr = 0.5 * float(np.sum(np.abs(w_bary - w_curr)))
            turnovers.append(to_curr)

        # 1. Verify that distinct curvatures produce distinctly different allocation vectors
        for i in range(len(curvatures)):
            for j in range(i + 1, len(curvatures)):
                diff = np.linalg.norm(allocations[i] - allocations[j])
                self.assertGreater(
                    diff,
                    1e-4,
                    f"Curvatures c={curvatures[i]} and c={curvatures[j]} produced identical allocations (Euclidean facade!)"
                )

        # 2. Verify capital retention near origin:
        # As c increases from 0.01 to 0.99, transport progression alpha contracts,
        # retaining more mass at current position w_curr. Thus turnover to w_curr should decrease.
        self.assertLess(
            turnovers[-1],
            turnovers[0],
            f"Higher curvature did not retain capital near origin: TO(c={curvatures[-1]})={turnovers[-1]} vs TO(c={curvatures[0]})={turnovers[0]}"
        )

    def test_adv_curvature_mass_preservation_stress(self):
        """Verify mass preservation across multi-level leverages L in [0.05, 3.0] and c in [0.01, 0.99]."""
        rng = np.random.RandomState(42)
        n_assets = 10
        w_c_base = rng.uniform(0.01, 1.0, n_assets)
        w_c = w_c_base / np.sum(w_c_base)

        curvatures = [0.01, 0.10, 0.25, 0.50, 0.85, 0.99]
        target_masses = [0.05, 0.20, 0.50, 1.00, 1.50, 1.95, 2.50, 3.00]

        for c in curvatures:
            for L in target_masses:
                w_t = (rng.uniform(0.01, 1.0, n_assets) / 10.0)
                w_t = (w_t / np.sum(w_t)) * L

                res = compute_poincare_wasserstein_barycenter(w_c, w_t, curvature=c, epsilon=0.03)
                w_b = res["barycenter_weights"]

                mass_diff = abs(float(np.sum(w_b)) - L)
                self.assertLess(
                    mass_diff,
                    1e-5,
                    f"Total mass preservation violated at c={c}, L={L}: error={mass_diff}"
                )
                self.assertTrue(np.all(w_b >= -1e-12), f"Negative weight encountered at c={c}, L={L}")

    def test_adv_poincare_metric_axioms_exhaustive(self):
        """Exhaustively verify Poincaré geodesic metric axioms under random points in Poincaré ball."""
        rng = np.random.RandomState(1337)
        c = 0.40
        max_r = (1.0 / math.sqrt(c)) - 1e-3

        # Generate 50 points inside B_c^3
        points = []
        for _ in range(50):
            d = rng.randn(3)
            d = d / np.linalg.norm(d)
            r = rng.uniform(0.0, 0.99) * max_r
            points.append(d * r)

        alloc = HyperbolicOptimalTransportAllocator()

        # Axiom 1 & 2: Identity of Indiscernibles and Positivity
        for p in points:
            d_self = alloc.poincare_geodesic_distance(p, p, c=c)
            self.assertAlmostEqual(d_self, 0.0, places=9)

        # Axiom 3: Symmetry
        for i in range(25):
            p1 = points[i]
            p2 = points[i + 25]
            d12 = alloc.poincare_geodesic_distance(p1, p2, c=c)
            d21 = alloc.poincare_geodesic_distance(p2, p1, c=c)
            self.assertAlmostEqual(d12, d21, places=8)
            self.assertGreaterEqual(d12, 0.0)

        # Axiom 4: Triangle Inequality for 100 random triplets
        for _ in range(100):
            idx = rng.choice(50, 3, replace=False)
            x, y, z = points[idx[0]], points[idx[1]], points[idx[2]]
            d_xy = alloc.poincare_geodesic_distance(x, y, c=c)
            d_yz = alloc.poincare_geodesic_distance(y, z, c=c)
            d_xz = alloc.poincare_geodesic_distance(x, z, c=c)
            self.assertLessEqual(
                d_xz,
                d_xy + d_yz + 1e-6,
                f"Triangle inequality violated: d(x,z)={d_xz} > d(x,y)={d_xy} + d(y,z)={d_yz}"
            )

    def test_adv_riemannian_wasserstein_distance_properties(self):
        """Verify Riemannian Wasserstein coupling distance behavior in barycenter output."""
        w_curr = np.array([0.25, 0.25, 0.25, 0.25])

        # Case 1: Identical current and target -> entropic coupling distance is bounded by entropic blur (< 0.01)
        res_same = compute_poincare_wasserstein_barycenter(w_curr, w_curr.copy(), curvature=0.30, epsilon=0.05)
        self.assertLess(res_same["hyperbolic_geodesic_distance"], 0.01)
        self.assertLess(res_same["wasserstein_distance"], 0.01)

        # Case 2: Divergent target -> distance must be orders of magnitude larger
        w_target = np.array([0.80, 0.10, 0.05, 0.05])
        res_diff = compute_poincare_wasserstein_barycenter(w_curr, w_target, curvature=0.30, epsilon=0.05)
        self.assertGreater(res_diff["hyperbolic_geodesic_distance"], 0.10)
        self.assertGreater(res_diff["hyperbolic_geodesic_distance"], 10.0 * res_same["hyperbolic_geodesic_distance"])
        self.assertGreater(res_diff["wasserstein_distance"], 0.10)

        # Case 3: More distant target -> distance should be larger
        w_target_far = np.array([1.0, 0.0, 0.0, 0.0])
        res_far = compute_poincare_wasserstein_barycenter(w_curr, w_target_far, curvature=0.30)
        self.assertGreaterEqual(res_far["hyperbolic_geodesic_distance"], res_diff["hyperbolic_geodesic_distance"])

    def test_adv_high_dimensional_stress_500_assets(self):
        """Stress test Poincaré barycenter on N=500 assets under extreme leverage."""
        rng = np.random.RandomState(999)
        N = 500
        w_c = rng.exponential(scale=1.0, size=N)
        w_c /= np.sum(w_c)
        w_t = rng.exponential(scale=2.0, size=N)
        w_t = (w_t / np.sum(w_t)) * 1.95

        res = compute_poincare_wasserstein_barycenter(w_c, w_t, curvature=0.25, epsilon=0.08, max_iter=30)
        w_b = res["barycenter_weights"]

        self.assertEqual(len(w_b), N)
        self.assertAlmostEqual(float(np.sum(w_b)), 1.95, places=4)
        self.assertTrue(np.all(np.isfinite(w_b)))
        self.assertTrue(np.all(w_b >= 0.0))
        self.assertEqual(res["synthetic_rows"], 0)


class TestF891DeepAdversarialChallenge(unittest.TestCase):
    """Deep adversarial verification of Feature F891."""

    def setUp(self):
        self.alloc = DynamicRegimeLeverageAllocator()

    def test_adv_contango_lock_boundary_matrix(self):
        """Exhaustive boundary testing of contango lock condition (VTS <= 0.92, days >= 5)."""
        test_cases = [
            # (days, vts, expected)
            (5, 0.9200000, True),
            (5, 0.9200001, False),
            (5, 0.9199999, True),
            (4, 0.9200000, False),
            (4, 0.8500000, False),
            (6, 0.9200000, True),
            (6, 0.9200001, False),
            (10, 0.7000000, True),
            (0, 0.5000000, False),
            (-1, 0.5000000, False),
            (5, 1.0000000, False),
            (5, 1.5000000, False),
        ]
        for days, vts, expected in test_cases:
            res = self.alloc.check_contango_lock(contango_days=days, vts_ratio=vts)
            self.assertEqual(
                res,
                expected,
                f"Contango lock failed for days={days}, vts={vts}: got {res}, expected {expected}"
            )

    def test_adv_bull_low_vol_leverage_ceiling_lock_vs_unlocked(self):
        """Verify that BULL_LOW_VOL leverage strictly requires contango lock to reach 1.95x."""
        # Max momentum condition: trend_50d high, vol_20d low
        trend = 0.50
        vol = 0.08

        # Condition 1: Contango locked (5 days, VTS=0.88)
        lev_locked = self.alloc.compute_regime_compounding_leverage(
            regime="BULL_LOW_VOL",
            contango_days=5,
            vts_ratio=0.88,
            trend_50d=trend,
            vol_20d=vol,
        )
        self.assertGreaterEqual(float(lev_locked), 1.85)
        self.assertLessEqual(float(lev_locked), 1.950001)

        # Condition 2: 4 days contango -> must NOT reach 1.95x, max is 1.85x
        lev_day4 = self.alloc.compute_regime_compounding_leverage(
            regime="BULL_LOW_VOL",
            contango_days=4,
            vts_ratio=0.88,
            trend_50d=trend,
            vol_20d=vol,
        )
        self.assertLessEqual(float(lev_day4), 1.850001)

        # Condition 3: VTS = 0.93 -> must NOT reach 1.95x, max is 1.85x
        lev_vts93 = self.alloc.compute_regime_compounding_leverage(
            regime="BULL_LOW_VOL",
            contango_days=10,
            vts_ratio=0.93,
            trend_50d=trend,
            vol_20d=vol,
        )
        self.assertLessEqual(float(lev_vts93), 1.850001)

    def test_adv_crisis_and_panic_regime_frontiers(self):
        """Verify all crisis permutations strictly compress leverage <= 0.20x."""
        crisis_regimes = ["PANIC_CRISIS", "CRISIS", "panic_crisis", "crisis"]
        for cr in crisis_regimes:
            lim = self.alloc.get_regime_leverage_limit(cr)
            self.assertLessEqual(float(lim), 0.200001)

            # Even with 100 days contango and huge bull trend, crisis regime must clamp leverage <= 0.20x
            lev = self.alloc.compute_regime_compounding_leverage(
                regime=cr,
                contango_days=100,
                vts_ratio=0.70,
                trend_50d=1.00,
                vol_20d=0.05,
            )
            self.assertLessEqual(float(lev), 0.200001)

    def test_adv_mcsi_and_backwardation_protective_gating(self):
        """Verify MCSI systemic risk override and backwardation TSR cap."""
        # MCSI >= 2.50 forces crisis clamp
        lev_mcsi = self.alloc.compute_regime_compounding_leverage(
            regime="BULL_LOW_VOL",
            contango_days=10,
            vts_ratio=0.80,
            trend_50d=0.50,
            vol_20d=0.08,
            mcsi_score=2.65,
        )
        self.assertLessEqual(float(lev_mcsi), 0.200001)

        # TSR backwardation capping in evaluate_dynamic_leverage_frontier
        # TSR > 1.25 -> 0.15
        frontier_res = self.alloc.evaluate_dynamic_leverage_frontier(
            current_nav=1.0,
            vix=35.0,
            vix_history=[25.0] * 20,
            tsr_ratio=1.28,
            regime="BULL_LOW_VOL",
        )
        self.assertLessEqual(float(frontier_res), 0.200001)

    def test_adv_capital_conservation_under_dynamic_leverage(self):
        """Verify master portfolio allocator satisfies Net Equity <= Gross Equity across 10 random setups."""
        rng = np.random.RandomState(777)
        regimes = ["BULL_LOW_VOL", "BULL_HIGH_VOL", "SIDEWAYS", "BEAR_LOW_VOL", "CRISIS"]

        for reg in regimes:
            symbols = [f"STOCK_{i}" for i in range(15)]
            alphas = {s: float(rng.uniform(-2.0, 3.0)) for s in symbols}

            res = allocate_portfolio_phase182(
                alpha_vector=alphas,
                regime=reg,
                contango_days=6 if "BULL" in reg else 0,
                vts_ratio=0.88 if "BULL" in reg else 1.10,
            )

            # Invariant: Net leverage <= Gross leverage
            self.assertLessEqual(res.net_leverage, res.gross_leverage + 1e-6)
            # Invariant: synthetic_rows == 0
            self.assertEqual(res.metadata["synthetic_rows"], 0)
            self.assertIs(type(res.metadata["synthetic_rows"]), int)
            # Target weights non-negative
            for w in res.target_weights.values():
                self.assertGreaterEqual(w, -1e-7)


if __name__ == "__main__":
    unittest.main()
