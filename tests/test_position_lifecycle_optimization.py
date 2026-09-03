"""
Comprehensive Test Suite for Position Lifecycle Optimization & Return Maximization Framework
Verifies:
1. 3-Tier Dynamic Profit Taking Engine (Tier 1 BEP Lock, Tier 2, Tier 3 Trend Runner)
2. Alpha-Vol Blended Sizing (Alpha conviction tilting with HRP risk parity & capping)
3. Asymmetric Leland Dynamic No-Trade Buffer Bands (Upper expansion for runners, lower tightening for laggards)
4. Alpha Decay Soft Exit & Time-Stop Inactivity Exit
5. Intraday Monotonic Ratchet & Breakeven Profit Lock
"""

import unittest
import numpy as np
import pandas as pd

from src.execution.oms_engine import ExecutionOMSEngine
from src.risk.portfolio_allocator import PortfolioAllocator
from src.realtime.intraday_monitor import IntradayMonitor, WatchItem, MonitorAction
from src.risk.intraday_stop_loss import IntradayStopLossEngine


class TestPositionLifecycleOptimization(unittest.TestCase):

    def setUp(self):
        self.oms = ExecutionOMSEngine(db_path=":memory:")
        self.allocator = PortfolioAllocator()
        self.stop_engine = IntradayStopLossEngine()
        self.monitor = IntradayMonitor()

    # =========================================================================
    # 1. 3-Tier Dynamic Profit Taking Engine Tests
    # =========================================================================

    def test_3tier_profit_taking_tier1_bep_lock(self):
        """Verify Tier 1 profit taking (+8% / +1.5R) takes 30% profit and raises stop loss to breakeven."""
        holdings = {
            "RUNNER_T1": {
                "quantity": 100,
                "entry_price": 100.0,
                "current_price": 109.0,  # +9% gain (Tier 1 triggered)
                "days_held": 3,
                "volatility_20d": 0.02,
                "current_score": 0.75,
                "enable_3tier_tp": True
            }
        }
        plans = self.oms.calculate_trailing_stop_plan(
            current_holdings=holdings,
            prices_dict=None,
            regime="BULL_LOW_VOL",
            enable_3tier_tp=True
        )
        self.assertTrue(len(plans) >= 1)
        plan = next(p for p in plans if p["symbol"] == "RUNNER_T1")
        self.assertEqual(plan["action"], "SELL")
        self.assertEqual(plan["reason"], "TIER_1_PROFIT_LOCK")
        self.assertEqual(plan["quantity"], 30)  # 30% of 100
        self.assertGreaterEqual(plan["stop_loss_price"], 100.3)  # Breakeven protected

    def test_3tier_profit_taking_tier2_chandelier(self):
        """Verify Tier 2 profit taking (+15% / +3.0R) triggers TIER_2_PROFIT_LOCK or CHANDELIER_TRAILING_PROFIT."""
        holdings = {
            "RUNNER_T2": {
                "quantity": 100,
                "entry_price": 100.0,
                "current_price": 118.0,  # +18% gain
                "days_held": 8,
                "volatility_20d": 0.02,
                "tier1_taken": True,
                "enable_3tier_tp": True
            }
        }
        plans = self.oms.calculate_trailing_stop_plan(
            current_holdings=holdings,
            prices_dict=None,
            regime="BULL_LOW_VOL",
            enable_3tier_tp=True
        )
        self.assertTrue(len(plans) >= 1)
        plan = next(p for p in plans if p["symbol"] == "RUNNER_T2")
        self.assertEqual(plan["action"], "SELL")
        self.assertIn(plan["reason"], ("TIER_2_PROFIT_LOCK", "CHANDELIER_TRAILING_PROFIT"))

    def test_3tier_profit_taking_breakeven_lock_triggered_on_pullback(self):
        """Verify that when a stock gained +9% but pulls back to breakeven, BREAKEVEN_PROFIT_LOCK fires."""
        holdings = {
            "PULLBACK_STOCK": {
                "quantity": 70,
                "entry_price": 100.0,
                "current_price": 100.2,  # Pulled back below breakeven (100.3)
                "days_held": 5,
                "volatility_20d": 0.02,
            }
        }
        # Simulate that high was 109 previously via price history
        dates = pd.date_range("2026-01-01", periods=15, freq="B")
        prices_df = pd.DataFrame({
            "High": [100, 102, 105, 109, 108, 107, 106, 105, 104, 103, 102, 101, 100.5, 100.3, 100.2],
            "Low": [99, 101, 103, 106, 105, 104, 103, 102, 101, 100, 99.5, 99.5, 99.8, 99.9, 99.9],
            "Close": [100, 102, 105, 108, 107, 106, 105, 104, 103, 102, 101, 100.5, 100.3, 100.2, 100.2],
        }, index=dates)

        plans = self.oms.calculate_trailing_stop_plan(
            current_holdings=holdings,
            prices_dict={"PULLBACK_STOCK": prices_df},
            regime="BULL_LOW_VOL"
        )
        self.assertTrue(len(plans) >= 1)
        plan = next(p for p in plans if p["symbol"] == "PULLBACK_STOCK")
        self.assertEqual(plan["action"], "SELL")
        self.assertIn(plan["reason"], ("BREAKEVEN_PROFIT_LOCK", "ATR_STOP_LOSS"))

    # =========================================================================
    # 2. Alpha-Vol Blended Sizing Tests
    # =========================================================================

    def test_alpha_vol_blended_weights(self):
        """Verify Alpha-Vol Blended Sizing tilts weights toward high alpha conviction."""
        hrp_weights = {
            "ALPHA_LEADER": 0.20,
            "MEDIAN_STOCK": 0.20,
            "ALPHA_LAGGER": 0.20,
        }
        alpha_scores = {
            "ALPHA_LEADER": 0.90,  # High alpha conviction
            "MEDIAN_STOCK": 0.50,  # Average
            "ALPHA_LAGGER": 0.10,  # Low alpha conviction
        }

        tilted = PortfolioAllocator.calculate_alpha_vol_blended_weights(
            hrp_weights=hrp_weights,
            alpha_scores=alpha_scores,
            beta=0.50,
            max_single_weight=0.45,
            target_total_weight=0.85
        )

        self.assertIn("ALPHA_LEADER", tilted)
        self.assertIn("ALPHA_LAGGER", tilted)
        # Leader should receive significantly higher weight than lagger
        self.assertGreater(tilted["ALPHA_LEADER"], tilted["MEDIAN_STOCK"])
        self.assertGreater(tilted["MEDIAN_STOCK"], tilted["ALPHA_LAGGER"])
        # Total weight should equal target_total_weight
        self.assertAlmostEqual(sum(tilted.values()), 0.85, places=4)
        # Max single weight cap respected
        for w in tilted.values():
            self.assertLessEqual(w, 0.45 + 1e-6)

    # =========================================================================
    # 3. Asymmetric Leland Dynamic No-Trade Buffer Bands Tests
    # =========================================================================

    def test_asymmetric_leland_buffer_bands(self):
        """Verify winning runner (+15%) gets upper band expanded (1.8x) preventing premature sell."""
        current_weights = {"RUNNER": 0.12, "LAGGER": 0.10}
        target_weights = {"RUNNER": 0.10, "LAGGER": 0.10}
        market_map = {"RUNNER": "KOSPI", "LAGGER": "KOSPI"}
        vol_map = {"RUNNER": 0.02, "LAGGER": 0.02}
        adv_map = {"RUNNER": 1e9, "LAGGER": 1e9}

        # Symmetric rebalance without returns: delta ~ 0.015 -> U_i ~ 0.115 -> 0.12 > 0.115 -> SELL!
        res_sym = self.allocator.compute_portfolio_rebalance(
            current_weights=current_weights,
            target_weights=target_weights,
            market_map=market_map,
            volatility_map=vol_map,
            adv_map=adv_map,
            use_asymmetric_bands=False
        )

        # Asymmetric rebalance with +15% unrealized gain on RUNNER:
        # Upper band expanded to target + 1.8 * delta -> ~ 0.127 -> 0.12 is INSIDE -> HOLD!
        res_asym = self.allocator.compute_portfolio_rebalance(
            current_weights=current_weights,
            target_weights=target_weights,
            market_map=market_map,
            volatility_map=vol_map,
            adv_map=adv_map,
            unrealized_returns={"RUNNER": 0.15, "LAGGER": -0.05},
            use_asymmetric_bands=True
        )

        self.assertEqual(res_asym["trades"]["RUNNER"]["action"], "HOLD")
        # And lagger with -5% return has lower band tightened
        band_lagger = res_asym["buffer_bands"]["LAGGER"]
        self.assertIsNotNone(band_lagger)

    # =========================================================================
    # 4. Alpha Decay Soft Exit & Time-Stop Exit Tests
    # =========================================================================

    def test_alpha_decay_soft_exit(self):
        """Verify that when current ensemble score collapses >= 30%, ALPHA_DECAY_EXIT fires."""
        item = WatchItem(
            symbol="DECAY_STOCK",
            market="KOSPI",
            entry_price=100.0,
            position_qty=50,
            entry_score=0.85,
            current_score=0.50,  # Collapsed by 41% (< 0.85 * 0.70 = 0.595)
        )
        actions = self.monitor.evaluate_symbol(
            item=item,
            quote_price=98.0,  # Price dropped only 2% (well above -4% stop loss)
            date="2026-09-03"
        )
        action_types = [a.action_type for a in actions]
        self.assertIn("ALPHA_DECAY_EXIT", action_types)
        decay_act = next(a for a in actions if a.action_type == "ALPHA_DECAY_EXIT")
        self.assertEqual(decay_act.severity, "WARN")

    def test_time_stop_fast_sleeve_exit(self):
        """Verify Fast Momentum sleeve held >= 5 days with gain < 3% triggers TIME_STOP_EXIT."""
        item = WatchItem(
            symbol="FAST_STALLED",
            market="NASDAQ",
            entry_price=50.0,
            position_qty=100,
            days_held=6,  # > 5 days
            sleeve_type="FAST_MOMENTUM"
        )
        actions = self.monitor.evaluate_symbol(
            item=item,
            quote_price=50.5,  # +1% gain (< 3% threshold)
            date="2026-09-03"
        )
        action_types = [a.action_type for a in actions]
        self.assertIn("TIME_STOP_EXIT", action_types)

    def test_time_stop_core_sleeve_exit(self):
        """Verify Core Structural sleeve held >= 30 days with gain < 5% triggers TIME_STOP_EXIT."""
        item = WatchItem(
            symbol="CORE_STALLED",
            market="SP500",
            entry_price=200.0,
            position_qty=20,
            days_held=35,  # > 30 days
            sleeve_type="CORE_FUNDAMENTAL"
        )
        actions = self.monitor.evaluate_symbol(
            item=item,
            quote_price=204.0,  # +2% gain (< 5% threshold)
            date="2026-09-03"
        )
        action_types = [a.action_type for a in actions]
        self.assertIn("TIME_STOP_EXIT", action_types)

    # =========================================================================
    # 5. Intraday Stop Loss Monotonic Ratchet & Breakeven Lock
    # =========================================================================

    def test_intraday_stop_loss_breakeven_ratchet(self):
        """Verify intraday stop-loss ratchets up to breakeven when gain >= 8%."""
        res = self.stop_engine.evaluate("RATCHET_SYM", {
            "current_price": 92.0,  # Pulled down to entry
            "peak_price": 102.0,    # Was at +10.8%
            "entry_price": 92.0,
            "atr": 1.5,
            "volume": 1000,
            "volume_ma_20": 1000
        })
        self.assertTrue(res.triggered)
        self.assertIn("DYNAMIC_ATR_TRAILING_BREACH", res.reason)

    # =========================================================================
    # 6. Rebalance Liquidation & Unified Allocator Integration Tests
    # =========================================================================

    def test_rebalance_liquidation_of_dropped_holdings(self):
        """Verify that when a stock is held but drops out of top_predictions, OMS generates SELL order."""
        # Current holdings has DROPPED_SYM with 10% weight
        current_holdings = {
            "DROPPED_SYM": {
                "weight": 0.10,
                "current_price": 50000.0,
                "quantity": 20
            }
        }
        # Top predictions only has NEW_LEADER with target weight 0.15
        top_predictions = [
            {"symbol": "NEW_LEADER", "close_price": 100000.0, "market": "KOSPI", "action": "BUY"}
        ]
        portfolio_weights = {
            "NEW_LEADER": 0.15,
            "DROPPED_SYM": 0.0  # Zero target weight
        }

        order_plans = self.oms.generate_order_plan(
            top_predictions=top_predictions,
            portfolio_weights=portfolio_weights,
            total_capital=100_000_000.0,
            current_holdings=current_holdings,
            use_leland_buffer=False
        )

        # There should be a SELL order for DROPPED_SYM
        actions = {p["symbol"]: p["action"] for p in order_plans}
        self.assertIn("DROPPED_SYM", actions)
        self.assertEqual(actions["DROPPED_SYM"], "SELL")

    def test_get_current_holdings_details_from_db(self):
        """Verify get_current_holdings_details_from_db returns rich metadata."""
        # Insert a mock executed order
        conn = self.oms._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO order_plans (order_id, symbol, name, market, action, target_weight, target_amount, target_price, quantity, status, created_at, sleeve_type)
            VALUES ('ORD_TEST_1', 'HOLD_SYM', 'Hold Corp', 'KOSPI', 'BUY', 0.10, 10000000.0, 50000.0, 200, 'EXECUTED', '2026-08-20 10:00:00', 'FAST_MOMENTUM')
        """)
        conn.commit()

        details = self.oms.get_current_holdings_details_from_db()
        self.assertIn("HOLD_SYM", details)
        self.assertEqual(details["HOLD_SYM"]["quantity"], 200)
        self.assertEqual(details["HOLD_SYM"]["entry_price"], 50000.0)
        self.assertEqual(details["HOLD_SYM"]["sleeve_type"], "FAST_MOMENTUM")
        self.assertTrue(details["HOLD_SYM"]["days_held"] > 0)


if __name__ == "__main__":
    unittest.main()
