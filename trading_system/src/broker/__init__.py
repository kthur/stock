"""
Broker Abstraction, Direct Market Access & Kernel-Bypass Network Transport Package
Phase 112 (Release R128 / v119 Production Master, Feature F530)

Provides unified connectivity across domestic and global institutional brokers:
  - Native OpenAPI Connectors: Korea Investment & Securities (KIS) & LS Securities (eBest Xing)
    REST & Real-Time WebSocket DMA interfaces with 10-level orderbook depth and OAuth token lifecycle.
  - Multi-Venue Execution: Kiwoom, Daishin, Hanwha, Mirae Asset, NH, Interactive Brokers (IBKR), FIX 4.4 DMA.
  - Kernel-Bypass Transport: DPDK/AF_XDP Mock DMA transport engine with UMEM memory pools,
    zero-copy FIX 4.4, binary LOB multicast, and sub-microsecond descriptor ring queues.
"""

from __future__ import annotations

# Native OpenAPI Connectors (Phase 112 F530)
from .kis_broker_connector import (
    AccountBalanceSnapshot,
    BaseBrokerConnector,
    BrokerResponse,
    ConnectedState,
    ExecutionNotice,
    KISBrokerConnector,
    KISConnector,
    KoreaInvestmentOpenAPIConnector,
    MarketTradeTick,
    OrderbookDepth,
    OrderbookLevel,
    Phase112KISConnector,
    PositionSnapshot,
    TokenBucketRateLimiter,
)
from .ls_broker_connector import (
    EBestXingConnector,
    LSBrokerConnector,
    LSOpenAPIConnector,
    LSSecuritiesConnector,
    Phase112LSConnector,
)

# Kernel-Bypass Transport Engine & related abstractions
try:
    from .kernel_bypass_transport import (
        AFXDPRingQueue,
        AFXDPTransportEngine,
        BinaryLOBPacket,
        DPDKMockTransport,
        DescriptorRingQueue,
        FIXMessage,
        KernelBypassDMAEngine,
        KernelBypassTransport,
        KernelBypassTransportEngine,
        LOBMulticastPacket,
        PacketDescriptor,
        Phase109KernelBypassTransport,
        SPSCRingQueue,
        UMEMDescriptor,
        UMEMFramePool,
        UMEMMemoryPool,
        ZeroCopyDMATransport,
    )
except ImportError:
    from trading_system.src.broker.kernel_bypass_transport import (
        AFXDPRingQueue,
        AFXDPTransportEngine,
        BinaryLOBPacket,
        DPDKMockTransport,
        DescriptorRingQueue,
        FIXMessage,
        KernelBypassDMAEngine,
        KernelBypassTransport,
        KernelBypassTransportEngine,
        LOBMulticastPacket,
        PacketDescriptor,
        Phase109KernelBypassTransport,
        SPSCRingQueue,
        UMEMDescriptor,
        UMEMFramePool,
        UMEMMemoryPool,
        ZeroCopyDMATransport,
    )

# Institutional Multi-Broker Management & Protocol
try:
    from .protocol import BrokerProtocol
    from .multi_broker_manager import BrokerType, MultiBrokerManager
    from .daishin import DaishinConnector
    from .hanwha import HanwhaConnector
    from .kiwoom import KiwoomConnector
    from .korea_investment import KoreaInvestmentConnector
    from .ls import LSConnector
    from .miraeasset import MiraeAssetConnector
    from .nh import NHConnector
    from .interactive_brokers import InteractiveBrokersConnector
    from .fix_protocol_engine import FIXProtocolEngine, FIX44Engine
except ImportError:
    from trading_system.src.broker.protocol import BrokerProtocol
    from trading_system.src.broker.multi_broker_manager import BrokerType, MultiBrokerManager
    from trading_system.src.broker.daishin import DaishinConnector
    from trading_system.src.broker.hanwha import HanwhaConnector
    from trading_system.src.broker.kiwoom import KiwoomConnector
    from trading_system.src.broker.korea_investment import KoreaInvestmentConnector
    from trading_system.src.broker.ls import LSConnector
    from trading_system.src.broker.miraeasset import MiraeAssetConnector
    from trading_system.src.broker.nh import NHConnector
    from trading_system.src.broker.interactive_brokers import InteractiveBrokersConnector
    from trading_system.src.broker.fix_protocol_engine import FIXProtocolEngine, FIX44Engine

# Phase 118 Sub-Nanosecond DMA Broker Gateway (F563)
try:
    from .sub_nano_dma_broker_gateway import (
        SubNanoDMABrokerGateway,
        DMAGatewayConfig,
        DMAOrder,
        BrokerState,
        OrderSide,
        OrderType,
        DispatchReceipt,
        MemoryMappedRingBuffer,
    )
except ImportError:
    try:
        from trading_system.src.broker.sub_nano_dma_broker_gateway import (
            SubNanoDMABrokerGateway,
            DMAGatewayConfig,
            DMAOrder,
            BrokerState,
            OrderSide,
            OrderType,
            DispatchReceipt,
            MemoryMappedRingBuffer,
        )
    except ImportError:
        pass

__all__ = [
    # Phase 118 Sub-Nanosecond DMA Broker Gateway (F563)
    "SubNanoDMABrokerGateway",
    "DMAGatewayConfig",
    "DMAOrder",
    "BrokerState",
    "OrderSide",
    "OrderType",
    "DispatchReceipt",
    "MemoryMappedRingBuffer",
    # Phase 112 Native OpenAPI Connectors & Data Models
    "BaseBrokerConnector",
    "KISBrokerConnector",
    "KoreaInvestmentOpenAPIConnector",
    "KISConnector",
    "Phase112KISConnector",
    "LSBrokerConnector",
    "LSSecuritiesConnector",
    "EBestXingConnector",
    "LSOpenAPIConnector",
    "Phase112LSConnector",
    "OrderbookLevel",
    "OrderbookDepth",
    "MarketTradeTick",
    "ExecutionNotice",
    "PositionSnapshot",
    "AccountBalanceSnapshot",
    "TokenBucketRateLimiter",
    "ConnectedState",
    "BrokerResponse",
    # Institutional Multi-Broker Infrastructure
    "BrokerProtocol",
    "BrokerType",
    "MultiBrokerManager",
    "DaishinConnector",
    "HanwhaConnector",
    "KiwoomConnector",
    "KoreaInvestmentConnector",
    "LSConnector",
    "MiraeAssetConnector",
    "NHConnector",
    "InteractiveBrokersConnector",
    "FIXProtocolEngine",
    "FIX44Engine",
    # Kernel-Bypass DPDK/AF_XDP Mock DMA Infrastructure
    "KernelBypassTransportEngine",
    "KernelBypassTransport",
    "KernelBypassDMAEngine",
    "AFXDPTransportEngine",
    "DPDKMockTransport",
    "ZeroCopyDMATransport",
    "Phase109KernelBypassTransport",
    "UMEMMemoryPool",
    "UMEMFramePool",
    "PacketDescriptor",
    "UMEMDescriptor",
    "DescriptorRingQueue",
    "SPSCRingQueue",
    "AFXDPRingQueue",
    "LOBMulticastPacket",
    "BinaryLOBPacket",
    "FIXMessage",
]
