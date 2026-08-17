"""
test_data_validator.py — Unit tests for DataValidator module
"""

import unittest
import pandas as pd
from src.data_layer.data_validator import DataValidator, detect_shared_series_corruption, clean_macro_value, filter_price_spikes


class TestDataValidator(unittest.TestCase):

    def test_detect_shared_series_corruption(self):
        # Corrupted identical values
        self.assertTrue(detect_shared_series_corruption(103.478, 103.478, 103.478, 103.478))
        # Normal market values
        self.assertFalse(detect_shared_series_corruption(18.5, 75.2, 2380.0, 4.25))

    def test_clean_macro_value(self):
        # Valid value
        self.assertEqual(clean_macro_value("18.50", "20.0", "vix"), "18.50")
        # Invalid / Out of bounds VIX (103.478 > 55.0) -> Fallback applied
        self.assertEqual(clean_macro_value("103.478", "18.50", "vix"), "18.50")
        # NaN handling
        self.assertEqual(clean_macro_value("NaN", "18.50", "vix"), "18.50")

    def test_validate_price_data(self):
        # Valid DataFrame
        df_valid = pd.DataFrame({
            "Open": [100, 101, 102, 103, 104],
            "Close": [101, 102, 103, 104, 105],
            "Volume": [1000, 1100, 1200, 1300, 1400]
        })
        self.assertTrue(DataValidator.validate_price_data("005930", df_valid))

        # Invalid DataFrame (all NaNs)
        df_invalid = pd.DataFrame({
            "Close": [None, None, None, None]
        })
        self.assertFalse(DataValidator.validate_price_data("BAD", df_invalid))

    def test_single_day_price_spike_rejection(self):
        # Normal prices with one massive single-day spike (+400%)
        df_spike = pd.DataFrame({
            "Open": [100, 101, 500, 505, 510],
            "Close": [100, 101, 500, 505, 510],
            "Volume": [1000, 1000, 1000, 1000, 1000]
        })
        # Should be rejected because max return magnitude > 300% (from 101 to 500 = +395%)
        self.assertFalse(DataValidator.validate_price_data("SPIKE", df_spike))

    def test_unadjusted_split_and_corporate_action_gate(self):
        # Unadjusted 1:4 stock split (price dropped from 400 to 100)
        dates = pd.date_range("2026-01-01", periods=6)
        df_split = pd.DataFrame({
            "Open": [400.0, 404.0, 408.0, 100.0, 101.0, 102.0],
            "High": [405.0, 409.0, 412.0, 102.0, 103.0, 104.0],
            "Low": [398.0, 400.0, 405.0, 99.0, 100.0, 101.0],
            "Close": [400.0, 404.0, 408.0, 100.0, 101.0, 102.0],
            "Volume": [100, 100, 100, 400, 400, 400]
        }, index=dates)

        is_valid, adjusted_df = DataValidator.sanitize_and_validate_price_data("SPLIT_SYM", df_split)
        self.assertTrue(is_valid)
        # Prior prices before split are scaled down (~400 * (100/408) ≈ 98.039)
        self.assertAlmostEqual(float(adjusted_df["Close"].iloc[0]), 98.039, delta=2.0)

    def test_filter_price_spikes(self):
        dates = pd.date_range("2026-01-01", periods=5)
        df_spike = pd.DataFrame({
            "Open": [100, 101, 1000, 102, 103],
            "Close": [100, 101, 1000, 102, 103],
            "Volume": [1000, 1000, 1000, 1000, 1000]
        }, index=dates)

        cleaned_df = filter_price_spikes(df_spike, max_return=3.0)
        self.assertNotIn(1000, cleaned_df["Close"].values)
        self.assertTrue(DataValidator.validate_price_data("CLEAN_SPIKE", cleaned_df))


if __name__ == "__main__":
    unittest.main()
