## 2026-06-13T00:05:03Z
You are the teamwork_preview_worker.
Your task is to implement the central orchestrator CLI, the daemon scheduler using APScheduler (with fallback), Telegram status alerts, database/file logging, and unit tests, and verify it all runs successfully.

### Target Files to Create or Edit:
1. `trading_system/src/data_layer/indicator_storage.py`:
   - In `_init_db()`, add table `pipeline_runs` if it doesn't exist:
     ```sql
     CREATE TABLE IF NOT EXISTS pipeline_runs (
         id INTEGER PRIMARY KEY AUTOINCREMENT,
         stage TEXT NOT NULL,
         start_time TEXT NOT NULL,
         end_time TEXT,
         status TEXT NOT NULL,
         error_message TEXT
     )
     ```
2. `trading_system/orchestrator.py`:
   - Implement the `Orchestrator` and daemon scheduling runner.
   - Configure a rolling file logger to `orchestrator.log` (UTF-8 encoding, maxBytes=10MB, backupCount=5).
   - Track each execution of pipeline stages in `pipeline_runs` table in `market_indicators.db`.
   - Scheduler: Coordinated via APScheduler or a time-loop check (fallback if APScheduler cannot be imported) with safe concurrency (no overlap).
   - Support executing stages: `ingest`, `train`, `score`, `dashboard` (or `indicators`, `universe`, `train`, `predict`, `all`). Wait, let's support both sets of stage names so it is robust!
     - `ingest` / `indicators`: fetch global indicators and sync stock universe.
     - `score`: run `scripts/post_market_scoring.py` as a subprocess.
     - `train`: run XGBoost retraining from `run_pipeline.py`.
     - `predict`: run prediction inference.
     - `all`: execute the full pipeline.
   - Implement Telegram integration with a graceful fallback if credentials (TELEGRAM_BOT_TOKEN, etc.) are missing. When fallback occurs, log a warning and print the status message to stdout and `orchestrator.log`.
   - The daemon loop should check for a `stop.flag` file to shutdown gracefully.
3. `trading_system/run_orchestrator.py`:
   - The CLI entrypoint. Supports arguments: `start`, `stop`, `status`, `run-now <stage>`.
   - `start`: Launches the daemon process in the background using `subprocess.Popen` with `CREATE_NO_WINDOW | DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP` flags (on Windows) or standard flags on other OSes. Writes its PID to `orchestrator.pid`.
   - `stop`: Gracefully stops the running daemon (writes to `stop.flag` first, waits up to 10 seconds, then kills process if still running).
   - `status`: Displays current daemon state (RUNNING with PID or STOPPED) and displays the last scheduled runs from `pipeline_runs`.
   - `run-now <stage>`: Force executes a stage in the foreground immediately.
4. `trading_system/tests/test_orchestrator.py`:
   - Implement a pytest suite verifying:
     - Parser arguments (`start`, `stop`, `status`, `run-now`).
     - Correct `pipeline_runs` database logging.
     - Daemon scheduler startup, task triggering, and shutdown.
     - Safe gracefully-handled fallback logs when Telegram keys are missing.
   - Verify that all tests pass.

### Execution Commands to Run:
Run the pytest suite to verify:
```powershell
python -m pytest trading_system/tests/test_orchestrator.py
```
And make sure all tests pass.

⚠️ MANDATORY INTEGRITY WARNING — include this verbatim in your implementation:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.
