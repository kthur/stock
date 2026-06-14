## 2026-06-12T19:32:53+09:00
You are teamwork_preview_worker. Your mission is to implement fundamental data (Revenue, Operating Income, Dividends) and fundamental-based features (operating_margin, revenue_to_market_cap, dividend_yield) into the stock prediction models, pipelines, strategy engine, database schemas, and documentation.

Your workspace directory is d:\Finance\code\stock.
Please write your coordination files to:
- Progress heartbeat: d:\Finance\code\stock\.agents\worker_fundamental_1\progress.md
- Handoff report: d:\Finance\code\stock\.agents\worker_fundamental_1\handoff.md

Follow the design proposals located in:
1. d:\Finance\code\stock\.agents\explorer_fundamental_2\analysis.md
2. d:\Finance\code\stock\.agents\explorer_fundamental_3\analysis.md

Detailed Implementation Steps:
1. Baseline Test Run: Run the existing test suite first to ensure you have a clean starting point.
2. Database Schema: Create table `stock_fundamentals` (symbol TEXT, date TEXT, revenue REAL, operating_income REAL, dividend_per_share REAL, PRIMARY KEY (symbol, date)) in `_init_db` of `trading_system/src/data_layer/indicator_storage.py`. Add methods `save_fundamentals(df_fundamentals)` and `get_fundamentals(symbol)`.
3. Offline Fallbacks: Update `FallbackMetadataDict` and `_generate_mock_metadata` in `trading_system/src/ai/prediction_model.py` to include deterministic mock values for `revenue`, `operating_income`, and `dividend_per_share`.
4. Feature Engineering: Update `OnDevicePredictionModel._create_features` to merge the fundamental columns (using forward-filling `ffill().fillna(0.0)`) and calculate the three new features:
   - `operating_margin` = operating_income / revenue
   - `revenue_to_market_cap` = revenue / market_cap
   - `dividend_yield` = dividend_per_share / Close
   Ensure division-by-zero protection (e.g., using `replace(0.0, np.nan)` or a safe divide function).
5. Model Upgrade: Expand the feature list from 9 features to 12 features in:
   - `OnDevicePredictionModel.train`
   - `OnDevicePredictionModel.predict_current`
   - `OnDevicePredictionModel.process_and_predict_all`
6. Pipeline Updates: Ensure `run_pipeline.py` and `scripts/post_market_scoring.py` fetch/generate mock fundamental data and merge it correctly into the price DataFrames before feature generation and predictions are run. Ensure `generate_simulated_prices` inside `post_market_scoring.py` returns mock fundamental columns.
7. Documentation: Add a description of the 12-feature model and `stock_fundamentals` database table to `trading_system/docs/SYSTEM_ARCHITECTURE.md`.
8. Tests Update: Update tests in:
   - `tests/test_database.py` (add unit tests for `save_fundamentals` and `get_fundamentals`)
   - `tests/test_feature_normalization.py` (verify mock fundamentals are parsed and features are generated)
   - `tests/test_feature_normalization_stress.py` (test edge cases like zero revenue, division by zero, missing records, inf, NaN)
   - `tests/test_post_market_scoring.py` (ensure mock dataframes contain mock fundamental columns)
9. Verification: Run the test suite and verify that all tests pass.

⚠️ MANDATORY INTEGRITY WARNING — include this verbatim in your implementation:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

When completed, write progress.md and handoff.md, and send a message with the results.
