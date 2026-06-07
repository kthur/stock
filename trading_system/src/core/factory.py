from src.data_layer import MarketDataHandler, NLPEngine, GlobalMarketClient
from src.core import (
    PortfolioManager,
    HybridStrategyEngine,
    OptimizationEngine,
    OrderManagementSystem,
)
from src.persistence import TradeLogger, AssetHistoryDB, AIPredictionDB
from src.risk import RiskManager
from src.analysis import BacktestEngine, AdvancedStatistics, RelativeStrengthAnalyzer
from src.utils import ErrorHandler, EventBus
from src.broker import KiwoomConnector, MultiBrokerManager
from src.strategy import InvestorStrategyEngine
from src.ai import LLMEngine
from src.core.asset_management import AccountSyncAgent


class SystemFactory:
    @staticmethod
    def create_default_components(initial_cash: float, event_bus: EventBus | None = None):
        if event_bus is None:
            event_bus = EventBus()

        market_data = MarketDataHandler(event_bus=event_bus)

        global_market = GlobalMarketClient()
        rsa = RelativeStrengthAnalyzer(
            market_data_handler=market_data,
            global_market=global_market,
        )

        strategy_engine = HybridStrategyEngine(
            event_bus=event_bus,
            global_market=global_market,
            relative_strength=rsa,
            global_market_weight=0.10,
        )
        portfolio = PortfolioManager(initial_cash=initial_cash)
        return {
            'event_bus': event_bus,
            'market_data': market_data,
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
            'global_market': global_market,
            'relative_strength': rsa,
        }
