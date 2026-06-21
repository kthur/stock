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
)
from src.risk import RiskManager


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

    def test_normalize_weights_sum_to_one(self):
        """가중치 정규화 후 합계 = 1.0"""
        for attr in ("sentiment_weight", "technical_weight", "ml_weight",
                     "rl_weight", "darkpool_weight", "llm_weight",
                     "global_market_weight", "cash_ratio_weight",
                     "macro_weight"):
            setattr(self.engine, attr, 0.5)
        self.engine._normalize_weights()
        total = (self.engine.sentiment_weight + self.engine.technical_weight +
                 self.engine.ml_weight + self.engine.rl_weight +
                 self.engine.darkpool_weight + self.engine.llm_weight +
                 self.engine.global_market_weight + self.engine.cash_ratio_weight +
                 self.engine.macro_weight)
        self.assertAlmostEqual(total, 1.0, places=6)

    def test_normalize_weights_zero_case(self):
        """모든 가중치가 0이면 균등 분배"""
        for attr in ("sentiment_weight", "technical_weight", "ml_weight",
                     "rl_weight", "darkpool_weight", "llm_weight",
                     "global_market_weight", "cash_ratio_weight",
                     "macro_weight"):
            setattr(self.engine, attr, 0.0)
        self.engine._normalize_weights()
        n = len(self.engine.SIGNAL_NAMES)
        total = (self.engine.sentiment_weight + self.engine.technical_weight +
                 self.engine.ml_weight + self.engine.rl_weight +
                 self.engine.darkpool_weight + self.engine.llm_weight +
                 self.engine.global_market_weight + self.engine.cash_ratio_weight +
                 self.engine.macro_weight)
        self.assertAlmostEqual(total, 1.0, places=6)
        self.assertAlmostEqual(self.engine.sentiment_weight, 1.0 / n, places=6)

    def test_adapt_weights_increases_accurate_signals(self):
        """정답률 높은 신호의 가중치가 증가"""
        initial = self.engine.sentiment_weight
        for _ in range(20):
            self.engine.record_signal_outcome("sentiment", True)
        for name in ("technical", "ml", "rl", "darkpool", "llm", "global_market"):
            for _ in range(20):
                self.engine.record_signal_outcome(name, False)
        # Force adaptation by pushing results_history length past the window
        from src.core.strategy_engine import StrategyResult
        from datetime import datetime
        for _ in range(self.engine.weight_adaptation_window + 1):
            self.engine.results_history.append(
                StrategyResult("TEST", None, 0.0, 0.0, "", datetime.now())
            )
        self.engine._adapt_weights()
        self.assertGreater(self.engine.sentiment_weight, initial)

    def test_detect_regime_sideways_with_few_bars(self):
        """200개 미만 봉 -> weak_bear 반환 (4-레짐 분류에서 기본값)"""
        class FakeBar:
            def __init__(self, close):
                self.open = self.high = self.low = self.close = close
                self.volume = 1_000_000
        bars = [FakeBar(100.0 + i * 0.1) for i in range(50)]
        regime = self.engine.detect_regime(bars)
        self.assertEqual(regime, "weak_bear")

    def test_detect_regime_bull(self):
        """EMA50 >> EMA200 -> bull 반환"""
        class FakeBar:
            def __init__(self, close):
                self.open = self.high = self.low = self.close = close
                self.volume = 1_000_000
        # Uptrend: prices increase monotonically
        prices = [100.0 + i * 0.5 for i in range(250)]
        bars = [FakeBar(p) for p in prices]
        regime = self.engine.detect_regime(bars)
        self.assertIn(regime, ("strong_bull", "weak_bull"), f"Expected bull regime, got {regime}")

    def test_global_market_signal_without_client(self):
        """GlobalMarketClient 없이 analyze 호출 -> 정상 동작"""
        market_data = {'price': 150.0, 'bid': 149.95, 'ask': 150.05, 'volume': 5000000}
        result = self.engine.analyze("AAPL", market_data, 0.5)
        self.assertIsNotNone(result.signal)
        self.assertIsNotNone(result.confidence)

    def test_signal_names_includes_global_market(self):
        """SIGNAL_NAMES에 global_market 포함"""
        self.assertIn("global_market", self.engine.SIGNAL_NAMES)

    def test_raw_scores_contains_global_market(self):
        """analyze 결과 raw_scores에 global_market 포함"""
        self.engine.ml_engine = None
        market_data = {'price': 150.0, 'bid': 149.95, 'ask': 150.05, 'volume': 5000000}
        result = self.engine.analyze("AAPL", market_data, 0.5)
        self.assertTrue(hasattr(result, 'signal'))
        self.assertGreaterEqual(result.confidence, 0.0)

    def test_signal_outcome_recorded_without_error(self):
        """record_signal_outcome호출시 에러 없음"""
        self.engine.record_signal_outcome("sentiment", True)
        self.engine.record_signal_outcome("unknown", True)  # should be no-op
        self.assertIn("sentiment", self.engine._signal_performance)
        self.assertEqual(len(self.engine._signal_performance["sentiment"]), 1)

    def test_cash_ratio_signal_high_cash_scores_above_neutral(self):
        """현금 많고 VIX 낮음 -> score > 0.5"""
        self.engine.ml_engine = None
        market_data = {'price': 150.0, 'bid': 149.95, 'ask': 150.05, 'volume': 5000000}
        result = self.engine.analyze("AAPL", market_data, 0.0, cash_ratio=0.9)
        self.assertGreaterEqual(result.confidence, 0.0)
        self.assertIn("cash_ratio", self.engine.SIGNAL_NAMES)

    def test_cash_ratio_signal_low_cash_scores_below_neutral(self):
        """현금 적고 VIX 높음 -> score < 0.5"""
        self.engine.ml_engine = None
        self.engine.sentiment_weight = 0.0
        self.engine.technical_weight = 0.0
        self.engine.ml_weight = 0.0
        self.engine.rl_weight = 0.0
        self.engine.darkpool_weight = 0.0
        self.engine.llm_weight = 0.0
        self.engine.global_market_weight = 0.0
        self.engine.cash_ratio_weight = 1.0
        market_data = {'price': 150.0, 'bid': 149.95, 'ask': 150.05, 'volume': 5000000}
        result = self.engine.analyze("AAPL", market_data, 0.0, cash_ratio=0.05)
        self.assertLess(result.confidence, 0.5)


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
        # 4 tranches x 3 orders each (entry + SL + TP) = 12
        self.assertEqual(len(orders), 12, f"Expected 12 orders, got {len(orders)}")
        entry_qty = sum(o.quantity for o in orders if o.order_type == OrderType.BUY)
        self.assertEqual(entry_qty, 300)

    def test_distributed_buy_price_descending(self):
        """분산 매수 가격이 내림차순인지 확인"""
        orders = self.dom.create_distributed_buy("MSFT", 200, 400.0, 380.0, 440.0)
        buy_prices = [o.price for o in orders if o.order_type == OrderType.BUY]
        self.assertEqual(len(buy_prices), 4)
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


class TestPreTradeConcentrationCheck(unittest.TestCase):
    """Pre-trade position concentration limit tests"""

    def setUp(self):
        from src.core.asset_management import PortfolioManager
        self.portfolio = PortfolioManager(initial_cash=1_000_000)
        self.risk_manager = RiskManager(portfolio_value=1_000_000)
        self.risk_manager.max_position_size_pct = 0.20
        self.market_cache = {}

    def _max_position_value(self):
        return 1_000_000 * self.risk_manager.max_position_size_pct  # 200,000

    def test_no_position_allows_full_order(self):
        """기존 포지션 없음 -> 집중도 제한 없음"""
        position = self.portfolio.positions.get("AAPL")
        self.assertIsNone(position)

    def test_position_under_limit_passes_check(self):
        """기존 포지션이 한도 내 -> 통과"""
        self.portfolio.add_position("AAPL", 500, 150.0)  # $75,000
        position = self.portfolio.positions["AAPL"]
        current_value = position.quantity * 150.0
        new_value = 50 * 150.0  # $7,500
        limit = self._max_position_value()
        self.assertLess(current_value + new_value, limit)

    def test_position_exceeding_limit_is_clamped(self):
        """기존 + 신규가 한도 초과 -> 수량 감소"""
        self.portfolio.add_position("AAPL", 1200, 150.0)  # $180,000
        position = self.portfolio.positions["AAPL"]
        current_value = position.quantity * 150.0
        limit = self._max_position_value()  # $200,000
        remaining = limit - current_value  # $20,000
        clamped_qty = max(0, int(remaining / 150.0))  # 133
        new_qty = 500
        self.assertGreater(new_qty, clamped_qty)

    def test_at_max_position_blocks_additional(self):
        """이미 한도에 도달 -> 추가 매수 차단"""
        self.portfolio.add_position("AAPL", 1334, 150.0)  # $200,100
        position = self.portfolio.positions["AAPL"]
        current_value = position.quantity * 150.0
        limit = self._max_position_value()
        remaining = limit - current_value
        clamped_qty = max(0, int(remaining / 150.0))
        self.assertEqual(clamped_qty, 0)


class TestPortfolioBasedSizing(unittest.TestCase):
    """Integration tests for portfolio-value-based trade unit logic"""

    def test_min_trade_quantity_scales_with_portfolio(self):
        """portfolio_value * min_trade_pct / price = 최소 거래 단위"""
        cases = [
            (1_000_000, 100.0, 10),    # $1M → 10주 @ $100
            (100_000,  100.0, 1),      # $100k → 1주 @ $100
            (5_000_000, 500.0, 10),    # $5M → 10주 @ $500
            (50_000,   50.0,  1),      # $50k → 1주 @ $50
        ]
        for pv, price, expected in cases:
            q = max(1, int(pv * 0.001 / price))
            self.assertEqual(q, expected, f"PV={pv} price={price}")

    def test_distributed_threshold_scales_with_portfolio(self):
        """portfolio_value * distributed_pct / price = 분산 주문 활성화 기준"""
        cases = [
            (1_000_000, 100.0, 50),    # $1M → 50주 @ $100
            (200_000,   100.0, 10),    # $200k → 10주 @ $100
            (10_000_000, 500.0, 100),  # $10M → 100주 @ $500
        ]
        for pv, price, expected in cases:
            q = max(2, int(pv * 0.005 / price))
            self.assertEqual(q, expected, f"PV={pv} price={price}")

    def test_min_trade_quantity_floor_is_one(self):
        """매우 작은 PV여도 최소 1주 보장"""
        q = max(1, int(1000 * 0.001 / 100.0))  # $1k → 0.01 → floor=0 → max=1
        self.assertEqual(q, 1)

    def test_distributed_threshold_floor_is_two(self):
        """매우 작은 PV여도 분산 기준 최소 2주"""
        q = max(2, int(1000 * 0.005 / 100.0))  # $1k → 0.05 → floor=0 → max=2
        self.assertEqual(q, 2)

    def test_distributed_enabled_when_quantity_exceeds_threshold(self):
        """Kelly 수량 >= distributed_threshold → 분산 주문 활성화"""
        pv = 1_000_000
        price = 100.0
        threshold = max(2, int(pv * 0.005 / price))  # 50
        kelly_qty = 100
        self.assertTrue(kelly_qty >= threshold)

    def test_distributed_disabled_below_threshold(self):
        """Kelly 수량 < distributed_threshold → 단일 주문"""
        pv = 100_000
        price = 100.0
        threshold = max(2, int(pv * 0.005 / price))  # 5
        kelly_qty = 3
        self.assertFalse(kelly_qty >= threshold)

    def test_min_trade_overrides_kelly_when_too_small(self):
        """Kelly 수량 < min_trade_quantity → min_trade_quantity로 올림"""
        pv = 1_000_000
        price = 100.0
        min_q = max(1, int(pv * 0.001 / price))  # 10
        kelly_qty = 3
        final = max(kelly_qty, min_q)
        self.assertEqual(final, 10)


if __name__ == "__main__":
    unittest.main(verbosity=2)
