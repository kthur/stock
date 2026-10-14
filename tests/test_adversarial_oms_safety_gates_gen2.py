"""
Adversarial Empirical Stress Testing Suite for R3:
Execution OMS Safety Gates, ATR/Kelly Sizing, and Edge Cases
=============================================================
Stress-tests:
1. Identified Vulnerabilities Reproduction:
   - Bug 1 (CRITICAL): UnboundLocalError for 'slice_count' on lower limit lock (-30%) liquidation
   - Bug 2 (HIGH): Unhandled ValueError on non-numeric price string in Gate price parsing
2. 8 Safety Gates under extreme conditions:
   - Bogus, corrupted, SQL-injection, and dict-string symbols
   - Zero, negative, sub-penny, astronomical, NaN, and Inf prices
   - Huge, microscopic, negative, zero, and NaN portfolio capital and quantities
   - Toxic order books: VPIN > 0.99, wide bid-ask spread, adverse gap, limit-lock
   - Gate 8 extreme FX rates (0, negative, NaN, Inf) and missing/corrupted hedge prices
3. Dynamic stop loss and take profit calculations with degenerate volatility & alpha:
   - NaN, Inf, zero, and negative volatility_20d
   - NaN, Inf, negative, and astronomical expected returns
   - Multi-tier trailing stop plans under corrupted/sparse OHLCV data
4. Kelly criterion and Fractional Kelly boundary conditions:
   - win_rate in [-0.5, 0.0, 1.0, 2.0, NaN, Inf]
   - win_loss_ratio in [-1.0, 0.0, 1e-6, 1e8, NaN, Inf]
   - Robust Kelly under severe consecutive losses (5, 8, 10, 15)
   - calculate_position_sizing with NaN/invalid stop loss, extreme VIX, and SEVERE crisis blocking
5. Concurrency and Thread Safety:
   - Multi-threaded rapid order plan generation under fluctuating CrisisLevels and shared SQLite DB
"""

import math
import os
import unittest
import threading
import sqlite3
import numpy as np
import pandas as pd

from trading_system.src.execution.oms_engine import ExecutionOMSEngine
from trading_system.src.risk.risk_manager import RiskManager, CrisisDetector, CrisisLevel


class TestAdversarialVulnerabilitiesReproduction(unittest.TestCase):
    """Reproduces the critical failure modes identified during adversarial stress testing."""

    def setUp(self):
        self.oms = ExecutionOMSEngine(db_path=":memory:", version=102)

    def test_reproduce_bug1_unbound_local_slice_count_on_lower_limit_lock(self):
        """
        VULNERABILITY 1 (CRITICAL):
        In Gate 7.2 (oms_engine.py:657), when a held KRX stock locks at lower limit (-30%),
        it sets exec_strategy = 'PASSIVE_LIMIT'. Because is_preassigned_strategy becomes True,
        lines 862-876 are bypassed and slice_count is never assigned.
        Line 881 then raises UnboundLocalError: cannot access local variable 'slice_count'.
        """
        pred_lower_sell = [{
            "symbol": "005930",
            "market": "KOSPI",
            "action": "SELL",
            "target_price": 50000.0,
            "change_pct": -29.8,
        }]
        holdings = {"005930": {"quantity": 200, "current_price": 50000.0, "portfolio_weight": 0.10}}

        # Remediated: PASSIVE_LIMIT plan is generated cleanly without UnboundLocalError
        plans = self.oms.generate_order_plan(
            pred_lower_sell,
            {"005930": 0.0},
            total_capital=100000000.0,
            current_holdings=holdings
        )
        self.assertEqual(len(plans), 1)
        self.assertEqual(plans[0]["exec_strategy"], "PASSIVE_LIMIT")
        self.assertGreaterEqual(plans[0]["slice_count"], 1)

    def test_reproduce_bug2_unhandled_value_error_on_non_numeric_price_string(self):
        """
        VULNERABILITY 2 (HIGH):
        In oms_engine.py:597:
        'if (close_price is None or close_price == "" or float(close_price or 0.0) <= 0.0) and raw_action == "SELL":'
        Python evaluates float(close_price or 0.0) without a try-except.
        If close_price is any non-numeric string (e.g. 'INVALID_PRICE', 'N/A', 'UNKNOWN'),
        it immediately raises an unhandled ValueError.
        """
        pred_corrupted_price = [{
            "symbol": "005930",
            "market": "KOSPI",
            "action": "BUY",
            "close_price": "INVALID_PRICE",
            "target_price": "INVALID_PRICE",
            "expected_return": 0.05
        }]

        # Remediated: Non-numeric price strings are safely rejected without throwing unhandled ValueError
        plans = self.oms.generate_order_plan(
            pred_corrupted_price,
            {"005930": 0.10},
            total_capital=100000000.0
        )
        self.assertEqual(len(plans), 0)


class TestAdversarialOMSSafetyGates(unittest.TestCase):
    """Domain 1: 8 Safety Gates Under Adversarial & Malformed Inputs."""

    def setUp(self):
        self.oms = ExecutionOMSEngine(db_path=":memory:", version=102)

    def test_gate_symbol_validation_adversarial(self):
        """Bogus, corrupted, SQL-injection, and dict-string symbols must be safely dropped."""
        adversarial_symbols = [
            None,
            "",
            "   ",
            "{'symbol': '005930'}",
            '{"symbol": "AAPL"}',
            "005930; DROP TABLE order_plans; --",
            "AAPL' OR '1'='1",
            "KRX:005930",
            "AAPL US",
            "005930{KS}",
            "VERYLONGSYMBOLNAMEEXCEEDINGTWENTYCHARACTERS",
            12345,
            ["AAPL"],
            {"sym": "MSFT"},
            "\t\n\r",
            "$$$INVALID$$$",
        ]

        for bogus_sym in adversarial_symbols:
            valid_sym = self.oms._validate_symbol(bogus_sym)
            self.assertEqual(valid_sym, "", msg=f"Symbol '{bogus_sym}' was not rejected by _validate_symbol")

        # Test that generate_order_plan rejects all bogus symbols without throwing exceptions
        predictions = [
            {"symbol": bogus_sym, "market": "KOSPI", "target_price": 50000.0, "expected_return": 0.05}
            for bogus_sym in adversarial_symbols
        ]
        weights = {str(bogus_sym): 0.10 for bogus_sym in adversarial_symbols}

        orders = self.oms.generate_order_plan(
            top_predictions=predictions,
            portfolio_weights=weights,
            total_capital=100000000.0,
            crisis_level="NORMAL",
        )
        self.assertEqual(len(orders), 0, "Expected 0 orders generated for bogus symbols")

    def test_gate_price_boundaries_and_numeric_nan_inf(self):
        """Zero, negative, sub-penny, astronomical, NaN, and Inf numeric prices must be rejected."""
        extreme_prices = [
            0.0,
            -100.0,
            -0.0001,
            float("nan"),
            float("inf"),
            float("-inf"),
            0.5,          # Below _MIN_PRICE_BOUND = 1.0
            0.00001,
            100_000_001.0,  # Above _MAX_PRICE_BOUND = 100_000_000.0
            None,
        ]

        predictions = []
        weights = {}
        for i, px in enumerate(extreme_prices):
            sym = f"TEST{i}"
            predictions.append({
                "symbol": sym,
                "market": "KOSPI",
                "close_price": px,
                "target_price": px,
                "expected_return": 0.05
            })
            weights[sym] = 0.05

        orders = self.oms.generate_order_plan(
            top_predictions=predictions,
            portfolio_weights=weights,
            total_capital=100000000.0,
            crisis_level="NORMAL",
        )
        self.assertEqual(len(orders), 0, f"Expected 0 orders for extreme prices, got {len(orders)}")

    def test_gate_capital_and_quantity_anomalies(self):
        """Degenerate capital, negative weights, zero delta, and extreme capital values."""
        # 1. Zero and negative total_capital
        preds = [{"symbol": "005930", "market": "KOSPI", "target_price": 70000.0, "expected_return": 0.05}]
        weights = {"005930": 0.20}

        orders_zero_cap = self.oms.generate_order_plan(preds, weights, total_capital=0.0)
        self.assertEqual(len(orders_zero_cap), 0)

        orders_neg_cap = self.oms.generate_order_plan(preds, weights, total_capital=-100000000.0)
        self.assertEqual(len(orders_neg_cap), 0)

        # 2. NaN capital
        orders_nan_cap = self.oms.generate_order_plan(preds, weights, total_capital=float("nan"))
        self.assertTrue(isinstance(orders_nan_cap, list))

        # 3. Negative and NaN weights
        orders_neg_weight = self.oms.generate_order_plan(preds, {"005930": -0.20}, total_capital=100000000.0)
        self.assertEqual(len(orders_neg_weight), 0)

        orders_nan_weight = self.oms.generate_order_plan(preds, {"005930": float("nan")}, total_capital=100000000.0)
        self.assertEqual(len(orders_nan_weight), 0)

        # 4. Large capital on US stock (not blocked by KRX STT Gate 7.3 hurdle)
        preds_us = [{"symbol": "AAPL", "market": "SP500", "target_price": 200.0, "ensemble_expected_return": 0.05}]
        orders_us = self.oms.generate_order_plan(preds_us, {"AAPL": 0.20}, total_capital=1e10, usdkrw_rate=1350.0)
        self.assertEqual(len(orders_us), 1)
        self.assertGreater(orders_us[0]["quantity"], 0)
        self.assertTrue(math.isfinite(orders_us[0]["order_amount"]))

        # 5. Delta rebalance HOLD when target == current holdings
        holdings = {"005930": {"quantity": 285, "current_price": 70000.0, "portfolio_weight": 0.20}}
        orders_hold = self.oms.generate_order_plan(
            preds, {"005930": 0.20}, total_capital=100000000.0, current_holdings=holdings
        )
        self.assertEqual(len(orders_hold), 0, "Zero delta rebalance should yield 0 orders (HOLD)")

    def test_gate_7_6_and_7_7_microstructure_toxicity_and_gap_overheat(self):
        """VPIN toxicity, wide spread, and opening gap overheat adaptive routing."""
        # A. High VPIN on BUY -> PASSIVE_LIMIT
        pred_toxic_buy = [{
            "symbol": "005930",
            "market": "KOSPI",
            "target_price": 70000.0,
            "expected_return": 0.05,
            "vpin": 0.95,  # Above 0.70 threshold
        }]
        orders_vpin_buy = self.oms.generate_order_plan(
            pred_toxic_buy, {"005930": 0.20}, total_capital=100000000.0
        )
        self.assertEqual(len(orders_vpin_buy), 1)
        self.assertEqual(orders_vpin_buy[0]["execution_strategy"], "PASSIVE_LIMIT")
        self.assertGreaterEqual(orders_vpin_buy[0]["slice_count"], 6)

        # B. High VPIN on SELL -> FAST_VWAP
        pred_toxic_sell = [{
            "symbol": "005930",
            "market": "KOSPI",
            "action": "SELL",
            "target_price": 70000.0,
            "vpin": 0.95,
        }]
        orders_vpin_sell = self.oms.generate_order_plan(
            pred_toxic_sell, {"005930": 0.0}, total_capital=100000000.0,
            current_holdings={"005930": {"quantity": 500, "current_price": 70000.0, "portfolio_weight": 0.20}}
        )
        self.assertEqual(len(orders_vpin_sell), 1)
        self.assertEqual(orders_vpin_sell[0]["execution_strategy"], "FAST_VWAP")

        # C. Opening Gap Overheat (> 5%) on BUY -> DIP_LIMIT with discounted target price
        pred_gap = [{
            "symbol": "005930",
            "market": "KOSPI",
            "target_price": 70000.0,
            "expected_return": 0.06,
            "change_pct": 8.0,  # +8% opening gap
        }]
        orders_gap = self.oms.generate_order_plan(
            pred_gap, {"005930": 0.20}, total_capital=100000000.0
        )
        self.assertEqual(len(orders_gap), 1)
        self.assertEqual(orders_gap[0]["execution_strategy"], "DIP_LIMIT")
        # Target price should be strictly discounted below nominal 70000.0
        self.assertLess(orders_gap[0]["target_price"], 70000.0)

    def test_gate_7_2_krx_price_upper_limit_lock(self):
        """KRX upper (+30%) limit lock execution safety blocks new buys."""
        pred_upper = [{
            "symbol": "005930",
            "market": "KOSPI",
            "target_price": 70000.0,
            "expected_return": 0.10,
            "change_pct": 29.8,  # Near +30% limit
        }]
        orders_upper = self.oms.generate_order_plan(
            pred_upper, {"005930": 0.20}, total_capital=100000000.0
        )
        self.assertEqual(len(orders_upper), 0, "Upper limit locked stock must skip BUY")

    def test_gate_8_extreme_fx_and_inverse_hedges(self):
        """Gate 8 synthetic inverse hedge with extreme/degenerate FX rates and missing prices."""
        fx_rates = [0.0, -1350.0, float("nan"), float("inf"), 1e8, 1e-4]
        preds = [
            {"symbol": "AAPL", "market": "SP500", "target_price": 220.0, "ensemble_expected_return": 0.05},
            {"symbol": "MSFT", "market": "SP500", "target_price": 400.0, "ensemble_expected_return": 0.04}
        ]
        weights = {"AAPL": 0.40, "MSFT": 0.30}

        for fx in fx_rates:
            orders = self.oms.generate_order_plan(
                top_predictions=preds,
                portfolio_weights=weights,
                total_capital=135000000.0,
                regime_label="CRISIS",
                usdkrw_rate=fx,
            )
            self.assertTrue(isinstance(orders, list))
            hedge_orders = [o for o in orders if "HEDGE" in str(o.get("order_id", "")) or o.get("action") == "BUY_HEDGE"]
            if hedge_orders:
                h = hedge_orders[0]
                self.assertGreater(h["quantity"], 0)
                self.assertTrue(math.isfinite(h["quantity"]))
                self.assertTrue(math.isfinite(h["target_price"]))
                self.assertGreater(h["target_price"], 0.0)
                self.assertLessEqual(h["target_weight"], 0.50)


class TestAdversarialDynamicStopLossTakeProfit(unittest.TestCase):
    """Domain 2: Dynamic Stop-Loss, Take-Profit, and Trailing Stops with Degenerate Inputs."""

    def setUp(self):
        self.oms = ExecutionOMSEngine(db_path=":memory:", version=102)

    def test_dynamic_sl_tp_with_degenerate_volatility_and_return(self):
        """dynamic_sl_pct and dynamic_tp_pct must be strictly clamped with NaN/Inf/negative inputs."""
        degenerate_cases = [
            {"volatility_20d": float("nan"), "expected_return": 0.05},
            {"volatility_20d": float("inf"), "expected_return": 0.05},
            {"volatility_20d": float("-inf"), "expected_return": 0.05},
            {"volatility_20d": -0.05, "expected_return": 0.05},
            {"volatility_20d": 0.0, "expected_return": 0.05},
            {"volatility_20d": 100.0, "expected_return": 0.05},
            {"volatility_20d": 0.02, "expected_return": float("nan")},
            {"volatility_20d": 0.02, "expected_return": float("inf")},
            {"volatility_20d": 0.02, "expected_return": float("-inf")},
            {"volatility_20d": 0.02, "expected_return": -1.0},
            {"volatility_20d": 0.02, "expected_return": 500.0},
            {"volatility_20d": float("nan"), "expected_return": float("nan")},
        ]

        for i, case in enumerate(degenerate_cases):
            sym = f"DEG{i}"
            pred = [{
                "symbol": sym,
                "market": "KOSPI",
                "target_price": 50000.0,
                "volatility_20d": case["volatility_20d"],
                "expected_return": case["expected_return"],
            }]
            orders = self.oms.generate_order_plan(
                pred, {sym: 0.20}, total_capital=100000000.0, crisis_level="NORMAL"
            )
            if orders:
                o = orders[0]
                tp = o["target_take_profit"]
                sl = o["target_stop_loss"]
                self.assertIsNotNone(tp)
                self.assertIsNotNone(sl)
                self.assertTrue(math.isfinite(tp), f"TP is not finite for case {case}: {tp}")
                self.assertTrue(math.isfinite(sl), f"SL is not finite for case {case}: {sl}")
                self.assertGreater(tp, o["target_price"], f"TP must exceed target price for {sym}")
                self.assertLess(sl, o["target_price"], f"SL must be below target price for {sym}")
                self.assertGreater(sl, 0.0, f"SL must be strictly positive for {sym}")

    def test_trailing_stop_plan_with_sparse_corrupted_prices(self):
        """calculate_trailing_stop_plan under empty, NaN, and sparse DataFrames."""
        holdings = {
            "005930": {
                "quantity": 100,
                "entry_price": 70000.0,
                "current_price": 72000.0,
                "days_held": 5,
                "current_score": 0.65,
                "volatility_20d": float("nan"),
            },
            "000660": {
                "quantity": 50,
                "entry_price": 120000.0,
                "current_price": 110000.0,
                "days_held": 15,
                "current_score": 0.40,
                "volatility_20d": -0.05,
            }
        }

        # Sparse prices dictionary with corrupted / NaN columns
        corrupted_df = pd.DataFrame({
            "High": [float("nan")] * 20,
            "Low": [float("nan")] * 20,
            "Close": [72000.0] * 20,
            "Volume": [0] * 20
        })
        prices_dict = {"005930": corrupted_df, "000660": pd.DataFrame()}

        plans = self.oms.calculate_trailing_stop_plan(
            current_holdings=holdings,
            prices_dict=prices_dict,
            regime="SIDEWAYS_LOW_VOL"
        )
        self.assertTrue(isinstance(plans, list))
        self.assertTrue(len(plans) >= 1)
        for p in plans:
            self.assertTrue(math.isfinite(p["current_price"]))
            self.assertGreater(p["quantity"], 0)


class TestAdversarialKellyAndPositionSizing(unittest.TestCase):
    """Domain 3: Kelly Criterion and Position Sizing Boundary Conditions."""

    def setUp(self):
        self.rm = RiskManager(portfolio_value=100000000.0, max_position_size_pct=0.25)

    def test_calculate_kelly_fraction_boundary_conditions(self):
        """calculate_kelly_fraction must strictly bound within [0.0, max_position_size_pct]."""
        extreme_inputs = [
            # (win_rate, win_loss_ratio)
            (0.0, 1.5),
            (1.0, 1.5),
            (-0.5, 2.0),
            (2.0, 2.0),
            (float("nan"), 1.5),
            (0.55, float("nan")),
            (float("inf"), 1.5),
            (0.55, float("inf")),
            (0.55, 0.0),
            (0.55, -1.0),
            (0.50, 1.0),    # 50% win rate, 1:1 reward:risk -> Kelly = 0
            (0.40, 1.0),    # 40% win rate, 1:1 reward:risk -> negative edge -> 0
            (0.60, 2.0),    # Positive edge: 0.6 - (0.4 / 2) = 0.40 -> Half Kelly = 0.20 -> clipped to 0.20
            (0.99, 10.0),   # Extreme edge: must clip to max_position_size_pct = 0.25
        ]

        for wr, r in extreme_inputs:
            kf = self.rm.calculate_kelly_fraction(win_rate=wr, win_loss_ratio=r)
            self.assertTrue(math.isfinite(kf), f"Kelly fraction is not finite for ({wr}, {r}): {kf}")
            self.assertGreaterEqual(kf, 0.0, f"Kelly fraction is negative for ({wr}, {r}): {kf}")
            self.assertLessEqual(kf, self.rm.max_position_size_pct, f"Kelly exceeds max cap for ({wr}, {r}): {kf}")

    def test_calculate_robust_kelly_consecutive_losses(self):
        """calculate_robust_kelly must enforce progressive penalties and shut off on severe streaks."""
        wr, r, n_trades = 0.60, 2.0, 50

        # Baseline
        k_base = self.rm.calculate_robust_kelly(wr, r, n_trades, consecutive_losses=0)
        self.assertGreater(k_base, 0.0)

        # 5 consecutive losses -> 30% penalty
        k_5 = self.rm.calculate_robust_kelly(wr, r, n_trades, consecutive_losses=5)
        self.assertLess(k_5, k_base)

        # 8 consecutive losses -> 50% penalty
        k_8 = self.rm.calculate_robust_kelly(wr, r, n_trades, consecutive_losses=8)
        self.assertLess(k_8, k_5)

        # 10 or 15 consecutive losses -> 0.0 (trading halted)
        k_10 = self.rm.calculate_robust_kelly(wr, r, n_trades, consecutive_losses=10)
        self.assertEqual(k_10, 0.0)

        k_15 = self.rm.calculate_robust_kelly(wr, r, n_trades, consecutive_losses=15)
        self.assertEqual(k_15, 0.0)

    def test_calculate_position_sizing_severe_crisis_and_nan_stops(self):
        """calculate_position_sizing under SEVERE crisis, NaN stops, and invalid parameters."""
        # 1. Normal sizing
        qty_normal = self.rm.calculate_position_sizing(
            symbol="005930",
            entry_price=70000.0,
            stop_loss_price=66500.0,
            win_rate=0.55,
            win_loss_ratio=1.5
        )
        self.assertGreater(qty_normal, 0)
        unpenalized_cap = int((self.rm.portfolio_value * self.rm.max_position_size_pct) / 70000.0)
        self.assertLessEqual(qty_normal, unpenalized_cap)

        # 2. SEVERE crisis: must return exactly 0
        self.rm.crisis_detector.crisis_level = CrisisLevel.SEVERE
        qty_severe = self.rm.calculate_position_sizing(
            symbol="005930",
            entry_price=70000.0,
            stop_loss_price=66500.0,
            win_rate=0.55,
            win_loss_ratio=1.5
        )
        self.assertEqual(qty_severe, 0, "New buy sizing must return 0 under SEVERE crisis")
        self.rm.crisis_detector.crisis_level = CrisisLevel.NORMAL

        # 3. Invalid stop loss price (stop >= entry) -> must return 0
        qty_invalid_stop = self.rm.calculate_position_sizing(
            symbol="005930",
            entry_price=70000.0,
            stop_loss_price=71000.0
        )
        self.assertEqual(qty_invalid_stop, 0, "Stop loss >= entry price must return 0")

        # 4. NaN / None stop loss price -> fallback to default stop loss without throwing
        qty_nan_stop = self.rm.calculate_position_sizing(
            symbol="005930",
            entry_price=70000.0,
            stop_loss_price=float("nan")
        )
        self.assertGreater(qty_nan_stop, 0)

        # 5. Non-positive or NaN entry price -> must return 0
        self.assertEqual(self.rm.calculate_position_sizing("005930", 0.0, 0.0), 0)
        self.assertEqual(self.rm.calculate_position_sizing("005930", -100.0, -110.0), 0)
        self.assertEqual(self.rm.calculate_position_sizing("005930", float("nan"), 65000.0), 0)


class TestAdversarialConcurrencyAndThroughput(unittest.TestCase):
    """Domain 4: Concurrency and Thread Safety Under Rapid Order Generation."""

    def test_concurrent_order_plan_generation_multi_threaded(self):
        """Simulate 10 worker threads simultaneously generating order plans with shared SQLite."""
        db_path = "test_concurrent_oms.db"
        if os.path.exists(db_path):
            try:
                os.remove(db_path)
            except Exception:
                pass

        oms = ExecutionOMSEngine(db_path=db_path, version=102)
        n_threads = 10
        errors = []
        order_counts = []

        def worker_task(thread_id: int):
            try:
                crisis_levels = ["NORMAL", "WATCH", "ACTIVE", "RECOVERY", "ELEVATED"]
                cl = crisis_levels[thread_id % len(crisis_levels)]
                symbols = [f"SYM_{thread_id}_{j}" for j in range(5)]
                preds = [
                    {"symbol": s, "market": "KOSPI", "target_price": 50000.0 + j * 1000, "expected_return": 0.05}
                    for j, s in enumerate(symbols)
                ]
                weights = {s: 0.05 for s in symbols}
                plans = oms.generate_order_plan(
                    top_predictions=preds,
                    portfolio_weights=weights,
                    total_capital=100000000.0,
                    crisis_level=cl
                )
                order_counts.append(len(plans))
            except Exception as e:
                errors.append(f"Thread {thread_id} failed: {e}")

        threads = [threading.Thread(target=worker_task, args=(i,)) for i in range(n_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        if os.path.exists(db_path):
            try:
                os.remove(db_path)
            except Exception:
                pass

        self.assertEqual(len(errors), 0, f"Concurrent threads raised errors: {errors}")
        self.assertEqual(len(order_counts), n_threads, "All threads must complete successfully")
        self.assertTrue(all(c > 0 for c in order_counts), f"All threads must generate orders: {order_counts}")


if __name__ == "__main__":
    unittest.main()
