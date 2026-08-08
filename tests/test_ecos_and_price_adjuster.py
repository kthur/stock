"""
test_ecos_and_price_adjuster.py — Unit Tests for ECOS Client and Corporate Action Price Adjuster
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "trading_system")))

from src.data_layer.ecos_client import BOKECOSClient
from src.data_layer.price_adjuster import CorporateActionAdjuster


class TestECOSAndPriceAdjuster(unittest.TestCase):

    def test_corporate_action_adjuster(self):
        # Create synthetic 1:2 split data
        dates = pd.date_range("2024-01-01", periods=5, freq="D")
        closes = [100.0, 102.0, 51.0, 52.0, 53.0] # 50% drop at day 3 (split 1:2)
        df_raw = pd.DataFrame({"Close": closes, "Open": closes, "High": closes, "Low": closes, "Volume": [1000]*5}, index=dates)

        adjuster = CorporateActionAdjuster(split_threshold_pct=0.40)
        df_adj = adjuster.adjust_ohlcv(df_raw)

        # Before split (days 1 and 2), prices should be scaled down by 0.5 -> 50.0 and 51.0
        self.assertAlmostEqual(df_adj.loc[dates[0], "Close"], 50.0, places=1)
        self.assertAlmostEqual(df_adj.loc[dates[1], "Close"], 51.0, places=1)
        self.assertAlmostEqual(df_adj.loc[dates[2], "Close"], 51.0, places=1)

    @patch("urllib.request.urlopen")
    def test_ecos_client_statistic_fetch(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = b'''{
            "StatisticSearch": {
                "row": [
                    {"TIME": "20240101", "DATA_VALUE": "3.50"},
                    {"TIME": "20240102", "DATA_VALUE": "3.50"}
                ]
            }
        }'''
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        client = BOKECOSClient(api_key="mock_key")
        df_stat = client.fetch_statistic("722Y001", "0101000")

        self.assertFalse(df_stat.empty)
        self.assertEqual(len(df_stat), 2)
        self.assertAlmostEqual(df_stat["Value"].iloc[0], 3.50)

    def test_ecos_client_koreabank_key_env(self):
        with patch.dict(os.environ, {"KOREABANK_ECOS_KEY": "my_test_koreabank_key"}, clear=True):
            client = BOKECOSClient()
            self.assertEqual(client.api_key, "my_test_koreabank_key")


if __name__ == "__main__":
    unittest.main()
