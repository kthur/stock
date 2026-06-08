# Empirical Challenge Analysis: Global Macro Correlation Engine & ML Predictor

This analysis report documents the findings and results from empirical stress testing and adversarial review of the **Global Macro Correlation Engine** and the **Macro Predictor (ML Model)**.

## 1. Global Macro Correlation Engine (`calculate_cross_correlation`)

We tested `calculate_cross_correlation` against extreme conditions, missing data, timezone mismatches, and numerical limits.

### A. Completely Missing/NaN Datasets
- **Test Case**: Input DataFrame consisting entirely of `NaN` values across all macro indices.
- **Observed Behavior**: The engine applies forward-fill and backward-fill (`ffill().bfill()`). With all-NaN data, the filled DataFrame remains NaN. `pct_change()` produces all-NaN returns. Pearson correlation computations return NaN, which are caught by the check:
  `val if not pd.isna(val) else 0.0`
- **Result**: The function successfully returns a correlation matrix containing only `0.0` values. No crash occurs.
- **Numpy Warning**: Triggers `RuntimeWarning: invalid value encountered in subtract` during pandas internal mean subtraction.

### B. Varying Lengths and Non-Overlapping Timezones
- **Test Case 1 (Varying Lengths)**: Columns containing data only in distinct, non-overlapping windows (e.g., Ticker A only in days 1–15, Ticker B only in days 16–30).
- **Observed Behavior**: The `.ffill().bfill()` operations extend the boundary values across the missing dates. During percentage return calculations, these filled regions become constant (zero returns). The Pearson correlation of constant returns returns NaN, which is replaced by `0.0`.
- **Result**: Runs without crashing, correctly fallback-assigning `0.0` correlation.
- **Test Case 2 (Non-Overlapping Timezones)**: Mixing indices with explicit timezones (e.g., `America/New_York` vs `Asia/Seoul`).
- **Observed Behavior**: The engine normalizes the timezone-aware DatetimeIndex to timezone-naive normalized dates:
  ```python
  if df.index.tz is not None:
      df.index = df.index.tz_convert(None)
  df.index = df.index.normalize()
  ```
- **Result**: Successfully aligns timezone-mismatched indices.
- **Warning**: Merging timezone-aware Series with differing timezones via `pd.concat` beforehand can trigger:
  `Pandas4Warning: Sorting by default when concatenating all DatetimeIndex is deprecated.`

### C. Out-of-Bounds/Extreme Numbers
- **Test Case**: Datasets containing `np.inf`, `-np.inf`, huge values (`1e300`), and tiny values (`1e-300`).
- **Observed Behavior**: The values flow into returns and correlation calculations. Infinities propagate to percentage returns as NaNs or Infs.
- **Result**: The output correlation matrix is successfully generated, containing only finite numbers, with all NaNs/Infs correctly forced to `0.0`.
- **Numpy Warning**: Triggers `RuntimeWarning: invalid value encountered in subtract` during computation.

---

## 2. ML Predictor (`MacroPredictor`)

We stress-tested the Scikit-Learn `RandomForestRegressor` wrapper with bad data, scaling issues, and feature mismatches.

### A. All Constant Values
- **Test Case**: All features and targets set to constant values.
- **Result**: The model fits successfully without raising errors. Metrics such as `mse` and `r2_score` are returned (with `r2_score` computed as a float/NaN depending on sklearn's behavior). No crash is experienced during training or prediction.

### B. All NaNs
- **Test Case**: Features and targets consisting entirely of `NaN`.
- **Result**: The model training correctly filters out all rows containing NaNs:
  ```python
  valid_mask = ~(X.isna().any(axis=1) | y.isna())
  X = X[valid_mask]
  y = y[valid_mask]
  ```
- Since the aligned dataset length becomes `0`, it correctly raises:
  `ValueError: Insufficient aligned non-NaN data points: 0 (need >= 5)`

### C. Very Small Dataset Sizes
- **Test Case 1 (Size < 5)**: Attempting to train on 4 samples.
- **Result**: Correctly throws `ValueError` (as `len(X) < 5`).
- **Test Case 2 (Size = 5)**: Training on exactly 5 samples.
- **Result**: Successfully trains. The model uses the fallback split logic:
  ```python
  if len(X) >= 10:
      split_idx = int(len(X) * 0.8)
      # ...
  else:
      X_train, X_test = X, X
      y_train, y_test = y, y
  ```
  This prevents train/test split size errors for small samples by reusing the dataset.

### D. Large Number of Features
- **Test Case**: 200 features with only 30 samples.
- **Result**: Training completes successfully. RandomForestRegressor naturally handles wide features.

### E. Mismatched Prediction Features
- **Test Case**: Training the model on features `['feat_1', 'feat_2']`, then predicting on `['feat_2', 'feat_3']`.
- **Observed Behavior**: The predictor's defensive alignment logic:
  ```python
  if self.feature_names:
      for col in self.feature_names:
          if col not in features.columns:
              features[col] = 0.0
      X = features[self.feature_names]
  ```
- **Result**: Successfully fills missing columns with `0.0`, discards extra columns, and predicts without throwing Scikit-Learn feature shape mismatch errors.

---

## 3. Cached Metrics JSON File (`data/macro_model_metrics.json`)

We examined the JSON caching mechanism's robustness.

### A. Write Failure Safety
- **Test Case**: Simulating an OS permission write failure when saving the JSON metrics file.
- **Observed Behavior**: The code wraps the file write operation in a try-except block:
  ```python
  try:
      with open("data/macro_model_metrics.json", "w") as f:
          json.dump(metrics, f, indent=4)
  except Exception as e:
      logger.error(f"Failed to save macro model metrics to JSON: {e}")
  ```
- **Result**: The exception is caught, logged, and the training routine returns metrics successfully without crashing the application.

### B. Vulnerabilities & Robustness Issues
1. **No Explicit Encoding**: `open()` is called without specifying `encoding="utf-8"`. On Windows platforms, this uses the default system encoding, which might lead to encoding warnings or corruption if non-ASCII characters ever enter the metrics (e.g. ticker names or feature metadata).
2. **No Read Integration**: The metrics JSON file is written to disk but is never read or loaded anywhere in the codebase (the dashboard and screener train the model in-memory and discard/overwrite the file).
3. **No File Locking**: If multiple dashboard threads or workers attempt to train the model concurrently, they will execute concurrent writes to the same JSON file path, leading to race conditions and potential file corruption (partially written files).

---

## 4. Critical Logical Vulnerability: The "Placebo" ML Predictor

Through adversarial review of `screener.py` (`screen_global_outperformers`), we identified a major design flaw:

1. **Shared Macro Features**: The features used to train the `MacroPredictor` are strictly global macro variables (lagged returns of `^GSPC`, `^IXIC`, etc.). The training data `X_pool` is created by duplicating these macro features for every stock in the universe, while the targets `y_pool` are the stock-specific excess returns.
2. **Identical Predictions**: When predicting expected excess returns for individual tickers, the model is fed the *latest macro features vector* (`latest_features`). Since this vector contains only macro data (which is identical for all stocks in the region on a given day), the model predicts the **exact same expected excess return** for every ticker (representing the predicted market-average excess return).
3. **Sorting Degradation**: Because the predicted excess returns for all tickers are mathematically identical (verified by `test_screener_predictions_identical` in our stress test), the sorting step:
   ```python
   results.sort(key=lambda x: x["expected_excess_return"], reverse=True)
   ```
   degrades to a stable sort that simply preserves the order of tickers as they were originally hardcoded in the input lists (`US_TICKERS` and `KR_TICKERS`).
4. **Impact**: The machine learning model is completely unable to distinguish or rank individual stocks based on expected returns. The "ML screening" is effectively a placebo.

---

## 5. Performance and Test Suite Execution

We successfully executed the test suite including the new stress tests:
- **Command**: `pytest tests/test_macro.py tests/test_macro_stress.py`
- **Results**: `16 passed, 6 warnings in 47.12s`
  - 5 tests from `test_macro.py` passed.
  - 11 stress/edge tests from `test_macro_stress.py` passed.
- **Warnings Observed**:
  - `DeprecationWarning`: Dash `DataTable` deprecation warnings.
  - `RuntimeWarning`: Numpy mean subtraction warning due to NaN inputs in correlation testing.
  - `Pandas4Warning`: DatetimeIndex concat warning due to different timezones in stress testing.
