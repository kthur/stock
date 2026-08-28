# -*- coding: utf-8 -*-
"""
Unit tests for TimeSeriesPatchTransformer and PatchTransformerPredictor.
"""

import os
import tempfile
import unittest
import numpy as np
import torch

try:
    from trading_system.src.ai.transformer_predictor import TimeSeriesPatchTransformer, PatchTransformerPredictor
except ImportError:
    from src.ai.transformer_predictor import TimeSeriesPatchTransformer, PatchTransformerPredictor


class TestTransformerPredictor(unittest.TestCase):

    def test_model_forward_shape(self):
        batch_size = 8
        seq_len = 30
        in_features = 1
        macro_dim = 4
        horizons = (1, 5, 20, 60)

        model = TimeSeriesPatchTransformer(
            in_features=in_features,
            macro_features=macro_dim,
            d_model=32,
            nhead=2,
            num_layers=1,
            horizons=horizons,
            patch_size=5,
            stride=2
        )

        x = torch.randn(batch_size, seq_len, in_features)
        macro_x = torch.randn(batch_size, macro_dim)

        outputs = model(x, macro_x)
        self.assertIsInstance(outputs, dict)
        for h in horizons:
            self.assertIn(h, outputs)
            self.assertEqual(outputs[h].shape, (batch_size,))

    def test_predictor_train_and_predict(self):
        N = 40
        seq_len = 25
        in_features = 1
        horizons = (1, 5, 20)

        X = np.random.randn(N, seq_len, in_features).astype(np.float32)
        y_dict = {
            1: np.random.randn(N).astype(np.float32) * 0.02,
            5: np.random.randn(N).astype(np.float32) * 0.05,
            20: np.random.randn(N).astype(np.float32) * 0.10,
        }
        macro_X = np.random.randn(N, 4).astype(np.float32)

        predictor = PatchTransformerPredictor(
            horizons=horizons,
            seq_len=seq_len,
            d_model=16,
            nhead=2,
            num_layers=1,
            epochs=2,
            batch_size=16
        )

        history = predictor.train(X, y_dict, macro_X=macro_X, val_split=0.2)
        self.assertIn('train_loss', history)
        self.assertTrue(len(history['train_loss']) > 0)
        self.assertTrue(predictor.is_fitted)

        preds = predictor.predict(X[:5], macro_X=macro_X[:5])
        for h in horizons:
            self.assertIn(h, preds)
            self.assertEqual(len(preds[h]), 5)
            self.assertTrue(np.all(np.isfinite(preds[h])))

    def test_save_and_load(self):
        N = 30
        seq_len = 20
        in_features = 1
        horizons = (1, 5)

        X = np.random.randn(N, seq_len, in_features).astype(np.float32)
        y_dict = {1: np.random.randn(N).astype(np.float32), 5: np.random.randn(N).astype(np.float32)}

        predictor = PatchTransformerPredictor(
            horizons=horizons,
            seq_len=seq_len,
            d_model=16,
            nhead=2,
            num_layers=1,
            epochs=1,
            batch_size=16
        )
        predictor.train(X, y_dict)

        with tempfile.NamedTemporaryFile(suffix='.pt', delete=False) as tmp:
            tmp_path = tmp.name

        try:
            predictor.save(tmp_path)
            self.assertTrue(os.path.exists(tmp_path))

            loaded_predictor = PatchTransformerPredictor(horizons=horizons)
            success = loaded_predictor.load(tmp_path)
            self.assertTrue(success)
            self.assertTrue(loaded_predictor.is_fitted)

            loaded_preds = loaded_predictor.predict(X[:3])
            self.assertEqual(len(loaded_preds[1]), 3)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)


if __name__ == '__main__':
    unittest.main()
