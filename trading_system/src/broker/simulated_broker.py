import logging
import random
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class BrokerOrder:
    order_id: str
    code: str
    quantity: int
    price: float
    order_type: str
    status: str
    timestamp: datetime


class SimulatedBrokerBase:
    API_VERSION = "1.0"
    BROKER_NAME = "Base"
    BROKER_CODE = "BASE"
    ORDER_PREFIX = "BR"

    def __init__(self, account_number: Optional[str] = None):
        self.account_number = account_number or "0000000000"
        self.is_connected = False
        self.simulation_mode = True
        self.orders: Dict[str, BrokerOrder] = {}
        self.positions: Dict[str, int] = {}
        self.balance = 10000000
        self.logger = logger

    def connect(self, account_number: str) -> bool:
        self.account_number = account_number
        self.is_connected = True
        self.logger.info(f"Connecting to {self.BROKER_NAME} API (version {self.API_VERSION})...")
        self.logger.info(f"Simulated account initialized: {account_number}")
        self.logger.info(f"Connected to {self.BROKER_NAME} API (simulation mode)")
        return True

    def disconnect(self) -> bool:
        self.is_connected = False
        self.logger.info(f"Disconnected from {self.BROKER_NAME} API")
        return True

    def get_account_info(self) -> Dict:
        return {
            'account_number': self.account_number,
            'balance': self.balance,
            'positions': self.positions,
            'total_value': self.balance + sum(self.positions.values()),
            'timestamp': datetime.now()
        }

    def get_daily_chart(self, code: str, days: int = 20) -> List[Dict]:
        chart = []
        price = 100.0
        for _ in range(days):
            change = random.uniform(-0.02, 0.02)
            bar = {
                'date': datetime.now().strftime('%Y-%m-%d'),
                'open': price,
                'high': price * (1 + abs(change)),
                'low': price * (1 - abs(change)),
                'close': price * (1 + change),
                'volume': random.randint(1000000, 10000000)
            }
            chart.append(bar)
            price = bar['close']
        return chart

    def place_order(self, code: str, quantity: int, price: float, order_type: str) -> str:
        order_id = f"{self.ORDER_PREFIX}_{datetime.timestamp(datetime.now())}"
        order = BrokerOrder(
            order_id=order_id,
            code=code,
            quantity=quantity,
            price=price,
            order_type=order_type,
            status='0',
            timestamp=datetime.now()
        )
        self.orders[order_id] = order
        self.logger.info(f"Order placed: {order_id} {order_type} {quantity}주 @ {price:,.0f}")
        return order_id

    def cancel_order(self, order_id: str) -> bool:
        if order_id in self.orders:
            del self.orders[order_id]
            self.logger.info(f"Order cancelled: {order_id}")
            return True
        return False

    def get_order_status(self, order_id: str) -> Dict:
        if order_id in self.orders:
            order = self.orders[order_id]
            return {
                'order_id': order.order_id,
                'code': order.code,
                'quantity': order.quantity,
                'price': order.price,
                'order_type': order.order_type,
                'status': order.status,
                'timestamp': order.timestamp,
                'filled_quantity': 0
            }
        return {}

    def get_stock_quote(self, code: str) -> Dict:
        return {
            'code': code,
            'name': f'Stock_{code}',
            'current_price': random.uniform(50, 150),
            'bid': random.uniform(49, 149),
            'ask': random.uniform(51, 151),
            'volume': random.randint(1000000, 10000000),
            'timestamp': datetime.now()
        }

    def subscribe_realtime(self, code: str, callback) -> bool:
        self.logger.info(f"Subscribed to realtime for {code}")
        return True

    def unsubscribe_realtime(self, code: str) -> bool:
        self.logger.info(f"Unsubscribed from realtime for {code}")
        return True

    def get_broker_info(self) -> Dict:
        return {
            'name': self.BROKER_NAME,
            'code': self.BROKER_CODE,
            'api_version': self.API_VERSION,
            'simulation_mode': self.simulation_mode
        }
