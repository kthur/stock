# Handoff Report: Codebase Researcher - Scheduler Daemon

## 1. Observation

- **Data Ingestion & Sync pathways**:
  - `trading_system/run_pipeline.py` (lines 70–87):
    - `market_client = GlobalMarketClient()` and `market_summary = market_client.get_summary()`.
    - `storage = MarketIndicatorStorage(db_path=cfg.db_path)`.
    - `storage.save_indicators(market_summary, date_str)` writes indices, FX rates, and macro commodities.
    - `storage.update_stock_universe()` fetches KRX and S&P 500 stocks.
  - `trading_system/src/ai/prediction_model.py` (lines 200–292):
    - `OnDevicePredictionModel.merge_fundamentals(self, symbol, df_prices, storage)` merges fundamental metrics (`revenue`, `operating_income`, `dividend_per_share`) from the database (via `storage.get_fundamentals(symbol)`) and falls back to dynamic deterministic values in `FALLBACK_METADATA[symbol]` if missing.
  - `trading_system/tests/test_database.py` (lines 150–170):
    - Tests `MarketIndicatorStorage.save_fundamentals` and `get_fundamentals` showing they read/write to the SQLite DB.
- **Stock Scoring & XGBoost Retraining**:
  - `trading_system/scripts/post_market_scoring.py` (lines 150–316):
    - Executes `main()` which fetches stock universe, historical prices, merges fundamentals, applies `apply_market_normalization()`, computes technical score (RSI, MACD, EMA, BB), AI score (queries `ai_predictions` table for `date_str` horizon 20), sentiment score, and computes:
      `composite_score = 0.40 * tech_score + 0.40 * ai_score + 0.20 * sentiment_score`.
      Ranks are saved using `storage.save_post_market_rankings(date_str, rankings)`.
  - `trading_system/run_pipeline.py` (lines 90–170):
    - Samples training symbols, fetches training data, retrains XGBoost regressor models in-memory for each horizon (`self.models[h] = model`), fetches inference data for ALL symbols, runs prediction batch inference, and saves the results to `ai_predictions` table via `storage.save_predictions(res_df, date_str)`.
  - `trading_system/src/ai/prediction_model.py` (lines 102, 373–394):
    - Models are stored in-memory in `self.models: Dict[int, xgb.XGBRegressor] = {}` and are **not serialized to disk**.
- **Database Status**:
  - Proposing a python checker script to inspect tables in both `market_indicators.db` files returned:
    - Root DB tables: `['global_indicators', 'stock_universe', 'ai_predictions', 'post_market_rankings', 'stock_fundamentals']`
    - Subfolder DB tables: `['global_indicators', 'stock_universe', 'ai_predictions', 'post_market_rankings', 'stock_fundamentals']`
    - Both databases lack a `pipeline_runs` table.
- **Dependencies & Environment**:
  - `apscheduler` is **not** installed in the active environment (`ModuleNotFoundError: No module named 'apscheduler'`).
  - `filelock` is installed in the active environment (version `3.12.2` listed in `out_pip_list.txt`).

## 2. Logic Chain

1. **Ingestion & Sync Invocations**: Because `GlobalMarketClient` and `MarketIndicatorStorage` expose clear methods (`get_summary`, `save_indicators`, `update_stock_universe`), we can invoke these programmatically to sync macro data and stock universe listings daily.
2. **In-Memory XGBoost Model Retraining**: Because `OnDevicePredictionModel` trains model instances purely in-memory and does not write them to disk, any separate execution of `post_market_scoring.py` will have no access to the trained models. If predictions for `date_str` are not pre-saved in the `ai_predictions` table, the scoring script defaults the AI return prediction to `0.0`.
3. **Execution Ordering**: Therefore, `run_pipeline.py` (retraining and batch inference) must run and populate `ai_predictions` before `post_market_scoring.py` executes on the day of evaluation. Alternatively, model serialization must be added.
4. **Table creation**: The database files exist but lack `pipeline_runs`. To persist logs and statuses, the table must be created with columns: `id`, `stage`, `start_time`, `end_time`, `status`, `error_message`.
5. **Scheduler & Overlap prevention**:
   - Because SQLite only supports a single concurrent writer, running ingestion, scoring, or retraining simultaneously will result in database lock errors.
   - Because `apscheduler` is missing, we must fallback to a single-threaded time-loop check daemon (sequential queue) or use locking.
   - Because `filelock` is installed, we can use a file lock on `pipeline.lock` to guarantee mutual exclusion across multiple processes (CLI triggers and daemon scheduler).

## 3. Caveats

- We did not write or modify any source code files (strictly read-only investigation).
- We assumed that `filelock` is the preferred tool for cross-process locking, as it is already installed.

## 4. Conclusion

- Programmatic calls for daily ingestion, stock universe sync, post-market scoring, and model retraining have been located and mapped.
- `pipeline_runs` table is missing and needs to be created in `market_indicators.db` using the recommended schema.
- Overlapping runs and concurrency can be handled by coordinating the schedule, using a shared threading lock, single-threaded execution queue, or `filelock`.

## 5. Verification Method

- **Analysis Verification**: Verify that `d:/Finance/code/stock/.agents/orchestrator_pipeline/explorer_daemon.md` is present and details the four items.
- **Pipeline Execution**: Verify execution pathways by manually executing:
  ```powershell
  python trading_system/run_pipeline.py
  python trading_system/scripts/post_market_scoring.py
  ```
- **Unit Test Execution**: Verify database CRUD functionality using:
  ```powershell
  pytest trading_system/tests/test_database.py
  ```
