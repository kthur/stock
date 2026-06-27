import urllib.request
import xml.etree.ElementTree as ET
import logging
from datetime import datetime, timedelta
from typing import Dict, Tuple, Optional
import urllib.parse

from src.ai.sentiment import SentimentAnalyzer

logger = logging.getLogger(__name__)

class NewsSentimentFetcher:
    """뉴스 수집 및 감성 분석 엔진 (Google News RSS & SentimentAnalyzer 통합)"""

    def __init__(self, sentiment_analyzer: Optional[SentimentAnalyzer] = None, cache_ttl_hours: int = 1):
        self.sentiment_analyzer = sentiment_analyzer or SentimentAnalyzer(domain="finance")
        self.cache_ttl_hours = cache_ttl_hours
        self.cache: Dict[str, Tuple[float, datetime]] = {} # symbol -> (score, expiry)

    def _get_rss_url(self, query: str, is_korean: bool = True) -> str:
        encoded_query = urllib.parse.quote(query)
        if is_korean:
            return f"https://news.google.com/rss/search?q={encoded_query}&hl=ko&gl=KR&ceid=KR:ko"
        else:
            return f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"

    def fetch_and_analyze(self, symbol: str, name: Optional[str] = None, market: str = "KOSPI") -> float:
        """종목 관련 뉴스 수집 후 평균 감성 점수 반환 [-1.0, 1.0]. 실패 시 0.0 (중립) 반환"""
        now = datetime.now()

        # 캐시 확인
        if symbol in self.cache:
            score, expiry = self.cache[symbol]
            if now < expiry:
                logger.debug(f"Cache hit for symbol {symbol}: {score}")
                return score

        # 검색 쿼리 결정 (이름 우선, 없으면 심볼)
        query = name if name else symbol
        is_korean = market in ["KOSPI", "KOSDAQ", "KONEX"]
        url = self._get_rss_url(query, is_korean=is_korean)

        try:
            req = urllib.request.Request(
                url,
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
            )
            # 타임아웃 10초
            with urllib.request.urlopen(req, timeout=10) as response:  # nosec B310
                xml_data = response.read()

            root = ET.fromstring(xml_data)  # nosec B314
            items = root.findall('.//item')

            if not items:
                logger.warning(f"No news found for query: {query}")
                self.cache[symbol] = (0.0, now + timedelta(hours=self.cache_ttl_hours))
                return 0.0

            total_score = 0.0
            count = 0

            # 상위 5개 뉴스 기사 분석
            for item in items[:5]:
                title = item.find('title')
                desc = item.find('description')

                text_to_analyze = ""
                if title is not None and title.text:
                    text_to_analyze += title.text + " "
                if desc is not None and desc.text:
                    # HTML 태그 제거
                    cleaned_desc = ET.fromstring(f"<span>{desc.text}</span>").itertext()  # nosec B314
                    text_to_analyze += "".join(cleaned_desc)

                text_to_analyze = text_to_analyze.strip()
                if text_to_analyze:
                    try:
                        # SentimentAnalyzer.analyze()는 딕셔너리를 반환하며 'score' 키에 [-1.0, 1.0] 점수가 들어있음
                        res = self.sentiment_analyzer.analyze(text_to_analyze)
                        total_score += res.get('score', 0.0)
                        count += 1
                    except Exception as e:
                        logger.debug(f"Error analyzing text: {e}")
                        continue

            avg_score = total_score / count if count > 0 else 0.0

            # 결과 캐싱
            self.cache[symbol] = (avg_score, now + timedelta(hours=self.cache_ttl_hours))
            logger.info(f"Fetched and analyzed news for {symbol} ({query}): score={avg_score:.4f} (based on {count} articles)")
            return avg_score

        except Exception as e:
            logger.error(f"Failed to fetch news sentiment for {symbol}: {e}")
            # 에러 발생 시에도 캐시를 0.0으로 5분간 임시 저장하여 연속적인 API 타임아웃/오류를 방지
            self.cache[symbol] = (0.0, now + timedelta(minutes=5))
            return 0.0
