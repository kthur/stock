import unittest
import pandas as pd
import numpy as np
from pathlib import Path
import tempfile
import shutil
from src.ai.prediction_model import OnDevicePredictionModel
from src.config import TradingConfig

class TestLeadLagIndex(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for model savings
        self.test_dir = Path(tempfile.mkdtemp())
        self.config = TradingConfig()
        
        # Instantiate prediction model with a temp directory for saving models
        self.model = OnDevicePredictionModel(model_dir=str(self.test_dir))
        self.model.model_dir = self.test_dir

    def tearDown(self):
        # Cleanup temporary directory
        shutil.rmtree(self.test_dir)

    def test_compute_and_predict_lead_lag_with_indicators(self):
        # 1. Create dummy training data (dates from T0 to T10)
        dates = pd.date_range(start='2026-06-01', periods=15, freq='D')
        
        # Create stock prices train data
        records = []
        for d in dates:
            # Let Stock_A follow ^GSPC with 1-day lag
            # Let Stock_B follow 091160.KS with 1-day lag
            records.append({'date': d, 'symbol': 'Stock_A', 'ret_1d': 0.0, 'market_cap': 1000})
            records.append({'date': d, 'symbol': 'Stock_B', 'ret_1d': 0.0, 'market_cap': 2000})
            records.append({'date': d, 'symbol': 'Stock_C', 'ret_1d': 0.01, 'market_cap': 500})
            
        df_train = pd.DataFrame(records)
        df_train['date'] = pd.to_datetime(df_train['date'])
        
        # Create indicator train data
        indicator_records = []
        for d in dates:
            indicator_records.append({
                'date': d,
                'sp500_change': 0.0,
                'kodex_semicon_change': 0.0,
                'kospi_change': 0.0,
                'kosdaq_change': 0.0,
                'vix_change': 0.0,
                'us10y': 3.5,
                'usdkrw_change': 0.0,
                'dxy_change': 0.0,
                'wti_change': 0.0,
                'put_call_ratio': 0.6
            })
        indicator_df = pd.DataFrame(indicator_records)
        indicator_df['date'] = pd.to_datetime(indicator_df['date'])
        indicator_df = indicator_df.set_index('date')

        # Insert lag-1 relationships (make them distinct for Stock_A and Stock_B)
        # T_i of indicator -> T_i+1 of stock
        for i in range(1, 14):
            if i % 2 == 0:
                # sp500_change leads Stock_A
                indicator_df.iloc[i, indicator_df.columns.get_loc('sp500_change')] = 3.0  # 3.0%
                idx_stock_a = (df_train['date'] == dates[i+1]) & (df_train['symbol'] == 'Stock_A')
                df_train.loc[idx_stock_a, 'ret_1d'] = 0.06  # 6%
            else:
                # kodex_semicon_change leads Stock_B
                indicator_df.iloc[i, indicator_df.columns.get_loc('kodex_semicon_change')] = 4.0  # 4.0%
                idx_stock_b = (df_train['date'] == dates[i+1]) & (df_train['symbol'] == 'Stock_B')
                df_train.loc[idx_stock_b, 'ret_1d'] = 0.08  # 8%

        # 2. Compute Lead-Lag Matrix
        self.model.compute_lead_lag(df_train, indicator_df=indicator_df, lead_lag_days=1)
        
        # Assertions on computation
        self.assertIn('^GSPC', self.model.lead_lag_leaders)
        self.assertIn('091160.KS', self.model.lead_lag_leaders)
        
        # Check followers of ^GSPC (Should have Stock_A with strong correlation)
        gspc_followers = dict(self.model.lead_lag_matrix['^GSPC'])
        self.assertIn('Stock_A', gspc_followers)
        self.assertGreater(gspc_followers['Stock_A'], 0.5)

        # Check followers of 091160.KS (Should have Stock_B with strong correlation)
        semicon_followers = dict(self.model.lead_lag_matrix['091160.KS'])
        self.assertIn('Stock_B', semicon_followers)
        self.assertGreater(semicon_followers['Stock_B'], 0.5)
        
        # Verify that virtual index symbols are NOT followers of other leaders
        for leader, followers in self.model.lead_lag_matrix.items():
            follower_symbols = [f[0] for f in followers]
            self.assertNotIn('^GSPC', follower_symbols)
            self.assertNotIn('091160.KS', follower_symbols)

        # 3. Predict Lead-Lag
        # Construct dummy prices dict for inference
        prices_dict = {
            'Stock_A': pd.DataFrame({'Close': [100.0, 101.0]}, index=dates[-2:]),
            'Stock_B': pd.DataFrame({'Close': [100.0, 101.0]}, index=dates[-2:]),
            'Stock_C': pd.DataFrame({'Close': [100.0, 101.0]}, index=dates[-2:]),
        }
        
        # Case A: Today index change is high (SP500 rose 2.5%)
        indicator_infer_a = pd.DataFrame([{
            'sp500_change': 2.5,
            'kodex_semicon_change': 0.0
        }], index=[dates[-1]])
        indicator_infer_a.index.name = 'date'
        
        res_a = self.model.predict_lead_lag(prices_dict, indicator_df=indicator_infer_a)
        self.assertFalse(res_a.empty)
        
        # Stock_A should have higher score than Stock_B because ^GSPC went up
        scores_a = dict(zip(res_a['symbol'], res_a['lead_lag_score']))
        self.assertIn('Stock_A', scores_a)
        if 'Stock_B' in scores_a:
            self.assertGreater(scores_a['Stock_A'], scores_a['Stock_B'])
            
        # Case B: Semicon ETF change is high (KODEX semicon rose 3.0%)
        indicator_infer_b = pd.DataFrame([{
            'sp500_change': 0.0,
            'kodex_semicon_change': 3.0
        }], index=[dates[-1]])
        indicator_infer_b.index.name = 'date'
        
        res_b = self.model.predict_lead_lag(prices_dict, indicator_df=indicator_infer_b)
        self.assertFalse(res_b.empty)
        
        # Stock_B should have higher score than Stock_A because 091160.KS went up
        scores_b = dict(zip(res_b['symbol'], res_b['lead_lag_score']))
        self.assertIn('Stock_B', scores_b)
        if 'Stock_A' in scores_b:
            self.assertGreater(scores_b['Stock_B'], scores_b['Stock_A'])

if __name__ == '__main__':
    unittest.main()
