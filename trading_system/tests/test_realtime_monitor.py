# -*- coding: utf-8 -*-
"""
Realtime Intraday Monitor 단위 테스트
- market_hours: KRX/US 장중 판별
- price_feed: yfinance 심볼 매핑, RealtimeQuote 계산
- state_store: SQLite 상태 영속화
- intraday_monitor: 손절/익절/시그널 보정/매크로 경보
- trade_executor: DRY_RUN / OMS 기록 / 상한·호가단위
"""

import os
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.realtime.market_hours import is_krx_open, is_us_open, get_session
from src.realtime.price_feed import RealtimeQuote, to_yfinance_symbol
from src.realtime.state_store import RealtimeStateStore
from src.realtime.intraday_monitor import IntradayMonitor, WatchItem
from src.realtime.trade_executor import TradeExecutor


class TestMarketHours(unittest.TestCase):
    def test_krx_open_afternoon(self):
        self.assertTrue(is_krx_open(datetime(2026, 8, 4, 14, 0)))   # 화요일 오후
        self.assertTrue(is_krx_open(datetime(2026, 8, 4, 9, 0)))    # 개장 시각
        self.assertTrue(is_krx_open(datetime(2026, 8, 4, 15, 30)))  # 마감 직전

    def test_krx_closed(self):
        self.assertFalse(is_krx_open(datetime(2026, 8, 4, 8, 59)))   # 개장 전
        self.assertFalse(is_krx_open(datetime(2026, 8, 4, 15, 31)))  # 마감 후
        self.assertFalse(is_krx_open(datetime(2026, 8, 8, 12, 0)))   # 토요일
        self.assertFalse(is_krx_open(datetime(2026, 8, 9, 12, 0)))   # 일요일

    def test_us_open_evening_kst(self):
        # KST 화요일 23:00 = US 장중
        self.assertTrue(is_us_open(datetime(2026, 8, 4, 23, 0)))

    def test_us_open_morning_kst(self):
        # KST 화요일 새벽 03:00 = US 월요일 장중
        self.assertTrue(is_us_open(datetime(2026, 8, 4, 3, 0)))

    def test_us_closed_weekend_kst_morning(self):
        # KST 일요일 새벽 = US 토요일 (휴장)
        self.assertFalse(is_us_open(datetime(2026, 8, 9, 3, 0)))

    def test_session_labels(self):
        s = get_session(datetime(2026, 8, 4, 14, 0))
        self.assertTrue(s.is_open)
        self.assertTrue(s.is_krx_trading)
        s2 = get_session(datetime(2026, 8, 4, 3, 0))
        self.assertTrue(s2.is_open)
        self.assertFalse(s2.is_krx_trading)
        s3 = get_session(datetime(2026, 8, 4, 17, 0))
        self.assertFalse(s3.is_open)


class TestPriceFeed(unittest.TestCase):
    def test_yfinance_symbol_mapping(self):
        self.assertEqual(to_yfinance_symbol("005930", "KOSPI"), "005930.KS")
        self.assertEqual(to_yfinance_symbol("068270", "KOSDAQ"), "068270.KQ")
        self.assertEqual(to_yfinance_symbol("AAPL", "SP500"), "AAPL")
        self.assertEqual(to_yfinance_symbol("005930", "KOSDAQ"), "005930.KQ")

    def test_quote_change_pct(self):
        q = RealtimeQuote(symbol="AAPL", market="SP500", price=110.0, prev_close=100.0)
        self.assertAlmostEqual(q.change_pct, 10.0)
        q2 = RealtimeQuote(symbol="AAPL", market="SP500", price=100.0, prev_close=0.0)
        self.assertEqual(q2.change_pct, 0.0)


class TestStateStore(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.store = RealtimeStateStore(db_path=self.db_path)

    def tearDown(self):
        try:
            os.unlink(self.db_path)
        except OSError:
            pass

    def test_state_roundtrip(self):
        from src.realtime.state_store import SymbolIntradayState
        st = SymbolIntradayState(symbol="005930", date="2026-08-04", open_price=60000,
                                 peak_price=61000, low_price=59000)
        self.store.update_state(st)
        loaded = self.store.get_state("005930", "2026-08-04")
        self.assertEqual(loaded.peak_price, 61000.0)
        self.assertEqual(loaded.open_price, 60000.0)

    def test_default_state_for_unknown(self):
        st = self.store.get_state("NVDA", "2026-08-04")
        self.assertEqual(st.open_price, 0.0)
        self.assertFalse(st.stop_triggered)

    def test_log_events(self):
        self.store.log_event("2026-08-04", "005930", "STOP_LOSS", "test stop", "detail")
        events = self.store.get_events("2026-08-04", "STOP_LOSS")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["symbol"], "005930")
        # 날짜별 필터
        other = self.store.get_events("2026-08-05", "STOP_LOSS")
        self.assertEqual(len(other), 0)


class TestIntradayMonitor(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.store = RealtimeStateStore(db_path=self.db_path)
        self.monitor = IntradayMonitor(state_store=self.store)

    def tearDown(self):
        try:
            os.unlink(self.db_path)
        except OSError:
            pass

    def test_stop_loss_trigger(self):
        item = WatchItem(symbol="005930", market="KOSPI", entry_price=100000.0,
                         position_qty=10, stop_loss_pct=-0.04)
        actions = self.monitor.evaluate_symbol(item, 95000.0, "2026-08-04")
        stop = [a for a in actions if a.action_type == "STOP_LOSS"]
        self.assertEqual(len(stop), 1)
        self.assertEqual(stop[0].symbol, "005930")
        self.assertEqual(stop[0].severity, "CRITICAL")

    def test_no_stop_without_position(self):
        item = WatchItem(symbol="AAPL", market="SP500", entry_price=0.0, position_qty=0)
        actions = self.monitor.evaluate_symbol(item, 90.0, "2026-08-04")
        stops = [a for a in actions if a.action_type == "STOP_LOSS"]
        self.assertEqual(len(stops), 0)

    def test_take_profit_trigger(self):
        item = WatchItem(symbol="005930", market="KOSPI", entry_price=100000.0,
                         position_qty=10, take_profit_pct=0.08)
        actions = self.monitor.evaluate_symbol(item, 110000.0, "2026-08-04")
        tp = [a for a in actions if a.action_type == "TAKE_PROFIT"]
        self.assertEqual(len(tp), 1)

    def test_signal_downgrade(self):
        item = WatchItem(symbol="005930", market="KOSPI", entry_price=0.0, position_qty=0,
                         expected_return=0.05)
        self.monitor.evaluate_symbol(item, 100000.0, "2026-08-04")  # 첫 틱이 시가로 설정
        actions2 = self.monitor.evaluate_symbol(item, 95000.0, "2026-08-04")  # 시가 대비 -5% 역행
        downgrades = [a for a in actions2 if a.action_type == "SIGNAL_DOWNGRADE"]
        self.assertEqual(len(downgrades), 1)

    def test_macro_alert(self):
        act = self.monitor.evaluate_macro(vix=35.0, usdkrw=None)
        self.assertIsNotNone(act)
        self.assertEqual(act.action_type, "MACRO_ALERT")
        self.assertIn("VIX", act.reason)
        act2 = self.monitor.evaluate_macro(vix=None, usdkrw=1500.0)
        self.assertIsNotNone(act2)
        self.assertIn("USD/KRW", act2.reason)
        act3 = self.monitor.evaluate_macro(vix=18.0, usdkrw=1350.0)
        self.assertIsNone(act3)

    def test_state_persisted_after_stop(self):
        item = WatchItem(symbol="005930", market="KOSPI", entry_price=100000.0,
                         position_qty=10)
        self.monitor.evaluate_symbol(item, 95000.0, "2026-08-04")
        st = self.store.get_state("005930", "2026-08-04")
        self.assertTrue(st.stop_triggered)
        self.assertIn("ENTRY_DROP", st.stop_reasons)

    def test_no_duplicate_stop_trigger(self):
        item = WatchItem(symbol="005930", market="KOSPI", entry_price=100000.0,
                         position_qty=10)
        self.monitor.evaluate_symbol(item, 95000.0, "2026-08-04")
        actions2 = self.monitor.evaluate_symbol(item, 94000.0, "2026-08-04")
        stops = [a for a in actions2 if a.action_type == "STOP_LOSS"]
        self.assertEqual(len(stops), 0)  # 이미 발동됨


class TestTradeExecutor(unittest.TestCase):
    def test_dry_run_executes(self):
        ex = TradeExecutor(dry_run=True)
        res = ex.execute("005930", "KOSPI", "SELL", 10, 100000.0, reason="STOP_LOSS")
        self.assertTrue(res.executed)
        self.assertEqual(res.mode, "dry_run")
        self.assertEqual(res.action, "SELL")

    def test_krx_lot_rounding(self):
        ex = TradeExecutor(dry_run=True)
        res = ex.execute("005930", "KOSPI", "BUY", 7, 100000.0)
        self.assertEqual(res.quantity, 10)  # 10주 단위로 반올림

    def test_max_order_value_capped(self):
        ex = TradeExecutor(dry_run=True, max_order_value_krw=1_000_000.0)
        res = ex.execute("005930", "KOSPI", "BUY", 1000, 100000.0)
        self.assertLessEqual(res.quantity * 100000.0, 1_000_000.0 + 100000.0)

    def test_duplicate_action_blocked(self):
        ex = TradeExecutor(dry_run=True)
        ex.execute("005930", "KOSPI", "SELL", 10, 100000.0)
        res2 = ex.execute("005930", "KOSPI", "SELL", 10, 100000.0)
        self.assertFalse(res2.executed)
        self.assertIn("duplicate", res2.message)

    def test_invalid_quantity(self):
        ex = TradeExecutor(dry_run=True)
        res = ex.execute("005930", "KOSPI", "BUY", 0, 100000.0)
        self.assertFalse(res.executed)

    def test_oms_recorded(self):
        from src.core.order_management import OrderManagementSystem
        oms = OrderManagementSystem()
        ex = TradeExecutor(dry_run=True, oms=oms)
        ex.execute("AAPL", "SP500", "BUY", 5, 150.0, reason="test")
        self.assertEqual(len(oms.orders), 1)
        order = list(oms.orders.values())[0]
        self.assertEqual(order.symbol, "AAPL")
        self.assertEqual(order.filled_quantity, 5)


if __name__ == "__main__":
    unittest.main()
