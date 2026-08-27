import os
import sys
import unittest
import numpy as np
import pandas as pd

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../trading_system')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.ai.factor_orthogonalizer import FactorOrthogonalizerEngine
from src.ai.factor_suppression import RegimeFactorSuppressionEngine
from src.ai.ensemble_scorer import EnsembleScoringEngine


def log(msg):
    print(msg)
    sys.stdout.flush()
    sys.stderr.flush()


class TestM1EmpiricalChallenger(unittest.TestCase):

    def setUp(self):
        self.ortho_engine = FactorOrthogonalizerEngine(shrinkage_alpha=0.01)
        self.supp_engine = RegimeFactorSuppressionEngine()
        self.ensemble_engine = EnsembleScoringEngine(alpha_smoothing=0.2)
        self.strategies = [
            'regression', 'surge', 'lead_lag', 'vcp_rule', 'vcp_ml',
            'lstm', 'stat_arb', 'sector_rotation', 'rim_valuation', 'event_driven',
            'mq_factor', 'iv_skew', 'order_flow', 'short_term_reversal',
            'arm_factor', 'card_factor', 'latr_factor', 'inst_foreign_sector',
            'supply_chain', 'sentiment', 'factor_neutralized', 'vol_target', 'microstructure'
        ]

    def test_empirical_ledoit_wolf_matrix_conditioning(self):
        """Empirically stress-test Ledoit-Wolf shrinkage regularization under extreme singular & collinear scenarios."""
        log("\n--- STRESS TEST 1: Ledoit-Wolf Matrix Conditioning ---")
        
        # Scenario 1.1: Perfect Collinearity (rho = 1.0 across 17 strategies)
        N, K = 100, 17
        base_signal = np.random.randn(N, 1)
        X_collinear = np.tile(base_signal, (1, K)) + np.random.randn(N, K) * 1e-12
        
        X_bar = (X_collinear - np.mean(X_collinear, axis=0)) / np.std(X_collinear, axis=0)
        C_raw = np.dot(X_bar.T, X_bar) / (N - 1)
        cond_raw = np.linalg.cond(C_raw)
        
        alpha = 0.01
        C_shrunk = (1.0 - alpha) * C_raw + alpha * np.eye(K)
        cond_shrunk = np.linalg.cond(C_shrunk)
        
        log(f"Scenario 1.1 (Perfect Collinearity): Raw Cond = {cond_raw:.2e}, Shrunk Cond = {cond_shrunk:.2f}")
        self.assertLess(cond_shrunk, 2000.0, "Condition number must be strictly bounded below 2000 under perfect collinearity.")
        
        cols = [f"s_{i}" for i in range(K)]
        df_collinear = pd.DataFrame(X_collinear, columns=cols)
        df_collinear = (df_collinear - df_collinear.min()) / (df_collinear.max() - df_collinear.min() + 1e-6)
        
        df_ortho = self.ortho_engine.orthogonalize(df_collinear, cols)
        self.assertFalse(df_ortho.isna().any().any(), "Orthogonalized scores must contain zero NaNs.")
        self.assertTrue((df_ortho.to_numpy() >= 0.0).all() and (df_ortho.to_numpy() <= 1.0).all(), "Scores must remain bounded in [0, 1].")

        # Scenario 1.2: Rank Deficient Sample Count (N = 5 samples, K = 17 strategies)
        N_small = 5
        X_small = np.random.randn(N_small, K)
        df_small = pd.DataFrame(X_small, columns=cols)
        df_small_norm = (df_small - df_small.min()) / (df_small.max() - df_small.min() + 1e-6)
        
        df_small_ortho = self.ortho_engine.orthogonalize(df_small_norm, cols)
        self.assertFalse(df_small_ortho.isna().any().any(), "Rank-deficient small sample matrix output must not contain NaNs.")
        log("Scenario 1.2 (Rank Deficient N=5, K=17): Successfully orthogonalized without failure.")

        # Scenario 1.3: Zero-Variance Column (One strategy produces constant score)
        df_zero_var = df_collinear.copy()
        df_zero_var['s_0'] = 0.5
        df_zero_var_ortho = self.ortho_engine.orthogonalize(df_zero_var, cols)
        self.assertFalse(df_zero_var_ortho.isna().any().any(), "Zero-variance column must not produce NaNs.")
        log("Scenario 1.3 (Zero Variance Column): Successfully handled zero-variance column.")

    def test_empirical_regime_factor_suppression(self):
        """Empirically stress-test factor suppression parameter mappings and penalties for CRISIS and HIGH_VOL."""
        log("\n--- STRESS TEST 2: Regime Factor Suppression Mappings ---")
        
        t_crisis, l_crisis = self.supp_engine._get_regime_params('CRISIS')
        self.assertEqual(t_crisis, 0.50, "CRISIS theta cutoff must be 0.50")
        self.assertEqual(l_crisis, 2.00, "CRISIS lambda penalty must be 2.00")
        
        clusters_crisis = self.supp_engine._get_high_risk_clusters('CRISIS')
        self.assertIn('MOMENTUM', clusters_crisis)
        self.assertIn('FLOW_MICRO', clusters_crisis)
        self.assertIn('REVERSAL', clusters_crisis)

        t_highvol, l_highvol = self.supp_engine._get_regime_params('HIGH_VOL')
        self.assertEqual(t_highvol, 0.55, "HIGH_VOL theta cutoff must be 0.55")
        self.assertEqual(l_highvol, 1.50, "HIGH_VOL lambda penalty must be 1.50")

        t_lower, l_lower = self.supp_engine._get_regime_params('crisis')
        self.assertEqual(t_lower, 0.50)
        self.assertEqual(l_lower, 2.00)

        strats = ['surge', 'vcp_ml', 'sector_rotation', 'stat_arb', 'rim_valuation']
        corr_matrix = pd.DataFrame([
            [1.00, 0.85, 0.40, 0.10, 0.05],
            [0.85, 1.00, 0.35, 0.08, 0.02],
            [0.40, 0.35, 1.00, 0.15, 0.10],
            [0.10, 0.08, 0.15, 1.00, 0.20],
            [0.05, 0.02, 0.10, 0.20, 1.00],
        ], index=strats, columns=strats)

        penalties_crisis = self.supp_engine.compute_penalties(corr_matrix, 'CRISIS', theta=0.50, lambda_penalty=2.00)
        log(f"CRISIS Penalties with High Momentum Correlation: {penalties_crisis}")
        
        self.assertLess(penalties_crisis['surge'], penalties_crisis['rim_valuation'], "Surge must receive heavier penalty than low-correlation Rim Valuation.")
        self.assertLess(penalties_crisis['vcp_ml'], penalties_crisis['stat_arb'], "VCP ML must receive heavier penalty than low-correlation Stat-Arb.")

    def test_empirical_isotonic_calibration_zero_variance(self):
        """Empirically stress-test Isotonic calibration handling of single-class target zero-variance edge cases."""
        log("\n--- STRESS TEST 3: Isotonic Calibration Zero-Variance Edge Cases ---")
        
        raw_scores = np.random.uniform(0.1, 0.9, 100)
        
        y_all_zeros = np.zeros(100)
        engine_zeros = EnsembleScoringEngine()
        engine_zeros.fit_calibrators({'regression': raw_scores}, y_all_zeros)
        self.assertNotIn('regression', engine_zeros._calibrators, "Calibrator fit must be skipped for single-class all-zero targets.")
        calibrated_zeros = engine_zeros.calibrate_scores('regression', raw_scores)
        np.testing.assert_array_equal(calibrated_zeros, raw_scores, "Raw scores must be returned unchanged when calibration is skipped.")

        y_all_ones = np.ones(100)
        engine_ones = EnsembleScoringEngine()
        engine_ones.fit_calibrators({'surge': raw_scores}, y_all_ones)
        self.assertNotIn('surge', engine_ones._calibrators, "Calibrator fit must be skipped for single-class all-one targets.")
        calibrated_ones = engine_ones.calibrate_scores('surge', raw_scores)
        np.testing.assert_array_equal(calibrated_ones, raw_scores, "Raw scores must be returned unchanged when calibration is skipped.")

        log("Successfully verified zero-variance target label skip behavior for both all-0 and all-1 classes.")

    def test_empirical_ema_regime_shift_reset(self):
        """Empirically stress-test EMA dynamic weight reset behavior on 2D regime transitions."""
        log("\n--- STRESS TEST 4: EMA Regime Shift Reset Behavior ---")
        
        engine = EnsembleScoringEngine(alpha_smoothing=0.2)
        fake_sharpes = {s: 0.5 for s in engine.get_base_weights('BULL_LOW_VOL').keys()}
        
        w_bull_1 = engine.compute_dynamic_weights_from_sharpe(fake_sharpes, regime='BULL_LOW_VOL')
        self.assertEqual(engine._prev_regime, 'BULL_LOW_VOL')
        
        updated_sharpes = dict(fake_sharpes)
        updated_sharpes['surge'] = 0.8
        w_bull_2 = engine.compute_dynamic_weights_from_sharpe(updated_sharpes, regime='BULL_LOW_VOL')
        
        w_bear_reset = engine.compute_dynamic_weights_from_sharpe(updated_sharpes, regime='BEAR_HIGH_VOL')
        self.assertEqual(engine._prev_regime, 'BEAR_HIGH_VOL')
        
        base_bear_weights = engine.get_base_weights('BEAR_HIGH_VOL')
        expected_scores = {k: base_bear_weights[k] * np.exp(1.0 * np.clip(updated_sharpes[k], -3.0, 3.0)) for k in base_bear_weights.keys()}
        tot_exp = sum(expected_scores.values())
        expected_w = {k: v / tot_exp for k, v in expected_scores.items()}
        
        for s in base_bear_weights.keys():
            self.assertAlmostEqual(w_bear_reset[s], expected_w[s], places=5, msg=f"Strategy {s} weight did not reset instantly on regime transition.")

        log("Successfully verified instant EMA weight reset on 2D regime transition.")


if __name__ == '__main__':
    unittest.main(verbosity=2)
