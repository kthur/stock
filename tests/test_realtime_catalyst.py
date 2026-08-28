# -*- coding: utf-8 -*-
"""
Unit tests for RealTimeCatalystEngine.
"""

import unittest
from datetime import datetime, timedelta

from src.core.realtime_catalyst import RealTimeCatalystEngine


class TestRealTimeCatalystEngine(unittest.TestCase):

    def setUp(self):
        self.engine = RealTimeCatalystEngine(half_life_days=10.0)

    def test_score_event_text(self):
        # Positive KRX event
        score_pos = self.engine.score_event_text("주요사항보고서(자사주 소각 결정)", market='KOSPI')
        self.assertGreater(score_pos, 0.0)

        # Negative KRX event
        score_neg = self.engine.score_event_text("풍문관련(횡령ㆍ배임혐의발생)", market='KOSDAQ')
        self.assertLess(score_neg, 0.0)

        # Positive US event
        score_us = self.engine.score_event_text("FORM 8-K ITEM 2.02 RESULTS OF OPERATIONS AND BUYBACK", market='SP500')
        self.assertGreater(score_us, 0.0)

    def test_compute_decayed_catalyst_scores(self):
        now = datetime(2026, 8, 29, 10, 0, 0)
        events = [
            # Recent strong positive event (today)
            {
                'symbol': '005930',
                'market': 'KOSPI',
                'title': '자사주 소각 및 대규모 단일판매ㆍ공급계약체결',
                'date': now.strftime('%Y-%m-%d'),
            },
            # 10 days ago positive event (should decay by ~50%)
            {
                'symbol': '000660',
                'market': 'KOSPI',
                'title': '무상증자 결정',
                'date': (now - timedelta(days=10)).strftime('%Y-%m-%d'),
            },
            # Recent negative event
            {
                'symbol': 'NVDA',
                'market': 'NASDAQ',
                'title': 'FORM 8-K RESTATEMENT OF FINANCIALS',
                'date': now.strftime('%Y-%m-%d'),
            }
        ]

        scores = self.engine.compute_decayed_catalyst_scores(events, current_date=now)
        self.assertIn('005930', scores)
        self.assertIn('000660', scores)
        self.assertIn('NVDA', scores)

        self.assertGreater(scores['005930'], 0.50)
        self.assertGreater(scores['000660'], 0.50)
        # Recent event should have stronger impact than 10-day old event
        self.assertGreater(scores['005930'], scores['000660'])
        self.assertLess(scores['NVDA'], 0.50)


if __name__ == '__main__':
    unittest.main()
