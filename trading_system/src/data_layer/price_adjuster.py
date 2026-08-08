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
        if df_prices is None or df_prices.empty or "Close" in df_prices.columns and len(df_prices) < 2:
            return df_prices

        df = df_prices.copy()
        close_series = df["Close"]
        if isinstance(close_series, pd.DataFrame):
            close_series = close_series.iloc[:, 0]

        # Calculate overnight price ratios
        ratios = (close_series / close_series.shift(1)).fillna(1.0)

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
                price_cols = [c for c in ["Open", "High", "Low", "Close", "Adj Close"] if c in df.columns]
                df.loc[prior_mask, price_cols] = df.loc[prior_mask, price_cols] * r
                if "Volume" in df.columns:
                    df.loc[prior_mask, "Volume"] = df.loc[prior_mask, "Volume"] / r

        return df
