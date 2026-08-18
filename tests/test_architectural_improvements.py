"""Unit tests for Architectural Improvements & Refinements."""

import unittest
import numpy as np
import pandas as pd
from src.persistence.database import StockPriceDB
from src.ai.ensemble_scorer import EnsembleScoringEngine
from src.data_layer.overnight_gap_shifter import OvernightGapShifter


class TestArchitecturalImprovements(unittest.TestCase):

    def test_ohlc_invariant_and_multi_column_cleaning(self):
        """Test validate_and_clean_price_series preserves Low <= Open,Close <= High under extreme spikes."""
        dates = pd.date_range('2026-01-01', periods=10, freq='D')
        df = pd.DataFrame({
            'Open': [100.0, 101.0, 102.0, 103.0, 500.0, 104.0, 105.0, 106.0, 107.0, 108.0],
            'High': [102.0, 103.0, 104.0, 105.0, 550.0, 106.0, 107.0, 108.0, 109.0, 110.0],
            'Low':  [98.0,  99.0,  100.0, 101.0, 480.0, 102.0, 103.0, 104.0, 105.0, 106.0],
            'Close':[101.0, 102.0, 103.0, 104.0, 520.0, 105.0, 106.0, 107.0, 108.0, 109.0],
            'Volume': [1000] * 10
        }, index=dates)

        cleaned = StockPriceDB.validate_and_clean_price_series(df, max_daily_jump=0.65)
        self.assertFalse(cleaned.empty)

        # Bar 4 (index 4) should be interpolated to smooth series around ~104-105
        self.assertLess(cleaned.iloc[4]['Close'], 150.0)
        self.assertLess(cleaned.iloc[4]['High'], 150.0)
        self.assertLess(cleaned.iloc[4]['Open'], 150.0)
        self.assertLess(cleaned.iloc[4]['Low'], 150.0)

        # Strict OHLC invariants across all rows
        for idx, row in cleaned.iterrows():
            self.assertGreaterEqual(row['High'], row['Close'])
            self.assertGreaterEqual(row['High'], row['Open'])
            self.assertLessEqual(row['Low'], row['Close'])
            self.assertLessEqual(row['Low'], row['Open'])
            self.assertGreater(row['Low'], 0.0)

    def test_ensemble_scorer_real_prices_dict_covariance(self):
        """Test EnsembleScoringEngine utilizes real return series from prices_dict for risk parity."""
        scorer = EnsembleScoringEngine()
        dates = pd.date_range('2026-01-01', periods=60, freq='D')
        np.random.seed(42)

        # Create 3 candidate symbols with realistic correlated price series
        prices_dict = {
            '005930': pd.DataFrame({'Close': 70000.0 * np.exp(np.cumsum(np.random.normal(0.0005, 0.015, 60)))}, index=dates),
            '000660': pd.DataFrame({'Close': 120000.0 * np.exp(np.cumsum(np.random.normal(0.0008, 0.020, 60)))}, index=dates),
            '035420': pd.DataFrame({'Close': 200000.0 * np.exp(np.cumsum(np.random.normal(0.0002, 0.018, 60)))}, index=dates),
        }

        # Mock strategy prediction DataFrames
        reg_df = pd.DataFrame({'symbol': ['005930', '000660', '035420'], 'market': ['KOSPI', 'KOSPI', 'KOSPI'], 'expected_return': [0.12, 0.15, 0.08]})
        surge_df = pd.DataFrame({'symbol': ['005930', '000660', '035420'], 'surge_probability': [0.45, 0.60, 0.30]})

        res = scorer.calculate_ensemble_score(
            regression_df=reg_df,
            surge_df=surge_df,
            prices_dict=prices_dict,
            target_horizon=20
        )

        self.assertFalse(res.empty)
        self.assertIn('portfolio_weight', res.columns)
        self.assertEqual(len(res), 3)
        self.assertAlmostEqual(res['portfolio_weight'].sum(), 1.0, places=2)

    def test_overnight_gap_shifter_krx_markets(self):
        """Test OvernightGapShifter handles both KOSPI and KOSDAQ correctly."""
        shifter = OvernightGapShifter()
        df = pd.DataFrame({
            'symbol': ['005930', '091990'],
            'market': ['KOSPI', 'KOSDAQ'],
            'surge_score': [0.50, 0.50],
            'rim_score': [0.50, 0.50]
        })

        # +1.0% positive gap -> momentum score boosted
        shifted_pos = shifter.apply_gap_shift_to_scores(df, 1.0, market='KRX')
        self.assertGreater(shifted_pos.iloc[0]['surge_score'], 0.50)
        self.assertGreater(shifted_pos.iloc[1]['surge_score'], 0.50)

        # -1.0% negative gap -> defensive / RIM score boosted
        shifted_neg = shifter.apply_gap_shift_to_scores(df, -1.0, market='KRX')
        self.assertGreater(shifted_neg.iloc[0]['rim_score'], 0.50)
        self.assertGreater(shifted_neg.iloc[1]['rim_score'], 0.50)


if __name__ == '__main__':
    unittest.main()
