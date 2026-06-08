# Handoff Report - Challenger Macro 2

## 1. Observation

We executed the test suite `tests/test_screener_dash_challenger.py` inside the virtual environment:
* **Command**: `.venv\Scripts\python.exe -m unittest tests/test_screener_dash_challenger.py`
* **Result**:
  ```
  Ran 10 tests in 67.074s

  OK
  [PASS] update_macro_correlation_heatmap handled empty symbol list gracefully.
  [PASS] update_macro_correlation_heatmap handled invalid/None timeframe gracefully.
  [PASS] update_macro_correlation_heatmap handled non-existent symbols gracefully.
  [PASS] update_macro_correlation_heatmap handled None symbols gracefully.
  [CONFIRMED SLICING BUG] update_outperformers_table with negative limit -5 returned 5 elements.
  [PASS] update_outperformers_table handled invalid limits gracefully.
  [PASS] update_outperformers_table handled invalid/None timeframe gracefully.
  [PASS] update_outperformers_table handled invalid/None country gracefully.
  [CONFIRMED BUG 2] screen_global_outperformers failed with broadcasting shape mismatch: operands could not be broadcast together with shapes (249,) (250,) 

  [CONFIRMED BUG 1] generate_simulated_macro_data failed with: Matrix is not positive definite
  [PASS] Stock Screener Offline Fallback Test successful when bypassing both bugs!
  ```

Additionally, we observed that:
* In `src/analysis/macro_analyzer.py` line 140, the line `L = np.linalg.cholesky(cov_matrix)` triggers a `np.linalg.LinAlgError: Matrix is not positive definite` crash.
* In `src/analysis/screener.py` line 212, the expression `ret = beta_bench * bench_ret + beta_fx * fx_ret + noise` triggers a `ValueError: operands could not be broadcast together with shapes (249,) (250,)` crash.
* In `src/web/dashboard.py` line 291, returning `region_results[:limit]` with `limit = -5` yields a 5-element list rather than failing or returning an empty list.
* The dashboard server started via `run_dashboard.py` outputs:
  `2026-06-08 05:26:51,848 - src.web.dashboard - INFO - Dashboard running in background thread on 127.0.0.1:5000`
* `src/web/dashboard.py` lines 12-14 exposes the Flask server as `server = app.server` at the module level.

---

## 2. Logic Chain

1. **LinAlgError Crash (Bug 1)**: `cov_matrix` is defined as `corr_matrix + np.eye(n_symbols) * 1e-6`. Since the hardcoded correlations in `set_corr()` produce a matrix whose smallest eigenvalue is approximately `-0.308`, the resulting `cov_matrix` has negative eigenvalues and is not positive-definite. Thus, `np.linalg.cholesky(cov_matrix)` fails with `LinAlgError`.
2. **ValueError Broadcasting Mismatch (Bug 2)**: The length of `dates` (from `macro_df.index`) is 250, so `noise` is created with size 250. However, `bench_ret` and `fx_ret` are derived from `macro_returns`, which has length 249 due to `.pct_change().dropna(how='all')`. This mismatch in operand shapes (249 vs 250) raises a `ValueError`.
3. **Offline Fallback Correctness (Successful Path)**: When Bug 1 and Bug 2 are bypassed using unit-test mocks (mocking a positive-definite matrix and matching the noise array to the size of returns), the offline fallback screens and outputs exactly 10 US and 10 KR stocks with correct keys (`"ticker"`, `"expected_excess_return"`, and `"correlation_to_exchange_rate"`) and data types.
4. **Slicing Bug (Bug 3)**: When passing a negative limit `-N`, python slices the list as `results[:-N]`, which returns the list excluding the last N elements. For a 10-element list and limit `-5`, it returns the first 5 elements instead of 0 elements or throwing an error.
5. **Callback Gracefulness**: Apart from the negative slicing issue, Dash UI callbacks handle empty lists, None arguments, non-existent symbols, non-existent countries, and invalid timeframes gracefully, returning fallback structures or clear titles.
6. **Server Startup**: Running `run_dashboard.py` initializes the `StockTradingSystem` and correctly launches the background Dash dashboard thread listening on port 5000 with the Flask server exposed as `server`.

---

## 3. Caveats

* Tested under offline conditions using yfinance failure mocks. We assumed that a lack of internet/yfinance API failure is the primary offline scenario.
* We verified the output keys and length but did not check the economic accuracy or profitability of the simulated stock prices.
* No changes were made to the implementation code directly, per the "Review-only" constraint.

---

## 4. Conclusion

* **Bug 1 (Cholesky)** and **Bug 2 (Broadcasting Mismatch)** are critical implementation defects that completely break the Stock Screener's offline fallback mode.
* **Bug 3 (Negative Slicing)** is a silent logic bug in the dashboard table callbacks.
* When these bugs are bypassed via mocks, the offline fallback functions correctly, producing exactly 10 US and 10 KR stocks with correct schemas.
* The Dash callbacks handle all other invalid inputs gracefully.
* The Dash web dashboard successfully exposes `app.server` as `server` and starts on port 5000.

---

## 5. Verification Method

To independently verify these findings, run the following command in `d:\Finance\code\stock\trading_system`:
`venv/Scripts/python.exe -m unittest tests/test_screener_dash_challenger.py`

Inspect the test results:
* `test_r1_linalg_error_bug_reproduction` verifies Bug 1.
* `test_r1_broadcasting_error_bug_reproduction` verifies Bug 2.
* `test_screener_offline_fallback_fully_bypassed` verifies screener correctness when mocks bypass both bugs.
* `test_dash_callback_outperformers_invalid_limits` verifies Bug 3 (negative slicing).
* Other tests verify callback robustness under invalid arguments.
