import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.risk.risk_manager import RiskManager, RiskLevel, CrisisDetector, CrisisLevel


class TestRiskManagerKelly(unittest.TestCase):
    """Kelly Criterion fraction tests"""

    def setUp(self):
        self.rm = RiskManager(portfolio_value=1_000_000)

    def test_kelly_positive_win_rate(self):
        f = self.rm.calculate_kelly_fraction(0.55, 1.5, half_kelly=True)
        self.assertGreater(f, 0.0)
        self.assertLess(f, 1.0)

    def test_kelly_zero_for_negative_edge(self):
        f = self.rm.calculate_kelly_fraction(0.4, 1.0, half_kelly=True)
        self.assertEqual(f, 0.0)

    def test_kelly_half_is_less_than_full(self):
        full = self.rm.calculate_kelly_fraction(0.52, 1.2, half_kelly=False)
        half = self.rm.calculate_kelly_fraction(0.52, 1.2, half_kelly=True)
        self.assertAlmostEqual(half, full / 2.0, places=6)

    def test_kelly_capped_at_max_position_pct(self):
        f = self.rm.calculate_kelly_fraction(0.9, 5.0, half_kelly=False)
        self.assertLessEqual(f, self.rm.max_position_size_pct)

    def test_kelly_zero_for_zero_win_loss_ratio(self):
        f = self.rm.calculate_kelly_fraction(0.5, 0.0, half_kelly=True)
        self.assertEqual(f, 0.0)


class TestRiskManagerPositionSizing(unittest.TestCase):
    """Position sizing calculation tests"""

    def setUp(self):
        self.rm = RiskManager(portfolio_value=1_000_000)
        self.rm.max_position_size_pct = 0.20

    def test_position_sizing_basic(self):
        qty = self.rm.calculate_position_sizing(
            "AAPL", entry_price=150.0, stop_loss_price=142.0,
        )
        self.assertGreater(qty, 0)

    def test_position_sizing_zero_for_invalid_stop(self):
        qty = self.rm.calculate_position_sizing(
            "AAPL", entry_price=150.0, stop_loss_price=160.0,
        )
        self.assertEqual(qty, 0)

    def test_position_sizing_with_kelly(self):
        qty = self.rm.calculate_position_sizing(
            "AAPL", entry_price=150.0, stop_loss_price=142.0,
            win_rate=0.55, win_loss_ratio=1.5,
        )
        self.assertGreater(qty, 0)

    def test_position_sizing_respects_position_limit(self):
        self.rm.set_position_limit("AAPL", 50)
        qty = self.rm.calculate_position_sizing(
            "AAPL", entry_price=10.0, stop_loss_price=9.5,
        )
        self.assertLessEqual(qty, 50)

    def test_max_position_size_calculation(self):
        max_qty = self.rm.calculate_max_position_size(100.0)
        expected = int(1_000_000 * 0.20 / 100.0)
        self.assertEqual(max_qty, expected)


class TestRiskManagerATR(unittest.TestCase):
    """ATR-based stop/target tests"""

    def setUp(self):
        self.rm = RiskManager(portfolio_value=1_000_000)

    def test_atr_stop_below_entry(self):
        stop = self.rm.calculate_atr_based_stop(100.0, 2.0)
        self.assertLess(stop, 100.0)

    def test_atr_target_above_entry(self):
        target = self.rm.calculate_atr_based_target(100.0, 2.0)
        self.assertGreater(target, 100.0)

    def test_atr_stop_has_floor(self):
        stop = self.rm.calculate_atr_based_stop(100.0, 50.0)
        self.assertGreaterEqual(stop, 100.0 * (1 - 0.05 * 2))

    def test_atr_target_has_ceiling(self):
        target = self.rm.calculate_atr_based_target(100.0, 50.0)
        self.assertLessEqual(target, 100.0 * (1 + self.rm.default_take_profit_pct * 2))


class TestRiskManagerVolatility(unittest.TestCase):
    """VIX-based volatility scaling tests"""

    def setUp(self):
        self.rm = RiskManager(portfolio_value=1_000_000)

    def test_vol_scalar_normal_vix(self):
        s = self.rm._volatility_scalar(20.0)
        self.assertEqual(s, 1.0)

    def test_vol_scalar_high_vix(self):
        s = self.rm._volatility_scalar(35.0)
        self.assertLess(s, 1.0)

    def test_vol_scalar_low_vix(self):
        s = self.rm._volatility_scalar(10.0)
        self.assertGreater(s, 1.0)

    def test_vol_scalar_extreme_vix(self):
        s = self.rm._volatility_scalar(45.0)
        self.assertAlmostEqual(s, 0.444, places=3)


class TestRiskManagerRiskOff(unittest.TestCase):
    """check_risk_off_signal tests"""

    def setUp(self):
        self.rm = RiskManager(portfolio_value=1_000_000)

    def test_risk_off_when_vix_high(self):
        self.assertTrue(self.rm.check_risk_off_signal(30.0))

    def test_risk_off_false_when_vix_low(self):
        self.assertFalse(self.rm.check_risk_off_signal(20.0))

    def test_risk_off_default_threshold(self):
        self.assertTrue(self.rm.check_risk_off_signal(25.0))
        self.assertFalse(self.rm.check_risk_off_signal(24.99))

    def test_risk_off_fallback_on_none(self):
        vix = self.rm.check_risk_off_signal()
        self.assertIn(vix, (True, False))


class TestRiskManagerVarCvar(unittest.TestCase):
    """VaR / CVaR calculation tests"""

    def setUp(self):
        self.rm = RiskManager(portfolio_value=1_000_000)

    def test_var_empty_returns_zero(self):
        self.assertEqual(self.rm.calculate_var([]), 0.0)

    def test_var_always_negative_or_zero(self):
        returns = [0.01, -0.02, 0.015, -0.005, -0.03, 0.008, -0.01, 0.02]
        var = self.rm.calculate_var(returns, 0.95)
        self.assertLessEqual(var, 0.0)

    def test_cvar_empty_returns_zero(self):
        self.assertEqual(self.rm.calculate_cvar([]), 0.0)

    def test_cvar_more_extreme_than_var(self):
        returns = [0.01, -0.02, 0.015, -0.005, -0.03, 0.008, -0.01, 0.02,
                   -0.04, 0.005, -0.015, 0.012, -0.025, 0.003]
        var = self.rm.calculate_var(returns, 0.95)
        cvar = self.rm.calculate_cvar(returns, 0.95)
        self.assertLessEqual(cvar, var)


class TestRiskManagerRiskLevel(unittest.TestCase):
    """Risk level calculation tests"""

    def setUp(self):
        self.rm = RiskManager(portfolio_value=1_000_000)

    def test_risk_level_low_initial(self):
        level = self.rm.calculate_risk_level({})
        self.assertEqual(level, RiskLevel.LOW)

    def test_risk_level_critical_at_max_drawdown(self):
        self.rm.update_portfolio_value(1_000_000)
        self.rm.peak_value = 1_000_000
        self.rm.portfolio_value = 750_000  # 25% drawdown
        level = self.rm.calculate_risk_level({})  # empty positions to isolate drawdown
        self.assertEqual(level, RiskLevel.CRITICAL)

    def test_risk_level_medium_at_half_drawdown(self):
        self.rm.update_portfolio_value(1_000_000)
        self.rm.peak_value = 1_000_000
        self.rm.portfolio_value = 940_000  # 6% drawdown (between 5% and 10%)
        level = self.rm.calculate_risk_level({})  # empty positions to isolate drawdown
        self.assertEqual(level, RiskLevel.MEDIUM)


class TestRiskManagerDrawdown(unittest.TestCase):
    """Drawdown calculation tests"""

    def setUp(self):
        self.rm = RiskManager(portfolio_value=1_000_000)

    def test_drawdown_zero_when_at_peak(self):
        self.rm.peak_value = 1_000_000
        self.rm.portfolio_value = 1_000_000
        self.assertAlmostEqual(self.rm.calculate_drawdown(), 0.0)

    def test_drawdown_positive_when_below_peak(self):
        self.rm.peak_value = 1_000_000
        self.rm.portfolio_value = 900_000
        self.assertAlmostEqual(self.rm.calculate_drawdown(), 0.10, places=4)

    def test_drawdown_updates_peak(self):
        self.rm.update_portfolio_value(1_200_000)
        self.assertEqual(self.rm.peak_value, 1_200_000)
        self.rm.update_portfolio_value(1_100_000)
        self.assertEqual(self.rm.peak_value, 1_200_000)  # peak unchanged

    def test_risk_adjusted_position_size(self):
        base = 100
        adj = self.rm.get_risk_adjusted_position_size(
            base, RiskLevel.HIGH
        )
        self.assertEqual(adj, 50)


class TestRiskManagerLiquidity(unittest.TestCase):
    """Liquidity screening tests (preferred stocks, SPACs, zero volume)"""

    def setUp(self):
        self.rm = RiskManager(portfolio_value=1_000_000)

    def test_screen_liquidity_valid_stock(self):
        self.assertTrue(self.rm.screen_liquidity("005930", "삼성전자", 1000000))
        self.assertFalse(self.rm.is_illiquid_or_preferred("005930", "삼성전자", 1000000))

    def test_screen_liquidity_preferred_stocks(self):
        self.assertFalse(self.rm.screen_liquidity("005935", "삼성전자우", 500000))
        self.assertTrue(self.rm.is_illiquid_or_preferred("005935", "삼성전자우", 500000))
        self.assertFalse(self.rm.screen_liquidity("000665", "SK하이닉스1우", 500000))
        self.assertFalse(self.rm.screen_liquidity("00593K", "삼성전자우B", 500000))

    def test_screen_liquidity_spac(self):
        self.assertFalse(self.rm.screen_liquidity("300000", "미래에셋스팩1호", 100000))
        self.assertTrue(self.rm.is_illiquid_or_preferred("300000", "미래에셋스팩1호", 100000))
        self.assertFalse(self.rm.screen_liquidity("300001", "ACME SPAC CORP", 100000))

    def test_screen_liquidity_zero_volume(self):
        self.assertFalse(self.rm.screen_liquidity("005930", "삼성전자", 0))
        self.assertTrue(self.rm.is_illiquid_or_preferred("005930", "삼성전자", 0))


class TestCrisisDetectorLevels(unittest.TestCase):
    """CrisisDetector level classification and failsafe tests"""

    def setUp(self):
        self.detector = CrisisDetector()

    def test_crisis_detector_levels(self):
        self.assertEqual(self.detector.evaluate(vix=18.0), CrisisLevel.NONE)
        self.assertEqual(self.detector.evaluate(vix=32.0), CrisisLevel.ACTIVE)
        self.assertEqual(self.detector.evaluate(vix=42.0), CrisisLevel.SEVERE)

    def test_crisis_detector_macro_escalation(self):
        # Pre-fill stable 6-day histories so macro spikes register on first call
        self.detector._vix_history.extend([20.0] * 6)
        self.detector._usdkrw_history.extend([1350.0] * 6)
        self.detector._oil_history.extend([80.0] * 6)
        self.detector._tnx_history.extend([4.0] * 6)
        self.detector._dxy_history.extend([100.0] * 6)
        level = self.detector.evaluate(
            vix=28.0,
            daily_volume_ratio=3.0,
            usdkrw=1700.0,
            oil=150.0,
            tnx=6.5,
            dxy=120.0,
        )
        self.assertIn(level, (CrisisLevel.WATCH, CrisisLevel.ACTIVE, CrisisLevel.SEVERE))

    def test_crisis_detector_fails_safe(self):
        level = self.detector.evaluate(vix=float("nan"))
        self.assertNotEqual(level, CrisisLevel.NONE)


if __name__ == "__main__":
    unittest.main(verbosity=2)

