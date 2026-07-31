# Milestone 1 (R1) Bug Remediation & Engine Hardening Report

## Summary of Remediated Bugs

### 1. Per-Symbol Exception Isolation in `RiskManager.check_intraday_risk()`
- **Target File**: `trading_system/src/risk/risk_manager.py`
- **Root Cause**: `RiskManager.check_intraday_risk()` iterated over `portfolio_intraday_data.items()` without per-symbol error boundaries. A single malformed data structure (e.g., `None` or missing mandatory key) raised an unhandled exception that halted batch processing for all remaining symbols.
- **Fix**: Wrapped each symbol evaluation inside a `try...except Exception as e:` block. If an exception is raised for a symbol, a warning is logged and a safe fallback `StopLossResult(triggered=False, symbol=symbol, drop_pct=0.0, panic_volume_ratio=1.0, reason="EVALUATION_ERROR", recommended_action="NO_ACTION")` is returned, allowing batch evaluation of all remaining portfolio symbols to continue uninterrupted.

### 2. NaN / Inf / Zero Price Validation & State Preservation
- **Target File**: `trading_system/src/risk/intraday_stop_loss.py`
- **Root Cause**: `IntradayStopLossEngine.evaluate()` performed standard `< 0.0` check on `current_price` after calling `self.update_intraday_candle()`. Because `float('nan') <= 0.0` evaluates to `False` in Python, NaN price ticks bypassed validation and modified `_symbol_peaks[symbol]` to `nan`, permanently corrupting engine state.
- **Fix**: Added static helpers `_is_invalid_price()` and `_is_invalid_volume()` using `math.isnan()`, `math.isinf()`, `not math.isfinite()`, and `f <= 0.0`. Validated prices BEFORE any state modification (`_symbol_peaks` or `_price_history`). If price is invalid, immediately returns `StopLossResult(triggered=False, symbol=symbol, drop_pct=0.0, panic_volume_ratio=1.0, reason="INVALID_PRICE", recommended_action="NO_ACTION")` WITHOUT updating internal state.

### 3. Dict vs DataFrame Zero-Volume Ratio Parity & Window Slicing Fix
- **Target File**: `trading_system/src/risk/intraday_stop_loss.py`
- **Root Cause**: 
  1. `volumes[-20:-1]` sliced 19 elements excluding index -1 (current volume).
  2. When volume SMA / baseline was `<= 0.0` or zero, Dict inputs computed `volume / 1e-6` (resulting in false 10,000,000x panic ratio alarms), while DataFrame fallback computed `current_volume / current_volume = 1.0x`.
- **Fix**: Changed window slicing to `volumes[-window_len:]` where `window_len = min(len(volumes), self.window_size)` (correctly slicing up to 20 elements). Added explicit guard: when `vol_sma <= 0.0` or `current_volume <= 0.0` or invalid, `panic_volume_ratio = 1.0` is returned for BOTH Dict and DataFrame inputs.

### 4. Flash Spike Peak Contamination & Outlier Guard
- **Target File**: `trading_system/src/risk/intraday_stop_loss.py`
- **Root Cause**: A single flash spike tick (e.g. 10,000.0 vs historical 100.0) updated `_symbol_peaks[symbol]` permanently, causing all subsequent normal price ticks (100.0) to register a false -99% drop and trigger constant stop-loss liquidations.
- **Fix**: Added transient outlier detection `if last_valid_price > 0 and current_price > 1.5 * last_valid_price`. If an obvious outlier is detected, `_symbol_peaks[symbol]` is NOT updated with the bad peak. Added `reset_symbol(symbol)` and `reset_all()` methods to support manual/programmatic state resets.

### 5. State Memory Safety & LRU Eviction
- **Target File**: `trading_system/src/risk/intraday_stop_loss.py`
- **Root Cause**: `_symbol_peaks` used a standard dictionary without eviction, accumulating state for thousands of tickers indefinitely and risking memory leaks during high-frequency streaming operations.
- **Fix**: Replaced standard dict with `collections.OrderedDict` for `_symbol_peaks`. Added LRU eviction `_touch_symbol_unlocked()` that bounds `_symbol_peaks`, `_price_history`, and `_volume_history` to `max_symbols` (default 10,000 tickers). Wrapped state operations in `threading.Lock()` for full thread safety under concurrent execution.

---

## File Modifications Summary

| Modified File | Description |
|---|---|
| `trading_system/src/risk/intraday_stop_loss.py` | Added NaN/Inf/Zero validation, LRU eviction, flash spike outlier guard, 20-element window slicing, zero-volume parity logic, thread lock, and `reset_symbol`/`reset_all`/`evaluate_stop_loss` methods. |
| `trading_system/src/risk/risk_manager.py` | Added `try...except Exception as e:` block in `check_intraday_risk()` for per-symbol exception isolation. |
| `trading_system/tests/test_intraday_stop_loss.py` | Added comprehensive unit tests covering all 5 remediated bug areas. |
