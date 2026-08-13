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

from .base_strategy import BaseStrategyEngine

logger = logging.getLogger(__name__)


from src.core.strategy_registry import register_strategy, StrategyMeta


@register_strategy(
    StrategyMeta(
        strategy_id="trend_efficiency",
        display_name="Kaufman Trend Efficiency",
        score_column="trend_efficiency_score",
        category="factor",
        output_file="trend_efficiency_predictions.txt",
        default_regime_weights={
            "BEAR": 0.01, "BEAR_HIGH_VOL": 0.00, "SIDEWAYS_LOW_VOL": 0.04, "BULL_HIGH_VOL": 0.08, "BULL_LOW_VOL": 0.06
        },
    )
)
class TrendEfficiencyEngine(BaseStrategyEngine):
    """
    Computes Trend Efficiency Score [0.0, 1.0] for stocks.
    High Score = Smooth, high-purity upward trend with high Kaufman Efficiency Ratio (KER) & low noise.
    Low Score = Choppy, noisy movement or downward trend.
    """

    def __init__(self, config: Optional[Any] = None) -> None:
        self.config = config

    def compute_scores(
        self,
        prices_dict: Dict[str, pd.DataFrame],
        fundamentals_dict: Optional[Dict[str, Dict[str, Any]]] = None,
        indicators_df: Optional[pd.DataFrame] = None,
        **kwargs
    ) -> pd.DataFrame:
        symbols = list(prices_dict.keys()) if prices_dict else []
        return self.calculate_scores(symbols, prices_dict=prices_dict, features_df=fundamentals_dict)

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

        valid_cols = {}
        for sym in symbols:
            sym_str = str(sym)
            p_df = prices_dict.get(sym_str, prices_dict.get(sym))
            if isinstance(p_df, pd.DataFrame):
                close_col = 'close' if 'close' in p_df.columns else ('Close' if 'Close' in p_df.columns else None)
                if close_col:
                    c_series = p_df[close_col].dropna()
                    if len(c_series) >= 21:
                        valid_cols[sym_str] = c_series

        if not valid_cols:
            df_out = pd.DataFrame({'symbol': [str(s) for s in symbols], 'trend_efficiency_score': 0.50})
            return df_out[['symbol', 'trend_efficiency_score']]

        # Date-aligned price matrix
        close_2d = pd.DataFrame(valid_cols).ffill().tail(21)
        if len(close_2d) < 21:
            df_out = pd.DataFrame({'symbol': [str(s) for s in symbols], 'trend_efficiency_score': 0.50})
            return df_out[['symbol', 'trend_efficiency_score']]

        change_5 = (close_2d.iloc[-1] - close_2d.iloc[-6]).abs()
        vol_5 = close_2d.iloc[-6:].diff().abs().sum(axis=0)
        ker5 = np.where(vol_5 > 1e-8, change_5 / vol_5, 0.0)

        change_10 = (close_2d.iloc[-1] - close_2d.iloc[-11]).abs()
        vol_10 = close_2d.iloc[-11:].diff().abs().sum(axis=0)
        ker10 = np.where(vol_10 > 1e-8, change_10 / vol_10, 0.0)

        change_20 = (close_2d.iloc[-1] - close_2d.iloc[-21]).abs()
        vol_20 = close_2d.iloc[-21:].diff().abs().sum(axis=0)
        ker20 = np.where(vol_20 > 1e-8, change_20 / vol_20, 0.0)

        avg_ker = (ker5 + ker10 + ker20) / 3.0
        ret_20d = (close_2d.iloc[-1] / close_2d.iloc[-21]) - 1.0

        # R/S Hurst Exponent over 20 days
        diffs = close_2d.diff().iloc[1:]
        mean_diff = diffs.mean(axis=0)
        deviations = (diffs - mean_diff).cumsum(axis=0)
        r_range = deviations.max(axis=0) - deviations.min(axis=0)
        s_std = diffs.std(axis=0, ddof=1).replace(0, 1e-8)
        rs = np.maximum(r_range / s_std, 1e-4)
        hurst = np.clip(np.log(rs) / np.log(20.0), 0.1, 0.9)

        # Signed trend score: High KER + High Hurst on uptrend yields high score; downtrend penalizes
        score_arr = np.where(
            ret_20d >= 0,
            0.5 + 0.5 * avg_ker * (hurst / 0.5),
            0.5 - 0.5 * avg_ker * (hurst / 0.5)
        )

        results = dict(zip(close_2d.columns, score_arr))
        df_out = pd.DataFrame([{'symbol': str(s), 'raw_score': results.get(str(s), np.nan)} for s in symbols])
        valid_mask = df_out['raw_score'].notna() & np.isfinite(df_out['raw_score'])

        if valid_mask.sum() > 0:
            ranks = df_out.loc[valid_mask, 'raw_score'].rank(pct=True, ascending=True)
            df_out.loc[valid_mask, 'trend_efficiency_score'] = ranks
        else:
            df_out['trend_efficiency_score'] = 0.50

        df_out['trend_efficiency_score'] = df_out['trend_efficiency_score'].fillna(0.50).astype(float)

        return df_out[['symbol', 'trend_efficiency_score']]


# Alias for backward compatibility
KaufmanTrendEfficiencyEngine = TrendEfficiencyEngine
