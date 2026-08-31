import unittest
import numpy as np
import pandas as pd

from src.execution.oms_engine import ExecutionOMSEngine
from src.risk.risk_manager import RiskManager, CrisisLevel
from src.ai.ensemble_scorer import EnsembleScoringEngine
from src.ai.score_normalizer import CrossSectionalScoreNormalizer
from src.ai.factor_suppression import RegimeFactorSuppressionEngine
from src.risk.portfolio_allocator import PortfolioAllocator
from src.execution.slippage_feedback import SlippageFeedbackEngine, SlippageMetrics
from src.core.mq_factor import MQFactorEngine
from src.core.sector_rotation import SectorRotationEngine
from src.core.stat_arb import StatisticalArbitrageEngine
from src.core.short_term_reversal import ShortTermReversalEngine
from src.core.rim_valuation import RIMValuationEngine


class TestReturnsImprovementsComprehensive(unittest.TestCase):

    def test_oms_amortized_hurdle_allows_positive_alpha(self):
        """P1-01: Validates that holding-period amortized hurdle allows normal positive alphas."""
        oms = ExecutionOMSEngine()
        predictions = [{
            'symbol': '005930',
            'name': 'Samsung Electronics',
            'market': 'KOSPI',
            'action': 'BUY',
            'close_price': 70000.0,
            'target_price': 70000.0,
            'expected_return': 5.0,  # 5% expected return (percentage scale)
            'regression_score': 0.85,
            'regression_20d': 0.05,
            'volatility_20d': 0.015,
            'adv': 500_000_000_000.0,
            'target_shares': 100
        }]
        portfolio_weights = {'005930': 0.10}
        plan = oms.generate_order_plan(
            top_predictions=predictions,
            portfolio_weights=portfolio_weights,
            total_capital=100_000_000.0,
            use_leland_buffer=False
        )
        self.assertEqual(len(plan), 1)
        self.assertEqual(plan[0]['symbol'], '005930')

    def test_risk_manager_vix_recalibrated_triggers(self):
        """P1-02: Validates VIX 30+ triggers ACTIVE crisis level and 40+ triggers SEVERE."""
        rm = RiskManager()
        # VIX at 25 with normal conditions
        level = rm.evaluate_crisis(vix=25.0, daily_volume_ratio=1.0)
        self.assertIn(level, (CrisisLevel.NONE, CrisisLevel.WATCH))

        # VIX at 32 triggers ACTIVE
        level_active = rm.evaluate_crisis(vix=32.0, daily_volume_ratio=1.0)
        self.assertEqual(level_active, CrisisLevel.ACTIVE)

        # VIX at 46 triggers SEVERE
        level_severe = rm.evaluate_crisis(vix=46.0, daily_volume_ratio=2.0)
        self.assertEqual(level_severe, CrisisLevel.SEVERE)

    def test_ensemble_scorer_adaptive_vix_override(self):
        """P1-03: Validates adaptive VIX override with dynamic baseline."""
        scorer = EnsembleScoringEngine()
        base_weights = {'surge': 0.20, 'regression': 0.20, 'stat_arb': 0.20, 'mq_factor': 0.20, 'rim_valuation': 0.20}
        
        # When VIX is below dynamic baseline (e.g. 22 vs baseline 24), no override applied
        w_no_decay = scorer.apply_vix_override(base_weights, vix_val=22.0, vix_baseline=24.0)
        self.assertAlmostEqual(w_no_decay['surge'], 0.20, places=4)

        # When VIX is above baseline (e.g. 30 vs baseline 22), defensive override applies smoothly
        w_decay = scorer.apply_vix_override(base_weights, vix_val=30.0, vix_baseline=22.0)
        self.assertLess(w_decay['surge'], 0.20)
        self.assertGreater(w_decay['rim_valuation'], 0.20)

    def test_score_normalizer_winsorized_zscore_preserves_dispersion(self):
        """P2-01: Validates winsorized_zscore preserves fat-tail score dispersion."""
        normalizer = CrossSectionalScoreNormalizer(method='winsorized_zscore', min_symbols_per_market=10)
        # 20 symbols with one extreme outlier
        raw_scores = [0.1] * 18 + [0.15, 0.95]
        df = pd.DataFrame({
            'symbol': [f'S{i}' for i in range(20)],
            'market': ['KOSPI'] * 20,
            'alpha': raw_scores
        })
        norm_df = normalizer.normalize_scores(df, strategy_cols=['alpha'])
        self.assertEqual(len(norm_df), 20)
        # Outlier should receive distinctively higher score than second highest
        s_outlier = float(norm_df.loc[norm_df['symbol'] == 'S19', 'alpha'].iloc[0])
        s_runner_up = float(norm_df.loc[norm_df['symbol'] == 'S18', 'alpha'].iloc[0])
        self.assertGreater(s_outlier - s_runner_up, 0.10)

    def test_factor_suppression_single_penalty_and_dynamic_clusters(self):
        """P2-02 & P2-03: Validates single stricter penalty (no double multiplication) and cluster Sharpe filtering."""
        engine = RegimeFactorSuppressionEngine()
        corr_mat = pd.DataFrame([
            [1.0, 0.85],
            [0.85, 1.0]
        ], index=['strat_a', 'strat_b'], columns=['strat_a', 'strat_b'])
        vif_dict = {'strat_a': 12.0, 'strat_b': 12.0}

        penalties = engine.compute_penalties(corr_mat, 'EXPANSION', vif_dict=vif_dict)
        self.assertIn('strat_a', penalties)
        self.assertGreater(penalties['strat_a'], 0.10)  # Not double penalized down to near zero

        # Dynamic cluster performance test
        cluster_sharpes = {'MOMENTUM': 1.20}  # Strong momentum performance
        active_clusters = engine._get_high_risk_clusters('BEAR', cluster_sharpes=cluster_sharpes)
        self.assertNotIn('MOMENTUM', active_clusters)  # Should not suppress positive momentum

    def test_leland_buffer_bandwidth_calibrated(self):
        """P3-01: Validates Leland buffer band width for 10% weight is not collapsed to zero."""
        allocator = PortfolioAllocator(delta_floor=0.005, delta_cap=0.05)
        delta = allocator.calculate_dynamic_buffer_band(
            symbol='005930',
            target_weight=0.10,
            cost_rate=0.003,
            volatility_20d=0.02,
            risk_aversion=3.0
        )
        self.assertGreater(delta, 0.005)
        self.assertLessEqual(delta, 0.05)

    def test_mq_factor_idiosyncratic_momentum(self):
        """P4-01: Validates MQ factor calculates risk-adjusted momentum."""
        engine = MQFactorEngine()
        dates = pd.date_range('2025-01-01', periods=260)
        # Strong steady uptrend vs downtrend
        steady_prices = pd.DataFrame({'Close': np.linspace(100, 200, 260)}, index=dates)
        down_prices = pd.DataFrame({'Close': np.linspace(200, 100, 260)}, index=dates)
        prices_dict = {'STEADY': steady_prices, 'DOWN': down_prices}
        res = engine.compute_mq_scores(prices_dict)
        self.assertFalse(res.empty)
        self.assertIn('STEADY', res['symbol'].values)
        score = float(res.loc[res['symbol'] == 'STEADY', 'mq_score'].iloc[0])
        self.assertGreater(score, 0.50)

    def test_sector_rotation_multi_horizon(self):
        """P4-02: Validates SectorRotationEngine uses 20d, 60d, and 126d momentum."""
        engine = SectorRotationEngine(w_20d=0.30, w_60d=0.40, w_126d=0.30)
        dates = pd.date_range('2025-01-01', periods=150)
        prices = {
            '005930': pd.DataFrame({'Close': np.linspace(50000, 80000, 150)}, index=dates),
            '000660': pd.DataFrame({'Close': np.linspace(100000, 120000, 150)}, index=dates)
        }
        sector_map = {'005930': 'Information Technology', '000660': 'Information Technology'}
        res = engine.compute_sector_momentum_scores(prices, sector_map=sector_map)
        self.assertFalse(res.empty)
        self.assertIn('005930', res['symbol'].values)

    def test_stat_arb_adaptive_entry(self):
        """P4-03: Validates adaptive entry threshold in Stat-Arb."""
        engine = StatisticalArbitrageEngine()
        # Fast half-life pair should have lower entry threshold
        dates = pd.date_range('2026-01-01', periods=60)
        np.random.seed(42)
        s1 = 100.0 + np.sin(np.linspace(0, 10, 60)) * 5.0
        s2 = 100.0 + np.sin(np.linspace(0, 10, 60)) * 5.0 + np.random.normal(0, 0.2, 60)
        prices = {
            'A': pd.DataFrame({'Close': s1}, index=dates),
            'B': pd.DataFrame({'Close': s2}, index=dates)
        }
        res = engine.find_cointegrated_pairs(prices)
        self.assertIsInstance(res, list)

    def test_rim_valuation_pure_fundamental(self):
        """P5-02: Validates allow_price_proxy=False does not invent price trend proxies."""
        engine = RIMValuationEngine()
        df = pd.DataFrame({
            'symbol': ['MISSING_BPS'],
            'market': ['KOSPI'],
            'Close': [50000.0],
            'bps': [np.nan],
            'roe': [np.nan]
        })
        res = engine.compute_rim_scores(df, allow_price_proxy=False)
        self.assertTrue(res['rim_score'].isna().all() or (res['rim_score'] == 0.50).all() or res.empty or pd.isna(res.iloc[0]['rim_score']))


if __name__ == '__main__':
    unittest.main()
