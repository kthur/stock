import os
import sys
import unittest
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.core.strategy_engine import HybridStrategyEngine, TradeSignal

class TestStrategyUpdates(unittest.TestCase):
    """
    Unit tests for HybridStrategyEngine updates: volume expansion rules, low liquidity penalties,
    and normalized targets scaling.
    """
    def setUp(self):
        self.engine = HybridStrategyEngine()

    def test_volume_expansion_positive_trend(self):
        # 60 price bars with a clear positive trend (increasing prices)
        # MACD and EMA will reflect a positive trend
        closes = [float(100 + i) for i in range(60)]
        
        # Volume has a volume expansion:
        # Last 5 elements are 300,000. Prior 15 are 100,000.
        # 5-day volume SMA = 300,000. 20-day volume SMA = (15 * 100,000 + 5 * 300,000) / 20 = 150,000.
        # 300,000 > 1.5 * 150,000 (225,000). Volume expansion active.
        volumes = [100000.0] * 55 + [300000.0] * 5
        
        res = self.engine._compute_technical_indicators(closes, volume_bars=volumes)
        details = res.get("details", {})
        
        self.assertTrue(details.get("volume_expansion_active"))
        self.assertEqual(details.get("volume_bonus_applied"), 0.05)
        # Check that score is computed and bounded
        self.assertTrue(0.0 <= res["score"] <= 1.0)

    def test_volume_expansion_negative_trend(self):
        # 60 price bars with a clear negative trend (decreasing prices)
        # MACD and EMA will reflect a negative trend
        closes = [float(200 - i) for i in range(60)]
        
        # Volume expansion active
        volumes = [100000.0] * 55 + [300000.0] * 5
        
        res = self.engine._compute_technical_indicators(closes, volume_bars=volumes)
        details = res.get("details", {})
        
        self.assertTrue(details.get("volume_expansion_active"))
        self.assertEqual(details.get("volume_bonus_applied"), -0.05)
        self.assertTrue(0.0 <= res["score"] <= 1.0)

    def test_liquidity_penalty_low_floating_shares(self):
        # Standard price series
        closes = [100.0] * 60
        # Normal volumes (no volume expansion)
        volumes = [100000.0] * 60
        
        # Extremely low floating shares: 10.0
        # Floating value = 100.0 * 10.0 = 1,000 (which is < 10,000,000 for USD close < 1000)
        res = self.engine._compute_technical_indicators(closes, volume_bars=volumes, floating_shares=10.0)
        details = res.get("details", {})
        
        self.assertTrue(details.get("low_liquidity_penalty"))
        self.assertLessEqual(res["score"], 0.4)

    def test_target_allocation_confidence_scaling(self):
        # Price bars
        # Creating mock bars with close and volume attributes
        class MockBar:
            def __init__(self, close, volume, norm_volume=1.0, norm_floating_value=1.0):
                self.close = close
                self.volume = volume
                self.norm_volume = norm_volume
                self.norm_floating_value = norm_floating_value
        
        price_bars = [MockBar(100.0, 1500000.0) for _ in range(60)]
        
        # Base run: normal normalized features (no scaling down)
        market_data_base = {
            "price": 100.0,
            "volume": 1500000.0,
            "bid": 99.9,
            "ask": 100.1,
            "norm_volume": 1.0,
            "norm_floating_value": 1.0
        }
        res_base = self.engine.analyze(
            symbol="TEST",
            market_data=market_data_base,
            news_sentiment=0.0,
            price_bars=price_bars
        )
        
        # Penalty run: low norm_volume (0.002, which is < 0.01)
        market_data_penalty = {
            "price": 100.0,
            "volume": 1500000.0,
            "bid": 99.9,
            "ask": 100.1,
            "norm_volume": 0.002,
            "norm_floating_value": 1.0
        }
        res_penalty = self.engine.analyze(
            symbol="TEST",
            market_data=market_data_penalty,
            news_sentiment=0.0,
            price_bars=price_bars
        )
        
        # Verification: Confidence should be scaled down
        # Base norm_volume = 1.0 (no scaling)
        # Penalty norm_volume = 0.002 (scaled by 0.002/0.01 = 0.2)
        # So res_penalty.confidence should be approximately 0.2 * res_base.confidence
        self.assertLess(res_penalty.confidence, res_base.confidence)
        self.assertAlmostEqual(res_penalty.confidence, res_base.confidence * 0.2, places=4)

if __name__ == "__main__":
    unittest.main()
