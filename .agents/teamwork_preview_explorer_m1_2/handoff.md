# Handoff Report — Explorer M1-2: SQLite Write-Lock Bottleneck Analysis & Storage Engine Solution Design

**Working Directory**: `d:\Finance\code\stock\.agents\teamwork_preview_explorer_m1_2`  
**Target Milestone**: Milestone 1 (R1) - Architecture Modularization & Data Engine Upgrade  
**Author**: Explorer M1-2  
**Date**: 2026-07-30  

---

## 1. Observation

### 1.1 Direct File & Code Observations
1. **`trading_system/src/data_layer/indicator_storage.py`**:
   - Lines 20–22: `self._write_lock = threading.Lock()`
   - Lines 27–32: Connection parameters: `sqlite3.connect(..., timeout=30)`, `PRAGMA journal_mode=WAL`, `PRAGMA busy_timeout=5000`.
   - Lines 384–404 (`save_fundamentals`): Iterates over DataFrame rows executing individual `INSERT OR REPLACE INTO stock_fundamentals` queries while holding `_write_lock`.
   - Lines 163–208 (`pipeline_stage` context manager): Logs pipeline stages to `pipeline_runs` using `_write_lock`.
2. **`trading_system/src/persistence/database.py`**:
   - Lines 365–376 (`StockPriceDB`): Uses `threading.local()` for connection caching per thread and `self._write_lock = threading.Lock()`.
   - Lines 441–449 (`update_prices`): Executes `conn.executemany("INSERT OR REPLACE INTO stock_prices ...", records)` under `with self._write_lock:`.
3. **`trading_system/run_pipeline.py`**:
   - Line 1116: `with ThreadPoolExecutor(max_workers=_CPU_WORKERS) as executor:` concurrently invokes `fetch_data_fdr()` for all 3,379 symbols.
   - Line 394 (`fetch_data_fdr`): Worker threads concurrently call `price_db.update_prices(s, network_result)`.
   - Line 1107: Starts background thread `_bg_fundamentals` for inference symbols concurrent with price fetching.
4. **`trading_system/src/config.py`**:
   - Line 25: `db_path: str = "market_indicators.db"`
   - Line 39: `stock_price_db_path: str = "stock_prices.db"`

### 1.2 Verbatim Error Logs & Behavior
- Under multi-threaded multi-asset data fetching, worker threads crash with:
  `sqlite3.OperationalError: database is locked`
- Cause: SQLite's single-writer architecture restricts write transactions to 1 active writer file lock. While `threading.Lock()` serializes threads within one process, multi-process execution (pipeline + background fundamentals fetch + dashboard server) bypasses the Python lock, exceeding SQLite `busy_timeout` (5s).

---

## 2. Logic Chain

1. **Premise 1**: SQLite operates as a single-writer file-based database. Even with Write-Ahead Logging (WAL mode), only one connection can hold a write lock at any instant.
2. **Premise 2**: `run_pipeline.py` uses `ThreadPoolExecutor(max_workers=16)` to fetch OHLCV prices and fundamentals for 3,379 symbols in parallel.
3. **Premise 3**: Worker threads call `StockPriceDB.update_prices()` and `MarketIndicatorStorage.save_fundamentals()`, acquiring `self._write_lock`.
4. **Step 1**: In-memory `threading.Lock()` forces 16 parallel network fetch threads to block sequentially on database writes. Parallel throughput collapses to single-threaded serial write speed.
5. **Step 2**: Secondary processes (e.g., background `_bg_fundamentals` thread, dashboard process, or orchestrator daemon) attempt to write to `stock_prices.db` or `market_indicators.db` without sharing Python's `threading.Lock()`.
6. **Step 3**: SQLite's OS-level file lock blocks the secondary process. When write transactions take longer than `busy_timeout` (5,000 ms) due to inserting 4+ million rows into SQLite B-trees, SQLite raises `OperationalError: database is locked`.
7. **Conclusion**: Resolving the bottleneck requires decoupling parallel write ingestion from SQLite's single-writer lock model using a lock-free staging write path (Parquet WAL) combined with a background single-writer compaction queue.

---

## 3. Caveats

- **Scope Boundary**: This report performs a read-only investigation and produces architecture design documentation in `.agents/teamwork_preview_explorer_m1_2/`. No modifications have been made directly to project source code.
- **Assumptions**: Assumes Apache PyArrow and pandas are available in `.venv` (verified during test execution).

---

## 4. Conclusion

The SQLite write-lock bottleneck is caused by applying in-memory `threading.Lock()` guards over file-level single-writer SQLite databases under multi-threaded (`ThreadPoolExecutor`) and multi-process execution. 

The recommended solution is **Option B: Hybrid SQLite + Parquet WAL Storage Engine**:
1. Workers write fetched symbol price frames into lock-free staging Parquet WAL files (`data/wal_staging/prices_{symbol}_{uuid}.parquet`).
2. A single-writer background worker thread (`WALCompactor`) batches and compacts staging files into the master Parquet analytical store and SQLite database.
3. Readers (`get_prices`) query master storage merged with active staging delta files, providing immediate read-your-own-writes consistency without lock errors.

---

## 5. Verification Method

### 5.1 Command Line Verification
Run current database concurrency unit tests using the project virtual environment:
```powershell
.venv\Scripts\python.exe -m pytest trading_system/tests/test_database.py -v
```

### 5.2 Verification of Proposed Storage Engine Implementation
After implementers build `src/data_layer/hybrid_storage.py`:
1. Run multi-threaded stress test with 32 worker threads issuing 1,000 concurrent writes:
   ```powershell
   .venv\Scripts\python.exe -m pytest trading_system/tests/test_database.py -k "TestStockPriceDBConcurrency"
   ```
2. Execute full pipeline dry run across 3,379 symbols in debug mode:
   ```powershell
   .venv\Scripts\python.exe trading_system/run_pipeline.py --debug
   ```
3. Inspect `data/wal_staging/` to verify staging cleanup and check row counts in `stock_prices.db` and master Parquet files.

### 5.3 Invalidation Conditions
- Any occurrence of `OperationalError: database is locked` during parallel execution.
- Discrepancies in OHLCV row counts or values returned by `get_prices()` before and after compaction.
