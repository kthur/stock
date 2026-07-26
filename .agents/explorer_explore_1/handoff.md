# Handoff Report — explorer_explore_1

## 1. Observation

- **GitHub Actions (GHA) Workflows**:
  - Path: `d:\Finance\code\stock\.github\workflows\pipeline.yml`
    - Line 68: `key: ai-models-v2` (Static cache key)
    - Line 88: `SKIP_TRAINING: ${{ steps.models-cache.outputs.cache-hit == 'true' && 'True' || 'False' }}`
  - Path: `d:\Finance\code\stock\.github\workflows\training.yml`
    - Line 64: `key: ai-models-v2` (Static cache key)
  - Path: `d:\Finance\code\stock\trading_system\run_pipeline.py`
    - Line 558-560:
      ```python
              else:
                  logger.warning("Missing or incomplete pre-trained models on disk but SKIP_TRAINING is requested. Skipping model training phase anyway.")
                  should_skip = True
      ```

- **Prediction Model**:
  - Path: `d:\Finance\code\stock\trading_system\src\ai\prediction_model.py`
    - Lines 1806-1809:
      ```python
                              xgb_m = self.models.get(mkt, {}).get(h)
                              lgb_m = self.lgb_models.get(mkt, {}).get(h)
                              cat_m = self.cat_models.get(mkt, {}).get(h)
      ```
    - Lines 1821-1822:
      ```python
                              if isinstance(self.ensemble_weights.get("regression", {}).get(mkt, {}), dict):
                                  w_dict = self.ensemble_weights.get("regression", {}).get(mkt, {}).get(h, {})
      ```
    - Line 1871: `res_df.loc[idx, h] = 0.0`
    - Line 1959: `res_df.loc[idx, col_name] = 0.0`
    - Line 843: `df[self.GLOBAL_FEATURES] = df[self.GLOBAL_FEATURES].ffill().fillna(0.0)`

- **VCP ML Predictor**:
  - Path: `d:\Finance\code\stock\trading_system\src\ai\vcp_ml_predictor.py`
    - Lines 581-589:
      ```python
                              if xgb_m is not None:
                                  preds.append(xgb_m.predict_proba(X_mkt)[:, 1])
                                  weights.append(0.4)
                              if lgb_m is not None:
                                  preds.append(lgb_m.predict_proba(X_mkt)[:, 1])
                                  weights.append(0.3)
      ```
    - Line 612: `res_df.loc[idx, col_name] = 0.0`
    - Line 554: `feat_cols = list(dict.fromkeys([c for c in self._ft.ALL_FEATURES + VCP_FEATURES if c in feats[0].columns]))`

- **Verification Run**:
  - Command: `.venv\Scripts\pytest trading_system\tests\test_ensemble_lgb_cat.py -v`
  - Output: `4 passed, 16 warnings in 68.38s` (Successful run of all 4 test cases)

---

## 2. Logic Chain

1. **GHA Cache Mismatches**:
   - Because the AI model cache key is `ai-models-v2` in both `pipeline.yml` and `training.yml`, it is static.
   - GHA caches are immutable. The first workflow run will create `ai-models-v2` cache. Subsequent runs (both daily pipelines and weekly trainings) will fail to update/save the cache key because it already exists.
   - This means weekly training builds never actually cache the new models, and daily runs restore outdated models.
   - Furthermore, `SKIP_TRAINING` in `pipeline.yml` checks if the cache was hit (`true`), which it always will be. Thus daily pipelines will always skip training, even when models are stale.
   - In `run_pipeline.py`, the fallback when `skip_training` is true but models are missing still sets `should_skip = True`, leading to silent empty predictions instead of training.

2. **Key Type & Casing Mismatch in `prediction_model.py`**:
   - Market names loaded from model files are lowercased (e.g. `sp500`, `kospi`), but `mkt` passed to `_predict_regression()` and `_predict_surge()` is lowercase/uppercase depending on setup. If uppercase, lookups fail.
   - For ensemble weights, `h` is checked as an integer: `.get(h, {})`. In JSON, all keys are strings (e.g. `"5"`). Thus, `w_dict` resolves to `{}` and fallback weights of `0.4/0.3/0.3` are always used.
   - If models are missing, the predictions default to `0.0` silently with no warning.

3. **VCP ML Lookup & Platt Scaling**:
   - The ensemble weights for VCP ML models in `vcp_ml_predictor.py` are hardcoded as `0.4/0.3/0.3` rather than looked up dynamically from `ensemble_weights.json`.
   - VCP ML prediction defaults to `0.0` silently on failure.
   - Feature columns list (`feat_cols`) is dynamically sliced, risking shape mismatch when some features are missing in inference data.

4. **Missing Global Indicators Handling**:
   - In `_merge_indicator_history`, if any indicator fails to download, its column is not added to the joined dataframe.
   - Subsequently, `df[self.GLOBAL_FEATURES]` raises `KeyError` due to missing columns, crash-terminating the entire pipeline.

5. **Missing Outputs Verification**:
   - There is currently no check inside `run_pipeline.py` to see if output files are empty or if they contain all `0.0` predictions, making debugging model loading failures hard.

---

## 3. Caveats

- We assumed that the market keys in `self.ensemble_weights` follow the casing of model file name outputs (mostly lowercase or handled case-insensitively).
- The weekly training pipeline runs once a week. Changing the cache keys to include the date will create a new cache for each weekly training, which will be consumed by the daily runs.

---

## 4. Conclusion

The investigated bugs/discrepancies are:
- GHA workflow cache key is static, preventing cache updates and keeping stale models.
- `SKIP_TRAINING` fallback in `run_pipeline.py` skips training even when models are missing.
- Integer keys lookup bug in `prediction_model.py` prevents custom regression weights from being loaded.
- Casing mismatch in model loading key lookups causes silent `0.0` prediction defaults.
- Hardcoded VCP ML weights prevent dynamic ensemble weights from being utilized.
- Global indicator joining lacks missing columns validation, leading to crash-level `KeyError`.
- No warnings are raised for empty outputs or all `0.0` predictions.

All details and exact proposed code diff patches are stored in `d:\Finance\code\stock\.agents\explorer_explore_1\analysis.md`.

---

## 5. Verification Method

To verify the proposed fixes:
1. Ensure unit tests pass using:
   ```bash
   .venv\Scripts\pytest trading_system/tests/test_ensemble_lgb_cat.py -v
   ```
2. Inspect the proposed diff patches in `analysis.md` to ensure correct case handling and dynamic weights lookup.
3. Validate that `run_pipeline.py` warning checks are triggered on empty predictions/missing models.
