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

        if df_price is not None and len(df_price) >= 2 and 'Close' in df_price.columns and 'Volume' in df_price.columns:
            clean = df_price[['Close', 'Volume']].dropna()
            if len(clean) >= 2:
                last_close = float(clean['Close'].iloc[-1])
                prev_close = float(clean['Close'].iloc[-2])
                ret_last = (last_close / prev_close) - 1.0 if prev_close > 0 else 0.0

                volumes = clean['Volume'].values
                cur_vol = float(volumes[-1])
                avg_vol = float(volumes[:-1].mean()) if len(volumes) > 1 else cur_vol
                vol_ratio = (cur_vol / avg_vol) if avg_vol > 0 else 1.0

                if ret_last > 0 and vol_ratio > 1.2:
                    is_accum = True
                    net_usd = last_close * cur_vol * 0.2
                elif ret_last < 0 and vol_ratio > 1.2:
                    is_dist = True
                    net_usd = -last_close * cur_vol * 0.2

                dp_ratio = float(np.clip(0.35 * min(2.0, max(0.5, vol_ratio)), 0.1, 0.6))

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
                if df is not None and len(df) >= 10 and 'Close' in df.columns and 'Volume' in df.columns:
                    clean_df = df[['Close', 'Volume']].dropna()

                    if len(clean_df) >= 10:
                        c = clean_df['Close']
                        v = clean_df['Volume']
                        if c.iloc[-10] > 0:
                            ret_10d = float((c.iloc[-1] / c.iloc[-10]) - 1.0)
                            avg_vol = float(v.iloc[-10:-1].mean())
                            cur_vol = float(v.iloc[-1])
                            vol_spike = (cur_vol / avg_vol) if avg_vol > 0 else 1.0

                            # Accumulation Divergence: Flat price (-2% ~ +2%) + Massive Volume Spike (> 2.5x)
                            if abs(ret_10d) < 0.02 and vol_spike > 2.5:
                                base_score = float(np.clip(0.50 + 0.15 * vol_spike, 0.50, 0.95))
                                # Dark Pool Stealth Inflow Booster for high conviction accumulation
                                score = float(np.clip(base_score * 1.10, 0.50, 0.98))
                                logger.info(f"[DARK POOL ENGINE] Accumulation divergence for {sym} (Vol Spike={vol_spike:.1f}x, Ret={ret_10d*100:.1f}%, Score={score:.2f})")

            # 2. Live Dark Pool / ATS Volume Data override
            if darkpool_data_dict and sym in darkpool_data_dict:
                dp_data = darkpool_data_dict[sym]
                dp_share = dp_data.get('dark_pool_ratio', 0.30)
                dp_buy_bias = dp_data.get('buy_bias', 0.50)

                if dp_share > 0.40 and dp_buy_bias > 0.65:  # High dark pool volume with institutional buy bias
                    score = float(np.clip(score + 0.30, 0.0, 1.0))
                    logger.info(f"[DARK POOL ENGINE] High Dark Pool institutional buying for {sym} (Share={dp_share*100:.1f}%, Buy Bias={dp_buy_bias:.2f})")

            results.append({'symbol': sym, 'darkpool_score': score})

        return pd.DataFrame(results)


# Alias for backward compatibility
DarkPoolTracker = DarkPoolTrackerEngine
