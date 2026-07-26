# Codebase and GHA Investigation Analysis Report

This report documents operating bugs, logical errors, and configuration discrepancies identified in the `stock` trading system codebase and GitHub Actions workflows.

---

## 1. GitHub Actions Workflows (`.github/workflows/*`)

### Findings & Issues
1. **AI Models Cache Key and Immutability (`pipeline.yml` & `training.yml`)**:
   - Both workflows use a static cache key `ai-models-v2`. Because GitHub Actions caches are immutable, once this key is cached, it can never be updated.
   - In `training.yml` (weekly training), the new models are trained but can never overwrite the existing `ai-models-v2` cache.
   - In `pipeline.yml` (daily pipeline), the step retrieves the static `ai-models-v2` cache and sets `SKIP_TRAINING: ${{ steps.models-cache.outputs.cache-hit == 'true' && 'True' || 'False' }}`. Because the cache key is static, `cache-hit` will always be `'true'` (once cached), and daily pipeline will forever skip training and run inference using outdated/stale models.
   - **Remedy**: Use a dynamic cache key containing a date, e.g., `ai-models-v2-${{ steps.date.outputs.date }}`, with `restore-keys` set to `ai-models-v2-` to retrieve the latest available cached models.

2. **Conditional `SKIP_TRAINING` Logic Bug (`run_pipeline.py`)**:
   - In `run_pipeline.py` (lines 550-561), if `SKIP_TRAINING` is requested (`cfg.skip_training == True`), the code checks if pre-trained models are available on disk. If any models are missing, it logs a warning but still sets `should_skip = True`, causing the pipeline to skip training and predict `0.0`.
   - **Remedy**: Set `should_skip = False` if any pre-trained model is missing on disk so that training runs automatically.

3. **Release Asset Upload Reliability**:
   - `pipeline.yml` merges results from different matrix targets (`SP500`, `KOSPI`, `KOSDAQ`, `KONEX`) in `merge-and-release` job.
   - Artifact download and reconstruction paths are correct, but `gh release create` and `gh release upload` handles release duplication gracefully with fallback (`|| echo "Release ... already exists"`). GITHUB_TOKEN has write permission to `contents`.

---

## 2. Prediction Model (`prediction_model.py`)

### Findings & Issues
1. **Silent Fallback to `0.0` Expected Returns**:
   - When models are missing for a given market/horizon, `_predict_regression()` and `_predict_surge()` silently assign `0.0` prediction values without logging any warning.
   - **Remedy**: Add `logger.warning()` to clearly log instances where models are missing and the prediction defaults to `0.0`.

2. **Ensemble Weights Key Type Mismatch (int vs str)**:
   - JSON keys parsed from `ensemble_weights.json` are always strings (e.g. `"5"`).
   - In `_predict_regression()` (lines 1821-1822), the lookup checks `self.ensemble_weights.get("regression", {}).get(mkt, {}).get(h, {})` where `h` is an integer. This look up always fails and returns `{}`, meaning custom ensemble weights are never applied and always fall back to `0.4/0.3/0.3`.
   - **Remedy**: Query with `str(h)` and fallback to `h`.

3. **Market Tag Casing Mismatch**:
   - The model directory keys in `self.models` are loaded in lowercase (`'sp500'`, `'kospi'`, etc.) by parsing model filenames.
   - In `_predict_regression` and `_predict_surge`, the market lookups `self.models.get(mkt)` use raw market tags which can be uppercase (e.g. `'SP500'`). If uppercase, model lookups fail, returning `None` and defaulting predictions to `0.0`.
   - **Remedy**: Implement case-insensitive lookups for all models, calibration dicts, and weights.

---

## 3. VCP ML Predictor (`vcp_ml_predictor.py`)

### Findings & Issues
1. **Platt Scaling and Hardcoded Ensemble Weights**:
   - VCP ML prediction hardcodes ensemble weights to `[0.4, 0.3, 0.3]` and ignores the `ensemble_weights.json` weight configurations.
   - **Remedy**: Look up weights from `ensemble_weights.json` under `"vcp_ml"` (case-insensitively and with integer/string keys fallback) before resorting to hardcoded values.
   - Platt Scaling calibration is loaded case-insensitively, which is correct.

2. **Casing Consistency**:
   - The market tags in `vcp_ml_predictor.py` are uppercase (`MARKETS = ['KOSPI', 'KOSDAQ', 'KONEX', 'SP500']`), but the base `OnDevicePredictionModel` uses lowercase tags. Models are loaded case-insensitively, but warnings are missing when models are not loaded.

---

## 4. Data Loading and Feature Engineering

### Findings & Issues
1. **`ALL_FEATURES` Order and Dimension Alignment**:
   - The feature columns order is preserved using `ALL_FEATURES` during regression and surge training/inference.
   - However, in VCP ML `predict()`, `feat_cols` is dynamically filtered based on `feats[0].columns` which could cause feature dimension mismatch if some features are missing in the inference data.
   - **Remedy**: Pad missing features with `0.0` rather than dropping columns, and align `feat_cols` strictly to the trained feature set `ALL_FEATURES + VCP_FEATURES`.

2. **`load_scaler` Fallback and Missing Global Indicators**:
   - `load_scaler` returns an unfitted `StandardScaler` if the scaler file is missing, triggering a graceful `NotFittedError` handling in `apply_scaler` that falls back to raw features.
   - In `_merge_indicator_history()`, the code runs `df[self.GLOBAL_FEATURES] = df[self.GLOBAL_FEATURES].ffill().fillna(0.0)`. If any global indicator ticker fails to download, that column will not exist in `df`, raising a `KeyError` and crashing the entire pipeline.
   - **Remedy**: Populate any missing global feature columns in `df` with `0.0` before performing `ffill()`.

---

## 5. Output Verification Logic

### Findings & Issues
1. **Missing Warnings for Empty or 0.0 Predictions**:
   - The pipeline currently lacks any validation check to verify if the output files (such as `pipeline_result.txt`, `vcp_ml_predictions.txt`, etc.) are empty or if the expected returns in `pipeline_result.txt` are all `0.0` (due to silent model load failures).
   - **Remedy**: Add a verification step at the end of `run_pipeline.py` to check file sizes and assert non-zero predictions, raising warnings when failures are detected.

---

## Proposed Diff Patches

### Patch 1: `trading_system/run_pipeline.py`
```diff
@@ -554,9 +554,9 @@
         if regression_loaded and surge_loaded and vcp_loaded:
             logger.info("Pre-trained models found and loaded successfully. Skipping model training phase.")
             should_skip = True
         else:
-            logger.warning("Missing or incomplete pre-trained models on disk but SKIP_TRAINING is requested. Skipping model training phase anyway.")
-            should_skip = True
+            logger.warning("Missing or incomplete pre-trained models on disk but SKIP_TRAINING is requested. Training models automatically.")
+            should_skip = False
 
     update_interval = cfg.get_update_interval()
@@ -1227,5 +1227,24 @@
             f.write(f"Remaining Cash   : {cash_weight*100:>5.2f}% ({cash_amount:>14,.0f})\n")
         logger.info(f"Saved portfolio allocation recommendations to {alloc_output_path}")
 
+    # Output files verification and warnings for empty or 0.0 values
+    prediction_files = [
+        "pipeline_result.txt", "surge_predictions.txt", "lead_lag_predictions.txt", 
+        "vcp_patterns.txt", "vcp_ml_predictions.txt", "ensemble_predictions.txt"
+    ]
+    for file_name in prediction_files:
+        file_path = os.path.join(result_dir, file_name)
+        if os.path.exists(file_path):
+            if os.path.getsize(file_path) == 0:
+                logger.warning(f"Prediction output file '{file_name}' is empty.")
+        else:
+            logger.warning(f"Prediction output file '{file_name}' was not created.")
+
+    if not res_df.empty:
+        non_zero_found = False
+        for h in [1, 5, 10, 20, 30, 60, 120, 200]:
+            if h in res_df.columns and (res_df[h] != 0.0).any():
+                non_zero_found = True
+                break
+        if not non_zero_found:
+            logger.warning("All regression predicted expected returns in pipeline_result.txt are 0.0.")
+
     return res_df, message_text
```

### Patch 2: `trading_system/src/ai/prediction_model.py`
```diff
@@ -840,4 +840,7 @@
         df = df.join(indicator_df, how='left')
         if len(df) > before:
             df = df.iloc[:before]
+        # Fill missing global feature columns to avoid KeyError
+        for col in self.GLOBAL_FEATURES:
+            if col not in df.columns:
+                df[col] = 0.0
         df[self.GLOBAL_FEATURES] = df[self.GLOBAL_FEATURES].ffill().fillna(0.0)
         return df
@@ -1803,18 +1806,23 @@
-                        xgb_m = self.models.get(mkt, {}).get(h)
-                        lgb_m = self.lgb_models.get(mkt, {}).get(h)
-                        cat_m = self.cat_models.get(mkt, {}).get(h)
-                        lstm_m = self.lstm_models.get(mkt, {}).get(h)
+                        # Case-insensitive market lookup
+                        mkt_lower = mkt.lower()
+                        mkt_upper = mkt.upper()
+                        xgb_m = self.models.get(mkt_lower, self.models.get(mkt_upper, {})).get(h)
+                        lgb_m = self.lgb_models.get(mkt_lower, self.lgb_models.get(mkt_upper, {})).get(h)
+                        cat_m = self.cat_models.get(mkt_lower, self.cat_models.get(mkt_upper, {})).get(h)
+                        lstm_m = self.lstm_models.get(mkt_lower, self.lstm_models.get(mkt_upper, {})).get(h)
 
                         preds = []
                         weights = []
 
-                        # Get dynamic weights or fallback to default
-                        w_xgb_val = self.ensemble_weights.get("regression", {}).get(mkt, {}).get(str(h), {}).get("xgb", 0.4)
-                        w_lgb_val = self.ensemble_weights.get("regression", {}).get(mkt, {}).get(str(h), {}).get("lgb", 0.3)
-                        w_cat_val = self.ensemble_weights.get("regression", {}).get(mkt, {}).get(str(h), {}).get("cat", 0.3)
-                        w_lstm_val = self.ensemble_weights.get("regression", {}).get(mkt, {}).get(str(h), {}).get("lstm", 0.0)
+                        # Get dynamic weights or fallback to default (checking both case and string/int keys)
+                        mkt_key = mkt_lower if mkt_lower in self.ensemble_weights.get("regression", {}) else mkt_upper
+                        w_xgb_val = self.ensemble_weights.get("regression", {}).get(mkt_key, {}).get(str(h), {}).get("xgb", 0.4)
+                        w_lgb_val = self.ensemble_weights.get("regression", {}).get(mkt_key, {}).get(str(h), {}).get("lgb", 0.3)
+                        w_cat_val = self.ensemble_weights.get("regression", {}).get(mkt_key, {}).get(str(h), {}).get("cat", 0.3)
+                        w_lstm_val = self.ensemble_weights.get("regression", {}).get(mkt_key, {}).get(str(h), {}).get("lstm", 0.0)
 
                         # Convert integer keys back if needed (fix int key bug)
-                        if isinstance(self.ensemble_weights.get("regression", {}).get(mkt, {}), dict):
-                            w_dict = self.ensemble_weights.get("regression", {}).get(mkt, {}).get(h, {})
+                        if isinstance(self.ensemble_weights.get("regression", {}).get(mkt_key, {}), dict):
+                            w_dict = self.ensemble_weights.get("regression", {}).get(mkt_key, {}).get(str(h), {})
+                            if not w_dict:
+                                w_dict = self.ensemble_weights.get("regression", {}).get(mkt_key, {}).get(h, {})
@@ -1867,4 +1875,5 @@
                             res_df.loc[idx, h] = blend_pred_inv
                         else:
+                            logger.warning(f"No regression models found for market '{mkt}' horizon {h}d. Defaulting predictions to 0.0.")
                             res_df.loc[idx, h] = 0.0
@@ -1909,14 +1918,19 @@
-                        xgb_m = self.surge_models.get(mkt, {}).get(h)
-                        lgb_m = self.surge_lgb_models.get(mkt, {}).get(h)
-                        cat_m = self.surge_cat_models.get(mkt, {}).get(h)
+                        # Case-insensitive market lookup
+                        mkt_lower = mkt.lower()
+                        mkt_upper = mkt.upper()
+                        xgb_m = self.surge_models.get(mkt_lower, self.surge_models.get(mkt_upper, {})).get(h)
+                        lgb_m = self.surge_lgb_models.get(mkt_lower, self.surge_lgb_models.get(mkt_upper, {})).get(h)
+                        cat_m = self.surge_cat_models.get(mkt_lower, self.surge_cat_models.get(mkt_upper, {})).get(h)
 
                         preds = []
                         weights = []
 
-                        # Get dynamic weights or fallback to default
-                        w_xgb_val = self.ensemble_weights.get("surge", {}).get(mkt, {}).get(str(h), {}).get("xgb", 0.4)
-                        w_lgb_val = self.ensemble_weights.get("surge", {}).get(mkt, {}).get(str(h), {}).get("lgb", 0.3)
-                        w_cat_val = self.ensemble_weights.get("surge", {}).get(mkt, {}).get(str(h), {}).get("cat", 0.3)
+                        # Get dynamic weights or fallback to default (case-insensitive lookup)
+                        mkt_key = mkt_lower if mkt_lower in self.ensemble_weights.get("surge", {}) else mkt_upper
+                        w_xgb_val = self.ensemble_weights.get("surge", {}).get(mkt_key, {}).get(str(h), {}).get("xgb", 0.4)
+                        w_lgb_val = self.ensemble_weights.get("surge", {}).get(mkt_key, {}).get(str(h), {}).get("lgb", 0.3)
+                        w_cat_val = self.ensemble_weights.get("surge", {}).get(mkt_key, {}).get(str(h), {}).get("cat", 0.3)
 
                         # Convert integer keys back if needed
                         # str(h) key is canonical; int key (h) is in-memory fallback
-                        w_dict = self.ensemble_weights.get("surge", {}).get(mkt, {}).get(str(h), {})
+                        w_dict = self.ensemble_weights.get("surge", {}).get(mkt_key, {}).get(str(h), {})
                         if not w_dict:
-                            w_dict = self.ensemble_weights.get("surge", {}).get(mkt, {}).get(h, {})
+                            w_dict = self.ensemble_weights.get("surge", {}).get(mkt_key, {}).get(h, {})
@@ -1945,6 +1959,7 @@
                             # Apply Platt Scaling calibration if coefficient metadata is present
-                            calib_dict = self.ensemble_weights.get("calibration", {}).get(mkt, {}).get(str(h), {})
+                            mkt_calib_key = mkt_lower if mkt_lower in self.ensemble_weights.get("calibration", {}) else mkt_upper
+                            calib_dict = self.ensemble_weights.get("calibration", {}).get(mkt_calib_key, {}).get(str(h), {})
                             if calib_dict:
                                 coef = calib_dict.get("coef")
@@ -1958,2 +1973,3 @@
                         else:
+                            logger.warning(f"No surge models found for market '{mkt}' horizon {h}d. Defaulting predictions to 0.0.")
                             res_df.loc[idx, col_name] = 0.0
```

### Patch 3: `trading_system/src/ai/vcp_ml_predictor.py`
```diff
@@ -551,9 +551,12 @@
         if not feats:
             return pd.DataFrame()
 
-        feat_cols = list(dict.fromkeys([c for c in self._ft.ALL_FEATURES + VCP_FEATURES if c in feats[0].columns]))
+        feat_cols = list(dict.fromkeys(self._ft.ALL_FEATURES + VCP_FEATURES))
 
         import warnings
         res_df = pd.DataFrame({'symbol': syms, 'market': markets})
         df_all = pd.concat(feats, ignore_index=True)
+        # Ensure all columns in feat_cols exist in df_all to prevent KeyError/dimension mismatch
+        for col in feat_cols:
+            if col not in df_all.columns:
+                df_all[col] = 0.0
@@ -578,14 +581,25 @@
                         preds = []
                         weights = []
 
+                        # Dynamic weights lookup with fallbacks (string/int keys, upper/lower case)
+                        w_dict = self._ft.ensemble_weights.get("vcp_ml", {}).get(mkt_lower, {}).get(str(h), {})
+                        if not w_dict:
+                            w_dict = self._ft.ensemble_weights.get("vcp_ml", {}).get(mkt_upper, {}).get(str(h), {})
+                        if not w_dict:
+                            w_dict = self._ft.ensemble_weights.get("vcp_ml", {}).get(mkt_lower, {}).get(h, {})
+                        if not w_dict:
+                            w_dict = self._ft.ensemble_weights.get("vcp_ml", {}).get(mkt_upper, {}).get(h, {})
+
+                        w_xgb = w_dict.get("xgb", 0.4)
+                        w_lgb = w_dict.get("lgb", 0.3)
+                        w_cat = w_dict.get("cat", 0.3)
+
                         if xgb_m is not None:
                             preds.append(xgb_m.predict_proba(X_mkt)[:, 1])
-                            weights.append(0.4)
+                            weights.append(w_xgb)
                         if lgb_m is not None:
                             preds.append(lgb_m.predict_proba(X_mkt)[:, 1])
-                            weights.append(0.3)
+                            weights.append(w_lgb)
                         if cat_m is not None:
                             preds.append(cat_m.predict_proba(X_mkt)[:, 1])
-                            weights.append(0.3)
+                            weights.append(w_cat)
 
                         if preds:
@@ -610,4 +624,5 @@
                             res_df.loc[idx, col_name] = blend_prob
                         else:
+                            logger.warning(f"No VCP ML models found for market '{mkt}' horizon {h}d. Defaulting predictions to 0.0.")
                             res_df.loc[idx, col_name] = 0.0
```
