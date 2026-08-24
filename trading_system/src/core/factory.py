"""
Strategy Factory and Service Container for Dependency Injection.
Enables decoupled instantiation, lifecycle management, and test mocking across all 31 quantitative engines.
"""

from typing import Dict, Any, Type, Optional, Callable
import logging
import math

logger = logging.getLogger(__name__)


class ServiceContainer:
    """
    Lightweight dependency injection container for sharing core infrastructure
    services (Storage, RiskManager, Scorer, Config) across trading components.
    """
    _instance: Optional['ServiceContainer'] = None

    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._factories: Dict[str, Callable[['ServiceContainer'], Any]] = {}
        self._resolving: set = set()

    @classmethod
    def get_instance(cls) -> 'ServiceContainer':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls):
        """Reset container singleton (useful for test isolation)."""
        cls._instance = None

    def register(self, service_name: str, instance: Any) -> None:
        """Register an existing singleton service instance."""
        self._services[service_name] = instance

    def register_factory(self, service_name: str, factory_fn: Callable[['ServiceContainer'], Any]) -> None:
        """Register a lazy service factory."""
        self._factories[service_name] = factory_fn

    def resolve(self, service_name: str) -> Any:
        """Resolve a registered service or construct it via factory with circular dependency protection."""
        if service_name in self._services:
            return self._services[service_name]
        if service_name in self._factories:
            if service_name in self._resolving:
                raise RuntimeError(
                    f"Circular dependency detected in ServiceContainer while resolving {service_name!r}. "
                    f"Active resolution chain: {list(self._resolving)}"
                )
            self._resolving.add(service_name)
            try:
                instance = self._factories[service_name](self)
                self._services[service_name] = instance
                return instance
            finally:
                self._resolving.remove(service_name)
        raise KeyError(f"Service {service_name!r} is not registered in the ServiceContainer.")

    def has(self, service_name: str) -> bool:
        return service_name in self._services or service_name in self._factories


class StrategyFactory:
    """
    Factory for creating and configuring quantitative strategy engines with injected dependencies.
    """
    _registered_strategies: Dict[int, Type] = {}
    _strategy_names: Dict[int, str] = {}

    @classmethod
    def register(cls, strategy_id: int, name: str):
        """Decorator to register a strategy engine class by its unique ID."""
        def decorator(engine_cls: Type):
            cls._registered_strategies[strategy_id] = engine_cls
            cls._strategy_names[strategy_id] = name
            return engine_cls
        return decorator

    @classmethod
    def create(cls, strategy_id: int, container: Optional[ServiceContainer] = None, **kwargs) -> Any:
        """Instantiate a registered strategy engine with dependency resolution."""
        if strategy_id not in cls._registered_strategies:
            raise KeyError(f"Strategy ID {strategy_id} is not registered.")
        engine_cls = cls._registered_strategies[strategy_id]
        return engine_cls(**kwargs)

    @classmethod
    def list_strategies(cls) -> Dict[int, str]:
        """Return a mapping of registered strategy IDs to human-readable names."""
        return dict(cls._strategy_names)


class SystemFactory:
    """
    Factory for creating default StockTradingSystem core components.
    Maintains full backward compatibility for trading_system.py.
    """
    @staticmethod
    def create_default_components(initial_cash: float, event_bus: Optional[Any] = None) -> Dict[str, Any]:
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

        safe_cash = 0.0
        if initial_cash is not None:
            try:
                c_val = float(initial_cash)
                safe_cash = max(0.0, c_val) if math.isfinite(c_val) else 0.0
            except (ValueError, TypeError):
                safe_cash = 0.0
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
