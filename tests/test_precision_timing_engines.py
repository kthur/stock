# -*- coding: utf-8 -*-
"""
Unit tests for 6 Precision Buy & Sell Timing Engines in ExecutionOMSEngine.
"""

import unittest
import numpy as np
import pandas as pd

from src.execution.oms_engine import ExecutionOMSEngine


class TestPrecisionTimingEngines(unittest.TestCase):

    def setUp(self):
        self.engine = ExecutionOMSEngine()

    def test_confluence_entry_score(self):
        # Strong confluence (high ensemble + high VCP + high volume + positive OBI)
        res_strong = self.engine.calculate_confluence_entry_score(
            ensemble_score=0.85,
            vcp_score=0.90,
            volume_surge_ratio=3.0,
            obi_score=0.50,
            price_above_ma50=True
        )
        self.assertGreaterEqual(res_strong['confluence_score'], 0.70)
        self.assertTrue(res_strong['is_valid_entry'])

        # Weak confluence (low ensemble)
        res_weak = self.engine.calculate_confluence_entry_score(
            ensemble_score=0.45,
            vcp_score=0.30,
            volume_surge_ratio=1.0,
            obi_score=-0.20,
            price_above_ma50=False
        )
        self.assertFalse(res_weak['is_valid_entry'])

    def test_scale_in_pyramiding_plan(self):
        total_shares = 1000

        # Stage 1: Probe (30%)
        p1 = self.engine.generate_scale_in_order_plan('AAPL', total_shares, current_stage=1)
        self.assertEqual(p1['action'], 'BUY_PROBE')
        self.assertEqual(p1['allocated_shares'], 300)

        # Stage 2: Breakout (50%)
        p2 = self.engine.generate_scale_in_order_plan('AAPL', total_shares, current_stage=2)
        self.assertEqual(p2['action'], 'BUY_BREAKOUT')
        self.assertEqual(p2['allocated_shares'], 500)

        # Stage 3: Pullback (20%)
        p3 = self.engine.generate_scale_in_order_plan('AAPL', total_shares, current_stage=3)
        self.assertEqual(p3['action'], 'BUY_PYRAMID')
        self.assertEqual(p3['allocated_shares'], 200)

    def test_signal_exhaustion_exit(self):
        # Score collapsed to 0.40 -> True
        is_exit, reason = self.engine.check_signal_exhaustion_exit(current_score=0.40)
        self.assertTrue(is_exit)
        self.assertEqual(reason, "ALPHA_SCORE_COLLAPSE")

        # Switching hurdle triggered (+10%p higher opportunity)
        is_switch, reason_sw = self.engine.check_signal_exhaustion_exit(
            current_score=0.60,
            top_candidates_avg_expected_return=0.15,
            holding_expected_return=0.03
        )
        self.assertTrue(is_switch)
        self.assertEqual(reason_sw, "OPPORTUNITY_COST_SWITCHING")

    def test_time_stop_exit(self):
        # Stalled for 15 days within [-2%, +3%] -> True
        is_exit, reason = self.engine.check_time_stop_exit(days_held=15, unrealized_return=0.01)
        self.assertTrue(is_exit)
        self.assertEqual(reason, "TIME_STOP_MOMENTUM_STALLED")

        # Gaining +10% after 15 days -> False (winner)
        is_gain, _ = self.engine.check_time_stop_exit(days_held=15, unrealized_return=0.10)
        self.assertFalse(is_gain)

    def test_order_flow_shock_exit(self):
        # Severe institutional dump (low MFI + heavy down volume)
        is_shock, reason = self.engine.check_order_flow_shock_exit(
            mfi_value=18.0,
            is_down_day=True,
            volume_ratio=4.0,
            obi=-0.70
        )
        self.assertTrue(is_shock)
        self.assertEqual(reason, "EMERGENCY_ORDER_FLOW_SHOCK")

    def test_4tier_profit_taking_plan(self):
        current_holdings = {
            'RUNNER_STOCK': {
                'quantity': 100,
                'entry_price': 100.0,
                'current_price': 130.0, # +30% profit (Tier 3)
                'days_held': 10,
                'current_score': 0.80
            },
            'TIER1_STOCK': {
                'quantity': 100,
                'entry_price': 100.0,
                'current_price': 109.0, # +9% profit (Tier 1)
                'days_held': 3,
                'current_score': 0.75
            },
            'LOSS_STOCK': {
                'quantity': 100,
                'entry_price': 100.0,
                'current_price': 90.0, # -10% loss (Stop loss)
                'days_held': 2,
                'current_score': 0.60
            }
        }

        # Mock prices dict with ATR ~ 2.0
        dates = pd.date_range('2026-01-01', periods=30, freq='B')
        prices_dict = {
            'RUNNER_STOCK': pd.DataFrame({'High': np.linspace(100, 132, 30), 'Low': np.linspace(98, 128, 30), 'Close': np.linspace(99, 130, 30)}, index=dates),
            'TIER1_STOCK': pd.DataFrame({'High': np.linspace(100, 110, 30), 'Low': np.linspace(98, 108, 30), 'Close': np.linspace(99, 109, 30)}, index=dates),
            'LOSS_STOCK': pd.DataFrame({'High': np.linspace(100, 92, 30), 'Low': np.linspace(98, 88, 30), 'Close': np.linspace(99, 90, 30)}, index=dates),
        }

        plans = self.engine.calculate_trailing_stop_plan(current_holdings, prices_dict, regime='BULL_LOW_VOL')
        self.assertIsInstance(plans, list)
        self.assertTrue(len(plans) >= 2)

        symbols_in_plan = [p['symbol'] for p in plans]
        self.assertIn('RUNNER_STOCK', symbols_in_plan)
        self.assertIn('LOSS_STOCK', symbols_in_plan)

        # Loss stock should have triggered stop loss
        loss_plan = next(p for p in plans if p['symbol'] == 'LOSS_STOCK')
        self.assertEqual(loss_plan['reason'], 'ATR_STOP_LOSS')


if __name__ == '__main__':
    unittest.main()
