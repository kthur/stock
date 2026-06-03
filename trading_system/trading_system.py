"""메인 트레이딩 시스템 통합 (EventBus 및 DI 구조 개선)"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Callable
import sys
import asyncio
from pathlib import Path
import sqlite3

# 프로젝트 경로 추가
sys.path.insert(0, str(Path(__file__).parent))

from src.data_layer import MarketDataHandler, NLPEngine
from src.data_layer.market_data_handler import MarketData
from src.data_layer.nlp_engine import NewsData
from src.core import (
    PortfolioManager,
    AccountSyncAgent,
    HybridStrategyEngine,
    OptimizationEngine,
    OrderManagementSystem,
    OrderType,
    TradeSignal
)
from src.core.order_management import Order
from src.persistence import TradeLogger, AssetHistoryDB
from src.risk import RiskManager
from src.analysis import BacktestEngine, AdvancedStatistics
from src.web import WebDashboard
from src.utils import ErrorHandler, ErrorSeverity, EventBus
from src.broker import KiwoomConnector, MultiBrokerManager, BrokerType
from src.strategy import InvestorStrategyEngine
from src.ai import LLMEngine
from src.telegram_bot import TelegramBotEngine
from src.config import TradingConfig
from src.core.factory import SystemFactory
from src.core.strategy_engine import StrategyResult
from src.analysis.backtest import PriceBar

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
        
        self.event_bus = components.get('event_bus') if components else EventBus()
        
        # 컴포넌트 설정
        self.comp = components or SystemFactory.create_default_components(self.config.initial_cash, self.event_bus)
        
        # 컴포넌트 매핑
        self.market_data_handler = self.comp['market_data']
        self.nlp_engine = self.comp['nlp']
        self.portfolio = self.comp['portfolio']
        
        # 계좌 동기화 에이전트 생성 시 EventBus 주입
        self.account_sync = self.comp.get('account_sync') or AccountSyncAgent(self.portfolio, event_bus=self.event_bus)
        
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
        
        # 시스템 인스턴스 의존성 설정 (DI 적용 및 EventBus 주입)
        self.dashboard = self.comp.get('dashboard') or WebDashboard(self, event_bus=self.event_bus)
        self.telegram_bot = self.comp.get('telegram') or TelegramBotEngine(trading_system=self, event_bus=self.event_bus)
        
        # 시스템 상태 캐시
        self.market_data_cache: Dict = {}
        self.news_sentiment_cache: Dict = {}
        self.ai_opinions_cache: Dict = {}
        self.investor_opinions_cache: Dict = {}
        
        logger.info(f"Trading system initialized with ${self.config.initial_cash:,}")
        
        # 콜백 등록
        self._setup_callbacks()
    
    def _setup_callbacks(self) -> None:
        """이벤트 버스 콜백 등록"""
        # 시장 데이터 업데이트 시
        self.event_bus.subscribe("market_data", self._on_market_data)
        
        # 뉴스 분석 결과
        self.event_bus.subscribe("news_sentiment", self._on_news_analyzed)
        
        # 전략 신호
        self.event_bus.subscribe("strategy_signal", self._on_strategy_signal)
        
        # 자산 동기화
        self.event_bus.subscribe("account_sync", self._on_account_synced)
        
        # 주문 상태 변경
        self.event_bus.subscribe("order_status", self._on_order_status_changed)
    
    def _on_market_data(self, market_data: MarketData) -> None:
        """시장 데이터 콜백 (동기 처리 캐싱)"""
        self.market_data_cache[market_data.symbol] = {
            'price': market_data.price,
            'bid': market_data.bid,
            'ask': market_data.ask,
            'volume': market_data.volume
        }
        logger.debug(f"Market data cached: {market_data.symbol}")
    
    def _on_news_analyzed(self, news: NewsData) -> None:
        """뉴스 분석 콜백"""
        self.news_sentiment_cache[news.symbol] = news.score
        logger.info(f"News analyzed: {news.symbol} - sentiment={news.score:.2f}")
    
    async def _on_strategy_signal(self, result: StrategyResult) -> None:
        """전략 신호 콜백 (비동기 처리)"""
        logger.info(f"Strategy signal: {result.symbol} - {result.signal.name} (confidence={result.confidence:.2f})")
        
        # 자동 주문 생성
        if result.signal == TradeSignal.BUY:
            await self._create_and_submit_order(result.symbol, OrderType.BUY, result.price)
        elif result.signal == TradeSignal.SELL:
            await self._create_and_submit_order(result.symbol, OrderType.SELL, result.price)
    
    def _on_account_synced(self, sync_result: Dict) -> None:
        """자산 동기화 콜백"""
        logger.info(f"Account synced: cash_diff={sync_result['cash_diff']}")
    
    async def _on_order_status_changed(self, order: Order) -> None:
        """주문 상태 변경 콜백 (비동기 DB 저장 지원)"""
        logger.info(f"Order status changed: {order.order_id} - {order.status.value}")
        await self.trade_logger.log_order(order)
    
    async def _create_and_submit_order(self, symbol: str, order_type: OrderType, price: float) -> None:
        """주문 생성 및 비동기 제출 (동적 포지션 사이징 적용)"""
        if price <= 0:
            logger.warning(f"Invalid price {price} for {symbol}. Order aborted.")
            return
            
        # 포트폴리오 가치의 5% 수준을 투자 규모로 설정
        portfolio_total = self.portfolio.get_portfolio_value(self.market_data_cache.get(symbol, {}))
        if portfolio_total <= 0:
            portfolio_total = self.portfolio.cash
            
        target_value = portfolio_total * 0.05
        quantity = int(target_value / price)
        
        # Max position limit 적용
        max_size = self.risk_manager.calculate_max_position_size(price)
        quantity = min(quantity, max_size)
        
        # 가용 자금 체크 (매수일 때만 조절)
        if order_type == OrderType.BUY:
            available_cash = self.portfolio.cash
            if price * quantity > available_cash:
                quantity = int(available_cash * 0.95 / price)  # 95% 현금 소진
                
        if quantity <= 0:
            logger.warning(f"Calculated quantity is 0 for {symbol} @ price {price}. Order aborted.")
            return
            
        order = self.order_management.create_order(symbol, order_type, quantity, price)
        await self.order_management.submit_order(order)
        logger.info(f"Order dynamically sized and submitted: {order.order_id} ({symbol} x{quantity} @ {price})")

    def _evaluate_active_strategy(self, symbol: str, current_price: float, volume: int) -> TradeSignal:
        """현재 설정된 활성 매매 전략에 따라 매매 신호 평가"""
        strategy_name = getattr(self.risk_manager, 'active_strategy', 'HYBRID').upper()
        
        # 1. 기본 하이브리드 전략
        if strategy_name == 'HYBRID':
            market_data = self.market_data_cache.get(symbol, {})
            sentiment = self.news_sentiment_cache.get(symbol, 0)
            result = self.strategy_engine.analyze(symbol, market_data, sentiment)
            return result.signal
            
        # 2. 기술적 백테스트 기반 전략 실행
        try:
            # 버핏/달리오/추세 등 장기 전략은 1y, 그 외는 1mo 데이터 사용
            period = "1y" if strategy_name in ["BUFFETT", "DALIO", "TREND"] else "1mo"
            bars = self.market_data_handler.fetch_historical_data(symbol, period=period)
            if not bars:
                logger.warning(f"No historical data for {symbol}. Falling back to HOLD.")
                return TradeSignal.HOLD
                
            # 가장 마지막 봉을 현재 가격/거래량 정보로 추가하여 현재 캔들 완성
            current_bar = PriceBar(
                timestamp=datetime.now(),
                open=current_price,
                high=current_price,
                low=current_price,
                close=current_price,
                volume=volume
            )
            bars.append(current_bar)
            
            # 전략 함수 획득 및 분석 실행
            strat_func = self.backtest_engine.get_strategy_func(strategy_name)
            signal_str = strat_func(bars)
            
            # 문자열 신호를 Enum으로 맵핑
            if signal_str == "BUY":
                return TradeSignal.BUY
            elif signal_str == "SELL":
                return TradeSignal.SELL
            else:
                return TradeSignal.HOLD
        except Exception as e:
            logger.error(f"Error evaluating active strategy {strategy_name} for {symbol}: {e}")
            return TradeSignal.HOLD

    async def simulate_trading_day(self, symbol: str = "AAPL") -> None:
        """하루 거래 시뮬레이션"""
        logger.info(f"=== Simulating trading day for {symbol} ===")
        
        # 1. 뉴스 처리
        news_results = []
        news_texts = [
            (f"{symbol} 신제품 발표 성공적", f"{symbol}의 새로운 제품이 시장 호응 얻음", "긍정적"),
            ("시장 약세 우려", "글로벌 경제 둔화 신호", "부정적"),
            (f"{symbol} 실적 호조", f"{symbol} 3분기 수익 상승", "긍정적")
        ]
        
        for title, content, _ in news_texts:
            result = self.nlp_engine.process_news(title, content, symbol)
            news_results.append(result)
        
        # 평균 감정 점수
        avg_sentiment = sum(r.score for r in news_results) / len(news_results)
        self.news_sentiment_cache[symbol] = avg_sentiment
        
        # 2. 시장 데이터 수집 (실시간 데이터 활용)
        try:
            live_data = self.market_data_handler.fetch_live_data(symbol)
        except Exception as e:
            logger.error(f"Failed to fetch live data for {symbol}: {e}")
            live_data = None
            
        if live_data and live_data.price > 0:
            price = live_data.price
            volume = live_data.volume
            # 0.2% 범위의 변동폭을 주어 3번의 틱 생성
            market_prices = [
                (round(price * 0.999, 2), round(price * 0.998, 2), round(price * 0.999, 2), volume),
                (price, round(price - 0.05, 2), round(price + 0.05, 2), volume),
                (round(price * 1.001, 2), round(price * 1.000, 2), round(price * 1.001, 2), volume),
            ]
        else:
            market_prices = [
                (150.00, 149.95, 150.05, 5000000),
                (150.50, 150.45, 150.55, 6000000),
                (151.00, 150.95, 151.05, 7000000),
            ]
            
        for price, bid, ask, volume in market_prices:
            self.market_data_handler.simulate_api_call(symbol, price, bid, ask, volume)
            
            # 3. 전략 분석
            market_data = self.market_data_cache.get(symbol, {})
            
            if market_data:
                # 활성 매매 전략에 따른 분석 신호 생성
                signal = self._evaluate_active_strategy(symbol, price, volume)
                
                # 결과 기록 및 이벤트 발행
                result = StrategyResult(
                    symbol=symbol,
                    signal=signal,
                    price=price,
                    confidence=0.8,
                    reason=f"Active strategy: {getattr(self.risk_manager, 'active_strategy', 'HYBRID')}",
                    timestamp=datetime.now()
                )
                self.strategy_engine.results_history.append(result)
                self.event_bus.publish("strategy_signal", result)
                
                # 주문 실행 시뮬레이션
                if signal in [TradeSignal.BUY, TradeSignal.SELL]:
                    await self._simulate_order_execution()
        
        # 4. 자산 스냅샷
        snapshot = self.portfolio.take_snapshot()
        await self.asset_history.save_snapshot(snapshot.cash, snapshot.total_value, snapshot.holdings)
        
        # 5. 미체결 주문 감시
        self.order_management.monitor_unfilled_orders()
        
        # 6. 성과 분석
        self._print_performance_report()
        
    def reset_system_portfolio(self) -> None:
        """자산 및 시뮬레이션 상태 초기화"""
        logger.info("Resetting trading system portfolio and database logs...")
        
        # 1. 포지션 청산 및 현금 원복
        self.portfolio.positions.clear()
        self.portfolio.cash = self.config.initial_cash
        self.portfolio.asset_history.clear()
        
        # 2. 리스크 매니저 피크 밸류 리셋
        self.risk_manager.portfolio_value = self.config.initial_cash
        self.risk_manager.peak_value = self.config.initial_cash
        self.risk_manager.metrics_history.clear()
        self.risk_manager.alerts.clear()
        
        # 3. 주문 관리자 미체결 주문 및 히스토리 초기화
        self.order_management.orders.clear()
        
        # 4. 캐시 초기화
        self.market_data_cache.clear()
        self.news_sentiment_cache.clear()
        self.ai_opinions_cache.clear()
        self.investor_opinions_cache.clear()
        
        # 5. DB 파일 초기화 (비동기 DB 연결 종료 후 파일 삭제 또는 테이블 DROP)
        for db_name in ["trade_logs.db", "asset_history.db"]:
            try:
                db_path = Path(db_name)
                if db_path.exists():
                    with sqlite3.connect(db_path) as conn:
                        conn.execute("DROP TABLE IF EXISTS orders;")
                        conn.execute("DROP TABLE IF EXISTS executions;")
                        conn.execute("DROP TABLE IF EXISTS asset_snapshots;")
                        conn.commit()
                    logger.info(f"Database tables dropped for {db_name}")
            except Exception as e:
                logger.error(f"Failed to drop tables in {db_name}: {e}")
    
    async def _simulate_order_execution(self) -> None:
        """주문 실행 시뮬레이션"""
        unfilled = self.order_management.get_unfilled_orders()
        if unfilled:
            for order in unfilled[:1]:  # 첫 번째 미체결 주문만 체결
                await self.order_management.execute_order(order.order_id)
                await self.trade_logger.log_execution(
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
    
    def _print_performance_report(self) -> None:
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
    
    def disconnect_broker(self) -> None:
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
    
    def start_dashboard(self, port: int = 5000, debug: bool = False) -> None:
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
    
    def run_backtest(self, symbol: str, price_bars: List, strategy_func: Callable) -> Dict:
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
    
    def sync_with_broker(self, broker_cash: float, broker_holdings: Dict[str, int]) -> None:
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

        # 비동기로 AI 예측 저장
        if hasattr(self, 'comp') and 'ai_db' in self.comp:
            price = stock_data.get('price', 0.0)
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self.comp['ai_db'].log_prediction(opinion, price))
            except RuntimeError:
                pass # 이벤트 루프가 없으면(예: 동기 환경) 스킵

        return {
            'symbol': opinion.symbol,
            'recommendation': opinion.recommendation,
            'sentiment': opinion.sentiment.value,
            'confidence': opinion.confidence,
            'target_price': opinion.target_price,
            'reasoning': opinion.reasoning,
            'risks': opinion.risks,
            'opportunities': opinion.opportunities,
            'timestamp': opinion.timestamp.isoformat(),
            'is_simulated': getattr(opinion, 'is_simulated', False)
        }    
    def get_consensus_with_ai(self, stock_data: Dict, 
                             investor_opinions: Optional[Dict] = None) -> Dict:
        """AI와 투자자 의견의 합의"""
        symbol = stock_data.get('symbol', 'UNKNOWN')
        
        # 투자자 의견이 전달되지 않은 경우에만 새로 생성
        if investor_opinions is None:
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
                               order_type: str, broker_type: Optional[str] = None) -> str:
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
    
    def get_broker_account_info(self, broker_type: Optional[str] = None) -> Dict:
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
    
    def get_stock_quote_from_broker(self, code: str, broker_type: Optional[str] = None) -> Dict:
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
                             broker_type: Optional[str] = None) -> List[Dict]:
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
    
    def start_telegram_bot(self) -> None:
        """텔레그램 봇 시작"""
        self.telegram_bot.start()
        logger.info("Telegram bot started")
    
    def stop_telegram_bot(self) -> None:
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
