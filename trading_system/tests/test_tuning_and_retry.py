import sys
import json
import time
import shutil
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
import pandas as pd

# Add trading_system and src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ai.prediction_model import OnDevicePredictionModel
from src.ai.vcp_ml_predictor import VCPSurgePredictor
from scripts.tune_models import tune_hyperparameters
from run_pipeline import fetch_data_fdr, _download_indicator_network
from src.data_layer.earnings_data import fetch_fundamentals
from src.utils.rate_limiter import get_global_rate_limiter


class TestTuningAndRetry(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.model_dir = Path(self.temp_dir) / "models"
        self.model_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_optuna_tuning_runs_and_saves_params(self):
        """Verify that Optuna tuning script runs, saves tuned_params.json, and OnDevicePredictionModel loads them."""
        # Run tuning with small trials
        tune_hyperparameters(n_trials=2, output_dir=str(self.model_dir))

        # Verify JSON file exists
        json_path = self.model_dir / "tuned_params.json"
        self.assertTrue(json_path.exists())

        # Load and verify structure
        with open(json_path, 'r') as f:
            data = json.load(f)

        for key in ['xgb', 'lgb', 'cat', 'surge_xgb', 'surge_lgb', 'surge_cat']:
            self.assertIn(key, data)
            self.assertIsInstance(data[key], dict)

        # Verify OnDevicePredictionModel loads them
        model = OnDevicePredictionModel(model_dir=str(self.model_dir))

        # Spot check that model parameters match json parameters
        for key in data['xgb']:
            self.assertEqual(model._xgb_kwargs[key], data['xgb'][key])

        for key in data['surge_xgb']:
            self.assertEqual(model._surge_xgb_kwargs[key], data['surge_xgb'][key])

        # Verify VCPSurgePredictor loads them
        vcp_predictor = VCPSurgePredictor(model_dir=str(self.model_dir))
        for key in data['surge_xgb']:
            self.assertEqual(vcp_predictor._surge_xgb_kwargs[key], data['surge_xgb'][key])

    @patch('FinanceDataReader.DataReader')
    def test_fetch_data_fdr_retry_success(self, mock_fdr):
        """Verify that fetch_data_fdr retries on exception and returns correct result on eventual success."""
        # Configure mock to raise exceptions twice and then return a valid DataFrame
        mock_df = pd.DataFrame({'Open': [100], 'High': [105], 'Low': [95], 'Close': [102], 'Volume': [1000]}, index=pd.date_range('2023-01-01', periods=1))
        mock_fdr.side_effect = [Exception("Network error 1"), Exception("Network error 2"), mock_df]

        # Temporarily speed up retry wait for tests
        with patch('tenacity.wait_exponential.__call__', return_value=0.01):
            result = fetch_data_fdr("AAPL", "SP500", "2023-01-01", price_db=None, freshness_days=7)

        self.assertIsNotNone(result)
        self.assertEqual(mock_fdr.call_count, 3)
        self.assertEqual(result.iloc[0]['Close'], 102)

    @patch('FinanceDataReader.DataReader')
    def test_fetch_data_fdr_max_retries_fail(self, mock_fdr):
        """Verify that fetch_data_fdr retries up to max limit and resumes gracefully returning None."""
        mock_fdr.side_effect = Exception("Permanent network error")

        with patch('tenacity.wait_exponential.__call__', return_value=0.01):
            result = fetch_data_fdr("AAPL", "SP500", "2023-01-01", price_db=None, freshness_days=7)

        self.assertNull_or_None = result is None
        self.assertTrue(self.assertNull_or_None)
        # Should call 3 times (1 initial + 2 retries)
        self.assertEqual(mock_fdr.call_count, 3)

    @patch('yfinance.download')
    def test_fetch_indicator_history_retry(self, mock_yf):
        """Verify that fetch_indicator_history retries on failure when downloading indicators."""
        mock_df = pd.DataFrame({'Open': [100], 'High': [105], 'Low': [95], 'Close': [102], 'Volume': [1000]}, index=pd.date_range('2023-01-01', periods=1))
        mock_yf.side_effect = [Exception("Rate limit"), mock_df]

        with patch('tenacity.wait_exponential.__call__', return_value=0.01):
            result = _download_indicator_network("^VIX", "2023-01-01")

        self.assertIsNotNone(result)
        self.assertEqual(mock_yf.call_count, 2)

    @patch('yfinance.Ticker')
    def test_fetch_fundamentals_retry(self, mock_ticker_class):
        """Verify that fetch_fundamentals retries on empty financials and returns None after max attempts."""
        mock_ticker = MagicMock()
        mock_ticker.financials = pd.DataFrame()  # Empty financials triggers retry
        mock_ticker_class.return_value = mock_ticker

        with patch('tenacity.wait_exponential.__call__', return_value=0.01):
            result = fetch_fundamentals("005930", "KOSPI")

        self.assertIsNone(result)
        # 3 calls total
        self.assertEqual(mock_ticker_class.call_count, 3)

    def test_global_rate_limiter_coordination(self):
        """Verify that get_global_rate_limiter correctly spaces out concurrent requests."""
        limiter = get_global_rate_limiter()
        original_interval = limiter.min_interval
        limiter.min_interval = 0.2  # Use short interval for testing

        times = []
        def task():
            limiter.wait()
            times.append(time.time())

        threads = [threading.Thread(target=task) for _ in range(3)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Restore original interval
        limiter.min_interval = original_interval

        times.sort()
        # Verify that time diff between consecutive calls is at least 0.18 seconds (with some scheduling allowance)
        diff1 = times[1] - times[0]
        diff2 = times[2] - times[1]

        self.assertGreaterEqual(diff1, 0.15)
        self.assertGreaterEqual(diff2, 0.15)


if __name__ == '__main__':
    unittest.main()
