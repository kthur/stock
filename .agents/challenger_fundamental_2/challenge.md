# Adversarial Verification & Stress Test Report

## Challenge Summary

**Overall risk assessment**: **HIGH**

This assessment is driven by a critical lookahead bias vulnerability uncovered in the fundamental time-series forward-filling logic, which can lead to artificial inflated performance in backtests and corrupted feature inputs during training.

---

## Challenges

### [Critical] Challenge 1: Lookahead Leakage (Lookahead Bias) in Forward-Filling

- **Assumption challenged**: The time-series forward-filling assumes that input daily prices (`df_prices`) are always pre-sorted in ascending chronological order.
- **Attack scenario**: If the input dataframe is sorted in descending order (newest date first)—which frequently occurs when fetching raw data from historical APIs or DB queries that return newest records first—`ffill()` propagates the values from top to bottom. In a descending series, moving from top to bottom is moving from **future** to **past**. For example, if a fundamental data update is merged on `2026-02-15`, `ffill()` propagates it backwards to `2026-02-14`, `2026-02-13`, ..., all the way to `2026-01-16`.
- **Blast radius**: The model trains on and predicts with future fundamental information (e.g. earnings, revenue), completely corrupting backtests and causing massive lookahead leakage.
- **Mitigation**: Explicitly sort the prices dataframe chronologically in ascending order by index or date column prior to merging and forward-filling in `merge_fundamentals`. For example:
  ```python
  df = df_prices.sort_index(ascending=True).copy()
  ```

### [Medium] Challenge 2: Crash on Missing Columns (e.g., Volume, Close)

- **Assumption challenged**: Input dataframes passed to `predict_current` or `apply_market_normalization` are assumed to contain all technical price columns.
- **Attack scenario**: If a ticker is passed that lacks the `Volume` or `Close` column (e.g. mutual funds, indices, or yfinance data-download issues), `apply_market_normalization` raises a `KeyError` on `df_copy['Volume']` or `df_copy['Close']`, crashing the execution pipeline.
- **Blast radius**: The entire daily scoring pipeline or real-time prediction batch fails.
- **Mitigation**: Add validation or defensive default handling in `apply_market_normalization` (e.g., if `'Volume'` not in columns, fall back to a default value or log a warning and skip/drop the stock).

### [Medium/Low] Challenge 3: Silent Data Loss / Predicting on Stale Days

- **Assumption challenged**: If the latest price data is invalid, the model should handle it transparently.
- **Attack scenario**: When the latest row's `Close` or other price fields are `NaN` or `Inf`, `_create_features` calls `df.dropna(inplace=True)` to remove rolling window NaNs. This silently drops the latest row.
- **Blast radius**: `predict_current` successfully returns expected returns, but they are actually computed on the *previous day's* data (the second-to-last row) instead of the latest day. This happens completely silently without raising any warnings or logs, meaning users might get stale predictions.
- **Mitigation**: If the latest row is dropped during feature calculation, log a warning or raise a validation exception so that callers are aware they are using stale data.

---

## Stress Test Results

A dedicated adversarial test suite was designed, implemented, and executed at `trading_system/tests/test_adversarial_fundamental.py`. It verifies all requested edge conditions:

### 1. Feature Calculations Under Extreme Edge Conditions
- **Scenarios tested**: Zero, NaN, Inf, and extreme out-of-bounds (1e308, -1e308, 1e-308) values for `revenue`, `operating_income`, `dividend_per_share`, and `Close`.
- **Expected behavior**: Division-by-zero protection (`safe_divide`) prevents `ZeroDivisionError` and replaces `Inf` / `NaN` with `0.0`. Technical feature dropna behaves predictably.
- **Actual behavior**: The calculations successfully handled extreme values. Scenarios with invalid `Close` (0.0, NaN, Inf) resulted in `dropna` dropping the affected rows (yielding empty dataframes) as expected due to invalid return indicators, while valid inputs with extreme fundamentals computed features safely.
- **Status**: **PASS**

### 2. Time-Series Forward-Filling Correctness
- **Scenarios tested**: Sparse fundamental updates merged into daily prices, sorted in both ascending and descending order.
- **Expected behavior**: Fundamentals are forward-filled chronologically, keeping past dates unaffected by future updates.
- **Actual behavior**:
  - **Ascending order**: Correct chronological forward-filling.
  - **Descending order**: **Lookahead Leakage Detected**. The revenue on `2026-02-10` was filled with `2,000,000` (the future value from `2026-02-15`) instead of `1,000,000` (the past value from `2026-01-15`).
- **Status**: **FAIL** (Vulnerability confirmed)

### 3. Model Training & Prediction Robustness
- **Scenarios tested**: 12-feature model training on 3-stock mock data, batch prediction (`process_and_predict_all`), and single prediction (`predict_current`) under stress:
  - Scenario A (Missing Volume): Raised `KeyError` as expected (Vulnerability confirmed).
  - Scenario B (Extra Columns): Succeeded; model ignored extra columns.
  - Scenario C (Inf prices/volume in latest row): Succeeded by silently dropping the latest row and predicting on the previous day.
  - Scenario D (NaN prices/volume in latest row): Succeeded by silently dropping the latest row and predicting on the previous day.
  - Scenario E (Pre-computed features with NaN in latest row): Succeeded; XGBoost natively handled the NaN feature value and predicted successfully.
  - Scenario F (Pre-computed features with Inf in latest row): Succeeded; XGBoost natively handled the Inf feature value and predicted successfully.
- **Status**: **PASS** (with caveats noted in Challenges 2 and 3)

---

## Unchallenged Areas

- **Technical Models (`MLEngine`)**: `src/analysis/ml_engine.py` was inspected. It relies on 24 market/technical indicators (e.g. `rsi_14`, `macd`, `bb_width`) and does not utilize fundamental parameters like `operating_margin`, `revenue_to_market_cap`, or `dividend_yield`. Hence, it was excluded from the fundamental-specific challenge scope.
