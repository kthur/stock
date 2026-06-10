# Analysis of Test Failures in `tests/test_screener_dash_challenger.py`

This report analyzes the 4 test failures in `trading_system/tests/test_screener_dash_challenger.py`. All 4 failures are caused by discrepancies between the test expectations and the corrected/updated source code implementations in `screener.py`, `macro_analyzer.py`, and `dashboard.py`.

---

## 1. Summary of Findings

- **Root Cause**: The test suite is attempting to assert historical buggy behaviors (such as Cholesky `LinAlgError`, slicing index errors, and shape mismatches) that have already been fixed in the codebase. Additionally, the test asserts that expected returns for all stocks are identical, which contradicts the modern feature engineering design of the ensemble ML predictor model (which utilizes ticker-specific lag features).
- **Ensemble Model Integrity**: The current implementation of the ensemble model in `macro_predictor.py` uses an ensemble of `XGBRegressor` and `LGBMRegressor` models trained on both global macro lags and stock-specific return lags. This implementation is correct and must be preserved.

---

## 2. Detailed Test Failure Breakdown

### Failure A: `test_r1_linalg_error_bug_reproduction`
* **Test File & Line**: `trading_system/tests/test_screener_dash_challenger.py:61`
* **Observation**: The test expects `generate_simulated_macro_data(period="1y")` to raise a `np.linalg.LinAlgError` due to a non-positive definite correlation matrix.
* **Logic/Reasoning**: In `trading_system/src/analysis/macro_analyzer.py` (lines 143-149), the simulated correlation matrix is projected onto the nearest positive semi-definite (PSD) matrix before performing Cholesky decomposition:
  ```python
  w, v = np.linalg.eigh(corr_matrix)
  w = np.maximum(w, 1e-6)
  corr_matrix_psd = v @ np.diag(w) @ v.T
  d = np.sqrt(np.diag(corr_matrix_psd))
  corr_matrix_psd = corr_matrix_psd / np.outer(d, d)
  L = np.linalg.cholesky(corr_matrix_psd)
  ```
  Since the correlation matrix is projected to PSD, Cholesky decomposition is guaranteed to succeed and does not raise `LinAlgError`. Thus, the test's `assertRaises(np.linalg.LinAlgError)` fails.

### Failure B: `test_r1_broadcasting_error_bug_reproduction`
* **Test File & Line**: `trading_system/tests/test_screener_dash_challenger.py:74`
* **Observation**: The test asserts that `screener.screen_global_outperformers()` raises a `ValueError` because of a broadcasting shape mismatch between the macro returns and the generated stock returns noise.
* **Logic/Reasoning**: In `trading_system/src/analysis/screener.py` (lines 229 and 261), the noise arrays are generated with size `len(dates)` (which is the correct size of 249) instead of hardcoding 250:
  ```python
  noise = np.random.normal(0, 0.015, size=len(dates))
  ```
  Because the lengths match, no broadcasting error occurs and `ValueError` is not raised.

### Failure C: `test_screener_offline_fallback_fully_bypassed`
* **Test File & Line**: `trading_system/tests/test_screener_dash_challenger.py:125`
* **Observation**: The test asserts that all US stocks return identical expected returns (`self.assertEqual(len(set(us_returns)), 1)`).
* **Logic/Reasoning**: In `trading_system/src/analysis/screener.py` (lines 290-292), ticker-specific features (`stock_lag_{lag}`) are appended to the training and testing matrices for each ticker:
  ```python
  for lag in range(1, 6):
      ticker_features[f"stock_lag_{lag}"] = stock_returns[ticker].shift(lag)
  ```
  Because the ML ensemble predictor relies on stock-specific features in addition to global macro features, different tickers receive different feature inputs and thus produce distinct predicted returns. This is correct behavior, but it violates the outdated test assumption.

### Failure D: `test_dash_callback_outperformers_invalid_limits`
* **Test File & Line**: `trading_system/tests/test_screener_dash_challenger.py:212`
* **Observation**: The test passes a negative limit (`limit=-5`) to `update_outperformers_table` and asserts that it returns 5 elements due to a slicing bug (`self.assertEqual(len(res_neg), 5)`).
* **Logic/Reasoning**: In `trading_system/src/web/dashboard.py` (line 284), the limit input is sanitized using `limit = max(0, limit)`. Since `-5` becomes `0`, `region_results[:0]` returns `[]` (length 0). The assertion fails because `0 != 5`.

---

## 3. Proposed Action Plan

Since the source code files (`macro_analyzer.py`, `screener.py`, and `dashboard.py`) contain the correct, robust, and updated implementations, the proposed plan is to update the tests in `tests/test_screener_dash_challenger.py` to match the correct behavior:

1. **Fix `test_r1_linalg_error_bug_reproduction`**:
   - Mock `np.linalg.cholesky` to explicitly raise a `np.linalg.LinAlgError("Matrix is not positive definite")` to simulate the bug scenario and verify that the fallback mechanisms handle the error.
   
2. **Fix `test_r1_broadcasting_error_bug_reproduction`**:
   - Mock `numpy.random.normal` to return an array of mismatched shape (e.g. size 250 when 249 is expected) during this test, verifying that if a shape mismatch were to occur, it correctly raises `ValueError`.

3. **Fix `test_screener_offline_fallback_fully_bypassed`**:
   - Change `self.assertEqual(len(set(us_returns)), 1)` to `self.assertGreater(len(set(us_returns)), 1)` to reflect the correct implementation of the ensemble model where expected returns vary across stocks due to ticker-specific features.

4. **Fix `test_dash_callback_outperformers_invalid_limits`**:
   - Change the assertion for negative limits from `self.assertEqual(len(res_neg), 5)` to `self.assertEqual(len(res_neg), 0)` (or `self.assertEqual(res_neg, [])`) to verify that the dashboard now handles negative limits safely without indexing bugs.
