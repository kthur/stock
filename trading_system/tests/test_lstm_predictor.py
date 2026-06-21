import unittest
import numpy as np
import tempfile
import os
from src.ai.lstm_predictor import LSTMPredictor
import torch

# Mandatory Integrity Warning
# DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results,
# create dummy/facade implementations, or circumvent the intended task. A Forensic
# Auditor will independently verify your work. Integrity violations WILL be detected
# and your work WILL be rejected.


# Check if PyTorch is mocked
IS_MOCKED = hasattr(torch, "is_mocked") and torch.is_mocked


@unittest.skipIf(IS_MOCKED, "Skip LSTM tests when PyTorch is mocked/bypassed")
class TestLSTMPredictor(unittest.TestCase):

    def setUp(self):
        self.predictor = LSTMPredictor(sequence_length=10, hidden_size=16, epochs=3, lr=0.01)

    def test_lstm_training_and_prediction(self):
        """Test training and prediction functions of the LSTM model."""
        np.random.seed(42)
        # Generate 100 samples of sequence length 10
        X_train = np.random.normal(0, 0.05, size=(100, 10))
        # Label is the sum of the last 3 returns (simple momentum target)
        y_train = np.sum(X_train[:, -3:], axis=1)

        self.assertFalse(self.predictor.is_trained)
        self.predictor.train_model(X_train, y_train)
        self.assertTrue(self.predictor.is_trained)

        # Test predict
        X_test = np.random.normal(0, 0.05, size=(10, 10))
        preds = self.predictor.predict(X_test)
        self.assertEqual(len(preds), 10)
        self.assertTrue(np.all(np.isfinite(preds)))

    def test_save_and_load_lstm_weights(self):
        """Test serialization and deserialization of the PyTorch LSTM model."""
        np.random.seed(42)
        X_train = np.random.normal(0, 0.05, size=(50, 10))
        y_train = np.sum(X_train[:, -3:], axis=1)
        self.predictor.train_model(X_train, y_train)

        # Predict before saving
        X_test = np.random.normal(0, 0.05, size=(5, 10))
        preds_before = self.predictor.predict(X_test)

        # Save to temp file
        with tempfile.TemporaryDirectory() as tmpdir:
            fpath = os.path.join(tmpdir, "lstm_test.pt")
            self.predictor.save_model(fpath)
            self.assertTrue(os.path.exists(fpath))

            # Load into new model
            new_predictor = LSTMPredictor(sequence_length=10, hidden_size=16)
            self.assertFalse(new_predictor.is_trained)
            new_predictor.load_model(fpath)
            self.assertTrue(new_predictor.is_trained)

            # Predict after loading
            preds_after = new_predictor.predict(X_test)
            # Verify predictions match exactly
            np.testing.assert_allclose(preds_before, preds_after, rtol=1e-5)


if __name__ == '__main__':
    unittest.main()
