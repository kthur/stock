import unittest
import numpy as np
import pandas as pd
import threading
from concurrent.futures import ThreadPoolExecutor

from src.risk.risk_manager import CrisisDetector, CrisisLevel
from src.ai.optuna_tuner import OptunaStrategyTuner
from src.data_layer.indicator_storage import MarketIndicatorStorage


class TestSprint4OpsTuning(unittest.TestCase):
    """Unit and Integration Tests for Sprint 4 Operations, HPO, and Gating."""

    def test_continuous_sigmoid_crisis_gating(self):
        """Verify smooth continuous sigmoid crisis gating eliminates discrete liquidation cliffs."""
        detector = CrisisDetector()

        # Test varying composite scores from 0.0 (calm) to 1.0 (crisis)
        mult_calm = detector.get_smooth_crisis_position_multiplier(composite_score=0.10)
        mult_moderate = detector.get_smooth_crisis_position_multiplier(composite_score=0.45)
        mult_severe = detector.get_smooth_crisis_position_multiplier(composite_score=0.85)

        # 1. Monotonically decreasing
        self.assertGreater(mult_calm, mult_moderate)
        self.assertGreater(mult_moderate, mult_severe)

        # 2. Smooth bounds
        self.assertLessEqual(mult_calm, 1.0)
        self.assertGreaterEqual(mult_severe, 0.15)

        # 3. No abrupt step cliff between 0.44 and 0.46
        m_44 = detector.get_smooth_crisis_position_multiplier(composite_score=0.44)
        m_46 = detector.get_smooth_crisis_position_multiplier(composite_score=0.46)
        self.assertLess(abs(m_44 - m_46), 0.10)  # Smooth delta, not 30% jump

        # 4. Smooth cash target
        cash_calm = detector.get_smooth_crisis_cash_target(composite_score=0.10)
        cash_severe = detector.get_smooth_crisis_cash_target(composite_score=0.85)
        self.assertLess(cash_calm, cash_severe)

    def test_deflated_sharpe_ratio_computation(self):
        """Verify Deflated Sharpe Ratio (DSR) penalizes selection bias under multiple trials."""
        np.random.seed(42)
        # Moderate Sharpe ratio series
        rets_series = pd.Series(np.random.normal(0.0008, 0.015, size=200))

        dsr_few_trials = OptunaStrategyTuner.compute_deflated_sharpe_ratio(rets_series, n_trials=5)
        dsr_many_trials = OptunaStrategyTuner.compute_deflated_sharpe_ratio(rets_series, n_trials=500)

        # DSR should be lower (more heavily penalized) when evaluated under 500 trials than 5 trials
        self.assertGreater(dsr_few_trials, dsr_many_trials)
        self.assertTrue(0.0 < dsr_few_trials < 1.0)
        self.assertTrue(0.0 < dsr_many_trials < 1.0)

    def test_optuna_softmax_regime_weights_tuning(self):
        """Verify tune_regime_2d_weights produces valid simplex weights using Softmax parameterization."""
        tuner = OptunaStrategyTuner()
        np.random.seed(42)

        strategy_returns = {
            'BULL_LOW_VOL': {
                'regression': pd.Series(np.random.normal(0.001, 0.01, 30)),
                'surge': pd.Series(np.random.normal(0.0015, 0.02, 30)),
                'vcp_ml': pd.Series(np.random.normal(0.0012, 0.018, 30)),
            }
        }

        tuned = tuner.tune_regime_2d_weights(strategy_returns, n_trials=5)
        bull_weights = tuned['BULL_LOW_VOL']

        self.assertAlmostEqual(sum(bull_weights.values()), 1.0, places=3)
        for s, w in bull_weights.items():
            self.assertGreater(w, 0.0)

    def test_thread_local_connection_pooling_concurrency(self, tmp_path_factory=None):
        """Verify MarketIndicatorStorage thread-local connections execute concurrently without locking stalls."""
        import tempfile
        import os
        tmp_dir = tempfile.mkdtemp()
        db_file = os.path.join(tmp_dir, "test_thread_local.db")
        storage = MarketIndicatorStorage(db_path=db_file)

        def worker_task(thread_id: int):
            df = pd.DataFrame({'Close': [100.0 + thread_id]}, index=pd.date_range('2026-01-01', periods=1))
            storage.save_indicators('VIX', df)
            latest = storage.get_latest_global_indicators()
            return latest

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(worker_task, i) for i in range(8)]
            results = [f.result() for f in futures]

        self.assertEqual(len(results), 8)
        storage.checkpoint_wal()


if __name__ == "__main__":
    unittest.main()
