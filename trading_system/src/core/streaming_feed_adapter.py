"""
src/core/streaming_feed_adapter.py — Real-Time Streaming WebSocket Quote Feed & LOB Adapter

Phase 123 (Release R139 / v130 Production Master, Feature F586)
Milestone 2: Real-Time Streaming WebSocket Quote Feed & Fast LOB OMS Integration.

Provides:
- Normalized market event schemas: QuoteUpdate, DepthUpdate, TradeUpdate, TopOfBook, DepthLevel.
- Backpressure policies: DROP_OLDEST, DROP_NEWEST, BLOCK, COALESCE.
- StreamingFeedProvider abstract interface, MockStreamingProvider (synthetic deterministic stream),
  HistoricalReplayFeedProvider, and WebSocketFeedProvider.
- StreamingFeedAdapter: Bounded event queue, asynchronous & synchronous pub/sub dispatcher,
  microsecond latency & loss telemetry, multi-symbol routing.
- StreamingLOBManager: Multi-symbol order book manager connecting feed updates to
  FastOrderBookMatchingEngine instances, exposing atomic TopOfBook, Hawkes intensity,
  VPIN, and depth snapshots.
"""

from __future__ import annotations

import asyncio
import collections
from dataclasses import dataclass, field
from enum import Enum
import logging
import math
import random
import threading
import time
from abc import ABC, abstractmethod
from typing import Any, Callable, Deque, Dict, List, Optional, Sequence, Set, Tuple, Union

import numpy as np

logger = logging.getLogger(__name__)


# ==============================================================================
# 1. Event Enums & Dataclasses
# ==============================================================================

class FeedEventType(str, Enum):
    """Types of streaming market feed events."""
    QUOTE = "QUOTE"
    DEPTH = "DEPTH"
    TRADE = "TRADE"
    STATUS = "STATUS"


class BackpressurePolicy(str, Enum):
    """Queue overflow backpressure shedding policy."""
    DROP_OLDEST = "DROP_OLDEST"  # Drops oldest event in queue (optimal for real-time market data)
    DROP_NEWEST = "DROP_NEWEST"  # Discards incoming event if queue is full
    BLOCK = "BLOCK"              # Synchronously blocks / awaits with timeout
    COALESCE = "COALESCE"        # Overwrites prior quote for same symbol, keeping queue bounded


class _BoolCallable:
    """Helper enabling a boolean validity check to evaluate as bool and be callable ()."""
    def __init__(self, val: bool):
        self._val = bool(val)

    def __bool__(self) -> bool:
        return self._val

    def __call__(self) -> bool:
        return self._val

    def __eq__(self, other: Any) -> bool:
        return self._val == bool(other)

    def __repr__(self) -> str:
        return str(self._val)


@dataclass(frozen=True)
class TopOfBook:
    """Zero-contention immutable top-of-book BBO snapshot."""
    symbol: str = ""
    best_bid: float = 0.0
    best_bid_volume: float = 0.0
    best_ask: float = 0.0
    best_ask_volume: float = 0.0
    spread: float = 0.0
    spread_bps: float = 0.0
    mid_price: float = 0.0
    micro_price: float = 0.0
    timestamp_ns: int = 0
    sequence: int = 0
    venue: str = "DEFAULT"
    market: str = "DEFAULT"

    def __init__(
        self,
        symbol: str = "",
        best_bid: Optional[float] = None,
        best_bid_volume: Optional[float] = None,
        best_ask: Optional[float] = None,
        best_ask_volume: Optional[float] = None,
        spread: Optional[float] = None,
        spread_bps: Optional[float] = None,
        mid_price: Optional[float] = None,
        micro_price: Optional[float] = None,
        timestamp_ns: Optional[int] = None,
        sequence: int = 0,
        venue: str = "DEFAULT",
        market: str = "DEFAULT",
        bid_price: Optional[float] = None,
        ask_price: Optional[float] = None,
        bid_size: Optional[float] = None,
        ask_size: Optional[float] = None,
        sequence_id: Optional[int] = None,
        **kwargs
    ):
        bb = float(bid_price if bid_price is not None else (best_bid if best_bid is not None else 0.0))
        ba = float(ask_price if ask_price is not None else (best_ask if best_ask is not None else 0.0))
        bbv = float(bid_size if bid_size is not None else (best_bid_volume if best_bid_volume is not None else 0.0))
        bav = float(ask_size if ask_size is not None else (best_ask_volume if best_ask_volume is not None else 0.0))
        seq = int(sequence_id if sequence_id is not None else sequence)
        ts = int(timestamp_ns if timestamp_ns is not None else time.time_ns())
        spr = float(spread if spread is not None else max(0.0, ba - bb))
        mid = float(mid_price if mid_price is not None else (0.5 * (bb + ba) if (bb > 0 and ba > 0) else max(bb, ba)))
        sbps = float(spread_bps if spread_bps is not None else ((spr / mid * 10000.0) if mid > 0 else 0.0))
        if micro_price is not None:
            mic = float(micro_price)
        elif bbv + bav > 0:
            mic = (bbv * ba + bav * bb) / (bbv + bav)
        else:
            mic = mid

        object.__setattr__(self, "symbol", str(symbol))
        object.__setattr__(self, "best_bid", bb)
        object.__setattr__(self, "best_bid_volume", bbv)
        object.__setattr__(self, "best_ask", ba)
        object.__setattr__(self, "best_ask_volume", bav)
        object.__setattr__(self, "spread", spr)
        object.__setattr__(self, "spread_bps", sbps)
        object.__setattr__(self, "mid_price", mid)
        object.__setattr__(self, "micro_price", mic)
        object.__setattr__(self, "timestamp_ns", ts)
        object.__setattr__(self, "sequence", seq)
        object.__setattr__(self, "venue", str(venue))
        object.__setattr__(self, "market", str(market))

    @property
    def bid_price(self) -> float:
        return self.best_bid

    @property
    def ask_price(self) -> float:
        return self.best_ask

    @property
    def bid_size(self) -> float:
        return self.best_bid_volume

    @property
    def ask_size(self) -> float:
        return self.best_ask_volume

    @property
    def bid_volume(self) -> float:
        return self.best_bid_volume

    @property
    def ask_volume(self) -> float:
        return self.best_ask_volume

    @property
    def is_valid(self) -> _BoolCallable:
        valid = (
            math.isfinite(self.best_bid) and self.best_bid > 0 and
            math.isfinite(self.best_ask) and self.best_ask > 0 and
            self.best_bid <= self.best_ask
        )
        return _BoolCallable(valid)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "best_bid": self.best_bid,
            "best_bid_volume": self.best_bid_volume,
            "best_ask": self.best_ask,
            "best_ask_volume": self.best_ask_volume,
            "spread": self.spread,
            "spread_bps": self.spread_bps,
            "mid_price": self.mid_price,
            "micro_price": self.micro_price,
            "timestamp_ns": self.timestamp_ns,
            "sequence": self.sequence,
            "venue": self.venue,
            "market": self.market,
        }


@dataclass(frozen=True, slots=True)
class QuoteUpdate:
    """Normalized Top-of-Book (BBO) Quote Event."""
    symbol: str
    bid_price: float
    bid_size: float
    ask_price: float
    ask_size: float
    timestamp_ns: int = field(default_factory=time.time_ns)
    sequence: int = 0
    venue: str = "DEFAULT"
    market: str = "DEFAULT"

    @property
    def bid_volume(self) -> float:
        return self.bid_size

    @property
    def ask_volume(self) -> float:
        return self.ask_size

    @property
    def seq_num(self) -> int:
        return self.sequence

    @property
    def mid_price(self) -> float:
        if self.bid_price > 0 and self.ask_price > 0:
            return 0.5 * (self.bid_price + self.ask_price)
        return max(self.bid_price, self.ask_price)

    @property
    def spread(self) -> float:
        if self.bid_price > 0 and self.ask_price > 0:
            return self.ask_price - self.bid_price
        return 0.0

    @property
    def spread_bps(self) -> float:
        m = self.mid_price
        return (self.spread / m * 10000.0) if m > 0 else 0.0

    @property
    def micro_price(self) -> float:
        tot = self.bid_size + self.ask_size
        if tot > 0 and self.bid_price > 0 and self.ask_price > 0:
            return (self.ask_size * self.bid_price + self.bid_size * self.ask_price) / tot
        return self.mid_price

    @property
    def is_valid(self) -> _BoolCallable:
        valid = (
            math.isfinite(self.bid_price) and self.bid_price > 0 and
            math.isfinite(self.ask_price) and self.ask_price > 0 and
            self.bid_price <= self.ask_price
        )
        return _BoolCallable(valid)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "bid_price": self.bid_price,
            "bid_size": self.bid_size,
            "ask_price": self.ask_price,
            "ask_size": self.ask_size,
            "timestamp_ns": self.timestamp_ns,
            "sequence": self.sequence,
            "venue": self.venue,
            "market": self.market,
            "mid_price": self.mid_price,
            "spread": self.spread,
            "spread_bps": self.spread_bps,
            "micro_price": self.micro_price,
        }


@dataclass(frozen=True, slots=True)
class DepthLevel:
    """Individual price level in depth ladder."""
    price: float
    size: float = 0.0
    order_count: int = 1
    volume: Optional[float] = None

    def __post_init__(self):
        if self.volume is not None and self.size == 0.0:
            object.__setattr__(self, "size", float(self.volume))
        elif self.volume is None:
            object.__setattr__(self, "volume", float(self.size))


@dataclass(frozen=True, slots=True)
class DepthUpdate:
    """Normalized Multi-Level Order Book Depth Update (L2/L3)."""
    symbol: str
    bids: Sequence[DepthLevel]
    asks: Sequence[DepthLevel]
    is_snapshot: bool = True
    timestamp_ns: int = field(default_factory=time.time_ns)
    sequence: int = 0
    venue: str = "DEFAULT"
    market: str = "DEFAULT"

    @property
    def seq_num(self) -> int:
        return self.sequence

    @property
    def best_bid(self) -> float:
        return self.bids[0].price if self.bids else 0.0

    @property
    def best_ask(self) -> float:
        return self.asks[0].price if self.asks else 0.0

    @property
    def best_bid_volume(self) -> float:
        return (self.bids[0].volume if getattr(self.bids[0], "volume", None) is not None else self.bids[0].size) if self.bids else 0.0

    @property
    def best_ask_volume(self) -> float:
        return (self.asks[0].volume if getattr(self.asks[0], "volume", None) is not None else self.asks[0].size) if self.asks else 0.0

    @property
    def best_bid_size(self) -> float:
        return self.best_bid_volume

    @property
    def best_ask_size(self) -> float:
        return self.best_ask_volume

    @property
    def total_bid_depth(self) -> float:
        return sum(b.volume if getattr(b, "volume", None) is not None else b.size for b in self.bids)

    @property
    def total_ask_depth(self) -> float:
        return sum(a.volume if getattr(a, "volume", None) is not None else a.size for a in self.asks)

    @property
    def order_book_imbalance(self) -> float:
        tb = self.total_bid_depth
        ta = self.total_ask_depth
        tot = tb + ta
        return (tb - ta) / tot if tot > 0 else 0.0

    @property
    def spread(self) -> float:
        bb = self.best_bid
        ba = self.best_ask
        return max(0.0, ba - bb) if bb > 0 and ba > 0 else 0.0

    @property
    def mid_price(self) -> float:
        bb = self.best_bid
        ba = self.best_ask
        return 0.5 * (bb + ba) if bb > 0 and ba > 0 else max(bb, ba)

    @property
    def spread_bps(self) -> float:
        m = self.mid_price
        return (self.spread / m * 10000.0) if m > 0 else 0.0

    @property
    def micro_price(self) -> float:
        tot = self.best_bid_volume + self.best_ask_volume
        if tot > 0 and self.best_bid > 0 and self.best_ask > 0:
            return (self.best_bid_volume * self.best_ask + self.best_ask_volume * self.best_bid) / tot
        return self.mid_price


@dataclass(frozen=True, slots=True)
class TradeUpdate:
    """Normalized Public Market Trade Tick Print."""
    symbol: str
    price: float
    volume: float
    side: str  # "BUY", "SELL", "UNKNOWN"
    timestamp_ns: int = field(default_factory=time.time_ns)
    sequence: int = 0
    venue: str = "DEFAULT"
    trade_id: str = ""
    market: str = "DEFAULT"

    @property
    def seq_num(self) -> int:
        return self.sequence

    @property
    def notional(self) -> float:
        return self.price * self.volume


MarketFeedEvent = Union[QuoteUpdate, DepthUpdate, TradeUpdate]


@dataclass
class FeedTelemetry:
    """Real-time throughput, latency and loss telemetry."""
    events_received: int = 0
    events_dispatched: int = 0
    events_dropped_backpressure: int = 0
    current_queue_depth: int = 0
    max_queue_depth: int = 0
    mean_dispatch_latency_us: float = 0.0
    p99_dispatch_latency_us: float = 0.0
    _latencies: Deque[float] = field(default_factory=lambda: collections.deque(maxlen=2000), repr=False)
    _latency_sum_us: float = field(default=0.0, repr=False)

    @property
    def events_processed(self) -> int:
        return self.events_dispatched

    @property
    def events_dropped(self) -> int:
        return self.events_dropped_backpressure

    @property
    def avg_latency_us(self) -> float:
        return self.mean_dispatch_latency_us

    @property
    def p50_latency_us(self) -> float:
        if not self._latencies:
            return 0.0
        return float(np.percentile(list(self._latencies), 50))

    @property
    def p99_latency_us(self) -> float:
        if not self._latencies:
            return 0.0
        return float(np.percentile(list(self._latencies), 99))

    def record_latency(self, latency_us: float) -> None:
        if len(self._latencies) == self._latencies.maxlen:
            self._latency_sum_us -= self._latencies[0]
        self._latencies.append(latency_us)
        self._latency_sum_us += latency_us
        n = len(self._latencies)
        if n > 0:
            self.mean_dispatch_latency_us = self._latency_sum_us / n
            if self.events_dispatched > 0 and self.events_dispatched % 50 == 0:
                self.p99_dispatch_latency_us = float(np.percentile(list(self._latencies), 99))
            elif n < 20:
                self.p99_dispatch_latency_us = max(self._latencies)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "events_received": self.events_received,
            "events_dispatched": self.events_dispatched,
            "events_dropped_backpressure": self.events_dropped_backpressure,
            "current_queue_depth": self.current_queue_depth,
            "max_queue_depth": self.max_queue_depth,
            "mean_dispatch_latency_us": round(self.mean_dispatch_latency_us, 2),
            "p99_dispatch_latency_us": round(self.p99_latency_us, 2),
            "p50_latency_us": round(self.p50_latency_us, 2),
        }


# ==============================================================================
# 2. Feed Provider Interface & Mock Generator
# ==============================================================================

class StreamingFeedProvider(ABC):
    """Abstract base class for streaming market data providers."""

    @abstractmethod
    def connect(self) -> bool:
        """Establishes connection to the data feed source."""
        pass

    @abstractmethod
    def disconnect(self) -> bool:
        """Closes connection to the data feed source."""
        pass

    @abstractmethod
    def subscribe(self, symbols: Sequence[str]) -> bool:
        """Subscribes to market updates for symbols."""
        pass

    @abstractmethod
    def unsubscribe(self, symbols: Sequence[str]) -> bool:
        """Unsubscribes from market updates for symbols."""
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """Returns True if connected to feed."""
        pass

    async def aconnect(self) -> bool:
        """Async variant of connect."""
        return self.connect()

    async def adisconnect(self) -> bool:
        """Async variant of disconnect."""
        return self.disconnect()


class MockStreamingProvider(StreamingFeedProvider):
    """
    Deterministic synthetic quote, depth, and trade stream generator.
    Simulates geometric random walks, Poisson arrivals, and cluster bursts.
    """

    def __init__(
        self,
        symbols: Sequence[str] = ("005930", "000660", "AAPL", "MSFT"),
        frequency_hz: float = 100.0,
        spread_bps: float = 5.0,
        volatility: float = 0.01,
        seed: Optional[int] = None,
        trade_cluster_burst_mode: bool = False,
        initial_prices: Optional[Dict[str, float]] = None,
        base_prices: Optional[Dict[str, float]] = None,
    ):
        self.symbols = list(symbols)
        self.frequency_hz = max(1.0, float(frequency_hz))
        self.spread_bps = max(0.5, float(spread_bps))
        self.volatility = max(0.0001, float(volatility))
        self.trade_cluster_burst_mode = bool(trade_cluster_burst_mode)
        self.seed = seed

        self._connected = False
        self._subscribed: Set[str] = set(self.symbols)
        self._seq = 0
        self._lock = threading.Lock()

        # Seeded random state
        if seed is not None:
            self._rng = random.Random(seed)
            self._np_rng = np.random.RandomState(seed)
        else:
            self._rng = random.Random()
            self._np_rng = np.random.RandomState()

        # Initial prices
        self._prices: Dict[str, float] = {}
        defaults = {
            "005930": 75000.0,
            "000660": 130000.0,
            "AAPL": 180.0,
            "MSFT": 420.0,
        }
        init_p = base_prices or initial_prices or {}
        for s in self.symbols:
            if s in init_p:
                self._prices[s] = float(init_p[s])
            elif s in defaults:
                self._prices[s] = defaults[s]
            else:
                self._prices[s] = 1000.0 if s.isdigit() else 100.0

        self._producing = False
        self._producer_thread: Optional[threading.Thread] = None

    def connect(self) -> bool:
        self._connected = True
        return True

    def disconnect(self) -> bool:
        self.stop_producing()
        self._connected = False
        return True

    def subscribe(self, symbols: Sequence[str]) -> bool:
        with self._lock:
            for s in symbols:
                self._subscribed.add(s)
                if s not in self._prices:
                    self._prices[s] = 1000.0 if s.isdigit() else 100.0
        return True

    def unsubscribe(self, symbols: Sequence[str]) -> bool:
        with self._lock:
            for s in symbols:
                self._subscribed.discard(s)
        return True

    def is_connected(self) -> bool:
        return self._connected

    def generate_quote(self, symbol: str) -> QuoteUpdate:
        """Generates a realistic synthetic QuoteUpdate for symbol."""
        with self._lock:
            self._seq += 1
            seq = self._seq
            cur_p = self._prices.get(symbol, 100.0)

            # Random walk tick
            dt = 1.0 / self.frequency_hz
            ret = self._np_rng.normal(0.0, self.volatility * math.sqrt(dt))
            new_p = max(0.01, cur_p * (1.0 + ret))
            self._prices[symbol] = new_p

            half_spread = new_p * (self.spread_bps / 20000.0)
            is_krx = symbol.isdigit()
            tick_size = 100.0 if (is_krx and new_p >= 50000.0) else (1.0 if is_krx else 0.01)

            bid = max(tick_size, round((new_p - half_spread) / tick_size) * tick_size)
            ask = max(bid + tick_size, round((new_p + half_spread) / tick_size) * tick_size)

            bid_size = float(self._rng.randint(10, 500) * (1 if is_krx else 10))
            ask_size = float(self._rng.randint(10, 500) * (1 if is_krx else 10))

            return QuoteUpdate(
                symbol=symbol,
                bid_price=float(bid),
                bid_size=bid_size,
                ask_price=float(ask),
                ask_size=ask_size,
                timestamp_ns=time.time_ns(),
                sequence=seq,
                venue="MOCK",
            )

    def generate_depth(self, symbol: str, levels: int = 10, is_snapshot: bool = True) -> DepthUpdate:
        """Generates a realistic synthetic multi-tier DepthUpdate."""
        q = self.generate_quote(symbol)
        is_krx = symbol.isdigit()
        tick_size = 100.0 if (is_krx and q.mid_price >= 50000.0) else (1.0 if is_krx else 0.01)

        bids = []
        asks = []
        for i in range(levels):
            p_b = max(tick_size, q.bid_price - i * tick_size)
            sz_b = float(self._rng.randint(20, 1000) * (1 if is_krx else 5))
            bids.append(DepthLevel(price=round(p_b, 2), size=sz_b, order_count=self._rng.randint(1, 10)))

            p_a = q.ask_price + i * tick_size
            sz_a = float(self._rng.randint(20, 1000) * (1 if is_krx else 5))
            asks.append(DepthLevel(price=round(p_a, 2), size=sz_a, order_count=self._rng.randint(1, 10)))

        return DepthUpdate(
            symbol=symbol,
            bids=tuple(bids),
            asks=tuple(asks),
            is_snapshot=is_snapshot,
            timestamp_ns=time.time_ns(),
            sequence=q.sequence,
            venue="MOCK",
        )

    def generate_trade(
        self,
        symbol: str,
        side: Optional[str] = None,
        volume: Optional[float] = None,
        is_burst: bool = False,
    ) -> TradeUpdate:
        """Generates a realistic trade tick."""
        with self._lock:
            self._seq += 1
            seq = self._seq
            cur_p = self._prices.get(symbol, 100.0)

            if side is None:
                side = "BUY" if self._rng.random() >= 0.50 else "SELL"

            if volume is None:
                mult = 5.0 if is_burst or self.trade_cluster_burst_mode else 1.0
                volume = float(self._rng.randint(5, 200) * mult)

            # Trade price touches bid or ask
            half_spread = cur_p * (self.spread_bps / 20000.0)
            trade_p = cur_p + half_spread if side == "BUY" else cur_p - half_spread

            return TradeUpdate(
                symbol=symbol,
                price=round(max(0.01, trade_p), 2),
                volume=float(volume),
                side=side,
                timestamp_ns=time.time_ns(),
                sequence=seq,
                venue="MOCK",
                trade_id=f"TRD_{seq}",
            )

    def produce_quote_stream(self, count: int = 100, symbol: Optional[str] = None) -> List[QuoteUpdate]:
        """Synchronously generates a deterministic stream of QuoteUpdates."""
        sym = symbol or (self.symbols[0] if self.symbols else "005930")
        return [self.generate_quote(sym) for _ in range(count)]

    def produce_depth_stream(self, count: int = 50, symbol: Optional[str] = None) -> List[DepthUpdate]:
        """Synchronously generates a deterministic stream of DepthUpdates."""
        sym = symbol or (self.symbols[0] if self.symbols else "005930")
        return [self.generate_depth(sym) for _ in range(count)]

    def produce_trade_stream(
        self,
        count: int = 100,
        symbol: Optional[str] = None,
        burst_interval_ms: float = 0.0,
    ) -> List[TradeUpdate]:
        """Synchronously generates a deterministic stream of TradeUpdates."""
        sym = symbol or (self.symbols[0] if self.symbols else "005930")
        trades = []
        for _ in range(count):
            trades.append(self.generate_trade(sym))
            if burst_interval_ms > 0:
                time.sleep(burst_interval_ms / 1000.0)
        return trades

    def start_producing(
        self,
        adapter: StreamingFeedAdapter,
        duration_seconds: Optional[float] = None,
    ) -> None:
        """Starts asynchronous background event emission to the adapter."""
        if self._producing:
            return
        self._producing = True

        def _worker() -> None:
            interval = 1.0 / self.frequency_hz
            t_start = time.perf_counter()
            while self._producing:
                with self._lock:
                    active_syms = list(self._subscribed)
                if not active_syms:
                    time.sleep(interval)
                    continue

                for sym in active_syms:
                    if not self._producing:
                        break
                    # Alternating quote, depth, and occasional trades
                    r = self._rng.random()
                    if r < 0.60:
                        adapter.push_quote(self.generate_quote(sym))
                    elif r < 0.85:
                        adapter.push_depth(self.generate_depth(sym))
                    else:
                        adapter.push_trade(self.generate_trade(sym))

                if duration_seconds and (time.perf_counter() - t_start) >= duration_seconds:
                    break
                time.sleep(interval)
            self._producing = False

        self._producer_thread = threading.Thread(target=_worker, daemon=True, name="MockProducerThread")
        self._producer_thread.start()

    def stop_producing(self) -> None:
        """Stops background event production."""
        self._producing = False
        if self._producer_thread and self._producer_thread.is_alive():
            self._producer_thread.join(timeout=1.0)
        self._producer_thread = None

    def stop(self) -> None:
        """Alias for stop_producing."""
        self.stop_producing()

    def generate_next_event(self) -> MarketFeedEvent:
        """Generates the next sequential event deterministically."""
        with self._lock:
            active_syms = list(self._subscribed)
        sym = active_syms[0] if active_syms else (self.symbols[0] if self.symbols else "005930")
        r = self._rng.random()
        if r < 0.60:
            return self.generate_quote(sym)
        elif r < 0.85:
            return self.generate_depth(sym)
        else:
            return self.generate_trade(sym)


MockStreamingFeedGenerator = MockStreamingProvider  # Alias for backward-compatibility


class HistoricalReplayFeedProvider(StreamingFeedProvider):
    """Replays pre-recorded or test fixture market events with configurable speed."""

    def __init__(
        self,
        events: Optional[Sequence[MarketFeedEvent]] = None,
        speed_multiplier: float = 1.0,
        records: Optional[Sequence[MarketFeedEvent]] = None,
        playback_speed: Optional[float] = None,
    ):
        items = events if events is not None else (records or [])
        self.events = list(items)
        mult = playback_speed if playback_speed is not None else speed_multiplier
        self.speed_multiplier = max(0.0, float(mult))
        self._connected = False
        self._subscribed: Set[str] = set()
        self._replay_thread: Optional[threading.Thread] = None

    def connect(self) -> bool:
        self._connected = True
        return True

    def disconnect(self) -> bool:
        self._connected = False
        return True

    def subscribe(self, symbols: Sequence[str]) -> bool:
        self._subscribed.update(symbols)
        return True

    def unsubscribe(self, symbols: Sequence[str]) -> bool:
        self._subscribed.difference_update(symbols)
        return True

    def is_connected(self) -> bool:
        return self._connected

    def replay_into(self, adapter: StreamingFeedAdapter) -> int:
        """Replays all matching events into the adapter."""
        dispatched = 0
        for ev in self.events:
            if not self._subscribed or ev.symbol in self._subscribed or "*" in self._subscribed:
                adapter.push_event(ev)
                dispatched += 1
                if self.speed_multiplier > 0:
                    time.sleep(0.001 / self.speed_multiplier)
        return dispatched

    def start_producing(self, adapter: StreamingFeedAdapter, duration_seconds: Optional[float] = None) -> None:
        self._replay_thread = threading.Thread(target=self.replay_into, args=(adapter,), daemon=True)
        self._replay_thread.start()

    def wait_until_complete(self, timeout: float = 2.0) -> None:
        if self._replay_thread and self._replay_thread.is_alive():
            self._replay_thread.join(timeout=timeout)


class WebSocketFeedProvider(StreamingFeedProvider):
    """
    Robust WebSocket client feed provider with exponential backoff reconnect,
    heartbeat monitoring, and normalized frame dispatching.
    """

    def __init__(
        self,
        endpoint_url: str = "wss://mock.exchange.com/ws",
        symbols: Sequence[str] = (),
        reconnect_interval_sec: float = 0.5,
        max_reconnect_interval_sec: float = 15.0,
        uri: Optional[str] = None,
        initial_backoff_sec: Optional[float] = None,
        max_backoff_sec: Optional[float] = None,
        backoff_factor: float = 2.0,
    ):
        self.endpoint_url = uri or endpoint_url
        self.symbols = list(symbols)
        self.reconnect_interval_sec = initial_backoff_sec if initial_backoff_sec is not None else reconnect_interval_sec
        self.max_reconnect_interval_sec = max_backoff_sec if max_backoff_sec is not None else max_reconnect_interval_sec
        self.backoff_factor = float(backoff_factor)
        self._current_backoff = self.reconnect_interval_sec
        self._connected = False
        self._running = False
        self._subscribed: Set[str] = set(self.symbols)
        self.reconnect_count = 0

    @property
    def current_backoff(self) -> float:
        return self._current_backoff

    def connect(self) -> bool:
        self._connected = True
        self._running = True
        return True

    def disconnect(self) -> bool:
        self._connected = False
        self._running = False
        return True

    def subscribe(self, symbols: Sequence[str]) -> bool:
        self._subscribed.update(symbols)
        return True

    def unsubscribe(self, symbols: Sequence[str]) -> bool:
        self._subscribed.difference_update(symbols)
        return True

    def is_connected(self) -> bool:
        return self._connected

    def record_disconnect(self) -> None:
        self._connected = False
        self.reconnect_count += 1
        self._current_backoff = min(
            self.max_reconnect_interval_sec,
            self.reconnect_interval_sec * (self.backoff_factor ** self.reconnect_count)
        )

    def record_connect_success(self) -> None:
        self._connected = True
        self.reconnect_count = 0
        self._current_backoff = self.reconnect_interval_sec

    def simulate_disconnect(self) -> None:
        """Simulates transport disconnect for testing exponential backoff recovery."""
        self.record_disconnect()
        logger.info(f"[WebSocket] Reconnecting in {self._current_backoff:.2f}s (attempt {self.reconnect_count})")
        # Recover
        self._connected = True


# ==============================================================================
# 3. Asynchronous Event Dispatcher & Backpressure Queue
# ==============================================================================

class StreamingFeedAdapter:
    """
    High-throughput asynchronous quote/depth/trade feed dispatcher with
    bounded event queue, DROP_OLDEST backpressure, subscriber routing,
    and microsecond latency telemetry.
    """

    def __init__(
        self,
        buffer_capacity: int = 50_000,
        overflow_policy: Union[BackpressurePolicy, str] = BackpressurePolicy.DROP_OLDEST,
        lob_manager: Optional[StreamingLOBManager] = None,
        provider: Optional[StreamingFeedProvider] = None,
        on_quote_callback: Optional[Callable[[QuoteUpdate], None]] = None,
        on_depth_callback: Optional[Callable[[DepthUpdate], None]] = None,
        on_trade_callback: Optional[Callable[[TradeUpdate], None]] = None,
        max_queue_size: Optional[int] = None,
        backpressure_policy: Optional[Union[BackpressurePolicy, str]] = None,
    ):
        cap = max_queue_size if max_queue_size is not None else buffer_capacity
        self.buffer_capacity = max(2, int(cap))
        policy = backpressure_policy if backpressure_policy is not None else overflow_policy
        if isinstance(policy, str):
            self.backpressure_policy = BackpressurePolicy(policy.upper())
        else:
            self.backpressure_policy = policy

        self.lob_manager = lob_manager
        self.provider = provider
        self.telemetry = FeedTelemetry()

        self._queue: Deque[MarketFeedEvent] = collections.deque()
        self._enqueue_timestamps: Dict[int, int] = {}
        self._lock = threading.RLock()
        self._not_empty = threading.Condition(self._lock)
        self._not_full = threading.Condition(self._lock)
        self._in_flight: int = 0
        self._drained_condition = threading.Condition(self._lock)

        # Symbol & Event subscriptions: symbol -> list of callbacks
        self._symbol_callbacks: Dict[str, List[Callable[[Any], None]]] = collections.defaultdict(list)
        self._symbol_quote_callbacks: Dict[str, List[Callable[[QuoteUpdate], None]]] = collections.defaultdict(list)
        self._symbol_depth_callbacks: Dict[str, List[Callable[[DepthUpdate], None]]] = collections.defaultdict(list)
        self._symbol_trade_callbacks: Dict[str, List[Callable[[TradeUpdate], None]]] = collections.defaultdict(list)
        self._subscribers: Dict[str, List[Callable[[Any], None]]] = self._symbol_callbacks
        self._type_subscribers: Dict[FeedEventType, List[Callable[[Any], None]]] = collections.defaultdict(list)

        if on_quote_callback:
            self._type_subscribers[FeedEventType.QUOTE].append(on_quote_callback)
        if on_depth_callback:
            self._type_subscribers[FeedEventType.DEPTH].append(on_depth_callback)
        if on_trade_callback:
            self._type_subscribers[FeedEventType.TRADE].append(on_trade_callback)

        self._running = False
        self._worker_thread: Optional[threading.Thread] = None

    def enqueue(self, event: MarketFeedEvent) -> bool:
        """Alias for push_event."""
        return self.push_event(event)

    def close(self) -> None:
        """Stops background worker and closes adapter."""
        self.stop()

    def subscribe(
        self,
        symbols: Union[str, Sequence[str]],
        callback: Optional[Callable[[Any], None]] = None,
        event_type: Optional[FeedEventType] = None,
        on_quote: Optional[Callable[[QuoteUpdate], None]] = None,
        on_depth: Optional[Callable[[DepthUpdate], None]] = None,
        on_trade: Optional[Callable[[TradeUpdate], None]] = None,
    ) -> None:
        """Subscribes callback to symbol(s) or wildcard '*'."""
        sym_list = [symbols] if isinstance(symbols, str) else list(symbols)
        with self._lock:
            for sym in sym_list:
                if callback is not None:
                    if event_type in (FeedEventType.QUOTE, "QUOTE"):
                        if callback not in self._symbol_quote_callbacks[sym]:
                            self._symbol_quote_callbacks[sym].append(callback)
                    elif event_type in (FeedEventType.DEPTH, "DEPTH"):
                        if callback not in self._symbol_depth_callbacks[sym]:
                            self._symbol_depth_callbacks[sym].append(callback)
                    elif event_type in (FeedEventType.TRADE, "TRADE"):
                        if callback not in self._symbol_trade_callbacks[sym]:
                            self._symbol_trade_callbacks[sym].append(callback)
                    else:
                        if callback not in self._symbol_callbacks[sym]:
                            self._symbol_callbacks[sym].append(callback)
                if on_quote is not None:
                    if on_quote not in self._symbol_quote_callbacks[sym]:
                        self._symbol_quote_callbacks[sym].append(on_quote)
                if on_depth is not None:
                    if on_depth not in self._symbol_depth_callbacks[sym]:
                        self._symbol_depth_callbacks[sym].append(on_depth)
                if on_trade is not None:
                    if on_trade not in self._symbol_trade_callbacks[sym]:
                        self._symbol_trade_callbacks[sym].append(on_trade)
                if self.provider:
                    self.provider.subscribe([sym])

    def unsubscribe(
        self,
        symbols: Union[str, Sequence[str]],
        callback: Optional[Callable[[Any], None]] = None,
    ) -> None:
        """Unsubscribes callback from symbol(s)."""
        sym_list = [symbols] if isinstance(symbols, str) else list(symbols)
        with self._lock:
            for sym in sym_list:
                for cdict in (self._symbol_callbacks, self._symbol_quote_callbacks,
                              self._symbol_depth_callbacks, self._symbol_trade_callbacks):
                    if callback is not None:
                        if callback in cdict[sym]:
                            cdict[sym].remove(callback)
                    else:
                        cdict.pop(sym, None)
                if self.provider:
                    self.provider.unsubscribe([sym])

    def subscribe_quote(self, symbol: str, callback: Callable[[QuoteUpdate], None]) -> None:
        """Subscribes callback to QuoteUpdate events for symbol."""
        self.subscribe(symbol, callback=callback, event_type=FeedEventType.QUOTE)

    def subscribe_depth(self, symbol: str, callback: Callable[[DepthUpdate], None]) -> None:
        """Subscribes callback to DepthUpdate events for symbol."""
        self.subscribe(symbol, callback=callback, event_type=FeedEventType.DEPTH)

    def subscribe_trade(self, symbol: str, callback: Callable[[TradeUpdate], None]) -> None:
        """Subscribes callback to TradeUpdate events for symbol."""
        self.subscribe(symbol, callback=callback, event_type=FeedEventType.TRADE)

    def subscribe_all(self, callback: Callable[[Any], None]) -> None:
        """Subscribes callback to all events on any symbol ('*')."""
        self.subscribe("*", callback=callback)

    def push_quote(self, quote: QuoteUpdate) -> bool:
        """Enqueues QuoteUpdate with backpressure handling."""
        return self.push_event(quote)

    def push_depth(self, depth: DepthUpdate) -> bool:
        """Enqueues DepthUpdate with backpressure handling."""
        return self.push_event(depth)

    def push_trade(self, trade: TradeUpdate) -> bool:
        """Enqueues TradeUpdate with backpressure handling."""
        return self.push_event(trade)

    def push_event(self, event: MarketFeedEvent) -> bool:
        """
        Enqueues an event into bounded queue following BackpressurePolicy.
        Returns True if accepted/enqueued, False if dropped under DROP_NEWEST.
        """
        ts_enqueue = time.perf_counter_ns()
        with self._lock:
            self.telemetry.events_received += 1

            if self.backpressure_policy == BackpressurePolicy.COALESCE and isinstance(event, QuoteUpdate):
                replaced = False
                for idx, old_ev in enumerate(self._queue):
                    if isinstance(old_ev, QuoteUpdate) and old_ev.symbol == event.symbol:
                        old_dropped = self._queue[idx]
                        self._enqueue_timestamps.pop(id(old_dropped), None)
                        self._queue[idx] = event
                        self._enqueue_timestamps[id(event)] = ts_enqueue
                        replaced = True
                        break
                if replaced:
                    return True

            q_len = len(self._queue)
            if q_len >= self.buffer_capacity:
                if self.backpressure_policy == BackpressurePolicy.DROP_OLDEST:
                    dropped = self._queue.popleft()
                    self._enqueue_timestamps.pop(id(dropped), None)
                    self.telemetry.events_dropped_backpressure += 1
                elif self.backpressure_policy == BackpressurePolicy.DROP_NEWEST:
                    self.telemetry.events_dropped_backpressure += 1
                    return False
                elif self.backpressure_policy == BackpressurePolicy.COALESCE:
                    dropped = self._queue.popleft()
                    self._enqueue_timestamps.pop(id(dropped), None)
                    self.telemetry.events_dropped_backpressure += 1
                elif self.backpressure_policy == BackpressurePolicy.BLOCK:
                    # Wait up to 100ms for space
                    self._not_full.wait(timeout=0.1)
                    if len(self._queue) >= self.buffer_capacity:
                        self.telemetry.events_dropped_backpressure += 1
                        return False

            self._queue.append(event)
            self._enqueue_timestamps[id(event)] = ts_enqueue
            curr_depth = len(self._queue)
            self.telemetry.current_queue_depth = curr_depth
            if curr_depth > self.telemetry.max_queue_depth:
                self.telemetry.max_queue_depth = curr_depth

            self._not_empty.notify()
            return True

    def start(self) -> None:
        """Starts the asynchronous dispatcher worker thread."""
        with self._lock:
            if self._running:
                return
            self._running = True
            if self.provider and not self.provider.is_connected():
                self.provider.connect()
            self._worker_thread = threading.Thread(target=self._dispatch_loop, daemon=True, name="FeedAdapterWorker")
            self._worker_thread.start()

    def stop(self) -> None:
        """Stops the dispatcher worker thread and provider."""
        with self._lock:
            self._running = False
            self._not_empty.notify_all()
            self._not_full.notify_all()
            self._drained_condition.notify_all()

        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=2.0)
        self._worker_thread = None

        if self.provider and self.provider.is_connected():
            self.provider.disconnect()

    def flush(self, timeout_sec: float = 2.0, timeout: Optional[float] = None) -> int:
        """
        Synchronously drains and dispatches all currently queued events.
        Useful for deterministic testing.
        """
        effective_timeout = timeout if timeout is not None else timeout_sec
        dispatched_count = 0
        t0 = time.perf_counter()
        while time.perf_counter() - t0 < effective_timeout:
            with self._lock:
                if not self._queue and self._in_flight == 0:
                    break

                if self._worker_thread and self._worker_thread.is_alive() and threading.current_thread() != self._worker_thread:
                    rem = effective_timeout - (time.perf_counter() - t0)
                    if rem <= 0:
                        break
                    self._drained_condition.wait(timeout=min(0.01, rem))
                    continue

                if not self._queue:
                    if self._in_flight == 0:
                        break
                    rem = effective_timeout - (time.perf_counter() - t0)
                    if rem <= 0:
                        break
                    self._drained_condition.wait(timeout=min(0.01, rem))
                    continue

                event = self._queue.popleft()
                self._in_flight += 1
                ts_enqueue = self._enqueue_timestamps.pop(id(event), time.perf_counter_ns())
                self._not_full.notify()
                self.telemetry.current_queue_depth = len(self._queue)

            try:
                self._dispatch_event(event, ts_enqueue)
            finally:
                with self._lock:
                    self._in_flight = max(0, self._in_flight - 1)
                    self._drained_condition.notify_all()
            dispatched_count += 1
        return dispatched_count

    def get_telemetry(self) -> Dict[str, Any]:
        """Returns snapshot of current feed telemetry metrics."""
        with self._lock:
            self.telemetry.current_queue_depth = len(self._queue)
            return self.telemetry.to_dict()

    def reset_telemetry(self) -> None:
        """Resets telemetry counters."""
        with self._lock:
            self.telemetry = FeedTelemetry()

    def _dispatch_loop(self) -> None:
        """Internal dispatch loop running in dedicated worker thread."""
        while self._running:
            event = None
            ts_enqueue = 0
            with self._lock:
                while self._running and not self._queue:
                    self._not_empty.wait(timeout=0.1)
                if not self._running:
                    break
                if self._queue:
                    event = self._queue.popleft()
                    self._in_flight += 1
                    ts_enqueue = self._enqueue_timestamps.pop(id(event), time.perf_counter_ns())
                    self._not_full.notify()
                    self.telemetry.current_queue_depth = len(self._queue)

            if event is not None:
                try:
                    self._dispatch_event(event, ts_enqueue)
                finally:
                    with self._lock:
                        self._in_flight = max(0, self._in_flight - 1)
                        self._drained_condition.notify_all()

    def _dispatch_event(self, event: MarketFeedEvent, ts_enqueue: int) -> None:
        """Dispatches an event to LOB manager and matching subscriber callbacks."""
        t_dispatch_start = time.perf_counter_ns()
        # 1. Update attached StreamingLOBManager
        if self.lob_manager:
            try:
                if isinstance(event, QuoteUpdate):
                    self.lob_manager.on_quote(event)
                elif isinstance(event, DepthUpdate):
                    self.lob_manager.on_depth(event)
                elif isinstance(event, TradeUpdate):
                    self.lob_manager.on_trade(event)
            except Exception as e:
                logger.error(f"[FeedAdapter] Error updating LOB manager: {e}", exc_info=True)

        # 2. Collect target callbacks
        callbacks: List[Callable[[Any], None]] = []
        seen = set()

        def _add(cb):
            if id(cb) not in seen:
                seen.add(id(cb))
                callbacks.append(cb)

        with self._lock:
            # Symbol generic callbacks
            for cb in self._symbol_callbacks.get(event.symbol, []):
                _add(cb)
            for cb in self._symbol_callbacks.get("*", []):
                _add(cb)

            if isinstance(event, QuoteUpdate):
                for cb in self._symbol_quote_callbacks.get(event.symbol, []):
                    _add(cb)
                for cb in self._symbol_quote_callbacks.get("*", []):
                    _add(cb)
                for cb in self._type_subscribers.get(FeedEventType.QUOTE, []):
                    _add(cb)
            elif isinstance(event, DepthUpdate):
                for cb in self._symbol_depth_callbacks.get(event.symbol, []):
                    _add(cb)
                for cb in self._symbol_depth_callbacks.get("*", []):
                    _add(cb)
                for cb in self._type_subscribers.get(FeedEventType.DEPTH, []):
                    _add(cb)
            elif isinstance(event, TradeUpdate):
                for cb in self._symbol_trade_callbacks.get(event.symbol, []):
                    _add(cb)
                for cb in self._symbol_trade_callbacks.get("*", []):
                    _add(cb)
                for cb in self._type_subscribers.get(FeedEventType.TRADE, []):
                    _add(cb)

        # 3. Invoke callbacks with error isolation
        for cb in callbacks:
            try:
                if asyncio.iscoroutinefunction(cb):
                    # Asynchronous coroutine callback execution
                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            asyncio.run_coroutine_threadsafe(cb(event), loop)
                        else:
                            loop.run_until_complete(cb(event))
                    except RuntimeError:
                        asyncio.run(cb(event))
                else:
                    # Standard synchronous callback
                    cb(event)
            except Exception as e:
                logger.error(f"[FeedAdapter] Exception in subscriber callback {getattr(cb, '__name__', cb)}: {e}")

        # 4. Telemetry tracking
        latency_us = (time.perf_counter_ns() - t_dispatch_start) / 1000.0
        with self._lock:
            self.telemetry.events_dispatched += 1
            self.telemetry.record_latency(latency_us)


# ==============================================================================
# 4. Multi-Symbol LOB Manager
# ==============================================================================

class StreamingLOBManager:
    """
    Coordinates multi-symbol FastOrderBookMatchingEngine instances,
    Hawkes processes, and VPIN toxicity estimators.
    """

    def __init__(self, tick_sizes: Optional[Dict[str, float]] = None):
        self.tick_sizes = tick_sizes or {}
        # Lazy imported / instantiated FastOrderBookMatchingEngine
        self._books: Dict[str, Any] = {}
        self._latest_quotes: Dict[str, QuoteUpdate] = {}
        self._lock = threading.RLock()

    def get_or_create(self, symbol: str, tick_size: Optional[float] = None) -> Any:
        """Retrieves or creates a FastOrderBookMatchingEngine for symbol."""
        with self._lock:
            if symbol not in self._books:
                from src.core.fast_lob_engine import FastOrderBookMatchingEngine
                ts = tick_size or self.tick_sizes.get(symbol, (100.0 if symbol.isdigit() else 0.01))
                self._books[symbol] = FastOrderBookMatchingEngine(symbol=symbol, tick_size=ts)
            return self._books[symbol]

    def get_book(self, symbol: str, tick_size: Optional[float] = None) -> Any:
        """Alias for get_or_create."""
        return self.get_or_create(symbol, tick_size=tick_size)

    def get(self, symbol: str, default: Any = None) -> Any:
        """Dict-like access returning market state for symbol."""
        if self.has_symbol(symbol):
            return self.get_market_state(symbol)
        return default

    def __getitem__(self, symbol: str) -> Dict[str, Any]:
        return self.get_market_state(symbol)

    def __contains__(self, symbol: str) -> bool:
        return self.has_symbol(symbol)

    def has_symbol(self, symbol: str) -> bool:
        """Checks if symbol is tracked in LOB manager."""
        with self._lock:
            return symbol in self._books

    def on_quote(self, quote: QuoteUpdate) -> TopOfBook:
        """Ingests QuoteUpdate into target book."""
        book = self.get_or_create(quote.symbol)
        tob = book.on_quote_update(
            bid_price=quote.bid_price,
            bid_size=quote.bid_size,
            ask_price=quote.ask_price,
            ask_size=quote.ask_size,
            timestamp_ns=quote.timestamp_ns,
            venue=quote.venue,
        )
        with self._lock:
            self._latest_quotes[quote.symbol] = quote
        return tob

    def on_depth(self, depth: DepthUpdate) -> TopOfBook:
        """Ingests DepthUpdate into target book."""
        book = self.get_or_create(depth.symbol)
        tob = book.on_depth_update(
            bids=depth.bids,
            asks=depth.asks,
            is_snapshot=depth.is_snapshot,
            timestamp_ns=depth.timestamp_ns,
            venue=depth.venue,
        )
        return tob

    def on_trade(self, trade: TradeUpdate) -> Dict[str, Any]:
        """Ingests TradeUpdate into target book, exciting Hawkes and updating VPIN."""
        book = self.get_or_create(trade.symbol)
        return book.on_trade_tick(
            price=trade.price,
            volume=trade.volume,
            side=trade.side,
            timestamp_ns=trade.timestamp_ns,
            venue=trade.venue,
        )

    def get_top_of_book(self, symbol: str) -> Optional[TopOfBook]:
        """Atomic lockless read of top-of-book for symbol."""
        with self._lock:
            book = self._books.get(symbol)
        if book is not None:
            return book.get_top_of_book()
        return None

    def get_effective_spread(self, symbol: str, side: str = "BUY", quantity: float = 100.0) -> float:
        """Calculates volume-weighted effective spread in bps against resting depth."""
        with self._lock:
            book = self._books.get(symbol)
        if book is not None:
            return book.get_effective_spread(side=side, quantity=quantity)
        return 10.0

    def get_hawkes_intensity(self, symbol: str) -> float:
        """Returns total decaying Hawkes arrival intensity for symbol."""
        with self._lock:
            book = self._books.get(symbol)
        if book is not None:
            return book.get_hawkes_intensity()
        return 1.0

    def get_vpin(self, symbol: str) -> float:
        """Returns rolling Volume-Synchronized Probability of Toxicity (VPIN) for symbol."""
        with self._lock:
            book = self._books.get(symbol)
        if book is not None:
            return book.get_vpin()
        return 0.0

    def get_depth_snapshot(self, symbol: str, levels: int = 10) -> Optional[Dict[str, Any]]:
        """Returns depth snapshot dict from book."""
        with self._lock:
            book = self._books.get(symbol)
        if book is not None:
            return book.get_depth_snapshot(levels=levels)
        return None

    def get_market_state(self, symbol: str) -> Dict[str, Any]:
        """
        Returns comprehensive instantaneous microstructure state for OMS & Paper Trading:
        - best_bid, best_ask, spread, spread_bps, mid_price, micro_price
        - obi_1, obi_5, obi_10, l3_imbalance, l3_micro_price
        - hawkes_intensity, hawkes_toxicity, hawkes_arrival_imbalance
        - vpin_score, is_toxic
        """
        tob = self.get_top_of_book(symbol)
        snap = self.get_depth_snapshot(symbol, levels=10) or {}
        h_int = self.get_hawkes_intensity(symbol)
        vpin = self.get_vpin(symbol)

        # Hawkes directional metrics if bivariate hawkes present
        h_tox = 0.0
        h_imb = 0.0
        with self._lock:
            book = self._books.get(symbol)
            if book is not None and hasattr(book, "bivariate_hawkes") and book.bivariate_hawkes is not None:
                tox_dict = book.bivariate_hawkes.get_directional_toxicity("BUY")
                h_tox = float(tox_dict.get("gamma_toxic_dir", 0.0))
                imb_dict = book.bivariate_hawkes.get_arrival_imbalance()
                h_imb = float(imb_dict.get("delta_lambda_dir", 0.0))

        bb = tob.best_bid if tob else float(snap.get("best_bid", 0.0))
        ba = tob.best_ask if tob else float(snap.get("best_ask", 0.0))
        mid = tob.mid_price if tob else (0.5 * (bb + ba) if (bb > 0 and ba > 0) else max(bb, ba))
        spr = tob.spread if tob else float(snap.get("spread", 0.0))
        spr_bps = tob.spread_bps if tob else ((spr / mid * 10000.0) if mid > 0 else 0.0)
        micro = tob.micro_price if tob else float(snap.get("micro_price", mid))

        return {
            "symbol": symbol,
            "best_bid": bb,
            "best_ask": ba,
            "bid": bb,
            "ask": ba,
            "spread": spr,
            "spread_bps": spr_bps,
            "mid_price": mid,
            "micro_price": micro,
            "l3_micro_price": snap.get("l3_micro_price", micro),
            "l3_imbalance": snap.get("l3_imbalance", 0.0),
            "obi_1": snap.get("obi_1", 0.0),
            "obi_5": snap.get("obi_5", 0.0),
            "obi_10": snap.get("obi_10", 0.0),
            "hawkes_intensity": h_int,
            "hawkes_toxicity": h_tox,
            "hawkes_arrival_imbalance": h_imb,
            "vpin": vpin,
            "vpin_score": vpin,
            "is_toxic": bool(vpin >= 0.70 or h_tox >= 0.70),
            "timestamp_ns": tob.timestamp_ns if tob else time.time_ns(),
        }

    get_symbol_state = get_market_state

    def get_all_snapshots(self) -> Dict[str, Dict[str, Any]]:
        """Returns market state for all registered symbols."""
        with self._lock:
            syms = list(self._books.keys())
        return {s: self.get_market_state(s) for s in syms}


MultiSymbolLOBManager = StreamingLOBManager  # Alias for backward-compatibility
