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
        output_file="arm_factor_predictions.txt",
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
        from .base_strategy import make_score_dataframe

        # Robust argument binding (handles positional swaps or dict inputs)
        if isinstance(prices_dict, dict) and any(isinstance(v, dict) for v in prices_dict.values()):
            fund = prices_dict
            prc = fundamentals_dict if isinstance(fundamentals_dict, dict) else kwargs.get("prices_dict", {})
        elif isinstance(fundamentals_dict, dict) and any(isinstance(v, dict) for v in fundamentals_dict.values()):
            fund = fundamentals_dict
            prc = prices_dict if isinstance(prices_dict, dict) else {}
        else:
            prc = prices_dict if isinstance(prices_dict, dict) else {}
            fund = fundamentals_dict if isinstance(fundamentals_dict, dict) else {}

        if not prc and not fund:
            return make_score_dataframe({}, 'arm_score')

        symbols = list(set(list(prc.keys()) + list(fund.keys())))
        raw_scores = {}

        for sym in symbols:
            p_df = prc.get(sym)
            f_dict = fund.get(sym, {})

            # 1. Consensus Revision (EPS 추정치 변경율 및 fallback)
            raw_eps_rev = f_dict.get('eps_revision_pct')
            if raw_eps_rev is None:
                raw_eps_rev = f_dict.get('eps_growth')
            eps_rev = float(np.clip(_safe_float(raw_eps_rev, default=0.0), -1.0, 2.0))

            raw_tp_rev = f_dict.get('target_price_revision_pct')
            if raw_tp_rev is None:
                raw_tp_rev = f_dict.get('tp_revision_pct')
            target_p_rev = float(np.clip(_safe_float(raw_tp_rev, default=0.0), -1.0, 2.0))

            # 2. Earnings Surprise
            surprise = float(np.clip(_safe_float(f_dict.get('earnings_surprise_pct'), default=0.0), -1.0, 2.0))

            # 3. Fundamental Growth vs Valuation
            growth_score = 0.0
            per = _safe_float(f_dict.get('per'), default=15.0)
            if per > 0:
                # PEG 스타일 (PER 대비 EPS 성장률)
                peg_proxy = eps_rev / (per + 1e-4)
                growth_score = float(np.clip(peg_proxy * 5.0, -0.2, 0.2))
            elif per < 0:
                # Loss making firms (negative PER): negative growth penalized
                growth_score = float(np.clip(eps_rev * 0.10, -0.2, 0.2))

            # 복합 Revision 점수
            revision_composite = (eps_rev * 0.40) + (target_p_rev * 0.30) + (surprise * 0.20) + (growth_score * 0.10)

            # 4. Price Confirmation (최근 20일 주가 모멘텀)
            price_mom = 0.0
            if isinstance(p_df, pd.DataFrame) and len(p_df) >= 20:
                col = 'Close' if 'Close' in p_df.columns else ('close' if 'close' in p_df.columns else None)
                if col:
                    close = p_df[col].dropna()
                    if len(close) >= 20 and close.iloc[-20] > 0:
                        raw_pm = float((close.iloc[-1] / close.iloc[-20]) - 1.0)
                        price_mom = float(np.clip(raw_pm, -0.99, 5.0)) if np.isfinite(raw_pm) else 0.0

            # 가격 확인 필터 (추정치 상향 + 주가 상승 = 강력한 동반 모멘텀, 부드러운 연속형 시너지)
            syn_pos = np.maximum(0.0, np.tanh(10.0 * revision_composite)) * np.maximum(0.0, np.tanh(10.0 * price_mom))
            syn_neg = np.maximum(0.0, np.tanh(-10.0 * revision_composite)) * np.maximum(0.0, np.tanh(-10.0 * price_mom))
            synergy_bonus = float(0.15 * (syn_pos - syn_neg))

            raw_score = 0.5 + (revision_composite * 2.0) + (price_mom * 0.5) + synergy_bonus
            raw_scores[sym] = float(np.clip(raw_score, -5.0, 5.0)) if np.isfinite(raw_score) else 0.5

        if not raw_scores:
            return make_score_dataframe({}, 'arm_score')

        vals = np.array([v for v in raw_scores.values() if np.isfinite(v)])
        if len(vals) == 0:
            return make_score_dataframe({k: 0.5 for k in raw_scores.keys()}, 'arm_score')
        lower = float(np.percentile(vals, 1))
        upper = float(np.percentile(vals, 99))
        if upper <= lower:
            return make_score_dataframe({k: 0.5 for k in raw_scores.keys()}, 'arm_score')

        res_scores = {}
        for k, v in raw_scores.items():
            sc = float(np.clip((v - lower) / (upper - lower), 0.0, 1.0))
            # ARM Consensus Revision Booster for high-conviction analyst upgrades (smooth continuous)
            smooth_boost = 1.0 + 0.10 / (1.0 + np.exp(-10.0 * (sc - 0.75)))
            res_scores[k] = float(np.clip(sc * smooth_boost, 0.0, 1.0))

        return make_score_dataframe(res_scores, 'arm_score')
