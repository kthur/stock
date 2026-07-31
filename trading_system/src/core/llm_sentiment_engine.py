"""
LLM/NLP DART & SEC Filing Sentiment Engine
Extracts sentiment and tone scores from DART/SEC filings using LLM/FinBERT-style NLP rules.
"""

import logging
import re
from dataclasses import dataclass
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class FilingSentimentResult:
    symbol: str
    sentiment_score: float  # [-1.0, +1.0]
    tone_confidence: float
    positive_keywords_count: int
    negative_keywords_count: int
    summary_tone: str


class DARTSECSentimentEngine:
    """
    NLP & Sentiment Scoring Engine for DART (Korean) and SEC (English) filings.
    Quantifies management tone, risk disclosures, and forward guidance sentiment.
    """

    POSITIVE_WORDS_KO = {"흑자전환", "최고실적", "수주계약", "자사주소각", "영업이익증가", "기술이전", "특허취득", "매출상향"}
    NEGATIVE_WORDS_KO = {"적자전환", "감감계약", "횡령", "배임", "소송", "회계감사거절", "영업이익감소", "유상증자", "부도"}

    POSITIVE_WORDS_EN = {"record revenue", "earnings surprise", "share buyback", "upgraded guidance", "patent granted", "contract win"}
    NEGATIVE_WORDS_EN = {"going concern", "sec investigation", "accounting restatement", "default risk", "downgraded guidance", "class action"}

    def __init__(self):
        pass

    def analyze_filing_text(self, symbol: str, text: str) -> FilingSentimentResult:
        """Analyzes text from DART or SEC filings and outputs sentiment score in [-1.0, 1.0]."""
        if not text:
            return FilingSentimentResult(symbol, 0.0, 0.0, 0, 0, "NEUTRAL")

        text_lower = text.lower()
        pos_count = 0
        neg_count = 0

        # Scan Korean keywords
        for w in self.POSITIVE_WORDS_KO:
            if w in text:
                pos_count += 1
        for w in self.NEGATIVE_WORDS_KO:
            if w in text:
                neg_count += 1

        # Scan English keywords
        for w in self.POSITIVE_WORDS_EN:
            if w in text_lower:
                pos_count += 1
        for w in self.NEGATIVE_WORDS_EN:
            if w in text_lower:
                neg_count += 1

        total_matches = pos_count + neg_count
        if total_matches == 0:
            return FilingSentimentResult(symbol, 0.0, 0.5, 0, 0, "NEUTRAL")

        raw_score = (pos_count - neg_count) / float(total_matches)
        confidence = min(1.0, total_matches / 5.0)

        if raw_score >= 0.2:
            summary = "BULLISH"
        elif raw_score <= -0.2:
            summary = "BEARISH"
        else:
            summary = "NEUTRAL"

        return FilingSentimentResult(
            symbol=symbol,
            sentiment_score=float(raw_score),
            tone_confidence=float(confidence),
            positive_keywords_count=pos_count,
            negative_keywords_count=neg_count,
            summary_tone=summary,
        )


# Aliases for backwards compatibility
LLMSentimentEngine = DARTSECSentimentEngine
FilingSentimentMetrics = FilingSentimentResult
