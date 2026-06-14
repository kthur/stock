# Milestone 2 Implementation Report — Model Updates

This report details the updates implemented for Milestone 2, which upgrades the price prediction feature set to include normalized stock-level metrics and ensures that both the prediction and macro screener components correctly train and infer with the new 9-feature structure.

## Summary of Changes

### 1. Main Prediction Model Upgrades
**File Modified**: `trading_system/src/ai/prediction_model.py`
- Updated the features list in the `train`, `predict_current`, and `process_and_predict_all` methods to support the 9-feature structure:
  `['ret_1d', 'ret_5d', 'ret_20d', 'ret_60d', 'dist_sma_20', 'vol_20d', 'norm_market_cap', 'norm_floating_value', 'norm_volume']`.
- Updated `_create_features(self, df)` to check if the new normalized features exist in the input DataFrame. If any are missing, it runs `self.apply_market_normalization` on a single-item temporary dictionary for that DataFrame as a robust fallback.
- Updated `prepare_training_data` and `process_and_predict_all` to apply the cross-sectional market normalization using `apply_market_normalization` on the prices dictionary before creating technical indicators and feature matrices.
- Updated `predict_current` to verify if features are computed. If the input is raw prices, it normalizes and generates features dynamically. If features are present but normalized columns are missing, it applies market normalization before predicting, ensuring robust compatibility.

### 2. Stock Screener & Macro Predictor Upgrades
**File Modified**: `trading_system/src/analysis/screener.py`
- Updated `StockScreener.screen_global_outperformers`:
  - Dynamically constructed `us_prices_dict` and `kr_prices_dict` containing the `Close` and `Volume` columns for all stock tickers in the region (US and KR).
  - Automatically applied regional market-level normalization using `OnDevicePredictionModel.apply_market_normalization`.
  - In `train_and_predict_region`, injected `norm_market_cap`, `norm_floating_value`, and `norm_volume` along with their lags (lags 1 through 5) into the pooled feature matrix `X_pool` during training.
  - In prediction phase, dynamically extracted the latest values and historical lags of these features (using `.shift(lag).iloc[-1]` to prevent index errors) and injected them into `ticker_latest` before predicting with `MacroPredictor`.
  - Initialized `df_us` and `df_kr` to empty `pd.DataFrame()` objects prior to the yfinance download try-catch blocks to prevent `UnboundLocalError` in offline/simulated fallback situations.

**File Inspected**: `trading_system/src/analysis/macro_predictor.py`
- Verified that `MacroPredictor` is feature-agnostic, training on all columns present in `X_train` dynamically (via `self.feature_names = list(X.columns)`) and aligning columns correctly for prediction (via `predict_outperformers`), requiring no code modifications.

---

## Verification and Testing

Pytest was executed on the following suites to verify correctness:
1. `tests/test_macro.py`: Passed successfully (5/5).
2. `tests/test_feature_normalization.py` & `tests/test_feature_normalization_stress.py`: Passed successfully (11/11).
3. `tests/test_screener_dash_challenger.py`: Passed successfully (10/10).
4. `tests/test_post_market_scoring.py`: Passed successfully (1/1).
5. `tests/test_system.py`: Passed successfully (55/55).
6. `tests/phase3`: Passed successfully (68 passed, 2 skipped).

All tests passed successfully, confirming the models fit and predict cleanly with the upgraded 9-feature schema.
