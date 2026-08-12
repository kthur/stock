# Plan — Stock Trading System (31-Strategy Multi-Factor Engine) Enhancement

## Executive Summary
This project enhances the Stock Trading System across data quality/sanity checks, inference vectorization & database concurrency, dynamic microstructure slippage modeling & OMS guardrails, and CI/CD archiving & API resilience.

## Objectives & Work Breakdown

### Milestone 1: Data Quality & Corporate Action Sanity Gates
- **Objective**: Prevent unadjusted corporate action price anomalies and cache staleness.
- **Tasks**:
  1. Add corporate action price spike filter (> 300% single-day change or unadjusted split detector) in data ingestion/cleaning pipelines.
  2. Implement TTL auto-eviction and date-change invalidation in `DataFrameCache`.
- **Target Files**: `src/data_layer/`, `src/persistence/database.py`, `src/config.py`

### Milestone 2: Inference Vectorization & SQLite Concurrency Protection
- **Objective**: Accelerate 3,379-symbol inference and prevent SQLite `database is locked` errors during multi-threaded operation.
- **Tasks**:
  1. Vectorize symbol-level loop calculations in `OnDevicePredictionModel` and strategy scorers using NumPy/Pandas.
  2. Ensure `PRAGMA busy_timeout = 30000;` is executed on all SQLite connections in `StockPriceDB` and `MarketIndicatorStorage`.
- **Target Files**: `src/ai/prediction_model.py`, `src/ai/ensemble_scorer.py`, `src/persistence/database.py`, `src/data_layer/indicator_storage.py`

### Milestone 3: Dynamic Slippage Model & OMS Portfolio Guardrails
- **Objective**: Improve real-money execution accuracy and portfolio safety.
- **Tasks**:
  1. Enhance `MicrostructureCostModel` to incorporate intraday ATR and ADV (Average Daily Volume) ratio scaling for dynamic market impact & slippage.
  2. Update OMS / `PortfolioAllocator` to check single stock (<= 5%) and sector (<= 20%) constraints, logging compliance to `trade_logs.db`.
- **Target Files**: `src/core/microstructure.py`, `src/execution/oms.py`, `src/portfolio/allocator.py`

### Milestone 4: CI/CD Build Artifact Archiving & API Retry Jitter
- **Objective**: Harden CI/CD pipeline artifact output and prevent API rate-limit throttling.
- **Tasks**:
  1. Update `.github/workflows/*.yml` to upload/archive `ensemble_predictions.txt`, `strategy_data_coverage_report.txt`, `index.html`.
  2. Add randomized exponential backoff jitter to API fetchers (`earnings_data.py`, global indicators, rate-limited HTTP calls).
- **Target Files**: `.github/workflows/`, `src/data_layer/earnings_data.py`, `src/data_layer/`

### Milestone 5: E2E Testing & System Verification
- **Objective**: Verify that all 725+ unit tests pass, vectorization speeds up inference, SQLite stress test passes without lock errors, and build artifacts are valid.

## Execution Strategy
1. **Step 0: Survey**: Dispatch 3 Explorers / Spec Miners to map current implementation in target modules and existing tests.
2. **Decompose & Dispatch**: Delegate each milestone to sub-orchestrators/workers with Explorer -> Worker -> Reviewer -> Challenger -> Auditor iteration loop.
3. **Verification**: Worker runs pytest and benchmarks; Reviewers approve; Challengers stress-test; Forensic Auditor verifies integrity.
