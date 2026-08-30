"""
Comprehensive Unit & Regression Tests for System Issue Fixes:
1. PortfolioAllocator: NaN / Inf covariance fallback safety in EVT-CVaR & Turnover-regularized optimization
2. RiskManager: Missing 'close' column in intraday stop-loss evaluation
3. Stat-Arb: Zero variance / halted pair handling and Kalman filter Q matrix stability
4. FactorSuppression: Zero-weight and zero-sum entropy allocation & zero VIF damping safety
5. OptunaTuner: Empty / zero-sum simplex projection in alpha decay
6. TrendEfficiency: Flat price / zero range Hurst calculation safety
7. VolTarget: Parkinson volatility calculation with zero / identical prices
8. ScoreNormalizer: Duplicate DataFrame index handling
9. OMSEngine: Non-numeric / string change_pct parsing in order generation
"""

import unittest
import numpy as np
import pandas as pd

from src.risk.portfolio_allocator import PortfolioAllocator
from src.risk.risk_manager import RiskManager
from src.core.stat_arb import KalmanPairTracker, _estimate_half_life
from src.ai.factor_suppression import solve_single_stage_entropy_allocation, RegimeFactorSuppressionEngine
from src.ai.optuna_tuner import OptunaStrategyTuner, AlphaDecayTracker
from src.core.trend_efficiency import TrendEfficiencyEngine
from src.core.vol_target import VolTargetingEngine
from src.ai.score_normalizer import CrossSectionalScoreNormalizer
from src.execution.oms_engine import ExecutionOMSEngine


class TestSystemIssueFixesComprehensive(unittest.TestCase):

    def test_portfolio_allocator_nan_covariance_fallback(self):
        allocator = PortfolioAllocator()
        symbols = ['AAPL', 'MSFT', 'GOOG']
        rets = np.array([
            [0.01, 0.02, np.nan],
            [np.nan, 0.01, 0.03],
            [0.02, np.nan, 0.01],
            [0.01, 0.01, 0.02],
            [0.03, 0.02, 0.01],
            [0.01, 0.01, 0.01],
        ])
        returns_df = pd.DataFrame(rets, columns=symbols)
        expected_returns = pd.Series([0.05, 0.04, 0.03], index=symbols)

        weights_cvar = allocator.optimize_with_evt_cvar_constraint(
            expected_returns=expected_returns,
            returns_df=returns_df
        )
        self.assertEqual(len(weights_cvar), 3)
        for sym, w in weights_cvar.items():
            self.assertTrue(np.isfinite(w), f"Weight for {sym} is not finite: {w}")
            self.assertGreaterEqual(w, 0.0)

        weights_turnover = allocator.optimize_turnover_regularized_portfolio(
            expected_returns=expected_returns,
            returns_df=returns_df,
            previous_weights={'AAPL': 0.33, 'MSFT': 0.33, 'GOOG': 0.34}
        )
        self.assertEqual(len(weights_turnover), 3)
        for sym, w in weights_turnover.items():
            self.assertTrue(np.isfinite(w), f"Weight for {sym} is not finite: {w}")
            self.assertGreaterEqual(w, 0.0)

    def test_risk_manager_intraday_missing_close_column(self):
        rm = RiskManager()
        df_no_close = pd.DataFrame({
            'volume': [1000, 2000, 3000],
            'high': [105.0, 106.0, 107.0]
        })
        res = rm.evaluate_intraday_stop_loss("005930", df_no_close, entry_price=100.0)
        self.assertIsNotNone(res)
        self.assertEqual(res.symbol, "005930")

    def test_stat_arb_zero_returns_and_kalman_stability(self):
        tracker = KalmanPairTracker(delta_w=0.0001, v_e=0.001)
        res = tracker.update(100.0, 100.0)
        self.assertIn('beta_t', res)
        self.assertTrue(np.isfinite(res['beta_t']))

        # Test _estimate_half_life with short array, flat array, and synthetic AR(1)
        hl_short = _estimate_half_life(np.ones(5))
        self.assertEqual(hl_short, 999.0)

        # Flat residuals
        hl_flat = _estimate_half_life(np.ones(20))
        self.assertEqual(hl_flat, 999.0)

        # Mean-reverting synthetic residuals
        np.random.seed(42)
        ar1_res = np.zeros(50)
        for t in range(1, 50):
            ar1_res[t] = 0.5 * ar1_res[t-1] + np.random.normal(0, 0.1)
        hl_normal = _estimate_half_life(ar1_res)
        self.assertGreater(hl_normal, 0.0)
        self.assertLess(hl_normal, 999.0)

    def test_factor_suppression_zero_weights(self):
        R = np.eye(3)
        w0 = np.array([0.0, 0.0, 0.0])
        w = solve_single_stage_entropy_allocation(R, w0)
        self.assertEqual(len(w), 3)
        self.assertTrue(np.all(np.isfinite(w)))
        self.assertAlmostEqual(float(np.sum(w)), 1.0, places=4)

        engine = RegimeFactorSuppressionEngine()
        corr_mat = pd.DataFrame(np.eye(2), index=['s1', 's2'], columns=['s1', 's2'])
        vif_dict = {'s1': 0.0, 's2': 10.0}
        penalties = engine.compute_penalties(corr_mat, 'EXPANSION', vif_dict=vif_dict)
        self.assertIn('s1', penalties)
        self.assertTrue(np.isfinite(penalties['s1']))
        self.assertTrue(np.isfinite(penalties['s2']))

    def test_optuna_tuner_simplex_projection(self):
        tracker = AlphaDecayTracker()
        res_empty = tracker.calculate_decay_adjusted_weights({}, {})
        self.assertEqual(res_empty, {})

        base_w = {'strat_a': 0.0, 'strat_b': 0.0}
        sharpes = {'strat_a': 0.0, 'strat_b': 0.0}
        res_zero = tracker.calculate_decay_adjusted_weights(base_w, sharpes)
        self.assertEqual(len(res_zero), 2)
        self.assertTrue(all(np.isfinite(v) for v in res_zero.values()))

    def test_trend_efficiency_flat_series(self):
        engine = TrendEfficiencyEngine()
        universe = pd.DataFrame({
            'symbol': ['005930', '000660'],
            'market': ['KOSPI', 'KOSPI']
        })
        dates = pd.date_range('2026-01-01', periods=40)
        prices = {
            '005930': pd.DataFrame({'Close': np.full(40, 50000.0)}, index=dates),
            '000660': pd.DataFrame({'Close': np.full(40, 100000.0)}, index=dates)
        }
        res = engine.calculate_scores(universe, prices)
        self.assertFalse(res.empty)
        self.assertIn('005930', res['symbol'].values)
        self.assertIn('000660', res['symbol'].values)
        self.assertTrue(res['trend_efficiency_score'].notna().all())

    def test_vol_target_zero_and_missing_prices(self):
        engine = VolTargetingEngine(target_vol_annual=0.12)
        universe = pd.DataFrame({
            'symbol': ['AAPL', 'MSFT'],
            'name': ['Apple', 'Microsoft'],
            'market': ['SP500', 'SP500']
        })
        dates = pd.date_range('2026-01-01', periods=35)
        price_data = {
            'AAPL': pd.DataFrame({
                'Close': np.full(35, 150.0),
                'High': np.full(35, 150.0),
                'Low': np.full(35, 150.0)
            }, index=dates),
            'MSFT': pd.DataFrame({
                'Close': np.linspace(200.0, 220.0, 35)
            }, index=dates)
        }
        df_res = engine.compute_scores(universe, price_data)
        self.assertFalse(df_res.empty)
        self.assertTrue(df_res['vol_target_score'].notna().all())

    def test_score_normalizer_duplicate_index(self):
        normalizer = CrossSectionalScoreNormalizer(method='rank_percentile')
        df = pd.DataFrame({
            'symbol': ['A', 'B', 'C', 'D'],
            'market': ['US', 'US', 'US', 'US'],
            'strat_score': [0.1, 0.5, 0.8, 0.3]
        }, index=[0, 0, 1, 1])

        norm_df = normalizer.normalize_scores(df, strategy_cols=['strat_score'])
        self.assertEqual(len(norm_df), 4)
        self.assertTrue(norm_df['strat_score'].notna().all())
        self.assertTrue((norm_df['strat_score'] >= 0.0).all() and (norm_df['strat_score'] <= 1.0).all())

    def test_oms_engine_invalid_change_pct(self):
        oms = ExecutionOMSEngine()
        predictions = [{
            'symbol': '005930',
            'market': 'KOSPI',
            'ensemble_score': 0.85,
            'change_pct': 'N/A',
            'volatility_20d': 0.02,
            'expected_return': 0.05,
            'current_price': 70000.0,
            'target_shares': 10
        }]
        portfolio_weights = {'005930': 0.10}
        order_plan = oms.generate_order_plan(predictions, portfolio_weights, total_capital=10_000_000.0)
        self.assertIsInstance(order_plan, list)


if __name__ == '__main__':
    unittest.main()
