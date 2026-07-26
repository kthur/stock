from pathlib import Path

path = Path(r"d:\Finance\code\stock\trading_system\tests\test_tuning_and_retry.py")

target = """    @patch('FinanceDataReader.DataReader')
    def test_fetch_data_fdr_retry_success(self, mock_fdr):
        \"\"\"Verify that fetch_data_fdr retries on exception and returns correct result on eventual success.\"\"\"
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
        \"\"\"Verify that fetch_data_fdr retries up to max limit and resumes gracefully returning None.\"\"\"
        mock_fdr.side_effect = Exception("Permanent network error")

        with patch('tenacity.wait_exponential.__call__', return_value=0.01):
            result = fetch_data_fdr("AAPL", "SP500", "2023-01-01", price_db=None, freshness_days=7)

        self.assertNull_or_None = result is None
        self.assertTrue(self.assertNull_or_None)
        # Should call 3 times (1 initial + 2 retries)
        self.assertEqual(mock_fdr.call_count, 3)"""

replacement = """    @patch('yfinance.download')
    @patch('FinanceDataReader.DataReader')
    def test_fetch_data_fdr_retry_success(self, mock_fdr, mock_yf):
        \"\"\"Verify that fetch_data_fdr retries on exception and returns correct result on eventual success.\"\"\"
        # Tier 1 (yfinance) fails or returns empty, triggering Tier 2 (FDR) fallback
        mock_yf.side_effect = Exception("yfinance network error")
        mock_df = pd.DataFrame({'Open': [100], 'High': [105], 'Low': [95], 'Close': [102], 'Volume': [1000]}, index=pd.date_range('2023-01-01', periods=1))
        mock_fdr.side_effect = [Exception("Network error 1"), Exception("Network error 2"), mock_df]

        # Temporarily speed up retry wait for tests
        with patch('tenacity.wait_exponential.__call__', return_value=0.01):
            result = fetch_data_fdr("AAPL", "SP500", "2023-01-01", price_db=None, freshness_days=7)

        self.assertIsNotNone(result)
        self.assertEqual(mock_fdr.call_count, 3)
        self.assertEqual(result.iloc[0]['Close'], 102)

    @patch('yfinance.download')
    @patch('FinanceDataReader.DataReader')
    def test_fetch_data_fdr_max_retries_fail(self, mock_fdr, mock_yf):
        \"\"\"Verify that fetch_data_fdr retries up to max limit and resumes gracefully returning None.\"\"\"
        mock_yf.side_effect = Exception("yfinance network error")
        mock_fdr.side_effect = Exception("Permanent network error")

        with patch('tenacity.wait_exponential.__call__', return_value=0.01):
            result = fetch_data_fdr("AAPL", "SP500", "2023-01-01", price_db=None, freshness_days=7)

        self.assertNull_or_None = result is None
        self.assertTrue(self.assertNull_or_None)
        # Should call 3 times (1 initial + 2 retries)
        self.assertEqual(mock_fdr.call_count, 3)"""

with open(path, "r+", encoding="utf-8") as f:
    content = f.read()
    assert target in content, "Target pattern not found in test_tuning_and_retry.py"
    new_content = content.replace(target, replacement, 1)
    f.seek(0)
    f.write(new_content)
    f.truncate()

print("Successfully updated test_tuning_and_retry.py")
