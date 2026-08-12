# Handoff Report: R2 Inference Vectorization & SQLite Concurrency Protection

**Author:** Explorer 2  
**Role:** Teamwork Explorer (Read-Only Investigation)  
**Working Directory:** `d:/Finance/code/stock/.agents/explorer_survey_2/`  
**Handoff Type:** Soft Handoff (Investigation Complete)  

---

## 1. Observation

### Observation 1: LSTM Single-Sample Item-by-Item Loop during Regression Inference
* **File Path:** `trading_system/src/ai/prediction_model.py`
* **Line Numbers:** 2319–2338 inside `_predict_regression()`
* **Verbatim Code:**
  ```python
  if lstm_m is not None and w_lstm_val > 0 and prices_dict is not None:
      lstm_preds = []
      for idx_val in idx:
          sym = symbols_list[idx_val]
          df_price = prices_dict.get(sym)
          if df_price is not None and len(df_price) >= 20:
              close_series = df_price['Close']
              if isinstance(close_series, pd.DataFrame):
                  close_series = close_series.iloc[:, 0]
              ret_seq = close_series.pct_change().dropna().tail(20).values
              if len(ret_seq) == 20:
                  x_in = ret_seq.reshape(1, 20, 1)
                  pred_val = lstm_m.predict(x_in)[0]
                  lstm_preds.append(pred_val)
              else:
                  lstm_preds.append(0.0)
          else:
              lstm_preds.append(0.0)
      preds.append(np.array(lstm_preds))
      weights.append(w_lstm_val)
  ```
* **Tool Command & Result:** Direct file inspection via `view_file`.

### Observation 2: Strategy Scorer Symbol-Level Loops
* **`TrendEfficiencyEngine`** (`trading_system/src/core/trend_efficiency.py`, Lines 77–109): Loop `for sym in symbols:` computing `_compute_ker()` on individual Series for 5D, 10D, 20D windows (over 10,000 `.diff().abs().sum()` calls per batch).
* **`ShortTermReversalEngine`** (`trading_system/src/core/short_term_reversal.py`, Lines 67–100): Loop `for sym, df in prices_dict.items():` computing 20-day mean, std, and Bollinger Band distances per symbol.
* **`AccrualsQualityEngine`** (`trading_system/src/core/accruals_quality.py`, Lines 81–106): Loop `for sym in symbols:` extracting dictionary fields (`net_income`, `operating_cash_flow`, `total_assets`) row by row.

### Observation 3: SQLite `PRAGMA busy_timeout` Configuration Audit
* **`MarketIndicatorStorage`** (`trading_system/src/data_layer/indicator_storage.py`, Line 77):
  ```python
  conn.execute("PRAGMA busy_timeout=5000")  # 5s retry on locked DB
  ```
  `PRAGMA busy_timeout` is set to `5000` ms (5s), failing the Requirement R2 mandate of `PRAGMA busy_timeout = 30000;`.
* **`StockPriceDB`** (`trading_system/src/persistence/database.py`, Lines 430, 441):
  ```python
  self._local.conn.execute("PRAGMA busy_timeout=60000")
  ```
  Uses `60000` ms (60s). Standardizing across storage handlers ensures consistent 30,000ms behavior.
* **Unprotected Auxiliary DB Connections:** `oms_engine.py` (lines 34, 119, 213), `trading_agent.py` (lines 112, 282, etc.), `trade_journal.py` (line 34), `slippage_feedback.py` (line 66), `state_store.py` (line 39), and `portfolio_allocator.py` (line 555) issue bare `sqlite3.connect()` calls without configuring `PRAGMA busy_timeout` or WAL mode.

### Observation 4: Existing Unit Test Execution Verification
* **Executed Tool Command:** `.venv\Scripts\python.exe -m pytest tests/test_database_concurrency.py -v`
* **Result:** **PASSED (2/2 tests passed in 0.95s)** — Verified multi-threaded 20-worker concurrent writes on `StockPriceDB` and lock-free Parquet WAL buffer flushing.
* **Executed Tool Command:** `.venv\Scripts\python.exe -m pytest trading_system/tests/test_hpo_and_2d_ensemble.py -v`
* **Result:** **PASSED (14/14 tests passed in 2.11s)** — Verified 2D regime matrix weighting, Optuna tuning, Platt scaling, Gram-Schmidt orthogonalization, and HRP asset allocation.

---

## 2. Logic Chain

1. **Observation 1** shows that `lstm_m.predict(x_in)` is invoked 3,379 times inside a Python `for` loop with single 3D arrays of shape `(1, 20, 1)`.
   * **Reasoning:** In neural network inference frameworks (PyTorch/TensorFlow/Keras/ONNX), calling single-sample `predict()` repeatedly incurs massive Python overhead and prevents SIMD / GPU batch processing.
   * **Conclusion:** Packing all 20-day return sequences into a single `(N_valid, 20, 1)` array and running `lstm_m.predict(X_batch)` in one call eliminates the loop bottleneck.

2. **Observation 2** shows symbol-level loops in `TrendEfficiencyEngine`, `ShortTermReversalEngine`, and `AccrualsQualityEngine`.
   * **Reasoning:** Price history and fundamental data can be represented as 2D DataFrames (dates/symbols x indicators/prices). Matrix operations in NumPy/Pandas evaluate across all symbols in a single C-optimized vectorized pass.
   * **Conclusion:** Refactoring these 3 strategy engines to 2D matrix operations will reduce strategy scoring overhead across 3,379 symbols.

3. **Observation 3** shows `MarketIndicatorStorage` sets `PRAGMA busy_timeout=5000` (5s), while auxiliary execution modules issue bare `sqlite3.connect()` calls without setting busy timeouts or WAL mode.
   * **Reasoning:** When multiple background threads (e.g. ThreadPoolExecutor during price fetch or strategy scoring) attempt to write to SQLite concurrently, a 5-second timeout is insufficient, leading to `sqlite3.OperationalError: database is locked`.
   * **Conclusion:** Setting `PRAGMA busy_timeout = 30000;` on `MarketIndicatorStorage` and adding WAL mode + `PRAGMA busy_timeout = 30000;` to all bare `sqlite3.connect()` calls satisfies Requirement R2 and eliminates database lock crashes.

4. **Observation 4** shows existing unit test suites (`test_database_concurrency.py`, `test_hpo_and_2d_ensemble.py`) pass cleanly in the `.venv` environment.
   * **Reasoning:** The test baseline is functional and reliable, providing a clear safety net for Implementer to apply vectorized refactoring and database timeout updates.

---

## 3. Caveats

* **No Code Modifications Made:** As Explorer, all source code in `trading_system/` remains unchanged per read-only investigation rules.
* **Hardware GPU Availability:** LSTM vectorization speedups will be greatest when CUDA or multi-core AVX-512 is available, but CPU batching will also yield significant speedups due to reduced Python interpreter call overhead.

---

## 4. Conclusion

Requirement R2 investigation is complete. The codebase exhibits clear vectorization targets in `OnDevicePredictionModel` (LSTM loop) and 3 core strategy scorers (`TrendEfficiencyEngine`, `ShortTermReversalEngine`, `AccrualsQualityEngine`), alongside non-compliant `PRAGMA busy_timeout=5000;` in `MarketIndicatorStorage` and missing timeout settings in auxiliary database modules. Full detailed findings and refactoring snippets are documented in `d:/Finance/code/stock/.agents/explorer_survey_2/report.md`.

---

## 5. Verification Method

To verify the investigation findings and test suite integrity independently:
1. **Run SQLite Concurrency Stress Tests:**
   ```bash
   .venv\Scripts\python.exe -m pytest tests/test_database_concurrency.py -v
   ```
2. **Run Ensemble & Strategy Scorer Tests:**
   ```bash
   .venv\Scripts\python.exe -m pytest trading_system/tests/test_hpo_and_2d_ensemble.py -v
   ```
3. **Inspect Target Files:**
   * `trading_system/src/ai/prediction_model.py` (lines 2319–2338)
   * `trading_system/src/data_layer/indicator_storage.py` (line 77)
   * `trading_system/src/core/trend_efficiency.py` (lines 77–109)
   * `trading_system/src/core/short_term_reversal.py` (lines 67–100)
   * `trading_system/src/core/accruals_quality.py` (lines 81–106)

---

## 6. Remaining Work (For Implementer)

1. **Implement Vectorized LSTM Batching:** Update `_predict_regression()` in `trading_system/src/ai/prediction_model.py` to construct `(N, 20, 1)` array and run batch `lstm_m.predict(X_batch)`.
2. **Refactor Core Strategy Engines:** Vectorize symbol-level loops in `TrendEfficiencyEngine`, `ShortTermReversalEngine`, and `AccrualsQualityEngine`.
3. **Configure SQLite `PRAGMA busy_timeout = 30000;`:** Update `MarketIndicatorStorage._connect()` (`indicator_storage.py`:77) and add busy_timeout configuration to auxiliary database connection sites (`oms_engine.py`, `trading_agent.py`, `trade_journal.py`, `slippage_feedback.py`, `portfolio_allocator.py`, `state_store.py`).
4. **Execute Full Test Suite Verification:** Run `.venv\Scripts\python.exe -m pytest tests/` to confirm zero regression.
