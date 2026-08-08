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
                    c = df['Close'].dropna()
                    v = df['Volume'].dropna()

                    if len(c) >= 10 and len(v) >= 10:
                        ret_10d = float((c.iloc[-1] / c.iloc[-10]) - 1.0)
                        avg_vol = float(v.iloc[-10:-1].mean())
                        cur_vol = float(v.iloc[-1])
                        vol_spike = (cur_vol / avg_vol) if avg_vol > 0 else 1.0

                        # Accumulation Divergence: Flat price (-2% ~ +2%) + Massive Volume Spike (> 2.5x)
                        if abs(ret_10d) < 0.02 and vol_spike > 2.5:
                            score = float(np.clip(0.50 + 0.15 * vol_spike, 0.50, 0.95))
                            logger.info(f"[DARK POOL ENGINE] Accumulation divergence for {sym} (Vol Spike={vol_spike:.1f}x, Ret={ret_10d*100:.1f}%)")

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
