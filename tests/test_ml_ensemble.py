import sys
import unittest
from unittest.mock import patch
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.analysis.ml_engine import MLEngine, HAS_SKLEARN, HAS_XGBOOST, HAS_OPTUNA

class MockPriceBar:
    def __init__(self, close, high, low, volume):
        self.close = close
        self.high = high
        self.low = low
        self.volume = volume

class TestMLEnsemble(unittest.TestCase):
    """Unit tests for MLEngine model ensemble (RandomForest + XGBoost)"""

    def setUp(self):
        self.engine = MLEngine()

    def generate_dummy_data(self, n_bars=500):
        # Generate dummy price bars with some volatility to trigger targets
        bars = []
        curr_close = 100.0
        np.random.seed(42)

        for i in range(n_bars):
            # Alternate up and down to create enough targets
            change = 0.015 if i % 2 == 0 else -0.015
            curr_close = curr_close * (1.0 + change)
            bars.append(MockPriceBar(
                close=curr_close,
                high=curr_close * 1.01,
                low=curr_close * 0.99,
                volume=1000 + (i % 5) * 500
            ))
        return bars

    def test_ensemble_initialization(self):
        """Test that ensemble is correctly initialized when both sklearn and xgboost are available"""
        if HAS_SKLEARN and HAS_XGBOOST:
            self.assertIsNotNone(self.engine.rf_model)
            self.assertIsNotNone(self.engine.xgb_model)
            self.assertIsInstance(self.engine.model, tuple)
            self.assertEqual(len(self.engine.model), 2)
        else:
            # Fallback checks
            self.assertTrue(self.engine.rf_model is None or self.engine.xgb_model is None)

    def test_train_and_predict(self):
        """Test that train and predict run successfully and predict a valid probability"""
        bars = self.generate_dummy_data(500)

        # Verify training returns True
        train_success = self.engine.train(bars)
        self.assertTrue(train_success, "Training should be successful with sufficient data")

        # Verify predict_prob returns a valid probability between 0.0 and 1.0
        prob = self.engine.predict_prob(bars)
        self.assertIsInstance(prob, float)
        self.assertGreaterEqual(prob, 0.0)
        self.assertLessEqual(prob, 1.0)

    def test_fallback_logic_only_rf(self):
        """Test fallback behavior when only sklearn is available"""
        with patch('src.analysis.ml_engine.HAS_XGBOOST', False), \
             patch('src.analysis.ml_engine.HAS_LIGHTGBM', False), \
             patch('src.analysis.ml_engine.HAS_SKLEARN', True):
            engine = MLEngine()
            self.assertIsNotNone(engine.rf_model)
            self.assertIsNone(engine.xgb_model)

            bars = self.generate_dummy_data(500)
            train_success = engine.train(bars)
            self.assertTrue(train_success)
            prob = engine.predict_prob(bars)
            self.assertGreaterEqual(prob, 0.0)
            self.assertLessEqual(prob, 1.0)

    def test_fallback_logic_only_xgb(self):
        """Test fallback behavior when only xgboost is available"""
        with patch('src.analysis.ml_engine.HAS_XGBOOST', True), \
             patch('src.analysis.ml_engine.HAS_LIGHTGBM', False), \
             patch('src.analysis.ml_engine.HAS_SKLEARN', False):
            engine = MLEngine()
            self.assertIsNone(engine.rf_model)
            self.assertIsNotNone(engine.xgb_model)

            bars = self.generate_dummy_data(500)
            train_success = engine.train(bars)
            self.assertTrue(train_success)
            prob = engine.predict_prob(bars)
            self.assertGreaterEqual(prob, 0.0)
            self.assertLessEqual(prob, 1.0)

    def test_optimize_hyperparameters(self):
        """Test hyperparameter optimization if Optuna is available"""
        if HAS_OPTUNA and HAS_SKLEARN:
            bars = self.generate_dummy_data(500)
            best_params = self.engine.optimize_hyperparameters(bars, n_trials=3)
            self.assertIsNotNone(best_params)
            self.assertIn('n_estimators', best_params)
            self.assertIn('max_depth', best_params)

if __name__ == "__main__":
    unittest.main(verbosity=2)
