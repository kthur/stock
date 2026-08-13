"""
LLM/NLP DART & SEC Filing Sentiment Engine
Extracts sentiment and tone scores from DART/SEC filings using LLM/FinBERT-style NLP rules.
"""

import logging
from dataclasses import dataclass
from typing import Any
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class FilingSentimentResult:
    symbol: str
    filing_date: str = ""
    filing_tone_score: float = 0.5
    catalyst_surprise_score: float = 0.5
    composite_sentiment_score: float = 0.5
    confidence_score: float = 0.7
    source_type: str = "OFFLINE_LEXICON"
    sentiment_score: float = 0.0  # [-1.0, +1.0]
    tone_confidence: float = 0.5
    positive_keywords_count: int = 0
    negative_keywords_count: int = 0
    summary_tone: str = "NEUTRAL"

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "filing_date": self.filing_date,
            "filing_tone_score": self.filing_tone_score,
            "catalyst_surprise_score": self.catalyst_surprise_score,
            "composite_sentiment_score": self.composite_sentiment_score,
            "confidence_score": self.confidence_score,
            "source_type": self.source_type,
            "sentiment_score": self.sentiment_score,
            "tone_confidence": self.tone_confidence,
            "summary_tone": self.summary_tone,
        }


from src.core.base_strategy import BaseStrategyEngine
from src.core.strategy_registry import register_strategy, StrategyMeta


@register_strategy(
    StrategyMeta(
        strategy_id="sentiment",
        display_name="NLP Sentiment Catalyst",
        score_column="sentiment_score",
        category="event",
        output_file="sentiment_predictions.txt",
        default_regime_weights={
            "BEAR": 0.05, "BEAR_HIGH_VOL": 0.06, "SIDEWAYS_LOW_VOL": 0.04, "BULL_HIGH_VOL": 0.04, "BULL_LOW_VOL": 0.04
        },
    )
)
class DARTSECSentimentEngine(BaseStrategyEngine):
    """
    NLP & Sentiment Scoring Engine for DART (Korean) and SEC (English) filings.
    Quantifies management tone, risk disclosures, and forward guidance sentiment.
    """

    POSITIVE_WORDS_KO = {"흑자전환", "최고실적", "수주계약", "자사주소각", "영업이익증가", "기술이전", "특허취득", "매출상향", "실적개선", "무상증자", "자기주식소각"}
    NEGATIVE_WORDS_KO = {"적자전환", "감감계약", "횡령", "배임", "소송", "회계감사거절", "영업이익감소", "유상증자", "부도", "실적 감소", "실적감소", "감자"}

    POSITIVE_WORDS_EN = {"record revenue", "earnings surprise", "share buyback", "upgraded guidance", "patent granted", "contract win", "revenue growth", "profit margin"}
    NEGATIVE_WORDS_EN = {"going concern", "sec investigation", "accounting restatement", "default risk", "downgraded guidance", "class action", "litigation", "net loss"}

    def __init__(self, db_storage=None):
        self.db_storage = db_storage

    def _score_offline_lexicon(self, text: str, symbol: str = "", market: str = "KOSPI", **kwargs) -> Any:
        if not text:
            score = 0.5
        else:
            text_lower = text.lower()
            pos_count = sum(1 for w in self.POSITIVE_WORDS_KO if w in text) + sum(1 for w in self.POSITIVE_WORDS_EN if w in text_lower)
            neg_count = sum(1 for w in self.NEGATIVE_WORDS_KO if w in text) + sum(1 for w in self.NEGATIVE_WORDS_EN if w in text_lower)
            total = pos_count + neg_count
            if total == 0:
                score = 0.5
            else:
                score = float(np.clip(0.5 + (pos_count - neg_count) / float(2 * (total + 1)), 0.0, 1.0))

        if symbol:
            comp = 0.6 * score + 0.4 * kwargs.get('catalyst_surprise_score', 0.5)
            return FilingSentimentResult(
                symbol=symbol,
                filing_tone_score=score,
                catalyst_surprise_score=kwargs.get('catalyst_surprise_score', 0.5),
                composite_sentiment_score=comp,
                confidence_score=0.7,
                source_type="OFFLINE_LEXICON",
                sentiment_score=float(score * 2.0 - 1.0),
            )
        return score

    def analyze_filing(self, symbol: str, text: str, filing_date: str = "", market: str = "KOSPI", catalyst_surprise_score: float = 0.5, filing_id: str = "") -> FilingSentimentResult:
        if self.db_storage and filing_id:
            cached = self.db_storage.get_filing_sentiment(symbol, filing_date=filing_date, filing_id=filing_id)
            if cached:
                return FilingSentimentResult(
                    symbol=cached.get('symbol', symbol),
                    filing_date=cached.get('filing_date', filing_date),
                    filing_tone_score=cached.get('filing_tone_score', 0.5),
                    catalyst_surprise_score=cached.get('catalyst_surprise_score', 0.5),
                    composite_sentiment_score=cached.get('composite_sentiment_score', 0.5),
                    confidence_score=cached.get('confidence_score', 0.7),
                    source_type="CACHE",
                    sentiment_score=float(cached.get('filing_tone_score', 0.5) * 2.0 - 1.0),
                )
        res = self._score_offline_lexicon(text, symbol=symbol, market=market, catalyst_surprise_score=catalyst_surprise_score)
        if isinstance(res, FilingSentimentResult):
            res.filing_date = filing_date
            return res
        tone_score = res
        comp_score = 0.6 * tone_score + 0.4 * catalyst_surprise_score
        return FilingSentimentResult(
            symbol=symbol,
            filing_date=filing_date,
            filing_tone_score=float(tone_score),
            catalyst_surprise_score=float(catalyst_surprise_score),
            composite_sentiment_score=float(comp_score),
            confidence_score=0.7,
            source_type="OFFLINE_LEXICON",
            sentiment_score=float(tone_score * 2.0 - 1.0),
            tone_confidence=0.7,
        )

    def analyze_filing_text(self, symbol: str, text: str) -> FilingSentimentResult:
        """Analyzes text from DART or SEC filings and outputs sentiment score in [-1.0, 1.0]."""
        if not text:
            return FilingSentimentResult(symbol=symbol, sentiment_score=0.0, tone_confidence=0.0, positive_keywords_count=0, negative_keywords_count=0, summary_tone="NEUTRAL")

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
            return FilingSentimentResult(symbol=symbol, sentiment_score=0.0, tone_confidence=0.5, positive_keywords_count=0, negative_keywords_count=0, summary_tone="NEUTRAL")

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

    def compute_scores(
        self,
        prices_dict: Any = None,
        fundamentals_dict: Any = None,
        indicators_df: Any = None,
        **kwargs: Any,
    ) -> Any:
        """Compute NLP sentiment catalyst score (0% to 100%) for universe symbols. Returns NaN if no filing text exists."""
        import pandas as pd
        
        universe = kwargs.get("universe", kwargs.get("universe_df"))
        filings_map = kwargs.get("filings_map") or {}

        if universe is None or not isinstance(universe, pd.DataFrame):
            if isinstance(prices_dict, dict):
                symbols = list(prices_dict.keys())
            elif isinstance(prices_dict, pd.DataFrame):
                universe = prices_dict
                symbols = []
            else:
                symbols = []
            if symbols:
                universe = pd.DataFrame({"symbol": symbols, "name": symbols, "market": "KRX"})

        results = []
        if universe is None or not isinstance(universe, pd.DataFrame) or universe.empty:
            return pd.DataFrame(columns=["symbol", "name", "market", "sentiment_score"])

        filings_dict = filings_map if isinstance(filings_map, dict) else {}

        for _, row in universe.iterrows():
            sym = str(row["symbol"]).strip()
            name = str(row.get("name", sym))
            mkt = str(row.get("market", "KRX"))

            text = filings_dict.get(sym, filings_dict.get(sym.zfill(6), ""))
            if text:
                res = self.analyze_filing_text(sym, text)
                score = float(np.clip(0.5 + res.sentiment_score * 0.4, 0.0, 1.0))
            else:
                score = np.nan

            results.append({
                "symbol": sym,
                "name": name,
                "market": mkt,
                "sentiment_score": round(score, 4) if pd.notna(score) else np.nan,
            })


        res_df = pd.DataFrame(results)
        if not res_df.empty:
            res_df = res_df.sort_values(by="sentiment_score", ascending=False, na_position='last').reset_index(drop=True)
        return res_df


# Aliases for backwards compatibility
LLMSentimentEngine = DARTSECSentimentEngine
FilingSentimentMetrics = FilingSentimentResult
