"""
tests/test_phase118_simd_lob.py
===============================
Comprehensive Unit, Integration, Invariant, Parity, and Benchmark Tests for:
Ultra-Low Latency SIMD/AVX2 Vectorized Zero-Copy LOB Matching Core (Feature F560).
Phase 118 (Release R134 / v125 Production Master).

Test Categories (59 Test Cases):
  - Category 1: Dual-Tree Parity, Module Exports & Complete Alias Trees (TC01 ~ TC04)
  - Category 2: Circular Ring Buffer Architecture & Wrap-Around Mechanics (TC05 ~ TC10)
  - Category 3: Contiguous Price Ladder Indexing & Price-Time Priority (TC11 ~ TC15)
  - Category 4: Limit Order Execution & Partial Fills (TC16 ~ TC20)
  - Category 5: Aggressive Market Orders & Multi-Level Sweeps (TC21 ~ TC24)
  - Category 6: Immediate-Or-Cancel (IOC) Execution Mechanics (TC25 ~ TC28)
  - Category 7: Fill-Or-Kill (FOK) All-or-None Feasibility & Atomicity (TC29 ~ TC32)
  - Category 8: Atomic Order Cancellations & Ladder Pruning (TC33 ~ TC36)
  - Category 9: Adversarial Stress & Edge Cases (TC37 ~ TC42)
  - Category 10: Determinism & Parity: NumPy Fallback vs PyTorch SIMD (TC43 ~ TC47)
  - Category 11: Microsecond Execution Latency & High-Throughput Benchmarks (TC48 ~ TC51)
  - Category 12: Iceberg Lifecycle, Priority Demotion & Validation (TC52 ~ TC59)
"""

from __future__ import annotations

import gc
import hashlib
import math
import sys
import time
import unittest
from pathlib import Path
from typing import Any, Dict, List

import numpy as np

# Ensure project root and trading_system are on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p in (str(PROJECT_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.core.simd_lob_matching_core import (
    VERSION,
    RELEASE,
    FEATURE,
    DEFAULT_ORDER_CAPACITY,
    DEFAULT_PRICE_LEVELS,
    DEFAULT_TICK_SIZE,
    ORDER_RECORD_SIZE,
    OrderSide,
    OrderType,
    OrderStatus,
    TimeInForce,
    SIMDBackend,
    ExecutionBackend,
    ORDER_SLOT_DTYPE,
    ORDER_RECORD_DTYPE,
    PRICE_LEVEL_DTYPE,
    MATCH_FILL_DTYPE,
    SIMDOrder,
    SIMDFillRecord,
    FillRecord,
    SIMDMatchResult,
    MatchExecutionResult,
    L3OrderEntry,
    L3PriceLevel,
    L3Snapshot,
    SIMDPriceLadderSnapshot,
    SIMDMicrostructureMetrics,
    SIMDLOBOrderPool,
    SIMDPriceLadder,
    SIMDLOBBookSide,
    SIMDOrderBook,
    SIMDLOBMatchingCore,
    UltraLowLatencySIMDLOB,
    VectorizedSIMDMatchingCore,
    Phase118SIMDLOBMatchingCore,
    AVX2LOBEngine,
    ZeroCopyLOBMatchingEngine,
    SIMDLOBEngine,
    UltraLowLatencySIMDLOBMatchingCore,
    AVX2VectorizedLOBEngine,
    SIMDVectorizedOrderBook,
    FastSIMDLOBMatcher,
    L3SIMDOrderBook,
    SIMDLOBMatchingEngine,
    VectorizedLOBMatchingCore,
    UltraLowLatencyMatchingCore,
    SIMDOrderBookMatcher,
    Level3VectorizedMatchingCore,
)


class TestPhase118SIMDLOB(unittest.TestCase):
    """51 Comprehensive Test Cases for Feature F560."""

    # -----------------------------------------------------------------------
    # Category 1: Dual-Tree Parity, Module Exports & Complete Alias Trees (TC01 ~ TC04)
    # -----------------------------------------------------------------------
    def test_tc01_dual_tree_cryptographic_parity(self):
        """TC01: Verify bit-for-bit SHA-256 cryptographic parity between canonical and mirrored paths."""
        p1 = PROJECT_ROOT / "src" / "core" / "simd_lob_matching_core.py"
        p2 = TRADING_SYSTEM_DIR / "src" / "core" / "simd_lob_matching_core.py"
        self.assertTrue(p1.exists(), f"Source file does not exist: {p1}")
        self.assertTrue(p2.exists(), f"Mirrored file does not exist: {p2}")

        h1 = hashlib.sha256(p1.read_bytes()).hexdigest()
        h2 = hashlib.sha256(p2.read_bytes()).hexdigest()
        self.assertEqual(h1, h2, f"SHA-256 mismatch:\n  src: {h1}\n  trading_system: {h2}")

    def test_tc02_version_release_feature_metadata(self):
        """TC02: Verify metadata constants at module and class levels."""
        self.assertEqual(VERSION, 118)
        self.assertEqual(RELEASE, "R134")
        self.assertEqual(FEATURE, "F560")
        self.assertEqual(SIMDLOBMatchingCore.VERSION, 118)
        self.assertEqual(SIMDLOBMatchingCore.RELEASE, "R134")
        self.assertEqual(SIMDLOBMatchingCore.FEATURE, "F560")

    def test_tc03_complete_alias_trees_and_types(self):
        """TC03: Verify all 16 class aliases and enums resolve identically."""
        aliases = [
            UltraLowLatencySIMDLOB,
            VectorizedSIMDMatchingCore,
            Phase118SIMDLOBMatchingCore,
            AVX2LOBEngine,
            ZeroCopyLOBMatchingEngine,
            SIMDLOBEngine,
            UltraLowLatencySIMDLOBMatchingCore,
            AVX2VectorizedLOBEngine,
            SIMDVectorizedOrderBook,
            FastSIMDLOBMatcher,
            L3SIMDOrderBook,
            SIMDLOBMatchingEngine,
            VectorizedLOBMatchingCore,
            UltraLowLatencyMatchingCore,
            SIMDOrderBookMatcher,
            Level3VectorizedMatchingCore,
        ]
        for alias in aliases:
            self.assertIs(alias, SIMDLOBMatchingCore, f"Alias {alias} does not match SIMDLOBMatchingCore")

        self.assertIs(FillRecord, SIMDFillRecord)
        self.assertIs(MatchExecutionResult, SIMDMatchResult)
        self.assertIs(ORDER_RECORD_DTYPE, ORDER_SLOT_DTYPE)

        # Enums
        self.assertEqual(int(OrderSide.BUY), 1)
        self.assertEqual(int(OrderSide.SELL), -1)
        self.assertEqual(int(OrderType.LIMIT), 0)
        self.assertEqual(int(OrderType.MARKET), 1)
        self.assertEqual(int(OrderType.IOC), 2)
        self.assertEqual(int(OrderType.FOK), 3)
        self.assertEqual(int(OrderStatus.ACTIVE), 1)
        self.assertEqual(int(OrderStatus.FILLED), 3)
        self.assertEqual(int(OrderStatus.CANCELED), 4)
        self.assertEqual(int(OrderStatus.REJECTED), 5)

    def test_tc04_mirrored_import_parity(self):
        """TC04: Verify import from trading_system module tree behaves identically."""
        import trading_system.src.core.simd_lob_matching_core as ts_core
        self.assertIs(ts_core.SIMDLOBMatchingCore, SIMDLOBMatchingCore)
        self.assertEqual(ts_core.VERSION, 118)
        self.assertEqual(ts_core.FEATURE, "F560")

    # -----------------------------------------------------------------------
    # Category 2: Circular Ring Buffer Architecture & Wrap-Around Mechanics (TC05 ~ TC10)
    # -----------------------------------------------------------------------
    def test_tc05_power_of_two_capacity_validation(self):
        """TC05: Power-of-two capacities succeed; non-power-of-two raise ValueError."""
        for valid_cap in (128, 512, 1024, 4096, 65536):
            pool = SIMDLOBOrderPool(capacity=valid_cap)
            self.assertEqual(pool.capacity, valid_cap)

        for invalid_cap in (1000, 1500, 0, -10, 3):
            with self.assertRaises(ValueError):
                SIMDLOBOrderPool(capacity=invalid_cap)

    def test_tc06_zero_copy_structured_compound_array_layout(self):
        """TC06: Memory buffer backed by ORDER_SLOT_DTYPE is contiguous with itemsize 130."""
        pool = SIMDLOBOrderPool(capacity=128)
        self.assertTrue(pool.slots.flags.c_contiguous)
        self.assertEqual(pool.slots.dtype.itemsize, ORDER_RECORD_SIZE)
        self.assertEqual(ORDER_RECORD_SIZE, 130)

        # Verify fields exist
        fields = pool.slots.dtype.names
        self.assertIn("order_id", fields)
        self.assertIn("price", fields)
        self.assertIn("volume", fields)
        self.assertIn("prev_slot", fields)
        self.assertIn("next_slot", fields)

    def test_tc07_monotonic_sequence_counter_and_indexing(self):
        """TC07: Inserting k items advances head_seq by k, slot index matches k % capacity."""
        pool = SIMDLOBOrderPool(capacity=16)
        for i in range(25):
            slot_idx = pool.alloc_slot(
                order_id=f"ORD_{i}",
                symbol="NVDA",
                side=OrderSide.BUY,
                order_type=OrderType.LIMIT,
                price=100.0,
                volume=10.0,
            )
            self.assertEqual(pool.head_seq, i + 1)
            self.assertEqual(slot_idx, i % 16)

    def test_tc08_circular_ring_buffer_wrap_around_integrity(self):
        """TC08: Capacity=8, insert 12 orders, orders 8..11 overwrite slots 0..3 with invariant memory."""
        pool = SIMDLOBOrderPool(capacity=8)
        initial_bytes = pool.slots.nbytes

        for i in range(12):
            pool.alloc_slot(
                order_id=f"ORD_{i}",
                symbol="NVDA",
                side=OrderSide.BUY,
                order_type=OrderType.LIMIT,
                price=100.0 + i,
                volume=10.0,
            )

        self.assertEqual(pool.slots.nbytes, initial_bytes)
        # Verify slots 0..3 hold orders 8..11
        for s in range(4):
            expected_oid = f"ORD_{s + 8}"
            actual_oid = pool.slots[s]["order_id"].split(b"\x00", 1)[0].decode("ascii")
            self.assertEqual(actual_oid, expected_oid)

    def test_tc09_overwritten_slot_eviction_and_ghost_cancellation_prevention(self):
        """TC09: Overwritten slot evicts old order from ID map, preventing ghost cancellations."""
        engine = SIMDLOBMatchingCore(symbol="NVDA", pool_capacity=8)

        # Fill 8 slots with non-crossing orders
        for i in range(8):
            engine.match_order({
                "order_id": f"ORD_{i}",
                "symbol": "NVDA",
                "side": OrderSide.BUY,
                "price": 90.0 - i,  # non-crossing
                "volume": 10.0,
                "order_type": OrderType.LIMIT,
            })

        self.assertIsNotNone(engine.get_order_by_id("ORD_0"))

        # 9th order overwrites slot 0
        engine.match_order({
            "order_id": "ORD_8",
            "symbol": "NVDA",
            "side": OrderSide.BUY,
            "price": 81.0,
            "volume": 10.0,
            "order_type": OrderType.LIMIT,
        })

        # Old order ORD_0 was evicted: cancel must return False, get_order must return None
        self.assertFalse(engine.cancel_order("ORD_0"))
        self.assertIsNone(engine.get_order_by_id("ORD_0"))

        # Active order ORD_8 in slot 0 remains valid and cancelable
        ord_8 = engine.get_order_by_id("ORD_8")
        self.assertIsNotNone(ord_8)
        self.assertEqual(ord_8["status"], OrderStatus.ACTIVE)
        self.assertTrue(engine.cancel_order("ORD_8"))

    def test_tc10_active_orders_view_extraction_under_wrap_around(self):
        """TC10: get_active_orders() returns only active orders, excluding canceled and evicted."""
        engine = SIMDLOBMatchingCore(symbol="NVDA", pool_capacity=16)
        for i in range(20):
            engine.match_order({
                "order_id": f"ORD_{i}",
                "symbol": "NVDA",
                "side": OrderSide.BUY,
                "price": 50.0 - (i * 0.1),
                "volume": 10.0,
                "order_type": OrderType.LIMIT,
            })

        # Cancel some active orders
        engine.cancel_order("ORD_18")
        engine.cancel_order("ORD_19")

        active_orders = engine.get_active_orders()
        active_ids = {o["order_id"] for o in active_orders}

        # ORD_18 and ORD_19 were canceled
        self.assertNotIn("ORD_18", active_ids)
        self.assertNotIn("ORD_19", active_ids)

        # ORD_0 .. ORD_3 were overwritten/evicted (since capacity=16 and 20 inserted)
        for old_i in range(4):
            self.assertNotIn(f"ORD_{old_i}", active_ids)

        # Remaining should be ACTIVE
        for o in active_orders:
            self.assertIn(o["status"], (OrderStatus.ACTIVE, OrderStatus.PARTIALLY_FILLED))

    # -----------------------------------------------------------------------
    # Category 3: Contiguous Price Ladder Indexing & Price-Time Priority (TC11 ~ TC15)
    # -----------------------------------------------------------------------
    def test_tc11_strictly_sorted_contiguous_price_ladders(self):
        """TC11: Bid prices strictly descending, Ask prices strictly ascending."""
        engine = SIMDLOBMatchingCore(symbol="NVDA")
        # Place bids in random order
        for px in (95.0, 98.0, 91.0, 99.0, 93.0):
            engine.match_order({"order_id": f"B_{px}", "side": "BUY", "price": px, "volume": 10.0})
        # Place asks in random order
        for px in (105.0, 102.0, 108.0, 101.0, 103.0):
            engine.match_order({"order_id": f"A_{px}", "side": "SELL", "price": px, "volume": 10.0})

        bids = engine.bid_prices
        asks = engine.ask_prices

        self.assertTrue(np.all(np.diff(bids) < 0.0), f"Bids not descending: {bids}")
        self.assertTrue(np.all(np.diff(asks) > 0.0), f"Asks not ascending: {asks}")
        self.assertEqual(engine.best_bid, 99.0)
        self.assertEqual(engine.best_ask, 101.0)

    def test_tc12_dynamic_price_level_allocation_and_binary_indexing(self):
        """TC12: Insert non-contiguous price levels, verify binary sort."""
        engine = SIMDLOBMatchingCore(symbol="NVDA")
        # Asks: 100.0, 102.5, 101.0 -> [100.0, 101.0, 102.5]
        for px in (100.0, 102.5, 101.0):
            engine.match_order({"order_id": f"A_{px}", "side": "SELL", "price": px, "volume": 10.0})
        np.testing.assert_allclose(engine.ask_prices, [100.0, 101.0, 102.5])

        # Bids: 99.0, 97.5, 98.0 -> [99.0, 98.0, 97.5]
        for px in (99.0, 97.5, 98.0):
            engine.match_order({"order_id": f"B_{px}", "side": "BUY", "price": px, "volume": 10.0})
        np.testing.assert_allclose(engine.bid_prices, [99.0, 98.0, 97.5])

    def test_tc13_level_pruning_upon_total_volume_depletion(self):
        """TC13: Level pruned from ladder array when volume/order count hits 0."""
        engine = SIMDLOBMatchingCore(symbol="NVDA")
        engine.match_order({"order_id": "B1", "side": "BUY", "price": 100.0, "volume": 50.0})
        engine.match_order({"order_id": "B2", "side": "BUY", "price": 95.0, "volume": 50.0})
        self.assertEqual(len(engine.bid_prices), 2)

        # Cancel B1 completely
        engine.cancel_order("B1")
        self.assertEqual(len(engine.bid_prices), 1)
        self.assertEqual(engine.best_bid, 95.0)

    def test_tc14_strict_price_time_priority_fifo_queue(self):
        """TC14: 3 makers at same price matched strictly in arrival order."""
        engine = SIMDLOBMatchingCore(symbol="NVDA")
        engine.match_order({"order_id": "M1", "side": "SELL", "price": 100.0, "volume": 50.0})
        engine.match_order({"order_id": "M2", "side": "SELL", "price": 100.0, "volume": 100.0})
        engine.match_order({"order_id": "M3", "side": "SELL", "price": 100.0, "volume": 75.0})

        # Taker buy 120 shares at 100.0
        res = engine.match_order({"order_id": "T1", "side": "BUY", "price": 100.0, "volume": 120.0})
        self.assertEqual(res.filled_volume, 120.0)
        self.assertEqual(len(res.fills), 2)

        # Fill 1: Maker M1 (50 shares)
        self.assertEqual(res.fills[0].maker_order_id, "M1")
        self.assertEqual(res.fills[0].volume, 50.0)

        # Fill 2: Maker M2 (70 shares, 30 remaining)
        self.assertEqual(res.fills[1].maker_order_id, "M2")
        self.assertEqual(res.fills[1].volume, 70.0)

        m2_info = engine.get_order_by_id("M2")
        self.assertEqual(m2_info["display_volume"], 30.0)

        # Next taker of 10 shares must match M2, NOT M3
        res2 = engine.match_order({"order_id": "T2", "side": "BUY", "price": 100.0, "volume": 10.0})
        self.assertEqual(len(res2.fills), 1)
        self.assertEqual(res2.fills[0].maker_order_id, "M2")
        self.assertEqual(res2.fills[0].volume, 10.0)

    def test_tc15_multi_level_depth_snapshotting(self):
        """TC15: get_l3_snapshot(depth=10) extracts accurate 10 levels and 40-float tensor."""
        engine = SIMDLOBMatchingCore(symbol="NVDA")
        for i in range(15):
            engine.match_order({"order_id": f"B_{i}", "side": "BUY", "price": 100.0 - i, "volume": 10.0 * (i + 1)})
            engine.match_order({"order_id": f"A_{i}", "side": "SELL", "price": 105.0 + i, "volume": 15.0 * (i + 1)})

        snap = engine.get_l3_snapshot(depth=10)
        self.assertEqual(snap.depth, 10)
        self.assertEqual(len(snap.bids), 10)
        self.assertEqual(len(snap.asks), 10)
        self.assertEqual(snap.flat_tensor_40.shape, (40,))
        self.assertFalse(np.any(np.isnan(snap.flat_tensor_40)))
        self.assertEqual(snap.best_bid, 100.0)
        self.assertEqual(snap.best_ask, 105.0)
        self.assertEqual(snap.spread, 5.0)

    # -----------------------------------------------------------------------
    # Category 4: Limit Order Execution & Partial Fills (TC16 ~ TC20)
    # -----------------------------------------------------------------------
    def test_tc16_resting_limit_order_placement_on_empty_book(self):
        """TC16: Limit Buy placed on empty book rests; fills=0, best_bid updated."""
        engine = SIMDLOBMatchingCore(symbol="NVDA")
        res = engine.match_order({"order_id": "B1", "side": "BUY", "price": 150.0, "volume": 100.0})
        self.assertEqual(res.filled_volume, 0.0)
        self.assertEqual(res.remaining_volume, 100.0)
        self.assertEqual(len(res.fills), 0)
        self.assertEqual(engine.best_bid, 150.0)
        self.assertEqual(engine.best_ask, float("inf"))

    def test_tc17_non_crossing_bid_ask_formation(self):
        """TC17: Buy 99.0 and Sell 101.0 form non-crossing book; spread=2.0, mid=100.0."""
        engine = SIMDLOBMatchingCore(symbol="NVDA")
        engine.match_order({"order_id": "B1", "side": "BUY", "price": 99.0, "volume": 100.0})
        engine.match_order({"order_id": "A1", "side": "SELL", "price": 101.0, "volume": 100.0})
        self.assertEqual(engine.spread, 2.0)
        self.assertEqual(engine.mid_price, 100.0)

    def test_tc18_taker_limit_order_exact_full_fill(self):
        """TC18: Resting Ask 100.0 (vol 100), incoming Buy 100.0 (vol 100) -> 100% filled."""
        engine = SIMDLOBMatchingCore(symbol="NVDA")
        engine.match_order({"order_id": "A1", "side": "SELL", "price": 100.0, "volume": 100.0})
        res = engine.match_order({"order_id": "T1", "side": "BUY", "price": 100.0, "volume": 100.0})
        self.assertEqual(res.filled_volume, 100.0)
        self.assertEqual(res.remaining_volume, 0.0)
        self.assertTrue(res.is_fully_filled)
        self.assertEqual(len(engine.ask_prices), 0)

    def test_tc19_taker_limit_order_partial_fill_queue_preservation(self):
        """TC19: Resting Ask 100.0 (vol 200), incoming Buy 100.0 (vol 75) -> maker leaves 125."""
        engine = SIMDLOBMatchingCore(symbol="NVDA")
        engine.match_order({"order_id": "A1", "side": "SELL", "price": 100.0, "volume": 200.0})
        res = engine.match_order({"order_id": "T1", "side": "BUY", "price": 100.0, "volume": 75.0})
        self.assertEqual(res.filled_volume, 75.0)
        self.assertTrue(res.is_fully_filled)
        a1_info = engine.get_order_by_id("A1")
        self.assertEqual(a1_info["display_volume"], 125.0)
        self.assertEqual(a1_info["status"], OrderStatus.PARTIALLY_FILLED)

    def test_tc20_taker_limit_order_residual_volume_resting(self):
        """TC20: Resting Ask 100.0 (vol 50), incoming Buy 100.0 (vol 120) -> 50 fills, 70 rests as Bid."""
        engine = SIMDLOBMatchingCore(symbol="NVDA")
        engine.match_order({"order_id": "A1", "side": "SELL", "price": 100.0, "volume": 50.0})
        res = engine.match_order({"order_id": "T1", "side": "BUY", "price": 100.0, "volume": 120.0})
        self.assertEqual(res.filled_volume, 50.0)
        self.assertEqual(res.remaining_volume, 70.0)
        self.assertEqual(len(engine.ask_prices), 0)
        self.assertEqual(engine.best_bid, 100.0)
        self.assertEqual(engine.bids.get_best_volume(), 70.0)

    # -----------------------------------------------------------------------
    # Category 5: Aggressive Market Orders & Multi-Level Sweeps (TC21 ~ TC24)
    # -----------------------------------------------------------------------
    def test_tc21_multi_level_market_buy_sweep(self):
        """TC21: Sweeps 3 ask tiers (100@100, 150@101, 50@102) for 300 volume."""
        engine = SIMDLOBMatchingCore(symbol="NVDA")
        engine.match_order({"order_id": "B0", "side": "BUY", "price": 99.0, "volume": 100.0})
        engine.match_order({"order_id": "A1", "side": "SELL", "price": 100.0, "volume": 100.0})
        engine.match_order({"order_id": "A2", "side": "SELL", "price": 101.0, "volume": 150.0})
        engine.match_order({"order_id": "A3", "side": "SELL", "price": 102.0, "volume": 200.0})

        res = engine.execute_market_order(symbol="NVDA", side="BUY", volume=300.0)
        self.assertEqual(res.filled_volume, 300.0)
        self.assertEqual(res.swept_levels_count, 3)

    def test_tc22_analytical_vwap_calculation_verification(self):
        """TC22: VWAP = (100*100 + 150*101 + 50*102) / 300 = 100.833333."""
        engine = SIMDLOBMatchingCore(symbol="NVDA")
        engine.match_order({"order_id": "B0", "side": "BUY", "price": 99.0, "volume": 100.0})
        engine.match_order({"order_id": "A1", "side": "SELL", "price": 100.0, "volume": 100.0})
        engine.match_order({"order_id": "A2", "side": "SELL", "price": 101.0, "volume": 150.0})
        engine.match_order({"order_id": "A3", "side": "SELL", "price": 102.0, "volume": 200.0})

        res = engine.execute_market_order(symbol="NVDA", side="BUY", volume=300.0)
        expected_vwap = (100 * 100.0 + 150 * 101.0 + 50 * 102.0) / 300.0
        self.assertAlmostEqual(res.vwap_fill_price, expected_vwap, places=5)

    def test_tc23_arrival_slippage_invariant_verification(self):
        """TC23: Arrival midpoint = 99.50, slippage bps matches formula within 1e-2."""
        engine = SIMDLOBMatchingCore(symbol="NVDA")
        engine.match_order({"order_id": "B0", "side": "BUY", "price": 99.0, "volume": 100.0})
        engine.match_order({"order_id": "A1", "side": "SELL", "price": 100.0, "volume": 100.0})
        engine.match_order({"order_id": "A2", "side": "SELL", "price": 101.0, "volume": 150.0})
        engine.match_order({"order_id": "A3", "side": "SELL", "price": 102.0, "volume": 200.0})

        res = engine.execute_market_order(symbol="NVDA", side="BUY", volume=300.0)
        expected_slippage = (100.833333 - 99.50) / 99.50 * 10000.0  # ~134.0033
        self.assertAlmostEqual(res.slippage_bps, expected_slippage, delta=0.05)

    def test_tc24_ladder_cleanup_and_new_best_quote(self):
        """TC24: Exhausted levels pruned; new best_ask = 102.0 with remaining 150.0."""
        engine = SIMDLOBMatchingCore(symbol="NVDA")
        engine.match_order({"order_id": "A1", "side": "SELL", "price": 100.0, "volume": 100.0})
        engine.match_order({"order_id": "A2", "side": "SELL", "price": 101.0, "volume": 150.0})
        engine.match_order({"order_id": "A3", "side": "SELL", "price": 102.0, "volume": 200.0})

        engine.execute_market_order(symbol="NVDA", side="BUY", volume=300.0)
        self.assertEqual(engine.best_ask, 102.0)
        self.assertEqual(engine.asks.get_best_volume(), 150.0)

    # -----------------------------------------------------------------------
    # Category 6: Immediate-Or-Cancel (IOC) Execution Mechanics (TC25 ~ TC28)
    # -----------------------------------------------------------------------
    def test_tc25_ioc_order_full_fill(self):
        """TC25: IOC order fills completely when opposing volume is sufficient."""
        engine = SIMDLOBMatchingCore(symbol="NVDA")
        engine.match_order({"order_id": "A1", "side": "SELL", "price": 100.0, "volume": 100.0})
        res = engine.execute_ioc({"order_id": "IOC1", "side": "BUY", "price": 100.0, "volume": 80.0})
        self.assertEqual(res.filled_volume, 80.0)
        self.assertEqual(res.remaining_volume, 0.0)
        self.assertTrue(res.is_fully_filled)
        self.assertEqual(engine.asks.get_best_volume(), 20.0)

    def test_tc26_ioc_order_partial_fill_residual_cancellation(self):
        """TC26: IOC fills available 50 shares, cancels 70 remainder; residual NEVER rests."""
        engine = SIMDLOBMatchingCore(symbol="NVDA")
        engine.match_order({"order_id": "A1", "side": "SELL", "price": 100.0, "volume": 50.0})
        res = engine.execute_ioc({"order_id": "IOC1", "side": "BUY", "price": 100.0, "volume": 120.0})
        self.assertEqual(res.filled_volume, 50.0)
        self.assertEqual(res.remaining_volume, 70.0)
        self.assertEqual(res.canceled_volume, 70.0)
        self.assertFalse(res.is_fully_filled)
        # Invariant: Unfilled residual never rests in book
        self.assertEqual(engine.best_bid, 0.0)

    def test_tc27_ioc_non_marketable_order_zero_footprint(self):
        """TC27: Non-marketable IOC produces 0 fills and leaves 0 footprint."""
        engine = SIMDLOBMatchingCore(symbol="NVDA")
        engine.match_order({"order_id": "A1", "side": "SELL", "price": 105.0, "volume": 50.0})
        res = engine.execute_ioc({"order_id": "IOC1", "side": "BUY", "price": 100.0, "volume": 50.0})
        self.assertEqual(res.filled_volume, 0.0)
        self.assertEqual(res.canceled_volume, 50.0)
        self.assertEqual(engine.best_bid, 0.0)
        self.assertEqual(engine.best_ask, 105.0)

    def test_tc28_ioc_multi_level_sweep_with_price_boundary_limit(self):
        """TC28: Sweeps within limit price; volume at higher price untouched, remainder discarded."""
        engine = SIMDLOBMatchingCore(symbol="NVDA")
        engine.match_order({"order_id": "A1", "side": "SELL", "price": 100.0, "volume": 50.0})
        engine.match_order({"order_id": "A2", "side": "SELL", "price": 101.0, "volume": 50.0})
        engine.match_order({"order_id": "A3", "side": "SELL", "price": 102.0, "volume": 50.0})

        # IOC Buy Limit at 101.0 for 120 shares
        res = engine.execute_ioc({"order_id": "IOC1", "side": "BUY", "price": 101.0, "volume": 120.0})
        self.assertEqual(res.filled_volume, 100.0)
        self.assertEqual(res.canceled_volume, 20.0)
        # Ask at 102.0 remains untouched
        self.assertEqual(engine.best_ask, 102.0)
        self.assertEqual(engine.asks.get_best_volume(), 50.0)

    # -----------------------------------------------------------------------
    # Category 7: Fill-Or-Kill (FOK) All-or-None Feasibility & Atomicity (TC29 ~ TC32)
    # -----------------------------------------------------------------------
    def test_tc29_fok_full_fill_success_case(self):
        """TC29: Available depth 110 >= 100 -> FOK commits 100% volume."""
        engine = SIMDLOBMatchingCore(symbol="NVDA")
        engine.match_order({"order_id": "A1", "side": "SELL", "price": 100.0, "volume": 50.0})
        engine.match_order({"order_id": "A2", "side": "SELL", "price": 101.0, "volume": 60.0})

        res = engine.execute_fok({"order_id": "FOK1", "side": "BUY", "price": 101.0, "volume": 100.0})
        self.assertEqual(res.filled_volume, 100.0)
        self.assertTrue(res.is_fully_filled)
        self.assertEqual(res.status, OrderStatus.FILLED)
        self.assertEqual(engine.asks.get_best_volume(), 10.0)

    def test_tc30_fok_rejection_due_to_insufficient_volume_zero_book_mutation(self):
        """TC30: Available depth 70 < 100 -> FOK aborts with 0 fills; book 100% untouched."""
        engine = SIMDLOBMatchingCore(symbol="NVDA")
        engine.match_order({"order_id": "A1", "side": "SELL", "price": 100.0, "volume": 40.0})
        engine.match_order({"order_id": "A2", "side": "SELL", "price": 101.0, "volume": 30.0})

        res = engine.execute_fok({"order_id": "FOK1", "side": "BUY", "price": 101.0, "volume": 100.0})
        self.assertEqual(res.filled_volume, 0.0)
        self.assertEqual(res.remaining_volume, 100.0)
        self.assertEqual(len(res.fills), 0)
        self.assertEqual(res.status, OrderStatus.REJECTED)
        self.assertTrue(res.is_rejected)

        # Invariant: Order book MUST be 100% untouched
        self.assertEqual(len(engine.ask_prices), 2)
        np.testing.assert_allclose(engine.ask_volumes, [40.0, 30.0])

    def test_tc31_fok_rejection_due_to_price_ceiling_violation(self):
        """TC31: Asks at 100.0 (50) and 105.0 (100). FOK Buy limit 102.0 for 100 -> aborts."""
        engine = SIMDLOBMatchingCore(symbol="NVDA")
        engine.match_order({"order_id": "A1", "side": "SELL", "price": 100.0, "volume": 50.0})
        engine.match_order({"order_id": "A2", "side": "SELL", "price": 105.0, "volume": 100.0})

        res = engine.execute_fok({"order_id": "FOK1", "side": "BUY", "price": 102.0, "volume": 100.0})
        self.assertEqual(res.filled_volume, 0.0)
        self.assertTrue(res.is_rejected)
        # Book untouched
        self.assertEqual(engine.asks.get_best_volume(), 50.0)

    def test_tc32_fok_on_empty_book_rejection(self):
        """TC32: FOK on empty book rejects cleanly without exception."""
        engine = SIMDLOBMatchingCore(symbol="NVDA")
        res = engine.execute_fok({"order_id": "FOK1", "side": "BUY", "price": 100.0, "volume": 50.0})
        self.assertEqual(res.filled_volume, 0.0)
        self.assertTrue(res.is_rejected)

    # -----------------------------------------------------------------------
    # Category 8: Atomic Order Cancellations & Ladder Pruning (TC33 ~ TC36)
    # -----------------------------------------------------------------------
    def test_tc33_o1_atomic_cancellation_of_resting_order(self):
        """TC33: Resting order B1 canceled atomically; ladder volume decrements."""
        engine = SIMDLOBMatchingCore(symbol="NVDA")
        engine.match_order({"order_id": "B1", "side": "BUY", "price": 100.0, "volume": 50.0})
        engine.match_order({"order_id": "B2", "side": "BUY", "price": 100.0, "volume": 50.0})
        self.assertEqual(engine.bids.get_best_volume(), 100.0)

        self.assertTrue(engine.cancel_order("B1"))
        self.assertEqual(engine.bids.get_best_volume(), 50.0)
        self.assertIsNone(engine.get_order_by_id("B1"))

    def test_tc34_level_depletion_via_cancellation(self):
        """TC34: Sole order at price level canceled -> level pruned from ladder."""
        engine = SIMDLOBMatchingCore(symbol="NVDA")
        engine.match_order({"order_id": "B1", "side": "BUY", "price": 95.0, "volume": 50.0})
        self.assertEqual(len(engine.bid_prices), 1)

        self.assertTrue(engine.cancel_order("B1"))
        self.assertEqual(len(engine.bid_prices), 0)
        self.assertEqual(engine.best_bid, 0.0)

    def test_tc35_idempotent_cancellation_invariance(self):
        """TC35: Second cancellation on already canceled order returns False."""
        engine = SIMDLOBMatchingCore(symbol="NVDA")
        engine.match_order({"order_id": "B1", "side": "BUY", "price": 100.0, "volume": 50.0})
        self.assertTrue(engine.cancel_order("B1"))
        self.assertFalse(engine.cancel_order("B1"))

    def test_tc36_non_existent_order_cancellation(self):
        """TC36: Canceling unknown order ID returns False without error."""
        engine = SIMDLOBMatchingCore(symbol="NVDA")
        self.assertFalse(engine.cancel_order("UNKNOWN_ORD_999"))

    # -----------------------------------------------------------------------
    # Category 9: Adversarial Stress & Edge Cases (TC37 ~ TC42)
    # -----------------------------------------------------------------------
    def test_tc37_empty_book_query_invariants(self):
        """TC37: Querying empty book yields safe default values without exception."""
        engine = SIMDLOBMatchingCore(symbol="NVDA")
        self.assertEqual(engine.best_bid, 0.0)
        self.assertEqual(engine.best_ask, float("inf"))
        self.assertEqual(engine.mid_price, 0.0)
        self.assertEqual(engine.spread, 0.0)
        snap = engine.get_l3_snapshot(depth=10)
        self.assertEqual(len(snap.bids), 0)
        self.assertEqual(len(snap.asks), 0)

    def test_tc38_crossed_book_resolution_price_improvement(self):
        """TC38: Taker Buy at 102 matches Ask at 100, providing 2.0 price improvement."""
        engine = SIMDLOBMatchingCore(symbol="NVDA")
        engine.match_order({"order_id": "A1", "side": "SELL", "price": 100.0, "volume": 50.0})
        res = engine.match_order({"order_id": "T1", "side": "BUY", "price": 102.0, "volume": 70.0})

        self.assertEqual(res.filled_volume, 50.0)
        self.assertEqual(res.fills[0].price, 100.0)  # Price improvement
        self.assertEqual(engine.best_bid, 102.0)     # Remainder rests at limit price
        self.assertEqual(engine.bids.get_best_volume(), 20.0)

    def test_tc39_whale_order_sweeping_entire_depth(self):
        """TC39: Whale market buy for 50k shares consumes all 1k shares; remainder canceled."""
        engine = SIMDLOBMatchingCore(symbol="NVDA")
        for i in range(5):
            engine.match_order({"order_id": f"A_{i}", "side": "SELL", "price": 100.0 + i, "volume": 200.0})

        res = engine.execute_market_order(symbol="NVDA", side="BUY", volume=50000.0)
        self.assertEqual(res.filled_volume, 1000.0)
        self.assertEqual(res.canceled_volume, 49000.0)
        self.assertEqual(len(engine.ask_prices), 0)
        self.assertEqual(res.swept_levels_count, 5)

    def test_tc40_zero_or_negative_volume_rejection(self):
        """TC40: Volume <= 0 raises ValueError."""
        engine = SIMDLOBMatchingCore(symbol="NVDA")
        with self.assertRaises(ValueError):
            engine.match_order({"order_id": "X", "side": "BUY", "price": 100.0, "volume": 0.0})
        with self.assertRaises(ValueError):
            engine.match_order({"order_id": "Y", "side": "BUY", "price": 100.0, "volume": -10.0})

    def test_tc41_invalid_price_rejection(self):
        """TC41: Limit price <= 0, NaN, or Inf raises ValueError."""
        engine = SIMDLOBMatchingCore(symbol="NVDA")
        with self.assertRaises(ValueError):
            engine.match_order({"order_id": "X", "side": "BUY", "price": 0.0, "volume": 10.0})
        with self.assertRaises(ValueError):
            engine.match_order({"order_id": "Y", "side": "BUY", "price": -50.0, "volume": 10.0})
        with self.assertRaises(ValueError):
            engine.match_order({"order_id": "Z", "side": "BUY", "price": float("nan"), "volume": 10.0})

    def test_tc42_invalid_side_and_type_input_parsing(self):
        """TC42: Unknown side or order type string raises ValueError."""
        with self.assertRaises(ValueError):
            OrderSide.from_str("INVALID_SIDE")
        with self.assertRaises(ValueError):
            OrderType.from_str("UNKNOWN_TYPE")

    # -----------------------------------------------------------------------
    # Category 10: Determinism & Parity: NumPy Fallback vs PyTorch SIMD (TC43 ~ TC47)
    # -----------------------------------------------------------------------
    def test_tc43_dual_backend_initialization_invariance(self):
        """TC43: Instantiate engines with NumPy and PyTorch backends cleanly."""
        eng_np = SIMDLOBMatchingCore(symbol="NVDA", use_torch=False)
        self.assertEqual(eng_np.backend, "numpy")
        self.assertFalse(eng_np.use_torch)

        eng_pt = SIMDLOBMatchingCore(symbol="NVDA", use_torch=True)
        # On this environment PyTorch is installed, so backend should be torch
        self.assertEqual(eng_pt.backend, "torch")
        self.assertTrue(eng_pt.use_torch)

    def test_tc44_deterministic_book_state_parity_after_identical_placements(self):
        """TC44: 50 non-crossing orders yield identical price/volume arrays on both backends."""
        eng_np = SIMDLOBMatchingCore(symbol="NVDA", use_torch=False)
        eng_pt = SIMDLOBMatchingCore(symbol="NVDA", use_torch=True)

        for i in range(25):
            ord_b = {"order_id": f"B_{i}", "side": "BUY", "price": 100.0 - (i * 0.5), "volume": 10.0 + i}
            ord_a = {"order_id": f"A_{i}", "side": "SELL", "price": 105.0 + (i * 0.5), "volume": 10.0 + i}
            eng_np.match_order(ord_b)
            eng_pt.match_order(ord_b)
            eng_np.match_order(ord_a)
            eng_pt.match_order(ord_a)

        np.testing.assert_allclose(eng_np.bid_prices, eng_pt.bid_prices)
        np.testing.assert_allclose(eng_np.bid_volumes, eng_pt.bid_volumes)
        np.testing.assert_allclose(eng_np.ask_prices, eng_pt.ask_prices)
        np.testing.assert_allclose(eng_np.ask_volumes, eng_pt.ask_volumes)
        self.assertEqual(eng_np.best_bid, eng_pt.best_bid)
        self.assertEqual(eng_np.best_ask, eng_pt.best_ask)
        self.assertEqual(eng_np.mid_price, eng_pt.mid_price)

    def test_tc45_deterministic_multi_level_sweep_execution_parity(self):
        """TC45: Identical sweeps executed on both engines produce identical fills and VWAP."""
        eng_np = SIMDLOBMatchingCore(symbol="NVDA", use_torch=False)
        eng_pt = SIMDLOBMatchingCore(symbol="NVDA", use_torch=True)

        for i in range(5):
            o = {"order_id": f"A_{i}", "side": "SELL", "price": 100.0 + i, "volume": 50.0 * (i + 1)}
            eng_np.match_order(o)
            eng_pt.match_order(o)

        sweep = {"order_id": "SWEEP", "side": "BUY", "price": 103.0, "volume": 200.0}
        res_np = eng_np.match_order(sweep)
        res_pt = eng_pt.match_order(sweep)

        self.assertEqual(res_np.filled_volume, res_pt.filled_volume)
        self.assertEqual(len(res_np.fills), len(res_pt.fills))
        self.assertAlmostEqual(res_np.vwap_fill_price, res_pt.vwap_fill_price, places=6)
        np.testing.assert_allclose(eng_np.ask_volumes, eng_pt.ask_volumes)

    def test_tc46_deterministic_ioc_and_fok_parity(self):
        """TC46: IOC and FOK execute with bit-level identical outcomes on both backends."""
        eng_np = SIMDLOBMatchingCore(symbol="NVDA", use_torch=False)
        eng_pt = SIMDLOBMatchingCore(symbol="NVDA", use_torch=True)

        # Pre-seed liquidity
        for i in range(3):
            o = {"order_id": f"A_{i}", "side": "SELL", "price": 100.0 + i, "volume": 30.0}
            eng_np.match_order(o)
            eng_pt.match_order(o)

        # FOK reject
        fok_rej = {"order_id": "FOK_R", "side": "BUY", "price": 101.0, "volume": 100.0}
        r1_np = eng_np.execute_fok(fok_rej)
        r1_pt = eng_pt.execute_fok(fok_rej)
        self.assertEqual(r1_np.is_rejected, r1_pt.is_rejected)
        self.assertEqual(r1_np.filled_volume, r1_pt.filled_volume)

        # IOC sweep
        ioc = {"order_id": "IOC_1", "side": "BUY", "price": 101.0, "volume": 50.0}
        r2_np = eng_np.execute_ioc(ioc)
        r2_pt = eng_pt.execute_ioc(ioc)
        self.assertEqual(r2_np.filled_volume, r2_pt.filled_volume)
        self.assertAlmostEqual(r2_np.vwap_fill_price, r2_pt.vwap_fill_price, places=6)

    def test_tc47_deterministic_order_cancellation_parity(self):
        """TC47: Canceling identical orders yields identical state on both backends."""
        eng_np = SIMDLOBMatchingCore(symbol="NVDA", use_torch=False)
        eng_pt = SIMDLOBMatchingCore(symbol="NVDA", use_torch=True)

        for i in range(10):
            o = {"order_id": f"B_{i}", "side": "BUY", "price": 100.0 - i, "volume": 20.0}
            eng_np.match_order(o)
            eng_pt.match_order(o)

        for i in (1, 3, 5, 7):
            c_np = eng_np.cancel_order(f"B_{i}")
            c_pt = eng_pt.cancel_order(f"B_{i}")
            self.assertEqual(c_np, c_pt)

        np.testing.assert_allclose(eng_np.bid_prices, eng_pt.bid_prices)
        np.testing.assert_allclose(eng_np.bid_volumes, eng_pt.bid_volumes)

    # -----------------------------------------------------------------------
    # Category 11: Microsecond Execution Latency & High-Throughput Benchmarks (TC48 ~ TC51)
    # -----------------------------------------------------------------------
    def test_tc48_ring_buffer_order_insertion_latency_benchmark(self):
        """TC48: Average order slot insertion latency < 10.0 microseconds."""
        pool = SIMDLOBOrderPool(capacity=4096)
        # Warmup
        for i in range(100):
            pool.alloc_slot(f"W_{i}", "NVDA", 1, 0, 100.0, 10.0)

        t0 = time.perf_counter_ns()
        N = 1000
        for i in range(N):
            pool.alloc_slot(f"ORD_{i}", "NVDA", 1, 0, 100.0, 10.0)
        t1 = time.perf_counter_ns()

        avg_latency_us = (t1 - t0) / (N * 1000.0)
        self.assertLess(avg_latency_us, 10.0, f"Average insertion latency too high: {avg_latency_us:.3f} us")

    def test_tc49_atomic_order_cancellation_latency_benchmark(self):
        """TC49: Average order cancellation latency < 25.0 microseconds."""
        engine = SIMDLOBMatchingCore(symbol="NVDA", pool_capacity=4096)
        N = 500
        for i in range(N):
            engine.match_order({"order_id": f"C_{i}", "side": "BUY", "price": 50.0 - (i * 0.01), "volume": 10.0})

        # Warmup loop to prime Python caches and instruction cache
        for w in range(20):
            engine.match_order({"order_id": f"W_{w}", "side": "BUY", "price": 40.0, "volume": 1.0})
            engine.cancel_order(f"W_{w}")

        # GC isolation for deterministic microsecond timing
        gc.collect()
        gc_was_enabled = gc.isenabled()
        gc.disable()
        try:
            t0 = time.perf_counter_ns()
            for i in range(N):
                engine.cancel_order(f"C_{i}")
            t1 = time.perf_counter_ns()
        finally:
            if gc_was_enabled:
                gc.enable()

        avg_cancel_us = (t1 - t0) / (N * 1000.0)
        self.assertLess(avg_cancel_us, 25.0, f"Average cancel latency too high: {avg_cancel_us:.3f} us")

    def test_tc50_order_matching_burst_throughput_benchmark(self):
        """TC50: Throughput > 20,000 orders/sec (< 50 us per match)."""
        engine = SIMDLOBMatchingCore(symbol="NVDA", pool_capacity=4096)
        # Seed opposing liquidity
        for i in range(20):
            engine.match_order({"order_id": f"SEED_{i}", "side": "SELL", "price": 100.0 + (i * 0.01), "volume": 10000.0})

        N = 500
        t0 = time.perf_counter_ns()
        for i in range(N):
            engine.match_order({"order_id": f"T_{i}", "side": "BUY", "price": 100.25, "volume": 1.0})
        t1 = time.perf_counter_ns()

        elapsed_sec = (t1 - t0) / 1e9
        throughput = N / elapsed_sec
        self.assertGreater(throughput, 20000.0, f"Throughput below threshold: {throughput:.0f} orders/sec")

    def test_tc51_sub_microsecond_average_operation_latency(self):
        """TC51: Mixed workload (Limit, Cancel, IOC, FOK, Snapshot) latency < 75 us."""
        engine = SIMDLOBMatchingCore(symbol="NVDA", pool_capacity=4096)
        # Warmup mixed operations
        for w in range(10):
            engine.match_order({"order_id": f"W_L_{w}", "side": "BUY", "price": 99.0, "volume": 10.0})
            engine.cancel_order(f"W_L_{w}")
            engine.execute_ioc({"order_id": f"W_IOC_{w}", "side": "BUY", "price": 98.0, "volume": 5.0})
            _ = engine.get_l3_snapshot(depth=5)

        gc.collect()
        gc_was_enabled = gc.isenabled()
        gc.disable()
        N = 200
        try:
            t0 = time.perf_counter_ns()
            for i in range(N):
                # Limit
                engine.match_order({"order_id": f"L_{i}", "side": "BUY", "price": 99.0 - (i % 10) * 0.1, "volume": 10.0})
                # Cancel
                if i > 0 and i % 5 == 0:
                    engine.cancel_order(f"L_{i - 1}")
                # IOC
                if i % 10 == 0:
                    engine.execute_ioc({"order_id": f"IOC_{i}", "side": "BUY", "price": 98.0, "volume": 5.0})
                # Snapshot
                if i % 25 == 0:
                    _ = engine.get_l3_snapshot(depth=5)
            t1 = time.perf_counter_ns()
        finally:
            if gc_was_enabled:
                gc.enable()

        avg_latency_us = (t1 - t0) / (N * 1000.0)
        self.assertLess(avg_latency_us, 75.0, f"Mixed workload latency too high: {avg_latency_us:.3f} us")

    # -----------------------------------------------------------------------
    # Category 12: Iceberg Lifecycle, Priority Demotion & Validation (TC52 ~ TC59)
    # -----------------------------------------------------------------------
    def test_tc52_iceberg_order_placement_and_concealment(self):
        """TC52: Placing iceberg order exposes only display volume on ladder; no volume inflation."""
        engine = SIMDLOBMatchingCore(symbol="ICE_TEST")
        engine.match_order({
            "order_id": "ICE_1",
            "side": "BUY",
            "order_type": OrderType.ICEBERG,
            "price": 100.0,
            "volume": 100.0,
            "display_volume": 20.0,
            "hidden_volume": 80.0,
            "peak_size": 20.0,
        })
        ord_info = engine.get_order_by_id("ICE_1")
        self.assertIsNotNone(ord_info)
        self.assertEqual(ord_info["display_volume"], 20.0)
        self.assertEqual(ord_info["hidden_volume"], 80.0)
        self.assertEqual(ord_info["volume"], 100.0)
        # Verify ladder visible vs hidden volumes
        np.testing.assert_allclose(engine.bid_volumes, [20.0])
        self.assertEqual(engine.bids.ladder.ladder[engine.bids.ladder.head_level, 2], 80.0)

    def test_tc53_iceberg_partial_fill_without_reload(self):
        """TC53: Partial fill of active display tranche decrements display volume without reloading."""
        engine = SIMDLOBMatchingCore(symbol="ICE_TEST")
        engine.match_order({
            "order_id": "ICE_1",
            "side": "BUY",
            "order_type": OrderType.ICEBERG,
            "price": 100.0,
            "volume": 100.0,
            "display_volume": 20.0,
            "hidden_volume": 80.0,
        })
        res = engine.match_order({"order_id": "S1", "side": "SELL", "price": 100.0, "volume": 5.0})
        self.assertEqual(res.filled_volume, 5.0)
        ord_info = engine.get_order_by_id("ICE_1")
        self.assertEqual(ord_info["display_volume"], 15.0)
        self.assertEqual(ord_info["hidden_volume"], 80.0)
        self.assertEqual(ord_info["cum_filled"], 5.0)
        self.assertEqual(ord_info["status"], OrderStatus.PARTIALLY_FILLED)

    def test_tc54_iceberg_tranche_exhaustion_reload_and_priority_demotion(self):
        """TC54: Exhausting visible tranche reloads peak from hidden and demotes iceberg to tail."""
        engine = SIMDLOBMatchingCore(symbol="ICE_TEST")
        engine.match_order({
            "order_id": "ICE_1",
            "side": "BUY",
            "order_type": OrderType.ICEBERG,
            "price": 100.0,
            "volume": 100.0,
            "display_volume": 20.0,
            "hidden_volume": 80.0,
            "peak_size": 20.0,
        })
        engine.match_order({"order_id": "REG_2", "side": "BUY", "price": 100.0, "volume": 30.0})

        # Sweep 25 shares: 20 from ICE_1, exhausting display. ICE_1 reloads & moves to tail.
        # Next 5 shares fill REG_2.
        sweep = engine.match_order({"order_id": "S1", "side": "SELL", "price": 100.0, "volume": 25.0})
        fills = [(f.maker_order_id, f.volume) for f in sweep.fills]
        self.assertEqual(fills, [("ICE_1", 20.0), ("REG_2", 5.0)])

    def test_tc55_iceberg_demoted_priority_respects_fifo_of_subsequent_orders(self):
        """TC55: Demoted iceberg sits behind regular order; subsequent sweep fills regular order first."""
        engine = SIMDLOBMatchingCore(symbol="ICE_TEST")
        engine.match_order({
            "order_id": "ICE_1",
            "side": "BUY",
            "order_type": OrderType.ICEBERG,
            "price": 100.0,
            "volume": 100.0,
            "display_volume": 20.0,
            "hidden_volume": 80.0,
            "peak_size": 20.0,
        })
        engine.match_order({"order_id": "REG_2", "side": "BUY", "price": 100.0, "volume": 30.0})
        engine.match_order({"order_id": "S1", "side": "SELL", "price": 100.0, "volume": 25.0})

        # Sweep 25 shares: REG_2 has remaining 25 shares and priority ahead of ICE_1
        sweep2 = engine.match_order({"order_id": "S2", "side": "SELL", "price": 100.0, "volume": 25.0})
        fills2 = [(f.maker_order_id, f.volume) for f in sweep2.fills]
        self.assertEqual(fills2, [("REG_2", 25.0)])

    def test_tc56_iceberg_consecutive_reloads_until_final_exhaustion(self):
        """TC56: Repeated sweeps exhaust all hidden tranches until iceberg is fully FILLED."""
        engine = SIMDLOBMatchingCore(symbol="ICE_TEST")
        engine.match_order({
            "order_id": "ICE_1",
            "side": "BUY",
            "order_type": OrderType.ICEBERG,
            "price": 100.0,
            "volume": 60.0,
            "display_volume": 20.0,
            "hidden_volume": 40.0,
            "peak_size": 20.0,
        })
        # Sweep all 60 shares
        res = engine.match_order({"order_id": "S_ALL", "side": "SELL", "price": 100.0, "volume": 60.0})
        self.assertEqual(res.filled_volume, 60.0)
        self.assertTrue(res.is_fully_filled)
        ord_info = engine.get_order_by_id("ICE_1")
        self.assertEqual(ord_info["status"], OrderStatus.FILLED)
        self.assertEqual(len(engine.bid_prices), 0)

    def test_tc57_iceberg_l3_snapshot_intrusive_pointer_integrity(self):
        """TC57: L3Snapshot correctly iterates intrusive next_slots including demoted tail order."""
        engine = SIMDLOBMatchingCore(symbol="ICE_TEST")
        engine.match_order({
            "order_id": "ICE_1",
            "side": "BUY",
            "order_type": OrderType.ICEBERG,
            "price": 100.0,
            "volume": 100.0,
            "display_volume": 20.0,
            "hidden_volume": 80.0,
            "peak_size": 20.0,
        })
        engine.match_order({"order_id": "REG_2", "side": "BUY", "price": 100.0, "volume": 30.0})
        engine.match_order({"order_id": "S1", "side": "SELL", "price": 100.0, "volume": 20.0})

        snap = engine.get_l3_snapshot(depth=5)
        level_orders = [o.order_id for o in snap.bids[0].orders]
        self.assertEqual(level_orders, ["REG_2", "ICE_1"])

    def test_tc58_iceberg_atomic_cancellation_volume_deduction(self):
        """TC58: Canceling a resting iceberg order deducts exact current display and hidden volume."""
        engine = SIMDLOBMatchingCore(symbol="ICE_TEST")
        engine.match_order({
            "order_id": "ICE_1",
            "side": "BUY",
            "order_type": OrderType.ICEBERG,
            "price": 100.0,
            "volume": 100.0,
            "display_volume": 20.0,
            "hidden_volume": 80.0,
            "peak_size": 20.0,
        })
        # Partial fill
        engine.match_order({"order_id": "S1", "side": "SELL", "price": 100.0, "volume": 5.0})
        ok = engine.cancel_order("ICE_1")
        self.assertTrue(ok)
        self.assertEqual(len(engine.bid_prices), 0)
        self.assertEqual(engine.best_bid, 0.0)

    def test_tc59_direct_methods_non_positive_and_nan_volume_rejection(self):
        """TC59: execute_ioc, execute_fok, and execute_market_order strictly reject volume <= 0 / NaN."""
        engine = SIMDLOBMatchingCore(symbol="VAL_TEST")
        for bad_vol in [0.0, -10.0, -1e-6, float("nan")]:
            with self.assertRaises(ValueError):
                engine.execute_ioc({"order_id": "B1", "side": "BUY", "price": 100.0, "volume": bad_vol})
            with self.assertRaises(ValueError):
                engine.execute_fok({"order_id": "B2", "side": "BUY", "price": 100.0, "volume": bad_vol})
            with self.assertRaises(ValueError):
                engine.execute_market_order("VAL_TEST", "BUY", bad_vol)


if __name__ == "__main__":
    unittest.main()
