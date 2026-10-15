#!/usr/bin/env python3
"""
trading_system/scripts/run_daily_supervisor.py
===============================================
CLI Runner for Autonomous Pipeline Daemon Supervisor (Phase 107 / F505 / Release R123).

Usage:
    python trading_system/scripts/run_daily_supervisor.py --once
    python trading_system/scripts/run_daily_supervisor.py --once --dry-run
    python trading_system/scripts/run_daily_supervisor.py --once --market KOSPI --capital 50000000
    python trading_system/scripts/run_daily_supervisor.py --interval-seconds 300 --regime BULL_LOW_VOL
"""

from __future__ import annotations

import argparse
import logging
import os
import signal
import sys
from pathlib import Path

# Setup paths to ensure clean imports
SCRIPT_DIR = Path(__file__).resolve().parent
TRADING_SYSTEM_DIR = SCRIPT_DIR.parent
REPO_ROOT = TRADING_SYSTEM_DIR.parent if TRADING_SYSTEM_DIR.name == "trading_system" else TRADING_SYSTEM_DIR

for p in (str(REPO_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.execution.pipeline_daemon_supervisor import (
    PipelineDaemonSupervisor,
    SupervisorLifecyclePhase,
    SupervisorCycleReport,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Autonomous Pipeline Daemon Supervisor CLI Runner (Phase 107 / Release R123)"
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Execute a single master cycle through all 4 lifecycle phases and exit with code 0."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run in dry-run simulation mode (no live database mutations or network orders)."
    )
    parser.add_argument(
        "--market",
        type=str,
        default="ALL",
        help="Target market filter (e.g. ALL, KRX, US, KOSPI, KOSDAQ, SP500, NASDAQ, RUSSELL2000). Default: ALL."
    )
    parser.add_argument(
        "--interval-seconds",
        type=int,
        default=60,
        help="Polling loop interval in seconds for daemon mode (default: 60s)."
    )
    parser.add_argument(
        "--capital",
        type=float,
        default=100_000_000.0,
        help="Initial portfolio capital in KRW (default: 100,000,000.0 KRW)."
    )
    parser.add_argument(
        "--db",
        type=str,
        default="trade_logs.db",
        help="Path to SQLite trade logs database (default: trade_logs.db)."
    )
    parser.add_argument(
        "--state-file",
        type=str,
        default="supervisor_state.json",
        help="Path to supervisor operational state JSON file (default: supervisor_state.json)."
    )
    parser.add_argument(
        "--regime",
        type=str,
        default="BULL_LOW_VOL",
        help="Market regime override (BULL_LOW_VOL, BULL_HIGH_VOL, SIDEWAYS, BEAR, CRISIS). Default: BULL_LOW_VOL."
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] [%(levelname)s] [SupervisorDaemon] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
    )
    logger = logging.getLogger("DailySupervisorRunner")

    logger.info("=" * 70)
    logger.info("Starting Autonomous Pipeline Daemon Supervisor (Phase 107 / Release R123)")
    logger.info(f"Target Market    : {args.market}")
    logger.info(f"Initial Capital  : {args.capital:,.0f} KRW")
    logger.info(f"Market Regime    : {args.regime}")
    logger.info(f"State File       : {args.state_file}")
    logger.info(f"Trade Logs DB    : {args.db}")
    logger.info(f"Execution Mode   : {'Single Sweep (--once)' if args.once else 'Continuous Daemon Loop'}")
    logger.info(f"Dry-Run Mode     : {args.dry_run}")
    logger.info("=" * 70)

    supervisor = PipelineDaemonSupervisor(
        capital=args.capital,
        db_path=args.db,
        state_file=args.state_file,
        market=args.market,
        regime_label=args.regime,
        interval_seconds=args.interval_seconds,
        dry_run=args.dry_run,
    )

    # Attach signal handlers for graceful shutdown in daemon mode
    def handle_signal(sig, frame):
        logger.info(f"Signal {sig} received. Requesting supervisor daemon stop...")
        supervisor.stop()

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    if args.once:
        logger.info("[Runner] Executing single complete lifecycle sweep (--once)...")
        reports = supervisor.run_single_sweep()
        all_ok = all(r.success for r in reports.values())
        logger.info(f"[Runner] Single sweep finished. Success={all_ok}")
        for phase_name, r in reports.items():
            status_str = "PASS" if r.success else f"FAIL ({r.error_message})"
            logger.info(f"  * Phase {phase_name:<15}: {status_str} ({r.details.get('duration_sec', 0.0):.2f}s)")
        return 0 if all_ok else 1
    else:
        logger.info(f"[Runner] Launching daemon loop with polling interval {args.interval_seconds}s...")
        supervisor.run_daemon_loop()
        return 0


if __name__ == "__main__":
    sys.exit(main())
