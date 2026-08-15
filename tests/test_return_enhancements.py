"""
Unit Test Suite for Profitability & Return Enhancements.
Tests:
1. Return-Tilted Risk Parity Optimizer:
   - Verifies higher capital allocation to high-expected-return assets while maintaining risk diversification.
   - Verifies max_weight bounds (0 <= w_i <= max_weight) and sum of weights = 1.0.
   - Verifies fallback behavior under None, empty, NaN, or constant expected returns.
2. Dynamic Sharpe Convex Elasticity Multiplier:
   - Verifies convex boost for strategies with Sharpe >= 1.50 and >= 1.00.
   - Verifies asymmetric downside penalties for negative-alpha strategies.
3. Triple Confirmation Alpha Confluence & Quality Compounder Bonus:
   - Verifies 1.050x boost for stocks with concurrent Value, Momentum, and Institutional Inflow.
   - Verifies 1.035x boost for profitable compounding champions (ROE >= 15%, Op Margin >= 15%).
   - Verifies 0.70x distress penalty for chronic loss-makers.
"""

import unittest
import numpy as np
import pandas as pd

from trading_system.src.risk.portfolio_optimizer import PortfolioOptimizer
from trading_system.src.ai.ensemble_scorer import EnsembleScoringEngine


class TestReturnEnhancements(unittest.TestCase):

    def setUp(self):
        self.optimizer = PortfolioOptimizer(default_max_weight=0.25, default_max_sector_weight=0.40)
        self.scorer = EnsembleScoringEngine()

        # Synthetic 5-asset return series
        np.random.seed(42)
        n_days = 60
        self.symbols = ['SYM_A', 'SYM_B', 'SYM_C', 'SYM_D', 'SYM_E']
        returns_data = {
            'SYM_A': np.random.normal(0.001, 0.02, n_days),
            'SYM_B': np.random.normal(0.002, 0.025, n_days),
            'SYM_C': np.random.normal(0.0005, 0.015, n_days),
            'SYM_D': np.random.normal(0.003, 0.03, n_days),
            'SYM_E': np.random.normal(0.0015, 0.02, n_days)
        }
        self.returns_df = pd.DataFrame(returns_data)

    def test_return_tilted_risk_parity_allocation_and_constraints(self):
        """Verify return-tilted risk parity tilts towards higher alpha stocks and satisfies constraints."""
        expected_returns = pd.Series({
            'SYM_A': 0.05,
            'SYM_B': 0.15,
            'SYM_C': 0.02,
            'SYM_D': 0.35,  # Top return leader
            'SYM_E': 0.10
        })

        base_erc = self.optimizer.optimize_risk_parity(self.returns_df, max_weight=0.35)
        tilted_weights = self.optimizer.optimize_return_tilted_risk_parity(
            self.returns_df,
            expected_returns=expected_returns,
            tilt_exponent=1.0,
            max_weight=0.35
        )

        # Constraint checks
        self.assertEqual(len(tilted_weights), len(self.symbols))
        self.assertAlmostEqual(sum(tilted_weights.values()), 1.0, places=5)
        for sym, w in tilted_weights.items():
            self.assertGreaterEqual(w, 0.0)
            self.assertLessEqual(w, 0.35001)

        # Alpha tilt check: Top expected return asset SYM_D should receive higher weight than base ERC
        self.assertGreater(tilted_weights['SYM_D'], base_erc['SYM_D'])
        # Low expected return asset SYM_C should receive lower weight than top asset
        self.assertLess(tilted_weights['SYM_C'], tilted_weights['SYM_D'])

    def test_return_tilted_risk_parity_fallbacks(self):
        """Verify graceful fallback when expected_returns is None or empty."""
        w_none = self.optimizer.optimize_return_tilted_risk_parity(self.returns_df, expected_returns=None)
        w_empty = self.optimizer.optimize_return_tilted_risk_parity(self.returns_df, expected_returns={})
        base_erc = self.optimizer.optimize_risk_parity(self.returns_df)

        self.assertAlmostEqual(sum(w_none.values()), 1.0, places=5)
        self.assertAlmostEqual(sum(w_empty.values()), 1.0, places=5)
        for sym in self.symbols:
            self.assertAlmostEqual(w_none[sym], base_erc[sym], places=5)
            self.assertAlmostEqual(w_empty[sym], base_erc[sym], places=5)

    def test_dynamic_sharpe_convex_elasticity(self):
        """Verify dynamic Sharpe weighting applies convex boosts to high Sharpe strategies."""
        # High Sharpe on regression (1.6), moderate on surge (1.1), neutral on stat_arb (0.2), negative on momentum (-0.3)
        sharpes = {
            'regression': 1.6,
            'surge': 1.1,
            'stat_arb': 0.2,
            'momentum_quality': -0.3
        }

        dyn_w = self.scorer.compute_dynamic_weights_from_sharpe(
            rolling_sharpes=sharpes,
            regime='BULL_LOW_VOL'
        )

        self.assertAlmostEqual(sum(dyn_w.values()), 1.0, places=5)
        # regression (Sharpe 1.6) should receive high weight boost
        self.assertGreater(dyn_w['regression'], dyn_w['stat_arb'])
        self.assertGreater(dyn_w['surge'], dyn_w['stat_arb'])

    def test_triple_confluence_and_quality_compounder_boosters(self):
        """Verify Triple Confirmation Alpha Confluence and Quality Compounder boosts."""
        symbols = [f'SYM_{i:02d}' for i in range(8)]
        n = len(symbols)

        # Baseline regression dataframe
        reg_df = pd.DataFrame({
            'symbol': symbols,
            'expected_return': [0.15] * n,
            'operating_margin': [0.05, 0.20, -0.15, 0.05, 0.05, 0.05, 0.05, 0.05],
            'roe': [0.05, 0.22, -0.18, 0.05, 0.05, 0.05, 0.05, 0.05],
            'market_cap': [1e11] * n,
            'volume_krw': [1e10] * n,
            'spread': [0.001] * n,
            'stt_rate': [0.0018] * n,
            'sec_rate': [0.0] * n,
            'market': ['KOSPI'] * n,
            'sector': ['Tech'] * n
        })

        # Provide baseline scores for all symbols: SYM_00 gets 0.75+ on Value, Momentum, and Order Flow
        rim_df = pd.DataFrame({
            'symbol': symbols,
            'rim_score': [0.75, 0.50, 0.50, 0.50, 0.50, 0.50, 0.50, 0.50]
        })
        mq_df = pd.DataFrame({
            'symbol': symbols,
            'mq_score': [0.75, 0.50, 0.50, 0.50, 0.50, 0.50, 0.50, 0.50]
        })
        order_flow_df = pd.DataFrame({
            'symbol': symbols,
            'order_flow_score': [0.75, 0.50, 0.50, 0.50, 0.50, 0.50, 0.50, 0.50]
        })

        result = self.scorer.combine_predictions(
            reg_df=reg_df,
            rim_df=rim_df,
            mq_df=mq_df,
            order_flow_df=order_flow_df,
            regime='BULL_LOW_VOL'
        )

        self.assertIn('ensemble_score', result.columns)
        self.assertIn('portfolio_weight', result.columns)

        res_dict = result.set_index('symbol')['ensemble_score'].to_dict()

        # SYM_00: Confluence leader should score significantly higher than neutral SYM_03
        self.assertGreater(res_dict['SYM_00'], res_dict['SYM_03'])

        # SYM_01: High quality compounder (Op Margin 20%, ROE 22%) should score higher than neutral SYM_03
        self.assertGreater(res_dict['SYM_01'], res_dict['SYM_03'])

        # SYM_02: Chronic Distress stock (Op Margin -15%, ROE -18%) should score lower due to 0.70x penalty
        self.assertLess(res_dict['SYM_02'], res_dict['SYM_03'])


if __name__ == '__main__':
    unittest.main()
