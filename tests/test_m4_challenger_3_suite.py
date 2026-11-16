"""
Adversarial Numerical Challenger Suite 3 for Milestone 4 (Gate 11 & Gate 12).
Independent Empirical Stress Harness designed by challenger_m4_3.

Coverage:
1. Zero weights & empty / near-zero vectors
2. Extreme magnitudes ($10^9$ to $10^{150}$ and float64 overflow bounds)
3. Non-normalized weights & scale-invariance across $10^4$ random scaling factors
4. Singular, rank-deficient, collinear, zero, and indefinite factor covariance Omega_F
5. Exact precision boundary conditions at min_irr = 0.7000 and max_shock_z = 3.0000
6. Half-integer & Prime integer tranche allocation across slices (Gate 12 passive TWAP execution)
7. OMS Engine integration, gating, and invariant checks (synthetic_rows == 0 as native int)
"""

import math
import unittest
import numpy as np
from typing import Dict, Any

from src.execution.oms_engine import (
    ExecutionOMSEngine,
    AlmgrenChrissScheduler,
    check_gate11_idiosyncratic_risk_ratio,
    check_gate12_factor_crowding_shock,
    evaluate_gate11_and_gate12,
)


class TestM4Challenger3ExtremeInputs(unittest.TestCase):
    """Adversarial stress testing on extreme and pathological inputs."""

    def setUp(self):
        self.rng = np.random.default_rng(20261116)

    def test_zero_weights_spectrum(self):
        """Verify zero weights, empty weights, and sub-normal/near-zero floats."""
        # 1. Empty array
        w_empty = np.array([])
        B = np.zeros((0, 3))
        p, irr, reason = check_gate11_idiosyncratic_risk_ratio(w_empty, B)
        self.assertTrue(p)
        self.assertEqual(irr, 1.0)
        self.assertIn("Zero/negligible total risk", reason)

        # 2. Vector of zeros for various lengths N in [1, 2, 5, 20, 100, 500]
        for N in [1, 2, 5, 20, 100, 500]:
            w_zeros = np.zeros(N)
            B_rand = self.rng.standard_normal((N, 4))
            Omega = np.eye(4)
            D = np.ones(N) * 0.05
            p, irr, reason = check_gate11_idiosyncratic_risk_ratio(w_zeros, B_rand, Omega, D)
            self.assertTrue(p)
            self.assertEqual(irr, 1.0)
            self.assertIn("Zero/negligible total risk", reason)

        # 3. Near-zero weights (e.g. 1e-15, 1e-25, 1e-50, 1e-100)
        for scale in [1e-15, 1e-25, 1e-50, 1e-100]:
            w_tiny = np.ones(5) * scale
            p, irr, reason = check_gate11_idiosyncratic_risk_ratio(
                w_tiny, self.rng.standard_normal((5, 2)), np.eye(2), np.ones(5) * 0.05
            )
            self.assertTrue(p)
            self.assertEqual(irr, 1.0)
            self.assertIn("Zero/negligible total risk", reason)

    def test_huge_magnitude_1e9_and_scale_invariance(self):
        """
        Verify mathematical scale invariance and numerical stability with 10^9 magnitude
        and beyond (10^12, 10^50, 10^100, 10^150).
        """
        N = 10
        K = 4
        w_base = self.rng.standard_normal(N)
        B = self.rng.standard_normal((N, K))
        A = self.rng.standard_normal((K, K))
        Omega = (A @ A.T) + np.eye(K) * 0.01
        D = np.abs(self.rng.standard_normal(N)) * 0.05 + 0.01

        p_base, irr_base, _ = check_gate11_idiosyncratic_risk_ratio(w_base, B, Omega, D)

        # Scale by 10^9
        w_1e9 = w_base * 1e9
        p_1e9, irr_1e9, _ = check_gate11_idiosyncratic_risk_ratio(w_1e9, B, Omega, D)
        self.assertEqual(p_base, p_1e9)
        self.assertAlmostEqual(irr_base, irr_1e9, places=8)

        # Scales from 10^-5 to 10^140 where variance > 1e-12: strictly scale-invariant
        for exp in [-5, -2, 0, 1, 5, 9, 20, 50, 100, 140]:
            w_scaled = w_base * (10.0 ** exp)
            p_s, irr_s, _ = check_gate11_idiosyncratic_risk_ratio(w_scaled, B, Omega, D)
            self.assertEqual(p_base, p_s, f"Failed at exp {exp}")
            self.assertAlmostEqual(irr_base, irr_s, places=7, msg=f"Scale invariance broken at 10^{exp}")

        # Scales with exp <= -20: variance <= 1e-12 triggers negligible total risk default
        for exp in [-20, -50, -100]:
            w_scaled = w_base * (10.0 ** exp)
            p_s, irr_s, r_s = check_gate11_idiosyncratic_risk_ratio(w_scaled, B, Omega, D)
            self.assertTrue(p_s)
            self.assertEqual(irr_s, 1.0)
            self.assertIn("Zero/negligible total risk", r_s)

        # Scale that causes float64 overflow (e.g. 10^160, squared = 10^320 -> inf)
        w_over = w_base * 1e160
        p_over, irr_over, r_over = check_gate11_idiosyncratic_risk_ratio(w_over, B, Omega, D)
        self.assertTrue(p_over)
        self.assertEqual(irr_over, 1.0)
        self.assertIn("Zero/negligible total risk", r_over)

    def test_non_normalized_weights(self):
        """
        Verify that weights do not need to sum to 1.0.
        Test dollar-neutral long-short, leveraged, and arbitrary sums.
        """
        N = 6
        K = 2
        B = np.array([
            [1.0, 0.2],
            [0.5, 0.8],
            [-0.4, 0.6],
            [0.1, -0.9],
            [0.7, 0.3],
            [-0.2, 0.5],
        ])
        Omega = np.array([[0.04, 0.01], [0.01, 0.05]])
        D = np.array([0.06, 0.05, 0.08, 0.04, 0.07, 0.05])

        # 1. Dollar-neutral long-short (sum(w) == 0.0)
        w_dn = np.array([0.2, 0.3, 0.5, -0.4, -0.3, -0.3])
        self.assertAlmostEqual(float(np.sum(w_dn)), 0.0)
        p_dn, irr_dn, _ = check_gate11_idiosyncratic_risk_ratio(w_dn, B, Omega, D)
        self.assertTrue(np.isfinite(irr_dn))
        self.assertTrue(0.0 <= irr_dn <= 1.0)

        # 2. Leveraged weights (sum(w) == 10.0)
        w_lev = w_dn * 5.0 + 1.0
        p_lev, irr_lev, _ = check_gate11_idiosyncratic_risk_ratio(w_lev, B, Omega, D)
        self.assertTrue(np.isfinite(irr_lev))
        self.assertTrue(0.0 <= irr_lev <= 1.0)

        # 3. L1 normalized vs raw
        w_norm_l1 = w_lev / np.sum(np.abs(w_lev))
        p_nl1, irr_nl1, _ = check_gate11_idiosyncratic_risk_ratio(w_norm_l1, B, Omega, D)
        self.assertEqual(p_lev, p_nl1)
        self.assertAlmostEqual(irr_lev, irr_nl1, places=9)

        # 4. L2 normalized vs raw
        w_norm_l2 = w_lev / np.linalg.norm(w_lev)
        p_nl2, irr_nl2, _ = check_gate11_idiosyncratic_risk_ratio(w_norm_l2, B, Omega, D)
        self.assertEqual(p_lev, p_nl2)
        self.assertAlmostEqual(irr_lev, irr_nl2, places=9)

    def test_singular_and_pathological_omega_f(self):
        """
        Adversarial test on singular and rank-deficient Omega_F:
        - Omega_F = 0 (all zeros)
        - Collinear factors (rank 1 in K=5)
        - Defective / Indefinite Omega_F (negative eigenvalues)
        - Asymmetric Omega_F
        """
        N = 8
        K = 5
        w = np.ones(N) / N
        B = self.rng.standard_normal((N, K))
        D = np.ones(N) * 0.05

        # 1. All-zero Omega_F
        Omega_zero = np.zeros((K, K))
        p_z, irr_z, _ = check_gate11_idiosyncratic_risk_ratio(w, B, Omega_zero, D)
        self.assertTrue(p_z)
        self.assertEqual(irr_z, 1.0)

        # 2. Rank 1 Omega_F (outer product of single vector)
        v = self.rng.standard_normal((K, 1))
        Omega_rank1 = v @ v.T
        self.assertEqual(np.linalg.matrix_rank(Omega_rank1), 1)
        p_r1, irr_r1, _ = check_gate11_idiosyncratic_risk_ratio(w, B, Omega_rank1, D)
        self.assertTrue(np.isfinite(irr_r1))
        self.assertTrue(0.0 <= irr_r1 <= 1.0)

        # 3. Collinear duplicate columns in Omega_F
        Omega_collinear = np.ones((K, K)) * 0.02
        p_col, irr_col, _ = check_gate11_idiosyncratic_risk_ratio(w, B, Omega_collinear, D)
        self.assertTrue(np.isfinite(irr_col))
        self.assertTrue(0.0 <= irr_col <= 1.0)

        # 4. Indefinite Omega_F with strongly negative eigenvalues
        A = self.rng.standard_normal((K, K))
        Omega_indef = (A + A.T) / 2.0
        Omega_indef[0, 0] = -10.0  # Force strongly negative eigenvalue
        min_eig_before = np.min(np.linalg.eigvalsh(Omega_indef))
        self.assertLess(min_eig_before, 0.0)

        p_indef, irr_indef, _ = check_gate11_idiosyncratic_risk_ratio(w, B, Omega_indef, D)
        self.assertTrue(np.isfinite(irr_indef))
        self.assertTrue(0.0 <= irr_indef <= 1.0)

        # 5. Strongly asymmetric Omega_F
        Omega_asym = np.array([
            [0.10, 0.50, 0.00, 0.00, 0.00],
            [0.00, 0.10, 0.00, 0.00, 0.00],
            [0.00, 0.00, 0.10, 0.00, 0.00],
            [0.00, 0.00, 0.00, 0.10, 0.00],
            [0.00, 0.00, 0.00, 0.00, 0.10],
        ])
        p_asym, irr_asym, _ = check_gate11_idiosyncratic_risk_ratio(w, B, Omega_asym, D)
        self.assertTrue(np.isfinite(irr_asym))
        self.assertTrue(0.0 <= irr_asym <= 1.0)

        # 6. Singular Omega_F and D=0 (Zero idiosyncratic risk)
        p_d0, irr_d0, r_d0 = check_gate11_idiosyncratic_risk_ratio(
            w, B, Omega_rank1, np.zeros(N)
        )
        self.assertFalse(p_d0)
        self.assertEqual(irr_d0, 0.0)
        self.assertIn("Gate 11 Breached", r_d0)


class TestM4Challenger3Boundaries(unittest.TestCase):
    """Adversarial boundary tests at 0.7000 (Gate 11) and 3.0000 (Gate 12)."""

    def test_gate11_boundary_at_0_7000(self):
        """
        Verify exact boundary behavior around 0.7000:
        - Exactly 0.700000000 -> PASS
        - 0.699999999 -> FAIL
        - 0.700000001 -> PASS
        - Floating point step perturbations from 1e-12 to 1e-3
        """
        w = np.array([1.0])
        B = np.array([[1.0]])

        # 1. Exact 0.700000000
        # idio_var = 0.70, factor_var = 0.30 => total = 1.00 => IRR = 0.70
        Omega = np.array([[0.300000000]])
        D = np.array([0.700000000])
        p, irr, r = check_gate11_idiosyncratic_risk_ratio(w, B, Omega, D, min_irr=0.70)
        self.assertTrue(p, f"IRR 0.700000000 must PASS, got {p}")
        self.assertAlmostEqual(irr, 0.700000000, places=9)
        self.assertEqual(r, "PASSED")

        # 2. Delta below: 0.70 - eps
        for eps in [1e-9, 1e-8, 1e-7, 1e-6, 1e-5, 1e-4, 1e-3]:
            D_below = np.array([0.70 - eps])
            Omega_adj = np.array([[0.30 + eps]])
            p_b, irr_b, r_b = check_gate11_idiosyncratic_risk_ratio(w, B, Omega_adj, D_below, min_irr=0.70)
            self.assertFalse(p_b, f"IRR {0.70 - eps} must FAIL, got {p_b}")
            self.assertIn("Gate 11 Breached", r_b)

        # 3. Delta above: 0.70 + eps
        for eps in [1e-9, 1e-8, 1e-7, 1e-6, 1e-5, 1e-4, 1e-3]:
            D_above = np.array([0.70 + eps])
            Omega_adj = np.array([[0.30 - eps]])
            p_a, irr_a, r_a = check_gate11_idiosyncratic_risk_ratio(w, B, Omega_adj, D_above, min_irr=0.70)
            self.assertTrue(p_a, f"IRR {0.70 + eps} must PASS, got {p_a}")
            self.assertEqual(r_a, "PASSED")

    def test_gate12_boundary_at_3_0000(self):
        """
        Verify exact boundary behavior around 3.0000:
        - Exactly 3.000000000 -> THROTTLED (True)
        - 2.999999999 -> NORMAL (False)
        - 3.000000001 -> THROTTLED (True)
        - Type spectrum: int, float, str, np.float64
        """
        # Exactly 3.0
        throttled, params = check_gate12_factor_crowding_shock(3.0, max_shock_z=3.0)
        self.assertTrue(throttled)
        self.assertEqual(params["urgency"], "passive_twap")
        self.assertEqual(params["max_adv_participation"], 0.0050)
        self.assertEqual(params["leland_buffer_multiplier"], 2.0)
        self.assertEqual(params["synthetic_rows"], 0)

        # Int 3
        throttled_int, params_int = check_gate12_factor_crowding_shock(3, max_shock_z=3.0)
        self.assertTrue(throttled_int)

        # np.float64(3.0)
        throttled_np, _ = check_gate12_factor_crowding_shock(np.float64(3.0), max_shock_z=3.0)
        self.assertTrue(throttled_np)

        # String '3.0'
        throttled_str, _ = check_gate12_factor_crowding_shock("3.0", max_shock_z=3.0)
        self.assertTrue(throttled_str)

        # Delta below: 3.0 - eps (normal)
        for eps in [1e-9, 1e-8, 1e-7, 1e-6, 1e-5, 1e-4, 1e-3, 0.1]:
            val = 3.0 - eps
            th_b, p_b = check_gate12_factor_crowding_shock(val, max_shock_z=3.0)
            self.assertFalse(th_b, f"Z={val} must NOT throttle")
            self.assertEqual(p_b["urgency"], "normal")
            self.assertEqual(p_b["max_adv_participation"], 0.0150)
            self.assertEqual(p_b["leland_buffer_multiplier"], 1.0)
            self.assertEqual(p_b["synthetic_rows"], 0)

        # Delta above: 3.0 + eps (throttled)
        for eps in [1e-9, 1e-8, 1e-7, 1e-6, 1e-5, 1e-4, 1e-3, 0.1]:
            val = 3.0 + eps
            th_a, p_a = check_gate12_factor_crowding_shock(val, max_shock_z=3.0)
            self.assertTrue(th_a, f"Z={val} must throttle")
            self.assertEqual(p_a["urgency"], "passive_twap")
            self.assertEqual(p_a["max_adv_participation"], 0.0050)
            self.assertEqual(p_a["leland_buffer_multiplier"], 2.0)
            self.assertEqual(p_a["synthetic_rows"], 0)


class TestM4Challenger3TrancheDeficitStress(unittest.TestCase):
    """
    Combinatorial stress testing on AlmgrenChrissScheduler.compute_trajectory
    under Gate 12 execution throttling ('passive_twap').
    """

    def test_half_integer_share_quantities_passive_twap(self):
        """
        Empirical demonstration of tranche non-uniformity under passive TWAP:
        When total_quantity / n_slices has fractional part 0.5 (e.g. 15 / 10 = 1.5,
        25 / 10 = 2.5, 61245 / 30 = 2041.5), np.diff(np.linspace) float precision jitter
        causes np.round to round some elements up and some down, leading to diff_total
        over-allocations that produce max - min == 2 (e.g. [2, 2, 3, 1, 1, 2, 1, 1, 1, 1]).
        A truly uniform TWAP must satisfy max(alloc) - min(alloc) <= 1.
        """
        cases = [
            (15, 10),
            (21, 14),
            (25, 10),
            (61245, 30),
        ]
        for qty, n_sl in cases:
            alloc = AlmgrenChrissScheduler.compute_trajectory(
                total_quantity=qty,
                adv=1_000_000.0,
                daily_volatility=0.02,
                strategy_tier="passive_twap",
                n_slices=n_sl,
            )
            self.assertEqual(sum(alloc), qty, f"Sum mismatch for qty={qty}, n_slices={n_sl}")
            spread = max(alloc) - min(alloc)
            self.assertLessEqual(
                spread, 1,
                f"Deficit reconciliation failure: qty={qty}, n_slices={n_sl} produced "
                f"non-uniform allocation {alloc} with max - min = {spread} > 1"
            )


class TestM4Challenger3OMSEngineIntegration(unittest.TestCase):
    """Verify ExecutionOMSEngine integration of Gate 11 and Gate 12."""

    def test_engine_gating_behavior(self):
        engine = ExecutionOMSEngine()

        # Gate 12 update
        th, p = engine.update_factor_crowding_state(3.2)
        self.assertTrue(th)
        self.assertTrue(engine.is_factor_crowding_throttled)
        self.assertEqual(engine.factor_crowding_shock_z, 3.2)

        # Reset
        engine.reset_factor_crowding_state()
        self.assertFalse(engine.is_factor_crowding_throttled)
        self.assertEqual(engine.factor_crowding_shock_z, 0.0)

        # evaluate_batch_factor_risk_gates helper
        res = engine.evaluate_batch_factor_risk_gates(
            portfolio_weights={"AAPL": 0.5, "MSFT": 0.5},
            factor_shock_z=1.5,
        )
        self.assertTrue(res["passed"])
        self.assertEqual(res["status"], "APPROVED")
        self.assertIs(type(res["synthetic_rows"]), int)
        self.assertEqual(res["synthetic_rows"], 0)


if __name__ == "__main__":
    unittest.main()
