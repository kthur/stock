"""Unit tests for VCP Real-Time Breakout Trigger & Supply/Demand Alpha Engine"""

import unittest
import numpy as np
import pandas as pd
from src.ai.vcp_realtime_trigger import VCPBreakoutTrigger, VCPBreakoutSignal
from src.ai.vcp_detector import detect_vcp


class TestVCPRealtimeTrigger(unittest.TestCase):

    def setUp(self):
        self.trigger = VCPBreakoutTrigger(breakout_vol_threshold=1.5, near_pivot_pct=0.02, min_vcp_score=50.0)
        # Create mock 100-day daily price history DataFrame
        dates = pd.date_range(end="2026-07-24", periods=100)
        np.random.seed(42)
        base_price = 10000.0
        prices = base_price + np.cumsum(np.random.randn(100) * 100.0)
        
        self.df_hist = pd.DataFrame({
            "Date": dates,
            "Open": prices - 50.0,
            "High": prices + 200.0,
            "Low": prices - 200.0,
            "Close": prices,
            "Volume": np.full(100, 100000.0),
            "inst_net_buy_5d": np.full(100, 50000.0),
            "foreigner_net_buy_5d": np.full(100, 30000.0),
        }).set_index("Date")

    def test_pivot_price_calculation(self):
        pivot_info = self.trigger.calculate_pivot_price(self.df_hist)
        self.assertIn("pivot_price", pivot_info)
        self.assertIn("avg_volume_20", pivot_info)
        self.assertGreater(pivot_info["pivot_price"], 0.0)
        self.assertEqual(pivot_info["avg_volume_20"], 100000.0)

    def test_supply_demand_score(self):
        sd_score = self.trigger.compute_supply_demand_score(self.df_hist)
        self.assertGreaterEqual(sd_score, 0.5)
        self.assertLessEqual(sd_score, 1.0)

    def test_breakout_detection_positive(self):
        pivot_info = self.trigger.calculate_pivot_price(self.df_hist)
        pivot_price = pivot_info["pivot_price"]

        # Current price above pivot and current volume 2.0x average -> Valid breakout
        signal = self.trigger.evaluate_realtime_breakout(
            symbol="005930",
            current_price=pivot_price * 1.01,
            current_volume=200000.0,  # 2.0x
            hist_df=self.df_hist,
            vcp_score=75.0,
        )

        self.assertTrue(signal.is_breakout)
        self.assertEqual(signal.symbol, "005930")
        self.assertGreaterEqual(signal.volume_ratio, 1.5)

    def test_breakout_detection_negative_low_volume(self):
        pivot_info = self.trigger.calculate_pivot_price(self.df_hist)
        pivot_price = pivot_info["pivot_price"]

        # Current price above pivot but volume only 1.0x average -> No breakout
        signal = self.trigger.evaluate_realtime_breakout(
            symbol="AAPL",
            current_price=pivot_price * 1.01,
            current_volume=100000.0,  # 1.0x < 1.5x
            hist_df=self.df_hist,
            vcp_score=75.0,
        )

        self.assertFalse(signal.is_breakout)
        self.assertLess(signal.volume_ratio, 1.5)

    def test_vcp_detector_pivot_price_integration(self):
        result = detect_vcp(self.df_hist)
        self.assertIn("pivot_price", result)
        self.assertGreater(result["pivot_price"], 0.0)


if __name__ == "__main__":
    unittest.main()
