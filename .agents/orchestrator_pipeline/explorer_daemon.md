# Codebase Analysis: Pipeline Ingestion, Model Retraining, and Scheduler Design

This document provides a detailed analysis of the execution paths for daily data ingestion, post-market stock scoring, XGBoost model retraining, database run logging, and scheduler coordination in the `trading_system` codebase.

---

## 1. Daily Data Ingestion and Database Sync (Prices & Fundamentals)

Daily data ingestion and database synchronization are split into three main components: global market indicators, the stock universe, and stock fundamentals/prices.

### 1.1 Global Market Indicators (Indices, FX, Macro Commodities)
- **Source Module**: `trading_system/src/data_layer/global_market.py`
  - Defines the `GlobalMarketClient` class which fetches indicators from `yfinance`.
  - Configures standard indices (`GLOBAL_INDICES`), currency pairs (`FX_PAIRS`), and macro items (`MACRO_COMMODITIES`).
- **Storage Module**: `trading_system/src/data_layer/indicator_storage.py`
  - Defines the `MarketIndicatorStorage` class which interacts with the SQLite database (`market_indicators.db`).
  - The `save_indicators(self, data: dict, date_str: str)` method writes these indicators into the `global_indicators` table.
- **Programmatic Invocation**:
  ```python
  from src.config import TradingConfig
  from src.data_layer.global_market import GlobalMarketClient
  from src.data_layer.indicator_storage import MarketIndicatorStorage
  from datetime import datetime

  # Load configuration and initialize components
  cfg = TradingConfig()
  market_client = GlobalMarketClient()
  storage = MarketIndicatorStorage(db_path=cfg.db_path)

  # Fetch current global indicators
  market_summary = market_client.get_summary()

  # Persist to database
  date_str = datetime.now().strftime('%Y-%m-%d')
  storage.save_indicators(market_summary, date_str)
  ```

### 1.2 Stock Universe Sync
- **Source Module**: `trading_system/src/data_layer/indicator_storage.py`
  - The `update_stock_universe(self)` method fetches S&P 500 and KRX tickers using `FinanceDataReader` and upserts them into the `stock_universe` table.
- **Programmatic Invocation**:
  ```python
  storage.update_stock_universe()
  ```

### 1.3 Price and Fundamentals Ingestion
- **Prices**: Daily historical prices are fetched on-the-fly during training and inference in `run_pipeline.py` (using `FinanceDataReader.DataReader(symbol, start=start_date)`).
- **Fundamentals CRUD**: 
  - `MarketIndicatorStorage` provides a CRUD interface for fundamentals:
    - Save: `storage.save_fundamentals(df_fundamentals)` (expects columns: `['symbol', 'date', 'revenue', 'operating_income', 'dividend_per_share']`)
    - Retrieve: `storage.get_fundamentals(symbol)`
  - **Fallback Behavior**: If no fundamental data exists in the database for a stock, `OnDevicePredictionModel.merge_fundamentals` falls back to generating deterministic mock data using the `FALLBACK_METADATA` hash-map.

---

## 2. Post-Market Stock Scoring and XGBoost Retraining

### 2.1 Daily Post-Market Stock Scoring
- **Source Module**: `trading_system/scripts/post_market_scoring.py`
- **Execution Mechanism**:
  - **CLI Command**:
    ```bash
    python trading_system/scripts/post_market_scoring.py --date YYYY-MM-DD
    ```
    *(If `--date` is omitted, it defaults to today's date).*
  - **Programmatic / Subprocess Invocations**:
    ```python
    import subprocess
    import sys
    subprocess.run([sys.executable, "trading_system/scripts/post_market_scoring.py", "--date", "2026-06-13"], check=True)
    ```
- **Operational Logic**:
  1. Loads stock universe and fetches 70 days of historical prices.
  2. Merges fundamentals (database lookup with fallback to mock metadata).
  3. Applies market normalization (`OnDevicePredictionModel.apply_market_normalization()`).
  4. Calculates **Technical Score** (composite of RSI, MACD, EMA, Bollinger Bands).
  5. Calculates **AI Score** (queries latest expected return for 20d horizon in `ai_predictions`).
  6. Calculates **Sentiment Score** (fetches yfinance news or falls back to deterministic text analysis).
  7. Computes **Composite Score** = `0.40 * Technical + 0.40 * AI + 0.20 * Sentiment`.
  8. Saves the ranked results to the `post_market_rankings` table in `market_indicators.db`.

### 2.2 XGBoost Model Retraining and Inference
- **Source Module**: `trading_system/run_pipeline.py`
- **Execution Mechanism**:
  - **CLI Command**:
    ```bash
    python trading_system/run_pipeline.py
    ```
  - **Programmatic Invocation**:
    ```python
    from run_pipeline import execute_prediction_pipeline
    res_df, message_text = execute_prediction_pipeline()
    ```
- **Operational Logic**:
  1. Fetches global market indicators and updates the stock universe.
  2. Samples symbols (`train_sample_size` in config).
  3. Fetches training price data and merges fundamentals.
  4. Trains `xgb.XGBRegressor` models in-memory for each prediction horizon (1, 5, 10, 20, 30, 60, 120, 200 days).
  5. Fetches recent price data for ALL symbols, runs inference, and writes predictions to the `ai_predictions` table.
- **CRITICAL ARCHITECTURAL FINDING**: The XGBoost models are kept in-memory in the `OnDevicePredictionModel` instance and **are not serialized to disk**. Because there is no serialization, running `post_market_scoring.py` as a separate process will result in AI scores of 0.0 unless:
  - Predictions for that date were already saved in the database by `run_pipeline.py`.
  - Therefore, `run_pipeline.py` must run before `post_market_scoring.py` on the day of evaluation, or model serialization must be added.

---

## 3. Database Table `pipeline_runs` Status and Schema

- **Status**: The table `pipeline_runs` does **NOT** exist in either `market_indicators.db` file (neither at the root nor in `trading_system/`).
- **SQL Schema Recommendation**:
  ```sql
  CREATE TABLE IF NOT EXISTS pipeline_runs (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      stage TEXT NOT NULL,
      start_time TEXT NOT NULL,
      end_time TEXT,
      status TEXT NOT NULL,
      error_message TEXT
  );
  ```
- **Implementation Strategy**:
  Modify the `_init_db()` method in `MarketIndicatorStorage` (`trading_system/src/data_layer/indicator_storage.py`) to create this table during database initialization:
  ```python
  conn.execute('''
      CREATE TABLE IF NOT EXISTS pipeline_runs (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          stage TEXT,
          start_time TEXT,
          end_time TEXT,
          status TEXT,
          error_message TEXT
      )
  ''')
  ```

---

## 4. Scheduler Coordination and Concurrency Management

To safely execute these tasks and handle concurrency, we must address SQLite's single-writer limitation and the high CPU/memory usage of XGBoost training.

### 4.1 Recommended Schedule
- **Daily Ingestion & DB Sync**: Run daily at **15:45** (shortly after KRX close, finishes in seconds).
- **Daily Post-Market Scoring**: Run daily at **16:30** (after ingestion).
- **Weekly XGBoost Retraining & Inference**: Run weekly on **Sunday at 01:00** (markets closed, generates predictions for the upcoming week).

### 4.2 Handling Concurrency and Preventing Overlap
Since `apscheduler` is **not** installed in the environment, we must design for both its introduction and a robust fallback mechanism.

#### Option A: APScheduler (AsyncIOScheduler / BackgroundScheduler)
If `apscheduler` is added to `requirements.txt` and installed:
1. **Instance Limiting**: Set `max_instances=1` on all jobs.
2. **Mutual Exclusion Lock**: Use a global `threading.Lock` to ensure only one task runs at a time:
   ```python
   import threading
   
   pipeline_lock = threading.Lock()

   def safe_job_wrapper(job_func):
       if not pipeline_lock.acquire(blocking=False):
           logger.warning(f"Task overlap detected. Skipping execution of {job_func.__name__}")
           return
       try:
           job_func()
       finally:
           pipeline_lock.release()
   ```

#### Option B: Fallback Time-Loop Check (No External Scheduler Library)
If we cannot add libraries:
1. **Single-Threaded Execution Queue**: Run a background thread with a `while` loop checking the time. When a task is due, execute it synchronously. Because execution is sequential and single-threaded, overlapping is physically impossible.
2. **State-based DB / File Locking**:
   - **DB Check**: Before running, query `SELECT COUNT(*) FROM pipeline_runs WHERE status = 'running'`. If > 0, wait or skip.
   - **File Lock (Recommended)**: Use `filelock` (which is already installed in the environment: version `3.12.2`) to lock a `pipeline.lock` file. This prevents overlap even if tasks are triggered concurrently via CLI:
     ```python
     from filelock import FileLock, Timeout

     lock = FileLock("pipeline.lock", timeout=1)
     try:
         with lock:
             # Execute stage
     except Timeout:
         # Log and skip
     ```
