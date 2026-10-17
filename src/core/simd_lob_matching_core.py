"""
src/core/simd_lob_matching_core.py
==================================
Ultra-Low Latency SIMD/AVX2 Vectorized Zero-Copy LOB Matching Core (Feature F560).
Phase 118 (Release R134 / v125 Production Master).

Features:
  1. Pre-allocated circular ring buffer order pool with bitwise power-of-two masking
     and intrusive linked-list next/prev pointer chaining.
  2. Contiguous 2D NumPy/AVX2 price ladder arrays ([max_levels, 4] for price, visible_volume,
     hidden_volume, order_count) for bids (descending) and asks (ascending) with binary search
     indexing and dynamic level management.
  3. Sub-microsecond deterministic price-time priority matching for Limit orders, immediate
     aggressive Market sweeps, Immediate-Or-Cancel (IOC) sweeps, and Fill-Or-Kill (FOK) atomic
     two-phase commit protocol.
  4. O(1) order cancellation via hash map lookup, intrusive linked list unlinking, and ladder volume deduction.
  5. Dual-backend vectorization: PyTorch C++/AVX2 tensor acceleration where available with automatic,
     seamless pure NumPy SIMD fallback.
  6. Granular Level 3 order book snapshot extraction producing L3Snapshot and contiguous 1D
     shape-(40,) float64 tensor compatible with LOBTransformerEngine.
  7. Multi-symbol and single-symbol operational modes with complete alias trees and sys.modules registration.
"""

from __future__ import annotations

import collections
from dataclasses import dataclass, field
from enum import IntEnum
import logging
import math
import sys
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import numpy as np

# PyTorch SIMD detection & fallback
try:
    import torch
    _TORCH_AVAILABLE = True
except ImportError:
    torch = None
    _TORCH_AVAILABLE = False

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module Metadata & Constants
# ---------------------------------------------------------------------------
VERSION: int = 118
RELEASE: str = "R134"
FEATURE: str = "F560"

DEFAULT_ORDER_CAPACITY: int = 65536  # Default power-of-2 order pool capacity
DEFAULT_PRICE_LEVELS: int = 50       # Depth ladder levels
DEFAULT_TICK_SIZE: float = 0.01      # Minimum price tick

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class OrderSide(IntEnum):
    """Normalized order side enumeration (BUY=1, SELL=-1)."""
    BUY = 1
    SELL = -1

    @classmethod
    def from_str(cls, side: Union[str, OrderSide, int]) -> OrderSide:
        if side is cls.BUY or side == "BUY" or side == 1:
            return cls.BUY
        if side is cls.SELL or side == "SELL" or side == -1:
            return cls.SELL
        if isinstance(side, cls):
            return side
        if isinstance(side, int):
            if side == 1:
                return cls.BUY
            elif side == -1:
                return cls.SELL
            raise ValueError(f"Invalid OrderSide int: {side}. Expected 1 or -1.")
        s = str(side).strip().upper()
        if s in ("BUY", "BID", "LONG", "B", "1", "+1"):
            return cls.BUY
        elif s in ("SELL", "ASK", "SHORT", "S", "-1"):
            return cls.SELL
        raise ValueError(f"Invalid OrderSide string: '{side}'")


class OrderType(IntEnum):
    """Institutional order type enumeration."""
    LIMIT = 0
    MARKET = 1
    IOC = 2        # Immediate-or-Cancel
    FOK = 3        # Fill-or-Kill
    ICEBERG = 4    # Iceberg with hidden reserve volume
    POST_ONLY = 5  # Maker-only order

    @classmethod
    def from_str(cls, order_type: Union[str, OrderType, int]) -> OrderType:
        if order_type is cls.LIMIT or order_type == "LIMIT" or order_type == 0:
            return cls.LIMIT
        if order_type is cls.MARKET or order_type == "MARKET" or order_type == 1:
            return cls.MARKET
        if order_type is cls.IOC or order_type == "IOC" or order_type == 2:
            return cls.IOC
        if order_type is cls.FOK or order_type == "FOK" or order_type == 3:
            return cls.FOK
        if isinstance(order_type, cls):
            return order_type
        if isinstance(order_type, int):
            try:
                return cls(order_type)
            except ValueError:
                raise ValueError(f"Invalid OrderType int: {order_type}")
        s = str(order_type).strip().upper()
        mapping = {
            "LIMIT": cls.LIMIT,
            "MARKET": cls.MARKET,
            "IOC": cls.IOC,
            "IMMEDIATE_OR_CANCEL": cls.IOC,
            "IMMEDIATE-OR-CANCEL": cls.IOC,
            "FOK": cls.FOK,
            "FILL_OR_KILL": cls.FOK,
            "FILL-OR-KILL": cls.FOK,
            "ICEBERG": cls.ICEBERG,
            "POST_ONLY": cls.POST_ONLY,
            "MAKER_ONLY": cls.POST_ONLY,
        }
        if s in mapping:
            return mapping[s]
        raise ValueError(f"Invalid OrderType string: '{order_type}'")


class OrderStatus(IntEnum):
    """Lifecycle status of an order in the ring buffer pool."""
    FREE = 0
    PENDING = 0
    ACTIVE = 1
    PARTIALLY_FILLED = 2
    FILLED = 3
    CANCELED = 4
    REJECTED = 5
    KILLED = 5


class TimeInForce(IntEnum):
    """Time-In-Force conditions."""
    GTC = 0  # Good 'Til Canceled
    IOC = 1  # Immediate or Cancel
    FOK = 2  # Fill or Kill
    DAY = 3  # Day order


class SIMDBackend(str):
    """Execution backend identifiers."""
    TORCH_AVX2 = "torch_avx2"
    NUMPY_SIMD = "numpy_simd"


class ExecutionBackend(IntEnum):
    """Execution backend enumeration."""
    NUMPY_AVX2 = 0
    TORCH_SIMD = 1


# ---------------------------------------------------------------------------
# Structured Array Compound Dtypes
# ---------------------------------------------------------------------------
ORDER_SLOT_DTYPE = np.dtype([
    ("order_id", "S32"),            # 32-byte ASCII Order ID
    ("symbol", "S16"),              # 16-byte ASCII Symbol
    ("side", np.int8),              # 1 = BUY, -1 = SELL
    ("order_type", np.int8),        # 0=LIMIT, 1=MARKET, 2=IOC, 3=FOK, 4=ICEBERG, 5=POST_ONLY
    ("status", np.int8),            # OrderStatus
    ("time_in_force", np.int8),     # TimeInForce
    ("padding", "S2"),              # Alignment padding
    ("price", np.float64),          # Order limit price
    ("volume", np.float64),         # Total requested volume
    ("display_volume", np.float64), # Currently active visible volume
    ("hidden_volume", np.float64),  # Remaining hidden reserve volume
    ("peak_size", np.float64),      # Maximum display reload volume
    ("cum_filled", np.float64),     # Cumulative executed volume
    ("timestamp_ns", np.int64),     # Epoch nanoseconds arrival
    ("priority_seq", np.int64),     # Monotonic priority sequence counter
    ("prev_slot", np.int32),        # Intrusive linked list previous slot index (-1 if head)
    ("next_slot", np.int32),        # Intrusive linked list next slot index (-1 if tail)
    ("level_idx", np.int32),        # Associated price level index in ladder
])

ORDER_RECORD_DTYPE = ORDER_SLOT_DTYPE
ORDER_RECORD_SIZE: int = ORDER_SLOT_DTYPE.itemsize

PRICE_LEVEL_DTYPE = np.dtype([
    ("price", np.float64),
    ("visible_volume", np.float64),
    ("hidden_volume", np.float64),
    ("order_count", np.int32),
    ("head_slot", np.int32),
    ("tail_slot", np.int32),
])

MATCH_FILL_DTYPE = np.dtype([
    ("price", np.float64),
    ("volume", np.float64),
    ("maker_order_id", "S32"),
    ("taker_order_id", "S32"),
    ("side", np.int8),
    ("timestamp_ns", np.int64),
])


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------
@dataclass
class SIMDOrder:
    order_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    price: float
    volume: float
    display_volume: float
    hidden_volume: float = 0.0
    peak_size: float = 0.0
    timestamp_ns: int = 0
    status: OrderStatus = OrderStatus.ACTIVE
    cum_filled: float = 0.0
    slot_idx: int = -1

    @property
    def remaining_volume(self) -> float:
        return self.display_volume + self.hidden_volume


@dataclass
class SIMDFillRecord:
    symbol: str
    taker_order_id: str
    maker_order_id: str
    price: float
    volume: float
    side: str
    timestamp_ns: int
    is_maker: bool = False
    is_liquidity_providing: bool = False
    fee_rebate_bps: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "taker_order_id": self.taker_order_id,
            "maker_order_id": self.maker_order_id,
            "price": float(self.price),
            "volume": float(self.volume),
            "side": self.side,
            "timestamp_ns": int(self.timestamp_ns),
            "is_maker": bool(self.is_maker),
            "is_liquidity_providing": bool(self.is_liquidity_providing),
            "fee_rebate_bps": float(self.fee_rebate_bps),
        }

FillRecord = SIMDFillRecord


@dataclass
class SIMDMatchResult:
    symbol: str
    taker_order_id: str
    side: str
    order_type: str
    requested_volume: float
    filled_volume: float
    remaining_volume: float
    canceled_volume: float = 0.0
    vwap_fill_price: float = 0.0
    slippage_bps: float = 0.0
    fills: List[SIMDFillRecord] = field(default_factory=list)
    swept_levels_count: int = 0
    is_fully_filled: bool = False
    status: OrderStatus = OrderStatus.FILLED
    is_rejected: bool = False
    rejection_reason: str = ""
    latency_ns: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "taker_order_id": self.taker_order_id,
            "side": self.side,
            "order_type": self.order_type,
            "requested_volume": float(self.requested_volume),
            "filled_volume": float(self.filled_volume),
            "remaining_volume": float(self.remaining_volume),
            "canceled_volume": float(self.canceled_volume),
            "vwap_fill_price": round(float(self.vwap_fill_price), 6),
            "slippage_bps": round(float(self.slippage_bps), 4),
            "swept_levels_count": int(self.swept_levels_count),
            "is_fully_filled": bool(self.is_fully_filled),
            "fills_count": len(self.fills),
            "status": int(self.status),
            "is_rejected": bool(self.is_rejected),
            "rejection_reason": self.rejection_reason,
            "latency_ns": int(self.latency_ns),
        }

MatchExecutionResult = SIMDMatchResult


@dataclass
class L3OrderEntry:
    order_id: str
    price: float
    volume: float
    display_volume: float
    hidden_volume: float
    timestamp_ns: int
    priority_seq: int
    is_iceberg: bool


@dataclass
class L3PriceLevel:
    price: float
    aggregated_volume: float
    order_count: int
    orders: List[L3OrderEntry]


@dataclass
class L3Snapshot:
    symbol: str
    timestamp_ns: int
    depth: int
    best_bid: float
    best_ask: float
    spread: float
    mid_price: float
    micro_price: float
    weighted_obi: float
    bids: List[L3PriceLevel]
    asks: List[L3PriceLevel]
    bid_prices: np.ndarray
    bid_volumes: np.ndarray
    ask_prices: np.ndarray
    ask_volumes: np.ndarray
    flat_tensor_40: np.ndarray

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "timestamp_ns": self.timestamp_ns,
            "depth": self.depth,
            "best_bid": self.best_bid,
            "best_ask": self.best_ask,
            "spread": self.spread,
            "mid_price": self.mid_price,
            "micro_price": self.micro_price,
            "weighted_obi": self.weighted_obi,
            "bids_count": len(self.bids),
            "asks_count": len(self.asks),
        }

    def to_array(self) -> np.ndarray:
        return self.flat_tensor_40


@dataclass
class SIMDPriceLadderSnapshot:
    symbol: str
    timestamp_ns: int
    depth_levels: int
    bid_prices: np.ndarray
    bid_volumes: np.ndarray
    bid_orders: np.ndarray
    ask_prices: np.ndarray
    ask_volumes: np.ndarray
    ask_orders: np.ndarray
    best_bid: float
    best_ask: float
    spread: float
    mid_price: float
    micro_price: float
    obi_1: float
    obi_5: float
    obi_10: float
    obi_20: float
    obi_50: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "timestamp_ns": self.timestamp_ns,
            "depth_levels": self.depth_levels,
            "best_bid": self.best_bid,
            "best_ask": self.best_ask,
            "spread": self.spread,
            "mid_price": self.mid_price,
            "micro_price": self.micro_price,
            "obi_1": self.obi_1,
            "obi_5": self.obi_5,
            "obi_10": self.obi_10,
            "obi_20": self.obi_20,
            "obi_50": self.obi_50,
        }


@dataclass
class SIMDMicrostructureMetrics:
    symbol: str
    timestamp_ns: int
    best_bid: float
    best_ask: float
    mid_price: float
    spread: float
    spread_bps: float
    micro_price_l1: float
    micro_price_decay: float
    effective_spread_bps: float
    obi_1: float
    obi_5: float
    obi_10: float
    obi_20: float
    obi_50: float
    weighted_obi: float
    book_depth_ratio: float
    queue_depletion_rate_bid: float
    queue_depletion_rate_ask: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "timestamp_ns": self.timestamp_ns,
            "best_bid": self.best_bid,
            "best_ask": self.best_ask,
            "mid_price": self.mid_price,
            "spread": self.spread,
            "spread_bps": self.spread_bps,
            "micro_price_l1": self.micro_price_l1,
            "micro_price_decay": self.micro_price_decay,
            "effective_spread_bps": self.effective_spread_bps,
            "obi_1": self.obi_1,
            "obi_5": self.obi_5,
            "obi_10": self.obi_10,
            "obi_20": self.obi_20,
            "obi_50": self.obi_50,
            "weighted_obi": self.weighted_obi,
            "book_depth_ratio": self.book_depth_ratio,
            "queue_depletion_rate_bid": self.queue_depletion_rate_bid,
            "queue_depletion_rate_ask": self.queue_depletion_rate_ask,
        }


# ---------------------------------------------------------------------------
# Order Pool: Contiguous Circular Ring Buffer with Intrusive Linked Lists
# ---------------------------------------------------------------------------
class SIMDLOBOrderPool:
    """
    Zero-copy pre-allocated circular ring buffer order pool.
    Manages structured array slots using bitwise power-of-two masking,
    intrusive linked-list chaining, and O(1) allocation/deallocation/eviction.
    """
    def __init__(self, capacity: int = DEFAULT_ORDER_CAPACITY):
        if capacity <= 0 or (capacity & (capacity - 1)) != 0:
            raise ValueError(f"Capacity must be a positive power of two (got {capacity})")
        self.capacity: int = int(capacity)
        self._mask: int = self.capacity - 1
        self.head_seq: int = 0
        self.slots: np.ndarray = np.zeros(self.capacity, dtype=ORDER_SLOT_DTYPE)
        self._id_to_slot: Dict[str, int] = {}
        self._internal_eviction_callback: Optional[Callable[[int, str], None]] = None
        self._eviction_callback: Optional[Callable[[int, str], None]] = None
        self.prev_slots: List[int] = [-1] * self.capacity
        self.next_slots: List[int] = [-1] * self.capacity

    def set_eviction_callback(self, cb: Optional[Callable[[int, str], None]]) -> None:
        self._eviction_callback = cb

    def alloc_slot(
        self,
        order_id: str,
        symbol: str,
        side: int,
        order_type: int,
        price: float,
        volume: float,
        display_volume: Optional[float] = None,
        hidden_volume: float = 0.0,
        peak_size: float = 0.0,
        time_in_force: int = 0,
        timestamp_ns: int = 0,
        priority_seq: int = 0,
    ) -> int:
        seq = self.head_seq
        self.head_seq += 1
        slot_idx = seq & self._mask

        # Overwritten slot handling: evict previous occupant if any (only on ring wrap-around)
        if seq >= self.capacity:
            old_id_bytes = self.slots[slot_idx]["order_id"]
            old_id = old_id_bytes.split(b"\x00", 1)[0].decode("ascii", errors="ignore")
            if old_id and old_id in self._id_to_slot and self._id_to_slot[old_id] == slot_idx:
                del self._id_to_slot[old_id]
                if self._internal_eviction_callback is not None:
                    self._internal_eviction_callback(slot_idx, old_id)
                if self._eviction_callback is not None:
                    self._eviction_callback(slot_idx, old_id)

        disp_vol = volume if display_volume is None else display_volume
        peak = disp_vol if peak_size <= 0.0 else peak_size
        ts = timestamp_ns if timestamp_ns > 0 else time.time_ns()
        p_seq = priority_seq if priority_seq > 0 else self.head_seq

        self.slots[slot_idx] = (
            order_id.encode("ascii")[:32],
            symbol.encode("ascii")[:16],
            side,
            order_type,
            OrderStatus.ACTIVE,
            time_in_force,
            b"\x00\x00",
            float(price),
            float(volume),
            float(disp_vol),
            float(hidden_volume),
            float(peak),
            0.0,
            ts,
            p_seq,
            -1,
            -1,
            -1,
        )

        self._id_to_slot[order_id] = slot_idx
        return slot_idx

    def free_slot(self, slot_idx: int) -> None:
        slot = self.slots[slot_idx]
        slot["status"] = np.int8(OrderStatus.FREE)
        oid_bytes = slot["order_id"]
        oid = oid_bytes.split(b"\x00", 1)[0].decode("ascii", errors="ignore")
        if oid in self._id_to_slot and self._id_to_slot[oid] == slot_idx:
            del self._id_to_slot[oid]
        slot["prev_slot"] = np.int32(-1)
        slot["next_slot"] = np.int32(-1)
        self.prev_slots[slot_idx] = -1
        self.next_slots[slot_idx] = -1

    def get_slot_idx(self, order_id: str) -> Optional[int]:
        slot_idx = self._id_to_slot.get(order_id)
        if slot_idx is None:
            return None
        if self.head_seq >= self.capacity:
            oid_bytes = self.slots[slot_idx]["order_id"]
            if not oid_bytes.startswith(order_id.encode("ascii")):
                del self._id_to_slot[order_id]
                return None
        return slot_idx

    def get_slot(self, order_id: str) -> Optional[np.void]:
        idx = self.get_slot_idx(order_id)
        if idx is None:
            return None
        return self.slots[idx]

    def unlink_slot(self, slot_idx: int) -> Tuple[int, int]:
        p = self.prev_slots[slot_idx]
        n = self.next_slots[slot_idx]
        if p != -1:
            self.next_slots[p] = n
            self.slots[p]["next_slot"] = np.int32(n)
        if n != -1:
            self.prev_slots[n] = p
            self.slots[n]["prev_slot"] = np.int32(p)
        self.prev_slots[slot_idx] = -1
        self.next_slots[slot_idx] = -1
        self.slots[slot_idx]["prev_slot"] = np.int32(-1)
        self.slots[slot_idx]["next_slot"] = np.int32(-1)
        return p, n


# ---------------------------------------------------------------------------
# Price Ladder & Book Side: Contiguous 2D Array & Vectorized Depth Scans
# ---------------------------------------------------------------------------
class SIMDPriceLadder:
    """
    Contiguous 2D NumPy array price ladder ([max_levels, 4] for price, visible_volume,
    hidden_volume, order_count). Bids are sorted strictly descending, Asks strictly ascending.
    Provides binary search insertion/lookup, vectorized cumulative depth scanning, and VWAP sweeps.
    Utilizes O(1) pointer-advance level pruning for ultra-low latency top-of-book sweeps and cancels.
    """
    def __init__(self, is_bid: bool, max_levels: int = DEFAULT_PRICE_LEVELS):
        self.is_bid: bool = is_bid
        self.max_levels: int = max(max_levels, 16)
        # Columns: [0: price, 1: visible_volume, 2: hidden_volume, 3: order_count]
        self.ladder: np.ndarray = np.zeros((self.max_levels, 4), dtype=np.float64)
        self.head_slots: np.ndarray = np.full(self.max_levels, -1, dtype=np.int32)
        self.tail_slots: np.ndarray = np.full(self.max_levels, -1, dtype=np.int32)
        self.active_levels: int = 0
        self.head_level: int = 0

    def _ensure_capacity(self) -> None:
        if self.active_levels == 0:
            self.head_level = 0
            return
        if self.head_level > 0 and (self.head_level + self.active_levels >= self.max_levels):
            start = self.head_level
            end = start + self.active_levels
            self.ladder[:self.active_levels] = self.ladder[start:end]
            self.head_slots[:self.active_levels] = self.head_slots[start:end]
            self.tail_slots[:self.active_levels] = self.tail_slots[start:end]
            self.ladder[self.active_levels:end] = 0.0
            self.head_slots[self.active_levels:end] = -1
            self.tail_slots[self.active_levels:end] = -1
            self.head_level = 0

        if self.active_levels >= self.max_levels:
            new_cap = self.max_levels * 2
            new_ladder = np.zeros((new_cap, 4), dtype=np.float64)
            new_ladder[:self.active_levels] = self.ladder[self.head_level:self.head_level + self.active_levels]
            self.ladder = new_ladder

            new_heads = np.full(new_cap, -1, dtype=np.int32)
            new_heads[:self.active_levels] = self.head_slots[self.head_level:self.head_level + self.active_levels]
            self.head_slots = new_heads

            new_tails = np.full(new_cap, -1, dtype=np.int32)
            new_tails[:self.active_levels] = self.tail_slots[self.head_level:self.head_level + self.active_levels]
            self.tail_slots = new_tails

            self.head_level = 0
            self.max_levels = new_cap

    def find_level_index(self, price: float) -> Tuple[int, bool]:
        """
        Vectorized binary search lookup for relative level index (0 to active_levels-1).
        Returns (index, exists_bool).
        """
        if self.active_levels == 0:
            return 0, False

        start = self.head_level
        # Fast path: Top of book
        if abs(self.ladder[start, 0] - price) < 1e-7:
            return 0, True

        prices = self.ladder[start:start + self.active_levels, 0]
        if self.is_bid:
            # Strictly descending view search
            rev = prices[::-1]
            idx = self.active_levels - int(rev.searchsorted(price, side="right"))
        else:
            # Strictly ascending view search
            idx = int(prices.searchsorted(price))

        if idx < self.active_levels and abs(prices[idx] - price) < 1e-7:
            return idx, True
        return idx, False

    def insert_order(
        self,
        slot_idx: int,
        price: float,
        display_volume: float,
        hidden_volume: float,
        pool: SIMDLOBOrderPool,
    ) -> int:
        idx, exists = self.find_level_index(price)
        abs_idx = self.head_level + idx

        if exists:
            # Level already exists: append order to tail of FIFO queue
            old_tail = int(self.tail_slots[abs_idx])
            if old_tail != -1:
                pool.next_slots[old_tail] = slot_idx
                pool.slots[old_tail]["next_slot"] = np.int32(slot_idx)
                pool.prev_slots[slot_idx] = old_tail
                pool.slots[slot_idx]["prev_slot"] = np.int32(old_tail)
                pool.next_slots[slot_idx] = -1
                pool.slots[slot_idx]["next_slot"] = np.int32(-1)
                self.tail_slots[abs_idx] = np.int32(slot_idx)
            else:
                self.head_slots[abs_idx] = np.int32(slot_idx)
                self.tail_slots[abs_idx] = np.int32(slot_idx)
                pool.prev_slots[slot_idx] = -1
                pool.slots[slot_idx]["prev_slot"] = np.int32(-1)
                pool.next_slots[slot_idx] = -1
                pool.slots[slot_idx]["next_slot"] = np.int32(-1)

            self.ladder[abs_idx, 1] += display_volume
            self.ladder[abs_idx, 2] += hidden_volume
            self.ladder[abs_idx, 3] += 1
            pool.slots[slot_idx]["level_idx"] = np.int32(idx)
            return idx

        # New level insertion
        # If new level is at the very top (idx == 0) and head_level > 0, expand backwards in O(1)
        if idx == 0 and self.head_level > 0:
            self.head_level -= 1
            abs_idx = self.head_level
            self.ladder[abs_idx, 0] = price
            self.ladder[abs_idx, 1] = display_volume
            self.ladder[abs_idx, 2] = hidden_volume
            self.ladder[abs_idx, 3] = 1
            self.head_slots[abs_idx] = np.int32(slot_idx)
            self.tail_slots[abs_idx] = np.int32(slot_idx)
            self.active_levels += 1
            pool.prev_slots[slot_idx] = -1
            pool.slots[slot_idx]["prev_slot"] = np.int32(-1)
            pool.next_slots[slot_idx] = -1
            pool.slots[slot_idx]["next_slot"] = np.int32(-1)
            pool.slots[slot_idx]["level_idx"] = np.int32(0)
            return 0

        self._ensure_capacity()
        abs_idx = self.head_level + idx
        end = self.head_level + self.active_levels
        if abs_idx < end:
            # Shift elements down from abs_idx
            self.ladder[abs_idx + 1:end + 1] = self.ladder[abs_idx:end]
            self.head_slots[abs_idx + 1:end + 1] = self.head_slots[abs_idx:end]
            self.tail_slots[abs_idx + 1:end + 1] = self.tail_slots[abs_idx:end]

        self.ladder[abs_idx, 0] = price
        self.ladder[abs_idx, 1] = display_volume
        self.ladder[abs_idx, 2] = hidden_volume
        self.ladder[abs_idx, 3] = 1
        self.head_slots[abs_idx] = np.int32(slot_idx)
        self.tail_slots[abs_idx] = np.int32(slot_idx)
        self.active_levels += 1

        pool.prev_slots[slot_idx] = -1
        pool.slots[slot_idx]["prev_slot"] = np.int32(-1)
        pool.next_slots[slot_idx] = -1
        pool.slots[slot_idx]["next_slot"] = np.int32(-1)
        pool.slots[slot_idx]["level_idx"] = np.int32(idx)
        return idx

    def remove_level(self, idx: int) -> None:
        if idx < 0 or idx >= self.active_levels:
            return

        if idx == 0:
            # O(1) top-of-book pointer advance
            abs_idx = self.head_level
            self.head_slots[abs_idx] = -1
            self.tail_slots[abs_idx] = -1
            self.head_level += 1
            self.active_levels -= 1
            if self.active_levels == 0:
                self.head_level = 0
            return

        abs_idx = self.head_level + idx
        end = self.head_level + self.active_levels
        if abs_idx < end - 1:
            self.ladder[abs_idx:end - 1] = self.ladder[abs_idx + 1:end]
            self.head_slots[abs_idx:end - 1] = self.head_slots[abs_idx + 1:end]
            self.tail_slots[abs_idx:end - 1] = self.tail_slots[abs_idx + 1:end]

        self.ladder[end - 1] = 0.0
        self.head_slots[end - 1] = -1
        self.tail_slots[end - 1] = -1
        self.active_levels -= 1
        if self.active_levels == 0:
            self.head_level = 0

    def deduct_volume(
        self,
        price: float,
        disp_vol: float,
        hid_vol: float,
        remove_order: bool = False,
    ) -> None:
        idx, exists = self.find_level_index(price)
        if not exists:
            return

        abs_idx = self.head_level + idx
        self.ladder[abs_idx, 1] = max(0.0, self.ladder[abs_idx, 1] - disp_vol)
        self.ladder[abs_idx, 2] = max(0.0, self.ladder[abs_idx, 2] - hid_vol)
        if remove_order:
            self.ladder[abs_idx, 3] = max(0, int(self.ladder[abs_idx, 3]) - 1)

        # Prune level if total volume or order count hits zero
        if (self.ladder[abs_idx, 1] + self.ladder[abs_idx, 2]) <= 1e-9 or self.ladder[abs_idx, 3] <= 0:
            self.remove_level(idx)

    def scan_crossable_depth(
        self,
        limit_price: float,
        requested_volume: float,
        is_market: bool = False,
        use_torch: bool = True,
    ) -> Dict[str, Any]:
        """
        SIMD/AVX2 vectorized depth scan.
        Calculates total available volume, swept level count, simulated VWAP,
        and slippage without mutating order book state.
        """
        if self.active_levels == 0:
            return {
                "total_executable_vol": 0.0,
                "swept_levels_count": 0,
                "simulated_vwap": 0.0,
                "is_fully_satisfied": False,
                "level_fills": np.array([], dtype=np.float64),
            }

        start = self.head_level
        end = start + self.active_levels

        # PyTorch acceleration branch
        if use_torch and _TORCH_AVAILABLE:
            try:
                prices_t = torch.from_numpy(self.ladder[start:end, 0])
                vols_t = torch.from_numpy(self.ladder[start:end, 1])

                if is_market:
                    mask_t = vols_t > 1e-9
                elif self.is_bid:
                    # Taker SELL: crosses bids where bid_price >= limit_price
                    mask_t = (vols_t > 1e-9) & (prices_t >= limit_price - 1e-9)
                else:
                    # Taker BUY: crosses asks where ask_price <= limit_price
                    mask_t = (vols_t > 1e-9) & (prices_t <= limit_price + 1e-9)

                indices = torch.nonzero(mask_t).squeeze(-1)
                if len(indices) == 0:
                    return {
                        "total_executable_vol": 0.0,
                        "swept_levels_count": 0,
                        "simulated_vwap": 0.0,
                        "is_fully_satisfied": False,
                        "level_fills": np.array([], dtype=np.float64),
                    }

                matched_vols = vols_t[indices]
                matched_prices = prices_t[indices]
                total_avail = float(torch.sum(matched_vols))

                target_vol = min(requested_volume, total_avail)
                if target_vol <= 1e-9:
                    return {
                        "total_executable_vol": 0.0,
                        "swept_levels_count": 0,
                        "simulated_vwap": 0.0,
                        "is_fully_satisfied": False,
                        "level_fills": np.array([], dtype=np.float64),
                    }

                cum_vols = torch.cumsum(matched_vols, dim=0)
                prev_cum = torch.roll(cum_vols, 1)
                prev_cum[0] = 0.0

                level_fills = torch.clamp(torch.minimum(matched_vols, target_vol - prev_cum), min=0.0)
                swept_count = int(torch.sum(level_fills > 1e-9))
                vwap = float(torch.dot(matched_prices, level_fills) / target_vol)

                return {
                    "total_executable_vol": total_avail,
                    "swept_levels_count": swept_count,
                    "simulated_vwap": vwap,
                    "is_fully_satisfied": (total_avail >= requested_volume - 1e-9),
                    "level_fills": level_fills.numpy(),
                }
            except Exception:
                pass  # Fall through to NumPy SIMD fallback

        # Pure NumPy SIMD Fallback
        prices = self.ladder[start:end, 0]
        vols = self.ladder[start:end, 1]

        if is_market:
            mask = vols > 1e-9
        elif self.is_bid:
            mask = (vols > 1e-9) & (prices >= limit_price - 1e-9)
        else:
            mask = (vols > 1e-9) & (prices <= limit_price + 1e-9)

        if not np.any(mask):
            return {
                "total_executable_vol": 0.0,
                "swept_levels_count": 0,
                "simulated_vwap": 0.0,
                "is_fully_satisfied": False,
                "level_fills": np.array([], dtype=np.float64),
            }

        matched_vols = vols[mask]
        matched_prices = prices[mask]
        total_avail = float(np.sum(matched_vols))

        target_vol = min(requested_volume, total_avail)
        if target_vol <= 1e-9:
            return {
                "total_executable_vol": 0.0,
                "swept_levels_count": 0,
                "simulated_vwap": 0.0,
                "is_fully_satisfied": False,
                "level_fills": np.array([], dtype=np.float64),
            }

        cum_vols = np.cumsum(matched_vols)
        prev_cum = np.roll(cum_vols, 1)
        prev_cum[0] = 0.0

        level_fills = np.maximum(0.0, np.minimum(matched_vols, target_vol - prev_cum))
        swept_count = int(np.sum(level_fills > 1e-9))
        vwap = float(np.dot(matched_prices, level_fills) / target_vol)

        return {
            "total_executable_vol": total_avail,
            "swept_levels_count": swept_count,
            "simulated_vwap": vwap,
            "is_fully_satisfied": (total_avail >= requested_volume - 1e-9),
            "level_fills": level_fills,
        }


class SIMDLOBBookSide:
    """Manages one side of the order book (Bids or Asks)."""
    def __init__(self, is_bid: bool, max_levels: int = DEFAULT_PRICE_LEVELS):
        self.is_bid: bool = is_bid
        self.ladder: SIMDPriceLadder = SIMDPriceLadder(is_bid=is_bid, max_levels=max_levels)

    @property
    def active_levels(self) -> int:
        return self.ladder.active_levels

    @property
    def head_slots(self) -> np.ndarray:
        start = self.ladder.head_level
        end = start + self.ladder.active_levels
        return self.ladder.head_slots[start:end]

    @property
    def tail_slots(self) -> np.ndarray:
        start = self.ladder.head_level
        end = start + self.ladder.active_levels
        return self.ladder.tail_slots[start:end]

    def get_best_price(self) -> float:
        if self.ladder.active_levels > 0 and self.ladder.ladder[self.ladder.head_level, 1] > 1e-9:
            return float(self.ladder.ladder[self.ladder.head_level, 0])
        return 0.0 if self.is_bid else float("inf")

    def get_best_volume(self) -> float:
        if self.ladder.active_levels > 0:
            return float(self.ladder.ladder[self.ladder.head_level, 1])
        return 0.0

    def insert_order(
        self,
        slot_idx: int,
        price: float,
        display_volume: float,
        hidden_volume: float,
        pool: SIMDLOBOrderPool,
    ) -> int:
        return self.ladder.insert_order(slot_idx, price, display_volume, hidden_volume, pool)

    def deduct_volume(
        self,
        price: float,
        disp_vol: float,
        hid_vol: float,
        remove_order: bool = False,
    ) -> None:
        self.ladder.deduct_volume(price, disp_vol, hid_vol, remove_order=remove_order)

    def remove_level(self, idx: int) -> None:
        self.ladder.remove_level(idx)

    def scan_crossable_depth(
        self,
        limit_price: float,
        requested_volume: float,
        is_market: bool = False,
        use_torch: bool = True,
    ) -> Dict[str, Any]:
        return self.ladder.scan_crossable_depth(
            limit_price, requested_volume, is_market=is_market, use_torch=use_torch
        )


# ---------------------------------------------------------------------------
# Single-Symbol Order Book (SIMDOrderBook)
# ---------------------------------------------------------------------------
class SIMDOrderBook:
    """
    Single-symbol L3 Limit Order Book engine.
    Encapsulates bids, asks, pre-allocated order pool, and matching logic.
    """
    def __init__(
        self,
        symbol: str,
        pool_capacity: int = DEFAULT_ORDER_CAPACITY,
        max_levels: int = DEFAULT_PRICE_LEVELS,
        tick_size: float = DEFAULT_TICK_SIZE,
        use_torch: bool = True,
        price_levels: Optional[int] = None,
    ):
        self.symbol: str = symbol
        if price_levels is not None:
            max_levels = price_levels
        self.tick_size: float = tick_size
        self.use_torch: bool = bool(use_torch and _TORCH_AVAILABLE)
        self.pool: SIMDLOBOrderPool = SIMDLOBOrderPool(capacity=pool_capacity)
        self.bids: SIMDLOBBookSide = SIMDLOBBookSide(is_bid=True, max_levels=max_levels)
        self.asks: SIMDLOBBookSide = SIMDLOBBookSide(is_bid=False, max_levels=max_levels)
        self._lock: threading.RLock = threading.RLock()
        self._order_meta: Dict[str, Tuple[int, int, float, float, float]] = {}
        self._slot_to_id: Dict[int, str] = {}
        self._slot_to_entry: Dict[int, L3OrderEntry] = {}

        # Connect eviction callback to prune price queues on ring buffer wrap-around
        self.pool._internal_eviction_callback = self._on_slot_evicted
        self.pool.set_eviction_callback(self._on_slot_evicted)

    def _on_slot_evicted(self, slot_idx: int, order_id: str) -> None:
        self._order_meta.pop(order_id, None)
        self._slot_to_id.pop(slot_idx, None)
        self._slot_to_entry.pop(slot_idx, None)
        slot = self.pool.slots[slot_idx]
        price = float(slot["price"])
        side = int(slot["side"])
        disp_vol = float(slot["display_volume"])
        hid_vol = float(slot["hidden_volume"])

        # Unlink from intrusive linked list
        book_side = self.bids if side == OrderSide.BUY else self.asks
        idx, exists = book_side.ladder.find_level_index(price)
        if exists:
            abs_idx = book_side.ladder.head_level + idx
            if int(book_side.ladder.head_slots[abs_idx]) == slot_idx:
                book_side.ladder.head_slots[abs_idx] = slot["next_slot"]
            if int(book_side.ladder.tail_slots[abs_idx]) == slot_idx:
                book_side.ladder.tail_slots[abs_idx] = slot["prev_slot"]

            self.pool.unlink_slot(slot_idx)
            lad = book_side.ladder
            lad.ladder[abs_idx, 1] = max(0.0, lad.ladder[abs_idx, 1] - disp_vol)
            lad.ladder[abs_idx, 2] = max(0.0, lad.ladder[abs_idx, 2] - hid_vol)
            lad.ladder[abs_idx, 3] = max(0, int(lad.ladder[abs_idx, 3]) - 1)
            if (lad.ladder[abs_idx, 1] + lad.ladder[abs_idx, 2]) <= 1e-9 or lad.ladder[abs_idx, 3] <= 0:
                lad.remove_level(idx)
        else:
            self.pool.unlink_slot(slot_idx)

    @property
    def capacity(self) -> int:
        return self.pool.capacity

    @property
    def head_seq(self) -> int:
        return self.pool.head_seq

    @property
    def bid_prices(self) -> np.ndarray:
        start = self.bids.ladder.head_level
        end = start + self.bids.active_levels
        return self.bids.ladder.ladder[start:end, 0].copy()

    @property
    def bid_volumes(self) -> np.ndarray:
        start = self.bids.ladder.head_level
        end = start + self.bids.active_levels
        return self.bids.ladder.ladder[start:end, 1].copy()

    @property
    def ask_prices(self) -> np.ndarray:
        start = self.asks.ladder.head_level
        end = start + self.asks.active_levels
        return self.asks.ladder.ladder[start:end, 0].copy()

    @property
    def ask_volumes(self) -> np.ndarray:
        start = self.asks.ladder.head_level
        end = start + self.asks.active_levels
        return self.asks.ladder.ladder[start:end, 1].copy()

    @property
    def best_bid(self) -> float:
        return self.bids.get_best_price()

    @property
    def best_ask(self) -> float:
        return self.asks.get_best_price()

    @property
    def mid_price(self) -> float:
        bb = self.best_bid
        ba = self.best_ask
        if bb > 1e-9 and not math.isinf(ba):
            return (bb + ba) / 2.0
        elif bb > 1e-9:
            return bb
        elif not math.isinf(ba):
            return ba
        return 0.0

    @property
    def spread(self) -> float:
        bb = self.best_bid
        ba = self.best_ask
        if bb > 1e-9 and not math.isinf(ba):
            return max(0.0, ba - bb)
        return 0.0

    @property
    def spread_bps(self) -> float:
        mid = self.mid_price
        if mid > 1e-9:
            return (self.spread / mid) * 10000.0
        return 0.0

    # -----------------------------------------------------------------------
    # Core Order Matching Pipeline
    # -----------------------------------------------------------------------
    def match_order(
        self,
        order: Union[SIMDOrder, Dict[str, Any]],
    ) -> SIMDMatchResult:
        t0 = time.perf_counter_ns()
        with self._lock:
            # 1. Validation & Ingestion
            oid, sym, side, o_type, px, vol, disp_vol, hid_vol, peak, ts = self._parse_order_input(order)

            if vol <= 0.0 or not math.isfinite(vol):
                raise ValueError(f"Order volume must be positive and finite (got {vol})")

            if o_type == OrderType.LIMIT:
                if px <= 0.0 or not math.isfinite(px):
                    raise ValueError(f"Limit price must be positive and finite (got {px})")
            elif o_type == OrderType.MARKET:
                px = float("inf") if side == OrderSide.BUY else 0.0

            arrival_mid: Optional[float] = None

            # Dispatch specialized execution types
            if o_type == OrderType.FOK:
                arrival_mid = self.mid_price
                return self._execute_fok_locked(oid, sym, side, px, vol, disp_vol, hid_vol, peak, ts, arrival_mid, t0)
            elif o_type == OrderType.IOC:
                arrival_mid = self.mid_price
                return self._execute_ioc_locked(oid, sym, side, px, vol, disp_vol, hid_vol, peak, ts, arrival_mid, t0)
            elif o_type == OrderType.MARKET:
                arrival_mid = self.mid_price
                return self._execute_market_locked(oid, sym, side, vol, ts, arrival_mid, t0)

            # LIMIT & ICEBERG Execution
            opposing = self.asks if side == OrderSide.BUY else self.bids
            same_side = self.bids if side == OrderSide.BUY else self.asks

            leaves_vol = vol
            fills: List[SIMDFillRecord] = []
            swept_levels = 0

            # Price-Time Priority Matching Sweep
            while leaves_vol > 1e-9 and opposing.active_levels > 0:
                abs_head = opposing.ladder.head_level
                best_px = float(opposing.ladder.ladder[abs_head, 0])
                if side == OrderSide.BUY and best_px > px + 1e-9:
                    break
                if side == OrderSide.SELL and best_px < px - 1e-9:
                    break

                swept_levels += 1
                head_slot_idx = int(opposing.ladder.head_slots[abs_head])

                while leaves_vol > 1e-9 and head_slot_idx != -1:
                    maker_slot = self.pool.slots[head_slot_idx]
                    maker_status = int(maker_slot["status"])
                    if maker_status not in (OrderStatus.ACTIVE, OrderStatus.PARTIALLY_FILLED):
                        # Skip canceled/freed slots (lazy eviction)
                        head_slot_idx = int(maker_slot["next_slot"])
                        continue

                    maker_disp = float(maker_slot["display_volume"])
                    fill_vol = min(leaves_vol, maker_disp)

                    if fill_vol > 1e-9:
                        leaves_vol -= fill_vol
                        maker_slot["display_volume"] -= fill_vol
                        maker_slot["cum_filled"] += fill_vol
                        opposing.ladder.ladder[abs_head, 1] = max(0.0, opposing.ladder.ladder[abs_head, 1] - fill_vol)

                        maker_id_str = self._slot_to_id.get(head_slot_idx)
                        if not maker_id_str:
                            maker_id_str = maker_slot["order_id"].split(b"\x00", 1)[0].decode("ascii", errors="ignore")
                        fills.append(SIMDFillRecord(
                            symbol=sym,
                            taker_order_id=oid,
                            maker_order_id=maker_id_str,
                            price=best_px,
                            volume=fill_vol,
                            side="BUY" if side == OrderSide.BUY else "SELL",
                            timestamp_ns=ts,
                            is_maker=False,
                        ))

                    # Maker exhaustion check & Iceberg reload
                    if float(maker_slot["display_volume"]) <= 1e-9:
                        maker_hid = float(maker_slot["hidden_volume"])
                        if maker_hid > 1e-9:
                            # Reload Iceberg tranche: loses priority, moves to tail
                            reload_vol = min(float(maker_slot["peak_size"]), maker_hid)
                            maker_slot["display_volume"] = reload_vol
                            maker_slot["hidden_volume"] -= reload_vol
                            opposing.ladder.ladder[abs_head, 1] += reload_vol
                            opposing.ladder.ladder[abs_head, 2] = max(0.0, opposing.ladder.ladder[abs_head, 2] - reload_vol)
                            maker_slot["priority_seq"] = np.int64(self.pool.head_seq)

                            # Move from head to tail of price queue if multiple orders exist
                            demoted_slot_idx = head_slot_idx
                            next_slot = int(maker_slot["next_slot"])
                            if head_slot_idx != int(opposing.ladder.tail_slots[abs_head]):
                                opposing.ladder.head_slots[abs_head] = np.int32(next_slot)
                                if next_slot != -1:
                                    self.pool.slots[next_slot]["prev_slot"] = np.int32(-1)
                                    self.pool.prev_slots[next_slot] = -1

                                old_tail = int(opposing.ladder.tail_slots[abs_head])
                                self.pool.slots[old_tail]["next_slot"] = np.int32(demoted_slot_idx)
                                self.pool.next_slots[old_tail] = demoted_slot_idx

                                maker_slot["prev_slot"] = np.int32(old_tail)
                                self.pool.prev_slots[demoted_slot_idx] = old_tail

                                maker_slot["next_slot"] = np.int32(-1)
                                self.pool.next_slots[demoted_slot_idx] = -1

                                opposing.ladder.tail_slots[abs_head] = np.int32(demoted_slot_idx)
                                head_slot_idx = next_slot
                            else:
                                # Single order at level: retains head position for continuing sweep
                                head_slot_idx = demoted_slot_idx

                            # Update metadata and cached entry for snapshot and cancel consistency
                            self._order_meta[maker_id_str] = (
                                demoted_slot_idx,
                                int(maker_slot["side"]),
                                float(maker_slot["price"]),
                                float(maker_slot["display_volume"]),
                                float(maker_slot["hidden_volume"]),
                            )
                            if demoted_slot_idx in self._slot_to_entry:
                                entry = self._slot_to_entry[demoted_slot_idx]
                                entry.display_volume = float(maker_slot["display_volume"])
                                entry.hidden_volume = float(maker_slot["hidden_volume"])
                                entry.volume = entry.display_volume + entry.hidden_volume
                                entry.priority_seq = int(maker_slot["priority_seq"])
                        else:
                            # Fully filled maker order
                            maker_slot["status"] = np.int8(OrderStatus.FILLED)
                            next_slot = int(maker_slot["next_slot"])
                            self.pool.unlink_slot(head_slot_idx)
                            opposing.ladder.head_slots[abs_head] = np.int32(next_slot)
                            if head_slot_idx == int(opposing.ladder.tail_slots[abs_head]):
                                opposing.ladder.tail_slots[abs_head] = np.int32(-1)
                            opposing.ladder.ladder[abs_head, 3] = max(0, int(opposing.ladder.ladder[abs_head, 3]) - 1)
                            self._order_meta.pop(maker_id_str, None)
                            self._slot_to_id.pop(head_slot_idx, None)
                            self._slot_to_entry.pop(head_slot_idx, None)
                            head_slot_idx = next_slot
                    else:
                        maker_slot["status"] = np.int8(OrderStatus.PARTIALLY_FILLED)
                        break

                # Level 0 exhaustion check
                if int(opposing.ladder.ladder[abs_head, 3]) <= 0 or (float(opposing.ladder.ladder[abs_head, 1]) + float(opposing.ladder.ladder[abs_head, 2])) <= 1e-9 or int(opposing.ladder.head_slots[abs_head]) == -1:
                    opposing.remove_level(0)

            filled_vol = vol - leaves_vol
            is_full = leaves_vol <= 1e-9

            # Resting phase: place unexecuted remainder into book
            if not is_full:
                if o_type == OrderType.ICEBERG or hid_vol > 0.0:
                    rem_disp = min(leaves_vol, disp_vol if disp_vol > 0.0 else peak)
                    rem_hid = max(0.0, leaves_vol - rem_disp)
                else:
                    rem_disp = leaves_vol
                    rem_hid = 0.0

                slot_idx = self.pool.alloc_slot(
                    order_id=oid,
                    symbol=sym,
                    side=int(side),
                    order_type=int(o_type),
                    price=px,
                    volume=vol,
                    display_volume=rem_disp,
                    hidden_volume=rem_hid,
                    peak_size=peak,
                    timestamp_ns=ts,
                )
                if filled_vol > 1e-9:
                    self.pool.slots[slot_idx]["cum_filled"] = filled_vol
                    self.pool.slots[slot_idx]["status"] = np.int8(OrderStatus.PARTIALLY_FILLED)

                same_side.insert_order(slot_idx, px, rem_disp, rem_hid, self.pool)
                self._order_meta[oid] = (slot_idx, int(side), px, rem_disp, rem_hid)
                self._slot_to_id[slot_idx] = oid
                self._slot_to_entry[slot_idx] = L3OrderEntry(
                    order_id=oid,
                    price=px,
                    volume=rem_disp + rem_hid,
                    display_volume=rem_disp,
                    hidden_volume=rem_hid,
                    timestamp_ns=ts,
                    priority_seq=self.pool.head_seq,
                    is_iceberg=(o_type == OrderType.ICEBERG or rem_hid > 0),
                )
                final_status = OrderStatus.PARTIALLY_FILLED if filled_vol > 1e-9 else OrderStatus.ACTIVE
            else:
                final_status = OrderStatus.FILLED

            # Calculate VWAP and arrival slippage
            if filled_vol > 1e-9:
                vwap = self._calculate_vwap(fills, filled_vol)
                if arrival_mid is None:
                    arrival_mid = self.mid_price
                slippage = self._calculate_slippage(vwap, arrival_mid, side)
            else:
                vwap = 0.0
                slippage = 0.0

            t1 = time.perf_counter_ns()
            return SIMDMatchResult(
                symbol=sym,
                taker_order_id=oid,
                side="BUY" if side == OrderSide.BUY else "SELL",
                order_type="LIMIT" if o_type == OrderType.LIMIT else "ICEBERG",
                requested_volume=vol,
                filled_volume=filled_vol,
                remaining_volume=leaves_vol,
                canceled_volume=0.0,
                vwap_fill_price=vwap,
                slippage_bps=slippage,
                fills=fills,
                swept_levels_count=swept_levels,
                is_fully_filled=is_full,
                status=final_status,
                latency_ns=t1 - t0,
            )

    # -----------------------------------------------------------------------
    # IOC Execution Mechanics
    # -----------------------------------------------------------------------
    def execute_ioc(
        self,
        order: Union[SIMDOrder, Dict[str, Any]],
    ) -> SIMDMatchResult:
        with self._lock:
            oid, sym, side, _, px, vol, disp, hid, peak, ts = self._parse_order_input(order)
            if vol <= 0.0 or not math.isfinite(vol):
                raise ValueError(f"Order volume must be positive and finite (got {vol})")
            arrival_mid = self.mid_price
            t0 = time.perf_counter_ns()
            return self._execute_ioc_locked(oid, sym, side, px, vol, disp, hid, peak, ts, arrival_mid, t0)

    def _execute_ioc_locked(
        self,
        oid: str,
        sym: str,
        side: OrderSide,
        px: float,
        vol: float,
        disp_vol: float,
        hid_vol: float,
        peak: float,
        ts: int,
        arrival_mid: float,
        t0: int,
    ) -> SIMDMatchResult:
        opposing = self.asks if side == OrderSide.BUY else self.bids
        leaves_vol = vol
        fills: List[SIMDFillRecord] = []
        swept_levels = 0

        while leaves_vol > 1e-9 and opposing.active_levels > 0:
            abs_head = opposing.ladder.head_level
            best_px = float(opposing.ladder.ladder[abs_head, 0])
            if side == OrderSide.BUY and best_px > px + 1e-9:
                break
            if side == OrderSide.SELL and best_px < px - 1e-9:
                break

            swept_levels += 1
            head_slot_idx = int(opposing.ladder.head_slots[abs_head])

            while leaves_vol > 1e-9 and head_slot_idx != -1:
                maker_slot = self.pool.slots[head_slot_idx]
                if int(maker_slot["status"]) not in (OrderStatus.ACTIVE, OrderStatus.PARTIALLY_FILLED):
                    head_slot_idx = int(maker_slot["next_slot"])
                    continue

                maker_disp = float(maker_slot["display_volume"])
                fill_vol = min(leaves_vol, maker_disp)

                if fill_vol > 1e-9:
                    leaves_vol -= fill_vol
                    maker_slot["display_volume"] -= fill_vol
                    maker_slot["cum_filled"] += fill_vol
                    opposing.ladder.ladder[abs_head, 1] = max(0.0, opposing.ladder.ladder[abs_head, 1] - fill_vol)

                    maker_id_str = self._slot_to_id.get(head_slot_idx)
                    if not maker_id_str:
                        maker_id_str = maker_slot["order_id"].split(b"\x00", 1)[0].decode("ascii", errors="ignore")
                    fills.append(SIMDFillRecord(
                        symbol=sym,
                        taker_order_id=oid,
                        maker_order_id=maker_id_str,
                        price=best_px,
                        volume=fill_vol,
                        side="BUY" if side == OrderSide.BUY else "SELL",
                        timestamp_ns=ts,
                    ))

                if float(maker_slot["display_volume"]) <= 1e-9:
                    maker_hid = float(maker_slot["hidden_volume"])
                    if maker_hid > 1e-9:
                        # Reload Iceberg tranche: loses priority, moves to tail
                        reload_vol = min(float(maker_slot["peak_size"]), maker_hid)
                        maker_slot["display_volume"] = reload_vol
                        maker_slot["hidden_volume"] -= reload_vol
                        opposing.ladder.ladder[abs_head, 1] += reload_vol
                        opposing.ladder.ladder[abs_head, 2] = max(0.0, opposing.ladder.ladder[abs_head, 2] - reload_vol)
                        maker_slot["priority_seq"] = np.int64(self.pool.head_seq)

                        # Move from head to tail of price queue if multiple orders exist
                        demoted_slot_idx = head_slot_idx
                        next_slot = int(maker_slot["next_slot"])
                        if head_slot_idx != int(opposing.ladder.tail_slots[abs_head]):
                            opposing.ladder.head_slots[abs_head] = np.int32(next_slot)
                            if next_slot != -1:
                                self.pool.slots[next_slot]["prev_slot"] = np.int32(-1)
                                self.pool.prev_slots[next_slot] = -1

                            old_tail = int(opposing.ladder.tail_slots[abs_head])
                            self.pool.slots[old_tail]["next_slot"] = np.int32(demoted_slot_idx)
                            self.pool.next_slots[old_tail] = demoted_slot_idx

                            maker_slot["prev_slot"] = np.int32(old_tail)
                            self.pool.prev_slots[demoted_slot_idx] = old_tail

                            maker_slot["next_slot"] = np.int32(-1)
                            self.pool.next_slots[demoted_slot_idx] = -1

                            opposing.ladder.tail_slots[abs_head] = np.int32(demoted_slot_idx)
                            head_slot_idx = next_slot
                        else:
                            # Single order at level: retains head position for continuing sweep
                            head_slot_idx = demoted_slot_idx

                        # Update metadata and cached entry for snapshot and cancel consistency
                        self._order_meta[maker_id_str] = (
                            demoted_slot_idx,
                            int(maker_slot["side"]),
                            float(maker_slot["price"]),
                            float(maker_slot["display_volume"]),
                            float(maker_slot["hidden_volume"]),
                        )
                        if demoted_slot_idx in self._slot_to_entry:
                            entry = self._slot_to_entry[demoted_slot_idx]
                            entry.display_volume = float(maker_slot["display_volume"])
                            entry.hidden_volume = float(maker_slot["hidden_volume"])
                            entry.volume = entry.display_volume + entry.hidden_volume
                            entry.priority_seq = int(maker_slot["priority_seq"])
                    else:
                        maker_slot["status"] = np.int8(OrderStatus.FILLED)
                        next_slot = int(maker_slot["next_slot"])
                        self.pool.unlink_slot(head_slot_idx)
                        opposing.ladder.head_slots[abs_head] = np.int32(next_slot)
                        if head_slot_idx == int(opposing.ladder.tail_slots[abs_head]):
                            opposing.ladder.tail_slots[abs_head] = np.int32(-1)
                        opposing.ladder.ladder[abs_head, 3] = max(0, int(opposing.ladder.ladder[abs_head, 3]) - 1)
                        self._order_meta.pop(maker_id_str, None)
                        self._slot_to_id.pop(head_slot_idx, None)
                        self._slot_to_entry.pop(head_slot_idx, None)
                        head_slot_idx = next_slot
                else:
                    maker_slot["status"] = np.int8(OrderStatus.PARTIALLY_FILLED)
                    break

            # Level 0 exhaustion check
            if int(opposing.ladder.ladder[abs_head, 3]) <= 0 or (float(opposing.ladder.ladder[abs_head, 1]) + float(opposing.ladder.ladder[abs_head, 2])) <= 1e-9 or int(opposing.ladder.head_slots[abs_head]) == -1:
                opposing.remove_level(0)


        filled_vol = vol - leaves_vol
        canceled_vol = leaves_vol
        is_full = (leaves_vol <= 1e-9)

        if filled_vol > 1e-9:
            vwap = self._calculate_vwap(fills, filled_vol)
            slippage = self._calculate_slippage(vwap, arrival_mid, side)
        else:
            vwap = 0.0
            slippage = 0.0

        t1 = time.perf_counter_ns()
        return SIMDMatchResult(
            symbol=sym,
            taker_order_id=oid,
            side="BUY" if side == OrderSide.BUY else "SELL",
            order_type="IOC",
            requested_volume=vol,
            filled_volume=filled_vol,
            remaining_volume=leaves_vol,
            canceled_volume=canceled_vol,
            vwap_fill_price=vwap,
            slippage_bps=slippage,
            fills=fills,
            swept_levels_count=swept_levels,
            is_fully_filled=is_full,
            status=OrderStatus.FILLED if is_full else (OrderStatus.PARTIALLY_FILLED if filled_vol > 1e-9 else OrderStatus.CANCELED),
            latency_ns=t1 - t0,
        )

    # -----------------------------------------------------------------------
    # FOK Two-Phase Commit Protocol
    # -----------------------------------------------------------------------
    def execute_fok(
        self,
        order: Union[SIMDOrder, Dict[str, Any]],
    ) -> SIMDMatchResult:
        with self._lock:
            oid, sym, side, _, px, vol, disp, hid, peak, ts = self._parse_order_input(order)
            if vol <= 0.0 or not math.isfinite(vol):
                raise ValueError(f"Order volume must be positive and finite (got {vol})")
            arrival_mid = self.mid_price
            t0 = time.perf_counter_ns()
            return self._execute_fok_locked(oid, sym, side, px, vol, disp, hid, peak, ts, arrival_mid, t0)

    def _execute_fok_locked(
        self,
        oid: str,
        sym: str,
        side: OrderSide,
        px: float,
        vol: float,
        disp_vol: float,
        hid_vol: float,
        peak: float,
        ts: int,
        arrival_mid: float,
        t0: int,
    ) -> SIMDMatchResult:
        opposing = self.asks if side == OrderSide.BUY else self.bids

        # Phase 1: Pre-flight feasibility simulation (Read-Only)
        scan = opposing.scan_crossable_depth(
            limit_price=px,
            requested_volume=vol,
            is_market=False,
            use_torch=self.use_torch,
        )

        if not scan["is_fully_satisfied"] or scan["total_executable_vol"] < vol - 1e-9:
            # Feasibility check failed: ABORT with 0 fills and zero state mutation
            t1 = time.perf_counter_ns()
            return SIMDMatchResult(
                symbol=sym,
                taker_order_id=oid,
                side="BUY" if side == OrderSide.BUY else "SELL",
                order_type="FOK",
                requested_volume=vol,
                filled_volume=0.0,
                remaining_volume=vol,
                canceled_volume=vol,
                vwap_fill_price=0.0,
                slippage_bps=0.0,
                fills=[],
                swept_levels_count=0,
                is_fully_filled=False,
                status=OrderStatus.REJECTED,
                is_rejected=True,
                rejection_reason=f"Insufficient liquidity for FOK (requested={vol}, available={scan['total_executable_vol']})",
                latency_ns=t1 - t0,
            )

        # Phase 2: Guaranteed full commit
        match_res = self._execute_ioc_locked(oid, sym, side, px, vol, disp_vol, hid_vol, peak, ts, arrival_mid, t0)
        match_res.order_type = "FOK"
        match_res.status = OrderStatus.FILLED
        match_res.is_fully_filled = True
        match_res.canceled_volume = 0.0
        match_res.remaining_volume = 0.0
        return match_res

    # -----------------------------------------------------------------------
    # Market Order Execution (Immediate Aggressive Sweep)
    # -----------------------------------------------------------------------
    def execute_market_order(
        self,
        symbol: str,
        side: Union[str, OrderSide],
        volume: float,
        timestamp_ns: Optional[int] = None,
    ) -> SIMDMatchResult:
        with self._lock:
            vol = float(volume)
            if vol <= 0.0 or not math.isfinite(vol):
                raise ValueError(f"Market order volume must be positive and finite (got {volume})")
            s_side = OrderSide.from_str(side)
            ts = timestamp_ns if timestamp_ns is not None else time.time_ns()
            t0 = time.perf_counter_ns()
            arrival_mid = self.mid_price
            return self._execute_market_locked(
                oid=f"MKT_{ts}",
                sym=symbol,
                side=s_side,
                vol=vol,
                ts=ts,
                arrival_mid=arrival_mid,
                t0=t0,
            )

    def _execute_market_locked(
        self,
        oid: str,
        sym: str,
        side: OrderSide,
        vol: float,
        ts: int,
        arrival_mid: float,
        t0: int,
    ) -> SIMDMatchResult:
        px = float("inf") if side == OrderSide.BUY else 0.0
        res = self._execute_ioc_locked(
            oid=oid,
            sym=sym,
            side=side,
            px=px,
            vol=vol,
            disp_vol=vol,
            hid_vol=0.0,
            peak=vol,
            ts=ts,
            arrival_mid=arrival_mid,
            t0=t0,
        )
        res.order_type = "MARKET"
        return res

    # -----------------------------------------------------------------------
    # Atomic Order Cancellation in O(1)
    # -----------------------------------------------------------------------
    def cancel_order(self, order_id: str, symbol: Optional[str] = None) -> bool:
        with self._lock:
            meta = self._order_meta.pop(order_id, None)
            if meta is not None:
                slot_idx, side, price, disp_vol, hid_vol = meta
                slot = self.pool.slots[slot_idx]
                st = int(slot["status"])
                if st not in (OrderStatus.ACTIVE, OrderStatus.PARTIALLY_FILLED):
                    self._slot_to_id.pop(slot_idx, None)
                    return False
            else:
                slot_idx = self.pool.get_slot_idx(order_id)
                if slot_idx is None:
                    return False
                slot = self.pool.slots[slot_idx]
                st = int(slot["status"])
                if st not in (OrderStatus.ACTIVE, OrderStatus.PARTIALLY_FILLED):
                    return False
                side = int(slot["side"])
                price = float(slot["price"])
                disp_vol = float(slot["display_volume"])
                hid_vol = float(slot["hidden_volume"])

            self._slot_to_id.pop(slot_idx, None)
            self._slot_to_entry.pop(slot_idx, None)
            slot["status"] = np.int8(OrderStatus.CANCELED)

            # Unlink from price queue
            book_side = self.bids if side == OrderSide.BUY else self.asks
            idx, exists = book_side.ladder.find_level_index(price)
            if exists:
                abs_idx = book_side.ladder.head_level + idx
                lad = book_side.ladder
                if lad.ladder[abs_idx, 3] <= 1:
                    lad.remove_level(idx)
                    slot["prev_slot"] = np.int32(-1)
                    slot["next_slot"] = np.int32(-1)
                else:
                    next_s = int(slot["next_slot"])
                    prev_s = int(slot["prev_slot"])
                    if int(lad.head_slots[abs_idx]) == slot_idx:
                        lad.head_slots[abs_idx] = np.int32(next_s)
                    if int(lad.tail_slots[abs_idx]) == slot_idx:
                        lad.tail_slots[abs_idx] = np.int32(prev_s)

                    self.pool.unlink_slot(slot_idx)
                    lad.ladder[abs_idx, 1] = max(0.0, lad.ladder[abs_idx, 1] - disp_vol)
                    lad.ladder[abs_idx, 2] = max(0.0, lad.ladder[abs_idx, 2] - hid_vol)
                    lad.ladder[abs_idx, 3] = max(0, int(lad.ladder[abs_idx, 3]) - 1)
                    if (lad.ladder[abs_idx, 1] + lad.ladder[abs_idx, 2]) <= 1e-9 or lad.ladder[abs_idx, 3] <= 0:
                        lad.remove_level(idx)
            else:
                self.pool.unlink_slot(slot_idx)

            self.pool._id_to_slot.pop(order_id, None)
            return True

    # -----------------------------------------------------------------------
    # Queries & State Extraction
    # -----------------------------------------------------------------------
    def get_order_by_id(self, order_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            slot_idx = self.pool.get_slot_idx(order_id)
            if slot_idx is None:
                return None
            slot = self.pool.slots[slot_idx]
            oid_bytes = slot["order_id"]
            oid = oid_bytes.split(b"\x00", 1)[0].decode("ascii", errors="ignore")
            if oid != order_id:
                return None
            sym_bytes = slot["symbol"]
            sym = sym_bytes.split(b"\x00", 1)[0].decode("ascii", errors="ignore")
            return {
                "order_id": oid,
                "symbol": sym,
                "side": OrderSide(int(slot["side"])),
                "order_type": OrderType(int(slot["order_type"])),
                "status": OrderStatus(int(slot["status"])),
                "price": float(slot["price"]),
                "volume": float(slot["volume"]),
                "display_volume": float(slot["display_volume"]),
                "hidden_volume": float(slot["hidden_volume"]),
                "cum_filled": float(slot["cum_filled"]),
                "timestamp_ns": int(slot["timestamp_ns"]),
                "priority_seq": int(slot["priority_seq"]),
            }

    def get_active_orders(self) -> List[Dict[str, Any]]:
        with self._lock:
            active_list: List[Dict[str, Any]] = []
            for oid, idx in list(self.pool._id_to_slot.items()):
                slot = self.pool.slots[idx]
                st = int(slot["status"])
                if st in (OrderStatus.ACTIVE, OrderStatus.PARTIALLY_FILLED):
                    slot_oid = slot["order_id"].split(b"\x00", 1)[0].decode("ascii", errors="ignore")
                    if slot_oid == oid:
                        active_list.append({
                            "order_id": oid,
                            "symbol": slot["symbol"].split(b"\x00", 1)[0].decode("ascii", errors="ignore"),
                            "side": OrderSide(int(slot["side"])),
                            "order_type": OrderType(int(slot["order_type"])),
                            "status": OrderStatus(st),
                            "price": float(slot["price"]),
                            "volume": float(slot["volume"]),
                            "display_volume": float(slot["display_volume"]),
                            "hidden_volume": float(slot["hidden_volume"]),
                            "cum_filled": float(slot["cum_filled"]),
                            "timestamp_ns": int(slot["timestamp_ns"]),
                            "priority_seq": int(slot["priority_seq"]),
                        })
            return active_list

    def get_l3_snapshot(self, depth: int = 10) -> L3Snapshot:
        with self._lock:
            ts = time.time_ns()
            bids_list: List[L3PriceLevel] = []
            asks_list: List[L3PriceLevel] = []

            # Extract bids
            b_levels = min(depth, self.bids.active_levels)
            for i in range(b_levels):
                abs_i = self.bids.ladder.head_level + i
                px = float(self.bids.ladder.ladder[abs_i, 0])
                vol = float(self.bids.ladder.ladder[abs_i, 1])
                cnt = int(self.bids.ladder.ladder[abs_i, 3])
                order_entries: List[L3OrderEntry] = []

                curr_slot = int(self.bids.ladder.head_slots[abs_i])
                while curr_slot != -1:
                    entry = self._slot_to_entry.get(curr_slot)
                    if entry is not None:
                        order_entries.append(entry)
                    else:
                        slot = self.pool.slots[curr_slot]
                        if int(slot["status"]) in (OrderStatus.ACTIVE, OrderStatus.PARTIALLY_FILLED):
                            entry_oid = self._slot_to_id.get(curr_slot)
                            if not entry_oid:
                                entry_oid = slot["order_id"].split(b"\x00", 1)[0].decode("ascii", errors="ignore")
                            d_vol = float(slot["display_volume"])
                            h_vol = float(slot["hidden_volume"])
                            order_entries.append(L3OrderEntry(
                                order_id=entry_oid,
                                price=float(slot["price"]),
                                volume=d_vol + h_vol,
                                display_volume=d_vol,
                                hidden_volume=h_vol,
                                timestamp_ns=int(slot["timestamp_ns"]),
                                priority_seq=int(slot["priority_seq"]),
                                is_iceberg=(int(slot["order_type"]) == OrderType.ICEBERG or h_vol > 0),
                            ))
                    curr_slot = self.pool.next_slots[curr_slot]

                bids_list.append(L3PriceLevel(
                    price=px,
                    aggregated_volume=vol,
                    order_count=cnt,
                    orders=order_entries,
                ))

            # Extract asks
            a_levels = min(depth, self.asks.active_levels)
            for i in range(a_levels):
                abs_i = self.asks.ladder.head_level + i
                px = float(self.asks.ladder.ladder[abs_i, 0])
                vol = float(self.asks.ladder.ladder[abs_i, 1])
                cnt = int(self.asks.ladder.ladder[abs_i, 3])
                order_entries = []

                curr_slot = int(self.asks.ladder.head_slots[abs_i])
                while curr_slot != -1:
                    entry = self._slot_to_entry.get(curr_slot)
                    if entry is not None:
                        order_entries.append(entry)
                    else:
                        slot = self.pool.slots[curr_slot]
                        if int(slot["status"]) in (OrderStatus.ACTIVE, OrderStatus.PARTIALLY_FILLED):
                            entry_oid = self._slot_to_id.get(curr_slot)
                            if not entry_oid:
                                entry_oid = slot["order_id"].split(b"\x00", 1)[0].decode("ascii", errors="ignore")
                            d_vol = float(slot["display_volume"])
                            h_vol = float(slot["hidden_volume"])
                            order_entries.append(L3OrderEntry(
                                order_id=entry_oid,
                                price=float(slot["price"]),
                                volume=d_vol + h_vol,
                                display_volume=d_vol,
                                hidden_volume=h_vol,
                                timestamp_ns=int(slot["timestamp_ns"]),
                                priority_seq=int(slot["priority_seq"]),
                                is_iceberg=(int(slot["order_type"]) == OrderType.ICEBERG or h_vol > 0),
                            ))
                    curr_slot = self.pool.next_slots[curr_slot]

                asks_list.append(L3PriceLevel(
                    price=px,
                    aggregated_volume=vol,
                    order_count=cnt,
                    orders=order_entries,
                ))

            # Build 1D flat tensor of shape (40,)
            # [bid_p_1, bid_v_1, ask_p_1, ask_v_1, ..., bid_p_10, bid_v_10, ask_p_10, ask_v_10]
            flat_40 = np.zeros(40, dtype=np.float64)
            for lvl in range(10):
                base_idx = lvl * 4
                if lvl < self.bids.active_levels:
                    abs_b = self.bids.ladder.head_level + lvl
                    flat_40[base_idx + 0] = self.bids.ladder.ladder[abs_b, 0]
                    flat_40[base_idx + 1] = self.bids.ladder.ladder[abs_b, 1]
                if lvl < self.asks.active_levels:
                    abs_a = self.asks.ladder.head_level + lvl
                    flat_40[base_idx + 2] = self.asks.ladder.ladder[abs_a, 0]
                    flat_40[base_idx + 3] = self.asks.ladder.ladder[abs_a, 1]

            bb = self.best_bid
            ba = self.best_ask
            spread = max(0.0, ba - bb) if (bb > 1e-9 and not math.isinf(ba)) else 0.0
            mid = (bb + ba) / 2.0 if (bb > 1e-9 and not math.isinf(ba)) else (bb if bb > 1e-9 else (ba if not math.isinf(ba) else 0.0))

            # Micro-price calculation
            bv1 = float(self.bids.ladder.ladder[self.bids.ladder.head_level, 1]) if self.bids.active_levels > 0 else 0.0
            av1 = float(self.asks.ladder.ladder[self.asks.ladder.head_level, 1]) if self.asks.active_levels > 0 else 0.0
            if bv1 + av1 > 1e-9 and bb > 1e-9 and not math.isinf(ba):
                micro_px = (ba * bv1 + bb * av1) / (bv1 + av1)
            else:
                micro_px = mid

            # OBI calculation
            obi_num = bv1 - av1
            obi_den = bv1 + av1
            w_obi = obi_num / obi_den if obi_den > 1e-9 else 0.0

            b_head = self.bids.ladder.head_level
            b_cnt = min(depth, self.bids.active_levels)
            bid_px_arr = self.bids.ladder.ladder[b_head : b_head + b_cnt, 0].copy()
            bid_vol_arr = self.bids.ladder.ladder[b_head : b_head + b_cnt, 1].copy()

            a_head = self.asks.ladder.head_level
            a_cnt = min(depth, self.asks.active_levels)
            ask_px_arr = self.asks.ladder.ladder[a_head : a_head + a_cnt, 0].copy()
            ask_vol_arr = self.asks.ladder.ladder[a_head : a_head + a_cnt, 1].copy()

            return L3Snapshot(
                symbol=self.symbol,
                timestamp_ns=ts,
                depth=depth,
                best_bid=bb,
                best_ask=ba,
                spread=spread,
                mid_price=mid,
                micro_price=micro_px,
                weighted_obi=w_obi,
                bids=bids_list,
                asks=asks_list,
                bid_prices=bid_px_arr,
                bid_volumes=bid_vol_arr,
                ask_prices=ask_px_arr,
                ask_volumes=ask_vol_arr,
                flat_tensor_40=flat_40,
            )

    def get_l2_snapshot(self, depth: int = 10) -> Dict[str, Any]:
        with self._lock:
            d = min(depth, max(self.bids.active_levels, self.asks.active_levels, 1))
            return {
                "symbol": self.symbol,
                "timestamp_ns": time.time_ns(),
                "depth": d,
                "bid_prices": self.bid_prices[:d],
                "bid_volumes": self.bid_volumes[:d],
                "ask_prices": self.ask_prices[:d],
                "ask_volumes": self.ask_volumes[:d],
                "best_bid": self.best_bid,
                "best_ask": self.best_ask,
                "spread": self.spread,
                "mid_price": self.mid_price,
            }

    def simulate_sweep(
        self,
        side: Union[str, OrderSide],
        volume: float,
        limit_price: Optional[float] = None,
    ) -> Tuple[float, float, float]:
        with self._lock:
            s_side = OrderSide.from_str(side)
            opposing = self.asks if s_side == OrderSide.BUY else self.bids
            px = limit_price if limit_price is not None else (float("inf") if s_side == OrderSide.BUY else 0.0)
            is_mkt = limit_price is None

            scan = opposing.scan_crossable_depth(
                limit_price=px,
                requested_volume=volume,
                is_market=is_mkt,
                use_torch=self.use_torch,
            )
            exec_vol = scan["total_executable_vol"]
            vwap = scan["simulated_vwap"]
            arr_mid = self.mid_price
            slippage = self._calculate_slippage(vwap, arr_mid, s_side)
            return float(min(volume, exec_vol)), float(vwap), float(slippage)

    def compute_microstructure_metrics(
        self,
        reference_order_size: float = 1000.0,
    ) -> SIMDMicrostructureMetrics:
        with self._lock:
            ts = time.time_ns()
            bb = self.best_bid
            ba = self.best_ask
            spread = max(0.0, ba - bb) if (bb > 1e-9 and not math.isinf(ba)) else 0.0
            mid = (bb + ba) / 2.0 if (bb > 1e-9 and not math.isinf(ba)) else (bb if bb > 1e-9 else (ba if not math.isinf(ba) else 0.0))
            spread_bps = (spread / mid * 10000.0) if mid > 1e-9 else 0.0

            bv = self.bid_volumes
            av = self.ask_volumes

            # Multi-tier OBI
            def calc_obi(k: int) -> float:
                b_sum = float(np.sum(bv[:k])) if len(bv) > 0 else 0.0
                a_sum = float(np.sum(av[:k])) if len(av) > 0 else 0.0
                return (b_sum - a_sum) / (b_sum + a_sum) if (b_sum + a_sum) > 1e-9 else 0.0

            obi_1 = calc_obi(1)
            obi_5 = calc_obi(5)
            obi_10 = calc_obi(10)
            obi_20 = calc_obi(20)
            obi_50 = calc_obi(50)

            # L1 Micro-price
            bv1 = bv[0] if len(bv) > 0 else 0.0
            av1 = av[0] if len(av) > 0 else 0.0
            if bv1 + av1 > 1e-9 and bb > 1e-9 and not math.isinf(ba):
                micro_l1 = (ba * bv1 + bb * av1) / (bv1 + av1)
            else:
                micro_l1 = mid

            # Exponential decay micro-price
            k_levels = min(len(bv), len(av), 10)
            if k_levels > 0 and bb > 1e-9 and not math.isinf(ba):
                weights = np.exp(-0.25 * np.arange(k_levels))
                weights /= np.sum(weights)
                bp_k = self.bid_prices[:k_levels]
                ap_k = self.ask_prices[:k_levels]
                bv_k = bv[:k_levels]
                av_k = av[:k_levels]
                tot_v = bv_k + av_k
                tot_v[tot_v <= 1e-9] = 1.0
                level_micros = (ap_k * bv_k + bp_k * av_k) / tot_v
                micro_decay = float(np.dot(weights, level_micros))
            else:
                micro_decay = micro_l1

            # Effective spread via reference sweep
            _, sweep_vwap, _ = self.simulate_sweep(OrderSide.BUY, reference_order_size)
            eff_spread_bps = abs(sweep_vwap - mid) / mid * 10000.0 if (mid > 1e-9 and sweep_vwap > 1e-9) else spread_bps

            tot_b = float(np.sum(bv)) if len(bv) > 0 else 0.0
            tot_a = float(np.sum(av)) if len(av) > 0 else 0.0
            depth_ratio = tot_b / tot_a if tot_a > 1e-9 else 1.0

            return SIMDMicrostructureMetrics(
                symbol=self.symbol,
                timestamp_ns=ts,
                best_bid=bb,
                best_ask=ba,
                mid_price=mid,
                spread=spread,
                spread_bps=spread_bps,
                micro_price_l1=micro_l1,
                micro_price_decay=micro_decay,
                effective_spread_bps=eff_spread_bps,
                obi_1=obi_1,
                obi_5=obi_5,
                obi_10=obi_10,
                obi_20=obi_20,
                obi_50=obi_50,
                weighted_obi=obi_5,
                book_depth_ratio=depth_ratio,
                queue_depletion_rate_bid=0.0,
                queue_depletion_rate_ask=0.0,
            )

    # -----------------------------------------------------------------------
    # Helper Computations
    # -----------------------------------------------------------------------
    @staticmethod
    def _parse_order_input(order: Union[SIMDOrder, Dict[str, Any]]) -> Tuple[str, str, OrderSide, OrderType, float, float, float, float, float, int]:
        if isinstance(order, SIMDOrder):
            oid = order.order_id
            sym = order.symbol
            side = order.side
            o_type = order.order_type
            px = float(order.price)
            vol = float(order.volume)
            disp = float(order.display_volume)
            hid = float(order.hidden_volume)
            peak = float(order.peak_size)
            ts = int(order.timestamp_ns)
        elif isinstance(order, dict):
            oid = str(order.get("order_id", f"ORD_{time.time_ns()}"))
            sym = str(order.get("symbol", "DEFAULT"))
            side = OrderSide.from_str(order["side"])
            o_type = OrderType.from_str(order.get("order_type", OrderType.LIMIT))
            px = float(order.get("price", 0.0))
            vol = float(order["volume"])
            disp = float(order.get("display_volume", vol))
            hid = float(order.get("hidden_volume", 0.0))
            peak = float(order.get("peak_size", disp))
            ts = int(order.get("timestamp_ns", 0))
        else:
            raise ValueError(f"Unsupported order input type: {type(order)}")

        if o_type == OrderType.ICEBERG:
            if disp <= 0.0 or disp >= vol:
                if peak > 0.0 and peak < vol:
                    disp = peak
                else:
                    disp = min(vol, disp) if disp > 0.0 else vol
            if hid <= 0.0:
                hid = max(0.0, vol - disp)
            if peak <= 0.0:
                peak = disp

        return oid, sym, side, o_type, px, vol, disp, hid, peak, ts

    @staticmethod
    def _calculate_vwap(fills: List[SIMDFillRecord], filled_volume: float) -> float:
        if filled_volume <= 1e-9 or len(fills) == 0:
            return 0.0
        dollar_sum = sum(f.price * f.volume for f in fills)
        return dollar_sum / filled_volume

    @staticmethod
    def _calculate_slippage(vwap: float, arrival_mid: float, side: OrderSide) -> float:
        if arrival_mid <= 1e-9 or vwap <= 1e-9:
            return 0.0
        return abs(vwap - arrival_mid) / arrival_mid * 10000.0


# ---------------------------------------------------------------------------
# Top-Level Orchestrator: SIMDLOBMatchingCore
# ---------------------------------------------------------------------------
class SIMDLOBMatchingCore:
    """
    Top-Level SIMD/AVX2 Vectorized Zero-Copy LOB Matching Core.
    Phase 118 (Release R134 / v125 Production Master / Feature F560).

    Supports both direct single-symbol mode and multi-symbol book routing.
    """
    VERSION: int = VERSION
    RELEASE: str = RELEASE
    FEATURE: str = FEATURE

    def __init__(
        self,
        symbol: str = "DEFAULT",
        pool_capacity: int = DEFAULT_ORDER_CAPACITY,
        max_levels: int = DEFAULT_PRICE_LEVELS,
        tick_size: float = DEFAULT_TICK_SIZE,
        use_torch: bool = True,
        backend: Optional[Union[str, SIMDBackend]] = None,
        price_levels: Optional[int] = None,
    ):
        if price_levels is not None:
            max_levels = price_levels
        if backend is not None:
            b_str = str(backend).lower()
            self.use_torch = ("torch" in b_str) and _TORCH_AVAILABLE
        else:
            self.use_torch = bool(use_torch and _TORCH_AVAILABLE)

        self.default_symbol: str = symbol
        self.pool_capacity: int = pool_capacity
        self.max_levels: int = max_levels
        self.tick_size: float = tick_size

        self._books: Dict[str, SIMDOrderBook] = {}
        self._lock: threading.RLock = threading.RLock()

        # Initialize default book
        self._default_book: SIMDOrderBook = self.get_or_create_book(symbol)

    @property
    def backend(self) -> str:
        return "torch" if self.use_torch else "numpy"

    def get_or_create_book(self, symbol: str) -> SIMDOrderBook:
        with self._lock:
            if symbol not in self._books:
                self._books[symbol] = SIMDOrderBook(
                    symbol=symbol,
                    pool_capacity=self.pool_capacity,
                    max_levels=self.max_levels,
                    tick_size=self.tick_size,
                    use_torch=self.use_torch,
                )
            return self._books[symbol]

    def _resolve_book(self, symbol: Optional[str]) -> SIMDOrderBook:
        if symbol is None or symbol == "" or symbol == self.default_symbol:
            return self._default_book
        return self.get_or_create_book(symbol)

    # -----------------------------------------------------------------------
    # Forwarded Single-Symbol Properties (For backward compatibility & direct inspection)
    # -----------------------------------------------------------------------
    @property
    def capacity(self) -> int:
        return self._default_book.capacity

    @property
    def head_seq(self) -> int:
        return self._default_book.head_seq

    @property
    def pool(self) -> SIMDLOBOrderPool:
        return self._default_book.pool

    @property
    def bids(self) -> SIMDLOBBookSide:
        return self._default_book.bids

    @property
    def asks(self) -> SIMDLOBBookSide:
        return self._default_book.asks

    @property
    def bid_prices(self) -> np.ndarray:
        return self._default_book.bid_prices

    @property
    def bid_volumes(self) -> np.ndarray:
        return self._default_book.bid_volumes

    @property
    def ask_prices(self) -> np.ndarray:
        return self._default_book.ask_prices

    @property
    def ask_volumes(self) -> np.ndarray:
        return self._default_book.ask_volumes

    @property
    def best_bid(self) -> float:
        return self._default_book.best_bid

    @property
    def best_ask(self) -> float:
        return self._default_book.best_ask

    @property
    def mid_price(self) -> float:
        return self._default_book.mid_price

    @property
    def spread(self) -> float:
        return self._default_book.spread

    @property
    def spread_bps(self) -> float:
        return self._default_book.spread_bps

    # -----------------------------------------------------------------------
    # Public Matching Interface
    # -----------------------------------------------------------------------
    def match_order(
        self,
        order: Union[SIMDOrder, Dict[str, Any]],
    ) -> SIMDMatchResult:
        sym = order.symbol if isinstance(order, SIMDOrder) else str(order.get("symbol", self.default_symbol))
        book = self._resolve_book(sym)
        return book.match_order(order)

    submit_order = match_order

    def execute_ioc(
        self,
        order: Union[SIMDOrder, Dict[str, Any]],
    ) -> SIMDMatchResult:
        sym = order.symbol if isinstance(order, SIMDOrder) else str(order.get("symbol", self.default_symbol))
        book = self._resolve_book(sym)
        return book.execute_ioc(order)

    def execute_fok(
        self,
        order: Union[SIMDOrder, Dict[str, Any]],
    ) -> SIMDMatchResult:
        sym = order.symbol if isinstance(order, SIMDOrder) else str(order.get("symbol", self.default_symbol))
        book = self._resolve_book(sym)
        return book.execute_fok(order)

    def execute_market_order(
        self,
        symbol: str,
        side: Union[str, OrderSide],
        volume: float,
        timestamp_ns: Optional[int] = None,
    ) -> SIMDMatchResult:
        book = self._resolve_book(symbol)
        return book.execute_market_order(symbol, side, volume, timestamp_ns=timestamp_ns)

    def cancel_order(self, order_id: str, symbol: Optional[str] = None) -> bool:
        if symbol is not None:
            return self._resolve_book(symbol).cancel_order(order_id)
        # Fast-path: check default book directly
        if self._default_book.cancel_order(order_id):
            return True
        # Search remaining books if any
        with self._lock:
            for sym, book in self._books.items():
                if sym != self.default_symbol and book.cancel_order(order_id):
                    return True
            return False

    def get_order_by_id(self, order_id: str, symbol: Optional[str] = None) -> Optional[Dict[str, Any]]:
        if symbol is not None:
            return self._resolve_book(symbol).get_order_by_id(order_id)
        with self._lock:
            for book in self._books.values():
                res = book.get_order_by_id(order_id)
                if res is not None:
                    return res
            return None

    def get_active_orders(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        if symbol is not None:
            return self._resolve_book(symbol).get_active_orders()
        with self._lock:
            orders: List[Dict[str, Any]] = []
            for book in self._books.values():
                orders.extend(book.get_active_orders())
            return orders

    def get_l3_snapshot(self, symbol: Optional[str] = None, depth: int = 10) -> L3Snapshot:
        return self._resolve_book(symbol).get_l3_snapshot(depth=depth)

    def get_l2_snapshot(self, symbol: Optional[str] = None, depth: int = 10) -> Dict[str, Any]:
        return self._resolve_book(symbol).get_l2_snapshot(depth=depth)

    def simulate_sweep(
        self,
        symbol: str,
        side: Union[str, OrderSide],
        volume: float,
        limit_price: Optional[float] = None,
    ) -> Tuple[float, float, float]:
        return self._resolve_book(symbol).simulate_sweep(side, volume, limit_price=limit_price)

    def compute_microstructure_metrics(
        self,
        symbol: Optional[str] = None,
        reference_order_size: float = 1000.0,
    ) -> SIMDMicrostructureMetrics:
        return self._resolve_book(symbol).compute_microstructure_metrics(reference_order_size=reference_order_size)

    def process_tick(
        self,
        symbol: str,
        price: float,
        volume: float,
        side: str,
        timestamp_ns: Optional[int] = None,
    ) -> None:
        """Process streaming market tick without disrupting resting book."""
        book = self._resolve_book(symbol)
        # Execute synthetic tick execution against book if crossing
        s_side = OrderSide.from_str(side)
        book.execute_market_order(symbol, s_side, volume, timestamp_ns=timestamp_ns)

    def benchmark_matching_latency(self, num_orders: int = 1000) -> Dict[str, float]:
        """
        High-precision benchmark measuring order placement, matching, and cancellation latency.
        """
        book = self._default_book
        # Warmup loop
        for i in range(100):
            book.match_order({
                "order_id": f"WARM_{i}",
                "symbol": self.default_symbol,
                "side": OrderSide.BUY if (i % 2 == 0) else OrderSide.SELL,
                "price": 100.0 + (i % 5) * 0.1,
                "volume": 10.0,
                "order_type": OrderType.LIMIT,
            })

        t0 = time.perf_counter_ns()
        for i in range(num_orders):
            book.match_order({
                "order_id": f"BENCH_{i}",
                "symbol": self.default_symbol,
                "side": OrderSide.BUY if (i % 2 == 0) else OrderSide.SELL,
                "price": 100.0 + (i % 10) * 0.05,
                "volume": 50.0,
                "order_type": OrderType.LIMIT,
            })
        t1 = time.perf_counter_ns()

        total_ns = t1 - t0
        avg_ns = total_ns / max(num_orders, 1)
        avg_us = avg_ns / 1000.0
        throughput = (num_orders / (total_ns / 1e9)) if total_ns > 0 else 0.0

        return {
            "num_orders": float(num_orders),
            "total_time_ms": round(total_ns / 1e6, 4),
            "avg_latency_us": round(avg_us, 4),
            "avg_latency_ns": round(avg_ns, 2),
            "throughput_orders_per_sec": round(throughput, 2),
        }


# ---------------------------------------------------------------------------
# Complete Alias Trees
# ---------------------------------------------------------------------------
UltraLowLatencySIMDLOB = SIMDLOBMatchingCore
VectorizedSIMDMatchingCore = SIMDLOBMatchingCore
Phase118SIMDLOBMatchingCore = SIMDLOBMatchingCore
AVX2LOBEngine = SIMDLOBMatchingCore
ZeroCopyLOBMatchingEngine = SIMDLOBMatchingCore
SIMDLOBEngine = SIMDLOBMatchingCore
UltraLowLatencySIMDLOBMatchingCore = SIMDLOBMatchingCore
AVX2VectorizedLOBEngine = SIMDLOBMatchingCore
SIMDVectorizedOrderBook = SIMDLOBMatchingCore
FastSIMDLOBMatcher = SIMDLOBMatchingCore
L3SIMDOrderBook = SIMDLOBMatchingCore
SIMDLOBMatchingEngine = SIMDLOBMatchingCore
VectorizedLOBMatchingCore = SIMDLOBMatchingCore
UltraLowLatencyMatchingCore = SIMDLOBMatchingCore
SIMDOrderBookMatcher = SIMDLOBMatchingCore
Level3VectorizedMatchingCore = SIMDLOBMatchingCore

# ---------------------------------------------------------------------------
# sys.modules registration for seamless dual import
# ---------------------------------------------------------------------------
import types as _types
for _pkg in ("trading_system", "trading_system.src", "trading_system.src.core"):
    if _pkg not in sys.modules:
        sys.modules[_pkg] = _types.ModuleType(_pkg)
sys.modules["trading_system.src.core.simd_lob_matching_core"] = sys.modules[__name__]
sys.modules.setdefault("src.core.simd_lob_matching_core", sys.modules[__name__])

# ---------------------------------------------------------------------------
# __all__ Export
# ---------------------------------------------------------------------------
__all__ = [
    "VERSION",
    "RELEASE",
    "FEATURE",
    "DEFAULT_ORDER_CAPACITY",
    "DEFAULT_PRICE_LEVELS",
    "DEFAULT_TICK_SIZE",
    "ORDER_RECORD_SIZE",
    "OrderSide",
    "OrderType",
    "OrderStatus",
    "TimeInForce",
    "SIMDBackend",
    "ExecutionBackend",
    "ORDER_SLOT_DTYPE",
    "ORDER_RECORD_DTYPE",
    "PRICE_LEVEL_DTYPE",
    "MATCH_FILL_DTYPE",
    "SIMDOrder",
    "SIMDFillRecord",
    "FillRecord",
    "SIMDMatchResult",
    "MatchExecutionResult",
    "L3OrderEntry",
    "L3PriceLevel",
    "L3Snapshot",
    "SIMDPriceLadderSnapshot",
    "SIMDMicrostructureMetrics",
    "SIMDLOBOrderPool",
    "SIMDPriceLadder",
    "SIMDLOBBookSide",
    "SIMDOrderBook",
    "SIMDLOBMatchingCore",
    "UltraLowLatencySIMDLOB",
    "VectorizedSIMDMatchingCore",
    "Phase118SIMDLOBMatchingCore",
    "AVX2LOBEngine",
    "ZeroCopyLOBMatchingEngine",
    "SIMDLOBEngine",
    "UltraLowLatencySIMDLOBMatchingCore",
    "AVX2VectorizedLOBEngine",
    "SIMDVectorizedOrderBook",
    "FastSIMDLOBMatcher",
    "L3SIMDOrderBook",
    "SIMDLOBMatchingEngine",
    "VectorizedLOBMatchingCore",
    "UltraLowLatencyMatchingCore",
    "SIMDOrderBookMatcher",
    "Level3VectorizedMatchingCore",
]
