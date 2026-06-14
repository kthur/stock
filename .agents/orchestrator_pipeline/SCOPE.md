# Scope: Central Orchestrator & Scheduler Daemon

## Architecture
The scheduler daemon coordinates:
- Daily Data Ingestion & Database Sync (prices + fundamentals).
- Daily Post-Market scoring & rankings calculation (post-market hour).
- Periodic XGBoost model retraining (e.g., weekly).
- Telegram alert notification status updates on success and failure.
- Database logging of runs in table `pipeline_runs`.
- Central CLI entrypoint `run_orchestrator.py` or similar in `trading_system/`.

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | Explore & Design | Analyze existing codebase and design CLI + daemon API. | None | DONE |
| 2 | Implementation | Implement central orchestrator class, daemon scheduler, CLI trigger, database/file logging, and Telegram integration. | M1 | DONE |
| 3 | Verification | Implement tests in `tests/test_orchestrator.py` and verify with pytest. | M2 | DONE |
| 4 | Audit & Challengers | Run challengers and Forensic Auditor. | M3 | IN_PROGRESS |

## Interface Contracts
### Daemon & CLI
- Commands: `start`, `stop`, `status`, `run-now <stage>`
- Scheduler tasks:
  - `ingest`: trigger daily ingest/db sync
  - `score`: trigger daily post-market scoring
  - `train`: trigger weekly retraining
- Log table: `pipeline_runs` columns: `id`, `stage`, `start_time`, `end_time`, `status`, `error_message`

## Code Layout
- Orchestrator Core: `trading_system/src/orchestration/orchestrator.py` (or `trading_system/orchestrator.py`)
- CLI Entrypoint: `trading_system/run_orchestrator.py`
- Test Suite: `trading_system/tests/test_orchestrator.py`
- DB: `market_indicators.db`
