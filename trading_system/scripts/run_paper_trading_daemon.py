#!/usr/bin/env python3
"""
CLI Runner for Autonomous Paper-Trading Shadow Execution Daemon (Phase 106 / F501 / Release R122).

Usage:
    python trading_system/scripts/run_paper_trading_daemon.py --once
    python trading_system/scripts/run_paper_trading_daemon.py --once --capital 500000000
    python trading_system/scripts/run_paper_trading_daemon.py --once --dry-run
    python trading_system/scripts/run_paper_trading_daemon.py --once --regime BEAR
"""

import sys
import os
import time
import argparse
import logging
from pathlib import Path

# Add project root and trading_system directory to sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
TRADING_SYSTEM_DIR = REPO_ROOT / "trading_system"

for p in (str(REPO_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.execution.paper_trading_daemon import PaperTradingDaemon


def parse_args():
    parser = argparse.ArgumentParser(
        description="Autonomous Paper-Trading Shadow Execution Daemon CLI Runner (Phase 106)"
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single paper trading cycle and exit gracefully with code 0."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Execute shadow paper trading in dry-run mode (no live DB modifications)."
    )
    parser.add_argument(
        "--capital",
        type=float,
        default=100_000_000.0,
        help="Initial portfolio capital in base currency (default: 100,000,000 KRW)."
    )
    parser.add_argument(
        "--db",
        type=str,
        default="trade_logs.db",
        help="Path to SQLite trade logs database (default: trade_logs.db)."
    )
    parser.add_argument(
        "--allocation-file",
        type=str,
        default="trading_system/portfolio_allocation.txt",
        help="Path to portfolio allocation recommendation file (default: trading_system/portfolio_allocation.txt)."
    )
    parser.add_argument(
        "--regime",
        type=str,
        default="BULL_LOW_VOL",
        help="Market regime identifier (e.g. BULL_LOW_VOL, BULL_HIGH_VOL, BEAR, CRISIS)."
    )
    parser.add_argument(
        "--crisis",
        type=str,
        default="NORMAL",
        help="Crisis level (NORMAL, ELEVATED, SEVERE)."
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=900,
        help="Polling loop interval in seconds for daemon mode (default: 900s)."
    )
    parser.add_argument(
        "--market",
        type=str,
        default="ALL",
        help="Target market filter (e.g. ALL, KOSPI, KOSDAQ, SP500, NASDAQ, RUSSELL2000)."
    )
    return parser.parse_args()


def main():
    args = parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] [%(levelname)s] [PaperTradingDaemon] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    logger = logging.getLogger("PaperTradingDaemonRunner")

    logger.info("=" * 70)
    logger.info("Initializing Autonomous Paper-Trading Shadow Execution Daemon")
    logger.info(f"Capital: {args.capital:,.0f} | Dry-run: {args.dry_run} | Once: {args.once}")
    logger.info(f"Regime: {args.regime} | Crisis: {args.crisis} | DB: {args.db}")
    logger.info(f"Allocation File: {args.allocation_file}")
    logger.info("=" * 70)

    daemon = PaperTradingDaemon(
        initial_capital=args.capital,
        db_path=args.db,
        dry_run=args.dry_run,
        regime_label=args.regime,
        crisis_level=args.crisis,
    )

    alloc_path = Path(args.allocation_file)
    if not alloc_path.exists():
        fallback_path = REPO_ROOT / args.allocation_file
        if fallback_path.exists():
            alloc_path = fallback_path
        else:
            logger.warning(f"Allocation file not found at {args.allocation_file}. Using existing portfolio state.")
            alloc_path = None

    if args.once:
        logger.info("Executing single rebalance cycle (--once)...")
        summary = daemon.run_cycle(target_input=str(alloc_path) if alloc_path else None)

        print("\n" + "=" * 70)
        print("          SHADOW PAPER TRADING EXECUTION SUMMARY")
        print("=" * 70)
        print(f"Status           : {summary['status']}")
        print(f"Timestamp        : {summary['timestamp']}")
        print(f"Target Symbols   : {summary['targets_count']}")
        print(f"Delta Orders     : {summary['deltas_count']}")
        print(f"Approved Orders  : {summary['approved_count']}")
        print(f"Suppressed Gates : {summary['suppressed_count']}")
        print(f"Executed Fills   : {summary['executed_count']}")
        print("-" * 70)
        print(f"Gross Equity     : {summary['gross_equity']:,.2f}")
        print(f"Net Equity       : {summary['net_equity']:,.2f}")
        print(f"Cash Balance     : {summary['cash_balance']:,.2f}")
        print(f"Total Fees Paid  : {summary['total_fees_paid']:,.2f}")
        print(f"Total Mkt Impact : {summary['total_impact_cost']:,.2f}")
        print(f"Invariant Passed : {'YES' if summary['invariant_net_le_gross'] else 'NO'} (Net Equity <= Gross Equity)")
        print("=" * 70 + "\n")

        if summary['executions']:
            print("Executions:")
            for ex in summary['executions'][:10]:
                print(f"  [{ex['action']}] {ex['symbol']} ({ex['market']}) - Qty: {ex['quantity']} @ {ex['executed_price']:,.2f} | Slip: {ex['slippage_bps']:+.1f}bps | Fee: {ex['fee_amount']:,.1f}")
            if len(summary['executions']) > 10:
                print(f"  ... and {len(summary['executions']) - 10} more executions.")
            print("-" * 70)

        logger.info("Cycle completed successfully. Exiting code 0.")
        sys.exit(0)
    else:
        logger.info(f"Starting continuous daemon loop (interval={args.interval}s). Press Ctrl+C to stop.")
        try:
            while True:
                summary = daemon.run_cycle(target_input=str(alloc_path) if alloc_path else None)
                logger.info(f"Cycle completed: {summary['executed_count']} executed, Net Equity={summary['net_equity']:,.0f}")
                time.sleep(args.interval)
        except KeyboardInterrupt:
            logger.info("Daemon interrupted by user. Shutting down gracefully.")
            sys.exit(0)


if __name__ == "__main__":
    main()
