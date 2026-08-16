import unittest
import numpy as np
from src.core.stat_arb import StatisticalArbitrageEngine
from src.core.hft_engine import HFTEngine

# Mandatory Integrity Warning
# DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results,
# create dummy/facade implementations, or circumvent the intended task. A Forensic
# Auditor will independently verify your work. Integrity violations WILL be detected
# and your work WILL be rejected.


class TestStatArbExecution(unittest.TestCase):

    def setUp(self):
        self.stat_arb = StatisticalArbitrageEngine()
        self.hft = HFTEngine()

    def test_stat_arb_pair_scanning(self):
        """Test StatisticalArbitrageEngine find_cointegrated_pairs with cointegrated prices."""
        # Create cointegrated series
        np.random.seed(42)
        steps = 100

        # s1: random walk
        p1 = np.cumsum(np.random.normal(0, 0.5, steps)) + 100.0
        # s2: s1 + stationary noise
        p2 = p1 + np.random.normal(0, 0.1, steps)

        # At the very end, force a spread divergence to trigger a signal below stop-loss threshold
        p1[-1] = p1[-1] + 0.15  # s1 spikes up relative to s2 (z-score = 2.88 in [1.5, 3.2], SHORT_s1_LONG_s2)

        prices_dict = {
            "AAPL": list(p1),
            "MSFT": list(p2)
        }

        pairs = self.stat_arb.find_cointegrated_pairs(prices_dict)
        self.assertTrue(len(pairs) > 0)

        pair_info = pairs[0]
        self.assertEqual(pair_info["pair"], ("AAPL", "MSFT"))
        self.assertTrue(pair_info["z_score"] > 2.0)
        self.assertEqual(pair_info["signal"], "SHORT_AAPL_LONG_MSFT")
        self.assertGreater(pair_info["correlation"], 0.8)

    def test_twap_execution_slicing(self):
        """Test TWAP order slicing correctness and slippage."""
        symbol = "AAPL"
        action = "BUY"
        total_quantity = 10005
        duration_minutes = 30
        intervals = 5
        start_price = 150.0

        records = self.hft.execute_twap(
            symbol=symbol,
            action=action,
            total_quantity=total_quantity,
            duration_minutes=duration_minutes,
            intervals=intervals,
            start_price=start_price
        )

        self.assertEqual(len(records), intervals)

        # 10005 / 5 = 2001 exactly, remainder = 0
        total_executed = sum(r["quantity"] for r in records)
        self.assertEqual(total_executed, total_quantity)
        for r in records:
            self.assertEqual(r["quantity"], 2001)
            self.assertEqual(r["symbol"], symbol)
            self.assertEqual(r["action"], action)
            self.assertTrue(r["slippage"] > 0)

            # Verify exact price formula used in execute_twap
            expected_slippage = 0.0001 * (r["quantity"] / 1000.0) * start_price
            expected_price = start_price + expected_slippage + (0.0005 * start_price * (r["slice_index"] - intervals / 2) / max(1, intervals))
            self.assertAlmostEqual(r["price"], expected_price, places=2)

    def test_vwap_execution_slicing(self):
        """Test VWAP volume-weighted order slicing correctness."""
        symbol = "MSFT"
        action = "SELL"
        total_quantity = 10000
        duration_minutes = 20
        intervals = 4
        start_price = 250.0
        # Volume profile sums to 1.0
        volume_profile = [0.4, 0.1, 0.1, 0.4]

        records = self.hft.execute_vwap(
            symbol=symbol,
            action=action,
            total_quantity=total_quantity,
            duration_minutes=duration_minutes,
            volume_profile=volume_profile,
            intervals=intervals,
            start_price=start_price
        )

        self.assertEqual(len(records), intervals)

        # Expected slices: 4000, 1000, 1000, 4000
        expected_quantities = [4000, 1000, 1000, 4000]
        for idx, r in enumerate(records):
            self.assertEqual(r["quantity"], expected_quantities[idx])
            self.assertEqual(r["symbol"], symbol)
            self.assertEqual(r["action"], action)
            self.assertTrue(r["slippage"] > 0)

            # Verify exact price formula used in execute_vwap
            volume_share = volume_profile[idx]
            impact_factor = (r["quantity"] / 1000.0) / (volume_share + 1e-5)
            expected_slippage = 0.00005 * impact_factor * start_price
            expected_price = start_price - expected_slippage + (0.0005 * start_price * (idx - intervals / 2) / max(1, intervals))
            self.assertAlmostEqual(r["price"], expected_price, places=2)


if __name__ == '__main__':
    unittest.main()
