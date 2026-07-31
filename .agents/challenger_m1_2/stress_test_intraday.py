"""
Empirical Adversarial Stress Harness for RiskManager & IntradayStopLossEngine
Location: .agents/challenger_m1_2/stress_test_intraday.py
"""

import sys
import os
import time
import math
import traceback
import threading
from concurrent.futures import ThreadPoolExecutor
import numpy as np
import pandas as pd

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from trading_system.src.risk.intraday_stop_loss import IntradayStopLossEngine, StopLossResult
from trading_system.src.risk.risk_manager import RiskManager, CrisisLevel, CrisisDetector


class EmpiricalStressTester:
    def __init__(self):
        self.results = []
        self.bugs_found = []

    def log_result(self, test_name: str, passed: bool, details: str, bug_severity: str = "NONE"):
        status = "PASS" if passed else f"FAIL [{bug_severity}]"
        print(f"[{status}] {test_name}: {details}")
        self.results.append({
            "test_name": test_name,
            "passed": passed,
            "severity": bug_severity,
            "details": details
        })
        if not passed:
            self.bugs_found.append({
                "test_name": test_name,
                "severity": bug_severity,
                "details": details
            })

    def run_all_tests(self):
        print("=" * 70)
        print("STARTING EMPIRICAL ADVERSARIAL STRESS TEST HARNESS")
        print("=" * 70)

        # 1. Corrupted Data Tests
        self.test_nan_prices_in_dict()
        self.test_nan_prices_in_dataframe()
        self.test_inf_values_in_dict_and_df()
        self.test_zero_volumes()
        self.test_infinite_returns_division_by_zero()
        self.test_empty_dataframe_variations()
        self.test_missing_dataframe_columns()
        self.test_invalid_types_and_nones()

        # 2. Concurrency & High Frequency Stress Tests
        self.test_high_frequency_evaluations()
        self.test_symbol_accumulation_memory_leak()
        self.test_thread_safety_concurrency()
        self.test_peak_tracking_whipsaw()

        # 3. Pipeline & RiskManager Integration Edge Cases
        self.test_riskmanager_check_intraday_risk_exception_isolation()
        self.test_positions_dict_edge_cases()

        print("\n" + "=" * 70)
        print(f"SUMMARY: Total Tests: {len(self.results)} | Passed: {len(self.results) - len(self.bugs_found)} | Failures/Bugs: {len(self.bugs_found)}")
        print("=" * 70)
        for b in self.bugs_found:
            print(f"  * [{b['severity']}] {b['test_name']}: {b['details']}")
        print("=" * 70)

    # -------------------------------------------------------------
    # 1. Corrupted Data Tests
    # -------------------------------------------------------------

    def test_nan_prices_in_dict(self):
        engine = IntradayStopLossEngine()
        nan = float('nan')

        # Test NaN current price
        try:
            data = {'current_price': nan, 'peak_price': 100.0, 'volume': 1000}
            res = engine.evaluate("TEST_NAN_PRICE", data)
            # Check if drop_pct or panic_volume_ratio is NaN or if exception occurred
            if math.isnan(res.drop_pct) or math.isnan(res.panic_volume_ratio):
                self.log_result("NaN dict current_price", False, f"Returned NaN in result: drop_pct={res.drop_pct}, panic_ratio={res.panic_volume_ratio}, triggered={res.triggered}", "MEDIUM")
            else:
                self.log_result("NaN dict current_price", True, f"Handled safely: {res}")
        except Exception as e:
            self.log_result("NaN dict current_price", False, f"Raised exception: {e}\n{traceback.format_exc()}", "HIGH")

        # Test NaN peak price
        try:
            data = {'current_price': 90.0, 'peak_price': nan, 'volume': 1000}
            res = engine.evaluate("TEST_NAN_PEAK", data)
            if math.isnan(res.drop_pct):
                self.log_result("NaN dict peak_price", False, f"Returned NaN in drop_pct: drop_pct={res.drop_pct}, triggered={res.triggered}", "MEDIUM")
            else:
                self.log_result("NaN dict peak_price", True, f"Handled safely: {res}")
        except Exception as e:
            self.log_result("NaN dict peak_price", False, f"Raised exception: {e}", "HIGH")

        # Test NaN ATR
        try:
            data = {'current_price': 90.0, 'peak_price': 100.0, 'volume': 1000, 'atr': nan}
            res = engine.evaluate("TEST_NAN_ATR", data)
            if math.isnan(res.drop_pct):
                self.log_result("NaN dict ATR", False, f"Returned NaN drop_pct: {res}", "MEDIUM")
            else:
                self.log_result("NaN dict ATR", True, f"Handled safely: {res}")
        except Exception as e:
            self.log_result("NaN dict ATR", False, f"Raised exception: {e}", "HIGH")

    def test_nan_prices_in_dataframe(self):
        engine = IntradayStopLossEngine()
        
        # Test 1: NaN in middle of close/high
        df_nan1 = pd.DataFrame({
            'close': [100.0, float('nan'), 95.0],
            'high': [101.0, 102.0, float('nan')],
            'volume': [1000, 1000, 1000]
        })
        try:
            res1 = engine.evaluate("TEST_DF_NAN1", df_nan1)
            if math.isnan(res1.drop_pct) or math.isnan(res1.panic_volume_ratio):
                self.log_result("NaN in DataFrame middle rows", False, f"Unfiltered NaN in result: drop_pct={res1.drop_pct}, panic_ratio={res1.panic_volume_ratio}, triggered={res1.triggered}", "HIGH")
            else:
                self.log_result("NaN in DataFrame middle rows", True, f"Handled safely: {res1}")
        except Exception as e:
            self.log_result("NaN in DataFrame middle rows", False, f"Raised exception: {e}", "HIGH")

        # Test 2: NaN in LAST row of close
        df_nan2 = pd.DataFrame({
            'close': [100.0, 98.0, float('nan')],
            'high': [101.0, 99.0, float('nan')],
            'volume': [1000, 1000, 1000]
        })
        try:
            res2 = engine.evaluate("TEST_DF_NAN_LAST", df_nan2)
            if math.isnan(res2.drop_pct) or math.isnan(res2.panic_volume_ratio) or res2.reason != "INVALID_PRICE":
                self.log_result("NaN in DataFrame last row close", False, f"Unfiltered NaN in result: drop_pct={res2.drop_pct}, panic_ratio={res2.panic_volume_ratio}, reason={res2.reason}, triggered={res2.triggered}", "HIGH")
            else:
                self.log_result("NaN in DataFrame last row close", True, f"Handled safely: {res2}")
        except Exception as e:
            self.log_result("NaN in DataFrame last row close", False, f"Raised exception: {e}", "HIGH")


    def test_inf_values_in_dict_and_df(self):
        engine = IntradayStopLossEngine()
        inf = float('inf')

        # Inf current_price
        try:
            data = {'current_price': inf, 'peak_price': 100.0, 'volume': 1000}
            res = engine.evaluate("TEST_INF_PRICE", data)
            if math.isinf(res.drop_pct) or math.isnan(res.drop_pct):
                self.log_result("Inf dict current_price", False, f"Returned Inf/NaN: drop_pct={res.drop_pct}", "MEDIUM")
            else:
                self.log_result("Inf dict current_price", True, f"Handled: {res}")
        except Exception as e:
            self.log_result("Inf dict current_price", False, f"Raised exception: {e}", "HIGH")

        # -Inf current_price
        try:
            data = {'current_price': -inf, 'peak_price': 100.0, 'volume': 1000}
            res = engine.evaluate("TEST_NEG_INF_PRICE", data)
            self.log_result("Negative Inf dict current_price", True, f"Handled: {res}")
        except Exception as e:
            self.log_result("Negative Inf dict current_price", False, f"Raised exception: {e}", "HIGH")

    def test_zero_volumes(self):
        engine = IntradayStopLossEngine()
        # Test zero current volume and zero SMA volume
        data = {'current_price': 95.0, 'peak_price': 100.0, 'volume': 0.0, 'volume_ma_20': 0.0}
        try:
            res = engine.evaluate("TEST_ZERO_VOL", data)
            if math.isnan(res.panic_volume_ratio) or math.isinf(res.panic_volume_ratio):
                self.log_result("Zero volumes division safety", False, f"Division by zero resulted in NaN/Inf: panic_ratio={res.panic_volume_ratio}", "HIGH")
            else:
                self.log_result("Zero volumes division safety", True, f"Panic volume ratio properly bounded: {res.panic_volume_ratio}")
        except Exception as e:
            self.log_result("Zero volumes division safety", False, f"Raised exception: {e}", "HIGH")

    def test_infinite_returns_division_by_zero(self):
        engine = IntradayStopLossEngine()
        # prev_price = 0.0, current_price = 100.0
        data = {'current_price': 100.0, 'prev_price': 0.0, 'volume': 1000, 'volume_ma_20': 1000}
        try:
            res = engine.evaluate("TEST_PREV_ZERO", data)
            self.log_result("Zero prev_price return calculation", True, f"Calculated safely: {res}")
        except Exception as e:
            self.log_result("Zero prev_price return calculation", False, f"Raised exception: {e}", "HIGH")

    def test_empty_dataframe_variations(self):
        engine = IntradayStopLossEngine()
        # Empty DF without columns
        try:
            df1 = pd.DataFrame()
            res1 = engine.evaluate("TEST_EMPTY_1", df1)
            self.log_result("Empty DataFrame (no cols)", True, f"Returned default: {res1}")
        except Exception as e:
            self.log_result("Empty DataFrame (no cols)", False, f"Raised exception: {e}", "HIGH")

        # Empty DF with columns
        try:
            df2 = pd.DataFrame(columns=['close', 'high', 'volume'])
            res2 = engine.evaluate("TEST_EMPTY_2", df2)
            self.log_result("Empty DataFrame (with cols)", True, f"Returned default: {res2}")
        except Exception as e:
            self.log_result("Empty DataFrame (with cols)", False, f"Raised exception: {e}", "HIGH")

    def test_missing_dataframe_columns(self):
        engine = IntradayStopLossEngine()
        # Missing 'close' / 'Close'
        df_noclose = pd.DataFrame({'open': [10, 11], 'volume': [100, 100]})
        try:
            res = engine.evaluate("TEST_NO_CLOSE", df_noclose)
            self.log_result("Missing close column in DataFrame", False, f"Did not raise KeyError/ValueError or handle safely: {res}", "HIGH")
        except (KeyError, ValueError) as e:
            self.log_result("Missing close column in DataFrame", True, f"Safely raised expected exception: {e}")
        except Exception as e:
            self.log_result("Missing close column in DataFrame", False, f"Unexpected exception: {e}", "MEDIUM")

        # Missing 'volume' / 'Volume'
        df_novol = pd.DataFrame({'close': [100.0, 95.0], 'high': [101.0, 96.0]})
        try:
            res = engine.evaluate("TEST_NO_VOL", df_novol)
            self.log_result("Missing volume column in DataFrame", False, f"Did not raise KeyError/ValueError or handle safely: {res}", "HIGH")
        except (KeyError, ValueError) as e:
            self.log_result("Missing volume column in DataFrame", True, f"Safely raised expected exception: {e}")
        except Exception as e:
            self.log_result("Missing volume column in DataFrame", False, f"Unexpected exception: {e}", "MEDIUM")

    def test_invalid_types_and_nones(self):
        engine = IntradayStopLossEngine()
        try:
            res = engine.evaluate("TEST_NONE", None)
            self.log_result("None intraday_data", False, f"Did not raise ValueError: {res}", "MEDIUM")
        except ValueError as e:
            self.log_result("None intraday_data", True, f"Safely raised ValueError: {e}")
        except Exception as e:
            self.log_result("None intraday_data", False, f"Raised non-ValueError: {e}", "LOW")

        try:
            data = {'current_price': "100.0", 'volume': 1000} # string price
            res = engine.evaluate("TEST_STR_PRICE", data)
            self.log_result("String price in dict", True, f"Converted and evaluated: {res}")
        except Exception as e:
            self.log_result("String price in dict", False, f"Failed on string price: {e}", "LOW")

    # -------------------------------------------------------------
    # 2. Concurrency & High Frequency Stress Tests
    # -------------------------------------------------------------

    def test_high_frequency_evaluations(self):
        engine = IntradayStopLossEngine()
        N = 50000
        start = time.time()
        for i in range(N):
            p = 100.0 - (i % 10) * 0.5
            data = {'current_price': p, 'peak_price': 100.0, 'volume': 1000, 'volume_ma_20': 1000}
            engine.evaluate("005930", data)
        elapsed = time.time() - start
        ops_per_sec = N / max(elapsed, 1e-6)
        passed = ops_per_sec > 10000
        self.log_result(f"High Frequency 50k calls ({ops_per_sec:.0f} ops/sec)", passed, f"Completed 50,000 evaluations in {elapsed:.3f}s")

    def test_symbol_accumulation_memory_leak(self):
        engine = IntradayStopLossEngine()
        N_SYMBOLS = 20000
        for i in range(N_SYMBOLS):
            sym = f"SYM_{i}"
            engine.evaluate(sym, {'current_price': 100.0, 'volume': 1000})

        # Check internal state dictionaries size
        peaks_size = len(engine._symbol_peaks)
        prices_size = len(engine._price_history)
        vols_size = len(engine._volume_history)

        print(f"    State Dict sizes: peaks={peaks_size}, prices={prices_size}, vols={vols_size}")
        # Note: If system receives 20,000 tickers over time without reset_symbol, memory grows indefinitely.
        # Is there a purge mechanism or max symbol limit?
        if peaks_size == N_SYMBOLS:
            self.log_result("Symbol dictionary accumulation (Memory Leak check)", False,
                            f"Engine accumulated {peaks_size} symbol states with no eviction/cleanup mechanism!", "MEDIUM")
        else:
            self.log_result("Symbol dictionary accumulation (Memory Leak check)", True, f"Engine bounded state: {peaks_size}")

    def test_thread_safety_concurrency(self):
        engine = IntradayStopLossEngine()
        errors = []

        def worker(thread_id):
            try:
                for i in range(1000):
                    sym = f"SYM_{i % 10}"
                    p = 100.0 - (i % 5)
                    engine.evaluate(sym, {'current_price': p, 'volume': 100 * (i + 1)})
            except Exception as e:
                errors.append(f"Thread {thread_id} error: {e}")

        threads = []
        for t_idx in range(10):
            t = threading.Thread(target=worker, args=(t_idx,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        if errors:
            self.log_result("Multi-threaded concurrent evaluation", False, f"Encountered race conditions / errors: {errors}", "HIGH")
        else:
            self.log_result("Multi-threaded concurrent evaluation", True, "Successfully executed 10 threads x 1,000 iterations without crash.")

    def test_peak_tracking_whipsaw(self):
        engine = IntradayStopLossEngine()
        sym = "WHIP"
        # 1. Price at 100
        res1 = engine.evaluate(sym, {'current_price': 100.0, 'volume': 1000})
        self.assertEqual(engine._symbol_peaks[sym], 100.0)

        # 2. Drops to 90 (-10% drop, triggers stop)
        res2 = engine.evaluate(sym, {'current_price': 90.0, 'volume': 1000})
        self.assertTrue(res2.triggered)

        # 3. Price jumps to 110 (New peak)
        res3 = engine.evaluate(sym, {'current_price': 110.0, 'volume': 1000})
        self.assertFalse(res3.triggered)
        self.assertEqual(engine._symbol_peaks[sym], 110.0)

        # 4. Drops to 105 (-4.55% drop from 110 peak, should trigger!)
        res4 = engine.evaluate(sym, {'current_price': 105.0, 'volume': 1000})
        if res4.triggered:
            self.log_result("Whipsaw peak tracking", True, f"Correctly tracked new peak 110.0 and triggered stop at 105.0 (-4.55% drop)")
        else:
            self.log_result("Whipsaw peak tracking", False, f"Failed to trigger stop at 105.0 from peak 110.0 (drop_pct={res4.drop_pct:.4f})", "HIGH")

    # Helper assertion
    def assertEqual(self, a, b):
        assert a == b, f"Expected {a} == {b}"

    def assertAlmostEqual(self, a, b, places=3):
        assert round(a - b, places) == 0, f"Expected {a} ~= {b}"

    def assertTrue(self, cond):
        assert cond, f"Expected True but got {cond}"

    def assertFalse(self, cond):
        assert not cond, f"Expected False but got {cond}"

    # -------------------------------------------------------------
    # 3. Pipeline & RiskManager Integration Edge Cases
    # -------------------------------------------------------------

    def test_riskmanager_check_intraday_risk_exception_isolation(self):
        rm = RiskManager()

        # Malformed data in one symbol (e.g. None or unsupported object)
        portfolio_data = {
            'GOOD_SYM': {'current_price': 95.0, 'peak_price': 100.0, 'volume': 1000},
            'BAD_SYM': None, # Unsupported type
            'ANOTHER_GOOD': {'current_price': 99.0, 'peak_price': 100.0, 'volume': 1000}
        }

        try:
            results = rm.check_intraday_risk(portfolio_data)
            self.log_result("RiskManager check_intraday_risk exception isolation", True, f"Completed without crashing whole batch: {results.keys()}")
        except Exception as e:
            self.log_result("RiskManager check_intraday_risk exception isolation", False,
                            f"One malformed symbol in portfolio_data crashed the entire check_intraday_risk batch! Exception: {e}", "CRITICAL")

    def test_positions_dict_edge_cases(self):
        rm = RiskManager()
        portfolio_data = {
            'AAPL': {'current_price': 140.0, 'peak_price': 150.0, 'volume': 1000}, # Drop from 150 peak is -6.67%
        }
        # Position entry price is higher than intraday peak (purchased earlier at 160.0)
        positions = {
            'AAPL': 160.0
        }

        res = rm.check_intraday_risk(portfolio_data, positions=positions)
        aapl_res = res['AAPL']
        # Current price 140 vs entry price 160: drop is -12.5%!
        if aapl_res.triggered and aapl_res.drop_pct <= -0.12:
            self.log_result("Positions entry_price peak override", True, f"Correctly used higher entry_price 160.0 to calculate drop_pct: {aapl_res.drop_pct:.2%}")
        else:
            self.log_result("Positions entry_price peak override", False, f"Failed to use entry_price 160.0: drop_pct={aapl_res.drop_pct:.2%}", "HIGH")


if __name__ == '__main__':
    tester = EmpiricalStressTester()
    tester.run_all_tests()
