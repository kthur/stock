# -*- coding: utf-8 -*-
"""
Unit tests for GNNSupplyChainEngine.
"""

import unittest
import numpy as np
import pandas as pd

from src.core.gnn_supply_chain import GNNSupplyChainEngine


class TestGNNSupplyChainEngine(unittest.TestCase):

    def setUp(self):
        self.engine = GNNSupplyChainEngine()

    def test_graph_adjacency_built(self):
        self.assertTrue(len(self.engine.adj) > 0)
        self.assertTrue(len(self.engine.in_adj) > 0)
        self.assertIn('NVDA', self.engine.adj)
        self.assertIn('000660', self.engine.in_adj)

    def test_compute_graph_momentum(self):
        # Create mock price history
        dates = pd.date_range('2026-01-01', periods=30, freq='B')
        prices_dict = {
            'NVDA': pd.DataFrame({'Close': np.linspace(100, 150, 30)}, index=dates),
            '000660': pd.DataFrame({'Close': np.linspace(80, 90, 30)}, index=dates),
            '042700': pd.DataFrame({'Close': np.linspace(20, 25, 30)}, index=dates),
            'AAPL': pd.DataFrame({'Close': np.linspace(180, 175, 30)}, index=dates),
        }

        scores = self.engine.compute_graph_momentum(prices_dict)
        self.assertIsInstance(scores, dict)
        self.assertIn('NVDA', scores)
        self.assertIn('000660', scores)
        self.assertIn('042700', scores)

        for sym, score in scores.items():
            self.assertTrue(0.0 <= score <= 1.0, f"Score out of range for {sym}: {score}")

        # NVDA strong uptrend should propagate high score to supplier 000660
        self.assertGreater(scores['000660'], 0.50)


if __name__ == '__main__':
    unittest.main()
