"""
tests/test_phase106_paper_trading.py — Comprehensive Unit, Integration & Invariant Test Harness.

Phase 106 / Feature F501 / Release R122 (v113 Production Master)
Milestone 2: Autonomous Paper-Trading Shadow Execution Daemon.

Test Categories Covered:
- Category 1: Exports, Class Signatures & Alias Trees (TC01~TC03)
- Category 2: Database Schema & Table Initialization (TC04~TC06)
- Category 3: Ingestion of Target Allocations (TC07~TC10)
- Category 4: Rebalance Delta Computation (TC11~TC14)
- Category 5: The 8 OMS Safety Gates Enforcement (TC15~TC23)
- Category 6: Realistic Execution Simulation (Gatheral 3/2 & Fast LOB) (TC24~TC26)
- Category 7: Mathematical Invariant: Net Equity <= Gross Equity (TC27~TC28)
- Category 8: Dry-Run Mode & CLI Runner Subprocess (TC29~TC30)
"""

from __future__ import annotations

import math
import os
import sys
import sqlite3
import tempfile
import unittest
import subprocess
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Path setup: Ensure repo root and trading_system are on sys.path
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p in (str(PROJECT_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.execution.paper_trading_daemon import (
    PaperOrderAction,
    PaperExecutionStatus,
    PaperExecutionRecord,
    PortfolioSnapshot,
    PaperTradingDaemon,
    AutonomousPaperTradingDaemon,
    PaperTradingExecutionDaemon,
    ShadowExecutionDaemon,
    Phase106PaperTradingDaemon,
)


class TestPhase106PaperTradingDaemon(unittest.TestCase):
    """Comprehensive test harness for PaperTradingDaemon."""

    def setUp(self):
        """Create a dedicated temporary directory and database for each test."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_trade_logs.db")
        self.daemon = PaperTradingDaemon(
            initial_capital=100_000_000.0,
            db_path=self.db_path,
            base_currency="KRW",
            usd_krw=1350.0,
            regime_label="BULL_LOW_VOL",
            crisis_level="NORMAL",
        )

    def tearDown(self):
        """Clean up temporary directory."""
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    # =========================================================================
    # Category 1: Exports, Class Signatures & Alias Trees (TC01~TC03)
    # =========================================================================

    def test_tc01_initialization_defaults(self):
        """TC01: Verify default parameters and initial portfolio state."""
        d = self.daemon
        self.assertEqual(d.initial_capital, 100_000_000.0)
        self.assertEqual(d.gross_equity, 100_000_000.0)
        self.assertEqual(d.net_equity, 100_000_000.0)
        self.assertEqual(d.cash_balance, 100_000_000.0)
        self.assertEqual(d.regime_label, "BULL_LOW_VOL")
        self.assertEqual(d.crisis_level, "NORMAL")
        self.assertEqual(len(d.holdings), 0)
        self.assertEqual(d.version, 113)

    def test_tc02_alias_trees_identity(self):
        """TC02: Verify all backward compatibility alias trees point to PaperTradingDaemon."""
        self.assertIs(AutonomousPaperTradingDaemon, PaperTradingDaemon)
        self.assertIs(PaperTradingExecutionDaemon, PaperTradingDaemon)
        self.assertIs(ShadowExecutionDaemon, PaperTradingDaemon)
        self.assertIs(Phase106PaperTradingDaemon, PaperTradingDaemon)

    def test_tc03_enums_and_dataclasses(self):
        """TC03: Verify dataclasses and enums convert to dict cleanly."""
        rec = PaperExecutionRecord(
            order_id="ORD_BUY_005930_TEST",
            symbol="005930",
            market="KOSPI",
            action=PaperOrderAction.BUY.value,
            target_price=70000.0,
            executed_price=70050.0,
            quantity=100,
            target_amount=7000000.0,
            executed_amount=7005000.0,
            slippage_bps=7.14,
            fee_amount=1050.75,
            net_amount=7006050.75,
            status=PaperExecutionStatus.FILLED.value,
            executed_at="2026-10-14 15:30:00",
        )
        d = rec.to_dict()
        self.assertEqual(d["symbol"], "005930")
        self.assertEqual(d["action"], "BUY")
        self.assertEqual(d["status"], "FILLED")
        self.assertEqual(d["executed_price"], 70050.0)

        snap = PortfolioSnapshot(
            timestamp="2026-10-14 15:30:00",
            gross_equity=100_000_000.0,
            net_equity=99_998_949.25,
            cash_balance=92_993_949.25,
            invested_value=7_005_000.0,
            holdings_count=1,
        )
        sd = snap.to_dict()
        self.assertEqual(sd["holdings_count"], 1)
        self.assertLessEqual(sd["net_equity"], sd["gross_equity"])

    # =========================================================================
    # Category 2: Database Schema & Table Initialization (TC04~TC06)
    # =========================================================================

    def test_tc04_sqlite_schema_creation(self):
        """TC04: Verify paper_executions table is created with all 20+ required columns."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cols = [r[1] for r in cursor.execute("PRAGMA table_info(paper_executions)").fetchall()]
        conn.close()

        required_cols = [
            "execution_id", "order_id", "symbol", "market", "action",
            "target_price", "executed_price", "quantity", "target_amount",
            "executed_amount", "slippage_bps", "market_impact_bps", "fee_amount",
            "net_amount", "gross_pnl", "net_pnl", "status", "executed_at",
            "gate_passed", "execution_mode", "notes"
        ]
        for col in required_cols:
            self.assertIn(col, cols, f"Required column '{col}' missing from paper_executions")

    def test_tc05_sqlite_indices_creation(self):
        """TC05: Verify all 4 required indices are created on paper_executions."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        indices = [r[1] for r in cursor.execute("PRAGMA index_list(paper_executions)").fetchall()]
        conn.close()

        self.assertIn("idx_paper_exec_symbol", indices)
        self.assertIn("idx_paper_exec_order_id", indices)
        self.assertIn("idx_paper_exec_date", indices)
        self.assertIn("idx_paper_exec_market", indices)

    def test_tc06_persist_and_query_execution_record(self):
        """TC06: Verify record persistence and retrieval via get_paper_executions."""
        rec = PaperExecutionRecord(
            order_id="ORD_TEST_PERSIST_01",
            symbol="005930",
            market="KOSPI",
            action="BUY",
            target_price=70000.0,
            executed_price=70050.0,
            quantity=50,
            target_amount=3500000.0,
            executed_amount=3502500.0,
            slippage_bps=7.14,
            market_impact_bps=2.5,
            fee_amount=525.0,
            net_amount=3503025.0,
            gross_pnl=0.0,
            net_pnl=0.0,
            status="FILLED",
            executed_at="2026-10-14 10:00:00",
            gate_passed="ALL_8_GATES",
            execution_mode="SHADOW_PAPER",
        )
        exec_id = self.daemon.persist_execution(rec)
        self.assertGreater(exec_id, 0)

        records = self.daemon.get_paper_executions(limit=10, symbol="005930")
        self.assertEqual(len(records), 1)
        r0 = records[0]
        self.assertEqual(r0["order_id"], "ORD_TEST_PERSIST_01")
        self.assertEqual(r0["symbol"], "005930")
        self.assertEqual(r0["executed_price"], 70050.0)
        self.assertEqual(r0["quantity"], 50)

    # =========================================================================
    # Category 3: Ingestion of Target Allocations (TC07~TC10)
    # =========================================================================

    def test_tc07_ingest_from_dataframe(self):
        """TC07: Ingest target allocations from pandas DataFrame."""
        df = pd.DataFrame([
            {"symbol": "005930", "weight": 0.05, "target_price": 70000.0, "market": "KOSPI", "volatility": 0.018, "adv_20d": 1e10, "predicted_return": 0.08},
            {"symbol": "AAPL", "weight": 0.04, "target_price": 220.0, "market": "NASDAQ", "volatility": 0.015, "adv_20d": 5e8, "predicted_return": 0.06},
        ])
        targets = self.daemon.ingest_target_allocations(df)
        self.assertEqual(len(targets), 2)
        self.assertEqual(targets[0]["symbol"], "005930")
        self.assertAlmostEqual(targets[0]["target_weight"], 0.05)
        self.assertEqual(targets[1]["symbol"], "AAPL")
        self.assertAlmostEqual(targets[1]["target_weight"], 0.04)

    def test_tc08_ingest_from_text_file(self):
        """TC08: Ingest target allocations from portfolio_allocation.txt."""
        sample_txt = """=== Portfolio Allocation Recommendations ===
No. Symbol    Name                Market    Return    Volatility  Weight    Amount         
--------------------------------------------------------------------------------------------
1   0131D0    키움히어로제2호스팩          KOSDAQ     112.5%        0.19%     5.00%    50,000,000
2   005930    삼성전자                KOSPI       85.2%        0.24%     5.00%    50,000,000
--------------------------------------------------------------------------------------------
"""
        txt_path = os.path.join(self.temp_dir.name, "portfolio_allocation.txt")
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(sample_txt)

        targets = self.daemon.ingest_target_allocations(txt_path)
        self.assertEqual(len(targets), 2)
        syms = [t["symbol"] for t in targets]
        self.assertIn("0131D0", syms)
        self.assertIn("005930", syms)
        self.assertAlmostEqual(targets[0]["target_weight"], 0.05)

    def test_tc09_ingest_from_dict(self):
        """TC09: Ingest target allocations from dictionary."""
        d_input = {
            "005930": 0.05,
            "000660": {"weight": 0.04, "target_price": 180000.0, "market": "KOSPI", "predicted_return": 0.09},
        }
        targets = self.daemon.ingest_target_allocations(d_input)
        self.assertEqual(len(targets), 2)
        sym_map = {t["symbol"]: t for t in targets}
        self.assertAlmostEqual(sym_map["005930"]["target_weight"], 0.05)
        self.assertAlmostEqual(sym_map["000660"]["target_weight"], 0.04)
        self.assertEqual(sym_map["000660"]["target_price"], 180000.0)

    def test_tc10_ingest_empty_and_corrupted(self):
        """TC10: Ingest edge cases (empty list, empty dict, None)."""
        self.assertEqual(self.daemon.ingest_target_allocations([]), [])
        self.assertEqual(self.daemon.ingest_target_allocations({}), [])
        self.assertEqual(self.daemon.ingest_target_allocations(None), [])

    # =========================================================================
    # Category 4: Rebalance Delta Computation (TC11~TC14)
    # =========================================================================

    def test_tc11_compute_deltas_positive_buy(self):
        """TC11: Positive delta creates BUY action with correct shares."""
        targets = [{
            "symbol": "005930",
            "target_weight": 0.05,  # 5,000,000 KRW
            "target_price": 50000.0,
            "market": "KOSPI",
            "volatility": 0.015,
            "adv_20d": 1e10,
            "predicted_return": 0.07,
        }]
        deltas = self.daemon.compute_rebalance_deltas(targets)
        self.assertEqual(len(deltas), 1)
        d0 = deltas[0]
        self.assertEqual(d0["action"], PaperOrderAction.BUY.value)
        self.assertEqual(d0["delta_quantity"], 100)  # 5,000,000 / 50,000 = 100
        self.assertTrue(d0["is_fresh_entry"])

    def test_tc12_compute_deltas_negative_sell(self):
        """TC12: Negative delta creates SELL action when target shares < current shares."""
        # Set existing holding of 200 shares
        self.daemon.holdings["005930"] = {
            "quantity": 200,
            "avg_cost": 50000.0,
            "gross_cost": 50000.0,
            "market": "KOSPI",
            "current_price": 50000.0,
        }
        targets = [{
            "symbol": "005930",
            "target_weight": 0.05,  # 5,000,000 KRW -> 100 shares
            "target_price": 50000.0,
            "market": "KOSPI",
            "volatility": 0.015,
            "adv_20d": 1e10,
            "predicted_return": 0.07,
        }]
        deltas = self.daemon.compute_rebalance_deltas(targets)
        self.assertEqual(len(deltas), 1)
        d0 = deltas[0]
        self.assertEqual(d0["action"], PaperOrderAction.SELL.value)
        self.assertEqual(d0["delta_quantity"], -100)  # 100 - 200 = -100
        self.assertFalse(d0["is_liquidation"])

    def test_tc13_compute_deltas_full_liquidation(self):
        """TC13: Holding present in current portfolio but omitted from targets is fully liquidated."""
        self.daemon.holdings["005930"] = {
            "quantity": 150,
            "avg_cost": 50000.0,
            "gross_cost": 50000.0,
            "market": "KOSPI",
            "current_price": 50000.0,
        }
        # Empty target list -> full liquidation
        deltas = self.daemon.compute_rebalance_deltas([])
        self.assertEqual(len(deltas), 1)
        d0 = deltas[0]
        self.assertEqual(d0["symbol"], "005930")
        self.assertEqual(d0["action"], PaperOrderAction.SELL.value)
        self.assertEqual(d0["delta_quantity"], -150)
        self.assertTrue(d0["is_liquidation"])

    def test_tc14_compute_deltas_zero_hold(self):
        """TC14: Target shares exactly equal current shares -> HOLD action."""
        self.daemon.holdings["005930"] = {
            "quantity": 100,
            "avg_cost": 50000.0,
            "gross_cost": 50000.0,
            "market": "KOSPI",
            "current_price": 50000.0,
        }
        targets = [{
            "symbol": "005930",
            "target_weight": 0.05,  # 100 shares
            "target_price": 50000.0,
            "market": "KOSPI",
            "volatility": 0.015,
            "adv_20d": 1e10,
            "predicted_return": 0.07,
        }]
        deltas = self.daemon.compute_rebalance_deltas(targets)
        self.assertEqual(len(deltas), 1)
        self.assertEqual(deltas[0]["action"], PaperOrderAction.HOLD.value)
        self.assertEqual(deltas[0]["delta_quantity"], 0)

    # =========================================================================
    # Category 5: The 8 OMS Safety Gates Enforcement (TC15~TC23)
    # =========================================================================

    def test_tc15_gate1_severe_crisis_blocks_buy(self):
        """TC15: Gate 1: Crisis Level SEVERE blocks new BUY entries."""
        self.daemon.crisis_level = "SEVERE"
        targets = [{
            "symbol": "005930",
            "target_weight": 0.05,
            "target_price": 50000.0,
            "market": "KOSPI",
            "volatility": 0.015,
            "adv_20d": 1e10,
            "predicted_return": 0.07,
        }]
        deltas = self.daemon.compute_rebalance_deltas(targets)
        approved, suppressed = self.daemon.evaluate_oms_safety_gates(deltas)
        self.assertEqual(len(approved), 0)
        self.assertEqual(len(suppressed), 1)
        self.assertEqual(suppressed[0]["gate_passed"], "GATE1_SEVERE_CRISIS_BLOCKED")

    def test_tc16_gate2_kill_switch_active_blocks_all(self):
        """TC16: Gate 2: Emergency Kill Switch blocks all order generation."""
        os.environ["KILL_SWITCH"] = "1"
        try:
            targets = [{
                "symbol": "005930",
                "target_weight": 0.05,
                "target_price": 50000.0,
                "market": "KOSPI",
                "volatility": 0.015,
                "adv_20d": 1e10,
                "predicted_return": 0.07,
            }]
            deltas = self.daemon.compute_rebalance_deltas(targets)
            approved, suppressed = self.daemon.evaluate_oms_safety_gates(deltas)
            self.assertEqual(len(approved), 0)
            self.assertEqual(len(suppressed), 1)
            self.assertEqual(suppressed[0]["gate_passed"], "GATE2_KILL_SWITCH_ACTIVE")
        finally:
            os.environ.pop("KILL_SWITCH", None)


    def test_tc17_gate3_leland_buffer_suppresses_minor_drift(self):
        """TC17: Gate 3: Weight drift within [-0.5%, +0.5%] is suppressed as noise."""
        # Current weight is 5.0%, target weight is 5.2% (drift = 0.2% <= 0.5% bandwidth)
        self.daemon.holdings["005930"] = {
            "quantity": 100,  # 5,000,000 KRW = 5.0%
            "avg_cost": 50000.0,
            "gross_cost": 50000.0,
            "market": "KOSPI",
            "current_price": 50000.0,
        }
        targets = [{
            "symbol": "005930",
            "target_weight": 0.052,  # 5.2% -> drift 0.2%
            "target_price": 50000.0,
            "market": "KOSPI",
            "volatility": 0.015,
            "adv_20d": 1e10,
            "predicted_return": 0.07,
        }]
        deltas = self.daemon.compute_rebalance_deltas(targets)
        approved, suppressed = self.daemon.evaluate_oms_safety_gates(deltas)
        self.assertEqual(len(approved), 0)
        self.assertEqual(len(suppressed), 1)
        self.assertEqual(suppressed[0]["gate_passed"], "GATE3_LELAND_BUFFER_SUPPRESSED")

    def test_tc18_gate3_fresh_entry_bypasses_leland_buffer(self):
        """TC18: Gate 3 Bypass: Fresh entry (q_curr=0, target > 0) bypasses Leland buffer."""
        # Target weight 0.2% (which is <= bandwidth), but since q_curr = 0, it must pass!
        targets = [{
            "symbol": "005930",
            "target_weight": 0.003,  # 0.3% <= 0.5% bandwidth
            "target_price": 50000.0,
            "market": "KOSPI",
            "volatility": 0.015,
            "adv_20d": 1e10,
            "predicted_return": 0.07,
        }]
        deltas = self.daemon.compute_rebalance_deltas(targets)
        approved, suppressed = self.daemon.evaluate_oms_safety_gates(deltas)
        self.assertEqual(len(approved), 1)
        self.assertEqual(len(suppressed), 0)
        self.assertEqual(approved[0]["symbol"], "005930")

    def test_tc19_gate3_full_exit_bypasses_leland_buffer(self):
        """TC19: Gate 3 Bypass: Full exit (target=0, q_curr>0) bypasses Leland buffer."""
        self.daemon.holdings["005930"] = {
            "quantity": 10,  # 0.5% weight
            "avg_cost": 50000.0,
            "gross_cost": 50000.0,
            "market": "KOSPI",
            "current_price": 50000.0,
        }
        # Liquidate to 0
        deltas = self.daemon.compute_rebalance_deltas([])
        approved, suppressed = self.daemon.evaluate_oms_safety_gates(deltas)
        self.assertEqual(len(approved), 1)
        self.assertEqual(approved[0]["action"], PaperOrderAction.SELL.value)
        self.assertTrue(approved[0]["is_liquidation"])

    def test_tc20_gate4_price_limit_lock(self):
        """TC20: Gate 4: Daily price surge >= +29.5% on KRX blocks BUY order."""
        targets = [{
            "symbol": "005930",
            "target_weight": 0.05,
            "target_price": 50000.0,
            "market": "KOSPI",
            "volatility": 0.015,
            "adv_20d": 1e10,
            "predicted_return": 0.07,
        }]
        deltas = self.daemon.compute_rebalance_deltas(targets)
        market_data = {"005930": {"daily_change_pct": 0.298}}  # +29.8% upper limit
        approved, suppressed = self.daemon.evaluate_oms_safety_gates(deltas, market_data=market_data)
        self.assertEqual(len(approved), 0)
        self.assertEqual(len(suppressed), 1)
        self.assertEqual(suppressed[0]["gate_passed"], "GATE4_UPPER_LIMIT_LOCKED")

    def test_tc21_gate5_friction_hurdle_blocks_low_alpha(self):
        """TC21: Gate 5: Expected alpha <= round-trip friction hurdle suppresses BUY."""
        targets = [{
            "symbol": "005930",
            "target_weight": 0.05,
            "target_price": 50000.0,
            "market": "KOSPI",
            "volatility": 0.015,
            "adv_20d": 1e10,
            "predicted_return": 0.0005,  # 5 bps return vs ~30 bps round-trip friction
        }]
        deltas = self.daemon.compute_rebalance_deltas(targets)
        approved, suppressed = self.daemon.evaluate_oms_safety_gates(deltas)
        self.assertEqual(len(approved), 0)
        self.assertEqual(len(suppressed), 1)
        self.assertEqual(suppressed[0]["gate_passed"], "GATE5_ALPHA_BELOW_FRICTION_HURDLE")

    def test_tc22_gate7_adv_capacity_cap(self):
        """TC22: Gate 7: Order quantity is clamped to <= 5.0% of 20-day ADV."""
        targets = [{
            "symbol": "005930",
            "target_weight": 0.10,  # 10M KRW
            "target_price": 50000.0,
            "market": "KOSPI",
            "volatility": 0.015,
            "adv_20d": 20_000_000.0,  # ADV is 20M KRW -> 5% cap is 1M KRW -> max 20 shares
            "predicted_return": 0.08,
        }]
        deltas = self.daemon.compute_rebalance_deltas(targets)
        approved, suppressed = self.daemon.evaluate_oms_safety_gates(deltas)
        self.assertEqual(len(approved), 1)
        app0 = approved[0]
        self.assertEqual(app0["gate_passed"], "GATE7_ADV_CAPPED")
        self.assertEqual(app0["executed_quantity"], 20)  # clamped from 200 to 20

    def test_tc23_gate8_synthetic_inverse_hedge_overlay(self):
        """TC23: Gate 8: In BEAR / CRISIS regime, emits BUY_HEDGE for 114800 (KRX) and PSQ/SH (US)."""
        self.daemon.regime_label = "BEAR_HIGH_VOL"
        targets = [
            {"symbol": "005930", "target_weight": 0.20, "target_price": 50000.0, "market": "KOSPI", "volatility": 0.015, "adv_20d": 1e10, "predicted_return": 0.08},
            {"symbol": "AAPL", "target_weight": 0.20, "target_price": 200.0, "market": "NASDAQ", "volatility": 0.015, "adv_20d": 5e8, "predicted_return": 0.08},
        ]
        deltas = self.daemon.compute_rebalance_deltas(targets)
        approved, _ = self.daemon.evaluate_oms_safety_gates(deltas)

        actions = [a["action"] for a in approved]
        symbols = [a["symbol"] for a in approved]

        self.assertIn(PaperOrderAction.BUY_HEDGE.value, actions)
        self.assertTrue(any(s == "114800" for s in symbols), "KRX inverse hedge 114800 missing")
        self.assertTrue(any(s in ["PSQ", "SH"] for s in symbols), "US inverse hedge PSQ/SH missing")

    # =========================================================================
    # Category 6: Realistic Execution Simulation (TC24~TC26)
    # =========================================================================

    def test_tc24_gatheral_3_2_impact_power_scaling(self):
        """TC24: Gatheral 3/2-power market impact scales non-linearly with participation rate."""
        # Case A: 1% participation
        order_small = {
            "symbol": "005930", "market": "KOSPI", "action": "BUY",
            "executed_quantity": 200, "target_price": 50000.0,  # 10M KRW
            "adv_20d": 1_000_000_000.0, "volatility": 0.015,  # part = 0.01
        }
        rec_small = self.daemon.simulate_fill(order_small)

        # Case B: 4% participation (4x larger)
        order_large = {
            "symbol": "005930", "market": "KOSPI", "action": "BUY",
            "executed_quantity": 800, "target_price": 50000.0,  # 40M KRW
            "adv_20d": 1_000_000_000.0, "volatility": 0.015,  # part = 0.04
        }
        rec_large = self.daemon.simulate_fill(order_large)

        # In 3/2 power, impact rate increases as (4)^1.5 = 8x!
        ratio = rec_large.market_impact_bps / max(1e-6, rec_small.market_impact_bps)
        self.assertGreater(ratio, 5.0, f"Gatheral 3/2 power scaling failed, ratio was {ratio:.2f}")

    def test_tc25_fast_lob_execution_pricing(self):
        """TC25: Fast LOB half-spread makes BUY execute above target and SELL execute below target."""
        order_buy = {
            "symbol": "005930", "market": "KOSPI", "action": "BUY",
            "executed_quantity": 100, "target_price": 50000.0,
            "adv_20d": 1e10, "volatility": 0.015,
        }
        rec_buy = self.daemon.simulate_fill(order_buy)
        self.assertGreaterEqual(rec_buy.executed_price, 50000.0)
        self.assertGreaterEqual(rec_buy.slippage_bps, 0.0)

        order_sell = {
            "symbol": "005930", "market": "KOSPI", "action": "SELL",
            "executed_quantity": 100, "target_price": 50000.0,
            "adv_20d": 1e10, "volatility": 0.015,
        }
        rec_sell = self.daemon.simulate_fill(order_sell)
        self.assertLessEqual(rec_sell.executed_price, 50000.0)
        self.assertGreaterEqual(rec_sell.slippage_bps, 0.0)

    def test_tc26_statutory_fees_and_stt_taxes(self):
        """TC26: Verify KRX STT 18 bps on sell and US SEC fee 0.3 bps on sell."""
        # KRX SELL: STT 18 bps + broker fee 1.5 bps = 19.5 bps
        order_krx_sell = {
            "symbol": "005930", "market": "KOSPI", "action": "SELL",
            "executed_quantity": 100, "target_price": 50000.0,
            "adv_20d": 1e10, "volatility": 0.015,
        }
        rec_krx = self.daemon.simulate_fill(order_krx_sell)
        expected_krx_fee_min = rec_krx.executed_amount * (0.0018 + 0.00015) * 0.99
        self.assertGreaterEqual(rec_krx.fee_amount, expected_krx_fee_min)

        # US SELL: SEC 0.3 bps + broker fee 0.5 bps = 0.8 bps
        order_us_sell = {
            "symbol": "AAPL", "market": "NASDAQ", "action": "SELL",
            "executed_quantity": 100, "target_price": 200.0,
            "adv_20d": 1e9, "volatility": 0.015,
        }
        rec_us = self.daemon.simulate_fill(order_us_sell)
        expected_us_fee_min = rec_us.executed_amount * (0.00003 + 0.00005) * 0.99
        self.assertGreaterEqual(rec_us.fee_amount, expected_us_fee_min)

    # =========================================================================
    # Category 7: Mathematical Invariant: Net Equity <= Gross Equity (TC27~TC28)
    # =========================================================================

    def test_tc27_net_equity_le_gross_equity_invariant(self):
        """TC27: Invariant Net Equity <= Gross Equity strictly holds across repeated rebalances."""
        targets_cycle1 = [
            {"symbol": "005930", "target_weight": 0.05, "target_price": 50000.0, "market": "KOSPI", "volatility": 0.02, "adv_20d": 1e9, "predicted_return": 0.08},
            {"symbol": "000660", "target_weight": 0.05, "target_price": 150000.0, "market": "KOSPI", "volatility": 0.025, "adv_20d": 1e9, "predicted_return": 0.09},
        ]
        s1 = self.daemon.run_cycle(target_input=targets_cycle1)
        self.assertTrue(s1["invariant_net_le_gross"])
        self.assertLessEqual(self.daemon.net_equity, self.daemon.gross_equity)

        # Cycle 2: trim one, liquidate one, buy a new one
        targets_cycle2 = [
            {"symbol": "005930", "target_weight": 0.02, "target_price": 52000.0, "market": "KOSPI", "volatility": 0.02, "adv_20d": 1e9, "predicted_return": 0.06},
            {"symbol": "035420", "target_weight": 0.05, "target_price": 200000.0, "market": "KOSPI", "volatility": 0.02, "adv_20d": 1e9, "predicted_return": 0.08},
        ]
        s2 = self.daemon.run_cycle(target_input=targets_cycle2)
        self.assertTrue(s2["invariant_net_le_gross"])
        self.assertLessEqual(self.daemon.net_equity, self.daemon.gross_equity)
        self.assertGreater(self.daemon.total_fees_paid, 0.0)

    def test_tc28_portfolio_snapshot_persistence(self):
        """TC28: Portfolio snapshot creates valid row in paper_portfolio_snapshots."""
        snap = self.daemon.snapshot_portfolio(notes="End of Day Audit")
        self.assertIsInstance(snap, PortfolioSnapshot)
        self.assertLessEqual(snap.net_equity, snap.gross_equity)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        rows = cursor.execute("SELECT gross_equity, net_equity, cash_balance FROM paper_portfolio_snapshots").fetchall()
        conn.close()
        self.assertEqual(len(rows), 1)
        self.assertAlmostEqual(rows[0][0], self.daemon.gross_equity, delta=1.0)
        self.assertAlmostEqual(rows[0][1], self.daemon.net_equity, delta=1.0)

    # =========================================================================
    # Category 8: Dry-Run Mode & CLI Runner Subprocess (TC29~TC30)
    # =========================================================================

    def test_tc29_dry_run_mode_skips_live_database_writes(self):
        """TC29: Dry-run mode does not commit irreversible executions to database."""
        dry_daemon = PaperTradingDaemon(
            initial_capital=50_000_000.0,
            db_path=self.db_path,
            dry_run=True,
        )
        targets = [
            {"symbol": "005930", "target_weight": 0.05, "target_price": 50000.0, "market": "KOSPI", "volatility": 0.015, "adv_20d": 1e10, "predicted_return": 0.08}
        ]
        summary = dry_daemon.run_cycle(target_input=targets)
        self.assertEqual(summary["status"], "SUCCESS")
        self.assertEqual(summary["executed_count"], 1)

        # In dry run mode, persist_execution is skipped during run_cycle
        records = dry_daemon.get_paper_executions()
        self.assertEqual(len(records), 0)

    def test_tc30_cli_runner_subprocess_once(self):
        """TC30: Verify run_paper_trading_daemon.py CLI with --once and --dry-run exits with code 0."""
        cli_script = TRADING_SYSTEM_DIR / "scripts" / "run_paper_trading_daemon.py"
        self.assertTrue(cli_script.exists(), "CLI script run_paper_trading_daemon.py must exist")

        cmd = [
            sys.executable,
            str(cli_script),
            "--once",
            "--dry-run",
            "--capital", "50000000",
            "--db", self.db_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, f"CLI runner failed with error:\n{result.stderr}")
        self.assertIn("SHADOW PAPER TRADING EXECUTION SUMMARY", result.stdout)
        self.assertIn("Status           : SUCCESS", result.stdout)


if __name__ == "__main__":
    unittest.main()
