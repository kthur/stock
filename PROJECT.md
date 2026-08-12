# Project: Stock Trading System Enhancement (31-Strategy Multi-Factor Engine)

## Architecture
- **Data Layer & Persistence**: `trading_system/src/data_layer/`, `trading_system/src/persistence/database.py`, `trading_system/src/data_layer/indicator_storage.py`
- **AI & Strategy Prediction Engine**: `trading_system/src/ai/prediction_model.py`, `trading_system/src/ai/ensemble_scorer.py`, `trading_system/src/core/`
- **Risk & Execution (OMS)**: `trading_system/src/risk/microstructure.py`, `trading_system/src/execution/oms_engine.py`, `trading_system/src/risk/portfolio_allocator.py`
- **CI/CD Workflows**: `.github/workflows/pipeline.yml`, `.github/workflows/ci.yml`, `.github/workflows/pytest.yml`

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Corporate Action Sanity Check | Automatic filter for abnormal price spikes (>300% single-day change / unadjusted splits) | M1 | ORIGINAL_REQUEST R1 |
| 2 | Technical Indicator Cache TTL Eviction | Auto-eviction on date change or TTL expiration in `DataFrameCache` | M1 | ORIGINAL_REQUEST R1 |
| 3 | Inference Vectorization | Refactor symbol loops in `OnDevicePredictionModel` & strategy scorers to NumPy/Pandas matrix ops | M2 | ORIGINAL_REQUEST R2 |
| 4 | SQLite Concurrency Protection | `PRAGMA busy_timeout = 30000;` on `StockPriceDB` & `MarketIndicatorStorage` | M2 | ORIGINAL_REQUEST R2 |
| 5 | Dynamic Slippage Model | Intraday ATR & ADV-dependent dynamic market impact scaling in `MicrostructureCostModel` | M3 | ORIGINAL_REQUEST R3 |
| 6 | OMS Portfolio Compliance Logging | Log single stock (<= 5%) & sector (<= 20%) compliance in `trade_logs.db` | M3 | ORIGINAL_REQUEST R3 |
| 7 | CI/CD Artifact Archiving | Archive `ensemble_predictions.txt`, `strategy_data_coverage_report.txt`, `index.html` in GHA workflows | M4 | ORIGINAL_REQUEST R4 |
| 8 | API Retry Backoff Jitter | Randomized exponential backoff jitter in rate-limited API fetch calls (`earnings_data.py`) | M4 | ORIGINAL_REQUEST R4 |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Data Quality & Corporate Action Sanity Gates | Price spike filter (>300%), unadjusted split filter, `DataFrameCache` TTL eviction | None | DONE |
| M2 | Vectorized Inference & SQLite Concurrency | Vectorize `OnDevicePredictionModel` symbol loops, `busy_timeout=30000` on DBs | M1 | IN_PROGRESS |
| M3 | Dynamic Slippage & OMS Guardrails | ATR & ADV market impact in `MicrostructureCostModel`, portfolio limits in OMS (`trade_logs.db`) | M2 | PLANNED |
| M4 | CI/CD Archiving & API Retry Jitter | GHA artifact upload, API fetch jitter backoff in `earnings_data.py` | M3 | PLANNED |
| M5 | E2E Testing & Final Verification | 725+ pytest verification, benchmark speedup, stress test concurrency, artifact check | M1, M2, M3, M4 | PLANNED |

## Code Layout
- `trading_system/src/data_layer/` - Data loading, technical indicators, `DataFrameCache`, `earnings_data.py`
- `trading_system/src/persistence/database.py` - `StockPriceDB` SQLite connection and WAL settings
- `trading_system/src/data_layer/indicator_storage.py` - `MarketIndicatorStorage` SQLite storage
- `trading_system/src/ai/prediction_model.py` - `OnDevicePredictionModel` inference & prediction routines
- `trading_system/src/ai/ensemble_scorer.py` - Strategy scoring and ensemble matrix calculations
- `trading_system/src/risk/microstructure.py` - `MicrostructureCostModel` market impact & slippage calculations
- `trading_system/src/execution/oms_engine.py` / `trading_system/src/risk/portfolio_allocator.py` - OMS order execution & portfolio allocation guardrails
- `.github/workflows/` - GitHub Actions CI/CD workflows
