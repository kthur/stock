# Handoff Report

## 1. Observation
- **Code implementation under test**: `d:\Finance\code\stock\trading_system\src\ai\prediction_model.py`
  - In `merge_fundamentals` (lines 247-251):
    ```python
    for col in ['revenue', 'operating_income', 'dividend_per_share']:
        if col not in df.columns:
            df[col] = meta[col]
        else:
            df[col] = df[col].ffill().fillna(meta[col])
    ```
- **Test execution command**:
  `python -m pytest -s trading_system/tests/test_adversarial_fundamental.py`
- **Output from Test execution**:
  - Verification of lookahead leakage in descending series:
    ```
    [LEAKAGE CHECK] Value at 2026-02-10 (ascending): 1000000.0
    [LEAKAGE CHECK] Value at 2026-02-10 (descending): 2000000.0
    [LEAKAGE CHECK] Lookahead leakage detected: True
    ```
  - Stress testing predictions:
    - Missing volume:
      `[STRESS] predict_current raised KeyError as expected (no Volume): 'Volume'`
    - NaN/Inf features in pre-computed dataframes:
      `[STRESS] predict_current with pre-computed NaN feature succeeded, returned: ...`
      `[STRESS] predict_current with pre-computed Inf feature succeeded, returned: ...`

---

## 2. Logic Chain
1. **Time-series forward-filling correctness**:
   - `merge_fundamentals` runs `df[col].ffill()` directly on the merged price-fundamental dataframe.
   - If the index of the dataframe is in descending order (newest first), `ffill()` propagates values from top (future) to bottom (past).
   - This was empirically confirmed in the test logs: a past date (`2026-02-10`) was filled with a future fundamental value (`2,000,000` from `2026-02-15`) instead of the correct historical value (`1,000,000` from `2026-01-15`).
   - Hence, lookahead bias occurs if inputs are descending or unsorted.
2. **Missing columns vulnerability**:
   - `apply_market_normalization` assumes `'Volume'` and `'Close'` columns exist.
   - Removing `'Volume'` resulted in a `KeyError` in the stress test log, showing that missing core columns will crash predictions.
3. **Robustness to NaN / Inf**:
   - If price input has `NaN` or `Inf` in the latest row, the row gets dropped inside `_create_features` via `dropna()`, resulting in a prediction on the second-to-last (valid) day.
   - If features are pre-computed with `NaN` or `Inf` in the latest row, the model (XGBoost) processes them natively and returns a valid float prediction without crashing.

---

## 3. Caveats
- Checked `OnDevicePredictionModel` in `src/ai/prediction_model.py`. `MLEngine` in `src/analysis/ml_engine.py` was reviewed but not tested because it does not use the 3 fundamental features.
- We did not connect to the actual database indicator storage and instead mocked the storage interface during the leakage tests.

---

## 4. Conclusion
The 12-feature model and its calculations are mostly numerically robust and handle NaN/Inf features gracefully (either via dropna or XGBoost native support). However, they are highly vulnerable to:
1. **Lookahead Bias (Critical)**: Future values leak to past dates if input price indexes are sorted descending.
2. **KeyError crashes (Medium)**: Crashes when key price/volume columns are missing.
3. **Silent stale predictions (Medium/Low)**: Silently drops the latest row if its price data has NaN/Inf, predicting on the day before.

---

## 5. Verification Method
To independently verify:
1. Inspect the test suite file `d:\Finance\code\stock\trading_system\tests\test_adversarial_fundamental.py`.
2. Run the command:
   ```powershell
   python -m pytest -s trading_system/tests/test_adversarial_fundamental.py
   ```
3. Verify that the output prints:
   `[LEAKAGE CHECK] Lookahead leakage detected: True`
   along with the outputs of all stress prediction scenarios, and that all 3 tests pass.
