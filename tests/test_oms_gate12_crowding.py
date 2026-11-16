"""
Unit and Integration Test Suite for OMS Gate 12: Factor Crowding Shock Circuit Breaker.
Specification: docs/MULTI_FACTOR_ARCHITECTURAL_FEASIBILITY_REPORT.md §5.5 & ORIGINAL_REQUEST.md §R4.

Formulation:
    Shock_crowd = (Crowd_t - mu_crowd) / sigma_crowd >= 3.0

Rule:
    If Shock_crowd >= 3.0, trigger execution throttling:
    1. Switch Almgren-Chriss urgency to 'passive_twap'.
    2. Cap ADV participation rate to 0.50% (0.0050).
    3. Expand Leland dynamic buffer band by 2.0x.
"""

import math
import unittest
import numpy as np

from src.execution.oms_engine import (
    ExecutionOMSEngine,
    AlmgrenChrissScheduler,
    check_gate12_factor_crowding_shock,
    evaluate_gate11_and_gate12,
)


class TestOMSGate12FactorCrowdingShock(unittest.TestCase):
    def setUp(self):
        self.oms = ExecutionOMSEngine(db_path=":memory:")

    def test_gate12_exact_boundary_conditions(self):
        """
        Boundary tests at threshold max_shock_z = 3.0:
        - Z = 2.99: normal (throttled=False, urgency='normal', max_adv=0.0150, buffer=1.0)
        - Z = 3.00: throttled (throttled=True, urgency='passive_twap', max_adv=0.0050, buffer=2.0)
        - Z = 3.01: throttled
        - Z = 5.80: extreme shock throttled
        - Z = -2.10: negative shock normal
        """
        # 1. Z = 2.99 (just below boundary)
        is_th_299, p_299 = check_gate12_factor_crowding_shock(2.99, max_shock_z=3.0)
        self.assertFalse(is_th_299)
        self.assertFalse(p_299["throttled"])
        self.assertEqual(p_299["urgency"], "normal")
        self.assertEqual(p_299["max_adv_participation"], 0.0150)
        self.assertEqual(p_299["leland_buffer_multiplier"], 1.0)
        self.assertEqual(p_299["reason"], "PASSED")

        # 2. Z = 3.00 (exact boundary)
        is_th_300, p_300 = check_gate12_factor_crowding_shock(3.00, max_shock_z=3.0)
        self.assertTrue(is_th_300)
        self.assertTrue(p_300["throttled"])
        self.assertEqual(p_300["urgency"], "passive_twap")
        self.assertEqual(p_300["max_adv_participation"], 0.0050)
        self.assertEqual(p_300["leland_buffer_multiplier"], 2.0)
        self.assertIn("Gate 12 Breached: Factor Crowding Shock Z=3.00 >= 3.00 (Throttling Triggered)", p_300["reason"])

        # 3. Z = 3.01 (just above boundary)
        is_th_301, p_301 = check_gate12_factor_crowding_shock(3.01, max_shock_z=3.0)
        self.assertTrue(is_th_301)
        self.assertTrue(p_301["throttled"])
        self.assertEqual(p_301["urgency"], "passive_twap")
        self.assertEqual(p_301["max_adv_participation"], 0.0050)
        self.assertEqual(p_301["leland_buffer_multiplier"], 2.0)

        # 4. Z = 5.80 (extreme acute shock)
        is_th_580, p_580 = check_gate12_factor_crowding_shock(5.80, max_shock_z=3.0)
        self.assertTrue(is_th_580)
        self.assertTrue(p_580["throttled"])
        self.assertEqual(p_580["urgency"], "passive_twap")
        self.assertEqual(p_580["max_adv_participation"], 0.0050)
        self.assertEqual(p_580["leland_buffer_multiplier"], 2.0)

        # 5. Z = -2.10 (negative shock / diversification)
        is_th_neg, p_neg = check_gate12_factor_crowding_shock(-2.10, max_shock_z=3.0)
        self.assertFalse(is_th_neg)
        self.assertFalse(p_neg["throttled"])
        self.assertEqual(p_neg["urgency"], "normal")
        self.assertEqual(p_neg["max_adv_participation"], 0.0150)
        self.assertEqual(p_neg["leland_buffer_multiplier"], 1.0)

    def test_gate12_nan_and_none_sanitization(self):
        """
        Verify safe sanitization when crowding_shock_z is NaN, None, or string:
        Must sanitize safely to 0.0 without raising exceptions, resulting in normal unthrottled execution.
        """
        # None input
        is_th_none, p_none = check_gate12_factor_crowding_shock(None, max_shock_z=3.0)
        self.assertFalse(is_th_none)
        self.assertFalse(p_none["throttled"])
        self.assertEqual(p_none["shock_z"], 0.0)

        # NaN input
        is_th_nan, p_nan = check_gate12_factor_crowding_shock(float("nan"), max_shock_z=3.0)
        self.assertFalse(is_th_nan)
        self.assertFalse(p_nan["throttled"])
        self.assertEqual(p_nan["shock_z"], 0.0)

        # Invalid string
        is_th_str, p_str = check_gate12_factor_crowding_shock("invalid", max_shock_z=3.0)
        self.assertFalse(is_th_str)
        self.assertFalse(p_str["throttled"])
        self.assertEqual(p_str["shock_z"], 0.0)

    def test_gate12_almgren_chriss_linear_twap_trajectory(self):
        """
        Verify that AlmgrenChrissScheduler with strategy_tier='passive_twap'
        produces an exact linear TWAP trajectory with equal tranche shares,
        strictly satisfies max - min <= 1, sum == total_quantity, min >= 0,
        and never generates negative slices or rounding artifacts on half-integers.
        """
        total_quantity = 600
        adv = 1_000_000.0
        daily_volatility = 0.02
        n_slices = 6

        # Standard passive_twap call (with use_u_curve=True default)
        twap_slices = AlmgrenChrissScheduler.compute_trajectory(
            total_quantity=total_quantity,
            adv=adv,
            daily_volatility=daily_volatility,
            strategy_tier="passive_twap",
            n_slices=n_slices,
        )

        # In linear TWAP across 6 slices for 600 shares: each slice is exactly 100 shares
        self.assertEqual(len(twap_slices), n_slices)
        self.assertEqual(sum(twap_slices), total_quantity)
        for s in twap_slices:
            self.assertEqual(s, 100)

        # Verify difference compared to fast execution (which uses intraday U-curve)
        fast_slices = AlmgrenChrissScheduler.compute_trajectory(
            total_quantity=total_quantity,
            adv=adv,
            daily_volatility=daily_volatility,
            strategy_tier="fast",
            n_slices=n_slices,
        )
        self.assertEqual(sum(fast_slices), total_quantity)
        # Fast trajectory is U-curved: open/close slices > middle slices
        self.assertGreater(fast_slices[0], fast_slices[2])
        # TWAP slices are strictly uniform across all slices
        self.assertEqual(len(set(twap_slices)), 1)

        # Adversarial half-integer and small quantity test vectors (Reviewer & Challenger findings)
        test_vectors = [
            (5, 10), (9, 18), (10, 20), (17, 34), (20, 40), (25, 50),
            (15, 10), (21, 14), (25, 10), (35, 10),
            (701, 7), (997, 11), (313, 5), (17, 3), (1, 5), (0, 4)
        ]
        for q, n in test_vectors:
            traj = AlmgrenChrissScheduler.compute_trajectory(
                total_quantity=q,
                adv=adv,
                daily_volatility=daily_volatility,
                strategy_tier="passive_twap",
                n_slices=n,
            )
            if q > 0 and n > 1:
                self.assertEqual(len(traj), n)
                self.assertEqual(sum(traj), q, f"Sum mismatch for Q={q}, N={n}")
                self.assertGreaterEqual(min(traj), 0, f"Negative slice in {traj} for Q={q}, N={n}")
                self.assertLessEqual(max(traj) - min(traj), 1, f"Spread > 1 in {traj} for Q={q}, N={n}")
            elif q <= 0 or n <= 1:
                self.assertEqual(traj, [q])

        # Verify non-TWAP deficit reconciliation guarantees min >= 0 and sum == Q
        for tier in ("fast", "medium", "slow"):
            for q in (1, 2, 3, 5, 7, 10):
                for n in (3, 5, 7):
                    s = AlmgrenChrissScheduler.compute_trajectory(
                        total_quantity=q,
                        adv=adv,
                        daily_volatility=daily_volatility,
                        strategy_tier=tier,
                        n_slices=n,
                    )
                    self.assertEqual(sum(s), q, f"Non-TWAP sum failed: {s} for Q={q}, N={n}")
                    self.assertGreaterEqual(min(s), 0, f"Non-TWAP negative slice in {s} for Q={q}, N={n}")

    def test_gate12_order_plan_generation_under_crowding_shock(self):
        """
        Verify that ExecutionOMSEngine.generate_order_plan properly enforces
        Gate 12 execution throttling when factor_shock_z >= 3.0:
        1. Clamps effective_max_adv_ratio to 0.0050.
        2. Sets urgency to 0.0 / passive_twap.
        3. Tags order plans and tranches as PASSIVE_TWAP.
        """
        preds = [{
            "symbol": "005930",
            "name": "Samsung Electronics",
            "market": "KOSPI",
            "action": "BUY",
            "target_price": 70000.0,
            "close_price": 70000.0,
            "adv": 100_000_000_000.0,  # 100 Billion KRW ADV
            "volatility_20d": 0.02,
        }]
        weights = {"005930": 0.05}

        # 1. Normal execution (factor_shock_z = 0.0)
        plans_normal = self.oms.generate_order_plan(
            top_predictions=preds,
            portfolio_weights=weights,
            total_capital=100_000_000.0,
            factor_shock_z=0.0,
        )
        self.assertEqual(len(plans_normal), 1)
        order_norm = plans_normal[0]
        self.assertFalse(order_norm.get("throttled", False))

        # 2. Throttled execution under crowding shock (factor_shock_z = 3.50)
        plans_throttled = self.oms.generate_order_plan(
            top_predictions=preds,
            portfolio_weights=weights,
            total_capital=100_000_000.0,
            factor_shock_z=3.50,
        )
        self.assertEqual(len(plans_throttled), 1)
        order_th = plans_throttled[0]
        self.assertTrue(order_th.get("throttled", False))
        self.assertEqual(order_th.get("urgency"), 0.0)
        self.assertEqual(order_th.get("execution_strategy"), "PASSIVE_TWAP")

        # Verify tranches use PASSIVE_TWAP execution tags
        tranches = order_th.get("tranches", [])
        self.assertGreater(len(tranches), 0)
        for tr in tranches:
            self.assertEqual(tr.get("exec_type"), "PASSIVE_TWAP")

    def test_gate12_state_management_and_synthetic_rows_invariant(self):
        """
        Verify:
        - update_factor_crowding_state and reset_factor_crowding_state
        - Attachment as staticmethod on ExecutionOMSEngine
        - synthetic_rows == 0 strictly verified as native int 0
        """
        # Static method
        is_th, p = ExecutionOMSEngine.check_gate12_factor_crowding_shock(3.2)
        self.assertTrue(is_th)
        self.assertIs(type(p["synthetic_rows"]), int)
        self.assertNotIsInstance(p["synthetic_rows"], bool)
        self.assertEqual(p["synthetic_rows"], 0)

        # Instance state updates
        self.oms.update_factor_crowding_state(3.8)
        self.assertTrue(self.oms.is_factor_crowding_throttled)
        self.assertEqual(self.oms.factor_crowding_shock_z, 3.8)
        self.assertEqual(self.oms.throttling_params["max_adv_participation"], 0.0050)

        self.oms.reset_factor_crowding_state()
        self.assertFalse(self.oms.is_factor_crowding_throttled)
        self.assertEqual(self.oms.factor_crowding_shock_z, 0.0)
        self.assertEqual(self.oms.throttling_params["max_adv_participation"], 0.0150)


if __name__ == "__main__":
    unittest.main()
