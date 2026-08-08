"""
src/core/lead_lag_3tier.py
3-Tier Cross-Asset Lead-Lag Momentum Transfer Engine.

Architecture:
- Tier 1: Global Tech Leaders (NVDA, TSMC, ASML, AAPL) 1D/3D momentum.
- Tier 2: KRX Sector Heavyweights (000660 SK Hynix, 005930 Samsung Electronics, 373220 LG Energy Solution).
- Tier 3: KOSDAQ Supply Chain Components & Equipment (HBM, CXL, Substrate, Materials).
"""

import logging
from typing import Dict, List
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class ThreeTierLeadLagEngine:
    """
    3-Tier Cross-Asset Lead-Lag Engine calculating lagged momentum transfer scores [0.0, 1.0].
    """

    TIER1_LEADERS = ['NVDA', 'TSM', 'ASML', 'AAPL', 'AMD']
    TIER2_LEADERS = ['000660', '005930', '373220', '005935']
    TICKER_ALIASES = {'TSMC': 'TSM', 'TSM': 'TSMC'}

    def __init__(self, config=None):
        self.config = config

    def compute_3tier_lead_lag_scores(
        self,
        prices_dict: Dict[str, pd.DataFrame],
        tier3_symbols: List[str]
    ) -> pd.DataFrame:
        """
        Computes 3-Tier Lead-Lag momentum transfer score for Tier 3 follower symbols.
        Returns DataFrame with ['symbol', 'tier3_lead_lag_score'].
        """
        if not tier3_symbols or not prices_dict:
            return pd.DataFrame(columns=['symbol', 'tier3_lead_lag_score'])

        # 1. Compute Tier 1 Global Tech Momentum (1D & 3D Returns)
        t1_returns = []
        for sym in self.TIER1_LEADERS:
            df = prices_dict.get(sym)
            if df is None:
                alias = self.TICKER_ALIASES.get(sym)
                if alias:
                    df = prices_dict.get(alias)
            if df is not None and len(df) >= 4 and 'Close' in df.columns:
                c = df['Close'].dropna()
                if len(c) >= 4 and c.iloc[-2] > 0 and c.iloc[-4] > 0:
                    ret_1d = float((c.iloc[-1] / c.iloc[-2]) - 1.0)
                    ret_3d = float((c.iloc[-1] / c.iloc[-4]) - 1.0)
                    t1_returns.append(0.6 * ret_1d + 0.4 * ret_3d)

        t1_score = float(np.mean(t1_returns)) if t1_returns else 0.0

        # 2. Compute Tier 2 KRX Heavyweight Momentum (1D Returns)
        t2_returns = []
        for sym in self.TIER2_LEADERS:
            df = prices_dict.get(sym)
            if df is None:
                df = prices_dict.get(f"{sym}.KS")
            if df is not None and len(df) >= 2 and 'Close' in df.columns:
                c = df['Close'].dropna()
                if len(c) >= 2 and c.iloc[-2] > 0:
                    ret_1d = float((c.iloc[-1] / c.iloc[-2]) - 1.0)
                    t2_returns.append(ret_1d)

        t2_score = float(np.mean(t2_returns)) if t2_returns else 0.0

        # 3. Composite Leader Momentum (dynamically weighted if missing data)
        if t1_returns and t2_returns:
            composite_leader_mom = 0.5 * t1_score + 0.5 * t2_score
        elif t1_returns:
            composite_leader_mom = t1_score
        elif t2_returns:
            composite_leader_mom = t2_score
        else:
            composite_leader_mom = 0.0

        # Map to 3-Tier Lead-Lag scores for Tier 3 follower symbols
        results = []
        for sym in tier3_symbols:
            df = prices_dict.get(sym)
            follower_mom = 0.0
            if df is not None and len(df) >= 2 and 'Close' in df.columns:
                c = df['Close'].dropna()
                if len(c) >= 2 and c.iloc[-2] > 0:
                    follower_mom = float((c.iloc[-1] / c.iloc[-2]) - 1.0)

            # Lag transfer bonus: High leader momentum vs delayed follower momentum
            # Restricted strictly to positive leader momentum (> 0)
            if composite_leader_mom > 0:
                lag_gap = max(0.0, composite_leader_mom - follower_mom)
            else:
                lag_gap = 0.0

            base_score = 0.5 + 5.0 * composite_leader_mom + 3.0 * lag_gap
            final_score = float(np.clip(base_score, 0.0, 1.0))
            results.append({'symbol': sym, 'tier3_lead_lag_score': final_score})

        return pd.DataFrame(results)
