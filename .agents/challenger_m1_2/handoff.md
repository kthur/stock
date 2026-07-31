# Handoff Report — Empirical Edge-Case Stress Testing of RiskManager & Intraday Stop-Loss Engine

**Agent**: `challenger_m1_2` (EMPIRICAL CHALLENGER)  
**Date**: 2026-07-31  
**Working Directory**: `d:\Finance\code\stock\.agents\challenger_m1_2`  
**Target Files**:
- `trading_system/src/risk/risk_manager.py` (specifically `RiskManager.check_intraday_risk` and `evaluate_intraday_stop_loss`)
- `trading_system/src/risk/intraday_stop_loss.py` (`IntradayStopLossEngine`)
- `trading_system/run_pipeline.py` (Step 10 pipeline risk integration)
- `trading_system/tests/test_intraday_stop_loss.py`

---

## Challenge Summary

**Overall risk assessment**: **HIGH**

Empirical stress testing of `IntradayStopLossEngine` and `RiskManager.check_intraday_risk` revealed **1 CRITICAL** pipeline isolation flaw, **1 HIGH** DataFrame NaN state corruption flaw, and **3 MEDIUM** edge-case failure modes in corrupted data handling and memory accumulation under high-frequency execution. Baseline unit tests passed (8/8 in 0.59s), but adversarial edge-case inputs exposed silent protection failure and pipeline bypass.

---

## 1. Observation

### Observation 1: Baseline Test Suite Execution
Running command:
```bash
.venv\Scripts\python.exe -m pytest trading_system/tests/test_intraday_stop_loss.py -v
```
Result:
```
============================== 8 passed in 0.59s ==============================
```
All 8 existing baseline tests in `test_intraday_stop_loss.py` passed.

### Observation 2: Unhandled Exception in Batch Risk Checking Crashes Pipeline (`check_intraday_risk`)
In `trading_system/src/risk/risk_manager.py` (lines 434–439):
```python
425:     def check_intraday_risk(
426:         self,
427:         portfolio_intraday_data: Dict[str, Union[pd.DataFrame, dict]],
428:         positions: Optional[Dict[str, float]] = None,
429:     ) -> Dict[str, StopLossResult]:
434:         results = {}
435:         for symbol, data in portfolio_intraday_data.items():
436:             entry_price = positions.get(symbol) if positions else None
437:             res = self.evaluate_intraday_stop_loss(symbol, data, entry_price=entry_price)
438:             results[symbol] = res
439:         return results
```
In `trading_system/run_pipeline.py` (lines 2465–2473):
```python
2465:         if 'infer_data_dict' in locals() and infer_data_dict:
2466:             intraday_results = risk_mgr.check_intraday_risk(infer_data_dict)
2467:             triggered_symbols = [sym for sym, res in intraday_results.items() if res.triggered]
2468:             if triggered_symbols:
2469:                 logger.warning(f"[INTRADAY RISK] Intraday stop-loss triggered for {len(triggered_symbols)} symbols: {triggered_symbols}")
2470:                 ensemble_df.loc[ensemble_df['symbol'].isin(triggered_symbols), 'ensemble_expected_return'] = -0.99
2471:                 ensemble_df.loc[ensemble_df['symbol'].isin(triggered_symbols), 'ensemble_score'] = 0.0
2472:     except Exception as _rm_e:
2473:         logger.warning(f"RiskManager evaluation skipped: {_rm_e}")
```
Empirical Test Output from `.agents/challenger_m1_2/stress_test_intraday.py`:
```
[FAIL [CRITICAL]] RiskManager check_intraday_risk exception isolation: One malformed symbol in portfolio_data crashed the entire check_intraday_risk batch! Exception: Unsupported intraday_data type: <class 'NoneType'>
```

### Observation 3: NaN Price in Dict or DataFrame Silently Bypasses Stop-Loss and Permanently Poisons State
In `trading_system/src/risk/intraday_stop_loss.py` (lines 139–147):
```python
139:         if current_price <= 0.0:
140:             return StopLossResult(False, symbol, 0.0, 1.0, "INVALID_PRICE", "NO_ACTION")
141: 
142:         # 2. Update Internal State
143:         self.update_intraday_candle(symbol, current_price, current_volume, high=peak_price)
144:         tracked_peak = max(self._symbol_peaks.get(symbol, current_price), peak_price)
145: 
146:         # 3. Calculate Core Metrics
147:         drop_pct = (current_price - tracked_peak) / max(tracked_peak, 1e-6)
```
Empirical Test Output from `stress_test_intraday.py`:
```
[FAIL [MEDIUM]] NaN dict current_price: Returned NaN in result: drop_pct=nan, panic_ratio=1.0, triggered=False
[FAIL [HIGH]] NaN in DataFrame last row close: Unfiltered NaN in result: drop_pct=nan, panic_ratio=1.0, reason=NONE, triggered=False
```
When `current_price` is `float('nan')`:
`float('nan') <= 0.0` is `False`. Line 139 fails to catch NaN. `update_intraday_candle` sets `_symbol_peaks[symbol] = nan`.
Subsequent calls for that symbol compute `drop_pct = nan`, and `nan <= -0.04` returns `False`. Stop loss is permanently disabled for that symbol.

### Observation 4: Infinite Price Input (`float('inf')`) Math Corruption
In `trading_system/src/risk/intraday_stop_loss.py`:
Empirical Test Output:
```
[FAIL [MEDIUM]] Inf dict current_price: Returned Inf/NaN: drop_pct=nan
```
Passing `current_price: float('inf')` results in `drop_pct=nan` without triggering an invalid price error.

### Observation 5: Memory Growth Under High Ticker Volume
In `trading_system/src/risk/intraday_stop_loss.py` (lines 47–49):
```python
self._symbol_peaks: Dict[str, float] = {}
self._price_history: Dict[str, deque] = {}
self._volume_history: Dict[str, deque] = {}
```
Empirical Test Output:
```
State Dict sizes: peaks=20000, prices=20000, vols=20000
[FAIL [MEDIUM]] Symbol dictionary accumulation (Memory Leak check): Engine accumulated 20000 symbol states with no eviction/cleanup mechanism!
```

---

## 2. Logic Chain

1. **Premise**: Real-time intraday risk management must be resilient against corrupted data (NaN/Inf, missing keys, null objects) and must guarantee that a single bad data point does not disable risk management for the rest of the portfolio.
2. **Step A (Observation 2)**: `RiskManager.check_intraday_risk` processes `portfolio_intraday_data` in a bare loop. If ticker item `N` has `None` data or throws an exception, `evaluate_intraday_stop_loss` raises `ValueError`.
3. **Step B (Observation 2)**: Because `check_intraday_risk` lacks per-symbol `try...except` isolation, the exception aborts the loop immediately. In `run_pipeline.py`, line 2472 catches this exception and logs `RiskManager evaluation skipped`, abandoning intraday stop-loss enforcement for ALL 3,379 symbols in the pipeline.
4. **Step C (Observation 3 & 4)**: In Python, `float('nan') <= 0.0` is `False`. Thus, `NaN` and `Inf` prices (in dict mode or DataFrame last row close) bypass line 139. When `_symbol_peaks[symbol]` is set to `NaN`, numpy/Python math forces all subsequent peak calculations to `NaN`. As `nan <= threshold` evaluates to `False`, the engine silently reports `triggered=False` for all future price drops of that symbol.
5. **Step D (Observation 5)**: `_symbol_peaks` grows indefinitely with every new ticker symbol evaluated, accumulating state memory across execution runs if not explicitly cleared or bounded by an LRU eviction size limit.

---

## 3. Adversarial Challenges & Mitigations

### [CRITICAL] Challenge 1: Pipeline Intraday Risk Bypass via Single Malformed Symbol Exception
- **Assumption challenged**: Assumed all ticker data inside `portfolio_intraday_data` / `infer_data_dict` is well-formed.
- **Attack scenario**: A single stock in the 3,379 universe returns `None` or an empty/malformed structure from data fetchers.
- **Blast radius**: `check_intraday_risk` crashes, outer `run_pipeline.py` exception block catches it and skips risk evaluation for ALL 3,379 symbols in the trading system.
- **Mitigation**: Wrap individual ticker evaluations inside `check_intraday_risk` in a `try...except Exception:` block, logging the error for the bad symbol and returning a safe fallback `StopLossResult` (`triggered=False, reason="DATA_ERROR"`), allowing remaining symbols to be evaluated safely.

### [HIGH] Challenge 2: DataFrame Last Row Close NaN State Corruption
- **Assumption challenged**: Assumed DataFrame price columns are sanitized prior to calling `evaluate()`.
- **Attack scenario**: Data provider returns a DataFrame where the most recent candle `close` or `high` is NaN.
- **Blast radius**: `prices[-1]` yields NaN. `_symbol_peaks[symbol]` becomes NaN. All subsequent stop-loss checks for that symbol permanently return `triggered=False`.
- **Mitigation**: Filter NaN values or validate `current_price`:
  ```python
  if math.isnan(current_price) or math.isinf(current_price) or current_price <= 0.0:
      return StopLossResult(False, symbol, 0.0, 1.0, "INVALID_PRICE", "NO_ACTION")
  ```

### [MEDIUM] Challenge 3: Dict NaN / Inf Current Price State Poisoning
- **Assumption challenged**: Assumed `current_price <= 0.0` catches all invalid prices.
- **Attack scenario**: Market feed supplies NaN or Infinity close prices in dict mode.
- **Blast radius**: `_symbol_peaks[symbol]` becomes NaN. All subsequent stop-loss checks for that symbol permanently return `triggered=False`.
- **Mitigation**: Add explicit `math.isnan(current_price) or math.isinf(current_price)` checks at line 139 of `intraday_stop_loss.py`.

### [MEDIUM] Challenge 4: Unbounded Symbol State Memory Accumulation
- **Assumption challenged**: Assumed symbol tracking dictionary size remains small.
- **Attack scenario**: Scanning 20,000+ symbols over long daemon runtimes without calling `reset_symbol`.
- **Blast radius**: Memory usage scales linearly with total historical tickers processed.
- **Mitigation**: Implement max capacity limit (e.g. 5,000 max symbols) or periodic LRU eviction on `_symbol_peaks`, `_price_history`, and `_volume_history`.

---

## 4. Stress Test Results

| Test Scenario | Input / Action | Expected Behavior | Actual Behavior | Result |
|---|---|---|---|---|
| Baseline Pytest | Run `test_intraday_stop_loss.py` | 8/8 tests pass | 8/8 tests passed in 0.59s | **PASS** |
| High Frequency (50k calls) | 50,000 evaluations | >10,000 ops/sec | 178,551 ops/sec (0.280s) | **PASS** |
| Thread Safety | 10 concurrent threads x 1,000 iterations | No thread crash | Completed without race condition error | **PASS** |
| Zero Volume Division | `volume=0, volume_ma_20=0` | `panic_volume_ratio` bounded | 0.0 (safely bounded) | **PASS** |
| Whipsaw Peak Tracking | 100 -> 90 -> 110 -> 105 | Track peak 110 & trigger at 105 | Peak tracked as 110.0, drop -4.55% triggered | **PASS** |
| Positions Entry Price Peak | `entry_price=160.0, price=140.0` | Drop calculated from 160.0 | `drop_pct=-12.50%` triggered | **PASS** |
| **Malformed Symbol in Batch** | Portfolio contains `None` symbol | Isolate exception, finish batch | **Crashed whole batch; `check_intraday_risk` raised exception** | **FAIL [CRITICAL]** |
| **DataFrame Last Row Close NaN** | DataFrame last row close is `NaN` | Return `INVALID_PRICE` | **Returned `drop_pct=nan, triggered=False`, poisoned peak state to NaN** | **FAIL [HIGH]** |
| **NaN Dict Current Price** | `current_price: float('nan')` | Return `INVALID_PRICE` | **Returned `drop_pct=nan, triggered=False`, poisoned peak state to NaN** | **FAIL [MEDIUM]** |
| **Inf Dict Current Price** | `current_price: float('inf')` | Return `INVALID_PRICE` | **Returned `drop_pct=nan, triggered=False`** | **FAIL [MEDIUM]** |
| **Symbol Accumulation** | 20,000 distinct symbol calls | Evict/limit state memory | **Accumulated 20,000 symbol dict entries without eviction** | **FAIL [MEDIUM]** |

---

## 5. Caveats

- Thread-safety stress testing passed under Python GIL, but mutating `self._symbol_peaks` across multiple threads without an explicit `threading.Lock` could still present race conditions in non-GIL CPython builds or heavy concurrent writes.
- Network socket packet drops were simulated via data payload corruption, not raw TCP socket injection.

---

## 6. Conclusion

`RiskManager.check_intraday_risk` and `IntradayStopLossEngine` perform efficiently under high frequency (178k ops/sec) and correctly implement core stop-loss logic (peak tracking, panic volume surge, ATR dynamic trailing). However, **CRITICAL vulnerability in single-symbol exception isolation** in `check_intraday_risk` must be patched by the implementer, along with `math.isnan()` / `math.isinf()` guards on input prices, to prevent complete pipeline protection bypass when corrupted data occurs.

---

## 7. Verification Method

To independently verify these findings:

1. **Run baseline unit test suite**:
   ```bash
   .venv\Scripts\python.exe -m pytest trading_system/tests/test_intraday_stop_loss.py -v
   ```
2. **Run empirical adversarial stress harness**:
   ```bash
   .venv\Scripts\python.exe .agents/challenger_m1_2/stress_test_intraday.py
   ```
3. **Invalidation condition**:
   The findings in this report are invalidated if `stress_test_intraday.py` reports `Failures/Bugs: 0` after implementation fixes are applied by the worker/implementer.
