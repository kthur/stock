"""
tests/test_phase112_m2_challenger2_stress.py — Empirical Stress Tests for Phase 112 M2
Milestone: Phase 112 (Release R128 / v119 Production Master, Feature F531)
Author: Challenger 2 (Empirical Challenger)

Mission Focus:
1. Flood event queue with high volume tick events (5,000~10,000 mock ticks) while submitting
   EMERGENCY signals (kill switch / toxicity spike T >= 0.85).
   Assert that EMERGENCY items preempt normal ticks and process immediately without starvation or latency blowout.
2. Verify that toxicity spike T >= 0.85 triggers immediate automatic emergency halt and order withdrawal.
3. Strict boundary condition analysis (T = 0.8499 vs T = 0.8500).
4. Sub-50ms parallel emergency order cancellation across 100+ orders with zero orphaned orders.
5. Post-halt rejection gating and thread-safe multi-producer flooding.
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
import logging
import math
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import MagicMock
import pytest

# Ensure repo root and trading_system are on path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "trading_system"))
sys.path.insert(0, str(REPO_ROOT))

from src.execution.live_trading_daemon import (
    DaemonEventType,
    DaemonPriority,
    DaemonSessionState,
    EmergencyHaltEvent,
    LiveDaemonConfig,
    LiveTradingDaemon,
    LiveTrancheOrder,
    MarketTickEvent,
    PrioritizedDaemonEvent,
    VolatilitySpikeEvent,
)


class TestPhase112M2Challenger2Stress(unittest.TestCase):
    """Adversarial stress and verification suite by Challenger 2."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.temp_dir.name) / "test_stress_trade_logs.db")
        self.state_file = str(Path(self.temp_dir.name) / "test_stress_daemon_state.json")
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

    def tearDown(self):
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def test_adv01_event_queue_priority_preemption_under_10k_flood(self):
        """
        ADV-01: Flood event queue with 10,000 LOW priority ticks and assert
        EMERGENCY signals strictly preempt LOW ticks without starvation.
        """
        async def _test():
            queue: asyncio.PriorityQueue[PrioritizedDaemonEvent] = asyncio.PriorityQueue()
            seq = 0

            # 1. Flood with 10,000 LOW priority events
            flood_count = 10_000
            t_fill_start = time.perf_counter()
            for i in range(flood_count):
                seq += 1
                evt = PrioritizedDaemonEvent(
                    priority=DaemonPriority.LOW,
                    sequence_id=seq,
                    timestamp_ns=time.perf_counter_ns(),
                    event_type=DaemonEventType.MARKET_TICK,
                    payload={"tick_id": i, "symbol": "005930", "price": 75000.0 + (i % 100)},
                )
                queue.put_nowait(evt)

            self.assertEqual(queue.qsize(), flood_count)

            # 2. Inject single EMERGENCY event at the very end of sequence
            seq += 1
            emergency_evt = PrioritizedDaemonEvent(
                priority=DaemonPriority.EMERGENCY,
                sequence_id=seq,
                timestamp_ns=time.perf_counter_ns(),
                event_type=DaemonEventType.KILL_SWITCH_TRIP,
                payload={"reason": "CRITICAL_KILL_SWITCH", "id": "EMERGENCY_ALPHA"},
            )
            queue.put_nowait(emergency_evt)

            self.assertEqual(queue.qsize(), flood_count + 1)

            # 3. Measure preemption dequeue time and assert EMERGENCY item is popped first
            t0 = time.perf_counter_ns()
            popped_first = await queue.get()
            t_pop_ns = time.perf_counter_ns() - t0
            t_pop_ms = t_pop_ns / 1_000_000.0

            # Strict assertion: Despite 10,000 items in queue, EMERGENCY item is dequeued first!
            self.assertEqual(popped_first.priority, DaemonPriority.EMERGENCY)
            self.assertEqual(popped_first.event_type, DaemonEventType.KILL_SWITCH_TRIP)
            self.assertEqual(popped_first.payload["id"], "EMERGENCY_ALPHA")

            # Assert zero latency blowout: min-heap pop takes O(log N) ~ 14 operations, < 5.0 ms
            self.assertLess(t_pop_ms, 5.0, f"Priority queue preemption too slow: {t_pop_ms:.3f} ms")

            # 4. Now inject HIGH and NORMAL priority items into remaining 10,000 LOW items
            seq += 1
            high_evt = PrioritizedDaemonEvent(
                priority=DaemonPriority.HIGH,
                sequence_id=seq,
                timestamp_ns=time.perf_counter_ns(),
                event_type=DaemonEventType.TRANCHE_FILL,
                payload={"id": "HIGH_FILL"},
            )
            seq += 1
            norm_evt = PrioritizedDaemonEvent(
                priority=DaemonPriority.NORMAL,
                sequence_id=seq,
                timestamp_ns=time.perf_counter_ns(),
                event_type=DaemonEventType.ORDER_SUBMIT,
                payload={"id": "NORM_ORDER"},
            )
            queue.put_nowait(norm_evt)
            queue.put_nowait(high_evt)

            # Next dequeue must be HIGH (priority=1), then NORMAL (priority=2), then first LOW
            d_high = await queue.get()
            d_norm = await queue.get()
            d_low = await queue.get()

            self.assertEqual(d_high.priority, DaemonPriority.HIGH)
            self.assertEqual(d_high.payload["id"], "HIGH_FILL")
            self.assertEqual(d_norm.priority, DaemonPriority.NORMAL)
            self.assertEqual(d_norm.payload["id"], "NORM_ORDER")
            self.assertEqual(d_low.priority, DaemonPriority.LOW)
            self.assertEqual(d_low.payload["tick_id"], 0)

        asyncio.run(_test())

    def test_adv02_live_daemon_execution_preemption_during_5k_tick_stream(self):
        """
        ADV-02: Start LiveTradingDaemon with active background dispatcher,
        flood with 5,000 ticks while dispatching EMERGENCY halt event.
        Verify EMERGENCY event interrupts normal processing and trips halt immediately.
        """
        async def _test():
            processed_order = []

            t_emerg_executed_ns = []

            class _InterceptingDaemon(LiveTradingDaemon):
                async def handle_event(self, event):
                    evt_type = getattr(event, "event_type", None)
                    payload = getattr(event, "payload", {})
                    prio = getattr(event, "priority", None)
                    if payload.get("id") == "EMERGENCY_KILL":
                        t_emerg_executed_ns.append(time.perf_counter_ns())
                    processed_order.append((prio, str(evt_type), payload.get("id")))
                    return await super().handle_event(event)

            daemon = _InterceptingDaemon(config=self.config)
            await daemon.start()
            daemon.set_session_state(DaemonSessionState.CONTINUOUS_TRADING)

            # Add working orders to test order withdrawal
            for i in range(10):
                tid = f"TR_WORK_{i}"
                daemon.active_orders[tid] = LiveTrancheOrder(
                    tranche_id=tid,
                    parent_order_id="P_WORK",
                    symbol="005930",
                    quantity=10,
                    target_price=70000.0,
                    status="SUBMITTED",
                )
            self.assertEqual(len(daemon.active_orders), 10)

            # Enqueue 5,000 LOW ticks
            t0 = time.perf_counter_ns()
            for i in range(5000):
                e = PrioritizedDaemonEvent(
                    priority=DaemonPriority.LOW,
                    sequence_id=daemon._next_sequence_id(),
                    timestamp_ns=time.perf_counter_ns(),
                    event_type=DaemonEventType.MARKET_TICK,
                    payload={"id": f"tick_{i}", "symbol": "005930", "price": 75000.0, "volume": 10.0},
                )
                await daemon.enqueue_event(e)

            # Submit EMERGENCY kill switch while queue has 5,000 pending items
            t_emerg_sent = time.perf_counter_ns()
            emerg_evt = PrioritizedDaemonEvent(
                priority=DaemonPriority.EMERGENCY,
                sequence_id=daemon._next_sequence_id(),
                timestamp_ns=t_emerg_sent,
                event_type=DaemonEventType.EMERGENCY_HALT,
                payload={"reason": "ADV_TEST_HALT", "id": "EMERGENCY_KILL"},
            )
            await daemon.enqueue_event(emerg_evt)

            # Wait briefly for dispatcher to process the emergency event and complete order withdrawal
            for _ in range(150):
                if daemon.session_state == DaemonSessionState.EMERGENCY_HALT and len(daemon.active_orders) == 0:
                    break
                await asyncio.sleep(0.01)

            # Assertions on State and Active Order Withdrawal
            self.assertEqual(daemon.session_state, DaemonSessionState.EMERGENCY_HALT)
            self.assertEqual(len(daemon.active_orders), 0)
            self.assertEqual(len(daemon.completed_orders), 10)
            for o in daemon.completed_orders:
                self.assertEqual(o.status, "CANCELLED")

            # Check where EMERGENCY event was processed relative to 5000 ticks
            emerg_indexes = [idx for idx, item in enumerate(processed_order) if item[2] == "EMERGENCY_KILL"]
            self.assertTrue(len(emerg_indexes) > 0, "Emergency event was not executed!")
            first_emerg_idx = emerg_indexes[0]

            # In priority queue min-heap, emergency event is dequeued at index 0 (ahead of all 5,000 ticks)
            self.assertLess(first_emerg_idx, 5, f"Emergency event was delayed by too many ticks: index {first_emerg_idx}")

            # Precise dispatch latency: from enqueue to execution start
            self.assertTrue(len(t_emerg_executed_ns) > 0, "Emergency execution timestamp missing!")
            dispatch_latency_ms = (t_emerg_executed_ns[0] - t_emerg_sent) / 1_000_000.0
            # Strict assertion: Preemption must execute in sub-10ms (empirical is < 1ms)
            self.assertLess(dispatch_latency_ms, 10.0, f"Emergency dispatch latency too slow: {dispatch_latency_ms:.2f} ms")

            await daemon.stop()

        asyncio.run(_test())

    def test_adv03_toxicity_spike_triggers_immediate_halt_and_withdrawal(self):
        """
        ADV-03: Verify that composite toxicity spike (T >= 0.85) triggers immediate
        emergency halt and order withdrawal across all broker orders.
        """
        async def _test():
            cancelled_order_ids = []

            class _BrokerMock:
                async def cancel_order(self, order_id, symbol=None, quantity=None):
                    cancelled_order_ids.append(order_id)
                    return {"status": "CANCELLED", "order_id": order_id}

            mock_broker = _BrokerMock()
            daemon = LiveTradingDaemon(config=self.config, broker_connector=mock_broker)
            await daemon.start()
            daemon.set_session_state(DaemonSessionState.CONTINUOUS_TRADING)

            # Create 20 active working orders
            for i in range(20):
                tid = f"TRANCHE_TOX_{i:02d}"
                daemon.active_orders[tid] = LiveTrancheOrder(
                    tranche_id=tid,
                    parent_order_id="P_TOX",
                    symbol="005930" if i % 2 == 0 else "000660",
                    market="KOSPI",
                    action="BUY" if i % 2 == 0 else "SELL",
                    quantity=50,
                    target_price=70000.0,
                    status="SUBMITTED",
                    broker_order_id=f"BROKER_TOX_{i:02d}",
                )

            self.assertEqual(len(daemon.active_orders), 20)

            # Fire VOLATILITY_SPIKE with T = 0.88 >= 0.85
            t0 = time.perf_counter_ns()
            spike = PrioritizedDaemonEvent(
                priority=DaemonPriority.EMERGENCY,
                sequence_id=daemon._next_sequence_id(),
                timestamp_ns=t0,
                event_type=DaemonEventType.VOLATILITY_SPIKE,
                payload={
                    "symbol": "005930",
                    "composite_toxicity": 0.88,
                    "is_evaporating": False,
                },
            )
            await daemon.enqueue_event(spike)

            # Wait for processing and order withdrawal
            for _ in range(100):
                if daemon.session_state == DaemonSessionState.EMERGENCY_HALT and len(daemon.active_orders) == 0:
                    break
                await asyncio.sleep(0.01)

            elapsed_ms = (time.perf_counter_ns() - t0) / 1_000_000.0

            # Assertions
            self.assertEqual(daemon.session_state, DaemonSessionState.EMERGENCY_HALT)
            self.assertEqual(len(daemon.active_orders), 0, "Orphaned active orders detected!")
            self.assertEqual(len(cancelled_order_ids), 20, "Not all orders sent cancellation to broker!")
            self.assertEqual(len(daemon.completed_orders), 20)
            self.assertGreaterEqual(daemon.metrics["emergency_cancels_count"], 1)

            # Latency verification
            self.assertLess(elapsed_ms, 50.0, f"Order withdrawal took {elapsed_ms:.2f}ms >= 50ms requirement!")

            await daemon.stop()

        asyncio.run(_test())

    def test_adv04_market_tick_stream_toxicity_threshold_boundary(self):
        """
        ADV-04: Test exact boundary conditions of IntradayToxicityFilter:
        - T = 0.8499 -> NO halt (normal quote shading)
        - T = 0.8500 -> IMMEDIATE emergency halt & withdrawal
        - is_evaporating = True (even if T < 0.85) -> IMMEDIATE emergency halt & withdrawal
        """
        async def _test():
            # Scenario A: T = 0.8499 (below threshold 0.85)
            mock_filter_sub = MagicMock()
            mock_filter_sub.evaluate_toxicity = MagicMock(
                return_value=MagicMock(composite_toxicity=0.8499, is_evaporating=False)
            )
            daemon_sub = LiveTradingDaemon(config=self.config, toxicity_filter=mock_filter_sub)
            await daemon_sub.start()
            daemon_sub.set_session_state(DaemonSessionState.CONTINUOUS_TRADING)

            tick_sub = PrioritizedDaemonEvent(
                priority=DaemonPriority.LOW,
                sequence_id=daemon_sub._next_sequence_id(),
                timestamp_ns=time.perf_counter_ns(),
                event_type=DaemonEventType.MARKET_TICK,
                payload={"symbol": "005930", "price": 75000.0, "volume": 100.0},
            )
            await daemon_sub.enqueue_event(tick_sub)
            await asyncio.sleep(0.05)

            # State MUST remain CONTINUOUS_TRADING
            self.assertEqual(daemon_sub.session_state, DaemonSessionState.CONTINUOUS_TRADING)
            await daemon_sub.stop()

            # Scenario B: T = 0.8500 (exact threshold)
            mock_filter_exact = MagicMock()
            mock_filter_exact.evaluate_toxicity = MagicMock(
                return_value=MagicMock(composite_toxicity=0.8500, is_evaporating=False)
            )
            daemon_exact = LiveTradingDaemon(config=self.config, toxicity_filter=mock_filter_exact)
            await daemon_exact.start()
            daemon_exact.set_session_state(DaemonSessionState.CONTINUOUS_TRADING)

            daemon_exact.active_orders["T_EXACT"] = LiveTrancheOrder(
                tranche_id="T_EXACT", parent_order_id="P1", symbol="005930", quantity=10, target_price=75000.0, status="SUBMITTED"
            )

            tick_exact = PrioritizedDaemonEvent(
                priority=DaemonPriority.LOW,
                sequence_id=daemon_exact._next_sequence_id(),
                timestamp_ns=time.perf_counter_ns(),
                event_type=DaemonEventType.MARKET_TICK,
                payload={"symbol": "005930", "price": 75000.0, "volume": 100.0},
            )
            await daemon_exact.enqueue_event(tick_exact)
            await asyncio.sleep(0.05)

            # Must trigger EMERGENCY_HALT and clear active orders
            self.assertEqual(daemon_exact.session_state, DaemonSessionState.EMERGENCY_HALT)
            self.assertEqual(len(daemon_exact.active_orders), 0)
            await daemon_exact.stop()

            # Scenario C: is_evaporating = True with low T = 0.40
            mock_filter_evap = MagicMock()
            mock_filter_evap.evaluate_toxicity = MagicMock(
                return_value=MagicMock(composite_toxicity=0.40, is_evaporating=True)
            )
            daemon_evap = LiveTradingDaemon(config=self.config, toxicity_filter=mock_filter_evap)
            await daemon_evap.start()
            daemon_evap.set_session_state(DaemonSessionState.CONTINUOUS_TRADING)

            daemon_evap.active_orders["T_EVAP"] = LiveTrancheOrder(
                tranche_id="T_EVAP", parent_order_id="P1", symbol="005930", quantity=10, target_price=75000.0, status="SUBMITTED"
            )

            tick_evap = PrioritizedDaemonEvent(
                priority=DaemonPriority.LOW,
                sequence_id=daemon_evap._next_sequence_id(),
                timestamp_ns=time.perf_counter_ns(),
                event_type=DaemonEventType.MARKET_TICK,
                payload={"symbol": "005930", "price": 75000.0, "volume": 100.0},
            )
            await daemon_evap.enqueue_event(tick_evap)
            await asyncio.sleep(0.05)

            self.assertEqual(daemon_evap.session_state, DaemonSessionState.EMERGENCY_HALT)
            self.assertEqual(len(daemon_evap.active_orders), 0)
            await daemon_evap.stop()

        asyncio.run(_test())

    def test_adv05_sub_50ms_mass_cancellation_under_200_orders(self):
        """
        ADV-05: Stress test emergency order withdrawal across 200 concurrent active orders.
        Assert cancellation takes strictly under 50.0 ms with zero orphaned orders.
        """
        async def _test():
            class _AsyncMockBroker:
                def __init__(self):
                    self.cancel_count = 0

                async def cancel_order(self, order_id, symbol=None, quantity=None):
                    self.cancel_count += 1
                    # Yield to event loop cooperatively
                    return {"status": "CANCELLED", "order_id": order_id}

            broker = _AsyncMockBroker()
            daemon = LiveTradingDaemon(config=self.config, broker_connector=broker)

            # Insert 200 orders across different symbols and directions
            order_count = 200
            for i in range(order_count):
                tid = f"TR_STRESS_{i:04d}"
                daemon.active_orders[tid] = LiveTrancheOrder(
                    tranche_id=tid,
                    parent_order_id=f"P_{i//20}",
                    symbol=f"SYM_{i%10:02d}",
                    market="KOSPI" if i % 2 == 0 else "NASDAQ",
                    action="BUY" if i % 2 == 0 else "SELL",
                    quantity=100,
                    target_price=50000.0 + i,
                    status="SUBMITTED",
                    broker_order_id=f"BRK_{i:04d}",
                )

            self.assertEqual(len(daemon.active_orders), order_count)

            # Execute parallel emergency cancel
            res = await daemon.emergency_cancel_all()

            # Strict assertions
            self.assertLess(res["elapsed_ms"], 50.0, f"Mass cancellation took {res['elapsed_ms']:.2f}ms >= 50ms limit!")
            self.assertEqual(res["canceled_count"], order_count)
            self.assertEqual(res["orphaned_count"], 0)
            self.assertEqual(res["status"], "CLEARED")
            self.assertEqual(broker.cancel_count, order_count)
            self.assertEqual(len(daemon.active_orders), 0)
            self.assertEqual(len(daemon.completed_orders), order_count)

        asyncio.run(_test())

    def test_adv06_post_halt_rejection_gating(self):
        """
        ADV-06: Verify that after emergency halt is triggered, subsequent order plan
        submissions are strictly rejected and return empty lists (preventing rogue orders).
        """
        async def _test():
            daemon = LiveTradingDaemon(config=self.config)
            await daemon.start()
            daemon.set_session_state(DaemonSessionState.CONTINUOUS_TRADING)

            # Normal submission before halt works
            plan = {
                "order_id": "P_NORMAL",
                "symbol": "005930",
                "action": "BUY",
                "quantity": 100,
                "target_price": 70000.0,
                "slice_count": 2,
            }
            tranches = await daemon.submit_order_plan(plan)
            self.assertEqual(len(tranches), 2)
            self.assertEqual(len(daemon.active_orders), 2)

            # Trigger emergency halt
            await daemon.trigger_emergency_halt("Test Halt Gate")
            self.assertEqual(daemon.session_state, DaemonSessionState.EMERGENCY_HALT)
            self.assertEqual(len(daemon.active_orders), 0)

            # Attempt submission after halt
            plan_post = {
                "order_id": "P_POST_HALT",
                "symbol": "005930",
                "action": "BUY",
                "quantity": 500,
                "target_price": 70000.0,
            }
            rejected_tranches = await daemon.submit_order_plan(plan_post)
            self.assertEqual(len(rejected_tranches), 0, "Orders must be rejected during EMERGENCY_HALT!")
            self.assertEqual(len(daemon.active_orders), 0)

            await daemon.stop()

        asyncio.run(_test())

    def test_adv07_threadsafe_multi_producer_flood_with_kill_switch(self):
        """
        ADV-07: Ingest 8,000 events across 4 background threads via enqueue_event_threadsafe
        while submitting an emergency kill switch from a 5th thread.
        Verify zero race condition exceptions, correct prioritization, and zero deadlock.
        """
        async def _test():
            daemon = LiveTradingDaemon(config=self.config)
            await daemon.start()
            daemon.set_session_state(DaemonSessionState.CONTINUOUS_TRADING)

            ticks_per_worker = 2000
            worker_count = 4

            def _producer(worker_id):
                for j in range(ticks_per_worker):
                    evt = PrioritizedDaemonEvent(
                        priority=DaemonPriority.LOW,
                        sequence_id=daemon._next_sequence_id(),
                        timestamp_ns=time.perf_counter_ns(),
                        event_type=DaemonEventType.MARKET_TICK,
                        payload={"worker": worker_id, "idx": j, "symbol": "005930", "price": 75000.0, "volume": 10.0},
                    )
                    daemon.enqueue_event_threadsafe(evt)

            def _kill_producer():
                time.sleep(0.01)  # small delay so flood is underway
                evt = PrioritizedDaemonEvent(
                    priority=DaemonPriority.EMERGENCY,
                    sequence_id=daemon._next_sequence_id(),
                    timestamp_ns=time.perf_counter_ns(),
                    event_type=DaemonEventType.KILL_SWITCH_TRIP,
                    payload={"reason": "THREAD_KILL_SWITCH"},
                )
                daemon.enqueue_event_threadsafe(evt)

            # Launch threads in parallel executor
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(_producer, i) for i in range(worker_count)]
                kill_future = executor.submit(_kill_producer)
                for f in futures:
                    f.result(timeout=10.0)
                kill_future.result(timeout=5.0)

            # Allow loop to process the kill switch
            for _ in range(50):
                if daemon.session_state == DaemonSessionState.EMERGENCY_HALT:
                    break
                await asyncio.sleep(0.02)

            self.assertEqual(daemon.session_state, DaemonSessionState.EMERGENCY_HALT)
            self.assertGreaterEqual(daemon.metrics["circuit_breaker_trips"], 1)

            await daemon.stop()

        asyncio.run(_test())

    def test_adv08_broker_exception_resilience_during_emergency_cancel(self):
        """
        ADV-08: Verify that if broker connector throws an exception or network timeout
        during emergency cancel, the daemon catches it, safely marks orders as CANCELLED,
        maintains zero orphaned active orders, and does not crash.
        """
        async def _test():
            class _FailingBroker:
                async def cancel_order(self, order_id, symbol=None, quantity=None):
                    raise ConnectionResetError("Broker gateway network disconnect!")

            daemon = LiveTradingDaemon(config=self.config, broker_connector=_FailingBroker())
            await daemon.start()

            for i in range(10):
                tid = f"FAIL_TR_{i}"
                daemon.active_orders[tid] = LiveTrancheOrder(
                    tranche_id=tid,
                    parent_order_id="P_FAIL",
                    symbol="005930",
                    quantity=10,
                    target_price=70000.0,
                    status="SUBMITTED",
                    broker_order_id=f"BRK_FAIL_{i}",
                )

            res = await daemon.emergency_cancel_all()

            # Resiliency assertion: all 10 orders must still be removed from active_orders!
            self.assertEqual(res["canceled_count"], 10)
            self.assertEqual(res["orphaned_count"], 0)
            self.assertEqual(len(daemon.active_orders), 0)
            self.assertEqual(len(daemon.completed_orders), 10)
            for o in daemon.completed_orders:
                self.assertEqual(o.status, "CANCELLED")

            await daemon.stop()

        asyncio.run(_test())


if __name__ == "__main__":
    unittest.main()
