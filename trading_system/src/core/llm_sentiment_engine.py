"""
LLM/NLP DART & SEC Filing Sentiment Engine
Extracts sentiment and tone scores from DART/SEC filings using LLM/FinBERT-style NLP rules.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Optional
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
    NEGATIVE_WORDS_KO = {"적자전환", "공급계약해지", "계약해지", "감액계약", "횡령", "배임", "소송", "회계감사거절", "영업이익감소", "유상증자", "부도", "실적 감소", "실적감소", "감자", "감사의견거절", "관리종목"}
    NEGATION_WORDS_KO = {"철회", "취소", "실패", "불투명", "무산", "지연", "불발", "의혹", "하향", "미달", "부정적", "소송", "제동", "차질", "난항"}

    POSITIVE_WORDS_EN = {"record revenue", "earnings surprise", "share buyback", "upgraded guidance", "patent granted", "contract win", "revenue growth", "profit margin"}
    NEGATIVE_WORDS_EN = {"going concern", "sec investigation", "accounting restatement", "default risk", "downgraded guidance", "class action", "litigation", "net loss"}
    NEGATION_WORDS_EN = {"cancel", "cancelled", "withdrawn", "failed", "unlikely", "delayed", "missed", "lawsuit", "investigation", "rejected"}

    def __init__(self, db_storage=None, model_name: Optional[str] = None):
        self.db_storage = db_storage
        self.model_name = model_name
        self._hf_pipeline = None
        if model_name:
            try:
                from transformers import pipeline
                self._hf_pipeline = pipeline("text-classification", model=model_name)
                logger.info(f"Loaded Transformer NLP model: {model_name}")
            except Exception as e:
                logger.debug(f"Transformers pipeline initialization skipped: {e}. Using robust lexicon.")

    def _score_offline_lexicon(self, text: str, symbol: str = "", market: str = "KOSPI", **kwargs) -> Any:
        if not text or not isinstance(text, str) or not text.strip():
            score = 0.5
        else:
            text_str = str(text)
            text_lower = text_str.lower()
            pos_count = 0.0
            neg_count = 0.0

            # Scan Korean positive words with window-based negation detection (±12 chars)
            for w in self.POSITIVE_WORDS_KO:
                start_idx = 0
                while True:
                    idx = text.find(w, start_idx)
                    if idx == -1:
                        break
                    window = text[max(0, idx - 12): min(len(text), idx + len(w) + 12)]
                    is_negated = any(neg in window for neg in self.NEGATION_WORDS_KO)
                    if "불구하고" in window or "비록" in window:
                        is_negated = False
                    if is_negated:
                        neg_count += 1.5  # Inverted fake-positive is penalized as a negative shock
                    else:
                        pos_count += 1.0
                    start_idx = idx + len(w)

            # Scan Korean negative words
            for w in self.NEGATIVE_WORDS_KO:
                start_idx = 0
                while True:
                    idx = text.find(w, start_idx)
                    if idx == -1:
                        break
                    neg_count += 1.0
                    start_idx = idx + len(w)

            # Scan English positive words with negation detection
            for w in self.POSITIVE_WORDS_EN:
                start_idx = 0
                while True:
                    idx = text_lower.find(w, start_idx)
                    if idx == -1:
                        break
                    window = text_lower[max(0, idx - 12): min(len(text_lower), idx + len(w) + 12)]
                    is_negated = any(neg in window for neg in self.NEGATION_WORDS_EN)
                    if "despite" in window or "although" in window:
                        is_negated = False
                    if is_negated:
                        neg_count += 1.5
                    else:
                        pos_count += 1.0
                    start_idx = idx + len(w)

            # Scan English negative words
            for w in self.NEGATIVE_WORDS_EN:
                start_idx = 0
                while True:
                    idx = text_lower.find(w, start_idx)
                    if idx == -1:
                        break
                    neg_count += 1.0
                    start_idx = idx + len(w)

            total = pos_count + neg_count
            if total == 0:
                score = 0.5
            else:
                score = float(np.clip(0.5 + (pos_count - neg_count) / float(2.0 * (total + 1.0)), 0.0, 1.0))

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

        try:
            from src.ai.sentiment import SentimentAnalyzer
            analyzer = SentimentAnalyzer()
            res = analyzer.analyze(text)
            if isinstance(res, dict):
                pos_val = float(res.get('positive', 0.0))
                neg_val = float(res.get('negative', 0.0))
                if pos_val > 0.0 or neg_val > 0.0:
                    raw_score = float(res.get('score', 0.0))
                    pos_count = int(pos_val * 5.0)
                    neg_count = int(neg_val * 5.0)
                    confidence = float(min(1.0, max(0.2, pos_val + neg_val)))
                    summary = "BULLISH" if raw_score >= 0.20 else ("BEARISH" if raw_score <= -0.20 else "NEUTRAL")
                    return FilingSentimentResult(
                        symbol=symbol,
                        sentiment_score=raw_score,
                        tone_confidence=confidence,
                        positive_keywords_count=pos_count,
                        negative_keywords_count=neg_count,
                        summary_tone=summary
                    )
        except Exception:
            pass

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

    def batch_analyze_filings(self, filings: Any) -> dict[str, FilingSentimentResult]:
        """Analyzes a list of DART or SEC filings in batch and returns a map of symbol -> FilingSentimentResult."""
        results: dict[str, FilingSentimentResult] = {}
        if not filings:
            return results

        filings_list = filings if isinstance(filings, list) else [filings]
        for item in filings_list:
            if not isinstance(item, dict):
                continue
            symbol = str(item.get("stock_code") or item.get("symbol") or "").strip()
            if not symbol:
                continue
            text = str(item.get("report_nm") or item.get("title") or item.get("content") or item.get("summary") or "").strip()
            filing_date = str(item.get("rcept_dt") or item.get("date") or item.get("filing_date") or "").strip()

            if not text:
                continue

            res = self.analyze_filing_text(symbol, text)
            res.filing_date = filing_date
            if symbol not in results or abs(res.sentiment_score) > abs(results[symbol].sentiment_score):
                results[symbol] = res
                # Also store without leading zeros or with zfill for robust lookup
                if symbol.isdigit():
                    results[symbol.zfill(6)] = res
                    results[symbol.lstrip('0') or '0'] = res

        return results

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
        sentiment_map = kwargs.get("sentiment_map") or {}
        filings = kwargs.get("filings") or kwargs.get("eff_filings")

        # Auto-compute sentiment map from raw filings if provided and sentiment_map is empty
        if not sentiment_map and filings:
            sentiment_map = self.batch_analyze_filings(filings)

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
        sent_dict = sentiment_map if isinstance(sentiment_map, dict) else {}

        for row in universe.itertuples(index=False):
            r_dict = row._asdict() if hasattr(row, '_asdict') else dict(zip(universe.columns, row))
            sym = str(r_dict.get("symbol", "")).strip()
            name = str(r_dict.get("name", sym))
            mkt = str(r_dict.get("market", "KRX"))

            score = np.nan

            # 1. Check pre-computed sentiment_map
            sent_res = sent_dict.get(sym) or sent_dict.get(sym.zfill(6)) or sent_dict.get(sym.lstrip('0'))
            if sent_res is not None:
                if isinstance(sent_res, FilingSentimentResult):
                    score = float(np.clip(0.5 + sent_res.sentiment_score * 0.4, 0.0, 1.0))
                elif isinstance(sent_res, (int, float)):
                    s_val = float(sent_res)
                    score = s_val if 0.0 <= s_val <= 1.0 else float(np.clip(0.5 + s_val * 0.4, 0.0, 1.0))
                score = score if np.isfinite(score) else 0.5

            # 2. Check filings text map if not resolved yet
            if pd.isna(score):
                text = filings_dict.get(sym) or filings_dict.get(sym.zfill(6)) or filings_dict.get(sym.lstrip('0'), "")
                if text:
                    res = self.analyze_filing_text(sym, str(text))
                    score = float(np.clip(0.5 + res.sentiment_score * 0.4, 0.0, 1.0))
                    score = score if np.isfinite(score) else 0.5

            results.append({
                "symbol": sym,
                "name": name,
                "market": mkt,
                "sentiment_score": round(float(score), 4) if (pd.notna(score) and np.isfinite(score)) else np.nan,
            })

        res_df = pd.DataFrame(results)
        if not res_df.empty:
            res_df['sentiment_score'] = pd.to_numeric(res_df['sentiment_score'], errors='coerce')
            res_df = res_df.sort_values(by="sentiment_score", ascending=False, na_position='last').reset_index(drop=True)
        return res_df


# Aliases for backwards compatibility
LLMSentimentEngine = DARTSECSentimentEngine
FilingSentimentMetrics = FilingSentimentResult
