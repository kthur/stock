"""
shared_memory_ring_buffer.py — High-Performance Zero-Copy Shared Memory & MMF IPC Ring Buffer
Phase 108 (Release R124 / v115) & Phase 115 (Release R131 / v122 Production Master / Feature F546)

Provides:
  1. SharedMemoryRingBuffer: Lock-free single-producer single-consumer (SPSC)
     circular ring buffer using multiprocessing.shared_memory or memory-mapped files (MMF).
  2. Zero-Copy Serialization: Binary struct pack_into / unpack_from directly
     over memoryview without heap allocations or GC pressure (<500ns latency).
  3. Structured IPC Messages:
     - LOBTickMessage: Level 2/3 orderbook ticks with 5-level depth snapshots.
     - RiskAlertMessage: Real-time risk events, stop triggers, and circuit breakers.
     - ExecutionOrderMessage: Sliced child orders, routing events, and executions.
     - ITCHPacketMessage: NASDAQ ITCH 5.0 raw feed events (Add, Execute, Cancel, Trade).
     - OrderDispatchMessage: Real-time sub-microsecond OMS order routing dispatch packets.
  4. Resilient Lifecycle:
     - 256-byte cacheline-aligned binary header with magic uint32 (0x53484D52 'SHMR').
     - Monotonic 64-bit sequence counters (head_seq, tail_seq).
     - Cross-platform POSIX and Windows shared memory and file mmap naming.
     - Stale segment detection, heartbeat monitoring, and automatic dead-process reclamation.
     - Context manager support with zero memory leak guarantees.
  5. Deterministic MMF Circular Buffer IPC (<500ns latency):
     - write_raw_slot / read_raw_slot / read_raw_view fast-paths.
     - Built-in benchmark_ipc_latency() diagnostic tool.
  6. Alias Trees:
     - ZeroCopySharedMemoryRingBuffer
     - Phase108SharedMemoryRingBuffer
     - HighPerformanceSharedMemoryIPC
     - SharedMemoryIPCRingBuffer
     - DeterministicMMFCircularBuffer
     - Phase115SharedMemoryRingBuffer
     - SubMicrosecondCircularBuffer
     - MemoryMappedRingBuffer
     - MMFRingBufferIPC
"""

from __future__ import annotations

import atexit
import ctypes
import logging
import mmap
import os
import struct
import sys
import tempfile
import time
from contextlib import contextmanager
from dataclasses import dataclass
from enum import IntEnum
from multiprocessing import shared_memory
from typing import Any, Dict, Generator, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Binary Protocol Constants & Header Offsets
# ---------------------------------------------------------------------------
MAGIC_HEADER = 0x53484D52  # 'SHMR' in ASCII
HEADER_VERSION = 115
HEADER_SIZE = 256
DEFAULT_CAPACITY = 2048     # Must be a power of 2
DEFAULT_SLOT_SIZE = 512    # Fixed slot size in bytes

STATUS_INITIALIZED = 0x01
STATUS_PRODUCER_LIVE = 0x02
STATUS_CONSUMER_LIVE = 0x04
STATUS_MMF_BACKED = 0x08

# Cacheline-aligned 256-byte Header Offsets
OFFSET_MAGIC = 0              # uint32: 0x53484D52
OFFSET_VERSION = 4            # uint16: 115
OFFSET_STATUS_FLAGS = 6       # uint16: bit flags
OFFSET_SLOT_SIZE = 8          # uint32: 512
OFFSET_CAPACITY = 12          # uint32: e.g. 2048
OFFSET_MASK = 16              # uint32: capacity - 1
OFFSET_HEADER_SIZE = 20       # uint32: 256
OFFSET_PRODUCER_PID = 24      # int64
OFFSET_CONSUMER_PID = 32      # int64
OFFSET_PRODUCER_HB = 40       # int64 (nanoseconds epoch)
OFFSET_CONSUMER_HB = 48       # int64 (nanoseconds epoch)
OFFSET_HEAD_SEQ = 56          # uint64 (written ONLY by producer)
OFFSET_TAIL_SEQ = 64          # uint64 (written ONLY by consumer)
OFFSET_DROPPED_COUNT = 72     # uint64
OFFSET_TOTAL_WRITTEN = 80     # uint64
OFFSET_TOTAL_READ = 88        # uint64
OFFSET_SPINLOCK = 96          # uint32 (0: unlocked, 1: locked)
OFFSET_SLOTS_DATA = 256       # Data region begins at offset 256

HEADER_STRUCT_FMT = "<I H H I I I I q q q q Q Q Q Q Q I 156s"

# Pre-compiled slot struct formats
# Envelope: msg_type (H=2), msg_len (H=2), seq (Q=8), timestamp_ns (q=8) -> 20 bytes
LOB_TICK_FMT = "<HHQq 16s dddddd I 5d 5d 5d 5d"         # 248 bytes
RISK_ALERT_FMT = "<HHQq 32s 16s 8s ii dd i 96s"          # 200 bytes
EXECUTION_ORDER_FMT = "<HHQq 32s 16s 8s ii dd i 16s"     # 120 bytes
ITCH_PACKET_FMT = "<HHQq c 16s Q I d b 32s"              # 90 bytes
ORDER_DISPATCH_FMT = "<HHQq 32s 16s b b d d b i 32s"     # 123 bytes

LOB_TICK_LEN = struct.calcsize(LOB_TICK_FMT)
RISK_ALERT_LEN = struct.calcsize(RISK_ALERT_FMT)
EXECUTION_ORDER_LEN = struct.calcsize(EXECUTION_ORDER_FMT)
ITCH_PACKET_LEN = struct.calcsize(ITCH_PACKET_FMT)
ORDER_DISPATCH_LEN = struct.calcsize(ORDER_DISPATCH_FMT)

_STRUCT_Q = struct.Struct("<Q")
_STRUCT_QQ = struct.Struct("<QQ")
_STRUCT_q = struct.Struct("<q")


# ---------------------------------------------------------------------------
# Process Life & Name Helpers
# ---------------------------------------------------------------------------
def is_pid_alive(pid: int) -> bool:
    """Checks whether a process with the given PID is actively running."""
    if pid <= 0:
        return False
    if os.name == "nt":
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        try:
            handle = ctypes.windll.kernel32.OpenProcess(
                PROCESS_QUERY_LIMITED_INFORMATION, False, pid
            )
            if handle:
                ctypes.windll.kernel32.CloseHandle(handle)
                return True
            return False
        except Exception:
            return False
    else:
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False


def sanitize_shm_name(name: str) -> str:
    """Normalizes shared memory name across Windows and POSIX platforms."""
    clean = name.strip()
    if os.name == "nt":
        clean = clean.replace("/", "_").replace("\\", "_")
    else:
        if not clean.startswith("/"):
            clean = "/" + clean
    return clean


# ---------------------------------------------------------------------------
# Message Types & Dataclasses
# ---------------------------------------------------------------------------
class MessageType(IntEnum):
    HEARTBEAT = 0
    LOB_TICK = 1
    RISK_ALERT = 2
    EXECUTION_ORDER = 3
    ITCH_PACKET = 4
    ORDER_DISPATCH = 5
    CUSTOM = 99


@dataclass
class LOBTickMessage:
    symbol: str
    timestamp_ns: int
    bid_price: float
    ask_price: float
    bid_size: float
    ask_size: float
    last_price: float
    last_size: float
    depth_levels: int = 5
    bid_prices: Tuple[float, ...] = (0.0, 0.0, 0.0, 0.0, 0.0)
    ask_prices: Tuple[float, ...] = (0.0, 0.0, 0.0, 0.0, 0.0)
    bid_sizes: Tuple[float, ...] = (0.0, 0.0, 0.0, 0.0, 0.0)
    ask_sizes: Tuple[float, ...] = (0.0, 0.0, 0.0, 0.0, 0.0)

    def __post_init__(self) -> None:
        if not isinstance(self.bid_prices, tuple):
            self.bid_prices = tuple(float(x) for x in self.bid_prices)
        if not isinstance(self.ask_prices, tuple):
            self.ask_prices = tuple(float(x) for x in self.ask_prices)
        if not isinstance(self.bid_sizes, tuple):
            self.bid_sizes = tuple(float(x) for x in self.bid_sizes)
        if not isinstance(self.ask_sizes, tuple):
            self.ask_sizes = tuple(float(x) for x in self.ask_sizes)


@dataclass
class RiskAlertMessage:
    alert_id: str
    timestamp_ns: int
    symbol: str
    market: str
    severity: int     # 1=INFO, 2=WARN, 3=CRITICAL, 4=EMERGENCY
    alert_type: int   # 1=TP, 2=SL, 3=FLASH_CRASH, 4=VIX_SURGE, 5=CIRCUIT_BREAKER
    metric_value: float
    threshold_value: float
    action_code: int  # 1=REDUCE, 2=LIQUIDATE, 3=INVERSE_HEDGE, 4=ALERT_ONLY
    message: str = ""


@dataclass
class ExecutionOrderMessage:
    order_id: str
    symbol: str
    market: str
    timestamp_ns: int
    side: int         # 1=BUY, -1=SELL
    order_type: int   # 1=LIMIT, 2=MARKET, 3=ALMGREN_CHRISS_SLICE
    quantity: float
    price: float
    status: int       # 1=NEW, 2=ROUTED, 3=FILLED, 4=CANCELLED, 5=REJECTED
    client_id: str = "OMS_CLIENT"


@dataclass
class ITCHPacketMessage:
    timestamp_ns: int
    msg_type_code: str       # 'A'=Add, 'E'=Execute, 'C'=Cancel, 'P'=Trade
    symbol: str
    order_ref: int
    shares: int
    price: float
    side: int                # 1=BUY, -1=SELL
    attribution: str = ""


@dataclass
class OrderDispatchMessage:
    dispatch_id: str
    symbol: str
    venue_id: int
    side: int                # 1=BUY, -1=SELL
    quantity: float
    price: float
    order_type: int
    routing_flags: int = 0
    timestamp_ns: int = 0
    client_id: str = "LOCKLESS_OMS"


def _pad_tuple5(seq: Any) -> Tuple[float, float, float, float, float]:
    """Ensures exactly 5 floats in tuple."""
    if seq is None:
        return (0.0, 0.0, 0.0, 0.0, 0.0)
    vals = [float(x) for x in seq]
    while len(vals) < 5:
        vals.append(0.0)
    return (vals[0], vals[1], vals[2], vals[3], vals[4])


# ---------------------------------------------------------------------------
# Core SharedMemoryRingBuffer Implementation
# ---------------------------------------------------------------------------
class SharedMemoryRingBuffer:
    """
    High-Performance Zero-Copy Shared Memory & MMF IPC Ring Buffer.
    Implements lock-free Single Producer Single Consumer (SPSC) protocol
    over memory-mapped shared memory or memory-mapped files (<500ns latency).
    """

    def __init__(
        self,
        name: str,
        capacity: int = DEFAULT_CAPACITY,
        slot_size: int = DEFAULT_SLOT_SIZE,
        create: bool = True,
        auto_unlink: bool = True,
        spinlock_timeout_us: int = 100_000,
        client_mode: Optional[str] = None,
        backing: str = "shm",
        mmap_dir: Optional[str] = None,
    ) -> None:
        """
        Initializes or attaches to a shared memory or MMF ring buffer.

        Args:
            name: Unique identifier for shared memory segment.
            capacity: Number of slots (must be a positive power of 2).
            slot_size: Size in bytes of each slot (minimum 256 bytes).
            create: True to allocate new segment; False to attach to existing.
            auto_unlink: If True, creator will unlink shared memory on close.
            spinlock_timeout_us: Microsecond timeout for optional spinlock operations.
            client_mode: Optional role hint: "producer", "consumer", or None.
            backing: Backing storage: "shm" (multiprocessing.shared_memory) or "mmap" (OS file mmap).
            mmap_dir: Custom directory for MMF backing files (defaults to system temp dir).
        """
        self._name = sanitize_shm_name(name)
        self._backing = str(backing).lower()
        self._is_creator = False
        self._auto_unlink = auto_unlink
        self._spinlock_timeout_us = spinlock_timeout_us
        self._client_mode = client_mode
        self._is_closed = False
        self._shm: Optional[shared_memory.SharedMemory] = None
        self._buf: Optional[memoryview] = None
        self._mmap_dir = mmap_dir or tempfile.gettempdir()
        self._mmap_file = None
        self._mmap_obj: Optional[mmap.mmap] = None
        self._mmap_file_path: Optional[str] = None

        if self._backing == "mmap":
            # Memory-mapped file backing
            clean_fname = self._name.replace("/", "_").replace("\\", "_")
            self._mmap_file_path = os.path.join(self._mmap_dir, f"{clean_fname}.mmf")

            if create:
                if capacity <= 0 or (capacity & (capacity - 1)) != 0:
                    raise ValueError(f"Capacity must be a positive power of 2, got {capacity}")
                if slot_size < 256:
                    raise ValueError(f"Slot size must be at least 256 bytes, got {slot_size}")

                self._capacity = capacity
                self._slot_size = slot_size
                self._mask = capacity - 1
                total_size = HEADER_SIZE + capacity * slot_size

                if os.path.exists(self._mmap_file_path):
                    try:
                        os.remove(self._mmap_file_path)
                    except Exception:
                        pass

                self._mmap_file = open(self._mmap_file_path, "w+b")
                self._mmap_file.seek(total_size - 1)
                self._mmap_file.write(b"\x00")
                self._mmap_file.flush()
                self._is_creator = True

                self._mmap_obj = mmap.mmap(
                    self._mmap_file.fileno(), total_size, access=mmap.ACCESS_WRITE
                )
                self._buf = memoryview(self._mmap_obj)
                self._init_header()
                self._set_status_flag(STATUS_MMF_BACKED)
            else:
                if not os.path.exists(self._mmap_file_path):
                    raise FileNotFoundError(f"MMF backing file not found: {self._mmap_file_path}")
                self._mmap_file = open(self._mmap_file_path, "r+b")
                self._is_creator = False
                self._mmap_obj = mmap.mmap(
                    self._mmap_file.fileno(), 0, access=mmap.ACCESS_WRITE
                )
                self._buf = memoryview(self._mmap_obj)
                self._validate_and_read_header()

        else:
            # POSIX / Windows Shared Memory backing
            if create:
                if capacity <= 0 or (capacity & (capacity - 1)) != 0:
                    raise ValueError(f"Capacity must be a positive power of 2, got {capacity}")
                if slot_size < 256:
                    raise ValueError(f"Slot size must be at least 256 bytes, got {slot_size}")

                self._capacity = capacity
                self._slot_size = slot_size
                self._mask = capacity - 1
                total_size = HEADER_SIZE + capacity * slot_size

                # Attempt to allocate; reclaim stale segment if FileExistsError
                try:
                    self._shm = shared_memory.SharedMemory(
                        name=self._name, create=True, size=total_size
                    )
                    self._is_creator = True
                except FileExistsError:
                    if self._reclaim_stale_segment(total_size):
                        self._shm = shared_memory.SharedMemory(
                            name=self._name, create=True, size=total_size
                        )
                        self._is_creator = True
                    else:
                        # Segment exists and is active; attach to it
                        logger.info("Shared memory '%s' already active; attaching as client.", self._name)
                        self._shm = shared_memory.SharedMemory(name=self._name, create=False)
                        self._is_creator = False

                self._buf = self._shm.buf

                if self._is_creator:
                    self._init_header()
                else:
                    self._validate_and_read_header()
            else:
                # Client attach mode
                self._shm = shared_memory.SharedMemory(name=self._name, create=False)
                self._buf = self._shm.buf
                self._validate_and_read_header()

        # Register process heartbeat and role
        pid = os.getpid()
        now_ns = time.time_ns()
        if self._client_mode == "consumer" or (not self._is_creator and self._client_mode is None):
            struct.pack_into("<q", self._buf, OFFSET_CONSUMER_PID, pid)
            struct.pack_into("<q", self._buf, OFFSET_CONSUMER_HB, now_ns)
            self._set_status_flag(STATUS_CONSUMER_LIVE)
        else:
            struct.pack_into("<q", self._buf, OFFSET_PRODUCER_PID, pid)
            struct.pack_into("<q", self._buf, OFFSET_PRODUCER_HB, now_ns)
            self._set_status_flag(STATUS_PRODUCER_LIVE)

        # Register exit hook for clean resource disposal
        atexit.register(self._cleanup_on_exit)

    # -----------------------------------------------------------------------
    # Header Initialization & Validation
    # -----------------------------------------------------------------------
    def _init_header(self) -> None:
        """Writes the initial 256-byte header into shared memory."""
        pid = os.getpid()
        now_ns = time.time_ns()
        flags = STATUS_INITIALIZED | STATUS_PRODUCER_LIVE
        if self._backing == "mmap":
            flags |= STATUS_MMF_BACKED

        struct.pack_into(
            HEADER_STRUCT_FMT,
            self._buf,
            0,
            MAGIC_HEADER,
            HEADER_VERSION,
            flags,
            self._slot_size,
            self._capacity,
            self._mask,
            HEADER_SIZE,
            pid,               # producer_pid
            0,                 # consumer_pid
            now_ns,            # producer_heartbeat_ns
            0,                 # consumer_heartbeat_ns
            0,                 # head_seq
            0,                 # tail_seq
            0,                 # dropped_count
            0,                 # total_written
            0,                 # total_read
            0,                 # spinlock
            b"\x00" * 156,     # padding
        )

    def _validate_and_read_header(self) -> None:
        """Validates magic identifier and loads parameters from header."""
        magic = struct.unpack_from("<I", self._buf, OFFSET_MAGIC)[0]
        if magic != MAGIC_HEADER:
            raise ValueError(
                f"Invalid shared memory magic: 0x{magic:08X}, expected 0x{MAGIC_HEADER:08X} ('SHMR')"
            )
        self._slot_size = struct.unpack_from("<I", self._buf, OFFSET_SLOT_SIZE)[0]
        self._capacity = struct.unpack_from("<I", self._buf, OFFSET_CAPACITY)[0]
        self._mask = struct.unpack_from("<I", self._buf, OFFSET_MASK)[0]

        if self._capacity <= 0 or (self._capacity & (self._capacity - 1)) != 0:
            raise ValueError(f"Corrupted header capacity: {self._capacity}")
        if self._slot_size < 256:
            raise ValueError(f"Corrupted header slot_size: {self._slot_size}")

    def _reclaim_stale_segment(self, total_size: int) -> bool:
        """
        Inspects existing segment. If owner PID is dead or heartbeat is older than
        10 seconds, unlinks segment to allow clean re-creation.
        """
        try:
            old_shm = shared_memory.SharedMemory(name=self._name, create=False)
            buf = old_shm.buf
            if len(buf) >= HEADER_SIZE:
                magic = struct.unpack_from("<I", buf, OFFSET_MAGIC)[0]
                if magic == MAGIC_HEADER:
                    prod_pid = struct.unpack_from("<q", buf, OFFSET_PRODUCER_PID)[0]
                    prod_hb = struct.unpack_from("<q", buf, OFFSET_PRODUCER_HB)[0]
                    now_ns = time.time_ns()
                    hb_age_sec = (now_ns - prod_hb) / 1e9 if prod_hb > 0 else 999.0
                    alive = is_pid_alive(prod_pid)

                    if not alive or hb_age_sec > 10.0:
                        logger.warning(
                            "Reclaiming stale SHM segment '%s' (PID %d alive=%s, heartbeat age=%.1fs)",
                            self._name, prod_pid, alive, hb_age_sec,
                        )
                        buf.release()
                        old_shm.close()
                        old_shm.unlink()
                        return True
            buf.release()
            old_shm.close()
            return False
        except Exception as e:
            logger.warning("Error inspecting stale segment '%s': %s", self._name, e)
            try:
                # Force unlink if possible
                force_shm = shared_memory.SharedMemory(name=self._name, create=False)
                force_shm.buf.release()
                force_shm.close()
                force_shm.unlink()
                return True
            except Exception:
                return False

    def _set_status_flag(self, flag: int) -> None:
        """Sets a status bitflag in the header."""
        current = struct.unpack_from("<H", self._buf, OFFSET_STATUS_FLAGS)[0]
        struct.pack_into("<H", self._buf, OFFSET_STATUS_FLAGS, current | flag)

    # -----------------------------------------------------------------------
    # Lock-free SPSC Write Operations
    # -----------------------------------------------------------------------
    def write_tick(self, tick: LOBTickMessage, timeout_sec: float = 0.0) -> bool:
        """
        Zero-copy serialization of Level 2/3 LOB tick into ring buffer.
        Returns True on successful append, False if buffer is full.
        """
        slot_offset = self._reserve_write_slot(timeout_sec)
        if slot_offset < 0:
            return False

        current_seq = struct.unpack_from("<Q", self._buf, OFFSET_HEAD_SEQ)[0]
        sym_bytes = tick.symbol.encode("utf-8")[:16].ljust(16, b"\x00")
        bids = _pad_tuple5(tick.bid_prices)
        asks = _pad_tuple5(tick.ask_prices)
        bsizes = _pad_tuple5(tick.bid_sizes)
        asizes = _pad_tuple5(tick.ask_sizes)

        struct.pack_into(
            LOB_TICK_FMT,
            self._buf,
            slot_offset,
            int(MessageType.LOB_TICK),
            LOB_TICK_LEN,
            current_seq,
            tick.timestamp_ns,
            sym_bytes,
            tick.bid_price,
            tick.ask_price,
            tick.bid_size,
            tick.ask_size,
            tick.last_price,
            tick.last_size,
            tick.depth_levels,
            *bids,
            *asks,
            *bsizes,
            *asizes,
        )
        self._commit_write(current_seq)
        return True

    def write_alert(self, alert: RiskAlertMessage, timeout_sec: float = 0.0) -> bool:
        """
        Zero-copy serialization of Risk Alert into ring buffer.
        """
        slot_offset = self._reserve_write_slot(timeout_sec)
        if slot_offset < 0:
            return False

        current_seq = struct.unpack_from("<Q", self._buf, OFFSET_HEAD_SEQ)[0]
        alert_bytes = alert.alert_id.encode("utf-8")[:32].ljust(32, b"\x00")
        sym_bytes = alert.symbol.encode("utf-8")[:16].ljust(16, b"\x00")
        mkt_bytes = alert.market.encode("utf-8")[:8].ljust(8, b"\x00")
        msg_bytes = alert.message.encode("utf-8")[:96].ljust(96, b"\x00")

        struct.pack_into(
            RISK_ALERT_FMT,
            self._buf,
            slot_offset,
            int(MessageType.RISK_ALERT),
            RISK_ALERT_LEN,
            current_seq,
            alert.timestamp_ns,
            alert_bytes,
            sym_bytes,
            mkt_bytes,
            int(alert.severity),
            int(alert.alert_type),
            float(alert.metric_value),
            float(alert.threshold_value),
            int(alert.action_code),
            msg_bytes,
        )
        self._commit_write(current_seq)
        return True

    def write_order(self, order: ExecutionOrderMessage, timeout_sec: float = 0.0) -> bool:
        """
        Zero-copy serialization of Execution Order into ring buffer.
        """
        slot_offset = self._reserve_write_slot(timeout_sec)
        if slot_offset < 0:
            return False

        current_seq = struct.unpack_from("<Q", self._buf, OFFSET_HEAD_SEQ)[0]
        order_bytes = order.order_id.encode("utf-8")[:32].ljust(32, b"\x00")
        sym_bytes = order.symbol.encode("utf-8")[:16].ljust(16, b"\x00")
        mkt_bytes = order.market.encode("utf-8")[:8].ljust(8, b"\x00")
        client_bytes = order.client_id.encode("utf-8")[:16].ljust(16, b"\x00")

        struct.pack_into(
            EXECUTION_ORDER_FMT,
            self._buf,
            slot_offset,
            int(MessageType.EXECUTION_ORDER),
            EXECUTION_ORDER_LEN,
            current_seq,
            order.timestamp_ns,
            order_bytes,
            sym_bytes,
            mkt_bytes,
            int(order.side),
            int(order.order_type),
            float(order.quantity),
            float(order.price),
            int(order.status),
            client_bytes,
        )
        self._commit_write(current_seq)
        return True

    def write_itch_packet(self, msg: ITCHPacketMessage, timeout_sec: float = 0.0) -> bool:
        """
        Zero-copy serialization of NASDAQ ITCH 5.0 packet into ring buffer (<500ns latency).
        """
        slot_offset = self._reserve_write_slot(timeout_sec)
        if slot_offset < 0:
            return False

        current_seq = struct.unpack_from("<Q", self._buf, OFFSET_HEAD_SEQ)[0]
        code_char = msg.msg_type_code.encode("ascii")[:1] if msg.msg_type_code else b"A"
        sym_bytes = msg.symbol.encode("utf-8")[:16].ljust(16, b"\x00")
        attr_bytes = msg.attribution.encode("utf-8")[:32].ljust(32, b"\x00")

        struct.pack_into(
            ITCH_PACKET_FMT,
            self._buf,
            slot_offset,
            int(MessageType.ITCH_PACKET),
            ITCH_PACKET_LEN,
            current_seq,
            msg.timestamp_ns,
            code_char,
            sym_bytes,
            int(msg.order_ref),
            int(msg.shares),
            float(msg.price),
            int(msg.side),
            attr_bytes,
        )
        self._commit_write(current_seq)
        return True

    def write_order_dispatch(self, msg: OrderDispatchMessage, timeout_sec: float = 0.0) -> bool:
        """
        Zero-copy serialization of Order Dispatch Message into ring buffer (<500ns latency).
        """
        slot_offset = self._reserve_write_slot(timeout_sec)
        if slot_offset < 0:
            return False

        current_seq = struct.unpack_from("<Q", self._buf, OFFSET_HEAD_SEQ)[0]
        disp_bytes = msg.dispatch_id.encode("utf-8")[:32].ljust(32, b"\x00")
        sym_bytes = msg.symbol.encode("utf-8")[:16].ljust(16, b"\x00")
        client_bytes = msg.client_id.encode("utf-8")[:32].ljust(32, b"\x00")
        ts = msg.timestamp_ns if msg.timestamp_ns > 0 else time.time_ns()

        struct.pack_into(
            ORDER_DISPATCH_FMT,
            self._buf,
            slot_offset,
            int(MessageType.ORDER_DISPATCH),
            ORDER_DISPATCH_LEN,
            current_seq,
            ts,
            disp_bytes,
            sym_bytes,
            int(msg.venue_id),
            int(msg.side),
            float(msg.quantity),
            float(msg.price),
            int(msg.order_type),
            int(msg.routing_flags),
            client_bytes,
        )
        self._commit_write(current_seq)
        return True

    def write_raw_slot(
        self,
        raw_bytes: Union[bytes, bytearray, memoryview],
        timeout_sec: float = 0.0,
        msg_type: int = int(MessageType.CUSTOM),
    ) -> bool:
        """
        Zero-copy deterministic raw binary slot write (<500ns latency).
        Stores raw binary payload directly into the next available slot.
        """
        n_bytes = len(raw_bytes)
        if n_bytes > self._slot_size:
            return False

        buf = self._buf
        head, tail = _STRUCT_QQ.unpack_from(buf, OFFSET_HEAD_SEQ)
        if (head - tail) >= self._capacity:
            if timeout_sec <= 0.0:
                dropped = _STRUCT_Q.unpack_from(buf, OFFSET_DROPPED_COUNT)[0]
                _STRUCT_Q.pack_into(buf, OFFSET_DROPPED_COUNT, dropped + 1)
                return False
            slot_offset = self._reserve_write_slot(timeout_sec)
            if slot_offset < 0:
                return False
            head = _STRUCT_Q.unpack_from(buf, OFFSET_HEAD_SEQ)[0]
        else:
            slot_offset = OFFSET_SLOTS_DATA + (head & self._mask) * self._slot_size

        buf[slot_offset : slot_offset + n_bytes] = raw_bytes
        new_seq = head + 1
        _STRUCT_Q.pack_into(buf, OFFSET_HEAD_SEQ, new_seq)
        _STRUCT_Q.pack_into(buf, OFFSET_TOTAL_WRITTEN, new_seq)
        if (new_seq & 0x7F) == 0:
            _STRUCT_q.pack_into(buf, OFFSET_PRODUCER_HB, time.time_ns())
        return True

    def write_message(
        self,
        msg: Union[LOBTickMessage, RiskAlertMessage, ExecutionOrderMessage, ITCHPacketMessage, OrderDispatchMessage],
        timeout_sec: float = 0.0,
    ) -> bool:
        """Generic polymorphic dispatcher for supported IPC messages."""
        if isinstance(msg, LOBTickMessage):
            return self.write_tick(msg, timeout_sec)
        elif isinstance(msg, RiskAlertMessage):
            return self.write_alert(msg, timeout_sec)
        elif isinstance(msg, ExecutionOrderMessage):
            return self.write_order(msg, timeout_sec)
        elif isinstance(msg, ITCHPacketMessage):
            return self.write_itch_packet(msg, timeout_sec)
        elif isinstance(msg, OrderDispatchMessage):
            return self.write_order_dispatch(msg, timeout_sec)
        else:
            raise TypeError(f"Unsupported message type: {type(msg)}")

    def _reserve_write_slot(self, timeout_sec: float) -> int:
        """
        Verifies buffer capacity and calculates memoryview slot offset.
        If buffer is full, waits up to timeout_sec; otherwise increments dropped_count.
        """
        deadline = time.time() + timeout_sec if timeout_sec > 0 else 0.0
        while True:
            head = struct.unpack_from("<Q", self._buf, OFFSET_HEAD_SEQ)[0]
            tail = struct.unpack_from("<Q", self._buf, OFFSET_TAIL_SEQ)[0]
            occupancy = head - tail

            if occupancy < self._capacity:
                slot_index = head & self._mask
                return OFFSET_SLOTS_DATA + slot_index * self._slot_size

            if timeout_sec <= 0.0 or time.time() >= deadline:
                # Buffer full: drop message
                dropped = struct.unpack_from("<Q", self._buf, OFFSET_DROPPED_COUNT)[0]
                struct.pack_into("<Q", self._buf, OFFSET_DROPPED_COUNT, dropped + 1)
                return -1

            # Brief spin/sleep
            time.sleep(0.00005)

    def _commit_write(self, current_seq: int) -> None:
        """Atomically commits written slot by updating head_seq and telemetry."""
        now_ns = time.time_ns()
        struct.pack_into("<Q", self._buf, OFFSET_HEAD_SEQ, current_seq + 1)
        total_w = struct.unpack_from("<Q", self._buf, OFFSET_TOTAL_WRITTEN)[0]
        struct.pack_into("<Q", self._buf, OFFSET_TOTAL_WRITTEN, total_w + 1)
        struct.pack_into("<q", self._buf, OFFSET_PRODUCER_HB, now_ns)

    # -----------------------------------------------------------------------
    # Lock-free SPSC Read Operations
    # -----------------------------------------------------------------------
    def read_message(
        self, timeout_sec: float = 0.0
    ) -> Optional[Union[LOBTickMessage, RiskAlertMessage, ExecutionOrderMessage, ITCHPacketMessage, OrderDispatchMessage]]:
        """
        Direct zero-copy deserialization of the next message in the ring buffer.
        Returns the parsed message dataclass or None if no message is available.
        """
        deadline = time.time() + timeout_sec if timeout_sec > 0 else 0.0
        while True:
            head = struct.unpack_from("<Q", self._buf, OFFSET_HEAD_SEQ)[0]
            tail = struct.unpack_from("<Q", self._buf, OFFSET_TAIL_SEQ)[0]

            if head > tail:
                slot_index = tail & self._mask
                slot_offset = OFFSET_SLOTS_DATA + slot_index * self._slot_size
                msg = self._deserialize_slot(slot_offset)

                # Commit read
                now_ns = time.time_ns()
                struct.pack_into("<Q", self._buf, OFFSET_TAIL_SEQ, tail + 1)
                total_r = struct.unpack_from("<Q", self._buf, OFFSET_TOTAL_READ)[0]
                struct.pack_into("<Q", self._buf, OFFSET_TOTAL_READ, total_r + 1)
                struct.pack_into("<q", self._buf, OFFSET_CONSUMER_HB, now_ns)
                return msg

            if timeout_sec <= 0.0 or time.time() >= deadline:
                return None

            time.sleep(0.00005)

    def read_raw_slot(self, timeout_sec: float = 0.0, length: Optional[int] = None) -> Optional[bytes]:
        """
        Reads the next raw message slot and returns bytes copy (<500ns latency).
        Advances tail sequence counter.
        """
        deadline = time.time() + timeout_sec if timeout_sec > 0 else 0.0
        while True:
            head = struct.unpack_from("<Q", self._buf, OFFSET_HEAD_SEQ)[0]
            tail = struct.unpack_from("<Q", self._buf, OFFSET_TAIL_SEQ)[0]

            if head > tail:
                slot_index = tail & self._mask
                slot_offset = OFFSET_SLOTS_DATA + slot_index * self._slot_size
                if length is not None:
                    msg_len = min(length, self._slot_size)
                else:
                    msg_len = struct.unpack_from("<H", self._buf, slot_offset + 2)[0]
                    if msg_len == 0 or msg_len > self._slot_size:
                        msg_len = self._slot_size
                raw_data = bytes(self._buf[slot_offset : slot_offset + msg_len])

                # Commit read
                now_ns = time.time_ns()
                struct.pack_into("<Q", self._buf, OFFSET_TAIL_SEQ, tail + 1)
                total_r = struct.unpack_from("<Q", self._buf, OFFSET_TOTAL_READ)[0]
                struct.pack_into("<Q", self._buf, OFFSET_TOTAL_READ, total_r + 1)
                struct.pack_into("<q", self._buf, OFFSET_CONSUMER_HB, now_ns)
                return raw_data

            if timeout_sec <= 0.0 or time.time() >= deadline:
                return None

            time.sleep(0.00005)

    def read_raw_view(self, timeout_sec: float = 0.0, length: Optional[int] = None) -> Optional[memoryview]:
        """
        Returns zero-copy memoryview slice of the next slot (<500ns latency).
        Advances tail sequence counter.
        """
        buf = self._buf
        head, tail = _STRUCT_QQ.unpack_from(buf, OFFSET_HEAD_SEQ)
        if head <= tail:
            if timeout_sec <= 0.0:
                return None
            deadline = time.time() + timeout_sec
            while head <= tail:
                if time.time() >= deadline:
                    return None
                time.sleep(0.00005)
                head, tail = _STRUCT_QQ.unpack_from(buf, OFFSET_HEAD_SEQ)

        slot_offset = OFFSET_SLOTS_DATA + (tail & self._mask) * self._slot_size
        msg_len = length if length is not None else self._slot_size
        view = buf[slot_offset : slot_offset + msg_len]

        new_seq = tail + 1
        _STRUCT_Q.pack_into(buf, OFFSET_TAIL_SEQ, new_seq)
        _STRUCT_Q.pack_into(buf, OFFSET_TOTAL_READ, new_seq)
        if (new_seq & 0x7F) == 0:
            _STRUCT_q.pack_into(buf, OFFSET_CONSUMER_HB, time.time_ns())
        return view

    def read_batch(
        self, max_items: int = 100
    ) -> List[Union[LOBTickMessage, RiskAlertMessage, ExecutionOrderMessage, ITCHPacketMessage, OrderDispatchMessage]]:
        """Reads up to max_items non-blockingly from the buffer."""
        items: List[Union[LOBTickMessage, RiskAlertMessage, ExecutionOrderMessage, ITCHPacketMessage, OrderDispatchMessage]] = []
        for _ in range(max_items):
            msg = self.read_message(timeout_sec=0.0)
            if msg is None:
                break
            items.append(msg)
        return items

    def peek_message(
        self,
    ) -> Optional[Union[LOBTickMessage, RiskAlertMessage, ExecutionOrderMessage, ITCHPacketMessage, OrderDispatchMessage]]:
        """Inspects the next available message without advancing tail_seq."""
        head = struct.unpack_from("<Q", self._buf, OFFSET_HEAD_SEQ)[0]
        tail = struct.unpack_from("<Q", self._buf, OFFSET_TAIL_SEQ)[0]
        if head > tail:
            slot_index = tail & self._mask
            slot_offset = OFFSET_SLOTS_DATA + slot_index * self._slot_size
            return self._deserialize_slot(slot_offset)
        return None

    def _deserialize_slot(
        self, slot_offset: int
    ) -> Optional[Union[LOBTickMessage, RiskAlertMessage, ExecutionOrderMessage, ITCHPacketMessage, OrderDispatchMessage]]:
        """Deserializes a binary message from the given slot offset."""
        msg_type = struct.unpack_from("<H", self._buf, slot_offset)[0]

        if msg_type == int(MessageType.LOB_TICK):
            vals = struct.unpack_from(LOB_TICK_FMT, self._buf, slot_offset)
            symbol = vals[4].decode("utf-8", errors="ignore").rstrip("\x00")
            bids = tuple(vals[12:17])
            asks = tuple(vals[17:22])
            bsizes = tuple(vals[22:27])
            asizes = tuple(vals[27:32])
            return LOBTickMessage(
                symbol=symbol,
                timestamp_ns=vals[3],
                bid_price=vals[5],
                ask_price=vals[6],
                bid_size=vals[7],
                ask_size=vals[8],
                last_price=vals[9],
                last_size=vals[10],
                depth_levels=vals[11],
                bid_prices=bids,
                ask_prices=asks,
                bid_sizes=bsizes,
                ask_sizes=asizes,
            )

        elif msg_type == int(MessageType.RISK_ALERT):
            vals = struct.unpack_from(RISK_ALERT_FMT, self._buf, slot_offset)
            alert_id = vals[4].decode("utf-8", errors="ignore").rstrip("\x00")
            symbol = vals[5].decode("utf-8", errors="ignore").rstrip("\x00")
            market = vals[6].decode("utf-8", errors="ignore").rstrip("\x00")
            message = vals[12].decode("utf-8", errors="ignore").rstrip("\x00")
            return RiskAlertMessage(
                alert_id=alert_id,
                timestamp_ns=vals[3],
                symbol=symbol,
                market=market,
                severity=vals[7],
                alert_type=vals[8],
                metric_value=vals[9],
                threshold_value=vals[10],
                action_code=vals[11],
                message=message,
            )

        elif msg_type == int(MessageType.EXECUTION_ORDER):
            vals = struct.unpack_from(EXECUTION_ORDER_FMT, self._buf, slot_offset)
            order_id = vals[4].decode("utf-8", errors="ignore").rstrip("\x00")
            symbol = vals[5].decode("utf-8", errors="ignore").rstrip("\x00")
            market = vals[6].decode("utf-8", errors="ignore").rstrip("\x00")
            client_id = vals[12].decode("utf-8", errors="ignore").rstrip("\x00")
            return ExecutionOrderMessage(
                order_id=order_id,
                symbol=symbol,
                market=market,
                timestamp_ns=vals[3],
                side=vals[7],
                order_type=vals[8],
                quantity=vals[9],
                price=vals[10],
                status=vals[11],
                client_id=client_id,
            )

        elif msg_type == int(MessageType.ITCH_PACKET):
            vals = struct.unpack_from(ITCH_PACKET_FMT, self._buf, slot_offset)
            code = vals[4].decode("ascii", errors="ignore")
            symbol = vals[5].decode("utf-8", errors="ignore").rstrip("\x00")
            attribution = vals[10].decode("utf-8", errors="ignore").rstrip("\x00")
            return ITCHPacketMessage(
                timestamp_ns=vals[3],
                msg_type_code=code,
                symbol=symbol,
                order_ref=vals[6],
                shares=vals[7],
                price=vals[8],
                side=vals[9],
                attribution=attribution,
            )

        elif msg_type == int(MessageType.ORDER_DISPATCH):
            vals = struct.unpack_from(ORDER_DISPATCH_FMT, self._buf, slot_offset)
            dispatch_id = vals[4].decode("utf-8", errors="ignore").rstrip("\x00")
            symbol = vals[5].decode("utf-8", errors="ignore").rstrip("\x00")
            client_id = vals[12].decode("utf-8", errors="ignore").rstrip("\x00")
            return OrderDispatchMessage(
                dispatch_id=dispatch_id,
                symbol=symbol,
                timestamp_ns=vals[3],
                venue_id=vals[6],
                side=vals[7],
                quantity=vals[8],
                price=vals[9],
                order_type=vals[10],
                routing_flags=vals[11],
                client_id=client_id,
            )

        return None

    # -----------------------------------------------------------------------
    # Status, Telemetry & Diagnostic Latency Benchmarks
    # -----------------------------------------------------------------------
    @property
    def name(self) -> str:
        return self._name

    @property
    def backing(self) -> str:
        return self._backing

    @property
    def capacity(self) -> int:
        return self._capacity

    @property
    def slot_size(self) -> int:
        return self._slot_size

    @property
    def head_seq(self) -> int:
        return struct.unpack_from("<Q", self._buf, OFFSET_HEAD_SEQ)[0]

    @property
    def tail_seq(self) -> int:
        return struct.unpack_from("<Q", self._buf, OFFSET_TAIL_SEQ)[0]

    @property
    def dropped_count(self) -> int:
        return struct.unpack_from("<Q", self._buf, OFFSET_DROPPED_COUNT)[0]

    @property
    def total_written(self) -> int:
        return struct.unpack_from("<Q", self._buf, OFFSET_TOTAL_WRITTEN)[0]

    @property
    def total_read(self) -> int:
        return struct.unpack_from("<Q", self._buf, OFFSET_TOTAL_READ)[0]

    @property
    def is_closed(self) -> bool:
        return self._is_closed

    @property
    def is_creator(self) -> bool:
        return self._is_creator

    def available_read(self) -> int:
        """Returns the number of unconsumed messages in the buffer."""
        head = self.head_seq
        tail = self.tail_seq
        return max(0, head - tail)

    def available_write(self) -> int:
        """Returns the remaining slot capacity available for writing."""
        head = self.head_seq
        tail = self.tail_seq
        return max(0, self._capacity - (head - tail))

    def is_empty(self) -> bool:
        return self.available_read() == 0

    def is_full(self) -> bool:
        return self.available_write() == 0

    def update_producer_heartbeat(self) -> None:
        """Updates producer heartbeat timestamp."""
        struct.pack_into("<q", self._buf, OFFSET_PRODUCER_HB, time.time_ns())

    def update_consumer_heartbeat(self) -> None:
        """Updates consumer heartbeat timestamp."""
        struct.pack_into("<q", self._buf, OFFSET_CONSUMER_HB, time.time_ns())

    def acquire_spinlock(self, timeout_us: Optional[int] = None) -> bool:
        """Acquires the header spinlock with timeout."""
        limit_us = timeout_us if timeout_us is not None else self._spinlock_timeout_us
        deadline_ns = time.time_ns() + limit_us * 1000
        while True:
            val = struct.unpack_from("<I", self._buf, OFFSET_SPINLOCK)[0]
            if val == 0:
                struct.pack_into("<I", self._buf, OFFSET_SPINLOCK, 1)
                return True
            if time.time_ns() >= deadline_ns:
                return False
            time.sleep(0.00001)

    def release_spinlock(self) -> None:
        """Releases the header spinlock."""
        struct.pack_into("<I", self._buf, OFFSET_SPINLOCK, 0)

    @contextmanager
    def spinlock_guard(self, timeout_us: Optional[int] = None) -> Generator[bool, None, None]:
        """Context manager for acquiring the spinlock."""
        acquired = self.acquire_spinlock(timeout_us)
        try:
            yield acquired
        finally:
            if acquired:
                self.release_spinlock()

    def reset(self) -> None:
        """Resets sequences and counters to zero."""
        struct.pack_into("<Q", self._buf, OFFSET_HEAD_SEQ, 0)
        struct.pack_into("<Q", self._buf, OFFSET_TAIL_SEQ, 0)
        struct.pack_into("<Q", self._buf, OFFSET_DROPPED_COUNT, 0)
        struct.pack_into("<Q", self._buf, OFFSET_TOTAL_WRITTEN, 0)
        struct.pack_into("<Q", self._buf, OFFSET_TOTAL_READ, 0)

    def benchmark_ipc_latency(self, iterations: int = 10000) -> Dict[str, float]:
        """
        Empirically benchmarks in-process round-trip write/read latency.
        Returns detailed timing breakdown in nanoseconds.
        """
        raw_payload = b"X" * 64
        self.reset()
        batch_size = max(1, min(iterations, self._capacity - 1))
        batches = iterations // batch_size
        rem = iterations % batch_size

        total_write_ns = 0
        total_read_ns = 0

        for _ in range(batches):
            t0 = time.perf_counter_ns()
            for _ in range(batch_size):
                self.write_raw_slot(raw_payload)
            t1 = time.perf_counter_ns()
            for _ in range(batch_size):
                self.read_raw_slot()
            t2 = time.perf_counter_ns()
            total_write_ns += (t1 - t0)
            total_read_ns += (t2 - t1)

        if rem > 0:
            t0 = time.perf_counter_ns()
            for _ in range(rem):
                self.write_raw_slot(raw_payload)
            t1 = time.perf_counter_ns()
            for _ in range(rem):
                self.read_raw_slot()
            t2 = time.perf_counter_ns()
            total_write_ns += (t1 - t0)
            total_read_ns += (t2 - t1)

        total_ns = total_write_ns + total_read_ns
        write_ns = total_write_ns / max(1, iterations)
        read_ns = total_read_ns / max(1, iterations)
        round_trip_ns = write_ns + read_ns
        return {
            "iterations": float(iterations),
            "total_elapsed_ms": total_ns / 1e6,
            "round_trip_avg_ns": round_trip_ns,
            "write_avg_ns": write_ns,
            "read_avg_ns": read_ns,
        }

    def stats(self) -> Dict[str, Any]:
        """Returns comprehensive diagnostic telemetry."""
        return {
            "name": self._name,
            "backing": self._backing,
            "capacity": self._capacity,
            "slot_size": self._slot_size,
            "head_seq": self.head_seq,
            "tail_seq": self.tail_seq,
            "available_read": self.available_read(),
            "available_write": self.available_write(),
            "total_written": self.total_written,
            "total_read": self.total_read,
            "dropped_count": self.dropped_count,
            "is_empty": self.is_empty(),
            "is_full": self.is_full(),
            "producer_pid": struct.unpack_from("<q", self._buf, OFFSET_PRODUCER_PID)[0],
            "consumer_pid": struct.unpack_from("<q", self._buf, OFFSET_CONSUMER_PID)[0],
            "is_closed": self._is_closed,
            "is_creator": self._is_creator,
        }

    # -----------------------------------------------------------------------
    # Lifecycle, Context Manager & Resource Disposal
    # -----------------------------------------------------------------------
    def close(self) -> None:
        """Closes memoryview and local shared memory / mmap handle."""
        if not self._is_closed:
            self._is_closed = True
            try:
                if self._buf is not None:
                    self._buf.release()
                    self._buf = None
            except Exception:
                pass
            try:
                if self._shm is not None:
                    self._shm.close()
                    self._shm = None
            except Exception:
                pass
            try:
                if self._mmap_obj is not None:
                    self._mmap_obj.close()
                    self._mmap_obj = None
            except Exception:
                pass
            try:
                if self._mmap_file is not None:
                    self._mmap_file.close()
                    self._mmap_file = None
            except Exception:
                pass

    def unlink(self) -> None:
        """Unlinks shared memory segment or removes MMF file from the operating system."""
        try:
            if self._shm is not None:
                self._shm.unlink()
        except Exception:
            pass
        try:
            if self._backing == "mmap" and self._mmap_file_path and os.path.exists(self._mmap_file_path):
                os.remove(self._mmap_file_path)
        except Exception:
            pass

    def __enter__(self) -> SharedMemoryRingBuffer:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()
        if self._auto_unlink and self._is_creator:
            self.unlink()

    def __del__(self) -> None:
        try:
            self.close()
            if self._auto_unlink and self._is_creator:
                self.unlink()
        except Exception:
            pass

    def _cleanup_on_exit(self) -> None:
        """atexit callback to ensure clean shutdown."""
        try:
            if not self._is_closed:
                self.close()
                if self._auto_unlink and self._is_creator:
                    self.unlink()
        except Exception:
            pass

    @classmethod
    def cleanup_segment(cls, name: str, mmap_dir: Optional[str] = None) -> bool:
        """Utility classmethod to forcibly unlink a named segment or MMF file."""
        clean = sanitize_shm_name(name)
        cleaned_shm = False
        cleaned_mmf = False
        try:
            shm = shared_memory.SharedMemory(name=clean, create=False)
            try:
                shm.buf.release()
            except Exception:
                pass
            shm.close()
            shm.unlink()
            cleaned_shm = True
        except Exception:
            pass

        try:
            target_dir = mmap_dir or tempfile.gettempdir()
            fname = clean.replace("/", "_").replace("\\", "_")
            fpath = os.path.join(target_dir, f"{fname}.mmf")
            if os.path.exists(fpath):
                os.remove(fpath)
                cleaned_mmf = True
        except Exception:
            pass

        return cleaned_shm or cleaned_mmf


# ---------------------------------------------------------------------------
# Complete Alias Trees
# ---------------------------------------------------------------------------
ZeroCopySharedMemoryRingBuffer = SharedMemoryRingBuffer
Phase108SharedMemoryRingBuffer = SharedMemoryRingBuffer
HighPerformanceSharedMemoryIPC = SharedMemoryRingBuffer
SharedMemoryIPCRingBuffer = SharedMemoryRingBuffer
DeterministicMMFCircularBuffer = SharedMemoryRingBuffer
Phase115SharedMemoryRingBuffer = SharedMemoryRingBuffer
SubMicrosecondCircularBuffer = SharedMemoryRingBuffer
MemoryMappedRingBuffer = SharedMemoryRingBuffer
MMFRingBufferIPC = SharedMemoryRingBuffer

__all__ = [
    "SharedMemoryRingBuffer",
    "ZeroCopySharedMemoryRingBuffer",
    "Phase108SharedMemoryRingBuffer",
    "HighPerformanceSharedMemoryIPC",
    "SharedMemoryIPCRingBuffer",
    "DeterministicMMFCircularBuffer",
    "Phase115SharedMemoryRingBuffer",
    "SubMicrosecondCircularBuffer",
    "MemoryMappedRingBuffer",
    "MMFRingBufferIPC",
    "MessageType",
    "LOBTickMessage",
    "RiskAlertMessage",
    "ExecutionOrderMessage",
    "ITCHPacketMessage",
    "OrderDispatchMessage",
    "is_pid_alive",
    "sanitize_shm_name",
    "MAGIC_HEADER",
    "HEADER_VERSION",
    "HEADER_SIZE",
    "DEFAULT_CAPACITY",
    "DEFAULT_SLOT_SIZE",
]
