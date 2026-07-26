# Handoff Report — Strategy Output Quality Bugs

## 1. Observation
- **GHA Cache Keys**:
  - In `.github/workflows/pipeline.yml` (line 69):
    ```yaml
    key: ai-models-v2-${{ matrix.target }}-${{ steps.date.outputs.date }}
    ```
  - In `.github/workflows/training.yml` (line 66):
    ```yaml
    key: ai-models-v2-${{ steps.date.outputs.date }}-${{ matrix.target }}
    ```
- **Fallback Markets**:
  - In `trading_system/src/ai/prediction_model.py` (line 578):
    ```python
    for market in ['sp500', 'krx']:
    ```
- **Lead-Lag Selection**:
  - In `trading_system/src/ai/prediction_model.py` (lines 2083-2085):
    ```python
    cap_col = 'market_cap' if 'market_cap' in df_train.columns else 'norm_market_cap'
    avg_caps = df_train.groupby('symbol')[cap_col].mean()
    top_50_leaders = avg_caps.nlargest(50).index.tolist()
    ```
- **Lead-Lag Threshold**:
  - In `trading_system/src/ai/prediction_model.py` (line 2199):
    ```python
    if leader_ret <= 0.01:
        continue
    ```
- **VCP ML Check**:
  - In `trading_system/src/ai/vcp_ml_predictor.py` (lines 487-489):
    ```python
    if not self.models:
        logger.warning("No VCP ML models loaded, skipping prediction")
        return pd.DataFrame()
    ```

## 2. Logic Chain
1. **Cache Key Mismatch**: The cache key in `pipeline.yml` differs from `training.yml`. This causes cache restore to fail on daily inference, leaving `trading_system/models/` empty.
2. **Missing models**: Because models are missing and loader check only checks `sp500` and `krx`, target-specific models (`kospi`, `kosdaq`, `konex`) are skipped. Thus, no models are loaded, and prediction defaults to `0.0`.
3. **KRX Lead-Lag Missing**: Because `market_cap` is scale-biased (USD vs KRW), consolidated training cannot select representative leaders. Also, there is no `market` column in `df_train`, so leader selection cannot be done per market. Lastly, the daily return threshold `leader_ret <= 0.01` is too high for indices (like `^KS11` and `^KQ11`), filtering out index leaders and leaving followers with zero score.
4. **VCP ML Empty**: The cache restore failure leaves models empty. Furthermore, checking only `self.models` (XGBoost) prevents using LightGBM or CatBoost models even if they are successfully loaded.
5. **Cascading Ensemble Score**: Since Surge, Lead-Lag, and VCP ML are 0.0/empty, the ensemble score is biased towards 0% for KRX markets.
6. **Missing file placeholders**: Writing logic only triggers when dataframes are not empty, leaving files empty or missing when no prediction is generated.

## 3. Caveats
- We did not execute the full pipeline network fetches because we are in read-only investigation mode and CODE_ONLY network mode.
- We assume that the database standardizes the `market` tag case (e.g. `KOSPI` in uppercase for universe data and `kospi` in lowercase for model filenames), which matches what we observed in the models folder.

## 4. Conclusion
The strategy output quality bugs are caused by (a) GHA cache key mismatches, (b) fallback market checking lists in model loaders failing to handle sub-markets, (c) scale-bias and excessive filtering thresholds in lead-lag leader selection/prediction, (d) overly restrictive empty checks in the VCP ML predictor, and (e) missing default file writing fallbacks for empty datasets. Implementing the proposed fixes in workflows, prediction model loader/predictors, and file outputs will resolve the issues.

## 5. Verification Method
- **Test Command**: `.venv\Scripts\python.exe -m pytest trading_system/tests/` (specifically `trading_system/tests/test_lead_lag_index.py`).
- **File Inspection**: Verify `analysis.md` exists and contains correct Before/After code snippets.
- **Merge script check**: Run `merge_predictions.py` and verify it writes placeholders for empty results.
