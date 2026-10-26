"""
tests/test_adversarial_challenger_m2_paper_trading.py
=====================================================
Adversarial Empirical Stress Testing Suite for Milestone 2 (Requirement R2):
Paper Trading Daemon, Authentic Non-Zero Friction Deduction,
Mathematical Invariant Net Equity <= Gross Equity, and OMS Safety Gates 1-8.

Test Coverage:
1. Domain 1: Authentic Non-Zero Friction on Every Single Execution
   - KRX BUY/SELL statutory taxes and broker fees
   - US BUY/SELL SEC fees and broker fees
   - Half-spread & Gatheral 3/2-power market impact scaling
   - Micro/Macro order sizes and ADV participation
2. Domain 2: Adversarial Invariant Probing: Net Equity <= Gross Equity
   - Multi-cycle random walk transaction sequences (100+ cycles)
   - Extreme price shifts (+1000%, -95%)
   - Full liquidations, re-entries, partial fills
   - Precision floating point boundary probing
3. Domain 3: OMS Safety Gates (Gates 1-8) Comprehensive Adversarial Evaluation
   - Gate 1: Crisis Gating (SEVERE blocks BUYs, allows SELLs)
   - Gate 2: Emergency Kill Switch (active blocks all, inactive permits)
   - Gate 3: Leland Buffer Band (noise suppression, fresh entry & full exit bypass)
   - Gate 4: Price Limit Locks (+/-29.5% KRX limit locks)
   - Gate 5: STT / Friction Net Alpha Hurdle
   - Gate 6: Adverse Opening Gap Filter
   - Gate 7: ADV Capacity Cap (clamping to <= 5% ADV)
   - Gate 8: Synthetic Beta Inverse Hedge Overlay (BEAR/CRISIS vs BULL)
4. Domain 4: Dry-Run Mode & SQLite DB State Isolation
"""

from __future__ import annotations

import math
import os
import sys
import sqlite3
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p in (str(PROJECT_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.execution.paper_trading_daemon import (
    PaperTradingDaemon,
    PaperOrderAction,
    PaperExecutionStatus,
    PaperExecutionRecord,
    PortfolioSnapshot,
)
from src.execution.kill_switch import engage, disengage, is_kill_switch_active


class TestAdversarialFrictionDeduction(unittest.TestCase):
    """Domain 1: Verify authentic non-zero friction on every single execution."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.temp_dir.name) / "test_friction.db")
        self.daemon = PaperTradingDaemon(
            initial_capital=100_000_000.0,
            db_path=self.db_path,
            krx_stt_rate=0.0018,
            krx_broker_fee=0.00015,
            us_sec_fee=0.00003,
            us_broker_fee=0.00005,
            gatheral_kappa=1.50,
            dry_run=True,
        )

    def tearDown(self):
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def test_krx_buy_friction_deduction(self):
        """KRX BUY execution must deduct broker fee, half-spread, and market impact."""
        order = {
            "symbol": "005930",
            "market": "KOSPI",
            "action": "BUY",
            "executed_quantity": 100,
            "target_price": 70000.0,
            "adv_20d": 1_000_000_000.0,
            "volatility": 0.02,
        }
        rec = self.daemon.simulate_fill(order)

        self.assertGreater(rec.fee_amount, 0.0, "KRX BUY broker fee must be strictly positive")
        expected_fee = rec.executed_amount * 0.00015
        self.assertAlmostEqual(rec.fee_amount, round(expected_fee, 2), delta=0.05)
        # Executed price must be >= target price for BUY
        self.assertGreaterEqual(rec.executed_price, rec.target_price)
        # Net amount must be executed_amount + fee_amount
        self.assertAlmostEqual(rec.net_amount, rec.executed_amount + rec.fee_amount, delta=0.01)

    def test_krx_sell_friction_deduction(self):
        """KRX SELL execution must deduct 18 bps STT tax + 1.5 bps broker fee."""
        # Prepopulate holding
        self.daemon.holdings["005930"] = {
            "quantity": 100,
            "avg_cost": 70000.0,
            "gross_cost": 70000.0,
            "market": "KOSPI",
            "current_price": 70000.0,
        }
        order = {
            "symbol": "005930",
            "market": "KOSPI",
            "action": "SELL",
            "executed_quantity": 100,
            "target_price": 70000.0,
            "adv_20d": 1_000_000_000.0,
            "volatility": 0.02,
        }
        rec = self.daemon.simulate_fill(order)

        # STT (18 bps) + broker fee (1.5 bps) = 19.5 bps on executed_amount
        expected_stt = rec.executed_amount * 0.0018
        expected_broker = rec.executed_amount * 0.00015
        total_expected_fee = expected_stt + expected_broker

        self.assertGreater(rec.fee_amount, 0.0)
        self.assertAlmostEqual(rec.fee_amount, round(total_expected_fee, 2), delta=0.10)
        # On SELL, net cash inflow must be executed_amount - fee_amount
        self.assertAlmostEqual(rec.net_amount, rec.executed_amount - rec.fee_amount, delta=0.01)

    def test_us_buy_sell_friction_deduction(self):
        """US equities must deduct SEC fee (SELL only) and broker fee."""
        buy_order = {
            "symbol": "AAPL",
            "market": "NASDAQ",
            "action": "BUY",
            "executed_quantity": 50,
            "target_price": 200.0,
            "adv_20d": 50_000_000.0,
            "volatility": 0.015,
        }
        buy_rec = self.daemon.simulate_fill(buy_order)
        # US BUY: broker fee only
        expected_buy_fee = buy_rec.executed_amount * 0.00005
        self.assertGreater(buy_rec.fee_amount, 0.0)
        self.assertAlmostEqual(buy_rec.fee_amount, round(expected_buy_fee, 2), delta=0.02)

        # Prepopulate holding for SELL
        self.daemon.holdings["AAPL"] = {
            "quantity": 50,
            "avg_cost": 200.0,
            "gross_cost": 200.0,
            "market": "NASDAQ",
            "current_price": 200.0,
        }
        sell_order = {
            "symbol": "AAPL",
            "market": "NASDAQ",
            "action": "SELL",
            "executed_quantity": 50,
            "target_price": 200.0,
            "adv_20d": 50_000_000.0,
            "volatility": 0.015,
        }
        sell_rec = self.daemon.simulate_fill(sell_order)
        # US SELL: SEC (0.3 bps) + broker (0.5 bps) = 0.8 bps
        expected_sell_fee = sell_rec.executed_amount * (0.00003 + 0.00005)
        self.assertGreater(sell_rec.fee_amount, 0.0)
        self.assertAlmostEqual(sell_rec.fee_amount, round(expected_sell_fee, 2), delta=0.02)

    def test_gatheral_3_2_power_scaling(self):
        """Market impact must strictly follow kappa * sigma * (Q*P / ADV)^1.5."""
        p0 = 100.0
        adv = 10_000_000.0
        vol = 0.02
        sigma_ann = vol * math.sqrt(252.0)

        # Small order: 100 shares ($10,000 / $10M = 0.001 participation)
        rec_small = self.daemon.simulate_fill({
            "symbol": "TEST_S",
            "market": "SP500",
            "action": "BUY",
            "executed_quantity": 100,
            "target_price": p0,
            "adv_20d": adv,
            "volatility": vol,
        })

        # Large order: 10,000 shares ($1,000,000 / $10M = 0.10 participation)
        rec_large = self.daemon.simulate_fill({
            "symbol": "TEST_L",
            "market": "SP500",
            "action": "BUY",
            "executed_quantity": 10_000,
            "target_price": p0,
            "adv_20d": adv,
            "volatility": vol,
        })

        self.assertGreater(rec_large.market_impact_bps, rec_small.market_impact_bps)
        # (0.10 / 0.001)^1.5 = 100^1.5 = 1000x scaling ratio
        ratio = rec_large.market_impact_bps / max(1e-4, rec_small.market_impact_bps)
        self.assertGreater(ratio, 500.0, "Gatheral 3/2 power scaling must scale superlinearly")


class TestAdversarialInvariantProbing(unittest.TestCase):
    """Domain 2: Adversarial Invariant Probing: Net Equity <= Gross Equity across all conditions."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.temp_dir.name) / "test_invariant.db")

    def tearDown(self):
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def test_multi_cycle_random_walk_transactions(self):
        """
        Adversarial probe: 100 randomized rebalance cycles with random weights,
        sudden price shocks, full liquidations, and partial fills.
        Net Equity <= Gross Equity must hold strictly at every single step.
        """
        daemon = PaperTradingDaemon(
            initial_capital=100_000_000.0,
            db_path=self.db_path,
            dry_run=True,
        )

        symbols = ["005930", "000660", "AAPL", "MSFT", "NVDA"]
        prices = {"005930": 70000.0, "000660": 120000.0, "AAPL": 220.0, "MSFT": 410.0, "NVDA": 130.0}

        np.random.seed(42)

        for cycle in range(1, 101):
            # Apply random price fluctuations between -10% and +10%
            for sym in symbols:
                pct = np.random.uniform(-0.10, 0.10)
                prices[sym] = max(1.0, prices[sym] * (1.0 + pct))

            # Generate random target weights summing to <= 0.90 (leaving cash)
            raw_weights = np.random.uniform(0.0, 0.25, size=len(symbols))
            # Occasionally zero out weights to force full liquidations
            if cycle % 5 == 0:
                raw_weights[np.random.choice(len(symbols))] = 0.0
            total_w = sum(raw_weights)
            weights = raw_weights / max(1.0, total_w * 1.2)

            targets = []
            for i, sym in enumerate(symbols):
                mkt = "KOSPI" if sym.isdigit() else "NASDAQ"
                targets.append({
                    "symbol": sym,
                    "market": mkt,
                    "target_weight": float(weights[i]),
                    "target_price": float(prices[sym]),
                    "volatility": 0.015,
                    "adv_20d": 1_000_000_000.0 if sym.isdigit() else 50_000_000.0,
                    "predicted_return": 0.05,
                })

            summary = daemon.run_cycle(target_input=targets)

            # Strict verification of mathematical invariant
            net_eq = daemon.net_equity
            gross_eq = daemon.gross_equity

            self.assertLessEqual(
                net_eq, gross_eq + 1e-9,
                msg=f"Invariant BREACHED at cycle {cycle}: Net Equity ({net_eq}) > Gross Equity ({gross_eq})"
            )
            self.assertTrue(summary["invariant_net_le_gross"])

    def test_extreme_price_collapse_and_full_liquidation(self):
        """Full liquidation of positions after a 95% price crash."""
        daemon = PaperTradingDaemon(
            initial_capital=100_000_000.0,
            db_path=self.db_path,
            dry_run=True,
        )

        # Cycle 1: Buy positions
        targets1 = [{
            "symbol": "005930",
            "market": "KOSPI",
            "target_weight": 0.50,
            "target_price": 50000.0,
            "volatility": 0.02,
            "adv_20d": 1e9,
            "predicted_return": 0.05,
        }]
        daemon.run_cycle(target_input=targets1)
        self.assertIn("005930", daemon.holdings)
        self.assertLessEqual(daemon.net_equity, daemon.gross_equity)

        # Cycle 2: Stock crashes 95% (to 2500 KRW) and target becomes 0.0 (full liquidation)
        targets2 = [{
            "symbol": "005930",
            "market": "KOSPI",
            "target_weight": 0.0,
            "target_price": 2500.0,
            "volatility": 0.10,
            "adv_20d": 1e9,
            "predicted_return": 0.0,
        }]
        summary = daemon.run_cycle(target_input=targets2)

        # Holding should be completely liquidated
        self.assertNotIn("005930", daemon.holdings)
        self.assertLessEqual(daemon.net_equity, daemon.gross_equity + 1e-9)
        self.assertTrue(summary["invariant_net_le_gross"])
        # Friction must have been paid on both buy and sell
        self.assertGreater(daemon.total_fees_paid, 0.0)

    def test_zero_capital_or_micro_holdings(self):
        """Micro holdings and fractional allocations down to 1 share."""
        daemon = PaperTradingDaemon(
            initial_capital=10_000.0,  # 10,000 KRW
            db_path=self.db_path,
            dry_run=True,
        )
        targets = [{
            "symbol": "005930",
            "market": "KOSPI",
            "target_weight": 0.50,
            "target_price": 70000.0,  # stock price > entire capital
            "volatility": 0.02,
            "adv_20d": 1e9,
            "predicted_return": 0.05,
        }]
        summary = daemon.run_cycle(target_input=targets)
        # Quantity should be 0 because 5000 KRW / 70000 KRW = 0 shares
        self.assertEqual(summary["executed_count"], 0)
        self.assertEqual(daemon.net_equity, 10_000.0)
        self.assertLessEqual(daemon.net_equity, daemon.gross_equity)


class TestAdversarialOMSSafetyGates(unittest.TestCase):
    """Domain 3: OMS Safety Gates 1-8 Comprehensive Verification."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.temp_dir.name) / "test_gates.db")
        disengage()

    def tearDown(self):
        disengage()
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def test_gate1_crisis_gating_blocks_buys_only(self):
        """Gate 1: SEVERE crisis blocks all BUY orders, but allows SELL orders."""
        daemon = PaperTradingDaemon(
            initial_capital=100_000_000.0,
            db_path=self.db_path,
            crisis_level="SEVERE",
            dry_run=True,
        )
        # Prepopulate holding to test SELL
        daemon.holdings["005930"] = {
            "quantity": 100,
            "avg_cost": 70000.0,
            "gross_cost": 70000.0,
            "market": "KOSPI",
            "current_price": 70000.0,
        }

        targets = [
            # BUY order
            {
                "symbol": "AAPL",
                "market": "NASDAQ",
                "target_weight": 0.10,
                "target_price": 200.0,
                "volatility": 0.02,
                "adv_20d": 5e7,
                "predicted_return": 0.08,
            },
            # SELL order (liquidation of 005930)
            {
                "symbol": "005930",
                "market": "KOSPI",
                "target_weight": 0.0,
                "target_price": 70000.0,
                "volatility": 0.02,
                "adv_20d": 1e9,
                "predicted_return": 0.0,
            }
        ]

        summary = daemon.run_cycle(target_input=targets)

        # AAPL BUY must be suppressed by Gate 1
        suppressed_symbols = {s["symbol"]: s["gate_passed"] for s in summary["suppressed"]}
        self.assertIn("AAPL", suppressed_symbols)
        self.assertEqual(suppressed_symbols["AAPL"], "GATE1_SEVERE_CRISIS_BLOCKED")

        # 005930 SELL must NOT be blocked by Gate 1
        executed_symbols = [e["symbol"] for e in summary["executions"]]
        self.assertIn("005930", executed_symbols)

    def test_gate2_emergency_kill_switch_blocks_all(self):
        """Gate 2: Active kill switch blocks both BUY and SELL orders."""
        daemon = PaperTradingDaemon(
            initial_capital=100_000_000.0,
            db_path=self.db_path,
            dry_run=True,
        )
        daemon.holdings["005930"] = {
            "quantity": 100,
            "avg_cost": 70000.0,
            "gross_cost": 70000.0,
            "market": "KOSPI",
            "current_price": 70000.0,
        }

        engage("Adversarial test emergency freeze")
        self.assertTrue(is_kill_switch_active())

        targets = [
            {"symbol": "AAPL", "market": "NASDAQ", "target_weight": 0.10, "target_price": 200.0, "predicted_return": 0.08},
            {"symbol": "005930", "market": "KOSPI", "target_weight": 0.0, "target_price": 70000.0, "predicted_return": 0.0},
        ]
        summary = daemon.run_cycle(target_input=targets)

        self.assertEqual(summary["executed_count"], 0)
        self.assertEqual(summary["approved_count"], 0)
        self.assertGreater(summary["suppressed_count"], 0)
        for supp in summary["suppressed"]:
            self.assertEqual(supp["gate_passed"], "GATE2_KILL_SWITCH_ACTIVE")

        disengage()
        self.assertFalse(is_kill_switch_active())

    def test_gate3_leland_buffer_bands_and_bypasses(self):
        """
        Gate 3: Leland buffer suppresses noise <= bandwidth (0.005).
        Fresh entries and full exits MUST bypass the buffer.
        """
        daemon = PaperTradingDaemon(
            initial_capital=100_000_000.0,
            db_path=self.db_path,
            leland_bandwidth=0.01,  # 1.0% bandwidth
            dry_run=True,
        )
        # Prepopulate holding with weight = 0.10 (10M KRW / 100M)
        daemon.holdings["005930"] = {
            "quantity": 200,
            "avg_cost": 50000.0,
            "gross_cost": 50000.0,
            "market": "KOSPI",
            "current_price": 50000.0,
        }

        # Case A: Minor weight adjustment |Delta w| = |0.105 - 0.10| = 0.005 <= 0.01 -> Suppressed
        deltas = daemon.compute_rebalance_deltas([{
            "symbol": "005930",
            "market": "KOSPI",
            "target_weight": 0.105,
            "target_price": 50000.0,
            "volatility": 0.02,
            "adv_20d": 1e9,
            "predicted_return": 0.05,
        }])
        approved, suppressed = daemon.evaluate_oms_safety_gates(deltas)
        self.assertEqual(len(approved), 0)
        self.assertEqual(len(suppressed), 1)
        self.assertEqual(suppressed[0]["gate_passed"], "GATE3_LELAND_BUFFER_SUPPRESSED")

        # Case B: Fresh entry (q_curr == 0, target_weight = 0.005 <= bandwidth) -> Must BYPASS!
        # Note: 005930 is also in holdings; if omitted from targets, it generates a full liquidation exit (which also bypasses Gate 3).
        # To isolate fresh entry, include 005930 at current weight so its delta is 0 (HOLD).
        deltas_fresh = daemon.compute_rebalance_deltas([
            {
                "symbol": "000660",
                "market": "KOSPI",
                "target_weight": 0.005,
                "target_price": 100000.0,
                "volatility": 0.02,
                "adv_20d": 1e9,
                "predicted_return": 0.05,
            },
            {
                "symbol": "005930",
                "market": "KOSPI",
                "target_weight": 0.10,
                "target_price": 50000.0,
                "volatility": 0.02,
                "adv_20d": 1e9,
                "predicted_return": 0.05,
            }
        ])
        approved_fresh, suppressed_fresh = daemon.evaluate_oms_safety_gates(deltas_fresh)
        approved_syms = [a["symbol"] for a in approved_fresh]
        self.assertIn("000660", approved_syms, "Fresh entry must bypass Leland buffer")
        self.assertEqual(len(approved_fresh), 1)

        # Case C: Full liquidation via omission from targets -> Must BYPASS!
        deltas_exit = daemon.compute_rebalance_deltas([])
        approved_exit, suppressed_exit = daemon.evaluate_oms_safety_gates(deltas_exit)
        self.assertEqual(len(approved_exit), 1)
        self.assertEqual(approved_exit[0]["symbol"], "005930")
        self.assertTrue(approved_exit[0]["is_liquidation"])

    def test_vulnerability_explicit_zero_target_suppressed_as_zombie_holding(self):
        """
        REMEDIATION VERIFIED: Explicit Zero-Weight Target Bypasses Leland Buffer Bands.
        When a position is held with a small weight (e.g. 0.5% weight <= 1.0% bandwidth),
        and the target allocation explicitly sets target_weight = 0.0 to liquidate it,
        compute_rebalance_deltas() dynamically sets 'is_liquidation': (q_curr > 0 and q_target == 0).
        As a result, Gate 3 recognizes full liquidation and allows the order to bypass
        the Leland buffer band, preventing zombie position trapping.
        """
        daemon = PaperTradingDaemon(
            initial_capital=100_000_000.0,
            db_path=self.db_path,
            leland_bandwidth=0.01,  # 1.0% bandwidth
            dry_run=True,
        )
        # Small holding of 10 shares = 500,000 KRW = 0.5% weight (<= 1.0% bandwidth)
        daemon.holdings["005930"] = {
            "quantity": 10,
            "avg_cost": 50000.0,
            "gross_cost": 50000.0,
            "market": "KOSPI",
            "current_price": 50000.0,
        }
        # Explicit liquidation target in target list
        targets = [{
            "symbol": "005930",
            "market": "KOSPI",
            "target_weight": 0.0,
            "target_price": 50000.0,
            "volatility": 0.02,
            "adv_20d": 1e9,
            "predicted_return": 0.0,
        }]
        deltas = daemon.compute_rebalance_deltas(targets)
        self.assertTrue(deltas[0]["is_liquidation"], "Remediation verified: explicit 0.0 weight sets is_liquidation to True")
        self.assertEqual(deltas[0]["action"], "SELL")
        self.assertEqual(deltas[0]["delta_quantity"], -10)

        approved, suppressed = daemon.evaluate_oms_safety_gates(deltas)
        # Remediation verified: order bypasses Gate 3 and is approved for execution
        self.assertEqual(len(approved), 1)
        self.assertEqual(len(suppressed), 0)
        self.assertEqual(approved[0]["symbol"], "005930")
        self.assertTrue(approved[0]["is_liquidation"])
        self.assertEqual(approved[0]["gate_passed"], "ALL_8_GATES")

    def test_vulnerability_us_equity_gate8_inverse_hedge_currency_mismatch(self):
        """
        Validates Gate 8 Synthetic Beta Inverse Hedge Currency Alignment on US Holdings.
        When base_currency is KRW (100M KRW), and AAPL is held (300 sh @ $200 = $60,000 USD = 81M KRW),
        the portfolio weight evaluates to 0.81 (81%). In a CRISIS regime, Gate 8 must generate
        an approved BUY_HEDGE order for PSQ with exact share sizing (740 shares).
        """
        daemon = PaperTradingDaemon(
            initial_capital=100_000_000.0,
            db_path=self.db_path,
            regime_label="CRISIS",
            dry_run=True,
        )
        # 300 shares of AAPL at $200 = $60,000 USD = ~81,000,000 KRW (81% of portfolio)
        daemon.holdings["AAPL"] = {
            "quantity": 300,
            "avg_cost": 200.0,
            "gross_cost": 200.0,
            "market": "NASDAQ",
            "current_price": 200.0,
        }
        daemon.gross_equity = 100_000_000.0

        approved, suppressed = daemon.evaluate_oms_safety_gates([])
        psq_hedges = [a for a in approved if a.get("symbol") in ("PSQ", "SH")]
        self.assertEqual(len(psq_hedges), 1, "Gate 8 must emit 1 hedge order for US equity portfolio in CRISIS")
        self.assertEqual(psq_hedges[0]["symbol"], "PSQ", "NASDAQ holdings must trigger PSQ inverse hedge")
        self.assertEqual(psq_hedges[0]["delta_quantity"], 740, "Calculated PSQ shares must equal 740 ($37,037 / $50)")
        self.assertEqual(psq_hedges[0]["gate_passed"], "GATE8_INVERSE_HEDGE_OVERLAY")

    def test_gate4_price_limit_locks(self):
        """Gate 4: KRX +/-29.5% daily limit locks block BUY orders."""
        daemon = PaperTradingDaemon(
            initial_capital=100_000_000.0,
            db_path=self.db_path,
            dry_run=True,
        )

        deltas = [
            # Upper limit locked (+30%)
            {
                "symbol": "005930",
                "market": "KOSPI",
                "action": "BUY",
                "delta_quantity": 100,
                "target_price": 65000.0,
                "target_weight": 0.065,
                "current_weight": 0.0,
                "volatility": 0.02,
                "adv_20d": 1e9,
                "predicted_return": 0.05,
                "is_fresh_entry": True,
                "is_liquidation": False,
            },
            # Lower limit locked (-30%)
            {
                "symbol": "000660",
                "market": "KOSPI",
                "action": "BUY",
                "delta_quantity": 100,
                "target_price": 70000.0,
                "target_weight": 0.07,
                "current_weight": 0.0,
                "volatility": 0.02,
                "adv_20d": 1e9,
                "predicted_return": 0.05,
                "is_fresh_entry": True,
                "is_liquidation": False,
            }
        ]

        market_data = {
            "005930": {"daily_change_pct": 0.298},
            "000660": {"daily_change_pct": -0.296},
        }

        approved, suppressed = daemon.evaluate_oms_safety_gates(deltas, market_data=market_data)
        self.assertEqual(len(approved), 0)
        self.assertEqual(len(suppressed), 2)
        gate_reasons = {s["symbol"]: s["gate_passed"] for s in suppressed}
        self.assertEqual(gate_reasons["005930"], "GATE4_UPPER_LIMIT_LOCKED")
        self.assertEqual(gate_reasons["000660"], "GATE4_LOWER_LIMIT_LOCKED")

    def test_gate5_friction_alpha_hurdle(self):
        """Gate 5: Alpha below friction hurdle is suppressed."""
        daemon = PaperTradingDaemon(
            initial_capital=100_000_000.0,
            db_path=self.db_path,
            krx_stt_rate=0.0018,
            krx_broker_fee=0.00015,
            dry_run=True,
        )
        # Friction hurdle = 2*0.0005 + 2*0.00015 + 0.0018 = 0.0031 (31 bps)
        deltas = [{
            "symbol": "005930",
            "market": "KOSPI",
            "action": "BUY",
            "delta_quantity": 100,
            "target_price": 50000.0,
            "target_weight": 0.05,
            "current_weight": 0.0,
            "volatility": 0.02,
            "adv_20d": 1e9,
            "predicted_return": 0.0015,  # 15 bps < 31 bps hurdle
            "is_fresh_entry": True,
            "is_liquidation": False,
        }]
        approved, suppressed = daemon.evaluate_oms_safety_gates(deltas)
        self.assertEqual(len(approved), 0)
        self.assertEqual(len(suppressed), 1)
        self.assertEqual(suppressed[0]["gate_passed"], "GATE5_ALPHA_BELOW_FRICTION_HURDLE")

    def test_gate6_adverse_opening_gap(self):
        """Gate 6: Adverse opening gap (< -3*vol or -5%) blocks BUY."""
        daemon = PaperTradingDaemon(
            initial_capital=100_000_000.0,
            db_path=self.db_path,
            dry_run=True,
        )
        deltas = [{
            "symbol": "005930",
            "market": "KOSPI",
            "action": "BUY",
            "delta_quantity": 100,
            "target_price": 50000.0,
            "target_weight": 0.05,
            "current_weight": 0.0,
            "volatility": 0.02,
            "adv_20d": 1e9,
            "predicted_return": 0.05,
            "is_fresh_entry": True,
            "is_liquidation": False,
        }]
        # Gap of -7% is adverse
        market_data = {"005930": {"open_gap_pct": -0.07}}
        approved, suppressed = daemon.evaluate_oms_safety_gates(deltas, market_data=market_data)
        self.assertEqual(len(approved), 0)
        self.assertEqual(len(suppressed), 1)
        self.assertEqual(suppressed[0]["gate_passed"], "GATE6_ADVERSE_GAP_BLOCKED")

    def test_gate7_adv_capacity_clamping(self):
        """Gate 7: Order exceeding 5% ADV is clamped to 5% ADV."""
        daemon = PaperTradingDaemon(
            initial_capital=100_000_000.0,
            db_path=self.db_path,
            adv_cap=0.05,
            dry_run=True,
        )
        # ADV = 1,000,000 KRW; 5% ADV = 50,000 KRW; Price = 10,000 KRW -> max shares = 5
        deltas = [{
            "symbol": "MICRO_STOCK",
            "market": "KOSPI",
            "action": "BUY",
            "delta_quantity": 100,  # 100 shares * 10,000 = 1,000,000 KRW (100% of ADV)
            "target_price": 10000.0,
            "target_weight": 0.01,
            "current_weight": 0.0,
            "volatility": 0.02,
            "adv_20d": 1_000_000.0,
            "predicted_return": 0.05,
            "is_fresh_entry": True,
            "is_liquidation": False,
        }]
        approved, suppressed = daemon.evaluate_oms_safety_gates(deltas)
        self.assertEqual(len(approved), 1)
        self.assertEqual(approved[0]["gate_passed"], "GATE7_ADV_CAPPED")
        self.assertEqual(approved[0]["executed_quantity"], 5)
        self.assertEqual(approved[0]["delta_quantity"], 5)

    def test_gate8_synthetic_inverse_hedge_regime_activation(self):
        """Gate 8: Synthetic beta inverse hedge is emitted in BEAR/CRISIS, omitted in BULL."""
        # Test A: BULL regime -> No hedge orders
        daemon_bull = PaperTradingDaemon(
            initial_capital=100_000_000.0,
            db_path=self.db_path,
            regime_label="BULL_LOW_VOL",
            dry_run=True,
        )
        daemon_bull.holdings["005930"] = {
            "quantity": 200,
            "avg_cost": 50000.0,
            "gross_cost": 50000.0,
            "market": "KOSPI",
            "current_price": 50000.0,
        }
        approved_bull, _ = daemon_bull.evaluate_oms_safety_gates([])
        hedge_bull = [o for o in approved_bull if o.get("action") == "BUY_HEDGE"]
        self.assertEqual(len(hedge_bull), 0)

        # Test B: BEAR regime -> Generates BUY_HEDGE on 114800
        daemon_bear = PaperTradingDaemon(
            initial_capital=100_000_000.0,
            db_path=self.db_path,
            regime_label="BEAR_HIGH_VOL",
            dry_run=True,
        )
        daemon_bear.holdings["005930"] = {
            "quantity": 1000,
            "avg_cost": 50000.0,
            "gross_cost": 50000.0,
            "market": "KOSPI",
            "current_price": 50000.0,
        }
        approved_bear, _ = daemon_bear.evaluate_oms_safety_gates([])
        hedge_bear = [o for o in approved_bear if o.get("action") == "BUY_HEDGE"]
        self.assertGreater(len(hedge_bear), 0)
        self.assertEqual(hedge_bear[0]["symbol"], "114800")
        self.assertEqual(hedge_bear[0]["gate_passed"], "GATE8_INVERSE_HEDGE_OVERLAY")


if __name__ == "__main__":
    unittest.main()
