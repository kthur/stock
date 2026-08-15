"""
Adversarial and Empirical Stress Test Suite for 31-Strategy Ensemble & Calibration Pipeline.
Author: Challenger 2 (challenger_2)
Scope:
1. scorer.fit_calibrators with corrupted, missing, identical, or extreme score distributions across all 31 strategies.
2. PCA ZCA factor orthogonalization and Gram-Schmidt decorrelation under collinear, rank-deficient, and single-asset matrices.
3. 2D market regime weighting, 3D macro overrides, and dynamic Sharpe weighting (sum of weights = 1.000, scores in [0.0, 1.0]).
4. End-to-end ensemble scoring pipeline stability and boundary enforcement under adversarial conditions.
"""

import os
import sys
import unittest
import time
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../trading_system')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.ai.factor_orthogonalizer import FactorOrthogonalizerEngine
from src.ai.ensemble_scorer import EnsembleScoringEngine
from src.ai.factor_suppression import RegimeFactorSuppressionEngine
from src.ai.correlation_monitor import StrategyCorrelationMonitor


class TestAdversarialEnsembleScorerChallenger(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.ALL_31_STRATEGIES = [
            'regression', 'surge', 'lead_lag', 'vcp_rule', 'vcp_ml',
            'lstm', 'stat_arb', 'sector_rotation', 'rim_valuation', 'event_driven',
            'mq_factor', 'iv_skew', 'order_flow', 'short_term_reversal',
            'arm_factor', 'card_factor', 'latr_factor', 'inst_foreign_sector',
            'supply_chain', 'sentiment', 'factor_neutralized', 'vol_target',
            'microstructure', 'accruals_quality', 'short_squeeze', 'valueup_catalyst',
            'trend_efficiency', 'gamma_squeeze', 'insider_buying', 'darkpool',
            'earnings_tone_drift'
        ]
        cls.ALL_31_SCORE_COLS = [
            'reg_score', 'surge_score', 'll_score', 'vcp_rule_score', 'vcp_ml_score',
            'lstm_score', 'stat_arb_score', 'sector_score', 'rim_score', 'event_score',
            'mq_score', 'iv_skew_score', 'order_flow_score', 'reversal_score',
            'arm_score', 'card_score', 'latr_score', 'inst_foreign_sector_score',
            'supply_chain_score', 'sentiment_score', 'factor_neutralized_score', 'vol_target_score',
            'microstructure_score', 'accruals_quality_score', 'short_squeeze_score', 'valueup_catalyst_score',
            'trend_efficiency_score', 'gamma_squeeze_score', 'insider_buying_score', 'darkpool_score',
            'earnings_tone_drift_score'
        ]

    def setUp(self):
        self.scorer = EnsembleScoringEngine(alpha_smoothing=0.2)
        self.ortho_pca = FactorOrthogonalizerEngine(default_method='pca_symmetric')
        self.ortho_gs = FactorOrthogonalizerEngine(default_method='gram_schmidt')

    # =========================================================================
    # Task 1: Calibrator Stress Testing (fit_calibrators & calibrate_scores)
    # =========================================================================

    def test_calibrators_across_all_31_strategies_normal_and_extreme(self):
        """Fit calibrators across all 31 strategies under varied sample sizes and noise."""
        np.random.seed(42)
        for i, strat in enumerate(self.ALL_31_STRATEGIES):
            N = 60 if i % 2 == 0 else 35  # Alternate between Isotonic (N>=50) and Platt (20<=N<50)
            raw_scores = np.sort(np.random.uniform(0.0, 1.0, N))
            true_labels = (raw_scores + np.random.normal(0, 0.15, N) > 0.5).astype(float)
            true_labels[0] = 0.0
            true_labels[-1] = 1.0

            scorer = EnsembleScoringEngine()
            scorer.fit_calibrators({strat: raw_scores}, true_labels)

            self.assertTrue(scorer.has_calibrators(), f"Strategy {strat} failed to fit calibrator")
            expected_type = 'isotonic' if N >= 50 else 'platt'
            cal_type, _ = scorer._calibrators[strat]
            self.assertEqual(cal_type, expected_type, f"Strategy {strat} expected {expected_type}, got {cal_type}")

            # Test calibrate_scores with out-of-bounds, NaNs, Infs
            test_input = np.array([-10.0, -0.5, 0.0, 0.25, 0.50, 0.75, 1.0, 1.5, 100.0, np.nan, np.inf, -np.inf])
            calibrated = scorer.calibrate_scores(strat, test_input)

            self.assertEqual(len(calibrated), len(test_input))
            self.assertFalse(np.isnan(calibrated).any(), f"NaN in calibrated scores for {strat}")
            self.assertFalse(np.isinf(calibrated).any(), f"Inf in calibrated scores for {strat}")
            self.assertTrue(np.all(calibrated >= 0.0), f"Scores < 0 for {strat}")
            self.assertTrue(np.all(calibrated <= 1.0), f"Scores > 1 for {strat}")

    def test_calibrators_corrupted_and_mismatched_inputs(self):
        """Verify fit_calibrators handles corrupted arrays, NaNs, Infs, length mismatches, and empty inputs."""
        corrupted_cases = [
            # Case 1: Array length mismatch
            (np.random.uniform(0, 1, 100), np.array([0, 1, 0, 1])),
            # Case 2: Extreme values (-1e10, +1e10, NaNs, Infs)
            (np.array([np.nan, np.inf, -np.inf, -1e10, 1e10] + list(np.linspace(0, 1, 60))),
             np.array([0, 1, 0, 1, 0] + list((np.linspace(0, 1, 60) > 0.5).astype(float)))),
            # Case 3: All NaNs
            (np.full(100, np.nan), np.random.randint(0, 2, 100).astype(float)),
            # Case 4: All Infs
            (np.full(100, np.inf), np.random.randint(0, 2, 100).astype(float)),
            # Case 5: Empty arrays
            (np.array([]), np.array([])),
            # Case 6: N < 20 samples (insufficient data)
            (np.linspace(0, 1, 15), np.random.randint(0, 2, 15).astype(float)),
        ]

        for idx, (scores, labels) in enumerate(corrupted_cases):
            scorer = EnsembleScoringEngine()
            # Must never raise an unhandled exception
            try:
                scorer.fit_calibrators({'regression': scores, 'surge': scores}, labels)
            except Exception as e:
                self.fail(f"fit_calibrators raised exception on case {idx}: {e}")

            # Verify calibrate_scores still functions safely without crashing
            test_finite = np.array([0.1, 0.5, 0.9])
            res_finite = scorer.calibrate_scores('regression', test_finite)
            self.assertFalse(np.isnan(res_finite).any())
            self.assertFalse(np.isinf(res_finite).any())
            self.assertTrue(np.all(res_finite >= 0.0) and np.all(res_finite <= 1.0))

            # When calibrator was fitted on valid subset (e.g. Case 2), verify out-of-bounds input sanitization
            if 'regression' in scorer._calibrators:
                res_extreme = scorer.calibrate_scores('regression', np.array([np.nan, np.inf, -100.0, 100.0]))
                self.assertFalse(np.isnan(res_extreme).any())
                self.assertFalse(np.isinf(res_extreme).any())
                self.assertTrue(np.all(res_extreme >= 0.0) and np.all(res_extreme <= 1.0))

    def test_calibrators_single_class_zero_variance_labels(self):
        """Verify that single-class target labels (all 0s or all 1s) are safely skipped without score distortion."""
        raw_scores = np.linspace(0.0, 1.0, 100)
        for val in [0.0, 1.0]:
            scorer = EnsembleScoringEngine()
            labels = np.full(100, val)
            scorer.fit_calibrators({'regression': raw_scores}, labels)
            # Calibrator must be skipped
            self.assertNotIn('regression', scorer._calibrators)
            # Scores must remain untouched
            calibrated = scorer.calibrate_scores('regression', raw_scores)
            np.testing.assert_array_almost_equal(calibrated, raw_scores)

    def test_calibrators_identical_score_distributions(self):
        """Verify behavior when score distribution is constant (e.g. all 0.5 or all 0.0)."""
        labels = np.array([0.0]*50 + [1.0]*50)
        for const_val in [0.0, 0.5, 1.0]:
            scores = np.full(100, const_val)
            scorer = EnsembleScoringEngine()
            scorer.fit_calibrators({'regression': scores}, labels)
            # Even if fitted or skipped, calibrate_scores must be stable
            res = scorer.calibrate_scores('regression', np.array([0.0, 0.5, 1.0]))
            self.assertTrue(np.all(res >= 0.0) and np.all(res <= 1.0))

    def test_compute_ece_and_brier_adversarial(self):
        """Verify compute_ece_and_brier under corrupted inputs (empty, NaNs, all Infs)."""
        scorer = EnsembleScoringEngine()
        # 1. Empty arrays
        metrics = scorer.compute_ece_and_brier(np.array([]), np.array([]))
        self.assertEqual(metrics, {"ece": 0.0, "brier": 0.0})

        # 2. Corrupted NaNs / Infs
        p = np.array([np.nan, np.inf, -np.inf, 0.2, 0.8])
        y = np.array([0.0, 1.0, np.nan, 0.0, 1.0])
        metrics2 = scorer.compute_ece_and_brier(p, y)
        self.assertGreaterEqual(metrics2['ece'], 0.0)
        self.assertGreaterEqual(metrics2['brier'], 0.0)

        # 3. Perfect predictions
        p_perf = np.array([0.0, 0.0, 1.0, 1.0])
        y_perf = np.array([0.0, 0.0, 1.0, 1.0])
        metrics_perf = scorer.compute_ece_and_brier(p_perf, y_perf)
        self.assertAlmostEqual(metrics_perf['brier'], 0.0)
        self.assertAlmostEqual(metrics_perf['ece'], 0.0)

    # =========================================================================
    # Task 2: Factor Orthogonalization Stress Testing (PCA ZCA & Gram-Schmidt)
    # =========================================================================

    def test_orthogonalization_single_asset_and_minimal_samples(self):
        """Test orthogonalization when N < 3 or valid_cols < 2 (must return copy safely without crash)."""
        cols = self.ALL_31_SCORE_COLS
        for n_rows in [0, 1, 2]:
            df = pd.DataFrame(
                np.random.uniform(0, 1, (n_rows, len(cols))),
                columns=cols
            )
            df['symbol'] = [f"SYM_{i}" for i in range(n_rows)]

            for method in ['pca_symmetric', 'gram_schmidt']:
                out_df = self.ortho_pca.orthogonalize(df, cols, method=method)
                self.assertEqual(len(out_df), n_rows)
                self.assertEqual(list(out_df.columns), list(df.columns))

    def test_orthogonalization_rank_deficient_and_fully_collinear_31_strategies(self):
        """Test rank-1 and rank-deficient matrices across all 31 strategies."""
        N = 200
        cols = self.ALL_31_SCORE_COLS
        K = len(cols)

        # Rank-1 Matrix: all 31 columns are identical copies of 1 latent vector
        latent = np.random.uniform(0.1, 0.9, N)
        rank1_matrix = np.column_stack([latent for _ in range(K)])
        df_rank1 = pd.DataFrame(rank1_matrix, columns=cols)
        df_rank1['symbol'] = [f"SYM_{i:04d}" for i in range(N)]

        for method in ['pca_symmetric', 'gram_schmidt']:
            res = self.ortho_pca.orthogonalize(df_rank1, cols, method=method)
            vals = res[cols].to_numpy()
            self.assertFalse(np.isnan(vals).any(), f"NaN in {method} for rank-1 matrix")
            self.assertFalse(np.isinf(vals).any(), f"Inf in {method} for rank-1 matrix")
            self.assertTrue(np.all(vals >= 0.0), f"Scores < 0 in {method}")
            self.assertTrue(np.all(vals <= 1.0), f"Scores > 1 in {method}")

        # Linear combination dependencies: col_i = a * col_0 + b * col_1
        c0 = np.random.uniform(0, 1, N)
        c1 = np.random.uniform(0, 1, N)
        dep_cols = [c0, c1]
        for i in range(2, K):
            dep_cols.append(0.6 * c0 + 0.4 * c1)
        df_dep = pd.DataFrame(np.column_stack(dep_cols), columns=cols)
        df_dep['symbol'] = [f"SYM_{i:04d}" for i in range(N)]

        for method in ['pca_symmetric', 'gram_schmidt']:
            res = self.ortho_pca.orthogonalize(df_dep, cols, method=method)
            vals = res[cols].to_numpy()
            self.assertFalse(np.isnan(vals).any())
            self.assertFalse(np.isinf(vals).any())
            self.assertTrue(np.all(vals >= 0.0) and np.all(vals <= 1.0))

    def test_orthogonalization_zero_variance_and_constant_columns(self):
        """Test zero-variance columns (all 0.0, all 0.5, all 1.0) mixed with random signals."""
        N = 150
        cols = self.ALL_31_SCORE_COLS
        K = len(cols)
        matrix = np.random.uniform(0.1, 0.9, (N, K))
        matrix[:, 0] = 0.0  # Constant 0.0
        matrix[:, 1] = 0.5  # Constant 0.5
        matrix[:, 2] = 1.0  # Constant 1.0
        matrix[:, 3] = 0.0  # Another constant 0.0

        df = pd.DataFrame(matrix, columns=cols)
        df['symbol'] = [f"SYM_{i:04d}" for i in range(N)]

        for method in ['pca_symmetric', 'gram_schmidt']:
            res = self.ortho_pca.orthogonalize(df, cols, method=method)
            vals = res[cols].to_numpy()
            self.assertFalse(np.isnan(vals).any(), f"NaN found in {method} with constant columns")
            self.assertFalse(np.isinf(vals).any(), f"Inf found in {method} with constant columns")
            self.assertTrue(np.all(vals >= 0.0) and np.all(vals <= 1.0))

    def test_orthogonalization_n_less_than_k(self):
        """Test severely underdetermined case where N < K (e.g. N = 10 stocks, K = 31 strategies)."""
        N = 10
        cols = self.ALL_31_SCORE_COLS
        matrix = np.random.uniform(0.1, 0.9, (N, len(cols)))
        df = pd.DataFrame(matrix, columns=cols)
        df['symbol'] = [f"SYM_{i:04d}" for i in range(N)]

        for method in ['pca_symmetric', 'gram_schmidt']:
            res = self.ortho_pca.orthogonalize(df, cols, method=method)
            vals = res[cols].to_numpy()
            self.assertEqual(vals.shape, (N, len(cols)))
            self.assertFalse(np.isnan(vals).any())
            self.assertFalse(np.isinf(vals).any())
            self.assertTrue(np.all(vals >= 0.0) and np.all(vals <= 1.0))

    def test_orthogonalization_extreme_nans_and_sparse_missingness(self):
        """Test handling of NaN values in score matrix."""
        N = 100
        cols = self.ALL_31_SCORE_COLS
        matrix = np.random.uniform(0.1, 0.9, (N, len(cols)))
        # Insert random NaNs
        nan_mask = np.random.random(matrix.shape) < 0.20
        matrix[nan_mask] = np.nan
        # Entire column of NaNs
        matrix[:, 5] = np.nan

        df = pd.DataFrame(matrix, columns=cols)
        df['symbol'] = [f"SYM_{i:04d}" for i in range(N)]

        for method in ['pca_symmetric', 'gram_schmidt']:
            res = self.ortho_pca.orthogonalize(df, cols, method=method)
            vals = res[cols].to_numpy()
            # NaNs in original should be preserved as NaNs in output, non-NaNs must be valid [0.0, 1.0]
            non_nan_mask = ~np.isnan(matrix)
            self.assertTrue(np.all(vals[non_nan_mask] >= 0.0))
            self.assertTrue(np.all(vals[non_nan_mask] <= 1.0))
            self.assertTrue(np.isnan(vals[nan_mask]).all())

    def test_orthogonalization_scale_and_performance(self):
        """Benchmark 3,379 symbols x 31 strategies performance (< 1.5 seconds)."""
        N = 3379
        cols = self.ALL_31_SCORE_COLS
        np.random.seed(42)
        matrix = np.random.uniform(0.1, 0.9, (N, len(cols)))
        df = pd.DataFrame(matrix, columns=cols)
        df['symbol'] = [f"SYM_{i:04d}" for i in range(N)]

        start_time = time.time()
        res = self.ortho_pca.orthogonalize(df, cols, method='pca_symmetric')
        elapsed = time.time() - start_time

        self.assertLess(elapsed, 1.5, f"Orthogonalization took {elapsed:.2f}s, expected < 1.5s")
        vals = res[cols].to_numpy()
        self.assertEqual(vals.shape, (N, len(cols)))
        self.assertFalse(np.isnan(vals).any())
        self.assertFalse(np.isinf(vals).any())

    # =========================================================================
    # Task 3: 2D Regime Weighting, Macro Overrides, and Dynamic Sharpe Weighting
    # =========================================================================

    def test_regime_weights_sum_to_one_all_regimes(self):
        """Verify baseline regime weights strictly sum to 1.000 for all 6 2D and 3 1D regimes."""
        regimes_2d = ['BEAR_LOW_VOL', 'BEAR_HIGH_VOL', 'SIDEWAYS_LOW_VOL', 'SIDEWAYS_HIGH_VOL', 'BULL_LOW_VOL', 'BULL_HIGH_VOL']
        regimes_1d = [0, 1, 2]

        for reg in regimes_2d + regimes_1d:
            w = self.scorer.get_base_weights(reg)
            total = sum(w.values())
            self.assertAlmostEqual(total, 1.0, places=6, msg=f"Regime {reg} base weights sum to {total} != 1.0")
            for strat, weight in w.items():
                self.assertGreaterEqual(weight, 0.0, f"Negative weight for {strat} in regime {reg}")

    def test_macro_overrides_sum_to_one(self):
        """Verify all 5 Macro Overrides combined with all 6 2D regimes sum to 1.000."""
        regimes = ['BEAR_LOW_VOL', 'BEAR_HIGH_VOL', 'SIDEWAYS_LOW_VOL', 'SIDEWAYS_HIGH_VOL', 'BULL_LOW_VOL', 'BULL_HIGH_VOL']
        macros = ['LIQUIDITY_SQUEEZE', 'HIGH_YIELD_BULL', 'HIGH_YIELD_BEAR', 'INFLATION_SHOCK', 'YIELD_INVERSION']

        for reg in regimes:
            for macro in macros:
                w = self.scorer.get_base_weights(reg, macro_label=macro)
                total = sum(w.values())
                self.assertAlmostEqual(total, 1.0, places=6, msg=f"Regime {reg} + Macro {macro} sum to {total} != 1.0")
                for strat, weight in w.items():
                    self.assertGreaterEqual(weight, 0.0, f"Negative weight for {strat} in {reg}+{macro}")

    def test_vix_overrides_sum_to_one(self):
        """Verify VIX fast overrides at critical thresholds sum to 1.000."""
        vix_values = [-5.0, 0.0, 15.0, 25.0, 29.9, 30.1, 39.9, 40.1, 55.0, 100.0]
        regimes = ['BEAR_LOW_VOL', 'BEAR_HIGH_VOL', 'SIDEWAYS_LOW_VOL', 'SIDEWAYS_HIGH_VOL', 'BULL_LOW_VOL', 'BULL_HIGH_VOL']

        for reg in regimes:
            for vix in vix_values:
                w = self.scorer.get_base_weights(reg, vix_val=vix)
                total = sum(w.values())
                self.assertAlmostEqual(total, 1.0, places=6, msg=f"Regime {reg} + VIX {vix} sum to {total} != 1.0")
                for strat, weight in w.items():
                    self.assertGreaterEqual(weight, 0.0, f"Negative weight for {strat} at VIX={vix}")

    def test_dynamic_sharpe_weighting_extreme_distributions(self):
        """Verify compute_dynamic_weights_from_sharpe under extreme, negative, infinite, and NaN Sharpe ratios."""
        regimes = ['BEAR_LOW_VOL', 'SIDEWAYS_LOW_VOL', 'BULL_HIGH_VOL']
        extreme_sharpe_cases = [
            # Case 1: All highly positive
            {s: 10.0 for s in self.ALL_31_STRATEGIES},
            # Case 2: All severely negative (pruned)
            {s: -5.0 for s in self.ALL_31_STRATEGIES},
            # Case 3: Mixed extreme (+50.0, -50.0, 0.0, NaN, Inf)
            {s: (50.0 if i % 4 == 0 else (-50.0 if i % 4 == 1 else (np.nan if i % 4 == 2 else np.inf)))
             for i, s in enumerate(self.ALL_31_STRATEGIES)},
            # Case 4: All zero (cold start)
            {s: 0.0 for s in self.ALL_31_STRATEGIES},
            # Case 5: Empty dict
            {},
        ]

        for reg in regimes:
            for idx, sharpes in enumerate(extreme_sharpe_cases):
                w = self.scorer.compute_dynamic_weights_from_sharpe(sharpes, reg, gamma=1.5)
                total = sum(w.values())
                self.assertAlmostEqual(total, 1.0, places=5, msg=f"Regime {reg} Sharpe case {idx} sum = {total} != 1.0")
                for s, weight in w.items():
                    self.assertFalse(np.isnan(weight), f"NaN weight for {s}")
                    self.assertFalse(np.isinf(weight), f"Inf weight for {s}")
                    self.assertGreaterEqual(weight, 0.0, f"Negative weight for {s}")

    def test_correlation_suppression_and_orthogonalization_penalty_sum_to_one(self):
        """Verify correlation suppression and orthogonalization penalties maintain sum(weights) = 1.000."""
        # Create collinear score DataFrame
        N = 100
        latent = np.random.uniform(0.2, 0.8, N)
        scores_dict = {'symbol': [f"SYM_{i:04d}" for i in range(N)]}
        for col in self.ALL_31_SCORE_COLS:
            scores_dict[col] = latent + np.random.normal(0, 0.05, N)
        scores_df = pd.DataFrame(scores_dict)

        base_weights = self.scorer.get_base_weights('SIDEWAYS_LOW_VOL')
        penalized_weights = self.scorer.apply_correlation_orthogonalization_penalty(
            base_weights, scores_df=scores_df, correlation_threshold=0.60
        )
        total_pen = sum(penalized_weights.values())
        self.assertAlmostEqual(total_pen, 1.0, places=5, msg=f"Penalized weights sum {total_pen} != 1.0")

        # Factor suppression engine
        corr_monitor = StrategyCorrelationMonitor()
        corr_matrix = corr_monitor.update_correlation(scores_df)
        suppression_engine = RegimeFactorSuppressionEngine()
        suppressed_w = suppression_engine.suppress_weights(
            base_weights=base_weights, corr_matrix=corr_matrix, regime_label='SIDEWAYS_LOW_VOL'
        )
        total_sup = sum(suppressed_w.values())
        self.assertAlmostEqual(total_sup, 1.0, places=5, msg=f"Suppressed weights sum {total_sup} != 1.0")

    # =========================================================================
    # Task 4: End-to-End Ensemble Pipeline Score Bounds and Robustness
    # =========================================================================

    def test_end_to_end_ensemble_score_bounds_and_completeness(self):
        """Execute end-to-end calculate_ensemble_score with adversarial data across all 31 strategies."""
        N = 100
        symbols = [f"SYM_{i:04d}" for i in range(N)]

        # Generate mock input DataFrames for strategies
        def _make_df(col_name, val_generator):
            df = pd.DataFrame({
                'symbol': symbols,
                col_name: val_generator(N),
                'close': np.random.uniform(10000, 100000, N),
                'market': np.random.choice(['KOSPI', 'KOSDAQ', 'SP500', 'NASDAQ', 'RUSSELL2000'], N),
                'volume': np.random.uniform(100000, 10000000, N),
                'operating_margin': np.random.uniform(-0.30, 0.30, N),
                'roe': np.random.uniform(-0.30, 0.30, N),
                'volatility_20d': np.random.uniform(0.01, 0.05, N),
            })
            return df

        reg_df = _make_df('expected_return_20d', lambda n: np.random.uniform(-50.0, 150.0, n))
        surge_df = _make_df('surge_score', lambda n: np.random.uniform(0.0, 1.0, n))
        ll_df = _make_df('ll_score', lambda n: np.random.uniform(0.0, 1.0, n))
        vcp_ml_df = _make_df('vcp_ml_score', lambda n: np.random.uniform(0.0, 1.0, n))
        vcp_rule_df = _make_df('vcp_rule_score', lambda n: np.random.uniform(0.0, 1.0, n))
        lstm_df = _make_df('lstm_score', lambda n: np.random.uniform(0.0, 1.0, n))
        stat_arb_df = _make_df('stat_arb_score', lambda n: np.random.uniform(0.0, 1.0, n))
        sector_df = _make_df('sector_score', lambda n: np.random.uniform(0.0, 1.0, n))
        rim_df = _make_df('rim_score', lambda n: np.random.uniform(0.0, 1.0, n))
        event_df = _make_df('event_score', lambda n: np.random.uniform(0.0, 1.0, n))
        mq_df = _make_df('mq_score', lambda n: np.random.uniform(0.0, 1.0, n))
        iv_skew_df = _make_df('iv_skew_score', lambda n: np.random.uniform(0.0, 1.0, n))
        order_flow_df = _make_df('order_flow_score', lambda n: np.random.uniform(0.0, 1.0, n))
        reversal_df = _make_df('reversal_score', lambda n: np.random.uniform(0.0, 1.0, n))
        arm_df = _make_df('arm_score', lambda n: np.random.uniform(0.0, 1.0, n))
        card_df = _make_df('card_score', lambda n: np.random.uniform(0.0, 1.0, n))
        latr_df = _make_df('latr_score', lambda n: np.random.uniform(0.0, 1.0, n))
        inst_df = _make_df('inst_foreign_sector_score', lambda n: np.random.uniform(0.0, 1.0, n))
        sc_df = _make_df('supply_chain_score', lambda n: np.random.uniform(0.0, 1.0, n))
        sent_df = _make_df('sentiment_score', lambda n: np.random.uniform(0.0, 1.0, n))
        fn_df = _make_df('factor_neutralized_score', lambda n: np.random.uniform(0.0, 1.0, n))
        vt_df = _make_df('vol_target_score', lambda n: np.random.uniform(0.0, 1.0, n))
        micro_df = _make_df('microstructure_score', lambda n: np.random.uniform(0.0, 1.0, n))
        aq_df = _make_df('accruals_quality_score', lambda n: np.random.uniform(0.0, 1.0, n))
        sq_df = _make_df('short_squeeze_score', lambda n: np.random.uniform(0.0, 1.0, n))
        vu_df = _make_df('valueup_catalyst_score', lambda n: np.random.uniform(0.0, 1.0, n))
        te_df = _make_df('trend_efficiency_score', lambda n: np.random.uniform(0.0, 1.0, n))
        gs_df = _make_df('gamma_squeeze_score', lambda n: np.random.uniform(0.0, 1.0, n))
        ib_df = _make_df('insider_buying_score', lambda n: np.random.uniform(0.0, 1.0, n))
        dp_df = _make_df('darkpool_score', lambda n: np.random.uniform(0.0, 1.0, n))
        etd_df = _make_df('earnings_tone_drift_score', lambda n: np.random.uniform(0.0, 1.0, n))

        # Test across all 6 regimes and with held symbols + sentiment blacklist
        held_syms = symbols[:10]
        blacklist = {symbols[15]: 'CRITICAL_ACCOUNTING_FRAUD', symbols[16]: 'DELISTING_NOTICE'}

        for reg in ['BEAR_LOW_VOL', 'BEAR_HIGH_VOL', 'SIDEWAYS_LOW_VOL', 'SIDEWAYS_HIGH_VOL', 'BULL_LOW_VOL', 'BULL_HIGH_VOL']:
            res_df = self.scorer.calculate_ensemble_score(
                regime=reg,
                regression_df=reg_df,
                surge_df=surge_df,
                lead_lag_df=ll_df,
                vcp_ml_df=vcp_ml_df,
                vcp_rule_df=vcp_rule_df,
                lstm_df=lstm_df,
                stat_arb_df=stat_arb_df,
                sector_df=sector_df,
                rim_df=rim_df,
                event_df=event_df,
                mq_df=mq_df,
                iv_skew_df=iv_skew_df,
                order_flow_df=order_flow_df,
                reversal_df=reversal_df,
                arm_df=arm_df,
                card_df=card_df,
                latr_df=latr_df,
                inst_foreign_sector_df=inst_df,
                supply_chain_df=sc_df,
                sentiment_df=sent_df,
                factor_neutralized_df=fn_df,
                vol_target_df=vt_df,
                microstructure_df=micro_df,
                accruals_quality_df=aq_df,
                short_squeeze_df=sq_df,
                valueup_catalyst_df=vu_df,
                trend_efficiency_df=te_df,
                gamma_squeeze_df=gs_df,
                insider_buying_df=ib_df,
                darkpool_df=dp_df,
                earnings_tone_drift_df=etd_df,
                sentiment_blacklist=blacklist,
                held_symbols=held_syms,
                target_horizon=20
            )

            # Assertions on ensemble scores and returns
            self.assertEqual(len(res_df), N)
            self.assertIn('ensemble_score', res_df.columns)
            self.assertIn('ensemble_expected_return', res_df.columns)

            e_scores = res_df['ensemble_score'].to_numpy()
            e_returns = res_df['ensemble_expected_return'].to_numpy()

            self.assertFalse(np.isnan(e_scores).any(), f"NaN in ensemble_score for regime {reg}")
            self.assertFalse(np.isinf(e_scores).any(), f"Inf in ensemble_score for regime {reg}")
            self.assertTrue(np.all(e_scores >= 0.0), f"Negative ensemble_score for regime {reg}")
            self.assertTrue(np.all(e_scores <= 1.0), f"ensemble_score > 1.0 for regime {reg}")

            self.assertFalse(np.isnan(e_returns).any(), f"NaN in ensemble_expected_return for regime {reg}")
            self.assertFalse(np.isinf(e_returns).any(), f"Inf in ensemble_expected_return for regime {reg}")
            self.assertTrue(np.all(e_returns >= 0.0), f"Negative return for regime {reg}")
            self.assertTrue(np.all(e_returns <= 50.0), f"Return > 50% for regime {reg}")

            # Verify blacklisted symbols are zero-weighted
            for b_sym in blacklist:
                b_row = res_df[res_df['symbol'] == b_sym]
                if not b_row.empty:
                    self.assertEqual(float(b_row['ensemble_score'].iloc[0]), 0.0)
                    self.assertEqual(float(b_row['ensemble_expected_return'].iloc[0]), 0.0)


if __name__ == '__main__':
    unittest.main()
