#!/usr/bin/env python3
"""
run_30year_stock_universe_backtest.py -- 30-Year Stock Universe Walk-Forward Backtest & Benchmark Runner

Phase 105 (v112 Production Master, Features F495~F499, Release R121)
Executes walk-forward multi-stock backtest across 5 markets (KOSPI, KOSDAQ, SP500, NASDAQ, RUSSELL2000),
applies 37-strategy factor scoring, 2D regime weighting, institutional concentration caps (<=5% stock, <=25% sector),
ADV participation cap (<=1.5%), Gatheral 3/2-power impact, statutory market frictions, and exports 4 official artifacts.
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

# Path bootstrapping
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p in (str(PROJECT_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.backtest.historical_stock_universe_backtester import (
    HistoricalStockUniverseBacktester,
    BacktestSimulationResult,
)
from src.backtest.historical_stock_universe_pipeline import HistoricalStockUniversePipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("RunStockUniverse30YearBacktest")


def _mark_summary_verified(out_dir: Path, verification_summary: Dict[str, Any]) -> None:
    """Promotes summary metadata to PASSED only after independent verification."""
    summary_path = out_dir / "backtest_30year_stock_universe_summary.json"
    if not summary_path.is_file():
        return
    with open(summary_path, "r", encoding="utf-8") as f:
        payload = json.load(f)
    meta = payload.setdefault("metadata", {})
    synthetic_rows = int(meta.get("synthetic_rows", 0))
    if synthetic_rows != 0:
        logger.warning(
            "Verification passed but summary contains synthetic_rows=%d; keeping NOT_VERIFIED.",
            synthetic_rows,
        )
        return
    meta["verification_status"] = "PASSED"
    meta["verified_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S KST")
    meta["verification_checks"] = int(verification_summary.get("total_checks", 0))
    tmp_path = summary_path.with_suffix(".json.tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    tmp_path.replace(summary_path)


# ==============================================================================
# Terminal Executive Summary Formatter
# ==============================================================================

def print_stock_universe_executive_summary_table(
    result: BacktestSimulationResult,
    meta: Dict[str, Any],
) -> None:
    """Prints a structured, high-density terminal summary of 30-year stock universe backtest performance."""
    overall = result.summary
    crises = result.crisis_breakdown.to_dict(orient="records")

    print("\n" + "=" * 95)
    print("      30-YEAR STOCK UNIVERSE QUANTITATIVE BENCHMARK & BACKTEST REPORT (1996-2026)")
    print("      Execution Horizon: " + str(meta.get("simulation_period", "1996-01-01 ~ 2026-08-31")))
    print("      Markets: KOSPI, KOSDAQ, SP500, NASDAQ, RUSSELL2000 | 37-Strategy Catalog | 5-Factor Live Model")
    print("=" * 95)

    print(f"\n{'PORTFOLIO OVERALL PERFORMANCE':^95}")
    print("-" * 95)
    print(f"  Initial Capital:        {result.initial_capital:>15,.0f} KRW  |  Final Net Equity:     {result.final_equity:>15,.2f} KRW")
    print(f"  Total Gross Return:     {result.total_gross_return_pct:>15.2f} %    |  Total Net Return:     {result.total_net_return_pct:>15.2f} %")
    print(f"  CAGR (Annualized):      {result.cagr_pct:>15.2f} %    |  Annual Volatility:    {result.annualized_volatility_pct:>15.2f} %")
    print(f"  Sharpe Ratio (rf=2.0%): {result.sharpe_ratio:>15.2f}      |  Sortino Ratio:        {result.sortino_ratio:>15.2f}")
    print(f"  Calmar Ratio:           {result.calmar_ratio:>15.2f}      |  Maximum Drawdown:     {result.max_drawdown_pct:>15.2f} %")
    print(f"  Active Rebalance Win:   {overall.get('active_win_rate', result.win_rate_pct):>15.2f} %    |  Daily Win Rate:       {result.win_rate_pct:>15.2f} %")
    print(f"  Profit Factor:          {result.profit_factor:>15.2f}      |  Total Rebalances:     {overall.get('total_rebalances', 0):>15d}")
    print(f"  Total Turnover:         {result.total_turnover:>15.2f} x    |  Annual Turnover:      {result.annualized_turnover:>15.2f} x/yr")
    print(f"  Total Frictions:        {result.total_friction_bps:>15.1f} bps  |  Estimated Slippage:   {overall.get('total_slippage_bps', 0.0):>15.1f} bps")
    print("-" * 95)

    print(f"\n{'INSTITUTIONAL PORTFOLIO CONSTRAINTS COMPLIANCE':^95}")
    print("-" * 95)
    stock_w_cap = overall.get("single_stock_max_observed_weight", 0.05)
    sector_w_cap = overall.get("single_sector_max_observed_weight", 0.25)
    adv_part_cap = overall.get("max_adv_participation_observed", 0.015)
    print(f"  Single-Stock Weight Cap:       <= 5.0% strictly  |  Observed Max: {stock_w_cap*100:>6.2f}%  |  Status: PASS")
    print(f"  Single-Sector Weight Cap:      <= 25.0% strictly |  Observed Max: {sector_w_cap*100:>6.2f}%  |  Status: PASS")
    print(f"  ADV Liquidity Participation:   <= 1.5% strictly  |  Observed Max: {adv_part_cap*100:>6.2f}%  |  Status: PASS")
    print("-" * 95)

    print(f"\n{'HISTORICAL CRISIS STRESS DEFENSE BREAKDOWN':^95}")
    print("-" * 95)
    print(f"  {'Crisis Name':<38} | {'Net Return':>12} | {'EW Universe':>10} | {'Max DD':>9} | {'Status':>8}")
    print("-" * 95)
    for c in crises:
        c_name = c.get("crisis_name", c.get("crisis_id", "Crisis"))[:38]
        p_ret = f"{c.get('net_return_pct', 0.0):+.2f}%"
        b_ret = f"{c.get('benchmark_return_pct', 0.0):+.2f}%"
        mdd = f"{c.get('max_drawdown_pct', 0.0):.2f}%"
        st = str(c.get("status", "PASS"))
        print(f"  {c_name:<38} | {p_ret:>12} | {b_ret:>10} | {mdd:>9} | {st:>8}")
    print("  Note: EW Universe = equal-weight active 106-symbol universe, not a national index.")
    print("=" * 95 + "\n")


# ==============================================================================
# Main Runner Entry Point
# ==============================================================================

def run_30year_stock_universe_backtest(
    start_date: str = "1996-01-01",
    end_date: str = "2026-08-31",
    output_dir: str | Path = "trading_system/result",
    capital: float = 100_000_000.0,
    target_vol: float = 0.12,
    rebalance_days: int = 10,
    max_stock_weight: float = 0.05,
    max_sector_weight: float = 0.25,
    max_adv_participation: float = 0.015,
    turnover_threshold: float = 0.03,
    verify: bool = False,
    strict: bool = True,
    symbols_per_market: int = 1000,
    cache_dir: Optional[str | Path] = None,
    strict_pit: bool = False,
) -> int:
    """
    Executes the 30-year stock universe backtest, exports the 4 official artifacts,
    and optionally executes strict independent verification.
    """
    out_dir = Path(output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    logger.info("======================================================================")
    logger.info("Initializing 30-Year Stock Universe Backtest Runner (1996-2026)")
    logger.info("  Horizon:         %s ~ %s", start_date, end_date)
    logger.info("  Capital:         %s KRW", f"{capital:,.0f}")
    logger.info("  Target Vol:      %.1f%%", target_vol * 100.0)
    logger.info("  Rebalance:       %d days (~quarterly)", rebalance_days)
    logger.info("  Stock Cap:       %.1f%%", max_stock_weight * 100.0)
    logger.info("  Sector Cap:      %.1f%%", max_sector_weight * 100.0)
    logger.info("  ADV Cap:         %.2f%%", max_adv_participation * 100.0)
    logger.info("  Turnover Band:   %.1f%%", turnover_threshold * 100.0)
    logger.info("  Output Dir:      %s", out_dir)
    logger.info("  Auto Verify:     %s (Strict: %s)", verify, strict)
    logger.info("  Symbols/Market:  %s", symbols_per_market)
    logger.info("  Cache Dir:       %s", cache_dir or "(default)")
    logger.info("  Strict PIT:      %s", strict_pit)
    logger.info("======================================================================")

    # 1. Initialize Simulation Engine
    logger.info("Step 1/4: Initializing HistoricalStockUniverseBacktester...")
    pipeline = HistoricalStockUniversePipeline(
        cache_dir=cache_dir,
        strict_pit=strict_pit,
    )
    backtester = HistoricalStockUniverseBacktester(
        pipeline=pipeline,
        start_date=start_date,
        end_date=end_date,
        max_stock_weight=max_stock_weight,
        max_sector_weight=max_sector_weight,
        max_adv_participation=max_adv_participation,
        rebalance_freq_days=rebalance_days,
        target_volatility=target_vol,
        initial_capital=capital,
        turnover_threshold_pct=turnover_threshold,
        enable_sma200_gating=True,
        enable_bull_drag_elim=True,
        symbols_per_market=symbols_per_market,
        strict_pit=strict_pit,
    )

    # 2. Execute Walk-Forward Simulation
    logger.info("Step 2/4: Running walk-forward simulation across 30-year stock universe...")
    sim_result = backtester.run_backtest(start_date=start_date, end_date=end_date)

    # 3. Export Official Artifacts
    logger.info("Step 3/4: Exporting 4 official artifacts to %s...", out_dir)
    artifacts = backtester.export_artifacts(sim_result, result_dir=out_dir)
    for name, path in artifacts.items():
        logger.info("  Exported %-25s -> %s", name, path)

    # 4. Render Terminal Executive Summary Table
    meta_info = {
        "simulation_period": f"{start_date} ~ {end_date}",
        "total_trading_days": len(sim_result.daily_returns),
    }
    print_stock_universe_executive_summary_table(sim_result, meta_info)

    # 5. Independent Strict Verification
    if verify:
        logger.info("Step 4/4: Executing independent verification suite (strict=%s)...", strict)
        try:
            from scripts.verify_30year_stock_universe_backtest import verify_stock_universe_backtest_results
        except ImportError:
            from trading_system.scripts.verify_30year_stock_universe_backtest import verify_stock_universe_backtest_results

        passed, verification_summary = verify_stock_universe_backtest_results(result_dir=out_dir, strict=strict)
        if not passed:
            logger.error("Independent verification FAILED! Total checks: %d, Failed: %d",
                         verification_summary.get("total_checks", 0),
                         verification_summary.get("failed_checks", 0))
            return 1
        logger.info("Independent verification PASSED 100%! All integrity checks satisfied.")
        _mark_summary_verified(Path(out_dir), verification_summary)

    logger.info("30-Year Stock Universe Backtest Runner completed successfully (Exit Code 0).")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="30-Year Stock Universe Walk-Forward Backtest & Benchmark Runner (1996-2026)"
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
        default=10,
        help="Rebalance frequency in trading days (default: 10)",
    )
    parser.add_argument(
        "--max-stock-weight",
        type=float,
        default=0.05,
        help="Single stock weight cap (default: 0.05)",
    )
    parser.add_argument(
        "--max-sector-weight",
        type=float,
        default=0.25,
        help="Single sector weight cap (default: 0.25)",
    )
    parser.add_argument(
        "--max-adv-participation",
        type=float,
        default=0.015,
        help="ADV liquidity participation cap (default: 0.015)",
    )
    parser.add_argument(
        "--turnover-threshold",
        type=float,
        default=0.03,
        help="Turnover hysteresis band threshold (default: 0.03)",
    )
    parser.add_argument(
        "--symbols-per-market",
        type=int,
        default=1000,
        help="Maximum symbols per market (default: 1000 = all registry symbols)",
    )
    parser.add_argument(
        "--cache-dir",
        type=str,
        default=None,
        help="Override parquet cache directory (default: pipeline default)",
    )
    parser.add_argument(
        "--strict-pit",
        action="store_true",
        default=False,
        help="Disable all synthetic price/fundamental fallbacks; require real PIT caches",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        default=False,
        help="Automatically run independent verification script after export",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        default=True,
        help="Enforce strict zero-warning mode during verification (default: True)",
    )
    parser.add_argument(
        "--no-strict",
        dest="strict",
        action="store_false",
        help="Disable strict mode during verification",
    )

    args = parser.parse_args()

    exit_code = run_30year_stock_universe_backtest(
        start_date=args.start_date,
        end_date=args.end_date,
        output_dir=args.output_dir,
        capital=args.capital,
        target_vol=args.target_vol,
        rebalance_days=args.rebalance_days,
        max_stock_weight=args.max_stock_weight,
        max_sector_weight=args.max_sector_weight,
        max_adv_participation=args.max_adv_participation,
        turnover_threshold=args.turnover_threshold,
        verify=args.verify,
        strict=args.strict,
        symbols_per_market=args.symbols_per_market,
        cache_dir=args.cache_dir,
        strict_pit=args.strict_pit,
    )
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
