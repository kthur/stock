"""Realtime price feed - 키움(실매매 가능 시) 우선, yfinance 폴백.

15분 간격 폴링 기준으로 설계: yfinance 5m 캔들 마지막 행 = 현재가.
키움 ZeroMQ 마이크로서비스가 연결되어 있으면 KRX 종목은 키움 실시간 시세를 우선 사용.
"""

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


logger = logging.getLogger(__name__)

_KR_MARKET_SUFFIX = {
    "KOSPI": ".KS",
    "KOSDAQ": ".KQ",
    "KRX": ".KS",
}


@dataclass
class RealtimeQuote:
    symbol: str
    market: str
    price: float
    open_price: float = 0.0
    prev_close: float = 0.0
    high: float = 0.0
    low: float = 0.0
    volume: float = 0.0
    source: str = "unknown"
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def change_pct(self) -> float:
        if self.prev_close and self.prev_close > 0:
            return (self.price - self.prev_close) / self.prev_close * 100.0
        return 0.0


def to_yfinance_symbol(symbol: str, market: str) -> str:
    """KRX 종목에 yfinance 접미사 부여 (005930 -> 005930.KS)."""
    if market in _KR_MARKET_SUFFIX and symbol.isdigit():
        return f"{symbol}{_KR_MARKET_SUFFIX[market]}"
    return symbol


def _normalize_symbol(yf_symbol: str) -> str:
    return yf_symbol.split(".")[0]


def fetch_quotes_yfinance(symbols: List[str], market_of: Dict[str, str]) -> Dict[str, RealtimeQuote]:
    """yfinance 5m 캔들로 종목별 현재가 조회. 실패 종목은 건너뜀."""
    quotes: Dict[str, RealtimeQuote] = {}
    if not symbols:
        return quotes

    yf_symbols = [to_yfinance_symbol(s, market_of.get(s, "KOSPI")) for s in symbols]
    try:
        import yfinance as yf

        data = yf.download(
            tickers=yf_symbols,
            period="5d",
            interval="5m",
            progress=False,
            auto_adjust=True,
            group_by="ticker",
            threads=True,
        )
    except Exception as e:
        logger.warning(f"[PRICE_FEED] yfinance 5m download failed: {e}")
        return quotes

    if data is None or data.empty:
        logger.warning("[PRICE_FEED] yfinance returned empty 5m data")
        return quotes

    try:
        for orig_sym, yf_sym in zip(symbols, yf_symbols):
            try:
                if len(yf_symbols) == 1:
                    df = data
                else:
                    if yf_sym not in data.columns.get_level_values(0):
                        df = None
                    else:
                        df = data[yf_sym]
                if df is None or df.empty or "Close" not in df.columns:
                    continue
                last = df.dropna(subset=["Close"])
                if last.empty:
                    continue
                price = float(last["Close"].iloc[-1])
                if price <= 0:
                    continue
                prev_close = float(df["Close"].dropna().iloc[-2]) if len(df["Close"].dropna()) >= 2 else 0.0
                quotes[orig_sym] = RealtimeQuote(
                    symbol=orig_sym,
                    market=market_of.get(orig_sym, "KOSPI"),
                    price=price,
                    open_price=float(df["Open"].dropna().iloc[-1]) if "Open" in df and not df["Open"].dropna().empty else 0.0,
                    prev_close=prev_close,
                    high=float(df["High"].dropna().tail(1).iloc[0]) if "High" in df and not df["High"].dropna().empty else 0.0,
                    low=float(df["Low"].dropna().tail(1).iloc[0]) if "Low" in df and not df["Low"].dropna().empty else 0.0,
                    volume=float(df["Volume"].dropna().iloc[-1]) if "Volume" in df and not df["Volume"].dropna().empty else 0.0,
                    source="yfinance_5m",
                )
            except Exception as e:
                logger.debug(f"[PRICE_FEED] parse failed for {orig_sym}: {e}")
                continue
    except Exception as e:
        logger.warning(f"[PRICE_FEED] yfinance result parsing failed: {e}")
    return quotes


class RealtimePriceFeed:
    """키움 실시간 시세 우선 + yfinance 5m 폴백 이중 피드."""

    def __init__(self, kiwoom=None, use_yfinance: bool = True):
        self.kiwoom = kiwoom  # KiwoomConnector 인스턴스 (연결 시)
        self.use_yfinance = use_yfinance
        self._cache: Dict[str, RealtimeQuote] = {}
        self._cache_ts: float = 0.0
        self._cache_ttl: float = 300.0  # 5분 캐시

    @property
    def has_kiwoom(self) -> bool:
        return self.kiwoom is not None and getattr(self.kiwoom, "is_connected", False)

    def _fetch_kiwoom(self, symbols: List[str], market_of: Dict[str, str]) -> Dict[str, RealtimeQuote]:
        quotes: Dict[str, RealtimeQuote] = {}
        if not self.has_kiwoom:
            return quotes
        for sym in symbols:
            if market_of.get(sym, "KOSPI") not in ("KOSPI", "KOSDAQ"):
                continue
            try:
                q = self.kiwoom.get_stock_quote(sym)
                price = float(q.get("price", 0.0))
                if price > 0:
                    quotes[sym] = RealtimeQuote(
                        symbol=sym,
                        market=market_of.get(sym, "KOSPI"),
                        price=price,
                        open_price=float(q.get("open", 0.0) or 0.0),
                        prev_close=float(q.get("prev_close", 0.0) or 0.0),
                        high=float(q.get("high", 0.0) or 0.0),
                        low=float(q.get("low", 0.0) or 0.0),
                        volume=float(q.get("volume", 0.0) or 0.0),
                        source="kiwoom",
                    )
            except Exception as e:
                logger.debug(f"[PRICE_FEED] kiwoom quote failed for {sym}: {e}")
        return quotes

    def get_quotes(
        self,
        symbols: List[str],
        market_of: Optional[Dict[str, str]] = None,
        force_refresh: bool = False,
    ) -> Dict[str, RealtimeQuote]:
        market_of = market_of or {}
        symbols = [s for s in symbols if s]
        if not symbols:
            return {}

        now = time.time()
        if not force_refresh and self._cache and (now - self._cache_ts) < self._cache_ttl:
            return {s: q for s, q in self._cache.items() if s in symbols}

        quotes: Dict[str, RealtimeQuote] = {}

        # 1) 키움 우선 (KRX)
        if self.has_kiwoom:
            quotes.update(self._fetch_kiwoom(symbols, market_of))

        # 2) yfinance 폴백 (미확보 종목만)
        missing = [s for s in symbols if s not in quotes]
        if missing and self.use_yfinance:
            quotes.update(fetch_quotes_yfinance(missing, market_of))

        if quotes:
            self._cache = quotes
            self._cache_ts = now
        return {s: q for s, q in quotes.items() if s in symbols}
