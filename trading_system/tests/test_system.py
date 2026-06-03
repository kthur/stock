import sys
import unittest
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data_layer import MarketDataHandler, NLPEngine, Sentiment
from src.core import (
    PortfolioManager,
    AccountSyncAgent,
    HybridStrategyEngine,
    OrderManagementSystem,
    OrderType,
    TradeSignal
)


class TestMarketDataHandler(unittest.TestCase):
    """시장 데이터 핸들러 테스트"""
    
    def setUp(self):
        self.handler = MarketDataHandler()
    
    def test_simulate_api_call(self):
        """API 호출 시뮬레이션"""
        data = self.handler.simulate_api_call("AAPL", 150.0, 149.95, 150.05, 5000000)
        
        self.assertEqual(data.symbol, "AAPL")
        self.assertEqual(data.price, 150.0)
        self.assertEqual(data.volume, 5000000)
    
    def test_get_market_data(self):
        """시장 데이터 조회"""
        self.handler.simulate_api_call("AAPL", 150.0, 149.95, 150.05, 5000000)
        data = self.handler.get_market_data("AAPL")
        
        self.assertIsNotNone(data)
        self.assertEqual(data.symbol, "AAPL")


class TestNLPEngine(unittest.TestCase):
    """NLP 엔진 테스트"""
    
    def setUp(self):
        self.engine = NLPEngine()
    
    def test_positive_sentiment(self):
        """긍정 감정 분석"""
        sentiment, score = self.engine.analyze_sentiment("애플 상승장 긍정적 뉴스")
        self.assertEqual(sentiment, Sentiment.POSITIVE)
        self.assertGreater(score, 0)
    
    def test_negative_sentiment(self):
        """부정 감정 분석"""
        sentiment, score = self.engine.analyze_sentiment("시장 하락 악재 소식")
        self.assertEqual(sentiment, Sentiment.NEGATIVE)
        self.assertLess(score, 0)
    
    def test_process_news(self):
        """뉴스 처리"""
        news = self.engine.process_news(
            title="AAPL 신제품 성공",
            content="새로운 제품 긍정적 반응",
            symbol="AAPL"
        )
        
        self.assertEqual(news.symbol, "AAPL")
        self.assertIsNotNone(news.sentiment)


class TestPortfolioManager(unittest.TestCase):
    """포트폴리오 관리자 테스트"""
    
    def setUp(self):
        self.portfolio = PortfolioManager(initial_cash=100000)
    
    def test_initial_cash(self):
        """초기 현금"""
        self.assertEqual(self.portfolio.get_available_cash(), 100000)
    
    def test_add_position(self):
        """포지션 추가"""
        self.portfolio.add_position("AAPL", 10, 150.0)
        
        self.assertEqual(len(self.portfolio.positions), 1)
        self.assertEqual(self.portfolio.positions["AAPL"].quantity, 10)
    
    def test_reduce_position(self):
        """포지션 감소"""
        self.portfolio.add_position("AAPL", 10, 150.0)
        self.portfolio.reduce_position("AAPL", 5)
        
        self.assertEqual(self.portfolio.positions["AAPL"].quantity, 5)
    
    def test_deposit_withdraw(self):
        """입금/출금"""
        self.portfolio.deposit(50000)
        self.assertEqual(self.portfolio.get_available_cash(), 150000)
        
        self.portfolio.withdraw(30000)
        self.assertEqual(self.portfolio.get_available_cash(), 120000)


class TestAccountSyncAgent(unittest.TestCase):
    """자산 동기화 에이전트 테스트"""
    
    def setUp(self):
        self.portfolio = PortfolioManager(initial_cash=100000)
        self.sync_agent = AccountSyncAgent(self.portfolio)
    
    def test_sync_with_broker(self):
        """증권사 동기화"""
        result = self.sync_agent.sync_with_broker(
            broker_cash=95000,
            broker_holdings={"AAPL": 10}
        )
        
        self.assertEqual(result['cash_diff'], -5000)
        self.assertIn('AAPL', result['holdings_diff'])


class TestOrderManagementSystem(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        cls.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(cls.loop)
    
    @classmethod
    def tearDownClass(cls):
        cls.loop.close()
    
    def setUp(self):
        self.oms = OrderManagementSystem()
    
    def _run_async(self, coro):
        return self.loop.run_until_complete(coro)
    
    def test_create_order(self):
        order = self.oms.create_order("AAPL", OrderType.BUY, 10, 150.0)
        self.assertEqual(order.symbol, "AAPL")
        self.assertEqual(order.quantity, 10)
    
    def test_submit_order(self):
        order = self.oms.create_order("AAPL", OrderType.BUY, 10, 150.0)
        result = self._run_async(self.oms.submit_order(order))
        self.assertTrue(result)
    
    def test_execute_order(self):
        order = self.oms.create_order("AAPL", OrderType.BUY, 10, 150.0)
        self._run_async(self.oms.submit_order(order))
        self._run_async(self.oms.execute_order(order.order_id, 10))
        self.assertEqual(order.filled_quantity, 10)
    
    def test_cancel_order(self):
        order = self.oms.create_order("AAPL", OrderType.BUY, 10, 150.0)
        self._run_async(self.oms.submit_order(order))
        result = self._run_async(self.oms.cancel_order(order.order_id))
        self.assertTrue(result)


class TestStrategyEngine(unittest.TestCase):
    """전략 엔진 테스트"""
    
    def setUp(self):
        self.engine = HybridStrategyEngine()
    
    def test_analyze_strong_buy(self):
        """강력한 매수 신호"""
        market_data = {
            'price': 150.0,
            'bid': 149.95,
            'ask': 150.05,
            'volume': 5000000
        }
        result = self.engine.analyze(
            symbol="AAPL",
            market_data=market_data,
            news_sentiment=0.8
        )
        
        self.assertIsNotNone(result.signal)


if __name__ == "__main__":
    unittest.main(verbosity=2)
