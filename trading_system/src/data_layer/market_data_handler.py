"""Market Data Handler - 실시간 시세 수신 및 처리"""

import logging
import os
import time
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Callable, List, Optional

import urllib.request
import xml.etree.ElementTree as ET
import pandas as pd
import yfinance as yf
import FinanceDataReader as fdr
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, retry_if_not_exception_type

from src.analysis.backtest import PriceBar

logger = logging.getLogger(__name__)


def _fetch_naver_direct(symbol: str, start_date: Optional[str] = None) -> pd.DataFrame:
    """Tier 3 fallback for KRX: Naver Financial Chart XML API."""
    code = symbol.zfill(6) if symbol.isdigit() and len(symbol) <= 6 else symbol.split('.')[0]
    url = f"https://fchart.stock.naver.com/sise.nhn?symbol={code}&timeframe=day&count=3000&requestType=0"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as resp:  # nosec B310
            xml_data = resp.read().decode('euc-kr', errors='ignore')
        root = ET.fromstring(xml_data)  # nosec B314
        items = root.findall('.//item')
        rows = []
        for item in items:
            data_str = item.attrib.get('data', '')
            parts = data_str.split('|')
            if len(parts) >= 6:
                d_str = parts[0]
                date_str = f"{d_str[:4]}-{d_str[4:6]}-{d_str[6:8]}"
                if not start_date or date_str >= start_date:
                    try:
                        o, h, l, c, v = float(parts[1]), float(parts[2]), float(parts[3]), float(parts[4]), float(parts[5])
                        rows.append({
                            'Date': pd.to_datetime(date_str, errors='coerce'),
                            'Open': o,
                            'High': h,
                            'Low': l,
                            'Close': c,
                            'Volume': v,
                        })
                    except (ValueError, TypeError):
                        continue
        if rows:
            df = pd.DataFrame(rows).dropna(subset=['Date', 'Close']).set_index('Date').sort_index()
            return df
    except Exception as e:
        logger.debug(f"Naver direct API fetch failed for {symbol}: {e}")
    return pd.DataFrame()


def _fetch_pykrx(symbol: str, start_date: Optional[str] = None) -> pd.DataFrame:
    """Tier 4 fallback for KRX: PyKRX API."""
    try:
        from pykrx import stock
        code = symbol.zfill(6) if symbol.isdigit() and len(symbol) <= 6 else symbol.split('.')[0]
        s_date = (start_date or "2018-01-01").replace('-', '')
        e_date = datetime.now().strftime('%Y%m%d')
        df = stock.get_market_ohlcv_by_date(s_date, e_date, code)
        if df is not None and not df.empty:
            col_map = {'시가': 'Open', '고가': 'High', '저가': 'Low', '종가': 'Close', '거래량': 'Volume'}
            df = df.rename(columns=col_map)
            cols = [c for c in ['Open', 'High', 'Low', 'Close', 'Volume'] if c in df.columns]
            df = df[cols]
            df.index.name = 'Date'
            return df
    except Exception as e:
        logger.debug(f"PyKRX fetch failed for {symbol}: {e}")
    return pd.DataFrame()


def _fetch_stooq_or_yahoo_direct(symbol: str, start_date: Optional[str] = None) -> pd.DataFrame:
    """Tier 3 fallback for US: Stooq / Yahoo Direct API."""
    try:
        df = fdr.DataReader(f"STOOQ:{symbol.upper()}", start=start_date)
        if df is not None and not df.empty:
            df.columns = [str(c).capitalize() for c in df.columns]
            return df
    except Exception as e:
        logger.debug(f"FDR Stooq fetch failed for {symbol}: {e}")

    try:
        stooq_sym = symbol.lower().replace('.', '-')
        url = f"https://stooq.com/q/d/l/?s={stooq_sym}.us&i=d"
        df = pd.read_csv(url, parse_dates=['Date'], index_col='Date')
        if df is not None and not df.empty:
            if start_date:
                df = df[df.index >= pd.to_datetime(start_date)]
            df.columns = [str(c).capitalize() for c in df.columns]
            return df
    except Exception as e:
        logger.debug(f"Direct Stooq CSV fetch failed for {symbol}: {e}")

    return pd.DataFrame()


class CircuitBreakerOpenException(Exception):
    """서킷 브레이커가 OPEN 상태일 때 발생하는 예외 (재시도 불가)"""
    pass


class RateLimiter:
    """토큰 버킷 알고리즘 기반 API 호출 제한기 (Thread-Safe)"""

    def __init__(self, rate_limit: int, time_window: float = 1.0):
        self.rate_limit = rate_limit
        self.time_window = time_window
        self.tokens = rate_limit
        self.last_updated = time.time()
        self._lock = threading.Lock()

    def acquire(self):
        with self._lock:
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
        self.market_data_dict: dict[str, MarketData] = {}
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
        callback_name = callback.__name__ if hasattr(callback, "__name__") else str(callback)
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

    def simulate_api_call(self, symbol: str, price: float, bid: float, ask: float, volume: int) -> MarketData:
        """증권사 API 호출 시뮬레이션"""
        data = MarketData(symbol=symbol, price=price, bid=bid, ask=ask, volume=volume, timestamp=datetime.now())
        self.publish_market_data(data)
        return data

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(Exception) & retry_if_not_exception_type(CircuitBreakerOpenException),
        reraise=True
    )
    def _fetch_yf_with_retry(self, symbol: str):
        if not self.circuit_breaker.check_state():
            raise CircuitBreakerOpenException("Circuit breaker is OPEN. API calls are temporarily blocked.")

        self.rate_limiter.wait()

        try:
            ticker = yf.Ticker(symbol)
            fast = ticker.fast_info
            price = fast.last_price

            if price is None or price <= 0:
                hist = ticker.history(period="1d", interval="1m")
                if not hist.empty:
                    price = float(hist["Close"].iloc[-1])
                    volume = int(hist["Volume"].iloc[-1])
                else:
                    raise ValueError("No price data returned from yfinance")
            else:
                volume = int(fast.last_volume) if fast.last_volume else 100000

            self.circuit_breaker.record_success()
            return price, volume
        except CircuitBreakerOpenException:
            raise
        except Exception:
            self.circuit_breaker.record_failure()
            raise

    def fetch_live_data(self, symbol: str) -> MarketData | None:
        """yfinance를 통해 실제 실시간 시세 데이터를 조회하고 이벤트로 전송"""
        try:
            price, volume = self._fetch_yf_with_retry(symbol)

            bid = round(price - 0.05, 2)
            ask = round(price + 0.05, 2)

            data = MarketData(symbol=symbol, price=price, bid=bid, ask=ask, volume=volume, timestamp=datetime.now())
            self.publish_market_data(data)
            self.logger.info(f"Live data fetched from yfinance for {symbol}: ${price:.2f}")
            return data

        except Exception as e:
            self.logger.error(f"Failed to fetch live data from yfinance for {symbol}: {e}")
            return None

    def fetch_historical_data(self, symbol: str, period: str = "5y") -> List[Any]:
        """yfinance를 통해 과거 데이터를 가져오고 DB+Parquet 캐시를 활용합니다.

        데이터는 StockPriceDB에 저장되어 이후 재호출을 방지합니다.
        period: "5y", "10y", "all" (전체기간), 숫자+y 형식
        """
        from src.persistence.database import StockPriceDB
        from src.config import TradingConfig

        config = TradingConfig()
        db = StockPriceDB(db_path=config.stock_price_db_path)

        # period -> start_date 변환
        if period == "all":
            start_date = None  # None → yfinance에 period="max"로 전달
            yf_period = "max"
        else:
            yf_period = None
            period_map = {
                "1mo": 30, "3mo": 90, "6mo": 180, "1y": 365,
                "2y": 730, "3y": 1095, "4y": 1460, "5y": 1825,
                "10y": 3650, "15y": 5475, "20y": 7300, "30y": 10950,
            }
            if period in period_map:
                days = period_map[period]
                start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
            elif period.endswith("y"):
                years = int(period.replace("y", ""))
                start_date = (datetime.now() - timedelta(days=365 * years)).strftime("%Y-%m-%d")
            else:
                start_date = None

        # 1. DB에서 먼저 조회
        df = db.get_prices(symbol, start_date=start_date)
        if not df.empty:
            dt = pd.to_datetime(df.index[-1])
            latest_db_dt = dt.tz_localize(None) if getattr(dt, "tz", None) is not None else dt
            cutoff = datetime.now() - timedelta(days=1)
            needs_fetch = latest_db_dt < cutoff
        else:
            needs_fetch = True

        # 2. 추가 fetch가 필요한 경우 yfinance 호출
        if needs_fetch:
            if not self.circuit_breaker.check_state():
                self.logger.error(f"Circuit breaker is OPEN. Blocked fetch for {symbol}")
                if not df.empty:
                    return self._df_to_price_bars(df)
                return []

            try:
                hist = self._fetch_historical_yf_with_retry(symbol, start_date=start_date, yf_period=yf_period, period=period)

                # 3. 새 데이터 DB에 저장 (DataValidator sanity check 적용)
                from src.data_layer.data_validator import DataValidator
                is_valid, hist = DataValidator.sanitize_and_validate_price_data(symbol, hist)
                if is_valid:
                    db.update_prices(symbol, hist)
                else:
                    self.logger.warning(f"Historical data for {symbol} failed quality validation. Skipping DB update.")

                # Parquet에도 저장 (하위 호환성)
                cache_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data", "cache")
                os.makedirs(cache_dir, exist_ok=True)
                safe_symbol = symbol.replace("/", "_").replace("\\", "_")
                cache_file = os.path.join(cache_dir, f"{safe_symbol}_{period}.parquet")
                try:
                    hist.to_parquet(cache_file)
                except Exception as e:
                    self.logger.warning(f"Failed to save parquet cache for {symbol}: {e}")

                # DB에서 다시 조회 (최신 전체 범위)
                df = db.get_prices(symbol, start_date=start_date)

            except Exception as e:
                self.logger.error(f"Failed to fetch historical data for {symbol}: {e}")

                if not df.empty:
                    price_bars = self._df_to_price_bars(df)
                    self.logger.info(f"Returning {len(price_bars)} cached bars for {symbol}")
                    return price_bars
                return []

        price_bars = self._df_to_price_bars(df)
        self.logger.info(f"Fetched {len(price_bars)} historical bars for {symbol} (DB cache)")
        return price_bars

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(Exception) & retry_if_not_exception_type(CircuitBreakerOpenException),
        reraise=True
    )
    def _fetch_historical_yf_with_retry(self, symbol: str, start_date: Optional[str] = None, yf_period: Optional[str] = None, period: str = "5y") -> pd.DataFrame:
        """Multi-tier historical data fetch with retries and fallbacks."""
        if not self.circuit_breaker.check_state():
            raise CircuitBreakerOpenException("Circuit breaker is OPEN. API calls are temporarily blocked.")

        self.rate_limiter.wait()

        # Symbol normalization
        clean_sym = symbol.zfill(6) if symbol.isdigit() and len(symbol) <= 6 else symbol
        is_krx = clean_sym.isdigit() and len(clean_sym) == 6 or clean_sym.endswith(('.KS', '.KQ', '.KX'))
        if is_krx:
            yf_symbol = f"{clean_sym.split('.')[0]}.KS" if not clean_sym.endswith(('.KS', '.KQ', '.KX')) else clean_sym
        else:
            yf_symbol = clean_sym.replace('.', '-')

        # Tier 1: yfinance
        try:
            ticker = yf.Ticker(yf_symbol)
            if yf_period == "max":
                hist = ticker.history(period="max")
            elif start_date:
                hist = ticker.history(start=start_date)
            else:
                hist = ticker.history(period=period)

            if hist is not None and not hist.empty:
                hist = hist.dropna(subset=["Open", "High", "Low", "Close"])
                if not hist.empty:
                    self.circuit_breaker.record_success()
                    return hist
        except CircuitBreakerOpenException:
            raise
        except Exception as e:
            logger.debug(f"Tier 1 (yfinance) failed for {yf_symbol}: {e}")

        # Tier 2: FinanceDataReader
        try:
            fdr_sym = clean_sym.split('.')[0] if is_krx else yf_symbol
            hist = fdr.DataReader(fdr_sym, start=start_date)
            if hist is not None and not hist.empty:
                hist.columns = [str(c).capitalize() for c in hist.columns]
                hist = hist.dropna(subset=["Open", "High", "Low", "Close"])
                if not hist.empty:
                    self.circuit_breaker.record_success()
                    return hist
        except Exception as e:
            logger.debug(f"Tier 2 (FinanceDataReader) failed for {clean_sym}: {e}")

        # Tier 3 & Tier 4 (KRX / US specific fallbacks)
        if is_krx:
            # Tier 3: Naver Direct API
            try:
                hist = _fetch_naver_direct(clean_sym, start_date)
                if hist is not None and not hist.empty:
                    self.circuit_breaker.record_success()
                    return hist
            except Exception as e:
                logger.debug(f"Tier 3 (Naver Direct) failed for {clean_sym}: {e}")

            # Tier 4: PyKRX
            try:
                hist = _fetch_pykrx(clean_sym, start_date)
                if hist is not None and not hist.empty:
                    self.circuit_breaker.record_success()
                    return hist
            except Exception as e:
                logger.debug(f"Tier 4 (PyKRX) failed for {clean_sym}: {e}")
        else:
            # Tier 3 US: Stooq / Yahoo Direct
            try:
                hist = _fetch_stooq_or_yahoo_direct(clean_sym, start_date)
                if hist is not None and not hist.empty:
                    self.circuit_breaker.record_success()
                    return hist
            except Exception as e:
                logger.debug(f"Tier 3 (Stooq/Yahoo Direct) failed for {clean_sym}: {e}")

        self.circuit_breaker.record_failure()
        raise ValueError(f"No historical price data returned across all providers for {symbol}")

    @staticmethod
    def _df_to_price_bars(df: pd.DataFrame) -> List[Any]:
        """DataFrame(인덱스=날짜, 컬럼=OHLCV) → PriceBar 리스트 변환 (대소문자 무관, ffill 연속성 보장)"""
        if df is None or df.empty:
            return []
        df = df.copy()
        cols = {c.lower(): c for c in df.columns}
        ohlcv_cols = [cols[k] for k in ["open", "high", "low", "close", "volume"] if k in cols]
        if ohlcv_cols:
            df[ohlcv_cols] = df[ohlcv_cols].ffill()
        for date_idx, row in df.iterrows():
            pydt = date_idx.to_pydatetime() if hasattr(date_idx, "to_pydatetime") else pd.to_datetime(date_idx).to_pydatetime()
            try:
                op = float(row[cols["open"]]) if "open" in cols else 0.0
                hi = float(row[cols["high"]]) if "high" in cols else 0.0
                lo = float(row[cols["low"]]) if "low" in cols else 0.0
                cl = float(row[cols["close"]]) if "close" in cols else 0.0
                vol = int(float(row[cols["volume"]])) if "volume" in cols else 0
            except (ValueError, TypeError, KeyError):
                continue
            price_bars.append(PriceBar(
                timestamp=pydt,
                open=op,
                high=hi,
                low=lo,
                close=cl,
                volume=vol,
            ))
        return price_bars
