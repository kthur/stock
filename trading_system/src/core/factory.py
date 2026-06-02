from src.data_layer import MarketDataHandler, NLPEngine
from src.core import (
    PortfolioManager,
    HybridStrategyEngine,
    OptimizationEngine,
    OrderManagementSystem,
)
from src.persistence import TradeLogger, AssetHistoryDB
from src.risk import RiskManager
from src.analysis import BacktestEngine, AdvancedStatistics
from src.utils import ErrorHandler, EventBus
from src.broker import KiwoomConnector, MultiBrokerManager
from src.strategy import InvestorStrategyEngine
from src.ai import LLMEngine

class SystemFactory:
    """시스템 컴포넌트 생성 및 주입 담당"""
    @staticmethod
    def create_default_components(initial_cash: float, event_bus: EventBus = None):
        if event_bus is None:
            event_bus = EventBus()
            
        strategy_engine = HybridStrategyEngine(event_bus=event_bus)
        portfolio = PortfolioManager(initial_cash=initial_cash)
        
        return {
            'event_bus': event_bus,
            'market_data': MarketDataHandler(event_bus=event_bus),
            'nlp': NLPEngine(event_bus=event_bus),
            'portfolio': portfolio,
            'account_sync': None, # 계좌 동기화는 포트폴리오 의존적이라 나중에 연결
            'strategy': strategy_engine,
            'optimization': OptimizationEngine(strategy_engine),
            'order_mgmt': OrderManagementSystem(event_bus=event_bus),
            'logger': TradeLogger(),
            'db': AssetHistoryDB(),
            'risk': RiskManager(portfolio_value=initial_cash),
            'backtest': BacktestEngine(initial_capital=initial_cash),
            'stats': AdvancedStatistics(),
            'error_handler': ErrorHandler(max_retries=3),
            'broker': KiwoomConnector(),
            'multi_broker': MultiBrokerManager(),
            'investor_strategy': InvestorStrategyEngine(),
            'llm': LLMEngine(),
            'dashboard': None, # 대시보드는 시스템 인스턴스에 의존적이므로 나중에 연결
            'telegram': None   # 텔레봇도 시스템 인스턴스 의존적
        }
