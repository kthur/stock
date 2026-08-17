import sys
import unittest
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.risk.risk_manager import RiskManager, CrisisLevel

class TestRiskManagerUpgrades(unittest.TestCase):
    """Milestone 2 Risk Management Upgrades tests"""

    def setUp(self):
        self.rm = RiskManager(portfolio_value=1_000_000)
        self.rm.REGIME_ATR_MULTIPLIERS = {
            "strong_bull": {"stop": 3.0, "target": 5.0, "trail": 0.08},
            "weak_bull": {"stop": 2.5, "target": 4.0, "trail": 0.06},
            "weak_bear": {"stop": 1.5, "target": 2.5, "trail": 0.04},
            "strong_bear": {"stop": 1.0, "target": 2.0, "trail": 0.03},
        }

    def test_check_trailing_stop_emergency_exit(self):
        # price <= 0.0 should trigger emergency exit (True)
        self.assertTrue(self.rm.check_trailing_stop_signal("AAPL", -1.0, 100.0, 2.0))
        self.assertTrue(self.rm.check_trailing_stop_signal("AAPL", 0.0, 100.0, 2.0))

    def test_check_trailing_stop_invalid_atr(self):
        # atr <= 0.0 should not trigger trailing stop (False)
        self.assertFalse(self.rm.check_trailing_stop_signal("AAPL", 90.0, 100.0, 0.0))
        self.assertFalse(self.rm.check_trailing_stop_signal("AAPL", 90.0, 100.0, -1.0))

    def test_check_trailing_stop_basic(self):
        # regime weak_bull stop multiplier is 2.5. With atr=2.0, stop distance is 5.0.
        # highest_price = 100.0
        # If current_price is 95.0, highest_price - current_price = 5.0 >= 5.0 -> True
        self.assertTrue(self.rm.check_trailing_stop_signal("AAPL", 95.0, 100.0, 2.0, "weak_bull", 20.0))
        # If current_price is 96.0, highest_price - current_price = 4.0 < 5.0 -> False
        self.assertFalse(self.rm.check_trailing_stop_signal("AAPL", 96.0, 100.0, 2.0, "weak_bull", 20.0))

    def test_check_trailing_stop_crisis_tightening(self):
        # regime weak_bull stop multiplier is 2.5. With atr=2.0, base stop distance is 5.0.
        # Set crisis level to WATCH -> crisis stop multiplier is 0.80.
        # Tightened stop distance = 5.0 * 0.80 = 4.0.
        # highest_price = 100.0, current_price = 96.0 -> drawdown = 4.0 >= 4.0 -> True
        self.rm.crisis_detector.crisis_level = CrisisLevel.WATCH
        self.assertTrue(self.rm.check_trailing_stop_signal("AAPL", 96.0, 100.0, 2.0, "weak_bull", 20.0))

    def test_check_trailing_stop_drawdown_tightening(self):
        # regime weak_bull stop multiplier is 2.5. With atr=2.0, base stop distance is 5.0.
        # Set portfolio drawdown to 5% (peak=1M, portfolio=950k), max allowed is 20%.
        # drawdown_scaler = 1.0 - (0.05 / 0.20) = 0.75.
        # Tightened stop distance = 5.0 * 0.75 = 3.75.
        # highest_price = 100.0, current_price = 96.0 -> drawdown = 4.0 >= 3.75 -> True
        self.rm.peak_value = 1_000_000
        self.rm.portfolio_value = 950_000
        self.assertTrue(self.rm.check_trailing_stop_signal("AAPL", 96.0, 100.0, 2.0, "weak_bull", 20.0))

    def test_kelly_volatility_scaling(self):
        # Test Kelly sizing path with atr volatility scaling
        # With atr = 0.0, no volatility scaling
        qty_no_vol = self.rm.calculate_position_sizing(
            "AAPL", entry_price=100.0, stop_loss_price=95.0,
            win_rate=0.55, win_loss_ratio=1.5, atr=0.0
        )
        # With atr = 2.0, asset_vol_annual = (2.0/100) * sqrt(252) = 0.02 * 15.8745 = 0.3175
        # target_vol = 0.15. vol_scaler = 0.15 / 0.3175 = 0.4725
        qty_with_vol = self.rm.calculate_position_sizing(
            "AAPL", entry_price=100.0, stop_loss_price=95.0,
            win_rate=0.55, win_loss_ratio=1.5, atr=2.0
        )
        self.assertLess(qty_with_vol, qty_no_vol)

    def test_fixed_risk_crisis_scaling(self):
        # Test Fixed Risk sizing path with active crisis scaling

        # Use prices that prevent max position capping
        # entry_price=100.0, stop_loss_price=80.0 -> risk_per_share=20.0
        # max_loss = 2% of 1M = 20,000. max_value = 20,000 * 5 = 100,000 (1000 shares)
        # Cap is 200,000 value (2000 shares), so 1000 is well below the cap.

        # CrisisLevel NONE: 1.0x risk_mult, 1.0x position_mult
        self.rm.crisis_detector.crisis_level = CrisisLevel.NONE
        qty_none = self.rm.calculate_position_sizing(
            "AAPL", entry_price=100.0, stop_loss_price=80.0, atr=0.0
        )
        self.assertEqual(qty_none, 1000)

        # CrisisLevel WATCH: 0.75x risk_mult, 0.70x position_mult
        self.rm.crisis_detector.crisis_level = CrisisLevel.WATCH
        qty_watch = self.rm.calculate_position_sizing(
            "AAPL", entry_price=100.0, stop_loss_price=80.0, atr=0.0
        )
        self.assertEqual(qty_watch, 525)

        # CrisisLevel ACTIVE: 0.50x risk_mult, 0.40x position_mult
        self.rm.crisis_detector.crisis_level = CrisisLevel.ACTIVE
        qty_active = self.rm.calculate_position_sizing(
            "AAPL", entry_price=100.0, stop_loss_price=80.0, atr=0.0
        )
        self.assertEqual(qty_active, 200)

        # CrisisLevel SEVERE: 0.25x risk_mult, 0.15x position_mult
        self.rm.crisis_detector.crisis_level = CrisisLevel.SEVERE
        qty_severe = self.rm.calculate_position_sizing(
            "AAPL", entry_price=100.0, stop_loss_price=80.0, atr=0.0
        )
        self.assertEqual(qty_severe, 37)


if __name__ == "__main__":
    unittest.main(verbosity=2)
