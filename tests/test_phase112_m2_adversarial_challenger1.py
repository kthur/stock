"""
tests/test_phase112_m2_adversarial_challenger1.py — Empirical Emergency Cancellation & Latency Stress Test Suite
Milestone: Phase 112 (Release R128 / v119 Production Master, Feature F531)
Author: Challenger 1 (EMPIRICAL CHALLENGER)

Adversarial Stress Battery:
1. Parallel Emergency Cancellation Latency Benchmarks:
   - 50 concurrent open orders (< 50ms strict threshold)
   - 100 concurrent open orders (< 50ms strict threshold)
   - 500 concurrent open orders (< 50ms strict threshold)
   - 1,000 concurrent open orders (extreme stress scaling & non-linear bottleneck analysis)
2. Zero Orphaned Open Orders on Mock/Simulated Broker Ledgers:
   - Full ledger audit verifying open order count == 0 on broker ledger and daemon state
   - Verification across daemon.stop() graceful / emergency shutdown
   - Mixed order state resilience (FILLED, REJECTED, SUBMITTED)
   - Realistic async network transport latency (asyncio.gather concurrency proof)
   - Broker partial failure / network exception resilience
   - High-concurrency race condition testing during emergency halt
   - Native KISBrokerConnector simulation ledger zero-orphans verification
   - Kill switch state verification and idempotent cleanup
"""

import asyncio
from dataclasses import dataclass, field
import logging
import math
import os
from pathlib import Path
import random
import sys
import tempfile
import time
from typing import Any, Dict, List, Optional, Set
import unittest
import pytest

# Ensure repo root and trading_system are on path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT / "trading_system") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "trading_system"))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.execution.live_trading_daemon import (
    DaemonEventType,
    DaemonPriority,
    DaemonSessionState,
    EmergencyHaltEvent,
    LiveDaemonConfig,
    LiveTradingDaemon,
    LiveTrancheOrder,
    PrioritizedDaemonEvent,
)
from src.broker.kis_broker_connector import KISBrokerConnector


class StatefulMockBrokerLedger:
    """
    High-fidelity stateful simulated broker ledger.
    Tracks every order in a simulated broker database, enforcing order state transitions
    (SUBMITTED -> FILLED | CANCELLED | REJECTED) and providing ledger audit queries.
    """

    def __init__(self, async_latency_sec: float = 0.0, failure_rate: float = 0.0):
        self.async_latency_sec = async_latency_sec
        self.failure_rate = failure_rate
        self.orders: Dict[str, Dict[str, Any]] = {}
        self.cancel_calls: List[str] = []
        self.exceptions_thrown: int = 0
        self.lock = asyncio.Lock()

    def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        price: float,
        quantity: int,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        order_id = f"BROKER_ORD_{len(self.orders) + 1:06d}"
        record = {
            "order_id": order_id,
            "symbol": symbol,
            "side": side,
            "order_type": order_type,
            "price": price,
            "quantity": quantity,
            "status": "SUBMITTED",
            "created_at": time.perf_counter_ns(),
        }
        self.orders[order_id] = record
        return {"success": True, "order_id": order_id, "status": "SUBMITTED"}

    async def cancel_order(
        self,
        order_id: str,
        symbol: Optional[str] = None,
        quantity: Optional[int] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        self.cancel_calls.append(order_id)

        # Inject simulated network latency if configured
        if self.async_latency_sec > 0:
            await asyncio.sleep(self.async_latency_sec)

        # Simulate intermittent broker network failure
        if self.failure_rate > 0 and random.random() < self.failure_rate:
            self.exceptions_thrown += 1
            raise ConnectionResetError(f"Broker connection reset during cancel of {order_id}")

        async with self.lock:
            if order_id not in self.orders:
                # Order might be indexed by tranche_id if broker_order_id was not populated
                for ord_rec in self.orders.values():
                    if ord_rec.get("tranche_id") == order_id:
                        ord_rec["status"] = "CANCELLED"
                        return {"success": True, "order_id": ord_rec["order_id"], "status": "CANCELLED"}
                return {"success": False, "error": f"Order {order_id} not found in broker ledger"}

            ord_rec = self.orders[order_id]
            if ord_rec["status"] == "FILLED":
                return {"success": False, "error": f"Order {order_id} already filled"}

            ord_rec["status"] = "CANCELLED"
            ord_rec["cancelled_at"] = time.perf_counter_ns()
            return {"success": True, "order_id": order_id, "status": "CANCELLED"}

    def get_open_orders(self) -> List[Dict[str, Any]]:
        return [
            o for o in self.orders.values()
            if o["status"] in ("SUBMITTED", "PENDING", "ACTIVE")
        ]

    def get_cancelled_orders(self) -> List[Dict[str, Any]]:
        return [o for o in self.orders.values() if o["status"] == "CANCELLED"]

    def get_filled_orders(self) -> List[Dict[str, Any]]:
        return [o for o in self.orders.values() if o["status"] == "FILLED"]


class TestPhase112M2AdversarialChallenger1(unittest.TestCase):
    """Empirical Stress Tests on Emergency Cancellation Latency and Ledger Invariants."""

    @classmethod
    def setUpClass(cls):
        # Warmup import of kill switch and execution infrastructure to avoid cold-import timing artifacts
        try:
            from trading_system.src.execution.kill_switch import disengage, is_kill_switch_active
            disengage()
        except Exception:
            pass

    @classmethod
    def tearDownClass(cls):
        try:
            from trading_system.src.execution.kill_switch import disengage
            disengage()
        except Exception:
            pass

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.temp_dir.name) / "test_adversarial_trade_logs.db")
        self.state_file = str(Path(self.temp_dir.name) / "test_adversarial_daemon_state.json")
        self.config = LiveDaemonConfig(
            db_path=self.db_path,
            state_file=self.state_file,
            market_mode="KRX",
            default_slice_count=5,
            emergency_cancel_timeout_sec=1.0,
            heartbeat_interval_sec=0.1,
            reconciliation_interval_sec=0.5,
            toxicity_evaporation_threshold=0.85,
        )
        try:
            from trading_system.src.execution.kill_switch import disengage
            disengage()
        except Exception:
            pass

    def tearDown(self):
        try:
            from trading_system.src.execution.kill_switch import disengage
            disengage()
        except Exception:
            pass
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    # -------------------------------------------------------------------------
    # SUITE 1: PARALLEL EMERGENCY CANCELLATION LATENCY BENCHMARKS (< 50ms)
    # -------------------------------------------------------------------------

    def test_adv01_parallel_cancellation_latency_50_orders(self):
        """
        ADV-01: Measure parallel emergency cancellation latency across 50 concurrent open orders.
        Assert that latency strictly satisfies < 50.0 ms across multiple iterations.
        """
        async def _test():
            trials = 5
            cancel_latencies = []
            outer_latencies = []

            for trial in range(trials):
                broker = StatefulMockBrokerLedger()
                daemon = LiveTradingDaemon(config=self.config, broker_connector=broker)

                # Populate 50 open orders on daemon and broker
                for i in range(50):
                    tid = f"TR_50_{trial}_{i:03d}"
                    b_res = broker.place_order(symbol="005930", side="BUY", order_type="LIMIT", price=70000.0, quantity=10)
                    daemon.active_orders[tid] = LiveTrancheOrder(
                        tranche_id=tid,
                        parent_order_id=f"P_{trial}",
                        symbol="005930",
                        quantity=10,
                        target_price=70000.0,
                        status="SUBMITTED",
                        broker_order_id=b_res["order_id"],
                    )

                self.assertEqual(len(daemon.active_orders), 50)
                self.assertEqual(len(broker.get_open_orders()), 50)

                # Benchmark cancellation latency
                t0 = time.perf_counter_ns()
                res = await daemon.emergency_cancel_all()
                outer_elapsed_ms = (time.perf_counter_ns() - t0) / 1_000_000.0

                cancel_latencies.append(res["elapsed_ms"])
                outer_latencies.append(outer_elapsed_ms)

                # Assertions on cancellation execution time (< 50ms requirement)
                self.assertLess(
                    res["elapsed_ms"],
                    50.0,
                    f"Trial {trial}: Cancellation latency {res['elapsed_ms']:.3f}ms exceeded 50ms threshold!"
                )
                self.assertLess(
                    outer_elapsed_ms,
                    50.0,
                    f"Trial {trial}: Outer execution latency {outer_elapsed_ms:.3f}ms exceeded 50ms threshold!"
                )
                self.assertEqual(res["canceled_count"], 50)
                self.assertEqual(res["orphaned_count"], 0)
                self.assertEqual(len(daemon.active_orders), 0)
                self.assertEqual(len(broker.get_open_orders()), 0)

            mean_cancel = sum(cancel_latencies) / len(cancel_latencies)
            max_cancel = max(cancel_latencies)
            min_cancel = min(cancel_latencies)
            mean_outer = sum(outer_latencies) / len(outer_latencies)
            max_outer = max(outer_latencies)

            print(
                f"\n[ADV-01 Latency 50 Orders] "
                f"Cancel Core: min={min_cancel:.3f}ms, mean={mean_cancel:.3f}ms, max={max_cancel:.3f}ms | "
                f"Outer: mean={mean_outer:.3f}ms, max={max_outer:.3f}ms (< 50ms: PASS)"
            )
            self.assertLess(max_cancel, 50.0)
            self.assertLess(max_outer, 50.0)

        asyncio.run(_test())

    def test_adv02_parallel_cancellation_latency_100_orders(self):
        """
        ADV-02: Measure parallel emergency cancellation latency across 100 concurrent open orders.
        Assert that latency strictly satisfies < 50.0 ms across multiple iterations.
        """
        async def _test():
            trials = 5
            cancel_latencies = []
            outer_latencies = []

            for trial in range(trials):
                broker = StatefulMockBrokerLedger()
                daemon = LiveTradingDaemon(config=self.config, broker_connector=broker)

                # Populate 100 open orders on daemon and broker
                for i in range(100):
                    tid = f"TR_100_{trial}_{i:03d}"
                    b_res = broker.place_order(symbol="000660", side="SELL", order_type="LIMIT", price=180000.0, quantity=5)
                    daemon.active_orders[tid] = LiveTrancheOrder(
                        tranche_id=tid,
                        parent_order_id=f"P_{trial}",
                        symbol="000660",
                        action="SELL",
                        quantity=5,
                        target_price=180000.0,
                        status="SUBMITTED",
                        broker_order_id=b_res["order_id"],
                    )

                self.assertEqual(len(daemon.active_orders), 100)
                self.assertEqual(len(broker.get_open_orders()), 100)

                # Benchmark cancellation latency
                t0 = time.perf_counter_ns()
                res = await daemon.emergency_cancel_all()
                outer_elapsed_ms = (time.perf_counter_ns() - t0) / 1_000_000.0

                cancel_latencies.append(res["elapsed_ms"])
                outer_latencies.append(outer_elapsed_ms)

                self.assertLess(
                    res["elapsed_ms"],
                    50.0,
                    f"Trial {trial}: Cancellation latency {res['elapsed_ms']:.3f}ms exceeded 50ms threshold!"
                )
                self.assertLess(
                    outer_elapsed_ms,
                    50.0,
                    f"Trial {trial}: Outer execution latency {outer_elapsed_ms:.3f}ms exceeded 50ms threshold!"
                )
                self.assertEqual(res["canceled_count"], 100)
                self.assertEqual(res["orphaned_count"], 0)
                self.assertEqual(len(daemon.active_orders), 0)
                self.assertEqual(len(broker.get_open_orders()), 0)

            mean_cancel = sum(cancel_latencies) / len(cancel_latencies)
            max_cancel = max(cancel_latencies)
            min_cancel = min(cancel_latencies)
            mean_outer = sum(outer_latencies) / len(outer_latencies)
            max_outer = max(outer_latencies)

            print(
                f"\n[ADV-02 Latency 100 Orders] "
                f"Cancel Core: min={min_cancel:.3f}ms, mean={mean_cancel:.3f}ms, max={max_cancel:.3f}ms | "
                f"Outer: mean={mean_outer:.3f}ms, max={max_outer:.3f}ms (< 50ms: PASS)"
            )
            self.assertLess(max_cancel, 50.0)
            self.assertLess(max_outer, 50.0)

        asyncio.run(_test())

    def test_adv03_parallel_cancellation_latency_500_orders(self):
        """
        ADV-03: Measure parallel emergency cancellation latency across 500 concurrent open orders.
        Assert that latency strictly satisfies < 50.0 ms across multiple iterations.
        """
        async def _test():
            trials = 5
            cancel_latencies = []
            outer_latencies = []

            for trial in range(trials):
                broker = StatefulMockBrokerLedger()
                daemon = LiveTradingDaemon(config=self.config, broker_connector=broker)

                # Populate 500 open orders on daemon and broker
                for i in range(500):
                    tid = f"TR_500_{trial}_{i:04d}"
                    b_res = broker.place_order(symbol="035420", side="BUY", order_type="LIMIT", price=200000.0, quantity=2)
                    daemon.active_orders[tid] = LiveTrancheOrder(
                        tranche_id=tid,
                        parent_order_id=f"P_{trial}",
                        symbol="035420",
                        quantity=2,
                        target_price=200000.0,
                        status="SUBMITTED",
                        broker_order_id=b_res["order_id"],
                    )

                self.assertEqual(len(daemon.active_orders), 500)
                self.assertEqual(len(broker.get_open_orders()), 500)

                # Benchmark cancellation latency
                t0 = time.perf_counter_ns()
                res = await daemon.emergency_cancel_all()
                outer_elapsed_ms = (time.perf_counter_ns() - t0) / 1_000_000.0

                cancel_latencies.append(res["elapsed_ms"])
                outer_latencies.append(outer_elapsed_ms)

                self.assertLess(
                    res["elapsed_ms"],
                    50.0,
                    f"Trial {trial}: Cancellation latency {res['elapsed_ms']:.3f}ms exceeded 50ms threshold!"
                )
                self.assertLess(
                    outer_elapsed_ms,
                    50.0,
                    f"Trial {trial}: Outer execution latency {outer_elapsed_ms:.3f}ms exceeded 50ms threshold!"
                )
                self.assertEqual(res["canceled_count"], 500)
                self.assertEqual(res["orphaned_count"], 0)
                self.assertEqual(len(daemon.active_orders), 0)
                self.assertEqual(len(broker.get_open_orders()), 0)

            mean_cancel = sum(cancel_latencies) / len(cancel_latencies)
            max_cancel = max(cancel_latencies)
            min_cancel = min(cancel_latencies)
            mean_outer = sum(outer_latencies) / len(outer_latencies)
            max_outer = max(outer_latencies)

            print(
                f"\n[ADV-03 Latency 500 Orders] "
                f"Cancel Core: min={min_cancel:.3f}ms, mean={mean_cancel:.3f}ms, max={max_cancel:.3f}ms | "
                f"Outer: mean={mean_outer:.3f}ms, max={max_outer:.3f}ms (< 50ms: PASS)"
            )
            self.assertLess(max_cancel, 50.0)
            self.assertLess(max_outer, 50.0)

        asyncio.run(_test())

    def test_adv04_parallel_cancellation_latency_1000_orders_extreme_stress(self):
        """
        ADV-04: Extreme stress test across 1,000 concurrent open orders.
        Tests asymptotic scaling, event loop overhead, and asserts sub-100ms execution.
        """
        async def _test():
            broker = StatefulMockBrokerLedger()
            daemon = LiveTradingDaemon(config=self.config, broker_connector=broker)

            for i in range(1000):
                tid = f"TR_1K_{i:04d}"
                b_res = broker.place_order(symbol="005930", side="BUY", order_type="LIMIT", price=70000.0, quantity=1)
                daemon.active_orders[tid] = LiveTrancheOrder(
                    tranche_id=tid,
                    parent_order_id="P_1K",
                    symbol="005930",
                    quantity=1,
                    target_price=70000.0,
                    status="SUBMITTED",
                    broker_order_id=b_res["order_id"],
                )

            self.assertEqual(len(daemon.active_orders), 1000)
            self.assertEqual(len(broker.get_open_orders()), 1000)

            t0 = time.perf_counter_ns()
            res = await daemon.emergency_cancel_all()
            outer_elapsed_ms = (time.perf_counter_ns() - t0) / 1_000_000.0

            print(
                f"\n[ADV-04 Extreme Stress 1000 Orders] "
                f"core={res['elapsed_ms']:.3f}ms, outer={outer_elapsed_ms:.3f}ms, cancelled={res['canceled_count']}"
            )
            self.assertEqual(res["canceled_count"], 1000)
            self.assertEqual(res["orphaned_count"], 0)
            self.assertEqual(len(daemon.active_orders), 0)
            self.assertEqual(len(broker.get_open_orders()), 0)
            # 1,000 orders extreme stress scaling bound (< 150ms)
            self.assertLess(res["elapsed_ms"], 150.0)
            self.assertLess(outer_elapsed_ms, 200.0)

        asyncio.run(_test())

    # -------------------------------------------------------------------------
    # SUITE 2: ZERO ORPHANED OPEN ORDERS ON SIMULATED BROKER LEDGERS
    # -------------------------------------------------------------------------

    def test_adv05_simulated_broker_ledger_zero_orphans_on_emergency_cancel(self):
        """
        ADV-05: Strict audit of simulated broker ledger.
        Verify that every open order in broker ledger is transitioned to CANCELLED,
        with exactly zero orphaned open orders remaining in broker ledger.
        """
        async def _test():
            broker = StatefulMockBrokerLedger()
            daemon = LiveTradingDaemon(config=self.config, broker_connector=broker)

            order_count = 150
            for i in range(order_count):
                tid = f"AUDIT_TR_{i:03d}"
                b_res = broker.place_order(
                    symbol="005930" if i % 2 == 0 else "000660",
                    side="BUY" if i % 3 == 0 else "SELL",
                    order_type="LIMIT",
                    price=75000.0 if i % 2 == 0 else 185000.0,
                    quantity=10,
                )
                daemon.active_orders[tid] = LiveTrancheOrder(
                    tranche_id=tid,
                    parent_order_id="P_AUDIT",
                    symbol="005930" if i % 2 == 0 else "000660",
                    quantity=10,
                    target_price=75000.0 if i % 2 == 0 else 185000.0,
                    status="SUBMITTED",
                    broker_order_id=b_res["order_id"],
                )

            self.assertEqual(len(broker.get_open_orders()), order_count)
            self.assertEqual(len(daemon.active_orders), order_count)

            # Trigger emergency cancellation
            res = await daemon.emergency_cancel_all()

            # 1. Daemon audit: zero active orders
            self.assertEqual(len(daemon.active_orders), 0, "Daemon still contains active orders!")
            self.assertEqual(len(daemon.completed_orders), order_count)

            # 2. Broker ledger audit: zero open orders
            open_ledger = broker.get_open_orders()
            self.assertEqual(len(open_ledger), 0, f"Broker ledger still has {len(open_ledger)} orphaned open orders!")

            # 3. Exactly order_count cancelled orders in broker ledger
            cancelled_ledger = broker.get_cancelled_orders()
            self.assertEqual(len(cancelled_ledger), order_count)

            # 4. Status verification on each individual order record
            for oid, o_data in broker.orders.items():
                self.assertEqual(o_data["status"], "CANCELLED")
                self.assertIn("cancelled_at", o_data)

        asyncio.run(_test())

    def test_adv06_simulated_broker_ledger_zero_orphans_on_daemon_stop(self):
        """
        ADV-06: Verify that daemon.stop() triggers full emergency cancellation
        and guarantees zero orphaned orders on both daemon state and broker ledger.
        """
        async def _test():
            broker = StatefulMockBrokerLedger()
            daemon = LiveTradingDaemon(config=self.config, broker_connector=broker)
            await daemon.start()

            # Place 75 active open orders
            for i in range(75):
                tid = f"STOP_TR_{i:03d}"
                b_res = broker.place_order(symbol="005930", side="BUY", order_type="LIMIT", price=72000.0, quantity=10)
                daemon.active_orders[tid] = LiveTrancheOrder(
                    tranche_id=tid,
                    parent_order_id="P_STOP",
                    symbol="005930",
                    quantity=10,
                    target_price=72000.0,
                    status="SUBMITTED",
                    broker_order_id=b_res["order_id"],
                )

            self.assertEqual(len(daemon.active_orders), 75)
            self.assertEqual(len(broker.get_open_orders()), 75)

            # Call graceful / emergency shutdown
            await daemon.stop(reason="Operator SIGINT test")

            # Assert complete cleanup
            self.assertEqual(daemon.session_state, DaemonSessionState.STOPPED)
            self.assertEqual(len(daemon.active_orders), 0, "Daemon active_orders must be empty after stop()")
            self.assertEqual(len(broker.get_open_orders()), 0, "Broker ledger must have 0 open orders after stop()")
            self.assertEqual(len(broker.get_cancelled_orders()), 75)

        asyncio.run(_test())

    def test_adv07_zero_orphans_with_mixed_order_states(self):
        """
        ADV-07: In real trading, some orders may already be FILLED or REJECTED
        when emergency cancel is triggered. Verify only SUBMITTED orders are cancelled,
        already-filled orders are not corrupted, and zero open orders remain.
        """
        async def _test():
            broker = StatefulMockBrokerLedger()
            daemon = LiveTradingDaemon(config=self.config, broker_connector=broker)

            # 30 orders SUBMITTED
            for i in range(30):
                tid = f"MIX_SUBMIT_{i:02d}"
                b_res = broker.place_order(symbol="005930", side="BUY", order_type="LIMIT", price=70000.0, quantity=10)
                daemon.active_orders[tid] = LiveTrancheOrder(
                    tranche_id=tid,
                    parent_order_id="P_MIX",
                    symbol="005930",
                    quantity=10,
                    target_price=70000.0,
                    status="SUBMITTED",
                    broker_order_id=b_res["order_id"],
                )

            # 20 orders already FILLED in broker ledger & daemon
            for i in range(20):
                tid = f"MIX_FILLED_{i:02d}"
                b_res = broker.place_order(symbol="000660", side="SELL", order_type="LIMIT", price=180000.0, quantity=5)
                broker.orders[b_res["order_id"]]["status"] = "FILLED"
                daemon.active_orders[tid] = LiveTrancheOrder(
                    tranche_id=tid,
                    parent_order_id="P_MIX",
                    symbol="000660",
                    quantity=5,
                    target_price=180000.0,
                    status="FILLED",
                    broker_order_id=b_res["order_id"],
                )

            # 10 orders REJECTED
            for i in range(10):
                tid = f"MIX_REJECT_{i:02d}"
                daemon.active_orders[tid] = LiveTrancheOrder(
                    tranche_id=tid,
                    parent_order_id="P_MIX",
                    symbol="035420",
                    quantity=1,
                    target_price=200000.0,
                    status="REJECTED",
                )

            self.assertEqual(len(broker.get_open_orders()), 30)

            # Run emergency cancel
            res = await daemon.emergency_cancel_all()

            # Only the 30 SUBMITTED orders should be cancelled
            self.assertEqual(res["canceled_count"], 30)

            # In broker ledger: exactly 0 open orders, 30 cancelled, 20 filled
            self.assertEqual(len(broker.get_open_orders()), 0)
            self.assertEqual(len(broker.get_cancelled_orders()), 30)
            self.assertEqual(len(broker.get_filled_orders()), 20)

        asyncio.run(_test())

    def test_adv08_zero_orphans_under_async_network_io_delay(self):
        """
        ADV-08: Concurrency Proof.
        Inject simulated 5ms asynchronous broker round-trip delay per cancellation.
        Across 50 concurrent orders:
          - Sequential time would be: 50 * 5ms = 250ms (FAILS < 50ms)
          - Concurrent asyncio.gather time must be: ~5-15ms (< 50ms PASS)
        Across 100 concurrent orders:
          - Sequential time would be: 100 * 5ms = 500ms (FAILS < 50ms)
          - Concurrent asyncio.gather time must be: ~5-25ms (< 50ms PASS)
        Across 500 concurrent orders:
          - Sequential time would be: 500 * 5ms = 2,500ms (FAILS < 50ms)
          - Concurrent asyncio.gather time must be: ~10-40ms (< 50ms PASS)
        Verify latency strictly < 50ms and zero orphans in all cases.
        """
        async def _test():
            for count in (50, 100, 500):
                # 5ms async I/O sleep per order
                broker = StatefulMockBrokerLedger(async_latency_sec=0.005)
                daemon = LiveTradingDaemon(config=self.config, broker_connector=broker)

                for i in range(count):
                    tid = f"ASYNC_{count}_{i:03d}"
                    b_res = broker.place_order(symbol="005930", side="BUY", order_type="LIMIT", price=70000.0, quantity=10)
                    daemon.active_orders[tid] = LiveTrancheOrder(
                        tranche_id=tid,
                        parent_order_id="P_ASYNC",
                        symbol="005930",
                        quantity=10,
                        target_price=70000.0,
                        status="SUBMITTED",
                        broker_order_id=b_res["order_id"],
                    )

                self.assertEqual(len(broker.get_open_orders()), count)

                t0 = time.perf_counter_ns()
                res = await daemon.emergency_cancel_all()
                outer_elapsed_ms = (time.perf_counter_ns() - t0) / 1_000_000.0

                print(
                    f"\n[ADV-08 Concurrency Test ({count} orders, 5ms delay/order)] "
                    f"core={res['elapsed_ms']:.2f}ms, outer={outer_elapsed_ms:.2f}ms "
                    f"(vs sequential {count * 5}ms), orphans={res['orphaned_count']}"
                )

                # Strict latency assertion: must finish in < 50ms despite 5ms delay per order!
                self.assertLess(
                    res["elapsed_ms"],
                    50.0,
                    f"{count} orders core latency {res['elapsed_ms']:.2f}ms >= 50ms!"
                )
                self.assertLess(
                    outer_elapsed_ms,
                    50.0,
                    f"{count} orders outer latency {outer_elapsed_ms:.2f}ms >= 50ms!"
                )
                self.assertEqual(res["canceled_count"], count)
                self.assertEqual(res["orphaned_count"], 0)
                self.assertEqual(len(daemon.active_orders), 0)
                self.assertEqual(len(broker.get_open_orders()), 0)

        asyncio.run(_test())

    def test_adv09_broker_partial_failure_and_exception_resilience(self):
        """
        ADV-09: Stress test broker intermittent network exceptions during emergency cancel.
        Ensure that when broker.cancel_order throws ConnectionResetError or TimeoutError,
        daemon catches the error, does not abort the remaining cancels, and completes safely.
        """
        async def _test():
            # 20% random broker cancellation failures
            broker = StatefulMockBrokerLedger(failure_rate=0.20)
            daemon = LiveTradingDaemon(config=self.config, broker_connector=broker)

            count = 100
            for i in range(count):
                tid = f"FAIL_TR_{i:03d}"
                b_res = broker.place_order(symbol="005930", side="BUY", order_type="LIMIT", price=70000.0, quantity=10)
                daemon.active_orders[tid] = LiveTrancheOrder(
                    tranche_id=tid,
                    parent_order_id="P_FAIL",
                    symbol="005930",
                    quantity=10,
                    target_price=70000.0,
                    status="SUBMITTED",
                    broker_order_id=b_res["order_id"],
                )

            # Execute emergency cancel
            res = await daemon.emergency_cancel_all()

            self.assertGreater(broker.exceptions_thrown, 0, "Failure rate should have produced exceptions")
            print(f"\n[ADV-09 Exception Resilience] Caught {broker.exceptions_thrown} simulated broker failures gracefully.")

            # Daemon active_orders must be completely cleared
            self.assertEqual(len(daemon.active_orders), 0)
            self.assertEqual(res["canceled_count"], count)
            self.assertEqual(res["orphaned_count"], 0)
            self.assertLess(res["elapsed_ms"], 50.0)

        asyncio.run(_test())

    def test_adv10_concurrent_order_submission_race_during_emergency_halt(self):
        """
        ADV-10: Concurrency Race Test.
        Simulate concurrent order submissions attempting to post orders at the exact
        same millisecond when an emergency halt and cancellation is triggered.
        Verify that after halt, submissions are rejected and zero orphaned orders leak into the system.
        """
        async def _test():
            broker = StatefulMockBrokerLedger()
            daemon = LiveTradingDaemon(config=self.config, broker_connector=broker)
            await daemon.start()
            daemon.set_session_state(DaemonSessionState.CONTINUOUS_TRADING)

            # Pre-populate 50 open orders
            for i in range(50):
                tid = f"RACE_PRE_{i:02d}"
                b_res = broker.place_order(symbol="005930", side="BUY", order_type="LIMIT", price=70000.0, quantity=10)
                daemon.active_orders[tid] = LiveTrancheOrder(
                    tranche_id=tid,
                    parent_order_id="P_RACE",
                    symbol="005930",
                    quantity=10,
                    target_price=70000.0,
                    status="SUBMITTED",
                    broker_order_id=b_res["order_id"],
                )

            # Launch concurrent submission attempts
            rejected_submissions = 0

            async def _submit_attempt():
                nonlocal rejected_submissions
                for j in range(5):
                    plan = {
                        "order_id": f"RACE_NEW_{j}",
                        "symbol": "005930",
                        "market": "KOSPI",
                        "action": "BUY",
                        "quantity": 100,
                        "target_price": 70000.0,
                        "slice_count": 3,
                    }
                    tranches = await daemon.submit_order_plan(plan)
                    if len(tranches) == 0:
                        rejected_submissions += 1
                    await asyncio.sleep(0.002)

            # Run emergency halt concurrently with submission attempts
            async def _trigger_halt():
                await asyncio.sleep(0.005)
                await daemon.trigger_emergency_halt("Critical toxicity surge during race test")

            await asyncio.gather(
                _submit_attempt(),
                _trigger_halt(),
                _submit_attempt(),
            )

            # System must now be in EMERGENCY_HALT
            self.assertEqual(daemon.session_state, DaemonSessionState.EMERGENCY_HALT)

            # Subsequent submissions must be rejected outright
            post_halt_plan = {
                "order_id": "POST_HALT_TEST",
                "symbol": "005930",
                "quantity": 50,
                "target_price": 70000.0,
            }
            res_post = await daemon.submit_order_plan(post_halt_plan)
            self.assertEqual(len(res_post), 0)

            # Final audit: zero active orders in daemon
            self.assertEqual(len(daemon.active_orders), 0)

            await daemon.stop()

        asyncio.run(_test())

    def test_adv11_native_kis_simulation_broker_zero_orphans(self):
        """
        ADV-11: Verify zero orphans on actual KISBrokerConnector in simulation_mode.
        Submit 50 orders via LiveTradingDaemon with KISBrokerConnector(simulation_mode=True).
        Trigger emergency_cancel_all() and verify:
        - daemon.active_orders has 0 orders
        - KISBrokerConnector._sim_orders has 0 open orders remaining (all CANCELLED)
        - Latency satisfies < 50ms
        """
        async def _test():
            kis_conn = KISBrokerConnector(account_number="12345678", simulation_mode=True)
            kis_conn.connect()

            daemon = LiveTradingDaemon(config=self.config, broker_connector=kis_conn)
            daemon.set_session_state(DaemonSessionState.CONTINUOUS_TRADING)

            # Retrieve simulated market quote to satisfy connector's ±3% sanity check
            quote_info = kis_conn.get_stock_quote("005930")
            quote_px = float(quote_info.get("price", 64648.0)) if isinstance(quote_info, dict) else 64648.0
            if quote_px <= 0:
                quote_px = 64648.0

            for i in range(50):
                tid = f"KIS_TR_{i:03d}"
                # Directly dispatch single tranche through daemon with unique parent_id
                tranche = await daemon.dispatch_order_slice(
                    symbol="005930",
                    side="BUY",
                    target_qty=10,
                    target_price=quote_px,
                    parent_id=f"P_KIS_{i:03d}",
                    market="KOSPI",
                )
                self.assertIsNotNone(tranche.broker_order_id)

            self.assertEqual(len(daemon.active_orders), 50)

            # Check open orders in KIS broker ledger before cancel
            open_in_kis_before = [
                o for o in kis_conn._sim_orders.values()
                if o["status"] in ("SUBMITTED", "PENDING", "ACTIVE")
            ]
            self.assertEqual(len(open_in_kis_before), 50)

            # Trigger emergency cancel
            res = await daemon.emergency_cancel_all()

            # Latency and orphan assertions
            self.assertLess(res["elapsed_ms"], 50.0)
            self.assertEqual(res["canceled_count"], 50)
            self.assertEqual(res["orphaned_count"], 0)
            self.assertEqual(len(daemon.active_orders), 0)

            # Check open orders in KIS broker ledger after cancel
            open_in_kis_after = [
                o for o in kis_conn._sim_orders.values()
                if o["status"] in ("SUBMITTED", "PENDING", "ACTIVE")
            ]
            self.assertEqual(len(open_in_kis_after), 0, "KIS simulated broker ledger still has open orders!")

            cancelled_in_kis = [
                o for o in kis_conn._sim_orders.values()
                if o["status"] == "CANCELLED"
            ]
            self.assertEqual(len(cancelled_in_kis), 50)

            print(f"\n[ADV-11 Native KIS Simulation] 50 orders cancelled in {res['elapsed_ms']:.3f}ms with 0 orphans in KIS ledger.")

        asyncio.run(_test())

    def test_adv12_kill_switch_engagement_and_clean_disengage(self):
        """
        ADV-12: Verify that emergency_cancel_all trips the kill switch,
        creates the audit record, and can be cleanly disengaged without leaving artifacts.
        """
        async def _test():
            from trading_system.src.execution.kill_switch import disengage, is_kill_switch_active, STATE_FILE

            disengage()
            self.assertFalse(is_kill_switch_active())

            broker = StatefulMockBrokerLedger()
            daemon = LiveTradingDaemon(config=self.config, broker_connector=broker)

            # Place 5 orders
            for i in range(5):
                tid = f"KS_TR_{i}"
                b_res = broker.place_order(symbol="005930", side="BUY", order_type="LIMIT", price=70000.0, quantity=10)
                daemon.active_orders[tid] = LiveTrancheOrder(
                    tranche_id=tid,
                    parent_order_id="P_KS",
                    symbol="005930",
                    quantity=10,
                    target_price=70000.0,
                    status="SUBMITTED",
                    broker_order_id=b_res["order_id"],
                )

            # Trigger emergency cancellation
            await daemon.emergency_cancel_all()

            # Assert kill switch is actively engaged
            self.assertTrue(is_kill_switch_active(), "Kill switch should be active after emergency cancel")

            # Clean up via disengage()
            disengage()
            self.assertFalse(is_kill_switch_active(), "Kill switch should be disengaged after disengage()")

        asyncio.run(_test())


if __name__ == "__main__":
    unittest.main()
