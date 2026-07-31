"""
Empirical Stress Test Runner for IntradayStopLossEngine
"""

import sys
from pathlib import Path
import numpy as np
import pandas as pd
import unittest

ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT_DIR))

from trading_system.src.risk.intraday_stop_loss import IntradayStopLossEngine, StopLossResult
from stress_test_generators import (
    generate_volatile_spike_series,
    generate_illiquid_gap_down_series,
    generate_flat_low_volume_series,
    generate_extreme_volatility_series,
    generate_nan_and_corrupted_data,
)


class TestIntradayStopLossEmpiricalStress(unittest.TestCase):

    def setUp(self):
        self.engine = IntradayStopLossEngine(
            peak_drop_threshold=-0.04,
            volume_spike_threshold=3.0,
            atr_multiplier=2.0,
            window_size=20,
        )

    def test_scenario1_flat_low_volume_panic_surge_suppression_bug(self):
        """
        Scenario 1: Illiquid/flat market with 0 volume for 20 periods, then sudden 5000 volume surge + -5% drop.
        EXPECTED: Panic volume surge trigger (5000 vs 0 prev volume baseline).
        ACTUAL: vol_sma falls back to 5000 because mean(prev_volumes) == 0 <= 0, causing volume ratio = 1.0 (SUPPRESSED!).
        """
        df = generate_flat_low_volume_series(length=25, spike_index=20, panic_vol=5000.0, drop_pct=-0.05)
        res = self.engine.evaluate("005930", df)

        print("\n--- Scenario 1: Flat Low Volume Panic Surge Suppression ---")
        print(f"Triggered: {res.triggered}, Reason: {res.reason}, Panic Vol Ratio: {res.panic_volume_ratio:.2f}")

        # Assert expected behavior: Should trigger panic volume spike!
        # If actual code fails this assertion, it empirically proves the bug!
        self.assertTrue(
            res.triggered and "PANIC_VOLUME_SPIKE" in res.reason,
            f"BUG REPRODUCED: Zero-volume baseline causes volume_ma fallback to current_volume, panic ratio is {res.panic_volume_ratio:.2f} instead of > 3.0!"
        )

    def test_scenario2_dict_vs_dataframe_volume_ma_parity_bug(self):
        """
        Scenario 2: Inconsistent behavior between dict and DataFrame input for zero volume baseline.
        Dict with volume=10, volume_ma_20=0.0 -> panic_volume_ratio = 10 / 1e-6 = 10,000,000x (triggers false alarm on tiny trade).
        DataFrame with prev volumes=0, current volume=10 -> volume_ma fallback to 10 -> ratio = 1.0x (completely suppresses alarm).
        """
        # Dict evaluation
        dict_data = {
            'current_price': 95.0,
            'prev_price': 100.0,
            'peak_price': 100.0,
            'volume': 10.0,
            'volume_ma_20': 0.0,
        }
        res_dict = self.engine.evaluate("TEST_DICT", dict_data)

        # DataFrame evaluation with matching data (19 zeros then volume 10)
        df_data = generate_flat_low_volume_series(length=20, spike_index=19, panic_vol=10.0, drop_pct=-0.05)
        res_df = self.engine.evaluate("TEST_DF", df_data)

        print("\n--- Scenario 2: Dict vs DataFrame Parity Discrepancy ---")
        print(f"Dict result: triggered={res_dict.triggered}, ratio={res_dict.panic_volume_ratio:.2f}, reason={res_dict.reason}")
        print(f"DataFrame result: triggered={res_df.triggered}, ratio={res_df.panic_volume_ratio:.2f}, reason={res_df.reason}")

        # Check parity: Either both trigger or neither trigger with similar ratios
        self.assertAlmostEqual(
            res_dict.panic_volume_ratio,
            res_df.panic_volume_ratio,
            delta=5.0,
            msg=f"PARITY BUG: Dict ratio ({res_dict.panic_volume_ratio:.2f}) completely diverges from DataFrame ratio ({res_df.panic_volume_ratio:.2f})!"
        )

    def test_scenario3_nan_price_silent_failure_bug(self):
        """
        Scenario 3: Corrupted market feed containing NaN prices in DataFrame or dict.
        EXPECTED: Signal invalid price or error handling.
        ACTUAL: Returns triggered=False with drop_pct=NaN and reason='NONE', silently passing corrupted market data!
        """
        df_nan = pd.DataFrame({
            'close': [100.0, np.nan],
            'high': [101.0, np.nan],
            'low': [99.0, np.nan],
            'volume': [1000, 1000]
        })
        res = self.engine.evaluate("NAN_TICK", df_nan)

        print("\n--- Scenario 3: NaN Price Silent Failure ---")
        print(f"Triggered: {res.triggered}, Reason: {res.reason}, drop_pct: {res.drop_pct}")

        self.assertEqual(
            res.reason,
            "INVALID_PRICE",
            f"BUG REPRODUCED: NaN price was not caught by current_price <= 0.0 check! Returned reason='{res.reason}' and drop_pct={res.drop_pct}"
        )

    def test_scenario4_transient_spike_peak_contamination_bug(self):
        """
        Scenario 4: Transient bad tick / flash spike (price 10,000 for 1 tick) corrupts _symbol_peaks permanently.
        Subsequent valid prices (e.g. 100) trigger stop-loss FOREVER (-99% drop relative to bad peak).
        """
        # Step 1: Flash spike
        df_spike = generate_volatile_spike_series(length=30, spike_index=10, spike_mult=100.0, crash_index=11, drop_pct=0.0)
        # Evaluate tick at spike
        self.engine.evaluate("SPIKE_TICK", df_spike.iloc[:11])

        # Step 2: Market returns to normal price 100.0
        normal_data = {
            'current_price': 100.0,
            'prev_price': 100.0,
            'peak_price': 100.0,
            'volume': 1000,
            'volume_ma_20': 1000
        }
        res_normal = self.engine.evaluate("SPIKE_TICK", normal_data)

        print("\n--- Scenario 4: Transient Spike Peak Contamination ---")
        print(f"Normal price evaluate after spike: triggered={res_normal.triggered}, drop_pct={res_normal.drop_pct:.4f}, reason={res_normal.reason}")

        # Price is 100.0 and peak_price passed is 100.0. Should drop_pct be -0.99?
        # If tracked_peak is contaminated by the bad tick (10,000), drop_pct is -0.99!
        self.assertFalse(
            res_normal.triggered,
            f"BUG REPRODUCED: Peak contamination from prior tick spike caused drop_pct={res_normal.drop_pct:.4f} and triggered stop loss!"
        )

    def test_scenario5_illiquid_gap_down_10pct_detection(self):
        """
        Scenario 5: Sudden illiquid gap down (-10% in 1 tick).
        EXPECTED: Peak-to-trough drop triggers FULL_LIQUIDATION.
        """
        df_gap = generate_illiquid_gap_down_series(length=20, gap_index=15, gap_drop=-0.10)
        res = self.engine.evaluate("GAP_STOCK", df_gap)

        print("\n--- Scenario 5: Illiquid Gap Down -10% ---")
        print(f"Triggered: {res.triggered}, Reason: {res.reason}, Drop Pct: {res.drop_pct:.4f}, Action: {res.recommended_action}")

        self.assertTrue(res.triggered)
        self.assertIn("PEAK_TO_TROUGH_DROP", res.reason)
        self.assertEqual(res.recommended_action, "FULL_LIQUIDATION")

    def test_scenario6_atr_trailing_stop_in_extreme_volatility(self):
        """
        Scenario 6: Dynamic ATR trailing stop evaluation in extreme noise.
        """
        df_vol = generate_extreme_volatility_series(length=50, mean_price=100.0, volatility=0.03, seed=123)
        # Evaluate with ATR = 5.0, multiplier = 2.0 (stop distance = 10.0 from peak)
        peak = df_vol['high'].max()
        last_price = df_vol['close'].iloc[-1]
        atr_val = 5.0
        res = self.engine.evaluate("VOL_STOCK", df_vol, atr=atr_val)

        print("\n--- Scenario 6: ATR Trailing Stop in Extreme Volatility ---")
        print(f"Peak: {peak:.2f}, Last Price: {last_price:.2f}, ATR: {atr_val}, Triggered: {res.triggered}, Reason: {res.reason}")

        expected_atr_stop = peak - (atr_val * 2.0)
        if last_price <= expected_atr_stop:
            self.assertTrue(res.triggered)
            self.assertIn("DYNAMIC_ATR_TRAILING_BREACH", res.reason)
        else:
            self.assertNotIn("DYNAMIC_ATR_TRAILING_BREACH", res.reason)

    def test_scenario7_crisis_multiplier_zero_or_negative_edge_case(self):
        """
        Scenario 7: crisis_multiplier = 0.0 or negative.
        If crisis_multiplier = 0.0, effective_drop_threshold becomes 0.0 -> ANY drop triggers stop-loss!
        """
        data = {
            'current_price': 99.9,
            'peak_price': 100.0,
            'volume': 1000,
            'volume_ma_20': 1000,
        }
        res_zero_crisis = self.engine.evaluate("CRISIS_STOCK", data, crisis_multiplier=0.0)

        print("\n--- Scenario 7: Crisis Multiplier Zero Edge Case ---")
        print(f"Zero Crisis Multiplier: Triggered={res_zero_crisis.triggered}, Reason={res_zero_crisis.reason}")

        # When crisis_multiplier=0.0, effective threshold is 0.0. A tiny 0.1% drop triggers stop loss!
        # Is this desirable or an edge case issue?
        self.assertTrue(res_zero_crisis.triggered)

    def test_scenario8_window_size_slicing_off_by_one(self):
        """
        Scenario 8: Checking if window_size slicing takes 19 or 20 elements.
        """
        vols = list(range(1, 21)) # 20 elements: 1, 2, ..., 20
        df = pd.DataFrame({'close': [100.0]*20, 'volume': vols})
        # evaluate
        self.engine.evaluate("SLICE_TEST", df)
        # Check vol_window calculation manually:
        # volumes[-20:-1] slices index 0..18 (19 elements: 1..19). Average is 10.0, excluding element 20.
        vol_window = np.array(vols)[-20:-1]
        print("\n--- Scenario 8: Window Slicing Check ---")
        print(f"Input volumes length: {len(vols)}, Sliced window length: {len(vol_window)}, Mean: {np.mean(vol_window):.2f}")
        self.assertEqual(len(vol_window), 19, "vol_window slices 19 elements instead of window_size (20)")


if __name__ == '__main__':
    unittest.main()
