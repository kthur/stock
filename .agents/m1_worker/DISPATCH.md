## 2026-08-29T22:12:24Z

You are the Milestone 1 Implementation Worker: Pipeline Speed, Memory & Persistence Hardening.
Your working directory is: d:\Finance\code\stock\.agents\m1_worker

Read:
- ORIGINAL_REQUEST.md at: d:\Finance\code\stock\ORIGINAL_REQUEST.md
- PROJECT.md at: d:\Finance\code\stock\PROJECT.md
- M1 Explorer 1 Analysis at: d:\Finance\code\stock\.agents\m1_explorer_db_mem\analysis.md
- M1 Explorer 2 Analysis at: d:\Finance\code\stock\.agents\m1_explorer_scaler_threads\analysis.md
- M1 Explorer 3 Analysis at: d:\Finance\code\stock\.agents\m1_explorer_parallel_scoring\analysis.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Write Ownership:
You have exclusive write ownership of:
- `trading_system/src/persistence/database.py` (and `src/persistence/database.py` if symlinked/mirrored)
- `trading_system/src/ai/feature_engineering.py` (and `src/ai/feature_engineering.py`)
- `trading_system/src/ai/prediction_model.py` (and `src/ai/prediction_model.py`)
- `trading_system/run_pipeline.py`
- `tests/test_database.py`
- `tests/test_prediction_model.py`

Implementation Tasks (Implement following the 3 Explorer specifications):
1. **DB Batching & Memory Downcasting**:
   - In `database.py`, implement `StockPriceDB.update_prices_batch(price_data: Dict[str, pd.DataFrame], bypass_validation: bool = False) -> int` with single-transaction `executemany` under `_SHARED_WRITE_LOCK`. Refactor `update_prices` to delegate to `update_prices_batch({symbol: df})`.
   - In `run_pipeline.py`, refactor `prefetch_prices_batch` to commit downloaded price DataFrames in batches using `update_prices_batch`.
   - In `run_pipeline.py`, ensure numeric columns (`open`, `high`, `low`, `close`, `volume`, `change`) are downcasted to `np.float32` in `fetch_data_fdr`, `prefetch_prices_batch`, and `infer_data_dict` / `train_data_dict` construction.
2. **Scaler LRU Caching & Dynamic ML Thread Allocation**:
   - In `src/ai/feature_engineering.py`, add `@functools.lru_cache(maxsize=128)` caching to `load_scaler` via `_load_scaler_cached(norm_model_dir, market, horizon)` with normalized path and key types. Add `clear_scaler_cache()` and call it in `fit_scaler`.
   - In `src/ai/prediction_model.py`, accept `n_jobs` in `train()` and `train_surge()` and pass `n_jobs=intra_n_jobs` to XGBoost/LightGBM and `thread_count=intra_n_jobs` to CatBoost.
   - In `run_pipeline.py`, dynamically compute `_intra_n_jobs = max(1, _CPU_WORKERS // _train_workers)` and pass to `model.train()` and `model.train_surge()`.
3. **Parallel Factor Strategy Scoring**:
   - In `run_pipeline.py`, replace serial factor evaluation (Strategies 10-34 and 6) with thread-safe `ThreadPoolExecutor` concurrent evaluation following the Explorer 3 specification. Pre-compute shared datasets on the main thread and iterate canonically over registry keys when assembling output dictionaries and writing text reports.
4. **Unit Tests**:
   - Add unit tests for `StockPriceDB.update_prices_batch` in `tests/test_database.py`.
   - Add unit tests for scaler caching and dynamic `n_jobs` thread allocation in `tests/test_prediction_model.py`.

Verification:
- Run the test suites using `.venv\Scripts\pytest tests/test_database.py tests/test_prediction_model.py tests/test_pipeline_integration.py tests/test_all_16_markets_31_strategies.py -v`.
- Ensure 100% test pass rate with 0 failures.
- Document all changes and verification outputs in `d:\Finance\code\stock\.agents\m1_worker\handoff.md`.
- Send a message back to the orchestrator when completed.
