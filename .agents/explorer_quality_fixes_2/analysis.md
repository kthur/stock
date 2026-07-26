# Strategy Output Quality Bug Analysis

This report diagnoses and analyzes the four strategy output quality bugs in the stock prediction pipeline and proposes concrete fixes.

---

## Bug 1: Surge Classifier 0% Probability (Model load paths in GHA/distributed pipeline)

### Root Cause
1. **GitHub Actions Cache Mismatch**: The training workflow (`training.yml`) caches AI models using the key structure `ai-models-v2-${{ steps.date.outputs.date }}-${{ matrix.target }}`. However, the inference pipeline (`pipeline.yml`) attempts to restore the models using `ai-models-v2-${{ matrix.target }}-${{ steps.date.outputs.date }}`. This mismatch causes cache restores to fail, meaning the `trading_system/models/` directory is left empty.
2. **Incomplete Fallback Market List**: If models are missing, the fallback check in `load_surge_models` and `load_models` only checks for `sp500` and `krx`. However, the model files are saved using target-specific market names (`kospi`, `kosdaq`, `konex`). Thus, target-specific models are skipped.
3. **Missing prediction fallback**: In `_predict_surge` and `_predict_regression`, if a model for a specific market (e.g., `kospi`) is not found, the code does not fall back to checking the `'krx'` models, defaulting the probability to `0.0%`.

### Evidence
- **Cache Key Mismatch**:
  - `training.yml` line 66:
    ```yaml
    key: ai-models-v2-${{ steps.date.outputs.date }}-${{ matrix.target }}
    ```
  - `pipeline.yml` line 69:
    ```yaml
    key: ai-models-v2-${{ matrix.target }}-${{ steps.date.outputs.date }}
    ```
- **Fallback Check**:
  - `prediction_model.py` line 578:
    ```python
    for market in ['sp500', 'krx']:
    ```
- **Prediction default**:
  - `prediction_model.py` lines 2004-2006:
    ```python
    else:
        res_df.loc[idx, col_name] = 0.0
        logger.warning(f"Surge prediction for market={mkt}, horizon={h} defaulted to 0.0 due to missing models.")
    ```

### Proposed Fixes

#### Fix 1: Align Cache Keys in GHA Workflows
Modify `.github/workflows/pipeline.yml` (around line 69) to align its cache restore key format with the training workflow:
```yaml
      - name: Cache AI models (Restore only)
        uses: actions/cache/restore@v4
        id: models-cache
        with:
          path: trading_system/models
          key: ai-models-v2-${{ steps.date.outputs.date }}-${{ matrix.target }}
          restore-keys: |
            ai-models-v2-${{ steps.date.outputs.date }}-
```

#### Fix 2: Extend Fallback Check Markets in `prediction_model.py`
In `prediction_model.py`'s `load_models()` (around line 441) and `load_surge_models()` (around line 578), expand the checked fallback markets:
```python
# Before
for market in ['sp500', 'krx']:

# After
for market in ['sp500', 'kospi', 'kosdaq', 'konex', 'krx']:
```

#### Fix 3: Implement `krx` Fallback in Predict Loops
In `prediction_model.py`'s `_predict_regression` (around line 1857) and `_predict_surge` (around line 1957), check for `'krx'` models as a fallback if specific market models are missing:
```python
# In _predict_regression:
xgb_m = case_insensitive_get(self.models, mkt, {}).get(h)
if xgb_m is None and mkt in ['kospi', 'kosdaq', 'konex']:
    xgb_m = case_insensitive_get(self.models, 'krx', {}).get(h)
lgb_m = case_insensitive_get(self.lgb_models, mkt, {}).get(h)
if lgb_m is None and mkt in ['kospi', 'kosdaq', 'konex']:
    lgb_m = case_insensitive_get(self.lgb_models, 'krx', {}).get(h)
cat_m = case_insensitive_get(self.cat_models, mkt, {}).get(h)
if cat_m is None and mkt in ['kospi', 'kosdaq', 'konex']:
    cat_m = case_insensitive_get(self.cat_models, 'krx', {}).get(h)

# In _predict_surge:
xgb_m = case_insensitive_get(self.surge_models, mkt, {}).get(h)
if xgb_m is None and mkt in ['kospi', 'kosdaq', 'konex']:
    xgb_m = case_insensitive_get(self.surge_models, 'krx', {}).get(h)
lgb_m = case_insensitive_get(self.surge_lgb_models, mkt, {}).get(h)
if lgb_m is None and mkt in ['kospi', 'kosdaq', 'konex']:
    lgb_m = case_insensitive_get(self.surge_lgb_models, 'krx', {}).get(h)
cat_m = case_insensitive_get(self.surge_cat_models, mkt, {}).get(h)
if cat_m is None and mkt in ['kospi', 'kosdaq', 'konex']:
    cat_m = case_insensitive_get(self.surge_cat_models, 'krx', {}).get(h)
```

---

## Bug 2: Lead-Lag predictions missing for KRX markets (leader selection logic in `prediction_model.py`)

### Root Cause
1. **Global Selection Bias**: The leader selection logic selects the top 50 symbols by market cap across all markets. Since SP500 is in USD and KRX markets are in KRW, and they are normalized differently, comparing them directly is scale-biased.
2. **Missing `market` Column in `df_train`**: The `prepare_training_data` method does not include the symbol's market tag in the prepared DataFrame, which makes it impossible to select representative leaders per market.
3. **Excessive Return Threshold**: The return threshold in `predict_lead_lag` requires the leader's return to be strictly > 1% (`leader_ret <= 0.01`). While reasonable for volatile individual stocks, this threshold filters out index leaders (like `^KS11` and `^KQ11`), which rarely move more than 1% daily, preventing signal propagation.

### Evidence
- **Selection Logic**:
  - `prediction_model.py` lines 2083-2085:
    ```python
    cap_col = 'market_cap' if 'market_cap' in df_train.columns else 'norm_market_cap'
    avg_caps = df_train.groupby('symbol')[cap_col].mean()
    top_50_leaders = avg_caps.nlargest(50).index.tolist()
    ```
- **Threshold**:
  - `prediction_model.py` line 2199:
    ```python
    if leader_ret <= 0.01:
        continue
    ```

### Proposed Fixes

#### Fix 1: Add `market` Column in `prepare_training_data`
Modify `prepare_training_data` to map each symbol to its market and store it in `df_clean`:
```python
        # Build symbol_to_market mapping using storage
        symbol_to_market = {}
        if storage is not None:
            try:
                univ = storage.get_universe()
                if not univ.empty:
                    symbol_to_market = dict(zip(univ['symbol'], univ['market']))
            except Exception as e:
                logger.warning(f"Failed to build symbol_to_market in prepare_training_data: {e}")
```
And during df creation:
```python
            df_clean = df_feat.dropna(subset=drop_subset)
            if not df_clean.empty:
                df_clean['market'] = symbol_to_market.get(sym, 'unknown')
```

#### Fix 2: Select Representative Leaders Per Market
In `compute_lead_lag()`, select leaders proportionally from each market:
```python
        logger.info("Selecting representative leaders per market...")
        cap_col = 'market_cap' if 'market_cap' in df_train.columns else 'norm_market_cap'
        
        leaders = []
        if 'market' in df_train.columns:
            for mkt, n_leaders in [('SP500', 15), ('KOSPI', 15), ('KOSDAQ', 15), ('KONEX', 5)]:
                mkt_df = df_train[df_train['market'].str.upper() == mkt]
                if not mkt_df.empty:
                    avg_caps = mkt_df.groupby('symbol')[cap_col].mean()
                    leaders.extend(avg_caps.nlargest(n_leaders).index.tolist())
        else:
            # Fallback when market column is not present
            avg_caps = df_train.groupby('symbol')[cap_col].mean()
            krx_symbols = [sym for sym in avg_caps.index if self.is_krx_symbol(sym)]
            us_symbols = [sym for sym in avg_caps.index if not self.is_krx_symbol(sym)]
            us_leaders = avg_caps.loc[us_symbols].nlargest(25).index.tolist() if us_symbols else []
            krx_leaders = avg_caps.loc[krx_symbols].nlargest(25).index.tolist() if krx_symbols else []
            leaders = us_leaders + krx_leaders
        
        top_50_leaders = leaders
```

#### Fix 3: Lower Index/Leader Return Threshold
In `predict_lead_lag()`, lower the threshold to `0.001` (0.1%) or `0.0` (any positive movement) so index/sector leaders can propagate co-movement signals:
```python
        for leader, followers in self.lead_lag_matrix.items():
            leader_ret = today_returns.get(leader, 0.0)
            if leader_ret <= 0.001:
                continue
```

---

## Bug 3: VCP ML predictions empty (model path logic in GHA/distributed environment)

### Root Cause
1. **GitHub Actions Cache Mismatch**: Models are not restored due to key mismatch, causing `vcp_ml.models` to be empty.
2. **Aggressive Empty Check**: In `vcp_ml_predictor.py`'s `predict()`, the code checks `if not self.models:`. If XGBoost models are empty but LightGBM (`self.lgb_models`) or CatBoost (`self.cat_models`) models are present, prediction is still skipped entirely.
3. **Missing sub-market fallback**: In the prediction loop, it does not fallback to checking for `'KRX'` models when specific market models (e.g. `'KOSPI'`) are missing.

### Evidence
- **Check Condition**:
  - `vcp_ml_predictor.py` lines 487-489:
    ```python
    if not self.models:
        logger.warning("No VCP ML models loaded, skipping prediction")
        return pd.DataFrame()
    ```

### Proposed Fixes

#### Fix 1: Update Check Condition in `predict()`
Allow prediction to continue if any model type is loaded:
```python
        if not self.models and not self.lgb_models and not self.cat_models:
            logger.warning("No VCP ML models loaded, skipping prediction")
            return pd.DataFrame()
```

#### Fix 2: Add KRX Fallback in VCP ML Predict Loop
In the sub-market prediction loop of `vcp_ml_predictor.py` (around line 514):
```python
                        xgb_m = case_insensitive_get(self.models, mkt, {}).get(h)
                        if xgb_m is None and mkt in ['KOSPI', 'KOSDAQ', 'KONEX']:
                            xgb_m = case_insensitive_get(self.models, 'KRX', {}).get(h)
                        lgb_m = case_insensitive_get(self.lgb_models, mkt, {}).get(h)
                        if lgb_m is None and mkt in ['KOSPI', 'KOSDAQ', 'KONEX']:
                            lgb_m = case_insensitive_get(self.lgb_models, 'KRX', {}).get(h)
                        cat_m = case_insensitive_get(self.cat_models, mkt, {}).get(h)
                        if cat_m is None and mkt in ['KOSPI', 'KOSDAQ', 'KONEX']:
                            cat_m = case_insensitive_get(self.cat_models, 'KRX', {}).get(h)
```

---

## Bug 4: Ensemble outputting 0% for KRX (consequence of Bug 1-3)

### Root Cause & Fix
This is a direct cascading effect of Bugs 1-3. Since Surge, Lead-Lag, and VCP ML scores default to 0.0, the ensemble weights calculate a score biased towards 0% or low scores. Once Bug 1-3 are fixed, Bug 4 is resolved automatically.

---

## R4: Output file placeholder when empty

### Proposed Fixes
To prevent empty files and strictly satisfy R4, add explicit empty-checks writing `"데이터 없음"` to all prediction save blocks:

#### In `run_pipeline.py`:
- **Regression output**:
  ```python
      if res_df.empty:
          with open(output_path, "w", encoding="utf-8") as f:
              f.write("=== Pipeline Inference Summary (TOP10 per Market) ===\n")
              f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
              f.write("데이터 없음: 분석 대상 종목이 없거나 예측 모델 로드에 실패했습니다.\n")
  ```
- **Surge output**:
  ```python
      surge_output_path = os.path.join(result_dir, "surge_predictions.txt")
      if not surge_df.empty:
          # (write logic)
      else:
          with open(surge_output_path, "w", encoding="utf-8") as f:
              f.write("=== Surge Detection Results (>= 20% return) ===\n")
              f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
              f.write("데이터 없음: 급등(Surge) 예상 종목이 없거나 예측 모델 로드에 실패했습니다.\n")
  ```
- **Lead-Lag output**:
  ```python
      lead_lag_output_path = os.path.join(result_dir, "lead_lag_predictions.txt")
      if not lead_lag_df.empty:
          # (write logic)
      else:
          with open(lead_lag_output_path, "w", encoding="utf-8") as f:
              f.write("=== Lead-Lag Surge Predictions ===\n")
              f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
              f.write("데이터 없음: 리드-랙(Lead-Lag) 분석 결과 종목이 없거나 모델 로드에 실패했습니다.\n")
  ```
- **VCP ML output**:
  ```python
      vcp_ml_output_path = os.path.join(result_dir, "vcp_ml_predictions.txt")
      if not vcp_ml_df.empty:
          # (write logic)
      else:
          with open(vcp_ml_output_path, "w", encoding="utf-8") as f:
              f.write("=== VCP ML Surge Predictions ===\n")
              f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
              f.write("데이터 없음: VCP ML 분석 결과 종목이 없거나 모델 로드에 실패했습니다.\n")
  ```
- **Ensemble output**:
  ```python
      ensemble_output_path = os.path.join(result_dir, "ensemble_predictions.txt")
      if not ensemble_df.empty:
          # (write logic)
      else:
          with open(ensemble_output_path, "w", encoding="utf-8") as f:
              f.write("=== Dynamic Multi-Strategy Ensemble Predictions ===\n")
              f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
              f.write("데이터 없음: 앙상블 분석 결과 종목이 없거나 모델 로드에 실패했습니다.\n")
  ```

#### In `merge_predictions.py`:
- Add checks to write `데이터 없음` if a file is empty or missing specific market segments. For instance:
  ```python
          # (inside merge_pipeline_result)
          if not written:
              out.write("데이터 없음: 병합할 분석 결과가 없습니다.\n")
  ```
