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
        if volatility <= 1e-8 or not (np.isfinite(change) and np.isfinite(volatility)):
            return 0.0
        return float(np.clip(change / max(volatility, 1e-8), 0.0, 1.0))

    def calculate_scores(
        self,
        symbols: Any,
        prices_dict: Optional[Dict[str, pd.DataFrame]] = None,
        features_df: Optional[Any] = None
    ) -> pd.DataFrame:
        """
        Computes Trend Efficiency Score per symbol.
        Returns DataFrame with ['symbol', 'trend_efficiency_score'].
        """
        if symbols is None or not prices_dict:
            return pd.DataFrame(columns=['symbol', 'trend_efficiency_score'])

        if isinstance(symbols, pd.DataFrame):
            if symbols.empty:
                return pd.DataFrame(columns=['symbol', 'trend_efficiency_score'])
            sym_list = symbols['symbol'].tolist() if 'symbol' in symbols.columns else symbols.index.tolist()
        elif isinstance(symbols, pd.Series):
            if symbols.empty:
                return pd.DataFrame(columns=['symbol', 'trend_efficiency_score'])
            sym_list = symbols.tolist()
        else:
            sym_list = list(symbols)
            if not sym_list:
                return pd.DataFrame(columns=['symbol', 'trend_efficiency_score'])

        valid_cols = {}
        for sym in sym_list:
            sym_str = str(sym)
            p_df = prices_dict.get(sym_str, prices_dict.get(sym))
            if isinstance(p_df, pd.DataFrame):
                close_col = 'close' if 'close' in p_df.columns else ('Close' if 'Close' in p_df.columns else None)
                if close_col:
                    c_series = p_df[close_col].dropna()
                    if len(c_series) >= 21:
                        valid_cols[sym_str] = c_series

        if not valid_cols:
            df_out = pd.DataFrame({'symbol': [str(s) for s in sym_list], 'trend_efficiency_score': np.nan})
            return df_out[['symbol', 'trend_efficiency_score']]

        # Full price matrix for extended Hurst calculation (up to 120 days)
        close_full = pd.DataFrame(valid_cols).ffill()
        n_hurst_obs = min(120, len(close_full))
        close_hurst = close_full.tail(n_hurst_obs)

        # 20-day slice for KER
        close_2d = close_full.tail(21)
        if len(close_2d) < 21:
            df_out = pd.DataFrame({'symbol': [str(s) for s in sym_list], 'trend_efficiency_score': np.nan})
            return df_out[['symbol', 'trend_efficiency_score']]

        # Vectorized KER across columns
        change_5 = (close_2d.iloc[-1] - close_2d.iloc[-6]).abs()
        vol_5 = close_2d.iloc[-6:].diff().abs().sum(axis=0)
        ker5 = np.where(vol_5 > 1e-8, change_5 / vol_5, 0.0)

        change_10 = (close_2d.iloc[-1] - close_2d.iloc[-11]).abs()
        vol_10 = close_2d.iloc[-11:].diff().abs().sum(axis=0)
        ker10 = np.where(vol_10 > 1e-8, change_10 / vol_10, 0.0)

        change_20 = (close_2d.iloc[-1] - close_2d.iloc[-21]).abs()
        vol_20 = close_2d.iloc[-21:].diff().abs().sum(axis=0)
        ker20 = np.where(vol_20 > 1e-8, change_20 / vol_20, 0.0)

        weighted_ker = 0.50 * ker5 + 0.30 * ker10 + 0.20 * ker20
        base_p = close_2d.iloc[-21].clip(lower=1e-8)
        ret_20d = (close_2d.iloc[-1] / base_p) - 1.0

        # R/S Hurst Exponent over extended lookback window (up to 120 days, min 20) with finite-sample correction
        h_len = len(close_hurst)
        if h_len >= 20:
            diffs_h = close_hurst.diff().iloc[1:]
            mean_diff_h = diffs_h.mean(axis=0)
            dev_h = (diffs_h - mean_diff_h).cumsum(axis=0)
            r_range_h = dev_h.max(axis=0) - dev_h.min(axis=0)
            s_std_h = diffs_h.std(axis=0, ddof=1).clip(lower=1e-8)
            flat_mask = (r_range_h <= 1e-8) | (s_std_h <= 1e-8)
            rs_h = np.maximum(r_range_h / s_std_h, 1e-4)
            n_obs = float(max(20, h_len))
            # Expected R/S under null hypothesis of random walk (Anis-Lloyd / Peters correction)
            e_rs = np.sqrt(np.pi * n_obs / 2.0) if n_obs > 50 else ((n_obs - 0.5) / n_obs) * np.sqrt(np.pi * n_obs / 2.0)
            e_rs = max(float(e_rs), 1e-8)
            hurst = 0.50 + (np.log(np.maximum(rs_h, 1e-8)) - np.log(e_rs)) / np.log(max(n_obs, 2.0))
            hurst = np.nan_to_num(hurst, nan=0.50, posinf=0.90, neginf=0.10)
            hurst = np.clip(hurst, 0.1, 0.9)
            hurst = np.where(flat_mask, 0.50, hurst)
        else:
            hurst = np.full(len(close_2d.columns), 0.50)

        # Signed trend score: High KER + High Hurst on uptrend yields high score; downtrend penalizes
        # Elite persistent trend accelerator & fractal mean-reverting noise filter
        trend_mult = np.where((weighted_ker > 0.60) & (hurst > 0.60) & (ret_20d > 0.08), 1.30,
                              np.where((weighted_ker > 0.55) & (hurst > 0.56) & (ret_20d > 0.04), 1.20,
                              np.where((weighted_ker > 0.45) & (hurst > 0.52) & (ret_20d > 0.02), 1.10,
                              np.where((hurst < 0.45) & (np.abs(ret_20d) < 0.03), 0.80, 1.0))))
        raw_score = np.where(
            ret_20d >= 0,
            0.5 + 0.5 * weighted_ker * (hurst / 0.5) * trend_mult,
            0.5 - 0.5 * weighted_ker * (hurst / 0.5) * 1.10
        )
        score_arr = np.clip(np.where(np.isfinite(raw_score), raw_score, 0.50), 0.0, 1.0)

        results = dict(zip(close_2d.columns, score_arr))
        df_out = pd.DataFrame([{'symbol': str(s), 'raw_score': results.get(str(s), np.nan)} for s in sym_list])
        valid_mask = df_out['raw_score'].notna() & np.isfinite(df_out['raw_score'])

        if valid_mask.sum() > 1:
            ranks = df_out.loc[valid_mask, 'raw_score'].rank(pct=True, ascending=True).clip(0.02, 0.98)
            df_out.loc[valid_mask, 'trend_efficiency_score'] = ranks
        elif valid_mask.sum() == 1:
            df_out.loc[valid_mask, 'trend_efficiency_score'] = 0.50
        else:
            df_out['trend_efficiency_score'] = np.nan

        df_out['trend_efficiency_score'] = df_out['trend_efficiency_score'].astype(float)

        return df_out[['symbol', 'trend_efficiency_score']]


# Alias for backward compatibility
KaufmanTrendEfficiencyEngine = TrendEfficiencyEngine
