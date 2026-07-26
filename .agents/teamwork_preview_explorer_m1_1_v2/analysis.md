# Comprehensive Audit Report: Strategy & Prediction Models

## Executive Summary
This audit investigated the 5 trading strategies and prediction models within `trading_system/src/ai/` and `trading_system/run_pipeline.py`. The investigation uncovered **9 primary root cause mechanisms** that account for:
1. Expected returns in `pipeline_result.txt` defaulting to `0.0` / `0.0%`.
2. Surge predictions, Lead-Lag predictions, VCP patterns, and VCP ML predictions producing empty, zero, or uncalibrated outputs.
3. Feature matrix values producing NaNs, zeros, or corrupted training/inference targets.

---

## Part 1: Root Causes of 0.0 / 0.0% Expected Returns in Regression (`pipeline_result.txt`)

### 1.1 Model Key / Market Name Lookup Discrepancy & Fallback to Default 0.0
- **File**: `trading_system/src/ai/prediction_model.py`
- **Line Numbers**: Lines 1938–2046 (`_predict_regression`)
- **Mechanism**:
  In `_predict_regression()`, predictions are computed per market `mkt` in `set(market_list)`.
  The model lookup relies on `case_insensitive_get(self.models, mkt, {}).get(h)`.
  If a model for horizon `h` is missing from `self.models[mkt]`, `self.lgb_models[mkt]`, and `self.cat_models[mkt]` (e.g., due to model load failure, missing model file, or small dataset skipping walk-forward training), `preds` list remains empty.
  When `preds` is empty, line 2044 executes:
  ```python
  res_df.loc[idx, h] = 0.0
  logger.warning(f"Regression prediction for market={mkt}, horizon={h} defaulted to 0.0 due to missing models.")
  ```
  This forces all predicted returns for horizon `h` of market `mkt` to default to `0.0`.

### 1.2 Unfitted Scaler Fallback & Feature Distortion
- **File**: `trading_system/src/ai/prediction_model.py` (lines 1958–1960), `trading_system/src/ai/feature_engineering.py` (lines 31–49)
- **Mechanism**:
  During inference in `_predict_regression()`, `load_scaler(str(self.model_dir), scaler_mkt, h)` is called.
  If the scalar file `scaler_{scaler_mkt}_{h}d.joblib` is missing or fails to load, `load_scaler` logs a warning and returns an unfitted `StandardScaler()`.
  When `apply_scaler()` calls `scaler.transform(X)`, scikit-learn raises a `NotFittedError`. `apply_scaler()` catches this exception and returns raw (unscaled) features.
  Feeding unscaled raw feature values (e.g. market cap ~$10^{11}$, volume ~$10^6$) into XGBoost / LightGBM models trained on standard-scaled features ($Z$-scores with mean 0, std 1) causes all tree split nodes to evaluate out-of-distribution extremes, driving predictions to tree leaf defaults (0.0).

### 1.3 Sharpe-Scale Inversion Multiplication by Zero Volatility (`vol_20d`)
- **File**: `trading_system/src/ai/prediction_model.py` (lines 2035–2042), `trading_system/src/ai/target_transform.py` (lines 28–46)
- **Mechanism**:
  The model outputs Sharpe-scaled predictions ($\text{raw\_return} / \text{vol\_20d}$).
  During inference, `inverse_transform_sharpe(blend_pred, vol_scale)` is called, where `vol_scale` is retrieved from `X_mkt_raw['vol_20d']`.
  `inverse_transform_sharpe` computes:
  ```python
  sharpe = np.sign(pred_series) * (np.expm1(np.abs(pred_series)))
  raw_ret = sharpe * vol_scale.values
  ```
  For any stock with zero volume, flat price history, or trading halt over the 20-day window, `vol_20d` is `0.0` (or filled with `0.0` in `_create_features`).
  Multiplying `sharpe * 0.0` forces the inverse-transformed expected return to be EXACTLY `0.0`.

### 1.4 Single-Stock `predict_current()` Minimum Length Short-Circuit
- **File**: `trading_system/src/ai/prediction_model.py` (lines 1800–1809)
- **Mechanism**:
  `predict_current()` calls `_create_features(df_current)`.
  In `_create_features()`, line 919 checks `if len(df) < 65: return pd.DataFrame()`.
  When `_create_features` returns an empty DataFrame, line 1809 short-circuits and returns `{h: 0.0 for h in self.horizons}`.
  Line 1812 also contains an unassigned statement `latest[self.ALL_FEATURES]`, which is a syntax no-op bug.

---

## Part 2: Root Causes of Empty, 0.0%, or NaN Outputs in Surge, Lead-Lag, VCP Rules, and VCP ML

### 2.1 Target Mismatch Bug in Surge Classifier Training (`train_surge`)
- **File**: `trading_system/src/ai/prediction_model.py` (lines 1575–1589)
- **Mechanism**:
  In `train_surge()`:
  ```python
  for h in self.surge_horizons:
      target_col = f'target_{h}d'
      if target_col not in df_train.columns:
          df_train[target_col] = ... # compute raw return shift(-h)/x - 1
      target = (df_train[target_col] >= self.surge_threshold).astype(int)
  ```
  **Critical Defect**: Before `train_surge()` is called, `prepare_training_data()` calls `_create_targets()` which populates `df_train['target_{h}d']` as **Sharpe-scaled returns** ($\text{raw\_ret} / \text{vol\_20d}$).
  Because `target_{h}d` ALREADY exists in `df_train`, `if target_col not in df_train.columns` is `FALSE`. `train_surge` NEVER recomputes raw returns!
  It directly compares `Sharpe-scaled return >= 0.20`.
  - For low-volatility stocks ($\text{vol\_20d} = 0.01$), a tiny +0.3% return becomes a Sharpe ratio of $0.30 \ge 0.20$, wrongly labeled as a 20% SURGE (false positive).
  - For high-volatility stocks ($\text{vol\_20d} = 0.20$), a 15% surge becomes $0.15 / 0.20 = 0.75 \ge 0.20$, but noisy small returns corrupt the classifier.
  This target corruption distorts model training, producing garbage probability predictions (0.0 or flat values) at inference.

### 2.2 Surge Horizon 20% Threshold Extreme Class Imbalance (Zero Positive Samples)
- **File**: `trading_system/src/ai/prediction_model.py` (lines 1588–1596, 2142–2144)
- **Mechanism**:
  In `train_surge()`, `pos_count = target.sum()`. If `pos_count == 0`, the training loop logs a warning and skips model creation.
  For 1-day or 3-day horizons (`surge_1d`, `surge_3d`), achieving $\ge 20\%$ return is virtually impossible for SP500 or KOSPI large-cap stocks during typical training periods.
  When no model is trained, `self.surge_models[market][h]` is empty.
  At inference time (`_predict_surge`), missing models cause `preds` to be empty, line 2143 executes:
  `res_df.loc[idx, col_name] = 0.0`
  resulting in 0.0% surge probability output for all symbols in `surge_predictions.txt`.

### 2.3 Rule-Based VCP Pattern Detection Nested Max Window Flaw (`detect_vcp`)
- **File**: `trading_system/src/ai/vcp_detector.py` (lines 37–47, 97)
- **Mechanism**:
  `detect_vcp()` evaluates daily price ranges across 5 nested windows: `windows = [5, 10, 20, 40, 60]`.
  ```python
  ranges = [float(df['range_pct'].tail(w).max()) for w in windows]
  decreasing = all(ranges[i] < ranges[i + 1] for i in range(len(ranges) - 1))
  ```
  `tail(w)` windows are cumulative subsets: the 60-day window contains the 40-day window, which contains the 20-day window, etc.
  If the single largest daily volatility spike of the last 60 days occurred within the recent 5 days, then:
  $\text{max}(5d) = \text{max}(10d) = \text{max}(20d) = \text{max}(40d) = \text{max}(60d)$.
  Under strict inequality `<` (`ranges[0] < ranges[1]`), `decreasing` evaluates to `False`.
  Line 97 requires `is_vcp = decreasing and above_sma50 and score >= 50`.
  Because `decreasing` evaluates to `False` whenever any shorter window's max range equals a longer window's max range (or whenever a recent surge occurs), valid VCP patterns are rejected, causing 0 patterns or empty `vcp_patterns.txt`.

### 2.4 Lead-Lag Leader Returns Zero / Key Mismatch Fallback Behavior
- **File**: `trading_system/src/ai/prediction_model.py` (lines 2330–2396)
- **Mechanism**:
  In `predict_lead_lag()`, `today_returns` dict is populated from `prices_dict.items()`.
  If leader ticker strings in `self.lead_lag_matrix` (e.g. `'005930'`) do not match keys in `prices_dict` (e.g. `'005930.KS'`), `today_returns.get(leader, 0.0)` returns `0.0`.
  If all leaders have $\le 0.001$ return today (e.g., market drop or ticker mismatch), `follower_scores` is empty.
  While a correlation-only fallback exists (lines 2379–2386), if `self.lead_lag_matrix` is unpopulated or missing from disk (`lead_lag_matrix.json`), `predict_lead_lag` returns an empty DataFrame `pd.DataFrame()`, producing `"데이터 없음"` in `lead_lag_predictions.txt`.

### 2.5 VCP ML Predictor Feature Pre-Drop & Length Rejection
- **File**: `trading_system/src/ai/vcp_ml_predictor.py` (lines 126–138, 173–186, 610–696)
- **Mechanism**:
  In `_compute_vcp_features()`, line 126 rejects any DataFrame with `len(df) < 200`.
  In `_batch_features_with_vcp()`, line 171 drops any symbol where `vcp_feat.empty` is True.
  During model loading (`load_models()`), dummy validation `model.predict_proba(dummy_df)` is performed. If feature column alignment differs between training and loading (e.g. `VCP_FEATURES` ordering vs `ALL_FEATURES`), XGBoost/LightGBM raises a feature name / shape mismatch exception, model load is skipped, and inference defaults all VCP ML probabilities to `0.0`.

---

## Part 3: Feature Matrix Corruptions (NaNs, Zeros, Inconsistencies)

### 3.1 Dropna Truncation & Insufficient Rows
- **File**: `trading_system/src/ai/prediction_model.py` (lines 956–960, 1119–1128)
- **Mechanism**:
  In `_create_features()`:
  `df['ret_60d'] = df['Close'].pct_change(60)` creates 60 NaNs at the start.
  Line 1128 calls `df = df.dropna(subset=existing_tech_cols)`.
  Because `ret_60d` is included in `existing_tech_cols`, `dropna` truncates the first 60 rows of history.
  If an input price DataFrame has 65 rows, after `dropna` only 5 rows remain!
  Then downstream checks requiring $\ge 65$ or $\ge 200$ rows reject the stock, causing empty DataFrames.

### 3.2 Fundamental Features Imputation & `has_fundamental` Masking
- **File**: `trading_system/src/ai/prediction_model.py` (lines 1140–1148), `trading_system/src/ai/feature_engineering.py` (lines 22, 42)
- **Mechanism**:
  In `_create_features()`:
  ```python
  if 'has_fundamental' in df.columns:
      mask_no_fund = (df['has_fundamental'] == 0.0)
      for col in fundamental_cols:
          if col in df.columns:
              df.loc[mask_no_fund, col] = np.nan
  ```
  Setting fundamental columns to `np.nan` is intended to preserve missingness for tree models.
  However, during feature scaling in `apply_scaler()`:
  `X = df[features].fillna(0.0)`
  Missing fundamental features are replaced with `0.0` prior to `StandardScaler.transform()`.
  This transforms missing fundamentals into $Z$-score values representing zero operating margin, zero revenue, zero EPS, wrongly signaling extreme financial distress to ML models instead of neutral missing data.

### 3.3 Global Macro Indicator Date Index Alignment Discrepancy
- **File**: `trading_system/src/ai/prediction_model.py` (lines 890–905)
- **Mechanism**:
  `_merge_indicator_history(df, indicator_df)` executes `df = df.join(indicator_df, how='left')`.
  If `df.index` is a string date index (e.g. `'2026-06-23'`) while `indicator_df.index` is a `DatetimeIndex` (or timezone-aware), `df.join()` fails to match rows and produces `NaN` for all global features (`vix_change`, `us10y`, `sp500_change`, etc.).
  Line 904 then executes `df[self.GLOBAL_FEATURES] = df[self.GLOBAL_FEATURES].ffill().fillna(0.0)`, turning all global macro indicators into static `0.0`s.

### 3.4 Discrepancy in `vol_20d` Feature vs Target Scaling Floor
- **File**: `trading_system/src/ai/prediction_model.py` (lines 964, 1167–1170)
- **Mechanism**:
  In `_create_features()`: `df['vol_20d'] = df['ret_1d'].rolling(20).std().fillna(0.0)`.
  In `_create_targets()`: `vol_20d = pct_chg.rolling(20, min_periods=5).std().fillna(method='bfill').fillna(0.01)`.
  In feature engineering, `vol_20d` has 0.0 for the first 20 rows and whenever returns are constant.
  In target creation, `vol_20d` has a 0.01 floor.
  This inconsistency creates a distribution mismatch between training targets, model features, and inference inverse-scaling.

---

## Part 4: Proposed Remediations (for Implementer Phase)

1. **Surge Target Fix**: In `train_surge()`, compute raw forward returns `raw_ret = df_train.groupby('symbol')['Close'].transform(lambda x: x.shift(-h)/x - 1)` explicitly instead of using `df_train['target_{h}d']` (which holds Sharpe-scaled returns).
2. **Surge Threshold Calibration**: Adjust surge threshold per horizon (e.g. 1d: 3%, 3d: 5%, 5d: 8%, 20d: 15% or 20%) to avoid zero-positive-sample training skips on short horizons.
3. **VCP Contraction Logic Fix**: In `vcp_detector.py`, update `decreasing` calculation to use non-overlapping windows or relaxed monotonic criteria (`ranges[i] <= ranges[i+1]` with eps tolerance) instead of cumulative nested `tail(w).max()`.
4. **Scaler Persistence Fix**: Ensure `fit_scaler` and `load_scaler` use consistent market names (mapping KOSPI/KOSDAQ/KONEX to KRX or market-specific names uniformly) and fit default scalers when missing.
5. **Volatility Floor Guard**: Enforce a minimum floor (e.g., `0.005` or 0.5% annualized) on `vol_20d` across all feature creation and inverse transform steps so `inverse_transform_sharpe` never evaluates to `0.0`.
6. **Date Index Normalization**: Normalize `df.index` to `pd.to_datetime(df.index)` before performing `df.join(indicator_df)` in `_merge_indicator_history()`.
7. **Symbol Suffix Normalization**: Ensure ticker symbols in `lead_lag_matrix` and `prices_dict` are normalized (stripping `.KS`, `.KQ`) prior to correlation lookup.
