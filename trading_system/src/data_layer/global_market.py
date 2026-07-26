"""Global market indices and FX rate data provider"""

import logging
import time
from datetime import datetime
from typing import Any, Dict, List

import yfinance as yf

logger = logging.getLogger(__name__)

# ─── Global Benchmarks ──────────────────────────────────────────────────────

GLOBAL_INDICES: Dict[str, str] = {
    "^GSPC": "S&P 500",
    "^IXIC": "NASDAQ",
    "^DJI": "Dow Jones",
    "^KS11": "KOSPI",
    "^N225": "Nikkei 225",
    "^HSI": "Hang Seng",
    "^FTSE": "FTSE 100",
    "000001.SS": "Shanghai Composite",
    "^BSESN": "BSE Sensex",
    "^AXJO": "ASX 200",
    "^GDAXI": "DAX",
    "^FCHI": "CAC 40",
    "^VIX": "CBOE Volatility",
}

FX_PAIRS: Dict[str, str] = {
    "USDKRW=X": "USD/KRW",
    "EURUSD=X": "EUR/USD",
    "USDJPY=X": "USD/JPY",
    "GBPUSD=X": "GBP/USD",
    "USDCAD=X": "USD/CAD",
    "USDCNY=X": "USD/CNY",
}

# 추가 거시경제 지표: 금리, 원자재, 달러인덱스, 한국 국채
MACRO_COMMODITIES: Dict[str, str] = {
    "^TNX": "US 10Y Treasury Yield",
    "^FVX": "US 5Y Treasury Yield",
    "^IRX": "US 13W Treasury Bill",
    "CL=F": "WTI Crude Oil",
    "DX-Y.NYB": "US Dollar Index (DXY)",
    "305720.KS": "KODEX KTB 3Y ETF",
    "273130.KS": "KODEX KTB 10Y ETF",
}

_CACHE_TTL = 300  # 5-minute cache


class GlobalMarketClient:
    """Fetches global equity indices and FX rates via yfinance."""

    def __init__(self):
        self._cache: Dict[str, Any] = {}
        self._cache_ts: float = 0.0

    def _get_cached_or_fetch(self, symbol: str, period: str = "1d") -> Any:
        cache_key = f"{symbol}_{period}"
        now = time.time()
        if cache_key in self._cache:
            data, ts = self._cache[cache_key]
            if now - ts < _CACHE_TTL:
                return data

        try:
            tk = yf.Ticker(symbol)
            hist = tk.history(period=period)
            if hist.empty:
                logger.warning("No data returned for %s", symbol)
            else:
                self._cache[cache_key] = (hist, now)
            return hist
        except Exception as e:
            logger.error("yfinance error for %s: %s", symbol, e)
            return None

    def get_index_current(self, symbol: str) -> Dict[str, Any]:
        """Return latest snapshot for a single index symbol."""
        hist = self._get_cached_or_fetch(symbol, period="5d")
        if hist is None or hist.empty:
            return {"symbol": symbol, "price": None, "change_pct": None}
        prices = hist["Close"]
        price = float(prices.iloc[-1])
        prev = float(prices.iloc[-2]) if len(prices) > 1 else price
        change_pct = ((price - prev) / prev) * 100 if prev else 0.0
        return {
            "symbol": symbol,
            "name": GLOBAL_INDICES.get(symbol, symbol),
            "price": round(price, 2),
            "change_pct": round(change_pct, 2),
            "timestamp": datetime.now().isoformat(),
        }

    def get_all_indices(self) -> Dict[str, Dict[str, Any]]:
        """Return current snapshot for every configured global index."""
        result: Dict[str, Dict[str, Any]] = {}
        for sym in GLOBAL_INDICES:
            result[sym] = self.get_index_current(sym)
        return result

    def get_fx_rate(self, pair: str) -> Dict[str, Any]:
        """Return latest rate for a single FX pair."""
        hist = self._get_cached_or_fetch(pair, period="5d")
        if hist is None or hist.empty:
            return {"pair": pair, "rate": None, "change_pct": None}
        prices = hist["Close"]
        rate = float(prices.iloc[-1])
        prev = float(prices.iloc[-2]) if len(prices) > 1 else rate
        change_pct = ((rate - prev) / prev) * 100 if prev else 0.0
        return {
            "pair": pair,
            "name": FX_PAIRS.get(pair, pair),
            "rate": round(rate, 4),
            "change_pct": round(change_pct, 2),
            "timestamp": datetime.now().isoformat(),
        }

    def get_all_fx_rates(self) -> Dict[str, Dict[str, Any]]:
        """Return latest rate for every configured FX pair."""
        result: Dict[str, Dict[str, Any]] = {}
        for pair in FX_PAIRS:
            result[pair] = self.get_fx_rate(pair)
        return result

    def get_macro_commodity(self, symbol: str) -> Dict[str, Any]:
        """Return latest snapshot for a macro commodity (yield, oil, DXY)."""
        hist = self._get_cached_or_fetch(symbol, period="5d")
        if hist is None or hist.empty:
            return {"symbol": symbol, "price": None, "change_pct": None}
        prices = hist["Close"]
        price = float(prices.iloc[-1])
        prev = float(prices.iloc[-2]) if len(prices) > 1 else price
        change_pct = ((price - prev) / prev) * 100 if prev else 0.0
        return {
            "symbol": symbol,
            "name": MACRO_COMMODITIES.get(symbol, symbol),
            "price": round(price, 4),
            "change_pct": round(change_pct, 2),
            "timestamp": datetime.now().isoformat(),
        }

    def get_all_macro_commodities(self) -> Dict[str, Dict[str, Any]]:
        """Return latest snapshot for every configured macro commodity."""
        result: Dict[str, Dict[str, Any]] = {}
        for sym in MACRO_COMMODITIES:
            result[sym] = self.get_macro_commodity(sym)
        return result

    def get_summary(self) -> Dict[str, Any]:
        """Combined market overview — indices + FX in one call."""
        now = time.time()
        if now - self._cache_ts < _CACHE_TTL and self._cache:
            return self._cache
        summary = {
            "indices": self.get_all_indices(),
            "fx_rates": self.get_all_fx_rates(),
            "macro_commodities": self.get_all_macro_commodities(),
            "updated_at": datetime.now().isoformat(),
        }
        self._cache = summary
        self._cache_ts = now
        return summary

    def get_index_historical(self, symbol: str, period: str = "6mo") -> List[Dict[str, float]]:
        """Return OHLCV history for an index."""
        hist = self._get_cached_or_fetch(symbol, period=period)
        if hist is None or hist.empty:
            return []
        records: List[Dict[str, Any]] = []
        for idx, row in hist.iterrows():
            records.append(
                {
                    "date": idx.isoformat() if hasattr(idx, "isoformat") else str(idx),
                    "open": float(row.get("Open", 0)),
                    "high": float(row.get("High", 0)),
                    "low": float(row.get("Low", 0)),
                    "close": float(row.get("Close", 0)),
                    "volume": int(row.get("Volume", 0)),
                }
            )
        return records


__all__ = ["FX_PAIRS", "GLOBAL_INDICES", "MACRO_COMMODITIES", "GlobalMarketClient"]
