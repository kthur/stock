"""Relative-strength / market-relative analysis for stock screening"""

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import numpy as np

from src.data_layer.global_market import GlobalMarketClient

if TYPE_CHECKING:
    from src.data_layer.market_data_handler import MarketDataHandler

logger = logging.getLogger(__name__)

# Default benchmark per market region
REGION_BENCHMARKS: Dict[str, str] = {
    "US": "^GSPC",
    "KR": "^KS11",
    "JP": "^N225",
    "HK": "^HSI",
    "CN": "000001.SS",
    "GB": "^FTSE",
    "DE": "^GDAXI",
    "FR": "^FCHI",
    "IN": "^BSESN",
    "AU": "^AXJO",
}

# Map common ticker suffixes to regions
_SUFFIX_MAP: Dict[str, str] = {
    ".KS": "KR",
    ".KQ": "KR",
    ".T": "JP",
    ".HK": "HK",
    ".SS": "CN",
    ".L": "GB",
    ".DE": "DE",
    ".PA": "FR",
    ".NS": "IN",
    ".AX": "AU",
}


def _guess_region(symbol: str) -> str:
    for suffix, region in _SUFFIX_MAP.items():
        if symbol.upper().endswith(suffix):
            return region
    # Default to US for unmarked tickers
    return "US"


def _benchmark_for_symbol(symbol: str) -> str:
    return REGION_BENCHMARKS.get(_guess_region(symbol), "^GSPC")


def _returns(series: np.ndarray) -> np.ndarray:
    if series is None or len(series) < 2:
        return np.array([])
    denom = series[:-1]
    denom = np.where(np.abs(denom) < 1e-8, np.nan, denom)
    result = (series[1:] - series[:-1]) / denom
    result = np.nan_to_num(result, nan=0.0, posinf=0.0, neginf=0.0)
    return np.asarray(result, dtype=float)


class RelativeStrengthAnalyzer:
    """Computes stock-level metrics relative to a market benchmark.

    Provides:
    - Market correlation (Pearson r)
    - CAPM beta
    - Jensen's alpha
    - Relative-strength score
    - Top-stock ranking
    """

    CACHE_TTL_S = 300  # 5 minutes

    def __init__(
        self,
        market_data_handler: "Optional[MarketDataHandler]" = None,
        global_market: "Optional[GlobalMarketClient]" = None,
    ):
        self.mdh = market_data_handler
        self.gm = global_market or GlobalMarketClient()
        self._score_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_ts: Dict[str, float] = {}

    # ── Public helpers ─────────────────────────────────────────────────────

    def get_benchmark(self, symbol: str) -> str:
        """Return the best-guess benchmark ticker for *symbol*."""
        return _benchmark_for_symbol(symbol)

    # ── Core computation ───────────────────────────────────────────────────

    def compute_metrics(
        self,
        symbol: str,
        stock_returns: np.ndarray,
        benchmark_returns: np.ndarray,
        risk_free_rate: float = 0.03,
    ) -> Dict[str, Any]:
        """Return correlation, beta, alpha, and R² for one stock.

        Parameters
        ----------
        symbol : str
            Ticker label (used for result key only).
        stock_returns : np.ndarray
            Daily returns (decimal, e.g. 0.01 for 1%).
        benchmark_returns : np.ndarray
            Same-length array of benchmark daily returns.
        risk_free_rate : float
            Annual risk-free rate (default 3%).

        Returns
        -------
        Dict with keys: symbol, correlation, beta, alpha, r_squared, n.
        """
        n = min(len(stock_returns), len(benchmark_returns))
        if n < 5:
            return {
                "symbol": symbol,
                "correlation": 0.0,
                "beta": 1.0,
                "alpha": 0.0,
                "r_squared": 0.0,
                "n": 0,
            }

        sr = np.asarray(stock_returns[-n:], dtype=float)
        br = np.asarray(benchmark_returns[-n:], dtype=float)
        valid = np.isfinite(sr) & np.isfinite(br)
        sr = sr[valid]
        br = br[valid]

        if len(sr) < 5:
            return {
                "symbol": symbol,
                "correlation": 0.0,
                "beta": 1.0,
                "alpha": 0.0,
                "r_squared": 0.0,
                "n": int(len(sr)),
            }

        corr_matrix = np.corrcoef(sr, br)
        corr_val = float(corr_matrix[0, 1]) if not np.isnan(corr_matrix[0, 1]) else 0.0
        corr = max(-1.0, min(1.0, corr_val)) if np.isfinite(corr_val) else 0.0

        # CAPM beta = cov(s, b) / var(b)  (same ddof for numerator and denominator)
        var_b = float(np.var(br))
        beta = float(np.cov(sr, br, ddof=0)[0, 1] / var_b) if var_b > 1e-10 else 1.0
        if not np.isfinite(beta):
            beta = 1.0
        beta = max(-5.0, min(5.0, beta))

        # R²
        r_sq = max(0.0, min(1.0, corr * corr))

        # Jensen's alpha = E[s] - rf - beta * (E[b] - rf)
        daily_rf = (risk_free_rate / 252.0) if np.isfinite(risk_free_rate) else (0.03 / 252.0)
        mean_s = float(np.mean(sr))
        mean_b = float(np.mean(br))
        alpha = mean_s - daily_rf - beta * (mean_b - daily_rf)
        if not np.isfinite(alpha):
            alpha = 0.0
        alpha = max(-1.0, min(1.0, alpha))

        return {
            "symbol": symbol,
            "correlation": round(corr, 4),
            "beta": round(beta, 4),
            "alpha": round(alpha, 6),
            "r_squared": round(r_sq, 4),
            "n": n,
        }

    def compute_metrics_from_histories(
        self,
        symbol: str,
        stock_prices: List[float],
        benchmark_prices: List[float],
        risk_free_rate: float = 0.03,
    ) -> Dict[str, Any]:
        """Convenience — compute metrics from price lists directly."""
        if stock_prices is None or benchmark_prices is None or len(stock_prices) < 3 or len(benchmark_prices) < 3:
            return self.compute_metrics(symbol, np.array([]), np.array([]))
        sr = _returns(np.array(stock_prices, dtype=float))
        br = _returns(np.array(benchmark_prices, dtype=float))
        return self.compute_metrics(symbol, sr, br, risk_free_rate)

    # ── Fetch & rank ──────────────────────────────────────────────────────

    def score_symbol(
        self,
        symbol: str,
        period: str = "6mo",
        risk_free_rate: float = 0.03,
        force_refresh: bool = False,
    ) -> Dict[str, Any]:
        """Fetch price history for *symbol* and its benchmark, return metrics.

        Results are cached for CACHE_TTL_S seconds.  Pass *force_refresh=True*
        to bypass cache.
        """
        if not force_refresh:
            cached = self._score_cache.get(symbol)
            ts = self._cache_ts.get(symbol, 0.0)
            if cached is not None and (datetime.now().timestamp() - ts) < self.CACHE_TTL_S:
                return cached

        if self.mdh is None:
            return {"symbol": symbol, "error": "MarketDataHandler not available"}

        benchmark = self.get_benchmark(symbol)

        try:
            stock_bars = self.mdh.fetch_historical_data(symbol, period=period)
            bench_bars = self.mdh.fetch_historical_data(benchmark, period=period)
        except Exception as e:
            logger.error("fetch failed for %s: %s", symbol, e)
            return {"symbol": symbol, "error": str(e)}

        if not stock_bars or not bench_bars:
            return {"symbol": symbol, "error": "No historical data"}

        stock_closes = [b.close for b in stock_bars if not isinstance(b, (int, float))]
        bench_closes = [b.close for b in bench_bars if not isinstance(b, (int, float))]

        if len(stock_closes) < 5 or len(bench_closes) < 5:
            return {"symbol": symbol, "error": "Insufficient data points"}

        metrics = self.compute_metrics_from_histories(symbol, stock_closes, bench_closes, risk_free_rate)

        # Additional relative-strength indicators
        s_first = stock_closes[0]
        s_last = stock_closes[-1]
        b_first = bench_closes[0]
        b_last = bench_closes[-1]
        stock_return = (s_last - s_first) / s_first if (s_first > 0 and np.isfinite(s_first) and np.isfinite(s_last)) else 0.0
        bench_return = (b_last - b_first) / b_first if (b_first > 0 and np.isfinite(b_first) and np.isfinite(b_last)) else 0.0
        relative_strength = stock_return - bench_return  # excess return
        if not np.isfinite(relative_strength):
            relative_strength = 0.0

        # Volatility ratio (stock vol / bench vol)
        sr = _returns(np.array(stock_closes, dtype=float))
        br = _returns(np.array(bench_closes, dtype=float))
        stock_vol = float(np.std(sr)) if len(sr) > 1 else 0.0
        bench_vol = float(np.std(br)) if len(br) > 1 else 0.0
        vol_ratio = stock_vol / max(bench_vol, 1e-10)
        if not np.isfinite(vol_ratio):
            vol_ratio = 1.0

        # Composite score: weighted sum of alpha, relative_strength,
        # and inversed vol_ratio (lower relative vol = better risk-adjusted)
        alpha_val = metrics.get("alpha", 0.0)
        alpha_val = float(alpha_val) if (alpha_val is not None and np.isfinite(float(alpha_val))) else 0.0
        alpha_score = max(-0.05, min(0.05, alpha_val)) * 100  # scale
        rs_score = max(-0.5, min(0.5, relative_strength)) * 2
        vol_score = max(-1.0, min(1.0, 1.0 - vol_ratio)) if vol_ratio > 0 else 0.0

        composite = round(alpha_score * 0.5 + rs_score * 0.3 + vol_score * 0.2, 4)
        if not np.isfinite(composite):
            composite = 0.0

        metrics.update(
            {
                "benchmark": benchmark,
                "stock_return_pct": round(stock_return * 100, 2),
                "bench_return_pct": round(bench_return * 100, 2),
                "relative_strength_pct": round(relative_strength * 100, 2),
                "stock_volatility": round(stock_vol, 6),
                "bench_volatility": round(bench_vol, 6),
                "vol_ratio": round(vol_ratio, 4),
                "composite_score": composite,
                "period": period,
            }
        )
        self._score_cache[symbol] = metrics
        self._cache_ts[symbol] = datetime.now().timestamp()
        return metrics

    def rank_symbols(
        self,
        symbols: List[str],
        period: str = "6mo",
        top_n: int = 10,
        min_correlation: float = 0.0,
        risk_free_rate: float = 0.03,
    ) -> List[Dict[str, Any]]:
        """Score a list of symbols and return the top *top_n* by composite score.

        Parameters
        ----------
        symbols : list of tickers
        period : str (e.g. "6mo", "1y")
        top_n : int — how many to return
        min_correlation : float — skip stocks with |correlation| below this
        risk_free_rate : float

        Returns
        -------
        List[Dict] sorted by composite_score descending.
        """
        results: List[Dict[str, Any]] = []
        for sym in symbols:
            score = self.score_symbol(sym, period=period, risk_free_rate=risk_free_rate)
            if "error" in score:
                logger.debug("Skipping %s: %s", sym, score["error"])
                continue
            corr = score.get("correlation", 0.0)
            if abs(corr) < min_correlation:
                logger.debug("Skipping %s: correlation %.3f below threshold", sym, corr)
                continue
            results.append(score)

        results.sort(key=lambda r: r.get("composite_score", -999), reverse=True)
        for rank, r in enumerate(results, 1):
            r["rank"] = rank
        return results[:top_n]

    def get_market_overview(self, symbols: List[str], period: str = "6mo") -> Dict[str, Any]:
        """Return a combined view: global snapshot + top stock ranks."""
        gm_summary = self.gm.get_summary()
        rankings = self.rank_symbols(symbols, period=period)
        return {
            "global_markets": gm_summary,
            "rankings": rankings,
            "total_scanned": len(symbols),
            "period": period,
        }


__all__ = [
    "REGION_BENCHMARKS",
    "RelativeStrengthAnalyzer",
    "_benchmark_for_symbol",
    "_guess_region",
]
