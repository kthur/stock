# Empirical Challenge & Stress Test Handoff Report

**Target Engine**: `trading_system/src/risk/intraday_stop_loss.py` (`IntradayStopLossEngine`)  
**Evaluator**: `challenger_m1_1` (Critic / Specialist)  
**Date**: 2026-07-31  

---

## 1. Observation

Direct observations from source code inspection (`trading_system/src/risk/intraday_stop_loss.py`) and empirical test executions (`.agents/challenger_m1_1/run_stress_tests.py`):

1. **Dict vs DataFrame Interface Discrepancy (Volume SMA Fallback)**:
   - Line 120 (DataFrame path):
     ```python
     vol_sma = float(np.mean(vol_window)) if len(vol_window) > 0 and np.mean(vol_window) > 0 else current_volume
     ```
   - Line 132 (Dict path):
     ```python
     vol_sma = float(intraday_data.get('volume_ma_20', current_volume))
     ```
   - Line 148:
     ```python
     panic_volume_ratio = current_volume / max(vol_sma, 1e-6)
     ```
   - **Empirical Execution Result**:
     - Dict input (`volume_ma_20 = 0.0`, `volume = 10.0`): `panic_volume_ratio = 10.0 / 1e-6 = 10,000,000.0`. Triggers `PANIC_VOLUME_SPIKE` on a tiny 10-share trade (Explosive False Alarm).
     - DataFrame input (19 zero-volume ticks followed by 1 tick with `volume = 10.0`): `np.mean(vol_window) == 0.0`, triggering fallback `vol_sma = current_volume` (10.0). `panic_volume_ratio = 10.0 / 10.0 = 1.0`. Fails to trigger `PANIC_VOLUME_SPIKE` (Suppression / False Negative).
     - Verbatim error from `run_stress_tests.py`:
       `AssertionError: 10000000.0 != 1.0 within 5.0 delta (9999999.0 difference) : PARITY BUG: Dict ratio (10000000.00) completely diverges from DataFrame ratio (1.00)!`

2. **Silent Failure on Corrupted/NaN Prices**:
   - Line 139:
     ```python
     if current_price <= 0.0:
         return StopLossResult(False, symbol, 0.0, 1.0, "INVALID_PRICE", "NO_ACTION")
     ```
   - **Empirical Execution Result**:
     - DataFrame input with `close = [100.0, np.nan]`: `current_price` is `np.nan`.
     - In Python, `float('nan') <= 0.0` evaluates to `False`. The `INVALID_PRICE` check is bypassed.
     - `drop_pct` evaluates to `np.nan`. All boolean triggers (`is_peak_drop`, `is_panic_volume`, `is_atr_breach`) evaluate to `False` (`np.nan <= threshold` is `False`).
     - Engine returns `StopLossResult(triggered=False, symbol='NAN_TICK', drop_pct=nan, panic_volume_ratio=1.0, reason='NONE', recommended_action='NO_ACTION')`.
     - Verbatim error from `run_stress_tests.py`:
       `AssertionError: 'NONE' != 'INVALID_PRICE' : BUG REPRODUCED: NaN price was not caught by current_price <= 0.0 check! Returned reason='NONE' and drop_pct=nan`

3. **Persistent State Contamination from Transient Spikes**:
   - Lines 68-71 (`update_intraday_candle`):
     ```python
     current_peak = self._symbol_peaks.get(symbol, price)
     cand_peak = max(price, high if high is not None else price)
     if cand_peak > current_peak:
         self._symbol_peaks[symbol] = cand_peak
     ```
   - **Empirical Execution Result**:
     - When a single flash spike or bad tick occurs (e.g. price 10,000 for 1 tick), `_symbol_peaks[symbol]` is set to 10,000.
     - On subsequent normal ticks (price 100.0), `tracked_peak` remains 10,000.
     - `drop_pct` is computed as `(100.0 - 10000.0) / 10000.0 = -0.9905` (-99.05%).
     - Verbatim error from `run_stress_tests.py`:
       `AssertionError: True is not false : BUG REPRODUCED: Peak contamination from prior tick spike caused drop_pct=-0.9905 and triggered stop loss!`

4. **Rolling Window Off-by-One Slicing**:
   - Line 119:
     ```python
     vol_window = volumes[-min(len(volumes), self.window_size):-1]
     ```
   - **Empirical Execution Result**:
     - For a 20-element `volumes` array, `volumes[-20:-1]` slices 19 elements (indices 0..18), omitting index 19. The rolling average excludes the 20th period.

5. **Existing Unit Test Output**:
   - Running `.venv\Scripts\python.exe -m pytest trading_system/tests/test_intraday_stop_loss.py -v`:
     `8 passed in 1.04s`

---

## 2. Logic Chain

1. **Dict vs DataFrame Parity Logic**:
   - Observation 1 shows that DataFrame volume SMA falls back to `current_volume` when previous volume mean is 0.0, while Dict volume SMA defaults to `volume_ma_20` (which can be 0.0).
   - In DataFrame mode, `current_volume / current_volume` evaluates to 1.0, suppressing panic volume spikes after flat zero-volume periods.
   - In Dict mode, `current_volume / 1e-6` evaluates to millions, falsely triggering panic volume spikes on normal small trades.
   - Therefore, the engine exhibits non-deterministic risk decisions depending purely on the data input format.

2. **NaN Guard Bypass Logic**:
   - Observation 2 shows line 139 uses `current_price <= 0.0` as the sole numerical validator.
   - In standard IEEE 754 float comparison semantics in Python, `nan <= 0.0` evaluates to `False`, `nan > 0.0` evaluates to `False`, and `nan <= threshold` evaluates to `False`.
   - As a result, NaN price inputs pass the guard check and cause all downstream rule conditions to evaluate to `False`, returning `triggered=False` (`NO_ACTION`).
   - Therefore, data feed outages or NaN values silently disable the intraday stop-loss system without warning.

3. **Peak Contamination Logic**:
   - Observation 3 shows `_symbol_peaks` is an unbounded instance-level dictionary updated via `max(current_peak, cand_peak)`.
   - Without rolling peak decay or outlier filtering, any transient bad tick permanently elevates `_symbol_peaks[symbol]`.
   - All subsequent normal prices are compared against the corrupted peak, producing `drop_pct <= -0.04` indefinitely.
   - Therefore, a single bad data tick locks the engine into ordering `FULL_LIQUIDATION` on every subsequent valid tick.

4. **Window Slicing Logic**:
   - Observation 4 shows array slicing `arr[-N:-1]`. In Python list/numpy slicing, the stop index `-1` is exclusive.
   - Thus, slicing `[-20:-1]` returns 19 elements, missing 1 period of requested history.

---

## 3. Caveats

- **Scope Limit**: Tested `IntradayStopLossEngine` in isolation and via `RiskManager.evaluate_intraday_stop_loss`. Order book L2 depth streams were not tested as the engine currently accepts OHLCV data structures.
- **External Resets**: If the caller explicitly invokes `engine.reset_symbol(symbol)` at every session boundary or bad-tick filter, peak contamination between sessions is mitigated. However, streaming pipelines calling `evaluate()` directly remain vulnerable to transient intraday spikes.

---

## 4. Conclusion

**Overall Risk Assessment**: **HIGH / CRITICAL**

The `IntradayStopLossEngine` successfully passes baseline unit tests under normal market conditions. However, empirical stress testing revealed 3 critical flaws and 2 medium edge-case bugs:

1. **CRITICAL**: Interface mismatch between DataFrame and Dict format causes zero-volume baseline behavior to split into explosive false positives (10,000,000x ratio) or complete suppression (1.0x ratio).
2. **CRITICAL**: `np.nan` prices bypass line 139 check (`nan <= 0.0` is `False`) and cause the engine to silently return `triggered=False`, masking feed failures.
3. **HIGH**: Unbounded state in `_symbol_peaks` allows transient flash spikes to corrupt the peak permanently, forcing continuous false liquidation triggers.
4. **MEDIUM**: Rolling volume window slice `[-20:-1]` takes 19 periods instead of 20.
5. **MEDIUM**: `crisis_multiplier` values <= 0.0 negate or invert drop thresholds.

---

## 5. Verification Method

To independently verify these findings:

1. **Run existing unit tests**:
   ```bash
   .venv\Scripts\python.exe -m pytest trading_system/tests/test_intraday_stop_loss.py -v
   ```
   *(Expected output: 8 passed)*

2. **Run empirical stress test suite**:
   ```bash
   .venv\Scripts\python.exe .agents/challenger_m1_1/run_stress_tests.py
   ```
   *(Expected output: 3 failures demonstrating Dict vs DF parity bug, NaN silent pass bug, and Transient spike peak contamination bug)*

3. **Inspect files**:
   - `trading_system/src/risk/intraday_stop_loss.py`: Lines 68-71, 118-122, 139, 148, 152.
   - `.agents/challenger_m1_1/run_stress_tests.py`: Stress test implementations.
   - `.agents/challenger_m1_1/stress_test_generators.py`: Dynamic synthetic price/volume series generators.
