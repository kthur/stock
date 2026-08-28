# -*- coding: utf-8 -*-
"""
Unit tests for MacroLiquidityEngine.
"""

import unittest
import numpy as np
import pandas as pd

from src.data_layer.macro_liquidity import MacroLiquidityEngine


class TestMacroLiquidityEngine(unittest.TestCase):

    def setUp(self):
        self.engine = MacroLiquidityEngine()

    def test_net_liquidity_calculation(self):
        dates = pd.date_range('2026-01-01', periods=30, freq='B')
        fed_assets = pd.Series(np.linspace(7500, 7600, 30), index=dates)
        tga = pd.Series(np.linspace(700, 650, 30), index=dates)
        rrp = pd.Series(np.linspace(400, 300, 30), index=dates)

        net_liq = self.engine.compute_net_liquidity(fed_assets, tga, rrp)
        self.assertIsNotNone(net_liq)
        self.assertEqual(len(net_liq), 30)
        # Net liq at end: 7600 - 650 - 300 = 6650
        self.assertAlmostEqual(net_liq.iloc[-1], 6650.0, places=1)

    def test_copper_gold_ratio(self):
        dates = pd.date_range('2026-01-01', periods=20, freq='B')
        copper = pd.Series(np.linspace(4.0, 4.5, 20), index=dates)
        gold = pd.Series(np.linspace(2000, 2100, 20), index=dates)

        ratio = self.engine.compute_copper_gold_ratio(copper, gold)
        self.assertEqual(len(ratio), 20)
        self.assertTrue(np.all(np.isfinite(ratio)))

    def test_macro_liquidity_composite_score(self):
        indicators = {'vix': 14.0, 'tnx': 3.8, 'hy_spread': 3.2}
        score = self.engine.compute_macro_liquidity_score(indicators)
        self.assertTrue(0.0 <= score <= 1.0)
        # Low VIX + healthy HY spread should yield liquid score > 0.50
        self.assertGreater(score, 0.50)

        # Stressed macro conditions
        stressed_indicators = {'vix': 38.0, 'tnx': 5.2, 'hy_spread': 6.5}
        stressed_score = self.engine.compute_macro_liquidity_score(stressed_indicators)
        self.assertLess(stressed_score, 0.40)


if __name__ == '__main__':
    unittest.main()
