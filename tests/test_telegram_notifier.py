"""
test_telegram_notifier.py — Unit Tests for Telegram Signal Card Notifier
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "trading_system")))

import pandas as pd
from src.execution.telegram_notifier import TelegramNotifier


class TestTelegramNotifier(unittest.TestCase):

    def setUp(self):
        self.mock_df = pd.DataFrame([
            {
                "symbol": "005930",
                "name": "삼성전자",
                "market": "KOSPI",
                "ensemble_score": 0.885,
                "close": 75000.0,
                "supply_chain_score": 0.90,
                "sentiment_score": 0.85,
                "factor_neutralized_score": 0.82,
                "vol_target_score": 0.80,
                "microstructure_score": 0.78,
            },
            {
                "symbol": "NVDA",
                "name": "NVIDIA",
                "market": "SP500",
                "ensemble_score": 0.920,
                "close": 120.50,
                "supply_chain_score": 0.95,
                "sentiment_score": 0.89,
                "factor_neutralized_score": 0.88,
                "vol_target_score": 0.85,
                "microstructure_score": 0.84,
            }
        ])

    def test_disabled_without_env_vars(self):
        notifier = TelegramNotifier(token="", chat_id="")
        self.assertFalse(notifier.is_enabled())
        res = notifier.send_top_recommendations_card(self.mock_df)
        self.assertFalse(res)

    @patch("urllib.request.urlopen")
    def test_send_top_recommendations_card_success(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_response

        notifier = TelegramNotifier(token="mock_token_123", chat_id="mock_chat_456")
        self.assertTrue(notifier.is_enabled())

        res = notifier.send_top_recommendations_card(self.mock_df, regime_name="BULL_LOW_VOL")
        self.assertTrue(res)
        self.assertTrue(mock_urlopen.called)


if __name__ == "__main__":
    unittest.main()
