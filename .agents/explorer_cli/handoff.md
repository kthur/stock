# Explorer CLI Handoff Report

## 1. Observation
- **Codebase Entrypoint**: `d:\Finance\code\stock\trading_system\run_pipeline.py` (line 62: `def execute_prediction_pipeline()`) executes the consolidated pipeline.
- **Scheduler Checks**: `d:\Finance\code\stock\trading_system\trading_system.py` (lines 2069-2110) contains periodic rebalancing and optimization scheduler checks (`_check_rebalance_schedule` and `_check_optimization_schedule`).
- **Dependencies**: `d:\Finance\code\stock\trading_system\requirements.txt` and `pyproject.toml` list external packages (e.g., `fastapi`, `xgboost`, `python-telegram-bot`) but do not include `apscheduler`.
- **Project Requirements**: `.agents/orchestrator_pipeline/plan.md` outlines the goal of implementing a CLI with `start`, `stop`, `status`, `run-now <stage>` commands, coordinating schedules (daily ingestion, daily scoring, weekly training), logging to `orchestrator.log`, and auditing runs in `pipeline_runs` SQLite table.

## 2. Logic Chain
- **CLI Design**: The CLI commands must route cleanly. The `run-now` command stages map directly to functional tasks:
  - `indicators`: Fetch indicators via `GlobalMarketClient` and `MarketIndicatorStorage`.
  - `universe`: Sync stock universe via `MarketIndicatorStorage.update_stock_universe()`.
  - `train`: Prepare data and train XGBoost models.
  - `predict`: Run prediction inference for all symbols.
  - `all`: Sequentially execute all of the above.
- **Windows Detached Process**: Traditional Unix fork-based daemonization does not work on Windows. Background processes are spawned using `subprocess.Popen` with creation flags `CREATE_NO_WINDOW | DETACHED_PROCESS` to hide console windows and detach execution.
- **Graceful Termination**: On Windows, sending standard `SIGTERM` terminates processes abruptly without invoking signal handlers. Implementing a dual stop mechanism is recommended:
  1. A file-based stop flag (`stop.flag`) checked during the daemon loop.
  2. Spawning with `CREATE_NEW_PROCESS_GROUP` and signaling with `CTRL_BREAK_EVENT` (received as `SIGBREAK` in Python) as a backup.
- **PID Verification**: To avoid stale PID file conflicts, liveness must be verified. On Windows, this is done by calling `tasklist /FI "PID eq <pid>"` or opening a handle via `ctypes.windll.kernel32.OpenProcess` and checking the exit code.
- **Log Rotation**: Logs are written to `orchestrator.log` using standard `RotatingFileHandler` with `encoding="utf-8"` (to support Korean text logs) and set to roll over at 10MB (`maxBytes=10*1024*1024`) with 5 backups kept.

## 3. Caveats
- No libraries were installed or packages modified as the investigation is strictly read-only.
- The actual background loop and signal handling have not been run or verified on the system; the proposals are based on Windows OS API specifications and Python standard library behavior.

## 4. Conclusion
A zero-dependency CLI structure and Windows-compatible background daemon architecture can be successfully implemented using Python's standard library (`argparse`, `subprocess`, `signal`, `ctypes`, and `logging`). The complete architecture design, database schema, and code templates have been written to `d:\Finance\code\stock\.agents\orchestrator_pipeline\explorer_cli.md`.

## 5. Verification Method
- Inspect the generated architectural report at `d:\Finance\code\stock\.agents\orchestrator_pipeline\explorer_cli.md`.
- Confirm that no files in `d:\Finance\code\stock\trading_system` were modified or created.
- The next agent (Implementer) can copy the provided templates to implement the orchestrator and daemon scripts.
