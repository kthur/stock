"""
tests/test_phase115_adversarial_challenger2.py
=============================================
Empirical Adversarial Challenge Test Suite for Milestone 1:
- Sub-Microsecond Vectorized Ring-Buffer Order Router & L3 Queue Matcher (Feature F545)
- Deterministic Shared Memory-Mapped Circular Buffer IPC (Feature F546)
Phase 115 (Release R131 / v122 Production Master).

Auditor: challenger_phase115_m1_2 (Empirical Challenger)
Focus Areas:
1. L3 price-time priority matching correctness under complex execution traces
   (icebergs, partial fills, cancels, priority inversion).
2. VectorizedRingOrderQueue buffer overflow, slot aliasing, and ghost cancellation.
3. SharedMemoryRingBuffer SPSC FIFO order conservation and zero-copy view hazards.
"""

from __future__ import annotations

import os
import struct
import sys
import threading
import time
import unittest
from pathlib import Path
from typing import List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p in (str(PROJECT_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.core.cython_order_router import (
    CythonOrderRouter,
    OrderRecord,
    OrderSide,
    OrderType,
    RoutingStatus,
    VectorizedL3QueueMatcher,
    VectorizedRingOrderQueue,
    VenueType,
)
from src.core.shared_memory_ring_buffer import (
    LOBTickMessage,
    MessageType,
    SharedMemoryRingBuffer,
)


class TestPhase115AdversarialChallenger2(unittest.TestCase):
    """Adversarial stress and correctness test suite for Milestone 1."""

    def setUp(self) -> None:
        self.shm_name = f"test_adv_shm_{os.getpid()}_{int(time.time() * 1000) % 100000}"
        SharedMemoryRingBuffer.cleanup_segment(self.shm_name)

    def tearDown(self) -> None:
        SharedMemoryRingBuffer.cleanup_segment(self.shm_name)

    # -----------------------------------------------------------------------
    # Challenge 1: L3 Price-Time Priority Violation on Iceberg Tranche Reload
    # -----------------------------------------------------------------------
    def test_adv01_iceberg_fifo_priority_violation_order_skipped(self) -> None:
        """
        ADV-01: Verify price-time priority when an iceberg order exhausts its visible peak.
        
        Scenario:
        1. ICE_1 (ASK at 70000.0, volume=100.0, peak=20.0) arrives first (priority 1).
        2. LIMIT_2 (ASK at 70000.0, volume=50.0) arrives second (priority 2).
        3. Aggressive BUY order arrives for 40.0 shares at 70000.0.

        Exchange Price-Time Priority Invariant:
        - First 20.0 shares MUST match ICE_1 (exhausting visible peak).
        - ICE_1 peak is exhausted; it reloads 20.0 from hidden volume and MUST be
          moved to the BACK of the queue (priority 3 > priority 2).
        - Second 20.0 shares MUST match LIMIT_2 (priority 2 < priority 3).
        - LIMIT_2 must have 30.0 leaves remaining.
        - ICE_1 must have 20.0 visible leaves and 60.0 hidden remaining.

        Vulnerability Found in VectorizedL3QueueMatcher:
        - In match_order (lines 590-600), when maker is ICEBERG and reloads:
          queue.sort(key=lambda o: o.priority_seq) is called.
          However, the loop does NOT execute 'continue' and falls through to 'i += 1'.
          Because ICE_1 moved to the end, the element at index 1 shifted to index 0.
          The loop then advances to i=1, skipping the higher-priority LIMIT_2 at index 0!
          ICE_1 at index 1 is matched a SECOND time ahead of LIMIT_2!
        """
        matcher = VectorizedL3QueueMatcher()
        matcher.add_resting_order(
            order_id="ICE_1",
            symbol="005930",
            side=-1,
            price=70000.0,
            volume=100.0,
            order_type=int(OrderType.ICEBERG),
            iceberg_peak=20.0,
        )
        matcher.add_resting_order(
            order_id="LIMIT_2",
            symbol="005930",
            side=-1,
            price=70000.0,
            volume=50.0,
            order_type=int(OrderType.LIMIT),
        )

        fills, _, _ = matcher.match_order(
            order_id="TAKER_BUY",
            symbol="005930",
            side=1,
            price=70000.0,
            volume=40.0,
        )

        # Expected fills under Price-Time Priority:
        # Fill 0: ICE_1 for 20.0
        # Fill 1: LIMIT_2 for 20.0
        self.assertEqual(len(fills), 2, "Expected exactly 2 fills for 40 shares")
        self.assertEqual(fills[0].maker_order_id, "ICE_1")
        self.assertEqual(fills[0].volume, 20.0)

        # CRITICAL ADVERSARIAL ASSERTION:
        # Second fill MUST be LIMIT_2. If this fails, price-time priority is violated!
        self.assertEqual(
            fills[1].maker_order_id,
            "LIMIT_2",
            f"Price-Time Priority Violated! Second fill matched '{fills[1].maker_order_id}' instead of 'LIMIT_2'.",
        )
        self.assertEqual(fills[1].volume, 20.0)

        limit_2_order = matcher._orders_by_id["LIMIT_2"]
        self.assertEqual(
            limit_2_order.leaves_volume,
            30.0,
            f"LIMIT_2 leaves should be 30.0, got {limit_2_order.leaves_volume}",
        )

    def test_adv02_iceberg_priority_inversion_among_third_party_orders(self) -> None:
        """
        ADV-02: Verify that iceberg reload does not invert FIFO priority between
        multiple other resting limit orders.

        Scenario:
        1. ICE_1 (ASK 70000.0, vol=40, peak=10) -> seq 1
        2. LIMIT_A (ASK 70000.0, vol=10) -> seq 2
        3. LIMIT_B (ASK 70000.0, vol=10) -> seq 3
        Queue order: [ICE_1, LIMIT_A, LIMIT_B]

        Taker BUY for 20.0 shares arrives.
        Expected fills:
        - Fill 0: ICE_1 for 10.0 (exhausts peak)
        - Fill 1: LIMIT_A for 10.0 (LIMIT_A has priority seq 2 < LIMIT_B seq 3)

        Vulnerability:
        - When ICE_1 reloads, it sorts to the back: [LIMIT_A, LIMIT_B, ICE_1].
        - But i += 1 increments i from 0 to 1!
        - queue[1] is LIMIT_B!
        - LIMIT_B (seq 3) matches, while LIMIT_A (seq 2) is completely skipped!
        """
        matcher = VectorizedL3QueueMatcher()
        matcher.add_resting_order(
            "ICE_1", "005930", -1, 70000.0, 40.0,
            order_type=int(OrderType.ICEBERG), iceberg_peak=10.0,
        )
        matcher.add_resting_order("LIMIT_A", "005930", -1, 70000.0, 10.0, order_type=int(OrderType.LIMIT))
        matcher.add_resting_order("LIMIT_B", "005930", -1, 70000.0, 10.0, order_type=int(OrderType.LIMIT))

        fills, _, _ = matcher.match_order("BUY_20", "005930", 1, 70000.0, 20.0)
        self.assertEqual(len(fills), 2)
        self.assertEqual(fills[0].maker_order_id, "ICE_1")
        self.assertEqual(fills[0].volume, 10.0)

        # LIMIT_A arrived before LIMIT_B, so LIMIT_A MUST fill before LIMIT_B!
        self.assertEqual(
            fills[1].maker_order_id,
            "LIMIT_A",
            f"Third-party order priority inverted! '{fills[1].maker_order_id}' was filled before 'LIMIT_A'.",
        )

    def test_adv03_sell_side_iceberg_fifo_priority_violation(self) -> None:
        """
        ADV-03: Verify price-time priority on the Bid side (taker SELL against resting Bids).
        Lines 649-660 suffer from the exact same 'i += 1' skip bug.
        """
        matcher = VectorizedL3QueueMatcher()
        matcher.add_resting_order(
            "ICE_BID", "005930", 1, 70000.0, 100.0,
            order_type=int(OrderType.ICEBERG), iceberg_peak=20.0,
        )
        matcher.add_resting_order("LIMIT_BID", "005930", 1, 70000.0, 50.0, order_type=int(OrderType.LIMIT))

        fills, _, _ = matcher.match_order("TAKER_SELL", "005930", -1, 70000.0, 40.0)
        self.assertEqual(len(fills), 2)
        self.assertEqual(fills[0].maker_order_id, "ICE_BID")
        self.assertEqual(fills[0].volume, 20.0)

        self.assertEqual(
            fills[1].maker_order_id,
            "LIMIT_BID",
            f"Bid-side Price-Time Priority Violated! Matched '{fills[1].maker_order_id}' instead of 'LIMIT_BID'.",
        )

    # -----------------------------------------------------------------------
    # Challenge 2: Aggressive Iceberg Unfilled Rest & Order Confidentiality
    # -----------------------------------------------------------------------
    def test_adv04_aggressive_iceberg_rest_loses_hidden_peak(self) -> None:
        """
        ADV-04: Verify that an unfilled aggressive ICEBERG order preserves its hidden/peak parameters
        when it rests on the book.

        Vulnerability:
        In match_order lines 673-686:
            if leaves > 1e-9 and order_type in (LIMIT, ICEBERG, PRIMARY_PEG):
                self.add_resting_order(
                    order_id=order_id,
                    symbol=symbol,
                    side=side,
                    price=price,
                    volume=leaves,
                    order_type=order_type,
                    timestamp_ns=ts,
                )
        Notice that iceberg_peak is NEVER passed! It defaults to 0.0.
        Therefore, add_resting_order sets visible_vol = leaves, hidden_volume = 0.0.
        The entire remaining volume of the iceberg order is publicly revealed on the depth ladder!
        """
        matcher = VectorizedL3QueueMatcher()
        # Seed 10 shares of resting ask
        matcher.add_resting_order("SEED_ASK", "005930", -1, 70000.0, 10.0)

        # Taker sends ICEBERG BUY: total 100 shares, peak 20 shares at 70000.0
        # match_order does not even accept iceberg_peak parameter!
        fills, _, _ = matcher.match_order(
            order_id="ICE_TAKER",
            symbol="005930",
            side=1,
            price=70000.0,
            volume=100.0,
            order_type=int(OrderType.ICEBERG),
        )
        self.assertEqual(len(fills), 1)
        self.assertEqual(fills[0].volume, 10.0)

        # 90 shares now rest on the book as a bid at 70000.0
        best_bid, _, bid_vol, _ = matcher.get_top_of_book()
        self.assertEqual(best_bid, 70000.0)

        resting_ice = matcher._orders_by_id.get("ICE_TAKER")
        self.assertIsNotNone(resting_ice)

        # An iceberg order with total 90 remaining and peak 20 should only show 20 on top of book!
        # If it shows 90, the iceberg confidentiality contract is broken.
        self.assertLessEqual(
            bid_vol,
            20.0,
            f"Iceberg confidentiality broken! Expected top-of-book visible volume <= 20.0, got {bid_vol}",
        )

    # -----------------------------------------------------------------------
    # Challenge 3: VectorizedRingOrderQueue Overrun, Aliasing & Ghost Cancels
    # -----------------------------------------------------------------------
    def test_adv05_vectorized_ring_queue_silent_overwrite_ghost_cancel(self) -> None:
        """
        ADV-05: Verify VectorizedRingOrderQueue behavior when pushed beyond capacity.
        
        Vulnerability:
        In push_order:
            slot_idx = self._head_seq & self._mask
            self._id_to_slot[order_id] = slot_idx
            self._head_seq += 1
        1. Capacity is never checked against tail_seq or active orders.
        2. Older orders are silently overwritten without updating or evicting _id_to_slot.
        3. Calling get_order_by_id(old_order_id) returns the NEW order's slot data.
        4. Calling cancel_order(old_order_id) or update_fill(old_order_id) mutates the NEW order!
        """
        q = VectorizedRingOrderQueue(capacity=4)
        for i in range(4):
            q.push_order(f"ORD_{i}", "AAPL", 1, 0, 100.0 + i, 10.0)

        # Push 5th order, wrapping around and overwriting slot 0 (where ORD_0 was)
        q.push_order("ORD_4", "AAPL", 1, 0, 999.0, 50.0)

        # Check get_order_by_id for evicted order
        slot_0 = q.get_order_by_id("ORD_0")
        self.assertIsNone(slot_0, "Evicted order ORD_0 must return None and not corrupt slot 0 lookup")

        # Ghost cancellation hazard:
        # Cancel the evicted order ORD_0
        cancelled = q.cancel_order("ORD_0")
        self.assertFalse(cancelled, "Cancelling evicted ORD_0 must return False")
        slot_4 = q.get_order_by_id("ORD_4")
        self.assertIsNotNone(slot_4)
        status_4 = slot_4["status"]

        # Ghost cancellation prevented: ORD_4 remains in active ROUTED status
        self.assertNotEqual(
            status_4,
            int(RoutingStatus.CANCELED),
            "Ghost cancellation bug! Cancelling evicted ORD_0 corrupted the status of active order ORD_4!",
        )
        self.assertEqual(status_4, int(RoutingStatus.ROUTED), "ORD_4 must remain in active ROUTED status")

    # -----------------------------------------------------------------------
    # Challenge 4: SharedMemoryRingBuffer SPSC FIFO Order Conservation
    # -----------------------------------------------------------------------
    def test_adv06_shared_memory_spsc_fifo_order_conservation(self) -> None:
        """
        ADV-06: Stress test SharedMemoryRingBuffer under rapid enqueue/dequeue cycles (5,000 items)
        across concurrent threads to verify strict FIFO ordering and zero data torn reads.
        """
        buf_prod = SharedMemoryRingBuffer(name=self.shm_name, capacity=64, create=True)
        buf_cons = SharedMemoryRingBuffer(name=self.shm_name, create=False, client_mode="consumer")

        n_items = 5000
        errors: List[str] = []

        def producer_worker():
            for i in range(n_items):
                msg = LOBTickMessage(
                    symbol=f"SYM_{i % 50}",
                    timestamp_ns=i,
                    bid_price=1000.0 + (i * 0.1),
                    ask_price=1001.0 + (i * 0.1),
                    bid_size=float(i % 100 + 1),
                    ask_size=float(i % 100 + 1),
                    last_price=1000.5 + (i * 0.1),
                    last_size=1.0,
                )
                while not buf_prod.write_tick(msg, timeout_sec=0.005):
                    time.sleep(0.00001)

        def consumer_worker():
            received = 0
            while received < n_items:
                msg = buf_cons.read_message(timeout_sec=0.005)
                if msg is not None:
                    if msg.timestamp_ns != received:
                        errors.append(f"Sequence mismatch: expected {received}, got {msg.timestamp_ns}")
                    expected_px = 1000.0 + (received * 0.1)
                    if abs(msg.bid_price - expected_px) > 1e-6:
                        errors.append(f"Torn read at {received}: expected {expected_px}, got {msg.bid_price}")
                    received += 1

        t_prod = threading.Thread(target=producer_worker)
        t_cons = threading.Thread(target=consumer_worker)
        t_prod.start()
        t_cons.start()
        t_prod.join(timeout=10)
        t_cons.join(timeout=10)

        self.assertEqual(len(errors), 0, f"SPSC FIFO errors encountered: {errors[:5]}")
        self.assertEqual(buf_cons.total_read, n_items)

        buf_prod.close()
        buf_prod.unlink()
        buf_cons.close()

    # -----------------------------------------------------------------------
    # Challenge 5: Zero-Copy read_raw_view Buffer Wrap Hazard
    # -----------------------------------------------------------------------
    def test_adv07_shared_memory_read_raw_view_wrap_hazard(self) -> None:
        """
        ADV-07: Verify whether read_raw_view premature slot commit allows subsequent
        producer writes to overwrite data while the consumer holds the memoryview.
        
        Mechanism:
        In read_raw_view:
            view = self._buf[slot_offset : slot_offset + msg_len]
            # Commit read immediately:
            struct.pack_into("<Q", self._buf, OFFSET_TAIL_SEQ, tail + 1)
            return view
        Because tail_seq is incremented BEFORE the caller processes the returned view,
        a fast producer can immediately wrap around and overwrite that exact slot memory!
        """
        buf = SharedMemoryRingBuffer(name=self.shm_name, capacity=4, slot_size=256, create=True)

        payload_1 = b"ORIGINAL_PAYLOAD_PACKET_A_12345"
        buf.write_raw_slot(payload_1)

        # Consumer gets zero-copy view of slot 0
        view = buf.read_raw_view()
        self.assertIsNotNone(view)
        self.assertEqual(bytes(view[:len(payload_1)]), payload_1)

        # Because tail_seq was committed, buffer appears to have capacity
        # Now producer writes 4 more items, wrapping around to slot 0:
        for i in range(4):
            buf.write_raw_slot(f"OVERWRITTEN_PAYLOAD_{i}".encode("ascii"))

        # Check what happened to consumer's view:
        current_data = bytes(view[:len(payload_1)])
        # If current_data has been altered by the producer, the zero-copy view was torn!
        is_torn = (current_data != payload_1)
        self.assertTrue(
            is_torn,
            "Documented memoryview hazard: caller's view was overwritten because tail was committed prematurely",
        )

        buf.close()
        buf.unlink()


if __name__ == "__main__":
    unittest.main()
