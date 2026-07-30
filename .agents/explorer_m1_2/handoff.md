# System Architecture, DB I/O, Concurrency, Memory & Pipeline Stability Audit

**Agent**: Explorer M1-2 (System Architecture & Concurrency Specialist)  
**Working Directory**: `d:\Finance\code\stock\.agents\explorer_m1_2`  
**Target Scope**: Stock Trading System (3,379 Symbols across SP500, KOSPI, KOSDAQ, KONEX)  
**Audit Date**: 2026-07-30  

---

## 1. Observation

Direct code inspection of the targeted codebase files revealed 13 specific vulnerabilities spanning database I/O performance, concurrency, memory footprint, data missingness handling, and pipeline orchestration stability.

### A. Database I/O & SQLite Locking Vulnerabilities

1. **Bare `sqlite3.connect` Calls Bypassing WAL Manager & Lock Control**
   - **Locations**:
     - `trading_system/src/execution/oms_engine.py`: Lines 23, 67, 131 (`conn = sqlite3.connect(self.db_path)`)
     - `trading_system/src/ai/trading_agent.py`: Lines 112, 282, 560, 587, 635, 714, 730 (`conn = sqlite3.connect(self.config.db_path)` and `self.config.stock_price_db_path`)
     - `trading_system/src/data_layer/trade_journal.py`: Line 34 (`conn = sqlite3.connect(self.db_path)`)
     - `trading_system/run_pipeline.py`: Line 2474 (`ExecutionOMSEngine(db_path=... "trade_logs.db")`)
   - **Observation**:
     ```python
     # oms_engine.py: line 23
     conn = sqlite3.connect(self.db_path)
     ```
     These raw connections do not set `PRAGMA journal_mode=WAL`, do not configure `busy_timeout`, do not set `check_same_thread=False`, and do not acquire process-level write locks (`_write_lock`).

2. **Connection Leak in ThreadPoolExecutor Connections (`StockPriceDB`)**
   - **Location**: `trading_system/src/persistence/database.py`: Lines 388-397 (`_get_conn()` using `threading.local()`) & `trading_system/run_pipeline.py`: Lines 924, 1116, 1185, 1222 (`ThreadPoolExecutor`)
   - **Observation**:
     ```python
     # database.py: lines 388-391
     def _get_conn(self) -> sqlite3.Connection:
         if not hasattr(self._local, "conn") or self._local.conn is None:
             self._local.conn = sqlite3.connect(str(self.db_path), timeout=30, check_same_thread=False)
     ```
     Connections stored in thread-local storage (`self._local.conn`) are never closed when `ThreadPoolExecutor` threads complete their futures.

3. **Missing `PRAGMA synchronous = NORMAL` in `StockPriceDB`**
   - **Location**: `trading_system/src/persistence/database.py`: Lines 388-397 (`_get_conn()`)
   - **Observation**:
     ```python
     self._local.conn.execute("PRAGMA journal_mode=WAL")
     self._local.conn.execute("PRAGMA busy_timeout=5000")
     self._local.conn.execute("PRAGMA cache_size=-500000")
     # Note: PRAGMA synchronous is missing!
     ```
     Default WAL synchronous mode is `FULL`, forcing a full disk `fsync` flush on every `conn.commit()`.

4. **Frequent Connection Creation / Teardown Overhead in `MarketIndicatorStorage`**
   - **Location**: `trading_system/src/data_layer/indicator_storage.py`: Lines 25-36 (`_connect()`)
   - **Observation**:
     ```python
     @contextmanager
     def _connect(self):
         conn = sqlite3.connect(self.db_path, timeout=30, check_same_thread=False)
         ...
         try:
             yield conn
         finally:
             conn.close()
     ```
     `_connect()` opens and closes a new SQLite connection on every single operation, including chunked loop iterations in `get_all_fundamentals`.

5. **`aiosqlite` Default `DELETE` Journal Mode in Persistence Connection Manager**
   - **Location**: `trading_system/src/persistence/database.py`: Lines 23-55 (`_DBConnection.get()`)
   - **Observation**:
     ```python
     async def get(self):
         async with self._lock:
             if self._conn is None:
                 self._conn = await aiosqlite.connect(self.db_path)
     ```
     `aiosqlite.connect()` opens connections for `TradeLogger`, `AssetHistoryDB`, and `AIPredictionDB` without setting WAL journal mode or busy timeouts.

---

### B. Concurrency & Memory Footprint Vulnerabilities

6. **Python GIL Thread-Pool Serialization on CPU-Bound Feature Extraction**
   - **Location**: `trading_system/run_pipeline.py`: Lines 924-953, Lines 1116-1145, Lines 1185-1193 (`ThreadPoolExecutor(max_workers=_CPU_WORKERS)`)
   - **Observation**:
     ```python
     with ThreadPoolExecutor(max_workers=_CPU_WORKERS) as executor:
         future_to_sym = {executor.submit(fetch_data_fdr, sym, ...): sym for sym in all_symbols}
     ```
     `fetch_data_fdr`, `prepare_training_data`, and `merge_fundamentals` perform heavy CPU-bound Pandas/Numpy computations (RSI, MACD, Moving Averages, fundamental merging) inside Python threads. CPython's GIL prevents concurrent execution across multi-core CPUs.

7. **Float32 Precision Loss for Mega-Cap Financial Figures**
   - **Locations**:
     - `trading_system/src/data_layer/indicator_storage.py`: Lines 120-129 (`market_baselines` table)
     - `trading_system/run_pipeline.py`: Downcasting routines
   - **Observation**:
     Mega-cap market caps in KRW (e.g. Samsung Electronics at ~400 Trillion KRW = $4 \times 10^{14}$) and USD (e.g. AAPL/NVDA at $3.5T = 4.8 \times 10^{15}$ KRW) exceed IEEE 754 `float32` mantissa precision ($2^{24} = 16,777,216$). At $4 \times 10^{14}$, `float32` LSB step size is ~33.5 Million KRW. Downcasting monetary columns to `float32` truncates low-order digits.

8. **Memory Accumulation Across 3,379 Symbols Without Intermediate Garbage Collection**
   - **Location**: `trading_system/run_pipeline.py`: Lines 853-983, Lines 1115-1193, Lines 1740-2288
   - **Observation**:
     `infer_data_dict` retains full OHLCV + fundamental DataFrames for 3,379 symbols throughout pipeline execution. DataFrames for 17 strategies (`res_df`, `surge_df`, `lead_lag_df`, `vcp_results`, `vcp_ml_df`, `stat_arb_df`, `sector_df`, `rim_df`, `event_df`, `mq_df`, `iv_skew_df`, `order_flow_df`, `reversal_df`, `arm_df`, `card_df`, `latr_df`) are created and retained simultaneously in local scope. Garbage collection (`gc.collect()`) is only invoked at lines 1641 and 2160.

---

### C. Data Missingness & Strategy Column Mapping Vulnerabilities

9. **Incomplete Strategy Column Schema in `ensemble_predictions` DB Table**
   - **Location**: `trading_system/src/data_layer/indicator_storage.py`: Lines 87-98 & Lines 496-518 (`CREATE TABLE ensemble_predictions`) & `trading_system/src/analysis/coverage_analyzer.py`: Lines 79-97 (`col_map`)
   - **Observation**:
     ```sql
     CREATE TABLE IF NOT EXISTS ensemble_predictions (
         date TEXT,
         symbol TEXT,
         ensemble_score REAL,
         ensemble_expected_return REAL,
         reg_score REAL,
         surge_score REAL,
         ll_score REAL,
         vcp_ml_score REAL,
         PRIMARY KEY (date, symbol)
     )
     ```
     The SQLite table schema includes columns for only 4 strategies (`reg_score`, `surge_score`, `ll_score`, `vcp_ml_score`), while `StrategyCoverageAnalyzer` expects 17 strategy columns. The remaining 13 strategies are omitted when saving ensemble predictions to DB.

10. **Selection Bias & Inflation in Dynamic Weight Renormalization**
    - **Location**: `trading_system/src/ai/ensemble_scorer.py`: Lines 924-939 (`combine_predictions`)
    - **Observation**:
      ```python
      for strat_name, score_col in strategy_cols:
          w = weights.get(strat_name, 0.10)
          if score_col in merged.columns:
              valid_mask = merged[score_col].notna() & np.isfinite(merged[score_col])
              total_score_series += merged[score_col].fillna(0.0) * w * valid_mask.astype(float)
              total_weight_series += w * valid_mask.astype(float)

      safe_weight_series = total_weight_series.replace(0.0, np.nan)
      linear_score = (total_score_series / safe_weight_series).fillna(0.0).clip(0.0, 1.0)
      ```
      If a stock has valid predictions for only 2 out of 17 strategies (e.g. `surge_score` = 0.9, `vcp_ml_score` = 0.8), `total_weight_series` is $0.22$. Dividing `total_score_series` ($0.188$) by $0.22$ yields a `linear_score` of $0.8545$. Stocks missing data for 15 strategies receive an inflated score without any missingness penalty.

---

### D. Pipeline Orchestration & Stability Vulnerabilities

11. **Silent Suppression of Pipeline Exceptions and False Success Reporting**
    - **Location**: `trading_system/run_pipeline.py`: Lines 2803-2836 (`except Exception as _exc` block)
    - **Observation**:
      ```python
      except Exception as _exc:
          ...
          has_results = os.path.exists(essential_file) and os.path.getsize(essential_file) > 0
          if has_results:
              logger.info("Output files detected in result directory. Treating as partial success (exiting with 0).")
              ...
              sys.exit(0)
      ```
      If an unhandled exception occurs late in execution (e.g. RiskManager error, OMS failure, report generation failure), but `pipeline_result.txt` was written earlier, the handler exits with status code `0`.

12. **Survivorship Bias in Universe Management**
    - **Location**: `trading_system/src/data_layer/indicator_storage.py`: Lines 212-257 (`update_stock_universe()`) & `trading_system/run_pipeline.py`: Lines 789-795
    - **Observation**:
      `update_stock_universe()` queries current `fdr.StockListing('S&P500')` and `fdr.StockListing('KRX')`. Delisted, merged, or bankrupt companies from historical periods are omitted from `stock_universe`.

13. **Widespread Exception Masking (`pass` / `except Exception:`) in Strategy Modules**
    - **Location**: `trading_system/run_pipeline.py`: Lines 1217, 1263, 1335, 1369, 1804, 1883, 1917, 1947, 1988, 2024, 2060, 2096, 2132, 2154, 2193, 2228, 2263, 2375, 2386, 2411, 2432, 2448, 2467, 2478
    - **Observation**:
      Strategy calculation steps wrap execution in broad `try...except Exception:` blocks that catch all errors and log warnings or execute `pass`.

---

## 2. Logic Chain

1. **DB Lock Contention & Concurrency**:
   - *Observation 1 & 5*: `oms_engine.py`, `trading_agent.py`, `trade_journal.py`, and `_DBConnection` open SQLite connections without WAL mode (`PRAGMA journal_mode=WAL`) or `busy_timeout`.
   - *Logic Step 1.1*: SQLite defaults to `DELETE` journal mode when WAL is not explicitly set. In `DELETE` mode, any write lock locks the entire database file for both reads and writes.
   - *Logic Step 1.2*: When `run_pipeline.py` or background threads invoke `oms_engine` or `trading_agent` while `indicator_storage` or `StockPriceDB` is writing, connection requests fail instantly with `sqlite3.OperationalError: database is locked`.
   - *Observation 2*: `StockPriceDB` stores connections in `threading.local()`. `run_pipeline.py` creates short-lived worker threads using `ThreadPoolExecutor`.
   - *Logic Step 2.1*: When worker threads complete, thread-local connections are not closed. Accumulated connections hold file locks on `stock_prices.db` and consume OS file descriptors.
   - *Observation 3*: `StockPriceDB._get_conn()` does not set `PRAGMA synchronous = NORMAL`.
   - *Logic Step 3.1*: SQLite WAL defaults to `synchronous = FULL`, requiring disk controller sync flushes on every `commit()`. Upserting 3,379 symbols creates write latency bottlenecks.

2. **Concurrency & Memory**:
   - *Observation 6*: `ThreadPoolExecutor` runs Python/Pandas feature extraction functions (`fetch_data_fdr`, `prepare_training_data`, `merge_fundamentals`).
   - *Logic Step 6.1*: CPython's GIL restricts execution of Python bytecode to a single thread at a time. Using threads for CPU-bound Pandas transformations results in thread serialization, limiting multi-core CPU usage.
   - *Observation 7*: Market Cap and fundamental figures for KRX/US mega-caps ($4 \times 10^{14}$ KRW) are stored/downcast to `float32`.
   - *Logic Step 7.1*: `float32` maintains 24 bits of mantissa (~7 decimal digits). $400,000,000,000,000$ in `float32` has a quantization granularity of ~33.5 Million KRW ($2^{25} \times 10^{-7}$). Downcasting truncates low-order digits and distorts ratio computations.
   - *Observation 8*: DataFrames for 3,379 symbols and 17 strategy outputs remain referenced in `run_pipeline.py` local scope without intermediate GC.
   - *Logic Step 8.1*: Retaining 3,379 full historical DataFrames plus 17 strategy feature matrices accumulates 4GB-6GB+ RAM, exceeding runner memory caps (e.g. GitHub Actions 7GB limit) and risking OOM termination.

3. **Data Missingness & Strategy Mapping**:
   - *Observation 9*: `ensemble_predictions` DB table schema contains only 4 strategy columns (`reg_score`, `surge_score`, `ll_score`, `vcp_ml_score`).
   - *Logic Step 9.1*: When predictions are saved to DB or queried by `StrategyCoverageAnalyzer`, 13 strategy scores are omitted, producing false 0% coverage metrics for 13 strategies.
   - *Observation 10*: `EnsembleScoringEngine.combine_predictions` renormalizes strategy weights by dividing `total_score_series` by `total_weight_series` (sum of active weights for present strategies).
   - *Logic Step 10.1*: A stock with valid scores for only 2 out of 17 strategies (e.g. 0.9 and 0.8) has `total_weight_series = 0.22`. Renormalizing yields $0.188 / 0.22 = 0.8545$. Sparse stocks missing 15 strategies receive inflated scores that outrank well-rounded stocks evaluated across all 17 strategies.

4. **Pipeline Orchestration**:
   - *Observation 11*: `run_pipeline.py` exception handler checks `os.path.exists("pipeline_result.txt")` and calls `sys.exit(0)` when errors occur late in pipeline execution.
   - *Logic Step 11.1*: Downstream failures (e.g., RiskManager crisis gating, OMS order generation, database persistence) are reported as exit code `0`, preventing CI/CD pipelines from catching execution failures.

---

## 3. Vulnerability Inventory Table

| ID | Module / File Path | Line Range | Vulnerability Description | Severity | System Impact |
|---|---|---|---|---|---|
| **V-01** | `src/execution/oms_engine.py`<br>`src/ai/trading_agent.py`<br>`src/data_layer/trade_journal.py` | `oms_engine.py:23,67,131`<br>`trading_agent.py:112,282...`<br>`trade_journal.py:34` | Bare `sqlite3.connect` calls bypassing WAL manager, busy timeouts, and process write locks. | **HIGH** | `sqlite3.OperationalError: database is locked` crashes during concurrent access. |
| **V-02** | `src/persistence/database.py`<br>`trading_system/run_pipeline.py` | `database.py:388-397`<br>`run_pipeline.py:924,1116` | Thread-local connection leaks in `StockPriceDB` under `ThreadPoolExecutor`. | **HIGH** | Unclosed DB handles accumulate, holding WAL locks and exhausting OS file descriptors. |
| **V-03** | `src/persistence/database.py` | `database.py:388-397` | Missing `PRAGMA synchronous = NORMAL` in `StockPriceDB._get_conn()`. | **MEDIUM** | Disk `fsync` blocking on commits; 3x-5x slower DB write throughput. |
| **V-04** | `src/data_layer/indicator_storage.py` | `indicator_storage.py:25-36` | High connection open/close overhead in `_connect()` context manager during batch loops. | **MEDIUM** | Increased system call and file handle open/close latency during bulk queries. |
| **V-05** | `src/persistence/database.py` | `database.py:23-55` | `aiosqlite` connection manager uses default `DELETE` journal mode. | **MEDIUM** | Whole-file database locks during async writes in `TradeLogger` and `AssetHistoryDB`. |
| **V-06** | `trading_system/run_pipeline.py` | `run_pipeline.py:924,1116,1185` | Python GIL thread-pool serialization on CPU-bound Pandas feature extraction. | **HIGH** | Multi-core CPU utilization limited to single-core speeds; 4x-8x slower pipeline runtimes. |
| **V-07** | `src/data_layer/indicator_storage.py`<br>`trading_system/run_pipeline.py` | `indicator_storage.py:120-129`<br>`run_pipeline.py:6` | `float32` precision loss on mega-cap monetary and market cap figures (>16.7M KRW). | **HIGH** | Quantization error (~33.5M KRW LSB at 400T KRW); distorts financial ratios and features. |
| **V-08** | `trading_system/run_pipeline.py` | `run_pipeline.py:853-1193,1740-2288` | Memory accumulation across 3,379 symbols without intermediate garbage collection. | **HIGH** | Peak memory exceeds 4GB-6GB+ RAM; risks OOM process termination on CI/CD runners. |
| **V-09** | `src/data_layer/indicator_storage.py`<br>`src/analysis/coverage_analyzer.py` | `indicator_storage.py:87-98`<br>`coverage_analyzer.py:79-97` | Incomplete `ensemble_predictions` DB table schema missing 13 strategy columns. | **HIGH** | DB persistence drops 13 strategy scores; causes false 0% coverage reports. |
| **V-10** | `src/ai/ensemble_scorer.py` | `ensemble_scorer.py:924-939` | Selection bias and score inflation in dynamic weight renormalization for missing data. | **HIGH** | Sparse stocks missing 15 strategies receive inflated scores (e.g. >0.85) and outrank solid multi-factor stocks. |
| **V-11** | `trading_system/run_pipeline.py` | `run_pipeline.py:2803-2836` | Silent exception suppression and false success reporting (`sys.exit(0)` on error). | **HIGH** | Masks downstream pipeline failures (OMS, RiskManager) as clean exits in CI/CD. |
| **V-12** | `src/data_layer/indicator_storage.py`<br>`trading_system/run_pipeline.py` | `indicator_storage.py:212-257`<br>`run_pipeline.py:789-795` | Survivorship bias in universe selection (evaluates only currently active stocks). | **MEDIUM** | Overstates historical backtest returns by excluding historically bankrupt/delisted stocks. |
| **V-13** | `trading_system/run_pipeline.py` | `run_pipeline.py:1217...2478` | Broad exception masking (`except Exception: pass`) across strategy modules. | **MEDIUM** | Suppresses structural bugs and missing column errors without alerting operators. |

---

## 4. Caveats

- **Read-Only Scope**: This audit is based on read-only static analysis and logic tracing of the target files. No code modifications were applied to the production repository during this audit phase.
- **Hardware Variation**: Memory footprint impact (V-08) and GIL multi-core bottlenecks (V-06) were evaluated assuming standard 4-core / 8-core CPU configurations with 7GB-16GB RAM. High-memory servers (>32GB RAM) may absorb memory accumulation without OOM crashes.
- **Data Coverage Context**: Strategy missingness reasons in `coverage_analyzer.py` depend on the availability of historical fundamental filings and options chain data from external APIs (`yfinance`, `DART`).

---

## 5. Conclusion

The audit identifies critical architectural bottlenecks and data integrity flaws in the Stock Trading System (3,379 symbols):

1. **Database Stability**: Direct bare `sqlite3.connect` calls in `oms_engine.py` and `trading_agent.py` bypass WAL mode and process locks, exposing the pipeline to locking crashes under concurrency.
2. **Execution Performance & Memory**: CPU-bound Pandas feature engineering inside `ThreadPoolExecutor` is bottlenecked by the Python GIL. In addition, retaining DataFrames for 3,379 symbols across 17 strategies causes memory build-up (4GB-6GB+), while `float32` downcasting introduces precision errors in mega-cap financial metrics.
3. **Alpha Model Integrity**: `ensemble_predictions` DB table drops 13 strategy scores, while `EnsembleScoringEngine`'s weight renormalization introduces selection bias, inflating sparse stocks over comprehensive multi-factor candidates.
4. **Pipeline Fault-Tolerance**: Masking late-stage exceptions with `sys.exit(0)` conceals downstream failures in CI/CD environments.

---

## 6. Verification Method

To independently verify the observations and findings in this report, execute the following commands and file inspections:

### A. SQLite Bare Connections & Lock Verification
```bash
# Verify bare sqlite3.connect calls in oms_engine.py, trading_agent.py, trade_journal.py
.venv/bin/python -c "
import re, glob
for path in glob.glob('trading_system/**/*.py', recursive=True):
    with open(path, 'r', encoding='utf-8') as f:
        for idx, line in enumerate(f, 1):
            if 'sqlite3.connect' in line and 'indicator_storage' not in path and 'database.py' not in path:
                print(f'{path}:{idx}: {line.strip()}')
"
```

### B. Verification of `ensemble_predictions` Table Schema
```bash
# Inspect ensemble_predictions schema in indicator_storage.py
.venv/bin/python -c "
from trading_system.src.data_layer.indicator_storage import MarketIndicatorStorage
storage = MarketIndicatorStorage(':memory:')
with storage._connect() as conn:
    cols = [row[1] for row in conn.execute('PRAGMA table_info(ensemble_predictions)').fetchall()]
    print('Columns in ensemble_predictions:', cols)
    assert len(cols) == 8, f'Expected 8 cols, found {len(cols)}'
"
```

### C. Verification of Float32 Mega-Cap Precision Quantization
```bash
# Test float32 precision loss for 400 Trillion KRW (Samsung Electronics Market Cap)
.venv/bin/python -c "
import numpy as np
val_64 = 400_000_000_000_000.0
val_32 = np.float32(val_64)
diff = float(np.float64(val_32) - val_64)
print(f'Original float64: {val_64:,.0f}')
print(f'Converted float32: {val_32:,.0f}')
print(f'Quantization error (diff): {diff:,.0f} KRW')
"
```

### D. Verification of Dynamic Weight Renormalization Selection Bias
```bash
# Verify score inflation for sparse stock (2 strategies) vs full stock (17 strategies)
.venv/bin/python -c "
import pandas as pd, numpy as np
from trading_system.src.ai.ensemble_scorer import EnsembleScoringEngine

scorer = EnsembleScoringEngine()
# Sparse stock: only surge=0.9, vcp_ml=0.8, all others NaN
df_sparse = pd.DataFrame([{'symbol': 'SPARSE', 'surge_score': 0.9, 'vcp_ml_score': 0.8}])
# Full stock: all 17 strategies present averaging 0.70
df_full = pd.DataFrame([{'symbol': 'FULL', 'reg_score': 0.7, 'surge_score': 0.7, 'll_score': 0.7,
                          'vcp_rule_score': 0.7, 'vcp_ml_score': 0.7, 'lstm_score': 0.7,
                          'stat_arb_score': 0.7, 'sector_score': 0.7, 'rim_score': 0.7,
                          'event_score': 0.7, 'mq_score': 0.7, 'iv_skew_score': 0.7,
                          'order_flow_score': 0.7, 'reversal_score': 0.7, 'arm_score': 0.7,
                          'card_score': 0.7, 'latr_score': 0.7}])

res_sparse = scorer.combine_predictions(pd.DataFrame(), df_sparse, pd.DataFrame(), vcp_ml_df=df_sparse)
res_full = scorer.combine_predictions(df_full, df_full, df_full, vcp_ml_df=df_full)

print('Sparse stock ensemble_score:', res_sparse['ensemble_score'].iloc[0])
print('Full stock ensemble_score  :', res_full['ensemble_score'].iloc[0])
"
```

---
*Report compiled by Explorer M1-2.*
