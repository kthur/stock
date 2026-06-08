# Empirical Challenge Analysis - Stock Screener and Dash UI Tab

## 1. Executive Summary

This report documents the empirical verification and stress testing of the **Stock Screener** and **Dash UI tab** in the Trading System. We verified the codebase under simulated offline conditions (network/yfinance failures), tested callback robustness against invalid inputs, and validated server startup and API exposure.

During testing, we discovered **two fatal implementation bugs** in the offline fallback path of the Stock Screener that cause complete crashes, and **one logic bug** in the Dash UI table limits slicing. When the two screener bugs are bypassed using targeted unit-test mocks, the offline fallback behaves correctly, generating realistic mock data and returning exactly 10 US and 10 KR stocks with correct keys.

---

## 2. Bug Findings and Explanations

### Bug 1: LinAlgError in Simulated Macro Data (Cholesky Crash)
* **Location**: `src/analysis/macro_analyzer.py` (line 140)
* **Code snippet**:
  ```python
  cov_matrix = corr_matrix + np.eye(n_symbols) * 1e-6
  L = np.linalg.cholesky(cov_matrix)
  ```
* **Failure Mechanism**: 
  The function `generate_simulated_macro_data()` defines a hardcoded correlation matrix `corr_matrix` with manually configured values. This matrix is mathematically **not positive definite** (its smallest eigenvalue is approximately `-0.308`). Adding `1e-6` is insufficient to make all eigenvalues positive. As a result, `np.linalg.cholesky(cov_matrix)` fails and raises:
  `np.linalg.LinAlgError: Matrix is not positive definite`
* **Impact**: The offline fallback crashes immediately whenever yfinance is unavailable.

### Bug 2: Shape Mismatch (ValueError) in Stock Data Simulator (Broadcasting Crash)
* **Location**: `src/analysis/screener.py` (line 212)
* **Code snippet**:
  ```python
  dates = macro_df.index
  bench_ret = macro_returns["^GSPC"]
  fx_ret = macro_returns["USDKRW=X"]
  np.random.seed(42)
  for ticker in US_TICKERS:
      ...
      noise = np.random.normal(0, 0.015, size=len(dates))
      ret = beta_bench * bench_ret + beta_fx * fx_ret + noise
  ```
* **Failure Mechanism**: 
  Even if Bug 1 is bypassed, simulated stock price generation crashes. `dates` corresponds to `macro_df.index` (length 250). However, `macro_returns` drops the first row of differences (`pct_change().dropna(how='all')`), giving `bench_ret` and `fx_ret` a length of 249. When the code attempts to compute `beta_bench * bench_ret + beta_fx * fx_ret + noise`, it mixes Series of length 249 with a numpy array (`noise`) of length 250. This triggers:
  `ValueError: operands could not be broadcast together with shapes (249,) (250,)`
* **Impact**: Total crash of the mock stock generator.

### Bug 3: Negative Limit Slicing Bug in Table Callback
* **Location**: `src/web/dashboard.py` (line 291)
* **Code snippet**:
  ```python
  region_results = results.get(country, [])
  return region_results[:limit]
  ```
* **Failure Mechanism**:
  If a negative limit (e.g., `-5`) is passed to `update_outperformers_table()`, Python's slicing syntax evaluates it as `region_results[:-5]`. This drops the last 5 elements of the list and returns the first 5, rather than returning an empty list or raising an error. This is a subtle logic bug.

---

## 3. Detailed Verification Results

### Stock Screener Offline Fallback Behavior (Bypassing Bugs)
After mocking the Cholesky matrix to be valid and adjusting the size of the random noise array to `len(dates) - 1` (249), we verified:
* **Output count**: Returns exactly 10 US and 10 KR stocks (sliced from lists of size 12).
* **Returned keys**: All dictionary items contain `"ticker"`, `"expected_excess_return"`, and `"correlation_to_exchange_rate"` with the correct types (`str`, `float`, `float`).
* **Return distribution**: The exchange rate correlation values vary across tickers, verifying that price simulations are unique.
* **Design Characteristic**: The `"expected_excess_return"` values are identical for all stocks within a region. This is a consequence of the `MacroPredictor` using only global macro features (lagged macro returns) without individual stock characteristics.

### Dash UI Callbacks Graceful Failure
* **Empty/Null inputs**: `update_macro_correlation_heatmap([], "1mo")` and `None` arguments return empty heatmap structures with appropriate descriptive titles (`"No symbols selected"` or `"No valid symbols found in returns"`).
* **Non-existent symbols**: Handled gracefully without crash, returning a `"No valid symbols found in returns"` title.
* **Invalid timeframes**: Gracefully default to `1y` (250 days) via simulated fallback.
* **Non-existent countries**: `update_outperformers_table("JP", "1mo")` returns an empty list `[]` gracefully.

### Dashboard Server Startup
* The script `run_dashboard.py` starts successfully and outputs:
  ```
  Dash is running on http://127.0.0.1:5000/
  Dashboard running in background thread on 127.0.0.1:5000
  ```
* `app.server` is correctly exposed at the module level in `src/web/dashboard.py` as `server`.
