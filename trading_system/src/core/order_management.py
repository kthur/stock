"""Order Management System - 주문 처리 및 관리"""

import logging
import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Callable

from src.utils import EventBus

logger = logging.getLogger(__name__)


class OrderType(Enum):
    """주문 유형"""
    BUY = "BUY"
    SELL = "SELL"


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
    order_id: str = field(default_factory=lambda: "")
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    executed_at: datetime | None = None
    
    def __post_init__(self):
        if not self.order_id:
            self.order_id = f"ORD_{self.created_at.timestamp()}"
    
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
    
    def create_order(self, symbol: str, order_type: OrderType, 
                    quantity: int, price: float) -> Order:
        """주문 생성"""
        order = Order(
            symbol=symbol,
            order_type=order_type,
            quantity=quantity,
            price=price
        )
        self.orders[order.order_id] = order
        self.logger.info(f"Order created: {order.order_id} {order_type.value} {symbol} x{quantity}")
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
            self.logger.warning(f"Filled quantity exceeds order quantity")
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
        unfilled = [o for o in self.orders.values() 
                   if o.status in [OrderStatus.PENDING, OrderStatus.SUBMITTED, OrderStatus.PARTIALLY_FILLED]]
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
                self.logger.warning(f"  Order {order.order_id}: {age:.1f} minutes old, {order.get_remaining_quantity()} remaining")
    
    def get_order(self, order_id: str) -> Order | None:
        """주문 조회"""
        return self.orders.get(order_id)
    
    def get_order_history(self, symbol: str | None = None) -> List[Order]:
        """주문 이력 조회"""
        history = [o for o in self.orders.values()]
        if symbol:
            history = [o for o in history if o.symbol == symbol]
        return history
    
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

