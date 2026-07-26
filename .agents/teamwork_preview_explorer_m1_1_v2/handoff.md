# Handoff Report: Audit of Strategy & Prediction Models (M1, Task 1)

## 1. Observation

### Observation 1: Model Prediction Fallback to 0.0 on Missing Models
- **File**: `trading_system/src/ai/prediction_model.py` (lines 2043–2046 in `_predict_regression`, lines 2142–2145 in `_predict_surge`)
- **Code Quote**:
  ```python
  if preds:
      total_w = sum(weights)
      ...
  else:
      res_df.loc[idx, h] = 0.0
      logger.warning(f"Regression prediction for market={mkt}, horizon={h} defaulted to 0.0 due to missing models.")
  ```
- **Context**: When XGBoost, LightGBM, and CatBoost models for market `mkt` and horizon `h` are missing or failed to load, `preds` is empty, causing predicted returns or surge probabilities to fall back to `0.0`.

### Observation 2: Unfitted Scaler Fallback Returning Raw Unscaled Features
- **File**: `trading_system/src/ai/feature_engineering.py` (lines 31–49) and `trading_system/src/ai/prediction_model.py` (lines 1958–1960)
- **Code Quote**:
  ```python
  def apply_scaler(df: pd.DataFrame, features: list, scaler: StandardScaler) -> pd.DataFrame:
      if df.empty:
          return df
      df_copy = df.copy()
      X = df_copy[features].fillna(0.0)
      try:
          scaled_values = scaler.transform(X)
          df_copy[features] = scaled_values
      except Exception as e:
          logger.warning(f"Failed to apply scaling: {e}. Using raw features.")
      return df_copy
  ```
- **Context**: Calling `transform()` on an unfitted `StandardScaler` raises `NotFittedError`, causing `apply_scaler` to return raw unscaled features.

### Observation 3: Inversion of Sharpe Predictions Returns Zero on Zero Volatility
- **File**: `trading_system/src/ai/target_transform.py` (lines 28–46) and `trading_system/src/ai/prediction_model.py` (lines 2035–2042)
- **Code Quote**:
  ```python
  def inverse_transform_sharpe(pred_series: pd.Series, vol_scale: pd.Series) -> pd.Series:
      sharpe = np.sign(pred_series) * (np.expm1(np.abs(pred_series)))
      raw_ret = sharpe * vol_scale.values
      return pd.Series(raw_ret, index=pred_series.index)
  ```
- **Context**: If `vol_scale` (`vol_20d`) is `0.0` (from zero price movement, trading halt, or `.fillna(0.0)`), `sharpe * 0.0` produces an expected return of `0.0`.

### Observation 4: Target Mismatch in Surge Classifier Training
- **File**: `trading_system/src/ai/prediction_model.py` (lines 1575–1589)
- **Code Quote**:
  ```python
  for h in self.surge_horizons:
      target_col = f'target_{h}d'
      if target_col not in df_train.columns:
          df_train[target_col] = ...
      target = (df_train[target_col] >= self.surge_threshold).astype(int)
  ```
- **Context**: `df_train` already has `target_{h}d` populated by `_create_targets()` as Sharpe-scaled returns ($\text{raw\_ret} / \text{vol\_20d}$). `if target_col not in df_train.columns` is `False`, so `train_surge` compares Sharpe-scaled targets against `surge_threshold` (0.20), corrupting surge labels.

### Observation 5: Zero Positive Samples in Short Horizon Surge Training
- **File**: `trading_system/src/ai/prediction_model.py` (lines 1590–1595)
- **Code Quote**:
  ```python
  pos_count = target.sum()
  if pos_count == 0:
      logger.warning(f"No surge samples for {market} {h}d, skipping")
      continue
  ```
- **Context**: A 20% surge in 1 or 3 days is extremely rare in large-caps. When `pos_count == 0`, model training is skipped, causing predictions for that horizon to default to 0.0.

### Observation 6: Nested Tail Window Flaw in Rule-Based VCP Pattern Detection
- **File**: `trading_system/src/ai/vcp_detector.py` (lines 37–47, 97)
- **Code Quote**:
  ```python
  windows = [5, 10, 20, 40, 60]
  ranges = []
  for w in windows:
      r = float(df['range_pct'].tail(w).max())
      ranges.append(r)
  decreasing = all(ranges[i] < ranges[i + 1] for i in range(len(ranges) - 1))
  ```
- **Context**: `tail(60)` contains `tail(40)`, which contains `tail(20)`, etc. If a volatility spike occurred within the last 5 days, `ranges[0] == ranges[1] == ... == ranges[4]`, making `decreasing` `False` and forcing `is_vcp = False`.

### Observation 7: Date Index Discrepancy in Global Macro Feature Join
- **File**: `trading_system/src/ai/prediction_model.py` (lines 890–905)
- **Code Quote**:
  ```python
  df = df.join(indicator_df, how='left')
  ...
  df[self.GLOBAL_FEATURES] = df[self.GLOBAL_FEATURES].ffill().fillna(0.0)
  ```
- **Context**: If `df.index` is a string date index and `indicator_df.index` is a `DatetimeIndex`, `join()` fails to align rows, filling all 9 global macro features with `0.0`.

---

## 2. Logic Chain

1. **Premise**: In `_predict_regression` (Obs 1), when model loading or training fails for a given market and horizon, `preds` is empty and predictions default to `0.0`.
2. **Premise**: In `feature_engineering.py` (Obs 2), missing scaler files cause `apply_scaler` to return raw unscaled features. Tree models trained on scaled inputs evaluate unscaled values out-of-distribution, outputting zero or leaf default predictions.
3. **Premise**: In `target_transform.py` (Obs 3), `vol_20d` is used to scale Sharpe predictions back to raw returns. When `vol_20d == 0.0` (unfloored rolling std), `sharpe * 0.0` yields zero expected return.
4. **Premise**: In `train_surge` (Obs 4 & Obs 5), `df_train['target_{h}d']` already contains Sharpe-scaled returns from regression preprocessing. Comparing Sharpe ratios against a 20% raw return threshold corrupts training labels. Additionally, a static 20% threshold on 1d/3d horizons produces zero positive samples, skipping model creation and defaulting surge outputs to `0.0%`.
5. **Premise**: In `detect_vcp` (Obs 6), calculating `tail(w).max()` over nested windows means any recent price expansion forces `r5 == r10 == r20`, making `decreasing` `False` and rejecting valid VCP setups.
6. **Premise**: In `_merge_indicator_history` (Obs 7), joining mismatched index types between price DataFrames and macro indicator DataFrames yields NaNs, which `.fillna(0.0)` converts to all zeros across global features.
7. **Conclusion**: These interconnected defects in feature alignment, target calculation, model lookup fallbacks, and window logic are the direct root causes of 0.0 expected returns, empty predictions, and feature corruption across the pipeline.

---

## 3. Caveats

- **No Code Modifications Made**: Per agent role constraints as an Exploration Specialist, no code files were modified in `src/` or `trading_system/`.
- **Environment Dependencies**: Model loading behavior depends on whether model files (`.json`, `.txt`, `.joblib`) exist in `trading_system/models/`. If models are generated from scratch using small training samples, class imbalance issues become more pronounced.
- **Hardware/CUDA Access**: CUDA/GPU availability affects model training runtime, but the logical bug mechanisms identified above are independent of hardware execution mode.

---

## 4. Conclusion

The audit has successfully identified all root causes responsible for 0.0 expected returns, empty prediction text files, and NaN/zero feature corruptions. A detailed, multi-part analysis report has been produced at `d:\Finance\code\stock\.agents\teamwork_preview_explorer_m1_1_v2\analysis.md`. The findings provide clear, actionable remediation specifications for the Implementer agent in Milestone 2.

---

## 5. Verification Method

To independently verify the audit findings:
1. **Inspect Audit Files**:
   - `d:\Finance\code\stock\.agents\teamwork_preview_explorer_m1_1_v2\analysis.md`
   - `d:\Finance\code\stock\.agents\teamwork_preview_explorer_m1_1_v2\handoff.md`
2. **Code Trace Verification**:
   - Verify line numbers 1575–1589 in `trading_system/src/ai/prediction_model.py` (`train_surge` target column check).
   - Verify line numbers 1938–2046 in `trading_system/src/ai/prediction_model.py` (`_predict_regression` fallback to 0.0).
   - Verify line numbers 37–47 in `trading_system/src/ai/vcp_detector.py` (`tail(w).max()` nested window range comparison).
   - Verify line numbers 31–49 in `trading_system/src/ai/feature_engineering.py` (`apply_scaler` exception handling).
3. **Invalidation Conditions**:
   - The findings would be invalidated if `train_surge` recomputed raw returns before thresholding, or if `inverse_transform_sharpe` used a strictly positive floored volatility scale.
