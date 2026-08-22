"""Global market indices and FX rate data provider"""

import logging
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
import yfinance as yf

from .fred_client import FredApiClient

logger = logging.getLogger(__name__)

# ─── Global Benchmarks ──────────────────────────────────────────────────────

GLOBAL_INDICES: Dict[str, str] = {
    "^GSPC": "S&P 500",
    "^IXIC": "NASDAQ",
    "^DJI": "Dow Jones",
    "^RUT": "Russell 2000",
    "^KS11": "KOSPI",
    "^KQ11": "KOSDAQ",
    "^N225": "Nikkei 225",
    "^HSI": "Hang Seng",
    "^FTSE": "FTSE 100",
    "000300.SS": "CSI 300",
    "000001.SS": "Shanghai Composite",
    "^BSESN": "BSE Sensex",
    "^NSEI": "Nifty 50",
    "^AXJO": "ASX 200",
    "^GDAXI": "DAX",
    "^FCHI": "CAC 40",
    "^STOXX50E": "Euro Stoxx 50",
    "^TWII": "TAIEX (Taiwan)",
    "^BVSP": "Bovespa (Brazil)",
    "^STI": "Straits Times (Singapore)",
    "^GSPTSE": "S&P/TSX (Canada)",
    "^VIX": "CBOE Volatility",
}

FX_PAIRS: Dict[str, str] = {
    "USDKRW=X": "USD/KRW",
    "EURUSD=X": "EUR/USD",
    "USDJPY=X": "USD/JPY",
    "GBPUSD=X": "GBP/USD",
    "USDCAD=X": "USD/CAD",
    "USDCNY=X": "USD/CNY",
    "USDINR=X": "USD/INR",
    "USDVND=X": "USD/VND",
    "USDTWD=X": "USD/TWD",
    "USDAUD=X": "USD/AUD",
    "USDBRL=X": "USD/BRL",
    "USDHKD=X": "USD/HKD",
    "USDSGD=X": "USD/SGD",
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
        self._summary_cache: Dict[str, Any] = {}
        self._summary_cache_ts: float = 0.0
        self.fred_client = FredApiClient()

    def _get_cached_or_fetch(self, symbol: str, period: str = "1d") -> Any:
        cache_key = f"{symbol}_{period}"
        now = time.time()
        if cache_key in self._cache:
            data, ts = self._cache[cache_key]
            if now - ts < _CACHE_TTL:
                return data

        hist = None
        # Tier 1: yf.Ticker fast path
        try:
            tk = yf.Ticker(symbol)
            hist = tk.history(period=period)
        except Exception as e:
            logger.debug("yfinance Ticker error for %s: %s", symbol, e)

        # Tier 2: yf.download batch path
        if hist is None or hist.empty:
            try:
                hist = yf.download(symbol, period=period, progress=False)
                if isinstance(hist.columns, pd.MultiIndex):
                    hist.columns = hist.columns.droplevel(1)
            except Exception as e:
                logger.debug("yfinance download error for %s: %s", symbol, e)

        # Tier 3: FinanceDataReader fallback
        if hist is None or hist.empty:
            try:
                import FinanceDataReader as fdr
                fdr_sym = symbol.replace("USDKRW=X", "USD/KRW").replace("EURUSD=X", "EUR/USD")
                hist = fdr.DataReader(fdr_sym, start=(datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d'))
                if hist is not None and not hist.empty:
                    hist.columns = [str(c).capitalize() for c in hist.columns]
            except Exception as e:
                logger.debug("FDR fallback error for %s: %s", symbol, e)

        if hist is not None and not hist.empty:
            self._cache[cache_key] = (hist, now)
            return hist
        else:
            logger.warning("No data returned for %s across all providers", symbol)
            return None


    def get_index_current(self, symbol: str) -> Dict[str, Any]:
        """Return latest snapshot for a single index symbol."""
        hist = self._get_cached_or_fetch(symbol, period="5d")
        if hist is None or hist.empty:
            return {"symbol": symbol, "price": None, "change_pct": None}
        c_col = next((c for c in hist.columns if str(c).lower() in ("close", "adj close", "adjclose")), None)
        if not c_col:
            return {"symbol": symbol, "price": None, "change_pct": None}
        prices = pd.to_numeric(hist[c_col], errors='coerce').dropna()
        if prices.empty:
            return {"symbol": symbol, "price": None, "change_pct": None}
        price = float(prices.iloc[-1])
        prev = float(prices.iloc[-2]) if len(prices) > 1 else price
        change_pct = ((price - prev) / abs(prev)) * 100.0 if (prev and abs(prev) > 1e-8) else 0.0
        return {
            "symbol": symbol,
            "name": GLOBAL_INDICES.get(symbol, symbol),
            "price": round(price, 2) if np.isfinite(price) else None,
            "change_pct": round(change_pct, 2) if np.isfinite(change_pct) else None,
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
        c_col = next((c for c in hist.columns if str(c).lower() in ("close", "adj close", "adjclose")), None)
        if not c_col:
            return {"pair": pair, "rate": None, "change_pct": None}
        prices = pd.to_numeric(hist[c_col], errors='coerce').dropna()
        if prices.empty:
            return {"pair": pair, "rate": None, "change_pct": None}
        rate = float(prices.iloc[-1])
        prev = float(prices.iloc[-2]) if len(prices) > 1 else rate
        change_pct = ((rate - prev) / abs(prev)) * 100.0 if (prev and abs(prev) > 1e-8) else 0.0
        return {
            "pair": pair,
            "name": FX_PAIRS.get(pair, pair),
            "rate": round(rate, 4) if np.isfinite(rate) else None,
            "change_pct": round(change_pct, 2) if np.isfinite(change_pct) else None,
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
        c_col = next((c for c in hist.columns if str(c).lower() in ("close", "adj close", "adjclose")), None)
        if not c_col:
            return {"symbol": symbol, "price": None, "change_pct": None}
        prices = pd.to_numeric(hist[c_col], errors='coerce').dropna()
        if prices.empty:
            return {"symbol": symbol, "price": None, "change_pct": None}
        price = float(prices.iloc[-1])
        prev = float(prices.iloc[-2]) if len(prices) > 1 else price
        change_pct = ((price - prev) / abs(prev)) * 100.0 if (prev and abs(prev) > 1e-8) else 0.0
        return {
            "symbol": symbol,
            "name": MACRO_COMMODITIES.get(symbol, symbol),
            "price": round(price, 4) if np.isfinite(price) else None,
            "change_pct": round(change_pct, 2) if np.isfinite(change_pct) else None,
            "timestamp": datetime.now().isoformat(),
        }

    def get_all_macro_commodities(self) -> Dict[str, Dict[str, Any]]:
        """Return latest snapshot for every configured macro commodity and FRED interest rate."""
        result: Dict[str, Dict[str, Any]] = {}
        for sym in MACRO_COMMODITIES:
            result[sym] = self.get_macro_commodity(sym)

        # Include official FRED interest rates (IRSTCI01KRM156N, DGS10, etc.) if FRED_API_KEY is active
        if self.fred_client.is_configured():
            try:
                fred_rates = self.fred_client.fetch_all_fred_indicators()
                for sid, info in fred_rates.items():
                    result[sid] = {
                        "symbol": sid,
                        "name": info.get("name", sid),
                        "price": info.get("price"),
                        "change_pct": info.get("change_pct", 0.0),
                        "timestamp": info.get("timestamp"),
                    }
                logger.info(f"[GlobalMarketClient] Merged {len(fred_rates)} FRED interest rate indicators.")
            except Exception as e:
                logger.warning(f"[GlobalMarketClient] Failed to fetch FRED indicators: {e}")

        return result

    def get_summary(self) -> Dict[str, Any]:
        """Combined market overview — indices + FX in one call."""
        now = time.time()
        if now - self._summary_cache_ts < _CACHE_TTL and self._summary_cache:
            return self._summary_cache
        summary = {
            "indices": self.get_all_indices(),
            "fx_rates": self.get_all_fx_rates(),
            "macro_commodities": self.get_all_macro_commodities(),
            "updated_at": datetime.now().isoformat(),
        }
        self._summary_cache = summary
        self._summary_cache_ts = now
        return summary

    def get_index_historical(self, symbol: str, period: str = "6mo") -> List[Dict[str, float]]:
        """Return OHLCV history for an index."""
        hist = self._get_cached_or_fetch(symbol, period=period)
        if hist is None or hist.empty:
            return []
        records: List[Dict[str, Any]] = []
        for row in hist.itertuples(index=True):
            idx = row[0]
            r_dict = row._asdict() if hasattr(row, '_asdict') else dict(zip(hist.columns, row[1:]))
            records.append(
                {
                    "date": idx.isoformat() if hasattr(idx, "isoformat") else str(idx),
                    "open": float(r_dict.get("Open", 0) or 0),
                    "high": float(r_dict.get("High", 0) or 0),
                    "low": float(r_dict.get("Low", 0) or 0),
                    "close": float(r_dict.get("Close", 0) or 0),
                    "volume": int(float(r_dict.get("Volume", 0) or 0)),
                }
            )
        return records

    def get_cross_rate(
        self,
        from_curr: str,
        to_curr: str = "KRW",
        fallback_rates: Optional[Dict[str, float]] = None
    ) -> float:
        """
        Computes triangular exchange rate from from_curr to to_curr (e.g. USD -> KRW, JPY -> KRW, EUR -> USD).
        1 from_curr = X to_curr.
        """
        c_from = str(from_curr).strip().upper()
        c_to = str(to_curr).strip().upper()

        if c_from == c_to:
            return 1.0

        # Baseline fallback rates (against USD)
        usd_rates: Dict[str, float] = {
            'USD': 1.0,
            'KRW': 1350.0,
            'JPY': 155.0,
            'EUR': 0.92,
            'GBP': 0.78,
            'CNY': 7.25,
            'INR': 83.5,
            'VND': 25400.0,
            'TWD': 32.5,
            'AUD': 1.52,
            'BRL': 5.45,
            'HKD': 7.82,
            'SGD': 1.35,
            'CAD': 1.37,
        }
        if fallback_rates:
            usd_rates.update(fallback_rates)

        # Dynamic live rate updates from FX_PAIRS
        try:
            live_fx = self.get_all_fx_rates()
            for pair_key, p_info in live_fx.items():
                p_rate = p_info.get('rate')
                if p_rate and math.isfinite(p_rate) and p_rate > 0:
                    if pair_key == 'USDKRW=X':
                        usd_rates['KRW'] = float(p_rate)
                    elif pair_key == 'USDJPY=X':
                        usd_rates['JPY'] = float(p_rate)
                    elif pair_key == 'EURUSD=X':
                        usd_rates['EUR'] = 1.0 / float(p_rate)
                    elif pair_key == 'GBPUSD=X':
                        usd_rates['GBP'] = 1.0 / float(p_rate)
                    elif pair_key == 'USDCNY=X':
                        usd_rates['CNY'] = float(p_rate)
                    elif pair_key == 'USDINR=X':
                        usd_rates['INR'] = float(p_rate)
                    elif pair_key == 'USDVND=X':
                        usd_rates['VND'] = float(p_rate)
                    elif pair_key == 'USDTWD=X':
                        usd_rates['TWD'] = float(p_rate)
                    elif pair_key == 'USDAUD=X':
                        usd_rates['AUD'] = float(p_rate)
                    elif pair_key == 'USDBRL=X':
                        usd_rates['BRL'] = float(p_rate)
                    elif pair_key == 'USDHKD=X':
                        usd_rates['HKD'] = float(p_rate)
                    elif pair_key == 'USDSGD=X':
                        usd_rates['SGD'] = float(p_rate)
                    elif pair_key == 'USDCAD=X':
                        usd_rates['CAD'] = float(p_rate)
        except Exception as e:
            logger.debug(f"[FX Cross] Live rate update fallback: {e}")

        # Rate relative to USD: 1 USD = rate_from from_curr, 1 USD = rate_to to_curr
        # => 1 from_curr = (rate_to / rate_from) to_curr
        rate_from = usd_rates.get(c_from, 1.0)
        rate_to = usd_rates.get(c_to, 1350.0 if c_to == 'KRW' else 1.0)

        if rate_from <= 0:
            return 1.0
        return float(rate_to / rate_from)


class MarketSessionManager:
    """
    Manages 24-hour follow-the-sun global market trading sessions,
    regional market opening hours, and timezone synchronization.
    """

    MARKET_HOURS = {
        'KRX': {'tz': 'Asia/Seoul', 'open': (9, 0), 'close': (15, 30)},
        'KOSPI': {'tz': 'Asia/Seoul', 'open': (9, 0), 'close': (15, 30)},
        'KOSDAQ': {'tz': 'Asia/Seoul', 'open': (9, 0), 'close': (15, 30)},
        'TSE': {'tz': 'Asia/Tokyo', 'open': (9, 0), 'close': (15, 30)},
        'JAPAN': {'tz': 'Asia/Tokyo', 'open': (9, 0), 'close': (15, 30)},
        'TWSE': {'tz': 'Asia/Taipei', 'open': (9, 0), 'close': (13, 30)},
        'SSE': {'tz': 'Asia/Shanghai', 'open': (9, 30), 'close': (15, 0)},
        'SZSE': {'tz': 'Asia/Shanghai', 'open': (9, 30), 'close': (15, 0)},
        'CHINA': {'tz': 'Asia/Shanghai', 'open': (9, 30), 'close': (15, 0)},
        'HKEX': {'tz': 'Asia/Hong_Kong', 'open': (9, 30), 'close': (16, 0)},
        'SGX': {'tz': 'Asia/Singapore', 'open': (9, 0), 'close': (17, 0)},
        'NSE': {'tz': 'Asia/Kolkata', 'open': (9, 15), 'close': (15, 30)},
        'HOSE': {'tz': 'Asia/Ho_Chi_Minh', 'open': (9, 0), 'close': (15, 0)},
        'ASX': {'tz': 'Australia/Sydney', 'open': (10, 0), 'close': (16, 0)},
        'STOXX': {'tz': 'Europe/Paris', 'open': (9, 0), 'close': (17, 30)},
        'DAX': {'tz': 'Europe/Berlin', 'open': (9, 0), 'close': (17, 30)},
        'FTSE': {'tz': 'Europe/London', 'open': (8, 0), 'close': (16, 30)},
        'SP500': {'tz': 'America/New_York', 'open': (9, 30), 'close': (16, 0)},
        'NASDAQ': {'tz': 'America/New_York', 'open': (9, 30), 'close': (16, 0)},
        'RUSSELL2000': {'tz': 'America/New_York', 'open': (9, 30), 'close': (16, 0)},
        'TSX': {'tz': 'America/Toronto', 'open': (9, 30), 'close': (16, 0)},
        'B3': {'tz': 'America/Sao_Paulo', 'open': (10, 0), 'close': (17, 0)},
    }

    @staticmethod
    def get_market_region(market: str) -> str:
        """Categorize market into macro geographic regions (ASIA, EUROPE, AMERICAS)."""
        mkt = str(market).strip().upper()
        if mkt in ('KOSPI', 'KOSDAQ', 'KRX', 'JAPAN', 'TSE', 'JAPAN_TSE', 'TAIWAN', 'TWSE', 'TAIWAN_TWSE', 'CHINA', 'SSE', 'SZSE', 'CHINA_SSE', 'CHINA_SZSE', 'HKEX', 'SINGAPORE', 'SGX', 'SINGAPORE_SGX', 'INDIA', 'NSE', 'INDIA_NSE', 'VIETNAM', 'HOSE', 'VIETNAM_HOSE', 'AUSTRALIA', 'ASX', 'AUSTRALIA_ASX'):
            return 'ASIA_PACIFIC'
        if mkt in ('EUROPE', 'STOXX', 'EUROPE_STOXX', 'DAX', 'FTSE', 'CAC'):
            return 'EUROPE'
        return 'AMERICAS'


__all__ = ["FX_PAIRS", "GLOBAL_INDICES", "MACRO_COMMODITIES", "GlobalMarketClient", "MarketSessionManager"]
