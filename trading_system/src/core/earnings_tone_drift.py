"""
src/core/earnings_tone_drift.py
LLM-based Earnings Call & Disclosure Tone Drift Engine.

Analyzes text sentiment drift from OpenDART / SEC filings and conference call transcripts:
  - Tone Acceleration: Delta in sentiment polarity (Pessimistic -> Optimistic)
  - Management Guidance Confidence Score
  - Tone Drift Score [0.0, 1.0]
"""

import logging
from typing import Dict, List, Optional, Any
import numpy as np
import pandas as pd

from src.core.base_strategy import BaseStrategyEngine
from src.core.strategy_registry import register_strategy, StrategyMeta

logger = logging.getLogger(__name__)


@register_strategy(
    StrategyMeta(
        strategy_id="earnings_tone_drift",
        display_name="Earnings Tone Drift",
        score_column="earnings_tone_drift_score",
        category="sentiment",
        output_file="earnings_tone_drift_predictions.txt",
        default_regime_weights={
            "BEAR": 0.02, "BEAR_HIGH_VOL": 0.02, "SIDEWAYS_LOW_VOL": 0.03, "BULL_HIGH_VOL": 0.03, "BULL_LOW_VOL": 0.03
        },
    )
)
class EarningsToneDriftEngine(BaseStrategyEngine):
    """
    LLM-based Earnings Call & Disclosure Tone Drift Engine.
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
        return self.compute_tone_drift_scores(symbols=symbols, **kwargs)

    def compute_tone_drift_scores(
        self,
        symbols: List[str],
        transcript_map: Optional[Dict[str, Dict[str, Any]]] = None
    ) -> pd.DataFrame:
        """
        Computes Tone Drift Acceleration score per symbol [0.0, 1.0].
        Returns DataFrame with ['symbol', 'earnings_tone_drift_score'].
        """
        if not symbols:
            return pd.DataFrame(columns=['symbol', 'earnings_tone_drift_score'])

        results = []

        def _safe_float(val: Any, default: float) -> float:
            if val is None or pd.isna(val):
                return default
            try:
                res = float(val)
                return default if np.isnan(res) else res
            except (ValueError, TypeError):
                return default

        for sym in symbols:
            score = 0.50  # Base neutral score

            if transcript_map and sym in transcript_map:
                t_data = transcript_map[sym]
                prev_tone = _safe_float(t_data.get('previous_quarter_tone'), 0.50)
                cur_tone = _safe_float(t_data.get('current_quarter_tone'), 0.50)
                confidence = _safe_float(t_data.get('confidence'), 1.0)

                # Tone Drift Delta (Positive = Management Sentiment Upgrade)
                tone_delta = (cur_tone - prev_tone) * confidence
                score = float(np.clip(0.50 + 1.0 * tone_delta, 0.0, 1.0))

            results.append({
                'symbol': sym,
                'earnings_tone_drift_score': score,
                'tone_drift_score': score
            })

        return pd.DataFrame(results)
