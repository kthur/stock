# -*- coding: utf-8 -*-
"""
Unit tests for AdaptiveOrderRouter and Orderbook Imbalance (OBI).
"""

import unittest
from src.execution.adaptive_router import AdaptiveOrderRouter


class TestAdaptiveOrderRouter(unittest.TestCase):

    def setUp(self):
        self.router = AdaptiveOrderRouter(default_tranches=5)

    def test_orderbook_imbalance_calculation(self):
        # Heavy buy depth
        bids = [(100.0, 5000), (99.9, 4000), (99.8, 3000)]
        asks = [(100.1, 1000), (100.2, 1000), (100.3, 1000)]
        obi_buy = self.router.compute_orderbook_imbalance(bids, asks)
        self.assertGreater(obi_buy, 0.50)

        # Heavy sell depth
        bids_light = [(100.0, 500), (99.9, 500)]
        asks_heavy = [(100.1, 5000), (100.2, 4000)]
        obi_sell = self.router.compute_orderbook_imbalance(bids_light, asks_heavy)
        self.assertLess(obi_sell, -0.50)

    def test_adaptive_slicing_schedule(self):
        total_shares = 10000
        # Positive OBI (Buy pressure) -> front-loaded schedule
        sched_fast = self.router.generate_adaptive_schedule(
            symbol='AAPL',
            total_quantity=total_shares,
            side='BUY',
            obi=0.60,
            num_tranches=5
        )
        self.assertEqual(len(sched_fast), 5)
        sum_shares = sum(t['shares'] for t in sched_fast)
        self.assertEqual(sum_shares, total_shares)
        # First tranche should be larger than last tranche
        self.assertGreater(sched_fast[0]['shares'], sched_fast[-1]['shares'])


if __name__ == '__main__':
    unittest.main()
