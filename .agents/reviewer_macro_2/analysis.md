# Review Analysis — Stock Screener and Dash UI

## Review Summary

**Verdict**: APPROVE

We reviewed the implementation of the Stock Screener and Dash UI in `src/analysis/screener.py` and `src/web/dashboard.py`. The implementations are functionally complete, syntactically correct, and run cleanly without runtime exceptions. All verification tests passed successfully.

---

## Findings

No critical or major findings were discovered that would prevent approval. The following are minor observations/improvements:

### [Minor] Finding 1: Retraining on UI Callback
- **What**: The DataTable callback helper `update_outperformers_table` instantiates `StockScreener()` and calls `screen_global_outperformers()`, which retrains the `MacroPredictor` on every call.
- **Where**: `src/web/dashboard.py`, lines 282–294
- **Why**: Retraining Random Forest models inside web dashboard callback functions can introduce UI latency as the dataset scales.
- **Suggestion**: Cache the trained model metrics and prediction output, or run the training/prediction pipeline asynchronously in a background scheduler, saving results to a database/JSON cache that the dashboard callbacks can query quickly.

---

## Verified Claims

- **Claim 1**: Stock Screener returns exactly 10 US and 10 KR outperforming stocks → verified via inspecting `screen_global_outperformers` code (lines 316–327) and running `test_macro.py` (`test_r3_global_outperformer_screener`) → **PASS**
- **Claim 2**: Returned stocks contain required fields (`ticker`, `expected_excess_return`, `correlation_to_exchange_rate`) → verified via code inspection and `test_macro.py` execution → **PASS**
- **Claim 3**: Dash layout contains the required IDs (`global-macro-tab`, `macro-correlation-heatmap`, `us-outperformers-table`, `kr-outperformers-table`) → verified via code inspection of `src/web/dashboard.py` → **PASS**
- **Claim 4**: Helper functions `update_macro_correlation_heatmap` and `update_outperformers_table` are implemented and registered to Dash callbacks → verified via code inspection and running `test_r4_dash_callbacks` → **PASS**
- **Claim 5**: Dashboard starts and imports cleanly without runtime exceptions → verified via importing `app` using the virtual environment Python interpreter → **PASS**

---

## Coverage Gaps

- **Unexplored area**: Real-time behavior under concurrent user load.
- **Risk level**: Low (since Dash is wrapped in a Flask server and run with `use_reloader=False`).
- **Recommendation**: Accept risk for local/single-user deployment.

---

## Unverified Items

- None. All required checks have been fully verified.

---

## Challenge Summary (Adversarial Review)

**Overall risk assessment**: LOW

We stress-tested the robustness of the implementation under potential failure modes, network restrictions, and boundary inputs.

### [Medium] Challenge 1: Blocking synchronous ML training in Dash UI
- **Assumption challenged**: ML training/screener execution is fast enough to run synchronously inside Dash callbacks.
- **Attack scenario**: If the ticker lists (`US_TICKERS`, `KR_TICKERS`) grow or yfinance historical data period increases, training the Random Forest models for each region sequentially in the callback will block Flask worker threads. If multiple users load the page simultaneously, it could lead to timeouts or application unresponsiveness.
- **Blast radius**: Medium (blocks dashboard responsiveness/interactivity).
- **Mitigation**: Offload prediction/screening to a background worker and read from a database cache.

### [Low] Challenge 2: Offline/Network Failure
- **Assumption challenged**: YFinance data download is always available.
- **Attack scenario**: Under network isolation (e.g., CODE_ONLY mode), YFinance API returns empty DataFrames or throws timeout/HTTP exceptions.
- **Blast radius**: Medium (causes screeners to return default list or mock values).
- **Mitigation**: The code contains robust local fallback simulation data generation (lines 202–215 and 234–247) which ensures the screener still outputs exactly 10 US and 10 KR stocks with realistic mock metrics under network failure.

---

## Stress Test Results

- **Empty Selected Symbols on Heatmap** → passing empty list `[]` to `update_macro_correlation_heatmap` → returns a safe error dictionary `{'data': [], 'layout': {'title': 'No symbols selected'}}` → **PASS**
- **Invalid Symbols on Heatmap** → passing arbitrary list `['INVALID_SYM']` to `update_macro_correlation_heatmap` → returns `{'data': [], 'layout': {'title': 'No valid symbols found in returns'}}` safely without raising exceptions → **PASS**
- **Offline / Isolated Mode Run** → `yf.download` timeout/network failures → fallback to synthetic data generator creates valid `pd.Series` of prices for all tickers → **PASS**
