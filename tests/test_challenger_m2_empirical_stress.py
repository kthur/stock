"""
Milestone 2 Empirical Stress Test Suite: Ensemble Meta-Learner & Dynamic 2D/3D Regime Weighting.
Author: Empirical Challenger (teamwork_preview_challenger)

Scope:
1. Degenerate regimes (invalid regime codes, unknown strings, empty dict, None, NaN, corrupt objects).
2. All-zero predictions across all 34 strategies.
3. All-one predictions across all 34 strategies.
4. Missing strategy columns (0 strategies, partial 1..33 strategies, missing symbols, corrupt headers).
5. Extreme volatility regimes (BEAR_HIGH_VOL, VIX_SURGE > 80, CRISIS_DRAWDOWN, dual-market decoupling).
6. Collinear strategy signals (rank-1 identical, pairwise 1.0 correlation, zero variance, N < K singular).
7. Singular covariance matrix PCA-ZCA whitening & Tikhonov regularizer stability.
8. Strict finite score bounds guarantee [0.0, 1.0] across all edge cases.
"""

import os
import sys
import unittest
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../trading_system')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.ai.ensemble_scorer import EnsembleScoringEngine
from src.ai.factor_orthogonalizer import FactorOrthogonalizerEngine
from src.ai.factor_suppression import RegimeFactorSuppressionEngine
from src.ai.meta_ensemble_learner import MetaEnsembleLearner, STRATEGY_SCORE_COLS
from src.ai.score_normalizer import CrossSectionalScoreNormalizer


class TestMilestone2EmpiricalStress(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.ALL_34_STRATEGIES = [
            'regression', 'surge', 'lead_lag', 'vcp_rule', 'vcp_ml',
            'lstm', 'stat_arb', 'sector_rotation', 'rim_valuation', 'event_driven',
            'mq_factor', 'iv_skew', 'order_flow', 'short_term_reversal',
            'arm_factor', 'card_factor', 'latr_factor', 'inst_foreign_sector',
            'supply_chain', 'sentiment', 'factor_neutralized', 'vol_target',
            'microstructure', 'accruals_quality', 'short_squeeze', 'valueup_catalyst',
            'trend_efficiency', 'gamma_squeeze', 'insider_buying', 'darkpool',
            'earnings_tone_drift', 'cross_asset_spillover', 'supply_chain_gnn',
            'range_expansion_breakout'
        ]
        cls.ALL_34_SCORE_COLS = [
            'reg_score', 'surge_score', 'll_score', 'vcp_rule_score', 'vcp_ml_score',
            'lstm_score', 'stat_arb_score', 'sector_score', 'rim_score', 'event_score',
            'mq_score', 'iv_skew_score', 'order_flow_score', 'reversal_score',
            'arm_score', 'card_score', 'latr_score', 'inst_foreign_sector_score',
            'supply_chain_score', 'sentiment_score', 'factor_neutralized_score', 'vol_target_score',
            'microstructure_score', 'accruals_quality_score', 'short_squeeze_score', 'valueup_catalyst_score',
            'trend_efficiency_score', 'gamma_squeeze_score', 'insider_buying_score', 'darkpool_score',
            'earnings_tone_drift_score', 'cross_asset_spillover_score', 'supply_chain_gnn_score',
            'range_expansion_score'
        ]

    def setUp(self):
        self.engine = EnsembleScoringEngine(alpha_smoothing=0.2)
        self.ortho = FactorOrthogonalizerEngine(default_method='pca_symmetric')
        self.normalizer = CrossSectionalScoreNormalizer()

    def _create_34_strategy_dfs(self, symbols, fill_value=0.5):
        dfs = {}
        for s_name, col_name in zip(self.ALL_34_STRATEGIES, self.ALL_34_SCORE_COLS):
            df = pd.DataFrame({
                'symbol': symbols,
                col_name: [fill_value(i) if callable(fill_value) else fill_value for i in range(len(symbols))]
            })
            if s_name == 'regression':
                df[20] = df[col_name]
            elif s_name == 'surge':
                df['surge_prob_20d'] = df[col_name]
            elif s_name == 'vcp_ml':
                df['vcp_prob_20d'] = df[col_name]
            elif s_name == 'lead_lag':
                df['lead_lag_score'] = df[col_name]
            dfs[s_name] = df
        return dfs

    # =========================================================================
    # 1. Degenerate Regimes & Weight Conservation Verification
    # =========================================================================

    def test_2d_regime_weights_conservation_and_positivity(self):
        regimes_2d = ['BEAR_LOW_VOL', 'BEAR_HIGH_VOL', 'SIDEWAYS_LOW_VOL', 'SIDEWAYS_HIGH_VOL', 'BULL_LOW_VOL', 'BULL_HIGH_VOL']
        for r_name in regimes_2d:
            weights = EnsembleScoringEngine.REGIME_2D_WEIGHTS.get(r_name, {})
            self.assertEqual(len(weights), 34, f'Regime {r_name} does not have exactly 34 strategy weights')
            w_sum = sum(weights.values())
            self.assertAlmostEqual(w_sum, 1.0, places=5, msg=f'Regime {r_name} weights sum to {w_sum}, expected 1.000')
            for strat, w in weights.items():
                self.assertGreater(w, 0.0, f'Strategy {strat} weight in {r_name} is non-positive: {w}')
                self.assertTrue(np.isfinite(w), f'Strategy {strat} weight in {r_name} is non-finite: {w}')

    def test_1d_regime_weights_conservation_and_positivity(self):
        for r_code in [0, 1, 2]:
            weights = EnsembleScoringEngine.REGIME_WEIGHTS.get(r_code, {})
            self.assertEqual(len(weights), 34, f'1D Regime {r_code} does not have exactly 34 strategy weights')
            w_sum = sum(weights.values())
            self.assertAlmostEqual(w_sum, 1.0, places=5, msg=f'1D Regime {r_code} weights sum to {w_sum}, expected 1.000')
            for strat, w in weights.items():
                self.assertGreater(w, 0.0, f'Strategy {strat} weight in 1D {r_code} is non-positive: {w}')

    def test_degenerate_and_corrupted_regime_inputs(self):
        symbols = [f'SYM_{i:02d}' for i in range(10)]
        dfs = self._create_34_strategy_dfs(symbols, fill_value=lambda i: 0.1 * (i + 1))

        corrupt_regimes = [
            None,
            -1,
            999,
            'INVALID_UNKNOWN_REGIME_NAME',
            float('nan'),
            {},
            {'invalid_key': 'invalid_value'},
            {'direction_code': 999, 'combo_2d_label': 'INVALID_2D'},
            '',
            100.5,
        ]

        for reg in corrupt_regimes:
            try:
                res = self.engine.calculate_ensemble_score(
                    regime=reg,
                    regression_df=dfs['regression'],
                    surge_df=dfs['surge'],
                    lead_lag_df=dfs['lead_lag'],
                    vcp_ml_df=dfs['vcp_ml'],
                    stat_arb_df=dfs['stat_arb'],
                    sector_df=dfs['sector_rotation'],
                    rim_df=dfs['rim_valuation'],
                    event_df=dfs['event_driven'],
                    mq_df=dfs['mq_factor'],
                    iv_skew_df=dfs['iv_skew'],
                    order_flow_df=dfs['order_flow'],
                    reversal_df=dfs['short_term_reversal'],
                    arm_df=dfs['arm_factor'],
                    card_df=dfs['card_factor'],
                    latr_df=dfs['latr_factor'],
                    inst_foreign_sector_df=dfs['inst_foreign_sector'],
                    supply_chain_df=dfs['supply_chain'],
                    sentiment_df=dfs['sentiment'],
                    factor_neutralized_df=dfs['factor_neutralized'],
                    vol_target_df=dfs['vol_target'],
                    microstructure_df=dfs['microstructure'],
                    accruals_quality_df=dfs['accruals_quality'],
                    short_squeeze_df=dfs['short_squeeze'],
                    valueup_catalyst_df=dfs['valueup_catalyst'],
                    trend_efficiency_df=dfs['trend_efficiency'],
                    gamma_squeeze_df=dfs['gamma_squeeze'],
                    insider_buying_df=dfs['insider_buying'],
                    darkpool_df=dfs['darkpool'],
                    earnings_tone_drift_df=dfs['earnings_tone_drift'],
                    cross_asset_spillover_df=dfs['cross_asset_spillover'],
                    supply_chain_gnn_df=dfs['supply_chain_gnn'],
                    range_expansion_breakout_df=dfs['range_expansion_breakout'],
                    target_horizon=20
                )
                self.assertFalse(res.empty, f'Empty result returned for regime: {reg}')
                self.assertIn('ensemble_score', res.columns)
                scores = res['ensemble_score'].to_numpy()
                self.assertTrue(np.all(np.isfinite(scores)), f'Non-finite scores in degenerate regime: {reg}')
                self.assertTrue(np.all((scores >= 0.0) & (scores <= 1.0)), f'Out-of-bounds scores in degenerate regime: {reg}')
            except Exception as e:
                self.fail(f'calculate_ensemble_score raised unhandled exception for degenerate regime {reg}: {e}')

    # =========================================================================
    # 2. All-Zero and All-One Predictions Stress Testing
    # =========================================================================

    def test_all_zero_predictions_across_34_strategies(self):
        symbols = [f'SYM_{i:03d}' for i in range(50)]
        dfs = self._create_34_strategy_dfs(symbols, fill_value=0.0)

        res = self.engine.calculate_ensemble_score(
            regime='SIDEWAYS_LOW_VOL',
            regression_df=dfs['regression'],
            surge_df=dfs['surge'],
            lead_lag_df=dfs['lead_lag'],
            vcp_ml_df=dfs['vcp_ml'],
            lstm_df=dfs['lstm'],
            stat_arb_df=dfs['stat_arb'],
            sector_df=dfs['sector_rotation'],
            rim_df=dfs['rim_valuation'],
            event_df=dfs['event_driven'],
            mq_df=dfs['mq_factor'],
            iv_skew_df=dfs['iv_skew'],
            order_flow_df=dfs['order_flow'],
            reversal_df=dfs['short_term_reversal'],
            arm_df=dfs['arm_factor'],
            card_df=dfs['card_factor'],
            latr_df=dfs['latr_factor'],
            inst_foreign_sector_df=dfs['inst_foreign_sector'],
            supply_chain_df=dfs['supply_chain'],
            sentiment_df=dfs['sentiment'],
            factor_neutralized_df=dfs['factor_neutralized'],
            vol_target_df=dfs['vol_target'],
            microstructure_df=dfs['microstructure'],
            accruals_quality_df=dfs['accruals_quality'],
            short_squeeze_df=dfs['short_squeeze'],
            valueup_catalyst_df=dfs['valueup_catalyst'],
            trend_efficiency_df=dfs['trend_efficiency'],
            gamma_squeeze_df=dfs['gamma_squeeze'],
            insider_buying_df=dfs['insider_buying'],
            darkpool_df=dfs['darkpool'],
            earnings_tone_drift_df=dfs['earnings_tone_drift'],
            cross_asset_spillover_df=dfs['cross_asset_spillover'],
            supply_chain_gnn_df=dfs['supply_chain_gnn'],
            range_expansion_breakout_df=dfs['range_expansion_breakout'],
            target_horizon=20
        )

        self.assertEqual(len(res), 50)
        scores = res['ensemble_score'].to_numpy()
        self.assertTrue(np.all(np.isfinite(scores)), 'All-zero input produced non-finite ensemble scores')
        self.assertTrue(np.all(scores >= 0.0), 'All-zero input produced negative ensemble scores')
        self.assertTrue(np.all(scores <= 1.0), 'All-zero input produced scores > 1.0')
        self.assertAlmostEqual(float(np.std(scores)), 0.0, places=4)

    def test_all_one_predictions_across_34_strategies(self):
        symbols = [f'SYM_{i:03d}' for i in range(50)]
        dfs = self._create_34_strategy_dfs(symbols, fill_value=1.0)

        res = self.engine.calculate_ensemble_score(
            regime='BULL_HIGH_VOL',
            regression_df=dfs['regression'],
            surge_df=dfs['surge'],
            lead_lag_df=dfs['lead_lag'],
            vcp_ml_df=dfs['vcp_ml'],
            lstm_df=dfs['lstm'],
            stat_arb_df=dfs['stat_arb'],
            sector_df=dfs['sector_rotation'],
            rim_df=dfs['rim_valuation'],
            event_df=dfs['event_driven'],
            mq_df=dfs['mq_factor'],
            iv_skew_df=dfs['iv_skew'],
            order_flow_df=dfs['order_flow'],
            reversal_df=dfs['short_term_reversal'],
            arm_df=dfs['arm_factor'],
            card_df=dfs['card_factor'],
            latr_df=dfs['latr_factor'],
            inst_foreign_sector_df=dfs['inst_foreign_sector'],
            supply_chain_df=dfs['supply_chain'],
            sentiment_df=dfs['sentiment'],
            factor_neutralized_df=dfs['factor_neutralized'],
            vol_target_df=dfs['vol_target'],
            microstructure_df=dfs['microstructure'],
            accruals_quality_df=dfs['accruals_quality'],
            short_squeeze_df=dfs['short_squeeze'],
            valueup_catalyst_df=dfs['valueup_catalyst'],
            trend_efficiency_df=dfs['trend_efficiency'],
            gamma_squeeze_df=dfs['gamma_squeeze'],
            insider_buying_df=dfs['insider_buying'],
            darkpool_df=dfs['darkpool'],
            earnings_tone_drift_df=dfs['earnings_tone_drift'],
            cross_asset_spillover_df=dfs['cross_asset_spillover'],
            supply_chain_gnn_df=dfs['supply_chain_gnn'],
            range_expansion_breakout_df=dfs['range_expansion_breakout'],
            target_horizon=20
        )

        self.assertEqual(len(res), 50)
        scores = res['ensemble_score'].to_numpy()
        self.assertTrue(np.all(np.isfinite(scores)), 'All-one input produced non-finite ensemble scores')
        self.assertTrue(np.all(scores >= 0.0), 'All-one input produced negative ensemble scores')
        self.assertTrue(np.all(scores <= 1.0), 'All-one input produced scores > 1.0')
        self.assertAlmostEqual(float(np.std(scores)), 0.0, places=4)

    # =========================================================================
    # 3. Missing Strategy Columns & Missingness-Aware Zero-Weighting
    # =========================================================================

    def test_zero_strategy_dataframes_provided(self):
        res = self.engine.calculate_ensemble_score(regime='SIDEWAYS_LOW_VOL')
        self.assertIsInstance(res, pd.DataFrame)
        if not res.empty:
            self.assertIn('symbol', res.columns)

    def test_single_strategy_provided(self):
        symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN']
        reg_df = pd.DataFrame({'symbol': symbols, 20: [0.15, 0.05, 0.08, -0.02]})

        res = self.engine.calculate_ensemble_score(
            regime='BEAR_LOW_VOL',
            regression_df=reg_df,
            target_horizon=20
        )

        self.assertEqual(len(res), 4)
        self.assertIn('ensemble_score', res.columns)
        scores = res['ensemble_score'].to_numpy()
        self.assertTrue(np.all(np.isfinite(scores)))
        self.assertTrue(np.all((scores >= 0.0) & (scores <= 1.0)))
        self.assertEqual(res.iloc[0]['symbol'], 'AAPL')
        self.assertEqual(res.iloc[-1]['symbol'], 'AMZN')

    def test_sparse_random_missingness_across_34_strategies(self):
        np.random.seed(42)
        symbols = [f'SYM_{i:04d}' for i in range(100)]
        dfs = self._create_34_strategy_dfs(symbols, fill_value=lambda i: np.random.uniform(0.0, 1.0))

        active_strategies = np.random.choice(self.ALL_34_STRATEGIES, size=9, replace=False)
        kwargs = {'regime': 'SIDEWAYS_HIGH_VOL', 'target_horizon': 20}
        for st in self.ALL_34_STRATEGIES:
            if st in active_strategies:
                arg_name = f'{st}_df' if not st.startswith('vcp_') and st not in ['regression', 'surge', 'lead_lag', 'sector_rotation', 'rim_valuation', 'event_driven', 'cross_asset_spillover', 'supply_chain_gnn', 'range_expansion_breakout'] else {
                    'regression': 'regression_df',
                    'surge': 'surge_df',
                    'lead_lag': 'lead_lag_df',
                    'vcp_ml': 'vcp_ml_df',
                    'vcp_rule': 'vcp_rule_df',
                    'sector_rotation': 'sector_df',
                    'rim_valuation': 'rim_df',
                    'event_driven': 'event_df',
                    'cross_asset_spillover': 'cross_asset_spillover_df',
                    'supply_chain_gnn': 'supply_chain_gnn_df',
                    'range_expansion_breakout': 'range_expansion_breakout_df'
                }.get(st, f'{st}_df')
                df_copy = dfs[st].copy()
                col = [c for c in df_copy.columns if c != 'symbol'][0]
                nan_mask = np.random.rand(len(df_copy)) < 0.40
                df_copy.loc[nan_mask, col] = np.nan
                kwargs[arg_name] = df_copy

        res = self.engine.calculate_ensemble_score(**kwargs)
        self.assertFalse(res.empty)
        scores = res['ensemble_score'].to_numpy()
        self.assertTrue(np.all(np.isfinite(scores)), 'Sparse missingness produced NaN/Inf ensemble scores')
        self.assertTrue(np.all((scores >= 0.0) & (scores <= 1.0)), 'Sparse missingness produced out-of-bounds scores')

    # =========================================================================
    # 4. Extreme Volatility, Macro Regimes & Decoupling Tilts
    # =========================================================================

    def test_extreme_3d_macro_regimes_and_modifiers(self):
        symbols = [f'SYM_{i:02d}' for i in range(20)]
        dfs = self._create_34_strategy_dfs(symbols, fill_value=lambda i: 0.05 * (i + 1))

        macro_labels = [
            'VIX_SURGE', 'RISING_YIELDS', 'DOLLAR_SURGE', 'INFLATION_SHOCK', 'YIELD_INVERSION',
            'LIQUIDITY_SQUEEZE', 'CRISIS_DRAWDOWN'
        ]

        for m_label in macro_labels:
            macro_3d_dict = {
                'direction_code': 0,
                'direction_label': 'BEAR',
                'volatility_label': 'HIGH_VOL',
                'combo_2d_label': 'BEAR_HIGH_VOL',
                'macro_label': m_label,
                'combo_3d_label': f'BEAR_HIGH_VOL_{m_label}'
            }

            res = self.engine.calculate_ensemble_score(
                regime=macro_3d_dict,
                regression_df=dfs['regression'],
                surge_df=dfs['surge'],
                lead_lag_df=dfs['lead_lag'],
                vcp_ml_df=dfs['vcp_ml'],
                cross_asset_spillover_df=dfs['cross_asset_spillover'],
                supply_chain_gnn_df=dfs['supply_chain_gnn'],
                range_expansion_breakout_df=dfs['range_expansion_breakout'],
                target_horizon=20
            )

            self.assertEqual(len(res), 20)
            scores = res['ensemble_score'].to_numpy()
            self.assertTrue(np.all(np.isfinite(scores)), f'Non-finite scores under 3D macro {m_label}')
            self.assertTrue(np.all((scores >= 0.0) & (scores <= 1.0)), f'Out-of-bounds scores under 3D macro {m_label}')

    def test_us_kr_market_decoupling_alpha_tilts(self):
        symbols = ['AAPL', '005930', 'NVDA', '000660']
        dfs = self._create_34_strategy_dfs(symbols, fill_value=0.6)

        dual_regimes = {
            'us_regime': {'combo_2d_label': 'BULL_HIGH_VOL'},
            'kr_regime': {'combo_2d_label': 'BEAR_LOW_VOL'},
            'decoupling_status': 'DECOUPLING_US_BULL_KR_BEAR'
        }

        res = self.engine.calculate_ensemble_score(
            dual_regimes=dual_regimes,
            regression_df=dfs['regression'],
            surge_df=dfs['surge'],
            lead_lag_df=dfs['lead_lag'],
            vcp_ml_df=dfs['vcp_ml'],
            range_expansion_breakout_df=dfs['range_expansion_breakout'],
            target_horizon=20
        )

        self.assertEqual(len(res), 4)
        scores = res['ensemble_score'].to_numpy()
        self.assertTrue(np.all(np.isfinite(scores)))
        self.assertTrue(np.all((scores >= 0.0) & (scores <= 1.0)))

    # =========================================================================
    # 5. Collinear Strategy Signals & Singular PCA-ZCA Whitening (Tikhonov Test)
    # =========================================================================

    def test_singular_covariance_matrix_tikhonov_regularizer_pca_zca(self):
        N = 100
        K = 34
        cols = self.ALL_34_SCORE_COLS

        base_signal = np.linspace(0.1, 0.9, N)
        singular_matrix = np.column_stack([base_signal for _ in range(K)])
        df_singular = pd.DataFrame(singular_matrix, columns=cols)
        df_singular['symbol'] = [f'SYM_{i:04d}' for i in range(N)]

        for method in ['pca_symmetric', 'gram_schmidt', 'esrw']:
            res = self.ortho.orthogonalize(df_singular, cols, method=method)
            vals = res[cols].to_numpy()

            self.assertFalse(np.isnan(vals).any(), f'NaN generated by {method} on singular covariance matrix')
            self.assertFalse(np.isinf(vals).any(), f'Inf generated by {method} on singular covariance matrix')
            self.assertTrue(np.all(vals >= 0.0), f'Negative scores generated by {method} on singular matrix')
            self.assertTrue(np.all(vals <= 1.0), f'Scores > 1.0 generated by {method} on singular matrix')

    def test_n_less_than_k_high_dimensional_singularity(self):
        N = 5
        K = 34
        cols = self.ALL_34_SCORE_COLS

        matrix_n_less_k = np.random.uniform(0.1, 0.9, (N, K))
        df_n_less_k = pd.DataFrame(matrix_n_less_k, columns=cols)
        df_n_less_k['symbol'] = [f'SYM_{i:02d}' for i in range(N)]

        for method in ['pca_symmetric', 'gram_schmidt', 'esrw']:
            res = self.ortho.orthogonalize(df_n_less_k, cols, method=method)
            vals = res[cols].to_numpy()

            self.assertFalse(np.isnan(vals).any(), f'NaN generated in N < K test by {method}')
            self.assertFalse(np.isinf(vals).any(), f'Inf generated in N < K test by {method}')
            self.assertTrue(np.all((vals >= 0.0) & (vals <= 1.0)))

    def test_zero_variance_columns_in_whitening(self):
        N = 80
        cols = self.ALL_34_SCORE_COLS
        matrix = np.random.uniform(0.2, 0.8, (N, len(cols)))
        matrix[:, 0] = 0.0
        matrix[:, 1] = 1.0
        matrix[:, 2] = 0.5
        matrix[:, 3] = 0.0
        matrix[:, 31] = 0.0
        matrix[:, 32] = 0.5
        matrix[:, 33] = 1.0

        df = pd.DataFrame(matrix, columns=cols)
        df['symbol'] = [f'SYM_{i:04d}' for i in range(N)]

        for method in ['pca_symmetric', 'gram_schmidt', 'esrw']:
            res = self.ortho.orthogonalize(df, cols, method=method)
            vals = res[cols].to_numpy()

            self.assertFalse(np.isnan(vals).any(), f'NaN generated in zero-variance test by {method}')
            self.assertFalse(np.isinf(vals).any(), f'Inf generated in zero-variance test by {method}')
            self.assertTrue(np.all((vals >= 0.0) & (vals <= 1.0)))

    def test_end_to_end_collinear_signals_ensemble_pipeline(self):
        symbols = [f'SYM_{i:03d}' for i in range(40)]
        latent = np.linspace(0.1, 0.9, 40)
        dfs = self._create_34_strategy_dfs(symbols, fill_value=lambda i: latent[i])

        res = self.engine.calculate_ensemble_score(
            regime='BULL_LOW_VOL',
            regression_df=dfs['regression'],
            surge_df=dfs['surge'],
            lead_lag_df=dfs['lead_lag'],
            vcp_ml_df=dfs['vcp_ml'],
            lstm_df=dfs['lstm'],
            stat_arb_df=dfs['stat_arb'],
            sector_df=dfs['sector_rotation'],
            rim_df=dfs['rim_valuation'],
            event_df=dfs['event_driven'],
            mq_df=dfs['mq_factor'],
            iv_skew_df=dfs['iv_skew'],
            order_flow_df=dfs['order_flow'],
            reversal_df=dfs['short_term_reversal'],
            arm_df=dfs['arm_factor'],
            card_df=dfs['card_factor'],
            latr_df=dfs['latr_factor'],
            inst_foreign_sector_df=dfs['inst_foreign_sector'],
            supply_chain_df=dfs['supply_chain'],
            sentiment_df=dfs['sentiment'],
            factor_neutralized_df=dfs['factor_neutralized'],
            vol_target_df=dfs['vol_target'],
            microstructure_df=dfs['microstructure'],
            accruals_quality_df=dfs['accruals_quality'],
            short_squeeze_df=dfs['short_squeeze'],
            valueup_catalyst_df=dfs['valueup_catalyst'],
            trend_efficiency_df=dfs['trend_efficiency'],
            gamma_squeeze_df=dfs['gamma_squeeze'],
            insider_buying_df=dfs['insider_buying'],
            darkpool_df=dfs['darkpool'],
            earnings_tone_drift_df=dfs['earnings_tone_drift'],
            cross_asset_spillover_df=dfs['cross_asset_spillover'],
            supply_chain_gnn_df=dfs['supply_chain_gnn'],
            range_expansion_breakout_df=dfs['range_expansion_breakout'],
            target_horizon=20
        )

        self.assertEqual(len(res), 40)
        scores = res['ensemble_score'].to_numpy()
        self.assertTrue(np.all(np.isfinite(scores)))
        self.assertTrue(np.all((scores >= 0.0) & (scores <= 1.0)))
        self.assertEqual(res.iloc[0]['symbol'], 'SYM_039')
        self.assertEqual(res.iloc[-1]['symbol'], 'SYM_000')

    # =========================================================================
    # 6. Meta-Learner & Factor Suppression Matrix Integrity for 34 Strategies
    # =========================================================================

    def test_meta_ensemble_learner_with_all_34_strategies(self):
        import tempfile
        from pathlib import Path
        temp_dir = Path(tempfile.mkdtemp())
        learner = MetaEnsembleLearner(model_dir=temp_dir)

        self.assertIn('cross_asset_spillover_score', STRATEGY_SCORE_COLS)
        self.assertIn('supply_chain_gnn_score', STRATEGY_SCORE_COLS)
        self.assertIn('range_expansion_score', STRATEGY_SCORE_COLS)

        hist_df = pd.DataFrame({col: np.random.uniform(0, 1, 60) for col in STRATEGY_SCORE_COLS})
        hist_df['target_return'] = (hist_df['reg_score'] > 0.5).astype(float)

        success = learner.auto_rolling_retrain(hist_df, target_col='target_return')
        self.assertTrue(success, 'MetaEnsembleLearner failed auto_rolling_retrain with 34 strategies')

        test_row = pd.DataFrame({col: [0.8] for col in STRATEGY_SCORE_COLS})
        pred_meta = learner.predict(test_row)
        self.assertTrue(np.all(np.isfinite(pred_meta)))
        self.assertTrue(np.all((pred_meta >= 0.0) & (pred_meta <= 1.0)))

    def test_factor_suppression_with_34_strategies_and_momentum_cluster(self):
        suppression = RegimeFactorSuppressionEngine()
        corr_matrix = pd.DataFrame(
            np.eye(34),
            index=self.ALL_34_STRATEGIES,
            columns=self.ALL_34_STRATEGIES
        )
        corr_matrix.loc['supply_chain_gnn', 'cross_asset_spillover'] = 0.92
        corr_matrix.loc['cross_asset_spillover', 'supply_chain_gnn'] = 0.92

        base_weights = EnsembleScoringEngine.REGIME_2D_WEIGHTS['BULL_LOW_VOL'].copy()
        suppressed = suppression.suppress_weights(
            base_weights=base_weights,
            corr_matrix=corr_matrix,
            regime_label='BULL_LOW_VOL'
        )

        self.assertEqual(len(suppressed), 34)
        w_sum = sum(suppressed.values())
        self.assertAlmostEqual(w_sum, 1.0, places=4)
        for st, w in suppressed.items():
            self.assertGreater(w, 0.0)
            self.assertTrue(np.isfinite(w))


if __name__ == '__main__':
    unittest.main()
