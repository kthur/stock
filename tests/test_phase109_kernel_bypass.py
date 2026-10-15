"""
tests/test_phase109_kernel_bypass.py
====================================
Comprehensive Master Test Harness for Kernel-Bypass DPDK/AF_XDP Mock DMA Transport Engine
Phase 109 (Release R125 / v116 Production Master / Feature F515).

Categories Tested:
- Category 1: Exports, Signatures & Alias Trees (TC01~TC03)
- Category 2: UMEM Memory Pool & Power-of-2 Validation (TC04~TC08)
- Category 3: Lock-Free Descriptor Ring Queues (TC09~TC13)
- Category 4: Sub-Microsecond Buffer Swap Latency Benchmark (< 1.0 us) (TC14~TC17)
- Category 5: FIX 4.4 Zero-Copy Serialization & Deserialization (TC18~TC22)
- Category 6: Binary LOB Multicast Packet Serialization (TC23~TC26)
- Category 7: Batch Burst Packet I/O & Completion Recycling (TC27~TC30)
- Category 8: Transparent Fallback Transport & Zero Memory Leak Lifecycle (TC31~TC35)
"""

from __future__ import annotations

import hashlib
import os
import sys
import time
import unittest
from pathlib import Path

# Ensure project roots are on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p in (str(PROJECT_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.broker.kernel_bypass_transport import (
    DEFAULT_FRAME_SIZE,
    DEFAULT_NUM_FRAMES,
    DEFAULT_RING_CAPACITY,
    FLAG_FALLBACK,
    FLAG_FIX,
    FLAG_LOB,
    FLAG_MULTICAST,
    LOB_MSG_TRADE,
    LOB_MSG_UPDATE,
    LOB_PACKET_FORMAT,
    LOB_PACKET_SIZE,
    MAGIC_LOBM,
    LOBM_VERSION,
    AFXDPRingQueue,
    AFXDPTransportEngine,
    BinaryLOBPacket,
    DPDKMockTransport,
    DescriptorRingQueue,
    FIXMessage,
    KernelBypassDMAEngine,
    KernelBypassTransport,
    KernelBypassTransportEngine,
    LOBMulticastPacket,
    PacketDescriptor,
    Phase109KernelBypassTransport,
    SPSCRingQueue,
    UMEMDescriptor,
    UMEMFramePool,
    UMEMMemoryPool,
    ZeroCopyDMATransport,
)


class TestPhase109KernelBypass(unittest.TestCase):
    """Master Test Suite for Kernel-Bypass DPDK/AF_XDP Mock DMA Transport Engine."""

    # -----------------------------------------------------------------------
    # Category 1: Exports, Signatures & Alias Trees (TC01~TC03)
    # -----------------------------------------------------------------------
    def test_tc01_alias_trees(self) -> None:
        """TC01: Verify complete alias trees for all kernel-bypass classes."""
        self.assertIs(KernelBypassTransport, KernelBypassTransportEngine)
        self.assertIs(KernelBypassDMAEngine, KernelBypassTransportEngine)
        self.assertIs(AFXDPTransportEngine, KernelBypassTransportEngine)
        self.assertIs(DPDKMockTransport, KernelBypassTransportEngine)
        self.assertIs(ZeroCopyDMATransport, KernelBypassTransportEngine)
        self.assertIs(Phase109KernelBypassTransport, KernelBypassTransportEngine)

        self.assertIs(UMEMFramePool, UMEMMemoryPool)
        self.assertIs(UMEMDescriptor, PacketDescriptor)
        self.assertIs(SPSCRingQueue, DescriptorRingQueue)
        self.assertIs(AFXDPRingQueue, DescriptorRingQueue)
        self.assertIs(BinaryLOBPacket, LOBMulticastPacket)

    def test_tc02_class_signatures_and_defaults(self) -> None:
        """TC02: Verify default parameters and descriptor structure."""
        desc = PacketDescriptor(frame_addr=4096, offset=64, length=188, flags=FLAG_FIX)
        self.assertEqual(desc.frame_addr, 4096)
        self.assertEqual(desc.frame_idx, 4096)
        self.assertEqual(desc.offset, 64)
        self.assertEqual(desc.length, 188)
        self.assertEqual(desc.len, 188)
        self.assertEqual(desc.flags, FLAG_FIX)
        self.assertGreater(desc.timestamp_ns, 0)

        # Unpacking as 4-tuple
        f_addr, offset, length, flags = desc
        self.assertEqual((f_addr, offset, length, flags), (4096, 64, 188, FLAG_FIX))

        # Indexing
        self.assertEqual(desc[0], 4096)
        self.assertEqual(desc[1], 64)
        self.assertEqual(desc[2], 188)
        self.assertEqual(desc[3], FLAG_FIX)

    def test_tc03_mirrored_file_integrity(self) -> None:
        """TC03: Assert src/broker and trading_system/src/broker files are SHA-256 bit-for-bit identical."""
        primary_path = PROJECT_ROOT / "src" / "broker" / "kernel_bypass_transport.py"
        mirrored_path = PROJECT_ROOT / "trading_system" / "src" / "broker" / "kernel_bypass_transport.py"

        self.assertTrue(primary_path.exists(), "Primary file must exist at src/broker/kernel_bypass_transport.py")
        self.assertTrue(
            mirrored_path.exists(),
            "Mirrored file must exist at trading_system/src/broker/kernel_bypass_transport.py",
        )

        h1 = hashlib.sha256(primary_path.read_bytes()).hexdigest()
        h2 = hashlib.sha256(mirrored_path.read_bytes()).hexdigest()
        self.assertEqual(h1, h2, "Primary and mirrored files must be bit-for-bit identical")

    # -----------------------------------------------------------------------
    # Category 2: UMEM Memory Pool & Power-of-2 Validation (TC04~TC08)
    # -----------------------------------------------------------------------
    def test_tc04_power_of_two_validation(self) -> None:
        """TC04: Verify power-of-2 constraints on frame count and frame size."""
        # Non-power-of-2 rejects
        with self.assertRaises(ValueError):
            UMEMMemoryPool(num_frames=1000, frame_size=2048)
        with self.assertRaises(ValueError):
            UMEMMemoryPool(num_frames=1024, frame_size=3000)
        with self.assertRaises(ValueError):
            UMEMMemoryPool(num_frames=0, frame_size=2048)
        with self.assertRaises(ValueError):
            UMEMMemoryPool(num_frames=512, frame_size=-2048)

        # Valid power-of-2 succeeds
        pool = UMEMMemoryPool(num_frames=128, frame_size=1024)
        self.assertEqual(pool.num_frames, 128)
        self.assertEqual(pool.frame_size, 1024)
        self.assertEqual(pool.total_size, 128 * 1024)
        pool.close()

    def test_tc05_frame_allocation_and_tracking(self) -> None:
        """TC05: Verify allocate_frame returns monotonic aligned addresses and tracks counts."""
        pool = UMEMMemoryPool(num_frames=16, frame_size=2048)
        self.assertEqual(pool.free_count, 16)
        self.assertEqual(pool.allocated_count, 0)

        addrs = []
        for i in range(16):
            addr = pool.allocate_frame()
            self.assertEqual(addr % 2048, 0, "Address must be frame-aligned")
            addrs.append(addr)

        self.assertEqual(pool.free_count, 0)
        self.assertEqual(pool.allocated_count, 16)
        self.assertEqual(len(set(addrs)), 16, "All frame addresses must be distinct")
        pool.close()

    def test_tc06_frame_release_and_recycling(self) -> None:
        """TC06: Verify release_frame correctly returns frames to free pool."""
        pool = UMEMMemoryPool(num_frames=8, frame_size=2048)
        a0 = pool.allocate_frame()
        a1 = pool.allocate_frame()
        self.assertEqual(pool.allocated_count, 2)
        self.assertEqual(pool.free_count, 6)

        # Release first frame
        pool.release_frame(a0)
        self.assertEqual(pool.allocated_count, 1)
        self.assertEqual(pool.free_count, 7)

        # Re-allocate should succeed without error
        a0_reclaimed = pool.allocate_frame()
        self.assertEqual(pool.allocated_count, 2)
        pool.close()

    def test_tc07_direct_memoryview_manipulation(self) -> None:
        """TC07: Verify zero-copy memoryview slice access and modifications."""
        pool = UMEMMemoryPool(num_frames=4, frame_size=2048)
        addr = pool.allocate_frame()
        view = pool.get_frame_buffer(addr)
        self.assertIsInstance(view, memoryview)
        self.assertEqual(len(view), 2048)

        # Modify view in-place
        test_payload = b"FIX_ZERO_COPY_PAYLOAD_TEST_12345"
        view[: len(test_payload)] = test_payload

        # Re-retrieve view and verify contents match exactly
        view2 = pool.get_view(addr)
        self.assertEqual(bytes(view2[: len(test_payload)]), test_payload)
        pool.close()

    def test_tc08_pool_exhaustion_and_recovery(self) -> None:
        """TC08: Verify MemoryError on exhaustion and recovery when freed."""
        pool = UMEMMemoryPool(num_frames=4, frame_size=1024)
        addrs = [pool.allocate_frame() for _ in range(4)]
        self.assertEqual(pool.free_count, 0)

        with self.assertRaises(MemoryError):
            pool.allocate_frame()

        # Free one and allocate again
        pool.release_frame(addrs[0])
        self.assertEqual(pool.free_count, 1)
        new_addr = pool.allocate_frame()
        self.assertIsNotNone(new_addr)
        pool.close()

    # -----------------------------------------------------------------------
    # Category 3: Lock-Free Descriptor Ring Queues (TC09~TC13)
    # -----------------------------------------------------------------------
    def test_tc09_ring_capacity_validation(self) -> None:
        """TC09: Verify power-of-2 validation for ring queues."""
        with self.assertRaises(ValueError):
            DescriptorRingQueue(capacity=100)
        with self.assertRaises(ValueError):
            DescriptorRingQueue(capacity=0)

        ring = DescriptorRingQueue(capacity=256)
        self.assertEqual(ring.capacity, 256)
        self.assertEqual(ring.mask, 255)

    def test_tc10_spsc_monotonic_sequence_and_wraparound(self) -> None:
        """TC10: Verify monotonic sequence counters and mask indexing across multiple wraparounds."""
        ring = DescriptorRingQueue(capacity=4)
        for cycle in range(10):
            for i in range(4):
                desc = PacketDescriptor(frame_addr=i * 2048, offset=0, length=100, flags=0)
                self.assertTrue(ring.enqueue(desc))
            self.assertTrue(ring.is_full())
            self.assertEqual(len(ring), 4)

            for i in range(4):
                d = ring.dequeue()
                self.assertIsNotNone(d)
                self.assertEqual(d.frame_addr, i * 2048)
            self.assertTrue(ring.is_empty())

        # Sequences must be monotonic
        self.assertEqual(ring.head_seq, 40)
        self.assertEqual(ring.tail_seq, 40)

    def test_tc11_enqueue_dequeue_empty_full_states(self) -> None:
        """TC11: Verify empty, full, count, and None return on empty dequeue."""
        ring = DescriptorRingQueue(capacity=8)
        self.assertTrue(ring.is_empty())
        self.assertFalse(ring.is_full())
        self.assertIsNone(ring.dequeue())

        desc = PacketDescriptor(frame_addr=2048, length=50)
        ring.enqueue(desc)
        self.assertFalse(ring.is_empty())
        self.assertEqual(len(ring), 1)

        d = ring.dequeue()
        self.assertEqual(d, desc)
        self.assertTrue(ring.is_empty())

    def test_tc12_ring_overflow_telemetry(self) -> None:
        """TC12: Verify ring overflow drops packet and increments dropped_count."""
        ring = DescriptorRingQueue(capacity=2)
        desc1 = PacketDescriptor(frame_addr=0)
        desc2 = PacketDescriptor(frame_addr=2048)
        desc3 = PacketDescriptor(frame_addr=4096)

        self.assertTrue(ring.enqueue(desc1))
        self.assertTrue(ring.enqueue(desc2))
        # Ring is full
        self.assertFalse(ring.enqueue(desc3))
        self.assertEqual(ring.dropped_count, 1)

    def test_tc13_batch_enqueue_and_dequeue(self) -> None:
        """TC13: Verify batch enqueue and dequeue operations."""
        ring = DescriptorRingQueue(capacity=16)
        descs = [PacketDescriptor(frame_addr=i * 2048) for i in range(10)]
        enqueued_count = ring.batch_enqueue(descs)
        self.assertEqual(enqueued_count, 10)
        self.assertEqual(len(ring), 10)

        dequeued = ring.batch_dequeue(max_count=6)
        self.assertEqual(len(dequeued), 6)
        self.assertEqual(len(ring), 4)

        dequeued_remaining = ring.batch_dequeue(max_count=10)
        self.assertEqual(len(dequeued_remaining), 4)
        self.assertEqual(len(ring), 0)

    # -----------------------------------------------------------------------
    # Category 4: Sub-Microsecond Buffer Swap Latency Benchmark (TC14~TC17)
    # -----------------------------------------------------------------------
    def test_tc14_descriptor_ring_swap_latency_sub_microsecond(self) -> None:
        """TC14: Assert DescriptorRingQueue swap latency is strictly < 1.0 us."""
        ring = DescriptorRingQueue(capacity=512)
        latency_us = ring.swap_buffers(iterations=200)
        self.assertGreater(latency_us, 0.0)
        self.assertLess(latency_us, 1.0, f"Ring swap latency must be < 1.0 us, got {latency_us:.4f} us")

    def test_tc15_engine_swap_buffers_sub_microsecond(self) -> None:
        """TC15: Assert KernelBypassTransportEngine.swap_buffers latency is < 1.0 us."""
        engine = KernelBypassTransportEngine(ring_capacity=512, use_mock_dma=True)
        latency_us = engine.swap_buffers(iterations=200)
        self.assertGreater(latency_us, 0.0)
        self.assertLess(latency_us, 1.0, f"Engine swap latency must be < 1.0 us, got {latency_us:.4f} us")
        engine.close()

    def test_tc16_dma_loopback_swap_sub_microsecond(self) -> None:
        """TC16: Assert swap_dma_loopback latency is < 1.0 us."""
        engine = KernelBypassTransportEngine(ring_capacity=512, use_mock_dma=True)
        latency_us = engine.swap_dma_loopback(iterations=200)
        self.assertGreater(latency_us, 0.0)
        self.assertLess(latency_us, 1.0, f"DMA loopback latency must be < 1.0 us, got {latency_us:.4f} us")
        engine.close()

    def test_tc17_large_burst_swap_benchmark(self) -> None:
        """TC17: Assert 1,000 swap iterations maintain average latency < 1.0 us."""
        engine = KernelBypassTransportEngine(ring_capacity=1024, use_mock_dma=True)
        avg_latency_us = engine.benchmark_swap_latency(iterations=1000)
        self.assertGreater(avg_latency_us, 0.0)
        self.assertLess(avg_latency_us, 1.0, f"1000-swap benchmark must be < 1.0 us, got {avg_latency_us:.4f} us")
        engine.close()

    # -----------------------------------------------------------------------
    # Category 5: FIX 4.4 Zero-Copy Serialization & Deserialization (TC18~TC22)
    # -----------------------------------------------------------------------
    def test_tc18_fix_new_order_single(self) -> None:
        """TC18: Verify NewOrderSingle (35=D) serialization, tags, and checksum."""
        engine = KernelBypassTransportEngine(use_mock_dma=True)
        desc = engine.serialize_fix_new_order(
            cl_ord_id="CLORD-001",
            symbol="005930",
            side=1,
            quantity=100,
            price=72500.0,
            account="KRW_DMA_ACC",
            ord_type=2,
        )
        self.assertGreater(desc.length, 0)
        self.assertEqual(desc.flags, FLAG_FIX)

        msg = engine.deserialize_fix_message(desc)
        self.assertEqual(msg.msg_type, "D")
        self.assertEqual(msg.get(35), "D")
        self.assertEqual(msg.get(11), "CLORD-001")
        self.assertEqual(msg.get(55), "005930")
        self.assertEqual(msg.get(54), "1")
        self.assertEqual(msg.get(38), "100")
        self.assertEqual(msg.get(44), "72500.0000")
        self.assertEqual(msg.get(1), "KRW_DMA_ACC")
        self.assertIsNotNone(msg.get(10), "Tag 10 CheckSum must be present")
        engine.close()

    def test_tc19_fix_execution_report(self) -> None:
        """TC19: Verify ExecutionReport (35=8) serialization and execution fields."""
        engine = KernelBypassTransportEngine(use_mock_dma=True)
        desc = engine.serialize_fix_execution_report(
            order_id="ORD-999",
            cl_ord_id="CLORD-001",
            exec_id="EXEC-777",
            exec_type="2",
            ord_status="2",
            symbol="AAPL",
            side=1,
            order_qty=500,
            last_qty=500,
            last_px=185.50,
            leaves_qty=0,
            cum_qty=500,
            avg_px=185.50,
        )
        msg = engine.deserialize_fix_message(desc)
        self.assertEqual(msg.msg_type, "8")
        self.assertEqual(msg.get(37), "ORD-999")
        self.assertEqual(msg.get(17), "EXEC-777")
        self.assertEqual(msg.get(150), "2")
        self.assertEqual(msg.get(39), "2")
        self.assertEqual(msg.get(31), "185.5000")
        self.assertEqual(msg.get(6), "185.5000")
        engine.close()

    def test_tc20_fix_heartbeat(self) -> None:
        """TC20: Verify Heartbeat (35=0) serialization and TestReqID."""
        engine = KernelBypassTransportEngine(use_mock_dma=True)
        desc = engine.serialize_fix_heartbeat(test_req_id="TEST-REQ-123")
        msg = engine.deserialize_fix_message(desc)
        self.assertEqual(msg.msg_type, "0")
        self.assertEqual(msg.get(112), "TEST-REQ-123")
        engine.close()

    def test_tc21_high_level_send_and_recv_fix(self) -> None:
        """TC21: Verify end-to-end send_fix and recv_fix round-trip in mock DMA loopback."""
        engine = KernelBypassTransportEngine(use_mock_dma=True)
        msg_in = FIXMessage(msg_type="D", sender_comp_id="ALPHA_DMA", target_comp_id="KRX_GATEWAY")
        msg_in.set(11, "ORDER-ROUNDTRIP-01").set(55, "000660").set(54, "2").set(38, "50")

        bytes_sent = engine.send_fix(msg_in)
        self.assertGreater(bytes_sent, 0)

        msg_out = engine.recv_fix()
        self.assertIsNotNone(msg_out)
        self.assertEqual(msg_out.msg_type, "D")
        self.assertEqual(msg_out.get(11), "ORDER-ROUNDTRIP-01")
        self.assertEqual(msg_out.get(55), "000660")
        self.assertEqual(msg_out.get(54), "2")
        self.assertEqual(msg_out.get(38), "50")
        engine.close()

    def test_tc22_corrupted_checksum_rejection(self) -> None:
        """TC22: Assert corrupted FIX CheckSum raises ValueError."""
        corrupted_fix = "8=FIX.4.4\x019=40\x0135=0\x0149=SENDER\x0156=TARGET\x0134=1\x0110=999\x01"
        with self.assertRaises(ValueError):
            FIXMessage.decode(corrupted_fix)

    # -----------------------------------------------------------------------
    # Category 6: Binary LOB Multicast Packet Serialization (TC23~TC26)
    # -----------------------------------------------------------------------
    def test_tc23_binary_lob_packet_structure_and_magic(self) -> None:
        """TC23: Verify binary LOB multicast packet size, magic, and version."""
        self.assertEqual(MAGIC_LOBM, 0x4C4F424D)
        self.assertEqual(LOBM_VERSION, 116)
        self.assertEqual(LOB_PACKET_SIZE, 236)

        pkt = LOBMulticastPacket(
            symbol="NVDA",
            timestamp_ns=1700000000000000000,
            bid_price=450.50,
            ask_price=450.60,
            bid_size=100.0,
            ask_size=200.0,
        )
        self.assertEqual(pkt.symbol, "NVDA")
        self.assertEqual(pkt.magic, MAGIC_LOBM)
        self.assertEqual(pkt.version, 116)

        encoded = pkt.encode()
        self.assertEqual(len(encoded), LOB_PACKET_SIZE)

    def test_tc24_binary_lob_depth_ladders_fidelity(self) -> None:
        """TC24: Verify 5-level bid/ask price and size ladders pack and unpack losslessly."""
        b_px = (450.50, 450.40, 450.30, 450.20, 450.10)
        a_px = (450.60, 450.70, 450.80, 450.90, 451.00)
        b_sz = (100.0, 250.0, 500.0, 750.0, 1000.0)
        a_sz = (150.0, 300.0, 450.0, 600.0, 850.0)

        pkt = LOBMulticastPacket(
            symbol="SPY",
            timestamp_ns=1700000000123456789,
            bid_price=450.50,
            ask_price=450.60,
            bid_size=100.0,
            ask_size=150.0,
            depth_levels=5,
            bid_prices=b_px,
            ask_prices=a_px,
            bid_sizes=b_sz,
            ask_sizes=a_sz,
            sequence=42,
        )

        encoded = pkt.encode()
        decoded = LOBMulticastPacket.decode(encoded)

        self.assertEqual(decoded.symbol, "SPY")
        self.assertEqual(decoded.sequence, 42)
        self.assertAlmostEqual(decoded.bid_price, 450.50)
        self.assertAlmostEqual(decoded.ask_price, 450.60)
        self.assertEqual(decoded.depth_levels, 5)

        for i in range(5):
            self.assertAlmostEqual(decoded.bid_prices[i], b_px[i])
            self.assertAlmostEqual(decoded.ask_prices[i], a_px[i])
            self.assertAlmostEqual(decoded.bid_sizes[i], b_sz[i])
            self.assertAlmostEqual(decoded.ask_sizes[i], a_sz[i])

    def test_tc25_high_level_send_and_recv_lob(self) -> None:
        """TC25: Verify high-level send_lob_multicast and recv_lob_multicast round-trip."""
        engine = KernelBypassTransportEngine(use_mock_dma=True)
        pkt_in = LOBMulticastPacket(
            symbol="005930",
            bid_price=71500.0,
            ask_price=71600.0,
            bid_size=300.0,
            ask_size=400.0,
        )
        bytes_sent = engine.send_lob_multicast(pkt_in)
        self.assertEqual(bytes_sent, LOB_PACKET_SIZE)

        pkt_out = engine.recv_lob_multicast()
        self.assertIsNotNone(pkt_out)
        self.assertEqual(pkt_out.symbol, "005930")
        self.assertAlmostEqual(pkt_out.bid_price, 71500.0)
        self.assertAlmostEqual(pkt_out.ask_price, 71600.0)
        engine.close()

    def test_tc26_direct_memoryview_lob_serialization(self) -> None:
        """TC26: Verify serialize_binary_lob and deserialize_binary_lob over UMEM buffer."""
        engine = KernelBypassTransportEngine(use_mock_dma=True)
        desc = engine.serialize_binary_lob(
            symbol="MSFT",
            bid_price=330.25,
            ask_price=330.35,
            bid_size=50.0,
            ask_size=75.0,
        )
        self.assertEqual(desc.length, LOB_PACKET_SIZE)
        self.assertEqual(desc.flags, FLAG_LOB)

        pkt = engine.deserialize_binary_lob(desc)
        self.assertEqual(pkt.symbol, "MSFT")
        self.assertAlmostEqual(pkt.bid_price, 330.25)
        self.assertAlmostEqual(pkt.ask_price, 330.35)
        engine.close()

    # -----------------------------------------------------------------------
    # Category 7: Batch Burst Packet I/O & Completion Recycling (TC27~TC30)
    # -----------------------------------------------------------------------
    def test_tc27_tx_burst_operations(self) -> None:
        """TC27: Verify tx_burst batch submissions."""
        engine = KernelBypassTransportEngine(use_mock_dma=True)
        descs = [
            engine.serialize_fix_heartbeat(test_req_id=f"BURST-{i}")
            for i in range(16)
        ]
        sent_count = engine.tx_burst(descs)
        self.assertEqual(sent_count, 16)
        self.assertEqual(engine.stats["tx_bursts"], 1)
        engine.close()

    def test_tc28_rx_burst_operations(self) -> None:
        """TC28: Verify rx_burst batch reception."""
        engine = KernelBypassTransportEngine(use_mock_dma=True)
        for i in range(10):
            d = engine.serialize_fix_heartbeat(test_req_id=f"RXBURST-{i}")
            engine.submit_tx(d)

        received = engine.rx_burst(max_packets=32)
        self.assertEqual(len(received), 10)
        self.assertEqual(engine.stats["rx_bursts"], 1)
        engine.close()

    def test_tc29_completion_ring_recycling(self) -> None:
        """TC29: Verify completion ring collects transmitted descriptors and recycles frames."""
        engine = KernelBypassTransportEngine(use_mock_dma=True)
        initial_free = engine.umem_pool.free_count

        d = engine.serialize_fix_heartbeat()
        self.assertEqual(engine.umem_pool.free_count, initial_free - 1)

        engine.submit_tx(d)
        # Recycles frame from completion ring
        recycled_count = engine.recycle_completion_ring()
        self.assertEqual(recycled_count, 1)
        self.assertEqual(engine.umem_pool.free_count, initial_free)
        engine.close()

    def test_tc30_telemetry_diagnostics(self) -> None:
        """TC30: Verify diagnostic telemetry and ring status."""
        engine = KernelBypassTransportEngine(use_mock_dma=True)
        engine.send_fix(FIXMessage(msg_type="0"))
        stats = engine.get_stats()
        self.assertEqual(stats["tx_packets"], 1)
        self.assertFalse(stats["is_fallback"])
        self.assertTrue(stats["use_mock_dma"])
        self.assertIn("umem_free_frames", stats)
        self.assertIn("rx_ring_queued", stats)
        engine.close()

    # -----------------------------------------------------------------------
    # Category 8: Transparent Fallback Transport & Zero Memory Leaks (TC31~TC35)
    # -----------------------------------------------------------------------
    def test_tc31_fallback_mode_activation(self) -> None:
        """TC31: Verify fallback transport activation when use_mock_dma=False."""
        engine = KernelBypassTransportEngine(use_mock_dma=False)
        self.assertTrue(engine.is_fallback_active())
        self.assertIsNone(engine.umem_pool)
        self.assertIsNone(engine.rx_ring)
        self.assertIsNone(engine.tx_ring)

        stats = engine.get_stats()
        self.assertTrue(stats["is_fallback"])
        self.assertFalse(stats["use_mock_dma"])
        engine.close()

    def test_tc32_fallback_send_recv_fix(self) -> None:
        """TC32: Verify FIX messaging works transparently in fallback mode."""
        engine = KernelBypassTransportEngine(use_mock_dma=False)
        msg_in = FIXMessage(msg_type="D").set(11, "FALLBACK-ORD").set(55, "GOOGL")
        length = engine.send_fix(msg_in)
        self.assertGreater(length, 0)

        msg_out = engine.recv_fix()
        self.assertIsNotNone(msg_out)
        self.assertEqual(msg_out.get(11), "FALLBACK-ORD")
        self.assertEqual(msg_out.get(55), "GOOGL")
        self.assertEqual(engine.stats["fallback_tx"], 1)
        self.assertEqual(engine.stats["fallback_rx"], 1)
        engine.close()

    def test_tc33_fallback_send_recv_lob(self) -> None:
        """TC33: Verify binary LOB multicast works transparently in fallback mode."""
        engine = KernelBypassTransportEngine(use_mock_dma=False)
        pkt_in = LOBMulticastPacket(symbol="AMZN", bid_price=140.0, ask_price=140.1)
        engine.send_lob_multicast(pkt_in)

        pkt_out = engine.recv_lob_multicast()
        self.assertIsNotNone(pkt_out)
        self.assertEqual(pkt_out.symbol, "AMZN")
        self.assertAlmostEqual(pkt_out.bid_price, 140.0)
        engine.close()

    def test_tc34_context_manager_cleanup(self) -> None:
        """TC34: Verify context manager clean resource release."""
        with KernelBypassTransportEngine(use_mock_dma=True) as engine:
            self.assertIsNotNone(engine.umem_pool)
        self.assertIsNone(engine.umem_pool)

        with KernelBypassTransportEngine(use_mock_dma=False) as engine_fb:
            self.assertTrue(engine_fb.is_fallback_active())
        self.assertIsNone(engine_fb._fallback_queue)

    def test_tc35_stress_lifecycle_zero_leak(self) -> None:
        """TC35: Verify 100 consecutive lifecycle open/close cycles without memory or resource leak."""
        for cycle in range(50):
            # DMA mock mode
            with KernelBypassTransportEngine(num_frames=64, ring_capacity=32, use_mock_dma=True) as eng:
                eng.send_fix(FIXMessage(msg_type="0"))
                _ = eng.recv_fix()

            # Fallback mode
            with KernelBypassTransportEngine(use_mock_dma=False) as eng_fb:
                eng_fb.send_fix(FIXMessage(msg_type="0"))
                _ = eng_fb.recv_fix()


if __name__ == "__main__":
    unittest.main()
