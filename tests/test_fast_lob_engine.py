"""Unit and Performance Tests for Fast LOB Engine."""

import time
import threading
import pytest
import numpy as np

from src.core.fast_lob_engine import (
    ZeroCopyRingBuffer,
    FastOrderBookMatchingEngine,
    MicrosecondHawkesIntensity
)


def test_zero_copy_ring_buffer_wraparound():
    """Test ring buffer insertion beyond capacity and wrap-around slicing."""
    buf = ZeroCopyRingBuffer(capacity=100)

    # Insert 150 ticks
    for i in range(150):
        buf.append(price=100.0 + i, volume=10.0 + i, timestamp_ns=i * 1000, is_buy=(i % 2 == 0))

    assert buf.size == 100

    # Retrieve last 10 ticks
    recent10 = buf.get_recent(10)
    assert len(recent10["prices"]) == 10
    assert recent10["prices"][-1] == 100.0 + 149
    assert recent10["prices"][0] == 100.0 + 140
    assert recent10["sides"][-1] == -1 # 149 is odd -> SELL -> -1

    # Retrieve all 100 ticks
    recent100 = buf.get_recent(100)
    assert len(recent100["prices"]) == 100
    assert recent100["prices"][0] == 100.0 + 50


def test_zero_copy_ring_buffer_concurrency():
    """Test multi-threaded concurrent appends to ring buffer."""
    buf = ZeroCopyRingBuffer(capacity=5000)

    def worker(worker_id):
        for i in range(100):
            buf.append(price=1000.0 + worker_id, volume=1.0, timestamp_ns=i, is_buy=True)

    threads = [threading.Thread(target=worker, args=(w,)) for w in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert buf.size == 1000
    recent = buf.get_recent(1000)
    assert len(recent["prices"]) == 1000


def test_fast_order_book_matching_fifo_and_depth():
    """Test L3 limit order matching, FIFO priority, and depth snapshotting."""
    ob = FastOrderBookMatchingEngine(symbol="005930", tick_size=100.0)

    # 1. Add resting asks
    ob.add_limit_order("ask_1", "SELL", price=70200.0, volume=10.0)
    ob.add_limit_order("ask_2", "SELL", price=70200.0, volume=20.0)
    ob.add_limit_order("ask_3", "SELL", price=70300.0, volume=50.0)

    # 2. Add resting bids
    ob.add_limit_order("bid_1", "BUY", price=70000.0, volume=15.0)
    ob.add_limit_order("bid_2", "BUY", price=69900.0, volume=25.0)

    snap = ob.get_depth_snapshot(levels=5)
    assert snap["best_bid"] == 70000.0
    assert snap["best_ask"] == 70200.0
    assert snap["spread"] == 200.0
    assert len(snap["bids"]) == 2
    assert len(snap["asks"]) == 2
    assert snap["asks"][0]["volume"] == 30.0 # 10 + 20

    # 3. Market order sweeping asks
    fills = ob.match_market_order("BUY", volume=25.0)
    assert len(fills) == 2
    assert fills[0]["maker_order_id"] == "ask_1"
    assert fills[0]["volume"] == 10.0
    assert fills[1]["maker_order_id"] == "ask_2"
    assert fills[1]["volume"] == 15.0

    # 4. Check remaining depth
    snap2 = ob.get_depth_snapshot(levels=5)
    assert snap2["asks"][0]["volume"] == 5.0 # 20 - 15 remaining on ask_2


def test_fast_order_book_cancellation():
    """Test O(1) order cancellation."""
    ob = FastOrderBookMatchingEngine(symbol="AAPL")
    ob.add_limit_order("o1", "BUY", 150.0, 100.0)
    ob.add_limit_order("o2", "BUY", 150.0, 200.0)

    snap = ob.get_depth_snapshot()
    assert snap["bids"][0]["volume"] == 300.0

    # Cancel o1
    assert ob.cancel_order("o1") is True
    snap2 = ob.get_depth_snapshot()
    assert snap2["bids"][0]["volume"] == 200.0

    # Cancel non-existent order
    assert ob.cancel_order("o_none") is False


def test_microsecond_hawkes_intensity():
    """Test Hawkes intensity jumps and exponential decay."""
    hawkes = MicrosecondHawkesIntensity(mu=1.0, alpha=2.0, beta=1.0)

    t0 = 1000.0
    int0 = hawkes.update(timestamp_sec=t0)
    assert int0 == 3.0 # mu(1.0) + alpha(2.0)

    # Short interval burst
    t1 = t0 + 0.01 # 10ms later
    int1 = hawkes.update(timestamp_sec=t1)
    assert int1 > int0 # Intensity should increase due to clustering

    # Long interval decay
    t_later = t1 + 10.0 # 10s later
    decayed = hawkes.get_intensity_at(t_query_sec=t_later)
    assert decayed < 1.5 # Decayed close to baseline mu=1.0