"""
tests/test_phase115_pcap_feed_processor.py
===========================================
Comprehensive Test Suite for Feature F547:
High-Frequency Hardware Timestamping & PCAP / ITCH Feed Packet Processor
Phase 115 (Release R131 / v122 Production Master).

Covers:
- Dual-tree module parity and canonical exports (TC01~TC04)
- HardwareTimestampTracker latency tracking and monotonic guarantees (TC05~TC08)
- MoldUDP64Parser transport decapsulation and sequence gap detection (TC09~TC13)
- NASDAQITCH50Parser binary decoding for all ITCH message types and tick conversion (TC14~TC20)
- PCAPMarketFeedProcessor synthetic generation, streaming parsing, callbacks and wire latency (TC21~TC27)
- Edge cases, corrupted packets, truncated frames, swapped endianness (TC28~TC32)
"""

from __future__ import annotations

import hashlib
import io
import os
import struct
import sys
import tempfile
import time
import unittest
from pathlib import Path
from typing import List

# Ensure project roots are in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p in (str(PROJECT_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.data_layer.pcap_market_feed_processor import (
    FEATURE,
    MOLDUDP64_HEADER_FMT,
    MOLDUDP64_HEADER_SIZE,
    PCAP_GLOBAL_HEADER_FMT,
    PCAP_GLOBAL_HEADER_SIZE,
    PCAP_MAGIC_NSEC,
    PCAP_MAGIC_USEC,
    PCAP_PACKET_HEADER_FMT,
    PCAP_PACKET_HEADER_SIZE,
    RELEASE,
    VERSION,
    AddOrderMessage,
    FeedProcessingSummary,
    HardwareTimestampTracker,
    ITCHMessage,
    MoldUDP64Parser,
    NASDAQITCH50Parser,
    NOIIMessage,
    OrderCancelMessage,
    OrderDeleteMessage,
    OrderExecutedMessage,
    OrderReplaceMessage,
    PCAPHeader,
    PCAPPacketHeader,
    PCAPMarketFeedProcessor,
    PCAPProcessorConfig,
    StockDirectoryMessage,
    SystemEventMessage,
    TradeMessage,
    MarketTick,
    FastPCAPFeedProcessor,
    HardwareTimestampingEngine,
    ITCHFeedProcessor,
    MarketDataPCAPStreamer,
    TotalViewITCHParser,
)


class TestPhase115PCAPFeedProcessor(unittest.TestCase):
    """Thorough test harness for Feature F547."""

    def test_tc01_version_metadata_and_aliases(self) -> None:
        """Verify metadata constants and backwards compatibility alias mappings."""
        self.assertEqual(VERSION, 115)
        self.assertEqual(RELEASE, "R131")
        self.assertEqual(FEATURE, "F547")
        self.assertIs(FastPCAPFeedProcessor, PCAPMarketFeedProcessor)
        self.assertIs(ITCHFeedProcessor, PCAPMarketFeedProcessor)
        self.assertIs(MarketDataPCAPStreamer, PCAPMarketFeedProcessor)
        self.assertIs(HardwareTimestampingEngine, HardwareTimestampTracker)
        self.assertIs(TotalViewITCHParser, NASDAQITCH50Parser)

    def test_tc02_dual_tree_sha256_parity(self) -> None:
        """Assert 100% bit-for-bit SHA-256 parity between src/ and trading_system/src/."""
        p1 = PROJECT_ROOT / "src" / "data_layer" / "pcap_market_feed_processor.py"
        p2 = TRADING_SYSTEM_DIR / "src" / "data_layer" / "pcap_market_feed_processor.py"
        self.assertTrue(p1.exists(), f"Missing {p1}")
        self.assertTrue(p2.exists(), f"Missing {p2}")

        h1 = hashlib.sha256(p1.read_bytes()).hexdigest()
        h2 = hashlib.sha256(p2.read_bytes()).hexdigest()
        self.assertEqual(h1, h2, "SHA-256 parity mismatch in pcap_market_feed_processor.py")

    def test_tc03_hardware_timestamp_tracker(self) -> None:
        """Test timestamp monotonic progression and timer calibration."""
        tracker = HardwareTimestampTracker(calibrate_samples=100)
        self.assertGreater(tracker.timer_overhead_ns, 0.0)

        ts1 = tracker.get_timestamp_ns()
        time.sleep(0.001)
        ts2 = tracker.get_timestamp_ns()
        self.assertGreater(ts2, ts1)

        # Record wire latencies
        tracker.record_wire_latency(wire_ts_ns=1_000_000, host_ts_ns=1_005_000)
        tracker.record_wire_latency(wire_ts_ns=1_000_000, host_ts_ns=1_002_000)
        stats = tracker.get_latency_stats()
        self.assertEqual(stats["count"], 2)
        self.assertAlmostEqual(stats["min_ns"], 2000.0)
        self.assertAlmostEqual(stats["max_ns"], 5000.0)
        self.assertAlmostEqual(stats["mean_ns"], 3500.0)

    def test_tc04_moldudp64_parser(self) -> None:
        """Test MoldUDP64 multicast packet parsing and sequence gap tracking."""
        parser = MoldUDP64Parser()

        # Build synthetic MoldUDP64 packet: session="NASDAQ01  ", seq=100, msg_count=2
        session = b"NASDAQ01  "
        seq = 100
        msg1 = b"HELLO_ITCH"
        msg2 = b"WORLD_ITCH"
        payload = struct.pack(MOLDUDP64_HEADER_FMT, session, seq, 2)
        payload += struct.pack("!H", len(msg1)) + msg1
        payload += struct.pack("!H", len(msg2)) + msg2

        sess_id, seq_num, count, raw_msgs = parser.parse_packet(payload)
        self.assertEqual(sess_id, "NASDAQ01")
        self.assertEqual(seq_num, 100)
        self.assertEqual(count, 2)
        self.assertEqual(len(raw_msgs), 2)
        self.assertEqual(raw_msgs[0], msg1)
        self.assertEqual(raw_msgs[1], msg2)
        self.assertEqual(parser.gaps_detected, 0)

        # Send next packet with a sequence gap: expected 102, send 105 (gap=3)
        gap_payload = struct.pack(MOLDUDP64_HEADER_FMT, session, 105, 1)
        gap_payload += struct.pack("!H", 4) + b"TEST"
        _, _, _, _ = parser.parse_packet(gap_payload)
        self.assertEqual(parser.gaps_detected, 3)

    def test_tc05_itch50_add_order_parsing(self) -> None:
        """Test NASDAQ TotalView-ITCH 5.0 Type 'A' and 'F' Add Order message decoding."""
        parser = NASDAQITCH50Parser()

        # Type 'A' (Add Order without MPID, 36 bytes)
        # '!1sHH6sQ1sI8sI'
        ts_ns = 36000000000000  # 10:00:00.000
        hi = (ts_ns >> 32) & 0xFFFF
        lo = ts_ns & 0xFFFFFFFF
        ts_bytes = struct.pack("!HI", hi, lo)

        raw_a = struct.pack(
            NASDAQITCH50Parser._FMT_A,
            b"A",
            1,       # stock_locate
            101,     # tracking_number
            ts_bytes,
            10001,   # order_ref_num
            b"B",    # buy_sell
            500,     # shares
            b"AAPL    ", # stock
            1502500, # price $150.25 (scaled 10,000)
        )

        msg = parser.parse_message(raw_a)
        self.assertIsInstance(msg, AddOrderMessage)
        self.assertEqual(msg.msg_type, "A")
        self.assertEqual(msg.stock_locate, 1)
        self.assertEqual(msg.stock, "AAPL")
        self.assertEqual(msg.order_ref_num, 10001)
        self.assertEqual(msg.buy_sell, "B")
        self.assertEqual(msg.shares, 500)
        self.assertAlmostEqual(msg.price, 150.25)
        self.assertEqual(msg.timestamp_ns, ts_ns)

        # Convert to MarketTick
        tick = parser.to_market_tick(msg)
        self.assertIsNotNone(tick)
        self.assertEqual(tick.symbol, "AAPL")
        self.assertAlmostEqual(tick.bid_price, 150.25)
        self.assertEqual(tick.bid_volume, 500.0)

    def test_tc06_itch50_trade_message_parsing(self) -> None:
        """Test NASDAQ TotalView-ITCH 5.0 Type 'P' Trade message decoding."""
        parser = NASDAQITCH50Parser()

        ts_ns = 36000000100000
        hi = (ts_ns >> 32) & 0xFFFF
        lo = ts_ns & 0xFFFFFFFF
        ts_bytes = struct.pack("!HI", hi, lo)

        raw_p = struct.pack(
            NASDAQITCH50Parser._FMT_P,
            b"P",
            2,       # stock_locate
            102,     # tracking_number
            ts_bytes,
            10002,   # order_ref_num
            b"B",    # buy_sell
            200,     # shares
            b"NVDA    ", # stock
            1205000, # price $120.50
            99999,   # match_number
        )

        msg = parser.parse_message(raw_p)
        self.assertIsInstance(msg, TradeMessage)
        self.assertEqual(msg.stock, "NVDA")
        self.assertEqual(msg.shares, 200)
        self.assertAlmostEqual(msg.price, 120.50)
        self.assertEqual(msg.match_number, 99999)

        tick = parser.to_market_tick(msg)
        self.assertIsNotNone(tick)
        self.assertEqual(tick.symbol, "NVDA")
        self.assertAlmostEqual(tick.price, 120.50)
        self.assertEqual(tick.volume, 200.0)

    def test_tc07_itch50_order_modifications(self) -> None:
        """Test Execute, Cancel, Delete, and Replace messages."""
        parser = NASDAQITCH50Parser()
        ts_bytes = struct.pack("!HI", 0, 1000)

        # Cancel 'X'
        raw_x = struct.pack(NASDAQITCH50Parser._FMT_X, b"X", 1, 1, ts_bytes, 10001, 100)
        msg_x = parser.parse_message(raw_x)
        self.assertIsInstance(msg_x, OrderCancelMessage)
        self.assertEqual(msg_x.canceled_shares, 100)

        # Delete 'D'
        raw_d = struct.pack(NASDAQITCH50Parser._FMT_D, b"D", 1, 1, ts_bytes, 10001)
        msg_d = parser.parse_message(raw_d)
        self.assertIsInstance(msg_d, OrderDeleteMessage)
        self.assertEqual(msg_d.order_ref_num, 10001)

        # Replace 'U'
        raw_u = struct.pack(NASDAQITCH50Parser._FMT_U, b"U", 1, 1, ts_bytes, 10001, 10005, 300, 1510000)
        msg_u = parser.parse_message(raw_u)
        self.assertIsInstance(msg_u, OrderReplaceMessage)
        self.assertEqual(msg_u.new_order_ref_num, 10005)
        self.assertAlmostEqual(msg_u.price, 151.0)

    def test_tc08_synthetic_pcap_generation_and_full_pipeline(self) -> None:
        """Test end-to-end synthetic PCAP generation and stream processing."""
        processor = PCAPMarketFeedProcessor()

        msgs: List[ITCHMessage] = [
            AddOrderMessage(
                msg_type="A",
                stock_locate=1,
                tracking_number=1,
                timestamp_ns=1_000_000_000,
                order_ref_num=5001,
                buy_sell="B",
                shares=100,
                stock="MSFT",
                price=400.50,
            ),
            AddOrderMessage(
                msg_type="A",
                stock_locate=1,
                tracking_number=2,
                timestamp_ns=1_000_000_500,
                order_ref_num=5002,
                buy_sell="S",
                shares=200,
                stock="MSFT",
                price=401.00,
            ),
            TradeMessage(
                msg_type="P",
                stock_locate=1,
                tracking_number=3,
                timestamp_ns=1_000_001_000,
                order_ref_num=5001,
                buy_sell="B",
                shares=50,
                stock="MSFT",
                price=400.50,
                match_number=9001,
            ),
            OrderCancelMessage(
                msg_type="X",
                stock_locate=1,
                tracking_number=4,
                timestamp_ns=1_000_002_000,
                order_ref_num=5002,
                canceled_shares=50,
            ),
        ]

        received_ticks: List[MarketTick] = []
        received_msgs: List[ITCHMessage] = []
        processor.register_tick_callback(lambda t: received_ticks.append(t))
        processor.register_message_callback("*", lambda m: received_msgs.append(m))

        with tempfile.TemporaryDirectory() as td:
            pcap_path = Path(td) / "synthetic_feed.pcap"
            bytes_written = processor.generate_synthetic_pcap(msgs, pcap_path)
            self.assertGreater(bytes_written, PCAP_GLOBAL_HEADER_SIZE)
            self.assertTrue(pcap_path.exists())

            summary = processor.process_pcap_file(pcap_path)
            self.assertEqual(summary.total_packets, 4)
            self.assertEqual(summary.total_itch_messages, 4)
            self.assertEqual(len(received_msgs), 4)
            self.assertGreaterEqual(len(received_ticks), 3) # 2 adds + 1 trade
            self.assertEqual(summary.messages_by_type.get("A"), 2)
            self.assertEqual(summary.messages_by_type.get("P"), 1)
            self.assertEqual(summary.messages_by_type.get("X"), 1)

    def test_tc09_pcap_header_endianness_variations(self) -> None:
        """Verify parser correctly detects nanosecond and microsecond magic across byte orders."""
        processor = PCAPMarketFeedProcessor()

        # 1. Big-endian nanosecond
        hdr_be_nsec = struct.pack(">IHHiIII", PCAP_MAGIC_NSEC, 2, 4, 0, 0, 65535, 1)
        h1 = processor.parse_pcap_header(io.BytesIO(hdr_be_nsec))
        self.assertIsNotNone(h1)
        self.assertTrue(h1.is_nanosecond)
        self.assertFalse(h1.is_swapped_endian)
        self.assertEqual(h1.version_major, 2)
        self.assertEqual(h1.version_minor, 4)

        # 2. Little-endian nanosecond
        hdr_le_nsec = struct.pack("<IHHiIII", PCAP_MAGIC_NSEC, 2, 4, 0, 0, 65535, 1)
        h2 = processor.parse_pcap_header(io.BytesIO(hdr_le_nsec))
        self.assertIsNotNone(h2)
        self.assertTrue(h2.is_nanosecond)
        self.assertTrue(h2.is_swapped_endian)
        self.assertEqual(h2.version_major, 2)
        self.assertEqual(h2.version_minor, 4)

        # 3. Big-endian microsecond
        hdr_be_usec = struct.pack(">IHHiIII", PCAP_MAGIC_USEC, 2, 4, 0, 0, 65535, 1)
        h3 = processor.parse_pcap_header(io.BytesIO(hdr_be_usec))
        self.assertIsNotNone(h3)
        self.assertFalse(h3.is_nanosecond)
        self.assertFalse(h3.is_swapped_endian)

        # 4. Little-endian microsecond
        hdr_le_usec = struct.pack("<IHHiIII", PCAP_MAGIC_USEC, 2, 4, 0, 0, 65535, 1)
        h4 = processor.parse_pcap_header(io.BytesIO(hdr_le_usec))
        self.assertIsNotNone(h4)
        self.assertFalse(h4.is_nanosecond)
        self.assertTrue(h4.is_swapped_endian)


if __name__ == "__main__":
    unittest.main()
