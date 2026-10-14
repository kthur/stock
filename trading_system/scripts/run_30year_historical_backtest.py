#!/usr/bin/env python3
"""
run_30year_historical_backtest.py — Standalone 30-Year Historical Backtest & Quantitative Benchmark Runner

Executes the institutional 30-year walk-forward backtest (1996–2026) across 5 markets
(KOSPI, KOSDAQ, SP500, NASDAQ, RUSSELL2000) using 37 multi-factor strategies, 2D regime
detection, institutional 4-model barycenter allocation, and realistic execution frictions.

Computes 15 standardized metrics, 31-year annual distribution table, 5 historical crises breakdown,
exports artifacts to designated output directory, and optionally executes independent verification.
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Ensure repository root and trading_system are on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p in (str(PROJECT_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.backtest.historical_30yr_backtester import (
    Historical30YrBacktester,
    BacktestSimulationResult,
)
from src.analysis.historical_30yr_analytics import (
    Historical30YrAnalytics,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("Run30YearBacktest")


# ==============================================================================
# Terminal Executive Summary Formatter
# ==============================================================================

def print_executive_summary_table(summary_payload: Dict[str, Any]) -> None:
    """Prints a clear, high-density terminal summary of key 30-year performance metrics."""
    overall = summary_payload.get("portfolio_overall", {})
    meta = summary_payload.get("metadata", {})
    mkt_map = summary_payload.get("market_breakdown", {})
    crises = summary_payload.get("historical_crises", [])

    print("\n" + "=" * 90)
    print("      30-YEAR HISTORICAL BACKTEST & QUANTITATIVE BENCHMARK (1996-2026)")
    print("      Execution Horizon: " + str(meta.get("simulation_period", "1996-01-01 ~ 2026-08-31")))
    print("      Total Trading Days: " + f"{meta.get('total_trading_days', 0):,} bars | Multi-Factor Strategies: 37")
    print("=" * 90)

    print(f"\n{'PORTFOLIO OVERALL PERFORMANCE':^90}")
    print("-" * 90)
    print(f"  Initial Capital:        {overall.get('initial_capital', 0.0):>15,.0f} KRW  |  Final Net Equity:     {overall.get('final_equity', 0.0):>15,.2f} KRW")
    print(f"  Total Gross Return:     {overall.get('total_gross_return_pct', 0.0):>15.2f} %    |  Total Net Return:     {overall.get('total_net_return_pct', 0.0):>15.2f} %")
    print(f"  CAGR (Annualized):      {overall.get('cagr_pct', 0.0):>15.2f} %    |  Annual Volatility:    {overall.get('annualized_volatility_pct', 0.0):>15.2f} %")
    print(f"  Sharpe Ratio (rf=2.0%): {overall.get('sharpe_ratio', 0.0):>15.2f}      |  Sortino Ratio:        {overall.get('sortino_ratio', 0.0):>15.2f}")
    print(f"  Calmar Ratio:           {overall.get('calmar_ratio', 0.0):>15.2f}      |  Maximum Drawdown:     {overall.get('max_drawdown_pct', 0.0):>15.2f} %")
    print(f"  Win Rate (Daily):       {overall.get('win_rate_pct', 0.0):>15.2f} %    |  Profit Factor:        {overall.get('profit_factor', 0.0):>15.2f}")
    print(f"  Total Turnover:         {overall.get('total_turnover', 0.0):>15.2f} x    |  Annual Turnover:      {overall.get('annualized_turnover', 0.0):>15.2f} x/yr")
    print(f"  Total Friction:         {overall.get('total_friction_bps', 0.0):>15.1f} bps  |  Estimated Slippage:   {overall.get('total_slippage_bps', 0.0):>15.1f} bps")
    print(f"  Daily VaR (95%):        {overall.get('var_95_pct', 0.0):>15.2f} %    |  Daily CVaR (95%):     {overall.get('cvar_95_pct', 0.0):>15.2f} %")
    print("-" * 90)

    print(f"\n{'HISTORICAL CRISIS STRESS BREAKDOWN':^90}")
    print("-" * 90)
    print(f"  {'Crisis Name':<35} | {'Portfolio Net':>13} | {'Benchmark':>10} | {'Max DD':>9} | {'Recovery':>9}")
    print("-" * 90)
    for c in crises:
        c_name = c.get("crisis_name", c.get("crisis_id", "Crisis"))[:35]
        p_ret = f"{c.get('net_return_pct', 0.0):+.2f}%"
        b_ret = f"{c.get('benchmark_return_pct', 0.0):+.2f}%"
        mdd = f"{c.get('max_drawdown_pct', 0.0):.2f}%"
        rec = f"{c.get('recovery_days', 0)}d"
        print(f"  {c_name:<35} | {p_ret:>13} | {b_ret:>10} | {mdd:>9} | {rec:>9}")
    print("-" * 90)

    print(f"\n{'MARKET ATTRIBUTION (5 GLOBAL MARKETS)':^90}")
    print("-" * 90)
    print(f"  {'Market':<15} | {'CAGR (%)':>12} | {'Annual Vol (%)':>16} | {'Sharpe':>10} | {'Max DD (%)':>12}")
    print("-" * 90)
    for m, s in mkt_map.items():
        cagr_s = f"{s.get('cagr_pct', 0.0):.2f}%"
        vol_s = f"{s.get('annualized_volatility_pct', 0.0):.2f}%"
        sharpe_s = f"{s.get('sharpe', 0.0):.2f}"
        mdd_s = f"{s.get('mdd_pct', 0.0):.2f}%"
        print(f"  {m:<15} | {cagr_s:>12} | {vol_s:>16} | {sharpe_s:>10} | {mdd_s:>12}")
    print("=" * 90 + "\n")


# ==============================================================================
# Main Runner Entry Point
# ==============================================================================

def run_30year_backtest(
    start_date: str = "1996-01-01",
    end_date: str = "2026-08-31",
    output_dir: str | Path = "trading_system/result",
    capital: float = 100_000_000.0,
    target_vol: float = 0.12,
    rebalance_days: int = 60,
    verify: bool = False,
) -> int:
    """
    Executes the full 30-year historical backtest, computes analytics,
    exports artifacts, and runs verification if requested.
    """
    out_dir = Path(output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    logger.info("======================================================================")
    logger.info("Initializing 30-Year Historical Backtest Runner (1996–2026)")
    logger.info("  Start Date:      %s", start_date)
    logger.info("  End Date:        %s", end_date)
    logger.info("  Initial Capital: %s KRW", f"{capital:,.0f}")
    logger.info("  Target Vol:      %.1f%%", target_vol * 100.0)
    logger.info("  Rebalance Freq:  %d trading days (~quarterly)", rebalance_days)
    logger.info("  Output Dir:      %s", out_dir)
    logger.info("  Auto Verify:     %s", verify)
    logger.info("======================================================================")

    # 1. Initialize Simulation Engine
    backtester = Historical30YrBacktester(
        start_date=start_date,
        end_date=end_date,
        initial_capital=capital,
        target_volatility=target_vol,
        rebalance_freq_days=rebalance_days,
    )

    # 2. Execute Walk-Forward Simulation
    logger.info("Step 1/4: Running walk-forward simulation across 30-year horizon...")
    sim_result = backtester.run_simulation()

    # 3. Compute Benchmark Analytics
    logger.info("Step 2/4: Computing 15 standardized metrics & stress testing slices...")
    analytics = Historical30YrAnalytics(
        risk_free_rate=0.02,
        target_volatility=target_vol,
        rebalance_freq_days=rebalance_days,
    )

    summary_payload, annual_df, crisis_df = analytics.analyze_simulation_result(
        result=sim_result,
        start_date=start_date,
        end_date=end_date,
        rebalance_freq_days=rebalance_days,
        target_volatility=target_vol,
    )

    # 4. Export Structured Artifacts
    logger.info("Step 3/4: Exporting artifacts to %s...", out_dir)
    exported_artifacts = analytics.export_all_artifacts(
        summary_payload=summary_payload,
        annual_df=annual_df,
        crisis_df=crisis_df,
        output_dir=out_dir,
    )

    for name, path in exported_artifacts.items():
        logger.info("  Exported %-25s -> %s", name, path)

    # 5. Print Terminal Executive Summary Table
    print_executive_summary_table(summary_payload)

    # 6. Automatic Independent Verification
    if verify:
        logger.info("Step 4/4: Executing independent verification suite (strict mode)...")
        try:
            from scripts.verify_30year_backtest import verify_backtest_results
        except ImportError:
            from trading_system.scripts.verify_30year_backtest import verify_backtest_results

        passed, verification_summary = verify_backtest_results(result_dir=out_dir, strict=True)
        if not passed:
            logger.error("Independent verification FAILED! Total checks: %d, Failed: %d",
                         verification_summary.get("total_checks", 0),
                         verification_summary.get("failed_checks", 0))
            return 1
        logger.info("Independent verification PASSED 100%! All integrity checks satisfied.")

    logger.info("30-Year Historical Backtest Runner completed successfully (Exit Code 0).")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="30-Year Historical Backtest & Quantitative Benchmark Runner (1996–2026)"
    )
    parser.add_argument(
        "--start-date",
        type=str,
        default="1996-01-01",
        help="Backtest start date (default: 1996-01-01)",
    )
    parser.add_argument(
        "--end-date",
        type=str,
        default="2026-08-31",
        help="Backtest end date (default: 2026-08-31)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="trading_system/result",
        help="Directory to save artifacts (default: trading_system/result)",
    )
    parser.add_argument(
        "--capital",
        type=float,
        default=100_000_000.0,
        help="Initial capital in KRW (default: 100,000,000.0)",
    )
    parser.add_argument(
        "--target-vol",
        type=float,
        default=0.12,
        help="Annual target portfolio volatility (default: 0.12)",
    )
    parser.add_argument(
        "--rebalance-days",
        type=int,
        default=60,
        help="Rebalance frequency in trading days (default: 60)",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        default=False,
        help="Automatically run independent verification script after export",
    )

    args = parser.parse_args()

    exit_code = run_30year_backtest(
        start_date=args.start_date,
        end_date=args.end_date,
        output_dir=args.output_dir,
        capital=args.capital,
        target_vol=args.target_vol,
        rebalance_days=args.rebalance_days,
        verify=args.verify,
    )
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
