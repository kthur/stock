import logging
import pandas as pd
import numpy as np
from typing import Dict, Any

logger = logging.getLogger(__name__)

class ARMFactorEngine:
    """
    15. Analyst Revision Momentum (ARM) Strategy Engine

    증권사 컨센서스(EPS, 목표주가) 상향 조정 및 실적 서프라이즈 모멘텀 수치화.
    - EPS / Target Price 추정치 변경 모멘텀
    - PBR / PER 대비 펀더멘탈 추정 개선율
    """
    def __init__(self, lookback_days: int = 60):
        self.lookback_days = lookback_days

    def compute_scores(self, fundamentals_dict: Dict[str, Dict[str, Any]], prices_dict: Dict[str, pd.DataFrame]) -> Dict[str, float]:
        """
        Computes ARM factor scores in [0.0, 1.0] for all symbols.
        """
        scores = {}
        for sym, fund in fundamentals_dict.items():
            try:
                # Extract EPS estimate revision proxies or actual analyst consensus revisions
                eps_rev = fund.get('eps_revision_pct')
                tp_rev = fund.get('tp_revision_pct')

                if eps_rev is not None or tp_rev is not None:
                    # True Analyst Revision Momentum (ARM)
                    e_rev = float(eps_rev or 0.0)
                    t_rev = float(tp_rev or 0.0)
                    arm_raw = (e_rev * 0.5) + (t_rev * 0.5)
                else:
                    # Fallback Fundamental Growth Momentum
                    eps_growth = float(fund.get('eps_growth', 0.0) or 0.0)
                    rev_growth = float(fund.get('revenue_growth', 0.0) or 0.0)
                    per = float(fund.get('per', 15.0) or 15.0)
                    arm_raw = (eps_growth * 0.4) + (rev_growth * 0.3) - (per * 0.01)

                # Price momentum overlay
                price_mom = 0.0
                if sym in prices_dict and not prices_dict[sym].empty:
                    df = prices_dict[sym]
                    close = df['Close'].iloc[:, 0] if isinstance(df['Close'], pd.DataFrame) else df['Close']
                    if len(close) >= 20:
                        price_mom = float((close.iloc[-1] - close.iloc[-20]) / close.iloc[-20] * 100)

                arm_raw += (price_mom * 0.2)
                scores[sym] = arm_raw
            except Exception:
                scores[sym] = 0.0

        if not scores:
            return {}

        # MinMax Normalization to [0.0, 1.0]
        vals = np.array(list(scores.values()))
        min_v, max_v = np.min(vals), np.max(vals)
        if max_v == min_v:
            return {k: 0.5 for k in scores.keys()}
        range_v = max_v - min_v

        return {k: float(np.clip((v - min_v) / range_v, 0.0, 1.0)) for k, v in scores.items()}
