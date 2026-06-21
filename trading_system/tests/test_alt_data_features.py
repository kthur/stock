import unittest
from unittest.mock import MagicMock, patch
import pandas as pd
import numpy as np
from src.data_layer.alt_data import AlternativeDataClient
from src.data_layer.darkpool_tracker import DarkPoolTracker

# Mandatory Integrity Warning
# DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results,
# create dummy/facade implementations, or circumvent the intended task. A Forensic
# Auditor will independently verify your work. Integrity violations WILL be detected
# and your work WILL be rejected.


class TestAltDataFeatures(unittest.TestCase):

    def setUp(self):
        self.alt_client = AlternativeDataClient()
        self.dp_tracker = DarkPoolTracker()

    @patch("yfinance.Ticker")
    def test_fetch_put_call_ratio_success(self, mock_ticker):
        """Test put/call ratio downloading successfully from yfinance."""
        mock_instance = MagicMock()
        mock_df = pd.DataFrame(
            {"Close": [0.65, 0.70, 0.58]},
            index=pd.date_range("2026-06-01", periods=3)
        )
        mock_instance.history.return_value = mock_df
        mock_ticker.return_value = mock_instance

        res = self.alt_client.fetch_put_call_ratio("2026-06-01")
        self.assertFalse(res.empty)
        self.assertEqual(len(res), 3)
        self.assertEqual(res.iloc[0], 0.65)
        self.assertEqual(res.iloc[2], 0.58)

    @patch("yfinance.Ticker")
    def test_fetch_put_call_ratio_fallback(self, mock_ticker):
        """Test fallback generation when yfinance fails or is empty."""
        mock_instance = MagicMock()
        mock_instance.history.return_value = pd.DataFrame()  # Empty
        mock_ticker.return_value = mock_instance

        res = self.alt_client.fetch_put_call_ratio("2026-06-01")
        self.assertFalse(res.empty)
        # Should generate a pandas Series with dates up to today
        self.assertTrue(isinstance(res, pd.Series))
        self.assertTrue(len(res) > 0)
        self.assertTrue((res >= 0.3).all() and (res <= 1.2).all())

    def test_dark_pool_tracker_with_data(self):
        """Test DarkPoolTracker with provided pricing DataFrame."""
        # Create 10 days of synthetic pricing data
        dates = pd.date_range("2026-06-01", periods=10)
        df_price = pd.DataFrame({
            "Close": [100.0, 101.0, 102.0, 101.5, 103.0, 104.0, 105.0, 104.5, 106.0, 108.0],
            "Volume": [1000, 1200, 1100, 900, 1500, 1300, 1400, 950, 1600, 2000]
        }, index=dates)

        res = self.dp_tracker.fetch_darkpool_activity("AAPL", df_price)
        self.assertEqual(res["symbol"], "AAPL")
        self.assertIn("dark_pool_ratio", res)
        self.assertIn("block_trade_net_usd", res)
        self.assertIn("is_accumulation", res)
        self.assertIn("is_distribution", res)

        # Check accumulation condition (last return > 0 and vol_ratio > 1.2)
        # vol_ratio relative to 20d mean:
        # last volume is 2000, mean is around 1300 -> ratio ~1.5 > 1.2
        # last return is from 106.0 to 108.0 (positive) -> accumulation should be True
        self.assertTrue(res["is_accumulation"])
        self.assertFalse(res["is_distribution"])
        self.assertTrue(0.1 <= res["dark_pool_ratio"] <= 0.6)

    @patch("yfinance.Ticker")
    def test_dark_pool_tracker_fallback(self, mock_ticker):
        """Test DarkPoolTracker fallback when no data is provided or yfinance fails."""
        mock_instance = MagicMock()
        mock_instance.history.return_value = pd.DataFrame()  # Empty
        mock_ticker.return_value = mock_instance

        res = self.dp_tracker.fetch_darkpool_activity("MSFT", None)
        self.assertEqual(res["symbol"], "MSFT")
        self.assertEqual(res["dark_pool_ratio"], 0.35)
        self.assertEqual(res["block_trade_net_usd"], 0.0)
        self.assertFalse(res["is_accumulation"])
        self.assertFalse(res["is_distribution"])


if __name__ == '__main__':
    unittest.main()
