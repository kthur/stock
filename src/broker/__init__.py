"""
src/broker/__init__.py — Unified Broker & Kernel-Bypass Network Transport Package
Phase 109 (Release R125 / v116 Production Master)

Provides unified connectivity across domestic and global institutional brokers:
  - Kernel-Bypass Transport: DPDK/AF_XDP Mock DMA transport engine with UMEM memory pools,
    zero-copy FIX 4.4, binary LOB multicast, and sub-microsecond descriptor ring queues.
"""

from __future__ import annotations

# Kernel-Bypass Transport Engine & related abstractions
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

# Optional re-export of legacy broker components if available
try:
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
except Exception:
    pass

__all__ = [
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
