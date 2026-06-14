# Handoff Report — Fundamental Features & Predictions Verification

## 1. Observation

Adversarial testing was performed using the custom test suite `trading_system/tests/test_fundamental_prediction_adversarial.py`. The test suite was executed via:
```powershell
$env:PYTHONPATH="trading_system"; python -m pytest trading_system/tests/test_fundamental_prediction_adversarial.py
```

Result: 3 out of 6 tests failed. Verbatim failures from the test execution logs:

1. **Duplicate fundamental dates duplication**:
   ```
   df_merged_dupes = self.model.merge_fundamentals("AAPL", df_prices, storage=MockStorageDupes())
   >       self.assertEqual(len(df_merged_dupes), length, "WARNING: Duplicate fundamental dates caused price row duplication!")
   E       AssertionError: 101 != 100 : WARNING: Duplicate fundamental dates caused price row duplication!
   ```
   File: `trading_system/src/ai/prediction_model.py` line 232:
   ```python
   df = pd.merge(df, df_fun, left_on='date_align', right_on='date', how='left')
   ```

2. **Blanket dropna emptying dataset**:
   ```
   df_zero = pd.DataFrame(base_data, index=dates)
   df_zero["Close"] = 0.0
   ...
   res_zero = self.model._create_features(df_zero)
   >       self.assertFalse(res_zero.empty)
   E       AssertionError: True is not false
   ```
   File: `trading_system/src/ai/prediction_model.py` lines 279, 293:
   ```python
   df['ret_1d'] = df['Close'].pct_change(1)
   ...
   df.dropna(inplace=True)
   ```

3. **KeyError on partial precomputed features**:
   ```
   df_aapl_pre = df_aapl.copy()
   df_aapl_pre['ret_1d'] = 0.0
   >       preds_pre = self.model.predict_current(df_aapl_pre)
   ...
   E           KeyError: "['ret_5d', 'ret_20d', 'ret_60d', 'dist_sma_20', 'vol_20d', 'operating_margin', 'revenue_to_market_cap', 'dividend_yield'] not in index"
   ```
   File: `trading_system/src/ai/prediction_model.py` lines 354, 372:
   ```python
   if 'ret_1d' not in df_current.columns:
       ...
   else:
       ...
   X = latest[features]
   ```

---

## 2. Logic Chain

1. **Duplicate date row inflation**:
   - `merge_fundamentals` executes a left join between the price DataFrame `df` and the fundamentals DataFrame `df_fun`.
   - If `df_fun` contains duplicate rows for the same date (e.g. `dates[10]`), the left join matches multiple rows in `df_fun` for that date.
   - This results in duplicate rows in the merged DataFrame, causing its length to grow (e.g. from 100 to 101).
   - Therefore, database duplicates in fundamentals directly corrupt price time-series length and order.

2. **Halted stock empty DataFrame**:
   - A halted/zero-price stock has constant `Close` prices of 0.0.
   - The method `_create_features` computes `pct_change()` on `Close`.
   - Since `(0.0 - 0.0) / 0.0` is `NaN`, all returns (`ret_1d`, `ret_5d`, etc.) evaluate to `NaN` for all rows.
   - At the end of `_create_features`, `df.dropna(inplace=True)` drops all rows that contain `NaN` in any column.
   - Since all rows contain `NaN` in returns, the entire DataFrame is dropped.
   - Therefore, halted/zero-price stocks return empty feature sets.

3. **Partial precomputed feature crash**:
   - `predict_current` uses `if 'ret_1d' not in df_current.columns` as a shortcut indicator to check if features are precalculated.
   - If `'ret_1d'` is present but other features are missing, it assumes *all* features are present, bypassing `_create_features`.
   - When it reaches `X = latest[features]`, it tries to select all 12 features from the DataFrame.
   - Since the other 11 features are missing, pandas raises a `KeyError`.
   - Therefore, partial features lead to key error crashes.

---

## 3. Caveats

- **Database storage**: We did not verify DB connection pools or ORM-specific behaviors, using a mock database class for standard alignment checks.
- **XGBoost internal handling of NaN/Inf**: While XGBoost can natively handle missing values during prediction, it was not tested on features that are completely missing (columns missing) since that causes a pandas `KeyError` before the model is invoked.

---

## 4. Conclusion

The feature calculations and predictions exhibit three distinct bugs under adversarial stress:
1. Row duplication when merging duplicate fundamental dates.
2. Complete dataset erasure via dropna on zero/constant close prices.
3. KeyError crash in `predict_current` when some but not all features are precalculated.
The extreme out-of-bound fundamental calculations, short-input limits, and extra column scenarios are handled robustly without crashes or overflows.

---

## 5. Verification Method

To verify these findings, run:
```powershell
$env:PYTHONPATH="trading_system"; python -m pytest trading_system/tests/test_fundamental_prediction_adversarial.py
```
This test suite runs all 6 stress scenarios, verifying where the codebase behaves correctly and demonstrating the 3 failures described above.
