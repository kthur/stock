import logging
import pandas as pd
import numpy as np
from typing import Dict, Any
from .base_strategy import BaseStrategyEngine

logger = logging.getLogger(__name__)

def _safe_float(val: Any, default: float = 0.0) -> float:
    if val is None:
        return default
    try:
        f = float(val)
        return default if np.isnan(f) or np.isinf(f) else f
    except (ValueError, TypeError):
        return default

class ARMFactorEngine(BaseStrategyEngine):
    """
    15. Analyst Revision Momentum (ARM) Strategy Engine

    증권사 컨센서스(EPS, 목표주가) 상향 조정 및 실적 서프라이즈 모멘텀 수치화.
    - EPS / Target Price 추정치 변경 모멘텀
    - PBR / PER 대비 펀더멘탈 추정 개선율
    """
    def __init__(self, lookback_days: int = 60):
        self.lookback_days = lookback_days

    def compute_scores(self, prices_dict: Any, fundamentals_dict: Any = None, indicators_df: Any = None, **kwargs) -> Dict[str, float]:
        if isinstance(prices_dict, dict) and any(isinstance(v, dict) for v in prices_dict.values()):
            return self._compute_scores_internal(prices_dict, fundamentals_dict or {})
        fund = fundamentals_dict if isinstance(fundamentals_dict, dict) else {}
        prc = prices_dict if isinstance(prices_dict, dict) else {}
        return self._compute_scores_internal(fund, prc)

    def _compute_scores_internal(self, fundamentals_dict: Dict[str, Dict[str, Any]], prices_dict: Dict[str, pd.DataFrame]) -> Dict[str, float]:
        """
        Computes ARM factor scores in [0.0, 1.0] for all symbols.
        """
        scores = {}
        for sym, fund in fundamentals_dict.items():
            if not isinstance(fund, dict):
                continue
            try:
                # Extract EPS estimate revision proxies or actual analyst consensus revisions
                eps_rev = fund.get('eps_revision_pct')
                tp_rev = fund.get('tp_revision_pct')

                if eps_rev is not None or tp_rev is not None:
                    # True Analyst Revision Momentum (ARM)
                    e_rev = _safe_float(eps_rev, 0.0)
                    t_rev = _safe_float(tp_rev, 0.0)
                    arm_raw = (e_rev * 0.5) + (t_rev * 0.5)
                else:
                    # Fallback Fundamental Growth Momentum
                    eps_growth = _safe_float(fund.get('eps_growth'), 0.0)
                    rev_growth = _safe_float(fund.get('revenue_growth'), 0.0)
                    per = _safe_float(fund.get('per'), 15.0)
                    per_penalty = max(0.0, per) * 0.01
                    arm_raw = (eps_growth * 0.4) + (rev_growth * 0.3) - per_penalty

                # Price momentum overlay
                price_mom = 0.0
                if sym in prices_dict and not prices_dict[sym].empty:
                    df = prices_dict[sym]
                    close = df['Close'].iloc[:, 0] if isinstance(df['Close'], pd.DataFrame) else df['Close']
                    if len(close) >= 20:
                        price_mom = float((close.iloc[-1] - close.iloc[-20]) / close.iloc[-20] * 100)

                arm_raw += (price_mom * 0.2)
                scores[sym] = arm_raw
            except Exception as e:
                logger.debug(f"[ARM FACTOR] Error computing score for {sym}: {e}")
                scores[sym] = 0.0

        if not scores:
            return {}

        # Winsorized MinMax Normalization to [0.0, 1.0] (1st and 99th percentiles)
        vals = np.array(list(scores.values()))
        lower = np.percentile(vals, 1)
        upper = np.percentile(vals, 99)
        if upper == lower:
            return {k: 0.5 for k in scores.keys()}

        return {k: float(np.clip((v - lower) / (upper - lower), 0.0, 1.0)) for k, v in scores.items()}

