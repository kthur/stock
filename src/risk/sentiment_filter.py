"""Sentiment Meta-Filter & Blacklist Engine

Changes vs. original:
- Negation-context filtering is now delegated to DARTNewsFetcher._match_risk_keyword(),
  so false positives from "유상증자 계획 없음" etc. are eliminated at source.
- risk_threshold and instant_blacklist_keywords are now configurable via constructor.
- fetch_naver_news() is called in evaluate_symbol() when no headlines are provided.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Set
import numpy as np
from src.data_layer.dart_news_fetcher import DARTNewsFetcher, DisclosureEvent

logger = logging.getLogger(__name__)

# Default set of keywords that immediately trigger score=1.0 (instant blacklist)
_DEFAULT_INSTANT_BLACKLIST_KW: Set[str] = {
    "유상증자", "횡령", "배임", "관리종목", "상장폐지", "감자의견", "영업정지"
}


@dataclass
class SentimentRiskResult:
    """Evaluation result for corporate sentiment and disclosure risk."""
    symbol: str
    is_blacklisted: bool
    risk_score: float
    detected_keywords: List[str] = field(default_factory=list)
    events: List[DisclosureEvent] = field(default_factory=list)
    reason: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))


class SentimentMetaFilter:
    """Evaluates corporate sentiment risk and filters out blacklisted symbols.

    Scoring logic:
    - Each unique risk keyword adds 0.40 score (capped at 1.0).
    - Any keyword in instant_blacklist_keywords immediately sets score = 1.0.
    - Negation context (e.g., "무혐의", "계획 없음") is filtered inside
      DARTNewsFetcher._match_risk_keyword() to avoid false positives.
    - Symbols with score >= risk_threshold are blacklisted.
    """

    def __init__(
        self,
        fetcher: Optional[DARTNewsFetcher] = None,
        risk_threshold: float = 0.70,
        instant_blacklist_keywords: Optional[Set[str]] = None,
        crawl_naver_news: bool = True,
    ):
        self.fetcher = fetcher or DARTNewsFetcher()
        safe_thresh = float(risk_threshold) if (risk_threshold is not None and np.isfinite(risk_threshold)) else 0.70
        self.risk_threshold = max(0.01, min(1.0, safe_thresh))
        self.instant_blacklist_keywords = (
            instant_blacklist_keywords
            if instant_blacklist_keywords is not None
            else _DEFAULT_INSTANT_BLACKLIST_KW
        )
        self.crawl_naver_news = bool(crawl_naver_news)
        self._blacklist: Dict[str, SentimentRiskResult] = {}

    def evaluate_symbol(
        self,
        symbol: str,
        headlines: Optional[List[str]] = None,
        disclosures: Optional[List[DisclosureEvent]] = None,
    ) -> SentimentRiskResult:
        """Evaluates disclosure and news headlines for a stock symbol.

        Data sources (in order of precedence):
        1. caller-provided disclosures (pre-fetched DART events)
        2. DART API via fetcher (if api_key is set)
        3. Naver Finance news crawler (if crawl_naver_news=True and symbol is KRX)
        4. caller-provided headlines text list (scan_text_items)
        """
        events: List[DisclosureEvent] = []

        # 1. Use pre-fetched disclosures if provided; otherwise call DART API
        if disclosures is not None:
            events.extend(disclosures)
        else:
            api_events = self.fetcher.fetch_dart_disclosures(symbol)
            events.extend(api_events)

        # 2. Crawl Naver Finance news (Korean market symbols only, handle .KS / .KQ suffixes)
        sym_clean = str(symbol).replace('.KS', '').replace('.KQ', '').replace('.ks', '').replace('.kq', '').strip()
        if self.crawl_naver_news and sym_clean.isdigit() and len(sym_clean) == 6:
            try:
                naver_events = self.fetcher.fetch_naver_news(sym_clean)
                events.extend(naver_events)
            except Exception as e:
                logger.debug(f"Naver news crawl skipped for {symbol}: {e}")

        # 3. Scan caller-provided headline strings
        if headlines:
            scanned_events = self.fetcher.scan_text_items(symbol, headlines, source="News")
            events.extend(scanned_events)

        # Aggregate detected risk keywords
        detected_kw: Set[str] = set()
        for ev in events:
            if ev.is_risk and ev.risk_keyword:
                detected_kw.add(ev.risk_keyword)

        kw_list = sorted(list(detected_kw))

        # Risk score calculation
        raw_score = min(len(kw_list) * 0.40, 1.0)
        risk_score = float(np.clip(raw_score if np.isfinite(raw_score) else 0.0, 0.0, 1.0))

        # Instant blacklist keywords bypass the threshold
        if any(kw in self.instant_blacklist_keywords for kw in kw_list):
            risk_score = 1.0

        is_blacklisted = bool(risk_score >= self.risk_threshold)

        reason = ""
        if is_blacklisted:
            reason = f"Critical risk disclosure/news detected: {', '.join(kw_list)}"
            logger.warning(
                f"[SENTIMENT BLACKLIST] Symbol {symbol} BLACKLISTED! "
                f"Reason: {reason} (Score: {risk_score:.2f})"
            )

        result = SentimentRiskResult(
            symbol=symbol,
            is_blacklisted=is_blacklisted,
            risk_score=risk_score,
            detected_keywords=kw_list,
            events=events,
            reason=reason,
        )

        if is_blacklisted:
            self._blacklist[symbol] = result

        return result

    def is_blacklisted(self, symbol: str) -> bool:
        """Checks if a symbol is currently blacklisted."""
        return symbol in self._blacklist

    def filter_blacklisted_symbols(self, symbols: List[str]) -> List[str]:
        """Filters out blacklisted symbols from a list."""
        return [s for s in symbols if not self.is_blacklisted(s)]

    def get_blacklist(self) -> Dict[str, SentimentRiskResult]:
        """Returns current blacklist mapping."""
        return self._blacklist.copy()

    def clear_blacklist(self):
        """Clears the internal blacklist cache."""
        self._blacklist.clear()
