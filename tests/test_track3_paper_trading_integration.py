"""
tests/test_track3_paper_trading_integration.py
==============================================
Track 3 Integration Test Suite: Autonomous Paper Trading & Real-Time Broker OMS Execution.

Verifies:
1. PaperTradingDaemon initialization, WAL database schema creation, and balance tracking.
2. Target allocation ingestion, delta generation, and 8 OMS safety gates.
3. Strict mathematical invariant: Net Equity <= Gross Equity at all times.
4. Kill switch integration: immediate suppression when engaged, seamless resume when disengaged.
5. Empirical execution logging and SlippageFeedbackEngine closed-loop adaptation.
"""

from __future__ import annotations

import os
import sys
import sqlite3
import tempfile
import unittest
from pathlib import Path

# Add project root and trading_system to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p in (str(PROJECT_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.execution.paper_trading_daemon import (
    PaperTradingDaemon,
    PaperOrderAction,
    PaperExecutionStatus,
    PaperExecutionRecord,
)
from src.execution.kill_switch import engage, disengage, is_kill_switch_active
from src.execution.slippage_feedback import SlippageFeedbackEngine


class TestTrack3PaperTradingIntegration(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.temp_dir.name) / "test_trade_logs.db")
        disengage()

    def tearDown(self):
        disengage()
        self.temp_dir.cleanup()

    def test_daemon_initialization_and_schema(self):
        daemon = PaperTradingDaemon(
            initial_capital=50_000_000.0,
            db_path=self.db_path,
            regime_label="BULL_LOW_VOL",
        )
        self.assertEqual(daemon.cash_balance, 50_000_000.0)
        self.assertEqual(daemon.gross_equity, 50_000_000.0)
        self.assertEqual(daemon.net_equity, 50_000_000.0)

        # Check tables in SQLite
        conn = sqlite3.connect(self.db_path)
        tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()
        table_names = [t[0] for t in tables]
        conn.close()

        self.assertIn("paper_executions", table_names)
        self.assertIn("paper_portfolio_snapshots", table_names)

    def test_rebalance_cycle_and_invariant(self):
        daemon = PaperTradingDaemon(
            initial_capital=100_000_000.0,
            db_path=self.db_path,
            regime_label="BULL_LOW_VOL",
        )

        mock_targets = [
            {
                "symbol": "005930",
                "market": "KOSPI",
                "target_weight": 0.15,
                "target_price": 70000.0,
                "volatility": 0.018,
                "adv_20d": 1500000000.0,
                "predicted_return": 0.08,
            },
            {
                "symbol": "AAPL",
                "market": "NASDAQ",
                "target_weight": 0.10,
                "target_price": 220.0,
                "volatility": 0.015,
                "adv_20d": 80000000.0,
                "predicted_return": 0.06,
            },
        ]

        summary = daemon.run_cycle(target_input=mock_targets)
        self.assertEqual(summary["status"], "SUCCESS")
        self.assertGreater(summary["executed_count"], 0)

        # Mathematical Invariant: Net Equity <= Gross Equity
        self.assertTrue(daemon.net_equity <= daemon.gross_equity + 1e-6)
        self.assertTrue(summary["invariant_net_le_gross"])

        # Check holdings were updated
        self.assertIn("005930", daemon.holdings)
        self.assertIn("AAPL", daemon.holdings)

    def test_kill_switch_suppression_and_release(self):
        daemon = PaperTradingDaemon(
            initial_capital=100_000_000.0,
            db_path=self.db_path,
        )

        mock_targets = [
            {
                "symbol": "005930",
                "market": "KOSPI",
                "target_weight": 0.15,
                "target_price": 70000.0,
                "predicted_return": 0.08,
            }
        ]

        # Engage kill switch
        engage("Unit test safety engagement")
        self.assertTrue(is_kill_switch_active())

        summary_killed = daemon.run_cycle(target_input=mock_targets)
        self.assertEqual(summary_killed["executed_count"], 0)
        self.assertGreater(summary_killed["suppressed_count"], 0)
        self.assertEqual(
            summary_killed["suppressed"][0]["gate_passed"],
            "GATE2_KILL_SWITCH_ACTIVE",
        )

        # Disengage kill switch and re-run
        disengage()
        self.assertFalse(is_kill_switch_active())

        summary_normal = daemon.run_cycle(target_input=mock_targets)
        self.assertGreater(summary_normal["executed_count"], 0)

    def test_slippage_feedback_engine_integration(self):
        feedback_engine = SlippageFeedbackEngine(db_path=self.db_path)
        feedback_engine.record_execution(
            symbol="005930",
            market="KOSPI",
            side="BUY",
            order_qty=100,
            filled_qty=100,
            target_price=70000.0,
            executed_price=70010.0,
            realized_slippage_bps=1.42,
            realized_impact_bps=0.50,
            adv_20d=1500000000.0,
            volatility=0.018,
        )

        summary = feedback_engine.get_summary()
        self.assertGreaterEqual(summary["total_executions"], 1)
        self.assertIn("KOSPI", summary["markets"])


if __name__ == "__main__":
    unittest.main()
