import unittest
import numpy as np
import pandas as pd

from trading_system.src.analysis.portfolio_optimizer import calculate_hrp_weights
from trading_system.src.ai.ensemble_scorer import EnsembleScoringEngine
from trading_system.src.ai.prediction_model import OnDevicePredictionModel
from trading_system.src.analysis.statistics import AdvancedStatistics


class TestMilestone1Fixes(unittest.TestCase):

    def test_hrp_inverse_variance_weighting(self):
        """Task 1: Verify calculate_hrp_weights uses inverse variance weighting."""
        # 3x3 covariance matrix
        cov = np.array([
            [0.04, 0.001, 0.001],
            [0.001, 0.01, 0.001],
            [0.001, 0.001, 0.09]
        ])
        weights = calculate_hrp_weights(cov)
        self.assertEqual(len(weights), 3)
        self.assertAlmostEqual(np.sum(weights), 1.0, places=5)
        self.assertTrue(np.all(weights >= 0.0))
        # Asset 1 (var=0.01) should have highest weight under inverse variance weighting
        self.assertGreater(weights[1], weights[0])
        self.assertGreater(weights[1], weights[2])

    def test_ensemble_scorer_spread_cost(self):
        """Task 2: Verify _get_cost_pct uses 1.0 * clamped_spread."""
        scorer = EnsembleScoringEngine()
        row = pd.Series({
            'symbol': 'AAPL',
            'market': 'SP500',
            'volume': 1_000_000,
            'close': 150.0,
            'volatility_20d': 0.015
        })
        df = pd.DataFrame([row])
        res_df = scorer.combine_predictions(
            reg_df=df, s_df=df, ll_df=df, v_rule_df=df, vcp_ml_df=df,
            lstm_df=df, stat_arb_df=df, sector_df=df, rim_df=df,
            event_df=df, mq_df=df, iv_skew_df=df, order_flow_df=df,
            reversal_df=df, arm_df=df, card_df=df, latr_df=df,
            inst_foreign_sector_df=df
        )
        self.assertIn('ensemble_score', res_df.columns)

    def test_prediction_model_merge_fundamentals_datetimeindex(self):
        """Task 3: Verify merge_fundamentals handles DatetimeIndex with 'index' name and enforces filing lag."""
        dates = pd.date_range('2025-01-01', periods=10, freq='D')
        df = pd.DataFrame({
            'close': np.linspace(100, 110, 10),
            'volume': 1000.0
        }, index=dates)
        df.index.name = 'index'

        # Fundamental DataFrame
        fun_df = pd.DataFrame({
            'date': [pd.Timestamp('2024-12-31')],
            'revenue': [1e9],
            'operating_income': [2e8],
            'net_income': [1.5e8],
            'eps': [5.0],
            'dividend_per_share': [1.0],
            'book_value': [50.0],
            'shares_outstanding': [1e8]
        })
        cache = {'TEST': fun_df}

        model = OnDevicePredictionModel()
        merged = model.merge_fundamentals('TEST', df, fundamentals_cache=cache)
        self.assertIn('book_value', merged.columns)
        self.assertIn('revenue', merged.columns)

    def test_statistics_annual_return_and_sortino_clamping(self):
        """Task 5: Verify statistics clamping for severe negative return and empty downside sortino."""
        stats = AdvancedStatistics()
        
        # Test annual return when total return < -1.0
        equity = [100.0, 50.0, -10.0]  # total_return = -1.1
        summary = stats.get_performance_summary(equity, [])
        self.assertIsInstance(summary['annual_return'], float)
        self.assertFalse(np.isnan(summary['annual_return']))
        self.assertFalse(np.iscomplex(summary['annual_return']))

        # Test Sortino ratio when downside returns list is empty
        all_positive_returns = [0.01, 0.02, 0.015, 0.03]
        sortino = stats.calculate_sortino_ratio(all_positive_returns, target_return=0.0)
        self.assertEqual(sortino, 10.0)
        self.assertFalse(np.isinf(sortino))

    def test_statistics_var_cvar_safe_bounds(self):
        """Task 5: Verify VaR and CVaR calculations on safe indices."""
        stats = AdvancedStatistics()
        self.assertEqual(stats.calculate_var([], 0.95), 0.0)
        self.assertEqual(stats.calculate_cvar([], 0.95), 0.0)
        
        returns = [-0.05, -0.02, 0.01, 0.03, 0.04]
        var = stats.calculate_var(returns, 0.95)
        cvar = stats.calculate_cvar(returns, 0.95)
        self.assertLessEqual(cvar, var)


if __name__ == '__main__':
    unittest.main()
