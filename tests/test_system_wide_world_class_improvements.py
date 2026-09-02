import datetime
import math
import sqlite3
import unittest
import numpy as np
import pandas as pd

from src.ai.ensemble_scorer import EnsembleScoringEngine
from src.core.index_rebalance import IndexRebalanceEngine
from src.core.overnight_gap_reversal import OvernightGapReversalEngine
from src.execution.oms_engine import ExecutionOMSEngine
from src.risk.portfolio_allocator import PortfolioAllocator
from src.risk.intraday_stop_loss import IntradayStopLossEngine


class TestSystemWideWorldClassImprovements(unittest.TestCase):
    """
    Unit tests for system-wide world-class quant enhancements across all 37 strategies.
    """

    def setUp(self):
        self.scorer = EnsembleScoringEngine()
        self.rebal_engine = IndexRebalanceEngine()
        self.gap_engine = OvernightGapReversalEngine()
        self.allocator = PortfolioAllocator()
        self.oms = ExecutionOMSEngine(db_path=":memory:")

    # -------------------------------------------------------------------------
    # 1. 37-Strategy Regime Weight Normalization & Sum-to-One Verification
    # -------------------------------------------------------------------------
    def test_all_37_strategies_in_1d_and_2d_regimes_sum_to_one(self):
        """Verify all 37 strategies are configured in 1D and 2D regime matrices with sum = 1.0000."""
        # 1D Regimes (0: BEAR, 1: SIDEWAYS, 2: BULL)
        for r_id, weights in self.scorer.REGIME_WEIGHTS.items():
            self.assertEqual(len(weights), 37, f"1D Regime {r_id} should have exactly 37 strategies, got {len(weights)}")
            w_sum = sum(weights.values())
            self.assertAlmostEqual(w_sum, 1.0, places=4, msg=f"1D Regime {r_id} weights must sum to 1.0, got {w_sum}")
            self.assertIn("dual_correction", weights)
            self.assertIn("index_rebalance", weights)
            self.assertIn("overnight_gap_reversal", weights)

        # 2D Regimes (6 states)
        for r_name, weights in self.scorer.REGIME_2D_WEIGHTS.items():
            self.assertEqual(len(weights), 37, f"2D Regime {r_name} should have exactly 37 strategies, got {len(weights)}")
            w_sum = sum(weights.values())
            self.assertAlmostEqual(w_sum, 1.0, places=4, msg=f"2D Regime {r_name} weights must sum to 1.0, got {w_sum}")
            self.assertIn("dual_correction", weights)
            self.assertIn("index_rebalance", weights)
            self.assertIn("overnight_gap_reversal", weights)

        # Dynamic weight computation across 37 strategies
        dyn_w = self.scorer.compute_dynamic_weights_from_sharpe(
            rolling_sharpes={"dual_correction": 1.5, "index_rebalance": 1.2, "regression": 0.5},
            regime="BULL_LOW_VOL"
        )
        self.assertAlmostEqual(sum(dyn_w.values()), 1.0, places=4)
        self.assertIn("dual_correction", dyn_w)
        self.assertIn("index_rebalance", dyn_w)
        self.assertIn("overnight_gap_reversal", dyn_w)

    # -------------------------------------------------------------------------
    # 2. OMS Gate 8 Synthetic Inverse Hedge Execution & DB Migration
    # -------------------------------------------------------------------------
    def test_oms_gate_8_synthetic_inverse_hedge_execution_and_db_schema(self):
        """Verify Gate 8 synthetic inverse hedge order generation operates without NameError."""
        # Check SQLite DB schema has the migrated columns
        conn = self.oms._get_conn()
        cursor = conn.cursor()
        cols = [r[1] for r in cursor.execute("PRAGMA table_info(order_plans)").fetchall()]
        self.assertIn("sleeve_type", cols)
        self.assertIn("target_take_profit", cols)
        self.assertIn("target_stop_loss", cols)

        top_preds = [
            {"symbol": "005930", "name": "Samsung", "market": "KOSPI", "action": "BUY", "target_price": 70000.0, "alpha_sleeve": "SLOW"}
        ]
        port_weights = {"005930": 0.30}

        # Generate orders in BEAR regime -> should trigger Gate 8 hedge
        order_plans = self.oms.generate_order_plans(
            top_predictions=top_preds,
            portfolio_weights=port_weights,
            total_capital=100_000_000.0,
            regime_label="BEAR_HIGH_VOL",
            prices_dict={"005930": pd.DataFrame({"Close": [70000.0] * 20})}
        )

        # Find the hedge order in generated order plans
        hedge_orders = [o for o in order_plans if o.get("action") == "BUY_HEDGE"]
        self.assertTrue(len(hedge_orders) >= 1, "Gate 8 must generate at least 1 synthetic inverse hedge order in BEAR regime")
        h_order = hedge_orders[0]
        self.assertEqual(h_order["symbol"], "114800")
        self.assertGreater(h_order["quantity"], 0)
        self.assertGreater(h_order["target_amount"], 0.0)

    # -------------------------------------------------------------------------
    # 3. Index Rebalance Calendar Expansion (March and September)
    # -------------------------------------------------------------------------
    def test_index_rebalance_march_and_september_schedule(self):
        """Verify March (3) and September (9) are recognized as active quarterly rebalance seasons."""
        march_date = datetime.date(2026, 3, 15)
        sept_date = datetime.date(2026, 9, 2)
        june_date = datetime.date(2026, 6, 10)

        march_res = self.rebal_engine.is_near_rebalance_window(march_date)
        self.assertTrue(march_res["in_window"])
        self.assertEqual(march_res["phase"], "REBALANCE_MONTH")
        self.assertEqual(march_res["target_index"], "SP500_NASDAQ")

        sept_res = self.rebal_engine.is_near_rebalance_window(sept_date)
        self.assertTrue(sept_res["in_window"])
        self.assertEqual(sept_res["phase"], "REBALANCE_MONTH")
        self.assertEqual(sept_res["target_index"], "SP500_NASDAQ")

        june_res = self.rebal_engine.is_near_rebalance_window(june_date)
        self.assertTrue(june_res["in_window"])
        self.assertEqual(june_res["target_index"], "KOSPI200")

    # -------------------------------------------------------------------------
    # 4. Overnight Gap Reversal: Filled vs Unfilled Dislocation Calibration
    # -------------------------------------------------------------------------
    def test_overnight_gap_reversal_unfilled_persistence(self):
        """Verify that unfilled downward gap receives stronger mean-reversion score than filled gap."""
        # Case A: Downward opening gap (-3%), but price filled the gap intraday (High >= prev_close)
        df_filled = pd.DataFrame({
            "Open": [100.0] * 14 + [97.0],
            "High": [101.0] * 14 + [100.5],  # Gap filled intraday
            "Low": [99.0] * 14 + [96.5],
            "Close": [100.0] * 14 + [99.5],
            "Volume": [1000.0] * 15
        })

        # Case B: Downward opening gap (-3%), and price remained completely unfilled (High < prev_close) with bullish close
        df_unfilled = pd.DataFrame({
            "Open": [100.0] * 14 + [97.0],
            "High": [101.0] * 14 + [98.5],  # Gap remained unfilled
            "Low": [99.0] * 14 + [96.5],
            "Close": [100.0] * 14 + [98.2],  # Bullish closing pin above open
            "Volume": [1000.0] * 15
        })

        res_filled = self.gap_engine.calculate_scores(["A"], prices_dict={"A": df_filled})
        res_unfilled = self.gap_engine.calculate_scores(["B"], prices_dict={"B": df_unfilled})

        score_filled = float(res_filled["overnight_gap_score"].iloc[0])
        score_unfilled = float(res_unfilled["overnight_gap_score"].iloc[0])

        self.assertGreater(score_unfilled, score_filled, "Unfilled gap must generate a higher pending bounce score than an already-filled gap")

    # -------------------------------------------------------------------------
    # 5. Portfolio Allocator: Top-K Kelly Fallback Concentration
    # -------------------------------------------------------------------------
    def test_quarter_kelly_top_k_fallback_concentration(self):
        """Verify that when total_k <= 1e-8, allocate_quarter_kelly respects top_k_concentration."""
        symbols = [f"SYM_{i}" for i in range(20)]
        # Flat expected returns equal to risk-free rate -> total_k <= 1e-8
        exp_ret = pd.Series([0.0] * 20, index=symbols)
        vols = pd.Series([0.02] * 20, index=symbols)

        weights = self.allocator.allocate_quarter_kelly(
            expected_returns=exp_ret,
            volatilities=vols,
            top_k_concentration=5
        )

        active_symbols = [s for s, w in weights.items() if w > 0.0]
        self.assertEqual(len(active_symbols), 5, "Fallback equal allocation must only allocate to top-K symbols")
        for s in symbols[5:]:
            self.assertEqual(weights[s], 0.0)

    # -------------------------------------------------------------------------
    # 6. Multi-Factor Confluence: Strategies 35, 36, 37 Confirmation
    # -------------------------------------------------------------------------
    def test_confluence_expansion_with_strategies_35_36_37(self):
        """Verify that dual_correction, index_rebalance, and overnight_gap trigger confluence boosters."""
        n_rows = 10
        symbols = [f"TICK_{i}" for i in range(n_rows)]

        # Stock 0: Confluence across Valuation (dual_correction), Momentum (dual_correction), Flow (index_rebalance), Catalyst (index_rebalance)
        df_scores = pd.DataFrame({
            "symbol": symbols,
            "dual_correction_score": [0.85] + [0.30] * (n_rows - 1),
            "index_rebalance_score": [0.80] + [0.30] * (n_rows - 1),
            "overnight_gap_score": [0.75] + [0.30] * (n_rows - 1),
            "reg_score": [0.50] * n_rows
        })

        res_df = self.scorer.calculate_ensemble_score(scores_df=df_scores)
        s0_score = float(res_df.loc[res_df["symbol"] == "TICK_0", "ensemble_score"].iloc[0])
        s1_score = float(res_df.loc[res_df["symbol"] == "TICK_1", "ensemble_score"].iloc[0])

        self.assertGreater(s0_score, s1_score)
        self.assertGreater(s0_score, 0.50)


if __name__ == "__main__":
    unittest.main()
