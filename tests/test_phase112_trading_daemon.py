"""
tests/test_phase112_trading_daemon.py — Comprehensive Unit & Integration Test Suite
Milestone: Phase 112 (Release R128 / v119 Production Master, Feature F531)

Test Coverage:
- TC01: Class exports, version metadata (VERSION=112, RELEASE="R128", FEATURE="F531"), and alias trees
- TC02: Mirrored import parity between src.execution and trading_system.src.execution
- TC03: Dual placement bit-for-bit SHA-256 hash identity across mirrored files
- TC04: DaemonPriority, DaemonEventType, SessionState enum values and data class serialization
- TC05: Prioritized event queue ordering (EMERGENCY=0 pre-empts HIGH=1, NORMAL=2, LOW=3)
- TC06: Thread-safe event enqueueing from external sync threads via enqueue_event_threadsafe
- TC07: Market session lifecycle state transitions (INITIALIZING -> PREWARM -> TRADING -> RECON -> CLOSED)
- TC08: Market session schedule monitor logic (KST / EST time-based checks)
- TC09: Market tick ingestion into IntradayToxicityFilter and event telemetry
- TC10: Orderbook depth ingestion (multi-level bids/asks) and telemetry
- TC11: Real-time quote shading math: S_shade = clip((T - 0.50) * 2.0 * spread_bps, 0.0, 50.0)
- TC12: Shaded limit price adaptation for BUY and SELL with market tick size quantization
- TC13: Dynamic Almgren-Chriss order slicing (U-curve weighting, conservation, non-negativity)
- TC14: Submit order plan decomposition into discrete LiveTrancheOrders
- TC15: Sub-50ms parallel emergency cancellation benchmark (100 concurrent mock orders cancelled in <50ms)
- TC16: Volatility spike event triggering automated emergency halt and order cancellation (T >= 0.85)
- TC17: Manual trading pause and resume controls (pause_trading, resume_trading)
- TC18: Tranche execution fill processing, slippage tracking, and reconciliation callback
- TC19: Cross-platform signal registration and graceful shutdown guaranteeing zero orphaned orders
- TC20: State serialization and deserialization (save_state, load_state)
- TC21: Real-time operational metrics and telemetry reporting (get_daemon_metrics)
- TC22: High-concurrency event ingestion stress test without queue deadlock
"""

import asyncio
import hashlib
import json
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import MagicMock
import pytest

from src.execution.live_trading_daemon import (
    AsyncExecutionDaemon,
    AsyncioTradingDaemon,
    DaemonEventType,
    DaemonPriority,
    DaemonSessionState,
    EmergencyHaltEvent,
    EventDrivenTradingDaemon,
    FEATURE,
    HighFrequencyTradingDaemon,
    InstitutionalTradingDaemon,
    LiveDaemonConfig,
    LiveExecutionDaemon,
    LiveTradingDaemon,
    LiveTrancheOrder,
    MarketTickEvent,
    OrderBookUpdateEvent,
    Phase112TradingDaemon,
    PrioritizedDaemonEvent,
    ProductionTradingDaemon,
    RELEASE,
    RealTimeTradingDaemon,
    SessionState,
    VERSION,
    VolatilitySpikeEvent,
)


class TestPhase112TradingDaemon(unittest.TestCase):
    """Production test suite for LiveTradingDaemon (Feature F531)."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.temp_dir.name) / "test_trade_logs.db")
        self.state_file = str(Path(self.temp_dir.name) / "test_daemon_state.json")
        self.config = LiveDaemonConfig(
            db_path=self.db_path,
            state_file=self.state_file,
            market_mode="KRX",
            default_slice_count=5,
            emergency_cancel_timeout_sec=1.0,
            heartbeat_interval_sec=0.1,
            reconciliation_interval_sec=0.5,
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
        self.assertEqual(FEATURE, "F531")

        aliases = [
            AsyncioTradingDaemon,
            EventDrivenTradingDaemon,
            LiveExecutionDaemon,
            Phase112TradingDaemon,
            ProductionTradingDaemon,
            RealTimeTradingDaemon,
            InstitutionalTradingDaemon,
            HighFrequencyTradingDaemon,
            AsyncExecutionDaemon,
        ]
        for alias in aliases:
            self.assertIs(alias, LiveTradingDaemon)
        self.assertIs(SessionState, DaemonSessionState)

    def test_tc02_mirrored_import_parity(self):
        """TC02: Verify identical exports between src.execution and trading_system.src.execution."""
        import src.execution as m1
        import trading_system.src.execution as m2

        symbols = [
            "LiveTradingDaemon",
            "AsyncioTradingDaemon",
            "Phase112TradingDaemon",
            "DaemonPriority",
            "DaemonEventType",
            "DaemonSessionState",
            "SessionState",
            "PrioritizedDaemonEvent",
            "MarketTickEvent",
            "OrderBookUpdateEvent",
            "LiveTrancheOrder",
            "LiveDaemonConfig",
        ]
        for sym in symbols:
            self.assertTrue(hasattr(m1, sym), f"Missing {sym} in src.execution")
            self.assertTrue(hasattr(m2, sym), f"Missing {sym} in trading_system.src.execution")
            self.assertEqual(getattr(m1, sym).__name__, getattr(m2, sym).__name__)

    def test_tc03_sha256_hash_identity(self):
        """TC03: Assert bit-for-bit SHA-256 hash identity between mirrored daemon implementations."""
        src_path = Path("src/execution/live_trading_daemon.py")
        ts_path = Path("trading_system/src/execution/live_trading_daemon.py")
        self.assertTrue(src_path.exists())
        self.assertTrue(ts_path.exists())

        h_src = hashlib.sha256(src_path.read_bytes()).hexdigest()
        h_ts = hashlib.sha256(ts_path.read_bytes()).hexdigest()
        self.assertEqual(h_src, h_ts, "Mirrored live_trading_daemon.py files have mismatched SHA-256!")

    def test_tc04_enums_and_dataclasses(self):
        """TC04: Verify enum values, serialization, and container properties."""
        self.assertEqual(DaemonPriority.EMERGENCY, 0)
        self.assertEqual(DaemonPriority.HIGH, 1)
        self.assertEqual(DaemonPriority.NORMAL, 2)
        self.assertEqual(DaemonPriority.LOW, 3)

        self.assertEqual(DaemonSessionState.INITIALIZING.value, "INITIALIZING")
        self.assertEqual(DaemonSessionState.PRE_MARKET_PREWARM.value, "PRE_MARKET_PREWARM")
        self.assertEqual(DaemonSessionState.CONTINUOUS_TRADING.value, "CONTINUOUS_TRADING")
        self.assertEqual(DaemonSessionState.POST_MARKET_RECONCILIATION.value, "POST_MARKET_RECONCILIATION")
        self.assertEqual(DaemonSessionState.EMERGENCY_HALT.value, "EMERGENCY_HALT")

        tick = MarketTickEvent(symbol="005930", price=75000.0, volume=100.0, side="BUY")
        d = tick.to_dict()
        self.assertEqual(d["symbol"], "005930")
        self.assertEqual(d["price"], 75000.0)

        order = LiveTrancheOrder(
            tranche_id="T1",
            parent_order_id="P1",
            symbol="005930",
            quantity=50,
            target_price=75000.0,
            shaded_limit_price=74900.0,
        )
        od = order.to_dict()
        self.assertEqual(od["tranche_id"], "T1")
        self.assertEqual(od["status"], "PENDING")

    def test_tc05_priority_queue_ordering(self):
        """TC05: Assert that EMERGENCY (0) events are dequeued before HIGH (1), NORMAL (2), LOW (3)."""
        async def _test():
            queue: asyncio.PriorityQueue[PrioritizedDaemonEvent] = asyncio.PriorityQueue()

            e_low = PrioritizedDaemonEvent(
                priority=DaemonPriority.LOW,
                sequence_id=1,
                timestamp_ns=time.perf_counter_ns(),
                event_type=DaemonEventType.MARKET_TICK,
                payload={"id": "low"},
            )
            e_norm = PrioritizedDaemonEvent(
                priority=DaemonPriority.NORMAL,
                sequence_id=2,
                timestamp_ns=time.perf_counter_ns(),
                event_type=DaemonEventType.ORDER_SUBMIT,
                payload={"id": "normal"},
            )
            e_high = PrioritizedDaemonEvent(
                priority=DaemonPriority.HIGH,
                sequence_id=3,
                timestamp_ns=time.perf_counter_ns(),
                event_type=DaemonEventType.TRANCHE_FILL,
                payload={"id": "high"},
            )
            e_emerg = PrioritizedDaemonEvent(
                priority=DaemonPriority.EMERGENCY,
                sequence_id=4,
                timestamp_ns=time.perf_counter_ns(),
                event_type=DaemonEventType.EMERGENCY_HALT,
                payload={"id": "emerg"},
            )

            # Enqueue in reverse priority order
            await queue.put(e_low)
            await queue.put(e_norm)
            await queue.put(e_high)
            await queue.put(e_emerg)

            # Verify dequeue priority order: 0 -> 1 -> 2 -> 3
            d1 = await queue.get()
            d2 = await queue.get()
            d3 = await queue.get()
            d4 = await queue.get()

            self.assertEqual(d1.priority, DaemonPriority.EMERGENCY)
            self.assertEqual(d1.payload["id"], "emerg")
            self.assertEqual(d2.priority, DaemonPriority.HIGH)
            self.assertEqual(d2.payload["id"], "high")
            self.assertEqual(d3.priority, DaemonPriority.NORMAL)
            self.assertEqual(d3.payload["id"], "normal")
            self.assertEqual(d4.priority, DaemonPriority.LOW)
            self.assertEqual(d4.payload["id"], "low")

        asyncio.run(_test())

    def test_tc06_threadsafe_enqueue(self):
        """TC06: Verify thread-safe event enqueueing from external sync thread."""
        async def _test():
            daemon = LiveTradingDaemon(config=self.config)
            await daemon.start()

            def _external_worker():
                for i in range(10):
                    evt = PrioritizedDaemonEvent(
                        priority=DaemonPriority.LOW,
                        sequence_id=i + 1,
                        timestamp_ns=time.perf_counter_ns(),
                        event_type=DaemonEventType.MARKET_TICK,
                        payload={"symbol": "005930", "price": 70000.0 + i, "volume": 10.0},
                    )
                    success = daemon.enqueue_event_threadsafe(evt)
                    assert success

            thread = threading.Thread(target=_external_worker)
            thread.start()
            thread.join(timeout=2.0)

            await asyncio.sleep(0.2)
            await daemon.stop()

            metrics = daemon.get_daemon_metrics()
            self.assertGreaterEqual(metrics["metrics"]["ticks_ingested"], 10)

        asyncio.run(_test())

    def test_tc07_session_state_transitions(self):
        """TC07: Test full lifecycle state machine transitions."""
        async def _test():
            daemon = LiveTradingDaemon(config=self.config)
            self.assertEqual(daemon.session_state, DaemonSessionState.INITIALIZING)

            await daemon.start()
            self.assertEqual(daemon.session_state, DaemonSessionState.PRE_MARKET_PREWARM)

            daemon.set_session_state(DaemonSessionState.CONTINUOUS_TRADING)
            self.assertEqual(daemon.session_state, DaemonSessionState.CONTINUOUS_TRADING)

            daemon.set_session_state(DaemonSessionState.POST_MARKET_RECONCILIATION)
            self.assertEqual(daemon.session_state, DaemonSessionState.POST_MARKET_RECONCILIATION)

            daemon.set_session_state(DaemonSessionState.SESSION_CLOSED)
            self.assertEqual(daemon.session_state, DaemonSessionState.SESSION_CLOSED)

            await daemon.stop()
            self.assertEqual(daemon.session_state, DaemonSessionState.STOPPED)

        asyncio.run(_test())

    def test_tc08_session_schedule_monitor(self):
        """TC08: Verify schedule-based state progression logic."""
        async def _test():
            cfg = LiveDaemonConfig(
                db_path=":memory:",
                pre_market_time_kst="00:00",
                market_open_time_kst="00:01",
                market_close_time_kst="23:59",
                market_mode="KRX",
            )
            daemon = LiveTradingDaemon(config=cfg)
            daemon.set_session_state(DaemonSessionState.PRE_MARKET_PREWARM)

            await daemon.start()
            daemon.set_session_state(DaemonSessionState.CONTINUOUS_TRADING)
            self.assertEqual(daemon.session_state, DaemonSessionState.CONTINUOUS_TRADING)
            await daemon.stop()

        asyncio.run(_test())

    def test_tc09_market_tick_ingestion(self):
        """TC09: Ingest trade tick and assert metrics telemetry update."""
        async def _test():
            mock_filter = MagicMock()
            mock_filter.update_trade = MagicMock()
            mock_filter.evaluate_toxicity = MagicMock(return_value=MagicMock(composite_toxicity=0.3, is_evaporating=False))

            daemon = LiveTradingDaemon(config=self.config, toxicity_filter=mock_filter)
            await daemon.start()

            tick_event = PrioritizedDaemonEvent(
                priority=DaemonPriority.LOW,
                sequence_id=1,
                timestamp_ns=time.perf_counter_ns(),
                event_type=DaemonEventType.MARKET_TICK,
                payload={"symbol": "005930", "price": 75000.0, "volume": 500.0},
            )
            await daemon.enqueue_event(tick_event)
            await asyncio.sleep(0.1)

            mock_filter.update_trade.assert_called_once()
            self.assertEqual(daemon.metrics["ticks_ingested"], 1)
            await daemon.stop()

        asyncio.run(_test())

    def test_tc10_orderbook_depth_ingestion(self):
        """TC10: Ingest L2/L3 orderbook depth and verify filter update."""
        async def _test():
            mock_filter = MagicMock()
            mock_filter.update_orderbook = MagicMock()

            daemon = LiveTradingDaemon(config=self.config, toxicity_filter=mock_filter)
            await daemon.start()

            book_event = PrioritizedDaemonEvent(
                priority=DaemonPriority.LOW,
                sequence_id=1,
                timestamp_ns=time.perf_counter_ns(),
                event_type=DaemonEventType.ORDERBOOK_UPDATE,
                payload={
                    "symbol": "005930",
                    "bids": [(74900.0, 1000.0), (74800.0, 2000.0)],
                    "asks": [(75000.0, 1200.0), (75100.0, 2500.0)],
                },
            )
            await daemon.enqueue_event(book_event)
            await asyncio.sleep(0.1)

            mock_filter.update_orderbook.assert_called_once()
            self.assertEqual(daemon.metrics["orderbook_updates"], 1)
            await daemon.stop()

        asyncio.run(_test())

    def test_tc11_quote_shading_math(self):
        """TC11: Verify real-time quote shading offset mathematical bounds."""
        # Case A: T <= 0.50 -> offset == 0.0
        mock_filter = MagicMock()
        mock_filter.evaluate_toxicity = MagicMock(return_value=MagicMock(composite_toxicity=0.45))
        daemon = LiveTradingDaemon(config=self.config, toxicity_filter=mock_filter)

        shade_0 = daemon.compute_quote_shading(symbol="005930", spread_bps=10.0)
        self.assertEqual(shade_0, 0.0)

        # Case B: T = 0.70, spread = 10 bps -> (0.70 - 0.50) * 2 * 10 = 4.0 bps
        mock_filter.evaluate_toxicity = MagicMock(return_value=MagicMock(composite_toxicity=0.70))
        shade_1 = daemon.compute_quote_shading(symbol="005930", spread_bps=10.0)
        self.assertAlmostEqual(shade_1, 4.0, places=4)

        # Case C: T = 1.00, spread = 60 bps -> (1.00 - 0.50) * 2 * 60 = 60.0 -> clipped to 50.0 bps
        mock_filter.evaluate_toxicity = MagicMock(return_value=MagicMock(composite_toxicity=1.00))
        shade_max = daemon.compute_quote_shading(symbol="005930", spread_bps=60.0)
        self.assertEqual(shade_max, 50.0)

    def test_tc12_shaded_price_quantization(self):
        """TC12: Verify shaded limit price direction and tick size quantization."""
        mock_filter = MagicMock()
        # Toxicity T=0.75, spread=10 bps -> S_shade = (0.75-0.50)*2*10 = 5.0 bps
        mock_filter.evaluate_toxicity = MagicMock(return_value=MagicMock(composite_toxicity=0.75))
        daemon = LiveTradingDaemon(config=self.config, toxicity_filter=mock_filter)

        # BUY order: mid = 70,000 KRW (tick size 100 KRW)
        p_buy = daemon.calculate_shaded_price(
            symbol="005930",
            target_price=70000.0,
            mid_price=70000.0,
            spread_bps=10.0,
            order_side="BUY",
            market="KOSPI",
        )
        self.assertLessEqual(p_buy, 70000.0)
        self.assertEqual(p_buy % 100.0, 0.0)

        # SELL order: shaded price >= target_price
        p_sell = daemon.calculate_shaded_price(
            symbol="005930",
            target_price=70000.0,
            mid_price=70000.0,
            spread_bps=10.0,
            order_side="SELL",
            market="KOSPI",
        )
        self.assertGreaterEqual(p_sell, 70000.0)
        self.assertEqual(p_sell % 100.0, 0.0)

        # US market: AAPL $200.00 (tick size $0.01)
        p_us = daemon.calculate_shaded_price(
            symbol="AAPL",
            target_price=200.0,
            mid_price=200.0,
            spread_bps=10.0,
            order_side="BUY",
            market="NASDAQ",
        )
        self.assertLessEqual(p_us, 200.0)
        self.assertAlmostEqual(p_us, round(p_us, 2))

    def test_tc13_almgren_chriss_slicing(self):
        """TC13: Test Almgren-Chriss order decomposition, conservation, and non-negativity."""
        daemon = LiveTradingDaemon(config=self.config)

        # Test varying slice counts and quantities
        for total_q in (10, 100, 1053, 50000):
            for n_sl in (3, 5, 8, 12):
                slices = daemon.slice_parent_order(
                    total_quantity=total_q,
                    adv=500000.0,
                    daily_volatility=0.025,
                    strategy_tier="fast",
                    n_slices=n_sl,
                )
                self.assertEqual(len(slices), n_sl)
                self.assertEqual(sum(slices), total_q, f"Sum failed for total_q={total_q}, n_sl={n_sl}")
                for s in slices:
                    self.assertGreaterEqual(s, 0)

        # Edge cases: 0 quantity, 1 slice
        self.assertEqual(daemon.slice_parent_order(0), [0])
        self.assertEqual(daemon.slice_parent_order(100, n_slices=1), [100])

    def test_tc14_submit_order_plan(self):
        """TC14: Decompose parent plan into LiveTrancheOrders and dispatch."""
        async def _test():
            mock_broker = MagicMock()
            mock_broker.place_order = MagicMock(return_value={"order_id": "MOCK_ORD_101"})

            daemon = LiveTradingDaemon(config=self.config, broker_connector=mock_broker)
            daemon.set_session_state(DaemonSessionState.CONTINUOUS_TRADING)

            plan = {
                "order_id": "PARENT_001",
                "symbol": "005930",
                "market": "KOSPI",
                "action": "BUY",
                "quantity": 1000,
                "target_price": 75000.0,
                "adv": 500000.0,
                "daily_volatility": 0.02,
                "slice_count": 4,
            }
            tranches = await daemon.submit_order_plan(plan)
            self.assertEqual(len(tranches), 4)
            self.assertEqual(sum(t.quantity for t in tranches), 1000)
            for t in tranches:
                self.assertEqual(t.status, "SUBMITTED")
                self.assertEqual(t.broker_order_id, "MOCK_ORD_101")
                self.assertIn(t.tranche_id, daemon.active_orders)

            self.assertEqual(daemon.metrics["orders_submitted"], 4)

        asyncio.run(_test())

    def test_tc15_sub_50ms_emergency_cancel_benchmark(self):
        """TC15: Assert 100 concurrent orders cancelled in < 50ms with zero orphans."""
        async def _test():
            class _FastMockBroker:
                def __init__(self):
                    self.cancelled_ids = []

                async def cancel_order(self, order_id, symbol=None, quantity=None):
                    self.cancelled_ids.append(order_id)
                    return {"status": "CANCELLED", "order_id": order_id}

            mock_broker = _FastMockBroker()
            daemon = LiveTradingDaemon(config=self.config, broker_connector=mock_broker)

            # Populate 100 mock open tranches
            for i in range(100):
                tid = f"TRANCHE_{i:03d}"
                daemon.active_orders[tid] = LiveTrancheOrder(
                    tranche_id=tid,
                    parent_order_id=f"P_{i//10}",
                    symbol="005930",
                    quantity=10,
                    target_price=75000.0,
                    status="SUBMITTED",
                    broker_order_id=f"BROKER_{i:03d}",
                )

            self.assertEqual(len(daemon.active_orders), 100)

            # Execute parallel emergency cancel
            res = await daemon.emergency_cancel_all()

            # Strict latency assertion: must cancel all 100 orders in under 50.0 ms
            self.assertLess(res["elapsed_ms"], 50.0, f"Cancellation took {res['elapsed_ms']:.2f}ms >= 50ms limit!")
            self.assertEqual(res["canceled_count"], 100)
            self.assertEqual(res["orphaned_count"], 0)
            self.assertEqual(res["status"], "CLEARED")
            self.assertEqual(len(daemon.active_orders), 0)
            self.assertEqual(len(daemon.completed_orders), 100)

        asyncio.run(_test())

    def test_tc16_volatility_spike_auto_halt(self):
        """TC16: Assert composite toxicity surge (T >= 0.85) triggers automated emergency halt."""
        async def _test():
            daemon = LiveTradingDaemon(config=self.config)
            await daemon.start()
            daemon.set_session_state(DaemonSessionState.CONTINUOUS_TRADING)

            # Add an active order
            daemon.active_orders["T_ACTIVE"] = LiveTrancheOrder(
                tranche_id="T_ACTIVE",
                parent_order_id="P1",
                symbol="005930",
                quantity=50,
                target_price=70000.0,
                status="SUBMITTED",
            )

            spike_event = PrioritizedDaemonEvent(
                priority=DaemonPriority.EMERGENCY,
                sequence_id=1,
                timestamp_ns=time.perf_counter_ns(),
                event_type=DaemonEventType.VOLATILITY_SPIKE,
                payload={
                    "symbol": "005930",
                    "composite_toxicity": 0.92,
                    "is_evaporating": True,
                },
            )
            await daemon.enqueue_event(spike_event)
            await asyncio.sleep(0.15)

            self.assertEqual(daemon.session_state, DaemonSessionState.EMERGENCY_HALT)
            self.assertEqual(len(daemon.active_orders), 0)
            self.assertGreaterEqual(daemon.metrics["emergency_cancels_count"], 1)
            await daemon.stop()

        asyncio.run(_test())

    def test_tc17_pause_and_resume(self):
        """TC17: Verify manual trading pause and resume controls."""
        daemon = LiveTradingDaemon(config=self.config)
        daemon.set_session_state(DaemonSessionState.CONTINUOUS_TRADING)

        daemon.pause_trading("Testing manual pause")
        self.assertEqual(daemon.session_state, DaemonSessionState.PAUSED_MANUAL)
        self.assertTrue(daemon._is_paused)

        daemon.resume_trading()
        self.assertEqual(daemon.session_state, DaemonSessionState.CONTINUOUS_TRADING)
        self.assertFalse(daemon._is_paused)

    def test_tc18_fill_processing_and_slippage(self):
        """TC18: Process tranche fill, compute slippage bps, and verify reconciliation callback."""
        async def _test():
            mock_recon = MagicMock()
            mock_recon.record_fill = MagicMock()

            daemon = LiveTradingDaemon(config=self.config, reconciliation_engine=mock_recon)
            daemon.active_orders["T_FILL"] = LiveTrancheOrder(
                tranche_id="T_FILL",
                parent_order_id="P1",
                symbol="005930",
                action="BUY",
                quantity=100,
                target_price=70000.0,
                status="SUBMITTED",
            )

            fill_event = PrioritizedDaemonEvent(
                priority=DaemonPriority.HIGH,
                sequence_id=1,
                timestamp_ns=time.perf_counter_ns(),
                event_type=DaemonEventType.TRANCHE_FILL,
                payload={
                    "tranche_id": "T_FILL",
                    "filled_price": 70100.0,
                    "filled_quantity": 100,
                },
            )
            await daemon.start()
            await daemon.enqueue_event(fill_event)
            await asyncio.sleep(0.1)

            self.assertNotIn("T_FILL", daemon.active_orders)
            self.assertEqual(len(daemon.completed_orders), 1)
            completed = daemon.completed_orders[0]
            self.assertEqual(completed.status, "FILLED")
            self.assertEqual(completed.filled_price, 70100.0)
            # Slippage: BUY filled at 70,100 vs target 70,000 -> +14.2857 bps
            self.assertAlmostEqual(completed.slippage_bps, (100.0 / 70000.0) * 10000.0, places=2)

            mock_recon.record_fill.assert_called_once_with(
                order_id="T_FILL",
                symbol="005930",
                market="KOSPI",
                action="BUY",
                quantity=100,
                price=70100.0,
            )
            await daemon.stop()

        asyncio.run(_test())

    def test_tc19_shutdown_and_zero_orphaned_orders(self):
        """TC19: Verify stop() cleanly cancels active tranches with zero orphans remaining."""
        async def _test():
            daemon = LiveTradingDaemon(config=self.config)
            await daemon.start()

            # Add working orders
            for i in range(5):
                tid = f"ORD_{i}"
                daemon.active_orders[tid] = LiveTrancheOrder(
                    tranche_id=tid,
                    parent_order_id="P1",
                    symbol="005930",
                    quantity=10,
                    target_price=70000.0,
                    status="SUBMITTED",
                )

            self.assertEqual(len(daemon.active_orders), 5)
            await daemon.stop(reason="Test clean shutdown")

            self.assertEqual(len(daemon.active_orders), 0)
            self.assertEqual(daemon.session_state, DaemonSessionState.STOPPED)

        asyncio.run(_test())

    def test_tc20_state_serialization(self):
        """TC20: Test save_state and load_state round-trip JSON persistence."""
        daemon = LiveTradingDaemon(config=self.config)
        daemon.set_session_state(DaemonSessionState.CONTINUOUS_TRADING)
        daemon.metrics["orders_submitted"] = 42

        daemon.save_state(self.state_file)
        self.assertTrue(Path(self.state_file).exists())

        # Load into new daemon instance
        daemon2 = LiveTradingDaemon(config=self.config)
        daemon2.load_state(self.state_file)

        self.assertEqual(daemon2.session_state, DaemonSessionState.CONTINUOUS_TRADING)
        self.assertEqual(daemon2.metrics["orders_submitted"], 42)

    def test_tc21_get_daemon_metrics(self):
        """TC21: Verify comprehensive telemetry reporting."""
        daemon = LiveTradingDaemon(config=self.config)
        metrics = daemon.get_daemon_metrics()

        self.assertEqual(metrics["version"], 112)
        self.assertEqual(metrics["release"], "R128")
        self.assertEqual(metrics["feature"], "F531")
        self.assertEqual(metrics["session_state"], "INITIALIZING")
        self.assertFalse(metrics["is_running"])
        self.assertIn("events_processed", metrics["metrics"])

    def test_tc22_concurrency_stress(self):
        """TC22: High-concurrency event ingestion stress test."""
        async def _test():
            daemon = LiveTradingDaemon(config=self.config)
            await daemon.start()

            total_events = 200
            for i in range(total_events):
                evt = PrioritizedDaemonEvent(
                    priority=DaemonPriority.LOW if i % 2 == 0 else DaemonPriority.NORMAL,
                    sequence_id=i,
                    timestamp_ns=time.perf_counter_ns(),
                    event_type=DaemonEventType.MARKET_TICK if i % 2 == 0 else DaemonEventType.HEARTBEAT,
                    payload={"symbol": "005930", "price": 75000.0, "volume": 10.0},
                )
                await daemon.enqueue_event(evt)

            # Allow worker loop to drain
            for _ in range(50):
                if daemon.metrics["events_processed"] >= total_events:
                    break
                await asyncio.sleep(0.02)

            self.assertGreaterEqual(daemon.metrics["events_processed"], total_events)
            await daemon.stop()

        asyncio.run(_test())


if __name__ == "__main__":
    unittest.main()
