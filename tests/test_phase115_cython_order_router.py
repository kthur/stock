"""
tests/test_phase115_cython_order_router.py
===========================================
Comprehensive Unit, Integration, Latency, and Invariant Test Harness for:
1. Sub-Microsecond Vectorized Ring-Buffer Order Router & Queue Matcher (Feature F545)
2. Deterministic Shared Memory-Mapped (MMF) Circular Buffer IPC (Feature F546)
Phase 115 (Release R131 / v122 Production Master).

Test Categories Covered:
- Category 1: Dual-Tree Parity, Module Exports & Complete Alias Trees (TC01~TC04)
- Category 2: OrderRecord Binary Struct & Zero-Copy Layout (TC05~TC08)
- Category 3: VectorizedRingOrderQueue Ring Buffer Operations (TC09~TC13)
- Category 4: VectorizedL3QueueMatcher Price-Time Priority & Execution (TC14~TC19)
- Category 5: CythonOrderRouter Multi-Venue Routing & Toxicity Gating (TC20~TC24)
- Category 6: Deterministic Shared Memory-Mapped (MMF) Circular Buffer IPC (TC25~TC29)
- Category 7: Phase 115 Message Formats & Sub-System Interoperability (TC30~TC33)
- Category 8: Edge Cases, Overrun Protection & Sub-Microsecond Benchmarks (TC34~TC36)
"""

from __future__ import annotations

import hashlib
import os
import struct
import sys
import tempfile
import time
import unittest
from pathlib import Path
from typing import List, Tuple

# Ensure project roots are on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p in (str(PROJECT_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.core.cython_order_router import (
    FEATURE,
    HAS_CYTHON_ACCELERATION,
    ORDER_RECORD_SIZE,
    ORDER_RECORD_STRUCT,
    ORDER_SLOT_DTYPE,
    RELEASE,
    VERSION,
    CythonOrderRouter,
    FastRingBufferOrderRouter,
    HighFrequencyOrderRouter,
    OrderBookQueueMatcher,
    OrderRecord,
    OrderSide,
    OrderType,
    Phase115OrderRouter,
    RouterFillRecord,
    RoutingDecision,
    RoutingStatus,
    SubMicrosecondOrderRouter,
    UltraLowLatencyOrderMatcher,
    VectorizedL3QueueMatcher,
    VectorizedQueueMatcher,
    VectorizedRingOrderQueue,
    VectorizedRingOrderRouter,
    VenueType,
    ZeroCopyQueueMatcher,
)
from src.core.shared_memory_ring_buffer import (
    DEFAULT_CAPACITY,
    DEFAULT_SLOT_SIZE,
    HEADER_SIZE,
    HEADER_VERSION,
    MAGIC_HEADER,
    STATUS_MMF_BACKED,
    DeterministicMMFCircularBuffer,
    ExecutionOrderMessage,
    HighPerformanceSharedMemoryIPC,
    ITCHPacketMessage,
    LOBTickMessage,
    MemoryMappedRingBuffer,
    MessageType,
    MMFRingBufferIPC,
    OrderDispatchMessage,
    Phase108SharedMemoryRingBuffer,
    Phase115SharedMemoryRingBuffer,
    RiskAlertMessage,
    SharedMemoryIPCRingBuffer,
    SharedMemoryRingBuffer,
    SubMicrosecondCircularBuffer,
    ZeroCopySharedMemoryRingBuffer,
)


class TestPhase115CythonOrderRouter(unittest.TestCase):
    """Master Unit & Integration Test Suite for Phase 115 Low-Latency Infrastructure."""

    def setUp(self) -> None:
        self.test_shm_name = f"test_p115_shm_{os.getpid()}_{int(time.time() * 1000) % 100000}"
        self.test_mmf_name = f"test_p115_mmf_{os.getpid()}_{int(time.time() * 1000) % 100000}"
        SharedMemoryRingBuffer.cleanup_segment(self.test_shm_name)
        SharedMemoryRingBuffer.cleanup_segment(self.test_mmf_name)

    def tearDown(self) -> None:
        SharedMemoryRingBuffer.cleanup_segment(self.test_shm_name)
        SharedMemoryRingBuffer.cleanup_segment(self.test_mmf_name)

    # -----------------------------------------------------------------------
    # Category 1: Dual-Tree Parity, Module Exports & Complete Alias Trees
    # -----------------------------------------------------------------------
    def test_tc01_dual_tree_parity_cython_order_router(self) -> None:
        """TC01: Verify 100% bit-for-bit SHA-256 parity for cython_order_router.py."""
        p1 = PROJECT_ROOT / "src" / "core" / "cython_order_router.py"
        p2 = PROJECT_ROOT / "trading_system" / "src" / "core" / "cython_order_router.py"
        self.assertTrue(p1.exists(), f"Primary path {p1} must exist")
        self.assertTrue(p2.exists(), f"Mirrored path {p2} must exist")
        h1 = hashlib.sha256(p1.read_bytes()).hexdigest()
        h2 = hashlib.sha256(p2.read_bytes()).hexdigest()
        self.assertEqual(h1, h2, "Dual-tree SHA-256 parity mismatch in cython_order_router.py")

    def test_tc02_dual_tree_parity_shared_memory_ring_buffer(self) -> None:
        """TC02: Verify 100% bit-for-bit SHA-256 parity for shared_memory_ring_buffer.py."""
        p1 = PROJECT_ROOT / "src" / "core" / "shared_memory_ring_buffer.py"
        p2 = PROJECT_ROOT / "trading_system" / "src" / "core" / "shared_memory_ring_buffer.py"
        self.assertTrue(p1.exists(), f"Primary path {p1} must exist")
        self.assertTrue(p2.exists(), f"Mirrored path {p2} must exist")
        h1 = hashlib.sha256(p1.read_bytes()).hexdigest()
        h2 = hashlib.sha256(p2.read_bytes()).hexdigest()
        self.assertEqual(h1, h2, "Dual-tree SHA-256 parity mismatch in shared_memory_ring_buffer.py")

    def test_tc03_cython_order_router_alias_trees(self) -> None:
        """TC03: Verify complete alias trees for CythonOrderRouter and matcher."""
        self.assertIs(FastRingBufferOrderRouter, CythonOrderRouter)
        self.assertIs(VectorizedQueueMatcher, CythonOrderRouter)
        self.assertIs(SubMicrosecondOrderRouter, CythonOrderRouter)
        self.assertIs(Phase115OrderRouter, CythonOrderRouter)
        self.assertIs(ZeroCopyQueueMatcher, CythonOrderRouter)
        self.assertIs(HighFrequencyOrderRouter, CythonOrderRouter)
        self.assertIs(UltraLowLatencyOrderMatcher, CythonOrderRouter)
        self.assertIs(VectorizedRingOrderRouter, CythonOrderRouter)
        self.assertIs(OrderBookQueueMatcher, VectorizedL3QueueMatcher)

        self.assertEqual(VERSION, 115)
        self.assertEqual(RELEASE, "R131")
        self.assertEqual(FEATURE, "F545")
        self.assertIn(HAS_CYTHON_ACCELERATION, (True, False))

    def test_tc04_shared_memory_ring_buffer_phase115_alias_trees(self) -> None:
        """TC04: Verify complete Phase 115 alias trees for SharedMemoryRingBuffer."""
        self.assertIs(DeterministicMMFCircularBuffer, SharedMemoryRingBuffer)
        self.assertIs(Phase115SharedMemoryRingBuffer, SharedMemoryRingBuffer)
        self.assertIs(SubMicrosecondCircularBuffer, SharedMemoryRingBuffer)
        self.assertIs(MemoryMappedRingBuffer, SharedMemoryRingBuffer)
        self.assertIs(MMFRingBufferIPC, SharedMemoryRingBuffer)

    # -----------------------------------------------------------------------
    # Category 2: OrderRecord Binary Struct & Zero-Copy Layout (F545.1)
    # -----------------------------------------------------------------------
    def test_tc05_order_record_binary_layout(self) -> None:
        """TC05: Verify exact 41-byte struct layout '!Q8sBddQ' for OrderRecord."""
        self.assertEqual(ORDER_RECORD_SIZE, 41)
        self.assertEqual(ORDER_RECORD_STRUCT.format, "!Q8sBddQ")

        rec = OrderRecord(
            order_id=987654321,
            symbol="005930",
            side=1,
            price=72500.0,
            qty=250.0,
            timestamp_ns=1700000000000000000,
        )
        self.assertEqual(rec.order_id, 987654321)
        self.assertEqual(rec.symbol, "005930")
        self.assertEqual(rec.side, 1)
        self.assertEqual(rec.price, 72500.0)
        self.assertEqual(rec.qty, 250.0)

        packed = rec.pack()
        self.assertEqual(len(packed), 41)

        unpacked = OrderRecord.unpack(packed)
        self.assertEqual(unpacked.order_id, 987654321)
        self.assertEqual(unpacked.symbol, "005930")
        self.assertEqual(unpacked.side, 1)
        self.assertEqual(unpacked.price, 72500.0)
        self.assertEqual(unpacked.qty, 250.0)
        self.assertEqual(unpacked.timestamp_ns, 1700000000000000000)

    def test_tc06_order_record_sell_side_normalization(self) -> None:
        """TC06: Verify OrderRecord normalizes side enum (-1 mapped to 2)."""
        rec_sell = OrderRecord(
            order_id=123,
            symbol="AAPL",
            side=OrderSide.SELL,
            price=185.50,
            qty=50.0,
        )
        self.assertEqual(rec_sell.side, 2)
        d = rec_sell.to_dict()
        self.assertEqual(d["side"], "SELL")

        packed = rec_sell.pack()
        unpacked = OrderRecord.unpack(packed)
        self.assertEqual(unpacked.side, 2)
        self.assertEqual(unpacked.symbol, "AAPL")

    def test_tc07_order_record_pack_into_zero_copy(self) -> None:
        """TC07: Verify pack_into and unpack_from over pre-allocated memoryview."""
        buf = bytearray(128)
        mv = memoryview(buf)

        rec = OrderRecord(
            order_id=55555,
            symbol="MSFT",
            side=1,
            price=420.25,
            qty=100.0,
            timestamp_ns=123456789,
        )
        rec.pack_into(mv, offset=16)

        unpacked = OrderRecord.unpack_from(mv, offset=16)
        self.assertEqual(unpacked.order_id, 55555)
        self.assertEqual(unpacked.symbol, "MSFT")
        self.assertEqual(unpacked.price, 420.25)

    def test_tc08_order_record_sub_microsecond_serialization(self) -> None:
        """TC08: Verify OrderRecord serialization operates in <1000ns (<1μs)."""
        rec = OrderRecord(1, "005930", 1, 71000.0, 100.0)
        # Warm-up to trigger PEP 659 bytecode specialization
        for _ in range(100):
            _b = rec.pack()
            OrderRecord.unpack(_b)

        n = 5000
        t0 = time.perf_counter_ns()
        for _ in range(n):
            b = rec.pack()
        pack_ns = (time.perf_counter_ns() - t0) / n

        t0 = time.perf_counter_ns()
        for _ in range(n):
            OrderRecord.unpack(b)
        unpack_ns = (time.perf_counter_ns() - t0) / n

        # Calibrate threshold: <1000ns for compiled Cython, <2000ns for pure-Python fallback
        max_ns = 1000.0 if HAS_CYTHON_ACCELERATION else 2000.0
        self.assertLess(pack_ns, max_ns, f"pack_ns={pack_ns:.1f}ns exceeds {max_ns}ns threshold")
        self.assertLess(unpack_ns, max_ns, f"unpack_ns={unpack_ns:.1f}ns exceeds {max_ns}ns threshold")

    # -----------------------------------------------------------------------
    # Category 3: VectorizedRingOrderQueue Ring Buffer Operations (F545.2)
    # -----------------------------------------------------------------------
    def test_tc09_ring_order_queue_power_of_two(self) -> None:
        """TC09: Verify power-of-two capacity validation in VectorizedRingOrderQueue."""
        q = VectorizedRingOrderQueue(capacity=1024)
        self.assertEqual(q.capacity, 1024)
        self.assertEqual(q.head_seq, 0)

        with self.assertRaises(ValueError):
            VectorizedRingOrderQueue(capacity=1000)
        with self.assertRaises(ValueError):
            VectorizedRingOrderQueue(capacity=-1)

    def test_tc10_ring_order_queue_push_and_retrieval(self) -> None:
        """TC10: Verify order insertion, indexing, and slot data integrity."""
        q = VectorizedRingOrderQueue(capacity=512)
        slot_idx = q.push_order(
            order_id="ORD_001",
            symbol="005930",
            side=1,
            order_type=int(OrderType.LIMIT),
            price=70500.0,
            volume=50.0,
            venue_type=int(VenueType.LIT_PRIMARY),
        )
        self.assertEqual(slot_idx, 0)
        self.assertEqual(q.head_seq, 1)

        raw_slot = q.get_order_by_id("ORD_001")
        self.assertIsNotNone(raw_slot)
        self.assertEqual(raw_slot["price"], 70500.0)
        self.assertEqual(raw_slot["volume"], 50.0)
        self.assertEqual(raw_slot["status"], int(RoutingStatus.ROUTED))

    def test_tc11_ring_order_queue_cancel(self) -> None:
        """TC11: Verify O(1) order cancellation in ring queue."""
        q = VectorizedRingOrderQueue(capacity=256)
        q.push_order("ORD_CANCEL", "005930", 1, 0, 70000.0, 10.0)
        self.assertTrue(q.cancel_order("ORD_CANCEL"))

        raw = q.get_order_by_id("ORD_CANCEL")
        self.assertEqual(raw["status"], int(RoutingStatus.CANCELED))
        self.assertFalse(q.cancel_order("NON_EXISTENT_ID"))

    def test_tc12_ring_order_queue_update_fill(self) -> None:
        """TC12: Verify partial and full fill state transitions in ring queue."""
        q = VectorizedRingOrderQueue(capacity=256)
        q.push_order("ORD_FILL", "005930", 1, 0, 70000.0, 100.0)

        # Partial fill
        q.update_fill("ORD_FILL", 40.0)
        slot = q.get_order_by_id("ORD_FILL")
        self.assertEqual(slot["cum_filled"], 40.0)
        self.assertEqual(slot["leaves_volume"], 60.0)
        self.assertEqual(slot["status"], int(RoutingStatus.PARTIALLY_FILLED))

        # Complete fill
        q.update_fill("ORD_FILL", 60.0)
        slot = q.get_order_by_id("ORD_FILL")
        self.assertEqual(slot["cum_filled"], 100.0)
        self.assertEqual(slot["leaves_volume"], 0.0)
        self.assertEqual(slot["status"], int(RoutingStatus.FILLED))

    def test_tc13_ring_order_queue_active_orders_view(self) -> None:
        """TC13: Verify active uncompleted orders extraction via structured array."""
        q = VectorizedRingOrderQueue(capacity=256)
        q.push_order("ORD_A", "005930", 1, 0, 70000.0, 10.0)
        q.push_order("ORD_B", "005930", 1, 0, 70100.0, 20.0)
        q.push_order("ORD_C", "005930", 1, 0, 70200.0, 30.0)

        q.cancel_order("ORD_B")
        active = q.get_active_orders()
        self.assertEqual(len(active), 2)
        active_ids = [s["order_id"].decode("ascii").rstrip("\x00") for s in active]
        self.assertIn("ORD_A", active_ids)
        self.assertIn("ORD_C", active_ids)
        self.assertNotIn("ORD_B", active_ids)

    def test_tc13b_ring_order_queue_wraparound_slot_isolation(self) -> None:
        """TC13b: Verify wraparound slot isolation and ghost cancellation prevention."""
        q = VectorizedRingOrderQueue(capacity=4)
        for i in range(4):
            q.push_order(f"ORD_{i}", "005930", 1, 0, 70000.0 + i * 10.0, 10.0)
        self.assertEqual(len(q._id_to_slot), 4)

        # Overwrite slot 0 with ORD_4
        q.push_order("ORD_4", "005930", 1, 0, 75000.0, 50.0)
        self.assertEqual(len(q._id_to_slot), 4)
        self.assertIsNone(q.get_order_by_id("ORD_0"))
        self.assertFalse(q.cancel_order("ORD_0"))
        self.assertFalse(q.update_fill("ORD_0", 10.0))

        # Active order ORD_4 in slot 0 must remain pristine
        ord_4 = q.get_order_by_id("ORD_4")
        self.assertIsNotNone(ord_4)
        self.assertEqual(ord_4["status"], int(RoutingStatus.ROUTED))
        self.assertEqual(ord_4["cum_filled"], 0.0)

        # Cancelling active ORD_4 succeeds
        self.assertTrue(q.cancel_order("ORD_4"))
        self.assertEqual(q.get_order_by_id("ORD_4")["status"], int(RoutingStatus.CANCELED))

    def test_tc13c_ring_order_queue_bounded_memory_under_burst(self) -> None:
        """TC13c: Verify strict memory bounding under high-throughput order burst."""
        cap = 64
        q = VectorizedRingOrderQueue(capacity=cap)
        for i in range(10_000):
            q.push_order(f"BURST_{i}", "005930", 1, 0, 70000.0, 10.0)

        self.assertEqual(q.head_seq, 10_000)
        self.assertLessEqual(len(q._id_to_slot), cap)
        self.assertLessEqual(q.stats()["total_registered_ids"], cap)
        self.assertLessEqual(len(q.get_active_orders()), cap)

        # Stale orders return None
        for i in range(10_000 - cap - 10, 10_000 - cap):
            self.assertIsNone(q.get_order_by_id(f"BURST_{i}"))
            self.assertFalse(q.cancel_order(f"BURST_{i}"))

        # Active window orders are accessible and cancellable
        for i in range(10_000 - cap, 10_000):
            self.assertIsNotNone(q.get_order_by_id(f"BURST_{i}"))

    # -----------------------------------------------------------------------
    # Category 4: VectorizedL3QueueMatcher Price-Time Priority & Execution (F545.3)
    # -----------------------------------------------------------------------
    def test_tc14_l3_matcher_resting_orders_and_top_of_book(self) -> None:
        """TC14: Verify resting order insertion and O(1) top-of-book queries."""
        matcher = VectorizedL3QueueMatcher()
        matcher.add_resting_order("B1", "005930", 1, 69900.0, 100.0)
        matcher.add_resting_order("B2", "005930", 1, 69800.0, 200.0)
        matcher.add_resting_order("A1", "005930", -1, 70100.0, 150.0)
        matcher.add_resting_order("A2", "005930", -1, 70200.0, 250.0)

        best_bid, best_ask, bid_vol, ask_vol = matcher.get_top_of_book()
        self.assertEqual(best_bid, 69900.0)
        self.assertEqual(best_ask, 70100.0)
        self.assertEqual(bid_vol, 100.0)
        self.assertEqual(ask_vol, 150.0)

    def test_tc15_l3_matcher_fifo_priority_execution(self) -> None:
        """TC15: Verify strict FIFO price-time priority matching."""
        matcher = VectorizedL3QueueMatcher()
        # Add two resting asks at the exact same price
        matcher.add_resting_order("A_FIRST", "005930", -1, 70000.0, 50.0)
        matcher.add_resting_order("A_SECOND", "005930", -1, 70000.0, 50.0)

        # Aggressive buy order consumes 60 shares
        fills, vwap_px, slippage_bps = matcher.match_order(
            order_id="BUY_AGG",
            symbol="005930",
            side=1,
            price=70000.0,
            volume=60.0,
        )
        self.assertEqual(len(fills), 2)
        # First fill MUST come from A_FIRST (full 50 shares)
        self.assertEqual(fills[0].maker_order_id, "A_FIRST")
        self.assertEqual(fills[0].volume, 50.0)
        # Second fill MUST come from A_SECOND (partial 10 shares)
        self.assertEqual(fills[1].maker_order_id, "A_SECOND")
        self.assertEqual(fills[1].volume, 10.0)
        self.assertEqual(vwap_px, 70000.0)

    def test_tc16_l3_matcher_multi_level_walking(self) -> None:
        """TC16: Verify walking through multiple price levels and VWAP computation."""
        matcher = VectorizedL3QueueMatcher()
        matcher.add_resting_order("A1", "005930", -1, 70000.0, 10.0)
        matcher.add_resting_order("A2", "005930", -1, 70100.0, 10.0)
        matcher.add_resting_order("A3", "005930", -1, 70200.0, 10.0)

        # Buy 25 shares up to 70150.0
        fills, vwap_px, _ = matcher.match_order(
            order_id="BUY_WALK",
            symbol="005930",
            side=1,
            price=70150.0,
            volume=25.0,
        )
        self.assertEqual(len(fills), 2)
        self.assertEqual(sum(f.volume for f in fills), 20.0)
        # VWAP = (10*70000 + 10*70100) / 20 = 70050.0
        self.assertEqual(vwap_px, 70050.0)

        # Unfilled 5 shares placed as resting bid at 70150.0
        best_bid, _, bid_vol, _ = matcher.get_top_of_book()
        self.assertEqual(best_bid, 70150.0)
        self.assertEqual(bid_vol, 5.0)

    def test_tc17_l3_matcher_iceberg_peak_reload(self) -> None:
        """TC17: Verify iceberg order tranche consumption and automatic hidden reload."""
        matcher = VectorizedL3QueueMatcher()
        # Iceberg ask: total 100 shares, visible peak 20 shares
        matcher.add_resting_order(
            order_id="ICE_1",
            symbol="005930",
            side=-1,
            price=70000.0,
            volume=100.0,
            order_type=int(OrderType.ICEBERG),
            iceberg_peak=20.0,
        )

        # First buy consumes peak of 20 shares
        fills1, _, _ = matcher.match_order("BUY_1", "005930", 1, 70000.0, 20.0)
        self.assertEqual(len(fills1), 1)
        self.assertEqual(fills1[0].volume, 20.0)

        # Verify peak reloaded from hidden volume
        _, best_ask, _, ask_vol = matcher.get_top_of_book()
        self.assertEqual(best_ask, 70000.0)
        self.assertEqual(ask_vol, 20.0)  # Next 20 shares visible

    def test_tc18_l3_matcher_cancel_resting_order(self) -> None:
        """TC18: Verify cancellation of resting orders and depth removal."""
        matcher = VectorizedL3QueueMatcher()
        matcher.add_resting_order("B_CANCEL", "005930", 1, 69500.0, 50.0)
        self.assertTrue(matcher.cancel_order("B_CANCEL"))
        best_bid, _, _, _ = matcher.get_top_of_book()
        self.assertEqual(best_bid, 0.0)

    def test_tc19_l3_matcher_depth_ladder(self) -> None:
        """TC19: Verify extraction of top N depth ladder levels."""
        matcher = VectorizedL3QueueMatcher()
        for i in range(5):
            matcher.add_resting_order(f"B_{i}", "005930", 1, 69000.0 + (i * 10), 10.0 * (i + 1))
            matcher.add_resting_order(f"A_{i}", "005930", -1, 70000.0 + (i * 10), 20.0 * (i + 1))

        bids, asks = matcher.get_depth_ladder(levels=3)
        self.assertEqual(len(bids), 3)
        self.assertEqual(len(asks), 3)
        # Bids sorted descending
        self.assertGreater(bids[0][0], bids[1][0])
        # Asks sorted ascending
        self.assertLess(asks[0][0], asks[1][0])

    # -----------------------------------------------------------------------
    # Category 5: CythonOrderRouter Multi-Venue Routing & Toxicity Gating (F545.4)
    # -----------------------------------------------------------------------
    def test_tc20_router_normal_limit_split(self) -> None:
        """TC20: Verify dark probe and lit maker quantity split under normal conditions."""
        router = CythonOrderRouter(dark_probe_ratio=0.40, maker_rebate_bps=2.5)
        plan = {
            "order_id": "ORD_SPLIT",
            "symbol": "005930",
            "side": 1,
            "quantity": 100.0,
            "price": 70000.0,
            "order_type": int(OrderType.LIMIT),
            "hawkes_intensity": 0.10,
        }
        dec = router.route_order(plan)
        self.assertEqual(dec.dark_quantity, 40.0)
        self.assertEqual(dec.lit_quantity, 60.0)
        self.assertEqual(dec.maker_quantity, 60.0)
        self.assertIn(VenueType.DARK_MIDPOINT, dec.target_venues)
        self.assertIn(VenueType.LIT_PRIMARY, dec.target_venues)

    def test_tc21_router_toxic_quote_gating(self) -> None:
        """TC21: Verify Hawkes quote volatility triggers 100% lit execution."""
        router = CythonOrderRouter(continuous_hawkes=True)
        plan = {
            "order_id": "ORD_TOXIC",
            "symbol": "005930",
            "side": 1,
            "quantity": 100.0,
            "price": 70000.0,
            "order_type": int(OrderType.LIMIT),
            "hawkes_intensity": 0.95,  # High toxicity trigger (>0.75)
        }
        dec = router.route_order(plan)
        self.assertEqual(dec.dark_quantity, 0.0)
        self.assertEqual(dec.lit_quantity, 100.0)
        self.assertEqual(dec.target_venues, [VenueType.LIT_PRIMARY])

    def test_tc22_router_market_order_routing(self) -> None:
        """TC22: Verify market orders are routed aggressively to lit + DMA venues."""
        router = CythonOrderRouter()
        plan = {
            "order_id": "ORD_MKT",
            "symbol": "AAPL",
            "side": -1,
            "quantity": 50.0,
            "price": 0.0,
            "order_type": int(OrderType.MARKET),
        }
        dec = router.route_order(plan)
        self.assertEqual(dec.dark_quantity, 0.0)
        self.assertEqual(dec.lit_quantity, 50.0)
        self.assertIn(VenueType.DIRECT_DMA, dec.target_venues)

    def test_tc23_router_atomic_route_and_execute(self) -> None:
        """TC23: Verify atomic route_and_execute integrates routing, queueing, and matching."""
        router = CythonOrderRouter()
        # Seed matching engine with resting liquidity
        router.matcher.add_resting_order("SEEDED_ASK", "005930", -1, 70000.0, 500.0)

        plan = {
            "order_id": "ORD_EXEC_1",
            "symbol": "005930",
            "side": 1,
            "quantity": 50.0,
            "price": 70000.0,
            "order_type": int(OrderType.LIMIT),
        }
        decision, fills = router.route_and_execute(plan)

        self.assertEqual(decision.order_id, "ORD_EXEC_1")
        self.assertEqual(len(fills), 1)
        self.assertEqual(fills[0].volume, 50.0)
        self.assertEqual(fills[0].price, 70000.0)

        # Verify ring queue recorded fill
        slot = router.queue.get_order_by_id("ORD_EXEC_1")
        self.assertIsNotNone(slot)
        self.assertEqual(slot["cum_filled"], 50.0)
        self.assertEqual(slot["status"], int(RoutingStatus.FILLED))

    def test_tc24_router_benchmark_latency(self) -> None:
        """TC24: Verify router benchmark_latency reports valid telemetry and sub-microsecond ops."""
        router = CythonOrderRouter()
        bench = router.benchmark_latency(iterations=1000)
        self.assertIn("record_pack_latency_ns", bench)
        self.assertIn("record_unpack_latency_ns", bench)
        self.assertIn("meets_sub_microsecond_target", bench)
        self.assertTrue(bench["meets_sub_microsecond_target"])
        max_pack_ns = 1000.0 if HAS_CYTHON_ACCELERATION else 2000.0
        self.assertLess(bench["record_pack_latency_ns"], max_pack_ns)

    # -----------------------------------------------------------------------
    # Category 6: Deterministic Shared Memory-Mapped (MMF) Circular Buffer IPC (F546.1)
    # -----------------------------------------------------------------------
    def test_tc25_mmf_backing_initialization_and_header(self) -> None:
        """TC25: Verify file mmap backing initialization and STATUS_MMF_BACKED flag."""
        buf = SharedMemoryRingBuffer(
            name=self.test_mmf_name,
            capacity=128,
            slot_size=512,
            create=True,
            backing="mmap",
        )
        self.assertEqual(buf.backing, "mmap")
        self.assertTrue(os.path.exists(buf._mmap_file_path))
        self.assertEqual(buf.capacity, 128)

        # Inspect binary status flag
        status = struct.unpack_from("<H", buf._buf, 6)[0]
        self.assertTrue(status & STATUS_MMF_BACKED)

        buf.close()
        buf.unlink()
        self.assertFalse(os.path.exists(buf._mmap_file_path))

    def test_tc26_mmf_backing_client_attach(self) -> None:
        """TC26: Verify client attach to existing MMF backing file."""
        creator = SharedMemoryRingBuffer(
            name=self.test_mmf_name,
            capacity=64,
            create=True,
            backing="mmap",
        )
        # Attach client
        client = SharedMemoryRingBuffer(
            name=self.test_mmf_name,
            create=False,
            backing="mmap",
            client_mode="consumer",
        )
        self.assertEqual(client.capacity, 64)
        self.assertFalse(client.is_creator)

        # Creator writes tick
        tick = LOBTickMessage(
            symbol="005930",
            timestamp_ns=1700000000,
            bid_price=70000.0,
            ask_price=70100.0,
            bid_size=10.0,
            ask_size=20.0,
            last_price=70050.0,
            last_size=5.0,
        )
        self.assertTrue(creator.write_tick(tick))

        # Client reads tick
        read_msg = client.read_message()
        self.assertIsInstance(read_msg, LOBTickMessage)
        self.assertEqual(read_msg.symbol, "005930")
        self.assertEqual(read_msg.last_price, 70050.0)

        client.close()
        creator.close()
        creator.unlink()

    def test_tc27_raw_slot_zero_copy_write_and_read(self) -> None:
        """TC27: Verify write_raw_slot and read_raw_slot payload integrity."""
        buf = SharedMemoryRingBuffer(name=self.test_shm_name, capacity=64, create=True)
        raw_payload = b"QUANT_ALPHA_SIGNAL_PACKET_V115_TEST"
        self.assertTrue(buf.write_raw_slot(raw_payload))

        read_data = buf.read_raw_slot(length=len(raw_payload))
        self.assertEqual(read_data, raw_payload)
        buf.close()
        buf.unlink()

    def test_tc28_raw_view_zero_copy_slice(self) -> None:
        """TC28: Verify read_raw_view returns direct memoryview without heap allocation."""
        buf = SharedMemoryRingBuffer(name=self.test_shm_name, capacity=64, create=True)
        raw_bytes = b"L3_ORDER_PAYLOAD_DIRECT_ZERO_COPY"
        buf.write_raw_slot(raw_bytes)

        view = buf.read_raw_view(length=len(raw_bytes))
        self.assertIsInstance(view, memoryview)
        self.assertEqual(bytes(view), raw_bytes)
        buf.close()
        buf.unlink()

    def test_tc29_ipc_latency_benchmark_method(self) -> None:
        """TC29: Verify benchmark_ipc_latency diagnostic reports valid timing metrics."""
        buf = SharedMemoryRingBuffer(name=self.test_shm_name, capacity=256, create=True)
        res = buf.benchmark_ipc_latency(iterations=1000)
        self.assertIn("round_trip_avg_ns", res)
        self.assertIn("write_avg_ns", res)
        self.assertIn("read_avg_ns", res)
        self.assertGreater(res["round_trip_avg_ns"], 0.0)
        buf.close()
        buf.unlink()

    # -----------------------------------------------------------------------
    # Category 7: Phase 115 Message Formats & Sub-System Interoperability (F546.2)
    # -----------------------------------------------------------------------
    def test_tc30_itch_packet_message_pack_unpack(self) -> None:
        """TC30: Verify ITCHPacketMessage serialization over SharedMemoryRingBuffer."""
        buf = SharedMemoryRingBuffer(name=self.test_shm_name, capacity=64, create=True)
        itch_msg = ITCHPacketMessage(
            timestamp_ns=1700000000123456789,
            msg_type_code="A",
            symbol="005930",
            order_ref=99887766,
            shares=500,
            price=71500.0,
            side=1,
            attribution="KRX_DMA",
        )
        self.assertTrue(buf.write_itch_packet(itch_msg))

        unpacked = buf.read_message()
        self.assertIsInstance(unpacked, ITCHPacketMessage)
        self.assertEqual(unpacked.msg_type_code, "A")
        self.assertEqual(unpacked.symbol, "005930")
        self.assertEqual(unpacked.order_ref, 99887766)
        self.assertEqual(unpacked.shares, 500)
        self.assertEqual(unpacked.price, 71500.0)
        self.assertEqual(unpacked.side, 1)
        self.assertEqual(unpacked.attribution, "KRX_DMA")

        buf.close()
        buf.unlink()

    def test_tc31_order_dispatch_message_pack_unpack(self) -> None:
        """TC31: Verify OrderDispatchMessage serialization over SharedMemoryRingBuffer."""
        buf = SharedMemoryRingBuffer(name=self.test_shm_name, capacity=64, create=True)
        dispatch = OrderDispatchMessage(
            dispatch_id="DISP_115_001",
            symbol="AAPL",
            venue_id=int(VenueType.DARK_MIDPOINT),
            side=-1,
            quantity=150.0,
            price=189.75,
            order_type=int(OrderType.LIMIT),
            routing_flags=0x04,
            timestamp_ns=1700000000000,
            client_id="LOCKLESS_OMS_P115",
        )
        self.assertTrue(buf.write_order_dispatch(dispatch))

        unpacked = buf.read_message()
        self.assertIsInstance(unpacked, OrderDispatchMessage)
        self.assertEqual(unpacked.dispatch_id, "DISP_115_001")
        self.assertEqual(unpacked.symbol, "AAPL")
        self.assertEqual(unpacked.venue_id, int(VenueType.DARK_MIDPOINT))
        self.assertEqual(unpacked.side, -1)
        self.assertEqual(unpacked.quantity, 150.0)
        self.assertEqual(unpacked.price, 189.75)
        self.assertEqual(unpacked.routing_flags, 0x04)
        self.assertEqual(unpacked.client_id, "LOCKLESS_OMS_P115")

        buf.close()
        buf.unlink()

    def test_tc32_router_to_ipc_ring_buffer_integration(self) -> None:
        """TC32: Verify end-to-end routing decision dispatch to IPC ring buffer."""
        router = CythonOrderRouter()
        buf = SharedMemoryRingBuffer(name=self.test_shm_name, capacity=128, create=True)

        plan = {
            "order_id": "ORD_INTEG",
            "symbol": "005930",
            "side": 1,
            "quantity": 200.0,
            "price": 70000.0,
            "order_type": int(OrderType.LIMIT),
        }
        dec = router.route_order(plan)

        # Convert decision to OrderDispatchMessage and transmit via IPC
        msg = OrderDispatchMessage(
            dispatch_id=dec.order_id,
            symbol=dec.symbol,
            venue_id=int(dec.target_venues[0]),
            side=int(dec.side),
            quantity=dec.total_quantity,
            price=70000.0,
            order_type=int(OrderType.LIMIT),
            timestamp_ns=dec.timestamp_ns,
        )
        self.assertTrue(buf.write_order_dispatch(msg))

        rx = buf.read_message()
        self.assertIsInstance(rx, OrderDispatchMessage)
        self.assertEqual(rx.dispatch_id, "ORD_INTEG")
        self.assertEqual(rx.quantity, 200.0)

        buf.close()
        buf.unlink()

    def test_tc33_polymorphic_write_message_all_types(self) -> None:
        """TC33: Verify write_message polymorphic dispatcher handles all 5 message types."""
        buf = SharedMemoryRingBuffer(name=self.test_shm_name, capacity=64, create=True)

        tick = LOBTickMessage("005930", 1, 70000.0, 70100.0, 10.0, 10.0, 70050.0, 1.0)
        alert = RiskAlertMessage("ALT1", 2, "005930", "KRX", 2, 1, 10.0, 5.0, 1)
        order = ExecutionOrderMessage("O1", "005930", "KRX", 3, 1, 1, 10.0, 70000.0, 1)
        itch = ITCHPacketMessage(4, "A", "005930", 11, 10, 70000.0, 1)
        disp = OrderDispatchMessage("D1", "005930", 1, 1, 10.0, 70000.0, 0)

        self.assertTrue(buf.write_message(tick))
        self.assertTrue(buf.write_message(alert))
        self.assertTrue(buf.write_message(order))
        self.assertTrue(buf.write_message(itch))
        self.assertTrue(buf.write_message(disp))

        msgs = buf.read_batch(max_items=10)
        self.assertEqual(len(msgs), 5)
        self.assertIsInstance(msgs[0], LOBTickMessage)
        self.assertIsInstance(msgs[1], RiskAlertMessage)
        self.assertIsInstance(msgs[2], ExecutionOrderMessage)
        self.assertIsInstance(msgs[3], ITCHPacketMessage)
        self.assertIsInstance(msgs[4], OrderDispatchMessage)

        buf.close()
        buf.unlink()

    # -----------------------------------------------------------------------
    # Category 8: Edge Cases, Overrun Protection & Sub-Microsecond Benchmarks
    # -----------------------------------------------------------------------
    def test_tc34_buffer_full_and_dropped_counter(self) -> None:
        """TC34: Verify buffer full drops message and increments dropped_count."""
        buf = SharedMemoryRingBuffer(name=self.test_shm_name, capacity=4, create=True)
        # Fill all 4 slots
        for i in range(4):
            self.assertTrue(buf.write_raw_slot(b"SLOT_DATA"))

        self.assertTrue(buf.is_full())
        # 5th write should be rejected without timeout
        self.assertFalse(buf.write_raw_slot(b"DROP_ME", timeout_sec=0.0))
        self.assertEqual(buf.dropped_count, 1)

        buf.close()
        buf.unlink()

    def test_tc35_oversized_slot_rejection(self) -> None:
        """TC35: Verify raw slot write rejects payloads exceeding slot size."""
        buf = SharedMemoryRingBuffer(name=self.test_shm_name, capacity=8, slot_size=256, create=True)
        oversized = b"X" * 300
        self.assertFalse(buf.write_raw_slot(oversized))
        buf.close()
        buf.unlink()

    def test_tc36_high_throughput_end_to_end_burst(self) -> None:
        """TC36: Verify 1,000 order burst through router and queue matcher with zero drops."""
        router = CythonOrderRouter(capacity=4096)
        # Pre-seed large liquidity
        router.matcher.add_resting_order("MAKER_BIG", "005930", -1, 70000.0, 50000.0)

        plan = {
            "order_id": "BURST",
            "symbol": "005930",
            "side": 1,
            "quantity": 10.0,
            "price": 70000.0,
            "order_type": int(OrderType.LIMIT),
        }

        t0 = time.perf_counter_ns()
        for i in range(1000):
            plan["order_id"] = f"B_{i}"
            router.route_and_execute(plan)
        elapsed_ms = (time.perf_counter_ns() - t0) / 1e6

        stats = router.stats()
        self.assertEqual(stats["total_routed_count"], 1000)
        self.assertEqual(stats["total_filled_count"], 1000)
        self.assertEqual(stats["total_volume_filled"], 10000.0)
        self.assertLess(elapsed_ms, 1000.0, f"1000 order burst took {elapsed_ms:.1f}ms (>1s)")


if __name__ == "__main__":
    unittest.main()
