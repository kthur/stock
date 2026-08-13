import logging
import pandas as pd
import numpy as np
from typing import Dict, Optional, Any
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

from src.core.strategy_registry import register_strategy, StrategyMeta


@register_strategy(
    StrategyMeta(
        strategy_id="arm_factor",
        display_name="Analyst Revision Momentum",
        score_column="arm_score",
        category="factor",
        output_file="arm_predictions.txt",
        requires_fundamentals=True,
        default_regime_weights={
            "BEAR": 0.05, "BEAR_HIGH_VOL": 0.05, "SIDEWAYS_LOW_VOL": 0.05, "BULL_HIGH_VOL": 0.06, "BULL_LOW_VOL": 0.05
        },
    )
)
class ARMFactorEngine(BaseStrategyEngine):
    """
    15. Analyst Revision Momentum (ARM) Strategy Engine

    증권사 컨센서스(EPS, 목표주가) 상향 조정 및 실적 서프라이즈 모멘텀 수치화.
    - EPS / Target Price 추정치 변경 모멘텀
    - PBR / PER 대비 펀더멘탈 추정 개선율
    """
    def __init__(self, lookback_days: int = 60):
        self.lookback_days = lookback_days

    def compute_scores(
        self,
        prices_dict: Dict[str, pd.DataFrame],
        fundamentals_dict: Optional[Dict[str, Dict[str, Any]]] = None,
        indicators_df: Optional[Any] = None,
        **kwargs: Any,
    ) -> pd.DataFrame:
        """
        Computes ARM factor scores in [0.0, 1.0] for all symbols.
        Returns pd.DataFrame with columns ['symbol', 'arm_score'].
        """
        # Handle dict or positional fallback
        if isinstance(prices_dict, dict) and any(isinstance(v, dict) for v in prices_dict.values()) and not fundamentals_dict:
            fund = prices_dict
            prc = kwargs.get("prices_dict", {}) if isinstance(kwargs.get("prices_dict"), dict) else {}
        else:
            prc = prices_dict if isinstance(prices_dict, dict) else {}
            fund = fundamentals_dict if isinstance(fundamentals_dict, dict) else {}

        if not prc and not fund:
            return pd.DataFrame(columns=['symbol', 'arm_score'])

        symbols = list(set(list(prc.keys()) + list(fund.keys())))
        raw_scores = {}

        for sym in symbols:
            f_data = fund.get(sym, {}) if isinstance(fund, dict) else {}
            try:
                eps_rev = f_data.get('eps_revision_pct')
                tp_rev = f_data.get('tp_revision_pct')

                if eps_rev is not None or tp_rev is not None:
                    e_rev = _safe_float(eps_rev, 0.0)
                    t_rev = _safe_float(tp_rev, 0.0)
                    arm_raw = (e_rev * 0.5) + (t_rev * 0.5)
                else:
                    eps_growth = _safe_float(f_data.get('eps_growth'), 0.0)
                    rev_growth = _safe_float(f_data.get('revenue_growth'), 0.0)
                    per = _safe_float(f_data.get('per'), 15.0)
                    per_penalty = max(0.0, per) * 0.01
                    arm_raw = (eps_growth * 0.4) + (rev_growth * 0.3) - per_penalty

                price_mom = 0.0
                if sym in prc and isinstance(prc[sym], pd.DataFrame) and not prc[sym].empty:
                    df = prc[sym]
                    col = 'close' if 'close' in df.columns else ('Close' if 'Close' in df.columns else None)
                    if col:
                        close = df[col].dropna()
                        if len(close) >= 20 and float(close.iloc[-20]) > 0:
                            price_mom = float((close.iloc[-1] - close.iloc[-20]) / close.iloc[-20] * 100)

                arm_raw += (price_mom * 0.2)
                raw_scores[sym] = arm_raw
            except Exception as e:
                logger.debug(f"[ARM FACTOR] Error computing score for {sym}: {e}")
                raw_scores[sym] = 0.0

        if not raw_scores:
            return pd.DataFrame(columns=['symbol', 'arm_score'])

        vals = np.array(list(raw_scores.values()))
        lower = np.percentile(vals, 1)
        upper = np.percentile(vals, 99)
        if upper == lower:
            return pd.DataFrame([{'symbol': k, 'arm_score': 0.5} for k in raw_scores.keys()])

        res_rows = []
        for k, v in raw_scores.items():
            sc = float(np.clip((v - lower) / (upper - lower), 0.0, 1.0))
            res_rows.append({'symbol': k, 'arm_score': sc})

        return pd.DataFrame(res_rows)

