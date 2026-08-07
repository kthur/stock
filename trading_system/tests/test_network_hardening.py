import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from run_pipeline import (
    _fetch_yf_primary,
    _fetch_data_fdr_network,
    prefetch_prices_batch,
    is_empty_result
)
from src.data_layer.market_data_handler import MarketDataHandler, CircuitBreakerOpenException


class TestNetworkHardening(unittest.TestCase):
    def setUp(self):
        self.handler = MarketDataHandler()

    @patch('run_pipeline.yf.download')
    def test_fetch_yf_primary_retries_on_exception_and_succeeds(self, mock_yf):
        """_fetch_yf_primary should retry on transient exception and return data when it succeeds."""
        mock_df = pd.DataFrame({'Close': [100.0]}, index=pd.date_range('2023-01-01', periods=1))
        mock_yf.side_effect = [Exception("Transient ConnectionError"), mock_df]

        with patch('tenacity.wait_exponential.__call__', return_value=0.001):
            res = _fetch_yf_primary("AAPL", "2023-01-01")

        self.assertFalse(res.empty)
        self.assertEqual(res.iloc[0]['Close'], 100.0)
        self.assertEqual(mock_yf.call_count, 2)

    @patch('run_pipeline.yf.download')
    def test_fetch_yf_primary_retries_on_empty_result(self, mock_yf):
        """_fetch_yf_primary should retry when yf.download returns an empty DataFrame."""
        empty_df = pd.DataFrame()
        valid_df = pd.DataFrame({'Close': [150.0]}, index=pd.date_range('2023-01-01', periods=1))
        mock_yf.side_effect = [empty_df, valid_df]

        with patch('tenacity.wait_exponential.__call__', return_value=0.001):
            res = _fetch_yf_primary("AAPL", "2023-01-01")

        self.assertFalse(res.empty)
        self.assertEqual(res.iloc[0]['Close'], 150.0)
        self.assertEqual(mock_yf.call_count, 2)

    @patch('run_pipeline._fetch_yf_primary')
    @patch('run_pipeline.fdr.DataReader')
    def test_fetch_data_fdr_network_fallback_to_tier2_after_tier1_exhaustion(self, mock_fdr, mock_tier1):
        """_fetch_data_fdr_network should attempt Tier 1 first and fall back to Tier 2 only if Tier 1 fails."""
        mock_tier1.side_effect = Exception("Tier 1 retries exhausted")
        fdr_df = pd.DataFrame({'Close': [200.0]}, index=pd.date_range('2023-01-01', periods=1))
        mock_fdr.return_value = fdr_df

        res = _fetch_data_fdr_network("005930", "KOSPI", "2023-01-01")

        self.assertFalse(res.empty)
        self.assertEqual(res.iloc[0]['Close'], 200.0)
        self.assertEqual(mock_tier1.call_count, 1)
        self.assertEqual(mock_fdr.call_count, 1)

    @patch('src.data_layer.market_data_handler._fetch_stooq_or_yahoo_direct')
    @patch('src.data_layer.market_data_handler.fdr.DataReader')
    @patch('src.data_layer.market_data_handler.yf.Ticker')
    def test_market_data_handler_historical_retry(self, mock_ticker_cls, mock_fdr, mock_stooq):
        """MarketDataHandler._fetch_historical_yf_with_retry should retry on failure and succeed on retry."""
        mock_ticker = MagicMock()
        empty_df = pd.DataFrame()
        valid_df = pd.DataFrame({
            'Open': [10.0], 'High': [12.0], 'Low': [9.0], 'Close': [11.0], 'Volume': [1000]
        }, index=pd.date_range('2023-01-01', periods=1))
        mock_ticker.history.side_effect = [Exception("yfinance network error"), valid_df]
        mock_ticker_cls.return_value = mock_ticker
        mock_fdr.side_effect = Exception("FDR network error")
        mock_stooq.side_effect = Exception("Stooq network error")

        with patch('time.sleep', return_value=None), patch('tenacity.wait_exponential.__call__', return_value=0.001):
            res = self.handler._fetch_historical_yf_with_retry("AAPL", start_date="2023-01-01")

        self.assertFalse(res.empty)
        self.assertEqual(res.iloc[0]['Close'], 11.0)
        self.assertEqual(mock_ticker.history.call_count, 2)

    @patch('src.data_layer.market_data_handler.yf.Ticker')
    def test_market_data_handler_historical_circuit_breaker_check(self, mock_ticker_cls):
        """When circuit breaker is OPEN, MarketDataHandler should raise CircuitBreakerOpenException immediately without retrying."""
        self.handler.circuit_breaker.is_open = True
        self.handler.circuit_breaker.last_failure_time = 9999999999.0  # open indefinitely

        with self.assertRaises(CircuitBreakerOpenException):
            self.handler._fetch_historical_yf_with_retry("AAPL", start_date="2023-01-01")

        self.assertEqual(mock_ticker_cls.call_count, 0)


if __name__ == '__main__':
    unittest.main()
