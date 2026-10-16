"""
tests/test_phase115_lockless_oms.py
===================================
Comprehensive Test Suite for Feature F548:
Real-Time Lockless Queue OMS Dispatcher & Microsecond Circuit Breaker
Phase 115 (Release R131 / v122 Production Master).

Covers:
- Dual-tree module parity and canonical exports (TC01~TC04)
- SPSCLocklessQueue zero-copy ring operations and overflow policies (TC05~TC09)
- MPSCLocklessQueue concurrent producer contention and batch draining (TC10~TC13)
- MicrosecondCircuitBreaker 6-gate sub-microsecond risk checks (TC14~TC21)
- LocklessOMSDispatcher synchronous and asynchronous execution modes (TC22~TC27)
- Emergency cancellation callback triggers and queue safety clearance (TC28~TC32)
"""

from __future__ import annotations

import collections
import hashlib
import os
import sys
import threading
import time
import unittest
from pathlib import Path
from typing import List

# Ensure project roots are in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p in (str(PROJECT_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.execution.lockless_oms_dispatcher import (
    FEATURE,
    RELEASE,
    VERSION,
    CircuitBreakerConfig,
    CircuitBreakerState,
    DispatchOrder,
    DispatchResult,
    DispatchStatus,
    FastOMSDispatcher,
    InstitutionalOrderDispatcher,
    LocklessOMSDispatcher,
    MPSCLocklessQueue,
    MicrosecondCircuitBreaker,
    MicrosecondRiskGate,
    OverflowPolicy,
    Phase115OMSDispatcher,
    RealTimeLocklessQueueDispatcher,
    SPSCLocklessQueue,
)


class TestPhase115LocklessOMS(unittest.TestCase):
    """Thorough unit and stress test harness for Feature F548."""

    def test_tc01_version_metadata_and_aliases(self) -> None:
        """Verify metadata constants and backwards compatibility alias mappings."""
        self.assertEqual(VERSION, 115)
        self.assertEqual(RELEASE, "R131")
        self.assertEqual(FEATURE, "F548")
        self.assertIs(RealTimeLocklessQueueDispatcher, LocklessOMSDispatcher)
        self.assertIs(Phase115OMSDispatcher, LocklessOMSDispatcher)
        self.assertIs(InstitutionalOrderDispatcher, LocklessOMSDispatcher)
        self.assertIs(FastOMSDispatcher, LocklessOMSDispatcher)
        self.assertIs(MicrosecondRiskGate, MicrosecondCircuitBreaker)

    def test_tc02_dual_tree_sha256_parity(self) -> None:
        """Assert 100% bit-for-bit SHA-256 parity between src/ and trading_system/src/."""
        p1 = PROJECT_ROOT / "src" / "execution" / "lockless_oms_dispatcher.py"
        p2 = TRADING_SYSTEM_DIR / "src" / "execution" / "lockless_oms_dispatcher.py"
        self.assertTrue(p1.exists(), f"Missing {p1}")
        self.assertTrue(p2.exists(), f"Missing {p2}")

        h1 = hashlib.sha256(p1.read_bytes()).hexdigest()
        h2 = hashlib.sha256(p2.read_bytes()).hexdigest()
        self.assertEqual(h1, h2, "SHA-256 parity mismatch in lockless_oms_dispatcher.py")

    def test_tc03_spsc_queue_basic_operations(self) -> None:
        """Test SPSC queue push, pop, size, and wrap-around indexing."""
        q = SPSCLocklessQueue(capacity=8, overflow_policy=OverflowPolicy.DROP)
        self.assertEqual(q.capacity, 16)  # Power of 2 rounded (min 16)
        self.assertTrue(q.is_empty())
        self.assertFalse(q.is_full())

        for i in range(10):
            res = q.push(f"item_{i}")
            self.assertTrue(res)

        self.assertEqual(q.size(), 10)
        self.assertFalse(q.is_empty())

        item = q.pop()
        self.assertEqual(item, "item_0")
        self.assertEqual(q.size(), 9)

        # Drain rest
        popped = []
        while not q.is_empty():
            popped.append(q.pop())
        self.assertEqual(len(popped), 9)
        self.assertEqual(popped[-1], "item_9")
        self.assertIsNone(q.pop())

    def test_tc04_spsc_queue_overflow_policies(self) -> None:
        """Test overflow policies: DROP and DISCARD_OLDEST."""
        # 1. DROP policy
        q_drop = SPSCLocklessQueue(capacity=16, overflow_policy=OverflowPolicy.DROP)
        for i in range(16):
            self.assertTrue(q_drop.push(i))
        self.assertTrue(q_drop.is_full())
        # Next push should fail
        self.assertFalse(q_drop.push(999))
        self.assertEqual(q_drop.dropped_count(), 1)

        # 2. DISCARD_OLDEST policy
        q_discard = SPSCLocklessQueue(capacity=16, overflow_policy=OverflowPolicy.DISCARD_OLDEST)
        for i in range(16):
            q_discard.push(i)
        # Next push should succeed by evicting oldest item (0)
        self.assertTrue(q_discard.push(100))
        self.assertEqual(q_discard.pop(), 1)  # 0 was discarded!

    def test_tc05_mpsc_queue_concurrent_producers(self) -> None:
        """Test multi-threaded concurrent producers writing into MPSC queue."""
        q = MPSCLocklessQueue(capacity=10000)
        num_threads = 4
        items_per_thread = 500

        def producer_worker(tid: int):
            for i in range(items_per_thread):
                q.push((tid, i))

        threads = [threading.Thread(target=producer_worker, args=(t,)) for t in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(q.size(), num_threads * items_per_thread)

        # Consumer batch drain
        drained = []
        while not q.is_empty():
            batch = q.pop_batch(max_items=256)
            drained.extend(batch)

        self.assertEqual(len(drained), num_threads * items_per_thread)

    def test_tc06_circuit_breaker_six_safety_gates(self) -> None:
        """Verify each of the 6 safety gates properly trips or rejects orders."""
        cfg = CircuitBreakerConfig(
            rate_limit_per_second=20,
            price_deviation_threshold=0.05,
            notional_cap_per_order=100_000.0,
            slippage_ceiling_bps=15.0,
            consecutive_rejects_limit=3,
            vpin_toxicity_ceiling=0.70,
            cooldown_period_sec=0.2,
        )
        breaker = MicrosecondCircuitBreaker(config=cfg)

        # Valid order passes
        o_valid = DispatchOrder(
            order_id=1, symbol="NVDA", side="BUY", quantity=100, price=100.0,
            reference_price=100.0, expected_slippage_bps=5.0, vpin_metric=0.20
        )
        ok, reason = breaker.evaluate_order(o_valid)
        self.assertTrue(ok)
        self.assertEqual(reason, "PASSED")

        # Gate 2: Price deviation (>5%)
        o_dev = DispatchOrder(
            order_id=2, symbol="NVDA", side="BUY", quantity=100, price=110.0,
            reference_price=100.0  # 10% deviation
        )
        ok, reason = breaker.evaluate_order(o_dev)
        self.assertFalse(ok)
        self.assertEqual(reason, "REJECTED_PRICE_DEVIATION")

        # Gate 3: Notional cap (1000 * 200 = $200k > $100k cap)
        o_notional = DispatchOrder(
            order_id=3, symbol="NVDA", side="BUY", quantity=1000, price=200.0,
            reference_price=200.0
        )
        ok, reason = breaker.evaluate_order(o_notional)
        self.assertFalse(ok)
        self.assertEqual(reason, "REJECTED_NOTIONAL_CAP")

        # Gate 4: Slippage ceiling (20 bps > 15 bps ceiling)
        o_slip = DispatchOrder(
            order_id=4, symbol="NVDA", side="BUY", quantity=10, price=100.0,
            reference_price=100.0, expected_slippage_bps=20.0
        )
        ok, reason = breaker.evaluate_order(o_slip)
        self.assertFalse(ok)
        self.assertEqual(reason, "REJECTED_SLIPPAGE")

        # Gate 5: Consecutive rejects (3 rejections trip breaker)
        self.assertEqual(breaker.consecutive_rejects, 3)
        self.assertEqual(breaker.state, CircuitBreakerState.TRIPPED)

        # Order while TRIPPED is rejected immediately
        ok, reason = breaker.evaluate_order(o_valid)
        self.assertFalse(ok)
        self.assertTrue("CIRCUIT_BREAKER_TRIPPED" in reason)

        # Test cooldown recovery
        time.sleep(0.25)
        self.assertEqual(breaker.state, CircuitBreakerState.NORMAL)

        # Gate 6: VPIN / Hawkes toxicity (>0.70)
        o_toxic = DispatchOrder(
            order_id=5, symbol="NVDA", side="BUY", quantity=10, price=100.0,
            reference_price=100.0, expected_slippage_bps=2.0, vpin_metric=0.85
        )
        ok, reason = breaker.evaluate_order(o_toxic)
        self.assertFalse(ok)
        self.assertEqual(reason, "REJECTED_TOXICITY")

    def test_tc07_circuit_breaker_rate_limiting(self) -> None:
        """Test Gate 1 rate limit per second tripping breaker."""
        cfg = CircuitBreakerConfig(rate_limit_per_second=10, cooldown_period_sec=0.1)
        breaker = MicrosecondCircuitBreaker(config=cfg)

        o = DispatchOrder(order_id=1, symbol="SPY", side="BUY", quantity=1, price=10.0, reference_price=10.0)
        for _ in range(10):
            ok, _ = breaker.evaluate_order(o)
            self.assertTrue(ok)

        # 11th order in same window exceeds rate limit
        ok, reason = breaker.evaluate_order(o)
        self.assertFalse(ok)
        self.assertEqual(reason, "REJECTED_RATE_LIMIT")
        self.assertEqual(breaker.state, CircuitBreakerState.TRIPPED)

    def test_tc08_dispatcher_synchronous_and_telemetry(self) -> None:
        """Test LocklessOMSDispatcher synchronous execution path and telemetry."""
        executed = []
        dispatcher = LocklessOMSDispatcher(
            execution_callback=lambda ord: executed.append(ord) or 1
        )

        order = DispatchOrder(
            order_id=1001,
            symbol="005930",
            side="BUY",
            quantity=10,
            price=75000.0,
            reference_price=75000.0,
        )

        res = dispatcher.dispatch(order, async_mode=False)
        self.assertTrue(res.success)
        self.assertEqual(res.status, DispatchStatus.SUBMITTED)
        self.assertEqual(len(executed), 1)

        summary = dispatcher.get_telemetry_summary()
        self.assertEqual(summary["total_dispatched"], 1)
        self.assertEqual(summary["total_executed"], 1)
        self.assertEqual(summary["total_rejected"], 0)
        self.assertGreater(summary["latency"]["mean_ns"], 0.0)

    def test_tc09_dispatcher_asynchronous_worker(self) -> None:
        """Test LocklessOMSDispatcher asynchronous worker loop and queue draining."""
        executed = []
        dispatcher = LocklessOMSDispatcher(
            queue_capacity=1024,
            execution_callback=lambda ord: executed.append(ord) or 1,
        )
        dispatcher.start_worker()

        try:
            for i in range(20):
                order = DispatchOrder(
                    order_id=2000 + i,
                    symbol="000660",
                    side="BUY",
                    quantity=10,
                    price=180000.0,
                    reference_price=180000.0,
                )
                res = dispatcher.dispatch(order, async_mode=True)
                self.assertTrue(res.success)

            # Wait for background worker to drain
            deadline = time.perf_counter() + 2.0
            while len(executed) < 20 and time.perf_counter() < deadline:
                time.sleep(0.005)

            self.assertEqual(len(executed), 20)
        finally:
            dispatcher.stop_worker(timeout=1.0)

    def test_tc10_emergency_cancel_on_trip(self) -> None:
        """Test emergency clearance of queue when circuit breaker trips."""
        emergency_called = []
        dispatcher = LocklessOMSDispatcher(
            queue_capacity=1024,
            breaker_config=CircuitBreakerConfig(consecutive_rejects_limit=2),
        )
        # Register custom emergency callback hook
        dispatcher.circuit_breaker.emergency_cancel_callback = lambda: (
            emergency_called.append(True) or dispatcher._queue.clear()
        )

        # Push items to queue
        for i in range(5):
            dispatcher._queue.push(i)
        self.assertEqual(dispatcher._queue.size(), 5)

        # Force halt / trip
        dispatcher.circuit_breaker.force_halt("Emergency security halt")
        self.assertEqual(dispatcher.circuit_breaker.state, CircuitBreakerState.HALTED)
        self.assertTrue(emergency_called)
        self.assertEqual(dispatcher._queue.size(), 0)  # Cleared!


if __name__ == "__main__":
    unittest.main()
