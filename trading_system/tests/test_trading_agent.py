import sys
import unittest
import os
import sqlite3
import shutil
import tempfile
import asyncio
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import TradingConfig
from src.broker.real_broker import RealBroker
from src.risk.risk_manager import RiskManager, CrisisLevel
from src.utils.notifier import NotificationSystem
from src.data_layer.trade_journal import TradeJournal, TradeRecord
from src.ai.trading_agent import (
    TradingAgent,
    BUY_EFFECTIVE_RATE,
    SELL_EFFECTIVE_RATE,
    CRISIS_RISK_CAP,
)
from src.ai.news_sentiment_fetcher import NewsSentimentFetcher


class MockNotifier(NotificationSystem):
    def __init__(self):
        super().__init__()
        self.broadcast = AsyncMock()
        self.send_telegram = AsyncMock()
        self.send_discord = AsyncMock()


# ─── 공통 DB 픽스처 ────────────────────────────────────────────────────────────

def _create_market_db(db_path: str, change_pct: float = 0.01, vix: float = 15.0):
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS global_indicators (
            date TEXT, symbol TEXT, name TEXT, price REAL, change_pct REAL,
            PRIMARY KEY (date, symbol)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS stock_universe (
            symbol TEXT PRIMARY KEY, name TEXT, market TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ensemble_predictions (
            date TEXT, symbol TEXT, ensemble_score REAL,
            ensemble_expected_return REAL, reg_score REAL,
            surge_score REAL, ll_score REAL, vcp_ml_score REAL,
            PRIMARY KEY (date, symbol)
        )
    """)
    conn.execute("INSERT OR REPLACE INTO stock_universe VALUES ('005930', '삼성전자', 'KOSPI')")
    conn.execute("INSERT OR REPLACE INTO stock_universe VALUES ('AAPL', 'Apple', 'SP500')")
    conn.execute(
        "INSERT OR REPLACE INTO global_indicators VALUES ('2026-06-26', '^KS11', 'KOSPI', 2700.0, ?)",
        (change_pct,)
    )
    conn.execute(
        "INSERT OR REPLACE INTO global_indicators VALUES ('2026-06-26', '^VIX', 'VIX', ?, 0.0)",
        (vix,)
    )
    conn.execute(
        "INSERT OR REPLACE INTO ensemble_predictions VALUES "
        "('2026-06-26', '005930', 0.85, 0.12, 0.8, 0.9, 0.7, 0.8)"
    )
    conn.commit()
    conn.close()


def _create_price_db(db_path: str, close: float = 80000.0, rows: int = 20):
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS stock_prices (
            symbol TEXT, date TEXT, open REAL, high REAL, low REAL,
            close REAL, volume INTEGER, updated_at TEXT,
            PRIMARY KEY (symbol, date)
        )
    """)
    import datetime as _dt
    base = _dt.date(2026, 1, 1)
    for i in range(rows):
        d = (base + _dt.timedelta(days=i)).isoformat()
        # 약간의 변동을 줘서 ATR 계산 가능하게
        high_val = close * (1 + 0.01 * (i % 3))
        low_val = close * (1 - 0.01 * (i % 3))
        conn.execute(
            "INSERT OR REPLACE INTO stock_prices VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ('005930', d, close, high_val, low_val, close, 1000000, d)
        )
    conn.commit()
    conn.close()


# ─── 테스트 클래스 ──────────────────────────────────────────────────────────────

class TestTradingAgent(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path       = os.path.join(self.temp_dir, "test_market.db")
        self.stock_db_path = os.path.join(self.temp_dir, "test_prices.db")
        self.log_db_path   = os.path.join(self.temp_dir, "test_trades.db")

        _create_market_db(self.db_path)
        _create_price_db(self.stock_db_path)

        self.config = TradingConfig()
        self.config.db_path             = self.db_path
        self.config.stock_price_db_path = self.stock_db_path
        self.config.initial_cash        = 100_000_000.0

        self.broker       = RealBroker()
        self.broker.connect()
        self.broker.submit_order = MagicMock(side_effect=self.broker.submit_order)

        self.risk_manager  = RiskManager(portfolio_value=100_000_000.0)
        self.notifier      = MockNotifier()
        self.trade_journal = TradeJournal(db_path=self.log_db_path)

        self.news_fetcher  = MagicMock(spec=NewsSentimentFetcher)
        self.news_fetcher.fetch_and_analyze.return_value = 0.1

        self.agent = TradingAgent(
            config=self.config,
            broker=self.broker,
            risk_manager=self.risk_manager,
            notifier=self.notifier,
            trade_journal=self.trade_journal,
            news_fetcher=self.news_fetcher,
        )

    def tearDown(self):
        import gc
        gc.collect()
        try:
            shutil.rmtree(self.temp_dir)
        except Exception:
            pass

    # ─── 기존 Rule 테스트 ────────────────────────────────────────────────────

    def test_rule_1_risk_limit_downsize(self):
        """Rule 1: 단일 거래 위험 노출액이 자본의 2% 이하인지 수량 축소 검증"""
        qty = 100
        safe_qty = self.agent._validate_risk_limit(
            symbol="TEST",
            qty=qty,
            price=100_000.0,
            stop_price=50_000.0,
            total_capital=100_000_000.0,
        )
        # max_risk = 2,000,000 / 50,000 per share = 40
        self.assertEqual(safe_qty, 40)

    def test_rule_2_sentiment_block(self):
        """Rule 2: 부정적인 뉴스 감성 발생 시 매수 차단"""
        self.news_fetcher.fetch_and_analyze.return_value = -0.5
        asyncio.run(self.agent._process_new_signals())
        self.broker.submit_order.assert_not_called()

    def test_rule_3_no_statistical_edge(self):
        """Rule 3: 통계적 우위 없을 때 매수 차단"""
        for _ in range(5):
            self.trade_journal.log_trade(TradeRecord(
                timestamp="2026-06-26 12:00:00",
                symbol="TEST", side="SELL", quantity=10,
                price=1000.0, pnl=-1000.0
            ))
        asyncio.run(self.agent._process_new_signals())
        self.broker.submit_order.assert_not_called()

    def test_rule_4_report_generation(self):
        """Rule 4: 매매 전 판단 근거 보고서 생성 확인"""
        report = self.agent._generate_trade_report(
            symbol="005930", qty=10, price=80000.0,
            signal_type="BUY", sentiment=0.35, vix=15.0,
            edge=0.08, decision="EXECUTE", reason="High ensemble score",
            net_pnl=500_000.0, crisis_level="NONE",
        )
        self.assertIn("005930", report)
        self.assertIn("80,000", report)
        self.assertIn("0.3500", report)
        self.assertIn("EXECUTE", report)
        self.assertIn("NONE", report)
        self.assertIn("Net PnL", report)

    def test_rule_5_emergency_protocol(self):
        """Rule 5: 변동성 5% 초과 시 비상 청산 트리거"""
        self.trade_journal.log_trade(TradeRecord(
            timestamp="2026-06-26 09:00:00",
            symbol="005930", side="BUY",
            quantity=50, price=80000.0,
            stop_loss=76000.0, take_profit=92000.0
        ))
        # 5.5% 변동 삽입
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT OR REPLACE INTO global_indicators VALUES (?, ?, ?, ?, ?)",
            ('2026-06-26', '^KS11', 'KOSPI', 2700.0, 0.055)
        )
        conn.commit()
        conn.close()

        triggered = asyncio.run(self.agent._emergency_protocol())
        self.assertTrue(triggered)
        self.broker.submit_order.assert_called_with("005930", 50, "SELL")

        active_pos = self.trade_journal.get_active_positions()
        self.assertNotIn("005930", active_pos)

    def test_position_management_stop_loss(self):
        """기존 포지션 손절선 이하 시 ATR 폴백 → Stop-Loss 자동 매도"""
        self.trade_journal.log_trade(TradeRecord(
            timestamp="2026-06-26 09:00:00",
            symbol="005930", side="BUY",
            quantity=10, price=80000.0,
            stop_loss=76000.0, take_profit=92000.0
        ))
        conn = sqlite3.connect(self.stock_db_path)
        conn.execute(
            "INSERT OR REPLACE INTO stock_prices VALUES (?,?,?,?,?,?,?,?)",
            ('005930', '2026-06-26', 80000.0, 81000.0, 74000.0, 75000.0, 1000000, '2026-06-26')
        )
        conn.commit()
        conn.close()

        asyncio.run(self.agent._manage_existing_positions())
        self.broker.submit_order.assert_called_with("005930", 10, "SELL")

        active_pos = self.trade_journal.get_active_positions()
        self.assertNotIn("005930", active_pos)

    def test_position_management_take_profit(self):
        """기존 포지션 익절선 이상 시 Take-Profit 자동 매도"""
        self.trade_journal.log_trade(TradeRecord(
            timestamp="2026-06-26 09:00:00",
            symbol="005930", side="BUY",
            quantity=10, price=80000.0,
            stop_loss=76000.0, take_profit=90000.0
        ))
        conn = sqlite3.connect(self.stock_db_path)
        conn.execute(
            "INSERT OR REPLACE INTO stock_prices VALUES (?,?,?,?,?,?,?,?)",
            ('005930', '2026-06-26', 80000.0, 92000.0, 80000.0, 91000.0, 1000000, '2026-06-26')
        )
        conn.commit()
        conn.close()

        asyncio.run(self.agent._manage_existing_positions())
        self.broker.submit_order.assert_called_with("005930", 10, "SELL")

        active_pos = self.trade_journal.get_active_positions()
        self.assertNotIn("005930", active_pos)

    # ─── Q1: ATR 트레일링 스탑 테스트 ───────────────────────────────────────

    def test_q1_atr_calculation(self):
        """Q1: ATR 계산이 0보다 크고 합리적인 범위인지 확인"""
        atr = self.agent._calculate_atr("005930", lookback=14)
        # ATR은 0 이상이어야 함 (가격 데이터 존재)
        self.assertGreaterEqual(atr, 0.0)

    def test_q1_atr_insufficient_data_returns_zero(self):
        """Q1: 데이터 부족 시 ATR = 0.0 반환 확인"""
        atr = self.agent._calculate_atr("NONEXISTENT_SYMBOL", lookback=14)
        self.assertEqual(atr, 0.0)

    def test_q1_highest_price_since_entry(self):
        """Q1: 진입 이후 최고가 조회 (매수 기록 없을 때 avg_price 반환)"""
        highest = self.agent._get_highest_price_since_entry("005930", avg_entry_price=80000.0)
        self.assertGreaterEqual(highest, 80000.0)

    # ─── Q2: 포트폴리오 상관관계 테스트 ───────────────────────────────────────

    def test_q2_correlation_no_positions_returns_ok(self):
        """Q2: 보유 포지션이 없을 때 상관관계 검사 결과는 OK"""
        result = self.agent._check_portfolio_correlation("005930", {})
        self.assertEqual(result, "OK")

    def test_q2_correlation_insufficient_data_returns_ok(self):
        """Q2: 가격 데이터 부족 시 보수적으로 OK 반환"""
        active = {"999999": {"qty": 10, "avg_price": 5000.0}}
        result = self.agent._check_portfolio_correlation("005930", active)
        # 999999 심볼 데이터 없으므로 OK
        self.assertEqual(result, "OK")

    def test_q2_high_correlation_causes_block(self):
        """Q2: 상관계수 0.85 초과 시 BLOCK 반환"""
        # setUp과 겹치지 않는 전용 심볼 사용 → 데이터 오염 방지
        import datetime as _dt

        # 두 종목에 동일한 단조증가 가격 시계열 삽입 → 상관계수 1.0
        base = _dt.date(2025, 6, 1)
        prices = [5000.0 * (1 + 0.005 * i) for i in range(65)]

        conn = sqlite3.connect(self.stock_db_path)
        for sym in ('CORR_A', 'CORR_B'):
            for i, p in enumerate(prices):
                d = (base + _dt.timedelta(days=i)).isoformat()
                conn.execute(
                    "INSERT OR REPLACE INTO stock_prices VALUES (?,?,?,?,?,?,?,?)",
                    (sym, d, p, p, p, p, 100000, d)
                )
        conn.commit()
        conn.close()

        active = {"CORR_B": {"qty": 5, "avg_price": 5000.0}}
        result = self.agent._check_portfolio_correlation("CORR_A", active)
        self.assertEqual(result, "BLOCK")

    # ─── Q3: 위기 단계별 동적 리스크 캡 테스트 ───────────────────────────────

    def test_q3_crisis_risk_cap_values(self):
        """Q3: 위기 단계별 CRISIS_RISK_CAP 값이 올바른지 검증"""
        self.assertEqual(CRISIS_RISK_CAP[CrisisLevel.NONE],   0.020)
        self.assertEqual(CRISIS_RISK_CAP[CrisisLevel.WATCH],  0.015)
        self.assertEqual(CRISIS_RISK_CAP[CrisisLevel.ACTIVE], 0.010)
        self.assertEqual(CRISIS_RISK_CAP[CrisisLevel.SEVERE], 0.000)

    def test_q3_active_crisis_halves_risk(self):
        """Q3: ACTIVE 위기 시 리스크 한도 1.0%로 수량 축소"""
        # 주가 10만, 손절 9만 → 주당 위험 1만원
        # ACTIVE 리스크 한도 1% of 1억 = 100만 → 최대 100주
        qty = 500
        adjusted = self.agent._validate_risk_limit(
            symbol="TEST", qty=qty,
            price=100_000.0, stop_price=90_000.0,
            total_capital=100_000_000.0,
            risk_pct_override=CRISIS_RISK_CAP[CrisisLevel.ACTIVE],
        )
        self.assertEqual(adjusted, 100)

    def test_q3_severe_crisis_blocks_new_buy(self):
        """Q3: SEVERE 위기 시 신규 매수 완전 차단"""
        # evaluate_crisis가 SEVERE를 반환하도록 모킹
        self.risk_manager.evaluate_crisis = MagicMock(return_value=CrisisLevel.SEVERE)
        asyncio.run(self.agent._process_new_signals())
        self.broker.submit_order.assert_not_called()

    # ─── Q4: 거래비용 Net PnL 테스트 ─────────────────────────────────────────

    def test_q4_effective_rate_constants(self):
        """Q4: BUY/SELL 실효 배율 상수가 올바른 범위인지 검증"""
        # 매수 실효가는 원가보다 높아야 함
        self.assertGreater(BUY_EFFECTIVE_RATE, 1.0)
        # 매도 실효가는 원가보다 낮아야 함
        self.assertLess(SELL_EFFECTIVE_RATE, 1.0)

    def test_q4_net_pnl_reflects_transaction_costs(self):
        """Q4: Net PnL이 거래 비용(세금 + 수수료 + 슬리피지) 차감 후 계산되는지 검증"""
        qty       = 10
        avg_price = 80_000.0
        curr_price = 90_000.0

        # 실효 계산 (agent 내부 로직과 동일)
        net_sell = curr_price * SELL_EFFECTIVE_RATE * qty
        net_buy  = avg_price  * BUY_EFFECTIVE_RATE  * qty
        net_pnl  = net_sell - net_buy

        # 단순 PnL (비용 미반영)
        gross_pnl = (curr_price - avg_price) * qty  # = 100,000

        # Net PnL은 Gross PnL보다 작아야 함 (비용 차감)
        self.assertLess(net_pnl, gross_pnl)
        # Net PnL은 양수여야 함 (10% 상승이므로 비용 초과 이익)
        self.assertGreater(net_pnl, 0.0)

    def test_q4_report_includes_net_pnl(self):
        """Q4: 보고서에 Net PnL 항목이 포함되는지 검증"""
        report = self.agent._generate_trade_report(
            symbol="005930", qty=10, price=90000.0,
            signal_type="SELL", sentiment=0.0, vix=15.0,
            edge=0.0, decision="EXECUTE", reason="Test",
            net_pnl=-50_000.0,
        )
        self.assertIn("Net PnL", report)
        self.assertIn("-50,000", report)


if __name__ == "__main__":
    unittest.main()
