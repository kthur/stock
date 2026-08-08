import unittest
import numpy as np
import pandas as pd

from src.risk.intraday_stop_loss import IntradayStopLossEngine
from src.risk.risk_manager import RiskManager


class TestIntradayStopLossEngine(unittest.TestCase):

    def setUp(self):
        self.engine = IntradayStopLossEngine(
            peak_drop_threshold=-0.04,
            volume_spike_threshold=3.0,
            atr_multiplier=2.0,
        )

    def test_peak_to_trough_4pct_drop_triggers_stop_loss(self):
        """Test -4.5% drop from peak triggers PEAK_TO_TROUGH_DROP stop-loss."""
        data = {
            'current_price': 95.5,
            'peak_price': 100.0,
            'volume': 1000,
            'volume_ma_20': 1000,
        }
        res = self.engine.evaluate("005930", data)
        self.assertTrue(res.triggered)
        self.assertIn("PEAK_TO_TROUGH_DROP", res.reason)
        self.assertEqual(res.recommended_action, "FULL_LIQUIDATION")
        self.assertAlmostEqual(res.drop_pct, -0.045, places=3)

    def test_volume_spike_panic_detection_triggers_stop_loss(self):
        """Test 3.5x volume acceleration with negative price return triggers PANIC_VOLUME_SPIKE."""
        data = {
            'current_price': 98.5,
            'prev_price': 100.0,
            'peak_price': 100.0,
            'volume': 3500,
            'volume_ma_20': 1000,
        }
        res = self.engine.evaluate("005930", data)
        self.assertTrue(res.triggered)
        self.assertIn("PANIC_VOLUME_SPIKE", res.reason)
        self.assertGreaterEqual(res.panic_volume_ratio, 3.0)

    def test_normal_market_movement_no_trigger(self):
        """Test normal price movement (-1% drop, 1.2x volume) passes without trigger."""
        data = {
            'current_price': 99.0,
            'prev_price': 99.5,
            'peak_price': 100.0,
            'volume': 1200,
            'volume_ma_20': 1000,
        }
        res = self.engine.evaluate("005930", data)
        self.assertFalse(res.triggered)
        self.assertEqual(res.reason, "NONE")
        self.assertEqual(res.recommended_action, "NO_ACTION")

    def test_dynamic_atr_trailing_stop_breach(self):
        """Test dynamic ATR trailing stop breach triggers DYNAMIC_ATR_TRAILING_BREACH."""
        # Peak = 100.0, ATR = 2.0, Multiplier = 2.0 -> Stop level = 96.0
        data = {
            'current_price': 95.8,
            'peak_price': 100.0,
            'volume': 1000,
            'volume_ma_20': 1000,
            'atr': 2.0,
        }
        res = self.engine.evaluate("AAPL", data)
        self.assertTrue(res.triggered)
        self.assertIn("DYNAMIC_ATR_TRAILING_BREACH", res.reason)

    def test_dataframe_input_format(self):
        """Test evaluation using pandas DataFrame input."""
        dates = pd.date_range("2026-07-31 09:00", periods=20, freq="1min")
        df = pd.DataFrame({
            'open': np.linspace(100, 95, 20),
            'high': np.linspace(101, 95.5, 20),
            'low': np.linspace(99.5, 94.5, 20),
            'close': np.linspace(100, 95, 20),
            'volume': [1000] * 19 + [3500],
        }, index=dates)

        res = self.engine.evaluate("NVDA", df)
        self.assertTrue(res.triggered)

    def test_crisis_multiplier_tightens_thresholds(self):
        """Test crisis multiplier (e.g. 0.8x) tightens drop threshold from -4.0% to -3.2%."""
        data = {
            'current_price': 96.5,  # -3.5% drop from 100.0 peak
            'peak_price': 100.0,
            'volume': 1000,
            'volume_ma_20': 1000,
        }
        # Normal crisis_multiplier=1.0: -3.5% > -4.0% -> NOT triggered
        res_normal = self.engine.evaluate("005930", data, crisis_multiplier=1.0)
        self.assertFalse(res_normal.triggered)

        # Tightened crisis_multiplier=0.8: threshold is -3.2% -> -3.5% <= -3.2% -> TRIGGERED
        res_crisis = self.engine.evaluate("005930", data, crisis_multiplier=0.8)
        self.assertTrue(res_crisis.triggered)
        self.assertIn("PEAK_TO_TROUGH_DROP", res_crisis.reason)

    def test_risk_manager_integration(self):
        """Test RiskManager's evaluate_intraday_stop_loss and check_intraday_risk methods."""
        rm = RiskManager(portfolio_value=1_000_000)
        data = {'current_price': 95.0, 'peak_price': 100.0, 'volume': 1000, 'volume_ma_20': 1000}

        res = rm.evaluate_intraday_stop_loss("005930", data)
        self.assertTrue(res.triggered)
        self.assertGreater(len(rm.alerts), 0)

        portfolio_data = {
            '005930': {'current_price': 95.0, 'peak_price': 100.0, 'volume': 1000, 'volume_ma_20': 1000},
            '000660': {'current_price': 99.5, 'peak_price': 100.0, 'volume': 1000, 'volume_ma_20': 1000},
        }
        batch_res = rm.check_intraday_risk(portfolio_data)
        self.assertEqual(len(batch_res), 2)
        self.assertTrue(batch_res['005930'].triggered)
        self.assertFalse(batch_res['000660'].triggered)

    def test_invalid_price_handled_safely(self):
        """Test zero or negative price handles without throwing exceptions."""
        data = {'current_price': 0.0, 'peak_price': 100.0, 'volume': 1000}
        res = self.engine.evaluate("005930", data)
        self.assertFalse(res.triggered)
        self.assertEqual(res.reason, "INVALID_PRICE")

    def test_per_symbol_exception_isolation(self):
        """Bug 1: Verify malformed or exception-raising symbol data does not crash batch processing."""
        rm = RiskManager(portfolio_value=1_000_000)
        portfolio_data = {
            'GOOD_1': {'current_price': 95.0, 'peak_price': 100.0, 'volume': 1000, 'volume_ma_20': 1000},
            'BAD_SYM': None,  # Unsupported input type -> exception handled inside check_intraday_risk
            'GOOD_2': {'current_price': 99.5, 'peak_price': 100.0, 'volume': 1000, 'volume_ma_20': 1000},
        }
        res = rm.check_intraday_risk(portfolio_data)
        self.assertEqual(len(res), 3)
        self.assertTrue(res['GOOD_1'].triggered)
        self.assertFalse(res['BAD_SYM'].triggered)
        self.assertEqual(res['BAD_SYM'].reason, "EVALUATION_ERROR")
        self.assertFalse(res['GOOD_2'].triggered)

    def test_nan_inf_price_validation(self):
        """Bug 2: Verify NaN, Inf, non-numeric or <=0 prices return INVALID_PRICE without corrupting internal state."""
        # Evaluate NaN dict price
        res_nan = self.engine.evaluate("NAN_SYM", {'current_price': float('nan'), 'peak_price': 100.0, 'volume': 1000})
        self.assertFalse(res_nan.triggered)
        self.assertEqual(res_nan.reason, "INVALID_PRICE")
        self.assertNotIn("NAN_SYM", self.engine._symbol_peaks)

        # Evaluate Inf dict price
        res_inf = self.engine.evaluate("INF_SYM", {'current_price': float('inf'), 'peak_price': 100.0, 'volume': 1000})
        self.assertFalse(res_inf.triggered)
        self.assertEqual(res_inf.reason, "INVALID_PRICE")
        self.assertNotIn("INF_SYM", self.engine._symbol_peaks)

        # Evaluate DataFrame with NaN in close
        df_nan = pd.DataFrame({'close': [100.0, float('nan')], 'volume': [1000, 1000]})
        res_df_nan = self.engine.evaluate("DF_NAN_SYM", df_nan)
        self.assertFalse(res_df_nan.triggered)
        self.assertEqual(res_df_nan.reason, "INVALID_PRICE")

    def test_dict_vs_dataframe_zero_volume_parity_and_window_slice(self):
        """Bug 3: Verify 20 elements sliced in DataFrame and zero volume SMA returns panic_volume_ratio = 1.0."""
        # 20 elements input volume (current_volume=20, mean=10.5 -> panic_volume_ratio = 20/10.5 = 1.90476)
        vols = list(range(1, 21))
        df_20 = pd.DataFrame({'close': [100.0] * 20, 'volume': vols})
        res_20 = self.engine.evaluate("SLICE_20", df_20)
        self.assertAlmostEqual(res_20.panic_volume_ratio, 1.90476, places=3)

        # Zero volume SMA in Dict and DataFrame
        dict_zero_vol = {'current_price': 95.0, 'peak_price': 100.0, 'volume': 0.0, 'volume_ma_20': 0.0}
        res_dict = self.engine.evaluate("ZERO_VOL_DICT", dict_zero_vol)
        self.assertEqual(res_dict.panic_volume_ratio, 1.0)

        df_zero_vol = pd.DataFrame({'close': [95.0] * 20, 'volume': [0.0] * 20})
        res_df = self.engine.evaluate("ZERO_VOL_DF", df_zero_vol)
        self.assertEqual(res_df.panic_volume_ratio, 1.0)

    def test_flash_spike_reset_symbol_and_reset_all(self):
        """Bug 4: Verify flash spike outliers (>1.5x) do not corrupt peak, and test reset_symbol / reset_all."""
        sym = "SPIKE_STOCK"
        # Initial normal price
        self.engine.evaluate(sym, {'current_price': 100.0, 'volume': 1000})
        self.assertEqual(self.engine._symbol_peaks[sym], 100.0)

        # Flash spike to 10,000.0 (> 1.5 * 100)
        res_spike = self.engine.evaluate(sym, {'current_price': 10000.0, 'volume': 1000})
        self.assertNotEqual(self.engine._symbol_peaks[sym], 10000.0)

        # Next normal tick (100.0)
        res_normal = self.engine.evaluate(sym, {'current_price': 100.0, 'volume': 1000})
        self.assertFalse(res_normal.triggered)

        # Test reset_symbol and reset_all
        self.engine.reset_symbol(sym)
        self.assertNotIn(sym, self.engine._symbol_peaks)

        self.engine.evaluate("TEMP_1", {'current_price': 100.0, 'volume': 1000})
        self.engine.reset_all()
        self.assertEqual(len(self.engine._symbol_peaks), 0)

    def test_state_memory_safety_lru_capacity(self):
        """Bug 5: Verify LRU eviction caps memory capacity at max_symbols."""
        small_engine = IntradayStopLossEngine(max_symbols=100)
        for i in range(200):
            small_engine.evaluate(f"SYM_{i}", {'current_price': 100.0, 'volume': 1000})

        self.assertLessEqual(len(small_engine._symbol_peaks), 100)
        self.assertLessEqual(len(small_engine._price_history), 100)
        self.assertLessEqual(len(small_engine._volume_history), 100)


if __name__ == '__main__':
    unittest.main()

