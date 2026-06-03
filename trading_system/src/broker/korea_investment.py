"""한국투자증권 API 통합"""

import logging
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class KoreaInvestmentOrder:
    """한국투자증권 주문"""
    order_id: str
    code: str
    quantity: int
    price: float
    order_type: str  # 매수, 매도
    status: str
    timestamp: datetime


class KoreaInvestmentConnector:
    """한국투자증권 API 연동"""
    
    API_VERSION = "1.0"
    
    def __init__(self, account_number: Optional[str] = None):
        """
        한국투자증권 연동 초기화
        
        Args:
            account_number: 계좌번호
        """
        self.account_number = account_number or "0000000000"
        self.is_connected = False
        self.simulation_mode = True
        self.orders: Dict[str, KoreaInvestmentOrder] = {}
        self.positions: Dict[str, int] = {}  # 종목: 수량
        self.balance = 10000000  # 기본 잔액
        self.logger = logger
    
    def connect(self, account_number: str) -> bool:
        """
        한국투자증권 서버 연결
        
        Args:
            account_number: 계좌번호
            
        Returns:
            bool: 연결 성공 여부
        """
        self.account_number = account_number
        self.is_connected = True
        
        self.logger.info(f"Connecting to Korea Investment API (version {self.API_VERSION})...")
        self.logger.info(f"Simulated account initialized: {account_number}")
        self.logger.info("Connected to Korea Investment API (simulation mode)")
        
        return True
    
    def disconnect(self) -> bool:
        """연결 해제"""
        self.is_connected = False
        self.logger.info("Disconnected from Korea Investment API")
        return True
    
    def get_account_info(self) -> Dict:
        """계좌 정보 조회"""
        return {
            'account_number': self.account_number,
            'balance': self.balance,
            'positions': self.positions,
            'total_value': self.balance + sum(self.positions.values()),
            'timestamp': datetime.now()
        }
    
    def get_daily_chart(self, code: str, days: int = 20) -> List[Dict]:
        """일봉 차트 조회"""
        import random
        
        chart = []
        price = 100.0
        
        for i in range(days):
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
    
    def place_order(self, code: str, quantity: int, price: float, 
                   order_type: str) -> str:
        """
        주문 접수
        
        Args:
            code: 종목코드
            quantity: 수량
            price: 가격
            order_type: 주문유형 (매수/매도)
            
        Returns:
            str: 주문번호
        """
        order_id = f"KIS_{datetime.now().timestamp()}"
        
        order = KoreaInvestmentOrder(
            order_id=order_id,
            code=code,
            quantity=quantity,
            price=price,
            order_type=order_type,
            status='0',  # 접수
            timestamp=datetime.now()
        )
        
        self.orders[order_id] = order
        
        self.logger.info(f"Order placed: {order_id} {order_type} "
                        f"{quantity}주 @ {price:,.0f}")
        
        return order_id
    
    def cancel_order(self, order_id: str) -> bool:
        """주문 취소"""
        if order_id in self.orders:
            del self.orders[order_id]
            self.logger.info(f"Order cancelled: {order_id}")
            return True
        return False
    
    def get_order_status(self, order_id: str) -> Dict:
        """주문 상태 조회"""
        if order_id in self.orders:
            order = self.orders[order_id]
            return {
                'order_id': order.order_id,
                'code': order.code,
                'quantity': order.quantity,
                'price': order.price,
                'order_type': order.order_type,
                'status': order.status,
                'timestamp': order.timestamp
            }
        return {}
