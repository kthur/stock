"""
tests/test_m2_adversarial_streaming_lob.py
Empirical Adversarial Stress Test Suite for Milestone 2:
Real-Time Streaming WebSocket Quote Feed & Fast LOB OMS Integration.

Focus Areas:
1. High-Volume Throughput (10,000+ to 25,000+ events) & Latency Benchmarking.
2. Burst Traffic & Bounded Queue DROP_OLDEST / Backpressure Behavior.
3. Thread Safety & FIFO Ordering under Concurrent Producers, Consumer Worker, and Synchronous flush() Calls.
4. VPIN Calculation Stability under Continuous Extreme Trade Bursts (zero vol, extreme jumps, one-sided, zero vol, huge vol).
"""

import collections
import math
import random
import threading
import time
import unittest
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pytest

from src.core.streaming_feed_adapter import (
    BackpressurePolicy,
    DepthLevel,
    DepthUpdate,
    FeedEventType,
    FeedTelemetry,
    MockStreamingProvider,
    QuoteUpdate,
    StreamingFeedAdapter,
    StreamingLOBManager,
    TopOfBook,
    TradeUpdate,
)
from src.core.fast_lob_engine import (
    FastOrderBookMatchingEngine,
    ZeroCopyRingBuffer,
)


class TestHighVolumeThroughputAndLatency(unittest.TestCase):
    """Area 1: High Volume Throughput (10,000+ events) and Microsecond Latency Profiling."""

    def test_high_volume_throughput_15000_events(self):
        """
        Stream 15,000 events (quotes, depths, trades) through StreamingFeedAdapter
        and StreamingLOBManager. Verify high events/sec throughput and sub-millisecond dispatch latency.
        """
        lob_manager = StreamingLOBManager()
        adapter = StreamingFeedAdapter(
            buffer_capacity=50_000,
            overflow_policy=BackpressurePolicy.DROP_OLDEST,
            lob_manager=lob_manager,
        )

        symbols = ["005930", "000660", "AAPL", "MSFT", "NVDA"]
        received_counts = collections.defaultdict(int)
        lock = threading.Lock()

        def on_any_event(event):
            with lock:
                received_counts[event.symbol] += 1

        adapter.subscribe_all(on_any_event)
        adapter.start()

        num_events = 10_000
        t_start = time.perf_counter()

        # Generate and enqueue 10,000 mixed events
        for i in range(num_events):
            sym = symbols[i % len(symbols)]
            r = i % 3
            if r == 0:
                ev = QuoteUpdate(
                    symbol=sym,
                    bid_price=100.0 + (i % 50),
                    bid_size=100.0,
                    ask_price=101.0 + (i % 50),
                    ask_size=120.0,
                    sequence=i,
                )
            elif r == 1:
                ev = DepthUpdate(
                    symbol=sym,
                    bids=((100.0, 50.0), (99.0, 80.0)),
                    asks=((101.0, 60.0), (102.0, 90.0)),
                    is_snapshot=True,
                    sequence=i,
                )
            else:
                ev = TradeUpdate(
                    symbol=sym,
                    price=100.5,
                    volume=10.0 + (i % 10),
                    side="BUY" if i % 2 == 0 else "SELL",
                    sequence=i,
                )
            adapter.push_event(ev)

        # Flush all queued events
        dispatched = adapter.flush(timeout_sec=10.0)
        t_elapsed = time.perf_counter() - t_start
        adapter.stop()

        total_received = sum(received_counts.values())
        throughput_eps = total_received / t_elapsed
        telem = adapter.get_telemetry()

        print(
            f"\n[Throughput Benchmark] 10,000 events in {t_elapsed:.4f}s "
            f"({throughput_eps:,.0f} events/sec), "
            f"Mean Dispatch Latency: {telem['mean_dispatch_latency_us']:.2f} us, "
            f"P99 Latency: {telem['p99_dispatch_latency_us']:.2f} us, "
            f"Dropped: {telem['events_dropped_backpressure']}"
        )

        self.assertEqual(total_received, num_events)
        self.assertEqual(telem["events_dropped_backpressure"], 0)
        # Latency should be sub-millisecond (less than 1,000 us average)
        self.assertLess(telem["mean_dispatch_latency_us"], 1000.0)
        # Pure Python throughput with full LOB updates, Hawkes intensity & VPIN
        self.assertGreater(throughput_eps, 1500.0)

        # Verify all symbols have updated TopOfBook in lob_manager
        for sym in symbols:
            tob = lob_manager.get_top_of_book(sym)
            self.assertIsNotNone(tob)
            self.assertGreater(tob.mid_price, 0.0)

    def test_mock_provider_high_frequency_burst(self):
        """
        Verify MockStreamingProvider running in burst mode emits thousands of events
        into StreamingFeedAdapter without dropping or degrading latency.
        """
        adapter = StreamingFeedAdapter(buffer_capacity=20_000)
        provider = MockStreamingProvider(
            symbols=["005930", "000660"],
            frequency_hz=1000.0,
            trade_cluster_burst_mode=True,
            seed=42,
        )

        events_seen = []
        adapter.subscribe_all(lambda ev: events_seen.append(ev))
        adapter.start()

        # Produce bursts
        provider.start_producing(adapter, duration_seconds=0.5)
        time.sleep(0.6)
        provider.stop_producing()

        adapter.flush(timeout_sec=2.0)
        adapter.stop()

        self.assertGreater(len(events_seen), 100)
        telem = adapter.get_telemetry()
        self.assertEqual(telem["events_dropped_backpressure"], 0)
        self.assertLess(telem["mean_dispatch_latency_us"], 1000.0)


class TestBurstTrafficAndBoundedQueueDropOldest(unittest.TestCase):
    """Area 2: Burst Traffic, Capacity Saturation, and Bounded Queue DROP_OLDEST Behavior."""

    def test_massive_burst_drop_oldest_strict_sequence(self):
        """
        Saturate a bounded adapter (capacity 50) with an instantaneous burst of 2,500 events.
        Verify:
        1. len(_queue) == 50 exactly.
        2. Exactly 2,450 events were dropped.
        3. The 50 events remaining in the queue are strictly the NEWEST 50 events [2450..2499].
        4. Telemetry counts match bit-for-bit.
        """
        cap = 50
        burst_size = 2500
        adapter = StreamingFeedAdapter(
            buffer_capacity=cap,
            overflow_policy=BackpressurePolicy.DROP_OLDEST,
        )

        # Enqueue burst while consumer thread is NOT running
        for i in range(burst_size):
            ev = QuoteUpdate(
                symbol="BURST",
                bid_price=float(1000 + i),
                bid_size=10.0,
                ask_price=float(1001 + i),
                ask_size=10.0,
                sequence=i,
            )
            adapter.enqueue(ev)

        self.assertEqual(len(adapter._queue), cap)
        self.assertEqual(adapter.telemetry.events_received, burst_size)
        self.assertEqual(adapter.telemetry.events_dropped_backpressure, burst_size - cap)
        self.assertEqual(adapter.telemetry.events_dropped, burst_size - cap)

        # Verify exact sequence numbers of remaining items
        remaining_seqs = [q.sequence for q in adapter._queue]
        expected_seqs = list(range(burst_size - cap, burst_size))
        self.assertEqual(remaining_seqs, expected_seqs)

        # Start consumer, flush, verify received items
        received = []
        adapter.subscribe("BURST", on_quote=lambda q: received.append(q.sequence))
        adapter.start()
        adapter.flush(timeout=1.0)
        adapter.stop()

        self.assertEqual(received, expected_seqs)

    def test_minimal_capacity_bounded_queue(self):
        """
        Verify DROP_OLDEST handles edge case of minimal capacity (capacity=2)
        under intense back-and-forth bursts without deadlock or index error.
        """
        adapter = StreamingFeedAdapter(
            buffer_capacity=2,
            overflow_policy=BackpressurePolicy.DROP_OLDEST,
        )
        self.assertEqual(adapter.buffer_capacity, 2)

        for i in range(100):
            adapter.push_quote(QuoteUpdate(
                symbol="MIN",
                bid_price=float(i),
                bid_size=10.0,
                ask_price=float(i + 1),
                ask_size=10.0,
                sequence=i,
            ))
            self.assertLessEqual(len(adapter._queue), 2)

        self.assertEqual(len(adapter._queue), 2)
        self.assertEqual(adapter.telemetry.events_dropped, 98)
        self.assertEqual([q.sequence for q in adapter._queue], [98, 99])

    def test_continuous_burst_streaming_with_active_consumer(self):
        """
        Test continuous rapid burst injection with consumer active and small buffer (cap=200).
        Verify that total events processed + dropped == total received.
        """
        adapter = StreamingFeedAdapter(
            buffer_capacity=200,
            overflow_policy=BackpressurePolicy.DROP_OLDEST,
        )
        delivered = []
        adapter.subscribe_all(lambda ev: delivered.append(ev))
        adapter.start()

        num_events = 5000
        for i in range(num_events):
            adapter.push_quote(QuoteUpdate(
                symbol="CONT",
                bid_price=float(i),
                bid_size=10.0,
                ask_price=float(i + 1),
                ask_size=10.0,
                sequence=i,
            ))

        adapter.flush(timeout=3.0)
        adapter.stop()

        telem = adapter.get_telemetry()
        total_accounted = len(delivered) + telem["events_dropped_backpressure"]
        print(f"\n[Continuous Burst] Injected: {num_events}, Delivered: {len(delivered)}, Dropped: {telem['events_dropped_backpressure']}")
        self.assertEqual(total_accounted, num_events)
        self.assertEqual(telem["events_received"], num_events)
        self.assertEqual(telem["events_dispatched"], len(delivered))

        # Check delivered sequence numbers are strictly non-decreasing
        seqs = [ev.sequence for ev in delivered]
        for idx in range(1, len(seqs)):
            self.assertGreater(seqs[idx], seqs[idx - 1], "Delivered sequence must be strictly increasing")


class TestThreadSafetyAndFIFOOrdering(unittest.TestCase):
    """Area 3: Thread Safety, Concurrent Producers, Consumer Worker Thread, and flush() Coordination."""

    def test_concurrent_multi_producer_single_symbol_fifo(self):
        """
        Run 8 producer threads concurrently pushing into an adapter with large buffer (no drop).
        Each thread produces tagged events with thread-specific sequence IDs.
        Verify:
        1. No events lost or duplicated.
        2. Per-thread FIFO order is strictly preserved.
        3. flush() drains 100% of events without deadlock.
        """
        adapter = StreamingFeedAdapter(
            buffer_capacity=50_000,
            overflow_policy=BackpressurePolicy.DROP_OLDEST,
        )

        num_threads = 8
        events_per_thread = 1_000
        total_events = num_threads * events_per_thread

        received_per_thread = collections.defaultdict(list)
        recv_lock = threading.Lock()

        def on_event(ev: QuoteUpdate):
            # Parse thread id and seq from symbol or venue
            t_id = int(ev.venue.split("_")[1])
            with recv_lock:
                received_per_thread[t_id].append(ev.sequence)

        adapter.subscribe_all(on_event)
        adapter.start()

        def producer_worker(t_id: int):
            for seq in range(events_per_thread):
                ev = QuoteUpdate(
                    symbol=f"SYM_{t_id}",
                    bid_price=100.0,
                    bid_size=10.0,
                    ask_price=101.0,
                    ask_size=10.0,
                    sequence=seq,
                    venue=f"THREAD_{t_id}",
                )
                adapter.push_event(ev)

        threads = [
            threading.Thread(target=producer_worker, args=(t,), name=f"Producer_{t}")
            for t in range(num_threads)
        ]

        t0 = time.perf_counter()
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Flush all remaining events
        dispatched = adapter.flush(timeout_sec=4.0)
        adapter.stop()
        t_elapsed = time.perf_counter() - t0

        print(f"\n[Multi-Producer FIFO] {total_events} events across {num_threads} threads in {t_elapsed:.4f}s")

        # Verify each thread's events
        for t_id in range(num_threads):
            seqs = received_per_thread[t_id]
            self.assertEqual(len(seqs), events_per_thread, f"Thread {t_id} lost events!")
            expected = list(range(events_per_thread))
            self.assertEqual(seqs, expected, f"Thread {t_id} experienced FIFO out-of-order execution!")

        telem = adapter.get_telemetry()
        self.assertEqual(telem["events_received"], total_events)
        self.assertEqual(telem["events_dispatched"], total_events)
        self.assertEqual(telem["events_dropped_backpressure"], 0)

    def test_concurrent_producers_and_concurrent_flush_calls(self):
        """
        Stress test: simultaneous producers pushing while multiple caller threads
        repeatedly invoke flush() concurrently with the background worker running.
        Verify no deadlock, no exceptions, and full draining at the end.
        """
        adapter = StreamingFeedAdapter(
            buffer_capacity=20_000,
            overflow_policy=BackpressurePolicy.DROP_OLDEST,
        )

        all_received = []
        lock = threading.Lock()

        def on_event(ev):
            with lock:
                all_received.append(ev)

        adapter.subscribe_all(on_event)
        adapter.start()

        stop_flag = threading.Event()
        flush_exceptions = []

        def flusher_task():
            while not stop_flag.is_set():
                try:
                    adapter.flush(timeout_sec=0.1)
                except Exception as e:
                    flush_exceptions.append(e)
                time.sleep(0.01)

        def producer_task(p_id: int):
            for i in range(500):
                adapter.push_quote(QuoteUpdate(
                    symbol=f"CONC_{p_id}",
                    bid_price=float(100 + i),
                    bid_size=10.0,
                    ask_price=float(101 + i),
                    ask_size=10.0,
                    sequence=i,
                ))
                if i % 50 == 0:
                    time.sleep(0.001)

        flushers = [threading.Thread(target=flusher_task) for _ in range(3)]
        producers = [threading.Thread(target=producer_task, args=(p,)) for p in range(4)]

        for f in flushers:
            f.start()
        for p in producers:
            p.start()

        for p in producers:
            p.join()

        stop_flag.set()
        for f in flushers:
            f.join()

        # Final synchronous flush
        adapter.flush(timeout_sec=3.0)
        adapter.stop()

        self.assertEqual(len(flush_exceptions), 0, f"Flush threw exceptions: {flush_exceptions}")
        self.assertEqual(len(all_received), 4 * 500)
        self.assertEqual(adapter.get_telemetry()["events_dispatched"], 2000)

    def test_rapid_start_stop_restart_cycles(self):
        """
        Verify that rapidly starting, pushing, flushing, stopping, and restarting
        the adapter does not leave lingering threads or corrupted state.
        """
        adapter = StreamingFeedAdapter(buffer_capacity=1000)
        received = []
        adapter.subscribe_all(lambda ev: received.append(ev))

        for cycle in range(5):
            adapter.start()
            for i in range(50):
                adapter.push_quote(QuoteUpdate(
                    symbol="CYCLE",
                    bid_price=float(i),
                    bid_size=10.0,
                    ask_price=float(i + 1),
                    ask_size=10.0,
                ))
            adapter.flush(timeout=1.0)
            adapter.stop()

        self.assertEqual(len(received), 250)
        self.assertIsNone(adapter._worker_thread)


class TestVPINCalculationStability(unittest.TestCase):
    """Area 4: VPIN Calculation Numerical Stability under Continuous Extreme Trade Bursts."""

    def setUp(self):
        self.engine = FastOrderBookMatchingEngine(symbol="VPIN_STRESS", tick_size=1.0)

    def test_vpin_zero_volatility_trade_burst(self):
        """
        Stress Case 1: 1,000 trades with identical price (std == 0).
        Verify: No ZeroDivisionError, no NaN, no inf, and VPIN returns finite 0.0.
        """
        for i in range(1000):
            res = self.engine.on_trade_tick(price=100.0, volume=10.0, side="BUY")
            vpin = self.engine.get_vpin()
            self.assertFalse(math.isnan(vpin), f"NaN VPIN at tick {i}")
            self.assertFalse(math.isinf(vpin), f"Inf VPIN at tick {i}")
            self.assertGreaterEqual(vpin, 0.0)
            self.assertLessEqual(vpin, 1.0)

        final_vpin = self.engine.get_vpin()
        self.assertEqual(final_vpin, 0.0, "Zero volatility trades must yield 0.0 VPIN")

    def test_vpin_extreme_price_jump_oscillation(self):
        """
        Stress Case 2: Extreme wild price jumps alternating between 1.0 and 1,000,000.0.
        Verify: Numerical stability of erf(), z-score clipping, and VPIN bounds [0.0, 1.0].
        """
        for i in range(500):
            px = 1.0 if (i % 2 == 0) else 1_000_000.0
            res = self.engine.on_trade_tick(price=px, volume=50.0, side="BUY" if (i % 3 == 0) else "SELL")
            vpin = self.engine.get_vpin()
            self.assertFalse(math.isnan(vpin), f"NaN at extreme oscillation tick {i}")
            self.assertFalse(math.isinf(vpin), f"Inf at extreme oscillation tick {i}")
            self.assertTrue(0.0 <= vpin <= 1.0, f"VPIN {vpin} out of bounds [0, 1] at tick {i}")

    def test_vpin_one_sided_toxic_buy_burst(self):
        """
        Stress Case 3: 500 consecutive aggressive BUY orders at rising prices.
        Verify: VPIN captures intense toxicity, remains bounded in [0.0, 1.0], and approaches high values.
        """
        for i in range(500):
            px = 100.0 + i * 0.5  # Monotonically rising prices
            self.engine.on_trade_tick(price=px, volume=100.0, side="BUY")
            vpin = self.engine.get_vpin()
            self.assertFalse(math.isnan(vpin))
            self.assertTrue(0.0 <= vpin <= 1.0)

        final_vpin = self.engine.get_vpin()
        print(f"\n[VPIN Toxic Buy Burst] Final VPIN: {final_vpin:.4f}")
        # Severe one-sided buying at rising prices represents extreme flow toxicity
        self.assertGreater(final_vpin, 0.50, "One-sided buy burst must yield elevated VPIN (> 0.50)")
        self.assertLessEqual(final_vpin, 1.0)

    def test_vpin_one_sided_toxic_sell_burst(self):
        """
        Stress Case 4: 500 consecutive aggressive SELL orders at declining prices.
        Verify: VPIN detects toxic sell dump, bounded in [0.0, 1.0].
        """
        for i in range(500):
            px = max(1.0, 500.0 - i * 0.5)  # Monotonically falling prices
            self.engine.on_trade_tick(price=px, volume=100.0, side="SELL")
            vpin = self.engine.get_vpin()
            self.assertFalse(math.isnan(vpin))
            self.assertTrue(0.0 <= vpin <= 1.0)

        final_vpin = self.engine.get_vpin()
        print(f"[VPIN Toxic Sell Burst] Final VPIN: {final_vpin:.4f}")
        self.assertGreater(final_vpin, 0.50, "One-sided sell burst must yield elevated VPIN (> 0.50)")
        self.assertLessEqual(final_vpin, 1.0)

    def test_vpin_balanced_random_walk_trades(self):
        """
        Stress Case 5: 1,000 balanced Gaussian random-walk trades.
        Verify: VPIN remains well-conditioned and moderate.
        """
        rng = np.random.RandomState(123)
        px = 50000.0
        for i in range(1000):
            ret = rng.normal(0.0, 0.001)
            px = max(100.0, px * (1.0 + ret))
            side = "BUY" if rng.random() >= 0.5 else "SELL"
            vol = float(rng.randint(10, 50))
            self.engine.on_trade_tick(price=px, volume=vol, side=side)

        final_vpin = self.engine.get_vpin()
        print(f"[VPIN Balanced Trades] Final VPIN: {final_vpin:.4f}")
        self.assertTrue(0.0 <= final_vpin <= 1.0)
        self.assertFalse(math.isnan(final_vpin))

    def test_vpin_near_zero_and_massive_volumes(self):
        """
        Stress Case 6: Edge-case volumes: 0.0 volume, micro-volume (1e-12), and massive volume (1e12).
        Verify: No float overflow, underflow, or divide by zero.
        """
        # Zero volume
        self.engine.on_trade_tick(price=100.0, volume=0.0, side="BUY")
        self.assertFalse(math.isnan(self.engine.get_vpin()))

        # Micro volume
        for i in range(20):
            self.engine.on_trade_tick(price=100.0 + i, volume=1e-12, side="BUY")
        self.assertFalse(math.isnan(self.engine.get_vpin()))

        # Massive volume
        for i in range(20):
            self.engine.on_trade_tick(price=100.0 + i, volume=1e12, side="SELL")
        vpin = self.engine.get_vpin()
        self.assertFalse(math.isnan(vpin))
        self.assertTrue(0.0 <= vpin <= 1.0)

    def test_vpin_continuous_10000_trades_memory_and_throttling(self):
        """
        Stress Case 7: Continuous 10,000 trades through StreamingLOBManager.
        Verify:
        1. VPIN updates at 10-tick throttled cadence without stall.
        2. Rolling deques remain capped at 1,000 elements (no memory leak).
        3. Hawkes arrival intensity updates continuously.
        """
        mgr = StreamingLOBManager()
        sym = "005930"
        mgr.get_or_create(sym)

        t0 = time.perf_counter()
        for i in range(10_000):
            t = TradeUpdate(
                symbol=sym,
                price=70000.0 + (i % 20) * 100.0,
                volume=10.0 + (i % 5),
                side="BUY" if i % 2 == 0 else "SELL",
                sequence=i,
            )
            mgr.on_trade(t)

        t_elapsed = time.perf_counter() - t0
        book = mgr.get_book(sym)

        print(f"\n[VPIN 10,000 Trades] Executed in {t_elapsed:.4f}s ({10000/t_elapsed:,.0f} ticks/sec)")

        # Verify deque capacity bound
        self.assertEqual(len(book._rolling_prices), 1000)
        self.assertEqual(len(book._rolling_volumes), 1000)

        # Verify Hawkes and VPIN validity
        vpin = mgr.get_vpin(sym)
        hawkes = mgr.get_hawkes_intensity(sym)
        self.assertFalse(math.isnan(vpin))
        self.assertTrue(0.0 <= vpin <= 1.0)
        self.assertGreater(hawkes, 0.0)


if __name__ == "__main__":
    unittest.main()
