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
    DistributedOrderManager,
    DistributedOrderConfig,
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


class TestGlobalMarketClient(unittest.TestCase):
    """GlobalMarketClient 단위 테스트"""

    def setUp(self):
        from src.data_layer.global_market import GlobalMarketClient, GLOBAL_INDICES, FX_PAIRS
        self.GlobalMarketClient = GlobalMarketClient
        self.GLOBAL_INDICES = GLOBAL_INDICES
        self.FX_PAIRS = FX_PAIRS

    def test_indices_defined(self):
        """글로벌 지수 13개가 정의되어 있는지 확인"""
        self.assertGreaterEqual(len(self.GLOBAL_INDICES), 13)

    def test_fx_pairs_defined(self):
        """환율 6개가 정의되어 있는지 확인"""
        self.assertGreaterEqual(len(self.FX_PAIRS), 6)

    def test_guess_region_us(self):
        from src.analysis.relative_strength import _guess_region
        self.assertEqual(_guess_region("AAPL"), "US")
        self.assertEqual(_guess_region("MSFT"), "US")

    def test_guess_region_kr(self):
        from src.analysis.relative_strength import _guess_region
        self.assertEqual(_guess_region("005930.KS"), "KR")
        self.assertEqual(_guess_region("000660.KQ"), "KR")

    def test_guess_region_jp(self):
        from src.analysis.relative_strength import _guess_region
        self.assertEqual(_guess_region("7203.T"), "JP")


class TestRelativeStrengthAnalyzer(unittest.TestCase):
    """RelativeStrengthAnalyzer 단위 테스트 (순수 계산)"""

    def setUp(self):
        from src.analysis import RelativeStrengthAnalyzer
        self.analyzer = RelativeStrengthAnalyzer()

    def test_compute_metrics_high_correlation(self):
        """완전히 동일한 수익률 -> 상관계수=1, 베타=1, 알파=0"""
        import numpy as np
        returns = np.array([0.01, 0.02, -0.01, 0.005, -0.005, 0.015])
        result = self.analyzer.compute_metrics("TEST", returns, returns)
        self.assertAlmostEqual(result["correlation"], 1.0, places=5)
        self.assertAlmostEqual(result["beta"], 1.0, places=5)
        self.assertAlmostEqual(result["alpha"], 0.0, places=5)

    def test_compute_metrics_low_correlation(self):
        """서로 다른 랜덤 수익률 -> 상관·베타는 0에 가까움"""
        import numpy as np
        np.random.seed(42)
        stock_r = np.random.randn(50) * 0.01
        bench_r = np.random.randn(50) * 0.01
        result = self.analyzer.compute_metrics("RND", stock_r, bench_r)
        self.assertLess(abs(result["correlation"]), 0.3)
        self.assertLess(abs(result["beta"]), 0.3)

    def test_compute_metrics_outperformance(self):
        """stock이 benchmark를 일관되게 초과 -> 양의 alpha"""
        import numpy as np
        br = np.array([0.001, 0.002, -0.001, 0.003, 0.001, -0.002, 0.002, 0.001])
        sr = br + 0.001  # +10bp daily outperformance
        result = self.analyzer.compute_metrics("ALPHA", sr, br, risk_free_rate=0.03)
        self.assertGreater(result["alpha"], 0.0)
        self.assertGreater(result["correlation"], 0.5)

    def test_compute_metrics_insufficient_data(self):
        """데이터가 5개 미만 -> 0 반환"""
        import numpy as np
        result = self.analyzer.compute_metrics("SHORT", np.array([0.01, 0.02]), np.array([0.01, 0.02]))
        self.assertEqual(result["n"], 0)

    def test_compute_metrics_from_histories(self):
        """가격 히스토리로부터 올바른 메트릭 계산"""
        stock_prices = [100, 102, 101, 105, 107, 106, 110]
        bench_prices = [100, 101, 100.5, 102, 103, 102.5, 104]
        result = self.analyzer.compute_metrics_from_histories("TEST", stock_prices, bench_prices)
        self.assertIn("correlation", result)
        self.assertGreater(result["n"], 0)

    def test_score_symbol_without_handler(self):
        """MarketDataHandler 없으면 에러 딕셔너리 반환"""
        result = self.analyzer.score_symbol("AAPL")
        self.assertIn("error", result)


class TestDistributedOrderManager(unittest.TestCase):
    """DistributedOrderManager 단위 테스트"""

    def setUp(self):
        self.oms = OrderManagementSystem()
        self.dom = DistributedOrderManager(self.oms)

    def test_distributed_buy_creates_tranches(self):
        """분산 매수 -> N개의 진입 + N개의 SL + N개의 TP 주문 생성"""
        orders = self.dom.create_distributed_buy("AAPL", 300, 150.0, 142.0, 165.0)
        # 3 tranches x 3 orders each (entry + SL + TP) = 9
        self.assertEqual(len(orders), 9, f"Expected 9 orders, got {len(orders)}")
        entry_qty = sum(o.quantity for o in orders if o.order_type == OrderType.BUY)
        self.assertEqual(entry_qty, 300)

    def test_distributed_buy_price_descending(self):
        """분산 매수 가격이 내림차순인지 확인"""
        orders = self.dom.create_distributed_buy("MSFT", 200, 400.0, 380.0, 440.0)
        buy_prices = [o.price for o in orders if o.order_type == OrderType.BUY]
        self.assertEqual(len(buy_prices), 3)
        for i in range(len(buy_prices) - 1):
            self.assertGreaterEqual(buy_prices[i], buy_prices[i + 1])

    def test_distributed_sell_creates_tranches(self):
        """분산 매도 -> N개의 진입 + SL + TP 주문 생성"""
        orders = self.dom.create_distributed_sell("AAPL", 150, 150.0, 142.0, 165.0)
        self.assertEqual(len(orders), 9)
        sell_qty = sum(o.quantity for o in orders if o.order_type == OrderType.SELL)
        self.assertEqual(sell_qty, 150)

    def test_distributed_sell_price_ascending(self):
        """분산 매도 가격이 오름차순인지 확인"""
        orders = self.dom.create_distributed_sell("GOOGL", 100, 2000.0, 1900.0, 2200.0)
        sell_prices = [o.price for o in orders if o.order_type == OrderType.SELL]
        self.assertEqual(len(sell_prices), 3)
        for i in range(len(sell_prices) - 1):
            self.assertLessEqual(sell_prices[i], sell_prices[i + 1])

    def test_zero_quantity_returns_empty(self):
        """수량 0 -> 빈 리스트 반환"""
        orders = self.dom.create_distributed_buy("AAPL", 0, 150.0, 142.0, 165.0)
        self.assertEqual(len(orders), 0)

    def test_tiny_quantity_single_tranche(self):
        """소량(1주) -> 적어도 하나의 트렌치 생성"""
        orders = self.dom.create_distributed_buy("AAPL", 1, 150.0, 142.0, 165.0)
        buy_orders = [o for o in orders if o.order_type == OrderType.BUY]
        self.assertGreaterEqual(len(buy_orders), 1)
        total = sum(o.quantity for o in buy_orders)
        self.assertEqual(total, 1)

    def test_cancel_all_for_symbol(self):
        """cancel_all_for_symbol -> 해당 심볼의 진행중 주문 취소"""
        self.dom.create_distributed_buy("AAPL", 300, 150.0, 142.0, 165.0)
        self.dom.create_distributed_buy("MSFT", 100, 400.0, 380.0, 440.0)
        cancelled = self.dom.cancel_all_for_symbol("AAPL")
        self.assertGreater(cancelled, 0)
        remaining_aapl = [o for o in self.oms.orders.values()
                          if o.symbol == "AAPL" and o.status.value in ("PENDING", "SUBMITTED")]
        self.assertEqual(len(remaining_aapl), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
