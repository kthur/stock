"""
total_return.py — Total Return Index (TRI) & Ex-Dividend Mean Reversion Alpha Engine

Reconstructs dividend-reinvested price series to prevent false trend breakdown signals
on ex-dividend dates and models short-term post-dividend mean-reversion rebound alpha.
"""

from __future__ import annotations

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any, Union

logger = logging.getLogger(__name__)


class TotalReturnEngine:
    """
    Total Return Index (TRI) Reconstructor and Dividend Capture Alpha Model.
    """

    def __init__(
        self,
        ex_date_window_pre: int = 5,  # 5 days before ex-date
        ex_date_window_post: int = 4   # 4 days after ex-date
    ):
        self.window_pre = ex_date_window_pre
        self.window_post = ex_date_window_post

    def build_total_return_series(
        self,
        prices: Union[pd.Series, np.ndarray],
        dividends: Union[pd.Series, np.ndarray]
    ) -> pd.Series:
        """
        Reconstructs dividend-reinvested Total Return Index (TRI):
        P_TRI(t) = P_TRI(t-1) * [ (P(t) + D(t)) / P(t-1) ]
        """
        p = np.asarray(prices, dtype=np.float64).ravel()
        d = np.nan_to_num(np.asarray(dividends, dtype=np.float64).ravel(), nan=0.0)
        
        N = len(p)
        if N == 0:
            return pd.Series([], dtype=np.float64)
        if N == 1:
            return pd.Series([p[0]], dtype=np.float64)

        tri = np.zeros(N, dtype=np.float64)
        tri[0] = p[0]

        for t in range(1, N):
            p_prev = max(p[t-1], 1e-4)
            p_curr = p[t]
            div = d[t]
            # Total return growth factor
            growth = (p_curr + div) / p_prev
            tri[t] = tri[t-1] * max(growth, 0.01)

        idx = prices.index if isinstance(prices, pd.Series) else pd.RangeIndex(N)
        return pd.Series(tri, index=idx, name="total_return_index")

    def compute_dividend_capture_score(
        self,
        dividend_yield: float,
        days_to_ex_date: int,
        market_median_yield: float = 0.020,
        market_std_yield: float = 0.015
    ) -> Dict[str, Any]:
        """
        Calculates Dividend Capture Mean-Reversion Alpha Score:
        High-dividend stocks within [-5d, +4d] of ex-dividend date exhibit empirical mean-reverting bounce.
        """
        std_yield = max(market_std_yield, 1e-4)
        # Z-score of dividend yield
        z_yield = (dividend_yield - market_median_yield) / std_yield

        # Proximity indicator to ex-date
        in_capture_window = (-self.window_pre <= days_to_ex_date <= self.window_post)
        
        if in_capture_window and z_yield > 0.0:
            # Gaussian bell curve centered at ex-date (t=0)
            time_decay = np.exp(-0.5 * (days_to_ex_date / 2.0) ** 2)
            # Sigmoid bounded score [0.5, 1.0]
            raw_score = 0.50 + 0.50 * (1.0 / (1.0 + np.exp(-z_yield))) * time_decay
        else:
            raw_score = 0.50 # Neutral

        return {
            "dividend_capture_score": round(float(raw_score), 4),
            "in_capture_window": in_capture_window,
            "yield_z_score": round(float(z_yield), 3),
            "days_to_ex_date": days_to_ex_date
        }

    def filter_false_breakdown_signals(
        self,
        raw_price_series: pd.Series,
        tri_price_series: pd.Series,
        breakdown_threshold: float = -0.025
    ) -> bool:
        """
        Checks if a perceived price breakdown on ex-dividend day is purely an artifact
        of mechanical cash dividend payout rather than genuine structural trend failure.
        """
        if len(raw_price_series) < 2 or len(tri_price_series) < 2:
            return False

        raw_ret = (raw_price_series.iloc[-1] - raw_price_series.iloc[-2]) / max(raw_price_series.iloc[-2], 1e-4)
        tri_ret = (tri_price_series.iloc[-1] - tri_price_series.iloc[-2]) / max(tri_price_series.iloc[-2], 1e-4)

        # False breakdown: Raw price fell below threshold, but TRI remained stable
        is_false_breakdown = (raw_ret < breakdown_threshold) and (tri_ret >= -0.005)
        return is_false_breakdown
