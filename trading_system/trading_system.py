"""메인 트레이딩 시스템 통합"""

import logging
from datetime import datetime
from typing import Dict, List
import sys
import asyncio
from pathlib import Path

# 프로젝트 경로 추가
sys.path.insert(0, str(Path(__file__).parent))

from src.data_layer import MarketDataHandler, NLPEngine
from src.core import (
    PortfolioManager,
    AccountSyncAgent,
    HybridStrategyEngine,
    OptimizationEngine,
    OrderManagementSystem,
    OrderType,
    TradeSignal
)
from src.persistence import TradeLogger, AssetHistoryDB
from src.risk import RiskManager
from src.analysis import BacktestEngine, AdvancedStatistics
from src.web import WebDashboard
from src.utils import ErrorHandler, ErrorSeverity
from src.broker import KiwoomConnector, MultiBrokerManager, BrokerType
from src.strategy import InvestorStrategyEngine
from src.ai import LLMEngine
from src.telegram_bot import TelegramBotEngine
from src.config import TradingConfig
from src.core.factory import SystemFactory

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class StockTradingSystem:
    """메인 주식 트레이딩 시스템"""
    
    def __init__(self, initial_cash: float = 1000000, config: TradingConfig = None, components: Dict = None):
        """
        시스템 초기화
        
        Args:
            initial_cash: 초기 자본금 (기존 호환성 유지)
            config: 시스템 설정
            components: 주입될 컴포넌트 딕셔너리
        """
        if config is None:
            config = TradingConfig(initial_cash=initial_cash)
        self.config = config
        
        self.comp = components or SystemFactory.create_default_components(self.config.initial_cash)
        # 컴포넌트 매핑
        self.market_data_handler = self.comp['market_data']
        self.nlp_engine = self.comp['nlp']
        self.portfolio = self.comp['portfolio']
        self.account_sync = AccountSyncAgent(self.portfolio) # Factory에서 생성할 수도 있음
        self.strategy_engine = self.comp['strategy']
        self.optimization_engine = self.comp['optimization']
        self.order_management = self.comp['order_mgmt']
        self.trade_logger = self.comp['logger']
        self.asset_history = self.comp['db']
        self.risk_manager = self.comp['risk']
        self.backtest_engine = self.comp['backtest']
        self.statistics = self.comp['stats']
        self.error_handler = self.comp['error_handler']
        self.broker = self.comp['broker']
        self.multi_broker_manager = self.comp['multi_broker']
        self.investor_strategy_engine = self.comp['investor_strategy']
        self.llm_engine = self.comp['llm']
        
        # 시스템 인스턴스 의존성 설정
        self.dashboard = WebDashboard(self)
        self.telegram_bot = TelegramBotEngine(trading_system=self)
        
        # 시스템 상태
        self.market_data_cache: Dict = {}
        self.news_sentiment_cache: Dict = {}
        self.ai_opinions_cache: Dict = {}  # AI 의견 캐시
        self.investor_opinions_cache: Dict = {}  # 투자자 의견 캐시
        
        logger.info(f"Trading system initialized with ${self.config.initial_cash:,}")
        
        # 콜백 등록
        self._setup_callbacks()
    
    def _setup_callbacks(self):
        """콜백 등록"""
        # 시장 데이터 업데이트 시
        self.market_data_handler.subscribe(self._on_market_data)
        
        # 뉴스 분석 결과
        self.nlp_engine.subscribe(self._on_news_analyzed)
        
        # 전략 신호
        self.strategy_engine.subscribe(self._on_strategy_signal)
        
        # 자산 동기화
        self.account_sync.subscribe(self._on_account_synced)
        
        # 주문 상태 변경
        self.order_management.subscribe(self._on_order_status_changed)
    
    def _on_market_data(self, market_data):
        """시장 데이터 콜백"""
        self.market_data_cache[market_data.symbol] = {
            'price': market_data.price,
            'bid': market_data.bid,
            'ask': market_data.ask,
            'volume': market_data.volume
        }
        logger.debug(f"Market data cached: {market_data.symbol}")
    
    def _on_news_analyzed(self, news):
        """뉴스 분석 콜백"""
        self.news_sentiment_cache[news.symbol] = news.score
        logger.info(f"News analyzed: {news.symbol} - sentiment={news.score:.2f}")
    
    def _on_strategy_signal(self, result):
        """전략 신호 콜백"""
        logger.info(f"Strategy signal: {result.symbol} - {result.signal.name} (confidence={result.confidence:.2f})")
        
        # 자동 주문 생성
        if result.signal == TradeSignal.BUY:
            self._create_and_submit_order(result.symbol, OrderType.BUY, result.price)
        elif result.signal == TradeSignal.SELL:
            self._create_and_submit_order(result.symbol, OrderType.SELL, result.price)
    
    def _on_account_synced(self, sync_result):
        """자산 동기화 콜백"""
        logger.info(f"Account synced: cash_diff={sync_result['cash_diff']}")
    
    def _on_order_status_changed(self, order):
        """주문 상태 변경 콜백"""
        logger.info(f"Order status changed: {order.order_id} - {order.status.value}")
        self.trade_logger.log_order(order)
    
    def _create_and_submit_order(self, symbol: str, order_type: OrderType, price: float):
        """주문 생성 및 제출"""
        # 수량 결정 (간단한 예제)
        quantity = 10
        
        order = self.order_management.create_order(symbol, order_type, quantity, price)
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.order_management.submit_order(order))
        except RuntimeError:
            asyncio.run(self.order_management.submit_order(order))
        
        logger.info(f"Order created and submitted: {order.order_id}")
    
    async def simulate_trading_day(self, symbol: str = "AAPL"):
        """하루 거래 시뮬레이션"""
        logger.info(f"=== Simulating trading day for {symbol} ===")
        
        # 1. 뉴스 처리
        news_results = []
        news_texts = [
            ("AAPL 신제품 발표 성공적", "애플의 새로운 제품이 시장 호응 얻음", "긍정적"),
            ("시장 약세 우려", "글로벌 경제 둔화 신호", "부정적"),
            ("AAPL 실적 호조", "3분기 수익 상승", "긍정적")
        ]
        
        for title, content, _ in news_texts:
            result = self.nlp_engine.process_news(title, content, symbol)
            news_results.append(result)
        
        # 평균 감정 점수
        avg_sentiment = sum(r.score for r in news_results) / len(news_results)
        self.news_sentiment_cache[symbol] = avg_sentiment
        
        # 2. 시장 데이터 시뮬레이션
        market_prices = [
            (150.00, 149.95, 150.05, 5000000),
            (150.50, 150.45, 150.55, 6000000),
            (151.00, 150.95, 151.05, 7000000),
        ]
        
        for price, bid, ask, volume in market_prices:
            self.market_data_handler.simulate_api_call(symbol, price, bid, ask, volume)
            
            # 3. 전략 분석
            market_data = self.market_data_cache.get(symbol, {})
            sentiment = self.news_sentiment_cache.get(symbol, 0)
            
            if market_data:
                result = self.strategy_engine.analyze(symbol, market_data, sentiment)
                
                # 주문 실행 시뮬레이션
                if result.signal in [TradeSignal.BUY, TradeSignal.SELL]:
                    await self._simulate_order_execution()
        
        # 4. 자산 스냅샷
        snapshot = self.portfolio.take_snapshot()
        self.asset_history.save_snapshot(snapshot.cash, snapshot.total_value, snapshot.holdings)
        
        # 5. 미체결 주문 감시
        self.order_management.monitor_unfilled_orders()
        
        # 6. 성과 분석
        self._print_performance_report()
    
    async def _simulate_order_execution(self):
        """주문 실행 시뮬레이션"""
        unfilled = self.order_management.get_unfilled_orders()
        if unfilled:
            for order in unfilled[:1]:  # 첫 번째 미체결 주문만 체결
                await self.order_management.execute_order(order.order_id)
                self.trade_logger.log_execution(
                    order.order_id,
                    order.symbol,
                    order.quantity,
                    order.price
                )
                
                # 포트폴리오 업데이트
                if order.order_type == OrderType.BUY:
                    self.portfolio.add_position(order.symbol, order.quantity, order.price)
                else:
                    self.portfolio.reduce_position(order.symbol, order.quantity)
    
    def _print_performance_report(self):
        """성과 보고서 출력"""
        logger.info("=== Performance Report ===")
        logger.info(f"Portfolio Cash: ${self.portfolio.get_available_cash():,.2f}")
        logger.info(f"Positions: {len(self.portfolio.positions)}")
        logger.info(f"Total Orders: {len(self.order_management.orders)}")
        logger.info(f"Win Rate: {self.optimization_engine.get_win_rate():.2%}")
        logger.info(f"Avg Slippage: {self.optimization_engine.get_avg_slippage():.4f}")
    
    def get_risk_report(self) -> Dict:
        """위험 보고서 조회"""
        positions_qty = {s: p.quantity for s, p in self.portfolio.positions.items()}
        metrics = self.risk_manager.generate_risk_report(
            positions_qty,
            self.market_data_cache
        )
        return {
            'current_value': metrics.current_value,
            'drawdown': f"{metrics.current_drawdown:.2%}",
            'risk_level': metrics.risk_level.value,
            'volatility': f"{metrics.portfolio_volatility:.2%}",
            'max_loss_limit': metrics.max_loss_limit
        }
    
    def connect_broker(self, account_number: str) -> bool:
        """증권사 연결"""
        return self.broker.connect(account_number)
    
    def disconnect_broker(self):
        """증권사 연결 해제"""
        self.broker.disconnect()
    
    def get_broker_status(self) -> Dict:
        """증권사 연결 상태"""
        return self.broker.get_connection_status()
    
    def sync_with_broker_api(self) -> bool:
        """증권사 API를 통해 계좌 동기화"""
        try:
            balance = self.broker.get_account_balance()
            holdings = self.broker.get_holdings()
            
            if balance and holdings:
                self.sync_with_broker(balance.get('cash', 0), holdings)
                return True
            return False
        
        except Exception as e:
            logger.error(f"Failed to sync with broker: {str(e)}")
            return False
    
    def start_dashboard(self, port: int = 5000, debug: bool = False):
        """웹 대시보드 시작"""
        logger.info(f"Starting dashboard on http://localhost:{port}")
        self.dashboard.run(debug=debug)
    
    def get_performance_metrics(self, equity_curve: List[float]) -> Dict:
        """성과 지표 계산"""
        returns = self.statistics.calculate_returns(equity_curve)
        
        summary = self.statistics.get_performance_summary(
            equity_curve,
            [{'pnl': 0}]  # 간단한 거래 정보
        )
        
        return summary
    
    def run_backtest(self, symbol: str, price_bars: List, strategy_func) -> Dict:
        """백테스트 실행"""
        result = self.backtest_engine.run_backtest(symbol, price_bars, strategy_func)
        
        return {
            'symbol': result.symbol,
            'total_return': f"{result.total_return_pct:.2f}%",
            'trades': len(result.trades),
            'win_rate': f"{result.win_rate:.2%}",
            'max_drawdown': f"{result.max_drawdown:.2%}",
            'sharpe_ratio': f"{result.sharpe_ratio:.2f}"
        }
    
    def get_error_summary(self) -> Dict:
        """에러 요약"""
        return self.error_handler.get_error_summary()
    
    def sync_with_broker(self, broker_cash: float, broker_holdings: Dict[str, int]):
        """증권사 계좌와 동기화"""
        logger.info("Syncing with broker...")
        result = self.account_sync.sync_with_broker(broker_cash, broker_holdings)
        logger.info(f"Sync completed: {result}")
    
    def get_trading_status(self) -> Dict:
        """거래 상태 조회"""
        return {
            'cash': self.portfolio.get_available_cash(),
            'positions': {s: p.quantity for s, p in self.portfolio.positions.items()},
            'open_orders': len(self.order_management.get_unfilled_orders()),
            'total_trades': len(self.order_management.orders),
            'timestamp': datetime.now().isoformat()
        }
    
    # ===== 유명인 전략 기능 =====
    
    def get_famous_investor_signals(self, stock_data: Dict) -> Dict:
        """유명인 전략 신호 조회"""
        symbol = stock_data.get('symbol', 'UNKNOWN')
        
        # 모든 투자자 전략으로 분석
        opinions = self.investor_strategy_engine.analyze_all_strategies(stock_data)
        self.investor_opinions_cache[symbol] = opinions
        
        logger.info(f"Generated investor signals for {symbol}")
        return opinions
    
    def get_investor_consensus(self, stock_data: Dict) -> Dict:
        """유명인들의 합의 의견"""
        return self.investor_strategy_engine.get_consensus_recommendation(stock_data)
    
    def get_top_recommendation_stocks(self, stocks_data: List[Dict], 
                                     top_n: int = 10) -> List[Dict]:
        """상위 추천주 조회 (유명인 전략 기반)"""
        return self.investor_strategy_engine.get_top_recommendations(stocks_data, top_n)
    
    # ===== AI/LLM 기능 =====
    
    def get_ai_investment_opinion(self, stock_data: Dict) -> Dict:
        """AI 투자 의견 조회"""
        symbol = stock_data.get('symbol', 'UNKNOWN')
        
        opinion = self.llm_engine.query_investment_opinion(stock_data)
        self.ai_opinions_cache[symbol] = opinion
        
        logger.info(f"AI opinion for {symbol}: {opinion.recommendation}")
        
        return {
            'symbol': opinion.symbol,
            'recommendation': opinion.recommendation,
            'sentiment': opinion.sentiment.value,
            'confidence': opinion.confidence,
            'target_price': opinion.target_price,
            'reasoning': opinion.reasoning,
            'risks': opinion.risks,
            'opportunities': opinion.opportunities,
            'timestamp': opinion.timestamp.isoformat()
        }
    
    def get_consensus_with_ai(self, stock_data: Dict) -> Dict:
        """AI와 투자자 의견의 합의"""
        symbol = stock_data.get('symbol', 'UNKNOWN')
        
        # 투자자 의견
        investor_opinions = self.investor_strategy_engine.analyze_all_strategies(stock_data)
        
        # AI와 합의
        consensus = self.llm_engine.get_consensus_with_ai(stock_data, investor_opinions)
        
        logger.info(f"Consensus for {symbol}: {consensus['consensus']}")
        
        return consensus
    
    def batch_ai_analysis(self, stocks_data: List[Dict]) -> Dict[str, Dict]:
        """여러 주식에 대한 배치 AI 분석"""
        return self.llm_engine.batch_query_stocks(stocks_data)
    
    # ===== 다중 증권사 기능 =====
    
    def connect_to_broker(self, broker_type: str, account_number: str) -> bool:
        """특정 증권사에 연결"""
        try:
            broker_enum = BrokerType[broker_type.upper()]
            result = self.multi_broker_manager.connect(broker_enum, account_number)
            
            if result:
                logger.info(f"Connected to {broker_type}: {account_number}")
            
            return result
        except KeyError:
            logger.error(f"Unknown broker type: {broker_type}")
            return False
    
    def disconnect_from_broker(self, broker_type: str) -> bool:
        """증권사 연결 해제"""
        try:
            broker_enum = BrokerType[broker_type.upper()]
            return self.multi_broker_manager.disconnect(broker_enum)
        except KeyError:
            return False
    
    def switch_broker(self, broker_type: str) -> bool:
        """사용 중인 증권사 전환"""
        try:
            broker_enum = BrokerType[broker_type.upper()]
            return self.multi_broker_manager.switch_broker(broker_enum)
        except KeyError:
            return False
    
    def place_order_with_broker(self, code: str, quantity: int, price: float,
                               order_type: str, broker_type: str = None) -> str:
        """증권사를 통해 주문"""
        if broker_type:
            try:
                broker_enum = BrokerType[broker_type.upper()]
            except KeyError:
                logger.error(f"Unknown broker type: {broker_type}")
                return ""
        else:
            broker_enum = None
        
        return self.multi_broker_manager.place_order(code, quantity, price, order_type, broker_enum)
    
    def get_broker_account_info(self, broker_type: str = None) -> Dict:
        """증권사 계좌 정보 조회"""
        if broker_type:
            try:
                broker_enum = BrokerType[broker_type.upper()]
                return self.multi_broker_manager.get_account_info(broker_enum)
            except KeyError:
                return {}
        else:
            # 모든 증권사 정보
            return self.multi_broker_manager.get_all_account_info()
    
    def get_all_broker_status(self) -> Dict:
        """모든 증권사 상태 조회"""
        return self.multi_broker_manager.get_broker_status()
    
    def get_stock_quote_from_broker(self, code: str, broker_type: str = None) -> Dict:
        """증권사에서 주식 시세 조회"""
        if broker_type:
            try:
                broker_enum = BrokerType[broker_type.upper()]
                return self.multi_broker_manager.get_stock_quote(code, broker_enum)
            except KeyError:
                return {}
        else:
            return self.multi_broker_manager.get_stock_quote(code)
    
    def get_chart_from_broker(self, code: str, days: int = 20,
                             broker_type: str = None) -> List[Dict]:
        """증권사에서 차트 조회"""
        if broker_type:
            try:
                broker_enum = BrokerType[broker_type.upper()]
                return self.multi_broker_manager.get_daily_chart(code, days, broker_enum)
            except KeyError:
                return []
        else:
            return self.multi_broker_manager.get_daily_chart(code, days)
    
    # ===== 텔레그램 봇 기능 =====
    
    def start_telegram_bot(self):
        """텔레그램 봇 시작"""
        self.telegram_bot.start()
        logger.info("Telegram bot started")
    
    def stop_telegram_bot(self):
        """텔레그램 봇 중지"""
        self.telegram_bot.stop()
        logger.info("Telegram bot stopped")
    
    def process_telegram_message(self, user_id: int, message: str) -> str:
        """텔레그램 메시지 처리"""
        return self.telegram_bot.process_message(user_id, message)
    
    def get_telegram_bot_stats(self) -> Dict:
        """텔레그램 봇 통계"""
        return self.telegram_bot.get_stats()
    
    def send_telegram_notification(self, user_id: int, event_type: str, data: Dict) -> str:
        """텔레그램 알림 전송"""
        return self.telegram_bot.get_notification(event_type, data)
    
    def get_telegram_daily_report(self, user_id: int) -> str:
        """텔레그램 일일 보고서"""
        return self.telegram_bot.send_periodic_report(user_id)

