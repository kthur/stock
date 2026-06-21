import unittest
from src.strategy.allocation import allocate_assets

class TestAllocateAssetsEdge(unittest.TestCase):
    def test_nan_price(self):
        prices = {'A': float('nan'), 'B': 10}
        weights = allocate_assets(prices)
        # NaN > 0 is False in python, so it should be filtered out
        self.assertEqual(weights, {'B': 1.0})

    def test_inf_price(self):
        prices = {'A': float('inf'), 'B': 10}
        weights = allocate_assets(prices)
        # inf > 0 is True, so total_price = inf + 10 = inf
        # weights = {'A': inf/inf, 'B': 10/inf} = {'A': nan, 'B': 0.0}
        # sum = nan + 0.0 = nan
        # remainder = 1.0 - nan = nan
        # largest = max() wait, max with nan is undefined, but max() iterates.
        print("INF WEIGHTS:", weights)

if __name__ == '__main__':
    unittest.main()
