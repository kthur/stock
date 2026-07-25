import unittest
import pandas as pd
from src.ai.ensemble_scorer import EnsembleScoringEngine

class TestRegimeEnsemble(unittest.TestCase):
    def setUp(self):
        self.engine = EnsembleScoringEngine()

        # Create mock dataframes for 3 stocks:
        # Stock_A: Good fundamentals (High regression score), poor surge/momentum
        # Stock_B: High surge probability, average fundamentals
        # Stock_C: Moderate in all categories

        self.regression_df = pd.DataFrame([
            {'symbol': 'Stock_A', 20: 0.15},  # 15% expected return
            {'symbol': 'Stock_B', 20: 0.02},  # 2% expected return
            {'symbol': 'Stock_C', 20: 0.08},  # 8% expected return
        ])

        self.surge_df = pd.DataFrame([
            {'symbol': 'Stock_A', 'surge_prob_20d': 0.05},
            {'symbol': 'Stock_B', 'surge_prob_20d': 0.90},
            {'symbol': 'Stock_C', 'surge_prob_20d': 0.40},
        ])

        self.lead_lag_df = pd.DataFrame([
            {'symbol': 'Stock_A', 'lead_lag_score': 0.10},
            {'symbol': 'Stock_B', 'lead_lag_score': 0.20},
            {'symbol': 'Stock_C', 'lead_lag_score': 0.80},
        ])

        self.vcp_ml_df = pd.DataFrame([
            {'symbol': 'Stock_A', 'vcp_prob_20d': 0.02},
            {'symbol': 'Stock_B', 'vcp_prob_20d': 0.85},
            {'symbol': 'Stock_C', 'vcp_prob_20d': 0.50},
        ])

    def test_bear_regime_ensemble(self):
        # 0: BEAR market - Regression fundamentals (70%) and Lead-Lag (20%) dominate
        # Surge is 0%, VCP ML is 10%
        # Stock_A (high regression) should score very high compared to Stock_B (high surge, low regression)
        res = self.engine.calculate_ensemble_score(
            regime=0,
            regression_df=self.regression_df,
            surge_df=self.surge_df,
            lead_lag_df=self.lead_lag_df,
            vcp_ml_df=self.vcp_ml_df,
            target_horizon=20
        )

        scores = dict(zip(res['symbol'], res['ensemble_score']))

        # Verify order: A should be higher than B
        self.assertGreater(scores['Stock_A'], scores['Stock_B'])

        # Score_B with 5-strategy weights:
        # reg(0.55)*(1/3) + surge(0.05)*0.90 + ll(0.15)*((0.2-0.1)/(0.8-0.1)) + vcp_rule(0.15)*0.0 + vcp_ml(0.10)*0.85
        expected_score_b = 0.55 * (1/3) + 0.05 * 0.90 + 0.15 * ((0.2-0.1)/(0.8-0.1)) + 0.10 * 0.85
        self.assertAlmostEqual(scores['Stock_B'], expected_score_b, places=3)


    def test_bull_regime_ensemble(self):
        # 2: BULL market - Surge (40%) and VCP ML (40%) dominate
        # Stock_B (high surge, high VCP ML) should score significantly higher than Stock_A
        res = self.engine.calculate_ensemble_score(
            regime=2,
            regression_df=self.regression_df,
            surge_df=self.surge_df,
            lead_lag_df=self.lead_lag_df,
            vcp_ml_df=self.vcp_ml_df,
            target_horizon=20
        )

        scores = dict(zip(res['symbol'], res['ensemble_score']))

        # Verify order: B should be higher than A
        self.assertGreater(scores['Stock_B'], scores['Stock_A'])

        # In BULL, Stock_B should be the top pick
        self.assertEqual(res['symbol'].iloc[0], 'Stock_B')

    def test_sideways_regime_ensemble(self):
        # 1: SIDEWAYS market - Rotation (Lead-Lag 35%, Regression 35%) dominates
        # Stock_C has very high Lead-Lag (0.80) and moderate regression, it should perform well
        res = self.engine.calculate_ensemble_score(
            regime=1,
            regression_df=self.regression_df,
            surge_df=self.surge_df,
            lead_lag_df=self.lead_lag_df,
            vcp_ml_df=self.vcp_ml_df,
            target_horizon=20
        )

        scores = dict(zip(res['symbol'], res['ensemble_score']))

        # Stock_C should be highly ranked because of high lead_lag_score and decent regression rank
        self.assertGreater(scores['Stock_C'], scores['Stock_A'])

if __name__ == '__main__':
    unittest.main()
