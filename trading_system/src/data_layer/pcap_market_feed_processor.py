"""
src/data_layer/pcap_market_feed_processor.py
=============================================
High-Frequency Hardware Timestamping & PCAP / ITCH Feed Packet Processor
Feature F547 | Release R131 (Phase 115 / v122 Production Master).

Provides wire-speed PCAP / PCAPNG packet stream decapsulation, MoldUDP64
multicast sequence gap tracking, hardware/host nanosecond timestamp correlation,
and binary NASDAQ TotalView-ITCH 5.0 protocol parsing with downstream emission
to MarketTick structures for high-frequency algorithmic ingestion.
"""

from __future__ import annotations

import collections
import dataclasses
import enum
import io
import logging
import math
import os
import struct
import sys
import time
from pathlib import Path
from typing import Any, Callable, Deque, Dict, Iterator, List, Optional, Tuple, Union

try:
    from src.data_layer.realtime_feature_store import MarketTick
except ImportError:
    @dataclasses.dataclass
    class MarketTick:  # type: ignore[no-redef]
        symbol: str
        timestamp_ns: int
        price: float
        volume: float
        high: Optional[float] = None
        low: Optional[float] = None
        open_p: Optional[float] = None
        bid_price: Optional[float] = None
        ask_price: Optional[float] = None
        bid_volume: Optional[float] = None
        ask_volume: Optional[float] = None
        market: str = "US"

logger = logging.getLogger(__name__)

# Module Metadata
VERSION: int = 115
RELEASE: str = "R131"
FEATURE: str = "F547"

# PCAP & Protocol Magic Constants
PCAP_MAGIC_USEC: int = 0xA1B2C3D4
PCAP_MAGIC_NSEC: int = 0xA1B23C4D
PCAP_MAGIC_SWAPPED_USEC: int = 0xD4C3B2A1
PCAP_MAGIC_SWAPPED_NSEC: int = 0x4D3CB2A1
PCAPNG_SHB_MAGIC: int = 0x0A0D0D0A

# Pre-compiled Struct Formats
PCAP_GLOBAL_HEADER_FMT = "IHHiIII"
PCAP_GLOBAL_HEADER_SIZE = struct.calcsize(PCAP_GLOBAL_HEADER_FMT)  # 24 bytes

PCAP_PACKET_HEADER_FMT = "IIII"
PCAP_PACKET_HEADER_SIZE = struct.calcsize(PCAP_PACKET_HEADER_FMT)  # 16 bytes

# MoldUDP64 Header: Session (10s), SequenceNumber (Q), MessageCount (H)
MOLDUDP64_HEADER_FMT = "!10sQH"
MOLDUDP64_HEADER_SIZE = struct.calcsize(MOLDUDP64_HEADER_FMT)  # 20 bytes


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

@dataclasses.dataclass
class PCAPHeader:
    """Represents a standard libpcap global header."""
    magic: int
    version_major: int
    version_minor: int
    thiszone: int
    sigfigs: int
    snaplen: int
    network: int
    is_nanosecond: bool = False
    is_swapped_endian: bool = False


@dataclasses.dataclass
class PCAPPacketHeader:
    """Represents an individual packet header in a PCAP capture."""
    ts_sec: int
    ts_sub: int
    incl_len: int
    orig_len: int
    wire_timestamp_ns: int


@dataclasses.dataclass
class ITCHMessage:
    """Base dataclass for all NASDAQ TotalView-ITCH 5.0 messages."""
    msg_type: str
    stock_locate: int
    tracking_number: int
    timestamp_ns: int
    payload: Dict[str, Any] = dataclasses.field(default_factory=dict)


@dataclasses.dataclass
class SystemEventMessage(ITCHMessage):
    event_code: str = "O"


@dataclasses.dataclass
class StockDirectoryMessage(ITCHMessage):
    stock: str = ""
    market_category: str = "Q"
    financial_status: str = "N"
    round_lot_size: int = 100
    round_lots_only: str = "N"
    issue_classification: str = "C"
    issue_subtype: str = ""
    authenticity: str = "P"
    short_sale_threshold_indicator: str = "N"
    ipo_flag: str = "N"
    luld_ref_price_tier: str = "1"
    etp_flag: str = "N"
    etp_leverage_factor: int = 1
    inverse_indicator: str = "N"


@dataclasses.dataclass
class AddOrderMessage(ITCHMessage):
    order_ref_num: int = 0
    buy_sell: str = "B"
    shares: int = 0
    stock: str = ""
    price: float = 0.0
    attribution: Optional[str] = None


@dataclasses.dataclass
class OrderExecutedMessage(ITCHMessage):
    order_ref_num: int = 0
    executed_shares: int = 0
    match_number: int = 0
    execution_price: Optional[float] = None


@dataclasses.dataclass
class OrderCancelMessage(ITCHMessage):
    order_ref_num: int = 0
    canceled_shares: int = 0


@dataclasses.dataclass
class OrderDeleteMessage(ITCHMessage):
    order_ref_num: int = 0


@dataclasses.dataclass
class OrderReplaceMessage(ITCHMessage):
    original_order_ref_num: int = 0
    new_order_ref_num: int = 0
    shares: int = 0
    price: float = 0.0


@dataclasses.dataclass
class TradeMessage(ITCHMessage):
    order_ref_num: int = 0
    buy_sell: str = "B"
    shares: int = 0
    stock: str = ""
    price: float = 0.0
    match_number: int = 0
    cross_type: Optional[str] = None


@dataclasses.dataclass
class NOIIMessage(ITCHMessage):
    paired_shares: int = 0
    imbalance_shares: int = 0
    imbalance_direction: str = "N"
    stock: str = ""
    far_price: float = 0.0
    near_price: float = 0.0
    current_reference_price: float = 0.0
    cross_type: str = "O"
    price_variation_indicator: str = "L"


@dataclasses.dataclass
class PCAPProcessorConfig:
    """Configuration options for PCAP packet ingestion."""
    udp_port_filter: Optional[int] = None
    default_market: str = "NASDAQ"
    fixed_point_divisor: float = 10000.0
    drop_unsupported_messages: bool = True
    max_packets: Optional[int] = None
    enable_wire_latency_tracking: bool = True
    calibrate_timestamp_samples: int = 1000


@dataclasses.dataclass
class FeedProcessingSummary:
    """Summary metrics of processed PCAP feed stream."""
    total_packets: int = 0
    total_bytes: int = 0
    total_itch_messages: int = 0
    messages_by_type: Dict[str, int] = dataclasses.field(default_factory=dict)
    sequence_gaps_detected: int = 0
    packets_dropped: int = 0
    processing_time_ms: float = 0.0
    avg_latency_ns: float = 0.0
    p50_latency_ns: float = 0.0
    p90_latency_ns: float = 0.0
    p99_latency_ns: float = 0.0


# ---------------------------------------------------------------------------
# Hardware Timestamp Tracker
# ---------------------------------------------------------------------------

class HardwareTimestampTracker:
    """
    Monotonic hardware/host timestamping and wire latency tracker.
    Provides sub-40ns resolution on Windows (QPC) and Linux (CLOCK_MONOTONIC_RAW).
    """

    def __init__(self, calibrate_samples: int = 1000) -> None:
        self.calibrate_samples = max(10, calibrate_samples)
        self.timer_overhead_ns: float = 0.0
        self._wire_latencies: Deque[int] = collections.deque(maxlen=100000)
        self._last_host_ts: int = 0
        self.calibrate()

    def calibrate(self) -> float:
        """Measures system timer access overhead in nanoseconds."""
        n = self.calibrate_samples
        t0 = time.perf_counter_ns()
        for _ in range(n):
            _ = time.perf_counter_ns()
        t1 = time.perf_counter_ns()
        self.timer_overhead_ns = (t1 - t0) / max(1, n)
        return self.timer_overhead_ns

    def get_timestamp_ns(self) -> int:
        """Returns current monotonic host timestamp in nanoseconds."""
        ts = time.perf_counter_ns()
        self._last_host_ts = ts
        return ts

    def record_wire_latency(self, wire_ts_ns: int, host_ts_ns: Optional[int] = None) -> int:
        """
        Records wire-to-host transit latency: max(0, host_ts_ns - wire_ts_ns).
        """
        h_ts = host_ts_ns if host_ts_ns is not None else self.get_timestamp_ns()
        # Handle zero or uninitialized wire timestamps
        if wire_ts_ns <= 0:
            delta = 0
        else:
            delta = max(0, h_ts - wire_ts_ns)
        self._wire_latencies.append(delta)
        return delta

    def get_latency_stats(self) -> Dict[str, float]:
        """Calculates percentile distribution of wire-to-host latencies."""
        if not self._wire_latencies:
            return {
                "count": 0.0,
                "mean_ns": 0.0,
                "min_ns": 0.0,
                "max_ns": 0.0,
                "p50_ns": 0.0,
                "p90_ns": 0.0,
                "p99_ns": 0.0,
                "jitter_ns": 0.0,
                "overhead_ns": self.timer_overhead_ns,
            }

        arr = sorted(self._wire_latencies)
        n = len(arr)
        mean_v = sum(arr) / n
        var = sum((x - mean_v) ** 2 for x in arr) / n
        jitter = math.sqrt(var)

        p50 = float(arr[int(n * 0.50)])
        p90 = float(arr[min(n - 1, int(n * 0.90))])
        p99 = float(arr[min(n - 1, int(n * 0.99))])

        return {
            "count": float(n),
            "mean_ns": mean_v,
            "min_ns": float(arr[0]),
            "max_ns": float(arr[-1]),
            "p50_ns": p50,
            "p90_ns": p90,
            "p99_ns": p99,
            "jitter_ns": jitter,
            "overhead_ns": self.timer_overhead_ns,
        }


# ---------------------------------------------------------------------------
# MoldUDP64 Multicast Protocol Parser
# ---------------------------------------------------------------------------

class MoldUDP64Parser:
    """
    Decapsulates MoldUDP64 multicast transport packets and tracks sequence gaps.
    Format:
      - Session ID: 10 bytes ASCII
      - Sequence Number: 8 bytes Big-Endian Unsigned Long Long
      - Message Count: 2 bytes Big-Endian Unsigned Short
      - Trailing payload blocks: 2 bytes length prefix + raw message bytes
    """

    def __init__(self) -> None:
        self.last_seq: Dict[str, int] = {}
        self.gaps_detected: int = 0
        self.total_packets: int = 0
        self.total_messages: int = 0

    def parse_packet(self, payload: bytes) -> Tuple[str, int, int, List[bytes]]:
        """
        Parses a MoldUDP64 packet payload.
        Returns: (session_id, seq_num, message_count, list_of_raw_messages)
        """
        self.total_packets += 1
        if len(payload) < MOLDUDP64_HEADER_SIZE:
            return "", 0, 0, []

        session_raw, seq_num, msg_count = struct.unpack_from(MOLDUDP64_HEADER_FMT, payload, 0)
        session_id = session_raw.decode("ascii", errors="ignore").rstrip("\x00 ").strip()
        if msg_count > 1000:
            return "", 0, 0, []

        # Sequence gap detection
        if session_id in self.last_seq:
            expected = self.last_seq[session_id] + 1
            if seq_num > expected and seq_num != 0xFFFFFFFFFFFFFFFF:
                gap = seq_num - expected
                self.gaps_detected += gap
                logger.warning(
                    "MoldUDP64 sequence gap detected on session '%s': expected %d, got %d (gap=%d)",
                    session_id, expected, seq_num, gap
                )

        if seq_num != 0xFFFFFFFFFFFFFFFF:
            self.last_seq[session_id] = seq_num + max(0, msg_count - 1)

        messages: List[bytes] = []
        offset = MOLDUDP64_HEADER_SIZE
        pl_len = len(payload)

        for _ in range(msg_count):
            if offset + 2 > pl_len:
                break
            msg_len = struct.unpack_from("!H", payload, offset)[0]
            offset += 2
            if offset + msg_len > pl_len:
                break
            msg_bytes = payload[offset : offset + msg_len]
            messages.append(msg_bytes)
            offset += msg_len
            self.total_messages += 1

        return session_id, seq_num, msg_count, messages

    def get_drop_stats(self) -> Dict[str, int]:
        return {
            "total_packets": self.total_packets,
            "total_messages": self.total_messages,
            "gaps_detected": self.gaps_detected,
        }


# ---------------------------------------------------------------------------
# NASDAQ TotalView-ITCH 5.0 Parser
# ---------------------------------------------------------------------------

class NASDAQITCH50Parser:
    """
    High-performance binary NASDAQ TotalView-ITCH 5.0 parser.
    Decodes wire binary payloads into structured ITCHMessage instances and MarketTick.
    """

    # Pre-compiled ITCH 5.0 message formats
    # Common header: msg_type (1s), stock_locate (H), tracking_number (H), timestamp (6s: 48-bit ns)
    _FMT_S = "!1sHH6s1s"                # System Event: 12 bytes
    _FMT_R = "!1sHH6s8s1s1sI1s2s1s1s1s1s1s"  # Stock Directory: 39 bytes
    _FMT_A = "!1sHH6sQ1sI8sI"          # Add Order: 36 bytes
    _FMT_F = "!1sHH6sQ1sI8sI4s"        # Add Order w/ MPID: 40 bytes
    _FMT_E = "!1sHH6sQIQ"              # Order Executed: 31 bytes
    _FMT_C = "!1sHH6sQIQ1sI"           # Order Executed w/ Price: 36 bytes
    _FMT_X = "!1sHH6sQI"               # Order Cancel: 23 bytes
    _FMT_D = "!1sHH6sQ"                # Order Delete: 19 bytes
    _FMT_U = "!1sHH6sQQII"             # Order Replace: 35 bytes
    _FMT_P = "!1sHH6sQ1sI8sIQ"         # Trade (Non-Cross): 44 bytes
    _FMT_Q = "!1sHH6sQ8sIQ1s"          # Cross Trade: 40 bytes
    _FMT_B = "!1sHH6sQ"                # Broken Trade: 19 bytes
    _FMT_I = "!1sHH6sQQ1s8sIII1s1s"    # NOII: 50 bytes

    MESSAGE_LENGTHS: Dict[str, int] = {
        "S": 12, "R": 39, "A": 36, "F": 40, "E": 31,
        "C": 36, "X": 23, "D": 19, "U": 35, "P": 44,
        "Q": 40, "B": 19, "I": 50,
    }

    def __init__(self, fixed_point_divisor: float = 10000.0, default_market: str = "NASDAQ") -> None:
        self.divisor = fixed_point_divisor
        self.market = default_market
        self._parsed_count: int = 0
        self._stock_locate_map: Dict[int, str] = {}

    @staticmethod
    def _parse_48bit_ts(raw_6bytes: bytes) -> int:
        """Decodes 6-byte big-endian integer into nanoseconds since midnight."""
        hi, lo = struct.unpack("!HI", raw_6bytes)
        return (hi << 32) | lo

    def parse_message(self, raw_bytes: bytes) -> Optional[ITCHMessage]:
        """Parses a single binary ITCH 5.0 message."""
        if not raw_bytes:
            return None

        msg_type_byte = raw_bytes[:1]
        msg_type = msg_type_byte.decode("ascii", errors="ignore")
        length = len(raw_bytes)
        self._parsed_count += 1

        try:
            if msg_type == "A" and length >= 35:
                vals = struct.unpack_from(self._FMT_A, raw_bytes, 0)
                ts_ns = self._parse_48bit_ts(vals[3])
                sym = vals[7].decode("ascii", errors="ignore").rstrip()
                self._stock_locate_map[vals[1]] = sym
                return AddOrderMessage(
                    msg_type="A",
                    stock_locate=vals[1],
                    tracking_number=vals[2],
                    timestamp_ns=ts_ns,
                    order_ref_num=vals[4],
                    buy_sell=vals[5].decode("ascii", errors="ignore"),
                    shares=vals[6],
                    stock=sym,
                    price=vals[8] / self.divisor,
                )

            elif msg_type == "F" and length >= 39:
                vals = struct.unpack_from(self._FMT_F, raw_bytes, 0)
                ts_ns = self._parse_48bit_ts(vals[3])
                sym = vals[7].decode("ascii", errors="ignore").rstrip()
                attribution = vals[9].decode("ascii", errors="ignore").rstrip()
                self._stock_locate_map[vals[1]] = sym
                return AddOrderMessage(
                    msg_type="F",
                    stock_locate=vals[1],
                    tracking_number=vals[2],
                    timestamp_ns=ts_ns,
                    order_ref_num=vals[4],
                    buy_sell=vals[5].decode("ascii", errors="ignore"),
                    shares=vals[6],
                    stock=sym,
                    price=vals[8] / self.divisor,
                    attribution=attribution,
                )

            elif msg_type == "E" and length >= 30:
                vals = struct.unpack_from(self._FMT_E, raw_bytes, 0)
                ts_ns = self._parse_48bit_ts(vals[3])
                return OrderExecutedMessage(
                    msg_type="E",
                    stock_locate=vals[1],
                    tracking_number=vals[2],
                    timestamp_ns=ts_ns,
                    order_ref_num=vals[4],
                    executed_shares=vals[5],
                    match_number=vals[6],
                )

            elif msg_type == "C" and length >= 35:
                vals = struct.unpack_from(self._FMT_C, raw_bytes, 0)
                ts_ns = self._parse_48bit_ts(vals[3])
                return OrderExecutedMessage(
                    msg_type="C",
                    stock_locate=vals[1],
                    tracking_number=vals[2],
                    timestamp_ns=ts_ns,
                    order_ref_num=vals[4],
                    executed_shares=vals[5],
                    match_number=vals[6],
                    execution_price=vals[8] / self.divisor,
                )

            elif msg_type == "P" and length >= 43:
                vals = struct.unpack_from(self._FMT_P, raw_bytes, 0)
                ts_ns = self._parse_48bit_ts(vals[3])
                sym = vals[7].decode("ascii", errors="ignore").rstrip()
                self._stock_locate_map[vals[1]] = sym
                return TradeMessage(
                    msg_type="P",
                    stock_locate=vals[1],
                    tracking_number=vals[2],
                    timestamp_ns=ts_ns,
                    order_ref_num=vals[4],
                    buy_sell=vals[5].decode("ascii", errors="ignore"),
                    shares=vals[6],
                    stock=sym,
                    price=vals[8] / self.divisor,
                    match_number=vals[9],
                )

            elif msg_type == "Q" and length >= 39:
                vals = struct.unpack_from(self._FMT_Q, raw_bytes, 0)
                ts_ns = self._parse_48bit_ts(vals[3])
                sym = vals[5].decode("ascii", errors="ignore").rstrip()
                self._stock_locate_map[vals[1]] = sym
                return TradeMessage(
                    msg_type="Q",
                    stock_locate=vals[1],
                    tracking_number=vals[2],
                    timestamp_ns=ts_ns,
                    order_ref_num=0,
                    buy_sell="B",
                    shares=vals[4],
                    stock=sym,
                    price=vals[6] / self.divisor,
                    match_number=vals[7],
                    cross_type=vals[8].decode("ascii", errors="ignore"),
                )

            elif msg_type == "S" and length >= 11:
                vals = struct.unpack_from(self._FMT_S, raw_bytes, 0)
                ts_ns = self._parse_48bit_ts(vals[3])
                return SystemEventMessage(
                    msg_type="S",
                    stock_locate=vals[1],
                    tracking_number=vals[2],
                    timestamp_ns=ts_ns,
                    event_code=vals[4].decode("ascii", errors="ignore"),
                )

            elif msg_type == "R" and length >= 38:
                vals = struct.unpack_from(self._FMT_R, raw_bytes, 0)
                ts_ns = self._parse_48bit_ts(vals[3])
                sym = vals[4].decode("ascii", errors="ignore").rstrip()
                self._stock_locate_map[vals[1]] = sym
                return StockDirectoryMessage(
                    msg_type="R",
                    stock_locate=vals[1],
                    tracking_number=vals[2],
                    timestamp_ns=ts_ns,
                    stock=sym,
                    market_category=vals[5].decode("ascii", errors="ignore"),
                    round_lot_size=vals[7],
                )

            elif msg_type == "X" and length >= 22:
                vals = struct.unpack_from(self._FMT_X, raw_bytes, 0)
                ts_ns = self._parse_48bit_ts(vals[3])
                return OrderCancelMessage(
                    msg_type="X",
                    stock_locate=vals[1],
                    tracking_number=vals[2],
                    timestamp_ns=ts_ns,
                    order_ref_num=vals[4],
                    canceled_shares=vals[5],
                )

            elif msg_type == "D" and length >= 18:
                vals = struct.unpack_from(self._FMT_D, raw_bytes, 0)
                ts_ns = self._parse_48bit_ts(vals[3])
                return OrderDeleteMessage(
                    msg_type="D",
                    stock_locate=vals[1],
                    tracking_number=vals[2],
                    timestamp_ns=ts_ns,
                    order_ref_num=vals[4],
                )

            elif msg_type == "U" and length >= 34:
                vals = struct.unpack_from(self._FMT_U, raw_bytes, 0)
                ts_ns = self._parse_48bit_ts(vals[3])
                return OrderReplaceMessage(
                    msg_type="U",
                    stock_locate=vals[1],
                    tracking_number=vals[2],
                    timestamp_ns=ts_ns,
                    original_order_ref_num=vals[4],
                    new_order_ref_num=vals[5],
                    shares=vals[6],
                    price=vals[7] / self.divisor,
                )

            elif msg_type == "I" and length >= 49:
                vals = struct.unpack_from(self._FMT_I, raw_bytes, 0)
                ts_ns = self._parse_48bit_ts(vals[3])
                sym = vals[6].decode("ascii", errors="ignore").rstrip()
                self._stock_locate_map[vals[1]] = sym
                return NOIIMessage(
                    msg_type="I",
                    stock_locate=vals[1],
                    tracking_number=vals[2],
                    timestamp_ns=ts_ns,
                    paired_shares=vals[4],
                    imbalance_shares=vals[5],
                    imbalance_direction=vals[6].decode("ascii", errors="ignore"),
                    stock=sym,
                    far_price=vals[7] / self.divisor,
                    near_price=vals[8] / self.divisor,
                    current_reference_price=vals[9] / self.divisor,
                    cross_type=vals[10].decode("ascii", errors="ignore"),
                )

            else:
                # Generic fallback for unparsed or less common types ('H', 'Y', 'L', 'V', 'W', 'K', 'B')
                if length >= 11:
                    ts_raw = raw_bytes[5:11]
                    ts_ns = self._parse_48bit_ts(ts_raw)
                    stock_loc = struct.unpack_from("!H", raw_bytes, 1)[0]
                    track_num = struct.unpack_from("!H", raw_bytes, 3)[0]
                else:
                    ts_ns = 0
                    stock_loc = 0
                    track_num = 0

                return ITCHMessage(
                    msg_type=msg_type,
                    stock_locate=stock_loc,
                    tracking_number=track_num,
                    timestamp_ns=ts_ns,
                    payload={"raw_len": length, "bytes": raw_bytes},
                )

        except Exception as exc:
            logger.debug("Failed to decode ITCH 5.0 message type '%s': %s", msg_type, exc)
            return None

    def to_market_tick(self, msg: ITCHMessage) -> Optional[MarketTick]:
        """Converts relevant ITCH messages (Trades, Add Orders) to standard MarketTick."""
        if isinstance(msg, TradeMessage):
            return MarketTick(
                symbol=msg.stock,
                timestamp_ns=msg.timestamp_ns,
                price=msg.price,
                volume=float(msg.shares),
                market=self.market,
            )
        elif isinstance(msg, AddOrderMessage):
            # Quotes can populate bid/ask prices
            is_buy = (msg.buy_sell == "B")
            return MarketTick(
                symbol=msg.stock,
                timestamp_ns=msg.timestamp_ns,
                price=msg.price,
                volume=float(msg.shares),
                bid_price=msg.price if is_buy else None,
                ask_price=msg.price if not is_buy else None,
                bid_volume=float(msg.shares) if is_buy else None,
                ask_volume=float(msg.shares) if not is_buy else None,
                market=self.market,
            )
        return None


# ---------------------------------------------------------------------------
# Master PCAP Market Feed Processor
# ---------------------------------------------------------------------------

class PCAPMarketFeedProcessor:
    """
    Master high-frequency PCAP stream and live packet processor.
    Peels raw PCAP file frames, decapsulates Ethernet/IP/UDP and MoldUDP64,
    and dispatches decoded ITCH 5.0 messages and MarketTicks to callbacks.
    """

    def __init__(self, config: Optional[PCAPProcessorConfig] = None) -> None:
        self.config = config or PCAPProcessorConfig()
        self.ts_tracker = HardwareTimestampTracker(
            calibrate_samples=self.config.calibrate_timestamp_samples
        )
        self.mold_parser = MoldUDP64Parser()
        self.itch_parser = NASDAQITCH50Parser(
            fixed_point_divisor=self.config.fixed_point_divisor,
            default_market=self.config.default_market,
        )

        self._tick_callbacks: List[Callable[[MarketTick], None]] = []
        self._msg_callbacks: Dict[str, List[Callable[[ITCHMessage], None]]] = collections.defaultdict(list)
        self._global_msg_callbacks: List[Callable[[ITCHMessage], None]] = []
        self._total_bytes_processed: int = 0
        self._total_packets_processed: int = 0
        self._total_messages_processed: int = 0

    def register_tick_callback(self, callback: Callable[[MarketTick], None]) -> None:
        """Registers a callback receiving translated MarketTick events."""
        self._tick_callbacks.append(callback)

    def register_message_callback(
        self, msg_type: Optional[str], callback: Callable[[ITCHMessage], None]
    ) -> None:
        """Registers a callback for specific or all ITCH message types."""
        if msg_type is None or msg_type == "*":
            self._global_msg_callbacks.append(callback)
        else:
            self._msg_callbacks[msg_type].append(callback)

    def parse_pcap_header(self, stream: io.BufferedReader) -> Optional[PCAPHeader]:
        """Reads and validates the 24-byte PCAP global header."""
        hdr_data = stream.read(PCAP_GLOBAL_HEADER_SIZE)
        if len(hdr_data) < PCAP_GLOBAL_HEADER_SIZE:
            return None

        magic_be = struct.unpack_from(">I", hdr_data, 0)[0]
        magic_le = struct.unpack_from("<I", hdr_data, 0)[0]
        swapped = False
        is_nsec = False

        if magic_be in (PCAP_MAGIC_NSEC, PCAP_MAGIC_USEC):
            swapped = False
            is_nsec = (magic_be == PCAP_MAGIC_NSEC)
        elif magic_le in (PCAP_MAGIC_NSEC, PCAP_MAGIC_USEC):
            swapped = True
            is_nsec = (magic_le == PCAP_MAGIC_NSEC)
        else:
            logger.warning("Unrecognized PCAP magic number: be=0x%08X, le=0x%08X", magic_be, magic_le)

        fmt = ("<" if swapped else ">") + PCAP_GLOBAL_HEADER_FMT
        vals = struct.unpack(fmt, hdr_data)

        return PCAPHeader(
            magic=vals[0],
            version_major=vals[1],
            version_minor=vals[2],
            thiszone=vals[3],
            sigfigs=vals[4],
            snaplen=vals[5],
            network=vals[6],
            is_nanosecond=is_nsec,
            is_swapped_endian=swapped,
        )

    def _peel_network_frame(self, raw_frame: bytes) -> bytes:
        """
        Strips Ethernet (14B), IPv4 (variable ~20B), and UDP (8B) headers
        to reveal the inner application payload (e.g. MoldUDP64).
        """
        length = len(raw_frame)
        if length < 42:
            return raw_frame  # Return as raw if smaller than standard eth+ip+udp

        # Check for standard Ethernet frame: IP protocol 0x0800 at offset 12
        eth_type = struct.unpack_from("!H", raw_frame, 12)[0]
        if eth_type == 0x0800:
            ip_offset = 14
            version_ihl = raw_frame[ip_offset]
            ihl = (version_ihl & 0x0F) * 4
            protocol = raw_frame[ip_offset + 9]

            if protocol == 17:  # UDP
                udp_offset = ip_offset + ihl
                src_port, dst_port, udp_len = struct.unpack_from("!HHH", raw_frame, udp_offset)

                if (
                    self.config.udp_port_filter is None
                    or dst_port == self.config.udp_port_filter
                    or src_port == self.config.udp_port_filter
                ):
                    payload_offset = udp_offset + 8
                    return raw_frame[payload_offset : payload_offset + (udp_len - 8)]

        # Fallback: Treat as raw application payload directly
        return raw_frame

    def process_packet_bytes(
        self, packet_bytes: bytes, host_timestamp_ns: Optional[int] = None
    ) -> List[ITCHMessage]:
        """
        Ingests a single network packet buffer, peeling transport layers,
        decapsulating MoldUDP64, and returning decoded ITCH messages.
        """
        host_ts = host_timestamp_ns if host_timestamp_ns is not None else self.ts_tracker.get_timestamp_ns()
        self._total_packets_processed += 1
        self._total_bytes_processed += len(packet_bytes)

        payload = self._peel_network_frame(packet_bytes)
        if not payload:
            return []

        # 1. Check for direct single ITCH message first
        msg_type_char = chr(payload[0]) if payload else ""
        if (
            msg_type_char in NASDAQITCH50Parser.MESSAGE_LENGTHS
            and len(payload) == NASDAQITCH50Parser.MESSAGE_LENGTHS[msg_type_char]
        ):
            msg = self.itch_parser.parse_message(payload)
            if msg is not None:
                self._dispatch_message(msg, host_ts)
                return [msg]

        # 2. Check for MoldUDP64 encapsulated stream
        messages: List[ITCHMessage] = []
        if len(payload) >= MOLDUDP64_HEADER_SIZE:
            _, _, count, raw_msgs = self.mold_parser.parse_packet(payload)
            if raw_msgs:
                for raw_m in raw_msgs:
                    msg = self.itch_parser.parse_message(raw_m)
                    if msg is not None:
                        self._dispatch_message(msg, host_ts)
                        messages.append(msg)
                if messages:
                    return messages

        # 3. Direct single ITCH message fallback
        msg = self.itch_parser.parse_message(payload)
        if msg is not None:
            self._dispatch_message(msg, host_ts)
            messages.append(msg)

        return messages

    def _dispatch_message(self, msg: ITCHMessage, host_ts: int) -> None:
        """Internal dispatcher routing messages to callbacks and telemetry."""
        self._total_messages_processed += 1

        if self.config.enable_wire_latency_tracking and msg.timestamp_ns > 0:
            self.ts_tracker.record_wire_latency(msg.timestamp_ns, host_ts)

        # Notify type-specific callbacks
        callbacks = self._msg_callbacks.get(msg.msg_type)
        if callbacks:
            for cb in callbacks:
                try:
                    cb(msg)
                except Exception as exc:
                    logger.debug("Exception in ITCH message callback: %s", exc)

        # Notify global message callbacks
        for g_cb in self._global_msg_callbacks:
            try:
                g_cb(msg)
            except Exception as exc:
                logger.debug("Exception in global ITCH callback: %s", exc)

        # Check and notify tick callbacks
        if self._tick_callbacks:
            tick = self.itch_parser.to_market_tick(msg)
            if tick is not None:
                for t_cb in self._tick_callbacks:
                    try:
                        t_cb(tick)
                    except Exception as exc:
                        logger.debug("Exception in MarketTick callback: %s", exc)

    def process_pcap_file(self, file_path: Union[str, Path]) -> FeedProcessingSummary:
        """
        Streams and parses an entire PCAP file chunk by chunk.
        Returns a FeedProcessingSummary.
        """
        p = Path(file_path)
        if not p.exists():
            raise FileNotFoundError(f"PCAP file not found: {p}")

        t0 = time.perf_counter()
        summary = FeedProcessingSummary()

        with open(p, "rb") as f:
            header = self.parse_pcap_header(f)
            if header is None:
                raise ValueError(f"Invalid PCAP file header in {p}")

            pkt_fmt = ("<" if header.is_swapped_endian else ">") + PCAP_PACKET_HEADER_FMT
            is_nsec = header.is_nanosecond

            while True:
                if self.config.max_packets and summary.total_packets >= self.config.max_packets:
                    break

                hdr_bytes = f.read(PCAP_PACKET_HEADER_SIZE)
                if len(hdr_bytes) < PCAP_PACKET_HEADER_SIZE:
                    break

                ts_sec, ts_sub, incl_len, orig_len = struct.unpack(pkt_fmt, hdr_bytes)
                wire_ts_ns = (ts_sec * 1_000_000_000) + (ts_sub if is_nsec else ts_sub * 1_000)

                packet_data = f.read(incl_len)
                if len(packet_data) < incl_len:
                    summary.packets_dropped += 1
                    break

                summary.total_packets += 1
                summary.total_bytes += (PCAP_PACKET_HEADER_SIZE + incl_len)

                msgs = self.process_packet_bytes(packet_data, host_timestamp_ns=wire_ts_ns)
                summary.total_itch_messages += len(msgs)

                for m in msgs:
                    summary.messages_by_type[m.msg_type] = summary.messages_by_type.get(m.msg_type, 0) + 1

        summary.sequence_gaps_detected = self.mold_parser.gaps_detected
        summary.processing_time_ms = (time.perf_counter() - t0) * 1000.0

        lat_stats = self.ts_tracker.get_latency_stats()
        summary.avg_latency_ns = lat_stats["mean_ns"]
        summary.p50_latency_ns = lat_stats["p50_ns"]
        summary.p90_latency_ns = lat_stats["p90_ns"]
        summary.p99_latency_ns = lat_stats["p99_ns"]

        return summary

    def generate_synthetic_pcap(
        self, messages: List[ITCHMessage], output_path: Union[str, Path]
    ) -> int:
        """
        Creates a valid standard libpcap capture file containing synthetic ITCH 5.0 messages.
        Useful for deterministic testing, replay, and CI benchmarks.
        """
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        bytes_written = 0

        with open(out, "wb") as f:
            # Write 24-byte PCAP global header (nanosecond timestamps, snaplen 65535, Ethernet network=1)
            global_hdr = struct.pack(
                ">" + PCAP_GLOBAL_HEADER_FMT,
                PCAP_MAGIC_NSEC,
                2,  # Major
                4,  # Minor
                0,  # GMT offset
                0,  # Accuracy
                65535,  # Snaplen
                1,  # LinkType Ethernet
            )
            f.write(global_hdr)
            bytes_written += len(global_hdr)

            for i, msg in enumerate(messages):
                raw_payload = self._encode_itch_message(msg)

                # Wrap in UDP/IP/Ethernet header
                frame = self._build_synthetic_ethernet_frame(raw_payload, dport=12000)
                frame_len = len(frame)

                sec = msg.timestamp_ns // 1_000_000_000
                nsec = msg.timestamp_ns % 1_000_000_000

                pkt_hdr = struct.pack(">" + PCAP_PACKET_HEADER_FMT, sec, nsec, frame_len, frame_len)
                f.write(pkt_hdr)
                f.write(frame)
                bytes_written += len(pkt_hdr) + frame_len

        return bytes_written

    def _encode_itch_message(self, msg: ITCHMessage) -> bytes:
        """Encodes an ITCHMessage dataclass back into standard ITCH 5.0 binary format."""
        ts_ns = msg.timestamp_ns
        hi = (ts_ns >> 32) & 0xFFFF
        lo = ts_ns & 0xFFFFFFFF
        ts_bytes = struct.pack("!HI", hi, lo)

        if isinstance(msg, AddOrderMessage):
            sym_bytes = msg.stock.encode("ascii")[:8].ljust(8, b" ")
            px_int = int(round(msg.price * self.config.fixed_point_divisor))
            if msg.attribution:
                attr_bytes = msg.attribution.encode("ascii")[:4].ljust(4, b" ")
                return struct.pack(
                    NASDAQITCH50Parser._FMT_F,
                    b"F",
                    msg.stock_locate,
                    msg.tracking_number,
                    ts_bytes,
                    msg.order_ref_num,
                    msg.buy_sell.encode("ascii"),
                    msg.shares,
                    sym_bytes,
                    px_int,
                    attr_bytes,
                )
            else:
                return struct.pack(
                    NASDAQITCH50Parser._FMT_A,
                    b"A",
                    msg.stock_locate,
                    msg.tracking_number,
                    ts_bytes,
                    msg.order_ref_num,
                    msg.buy_sell.encode("ascii"),
                    msg.shares,
                    sym_bytes,
                    px_int,
                )

        elif isinstance(msg, TradeMessage):
            sym_bytes = msg.stock.encode("ascii")[:8].ljust(8, b" ")
            px_int = int(round(msg.price * self.config.fixed_point_divisor))
            return struct.pack(
                NASDAQITCH50Parser._FMT_P,
                b"P",
                msg.stock_locate,
                msg.tracking_number,
                ts_bytes,
                msg.order_ref_num,
                msg.buy_sell.encode("ascii"),
                msg.shares,
                sym_bytes,
                px_int,
                msg.match_number,
            )

        elif isinstance(msg, OrderExecutedMessage):
            return struct.pack(
                NASDAQITCH50Parser._FMT_E,
                b"E",
                msg.stock_locate,
                msg.tracking_number,
                ts_bytes,
                msg.order_ref_num,
                msg.executed_shares,
                msg.match_number,
            )

        elif isinstance(msg, SystemEventMessage):
            return struct.pack(
                NASDAQITCH50Parser._FMT_S,
                b"S",
                msg.stock_locate,
                msg.tracking_number,
                ts_bytes,
                msg.event_code.encode("ascii"),
            )

        elif isinstance(msg, OrderCancelMessage):
            return struct.pack(
                NASDAQITCH50Parser._FMT_X,
                b"X",
                msg.stock_locate,
                msg.tracking_number,
                ts_bytes,
                msg.order_ref_num,
                msg.canceled_shares,
            )

        elif isinstance(msg, OrderDeleteMessage):
            return struct.pack(
                NASDAQITCH50Parser._FMT_D,
                b"D",
                msg.stock_locate,
                msg.tracking_number,
                ts_bytes,
                msg.order_ref_num,
            )

        elif isinstance(msg, OrderReplaceMessage):
            px_int = int(round(msg.price * self.config.fixed_point_divisor))
            return struct.pack(
                NASDAQITCH50Parser._FMT_U,
                b"U",
                msg.stock_locate,
                msg.tracking_number,
                ts_bytes,
                msg.original_order_ref_num,
                msg.new_order_ref_num,
                msg.shares,
                px_int,
            )

        # Fallback dummy payload
        return b"S" + b"\x00" * 11

    @staticmethod
    def _build_synthetic_ethernet_frame(payload: bytes, dport: int = 12000) -> bytes:
        """Wraps payload in minimal mock Ethernet (14B) + IPv4 (20B) + UDP (8B) headers."""
        udp_len = 8 + len(payload)
        ip_total_len = 20 + udp_len

        # Ethernet header: dst MAC (6), src MAC (6), ethertype 0x0800 (2)
        eth_hdr = b"\x00\x11\x22\x33\x44\x55\x66\x77\x88\x99\xaa\xbb\x08\x00"

        # IPv4 header: ver/ihl (0x45), dscp/ecn (0), total_len, id (0), flags/frag (0), ttl (64), proto 17 (UDP), csum (0), src IP, dst IP
        ip_hdr = struct.pack(
            "!BBHHHBBH4s4s",
            0x45, 0, ip_total_len, 0x1234, 0, 64, 17, 0,
            b"\xc0\xa8\x01\x01",  # 192.168.1.1
            b"\xe0\x00\x01\x80",  # 224.0.1.128 multicast
        )

        # UDP header: src port, dst port, length, checksum (0)
        udp_hdr = struct.pack("!HHHH", 50000, dport, udp_len, 0)

        return eth_hdr + ip_hdr + udp_hdr + payload

    def get_metrics(self) -> Dict[str, Any]:
        """Telemetry diagnostics of the processor."""
        return {
            "version": VERSION,
            "release": RELEASE,
            "feature": FEATURE,
            "total_packets_processed": self._total_packets_processed,
            "total_bytes_processed": self._total_bytes_processed,
            "total_messages_processed": self._total_messages_processed,
            "moldudp64_stats": self.mold_parser.get_drop_stats(),
            "latency_stats": self.ts_tracker.get_latency_stats(),
        }


# ---------------------------------------------------------------------------
# Aliases for Institutional Integration & Backward Compatibility
# ---------------------------------------------------------------------------
ITCHFeedPacketProcessor = PCAPMarketFeedProcessor
HardwareTimestampedPCAPProcessor = PCAPMarketFeedProcessor
HighFrequencyMarketFeedProcessor = PCAPMarketFeedProcessor
Phase115FeedProcessor = PCAPMarketFeedProcessor
ITCH50Parser = NASDAQITCH50Parser
MoldUDPParser = MoldUDP64Parser
FastPCAPFeedProcessor = PCAPMarketFeedProcessor
HardwareTimestampingEngine = HardwareTimestampTracker
ITCHFeedProcessor = PCAPMarketFeedProcessor
MarketDataPCAPStreamer = PCAPMarketFeedProcessor
TotalViewITCHParser = NASDAQITCH50Parser

__all__ = [
    "VERSION",
    "RELEASE",
    "FEATURE",
    "PCAP_MAGIC_USEC",
    "PCAP_MAGIC_NSEC",
    "PCAP_MAGIC_SWAPPED_USEC",
    "PCAP_MAGIC_SWAPPED_NSEC",
    "PCAP_GLOBAL_HEADER_FMT",
    "PCAP_GLOBAL_HEADER_SIZE",
    "PCAP_PACKET_HEADER_FMT",
    "PCAP_PACKET_HEADER_SIZE",
    "MOLDUDP64_HEADER_FMT",
    "MOLDUDP64_HEADER_SIZE",
    "PCAPHeader",
    "PCAPPacketHeader",
    "ITCHMessage",
    "SystemEventMessage",
    "StockDirectoryMessage",
    "AddOrderMessage",
    "OrderExecutedMessage",
    "OrderCancelMessage",
    "OrderDeleteMessage",
    "OrderReplaceMessage",
    "TradeMessage",
    "NOIIMessage",
    "MarketTick",
    "PCAPProcessorConfig",
    "FeedProcessingSummary",
    "HardwareTimestampTracker",
    "MoldUDP64Parser",
    "NASDAQITCH50Parser",
    "PCAPMarketFeedProcessor",
    "ITCHFeedPacketProcessor",
    "HardwareTimestampedPCAPProcessor",
    "HighFrequencyMarketFeedProcessor",
    "Phase115FeedProcessor",
    "ITCH50Parser",
    "MoldUDPParser",
    "FastPCAPFeedProcessor",
    "HardwareTimestampingEngine",
    "ITCHFeedProcessor",
    "MarketDataPCAPStreamer",
    "TotalViewITCHParser",
]

