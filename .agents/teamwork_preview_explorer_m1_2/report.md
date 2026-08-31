# Milestone 1 Investigation Report: Data Seeding & 5-Market Storage Integrity (R1, F01, F02)

**Author:** Explorer (teamwork_preview_explorer_m1_2)  
**Date:** 2026-08-31  
**Project:** Stock Trading System  
**Working Directory:** `d:\Finance\code\stock\.agents\teamwork_preview_explorer_m1_2\`  
**Target Milestone:** Milestone 1 (R1: Data Seeding & 5-Market Storage Integrity, F01, F02)

---

## 1. Executive Summary

Milestone 1 focuses on ensuring the end-to-end data integrity of the 5-market trading pipeline (SP500, NASDAQ, RUSSELL2000, KOSPI, KOSDAQ) across local execution and GitHub Actions workflows (`.github/workflows/preseed.yml`, `training.yml`, `pipeline.yml`). 

The system relies on a dual SQLite persistence architecture (`stock_prices.db` for price histories and `market_indicators.db` for universe listings, macro indicators, and fundamentals) backed by WAL (Write-Ahead Logging), mutex locking, and exponential backoff retries. In GitHub Actions, data caching and artifact synchronization allow matrix jobs to run concurrently without duplicate fetching or OOM crashes.

Our investigation confirmed the robust design of the core data seeding, dynamic filing lag, and Azure Blob redirect handlers, while identifying two critical GHA workflow issues (Feature F02) and specific edge cases that need attention during Worker implementation.

---

## 2. 5-Market Universe Seeding & Storage Architecture

### 2.1 Universe Fetching & Normalization (`StockUniverseManager` in `src/data_layer/indicator_storage.py`)
- **SP500**: Fetched via `FinanceDataReader.StockListing('S&P500')` with 3-attempt exponential retry. Ticker symbols and GICS sector/industry classifications are recorded.
- **NASDAQ**: Fetched via `FinanceDataReader.StockListing('NASDAQ')`. Cross-listed S&P500 stocks maintain primary SP500 classification to prevent dual counting.
- **RUSSELL2000**: Fetched via iShares Russell 2000 ETF holdings CSV (`IWM_holdings`), with automatic Tier-2 fallback to `NYSE` + `NASDAQ` listings excluding S&P500 and large-cap mega tickers (`_EXCLUDE_FALLBACK_TICKERS`).
- **KOSPI & KOSDAQ**: Fetched via `FinanceDataReader.StockListing('KRX')`. 6-digit numeric ticker codes are standardized with zero-padding (e.g. `'005930'`). Administrative items (`KRX-ADMINISTRATIVE`) and trading-halted stocks are automatically excluded from inference.
- **Storage Target**: `market_indicators.db` in table `stock_universe (symbol TEXT PRIMARY KEY, name TEXT, market TEXT, sector TEXT, industry TEXT)` with indexed market column.

### 2.2 Global Macro Indicators (`GlobalMarketClient` & `MacroIndicatorStore`)
- Macro indicators (`^VIX`, `USDKRW=X`, `^TNX`, `CL=F`, `GC=F`, `^GSPC`, `^IXIC`, `^RUT`, `^KS11`, `^KQ11`, `DX-Y.NYB`) are fetched with adaptive timeout and exponential backoff jitter.
- Corrupted anomaly values are filtered out using `INDICATOR_VALUE_BOUNDS` (e.g., VIX in `[5.0, 120.0]`, USD/KRW in `[900.0, 2500.0]`).
- Stored into `market_indicators.db` in table `global_indicators (date TEXT, symbol TEXT, name TEXT, price REAL, change_pct REAL, PRIMARY KEY (date, symbol))`.

### 2.3 Historical Prices Cache (`StockPriceDB` in `src/persistence/database.py`)
- OHLCV price series are stored in `stock_prices.db` in table `stock_prices (symbol, date, open, high, low, close, volume, updated_at, PRIMARY KEY (symbol, date))`.
- Validation invariants:
  - `DataValidator.validate_and_clean_price_series` detects transient single-day price spikes (>65%) and interpolates clean OHLC values.
  - Forward/reverse stock split detection guards against unadjusted historical series.
  - Consistency rule: `Low <= Open, Close <= High`, `Low >= 1e-4`.
- Batch Upsert: `update_prices_batch` aggregates multiple symbol series and performs an atomic `executemany` inside a shared mutex lock with `execute_sqlite_with_retry`.

---

## 3. GitHub Actions Workflows Analysis

| Workflow | Trigger | Matrix Targets | Key Roles & Actions | Status / Issues Identified |
|---|---|---|---|---|
| `.github/workflows/preseed.yml` | Daily 16:00 UTC (01:00 KST) | `SP500, NASDAQ, RUSSELL2000, KOSPI, KOSDAQ` | Preseeds price & indicator DB caches; runs `run_pipeline.py --skip-training --skip-inference`; uploads `stock-databases-${target}` artifact | ✅ Fully functional. Models & DB caches have appropriate `restore-keys`. |
| `.github/workflows/training.yml` | Weekly Sat 11:30 UTC (20:30 KST) | `SP500, NASDAQ, RUSSELL2000, KOSPI, KOSDAQ` | Trains regression, surge, VCP ML, LSTM, and Isotonic calibrators; saves models to `trading_system/models/` | ⚠️ **Issue 1 (F02)**: Step `Cache AI models` lacks `restore-keys`. If today's exact key misses, no previous weights are restored. |
| `.github/workflows/pipeline.yml` | Daily Mon-Fri 11:30 UTC (20:30 KST) | `SP500, NASDAQ, RUSSELL2000, KOSPI, KOSDAQ` | 1. Matrix inference runs `run_pipeline.py --skip-training`<br>2. `merge-and-release` consolidates per-market predictions<br>3. `deploy-pages` builds HTML dashboard | ⚠️ **Issue 2 (F02)**: Step Summary loop (line 193) and Release upload loop (line 333) omitted `lstm_predictions.txt`. |

---

## 4. Deep Dive on Critical Edge Cases

### 4.1 Dynamic Regulatory Filing Lag (`src/data_layer/earnings_data.py`)
- **Mechanism**:
  - KRX Statutory filing deadline: 45 calendar days for quarterly reports (1Q/2Q/3Q), 90 calendar days for annual report (12M).
  - US SEC Statutory filing deadline: 40 calendar days for Form 10-Q (quarterly), 60 calendar days for Form 10-K (annual).
- **Implementation**:
  ```python
  def compute_regulatory_filing_lag(period_end_date: Any, period_type: str = 'quarterly', is_krx: bool = True) -> str:
      ts = pd.to_datetime(period_end_date)
      is_year_end = (str(period_type).lower() == 'annual') or (ts.month == 12)
      if is_krx:
          lag_days = 90 if is_year_end else 45
      else:
          lag_days = 60 if is_year_end else 40
      return str((ts + pd.Timedelta(days=lag_days)).strftime('%Y-%m-%d'))
  ```
- **Integrity Verification**:
  - `_fetch_fundamentals_network` checks `yf_sym.endswith(('.KS', '.KQ'))` to determine market jurisdiction.
  - Generates `date_available` column on fundamentals data.
  - Ensures point-in-time training and inference strictly filter `date_available <= as_of_date`, eliminating forward-looking fundamental leakage.

### 4.2 Azure Blob SAS Redirect Token Stripping (`trading_system/download_db.py`)
- **Problem**: When downloading GitHub Action artifact ZIPs via `https://api.github.com/repos/{repo}/actions/artifacts/{artifact_id}/zip`, GitHub returns an HTTP 302 redirect with a pre-signed Azure Blob SAS URL. Standard Python `urllib` / `requests` forwards the `Authorization: Bearer {GITHUB_TOKEN}` header across the redirect, which Azure Blob Storage rejects with `401 AuthenticationFailed`.
- **Solution**:
  `download_db.py` uses a custom `_NoRedirectHandler` (lines 93-118) to capture HTTP 301/302/303/307/308 without following the redirect, extracts the signed `Location` URL, and executes a second request to Azure Blob Storage *without* the `Authorization` header.
- **Robustness**: Handles both direct downloads and redirects, supports fallback matching from `stock-databases-{target}` to `stock-databases*`, and gracefully handles empty artifact responses without failing the pipeline.

### 4.3 SQLite WAL Locks, Concurrency, and File Descriptors
- **WAL Configuration**:
  - Both `StockPriceDB` and `MarketIndicatorStorage` execute:
    - `PRAGMA journal_mode=WAL`
    - `PRAGMA synchronous=NORMAL`
    - `PRAGMA busy_timeout=30000` (30s)
    - `PRAGMA cache_size=-32000` (32MB)
    - `PRAGMA temp_store=MEMORY`
- **Lock Coordination**:
  - Intra-process thread concurrency uses `_SHARED_WRITE_LOCK = threading.Lock()`.
  - Storage write calls are wrapped in `execute_sqlite_with_retry` with exponential backoff and random jitter (up to 10 retries, max delay 500ms).
  - `ParquetWALBuffer` provides a lock-free staging buffer in `data/wal_staging/*.parquet` for multi-threaded downloads.
  - `MarketIndicatorStorage.close()` executes `PRAGMA wal_checkpoint(TRUNCATE)` to prevent WAL disk bloat.
  - SQLite query parameter chunking: `get_all_fundamentals` chunks lists of symbols into blocks of 900 to ensure queries stay below the SQLite 999 parameter limit.

---

## 5. Worker Recommendations & Action Plan (F01, F02)

### Action Item 1: Patch `training.yml` Models Cache Key (F02)
In `.github/workflows/training.yml` (around line 118):
Add `restore-keys` to `models-cache` so that weekly model training builds on the latest existing model checkpoint if an exact date match is not found:
```yaml
      - name: Cache AI models (Restore and Save)
        uses: actions/cache@v4
        id: models-cache
        with:
          path: trading_system/models
          key: ai-models-${{ matrix.target }}-${{ steps.date.outputs.date }}
          restore-keys: |
            ai-models-${{ matrix.target }}-
            ai-models-
```

### Action Item 2: Add `lstm_predictions.txt` to `pipeline.yml` Loops (F02)
In `.github/workflows/pipeline.yml`:
1. In `Write Step Summary` file list (line 193), add `lstm_predictions.txt`.
2. In `Create GitHub Release and Upload Assets` file list (lines 333-345), add `lstm_predictions.txt`.

### Action Item 3: Validate 5-Market Pipeline Integrity (F01)
Verify that when running `run_pipeline.py --target {MARKET}`, each of `SP500`, `NASDAQ`, `RUSSELL2000`, `KOSPI`, and `KOSDAQ` properly seeds data, extracts fundamentals with the appropriate filing lag, and produces valid output files.

---

## 6. Verification Method

To independently verify Milestone 1 changes:
```powershell
# 1. Run database and concurrency unit tests
.venv\Scripts\pytest tests/test_database.py tests/test_database_concurrency.py tests/test_multi_market_expansion.py -v

# 2. Run indicator storage and data layer tests
.venv\Scripts\pytest tests/test_indicator_storage.py tests/test_dart_fundamental_fetcher.py -v

# 3. Test multi-market ticker resolution and filing lag calculation
.venv\Scripts\pytest tests/test_all_16_markets_31_strategies.py -v

# 4. Dry-run pipeline target filtering
.venv\Scripts\python trading_system/run_pipeline.py --skip-training --skip-inference --target KOSPI --debug
```
