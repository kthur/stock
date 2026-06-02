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
    
    def __init__(self, event_bus=None):
        self.market_data_dict = {}
        self.subscribers: List[Callable] = []
        self.event_bus = event_bus
        self.logger = logger
        
    def subscribe(self, callback: Callable):
        """데이터 변경 구독"""
        self.subscribers.append(callback)
        callback_name = callback.__name__ if hasattr(callback, '__name__') else str(callback)
        self.logger.info(f"Subscribed callback: {callback_name}")
        
    def publish_market_data(self, data: MarketData):
        """시장 데이터 발행 (모든 구독자에게 알림)"""
        self.market_data_dict[data.symbol] = data
        self.logger.debug(f"Market data published: {data}")
        
        # 이벤트 버스로 전송
        if self.event_bus:
            self.event_bus.publish("market_data", data)
            
        # 모든 구독자에게 알림 (하위 호환성)
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

    def fetch_live_data(self, symbol: str) -> MarketData | None:
        """yfinance를 통해 실제 실시간 시세 데이터를 조회하고 이벤트로 전송"""
        try:
            import yfinance as yf
            ticker = yf.Ticker(symbol)
            fast = ticker.fast_info
            price = fast.last_price
            
            # fast_info 데이터 획득 실패 시 1일 1분 분봉을 통해 백업 데이터 획득
            if price is None or price <= 0:
                hist = ticker.history(period="1d", interval="1m")
                if not hist.empty:
                    price = float(hist['Close'].iloc[-1])
                    volume = int(hist['Volume'].iloc[-1])
                else:
                    raise ValueError("No price data returned from yfinance")
            else:
                volume = int(fast.last_volume) if fast.last_volume else 100000
                
            bid = round(price - 0.05, 2)
            ask = round(price + 0.05, 2)
            
            data = MarketData(
                symbol=symbol,
                price=price,
                bid=bid,
                ask=ask,
                volume=volume,
                timestamp=datetime.now()
            )
            self.publish_market_data(data)
            self.logger.info(f"Live data fetched from yfinance for {symbol}: ${price:.2f}")
            return data
            
        except Exception as e:
            self.logger.error(f"Failed to fetch live data from yfinance for {symbol}: {e}. Falling back to simulation.")
            # 실패 시 기존 데이터를 소폭 변동시켜 모의 데이터 생성
            existing = self.get_market_data(symbol)
            base_price = existing.price if existing else 150.0
            import random
            price = round(base_price * (1 + random.uniform(-0.002, 0.002)), 2)
            return self.simulate_api_call(symbol, price, price - 0.05, price + 0.05, 5000000)

