"""
Adversarial Retest Stress Harness: OMS Engine Defect Fixes Verification
========================================================================
Validates:
1. Defect 1: slice_count initialization, isolation across iterations, and all preassigned strategies (PASSIVE_LIMIT, DIP_LIMIT, CASH_OVERLAY).
2. Defect 2: _is_invalid_or_nonpositive_price behavior against exhaustive malformed, non-numeric, overflow, and type-mismatched inputs under BUY and SELL.
3. DB fallback retrieval for invalid price SELL orders.
"""

import math
import unittest
import sqlite3
import numpy as np

from trading_system.src.execution.oms_engine import (
    ExecutionOMSEngine,
    _is_invalid_or_nonpositive_price
)


class TestAdversarialRetestOMSVerification(unittest.TestCase):
    def setUp(self):
        self.oms = ExecutionOMSEngine(db_path=":memory:", version=102)

    # -------------------------------------------------------------------------
    # DEFECT 1: slice_count & Strategy Isolation Stress Tests
    # -------------------------------------------------------------------------

    def test_lower_limit_liquidation_various_quantities(self):
        """Test Gate 7.2 lower limit liquidation across tiny, large, and odd quantities."""
        test_cases = [
            (1, 1),       # 1 share, lot 1
            (10, 1),      # 10 shares, lot 1
            (50, 100),    # Sub-lot quantity
            (1000, 10),   # Multiple lots
            (555, 7),     # Odd lots
        ]
        for qty, lot in test_cases:
            pred = [{
                "symbol": "005930",
                "market": "KOSPI",
                "action": "SELL",
                "target_price": 60000.0,
                "change_pct": -30.0,
                "lot_size": lot,
            }]
            holdings = {"005930": {"quantity": qty, "current_price": 60000.0, "portfolio_weight": 0.10}}
            plans = self.oms.generate_order_plan(
                top_predictions=pred,
                portfolio_weights={"005930": 0.0},
                total_capital=100_000_000.0,
                current_holdings=holdings,
                lot_size_krx=lot
            )
            self.assertEqual(len(plans), 1, f"Failed for qty={qty}, lot={lot}")
            p = plans[0]
            self.assertEqual(p["exec_strategy"], "PASSIVE_LIMIT")
            self.assertIsInstance(p["slice_count"], int)
            self.assertGreaterEqual(p["slice_count"], 1)
            self.assertEqual(p["action"], "SELL")

    def test_iteration_isolation_no_strategy_leakage(self):
        """
        Verify that iteration 1 setting exec_strategy='PASSIVE_LIMIT' does NOT leak
        into iteration 2, which should evaluate its own strategy independently.
        """
        preds = [
            # Item 1: Lower limit lock SELL -> PASSIVE_LIMIT
            {
                "symbol": "005930",
                "market": "KOSPI",
                "action": "SELL",
                "target_price": 60000.0,
                "change_pct": -30.0,
            },
            # Item 2: Normal BUY with high half-life -> MIDPOINT_PEG
            {
                "symbol": "000660",
                "market": "KOSPI",
                "action": "BUY",
                "target_price": 150000.0,
                "expected_return": 0.08,
                "rim_valuation": 1.0,  # Half-life = 60.0 -> MIDPOINT_PEG (slice_count = 8)
                "adv": 500_000_000_000.0,
            },
            # Item 3: Normal BUY with fast alpha -> FAST_VWAP
            {
                "symbol": "035420",
                "market": "KOSPI",
                "action": "BUY",
                "target_price": 200000.0,
                "expected_return": 0.05,
                "overnight_gap_reversal": 1.0,  # Half-life = 1.0 -> FAST_VWAP (slice_count = 3)
                "adv": 500_000_000_000.0,
            }
        ]
        holdings = {"005930": {"quantity": 100, "current_price": 60000.0, "portfolio_weight": 0.10}}
        weights = {"005930": 0.0, "000660": 0.10, "035420": 0.10}

        plans = self.oms.generate_order_plan(
            top_predictions=preds,
            portfolio_weights=weights,
            total_capital=100_000_000.0,
            current_holdings=holdings
        )

        plan_map = {p["symbol"]: p for p in plans}
        self.assertIn("005930", plan_map)
        self.assertIn("000660", plan_map)
        self.assertIn("035420", plan_map)

        # Item 1 must be PASSIVE_LIMIT
        self.assertEqual(plan_map["005930"]["exec_strategy"], "PASSIVE_LIMIT")

        # Item 2 MUST NOT be contaminated by PASSIVE_LIMIT; must be MIDPOINT_PEG
        self.assertEqual(plan_map["000660"]["exec_strategy"], "MIDPOINT_PEG")
        self.assertGreaterEqual(plan_map["000660"]["slice_count"], 1)

        # Item 3 MUST NOT be contaminated by MIDPOINT_PEG or PASSIVE_LIMIT; must be FAST_VWAP
        self.assertEqual(plan_map["035420"]["exec_strategy"], "FAST_VWAP")
        self.assertGreaterEqual(plan_map["035420"]["slice_count"], 1)

    def test_all_preassigned_execution_strategies(self):
        """Stress-test all preassigned strategies: DIP_LIMIT, PASSIVE_LIMIT, CASH_OVERLAY."""
        # 1. DIP_LIMIT via Gate 7.7 opening gap >= 5% (via change_pct)
        pred_gap = [{
            "symbol": "005930",
            "market": "KOSPI",
            "action": "BUY",
            "target_price": 70000.0,
            "change_pct": 6.5,
            "expected_return": 0.06,
            "adv": 500_000_000_000.0,
        }]
        plans_dip = self.oms.generate_order_plan(
            top_predictions=pred_gap,
            portfolio_weights={"005930": 0.10},
            total_capital=100_000_000.0
        )
        self.assertEqual(len(plans_dip), 1)
        self.assertEqual(plans_dip[0]["exec_strategy"], "DIP_LIMIT")
        self.assertGreaterEqual(plans_dip[0]["slice_count"], 1)

        # 2. PASSIVE_LIMIT via Gate 7.6 VPIN toxicity > 0.70 on BUY
        pred_toxic = [{
            "symbol": "005930",
            "market": "KOSPI",
            "action": "BUY",
            "target_price": 70000.0,
            "vpin": 0.85,
            "expected_return": 0.06,
            "adv": 500_000_000_000.0,
        }]
        plans_passive = self.oms.generate_order_plan(
            top_predictions=pred_toxic,
            portfolio_weights={"005930": 0.10},
            total_capital=100_000_000.0
        )
        self.assertEqual(len(plans_passive), 1)
        self.assertEqual(plans_passive[0]["exec_strategy"], "PASSIVE_LIMIT")
        self.assertGreaterEqual(plans_passive[0]["slice_count"], 1)

        # 3. CASH_OVERLAY via Gate 7.1 SHORT on KRX
        pred_short = [{
            "symbol": "005930",
            "market": "KOSPI",
            "action": "SHORT",
            "target_price": 70000.0,
            "adv": 500_000_000_000.0,
        }]
        plans_short = self.oms.generate_order_plan(
            top_predictions=pred_short,
            portfolio_weights={"005930": 0.10},
            total_capital=100_000_000.0
        )
        self.assertEqual(len(plans_short), 1)
        self.assertEqual(plans_short[0]["exec_strategy"], "CASH_OVERLAY")
        self.assertGreaterEqual(plans_short[0]["slice_count"], 1)

    # -------------------------------------------------------------------------
    # DEFECT 2: Price Validation & Edge Case Stress Tests
    # -------------------------------------------------------------------------

    def test_is_invalid_or_nonpositive_price_exhaustive_inputs(self):
        """Test _is_invalid_or_nonpositive_price against all categories of input."""
        invalid_inputs = [
            None, "", "   ", "\t\r\n",
            "INVALID_PRICE", "N/A", "NaN", "nan", "NAN",
            "inf", "-inf", "Infinity", "-Infinity",
            0, 0.0, "0", "0.0", "-0.0",
            -1, -100.5, "-50", "-0.0001",
            float("nan"), float("inf"), float("-inf"),
            [], {}, set(), (1, 2), object(),
            "$$$100", "price_not_found", "ERR_NULL",
        ]
        for val in invalid_inputs:
            self.assertTrue(
                _is_invalid_or_nonpositive_price(val),
                f"Expected True (invalid) for {val!r} of type {type(val)}"
            )

        valid_inputs = [
            1, 1.0, "1", "1.0",
            50000, 50000.0, "50000", "50000.0", "5e4",
            0.001, "0.001", 1e8, "100000000"
        ]
        for val in valid_inputs:
            self.assertFalse(
                _is_invalid_or_nonpositive_price(val),
                f"Expected False (valid) for {val!r} of type {type(val)}"
            )

    def test_non_numeric_prices_in_batch_plan_generation(self):
        """Verify that malformed price strings in a batch do not crash valid predictions."""
        preds = [
            # Corrupted price items
            {"symbol": "SYM_ERR1", "market": "KOSPI", "action": "BUY", "close_price": "BAD_PRICE", "target_price": "BAD_PRICE"},
            {"symbol": "SYM_ERR2", "market": "KOSPI", "action": "SELL", "close_price": "N/A", "target_price": "N/A"},
            {"symbol": "SYM_ERR3", "market": "KOSPI", "action": "BUY", "close_price": "", "target_price": ""},
            {"symbol": "SYM_ERR4", "market": "KOSPI", "action": "SELL", "close_price": None, "target_price": None},
            {"symbol": "SYM_ERR5", "market": "KOSPI", "action": "BUY", "close_price": "nan", "target_price": "nan"},
            {"symbol": "SYM_ERR6", "market": "KOSPI", "action": "SELL", "close_price": "inf", "target_price": "inf"},
            # Valid item in same batch
            {"symbol": "005930", "market": "KOSPI", "action": "BUY", "close_price": 50000.0, "target_price": 50000.0, "expected_return": 0.05, "adv": 1e11},
        ]
        weights = {p["symbol"]: 0.10 for p in preds}

        plans = self.oms.generate_order_plan(
            top_predictions=preds,
            portfolio_weights=weights,
            total_capital=100_000_000.0
        )
        # Exactly 1 valid order should be generated (005930), all corrupted items skipped
        self.assertEqual(len(plans), 1)
        self.assertEqual(plans[0]["symbol"], "005930")

    def test_sell_order_db_price_recovery_when_input_price_invalid(self):
        """
        Verify that when a SELL order has an invalid close_price, OMS successfully
        queries historical order_plans table in DB to recover a valid price.
        """
        # Step 1: Pre-populate DB with a prior buy order for 005930 at price 55000.0
        conn = self.oms._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO order_plans (order_id, symbol, name, market, action, target_weight, target_amount, target_price, quantity, execution_strategy, status, created_at)
            VALUES ('ORD_PREV_1', '005930', 'Samsung', 'KOSPI', 'BUY', 0.10, 5500000.0, 55000.0, 100, 'DIRECT', 'PENDING', '2026-10-09 09:00:00')
        """)
        conn.commit()

        # Step 2: Now issue a SELL order for 005930 with corrupted/missing price
        pred_sell_corrupted = [{
            "symbol": "005930",
            "market": "KOSPI",
            "action": "SELL",
            "close_price": "UNKNOWN_PRICE",
            "target_price": "",
        }]
        holdings = {"005930": {"quantity": 100, "current_price": 0.0, "portfolio_weight": 0.10}}

        plans = self.oms.generate_order_plan(
            top_predictions=pred_sell_corrupted,
            portfolio_weights={"005930": 0.0},
            total_capital=100_000_000.0,
            current_holdings=holdings
        )

        self.assertEqual(len(plans), 1)
        self.assertEqual(plans[0]["symbol"], "005930")
        self.assertEqual(plans[0]["target_price"], 55000.0)
        self.assertEqual(plans[0]["action"], "SELL")


if __name__ == "__main__":
    unittest.main()
