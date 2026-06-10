"""NLP Engine - 뉴스 및 텍스트 데이터 분석"""

import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Callable, List

logger = logging.getLogger(__name__)


class Sentiment(Enum):
    """감정 분석 결과"""

    POSITIVE = 1
    NEUTRAL = 0
    NEGATIVE = -1


@dataclass
class NewsData:
    """뉴스 데이터 모델"""

    title: str
    content: str
    symbol: str
    sentiment: Sentiment
    score: float  # -1.0 ~ 1.0
    source: str
    timestamp: datetime

    def __repr__(self):
        return f"NewsData({self.symbol}, {self.sentiment.name}, score={self.score:.2f})"


class NLPEngine:
    DEFAULT_POSITIVE = [
        "상승",
        "긍정",
        "호재",
        "증가",
        "개선",
        "회복",
        "강세",
        "상승장",
        "수익",
        "success",
        "amazing",
        "profit",
        "win",
        "bullish",
    ]
    DEFAULT_NEGATIVE = [
        "하락",
        "부정",
        "악재",
        "감소",
        "악화",
        "위기",
        "약세",
        "하락장",
        "손실",
        "fail",
        "loss",
        "drop",
        "bearish",
    ]

    def __init__(self, event_bus=None, positive_keywords=None, negative_keywords=None):
        self.news_queue: List[NewsData] = []
        self.subscribers: List[Callable] = []
        self.event_bus = event_bus
        self.logger = logger
        self.positive_keywords = positive_keywords or list(self.DEFAULT_POSITIVE)
        self.negative_keywords = negative_keywords or list(self.DEFAULT_NEGATIVE)

    def subscribe(self, callback: Callable):
        """뉴스 분석 결과 구독"""
        self.subscribers.append(callback)
        callback_name = callback.__name__ if hasattr(callback, "__name__") else str(callback)
        self.logger.info(f"Subscribed NLP callback: {callback_name}")

    def analyze_sentiment(self, text: str) -> tuple[Sentiment, float]:
        text_lower = text.lower()

        positive_count = sum(1 for keyword in self.positive_keywords if keyword in text_lower)
        negative_count = sum(1 for keyword in self.negative_keywords if keyword in text_lower)

        max_keywords = max(len(self.positive_keywords), len(self.negative_keywords), 1)
        if positive_count > negative_count:
            score = min(positive_count / max_keywords, 1.0)
            return Sentiment.POSITIVE, score
        elif negative_count > positive_count:
            score = -min(negative_count / max_keywords, 1.0)
            return Sentiment.NEGATIVE, score
        else:
            return Sentiment.NEUTRAL, 0.0

    def process_news(self, title: str, content: str, symbol: str, source: str = "Naver") -> NewsData:
        """뉴스 처리 및 감정 분석"""
        sentiment, score = self.analyze_sentiment(f"{title} {content}")

        news = NewsData(
            title=title,
            content=content,
            symbol=symbol,
            sentiment=sentiment,
            score=score,
            source=source,
            timestamp=datetime.now(),
        )

        self.news_queue.append(news)
        self.logger.info(f"News processed: {news}")

        # 이벤트 버스로 전송
        if self.event_bus:
            self.event_bus.publish("news_sentiment", news)

        # 구독자에게 알림 (하위 호환성)
        for callback in self.subscribers:
            try:
                callback(news)
            except Exception as e:
                self.logger.error(f"NLP callback error: {e}")

        return news

    def get_latest_news(self, symbol: str | None = None, limit: int = 10) -> List[NewsData]:
        """최근 뉴스 조회"""
        if symbol:
            news = [n for n in self.news_queue if n.symbol == symbol]
        else:
            news = self.news_queue

        return news[-limit:]
