# Handoff Report — Quality Fixes Analysis

## 1. Observation
We observed the following in the repository:
1. **Cache Key Mismatch**:
   - In `.github/workflows/pipeline.yml` line 69:
     `key: ai-models-v2-${{ matrix.target }}-${{ steps.date.outputs.date }}`
   - In `.github/workflows/training.yml` line 66:
     `key: ai-models-v2-${{ steps.date.outputs.date }}-${{ matrix.target }}`
2. **Fallback Load Check**:
   - In `trading_system/src/ai/prediction_model.py` lines 440-441 and 577-578, the fallback loop is:
     `for market in ['sp500', 'krx']:`
3. **Leader Selection**:
   - In `trading_system/src/ai/prediction_model.py` lines 2083-2085:
     ```python
     cap_col = 'market_cap' if 'market_cap' in df_train.columns else 'norm_market_cap'
     avg_caps = df_train.groupby('symbol')[cap_col].mean()
     top_50_leaders = avg_caps.nlargest(50).index.tolist()
     ```
4. **VCP ML Initialization**:
   - In `trading_system/run_pipeline.py` line 713 and 926, it is instantiated as:
     `vcp_ml = VCPSurgePredictor()` without passing `model_dir`.
5. **Missing Placeholders**:
   - In `trading_system/run_pipeline.py` lines 1217, 1259, 1308, 1341, file writing steps are wrapped in conditional checks like `if not surge_df.empty:` and `if vcp_results:` and `if not vcp_ml_df.empty:`.

---

## 2. Logic Chain
1. **Cache Key & Fallback (Bug 1 & 3)**:
   - The reversed date and target variables in GHA cache keys mean the daily run fails to match and restore the models from the training run cache.
   - The models folder `trading_system/models` is empty. Because `SKIP_TRAINING` is active, it skips training and attempts fallback load.
   - The fallback check in `prediction_model.py` searches for `xgb_surge_model_krx_1d.json`, which does not exist because models are saved per-market (`kospi`, etc.). Thus, no models are loaded.
   - For Surge, this defaults predictions to `0.0`. For VCP ML, it skips predictions and returns an empty DataFrame, leaving `vcp_ml_predictions.txt` missing.
2. **Lead-Lag Selection (Bug 2)**:
   - Selecting the top 50 leaders globally using `norm_market_cap` causes SP500 to dominate the list (since SP500 has many large companies, while KRX has over 2800 symbols where Samsung Electronics is dominant and others are tiny).
   - This leaves KRX markets with no leader stocks selected, meaning `predict_lead_lag()` cannot compute follower scores for KRX, resulting in empty predictions.
3. **Ensemble & Output (Bug 4 & 5)**:
   - Since the strategy outputs are empty or `0.0`, the ensemble score evaluates to `0.0` (`0.0%`).
   - If strategy output dataframes are empty, the corresponding files are not written, which causes merge and upload failures in GHA steps.

---

## 3. Caveats
- We assumed that `stock_prices.db` and `market_indicators.db` are successfully populated and cached. If these DBs are corrupted, the pipeline will fail regardless of model fixes.
- Verification commands assume a working Python environment setup via `.venv` and a Windows OS for local execution.

---

## 4. Conclusion
The pipeline output quality bugs are caused by a GHA cache key mismatch, incorrect fallback loading targets, global leader cap-ranking imbalance, and directory path drift. Aligning the GHA cache keys, partitioning the leader selection, passing the model path explicitly, and adding empty output placeholders will restore full strategy predictions for all markets.

---

## 5. Verification Method
1. **Align GHA Cache Keys**: Verify that `.github/workflows/training.yml` and `.github/workflows/pipeline.yml` use matching keys.
2. **Execute Tests**:
   - Run unit tests locally using the virtual environment:
     `.\.venv\Scripts\pytest trading_system/tests/test_lead_lag_index.py -v`
3. **Inspect Output Files**:
   - Run the prediction pipeline locally or check GHA runs:
     `.\.venv\Scripts\python trading_system/run_pipeline.py`
   - Check that `surge_predictions.txt`, `lead_lag_predictions.txt`, `vcp_ml_predictions.txt`, and `vcp_patterns.txt` are generated with correct header metadata and predictions/placeholders.
