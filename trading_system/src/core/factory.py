from src.data_layer import MarketDataHandler, NLPEngine
from src.core import (
    PortfolioManager,
    HybridStrategyEngine,
    OptimizationEngine,
    OrderManagementSystem,
)
from src.persistence import TradeLogger, AssetHistoryDB, AIPredictionDB
from src.risk import RiskManager
from src.analysis import BacktestEngine, AdvancedStatistics
from src.utils import ErrorHandler, EventBus
from src.broker import KiwoomConnector, MultiBrokerManager
from src.strategy import InvestorStrategyEngine
from src.ai import LLMEngine
from src.core.asset_management import AccountSyncAgent
from src.analysis.ml_engine import MLEngine
from src.analysis.rl_engine import RLEngine
from src.data_layer.alt_data import AlternativeDataClient
from src.data_layer.darkpool_tracker import DarkPoolTracker
from src.ai.llm_earnings_agent import LLMEarningsAgent
from src.ai.llm_integration import LLMEngine
from src.core.stat_arb import StatisticalArbitrageEngine
from src.utils.notifier import NotificationSystem
from dotenv import load_dotenv
import os

class SystemFactory:
    """시스템 컴포넌트 생성 및 주입 담당"""
    @staticmethod
    def create_default_components(initial_cash: float, event_bus: EventBus | None = None):
        # 환경 변수 로드
        load_dotenv(override=True)
        
        if event_bus is None:
            event_bus = EventBus()
            
        ml_engine = MLEngine()
        rl_engine = RLEngine()
        alt_client = AlternativeDataClient()
        darkpool = DarkPoolTracker()
        llm_earnings = LLMEarningsAgent(llm_engine=LLMEngine())
        stat_arb = StatisticalArbitrageEngine()
        
        strategy_engine = HybridStrategyEngine(
            event_bus=event_bus, 
            ml_engine=ml_engine,
            rl_engine=rl_engine,
            alt_client=alt_client,
            darkpool=darkpool,
            llm_earnings=llm_earnings,
            stat_arb=stat_arb
        )
        portfolio = PortfolioManager(initial_cash=initial_cash)
        notifier = NotificationSystem()

        return {
            'event_bus': event_bus,
            'market_data': MarketDataHandler(event_bus=event_bus),
            'nlp': NLPEngine(event_bus=event_bus),
            'portfolio': portfolio,
            'account_sync': AccountSyncAgent(portfolio, event_bus=event_bus),
            'strategy': strategy_engine,
            'optimization': OptimizationEngine(strategy_engine),
            'order_mgmt': OrderManagementSystem(event_bus=event_bus),
            'logger': TradeLogger(),
            'db': AssetHistoryDB(),
            'ai_db': AIPredictionDB(),
            'risk': RiskManager(portfolio_value=initial_cash),
            'backtest': BacktestEngine(initial_capital=initial_cash),
            'stats': AdvancedStatistics(),
            'error_handler': ErrorHandler(max_retries=3),
            'broker': KiwoomConnector(),
            'multi_broker': MultiBrokerManager(),
            'investor_strategy': InvestorStrategyEngine(),
            'llm': LLMEngine(),
            'ml_engine': MLEngine(),
            'notifier': notifier,
        }
