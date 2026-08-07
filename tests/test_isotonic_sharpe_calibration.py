import os
import sys
import unittest
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../trading_system')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.ai.ensemble_scorer import EnsembleScoringEngine

# Mandatory Integrity Warning
# DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results,
# create dummy/facade implementations, or circumvent the intended task. A Forensic
# Auditor will independently verify your work. Integrity violations WILL be detected
# and your work WILL be rejected.


class TestIsotonicSharpeCalibration(unittest.TestCase):

    def setUp(self):
        self.engine = EnsembleScoringEngine(alpha_smoothing=0.2)
        self.strategies = [
            'regression', 'surge', 'lead_lag', 'vcp_rule', 'vcp_ml',
            'lstm', 'stat_arb', 'sector_rotation', 'rim_valuation', 'event_driven',
            'mq_factor', 'iv_skew', 'order_flow', 'short_term_reversal',
            'arm_factor', 'card_factor', 'latr_factor', 'inst_foreign_sector',
            'supply_chain', 'sentiment', 'factor_neutralized', 'vol_target', 'microstructure'
        ]

    def test_isotonic_and_platt_fitting_and_prediction(self):
        """Verify hybrid calibration fitting: Isotonic for N >= 50, Platt for 20 <= N < 50, skip for N < 20."""
        np.random.seed(42)

        # 1. N = 100 (Isotonic Regression)
        raw_scores_100 = np.linspace(0.0, 1.0, 100)
        true_labels_100 = (raw_scores_100 + np.random.normal(0, 0.2, 100) > 0.5).astype(float)
        # Ensure binary classes exist
        true_labels_100[0] = 0.0
        true_labels_100[-1] = 1.0

        scores_dict_100 = {'regression': raw_scores_100}
        self.engine.fit_calibrators(scores_dict_100, true_labels_100)

        self.assertTrue(self.engine.has_calibrators())
        cal_type, _ = self.engine._calibrators['regression']
        self.assertEqual(cal_type, 'isotonic')

        calibrated_100 = self.engine.calibrate_scores('regression', raw_scores_100)
        self.assertEqual(len(calibrated_100), 100)
        self.assertTrue(np.all(calibrated_100 >= 0.0))
        self.assertTrue(np.all(calibrated_100 <= 1.0))
        # Monotonicity check for Isotonic Regression
        diffs = np.diff(calibrated_100)
        self.assertTrue(np.all(diffs >= -1e-6))

        # 2. N = 30 (Platt Scaling via LogisticRegression)
        engine_platt = EnsembleScoringEngine()
        raw_scores_30 = np.linspace(0.1, 0.9, 30)
        true_labels_30 = (raw_scores_30 > 0.5).astype(float)

        scores_dict_30 = {'surge': raw_scores_30}
        engine_platt.fit_calibrators(scores_dict_30, true_labels_30)

        self.assertTrue(engine_platt.has_calibrators())
        cal_type_platt, _ = engine_platt._calibrators['surge']
        self.assertEqual(cal_type_platt, 'platt')

        calibrated_30 = engine_platt.calibrate_scores('surge', raw_scores_30)
        self.assertEqual(len(calibrated_30), 30)
        self.assertTrue(np.all(calibrated_30 >= 0.0))
        self.assertTrue(np.all(calibrated_30 <= 1.0))

        # 3. N = 10 (Insufficient samples, skip calibration)
        engine_small = EnsembleScoringEngine()
        raw_scores_10 = np.linspace(0.1, 0.9, 10)
        true_labels_10 = (raw_scores_10 > 0.5).astype(float)

        engine_small.fit_calibrators({'vcp_ml': raw_scores_10}, true_labels_10)
        self.assertFalse(engine_small.has_calibrators())

    def test_zero_variance_target_label_handling(self):
        """Verify that single-class target labels (all 0s or all 1s) are safely skipped without score flattening."""
        raw_scores = np.linspace(0.0, 1.0, 100)
        all_zeros = np.zeros(100)

        engine = EnsembleScoringEngine()
        engine.fit_calibrators({'regression': raw_scores}, all_zeros)

        # Single class should be skipped, leaving calibrators empty
        self.assertNotIn('regression', engine._calibrators)

        # Calibrating scores with no calibrators should return input scores untouched
        calibrated = engine.calibrate_scores('regression', raw_scores)
        np.testing.assert_array_equal(calibrated, raw_scores)
        self.assertGreater(np.max(calibrated), 0.5)  # Confirm scores were NOT flattened to 0.0

    def test_rolling_sharpe_calculation(self):
        """Verify rolling Sharpe calculations across positive, negative, zero variance, and small sample inputs."""
        returns_data = {
            'pos_strat': pd.Series([0.01, 0.02, 0.015, 0.008, 0.025, 0.012]),
            'neg_strat': pd.Series([-0.01, -0.02, -0.015, -0.008, -0.025, -0.012]),
            'zero_var_strat': pd.Series([0.01, 0.01, 0.01, 0.01, 0.01]),
            'small_strat': pd.Series([0.05]),
            'empty_strat': pd.Series([], dtype=float)
        }

        sharpes = self.engine.compute_rolling_sharpe(returns_data, window=60, risk_free_rate=0.0)

        self.assertGreater(sharpes['pos_strat'], 0.0)
        self.assertLess(sharpes['neg_strat'], 0.0)
        self.assertGreater(sharpes['zero_var_strat'], 0.0)  # Standard deviation epsilon prevents div-by-zero
        self.assertEqual(sharpes['small_strat'], 0.0)
        self.assertEqual(sharpes['empty_strat'], 0.0)

    def test_cold_start_seeds_across_all_6_regimes(self):
        """Verify cold-start seed Sharpes are applied across all 6 2D market regimes when realized return history is empty."""
        regimes = [
            'BULL_LOW_VOL',
            'BULL_HIGH_VOL',
            'SIDEWAYS_LOW_VOL',
            'SIDEWAYS_HIGH_VOL',
            'BEAR_LOW_VOL',
            'BEAR_HIGH_VOL'
        ]

        empty_sharpes = {s: 0.0 for s in self.strategies}

        for reg in regimes:
            engine = EnsembleScoringEngine()
            weights = engine.compute_dynamic_weights_from_sharpe(empty_sharpes, regime=reg)

            self.assertEqual(len(weights), 23)
            self.assertAlmostEqual(sum(weights.values()), 1.0, places=5)

            # In BULL regimes, surge and vcp_ml should receive boost relative to stat_arb
            if 'BULL' in reg:
                self.assertGreater(weights['surge'], weights['stat_arb'])
            # In BEAR regimes, defensive stat_arb and rim_valuation should receive boost
            elif 'BEAR' in reg:
                self.assertGreater(weights['stat_arb'], weights['surge'])

    def test_ema_regime_shift_reset(self):
        """Verify EMA smoothing resets alpha = 1.0 on 2D regime transition for immediate weight alignment."""
        engine = EnsembleScoringEngine(alpha_smoothing=0.2)

        fake_sharpes = {s: 0.5 for s in self.strategies}

        # Step 1: Initial call in BULL_LOW_VOL
        weights_bull_1 = engine.compute_dynamic_weights_from_sharpe(fake_sharpes, regime='BULL_LOW_VOL')
        self.assertEqual(engine._prev_regime, 'BULL_LOW_VOL')

        # Step 2: Second call in BULL_LOW_VOL with updated Sharpes (EMA smoothing alpha = 0.2 active)
        updated_sharpes = dict(fake_sharpes)
        updated_sharpes['surge'] = 2.5
        weights_bull_2 = engine.compute_dynamic_weights_from_sharpe(updated_sharpes, regime='BULL_LOW_VOL')

        # Target weight without EMA for surge would be much higher, EMA smooths it
        target_bull_weights = engine.get_base_weights('BULL_LOW_VOL')
        # Check that previous weights influenced weights_bull_2
        self.assertLess(weights_bull_2['surge'], 0.5)  # Smoothed, not instant jump

        # Step 3: Transition regime to BEAR_HIGH_VOL (Regime shift reset alpha = 1.0)
        weights_bear = engine.compute_dynamic_weights_from_sharpe(fake_sharpes, regime='BEAR_HIGH_VOL')
        self.assertEqual(engine._prev_regime, 'BEAR_HIGH_VOL')

        # On transition, weights should immediately match target BEAR_HIGH_VOL weights (alpha = 1.0)
        # Calculate un-smoothed target for BEAR_HIGH_VOL
        base_bear_weights = engine.get_base_weights('BEAR_HIGH_VOL')
        expected_bear_scores = {k: v * np.exp(1.0 * 0.5) for k, v in base_bear_weights.items()}
        tot_expected = sum(expected_bear_scores.values())
        expected_bear_w = {k: v / tot_expected for k, v in expected_bear_scores.items()}

        for strat in self.strategies:
            self.assertAlmostEqual(weights_bear[strat], expected_bear_w[strat], places=5)


if __name__ == '__main__':
    unittest.main()
