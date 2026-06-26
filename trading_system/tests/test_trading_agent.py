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
from src.risk.risk_manager import RiskManager
from src.utils.notifier import NotificationSystem
from src.data_layer.trade_journal import TradeJournal, TradeRecord
from src.ai.trading_agent import TradingAgent
from src.ai.news_sentiment_fetcher import NewsSentimentFetcher

class MockNotifier(NotificationSystem):
    def __init__(self):
        super().__init__()
        self.broadcast = AsyncMock()
        self.send_telegram = AsyncMock()
        self.send_discord = AsyncMock()

class TestTradingAgent(unittest.TestCase):

    def setUp(self):
        # Create temp folder for test databases
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_market_indicators.db")
        self.stock_db_path = os.path.join(self.temp_dir, "test_stock_prices.db")
        self.log_db_path = os.path.join(self.temp_dir, "test_trade_logs.db")
        
        # Initialize databases with dummy schema
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS global_indicators (
                date TEXT,
                symbol TEXT,
                name TEXT,
                price REAL,
                change_pct REAL,
                PRIMARY KEY (date, symbol)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS stock_universe (
                symbol TEXT PRIMARY KEY,
                name TEXT,
                market TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ensemble_predictions (
                date TEXT,
                symbol TEXT,
                ensemble_score REAL,
                ensemble_expected_return REAL,
                reg_score REAL,
                surge_score REAL,
                ll_score REAL,
                vcp_ml_score REAL,
                PRIMARY KEY (date, symbol)
            )
        """)
        # Insert dummy stock universe and predictions
        conn.execute("INSERT OR REPLACE INTO stock_universe VALUES ('005930', '삼성전자', 'KOSPI')")
        conn.execute("INSERT OR REPLACE INTO stock_universe VALUES ('AAPL', 'Apple', 'SP500')")
        conn.execute("INSERT OR REPLACE INTO global_indicators VALUES ('2026-06-26', '^KS11', 'KOSPI', 2700.0, 0.01)")
        conn.execute("INSERT OR REPLACE INTO global_indicators VALUES ('2026-06-26', '^VIX', 'VIX', 15.0, 0.0)")
        conn.execute("INSERT OR REPLACE INTO ensemble_predictions VALUES ('2026-06-26', '005930', 0.85, 0.12, 0.8, 0.9, 0.7, 0.8)")
        conn.commit()
        conn.close()

        # Stock Price DB
        conn = sqlite3.connect(self.stock_db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS stock_prices (
                symbol TEXT,
                date TEXT,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume INTEGER,
                updated_at TEXT,
                PRIMARY KEY (symbol, date)
            )
        """)
        conn.execute("INSERT OR REPLACE INTO stock_prices VALUES ('005930', '2026-06-26', 80000.0, 81000.0, 79000.0, 80000.0, 1000000, '2026-06-26')")
        conn.commit()
        conn.close()

        # Config setup
        self.config = TradingConfig()
        self.config.db_path = self.db_path
        self.config.stock_price_db_path = self.stock_db_path
        self.config.initial_cash = 100_000_000.0
        
        # Mocks & Journal
        self.broker = RealBroker()
        self.broker.connect()
        self.broker.submit_order = MagicMock(side_effect=self.broker.submit_order)
        
        self.risk_manager = RiskManager(portfolio_value=100_000_000.0)
        self.notifier = MockNotifier()
        self.trade_journal = TradeJournal(db_path=self.log_db_path)
        
        self.news_fetcher = MagicMock(spec=NewsSentimentFetcher)
        # Default neutral sentiment
        self.news_fetcher.fetch_and_analyze.return_value = 0.1

        self.agent = TradingAgent(
            config=self.config,
            broker=self.broker,
            risk_manager=self.risk_manager,
            notifier=self.notifier,
            trade_journal=self.trade_journal,
            news_fetcher=self.news_fetcher
        )

    def tearDown(self):
        import gc
        gc.collect()
        try:
            shutil.rmtree(self.temp_dir)
        except Exception:
            pass

    def test_rule_1_risk_limit_downsize(self):
        """Rule 1: 단일 거래 위험 노출액이 자본의 2% 이하인지 검증 및 수량 축소 테스트"""
        # 1억원 자본금 기준 2% = 200만원 리스크 감당 가능
        # 주가 10만원, 손절선 5만원 -> 주당 리스크 5만원. 
        # 최대 수량 = 200만원 / 5만원 = 40주 제한되어야 함.
        qty = 100 # 원래 매매 희망 수량 100주
        safe_qty = self.agent._validate_risk_limit(
            symbol="TEST",
            qty=qty,
            price=100000.0,
            stop_price=50000.0,
            total_capital=100_000_000.0
        )
        self.assertEqual(safe_qty, 40)

    def test_rule_2_sentiment_block(self):
        """Rule 2: 부정적인 뉴스 감성 발생 시 매수 차단 테스트"""
        self.news_fetcher.fetch_and_analyze.return_value = -0.5 # 부정적 감성 (-0.2 미만)
        
        # 신규 매수 신호 처리 실행
        asyncio.run(self.agent._process_new_signals())
        
        # broker.submit_order()가 호출되지 않았어야 함 (부정적 감성으로 차단)
        self.broker.submit_order.assert_not_called()

    def test_rule_3_no_statistical_edge(self):
        """Rule 3: 통계적 우위가 없을 때 매수 차단 테스트"""
        # 0승 5패인 Journal 기록 삽입 -> win_rate = 0%
        for i in range(5):
            self.trade_journal.log_trade(TradeRecord(
                timestamp="2026-06-26 12:00:00",
                symbol="TEST",
                side="SELL",
                quantity=10,
                price=1000.0,
                pnl=-1000.0
            ))
            
        asyncio.run(self.agent._process_new_signals())
        self.broker.submit_order.assert_not_called()

    def test_rule_4_report_generation(self):
        """Rule 4: 매매 전 판단 근거 보고서 생성 확인 테스트"""
        report = self.agent._generate_trade_report(
            symbol="005930",
            qty=10,
            price=80000.0,
            signal_type="BUY",
            sentiment=0.35,
            vix=15.0,
            edge=0.08,
            decision="EXECUTE",
            reason="High ensemble score"
        )
        self.assertIn("005930", report)
        self.assertIn("80,000", report)
        self.assertIn("0.3500", report)
        self.assertIn("EXECUTE", report)

    def test_rule_5_emergency_protocol(self):
        """Rule 5: 당일 변동성 5% 이상 발생 시 미체결 취소 및 보유 주식 전량 매도 (비상 대응) 테스트"""
        # 먼저 주식 매수해서 포지션을 보유하도록 구성
        self.trade_journal.log_trade(TradeRecord(
            timestamp="2026-06-26 09:00:00",
            symbol="005930",
            side="BUY",
            quantity=50,
            price=80000.0,
            stop_loss=76000.0,
            take_profit=92000.0
        ))
        
        # 시장 변동성 지표를 5.5%로 업데이트 (비상 조건 충족)
        conn = sqlite3.connect(self.db_path)
        conn.execute("INSERT OR REPLACE INTO global_indicators VALUES ('2026-06-26', '^KS11', 'KOSPI', 2700.0, 0.055)")
        conn.commit()
        conn.close()

        # 비상 대응 작동 실행
        triggered = asyncio.run(self.agent._emergency_protocol())
        
        self.assertTrue(triggered)
        # SELL 주문이 브로커로 제출되었는지 확인
        self.broker.submit_order.assert_called_with("005930", 50, "SELL")
        
        # 포지션이 완전히 정산되어 active position이 없어야 함
        active_pos = self.trade_journal.get_active_positions()
        self.assertNotIn("005930", active_pos)

    def test_position_management_stop_loss(self):
        """보유 주식이 손절선 이하로 하락 시 Stop-Loss 자동 매도 테스트"""
        # 005930 주식을 8만원에 매수, 손절선 76,000원 설정
        self.trade_journal.log_trade(TradeRecord(
            timestamp="2026-06-26 09:00:00",
            symbol="005930",
            side="BUY",
            quantity=10,
            price=80000.0,
            stop_loss=76000.0,
            take_profit=92000.0
        ))
        
        # 현재 주가를 75,000원으로 낮게 강제 설정
        conn = sqlite3.connect(self.stock_db_path)
        conn.execute("INSERT OR REPLACE INTO stock_prices VALUES ('005930', '2026-06-26', 80000.0, 81000.0, 74000.0, 75000.0, 1000000, '2026-06-26 12:00:00')")
        conn.commit()
        conn.close()

        # 포지션 관리 로직 실행
        asyncio.run(self.agent._manage_existing_positions())
        
        # 손절 주문 실행 여부 검증
        self.broker.submit_order.assert_called_with("005930", 10, "SELL")
        
        # DB의 active position이 삭제되었는지 확인
        active_pos = self.trade_journal.get_active_positions()
        self.assertNotIn("005930", active_pos)

    def test_position_management_take_profit(self):
        """보유 주식이 익절선 이상으로 상승 시 Take-Profit 자동 매도 테스트"""
        # 005930 주식을 8만원에 매수, 익절선 90,000원 설정
        self.trade_journal.log_trade(TradeRecord(
            timestamp="2026-06-26 09:00:00",
            symbol="005930",
            side="BUY",
            quantity=10,
            price=80000.0,
            stop_loss=76000.0,
            take_profit=90000.0
        ))
        
        # 현재 주가를 91,000원으로 높게 설정
        conn = sqlite3.connect(self.stock_db_path)
        conn.execute("INSERT OR REPLACE INTO stock_prices VALUES ('005930', '2026-06-26', 80000.0, 92000.0, 80000.0, 91000.0, 1000000, '2026-06-26 12:00:00')")
        conn.commit()
        conn.close()

        # 포지션 관리 로직 실행
        asyncio.run(self.agent._manage_existing_positions())
        
        # 익절 매도 주문 실행 여부 검증
        self.broker.submit_order.assert_called_with("005930", 10, "SELL")
        
        # DB의 active position이 삭제되었는지 확인
        active_pos = self.trade_journal.get_active_positions()
        self.assertNotIn("005930", active_pos)

if __name__ == "__main__":
    unittest.main()
