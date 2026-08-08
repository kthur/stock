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

logger = logging.getLogger(__name__)


class EarningsToneDriftEngine:
    """
    LLM-based Earnings Call & Disclosure Tone Drift Engine.
    """

    def __init__(self, config=None):
        self.config = config

    def compute_tone_drift_scores(
        self,
        symbols: List[str],
        transcript_map: Optional[Dict[str, Dict[str, Any]]] = None
    ) -> pd.DataFrame:
        """
        Computes Tone Drift Acceleration score per symbol [0.0, 1.0].
        Returns DataFrame with ['symbol', 'tone_drift_score'].
        """
        if not symbols:
            return pd.DataFrame(columns=['symbol', 'tone_drift_score'])

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

                if abs(tone_delta) > 0.15:
                    logger.info(f"[EARNINGS TONE DRIFT] Tone Drift acceleration for {sym}: {prev_tone:.2f} -> {cur_tone:.2f} (Delta={tone_delta:+.2f}, Score={score:.2f})")

            results.append({'symbol': sym, 'tone_drift_score': score})

        return pd.DataFrame(results)
