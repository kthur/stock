"""
Standalone Empirical Stress Test Suite for Milestone 4:
Execution OMS Throttling Integration & Almgren-Chriss Scheduler under Factor Shock.

Role: challenger_m4_2 (Execution & Integration Challenger)
Verifies:
1. ADV participation rate strictly clamped to <= 0.0050 when Z = 3.5.
2. Leland dynamic buffer band doubling: marginal rebalances passing at Z = 0.0 are suppressed (held) at Z = 3.5.
3. Almgren-Chriss scheduler under 'passive_twap': equal distribution across slices for odd and prime share quantities (e.g., 701 shares across 7 slices).
4. Batch factor risk gating in generate_order_plan: order batches with portfolio IRR < 0.70 are rejected (empty/safeguarded plan).
5. Numerical invariants: synthetic_rows == 0 strictly verified as native int.
"""

import math
import unittest
import numpy as np

from src.execution.oms_engine import (
    ExecutionOMSEngine,
    AlmgrenChrissScheduler,
    check_gate11_idiosyncratic_risk_ratio,
    check_gate12_factor_crowding_shock,
    evaluate_gate11_and_gate12,
    OrderPlanList,
)
from src.risk.portfolio_allocator import PortfolioAllocator


class TestOMSExecutionThrottlingADVClamp(unittest.TestCase):
    """Empirical verification of Gate 12 ADV participation rate clamping."""

    def setUp(self):
        self.oms = ExecutionOMSEngine(db_path=":memory:")

    def test_adv_participation_rate_strictly_clamped_at_z35(self):
        """
        Verify that when factor_shock_z = 3.5, the order plan's ADV participation
        rate is strictly clamped to <= 0.0050 (0.50% ADV).
        """
        adv_val = 100_000_000.0  # 100M KRW ADV
        tot_cap = 100_000_000.0  # 100M KRW Portfolio
        # Target weight 10% -> 10,000,000 KRW requested order value (10% ADV)
        pred = [{
            "symbol": "005930",
            "name": "Samsung",
            "market": "KOSPI",
            "action": "BUY",
            "close_price": 50000.0,
            "adv": adv_val,
            "expected_return": 10.0,
            "volatility_20d": 0.02,
        }]
        weights = {"005930": 0.10}

        plans = self.oms.generate_order_plan(
            top_predictions=pred,
            portfolio_weights=weights,
            total_capital=tot_cap,
            factor_shock_z=3.5,
            use_leland_buffer=False,
            max_adv_ratio=0.05,
        )

        self.assertEqual(len(plans), 1)
        plan = plans[0]

        # Order amount must not exceed 0.50% of ADV = 500,000 KRW
        max_allowed_amount = 0.0050 * adv_val
        self.assertLessEqual(plan["order_amount"], max_allowed_amount + 1e-6)
        actual_participation = plan["order_amount"] / adv_val
        self.assertLessEqual(actual_participation, 0.00500001)

        # Quantity must match capped order amount // price = 500,000 // 50,000 = 10 shares
        self.assertEqual(plan["quantity"], 10)
        self.assertEqual(plan["order_amount"], 500_000.0)

        # Execution strategy must be forced to PASSIVE_TWAP
        self.assertEqual(plan["execution_strategy"], "PASSIVE_TWAP")
        self.assertTrue(plan.get("throttled", False))
        self.assertEqual(plan.get("urgency", 1.0), 0.0)

    def test_adv_participation_comparison_z0_vs_z35(self):
        """
        Direct comparison:
        - At Z = 0.0 (normal): 5% ADV permitted (order_amount = 5,000,000 KRW).
        - At Z = 3.5 (throttled): strictly clamped to 0.5% ADV (order_amount = 500,000 KRW).
        """
        adv_val = 100_000_000.0
        tot_cap = 100_000_000.0
        pred = [{
            "symbol": "005930",
            "name": "Samsung",
            "market": "KOSPI",
            "action": "BUY",
            "close_price": 50000.0,
            "adv": adv_val,
            "expected_return": 10.0,
            "volatility_20d": 0.02,
        }]
        weights = {"005930": 0.05}  # 5,000,000 KRW requested

        # Normal condition Z = 0.0
        plans_z0 = self.oms.generate_order_plan(
            top_predictions=pred,
            portfolio_weights=weights,
            total_capital=tot_cap,
            factor_shock_z=0.0,
            use_leland_buffer=False,
            max_adv_ratio=0.05,
        )
        self.assertEqual(len(plans_z0), 1)
        plan_z0 = plans_z0[0]
        self.assertEqual(plan_z0["order_amount"], 5_000_000.0)
        self.assertAlmostEqual(plan_z0["order_amount"] / adv_val, 0.05, places=5)
        self.assertFalse(plan_z0.get("throttled", False))

        # Throttled condition Z = 3.5
        plans_z35 = self.oms.generate_order_plan(
            top_predictions=pred,
            portfolio_weights=weights,
            total_capital=tot_cap,
            factor_shock_z=3.5,
            use_leland_buffer=False,
            max_adv_ratio=0.05,
        )
        self.assertEqual(len(plans_z35), 1)
        plan_z35 = plans_z35[0]
        self.assertEqual(plan_z35["order_amount"], 500_000.0)
        self.assertAlmostEqual(plan_z35["order_amount"] / adv_val, 0.005, places=5)
        self.assertTrue(plan_z35.get("throttled", False))

    def test_adv_clamp_boundary_z299_vs_z300(self):
        """
        Boundary condition test at threshold Z = 3.0:
        - Z = 2.99: unthrottled (up to 5% ADV permitted).
        - Z = 3.00: throttled (clamped to 0.50% ADV).
        """
        adv_val = 100_000_000.0
        tot_cap = 100_000_000.0
        pred = [{
            "symbol": "005930",
            "name": "Samsung",
            "market": "KOSPI",
            "action": "BUY",
            "close_price": 50000.0,
            "adv": adv_val,
            "expected_return": 10.0,
            "volatility_20d": 0.02,
        }]
        weights = {"005930": 0.03}  # 3,000,000 KRW requested (3.0% ADV)

        # Z = 2.99 (just below 3.0 threshold)
        plans_299 = self.oms.generate_order_plan(
            top_predictions=pred,
            portfolio_weights=weights,
            total_capital=tot_cap,
            crowding_shock_z=2.99,
            use_leland_buffer=False,
            max_adv_ratio=0.05,
        )
        self.assertEqual(len(plans_299), 1)
        self.assertFalse(plans_299[0].get("throttled", False))
        self.assertEqual(plans_299[0]["order_amount"], 3_000_000.0)

        # Z = 3.00 (exact threshold)
        plans_300 = self.oms.generate_order_plan(
            top_predictions=pred,
            portfolio_weights=weights,
            total_capital=tot_cap,
            crowding_shock_z=3.00,
            use_leland_buffer=False,
            max_adv_ratio=0.05,
        )
        self.assertEqual(len(plans_300), 1)
        self.assertTrue(plans_300[0].get("throttled", False))
        self.assertEqual(plans_300[0]["order_amount"], 500_000.0)
        self.assertLessEqual(plans_300[0]["order_amount"] / adv_val, 0.00500001)

    def test_adv_throttling_execution_strategy_and_tranches(self):
        """
        Verify that under Z = 3.5, execution strategy is PASSIVE_TWAP,
        slice_count is at least 4, and all tranches are tagged PASSIVE_TWAP.
        """
        adv_val = 200_000_000.0
        tot_cap = 100_000_000.0
        # 0.5% of 200M = 1,000,000 KRW -> 20 shares at 50,000 KRW
        pred = [{
            "symbol": "005930",
            "name": "Samsung",
            "market": "KOSPI",
            "action": "BUY",
            "close_price": 50000.0,
            "adv": adv_val,
            "expected_return": 10.0,
            "volatility_20d": 0.02,
        }]
        weights = {"005930": 0.05}

        plans = self.oms.generate_order_plan(
            top_predictions=pred,
            portfolio_weights=weights,
            total_capital=tot_cap,
            factor_shock_z=3.5,
            use_leland_buffer=False,
        )
        self.assertEqual(len(plans), 1)
        plan = plans[0]

        self.assertEqual(plan["execution_strategy"], "PASSIVE_TWAP")
        self.assertGreaterEqual(plan["slice_count"], 4)
        tranches = plan.get("tranches", [])
        self.assertGreater(len(tranches), 0)
        for tr in tranches:
            self.assertEqual(tr["exec_type"], "PASSIVE_TWAP")
        # Sum of tranches must equal total plan quantity
        self.assertEqual(sum(tr["quantity"] for tr in tranches), plan["quantity"])

    def test_adv_clamp_multi_stock_batch(self):
        """
        Verify that in a multi-stock batch under Z = 3.5, every single order
        is individually clamped to <= 0.0050 of its respective symbol ADV.
        """
        preds = [
            {
                "symbol": "005930",
                "name": "Samsung",
                "market": "KOSPI",
                "action": "BUY",
                "close_price": 50000.0,
                "adv": 500_000_000.0,  # 0.5% = 2,500,000 KRW
                "expected_return": 15.0,
                "ensemble_expected_return": 15.0,
                "volatility_20d": 0.02,
            },
            {
                "symbol": "000660",
                "name": "SK Hynix",
                "market": "KOSPI",
                "action": "BUY",
                "close_price": 100000.0,
                "adv": 500_000_000.0,  # 0.5% = 2,500,000 KRW
                "expected_return": 15.0,
                "ensemble_expected_return": 15.0,
                "volatility_20d": 0.025,
            },
            {
                "symbol": "AAPL",
                "name": "Apple",
                "market": "US",
                "action": "BUY",
                "close_price": 150.0,
                "adv": 200_000.0,     # USD 200,000 ADV -> 0.5% = $1,000
                "expected_return": 15.0,
                "ensemble_expected_return": 15.0,
                "volatility_20d": 0.018,
                "currency": "USD",
                "fx_rate": 1350.0,
            },
        ]
        weights = {
            "005930": 0.05,  # 5M KRW requested (breaches 2.5M cap)
            "000660": 0.05,  # 5M KRW requested (breaches 2.5M cap)
            "AAPL": 0.05,    # ~3,700 USD requested (breaches $1,000 cap)
        }

        plans = self.oms.generate_order_plan(
            top_predictions=preds,
            portfolio_weights=weights,
            total_capital=100_000_000.0,
            factor_shock_z=3.5,
            use_leland_buffer=False,
            max_adv_ratio=0.05,
        )

        self.assertEqual(len(plans), 3)
        for p in plans:
            self.assertTrue(p["throttled"])
            self.assertEqual(p["execution_strategy"], "PASSIVE_TWAP")
            sym = p["symbol"]
            matching_pred = next(x for x in preds if x["symbol"] == sym)
            adv = float(matching_pred["adv"])
            if matching_pred.get("currency") == "USD":
                # For USD, effective target is capped in USD
                usd_order_amount = p["quantity"] * p["target_price"]
                self.assertLessEqual(usd_order_amount, 0.0050 * adv + 1e-4)
            else:
                self.assertLessEqual(p["order_amount"], 0.0050 * adv + 1e-4)


class TestLelandBufferDoublingSuppression(unittest.TestCase):
    """Empirical verification of Leland Dynamic Buffer Band doubling under factor crowding shock."""

    def setUp(self):
        self.oms = ExecutionOMSEngine(db_path=":memory:")
        self.allocator = PortfolioAllocator()

    def test_leland_doubling_suppresses_marginal_buy_rebalance(self):
        """
        Verify that a marginal upward rebalancing trade (|w_curr - w_target| in (delta, 2*delta])
        passes under normal conditions (Z = 0.0) but is strictly suppressed (held) under Z = 3.5.
        """
        sym = "005930"
        mkt = "KOSPI"
        target_w = 0.15
        tot_cap = 100_000_000.0
        vol = 0.02
        price = 50000.0

        cost = self.allocator.estimate_transaction_cost_rate(
            symbol=sym, market=mkt, target_weight=target_w, portfolio_value=tot_cap, volatility_20d=vol
        )
        delta_i = self.allocator.calculate_dynamic_buffer_band(
            symbol=sym, target_weight=target_w, cost_rate=cost, volatility_20d=vol
        )
        self.assertGreater(delta_i, 0.005)

        # Current weight chosen so that |w_curr - w_target| = 1.5 * delta_i
        # Since 1.5 * delta_i > delta_i, passes normal buffer.
        # But 1.5 * delta_i <= 2.0 * delta_i, suppressed when buffer doubles.
        curr_w = target_w - 1.5 * delta_i
        curr_shares = int((tot_cap * curr_w) // price)

        pred = [{
            "symbol": sym,
            "name": "Samsung",
            "market": mkt,
            "action": "BUY",
            "close_price": price,
            "adv": 1_000_000_000.0,
            "expected_return": 15.0,  # High alpha passes alpha hurdle
            "ensemble_expected_return": 15.0,
            "volatility_20d": vol,
        }]
        weights = {sym: target_w}
        holdings = {sym: {"portfolio_weight": curr_w, "current_price": price, "shares": curr_shares}}

        # 1. Normal conditions Z = 0.0 -> trade is NOT held, plan is generated
        plans_z0 = self.oms.generate_order_plan(
            top_predictions=pred,
            portfolio_weights=weights,
            total_capital=tot_cap,
            current_holdings=holdings,
            use_leland_buffer=True,
            factor_shock_z=0.0,
        )
        self.assertEqual(len(plans_z0), 1)
        self.assertEqual(plans_z0[0]["action"], "BUY")
        self.assertGreater(plans_z0[0]["quantity"], 0)

        # 2. Shock conditions Z = 3.5 -> delta_i doubles to 2*delta_i -> trade is suppressed (held)
        plans_z35 = self.oms.generate_order_plan(
            top_predictions=pred,
            portfolio_weights=weights,
            total_capital=tot_cap,
            current_holdings=holdings,
            use_leland_buffer=True,
            factor_shock_z=3.5,
        )
        self.assertEqual(len(plans_z35), 0, "Marginal rebalance must be suppressed under Z = 3.5")

    def test_leland_doubling_suppresses_marginal_sell_rebalance(self):
        """
        Verify that a marginal downward rebalancing trade (selling part of an existing holding)
        passing under normal conditions (Z = 0.0) is suppressed (held) under Z = 3.5.
        """
        sym = "005930"
        mkt = "KOSPI"
        target_w = 0.08
        tot_cap = 100_000_000.0
        vol = 0.02
        price = 50000.0

        cost = self.allocator.estimate_transaction_cost_rate(
            symbol=sym, market=mkt, target_weight=target_w, portfolio_value=tot_cap, volatility_20d=vol
        )
        delta_i = self.allocator.calculate_dynamic_buffer_band(
            symbol=sym, target_weight=target_w, cost_rate=cost, volatility_20d=vol
        )

        # Current weight is higher than target: curr_w = target_w + 1.5 * delta_i
        curr_w = target_w + 1.5 * delta_i
        curr_shares = int((tot_cap * curr_w) // price)

        pred = [{
            "symbol": sym,
            "name": "Samsung",
            "market": mkt,
            "action": "SELL",
            "close_price": price,
            "adv": 1_000_000_000.0,
            "expected_return": 15.0,
            "ensemble_expected_return": 15.0,
            "volatility_20d": vol,
        }]
        weights = {sym: target_w}
        holdings = {sym: {"portfolio_weight": curr_w, "current_price": price, "shares": curr_shares}}

        # Z = 0.0: rebalance sell order passes
        plans_z0 = self.oms.generate_order_plan(
            top_predictions=pred,
            portfolio_weights=weights,
            total_capital=tot_cap,
            current_holdings=holdings,
            use_leland_buffer=True,
            factor_shock_z=0.0,
        )
        self.assertEqual(len(plans_z0), 1)
        self.assertEqual(plans_z0[0]["action"], "SELL")

        # Z = 3.5: rebalance sell order is suppressed
        plans_z35 = self.oms.generate_order_plan(
            top_predictions=pred,
            portfolio_weights=weights,
            total_capital=tot_cap,
            current_holdings=holdings,
            use_leland_buffer=True,
            factor_shock_z=3.5,
        )
        self.assertEqual(len(plans_z35), 0, "Marginal rebalance SELL must be suppressed under Z = 3.5")

    def test_leland_sub_buffer_deviation_suppressed_in_both(self):
        """
        Verify that deviations strictly within the baseline buffer (|w_curr - w_target| <= delta)
        are suppressed under both Z = 0.0 and Z = 3.5.
        """
        sym = "005930"
        mkt = "KOSPI"
        target_w = 0.10
        tot_cap = 100_000_000.0
        vol = 0.02
        price = 50000.0

        cost = self.allocator.estimate_transaction_cost_rate(
            symbol=sym, market=mkt, target_weight=target_w, portfolio_value=tot_cap, volatility_20d=vol
        )
        delta_i = self.allocator.calculate_dynamic_buffer_band(
            symbol=sym, target_weight=target_w, cost_rate=cost, volatility_20d=vol
        )

        curr_w = target_w + 0.5 * delta_i  # Well within baseline delta
        curr_shares = int((tot_cap * curr_w) // price)

        pred = [{
            "symbol": sym,
            "name": "Samsung",
            "market": mkt,
            "action": "BUY",
            "close_price": price,
            "adv": 1_000_000_000.0,
            "expected_return": 10.0,
            "volatility_20d": vol,
        }]
        weights = {sym: target_w}
        holdings = {sym: {"portfolio_weight": curr_w, "current_price": price, "shares": curr_shares}}

        p_z0 = self.oms.generate_order_plan(
            top_predictions=pred, portfolio_weights=weights, total_capital=tot_cap,
            current_holdings=holdings, use_leland_buffer=True, factor_shock_z=0.0
        )
        self.assertEqual(len(p_z0), 0)

        p_z35 = self.oms.generate_order_plan(
            top_predictions=pred, portfolio_weights=weights, total_capital=tot_cap,
            current_holdings=holdings, use_leland_buffer=True, factor_shock_z=3.5
        )
        self.assertEqual(len(p_z35), 0)

    def test_leland_large_rebalance_exceeding_doubled_buffer_executed(self):
        """
        Verify that a substantial rebalance (|w_curr - w_target| > 2*delta) is still
        executed even under Z = 3.5 (though throttled to PASSIVE_TWAP and <= 0.0050 ADV).
        """
        sym = "005930"
        mkt = "KOSPI"
        target_w = 0.20
        tot_cap = 100_000_000.0
        vol = 0.02
        price = 50000.0

        cost = self.allocator.estimate_transaction_cost_rate(
            symbol=sym, market=mkt, target_weight=target_w, portfolio_value=tot_cap, volatility_20d=vol
        )
        delta_i = self.allocator.calculate_dynamic_buffer_band(
            symbol=sym, target_weight=target_w, cost_rate=cost, volatility_20d=vol
        )

        # Huge deviation: 3.5 * delta_i > 2.0 * delta_i
        curr_w = target_w - 3.5 * delta_i
        curr_shares = int((tot_cap * curr_w) // price)

        pred = [{
            "symbol": sym,
            "name": "Samsung",
            "market": mkt,
            "action": "BUY",
            "close_price": price,
            "adv": 500_000_000.0,
            "expected_return": 15.0,
            "volatility_20d": vol,
        }]
        weights = {sym: target_w}
        holdings = {sym: {"portfolio_weight": curr_w, "current_price": price, "shares": curr_shares}}

        plans_z35 = self.oms.generate_order_plan(
            top_predictions=pred,
            portfolio_weights=weights,
            total_capital=tot_cap,
            current_holdings=holdings,
            use_leland_buffer=True,
            factor_shock_z=3.5,
        )
        self.assertEqual(len(plans_z35), 1, "Large rebalance exceeding 2*delta must execute")
        self.assertTrue(plans_z35[0]["throttled"])
        self.assertEqual(plans_z35[0]["execution_strategy"], "PASSIVE_TWAP")

    def test_leland_full_liquidation_and_new_entry_bypass_buffer(self):
        """
        Verify that full position liquidations and brand new position entries
        bypass the Leland buffer completely, even when Z = 3.5.
        """
        sym = "005930"
        mkt = "KOSPI"
        tot_cap = 100_000_000.0
        price = 50000.0

        # Case 1: Brand new entry (curr_w = 0.0, target_w = 0.05)
        pred_entry = [{
            "symbol": sym,
            "name": "Samsung",
            "market": mkt,
            "action": "BUY",
            "close_price": price,
            "adv": 100_000_000.0,
            "expected_return": 10.0,
            "volatility_20d": 0.02,
        }]
        holdings_empty = {sym: {"portfolio_weight": 0.0, "current_price": price, "shares": 0}}
        p_entry = self.oms.generate_order_plan(
            top_predictions=pred_entry,
            portfolio_weights={sym: 0.05},
            total_capital=tot_cap,
            current_holdings=holdings_empty,
            use_leland_buffer=True,
            factor_shock_z=3.5,
        )
        self.assertEqual(len(p_entry), 1, "New entry must bypass Leland buffer")

        # Case 2: Full liquidation (target_w = 0.0, curr_w = 0.05)
        pred_exit = [{
            "symbol": sym,
            "name": "Samsung",
            "market": mkt,
            "action": "SELL",
            "close_price": price,
            "adv": 100_000_000.0,
            "volatility_20d": 0.02,
        }]
        holdings_held = {sym: {"portfolio_weight": 0.05, "current_price": price, "shares": 100}}
        p_exit = self.oms.generate_order_plan(
            top_predictions=pred_exit,
            portfolio_weights={sym: 0.0},
            total_capital=tot_cap,
            current_holdings=holdings_held,
            use_leland_buffer=True,
            factor_shock_z=3.5,
        )
        self.assertEqual(len(p_exit), 1, "Full exit must bypass Leland buffer")
        self.assertEqual(p_exit[0]["action"], "SELL")


class TestAlmgrenChrissPassiveTWAPPrimeOddDistribution(unittest.TestCase):
    """Empirical verification of Almgren-Chriss scheduler under 'passive_twap'."""

    def test_701_shares_across_7_slices(self):
        """
        User-specified test: 701 shares across 7 slices under 'passive_twap'.
        Must produce strictly uniform allocation: sum == 701, max - min <= 1.
        Exact expectation: [101, 100, 100, 100, 100, 100, 100].
        """
        slices = AlmgrenChrissScheduler.compute_trajectory(
            total_quantity=701,
            adv=1_000_000.0,
            daily_volatility=0.02,
            strategy_tier="passive_twap",
            n_slices=7,
        )
        self.assertEqual(len(slices), 7)
        self.assertEqual(sum(slices), 701)
        self.assertLessEqual(max(slices) - min(slices), 1)
        self.assertEqual(slices, [101, 100, 100, 100, 100, 100, 100])

    def test_997_prime_shares_across_11_prime_slices(self):
        """
        Prime quantity 997 across prime slices 11:
        997 // 11 = 90, remainder 7 -> seven 91s and four 90s.
        Sum == 997, max - min <= 1.
        """
        slices = AlmgrenChrissScheduler.compute_trajectory(
            total_quantity=997,
            adv=1_000_000.0,
            daily_volatility=0.025,
            strategy_tier="passive_twap",
            n_slices=11,
        )
        self.assertEqual(len(slices), 11)
        self.assertEqual(sum(slices), 997)
        self.assertLessEqual(max(slices) - min(slices), 1)
        self.assertEqual(slices.count(91), 7)
        self.assertEqual(slices.count(90), 4)

    def test_313_prime_shares_across_5_prime_slices(self):
        """
        Prime quantity 313 across prime slices 5:
        313 // 5 = 62, remainder 3 -> three 63s and two 62s.
        """
        slices = AlmgrenChrissScheduler.compute_trajectory(
            total_quantity=313,
            adv=500_000.0,
            daily_volatility=0.03,
            strategy_tier="passive_twap",
            n_slices=5,
        )
        self.assertEqual(len(slices), 5)
        self.assertEqual(sum(slices), 313)
        self.assertLessEqual(max(slices) - min(slices), 1)
        self.assertEqual(slices.count(63), 3)
        self.assertEqual(slices.count(62), 2)

    def test_17_prime_shares_across_3_prime_slices(self):
        """
        17 shares across 3 slices:
        17 // 3 = 5, remainder 2 -> [6, 6, 5].
        """
        slices = AlmgrenChrissScheduler.compute_trajectory(
            total_quantity=17,
            adv=100_000.0,
            daily_volatility=0.02,
            strategy_tier="passive_twap",
            n_slices=3,
        )
        self.assertEqual(len(slices), 3)
        self.assertEqual(sum(slices), 17)
        self.assertLessEqual(max(slices) - min(slices), 1)
        self.assertEqual(slices, [6, 6, 5])

    def test_small_quantities_and_primes(self):
        """Test small quantities, single shares, and boundary values."""
        # 13 shares across 4 slices: 13 // 4 = 3, rem 1 -> [4, 3, 3, 3]
        s13 = AlmgrenChrissScheduler.compute_trajectory(13, 100000.0, 0.02, "passive_twap", 4)
        self.assertEqual(sum(s13), 13)
        self.assertLessEqual(max(s13) - min(s13), 1)
        self.assertEqual(s13, [4, 3, 3, 3])

        # 1 share across 5 slices: sum 1
        s1 = AlmgrenChrissScheduler.compute_trajectory(1, 100000.0, 0.02, "passive_twap", 5)
        self.assertEqual(sum(s1), 1)
        self.assertEqual(s1, [1, 0, 0, 0, 0])

        # 0 shares: [0]
        s0 = AlmgrenChrissScheduler.compute_trajectory(0, 100000.0, 0.02, "passive_twap", 6)
        self.assertEqual(s0, [0])

        # 1 slice: returns full quantity
        s_one = AlmgrenChrissScheduler.compute_trajectory(500, 100000.0, 0.02, "passive_twap", 1)
        self.assertEqual(s_one, [500])

    def test_passive_twap_no_u_curve_distortion(self):
        """
        Verify that under 'passive_twap', the U-curve volume profile is completely disabled.
        Compared to 'medium' or 'fast' (which have U-curve weighting), passive_twap has
        minimal slice variance.
        """
        qty = 600
        slices_twap = AlmgrenChrissScheduler.compute_trajectory(
            qty, 1_000_000.0, 0.02, "passive_twap", n_slices=6
        )
        slices_medium = AlmgrenChrissScheduler.compute_trajectory(
            qty, 1_000_000.0, 0.02, "medium", n_slices=6
        )

        # In passive_twap, 600 // 6 = 100 exactly for every slice
        self.assertEqual(slices_twap, [100, 100, 100, 100, 100, 100])
        var_twap = float(np.var(slices_twap))
        self.assertEqual(var_twap, 0.0)

        # In medium, U-curve concentrates shares at the start and end
        var_medium = float(np.var(slices_medium))
        self.assertGreater(var_medium, 100.0)


class TestBatchFactorRiskGatingInGenerateOrderPlan(unittest.TestCase):
    """Empirical verification of Gate 11 Idiosyncratic Risk Ratio (IRR) batch rejection."""

    def setUp(self):
        self.oms = ExecutionOMSEngine(db_path=":memory:")

    def test_irr_below_070_rejects_entire_order_batch(self):
        """
        Verify that when portfolio IRR < 0.70, generate_order_plan rejects
        the entire order batch and returns an empty plan list.
        """
        # 2-asset portfolio dominated by systematic factor exposure
        # w = [0.5, 0.5], B = [[2.0], [2.0]], Omega_F = [[0.25]], D = [0.01, 0.01]
        # beta_p = 2.0, factor_var = 4.0 * 0.25 = 1.0
        # idio_var = 0.25 * 0.01 + 0.25 * 0.01 = 0.005
        # IRR = 0.005 / 1.005 = 0.00497 << 0.70
        preds = [
            {
                "symbol": "005930",
                "name": "Samsung",
                "market": "KOSPI",
                "action": "BUY",
                "close_price": 50000.0,
                "adv": 500_000_000.0,
                "expected_return": 10.0,
                "volatility_20d": 0.02,
            },
            {
                "symbol": "000660",
                "name": "SK Hynix",
                "market": "KOSPI",
                "action": "BUY",
                "close_price": 100000.0,
                "adv": 500_000_000.0,
                "expected_return": 12.0,
                "volatility_20d": 0.025,
            },
        ]
        weights = {"005930": 0.5, "000660": 0.5}

        B_bad = np.array([[2.0], [2.0]], dtype=np.float64)
        Omega_bad = np.array([[0.25]], dtype=np.float64)
        D_bad = np.array([0.01, 0.01], dtype=np.float64)

        plans = self.oms.generate_order_plan(
            top_predictions=preds,
            portfolio_weights=weights,
            total_capital=100_000_000.0,
            B_loadings=B_bad,
            Omega_F=Omega_bad,
            D_idio=D_bad,
            min_irr=0.70,
            use_leland_buffer=False,
        )

        self.assertEqual(len(plans), 0, "Order batch with IRR < 0.70 must be completely rejected")
        self.assertIsInstance(plans, (list, OrderPlanList))

    def test_irr_boundary_06999_rejected_vs_07001_accepted(self):
        """
        Boundary verification:
        - IRR = 0.6999 is rejected (empty plans).
        - IRR = 0.7001 is accepted (order plans generated).
        """
        pred = [{
            "symbol": "005930",
            "name": "Samsung",
            "market": "KOSPI",
            "action": "BUY",
            "close_price": 50000.0,
            "adv": 500_000_000.0,
            "expected_return": 20.0,
            "ensemble_expected_return": 20.0,
            "volatility_20d": 0.02,
        }]
        weights = {"005930": 0.05}
        w = np.array([0.05], dtype=np.float64)
        B = np.array([[1.0]], dtype=np.float64)

        # 1. IRR = 0.6999: factor_var = 0.3001, idio_var = 0.6999 => rejected
        Omega_sub = np.array([[0.3001]], dtype=np.float64)
        D_sub = np.array([0.6999], dtype=np.float64)
        plans_sub = self.oms.generate_order_plan(
            top_predictions=pred,
            portfolio_weights=weights,
            total_capital=100_000_000.0,
            B_loadings=B,
            Omega_F=Omega_sub,
            D_idio=D_sub,
            min_irr=0.70,
            use_leland_buffer=False,
        )
        self.assertEqual(len(plans_sub), 0, "IRR 0.6999 must be rejected")

        # 2. IRR = 0.7001: factor_var = 0.2999, idio_var = 0.7001 => accepted
        Omega_sup = np.array([[0.2999]], dtype=np.float64)
        D_sup = np.array([0.7001], dtype=np.float64)
        plans_sup = self.oms.generate_order_plan(
            top_predictions=pred,
            portfolio_weights=weights,
            total_capital=100_000_000.0,
            B_loadings=B,
            Omega_F=Omega_sup,
            D_idio=D_sup,
            min_irr=0.70,
            use_leland_buffer=False,
        )
        self.assertEqual(len(plans_sup), 1, "IRR 0.7001 must be accepted")

    def test_irr_above_070_generates_valid_order_plan(self):
        """
        Verify that when portfolio IRR >= 0.70, generate_order_plan proceeds
        normally and generates actionable order plan entries.
        """
        pred = [{
            "symbol": "005930",
            "name": "Samsung",
            "market": "KOSPI",
            "action": "BUY",
            "close_price": 50000.0,
            "adv": 500_000_000.0,
            "expected_return": 10.0,
            "volatility_20d": 0.02,
        }]
        weights = {"005930": 0.10}

        # Idiosyncratic risk heavily dominates: factor_var = 0.01, idio_var = 0.99 => IRR = 0.99
        B_good = np.array([[0.1]], dtype=np.float64)
        Omega_good = np.array([[0.01]], dtype=np.float64)
        D_good = np.array([0.99], dtype=np.float64)

        plans = self.oms.generate_order_plan(
            top_predictions=pred,
            portfolio_weights=weights,
            total_capital=100_000_000.0,
            B_loadings=B_good,
            Omega_F=Omega_good,
            D_idio=D_good,
            min_irr=0.70,
            use_leland_buffer=False,
        )
        self.assertEqual(len(plans), 1)
        self.assertEqual(plans[0]["symbol"], "005930")
        self.assertGreater(plans[0]["quantity"], 0)

    def test_missing_factor_loadings_graceful_pass_through(self):
        """
        Verify backward compatibility: when factor loadings are omitted (None),
        generate_order_plan defaults safely and does not reject or crash.
        """
        pred = [{
            "symbol": "005930",
            "name": "Samsung",
            "market": "KOSPI",
            "action": "BUY",
            "close_price": 50000.0,
            "adv": 500_000_000.0,
            "expected_return": 10.0,
            "volatility_20d": 0.02,
        }]
        weights = {"005930": 0.10}

        plans = self.oms.generate_order_plan(
            top_predictions=pred,
            portfolio_weights=weights,
            total_capital=100_000_000.0,
            B_loadings=None,
            use_leland_buffer=False,
        )
        self.assertEqual(len(plans), 1)

    def test_degenerate_factor_matrices_numerical_resilience(self):
        """
        Verify that all-zero or rank-deficient factor matrices default safely to
        IRR = 1.0 (safe default) and do not raise NaN or ZeroDivisionError.
        """
        pred = [{
            "symbol": "005930",
            "name": "Samsung",
            "market": "KOSPI",
            "action": "BUY",
            "close_price": 50000.0,
            "adv": 500_000_000.0,
            "expected_return": 10.0,
            "volatility_20d": 0.02,
        }]
        weights = {"005930": 0.10}

        B_zero = np.zeros((1, 1), dtype=np.float64)
        Omega_zero = np.zeros((1, 1), dtype=np.float64)
        D_zero = np.zeros(1, dtype=np.float64)

        plans = self.oms.generate_order_plan(
            top_predictions=pred,
            portfolio_weights=weights,
            total_capital=100_000_000.0,
            B_loadings=B_zero,
            Omega_F=Omega_zero,
            D_idio=D_zero,
            min_irr=0.70,
            use_leland_buffer=False,
        )
        self.assertEqual(len(plans), 1, "Degenerate zero-variance matrix must fall back to safe default")


class TestCombinedOMSGate11And12Interactions(unittest.TestCase):
    """Empirical verification of simultaneous Gate 11 and Gate 12 interactions."""

    def setUp(self):
        self.oms = ExecutionOMSEngine(db_path=":memory:")

    def test_gate11_breach_preempts_gate12_throttled_generation(self):
        """
        When both IRR < 0.70 and Z = 3.5 occur simultaneously:
        Gate 11 breach must reject the batch before any throttled orders can be generated.
        """
        pred = [{
            "symbol": "005930",
            "name": "Samsung",
            "market": "KOSPI",
            "action": "BUY",
            "close_price": 50000.0,
            "adv": 500_000_000.0,
            "expected_return": 10.0,
            "volatility_20d": 0.02,
        }]
        weights = {"005930": 0.10}

        # Systematic factor risk dominates -> IRR = 0.01 < 0.70
        B_bad = np.array([[2.0]])
        Omega_bad = np.array([[0.20]])
        D_bad = np.array([0.01])

        plans = self.oms.generate_order_plan(
            top_predictions=pred,
            portfolio_weights=weights,
            total_capital=100_000_000.0,
            factor_shock_z=3.5,
            B_loadings=B_bad,
            Omega_F=Omega_bad,
            D_idio=D_bad,
            min_irr=0.70,
            use_leland_buffer=False,
        )
        self.assertEqual(len(plans), 0)

    def test_gate11_pass_and_gate12_throttled_execution(self):
        """
        When IRR >= 0.70 and Z = 3.5:
        Gate 11 passes, allowing orders, but Gate 12 strictly throttles them:
        - ADV participation <= 0.0050.
        - Execution strategy is PASSIVE_TWAP.
        - Leland buffer band doubled.
        """
        adv_val = 100_000_000.0
        tot_cap = 100_000_000.0
        pred = [{
            "symbol": "005930",
            "name": "Samsung",
            "market": "KOSPI",
            "action": "BUY",
            "close_price": 50000.0,
            "adv": adv_val,
            "expected_return": 10.0,
            "volatility_20d": 0.02,
        }]
        weights = {"005930": 0.05}  # 5,000,000 KRW requested

        # Idiosyncratic risk dominates -> IRR = 0.99 >= 0.70
        B_good = np.array([[0.1]])
        Omega_good = np.array([[0.01]])
        D_good = np.array([0.99])

        plans = self.oms.generate_order_plan(
            top_predictions=pred,
            portfolio_weights=weights,
            total_capital=tot_cap,
            factor_shock_z=3.5,
            B_loadings=B_good,
            Omega_F=Omega_good,
            D_idio=D_good,
            min_irr=0.70,
            use_leland_buffer=False,
        )
        self.assertEqual(len(plans), 1)
        plan = plans[0]
        self.assertTrue(plan["throttled"])
        self.assertEqual(plan["execution_strategy"], "PASSIVE_TWAP")
        self.assertLessEqual(plan["order_amount"] / adv_val, 0.00500001)

    def test_synthetic_rows_invariant_native_int(self):
        """
        System Invariant R5:
        synthetic_rows == 0 must be strictly verified as native Python int
        (is_int=True, not_bool=True) across all gate outputs and payloads.
        """
        is_th, p12 = check_gate12_factor_crowding_shock(3.5, max_shock_z=3.0)
        self.assertIn("synthetic_rows", p12)
        sr = p12["synthetic_rows"]
        self.assertIsInstance(sr, int)
        self.assertNotIsInstance(sr, bool)
        self.assertEqual(sr, 0)

        # Batch evaluation
        b_res = self.oms.evaluate_batch_factor_risk_gates(
            portfolio_weights={"005930": 0.5},
            factor_shock_z=3.5,
        )
        self.assertIn("synthetic_rows", b_res)
        self.assertIsInstance(b_res["synthetic_rows"], int)
        self.assertNotIsInstance(b_res["synthetic_rows"], bool)
        self.assertEqual(b_res["synthetic_rows"], 0)


if __name__ == "__main__":
    unittest.main()
