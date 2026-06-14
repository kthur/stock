# Handoff Report — explorer_fundamental_1

This report summarizes the codebase investigation and the proposed integration strategy for incorporating fundamental stock data and calculated features into the system.

## 1. Observation
We observed the following exact file paths and code structures:
- **Database Path**: `src/config.py:24` defines the database path `db_path: str = os.getenv("DB_PATH", "market_indicators.db")`.
- **Database Tables**: `src/data_layer/indicator_storage.py:14-59` in `MarketIndicatorStorage._init_db()` defines and creates tables for the system: `global_indicators`, `stock_universe`, `ai_predictions`, and `post_market_rankings`.
- **Testing Fallback Mechanism**: `src/ai/prediction_model.py:17-80` defines `FallbackMetadataDict` and `FALLBACK_METADATA`, which generate deterministic mock `shares_outstanding` and `floating_shares` based on symbol MD5 hash in `_generate_mock_metadata` (lines 68-77).
- **Feature Engineering and XGBoost Model**: `src/ai/prediction_model.py:83` defines `OnDevicePredictionModel` which uses a hardcoded list of 9 features (lines 236, 270, 288):
  `features = ['ret_1d', 'ret_5d', 'ret_20d', 'ret_60d', 'dist_sma_20', 'vol_20d', 'norm_market_cap', 'norm_floating_value', 'norm_volume']`
  It calculates technical indicators in `_create_features` (lines 176-204) and targets in `_create_targets` (lines 205-210).
- **Consolidated Pipeline**: `run_pipeline.py:121-127` instantiates `OnDevicePredictionModel`, calls `prepare_training_data`, and trains XGBoost regressors for each forecast horizon (`[1, 5, 10, 20, 30, 60, 120, 200]`).
- **Post-Market Scoring**: `scripts/post_market_scoring.py:160` instantiates `OnDevicePredictionModel` and uses it to predict expected returns for the 20-day horizon (lines 252-257).
- **Strategy Engine**: `src/core/strategy_engine.py` defines `HybridStrategyEngine` (line 86) which uses `ml_engine` (an instance of `MLEngine` from `src/analysis/ml_engine.py` predicting binary up/down probabilities, lines 425-431) for trade signals.
- **Tests**:
  - `tests/test_feature_normalization.py` and `tests/test_feature_normalization_stress.py` verify that `OnDevicePredictionModel.apply_market_normalization` and `FallbackMetadataDict` function correctly.
  - `tests/test_post_market_scoring.py` tests `post_market_scoring.py`'s scoring script.
- **Baseline Test Execution**: Running the test suite (`.venv\Scripts\pytest`) in `d:\Finance\code\stock\trading_system` resulted in:
  `====== 1 failed, 328 passed, 2 skipped, 4 warnings in 182.55s (0:03:02) =======`
  The single failure is:
  `FAILED tests/phase3/e2e/test_e2e.py::test_report_overwrite - OSError: [Errno 22] Invalid argument: './test_report_overwrite.pdf'`

## 2. Logic Chain
- **Database Schema**: To store fundamentals (revenue, operating income, dividend per share), we need a persistent table. Since all SQLite tables are initialized in `MarketIndicatorStorage._init_db()`, we should define the `stock_fundamentals` table there and add save/retrieve helper APIs.
- **API Fetching and Testing Fallbacks**: Real fundamentals can be retrieved via `yfinance`'s `.info` or `.financials`. For offline unit tests, the system relies on `FallbackMetadataDict`. Therefore, we must add mock definitions for the new fundamental fields in `FallbackMetadataDict` benchmarks and the dynamic hash generator `_generate_mock_metadata` to prevent test failures in strict network isolation.
- **Feature Engineering**: Calculating the three new features requires `revenue`, `operating_income`, and `dividend_per_share`. In `OnDevicePredictionModel.apply_market_normalization`, we can merge these fundamental columns into the input DataFrame (either from the database or falling back to `FallbackMetadataDict` if missing). This ensures that `_create_features` has access to these columns and can cleanly compute `operating_margin`, `revenue_to_market_cap`, and `dividend_yield`.
- **Model Training and Predictors**: Changing `OnDevicePredictionModel` features list to 12 features will automatically expand the inputs used by XGBoost. The training pipeline in `run_pipeline.py` and `scripts/predict_best_stock.py` will automatically train models on 12 features. `MacroPredictor` is not affected because it predicts based on macro factors rather than stock-specific features.
- **Post-Market Scoring & Strategy Engine**: `post_market_scoring.py` must load the new fundamental columns from the database (using `get_fundamentals`) and merge them into each stock's prices DataFrame before calling the prediction model. This guarantees that real fundamentals are used in live scoring. `HybridStrategyEngine` consumes these predictions through the rankings table in the database.
- **Verification**: Updating the feature schema changes the expected inputs for `OnDevicePredictionModel`. Thus, the test suites in `tests/test_feature_normalization.py` and `tests/test_post_market_scoring.py` must be updated to mock/assert the 12 features.

## 3. Caveats
- We assume that `yfinance` API will reliably expose financials/info for all US tickers in production. For Korean stocks, we assume that either `yfinance` (using `.KS` or `.KQ` suffixes) or a custom handler will supply the fundamentals, with `FallbackMetadataDict` serving as a fallback.
- No actual code changes have been implemented on the codebase (only analysis files written to `.agents/explorer_fundamental_1/`), in accordance with the read-only constraint.
- The single test failure (`test_report_overwrite`) is a pre-existing environment-specific issue (likely related to file handles/locks or reportlab under Windows) and is unrelated to the fundamental data integration.

## 4. Conclusion
The proposed detailed design covers all required modifications. It leverages the existing decoupled structure of the pipeline by merging fundamentals into the DataFrames before normalization. This ensures compatibility with both real database-provided data and deterministic mock fallbacks for offline testing.

## 5. Verification Method
- **Analysis File Inspection**: Verify that the detailed design report is located at `d:\Finance\code\stock\.agents\explorer_fundamental_1\analysis.md`.
- **Pre-existing Tests Execution**: Execute pytest to ensure that the current test suite passes (with only the pre-existing `test_report_overwrite` failing):
  ```powershell
  .venv\Scripts\pytest
  ```
- **New Test Cases**: Future implementers should create `tests/test_fundamentals_features.py` to test the new 12-feature schema and database operations, and run it using:
  ```powershell
  .venv\Scripts\pytest trading_system/tests/test_fundamentals_features.py
  ```
