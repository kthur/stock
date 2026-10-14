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
    from trading_system.src.risk.risk_manager import RiskLevel, RiskManager, RiskMetrics
    from trading_system.src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator
    from trading_system.src.risk.portfolio_allocator import PortfolioAllocator
    from trading_system.src.risk.portfolio_optimizer import PortfolioOptimizer
    from trading_system.src.risk.intraday_stop_loss import IntradayStopLossEngine, StopLossSignal, StopLossResult
    from trading_system.src.risk.pretrade_gatekeeper import PreTradeRiskGatekeeper
    from trading_system.src.risk.delta_beta_hedge import DeltaBetaHedgeEngine

DeltaBetaHedgeOverlay = DeltaBetaHedgeEngine

__all__ = [
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
]
