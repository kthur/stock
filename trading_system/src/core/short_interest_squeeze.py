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
        features_df: Optional[Any] = None,
        **kwargs: Any
    ) -> pd.DataFrame:
        """
        Computes Short Interest & Squeeze Score per symbol.
        Returns DataFrame with ['symbol', 'short_squeeze_score'].
        """
        if not symbols:
            return pd.DataFrame(columns=['symbol', 'short_squeeze_score'])

        if features_df is None and 'fundamentals_dict' in kwargs:
            features_df = kwargs['fundamentals_dict']

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

            # Fast NumPy extraction of close & volume arrays from prices_dict
            p_df = None
            if prices_dict:
                p_df = prices_dict.get(sym_str)
                if p_df is None and sym is not sym_str:
                    p_df = prices_dict.get(sym)
                if p_df is None:
                    sym_clean = sym_str.split('.')[0]
                    p_df = prices_dict.get(sym_clean, prices_dict.get(sym_clean.zfill(6)))

            c_arr = None
            v_arr = None
            ret_5d = 0.0
            if isinstance(p_df, pd.DataFrame) and len(p_df) >= 5:
                cols = p_df.columns
                close_col = 'close' if 'close' in cols else ('Close' if 'Close' in cols else None)
                if close_col is not None:
                    raw_c = p_df[close_col].to_numpy(dtype=float, copy=False)
                    valid_c = raw_c[np.isfinite(raw_c)]
                    if len(valid_c) >= 5:
                        c_arr = valid_c
                        if len(c_arr) >= 6:
                            ret_5d = float((c_arr[-1] / max(1e-5, c_arr[-6])) - 1.0)
                        else:
                            ret_5d = float((c_arr[-1] / max(1e-5, c_arr[0])) - 1.0)
                        vol_col = 'volume' if 'volume' in cols else ('Volume' if 'Volume' in cols else None)
                        if vol_col is not None:
                            raw_v = p_df[vol_col].to_numpy(dtype=float, copy=False)
                            valid_v = raw_v[np.isfinite(raw_v)]
                            if len(valid_v) > 0:
                                v_arr = valid_v

            # Adaptive Microstructure Squeeze Proxy Fallback when explicit short interest/DTC is unavailable
            if pd.isna(short_ratio) or pd.isna(dtc):
                if c_arr is not None and len(c_arr) >= 5:
                    # 1. 5D Momentum
                    r_5d = ret_5d

                    # 2. Volatility Contraction (5D std / 20D std) via fast NumPy slicing
                    c_tail = c_arr[-21:]
                    rets = np.diff(c_tail) / np.maximum(1e-5, c_tail[:-1])
                    vol_5 = float(np.std(rets[-5:], ddof=1)) if len(rets) >= 5 else 0.02
                    vol_20 = float(np.std(rets[-20:], ddof=1)) if len(rets) >= 20 else (vol_5 if vol_5 > 0 else 0.02)
                    vol_ratio = vol_5 / max(1e-4, vol_20)
                    vol_contraction_factor = float(np.clip(1.30 - 0.40 * vol_ratio, 0.70, 1.40))

                    # 3. Volume Exhaustion / RVOL Breakout
                    if v_arr is not None and len(v_arr) > 0:
                        v_tail20 = v_arr[-20:]
                        avg_v = float(np.mean(v_tail20))
                        last_v = float(v_arr[-1])
                        rvol = (last_v / max(1.0, avg_v)) if avg_v > 0 else 1.0
                    else:
                        rvol = 1.0

                    # Down-volume vs Up-volume exhaustion ratio over past 10 bars
                    if len(c_arr) >= 11 and v_arr is not None and len(v_arr) >= 10:
                        ret_10 = np.diff(c_arr[-11:])
                        v_10 = v_arr[-10:]
                        up_vol = float(np.sum(v_10[ret_10 >= 0]))
                        dn_vol = float(np.sum(v_10[ret_10 < 0]))
                        tot_vol = up_vol + dn_vol
                        exhaustion_boost = (up_vol / max(1.0, tot_vol)) if tot_vol > 0 else 0.50
                    else:
                        exhaustion_boost = 0.50

                    # Combined synthetic squeeze score [0.10, 0.95]
                    mom_signal = float(np.tanh(r_5d * 5.0))
                    rvol_capped = float(np.clip(rvol, 0.5, 3.0))
                    synth_score = 0.50 + 0.20 * mom_signal + 0.10 * (rvol_capped - 1.0) / 2.0 + 0.10 * (vol_contraction_factor - 1.0) + 0.10 * (exhaustion_boost - 0.50)
                    results[sym_str] = float(np.clip(synth_score, 0.10, 0.95))
                else:
                    results[sym_str] = 0.50
            else:
                # Formula: Short Interest Ratio * DTC * Momentum Condition
                try:
                    f_sr = float(short_ratio)
                    f_dtc = float(dtc)
                    if not (np.isfinite(f_sr) and np.isfinite(f_dtc) and f_sr >= 0 and f_dtc >= 0):
                        results[sym_str] = 0.50
                    else:
                        if ret_5d >= 0.08 and f_dtc >= 6.0 and f_sr >= 0.25:
                            ignite_mult = 1.80  # Super Squeeze Avalanche Ignition
                        elif ret_5d >= 0.05 and f_dtc >= 4.5 and f_sr >= 0.18:
                            ignite_mult = 1.55  # High-Conviction Squeeze Ignition
                        elif ret_5d > 0.02 and f_dtc >= 3.0:
                            ignite_mult = 1.30  # Standard Squeeze Ignition
                        else:
                            ignite_mult = 1.0

                        htb_squeeze_mult = 1.30 if (f_sr > 0.30 or f_dtc > 8.0) else (1.15 if (f_sr > 0.15 or f_dtc > 4.0) else 1.0)
                        mom_factor = (1.0 + float(ret_5d) * 4.5) if ret_5d >= 0 else max(0.10, 1.0 + float(ret_5d) * 2.0)
                        mom_factor = mom_factor if np.isfinite(mom_factor) else 1.0
                        raw_squeeze = float(f_sr * f_dtc * mom_factor * ignite_mult * htb_squeeze_mult)
                        results[sym_str] = raw_squeeze if np.isfinite(raw_squeeze) else 0.50
                except (ValueError, TypeError):
                    results[sym_str] = 0.50

        # Build output DataFrame and normalize
        df_out = pd.DataFrame(list(results.items()), columns=['symbol', 'raw_score'])
        df_out['raw_score'] = pd.to_numeric(df_out['raw_score'], errors='coerce').fillna(0.50)
        valid_mask = df_out['raw_score'].notna() & np.isfinite(df_out['raw_score'])
        df_out['short_squeeze_score'] = np.nan

        if valid_mask.sum() > 1:
            valid_scores = df_out.loc[valid_mask, 'raw_score']
            # When all cross-sectional raw scores are constant/tied (e.g. missing price data or flat series), preserve neutral 0.50
            if float(valid_scores.max() - valid_scores.min()) < 1e-9:
                df_out.loc[valid_mask, 'short_squeeze_score'] = 0.50
            else:
                ranks = valid_scores.rank(pct=True, ascending=True).clip(0.02, 0.98)
                # Multi-Tier Short Squeeze Rank Booster (Top 5% receives 1.15x, Top 15% receives 1.10x)
                boosted_ranks = np.where(ranks >= 0.95, (ranks * 1.15).clip(0.05, 0.98),
                                np.where(ranks >= 0.85, (ranks * 1.10).clip(0.05, 0.98), ranks))
                df_out.loc[valid_mask, 'short_squeeze_score'] = pd.Series(boosted_ranks, index=df_out.loc[valid_mask].index).clip(0.05, 0.98)
        elif valid_mask.sum() == 1:
            df_out.loc[valid_mask, 'short_squeeze_score'] = 0.50
        else:
            df_out['short_squeeze_score'] = 0.50

        # Ensure all rows have valid non-NaN scores
        df_out['short_squeeze_score'] = df_out['short_squeeze_score'].fillna(0.50).clip(0.05, 0.98).astype(float)

        return df_out[['symbol', 'short_squeeze_score']]
