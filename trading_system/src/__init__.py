"""주식 트레이딩 시스템 초기화"""

from .data_layer import MarketDataHandler, NLPEngine
from .core import (
    PortfolioManager,
    AccountSyncAgent,
    HybridStrategyEngine,
    OptimizationEngine,
    OrderManagementSystem,
    OrderType,
    TradeSignal
)
from .persistence import TradeLogger, AssetHistoryDB

__version__ = "1.0.0"
__author__ = "Stock Trading Team"
__all__ = [
    'MarketDataHandler',
    'NLPEngine',
    'PortfolioManager',
    'AccountSyncAgent',
    'HybridStrategyEngine',
    'OptimizationEngine',
    'OrderManagementSystem',
    'TradeLogger',
    'AssetHistoryDB'
]
