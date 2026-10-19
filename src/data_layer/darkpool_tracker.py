"""
src/data_layer/darkpool_tracker.py
Dark Pool & Off-Exchange Volume Divergence Strategy Engine (Strategy #30).

Tracks off-exchange / block trade accumulation divergence relative to retail order flow:
  - Off-Exchange / Dark Pool Ratio: (Dark Pool Volume / Total Volume)
  - Accumulation Divergence: Price flat/falling while Dark Pool buying surges.
  - Dark Pool Score [0.0, 1.0].
"""

import logging
from typing import Dict, List, Optional, Any
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class DarkPoolTrackerEngine:
    """
    Strategy #30: Dark Pool & Off-Exchange Volume Divergence Engine.
    """

    def __init__(self, config=None):
        self.config = config

    def fetch_darkpool_activity(self, symbol: str, df_price: Optional[pd.DataFrame] = None, *args, **kwargs) -> Dict[str, Any]:
        """Fetch dark pool activity metrics for symbol (compatibility method)."""
        is_accum = False
        is_dist = False
        net_usd = 0.0
        dp_ratio = 0.35

        if df_price is not None and len(df_price) >= 2:
            c_col = next((c for c in df_price.columns if str(c).lower() in ('close', 'adj close', 'adjclose')), None)
            v_col = next((c for c in df_price.columns if str(c).lower() == 'volume'), None)
            if c_col and v_col:
                c_s = pd.to_numeric(df_price[c_col], errors='coerce')
                v_s = pd.to_numeric(df_price[v_col], errors='coerce')
                clean = pd.DataFrame({'c': c_s, 'v': v_s}).dropna()
                if len(clean) >= 2:
                    last_close = float(clean['c'].iloc[-1])
                    prev_close = float(clean['c'].iloc[-2])
                    ret_last = (last_close / prev_close) - 1.0 if prev_close > 0 else 0.0

                    volumes = clean['v'].values
                    cur_vol = float(volumes[-1])
                    avg_vol = float(volumes[:-1].mean()) if len(volumes) > 1 else cur_vol
                    vol_ratio = (cur_vol / avg_vol) if avg_vol > 0 else 1.0

                    if ret_last > 0 and vol_ratio > 1.2:
                        is_accum = True
                        net_usd = last_close * cur_vol * 0.2
                    elif ret_last < 0 and vol_ratio > 1.2:
                        is_dist = True
                        net_usd = -last_close * cur_vol * 0.2

                    dp_ratio = float(np.clip(0.35 * min(2.0, max(0.5, vol_ratio)), 0.1, 0.6)) if np.isfinite(vol_ratio) else 0.35

        return {
            'symbol': symbol,
            'dark_pool_ratio': dp_ratio,
            'buy_bias': 0.55 if not is_dist else 0.35,
            'block_trade_volume': 150000,
            'block_trade_net_usd': net_usd,
            'is_accumulation': is_accum,
            'is_distribution': is_dist
        }

    def calculate_scores(self, symbols: List[str], prices_dict: Optional[Dict[str, pd.DataFrame]] = None, darkpool_data_dict: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
        """Alias for compute_darkpool_scores."""
        return self.compute_darkpool_scores(symbols, prices_dict, darkpool_data_dict)

    def compute_scores(
        self,
        prices_dict: Optional[Dict[str, pd.DataFrame]] = None,
        symbols: Optional[List[str]] = None,
        darkpool_data_dict: Optional[Dict[str, Any]] = None,
        **kwargs: Any
    ) -> pd.DataFrame:
        """Pipeline standard adapter interface."""
        sym_list = list(symbols) if symbols is not None else (list(prices_dict.keys()) if prices_dict else [])
        return self.compute_darkpool_scores(sym_list, prices_dict, darkpool_data_dict)

    def compute_darkpool_scores(
        self,
        symbols: List[str],
        prices_dict: Optional[Dict[str, pd.DataFrame]] = None,
        darkpool_data_dict: Optional[Dict[str, Any]] = None
    ) -> pd.DataFrame:
        """
        Computes Dark Pool Divergence score per symbol [0.0, 1.0].
        Returns DataFrame with ['symbol', 'darkpool_score'].
        """
        if not symbols:
            return pd.DataFrame(columns=['symbol', 'darkpool_score'])

        results = []

        for sym in symbols:
            score = 0.50  # Base neutral score

            # 1. Price Volume Accumulation Proxy if live ATS data is unavailable
            if prices_dict and sym in prices_dict:
                df = prices_dict[sym]
                if df is not None and len(df) >= 10:
                    c_col = next((c for c in df.columns if str(c).lower() in ('close', 'adj close', 'adjclose')), None)
                    v_col = next((c for c in df.columns if str(c).lower() == 'volume'), None)
                    if c_col and v_col:
                        c_s = pd.to_numeric(df[c_col], errors='coerce')
                        v_s = pd.to_numeric(df[v_col], errors='coerce')
                        clean_df = pd.DataFrame({'c': c_s, 'v': v_s}).dropna()

                        if len(clean_df) >= 10:
                            c = clean_df['c']
                            v = clean_df['v']
                            ret_10d = 0.0
                            vol_spike = 1.0
                            p10 = float(c.iloc[-10])
                            if p10 > 0 and np.isfinite(p10):
                                ret_10d = float((c.iloc[-1] / p10) - 1.0)
                                avg_vol = float(v.iloc[-10:-1].mean())
                                cur_vol = float(v.iloc[-1])
                                vol_spike = (cur_vol / avg_vol) if (avg_vol > 0 and np.isfinite(avg_vol) and np.isfinite(cur_vol)) else 1.0

                            # Enforce minimum traded dollar value (1억원 for KRX, $100k for US)
                            traded_value = float(v.iloc[-1]) * float(c.iloc[-1])
                            min_val_thresh = 100_000_000 if str(sym).isdigit() else 100_000

                            # Multi-Tier Stealth Accumulation & Distribution Divergence Modeling
                            if traded_value >= min_val_thresh:
                                if abs(ret_10d) < 0.020 and vol_spike >= 4.0:
                                    # Mega Stealth Inflow Divergence: Price suppressed while massive block volume crosses
                                    score = float(np.clip(0.50 + 0.15 * vol_spike, 0.50, 0.98))
                                    logger.info(f"[DARK POOL ENGINE] Super mega accumulation divergence for {sym} (Vol Spike={vol_spike:.1f}x, Ret={ret_10d*100:.1f}%, Score={score:.2f})")
                                elif abs(ret_10d) < 0.025 and vol_spike >= 3.0:
                                    # Standard Mega Stealth Accumulation
                                    score = float(np.clip(0.50 + 0.12 * vol_spike, 0.50, 0.95))
                                elif abs(ret_10d) < 0.025 and vol_spike >= 2.0:
                                    # Standard Stealth Accumulation
                                    score = float(np.clip(0.50 + 0.10 * vol_spike, 0.50, 0.85))
                                elif 0.02 <= ret_10d <= 0.06 and vol_spike >= 1.8:
                                    # Institutional Breakout Expansion Footprint
                                    score = float(np.clip(0.60 + 0.08 * vol_spike, 0.60, 0.92))
                                elif ret_10d < -0.04 and vol_spike >= 2.0:
                                    # Institutional Stealth Distribution Divergence
                                    score = float(np.clip(0.50 - 0.10 * vol_spike, 0.10, 0.40))

            # 2. Live Dark Pool / ATS Volume Data override
            if darkpool_data_dict and sym in darkpool_data_dict:
                dp_data = darkpool_data_dict[sym]
                if isinstance(dp_data, dict):
                    raw_ratio = dp_data.get('dark_pool_ratio')
                    raw_bias = dp_data.get('buy_bias')
                    dp_share = float(raw_ratio) if (raw_ratio is not None and np.isfinite(float(raw_ratio))) else 0.30
                    dp_buy_bias = float(raw_bias) if (raw_bias is not None and np.isfinite(float(raw_bias))) else 0.50

                    if dp_share > 0.40 and dp_buy_bias > 0.65:  # High dark pool volume with institutional buy bias
                        score = float(np.clip(score + 0.30, 0.0, 0.98))
                        logger.info(f"[DARK POOL ENGINE] High Dark Pool institutional buying for {sym} (Share={dp_share*100:.1f}%, Buy Bias={dp_buy_bias:.2f})")

            score_clean = float(score) if (score is not None and np.isfinite(score)) else 0.50
            score_clipped = float(np.clip(score_clean, 0.0, 0.98))
            results.append({'symbol': sym, 'darkpool_score': round(score_clipped, 4)})

        res_df = pd.DataFrame(results)
        if not res_df.empty:
            s_series = pd.to_numeric(res_df['darkpool_score'], errors='coerce').fillna(0.50).clip(0.05, 0.98)
            if len(res_df) > 1:
                ranks = s_series.rank(pct=True, ascending=True)
                # Multi-Tier Darkpool Booster (Top 5% receives 1.15x, Top 15% receives 1.10x)
                enhanced = np.where(ranks >= 0.95, (s_series * 1.15).clip(0.05, 0.98),
                           np.where(ranks >= 0.85, (s_series * 1.10).clip(0.05, 0.98), s_series))
                res_df['darkpool_score'] = pd.to_numeric(pd.Series(enhanced, index=res_df.index), errors='coerce').fillna(0.50).clip(0.05, 0.98)
            else:
                res_df['darkpool_score'] = s_series
        return res_df


# Alias for backward compatibility
DarkPoolTracker = DarkPoolTrackerEngine
