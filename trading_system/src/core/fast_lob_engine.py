"""
fast_lob_engine.py — High-Throughput Microsecond Tick/LOB Parser & Matching Engine

Provides:
  1. ZeroCopyRingBuffer: Pre-allocated circular buffer for sub-microsecond tick ingestion without GC overhead.
  2. FastOrderBookMatchingEngine: Level 3 FIFO Price-Time Priority matching engine with 10-level depth snapshotting.
  3. MicrosecondHawkesIntensity: Real-time self-exciting point process estimator for trade clustering and liquidity shock detection.
"""

from __future__ import annotations

import math
import time
import threading
from collections import deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any, Deque

import numpy as np


class ZeroCopyRingBuffer:
    """
    High-speed circular ring buffer pre-allocated in memory.
    Ensures O(1) tick append and zero garbage collection pressure.
    """

    def __init__(self, capacity: int = 100_000, dtype: Any = np.float64):
        self.capacity = capacity
        self.prices = np.zeros(capacity, dtype=dtype)
        self.volumes = np.zeros(capacity, dtype=dtype)
        self.timestamps = np.zeros(capacity, dtype=np.int64) # Unix epoch nanoseconds
        self.sides = np.zeros(capacity, dtype=np.int8)       # 1 for BUY, -1 for SELL
        self._head = 0
        self._size = 0
        self._lock = threading.Lock()

    def append(self, price: float, volume: float, timestamp_ns: int, is_buy: bool) -> None:
        """Appends a tick into the ring buffer with O(1) complexity."""
        with self._lock:
            idx = self._head
            self.prices[idx] = price
            self.volumes[idx] = volume
            self.timestamps[idx] = timestamp_ns
            self.sides[idx] = 1 if is_buy else -1

            self._head = (self._head + 1) % self.capacity
            if self._size < self.capacity:
                self._size += 1

    def get_recent(self, n: int) -> Dict[str, np.ndarray]:
        """Retrieves the most recent n ticks as contiguous NumPy arrays."""
        with self._lock:
            count = min(n, self._size)
            if count == 0:
                return {
                    "prices": np.array([], dtype=np.float64),
                    "volumes": np.array([], dtype=np.float64),
                    "timestamps": np.array([], dtype=np.int64),
                    "sides": np.array([], dtype=np.int8),
                }

            start_idx = (self._head - count + self.capacity) % self.capacity
            if start_idx + count <= self.capacity:
                return {
                    "prices": self.prices[start_idx : start_idx + count].copy(),
                    "volumes": self.volumes[start_idx : start_idx + count].copy(),
                    "timestamps": self.timestamps[start_idx : start_idx + count].copy(),
                    "sides": self.sides[start_idx : start_idx + count].copy(),
                }
            else:
                part1_len = self.capacity - start_idx
                part2_len = count - part1_len
                return {
                    "prices": np.concatenate([self.prices[start_idx:], self.prices[:part2_len]]),
                    "volumes": np.concatenate([self.volumes[start_idx:], self.volumes[:part2_len]]),
                    "timestamps": np.concatenate([self.timestamps[start_idx:], self.timestamps[:part2_len]]),
                    "sides": np.concatenate([self.sides[start_idx:], self.sides[:part2_len]]),
                }

    @property
    def size(self) -> int:
        with self._lock:
            return self._size


@dataclass
class OrderNode:
    order_id: str
    price: float
    volume: float
    timestamp_ns: int
    side: str # "BUY" or "SELL"


class FastOrderBookMatchingEngine:
    """
    Level 3 FIFO Price-Time Priority Order Book Matching Engine.
    Maintains sorted price levels and FIFO order queues per price tier.
    """

    def __init__(self, symbol: str, tick_size: float = 0.01):
        self.symbol = symbol
        self.tick_size = tick_size
        self.bids: Dict[float, Deque[OrderNode]] = {} # price -> FIFO queue of orders
        self.asks: Dict[float, Deque[OrderNode]] = {}
        self.order_lookup: Dict[str, Tuple[str, float]] = {} # order_id -> (side, price)
        self._lock = threading.Lock()

    def add_limit_order(
        self,
        order_id: str,
        side: str,
        price: float,
        volume: float,
        timestamp_ns: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Inserts a limit order. If it crosses the book, matches immediately against opposing resting orders.
        """
        side_upper = side.upper()
        ts = timestamp_ns or time.perf_counter_ns()
        fills: List[Dict[str, Any]] = []

        with self._lock:
            rem_vol = volume

            if side_upper == "BUY":
                # Match against asks <= price
                while rem_vol > 1e-6 and self.asks:
                    best_ask = min(self.asks.keys())
                    if best_ask > price:
                        break

                    ask_queue = self.asks[best_ask]
                    while rem_vol > 1e-6 and ask_queue:
                        resting = ask_queue[0]
                        matched_qty = min(rem_vol, resting.volume)
                        rem_vol -= matched_qty
                        resting.volume -= matched_qty

                        fills.append({
                            "symbol": self.symbol,
                            "taker_order_id": order_id,
                            "maker_order_id": resting.order_id,
                            "price": best_ask,
                            "volume": matched_qty,
                            "side": "BUY",
                            "timestamp_ns": ts,
                        })

                        if resting.volume <= 1e-6:
                            ask_queue.popleft()
                            self.order_lookup.pop(resting.order_id, None)

                    if not ask_queue:
                        del self.asks[best_ask]

                # If remaining volume exists, rest in bids
                if rem_vol > 1e-6:
                    node = OrderNode(order_id=order_id, price=price, volume=rem_vol, timestamp_ns=ts, side="BUY")
                    if price not in self.bids:
                        self.bids[price] = deque()
                    self.bids[price].append(node)
                    self.order_lookup[order_id] = ("BUY", price)

            else: # SELL
                # Match against bids >= price
                while rem_vol > 1e-6 and self.bids:
                    best_bid = max(self.bids.keys())
                    if best_bid < price:
                        break

                    bid_queue = self.bids[best_bid]
                    while rem_vol > 1e-6 and bid_queue:
                        resting = bid_queue[0]
                        matched_qty = min(rem_vol, resting.volume)
                        rem_vol -= matched_qty
                        resting.volume -= matched_qty

                        fills.append({
                            "symbol": self.symbol,
                            "taker_order_id": order_id,
                            "maker_order_id": resting.order_id,
                            "price": best_bid,
                            "volume": matched_qty,
                            "side": "SELL",
                            "timestamp_ns": ts,
                        })

                        if resting.volume <= 1e-6:
                            bid_queue.popleft()
                            self.order_lookup.pop(resting.order_id, None)

                    if not bid_queue:
                        del self.bids[best_bid]

                # If remaining volume exists, rest in asks
                if rem_vol > 1e-6:
                    node = OrderNode(order_id=order_id, price=price, volume=rem_vol, timestamp_ns=ts, side="SELL")
                    if price not in self.asks:
                        self.asks[price] = deque()
                    self.asks[price].append(node)
                    self.order_lookup[order_id] = ("SELL", price)

        return fills

    def cancel_order(self, order_id: str) -> bool:
        """Cancels a resting limit order in O(1) level lookup."""
        with self._lock:
            if order_id not in self.order_lookup:
                return False

            side, price = self.order_lookup.pop(order_id)
            book = self.bids if side == "BUY" else self.asks

            if price in book:
                queue = book[price]
                # Filter out canceled order
                new_q = deque([o for o in queue if o.order_id != order_id])
                if new_q:
                    book[price] = new_q
                else:
                    del book[price]
                return True
            return False

    def match_market_order(self, side: str, volume: float) -> List[Dict[str, Any]]:
        """Executes a taker market order sweeping resting limit depth."""
        side_upper = side.upper()
        aggressive_price = 1e9 if side_upper == "BUY" else 0.0
        return self.add_limit_order(
            order_id=f"mkt_{int(time.perf_counter_ns())}",
            side=side_upper,
            price=aggressive_price,
            volume=volume
        )

    def get_depth_snapshot(self, levels: int = 10) -> Dict[str, Any]:
        """Returns top-K bids and asks, micro-price, and multi-tier OBI."""
        with self._lock:
            sorted_bid_prices = sorted(self.bids.keys(), reverse=True)[:levels]
            sorted_ask_prices = sorted(self.asks.keys())[:levels]

            bids = [{"price": p, "volume": sum(o.volume for o in self.bids[p])} for p in sorted_bid_prices]
            asks = [{"price": p, "volume": sum(o.volume for o in self.asks[p])} for p in sorted_ask_prices]

        # Calculate Micro-Price and OBI
        p_b1 = bids[0]["price"] if bids else 0.0
        v_b1 = bids[0]["volume"] if bids else 0.0
        p_a1 = asks[0]["price"] if asks else 0.0
        v_a1 = asks[0]["volume"] if asks else 0.0

        tot_vol1 = v_b1 + v_a1
        micro_price = (v_a1 * p_b1 + v_b1 * p_a1) / tot_vol1 if tot_vol1 > 0 else (0.5 * (p_b1 + p_a1))
        spread = max(0.0, p_a1 - p_b1) if (p_a1 > 0 and p_b1 > 0) else 0.0

        # Multi-tier OBI
        obi_1 = (v_b1 - v_a1) / tot_vol1 if tot_vol1 > 0 else 0.0

        def _calc_obi(k: int) -> float:
            n = min(len(bids), len(asks), k)
            if n == 0:
                return 0.0
            num = sum(bids[i]["volume"] - asks[i]["volume"] for i in range(n))
            denom = sum(bids[i]["volume"] + asks[i]["volume"] for i in range(n))
            return float(np.clip(num / denom, -1.0, 1.0)) if denom > 0 else 0.0

        return {
            "symbol": self.symbol,
            "bids": bids,
            "asks": asks,
            "best_bid": p_b1,
            "best_ask": p_a1,
            "spread": round(spread, 4),
            "micro_price": round(micro_price, 4),
            "obi_1": round(obi_1, 4),
            "obi_5": round(_calc_obi(5), 4),
            "obi_10": round(_calc_obi(10), 4),
        }


class MicrosecondHawkesIntensity:
    """
    Online Recursive Hawkes Intensity Process Estimator.
    Computes real-time arrival intensity:
    lambda(t) = mu + (lambda(t_{i-1}) - mu) * exp(-beta * dt) + alpha
    """

    def __init__(self, mu: float = 1.0, alpha: float = 0.5, beta: float = 1.2):
        self.mu = mu
        self.alpha = alpha
        self.beta = beta
        self.last_timestamp_sec: Optional[float] = None
        self.current_intensity: float = mu
        self._lock = threading.Lock()

    def update(self, timestamp_sec: Optional[float] = None) -> float:
        """Updates the arrival intensity upon receiving a new trade event."""
        t = timestamp_sec or time.time()
        with self._lock:
            if self.last_timestamp_sec is not None:
                dt = max(0.0, t - self.last_timestamp_sec)
                # Exponential decay of past excitation + new jump alpha
                decayed = (self.current_intensity - self.mu) * math.exp(-self.beta * dt)
                self.current_intensity = self.mu + max(0.0, decayed) + self.alpha
            else:
                self.current_intensity = self.mu + self.alpha

            self.last_timestamp_sec = t
            return self.current_intensity

    def get_intensity_at(self, t_query_sec: Optional[float] = None) -> float:
        """Evaluates current decayed intensity without triggering a new event."""
        t = t_query_sec or time.time()
        with self._lock:
            if self.last_timestamp_sec is None:
                return self.mu
            dt = max(0.0, t - self.last_timestamp_sec)
            decayed = (self.current_intensity - self.mu) * math.exp(-self.beta * dt)
            return float(self.mu + max(0.0, decayed))