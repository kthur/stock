"""Kiwoom API Integration - 키움증권 API 통합"""

import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Callable, Dict, List, Optional, cast

logger = logging.getLogger(__name__)


class KiwoomOrderType(Enum):
    """키움증권 주문 타입"""

    SEND = 1  # 매수
    CANCEL_SEND = 2  # 매수 취소
    BUY = 3  # 매수 체결
    SELL = 4  # 매도
    CANCEL_SELL = 5  # 매도 취소
    SELL_EXECUTION = 6  # 매도 체결


class KiwoomOrderStatus(Enum):
    """키움증권 주문 상태"""

    PENDING = "0"  # 대기
    SUBMITTED = "1"  # 접수
    CONFIRMED = "2"  # 확인
    PARTIAL = "3"  # 부분 체결
    EXECUTION = "4"  # 체결
    CANCELLED = "5"  # 취소
    REJECTED = "6"  # 거절


class KiwoomConnector:
    """키움증권 API 커넥터"""

    def __init__(self, api_version: str = "1.0"):
        """
        초기화

        Args:
            api_version: API 버전
        """
        self.api_version = api_version
        self.logger = logger
        self.is_connected = False
        self.account_number: Optional[str] = None
        self.realtime_callbacks: Dict[str, List[Callable]] = {}

        # 시뮬레이션 모드 (실제 API 없을 때)
        self.simulation_mode = True
        self.simulated_accounts: Dict = {}
        self.simulated_orders: Dict = {}

    def connect(self, account_number: str) -> bool:
        """
        API 연결

        Args:
            account_number: 계좌번호

        Returns:
            연결 성공 여부
        """
        try:
            self.logger.info(f"Connecting to Kiwoom API (version {self.api_version})...")
            safe_acc = str(account_number) if account_number is not None else ""

            if self.simulation_mode:
                # 시뮬레이션 모드
                self.is_connected = True
                self.account_number = safe_acc
                self._init_simulated_account()
                self.logger.info("Connected to Kiwoom API (simulation mode)")
            else:
                # 32비트 마이크로서비스로 ZeroMQ 통신
                import zmq

                self.context = zmq.Context()
                self.socket = self.context.socket(zmq.REQ)
                self.socket.connect("tcp://127.0.0.1:5555")
                # 테스트 핑
                self.socket.send_json({"command": "ping"})
                self.socket.recv_json()

                self.socket.send_json({"command": "connect", "args": {"account_number": safe_acc}})
                res: dict = cast(dict, self.socket.recv_json())
                if res.get("status") == "success":
                    self.is_connected = bool(res.get("data", False))
                    self.account_number = safe_acc
                    self.logger.info("Connected to Kiwoom 32-bit Microservice via ZeroMQ")
                else:
                    self.is_connected = False

            return self.is_connected

        except Exception as e:
            self.logger.error(f"Connection failed: {e!s}")
            return False

    def disconnect(self) -> bool:
        """API 연결 해제"""
        self.is_connected = False
        self.logger.info("Disconnected from Kiwoom API")
        return True

    def get_account_balance(self) -> Dict:
        """계좌 잔고 조회"""
        if not self.is_connected or not self.account_number:
            self.logger.error("Not connected to Kiwoom API")
            return {}

        if self.simulation_mode:
            return dict(self.simulated_accounts.get(self.account_number, {}))

        # 실제 API 호출
        # ...
        return {}

    def get_holdings(self) -> List[Dict]:
        """보유 종목 조회"""
        if not self.is_connected:
            self.logger.error("Not connected to Kiwoom API")
            return []

        if self.simulation_mode:
            account = dict(self.simulated_accounts.get(self.account_number, {}))
            return list(account.get("holdings", []))

        # 실제 API 호출
        # ...
        return []

    def get_stock_quote(self, code: str) -> Dict:
        """주식 시세 조회"""
        try:
            if self.simulation_mode:
                # 시뮬레이션 시세
                return {
                    "code": code,
                    "name": f"Stock_{code}",
                    "price": 100.0,
                    "bid": 99.95,
                    "ask": 100.05,
                    "volume": 1000000,
                    "timestamp": datetime.now(),
                }

            # 실제 API 호출
            # ...
            return {}

        except Exception as e:
            self.logger.error(f"Failed to get quote for {code}: {e!s}")
            return {}

    def place_order(self, code: str, quantity: int, price: float, order_type: str = "매수") -> str:
        """
        주문 접수

        Args:
            code: 종목 코드
            quantity: 수량
            price: 가격
            order_type: 주문 유형 (매수/매도)

        Returns:
            주문 번호
        """
        import time, math
        try:
            q = max(0, int(quantity)) if quantity is not None else 0
            if q <= 0:
                self.logger.warning(f"Invalid order quantity ({quantity}) for {code}")
                return ""

            try:
                p = float(price) if (price is not None and math.isfinite(float(price))) else 0.0
            except (ValueError, TypeError):
                p = 0.0
            p = max(0.0, p)

            order_id = f"KW_ORD_{int(time.time() * 1000)}"

            if self.simulation_mode:
                order = {
                    "order_id": order_id,
                    "code": str(code),
                    "quantity": q,
                    "price": p,
                    "order_type": str(order_type),
                    "status": KiwoomOrderStatus.SUBMITTED.value,
                    "timestamp": datetime.now(),
                    "filled_quantity": 0,
                }
                self.simulated_orders[order_id] = order
                self.logger.info(f"Order placed: {order_id} {order_type} {q}주 @ {p:,.0f}")

            # 주문 콜백 호출
            self._trigger_callback(
                "order", {"order_id": order_id, "code": str(code), "quantity": q, "price": p, "status": "SUBMITTED"}
            )

            return order_id

        except Exception as e:
            self.logger.error(f"Failed to place order: {e!s}")
            return ""

    def cancel_order(self, order_id: str) -> bool:
        """
        주문 취소

        Args:
            order_id: 주문 번호

        Returns:
            취소 성공 여부
        """
        try:
            if self.simulation_mode:
                if order_id in self.simulated_orders:
                    self.simulated_orders[order_id]["status"] = KiwoomOrderStatus.CANCELLED.value
                    self.logger.info(f"Order cancelled: {order_id}")

                    self._trigger_callback("order", {"order_id": order_id, "status": "CANCELLED"})
                    return True

            return False

        except Exception as e:
            self.logger.error(f"Failed to cancel order: {e!s}")
            return False

    def get_order_status(self, order_id: str) -> Dict:
        """주문 상태 조회"""
        if self.simulation_mode:
            return dict(self.simulated_orders.get(order_id, {}))

        # 실제 API 호출
        # ...
        return {}

    def get_daily_chart(self, code: str, days: int = 20) -> List[Dict]:
        """일봉 차트 조회"""
        try:
            if self.simulation_mode:
                # 시뮬레이션 데이터
                charts = []
                current_price = 100.0
                end_date = datetime.now()
                start_date = end_date - timedelta(days=days)
                current_date = start_date

                while current_date <= end_date:
                    if current_date.weekday() < 5:  # 평일만
                        chart = {
                            "date": current_date,
                            "open": current_price,
                            "high": current_price * 1.02,
                            "low": current_price * 0.98,
                            "close": current_price * (0.99 + 0.02),
                            "volume": 1000000,
                        }
                        charts.append(chart)
                        current_price = float(cast(float, chart["close"]))

                    current_date += timedelta(days=1)

                self.logger.info(f"Retrieved {len(charts)} daily charts for {code}")
                return charts

            # 실제 API 호출
            # ...
            return []

        except Exception as e:
            self.logger.error(f"Failed to get chart: {e!s}")
            return []

    def subscribe_realtime(self, code: str, callback: Callable) -> bool:
        """
        실시간 데이터 구독

        Args:
            code: 종목 코드
            callback: 콜백 함수

        Returns:
            구독 성공 여부
        """
        try:
            if code not in self.realtime_callbacks:
                self.realtime_callbacks[code] = []

            self.realtime_callbacks[code].append(callback)
            self.logger.info(f"Subscribed to realtime data for {code}")

            return True

        except Exception as e:
            self.logger.error(f"Failed to subscribe: {e!s}")
            return False

    def unsubscribe_realtime(self, code: str) -> bool:
        """
        실시간 데이터 구독 해제

        Args:
            code: 종목 코드

        Returns:
            해제 성공 여부
        """
        try:
            if code in self.realtime_callbacks:
                del self.realtime_callbacks[code]
                self.logger.info(f"Unsubscribed from realtime data for {code}")

            return True

        except Exception as e:
            self.logger.error(f"Failed to unsubscribe: {e!s}")
            return False

    def _trigger_callback(self, event_type: str, data: Dict):
        """콜백 트리거"""
        code = data.get("code")

        if code and code in self.realtime_callbacks:
            for callback in self.realtime_callbacks[code]:
                try:
                    callback(data)
                except Exception as e:
                    self.logger.error(f"Callback error: {e!s}")

    def _init_simulated_account(self):
        """시뮬레이션 계좌 초기화"""
        self.simulated_accounts[self.account_number] = {
            "account_number": self.account_number,
            "cash": 1000000.0,
            "holdings": [],
            "total_value": 1000000.0,
        }
        self.logger.info(f"Simulated account initialized: {self.account_number}")

    def get_connection_status(self) -> Dict:
        """연결 상태 조회"""
        return {
            "is_connected": self.is_connected,
            "account_number": self.account_number,
            "api_version": self.api_version,
            "simulation_mode": self.simulation_mode,
            "timestamp": datetime.now().isoformat(),
        }

    def get_account_info(self) -> Dict:
        """계좌 정보 조회 (get_account_balance와 호환성)"""
        if not self.is_connected or not self.account_number:
            self.logger.error("Not connected to Kiwoom API")
            return {}

        if self.simulation_mode:
            account = self.simulated_accounts.get(self.account_number, {})
            return {
                "account_number": self.account_number,
                "balance": account.get("cash", 0),
                "positions": account.get("holdings", {}),
                "total_value": account.get("total_value", 0),
                "timestamp": datetime.now(),
            }

        # 실제 API 호출
        return {}

    def get_broker_info(self) -> Dict:
        """증권사 정보"""
        return {
            "name": "키움증권",
            "code": "KIWOOM",
            "api_version": self.api_version,
            "simulation_mode": self.simulation_mode,
        }
