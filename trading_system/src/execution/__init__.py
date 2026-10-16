"""
Execution & Institutional OMS Layer
Provides unified access to Order Management System (OMS), Smart Order Routing (SOR),
optimal execution schedulers, live/dry-run trade executors, safety kill switches,
and real-time asyncio live execution trading daemons.
"""

from __future__ import annotations

# OMS & SOR
try:
    from .oms_engine import ExecutionOMSEngine, OMSEngine, AlmgrenChrissScheduler
except ImportError:
    try:
        from trading_system.src.execution.oms_engine import ExecutionOMSEngine, OMSEngine, AlmgrenChrissScheduler
    except ImportError:
        ExecutionOMSEngine = None
        OMSEngine = None
        AlmgrenChrissScheduler = None

try:
    from .smart_order_router import SmartOrderRouter
except ImportError:
    try:
        from trading_system.src.execution.smart_order_router import SmartOrderRouter
    except ImportError:
        SmartOrderRouter = None

# Optional routers & feedback engines
try:
    from .adaptive_router import AdaptiveOrderRouter
except ImportError:
    try:
        from trading_system.src.execution.adaptive_router import AdaptiveOrderRouter
    except ImportError:
        AdaptiveOrderRouter = None

AdaptiveRouter = AdaptiveOrderRouter

try:
    from .cross_impact import CrossAssetImpactEngine
except ImportError:
    try:
        from trading_system.src.execution.cross_impact import CrossAssetImpactEngine
    except ImportError:
        CrossAssetImpactEngine = None

CrossImpactEngine = CrossAssetImpactEngine

try:
    from .hawkes_vpin import HawkesVPINToxicityGate
except ImportError:
    try:
        from trading_system.src.execution.hawkes_vpin import HawkesVPINToxicityGate
    except ImportError:
        HawkesVPINToxicityGate = None

HawkesVPINEngine = HawkesVPINToxicityGate

try:
    from .slippage_feedback import SlippageFeedbackEngine
except ImportError:
    try:
        from trading_system.src.execution.slippage_feedback import SlippageFeedbackEngine
    except ImportError:
        SlippageFeedbackEngine = None

try:
    from .turnover_optimizer import TurnoverOptimizer
except ImportError:
    try:
        from trading_system.src.execution.turnover_optimizer import TurnoverOptimizer
    except ImportError:
        TurnoverOptimizer = None

try:
    from .kill_switch import (
        is_kill_switch_active,
        engage,
        disengage,
        get_state as get_kill_switch_state,
    )
except ImportError:
    try:
        from trading_system.src.execution.kill_switch import (
            is_kill_switch_active,
            engage,
            disengage,
            get_state as get_kill_switch_state,
        )
    except ImportError:
        is_kill_switch_active = lambda: False
        engage = lambda reason="": None
        disengage = lambda: None
        get_kill_switch_state = lambda: {}

try:
    from src.realtime.trade_executor import TradeExecutor, ExecResult
except ImportError:
    try:
        from trading_system.src.realtime.trade_executor import TradeExecutor, ExecResult
    except ImportError:
        TradeExecutor = None
        ExecResult = None

# Live Trading Daemon (Phase 112 / Feature F531)
from .live_trading_daemon import (
    LiveTradingDaemon,
    AsyncioTradingDaemon,
    EventDrivenTradingDaemon,
    LiveExecutionDaemon,
    Phase112TradingDaemon,
    ProductionTradingDaemon,
    RealTimeTradingDaemon,
    InstitutionalTradingDaemon,
    HighFrequencyTradingDaemon,
    AsyncExecutionDaemon,
    DaemonPriority,
    DaemonEventType,
    DaemonSessionState,
    SessionState,
    PrioritizedDaemonEvent,
    MarketTickEvent,
    OrderBookUpdateEvent,
    LiveTrancheOrder,
    VolatilitySpikeEvent,
    EmergencyHaltEvent,
    LiveDaemonConfig,
)

# Account Reconciliation Engine (Phase 112 / Feature F532)
from .account_reconciliation_engine import (
    AccountReconciliationEngine,
    RealTimeReconciliationEngine,
    PositionReconciliationEngine,
    BrokerReconciliationEngine,
    Phase112ReconciliationEngine,
    InstitutionalReconciliationEngine,
    CashPositionReconciler,
    ClearingReconciliationEngine,
    PortfolioReconciliationEngine,
    PennyConservationReconciler,
    TaxLotMethod,
    ReconciliationStatus,
    TaxLot,
    TaxLotAdjustment,
    BrokerAccountSnapshot,
    ReconciliationReport,
    KRX_STT_RATE,
    SEC_SECTION_31_RATE,
    FINRA_TAF_RATE_PER_SHARE,
    FINRA_TAF_MAX_PER_TRADE,
    KRX_BROKER_FEE,
    US_BROKER_FEE,
    DISCREPANCY_TOLERANCE_PCT,
    PENNY_CONSERVATION_EPSILON,
)

# Real-Time Lockless Queue OMS Dispatcher (Phase 115 / Feature F548)
try:
    from .lockless_oms_dispatcher import (
        CircuitBreakerState,
        OverflowPolicy,
        DispatchStatus,
        CircuitBreakerConfig,
        DispatchOrder,
        DispatchResult,
        SPSCLocklessQueue,
        MPSCLocklessQueue,
        MicrosecondCircuitBreaker,
        LocklessOMSDispatcher,
        RealTimeLocklessQueueDispatcher,
        Phase115OMSDispatcher,
        InstitutionalOrderDispatcher,
        FastOMSDispatcher,
        MicrosecondRiskGate,
    )
except ImportError:
    try:
        from trading_system.src.execution.lockless_oms_dispatcher import (
            CircuitBreakerState,
            OverflowPolicy,
            DispatchStatus,
            CircuitBreakerConfig,
            DispatchOrder,
            DispatchResult,
            SPSCLocklessQueue,
            MPSCLocklessQueue,
            MicrosecondCircuitBreaker,
            LocklessOMSDispatcher,
            RealTimeLocklessQueueDispatcher,
            Phase115OMSDispatcher,
            InstitutionalOrderDispatcher,
            FastOMSDispatcher,
            MicrosecondRiskGate,
        )
    except ImportError:
        pass

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
    # Live Trading Daemon (Phase 112 / Feature F531)
    "LiveTradingDaemon",
    "AsyncioTradingDaemon",
    "EventDrivenTradingDaemon",
    "LiveExecutionDaemon",
    "Phase112TradingDaemon",
    "ProductionTradingDaemon",
    "RealTimeTradingDaemon",
    "InstitutionalTradingDaemon",
    "HighFrequencyTradingDaemon",
    "AsyncExecutionDaemon",
    "DaemonPriority",
    "DaemonEventType",
    "DaemonSessionState",
    "SessionState",
    "PrioritizedDaemonEvent",
    "MarketTickEvent",
    "OrderBookUpdateEvent",
    "LiveTrancheOrder",
    "VolatilitySpikeEvent",
    "EmergencyHaltEvent",
    "LiveDaemonConfig",
    # Account Reconciliation Engine (Phase 112 / Feature F532)
    "AccountReconciliationEngine",
    "RealTimeReconciliationEngine",
    "PositionReconciliationEngine",
    "BrokerReconciliationEngine",
    "Phase112ReconciliationEngine",
    "InstitutionalReconciliationEngine",
    "CashPositionReconciler",
    "ClearingReconciliationEngine",
    "PortfolioReconciliationEngine",
    "PennyConservationReconciler",
    "TaxLotMethod",
    "ReconciliationStatus",
    "TaxLot",
    "TaxLotAdjustment",
    "BrokerAccountSnapshot",
    "ReconciliationReport",
    "KRX_STT_RATE",
    "SEC_SECTION_31_RATE",
    "FINRA_TAF_RATE_PER_SHARE",
    "FINRA_TAF_MAX_PER_TRADE",
    "KRX_BROKER_FEE",
    "US_BROKER_FEE",
    "DISCREPANCY_TOLERANCE_PCT",
    "PENNY_CONSERVATION_EPSILON",
    # Real-Time Lockless Queue OMS Dispatcher (Phase 115 / Feature F548)
    "CircuitBreakerState",
    "OverflowPolicy",
    "DispatchStatus",
    "CircuitBreakerConfig",
    "DispatchOrder",
    "DispatchResult",
    "SPSCLocklessQueue",
    "MPSCLocklessQueue",
    "MicrosecondCircuitBreaker",
    "LocklessOMSDispatcher",
    "RealTimeLocklessQueueDispatcher",
    "Phase115OMSDispatcher",
    "InstitutionalOrderDispatcher",
    "FastOMSDispatcher",
    "MicrosecondRiskGate",
]

