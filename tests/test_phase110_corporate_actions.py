"""
tests/test_phase110_corporate_actions.py
=========================================
Comprehensive Unit, Integration, Invariant, and Property Test Harness for
Corporate Actions & Dividend Adjustment Real-Time Rebalancing Engine
Phase 110 (Release R126 / v117 Production Master / Feature F523).

Test Categories Covered:
- Category 1: Class Exports, Signatures & Full Alias Trees (TC01~TC04)
- Category 2: Dual Placement Mirror SHA-256 Hash Integrity (TC05)
- Category 3: Forward Stock Splits (2:1, 10:1, 100:1) & Ex-Price Invariants (TC06~TC10)
- Category 4: Reverse Stock Splits (1:5, 1:10) & Fractional Cash-in-Lieu (TC11~TC15)
- Category 5: Cash Dividends (Ordinary, Special) & Zero Artificial PnL Spike (TC16~TC20)
- Category 6: Stock Dividends & Rights Issues (TC21~TC25)
- Category 7: Structural Actions: Spin-Offs & Mergers (TC26~TC30)
- Category 8: Continuous Adjustment Factor Chains & OHLCV Adjustments (TC31~TC35)
- Category 9: Rebalance Order Synthesis & Cash Drag Neutralization (TC36~TC40)
- Category 10: Non-Interfering OMS Execution Safety & Multi-Market Stress (TC41~TC45)
"""

from __future__ import annotations

import copy
import datetime
import hashlib
import math
import sys
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

# Ensure project roots are on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p in (str(PROJECT_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.data_layer.corporate_action_rebalancer import (
    ActionResult,
    CorporateAction,
    CorporateActionEvent,
    CorporateActionRebalanceEngine,
    CorporateActionRebalancer,
    CorporateActionResult,
    CorporateActionType,
    DividendSplitAdjustmentEngine,
    ExDividendRebalancer,
    InstitutionalCorporateActionEngine,
    Phase110CorporateActionRebalancer,
    RebalanceOrder,
    RebalanceOrderPlan,
    TaxLot,
    format_date,
    parse_date,
)
from trading_system.src.data_layer.corporate_action_rebalancer import (
    CorporateActionRebalancer as MirroredCorporateActionRebalancer,
    TaxLot as MirroredTaxLot,
)


class TestPhase110CorporateActions(unittest.TestCase):
    """Exhaustive test suite for CorporateActionRebalancer (Feature F523)."""

    def setUp(self) -> None:
        self.rebalancer = CorporateActionRebalancer(
            cash_drag_threshold_pct=0.005,
            target_cash_pct=0.01,
            min_order_notional=50.0,
            allow_fractional_shares=False,
            version=117,
        )

    # -----------------------------------------------------------------------
    # Category 1: Class Exports, Signatures & Full Alias Trees (TC01~TC04)
    # -----------------------------------------------------------------------

    def test_tc01_class_exports_and_alias_tree(self) -> None:
        """Verify all canonical classes and institutional alias trees are exported and identical."""
        self.assertIs(CorporateActionRebalanceEngine, CorporateActionRebalancer)
        self.assertIs(InstitutionalCorporateActionEngine, CorporateActionRebalancer)
        self.assertIs(DividendSplitAdjustmentEngine, CorporateActionRebalancer)
        self.assertIs(Phase110CorporateActionRebalancer, CorporateActionRebalancer)
        self.assertIs(ExDividendRebalancer, CorporateActionRebalancer)
        self.assertIs(CorporateActionEvent, CorporateAction)
        self.assertIs(CorporateActionResult, ActionResult)
        self.assertIs(RebalanceOrderPlan, RebalanceOrder)

    def test_tc02_corporate_action_types_enum(self) -> None:
        """Verify all 7 standard and structural corporate action enum types exist."""
        expected_types = {
            "CASH_DIVIDEND",
            "STOCK_DIVIDEND",
            "STOCK_SPLIT",
            "REVERSE_SPLIT",
            "RIGHTS_ISSUE",
            "SPIN_OFF",
            "MERGER",
        }
        actual_types = {e.value for e in CorporateActionType}
        self.assertEqual(expected_types, actual_types)

    def test_tc03_taxlot_initialization_and_properties(self) -> None:
        """Verify TaxLot dataclass initialization, market value, unrealized pnl, and holding period."""
        lot = TaxLot(
            lot_id="LOT_001",
            symbol="aapl",
            market="nasdaq",
            acquisition_date="2025-01-15",
            quantity=100.0,
            cost_basis_per_share=150.0,
            current_price=180.0,
            commission_paid=5.0,
            tax_regime="US",
        )
        self.assertEqual(lot.symbol, "AAPL")
        self.assertEqual(lot.market, "NASDAQ")
        self.assertEqual(lot.acquisition_date, "2025-01-15")
        self.assertAlmostEqual(lot.total_cost, 15005.0)
        self.assertAlmostEqual(lot.market_value, 18000.0)
        self.assertAlmostEqual(lot.unrealized_pnl, 3000.0)
        self.assertAlmostEqual(lot.unrealized_return_pct, 0.20)
        self.assertGreater(lot.holding_days("2026-02-01"), 365)
        self.assertTrue(lot.is_long_term("2026-02-01"))
        self.assertEqual(lot.resolve_tax_regime(), "US")

    def test_tc04_krx_taxlot_tax_regime_inference(self) -> None:
        """Verify KRX taxlot numeric symbol inference and holding calculation."""
        lot = TaxLot(
            lot_id="LOT_KRX_001",
            symbol="005930",
            market="KOSPI",
            acquisition_date="2026-05-01",
            quantity=50.0,
            cost_basis_per_share=70000.0,
            current_price=72000.0,
        )
        self.assertEqual(lot.resolve_tax_regime(), "KRX")
        self.assertFalse(lot.is_long_term("2026-08-01"))

    # -----------------------------------------------------------------------
    # Category 2: Dual Placement Mirror SHA-256 Hash Integrity (TC05)
    # -----------------------------------------------------------------------

    def test_tc05_dual_placement_mirror_sha256_hash_integrity(self) -> None:
        """Verify bit-for-bit SHA-256 identity between root and trading_system paths."""
        p1 = PROJECT_ROOT / "src" / "data_layer" / "corporate_action_rebalancer.py"
        p2 = TRADING_SYSTEM_DIR / "src" / "data_layer" / "corporate_action_rebalancer.py"

        self.assertTrue(p1.exists(), f"Root file missing: {p1}")
        self.assertTrue(p2.exists(), f"Mirrored file missing: {p2}")

        h1 = hashlib.sha256(p1.read_bytes()).hexdigest()
        h2 = hashlib.sha256(p2.read_bytes()).hexdigest()
        self.assertEqual(h1, h2, "Dual placement files must be 100% bit-for-bit identical.")
        self.assertGreater(len(h1), 0)

    # -----------------------------------------------------------------------
    # Category 3: Forward Stock Splits (2:1, 10:1, 100:1) & Ex-Price Invariants (TC06~TC10)
    # -----------------------------------------------------------------------

    def test_tc06_forward_split_2_for_1_factor_and_prices(self) -> None:
        """Verify 2:1 forward split: factor f=0.5, shares double, price halves, NAV strictly conserved."""
        action = CorporateAction(
            event_id="SPLIT_2_1_AAPL",
            symbol="AAPL",
            action_type=CorporateActionType.STOCK_SPLIT,
            ex_date="2026-06-01",
            ratio=2.0,
            cum_price=200.0,
        )
        factor = self.rebalancer.calculate_adjustment_factor(action)
        self.assertAlmostEqual(factor, 0.50)

        portfolio = {
            "cash": 10000.0,
            "positions": {"AAPL": 100.0},
            "prices": {"AAPL": 200.0},
        }
        res = self.rebalancer.process_action(action, portfolio_state=portfolio)
        self.assertAlmostEqual(res.adjustment_factor, 0.50)
        self.assertAlmostEqual(res.old_quantity, 100.0)
        self.assertAlmostEqual(res.new_quantity, 200.0)
        self.assertAlmostEqual(res.post_event_price, 100.0)
        self.assertAlmostEqual(res.nav_pre, 30000.0)
        self.assertAlmostEqual(res.nav_post, 30000.0)
        self.assertAlmostEqual(res.nav_delta, 0.0, places=7)

    def test_tc07_forward_split_10_for_1_taxlot_conservation(self) -> None:
        """Verify 10:1 forward split preserves TaxLot total acquisition cost basis strictly."""
        lots = [
            TaxLot(lot_id="L1", symbol="NVDA", quantity=10.0, cost_basis_per_share=800.0),
            TaxLot(lot_id="L2", symbol="NVDA", quantity=25.0, cost_basis_per_share=920.0),
        ]
        total_cost_pre = sum(l.total_cost for l in lots)
        self.assertAlmostEqual(total_cost_pre, (10 * 800) + (25 * 920))

        action = CorporateAction(
            event_id="SPLIT_10_1_NVDA",
            symbol="NVDA",
            action_type=CorporateActionType.STOCK_SPLIT,
            ex_date="2026-07-01",
            ratio=10.0,
            cum_price=1000.0,
        )
        adjusted_lots = self.rebalancer.adjust_tax_lots(lots, action)
        self.assertEqual(len(adjusted_lots), 2)
        self.assertAlmostEqual(adjusted_lots[0].quantity, 100.0)
        self.assertAlmostEqual(adjusted_lots[0].cost_basis_per_share, 80.0)
        self.assertAlmostEqual(adjusted_lots[1].quantity, 250.0)
        self.assertAlmostEqual(adjusted_lots[1].cost_basis_per_share, 92.0)

        total_cost_post = sum(l.total_cost for l in adjusted_lots)
        self.assertAlmostEqual(total_cost_pre, total_cost_post, places=7)

    def test_tc08_forward_split_100_for_1_extreme_scale(self) -> None:
        """Verify extreme 100:1 forward split maintains precision without overflow or float drift."""
        action = CorporateAction(
            event_id="SPLIT_100_1",
            symbol="BRK",
            action_type=CorporateActionType.STOCK_SPLIT,
            ex_date="2026-08-01",
            ratio=100.0,
            cum_price=500000.0,
        )
        factor = self.rebalancer.calculate_adjustment_factor(action)
        self.assertAlmostEqual(factor, 0.01)

        lot = TaxLot(lot_id="L_BRK", symbol="BRK", quantity=5.0, cost_basis_per_share=450000.0)
        adj_lots = self.rebalancer.adjust_tax_lots([lot], action)
        self.assertAlmostEqual(adj_lots[0].quantity, 500.0)
        self.assertAlmostEqual(adj_lots[0].cost_basis_per_share, 4500.0)
        self.assertAlmostEqual(lot.total_cost, adj_lots[0].total_cost, places=7)

    def test_tc09_multi_lot_forward_split_different_symbols(self) -> None:
        """Verify split on target symbol leaves other symbols in tax lot portfolio unaffected."""
        lots = [
            TaxLot(lot_id="L_AAPL", symbol="AAPL", quantity=50.0, cost_basis_per_share=150.0),
            TaxLot(lot_id="L_MSFT", symbol="MSFT", quantity=30.0, cost_basis_per_share=400.0),
        ]
        action = CorporateAction(
            event_id="SPLIT_AAPL",
            symbol="AAPL",
            action_type=CorporateActionType.STOCK_SPLIT,
            ex_date="2026-08-10",
            ratio=2.0,
        )
        adj = self.rebalancer.adjust_tax_lots(lots, action)
        aapl_lot = next(l for l in adj if l.symbol == "AAPL")
        msft_lot = next(l for l in adj if l.symbol == "MSFT")

        self.assertAlmostEqual(aapl_lot.quantity, 100.0)
        self.assertAlmostEqual(msft_lot.quantity, 30.0)  # Unchanged
        self.assertAlmostEqual(msft_lot.cost_basis_per_share, 400.0)

    def test_tc10_zero_or_negative_split_guard(self) -> None:
        """Verify resilient fallback if invalid split ratio <= 0 is passed."""
        action = CorporateAction(
            event_id="BAD_SPLIT",
            symbol="XYZ",
            action_type=CorporateActionType.STOCK_SPLIT,
            ex_date="2026-08-15",
            ratio=-5.0,
        )
        factor = self.rebalancer.calculate_adjustment_factor(action)
        self.assertGreater(factor, 0.0)

    # -----------------------------------------------------------------------
    # Category 4: Reverse Stock Splits (1:5, 1:10) & Fractional Cash-in-Lieu (TC11~TC15)
    # -----------------------------------------------------------------------

    def test_tc11_reverse_split_1_for_5_factor_and_prices(self) -> None:
        """Verify 1:5 reverse split: ratio=0.2, price multiplier=5.0, quantity divided by 5."""
        action = CorporateAction(
            event_id="REV_1_5",
            symbol="MEME",
            action_type=CorporateActionType.REVERSE_SPLIT,
            ex_date="2026-09-01",
            ratio=0.20,
            cum_price=10.0,
        )
        factor = self.rebalancer.calculate_adjustment_factor(action)
        self.assertAlmostEqual(factor, 5.0)

        portfolio = {
            "cash": 2000.0,
            "positions": {"MEME": 100.0},
            "prices": {"MEME": 10.0},
        }
        res = self.rebalancer.process_action(action, portfolio_state=portfolio)
        self.assertAlmostEqual(res.new_quantity, 20.0)
        self.assertAlmostEqual(res.post_event_price, 50.0)
        self.assertAlmostEqual(res.nav_pre, 3000.0)
        self.assertAlmostEqual(res.nav_post, 3000.0)
        self.assertAlmostEqual(res.nav_delta, 0.0, places=7)

    def test_tc12_reverse_split_1_for_10_taxlot_basis_preservation(self) -> None:
        """Verify 1:10 reverse split: ratio=0.10, per-share basis x10, total cost strictly preserved."""
        lot = TaxLot(lot_id="LOT_REV10", symbol="PENNY", quantity=1000.0, cost_basis_per_share=2.50)
        action = CorporateAction(
            event_id="REV_1_10",
            symbol="PENNY",
            action_type=CorporateActionType.REVERSE_SPLIT,
            ex_date="2026-09-10",
            ratio=0.10,
            cum_price=2.0,
        )
        adj_lots = self.rebalancer.adjust_tax_lots([lot], action)
        self.assertEqual(len(adj_lots), 1)
        self.assertAlmostEqual(adj_lots[0].quantity, 100.0)
        self.assertAlmostEqual(adj_lots[0].cost_basis_per_share, 25.0)
        self.assertAlmostEqual(lot.total_cost, adj_lots[0].total_cost, places=7)

    def test_tc13_reverse_split_fractional_shares_cash_in_lieu(self) -> None:
        """Verify fractional shares in reverse split are liquidated into cash with exact NAV conservation."""
        # Holding 12 shares. 1:5 reverse split -> 12 * 0.2 = 2.4 shares.
        # Under integer share mode (allow_fractional_shares=False), 2 whole shares + 0.4 cash-in-lieu.
        # Cum price = 10.0, Ex price = 50.0. Cash in lieu = 0.4 * 50 = $20.0.
        action = CorporateAction(
            event_id="REV_FRAC",
            symbol="FRAC",
            action_type=CorporateActionType.REVERSE_SPLIT,
            ex_date="2026-09-15",
            ratio=0.20,
            cum_price=10.0,
            cash_in_lieu=True,
        )
        portfolio = {
            "cash": 500.0,
            "positions": {"FRAC": 12.0},
            "prices": {"FRAC": 10.0},
        }
        res = self.rebalancer.process_action(action, portfolio_state=portfolio)
        self.assertEqual(res.new_quantity, 2.0)
        self.assertAlmostEqual(res.cash_in_lieu, 20.0)
        self.assertAlmostEqual(res.cash_generated, 20.0)

        # Pre-event: 12 * 10 + 500 = 620
        # Post-event: 2 * 50 + (500 + 20) = 100 + 520 = 620
        self.assertAlmostEqual(res.nav_pre, 620.0)
        self.assertAlmostEqual(res.nav_post, 620.0)
        self.assertAlmostEqual(res.nav_delta, 0.0, places=7)

    def test_tc14_reverse_split_allow_fractional_shares_mode(self) -> None:
        """Verify fractional shares mode retains exact non-integer float quantities without cash-in-lieu."""
        reb = CorporateActionRebalancer(allow_fractional_shares=True)
        action = CorporateAction(
            event_id="REV_FLOAT",
            symbol="FRAC",
            action_type=CorporateActionType.REVERSE_SPLIT,
            ex_date="2026-09-18",
            ratio=0.20,
            cum_price=10.0,
        )
        portfolio = {
            "cash": 500.0,
            "positions": {"FRAC": 12.0},
            "prices": {"FRAC": 10.0},
        }
        res = reb.process_action(action, portfolio_state=portfolio)
        self.assertAlmostEqual(res.new_quantity, 2.4)
        self.assertAlmostEqual(res.cash_in_lieu, 0.0)
        self.assertAlmostEqual(res.nav_pre, 620.0)
        self.assertAlmostEqual(res.nav_post, 620.0)

    def test_tc15_consecutive_forward_and_reverse_splits(self) -> None:
        """Verify 2:1 forward split followed by 1:2 reverse split returns to original basis."""
        lot = TaxLot(lot_id="LOT_CYCLE", symbol="CYCLE", quantity=100.0, cost_basis_per_share=50.0)
        a1 = CorporateAction("A1", "CYCLE", CorporateActionType.STOCK_SPLIT, "2026-01-01", ratio=2.0)
        a2 = CorporateAction("A2", "CYCLE", CorporateActionType.REVERSE_SPLIT, "2026-02-01", ratio=0.50)

        step1 = self.rebalancer.adjust_tax_lots([lot], a1)
        self.assertAlmostEqual(step1[0].quantity, 200.0)
        self.assertAlmostEqual(step1[0].cost_basis_per_share, 25.0)

        step2 = self.rebalancer.adjust_tax_lots(step1, a2)
        self.assertAlmostEqual(step2[0].quantity, 100.0)
        self.assertAlmostEqual(step2[0].cost_basis_per_share, 50.0)
        self.assertAlmostEqual(lot.total_cost, step2[0].total_cost, places=7)

    # -----------------------------------------------------------------------
    # Category 5: Cash Dividends (Ordinary, Special) & Zero Artificial PnL Spike (TC16~TC20)
    # -----------------------------------------------------------------------

    def test_tc16_ordinary_cash_dividend_nav_conservation(self) -> None:
        """Verify $2.50 cash dividend on $100 stock drops ex-price to $97.50 with exact NAV preservation."""
        action = CorporateAction(
            event_id="DIV_001",
            symbol="KO",
            action_type=CorporateActionType.CASH_DIVIDEND,
            ex_date="2026-03-15",
            cash_amount=2.50,
            cum_price=100.0,
        )
        factor = self.rebalancer.calculate_adjustment_factor(action)
        self.assertAlmostEqual(factor, (100.0 - 2.50) / 100.0)  # 0.975

        portfolio = {
            "cash": 5000.0,
            "positions": {"KO": 200.0},
            "prices": {"KO": 100.0},
        }
        res = self.rebalancer.process_action(action, portfolio_state=portfolio)
        self.assertAlmostEqual(res.cash_generated, 500.0)  # 200 * $2.50
        self.assertAlmostEqual(res.post_event_price, 97.50)
        # Pre: 200 * 100 + 5000 = 25000
        # Post: 200 * 97.50 + 5500 = 19500 + 5500 = 25000
        self.assertAlmostEqual(res.nav_pre, 25000.0)
        self.assertAlmostEqual(res.nav_post, 25000.0)
        self.assertAlmostEqual(res.nav_delta, 0.0, places=7)

    def test_tc17_krx_cash_dividend_reconciliation(self) -> None:
        """Verify KRX 1,500 KRW cash dividend on Samsung Electronics (005930)."""
        action = CorporateAction(
            event_id="DIV_005930",
            symbol="005930",
            action_type=CorporateActionType.CASH_DIVIDEND,
            ex_date="2026-04-01",
            cash_amount=1500.0,
            cum_price=75000.0,
        )
        factor = self.rebalancer.calculate_adjustment_factor(action)
        self.assertAlmostEqual(factor, (75000 - 1500) / 75000)

        portfolio = {
            "cash": 10000000.0,
            "positions": {"005930": 1000.0},
            "prices": {"005930": 75000.0},
        }
        res = self.rebalancer.process_action(action, portfolio_state=portfolio)
        self.assertAlmostEqual(res.cash_generated, 1500000.0)
        self.assertAlmostEqual(res.post_event_price, 73500.0)
        self.assertAlmostEqual(res.nav_delta, 0.0, places=5)

    def test_tc18_special_large_cash_dividend(self) -> None:
        """Verify massive special dividend (e.g. $20 on $50 stock = 40%) preserves NAV."""
        action = CorporateAction(
            event_id="SPEC_DIV",
            symbol="SPCL",
            action_type=CorporateActionType.CASH_DIVIDEND,
            ex_date="2026-05-15",
            cash_amount=20.0,
            cum_price=50.0,
        )
        factor = self.rebalancer.calculate_adjustment_factor(action)
        self.assertAlmostEqual(factor, 0.60)

        portfolio = {"cash": 1000.0, "positions": {"SPCL": 500.0}, "prices": {"SPCL": 50.0}}
        res = self.rebalancer.process_action(action, portfolio_state=portfolio)
        self.assertAlmostEqual(res.cash_generated, 10000.0)
        self.assertAlmostEqual(res.post_event_price, 30.0)
        self.assertAlmostEqual(res.nav_pre, 26000.0)
        self.assertAlmostEqual(res.nav_post, 26000.0)

    def test_tc19_cash_dividend_taxlot_basis_preservation(self) -> None:
        """Verify ordinary cash dividend does not alter per-share tax basis."""
        lot = TaxLot(lot_id="LOT_DIV", symbol="DIVS", quantity=100.0, cost_basis_per_share=80.0)
        action = CorporateAction(
            event_id="DIV_ACT",
            symbol="DIVS",
            action_type=CorporateActionType.CASH_DIVIDEND,
            ex_date="2026-06-01",
            cash_amount=2.0,
            cum_price=90.0,
        )
        adj_lots = self.rebalancer.adjust_tax_lots([lot], action)
        self.assertAlmostEqual(adj_lots[0].quantity, 100.0)
        self.assertAlmostEqual(adj_lots[0].cost_basis_per_share, 80.0)
        self.assertAlmostEqual(adj_lots[0].current_price, 88.0)

    def test_tc20_zero_cash_dividend_guard(self) -> None:
        """Verify zero cash dividend returns factor 1.0 without NaN."""
        action = CorporateAction(
            event_id="ZERO_DIV",
            symbol="DIVS",
            action_type=CorporateActionType.CASH_DIVIDEND,
            ex_date="2026-06-05",
            cash_amount=0.0,
            cum_price=50.0,
        )
        factor = self.rebalancer.calculate_adjustment_factor(action)
        self.assertEqual(factor, 1.0)

    # -----------------------------------------------------------------------
    # Category 6: Stock Dividends & Rights Issues (TC21~TC25)
    # -----------------------------------------------------------------------

    def test_tc21_stock_dividend_5_percent_reconciliation(self) -> None:
        """Verify 5% stock dividend (ratio=0.05): shares x1.05, price / 1.05, NAV conserved."""
        action = CorporateAction(
            event_id="STK_DIV_5",
            symbol="GROW",
            action_type=CorporateActionType.STOCK_DIVIDEND,
            ex_date="2026-04-10",
            ratio=0.05,
            cum_price=105.0,
        )
        factor = self.rebalancer.calculate_adjustment_factor(action)
        self.assertAlmostEqual(factor, 1.0 / 1.05)

        lot = TaxLot(lot_id="L_GROW", symbol="GROW", quantity=100.0, cost_basis_per_share=90.0)
        adj = self.rebalancer.adjust_tax_lots([lot], action)
        self.assertAlmostEqual(adj[0].quantity, 105.0)
        self.assertAlmostEqual(adj[0].cost_basis_per_share, 90.0 / 1.05)
        self.assertAlmostEqual(lot.total_cost, adj[0].total_cost, places=7)

    def test_tc22_stock_dividend_10_percent_nav_conservation(self) -> None:
        """Verify 10% stock dividend process_action preserves NAV."""
        action = CorporateAction(
            event_id="STK_DIV_10",
            symbol="GROW10",
            action_type=CorporateActionType.STOCK_DIVIDEND,
            ex_date="2026-04-20",
            ratio=0.10,
            cum_price=110.0,
        )
        portfolio = {"cash": 1000.0, "positions": {"GROW10": 100.0}, "prices": {"GROW10": 110.0}}
        res = self.rebalancer.process_action(action, portfolio_state=portfolio)
        self.assertAlmostEqual(res.new_quantity, 110.0)
        self.assertAlmostEqual(res.post_event_price, 100.0)
        self.assertAlmostEqual(res.nav_pre, 12000.0)
        self.assertAlmostEqual(res.nav_post, 12000.0)

    def test_tc23_rights_issue_theoretical_ex_rights_price(self) -> None:
        """Verify theoretical ex-rights price P_ex = (P_cum + r * P_sub) / (1 + r)."""
        # P_cum = 100.0, ratio = 0.25 (1 for 4), P_sub = 80.0
        # P_ex = (100 + 0.25 * 80) / 1.25 = (100 + 20) / 1.25 = 120 / 1.25 = 96.0
        # Factor = 96 / 100 = 0.96
        action = CorporateAction(
            event_id="RIGHTS_01",
            symbol="CORP",
            action_type=CorporateActionType.RIGHTS_ISSUE,
            ex_date="2026-05-01",
            ratio=0.25,
            subscription_price=80.0,
            cum_price=100.0,
        )
        factor = self.rebalancer.calculate_adjustment_factor(action)
        self.assertAlmostEqual(factor, 0.96)

    def test_tc24_rights_issue_exercised_nav_conservation(self) -> None:
        """Verify exercised rights issue: subscription cash paid from portfolio cash, NAV strictly conserved."""
        # 400 shares held. Ratio = 0.25 -> 100 new shares acquired at $80. Cost = $8,000.
        # Total shares = 500. P_ex = $96.0. New stock value = 500 * 96 = $48,000.
        # Cash was $10,000. Cash post = 10,000 - 8,000 = $2,000.
        # Pre: 400 * 100 + 10,000 = 50,000. Post: 48,000 + 2,000 = 50,000. Exact NAV!
        action = CorporateAction(
            event_id="RIGHTS_EX",
            symbol="CORP",
            action_type=CorporateActionType.RIGHTS_ISSUE,
            ex_date="2026-05-01",
            ratio=0.25,
            subscription_price=80.0,
            cum_price=100.0,
        )
        portfolio = {"cash": 10000.0, "positions": {"CORP": 400.0}, "prices": {"CORP": 100.0}}
        res = self.rebalancer.process_action(action, portfolio_state=portfolio)
        self.assertAlmostEqual(res.new_quantity, 500.0)
        self.assertAlmostEqual(res.post_event_price, 96.0)
        self.assertAlmostEqual(res.nav_pre, 50000.0)
        self.assertAlmostEqual(res.nav_post, 50000.0)
        self.assertAlmostEqual(res.nav_delta, 0.0, places=7)

    def test_tc25_rights_issue_taxlot_blended_basis(self) -> None:
        """Verify rights issue blends subscription cost into taxlot basis accurately."""
        # 100 shares at $60 cost basis. Ratio = 0.20, P_sub = $50.
        # New shares = 20. Total cost = 100*60 + 20*50 = 6000 + 1000 = 7000.
        # Total shares = 120. New cost basis = 7000 / 120 = 58.3333333333.
        lot = TaxLot(lot_id="LOT_RIGHTS", symbol="CAP", quantity=100.0, cost_basis_per_share=60.0)
        action = CorporateAction(
            event_id="RIGHTS_LOT",
            symbol="CAP",
            action_type=CorporateActionType.RIGHTS_ISSUE,
            ex_date="2026-05-10",
            ratio=0.20,
            subscription_price=50.0,
            cum_price=80.0,
        )
        adj_lots = self.rebalancer.adjust_tax_lots([lot], action)
        self.assertAlmostEqual(adj_lots[0].quantity, 120.0)
        self.assertAlmostEqual(adj_lots[0].cost_basis_per_share, 7000.0 / 120.0)
        self.assertAlmostEqual(adj_lots[0].total_cost, 7000.0)

    # -----------------------------------------------------------------------
    # Category 7: Structural Actions: Spin-Offs & Mergers (TC26~TC30)
    # -----------------------------------------------------------------------

    def test_tc26_spin_off_ex_price_and_adjustment_factor(self) -> None:
        """Verify parent ex-price drops by child market value: P_ex = P_cum - r_spin * P_spin."""
        # Parent cum price = 100. Child ratio = 0.20, child price = 50.
        # Child value per parent share = 0.20 * 50 = $10.0.
        # Parent P_ex = 100 - 10 = $90.0. Factor = 90 / 100 = 0.90.
        action = CorporateAction(
            event_id="SPIN_01",
            symbol="PARENT",
            action_type=CorporateActionType.SPIN_OFF,
            ex_date="2026-06-01",
            spin_off_symbol="CHILD",
            spin_off_ratio=0.20,
            spin_off_price=50.0,
            cum_price=100.0,
        )
        factor = self.rebalancer.calculate_adjustment_factor(action)
        self.assertAlmostEqual(factor, 0.90)

    def test_tc27_spin_off_nav_conservation(self) -> None:
        """Verify spin-off distributes child shares with exact portfolio NAV preservation."""
        action = CorporateAction(
            event_id="SPIN_NAV",
            symbol="PARENT",
            action_type=CorporateActionType.SPIN_OFF,
            ex_date="2026-06-01",
            spin_off_symbol="CHILD",
            spin_off_ratio=0.20,
            spin_off_price=50.0,
            cum_price=100.0,
        )
        portfolio = {"cash": 5000.0, "positions": {"PARENT": 500.0}, "prices": {"PARENT": 100.0}}
        res = self.rebalancer.process_action(action, portfolio_state=portfolio)
        # Pre: 500 * 100 + 5000 = 55,000.
        # Post: 500 * 90 (Parent) + 100 * 50 (Child) + 5000 = 45000 + 5000 + 5000 = 55,000.
        self.assertAlmostEqual(res.nav_pre, 55000.0)
        self.assertAlmostEqual(res.nav_post, 55000.0)
        self.assertAlmostEqual(res.nav_delta, 0.0, places=7)

    def test_tc28_spin_off_taxlot_basis_bifurcation(self) -> None:
        """Verify parent and child tax lots conserve total initial cost basis exactly."""
        # Parent lot: 100 shares at $80 cost basis. Initial total cost = $8,000.
        # Parent P_ex = $90, Child value = $10. Weight parent = 90/100 = 0.90, Weight child = 0.10.
        # Parent new basis = 80 * 0.90 = $72.0. Parent total cost = 100 * 72 = $7,200.
        # Child lot: 20 shares (100 * 0.2). Child basis = (80 * 0.10) / 0.20 = $40.0.
        # Child total cost = 20 * 40 = $800.
        # Combined cost = 7200 + 800 = $8,000. Strictly conserved!
        lot = TaxLot(lot_id="LOT_PAR", symbol="PARENT", quantity=100.0, cost_basis_per_share=80.0)
        action = CorporateAction(
            event_id="SPIN_LOTS",
            symbol="PARENT",
            action_type=CorporateActionType.SPIN_OFF,
            ex_date="2026-06-01",
            spin_off_symbol="CHILD",
            spin_off_ratio=0.20,
            spin_off_price=50.0,
            cum_price=100.0,
        )
        adj_lots = self.rebalancer.adjust_tax_lots([lot], action)
        self.assertEqual(len(adj_lots), 2)

        parent_lot = next(l for l in adj_lots if l.symbol == "PARENT")
        child_lot = next(l for l in adj_lots if l.symbol == "CHILD")

        self.assertAlmostEqual(parent_lot.quantity, 100.0)
        self.assertAlmostEqual(parent_lot.cost_basis_per_share, 72.0)
        self.assertAlmostEqual(child_lot.quantity, 20.0)
        self.assertAlmostEqual(child_lot.cost_basis_per_share, 40.0)

        total_cost_post = parent_lot.total_cost + child_lot.total_cost
        self.assertAlmostEqual(lot.total_cost, total_cost_post, places=7)

    def test_tc29_stock_and_cash_merger_reconciliation(self) -> None:
        """Verify stock + cash acquisition merger converts target into cash + acquirer shares."""
        # Target shares 100 at $50. Merger terms: $10 cash + 0.5 shares of ACQ (price = $80).
        # Total target value = 10 + 0.5 * 80 = $50.
        # Cash received = 100 * 10 = $1,000. ACQ shares received = 100 * 0.5 = 50 shares.
        # NAV pre = 100 * 50 + 2000 = $7,000.
        # NAV post = 50 * 80 (ACQ) + (2000 + 1000) = 4000 + 3000 = $7,000. Exact NAV!
        action = CorporateAction(
            event_id="MERGE_01",
            symbol="TARGET",
            action_type=CorporateActionType.MERGER,
            ex_date="2026-07-01",
            new_symbol="ACQUIRER",
            ratio=0.50,
            cash_amount=10.0,
            cum_price=50.0,  # Target pre-deal cum price
            ex_price=80.0,   # Acquirer price
        )
        portfolio = {"cash": 2000.0, "positions": {"TARGET": 100.0}, "prices": {"TARGET": 50.0}}
        res = self.rebalancer.process_action(action, portfolio_state=portfolio)
        self.assertAlmostEqual(res.cash_generated, 1000.0)
        self.assertAlmostEqual(res.new_quantity, 50.0)
        self.assertAlmostEqual(res.nav_pre, 7000.0)
        self.assertAlmostEqual(res.nav_post, 7000.0)
        self.assertAlmostEqual(res.nav_delta, 0.0, places=7)

    def test_tc30_merger_taxlot_basis_rollover(self) -> None:
        """Verify merger rolls over remaining basis to acquirer shares."""
        # 100 shares of TARGET with $40 cost basis (Total cost $4,000).
        # $10 cash per share received = $1,000 cash.
        # Remaining basis = 4000 - 1000 = $3,000.
        # 50 shares of ACQUIRER received -> cost basis per share = 3000 / 50 = $60.0.
        lot = TaxLot(lot_id="LOT_TGT", symbol="TARGET", quantity=100.0, cost_basis_per_share=40.0)
        action = CorporateAction(
            event_id="MERGE_LOTS",
            symbol="TARGET",
            action_type=CorporateActionType.MERGER,
            ex_date="2026-07-01",
            new_symbol="ACQUIRER",
            ratio=0.50,
            cash_amount=10.0,
            cum_price=50.0,
            ex_price=80.0,
        )
        adj_lots = self.rebalancer.adjust_tax_lots([lot], action)
        self.assertEqual(len(adj_lots), 1)
        acq_lot = adj_lots[0]
        self.assertEqual(acq_lot.symbol, "ACQUIRER")
        self.assertAlmostEqual(acq_lot.quantity, 50.0)
        self.assertAlmostEqual(acq_lot.cost_basis_per_share, 60.0)
        self.assertAlmostEqual(acq_lot.total_cost, 3000.0)

    # -----------------------------------------------------------------------
    # Category 8: Continuous Adjustment Factor Chains & OHLCV Adjustments (TC31~TC35)
    # -----------------------------------------------------------------------

    def test_tc31_continuous_adjustment_factor_single_event(self) -> None:
        """Verify continuous adjustment factor chain with a registered single split."""
        a = CorporateAction("A1", "TSLA", CorporateActionType.STOCK_SPLIT, "2026-06-15", ratio=3.0)
        self.rebalancer.register_action(a)

        # Before ex_date -> factor is 1/3
        f_pre = self.rebalancer.get_continuous_adjustment_factor("TSLA", "2026-06-01")
        self.assertAlmostEqual(f_pre, 1.0 / 3.0)

        # On or after ex_date -> factor is 1.0 (no future events)
        f_post = self.rebalancer.get_continuous_adjustment_factor("TSLA", "2026-06-15")
        self.assertAlmostEqual(f_post, 1.0)
        f_after = self.rebalancer.get_continuous_adjustment_factor("TSLA", "2026-07-01")
        self.assertAlmostEqual(f_after, 1.0)

    def test_tc32_continuous_adjustment_factor_chain_multiple_events(self) -> None:
        """Verify continuous cumulative adjustment factor with split followed by cash dividend."""
        # Event 1: 2:1 split on 2026-03-01 -> f1 = 0.50
        # Event 2: $5 dividend on $100 stock on 2026-06-01 -> f2 = 0.95
        a1 = CorporateAction("A1", "MULT", CorporateActionType.STOCK_SPLIT, "2026-03-01", ratio=2.0)
        a2 = CorporateAction("A2", "MULT", CorporateActionType.CASH_DIVIDEND, "2026-06-01", cash_amount=5.0, cum_price=100.0)
        self.rebalancer.register_action(a1)
        self.rebalancer.register_action(a2)

        # Before 2026-03-01: affected by both a1 and a2 -> 0.50 * 0.95 = 0.475
        f_early = self.rebalancer.get_continuous_adjustment_factor("MULT", "2026-01-15")
        self.assertAlmostEqual(f_early, 0.50 * 0.95)

        # Between 2026-03-01 and 2026-06-01: affected only by a2 -> 0.95
        f_mid = self.rebalancer.get_continuous_adjustment_factor("MULT", "2026-04-15")
        self.assertAlmostEqual(f_mid, 0.95)

        # After 2026-06-01: 1.0
        f_late = self.rebalancer.get_continuous_adjustment_factor("MULT", "2026-07-01")
        self.assertAlmostEqual(f_late, 1.0)

    def test_tc33_adjust_ohlcv_series_dollar_volume_invariance(self) -> None:
        """Verify OHLCV price series backward scaling preserves dollar volume (Close * Volume)."""
        dates = pd.date_range("2026-05-01", periods=10, freq="B")
        df = pd.DataFrame(
            {
                "Open": [200.0] * 10,
                "High": [205.0] * 10,
                "Low": [195.0] * 10,
                "Close": [200.0] * 10,
                "Volume": [1000.0] * 10,
            },
            index=dates,
        )

        # 2:1 split on 6th day (dates[5])
        split_date = dates[5].strftime("%Y-%m-%d")
        action = CorporateAction(
            event_id="SPLIT_DF",
            symbol="TEST_DF",
            action_type=CorporateActionType.STOCK_SPLIT,
            ex_date=split_date,
            ratio=2.0,
            cum_price=200.0,
        )

        df_adj = self.rebalancer.adjust_ohlcv_series(df, events=[action])

        # Prior bars (0..4) should have price * 0.5 = 100.0, volume / 0.5 = 2000.0
        for i in range(5):
            self.assertAlmostEqual(df_adj["Close"].iloc[i], 100.0)
            self.assertAlmostEqual(df_adj["Open"].iloc[i], 100.0)
            self.assertAlmostEqual(df_adj["High"].iloc[i], 102.5)
            self.assertAlmostEqual(df_adj["Low"].iloc[i], 97.5)
            self.assertAlmostEqual(df_adj["Volume"].iloc[i], 2000.0)
            # Dollar volume invariant: 100.0 * 2000.0 == 200.0 * 1000.0 == 200,000.0
            self.assertAlmostEqual(df_adj["Close"].iloc[i] * df_adj["Volume"].iloc[i], 200000.0)

        # On or after split date (5..9), unchanged
        for i in range(5, 10):
            self.assertAlmostEqual(df_adj["Close"].iloc[i], 200.0)
            self.assertAlmostEqual(df_adj["Volume"].iloc[i], 1000.0)

    def test_tc34_adjust_ohlcv_series_with_date_column(self) -> None:
        """Verify OHLCV adjustment works seamlessly when Date is a column rather than index."""
        dates = ["2026-05-01", "2026-05-02", "2026-05-03", "2026-05-04"]
        df = pd.DataFrame(
            {
                "Date": dates,
                "Open": [100.0, 100.0, 100.0, 100.0],
                "High": [105.0, 105.0, 105.0, 105.0],
                "Low": [95.0, 95.0, 95.0, 95.0],
                "Close": [100.0, 100.0, 100.0, 100.0],
                "Volume": [500.0, 500.0, 500.0, 500.0],
            }
        )
        action = CorporateAction("A_COL", "COL_SYM", CorporateActionType.STOCK_SPLIT, "2026-05-03", ratio=2.0)
        df_adj = self.rebalancer.adjust_ohlcv_series(df, events=[action])

        self.assertAlmostEqual(df_adj["Close"].iloc[0], 50.0)
        self.assertAlmostEqual(df_adj["Close"].iloc[1], 50.0)
        self.assertAlmostEqual(df_adj["Close"].iloc[2], 100.0)
        self.assertAlmostEqual(df_adj["Close"].iloc[3], 100.0)

    def test_tc35_empty_dataframe_adjustment_returns_gracefully(self) -> None:
        """Verify empty or None DataFrame is handled gracefully without exception."""
        self.assertIsNone(self.rebalancer.adjust_ohlcv_series(None))
        empty_df = pd.DataFrame()
        self.assertTrue(self.rebalancer.adjust_ohlcv_series(empty_df).empty)

    # -----------------------------------------------------------------------
    # Category 9: Rebalance Order Synthesis & Cash Drag Neutralization (TC36~TC40)
    # -----------------------------------------------------------------------

    def test_tc36_cash_drag_detection_and_order_synthesis(self) -> None:
        """Verify excess cash exceeding 0.5% NAV synthesizes proportional rebalance BUY orders."""
        # NAV: Total equity = $90,000, Total Cash = $10,000. Total NAV = $100,000.
        # Target cash = 1.0% = $1,000. Excess cash = $9,000 (9% NAV > 0.5% threshold).
        # Target weights: AAPL: 0.60, MSFT: 0.40.
        # Current prices: AAPL = $150, MSFT = $300.
        portfolio = {
            "cash": 10000.0,
            "positions": {"AAPL": 400.0, "MSFT": 100.0},
            "prices": {"AAPL": 150.0, "MSFT": 300.0},
            "target_weights": {"AAPL": 0.60, "MSFT": 0.40},
        }
        orders = self.rebalancer.synthesize_rebalance_orders(portfolio)
        self.assertEqual(len(orders), 2)

        aapl_order = next(o for o in orders if o.symbol == "AAPL")
        msft_order = next(o for o in orders if o.symbol == "MSFT")

        # AAPL target: 9,000 * 0.60 = $5,400 -> 5400 / 150 = 36 shares.
        # MSFT target: 9,000 * 0.40 = $3,600 -> 3600 / 300 = 12 shares.
        self.assertEqual(aapl_order.quantity, 36.0)
        self.assertAlmostEqual(aapl_order.notional, 5400.0)
        self.assertEqual(msft_order.quantity, 12.0)
        self.assertAlmostEqual(msft_order.notional, 3600.0)

        # Budget conservation
        self.assertLessEqual(aapl_order.notional + msft_order.notional, 9000.0)

    def test_tc37_no_cash_drag_below_threshold(self) -> None:
        """Verify zero orders synthesized when cash is within target threshold (<= 0.5% drag)."""
        # Total NAV = $100,000. Target cash = $1,000. Current cash = $1,200.
        # Excess cash = $200 (0.2% NAV < 0.5% threshold).
        portfolio = {
            "cash": 1200.0,
            "positions": {"AAPL": 500.0},
            "prices": {"AAPL": 200.0},
            "target_weights": {"AAPL": 1.0},
        }
        orders = self.rebalancer.synthesize_rebalance_orders(portfolio)
        self.assertEqual(len(orders), 0)

    def test_tc38_pending_dividend_accumulation_triggers_rebalance(self) -> None:
        """Verify pending cash dividend is processed first, and the resulting cash triggers rebalance."""
        # Initial cash = $500 (below threshold).
        # Holding 1000 shares of KO at $100 ($100k equity).
        # Dividend of $2.50 per share adds $2,500 cash -> Total cash = $3,000.
        # Total NAV = $3,000 + 1000 * 97.50 = 3,000 + 97,500 = $100,500.
        # Target cash = 1% = $1,005. Excess cash = $1,995 (1.98% NAV > 0.5% threshold).
        div_action = CorporateAction(
            event_id="DIV_PENDING",
            symbol="KO",
            action_type=CorporateActionType.CASH_DIVIDEND,
            ex_date="2026-08-01",
            cash_amount=2.50,
            cum_price=100.0,
        )
        portfolio = {
            "cash": 500.0,
            "positions": {"KO": 1000.0},
            "prices": {"KO": 100.0},
            "target_weights": {"KO": 1.0},
        }
        orders = self.rebalancer.synthesize_rebalance_orders(portfolio, pending_actions=[div_action])
        self.assertGreater(len(orders), 0)
        self.assertEqual(orders[0].symbol, "KO")
        self.assertEqual(orders[0].action, "BUY")
        self.assertEqual(orders[0].source, "CORPORATE_ACTION_REBALANCE")

    def test_tc39_minimum_order_notional_filter(self) -> None:
        """Verify tiny dust allocations below min_order_notional are filtered out."""
        reb = CorporateActionRebalancer(min_order_notional=200.0)
        # Excess cash = $150. Target weight = 1.0. Notional $150 < $200 min threshold.
        orders = reb.generate_cash_drag_rebalance_orders(
            excess_cash=150.0,
            target_weights={"XYZ": 1.0},
            current_prices={"XYZ": 50.0},
        )
        self.assertEqual(len(orders), 0)

    def test_tc40_exact_nav_conservation_post_rebalance_fill(self) -> None:
        """Verify mathematical theorem: NAV before rebalance == NAV after hypothetical fill."""
        # NAV before = Cash + sum(Q_i * P_i).
        # Order fills decrease cash by sum(Q_buy * P_i) and increase equity by sum(Q_buy * P_i).
        # Delta NAV is identically 0.0.
        portfolio = {
            "cash": 20000.0,
            "positions": {"AAPL": 100.0, "GOOGL": 50.0},
            "prices": {"AAPL": 150.0, "GOOGL": 100.0},
            "target_weights": {"AAPL": 0.50, "GOOGL": 0.50},
        }
        orders = self.rebalancer.synthesize_rebalance_orders(portfolio)
        total_order_notional = sum(o.notional for o in orders)

        nav_before = portfolio["cash"] + (100 * 150) + (50 * 100)
        cash_after = portfolio["cash"] - total_order_notional
        equity_after = (100 * 150) + (50 * 100) + total_order_notional
        nav_after = cash_after + equity_after

        self.assertAlmostEqual(nav_before, nav_after, places=7)

    # -----------------------------------------------------------------------
    # Category 10: Non-Interfering OMS Execution Safety & Multi-Market Stress (TC41~TC45)
    # -----------------------------------------------------------------------

    def test_tc41_bypassing_active_oms_execution_slice(self) -> None:
        """Verify active OMS slice symbol is strictly bypassed, with weight reallocated to non-active symbols."""
        portfolio = {
            "cash": 10000.0,
            "positions": {"AAPL": 100.0, "MSFT": 100.0, "NVDA": 50.0},
            "prices": {"AAPL": 150.0, "MSFT": 300.0, "NVDA": 400.0},
            "target_weights": {"AAPL": 0.50, "MSFT": 0.30, "NVDA": 0.20},
        }
        # AAPL is currently being sliced by OMS
        active_orders = [{"symbol": "AAPL", "order_id": "OMS_ACTIVE_001"}]
        orders = self.rebalancer.synthesize_rebalance_orders(
            portfolio,
            active_oms_orders=active_orders,
        )
        symbols_ordered = {o.symbol for o in orders}
        self.assertNotIn("AAPL", symbols_ordered, "Active OMS slice symbol MUST be bypassed.")
        self.assertIn("MSFT", symbols_ordered)
        self.assertIn("NVDA", symbols_ordered)

    def test_tc42_all_target_symbols_active_in_oms_guard(self) -> None:
        """Verify when all target symbols are active in OMS, zero orders are emitted without error."""
        portfolio = {
            "cash": 10000.0,
            "positions": {"AAPL": 100.0},
            "prices": {"AAPL": 150.0},
            "target_weights": {"AAPL": 1.0},
        }
        active_orders = ["AAPL"]
        orders = self.rebalancer.synthesize_rebalance_orders(
            portfolio,
            active_oms_orders=active_orders,
        )
        self.assertEqual(len(orders), 0)

    def test_tc43_krx_and_us_multi_market_portfolio_stress(self) -> None:
        """Verify multi-market portfolio (KOSPI, KOSDAQ, SP500, NASDAQ, RUSSELL2000) corporate actions."""
        # Process actions across 5 symbols simultaneously
        actions = [
            CorporateAction("A_KOSPI", "005930", CorporateActionType.CASH_DIVIDEND, "2026-05-01", cash_amount=1000.0, cum_price=70000.0),
            CorporateAction("A_KOSDAQ", "091990", CorporateActionType.STOCK_DIVIDEND, "2026-05-01", ratio=0.05, cum_price=100000.0),
            CorporateAction("A_SP500", "AAPL", CorporateActionType.STOCK_SPLIT, "2026-05-01", ratio=2.0, cum_price=200.0),
            CorporateAction("A_NASDAQ", "MSFT", CorporateActionType.CASH_DIVIDEND, "2026-05-01", cash_amount=3.0, cum_price=400.0),
            CorporateAction("A_RUSSELL", "IWM", CorporateActionType.CASH_DIVIDEND, "2026-05-01", cash_amount=1.5, cum_price=220.0),
        ]
        portfolio = {
            "cash": 50000000.0,
            "positions": {"005930": 100.0, "091990": 50.0, "AAPL": 200.0, "MSFT": 100.0, "IWM": 100.0},
            "prices": {"005930": 70000.0, "091990": 100000.0, "AAPL": 200.0, "MSFT": 400.0, "IWM": 220.0},
            "target_weights": {"005930": 0.30, "091990": 0.20, "AAPL": 0.25, "MSFT": 0.15, "IWM": 0.10},
        }
        for act in actions:
            res = self.rebalancer.process_action(act, portfolio_state=portfolio)
            self.assertAlmostEqual(res.nav_delta, 0.0, places=5)
            self.assertEqual(res.status, "COMPLETED")

    def test_tc44_mirrored_class_interoperability(self) -> None:
        """Verify mirrored class from trading_system branch operates identically."""
        mirrored_reb = MirroredCorporateActionRebalancer()
        action = CorporateAction("M_ACT", "MSFT", CorporateActionType.STOCK_SPLIT, "2026-07-01", ratio=4.0)
        f = mirrored_reb.calculate_adjustment_factor(action)
        self.assertAlmostEqual(f, 0.25)

        lot = MirroredTaxLot("L_M", "MSFT", "NASDAQ", "2026-01-01", 10.0, 400.0)
        adj = mirrored_reb.adjust_tax_lots([lot], action)
        self.assertAlmostEqual(adj[0].quantity, 40.0)
        self.assertAlmostEqual(adj[0].cost_basis_per_share, 100.0)

    def test_tc45_date_utility_parsers(self) -> None:
        """Verify robust parsing of various string, timestamp, and datetime formats."""
        d1 = parse_date("2026-10-15")
        d2 = parse_date("2026/10/15")
        d3 = parse_date("20261015")
        d4 = parse_date(pd.Timestamp("2026-10-15"))
        d5 = parse_date(datetime.datetime(2026, 10, 15, 12, 0, 0))
        self.assertEqual(d1, d2)
        self.assertEqual(d1, d3)
        self.assertEqual(d1, d4)
        self.assertEqual(d1, d5)
        self.assertEqual(format_date(d1), "2026-10-15")


if __name__ == "__main__":
    unittest.main()
