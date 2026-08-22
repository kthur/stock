"""
tests/test_run_snapshot.py
Unit tests for generate_run_snapshot.py (V6-34) verifying regex structured parsing
of ensemble_predictions.txt fallback without 0.50 score fabrication.
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

# Ensure project root and trading_system are on sys.path
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_TS_DIR = os.path.join(_ROOT, "trading_system")
if _TS_DIR not in sys.path:
    sys.path.insert(0, _TS_DIR)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from trading_system.generate_run_snapshot import generate_snapshot


class TestGenerateRunSnapshot(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.result_dir = Path(self.temp_dir.name) / "result"
        self.result_dir.mkdir(parents=True, exist_ok=True)
        self.output_json = self.result_dir / "run_snapshot.json"
        self.db_path = self.result_dir / "non_existent_market_indicators.db"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_fallback_parsing_with_ensemble_text(self):
        """V6-34: Verify that generate_snapshot parses table columns, strategy scores, and metadata without fabricating 0.50 fallbacks."""
        # Sample text mimicking real ensemble_predictions.txt format with 31 strategies
        sample_text = """=== Dynamic Multi-Strategy Ensemble Predictions (31 Strategies) ===
Date: 2026-08-22 09:30 KST

--- Executive Market Summary ---
Current Market Regime Detected: Bullish-LowVol (2D State: BULL_LOW_VOL)
US Market Regime (S&P500): BULL_LOW_VOL
KR Market Regime (KOSPI) : BULL_LOW_VOL
Maximum Total Allocation Allowed: 100.0%

--- Applied Ensemble Strategy Weights (31 Strategies) ---
  XGBoost Regression Fundamentals     : 12.0%
  Surge Classifier (XGBoost)          : 10.0%
  Index & Sector Lead-Lag Flow        :  8.0%

--- Top 20 Recommendations by Market ---

=========================================
[KOSPI] Top 100 Ensemble Picks (Target Horizon: 20D Expected Return)
=========================================
Rank Symbol    Name              Ens Score   Exp Ret(20D)  Reg  Srg  L-L  VCP-R VCP-M LSTM S-Arb Sec-R RIM  Event MQ   IV-Sk Flow Rev  ARM  CARD  LATR IFS  Supply NLP  Neutral Vol-T Micro Accrual S-Sq ValueUp TrendEff GammaSq Insider Darkpool ToneDrift
----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
1    005930    삼성전자              68.4%       +12.50%  65%  72%  58%   60%   70%   64%   55%   75%   80%  62%   71%  50%   66%  59%  63%   57%   68%  61%   74%    53%    69%    58%   62%    55%    73%   67%      64%      52%     78%      56%      60%
2    000660    SK하이닉스             75.2%       +18.30%  78%  80%  65%   62%   76%   70%   58%   82%   85%  68%   79%  55%   72%  64%  70%   61%   75%  69%   81%    60%    77%    65%   68%    62%    80%   73%      71%      59%     84%      63%      66%
3    AAPL      Apple Inc.           62.1%        +8.40%  60%  58%  54%   52%   65%   61%   50%   68%   72%  55%   63%  48%   60%  53%  58%   51%   62%  56%   67%    49%    63%    52%   57%    50%    66%   61%      58%      47%     71%      51%      55%
"""
        ens_file = self.result_dir / "ensemble_predictions.txt"
        ens_file.write_text(sample_text, encoding="utf-8")

        snapshot = generate_snapshot(
            result_dir=self.result_dir,
            db_path=self.db_path,
            output_file=self.output_json
        )

        self.assertTrue(self.output_json.exists())
        self.assertEqual(snapshot["run_metadata"]["regime_detected"], "Bullish-LowVol (2D State: BULL_LOW_VOL)")
        
        top_picks = snapshot["top_50_picks"]
        self.assertEqual(len(top_picks), 3)

        # Check 1st pick: 005930
        pick1 = top_picks[0]
        self.assertEqual(pick1["rank"], 1)
        self.assertEqual(pick1["symbol"], "005930")
        self.assertAlmostEqual(pick1["ensemble_score"], 0.684, places=3)
        self.assertAlmostEqual(pick1["net_expected_return_pct"], 12.50, places=2)
        self.assertIn("reg_score", pick1["strategy_scores"])
        self.assertAlmostEqual(pick1["strategy_scores"]["reg_score"], 0.65, places=2)
        self.assertAlmostEqual(pick1["strategy_scores"]["surge_score"], 0.72, places=2)
        self.assertAlmostEqual(pick1["strategy_scores"]["ll_score"], 0.58, places=2)
        self.assertAlmostEqual(pick1["strategy_scores"]["earnings_tone_drift_score"], 0.60, places=2)

        # Check 2nd pick: 000660
        pick2 = top_picks[1]
        self.assertEqual(pick2["rank"], 2)
        self.assertEqual(pick2["symbol"], "000660")
        self.assertAlmostEqual(pick2["ensemble_score"], 0.752, places=3)
        self.assertAlmostEqual(pick2["net_expected_return_pct"], 18.30, places=2)
        self.assertAlmostEqual(pick2["strategy_scores"]["reg_score"], 0.78, places=2)

        # Check 3rd pick: AAPL
        pick3 = top_picks[2]
        self.assertEqual(pick3["rank"], 3)
        self.assertEqual(pick3["symbol"], "AAPL")
        self.assertAlmostEqual(pick3["ensemble_score"], 0.621, places=3)
        self.assertAlmostEqual(pick3["net_expected_return_pct"], 8.40, places=2)

        # Ensure no fabricated uniform 0.50 score
        self.assertNotEqual(pick1["ensemble_score"], 0.5)
        self.assertNotEqual(pick2["ensemble_score"], 0.5)
        self.assertNotEqual(pick3["ensemble_score"], 0.5)


if __name__ == "__main__":
    unittest.main()
