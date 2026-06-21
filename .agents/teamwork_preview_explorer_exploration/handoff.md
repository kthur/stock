# Consolidate Codebase Exploration and Integration Plan

## 1. Observation
We analyzed the following codebase files and tests:
- `trading_system/run_pipeline.py`
- `trading_system/src/ai/prediction_model.py`
- `trading_system/src/ai/vcp_ml_predictor.py`
- `trading_system/src/data_layer/earnings_data.py`
- `trading_system/src/config.py`
- `trading_system/src/persistence/database.py`
- Files inside `trading_system/tests/`

We ran the baseline test suite via targeted pytest:
`pytest trading_system/tests/ -v`
The command completed successfully with:
`354 passed, 2 skipped, 35 warnings in 160.49s (0:02:40)`

### A. Feature Mapping (ALL_FEATURES, VCP Features)
1. **ALL_FEATURES** is defined in `trading_system/src/ai/prediction_model.py` (lines 102-116):
   - `FEATURES = ['ret_1d', 'ret_5d', 'ret_20d', 'ret_60d', 'dist_sma_20', 'vol_20d', 'norm_market_cap', 'norm_floating_value', 'norm_volume', 'operating_margin', 'revenue_to_market_cap', 'dividend_yield', 'net_profit_margin', 'eps_yield', 'eps_growth_1y', 'rsi_14', 'rsi_5', 'macd', 'macd_signal', 'macd_hist_norm', 'bb_upper_dist', 'bb_lower_dist', 'bb_width', 'atr_14', 'roc_10', 'roc_20', 'higher_high', 'higher_low', 'distance_from_52w_high']`
   - `GLOBAL_FEATURES = ['vix_change', 'us10y', 'usdkrw_change', 'sp500_change', 'dxy_change', 'wti_change', 'kospi_change', 'kosdaq_change']`
   - `ALL_FEATURES = FEATURES + GLOBAL_FEATURES` (29 base features + 8 global indicators = 37 features).
2. **VCP Features** is defined in `trading_system/src/ai/vcp_ml_predictor.py` (lines 22-28):
   - `VCP_FEATURES = ['range_5v20', 'range_10v20', 'range_20v40', 'range_40v60', 'vol_20v60', 'dist_ma50', 'dist_ma200', 'range_pos_10d', 'range_pos_20d', 'atr_14d_norm', 'monotonic', 'vcp_score']` (12 features).
3. **Where/How computed**:
   - `OnDevicePredictionModel._create_features` (lines 523-647 of `prediction_model.py`) calculates technical/momentum features and merges global indicator history from `indicator_df` by index join.
   - `OnDevicePredictionModel.apply_market_normalization` (lines 290-391 of `prediction_model.py`) normalizes stock features (`market_cap`, `floating_value`, `Volume`) by daily regional total sum. Regional split is defined by `is_kr_symbol` heuristic.
   - `OnDevicePredictionModel.merge_fundamentals` (lines 393-507 of `prediction_model.py`) merges corporate fundamentals (revenue, operating income, net income, EPS, dividends) from `MarketIndicatorStorage` or uses `FALLBACK_METADATA` fallback dict.
   - `VCPSurgePredictor._compute_vcp_features` (lines 76-148 of `vcp_ml_predictor.py`) calculates contraction ranges (rolling peak-to-trough price spread normalised by mean), volume trends (`vol_20v60`), moving average distance, range positions, normalised ATR, monotonic contraction flag, and final VCP score.

### B. Model Lifecycles (Regression, Surge, VCP ML)
1. **Regression Models**:
   - **Trained**: `OnDevicePredictionModel.train` (lines 709-755) trains `xgb.XGBRegressor` on `ALL_FEATURES` for 8 horizons (`[1, 5, 10, 20, 30, 60, 120, 200]`). Splits data: first 80% chronologically for training, last 20% for validation/early stopping.
   - **Saved**: `OnDevicePredictionModel.save_models` (lines 167-177) saves to `models/xgb_model_{market}_{horizon}d.json` using `model.get_booster().save_model()`.
   - **Loaded**: `OnDevicePredictionModel.load_models` (lines 178-219) loads using `xgb.Booster().load_model()`, wraps in `xgb.XGBRegressor`, and manually sets `_estimator_type = 'regressor'`.
   - **Evaluated**: Validation MSE/early stopping during training.
2. **Surge Models**:
   - **Trained**: `OnDevicePredictionModel.train_surge` (lines 756-828) trains `xgb.XGBClassifier` on `ALL_FEATURES` for 4 horizons (`[1, 3, 5, 20]`). Predicts whether forward returns exceed 20% threshold (`self.surge_threshold`).
   - **Saved**: `OnDevicePredictionModel.save_surge_models` (lines 220-230) saves to `models/xgb_surge_model_{market}_{horizon}d.json`.
   - **Loaded**: `OnDevicePredictionModel.load_surge_models` (lines 231-284) wraps loaded booster in `xgb.XGBClassifier`, sets `_estimator_type = 'classifier'`, `n_classes_ = 2`, and `classes_ = np.array([0, 1])`.
   - **Evaluated**: Validation AUC/early stopping.
3. **VCP ML Models**:
   - **Trained**: `VCPSurgePredictor.train` (lines 238-416) generates windowed features by backward sliding (step=20), merges base `ALL_FEATURES` and `VCP_FEATURES`, and trains `xgb.XGBClassifier` per market (KOSPI, KOSDAQ, KONEX, SP500) and horizon (`[1, 3, 5, 20]`).
   - **Saved/Loaded**: `save_models` / `load_models` (lines 452-486) saves to `models/vcp_surge_{market}_{horizon}d.json` and loads booster files similarly.

### C. External API Calls and Rate Limiting
1. **`trading_system/run_pipeline.py`**:
   - `fetch_data_fdr` (lines 55-134): Calls `fdr.DataReader(symbol, start=start_date)` for SP500 / fallbacks, and `yf.download(yf_symbol, ...)` for Korean markets.
   - `fetch_indicator_history` (lines 149-206): Calls `yf.download(ticker, ...)` for global indicators.
   - `_get_excluded_krx_symbols` (lines 257-285): Calls `fdr.StockListing('KRX')` and `fdr.StockListing('KRX-ADMINISTRATIVE')`.
2. **`trading_system/src/data_layer/earnings_data.py`**:
   - `fetch_fundamentals` (lines 26-95): Calls `yf.Ticker(yf_sym).financials` and `ticker.info`.
3. **Current Rate Limiting**:
   - `run_pipeline.py` has a global thread lock `_rate_lock` and `update_interval` sleep logic.
   - `earnings_data.py` catches rate limits and retries with exponential backoff (`wait = 2 ** attempt`).

## 2. Logic Chain
To add new features (LightGBM, CatBoost, Optuna, rate limiting/retry decoration, and R1/R2/R3 enhancements), we can structure the integration points as follows:

### A. Integration Point for LightGBM and CatBoost
- **Location**: `OnDevicePredictionModel` and `VCPSurgePredictor`.
- **Implementation**:
  - We will introduce `self.lgb_models` and `self.cat_models` dictionaries alongside `self.models` (for regression) and `self.lgb_surge_models` / `self.cat_surge_models` alongside `self.surge_models`.
  - In `train` and `train_surge`, fit `LGBMRegressor`/`LGBMClassifier` and `CatBoostRegressor`/`CatBoostClassifier`.
  - In `save_models` and `load_models`, save/load these models (LightGBM booster file using `model.booster_.save_model(path)` and CatBoost using `model.save_model(path, format="json")` or pickle/joblib).
  - Create a blending method `_ensemble_predict` to aggregate predictions:
    `final_prediction = 0.4 * xgb_pred + 0.3 * lgb_pred + 0.3 * cat_pred`.

### B. Optuna Hyperparameter Tuning Integration
- **Location**: A new module `trading_system/src/ai/hyperparameter_tuner.py` or addition to `OnDevicePredictionModel`.
- **Implementation**:
  - Introduce a method `tune_hyperparameters(df_train, market, model_type, horizon)` that runs an Optuna study.
  - Define search spaces (e.g. `n_estimators`, `max_depth`, `learning_rate` for all three models; `num_leaves` for LightGBM; `depth` and `l2_leaf_reg` for CatBoost).
  - Train on chronological 80% split and validate on last 20% to compute RMSE (regression) or LogLoss/AUC (classification).
  - Store tuned parameters in a JSON file `trading_system/models/tuned_params.json` to prevent running expensive tuning runs during daily pipeline execution.

### C. Rate Limiting and Retry Decoration
- **Location**: Wrap `fdr.DataReader`, `yf.download`, `yf.Ticker` operations in a custom decorator or Tenacity retry scheme.
- **Decorator**:
  ```python
  from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
  
  @retry(
      stop=stop_after_attempt(5),
      wait=wait_exponential(multiplier=1, min=2, max=30),
      retry=retry_if_exception_type((Exception)), # Catch timeout and connection issues
      reraise=True
  )
  def fetch_api_with_retry_and_limit(*args, **kwargs):
      # call yfinance or fdr with a global lock-regulated delay
  ```

### D. R1, R2, and R3 Concrete Implementation Plan
1. **R1 (Post-Market Scoring + Dashboard)**:
   - Ensure the post-market scoring script `scripts/post_market_scoring.py` runs inside `run_pipeline.py` or the orchestrator.
   - Extend the composite score formula (`composite_score = 0.4 * tech_score + 0.4 * ai_score + 0.2 * sentiment_score`) to include a VCP pattern check multiplier or weight (e.g. `+0.1` boost if VCP pattern is detected).
   - Render the top 20 ranked stocks dynamically in the dashboard HTML.
2. **R2 (Market-cap/Volume/Floating-shares Feature Engineering)**:
   - Enhance the regional classification in `apply_market_normalization`. Currently, it only separates US vs. KR. We should separate by exact markets (KOSPI, KOSDAQ, KONEX, SP500) to avoid KONEX micro-caps distorting the KR baseline total.
3. **R3 (Corporate Fundamentals + 12-Feature Model)**:
   - Build a robust quarterly fundamentals aligner in `merge_fundamentals` to supplement fiscal year data.
   - Refine the YoY growth formulas (`eps_growth_1y`, `revenue_growth_1y`) to handle missing data points cleanly and assert a strict minimum history validation.

## 3. Caveats
- Baseline test results are based on the offline SQLite cache state since we are in code-only mode.
- We assume that `lightgbm` and `catboost` packages can be added to the `.venv` using pip without library conflicts.
- Rate limits of Yahoo Finance are volatile; aggressive multi-threaded querying can cause temporary IP blocks even with retries/delays.

## 4. Conclusion
The trading system has a well-structured pipeline using SQLite caching, background fundamentals fetching, and parallel model training. We can seamlessly integrate LightGBM and CatBoost by creating wrapper models, storing best parameters via Optuna studies, and safeguarding network calls using Tenacity retry decorators.

## 5. Verification Method
- **Test execution**: Run `.venv\Scripts\pytest trading_system\tests/ -v` to ensure no regressions are introduced.
- **Model checkpoints**: Verify files `xgb_model_*.json`, `lgb_model_*.txt`, and `cat_model_*.bin` exist in the `models/` directory after pipeline training.
- **Database logs**: Inspect SQLite tables `ai_predictions` and `post_market_rankings` to verify new features and ensemble scores are recorded correctly.
