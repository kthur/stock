#!/usr/bin/env python3
"""
scripts/run_daily_supervisor.py
================================
Repo root forwarding wrapper for Autonomous Pipeline Daemon Supervisor CLI Runner (Phase 107).
"""

import sys
from pathlib import Path

# Setup paths to ensure clean imports
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
TRADING_SYSTEM_DIR = REPO_ROOT / "trading_system"

for p in (str(REPO_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    from trading_system.scripts.run_daily_supervisor import main
except ImportError:
    from scripts.run_daily_supervisor import main

if __name__ == "__main__":
    sys.exit(main())
