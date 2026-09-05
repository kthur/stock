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
from dataclasses import dataclass
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
        self._lock = threading.RLock()
        self._qi_history: Deque[Tuple[float, float]] = deque(maxlen=20)

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

    def estimate_queue_position(self, order_id: str) -> Optional[Dict[str, Any]]:
        """
        F44: Computes exact FIFO queue position and fill probability for a resting order.
        Returns:
            queue_ahead: Volume ahead of this order in the FIFO queue
            queue_behind: Volume behind this order in the FIFO queue
            my_volume: Order's current active volume
            queue_position_ratio: u_q = Q_ahead / max(1e-6, Q_ahead + my_vol + Q_behind) in [0.0, 1.0]
            estimated_p_fill: Non-linear probability of execution before cancellation
        """
        with self._lock:
            if order_id not in self.order_lookup:
                return None
            side, price = self.order_lookup[order_id]
            book = self.bids if side == "BUY" else self.asks
            if price not in book:
                return None

            q = book[price]
            q_ahead = 0.0
            my_vol = 0.0
            q_behind = 0.0
            found = False

            for node in q:
                if node.order_id == order_id:
                    my_vol = node.volume
                    found = True
                elif not found:
                    q_ahead += node.volume
                else:
                    q_behind += node.volume

            if not found:
                return None

            tot = q_ahead + my_vol + q_behind
            u_q = float(q_ahead / max(1e-6, tot))
            # Cont-Kukanov fill probability: P_fill(u_q) = exp(-1.5 * u_q) * (1 - 0.25 * u_q)
            p_fill = float(np.clip(math.exp(-1.5 * u_q) * (1.0 - 0.25 * u_q), 0.05, 0.95))

            return {
                "order_id": order_id,
                "side": side,
                "price": price,
                "my_volume": my_vol,
                "queue_ahead": q_ahead,
                "queue_behind": q_behind,
                "total_level_volume": tot,
                "queue_position_ratio": round(u_q, 4),
                "estimated_p_fill": round(p_fill, 4),
            }

    def get_depth_snapshot(self, levels: int = 10) -> Dict[str, Any]:
        """Returns top-K bids and asks, micro-price, L3 depth decay micro-price, and multi-tier OBI."""
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

        # Multi-level exponential depth decay micro-price (lambda_depth = 0.35, F44)
        w_k = [math.exp(-0.35 * i) for i in range(min(len(bids), len(asks), levels))]
        if w_k and sum(w_k) > 0:
            num_l3 = sum(w_k[i] * (bids[i]["volume"] - asks[i]["volume"]) for i in range(len(w_k)))
            den_l3 = sum(w_k[i] * (bids[i]["volume"] + asks[i]["volume"]) for i in range(len(w_k)))
            l3_imbalance = float(np.clip(num_l3 / max(1e-6, den_l3), -1.0, 1.0)) if den_l3 > 0 else 0.0
            l3_micro_price = 0.5 * (p_b1 + p_a1) + 0.5 * spread * l3_imbalance
        else:
            l3_imbalance = obi_1
            l3_micro_price = micro_price

        # Order count fragmentation ratio at best bid/ask (F44)
        with self._lock:
            n_b1 = len(self.bids.get(p_b1, [])) if p_b1 in self.bids else 1
            n_a1 = len(self.asks.get(p_a1, [])) if p_a1 in self.asks else 1
        avg_sz_b1 = v_b1 / max(1, n_b1)
        avg_sz_a1 = v_a1 / max(1, n_a1)
        frag_ratio = float(np.clip(avg_sz_b1 / max(1e-6, avg_sz_a1), 0.1, 10.0))

        return {
            "symbol": self.symbol,
            "bids": bids,
            "asks": asks,
            "best_bid": p_b1,
            "best_ask": p_a1,
            "spread": round(spread, 4),
            "micro_price": round(micro_price, 4),
            "l3_micro_price": round(l3_micro_price, 4),
            "l3_imbalance": round(l3_imbalance, 4),
            "order_fragmentation_ratio": round(frag_ratio, 4),
            "n_orders_best_bid": n_b1,
            "n_orders_best_ask": n_a1,
            "obi_1": round(obi_1, 4),
            "obi_5": round(_calc_obi(5), 4),
            "obi_10": round(_calc_obi(10), 4),
        }

    def get_best_bid(self) -> Tuple[float, float]:
        """Returns (price, total_volume) of the highest active bid level."""
        with self._lock:
            for p in sorted(self.bids.keys(), reverse=True):
                if p > 0 and self.bids[p]:
                    return p, sum(o.volume for o in self.bids[p])
        return 0.0, 0.0

    def get_best_ask(self) -> Tuple[float, float]:
        """Returns (price, total_volume) of the lowest active ask level."""
        with self._lock:
            for p in sorted(self.asks.keys()):
                if p > 0 and self.asks[p]:
                    return p, sum(o.volume for o in self.asks[p])
        return 0.0, 0.0

    def compute_l3_queue_imbalance(
        self,
        levels: int = 10,
        lambda_depth: float = 0.35,
        alpha_dist: float = 0.50,
        timestamp_sec: Optional[float] = None,
    ) -> Dict[str, float]:
        """
        Phase 7 (F50.1) & Phase 8 (F54.1): Physical Distance-Decayed, Fragmentation-Adjusted,
        and 2nd-Order Time-Derivative Accelerated Level-3 Queue Imbalance (QI_L3*, v_QI, a_QI).
        w_k^dist = exp(-lambda_depth * k - alpha_dist * |P_k - P_1| / max(spread, tick_size))
        Phi_k^bid = ( (V_k^bid / N_k^bid) / (V_k^bid / N_k^bid + V_k^ask / N_k^ask) )^0.25
        v_QI = dQI/dt, a_QI = d^2QI/dt^2
        QI_pred = clip(QI + tau_lead * v_QI + 0.5 * tau_lead^2 * a_QI, -1.0, 1.0)
        """
        with self._lock:
            p_b1, v_b1 = self.get_best_bid()
            p_a1, v_a1 = self.get_best_ask()
            if p_b1 <= 0 or p_a1 <= 0 or p_b1 >= p_a1:
                return {
                    "l3_queue_imbalance": 0.0,
                    "l3_micro_price": max(p_b1, p_a1, 0.0),
                    "qi_velocity": 0.0,
                    "qi_acceleration": 0.0,
                    "accelerated_l3_micro_price": max(p_b1, p_a1, 0.0),
                    "weighted_bid_depth": 0.0,
                    "weighted_ask_depth": 0.0,
                }

            spread = max(1e-4, p_a1 - p_b1)
            tick_size = max(1e-4, spread * 0.10)
            norm_unit = max(spread, tick_size)

            bids = [
                {"price": p, "volume": sum(o.volume for o in self.bids[p]), "n_orders": max(1, len(self.bids[p]))}
                for p in sorted(self.bids.keys(), reverse=True) if p > 0 and self.bids[p]
            ][:levels]
            asks = [
                {"price": p, "volume": sum(o.volume for o in self.asks[p]), "n_orders": max(1, len(self.asks[p]))}
                for p in sorted(self.asks.keys()) if p > 0 and self.asks[p]
            ][:levels]

        if not bids and not asks:
            p_mid = 0.5 * (p_b1 + p_a1)
            return {
                "l3_queue_imbalance": 0.0,
                "l3_micro_price": p_mid,
                "qi_velocity": 0.0,
                "qi_acceleration": 0.0,
                "accelerated_l3_micro_price": p_mid,
                "weighted_bid_depth": 0.0,
                "weighted_ask_depth": 0.0,
            }

        w_bid_tot = 0.0
        w_ask_tot = 0.0

        for k in range(len(bids)):
            dist_b = abs(bids[k]["price"] - p_b1) / norm_unit
            w_k_bid = math.exp(-lambda_depth * k - alpha_dist * dist_b)
            avg_sz_b = bids[k]["volume"] / bids[k]["n_orders"]
            avg_sz_a = (asks[k]["volume"] / asks[k]["n_orders"]) if k < len(asks) else (asks[0]["volume"] / asks[0]["n_orders"])
            tot_avg = avg_sz_b + avg_sz_a
            phi_bid = (avg_sz_b / tot_avg) ** 0.25 if tot_avg > 0 else 1.0
            w_bid_tot += w_k_bid * bids[k]["volume"] * phi_bid

        for k in range(len(asks)):
            dist_a = abs(asks[k]["price"] - p_a1) / norm_unit
            w_k_ask = math.exp(-lambda_depth * k - alpha_dist * dist_a)
            avg_sz_a = asks[k]["volume"] / asks[k]["n_orders"]
            avg_sz_b = (bids[k]["volume"] / bids[k]["n_orders"]) if k < len(bids) else (bids[0]["volume"] / bids[0]["n_orders"])
            tot_avg = avg_sz_b + avg_sz_a
            phi_ask = (avg_sz_a / tot_avg) ** 0.25 if tot_avg > 0 else 1.0
            w_ask_tot += w_k_ask * asks[k]["volume"] * phi_ask

        den = w_bid_tot + w_ask_tot
        qi_l3 = float(np.clip((w_bid_tot - w_ask_tot) / max(1e-6, den), -1.0, 1.0)) if den > 0 else 0.0
        p_mid = 0.5 * (p_b1 + p_a1)
        l3_micro_price = p_mid + 0.5 * spread * qi_l3

        # F54.1 & F58.1: Level-3 Queue Imbalance Acceleration (d^2QI/dt^2) and 3rd-order Jerk (d^3QI/dt^3)
        t_now = float(timestamp_sec) if (timestamp_sec is not None and math.isfinite(float(timestamp_sec))) else time.time()
        with self._lock:
            self._qi_history.append((t_now, qi_l3))

            qi_velocity = 0.0
            qi_acceleration = 0.0
            qi_jerk = 0.0

            if len(self._qi_history) >= 2:
                t0, q0 = self._qi_history[-1]
                t1, q1 = self._qi_history[-2]
                dt1 = max(1e-4, t0 - t1)
                v0 = (q0 - q1) / dt1
                qi_velocity = float(np.clip(v0, -20.0, 20.0))

                if len(self._qi_history) >= 3:
                    t2, q2 = self._qi_history[-3]
                    dt2 = max(1e-4, t1 - t2)
                    v1 = (q1 - q2) / dt2
                    dt_mid = max(1e-4, 0.5 * (dt1 + dt2))
                    qi_acceleration = float(np.clip((v0 - v1) / dt_mid, -50.0, 50.0))

                    if len(self._qi_history) >= 4:
                        t3, q3 = self._qi_history[-4]
                        dt3 = max(1e-4, t2 - t3)
                        v2 = (q2 - q3) / dt3
                        dt_mid1 = max(1e-4, 0.5 * (dt2 + dt3))
                        a1 = (v1 - v2) / dt_mid1
                        dt_jerk = max(1e-4, 0.5 * (dt_mid + dt_mid1))
                        qi_jerk = float(np.clip((qi_acceleration - a1) / dt_jerk, -100.0, 100.0))

        # Level 1..5 Deep-OFI (Feature F58.1)
        deep_ofi_weights = [math.exp(-0.6 * k) for k in range(min(5, max(len(bids), len(asks))))]
        deep_ofi_num = 0.0
        deep_ofi_den = 0.0
        for k in range(len(deep_ofi_weights)):
            b_vol = bids[k]["volume"] if k < len(bids) else 0.0
            a_vol = asks[k]["volume"] if k < len(asks) else 0.0
            w_k = deep_ofi_weights[k]
            deep_ofi_num += w_k * (b_vol - a_vol)
            deep_ofi_den += w_k * (b_vol + a_vol)
        deep_ofi = float(np.clip(deep_ofi_num / max(1e-6, deep_ofi_den), -1.0, 1.0)) if deep_ofi_den > 0 else 0.0

        # Predictive Taylor Expansion Micro-Price
        tau_lead = 0.10  # 100ms predictive horizon
        qi_pred = float(np.clip(qi_l3 + tau_lead * qi_velocity + 0.5 * (tau_lead ** 2) * qi_acceleration, -1.0, 1.0))
        accel_micro_price = p_mid + 0.5 * spread * qi_pred

        # Feature F58.1: 3rd-order Taylor Expansion Micro-Price with Deep-OFI
        tau3 = (tau_lead ** 3) / 6.0
        qi_pred_v9 = float(np.clip(
            qi_l3 + tau_lead * qi_velocity + 0.5 * (tau_lead ** 2) * qi_acceleration + tau3 * qi_jerk + 0.15 * deep_ofi,
            -1.0, 1.0
        ))
        jerk_micro_price = p_mid + 0.5 * spread * qi_pred_v9

        return {
            "l3_queue_imbalance": round(qi_l3, 4),
            "l3_micro_price": round(l3_micro_price, 4),
            "qi_velocity": round(qi_velocity, 4),
            "qi_acceleration": round(qi_acceleration, 4),
            "qi_jerk": round(qi_jerk, 4),
            "deep_ofi": round(deep_ofi, 4),
            "accelerated_l3_micro_price": round(accel_micro_price, 4),
            "jerk_micro_price": round(jerk_micro_price, 4),
            "weighted_bid_depth": round(w_bid_tot, 4),
            "weighted_ask_depth": round(w_ask_tot, 4),
        }

    def compute_deep_ofi_jerk_microprice(
        self,
        depth: int = 5,
        timestamp_sec: Optional[float] = None
    ) -> Dict[str, float]:
        """Convenience method for Feature F58.1 Deep-OFI and 3rd-order Taylor micro-price."""
        return self.compute_l3_queue_imbalance(levels=depth, timestamp_sec=timestamp_sec)

    compute_l3_fragmentation_adjusted_imbalance = compute_l3_queue_imbalance


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


class BivariateHawkesIntensity:
    """
    F44: Directional Bivariate Hawkes Intensity Process for Buy/Sell Toxicity Tracking.
    Maintains coupled arrival intensities:
        lambda_+(t) = mu_+ + (lambda_+ - mu_+) * exp(-beta * dt) + alpha_self * dN_+ + alpha_cross * dN_-
        lambda_-(t) = mu_- + (lambda_- - mu_-) * exp(-beta * dt) + alpha_self * dN_- + alpha_cross * dN_+
    """

    def __init__(
        self,
        mu_buy: float = 1.0,
        mu_sell: float = 1.0,
        alpha_self: float = 0.4,
        alpha_cross: float = 0.1,
        beta: float = 1.2,
    ):
        self.mu_buy = float(mu_buy)
        self.mu_sell = float(mu_sell)
        self.alpha_self = float(alpha_self)
        self.alpha_cross = float(alpha_cross)
        self.beta = float(beta)
        self.last_ts: Optional[float] = None
        self.lambda_buy = float(mu_buy)
        self.lambda_sell = float(mu_sell)
        self._lock = threading.Lock()

    def update(self, side: str, timestamp_sec: Optional[float] = None) -> Tuple[float, float]:
        """Updates coupled arrival intensities with a directional trade event."""
        t = timestamp_sec or time.time()
        with self._lock:
            if self.last_ts is not None:
                dt = max(0.0, t - self.last_ts)
                decay = math.exp(-self.beta * dt)
                self.lambda_buy = self.mu_buy + max(0.0, self.lambda_buy - self.mu_buy) * decay
                self.lambda_sell = self.mu_sell + max(0.0, self.lambda_sell - self.mu_sell) * decay

            side_upper = str(side).upper()
            if side_upper in ["BUY", "BID"]:
                self.lambda_buy += self.alpha_self
                self.lambda_sell += self.alpha_cross
            else:
                self.lambda_sell += self.alpha_self
                self.lambda_buy += self.alpha_cross

            self.last_ts = t
            return (self.lambda_buy, self.lambda_sell)

    def get_directional_toxicity(self, action: str, t_query: Optional[float] = None) -> Dict[str, float]:
        """
        Evaluates directional toxicity metrics for a proposed action (BUY vs SELL).
        For BUY: adverse flow is aggressive selling (lambda_sell).
        For SELL: adverse flow is aggressive buying (lambda_buy).
        """
        t = t_query or time.time()
        with self._lock:
            dt = max(0.0, t - self.last_ts) if self.last_ts else 0.0
            decay = math.exp(-self.beta * dt)
            lam_b = self.mu_buy + max(0.0, self.lambda_buy - self.mu_buy) * decay
            lam_s = self.mu_sell + max(0.0, self.lambda_sell - self.mu_sell) * decay

            delta_dir = (lam_s - lam_b) / max(1e-6, lam_s + lam_b)
            is_buy = str(action).upper() in ["BUY", "BID", "LONG"]
            if is_buy:
                gamma = float(np.clip((lam_s - self.mu_sell) / (1.5 * self.mu_sell) + 0.35 * delta_dir, 0.0, 1.0))
            else:
                gamma = float(np.clip((lam_b - self.mu_buy) / (1.5 * self.mu_buy) - 0.50 * delta_dir, 0.0, 1.0))

            return {
                "lambda_buy": round(lam_b, 4),
                "lambda_sell": round(lam_s, 4),
                "delta_dir": round(delta_dir, 4),
                "gamma_toxic_dir": round(gamma, 4),
            }

    def get_arrival_imbalance(self, t_query: Optional[float] = None) -> Dict[str, float]:
        """
        Phase 7 (F50.2): Evaluates Bivariate Hawkes Arrival Intensity Imbalance Delta lambda_dir.
        Delta lambda_dir = (lambda_buy - lambda_sell) / max(1e-6, lambda_buy + lambda_sell) in [-1.0, 1.0].
        Branching ratio eta = (alpha_self + alpha_cross) / beta.
        """
        t = t_query or time.time()
        with self._lock:
            dt = max(0.0, t - self.last_ts) if self.last_ts else 0.0
            decay = math.exp(-self.beta * dt)
            lam_b = self.mu_buy + max(0.0, self.lambda_buy - self.mu_buy) * decay
            lam_s = self.mu_sell + max(0.0, self.lambda_sell - self.mu_sell) * decay
            tot = max(1e-6, lam_b + lam_s)
            delta_dir = float(np.clip((lam_b - lam_s) / tot, -1.0, 1.0))
            branching_ratio = float((self.alpha_self + self.alpha_cross) / max(1e-6, self.beta))
            return {
                "arrival_imbalance": round(delta_dir, 4),
                "lambda_total": round(lam_b + lam_s, 4),
                "branching_ratio": round(branching_ratio, 4),
                "lambda_buy": round(lam_b, 4),
                "lambda_sell": round(lam_s, 4),
            }


class MultivariateHawkesIntensity:
    """
    Phase 10 (F61.2): Multivariate Self- and Cross-Excited Hawkes Arrival Intensity Process.
    Tracks high-frequency arrival intensities across M venues (e.g., Lit, ATS, Dark) or buy/sell directions:
        lambda_m(t) = mu_m + sum_{n=1}^M int_0^t alpha_{mn} e^{-beta_{mn}(t - s)} dN_n(s)
    Recursive update upon event at venue n at time t:
        lambda_m(t) = mu_m + (lambda_m(t_{prev}) - mu_m) * exp(-beta_{mn} * dt) + alpha_{mn}
    """

    def __init__(
        self,
        mu: Optional[np.ndarray] = None,
        alpha: Optional[np.ndarray] = None,
        beta: Optional[Union[float, np.ndarray]] = None,
        num_venues: int = 3,
        venue_names: Optional[List[str]] = None,
    ):
        self.num_venues = int(num_venues)
        self.venue_names = (
            [str(v).upper() for v in venue_names]
            if venue_names
            else ["LIT", "ATS", "DARK"][: self.num_venues]
        )
        if len(self.venue_names) < self.num_venues:
            for i in range(len(self.venue_names), self.num_venues):
                self.venue_names.append(f"VENUE_{i}")

        # Baselines mu_m > 0
        if mu is not None:
            self.mu = np.asarray(mu, dtype=float).flatten()
        else:
            self.mu = np.array([1.0, 0.6, 0.3][: self.num_venues], dtype=float)
            if len(self.mu) < self.num_venues:
                self.mu = np.full(self.num_venues, 0.5)

        # Excitation matrix alpha_{mn} (impact of event in venue n on intensity of venue m)
        if alpha is not None:
            self.alpha = np.asarray(alpha, dtype=float)
        else:
            # Default: diagonal (self-excitation) 0.35, off-diagonal (cross-excitation) 0.12
            self.alpha = 0.12 * np.ones((self.num_venues, self.num_venues), dtype=float)
            np.fill_diagonal(self.alpha, 0.35)

        # Decay matrix beta_{mn} > 0
        if beta is not None:
            self.beta = np.asarray(beta, dtype=float)
            if self.beta.ndim == 0:
                self.beta = np.full((self.num_venues, self.num_venues), float(beta), dtype=float)
        else:
            self.beta = np.full((self.num_venues, self.num_venues), 1.25, dtype=float)

        self.last_ts: Optional[float] = None
        self.intensities = np.copy(self.mu)
        self._lock = threading.Lock()

    def update(self, venue: Union[int, str], timestamp_sec: Optional[float] = None) -> np.ndarray:
        """Updates arrival intensities upon an event at given venue."""
        t = float(timestamp_sec) if timestamp_sec is not None else time.time()
        v_idx = 0
        if isinstance(venue, str):
            v_str = str(venue).upper()
            if v_str in self.venue_names:
                v_idx = self.venue_names.index(v_str)
        else:
            v_idx = int(venue) % self.num_venues

        with self._lock:
            if self.last_ts is not None:
                dt = max(0.0, t - self.last_ts)
                decay = np.exp(-self.beta[:, v_idx] * dt)
                self.intensities = self.mu + np.maximum(0.0, self.intensities - self.mu) * decay

            # Add excitation from venue v_idx to all venues m
            self.intensities += self.alpha[:, v_idx]
            self.last_ts = t
            return np.copy(self.intensities)

    def get_intensity_at(self, t_query_sec: Optional[float] = None) -> np.ndarray:
        """Evaluates decaying arrival intensities without triggering an event."""
        t = float(t_query_sec) if t_query_sec is not None else time.time()
        with self._lock:
            if self.last_ts is None:
                return np.copy(self.mu)
            dt = max(0.0, t - self.last_ts)
            # Use mean decay across columns if last triggering venue not specified
            decay = np.exp(-np.mean(self.beta, axis=1) * dt)
            return self.mu + np.maximum(0.0, self.intensities - self.mu) * decay

    def get_intensity_dict(self, t_query_sec: Optional[float] = None) -> Dict[str, float]:
        """Returns mapping from venue name to current arrival intensity."""
        lam = self.get_intensity_at(t_query_sec)
        return {v: round(float(lam[i]), 4) for i, v in enumerate(self.venue_names)}

    def compute_cross_excitation_toxicity(self, proposed_venue: str = "ATS") -> Dict[str, float]:
        """Evaluates toxicity when routing to proposed_venue under cross-excitation from other venues."""
        pv = str(proposed_venue).upper()
        p_idx = self.venue_names.index(pv) if pv in self.venue_names else 0
        lam = self.get_intensity_at()

        # Cross-venue intensity from all venues except proposed_venue
        other_indices = [i for i in range(self.num_venues) if i != p_idx]
        cross_intensity = float(np.sum(lam[other_indices])) if other_indices else 0.0
        tot_intensity = float(np.sum(lam))

        tox_ratio = cross_intensity / max(1e-6, tot_intensity)
        return {
            "proposed_venue": pv,
            "venue_intensity": round(float(lam[p_idx]), 4),
            "cross_excitation_intensity": round(cross_intensity, 4),
            "total_intensity": round(tot_intensity, 4),
            "cross_excitation_toxicity": round(float(np.clip(tox_ratio, 0.0, 1.0)), 4),
        }


def compute_multivariate_hawkes_arrival_intensity(
    event_timestamps: np.ndarray,
    event_venues: Union[np.ndarray, List[str], List[int]],
    decay_beta: Optional[Union[float, np.ndarray]] = 1.2,
    alpha_matrix: Optional[np.ndarray] = None,
    mu_vector: Optional[np.ndarray] = None,
    query_timestamp: Optional[float] = None,
    venue_labels: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Phase 10 (F61.2): Evaluates batch Multivariate Hawkes Arrival Intensity Process.
    Supports multi-venue trade stream (e.g., LIT, ATS, DARK) and computes cross-excitation metrics.
    """
    ts = np.asarray(event_timestamps, dtype=float)
    labels = venue_labels or ["LIT", "ATS", "DARK"]
    M = len(labels)

    if ts.size == 0:
        mu_def = np.asarray(mu_vector, dtype=float) if mu_vector is not None else np.array([1.0, 0.6, 0.3][:M])
        return {
            "intensities": mu_def,
            "intensity_dict": {v: round(float(mu_def[i]), 4) for i, v in enumerate(labels)},
            "total_intensity": float(np.sum(mu_def)),
            "cross_excitation_toxicity": 0.0,
            "decay_rate": float(decay_beta) if isinstance(decay_beta, (int, float)) else 1.2,
        }

    model = MultivariateHawkesIntensity(
        mu=mu_vector,
        alpha=alpha_matrix,
        beta=decay_beta,
        num_venues=M,
        venue_names=labels,
    )

    # Sort events by timestamp
    venues_list = list(event_venues)
    sort_idx = np.argsort(ts)
    for idx in sort_idx:
        t_ev = float(ts[idx])
        v_ev = venues_list[idx]
        model.update(v_ev, timestamp_sec=t_ev)

    q_t = query_timestamp if query_timestamp is not None else float(ts[sort_idx[-1]])
    cur_intensities = model.get_intensity_at(q_t)
    int_dict = model.get_intensity_dict(q_t)
    tox_info = model.compute_cross_excitation_toxicity("ATS")

    return {
        "intensities": cur_intensities,
        "intensity_dict": int_dict,
        "total_intensity": round(float(np.sum(cur_intensities)), 4),
        "cross_excitation_toxicity": tox_info["cross_excitation_toxicity"],
        "decay_rate": float(decay_beta) if isinstance(decay_beta, (int, float)) else 1.2,
    }

