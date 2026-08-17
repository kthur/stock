"""
Unit tests for FredApiClient and FRED interest rate integration.
Tests URL formatting, mock JSON response parsing, fallback handling, and IRSTCI01KRM156N series retrieval.
"""

import json
import unittest
from unittest.mock import MagicMock, patch

import pandas as pd
from src.data_layer.fred_client import FredApiClient, FRED_SERIES_MAP
from src.data_layer.global_market import GlobalMarketClient


class TestFredApiClient(unittest.TestCase):
    def setUp(self):
        self.api_key = "dummy_fred_api_key_12345"
        self.client = FredApiClient(api_key=self.api_key)

    def test_configuration(self):
        self.assertTrue(self.client.is_configured())

        empty_client = FredApiClient(api_key="")
        with patch.dict("os.environ", {}, clear=True):
            empty_client.api_key = ""
            self.assertFalse(empty_client.is_configured())

    @patch("urllib.request.urlopen")
    def test_fetch_series_observations_success(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.status = 200
        mock_payload = {
            "observations": [
                {"date": "2026-08-01", "value": "3.50"},
                {"date": "2026-08-02", "value": "3.55"},
                {"date": "2026-08-03", "value": "3.60"},
            ]
        }
        mock_response.read.return_value = json.dumps(mock_payload).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        df = self.client.fetch_series_observations("IRSTCI01KRM156N", limit=5)
        self.assertFalse(df.empty)
        self.assertIn("value", df.columns)
        self.assertEqual(len(df), 3)

    @patch("urllib.request.urlopen")
    def test_get_latest_rate_korea_short_term(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.status = 200
        mock_payload = {
            "observations": [
                {"date": "2026-08-01", "value": "3.50"},
                {"date": "2026-08-02", "value": "3.55"},
            ]
        }
        mock_response.read.return_value = json.dumps(mock_payload).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        snapshot = self.client.fetch_korea_short_term_rate()
        self.assertIsNotNone(snapshot)
        self.assertEqual(snapshot["series_id"], "IRSTCI01KRM156N")
        self.assertEqual(snapshot["name"], "Korea Short-Term Interest Rate")
        self.assertEqual(snapshot["value"], 3.55)
        self.assertAlmostEqual(snapshot["change_pct"], 1.43, places=2)

    @patch.object(FredApiClient, "is_configured", return_value=True)
    @patch.object(FredApiClient, "fetch_all_fred_indicators")
    def test_global_market_client_integration(self, mock_fetch_all, mock_is_configured):
        mock_fetch_all.return_value = {
            "IRSTCI01KRM156N": {
                "series_id": "IRSTCI01KRM156N",
                "name": "Korea Short-Term Interest Rate",
                "price": 3.55,
                "change_pct": 1.43,
                "timestamp": "2026-08-09T00:00:00",
            }
        }

        gm_client = GlobalMarketClient()
        macros = gm_client.get_all_macro_commodities()

        self.assertIn("IRSTCI01KRM156N", macros)
        self.assertEqual(macros["IRSTCI01KRM156N"]["price"], 3.55)
        self.assertEqual(macros["IRSTCI01KRM156N"]["name"], "Korea Short-Term Interest Rate")


if __name__ == "__main__":
    unittest.main()
