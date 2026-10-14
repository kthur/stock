"""
Adversarial Stress Test Suite for R3 OMS Safety Gates & Numerical Resilience
Challenger 2 (teamwork_preview_challenger) - Risk Defense Overhaul M2

Probes:
1. OMS 8 Safety Gates under extreme/toxic order flow, zero/negative prices, huge quantities,
   and Gate 8 synthetic inverse hedge order generation.
2. Dynamic volatility & ATR fallbacks under NaN, Inf, zero, and negative inputs.
3. Kelly position sizing clipping strictly within [0, max_cap] under invalid stop loss inputs,
   extreme win rates, zero prices, and crisis states.
"""

import math
import os
import sqlite3
import pytest
import numpy as np
import pandas as pd

from src.execution.oms_engine import ExecutionOMSEngine, _MIN_PRICE_BOUND, _MAX_PRICE_BOUND
from src.execution.kill_switch import engage as engage_kill_switch, disengage as disengage_kill_switch
from src.risk.risk_manager import RiskManager, CrisisDetector, CrisisLevel
from src.risk.portfolio_allocator import PortfolioAllocator


class TestOMS8SafetyGatesAdversarial:
    """Adversarial stress-testing of all OMS 8 Safety Gates."""

    @pytest.fixture(autouse=True)
    def ensure_kill_switch_clean(self):
        disengage_kill_switch()
        yield
        disengage_kill_switch()

    def test_gate1_kill_switch_suppression_and_recovery(self, tmp_path):
        db_file = str(tmp_path / "test_gate1.db")
        oms = ExecutionOMSEngine(db_path=db_file)
        preds = [{"symbol": "005930", "market": "KOSPI", "close_price": 70000.0, "target_price": 70000.0}]
        weights = {"005930": 0.20}

        # Baseline: normal generation
        plans_before = oms.generate_order_plan(preds, weights, total_capital=100_000_000.0)
        assert len(plans_before) == 1, "Baseline order generation must yield 1 order"

        # Engage kill switch
        engage_kill_switch(reason="Adversarial stress test trigger")
        plans_blocked = oms.generate_order_plan(preds, weights, total_capital=100_000_000.0)
        assert plans_blocked == [], "Gate 1 Kill Switch must unconditionally return empty list"

        # Disengage and verify recovery
        disengage_kill_switch()
        plans_after = oms.generate_order_plan(preds, weights, total_capital=100_000_000.0)
        assert len(plans_after) == 1, "After kill switch disengagement, order generation must resume"

    def test_gate2_crisis_gating_hierarchical_haircuts_and_severe_blocking(self, tmp_path):
        db_file = str(tmp_path / "test_gate2.db")
        oms = ExecutionOMSEngine(db_path=db_file)
        preds = [
            {"symbol": "005930", "market": "KOSPI", "close_price": 70000.0, "target_price": 70000.0, "action": "BUY"},
            {"symbol": "AAPL", "market": "NASDAQ", "close_price": 200.0, "target_price": 200.0, "action": "BUY"},
        ]
        weights = {"005930": 0.50, "AAPL": 0.50}

        # 1. NORMAL crisis level
        plans_normal = oms.generate_order_plan(preds, weights, total_capital=100_000_000.0, crisis_level="NORMAL")
        assert len(plans_normal) == 2
        amt_normal_krw = plans_normal[0]["target_amount"]

        # 2. WATCH / ELEVATED crisis level (0.70 multiplier)
        plans_watch = oms.generate_order_plan(preds, weights, total_capital=100_000_000.0, crisis_level="WATCH")
        assert len(plans_watch) == 2
        amt_watch_krw = plans_watch[0]["target_amount"]
        assert math.isclose(amt_watch_krw, amt_normal_krw * 0.70, rel_tol=1e-3), "WATCH must scale capital to 70%"

        # 3. ACTIVE / HIGH crisis level (0.40 multiplier)
        plans_active = oms.generate_order_plan(preds, weights, total_capital=100_000_000.0, crisis_level="ACTIVE")
        assert len(plans_active) == 2
        amt_active_krw = plans_active[0]["target_amount"]
        assert math.isclose(amt_active_krw, amt_normal_krw * 0.40, rel_tol=1e-3), "ACTIVE must scale capital to 40%"

        # 4. Enum-based CrisisLevel compatibility
        plans_enum_high = oms.generate_order_plan(preds, weights, total_capital=100_000_000.0, crisis_level=CrisisLevel.ACTIVE)
        assert len(plans_enum_high) == 2
        assert math.isclose(plans_enum_high[0]["target_amount"], amt_normal_krw * 0.40, rel_tol=1e-3)

        # 5. SEVERE crisis level: 100% blocks standard BUY orders
        plans_severe = oms.generate_order_plan(preds, weights, total_capital=100_000_000.0, crisis_level=CrisisLevel.SEVERE)
        assert plans_severe == [], "SEVERE crisis must block all standard BUY order plans"

        # 6. SEVERE crisis allows SELL / liquidation orders
        current_holdings = {"005930": {"portfolio_weight": 0.50, "shares": 714, "current_price": 70000.0}}
        weights_liquidate = {"005930": 0.0}
        plans_severe_sell = oms.generate_order_plan(
            preds, weights_liquidate, total_capital=100_000_000.0, crisis_level="SEVERE", current_holdings=current_holdings
        )
        sell_orders = [p for p in plans_severe_sell if p["action"] == "SELL"]
        assert len(sell_orders) == 1, "SEVERE crisis must allow liquidation/SELL orders"

        # 7. Capitulation oversold entry in SEVERE crisis is permitted but capped to <= 15%
        capitulation_preds = [
            {
                "symbol": "005930",
                "market": "KOSPI",
                "close_price": 70000.0,
                "target_price": 70000.0,
                "action": "BUY",
                "short_term_reversal": 0.85,
                "expected_return": 5.0
            }
        ]
        plans_capitulation = oms.generate_order_plan(
            capitulation_preds, {"005930": 0.80}, total_capital=100_000_000.0, crisis_level="SEVERE"
        )
        assert len(plans_capitulation) == 1
        assert plans_capitulation[0]["target_weight"] <= 0.15, "Capitulation oversold play must be capped to <= 15%"

    def test_gate3_symbol_validation_corrupted_dict_and_garbage_rejection(self, tmp_path):
        db_file = str(tmp_path / "test_gate3.db")
        oms = ExecutionOMSEngine(db_path=db_file)
        toxic_preds = [
            {"symbol": "{'is_vcp': False, 'vcp_score': 45.0, 'symbol': 'MSFT'}", "close_price": 100.0, "market": "NASDAQ"},
            {"symbol": "", "close_price": 100.0, "market": "KOSPI"},
            {"symbol": None, "close_price": 100.0, "market": "KOSPI"},
            {"symbol": "005930; DROP TABLE order_plans;--", "close_price": 70000.0, "market": "KOSPI"},
            {"symbol": "INVALID SYMBOL WITH SPACES", "close_price": 50.0, "market": "US"},
            {"symbol": "VALID_SYM", "close_price": 50.0, "market": "US"},
        ]
        weights = {p["symbol"]: 0.20 for p in toxic_preds if p["symbol"]}

        plans = oms.generate_order_plan(toxic_preds, weights, total_capital=100_000_000.0)
        assert len(plans) == 1
        assert plans[0]["symbol"] == "VALID_SYM"

    def test_gate4_price_sanity_extreme_and_degenerate_bounds(self, tmp_path):
        db_file = str(tmp_path / "test_gate4.db")
        oms = ExecutionOMSEngine(db_path=db_file)
        bad_price_preds = [
            {"symbol": "SYM_ZERO", "market": "US", "close_price": 0.0},
            {"symbol": "SYM_NEG", "market": "US", "close_price": -50.0},
            {"symbol": "SYM_NAN", "market": "US", "close_price": float("nan")},
            {"symbol": "SYM_INF", "market": "US", "close_price": float("inf")},
            {"symbol": "SYM_NEGINF", "market": "US", "close_price": float("-inf")},
            {"symbol": "SYM_TINY", "market": "US", "close_price": 0.50},  # < _MIN_PRICE_BOUND=1.0
            {"symbol": "SYM_HUGE", "market": "KRX", "close_price": 200_000_000.0},  # > _MAX_PRICE_BOUND=100M
            {"symbol": "SYM_NONE", "market": "US"},  # No price at all
            {"symbol": "SYM_VALID", "market": "US", "close_price": 150.0},
        ]
        weights = {p["symbol"]: 0.10 for p in bad_price_preds}

        plans = oms.generate_order_plan(bad_price_preds, weights, total_capital=100_000_000.0)
        assert len(plans) == 1
        assert plans[0]["symbol"] == "SYM_VALID"
        assert plans[0]["target_price"] == 150.0

    def test_gate5_extreme_quantities_and_capital_bounds(self, tmp_path):
        db_file = str(tmp_path / "test_gate5.db")
        oms = ExecutionOMSEngine(db_path=db_file)
        preds = [{"symbol": "005930", "market": "KOSPI", "close_price": 70000.0, "target_price": 70000.0}]
        weights = {"005930": 0.50}

        # 1. Zero capital -> 0 orders
        assert oms.generate_order_plan(preds, weights, total_capital=0.0) == []

        # 2. Negative capital -> 0 orders
        assert oms.generate_order_plan(preds, weights, total_capital=-100_000_000.0) == []

        # 3. NaN / Inf capital -> fallback to safe 100M default
        plans_nan = oms.generate_order_plan(preds, weights, total_capital=float("nan"))
        assert len(plans_nan) == 1
        assert math.isclose(plans_nan[0]["target_amount"], 50_000_000.0, rel_tol=1e-2)

        plans_inf = oms.generate_order_plan(preds, weights, total_capital=float("inf"))
        assert len(plans_inf) == 1
        assert math.isclose(plans_inf[0]["target_amount"], 50_000_000.0, rel_tol=1e-2)

        # 4. Huge capital (10 Trillion KRW) -> produces valid large integer shares without overflow
        plans_huge = oms.generate_order_plan(preds, weights, total_capital=10_000_000_000_000.0)
        assert len(plans_huge) == 1
        assert plans_huge[0]["quantity"] > 0
        assert isinstance(plans_huge[0]["quantity"], int)
        assert math.isfinite(plans_huge[0]["order_amount"])

    def test_gate6_leland_dynamic_buffer_band_no_trade_hold(self, tmp_path):
        db_file = str(tmp_path / "test_gate6.db")
        oms = ExecutionOMSEngine(db_path=db_file)
        preds = [
            {"symbol": "005930", "market": "KOSPI", "close_price": 70000.0, "target_price": 70000.0, "volatility_20d": 0.02}
        ]

        # Case A: Current weight 0.20, Target weight 0.202 (drift = 0.002, inside Leland buffer)
        current_holdings = {"005930": {"portfolio_weight": 0.20, "shares": 285, "current_price": 70000.0}}
        weights_minor = {"005930": 0.202}
        plans_hold = oms.generate_order_plan(
            preds, weights_minor, total_capital=100_000_000.0, current_holdings=current_holdings, use_leland_buffer=True
        )
        assert plans_hold == [], "Minor drift within Leland band must be skipped (HOLD)"

        # Case B: Significant rebalance (Target = 0.35, outside Leland buffer) -> creates order
        weights_major = {"005930": 0.35}
        plans_rebalance = oms.generate_order_plan(
            preds, weights_major, total_capital=100_000_000.0, current_holdings=current_holdings, use_leland_buffer=True
        )
        assert len(plans_rebalance) == 1
        assert plans_rebalance[0]["action"] == "BUY"

        # Case C: New entry (Current = 0.0, Target = 0.20) -> immediately bypasses buffer
        plans_new_entry = oms.generate_order_plan(
            preds, {"005930": 0.20}, total_capital=100_000_000.0, current_holdings={}, use_leland_buffer=True
        )
        assert len(plans_new_entry) == 1

        # Case D: Full liquidation (Current = 0.20, Target = 0.0) -> immediately bypasses buffer
        plans_exit = oms.generate_order_plan(
            preds, {"005930": 0.0}, total_capital=100_000_000.0, current_holdings=current_holdings, use_leland_buffer=True
        )
        assert len(plans_exit) == 1
        assert plans_exit[0]["action"] == "SELL"

    def test_gate7_krx_microstructure_and_limits(self, tmp_path):
        db_file = str(tmp_path / "test_gate7.db")
        oms = ExecutionOMSEngine(db_path=db_file)

        # Gate 7.1: KRX Short-Sell mapping to CASH_OVERLAY
        pred_short = [{"symbol": "005930", "market": "KOSPI", "close_price": 70000.0, "action": "SHORT"}]
        plans_short = oms.generate_order_plan(pred_short, {"005930": 0.10}, total_capital=100_000_000.0)
        assert len(plans_short) == 1
        assert plans_short[0]["action"] == "CASH_OVERLAY"
        assert plans_short[0]["status"] == "HEDGE_FLAG"

        # Gate 7.2: KRX Upper limit lock (+30%) blocks BUY
        pred_upper = [{"symbol": "005930", "market": "KOSPI", "close_price": 70000.0, "action": "BUY", "change_pct": 29.8}]
        plans_upper = oms.generate_order_plan(pred_upper, {"005930": 0.10}, total_capital=100_000_000.0)
        assert plans_upper == [], "Upper price limit lock (+29.8%) must block new BUY orders"

        # Gate 7.4: Adverse opening gap filter (-4 * vol) blocks BUY
        pred_adverse_gap = [{
            "symbol": "005930", "market": "KOSPI", "close_price": 70000.0, "action": "BUY",
            "volatility_20d": 0.02, "change_pct": -10.0  # -10% gap is worse than -3*2% = -6%
        }]
        plans_adverse = oms.generate_order_plan(pred_adverse_gap, {"005930": 0.10}, total_capital=100_000_000.0)
        assert plans_adverse == [], "Adverse opening gap (-10% < -3*vol) must block BUY"

        # Gate 7.6: High VPIN order flow toxicity routes BUY to PASSIVE_LIMIT
        pred_vpin_buy = [{
            "symbol": "005930", "market": "KOSPI", "close_price": 70000.0, "action": "BUY",
            "vpin": 0.85  # Toxic buyer flow
        }]
        plans_vpin_buy = oms.generate_order_plan(pred_vpin_buy, {"005930": 0.10}, total_capital=100_000_000.0)
        assert len(plans_vpin_buy) == 1
        assert plans_vpin_buy[0]["execution_strategy"] == "PASSIVE_LIMIT"

        # Gate 7.7: Overheated gap (>= 5%) routes to DIP_LIMIT with adaptive discount
        pred_gap_up = [{
            "symbol": "005930", "market": "KOSPI", "close_price": 70000.0, "action": "BUY",
            "change_pct": 6.5, "atr_15m": 1400.0
        }]
        plans_gap_up = oms.generate_order_plan(pred_gap_up, {"005930": 0.10}, total_capital=100_000_000.0)
        assert len(plans_gap_up) == 1
        assert plans_gap_up[0]["execution_strategy"] == "DIP_LIMIT"
        assert plans_gap_up[0]["target_price"] < 70000.0, "DIP_LIMIT target price must be shaded below close"

    def test_gate7_2_lower_limit_lock_unbound_slice_count_bug(self, tmp_path):
        """
        CRITICAL DEFECT DEMONSTRATION:
        Under Gate 7.2 (KRX lower limit lock -30%), when action == 'SELL',
        oms_engine:657 sets exec_strategy = 'PASSIVE_LIMIT'.
        Because exec_strategy is preassigned, lines 861-876 are bypassed and
        slice_count is NEVER initialized, causing UnboundLocalError at line 881:
        'slice_count = min(slice_count, max_possible_slices)'.
        """
        db_file = str(tmp_path / "test_gate7_bug.db")
        oms = ExecutionOMSEngine(db_path=db_file)
        current_holdings = {"005930": {"portfolio_weight": 0.10, "shares": 142, "current_price": 70000.0}}
        pred_lower = [{"symbol": "005930", "market": "KOSPI", "close_price": 70000.0, "action": "SELL", "change_pct": -29.9}]

        # Remediated: generate_order_plan now cleanly generates valid order plan without UnboundLocalError
        plans = oms.generate_order_plan(
            pred_lower, {"005930": 0.0}, total_capital=100_000_000.0, current_holdings=current_holdings
        )
        assert len(plans) == 1
        assert plans[0]["exec_strategy"] == "PASSIVE_LIMIT"
        assert plans[0]["slice_count"] >= 1

    def test_gate8_synthetic_inverse_hedge_generation_and_edge_cases(self, tmp_path):
        db_file = str(tmp_path / "test_gate8.db")
        oms = ExecutionOMSEngine(db_path=db_file)

        # 1. Bear regime with KRX portfolio
        krx_preds = [{"symbol": "005930", "market": "KOSPI", "close_price": 70000.0}]
        plans_krx_hedge = oms.generate_order_plan(
            krx_preds, {"005930": 0.40}, total_capital=100_000_000.0, regime_label="BEAR_HIGH_VOL"
        )
        hedge_krx = [p for p in plans_krx_hedge if p.get("name") == "INVERSE_HEDGE_OVERLAY"]
        assert len(hedge_krx) == 1, "BEAR_HIGH_VOL with KRX holdings must generate 1 KRX inverse hedge"
        assert hedge_krx[0]["symbol"] in ["114800", "252670"], f"Expected KRX inverse symbol, got {hedge_krx[0]['symbol']}"
        assert hedge_krx[0]["action"] == "BUY_HEDGE"
        assert hedge_krx[0]["quantity"] > 0

        # 2. Crisis regime with US NASDAQ portfolio
        us_preds = [{"symbol": "NVDA", "market": "NASDAQ", "close_price": 120.0}]
        plans_us_hedge = oms.generate_order_plan(
            us_preds, {"NVDA": 0.40}, total_capital=100_000_000.0, regime_label="CRISIS", usdkrw_rate=1350.0
        )
        hedge_us = [p for p in plans_us_hedge if p.get("name") == "INVERSE_HEDGE_OVERLAY"]
        assert len(hedge_us) == 1, "CRISIS with US NASDAQ holdings must generate 1 US inverse hedge"
        assert hedge_us[0]["symbol"] in ["PSQ", "SH"], f"Expected US inverse symbol, got {hedge_us[0]['symbol']}"

        # 3. Dual market (KRX + US) generates 2 decomposed hedges
        dual_preds = [
            {"symbol": "005930", "market": "KOSPI", "close_price": 70000.0},
            {"symbol": "AAPL", "market": "NASDAQ", "close_price": 200.0}
        ]
        plans_dual = oms.generate_order_plan(
            dual_preds, {"005930": 0.25, "AAPL": 0.25}, total_capital=100_000_000.0, regime_label="BEAR_HIGH_VOL"
        )
        hedge_dual = [p for p in plans_dual if p.get("name") == "INVERSE_HEDGE_OVERLAY"]
        assert len(hedge_dual) == 2, "Dual market portfolio in BEAR regime must generate 2 decomposed hedges"

        # 4. Bull regime -> Zero hedge orders
        plans_bull = oms.generate_order_plan(
            dual_preds, {"005930": 0.25, "AAPL": 0.25}, total_capital=100_000_000.0, regime_label="BULL_LOW_VOL"
        )
        hedge_bull = [p for p in plans_bull if p.get("name") == "INVERSE_HEDGE_OVERLAY"]
        assert len(hedge_bull) == 0, "BULL regime must not generate inverse hedges"

        # 5. Missing / zero hedge price fallback
        # When price dictionary has 0.0 or missing price for 114800, oms._get_latest_price returns 0.0,
        # and oms_engine falls back to 10,000.0 KRW for KRX or 50.0 USD for US.
        plans_zero_px = oms.generate_order_plan(
            krx_preds, {"005930": 0.30}, total_capital=100_000_000.0, regime_label="BEAR_HIGH_VOL",
            prices_dict={"114800": 0.0}
        )
        hedge_zero = [p for p in plans_zero_px if p.get("name") == "INVERSE_HEDGE_OVERLAY"]
        assert len(hedge_zero) == 1
        assert hedge_zero[0]["target_price"] == 10000.0, "Zero price fallback must establish 10,000 KRW for KRX hedge"
        assert hedge_zero[0]["quantity"] > 0


class TestNumericalResilienceVolatilityAndATR:
    """Adversarial stress-testing of ATR and Volatility fallbacks under NaN, Inf, zero, and negative inputs."""

    @pytest.fixture
    def rm(self):
        return RiskManager(portfolio_value=100_000_000.0)

    def test_check_stop_loss_atr_fallbacks(self, rm):
        entry_price = 10000.0
        current_price = 9400.0  # -6% return
        default_sl = rm.default_stop_loss_pct  # 0.05 -> stop price = 9500

        # Normal valid ATR: atr = 200 -> stop_distance = 200 * 2.0 = 400 -> stop price = 9600
        assert rm.check_stop_loss("SYM", current_price=9400.0, entry_price=entry_price, atr=200.0) is True

        # Degenerate non-positive, negative-inf, positive-inf, and NaN ATR inputs safely fallback to 5% default stop loss:
        for bad_atr in [float("nan"), float("-inf"), float("inf"), 0.0, -50.0, None]:
            # With default stop 9500, price 9400 is below 9500 -> True
            assert rm.check_stop_loss("SYM", current_price=9400.0, entry_price=entry_price, atr=bad_atr) is True
            # With default stop 9500, price 9600 is above 9500 -> False
            assert rm.check_stop_loss("SYM", current_price=9600.0, entry_price=entry_price, atr=bad_atr) is False

    def test_check_take_profit_atr_fallbacks(self, rm):
        entry_price = 10000.0
        default_tp = rm.default_take_profit_pct  # 0.15 -> target price = 11500

        # Degenerate non-positive, negative-inf, positive-inf, and NaN ATR inputs safely fallback to 15% default target:
        for bad_atr in [float("nan"), float("-inf"), float("inf"), 0.0, -100.0, None]:
            # Price 11600 is above default TP 11500 -> True
            assert rm.check_take_profit("SYM", current_price=11600.0, entry_price=entry_price, atr=bad_atr) is True
            # Price 11400 is below default TP 11500 -> False
            assert rm.check_take_profit("SYM", current_price=11400.0, entry_price=entry_price, atr=bad_atr) is False

    def test_calculate_trailing_stop_price_adversarial(self, rm):
        prev_stop = 9000.0
        highest_price = 10000.0

        # Valid ATR calculation
        valid_stop = rm.calculate_trailing_stop_price(highest_price, atr=200.0, previous_stop_price=prev_stop)
        assert valid_stop >= prev_stop
        assert math.isfinite(valid_stop)

        # Adversarial inputs: NaN, Inf, Negative, Zero ATR
        for bad_atr in [float("nan"), float("inf"), -10.0, 0.0, None]:
            stop_res = rm.calculate_trailing_stop_price(highest_price, atr=bad_atr, previous_stop_price=prev_stop)
            assert stop_res == prev_stop, f"Bad ATR {bad_atr} must fall back to previous_stop_price"

        # Adversarial highest price: NaN, Inf, Negative, Zero
        for bad_hp in [float("nan"), float("inf"), -100.0, 0.0, None]:
            stop_res = rm.calculate_trailing_stop_price(bad_hp, atr=200.0, previous_stop_price=prev_stop)
            assert stop_res == prev_stop, f"Bad highest_price {bad_hp} must fall back to previous_stop_price"

    def test_oms_engine_dynamic_sl_tp_volatility_finiteness(self, tmp_path):
        db_file = str(tmp_path / "test_vol_finiteness.db")
        oms = ExecutionOMSEngine(db_path=db_file)

        # Predictions with diverse corrupted volatilities
        preds = [
            {"symbol": "SYM_VOL_NAN", "market": "US", "close_price": 100.0, "volatility_20d": float("nan")},
            {"symbol": "SYM_VOL_INF", "market": "US", "close_price": 100.0, "volatility_20d": float("inf")},
            {"symbol": "SYM_VOL_NEG", "market": "US", "close_price": 100.0, "volatility_20d": -0.50},
            {"symbol": "SYM_VOL_ZERO", "market": "US", "close_price": 100.0, "volatility_20d": 0.0},
            {"symbol": "SYM_VOL_STRING", "market": "US", "close_price": 100.0, "volatility_20d": "corrupt"},
        ]
        weights = {p["symbol"]: 0.15 for p in preds}

        plans = oms.generate_order_plan(preds, weights, total_capital=100_000_000.0)
        assert len(plans) == len(preds), "All plans with corrupted volatility must be safely rescued"

        for p in plans:
            sl = p["target_stop_loss"]
            tp = p["target_take_profit"]
            px = p["target_price"]
            assert math.isfinite(sl) and sl > 0.0, f"Stop loss {sl} must be finite positive"
            assert math.isfinite(tp) and tp > 0.0, f"Take profit {tp} must be finite positive"
            assert sl < px < tp, f"Must maintain sl ({sl}) < price ({px}) < tp ({tp})"

    def test_vix_scalar_and_position_caps_boundary_resilience(self, rm):
        # VIX scalar robustness
        for bad_vix in [0.0, -10.0, float("nan"), float("inf")]:
            scalar = rm._volatility_scalar(bad_vix)
            assert math.isfinite(scalar) and 0.25 <= scalar <= 1.5

        # VIX position cap
        assert rm.get_vix_position_cap(35.0) == 0.40
        assert rm.get_vix_position_cap(26.0) == 0.60
        assert rm.get_vix_position_cap(22.0) == 0.80
        assert rm.get_vix_position_cap(15.0) == 1.00
        assert rm.get_vix_position_cap(float("nan")) == 1.00
        assert rm.get_vix_position_cap(float("inf")) == 0.40


class TestKellyPositionSizingClipping:
    """Adversarial stress-testing of Kelly Position Sizing and clipping bounds."""

    @pytest.fixture
    def rm(self):
        return RiskManager(portfolio_value=100_000_000.0)

    def test_calculate_kelly_fraction_bounds(self, rm):
        max_cap = rm.max_position_size_pct  # default 0.20

        # Normal valid Kelly
        k = rm.calculate_kelly_fraction(win_rate=0.60, win_loss_ratio=2.0)
        # f* = 0.60 - 0.40 / 2.0 = 0.40. Half Kelly = 0.20. Clipped to max_cap 0.20
        assert math.isclose(k, max_cap, rel_tol=1e-5)

        # Edge cases: non-positive win_loss_ratio
        assert rm.calculate_kelly_fraction(win_rate=0.60, win_loss_ratio=0.0) == 0.0
        assert rm.calculate_kelly_fraction(win_rate=0.60, win_loss_ratio=-1.5) == 0.0

        # Edge cases: win_rate out of (0, 1)
        assert rm.calculate_kelly_fraction(win_rate=0.0, win_loss_ratio=2.0) == 0.0
        assert rm.calculate_kelly_fraction(win_rate=1.0, win_loss_ratio=2.0) == 0.0
        assert rm.calculate_kelly_fraction(win_rate=-0.2, win_loss_ratio=2.0) == 0.0
        assert rm.calculate_kelly_fraction(win_rate=1.5, win_loss_ratio=2.0) == 0.0

        # Non-finite inputs
        assert rm.calculate_kelly_fraction(win_rate=float("nan"), win_loss_ratio=2.0) == 0.0
        assert rm.calculate_kelly_fraction(win_rate=0.5, win_loss_ratio=float("nan")) == 0.0
        assert rm.calculate_kelly_fraction(win_rate=float("inf"), win_loss_ratio=2.0) == 0.0
        assert rm.calculate_kelly_fraction(win_rate=0.5, win_loss_ratio=float("inf")) == 0.0

        # Negative edge Kelly (f* < 0)
        assert rm.calculate_kelly_fraction(win_rate=0.20, win_loss_ratio=1.0) == 0.0

    def test_calculate_position_sizing_invalid_stop_loss(self, rm):
        entry_price = 50000.0

        # Invalid stop loss >= entry price (stop above entry for long buy) -> must return 0
        assert rm.calculate_position_sizing("SYM", entry_price=entry_price, stop_loss_price=50000.0) == 0
        assert rm.calculate_position_sizing("SYM", entry_price=entry_price, stop_loss_price=55000.0) == 0

        # Missing / NaN / negative stop loss -> must safely fallback to default 5% stop
        qty_fallback_none = rm.calculate_position_sizing("SYM", entry_price=entry_price, stop_loss_price=None)
        assert qty_fallback_none > 0

        qty_fallback_nan = rm.calculate_position_sizing("SYM", entry_price=entry_price, stop_loss_price=float("nan"))
        assert qty_fallback_nan == qty_fallback_none

        qty_fallback_neg = rm.calculate_position_sizing("SYM", entry_price=entry_price, stop_loss_price=-1000.0)
        assert qty_fallback_neg == qty_fallback_none

    def test_calculate_position_sizing_severe_crisis_blocking(self, rm):
        # Set crisis level to SEVERE
        rm.crisis_detector.crisis_level = CrisisLevel.SEVERE
        assert rm.crisis_detector.should_block_new_buys() is True

        qty = rm.calculate_position_sizing(
            "SYM", entry_price=50000.0, stop_loss_price=47500.0, win_rate=0.70, win_loss_ratio=2.5
        )
        assert qty == 0, "calculate_position_sizing must return 0 under SEVERE crisis"

    def test_calculate_position_sizing_zero_and_extreme_prices(self, rm):
        # Zero, negative, non-finite entry prices
        for bad_px in [0.0, -100.0, float("nan"), float("inf"), None]:
            assert rm.calculate_position_sizing("SYM", entry_price=bad_px, stop_loss_price=40.0) == 0

        # Extreme positive parameters: Kelly should NEVER breach unpenalized_max_position
        entry_price = 50000.0
        stop_price = 49999.0  # minimal risk per share = 1 KRW, could theoretically allow huge shares
        max_shares_allowed = int((rm.portfolio_value * rm.max_position_size_pct) / entry_price)

        qty = rm.calculate_position_sizing(
            "SYM", entry_price=entry_price, stop_loss_price=stop_price, win_rate=0.99, win_loss_ratio=100.0
        )
        assert qty <= max_shares_allowed, f"Calculated qty ({qty}) must strictly obey max position cap ({max_shares_allowed})"
