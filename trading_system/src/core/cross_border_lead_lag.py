"""
Cross-Border Lead-Lag Strategy Engine
S&P 500 빅테크 (NVDA, TSLA, MSFT, AAPL, AMZN 등)의 미국 장 마감 수익률이 KOSPI/KOSDAQ 벨류체인 후행 종목(SK하이닉스, 한미반도체, LG에너지솔루션 등)으로 파급되는 시차 상관성(Cross-Market Lag Shift) 알파 포착.
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class CrossBorderLeadLagEngine:
    """
    Cross-Border (US -> KR) Lead-Lag Matrix Engine.
    Maps US market leaders to KR target stocks and computes lag-shifted momentum scores.
    """

    US_LEADERS = ['NVDA', 'TSLA', 'AAPL', 'MSFT', 'AMZN', 'GOOGL', 'META']

    # Cross-border Value Chain Sector Mappings
    SECTOR_LEADER_MAP = {
        'Information Technology': ['NVDA', 'MSFT', 'AAPL'],
        'Consumer Discretionary': ['TSLA', 'AMZN'],
        'Communication Services': ['GOOGL', 'META'],
        'General': ['NVDA', 'AAPL']
    }

    def __init__(self):
        pass

    def compute_cross_border_scores(
        self,
        prices_dict: Dict[str, pd.DataFrame],
        sector_map: Optional[Dict[str, str]] = None
    ) -> Dict[str, float]:
        """
        Calculates cross-border lead-lag alpha score [0.0, 1.0] for all target symbols.
        """
        if not prices_dict:
            return {}

        sector_map = sector_map or {}

        # 1. Compute recent 1-day & 5-day returns for US Leaders present in prices_dict
        us_returns: Dict[str, float] = {}
        for us_sym in self.US_LEADERS:
            if us_sym in prices_dict:
                df = prices_dict[us_sym]
                if df is not None and len(df) >= 2:
                    col = 'Close' if 'Close' in df.columns else ('close' if 'close' in df.columns else None)
                    if not col:
                        continue
                    close = df[col].iloc[:, 0] if isinstance(df[col], pd.DataFrame) else df[col]
                    us_ret = (close.iloc[-1] - close.iloc[-2]) / max(close.iloc[-2], 1e-4)
                    us_returns[us_sym] = float(us_ret)

        # Default fallback US tech return if US ticker prices aren't loaded explicitly
        if not us_returns:
            return {sym: 0.5 for sym in prices_dict.keys() if sym not in self.US_LEADERS}

        avg_us_tech_ret = float(np.mean(list(us_returns.values())))

        scores: Dict[str, float] = {}

        for sym, df in prices_dict.items():
            if sym in self.US_LEADERS:
                continue

            try:
                if df is None or len(df) < 5:
                    scores[sym] = 0.5
                    continue

                col = 'Close' if 'Close' in df.columns else ('close' if 'close' in df.columns else None)
                if not col:
                    scores[sym] = 0.5
                    continue
                close = df[col].iloc[:, 0] if isinstance(df[col], pd.DataFrame) else df[col]
                kr_5d_ret = float((close.iloc[-1] - close.iloc[-5]) / max(close.iloc[-5], 1e-4))

                sec = sector_map.get(sym, 'General')
                leaders = self.SECTOR_LEADER_MAP.get(sec, self.SECTOR_LEADER_MAP['General'])

                # Measure US leader shock vs KR stock recent momentum
                avail_leaders = [l_sym for l_sym in leaders if l_sym in us_returns]
                if not avail_leaders:
                    scores[sym] = 0.5
                    continue

                leader_rets = [us_returns[l_sym] for l_sym in avail_leaders]
                mean_leader_ret = float(np.mean(leader_rets))

                # Lag divergence: US leader rose but KR stock hasn't caught up yet -> Buying Opportunity
                lag_divergence = mean_leader_ret - (kr_5d_ret * 0.2)
                score = 1.0 / (1.0 + np.exp(-lag_divergence * 15.0))
                scores[sym] = float(np.clip(score, 0.0, 1.0))
            except Exception as e:
                logger.debug(f"Cross-border scoring error for {sym}: {e}")
                scores[sym] = 0.5

        return scores
