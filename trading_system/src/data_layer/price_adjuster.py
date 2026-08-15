"""
price_adjuster.py — Corporate Action & Stock Split Resilient Price Adjuster

Detects price discontinuities (splits, reverse splits, corporate actions)
and normalizes OHLCV price series to ensure continuous, reliable input
for all 23 multi-factor quantitative strategy engines.
"""

from __future__ import annotations

import logging
import pandas as pd

logger = logging.getLogger(__name__)


class CorporateActionAdjuster:
    """Detects and adjusts stock split price jumps/drops in OHLCV DataFrames."""

    def __init__(self, split_threshold_pct: float = 0.40) -> None:
        self.split_threshold_pct = split_threshold_pct

    def adjust_ohlcv(self, df_prices: pd.DataFrame) -> pd.DataFrame:
        """Detect unadjusted stock split price gaps and scale OHLCV appropriately.

        Args:
            df_prices: OHLCV DataFrame with Date/Datetime index or column and 'Close', 'Open', 'High', 'Low', 'Volume'.

        Returns:
            Cleaned and split-adjusted OHLCV DataFrame.
        """
        if df_prices is None or df_prices.empty:
            return df_prices

        close_col = None
        for col in ["Close", "close"]:
            if col in df_prices.columns:
                close_col = col
                break
        if close_col is None or len(df_prices) < 2:
            return df_prices

        df = df_prices.copy()
        close_series = df[close_col]
        if isinstance(close_series, pd.DataFrame):
            close_series = close_series.iloc[:, 0]

        # Calculate overnight price ratios
        prev_close = close_series.shift(1).replace(0, float('nan'))
        ratios = (close_series / prev_close).fillna(1.0)

        # Detect split ratio anomalies (e.g., 1:2 split -> 0.50, 1:5 split -> 0.20, 5:1 reverse split -> 5.0)
        split_mask = (ratios < (1.0 - self.split_threshold_pct)) | (ratios > (1.0 + 1.5 * self.split_threshold_pct))

        if split_mask.any():
            split_indices = df.index[split_mask]
            for idx in split_indices:
                r = float(ratios.loc[idx])
                if r <= 0:
                    continue
                logger.info("[CorporateActionAdjuster] Stock split/action ratio %.2fx detected at %s. Adjusting prior history...", r, idx)

                # Backward adjust prior prices before split
                prior_mask = df.index < idx
                price_cols = [c for c in df.columns if str(c).lower() in ["open", "high", "low", "close", "adj close"]]
                for pc in price_cols:
                    df[pc] = df[pc].astype(float)
                df.loc[prior_mask, price_cols] = df.loc[prior_mask, price_cols] * r
                vol_cols = [c for c in df.columns if str(c).lower() == "volume"]
                if vol_cols:
                    df[vol_cols[0]] = df[vol_cols[0]].astype(float)
                    df.loc[prior_mask, vol_cols[0]] = df.loc[prior_mask, vol_cols[0]] / r

        return df

    def filter_price_spikes(self, df_prices: pd.DataFrame, max_spike_pct: float = 3.0) -> pd.DataFrame:
        """Sanity filter to clean single-day abnormal spikes (> 300%) or unadjusted splits."""
        from src.data_layer.data_validator import filter_price_spikes
        return filter_price_spikes(df_prices, max_return=max_spike_pct)


def filter_price_spikes(df: pd.DataFrame, max_spike_pct: float = 3.0) -> pd.DataFrame:
    """Sanity filter function to clean single-day abnormal spikes (> 300%) or unadjusted splits."""
    from src.data_layer.data_validator import filter_price_spikes as dv_filter
    return dv_filter(df, max_return=max_spike_pct)
