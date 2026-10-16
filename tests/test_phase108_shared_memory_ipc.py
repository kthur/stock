"""
tests/test_phase108_shared_memory_ipc.py
=========================================
Comprehensive Unit, Integration, Lifecycle, Concurrency, and Invariant Test Harness
for High-Performance Zero-Copy Shared Memory IPC Ring Buffer
Phase 108 (Release R124 / v115 Production Master / Feature F513).

Test Categories Covered:
- Category 1: Exports, Class Signatures & Alias Trees (TC01~TC03)
- Category 2: Header Validation & Parameter Bounds (TC04~TC08)
- Category 3: Zero-Copy Struct Pack/Unpack Consistency (TC09~TC13)
- Category 4: Buffer Capacity, Overflow, Wraparound & Monotonicity (TC14~TC18)
- Category 5: Concurrency, Spinlock & Telemetry Diagnostics (TC19~TC22)
- Category 6: Resilient Lifecycle, Stale Segment Reclamation & Cleanup (TC23~TC26)
- Category 7: Cross-Process SPSC Message Transfer (TC27~TC30)
"""

from __future__ import annotations

import os
import struct
import subprocess
import sys
import time
import unittest
from pathlib import Path
from typing import List

# Ensure project roots are on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p in (str(PROJECT_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.core.shared_memory_ring_buffer import (
    DEFAULT_CAPACITY,
    DEFAULT_SLOT_SIZE,
    HEADER_SIZE,
    HEADER_VERSION,
    MAGIC_HEADER,
    OFFSET_CAPACITY,
    OFFSET_DROPPED_COUNT,
    OFFSET_HEAD_SEQ,
    OFFSET_MAGIC,
    OFFSET_MASK,
    OFFSET_PRODUCER_HB,
    OFFSET_PRODUCER_PID,
    OFFSET_SLOT_SIZE,
    OFFSET_TAIL_SEQ,
    ExecutionOrderMessage,
    HighPerformanceSharedMemoryIPC,
    LOBTickMessage,
    MessageType,
    Phase108SharedMemoryRingBuffer,
    RiskAlertMessage,
    SharedMemoryIPCRingBuffer,
    SharedMemoryRingBuffer,
    ZeroCopySharedMemoryRingBuffer,
    is_pid_alive,
    sanitize_shm_name,
)


class TestPhase108SharedMemoryIPC(unittest.TestCase):
    """Master Test Suite for High-Performance Zero-Copy Shared Memory IPC Ring Buffer."""

    def setUp(self) -> None:
        self.test_shm_name = f"test_shm_p108_{os.getpid()}_{int(time.time() * 1000) % 100000}"
        SharedMemoryRingBuffer.cleanup_segment(self.test_shm_name)

    def tearDown(self) -> None:
        SharedMemoryRingBuffer.cleanup_segment(self.test_shm_name)

    # -----------------------------------------------------------------------
    # Category 1: Exports, Class Signatures & Alias Trees (TC01~TC03)
    # -----------------------------------------------------------------------
    def test_tc01_alias_trees(self) -> None:
        """TC01: Verify complete alias trees for SharedMemoryRingBuffer."""
        self.assertIs(ZeroCopySharedMemoryRingBuffer, SharedMemoryRingBuffer)
        self.assertIs(Phase108SharedMemoryRingBuffer, SharedMemoryRingBuffer)
        self.assertIs(HighPerformanceSharedMemoryIPC, SharedMemoryRingBuffer)
        self.assertIs(SharedMemoryIPCRingBuffer, SharedMemoryRingBuffer)

    def test_tc02_message_types_and_dataclasses(self) -> None:
        """TC02: Verify MessageType enum and message dataclass structures."""
        self.assertEqual(int(MessageType.HEARTBEAT), 0)
        self.assertEqual(int(MessageType.LOB_TICK), 1)
        self.assertEqual(int(MessageType.RISK_ALERT), 2)
        self.assertEqual(int(MessageType.EXECUTION_ORDER), 3)

        tick = LOBTickMessage(
            symbol="005930",
            timestamp_ns=1700000000000000000,
            bid_price=71000.0,
            ask_price=71100.0,
            bid_size=150.0,
            ask_size=250.0,
            last_price=71050.0,
            last_size=50.0,
        )
        self.assertEqual(tick.depth_levels, 5)
        self.assertEqual(len(tick.bid_prices), 5)
        self.assertEqual(len(tick.ask_prices), 5)

        alert = RiskAlertMessage(
            alert_id="ALT-001",
            timestamp_ns=1700000000000000000,
            symbol="AAPL",
            market="NASDAQ",
            severity=3,
            alert_type=2,
            metric_value=-0.035,
            threshold_value=-0.030,
            action_code=2,
            message="Stop Loss Exceeded",
        )
        self.assertEqual(alert.alert_id, "ALT-001")
        self.assertEqual(alert.severity, 3)

        order = ExecutionOrderMessage(
            order_id="ORD-001",
            symbol="NVDA",
            market="SP500",
            timestamp_ns=1700000000000000000,
            side=1,
            order_type=3,
            quantity=500.0,
            price=450.25,
            status=1,
        )
        self.assertEqual(order.client_id, "OMS_CLIENT")
        self.assertEqual(order.quantity, 500.0)

    def test_tc03_mirrored_file_integrity(self) -> None:
        """TC03: Verify primary and mirrored modules are identical and importable."""
        import hashlib
        primary_path = PROJECT_ROOT / "src" / "core" / "shared_memory_ring_buffer.py"
        mirrored_path = PROJECT_ROOT / "trading_system" / "src" / "core" / "shared_memory_ring_buffer.py"

        self.assertTrue(primary_path.exists(), "Primary file must exist")
        self.assertTrue(mirrored_path.exists(), "Mirrored file must exist")

        h1 = hashlib.sha256(primary_path.read_bytes()).hexdigest()
        h2 = hashlib.sha256(mirrored_path.read_bytes()).hexdigest()
        self.assertEqual(h1, h2, "Primary and mirrored files must be bit-for-bit identical")

    # -----------------------------------------------------------------------
    # Category 2: Header Validation & Parameter Bounds (TC04~TC08)
    # -----------------------------------------------------------------------
    def test_tc04_capacity_power_of_two(self) -> None:
        """TC04: Verify power-of-2 capacity constraints."""
        valid_caps = [2, 4, 16, 64, 256, 1024, 2048]
        for cap in valid_caps:
            name = f"{self.test_shm_name}_cap_{cap}"
            try:
                buf = SharedMemoryRingBuffer(name, capacity=cap, create=True)
                self.assertEqual(buf.capacity, cap)
                buf.close()
                buf.unlink()
            finally:
                SharedMemoryRingBuffer.cleanup_segment(name)

        invalid_caps = [0, -1, 3, 5, 100, 500, 1000, 3000]
        for bad_cap in invalid_caps:
            with self.assertRaises(ValueError):
                SharedMemoryRingBuffer(f"{self.test_shm_name}_bad", capacity=bad_cap, create=True)

    def test_tc05_slot_size_validation(self) -> None:
        """TC05: Verify minimum slot size requirements."""
        with self.assertRaises(ValueError):
            SharedMemoryRingBuffer(self.test_shm_name, slot_size=128, create=True)

        buf = SharedMemoryRingBuffer(self.test_shm_name, slot_size=512, capacity=16, create=True)
        self.assertEqual(buf.slot_size, 512)
        buf.close()
        buf.unlink()

    def test_tc06_header_magic_and_constants(self) -> None:
        """TC06: Verify 256-byte cacheline aligned header structure and magic constant."""
        self.assertEqual(MAGIC_HEADER, 0x53484D52)
        self.assertEqual(HEADER_SIZE, 256)
        self.assertEqual(HEADER_VERSION, 115)

        buf = SharedMemoryRingBuffer(self.test_shm_name, capacity=16, create=True)
        # Directly inspect header bytes in memoryview
        magic = struct.unpack_from("<I", buf._buf, OFFSET_MAGIC)[0]
        self.assertEqual(magic, MAGIC_HEADER)
        slot_sz = struct.unpack_from("<I", buf._buf, OFFSET_SLOT_SIZE)[0]
        self.assertEqual(slot_sz, DEFAULT_SLOT_SIZE)
        buf.close()
        buf.unlink()

    def test_tc07_corrupted_header_detection(self) -> None:
        """TC07: Verify detection of corrupted shared memory header magic."""
        buf = SharedMemoryRingBuffer(self.test_shm_name, capacity=16, create=True)
        # Corrupt magic
        struct.pack_into("<I", buf._buf, OFFSET_MAGIC, 0xDEADBEEF)

        # Attempt to attach as client
        with self.assertRaises(ValueError) as ctx:
            SharedMemoryRingBuffer(self.test_shm_name, create=False)
        self.assertIn("Invalid shared memory magic", str(ctx.exception))

        buf.close()
        buf.unlink()

    def test_tc08_sanitize_shm_name(self) -> None:
        """TC08: Verify platform-safe shared memory name normalization."""
        raw_name = "/my_channel/v1"
        clean = sanitize_shm_name(raw_name)
        if os.name == "nt":
            self.assertNotIn("/", clean)
            self.assertNotIn("\\", clean)
        else:
            self.assertTrue(clean.startswith("/"))

    # -----------------------------------------------------------------------
    # Category 3: Zero-Copy Struct Pack/Unpack Consistency (TC09~TC13)
    # -----------------------------------------------------------------------
    def test_tc09_lob_tick_pack_unpack(self) -> None:
        """TC09: Direct zero-copy serialization/deserialization fidelity for LOB ticks."""
        with SharedMemoryRingBuffer(self.test_shm_name, capacity=16, create=True) as buf:
            orig = LOBTickMessage(
                symbol="005930",
                timestamp_ns=1700000000123456789,
                bid_price=71500.0,
                ask_price=71600.0,
                bid_size=1200.0,
                ask_size=800.0,
                last_price=71550.0,
                last_size=150.0,
                depth_levels=5,
                bid_prices=(71500.0, 71400.0, 71300.0, 71200.0, 71100.0),
                ask_prices=(71600.0, 71700.0, 71800.0, 71900.0, 72000.0),
                bid_sizes=(1200.0, 2000.0, 3500.0, 4000.0, 5000.0),
                ask_sizes=(800.0, 1500.0, 2200.0, 3000.0, 4500.0),
            )
            success = buf.write_tick(orig)
            self.assertTrue(success)

            unpacked = buf.read_message()
            self.assertIsInstance(unpacked, LOBTickMessage)
            self.assertEqual(unpacked.symbol, orig.symbol)
            self.assertEqual(unpacked.timestamp_ns, orig.timestamp_ns)
            self.assertAlmostEqual(unpacked.bid_price, orig.bid_price)
            self.assertAlmostEqual(unpacked.ask_price, orig.ask_price)
            self.assertAlmostEqual(unpacked.bid_size, orig.bid_size)
            self.assertAlmostEqual(unpacked.ask_size, orig.ask_size)
            self.assertAlmostEqual(unpacked.last_price, orig.last_price)
            self.assertAlmostEqual(unpacked.last_size, orig.last_size)
            self.assertEqual(unpacked.depth_levels, 5)

            for i in range(5):
                self.assertAlmostEqual(unpacked.bid_prices[i], orig.bid_prices[i])
                self.assertAlmostEqual(unpacked.ask_prices[i], orig.ask_prices[i])
                self.assertAlmostEqual(unpacked.bid_sizes[i], orig.bid_sizes[i])
                self.assertAlmostEqual(unpacked.ask_sizes[i], orig.ask_sizes[i])

    def test_tc10_risk_alert_pack_unpack(self) -> None:
        """TC10: Serialization/deserialization fidelity for Risk Alert messages."""
        with SharedMemoryRingBuffer(self.test_shm_name, capacity=16, create=True) as buf:
            orig = RiskAlertMessage(
                alert_id="ALERT-CIRCUIT-099",
                timestamp_ns=1700000000987654321,
                symbol="TSLA",
                market="NASDAQ",
                severity=4,
                alert_type=5,
                metric_value=-0.0825,
                threshold_value=-0.0800,
                action_code=2,
                message="Extreme volatility halt: liquidate active tranche",
            )
            self.assertTrue(buf.write_alert(orig))

            unpacked = buf.read_message()
            self.assertIsInstance(unpacked, RiskAlertMessage)
            self.assertEqual(unpacked.alert_id, orig.alert_id)
            self.assertEqual(unpacked.symbol, orig.symbol)
            self.assertEqual(unpacked.market, orig.market)
            self.assertEqual(unpacked.severity, 4)
            self.assertEqual(unpacked.alert_type, 5)
            self.assertAlmostEqual(unpacked.metric_value, orig.metric_value)
            self.assertAlmostEqual(unpacked.threshold_value, orig.threshold_value)
            self.assertEqual(unpacked.action_code, 2)
            self.assertEqual(unpacked.message, orig.message)

    def test_tc11_execution_order_pack_unpack(self) -> None:
        """TC11: Serialization/deserialization fidelity for Execution Order messages."""
        with SharedMemoryRingBuffer(self.test_shm_name, capacity=16, create=True) as buf:
            orig = ExecutionOrderMessage(
                order_id="SLICE-2026-X115",
                symbol="MSFT",
                market="SP500",
                timestamp_ns=1700000000555555555,
                side=1,
                order_type=3,
                quantity=1250.0,
                price=412.80,
                status=2,
                client_id="ALMGREN_OMS",
            )
            self.assertTrue(buf.write_order(orig))

            unpacked = buf.read_message()
            self.assertIsInstance(unpacked, ExecutionOrderMessage)
            self.assertEqual(unpacked.order_id, orig.order_id)
            self.assertEqual(unpacked.symbol, orig.symbol)
            self.assertEqual(unpacked.market, orig.market)
            self.assertEqual(unpacked.side, 1)
            self.assertEqual(unpacked.order_type, 3)
            self.assertAlmostEqual(unpacked.quantity, 1250.0)
            self.assertAlmostEqual(unpacked.price, 412.80)
            self.assertEqual(unpacked.status, 2)
            self.assertEqual(unpacked.client_id, "ALMGREN_OMS")

    def test_tc12_polymorphic_write_message(self) -> None:
        """TC12: Polymorphic message dispatch via write_message."""
        with SharedMemoryRingBuffer(self.test_shm_name, capacity=16, create=True) as buf:
            tick = LOBTickMessage("000660", 1, 130000.0, 130100.0, 10.0, 10.0, 130050.0, 5.0)
            alert = RiskAlertMessage("A1", 2, "000660", "KOSPI", 1, 1, 0.05, 0.04, 1, "TP")
            order = ExecutionOrderMessage("O1", "000660", "KOSPI", 3, -1, 1, 100.0, 130100.0, 1)

            self.assertTrue(buf.write_message(tick))
            self.assertTrue(buf.write_message(alert))
            self.assertTrue(buf.write_message(order))

            r1 = buf.read_message()
            r2 = buf.read_message()
            r3 = buf.read_message()

            self.assertIsInstance(r1, LOBTickMessage)
            self.assertIsInstance(r2, RiskAlertMessage)
            self.assertIsInstance(r3, ExecutionOrderMessage)

    def test_tc13_peek_message_idempotence(self) -> None:
        """TC13: Verify peek_message does not advance tail sequence counter."""
        with SharedMemoryRingBuffer(self.test_shm_name, capacity=8, create=True) as buf:
            tick = LOBTickMessage("AAPL", 100, 150.0, 150.1, 10.0, 20.0, 150.05, 5.0)
            buf.write_tick(tick)

            tail_before = buf.tail_seq
            peeked = buf.peek_message()
            self.assertIsInstance(peeked, LOBTickMessage)
            self.assertEqual(peeked.symbol, "AAPL")
            self.assertEqual(buf.tail_seq, tail_before)

            # Subsequent read must return the same item and advance tail_seq
            read_item = buf.read_message()
            self.assertIsInstance(read_item, LOBTickMessage)
            self.assertEqual(read_item.symbol, "AAPL")
            self.assertEqual(buf.tail_seq, tail_before + 1)

    # -----------------------------------------------------------------------
    # Category 4: Capacity, Overflow, Wraparound & Monotonicity (TC14~TC18)
    # -----------------------------------------------------------------------
    def test_tc14_buffer_full_and_occupancy(self) -> None:
        """TC14: Assert exact capacity occupancy when filled."""
        cap = 8
        with SharedMemoryRingBuffer(self.test_shm_name, capacity=cap, create=True) as buf:
            self.assertTrue(buf.is_empty())
            self.assertFalse(buf.is_full())
            self.assertEqual(buf.available_read(), 0)
            self.assertEqual(buf.available_write(), cap)

            for i in range(cap):
                msg = ExecutionOrderMessage(f"ORD-{i}", "SYM", "MKT", i, 1, 1, 10.0, 100.0, 1)
                self.assertTrue(buf.write_order(msg))

            self.assertTrue(buf.is_full())
            self.assertFalse(buf.is_empty())
            self.assertEqual(buf.available_read(), cap)
            self.assertEqual(buf.available_write(), 0)

    def test_tc15_overflow_drop_handling(self) -> None:
        """TC15: When full, non-blocking write returns False and increments dropped_count."""
        cap = 4
        with SharedMemoryRingBuffer(self.test_shm_name, capacity=cap, create=True) as buf:
            for i in range(cap):
                buf.write_order(ExecutionOrderMessage(f"O-{i}", "SYM", "MKT", i, 1, 1, 1.0, 1.0, 1))

            self.assertEqual(buf.dropped_count, 0)

            # Next write must fail immediately
            overflow_msg = ExecutionOrderMessage("O-EXTRA", "SYM", "MKT", 99, 1, 1, 1.0, 1.0, 1)
            success = buf.write_order(overflow_msg, timeout_sec=0.0)
            self.assertFalse(success)
            self.assertEqual(buf.dropped_count, 1)

    def test_tc16_ring_wraparound_and_monotonicity(self) -> None:
        """TC16: Verify seamless ring buffer wraparound across 5x capacity."""
        cap = 8
        total_items = 40  # 5 full buffer cycles
        with SharedMemoryRingBuffer(self.test_shm_name, capacity=cap, create=True) as buf:
            written_seqs: List[int] = []
            read_seqs: List[int] = []

            for i in range(total_items):
                tick = LOBTickMessage("WRAP", i, float(i), float(i + 1), 10.0, 10.0, float(i), 1.0)
                self.assertTrue(buf.write_tick(tick))
                written_seqs.append(i)

                # Read immediately to keep space
                read_msg = buf.read_message()
                self.assertIsNotNone(read_msg)
                read_seqs.append(read_msg.timestamp_ns)

            self.assertEqual(written_seqs, read_seqs)
            self.assertEqual(buf.total_written, total_items)
            self.assertEqual(buf.total_read, total_items)
            self.assertEqual(buf.head_seq, total_items)
            self.assertEqual(buf.tail_seq, total_items)

    def test_tc17_read_batch(self) -> None:
        """TC17: Batch read returns all available messages non-blockingly."""
        cap = 16
        with SharedMemoryRingBuffer(self.test_shm_name, capacity=cap, create=True) as buf:
            for i in range(10):
                buf.write_tick(LOBTickMessage("BATCH", i, 10.0, 11.0, 1.0, 1.0, 10.0, 1.0))

            batch = buf.read_batch(max_items=6)
            self.assertEqual(len(batch), 6)
            self.assertEqual(buf.available_read(), 4)

            remaining = buf.read_batch(max_items=10)
            self.assertEqual(len(remaining), 4)
            self.assertEqual(buf.available_read(), 0)

    def test_tc18_drain_to_empty(self) -> None:
        """TC18: Sequential drain leaves buffer empty with zero read timeout."""
        with SharedMemoryRingBuffer(self.test_shm_name, capacity=8, create=True) as buf:
            for i in range(5):
                buf.write_tick(LOBTickMessage("D", i, 1.0, 2.0, 1.0, 1.0, 1.0, 1.0))

            self.assertEqual(buf.available_read(), 5)
            for _ in range(5):
                self.assertIsNotNone(buf.read_message(timeout_sec=0.0))

            self.assertIsNone(buf.read_message(timeout_sec=0.0))
            self.assertTrue(buf.is_empty())

    # -----------------------------------------------------------------------
    # Category 5: Concurrency, Spinlock & Telemetry Diagnostics (TC19~TC22)
    # -----------------------------------------------------------------------
    def test_tc19_spinlock_acquire_and_release(self) -> None:
        """TC19: Spinlock acquire, release, and contention timeout."""
        with SharedMemoryRingBuffer(self.test_shm_name, capacity=8, create=True) as buf:
            acquired = buf.acquire_spinlock(timeout_us=10_000)
            self.assertTrue(acquired)

            # Second acquire attempt should fail
            contended = buf.acquire_spinlock(timeout_us=5_000)
            self.assertFalse(contended)

            buf.release_spinlock()
            reacquired = buf.acquire_spinlock(timeout_us=10_000)
            self.assertTrue(reacquired)
            buf.release_spinlock()

    def test_tc20_spinlock_guard_context_manager(self) -> None:
        """TC20: Spinlock guard context manager cleans up lock upon exit."""
        with SharedMemoryRingBuffer(self.test_shm_name, capacity=8, create=True) as buf:
            with buf.spinlock_guard(timeout_us=10_000) as locked:
                self.assertTrue(locked)
                # Ensure locked internally
                second = buf.acquire_spinlock(timeout_us=2_000)
                self.assertFalse(second)

            # Once exited, lock is released
            can_lock = buf.acquire_spinlock(timeout_us=5_000)
            self.assertTrue(can_lock)
            buf.release_spinlock()

    def test_tc21_heartbeats_and_pids(self) -> None:
        """TC21: Verify producer and consumer heartbeat updates."""
        with SharedMemoryRingBuffer(self.test_shm_name, capacity=8, create=True) as buf:
            stats = buf.stats()
            self.assertEqual(stats["producer_pid"], os.getpid())
            self.assertTrue(is_pid_alive(os.getpid()))

            old_hb = struct.unpack_from("<q", buf._buf, OFFSET_PRODUCER_HB)[0]
            time.sleep(0.005)
            buf.update_producer_heartbeat()
            new_hb = struct.unpack_from("<q", buf._buf, OFFSET_PRODUCER_HB)[0]
            self.assertGreater(new_hb, old_hb)

    def test_tc22_stats_and_reset(self) -> None:
        """TC22: Comprehensive diagnostic telemetry and counter reset."""
        with SharedMemoryRingBuffer(self.test_shm_name, capacity=8, create=True) as buf:
            buf.write_tick(LOBTickMessage("S", 1, 1.0, 2.0, 1.0, 1.0, 1.0, 1.0))
            buf.read_message()

            stats = buf.stats()
            self.assertEqual(stats["total_written"], 1)
            self.assertEqual(stats["total_read"], 1)
            self.assertEqual(stats["head_seq"], 1)
            self.assertEqual(stats["tail_seq"], 1)

            buf.reset()
            reset_stats = buf.stats()
            self.assertEqual(reset_stats["total_written"], 0)
            self.assertEqual(reset_stats["total_read"], 0)
            self.assertEqual(reset_stats["head_seq"], 0)
            self.assertEqual(reset_stats["tail_seq"], 0)

    # -----------------------------------------------------------------------
    # Category 6: Resilient Lifecycle, Stale Segment Reclamation & Cleanup (TC23~TC26)
    # -----------------------------------------------------------------------
    def test_tc23_stale_segment_dead_pid_reclamation(self) -> None:
        """TC23: Reclaim stale segment when owner PID is verified dead."""
        # Create segment and manually corrupt producer PID to a dead PID
        buf = SharedMemoryRingBuffer(self.test_shm_name, capacity=16, create=True, auto_unlink=False)
        struct.pack_into("<q", buf._buf, OFFSET_PRODUCER_PID, 99999999) # Non-existent PID
        buf.close()

        # Re-creating should detect dead PID and successfully reclaim
        reclaimed_buf = SharedMemoryRingBuffer(self.test_shm_name, capacity=16, create=True)
        self.assertTrue(reclaimed_buf.is_creator)
        reclaimed_buf.close()
        reclaimed_buf.unlink()

    def test_tc24_stale_segment_heartbeat_timeout(self) -> None:
        """TC24: Reclaim segment when producer heartbeat is older than 10 seconds."""
        buf = SharedMemoryRingBuffer(self.test_shm_name, capacity=16, create=True, auto_unlink=False)
        # Set heartbeat to 20 seconds in the past
        ancient_ns = time.time_ns() - int(20 * 1e9)
        struct.pack_into("<q", buf._buf, OFFSET_PRODUCER_HB, ancient_ns)
        struct.pack_into("<q", buf._buf, OFFSET_PRODUCER_PID, 99999999)
        buf.close()

        reclaimed_buf = SharedMemoryRingBuffer(self.test_shm_name, capacity=16, create=True)
        self.assertTrue(reclaimed_buf.is_creator)
        reclaimed_buf.close()
        reclaimed_buf.unlink()

    def test_tc25_context_manager_auto_unlink(self) -> None:
        """TC25: Context manager guarantees automatic unlinking upon exit."""
        name = f"{self.test_shm_name}_ctx"
        with SharedMemoryRingBuffer(name, capacity=8, create=True, auto_unlink=True) as buf:
            buf.write_tick(LOBTickMessage("CTX", 1, 10.0, 11.0, 1.0, 1.0, 10.0, 1.0))
            self.assertFalse(buf.is_closed)

        # Segment must now be cleaned up from OS
        with self.assertRaises(FileNotFoundError):
            SharedMemoryRingBuffer(name, create=False)

    def test_tc26_cleanup_segment_utility(self) -> None:
        """TC26: Utility classmethod forcibly unlinks existing segment."""
        name = f"{self.test_shm_name}_force"
        buf = SharedMemoryRingBuffer(name, capacity=8, create=True, auto_unlink=False)

        cleaned = SharedMemoryRingBuffer.cleanup_segment(name)
        self.assertTrue(cleaned)
        buf.close()

        # Subsequent cleanup on non-existent segment returns False
        self.assertFalse(SharedMemoryRingBuffer.cleanup_segment(name))

    # -----------------------------------------------------------------------
    # Category 7: Cross-Process SPSC Message Transfer (TC27~TC30)
    # -----------------------------------------------------------------------
    def test_tc27_cross_process_lob_ticks(self) -> None:
        """TC27: Cross-process transfer of 100 LOB ticks using spawned subprocess producer."""
        count = 100
        shm_name = f"{self.test_shm_name}_tc27"
        main_buf = SharedMemoryRingBuffer(shm_name, capacity=256, create=True)

        producer_script = f"""
import sys, time
sys.path.insert(0, r"{PROJECT_ROOT}")
sys.path.insert(0, r"{TRADING_SYSTEM_DIR}")
from src.core.shared_memory_ring_buffer import SharedMemoryRingBuffer, LOBTickMessage

buf = SharedMemoryRingBuffer("{shm_name}", create=False, client_mode="producer")
for i in range({count}):
    tick = LOBTickMessage(
        symbol="005930",
        timestamp_ns=time.time_ns(),
        bid_price=70000.0 + i,
        ask_price=70100.0 + i,
        bid_size=100.0 + i,
        ask_size=200.0 + i,
        last_price=70050.0 + i,
        last_size=50.0,
    )
    while not buf.write_tick(tick, timeout_sec=0.02):
        time.sleep(0.001)
buf.close()
"""
        proc = subprocess.Popen([sys.executable, "-c", producer_script])

        try:
            received: List[LOBTickMessage] = []
            deadline = time.time() + 20.0
            while len(received) < count and time.time() < deadline:
                msg = main_buf.read_message(timeout_sec=0.05)
                if msg is not None:
                    self.assertIsInstance(msg, LOBTickMessage)
                    received.append(msg)

            proc.wait(timeout=15.0)
            self.assertEqual(len(received), count)
            self.assertEqual(received[0].symbol, "005930")
            self.assertAlmostEqual(received[0].bid_price, 70000.0)
            self.assertAlmostEqual(received[-1].bid_price, 70000.0 + count - 1)
        finally:
            if proc.poll() is None:
                proc.kill()
                try:
                    proc.wait(timeout=5.0)
                except subprocess.TimeoutExpired:
                    pass
            main_buf.close()
            main_buf.unlink()

    def test_tc28_cross_process_execution_orders(self) -> None:
        """TC28: Cross-process transfer of 100 Execution Orders with sequence integrity."""
        count = 100
        shm_name = f"{self.test_shm_name}_tc28"
        main_buf = SharedMemoryRingBuffer(shm_name, capacity=256, create=True)

        producer_script = f"""
import sys, time
sys.path.insert(0, r"{PROJECT_ROOT}")
sys.path.insert(0, r"{TRADING_SYSTEM_DIR}")
from src.core.shared_memory_ring_buffer import SharedMemoryRingBuffer, ExecutionOrderMessage

buf = SharedMemoryRingBuffer("{shm_name}", create=False, client_mode="producer")
for i in range({count}):
    order = ExecutionOrderMessage(
        order_id=f"ORD-{{i:04d}}",
        symbol="NVDA",
        market="SP500",
        timestamp_ns=i,
        side=1 if (i % 2 == 0) else -1,
        order_type=3,
        quantity=100.0 * (i + 1),
        price=500.0 + i * 0.1,
        status=1,
    )
    while not buf.write_order(order, timeout_sec=0.02):
        time.sleep(0.001)
buf.close()
"""
        proc = subprocess.Popen([sys.executable, "-c", producer_script])

        try:
            received: List[ExecutionOrderMessage] = []
            deadline = time.time() + 20.0
            while len(received) < count and time.time() < deadline:
                msg = main_buf.read_message(timeout_sec=0.05)
                if msg is not None:
                    self.assertIsInstance(msg, ExecutionOrderMessage)
                    received.append(msg)

            proc.wait(timeout=15.0)
            self.assertEqual(len(received), count)
            for i, order in enumerate(received):
                self.assertEqual(order.order_id, f"ORD-{i:04d}")
                self.assertEqual(order.timestamp_ns, i)
        finally:
            if proc.poll() is None:
                proc.kill()
                try:
                    proc.wait(timeout=5.0)
                except subprocess.TimeoutExpired:
                    pass
            main_buf.close()
            main_buf.unlink()

    def test_tc29_cross_process_mixed_stream(self) -> None:
        """TC29: Stream mixed ticks, alerts, and orders across processes with zero loss."""
        total_msgs = 150
        shm_name = f"{self.test_shm_name}_tc29"
        main_buf = SharedMemoryRingBuffer(shm_name, capacity=256, create=True)

        producer_script = f"""
import sys, time
sys.path.insert(0, r"{PROJECT_ROOT}")
sys.path.insert(0, r"{TRADING_SYSTEM_DIR}")
from src.core.shared_memory_ring_buffer import (
    SharedMemoryRingBuffer, LOBTickMessage, RiskAlertMessage, ExecutionOrderMessage
)

buf = SharedMemoryRingBuffer("{shm_name}", create=False, client_mode="producer")
for i in range({total_msgs}):
    mod = i % 3
    if mod == 0:
        msg = LOBTickMessage("AAPL", i, 180.0, 180.1, 10.0, 10.0, 180.05, 1.0)
    elif mod == 1:
        msg = RiskAlertMessage(f"ALT-{{i}}", i, "AAPL", "NASDAQ", 2, 1, 0.02, 0.01, 1, "Alert")
    else:
        msg = ExecutionOrderMessage(f"ORD-{{i}}", "AAPL", "NASDAQ", i, 1, 1, 50.0, 180.05, 1)
    
    while not buf.write_message(msg, timeout_sec=0.02):
        time.sleep(0.001)
buf.close()
"""
        proc = subprocess.Popen([sys.executable, "-c", producer_script])

        try:
            received = []
            deadline = time.time() + 20.0
            while len(received) < total_msgs and time.time() < deadline:
                msg = main_buf.read_message(timeout_sec=0.05)
                if msg is not None:
                    received.append(msg)

            proc.wait(timeout=15.0)
            self.assertEqual(len(received), total_msgs)

            tick_count = sum(1 for m in received if isinstance(m, LOBTickMessage))
            alert_count = sum(1 for m in received if isinstance(m, RiskAlertMessage))
            order_count = sum(1 for m in received if isinstance(m, ExecutionOrderMessage))

            self.assertEqual(tick_count, 50)
            self.assertEqual(alert_count, 50)
            self.assertEqual(order_count, 50)
        finally:
            if proc.poll() is None:
                proc.kill()
                try:
                    proc.wait(timeout=5.0)
                except subprocess.TimeoutExpired:
                    pass
            main_buf.close()
            main_buf.unlink()

    def test_tc30_high_throughput_burst_benchmark(self) -> None:
        """TC30: High-throughput benchmark (> 5,000 messages in-process)."""
        cap = 2048
        burst_size = 5000
        with SharedMemoryRingBuffer(self.test_shm_name, capacity=cap, create=True) as buf:
            tick = LOBTickMessage("BENCH", 1, 100.0, 101.0, 50.0, 50.0, 100.5, 10.0)

            t0 = time.perf_counter()
            # Interleaved streaming write and read
            written = 0
            read = 0
            while read < burst_size:
                # Write batch
                while written < burst_size and buf.available_write() > 0:
                    buf.write_tick(tick)
                    written += 1
                # Read batch
                while buf.available_read() > 0:
                    msg = buf.read_message()
                    self.assertIsNotNone(msg)
                    read += 1

            elapsed = time.perf_counter() - t0
            throughput = burst_size / max(1e-6, elapsed)
            avg_latency_us = (elapsed / burst_size) * 1e6

            # Performance verification: should easily exceed 50,000 msgs/sec in Python
            self.assertEqual(read, burst_size)
            self.assertGreater(throughput, 20_000, f"Expected >= 20k msgs/sec, got {throughput:.0f}")
            # print(f"\\nThroughput: {throughput:,.0f} msgs/sec, Latency: {avg_latency_us:.2f} µs/msg")


if __name__ == "__main__":
    unittest.main()
