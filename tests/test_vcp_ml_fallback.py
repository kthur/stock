import unittest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "trading_system"))

import pandas as pd
import numpy as np
from tempfile import TemporaryDirectory
from src.ai.vcp_ml_predictor import VCPSurgePredictor, SURGE_HORIZONS

class TestVCPSurgePredictorFallbackAndPipeline(unittest.TestCase):
    def test_predict_fallback_when_no_models(self):
        with TemporaryDirectory() as tmp_dir:
            predictor = VCPSurgePredictor(model_dir=tmp_dir)
            predictor.load_models()
            self.assertEqual(len(predictor.models), 0)
            self.assertEqual(len(predictor.lgb_models), 0)
            self.assertEqual(len(predictor.cat_models), 0)

            # Create dummy price data for a symbol
            dates = pd.date_range(end='2026-08-17', periods=100, freq='D')
            prices = pd.DataFrame({
                'Open': np.linspace(100, 110, 100),
                'High': np.linspace(102, 112, 100),
                'Low': np.linspace(99, 109, 100),
                'Close': np.linspace(101, 111, 100),
                'Volume': np.random.randint(1000, 5000, 100),
            }, index=dates)

            prices_dict = {'TEST_SYM': prices}
            universe = pd.DataFrame([{'symbol': 'TEST_SYM', 'name': 'Test Stock', 'market': 'SP500'}])

            # Predict without trained models on disk -> should trigger heuristic fallback instead of empty DataFrame
            preds = predictor.predict(prices_dict, indicator_df=pd.DataFrame(), universe=universe)
            self.assertFalse(preds.empty)
            self.assertIn('symbol', preds.columns)
            self.assertIn('market', preds.columns)
            self.assertEqual(preds.iloc[0]['symbol'], 'TEST_SYM')
            for h in SURGE_HORIZONS:
                self.assertIn(f'vcp_{h}d', preds.columns)
                val = preds.iloc[0][f'vcp_{h}d']
                self.assertGreaterEqual(val, 0.0)
                self.assertLessEqual(val, 1.0)

if __name__ == '__main__':
    unittest.main()
