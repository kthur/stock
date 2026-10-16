"""
tests/test_phase112_account_reconciliation.py — Comprehensive Unit & Integration Test Suite
Milestone: Phase 112 (Release R128 / v119 Production Master, Feature F532)

Test Coverage:
- TC01: Class exports, version metadata (VERSION=112, RELEASE="R128", FEATURE="F532"), and alias trees
- TC02: Mirrored import parity between src.execution and trading_system.src.execution
- TC03: Dual placement bit-for-bit SHA-256 hash identity across mirrored files
- TC04: TaxLotMethod and ReconciliationStatus enums and dataclass serialization
- TC05: Penny-level conservation on BUY fills: |Delta Cash + Cost Basis + Comm| < 0.0001
- TC06: Penny-level conservation on SELL fills: |Delta Cash - (Gross - Comm - Tax - TAF)| < 0.0001
- TC07: Net Equity <= Gross Equity accounting invariant across mixed long and short positions
- TC08: KRX Statutory Transaction Tax (15 bps) on KOSPI and KOSDAQ SELLs (and 0 on BUY)
- TC09: US SEC Section 31 tax (2.78e-5) on US equity sales
- TC10: US FINRA TAF ($0.000166 per share, capped at $8.30) on US equity sales
- TC11: Standard broker commission calculations (KRX 1.5 bps vs US 0.5 bps)
- TC12: Tax Lot Method: FIFO matching (oldest acquired lot consumed first)
- TC13: Tax Lot Method: LIFO matching (newest acquired lot consumed first)
- TC14: Tax Lot Method: HIFO matching (highest cost lot consumed first to minimize tax/PnL)
- TC15: Partial lot consumption across multiple tranches with remaining_qty tracking
- TC16: Realized PnL attribution per lot and engine-level realized PnL accumulation
- TC17: Short borrow fee daily accrual via BorrowDynamicsModel or borrow rates
- TC18: Accrued borrow fees deduction from Net Equity
- TC19: Continuous 5-dimensional reconciliation: Cash Balance (C_internal vs C_broker)
- TC20: Continuous 5-dimensional reconciliation: Purchasing Power (PP_internal vs PP_broker)
- TC21: Continuous 5-dimensional reconciliation: Margin Limits (M_internal vs M_broker)
- TC22: Continuous 5-dimensional reconciliation: Open Orders (ghost & orphaned detection)
- TC23: Continuous 5-dimensional reconciliation: Settled Positions (shares & cost basis)
- TC24: Orphaned broker order triggers circuit breaker immediately
- TC25: Position quantity mismatch triggers circuit breaker immediately
- TC26: Discrepancy > 0.01% (0.0001) triggers circuit breaker and trading pause callback
- TC27: Discrepancy within tolerance (<= 0.001%) classifies as PERFECT or WITHIN_TOLERANCE
- TC28: Discrepancy warning state (0.001% < delta <= 0.01%)
- TC29: Circuit breaker reset (reset_circuit_breaker) clears tripped state
- TC30: Ledger synchronization to broker (sync_to_broker)
- TC31: SQLite database persistence: audit records in account_reconciliations table
- TC32: SQLite database persistence: tax lots in tax_lots table
- TC33: Export reconciliation history with limit parameter
- TC34: Query tax lots with symbol filter and open_only filter
- TC35: Invalid fill parameters validation (zero/negative quantity, negative price, invalid action)
- TC36: High-frequency randomized round-trip execution stress test (500 fills) with zero conservation leakage
- TC37: BrokerAccountSnapshot object vs Dict input inter-operability
- TC38: Thread-safe concurrent fill recording and reconciliation without race conditions
- TC39: Multi-market portfolio valuation with simultaneous KRX and US equity holdings
- TC40: Integration with live trading daemon interface (record_fill, check_circuit_breaker, reconcile_snapshot)
"""

import collections
import hashlib
import json
import math
import os
from pathlib import Path
import random
import sqlite3
import tempfile
import threading
import time
import unittest
from unittest.mock import MagicMock
import pytest

from src.execution.account_reconciliation_engine import (
    AccountReconciliationEngine,
    BrokerAccountSnapshot,
    BrokerReconciliationEngine,
    CashPositionReconciler,
    ClearingReconciliationEngine,
    DISCREPANCY_TOLERANCE_PCT,
    FEATURE,
    FINRA_TAF_MAX_PER_TRADE,
    FINRA_TAF_RATE_PER_SHARE,
    InstitutionalReconciliationEngine,
    KRX_BROKER_FEE,
    KRX_STT_RATE,
    PennyConservationReconciler,
    PENNY_CONSERVATION_EPSILON,
    Phase112ReconciliationEngine,
    PortfolioReconciliationEngine,
    PositionReconciliationEngine,
    ReconciliationReport,
    ReconciliationStatus,
    RealTimeReconciliationEngine,
    RELEASE,
    SEC_SECTION_31_RATE,
    TaxLot,
    TaxLotAdjustment,
    TaxLotMethod,
    US_BROKER_FEE,
    VERSION,
)


class TestPhase112AccountReconciliation(unittest.TestCase):
    """Production test suite for AccountReconciliationEngine (Feature F532)."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.temp_dir.name) / "test_trade_logs.db")
        self.engine = AccountReconciliationEngine(
            initial_cash=100_000_000.0,
            base_currency="KRW",
            db_path=self.db_path,
            tax_lot_method=TaxLotMethod.FIFO,
        )

    def tearDown(self):
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def test_tc01_class_exports_and_aliases(self):
        """TC01: Verify version metadata and complete alias tree resolution."""
        self.assertEqual(VERSION, 112)
        self.assertEqual(RELEASE, "R128")
        self.assertEqual(FEATURE, "F532")

        aliases = [
            RealTimeReconciliationEngine,
            PositionReconciliationEngine,
            BrokerReconciliationEngine,
            Phase112ReconciliationEngine,
            InstitutionalReconciliationEngine,
            CashPositionReconciler,
            ClearingReconciliationEngine,
            PortfolioReconciliationEngine,
            PennyConservationReconciler,
        ]
        for alias in aliases:
            self.assertIs(alias, AccountReconciliationEngine)

        self.assertAlmostEqual(KRX_STT_RATE, 0.0015)
        self.assertAlmostEqual(SEC_SECTION_31_RATE, 2.78e-05)
        self.assertAlmostEqual(FINRA_TAF_RATE_PER_SHARE, 0.000166)
        self.assertAlmostEqual(FINRA_TAF_MAX_PER_TRADE, 8.30)
        self.assertAlmostEqual(DISCREPANCY_TOLERANCE_PCT, 0.0001)
        self.assertAlmostEqual(PENNY_CONSERVATION_EPSILON, 0.0001)

    def test_tc02_mirrored_import_parity(self):
        """TC02: Verify mirrored import parity between src.execution and trading_system.src.execution."""
        import src.execution as src_exec
        import trading_system.src.execution as ts_exec

        self.assertEqual(
            src_exec.AccountReconciliationEngine.__name__,
            ts_exec.AccountReconciliationEngine.__name__,
        )
        self.assertEqual(src_exec.TaxLotMethod.FIFO, ts_exec.TaxLotMethod.FIFO)
        self.assertEqual(src_exec.ReconciliationStatus.PERFECT, ts_exec.ReconciliationStatus.PERFECT)

    def test_tc03_sha256_hash_identity(self):
        """TC03: Guarantee bit-for-bit SHA-256 hash synchrony between src/ and trading_system/ mirrors."""
        root = Path(__file__).resolve().parent.parent
        file_pairs = [
            ("src/execution/account_reconciliation_engine.py", "trading_system/src/execution/account_reconciliation_engine.py"),
            ("src/execution/__init__.py", "trading_system/src/execution/__init__.py"),
        ]
        for p1, p2 in file_pairs:
            path1 = root / p1
            path2 = root / p2
            self.assertTrue(path1.exists(), f"Missing {path1}")
            self.assertTrue(path2.exists(), f"Missing {path2}")
            h1 = hashlib.sha256(path1.read_bytes()).hexdigest()
            h2 = hashlib.sha256(path2.read_bytes()).hexdigest()
            self.assertEqual(h1, h2, f"SHA-256 hash mismatch for {p1} vs {p2}")

    def test_tc04_enums_and_dataclasses(self):
        """TC04: Verify enum values and dataclass serialization."""
        self.assertEqual(TaxLotMethod.FIFO.value, "FIFO")
        self.assertEqual(TaxLotMethod.LIFO.value, "LIFO")
        self.assertEqual(TaxLotMethod.HIFO.value, "HIFO")

        self.assertEqual(ReconciliationStatus.PERFECT.value, "PERFECT")
        self.assertEqual(ReconciliationStatus.WITHIN_TOLERANCE.value, "WITHIN_TOLERANCE")
        self.assertEqual(ReconciliationStatus.WARNING.value, "WARNING")
        self.assertEqual(ReconciliationStatus.CIRCUIT_BREAKER_TRIGGERED.value, "CIRCUIT_BREAKER_TRIGGERED")

        lot = TaxLot(
            lot_id="LOT_1",
            symbol="005930",
            market="KOSPI",
            buy_order_id="ORD_1",
            acquired_at="2026-10-15T09:00:00Z",
            cost_per_share=70000.0,
            original_qty=100,
            remaining_qty=100,
        )
        d = lot.to_dict()
        self.assertEqual(d["lot_id"], "LOT_1")
        self.assertEqual(d["remaining_qty"], 100)
        self.assertEqual(d["cost_per_share"], 70000.0)

    def test_tc05_penny_conservation_buy(self):
        """TC05: Exact penny conservation on BUY fills: |Delta Cash + Cost Basis + Comm| < 0.0001."""
        adj = self.engine.record_fill(
            order_id="ORD_BUY_1",
            symbol="005930",
            market="KOSPI",
            action="BUY",
            quantity=50,
            price=72400.0,
        )
        self.assertLess(adj.conservation_delta, 0.0001)
        # Gross = 50 * 72400 = 3,620,000 KRW
        expected_gross = 3_620_000.0
        expected_comm = round(expected_gross * KRX_BROKER_FEE, 6)
        expected_cash_delta = -expected_gross - expected_comm

        self.assertAlmostEqual(adj.gross_amount, expected_gross, places=4)
        self.assertAlmostEqual(adj.net_cash_delta, expected_cash_delta, places=4)
        self.assertAlmostEqual(self.engine.current_cash, 100_000_000.0 + expected_cash_delta, places=4)
        self.assertEqual(self.engine.positions["005930"]["quantity"], 50)

    def test_tc06_penny_conservation_sell(self):
        """TC06: Exact penny conservation on SELL fills: |Delta Cash - (Gross - Comm - Tax - TAF)| < 0.0001."""
        # First buy 100 shares
        self.engine.record_fill("ORD_BUY", "005930", "KOSPI", "BUY", 100, 70000.0)
        # Then sell 40 shares
        adj = self.engine.record_fill("ORD_SELL", "005930", "KOSPI", "SELL", 40, 75000.0)

        self.assertLess(adj.conservation_delta, 0.0001)
        gross = 40 * 75000.0  # 3,000,000 KRW
        comm = gross * KRX_BROKER_FEE  # 450 KRW
        tax = gross * KRX_STT_RATE      # 4,500 KRW (15 bps)
        expected_net_cash = gross - comm - tax

        self.assertAlmostEqual(adj.net_cash_delta, expected_net_cash, places=4)
        self.assertAlmostEqual(adj.statutory_tax, tax, places=4)
        self.assertEqual(self.engine.positions["005930"]["quantity"], 60)

    def test_tc07_net_equity_le_gross_equity_invariant(self):
        """TC07: Net Equity <= Gross Equity accounting invariant across mixed positions."""
        self.engine.record_fill("B1", "005930", "KOSPI", "BUY", 100, 70000.0)
        self.engine.record_fill("S1", "005930", "KOSPI", "SELL", 30, 72000.0)
        self.engine.accrue_borrow_fees(symbol="005930", annual_rate=0.01, days=5.0)

        val = self.engine.get_portfolio_valuation(current_prices={"005930": 73000.0})
        self.assertLessEqual(val["net_equity"], val["gross_equity"] + 1e-9)
        self.assertGreater(val["accrued_taxes"], 0.0)

    def test_tc08_krx_statutory_taxes(self):
        """TC08: KRX Statutory Transaction Tax (15 bps) on KOSPI and KOSDAQ SELLs (and 0 on BUY)."""
        tax_buy = self.engine.compute_statutory_taxes("005930", "BUY", 70000.0, 100, "KOSPI")
        self.assertEqual(tax_buy, 0.0)

        tax_sell_kospi = self.engine.compute_statutory_taxes("005930", "SELL", 70000.0, 100, "KOSPI")
        self.assertAlmostEqual(tax_sell_kospi, 7_000_000.0 * 0.0015, places=4)

        tax_sell_kosdaq = self.engine.compute_statutory_taxes("091990", "SELL", 50000.0, 200, "KOSDAQ")
        self.assertAlmostEqual(tax_sell_kosdaq, 10_000_000.0 * 0.0015, places=4)

    def test_tc09_us_sec_section_31_tax(self):
        """TC09: US SEC Section 31 tax (2.78e-5) on US equity sales."""
        # 1,000 shares of AAPL at $150 = $150,000
        tax = self.engine.compute_statutory_taxes("AAPL", "SELL", 150.0, 1000, "SP500")
        gross = 150_000.0
        expected_sec = gross * 2.78e-05
        expected_taf = min(8.30, 0.000166 * 1000)
        self.assertAlmostEqual(tax, expected_sec + expected_taf, places=4)

    def test_tc10_us_finra_taf_capping(self):
        """TC10: US FINRA TAF ($0.000166 per share, capped at $8.30) on US equity sales."""
        # Small order: 100 shares -> 100 * 0.000166 = $0.0166
        adj_small = self.engine.record_fill("US_B1", "NVDA", "NASDAQ", "BUY", 100, 100.0)
        adj_sell_small = self.engine.record_fill("US_S1", "NVDA", "NASDAQ", "SELL", 100, 120.0)
        self.assertAlmostEqual(adj_sell_small.finra_taf, 0.0166, places=4)

        # Huge order: 100,000 shares -> 100000 * 0.000166 = $16.60 -> Capped at $8.30
        adj_huge = self.engine.record_fill("US_B2", "NVDA", "NASDAQ", "BUY", 100000, 100.0)
        adj_sell_huge = self.engine.record_fill("US_S2", "NVDA", "NASDAQ", "SELL", 100000, 120.0)
        self.assertAlmostEqual(adj_sell_huge.finra_taf, 8.30, places=4)

    def test_tc11_broker_commission_rates(self):
        """TC11: Standard broker commission calculations (KRX 1.5 bps vs US 0.5 bps)."""
        adj_krx = self.engine.record_fill("KRX_1", "005930", "KOSPI", "BUY", 100, 50000.0)
        # 5,000,000 * 0.00015 = 750 KRW
        self.assertAlmostEqual(adj_krx.commission, 750.0, places=4)

        adj_us = self.engine.record_fill("US_1", "MSFT", "NASDAQ", "BUY", 100, 300.0)
        # 30,000 * 0.00005 = 1.50 USD
        self.assertAlmostEqual(adj_us.commission, 1.50, places=4)

    def test_tc12_tax_lot_fifo_matching(self):
        """TC12: Tax Lot Method: FIFO matching (oldest acquired lot consumed first)."""
        engine_fifo = AccountReconciliationEngine(tax_lot_method=TaxLotMethod.FIFO, db_path=":memory:")
        # Buy Lot 1 at t1, price 50000
        engine_fifo.record_fill("B1", "005930", "KOSPI", "BUY", 100, 50000.0, timestamp="2026-10-01T09:00:00Z")
        # Buy Lot 2 at t2, price 60000
        engine_fifo.record_fill("B2", "005930", "KOSPI", "BUY", 100, 60000.0, timestamp="2026-10-02T09:00:00Z")

        # Sell 50 shares
        adj = engine_fifo.record_fill("S1", "005930", "KOSPI", "SELL", 50, 70000.0, timestamp="2026-10-03T09:00:00Z")
        lots = engine_fifo.tax_lots["005930"]
        # FIFO must consume from Lot 1 (remaining should be 50)
        self.assertEqual(lots[0].remaining_qty, 50)
        self.assertEqual(lots[1].remaining_qty, 100)
        self.assertFalse(lots[0].is_closed)
        self.assertFalse(lots[1].is_closed)

    def test_tc13_tax_lot_lifo_matching(self):
        """TC13: Tax Lot Method: LIFO matching (newest acquired lot consumed first)."""
        engine_lifo = AccountReconciliationEngine(tax_lot_method=TaxLotMethod.LIFO, db_path=":memory:")
        # Buy Lot 1 at t1, price 50000
        engine_lifo.record_fill("B1", "005930", "KOSPI", "BUY", 100, 50000.0, timestamp="2026-10-01T09:00:00Z")
        # Buy Lot 2 at t2, price 60000
        engine_lifo.record_fill("B2", "005930", "KOSPI", "BUY", 100, 60000.0, timestamp="2026-10-02T09:00:00Z")

        # Sell 50 shares
        adj = engine_lifo.record_fill("S1", "005930", "KOSPI", "SELL", 50, 70000.0, timestamp="2026-10-03T09:00:00Z")
        lots = engine_lifo.tax_lots["005930"]
        # LIFO must consume from Lot 2 (Lot 2 remaining should be 50, Lot 1 remains 100)
        self.assertEqual(lots[0].remaining_qty, 100)
        self.assertEqual(lots[1].remaining_qty, 50)

    def test_tc14_tax_lot_hifo_matching(self):
        """TC14: Tax Lot Method: HIFO matching (highest cost lot consumed first to minimize realized PnL)."""
        engine_hifo = AccountReconciliationEngine(tax_lot_method=TaxLotMethod.HIFO, db_path=":memory:")
        # Buy Lot 1 at 50000
        engine_hifo.record_fill("B1", "005930", "KOSPI", "BUY", 100, 50000.0, timestamp="2026-10-01T09:00:00Z")
        # Buy Lot 2 at 70000 (highest cost)
        engine_hifo.record_fill("B2", "005930", "KOSPI", "BUY", 100, 70000.0, timestamp="2026-10-02T09:00:00Z")
        # Buy Lot 3 at 60000
        engine_hifo.record_fill("B3", "005930", "KOSPI", "BUY", 100, 60000.0, timestamp="2026-10-03T09:00:00Z")

        # Sell 50 shares
        adj = engine_hifo.record_fill("S1", "005930", "KOSPI", "SELL", 50, 80000.0, timestamp="2026-10-04T09:00:00Z")
        lots = engine_hifo.tax_lots["005930"]
        # HIFO must consume from Lot 2 (price 70000)
        self.assertEqual(lots[0].remaining_qty, 100)  # Lot 1
        self.assertEqual(lots[1].remaining_qty, 50)   # Lot 2 (consumed 50)
        self.assertEqual(lots[2].remaining_qty, 100)  # Lot 3

    def test_tc15_partial_lot_consumption_across_multiple_lots(self):
        """TC15: Partial lot consumption across multiple tranches with remaining_qty tracking."""
        self.engine.record_fill("B1", "005930", "KOSPI", "BUY", 40, 50000.0, timestamp="2026-10-01T09:00:00Z")
        self.engine.record_fill("B2", "005930", "KOSPI", "BUY", 40, 52000.0, timestamp="2026-10-02T09:00:00Z")

        # Sell 60 shares (closes Lot 1 completely [40 shares] and Lot 2 partially [20 shares])
        adj = self.engine.record_fill("S1", "005930", "KOSPI", "SELL", 60, 55000.0, timestamp="2026-10-03T09:00:00Z")
        lots = self.engine.tax_lots["005930"]

        self.assertEqual(lots[0].remaining_qty, 0)
        self.assertTrue(lots[0].is_closed)
        self.assertEqual(lots[1].remaining_qty, 20)
        self.assertFalse(lots[1].is_closed)
        self.assertEqual(len(adj.closed_lot_ids), 2)

    def test_tc16_realized_pnl_accumulation(self):
        """TC16: Realized PnL attribution per lot and engine-level realized PnL accumulation."""
        self.engine.record_fill("B1", "005930", "KOSPI", "BUY", 100, 50000.0)
        adj = self.engine.record_fill("S1", "005930", "KOSPI", "SELL", 100, 60000.0)

        # Gross PnL ~ (60000 - 50000)*100 = 1,000,000 KRW minus statutory tax & commissions
        self.assertGreater(adj.realized_pnl, 980_000.0)
        self.assertAlmostEqual(self.engine.realized_pnl, adj.realized_pnl, places=4)

    def test_tc17_short_borrow_fee_accrual(self):
        """TC17: Short borrow fee daily accrual via BorrowDynamicsModel or borrow rates."""
        # Open short position: sell 100 shares without prior long holding
        self.engine.record_fill("SHORT_1", "TSLA", "NASDAQ", "SELL", 100, 200.0)
        self.assertEqual(self.engine.positions["TSLA"]["quantity"], -100)

        # Accrue 5 days of borrow fee at 2.0% annual rate
        fee = self.engine.accrue_borrow_fees(symbol="TSLA", annual_rate=0.02, days=5.0, current_price=200.0)
        # short_mv = 100 * 200 = 20,000 USD
        # daily_fee = 20000 * 0.02 / 365 = 1.09589 USD
        expected_fee = (20000.0 * 0.02 / 365.0) * 5.0
        self.assertAlmostEqual(fee, expected_fee, places=3)
        self.assertAlmostEqual(self.engine.accrued_borrow_fees, expected_fee, places=3)

    def test_tc18_borrow_fees_reduce_net_equity(self):
        """TC18: Accrued borrow fees deduction from Net Equity."""
        val_before = self.engine.get_portfolio_valuation()
        self.engine.record_fill("S_SHORT", "NVDA", "NASDAQ", "SELL", 50, 100.0)
        self.engine.accrue_borrow_fees("NVDA", annual_rate=0.10, days=10.0, current_price=100.0)
        val_after = self.engine.get_portfolio_valuation()

        self.assertGreater(val_after["accrued_borrow_fees"], 0.0)
        self.assertEqual(
            val_after["net_equity"],
            val_after["gross_equity"] - val_after["accrued_taxes"] - val_after["accrued_borrow_fees"],
        )

    def test_tc19_reconciliation_dimension1_cash(self):
        """TC19: Continuous 5D reconciliation: Cash Balance (C_internal vs C_broker)."""
        snap = {
            "cash_balance": 100_000_000.0,
            "purchasing_power": 100_000_000.0,
            "maintenance_margin": 0.0,
            "total_asset_value": 100_000_000.0,
            "positions": {},
            "open_orders": [],
        }
        report = self.engine.reconcile_snapshot(snap)
        self.assertAlmostEqual(report.cash_delta, 0.0)
        self.assertEqual(report.status, ReconciliationStatus.PERFECT.value)

    def test_tc20_reconciliation_dimension2_purchasing_power(self):
        """TC20: Continuous 5D reconciliation: Purchasing Power (PP_internal vs PP_broker)."""
        snap = {
            "cash_balance": 100_000_000.0,
            "purchasing_power": 99_999_990.0,  # Tiny delta within tolerance
            "maintenance_margin": 0.0,
            "total_asset_value": 100_000_000.0,
            "positions": {},
            "open_orders": [],
        }
        report = self.engine.reconcile_snapshot(snap)
        self.assertAlmostEqual(report.purchasing_power_delta, 10.0)
        self.assertFalse(report.circuit_breaker_triggered)

    def test_tc21_reconciliation_dimension3_margin(self):
        """TC21: Continuous 5D reconciliation: Margin Limits (M_internal vs M_broker)."""
        self.engine.record_fill("B1", "005930", "KOSPI", "BUY", 100, 70000.0)
        # Margin requirement = 7,000,000 * 0.30 = 2,100,000 KRW
        val = self.engine.get_portfolio_valuation()
        snap = {
            "cash_balance": self.engine.current_cash,
            "purchasing_power": self.engine.current_cash,
            "maintenance_margin": 2_100_000.0,
            "total_asset_value": val["net_equity"],
            "positions": {"005930": 100},
            "open_orders": [],
        }
        report = self.engine.reconcile_snapshot(snap)
        self.assertAlmostEqual(report.internal_margin, 2_100_000.0, places=1)
        self.assertAlmostEqual(report.margin_delta, 0.0, places=1)

    def test_tc22_reconciliation_dimension4_open_orders(self):
        """TC22: Continuous 5D reconciliation: Open Orders (ghost & orphaned detection)."""
        # Internal has order ORD_1
        self.engine.register_open_order("ORD_1", "005930", "BUY", 70000.0, 10)

        # Broker has order ORD_1 matching perfectly
        snap = {
            "cash_balance": self.engine.current_cash,
            "purchasing_power": self.engine.current_cash,
            "total_asset_value": self.engine.get_portfolio_valuation()["net_equity"],
            "positions": {},
            "open_orders": [{"order_id": "ORD_1", "status": "OPEN", "leaves_qty": 10}],
        }
        report = self.engine.reconcile_snapshot(snap)
        self.assertEqual(report.open_order_mismatches, 0)

    def test_tc23_reconciliation_dimension5_settled_positions(self):
        """TC23: Continuous 5D reconciliation: Settled Positions (shares & cost basis)."""
        self.engine.record_fill("B1", "005930", "KOSPI", "BUY", 50, 70000.0)
        val = self.engine.get_portfolio_valuation()
        snap = {
            "cash_balance": self.engine.current_cash,
            "purchasing_power": self.engine.current_cash,
            "total_asset_value": val["net_equity"],
            "positions": {"005930": 50},
            "open_orders": [],
        }
        report = self.engine.reconcile_snapshot(snap)
        self.assertEqual(report.position_mismatches, 0)
        self.assertFalse(report.circuit_breaker_triggered)

    def test_tc24_orphaned_broker_order_circuit_breaker(self):
        """TC24: Orphaned broker order triggers circuit breaker immediately."""
        # Broker has working order ORD_GHOST that internal OMS does not track
        snap = {
            "cash_balance": self.engine.current_cash,
            "purchasing_power": self.engine.current_cash,
            "total_asset_value": self.engine.get_portfolio_valuation()["net_equity"],
            "positions": {},
            "open_orders": [{"order_id": "ORD_ORPHAN_1", "status": "OPEN", "leaves_qty": 50}],
        }
        report = self.engine.reconcile_snapshot(snap)
        self.assertTrue(report.circuit_breaker_triggered)
        self.assertEqual(report.status, ReconciliationStatus.CIRCUIT_BREAKER_TRIGGERED.value)
        self.assertIn("ORD_ORPHAN_1", report.details["orphaned_broker_orders"])
        self.assertTrue(self.engine.check_circuit_breaker())

    def test_tc25_position_quantity_mismatch_circuit_breaker(self):
        """TC25: Position quantity mismatch triggers circuit breaker immediately."""
        self.engine.record_fill("B1", "005930", "KOSPI", "BUY", 100, 70000.0)
        val = self.engine.get_portfolio_valuation()

        # Broker claims we only hold 80 shares
        snap = {
            "cash_balance": self.engine.current_cash,
            "purchasing_power": self.engine.current_cash,
            "total_asset_value": val["net_equity"],
            "positions": {"005930": 80},
            "open_orders": [],
        }
        report = self.engine.reconcile_snapshot(snap)
        self.assertTrue(report.circuit_breaker_triggered)
        self.assertEqual(report.position_mismatches, 1)
        self.assertTrue(self.engine.check_circuit_breaker())

    def test_tc26_equity_discrepancy_circuit_breaker_and_callback(self):
        """TC26: Discrepancy > 0.01% (0.0001) triggers circuit breaker and trading pause callback."""
        callback_mock = MagicMock()
        engine_cb = AccountReconciliationEngine(
            initial_cash=100_000_000.0,
            circuit_breaker_callback=callback_mock,
            db_path=":memory:",
        )
        # Broker reports equity of 99,800,000 KRW (discrepancy = 200,000 / 100,000,000 = 0.20% > 0.01%)
        snap = {
            "cash_balance": 100_000_000.0,
            "purchasing_power": 100_000_000.0,
            "total_asset_value": 99_800_000.0,
            "positions": {},
            "open_orders": [],
        }
        report = engine_cb.reconcile_snapshot(snap)
        self.assertTrue(report.circuit_breaker_triggered)
        self.assertEqual(report.status, ReconciliationStatus.CIRCUIT_BREAKER_TRIGGERED.value)
        self.assertTrue(engine_cb.check_circuit_breaker())
        callback_mock.assert_called_once_with(report)

    def test_tc27_discrepancy_within_tolerance(self):
        """TC27: Discrepancy within tolerance (<= 0.001%) classifies as PERFECT or WITHIN_TOLERANCE."""
        val = self.engine.get_portfolio_valuation()["net_equity"]
        # Discrepancy = 200 KRW on 100,000,000 KRW = 0.0002% <= 0.001%
        snap = {
            "cash_balance": self.engine.current_cash + 200.0,
            "purchasing_power": self.engine.current_cash,
            "total_asset_value": val + 200.0,
            "positions": {},
            "open_orders": [],
        }
        report = self.engine.reconcile_snapshot(snap)
        self.assertFalse(report.circuit_breaker_triggered)
        self.assertIn(report.status, (ReconciliationStatus.PERFECT.value, ReconciliationStatus.WITHIN_TOLERANCE.value))

    def test_tc28_discrepancy_warning_classification(self):
        """TC28: Discrepancy warning state (0.001% < delta <= 0.01%)."""
        val = self.engine.get_portfolio_valuation()["net_equity"]
        # Delta = 5,000 KRW on 100,000,000 KRW = 0.005% (between 0.001% and 0.01%)
        snap = {
            "cash_balance": self.engine.current_cash + 5_000.0,
            "purchasing_power": self.engine.current_cash,
            "total_asset_value": val + 5_000.0,
            "positions": {},
            "open_orders": [],
        }
        report = self.engine.reconcile_snapshot(snap)
        self.assertFalse(report.circuit_breaker_triggered)
        self.assertEqual(report.status, ReconciliationStatus.WARNING.value)

    def test_tc29_circuit_breaker_reset(self):
        """TC29: Circuit breaker reset (reset_circuit_breaker) clears tripped state."""
        self.engine.is_circuit_breaker_triggered = True
        self.assertTrue(self.engine.check_circuit_breaker())

        self.engine.reset_circuit_breaker("Operator audit completed")
        self.assertFalse(self.engine.check_circuit_breaker())

    def test_tc30_sync_to_broker(self):
        """TC30: Ledger synchronization to broker (sync_to_broker)."""
        self.engine.is_circuit_breaker_triggered = True
        snap = {
            "cash_balance": 105_000_000.0,
            "positions": {"005930": {"quantity": 75, "average_price": 71000.0}},
        }
        self.engine.sync_to_broker(snap)

        self.assertEqual(self.engine.current_cash, 105_000_000.0)
        self.assertEqual(self.engine.positions["005930"]["quantity"], 75)
        self.assertFalse(self.engine.check_circuit_breaker())

    def test_tc31_sqlite_persistence_account_reconciliations(self):
        """TC31: SQLite database persistence: audit records in account_reconciliations table."""
        snap = {
            "cash_balance": 100_000_000.0,
            "purchasing_power": 100_000_000.0,
            "total_asset_value": 100_000_000.0,
            "positions": {},
            "open_orders": [],
        }
        rep = self.engine.reconcile_snapshot(snap)

        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT reconciliation_id, status, internal_cash FROM account_reconciliations WHERE reconciliation_id = ?", (rep.reconciliation_id,))
        row = cur.fetchone()
        conn.close()

        self.assertIsNotNone(row)
        self.assertEqual(row[0], rep.reconciliation_id)
        self.assertEqual(row[1], rep.status)
        self.assertEqual(row[2], 100_000_000.0)

    def test_tc32_sqlite_persistence_tax_lots(self):
        """TC32: SQLite database persistence: tax lots in tax_lots table."""
        adj = self.engine.record_fill("B_SQL", "005930", "KOSPI", "BUY", 100, 68000.0)
        lot = self.engine.tax_lots["005930"][0]

        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT lot_id, symbol, cost_per_share, original_qty, remaining_qty FROM tax_lots WHERE lot_id = ?", (lot.lot_id,))
        row = cur.fetchone()
        conn.close()

        self.assertIsNotNone(row)
        self.assertEqual(row[0], lot.lot_id)
        self.assertEqual(row[1], "005930")
        self.assertEqual(row[2], 68000.0)
        self.assertEqual(row[3], 100)
        self.assertEqual(row[4], 100)

    def test_tc33_export_reconciliation_history(self):
        """TC33: Export reconciliation history with limit parameter."""
        snap = {
            "cash_balance": 100_000_000.0,
            "purchasing_power": 100_000_000.0,
            "total_asset_value": 100_000_000.0,
            "positions": {},
            "open_orders": [],
        }
        for _ in range(5):
            self.engine.reconcile_snapshot(snap)

        history = self.engine.export_reconciliation_history(limit=3)
        self.assertEqual(len(history), 3)
        self.assertIn("reconciliation_id", history[0])

    def test_tc34_query_tax_lots_filtering(self):
        """TC34: Query tax lots with symbol filter and open_only filter."""
        self.engine.record_fill("B1", "005930", "KOSPI", "BUY", 50, 70000.0)
        self.engine.record_fill("B2", "000660", "KOSPI", "BUY", 50, 120000.0)
        self.engine.record_fill("S1", "005930", "KOSPI", "SELL", 50, 75000.0)  # Closes 005930 lot

        open_lots = self.engine.get_tax_lots(open_only=True)
        self.assertEqual(len(open_lots), 1)
        self.assertEqual(open_lots[0].symbol, "000660")

        all_005930_lots = self.engine.get_tax_lots("005930", open_only=False)
        self.assertEqual(len(all_005930_lots), 1)
        self.assertTrue(all_005930_lots[0].is_closed)

    def test_tc35_invalid_fill_parameters_validation(self):
        """TC35: Invalid fill parameters validation (zero/negative quantity, negative price, invalid action)."""
        with self.assertRaises(ValueError):
            self.engine.record_fill("ORD_ERR", "005930", "KOSPI", "BUY", 0, 70000.0)

        with self.assertRaises(ValueError):
            self.engine.record_fill("ORD_ERR", "005930", "KOSPI", "BUY", 10, -500.0)

        with self.assertRaises(ValueError):
            self.engine.record_fill("ORD_ERR", "005930", "KOSPI", "INVALID_ACTION", 10, 70000.0)

    def test_tc36_high_frequency_randomized_round_trip_stress(self):
        """TC36: High-frequency randomized round-trip execution stress test (500 fills) with zero conservation leakage."""
        rng = random.Random(42)
        symbols = ["005930", "000660", "AAPL", "MSFT", "NVDA"]

        for i in range(250):
            sym = rng.choice(symbols)
            mkt = "KOSPI" if sym.isdigit() else "NASDAQ"
            px = round(rng.uniform(50.0, 500.0) if not sym.isdigit() else rng.uniform(40000.0, 90000.0), 2)
            qty = rng.randint(1, 20)

            # Buy
            adj_buy = self.engine.record_fill(f"R_BUY_{i}", sym, mkt, "BUY", qty, px)
            self.assertLess(adj_buy.conservation_delta, 0.0001)

            # Sell
            px_sell = px * rng.uniform(0.95, 1.05)
            adj_sell = self.engine.record_fill(f"R_SELL_{i}", sym, mkt, "SELL", qty, px_sell)
            self.assertLess(adj_sell.conservation_delta, 0.0001)

        val = self.engine.get_portfolio_valuation()
        self.assertLessEqual(val["net_equity"], val["gross_equity"] + 1e-9)

    def test_tc37_broker_snapshot_interoperability(self):
        """TC37: BrokerAccountSnapshot object vs Dict input inter-operability."""
        snap_obj = BrokerAccountSnapshot(
            cash_balance=100_000_000.0,
            purchasing_power=100_000_000.0,
            maintenance_margin=0.0,
            total_asset_value=100_000_000.0,
            positions={"005930": 0},
            open_orders=[],
        )
        rep1 = self.engine.reconcile_snapshot(snap_obj)
        self.assertEqual(rep1.status, ReconciliationStatus.PERFECT.value)

        snap_dict = snap_obj.to_dict()
        rep2 = self.engine.reconcile_snapshot(snap_dict)
        self.assertEqual(rep2.status, ReconciliationStatus.PERFECT.value)

    def test_tc38_threadsafe_concurrent_fill_and_reconciliation(self):
        """TC38: Thread-safe concurrent fill recording and reconciliation without race conditions."""
        exceptions = []

        def _worker_buys(n):
            try:
                for i in range(25):
                    self.engine.record_fill(f"TH_BUY_{n}_{i}", "005930", "KOSPI", "BUY", 1, 70000.0)
            except Exception as e:
                exceptions.append(e)

        def _worker_recon():
            try:
                for _ in range(10):
                    val = self.engine.get_portfolio_valuation()["net_equity"]
                    self.engine.reconcile_snapshot({
                        "cash_balance": self.engine.current_cash,
                        "purchasing_power": self.engine.current_cash,
                        "total_asset_value": val,
                        "positions": {"005930": self.engine.positions.get("005930", {}).get("quantity", 0)},
                        "open_orders": [],
                    })
                    time.sleep(0.005)
            except Exception as e:
                exceptions.append(e)

        threads = [
            threading.Thread(target=_worker_buys, args=(1,)),
            threading.Thread(target=_worker_buys, args=(2,)),
            threading.Thread(target=_worker_recon),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(exceptions), 0, f"Thread safety exceptions: {exceptions}")
        self.assertEqual(self.engine.positions["005930"]["quantity"], 50)

    def test_tc39_multi_market_portfolio_valuation(self):
        """TC39: Multi-market portfolio valuation with simultaneous KRX and US equity holdings."""
        self.engine.record_fill("KRX_B", "005930", "KOSPI", "BUY", 100, 70000.0)
        self.engine.record_fill("US_B", "AAPL", "SP500", "BUY", 50, 150.0)

        val = self.engine.get_portfolio_valuation(current_prices={"005930": 72000.0, "AAPL": 160.0})
        # Long MV = 100 * 72000 + 50 * 160 = 7,200,000 + 8,000 = 7,208,000
        self.assertAlmostEqual(val["long_market_value"], 7_208_000.0, places=2)
        self.assertLessEqual(val["net_equity"], val["gross_equity"])

    def test_tc40_live_trading_daemon_interface_compatibility(self):
        """TC40: Integration with live trading daemon interface (record_fill, check_circuit_breaker, reconcile_snapshot)."""
        from src.execution.live_trading_daemon import LiveTradingDaemon, LiveDaemonConfig

        cfg = LiveDaemonConfig(db_path=":memory:")
        daemon = LiveTradingDaemon(config=cfg, reconciliation_engine=self.engine)

        self.assertIs(daemon.reconciliation_engine, self.engine)
        self.assertFalse(daemon.reconciliation_engine.check_circuit_breaker())

        # Simulate daemon invoking record_fill upon tranche fill
        adj = daemon.reconciliation_engine.record_fill(
            order_id="TR_101",
            symbol="005930",
            market="KOSPI",
            action="BUY",
            quantity=25,
            price=70500.0,
        )
        self.assertEqual(adj.quantity, 25)
        self.assertEqual(self.engine.positions["005930"]["quantity"], 25)


if __name__ == "__main__":
    unittest.main()
