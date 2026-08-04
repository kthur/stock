"""
test_data_validator.py — Unit tests for DataValidator module
"""

import unittest
import pandas as pd
from src.data_layer.data_validator import DataValidator, detect_shared_series_corruption, clean_macro_value, validate_price_data


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


if __name__ == "__main__":
    unittest.main()
