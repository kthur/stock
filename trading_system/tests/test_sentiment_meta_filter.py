"""Unit tests for DART News Sentiment Meta-Filter & Risk Integration"""

import unittest
import pandas as pd
from src.data_layer.dart_news_fetcher import DARTNewsFetcher
from src.risk.sentiment_filter import SentimentMetaFilter
from src.ai.ensemble_scorer import EnsembleScoringEngine
from src.risk.risk_manager import RiskManager


class TestSentimentMetaFilter(unittest.TestCase):

    def setUp(self):
        self.fetcher = DARTNewsFetcher()
        self.meta_filter = SentimentMetaFilter(fetcher=self.fetcher, risk_threshold=0.70)
        self.scorer = EnsembleScoringEngine()
        self.risk_mgr = RiskManager(portfolio_value=10000000.0)

    def test_risk_keyword_matching(self):
        matched = self.fetcher._match_risk_keyword("주요사항보고서(유상증자 결정)")
        self.assertEqual(matched, "유상증자")

        matched_safe = self.fetcher._match_risk_keyword("단기금융업무 영가 승인 안내")
        self.assertIsNone(matched_safe)

    def test_instant_blacklist_critical_disclosure(self):
        headlines = ["회사 배임 및 횡령 혐의 수사 개시"]
        result = self.meta_filter.evaluate_symbol("000001", headlines=headlines)

        self.assertTrue(result.is_blacklisted)
        self.assertEqual(result.risk_score, 1.0)
        self.assertIn("횡령", result.detected_keywords)
        self.assertTrue(self.meta_filter.is_blacklisted("000001"))

    def test_clean_symbol_not_blacklisted(self):
        headlines = ["분기 최고 실적 달성 및 신제품 양산 개시"]
        result = self.meta_filter.evaluate_symbol("005930", headlines=headlines)

        self.assertFalse(result.is_blacklisted)
        self.assertEqual(result.risk_score, 0.0)
        self.assertFalse(self.meta_filter.is_blacklisted("005930"))

    def test_ensemble_scorer_zero_weighting_blacklisted(self):
        # Blacklist 000001
        self.meta_filter.evaluate_symbol("000001", headlines=["유상증자 결정 공시"])

        reg_df = pd.DataFrame({"symbol": ["005930", "000001"], 20: [0.10, 0.20]})
        surge_df = pd.DataFrame({"symbol": ["005930", "000001"], "surge_20d": [0.8, 0.9]})
        lead_lag_df = pd.DataFrame({"symbol": ["005930", "000001"], "lead_lag_score": [0.5, 0.7]})
        vcp_ml_df = pd.DataFrame({"symbol": ["005930", "000001"], "vcp_20d": [0.6, 0.8]})

        ensemble_df = self.scorer.calculate_ensemble_score(
            regime="BULL_LOW_VOL",
            regression_df=reg_df,
            surge_df=surge_df,
            lead_lag_df=lead_lag_df,
            vcp_ml_df=vcp_ml_df,
            sentiment_blacklist=self.meta_filter.get_blacklist(),
        )

        blacklisted_row = ensemble_df[ensemble_df["symbol"] == "000001"]
        self.assertFalse(blacklisted_row.empty)
        self.assertEqual(float(blacklisted_row["ensemble_score"].iloc[0]), 0.0)
        self.assertEqual(float(blacklisted_row["ensemble_expected_return"].iloc[0]), 0.0)

    def test_risk_manager_blacklist_guard(self):
        self.meta_filter.evaluate_symbol("BAD_STOCK", headlines=["상장폐지 절차 진행 안내"])
        is_blocked = self.risk_mgr.check_sentiment_blacklist("BAD_STOCK", blacklist=self.meta_filter.get_blacklist())
        self.assertTrue(is_blocked)

        is_blocked_clean = self.risk_mgr.check_sentiment_blacklist("GOOD_STOCK", blacklist=self.meta_filter.get_blacklist())
        self.assertFalse(is_blocked_clean)


if __name__ == "__main__":
    unittest.main()
