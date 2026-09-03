"""다중 증권사 관리자"""

import logging
from enum import Enum
from typing import Dict, List, Optional

from .daishin import DaishinConnector
from .hanwha import HanwhaConnector
from .kiwoom import KiwoomConnector
from .korea_investment import KoreaInvestmentConnector
from .ls import LSConnector
from .miraeasset import MiraeAssetConnector
from .nh import NHConnector
from .interactive_brokers import InteractiveBrokersConnector
from .fix_protocol_engine import FIX44Engine
from .protocol import BrokerProtocol

logger = logging.getLogger(__name__)


class BrokerType(Enum):
    """증권사 유형"""

    KIWOOM = "kiwoom"
    DAISHIN = "daishin"
    HANWHA = "hanwha"
    KOREA_INVESTMENT = "korea_investment"
    MIRAE_ASSET = "mirae_asset"
    NH = "nh"
    LS = "ls"
    INTERACTIVE_BROKERS = "interactive_brokers"
    FIX_PROTOCOL = "fix_protocol"


class MultiBrokerManager:
    """다중 증권사 관리자"""

    def __init__(self):
        """다중 증권사 관리자 초기화"""
        self.brokers: Dict[BrokerType, BrokerProtocol] = {}
        self.active_broker: Optional[BrokerType] = None
        self.logger = logger

        # 기본 증권사 초기화
        self._init_brokers()

    def _init_brokers(self) -> None:
        """모든 증권사 초기화"""
        self.brokers[BrokerType.KIWOOM] = KiwoomConnector()
        self.brokers[BrokerType.DAISHIN] = DaishinConnector()
        self.brokers[BrokerType.HANWHA] = HanwhaConnector()
        self.brokers[BrokerType.KOREA_INVESTMENT] = KoreaInvestmentConnector()
        self.brokers[BrokerType.MIRAE_ASSET] = MiraeAssetConnector()
        self.brokers[BrokerType.NH] = NHConnector()
        self.brokers[BrokerType.LS] = LSConnector()
        self.brokers[BrokerType.INTERACTIVE_BROKERS] = InteractiveBrokersConnector()
        self.brokers[BrokerType.FIX_PROTOCOL] = FIX44Engine()

        self.logger.info("MultiBrokerManager initialized with 9 brokers (including IBKR & FIX 4.4)")

    def connect(self, broker_type: BrokerType, account_number: str) -> bool:
        """
        특정 증권사에 연결

        Args:
            broker_type: 증권사 유형
            account_number: 계좌번호

        Returns:
            bool: 연결 성공 여부
        """
        if broker_type not in self.brokers:
            self.logger.error(f"Unknown broker type: {broker_type}")
            return False

        safe_acc = str(account_number) if account_number is not None else ""
        broker = self.brokers[broker_type]
        result = broker.connect(safe_acc)

        if result:
            self.active_broker = broker_type
            self.logger.info(f"Connected to {broker_type.value} with account {safe_acc}")

        return result

    def disconnect(self, broker_type: BrokerType) -> bool:
        """증권사 연결 해제"""
        if broker_type not in self.brokers:
            return False

        broker = self.brokers[broker_type]
        result = broker.disconnect()

        if self.active_broker == broker_type:
            self.active_broker = None

        return result

    def switch_broker(self, broker_type: BrokerType) -> bool:
        """증권사 전환"""
        if broker_type not in self.brokers:
            self.logger.error(f"Unknown broker type: {broker_type}")
            return False

        broker = self.brokers[broker_type]
        if not broker.is_connected:
            self.logger.warning(f"Broker {broker_type.value} is not connected")
            return False

        self.active_broker = broker_type
        self.logger.info(f"Switched to {broker_type.value}")

        return True

    def get_active_broker(self) -> Optional[BrokerProtocol]:
        if self.active_broker:
            return self.brokers[self.active_broker]
        return None

    def place_order(
        self, code: str, quantity: int, price: float, order_type: str, broker_type: Optional[BrokerType] = None
    ) -> str:
        """주문 접수 (지정 증권사 또는 활성 증권사)"""
        import math
        broker_to_use = broker_type or self.active_broker

        if not broker_to_use or broker_to_use not in self.brokers:
            self.logger.error("No active broker selected")
            return ""

        q = max(0, int(quantity)) if quantity is not None else 0
        if q <= 0:
            self.logger.warning(f"Invalid order quantity ({quantity}) for {code}")
            return ""

        try:
            p = float(price) if (price is not None and math.isfinite(float(price))) else 0.0
        except (ValueError, TypeError):
            p = 0.0

        broker = self.brokers[broker_to_use]
        try:
            return broker.place_order(str(code), q, p, str(order_type))
        except Exception as e:
            self.logger.error(f"Error placing order on {broker_to_use.value}: {e}")
            return ""

    def cancel_order(self, order_id: str, broker_type: Optional[BrokerType] = None) -> bool:
        """주문 취소"""
        broker_to_use = broker_type or self.active_broker

        if not broker_to_use or broker_to_use not in self.brokers or not order_id:
            return False

        broker = self.brokers[broker_to_use]
        try:
            return broker.cancel_order(str(order_id))
        except Exception as e:
            self.logger.error(f"Error cancelling order {order_id} on {broker_to_use.value}: {e}")
            return False

    def get_order_status(self, order_id: str, broker_type: Optional[BrokerType] = None) -> Dict:
        """주문 상태 조회"""
        broker_to_use = broker_type or self.active_broker

        if not broker_to_use or broker_to_use not in self.brokers:
            return {}

        broker = self.brokers[broker_to_use]
        return broker.get_order_status(order_id)

    def get_account_info(self, broker_type: Optional[BrokerType] = None) -> Dict:
        """계좌 정보 조회"""
        broker_to_use = broker_type or self.active_broker

        if not broker_to_use or broker_to_use not in self.brokers:
            return {}

        broker = self.brokers[broker_to_use]
        return broker.get_account_info()

    def get_all_account_info(self) -> Dict[str, Dict]:
        """모든 증권사 계좌 정보 조회"""
        accounts = {}

        for broker_type, broker in self.brokers.items():
            if broker.is_connected:
                accounts[broker_type.value] = broker.get_account_info()

        return accounts

    def get_stock_quote(self, code: str, broker_type: Optional[BrokerType] = None) -> Dict:
        """주식 시세 조회"""
        broker_to_use = broker_type or self.active_broker

        if not broker_to_use or broker_to_use not in self.brokers:
            return {}

        broker = self.brokers[broker_to_use]
        return broker.get_stock_quote(code)

    def get_daily_chart(self, code: str, days: int = 20, broker_type: Optional[BrokerType] = None) -> List[Dict]:
        """일봉 차트 조회"""
        broker_to_use = broker_type or self.active_broker

        if not broker_to_use or broker_to_use not in self.brokers:
            return []

        broker = self.brokers[broker_to_use]
        return broker.get_daily_chart(code, days)

    def get_broker_status(self) -> Dict:
        """모든 증권사 상태 조회"""
        status = {}

        for broker_type, broker in self.brokers.items():
            status[broker_type.value] = {
                "is_connected": broker.is_connected,
                "account_number": getattr(broker, "account_number", ""),
                "simulation_mode": getattr(broker, "simulation_mode", False),
                "is_active": broker_type == self.active_broker,
            }

        return status

    def get_broker_info(self, broker_type: BrokerType) -> Dict:
        """증권사 정보 조회"""
        if broker_type not in self.brokers:
            return {}

        broker = self.brokers[broker_type]
        return broker.get_broker_info()

    def get_all_brokers_info(self) -> Dict[str, Dict]:
        """모든 증권사 정보 조회"""
        infos = {}

        for broker_type, broker in self.brokers.items():
            infos[broker_type.value] = broker.get_broker_info()

        return infos
