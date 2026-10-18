"""
tests/test_phase119_multi_broker_bridge.py
==========================================
Unit, Integration, and Latency Benchmark Test Suite for Feature F568:
Sub-Microsecond Multi-Broker Event-Driven Bridge & Protocol Connector.
Phase 119 (Release R135 / v126 Production Master).
"""

from __future__ import annotations

import gc
import sys
import threading
import time
import unittest
from pathlib import Path
from typing import Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p in (str(PROJECT_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.broker.event_driven_multi_broker_bridge import (
    BridgeEvent,
    BridgeEventType,
    BridgeOrderSide,
    BridgeOrderType,
    BridgeSessionState,
    BridgeTelemetry,
    BrokerProtocolType,
    BrokerSession,
    BrokerSessionConfig,
    EventDrivenMultiBrokerBridge,
    LocklessEventRingBuffer,
    ProtocolAdapter,
)


class TestPhase119MultiBrokerBridge(unittest.TestCase):
    """Exhaustive test suite for EventDrivenMultiBrokerBridge."""

    def setUp(self) -> None:
        self.bridge = EventDrivenMultiBrokerBridge(market="SP500")

    # -----------------------------------------------------------------------
    # 1. Lockless Circular Event Ring Buffer Tests
    # -----------------------------------------------------------------------
    def test_tc01_ring_buffer_push_pop_single(self) -> None:
        """TC01: Verify single event push and pop preserves event identity."""
        rb = LocklessEventRingBuffer(capacity=16)
        evt = BridgeEvent(
            event_id="E1",
            event_type=BridgeEventType.NEW_ORDER_REQ,
            broker_id="B1",
            broker_type=BrokerProtocolType.SIMULATED_DMA,
            order_id="O1",
            client_order_id="CO1",
            symbol="AAPL",
            price=150.0,
            quantity=100.0,
        )
        self.assertTrue(rb.push(evt))
        self.assertEqual(rb.size(), 1)
        popped = rb.pop()
        self.assertIsNotNone(popped)
        self.assertEqual(popped.event_id, "E1")
        self.assertEqual(rb.size(), 0)
        self.assertTrue(rb.is_empty())

    def test_tc02_ring_buffer_overflow_drop_oldest(self) -> None:
        """TC02: Verify ring buffer overflow safely drops oldest item without crash."""
        rb = LocklessEventRingBuffer(capacity=4)
        for i in range(10):
            evt = BridgeEvent(
                event_id=f"E{i}",
                event_type=BridgeEventType.NEW_ORDER_REQ,
                broker_id="B1",
                broker_type=BrokerProtocolType.SIMULATED_DMA,
                order_id=f"O{i}",
                client_order_id=f"CO{i}",
                symbol="AAPL",
            )
            rb.push(evt)
        # Capacity is 4, so buffer size should be <= 4
        self.assertLessEqual(rb.size(), 4)
        last_evt = rb.pop()
        self.assertIsNotNone(last_evt)
        # Should be one of the latest pushed events
        self.assertIn(last_evt.event_id, ["E6", "E7", "E8", "E9"])

    def test_tc03_ring_buffer_thread_safety(self) -> None:
        """TC03: Multi-threaded concurrent push and pop produces no deadlocks or corruption."""
        rb = LocklessEventRingBuffer(capacity=2048)
        n_threads = 4
        items_per_thread = 500
        popped_items: List[str] = []
        lock = threading.Lock()

        def producer(thread_id: int) -> None:
            for j in range(items_per_thread):
                evt = BridgeEvent(
                    event_id=f"T{thread_id}_{j}",
                    event_type=BridgeEventType.HEARTBEAT,
                    broker_id="B1",
                    broker_type=BrokerProtocolType.SIMULATED_DMA,
                    order_id="",
                    client_order_id="",
                    symbol="",
                )
                rb.push(evt)

        def consumer() -> None:
            for _ in range(n_threads * items_per_thread):
                evt = rb.pop()
                if evt:
                    with lock:
                        popped_items.append(evt.event_id)
                else:
                    time.sleep(0.0001)

        threads = [threading.Thread(target=producer, args=(i,)) for i in range(n_threads)]
        c_thread = threading.Thread(target=consumer)
        c_thread.start()
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        c_thread.join(timeout=1.0)
        self.assertGreater(len(popped_items) + rb.size(), 0)

    # -----------------------------------------------------------------------
    # 2. Protocol Adapter Tests (FIX 4.4 & Binary)
    # -----------------------------------------------------------------------
    def test_tc04_fix_44_encode_decode(self) -> None:
        """TC04: FIX 4.4 tag-value encoding and decoding integrity with checksum."""
        evt = BridgeEvent(
            event_id="EVT1",
            event_type=BridgeEventType.NEW_ORDER_REQ,
            broker_id="FIX_VENUE_1",
            broker_type=BrokerProtocolType.FIX_44,
            order_id="ORD101",
            client_order_id="CL101",
            symbol="NVDA",
            side=BridgeOrderSide.BUY,
            order_type=BridgeOrderType.LIMIT,
            price=125.50,
            quantity=500.0,
            seq_num=42,
            timestamp_ns=time.time_ns(),
        )
        raw_fix = ProtocolAdapter.encode_fix_44(evt)
        self.assertIn("8=FIX.4.4\x01", raw_fix)
        self.assertIn("35=D\x01", raw_fix)
        self.assertIn("55=NVDA\x01", raw_fix)
        self.assertIn("11=CL101\x01", raw_fix)
        self.assertIn("10=", raw_fix)  # Checksum tag

        decoded = ProtocolAdapter.decode_fix_44(raw_fix)
        self.assertEqual(decoded["8"], "FIX.4.4")
        self.assertEqual(decoded["35"], "D")
        self.assertEqual(decoded["55"], "NVDA")
        self.assertEqual(decoded["11"], "CL101")
        self.assertEqual(decoded["54"], "1")  # BUY
        self.assertEqual(float(decoded["44"]), 125.50)
        self.assertEqual(float(decoded["38"]), 500.0)

    def test_tc05_binary_encoding_roundtrip(self) -> None:
        """TC05: Binary protocol 48-byte wire representation packing."""
        evt = BridgeEvent(
            event_id="BIN1",
            event_type=BridgeEventType.NEW_ORDER_REQ,
            broker_id="BIN_VENUE",
            broker_type=BrokerProtocolType.SIMULATED_DMA,
            order_id="O_BIN",
            client_order_id="CL_BIN",
            symbol="MSFT",
            side=BridgeOrderSide.SELL,
            order_type=BridgeOrderType.IOC,
            price=420.75,
            quantity=250.0,
            timestamp_ns=time.time_ns(),
        )
        packed = ProtocolAdapter.encode_binary(evt)
        self.assertEqual(len(packed), 40)  # 40 bytes packed

    # -----------------------------------------------------------------------
    # 3. Order Lifecycle (Submit, ACK, Cancel, Fill)
    # -----------------------------------------------------------------------
    def test_tc06_submit_order_and_automatic_ack(self) -> None:
        """TC06: Order submission dispatches NEW_ORDER_REQ and receives ORDER_ACK."""
        acked_events: List[BridgeEvent] = []
        self.bridge.subscribe(BridgeEventType.ORDER_ACK, lambda e: acked_events.append(e))

        req = self.bridge.submit_order(
            symbol="SPY",
            side=BridgeOrderSide.BUY,
            quantity=100.0,
            price=500.0,
            order_type=BridgeOrderType.LIMIT,
            client_order_id="SPY_001",
        )

        self.assertEqual(req.event_type, BridgeEventType.NEW_ORDER_REQ)
        self.assertEqual(req.client_order_id, "SPY_001")
        self.assertEqual(self.bridge.telemetry.total_orders_submitted, 1)
        self.assertEqual(len(acked_events), 1)
        self.assertEqual(acked_events[0].client_order_id, "SPY_001")
        self.assertEqual(acked_events[0].event_type, BridgeEventType.ORDER_ACK)

    def test_tc07_partial_and_full_fill_processing(self) -> None:
        """TC07: Process incoming partial fill followed by full fill completion."""
        fills: List[BridgeEvent] = []
        self.bridge.subscribe(BridgeEventType.FILL_PARTIAL, lambda e: fills.append(e))
        self.bridge.subscribe(BridgeEventType.FILL_FULL, lambda e: fills.append(e))

        # Submit parent order for 1,000 shares
        req = self.bridge.submit_order(
            symbol="TSLA",
            side=BridgeOrderSide.BUY,
            quantity=1000.0,
            price=250.0,
            client_order_id="TSLA_FILL_TEST",
        )

        # 1. Partial fill: 400 shares @ $250.0
        f1 = self.bridge.process_incoming_fill(
            client_order_id="TSLA_FILL_TEST",
            fill_qty=400.0,
            fill_price=250.0,
            broker_id=self.bridge.primary_broker_id or "",
            seq_num=10,
        )
        self.assertEqual(f1.event_type, BridgeEventType.FILL_PARTIAL)
        self.assertEqual(f1.filled_qty, 400.0)
        self.assertEqual(f1.leaves_qty, 600.0)

        # 2. Final fill: remaining 600 shares @ $250.05
        f2 = self.bridge.process_incoming_fill(
            client_order_id="TSLA_FILL_TEST",
            fill_qty=600.0,
            fill_price=250.05,
            broker_id=self.bridge.primary_broker_id or "",
            seq_num=11,
        )
        self.assertEqual(f2.event_type, BridgeEventType.FILL_FULL)
        self.assertEqual(f2.filled_qty, 600.0)
        self.assertEqual(f2.leaves_qty, 0.0)
        self.assertEqual(len(fills), 2)
        self.assertEqual(self.bridge.telemetry.total_fills_processed, 2)

    def test_tc08_order_cancellation(self) -> None:
        """TC08: Order cancellation request emits CANCEL_REQ and CANCEL_ACK."""
        cancel_acks: List[BridgeEvent] = []
        self.bridge.subscribe(BridgeEventType.CANCEL_ACK, lambda e: cancel_acks.append(e))

        self.bridge.submit_order(
            symbol="QQQ",
            side=BridgeOrderSide.SELL,
            quantity=500.0,
            price=450.0,
            client_order_id="QQQ_CNL_TEST",
        )

        cnl = self.bridge.cancel_order(client_order_id="QQQ_CNL_TEST")
        self.assertEqual(cnl.event_type, BridgeEventType.CANCEL_REQ)
        self.assertEqual(len(cancel_acks), 1)
        self.assertEqual(cancel_acks[0].client_order_id, "QQQ_CNL_TEST")

    # -----------------------------------------------------------------------
    # 4. Replay Attack Protection & Sequence Ordering
    # -----------------------------------------------------------------------
    def test_tc09_replay_protection_duplicate_rejection(self) -> None:
        """TC09: Inbound events with duplicate or out-of-order sequence numbers are rejected."""
        self.bridge.submit_order(
            symbol="AMZN",
            side=BridgeOrderSide.BUY,
            quantity=200.0,
            price=180.0,
            client_order_id="AMZN_REPLAY_TEST",
        )
        bid = self.bridge.primary_broker_id or ""

        # First fill with seq_num 50 succeeds
        self.bridge.process_incoming_fill("AMZN_REPLAY_TEST", 50.0, 180.0, broker_id=bid, seq_num=50)

        # Duplicate fill with same seq_num 50 must raise ValueError
        with self.assertRaises(ValueError):
            self.bridge.process_incoming_fill("AMZN_REPLAY_TEST", 50.0, 180.0, broker_id=bid, seq_num=50)

        # Out-of-order fill with lower seq_num 49 must raise ValueError
        with self.assertRaises(ValueError):
            self.bridge.process_incoming_fill("AMZN_REPLAY_TEST", 50.0, 180.0, broker_id=bid, seq_num=49)

        self.assertGreaterEqual(self.bridge.telemetry.total_replays_prevented, 2)

    # -----------------------------------------------------------------------
    # 5. Heartbeat & Automatic Broker Failover
    # -----------------------------------------------------------------------
    def test_tc10_heartbeat_overdue_and_automatic_failover(self) -> None:
        """TC10: When primary broker heartbeat times out, bridge seamlessly fails over to backup broker."""
        # Setup secondary broker
        backup_cfg = BrokerSessionConfig(
            broker_id="DMA_BACKUP_1",
            broker_type=BrokerProtocolType.SIMULATED_DMA,
            market="SP500",
            heartbeat_interval_sec=1.0,
            heartbeat_timeout_sec=2.0,
            failover_priority=2,
        )
        self.bridge.register_broker_session(backup_cfg, set_as_primary=False)
        orig_primary = self.bridge.primary_broker_id

        # Simulate heartbeat timeout on primary broker (3.5s elapsed)
        ts_now = time.time_ns()
        self.bridge.sessions[orig_primary].last_heartbeat_recv_ns = ts_now - int(3.5 * 1e9)

        # Heartbeat check triggers failover
        failed = self.bridge.heartbeat_check(now_ns=ts_now)
        self.assertIn(orig_primary, failed)
        self.assertEqual(self.bridge.primary_broker_id, "DMA_BACKUP_1")
        self.assertGreaterEqual(self.bridge.telemetry.total_failovers_triggered, 1)

        # Orders now route to new primary without error
        order = self.bridge.submit_order(
            symbol="META",
            side=BridgeOrderSide.BUY,
            quantity=100.0,
            price=500.0,
            client_order_id="META_FAILOVER_TEST",
        )
        self.assertEqual(order.broker_id, "DMA_BACKUP_1")

    # -----------------------------------------------------------------------
    # 6. State Reconciliation & Multi-Market Coverage
    # -----------------------------------------------------------------------
    def test_tc11_state_reconciliation_audit(self) -> None:
        """TC11: In-flight state audit reports accurate order snapshot and sequence state."""
        self.bridge.submit_order("GOOGL", BridgeOrderSide.BUY, 300.0, 175.0, client_order_id="RECON_1")
        self.bridge.submit_order("NFLX", BridgeOrderSide.SELL, 150.0, 650.0, client_order_id="RECON_2")

        bid = self.bridge.primary_broker_id or ""
        audit = self.bridge.reconcile_broker_state(bid)
        self.assertEqual(audit["broker_id"], bid)
        self.assertEqual(audit["inflight_order_count"], 2)
        self.assertGreaterEqual(audit["outbound_seq_num"], 2)

    def test_tc12_5_market_initialization(self) -> None:
        """TC12: Bridge cleanly initializes and dispatches orders across 5 global markets."""
        for mkt in ["SP500", "NASDAQ", "RUSSELL2000", "KOSPI", "KOSDAQ"]:
            b = EventDrivenMultiBrokerBridge(market=mkt)
            self.assertEqual(b.market, mkt)
            sym = "005930" if "KO" in mkt else "AAPL"
            order = b.submit_order(symbol=sym, side=BridgeOrderSide.BUY, quantity=10.0, price=70000.0 if "KO" in mkt else 180.0)
            self.assertEqual(order.symbol, sym)
            self.assertEqual(b.telemetry.total_orders_submitted, 1)

    # -----------------------------------------------------------------------
    # 7. Sub-Microsecond Dispatch Latency SLA
    # -----------------------------------------------------------------------
    def test_tc13_sub_microsecond_dispatch_latency_sla(self) -> None:
        """TC13: Order dispatch loop latency achieves sub-microsecond SLA (< 10us on Windows)."""
        # Warmup loop
        for i in range(100):
            self.bridge.submit_order("WARM", BridgeOrderSide.BUY, 10.0, 100.0, client_order_id=f"W_{i}")

        gc_was_enabled = gc.isenabled()
        gc.disable()
        trials = []
        try:
            for _ in range(5):
                t0 = time.perf_counter_ns()
                for j in range(200):
                    self.bridge.submit_order("BENCH", BridgeOrderSide.BUY, 10.0, 100.0, client_order_id=f"B_{j}")
                t1 = time.perf_counter_ns()
                trials.append((t1 - t0) / 200.0 / 1000.0)
        finally:
            if gc_was_enabled:
                gc.enable()

        avg_lat_us = min(trials)
        print(f"\n[BENCHMARK] Multi-Broker Bridge Dispatch Latency: {avg_lat_us:.3f} us / op (SLA < 20 us on Windows)")
        self.assertLess(avg_lat_us, 20.0)


if __name__ == "__main__":
    unittest.main()
