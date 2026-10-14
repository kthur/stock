"""
Core Trading System — Order Management, Microstructure, and Alpha Engines
Provides order tracking, portfolio management, microsecond LOB matching,
Hawkes arrival intensity, and core strategy generation engines.
"""

from __future__ import annotations

try:
    from .asset_management import AccountSyncAgent, PortfolioManager
    from .distributed_order import DistributedOrderConfig, DistributedOrderManager
    from .order_management import Order, OrderManagementSystem, OrderStatus, OrderType
    from .strategy_engine import HybridStrategyEngine, OptimizationEngine, TradeSignal
    from .fast_lob_engine import (
        FastLOBEngine,
        ZeroCopyRingBuffer,
        FastOrderBookMatchingEngine,
        MicrosecondHawkesIntensity,
    )
    from .event_driven import EventDrivenEngine
    from .mq_factor import MQFactorEngine
    from .cross_asset_spillover import CrossAssetSpilloverEngine
    from .supply_chain_gnn import SupplyChainGNNEngine
    from .range_expansion_breakout import RangeExpansionBreakoutEngine
    from .dual_correction import DualCorrectionEngine
    from .index_rebalance import IndexRebalanceEngine
    from .overnight_gap_reversal import OvernightGapReversalEngine
except ImportError:
    from trading_system.src.core.asset_management import AccountSyncAgent, PortfolioManager
    from trading_system.src.core.distributed_order import DistributedOrderConfig, DistributedOrderManager
    from trading_system.src.core.order_management import Order, OrderManagementSystem, OrderStatus, OrderType
    from trading_system.src.core.strategy_engine import HybridStrategyEngine, OptimizationEngine, TradeSignal
    from trading_system.src.core.fast_lob_engine import (
        FastLOBEngine,
        ZeroCopyRingBuffer,
        FastOrderBookMatchingEngine,
        MicrosecondHawkesIntensity,
    )
    from trading_system.src.core.event_driven import EventDrivenEngine
    from trading_system.src.core.mq_factor import MQFactorEngine
    from trading_system.src.core.cross_asset_spillover import CrossAssetSpilloverEngine
    from trading_system.src.core.supply_chain_gnn import SupplyChainGNNEngine
    from trading_system.src.core.range_expansion_breakout import RangeExpansionBreakoutEngine
    from trading_system.src.core.dual_correction import DualCorrectionEngine
    from trading_system.src.core.index_rebalance import IndexRebalanceEngine
    from trading_system.src.core.overnight_gap_reversal import OvernightGapReversalEngine

__all__ = [
    "AccountSyncAgent",
    "DistributedOrderConfig",
    "DistributedOrderManager",
    "HybridStrategyEngine",
    "OptimizationEngine",
    "Order",
    "OrderManagementSystem",
    "OrderStatus",
    "OrderType",
    "PortfolioManager",
    "TradeSignal",
    "FastLOBEngine",
    "ZeroCopyRingBuffer",
    "FastOrderBookMatchingEngine",
    "MicrosecondHawkesIntensity",
    "EventDrivenEngine",
    "MQFactorEngine",
    "CrossAssetSpilloverEngine",
    "SupplyChainGNNEngine",
    "RangeExpansionBreakoutEngine",
    "DualCorrectionEngine",
    "IndexRebalanceEngine",
    "OvernightGapReversalEngine",
]
