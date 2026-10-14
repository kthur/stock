"""
Execution & Institutional OMS Layer
Provides unified access to Order Management System (OMS), Smart Order Routing (SOR),
optimal execution schedulers, live/dry-run trade executors, and safety kill switches.
"""

from __future__ import annotations

try:
    from src.execution.oms_engine import ExecutionOMSEngine, OMSEngine, AlmgrenChrissScheduler
    from src.execution.smart_order_router import SmartOrderRouter
    from src.execution.adaptive_router import AdaptiveOrderRouter
    from src.execution.cross_impact import CrossAssetImpactEngine
    from src.execution.hawkes_vpin import HawkesVPINToxicityGate
    from src.execution.slippage_feedback import SlippageFeedbackEngine
    from src.execution.turnover_optimizer import TurnoverOptimizer
    from src.execution.kill_switch import (
        is_kill_switch_active,
        engage,
        disengage,
        get_state as get_kill_switch_state,
    )
    from src.realtime.trade_executor import TradeExecutor, ExecResult
except ImportError:
    from trading_system.src.execution.oms_engine import ExecutionOMSEngine, OMSEngine, AlmgrenChrissScheduler
    from trading_system.src.execution.smart_order_router import SmartOrderRouter
    from trading_system.src.execution.adaptive_router import AdaptiveOrderRouter
    from trading_system.src.execution.cross_impact import CrossAssetImpactEngine
    from trading_system.src.execution.hawkes_vpin import HawkesVPINToxicityGate
    from trading_system.src.execution.slippage_feedback import SlippageFeedbackEngine
    from trading_system.src.execution.turnover_optimizer import TurnoverOptimizer
    from trading_system.src.execution.kill_switch import (
        is_kill_switch_active,
        engage,
        disengage,
        get_state as get_kill_switch_state,
    )
    from trading_system.src.realtime.trade_executor import TradeExecutor, ExecResult

AdaptiveRouter = AdaptiveOrderRouter
CrossImpactEngine = CrossAssetImpactEngine
HawkesVPINEngine = HawkesVPINToxicityGate

__all__ = [
    "ExecutionOMSEngine",
    "OMSEngine",
    "AlmgrenChrissScheduler",
    "SmartOrderRouter",
    "AdaptiveOrderRouter",
    "AdaptiveRouter",
    "CrossAssetImpactEngine",
    "CrossImpactEngine",
    "HawkesVPINToxicityGate",
    "HawkesVPINEngine",
    "SlippageFeedbackEngine",
    "TurnoverOptimizer",
    "TradeExecutor",
    "ExecResult",
    "is_kill_switch_active",
    "engage",
    "disengage",
    "get_kill_switch_state",
]
