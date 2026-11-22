"""다중 증권사 관리자"""

import logging
from enum import Enum
from typing import Any, Dict, List, Optional, Union

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
    """다중 증권사 관리자 (의존성 주입 및 동적 브로커 등록 지원)"""

    def __init__(
        self,
        brokers: Optional[Dict[Union[BrokerType, str], Any]] = None,
        default_broker: Optional[Union[BrokerType, str]] = None,
    ):
        """
        다중 증권사 관리자 초기화

        Args:
            brokers: 사전 등록할 브로커 인스턴스 딕셔너리 (BrokerType 또는 문자열 키).
                     None인 경우 기본 9대 브로커 자동 초기화 (100% 하위 호환성).
            default_broker: 초기 활성 브로커 (선택사항).
        """
        self.brokers: Dict[Union[BrokerType, str], Any] = {}
        self.active_broker: Optional[Union[BrokerType, str]] = None
        self.logger = logger

        if brokers is not None:
            for b_key, b_inst in brokers.items():
                self.register_broker(b_key, b_inst)
        else:
            # 기본 증권사 초기화
            self._init_brokers()

        if default_broker is not None:
            normalized_default = self._normalize_broker_type(default_broker)
            if normalized_default in self.brokers:
                self.active_broker = normalized_default

    def _normalize_broker_type(self, broker_type: Union[BrokerType, str]) -> Union[BrokerType, str]:
        """BrokerType 또는 문자열을 등록된 키 또는 표준 키로 정규화"""
        if isinstance(broker_type, BrokerType):
            return broker_type
        if isinstance(broker_type, str):
            if broker_type in self.brokers:
                return broker_type
            for b in BrokerType:
                if b.value.lower() == broker_type.lower():
                    return b
            try:
                return BrokerType[broker_type.upper()]
            except KeyError:
                pass
            for k in self.brokers:
                k_str = k.value if isinstance(k, BrokerType) else str(k)
                if k_str.lower() == broker_type.lower():
                    return k
        return broker_type

    def register_broker(
        self,
        broker_type: Union[BrokerType, str],
        broker_instance: Any,
        set_active: bool = False,
    ) -> bool:
        """
        브로커 인스턴스 동적 등록 (Dependency Injection 지원).
        BrokerProtocol, BrokerBase, BaseBrokerConnector 등 모든 브로커 타입을
        UnifiedBrokerAdapter로 감싸 표준 인터페이스로 등록합니다.

        Args:
            broker_type: 증권사 식별자 (BrokerType Enum 또는 문자열).
            broker_instance: 등록할 브로커 인스턴스.
            set_active: True일 경우 등록과 동시에 활성 브로커로 설정.

        Returns:
            bool: 등록 성공 여부.
        """
        if broker_instance is None:
            self.logger.error(f"Cannot register None broker for {broker_type}")
            return False

        norm_key = self._normalize_broker_type(broker_type)
        from .unified_adapter import UnifiedBrokerAdapter

        name_str = norm_key.value if isinstance(norm_key, BrokerType) else str(norm_key)
        adapted = UnifiedBrokerAdapter.wrap(broker_instance, broker_name=name_str)
        self.brokers[norm_key] = adapted

        if set_active or self.active_broker is None:
            self.active_broker = norm_key

        self.logger.info(f"Registered broker: {norm_key}")
        return True

    def unregister_broker(self, broker_type: Union[BrokerType, str]) -> bool:
        """브로커 등록 해제"""
        norm_key = self._normalize_broker_type(broker_type)
        if norm_key in self.brokers:
            if self.active_broker == norm_key:
                self.active_broker = None
            del self.brokers[norm_key]
            self.logger.info(f"Unregistered broker: {norm_key}")
            return True
        return False

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

    def connect(self, broker_type: Union[BrokerType, str], account_number: str) -> bool:
        """
        특정 증권사에 연결

        Args:
            broker_type: 증권사 유형
            account_number: 계좌번호

        Returns:
            bool: 연결 성공 여부
        """
        norm_key = self._normalize_broker_type(broker_type)
        if norm_key not in self.brokers:
            self.logger.error(f"Unknown broker type: {broker_type}")
            return False

        safe_acc = str(account_number) if account_number is not None else ""
        broker = self.brokers[norm_key]
        result = broker.connect(safe_acc)

        if result:
            self.active_broker = norm_key
            label = norm_key.value if isinstance(norm_key, BrokerType) else str(norm_key)
            self.logger.info(f"Connected to {label} with account {safe_acc}")

        return result

    def disconnect(self, broker_type: Union[BrokerType, str]) -> bool:
        """증권사 연결 해제"""
        norm_key = self._normalize_broker_type(broker_type)
        if norm_key not in self.brokers:
            return False

        broker = self.brokers[norm_key]
        result = broker.disconnect()

        if self.active_broker == norm_key:
            self.active_broker = None

        return result

    def switch_broker(self, broker_type: Union[BrokerType, str]) -> bool:
        """증권사 전환"""
        norm_key = self._normalize_broker_type(broker_type)
        if norm_key not in self.brokers:
            self.logger.error(f"Unknown broker type: {broker_type}")
            return False

        broker = self.brokers[norm_key]
        is_conn = broker.is_connected() if callable(broker.is_connected) else bool(broker.is_connected)
        if not is_conn:
            label = norm_key.value if isinstance(norm_key, BrokerType) else str(norm_key)
            self.logger.warning(f"Broker {label} is not connected")
            return False

        self.active_broker = norm_key
        label = norm_key.value if isinstance(norm_key, BrokerType) else str(norm_key)
        self.logger.info(f"Switched to {label}")

        return True

    def get_active_broker(self) -> Optional[Any]:
        if self.active_broker and self.active_broker in self.brokers:
            return self.brokers[self.active_broker]
        return None

    def place_order(
        self, code: str, quantity: int, price: float, order_type: str, broker_type: Optional[Union[BrokerType, str]] = None
    ) -> str:
        """주문 접수 (지정 증권사 또는 활성 증권사)"""
        import math
        raw_to_use = broker_type or self.active_broker
        broker_to_use = self._normalize_broker_type(raw_to_use) if raw_to_use else None

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
            res = broker.place_order(str(code), q, p, str(order_type))
            if isinstance(res, dict):
                return str(res.get("order_id", res))
            return str(res)
        except Exception as e:
            label = broker_to_use.value if isinstance(broker_to_use, BrokerType) else str(broker_to_use)
            self.logger.error(f"Error placing order on {label}: {e}")
            return ""

    def cancel_order(self, order_id: str, broker_type: Optional[Union[BrokerType, str]] = None) -> bool:
        """주문 취소"""
        raw_to_use = broker_type or self.active_broker
        broker_to_use = self._normalize_broker_type(raw_to_use) if raw_to_use else None

        if not broker_to_use or broker_to_use not in self.brokers or not order_id:
            return False

        broker = self.brokers[broker_to_use]
        try:
            res = broker.cancel_order(str(order_id))
            if isinstance(res, dict):
                return bool(res.get("success", True))
            return bool(res)
        except Exception as e:
            label = broker_to_use.value if isinstance(broker_to_use, BrokerType) else str(broker_to_use)
            self.logger.error(f"Error cancelling order {order_id} on {label}: {e}")
            return False

    def get_order_status(self, order_id: str, broker_type: Optional[Union[BrokerType, str]] = None) -> Dict:
        """주문 상태 조회"""
        raw_to_use = broker_type or self.active_broker
        broker_to_use = self._normalize_broker_type(raw_to_use) if raw_to_use else None

        if not broker_to_use or broker_to_use not in self.brokers:
            return {}

        broker = self.brokers[broker_to_use]
        return broker.get_order_status(order_id)

    def get_account_info(self, broker_type: Optional[Union[BrokerType, str]] = None) -> Dict:
        """계좌 정보 조회"""
        raw_to_use = broker_type or self.active_broker
        broker_to_use = self._normalize_broker_type(raw_to_use) if raw_to_use else None

        if not broker_to_use or broker_to_use not in self.brokers:
            return {}

        broker = self.brokers[broker_to_use]
        return broker.get_account_info()

    def get_all_account_info(self) -> Dict[str, Dict]:
        """모든 증권사 계좌 정보 조회"""
        accounts = {}

        for broker_type, broker in self.brokers.items():
            is_conn = broker.is_connected() if callable(broker.is_connected) else bool(broker.is_connected)
            if is_conn:
                label = broker_type.value if isinstance(broker_type, BrokerType) else str(broker_type)
                accounts[label] = broker.get_account_info()

        return accounts

    def get_stock_quote(self, code: str, broker_type: Optional[Union[BrokerType, str]] = None) -> Dict:
        """주식 시세 조회"""
        raw_to_use = broker_type or self.active_broker
        broker_to_use = self._normalize_broker_type(raw_to_use) if raw_to_use else None

        if not broker_to_use or broker_to_use not in self.brokers:
            return {}

        broker = self.brokers[broker_to_use]
        return broker.get_stock_quote(code)

    def get_daily_chart(self, code: str, days: int = 20, broker_type: Optional[Union[BrokerType, str]] = None) -> List[Dict]:
        """일봉 차트 조회"""
        raw_to_use = broker_type or self.active_broker
        broker_to_use = self._normalize_broker_type(raw_to_use) if raw_to_use else None

        if not broker_to_use or broker_to_use not in self.brokers:
            return []

        broker = self.brokers[broker_to_use]
        return broker.get_daily_chart(code, days)

    def get_broker_status(self) -> Dict:
        """모든 증권사 상태 조회"""
        status = {}

        for broker_type, broker in self.brokers.items():
            is_conn = broker.is_connected() if callable(broker.is_connected) else bool(broker.is_connected)
            label = broker_type.value if isinstance(broker_type, BrokerType) else str(broker_type)
            status[label] = {
                "is_connected": is_conn,
                "account_number": getattr(broker, "account_number", ""),
                "simulation_mode": getattr(broker, "simulation_mode", False),
                "is_active": broker_type == self.active_broker,
            }

        return status

    def get_broker_info(self, broker_type: Union[BrokerType, str]) -> Dict:
        """증권사 정보 조회"""
        norm_key = self._normalize_broker_type(broker_type)
        if norm_key not in self.brokers:
            return {}

        broker = self.brokers[norm_key]
        return broker.get_broker_info()

    def get_all_brokers_info(self) -> Dict[str, Dict]:
        """모든 증권사 정보 조회"""
        infos = {}

        for broker_type, broker in self.brokers.items():
            label = broker_type.value if isinstance(broker_type, BrokerType) else str(broker_type)
            infos[label] = broker.get_broker_info()

        return infos
