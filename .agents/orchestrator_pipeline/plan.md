# Execution Plan: Central Orchestrator & Scheduler Daemon

## Objectives
1. Implement a central orchestrator component with a single CLI entrypoint (`run_orchestrator.py` or similar) supporting: `start`, `stop`, `status`, `run-now <stage>`.
2. Implement a scheduler daemon using APScheduler (or background loops as fallback) to coordinate daily ingestion/db sync, daily post-market scoring, weekly XGBoost retraining.
3. Integrate Telegram bot alerts with graceful fallback if credentials are missing.
4. Log all actions to `orchestrator.log` and SQLite database table `pipeline_runs`.
5. Verify behavior with tests in `tests/test_orchestrator.py` via pytest.

## Execution Steps
1. **Explore**:
   - Spawn Explorer agent to analyze codebase structure, check installed libraries (especially if `apscheduler` is installed, and how `TradingConfig` works).
   - Explorer checks how telegram messages are sent and how `run_pipeline.py` / `post_market_scoring.py` are executed.
2. **Design**:
   - Define exact design of the CLI, scheduler daemon, logging database table schema, and fallback mechanism.
3. **Implement**:
   - Spawn Worker agent to implement:
     - The orchestrator and scheduler logic (e.g. `trading_system/orchestrator.py`).
     - CLI entrypoint (`trading_system/run_orchestrator.py`).
     - Logging to `pipeline_runs` and `orchestrator.log`.
     - Telegram alert messaging.
4. **Test & Verify**:
   - Spawn Worker to write test suite in `trading_system/tests/test_orchestrator.py`.
   - Run tests using pytest.
5. **Review & Audit**:
   - Review code correctness.
   - Run Forensic Integrity Audit.
