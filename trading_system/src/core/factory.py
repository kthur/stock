from src.ai import LLMEngine
from src.analysis import AdvancedStatistics, BacktestEngine, RelativeStrengthAnalyzer
from src.broker import KiwoomConnector, MultiBrokerManager
from src.core import (
    HybridStrategyEngine,
    OptimizationEngine,
    OrderManagementSystem,
    PortfolioManager,
)
from src.core.asset_management import AccountSyncAgent
from src.data_layer import GlobalMarketClient, MarketDataHandler, NLPEngine
from src.persistence import AIPredictionDB, AssetHistoryDB, TradeLogger
from src.risk import RiskManager
from src.strategy import InvestorStrategyEngine
from src.utils import ErrorHandler, EventBus


class SystemFactory:
    @staticmethod
    def create_default_components(initial_cash: float, event_bus: EventBus | None = None):
        safe_cash = max(0.0, float(initial_cash)) if initial_cash is not None else 0.0
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
            cash_ratio_weight=0.08,
        )
        portfolio = PortfolioManager(initial_cash=safe_cash)
        strategy_engine.portfolio = portfolio
        return {
            "event_bus": event_bus,
            "market_data": market_data,
            "nlp": NLPEngine(event_bus=event_bus),
            "portfolio": portfolio,
            "account_sync": AccountSyncAgent(portfolio, event_bus=event_bus),
            "strategy": strategy_engine,
            "optimization": OptimizationEngine(strategy_engine),
            "order_mgmt": OrderManagementSystem(event_bus=event_bus),
            "logger": TradeLogger(),
            "db": AssetHistoryDB(),
            "ai_db": AIPredictionDB(),
            "risk": RiskManager(portfolio_value=safe_cash),
            "backtest": BacktestEngine(initial_capital=safe_cash),
            "stats": AdvancedStatistics(),
            "error_handler": ErrorHandler(max_retries=3),
            "broker": KiwoomConnector(),
            "multi_broker": MultiBrokerManager(),
            "investor_strategy": InvestorStrategyEngine(),
            "llm": LLMEngine(),
            "global_market": global_market,
            "relative_strength": rsa,
        }
