# Software Architecture & CI/CD Pipeline Audit Report

**System**: Stock Trading System (3,379 symbols across SP500, NASDAQ, RUSSELL2000, KOSPI, KOSDAQ)  
**Audit Scope**: Pipeline Automation & Orchestration, Database & SQLite WAL Concurrency, Artifact Aggregation & Output Resilience  
**Auditor**: Explorer 2 (Software Architecture & GHA Workflow Specialist)  
**Date**: 2026-08-05  

---

## Executive Summary

A comprehensive read-only software architecture and CI/CD pipeline audit of the Stock Trading System was conducted. The audit analyzed the orchestrator execution flow (`trading_system/run_pipeline.py`), GitHub Actions workflows (`.github/workflows/`), SQLite WAL database concurrency mechanisms (`trading_system/src/persistence/database.py` and `trading_system/src/data_layer/indicator_storage.py`), artifact aggregation logic (`trading_system/merge_predictions.py`), and GitHub Pages report generation (`trading_system/generate_report.py` and `trading_system/scripts/verify_gha_artifacts.py`).

Key Findings:
1. **Pipeline Automation & Orchestration**: High structural efficiency achieved via matrix parallelization across 5 markets (`SP500`, `NASDAQ`, `RUSSELL2000`, `KOSPI`, `KOSDAQ`) and strict separation of weekend training (`training.yml`) vs daily inference (`pipeline.yml`). However, an exception resilience pattern in `run_pipeline.py` (exiting with code 0 on partial success when `pipeline_result.txt` exists) carries a risk of masking partial strategy generation failures in matrix GHA runs.
2. **Database & SQLite WAL Concurrency**: SQLite WAL mode (`PRAGMA journal_mode=WAL`), 5000ms busy timeouts, and python `threading.Lock()` write mutex protection successfully prevent database locking errors during local multi-threaded execution (`ThreadPoolExecutor`). Inter-process lock contention between GHA matrix jobs is eliminated by GHA's runner container isolation architecture.
3. **Artifact Aggregation & Output Resilience**: Multi-market split artifact generation and post-pipeline merging (`merge_predictions.py`) operate reliably with pre-read memory caching, cross-market allocation deduplication, resilient regex parsing, and KST timestamping. Stale deployment guard mechanisms in `pipeline.yml` prevent corrupted or empty releases to GitHub Pages.

---

## 1. Pipeline Automation & Orchestration Audit

### 1.1 Weekend Model Training vs. Daily Split Market Inference Architecture

The CI/CD pipeline is split into two primary automated workflows defined in `.github/workflows/`:

#### A. Weekend Model Training Workflow (`training.yml`)
- **Trigger**: Schedule cron `'30 11 * * 6'` (Saturdays 11:30 UTC / 20:30 KST) & `workflow_dispatch`.
- **Configuration**:
  - `SKIP_TRAINING: 'False'`
  - `SKIP_INFERENCE: 'True'`
  - Strategy matrix across 5 target markets: `[SP500, NASDAQ, RUSSELL2000, KOSPI, KOSDAQ]`.
- **Execution Flow**:
  1. Restores historical `stock_prices.db` and `market_indicators.db` from shared GitHub Actions cache (`key: stock-prices-db-${{ steps.date.outputs.date }}`).
  2. Executes full model training per market target (`run_pipeline.py`).
  3. Saves trained models to `trading_system/models/`.
  4. Saves trained model files to target-specific GHA cache (`ai-models-${{ matrix.target }}-${{ steps.date.outputs.date }}`).

#### B. Daily Inference Workflow (`pipeline.yml`)
- **Trigger**: Schedule cron `'30 11 * * 1-5'` (Monday–Friday 11:30 UTC / 20:30 KST) & `push` on main/master & `workflow_dispatch`.
- **Configuration**:
  - `SKIP_TRAINING: 'True'`
  - Strategy matrix across 5 target markets: `[SP500, NASDAQ, RUSSELL2000, KOSPI, KOSDAQ]`.
- **Execution Flow**:
  1. Restores SQLite DB caches (`stock_prices.db`, `market_indicators.db`).
  2. Restores pre-trained AI model cache using `actions/cache/restore@v4` with key prefix `ai-models-${{ matrix.target }}-`.
  3. Runs daily prediction pipeline (`run_pipeline.py`) per market target.
  4. Renames output text prediction files into `trading_system/result_split/*_${MARKET}.txt`.
  5. Uploads split artifacts (`result-${{ matrix.target }}`).

#### C. Architectural Evaluation
- **Memory & Resource Efficiency**: Splitting inference by `INFERENCE_TARGET` limits in-memory DataFrame operations to a single market's symbol set per GHA runner, preventing Out-Of-Memory (OOM) crashes during feature generation.
- **Parallelization Speedup**: Running 5 concurrent matrix jobs reduces total pipeline wall-clock execution time from > 150 minutes to ~20–30 minutes.

### 1.2 Execution Order, Multithreading & Process Control

#### A. Pipeline Execution Sequence in `run_pipeline.py`
1. **Configuration & Global Indicators**: Initializes `TradingConfig`, fetches global macro indicators (VIX, TNX, USDKRW, WTI, Gold) via `GlobalMarketClient`, and persists raw indicators into `MarketIndicatorStorage`.
2. **Universe Management**: Updates 3,379 stock universe symbols and filters out administrative/suspended KRX symbols (`fdr.StockListing('KRX-ADMINISTRATIVE')`).
3. **Data Prefetching**: Prefetches historical OHLCV price data and fundamental metrics. Uses `DataValidator` quality gates to reject invalid/zero price series.
4. **18-Strategy Signal Generation**:
   - XGBoost Regression & Surge Classifier
   - Lead-Lag 2-Tier Shift Matrix
   - VCP Pattern & VCP ML Classifier
   - Strict Causal LSTM
   - Stat-Arb Cointegration Scanning
   - Sector Rotation Relative Momentum
   - RIM Intrinsic Valuation
   - Event-Driven Catalysts
   - Momentum Quality (MQ) Factor
   - Options IV Skew
   - Order Flow Imbalance (MFI)
   - Short-Term Reversal
   - Analyst Revision Momentum (ARM)
   - Cross-Asset Regime Divergence (CARD)
   - Liquidity-Adjusted Tail Risk (LATR)
   - Institutional & Foreign Sector Flows
5. **Regime Gating & Dynamic Ensemble Scoring**: Invokes 2D Market Regime Detector and `EnsembleScoringEngine` to compute Gram-Schmidt orthogonalized factor weights, deduct microstructure transaction costs (STT 0.18%, bid-ask spread, market impact), and output dynamic ensemble scores.
6. **Result Serialization**: Writes prediction text files to `trading_system/result/` and updates `gh-pages/index.html`.

#### B. Multithreading (`ThreadPoolExecutor`) Implementation
- **Worker Configuration**: Uses `_CPU_WORKERS = max(1, os.cpu_count())`.
- **Parallel Tasks**:
  - Global indicator downloads (`max_workers=len(_INDICATOR_TICKERS)`).
  - Price prefetching (`max_workers=_CPU_WORKERS * 2`).
  - Feature computation & fundamental fetching (`max_workers=_CPU_WORKERS`).
- **Rate Limiting Protection**: Thread calls to Yahoo Finance and FinanceDataReader are throttled by `get_global_rate_limiter()` and `_rate_lock` to prevent 429 HTTP rate-limit errors.

#### C. Exception Resilience & Return Code Analysis
- In `run_pipeline.py` (lines 3173–3206):
```python
except Exception as _exc:
    result_dir = os.environ.get("OUTPUT_RESULT_DIR", os.path.join(os.path.dirname(__file__), "result"))
    essential_file = os.path.join(result_dir, "pipeline_result.txt")
    has_results = os.path.exists(essential_file) and os.path.getsize(essential_file) > 0

    if has_results:
        logger.info("Output files detected in result directory. Treating as partial success (exiting with 0).")
        _notify_telegram(...)
        sys.exit(0)
    else:
        _notify_telegram(...)
        sys.exit(1)
```
- **Audit Assessment**:
  - *Strength*: Prevents GHA pipeline hard failures when non-critical downstream steps fail after essential regression results are written.
  - *Risk*: Returning exit code 0 when `pipeline_result.txt` exists can hide crashes in later strategies (e.g. failure during `ensemble_predictions.txt` or `strategy_data_coverage_report.txt` generation). GHA considers the step successful, which can lead to incomplete data in merged releases.

---

## 2. Database & SQLite WAL Concurrency Audit

### 2.1 Architecture & Database Schemas

The system employs SQLite databases located in `trading_system/`:
1. `stock_prices.db` (`StockPriceDB` in `src/persistence/database.py`): Caches daily OHLCV prices and volume for all symbols.
2. `market_indicators.db` (`MarketIndicatorStorage` in `src/data_layer/indicator_storage.py`): Stores stock universe, global indicators, fundamentals, AI predictions, post-market rankings, ensemble scores, pipeline run metrics, and filing sentiment cache.
3. `trade_logs.db` (`TradeLogger`): Execution logs, order tracking, real vs theoretical slippage.
4. `asset_history.db` (`AssetHistoryDB`): Daily asset portfolio snapshot tracking.
5. `ai_predictions.db` (`AIPredictionDB`): Historical prediction accuracy evaluation.

### 2.2 Concurrency & Lock Mutex Mechanism Analysis

| Metric / Mechanism | `StockPriceDB` Implementation | `MarketIndicatorStorage` Implementation |
|-------------------|-------------------------------|-----------------------------------------|
| Journal Mode | `PRAGMA journal_mode=WAL` | `PRAGMA journal_mode=WAL` |
| Busy Timeout | `PRAGMA busy_timeout=5000` (5s) | `PRAGMA busy_timeout=5000` (5s) |
| Cache & Memory | `cache_size=-500000` (500MB), `temp_store=MEMORY`, `mmap_size=2GB` | `cache_size=-50000` (50MB), `temp_store=MEMORY`, `synchronous=NORMAL` |
| Connection Model | Thread-local connections via `threading.local()` | Context manager `_connect()` per operation |
| Write Lock Mutex | `self._write_lock = threading.Lock()` | `self._write_lock = threading.Lock()` |
| Retry Mechanism | `execute_sqlite_with_retry` helper | `execute_sqlite_with_retry` helper |

#### Evaluation of Concurrency Safety:
1. **Intra-Process Thread Safety**: When `run_pipeline.py` executes multi-threaded tasks (`ThreadPoolExecutor`), python's `threading.Lock()` (`self._write_lock`) serializes all SQLite write transactions. This eliminates `sqlite3.OperationalError: database is locked` errors during parallel price or fundamental updates.
2. **Inter-Process GHA Isolation**: In GitHub Actions matrix runs, each target market (`SP500`, `KOSPI`, etc.) executes in a completely isolated virtual runner container with its own independent disk filesystem. Thus, multi-process SQLite write locking issues between matrix jobs do not occur.

---

## 3. Artifact Aggregation & Output Resilience Audit

### 3.1 Per-Market Split Result Serialization

During daily pipeline execution, `run_pipeline.py` outputs strategy text files to `trading_system/result/`:
- `pipeline_result.txt`
- `ensemble_predictions.txt`
- `strategy_data_coverage_report.txt`
- `portfolio_allocation.txt`
- `surge_predictions.txt`
- `lead_lag_predictions.txt`
- `vcp_patterns.txt`
- `vcp_ml_predictions.txt`
- `stat_arb_predictions.txt`
- 11 individual factor prediction files (`sector_predictions.txt`, `rim_predictions.txt`, etc.)

GHA step `Rename output files to avoid conflicts` copies these files to `trading_system/result_split/` appended with `_${MARKET}.txt` and uploads them as GHA artifacts (`result-${{ matrix.target }}`).

### 3.2 Merging Pipeline (`merge_predictions.py`) & GitHub Release

The `merge-and-release` job aggregates split artifacts into a single unified directory `trading_system/result/`:

1. **Pre-Release Guard**:
   ```bash
   FOUND=0
   for m in SP500 NASDAQ RUSSELL2000 KOSPI KOSDAQ; do
     if ls trading_system/result_${m}/*.txt >/dev/null 2>&1; then FOUND=1; break; fi
   done
   if [ "$FOUND" != "1" ]; then
     echo "::error::All market pipelines failed - no prediction files. Skipping release & deploy."
     exit 1
   fi
   ```
2. **Merging Execution (`merge_predictions.py`)**:
   - **Header Timestamping**: Standardized to KST timezone (`Asia/Seoul`, `+09:00`).
   - **Regex Section Extraction**: Extracts market blocks (`[SP500]`, `[KOSPI]`, etc.) using resilient multiline regex matching.
   - **Self-Referencing Fallback Protection**: Pre-reads all per-market input files into memory buffer before opening the output file in write mode (`open(..., 'w')`), preventing empty file truncation bugs.
   - **Portfolio Allocation Deduplication**: Merges per-market allocation recommendations and deduplicates symbols by keeping the highest weight recommendation.
3. **GitHub Release Upload**: Assets are published to release `vYYYY-MM-DD` via `gh release upload --clobber`.

### 3.3 Dashboard Generation & Resilience (`generate_report.py` & `verify_gha_artifacts.py`)

#### A. HTML Report Generation (`generate_report.py`)
- Compiles merged text outputs into `gh-pages/index.html`.
- **Live Macro Indicator Badges**: Displays VIX, US 10Y Yield, KR 10Y Yield, USD/KRW, WTI Crude Oil, and Gold. Uses `DataValidator.clean_macro_value` to detect shared-series cache corruption and apply safe fallback values.
- **UI/UX Responsiveness**: HTML template includes responsive CSS media queries for Mobile (375px / 414px) and Desktop (1920px), sticky table column headers, and overflow scroll containers for strategy tables.
- **Build Timestamp**: Writes `gh-pages/build.txt` containing execution date in KST (`YYYY-MM-DD HH:MM KST`) and GHA run URL.

#### B. Stale Deployment Prevention
- In `deploy-pages` job:
  ```bash
  if ! ls trading_system/result/*.txt >/dev/null 2>&1; then
    echo "::error::Merged result files missing - refusing to deploy a stale/fabricated dashboard."
    exit 1
  fi
  ```

#### C. Verification Tooling (`verify_gha_artifacts.py`)
- Audits 5 markets across 14 strategy panels on `gh-pages/index.html` and text prediction files.
- Enforces non-zero predictions, minimum item counts (>= 10 entries per strategy), and valid table markup. Can be invoked with `--strict` for strict CI pass/fail enforcement.

---

## Conclusion & Recommendations

1. **Pipeline Return Code Hardening**: Modify `run_pipeline.py` exception handling so that "partial success" exit code 0 is only granted if BOTH `pipeline_result.txt` AND `ensemble_predictions.txt` are present and non-empty. If ensemble predictions are missing, exit with code 1 to alert GHA.
2. **SQLite WAL Checkpointing**: Add explicit `PRAGMA wal_checkpoint(PASSIVE)` during pipeline shutdown in `run_pipeline.py` to ensure WAL log files are flushed back into main `.db` files prior to artifact caching.
3. **CI Verification Gating**: Add `python trading_system/scripts/verify_gha_artifacts.py --strict` as an explicit validation step in `pipeline.yml` prior to the `deploy-pages` job.
4. **Pytest Baseline Test Suite Status**:
   - Total tests executed: 601
   - Passed: 592
   - Failed: 9 (specifically: 5 tests in `test_correlation_suppression.py`, 1 test in `test_dag_pipeline_stress_m1.py`, 1 test in `test_fast_cointegration.py`, 1 test in `test_phase1_target_and_walkforward.py`, and 1 test in `test_target_labeling_and_walkforward.py`).
   - Implementers should address these 9 failing test cases to achieve 100% test pass rate required by Acceptance Criteria R3.

