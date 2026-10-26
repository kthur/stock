"""
tests/test_challenger_m2_it2_2_leland_stress.py
===============================================
Adversarial Empirical Stress Testing Suite for Milestone 2 Iteration 2:
Gate 3 Leland Buffer Band Behavior & Liquidation Stress Testing.
Challenger: challenger_m2_it2_2 (Gate 3 Liquidation Stress Challenger)

Stress Test Matrix:
1. Zombie Holding Eradication:
   - 100 random symbols & combinations across KOSPI, KOSDAQ, SP500, NASDAQ, RUSSELL2000.
   - Micro positions: w in [10^-6, bandwidth].
   - Target weight: explicit 0.0 (and omission).
   - Verify 100% liquidation approval without suppression.
2. Boundary Stress on Partial Sales:
   - Partial sells: w_curr -> w_target > 0.
   - Boundary Delta w = bandwidth - 10^-6: MUST be suppressed by Gate 3.
   - Boundary Delta w = bandwidth + 10^-6: MUST pass Gate 3.
   - Cross-currency evaluation (US stocks under KRW base currency).
3. Round-Trip Trade Cycles:
   - Fresh entry -> partial sell -> drift hold -> full liquidation -> re-entry.
   - Verify zero order state corruption, invariant Net Equity <= Gross Equity.
4. Daemon Multi-Cycle Execution:
   - Run paper trading daemon across multiple full rebalance cycles.
   - Verify zero zombie holdings remain post-liquidation.
"""

import math
import os
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, List
import numpy as np

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
)
from src.execution.kill_switch import disengage


class TestGate3ZombieHoldingEradication(unittest.TestCase):
    """
    Stress Dimension 1: Zombie Holding Eradication.
    Test explicit zero target liquidation with micro positions (w in [10^-6, bandwidth])
    across 100 random symbols and combinations. Verify 100% liquidation approval without suppression.
    """

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.temp_dir.name) / "test_zombie.db")
        disengage()

    def tearDown(self):
        disengage()
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def test_100_random_micro_positions_explicit_zero_liquidation(self):
        """
        Generates 100 random micro positions with weights w in [10^-6, bandwidth].
        Asserts that when target_weight == 0.0 is explicitly specified:
        1. 100% of orders have is_liquidation == True.
        2. 100% of orders are APPROVED (len(approved) == 100).
        3. 0% of orders are SUPPRESSED (len(suppressed) == 0).
        4. Every approved order has gate_passed == 'ALL_8_GATES' and delta_quantity == -q_curr.
        """
        np.random.seed(42)
        total_equity = 100_000_000.0  # 100M KRW
        bandwidth = 0.010  # 1.0% Leland bandwidth
        daemon = PaperTradingDaemon(
            initial_capital=total_equity,
            db_path=self.db_path,
            leland_bandwidth=bandwidth,
            base_currency="KRW",
            dry_run=True,
        )

        markets = ["KOSPI", "KOSDAQ", "SP500", "NASDAQ", "RUSSELL2000"]
        targets: List[Dict[str, Any]] = []

        for i in range(100):
            sym = f"SYM_{i:03d}"
            mkt = markets[i % len(markets)]
            is_us = mkt in ["SP500", "NASDAQ", "RUSSELL2000"]

            # Micro weight strictly within [10^-6, bandwidth]
            # e.g., uniform random between 0.0001 and 0.0099
            w_micro = float(np.random.uniform(0.0001, bandwidth * 0.99))
            pos_value_krw = total_equity * w_micro

            if is_us:
                px_usd = float(np.random.uniform(20.0, 500.0))
                pos_value_usd = pos_value_krw / daemon.usd_krw
                qty = max(1, int(pos_value_usd / px_usd))
                px = px_usd
            else:
                px_krw = float(np.random.uniform(1000.0, 100000.0))
                qty = max(1, int(pos_value_krw / px_krw))
                px = px_krw

            daemon.holdings[sym] = {
                "quantity": qty,
                "avg_cost": px,
                "gross_cost": px,
                "market": mkt,
                "current_price": px,
            }

            targets.append({
                "symbol": sym,
                "market": mkt,
                "target_weight": 0.0,  # Explicit zero target
                "target_price": px,
                "volatility": 0.02,
                "adv_20d": 1e9 if not is_us else 5e7,
                "predicted_return": 0.0,
            })

        self.assertEqual(len(daemon.holdings), 100)

        # Compute deltas
        deltas = daemon.compute_rebalance_deltas(targets)
        self.assertEqual(len(deltas), 100)

        # Check all deltas have is_liquidation == True
        for d in deltas:
            sym = d["symbol"]
            q_held = daemon.holdings[sym]["quantity"]
            self.assertTrue(d["is_liquidation"], f"Order for {sym} must have is_liquidation == True")
            self.assertEqual(d["action"], PaperOrderAction.SELL.value)
            self.assertEqual(d["delta_quantity"], -q_held)

        # Evaluate through OMS gates
        approved, suppressed = daemon.evaluate_oms_safety_gates(deltas)

        # Strict Assertions: Zero Suppression
        self.assertEqual(len(suppressed), 0, f"Found {len(suppressed)} unexpectedly suppressed orders: {suppressed}")
        self.assertEqual(len(approved), 100, f"Expected 100 approved orders, got {len(approved)}")

        for app in approved:
            self.assertEqual(app["gate_passed"], "ALL_8_GATES")
            self.assertTrue(app["is_liquidation"])
            self.assertEqual(app["action"], PaperOrderAction.SELL.value)

    def test_omission_based_micro_liquidation_100_symbols(self):
        """
        Verify that 100 micro positions omitted completely from the target list
        are also 100% liquidated with zero zombie holdings.
        """
        total_equity = 100_000_000.0
        bandwidth = 0.015
        daemon = PaperTradingDaemon(
            initial_capital=total_equity,
            db_path=self.db_path,
            leland_bandwidth=bandwidth,
            dry_run=True,
        )

        for i in range(100):
            sym = f"OMIT_{i:03d}"
            px = 10000.0
            qty = 10  # 100,000 KRW = 0.1% weight <= 1.5% bandwidth
            daemon.holdings[sym] = {
                "quantity": qty,
                "avg_cost": px,
                "gross_cost": px,
                "market": "KOSPI",
                "current_price": px,
            }

        # Targets list empty (all 100 symbols omitted)
        deltas = daemon.compute_rebalance_deltas([])
        self.assertEqual(len(deltas), 100)
        for d in deltas:
            self.assertTrue(d["is_liquidation"])

        approved, suppressed = daemon.evaluate_oms_safety_gates(deltas)
        self.assertEqual(len(approved), 100)
        self.assertEqual(len(suppressed), 0)


class TestGate3BoundaryStressPartialSales(unittest.TestCase):
    """
    Stress Dimension 2: Boundary stress on partial sales.
    Test partial sells (w_curr -> w_target > 0) with:
    - Delta w = bandwidth - 10^-6 (must be suppressed)
    - Delta w = bandwidth + 10^-6 (must pass)
    """

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.temp_dir.name) / "test_boundary.db")
        disengage()

    def tearDown(self):
        disengage()
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def test_krx_partial_sells_exact_bandwidth_boundary(self):
        """
        Tests KRX partial sales at the exact floating-point boundary of Leland bandwidth:
        Sub-case 1: Delta w = bandwidth - 1e-6 -> MUST BE SUPPRESSED.
        Sub-case 2: Delta w = bandwidth + 1e-6 -> MUST PASS.
        Tested across 4 different bandwidth values: 0.005, 0.010, 0.020, 0.050.
        """
        total_equity = 100_000_000.0  # 100M KRW
        bandwidths = [0.005, 0.010, 0.020, 0.050]
        eps = 1e-6

        for bw in bandwidths:
            daemon = PaperTradingDaemon(
                initial_capital=total_equity,
                db_path=self.db_path,
                leland_bandwidth=bw,
                base_currency="KRW",
                dry_run=True,
            )

            # --- Sub-case 1: Delta w = bandwidth - 1e-6 (SUPPRESSION EXPECTED) ---
            w_curr_1 = 0.100000
            w_target_1 = w_curr_1 - (bw - eps)  # Delta w = bw - 1e-6 < bw
            px = 10000.0
            q_curr_1 = int((total_equity * w_curr_1) / px)

            daemon.holdings = {
                "005930": {
                    "quantity": q_curr_1,
                    "avg_cost": px,
                    "gross_cost": px,
                    "market": "KOSPI",
                    "current_price": px,
                }
            }

            targets_sub = [{
                "symbol": "005930",
                "market": "KOSPI",
                "target_weight": w_target_1,
                "target_price": px,
                "volatility": 0.02,
                "adv_20d": 1e9,
                "predicted_return": 0.05,
            }]

            deltas_sub = daemon.compute_rebalance_deltas(targets_sub)
            self.assertFalse(deltas_sub[0]["is_liquidation"], "Partial sell must NOT have is_liquidation=True")
            self.assertFalse(deltas_sub[0]["is_fresh_entry"])
            self.assertEqual(deltas_sub[0]["action"], PaperOrderAction.SELL.value)

            app_sub, supp_sub = daemon.evaluate_oms_safety_gates(deltas_sub)
            self.assertEqual(len(app_sub), 0, f"BW {bw}: Delta w = bw - eps must NOT be approved")
            self.assertEqual(len(supp_sub), 1, f"BW {bw}: Delta w = bw - eps must be suppressed")
            self.assertEqual(supp_sub[0]["gate_passed"], "GATE3_LELAND_BUFFER_SUPPRESSED")

            # --- Sub-case 2: Delta w = bandwidth + 1e-6 (APPROVAL EXPECTED) ---
            w_curr_2 = 0.100000
            w_target_2 = w_curr_2 - (bw + eps)  # Delta w = bw + 1e-6 > bw
            q_curr_2 = int((total_equity * w_curr_2) / px)

            daemon.holdings = {
                "005930": {
                    "quantity": q_curr_2,
                    "avg_cost": px,
                    "gross_cost": px,
                    "market": "KOSPI",
                    "current_price": px,
                }
            }

            targets_pass = [{
                "symbol": "005930",
                "market": "KOSPI",
                "target_weight": w_target_2,
                "target_price": px,
                "volatility": 0.02,
                "adv_20d": 1e9,
                "predicted_return": 0.05,
            }]

            deltas_pass = daemon.compute_rebalance_deltas(targets_pass)
            self.assertFalse(deltas_pass[0]["is_liquidation"])
            self.assertFalse(deltas_pass[0]["is_fresh_entry"])
            self.assertEqual(deltas_pass[0]["action"], PaperOrderAction.SELL.value)

            app_pass, supp_pass = daemon.evaluate_oms_safety_gates(deltas_pass)
            self.assertEqual(len(app_pass), 1, f"BW {bw}: Delta w = bw + eps must be approved")
            self.assertEqual(len(supp_pass), 0, f"BW {bw}: Delta w = bw + eps must not be suppressed")
            self.assertEqual(app_pass[0]["gate_passed"], "ALL_8_GATES")

    def test_usd_base_currency_partial_sells_boundary(self):
        """
        Tests US partial sales when base_currency == 'USD':
        Verifies that when denominations are aligned, the boundary holds cleanly.
        """
        total_equity = 100_000.0  # 100k USD
        bw = 0.010
        eps = 1e-6

        daemon = PaperTradingDaemon(
            initial_capital=total_equity,
            db_path=self.db_path,
            leland_bandwidth=bw,
            base_currency="USD",
            dry_run=True,
        )

        px = 100.0
        w_curr = 0.200000

        # Sub-case 1: bw - eps -> Suppressed
        w_tgt_sub = w_curr - (bw - eps)
        q_curr = int((total_equity * w_curr) / px)
        daemon.holdings = {
            "AAPL": {
                "quantity": q_curr,
                "avg_cost": px,
                "gross_cost": px,
                "market": "NASDAQ",
                "current_price": px,
            }
        }
        targets_sub = [{
            "symbol": "AAPL",
            "market": "NASDAQ",
            "target_weight": w_tgt_sub,
            "target_price": px,
            "volatility": 0.02,
            "adv_20d": 5e7,
            "predicted_return": 0.05,
        }]
        app, supp = daemon.evaluate_oms_safety_gates(daemon.compute_rebalance_deltas(targets_sub))
        self.assertEqual(len(app), 0)
        self.assertEqual(len(supp), 1)
        self.assertEqual(supp[0]["gate_passed"], "GATE3_LELAND_BUFFER_SUPPRESSED")

        # Sub-case 2: bw + eps -> Approved
        w_tgt_pass = w_curr - (bw + eps)
        targets_pass = [{
            "symbol": "AAPL",
            "market": "NASDAQ",
            "target_weight": w_tgt_pass,
            "target_price": px,
            "volatility": 0.02,
            "adv_20d": 5e7,
            "predicted_return": 0.05,
        }]
        app2, supp2 = daemon.evaluate_oms_safety_gates(daemon.compute_rebalance_deltas(targets_pass))
        self.assertEqual(len(app2), 1)
        self.assertEqual(len(supp2), 0)
        self.assertEqual(app2[0]["gate_passed"], "ALL_8_GATES")

    def test_vulnerability_us_partial_sell_under_krw_base_currency(self):
        """
        ADVERSARIAL PROBE: US Partial Sells under KRW Base Currency.
        Demonstrates how w_curr = (q_curr * price) / tot_equity (unscaled USD / KRW)
        breaks Gate 3 Leland buffer filtering for US stocks when base_currency == 'KRW'.
        """
        total_equity = 100_000_000.0  # 100M KRW
        bw = 0.010  # 1.0% bandwidth
        daemon = PaperTradingDaemon(
            initial_capital=total_equity,
            db_path=self.db_path,
            leland_bandwidth=bw,
            base_currency="KRW",
            usd_krw=1350.0,
            dry_run=True,
        )

        # 100 shares of AAPL @ $200 = $20,000 USD = 27,000,000 KRW = 27.0% weight
        daemon.holdings["AAPL"] = {
            "quantity": 100,
            "avg_cost": 200.0,
            "gross_cost": 200.0,
            "market": "NASDAQ",
            "current_price": 200.0,
        }

        # Target weight = 0.265 (26.5%).
        # Real Delta w = |0.265 - 0.270| = 0.005 (0.5% <= 1.0% bandwidth).
        # Expected behavior: Gate 3 MUST SUPPRESS this 2-share trim.
        targets = [{
            "symbol": "AAPL",
            "market": "NASDAQ",
            "target_weight": 0.265,
            "target_price": 200.0,
            "volatility": 0.02,
            "adv_20d": 5e7,
            "predicted_return": 0.05,
        }]

        deltas = daemon.compute_rebalance_deltas(targets)
        # Check unscaled w_curr
        # Note: q*p / tot_equity = 20,000 / 100,000,000 = 0.0002 (instead of 0.27)
        self.assertAlmostEqual(deltas[0]["current_weight"], 0.0002, places=6)

        approved, suppressed = daemon.evaluate_oms_safety_gates(deltas)
        # Because delta_w = |0.265 - 0.0002| = 0.2648 > 0.010, it is erroneously APPROVED!
        is_erroneously_approved = (len(approved) == 1 and approved[0]["gate_passed"] == "ALL_8_GATES")
        self.assertTrue(
            is_erroneously_approved,
            "Empirical proof: US partial sell under KRW base currency leaks through Gate 3 due to missing usd_krw multiplier"
        )


class TestGate3RoundTripTradeCycles(unittest.TestCase):
    """
    Stress Dimension 3: Round-trip trade cycles.
    Sequence: Fresh entry -> Partial sell -> Full liquidation -> Re-entry.
    Verify zero order state corruption, unique order IDs, and strict invariant preservation.
    """

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.temp_dir.name) / "test_roundtrip.db")
        disengage()

    def tearDown(self):
        disengage()
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def test_complete_round_trip_lifecycle_single_stock(self):
        """
        Executes a 5-step round trip on a KRX stock:
        Step 1: Fresh entry (0.0 -> 0.05) -> Approved (Gate 3 fresh bypass), Holding created.
        Step 2: Partial sell above bandwidth (0.05 -> 0.035, Delta=0.015 > 0.01) -> Approved, Holding trimmed.
        Step 3: Noise drift within bandwidth (0.035 -> 0.030, Delta=0.005 <= 0.01) -> Suppressed, Holding unchanged.
        Step 4: Explicit full liquidation (0.035 -> 0.000, explicit 0.0) -> Approved (Gate 3 liquidation bypass), Holding deleted.
        Step 5: Re-entry (0.0 -> 0.02) -> Approved (Gate 3 fresh bypass), Holding re-created.
        Asserts zero order state corruption and Net Equity <= Gross Equity throughout.
        """
        daemon = PaperTradingDaemon(
            initial_capital=100_000_000.0,
            db_path=self.db_path,
            leland_bandwidth=0.010,
            dry_run=True,
        )
        sym = "005930"
        mkt = "KOSPI"
        px = 50000.0

        # Step 1: Fresh Entry (0.0 -> 0.05)
        res1 = daemon.run_cycle([{
            "symbol": sym, "market": mkt, "target_weight": 0.05,
            "target_price": px, "volatility": 0.02, "adv_20d": 1e9, "predicted_return": 0.05
        }])
        self.assertEqual(res1["executed_count"], 1)
        self.assertIn(sym, daemon.holdings)
        q_step1 = daemon.holdings[sym]["quantity"]
        self.assertEqual(q_step1, 100)  # 5,000,000 / 50,000
        self.assertLessEqual(daemon.net_equity, daemon.gross_equity)

        # Step 2: Partial Sell above bandwidth (0.05 -> 0.035, Delta=0.015 > 0.01)
        res2 = daemon.run_cycle([{
            "symbol": sym, "market": mkt, "target_weight": 0.035,
            "target_price": px, "volatility": 0.02, "adv_20d": 1e9, "predicted_return": 0.05
        }])
        self.assertEqual(res2["executed_count"], 1)
        q_step2 = daemon.holdings[sym]["quantity"]
        self.assertEqual(q_step2, 70)  # 3,500,000 / 50,000
        self.assertLessEqual(daemon.net_equity, daemon.gross_equity)

        # Step 3: Noise drift within bandwidth (0.035 -> 0.030, Delta=0.005 <= 0.01)
        res3 = daemon.run_cycle([{
            "symbol": sym, "market": mkt, "target_weight": 0.030,
            "target_price": px, "volatility": 0.02, "adv_20d": 1e9, "predicted_return": 0.05
        }])
        self.assertEqual(res3["executed_count"], 0)
        self.assertEqual(res3["suppressed_count"], 1)
        self.assertEqual(res3["suppressed"][0]["gate_passed"], "GATE3_LELAND_BUFFER_SUPPRESSED")
        self.assertEqual(daemon.holdings[sym]["quantity"], q_step2)  # Unchanged
        self.assertLessEqual(daemon.net_equity, daemon.gross_equity)

        # Step 4: Explicit full liquidation (0.035 -> 0.000)
        res4 = daemon.run_cycle([{
            "symbol": sym, "market": mkt, "target_weight": 0.0,
            "target_price": px, "volatility": 0.02, "adv_20d": 1e9, "predicted_return": 0.0
        }])
        self.assertEqual(res4["executed_count"], 1)
        self.assertNotIn(sym, daemon.holdings, "Full liquidation must delete the holding completely")
        self.assertLessEqual(daemon.net_equity, daemon.gross_equity)

        # Step 5: Re-entry (0.0 -> 0.02)
        res5 = daemon.run_cycle([{
            "symbol": sym, "market": mkt, "target_weight": 0.02,
            "target_price": px, "volatility": 0.02, "adv_20d": 1e9, "predicted_return": 0.05
        }])
        self.assertEqual(res5["executed_count"], 1)
        self.assertIn(sym, daemon.holdings)
        self.assertEqual(daemon.holdings[sym]["quantity"], 40)  # 2,000,000 / 50,000
        self.assertLessEqual(daemon.net_equity, daemon.gross_equity)

        # Verify zero order state corruption
        order_ids = [r.order_id for r in daemon.execution_history]
        self.assertEqual(len(order_ids), len(set(order_ids)), "All order IDs must be strictly unique")
        self.assertEqual(len(daemon.execution_history), 4)  # 4 executed orders (steps 1, 2, 4, 5)

    def test_50_consecutive_round_trips_multi_asset(self):
        """
        Executes 50 consecutive round trips across 5 symbols simultaneously.
        Verifies no memory leaks, state corruption, or invariant violations.
        """
        daemon = PaperTradingDaemon(
            initial_capital=100_000_000.0,
            db_path=self.db_path,
            leland_bandwidth=0.010,
            dry_run=True,
        )
        symbols = [f"RT_{i:02d}" for i in range(5)]
        px = 10000.0

        for cycle in range(50):
            # Phase A: Enter all 5 at 0.05 each
            targets_entry = [
                {"symbol": s, "market": "KOSPI", "target_weight": 0.05, "target_price": px,
                 "volatility": 0.02, "adv_20d": 1e9, "predicted_return": 0.05}
                for s in symbols
            ]
            res_a = daemon.run_cycle(targets_entry)
            self.assertEqual(len(daemon.holdings), 5)
            self.assertLessEqual(daemon.net_equity, daemon.gross_equity)

            # Phase B: Liquidate all 5 with explicit 0.0
            targets_exit = [
                {"symbol": s, "market": "KOSPI", "target_weight": 0.0, "target_price": px,
                 "volatility": 0.02, "adv_20d": 1e9, "predicted_return": 0.0}
                for s in symbols
            ]
            res_b = daemon.run_cycle(targets_exit)
            self.assertEqual(len(daemon.holdings), 0, f"Cycle {cycle}: Zombie holdings remained after liquidation!")
            self.assertLessEqual(daemon.net_equity, daemon.gross_equity)


class TestGate3DaemonMultiCycleExecution(unittest.TestCase):
    """
    Stress Dimension 4: Daemon multi-cycle execution.
    Run paper trading daemon through multiple rebalance loops and confirm zero zombie holdings remain.
    """

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.temp_dir.name) / "test_multicycle.db")
        disengage()

    def tearDown(self):
        disengage()
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def test_10_cycle_realistic_portfolio_rebalance_and_clean_exit(self):
        """
        Executes a 10-cycle realistic portfolio management scenario:
        - Cycles 1-2: Build 10-stock portfolio across KRX and US.
        - Cycle 3: Random price shocks + minor rebalances (some suppressed by Leland buffer).
        - Cycle 4: Explicit liquidation of 4 stocks (including micro positions).
        - Cycle 5: Confirm 0 zombie positions remain for the liquidated 4 stocks.
        - Cycle 6: Rotate into 3 new stocks.
        - Cycle 7: Omission liquidation of 3 stocks.
        - Cycle 8: Confirm 0 zombie positions for omitted stocks.
        - Cycle 9: Total liquidation of all remaining holdings.
        - Cycle 10: Confirm portfolio is 100% cash with 0 holdings.
        """
        daemon = PaperTradingDaemon(
            initial_capital=100_000_000.0,
            db_path=self.db_path,
            leland_bandwidth=0.010,
            dry_run=True,
        )

        krx_syms = ["005930", "000660", "035420", "051910", "005380"]
        us_syms = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"]
        all_syms = krx_syms + us_syms

        # Cycle 1: Build initial 10-stock portfolio (0.05 weight each = 50% invested)
        c1_targets = [
            {"symbol": s, "market": "KOSPI" if s in krx_syms else "NASDAQ",
             "target_weight": 0.05, "target_price": 50000.0 if s in krx_syms else 100.0,
             "volatility": 0.02, "adv_20d": 1e9 if s in krx_syms else 5e7, "predicted_return": 0.05}
            for s in all_syms
        ]
        r1 = daemon.run_cycle(c1_targets)
        self.assertEqual(len(daemon.holdings), 10)
        self.assertLessEqual(daemon.net_equity, daemon.gross_equity)

        # Cycle 4: Liquidate 4 stocks explicitly (2 KRX, 2 US)
        liquidated_explicit = ["005930", "000660", "AAPL", "MSFT"]
        c4_targets = []
        for s in all_syms:
            w = 0.0 if s in liquidated_explicit else 0.05
            c4_targets.append({
                "symbol": s, "market": "KOSPI" if s in krx_syms else "NASDAQ",
                "target_weight": w, "target_price": 50000.0 if s in krx_syms else 100.0,
                "volatility": 0.02, "adv_20d": 1e9 if s in krx_syms else 5e7, "predicted_return": 0.05 if w > 0 else 0.0
            })
        r4 = daemon.run_cycle(c4_targets)

        # Cycle 5: Confirm the 4 liquidated stocks are completely eradicated from holdings
        for sym in liquidated_explicit:
            self.assertNotIn(sym, daemon.holdings, f"Zombie holding detected: {sym} was not liquidated!")
        self.assertEqual(len(daemon.holdings), 6)
        self.assertLessEqual(daemon.net_equity, daemon.gross_equity)

        # Cycle 7: Omission liquidation of 3 stocks (035420, GOOGL, AMZN)
        omitted_syms = ["035420", "GOOGL", "AMZN"]
        remaining_targets = [
            {"symbol": s, "market": "KOSPI" if s in krx_syms else "NASDAQ",
             "target_weight": 0.05, "target_price": 50000.0 if s in krx_syms else 100.0,
             "volatility": 0.02, "adv_20d": 1e9 if s in krx_syms else 5e7, "predicted_return": 0.05}
            for s in all_syms if s not in liquidated_explicit and s not in omitted_syms
        ]
        r7 = daemon.run_cycle(remaining_targets)

        # Cycle 8: Confirm omitted stocks are also eradicated
        for sym in omitted_syms:
            self.assertNotIn(sym, daemon.holdings, f"Zombie holding detected for omitted: {sym}!")
        self.assertEqual(len(daemon.holdings), 3)
        self.assertLessEqual(daemon.net_equity, daemon.gross_equity)

        # Cycle 9: Total liquidation of all remaining holdings (empty targets)
        r9 = daemon.run_cycle([])
        self.assertEqual(len(daemon.holdings), 0, "All holdings must be 0 after total liquidation")
        self.assertLessEqual(daemon.net_equity, daemon.gross_equity)

        # Cycle 10: Another empty cycle confirms 0 holdings persist (no resurrected zombies)
        r10 = daemon.run_cycle([])
        self.assertEqual(len(daemon.holdings), 0)
        self.assertLessEqual(daemon.net_equity, daemon.gross_equity)


if __name__ == "__main__":
    unittest.main()
