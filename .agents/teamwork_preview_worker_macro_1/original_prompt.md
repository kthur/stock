## 2026-06-07T20:14:50Z

You are teamwork_preview_worker. Your working directory is d:\Finance\code\stock\.agents\teamwork_preview_worker_macro_1\.
Please implement the Global Macro enhancements (R1-R4) in d:\Finance\code\stock\trading_system.

Here is the implementation plan based on Explorers' investigations:

1. Dependency Sync:
   - Check requirements.txt and pyproject.toml. Update pyproject.toml to include any missing dependencies (such as pandas, scikit-learn, pyarrow, finance-datareader, etc.) under the [project] section dependencies.

2. R1. Global Macro Correlation Engine:
   - Create a module `src/analysis/macro_analyzer.py`.
   - Implement `calculate_cross_correlation(indices_data: pd.DataFrame, lags: int = 5) -> pd.DataFrame` (or similar signature).
   - This should align timezone-mismatched indices, forward-fill missing values, calculate percentage returns, and compute Pearson cross-correlation with lags (0 to 5 days) for:
     - S&P 500 (^GSPC), Nasdaq (^IXIC), KOSPI (^KS11), KOSDAQ (^KQ11), USDKRW=X, ^TNX, and ^VIX.
   - Design robust fallback data simulation logic if yfinance data cannot be retrieved (e.g. in offline network mode).

3. R2. ML Predictor Model:
   - Create a module `src/analysis/macro_predictor.py`.
   - Implement `MacroPredictor` class containing:
     - `train_model(features, targets) -> Dict`: Trains a RandomForestRegressor (or other sklearn regressor) to predict stock excess returns over local benchmark (S&P 500 for US, KOSPI for KR). Hyperparameters should control tree depth to prevent overfitting. Returns evaluation metrics (MSE, R2 Score).
     - `predict_outperformers(features) -> pd.Series`: Predicts expected excess returns.
     - Caching: Save evaluation metrics and analysis results to `data/macro_model_metrics.json` in a clean JSON format.
   - Design robust fallback data simulation logic if yfinance data cannot be retrieved (e.g. in offline network mode).

4. R3. Global Outperformer Screener:
   - Extend `StockScreener` class in `src/analysis/screener.py` with:
     - `screen_global_outperformers() -> Dict[str, List[Dict]]`
   - Define a subset of top major constituent tickers for US (S&P 500) and KR (KOSPI 200).
   - Fetch historical data for all stocks, calculate return-based Pearson correlation with `USDKRW=X`, build lagged features, run the trained `MacroPredictor` to predict excess returns, and select the top 10 US and top 10 KR stocks descending by expected excess return.
   - Return format:
     ```python
     {
         "US": [{"ticker": "AAPL", "expected_excess_return": float, "correlation_to_exchange_rate": float}, ...],
         "KR": [{"ticker": "005930.KS", "expected_excess_return": float, "correlation_to_exchange_rate": float}, ...]
     }
     ```
     (exactly 10 items for each region).
   - Ensure the method does not crash if yfinance returns empty data, by dynamically falling back to simulated data.

5. R4. Dash UI 'Global Macro' Tab Integration:
   - Update `src/web/dashboard.py` to add the fourth tab `'Global Macro'` (`id='global-macro-tab'`).
   - The layout must contain:
     - Plotly Heatmap Graph (`macro-correlation-heatmap` ID or equivalent).
     - Dash DataTable for US recommenders (`us-outperformers-table` ID or equivalent).
     - Dash DataTable for KR recommenders (`kr-outperformers-table` ID or equivalent).
   - Implement stateless callback helper functions:
     - `update_macro_correlation_heatmap(selected_symbols, timeframe)`
     - `update_outperformers_table(country, timeframe, limit)`
   - Register Dash callbacks mapping these helper functions to the Dash components.
   - Ensure `server = app.server` is exposed and the app starts without errors.

6. Verification:
   - Write a unit/integration test file `tests/test_macro.py` or equivalent.
   - Run the full test suite using `pytest` and verify it passes.
   - Propose and run command to launch the dashboard and verify there are no compilation/runtime errors.

⚠️ MANDATORY INTEGRITY WARNING — include this verbatim in your implementation:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Please write your completed changes and handoff report to d:\Finance\code\stock\.agents\teamwork_preview_worker_macro_1\handoff.md when done.
