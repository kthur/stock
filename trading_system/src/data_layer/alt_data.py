import logging
from datetime import datetime
from typing import Any, Dict

import numpy as np
import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)


class AlternativeDataClient:
    """대체 데이터(Alternative Data) 수집 - 시장 레짐 및 추세 탐지"""

    def __init__(self):
        self._cache = {}
        self._last_spx_fetch: datetime | None = None
        self._spx_history: list = []

    def fetch_put_call_ratio(self, start_date: str) -> pd.Series:
        """
        Fetches historical CBOE Options Put/Call Ratio (^CPC) using yfinance.
        Falls back to generating a realistic Series if empty or error.
        """
        try:
            logger.info("Attempting to fetch CBOE Put/Call Ratio (^CPC)...")
            ticker = yf.Ticker("^CPC")
            df = ticker.history(start=start_date)
            if not df.empty and 'Close' in df.columns:
                return df['Close'].ffill().fillna(0.6)
        except Exception as e:
            logger.warning(f"Failed to fetch Put/Call Ratio via yfinance: {e}")

        # Fallback: generate a realistic put/call ratio series (mean around 0.6)
        logger.info("Generating fallback simulated Put/Call Ratio data.")
        dates = pd.date_range(start=start_date, end=datetime.now(), freq="B")
        np.random.seed(42)
        pcc = 0.6 + np.random.normal(0, 0.08, size=len(dates))
        pcc = np.clip(pcc, 0.3, 1.2)
        return pd.Series(pcc, index=dates)

    def fetch_vix(self) -> float:
        try:
            vix = yf.Ticker("^VIX")
            hist = vix.history(period="1d")
            if not hist.empty and "Close" in hist.columns:
                val = float(hist["Close"].iloc[-1])
                return val if np.isfinite(val) and val > 0 else 20.0
            return 20.0
        except Exception as e:
            logger.error(f"VIX fetch failed: {e}")
            return 20.0

    def fetch_fear_and_greed_proxy(self) -> str:
        vix = self.fetch_vix()
        if vix >= 30:
            return "EXTREME_FEAR"
        elif vix >= 20:
            return "FEAR"
        elif vix <= 12:
            return "EXTREME_GREED"
        elif vix <= 15:
            return "GREED"
        return "NEUTRAL"

    def _fetch_spx_trend(self) -> Dict[str, Any]:
        try:
            spx = yf.Ticker("^GSPC")
            hist = spx.history(period="6mo")
            if hist.empty or len(hist) < 50:
                return {"trend": "NEUTRAL", "strength": 0.0}
            closes = hist["Close"].values
            closes = np.nan_to_num(closes, nan=1.0, posinf=1.0, neginf=1.0)
            if len(closes) < 50:
                return {"trend": "NEUTRAL", "strength": 0.0}
            sma50 = float(np.mean(closes[-50:]))
            sma200 = float(np.mean(closes[-200:])) if len(closes) >= 200 else sma50
            current = float(closes[-1])
            returns_1m = float((closes[-1] / closes[-21] - 1.0)) if len(closes) >= 21 and closes[-21] > 0 and np.isfinite(closes[-21]) else 0.0
            returns_3m = float((closes[-1] / closes[-63] - 1.0)) if len(closes) >= 63 and closes[-63] > 0 and np.isfinite(closes[-63]) else 0.0

            if current > sma50 and returns_1m > 0.02:
                trend = "BULL"
                strength = min(abs(returns_3m) * 5.0, 1.0)
            elif current < sma50 and returns_1m < -0.02:
                trend = "BEAR"
                strength = min(abs(returns_3m) * 5.0, 1.0)
            elif sma50 > sma200:
                trend = "BULLISH"
                strength = 0.3
            elif sma50 < sma200:
                trend = "BEARISH"
                strength = 0.3
            else:
                trend = "NEUTRAL"
                strength = 0.0

            self._spx_history = closes.tolist()
            return {"trend": trend, "strength": round(strength, 3)}
        except Exception as e:
            logger.error(f"SPX fetch failed: {e}")
            return {"trend": "NEUTRAL", "strength": 0.0}

    def _detect_volatility_regime(self, vix: float) -> str:
        if vix >= 30:
            return "CRISIS"
        elif vix >= 25:
            return "HIGH_VOL"
        elif vix >= 18:
            return "NORMAL"
        elif vix >= 12:
            return "LOW_VOL"
        else:
            return "COMPRESSION"

    def get_market_regime(self) -> Dict[str, Any]:
        vix = self.fetch_vix()
        vix_clean = float(vix) if (vix is not None and np.isfinite(vix)) else 20.0
        vix_safe = float(np.clip(vix_clean, 8.0, 100.0))

        sentiment = self.fetch_fear_and_greed_proxy()
        trend_info = self._fetch_spx_trend()
        vol_regime = self._detect_volatility_regime(vix_safe)

        trend = trend_info["trend"]
        trend_strength = trend_info["strength"] * (1.0 if trend in ("BULL", "BULLISH") else -1.0)

        return {
            "vix": vix_safe,
            "sentiment": sentiment,
            "volatility_regime": vol_regime,
            "trend": trend,
            "trend_strength": trend_strength,
            "is_high_volatility": vix_safe > 25,
            "is_bull_market": trend in ("BULL", "BULLISH"),
            "is_bear_market": trend in ("BEAR", "BEARISH"),
            "regime_score": round(trend_strength * 0.6 + (1.0 - vix_safe / 50.0) * 0.4, 3),
        }
