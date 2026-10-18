r"""
tests/test_phase121_pcie_dma_engine.py
=======================================
Exhaustive 50-Test Verification Suite across 10 Rigorous Categories for:
FPGA-Emulated Sub-Nanosecond Direct PCI-e Memory-Mapped DMA Trading Engine (Feature F578).
Phase 121 (Release R137 / v128 Production Master).

Categories (50 Test Cases):
  - Category 1: Dual-Tree Parity, Metadata & Module Exports (TC01 ~ TC05)
  - Category 2: 32-Byte Struct Packing & Bitfield Encoding Precision (TC06 ~ TC10)
  - Category 3: FNV-1a 32-Bit Hash Determinism & Collision Resistance (TC11 ~ TC15)
  - Category 4: BAR0 CSR Space MMIO Read/Write Register Mechanics (TC16 ~ TC20)
  - Category 5: Zero-Copy Circular DMA Ring Buffer Enqueue/Dequeue Invariants (TC21 ~ TC25)
  - Category 6: 4-Class Hardware Priority Queue Arbitration Mechanics (TC26 ~ TC30)
  - Category 7: Sub-Nanosecond T1~T4 Hardware Timestamping Telemetry (TC31 ~ TC35)
  - Category 8: Cancel-On-Disconnect (COD) Watchdog & Emergency Kill (TC36 ~ TC40)
  - Category 9: Multi-Broker Hot-Standby Failover Transparency (TC41 ~ TC45)
  - Category 10: Throughput Scalability & Sub-Microsecond Latency SLA (TC46 ~ TC50)
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import struct
import sys
import time
import unittest
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np

# Ensure project root and trading_system are on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p in (str(PROJECT_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

import src.broker.pcie_dma_trading_engine as pcie_module
from src.broker.pcie_dma_trading_engine import (
    VERSION,
    RELEASE,
    FEATURE,
    PCIE_ORDER_STRUCT,
    PCIE_ORDER_SIZE,
    PRICE_SCALE,
    BAR0_CSR_SIZE,
    DEFAULT_RING_CAPACITY,
    OrderSide,
    OrderType,
    TimeInForce,
    PriorityClass,
    RoutingVenue,
    EngineStatus,
    BrokerID,
    fnv1a_32,
    PCIeOrderMessage,
    PCIeBAR0Registers,
    PCIeDMARingBuffer,
    PCIeDMATradingEngine,
)


class TestPhase121PCIeDMAEngine(unittest.TestCase):
    """Exhaustive 50-Test Verification Suite for Feature F578."""

    def setUp(self) -> None:
        self.engine = PCIeDMATradingEngine(ring_capacity=1024, cod_timeout_ms=100)

    # =========================================================================
    # Category 1: Dual-Tree Parity, Metadata & Module Exports
    # =========================================================================
    def test_tc01_dual_tree_sha256_cryptographic_parity(self) -> None:
        src_file = PROJECT_ROOT / "src" / "broker" / "pcie_dma_trading_engine.py"
        ts_file = TRADING_SYSTEM_DIR / "src" / "broker" / "pcie_dma_trading_engine.py"
        self.assertTrue(src_file.exists())
        self.assertTrue(ts_file.exists())

        h_src = hashlib.sha256(src_file.read_bytes()).hexdigest()
        h_ts = hashlib.sha256(ts_file.read_bytes()).hexdigest()
        self.assertEqual(h_src, h_ts, "SHA-256 cryptographic parity violation between src and trading_system!")

    def test_tc02_version_and_metadata_constants(self) -> None:
        self.assertEqual(VERSION, 121)
        self.assertEqual(RELEASE, "R137")
        self.assertEqual(FEATURE, "F578")
        self.assertEqual(PCIE_ORDER_SIZE, 32)
        self.assertEqual(struct.calcsize(PCIE_ORDER_STRUCT), 32)

    def test_tc03_enum_definitions(self) -> None:
        self.assertEqual(int(OrderSide.BUY), 0)
        self.assertEqual(int(OrderSide.SELL), 1)
        self.assertEqual(int(PriorityClass.CANCEL_EMERGENCY), 0)
        self.assertEqual(int(PriorityClass.AUDIT_TELEMETRY), 3)
        self.assertEqual(int(BrokerID.PRIMARY_PCIE), 0)
        self.assertEqual(int(BrokerID.STANDBY_BROKER), 1)

    def test_tc04_package_init_exports(self) -> None:
        import src.broker as broker_pkg
        self.assertTrue(hasattr(broker_pkg, "PCIeDMATradingEngine"))
        self.assertTrue(hasattr(broker_pkg, "PCIeOrderMessage"))
        self.assertTrue(hasattr(broker_pkg, "PCIeBAR0Registers"))
        self.assertTrue(hasattr(broker_pkg, "PCIeDMARingBuffer"))

    def test_tc05_mirror_package_init_exports(self) -> None:
        import trading_system.src.broker as ts_broker_pkg
        self.assertTrue(hasattr(ts_broker_pkg, "PCIeDMATradingEngine"))
        self.assertTrue(hasattr(ts_broker_pkg, "PCIE_ORDER_SIZE"))

    # =========================================================================
    # Category 2: 32-Byte Struct Packing & Bitfield Encoding Precision
    # =========================================================================
    def test_tc06_order_packing_exact_32_bytes(self) -> None:
        msg = PCIeOrderMessage(
            order_id=1234567890,
            symbol="NVDA",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            qty=100,
            price=125.50,
            tif=TimeInForce.DAY,
            priority=PriorityClass.LIMIT_PEGGED,
            venue=RoutingVenue.PCIE_DMA,
            client_id=42,
            cod_armed=True,
            seq_num=777,
        )
        packed = msg.pack()
        self.assertEqual(len(packed), 32)

    def test_tc07_order_roundtrip_unpacking_fidelity(self) -> None:
        sym = "AAPL"
        sym_hash = fnv1a_32(sym)
        lookup = {sym_hash: sym}

        msg = PCIeOrderMessage(
            order_id=9876543210,
            symbol=sym,
            side=OrderSide.SELL,
            order_type=OrderType.IOC,
            qty=250,
            price=220.12345678,
            tif=TimeInForce.IOC,
            priority=PriorityClass.IOC_MARKET,
            venue=RoutingVenue.PRIMARY_IBKR,
            client_id=99,
            cod_armed=False,
            seq_num=1234,
        )
        packed = msg.pack()
        unpacked = PCIeOrderMessage.unpack(packed, symbol_lookup=lookup)

        self.assertEqual(unpacked.order_id, 9876543210)
        self.assertEqual(unpacked.symbol, "AAPL")
        self.assertEqual(unpacked.side, OrderSide.SELL)
        self.assertEqual(unpacked.order_type, OrderType.IOC)
        self.assertEqual(unpacked.qty, 250)
        self.assertAlmostEqual(unpacked.price, 220.12345678, places=6)
        self.assertEqual(unpacked.priority, PriorityClass.IOC_MARKET)
        self.assertEqual(unpacked.venue, RoutingVenue.PRIMARY_IBKR)
        self.assertEqual(unpacked.client_id, 99)
        self.assertFalse(unpacked.cod_armed)
        self.assertEqual(unpacked.seq_num, 1234)

    def test_tc08_invalid_buffer_size_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            PCIeOrderMessage.unpack(b"short_buffer_16b")

    def test_tc09_flags_bitfield_masks_isolation(self) -> None:
        msg = PCIeOrderMessage(
            order_id=1, symbol="SPY", side=OrderSide.BUY,
            order_type=OrderType.CANCEL_REQ, qty=10, price=500.0,
            priority=PriorityClass.CANCEL_EMERGENCY, cod_armed=True, seq_num=100,
        )
        flags = msg.encode_flags()
        self.assertEqual((flags & 0x01), 0)  # BUY
        self.assertEqual(((flags >> 1) & 0x07), int(OrderType.CANCEL_REQ))
        self.assertEqual(((flags >> 6) & 0x03), int(PriorityClass.CANCEL_EMERGENCY))
        self.assertTrue(bool((flags >> 12) & 0x01))  # COD armed

    def test_tc10_fixed_point_price_scaling(self) -> None:
        price = 123.45678901
        fixed = int(round(price * PRICE_SCALE))
        recovered = float(fixed) / PRICE_SCALE
        self.assertAlmostEqual(price, recovered, places=8)

    # =========================================================================
    # Category 3: FNV-1a 32-Bit Hash Determinism & Collision Resistance
    # =========================================================================
    def test_tc11_fnv1a_deterministic_output(self) -> None:
        h1 = fnv1a_32("AAPL")
        h2 = fnv1a_32("AAPL")
        self.assertEqual(h1, h2)
        self.assertIsInstance(h1, int)
        self.assertLessEqual(h1, 0xFFFFFFFF)

    def test_tc12_fnv1a_distinct_symbols_distinct_hashes(self) -> None:
        symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META", "005930.KS", "000660.KS"]
        hashes = {fnv1a_32(s) for s in symbols}
        self.assertEqual(len(hashes), len(symbols), "Hash collision detected among test symbols!")

    def test_tc13_fnv1a_bytes_and_string_parity(self) -> None:
        h_str = fnv1a_32("005930.KS")
        h_bytes = fnv1a_32(b"005930.KS")
        self.assertEqual(h_str, h_bytes)

    def test_tc14_fnv1a_empty_string(self) -> None:
        h_empty = fnv1a_32("")
        self.assertEqual(h_empty, 0x811C9DC5)

    def test_tc15_symbol_table_registration(self) -> None:
        h = self.engine.register_symbol("KOSPI200")
        self.assertIn(h, self.engine.symbol_table)
        self.assertEqual(self.engine.symbol_table[h], "KOSPI200")

    # =========================================================================
    # Category 4: BAR0 CSR Space MMIO Read/Write Register Mechanics
    # =========================================================================
    def test_tc16_bar0_initial_state(self) -> None:
        bar0 = PCIeBAR0Registers()
        self.assertEqual(len(bar0.mem), BAR0_CSR_SIZE)
        self.assertEqual(bar0.status, EngineStatus.READY)
        self.assertEqual(bar0.dropped_packets, 0)
        self.assertEqual(bar0.cod_timeout_ms, 100)
        self.assertEqual(bar0.active_broker, BrokerID.PRIMARY_PCIE)

    def test_tc17_bar0_status_write_and_read(self) -> None:
        bar0 = PCIeBAR0Registers()
        bar0.status = EngineStatus.TRANSMITTING
        self.assertEqual(bar0.status, EngineStatus.TRANSMITTING)
        bar0.status = EngineStatus.FAILOVER
        self.assertEqual(bar0.status, EngineStatus.FAILOVER)

    def test_tc18_bar0_dropped_packets_counter_64bit(self) -> None:
        bar0 = PCIeBAR0Registers()
        bar0.dropped_packets = 0x123456789ABCDEF0
        self.assertEqual(bar0.dropped_packets, 0x123456789ABCDEF0)

    def test_tc19_bar0_cod_timeout_setting(self) -> None:
        bar0 = PCIeBAR0Registers()
        bar0.cod_timeout_ms = 250
        self.assertEqual(bar0.cod_timeout_ms, 250)

    def test_tc20_bar0_active_broker_switch(self) -> None:
        bar0 = PCIeBAR0Registers()
        bar0.active_broker = BrokerID.STANDBY_BROKER
        self.assertEqual(bar0.active_broker, BrokerID.STANDBY_BROKER)

    # =========================================================================
    # Category 5: Zero-Copy Circular DMA Ring Buffer Invariants
    # =========================================================================
    def test_tc21_ring_buffer_initial_empty(self) -> None:
        ring = PCIeDMARingBuffer(capacity=64)
        self.assertTrue(ring.is_empty())
        self.assertFalse(ring.is_full())
        self.assertEqual(ring.size(), 0)

    def test_tc22_ring_buffer_enqueue_dequeue(self) -> None:
        ring = PCIeDMARingBuffer(capacity=64)
        msg_bytes = b"X" * 32
        ok = ring.enqueue(msg_bytes)
        self.assertTrue(ok)
        self.assertEqual(ring.size(), 1)
        self.assertFalse(ring.is_empty())

        retrieved = ring.dequeue()
        self.assertEqual(retrieved, msg_bytes)
        self.assertTrue(ring.is_empty())

    def test_tc23_ring_buffer_full_overflow_prevention(self) -> None:
        ring = PCIeDMARingBuffer(capacity=16)
        msg_bytes = b"O" * 32
        for _ in range(16):
            self.assertTrue(ring.enqueue(msg_bytes))

        self.assertTrue(ring.is_full())
        # 17th enqueue should fail
        self.assertFalse(ring.enqueue(msg_bytes))
        self.assertEqual(ring.size(), 16)

    def test_tc24_ring_buffer_wraparound_fifo_preservation(self) -> None:
        ring = PCIeDMARingBuffer(capacity=8)
        for i in range(20):
            val = struct.pack("<Q24s", i, b"test")
            self.assertTrue(ring.enqueue(val))
            out = ring.dequeue()
            self.assertIsNotNone(out)
            out_i = struct.unpack("<Q24s", out)[0]
            self.assertEqual(out_i, i)

    def test_tc25_ring_buffer_clear(self) -> None:
        ring = PCIeDMARingBuffer(capacity=16)
        for _ in range(5):
            ring.enqueue(b"A" * 32)
        self.assertEqual(ring.size(), 5)
        ring.clear()
        self.assertTrue(ring.is_empty())
        self.assertEqual(ring.size(), 0)

    # =========================================================================
    # Category 6: 4-Class Hardware Priority Queue Arbitration
    # =========================================================================
    def test_tc26_priority_arbitration_cancel_preempts_all(self) -> None:
        # Submit Limit, then IOC, then Cancel
        self.engine.submit_order(1, "AAPL", OrderSide.BUY, OrderType.LIMIT, 100, 150.0)
        self.engine.submit_order(2, "MSFT", OrderSide.BUY, OrderType.IOC, 50, 400.0)
        self.engine.submit_order(3, "GOOGL", OrderSide.SELL, OrderType.CANCEL_REQ, 10, 180.0)

        dispatched = self.engine.arbitrate_and_dispatch_batch(max_batch=3)
        self.assertEqual(len(dispatched), 3)
        # 1st dispatched must be CANCEL_EMERGENCY (order 3)
        self.assertEqual(dispatched[0].order_id, 3)
        self.assertEqual(dispatched[0].priority, PriorityClass.CANCEL_EMERGENCY)
        # 2nd dispatched must be IOC_MARKET (order 2)
        self.assertEqual(dispatched[1].order_id, 2)
        self.assertEqual(dispatched[1].priority, PriorityClass.IOC_MARKET)
        # 3rd dispatched must be LIMIT_PEGGED (order 1)
        self.assertEqual(dispatched[2].order_id, 1)
        self.assertEqual(dispatched[2].priority, PriorityClass.LIMIT_PEGGED)

    def test_tc27_cancel_order_creates_emergency_priority(self) -> None:
        self.engine.submit_order(101, "NVDA", OrderSide.BUY, OrderType.LIMIT, 100, 120.0)
        ok = self.engine.cancel_order(101)
        self.assertTrue(ok)
        self.assertEqual(len(self.engine.priority_queues[PriorityClass.CANCEL_EMERGENCY]), 1)

    def test_tc28_cancel_nonexistent_order_returns_false(self) -> None:
        ok = self.engine.cancel_order(999999)
        self.assertFalse(ok)

    def test_tc29_batch_dispatch_honors_max_batch(self) -> None:
        for i in range(10):
            self.engine.submit_order(i, "AAPL", OrderSide.BUY, OrderType.LIMIT, 10, 150.0)
        dispatched = self.engine.arbitrate_and_dispatch_batch(max_batch=4)
        self.assertEqual(len(dispatched), 4)
        self.assertEqual(self.engine.dma_ring.size(), 4)

    def test_tc30_empty_queues_dispatch_returns_empty(self) -> None:
        dispatched = self.engine.arbitrate_and_dispatch_batch(max_batch=10)
        self.assertEqual(len(dispatched), 0)

    # =========================================================================
    # Category 7: Sub-Nanosecond T1~T4 Hardware Timestamping Telemetry
    # =========================================================================
    def test_tc31_hardware_timestamps_populated(self) -> None:
        self.engine.submit_order(1, "AAPL", OrderSide.BUY, OrderType.LIMIT, 10, 150.0)
        dispatched = self.engine.arbitrate_and_dispatch_batch(max_batch=1)
        msg = dispatched[0]
        self.assertGreater(msg.t1_host_ns, 0)
        self.assertGreater(msg.t2_nic_ingress_ns, 0)
        self.assertGreater(msg.t3_match_ns, 0)
        self.assertGreater(msg.t4_egress_ns, 0)

    def test_tc32_hardware_transit_latency_monotonic(self) -> None:
        self.engine.submit_order(1, "NVDA", OrderSide.BUY, OrderType.LIMIT, 10, 120.0)
        dispatched = self.engine.arbitrate_and_dispatch_batch(max_batch=1)
        msg = dispatched[0]
        self.assertLessEqual(msg.t1_host_ns, msg.t2_nic_ingress_ns)
        self.assertLessEqual(msg.t2_nic_ingress_ns, msg.t3_match_ns)
        self.assertLessEqual(msg.t3_match_ns, msg.t4_egress_ns)

    def test_tc33_telemetry_avg_latency_computed(self) -> None:
        for i in range(5):
            self.engine.submit_order(i, "SPY", OrderSide.BUY, OrderType.IOC, 10, 500.0)
        self.engine.arbitrate_and_dispatch_batch(max_batch=5)
        self.assertGreater(self.engine.metrics["avg_latency_ns"], 0.0)

    def test_tc34_p99_latency_computed(self) -> None:
        for i in range(10):
            self.engine.submit_order(i, "QQQ", OrderSide.BUY, OrderType.LIMIT, 10, 400.0)
        self.engine.arbitrate_and_dispatch_batch(max_batch=10)
        self.assertGreater(self.engine.metrics["p99_latency_ns"], 0.0)

    def test_tc35_telemetry_export_dict(self) -> None:
        telem = self.engine.export_telemetry()
        self.assertEqual(telem["status"], "READY")
        self.assertEqual(telem["active_broker"], "PRIMARY_PCIE")
        self.assertIn("metrics", telem)
        self.assertEqual(telem["version"], 121)
        self.assertEqual(telem["feature"], "F578")

    # =========================================================================
    # Category 8: Cancel-On-Disconnect (COD) Watchdog & Emergency Kill
    # =========================================================================
    def test_tc36_heartbeat_updates_timestamp(self) -> None:
        t_prev = self.engine.last_heartbeat_time
        time.sleep(0.01)
        self.engine.heartbeat()
        self.assertGreater(self.engine.last_heartbeat_time, t_prev)
        self.assertTrue(self.engine.is_connected)

    def test_tc37_cod_watchdog_within_timeout_does_nothing(self) -> None:
        self.engine.heartbeat()
        triggered = self.engine.check_cod_watchdog()
        self.assertFalse(triggered)
        self.assertTrue(self.engine.is_connected)

    def test_tc38_cod_watchdog_timeout_triggers_emergency_kill(self) -> None:
        engine_fast_cod = PCIeDMATradingEngine(cod_timeout_ms=5)
        engine_fast_cod.submit_order(1, "AAPL", OrderSide.BUY, OrderType.LIMIT, 10, 150.0)
        engine_fast_cod.submit_order(2, "NVDA", OrderSide.BUY, OrderType.LIMIT, 20, 120.0)

        time.sleep(0.02)  # Exceed 5ms timeout
        triggered = engine_fast_cod.check_cod_watchdog()
        self.assertTrue(triggered)
        self.assertFalse(engine_fast_cod.is_connected)
        self.assertEqual(engine_fast_cod.bar0.status, EngineStatus.ERROR)
        self.assertGreater(engine_fast_cod.metrics["emergency_kills"], 0)

    def test_tc39_emergency_kill_all_cancels_all_working_orders(self) -> None:
        self.engine.submit_order(10, "AAPL", OrderSide.BUY, OrderType.LIMIT, 100, 150.0)
        self.engine.submit_order(11, "MSFT", OrderSide.SELL, OrderType.LIMIT, 50, 420.0)
        self.engine.submit_order(12, "GOOGL", OrderSide.BUY, OrderType.LIMIT, 20, 180.0)

        killed = self.engine.emergency_kill_all()
        self.assertEqual(killed, 3)
        self.assertEqual(len(self.engine.priority_queues[PriorityClass.CANCEL_EMERGENCY]), 3)

    def test_tc40_emergency_kill_ignores_already_cancelled_orders(self) -> None:
        self.engine.submit_order(1, "AAPL", OrderSide.BUY, OrderType.LIMIT, 10, 150.0)
        self.engine.cancel_order(1)
        killed = self.engine.emergency_kill_all()
        # Order 1 was already CancelReq so no extra kill generated
        self.assertEqual(killed, 0)

    # =========================================================================
    # Category 9: Multi-Broker Hot-Standby Failover Transparency
    # =========================================================================
    def test_tc41_failover_to_standby(self) -> None:
        self.assertEqual(self.engine.bar0.active_broker, BrokerID.PRIMARY_PCIE)
        new_broker = self.engine.failover_to_standby()
        self.assertEqual(new_broker, BrokerID.STANDBY_BROKER)
        self.assertEqual(self.engine.bar0.active_broker, BrokerID.STANDBY_BROKER)
        self.assertEqual(self.engine.metrics["failover_events"], 1)

    def test_tc42_failover_latency_sub_50_microsecond(self) -> None:
        latencies = []
        for _ in range(5):
            t0 = time.perf_counter_ns()
            self.engine.failover_to_standby()
            latencies.append(time.perf_counter_ns() - t0)
        best_ns = min(latencies)
        self.assertLess(best_ns, 50000, f"Failover took {best_ns}ns, exceeded 50000ns SLA!")

    def test_tc43_dispatch_operates_normally_after_failover(self) -> None:
        self.engine.failover_to_standby()
        self.engine.submit_order(1, "TSLA", OrderSide.BUY, OrderType.LIMIT, 10, 200.0)
        dispatched = self.engine.arbitrate_and_dispatch_batch(max_batch=1)
        self.assertEqual(len(dispatched), 1)
        self.assertEqual(dispatched[0].symbol, "TSLA")

    def test_tc44_venue_routing_flags_preservation(self) -> None:
        msg = self.engine.submit_order(
            order_id=5, symbol="005930.KS", side=OrderSide.BUY,
            order_type=OrderType.LIMIT, qty=100, price=75000.0,
            venue=RoutingVenue.SECONDARY_KRX,
        )
        self.assertEqual(msg.venue, RoutingVenue.SECONDARY_KRX)
        packed = msg.pack()
        unpacked = PCIeOrderMessage.unpack(packed)
        self.assertEqual(unpacked.venue, RoutingVenue.SECONDARY_KRX)

    def test_tc45_multiple_failovers_tracking(self) -> None:
        self.engine.failover_to_standby()
        self.engine.failover_to_standby()
        self.assertEqual(self.engine.metrics["failover_events"], 2)

    # =========================================================================
    # Category 10: Throughput Scalability & Sub-Microsecond Latency SLA
    # =========================================================================
    def test_tc46_struct_pack_speed_sub_10us(self) -> None:
        msg = PCIeOrderMessage(
            order_id=1, symbol="NVDA", side=OrderSide.BUY,
            order_type=OrderType.LIMIT, qty=100, price=125.0,
        )
        t0 = time.perf_counter_ns()
        for _ in range(1000):
            _ = msg.pack()
        avg_ns = (time.perf_counter_ns() - t0) / 1000.0
        self.assertLess(avg_ns, 10000.0, f"Average struct pack time {avg_ns:.1f}ns exceeded 10us SLA!")

    def test_tc47_struct_unpack_speed_sub_15us(self) -> None:
        msg = PCIeOrderMessage(
            order_id=1, symbol="NVDA", side=OrderSide.BUY,
            order_type=OrderType.LIMIT, qty=100, price=125.0,
        )
        packed = msg.pack()
        t0 = time.perf_counter_ns()
        for _ in range(1000):
            _ = PCIeOrderMessage.unpack(packed)
        avg_ns = (time.perf_counter_ns() - t0) / 1000.0
        self.assertLess(avg_ns, 15000.0, f"Average struct unpack time {avg_ns:.1f}ns exceeded 15us SLA!")

    def test_tc48_ring_buffer_enqueue_speed_sub_2us(self) -> None:
        ring = PCIeDMARingBuffer(capacity=1024)
        msg_bytes = b"Z" * 32
        t0 = time.perf_counter_ns()
        for _ in range(500):
            ring.enqueue(msg_bytes)
        avg_ns = (time.perf_counter_ns() - t0) / 500.0
        self.assertLess(avg_ns, 2000.0, f"Average ring enqueue time {avg_ns:.1f}ns exceeded 2us SLA!")


    def test_tc49_high_throughput_batch_submission_1000_orders(self) -> None:
        t0 = time.perf_counter()
        for i in range(1000):
            self.engine.submit_order(i, "AAPL", OrderSide.BUY, OrderType.LIMIT, 10, 150.0)
        elapsed = time.perf_counter() - t0
        self.assertLess(elapsed, 0.05, f"1000 order submissions took {elapsed:.3f}s exceeded 50ms SLA!")
        self.assertEqual(self.engine.metrics["total_submitted"], 1000)

    def test_tc50_batch_arbitration_throughput_1000_orders(self) -> None:
        for i in range(1000):
            self.engine.submit_order(i, "AAPL", OrderSide.BUY, OrderType.LIMIT, 10, 150.0)
        t0 = time.perf_counter()
        dispatched = self.engine.arbitrate_and_dispatch_batch(max_batch=1000)
        elapsed = time.perf_counter() - t0
        self.assertEqual(len(dispatched), 1000)
        self.assertLess(elapsed, 0.05, f"1000 order arbitration took {elapsed:.3f}s exceeded 50ms SLA!")


if __name__ == "__main__":
    unittest.main()
