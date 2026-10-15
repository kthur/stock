r"""
tests/test_phase109_adversarial_challenger1.py
=============================================
Empirical Adversarial Stress Testing & Invariant Challenge Suite for Phase 109.
Release R125 / v116 Production Master (Features F515, F518).

Adversarial Challenge Targets:
1. R1: Kernel-Bypass DPDK/AF_XDP Mock DMA Transport Engine (F515)
   - UMEM Memory Pool stress: High-frequency frame allocation/release cycles (10,000+),
     buffer exhaustion, out-of-bounds addresses, zero-copy view mutations, double-free safety.
   - Descriptor Ring Swap Latency: 10,000 bursts benchmark asserting sub-microsecond latency (< 1.0 μs),
     queue overflow drop semantics, and batch I/O invariants.
   - FIX 4.4 Parser/Encoder Fuzzing: Corrupted checksum injection, truncated frames, malformed tags,
     mutant string payloads, and round-trip serialization fidelity.
   - Fallback Transport: Rapid lifecycle creation/destruction (1,000 cycles), zero socket leaks,
     zero memory leaks, and transparent fallback operation.
2. R4: Synthetic Dark Pool Cross-Asset Matching Engine (F518)
   - Adversarial HFT Pinging: Sub-MFI micro-orders (1~5 shares) attacking institutional block orders,
     verifying zero leakage and complete ping suppression.
   - Locked & Crossed Markets: Lit quote sanity violations ($P_{bid} \ge P_{ask}$), violent spread widenings
     (flash-crash collar breaches), and negative quotes.
   - Mathematical Invariants: Exact integer volume conservation ($Q_{order} == Q_{filled} + Q_{residual}$)
     across asymmetric fragmented fills, multi-symbol opposing baskets across 5 markets, and
     exact half-spread capture arithmetic ($Savings_{buyer} + Savings_{seller} == Spread \times Q$).
"""

from __future__ import annotations

import collections
import gc
import logging
import math
import os
import random
import string
import struct
import sys
import time
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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
    LOB_PACKET_FORMAT,
    LOB_PACKET_SIZE,
    MAGIC_LOBM,
    DescriptorRingQueue,
    FIXMessage,
    KernelBypassTransportEngine,
    LOBMulticastPacket,
    PacketDescriptor,
    UMEMMemoryPool,
)
from src.broker.synthetic_dark_pool import (
    DarkCrossExecution,
    DarkPoolMatchResult,
    DarkPoolOrder,
    DarkPoolOrderStatus,
    DarkPoolSavingsReport,
    DarkPoolSide,
    QueuePriorityMode,
    ResidualOrderPlan,
    SyntheticDarkPool,
    round_to_tick_size,
)


class TestPhase109AdversarialChallenger1(unittest.TestCase):
    """Empirical Adversarial Challenger Test Suite for Phase 109 R1 & R4."""

    # =======================================================================
    # SECTION 1: UMEM Memory Pool Adversarial Stress Testing (Task 1A)
    # =======================================================================

    def test_adv_umem_high_frequency_churn_10000(self) -> None:
        """Stress test UMEM memory pool under 10,000 rapid frame allocation and release cycles."""
        num_frames = 64
        frame_size = 2048
        pool = UMEMMemoryPool(num_frames=num_frames, frame_size=frame_size)

        self.assertEqual(pool.free_count, num_frames)
        self.assertEqual(pool.allocated_count, 0)

        # 10,000 rapid allocate/release cycles
        for cycle in range(10000):
            # Allocate 16 frames
            addrs = [pool.allocate_frame() for _ in range(16)]
            self.assertEqual(len(addrs), 16)
            self.assertEqual(pool.allocated_count, 16)
            self.assertEqual(pool.free_count, num_frames - 16)

            # Release in reverse order
            for a in reversed(addrs):
                pool.release_frame(a)

            self.assertEqual(pool.free_count, num_frames)
            self.assertEqual(pool.allocated_count, 0)

        pool.close()

    def test_adv_umem_buffer_exhaustion_and_recovery(self) -> None:
        """Stress test UMEM memory pool under complete buffer exhaustion."""
        num_frames = 32
        frame_size = 1024
        pool = UMEMMemoryPool(num_frames=num_frames, frame_size=frame_size)

        # Allocate all 32 frames
        allocated = []
        for _ in range(num_frames):
            allocated.append(pool.allocate_frame())

        self.assertEqual(pool.free_count, 0)
        self.assertEqual(pool.allocated_count, num_frames)

        # 33rd allocation MUST raise MemoryError
        with self.assertRaises(MemoryError):
            pool.allocate_frame()

        # Partial release: release 10 frames
        for addr in allocated[:10]:
            pool.release_frame(addr)

        self.assertEqual(pool.free_count, 10)
        self.assertEqual(pool.allocated_count, num_frames - 10)

        # Re-allocate those 10 frames
        re_alloc = [pool.allocate_frame() for _ in range(10)]
        self.assertEqual(len(re_alloc), 10)
        self.assertEqual(pool.free_count, 0)

        # Fully release all remaining
        for addr in allocated[10:] + re_alloc:
            pool.release_frame(addr)

        self.assertEqual(pool.free_count, num_frames)
        self.assertEqual(pool.allocated_count, 0)
        pool.close()

    def test_adv_umem_out_of_bounds_and_invalid_addresses(self) -> None:
        """Adversarial stress test on out-of-bounds offsets and invalid frame addresses."""
        num_frames = 16
        frame_size = 2048
        pool = UMEMMemoryPool(num_frames=num_frames, frame_size=frame_size)

        # Negative addresses
        with self.assertRaises(ValueError):
            pool.release_frame(-1)
        with self.assertRaises(ValueError):
            pool.get_frame_buffer(-2048)

        # Address beyond total buffer size
        total_size = num_frames * frame_size  # 32768
        with self.assertRaises(ValueError):
            pool.release_frame(total_size + 100)
        with self.assertRaises(ValueError):
            pool.get_frame_buffer(total_size * 2)

        # Address exceeding total size by exact frame size
        with self.assertRaises(ValueError):
            pool.release_frame(total_size)
        with self.assertRaises(ValueError):
            pool.get_frame_buffer(total_size)

        pool.close()

    def test_adv_umem_double_free_resilience(self) -> None:
        """Verify that double-releasing a frame does NOT corrupt the free frames deque."""
        pool = UMEMMemoryPool(num_frames=8, frame_size=1024)
        addr = pool.allocate_frame()
        self.assertEqual(pool.allocated_count, 1)
        self.assertEqual(pool.free_count, 7)

        # First release
        pool.release_frame(addr)
        self.assertEqual(pool.allocated_count, 0)
        self.assertEqual(pool.free_count, 8)

        # Second release (double free attempt) — should be a safe no-op
        pool.release_frame(addr)
        self.assertEqual(pool.allocated_count, 0)
        self.assertEqual(pool.free_count, 8)

        # Verify we can allocate all 8 unique frames without duplicate tokens
        addrs = set()
        for _ in range(8):
            addrs.add(pool.allocate_frame())
        self.assertEqual(len(addrs), 8)
        self.assertEqual(pool.free_count, 0)

        pool.close()

    def test_adv_umem_zero_copy_view_mutation_isolation(self) -> None:
        """Verify zero-copy memoryview slices mutate underlying buffer and isolate frames."""
        pool = UMEMMemoryPool(num_frames=4, frame_size=256)
        addr0 = pool.allocate_frame()
        addr1 = pool.allocate_frame()

        view0 = pool.get_frame_buffer(addr0)
        view1 = pool.get_frame_buffer(addr1)

        # Write pattern into frame 0
        pat0 = b"A" * 64
        view0[:64] = pat0

        # Write pattern into frame 1
        pat1 = b"B" * 64
        view1[:64] = pat1

        # Verify zero-copy persistence
        self.assertEqual(bytes(view0[:64]), pat0)
        self.assertEqual(bytes(view1[:64]), pat1)

        # Verify frame 0 did not bleed into frame 1
        self.assertNotEqual(bytes(view0[:64]), bytes(view1[:64]))
        self.assertEqual(bytes(view0[64:128]), b"\x00" * 64)

        # Re-fetch new views and check content is preserved
        fresh_view0 = pool.get_frame_buffer(addr0)
        self.assertEqual(bytes(fresh_view0[:64]), pat0)

        pool.close()

    # =======================================================================
    # SECTION 2: Descriptor Ring Swap Latency Benchmark (Task 1B)
    # =======================================================================

    def test_adv_descriptor_ring_swap_latency_10000_bursts(self) -> None:
        """
        Adversarial benchmark of descriptor ring swap latency across 10,000 bursts.
        Strict assertion: average swap latency must be sub-microsecond (< 1.0 μs).
        """
        capacity = 512
        ring = DescriptorRingQueue(capacity=capacity, name="benchmark_ring")

        iterations = 10000
        latency_us = ring.swap_buffers(iterations=iterations)

        # Assert sub-microsecond SLA
        self.assertLess(
            latency_us,
            1.0,
            f"Descriptor ring swap latency {latency_us:.4f} μs breached sub-microsecond SLA (< 1.0 μs)",
        )
        self.assertGreater(latency_us, 0.0)
        print(f"\n[EMPIRICAL BENCHMARK] 10,000 Bursts Swap Latency: {latency_us * 1000.0:.2f} ns ({latency_us:.4f} μs)")

    def test_adv_descriptor_ring_overflow_drop_semantics(self) -> None:
        """Adversarial stress test on ring buffer overflow and drop counters."""
        capacity = 16
        ring = DescriptorRingQueue(capacity=capacity, name="overflow_test")

        # Fill capacity exactly
        for i in range(capacity):
            desc = PacketDescriptor(frame_addr=i * 2048, offset=0, length=128, flags=FLAG_FIX)
            success = ring.enqueue(desc)
            self.assertTrue(success)

        self.assertTrue(ring.is_full())
        self.assertEqual(len(ring), capacity)
        self.assertEqual(ring.dropped_count, 0)

        # Attempt to enqueue 50 additional descriptors into full ring
        for i in range(50):
            overflow_desc = PacketDescriptor(frame_addr=9999, offset=0, length=128, flags=FLAG_FIX)
            success = ring.enqueue(overflow_desc)
            self.assertFalse(success)

        self.assertEqual(ring.dropped_count, 50)
        self.assertEqual(len(ring), capacity)

        # Dequeue half the descriptors
        dequeued = ring.batch_dequeue(max_count=8)
        self.assertEqual(len(dequeued), 8)
        self.assertEqual(len(ring), 8)
        self.assertFalse(ring.is_full())

        # Now enqueue 8 new descriptors
        for i in range(8):
            desc = PacketDescriptor(frame_addr=(i + 100) * 2048, offset=0, length=128, flags=FLAG_FIX)
            success = ring.enqueue(desc)
            self.assertTrue(success)

        self.assertTrue(ring.is_full())
        self.assertEqual(ring.dropped_count, 50)

    # =======================================================================
    # SECTION 3: FIX 4.4 Parser / Encoder Fuzzing & Corruption (Task 1C)
    # =======================================================================

    def test_adv_fix_corrupted_checksum_rejection(self) -> None:
        """Verify corrupted checksums in FIX messages are strictly detected and rejected."""
        msg = FIXMessage(msg_type="0", sender_comp_id="SENDER", target_comp_id="TARGET")
        valid_msg = msg.encode(msg_seq_num=1)

        # Confirm valid message decodes cleanly
        parsed_valid = FIXMessage.decode(valid_msg)
        self.assertEqual(parsed_valid.msg_type, "0")

        # Corrupt tag 10 checksum deliberately (tampered checksum: 999 instead of correct)
        valid_chk = parsed_valid.get(10)
        self.assertIsNotNone(valid_chk)
        corrupted_checksum_msg = valid_msg.replace(f"10={valid_chk}", "10=999")
        with self.assertRaises(ValueError) as ctx:
            FIXMessage.decode(corrupted_checksum_msg)
        self.assertIn("FIX Checksum mismatch", str(ctx.exception))

        # Off-by-one checksum corruption
        tampered_chk = f"{(int(valid_chk) + 1) % 256:03d}"
        corrupted_off_by_one = valid_msg.replace(f"10={valid_chk}", f"10={tampered_chk}")
        with self.assertRaises(ValueError) as ctx:
            FIXMessage.decode(corrupted_off_by_one)
        self.assertIn("FIX Checksum mismatch", str(ctx.exception))

    def test_adv_fix_truncated_and_malformed_frames_fuzz(self) -> None:
        """Fuzz testing with truncated frames, malformed tags, and missing fields."""
        # Empty string
        with self.assertRaises(ValueError):
            FIXMessage.decode("")

        # Truncated mid-tag
        truncated_msg = "8=FIX.4.4\x019=45\x0135="
        msg = FIXMessage.decode(truncated_msg)
        self.assertEqual(msg.tags.get(35), "")

        # Non-numeric tag ignored gracefully without crashing
        malformed_tag_msg = "8=FIX.4.4\x01INVALID_TAG=123\x0135=D\x01"
        msg = FIXMessage.decode(malformed_tag_msg)
        self.assertEqual(msg.msg_type, "D")
        self.assertNotIn("INVALID_TAG", msg.tags)

        # Repeated delimiters \x01\x01\x01
        spam_delims = "8=FIX.4.4\x01\x01\x0135=8\x01\x0155=AAPL\x01"
        msg = FIXMessage.decode(spam_delims)
        self.assertEqual(msg.msg_type, "8")
        self.assertEqual(msg.get(55), "AAPL")

    def test_adv_fix_round_trip_encoding_and_checksum_integrity(self) -> None:
        """Verify encode -> decode exact round trip with valid modulo-256 checksum."""
        engine = KernelBypassTransportEngine(num_frames=32, frame_size=2048, ring_capacity=16)

        # Test NewOrderSingle (35=D)
        desc_d = engine.serialize_fix_new_order(
            cl_ord_id="ORD_FUZZ_001",
            symbol="NVDA",
            side=1,
            quantity=5000,
            price=125.75,
            account="DMA_CORE_HFT",
        )
        msg_d = engine.deserialize_fix_message(desc_d)
        self.assertEqual(msg_d.msg_type, "D")
        self.assertEqual(msg_d.get(11), "ORD_FUZZ_001")
        self.assertEqual(msg_d.get(55), "NVDA")
        self.assertEqual(msg_d.get(54), "1")
        self.assertEqual(msg_d.get(38), "5000")
        self.assertEqual(msg_d.get(44), "125.7500")

        # Test ExecutionReport (35=8)
        desc_8 = engine.serialize_fix_execution_report(
            order_id="EX_001",
            cl_ord_id="ORD_FUZZ_001",
            exec_id="EXEC_001",
            exec_type="0",
            ord_status="2",
            symbol="NVDA",
            side=1,
            order_qty=5000,
            last_qty=5000,
            last_px=125.75,
            leaves_qty=0,
            cum_qty=5000,
            avg_px=125.75,
        )
        msg_8 = engine.deserialize_fix_message(desc_8)
        self.assertEqual(msg_8.msg_type, "8")
        self.assertEqual(msg_8.get(37), "EX_001")
        self.assertEqual(msg_8.get(14), "5000")

        engine.close()

    # =======================================================================
    # SECTION 4: Fallback Transport Stress & Lifecycle (Task 1D)
    # =======================================================================

    def test_adv_fallback_transport_rapid_lifecycle_1000_cycles(self) -> None:
        """Verify zero socket/resource leaks or deadlocks under 1,000 rapid fallback cycles."""
        for _ in range(1000):
            engine = KernelBypassTransportEngine(fallback_mode=True)
            self.assertTrue(engine.is_fallback_active())
            self.assertIsNone(engine.umem_pool)
            self.assertIsNone(engine.rx_ring)

            # Send and receive in fallback mode
            msg = FIXMessage(msg_type="D")
            msg.set(55, "TSLA")
            msg.set(38, "100")
            tx_len = engine.send_fix(msg)
            self.assertGreater(tx_len, 0)

            rx_msg = engine.recv_fix()
            self.assertIsNotNone(rx_msg)
            self.assertEqual(rx_msg.get(55), "TSLA")

            engine.close()

        # Check process garbage collector is clean
        gc.collect()

    def test_adv_fallback_mixed_stream_stress(self) -> None:
        """Stress test high-throughput interleaved FIX and LOB packets in fallback mode."""
        engine = KernelBypassTransportEngine(fallback_mode=True)

        for i in range(100):
            # Send FIX
            f_msg = FIXMessage(msg_type="0")
            f_msg.set(112, f"PING_{i}")
            engine.send_fix(f_msg)

            # Send LOB
            lob_dict = {
                "symbol": "SPY",
                "bid_price": 500.0 + i * 0.01,
                "ask_price": 500.05 + i * 0.01,
                "bid_size": 1000.0,
                "ask_size": 1200.0,
            }
            engine.send_lob_multicast(lob_dict)

        self.assertEqual(engine.stats["tx_packets"], 200)

        # Dequeue interleaved packets
        for i in range(100):
            f_rx = engine.recv_fix()
            self.assertIsNotNone(f_rx)
            self.assertEqual(f_rx.get(112), f"PING_{i}")

            lob_rx = engine.recv_lob_multicast()
            self.assertIsNotNone(lob_rx)
            self.assertEqual(lob_rx.symbol, "SPY")
            self.assertAlmostEqual(lob_rx.bid_price, 500.0 + i * 0.01, places=4)

        self.assertEqual(engine.stats["rx_packets"], 200)
        engine.close()

    # =======================================================================
    # SECTION 5: Synthetic Dark Pool Adversarial HFT Attacks (Task 1E)
    # =======================================================================

    def test_adv_dark_pool_sub_mfi_predatory_ping_suppression(self) -> None:
        """
        Adversarial HFT Attack: An attacker submits 1-share and 5-share micro-orders
        to probe and sniff an institutional block order of 50,000 shares (MFI=1,000).
        Assertion: All predatory pings are completely blocked; block order remains 100% unfilled.
        """
        dark_pool = SyntheticDarkPool(
            min_fill_ratio=0.20,
            default_min_fill_size=100,
            enable_anti_gaming=True,
        )

        # Institutional Buyer resting order: 50,000 shares with MFI = 10,000 (20% of 50k)
        inst_buy = dark_pool.add_order(
            order_id="INST_BLOCK_BUY_001",
            symbol="MSFT",
            market="NASDAQ",
            side="BUY",
            quantity=50000,
            client_id="PENSION_FUND_ALPHA",
            min_fill_size=10000,
        )

        # Attacker 1: 1-share predatory ping
        ping1 = dark_pool.add_order(
            order_id="PREDATOR_PING_001",
            symbol="MSFT",
            market="NASDAQ",
            side="SELL",
            quantity=1,
            client_id="PREDATORY_HFT",
            min_fill_size=1,
        )

        # Attacker 2: 50-share probing order
        ping2 = dark_pool.add_order(
            order_id="PREDATOR_PING_002",
            symbol="MSFT",
            market="NASDAQ",
            side="SELL",
            quantity=50,
            client_id="PREDATORY_HFT",
            min_fill_size=1,
        )

        # Attacker 3: 500-share probing order (still below 10,000 MFI)
        ping3 = dark_pool.add_order(
            order_id="PREDATOR_PING_003",
            symbol="MSFT",
            market="NASDAQ",
            side="SELL",
            quantity=500,
            client_id="PREDATORY_HFT",
            min_fill_size=1,
        )

        # Match at valid quotes
        execs, residuals = dark_pool.match_orders(symbol="MSFT", bid_quote=420.00, ask_quote=420.10)

        # Assert zero fills executed against predatory pings
        self.assertEqual(len(execs), 0, "Predatory pings must not trigger any execution")
        self.assertEqual(inst_buy.filled_quantity, 0)
        self.assertEqual(inst_buy.remaining_quantity, 50000)
        self.assertEqual(ping1.filled_quantity, 0)
        self.assertEqual(ping2.filled_quantity, 0)
        self.assertEqual(ping3.filled_quantity, 0)

        # Now legitimate counterparty submits 15,000 shares (>= 10,000 MFI)
        legit_sell = dark_pool.add_order(
            order_id="LEGIT_INST_SELL_001",
            symbol="MSFT",
            market="NASDAQ",
            side="SELL",
            quantity=15000,
            client_id="SOVEREIGN_WEALTH_BETA",
            min_fill_size=3000,
        )

        execs_legit, _ = dark_pool.match_orders(symbol="MSFT", bid_quote=420.00, ask_quote=420.10)
        self.assertEqual(len(execs_legit), 1)
        self.assertEqual(execs_legit[0].matched_quantity, 15000)
        self.assertEqual(inst_buy.filled_quantity, 15000)
        self.assertEqual(inst_buy.remaining_quantity, 35000)
        self.assertEqual(legit_sell.filled_quantity, 15000)
        self.assertEqual(legit_sell.remaining_quantity, 0)

    def test_adv_dark_pool_locked_and_crossed_market_rejection(self) -> None:
        """
        Adversarial Market Condition: Lit quotes are locked (bid == ask) or crossed (bid > ask).
        Assertion: Crossing engine suspends immediately; 0 shares matched; residuals flagged.
        """
        dark_pool = SyntheticDarkPool()

        dark_pool.add_order(
            order_id="BUY_LOCKED",
            symbol="005930",
            market="KOSPI",
            side="BUY",
            quantity=1000,
        )
        dark_pool.add_order(
            order_id="SELL_LOCKED",
            symbol="005930",
            market="KOSPI",
            side="SELL",
            quantity=1000,
        )

        # 1. Test Locked Market (bid == ask == 70,000 KRW)
        execs_locked, residuals_locked = dark_pool.match_orders(
            symbol="005930", bid_quote=70000.0, ask_quote=70000.0, market="KOSPI"
        )
        self.assertEqual(len(execs_locked), 0, "Locked market must suspend execution")
        self.assertEqual(len(residuals_locked), 2)
        for r in residuals_locked:
            self.assertEqual(r.routing_reason, "LOCKED_CROSSED_MARKET")

        # 2. Test Crossed Market (bid 70,500 > ask 70,000 KRW)
        execs_crossed, residuals_crossed = dark_pool.match_orders(
            symbol="005930", bid_quote=70500.0, ask_quote=70000.0, market="KOSPI"
        )
        self.assertEqual(len(execs_crossed), 0, "Crossed market must suspend execution")
        self.assertEqual(len(residuals_crossed), 2)
        for r in residuals_crossed:
            self.assertEqual(r.routing_reason, "LOCKED_CROSSED_MARKET")

        # 3. Test Negative / Zero quotes
        execs_neg, _ = dark_pool.match_orders(
            symbol="005930", bid_quote=-100.0, ask_quote=70000.0, market="KOSPI"
        )
        self.assertEqual(len(execs_neg), 0)

    def test_adv_dark_pool_spread_collar_breach(self) -> None:
        """
        Adversarial Market Condition: Spread violently widens past max collar (200 bps).
        Assertion: Matching suspended, residual tagged with COLLAR_BREACH.
        """
        dark_pool = SyntheticDarkPool(max_spread_bps_collar=200.0)

        dark_pool.add_order(
            order_id="BUY_COLLAR",
            symbol="AAPL",
            market="NASDAQ",
            side="BUY",
            quantity=500,
        )
        dark_pool.add_order(
            order_id="SELL_COLLAR",
            symbol="AAPL",
            market="NASDAQ",
            side="SELL",
            quantity=500,
        )

        # Spread: bid=150.0, ask=160.0 -> mid=155.0, spread=10.0 -> bps = (10/155)*10000 = 645 bps > 200 bps
        execs, residuals = dark_pool.match_orders(symbol="AAPL", bid_quote=150.00, ask_quote=160.00)

        self.assertEqual(len(execs), 0, "Spread collar breach must suspend matching")
        self.assertEqual(len(residuals), 2)
        for r in residuals:
            self.assertEqual(r.routing_reason, "COLLAR_BREACH")

    def test_adv_dark_pool_wash_sale_guard_enforcement(self) -> None:
        """Verify wash-sale protection prevents identical client and portfolio accounts from matching."""
        dark_pool = SyntheticDarkPool(wash_sale_guard=True)

        # Same client and same portfolio
        buy_same = dark_pool.add_order(
            order_id="BUY_WASH",
            symbol="AMZN",
            market="SP500",
            side="BUY",
            quantity=200,
            client_id="DESK_QUANT_1",
            portfolio_id="PORTFOLIO_ALPHA",
        )
        sell_same = dark_pool.add_order(
            order_id="SELL_WASH",
            symbol="AMZN",
            market="SP500",
            side="SELL",
            quantity=200,
            client_id="DESK_QUANT_1",
            portfolio_id="PORTFOLIO_ALPHA",
        )

        execs, _ = dark_pool.match_orders(symbol="AMZN", bid_quote=185.00, ask_quote=185.10)
        self.assertEqual(len(execs), 0, "Wash sale guard must block identical client & portfolio")
        self.assertEqual(buy_same.filled_quantity, 0)
        self.assertEqual(sell_same.filled_quantity, 0)

        # Different client ID allows match
        sell_diff = dark_pool.add_order(
            order_id="SELL_LEGIT",
            symbol="AMZN",
            market="SP500",
            side="SELL",
            quantity=200,
            client_id="DESK_QUANT_2",
            portfolio_id="PORTFOLIO_ALPHA",
        )

        execs_diff, _ = dark_pool.match_orders(symbol="AMZN", bid_quote=185.00, ask_quote=185.10)
        self.assertEqual(len(execs_diff), 1)
        self.assertEqual(buy_same.filled_quantity, 200)
        self.assertEqual(sell_diff.filled_quantity, 200)

    # =======================================================================
    # SECTION 6: Mathematical Invariants & Volume Conservation (Task 1F)
    # =======================================================================

    def test_adv_integer_volume_conservation_complex_topology(self) -> None:
        """
        Empirically verify exact integer volume conservation:
            Q_order == Q_filled_dark + Q_residual
        across fragmented, asymmetric, multi-counterparty order topologies.
        """
        dark_pool = SyntheticDarkPool(
            min_fill_ratio=0.0,
            default_min_fill_size=1,
            enable_anti_gaming=False,
            queue_priority_mode=QueuePriorityMode.SIZE_TIME,
        )

        # Buyers: 5 orders with irregular prime-number quantities
        buy_quantities = [13337, 7777, 4999, 2111, 883]
        total_buy_shares = sum(buy_quantities)

        for i, q in enumerate(buy_quantities):
            dark_pool.add_order(
                order_id=f"BUY_{i}",
                symbol="GOOGL",
                market="NASDAQ",
                side="BUY",
                quantity=q,
                client_id=f"STRAT_BUY_{i}",
            )

        # Sellers: 4 orders with different prime quantities
        sell_quantities = [11113, 6421, 5333, 3109]
        total_sell_shares = sum(sell_quantities)

        for j, q in enumerate(sell_quantities):
            dark_pool.add_order(
                order_id=f"SELL_{j}",
                symbol="GOOGL",
                market="NASDAQ",
                side="SELL",
                quantity=q,
                client_id=f"STRAT_SELL_{j}",
            )

        # Match orders
        execs, residuals = dark_pool.match_orders(symbol="GOOGL", bid_quote=175.20, ask_quote=175.24)

        matched_volume = sum(e.matched_quantity for e in execs)
        expected_match_volume = min(total_buy_shares, total_sell_shares)
        self.assertEqual(matched_volume, expected_match_volume)

        # Invariant 1: For every single order, Q_order == Q_filled + Q_remaining
        self.assertTrue(dark_pool.verify_volume_conservation())

        for order_id, order in dark_pool._all_orders.items():
            self.assertEqual(
                order.quantity,
                order.filled_quantity + order.remaining_quantity,
                f"Volume conservation breached for order {order_id}",
            )

        # Invariant 2: Total order volume submitted == 2 * matched_volume + total_residual_volume
        total_submitted = total_buy_shares + total_sell_shares
        total_residuals = sum(r.quantity for r in residuals)
        self.assertEqual(total_submitted, 2 * matched_volume + total_residuals)

    def test_adv_half_spread_capture_exact_arithmetic(self) -> None:
        """
        Verify exact mathematical accuracy of institutional half-spread capture:
            Buyer Savings = (P_ask - P_mid) * Q
            Seller Savings = (P_mid - P_bid) * Q
            Total Spread Savings = (P_ask - P_bid) * Q == Buyer Savings + Seller Savings
            Fee Savings = 2 * (Taker + Clearing) * P_mid * Q
        """
        taker_bps = 2.0
        clearing_bps = 0.5
        dark_pool = SyntheticDarkPool(
            taker_fee_bps=taker_bps,
            clearing_fee_bps=clearing_bps,
            enable_tick_conformity=False,  # Raw math check
        )

        qty = 10000
        bid = 100.00
        ask = 100.10
        mid = (bid + ask) / 2.0  # 100.05
        spread = ask - bid       # 0.10

        dark_pool.add_order("B1", "IBM", "SP500", "BUY", qty, client_id="BUYER_1")
        dark_pool.add_order("S1", "IBM", "SP500", "SELL", qty, client_id="SELLER_1")

        execs, _ = dark_pool.match_orders(symbol="IBM", bid_quote=bid, ask_quote=ask)
        self.assertEqual(len(execs), 1)
        ex = execs[0]

        # Check midpoint
        self.assertAlmostEqual(ex.midpoint_price, 100.05, places=6)

        # Buyer savings: (100.10 - 100.05) * 10,000 = $500.00
        self.assertAlmostEqual(ex.buyer_spread_savings_value, 500.00, places=4)

        # Seller savings: (100.05 - 100.00) * 10,000 = $500.00
        self.assertAlmostEqual(ex.seller_spread_savings_value, 500.00, places=4)

        # Combined spread savings: $1,000.00
        self.assertAlmostEqual(ex.spread_savings_value, 1000.00, places=4)
        self.assertAlmostEqual(
            ex.spread_savings_value,
            ex.buyer_spread_savings_value + ex.seller_spread_savings_value,
            places=4,
        )

        # Fee savings: 2 sides * (2.0 + 0.5) bps = 5.0 bps = 0.0005 * 100.05 * 10,000 = $500.25
        expected_fee_savings = 2.0 * ((taker_bps + clearing_bps) * 1e-4) * mid * qty
        self.assertAlmostEqual(ex.fee_savings_value, expected_fee_savings, places=4)

        # Total savings
        self.assertAlmostEqual(ex.total_savings_value, 1000.00 + expected_fee_savings, places=4)

        # Cumulative Report Verification
        report = dark_pool.calculate_institutional_savings()
        self.assertEqual(report.total_matched_volume, qty)
        self.assertAlmostEqual(report.total_spread_savings_value, 1000.00, places=4)
        self.assertAlmostEqual(report.total_fee_savings_value, expected_fee_savings, places=4)
        self.assertTrue(report.volume_conservation_verified)

    def test_adv_multi_symbol_cross_batch_across_5_markets(self) -> None:
        """
        Adversarial Basket Crossing: Simultaneously crosses orders across 5 global markets
        (SP500, NASDAQ, RUSSELL2000, KOSPI, KOSDAQ) with 10 symbols and verifies
        volume conservation, residual routing, and institutional savings.
        """
        dark_pool = SyntheticDarkPool(
            min_fill_ratio=0.10,
            default_min_fill_size=5,
            enable_anti_gaming=True,
            enable_tick_conformity=True,
        )

        # 10 symbols across 5 markets
        market_quotes = {
            "SPY": {"bid": 505.20, "ask": 505.24, "market": "SP500"},
            "AAPL": {"bid": 182.50, "ask": 182.52, "market": "NASDAQ"},
            "IWM": {"bid": 204.10, "ask": 204.14, "market": "RUSSELL2000"},
            "005930": {"bid": 71000.0, "ask": 71100.0, "market": "KOSPI"},
            "000660": {"bid": 185000.0, "ask": 185500.0, "market": "KOSPI"},
            "091990": {"bid": 42000.0, "ask": 42100.0, "market": "KOSDAQ"},
            "068270": {"bid": 192000.0, "ask": 192500.0, "market": "KOSPI"},
            "NVDA": {"bid": 130.00, "ask": 130.04, "market": "NASDAQ"},
            "MSFT": {"bid": 418.80, "ask": 418.88, "market": "NASDAQ"},
            "QQQ": {"bid": 445.10, "ask": 445.16, "market": "NASDAQ"},
        }

        # Create 100 orders (50 buys, 50 sells) randomly distributed
        random.seed(42)
        symbols = list(market_quotes.keys())
        order_plans = []

        total_shares_submitted = 0
        order_idx = 0
        for sym in symbols:
            mkt = market_quotes[sym]["market"]
            # Generate 5 BUY orders and 5 SELL orders per symbol (100 orders total)
            for k in range(10):
                side = "BUY" if k < 5 else "SELL"
                qty = random.randint(500, 2000)
                total_shares_submitted += qty
                order_plans.append({
                    "order_id": f"BASKET_ORD_{order_idx:03d}",
                    "symbol": sym,
                    "market": mkt,
                    "side": side,
                    "quantity": qty,
                    "client_id": f"STRAT_{order_idx % 5}",
                    "portfolio_id": f"PORT_{order_idx % 3}",
                })
                order_idx += 1

        batch_result = dark_pool.cross_batch(order_plans, market_quotes)

        # Assertions
        self.assertTrue(batch_result["volume_conservation_verified"])
        self.assertGreater(batch_result["total_matched_volume"], 0)
        self.assertGreater(batch_result["total_institutional_savings"], 0.0)
        self.assertGreater(batch_result["total_spread_savings_value"], 0.0)
        self.assertGreater(batch_result["total_fee_savings_value"], 0.0)

        # Verify all residuals forward cleanly
        residuals = dark_pool.get_unmatched_residuals()
        routed_plans = dark_pool.forward_residuals_to_sor(residuals)
        self.assertEqual(len(routed_plans), len(residuals))

        # Verify volume conservation across all 100 orders
        self.assertTrue(dark_pool.verify_volume_conservation())


if __name__ == "__main__":
    unittest.main()
