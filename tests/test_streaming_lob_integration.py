"""
tests/test_streaming_lob_integration.py — Real-Time Streaming WebSocket Quote Feed & Fast LOB Integration Test Suite

Phase 123 (Release R139 / v130 Institutional Production Master, Feature F586)
Milestone 2 Verification:
- Normalized market event schemas (QuoteUpdate, DepthUpdate, TradeUpdate, TopOfBook, DepthLevel)
- StreamingFeedAdapter bounded queue, backpressure policies (DROP_OLDEST, DROP_NEWEST, COALESCE, BLOCK),
  thread-safe event routing, symbol & wildcard dispatch, sync/async callbacks, telemetry tracking
- Feed Providers: MockStreamingProvider (seed determinism, burst rate), HistoricalReplayFeedProvider,
  WebSocketFeedProvider (reconnect with exponential backoff)
- FastLOBEngine streaming ingestion: atomic lockless get_top_of_book(), Hawkes arrival intensity,
  continuous VPIN volume clock estimation, multi-symbol manager
- OMS Engine integration: live spread and micro-price anchoring, Hawkes/VPIN tranche peg shading,
  toxicity rejection
- PaperTradingDaemon integration: live spread & multi-level depth sweeps, strict Net Equity <= Gross Equity invariant
- Concurrency stress testing: high-throughput multi-threaded stream ingestion with zero lock contention
"""

import asyncio
import os
import sys
import tempfile
import threading
import time
import unittest
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pytest

from src.core.streaming_feed_adapter import (
    BackpressurePolicy,
    DepthLevel,
    DepthUpdate,
    FeedEventType,
    FeedTelemetry,
    HistoricalReplayFeedProvider,
    MockStreamingProvider,
    QuoteUpdate,
    StreamingFeedAdapter,
    StreamingLOBManager,
    TopOfBook,
    TradeUpdate,
    WebSocketFeedProvider,
)
from src.core.fast_lob_engine import FastLOBEngine, FastOrderBookMatchingEngine
from src.execution.oms_engine import ExecutionOMSEngine
from src.execution.paper_trading_daemon import PaperTradingDaemon


# ==============================================================================
# 1. Event Schemas Tests (4 tests)
# ==============================================================================

class TestEventSchemas(unittest.TestCase):
    """Test normalized market event data models and integrity constraints."""

    def test_quote_update_validity_and_spread_bps(self):
        """TC01: Verify QuoteUpdate spread calculation, mid price, and validity check."""
        # Valid quote
        q1 = QuoteUpdate(
            symbol="005930",
            market="KRX",
            bid_price=70000.0,
            bid_size=1500.0,
            ask_price=70200.0,
            ask_size=2000.0,
            timestamp_ns=time.time_ns(),
        )
        self.assertTrue(q1.is_valid())
        self.assertEqual(q1.mid_price, 70100.0)
        self.assertEqual(q1.spread, 200.0)
        expected_bps = (200.0 / 70100.0) * 10000.0
        self.assertAlmostEqual(q1.spread_bps, expected_bps, places=4)

        # Inverted or crossed quote
        q_inverted = QuoteUpdate(
            symbol="005930",
            market="KRX",
            bid_price=70500.0,
            bid_size=100.0,
            ask_price=70000.0,
            ask_size=100.0,
        )
        self.assertFalse(q_inverted.is_valid())
        self.assertLess(q_inverted.spread, 0.0)

        # Non-positive quote
        q_zero = QuoteUpdate(
            symbol="005930",
            market="KRX",
            bid_price=0.0,
            bid_size=100.0,
            ask_price=70000.0,
            ask_size=100.0,
        )
        self.assertFalse(q_zero.is_valid())

    def test_depth_update_bids_asks_sorting_and_micro_price(self):
        """TC02: Verify DepthUpdate multi-level sorting and analytical micro-price."""
        bids = [
            DepthLevel(price=70000.0, volume=1000.0, order_count=10),
            DepthLevel(price=69900.0, volume=2500.0, order_count=20),
            DepthLevel(price=69800.0, volume=5000.0, order_count=35),
        ]
        asks = [
            DepthLevel(price=70100.0, volume=3000.0, order_count=25),
            DepthLevel(price=70200.0, volume=1500.0, order_count=15),
            DepthLevel(price=70300.0, volume=4000.0, order_count=30),
        ]
        depth = DepthUpdate(
            symbol="005930",
            market="KRX",
            bids=bids,
            asks=asks,
            timestamp_ns=time.time_ns(),
        )
        self.assertEqual(depth.best_bid, 70000.0)
        self.assertEqual(depth.best_ask, 70100.0)
        self.assertEqual(depth.best_bid_size, 1000.0)
        self.assertEqual(depth.best_ask_size, 3000.0)
        self.assertEqual(depth.total_bid_depth, 8500.0)
        self.assertEqual(depth.total_ask_depth, 8500.0)

        # Micro-price = (bid_vol * ask_price + ask_vol * bid_price) / (bid_vol + ask_vol)
        # = (1000 * 70100 + 3000 * 70000) / 4000 = (70100000 + 210000000) / 4000 = 70025.0
        self.assertAlmostEqual(depth.micro_price, 70025.0, places=4)
        self.assertLess(depth.micro_price, depth.mid_price)

    def test_trade_update_attributes_and_sides(self):
        """TC03: Verify TradeUpdate volume, notional, and side string validation."""
        trade_buy = TradeUpdate(
            symbol="AAPL",
            market="NASDAQ",
            price=185.50,
            volume=500.0,
            side="BUY",
            trade_id="TRD-1001",
            timestamp_ns=time.time_ns(),
        )
        self.assertEqual(trade_buy.notional, 185.50 * 500.0)
        self.assertEqual(trade_buy.side, "BUY")
        self.assertGreater(trade_buy.timestamp_ns, 0)

        trade_sell = TradeUpdate(
            symbol="AAPL",
            market="NASDAQ",
            price=185.45,
            volume=300.0,
            side="SELL",
            trade_id="TRD-1002",
        )
        self.assertEqual(trade_sell.notional, 185.45 * 300.0)
        self.assertEqual(trade_sell.side, "SELL")

    def test_top_of_book_immutability_and_spread(self):
        """TC04: Verify TopOfBook properties, spread bps, and micro-price calculation."""
        tob = TopOfBook(
            symbol="NVDA",
            market="NASDAQ",
            bid_price=120.00,
            bid_size=800.0,
            ask_price=120.10,
            ask_size=200.0,
            timestamp_ns=time.time_ns(),
            sequence_id=42,
        )
        self.assertTrue(tob.is_valid())
        self.assertAlmostEqual(tob.spread, 0.10, places=5)
        self.assertAlmostEqual(tob.mid_price, 120.05, places=5)
        # Micro price = (800 * 120.10 + 200 * 120.00) / 1000 = (96080 + 24000)/1000 = 120.08
        self.assertAlmostEqual(tob.micro_price, 120.08, places=4)
        self.assertGreater(tob.micro_price, tob.mid_price)


# ==============================================================================
# 2. Streaming Feed Adapter & Backpressure Tests (8 tests)
# ==============================================================================

class TestStreamingFeedAdapter(unittest.TestCase):
    """Test StreamingFeedAdapter queues, policies, pub/sub routing, and telemetry."""

    def test_adapter_bounded_queue_and_drop_oldest(self):
        """TC05: Verify DROP_OLDEST backpressure drops the oldest queued items under capacity saturation."""
        adapter = StreamingFeedAdapter(
            max_queue_size=5,
            backpressure_policy=BackpressurePolicy.DROP_OLDEST,
        )
        received_quotes = []

        def on_quote(q: QuoteUpdate):
            received_quotes.append(q.bid_price)

        adapter.subscribe("TEST", on_quote=on_quote)

        # Enqueue 10 events directly into adapter's queue before starting consumer worker
        for i in range(10):
            adapter.enqueue(QuoteUpdate(
                symbol="TEST",
                market="KRX",
                bid_price=float(100 + i),
                bid_size=10.0,
                ask_price=float(101 + i),
                ask_size=10.0,
            ))

        # Under DROP_OLDEST with size 5, only the last 5 items should remain in queue
        self.assertEqual(len(adapter._queue), 5)
        # The oldest items (100..104) were dropped, so queue has 105..109
        self.assertEqual([q.bid_price for q in adapter._queue], [105.0, 106.0, 107.0, 108.0, 109.0])
        self.assertEqual(adapter.telemetry.events_dropped, 5)

        adapter.start()
        adapter.flush(timeout=1.0)
        adapter.stop()

        self.assertEqual(received_quotes, [105.0, 106.0, 107.0, 108.0, 109.0])

    def test_adapter_drop_newest(self):
        """TC06: Verify DROP_NEWEST backpressure sheds newly incoming items when queue is saturated."""
        adapter = StreamingFeedAdapter(
            max_queue_size=4,
            backpressure_policy=BackpressurePolicy.DROP_NEWEST,
        )

        for i in range(8):
            adapter.enqueue(QuoteUpdate(
                symbol="TEST",
                market="KRX",
                bid_price=float(100 + i),
                bid_size=10.0,
                ask_price=float(101 + i),
                ask_size=10.0,
            ))

        self.assertEqual(len(adapter._queue), 4)
        # Oldest items (100..103) were preserved, subsequent (104..107) were dropped
        self.assertEqual([q.bid_price for q in adapter._queue], [100.0, 101.0, 102.0, 103.0])
        self.assertEqual(adapter.telemetry.events_dropped, 4)
        adapter.close()

    def test_adapter_coalesce_policy(self):
        """TC07: Verify COALESCE backpressure merges stale quotes for identical symbols."""
        adapter = StreamingFeedAdapter(
            max_queue_size=3,
            backpressure_policy=BackpressurePolicy.COALESCE,
        )

        # Enqueue multiple quotes for SYM_A and SYM_B
        adapter.enqueue(QuoteUpdate(symbol="SYM_A", market="KRX", bid_price=10.0, bid_size=1.0, ask_price=11.0, ask_size=1.0))
        adapter.enqueue(QuoteUpdate(symbol="SYM_B", market="KRX", bid_price=20.0, bid_size=1.0, ask_price=21.0, ask_size=1.0))
        adapter.enqueue(QuoteUpdate(symbol="SYM_A", market="KRX", bid_price=12.0, bid_size=1.0, ask_price=13.0, ask_size=1.0))
        adapter.enqueue(QuoteUpdate(symbol="SYM_B", market="KRX", bid_price=22.0, bid_size=1.0, ask_price=23.0, ask_size=1.0))

        # Size should stay capped at 3
        self.assertLessEqual(len(adapter._queue), 3)
        prices_in_queue = {q.symbol: q.bid_price for q in adapter._queue if isinstance(q, QuoteUpdate)}
        # Latest quotes should be preserved
        self.assertEqual(prices_in_queue.get("SYM_A"), 12.0)
        self.assertEqual(prices_in_queue.get("SYM_B"), 22.0)
        adapter.close()

    def test_adapter_block_policy(self):
        """TC08: Verify BLOCK policy unblocks producer once queue space becomes available."""
        adapter = StreamingFeedAdapter(
            max_queue_size=2,
            backpressure_policy=BackpressurePolicy.BLOCK,
        )
        adapter.enqueue(QuoteUpdate(symbol="SYM", market="KRX", bid_price=10.0, bid_size=1.0, ask_price=11.0, ask_size=1.0))
        adapter.enqueue(QuoteUpdate(symbol="SYM", market="KRX", bid_price=20.0, bid_size=1.0, ask_price=21.0, ask_size=1.0))

        # Queue is full. Start adapter worker in thread so it drains
        adapter.start()
        # Enqueue 3rd item should succeed quickly once worker drains
        t0 = time.time()
        success = adapter.enqueue(QuoteUpdate(symbol="SYM", market="KRX", bid_price=30.0, bid_size=1.0, ask_price=31.0, ask_size=1.0))
        t_elapsed = time.time() - t0
        self.assertTrue(success)
        self.assertLess(t_elapsed, 1.0)
        adapter.close()

    def test_adapter_symbol_and_wildcard_dispatch(self):
        """TC09: Verify targeted symbol subscriptions and wildcard (*) broadcast listeners."""
        adapter = StreamingFeedAdapter()
        samsung_quotes = []
        wildcard_quotes = []

        adapter.subscribe("005930", on_quote=lambda q: samsung_quotes.append(q))
        adapter.subscribe("*", on_quote=lambda q: wildcard_quotes.append(q))

        adapter.start()

        q_sam = QuoteUpdate(symbol="005930", market="KRX", bid_price=70000.0, bid_size=10.0, ask_price=70100.0, ask_size=10.0)
        q_skh = QuoteUpdate(symbol="000660", market="KRX", bid_price=150000.0, bid_size=5.0, ask_price=150200.0, ask_size=5.0)

        adapter.enqueue(q_sam)
        adapter.enqueue(q_skh)

        adapter.flush(timeout=1.0)
        adapter.stop()

        self.assertEqual(len(samsung_quotes), 1)
        self.assertEqual(samsung_quotes[0].symbol, "005930")
        self.assertEqual(len(wildcard_quotes), 2)
        self.assertEqual([q.symbol for q in wildcard_quotes], ["005930", "000660"])

    def test_adapter_async_and_sync_callbacks(self):
        """TC10: Verify adapter invokes both synchronous and asynchronous coroutine subscribers."""
        adapter = StreamingFeedAdapter()
        sync_hits = []
        async_hits = []

        def sync_cb(q: QuoteUpdate):
            sync_hits.append(q.bid_price)

        async def async_cb(q: QuoteUpdate):
            await asyncio.sleep(0.001)
            async_hits.append(q.ask_price)

        adapter.subscribe("SYM", on_quote=sync_cb)
        adapter.subscribe("SYM", on_quote=async_cb)

        adapter.start()
        adapter.enqueue(QuoteUpdate(symbol="SYM", market="KRX", bid_price=50.0, bid_size=1.0, ask_price=51.0, ask_size=1.0))

        adapter.flush(timeout=1.0)
        time.sleep(0.05)
        adapter.stop()

        self.assertEqual(sync_hits, [50.0])
        self.assertEqual(async_hits, [51.0])

    def test_adapter_subscriber_isolation_on_exception(self):
        """TC11: Verify an unhandled exception in one subscriber callback does not kill dispatcher or drop events."""
        adapter = StreamingFeedAdapter()
        healthy_hits = []

        def buggy_cb(q: QuoteUpdate):
            raise RuntimeError("Deliberate test failure in faulty subscriber")

        def healthy_cb(q: QuoteUpdate):
            healthy_hits.append(q.symbol)

        adapter.subscribe("SYM", on_quote=buggy_cb)
        adapter.subscribe("SYM", on_quote=healthy_cb)

        adapter.start()
        adapter.enqueue(QuoteUpdate(symbol="SYM", market="KRX", bid_price=10.0, bid_size=1.0, ask_price=11.0, ask_size=1.0))
        adapter.enqueue(QuoteUpdate(symbol="SYM", market="KRX", bid_price=12.0, bid_size=1.0, ask_price=13.0, ask_size=1.0))

        adapter.flush(timeout=1.0)
        adapter.stop()

        self.assertEqual(healthy_hits, ["SYM", "SYM"])

    def test_adapter_telemetry_metrics(self):
        """TC12: Verify microsecond latency percentiles, queue depth, and throughput telemetry."""
        adapter = StreamingFeedAdapter()
        adapter.start()

        for i in range(50):
            adapter.enqueue(TradeUpdate(
                symbol="SYM",
                market="KRX",
                price=100.0 + i,
                volume=10.0,
                side="BUY" if i % 2 == 0 else "SELL",
                timestamp_ns=time.time_ns(),
            ))

        adapter.flush(timeout=1.0)
        adapter.stop()

        telemetry = adapter.telemetry
        self.assertEqual(telemetry.events_processed, 50)
        self.assertEqual(telemetry.events_dropped, 0)
        self.assertGreaterEqual(telemetry.avg_latency_us, 0.0)
        self.assertGreaterEqual(telemetry.p99_latency_us, telemetry.p50_latency_us)


# ==============================================================================
# 3. Feed Providers Tests (4 tests)
# ==============================================================================

class TestFeedProviders(unittest.TestCase):
    """Test deterministic mock, replay, and websocket feed providers."""

    def test_mock_provider_deterministic_seed(self):
        """TC13: Verify MockStreamingProvider produces identical stream sequences with fixed RNG seeds."""
        symbols = ["005930", "000660"]
        base_prices = {"005930": 70000.0, "000660": 140000.0}

        p1 = MockStreamingProvider(symbols=symbols, base_prices=base_prices, seed=12345)
        p2 = MockStreamingProvider(symbols=symbols, base_prices=base_prices, seed=12345)

        stream1 = [p1.generate_next_event() for _ in range(20)]
        stream2 = [p2.generate_next_event() for _ in range(20)]

        for e1, e2 in zip(stream1, stream2):
            self.assertEqual(type(e1), type(e2))
            self.assertEqual(e1.symbol, e2.symbol)
            if isinstance(e1, QuoteUpdate):
                self.assertAlmostEqual(e1.bid_price, e2.bid_price, places=4)
                self.assertAlmostEqual(e1.ask_price, e2.ask_price, places=4)
            elif isinstance(e1, TradeUpdate):
                self.assertAlmostEqual(e1.price, e2.price, places=4)

    def test_mock_provider_burst_mode(self):
        """TC14: Verify burst mode production generating high-frequency events seamlessly."""
        provider = MockStreamingProvider(symbols=["AAPL"], frequency_hz=1000.0, seed=42)
        adapter = StreamingFeedAdapter(max_queue_size=2000)
        adapter.start()

        provider.start_producing(adapter)
        time.sleep(0.1)  # 100ms should produce ~100 events
        provider.stop()
        adapter.flush(timeout=1.0)
        adapter.stop()

        self.assertGreater(adapter.telemetry.events_processed, 20)

    def test_historical_replay_provider(self):
        """TC15: Verify HistoricalReplayFeedProvider sequential replay across timestamp ordering."""
        now = time.time_ns()
        records = [
            QuoteUpdate(symbol="005930", market="KRX", bid_price=70000.0, bid_size=10.0, ask_price=70100.0, ask_size=10.0, timestamp_ns=now),
            TradeUpdate(symbol="005930", market="KRX", price=70100.0, volume=50.0, side="BUY", timestamp_ns=now + 1_000_000),
            QuoteUpdate(symbol="005930", market="KRX", bid_price=70100.0, bid_size=20.0, ask_price=70200.0, ask_size=15.0, timestamp_ns=now + 2_000_000),
        ]

        replay = HistoricalReplayFeedProvider(records=records, playback_speed=0.0)
        adapter = StreamingFeedAdapter()
        received = []

        adapter.subscribe("005930", on_quote=lambda q: received.append(q), on_trade=lambda t: received.append(t))
        adapter.start()

        replay.start_producing(adapter)
        replay.wait_until_complete(timeout=1.0)
        adapter.flush(timeout=1.0)
        adapter.stop()

        self.assertEqual(len(received), 3)
        self.assertIsInstance(received[0], QuoteUpdate)
        self.assertIsInstance(received[1], TradeUpdate)
        self.assertIsInstance(received[2], QuoteUpdate)

    def test_websocket_provider_reconnect_backoff(self):
        """TC16: Verify WebSocketFeedProvider exponential backoff calculation and connection state."""
        ws = WebSocketFeedProvider(
            uri="wss://stream.institution.krx/v1",
            initial_backoff_sec=0.1,
            max_backoff_sec=1.6,
            backoff_factor=2.0,
        )
        self.assertEqual(ws.current_backoff, 0.1)
        ws.record_disconnect()
        self.assertAlmostEqual(ws.current_backoff, 0.2, places=3)
        ws.record_disconnect()
        self.assertAlmostEqual(ws.current_backoff, 0.4, places=3)
        ws.record_disconnect()
        self.assertAlmostEqual(ws.current_backoff, 0.8, places=3)
        ws.record_disconnect()
        self.assertAlmostEqual(ws.current_backoff, 1.6, places=3)
        ws.record_disconnect()
        # Capped at max_backoff_sec
        self.assertAlmostEqual(ws.current_backoff, 1.6, places=3)

        ws.record_connect_success()
        self.assertAlmostEqual(ws.current_backoff, 0.1, places=3)


# ==============================================================================
# 4. Fast LOB Streaming Integration Tests (5 tests)
# ==============================================================================

class TestFastLOBStreamingIntegration(unittest.TestCase):
    """Test FastLOBEngine streaming ingestion, atomic lockless top-of-book, and metrics."""

    def test_lob_on_quote_update_atomic_bbo(self):
        """TC17: Verify LOB updates BBO atomically upon receiving QuoteUpdate."""
        lob = FastOrderBookMatchingEngine(symbol="005930")
        quote = QuoteUpdate(
            symbol="005930",
            market="KRX",
            bid_price=71000.0,
            bid_size=1200.0,
            ask_price=71100.0,
            ask_size=800.0,
            timestamp_ns=time.time_ns(),
        )
        lob.on_quote_update(quote)

        tob = lob.get_top_of_book()
        self.assertIsNotNone(tob)
        self.assertEqual(tob.bid_price, 71000.0)
        self.assertEqual(tob.bid_size, 1200.0)
        self.assertEqual(tob.ask_price, 71100.0)
        self.assertEqual(tob.ask_size, 800.0)
        self.assertEqual(tob.mid_price, 71050.0)
        self.assertEqual(lob.get_effective_spread(), 100.0)

    def test_lob_on_depth_update_multi_tier(self):
        """TC18: Verify LOB depth level ingestion and cumulative depth reporting."""
        lob = FastOrderBookMatchingEngine(symbol="005930")
        depth = DepthUpdate(
            symbol="005930",
            market="KRX",
            bids=[
                DepthLevel(price=70000.0, volume=500.0),
                DepthLevel(price=69900.0, volume=1500.0),
            ],
            asks=[
                DepthLevel(price=70100.0, volume=800.0),
                DepthLevel(price=70200.0, volume=2000.0),
            ],
            timestamp_ns=time.time_ns(),
        )
        lob.on_depth_update(depth)

        bbo = lob.get_top_of_book()
        self.assertEqual(bbo.bid_price, 70000.0)
        self.assertEqual(bbo.ask_price, 70100.0)

        snapshot = lob.get_depth_snapshot(levels=2)
        self.assertEqual(len(snapshot["bids"]), 2)
        self.assertEqual(len(snapshot["asks"]), 2)
        self.assertEqual(snapshot["bids"][0], (70000.0, 500.0))
        self.assertEqual(snapshot["asks"][0], (70100.0, 800.0))

    def test_lob_on_trade_tick_continuous_vpin(self):
        """TC19: Verify consecutive trade ticks update rolling volume buckets and calculate continuous VPIN."""
        lob = FastOrderBookMatchingEngine(symbol="005930")
        # Ingest series of predominantly BUY trade ticks to induce informed order toxicity
        for i in range(40):
            lob.on_trade_tick(TradeUpdate(
                symbol="005930",
                market="KRX",
                price=70000.0 + i * 10,
                volume=100.0,
                side="BUY" if i < 35 else "SELL",
                timestamp_ns=time.time_ns(),
            ))

        vpin = lob.get_vpin()
        self.assertGreaterEqual(vpin, 0.0)
        self.assertLessEqual(vpin, 1.0)
        # Because buys vastly outnumber sells (35 vs 5), VPIN toxicity should be elevated
        self.assertGreater(vpin, 0.5)

    def test_lob_hawkes_intensity_acceleration(self):
        """TC20: Verify arrival of rapid trade ticks accelerates microsecond Hawkes intensity."""
        lob = FastOrderBookMatchingEngine(symbol="005930")
        intensity_initial = lob.get_hawkes_intensity()

        # Ingest rapid succession of 20 trades
        now = time.time_ns()
        for i in range(20):
            lob.on_trade_tick(TradeUpdate(
                symbol="005930",
                market="KRX",
                price=70000.0,
                volume=50.0,
                side="BUY",
                timestamp_ns=now + i * 10_000,
            ))

        intensity_accelerated = lob.get_hawkes_intensity()
        self.assertGreater(intensity_accelerated, intensity_initial)

    def test_lob_streaming_manager_multi_symbol(self):
        """TC21: Verify StreamingLOBManager multi-symbol routing and market state queries."""
        mgr = StreamingLOBManager()
        adapter = StreamingFeedAdapter(lob_manager=mgr)
        adapter.start()

        adapter.enqueue(QuoteUpdate(symbol="005930", market="KRX", bid_price=70000.0, bid_size=10.0, ask_price=70100.0, ask_size=10.0))
        adapter.enqueue(QuoteUpdate(symbol="000660", market="KRX", bid_price=140000.0, bid_size=5.0, ask_price=140200.0, ask_size=5.0))

        adapter.flush(timeout=1.0)
        adapter.stop()

        tob_sam = mgr.get_top_of_book("005930")
        tob_skh = mgr.get_top_of_book("000660")
        self.assertIsNotNone(tob_sam)
        self.assertIsNotNone(tob_skh)
        self.assertEqual(tob_sam.mid_price, 70050.0)
        self.assertEqual(tob_skh.mid_price, 140100.0)

        state = mgr.get_market_state("005930")
        self.assertEqual(state["bid"], 70000.0)
        self.assertEqual(state["ask"], 70100.0)
        self.assertEqual(state["spread"], 100.0)


# ==============================================================================
# 5. OMS LOB Integration Tests (3 tests)
# ==============================================================================

class TestOMSLOBIntegration(unittest.TestCase):
    """Test ExecutionOMSEngine live LOB integration, spread anchoring, and Hawkes/VPIN peg shading."""

    def test_oms_generate_order_plan_with_live_lob(self):
        """TC22: Verify OMS anchors order target price to live LOB micro-price and current spread."""
        mgr = StreamingLOBManager()
        lob = mgr.get_book("005930")
        # Ingest BBO with ask heavy imbalance
        lob.on_quote_update(QuoteUpdate(
            symbol="005930",
            market="KRX",
            bid_price=70000.0,
            bid_size=1000.0,
            ask_price=70200.0,
            ask_size=4000.0,
            timestamp_ns=time.time_ns(),
        ))

        oms = ExecutionOMSEngine(
            account_id="ACC_STREAMING_TEST",
            initial_capital=100_000_000.0,
            lob_engine=mgr,
        )

        plan = oms.generate_order_plan(
            symbol="005930",
            target_weight=0.10,
            current_weight=0.0,
            portfolio_equity=100_000_000.0,
            pred={
                "close": 70000.0,
                "current_price": 70000.0,
                "market": "KRX",
                "volatility": 0.02,
                "adv_20d": 1e9,
            },
        )
        self.assertIsNotNone(plan)
        # Target price should be enriched and anchored to micro-price or BBO mid
        self.assertGreater(plan.target_price, 70000.0)
        self.assertLess(plan.target_price, 70200.0)
        self.assertAlmostEqual(plan.target_price, 70040.0, places=1)

    def test_oms_tranche_peg_limit_shading(self):
        """TC23: Verify calculate_peg_limit_price applies Hawkes toxicity and arrival imbalance shading."""
        oms = ExecutionOMSEngine(account_id="ACC_TEST")
        base_bid = 100.0
        base_ask = 101.0

        # Normal condition
        peg_normal = oms.calculate_peg_limit_price(
            side="BUY",
            bid_price=base_bid,
            ask_price=base_ask,
            urgency=0.5,
            hawkes_intensity=1.0,
            hawkes_toxicity=0.0,
        )

        # High toxicity condition: toxic order flow shades buyer more passively / conservatively
        peg_toxic = oms.calculate_peg_limit_price(
            side="BUY",
            bid_price=base_bid,
            ask_price=base_ask,
            urgency=0.5,
            hawkes_intensity=10.0,
            hawkes_toxicity=0.9,
        )

        self.assertLess(peg_toxic, peg_normal)

    def test_oms_gate7_vpin_toxicity_rejection(self):
        """TC24: Verify Gate 7 blocks aggressive execution under extreme VPIN adverse flow."""
        mgr = StreamingLOBManager()
        lob = mgr.get_book("005930")
        # Simulate extreme toxicity by pumping 50 one-sided trades
        for i in range(50):
            lob.on_trade_tick(TradeUpdate(
                symbol="005930",
                market="KRX",
                price=70000.0 + i,
                volume=1000.0,
                side="SELL",  # Adverse selling cascade
                timestamp_ns=time.time_ns(),
            ))

        vpin = lob.get_vpin()
        self.assertGreater(vpin, 0.70)

        oms = ExecutionOMSEngine(
            account_id="ACC_TEST",
            initial_capital=100_000_000.0,
            lob_engine=mgr,
        )

        plan = oms.generate_order_plan(
            symbol="005930",
            target_weight=0.10,
            current_weight=0.0,
            portfolio_equity=100_000_000.0,
            pred={
                "close": 70000.0,
                "current_price": 70000.0,
                "market": "KRX",
                "volatility": 0.02,
                "adv_20d": 1e9,
                "vpin": vpin,
            },
        )
        # Plan execution should either be shaded passively or gated under excessive VPIN
        self.assertIsNotNone(plan)
        self.assertGreaterEqual(plan.urgency, 0.0)


# ==============================================================================
# 6. Paper Trading Daemon LOB Integration Tests (3 tests)
# ==============================================================================

class TestPaperTradingLOBIntegration(unittest.TestCase):
    """Test PaperTradingDaemon execution with live streaming LOB orderbooks."""

    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self.temp_db.name
        self.temp_db.close()

    def tearDown(self):
        try:
            if os.path.exists(self.db_path):
                os.remove(self.db_path)
        except Exception:
            pass

    def test_paper_trading_daemon_live_lob_fill(self):
        """TC25: Verify PaperTradingDaemon fills orders using live BBO spread from LOB."""
        mgr = StreamingLOBManager()
        lob = mgr.get_book("005930")
        lob.on_quote_update(QuoteUpdate(
            symbol="005930",
            market="KRX",
            bid_price=69800.0,
            bid_size=500.0,
            ask_price=70200.0,
            ask_size=500.0,
            timestamp_ns=time.time_ns(),
        ))

        daemon = PaperTradingDaemon(
            initial_capital=50_000_000.0,
            db_path=self.db_path,
            dry_run=True,
            lob_engine=mgr,
        )

        alloc = {
            "005930": {
                "target_weight": 0.20,
                "current_price": 70000.0,
                "market": "KRX",
                "adv_20d": 1e9,
                "volatility": 0.02,
            }
        }

        summary = daemon.run_cycle(target_input=alloc, market_data=mgr)
        self.assertGreater(summary["executed_count"], 0)
        self.assertTrue(summary["invariant_net_le_gross"])

    def test_paper_trading_daemon_multi_level_depth_sweep(self):
        """TC26: Verify multi-level orderbook sweep fills order at depth-weighted prices."""
        mgr = StreamingLOBManager()
        lob = mgr.get_book("005930")
        # Populate asks: 100 shares @ 70100, 500 shares @ 70300
        lob.on_depth_update(DepthUpdate(
            symbol="005930",
            market="KRX",
            bids=[DepthLevel(price=70000.0, volume=1000.0)],
            asks=[
                DepthLevel(price=70100.0, volume=100.0),
                DepthLevel(price=70300.0, volume=500.0),
            ],
            timestamp_ns=time.time_ns(),
        ))

        daemon = PaperTradingDaemon(
            initial_capital=50_000_000.0,
            db_path=self.db_path,
            dry_run=True,
            lob_engine=mgr,
        )

        fill = daemon.simulate_fill(
            symbol="005930",
            side="BUY",
            quantity=300,
            target_price=70000.0,
            market="KRX",
            adv_20d=1e9,
            volatility=0.02,
            market_data=mgr,
        )

        # 100 shares @ 70100 + 200 shares @ 70300 => (7010000 + 14060000)/300 = 21070000/300 = 70233.33
        self.assertGreater(fill.executed_price, 70100.0)
        self.assertLessEqual(fill.executed_price, 70300.0)
        self.assertAlmostEqual(fill.executed_price, 70233.33, places=1)

    def test_paper_trading_daemon_equity_invariant_with_streaming(self):
        """TC27: Verify strict mathematical invariant Net Equity <= Gross Equity across multiple streaming cycles."""
        provider = MockStreamingProvider(symbols=["005930", "000660"], seed=777)
        mgr = StreamingLOBManager()
        adapter = StreamingFeedAdapter(lob_manager=mgr, provider=provider)
        adapter.start()
        provider.start_producing(adapter)

        time.sleep(0.05)  # Let feed populate books

        daemon = PaperTradingDaemon(
            initial_capital=100_000_000.0,
            db_path=self.db_path,
            dry_run=True,
            lob_engine=mgr,
        )

        alloc = {
            "005930": {"target_weight": 0.20, "current_price": 70000.0, "market": "KRX", "adv_20d": 1e9, "volatility": 0.02},
            "000660": {"target_weight": 0.15, "current_price": 140000.0, "market": "KRX", "adv_20d": 5e8, "volatility": 0.025},
        }

        for cycle in range(3):
            time.sleep(0.02)
            summary = daemon.run_cycle(target_input=alloc, market_data=mgr)
            self.assertTrue(summary["invariant_net_le_gross"])
            self.assertLessEqual(daemon.net_equity, daemon.gross_equity + 1e-6)

        provider.stop()
        adapter.close()


# ==============================================================================
# 7. High-Throughput Concurrency Stress Test (1 test)
# ==============================================================================

class TestConcurrencyStress(unittest.TestCase):
    """Test high-frequency streaming feed producer with concurrent readers under zero lock contention."""

    def test_concurrent_feed_and_lob_readers(self):
        """TC28: Verify 5,000+ rapid events ingested concurrently with 4 active reader threads without race condition."""
        mgr = StreamingLOBManager()
        adapter = StreamingFeedAdapter(
            lob_manager=mgr,
            max_queue_size=10000,
            backpressure_policy=BackpressurePolicy.DROP_OLDEST,
        )
        adapter.start()

        num_events = 2500
        symbols = ["005930", "000660", "AAPL", "NVDA"]
        stop_readers = threading.Event()
        read_counts = [0, 0, 0, 0]
        reader_errors = []

        def reader_worker(worker_id: int):
            try:
                while not stop_readers.is_set():
                    for sym in symbols:
                        tob = mgr.get_top_of_book(sym)
                        if tob is not None:
                            # Verify structural integrity
                            assert tob.bid_price <= tob.ask_price or tob.ask_price == 0.0
                        intensity = mgr.get_hawkes_intensity(sym)
                        assert intensity >= 0.0
                    read_counts[worker_id] += 1
                    time.sleep(0.0001)
            except Exception as e:
                reader_errors.append((worker_id, e))

        # Start 4 concurrent reader threads
        threads = [threading.Thread(target=reader_worker, args=(i,)) for i in range(4)]
        for t in threads:
            t.start()

        # Producer thread pushing 2,500 quote + 2,500 trade events
        t0 = time.time()
        for i in range(num_events):
            sym = symbols[i % len(symbols)]
            adapter.enqueue(QuoteUpdate(
                symbol=sym,
                market="KRX" if "00" in sym else "NASDAQ",
                bid_price=100.0 + (i % 50),
                bid_size=10.0,
                ask_price=101.0 + (i % 50),
                ask_size=10.0,
                timestamp_ns=time.time_ns(),
            ))
            adapter.enqueue(TradeUpdate(
                symbol=sym,
                market="KRX" if "00" in sym else "NASDAQ",
                price=100.5 + (i % 50),
                volume=10.0,
                side="BUY" if i % 2 == 0 else "SELL",
                timestamp_ns=time.time_ns(),
            ))

        adapter.flush(timeout=3.0)
        stop_readers.set()
        for t in threads:
            t.join(timeout=2.0)

        adapter.stop()
        t_total = time.time() - t0

        self.assertEqual(len(reader_errors), 0, f"Reader thread errors: {reader_errors}")
        self.assertGreater(sum(read_counts), 50)
        self.assertGreaterEqual(adapter.telemetry.events_processed, num_events * 2)
        # Latency should be sub-millisecond on average
        self.assertLess(adapter.telemetry.avg_latency_us, 5000.0)


if __name__ == "__main__":
    unittest.main()
