"""Order Management System - 주문 처리 및 관리"""

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Callable, Dict, List
import numpy as np

from src.utils import EventBus

logger = logging.getLogger(__name__)


def calculate_almgren_chriss_impact(
    order_quantity: int,
    adv: float,
    daily_volatility: float,
    spread: float = 0.001,
    gamma: float = 0.1
) -> float:
    """
    Computes non-linear Almgren-Chriss market impact cost (pct of price).
    Formula: Cost = 0.5 * spread + gamma * daily_volatility * sqrt(order_quantity / max(adv, 1.0))
    """
    sp = float(spread) if np.isfinite(spread) else 0.001
    try:
        adv_f = float(adv)
        qty_f = float(order_quantity)
        if adv_f <= 0 or qty_f <= 0 or not np.isfinite(adv_f) or not np.isfinite(qty_f):
            return 0.5 * sp + 0.005
    except (ValueError, TypeError):
        return 0.5 * sp + 0.005

    vol = float(daily_volatility) if np.isfinite(daily_volatility) else 0.02
    ratio = max(0.0, qty_f) / max(adv_f, 1.0)
    vol_clean = max(1e-4, vol)
    impact = 0.5 * sp + gamma * vol_clean * float(np.sqrt(ratio))
    if np.isnan(impact) or np.isinf(impact):
        return 0.5 * sp + 0.005
    return float(np.clip(impact, 0.0005, 0.05))



class OrderType(Enum):
    """주문 유형"""

    BUY = "BUY"
    SELL = "SELL"
    STOP_LOSS = "STOP_LOSS"  # 손절매 주문
    TAKE_PROFIT = "TAKE_PROFIT"  # 익절매 주문


class OrderStatus(Enum):
    """주문 상태"""

    PENDING = "PENDING"  # 대기
    SUBMITTED = "SUBMITTED"  # 제출됨
    EXECUTED = "EXECUTED"  # 체결됨
    PARTIALLY_FILLED = "PARTIALLY_FILLED"  # 부분 체결
    CANCELLED = "CANCELLED"  # 취소됨
    REJECTED = "REJECTED"  # 거절됨


@dataclass
class Order:
    """주문 정보"""

    symbol: str
    order_type: OrderType
    quantity: int
    price: float
    signal_name: str = ""
    order_id: str = field(default_factory=lambda: "")
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    executed_at: datetime | None = None
    # Stop loss / Take profit related fields
    trigger_price: float | None = None  # 발동 가격 (stop loss/take profit용)
    parent_order_id: str | None = None  # 연결된 진입 주문 ID
    broker_order_id: str = ""  # 브로커 측 주문 ID (모의투자 연동)

    def __post_init__(self):
        if not self.order_id:
            self.order_id = f"ORD_{self.created_at.timestamp()}_{uuid.uuid4().hex[:6]}"

    def is_stop_order(self) -> bool:
        """손절/익절 주문인지 확인"""
        return self.order_type in (OrderType.STOP_LOSS, OrderType.TAKE_PROFIT)

    def is_filled(self) -> bool:
        return self.filled_quantity >= self.quantity

    def get_remaining_quantity(self) -> int:
        return self.quantity - self.filled_quantity


class OrderManagementSystem:
    """주문 관리 시스템"""

    def __init__(self, event_bus: EventBus | None = None) -> None:
        self.orders: Dict[str, Order] = {}
        self.order_history: List[Order] = []
        self.event_bus = event_bus
        self.logger = logger
        self.subscribers: List[Callable] = []
        self.unfilled_monitor_enabled = True

    def subscribe(self, callback: Callable) -> None:
        """주문 상태 변경 구독"""
        self.subscribers.append(callback)

    def create_order(
        self, symbol: str, order_type: OrderType, quantity: int, price: float, signal_name: str = ""
    ) -> Order:
        """주문 생성"""
        try:
            qty = max(0, int(quantity)) if (quantity is not None and np.isfinite(float(quantity))) else 0
        except (ValueError, TypeError):
            qty = 0
        try:
            p = max(0.0, float(price)) if (price is not None and np.isfinite(float(price))) else 0.0
        except (ValueError, TypeError):
            p = 0.0
        order = Order(symbol=symbol, order_type=order_type, quantity=qty, price=p, signal_name=signal_name)
        self.orders[order.order_id] = order
        self.logger.info(f"Order created: {order.order_id} {order_type.value} {symbol} x{qty}")
        return order

    async def submit_order(self, order: Order) -> bool:
        """주문 제출"""
        if order.order_id not in self.orders:
            self.logger.error(f"Order not found: {order.order_id}")
            return False

        order.status = OrderStatus.SUBMITTED
        await self._notify_subscribers_async(order)
        self.logger.info(f"Order submitted: {order.order_id}")
        return True

    async def execute_order(self, order_id: str, filled_quantity: int | None = None) -> bool:
        """주문 체결"""
        if order_id not in self.orders:
            self.logger.error(f"Order not found: {order_id}")
            return False

        order = self.orders[order_id]

        if filled_quantity is None:
            filled_quantity = order.quantity

        if filled_quantity > order.quantity:
            self.logger.warning("Filled quantity exceeds order quantity")
            filled_quantity = order.quantity

        order.filled_quantity = filled_quantity
        order.executed_at = datetime.now()

        if order.filled_quantity >= order.quantity:
            order.status = OrderStatus.EXECUTED
        else:
            order.status = OrderStatus.PARTIALLY_FILLED

        await self._notify_subscribers_async(order)
        self.logger.info(f"Order executed: {order_id} filled={filled_quantity}")
        return True

    async def cancel_order(self, order_id: str) -> bool:
        """주문 취소"""
        if order_id not in self.orders:
            self.logger.error(f"Order not found: {order_id}")
            return False

        order = self.orders[order_id]

        if order.status in [OrderStatus.EXECUTED, OrderStatus.CANCELLED]:
            self.logger.warning(f"Cannot cancel order in status: {order.status}")
            return False

        order.status = OrderStatus.CANCELLED
        await self._notify_subscribers_async(order)
        self.logger.info(f"Order cancelled: {order_id}")
        return True

    def get_unfilled_orders(self) -> List[Order]:
        """미체결 주문 조회"""
        unfilled = [
            o
            for o in self.orders.values()
            if o.status in [OrderStatus.PENDING, OrderStatus.SUBMITTED, OrderStatus.PARTIALLY_FILLED]
        ]
        return unfilled

    def monitor_unfilled_orders(self):
        """미체결 주문 감시"""
        if not self.unfilled_monitor_enabled:
            return

        unfilled = self.get_unfilled_orders()
        if unfilled:
            self.logger.warning(f"Unfilled orders detected: {len(unfilled)}")
            for order in unfilled:
                age = (datetime.now() - order.created_at).total_seconds() / 60
                self.logger.warning(
                    f"  Order {order.order_id}: {age:.1f} minutes old, {order.get_remaining_quantity()} remaining"
                )

    def get_order(self, order_id: str) -> Order | None:
        """주문 조회"""
        return self.orders.get(order_id)

    def get_order_history(self, symbol: str | None = None) -> List[Order]:
        """주문 이력 조회"""
        history = [o for o in self.orders.values()]
        if symbol:
            history = [o for o in history if o.symbol == symbol]
        return history

    def create_stop_loss_order(
        self, symbol: str, quantity: int, trigger_price: float, parent_order_id: str | None = None
    ) -> Order:
        """손절매 주문 생성"""
        try:
            qty = max(0, int(quantity)) if (quantity is not None and np.isfinite(float(quantity))) else 0
        except (ValueError, TypeError):
            qty = 0
        try:
            tp = max(0.0, float(trigger_price)) if (trigger_price is not None and np.isfinite(float(trigger_price))) else 0.0
        except (ValueError, TypeError):
            tp = 0.0
        order = Order(
            symbol=symbol,
            order_type=OrderType.STOP_LOSS,
            quantity=qty,
            price=tp,  # Stop loss 주문의 price는 trigger_price
            trigger_price=tp,
            parent_order_id=parent_order_id,
        )
        self.orders[order.order_id] = order
        self.logger.info(
            f"Stop loss order created: {order.order_id} {symbol} x{qty} @ trigger={tp:,.0f}"
        )
        return order

    def create_take_profit_order(
        self, symbol: str, quantity: int, trigger_price: float, parent_order_id: str | None = None
    ) -> Order:
        """익절매 주문 생성"""
        order = Order(
            symbol=symbol,
            order_type=OrderType.TAKE_PROFIT,
            quantity=quantity,
            price=trigger_price,
            trigger_price=trigger_price,
            parent_order_id=parent_order_id,
        )
        self.orders[order.order_id] = order
        self.logger.info(
            f"Take profit order created: {order.order_id} {symbol} x{quantity} @ trigger={trigger_price:,.0f}"
        )
        return order

    def check_and_trigger_stop_orders(self, symbol: str, current_price: float) -> List[Order]:
        """현재 가격 기준으로 발동되어야 할 stop loss/take profit 주문 확인 및 발동"""
        triggered = []
        for order in self.orders.values():
            if order.symbol != symbol:
                continue
            if order.status not in (OrderStatus.PENDING, OrderStatus.SUBMITTED):
                continue
            if not order.is_stop_order() or order.trigger_price is None:
                continue

            should_trigger = False
            if order.order_type == OrderType.STOP_LOSS:
                # Stop loss: 현재 가격이 트리거 가격 이하로 내려가면 발동
                if current_price <= order.trigger_price:
                    should_trigger = True
            elif order.order_type == OrderType.TAKE_PROFIT:
                # Take profit: 현재 가격이 트리거 가격 이상으로 올라가면 발동
                if current_price >= order.trigger_price:
                    should_trigger = True

            if should_trigger:
                # 시장가로 체결 처리
                order.status = OrderStatus.SUBMITTED
                triggered.append(order)
                self.logger.warning(
                    f"Stop order triggered: {order.order_id} {order.order_type.value} "
                    f"{symbol} @ {current_price:,.0f} (trigger={order.trigger_price:,.0f})"
                )

        return triggered

    def get_stop_orders(self, symbol: str | None = None) -> List[Order]:
        """손절/익절 주문 조회"""
        orders = [o for o in self.orders.values() if o.is_stop_order()]
        if symbol:
            orders = [o for o in orders if o.symbol == symbol]
        return orders

    def cancel_stop_orders(self, symbol: str) -> int:
        """특정 종목의 모든 손절/익절 주문 취소"""
        cancelled = 0
        for order in self.orders.values():
            if order.symbol != symbol:
                continue
            if not order.is_stop_order():
                continue
            if order.status in (OrderStatus.PENDING, OrderStatus.SUBMITTED):
                order.status = OrderStatus.CANCELLED
                cancelled += 1
                self.logger.info(f"Stop order cancelled: {order.order_id}")
        return cancelled

    async def _notify_subscribers_async(self, order: Order):
        """구독자에게 비동기 알림"""
        if self.event_bus:
            self.event_bus.publish("order_status", order)

        for callback in self.subscribers:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(order)
                else:
                    callback(order)
            except Exception as e:
                self.logger.error(f"Subscriber callback error: {e}")
