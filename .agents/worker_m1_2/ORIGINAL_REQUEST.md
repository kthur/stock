## 2026-07-31T18:49:59Z
Task: Implement bug fixes and hardening for Milestone 1 (R1): Intraday Microstructure & Dynamic Stop-Loss Engine based on Challenger reports.

Bugs to remediate in `trading_system/src/risk/intraday_stop_loss.py`, `trading_system/src/risk/risk_manager.py`, and `src/risk/intraday_stop_loss.py`:

1. **Per-Symbol Exception Isolation in `RiskManager.check_intraday_risk()`**:
   - In `RiskManager.check_intraday_risk(infer_data_dict)`, wrap each symbol's evaluation inside a `try...except Exception as e:` block.
   - If one symbol in `infer_data_dict` raises an exception or has malformed data, log a warning and continue iterating through all remaining symbols in `infer_data_dict`. Never allow a single bad symbol to crash the entire batch.

2. **NaN / Inf / Zero Price Validation**:
   - In `IntradayStopLossEngine.evaluate_stop_loss()`, check if `current_price` (or `last_close`/`peak`) is NaN, Inf, non-numeric, or `<= 0.0` using `math.isnan(current_price)` or `math.isinf(current_price)` or `not math.isfinite(current_price)`.
   - If invalid, return `StopLossResult(triggered=False, symbol=symbol, drop_pct=0.0, panic_volume_ratio=1.0, reason="INVALID_PRICE", recommended_action="NO_ACTION")` WITHOUT updating `_symbol_peaks[symbol]` or corrupting state.

3. **Dict vs DataFrame Zero-Volume Ratio Parity & Window Slice Fix**:
   - Change `volumes[-20:-1]` to `volumes[-20:]` so 20 elements are sliced.
   - When volume SMA / baseline is `<= 0.0` or zero, return `panic_volume_ratio = 1.0` (for both Dict and DataFrame inputs).

4. **Flash Spike Peak Contamination & Outlier Guard**:
   - Do not update `_symbol_peaks[symbol]` if `current_price` is an obvious transient outlier (e.g. `current_price > 1.5 * last_valid_price` when historical price exists).
   - Add a `reset_symbol(symbol)` and `reset_all()` method to `IntradayStopLossEngine`.

5. **State Memory Safety**:
   - Implement max capacity / LRU cleanup if `_symbol_peaks` exceeds e.g. 10,000 tickers.

6. **Regression Tests**:
   - Add unit tests in `trading_system/tests/test_intraday_stop_loss.py` for all 5 bugs (per-symbol exception isolation, NaN price input, dict vs dataframe zero volume parity, flash spike reset, window slice).
   - Run `.venv\Scripts\python.exe -m pytest trading_system/tests/test_intraday_stop_loss.py -v`.
   - Also run stress test scripts `.agents/challenger_m1_1/run_stress_tests.py` and `.agents/challenger_m1_2/stress_test_intraday.py` if present, ensuring 100% pass rate.
   - Run full test suite `.venv\Scripts\python.exe -m pytest trading_system/tests/ -v`.

Deliverables:
1. Write detailed remediation report to `d:\Finance\code\stock\.agents\worker_m1_2\changes.md`.
2. Write self-contained handoff report to `d:\Finance\code\stock\.agents\worker_m1_2\handoff.md` with test output.
3. Notify parent via `send_message`.
