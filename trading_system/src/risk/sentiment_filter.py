"""Sentiment Meta-Filter & Blacklist Engine"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Set, Any
from src.data_layer.dart_news_fetcher import DARTNewsFetcher, DisclosureEvent, CRITICAL_RISK_KEYWORDS

logger = logging.getLogger(__name__)


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
    """Evaluates corporate sentiment risk and filters out blacklisted symbols due to negative disclosures/news."""

    def __init__(
        self,
        fetcher: Optional[DARTNewsFetcher] = None,
        risk_threshold: float = 0.70,
    ):
        self.fetcher = fetcher or DARTNewsFetcher()
        self.risk_threshold = risk_threshold
        self._blacklist: Dict[str, SentimentRiskResult] = {}

    def evaluate_symbol(
        self,
        symbol: str,
        headlines: Optional[List[str]] = None,
        disclosures: Optional[List[DisclosureEvent]] = None,
    ) -> SentimentRiskResult:
        """Evaluates disclosure and news headlines for a stock symbol to check for severe risk."""
        events: List[DisclosureEvent] = []

        if disclosures:
            events.extend(disclosures)
        else:
            api_events = self.fetcher.fetch_dart_disclosures(symbol)
            events.extend(api_events)

        if headlines:
            scanned_events = self.fetcher.scan_text_items(symbol, headlines, source="News")
            events.extend(scanned_events)

        detected_kw: Set[str] = set()
        for ev in events:
            if ev.is_risk and ev.risk_keyword:
                detected_kw.add(ev.risk_keyword)

        kw_list = sorted(list(detected_kw))

        # Risk score calculation:
        # Base score = 0.0
        # Each unique risk keyword adds 0.40 score (capped at 1.0)
        risk_score = min(len(kw_list) * 0.40, 1.0)

        # High priority critical keywords (유상증자, 횡령, 배임, 관리종목, 상장폐지) instantly cause score = 1.0
        instant_blacklist_kw = {"유상증자", "횡령", "배임", "관리종목", "상장폐지", "감자의견", "영업정지"}
        if any(kw in instant_blacklist_kw for kw in kw_list):
            risk_score = 1.0

        is_blacklisted = risk_score >= self.risk_threshold

        reason = ""
        if is_blacklisted:
            reason = f"Critical risk disclosure/news detected: {', '.join(kw_list)}"
            logger.warning(f"[SENTIMENT BLACKLIST] Symbol {symbol} BLACKLISTED! Reason: {reason} (Score: {risk_score:.2f})")

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
