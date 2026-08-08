"""
trading_system/src/core/trend_efficiency.py
Strategy #27: Kaufman Trend Efficiency & Fractal Persistence Engine.
Calculates multi-window Kaufman Efficiency Ratio (KER) and trend directionality to filter out
choppy sideways noise and select high-conviction, low-noise directional trenders.
"""

import logging
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class TrendEfficiencyEngine:
    """
    Computes Trend Efficiency Score [0.0, 1.0] for stocks.
    High Score = Smooth, high-purity upward trend with high Kaufman Efficiency Ratio (KER) & low noise.
    Low Score = Choppy, noisy movement or downward trend.
    """

    def __init__(self, config: Optional[Any] = None) -> None:
        self.config = config

    def _compute_ker(self, series: pd.Series, window: int) -> float:
        """Calculates Kaufman Efficiency Ratio over window."""
        if len(series) < window + 1:
            return 0.0
        change = abs(series.iloc[-1] - series.iloc[-1 - window])
        volatility = series.iloc[-window-1:].diff().abs().sum()
        if volatility <= 1e-8:
            return 0.0
        return float(change / volatility)

    def calculate_scores(
        self,
        symbols: list,
        prices_dict: Optional[Dict[str, pd.DataFrame]] = None,
        features_df: Optional[Any] = None
    ) -> pd.DataFrame:
        """
        Computes Trend Efficiency Score per symbol.
        Returns DataFrame with ['symbol', 'trend_efficiency_score'].
        """
        if not symbols or not prices_dict:
            return pd.DataFrame(columns=['symbol', 'trend_efficiency_score'])

        results = {}
        for sym in symbols:
            sym_str = str(sym)
            p_df = prices_dict.get(sym_str, prices_dict.get(sym))

            if not isinstance(p_df, pd.DataFrame) or len(p_df) < 21:
                results[sym_str] = np.nan
                continue

            close_col = 'close' if 'close' in p_df.columns else 'Close'
            if close_col not in p_df.columns:
                results[sym_str] = np.nan
                continue

            c_series = p_df[close_col].dropna()
            if len(c_series) < 21:
                results[sym_str] = np.nan
                continue

            # Calculate KER across 5D, 10D, 20D
            ker5 = self._compute_ker(c_series, 5)
            ker10 = self._compute_ker(c_series, 10)
            ker20 = self._compute_ker(c_series, 20)
            avg_ker = (ker5 + ker10 + ker20) / 3.0

            # Directional multiplier (positive trend gets bonus, negative gets penalty)
            ret_20d = (c_series.iloc[-1] / c_series.iloc[-21]) - 1.0

            if ret_20d > 0:
                score = avg_ker * (1.0 + min(1.0, ret_20d * 2.0))
            else:
                score = avg_ker * max(0.1, 1.0 + ret_20d)

            results[sym_str] = float(score)

        df_out = pd.DataFrame(list(results.items()), columns=['symbol', 'raw_score'])
        valid_mask = df_out['raw_score'].notna() & np.isfinite(df_out['raw_score'])

        if valid_mask.sum() > 0:
            ranks = df_out.loc[valid_mask, 'raw_score'].rank(pct=True, ascending=True)
            df_out.loc[valid_mask, 'trend_efficiency_score'] = ranks.clip(0.05, 0.95)
        else:
            df_out['trend_efficiency_score'] = 0.50

        df_out['trend_efficiency_score'] = df_out['trend_efficiency_score'].fillna(0.50).astype(float)

        return df_out[['symbol', 'trend_efficiency_score']]


# Alias for backward compatibility
KaufmanTrendEfficiencyEngine = TrendEfficiencyEngine
