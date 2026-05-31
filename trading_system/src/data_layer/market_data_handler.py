"""Market Data Handler - 실시간 시세 수신 및 처리"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Callable
import logging

logger = logging.getLogger(__name__)


@dataclass
class MarketData:
    """시장 데이터 모델"""
    symbol: str
    price: float
    bid: float
    ask: float
    volume: int
    timestamp: datetime
    
    def __repr__(self):
        return f"MarketData({self.symbol}, price={self.price}, bid={self.bid}, ask={self.ask}, vol={self.volume})"


class MarketDataHandler:
    """실시간 시세 수신 및 관리"""
    
    def __init__(self):
        self.market_data_dict = {}
        self.subscribers: List[Callable] = []
        self.logger = logger
        
    def subscribe(self, callback: Callable):
        """데이터 변경 구독"""
        self.subscribers.append(callback)
        self.logger.info(f"Subscribed callback: {callback.__name__}")
        
    def publish_market_data(self, data: MarketData):
        """시장 데이터 발행 (모든 구독자에게 알림)"""
        self.market_data_dict[data.symbol] = data
        self.logger.debug(f"Market data published: {data}")
        
        # 모든 구독자에게 알림
        for callback in self.subscribers:
            try:
                callback(data)
            except Exception as e:
                self.logger.error(f"Callback error: {e}")
    
    def get_market_data(self, symbol: str) -> MarketData | None:
        """특정 종목의 최신 시장 데이터 조회"""
        return self.market_data_dict.get(symbol)
    
    def get_all_market_data(self) -> dict:
        """모든 시장 데이터 조회"""
        return self.market_data_dict.copy()
    
    def simulate_api_call(self, symbol: str, price: float, bid: float, ask: float, volume: int):
        """증권사 API 호출 시뮬레이션"""
        data = MarketData(
            symbol=symbol,
            price=price,
            bid=bid,
            ask=ask,
            volume=volume,
            timestamp=datetime.now()
        )
        self.publish_market_data(data)
        return data
