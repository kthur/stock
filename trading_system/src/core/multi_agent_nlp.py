"""
Multi-Agent LLM DART/SEC Filing & Tone Drift Analyzer (Strategy #35)
Multi-Agent architecture extracting quantitative catalysts and quarter-over-quarter management tone drift.
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class MultiAgentNLPEngine:
    """
    Strategy #35: Multi-Agent LLM Sentiment & Management Tone Drift Analyzer.
    Agents:
    - Agent 1: Quantitative Catalyst Extractor (CAPEX, Margins, Surprises)
    - Agent 2: Management Tone Drift Evaluator (Quarter-over-Quarter Delta)
    - Agent 3: Synthesis & Risk Weighting
    """

    def __init__(self, tone_drift_weight: float = 0.6, catalyst_weight: float = 0.4):
        self.tone_drift_weight = tone_drift_weight
        self.catalyst_weight = catalyst_weight

    def analyze_filing_text(self, current_text: str, previous_text: Optional[str] = None) -> Dict[str, float]:
        """
        Simulates multi-agent text evaluation on corporate filings / earnings calls.
        """
        if not current_text or len(current_text.strip()) == 0:
            return {"catalyst_score": 50.0, "tone_drift_score": 0.0, "composite_nlp_score": 50.0}

        # Keyword catalyst detection
        positive_keywords = ["expansion", "record revenue", "margin growth", "patent granted", "share buyback"]
        negative_keywords = ["investigation", "litigation", "margin contraction", "guidance cut", "impairment"]

        text_lower = current_text.lower()
        pos_count = sum(1 for kw in positive_keywords if kw in text_lower)
        neg_count = sum(1 for kw in negative_keywords if kw in text_lower)

        catalyst_score = 50.0 + (pos_count * 10.0) - (neg_count * 15.0)
        catalyst_score = float(np.clip(catalyst_score, 0.0, 100.0))

        # Tone drift computation (QoQ comparison)
        if previous_text:
            prev_lower = previous_text.lower()
            prev_pos = sum(1 for kw in positive_keywords if kw in prev_lower)
            prev_neg = sum(1 for kw in negative_keywords if kw in prev_lower)
            prev_score = 50.0 + (prev_pos * 10.0) - (prev_neg * 15.0)
            tone_drift = catalyst_score - prev_score
        else:
            tone_drift = 0.0

        total_w = self.catalyst_weight + self.tone_drift_weight
        if total_w <= 0:
            total_w = 1.0
        composite = ((catalyst_score * self.catalyst_weight) + ((50.0 + tone_drift * 2.0) * self.tone_drift_weight)) / total_w
        if np.isnan(composite) or np.isinf(composite):
            composite = 50.0
        composite = float(np.clip(composite, 0.0, 100.0))

        return {
            "catalyst_score": round(catalyst_score, 2),
            "tone_drift_score": round(tone_drift, 2),
            "composite_nlp_score": round(composite, 2)
        }

    def compute_scores(self, universe_df: pd.DataFrame, filing_sentiment_cache: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
        """
        Calculates Strategy #35 Multi-Agent NLP scores across universe.
        """
        results = []
        for row in universe_df.itertuples(index=False):
            r_dict = row._asdict() if hasattr(row, '_asdict') else dict(zip(universe_df.columns, row))
            sym = str(r_dict.get('symbol', ''))
            name = str(r_dict.get('name', ''))
            mkt = str(r_dict.get('market', ''))

            cached = filing_sentiment_cache.get(sym) if filing_sentiment_cache else None
            if cached and isinstance(cached, dict):
                score = float(cached.get('composite_sentiment_score', 50.0))
                tone = float(cached.get('tone_drift_score', 0.0))
            else:
                score = 50.0
                tone = 0.0

            results.append({
                "symbol": sym,
                "name": name,
                "market": mkt,
                "multi_agent_nlp_score": round(score, 2),
                "tone_drift": round(tone, 2)
            })

        res_df = pd.DataFrame(results)
        if not res_df.empty:
            res_df = res_df.sort_values(by="multi_agent_nlp_score", ascending=False).reset_index(drop=True)
        return res_df
