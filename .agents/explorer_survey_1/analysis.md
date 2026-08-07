# Stock Price Fetching & Data Resilience Investigation Report

**Explorer**: Explorer 1  
**Project**: Price Fetch Hardening Project  
**Date**: 2026-08-06  
**Target Directory**: `d:\Finance\code\stock`  

---

## Executive Summary

An in-depth investigation was conducted into the price fetching, caching, and update architecture across all 6 target stock markets (**KOSPI, KOSDAQ, KONEX, SP500, NASDAQ, RUSSELL2000**, comprising ~3,379 active symbols).

While the system implements a conceptual **3-Tier Fallback Architecture** (Tier 1: `yfinance` → Tier 2: `FinanceDataReader` → Tier 3: `StockPriceDB` local SQLite WAL cache), the audit uncovered critical network retry gaps, exception swallowing bugs, ticker symbol format mismatches (especially for KONEX and dotted US tickers), missing rate-limit backoff in batch prefetching, and data quality gate bypasses.

---

## 1. `StockPriceDB` Persistence Layer Analysis (`trading_system/src/persistence/database.py`)

### 1.1 Architecture & Schema
`StockPriceDB` manages daily OHLCV bar storage in `trading_system/stock_prices.db` using SQLite WAL mode.
- **Table Schema**:
  ```sql
  CREATE TABLE IF NOT EXISTS stock_prices (
      symbol TEXT NOT NULL,
      date TEXT NOT NULL,
      open REAL,
      high REAL,
      low REAL,
      close REAL,
      volume INTEGER,
      updated_at TEXT DEFAULT (datetime('now')),
      PRIMARY KEY (symbol, date)
  );
  CREATE INDEX IF NOT EXISTS idx_stock_prices_symbol_date ON stock_prices(symbol, date);
  ```

### 1.2 Thread Safety & Concurrency Locking
- **Thread-local connections**: Managed via `_get_conn()` using `threading.local()`.
- **WAL Settings**: Enables `PRAGMA journal_mode=WAL`, `PRAGMA busy_timeout=60000`, `cache_size=-500000` (500MB cache), `mmap_size=2000000000` (2GB memory mapped I/O).
- **Write Lock Mutex**: `self._write_lock = threading.Lock()` wraps all upserts in `update_prices()`.
- **Retry Mechanism**: Delegates to `execute_sqlite_with_retry(_do_update)` from `src.data_layer.hybrid_storage` to handle SQLite write lock contention.

### 1.3 Key Functionalities
- `update_prices(symbol, df)`: Normalizes date index, constructs `(symbol, date, open, high, low, close, volume)` tuples, and executes batch `INSERT OR REPLACE INTO stock_prices`.
- `get_prices(symbol, start_date, end_date)`: Queries records matching symbol and date bounds, returns a DatetimeIndex-sorted pandas DataFrame with capitalized columns (`Open`, `High`, `Low`, `Close`, `Volume`).
- `needs_update(symbol, max_age_days=1, start_date=None)`: Checks if cached data is older than `max_age_days` or if historical backfill is required (`earliest_cached_date - start_date > 7 days`).

### 1.4 Critical Vulnerabilities & Gaps in `StockPriceDB`
1. **Passive Storage Only**: `StockPriceDB` contains no internal network fetching logic; it relies strictly on caller functions (`fetch_data_fdr`, `prefetch_prices_batch`) to fetch and inject data.
2. **Missing Input Data Quality Validation**: `update_prices()` inserts any DataFrame passed to it without verifying if values contain NaNs, non-positive prices, or zero-volume anomalies.
3. **Ticker Casing & Alias Fragmentation**: Tickers are stored verbatim (`'005930'` vs `'005930.KS'`, `'BRK.B'` vs `'BRK-B'`). Inconsistent formatting across modules creates duplicate or fragmented DB records and causes cache misses.

---

## 2. Model Training & Inference Data Ingestion Analysis (`trading_system/src/ai/prediction_model.py`)

### 2.1 Ingestion Mechanism (`OnDevicePredictionModel`)
`OnDevicePredictionModel` does NOT directly fetch data from network APIs. It receives pre-fetched price DataFrames via `prices_dict: Dict[str, pd.DataFrame]` supplied by `run_pipeline.py`.

### 2.2 Data Quality & Length Requirements
- **Training (`prepare_training_data`)**:
  - Filters out symbols where `df is None or len(df) < 70`.
  - Normalizes market capitalization and volume scale (`apply_market_normalization`).
  - Computes 54+ technical indicators, VCP vectorized features, and lag features (`_create_features`).
  - Computes Sharpe-scaled forward return targets (`target_1d` to `target_200d`) in `_create_targets`.
  - Downcasts `float64` to `float32` for memory optimization.
- **Inference (`predict_all`)**:
  - Requires `len(df) >= 200` trading days of price history. Symbols with `< 200` days are filtered out prior to inference in `run_pipeline.py`.
  - Generates predictions across 8 regression horizons and 4 surge horizons per market.

### 2.3 Fallback Mechanism (`FALLBACK_METADATA`)
- `FallbackMetadataDict` provides benchmark fundamental metrics (shares outstanding, floating shares) for 16 core US/KR stocks.
- For non-benchmark symbols, it returns `np.nan` rather than artificial dummy values, preventing synthetic feature corruption during inference.

### 2.4 Critical Gaps in Model Ingestion
- `prediction_model.py` drops symbols cleanly if data is below the threshold (`len(df) < 70` for train, `len(df) < 200` for infer), but network fetch failures directly reduce universe coverage and prediction yield.

---

## 3. Pipeline Step 5 & Step 9 Price Fetching Analysis (`trading_system/run_pipeline.py`)

### 3.1 Step 5: Training Data Fetching Flow
1. **Universe Sampling**: Selects active KRX and US symbols based on `TradingConfig` sample sizes.
2. **Background Fundamentals**: Starts non-blocking thread `_bg_fundamentals(train_symbols, "training")`.
3. **Batch Prefetching**: Executes `prefetch_prices_batch(train_symbols, symbol_market, start_date_train, price_db, freshness)`:
   - Batches symbols in chunks of 100 tickers.
   - Downloads from yfinance (`yf.download`) using `_download_with_recovery`.
   - Validates data via `_validate_price_data` (DataQualityGate).
   - Writes valid bars to `StockPriceDB`.
4. **Parallel Per-Symbol Fetching**:
   - Spawns `ThreadPoolExecutor(max_workers=_CPU_WORKERS)` calling `fetch_data_fdr(sym, sym_market, start_date_train, price_db, freshness, update_interval)`.
   - Times out individual symbol tasks after `_PER_SYMBOL_TIMEOUT = 30` seconds.
   - Stores valid DataFrames into `train_data_dict`.
5. **Feature & Target Generation**: Merges fundamentals, prepares `df_train`, fits per-market models (`sp500`, `nasdaq`, `russell2000`, `kospi`, `kosdaq`), computes lead-lag matrix, and fits Isotonic calibrators.

### 3.2 Step 9: Inference Data Fetching Flow
1. **Full Universe Resolution**: Resolves all active target symbols across target markets (~3,379 symbols).
2. **Administrative/Halted Filter**: Excludes halted and administrative KRX stocks via `_get_excluded_krx_symbols()`.
3. **Background Fundamentals**: Starts non-blocking inference fundamentals thread `t2`.
4. **Batch Prefetching**: Executes `prefetch_prices_batch(all_symbols, symbol_market, start_date_infer, price_db, freshness)`.
5. **Parallel Per-Symbol Fetching**:
   - Spawns `ThreadPoolExecutor(max_workers=_CPU_WORKERS)` running `fetch_data_fdr` across all symbols.
   - Collects DataFrames into `infer_data_dict`.
6. **Data Length Filtering**: Excludes symbols with `< 200` days of OHLCV history (`infer_data_dict = {s: df for s, df in infer_data_dict.items() if len(df) >= 200}`).
7. **Model Execution**: Merges fundamentals and runs `model.predict_all(...)`.

---

## 4. Comprehensive Audit of Retries, Exponential Backoff, Rate Limiting & Exception Handling

### 4.1 Implemented 3-Tier Fallback Architecture
```
[Client Request: fetch_data_fdr(symbol)]
       │
       ▼
┌───────────────────────────────┐
│ Tier 1: yfinance Download     │  <-- Wrapped with @retry(stop_after_attempt(3), wait_exponential)
│ (US: AAPL | KR: 005930.KS)    │
└──────────────┬────────────────┘
               │ (Fails / Empty)
               ▼
┌───────────────────────────────┐
│ Tier 2: FinanceDataReader     │  <-- Secondary provider fallback
│ (Direct symbol: 005930)       │
└──────────────┬────────────────┘
               │ (Fails / Empty)
               ▼
┌───────────────────────────────┐
│ Tier 3: StockPriceDB Cache    │  <-- Offline SQLite WAL historical fallback
│ (Local stock_prices.db)       │
└───────────────────────────────┘
```

---

### 4.2 Exhaustive Findings: Missing Retries, Defective Backoff & Edge Cases

| # | Vulnerability / Defect Area | Location | Specific Finding & Impact | Recommended Fix |
|---|-----------------------------|----------|---------------------------|-----------------|
| **1** | **KONEX Market Suffix Missing** | `run_pipeline.py` (line 151) | `_KR_MARKET_SUFFIX` only maps `KOSPI`, `KOSDAQ`, `KRX`. `KONEX` falls back to `.KS` suffix on `yfinance`, causing 404 / empty download errors on Yahoo Finance for all KONEX symbols. | Add `'KONEX': '.KS'` or special handling for KONEX to route directly to FinanceDataReader (`fdr.DataReader`). |
| **2** | **Batch Prefetching Missing Retries & Backoff** | `run_pipeline.py` (lines 310-347) | `prefetch_prices_batch` calls `_download_with_recovery`, which uses raw `yf.download` **without Tenacity `@retry` decorators or exponential backoff**. Transient network errors or HTTP 429 rate limits trigger binary batch splitting without retrying the network call. | Decorate `_download_with_recovery` or internal batch downloader with `@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))`. |
| **3** | **Batch Prefetching Lacks Tier 2 Secondary Fallback** | `run_pipeline.py` (lines 236-376) | `prefetch_prices_batch` relies exclusively on `yfinance`. If `yfinance` rate-limits or blocks a batch of KRX symbols, it fails completely and does not fall back to `FinanceDataReader`. | Add secondary batch fallback using `FinanceDataReader` or individual `fdr.DataReader` when yfinance batch fails. |
| **4** | **Internal Exception Catching Swallows Tier 1 Retries** | `run_pipeline.py` (lines 177-184) | `_fetch_data_fdr_network` encloses `yf.download` in a local `try...except` block that catches `Exception` and swallows it locally (setting `result = None`) before cascading to Tier 2. Because the Tier 1 exception is swallowed locally, Tenacity's `@retry` decorator on `_fetch_data_fdr_network` NEVER retries Tier 1 (`yf.download`) on transient failures! | Decouple Tier 1 into a separate retryable function `_fetch_yf_primary(symbol, start_date)` decorated with `@retry(reraise=True)`, matching the pattern used in `_download_indicator_yf`. |
| **5** | **Ticker Symbol Format Mismatches** | `run_pipeline.py` & `database.py` | US tickers with dots (`BRK.B`, `BF.B`) fail on `yfinance` unless converted to `BRK-B`. KRX numeric tickers passed as unpadded strings (e.g. `'5930'`) fail unless zero-padded (`'005930'`). | Implement a centralized `normalize_ticker(symbol, market)` helper to standardize tickers before calling APIs or querying `StockPriceDB`. |
| **6** | **Single-Symbol Data Quality Gate Bypass** | `run_pipeline.py` (lines 408-413) | `prefetch_prices_batch` enforces `DataValidator.validate_price_data()` before writing to `StockPriceDB`, but single-symbol `fetch_data_fdr()` directly calls `price_db.update_prices(s, network_result)` **without quality validation**. Corrupted network payloads overwrite clean DB cache. | Wrap `network_result` in `DataValidator.validate_price_data(s, network_result)` inside `fetch_data_fdr()` before updating `price_db`. |
| **7** | **`MarketDataHandler` Single-Provider Dependency** | `src/data_layer/market_data_handler.py` (lines 201-305) | `MarketDataHandler.fetch_historical_data` uses `yfinance` exclusively (`yf.Ticker(symbol)`). If yfinance fails, it returns empty or cached bars without attempting Tier 2 `FinanceDataReader` fallback. | Add `FinanceDataReader` secondary fallback inside `MarketDataHandler.fetch_historical_data`. |
| **8** | **ThreadPool Rate Limiter Timeout Contention** | `run_pipeline.py` (lines 957-985, 1164-1194) | During 3,379 symbol parallel fetching, worker threads block on `get_global_rate_limiter().wait()`. Under heavy thread contention, worker threads time out waiting in queue (`_PER_SYMBOL_TIMEOUT = 30s`), logging `Skipping {sym}: timeout (>=30s)` and dropping valid symbols. | Increase per-symbol timeout during batch runs, optimize batch size, and ensure rate limiter token replenishment is smooth. |

---

## 5. Summary of Recommended Actions for Implementation Team

1. **Decouple Tier 1 & Tier 2 Retries in `_fetch_data_fdr_network`**:
   - Extract `_fetch_yf_primary(symbol, market, start_date)` decorated with `@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)`.
   - Call `_fetch_yf_primary` inside `_fetch_data_fdr_network` and fall back to `fdr.DataReader` only after Tier 1 retries are exhausted.
2. **Add Network Retries & Secondary Fallback to `prefetch_prices_batch`**:
   - Decorate batch downloads with Tenacity exponential backoff `@retry`.
   - Add fallback to `FinanceDataReader` for failed yfinance batches.
3. **Standardize Ticker Normalization**:
   - Add `normalize_ticker(symbol, market)` handling dot-to-dash conversion (`BRK.B` -> `BRK-B`) and 6-digit zero-padding (`'5930'` -> `'005930'`).
   - Add `'KONEX'` explicit suffix mapping in `_KR_MARKET_SUFFIX`.
4. **Enforce Data Quality Gate in Single-Symbol `fetch_data_fdr`**:
   - Validate `network_result` via `DataValidator.validate_price_data()` before updating `StockPriceDB`.
5. **Add Tier 2 Fallback to `MarketDataHandler`**:
   - Update `fetch_historical_data` in `src/data_layer/market_data_handler.py` to fall back to `FinanceDataReader` if `yfinance` fails.
