# Handoff Report - Global Macro Enhancements (R1-R4)

## 1. Observation
- **Dependency Sync**: Observed `pyproject.toml` dependencies block (lines 19-42) and `requirements.txt` (lines 1-23) did not include the `dash` dependency, despite `src/web/dashboard.py` importing `dash` (lines 6-7).
- **R1/R2 Implementation**: Modules `src/analysis/macro_analyzer.py` and `src/analysis/macro_predictor.py` were inspected. `macro_analyzer.py` contained `calculate_cross_correlation` and offline fallback simulation logic. `macro_predictor.py` contained `MacroPredictor` training and prediction functions, but during initial testing, training threw:
  `ERROR    src.analysis.screener:screener.py:283 Error training MacroPredictor for ^GSPC: Input y contains NaN.`
  And subsequently during prediction:
  `AttributeError: 'RandomForestRegressor' object has no attribute 'estimators_'`
- **R3 Screener**: Modified `src/analysis/screener.py` to append `screen_global_outperformers()` returning a dictionary of US and KR top 10 stocks predicted to outperform. Added robust stock price returns simulation mimicking benchmark correlation and USDKRW=X exchange rate correlation.
- **R4 Dashboard**: Updated `src/web/dashboard.py` to incorporate a fourth tab `'Global Macro'` (`id='global-macro-tab'`) containing:
  - Dropdowns for symbol selections and timeframes.
  - A slider for filtering row counts.
  - A `dcc.Graph` with ID `macro-correlation-heatmap`.
  - Two `dash_table.DataTable` elements with IDs `us-outperformers-table` and `kr-outperformers-table`.
  - Callback helper functions: `update_macro_correlation_heatmap` and `update_outperformers_table`.
  - Registered callbacks using `@app.callback`.
- **Verification Run**: Ran `.venv\Scripts\pytest tests/test_macro.py` resulting in:
  `======================= 5 passed, 3 warnings in 33.39s ========================`
- **Startup Run**: Ran `.venv\Scripts\python run_dashboard.py` resulting in successful launch log:
  `* Running on http://127.0.0.1:5000`
  `2026-06-08 05:22:56,224 - src.web.dashboard - INFO - Dashboard running in background thread on 127.0.0.1:5000`

## 2. Logic Chain
- Adding `dash` to `pyproject.toml` and `requirements.txt` aligns dependencies with the codebase usage, resolving any potential missing imports when running dashboard code.
- Dropping NaNs in features and targets in `MacroPredictor.train_model` handles potential missing returns on first-day calculations when computing `pct_change()` on stock histories or index benchmarks, preventing RandomForestRegressor fitting from raising exceptions.
- Implementing `screen_global_outperformers` using a pooled RandomForestRegressor trained on lagged macro feature vectors (lag 1 to 5 for S&P 500, Nasdaq, KOSPI, KOSDAQ, USD/KRW, US 10-Yr Yield, VIX) ensures the model predicts outperformance of US/KR stocks over their local benchmarks. Sorting by expected return and taking the top 10 satisfies the screening requirements.
- Adding the `'Global Macro'` tab layout components and registering the stateless helpers (`update_macro_correlation_heatmap` and `update_outperformers_table`) with `@app.callback` enables user interaction and reactive dashboard rendering.
- Running the newly written tests in `tests/test_macro.py` verifies both the calculation mathematics, ML predictions, stock screening, and dashboard callbacks return formatted figures and lists correctly.

## 3. Caveats
- Historical data fetching via `yfinance` relies on internet connectivity. In offline settings, the engine automatically falls back to simulated data, which maintains identical properties for validation purposes but is randomly generated.

## 4. Conclusion
The Global Macro Correlation Engine, ML Predictor Model, Global Outperformer Screener, and Dash UI 'Global Macro' Tab Integration have been successfully implemented, integrated, and verified to run without errors.

## 5. Verification Method
To independently verify the implementation:
1. Run the test suite:
   ```powershell
   .venv\Scripts\pytest tests/test_macro.py
   ```
   Ensure all 5 tests pass successfully.
2. Confirm the dashboard starts and exposes the server on localhost:
   ```powershell
   .venv\Scripts\python run_dashboard.py
   ```
   Check the output console for standard Dash listener activation without compilation errors.
