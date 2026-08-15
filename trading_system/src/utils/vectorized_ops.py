"""
High-Performance Vectorized Feature Engine

Provides optimized NumPy vectorization for technical indicators and feature engineering
to reduce inference latency across 3,379 symbols.
"""

from typing import Tuple
import numpy as np
import pandas as pd


class VectorizedFeatureEngine:
    """Vectorized calculation routines for high-speed technical indicator computation."""

    @staticmethod
    def rsi_vectorized(prices: np.ndarray, period: int = 14) -> np.ndarray:
        """Fast vectorized Relative Strength Index (RSI)."""
        safe_period = max(1, int(period)) if period is not None else 14
        if prices is None or len(prices) <= safe_period:
            return np.full_like(prices, 50.0) if prices is not None else np.array([])

        deltas = np.diff(prices)
        seed = deltas[:period]
        up = seed[seed >= 0].sum() / period
        down = -seed[seed < 0].sum() / period

        if down == 0:
            rs = 100.0
        else:
            rs = up / down

        rsi = np.zeros_like(prices)
        rsi[:period] = 100.0 - (100.0 / (1.0 + rs))

        up_vals = np.where(deltas > 0, deltas, 0.0)
        down_vals = np.where(deltas < 0, -deltas, 0.0)

        for i in range(period, len(prices)):
            up = (up * (period - 1) + up_vals[i - 1]) / period
            down = (down * (period - 1) + down_vals[i - 1]) / period

            if down == 0:
                rsi[i] = 100.0
            else:
                rsi[i] = 100.0 - (100.0 / (1.0 + (up / down)))

        return rsi

    @staticmethod
    def bollinger_bands_vectorized(
        prices: np.ndarray, window: int = 20, num_std: float = 2.0
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Vectorized Bollinger Bands calculation returning (upper, middle, lower)."""
        if len(prices) < window:
            return prices.copy(), prices.copy(), prices.copy()

        df_series = pd.Series(prices)
        rolling = df_series.rolling(window=window, min_periods=1)
        sma = rolling.mean().to_numpy()
        std = rolling.std(ddof=0).fillna(0.0).to_numpy()

        upper = sma + (std * num_std)
        lower = sma - (std * num_std)
        return upper, sma, lower

    @staticmethod
    def compute_fast_indicators(df: pd.DataFrame) -> pd.DataFrame:
        """Computes technical indicator set directly on a DataFrame with zero allocation overhead."""
        if df.empty or "close" not in df.columns:
            return df

        closes = df["close"].to_numpy(dtype=np.float64)

        df["rsi_14"] = VectorizedFeatureEngine.rsi_vectorized(closes, period=14)
        upper, sma, lower = VectorizedFeatureEngine.bollinger_bands_vectorized(closes, window=20)
        df["bb_upper"] = upper
        df["bb_middle"] = sma
        df["bb_lower"] = lower
        df["bb_pct_b"] = np.where((upper - lower) == 0, 0.5, (closes - lower) / np.maximum(1e-6, upper - lower))

        return df
