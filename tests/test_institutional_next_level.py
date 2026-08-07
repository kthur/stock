"""
test_institutional_next_level.py — Unit Tests for 4 Next-Level Quantitative Engines

Tests:
1. WalkForwardBacktester (Pearson & Rank IC)
2. LiveAlphaTracker (Hit Rate & Feedback Multipliers)
3. TurnoverOptimizer (Hysteresis Buffer & Turnover Reduction)
4. CrowdingRiskMonitor (Sector Concentration & Anti-Crowding Penalty)
"""

import os
import sys
import unittest
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "trading_system")))

from src.analysis.walk_forward_backtester import WalkForwardBacktester
from src.analysis.live_alpha_tracker import LiveAlphaTracker
from src.execution.turnover_optimizer import TurnoverOptimizer
from src.risk.crowding_monitor import CrowdingRiskMonitor


class TestInstitutionalNextLevel(unittest.TestCase):

    def test_walk_forward_backtester(self):
        pred_df = pd.DataFrame([
            {"date": "2024-01-01", "symbol": "005930", "supply_chain_score": 0.80, "ensemble_score": 0.85},
            {"date": "2024-01-01", "symbol": "000660", "supply_chain_score": 0.70, "ensemble_score": 0.75},
            {"date": "2024-01-01", "symbol": "NVDA", "supply_chain_score": 0.90, "ensemble_score": 0.92},
            {"date": "2024-01-01", "symbol": "AAPL", "supply_chain_score": 0.40, "ensemble_score": 0.45},
            {"date": "2024-01-01", "symbol": "MSFT", "supply_chain_score": 0.50, "ensemble_score": 0.55},
        ])
        ret_df = pd.DataFrame([
            {"date": "2024-01-01", "symbol": "005930", "forward_return_20d": 0.10},
            {"date": "2024-01-01", "symbol": "000660", "forward_return_20d": 0.05},
            {"date": "2024-01-01", "symbol": "NVDA", "forward_return_20d": 0.15},
            {"date": "2024-01-01", "symbol": "AAPL", "forward_return_20d": -0.05},
            {"date": "2024-01-01", "symbol": "MSFT", "forward_return_20d": -0.02},
        ])

        backtester = WalkForwardBacktester()
        res = backtester.run_walk_forward(pred_df, ret_df)

        self.assertEqual(res["status"], "SUCCESS")
        self.assertIn("ensemble_score", res["strategy_metrics"])
        self.assertGreater(res["strategy_metrics"]["ensemble_score"]["ic"], 0.80)

    def test_live_alpha_tracker(self):
        pred_history = pd.DataFrame([
            {"date": "2024-01-01", "symbol": "005930", "strategy_name": "supply_chain", "pred_score": 0.80},
            {"date": "2024-01-01", "symbol": "000660", "strategy_name": "supply_chain", "pred_score": 0.70},
            {"date": "2024-01-01", "symbol": "NVDA", "strategy_name": "decaying_strat", "pred_score": 0.90},
            {"date": "2024-01-01", "symbol": "AAPL", "strategy_name": "decaying_strat", "pred_score": 0.85},
        ])
        realized_returns = pd.DataFrame([
            {"date": "2024-01-01", "symbol": "005930", "realized_return_20d": 0.10},
            {"date": "2024-01-01", "symbol": "000660", "realized_return_20d": 0.05},
            {"date": "2024-01-01", "symbol": "NVDA", "realized_return_20d": -0.15},
            {"date": "2024-01-01", "symbol": "AAPL", "realized_return_20d": -0.10},
        ])

        tracker = LiveAlphaTracker()
        eval_res = tracker.evaluate_realized_alpha(pred_history, realized_returns)

        self.assertEqual(eval_res["status"], "SUCCESS")
        self.assertGreater(eval_res["multipliers"]["supply_chain"], 1.0)
        self.assertLess(eval_res["multipliers"]["decaying_strat"], 0.5)

    def test_turnover_optimizer(self):
        current_holdings = {"005930": 0.10, "NVDA": 0.20}
        target_allocations = {"005930": 0.12, "NVDA": 0.35} # 005930 change is 2% (<5%), NVDA change is 15% (>5%)

        optimizer = TurnoverOptimizer(turnover_threshold_pct=0.05)
        opt_res = optimizer.optimize_allocations(current_holdings, target_allocations)

        self.assertEqual(opt_res["005930"]["action"], "HOLD")
        self.assertEqual(opt_res["005930"]["target_weight"], 0.10)
        self.assertEqual(opt_res["NVDA"]["action"], "BUY")
        self.assertEqual(opt_res["NVDA"]["target_weight"], 0.35)

    def test_crowding_risk_monitor(self):
        df_ensemble = pd.DataFrame([
            {"symbol": "005930", "sector": "Semiconductors", "ensemble_score": 0.90, "s1_score": 0.85, "s2_score": 0.80},
            {"symbol": "000660", "sector": "Semiconductors", "ensemble_score": 0.85, "s1_score": 0.82, "s2_score": 0.78},
            {"symbol": "NVDA", "sector": "Semiconductors", "ensemble_score": 0.95, "s1_score": 0.90, "s2_score": 0.88},
            {"symbol": "005380", "sector": "Automotive", "ensemble_score": 0.10, "s1_score": 0.20, "s2_score": 0.15},
        ])

        monitor = CrowdingRiskMonitor(max_sector_weight=0.40)
        df_dampened, status = monitor.evaluate_crowding_risk(df_ensemble)

        self.assertEqual(status["status"], "SUCCESS")
        self.assertGreater(len(status["warnings"]), 0)


if __name__ == "__main__":
    unittest.main()
