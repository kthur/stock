"""
Unit tests for strategy engines edge cases:
- Empty DataFrames / empty dictionaries
- NaNs and Infs in prices or fundamentals
- Missing required columns
- Zero division protection
"""

import unittest
import numpy as np
import pandas as pd

from src.core.arm_factor import ARMFactorEngine
from src.core.card_factor import CARDFactorEngine
from src.core.latr_factor import LATRFactorEngine
from src.core.accruals_quality import AccrualsQualityEngine
from src.core.trend_efficiency import TrendEfficiencyEngine
from src.core.supply_chain import SupplyChainEngine


class TestStrategyEdgeCases(unittest.TestCase):
    def setUp(self):
        # Sample empty & corrupted price dataframes
        dates = pd.date_range("2024-01-01", periods=30)
        self.valid_df = pd.DataFrame({
            "Open": np.linspace(100, 110, 30),
            "High": np.linspace(102, 112, 30),
            "Low": np.linspace(99, 109, 30),
            "Close": np.linspace(101, 111, 30),
            "Volume": [10000] * 30,
        }, index=dates)

        self.nan_df = pd.DataFrame({
            "Open": [np.nan] * 30,
            "High": [np.nan] * 30,
            "Low": [np.nan] * 30,
            "Close": [np.nan] * 30,
            "Volume": [0] * 30,
        }, index=dates)

        self.empty_df = pd.DataFrame()

    def test_arm_factor_edge_cases(self):
        engine = ARMFactorEngine()
        # Empty inputs
        res = engine.compute_scores({}, {})
        self.assertEqual(res, {})

        # Valid mock inputs
        fund = {"AAPL": {"eps_revision_pct": 0.05, "per": 15.0}}
        prices = {"AAPL": self.valid_df}
        scores = engine.compute_scores(prices, fund)
        self.assertIn("AAPL", scores)
        self.assertTrue(0.0 <= scores["AAPL"] <= 1.0)

    def test_card_factor_edge_cases(self):
        engine = CARDFactorEngine()
        # Empty inputs
        res = engine.compute_scores(pd.DataFrame(), {})
        self.assertEqual(res, {})

        # Valid inputs
        indicator_df = pd.DataFrame({"usdkrw_change": [0.01], "wti_change": [0.02], "vix_change": [0.0]})
        prices = {"AAPL": self.valid_df}
        scores = engine.compute_scores(indicator_df, prices)
        self.assertIn("AAPL", scores)
        self.assertTrue(0.0 <= scores["AAPL"] <= 1.0)

    def test_latr_factor_edge_cases(self):
        engine = LATRFactorEngine()
        # Empty input
        res = engine.compute_scores({})
        self.assertEqual(res, {})

        # Valid inputs
        prices = {"AAPL": self.valid_df}
        scores = engine.compute_scores(prices)
        self.assertIn("AAPL", scores)
        self.assertTrue(0.0 <= scores["AAPL"] <= 1.0)

    def test_accruals_quality_edge_cases(self):
        engine = AccrualsQualityEngine()
        # Empty symbols
        df_out = engine.compute_scores({})
        self.assertTrue(df_out.empty)

        # Missing OCF & Net Income with NaNs
        prices = {"005930": self.valid_df}
        fund = {"005930": {"net_income": np.nan, "operating_cash_flow": np.nan}}
        df_out = engine.compute_scores(prices, fund)
        self.assertFalse(df_out.empty)
        self.assertIn("accruals_quality_score", df_out.columns)

    def test_trend_efficiency_edge_cases(self):
        engine = TrendEfficiencyEngine()
        # Empty prices
        df_out = engine.compute_scores({})
        self.assertTrue(df_out.empty)

        # NaN price series
        prices = {"005930": self.nan_df}
        df_out = engine.compute_scores(prices)
        self.assertFalse(df_out.empty)

    def test_supply_chain_edge_cases(self):
        engine = SupplyChainEngine()
        # Empty inputs
        df_out = engine.compute_scores({}, None)
        self.assertTrue(df_out.empty)


if __name__ == "__main__":
    unittest.main()
