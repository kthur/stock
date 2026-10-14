"""
Broker Abstraction & Multi-Venue Execution Package
Provides unified connectivity across domestic (Kiwoom, KIS, Daishin, Mirae, LS, NH, Hanwha)
and global institutional brokers (Interactive Brokers IBKR, FIX 4.4 DMA Engine).
"""

from __future__ import annotations

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
    from .fix_protocol_engine import FIXProtocolEngine, FIX44Engine, FIXMessage
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
    from trading_system.src.broker.fix_protocol_engine import FIXProtocolEngine, FIX44Engine, FIXMessage

__all__ = [
    "BrokerProtocol",
    "BrokerType",
    "DaishinConnector",
    "HanwhaConnector",
    "KiwoomConnector",
    "KoreaInvestmentConnector",
    "LSConnector",
    "MiraeAssetConnector",
    "MultiBrokerManager",
    "NHConnector",
    "InteractiveBrokersConnector",
    "FIX44Engine",
    "FIXProtocolEngine",
    "FIXMessage",
]

