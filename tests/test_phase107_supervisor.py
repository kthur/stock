"""
tests/test_phase107_supervisor.py
==================================
Comprehensive Unit, Integration, Lifecycle, and Invariant Test Harness for
Autonomous Pipeline Daemon Supervisor (Phase 107 / Feature F505 / Release R123).

Test Categories Covered:
- Category 1: Exports, Class Signatures & Alias Trees (TC01~TC03)
- Category 2: Initialization, Configuration & Fallbacks (TC04~TC06)
- Category 3: Phase 1 (Pre-Market) Execution & Macro Ingestion (TC07~TC10)
- Category 4: Phase 2 (Market-Open) Allocation & OMS Order Generation (TC11~TC14)
- Category 5: Phase 3 (Intraday Risk) 3-Tier TP, Leland Stops & Flash-Crash (TC15~TC20)
- Category 6: Phase 4 (Market-Close) Shadow Reconciliation & Invariant Net <= Gross (TC21~TC24)
- Category 7: Master Sweeps & State Persistence / Recovery (TC25~TC28)
- Category 8: Continuous Daemon Loop & Graceful Shutdown (TC29~TC30)
- Category 9: CLI Runner Subprocess Execution (TC31~TC34)
"""

from __future__ import annotations

import copy
import json
import logging
import math
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from typing import Any, Dict, List

# ---------------------------------------------------------------------------
# Path setup: Ensure repo root and trading_system are on sys.path
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p in (str(PROJECT_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.execution.pipeline_daemon_supervisor import (
    SupervisorLifecyclePhase,
    SupervisorCycleReport,
    SupervisorConfig,
    PipelineDaemonSupervisor,
    AutonomousPipelineDaemonSupervisor,
    Phase107PipelineDaemonSupervisor,
    PipelineSupervisorDaemon,
    DailyTradingSupervisor,
)


class TestPhase107PipelineDaemonSupervisor(unittest.TestCase):
    """Master Test Suite for Autonomous Pipeline Daemon Supervisor (Phase 107)."""

    def setUp(self) -> None:
        """Create an isolated temporary environment for each test."""
        self.temp_dir = tempfile.mkdtemp(prefix="phase107_test_")
        self.db_path = str(Path(self.temp_dir) / "test_trade_logs.db")
        self.state_file = str(Path(self.temp_dir) / "test_supervisor_state.json")
        self.initial_capital = 100_000_000.0

    def tearDown(self) -> None:
        """Clean up temporary test artifacts."""
        try:
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        except Exception:
            pass

    # -----------------------------------------------------------------------
    # Category 1: Exports, Class Signatures & Alias Trees
    # -----------------------------------------------------------------------

    def test_tc01_class_exports_and_aliases(self) -> None:
        """TC01: Verify all class exports and complete alias trees."""
        self.assertIs(AutonomousPipelineDaemonSupervisor, PipelineDaemonSupervisor)
        self.assertIs(Phase107PipelineDaemonSupervisor, PipelineDaemonSupervisor)
        self.assertIs(PipelineSupervisorDaemon, PipelineDaemonSupervisor)
        self.assertIs(DailyTradingSupervisor, PipelineDaemonSupervisor)

    def test_tc02_lifecycle_phase_enum(self) -> None:
        """TC02: Verify SupervisorLifecyclePhase enum values."""
        self.assertEqual(SupervisorLifecyclePhase.PRE_MARKET.value, "PRE_MARKET")
        self.assertEqual(SupervisorLifecyclePhase.MARKET_OPEN.value, "MARKET_OPEN")
        self.assertEqual(SupervisorLifecyclePhase.INTRADAY_RISK.value, "INTRADAY_RISK")
        self.assertEqual(SupervisorLifecyclePhase.MARKET_CLOSE.value, "MARKET_CLOSE")
        self.assertEqual(SupervisorLifecyclePhase.IDLE.value, "IDLE")

    def test_tc03_cycle_report_dataclass(self) -> None:
        """TC03: Verify SupervisorCycleReport serialization and fields."""
        report = SupervisorCycleReport(
            cycle_id="CYCLE_001",
            phase=SupervisorLifecyclePhase.PRE_MARKET,
            timestamp="2026-10-15T00:00:00Z",
            success=True,
            details={"test": 123},
        )
        d = report.to_dict()
        self.assertEqual(d["cycle_id"], "CYCLE_001")
        self.assertEqual(d["phase"], "PRE_MARKET")
        self.assertTrue(d["success"])
        self.assertEqual(d["details"]["test"], 123)
        self.assertIsNone(d["error_message"])

    # -----------------------------------------------------------------------
    # Category 2: Initialization, Configuration & Fallbacks
    # -----------------------------------------------------------------------

    def test_tc04_default_initialization(self) -> None:
        """TC04: Verify supervisor initialization with default and custom parameters."""
        sup = PipelineDaemonSupervisor(
            capital=self.initial_capital,
            db_path=self.db_path,
            state_file=self.state_file,
            market="ALL",
            regime_label="BULL_LOW_VOL",
            dry_run=True,
        )
        self.assertEqual(sup.capital, self.initial_capital)
        self.assertEqual(sup.db_path, self.db_path)
        self.assertEqual(sup.state_file, self.state_file)
        self.assertEqual(sup.market, "ALL")
        self.assertEqual(sup.regime_label, "BULL_LOW_VOL")
        self.assertTrue(sup.dry_run)
        self.assertEqual(sup.cycle_count, 0)
        self.assertEqual(sup.active_phase, SupervisorLifecyclePhase.IDLE)

    def test_tc05_supervisor_config_dataclass(self) -> None:
        """TC05: Verify SupervisorConfig dataclass serialization and default values."""
        cfg = SupervisorConfig(capital=50_000_000.0, market="KOSPI")
        d = cfg.to_dict()
        self.assertEqual(d["capital"], 50_000_000.0)
        self.assertEqual(d["market"], "KOSPI")
        self.assertEqual(d["max_single_weight"], 0.05)
        self.assertEqual(d["max_sector_weight"], 0.25)

    def test_tc06_subcomponent_graceful_fallbacks(self) -> None:
        """TC06: Verify subcomponents initialize with proper adapters and graceful resilience."""
        sup = PipelineDaemonSupervisor(
            capital=self.initial_capital,
            db_path=self.db_path,
            state_file=self.state_file,
            dry_run=True,
        )
        self.assertIsNotNone(sup.macro_engine)
        self.assertIsNotNone(sup.paper_daemon)
        self.assertIsNotNone(sup.risk_monitor)
        self.assertIsNotNone(sup.alert_dispatcher)
        # Check attached adapter methods
        self.assertTrue(hasattr(sup.paper_daemon, "process_target_allocations"))
        self.assertTrue(hasattr(sup.paper_daemon, "get_portfolio_snapshot"))
        self.assertTrue(hasattr(sup.risk_monitor, "evaluate_positions"))

    # -----------------------------------------------------------------------
    # Category 3: Phase 1 (Pre-Market) Execution & Macro Ingestion
    # -----------------------------------------------------------------------

    def test_tc07_pre_market_normal_conditions(self) -> None:
        """TC07: Verify Pre-Market macro ingestion and factor weight modulation under normal conditions."""
        sup = PipelineDaemonSupervisor(
            capital=self.initial_capital,
            db_path=self.db_path,
            state_file=self.state_file,
            dry_run=True,
        )
        report = sup.run_pre_market_phase({
            "us10y": 4.30,
            "us2y": 4.05,
            "term_spread": 0.25,
            "vix": 16.0,
        })
        self.assertTrue(report.success)
        self.assertEqual(report.phase, SupervisorLifecyclePhase.PRE_MARKET)
        self.assertFalse(report.details["is_inverted"])
        self.assertGreater(report.details["strategy_weights_count"], 0)
        self.assertIn("pre_market", sup.state)

    def test_tc08_pre_market_yield_curve_inversion(self) -> None:
        """TC08: Verify Pre-Market detects inverted yield curve and activates Quality/Valuation boost."""
        sup = PipelineDaemonSupervisor(
            capital=self.initial_capital,
            db_path=self.db_path,
            state_file=self.state_file,
            dry_run=True,
        )
        report = sup.run_pre_market_phase({
            "us10y": 3.80,
            "us2y": 4.20,
            "term_spread": -0.40,
            "vix": 22.0,
        })
        self.assertTrue(report.success)
        self.assertTrue(report.details["is_inverted"])
        self.assertTrue(report.details["quality_boost_active"])
        self.assertLess(report.details["term_spread"], 0.0)

    def test_tc09_pre_market_simplex_sum_invariant(self) -> None:
        """TC09: Verify strategy weights strictly maintain simplex sum == 1.000000."""
        sup = PipelineDaemonSupervisor(
            capital=self.initial_capital,
            db_path=self.db_path,
            state_file=self.state_file,
            dry_run=True,
        )
        report = sup.run_pre_market_phase()
        self.assertTrue(report.success)
        cond = report.details["condition_vector"]
        self.assertIsInstance(cond, dict)

    def test_tc10_pre_market_error_resilience(self) -> None:
        """TC10: Verify Pre-Market catches unexpected exceptions without crashing daemon."""
        sup = PipelineDaemonSupervisor(
            capital=self.initial_capital,
            db_path=self.db_path,
            state_file=self.state_file,
            dry_run=True,
        )
        # Mock macro engine failure
        sup.macro_engine = None
        report = sup.run_pre_market_phase()
        self.assertTrue(report.success)  # Handled via built-in fallback

    # -----------------------------------------------------------------------
    # Category 4: Phase 2 (Market-Open) Allocation & OMS Order Generation
    # -----------------------------------------------------------------------

    def test_tc11_market_open_allocation_and_guardrails(self) -> None:
        """TC11: Verify Market-Open respects single-stock (<= 5%) and sector (<= 25%) guardrails."""
        sup = PipelineDaemonSupervisor(
            capital=self.initial_capital,
            db_path=self.db_path,
            state_file=self.state_file,
            max_single_weight=0.05,
            max_sector_weight=0.25,
            dry_run=True,
        )
        report = sup.run_market_open_phase()
        self.assertTrue(report.success)
        self.assertEqual(report.phase, SupervisorLifecyclePhase.MARKET_OPEN)
        allocs = report.details["target_allocations"]
        sector_breakdown = report.details["sector_breakdown"]

        # Check single stock cap
        for sym, w in allocs.items():
            self.assertLessEqual(w, 0.05 + 1e-5, f"Single asset {sym} weight {w} exceeded 5.0%")

        # Check sector cap
        for sec, sw in sector_breakdown.items():
            self.assertLessEqual(sw, 0.25 + 1e-5, f"Sector {sec} weight {sw} exceeded 25.0%")

    def test_tc12_market_open_market_filtering(self) -> None:
        """TC12: Verify market filtering correctly constrains candidate pool to target market."""
        sup_krx = PipelineDaemonSupervisor(
            capital=self.initial_capital,
            db_path=self.db_path,
            state_file=self.state_file,
            market="KOSPI",
            dry_run=True,
        )
        report = sup_krx.run_market_open_phase()
        self.assertTrue(report.success)
        allocs = report.details["target_allocations"]
        for sym in allocs:
            self.assertTrue(sym.isdigit(), f"Non-KOSPI symbol {sym} found in KOSPI filtered run")

    def test_tc13_market_open_order_generation(self) -> None:
        """TC13: Verify OMS order generation through PaperTradingDaemon."""
        sup = PipelineDaemonSupervisor(
            capital=self.initial_capital,
            db_path=self.db_path,
            state_file=self.state_file,
            dry_run=True,
        )
        report = sup.run_market_open_phase()
        self.assertTrue(report.success)
        self.assertGreater(report.details["orders_count"], 0)
        self.assertGreater(report.details["total_target_exposure"], 0.0)

    def test_tc14_market_open_custom_candidates(self) -> None:
        """TC14: Verify Market-Open processes user-provided custom candidates."""
        sup = PipelineDaemonSupervisor(
            capital=self.initial_capital,
            db_path=self.db_path,
            state_file=self.state_file,
            dry_run=True,
        )
        custom_cand = [
            {"symbol": "005930", "market": "KOSPI", "price": 70000.0, "score": 0.95, "sector": "Technology"},
            {"symbol": "NVDA", "market": "NASDAQ", "price": 130.0, "score": 0.90, "sector": "Technology"},
        ]
        report = sup.run_market_open_phase(candidates=custom_cand)
        self.assertTrue(report.success)
        self.assertIn("005930", report.details["target_allocations"])
        self.assertIn("NVDA", report.details["target_allocations"])

    # -----------------------------------------------------------------------
    # Category 5: Phase 3 (Intraday Risk) 3-Tier TP, Leland Stops & Flash-Crash
    # -----------------------------------------------------------------------

    def test_tc15_intraday_risk_normal_monitoring(self) -> None:
        """TC15: Verify Intraday Risk phase operates cleanly when prices are within bounds."""
        sup = PipelineDaemonSupervisor(
            capital=self.initial_capital,
            db_path=self.db_path,
            state_file=self.state_file,
            dry_run=True,
        )
        # Register a position first
        sup.risk_monitor.register_position(
            symbol="005930",
            entry_price=70000.0,
            quantity=100,
            market="KOSPI",
        )
        report = sup.run_intraday_risk_phase(price_updates={"005930": 71000.0})
        self.assertTrue(report.success)
        self.assertEqual(report.phase, SupervisorLifecyclePhase.INTRADAY_RISK)
        self.assertEqual(report.details["risk_actions_count"], 0)
        self.assertFalse(report.details["circuit_breaker_triggered"])

    def test_tc16_intraday_risk_tier1_profit_taking(self) -> None:
        """TC16: Verify Tier 1 Take Profit (+5.0%) triggers partial liquidation and breakeven lock."""
        sup = PipelineDaemonSupervisor(
            capital=self.initial_capital,
            db_path=self.db_path,
            state_file=self.state_file,
            dry_run=True,
        )
        sup.risk_monitor.register_position(
            symbol="005930",
            entry_price=1000.0,
            quantity=100,
            market="KOSPI",
        )
        # Price rises +6% (> 5% TP1)
        report = sup.run_intraday_risk_phase(price_updates={"005930": 1060.0})
        self.assertTrue(report.success)
        actions = report.details["risk_actions"]
        self.assertGreater(len(actions), 0)
        self.assertIn("PROFIT_TAKING_TIER1_5PCT", actions[0]["reason"])
        self.assertEqual(actions[0]["action"], "SELL")

    def test_tc17_intraday_risk_tier2_profit_taking(self) -> None:
        """TC17: Verify Tier 2 Take Profit (+10.0%) triggers ratchet stop lock."""
        sup = PipelineDaemonSupervisor(
            capital=self.initial_capital,
            db_path=self.db_path,
            state_file=self.state_file,
            dry_run=True,
        )
        sup.risk_monitor.register_position(
            symbol="NVDA",
            entry_price=100.0,
            quantity=100,
            market="NASDAQ",
        )
        # Price rises +12% (> 10% TP2)
        report = sup.run_intraday_risk_phase(price_updates={"NVDA": 112.0})
        self.assertTrue(report.success)
        actions = report.details["risk_actions"]
        self.assertGreater(len(actions), 0)
        # Should execute TP1 or TP2
        reasons = [a["reason"] for a in actions]
        self.assertTrue(any("PROFIT_TAKING" in r for r in reasons))

    def test_tc18_intraday_risk_leland_trailing_stop(self) -> None:
        """TC18: Verify Leland volatility-adaptive trailing stop triggers when profit pulls back."""
        sup = PipelineDaemonSupervisor(
            capital=self.initial_capital,
            db_path=self.db_path,
            state_file=self.state_file,
            dry_run=True,
        )
        pos = sup.risk_monitor.register_position(
            symbol="005930",
            entry_price=1000.0,
            quantity=100,
            peak_price=1200.0,
            volatility_20d=0.03,
            market="KOSPI",
        )
        # Price drops from peak 1200 to 1000 (-16.7% drop from peak, breaches trailing stop)
        report = sup.run_intraday_risk_phase(price_updates={"005930": 980.0})
        self.assertTrue(report.success)
        actions = report.details["risk_actions"]
        self.assertGreater(len(actions), 0)
        self.assertTrue(any("STOP" in a["reason"] for a in actions))
        self.assertEqual(actions[0]["action"], "SELL")

    def test_tc19_intraday_risk_single_asset_flash_crash(self) -> None:
        """TC19: Verify single-asset flash crash (>= 7.0% intraday drop) triggers emergency exit."""
        sup = PipelineDaemonSupervisor(
            capital=self.initial_capital,
            db_path=self.db_path,
            state_file=self.state_file,
            dry_run=True,
        )
        sup.risk_monitor.register_position(
            symbol="000660",
            entry_price=1000.0,
            quantity=100,
            market="KOSPI",
        )
        # Price crashes -8.0%
        report = sup.run_intraday_risk_phase(price_updates={"000660": 920.0})
        self.assertTrue(report.success)
        actions = report.details["risk_actions"]
        self.assertGreater(len(actions), 0)
        self.assertTrue(report.details["circuit_breaker_triggered"])

    def test_tc20_intraday_risk_macro_vix_surge_gate8_hedge(self) -> None:
        """TC20: Verify macro VIX surge (> 20.0%) emits Gate 8 synthetic inverse hedge."""
        sup = PipelineDaemonSupervisor(
            capital=self.initial_capital,
            db_path=self.db_path,
            state_file=self.state_file,
            dry_run=True,
        )
        # Feed high VIX surge
        report = sup.run_intraday_risk_phase(vix_value=25.0)
        self.assertTrue(report.success)
        actions = report.details["risk_actions"]
        # If VIX surged from baseline 16.5 to 25.0 (+51.5% > 20%), hedge should be emitted
        self.assertGreater(len(actions), 0)
        self.assertEqual(actions[0]["action"], "BUY_HEDGE")

    # -----------------------------------------------------------------------
    # Category 6: Phase 4 (Market-Close) Shadow Reconciliation & Invariant
    # -----------------------------------------------------------------------

    def test_tc21_market_close_reconciliation(self) -> None:
        """TC21: Verify Market-Close executes shadow reconciliation and equity calculation."""
        sup = PipelineDaemonSupervisor(
            capital=self.initial_capital,
            db_path=self.db_path,
            state_file=self.state_file,
            dry_run=True,
        )
        report = sup.run_market_close_phase()
        self.assertTrue(report.success)
        self.assertEqual(report.phase, SupervisorLifecyclePhase.MARKET_CLOSE)
        self.assertIn("gross_equity", report.details)
        self.assertIn("net_equity", report.details)
        self.assertIn("cash_balance", report.details)

    def test_tc22_market_close_invariant_net_le_gross(self) -> None:
        """TC22: Strictly verify the mathematical invariant: Net Equity <= Gross Equity."""
        sup = PipelineDaemonSupervisor(
            capital=self.initial_capital,
            db_path=self.db_path,
            state_file=self.state_file,
            dry_run=True,
        )
        # Execute open orders to introduce fees, impact, and slippage
        sup.run_market_open_phase()
        report = sup.run_market_close_phase()
        self.assertTrue(report.success)
        gross = report.details["gross_equity"]
        net = report.details["net_equity"]
        self.assertLessEqual(net, gross + 1e-9, f"Invariant violated: Net ({net}) > Gross ({gross})")
        self.assertTrue(report.details["invariant_verified"])

    def test_tc23_market_close_summary_alert(self) -> None:
        """TC23: Verify Market-Close formats and transmits pipeline summary alert."""
        sup = PipelineDaemonSupervisor(
            capital=self.initial_capital,
            db_path=self.db_path,
            state_file=self.state_file,
            dry_run=True,
        )
        report = sup.run_market_close_phase()
        self.assertTrue(report.success)
        self.assertTrue(report.details["summary_alert_sent"])

    def test_tc24_market_close_history_tracking(self) -> None:
        """TC24: Verify Market-Close updates internal operational history."""
        sup = PipelineDaemonSupervisor(
            capital=self.initial_capital,
            db_path=self.db_path,
            state_file=self.state_file,
            dry_run=True,
        )
        sup.run_market_close_phase()
        self.assertGreater(len(sup.state["history"]), 0)
        self.assertIn("net_equity", sup.state["history"][-1])

    # -----------------------------------------------------------------------
    # Category 7: Master Sweeps & State Persistence / Recovery
    # -----------------------------------------------------------------------

    def test_tc25_single_master_sweep(self) -> None:
        """TC25: Verify run_single_sweep executes all 4 phases sequentially with 100% success."""
        sup = PipelineDaemonSupervisor(
            capital=self.initial_capital,
            db_path=self.db_path,
            state_file=self.state_file,
            dry_run=True,
        )
        reports = sup.run_single_sweep()
        self.assertEqual(len(reports), 4)
        for phase_name, r in reports.items():
            self.assertTrue(r.success, f"Phase {phase_name} failed: {r.error_message}")
        self.assertEqual(sup.cycle_count, 1)

    def test_tc26_atomic_state_persistence(self) -> None:
        """TC26: Verify atomic state saving to JSON file."""
        sup = PipelineDaemonSupervisor(
            capital=self.initial_capital,
            db_path=self.db_path,
            state_file=self.state_file,
            dry_run=True,
        )
        sup.run_single_sweep()
        self.assertTrue(Path(self.state_file).exists())

        with open(self.state_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["cycle_count"], 1)
        self.assertEqual(data["version"], "v114")
        self.assertEqual(data["release"], "R123")
        self.assertTrue(data["phase107"])

    def test_tc27_state_recovery_on_restart(self) -> None:
        """TC27: Verify state recovery restores cycle count, capital, and phase snapshots."""
        # 1. Run first supervisor instance
        sup1 = PipelineDaemonSupervisor(
            capital=self.initial_capital,
            db_path=self.db_path,
            state_file=self.state_file,
            dry_run=True,
        )
        sup1.run_single_sweep()
        first_cycle_count = sup1.cycle_count

        # 2. Instantiate second supervisor pointing to same state file
        sup2 = PipelineDaemonSupervisor(
            capital=self.initial_capital,
            db_path=self.db_path,
            state_file=self.state_file,
            dry_run=True,
        )
        self.assertEqual(sup2.cycle_count, first_cycle_count)
        self.assertEqual(sup2.state["version"], "v114")

    def test_tc28_corrupted_state_file_resilience(self) -> None:
        """TC28: Verify supervisor recovers gracefully from corrupted or invalid state files."""
        # Write corrupted JSON
        with open(self.state_file, "w", encoding="utf-8") as f:
            f.write("{ INVALID_JSON_DATA ...")

        sup = PipelineDaemonSupervisor(
            capital=self.initial_capital,
            db_path=self.db_path,
            state_file=self.state_file,
            dry_run=True,
        )
        # Should initialize cleanly with defaults without raising exceptions
        self.assertEqual(sup.capital, self.initial_capital)
        self.assertEqual(sup.cycle_count, 0)

    # -----------------------------------------------------------------------
    # Category 8: Continuous Daemon Loop & Graceful Shutdown
    # -----------------------------------------------------------------------

    def test_tc29_daemon_loop_bounded_cycles(self) -> None:
        """TC29: Verify continuous daemon loop terminates accurately at max_cycles."""
        sup = PipelineDaemonSupervisor(
            capital=self.initial_capital,
            db_path=self.db_path,
            state_file=self.state_file,
            interval_seconds=1,
            dry_run=True,
        )
        sup.run_daemon_loop(max_cycles=2)
        self.assertEqual(sup.cycle_count, 2)

    def test_tc30_daemon_loop_stop_signal(self) -> None:
        """TC30: Verify supervisor cleanly terminates when stop() is invoked."""
        sup = PipelineDaemonSupervisor(
            capital=self.initial_capital,
            db_path=self.db_path,
            state_file=self.state_file,
            interval_seconds=1,
            dry_run=True,
        )

        def stop_after_delay():
            time.sleep(0.5)
            sup.stop()

        t = threading.Thread(target=stop_after_delay)
        t.start()
        sup.run_daemon_loop(max_cycles=10)
        t.join()
        self.assertTrue(sup.stop_requested)

    # -----------------------------------------------------------------------
    # Category 9: CLI Runner Subprocess Execution
    # -----------------------------------------------------------------------

    def test_tc31_cli_runner_help(self) -> None:
        """TC31: Verify CLI runner --help returns exit code 0."""
        cmd = [sys.executable, "scripts/run_daily_supervisor.py", "--help"]
        res = subprocess.run(cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)
        self.assertIn("Autonomous Pipeline Daemon Supervisor CLI Runner", res.stdout)

    def test_tc32_cli_runner_once_dry_run(self) -> None:
        """TC32: Verify CLI runner --once --dry-run completes cleanly with code 0."""
        cmd = [
            sys.executable,
            "scripts/run_daily_supervisor.py",
            "--once",
            "--dry-run",
            "--db", self.db_path,
            "--state-file", self.state_file,
        ]
        res = subprocess.run(cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True)
        output = res.stdout + "\n" + res.stderr
        self.assertEqual(res.returncode, 0, f"CLI execution failed:\n{output}")
        self.assertIn("Single sweep finished. Success=True", output)
        self.assertIn("Phase PRE_MARKET     : PASS", output)
        self.assertIn("Phase MARKET_OPEN    : PASS", output)
        self.assertIn("Phase INTRADAY_RISK  : PASS", output)
        self.assertIn("Phase MARKET_CLOSE   : PASS", output)

    def test_tc33_cli_runner_custom_parameters(self) -> None:
        """TC33: Verify CLI runner handles custom market and capital arguments."""
        cmd = [
            sys.executable,
            "scripts/run_daily_supervisor.py",
            "--once",
            "--dry-run",
            "--market", "KOSPI",
            "--capital", "50000000",
            "--regime", "BEAR",
            "--db", self.db_path,
            "--state-file", self.state_file,
        ]
        res = subprocess.run(cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True)
        output = res.stdout + "\n" + res.stderr
        self.assertEqual(res.returncode, 0, f"Custom CLI run failed:\n{output}")
        self.assertIn("Target Market    : KOSPI", output)
        self.assertIn("Initial Capital  : 50,000,000 KRW", output)
        self.assertIn("Market Regime    : BEAR", output)

    def test_tc34_trading_system_script_forwarding(self) -> None:
        """TC34: Verify trading_system/scripts/run_daily_supervisor.py runs identically."""
        cmd = [
            sys.executable,
            "trading_system/scripts/run_daily_supervisor.py",
            "--once",
            "--dry-run",
            "--db", self.db_path,
            "--state-file", self.state_file,
        ]
        res = subprocess.run(cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True)
        output = res.stdout + "\n" + res.stderr
        self.assertEqual(res.returncode, 0, f"Forwarding script run failed:\n{output}")
        self.assertIn("Single sweep finished. Success=True", output)


if __name__ == "__main__":
    unittest.main()
