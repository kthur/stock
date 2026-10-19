"""DART Corporate Disclosure & Financial News Fetcher

Fixes:
  - corp_code is now resolved via DARTCorpMapper (CORPCODE.xml-based lookup)
    instead of incorrectly using symbol.zfill(8).
  - Added fetch_naver_news() for real-time Korean financial news crawling.
"""

import os
import logging
import re
import html
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import requests

from src.data_layer.dart_corp_mapper import DARTCorpMapper

logger = logging.getLogger(__name__)

# 12 Mandatory Risk Disclosure Keywords (DART & News)
CRITICAL_RISK_KEYWORDS = [
    "유상증자",
    "전환사채",
    "신주인수권부사채",
    "횡령",
    "배임",
    "관리종목",
    "감자의견",
    "영업정지",
    "소송",
    "회계처리기준위반",
    "상장폐지",
    "불성실공시",
]

# Negation patterns: if present near the keyword, treat as non-risk
_NEGATION_PATTERNS = [
    "계획 없음", "계획없음", "부인", "무혐의", "기각", "해소", "철회", "완료",
    "없다", "아니다", "아님", "취소", "철수", "면제", "결정 취소", "허위",
    "오해", "정정", "해명", "반박", "부정", "소송 취하",
]
# Window (characters) around keyword to check for negation context
_NEGATION_WINDOW = 50


@dataclass
class DisclosureEvent:
    """Represents a corporate disclosure or news headline event."""
    symbol: str
    title: str
    date: str
    is_risk: bool
    risk_keyword: Optional[str] = None
    source: str = "DART"
    details: Dict[str, Any] = field(default_factory=dict)


class DARTNewsFetcher:
    """Fetches corporate disclosures via OpenDART API and recent Korean financial news.

    Key Fixes vs. original implementation:
    - corp_code is now properly resolved via DARTCorpMapper instead of zfill(8).
    - fetch_naver_news() added for real-time headline crawling.
    - _match_risk_keyword() now supports negation-context filtering.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        corp_mapper: Optional[DARTCorpMapper] = None,
    ):
        self.api_key = api_key or os.environ.get("DART_API_KEY", "").strip()
        self.corp_mapper = corp_mapper or DARTCorpMapper(api_key=self.api_key)
        self.timeout = 5.0

    # ------------------------------------------------------------------
    # OpenDART disclosure fetch (bug-fixed)
    # ------------------------------------------------------------------

    def fetch_dart_disclosures(self, symbol: str, days: int = 7) -> List[DisclosureEvent]:
        """Fetches disclosures from OpenDART API.

        FIXED: corp_code is now resolved via DARTCorpMapper.get_corp_code()
        instead of the incorrect symbol.zfill(8) which returns the KRX symbol
        (e.g., "005930") instead of the OpenDART corp_code (e.g., "00126380").
        """
        if not self.api_key:
            logger.debug(f"DART_API_KEY not set. Using local disclosure scanner for {symbol}")
            return []

        safe_days = max(1, int(days)) if days is not None else 7

        # ✅ Fixed: resolve actual DART corp_code from KRX stock symbol
        corp_code = self.corp_mapper.get_corp_code(symbol)
        if not corp_code:
            logger.debug(
                f"DARTNewsFetcher: no corp_code mapping found for symbol={symbol}. "
                "Skipping OpenDART API call."
            )
            return []

        url = "https://opendart.fss.or.kr/api/list.json"
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=safe_days)).strftime("%Y%m%d")

        params: Dict[str, Any] = {
            "crtfc_key": self.api_key,
            "corp_code": corp_code,
            "bgn_de": start_date,
            "end_de": end_date,
            "page_count": 50,
        }

        events = []
        try:
            resp = requests.get(url, params=params, timeout=self.timeout)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("status") == "000" and "list" in data:
                    for item in data["list"]:
                        title = item.get("report_nm", "")
                        r_date = item.get("rcept_dt", end_date)
                        risk_kw = self._match_risk_keyword(title)
                        events.append(
                            DisclosureEvent(
                                symbol=symbol,
                                title=title,
                                date=r_date,
                                is_risk=bool(risk_kw),
                                risk_keyword=risk_kw,
                                source="OpenDART",
                            )
                        )
        except Exception as e:
            logger.warning(f"Failed to fetch OpenDART disclosures for {symbol}: {e}")

        return events

    # ------------------------------------------------------------------
    # Naver Financial News Crawler (NEW)
    # ------------------------------------------------------------------

    def fetch_naver_news(self, symbol: str, max_items: int = 20) -> List[DisclosureEvent]:
        """Crawls recent Naver Finance news headlines for the given Korean stock symbol.

        Uses Naver Finance news RSS feed (no API key required).
        Returns DisclosureEvents for any headlines containing risk keywords.
        """
        safe_max = max(1, int(max_items)) if max_items is not None else 20
        # Naver Finance news search RSS for Korean stocks
        code = str(symbol).strip().split('.')[0].zfill(6) if str(symbol).strip().split('.')[0].isdigit() else str(symbol).strip()
        rss_url = f"https://finance.naver.com/item/news_news.naver?code={code}&page=1&sm=title_entity_id.basic&clusterId="
        events: List[DisclosureEvent] = []
        today_str = datetime.now().strftime("%Y%m%d")

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Referer": "https://finance.naver.com",
        }

        try:
            resp = requests.get(rss_url, headers=headers, timeout=self.timeout)
            if resp.status_code != 200:
                logger.debug(f"Naver news fetch returned {resp.status_code} for {symbol}")
                return []

            # Naver Finance news pages use EUC-KR / CP949 encoding
            try:
                text = resp.content.decode("euc-kr", errors="replace")
            except Exception:
                text = resp.text

            # Match title anchors from the news list table
            title_pattern = re.compile(
                r'<a[^>]+class="[^"]*tit[^"]*"[^>]*>(.*?)</a>', re.DOTALL
            )
            raw_titles = title_pattern.findall(text)

            # Strip HTML tags and decode entities
            safe_max = max(1, int(max_items)) if max_items is not None else 10
            clean_titles = []
            for raw in raw_titles[:safe_max]:
                clean = re.sub(r"<[^>]+>", "", raw).strip()
                clean = html.unescape(clean)
                if clean:
                    clean_titles.append(clean)

            # Scan cleaned titles for risk keywords
            for title in clean_titles[:safe_max]:
                kw = self._match_risk_keyword(title)
                if kw:
                    events.append(
                        DisclosureEvent(
                            symbol=symbol,
                            title=title,
                            date=today_str,
                            is_risk=True,
                            risk_keyword=kw,
                            source="NaverNews",
                        )
                    )

        except Exception as e:
            logger.debug(f"Naver news crawl failed for {symbol}: {e}")

        return events

    # ------------------------------------------------------------------
    # Text scanning
    # ------------------------------------------------------------------

    def scan_text_items(
        self, symbol: str, text_items: List[str], source: str = "News"
    ) -> List[DisclosureEvent]:
        """Scans a list of text strings (headlines, filings, reports) for risk keywords."""
        events = []
        today_str = datetime.now().strftime("%Y%m%d")
        for text in text_items:
            kw = self._match_risk_keyword(text)
            if kw:
                events.append(
                    DisclosureEvent(
                        symbol=symbol,
                        title=text,
                        date=today_str,
                        is_risk=True,
                        risk_keyword=kw,
                        source=source,
                    )
                )
        return events

    # ------------------------------------------------------------------
    # Keyword matching with negation context filtering
    # ------------------------------------------------------------------

    def _match_risk_keyword(self, text: str) -> Optional[str]:
        """Checks if text contains any of the 12 critical risk keywords.

        NEW: Applies negation-context filtering to reduce false positives.
        If the keyword appears near a negation phrase (e.g., "유상증자 계획 없음"),
        it is NOT treated as a risk.
        """
        if not text:
            return None
        for kw in CRITICAL_RISK_KEYWORDS:
            idx = text.find(kw)
            if idx == -1:
                continue
            # Check negation context in a window around the keyword
            start = max(0, idx - _NEGATION_WINDOW)
            end = min(len(text), idx + len(kw) + _NEGATION_WINDOW)
            window = text[start:end]
            if self._has_negation_context(window):
                logger.debug(
                    f"Keyword '{kw}' found in '{text[:60]}' but negation context detected – skipped."
                )
                continue
            return kw
        return None

    @staticmethod
    def _has_negation_context(window_text: str) -> bool:
        """Returns True if the text window contains any negation pattern."""
        for neg in _NEGATION_PATTERNS:
            if neg in window_text:
                return True
        return False
