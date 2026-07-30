"""
tests/test_r3_coverage_and_universe.py
Unit tests for Strategy Data Coverage Analyzer, Raw Score NaN Masking, and Universe Fundamentals.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results,
create dummy/facade implementations, or circumvent the intended task. A Forensic
Auditor will independently verify your work. Integrity violations WILL be detected
and your work WILL be rejected.
"""

import os
import sys
import unittest
import numpy as np
import pandas as pd

# Ensure project root and trading_system are in sys.path
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_TS_DIR = os.path.join(_ROOT, "trading_system")
if _TS_DIR not in sys.path:
    sys.path.insert(0, _TS_DIR)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.ai.ensemble_scorer import EnsembleScoringEngine
from src.analysis.coverage_analyzer import StrategyCoverageAnalyzer


class TestCoverageAndUniverse(unittest.TestCase):

    def setUp(self):
        self.analyzer = StrategyCoverageAnalyzer()
        self.engine = EnsembleScoringEngine()

    def test_ensemble_scorer_preserves_raw_score_nans(self):
        reg_df = pd.DataFrame({"symbol": ["005930", "000660"], "reg_score": [0.8, 0.6]})
        surge_df = pd.DataFrame({"symbol": ["005930"], "surge_score": [0.9]})  # 000660 missing surge_score!

        merged = self.engine.combine_predictions(
            reg_df=reg_df,
            s_df=surge_df,
            ll_df=pd.DataFrame(),
            vcp_ml_df=pd.DataFrame()
        )

        # Confirm merged returned DataFrame has filled values for reporting
        self.assertIn("ensemble_score", merged.columns)

        # Confirm raw_scores stored in attrs preserves NaNs prior to fillna(0.0)
        self.assertIn("raw_scores", merged.attrs)
        raw_scores = merged.attrs["raw_scores"]
        self.assertIn("surge_score", raw_scores.columns)

        # 000660 should be NaN in raw_scores for surge_score
        row_660 = raw_scores[raw_scores["symbol"] == "000660"]
        self.assertFalse(row_660.empty)
        self.assertTrue(pd.isna(row_660.iloc[0]["surge_score"]))

    def test_coverage_analyzer_reasons_and_counts(self):
        # Create ensemble_df with raw_scores in attrs
        ensemble_df = pd.DataFrame({"symbol": ["005930", "000660"], "ensemble_score": [0.8, 0.6]})
        raw_scores = pd.DataFrame({
            "symbol": ["005930", "000660"],
            "reg_score": [0.8, 0.6],
            "surge_score": [0.9, np.nan],
            "rim_score": [np.nan, np.nan],
        })
        ensemble_df.attrs["raw_scores"] = raw_scores

        prices_dict = {
            "005930": pd.DataFrame(index=pd.date_range("2023-01-01", periods=250, freq="D")),
            "000660": pd.DataFrame(index=pd.date_range("2023-01-01", periods=100, freq="D")),  # < 200 days
        }

        features_df = pd.DataFrame({
            "symbol": ["000990"],
            "bps": [50000.0],
            "roe": [0.12]
        })

        analysis = self.analyzer.analyze_coverage(
            ensemble_df=ensemble_df,
            prices_dict=prices_dict,
            features_df=features_df
        )

        self.assertEqual(analysis["total_symbols"], 2)
        strats = analysis["strategies"]

        # Regression: 2 valid (100% coverage)
        self.assertEqual(strats["regression"]["valid_count"], 2)
        self.assertEqual(strats["regression"]["coverage_pct"], 100.0)

        # Surge: 1 valid, 1 missing
        self.assertEqual(strats["surge"]["valid_count"], 1)
        self.assertEqual(strats["surge"]["missing_count"], 1)

        # RIM Valuation: 0 valid, missing due to insufficient price history & no fundamental data
        self.assertEqual(strats["rim_valuation"]["valid_count"], 0)
        reasons = strats["rim_valuation"]["reasons"]
        self.assertIn("INSUFFICIENT_PRICE_HISTORY", reasons)
        self.assertIn("NO_FUNDAMENTAL_DATA", reasons)

    def test_has_symbol_fundamental_data_variations(self):
        # Test DataFrame with symbol column
        df = pd.DataFrame({"symbol": ["005930"], "roe": [0.15], "bps": [52000.0]})
        self.assertTrue(self.analyzer._has_symbol_fundamental_data(df, "005930"))
        self.assertFalse(self.analyzer._has_symbol_fundamental_data(df, "000660"))

        # Test zfill matching
        df2 = pd.DataFrame({"symbol": ["005930"], "eps": [1000.0]})
        self.assertTrue(self.analyzer._has_symbol_fundamental_data(df2, "5930"))

        # Test Dict of DataFrames
        dict_feats = {"005930": pd.DataFrame({"operating_margin": [0.10]})}
        self.assertTrue(self.analyzer._has_symbol_fundamental_data(dict_feats, "005930"))


if __name__ == "__main__":
    unittest.main()
