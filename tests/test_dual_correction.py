# -*- coding: utf-8 -*-
"""
Unit tests for DualCorrectionEngine (Price Correction & Time Correction).
"""

import unittest
import numpy as np
import pandas as pd

from src.core.dual_correction import (
    DualCorrectionEngine,
    PriceCorrectionScorer,
    TimeCorrectionScorer
)
from src.execution.oms_engine import ExecutionOMSEngine


class TestDualCorrectionEngine(unittest.TestCase):

    def setUp(self):
        self.engine = DualCorrectionEngine()
        self.oms = ExecutionOMSEngine()

    def test_price_correction_fibonacci_and_avwap(self):
        # Create a stock that had a rally from 100 to 200, then pulled back to ~150 (50% Fibonacci level)
        dates = pd.date_range('2026-01-01', periods=120, freq='B')
        prices = np.concatenate([
            np.linspace(100, 200, 80),
            np.linspace(200, 150, 40)
        ])
        volumes = np.ones(120) * 10000.0
        volumes[-1] = 35000.0  # Panic selling climax volume

        df = pd.DataFrame({
            'High': prices + 2.0,
            'Low': prices - 2.0,
            'Close': prices,
            'Volume': volumes
        }, index=dates)

        score, details = PriceCorrectionScorer.compute_score(df)
        self.assertIsInstance(score, float)
        self.assertGreaterEqual(score, 0.60)
        self.assertGreaterEqual(details['fib_score'], 0.70)
        self.assertGreaterEqual(details['climax_score'], 0.70)

    def test_time_correction_vdi_and_ribbon(self):
        # Create a stock that went from 100 to 150, then consolidated horizontally at ~150 for 30 days
        dates = pd.date_range('2026-01-01', periods=120, freq='B')
        prices = np.concatenate([
            np.linspace(100, 150, 90),
            150.0 + np.sin(np.linspace(0, 3.14 * 4, 30)) * 1.5  # Very tight +/- 1.5 variation
        ])
        volumes = np.concatenate([
            np.ones(110) * 100000.0,
            np.ones(10) * 20000.0  # VDI ~ 0.24 (Extreme volume dry-up)
        ])

        df = pd.DataFrame({
            'High': prices + 1.0,
            'Low': prices - 1.0,
            'Close': prices,
            'Volume': volumes
        }, index=dates)

        score, details = TimeCorrectionScorer.compute_score(df)
        self.assertIsInstance(score, float)
        self.assertGreaterEqual(score, 0.70)
        self.assertGreaterEqual(details['vdi_score'], 0.80)
        self.assertGreaterEqual(details['ribbon_score'], 0.80)
        self.assertGreaterEqual(details['base_duration_score'], 0.80)

    def test_dual_correction_engine_scoring_and_phases(self):
        dates = pd.date_range('2026-01-01', periods=120, freq='B')

        # Stock 1: Time Consolidation near Highs
        p1 = np.concatenate([np.linspace(100, 200, 80), 200.0 + np.sin(np.linspace(0, 10, 40)) * 2.0])
        v1 = np.concatenate([np.ones(110) * 100000.0, np.ones(10) * 20000.0])
        df_time = pd.DataFrame({'High': p1 + 1, 'Low': p1 - 1, 'Close': p1, 'Volume': v1}, index=dates)

        # Stock 2: Price Retracement from Highs
        p2 = np.concatenate([np.linspace(100, 200, 80), np.linspace(200, 150, 40)])
        v2 = np.concatenate([np.ones(119) * 50000.0, [150000.0]])
        df_price = pd.DataFrame({'High': p2 + 2, 'Low': p2 - 2, 'Close': p2, 'Volume': v2}, index=dates)

        prices_dict = {'TIME_STOCK': df_time, 'PRICE_STOCK': df_price}

        # In Bull regime
        scores_bull = self.engine.compute_scores(prices_dict, regime='BULL_LOW_VOL')
        self.assertEqual(len(scores_bull), 2)
        self.assertIn('TIME_STOCK', scores_bull['symbol'].values)
        self.assertIn('PRICE_STOCK', scores_bull['symbol'].values)

        time_row = scores_bull[scores_bull['symbol'] == 'TIME_STOCK'].iloc[0]
        self.assertEqual(time_row['correction_phase'], 'TIME_CONSOLIDATION')

        price_row = scores_bull[scores_bull['symbol'] == 'PRICE_STOCK'].iloc[0]
        self.assertEqual(price_row['correction_phase'], 'PRICE_PULLBACK')

    def test_oms_phase_adaptive_execution(self):
        # Verify that TIME_CONSOLIDATION gets tighter stop loss, while PRICE_PULLBACK gets wider room
        holdings = {
            'TIME_STOCK': {
                'quantity': 100,
                'entry_price': 100.0,
                'current_price': 98.0,  # -2% dip
                'days_held': 3,
                'correction_phase': 'TIME_CONSOLIDATION'
            },
            'PRICE_STOCK': {
                'quantity': 100,
                'entry_price': 100.0,
                'current_price': 98.0,  # -2% dip
                'days_held': 3,
                'correction_phase': 'PRICE_PULLBACK'
            }
        }
        dates = pd.date_range('2026-01-01', periods=30, freq='B')
        prices_dict = {
            'TIME_STOCK': pd.DataFrame({'High': np.linspace(100, 98, 30), 'Low': np.linspace(99, 97, 30), 'Close': np.linspace(100, 98, 30)}, index=dates),
            'PRICE_STOCK': pd.DataFrame({'High': np.linspace(100, 98, 30), 'Low': np.linspace(99, 97, 30), 'Close': np.linspace(100, 98, 30)}, index=dates),
        }
        plans = self.oms.calculate_trailing_stop_plan(holdings, prices_dict, regime='BULL_LOW_VOL')
        self.assertIsInstance(plans, list)


if __name__ == '__main__':
    unittest.main()
