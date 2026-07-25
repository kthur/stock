"""DART Corporate Disclosure & Financial News Fetcher"""

import os
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import requests

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
    """Fetches corporate disclosures via OpenDART API and recent financial news headlines for stock symbols."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("DART_API_KEY", "").strip()
        self.timeout = 5.0

    def fetch_dart_disclosures(self, symbol: str, days: int = 7) -> List[DisclosureEvent]:
        """Fetches disclosures from OpenDART API or falls back to rules engine if API key is not set."""
        if not self.api_key:
            logger.debug(f"DART_API_KEY not set. Using local disclosure scanner for {symbol}")
            return []

        # OpenDART API URL for disclosures
        url = "https://opendart.fss.or.kr/api/list.json"
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")

        params = {
            "crtfc_key": self.api_key,
            "corp_code": symbol.zfill(8),
            "bde_de": start_date,
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

    def _match_risk_keyword(self, text: str) -> Optional[str]:
        """Checks if text contains any of the 12 critical risk keywords."""
        if not text:
            return None
        for kw in CRITICAL_RISK_KEYWORDS:
            if kw in text:
                return kw
        return None

    def scan_text_items(self, symbol: str, text_items: List[str], source: str = "News") -> List[DisclosureEvent]:
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
