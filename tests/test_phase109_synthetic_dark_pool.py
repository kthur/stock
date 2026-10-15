"""
tests/test_phase109_synthetic_dark_pool.py
==========================================
Comprehensive Unit, Integration, Invariant, and Stress Test Harness for
Synthetic Dark Pool Cross-Asset Matching Engine & Internal Crossing Network
Phase 109 (Release R125 / v116 Production Master / Feature F518).

Test Categories Covered:
- Category 1: Class Exports, Signatures & Full Alias Trees (TC01~TC04)
- Category 2: Dual Placement Mirror SHA-256 Hash Integrity (TC05)
- Category 3: Volume-Weighted Midpoint Pricing & Tick Conformity across 5 Markets (TC06~TC10)
- Category 4: Anti-Gaming Guardrails & MFI Minimum Fill Enforcement (TC11~TC15)
- Category 5: Confidential Queue Priority (Size-Time, FIFO, Price-Time) & Zero Display (TC16~TC19)
- Category 6: Exact Institutional Cost Savings Quantification (Half-Spread & Zero Fees) (TC20~TC24)
- Category 7: Strict Volume Conservation Invariant & Residual Forwarding to SOR (TC25~TC29)
- Category 8: Locked/Crossed Markets, Spread Collars & Edge Case Handlers (TC30~TC34)
- Category 9: Multi-Strategy Batch Crossing across Global Portfolios (TC35~TC38)
- Category 10: Order Lifecycle, Cancellation, Wash-Sale Guard & Telemetry (TC39~TC42)
"""

from __future__ import annotations

import hashlib
import math
import sys
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure project roots are on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p in (str(PROJECT_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.broker.synthetic_dark_pool import (
    CrossAssetDarkPoolEngine,
    DarkCrossExecution,
    DarkLiquidityCrossEngine,
    DarkPoolExecution,
    DarkPoolMatchResult,
    DarkPoolOrder,
    DarkPoolOrderStatus,
    DarkPoolSavingsReport,
    DarkPoolSide,
    ExecutionOrder,
    InternalCrossingNetwork,
    InternalDarkPoolMatchingEngine,
    InternalOrder,
    Phase109SyntheticDarkPool,
    QueuePriorityMode,
    ResidualOrderPlan,
    SyntheticDarkPool,
    SyntheticDarkPoolCrossAssetEngine,
    SyntheticDarkPoolEngine,
    round_to_tick_size,
)
from trading_system.src.broker.synthetic_dark_pool import (
    SyntheticDarkPool as MirroredSyntheticDarkPool,
    SyntheticDarkPoolEngine as MirroredSyntheticDarkPoolEngine,
)


class MockSmartOrderRouter:
    """Mock SmartOrderRouter to verify seamless residual forwarding integration."""
    def __init__(self) -> None:
        self.routed_orders: List[Dict[str, Any]] = []

    def route_order(self, order_dict: Dict[str, Any]) -> Dict[str, Any]:
        result = {
            "order_id": order_dict["order_id"],
            "symbol": order_dict["symbol"],
            "routed_venue": "LIT_EXCHANGE_SWEEPER",
            "quantity": order_dict["quantity"],
            "legs": [
                {
                    "venue_type": "LIT_EXCHANGE_SWEEPER",
                    "order_type": "LIMIT_IOC",
                    "quantity": order_dict["quantity"],
                    "target_price": order_dict.get("price_limit"),
                }
            ],
            "routing_status": "DISPATCHED",
        }
        self.routed_orders.append(result)
        return result


class TestPhase109SyntheticDarkPool(unittest.TestCase):
    """Master Test Suite for Synthetic Dark Pool Cross-Asset Matching Engine."""

    def setUp(self) -> None:
        self.engine = SyntheticDarkPool(
            min_fill_ratio=0.20,
            default_min_fill_size=10,
            max_spread_bps_collar=200.0,
            taker_fee_bps=1.5,
            clearing_fee_bps=0.5,
            enable_anti_gaming=True,
            enable_tick_conformity=True,
            wash_sale_guard=False,
            queue_priority_mode=QueuePriorityMode.SIZE_TIME,
        )

    # -----------------------------------------------------------------------
    # Category 1: Class Exports, Signatures & Full Alias Trees (TC01~TC04)
    # -----------------------------------------------------------------------

    def test_tc01_class_exports_and_aliases(self) -> None:
        """Verify that all core classes and backward-compatible alias trees are properly exported."""
        self.assertIs(SyntheticDarkPoolEngine, SyntheticDarkPool)
        self.assertIs(InternalCrossingNetwork, SyntheticDarkPool)
        self.assertIs(SyntheticDarkPoolCrossAssetEngine, SyntheticDarkPool)
        self.assertIs(InternalDarkPoolMatchingEngine, SyntheticDarkPool)
        self.assertIs(CrossAssetDarkPoolEngine, SyntheticDarkPool)
        self.assertIs(DarkLiquidityCrossEngine, SyntheticDarkPool)
        self.assertIs(Phase109SyntheticDarkPool, SyntheticDarkPool)

        self.assertIs(InternalOrder, DarkPoolOrder)
        self.assertIs(DarkPoolExecution, DarkCrossExecution)
        self.assertIs(ExecutionOrder, ResidualOrderPlan)

    def test_tc02_mirrored_import_parity(self) -> None:
        """Verify mirrored package imports match primary package definitions."""
        self.assertEqual(SyntheticDarkPool.__name__, MirroredSyntheticDarkPool.__name__)
        self.assertEqual(SyntheticDarkPoolEngine.__name__, MirroredSyntheticDarkPoolEngine.__name__)
        s1 = SyntheticDarkPool()
        s2 = MirroredSyntheticDarkPool()
        self.assertEqual(s1.min_fill_ratio, s2.min_fill_ratio)
        self.assertEqual(s1.taker_fee_bps, s2.taker_fee_bps)
        self.assertEqual(s1.max_spread_bps_collar, s2.max_spread_bps_collar)

    def test_tc03_order_dataclass_initialization(self) -> None:
        """Verify DarkPoolOrder initialization, validation, and auto-population."""
        order = DarkPoolOrder(
            order_id="ord_101",
            symbol="aapl",
            side="buy",
            quantity=500,
            market="nasdaq",
            price_limit=180.50,
            min_fill_size=50,
        )
        self.assertEqual(order.symbol, "AAPL")
        self.assertEqual(order.side, "BUY")
        self.assertEqual(order.market, "NASDAQ")
        self.assertEqual(order.quantity, 500)
        self.assertEqual(order.remaining_quantity, 500)
        self.assertEqual(order.filled_quantity, 0)
        self.assertEqual(order.status, DarkPoolOrderStatus.PENDING.value)
        self.assertTrue(order.is_active)

    def test_tc04_order_invalid_side_or_qty_raises(self) -> None:
        """Verify that invalid side or non-positive quantity raises ValueError."""
        with self.assertRaises(ValueError):
            DarkPoolOrder(order_id="bad_1", symbol="NVDA", side="HOLD", quantity=100)
        with self.assertRaises(ValueError):
            DarkPoolOrder(order_id="bad_2", symbol="NVDA", side="BUY", quantity=0)
        with self.assertRaises(ValueError):
            DarkPoolOrder(order_id="bad_3", symbol="NVDA", side="BUY", quantity=-50)

    # -----------------------------------------------------------------------
    # Category 2: Dual Placement Mirror SHA-256 Hash Integrity (TC05)
    # -----------------------------------------------------------------------

    def test_tc05_mirrored_file_sha256_equality(self) -> None:
        """Verify bit-for-bit SHA-256 synchronization between src/ and trading_system/src/."""
        p1 = PROJECT_ROOT / "src" / "broker" / "synthetic_dark_pool.py"
        p2 = TRADING_SYSTEM_DIR / "src" / "broker" / "synthetic_dark_pool.py"

        self.assertTrue(p1.exists(), f"Primary file missing: {p1}")
        self.assertTrue(p2.exists(), f"Mirrored file missing: {p2}")

        h1 = hashlib.sha256(p1.read_bytes()).hexdigest()
        h2 = hashlib.sha256(p2.read_bytes()).hexdigest()
        self.assertEqual(h1, h2, "Dual placement files must be 100% bit-for-bit SHA-256 identical.")
        self.assertGreater(len(h1), 0)

    # -----------------------------------------------------------------------
    # Category 3: Midpoint Pricing & Tick Conformity across 5 Markets (TC06~TC10)
    # -----------------------------------------------------------------------

    def test_tc06_midpoint_calculation_us_market(self) -> None:
        """Verify volume-weighted midpoint price calculation on US markets (SP500, NASDAQ, RUSSELL2000)."""
        bid = 150.10
        ask = 150.30
        expected_mid = 150.20
        self.engine.add_order("b1", "AAPL", "SP500", "BUY", 100)
        self.engine.add_order("s1", "AAPL", "SP500", "SELL", 100)

        execs, residuals = self.engine.match_orders("AAPL", bid, ask, "SP500")
        self.assertEqual(len(execs), 1)
        self.assertAlmostEqual(execs[0].midpoint_price, expected_mid, places=4)
        self.assertEqual(execs[0].matched_quantity, 100)

    def test_tc07_tick_conformity_kospi_ladder(self) -> None:
        """Verify KRX tick conformity rounding across the Won ladder."""
        # 1. Under 2,000 KRW: tick = 1 KRW
        self.assertEqual(round_to_tick_size(1542.4, "KOSPI"), 1542.0)
        # 2. 2,000 ~ 5,000 KRW: tick = 5 KRW
        self.assertEqual(round_to_tick_size(3452.3, "KOSPI"), 3450.0)
        self.assertEqual(round_to_tick_size(3453.0, "KOSPI"), 3455.0)
        # 3. 5,000 ~ 20,000 KRW: tick = 10 KRW
        self.assertEqual(round_to_tick_size(12344.0, "KOSPI"), 12340.0)
        # 4. 20,000 ~ 50,000 KRW: tick = 50 KRW
        self.assertEqual(round_to_tick_size(35422.0, "KOSPI"), 35400.0)
        # 5. 50,000 ~ 200,000 KRW: tick = 100 KRW (e.g. Samsung Elec at ~70,000)
        self.assertEqual(round_to_tick_size(71260.0, "KOSPI"), 71300.0)
        # 6. 200,000 ~ 500,000 KRW: tick = 500 KRW
        self.assertEqual(round_to_tick_size(345200.0, "KOSPI"), 345000.0)
        # 7. >= 500,000 KRW: tick = 1,000 KRW
        self.assertEqual(round_to_tick_size(684400.0, "KOSPI"), 684000.0)

    def test_tc08_tick_conformity_kosdaq_matching(self) -> None:
        """Verify dark midpoint matching for KOSDAQ stocks with tick ladder."""
        self.engine.add_order("k_b1", "068270", "KOSDAQ", "BUY", 200)
        self.engine.add_order("k_s1", "068270", "KOSDAQ", "SELL", 200)

        # Midpoint of 70,500 and 70,700 is 70,600 (tick is 100 KRW)
        execs, residuals = self.engine.match_orders("068270", 70500.0, 70700.0, "KOSDAQ")
        self.assertEqual(len(execs), 1)
        self.assertEqual(execs[0].midpoint_price, 70600.0)
        self.assertEqual(execs[0].matched_quantity, 200)

    def test_tc09_sub_penny_us_midpoint_accuracy(self) -> None:
        """Verify sub-penny midpoint pricing for US stocks with 1-cent lit spread."""
        # Bid = 100.00, Ask = 100.01 -> Mid = 100.005
        self.engine.add_order("us_b1", "MSFT", "NASDAQ", "BUY", 300)
        self.engine.add_order("us_s1", "MSFT", "NASDAQ", "SELL", 300)

        execs, _ = self.engine.match_orders("MSFT", 100.00, 100.01, "NASDAQ")
        self.assertEqual(len(execs), 1)
        self.assertAlmostEqual(execs[0].midpoint_price, 100.005, places=4)

    def test_tc10_midpoint_bounded_within_lit_spread(self) -> None:
        """Verify invariant that executed dark midpoint is strictly bounded: bid <= p_mid <= ask."""
        for bid, ask in [(10.0, 10.05), (99.9, 100.1), (50000.0, 50200.0)]:
            self.engine.reset()
            self.engine.add_order("b", "SYM", "SP500", "BUY", 100)
            self.engine.add_order("s", "SYM", "SP500", "SELL", 100)
            execs, _ = self.engine.match_orders("SYM", bid, ask, "SP500")
            self.assertTrue(len(execs) > 0)
            self.assertGreaterEqual(execs[0].midpoint_price, bid)
            self.assertLessEqual(execs[0].midpoint_price, ask)

    # -----------------------------------------------------------------------
    # Category 4: Anti-Gaming Guardrails & MFI Minimum Fill Enforcement (TC11~TC15)
    # -----------------------------------------------------------------------

    def test_tc11_predatory_ping_suppressed_by_mfi(self) -> None:
        """Verify that a 1-share predatory probe is blocked when institutional order has MFI > 1."""
        # Institutional block order: 5,000 shares with MFI = 500
        self.engine.add_order("inst_buy", "TSLA", "NASDAQ", "BUY", 5000, min_fill_size=500)
        # Predatory HFT probe: 1 share
        self.engine.add_order("hft_ping", "TSLA", "NASDAQ", "SELL", 1, min_fill_size=1)

        execs, residuals = self.engine.match_orders("TSLA", 200.00, 200.20, "NASDAQ")
        # Match MUST be rejected to prevent sniffing institutional liquidity
        self.assertEqual(len(execs), 0, "Predatory 1-share ping must not match against block MFI.")
        # Both orders must remain active and unrevealed
        active = self.engine.get_active_orders("TSLA")
        self.assertEqual(len(active), 2)
        inst_ord = self.engine.get_order("inst_buy")
        self.assertIsNotNone(inst_ord)
        self.assertEqual(inst_ord.filled_quantity, 0)
        self.assertEqual(inst_ord.remaining_quantity, 5000)

    def test_tc12_dynamic_min_fill_ratio_enforcement(self) -> None:
        """Verify dynamic MFI based on min_fill_ratio (20% of 1,000 shares = 200 shares)."""
        # Order 1: 1,000 shares. Dynamic MFI = 200
        self.engine.add_order("ord_block", "AMD", "NASDAQ", "BUY", 1000)
        # Order 2: 150 shares (below 200 shares dynamic threshold)
        self.engine.add_order("ord_small", "AMD", "NASDAQ", "SELL", 150)

        execs, residuals = self.engine.match_orders("AMD", 120.0, 120.5, "NASDAQ")
        self.assertEqual(len(execs), 0, "Candidate volume below 20% MFI must be suppressed.")

    def test_tc13_sufficient_counterparty_satisfies_mfi(self) -> None:
        """Verify that when counterparty volume meets or exceeds MFI, trade executes smoothly."""
        self.engine.add_order("b_inst", "GOOGL", "NASDAQ", "BUY", 1000, min_fill_size=200)
        self.engine.add_order("s_inst", "GOOGL", "NASDAQ", "SELL", 400, min_fill_size=200)

        execs, _ = self.engine.match_orders("GOOGL", 140.0, 140.2, "NASDAQ")
        self.assertEqual(len(execs), 1)
        self.assertEqual(execs[0].matched_quantity, 400)
        self.assertEqual(self.engine.get_order("b_inst").filled_quantity, 400)
        self.assertEqual(self.engine.get_order("b_inst").remaining_quantity, 600)
        self.assertEqual(self.engine.get_order("s_inst").status, DarkPoolOrderStatus.FILLED.value)

    def test_tc14_anti_gaming_disabled_allows_small_fills(self) -> None:
        """Verify that when anti-gaming is explicitly disabled, smaller fills execute."""
        engine_no_ag = SyntheticDarkPool(enable_anti_gaming=False, default_min_fill_size=1)
        engine_no_ag.add_order("b", "AAPL", "SP500", "BUY", 1000)
        engine_no_ag.add_order("s", "AAPL", "SP500", "SELL", 5)

        execs, _ = engine_no_ag.match_orders("AAPL", 150.0, 150.1, "SP500")
        self.assertEqual(len(execs), 1)
        self.assertEqual(execs[0].matched_quantity, 5)

    def test_tc15_bidirectional_mfi_protection(self) -> None:
        """Verify that MFI protects both Buyer and Seller independently."""
        # Buyer allows 50 shares minimum, but Seller demands 300 shares minimum
        self.engine.add_order("b", "META", "NASDAQ", "BUY", 200, min_fill_size=50)
        self.engine.add_order("s", "META", "NASDAQ", "SELL", 500, min_fill_size=300)

        execs, _ = self.engine.match_orders("META", 300.0, 300.5, "NASDAQ")
        # Candidate is 200, but seller requires 300 -> MUST NOT MATCH
        self.assertEqual(len(execs), 0)

    # -----------------------------------------------------------------------
    # Category 5: Confidential Queue Priority & Zero Display (TC16~TC19)
    # -----------------------------------------------------------------------

    def test_tc16_size_time_priority_matching(self) -> None:
        """Verify SIZE_TIME priority matches largest block size first."""
        engine_st = SyntheticDarkPool(
            queue_priority_mode=QueuePriorityMode.SIZE_TIME,
            enable_anti_gaming=False,
        )
        # Sell side: 500 shares available
        engine_st.add_order("s1", "AMZN", "NASDAQ", "SELL", 500)

        # Buy side: Small order arrived earlier, large order arrived later
        engine_st.add_order("b_small", "AMZN", "NASDAQ", "BUY", 100)
        engine_st.add_order("b_large", "AMZN", "NASDAQ", "BUY", 400)

        execs, _ = engine_st.match_orders("AMZN", 175.0, 175.2, "NASDAQ")
        # Under SIZE_TIME, b_large must match first
        self.assertEqual(len(execs), 2)
        self.assertEqual(execs[0].buy_order_id, "b_large")
        self.assertEqual(execs[0].matched_quantity, 400)
        self.assertEqual(execs[1].buy_order_id, "b_small")
        self.assertEqual(execs[1].matched_quantity, 100)

    def test_tc17_fifo_time_priority_matching(self) -> None:
        """Verify TIME (FIFO) priority matches earliest timestamp first."""
        engine_fifo = SyntheticDarkPool(
            queue_priority_mode=QueuePriorityMode.TIME,
            enable_anti_gaming=False,
        )
        engine_fifo.add_order("s1", "AMZN", "NASDAQ", "SELL", 300)
        engine_fifo.add_order("b_first", "AMZN", "NASDAQ", "BUY", 200)
        engine_fifo.add_order("b_second", "AMZN", "NASDAQ", "BUY", 500)

        execs, _ = engine_fifo.match_orders("AMZN", 175.0, 175.2, "NASDAQ")
        self.assertEqual(execs[0].buy_order_id, "b_first")
        self.assertEqual(execs[0].matched_quantity, 200)

    def test_tc18_price_time_priority_respects_limits(self) -> None:
        """Verify PRICE_TIME priority matches most aggressive limit price first."""
        engine_pt = SyntheticDarkPool(
            queue_priority_mode=QueuePriorityMode.PRICE_TIME,
            enable_anti_gaming=False,
        )
        engine_pt.add_order("s1", "NFLX", "NASDAQ", "SELL", 100)

        # b_passive willing to pay up to 600.10, b_aggress willing to pay up to 600.25
        engine_pt.add_order("b_passive", "NFLX", "NASDAQ", "BUY", 100, price_limit=600.10)
        engine_pt.add_order("b_aggress", "NFLX", "NASDAQ", "BUY", 100, price_limit=600.25)

        # Midpoint is 600.05
        execs, _ = engine_pt.match_orders("NFLX", 600.00, 600.10, "NASDAQ")
        self.assertEqual(len(execs), 1)
        self.assertEqual(execs[0].buy_order_id, "b_aggress")

    def test_tc19_zero_quote_display_guarantee(self) -> None:
        """Verify that resting orders are never exposed via public orderbook dictionaries."""
        self.engine.add_order("conf_1", "SPY", "SP500", "BUY", 10000)
        stats = self.engine.get_stats()
        # Telemetry provides counts and volume, never open price ladders or active quotes
        self.assertNotIn("bids", stats)
        self.assertNotIn("asks", stats)
        self.assertNotIn("orderbook", stats)
        self.assertEqual(stats["active_orders"], 1)

    # -----------------------------------------------------------------------
    # Category 6: Institutional Cost Savings Quantification (TC20~TC24)
    # -----------------------------------------------------------------------

    def test_tc20_exact_half_spread_capture(self) -> None:
        """Verify exact half-spread savings calculation: 0.5 * (ask - bid) * shares."""
        # Lit bid = 100.0, ask = 101.0. Spread = 1.0. Midpoint = 100.5.
        # Matched shares = 200.
        self.engine.add_order("b", "TEST", "SP500", "BUY", 200, min_fill_size=50)
        self.engine.add_order("s", "TEST", "SP500", "SELL", 200, min_fill_size=50)

        execs, _ = self.engine.match_orders("TEST", 100.0, 101.0, "SP500")
        self.assertEqual(len(execs), 1)
        e = execs[0]

        # Buyer saved: (101.0 - 100.5) * 200 = 100.0
        self.assertAlmostEqual(e.buyer_spread_savings_value, 100.0, places=6)
        # Seller saved: (100.5 - 100.0) * 200 = 100.0
        self.assertAlmostEqual(e.seller_spread_savings_value, 100.0, places=6)
        # Total spread savings = 200.0
        self.assertAlmostEqual(e.spread_savings_value, 200.0, places=6)

        # Spread savings bps: (0.5 / 100.5) * 10,000 = 49.7512 bps
        expected_bps = (0.5 / 100.5) * 10000.0
        self.assertAlmostEqual(e.spread_savings_bps, expected_bps, places=4)

    def test_tc21_zero_exchange_and_clearing_fee_savings(self) -> None:
        """Verify quantification of avoided lit exchange taker and clearing fees."""
        # taker_fee_bps = 1.5, clearing_fee_bps = 0.5. Total = 2.0 bps per side.
        # For 2 sides (buy and sell), total avoided rate = 4.0 bps = 0.0004
        # Midpoint = 100.0, shares = 1,000. Notional = 100,000.
        # Fee savings = 0.0004 * 100,000 = $40.00
        engine = SyntheticDarkPool(taker_fee_bps=1.5, clearing_fee_bps=0.5, enable_anti_gaming=False)
        engine.add_order("b", "XOM", "SP500", "BUY", 1000)
        engine.add_order("s", "XOM", "SP500", "SELL", 1000)

        execs, _ = engine.match_orders("XOM", 99.9, 100.1, "SP500")
        self.assertEqual(len(execs), 1)
        e = execs[0]
        self.assertAlmostEqual(e.fee_savings_value, 40.0, places=4)
        self.assertAlmostEqual(e.total_savings_value, e.spread_savings_value + 40.0, places=4)

    def test_tc22_institutional_savings_report_aggregation(self) -> None:
        """Verify cumulative DarkPoolSavingsReport aggregation across multiple trades."""
        self.engine.add_order("b1", "AAPL", "SP500", "BUY", 100, client_id="STRAT_ALPHA")
        self.engine.add_order("s1", "AAPL", "SP500", "SELL", 100, client_id="STRAT_BETA")
        self.engine.match_orders("AAPL", 150.0, 150.2, "SP500")

        self.engine.add_order("b2", "MSFT", "NASDAQ", "BUY", 200, client_id="STRAT_ALPHA")
        self.engine.add_order("s2", "MSFT", "NASDAQ", "SELL", 200, client_id="STRAT_GAMMA")
        self.engine.match_orders("MSFT", 300.0, 300.4, "NASDAQ")

        report = self.engine.calculate_institutional_savings()
        self.assertIsInstance(report, DarkPoolSavingsReport)
        self.assertEqual(report.total_matched_volume, 300)
        self.assertEqual(report.execution_count, 2)
        self.assertGreater(report.total_spread_savings_value, 0.0)
        self.assertGreater(report.total_fee_savings_value, 0.0)
        self.assertGreater(report.total_institutional_savings, 0.0)

        # Check breakdown by symbol
        self.assertIn("AAPL", report.by_symbol)
        self.assertIn("MSFT", report.by_symbol)
        self.assertEqual(report.by_symbol["AAPL"]["matched_volume"], 100)
        self.assertEqual(report.by_symbol["MSFT"]["matched_volume"], 200)

        # Check breakdown by strategy client
        self.assertIn("STRAT_ALPHA", report.by_client)
        self.assertIn("STRAT_BETA", report.by_client)
        self.assertIn("STRAT_GAMMA", report.by_client)

    def test_tc23_zero_market_impact_benefit(self) -> None:
        """Verify dark crossing executes internally with zero lit orderbook sweeping."""
        self.engine.add_order("b", "NVDA", "NASDAQ", "BUY", 500)
        self.engine.add_order("s", "NVDA", "NASDAQ", "SELL", 500)
        execs, _ = self.engine.match_orders("NVDA", 120.0, 120.2, "NASDAQ")
        # Internal fill leaves zero footprint on public books
        self.assertEqual(execs[0].matched_quantity, 500)
        self.assertAlmostEqual(execs[0].lit_spread, 0.20, places=4)

    def test_tc24_savings_report_to_dict_serializability(self) -> None:
        """Verify DarkPoolSavingsReport converts cleanly to JSON-serializable dict."""
        self.engine.add_order("b", "AAPL", "SP500", "BUY", 100)
        self.engine.add_order("s", "AAPL", "SP500", "SELL", 100)
        self.engine.match_orders("AAPL", 150.0, 150.2, "SP500")

        rep_dict = self.engine.calculate_institutional_savings().to_dict()
        self.assertIsInstance(rep_dict, dict)
        self.assertIn("total_institutional_savings", rep_dict)
        self.assertIn("by_symbol", rep_dict)
        self.assertTrue(rep_dict["volume_conservation_verified"])

    # -----------------------------------------------------------------------
    # Category 7: Strict Volume Conservation Invariant & Residual Routing (TC25~TC29)
    # -----------------------------------------------------------------------

    def test_tc25_strict_integer_volume_conservation(self) -> None:
        """Verify strict volume conservation: Q_order == Q_filled_dark + Q_residual."""
        # Buy 1,000 shares; Sell 600 shares.
        # Matched = 600 shares.
        # Buyer: filled = 600, residual = 400. Sum = 1000.
        # Seller: filled = 600, residual = 0. Sum = 600.
        self.engine.add_order("b_big", "JPM", "SP500", "BUY", 1000, min_fill_size=50)
        self.engine.add_order("s_small", "JPM", "SP500", "SELL", 600, min_fill_size=50)

        execs, residuals = self.engine.match_orders("JPM", 195.0, 195.2, "SP500")
        self.assertEqual(len(execs), 1)
        self.assertEqual(execs[0].matched_quantity, 600)

        # Verify volume conservation across engine
        self.assertTrue(self.engine.verify_volume_conservation())

        # Inspect buyer residual
        self.assertEqual(len(residuals), 1)
        res = residuals[0]
        self.assertEqual(res.original_order_id, "b_big")
        self.assertEqual(res.quantity, 400)
        self.assertEqual(res.filled_dark_quantity, 600)
        self.assertEqual(res.original_quantity, 1000)
        self.assertEqual(res.quantity + res.filled_dark_quantity, res.original_quantity)

    def test_tc26_multi_fill_tranches_volume_conservation(self) -> None:
        """Verify volume conservation across multiple sequential partial fills."""
        # 1 large buyer of 1,000 shares against 3 sellers (300, 400, 200)
        self.engine.add_order("b", "WMT", "SP500", "BUY", 1000, min_fill_size=50)
        self.engine.add_order("s1", "WMT", "SP500", "SELL", 300, min_fill_size=50)
        self.engine.add_order("s2", "WMT", "SP500", "SELL", 400, min_fill_size=50)
        self.engine.add_order("s3", "WMT", "SP500", "SELL", 200, min_fill_size=50)

        execs, residuals = self.engine.match_orders("WMT", 65.0, 65.1, "SP500")
        self.assertEqual(len(execs), 3)
        self.assertEqual(sum(e.matched_quantity for e in execs), 900)

        b_ord = self.engine.get_order("b")
        self.assertEqual(b_ord.filled_quantity, 900)
        self.assertEqual(b_ord.remaining_quantity, 100)
        self.assertTrue(self.engine.verify_volume_conservation())

        self.assertEqual(len(residuals), 1)
        self.assertEqual(residuals[0].quantity, 100)

    def test_tc27_residual_order_formatting(self) -> None:
        """Verify ResidualOrderPlan formats properly for downstream OMS consumption."""
        self.engine.add_order("ord_x", "DIS", "SP500", "SELL", 800, price_limit=110.0, client_id="REVERSAL")
        residuals = self.engine.get_unmatched_residuals("DIS")
        self.assertEqual(len(residuals), 1)
        plan_dict = residuals[0].to_dict()
        self.assertEqual(plan_dict["symbol"], "DIS")
        self.assertEqual(plan_dict["side"], "SELL")
        self.assertEqual(plan_dict["quantity"], 800)
        self.assertEqual(plan_dict["price_limit"], 110.0)
        self.assertEqual(plan_dict["routing_reason"], "UNMATCHED_RESIDUAL")

    def test_tc28_forward_residuals_to_smart_order_router(self) -> None:
        """Verify seamless forwarding of residuals to mock SmartOrderRouter."""
        mock_sor = MockSmartOrderRouter()
        self.engine.add_order("b_res", "KO", "SP500", "BUY", 500)
        residuals = self.engine.get_unmatched_residuals("KO")

        routed = self.engine.forward_residuals_to_sor(residuals, sor_engine=mock_sor)
        self.assertEqual(len(routed), 1)
        self.assertEqual(len(mock_sor.routed_orders), 1)
        self.assertEqual(mock_sor.routed_orders[0]["quantity"], 500)
        self.assertEqual(routed[0]["status"], DarkPoolOrderStatus.ROUTED_LIT.value)

    def test_tc29_empty_residuals_when_fully_matched(self) -> None:
        """Verify get_unmatched_residuals returns empty list when all orders are 100% matched."""
        self.engine.add_order("b", "PG", "SP500", "BUY", 300)
        self.engine.add_order("s", "PG", "SP500", "SELL", 300)
        execs, residuals = self.engine.match_orders("PG", 160.0, 160.2, "SP500")
        self.assertEqual(len(residuals), 0)
        self.assertEqual(len(self.engine.get_unmatched_residuals("PG")), 0)

    # -----------------------------------------------------------------------
    # Category 8: Locked/Crossed Markets & Collar Handlers (TC30~TC34)
    # -----------------------------------------------------------------------

    def test_tc30_crossed_market_suspends_midpoint_crossing(self) -> None:
        """Verify crossed market (bid > ask) immediately suspends dark crossing."""
        self.engine.add_order("b_cross", "SPY", "SP500", "BUY", 500)
        self.engine.add_order("s_cross", "SPY", "SP500", "SELL", 500)

        # Toxic inverted quotes: Bid = 450.50 > Ask = 450.20
        execs, residuals = self.engine.match_orders("SPY", 450.50, 450.20, "SP500")
        self.assertEqual(len(execs), 0, "Crossed market must produce zero dark executions.")
        self.assertEqual(len(residuals), 2)
        for r in residuals:
            self.assertEqual(r.routing_reason, "LOCKED_CROSSED_MARKET")
            self.assertEqual(r.route_destination, "LIT_EXCHANGE_SWEEPER")

    def test_tc31_locked_market_suspends_crossing(self) -> None:
        """Verify locked market (bid == ask) suspends dark crossing and routes lit."""
        self.engine.add_order("b_lock", "QQQ", "NASDAQ", "BUY", 400)
        self.engine.add_order("s_lock", "QQQ", "NASDAQ", "SELL", 400)

        # Locked quote: Bid = 380.00 == Ask = 380.00
        execs, residuals = self.engine.match_orders("QQQ", 380.00, 380.00, "NASDAQ")
        self.assertEqual(len(execs), 0)
        self.assertEqual(len(residuals), 2)
        self.assertEqual(residuals[0].routing_reason, "LOCKED_CROSSED_MARKET")

    def test_tc32_spread_collar_breach_rejection(self) -> None:
        """Verify excessively wide lit spread breaches collar and suspends crossing."""
        # max_spread_bps_collar = 200 bps (2.0%)
        # Bid = 100.0, Ask = 105.0. Spread = 5.0 on mid 102.5 = 487.8 bps (> 200 bps)
        self.engine.add_order("b_wide", "MEME", "SP500", "BUY", 200)
        self.engine.add_order("s_wide", "MEME", "SP500", "SELL", 200)

        execs, residuals = self.engine.match_orders("MEME", 100.0, 105.0, "SP500")
        self.assertEqual(len(execs), 0)
        self.assertEqual(len(residuals), 2)
        self.assertEqual(residuals[0].routing_reason, "COLLAR_BREACH")

    def test_tc33_non_positive_quotes_graceful_handling(self) -> None:
        """Verify non-positive quotes (bid <= 0 or ask <= 0) produce zero matches safely."""
        self.engine.add_order("b", "SYM", "SP500", "BUY", 100)
        self.engine.add_order("s", "SYM", "SP500", "SELL", 100)

        execs, _ = self.engine.match_orders("SYM", 0.0, 10.0, "SP500")
        self.assertEqual(len(execs), 0)
        execs2, _ = self.engine.match_orders("SYM", 10.0, -5.0, "SP500")
        self.assertEqual(len(execs2), 0)

    def test_tc34_price_limit_breach_prevents_unwanted_fills(self) -> None:
        """Verify price limits prevent buyer paying above limit or seller selling below limit."""
        # Lit bid = 100.0, ask = 102.0. Midpoint = 101.0.
        # Buyer limit is 100.50 (wants <= 100.50, but mid is 101.00)
        self.engine.add_order("b_lim", "IBM", "SP500", "BUY", 100, price_limit=100.50)
        self.engine.add_order("s_lim", "IBM", "SP500", "SELL", 100, price_limit=100.80)

        execs, residuals = self.engine.match_orders("IBM", 100.0, 102.0, "SP500")
        self.assertEqual(len(execs), 0, "Buyer limit was breached; trade must not execute.")
        self.assertEqual(len(residuals), 2)

    # -----------------------------------------------------------------------
    # Category 9: Multi-Strategy Batch Crossing across Portfolios (TC35~TC38)
    # -----------------------------------------------------------------------

    def test_tc35_cross_batch_multi_symbol_multi_strategy(self) -> None:
        """Verify cross_batch processes multi-symbol rebalancing basket simultaneously."""
        order_plans = [
            # Apple (matching pair)
            {"order_id": "op_1", "symbol": "AAPL", "side": "BUY", "quantity": 1000, "client_id": "STRAT_MQ"},
            {"order_id": "op_2", "symbol": "AAPL", "side": "SELL", "quantity": 800, "client_id": "STRAT_NEUTRAL"},
            # Nvidia (matching pair)
            {"order_id": "op_3", "symbol": "NVDA", "side": "BUY", "quantity": 500, "client_id": "STRAT_SURGE"},
            {"order_id": "op_4", "symbol": "NVDA", "side": "SELL", "quantity": 500, "client_id": "STRAT_REV"},
            # Samsung Elec (KRX matching pair)
            {"order_id": "op_5", "symbol": "005930", "side": "BUY", "quantity": 200, "client_id": "STRAT_VALUEUP", "market": "KOSPI"},
            {"order_id": "op_6", "symbol": "005930", "side": "SELL", "quantity": 300, "client_id": "STRAT_FLOW", "market": "KOSPI"},
        ]

        quotes = {
            "AAPL": {"bid": 180.00, "ask": 180.20, "market": "NASDAQ"},
            "NVDA": {"bid": 120.00, "ask": 120.40, "market": "NASDAQ"},
            "005930": {"bid": 71000.0, "ask": 71200.0, "market": "KOSPI"},
        }

        res = self.engine.cross_batch(order_plans, quotes)
        self.assertTrue(res["volume_conservation_verified"])
        self.assertGreater(res["total_matched_volume"], 0)
        self.assertGreater(res["total_spread_savings_value"], 0)
        self.assertGreater(res["total_fee_savings_value"], 0)

        # Check matched volumes:
        # AAPL: min(1000, 800) = 800
        # NVDA: min(500, 500) = 500
        # 005930: min(200, 300) = 200
        # Total matched = 1500
        self.assertEqual(res["total_matched_volume"], 1500)

        # Residuals: AAPL buy 200, 005930 sell 100 -> Total residuals = 2
        residuals = res["residuals"]
        self.assertEqual(len(residuals), 2)

    def test_tc36_cross_batch_zero_cross_no_opposing_flow(self) -> None:
        """Verify cross_batch handles one-sided order flow (all buys) gracefully."""
        order_plans = [
            {"order_id": "b1", "symbol": "AAPL", "side": "BUY", "quantity": 500},
            {"order_id": "b2", "symbol": "MSFT", "side": "BUY", "quantity": 300},
        ]
        quotes = {
            "AAPL": {"bid": 180.0, "ask": 180.2},
            "MSFT": {"bid": 300.0, "ask": 300.4},
        }
        res = self.engine.cross_batch(order_plans, quotes)
        self.assertEqual(res["total_matched_volume"], 0)
        self.assertEqual(len(res["executions"]), 0)
        self.assertEqual(len(res["residuals"]), 2)
        self.assertTrue(res["volume_conservation_verified"])

    def test_tc37_submit_internal_order_polymorphism(self) -> None:
        """Verify submit_internal_order accepts both dict and DarkPoolOrder with immediate crossing."""
        # Submit buy order first (resting)
        res1 = self.engine.submit_internal_order({
            "order_id": "d1",
            "symbol": "INTC",
            "side": "BUY",
            "quantity": 1000,
            "min_fill_size": 100,
        })
        self.assertEqual(res1.status, "PENDING")

        # Submit sell order with live quote (triggers match)
        ord_sell = DarkPoolOrder("d2", "INTC", "SELL", 1000, min_fill_size=100)
        res2 = self.engine.submit_internal_order(ord_sell, bid_quote=30.00, ask_quote=30.10)
        self.assertEqual(res2.status, "MATCHED")
        self.assertEqual(res2.matched_quantity, 1000)
        self.assertEqual(len(res2.executions), 1)

    def test_tc38_cross_batch_internal_cross_ratio(self) -> None:
        """Verify internal crossing ratio calculation in cross_batch."""
        # 500 buy, 500 sell -> total input = 1000 shares. Matched = 500 trades * 2 sides = 1000 shares.
        # Cross ratio should be 1.0 (100%)
        order_plans = [
            {"symbol": "QQQ", "side": "BUY", "quantity": 500},
            {"symbol": "QQQ", "side": "SELL", "quantity": 500},
        ]
        quotes = {"QQQ": {"bid": 380.0, "ask": 380.2}}
        res = self.engine.cross_batch(order_plans, quotes)
        self.assertAlmostEqual(res["internal_cross_ratio"], 1.0, places=4)

    # -----------------------------------------------------------------------
    # Category 10: State Machine, Cancellation, Wash-Sale & Telemetry (TC39~TC42)
    # -----------------------------------------------------------------------

    def test_tc39_wash_sale_protection_same_client_and_portfolio(self) -> None:
        """Verify wash-sale guard prevents internal crossing between identical client & portfolio."""
        engine_wash = SyntheticDarkPool(wash_sale_guard=True)
        engine_wash.add_order(
            "wash_b", "CAT", "SP500", "BUY", 100,
            client_id="TAX_ACCT_1", portfolio_id="PORTFOLIO_US_TAXABLE",
        )
        engine_wash.add_order(
            "wash_s", "CAT", "SP500", "SELL", 100,
            client_id="TAX_ACCT_1", portfolio_id="PORTFOLIO_US_TAXABLE",
        )

        execs, _ = engine_wash.match_orders("CAT", 250.0, 250.4, "SP500")
        self.assertEqual(len(execs), 0, "Wash-sale guard must prevent self-crossing.")

    def test_tc40_wash_sale_guard_allows_different_portfolios(self) -> None:
        """Verify crossing between different strategies / sleeves is permitted."""
        engine_wash = SyntheticDarkPool(wash_sale_guard=True)
        engine_wash.add_order(
            "cross_b", "CAT", "SP500", "BUY", 100,
            client_id="MOMENTUM_SLEEVE", portfolio_id="PORT_A",
        )
        engine_wash.add_order(
            "cross_s", "CAT", "SP500", "SELL", 100,
            client_id="VALUE_SLEEVE", portfolio_id="PORT_B",
        )

        execs, _ = engine_wash.match_orders("CAT", 250.0, 250.4, "SP500")
        self.assertEqual(len(execs), 1)
        self.assertEqual(execs[0].matched_quantity, 100)

    def test_tc41_cancel_order_lifecycle(self) -> None:
        """Verify cancelling an active resting order updates status and prevents future matches."""
        self.engine.add_order("c_b1", "BA", "SP500", "BUY", 200)
        self.assertTrue(self.engine.cancel_order("c_b1"))
        # Second cancellation should return False (already cancelled)
        self.assertFalse(self.engine.cancel_order("c_b1"))

        # Subsequent matching must not touch the cancelled order
        self.engine.add_order("c_s1", "BA", "SP500", "SELL", 200)
        execs, _ = self.engine.match_orders("BA", 180.0, 180.2, "SP500")
        self.assertEqual(len(execs), 0)

    def test_tc42_engine_reset_and_stats(self) -> None:
        """Verify engine reset cleans internal queues and telemetry reflects accurate counts."""
        self.engine.add_order("t1", "AAPL", "SP500", "BUY", 100)
        self.engine.add_order("t2", "AAPL", "SP500", "SELL", 100)
        self.engine.match_orders("AAPL", 150.0, 150.2, "SP500")

        stats = self.engine.get_stats()
        self.assertEqual(stats["total_orders"], 2)
        self.assertEqual(stats["total_executions"], 1)
        self.assertEqual(stats["total_matched_volume"], 100)
        self.assertTrue(stats["volume_conservation_verified"])

        # Reset engine
        self.engine.reset()
        reset_stats = self.engine.get_stats()
        self.assertEqual(reset_stats["total_orders"], 0)
        self.assertEqual(reset_stats["active_orders"], 0)
        self.assertEqual(reset_stats["total_executions"], 0)
        self.assertEqual(reset_stats["total_matched_volume"], 0)


if __name__ == "__main__":
    unittest.main()
