import unittest
import numpy as np

from src.ai.lstm_predictor import LSTMPredictor
from src.core.stat_arb import KalmanPairTracker
from src.core.rim_valuation import RIMValuationEngine
from src.data_layer.earnings_data import compute_regulatory_filing_lag


class TestSprint3AlphaRefactor(unittest.TestCase):
    """Unit tests for Sprint 3 Deep Alpha Refactoring across 31 strategies."""

    def test_multivariate_lstm_training_and_inference(self):
        """Verify LSTMPredictor trains and infers on (N, T, D) multivariate sequence tensors."""
        np.random.seed(42)
        N_samples = 40
        seq_len = 10
        num_features = 4  # e.g., Return, Volume, Volatility, OrderFlow

        X_multi = np.random.normal(0, 1, size=(N_samples, seq_len, num_features)).astype(np.float32)
        y_multi = np.random.normal(0.01, 0.02, size=(N_samples, 1)).astype(np.float32)

        predictor = LSTMPredictor(sequence_length=seq_len, input_size=num_features, hidden_size=16, epochs=2)
        predictor.train_model(X_multi, y_multi, val_split=0.1)

        self.assertTrue(predictor.is_trained)

        # Test inference
        test_X = np.random.normal(0, 1, size=(5, seq_len, num_features)).astype(np.float32)
        preds = predictor.predict(test_X)

        self.assertEqual(len(preds), 5)
        self.assertTrue(np.all(np.isfinite(preds)))

    def test_kalman_pair_tracker_online_updates(self):
        """Verify KalmanPairTracker online hedge ratio tracking and structural break detection."""
        tracker = KalmanPairTracker(delta_w=1e-4, v_e=1e-3, break_threshold=3.0)

        # Generate synthetic cointegrated pair with true beta = 1.5
        np.random.seed(42)
        true_beta = 1.5
        true_alpha = 0.5

        for _ in range(50):
            y2_val = float(np.random.uniform(50, 100))
            noise = float(np.random.normal(0, 0.1))
            y1_val = true_alpha + true_beta * y2_val + noise
            res = tracker.update(y1_val, y2_val)

        # 1. Check converged hedge ratio is close to true beta 1.5
        est_beta = tracker.get_current_hedge_ratio()
        self.assertAlmostEqual(est_beta, true_beta, delta=0.25)
        self.assertFalse(res['is_structural_break'])

        # 2. Inject massive structural shock and verify break detection
        shock_y1 = y1_val + 50.0  # +50 huge jump
        shock_res = tracker.update(shock_y1, y2_val)
        self.assertTrue(shock_res['is_structural_break'])
        self.assertGreater(shock_res['innovation_z'], 3.0)

    def test_rim_asset_specific_capm_cost_of_equity(self):
        """Verify RIM derive_required_return scales dynamically with asset beta and size premium."""
        rim = RIMValuationEngine()

        # Benchmark stock (beta=1.0, large cap)
        re_base = rim.derive_required_return(market="KOSPI", us10y_yield=3.5, vix_val=15.0, asset_beta=1.0, is_small_cap=False)

        # High beta speculative stock (beta=1.8, large cap) -> higher cost of equity
        re_high_beta = rim.derive_required_return(market="KOSPI", us10y_yield=3.5, vix_val=15.0, asset_beta=1.8, is_small_cap=False)
        self.assertGreater(re_high_beta, re_base)

        # Small cap stock (beta=1.0, small cap) -> higher cost of equity by +1.0% size premium
        re_small_cap = rim.derive_required_return(market="KOSPI", us10y_yield=3.5, vix_val=15.0, asset_beta=1.0, is_small_cap=True)
        self.assertAlmostEqual(re_small_cap - re_base, 0.010, places=3)

    def test_jurisdiction_aware_filing_lag(self):
        """Verify KRX (45d/90d) and SEC (40d/60d) statutory filing lag compliance."""
        # KRX Q1 (March 31 -> May 15 = 45 days)
        krx_q1 = compute_regulatory_filing_lag("2026-03-31", period_type="quarterly", is_krx=True)
        self.assertEqual(krx_q1, "2026-05-15")

        # KRX Q4 / Annual (Dec 31 -> Mar 31 = 90 days)
        krx_q4 = compute_regulatory_filing_lag("2025-12-31", period_type="quarterly", is_krx=True)
        self.assertEqual(krx_q4, "2026-03-31")

        # SEC 10-Q Q1 (March 31 -> May 10 = 40 days)
        sec_q1 = compute_regulatory_filing_lag("2026-03-31", period_type="quarterly", is_krx=False)
        self.assertEqual(sec_q1, "2026-05-10")

        # SEC 10-K Annual (Dec 31 -> March 1 = 60 days)
        sec_10k = compute_regulatory_filing_lag("2025-12-31", period_type="annual", is_krx=False)
        self.assertEqual(sec_10k, "2026-03-01")


if __name__ == "__main__":
    unittest.main()
