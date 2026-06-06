import random
import math
import sys
import unittest
from src.strategy.allocation import allocate_assets

class TestAllocateAssets(unittest.TestCase):
    def check_weights(self, prices, expected_empty=False):
        weights = allocate_assets(prices)
        if expected_empty:
            self.assertEqual(weights, {})
            return
        
        self.assertNotEqual(weights, {})
        
        # Verify all weights correspond to valid prices
        for k, w in weights.items():
            self.assertTrue(prices.get(k, 0) > 0, f"Asset {k} got weight but price is {prices.get(k)}")
            self.assertTrue(w >= 0, f"Weight for {k} is negative: {w}")
            
        # Verify sum is exactly 1.0
        # NOTE: checking exact float equality here
        total_weight = sum(weights.values())
        self.assertEqual(total_weight, 1.0, f"Sum is {total_weight}, not exactly 1.0")
        
        # Verify proportional mapping for valid prices
        # except for the largest asset which might be modified
        valid_prices = {k: v for k, v in prices.items() if v > 0}
        largest_asset = max(weights, key=lambda k: weights[k])
        total_valid_price = sum(valid_prices.values())
        
        for k, w in weights.items():
            expected_w = valid_prices[k] / total_valid_price
            if k != largest_asset:
                # the others should be exactly proportional
                self.assertEqual(w, expected_w)

    def test_empty(self):
        self.check_weights({}, expected_empty=True)
        
    def test_only_zero_or_negative(self):
        self.check_weights({'A': 0, 'B': -1, 'C': -0.0001}, expected_empty=True)

    def test_normal_prices(self):
        self.check_weights({'A': 10, 'B': 20, 'C': 70})
        
    def test_float_precision_edge_case(self):
        # A case where sum(weights) is naturally not 1.0 without adjustment
        # e.g. 1/3, 1/3, 1/3
        self.check_weights({'A': 1, 'B': 1, 'C': 1})
        
    def test_random_large_numbers(self):
        for _ in range(100):
            prices = {f"Asset{i}": random.uniform(1e10, 1e20) for i in range(100)}
            self.check_weights(prices)

    def test_random_small_numbers(self):
        for _ in range(100):
            prices = {f"Asset{i}": random.uniform(1e-300, 1e-290) for i in range(100)}
            self.check_weights(prices)

    def test_many_assets(self):
        prices = {f"Asset{i}": random.random() for i in range(10000)}
        self.check_weights(prices)
        
    def test_infinite_prices(self):
        # infinite price should probably not crash, but what is expected?
        pass

if __name__ == '__main__':
    unittest.main()
