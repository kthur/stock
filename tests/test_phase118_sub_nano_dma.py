r"""
tests/test_phase118_sub_nano_dma.py
===================================
Comprehensive Unit, Integration, and Performance Test Suite for Feature F563:
Sub-Nanosecond Direct Memory Access (DMA) Smart Router & Broker Gateway.
Phase 118 (Release R134 / v125 Production Master).
"""

from __future__ import annotations

import hashlib
import os
import struct
import time
from pathlib import Path
import pytest

from src.broker.sub_nano_dma_broker_gateway import (
    BrokerState,
    DMAOrder,
    DMAGatewayConfig,
    DispatchReceipt,
    MemoryMappedRingBuffer,
    OrderSide,
    OrderType,
    SubNanoDMABrokerGateway,
    MARKET_DMA_PROFILES,
    ORDER_MSG_FORMAT,
    ORDER_MSG_SIZE,
    SLOT_SIZE,
    VERSION,
    RELEASE,
    FEATURE,
)


class TestSubNanoDMAGateway:
    """Test suite covering F563 Sub-Nanosecond DMA Broker Gateway."""

    def test_version_and_metadata(self):
        """Verify module constants and release metadata."""
        assert VERSION == 118
        assert RELEASE == "R134"
        assert FEATURE == "F563"
        assert ORDER_MSG_SIZE == 34
        assert SLOT_SIZE == 64

    def test_dma_order_packing_unpacking_roundtrip(self):
        """Verify binary wire struct packing and unpacking fidelity."""
        order = DMAOrder(
            order_id=987654321,
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=150,
            price=245.50,
        )
        packed = order.pack()
        assert len(packed) == SLOT_SIZE

        # Unpack without symbol table
        unpacked = DMAOrder.unpack(packed)
        assert unpacked.order_id == 987654321
        assert unpacked.side == OrderSide.BUY
        assert unpacked.order_type == OrderType.LIMIT
        assert unpacked.quantity == 150
        assert pytest.approx(unpacked.price, rel=1e-5) == 245.50

        # Unpack with symbol table
        sym_hash = hash("AAPL") & 0xFFFFFFFF
        sym_table = {sym_hash: "AAPL"}
        unpacked_with_sym = DMAOrder.unpack(packed, symbol_lookup=sym_table)
        assert unpacked_with_sym.symbol == "AAPL"

    def test_order_side_and_type_variants(self):
        """Verify packing across all enum variants."""
        for side in (OrderSide.BUY, OrderSide.SELL):
            for o_type in (OrderType.LIMIT, OrderType.MARKET, OrderType.IOC, OrderType.FOK):
                order = DMAOrder(
                    order_id=101,
                    symbol="005930",
                    side=side,
                    order_type=o_type,
                    quantity=500,
                    price=72300.0,
                )
                packed = order.pack()
                unpacked = DMAOrder.unpack(packed)
                assert unpacked.side == side
                assert unpacked.order_type == o_type
                assert unpacked.quantity == 500
                assert pytest.approx(unpacked.price, rel=1e-4) == 72300.0

    def test_memory_mapped_ring_buffer_fifo(self):
        """Verify SPSC ring buffer FIFO ordering and slot isolation."""
        ring = MemoryMappedRingBuffer(capacity=16)
        assert ring.count == 0
        assert ring.capacity == 16

        items = [f"PAYLOAD_{i}".encode("utf-8").ljust(SLOT_SIZE, b"\x00") for i in range(10)]
        for item in items:
            assert ring.push(item) is True
        assert ring.count == 10

        for item in items:
            popped = ring.pop()
            assert popped == item
        assert ring.count == 0
        assert ring.pop() is None

    def test_ring_buffer_capacity_overflow(self):
        """Verify push rejection upon capacity exhaustion."""
        ring = MemoryMappedRingBuffer(capacity=4)
        payload = b"TEST" * 16

        for _ in range(4):
            assert ring.push(payload) is True
        assert ring.count == 4

        # 5th push should fail
        assert ring.push(payload) is False
        assert ring.count == 4

        # Pop one, now push should succeed
        assert ring.pop() is not None
        assert ring.push(payload) is True

    def test_ring_buffer_wrap_around(self):
        """Verify cyclic pointer wrap-around over multiple buffer cycles."""
        ring = MemoryMappedRingBuffer(capacity=8)
        payload = b"X" * SLOT_SIZE

        for cycle in range(5):
            for _ in range(6):
                assert ring.push(payload) is True
            for _ in range(6):
                assert ring.pop() == payload
            assert ring.count == 0

    def test_ring_buffer_clear(self):
        """Verify ring buffer reset."""
        ring = MemoryMappedRingBuffer(capacity=10)
        ring.push(b"A" * SLOT_SIZE)
        ring.push(b"B" * SLOT_SIZE)
        assert ring.count == 2
        ring.clear()
        assert ring.count == 0
        assert ring.pop() is None

    def test_5_market_profiles_loaded(self):
        """Verify all 5 institutional markets have valid DMA configurations."""
        markets = ["SP500", "NASDAQ", "RUSSELL2000", "KOSPI", "KOSDAQ"]
        for m in markets:
            gw = SubNanoDMABrokerGateway(market=m)
            assert gw.market == m
            assert gw.primary_venue is not None
            assert gw.secondary_venue is not None
            assert gw.primary_latency > 0
            assert gw.backup_latency > gw.primary_latency
            assert gw.max_rate > 0

    def test_order_dispatch_primary_success(self):
        """Verify regular order dispatch acknowledged by primary venue."""
        gw = SubNanoDMABrokerGateway(market="SP500")
        order = DMAOrder(
            order_id=1,
            symbol="MSFT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=100,
            price=420.0,
        )
        receipt = gw.dispatch_order(order)
        assert receipt.order_id == 1
        assert receipt.status == "ACKNOWLEDGED"
        assert receipt.broker_name == "CHIX_DMA"
        assert receipt.is_failover_routed is False
        assert receipt.dispatch_latency_ns > 0

        telemetry = gw.export_telemetry()
        assert telemetry["total_orders"] == 1
        assert telemetry["primary_fills"] == 1
        assert telemetry["failover_fills"] == 0
        assert telemetry["dropped_orders"] == 0

    def test_automatic_broker_failover(self):
        """Verify failover to secondary venue when primary times out."""
        config = DMAGatewayConfig(heartbeat_timeout_ms=50.0)
        gw = SubNanoDMABrokerGateway(config=config, market="NASDAQ")
        assert gw.primary_venue == "INET_OUCH"
        assert gw.secondary_venue == "BATS_DIRECT"

        # Initially active
        health = gw.check_health()
        assert health["is_failover_active"] is False

        # Simulate timeout on primary
        gw.last_primary_heartbeat_ns = time.time_ns() - 100_000_000  # 100ms ago (> 50ms)
        health = gw.check_health()
        assert health["primary_state"] == "DISCONNECTED"
        assert health["is_failover_active"] is True

        # Dispatch order should failover to secondary
        order = DMAOrder(
            order_id=2,
            symbol="NVDA",
            side=OrderSide.BUY,
            order_type=OrderType.IOC,
            quantity=200,
            price=135.0,
        )
        receipt = gw.dispatch_order(order, allow_failover=True)
        assert receipt.status == "ACKNOWLEDGED"
        assert receipt.broker_name == "BATS_DIRECT"
        assert receipt.is_failover_routed is True

        # Telemetry check
        telemetry = gw.export_telemetry()
        assert telemetry["failover_fills"] == 1

        # Reconnect primary via heartbeat
        gw.send_heartbeat("PRIMARY")
        health = gw.check_health()
        assert health["primary_state"] == "ACTIVE"
        assert health["is_failover_active"] is False

        # Next order routed to primary
        receipt2 = gw.dispatch_order(order, allow_failover=True)
        assert receipt2.broker_name == "INET_OUCH"
        assert receipt2.is_failover_routed is False

    def test_circuit_breaker_engagement_and_recovery(self):
        """Verify circuit breaker trips and resets cleanly."""
        gw = SubNanoDMABrokerGateway(market="KOSPI")
        order = DMAOrder(
            order_id=3,
            symbol="005930",
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            quantity=1000,
            price=70000.0,
        )

        gw.trigger_circuit_breaker("VOLATILITY_SPIKE")
        assert gw.is_circuit_tripped is True

        receipt = gw.dispatch_order(order)
        assert receipt.status == "REJECTED"
        assert receipt.broker_name == "REJECTED_CIRCUIT_BREAKER"

        telemetry = gw.export_telemetry()
        assert telemetry["dropped_orders"] == 1

        # Reset
        gw.reset_circuit_breaker()
        assert gw.is_circuit_tripped is False

        receipt2 = gw.dispatch_order(order)
        assert receipt2.status == "ACKNOWLEDGED"
        assert receipt2.broker_name == "KRX_FIX_DMA"

    def test_rate_limiting_enforcement(self):
        """Verify strict throttling when order volume exceeds limits."""
        gw = SubNanoDMABrokerGateway(market="SP500")
        gw.max_rate = 5  # artificially constrain to 5 orders/sec

        order = DMAOrder(
            order_id=4,
            symbol="AMZN",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=50,
            price=180.0,
        )

        receipts = [gw.dispatch_order(order) for _ in range(5)]
        for r in receipts:
            assert r.status == "ACKNOWLEDGED"

        # 6th order should be rate limited
        rejected = gw.dispatch_order(order)
        assert rejected.status == "RATE_LIMITED"
        assert rejected.broker_name == "REJECTED_RATE_LIMIT"

    def test_queue_overflow_rejection(self):
        """Verify graceful rejection when shared memory ring is full."""
        config = DMAGatewayConfig(ring_capacity=3)
        gw = SubNanoDMABrokerGateway(config=config, market="RUSSELL2000")

        order = DMAOrder(
            order_id=5,
            symbol="IWM",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=10,
            price=220.0,
        )

        for _ in range(3):
            r = gw.dispatch_order(order)
            assert r.status == "ACKNOWLEDGED"

        # 4th should overflow
        overflow = gw.dispatch_order(order)
        assert overflow.status == "OVERFLOW"
        assert overflow.broker_name == "REJECTED_QUEUE_OVERFLOW"

    def test_dispatch_throughput_latency_performance(self):
        """Benchmark 500 order dispatches and ensure sub-microsecond/low-microsecond handling."""
        gw = SubNanoDMABrokerGateway(market="NASDAQ")
        order = DMAOrder(
            order_id=99,
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=100,
            price=230.0,
        )

        t0 = time.perf_counter()
        N = 500
        for i in range(N):
            receipt = gw.dispatch_order(order)
            assert receipt.status == "ACKNOWLEDGED"
            # drain ring buffer occasionally
            if i % 50 == 0:
                gw.ring_buffer.pop()

        elapsed = time.perf_counter() - t0
        avg_us = (elapsed / N) * 1_000_000
        # In pure Python, dispatch should take under 100 microseconds per order
        assert avg_us < 100.0

    def test_dual_tree_parity(self):
        """Cryptographic SHA-256 bit-for-bit parity verification."""
        p1 = Path("src/broker/sub_nano_dma_broker_gateway.py")
        p2 = Path("trading_system/src/broker/sub_nano_dma_broker_gateway.py")

        assert p1.exists() and p2.exists()
        h1 = hashlib.sha256(p1.read_bytes()).hexdigest()
        h2 = hashlib.sha256(p2.read_bytes()).hexdigest()
        assert h1 == h2
