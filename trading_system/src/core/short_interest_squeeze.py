"""
trading_system/src/core/short_interest_squeeze.py
Strategy #25: Short Interest & Squeeze Potential Engine.
Quantifies short selling pressure, Days-to-Cover (DTC), and price momentum to detect
explosive short squeeze opportunities and institutional short accumulation.
"""

import logging
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np

from src.core.base_strategy import BaseStrategyEngine
from src.core.strategy_registry import register_strategy, StrategyMeta

logger = logging.getLogger(__name__)


@register_strategy(
    StrategyMeta(
        strategy_id="short_squeeze",
        display_name="Short Interest & Squeeze",
        score_column="short_squeeze_score",
        category="catalyst",
        output_file="short_squeeze_predictions.txt",
        default_regime_weights={
            "BEAR": 0.02, "BEAR_HIGH_VOL": 0.01, "SIDEWAYS_LOW_VOL": 0.03, "BULL_HIGH_VOL": 0.05, "BULL_LOW_VOL": 0.03
        },
    )
)
class ShortInterestSqueezeEngine(BaseStrategyEngine):
    """
    Computes Short Interest & Squeeze Score [0.0, 1.0] for stocks.
    High Score = High short interest + High days-to-cover + Positive short-term momentum (Short Squeeze catalyst).
    Low Score = Low short interest or heavy downward price momentum driven by informed short sellers.
    """

    def __init__(self, config: Optional[Any] = None) -> None:
        self.config = config

    def compute_scores(
        self,
        prices_dict: Dict[str, pd.DataFrame],
        fundamentals_dict: Optional[Dict[str, Dict[str, Any]]] = None,
        indicators_df: Optional[pd.DataFrame] = None,
        **kwargs: Any,
    ) -> pd.DataFrame:
        symbols = list(prices_dict.keys()) if prices_dict else []
        return self.calculate_scores(symbols=symbols, prices_dict=prices_dict, **kwargs)

    def calculate_scores(
        self,
        symbols: list,
        prices_dict: Optional[Dict[str, pd.DataFrame]] = None,
        features_df: Optional[Any] = None
    ) -> pd.DataFrame:
        """
        Computes Short Interest & Squeeze Score per symbol.
        Returns DataFrame with ['symbol', 'short_squeeze_score'].
        """
        if not symbols:
            return pd.DataFrame(columns=['symbol', 'short_squeeze_score'])

        results = {}

        # Build lookup table from features_df or price history
        short_map = {}
        if features_df is not None:
            if isinstance(features_df, dict):
                for sym, df_item in features_df.items():
                    if isinstance(df_item, pd.DataFrame) and not df_item.empty:
                        short_map[str(sym)] = df_item.iloc[-1].to_dict()
                    elif isinstance(df_item, dict):
                        short_map[str(sym)] = df_item
            elif isinstance(features_df, pd.DataFrame) and not features_df.empty:
                if 'symbol' in features_df.columns:
                    deduped = features_df.drop_duplicates(subset=['symbol'], keep='last')
                    short_map = deduped.set_index('symbol').to_dict(orient='index')

        for sym in symbols:
            sym_str = str(sym)
            row = short_map.get(sym_str, short_map.get(sym_str.zfill(6), {}))

            # Short interest metrics
            short_ratio = row.get('short_ratio', row.get('short_pct', row.get('short_float_pct', row.get('short_interest_ratio', np.nan))))
            dtc = row.get('days_to_cover', row.get('dtc', np.nan))

            # Compute 5-day return from prices_dict if available
            ret_5d = 0.0
            if prices_dict and (sym_str in prices_dict or sym in prices_dict):
                p_df = prices_dict.get(sym_str, prices_dict.get(sym))
                if isinstance(p_df, pd.DataFrame) and len(p_df) >= 6:
                    close_col = 'close' if 'close' in p_df.columns else 'Close'
                    if close_col in p_df.columns:
                        c_series = p_df[close_col].dropna()
                        if len(c_series) >= 6:
                            ret_5d = (c_series.iloc[-1] / c_series.iloc[-6]) - 1.0

            # V8-HIGH-12 Fix: Return NaN when explicit short interest/DTC is unavailable
            # to allow ensemble missingness renormalization without corrupting cross-sectional ranks.
            if pd.isna(short_ratio) or pd.isna(dtc):
                results[sym_str] = np.nan
            else:
                # Formula: Short Interest Ratio * DTC * Momentum Condition
                # Add squeeze ignition multiplier when momentum turns positive with heavy DTC
                try:
                    f_sr = float(short_ratio)
                    f_dtc = float(dtc)
                    if not (np.isfinite(f_sr) and np.isfinite(f_dtc) and f_sr >= 0 and f_dtc >= 0):
                        results[sym_str] = np.nan
                    else:
                        # Multi-Tier Squeeze Ignition Accelerator:
                        # Explosive Squeeze Trigger: High DTC + High Short Float + Strong 5D Breakout
                        if ret_5d >= 0.08 and f_dtc >= 6.0 and f_sr >= 0.25:
                            ignite_mult = 1.80  # Super Squeeze Avalanche Ignition
                        elif ret_5d >= 0.05 and f_dtc >= 4.5 and f_sr >= 0.18:
                            ignite_mult = 1.55  # High-Conviction Squeeze Ignition
                        elif ret_5d > 0.02 and f_dtc >= 3.0:
                            ignite_mult = 1.30  # Standard Squeeze Ignition
                        else:
                            ignite_mult = 1.0

                        # Hard-to-Borrow (HTB) Squeeze Pressure
                        htb_squeeze_mult = 1.30 if (f_sr > 0.30 or f_dtc > 8.0) else (1.15 if (f_sr > 0.15 or f_dtc > 4.0) else 1.0)
                        mom_factor = (1.0 + float(ret_5d) * 4.5) if ret_5d >= 0 else max(0.10, 1.0 + float(ret_5d) * 2.0)
                        mom_factor = mom_factor if np.isfinite(mom_factor) else 1.0
                        raw_squeeze = float(f_sr * f_dtc * mom_factor * ignite_mult * htb_squeeze_mult)
                        results[sym_str] = raw_squeeze if np.isfinite(raw_squeeze) else np.nan
                except (ValueError, TypeError):
                    results[sym_str] = np.nan

        # Build output DataFrame and normalize
        df_out = pd.DataFrame(list(results.items()), columns=['symbol', 'raw_score'])
        df_out['raw_score'] = pd.to_numeric(df_out['raw_score'], errors='coerce')
        valid_mask = df_out['raw_score'].notna() & np.isfinite(df_out['raw_score'])

        if valid_mask.sum() > 1:
            ranks = df_out.loc[valid_mask, 'raw_score'].rank(pct=True, ascending=True).clip(0.02, 0.98)
            # Multi-Tier Short Squeeze Rank Booster (Top 5% receives 1.15x, Top 15% receives 1.10x)
            boosted_ranks = np.where(ranks >= 0.95, (ranks * 1.15).clip(0.05, 0.98),
                            np.where(ranks >= 0.85, (ranks * 1.10).clip(0.05, 0.98), ranks))
            df_out.loc[valid_mask, 'short_squeeze_score'] = pd.Series(boosted_ranks, index=df_out.loc[valid_mask].index).clip(0.05, 0.98)
        elif valid_mask.sum() == 1:
            df_out.loc[valid_mask, 'short_squeeze_score'] = 0.50
        else:
            if len(df_out) == 1:
                df_out['short_squeeze_score'] = 0.50
            else:
                df_out['short_squeeze_score'] = np.nan

        df_out['short_squeeze_score'] = df_out['short_squeeze_score'].astype(float)

        return df_out[['symbol', 'short_squeeze_score']]
