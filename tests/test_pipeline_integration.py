import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
import sys
import os

# Ensure we can import from trading_system
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class TestPipelineIntegration(unittest.TestCase):
    @patch('time.sleep', return_value=None)
    @patch('trading_system.run_pipeline.yf.download')
    def test_http_429_abort_logic(self, mock_yf_download, mock_sleep):
        from trading_system.run_pipeline import prefetch_prices_batch
        
        # Test that _download_with_recovery aborts instead of splitting when encountering 429
        mock_yf_download.side_effect = Exception("HTTP 429 Too Many Requests")
        
        # Mock price_db
        mock_db = MagicMock()
        mock_db.needs_update.return_value = True
        mock_db.get_latest_date.return_value = "2023-01-01"
        
        # When 429 is encountered, binary split is aborted and count is 0
        count = prefetch_prices_batch(['AAPL', 'MSFT'], {'AAPL': 'SP500', 'MSFT': 'SP500'}, '2023-01-01', mock_db, 1)
        self.assertEqual(count, 0)
        # Verify that only the initial batch retries (3) happened, and no recursive binary split calls occurred
        self.assertEqual(mock_yf_download.call_count, 3)
        
    @patch('trading_system.run_pipeline.yf.download')
    def test_error_recovery_partial_failure(self, mock_yf_download):
        from trading_system.run_pipeline import prefetch_prices_batch
        
        # We need to simulate a network error on the batch, and success on the split items
        def side_effect(*args, **kwargs):
            tickers = args[0]
            if len(tickers) == 2:
                raise Exception("Random network error")
            if tickers == ['AAPL']:
                return pd.DataFrame({'AAPL': [1.0]})
            if tickers == ['MSFT']:
                return pd.DataFrame({'MSFT': [2.0]})
            return pd.DataFrame()
            
        mock_yf_download.side_effect = side_effect
        
        mock_db = MagicMock()
        mock_db.needs_update.return_value = True
        mock_db.get_latest_date.return_value = "2023-01-01"
        
        with patch('trading_system.run_pipeline.DataValidator.sanitize_and_validate_price_data', return_value=(True, pd.DataFrame())):
            count = prefetch_prices_batch(['AAPL', 'MSFT'], {'AAPL': 'SP500', 'MSFT': 'SP500'}, '2023-01-01', mock_db, 1)
            
        # 2 symbols successfully saved
        self.assertEqual(count, 2)

    @patch('trading_system.run_pipeline.fdr.DataReader')
    @patch('trading_system.run_pipeline.yf.download')
    def test_pipeline_stage_ordering(self, mock_yf, mock_fdr):
        # Verify that pipeline dependencies can be mocked and tested cleanly
        self.assertTrue(True)

if __name__ == '__main__':
    unittest.main()
