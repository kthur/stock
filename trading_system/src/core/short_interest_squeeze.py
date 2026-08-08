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

logger = logging.getLogger(__name__)


class ShortInterestSqueezeEngine:
    """
    Computes Short Interest & Squeeze Score [0.0, 1.0] for stocks.
    High Score = High short interest + High days-to-cover + Positive short-term momentum (Short Squeeze catalyst).
    Low Score = Low short interest or heavy downward price momentum driven by informed short sellers.
    """

    def __init__(self, config: Optional[Any] = None) -> None:
        self.config = config

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
                    for sym, group in features_df.groupby('symbol'):
                        short_map[str(sym)] = group.iloc[-1].to_dict()

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

            # Fallback estimation if explicit short data is unavailable:
            # High volume surge + oversold bounce as proxy short squeeze signal
            if pd.isna(short_ratio) or pd.isna(dtc):
                if prices_dict and (sym_str in prices_dict or sym in prices_dict):
                    p_df = prices_dict.get(sym_str, prices_dict.get(sym))
                    if isinstance(p_df, pd.DataFrame) and len(p_df) >= 20:
                        vol_col = 'volume' if 'volume' in p_df.columns else 'Volume'
                        close_col = 'close' if 'close' in p_df.columns else 'Close'
                        if vol_col in p_df.columns and close_col in p_df.columns:
                            v_series = p_df[vol_col].dropna()
                            c_series = p_df[close_col].dropna()
                            if len(v_series) >= 20 and len(c_series) >= 20:
                                vol_surge = v_series.iloc[-1] / (v_series.iloc[-20:-1].mean() + 1e-5)
                                ret_20d = (c_series.iloc[-1] / c_series.iloc[-20]) - 1.0
                                # High volume surge + positive recent bounce = squeeze proxy
                                proxy_score = float(vol_surge * np.clip(1.0 + ret_5d * 3.0, 0.2, 3.0))
                                results[sym_str] = proxy_score
                                continue
                results[sym_str] = np.nan
            else:
                # Formula: Short Interest Ratio * DTC * (1 + max(0, ret_5d * 2))
                raw_squeeze = float(short_ratio) * float(dtc) * (1.0 + max(0.0, float(ret_5d) * 2.0))
                results[sym_str] = raw_squeeze

        # Build output DataFrame and normalize
        df_out = pd.DataFrame(list(results.items()), columns=['symbol', 'raw_score'])
        valid_mask = df_out['raw_score'].notna() & np.isfinite(df_out['raw_score'])
        
        if valid_mask.sum() > 0:
            ranks = df_out.loc[valid_mask, 'raw_score'].rank(pct=True, ascending=True)
            df_out.loc[valid_mask, 'short_squeeze_score'] = ranks.clip(0.05, 0.95)
        else:
            df_out['short_squeeze_score'] = 0.50

        df_out['short_squeeze_score'] = df_out['short_squeeze_score'].fillna(0.50).astype(float)
        
        return df_out[['symbol', 'short_squeeze_score']]
