"""
tests/test_phase122_kernel_bypass_gateway.py
============================================
Verification Test Suite for:
Zero-Copy Kernel-Bypass DPDK/AF_XDP Sub-Microsecond Multi-Venue Routing Gateway (Feature F583).
Phase 122 (Release R138 / v129 Production Master).
"""

from __future__ import annotations

import hashlib
import os
import struct
import sys
import time
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p in (str(PROJECT_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.broker.kernel_bypass_routing_gateway import (
    VERSION,
    RELEASE,
    FEATURE,
    WIRE_STRUCT_FORMAT,
    WIRE_STRUCT_SIZE,
    RING_BUFFER_CAPACITY,
    VenueCode,
    HardwarePriority,
    OrderSide,
    KernelBypassOrderDescriptor,
    GatewayExecutionTelemetry,
    KernelBypassRoutingGateway,
    AFXDPKernelBypassGateway,
)


class TestPhase122KernelBypassGateway:
    """Tests for Kernel-Bypass Multi-Venue Routing Gateway."""

    def test_tc01_version_and_metadata(self):
        """Verifies metadata constants."""
        assert VERSION == 122
        assert RELEASE == "R138"
        assert FEATURE == "F583"
        assert WIRE_STRUCT_SIZE == 32
        assert struct.calcsize(WIRE_STRUCT_FORMAT) == 32

    def test_tc02_dual_tree_sha256_parity(self):
        """Verifies 100% bit-for-bit SHA-256 parity between src/ and trading_system/src/."""
        f1 = PROJECT_ROOT / "src" / "broker" / "kernel_bypass_routing_gateway.py"
        f2 = TRADING_SYSTEM_DIR / "src" / "broker" / "kernel_bypass_routing_gateway.py"
        assert f1.exists(), f"File {f1} does not exist"
        assert f2.exists(), f"File {f2} does not exist"
        h1 = hashlib.sha256(f1.read_bytes()).hexdigest()
        h2 = hashlib.sha256(f2.read_bytes()).hexdigest()
        assert h1 == h2, f"SHA-256 mismatch: {h1} != {h2}"

    def test_tc03_32byte_struct_packing_and_unpacking(self):
        """Verifies binary serialization to exactly 32 bytes and lossless roundtrip."""
        desc = KernelBypassOrderDescriptor(
            client_order_id=1001,
            symbol_hash=0x12345678,
            venue_code=int(VenueCode.NASDAQ),
            quantity=500,
            price_scaled=1502500,  # $150.25
            flags=int(OrderSide.BUY),
            t1_host_submit_ns=1000000,
        )
        packed = desc.pack()
        assert len(packed) == 32
        unpacked = KernelBypassOrderDescriptor.unpack(packed, t1_ns=1000000)
        assert unpacked.client_order_id == 1001
        assert unpacked.symbol_hash == 0x12345678
        assert unpacked.venue_code == int(VenueCode.NASDAQ)
        assert unpacked.quantity == 500
        assert unpacked.price_scaled == 1502500
        assert unpacked.flags == int(OrderSide.BUY)

    def test_tc04_fnv1a_32_hashing(self):
        """Verifies deterministic FNV-1a 32-bit hash."""
        h1 = KernelBypassRoutingGateway.fnv1a_32_hash("AAPL")
        h2 = KernelBypassRoutingGateway.fnv1a_32_hash("AAPL")
        h3 = KernelBypassRoutingGateway.fnv1a_32_hash("NVDA")
        assert h1 == h2
        assert h1 != h3
        assert 0 <= h1 <= 0xffffffff

    def test_tc05_venue_resolution(self):
        """Verifies multi-venue routing resolution across domestic and global venues."""
        assert KernelBypassRoutingGateway.resolve_venue("KOSPI") == VenueCode.KRX
        assert KernelBypassRoutingGateway.resolve_venue("KOSDAQ") == VenueCode.KRX
        assert KernelBypassRoutingGateway.resolve_venue("NASDAQ") == VenueCode.NASDAQ
        assert KernelBypassRoutingGateway.resolve_venue("NYSE") == VenueCode.NYSE
        assert KernelBypassRoutingGateway.resolve_venue("RUSSELL2000") == VenueCode.ARCA
        assert KernelBypassRoutingGateway.resolve_venue("HKEX") == VenueCode.HKEX
        assert KernelBypassRoutingGateway.resolve_venue("TSE") == VenueCode.TSE

    def test_tc06_submit_order_and_telemetry(self):
        """Tests order submission and T1~T4 telemetry capture."""
        gateway = KernelBypassRoutingGateway()
        telem = gateway.submit_order(
            symbol="NVDA",
            market="NASDAQ",
            quantity=100,
            price=125.50,
            side=OrderSide.BUY,
            priority=HardwarePriority.IOC_MARKET,
        )
        assert isinstance(telem, GatewayExecutionTelemetry)
        assert telem.symbol == "NVDA"
        assert telem.venue == "NASDAQ"
        assert telem.t1_ns > 0
        assert telem.t2_ns >= telem.t1_ns
        assert telem.t3_ns >= telem.t2_ns
        assert telem.t4_ns >= telem.t3_ns
        assert telem.total_latency_ns >= 0
        assert len(telem.payload_bytes) == 32

    def test_tc07_emergency_cancel_all(self):
        """Tests emergency cancellation across all venues."""
        gateway = KernelBypassRoutingGateway()
        telems = gateway.emergency_cancel_all("EMERGENCY_TEST")
        assert len(telems) == len(VenueCode)
        for t in telems:
            assert t.priority == "EMERGENCY_CANCEL"
            assert len(t.payload_bytes) == 32

    def test_tc08_heartbeat_tick_and_cod(self):
        """Tests cancel-on-disconnect watchdog heartbeat timeout."""
        gateway = KernelBypassRoutingGateway()
        # Initial tick is fine
        assert gateway.heartbeat_tick() is True
        # Simulate elapsed time > 150ms
        gateway.last_heartbeat_time = time.time() - 0.200  # 200ms ago
        # Next tick should trigger COD and return False
        assert gateway.heartbeat_tick() is False

    def test_tc09_class_alias_parity(self):
        """Verifies class alias parity."""
        assert AFXDPKernelBypassGateway is KernelBypassRoutingGateway
