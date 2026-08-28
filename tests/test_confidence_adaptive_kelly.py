# -*- coding: utf-8 -*-
"""
Unit tests for allocate_confidence_adaptive_kelly in PortfolioAllocator.
"""

import unittest
import pandas as pd

from src.risk.portfolio_allocator import PortfolioAllocator


class TestConfidenceAdaptiveKelly(unittest.TestCase):

    def setUp(self):
        self.allocator = PortfolioAllocator(default_max_weight=0.20, target_horizon=20)

    def test_adaptive_kelly_allocation_bounds(self):
        expected_returns = pd.Series({'AAPL': 0.08, 'MSFT': 0.05, 'GOOGL': 0.03, 'BAD': -0.02})
        volatilities = pd.Series({'AAPL': 0.015, 'MSFT': 0.018, 'GOOGL': 0.020, 'BAD': 0.025})
        conviction_scores = pd.Series({'AAPL': 0.85, 'MSFT': 0.65, 'GOOGL': 0.50, 'BAD': 0.20})

        weights = self.allocator.allocate_confidence_adaptive_kelly(
            expected_returns=expected_returns,
            volatilities=volatilities,
            conviction_scores=conviction_scores,
            max_weight=0.25,
            kelly_fraction=0.5
        )

        self.assertIsInstance(weights, dict)
        self.assertIn('AAPL', weights)
        self.assertIn('MSFT', weights)
        self.assertNotIn('BAD', weights)  # Negative expected return should receive 0 weight

        # Sum of weights <= 1.0
        self.assertLessEqual(sum(weights.values()), 1.0 + 1e-6)

        # High conviction + high return should get larger allocation
        self.assertGreater(weights['AAPL'], weights.get('GOOGL', 0.0))

    def test_empty_or_negative_returns(self):
        empty_weights = self.allocator.allocate_confidence_adaptive_kelly(pd.Series())
        self.assertEqual(empty_weights, {})

        all_neg = pd.Series({'A': -0.05, 'B': -0.10})
        neg_weights = self.allocator.allocate_confidence_adaptive_kelly(all_neg)
        self.assertEqual(neg_weights, {})


if __name__ == '__main__':
    unittest.main()
