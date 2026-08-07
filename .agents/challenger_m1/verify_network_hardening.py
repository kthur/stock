import sys
import time
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock, call
import pandas as pd
import requests

# Add trading_system root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "trading_system"))

from run_pipeline import (
    _fetch_yf_primary,
    _fetch_data_fdr_network,
    prefetch_prices_batch,
    is_empty_result
)
from src.data_layer.market_data_handler import MarketDataHandler, CircuitBreakerOpenException


class TestEmpiricalNetworkHardening(unittest.TestCase):

    def setUp(self):
        self.handler = MarketDataHandler()

    # -------------------------------------------------------------------------
    # 1. Test retry mechanics for _fetch_yf_primary
    # -------------------------------------------------------------------------

    @patch('run_pipeline.yf.download')
    def test_fetch_yf_primary_http_429_exhaustion(self, mock_yf):
        """_fetch_yf_primary should retry 3 times on HTTP 429 before raising Exception."""
        mock_yf.side_effect = requests.exceptions.HTTPError("429 Client Error: Too Many Requests")
        with patch('tenacity.wait_exponential.__call__', return_value=0.001):
            with self.assertRaises(requests.exceptions.HTTPError):
                _fetch_yf_primary("AAPL", "2023-01-01")
        self.assertEqual(mock_yf.call_count, 3)

    @patch('run_pipeline.yf.download')
    def test_fetch_yf_primary_connection_error_exhaustion(self, mock_yf):
        """_fetch_yf_primary should retry 3 times on ConnectionError before raising Exception."""
        mock_yf.side_effect = ConnectionError("Failed to connect")
        with patch('tenacity.wait_exponential.__call__', return_value=0.001):
            with self.assertRaises(ConnectionError):
                _fetch_yf_primary("AAPL", "2023-01-01")
        self.assertEqual(mock_yf.call_count, 3)

    @patch('run_pipeline.yf.download')
    def test_fetch_yf_primary_read_timeout_exhaustion(self, mock_yf):
        """_fetch_yf_primary should retry 3 times on ReadTimeout before raising Exception."""
        mock_yf.side_effect = requests.exceptions.ReadTimeout("Read timed out")
        with patch('tenacity.wait_exponential.__call__', return_value=0.001):
            with self.assertRaises(requests.exceptions.ReadTimeout):
                _fetch_yf_primary("AAPL", "2023-01-01")
        self.assertEqual(mock_yf.call_count, 3)

    @patch('run_pipeline.yf.download')
    def test_fetch_yf_primary_empty_df_exhaustion(self, mock_yf):
        """_fetch_yf_primary should retry 3 times on empty DataFrame return and raise RetryError on exhaustion."""
        import tenacity
        mock_yf.return_value = pd.DataFrame()
        with patch('tenacity.wait_exponential.__call__', return_value=0.001):
            with self.assertRaises(tenacity.RetryError):
                _fetch_yf_primary("AAPL", "2023-01-01")
        self.assertEqual(mock_yf.call_count, 3)

    @patch('run_pipeline.yf.download')
    def test_fetch_yf_primary_success_on_3rd_attempt(self, mock_yf):
        """_fetch_yf_primary should succeed on 3rd attempt after 2 initial HTTP 429 failures."""
        valid_df = pd.DataFrame({'Close': [150.0]}, index=pd.date_range('2023-01-01', periods=1))
        mock_yf.side_effect = [
            requests.exceptions.HTTPError("429 Too Many Requests"),
            requests.exceptions.ReadTimeout("Read timeout"),
            valid_df
        ]
        with patch('tenacity.wait_exponential.__call__', return_value=0.001):
            res = _fetch_yf_primary("AAPL", "2023-01-01")
        self.assertFalse(res.empty)
        self.assertEqual(res.iloc[0]['Close'], 150.0)
        self.assertEqual(mock_yf.call_count, 3)

    # -------------------------------------------------------------------------
    # 2. Test MarketDataHandler retries (_fetch_yf_with_retry & _fetch_historical_yf_with_retry)
    # -------------------------------------------------------------------------

    @patch('src.data_layer.market_data_handler.yf.Ticker')
    def test_market_data_handler_historical_http_429_retries(self, mock_ticker_cls):
        """_fetch_historical_yf_with_retry should retry 3 times on HTTP 429 error before raising."""
        mock_ticker = MagicMock()
        mock_ticker.history.side_effect = requests.exceptions.HTTPError("429 Too Many Requests")
        mock_ticker_cls.return_value = mock_ticker

        with patch('tenacity.wait_exponential.__call__', return_value=0.001):
            with self.assertRaises(requests.exceptions.HTTPError):
                self.handler._fetch_historical_yf_with_retry("AAPL", start_date="2023-01-01")

        self.assertEqual(mock_ticker.history.call_count, 3)

    @patch('src.data_layer.market_data_handler.yf.Ticker')
    def test_market_data_handler_historical_timeout_retries(self, mock_ticker_cls):
        """_fetch_historical_yf_with_retry should retry 3 times on ReadTimeout before raising."""
        mock_ticker = MagicMock()
        mock_ticker.history.side_effect = requests.exceptions.ReadTimeout("Read timed out")
        mock_ticker_cls.return_value = mock_ticker

        with patch('tenacity.wait_exponential.__call__', return_value=0.001):
            with self.assertRaises(requests.exceptions.ReadTimeout):
                self.handler._fetch_historical_yf_with_retry("AAPL", start_date="2023-01-01")

        self.assertEqual(mock_ticker.history.call_count, 3)

    # -------------------------------------------------------------------------
    # 3. Test batch recovery retry & backoff behavior in prefetch_prices_batch
    # -------------------------------------------------------------------------

    @patch('run_pipeline.yf.download')
    @patch('run_pipeline.time.sleep')
    def test_batch_recovery_backoff_on_http_429(self, mock_sleep, mock_yf):
        """Batch download should attempt retries with exponential backoff on HTTP 429 before splitting."""
        mock_db = MagicMock()
        mock_db.needs_update.return_value = True
        mock_db.get_latest_date.return_value = "2023-01-01"

        # Simulate 2 batch tickers
        symbols = ["AAPL", "MSFT"]
        symbol_market = {"AAPL": "SP500", "MSFT": "SP500"}

        # HTTP 429 on all attempts for full batch, then single-ticker attempts also fail after retries
        mock_yf.side_effect = requests.exceptions.HTTPError("429 Client Error: Too Many Requests")

        prefetch_prices_batch(symbols, symbol_market, "2023-01-01", price_db=mock_db)

        self.assertEqual(mock_yf.call_count, 9)

        # Verify backoff sleep was executed (2.0s and 4.0s for each 3-attempt cycle)
        sleep_args = [c[0][0] for c in mock_sleep.call_args_list]
        self.assertIn(2.0, sleep_args)
        self.assertIn(4.0, sleep_args)

    @patch('run_pipeline.yf.download')
    @patch('run_pipeline.time.sleep')
    def test_batch_recovery_succeeds_on_retry_backoff(self, mock_sleep, mock_yf):
        """Batch download should succeed on retry attempt 2 after HTTP 429 on attempt 1, without binary split."""
        mock_db = MagicMock()
        mock_db.needs_update.return_value = True
        mock_db.get_latest_date.return_value = "2023-01-01"

        # Create multi-index DataFrame response simulating 2 tickers
        index = pd.date_range('2023-01-01', periods=2)
        cols = pd.MultiIndex.from_tuples([
            ('Close', 'AAPL'), ('Close', 'MSFT'),
            ('Open', 'AAPL'), ('Open', 'MSFT'),
            ('High', 'AAPL'), ('High', 'MSFT'),
            ('Low', 'AAPL'), ('Low', 'MSFT'),
            ('Volume', 'AAPL'), ('Volume', 'MSFT')
        ])
        valid_batch_df = pd.DataFrame(100.0, index=index, columns=cols)

        # Attempt 1: HTTP 429, Attempt 2: valid_batch_df
        mock_yf.side_effect = [
            requests.exceptions.HTTPError("429 Too Many Requests"),
            valid_batch_df
        ]

        symbols = ["AAPL", "MSFT"]
        symbol_market = {"AAPL": "SP500", "MSFT": "SP500"}

        count = prefetch_prices_batch(symbols, symbol_market, "2023-01-01", price_db=mock_db)

        # Should attempt download twice for the batch, sleeping 2.0s after attempt 1
        self.assertEqual(mock_yf.call_count, 2)
        sleep_args = [c[0][0] for c in mock_sleep.call_args_list]
        self.assertIn(2.0, sleep_args)
        # Should update price_db for both symbols
        self.assertEqual(mock_db.update_prices.call_count, 2)
        self.assertEqual(count, 2)


if __name__ == '__main__':
    unittest.main()
