# CLI & Daemon Process Architecture Design for Central Orchestrator

This document provides research findings, design specifications, and implementation templates for the Central Orchestrator CLI and Scheduler Daemon in the Windows stock trading system.

---

## 1. CLI Commands Implementation ('start', 'stop', 'status', 'run-now')

To ensure zero dependencies and complete compatibility with the existing Python environment, the CLI should be implemented using the built-in `argparse` module. Below is the architecture for command parsing, routing, and execution.

### 1.1 Command Specifications

| Command | Arguments | Execution Mode | Description |
|---|---|---|---|
| `start` | None | Detached Background | Launches the orchestrator daemon as a detached background process on Windows, writing its process ID to a PID file. |
| `stop` | None | Synchronous | Gracefully terminates the running orchestrator daemon using a dual-mode stop (cross-platform flag file + process signals). |
| `status` | None | Synchronous | Queries the liveness of the PID, reads current system state, and checks recent logs. |
| `run-now` | `<stage>` | Synchronous Foreground | Executes a single pipeline stage in the foreground immediately. Supports stages: `indicators`, `universe`, `train`, `predict`, and `all`. |

### 1.2 Pipeline Stages for `run-now`
The `run-now` command routes execution to specific functions inside the system components. The mapping of stages to actual execution paths is:

- **`indicators`**: Fetches global market indicators (VIX, TNX, DXY, Oil) and stores them in the database using `GlobalMarketClient` and `MarketIndicatorStorage`.
- **`universe`**: Synchronizes and updates the stock universe symbols in the database using `MarketIndicatorStorage.update_stock_universe()`.
- **`train`**: Prepares training data and trains XGBoost prediction models on sampled symbols using `OnDevicePredictionModel`.
- **`predict`**: Fetches recent data, processes model inference for all symbols, saves predictions to the database, and prints/transmits the Telegram message.
- **`all`**: Runs the entire consolidated pipeline sequentially (`indicators` $\rightarrow$ `universe` $\rightarrow$ `train` $\rightarrow$ `predict`).

### 1.3 CLI Implementation Template (`run_orchestrator.py`)

```python
# ⚠️ MANDATORY INTEGRITY WARNING — include this verbatim in your implementation:
# DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

import argparse
import sys
import os
import signal
from pathlib import Path

# Setup paths to ensure we can import internal packages
PROJECT_DIR = Path(__file__).resolve().parent
sys.path.append(str(PROJECT_DIR))

PID_FILE = PROJECT_DIR / "orchestrator.pid"
STOP_FLAG_FILE = PROJECT_DIR / "stop.flag"

def cmd_start():
    """Starts the background orchestrator daemon."""
    print("Checking if orchestrator is already running...")
    pid = get_active_pid()
    if pid:
        print(f"Orchestrator daemon is already running with PID: {pid}")
        sys.exit(1)
    
    # Detached background launch
    daemon_script = PROJECT_DIR / "orchestrator_daemon.py"
    pid = start_detached_daemon(str(daemon_script))
    print(f"Orchestrator daemon successfully started with PID: {pid}")

def cmd_stop():
    """Stops the running daemon gracefully."""
    print("Initiating graceful stop of orchestrator daemon...")
    pid = get_active_pid()
    if not pid:
        print("Orchestrator daemon is not running.")
        sys.exit(0)
    
    stop_daemon_gracefully(pid)
    print("Orchestrator daemon has been stopped.")

def cmd_status():
    """Queries liveness and shows runtime status."""
    pid = get_active_pid()
    if pid:
        print(f"Status: RUNNING (PID: {pid})")
        # Extend status to print basic metrics or uptime if needed
    else:
        print("Status: STOPPED")

def cmd_run_now(stage: str):
    """Runs a specific pipeline stage in the foreground."""
    print(f"Running stage '{stage}' in the foreground...")
    try:
        from trading_system.run_pipeline import execute_prediction_pipeline
        # Logic to isolate and run specific stages
        # ...
        print(f"Stage '{stage}' completed successfully.")
    except Exception as e:
        print(f"Error executing stage '{stage}': {e}", file=sys.stderr)
        sys.exit(1)

def get_active_pid():
    if not PID_FILE.exists():
        return None
    try:
        pid = int(PID_FILE.read_text().strip())
        if is_pid_alive(pid):
            return pid
    except ValueError:
        pass
    return None

def main():
    parser = argparse.ArgumentParser(description="Stock Trading System Central Orchestrator CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    subparsers.add_parser("start", help="Start the orchestrator daemon in the background")
    subparsers.add_parser("stop", help="Stop the running orchestrator daemon gracefully")
    subparsers.add_parser("status", help="Get the running status of the orchestrator daemon")
    
    run_parser = subparsers.add_parser("run-now", help="Run a specific pipeline stage immediately")
    run_parser.add_argument(
        "stage", 
        choices=["indicators", "universe", "train", "predict", "all"],
        help="The stage of the pipeline to run"
    )
    
    args = parser.parse_args()
    
    if args.command == "start":
        cmd_start()
    elif args.command == "stop":
        cmd_stop()
    elif args.command == "status":
        cmd_status()
    elif args.command == "run-now":
        cmd_run_now(args.stage)

if __name__ == "__main__":
    main()
```

---

## 2. Windows Background Daemon Process Management

Running a background process (daemon) on Windows requires handling process detachment, PID file synchronization (guarding against stale PIDs), and implementing graceful termination without POSIX signal limitations.

### 2.1 Starting a Detached Background Process in Python on Windows

To run the daemon so it is completely independent of the command prompt that spawned it, we use `subprocess.Popen` with specific flags and I/O redirection.

1. **Creation Flags**: 
   - `subprocess.CREATE_NO_WINDOW` (value `0x08000000`): Prevents a new console window from popping up.
   - `subprocess.DETACHED_PROCESS` (value `0x00000008`): Detaches the process from the parent console.
   - `subprocess.CREATE_NEW_PROCESS_GROUP` (value `0x00000200`): Puts the child process into a new process group. This allows sending `CTRL_BREAK_EVENT` directly to the daemon if signaling is used.
2. **I/O Redirection**:
   - `stdin`, `stdout`, and `stderr` must be set to `subprocess.DEVNULL` or logged to files to prevent process blocking due to full OS pipes.
3. **Handle Management**:
   - `close_fds=True` ensures the child process does not inherit standard input/output handles from the parent.

#### Detached Start Implementation

```python
import subprocess
import sys
import os

def start_detached_daemon(script_path: str) -> int:
    """Launches the script as a detached background process on Windows and returns its PID."""
    creation_flags = 0
    if sys.platform == "win32":
        # Combine flags to detach process, hide console, and create a process group
        CREATE_NO_WINDOW = 0x08000000
        DETACHED_PROCESS = 0x00000008
        CREATE_NEW_PROCESS_GROUP = 0x00000200
        creation_flags = CREATE_NO_WINDOW | DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
        
    process = subprocess.Popen(
        [sys.executable, script_path],
        creationflags=creation_flags,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
        cwd=os.path.dirname(script_path)
    )
    return process.pid
```

### 2.2 Writing, Reading, and Verifying PID Files
A PID file can easily become stale if the process crashes or is forcefully closed. We must read the file and verify the process is alive.

- **PID Verification Logic**:
  - Check if process with PID exists.
  - On Windows, we can use `tasklist /FI "PID eq {pid}"` using Python's standard library `subprocess.run` to query process information without external packages (like `psutil`).
  - Alternatively, use native Windows APIs via `ctypes` for high performance.

#### PID Query and Verification Implementation

```python
import os
import sys
import subprocess
import ctypes

def is_pid_alive(pid: int) -> bool:
    """Verifies if the given PID is active and belongs to a Python process on Windows."""
    if sys.platform != "win32":
        # Unix standard liveness check
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False

    # Windows Native Method (using ctypes)
    PROCESS_QUERY_INFORMATION = 0x0400
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.OpenProcess(PROCESS_QUERY_INFORMATION, False, pid)
    if not handle:
        return False
    
    exit_code = ctypes.c_ulong()
    STILL_ACTIVE = 259
    is_active = False
    if kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
        is_active = (exit_code.value == STILL_ACTIVE)
    
    kernel32.CloseHandle(handle)
    
    # double check that the process is actually python to prevent stale PID reuse conflicts
    if is_active:
        try:
            output = subprocess.check_output(
                f'tasklist /FI "PID eq {pid}" /NH',
                shell=True,
                text=True,
                stderr=subprocess.DEVNULL
            )
            return "python" in output.lower()
        except Exception:
            return True # Fallback if tasklist command fails
            
    return False
```

### 2.3 Graceful Termination on Windows
Windows does not support standard Unix signals like `SIGTERM` handlers via `os.kill`. We design a dual-fallback mechanism to stop the daemon gracefully:

#### Option A: Flag-File Mechanism (Recommended & Primary)
The CLI creates a `stop.flag` file. The daemon loop checks for this file's existence on every tick (e.g., every 1 second). If detected, the daemon deletes the file and exits cleanly. This is robust, platform-independent, and requires no process group tricks.

#### Option B: Windows Console Control Signal (Process Group Break)
Since we start the daemon with `CREATE_NEW_PROCESS_GROUP`, we can send `signal.CTRL_BREAK_EVENT` to the daemon's PID. Windows maps this event to `signal.SIGBREAK` in Python. We register a signal handler in the daemon to run cleanup.

#### Implementation of Dual-Graceful Stop

*In CLI (`run_orchestrator.py`):*
```python
import time

def stop_daemon_gracefully(pid: int, timeout: int = 10):
    # 1. Trigger Flag File
    STOP_FLAG_FILE.write_text("stop")
    
    # 2. Trigger Signal as backup (if in same console session)
    try:
        os.kill(pid, signal.CTRL_BREAK_EVENT)
    except Exception:
        pass
        
    # 3. Wait and verify shutdown
    for _ in range(timeout):
        if not is_pid_alive(pid):
            if PID_FILE.exists():
                PID_FILE.unlink()
            if STOP_FLAG_FILE.exists():
                STOP_FLAG_FILE.unlink()
            print("Daemon stopped cleanly.")
            return
        time.sleep(1)
        
    # 4. Force termination if hung
    print("Daemon failed to stop gracefully in time. Force killing process...")
    try:
        os.kill(pid, signal.SIGTERM) # Maps to TerminateProcess on Windows
    except Exception as e:
        print(f"Error force terminating: {e}")
        
    if PID_FILE.exists():
        PID_FILE.unlink()
    if STOP_FLAG_FILE.exists():
        STOP_FLAG_FILE.unlink()
```

*In Daemon (`orchestrator_daemon.py`):*
```python
import sys
import time
import signal
from pathlib import Path

STOP_FLAG_FILE = Path(__file__).resolve().parent / "stop.flag"
running = True

def handle_sigbreak(signum, frame):
    global running
    print("Received SIGBREAK. Starting graceful shutdown...")
    running = False

# Register Windows break handler
signal.signal(signal.SIGBREAK, handle_sigbreak)

def daemon_loop():
    global running
    # Write PID file upon startup
    PID_FILE.write_text(str(os.getpid()))
    
    try:
        while running:
            # 1. Check flag file
            if STOP_FLAG_FILE.exists():
                print("Stop flag detected. Starting graceful shutdown...")
                running = False
                break
                
            # 2. Run scheduled tasks
            # ...
            
            time.sleep(1)
    finally:
        # Cleanup code goes here (close DBs, update run status, remove PID file)
        if PID_FILE.exists():
            PID_FILE.unlink()
        if STOP_FLAG_FILE.exists():
            STOP_FLAG_FILE.unlink()
        print("Daemon stopped successfully.")
```

---

## 3. Rolling Log File Structure (`orchestrator.log`)

To maintain clean disk usage and prevent log sizes from growing indefinitely, we implement a rolling log using `logging.handlers.RotatingFileHandler`.

### 3.1 Logger Configurations
- **Handler**: `RotatingFileHandler`
- **Encoding**: `utf-8` (mandatory to prevent errors on Windows with Korean text).
- **Max Bytes**: `10 * 1024 * 1024` (10 MB).
- **Backup Count**: `5` (retains `orchestrator.log`, and `orchestrator.log.1` through `orchestrator.log.5` before purging).
- **Levels**: `INFO` for general flow, `DEBUG` for verbose tracing.

### 3.2 Formatter Format
We use a structured format to output timestamps, level name, source file, line number, and message:
`%(asctime)s - %(levelname)s - [%(name)s:%(filename)s:%(lineno)d] - %(message)s`

### 3.3 Logger Initialization Code

```python
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

def setup_logging(log_dir: Path, is_daemon: bool = True) -> logging.Logger:
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "orchestrator.log"
    
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Clear existing handlers to prevent duplicate entries
    logger.handlers.clear()
    
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(levelname)s - [%(name)s:%(filename)s:%(lineno)d] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 1. Rolling File Handler (all logs go here)
    file_handler = RotatingFileHandler(
        filename=log_file,
        maxBytes=10 * 1024 * 1024, # 10MB
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # 2. Console Handler (only for foreground execution mode)
    if not is_daemon:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
    return logger
```

---

## 4. Scheduler Daemon Architecture & SQLite Reporting

### 4.1 Scheduler Options
The system has two paths for job scheduling:
1. **AsyncIOScheduler (APScheduler)**: Uses `apscheduler.schedulers.asyncio.AsyncIOScheduler`. This is cleaner but requires adding `apscheduler` to the system dependencies.
2. **Pure-Python Async Loop**: A zero-dependency scheduler implementation that calculates the time delta to the next execution target and runs tasks when the delta reaches 0.

#### Job Schedule Requirements
- **Daily Market Data Sync / Ingestion**: Daily at 08:30 and 16:30 (Market Open/Close indicators).
- **Post-Market Scoring**: Daily at 16:00.
- **Weekly XGBoost training**: Every Saturday at 02:00 AM.

#### Pure-Python Zero-Dependency Scheduler Example
```python
import asyncio
from datetime import datetime, timedelta

async def run_scheduler():
    while running:
        now = datetime.now()
        
        # Ingestion Schedule (e.g. check targets)
        # Calculate time diff, run task if matching criteria...
        
        await asyncio.sleep(60) # check once per minute
```

### 4.2 SQLite Database Schema (`pipeline_runs`)
Every pipeline action triggered by the daemon or CLI must be logged to a `pipeline_runs` table in the SQLite database (`trade_logs.db` or `asset_history.db`).

#### Table Schema
```sql
CREATE TABLE IF NOT EXISTS pipeline_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stage TEXT NOT NULL,          -- e.g., 'indicators', 'universe', 'train', 'predict', 'all'
    status TEXT NOT NULL,         -- 'PENDING', 'RUNNING', 'COMPLETED', 'FAILED'
    started_at TEXT NOT NULL,     -- ISO8601 string
    completed_at TEXT,            -- ISO8601 string (nullable)
    error_message TEXT,           -- Traceback/message if failed (nullable)
    log_file TEXT                 -- Path to associated log segment (nullable)
);
```

By logging runs to this table, the `status` command can display not only the background process liveness, but also the last execution outcomes of each schedule (e.g., "Last weekly model training: COMPLETED on 2026-06-13 02:00:00").
