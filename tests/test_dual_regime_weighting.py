import unittest
import pandas as pd
import numpy as np
from pathlib import Path
import tempfile

from trading_system.src.ai.ensemble_scorer import EnsembleScoringEngine
from trading_system.generate_report import parse_ensemble, generate_html, EnsembleData, REGIME_INFO


class TestDualRegimeWeighting(unittest.TestCase):
    def setUp(self):
        self.scorer = EnsembleScoringEngine()

    def test_dual_regime_scoring_and_decoupling_tilt(self):
        # Create dummy predictions for 1 US stock and 1 KR stock
        df_reg = pd.DataFrame([
            {'symbol': 'AAPL', 'name': 'Apple', 'market': 'SP500', 'expected_return': 0.05, 'close': 150.0},
            {'symbol': '005930', 'name': 'Samsung', 'market': 'KOSPI', 'expected_return': 0.02, 'close': 70000.0},
        ])
        df_surge = pd.DataFrame([
            {'symbol': 'AAPL', 'surge_probability': 0.8},
            {'symbol': '005930', 'surge_probability': 0.2},
        ])
        df_rim = pd.DataFrame([
            {'symbol': 'AAPL', 'rim_score': 0.4},
            {'symbol': '005930', 'rim_score': 0.9},
        ])

        # Test when US is BULL_LOW_VOL and KR is BEAR_LOW_VOL with DECOUPLING_US_BULL_KR_BEAR
        res = self.scorer.calculate_ensemble_score(
            regime='BULL_LOW_VOL',
            us_regime='BULL_LOW_VOL',
            kr_regime='BEAR_LOW_VOL',
            decoupling_status='DECOUPLING_US_BULL_KR_BEAR',
            regression_df=df_reg,
            surge_df=df_surge,
            rim_df=df_rim,
        )

        self.assertIsNotNone(res)
        self.assertIn('ensemble_score', res.columns)
        self.assertEqual(len(res), 2)

        # Check that us_strategy_weights and kr_strategy_weights were recorded
        self.assertTrue(hasattr(self.scorer, 'us_strategy_weights'))
        self.assertTrue(hasattr(self.scorer, 'kr_strategy_weights'))
        self.assertNotEqual(self.scorer.us_strategy_weights, self.scorer.kr_strategy_weights)

        # In US Bull, surge weight should be higher than in KR Bear
        self.assertGreater(self.scorer.us_strategy_weights.get('surge', 0.0),
                           self.scorer.kr_strategy_weights.get('surge', 0.0))

        # In KR Bear, rim_valuation weight should be higher than in US Bull
        self.assertGreater(self.scorer.kr_strategy_weights.get('rim_valuation', 0.0),
                           self.scorer.us_strategy_weights.get('rim_valuation', 0.0))

    def test_report_generation_dynamic_regime_matrix(self):
        sample_ensemble_text = """=== Dynamic Multi-Strategy Ensemble Predictions (31 Strategies) ===
Date: 2026-08-18 09:00 KST

--- Executive Market Summary ---
Current Market Regime Detected: BULL_LOW_VOL (2D State: BULL_LOW_VOL)
US Market Regime (S&P500): BULL_LOW_VOL
KR Market Regime (KOSPI) : SIDEWAYS_LOW_VOL
Maximum Total Allocation Allowed: 85.0%

[2D Market Regime & Strategy Decision Rationale]
• Selected Main Regime State: BULL_LOW_VOL
• Dual Market Correlation (20d): 0.65 | Status: DECOUPLING_US_BULL_KR_BEAR
  - US Market Regime (S&P500): BULL_LOW_VOL
  - KR Market Regime (KOSPI) : SIDEWAYS_LOW_VOL

--- Applied US Strategy Weights (31 Strategies) [US: BULL_LOW_VOL] ---
  Surge Classifier (XGBoost)          : 12.0%
  RIM Valuation (Residual Income)     : 3.0%

--- Applied KR Strategy Weights (31 Strategies) [KR: SIDEWAYS_LOW_VOL] ---
  Surge Classifier (XGBoost)          : 4.0%
  RIM Valuation (Residual Income)     : 8.0%

--- Applied Ensemble Strategy Weights (31 Strategies) ---
  Surge Classifier (XGBoost)          : 10.0%
  RIM Valuation (Residual Income)     : 5.0%

=========================================
[SP500] Top 100 Ensemble Picks (Target Horizon: 20D Expected Return)
=========================================
Rank Symbol    Name              Ens Score   Exp Ret(20D)  Reg  Srg  L-L  VCP-R VCP-M LSTM S-Arb Sec-R RIM  Event MQ   IV-Sk Flow Rev  ARM  CARD LATR IFS  Supply NLP  Neutral Vol-T Micro Accrual S-Sq ValueUp TrendEff GammaSq Insider Darkpool ToneDrift
----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
1    AAPL      Apple Inc.        0.852       +4.50%        0.8  0.9  0.7  0.0   0.0   0.0  0.0   0.0   0.4  0.0   0.0  0.0   0.0  0.0  0.0  0.0  0.0  0.0  0.0    0.0  0.0     0.0   0.0   0.0     0.0  0.0     0.0      0.0     0.0     0.0      0.0      
"""
        data = parse_ensemble(sample_ensemble_text)
        self.assertEqual(data.us_regime, "BULL_LOW_VOL")
        self.assertEqual(data.kr_regime, "SIDEWAYS_LOW_VOL")
        self.assertEqual(data.decoupling_status, "DECOUPLING_US_BULL_KR_BEAR")
        self.assertIn("Surge Classifier (XGBoost)", data.us_weights)
        self.assertIn("RIM Valuation (Residual Income)", data.kr_weights)

        html = generate_html(
            ensemble=data,
            surge_date="", surge_sections=[],
            vcp_date="", vcp_rows=[],
            lag_date="", follower_rows=[], leader_rows=[]
        )
        # Check that BULL_LOW_VOL is rendered with US 현재 badge
        self.assertIn("BULL_LOW_VOL", html)
        self.assertIn("🇺🇸 US 현재", html)
        self.assertIn("🇰🇷 KR 현재", html)
        # Check that Decoupling badge is rendered
        self.assertIn("Decoupled (DECOUPLING_US_BULL_KR_BEAR)", html)


if __name__ == '__main__':
    unittest.main()
