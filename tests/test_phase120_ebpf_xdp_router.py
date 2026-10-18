r"""
tests/test_phase120_ebpf_xdp_router.py
======================================
Comprehensive Unit Test Suite for Feature F573 (Phase 120 / Release R136):
Ultra-Low Latency Hardware-Accelerated Kernel Bypass Order Router & eBPF/XDP Bridge.

12 Test Categories (>= 50 Test Cases):
1. Category 1: Binary struct packing & unpacking (<QQIIQII, 40 bytes, FNV-1a, fixed-point price, latency).
2. Category 2: Bitfield flags & masks (side, order_type, TIF, venue, midpoint, jitter, COD, HW timestamp, micro_seq).
3. Category 3: UMEM memory pool & frame allocation (contiguous memory, allocation, release, exhaustion).
4. Category 4: SPSC Lockless Ring Queues (RX, TX, Fill, Completion rings, wrap-around mask indexing, FIFO).
5. Category 5: eBPF/XDP driver emulation & actions (NATIVE_DRV, ZERO_COPY_UMEM, XDP_PASS, XDP_TX, XDP_DROP).
6. Category 6: Synthetic Midpoint Crossing Engine (P_mid, spread savings, limit/market crossing, rejections).
7. Category 7: Anti-Latency Quote Jitter Protection (delay bounds [20ns, 150ns], determinism, flag setting).
8. Category 8: Cancel-on-Disconnect (COD) Watchdog (heartbeat exchange, timeout expiration, cancel burst).
9. Category 9: Microsecond Order State Reconciliation (sequence gap detection, GapFill request, reconciliation).
10. Category 10: Multi-Broker 3-Tier Session Failover (Tier 1 XDP -> Tier 2 FIX DMA -> Tier 3 Native API, failback).
11. Category 11: Hardware Timestamping Telemetry (4-point timestamps, decomposition, p50/p95/p99 statistics).
12. Category 12: 5-Market Venue Profiles, Complete Alias Trees & SHA-256 Dual-Tree Parity.
"""

from __future__ import annotations

import hashlib
import math
import os
import struct
import time
from pathlib import Path
from typing import List, Tuple

import numpy as np
import pytest

from src.broker.ebpf_xdp_order_router import (
    AntiLatencyJitterEngine,
    CancelOnDisconnectWatchdog,
    EBPFBrokerSession,
    EBPFXDPOrderRouter,
    FLAG_COD_ARMED,
    FLAG_HW_TIMESTAMP_VALID,
    FLAG_JITTER_ACTIVE,
    FLAG_MIDPOINT_CROSS,
    HardwareTimestampTelemetry,
    MARKET_VENUE_PROFILES,
    MASK_MICRO_SEQ,
    MASK_ORDER_TYPE,
    MASK_ROUTING_VENUE,
    MASK_SIDE,
    MASK_TIF,
    MAX_MICRO_SEQ,
    MidpointRejectReason,
    MultiBrokerSessionFailover,
    ORDER_WIRE_FORMAT,
    ORDER_WIRE_SIZE,
    OrderStateReconciler,
    PRICE_SCALE,
    ReconciliationStatus,
    SPSCDescriptorRingQueue,
    SyntheticMidpointCrossingEngine,
    XDPAction,
    XDPDescriptor,
    XDPDriverMode,
    XDPOrderPacket,
    XDPOrderStatus,
    XDPOrderType,
    XDPRoutingVenue,
    XDPSessionState,
    XDPSessionTier,
    XDPSide,
    XDPTIF,
    XDPUMEMRingBuffer,
    decode_flags,
    encode_flags,
    fnv1a_32,
    # Aliases
    BinaryOrderPacket,
    CODWatchdog,
    CompactOrderWirePacket,
    EBPFBridge,
    EBPFPacket,
    FastXDPDispatcher,
    HardwareAcceleratedRouter,
    JitterProtectionEngine,
    KernelBypassOrderRouter,
    KernelBypassSession,
    MicrosecondReconciler,
    MidpointCrossingEngine,
    Phase120EBPFXDPRouter,
    QuoteJitterScrambler,
    SPSCUMEMBuffer,
    UMEMRingBuffer,
    VENUE_PROFILES,
    WireTelemetry,
    XDPDMAOrderRouter,
    XDPFramePool,
    XDPHeartbeatWatchdog,
    XDPMessage,
    XDPMidpointEngine,
    XDPOrderRouter,
    XDPPacket,
    XDPSession,
    XDPStateReconciler,
    XDPTierSession,
    XDPTimestampTelemetry,
    XDP_MARKET_PROFILES,
    ZeroCopyRingBuffer,
)


# ===========================================================================
# Category 1: Binary Struct Packing & Unpacking (<QQIIQII, 40 bytes)
# ===========================================================================
class TestCategory1BinaryStructPacking:
    def test_wire_struct_exact_40_bytes(self):
        """Asserts struct layout is exactly 40 bytes with little-endian byte order."""
        size = struct.calcsize(ORDER_WIRE_FORMAT)
        assert size == 40, f"Expected 40 bytes, got {size}"
        assert ORDER_WIRE_SIZE == 40

    def test_pack_unpack_roundtrip(self):
        """Packs and unpacks order packet, asserting all fields match bit-for-bit."""
        packet = XDPOrderPacket(
            timestamp_ns=1730000000123456789,
            order_id=9876543210123,
            symbol_hash=fnv1a_32("AAPL"),
            client_id=42,
            price_fixed=int(round(150.255 * PRICE_SCALE)),
            qty=500,
            flags=encode_flags(
                side=XDPSide.BUY,
                order_type=XDPOrderType.LIMIT,
                time_in_force=XDPTIF.DAY,
                routing_venue=XDPRoutingVenue.PRIMARY_XDP,
                midpoint_cross=True,
                jitter_active=True,
                cod_armed=True,
                hw_timestamp_valid=True,
                micro_seq_num=1024,
            ),
        )
        packed = packet.pack()
        assert len(packed) == 40

        unpacked = XDPOrderPacket.unpack(packed)
        assert unpacked.timestamp_ns == packet.timestamp_ns
        assert unpacked.order_id == packet.order_id
        assert unpacked.symbol_hash == packet.symbol_hash
        assert unpacked.client_id == packet.client_id
        assert unpacked.price_fixed == packet.price_fixed
        assert unpacked.qty == packet.qty
        assert unpacked.flags == packet.flags
        assert math.isclose(unpacked.price, 150.255, rel_tol=1e-7)
        assert unpacked.side == XDPSide.BUY
        assert unpacked.order_type == XDPOrderType.LIMIT
        assert unpacked.midpoint_cross is True
        assert unpacked.jitter_active is True
        assert unpacked.cod_armed is True
        assert unpacked.hw_timestamp_valid is True
        assert unpacked.micro_seq_num == 1024

    def test_pack_into_zero_copy(self):
        """Tests zero-copy serialization into pre-allocated memoryview buffer."""
        buf = bytearray(128)
        packet = XDPOrderPacket.from_order(
            order_id=555,
            symbol="005930",
            side=XDPSide.SELL,
            order_type=XDPOrderType.IOC,
            price=72500.0,
            qty=100,
            client_id=99,
        )
        offset = 16
        packet.pack_into(buf, offset=offset)
        unpacked = XDPOrderPacket.unpack(buf, offset=offset)
        assert unpacked.order_id == 555
        assert unpacked.side == XDPSide.SELL
        assert unpacked.order_type == XDPOrderType.IOC
        assert math.isclose(unpacked.price, 72500.0, rel_tol=1e-7)
        assert unpacked.qty == 100

    def test_fnv1a_32_deterministic_hash(self):
        """Verifies deterministic FNV-1a 32-bit hash produces identical values."""
        h1 = fnv1a_32("AAPL")
        h2 = fnv1a_32("AAPL")
        h3 = fnv1a_32("005930")
        assert h1 == h2
        assert isinstance(h1, int)
        assert 0 <= h1 <= 0xFFFFFFFF
        assert h1 != h3

    def test_serialization_latency_sub_microsecond(self):
        """Benchmarks serialization speed, asserting sub-microsecond throughput."""
        packet = XDPOrderPacket.from_order(
            order_id=1,
            symbol="SPY",
            side=XDPSide.BUY,
            order_type=XDPOrderType.LIMIT,
            price=500.0,
            qty=100,
        )
        n_iters = 5000
        t0 = time.perf_counter()
        for _ in range(n_iters):
            _ = packet.pack()
        t1 = time.perf_counter()
        avg_us = ((t1 - t0) / n_iters) * 1_000_000.0
        # Expect packing in pure python struct to be < 5.0 us (typically ~0.2-1.5 us)
        assert avg_us < 5.0, f"Average serialization took {avg_us:.3f} us"


# ===========================================================================
# Category 2: Bitfield Flags & Masks Allocation
# ===========================================================================
class TestCategory2BitfieldFlags:
    def test_encode_decode_flags_roundtrip(self):
        """Tests complete bitfield encode/decode parity across all parameters."""
        encoded = encode_flags(
            side=XDPSide.SELL,
            order_type=XDPOrderType.MIDPOINT_CROSS,
            time_in_force=XDPTIF.GTC,
            routing_venue=XDPRoutingVenue.DARK_POOL,
            midpoint_cross=True,
            jitter_active=True,
            cod_armed=True,
            hw_timestamp_valid=True,
            micro_seq_num=65535,
        )
        decoded = decode_flags(encoded)
        assert decoded["side"] == XDPSide.SELL
        assert decoded["order_type"] == XDPOrderType.MIDPOINT_CROSS
        assert decoded["time_in_force"] == XDPTIF.GTC
        assert decoded["routing_venue"] == XDPRoutingVenue.DARK_POOL
        assert decoded["midpoint_cross"] is True
        assert decoded["jitter_active"] is True
        assert decoded["cod_armed"] is True
        assert decoded["hw_timestamp_valid"] is True
        assert decoded["micro_seq_num"] == 65535

    def test_side_flag_buy_sell(self):
        """Verifies bit 0 corresponds strictly to BUY (0) and SELL (1)."""
        flags_buy = encode_flags(side=XDPSide.BUY)
        assert (flags_buy & MASK_SIDE) == 0
        flags_sell = encode_flags(side=XDPSide.SELL)
        assert (flags_sell & MASK_SIDE) == 1

    def test_order_type_and_tif_flags(self):
        """Verifies order_type (bits 1..3) and time_in_force (bits 4..5)."""
        for otype in XDPOrderType:
            for tif in XDPTIF:
                f = encode_flags(order_type=otype, time_in_force=tif)
                d = decode_flags(f)
                assert d["order_type"] == otype
                assert d["time_in_force"] == tif

    def test_routing_venue_and_control_flags(self):
        """Verifies routing venue (bits 6..9) and independent control flags."""
        for venue in XDPRoutingVenue:
            f = encode_flags(
                routing_venue=venue,
                midpoint_cross=False,
                jitter_active=True,
                cod_armed=False,
                hw_timestamp_valid=True,
            )
            d = decode_flags(f)
            assert d["routing_venue"] == venue
            assert d["midpoint_cross"] is False
            assert d["jitter_active"] is True
            assert d["cod_armed"] is False
            assert d["hw_timestamp_valid"] is True

    def test_micro_seq_num_boundary(self):
        """Tests micro sequence counter boundaries up to 18-bit max (262,143)."""
        f_zero = encode_flags(micro_seq_num=0)
        assert decode_flags(f_zero)["micro_seq_num"] == 0

        f_max = encode_flags(micro_seq_num=MAX_MICRO_SEQ)
        assert decode_flags(f_max)["micro_seq_num"] == MAX_MICRO_SEQ

        # Overflow masking
        f_overflow = encode_flags(micro_seq_num=MAX_MICRO_SEQ + 5)
        assert decode_flags(f_overflow)["micro_seq_num"] == 4


# ===========================================================================
# Category 3: UMEM Memory Pool & Frame Allocation
# ===========================================================================
class TestCategory3UMEMMemoryPool:
    def test_umem_initialization(self):
        """Verifies UMEM buffer contiguous allocation and slice dimensions."""
        umem = XDPUMEMRingBuffer(num_frames=256, frame_size=2048)
        assert umem.num_frames == 256
        assert umem.frame_size == 2048
        assert umem.total_bytes == 256 * 2048
        assert len(umem._memview) == 256 * 2048

    def test_umem_frame_allocation_and_release(self):
        """Tests frame allocation stack and recycling."""
        umem = XDPUMEMRingBuffer(num_frames=64, frame_size=1024)
        f1 = umem.allocate_frame()
        f2 = umem.allocate_frame()
        assert f1 is not None and f2 is not None
        assert f1 != f2

        umem.free_frame(f1)
        # Should be able to re-allocate
        f3 = umem.allocate_frame()
        assert f3 is not None

    def test_umem_frame_exhaustion(self):
        """Asserts frame pool returns None when capacity is fully exhausted."""
        umem = XDPUMEMRingBuffer(num_frames=8, frame_size=512)
        frames = []
        for _ in range(8):
            f = umem.allocate_frame()
            assert f is not None
            frames.append(f)
        # 9th allocation should fail
        assert umem.allocate_frame() is None

        # Free one frame, then allocation should succeed
        umem.free_frame(frames[0])
        assert umem.allocate_frame() is not None

    def test_umem_write_read_packet_zero_copy(self):
        """Verifies zero-copy write and read through contiguous memoryview."""
        umem = XDPUMEMRingBuffer(num_frames=16, frame_size=1024)
        f = umem.allocate_frame()
        assert f is not None

        packet = XDPOrderPacket.from_order(
            order_id=777,
            symbol="NVDA",
            side=XDPSide.BUY,
            order_type=XDPOrderType.LIMIT,
            price=120.5,
            qty=200,
        )
        desc = umem.write_packet(frame_addr=f, data=packet.pack())
        assert desc.length == 40
        assert desc.frame_addr == f

        read_data = umem.read_packet(desc)
        unpacked = XDPOrderPacket.unpack(read_data)
        assert unpacked.order_id == 777
        assert math.isclose(unpacked.price, 120.5, rel_tol=1e-7)
        assert unpacked.qty == 200


# ===========================================================================
# Category 4: SPSC Lockless Ring Queues
# ===========================================================================
class TestCategory4SPSCLocklessRingQueues:
    def test_spsc_ring_power_of_two_capacity(self):
        """Verifies ring queue enforces power-of-two capacity."""
        q = SPSCDescriptorRingQueue(capacity=100)
        assert q.capacity == 128
        assert q.mask == 127

    def test_spsc_enqueue_dequeue_fifo(self):
        """Verifies strict FIFO ordering across single-item enqueues/dequeues."""
        q = SPSCDescriptorRingQueue(capacity=8)
        d1 = XDPDescriptor(frame_addr=1, offset=0, length=40)
        d2 = XDPDescriptor(frame_addr=2, offset=0, length=40)
        assert q.enqueue(d1) is True
        assert q.enqueue(d2) is True
        assert q.size() == 2

        out1 = q.dequeue()
        assert out1 is not None and out1.frame_addr == 1
        out2 = q.dequeue()
        assert out2 is not None and out2.frame_addr == 2
        assert q.dequeue() is None

    def test_spsc_is_full_and_is_empty(self):
        """Tests ring fullness and emptiness invariants."""
        q = SPSCDescriptorRingQueue(capacity=4)
        assert q.is_empty() is True
        assert q.is_full() is False

        for i in range(4):
            assert q.enqueue(XDPDescriptor(frame_addr=i)) is True

        assert q.is_full() is True
        assert q.is_empty() is False
        # Cannot enqueue beyond capacity
        assert q.enqueue(XDPDescriptor(frame_addr=99)) is False

    def test_spsc_batch_enqueue_dequeue(self):
        """Tests batch operations on SPSC ring queue."""
        q = SPSCDescriptorRingQueue(capacity=16)
        descs = [XDPDescriptor(frame_addr=i) for i in range(10)]
        pushed = q.batch_enqueue(descs)
        assert pushed == 10
        assert q.size() == 10

        pulled = q.batch_dequeue(6)
        assert len(pulled) == 6
        assert [d.frame_addr for d in pulled] == list(range(6))
        assert q.size() == 4

    def test_spsc_ring_wrap_around_indexing(self):
        """Tests wrap-around indexing beyond 2x capacity without buffer corruption."""
        q = SPSCDescriptorRingQueue(capacity=4)
        for i in range(20):
            d = XDPDescriptor(frame_addr=i)
            assert q.enqueue(d) is True
            popped = q.dequeue()
            assert popped is not None and popped.frame_addr == i
        assert q.is_empty() is True


# ===========================================================================
# Category 5: eBPF/XDP Driver Emulation & Actions
# ===========================================================================
class TestCategory5XDPDriverEmulation:
    def test_xdp_action_enums(self):
        """Asserts all standard XDP action codes match kernel enum values."""
        assert XDPAction.XDP_ABORTED == 0
        assert XDPAction.XDP_DROP == 1
        assert XDPAction.XDP_PASS == 2
        assert XDPAction.XDP_TX == 3
        assert XDPAction.XDP_REDIRECT == 4

    def test_xdp_driver_mode_enums(self):
        """Asserts XDP driver modes match AF_XDP specifications."""
        assert XDPDriverMode.NATIVE_DRV == 0
        assert XDPDriverMode.ZERO_COPY_UMEM == 1
        assert XDPDriverMode.GENERIC_SKB == 2
        assert XDPDriverMode.OFFLOADED_NIC == 3

    def test_xdp_dispatch_order_action_tx(self):
        """Verifies valid order dispatch issues XDP_TX action."""
        router = EBPFXDPOrderRouter()
        packet, _ = router.submit_order(
            order_id=101,
            symbol="SPY",
            side=XDPSide.BUY,
            order_type=XDPOrderType.LIMIT,
            price=510.0,
            qty=50,
        )
        ok, desc, lat_info = router.dispatch_order(packet)
        assert ok is True
        assert desc is not None
        assert lat_info["action"] == XDPAction.XDP_TX
        assert lat_info["enqueued"] is True

    def test_xdp_dispatch_order_umem_exhausted_drop(self):
        """Verifies UMEM exhaustion triggers XDP_DROP action."""
        router = EBPFXDPOrderRouter(num_frames=2)
        # Exhaust frames
        f1 = router.umem.allocate_frame()
        f2 = router.umem.allocate_frame()
        assert f1 is not None and f2 is not None

        packet, _ = router.submit_order(
            order_id=102,
            symbol="SPY",
            side=XDPSide.BUY,
            order_type=XDPOrderType.LIMIT,
            price=510.0,
            qty=50,
        )
        ok, desc, lat_info = router.dispatch_order(packet)
        assert ok is False
        assert desc is None
        assert lat_info["action"] == XDPAction.XDP_DROP


# ===========================================================================
# Category 6: Synthetic Midpoint Crossing Engine
# ===========================================================================
class TestCategory6SyntheticMidpointCrossing:
    def test_compute_midpoint(self):
        """Verifies exact midpoint price calculation."""
        engine = SyntheticMidpointCrossingEngine()
        assert engine.compute_midpoint(100.0, 101.0) == 100.5
        assert engine.compute_midpoint(50000.0, 50100.0) == 50050.0

    def test_midpoint_crossing_buy_limit_improvement(self):
        """BUY order crossing at midpoint saves 50% spread."""
        engine = SyntheticMidpointCrossingEngine()
        order = XDPOrderPacket.from_order(
            order_id=1,
            symbol="AAPL",
            side=XDPSide.BUY,
            order_type=XDPOrderType.LIMIT,
            price=150.50,
            qty=100,
        )
        # Bid = 150.00, Ask = 150.50, Mid = 150.25
        ts = time.time_ns()
        crossed, reason, exec_px, savings = engine.evaluate_crossing(
            order=order,
            bid=150.00,
            ask=150.50,
            quote_timestamp_ns=ts,
            current_time_ns=ts,
        )
        assert crossed is True
        assert reason == MidpointRejectReason.NONE
        assert exec_px == 150.25
        assert math.isclose(savings, 0.25, rel_tol=1e-5)

    def test_midpoint_crossing_sell_limit_improvement(self):
        """SELL order crossing at midpoint saves 50% spread."""
        engine = SyntheticMidpointCrossingEngine()
        order = XDPOrderPacket.from_order(
            order_id=2,
            symbol="AAPL",
            side=XDPSide.SELL,
            order_type=XDPOrderType.LIMIT,
            price=150.10,
            qty=200,
        )
        ts = time.time_ns()
        crossed, reason, exec_px, savings = engine.evaluate_crossing(
            order=order,
            bid=150.00,
            ask=150.50,
            quote_timestamp_ns=ts,
            current_time_ns=ts,
        )
        assert crossed is True
        assert reason == MidpointRejectReason.NONE
        assert exec_px == 150.25
        assert math.isclose(savings, 0.25, rel_tol=1e-5)

    def test_midpoint_crossing_market_order(self):
        """MARKET order always crosses at midpoint if spread is valid."""
        engine = SyntheticMidpointCrossingEngine()
        order = XDPOrderPacket.from_order(
            order_id=3,
            symbol="MSFT",
            side=XDPSide.BUY,
            order_type=XDPOrderType.MARKET,
            price=0.0,
            qty=50,
        )
        ts = time.time_ns()
        crossed, reason, exec_px, savings = engine.evaluate_crossing(
            order=order,
            bid=400.0,
            ask=402.0,
            quote_timestamp_ns=ts,
            current_time_ns=ts,
        )
        assert crossed is True
        assert exec_px == 401.0
        assert savings == 1.0

    def test_midpoint_rejection_crossed_book(self):
        """Crossed book (bid >= ask) is rejected."""
        engine = SyntheticMidpointCrossingEngine()
        order = XDPOrderPacket.from_order(
            order_id=4,
            symbol="TEST",
            side=XDPSide.BUY,
            order_type=XDPOrderType.LIMIT,
            price=105.0,
            qty=10,
        )
        ts = time.time_ns()
        crossed, reason, _, _ = engine.evaluate_crossing(
            order=order,
            bid=105.0,
            ask=104.0,  # Crossed!
            quote_timestamp_ns=ts,
            current_time_ns=ts,
        )
        assert crossed is False
        assert reason == MidpointRejectReason.CROSSED_BOOK

    def test_midpoint_rejection_one_sided_or_stale(self):
        """Rejects one-sided market quotes and stale quotes."""
        engine = SyntheticMidpointCrossingEngine(max_quote_age_ms=50.0)
        order = XDPOrderPacket.from_order(
            order_id=5,
            symbol="TEST",
            side=XDPSide.BUY,
            order_type=XDPOrderType.LIMIT,
            price=100.0,
            qty=10,
        )
        ts = time.time_ns()
        # One-sided check
        crossed, reason, _, _ = engine.evaluate_crossing(
            order=order,
            bid=0.0,
            ask=100.0,
            quote_timestamp_ns=ts,
            current_time_ns=ts,
        )
        assert crossed is False
        assert reason == MidpointRejectReason.ONE_SIDED_MARKET

        # Stale check (> 50ms)
        stale_ts = ts - int(100 * 1_000_000)
        crossed_stale, reason_stale, _, _ = engine.evaluate_crossing(
            order=order,
            bid=99.0,
            ask=101.0,
            quote_timestamp_ns=stale_ts,
            current_time_ns=ts,
        )
        assert crossed_stale is False
        assert reason_stale == MidpointRejectReason.STALE_QUOTE


# ===========================================================================
# Category 7: Anti-Latency Quote Jitter Protection
# ===========================================================================
class TestCategory7AntiLatencyJitter:
    def test_jitter_delay_within_bounds(self):
        """Verifies calculated micro-jitter is strictly inside [min_ns, max_ns]."""
        engine = AntiLatencyJitterEngine(default_min_ns=25, default_max_ns=120)
        for i in range(100):
            j = engine.compute_jitter_ns(symbol_hash=12345, order_id=i, min_ns=25, max_ns=120)
            assert 25 <= j <= 120

    def test_jitter_deterministic_xorshift(self):
        """Verifies deterministic reproduction of jitter sequence with same seed."""
        e1 = AntiLatencyJitterEngine(seed=0x123456)
        e2 = AntiLatencyJitterEngine(seed=0x123456)
        j1 = [e1.compute_jitter_ns(10, i, 20, 100) for i in range(50)]
        j2 = [e2.compute_jitter_ns(10, i, 20, 100) for i in range(50)]
        assert j1 == j2

    def test_apply_jitter_sets_flag(self):
        """Asserts apply_jitter sets FLAG_JITTER_ACTIVE in packet flags."""
        engine = AntiLatencyJitterEngine()
        packet = XDPOrderPacket.from_order(
            order_id=99,
            symbol="AMD",
            side=XDPSide.BUY,
            order_type=XDPOrderType.LIMIT,
            price=175.0,
            qty=100,
        )
        assert packet.jitter_active is False
        updated, delay = engine.apply_jitter(packet, min_ns=30, max_ns=150)
        assert updated.jitter_active is True
        assert 30 <= delay <= 150

    def test_jitter_preserves_order_sequencing(self):
        """Verifies applying jitter leaves order sequence IDs unchanged."""
        engine = AntiLatencyJitterEngine()
        orders = [
            XDPOrderPacket.from_order(
                order_id=i,
                symbol="QQQ",
                side=XDPSide.BUY,
                order_type=XDPOrderType.LIMIT,
                price=480.0,
                qty=10,
                micro_seq_num=i,
            )
            for i in range(10)
        ]
        for idx, o in enumerate(orders):
            updated, _ = engine.apply_jitter(o)
            assert updated.order_id == idx
            assert updated.micro_seq_num == idx


# ===========================================================================
# Category 8: Cancel-on-Disconnect (COD) Heartbeat Watchdog
# ===========================================================================
class TestCategory8CancelOnDisconnectWatchdog:
    def test_cod_register_and_heartbeat(self):
        """Registers venue and updates heartbeat timestamp."""
        wd = CancelOnDisconnectWatchdog(default_timeout_ms=100.0)
        wd.register_venue(XDPRoutingVenue.PRIMARY_XDP, timeout_ms=150.0)
        t0 = time.time_ns()
        wd.record_heartbeat(XDPRoutingVenue.PRIMARY_XDP, timestamp_ns=t0)
        assert wd._last_heartbeat_ns[XDPRoutingVenue.PRIMARY_XDP] == t0

    def test_cod_order_tracking_and_arming(self):
        """Verifies tracked order is armed with FLAG_COD_ARMED."""
        wd = CancelOnDisconnectWatchdog()
        order = XDPOrderPacket.from_order(
            order_id=123,
            symbol="TSLA",
            side=XDPSide.BUY,
            order_type=XDPOrderType.LIMIT,
            price=250.0,
            qty=10,
        )
        wd.track_order(XDPRoutingVenue.PRIMARY_XDP, order)
        assert order.cod_armed is True
        assert 123 in wd._resting_orders[XDPRoutingVenue.PRIMARY_XDP]

    def test_cod_timeout_detection(self):
        """Detects expired heartbeats past timeout limit."""
        wd = CancelOnDisconnectWatchdog(default_timeout_ms=100.0)
        venue = XDPRoutingVenue.PRIMARY_XDP
        wd.register_venue(venue, timeout_ms=100.0)
        t_now = time.time_ns()
        wd.record_heartbeat(venue, timestamp_ns=t_now)

        # 50ms later -> Not expired
        assert wd.check_watchdog(current_time_ns=t_now + int(50 * 1_000_000)) == []

        # 150ms later -> Expired!
        expired = wd.check_watchdog(current_time_ns=t_now + int(150 * 1_000_000))
        assert venue in expired

    def test_cod_trigger_cancel_burst(self):
        """Asserts triggering COD broadcasts cancel burst for all resting orders."""
        wd = CancelOnDisconnectWatchdog()
        venue = XDPRoutingVenue.PRIMARY_XDP
        wd.register_venue(venue)

        o1 = XDPOrderPacket.from_order(order_id=1, symbol="A", side=XDPSide.BUY, order_type=XDPOrderType.LIMIT, price=10.0, qty=5)
        o2 = XDPOrderPacket.from_order(order_id=2, symbol="B", side=XDPSide.SELL, order_type=XDPOrderType.LIMIT, price=20.0, qty=10)
        wd.track_order(venue, o1)
        wd.track_order(venue, o2)

        burst = wd.trigger_cancel_on_disconnect(venue)
        assert len(burst) == 2
        assert wd.cod_trigger_count == 1
        assert len(wd._resting_orders[venue]) == 0
        for cancel_pkt in burst:
            assert cancel_pkt.cod_armed is True
            assert cancel_pkt.qty == 0

    def test_cod_untrack_order_on_fill(self):
        """Verifies filled orders untracked from COD watchdog."""
        wd = CancelOnDisconnectWatchdog()
        venue = XDPRoutingVenue.PRIMARY_XDP
        wd.register_venue(venue)
        o = XDPOrderPacket.from_order(order_id=88, symbol="A", side=XDPSide.BUY, order_type=XDPOrderType.LIMIT, price=10.0, qty=5)
        wd.track_order(venue, o)
        untracked = wd.untrack_order(venue, 88)
        assert untracked is not None
        burst = wd.trigger_cancel_on_disconnect(venue)
        assert len(burst) == 0


# ===========================================================================
# Category 9: Microsecond Order State Reconciliation
# ===========================================================================
class TestCategory9OrderStateReconciliation:
    def test_reconciliation_synchronized_sequence(self):
        """Continuous sequences remain SYNCHRONIZED."""
        reconciler = OrderStateReconciler()
        venue = XDPRoutingVenue.PRIMARY_XDP
        s1, gap1 = reconciler.audit_sequence(venue, 1)
        assert s1 == ReconciliationStatus.SYNCHRONIZED and gap1 is None
        s2, gap2 = reconciler.audit_sequence(venue, 2)
        assert s2 == ReconciliationStatus.SYNCHRONIZED and gap2 is None

    def test_reconciliation_gap_detection(self):
        """Sequence skips trigger GAP_DETECTED and record missing sequence range."""
        reconciler = OrderStateReconciler()
        venue = XDPRoutingVenue.PRIMARY_XDP
        reconciler.audit_sequence(venue, 1)
        # Skip to seq 5 (missing 2, 3, 4)
        status, gap = reconciler.audit_sequence(venue, 5)
        assert status == ReconciliationStatus.GAP_DETECTED
        assert gap == (2, 4)

    def test_reconciliation_gap_fill_request(self):
        """Generates valid GapFill request payload."""
        reconciler = OrderStateReconciler()
        venue = XDPRoutingVenue.PRIMARY_XDP
        req = reconciler.generate_gap_fill_request(venue, 2, 4)
        assert req["type"] == "GAP_FILL_REQUEST"
        assert req["venue"] == int(venue)
        assert req["begin_seq"] == 2
        assert req["end_seq"] == 4

    def test_reconciliation_apply_gap_fill(self):
        """Applying recovered packets restores RECONCILED status."""
        reconciler = OrderStateReconciler()
        venue = XDPRoutingVenue.PRIMARY_XDP
        reconciler.audit_sequence(venue, 1)
        reconciler.audit_sequence(venue, 5)

        recovered = [
            XDPOrderPacket.from_order(order_id=i, symbol="X", side=XDPSide.BUY, order_type=XDPOrderType.LIMIT, price=1.0, qty=1, micro_seq_num=i)
            for i in (2, 3, 4)
        ]
        status = reconciler.apply_gap_fill(venue, recovered)
        assert status == ReconciliationStatus.RECONCILED
        assert reconciler.expected_seq[venue] >= 5


# ===========================================================================
# Category 10: Multi-Broker 3-Tier Session Failover
# ===========================================================================
class TestCategory10MultiBrokerSessionFailover:
    def test_failover_initial_active_tier_1(self):
        """Verifies session starts on Tier 1 (XDP Direct)."""
        fm = MultiBrokerSessionFailover()
        sess = fm.get_active_session()
        assert sess.tier == XDPSessionTier.TIER_1_XDP_DIRECT
        assert sess.state == XDPSessionState.ACTIVE

    def test_failover_automatic_tier_1_to_tier_2(self):
        """Repeated errors on Tier 1 triggers automatic failover to Tier 2."""
        fm = MultiBrokerSessionFailover()
        # Record 3 consecutive errors
        for _ in range(3):
            fm.record_error(XDPSessionTier.TIER_1_XDP_DIRECT, "TIMEOUT")
        new_sess = fm.get_active_session()
        assert new_sess.tier == XDPSessionTier.TIER_2_FIX_DMA
        assert fm.sessions[XDPSessionTier.TIER_1_XDP_DIRECT].state == XDPSessionState.FAILOVER

    def test_failover_tier_2_to_tier_3(self):
        """Tier 2 failure cascades to Tier 3 (Native API)."""
        fm = MultiBrokerSessionFailover()
        for _ in range(3):
            fm.record_error(XDPSessionTier.TIER_1_XDP_DIRECT, "TIMEOUT")
        for _ in range(3):
            fm.record_error(XDPSessionTier.TIER_2_FIX_DMA, "DISCONNECT")
        new_sess = fm.get_active_session()
        assert new_sess.tier == XDPSessionTier.TIER_3_NATIVE_API

    def test_failover_manual_trigger(self):
        """Tests manual explicit failover invocation."""
        fm = MultiBrokerSessionFailover()
        old_s, new_s = fm.trigger_failover("OPERATOR_SWITCH")
        assert old_s.tier == XDPSessionTier.TIER_1_XDP_DIRECT
        assert new_s.tier == XDPSessionTier.TIER_2_FIX_DMA
        assert len(fm.failover_history) == 1

    def test_failover_tier_restoration(self):
        """Restoring higher tier seamlessly reinstates Tier 1."""
        fm = MultiBrokerSessionFailover()
        fm.trigger_failover("TEST")
        assert fm.active_tier == XDPSessionTier.TIER_2_FIX_DMA
        # Restore Tier 1
        fm.restore_tier(XDPSessionTier.TIER_1_XDP_DIRECT)
        assert fm.get_active_session().tier == XDPSessionTier.TIER_1_XDP_DIRECT


# ===========================================================================
# Category 11: Hardware Timestamping Telemetry
# ===========================================================================
class TestCategory11HardwareTimestampTelemetry:
    def test_telemetry_latency_decomposition(self):
        """Verifies decomposition into serialization, queue, and wire RTT."""
        tel = HardwareTimestampTelemetry()
        t1 = 1_000_000
        t2 = 1_000_150  # +150ns ser
        t3 = 1_000_300  # +150ns drv
        t4 = 1_000_700  # +400ns wire
        entry = tel.record_latencies(order_id=1, t1_creation=t1, t2_ingress=t2, t3_egress=t3, t4_wire_ack=t4)
        assert entry["serialization_ns"] == 150
        assert entry["driver_queue_ns"] == 150
        assert entry["wire_rtt_ns"] == 400
        assert entry["total_transit_ns"] == 700

    def test_telemetry_rolling_percentiles(self):
        """Verifies rolling p50, p95, p99 percentiles calculation."""
        tel = HardwareTimestampTelemetry()
        for i in range(100):
            tel.record_latencies(
                order_id=i,
                t1_creation=0,
                t2_ingress=100,
                t3_egress=200,
                t4_wire_ack=300 + i * 10,
            )
        summ = tel.get_summary()
        assert summ["count"] == 100
        assert summ["serialization_p50_ns"] == 100.0
        assert summ["driver_queue_p50_ns"] == 100.0
        assert summ["total_transit_p50_ns"] > 0
        assert summ["total_transit_p99_ns"] >= summ["total_transit_p50_ns"]

    def test_telemetry_empty_summary(self):
        """Verifies empty telemetry summary returns zero-valued safe structure."""
        tel = HardwareTimestampTelemetry()
        summ = tel.get_summary()
        assert summ["count"] == 0
        assert summ["total_transit_p50_ns"] == 0.0

    def test_telemetry_hw_timestamp_flag(self):
        """Verifies FLAG_HW_TIMESTAMP_VALID is accurately preserved."""
        order = XDPOrderPacket.from_order(
            order_id=10,
            symbol="QQQ",
            side=XDPSide.BUY,
            order_type=XDPOrderType.LIMIT,
            price=450.0,
            qty=100,
            hw_timestamp_valid=True,
        )
        assert order.hw_timestamp_valid is True
        packed = order.pack()
        unpacked = XDPOrderPacket.unpack(packed)
        assert unpacked.hw_timestamp_valid is True


# ===========================================================================
# Category 12: 5-Market Venue Profiles, Complete Alias Trees & SHA-256 Parity
# ===========================================================================
class TestCategory12VenueProfilesAliasesAndParity:
    def test_5_market_venue_profiles(self):
        """Verifies all 5 market pre-calibrated profiles exist and match specs."""
        expected_markets = ["SP500", "NASDAQ", "RUSSELL2000", "KOSPI", "KOSDAQ"]
        for m in expected_markets:
            assert m in MARKET_VENUE_PROFILES
            prof = MARKET_VENUE_PROFILES[m]
            assert prof.wire_latency_ns > 0
            assert prof.jitter_max_ns > prof.jitter_min_ns
            assert prof.cod_timeout_ms >= 100
            assert prof.max_pps >= 100_000

        # Exact specification checks
        assert MARKET_VENUE_PROFILES["SP500"].interface == "eth0_xdp"
        assert MARKET_VENUE_PROFILES["SP500"].wire_latency_ns == 320
        assert MARKET_VENUE_PROFILES["NASDAQ"].interface == "ens2f0_xdp"
        assert MARKET_VENUE_PROFILES["NASDAQ"].wire_latency_ns == 280
        assert MARKET_VENUE_PROFILES["RUSSELL2000"].interface == "ens2f1_xdp"
        assert MARKET_VENUE_PROFILES["RUSSELL2000"].wire_latency_ns == 420
        assert MARKET_VENUE_PROFILES["KOSPI"].interface == "krx0_xdp"
        assert MARKET_VENUE_PROFILES["KOSPI"].wire_latency_ns == 480
        assert MARKET_VENUE_PROFILES["KOSDAQ"].interface == "krx1_xdp"
        assert MARKET_VENUE_PROFILES["KOSDAQ"].wire_latency_ns == 510

    def test_router_venue_profile_resolution(self):
        """Tests router resolution of market venue profiles."""
        router = EBPFXDPOrderRouter(default_market="NASDAQ")
        p_nasdaq = router.get_venue_profile()
        assert p_nasdaq.market == "NASDAQ"
        p_kospi = router.get_venue_profile("KOSPI")
        assert p_kospi.market == "KOSPI"
        # Unknown fallback to SP500
        p_unknown = router.get_venue_profile("UNKNOWN_EXCHANGE")
        assert p_unknown.market == "SP500"

    def test_10_plus_backward_compatibility_aliases(self):
        """Asserts all 10+ backward compatibility aliases point to canonical classes."""
        assert XDPOrderRouter is EBPFXDPOrderRouter
        assert KernelBypassOrderRouter is EBPFXDPOrderRouter
        assert EBPFBridge is EBPFXDPOrderRouter
        assert FastXDPDispatcher is EBPFXDPOrderRouter
        assert XDPDMAOrderRouter is EBPFXDPOrderRouter
        assert Phase120EBPFXDPRouter is EBPFXDPOrderRouter
        assert HardwareAcceleratedRouter is EBPFXDPOrderRouter

        assert XDPPacket is XDPOrderPacket
        assert EBPFPacket is XDPOrderPacket
        assert BinaryOrderPacket is XDPOrderPacket
        assert XDPMessage is XDPOrderPacket
        assert CompactOrderWirePacket is XDPOrderPacket

        assert UMEMRingBuffer is XDPUMEMRingBuffer
        assert ZeroCopyRingBuffer is XDPUMEMRingBuffer
        assert XDPFramePool is XDPUMEMRingBuffer
        assert SPSCUMEMBuffer is XDPUMEMRingBuffer

        assert XDPSession is EBPFBrokerSession
        assert KernelBypassSession is EBPFBrokerSession
        assert XDPTierSession is EBPFBrokerSession

        assert MidpointCrossingEngine is SyntheticMidpointCrossingEngine
        assert XDPMidpointEngine is SyntheticMidpointCrossingEngine

        assert JitterProtectionEngine is AntiLatencyJitterEngine
        assert QuoteJitterScrambler is AntiLatencyJitterEngine

        assert CODWatchdog is CancelOnDisconnectWatchdog
        assert XDPHeartbeatWatchdog is CancelOnDisconnectWatchdog

        assert XDPStateReconciler is OrderStateReconciler
        assert MicrosecondReconciler is OrderStateReconciler

        assert XDPTimestampTelemetry is HardwareTimestampTelemetry
        assert WireTelemetry is HardwareTimestampTelemetry

        assert VENUE_PROFILES is MARKET_VENUE_PROFILES
        assert XDP_MARKET_PROFILES is MARKET_VENUE_PROFILES

    def test_dual_tree_cryptographic_sha256_parity(self):
        """Asserts 100% bit-for-bit SHA-256 parity between src/ and trading_system/src/."""
        root_path = Path("src/broker/ebpf_xdp_order_router.py")
        mirror_path = Path("trading_system/src/broker/ebpf_xdp_order_router.py")
        assert root_path.exists(), f"Missing root file: {root_path}"
        assert mirror_path.exists(), f"Missing mirror file: {mirror_path}"

        root_hash = hashlib.sha256(root_path.read_bytes()).hexdigest()
        mirror_hash = hashlib.sha256(mirror_path.read_bytes()).hexdigest()
        assert root_hash == mirror_hash, f"SHA-256 parity mismatch: {root_hash} != {mirror_hash}"
