# Adversarial Review — Fundamental Features & Predictions

## Challenge Summary

**Overall risk assessment**: MEDIUM

During the adversarial verification of the feature calculations, forward-filling alignment, and 12-feature prediction models, three distinct vulnerabilities were uncovered:
1. **Row Duplication in daily time-series**: Merging fundamentals can duplicate price rows if there are duplicate dates in the fundamental records.
2. **Blanket Dropna emptying the dataset**: HALTED or Zero-close stocks result in NaN returns, which are dropped entirely by `dropna()`, returning empty DataFrames.
3. **Partial Feature KeyError**: A weak check (`'ret_1d' in df_current.columns`) to determine if features are precalculated leads to `KeyError` crashes if only a subset of features is present.

---

## Challenges

### [High] Challenge 1: Daily resolution row duplication during fundamentals merge

- **Assumption challenged**: The database/data source contains at most one fundamental record per ticker per date.
- **Attack scenario**: If the fundamentals database has duplicate entries for a ticker on the same date (e.g., corrections or multiple report versions), the left join `pd.merge(df, df_fun, left_on='date_align', right_on='date', how='left')` in `merge_fundamentals` (lines 232) duplicates the price rows.
- **Blast radius**: The length of the daily price series increases. This breaks downstream sequence length constraints, shifts targets (`shift(-h)`) incorrectly, and distorts the rolling indicator calculations.
- **Mitigation**: Deduplicate or group the fundamentals DataFrame by date (e.g., taking the latest or maximum values) before merging:
  ```python
  df_fun = df_fun.sort_values('date').groupby('date').last().reset_index()
  ```

### [Medium] Challenge 2: Blanket dropna leads to empty datasets on constant/zero close prices

- **Assumption challenged**: Close prices will always be positive and change over time.
- **Attack scenario**: If a stock is halted or has a close price of 0.0, the return columns `pct_change()` generate NaN for the entire Series. At the end of `_create_features` (line 293), `df.dropna(inplace=True)` drops all rows, returning an empty DataFrame.
- **Blast radius**: Prevents training and predictions on halted or constant-price stocks. In `predict_current`, this is gracefully handled (returns 0.0 predictions), but in training pipelines, it leads to silent exclusion of data.
- **Mitigation**: Fill returns NaNs with 0.0 for halted/constant periods before applying `dropna()`.

### [Medium] Challenge 3: Incomplete validation of precomputed features in `predict_current`

- **Assumption challenged**: The presence of `ret_1d` in the columns of `df_current` implies all 12 model features are computed and ready.
- **Attack scenario**: If the caller passes a DataFrame containing `ret_1d` but missing other features (like `vol_20d` or `operating_margin`), `predict_current` skips feature generation (line 360) and proceeds directly to `X = latest[features]` (line 372).
- **Blast radius**: The application crashes with a `KeyError` indicating missing features in the index.
- **Mitigation**: Check if *all* 12 required features are in `df_current.columns` instead of just `'ret_1d'`.
  ```python
  required_features = ['ret_1d', 'ret_5d', 'ret_20d', 'ret_60d', 'dist_sma_20', 'vol_20d', 'norm_market_cap', 'norm_floating_value', 'norm_volume', 'operating_margin', 'revenue_to_market_cap', 'dividend_yield']
  if not all(col in df_current.columns for col in required_features):
      # regenerate or fill missing features
  ```

---

## Stress Test Results

- **Zero close price returns** → Expected: DataFrame contains valid indicators (returns filled with 0.0) → Actual: Returns empty DataFrame due to `dropna` → **FAIL**
- **Duplicate fundamental dates** → Expected: Price DataFrame size remains unchanged after merge → Actual: Duplicates the matching row, expanding length → **FAIL**
- **Partial features in prediction** → Expected: Feature generation executes or fills missing features → Actual: Skips feature generation and crashes with `KeyError` → **FAIL**
- **Extreme out-of-bound fundamental metrics** → Expected: Calculations complete without overflow or crash → Actual: safe_divide prevents division by zero and extreme values are computed successfully → **PASS**
- **Short input length (< 65 rows)** → Expected: Safe fallback and returns 0.0 predictions → Actual: Returns 0.0 predictions safely → **PASS**
- **Extra columns in inputs** → Expected: Predicts correctly using the 12 features → Actual: Predicts successfully → **PASS**

---

## Unchallenged Areas

- **Database performance/deadlocks**: Out of scope for mathematical/feature correctness.
- **Model hyperparameter tuning**: Validated prediction pipeline stability, not the prediction accuracy itself.
