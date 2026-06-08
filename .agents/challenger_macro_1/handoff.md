# Handoff Report — challenger_macro_1

This handoff report summarizes the empirical challenge and findings for the Global Macro Correlation Engine and ML Predictor.

## 1. Observation

- **Source Files Inspected**:
  - `trading_system/src/analysis/macro_analyzer.py` (lines 21-72: `calculate_cross_correlation` logic).
  - `trading_system/src/analysis/macro_predictor.py` (lines 33-90: `train_model` and lines 92-110: `predict_outperformers` logic).
  - `trading_system/src/analysis/screener.py` (lines 279-311: `screen_global_outperformers` training and prediction loop).
- **Stress Tests Implemented**:
  - Created `trading_system/tests/test_macro_stress.py` containing 11 tests verifying NaN inputs, varying lengths, extreme numbers, constant values, feature mismatches, write failures, and screener predictions.
- **Verification Results**:
  - Command run: `.venv\Scripts\pytest tests/test_macro.py tests/test_macro_stress.py` in `d:\Finance\code\stock\trading_system`.
  - Verbatim Output:
    ```
    ============================= test session starts =============================
    platform win32 -- Python 3.11.9, pytest-9.0.3, pluggy-1.6.0
    rootdir: D:\Finance\code\stock\trading_system
    configfile: pyproject.toml
    plugins: anyio-4.13.0, dash-4.2.0
    collected 16 items

    tests\test_macro.py .....                                                [ 31%]
    tests\test_macro_stress.py ...........                                   [100%]
    ...
    ======================= 16 passed, 6 warnings in 47.12s =======================
    ```
  - Observed warning logs during tests:
    - `Failed to save macro model metrics to JSON: Permission denied / Disk full simulation`
    - `RuntimeWarning: invalid value encountered in subtract` (numpy internal warning from NaNs).
    - `Pandas4Warning: Sorting by default when concatenating all DatetimeIndex is deprecated.`

## 2. Logic Chain

1. **Correlation Engine Robustness**:
   - `calculate_cross_correlation` handles completely missing/NaN datasets because the NaNs propagate into Pearson correlation, returning `NaN` values, which are subsequently caught and replaced by `0.0` at line 70 (`val if not pd.isna(val) else 0.0`).
   - Varying lengths/non-overlapping dates are padded with boundary values via `.ffill().bfill()` (line 52), producing zero-variance returns which yield `NaN` correlations; these are safely replaced by `0.0`, avoiding crashes.
   - Out-of-bounds numbers result in extreme return percentages, which also flow into `pandas.DataFrame.corr()` and return finite numbers or NaNs (which are replaced by `0.0`), preventing crash errors.
   - Non-overlapping timezones are converted to timezone-naive indices via `.tz_convert(None)` at line 45 and `.normalize()` at line 46, ensuring proper index alignment.

2. **ML Predictor Robustness**:
   - `MacroPredictor.train_model` filters out `NaN` values via `valid_mask` at line 46. If all data is NaN, the dataset length is 0, raising `ValueError` (line 50) as expected instead of crashing.
   - Very small datasets (< 5) raise `ValueError` at line 50. Datasets between 5 and 9 bypass the train/test split at line 56, training and testing on the entire dataset to prevent empty splits.
   - Features not present at prediction time are dynamically aligned at line 101, where missing columns are filled with `0.0` and extra columns are discarded, preventing Scikit-Learn feature count mismatch errors.

3. **Placebo ML Predictor Finding**:
   - In `screener.py` line 280, a single `MacroPredictor` is trained on pooled macro features.
   - Inside the ticker evaluation loop (line 290), `latest_features` (defined at line 286 as the 1-row latest macro return vector) is fed to `predictor.predict_outperformers(latest_features)`.
   - Because `latest_features` is purely macro-based and contains no stock-specific characteristics, the prediction `pred_val` at line 302 is identical for all stocks in the universe.
   - Since `pred_val` is identical for all stocks, the sort by predicted returns (`results.sort(key=lambda x: x["expected_excess_return"], reverse=True)` at line 310) is a stable sort that simply preserves the default input list order. This logic was empirically verified by our passing test `test_screener_predictions_identical`.

4. **Cache Robustness**:
   - If writing `data/macro_model_metrics.json` fails, the exception is caught by the `try...except Exception` block at lines 84-88, preventing training crashes.
   - Since there is no read integration for the metrics cache file, any write failure does not impact other parts of the application.

## 3. Caveats

- **yfinance Network Fetching**: The actual live data download was simulated or fell back to simulated generation during tests due to local offline environment constraints.
- **Race Conditions**: Concurrency on `data/macro_model_metrics.json` was not tested under multi-threaded load, but file overwrite conflicts may occur if multiple workers train simultaneously.

## 4. Conclusion

- **Overall Assessment**: **Robust implementation with a critical design flaw.**
- **Robustness**: The Global Macro Correlation Engine and ML Predictor are highly resilient to malformed, missing, extreme, and timezone-mismatched data. Cache write failures are safely isolated.
- **Flaw**: The ML Predictor acts as a placebo. Because the feature set lacks stock-specific data, the model yields identical predicted excess returns for all stocks on any given day. This renders the stock screening sorting mechanism ineffective (defaulting to the hardcoded list order).

## 5. Verification Method

To verify these findings independently:
1. Navigate to `d:\Finance\code\stock\trading_system`.
2. Run `.venv\Scripts\pytest tests/test_macro.py tests/test_macro_stress.py`.
3. Confirm that all 16 tests pass, validating that all edge cases are handled and that the `test_screener_predictions_identical` test successfully asserts that predictions are identical for all tickers.
