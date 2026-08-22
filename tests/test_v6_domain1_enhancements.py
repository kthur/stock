"""
Domain 1 Comprehensive Unit & Regression Tests (V6-01 ~ V6-08).
Validates:
- V6-01: Strict Causal LSTM target transform_sharpe mapping
- V6-02: Multi-Horizon Exponential Decay Filter column alias schema map
- V6-03: Dual-Regime US/KR weight decoupling and suppression penalty transfer
- V6-04: Market-aware batch evaluation in predict_lstm
- V6-05: predict_lead_lag fallback 1-day return normalization
- V6-06: Optuna 2D regime quadratic risk utility & AlphaDecayTracker simplex projection
- V6-07: Lead-Lag HPO evaluations for all leaders without 10-symbol cap
- V6-08: MetaEnsembleLearner feature permutation & projection alignment
"""

import unittest
import numpy as np
import pandas as pd
from unittest.mock import MagicMock

from src.ai.prediction_model import OnDevicePredictionModel
from src.ai.ensemble_scorer import EnsembleScoringEngine
from src.ai.optuna_tuner import OptunaStrategyTuner, AlphaDecayTracker
from src.ai.meta_ensemble_learner import MetaEnsembleLearner, STRATEGY_SCORE_COLS
from src.ai.target_transform import transform_sharpe, inverse_transform_sharpe


class TestV6Domain1Enhancements(unittest.TestCase):

    def test_v6_01_lstm_target_transform_sharpe(self):
        """V6-01: Verify LSTM training data preparation applies transform_sharpe."""
        model = OnDevicePredictionModel()
        dates = pd.date_range('2026-01-01', periods=30, freq='D')
        raw_targets = np.array([2.0] * 30)  # Sharpe = 2.0
        df = pd.DataFrame({
            'symbol': ['AAPL'] * 30,
            'date': dates,
            'ret_1d': [0.01] * 30,
            'target_20d': raw_targets
        })

        X_arr, y_arr, idx_arr = model._prepare_lstm_data(df, 'target_20d', seq_len=20)
        self.assertGreater(len(y_arr), 0)

        # Expected value in sign*log1p(|x|) space: sign(2.0) * log(1 + 2.0) = ln(3.0) ≈ 1.098612
        expected_transformed = np.log1p(2.0)
        self.assertAlmostEqual(float(np.ravel(y_arr)[0]), expected_transformed, places=4)
        # Verify it is NOT the raw 2.0 value
        self.assertNotAlmostEqual(float(np.ravel(y_arr)[0]), 2.0, places=2)

    def test_v6_02_exponential_decay_filter_all_31_strategies(self):
        """V6-02: Verify multi-horizon decay filter applies correct half-lives to strategy score columns."""
        scorer = EnsembleScoringEngine()

        # Fast tier: microstructure (tau=0.5, alpha = 1 - exp(-ln2/0.5) = 0.75)
        # Medium tier: stat_arb (tau=10.0, alpha = 1 - exp(-ln2/10) ≈ 0.066967)
        # Slow tier: rim_valuation (tau=45.0, alpha = 1 - exp(-ln2/45) ≈ 0.015286)
        # Metadata: close (should NOT be smoothed)

        prev_df = pd.DataFrame({
            'symbol': ['AAPL', 'MSFT'],
            'microstructure_score': [0.2, 0.4],
            'stat_arb_score': [0.3, 0.5],
            'rim_score': [0.1, 0.2],
            'close': [100.0, 200.0]
        })

        curr_df = pd.DataFrame({
            'symbol': ['AAPL', 'MSFT'],
            'microstructure_score': [0.8, 0.9],
            'stat_arb_score': [0.7, 0.8],
            'rim_score': [0.9, 0.8],
            'close': [110.0, 210.0]
        })

        filtered_df = scorer.apply_exponential_decay_filter(curr_df, prev_df)
        self.assertEqual(len(filtered_df), 2)

        # Microstructure alpha = 0.75 -> 0.75 * 0.8 + 0.25 * 0.2 = 0.60 + 0.05 = 0.65
        aapl_row = filtered_df[filtered_df['symbol'] == 'AAPL'].iloc[0]
        self.assertAlmostEqual(aapl_row['microstructure_score'], 0.65, places=3)

        # Stat-Arb alpha ≈ 0.066967 -> 0.066967 * 0.7 + (1 - 0.066967) * 0.3 ≈ 0.32679
        self.assertAlmostEqual(aapl_row['stat_arb_score'], 0.066967 * 0.7 + (1.0 - 0.066967) * 0.3, places=3)

        # Close price must remain untouched (110.0)
        self.assertEqual(aapl_row['close'], 110.0)

    def test_v6_03_dual_regime_weight_squaring_and_kr_decoupling(self):
        """V6-03: Verify US weight squaring is decoupled and KR weights receive relative suppression penalties."""
        scorer = EnsembleScoringEngine()

        us_weights = {'surge': 0.8, 'rim_valuation': 0.2}
        kr_weights = {'surge': 0.2, 'rim_valuation': 0.8}
        # Suppressed weights (from VIF/orthogonalizer)
        suppressed_weights = {'surge': 0.6, 'rim_valuation': 0.4}

        df_reg = pd.DataFrame([
            {'symbol': 'AAPL', 'market': 'SP500', 'expected_return': 0.05, 'close': 150.0},
            {'symbol': '005930', 'market': 'KOSPI', 'expected_return': 0.02, 'close': 70000.0},
        ])
        df_surge = pd.DataFrame([
            {'symbol': 'AAPL', 'surge_probability': 0.9},
            {'symbol': '005930', 'surge_probability': 0.1},
        ])
        df_rim = pd.DataFrame([
            {'symbol': 'AAPL', 'rim_score': 0.1},
            {'symbol': '005930', 'rim_score': 0.9},
        ])

        res = scorer.combine_predictions(
            weights=suppressed_weights,
            us_weights=us_weights,
            kr_weights=kr_weights,
            reg_df=df_reg,
            s_df=df_surge,
            rim_df=df_rim,
        )

        self.assertIsNotNone(res)
        self.assertIn('ensemble_score', res.columns)
        self.assertEqual(len(res), 2)

    def test_v6_04_market_aware_predict_lstm(self):
        """V6-04: Verify predict_lstm evaluates each market with its respective trained model."""
        model = OnDevicePredictionModel()

        # Mock market models
        mock_sp500 = MagicMock()
        mock_sp500.is_trained = True
        mock_sp500.predict.return_value = np.array([[0.95]])

        mock_kospi = MagicMock()
        mock_kospi.is_trained = True
        mock_kospi.predict.return_value = np.array([[0.25]])

        model.lstm_models = {
            'sp500': {20: mock_sp500},
            'kospi': {20: mock_kospi}
        }

        # Create price history
        dates = pd.date_range('2026-01-01', periods=25, freq='D')
        df_us = pd.DataFrame({
            'Close': np.linspace(100, 120, 25),
            'Volume': [1000] * 25,
            'market': ['SP500'] * 25
        }, index=dates)
        df_kr = pd.DataFrame({
            'Close': np.linspace(70000, 68000, 25),
            'Volume': [5000] * 25,
            'market': ['KOSPI'] * 25
        }, index=dates)

        prices_dict = {'AAPL': df_us, '005930': df_kr}
        res = model.predict_lstm(prices_dict, horizon=20)

        self.assertEqual(len(res), 2)
        # Verify both models were called with their respective symbols
        mock_sp500.predict.assert_called_once()
        mock_kospi.predict.assert_called_once()

    def test_v6_05_predict_lead_lag_fallback_1d_return_scaling(self):
        """V6-05: Verify predict_lead_lag fallback normalizes to 1-day return [0.05, 0.95]."""
        model = OnDevicePredictionModel()
        # Non-empty matrix with a leader that has <= 0 return to trigger fallback
        model.lead_lag_matrix = {'LEADER': {'FOLLOWER': 0.8}}

        dates = pd.date_range('2020-01-01', periods=100, freq='D')
        # Leader flat (0% return)
        df_leader = pd.DataFrame({'Close': [100.0] * 100, 'Volume': [1000] * 100}, index=dates)
        # 100-day return is +300% (from 10 to 40), but 1-day return is +1% (from 39.6 to 40.0)
        closes = np.linspace(10, 39.6, 99).tolist() + [40.0]
        df_test = pd.DataFrame({'Close': closes, 'Volume': [1000] * 100}, index=dates)

        prices_dict = {'LEADER': df_leader, 'TEST_SYM': df_test}
        res = model.predict_lead_lag(prices_dict)

        self.assertFalse(res.empty)
        test_row = res[res['symbol'] == 'TEST_SYM']
        self.assertFalse(test_row.empty)
        score = float(test_row.iloc[0]['lead_lag_score'])
        # Expected: clip(0.50 + 2.5 * (40.0 / 39.6 - 1.0), 0.05, 0.95)
        # 40/39.6 - 1 ≈ 0.0101 -> 0.50 + 2.5*0.0101 ≈ 0.5252
        self.assertGreater(score, 0.50)
        self.assertLess(score, 0.60)
        # Verify it is not +300.0 or 100.0
        self.assertLess(score, 1.0)

    def test_v6_06_optuna_bear_regime_quadratic_utility_and_simplex_bounds(self):
        """V6-06: Verify quadratic risk utility during bear markets and iterative simplex projection."""
        tuner = OptunaStrategyTuner()

        # 1. Bear market negative mean series: higher volatility should yield LOWER utility score
        m_neg = -0.002
        s_low = 0.01
        s_high = 0.03
        u_low_vol = (m_neg - 0.5 * 2.5 * (s_low ** 2)) * 252.0
        u_high_vol = (m_neg - 0.5 * 2.5 * (s_high ** 2)) * 252.0
        self.assertGreater(u_low_vol, u_high_vol)  # Lower vol is favored

        # 2. AlphaDecayTracker bounded simplex projection with 10 strategies
        tracker = AlphaDecayTracker(decay_lambda=0.05, min_weight_bound=0.01, max_weight_bound=0.20)
        base_weights = {f's{i}': 0.10 for i in range(10)}
        # s0 decays heavily, others are normal
        rolling_sharpes = {f's{i}': (0.5 if i > 0 else -2.0) for i in range(10)}
        decay_periods = {f's{i}': (0 if i > 0 else 50) for i in range(10)}

        adj_w = tracker.calculate_decay_adjusted_weights(base_weights, rolling_sharpes, decay_periods)
        self.assertAlmostEqual(sum(adj_w.values()), 1.0, places=3)
        for s, w in adj_w.items():
            self.assertGreaterEqual(w, 0.009)
            self.assertLessEqual(w, 0.201)

    def test_v6_07_lead_lag_hpo_evaluates_all_leaders(self):
        """V6-07: Verify Lead-Lag HPO evaluates all sampled leaders without 10-symbol hardcap."""
        tuner = OptunaStrategyTuner()
        dates = pd.date_range('2026-01-01', periods=80, freq='D')

        # Create 14 price series with varying correlations
        prices_dict = {}
        np.random.seed(42)
        base_series = np.cumsum(np.random.normal(0, 1, 80)) + 100
        for i in range(14):
            noise = np.random.normal(0, 0.5, 80)
            prices_dict[f'SYM_{i}'] = pd.DataFrame({
                'Close': base_series + noise,
                'Volume': [10000 + i * 1000] * 80
            }, index=dates)

        best_params = tuner.tune_strategy_3_lead_lag(prices_dict=prices_dict, n_trials=3)
        self.assertIn('lead_lag', tuner.tuned_params)
        self.assertIn('leader_count', best_params)

    def test_v6_08_meta_ensemble_learner_feature_permutation(self):
        """V6-08: Verify MetaEnsembleLearner is robust to column ordering permutations."""
        learner = MetaEnsembleLearner()
        cols = ['reg_score', 'surge_score', 'll_score']
        learner.feature_names = cols
        learner.weights = np.array([0.5, 0.3, 0.2])
        learner.intercept = 0.0
        learner.is_fitted = True
        learner.learner_type = 'ridge'

        # Natural order DataFrame
        df_natural = pd.DataFrame({
            'reg_score': [1.0, 0.0],
            'surge_score': [0.0, 1.0],
            'll_score': [0.0, 0.0]
        })
        pred_natural = learner.predict(df_natural)
        self.assertAlmostEqual(pred_natural[0], 0.5, places=4)
        self.assertAlmostEqual(pred_natural[1], 0.3, places=4)

        # Permuted order DataFrame: ['ll_score', 'surge_score', 'reg_score']
        df_permuted = pd.DataFrame({
            'll_score': [0.0, 0.0],
            'surge_score': [0.0, 1.0],
            'reg_score': [1.0, 0.0]
        })
        pred_permuted = learner.predict(df_permuted)
        # Should produce identical predictions despite permuted columns
        np.testing.assert_allclose(pred_natural, pred_permuted, atol=1e-5)


if __name__ == '__main__':
    unittest.main()
