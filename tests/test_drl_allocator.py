"""
test_drl_allocator.py — Unit Tests for Deep Reinforcement Learning Allocator
"""

import os
import sys
import unittest
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "trading_system")))

from src.ai.drl_allocator import DRLPortfolioAllocator


class TestDRLAllocator(unittest.TestCase):

    def test_drl_portfolio_allocator(self):
        allocator = DRLPortfolioAllocator(num_strategies=23)
        base_w = {"regression": 0.10, "surge": 0.10, "stat_arb": 0.10}

        weights = allocator.allocate_weights(
            regime_code=2,  # BEAR_HIGH_VOL
            vix=28.5,
            rolling_sharpes={"s_6": 2.5, "s_13": 2.1},
            base_weights=base_w
        )

        self.assertIn("stat_arb", weights)
        self.assertIn("vol_target", weights)
        self.assertAlmostEqual(sum(weights.values()), 1.0, places=4)
        self.assertTrue(all(w >= 0.0 for w in weights.values()))


if __name__ == "__main__":
    unittest.main()
