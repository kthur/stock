# Handoff Report — Explorer Quality Fixes 3

## 1. Observation
* **Mismatched Cache Keys:**
  In `.github/workflows/training.yml` (line 66):
  `key: ai-models-v2-${{ steps.date.outputs.date }}-${{ matrix.target }}`
  In `.github/workflows/pipeline.yml` (line 69):
  `key: ai-models-v2-${{ matrix.target }}-${{ steps.date.outputs.date }}`
* **Default probability for missing models:**
  In `trading_system/src/ai/prediction_model.py` (line 2005):
  `res_df.loc[idx, col_name] = 0.0`
  `logger.warning(f"Surge prediction for market={mkt}, horizon={h} defaulted to 0.0 due to missing models.")`
* **Lead-Lag Leader Selection:**
  In `trading_system/src/ai/prediction_model.py` (lines 2083-2085):
  `cap_col = 'market_cap' if 'market_cap' in df_train.columns else 'norm_market_cap'`
  `avg_caps = df_train.groupby('symbol')[cap_col].mean()`
  `top_50_leaders = avg_caps.nlargest(50).index.tolist()`
* **Conditional Output File Saving:**
  In `trading_system/run_pipeline.py` (line 1217, 1259, 1308, 1341):
  `if not surge_df.empty: ...`
  `if not lead_lag_df.empty: ...`
  `if vcp_results: ...`
  `if not vcp_ml_df.empty: ...`

## 2. Logic Chain
* **Bugs 1 & 3 (Surge and VCP ML Empty):**
  1. Mismatched GHA cache keys result in failure to restore the `/home/runner/work/stock/stock/trading_system/models` directory.
  2. Because models are missing on start, the pipeline triggers on-the-fly training.
  3. On-the-fly training tries to fetch all universe symbols from 2006, hitting yfinance rate limits and resulting in an empty training dataset.
  4. With no models trained/restored, the predictions default to `0.0` (surge) or return empty (VCP ML).
* **Bug 2 (Lead-Lag KRX Missing):**
  1. `compute_lead_lag` selects the global top 50 leaders by raw market cap or normalized market cap.
  2. Without currency conversion, KRX raw market caps dominate SP500, but if normalized, smaller markets like KOSDAQ and KONEX are completely shut out of the top 50 leaders.
  3. During KOSDAQ or KONEX runs, the prediction data has no leaders to trigger follow-on correlation returns, leading to missing lead-lag predictions.
* **Bug 4 (Ensemble 0%):**
  1. Since all inputs to the ensemble (regression, surge, lead-lag, VCP ML) default to 0.0, the weighted sum is 0.0, which maps to `0.0%` expected returns.
* **Bug 5 (Output File Placeholders):**
  1. Conditional file writing skips creating files when predictions are empty.
  2. The missing files cause GHA pipeline steps to fail or produce warnings.
  3. Always writing placeholder files when empty resolves the pipeline fragility.

## 3. Caveats
* The GHA workflow files and source code were analyzed using read-only inspection.
* No code execution or training was performed locally as part of this analysis task, in accordance with the read-only scope constraint.

## 4. Conclusion
* Bug 1 and Bug 3 will be solved by updating `training.yml` to use the same cache key format as `pipeline.yml`.
* Bug 2 will be solved by grouping the training data by market and selecting a target number of leaders per market segment.
* Bug 4 will be resolved as a consequence of fixing Bugs 1-3.
* Bug 5 will be resolved by refactoring the file-saving blocks in `run_pipeline.py` to always write files with placeholder messages if empty.

## 5. Verification Method
* **Independent Verification Command:**
  Run the test suite to confirm no existing functionality is broken:
  ```bash
  .venv/bin/pytest tests/ -v
  ```
* **Verify Cache Key Change:**
  Inspect `.github/workflows/training.yml` and `.github/workflows/pipeline.yml` to confirm cache key definitions match.
* **Verify Lead-Lag Leader Selection:**
  Trigger model training with the modified `compute_lead_lag` code and verify that `lead_lag_matrix.json` contains leaders from all active markets.
* **Verify Output Placeholders:**
  Run the pipeline with empty prediction inputs (e.g. debug mode with a new/empty DB) and confirm that all files (e.g., `surge_predictions.txt`) are created and contain placeholder messages instead of being absent.
