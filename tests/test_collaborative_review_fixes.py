"""
test_collaborative_review_fixes.py — Multi-Disciplinary Quality & Regression Test Suite

Covers fixes collaboratively reviewed across:
1. Finance & Trader: KRX lot_size=1 unit, tick size rounding (ExecutionOMSEngine.round_to_tick_size),
   market string case normalization (preventing 1380x FX explosion on lowercase 'kospi').
2. Software Architecture & Risk Management: Multi-root KILL_SWITCH detection (trading_system + workspace root).
3. Risk Management: IntradayStopLossEngine multi-day intraday peak detection.
4. System Evaluation & UX: Symmetric prediction report scaling (no -250% bug on negative z-scores).
"""

import os
import math
import numpy as np
import pandas as pd
import pytest

from trading_system.src.realtime.trade_executor import TradeExecutor, ExecResult
from trading_system.src.execution import kill_switch
from trading_system.src.execution.oms_engine import ExecutionOMSEngine
from trading_system.src.risk.intraday_stop_loss import IntradayStopLossEngine
from trading_system.src.pipeline.prediction_reporter import (
    save_strategy_predictions_report,
    slice_top_dataframe,
)


class _MockKiwoom:
    is_connected = True
    simulation_mode = False

    def __init__(self):
        self.last_order = None

    def place_order(self, code, quantity, price, order_type):
        self.last_order = (code, quantity, price, order_type)
        return "MOCK_ORD_12345"


class TestCollaborativeFixes:
    """Multi-disciplinary test cases ensuring financial, trading, and system integrity."""

    def test_trader_krx_lot_size_one(self):
        """Trader & Finance: KRX lot size is 1 share; single-digit quantities are never dropped."""
        mock_kw = _MockKiwoom()
        ex = TradeExecutor(kiwoom=mock_kw, oms=None, dry_run=True)
        assert ex.lot_size_krx == 1

        # Test 3 shares of high-price stock (e.g. KRW 750,000)
        res = ex.execute("207940", "KOSPI", "BUY", quantity=3, price=750000.0)
        assert res.executed
        assert res.quantity == 3
        assert res.action == "BUY"

    def test_trader_krx_tick_size_rounding_applied(self):
        """Trader & Microstructure: TradeExecutor automatically rounds prices to valid exchange ticks."""
        mock_kw = _MockKiwoom()
        ex = TradeExecutor(kiwoom=mock_kw, oms=None, dry_run=True)

        # 72,345 KRW is in 50,000 ~ 200,000 KRW bracket (tick = 100 KRW)
        res = ex.execute("005930", "KOSPI", "BUY", quantity=10, price=72345.0)
        assert res.executed
        # Rounded to nearest 100 KRW (72300.0)
        assert res.price == 72300.0

        # Sub-2000 KRW stock (tick = 1 KRW)
        res2 = ex.execute("000001", "KOSDAQ", "BUY", quantity=10, price=1543.78)
        assert res2.executed
        assert res2.price == 1544.0

    def test_trader_market_case_normalization(self):
        """Software Architecture & Trader: Lowercase 'kospi' or 'krx' must not multiply FX rate."""
        mock_kw = _MockKiwoom()
        # Max order value: 50,000,000 KRW
        ex = TradeExecutor(kiwoom=mock_kw, oms=None, dry_run=True, max_order_value_krw=50_000_000.0)

        # 500 shares * 70,000 KRW = 35,000,000 KRW.
        # If market="kospi" were misclassified as US, order value would become 35,000,000 * 1380 = 48.3B KRW (rejected).
        res = ex.execute("005930", "kospi", "BUY", quantity=500, price=70000.0)
        assert res.executed
        assert res.quantity == 500
        assert "over max order value" not in res.message

    def test_risk_kill_switch_workspace_root_detection(self, tmp_path, monkeypatch):
        """Risk Management & Arch: Kill switch detects file in both project root and workspace root."""
        # Setup mock file paths
        project_root_kill = tmp_path / "trading_system" / "KILL_SWITCH"
        workspace_root_kill = tmp_path / "KILL_SWITCH"
        state_file = tmp_path / "kill_switch_state.json"

        project_root_kill.parent.mkdir(parents=True, exist_ok=True)

        monkeypatch.setattr(kill_switch, "KILL_SWITCH_FILE", project_root_kill)
        monkeypatch.setattr(kill_switch, "WORKSPACE_KILL_SWITCH_FILE", workspace_root_kill)
        monkeypatch.setattr(kill_switch, "STATE_FILE", state_file)

        # Baseline: neither file exists
        assert not kill_switch.is_kill_switch_active()

        # Place KILL_SWITCH in workspace root
        workspace_root_kill.touch()
        assert kill_switch.is_kill_switch_active()

        # Disengage cleans up
        kill_switch.disengage()
        assert not workspace_root_kill.exists()
        assert not kill_switch.is_kill_switch_active()

        # Place KILL_SWITCH in project root
        project_root_kill.touch()
        assert kill_switch.is_kill_switch_active()

        kill_switch.disengage()
        assert not project_root_kill.exists()
        assert not kill_switch.is_kill_switch_active()

    def test_risk_intraday_stop_loss_multi_day_peak(self):
        """Risk Management: Intraday stop loss identifies today's intraday peak across multi-day candles."""
        engine = IntradayStopLossEngine(peak_drop_threshold=-0.04)

        # 2 days of 5-min candles: Day 1 (yesterday) peaked at 120.
        # Day 2 (today) opened at 100, peaked at 105, then dropped to 99 (-5.7% from today's peak 105).
        # But the very last candle high was 100.
        # If peak_price took highs[-1] (100), drop would be only (99-100)/100 = -1.0% (NO stop loss).
        # With today's peak (105), drop is (99-105)/105 = -5.71% -> MUST TRIGGER STOP LOSS.

        dates_day1 = pd.date_range("2026-09-25 09:00", "2026-09-25 15:30", freq="5min")
        dates_day2 = pd.date_range("2026-09-26 09:00", "2026-09-26 11:00", freq="5min")
        all_dates = dates_day1.append(dates_day2)

        highs = [120.0] * len(dates_day1) + [105.0] * 10 + [100.0] * (len(dates_day2) - 10)
        closes = [118.0] * len(dates_day1) + [104.0] * 10 + [99.0] * (len(dates_day2) - 10)
        vols = [1000] * len(all_dates)

        df = pd.DataFrame({
            'date': all_dates,
            'high': highs,
            'close': closes,
            'volume': vols,
        })

        res = engine.evaluate("005930", df)
        assert res.triggered
        assert "PEAK_TO_TROUGH_DROP" in res.reason
        assert res.drop_pct < -0.05

    def test_ux_prediction_reporter_symmetric_scaling(self, tmp_path):
        """System Evaluation & UX: Negative scores/z-scores must not explode by 100x."""
        df_strat = pd.DataFrame({
            "symbol": ["005930", "000660", "NVDA", "TSLA"],
            "score": [2.5, -2.5, 0.05, -0.05],
            "market": ["KOSPI", "KOSPI", "NASDAQ", "NASDAQ"],
            "name": ["Samsung", "SK Hynix", "Nvidia", "Tesla"],
        })

        out_file = "test_sym_scores.txt"
        save_strategy_predictions_report(
            df_strat=df_strat,
            score_col="score",
            title="Symmetric Scaling Test",
            output_filename=out_file,
            result_dir=str(tmp_path),
            score_header="Score",
        )

        content = (tmp_path / out_file).read_text(encoding="utf-8")

        # Verify symmetric representation:
        # 2.5 prints as 2.5%
        # -2.5 prints as -2.5% (NEVER -250.0%)
        # 0.05 prints as 5.0%
        # -0.05 prints as -5.0%
        assert "  2.5%" in content
        assert " -2.5%" in content
        assert "-250.0%" not in content
        assert "  5.0%" in content
        assert " -5.0%" in content
