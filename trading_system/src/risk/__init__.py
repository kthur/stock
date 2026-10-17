"""
Risk & Institutional Portfolio Allocation Layer
Provides unified access to regime-adaptive multi-model portfolio allocation,
tail-risk budgeting (EVT-CVaR), intraday dynamic stop-loss, and pre-trade gating.
"""

from __future__ import annotations

try:
    from src.risk.risk_manager import RiskLevel, RiskManager, RiskMetrics
    from src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator
    from src.risk.portfolio_allocator import PortfolioAllocator
    from src.risk.portfolio_optimizer import PortfolioOptimizer
    from src.risk.intraday_stop_loss import IntradayStopLossEngine, StopLossSignal, StopLossResult
    from src.risk.pretrade_gatekeeper import PreTradeRiskGatekeeper
    from src.risk.delta_beta_hedge import DeltaBetaHedgeEngine
except ImportError:
    try:
        from trading_system.src.risk.risk_manager import RiskLevel, RiskManager, RiskMetrics
        from trading_system.src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator
        from trading_system.src.risk.portfolio_allocator import PortfolioAllocator
        from trading_system.src.risk.portfolio_optimizer import PortfolioOptimizer
        from trading_system.src.risk.intraday_stop_loss import IntradayStopLossEngine, StopLossSignal, StopLossResult
        from trading_system.src.risk.pretrade_gatekeeper import PreTradeRiskGatekeeper
        from trading_system.src.risk.delta_beta_hedge import DeltaBetaHedgeEngine
    except ImportError:
        pass

DeltaBetaHedgeOverlay = globals().get("DeltaBetaHedgeEngine", None)

# Phase 116 Avellaneda-Stoikov Controller (F552)
try:
    from src.risk.avellaneda_stoikov_controller import (
        AvellanedaStoikovController,
        AvellanedaStoikovConfig,
    )
except ImportError:
    try:
        from trading_system.src.risk.avellaneda_stoikov_controller import (
            AvellanedaStoikovController,
            AvellanedaStoikovConfig,
        )
    except ImportError:
        pass

# Phase 117 Dynamic Liquidity Risk Parity (F557)
try:
    from src.risk.dynamic_liquidity_risk_parity import (
        DynamicLiquidityRiskParityAllocator,
        LiquidityRiskParityConfig,
        AssetLiquidityMetrics,
        LiquidityRiskParityResult,
    )
except ImportError:
    try:
        from trading_system.src.risk.dynamic_liquidity_risk_parity import (
            DynamicLiquidityRiskParityAllocator,
            LiquidityRiskParityConfig,
            AssetLiquidityMetrics,
            LiquidityRiskParityResult,
        )
    except ImportError:
        pass

# Phase 118 Cross-Asset Lead-Lag Graph Flow Liquidity Rebalancing Allocator (F562)
try:
    from src.risk.cross_asset_graph_flow_allocator import (
        CrossAssetGraphFlowAllocator,
        GraphFlowConfig,
        GraphCentralityMetrics,
        GraphRebalancingResult,
        AssetClassType,
    )
except ImportError:
    try:
        from trading_system.src.risk.cross_asset_graph_flow_allocator import (
            CrossAssetGraphFlowAllocator,
            GraphFlowConfig,
            GraphCentralityMetrics,
            GraphRebalancingResult,
            AssetClassType,
        )
    except ImportError:
        pass

__all__ = [
    # Core Risk Management & Allocators
    "RiskLevel",
    "RiskManager",
    "RiskMetrics",
    "UnifiedPortfolioAllocator",
    "PortfolioAllocator",
    "PortfolioOptimizer",
    "IntradayStopLossEngine",
    "StopLossSignal",
    "StopLossResult",
    "PreTradeRiskGatekeeper",
    "DeltaBetaHedgeEngine",
    "DeltaBetaHedgeOverlay",
    # Phase 116 Exports (F552)
    "AvellanedaStoikovController",
    "AvellanedaStoikovConfig",
    # Phase 117 Exports (F557)
    "DynamicLiquidityRiskParityAllocator",
    "LiquidityRiskParityConfig",
    "AssetLiquidityMetrics",
    "LiquidityRiskParityResult",
    # Phase 118 Exports (F562)
    "CrossAssetGraphFlowAllocator",
    "GraphFlowConfig",
    "GraphCentralityMetrics",
    "GraphRebalancingResult",
    "AssetClassType",
]
