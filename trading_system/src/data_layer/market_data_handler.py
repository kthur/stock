"""Market Data Handler - 실시간 시세 수신 및 처리"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Callable, Any
import logging
import time
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

class RateLimiter:
    """토큰 버킷 알고리즘 기반 API 호출 제한기"""
    def __init__(self, rate_limit: int, time_window: float = 1.0):
        self.rate_limit = rate_limit
        self.time_window = time_window
        self.tokens = rate_limit
        self.last_updated = time.time()
        
    def acquire(self):
        now = time.time()
        elapsed = now - self.last_updated
        self.tokens += elapsed * (self.rate_limit / self.time_window)
        if self.tokens > self.rate_limit:
            self.tokens = self.rate_limit
        self.last_updated = now
        
        if self.tokens >= 1:
            self.tokens -= 1
            return True
        return False
        
    def wait(self):
        while not self.acquire():
            time.sleep(0.1)

class CircuitBreaker:
    """연속 실패 시 외부 호출을 차단하는 서킷 브레이커"""
    def __init__(self, max_failures: int = 5, reset_timeout: float = 60.0):
        self.max_failures = max_failures
        self.reset_timeout = reset_timeout
        self.failures = 0
        self.last_failure_time = 0
        self.is_open = False
        
    def record_failure(self):
        self.failures += 1
        self.last_failure_time = time.time()
        if self.failures >= self.max_failures:
            self.is_open = True
            
    def record_success(self):
        self.failures = 0
        self.is_open = False
        
    def check_state(self):
        if self.is_open:
            if time.time() - self.last_failure_time > self.reset_timeout:
                self.is_open = False
                self.failures = 0
                return True
            return False
        return True


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
        
        # 1초에 최대 5번 요청 허용
        self.rate_limiter = RateLimiter(rate_limit=5, time_window=1.0)
        # 5번 연속 실패 시 60초간 차단
        self.circuit_breaker = CircuitBreaker(max_failures=5, reset_timeout=60.0)
        
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

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
    def _fetch_yf_with_retry(self, symbol: str):
        if not self.circuit_breaker.check_state():
            raise Exception("Circuit breaker is OPEN. API calls are temporarily blocked.")
            
        self.rate_limiter.wait()
        
        import yfinance as yf
        try:
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
                
            self.circuit_breaker.record_success()
            return price, volume
        except Exception as e:
            self.circuit_breaker.record_failure()
            raise e

    def fetch_live_data(self, symbol: str) -> MarketData | None:
        """yfinance를 통해 실제 실시간 시세 데이터를 조회하고 이벤트로 전송"""
        try:
            price, volume = self._fetch_yf_with_retry(symbol)
            
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

    def fetch_historical_data(self, symbol: str, period: str = "10y") -> List[Any]:
        """yfinance를 통해 과거 데이터를 가져오고 로컬 캐시를 활용하여 반환 속도를 향상시킵니다."""
        import yfinance as yf
        import pandas as pd
        import os
        from src.analysis.backtest import PriceBar
        from datetime import timedelta

        # 캐시 디렉토리 설정
        cache_dir = os.path.join(os.getcwd(), 'data', 'cache')
        os.makedirs(cache_dir, exist_ok=True)

        # 특수 문자(_) 등 제거 (파일 시스템 안전을 위해)
        safe_symbol = symbol.replace('/', '_').replace('\\', '_')
        cache_file = os.path.join(cache_dir, f"{safe_symbol}_{period}.parquet")

        hist = None
        use_cache = False

        # 1. 캐시 파일이 존재하는지, 하루가 지나지 않았는지 확인
        if os.path.exists(cache_file):
            file_mod_time = datetime.fromtimestamp(os.path.getmtime(cache_file))
            if datetime.now() - file_mod_time < timedelta(hours=24):
                try:
                    hist = pd.read_parquet(cache_file)
                    use_cache = True
                    self.logger.debug(f"Loaded {symbol} ({period}) from local cache.")
                except Exception as e:
                    self.logger.warning(f"Failed to read cache for {symbol}: {e}")
                    hist = None

        if not use_cache or hist is None:
            if not self.circuit_breaker.check_state():
                self.logger.error(f"Circuit breaker is OPEN. Blocked fetch for {symbol}")
                return []

            self.rate_limiter.wait()
            try:
                ticker = yf.Ticker(symbol)

                # yfinance는 15y, 20y, 30y를 네이티브 period로 지원하지 않으므로 직접 날짜를 계산
                if period in ["15y", "20y", "30y"]:
                    years = int(period.replace("y", ""))
                    start_date = datetime.now() - timedelta(days=365 * years)
                    hist = ticker.history(start=start_date.strftime("%Y-%m-%d"))
                else:
                    hist = ticker.history(period=period)

                if hist.empty:
                    self.logger.warning(f"No historical data found for {symbol}")
                    self.circuit_breaker.record_success()
                    return []

                # NaN 값 정제: Open, High, Low, Close 중 하나라도 NaN인 행 제거
                hist = hist.dropna(subset=['Open', 'High', 'Low', 'Close'])

                if hist.empty:
                    self.logger.warning(f"No historical data found after filtering NaNs for {symbol}")
                    self.circuit_breaker.record_success()
                    return []

                self.circuit_breaker.record_success()
                # 2. 새로 받아온 데이터를 Parquet로 캐시 저장
                try:
                    hist.to_parquet(cache_file)
                    self.logger.debug(f"Saved {symbol} ({period}) to local cache.")
                except Exception as e:
                    self.logger.warning(f"Failed to save cache for {symbol}: {e}")

            except Exception as e:
                self.circuit_breaker.record_failure()
                self.logger.error(f"Failed to fetch historical data for {symbol}: {e}")
                return []
        price_bars = []
        for date, row in hist.iterrows():
            bar = PriceBar(
                timestamp=date.to_pydatetime() if hasattr(date, 'to_pydatetime') else pd.to_datetime(date).to_pydatetime(),
                open=float(row['Open']),
                high=float(row['High']),
                low=float(row['Low']),
                close=float(row['Close']),
                volume=int(row['Volume'])
            )
            price_bars.append(bar)

        self.logger.info(f"Fetched {len(price_bars)} historical bars for {symbol}")
        return price_bars
