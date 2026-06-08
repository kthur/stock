## 2026-06-07T20:33:22Z
You are teamwork_preview_worker. Your working directory is d:\Finance\code\stock\.agents\teamwork_preview_worker_macro_2\.
Please implement the following fixes and enhancements to resolve issues identified by the reviewers and challengers:

1. Timezone Alignment & Look-Ahead Bias:
   - In `src/analysis/macro_analyzer.py` inside the function `fetch_macro_indices_data()`, shift US symbols `["^GSPC", "^IXIC", "^TNX", "^VIX"]` forward by 1 day:
     ```python
     us_symbols = ["^GSPC", "^IXIC", "^TNX", "^VIX"]
     for sym in us_symbols:
         if sym in combined.columns:
             combined[sym] = combined[sym].shift(1)
     ```
     This aligns US trading sessions with Korean trading sessions and avoids look-ahead bias.

2. ML Predictor Placebo Flaw:
   - In `src/analysis/screener.py` inside `screen_global_outperformers()`:
     - For each ticker, construct ticker-specific features by copying `macro_features_df` and appending `stock_lag_1` to `stock_lag_5` (shifted daily returns of that specific ticker):
       ```python
       ticker_features = macro_features_df.copy()
       for lag in range(1, 6):
           ticker_features[f"stock_lag_{lag}"] = stock_returns[ticker].shift(lag)
       ticker_features = ticker_features.dropna()
       ```
     - Pool these ticker-specific feature DataFrames to train the `MacroPredictor`.
     - When predicting, construct a `latest_features` DataFrame containing the latest macro features AND the stock's own lagged returns:
       ```python
       ticker_latest = {}
       for sym in MACRO_SYMBOLS:
           for lag in range(1, 6):
               ticker_latest[f"{sym}_lag_{lag}"] = macro_returns[sym].iloc[-lag]
       for lag in range(1, 6):
           ticker_latest[f"stock_lag_{lag}"] = stock_returns[ticker].iloc[-lag]
       latest_features = pd.DataFrame([ticker_latest])
       ```
       Pass this ticker-specific `latest_features` to the predictor. This ensures predictions are unique per stock.

3. Bug 1 (Cholesky Crash):
   - In `src/analysis/macro_analyzer.py` inside `generate_simulated_macro_data()`:
     - Project the hardcoded correlation matrix `corr_matrix` to the nearest positive semi-definite matrix before running Cholesky:
       ```python
       w, v = np.linalg.eigh(corr_matrix)
       w = np.maximum(w, 1e-6)
       corr_matrix_psd = v @ np.diag(w) @ v.T
       d = np.sqrt(np.diag(corr_matrix_psd))
       corr_matrix_psd = corr_matrix_psd / np.outer(d, d)
       L = np.linalg.cholesky(corr_matrix_psd)
       ```

4. Bug 2 (Broadcasting Crash):
   - In `src/analysis/screener.py` inside `screen_global_outperformers()`:
     - For both the US stock simulation fallback and KR stock simulation fallback, change:
       `dates = macro_df.index`
       to:
       `dates = macro_returns.index`
       This resolves shape mismatch bugs between dates and returns.

5. Bug 3 (Dash UI Slicing):
   - In `src/web/dashboard.py` inside `update_outperformers_table()`:
     - Ensure the limit is non-negative: `limit = max(0, limit)`.

6. Verification:
   - Run the test suite using `pytest tests/test_macro.py` and `pytest tests/test_macro_stress.py`.
   - Verify that the dashboard launches without errors.
   - Provide the test execution results in your handoff.

⚠️ MANDATORY INTEGRITY WARNING — include this verbatim in your implementation:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Please write your completed changes and handoff report to d:\Finance\code\stock\.agents\teamwork_preview_worker_macro_2\handoff.md when done.
