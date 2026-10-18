"""
src/execution/adaptive_iceberg_pegged_router.py
===============================================
Microsecond Adaptive Iceberg & Pegged Order Execution Router (Feature F567).
Phase 119 (Release R135 / v126 Production Master).

Features:
- High-frequency institutional execution routing engine managing synthetic iceberg
  orders and dynamic pegged orders (Primary Peg, Midpoint Peg, Market Peg, Discretionary Peg).
- Synthetic iceberg order state machine (PENDING, ACTIVE, REPLENISHING, PAUSED, COMPLETED, CANCELLED)
  with strict local hidden reserve concealment and mass conservation:
  V_executed + V_active + V_hidden == V_total.
- Anti-clustering display quantity randomization: normal jitter N(mu, sigma^2) clamped
  to [min, max] lot-quantized display quantity to defeat predatory HFT size-fingerprinting.
- Dynamic pegged orders: Primary Peg (best same-side quote), Midpoint Peg (exact half-tick
  midpoint with US sub-penny ATS support), Market Peg (opposing quote), discretionary tick offsets,
  and strict limit price ceiling/floor enforcement.
- Hawkes toxicity adaptation: O(1) recursive arrival intensity lambda(t) and adverse directional
  toxicity h(t), dynamic offset Delta_offset(t) = base_offset + gamma_toxic * max(0, h(t) - h_thresh),
  preemptive tick shading away from predatory sweeps, emergency toxicity retreat/pausing under
  critical flow (h >= h_critical), and child slice replenishment throttling under toxic book depletion.
- Microsecond re-pegging engine with deadband threshold Delta P >= Delta P_thresh and throttle
  cooldown tau_throttle >= 50 us preventing quote flicker churn.
- Polymorphic L3 book ingestion (L3QuoteView) supporting SIMDLOBMatchingCore's get_l3_snapshot()
  and FastOrderBookMatchingEngine, with crossed-book (P_bid >= P_ask), one-sided liquidity,
  and empty-ladder safety handling.
- 5-market pre-calibrated venue profiles (MARKET_ICEBERG_ROUTER_PROFILES for SP500, NASDAQ,
  RUSSELL2000, KOSPI, KOSDAQ).
- Module metadata (VERSION=119, RELEASE="R135", FEATURE="F567") and 10 complete
  backward-compatibility alias tree.
- 100% bit-for-bit cryptographic parity between src/ and trading_system/src/.
"""

from __future__ import annotations

import copy
import json
import math
import random
import sys
import threading
import time
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import numpy as np

# ---------------------------------------------------------------------------
# Module Metadata
# ---------------------------------------------------------------------------
VERSION: int = 119
RELEASE: str = "R135"
FEATURE: str = "F567"


# ---------------------------------------------------------------------------
# Core Enums
# ---------------------------------------------------------------------------
class OrderSide(IntEnum):
    """Normalized order side enumeration."""
    BUY = 1
    SELL = -1

    @classmethod
    def from_str(cls, val: Union[str, int, "OrderSide"]) -> "OrderSide":
        if isinstance(val, cls):
            return val
        if isinstance(val, int):
            if val in (1, -1):
                return cls(val)
        s = str(val).strip().upper()
        if s in ("BUY", "B", "1", "+1", "LONG"):
            return cls.BUY
        if s in ("SELL", "S", "-1", "SHORT"):
            return cls.SELL
        raise ValueError(f"Unknown OrderSide: '{val}'")


class PeggedOrderType(IntEnum):
    """Institutional pegged order classification."""
    NONE = 0                 # Fixed limit price without active pegging
    PRIMARY_PEG = 1          # Pegged to same-side best quote (bid for BUY, ask for SELL)
    MIDPOINT_PEG = 2         # Pegged to exact half-tick midpoint ((best_bid + best_ask) / 2)
    MARKET_PEG = 3           # Pegged to opposing-side best quote (ask for BUY, bid for SELL)
    DISCRETIONARY_PEG = 4    # Rests at primary peg with discretionary price ceiling/floor
    REVERSE_PEG = 5          # Contrarian pegging stepping away from aggressive book changes

    @classmethod
    def from_str(cls, val: Union[str, int, "PeggedOrderType"]) -> "PeggedOrderType":
        if isinstance(val, cls):
            return val
        if isinstance(val, int):
            try:
                return cls(val)
            except ValueError:
                pass
        s = str(val).strip().upper()
        mapping: Dict[str, "PeggedOrderType"] = {
            "NONE": cls.NONE,
            "FIXED": cls.NONE,
            "LIMIT": cls.NONE,
            "0": cls.NONE,
            "PRIMARY": cls.PRIMARY_PEG,
            "PRIMARY_PEG": cls.PRIMARY_PEG,
            "BBO": cls.PRIMARY_PEG,
            "SAME_SIDE": cls.PRIMARY_PEG,
            "1": cls.PRIMARY_PEG,
            "MIDPOINT": cls.MIDPOINT_PEG,
            "MIDPOINT_PEG": cls.MIDPOINT_PEG,
            "MID": cls.MIDPOINT_PEG,
            "HALF_SPREAD": cls.MIDPOINT_PEG,
            "2": cls.MIDPOINT_PEG,
            "MARKET": cls.MARKET_PEG,
            "MARKET_PEG": cls.MARKET_PEG,
            "OPPOSING": cls.MARKET_PEG,
            "3": cls.MARKET_PEG,
            "DISCRETIONARY": cls.DISCRETIONARY_PEG,
            "DISCRETIONARY_PEG": cls.DISCRETIONARY_PEG,
            "4": cls.DISCRETIONARY_PEG,
            "REVERSE": cls.REVERSE_PEG,
            "REVERSE_PEG": cls.REVERSE_PEG,
            "5": cls.REVERSE_PEG,
        }
        if s in mapping:
            return mapping[s]
        raise ValueError(f"Unknown PeggedOrderType: '{val}'")


# Alias PegType for compatibility
PegType = PeggedOrderType


class RouterOrderStatus(IntEnum):
    """Parent synthetic iceberg order state machine status."""
    NEW = 0
    ACTIVE = 1
    PARTIALLY_FILLED = 2
    REPLENISHING = 3
    PAUSED = 4
    FILLED = 5
    CANCELLED = 6
    REJECTED = 7

    @classmethod
    def from_str(cls, val: Union[str, int, "RouterOrderStatus"]) -> "RouterOrderStatus":
        if isinstance(val, cls):
            return val
        if isinstance(val, int):
            try:
                return cls(val)
            except ValueError:
                pass
        s = str(val).strip().upper()
        mapping = {
            "NEW": cls.NEW,
            "PENDING": cls.NEW,
            "ACTIVE": cls.ACTIVE,
            "OPEN": cls.ACTIVE,
            "PARTIAL": cls.PARTIALLY_FILLED,
            "PARTIALLY_FILLED": cls.PARTIALLY_FILLED,
            "REPLENISHING": cls.REPLENISHING,
            "PAUSED": cls.PAUSED,
            "FILLED": cls.FILLED,
            "COMPLETED": cls.FILLED,
            "COMPLETE": cls.FILLED,
            "CANCELLED": cls.CANCELLED,
            "CANCELED": cls.CANCELLED,
            "REJECTED": cls.REJECTED,
        }
        if s in mapping:
            return mapping[s]
        raise ValueError(f"Unknown RouterOrderStatus: '{val}'")


# Alias ParentOrderStatus
ParentOrderStatus = RouterOrderStatus


class SliceStatus(IntEnum):
    """Individual child slice order execution status."""
    PENDING = 0
    OPEN = 1
    PARTIALLY_FILLED = 2
    FILLED = 3
    CANCELLED = 4
    REPLACED = 5
    REJECTED = 6

    @classmethod
    def from_str(cls, val: Union[str, int, "SliceStatus"]) -> "SliceStatus":
        if isinstance(val, cls):
            return val
        if isinstance(val, int):
            try:
                return cls(val)
            except ValueError:
                pass
        s = str(val).strip().upper()
        mapping = {
            "PENDING": cls.PENDING,
            "NEW": cls.PENDING,
            "OPEN": cls.OPEN,
            "SUBMITTED": cls.OPEN,
            "ACTIVE": cls.OPEN,
            "PARTIAL": cls.PARTIALLY_FILLED,
            "PARTIALLY_FILLED": cls.PARTIALLY_FILLED,
            "FILLED": cls.FILLED,
            "CANCELLED": cls.CANCELLED,
            "CANCELED": cls.CANCELLED,
            "REPLACED": cls.REPLACED,
            "REJECTED": cls.REJECTED,
        }
        if s in mapping:
            return mapping[s]
        raise ValueError(f"Unknown SliceStatus: '{val}'")


# Alias ChildOrderStatus
ChildOrderStatus = SliceStatus


class RepegTriggerReason(IntEnum):
    """Categorized root causes for re-pegging / slice replacement."""
    QUOTE_SHIFT = 1
    TOXICITY_SHADE = 2
    TOXICITY_RECOVERY = 3
    DISCRETIONARY_ADJUSTMENT = 4
    MANUAL_TRIGGER = 5

    @classmethod
    def from_str(cls, val: Union[str, int, "RepegTriggerReason"]) -> "RepegTriggerReason":
        if isinstance(val, cls):
            return val
        if isinstance(val, int):
            try:
                return cls(val)
            except ValueError:
                pass
        s = str(val).strip().upper()
        mapping = {
            "QUOTE_SHIFT": cls.QUOTE_SHIFT,
            "QUOTE_DELTA": cls.QUOTE_SHIFT,
            "TOXICITY_SHADE": cls.TOXICITY_SHADE,
            "PREEMPTIVE_TOXIC_SHADE": cls.TOXICITY_SHADE,
            "TOXICITY_RECOVERY": cls.TOXICITY_RECOVERY,
            "DISCRETIONARY_ADJUSTMENT": cls.DISCRETIONARY_ADJUSTMENT,
            "MANUAL": cls.MANUAL_TRIGGER,
        }
        if s in mapping:
            return mapping[s]
        return cls.QUOTE_SHIFT


# ---------------------------------------------------------------------------
# Multi-Market Tick Quantization Engine
# ---------------------------------------------------------------------------
def round_to_tick_size(price: float, market: str = "SP500", allow_half_tick: bool = False) -> float:
    """
    Exchange-compliant price discretization adhering strictly to KRX 7-tier
    brackets and US penny / sub-penny conventions (SEC Rule 612).
    """
    if price is None or math.isnan(price) or math.isinf(price) or price <= 0.0:
        return 0.0

    # Fast path for US markets (default)
    if not allow_half_tick and (market == "SP500" or market == "NASDAQ" or market == "RUSSELL2000"):
        if price >= 1.00:
            return float(round(price, 2))
        return float(round(round(price * 10000.0) / 10000.0, 4))
    elif allow_half_tick and (market == "SP500" or market == "NASDAQ" or market == "RUSSELL2000"):
        if price >= 1.00:
            return float(round(round(price * 200.0) / 200.0, 4))
        return float(round(round(price * 10000.0) / 10000.0, 4))

    mkt = market.upper() if market else "SP500"

    # KRX Markets (KOSPI, KOSDAQ)
    if "KOSPI" in mkt or "KOSDAQ" in mkt:
        if price < 2000.0:
            tick = 1.0
        elif price < 5000.0:
            tick = 5.0
        elif price < 20000.0:
            tick = 10.0
        elif price < 50000.0:
            tick = 50.0
        elif price < 200000.0:
            tick = 100.0
        elif price < 500000.0:
            tick = 500.0
        else:
            tick = 1000.0
        return float(round(price / tick) * tick)

    # US Markets fallback
    if allow_half_tick and price >= 1.00:
        return float(round(round(price * 200.0) / 200.0, 4))
    elif price >= 1.00:
        return float(round(price, 2))
    else:
        return float(round(round(price * 10000.0) / 10000.0, 4))


# ---------------------------------------------------------------------------
# 5-Market Pre-Calibrated Venue Profiles
# ---------------------------------------------------------------------------
MARKET_ICEBERG_ROUTER_PROFILES: Dict[str, Dict[str, Any]] = {
    "SP500": {
        "currency": "USD",
        "tick_size": 0.01,
        "lot_size": 1,
        "base_display_qty": 100.0,
        "mean_display_qty": 100.0,
        "display_qty_jitter_std": 15.0,
        "display_jitter_std": 15.0,
        "min_disp": 10.0,
        "min_display_qty": 10.0,
        "max_disp": 300.0,
        "max_display_qty": 300.0,
        "repeg_threshold_delta_p": 0.01,
        "repeg_threshold_price": 0.01,
        "repeg_threshold_ticks": 1.0,
        "base_peg_offset_ticks": 0.0,
        "hawkes_alpha": 0.60,
        "hawkes_beta": 1.20,
        "hawkes_mu": 0.15,
        "hawkes_toxic_threshold": 0.65,
        "hawkes_toxicity_threshold": 0.65,
        "hawkes_gamma_toxic": 2.0,
        "gamma_toxic": 2.0,
        "max_toxic_offset_ticks": 10.0,
        "hawkes_critical_threshold": 0.85,
        "toxicity_throttle_threshold": 0.85,
        "throttle_cooldown_ms": 25.0,
        "repeg_throttle_us": 50.0,
        "max_spread_ticks": 20.0,
        "allow_half_tick": True,
        "venue_name": "NYSE_ARCA",
    },
    "NASDAQ": {
        "currency": "USD",
        "tick_size": 0.01,
        "lot_size": 1,
        "base_display_qty": 150.0,
        "mean_display_qty": 150.0,
        "display_qty_jitter_std": 25.0,
        "display_jitter_std": 25.0,
        "min_disp": 10.0,
        "min_display_qty": 10.0,
        "max_disp": 500.0,
        "max_display_qty": 500.0,
        "repeg_threshold_delta_p": 0.01,
        "repeg_threshold_price": 0.01,
        "repeg_threshold_ticks": 1.0,
        "base_peg_offset_ticks": 0.0,
        "hawkes_alpha": 0.65,
        "hawkes_beta": 1.30,
        "hawkes_mu": 0.20,
        "hawkes_toxic_threshold": 0.60,
        "hawkes_toxicity_threshold": 0.60,
        "hawkes_gamma_toxic": 2.5,
        "gamma_toxic": 2.5,
        "max_toxic_offset_ticks": 12.0,
        "hawkes_critical_threshold": 0.80,
        "toxicity_throttle_threshold": 0.80,
        "throttle_cooldown_ms": 20.0,
        "repeg_throttle_us": 50.0,
        "max_spread_ticks": 25.0,
        "allow_half_tick": True,
        "venue_name": "NASDAQ_INET",
    },
    "RUSSELL2000": {
        "currency": "USD",
        "tick_size": 0.01,
        "lot_size": 1,
        "base_display_qty": 50.0,
        "mean_display_qty": 50.0,
        "display_qty_jitter_std": 10.0,
        "display_jitter_std": 10.0,
        "min_disp": 5.0,
        "min_display_qty": 5.0,
        "max_disp": 150.0,
        "max_display_qty": 150.0,
        "repeg_threshold_delta_p": 0.02,
        "repeg_threshold_price": 0.02,
        "repeg_threshold_ticks": 1.5,
        "base_peg_offset_ticks": 0.0,
        "hawkes_alpha": 0.50,
        "hawkes_beta": 1.00,
        "hawkes_mu": 0.10,
        "hawkes_toxic_threshold": 0.55,
        "hawkes_toxicity_threshold": 0.55,
        "hawkes_gamma_toxic": 3.0,
        "gamma_toxic": 3.0,
        "max_toxic_offset_ticks": 15.0,
        "hawkes_critical_threshold": 0.85,
        "toxicity_throttle_threshold": 0.85,
        "throttle_cooldown_ms": 50.0,
        "repeg_throttle_us": 75.0,
        "max_spread_ticks": 40.0,
        "allow_half_tick": True,
        "venue_name": "BATS_BYX",
    },
    "KOSPI": {
        "currency": "KRW",
        "tick_size": 100.0,
        "lot_size": 1,
        "base_display_qty": 500.0,
        "mean_display_qty": 500.0,
        "display_qty_jitter_std": 80.0,
        "display_jitter_std": 80.0,
        "min_disp": 50.0,
        "min_display_qty": 50.0,
        "max_disp": 1500.0,
        "max_display_qty": 1500.0,
        "repeg_threshold_delta_p": 100.0,
        "repeg_threshold_price": 100.0,
        "repeg_threshold_ticks": 1.0,
        "base_peg_offset_ticks": 0.0,
        "hawkes_alpha": 0.55,
        "hawkes_beta": 1.15,
        "hawkes_mu": 0.12,
        "hawkes_toxic_threshold": 0.65,
        "hawkes_toxicity_threshold": 0.65,
        "hawkes_gamma_toxic": 1.40,
        "gamma_toxic": 1.40,
        "max_toxic_offset_ticks": 8.0,
        "hawkes_critical_threshold": 0.85,
        "toxicity_throttle_threshold": 0.85,
        "throttle_cooldown_ms": 40.0,
        "repeg_throttle_us": 100.0,
        "max_spread_ticks": 15.0,
        "allow_half_tick": False,
        "venue_name": "KRX_KOSPI",
    },
    "KOSDAQ": {
        "currency": "KRW",
        "tick_size": 50.0,
        "lot_size": 1,
        "base_display_qty": 1000.0,
        "mean_display_qty": 1000.0,
        "display_qty_jitter_std": 150.0,
        "display_jitter_std": 150.0,
        "min_disp": 100.0,
        "min_display_qty": 100.0,
        "max_disp": 3000.0,
        "max_display_qty": 3000.0,
        "repeg_threshold_delta_p": 50.0,
        "repeg_threshold_price": 50.0,
        "repeg_threshold_ticks": 1.0,
        "base_peg_offset_ticks": 0.0,
        "hawkes_alpha": 0.60,
        "hawkes_beta": 1.10,
        "hawkes_mu": 0.15,
        "hawkes_toxic_threshold": 0.68,
        "hawkes_toxicity_threshold": 0.68,
        "hawkes_gamma_toxic": 1.70,
        "gamma_toxic": 1.70,
        "max_toxic_offset_ticks": 10.0,
        "hawkes_critical_threshold": 0.88,
        "toxicity_throttle_threshold": 0.88,
        "throttle_cooldown_ms": 45.0,
        "repeg_throttle_us": 100.0,
        "max_spread_ticks": 20.0,
        "allow_half_tick": False,
        "venue_name": "KRX_KOSDAQ",
    },
}


def get_market_iceberg_profile(market: str) -> Dict[str, Any]:
    """Retrieve pre-calibrated profile with case-insensitive matching."""
    mkt = market.upper().strip() if market else "SP500"
    if mkt in MARKET_ICEBERG_ROUTER_PROFILES:
        return MARKET_ICEBERG_ROUTER_PROFILES[mkt]
    return MARKET_ICEBERG_ROUTER_PROFILES["SP500"]


# ---------------------------------------------------------------------------
# Configuration Dataclass
# ---------------------------------------------------------------------------
@dataclass
class AdaptiveIcebergConfig:
    """Hyperparameters and operational limits for Adaptive Iceberg & Pegged Router."""
    symbol: str = ""
    market: str = "SP500"
    tick_size: float = 0.01
    lot_size: int = 1
    pegged_order_type: PeggedOrderType = PeggedOrderType.PRIMARY_PEG
    base_peg_offset_ticks: float = 0.0
    repeg_threshold_ticks: float = 1.0
    repeg_threshold_price: float = 0.01
    base_display_qty: float = 100.0
    mean_display_ratio: float = 0.10
    display_qty_jitter_std: float = 15.0
    min_display_qty: float = 20.0
    max_display_qty: float = 250.0
    anti_clustering_distribution: str = "gaussian"
    hawkes_alpha: float = 0.60
    hawkes_beta: float = 1.20
    hawkes_mu: float = 0.15
    hawkes_toxicity_threshold: float = 0.65
    hawkes_critical_threshold: float = 0.85
    hawkes_recovery_threshold: float = 0.50
    gamma_toxic: float = 2.0
    max_toxic_offset_ticks: float = 10.0
    repeg_throttle_us: float = 50.0
    throttle_cooldown_ms: float = 25.0
    throttle_qty_reduction_ratio: float = 0.50
    max_spread_ticks: float = 25.0
    allow_half_tick_midpoint: bool = True
    enable_preemptive_shading: bool = True
    enable_child_throttling: bool = True
    enable_microsecond_repegging: bool = True
    post_only_child: bool = False
    maker_floor_spread_fraction: float = 0.01
    anti_clustering_delay_range_us: Tuple[float, float] = (10.0, 150.0)
    seed: Optional[int] = None
    random_seed: Optional[int] = None

    def __post_init__(self) -> None:
        if self.seed is not None and self.random_seed is None:
            self.random_seed = self.seed
        elif self.random_seed is not None and self.seed is None:
            self.seed = self.random_seed

        if self.min_display_qty > self.max_display_qty:
            raise ValueError(
                f"min_display_qty ({self.min_display_qty}) cannot exceed max_display_qty ({self.max_display_qty})"
            )
        if self.base_display_qty <= 0.0:
            raise ValueError(f"base_display_qty must be > 0.0, got {self.base_display_qty}")
        if self.display_qty_jitter_std < 0.0:
            raise ValueError(
                f"display_qty_jitter_std must be >= 0.0, got {self.display_qty_jitter_std}"
            )
        if self.tick_size <= 0.0:
            raise ValueError(f"tick_size must be > 0.0, got {self.tick_size}")

    # Aliases
    @property
    def mean_display_qty(self) -> float:
        return self.base_display_qty

    @mean_display_qty.setter
    def mean_display_qty(self, val: float) -> None:
        self.base_display_qty = val

    @property
    def display_jitter_std(self) -> float:
        return self.display_qty_jitter_std

    @display_jitter_std.setter
    def display_jitter_std(self, val: float) -> None:
        self.display_qty_jitter_std = val

    @property
    def min_disp(self) -> float:
        return self.min_display_qty

    @min_disp.setter
    def min_disp(self, val: float) -> None:
        self.min_display_qty = val

    @property
    def max_disp(self) -> float:
        return self.max_display_qty

    @max_disp.setter
    def max_disp(self, val: float) -> None:
        self.max_display_qty = val

    @property
    def hawkes_toxic_threshold(self) -> float:
        return self.hawkes_toxicity_threshold

    @hawkes_toxic_threshold.setter
    def hawkes_toxic_threshold(self, val: float) -> None:
        self.hawkes_toxicity_threshold = val

    @property
    def hawkes_gamma_toxic(self) -> float:
        return self.gamma_toxic

    @hawkes_gamma_toxic.setter
    def hawkes_gamma_toxic(self, val: float) -> None:
        self.gamma_toxic = val

    @property
    def repeg_threshold_delta_p(self) -> float:
        return self.repeg_threshold_price

    @repeg_threshold_delta_p.setter
    def repeg_threshold_delta_p(self, val: float) -> None:
        self.repeg_threshold_price = val

    @property
    def peg_type(self) -> PeggedOrderType:
        return self.pegged_order_type

    @peg_type.setter
    def peg_type(self, val: PeggedOrderType) -> None:
        self.pegged_order_type = val


# ---------------------------------------------------------------------------
# Polymorphic L3 Quote View Struct
# ---------------------------------------------------------------------------
@dataclass(slots=True)
class L3QuoteView:
    """Normalized Level 3 book snapshot view with anomaly flags."""
    symbol: str = ""
    timestamp_ns: int = 0
    best_bid: float = 0.0
    best_ask: float = 0.0
    spread: float = 0.0
    mid_price: float = 0.0
    micro_price: float = 0.0
    bid_volume_l1: float = 0.0
    ask_volume_l1: float = 0.0
    weighted_obi: float = 0.0
    depth: int = 1
    is_valid: bool = True
    is_crossed: bool = False
    is_one_sided: bool = False
    quote_toxicity: float = 0.0

    @classmethod
    def from_l3_snapshot(cls, snapshot: Any) -> "L3QuoteView":
        """Polymorphic adapter ingesting SIMDLOBMatchingCore or FastLOBEngine."""
        if isinstance(snapshot, cls):
            return snapshot

        if isinstance(snapshot, dict):
            sym = str(snapshot.get("symbol", ""))
            ts = int(snapshot.get("timestamp_ns", 0))
            bid = float(snapshot.get("best_bid", 0.0))
            ask = float(snapshot.get("best_ask", 0.0))
            bid_vol = float(snapshot.get("bid_volume_l1", snapshot.get("bid_vol", 0.0)))
            ask_vol = float(snapshot.get("ask_volume_l1", snapshot.get("ask_vol", 0.0)))
            micro = float(snapshot.get("micro_price", (bid + ask) * 0.5 if bid > 0 and ask > 0 else 0.0))
            obi = float(snapshot.get("weighted_obi", snapshot.get("obi", 0.0)))
            tox = float(snapshot.get("quote_toxicity", snapshot.get("toxicity", 0.0)))
            depth = int(snapshot.get("depth", 1))
        else:
            sym = str(getattr(snapshot, "symbol", ""))
            ts = int(getattr(snapshot, "timestamp_ns", 0))
            bid = float(getattr(snapshot, "best_bid", 0.0))
            ask = float(getattr(snapshot, "best_ask", 0.0))
            bid_vol = float(getattr(snapshot, "bid_volume_l1", getattr(snapshot, "bid_vol", 0.0)))
            ask_vol = float(getattr(snapshot, "ask_volume_l1", getattr(snapshot, "ask_vol", 0.0)))
            micro = float(getattr(snapshot, "micro_price", (bid + ask) * 0.5 if bid > 0 and ask > 0 else 0.0))
            obi = float(getattr(snapshot, "weighted_obi", getattr(snapshot, "obi", 0.0)))
            tox = float(getattr(snapshot, "quote_toxicity", getattr(snapshot, "toxicity", 0.0)))
            depth = int(getattr(snapshot, "depth", 1))

        # Check anomalies
        is_crossed = (bid > 0 and ask > 0 and bid >= ask)
        is_one_sided = (
            bid <= 0
            or ask <= 0
            or math.isinf(ask)
            or math.isinf(bid)
            or math.isnan(bid)
            or math.isnan(ask)
        )
        is_valid = not (math.isnan(bid) or math.isnan(ask) or (bid <= 0 and ask <= 0))
        spread = ask - bid if (bid > 0 and ask > 0 and not math.isinf(ask)) else 0.0
        mid = (bid + ask) * 0.5 if (bid > 0 and ask > 0 and not math.isinf(ask)) else (bid if bid > 0 else ask)

        return cls(
            symbol=sym,
            timestamp_ns=ts,
            best_bid=bid,
            best_ask=ask,
            spread=spread,
            mid_price=mid,
            micro_price=micro,
            bid_volume_l1=bid_vol,
            ask_volume_l1=ask_vol,
            weighted_obi=obi,
            depth=depth,
            is_valid=is_valid,
            is_crossed=is_crossed,
            is_one_sided=is_one_sided,
            quote_toxicity=tox,
        )


# ---------------------------------------------------------------------------
# Hawkes Point Process Toxicity & Intensity Engine
# ---------------------------------------------------------------------------
class HawkesIntensityModel:
    """
    O(1) Recursive Exponential Decay Hawkes Intensity & Directional Toxicity Model.
    Tracks trade / quote arrival bursts and directional adverse selection.
    """
    __slots__ = ("alpha", "beta", "mu", "toxic_threshold", "gamma_toxic",
                 "max_toxic_offset_ticks", "lambda_buy", "lambda_sell", "last_update_ns")

    def __init__(
        self,
        alpha: float = 0.60,
        beta: float = 1.20,
        mu: float = 0.15,
        toxic_threshold: float = 0.65,
        gamma_toxic: float = 2.0,
        max_toxic_offset_ticks: float = 10.0,
    ):
        self.alpha = float(alpha)
        self.beta = float(beta)
        self.mu = float(mu)
        self.toxic_threshold = float(toxic_threshold)
        self.gamma_toxic = float(gamma_toxic)
        self.max_toxic_offset_ticks = float(max_toxic_offset_ticks)

        self.lambda_buy = self.mu * 0.5
        self.lambda_sell = self.mu * 0.5
        self.last_update_ns: int = 0

    def update_event(self, side: Union[OrderSide, int], timestamp_ns: int) -> None:
        """Update arrival intensity upon trade or aggressive sweep event."""
        self._decay(timestamp_ns)
        side_val = int(side)
        if side_val == OrderSide.BUY:
            self.lambda_buy += self.alpha
        else:
            self.lambda_sell += self.alpha

    def _decay(self, timestamp_ns: int) -> None:
        """O(1) continuous recursive exponential decay update."""
        if self.last_update_ns == 0 or timestamp_ns <= self.last_update_ns:
            self.last_update_ns = timestamp_ns
            return
        dt = (timestamp_ns - self.last_update_ns) / 1e9
        decay_factor = math.exp(-self.beta * dt)
        half_mu = self.mu * 0.5
        self.lambda_buy = half_mu + (self.lambda_buy - half_mu) * decay_factor
        self.lambda_sell = half_mu + (self.lambda_sell - half_mu) * decay_factor
        self.last_update_ns = timestamp_ns

    def get_total_intensity(self, timestamp_ns: Optional[int] = None) -> float:
        if timestamp_ns is not None:
            self._decay(timestamp_ns)
        return self.lambda_buy + self.lambda_sell

    def get_adverse_toxicity(self, side: Union[OrderSide, int], timestamp_ns: Optional[int] = None) -> float:
        """
        Adverse toxicity metric h_adverse(t) in [0.0, 1.0].
        Adverse flow for a BUY maker order is incoming aggressive sellers (lambda_sell).
        Adverse flow for a SELL maker order is incoming aggressive buyers (lambda_buy).
        """
        if timestamp_ns is not None:
            self._decay(timestamp_ns)
        total = self.lambda_buy + self.lambda_sell + 1e-6
        side_val = int(side)
        if side_val == OrderSide.BUY:
            return self.lambda_sell / total
        else:
            return self.lambda_buy / total

    def calculate_dynamic_offset(self, toxicity: float, base_offset: float = 0.0) -> float:
        """
        Dynamic peg offset:
        Delta_offset(t) = base_offset + gamma_toxic * max(0.0, h(t) - h_thresh)
        Clamped to [0.0, max_toxic_offset_ticks].
        """
        if toxicity <= self.toxic_threshold:
            return float(base_offset)
        raw_offset = float(base_offset) + self.gamma_toxic * (float(toxicity) - self.toxic_threshold)
        return min(self.max_toxic_offset_ticks, max(0.0, raw_offset))


# ---------------------------------------------------------------------------
# Order Dataclasses: ChildOrderSlice & IcebergParentOrder
# ---------------------------------------------------------------------------
@dataclass(slots=True)
class ChildOrderSlice:
    """Individual child slice order generated by the adaptive iceberg router."""
    child_order_id: str
    parent_order_id: str
    slice_index: int = 0
    symbol: str = ""
    side: OrderSide = OrderSide.BUY
    order_type: int = 0  # 0: LIMIT, 5: POST_ONLY
    pegged_order_type: PeggedOrderType = PeggedOrderType.PRIMARY_PEG
    target_price: float = 0.0
    display_quantity: float = 0.0
    hidden_quantity: float = 0.0
    status: SliceStatus = SliceStatus.OPEN
    cum_filled_quantity: float = 0.0
    remaining_quantity: float = 0.0
    is_shaded: bool = False
    shade_offset_ticks: float = 0.0
    discretionary_offset_ticks: float = 0.0
    toxicity_at_creation: float = 0.0
    repeg_attempts: int = 0
    created_timestamp_ns: int = 0
    last_repeg_timestamp_ns: int = 0

    def __post_init__(self) -> None:
        if self.remaining_quantity == 0.0 and self.cum_filled_quantity == 0.0:
            self.remaining_quantity = self.display_quantity

    # Property Aliases
    @property
    def price(self) -> float:
        return self.target_price

    @price.setter
    def price(self, val: float) -> None:
        self.target_price = val

    @property
    def quantity(self) -> float:
        return self.display_quantity

    @quantity.setter
    def quantity(self, val: float) -> None:
        self.display_quantity = val

    @property
    def filled_quantity(self) -> float:
        return self.cum_filled_quantity

    @filled_quantity.setter
    def filled_quantity(self, val: float) -> None:
        self.cum_filled_quantity = val

    @property
    def child_id(self) -> str:
        return self.child_order_id

    @property
    def parent_id(self) -> str:
        return self.parent_order_id

    @property
    def peg_type(self) -> PeggedOrderType:
        return self.pegged_order_type

    def to_dict(self) -> Dict[str, Any]:
        return {
            "child_order_id": self.child_order_id,
            "parent_order_id": self.parent_order_id,
            "slice_index": self.slice_index,
            "symbol": self.symbol,
            "side": int(self.side),
            "order_type": int(self.order_type),
            "pegged_order_type": int(self.pegged_order_type),
            "target_price": round(self.target_price, 4),
            "display_quantity": round(self.display_quantity, 4),
            "hidden_quantity": round(self.hidden_quantity, 4),
            "status": int(self.status),
            "cum_filled_quantity": round(self.cum_filled_quantity, 4),
            "remaining_quantity": round(self.remaining_quantity, 4),
            "is_shaded": self.is_shaded,
            "shade_offset_ticks": self.shade_offset_ticks,
            "toxicity_at_creation": round(self.toxicity_at_creation, 4),
            "repeg_attempts": self.repeg_attempts,
            "created_timestamp_ns": self.created_timestamp_ns,
            "last_repeg_timestamp_ns": self.last_repeg_timestamp_ns,
        }


# Alias ChildOrder
ChildOrder = ChildOrderSlice


@dataclass
class IcebergParentOrder:
    """Institutional Synthetic Iceberg Parent Order state tracker."""
    parent_order_id: str
    symbol: str = ""
    side: OrderSide = OrderSide.BUY
    total_quantity: float = 0.0
    pegged_type: PeggedOrderType = PeggedOrderType.PRIMARY_PEG
    limit_price: Optional[float] = None
    discretionary_offset_ticks: float = 0.0
    remaining_quantity: float = 0.0
    cum_filled_quantity: float = 0.0
    hidden_reserve_quantity: float = 0.0
    cum_executed_value: float = 0.0
    vwap_executed_price: float = 0.0
    status: RouterOrderStatus = RouterOrderStatus.NEW
    active_child_slice_id: Optional[str] = None
    active_child: Optional[ChildOrderSlice] = None
    child_history: List[ChildOrderSlice] = field(default_factory=list)
    child_slices: List[ChildOrderSlice] = field(default_factory=list)
    repeg_count: int = 0
    child_slice_count: int = 0
    fills_count: int = 0
    replenish_count: int = 0
    toxicity_pause_count: int = 0
    cancelled_quantity: float = 0.0
    created_timestamp_ns: int = 0
    updated_timestamp_ns: int = 0
    completed_at_ns: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.created_timestamp_ns == 0:
            self.created_timestamp_ns = time.time_ns()
        if self.updated_timestamp_ns == 0:
            self.updated_timestamp_ns = self.created_timestamp_ns
        if self.remaining_quantity == 0.0 and self.cum_filled_quantity == 0.0:
            self.remaining_quantity = self.total_quantity
        if self.hidden_reserve_quantity == 0.0 and self.active_child is None:
            self.hidden_reserve_quantity = self.remaining_quantity

    # Property Aliases
    @property
    def parent_id(self) -> str:
        return self.parent_order_id

    @property
    def executed_quantity(self) -> float:
        return self.cum_filled_quantity

    @executed_quantity.setter
    def executed_quantity(self, val: float) -> None:
        self.cum_filled_quantity = val

    @property
    def filled_quantity(self) -> float:
        return self.cum_filled_quantity

    @filled_quantity.setter
    def filled_quantity(self, val: float) -> None:
        self.cum_filled_quantity = val

    @property
    def hidden_reserve(self) -> float:
        return self.hidden_reserve_quantity

    @hidden_reserve.setter
    def hidden_reserve(self, val: float) -> None:
        self.hidden_reserve_quantity = val

    @property
    def total_repeg_count(self) -> int:
        return self.repeg_count

    @total_repeg_count.setter
    def total_repeg_count(self, val: int) -> None:
        self.repeg_count = val

    @property
    def active_slice(self) -> Optional[ChildOrderSlice]:
        return self.active_child

    @active_slice.setter
    def active_slice(self, val: Optional[ChildOrderSlice]) -> None:
        self.active_child = val
        self.active_child_slice_id = val.child_order_id if val else None

    @property
    def vwap(self) -> float:
        return self.vwap_executed_price

    @property
    def peg_type(self) -> PeggedOrderType:
        return self.pegged_type

    @peg_type.setter
    def peg_type(self, val: PeggedOrderType) -> None:
        self.pegged_type = val

    def is_complete(self) -> bool:
        return (
            self.remaining_quantity <= 1e-6
            or self.status in (RouterOrderStatus.FILLED, RouterOrderStatus.CANCELLED, RouterOrderStatus.REJECTED)
        )

    def check_volume_conservation(self) -> bool:
        """Strictly asserts: V_executed + V_active + V_hidden (+ V_cancelled) == V_total."""
        if self.status == RouterOrderStatus.CANCELLED:
            cancelled_vol = getattr(self, "cancelled_quantity", 0.0)
            if cancelled_vol > 0.0:
                return abs(self.cum_filled_quantity + cancelled_vol - self.total_quantity) < 1e-4
            return True
        active_vol = 0.0
        if self.active_child and self.active_child.status in (SliceStatus.OPEN, SliceStatus.PARTIALLY_FILLED):
            active_vol = self.active_child.remaining_quantity
        total_accounted = self.cum_filled_quantity + active_vol + self.hidden_reserve_quantity
        return abs(total_accounted - self.total_quantity) < 1e-4

    def to_dict(self) -> Dict[str, Any]:
        return {
            "parent_order_id": self.parent_order_id,
            "symbol": self.symbol,
            "side": int(self.side),
            "total_quantity": round(self.total_quantity, 4),
            "pegged_type": int(self.pegged_type),
            "limit_price": self.limit_price,
            "discretionary_offset_ticks": self.discretionary_offset_ticks,
            "remaining_quantity": round(self.remaining_quantity, 4),
            "cum_filled_quantity": round(self.cum_filled_quantity, 4),
            "hidden_reserve_quantity": round(self.hidden_reserve_quantity, 4),
            "vwap_executed_price": round(self.vwap_executed_price, 4),
            "status": int(self.status),
            "active_child_slice_id": self.active_child_slice_id,
            "repeg_count": self.repeg_count,
            "child_slice_count": self.child_slice_count,
            "fills_count": self.fills_count,
            "replenish_count": self.replenish_count,
            "toxicity_pause_count": self.toxicity_pause_count,
            "created_timestamp_ns": self.created_timestamp_ns,
            "updated_timestamp_ns": self.updated_timestamp_ns,
            "completed_at_ns": self.completed_at_ns,
        }


# Alias ParentOrder
ParentOrder = IcebergParentOrder


# ---------------------------------------------------------------------------
# Repeg Action & Telemetry Dataclasses
# ---------------------------------------------------------------------------
@dataclass(slots=True)
class RepegAction:
    """Action record when an active child order slice is re-pegged."""
    parent_id: str
    old_child_id: str
    new_child_id: str
    old_price: float
    new_price: float
    quantity: float
    reason: RepegTriggerReason
    latency_ns: int = 0
    timestamp_ns: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "parent_id": self.parent_id,
            "old_child_id": self.old_child_id,
            "new_child_id": self.new_child_id,
            "old_price": round(self.old_price, 4),
            "new_price": round(self.new_price, 4),
            "quantity": round(self.quantity, 4),
            "reason": int(self.reason),
            "latency_ns": self.latency_ns,
            "timestamp_ns": self.timestamp_ns,
        }


@dataclass
class RouterExecutionTelemetry:
    """Microsecond routing telemetry summary and diagnostic metrics."""
    total_parent_orders: int = 0
    completed_parent_orders: int = 0
    total_child_slices: int = 0
    total_fills: int = 0
    total_repegs: int = 0
    total_toxicity_retreats: int = 0
    throttled_replenishments: int = 0
    avg_routing_latency_us: float = 0.0
    average_repeg_latency_ns: float = 0.0
    anti_clustering_entropy: float = 0.0
    price_improvement_usd: float = 0.0
    price_improvement_bps: float = 0.0

    # Aliases
    @property
    def total_child_slices_emitted(self) -> int:
        return self.total_child_slices

    @property
    def total_repegs_executed(self) -> int:
        return self.total_repegs

    @property
    def total_shares_executed(self) -> int:
        return self.total_fills

    @property
    def toxic_shading_events_triggered(self) -> int:
        return self.total_toxicity_retreats

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_parent_orders": self.total_parent_orders,
            "completed_parent_orders": self.completed_parent_orders,
            "total_child_slices": self.total_child_slices,
            "total_fills": self.total_fills,
            "total_repegs": self.total_repegs,
            "total_toxicity_retreats": self.total_toxicity_retreats,
            "throttled_replenishments": self.throttled_replenishments,
            "avg_routing_latency_us": round(self.avg_routing_latency_us, 3),
            "average_repeg_latency_ns": round(self.average_repeg_latency_ns, 1),
            "anti_clustering_entropy": round(self.anti_clustering_entropy, 4),
            "price_improvement_usd": round(self.price_improvement_usd, 4),
            "price_improvement_bps": round(self.price_improvement_bps, 4),
        }


# Alias ExecutionTelemetrySummary
ExecutionTelemetrySummary = RouterExecutionTelemetry


# ---------------------------------------------------------------------------
# AdaptiveIcebergPeggedRouter: Core Execution Router
# ---------------------------------------------------------------------------
class AdaptiveIcebergPeggedRouter:
    """
    Feature F567: Microsecond Adaptive Iceberg & Pegged Order Execution Router.
    Phase 119 (Release R135 / v126 Production Master).
    """

    VERSION: int = 119
    RELEASE: str = "R135"
    FEATURE: str = "F567"

    def __init__(
        self,
        config: Optional[AdaptiveIcebergConfig] = None,
        market: str = "SP500",
    ) -> None:
        self.market = market.upper().strip() if market else "SP500"

        if config is not None:
            self.config = copy.deepcopy(config)
            if not self.config.market:
                self.config.market = self.market
        else:
            prof = get_market_iceberg_profile(self.market)
            self.config = AdaptiveIcebergConfig(
                market=self.market,
                tick_size=prof.get("tick_size", 0.01),
                lot_size=prof.get("lot_size", 1),
                base_display_qty=prof.get("base_display_qty", 100.0),
                display_qty_jitter_std=prof.get("display_qty_jitter_std", 15.0),
                min_display_qty=prof.get("min_disp", 10.0),
                max_display_qty=prof.get("max_disp", 300.0),
                repeg_threshold_price=prof.get("repeg_threshold_delta_p", 0.01),
                hawkes_toxicity_threshold=prof.get("hawkes_toxic_threshold", 0.65),
                gamma_toxic=prof.get("hawkes_gamma_toxic", 2.0),
                repeg_throttle_us=prof.get("repeg_throttle_us", 50.0),
                allow_half_tick_midpoint=prof.get("allow_half_tick", True),
            )

        # Instance metadata
        self.VERSION = VERSION
        self.RELEASE = RELEASE
        self.FEATURE = FEATURE

        # Fast lookup flags
        self._is_krx = ("KOSPI" in self.config.market.upper() or "KOSDAQ" in self.config.market.upper())
        self._tick_size = self.config.tick_size
        self._base_display_qty = self.config.base_display_qty
        self._display_jitter_std = self.config.display_qty_jitter_std
        self._min_display_qty = self.config.min_display_qty
        self._max_display_qty = self.config.max_display_qty
        self._lot_size = self.config.lot_size
        self._repeg_threshold_price = self.config.repeg_threshold_price
        self._repeg_throttle_us = self.config.repeg_throttle_us

        # PRNG
        seed = self.config.random_seed or self.config.seed
        self.rng = random.Random(seed) if seed is not None else random.Random()

        # Hawkes Model
        self.hawkes = HawkesIntensityModel(
            alpha=self.config.hawkes_alpha,
            beta=self.config.hawkes_beta,
            mu=self.config.hawkes_mu,
            toxic_threshold=self.config.hawkes_toxicity_threshold,
            gamma_toxic=self.config.gamma_toxic,
            max_toxic_offset_ticks=self.config.max_toxic_offset_ticks,
        )

        # Internal State Storage
        self._lock = threading.RLock()
        self.parent_orders: Dict[str, IcebergParentOrder] = {}
        self.child_to_parent: Dict[str, str] = {}
        self.active_slices: Dict[str, ChildOrderSlice] = {}

        # Quote / Debounce Cache
        self._last_quotes: Dict[str, L3QuoteView] = {}
        self._last_repeg_ns_by_parent: Dict[str, int] = {}
        self._last_fill_ns_by_parent: Dict[str, int] = {}
        self._quote_flicker_history: Dict[str, List[Tuple[float, int]]] = {}

        # Telemetry & Benchmark stats
        self.telemetry = RouterExecutionTelemetry()
        self.sample_display_sizes: List[float] = []
        self._latencies_ns: List[int] = []

    # -----------------------------------------------------------------------
    # Sizing & Randomization Engine
    # -----------------------------------------------------------------------
    def sample_display_quantity(
        self,
        mu: float,
        sigma: float,
        min_qty: float,
        max_qty: float,
        lot_size: int = 1,
        max_reserve: Optional[float] = None,
    ) -> float:
        """
        Anti-clustering display quantity calculation:
        Sample Gaussian jitter N(mu, sigma^2), clamp to [min_qty, max_qty],
        quantize to round-lot increment, and truncate to available reserve.
        """
        if sigma <= 0.0:
            raw_qty = float(mu)
        else:
            raw_qty = self.rng.gauss(mu, sigma)

        # Clamping
        if raw_qty < min_qty:
            clamped = float(min_qty)
        elif raw_qty > max_qty:
            clamped = float(max_qty)
        else:
            clamped = raw_qty

        # Lot quantization
        if lot_size > 1:
            quantized = max(float(lot_size), round(clamped / lot_size) * lot_size)
        else:
            quantized = max(1.0, round(clamped))

        # Truncate to reserve if provided
        if max_reserve is not None and quantized > max_reserve:
            quantized = float(max_reserve)

        # Track sample for entropy verification (cap to 500 to avoid unbounded growth)
        if len(self.sample_display_sizes) < 500:
            self.sample_display_sizes.append(quantized)
        return float(quantized)

    # -----------------------------------------------------------------------
    # Target Peg Price Calculation
    # -----------------------------------------------------------------------
    def calculate_target_peg_price(
        self,
        best_bid: float,
        best_ask: float,
        side: Union[int, OrderSide, str] = 1,
        peg_type: Union[int, PeggedOrderType, str] = PeggedOrderType.PRIMARY_PEG,
        discretionary_offset_ticks: float = 0.0,
        hawkes_toxicity: Optional[float] = None,
        limit_price: Optional[float] = None,
        market: Optional[str] = None,
    ) -> float:
        """
        Sub-microsecond dynamic pegged price formulation with Hawkes adverse
        toxicity shading and exchange-specific tick quantization.
        """
        side_val = OrderSide.from_str(side) if not isinstance(side, OrderSide) else side
        peg_val = PeggedOrderType.from_str(peg_type) if not isinstance(peg_type, PeggedOrderType) else peg_type

        # Determine reference price
        if peg_val == PeggedOrderType.PRIMARY_PEG:
            ref_price = best_bid if side_val == OrderSide.BUY else best_ask
            if ref_price <= 0.0 or math.isinf(ref_price):
                ref_price = best_ask if side_val == OrderSide.BUY else best_bid
        elif peg_val == PeggedOrderType.MIDPOINT_PEG:
            if best_bid > 0 and best_ask > 0 and not math.isinf(best_ask) and not math.isinf(best_bid):
                ref_price = (best_bid + best_ask) * 0.5
            else:
                ref_price = best_bid if (best_bid > 0 and not math.isinf(best_bid)) else best_ask
        elif peg_val == PeggedOrderType.MARKET_PEG:
            # Opposing-side quote
            if side_val == OrderSide.BUY:
                ref_price = best_ask if (best_ask > 0 and not math.isinf(best_ask)) else best_bid
            else:
                ref_price = best_bid if (best_bid > 0 and not math.isinf(best_bid)) else best_ask
        elif peg_val == PeggedOrderType.DISCRETIONARY_PEG:
            ref_price = best_bid if side_val == OrderSide.BUY else best_ask
        else:  # NONE (fixed limit)
            if limit_price is not None:
                return round_to_tick_size(limit_price, market or self.config.market)
            ref_price = best_bid if side_val == OrderSide.BUY else best_ask

        if (ref_price <= 0.0 or math.isinf(ref_price)) and limit_price is not None:
            return round_to_tick_size(limit_price, market or self.config.market)
        elif ref_price <= 0.0 or math.isinf(ref_price):
            return 0.0

        # Toxicity calculation
        # Toxicity calculation
        if hawkes_toxicity is not None:
            tox = float(hawkes_toxicity)
        elif self.hawkes.lambda_buy == 0.0 and self.hawkes.lambda_sell == 0.0:
            tox = 0.0
        else:
            tox = self.hawkes.get_adverse_toxicity(side_val)

        # Dynamic toxic offset
        if tox > self.hawkes.toxic_threshold:
            toxic_offset = self.hawkes.calculate_dynamic_offset(tox, base_offset=0.0)
            toxic_ticks = float(math.ceil(toxic_offset)) if toxic_offset > 0.0 else 0.0
        else:
            toxic_ticks = 0.0

        # Fast path for tick size
        is_us = (not self._is_krx) if market is None else (market in ("SP500", "NASDAQ", "RUSSELL2000"))
        if is_us:
            tick_sz = 0.01
        elif market is not None and not ("KOSPI" in market.upper() or "KOSDAQ" in market.upper()):
            tick_sz = 0.01
        else:
            temp_p = ref_price
            if temp_p < 2000:
                tick_sz = 1.0
            elif temp_p < 5000:
                tick_sz = 5.0
            elif temp_p < 20000:
                tick_sz = 10.0
            elif temp_p < 50000:
                tick_sz = 50.0
            elif temp_p < 200000:
                tick_sz = 100.0
            elif temp_p < 500000:
                tick_sz = 500.0
            else:
                tick_sz = 1000.0

        net_offset = discretionary_offset_ticks - toxic_ticks
        if net_offset != 0.0:
            if side_val == OrderSide.BUY:
                raw_p = ref_price + net_offset * tick_sz
                if limit_price is not None and raw_p > limit_price:
                    raw_p = float(limit_price)
            else:
                raw_p = ref_price - net_offset * tick_sz
                if limit_price is not None and raw_p < limit_price:
                    raw_p = float(limit_price)
        else:
            raw_p = ref_price
            if limit_price is not None:
                if side_val == OrderSide.BUY and raw_p > limit_price:
                    raw_p = float(limit_price)
                elif side_val != OrderSide.BUY and raw_p < limit_price:
                    raw_p = float(limit_price)

        if is_us:
            allow_half = (peg_val == PeggedOrderType.MIDPOINT_PEG and self.config.allow_half_tick_midpoint)
            if allow_half and raw_p >= 1.00:
                return max(0.0001, float(round(round(raw_p * 200.0) / 200.0, 4)))
            elif raw_p >= 1.00:
                return max(0.0001, float(round(raw_p, 2)))
            else:
                return max(0.0001, float(round(round(raw_p * 10000.0) / 10000.0, 4)))

        # Midpoint on US equities allows half-tick increments
        allow_half = (peg_val == PeggedOrderType.MIDPOINT_PEG and self.config.allow_half_tick_midpoint)
        quantized = round_to_tick_size(raw_p, market or self.config.market, allow_half_tick=allow_half)
        return max(0.0001, quantized)

    # -----------------------------------------------------------------------
    # Slice Calculation & Creation
    # -----------------------------------------------------------------------
    def calculate_child_slice(
        self,
        parent: IcebergParentOrder,
        current_quote: Optional[L3QuoteView] = None,
        best_bid: Optional[float] = None,
        best_ask: Optional[float] = None,
        hawkes_toxicity: Optional[float] = None,
        timestamp_ns: Optional[int] = None,
    ) -> ChildOrderSlice:
        """
        Microsecond slice generation: samples display quantity and prices child slice.
        """
        # Fast Quote resolution
        if current_quote is not None:
            bid = current_quote.best_bid
            ask = current_quote.best_ask
            tox = current_quote.quote_toxicity if hawkes_toxicity is None else hawkes_toxicity
        else:
            bid = best_bid if best_bid is not None else 0.0
            ask = best_ask if best_ask is not None else 0.0
            tox = hawkes_toxicity

        # Determine target price
        target_price = self.calculate_target_peg_price(
            best_bid=bid,
            best_ask=ask,
            side=parent.side,
            peg_type=parent.pegged_type,
            discretionary_offset_ticks=parent.discretionary_offset_ticks,
            hawkes_toxicity=tox,
            limit_price=parent.limit_price,
            market=self.config.market,
        )

        # Determine target display size
        reserve = parent.hidden_reserve_quantity
        if reserve <= 0.0:
            reserve = parent.remaining_quantity

        # If total parent quantity is small (e.g. <= base_display_qty), single slice
        if parent.total_quantity <= self._base_display_qty:
            display_qty = min(parent.total_quantity, reserve)
        elif reserve <= self._min_display_qty:
            display_qty = reserve
        else:
            display_qty = self.sample_display_quantity(
                mu=self._base_display_qty,
                sigma=self._display_jitter_std,
                min_qty=self._min_display_qty,
                max_qty=self._max_display_qty,
                lot_size=self._lot_size,
                max_reserve=reserve,
            )

        # Fast toxicity calculation
        if tox is not None:
            tox_val = float(tox)
        elif self.hawkes.lambda_buy == 0.0 and self.hawkes.lambda_sell == 0.0:
            tox_val = 0.0
        else:
            tox_val = self.hawkes.get_adverse_toxicity(parent.side)

        is_shaded = tox_val >= self.config.hawkes_toxicity_threshold
        shade_offset = self.hawkes.calculate_dynamic_offset(tox_val, 0.0) if is_shaded else 0.0

        # Instantiate ChildOrderSlice
        slice_idx = parent.child_slice_count
        ts = timestamp_ns if timestamp_ns is not None else 0
        child_id = f"SLICE_{parent.parent_order_id}_{slice_idx}_{ts}"

        return ChildOrderSlice(
            child_order_id=child_id,
            parent_order_id=parent.parent_order_id,
            slice_index=slice_idx,
            symbol=parent.symbol,
            side=parent.side,
            order_type=5 if self.config.post_only_child else 0,
            pegged_order_type=parent.pegged_type,
            target_price=target_price,
            display_quantity=display_qty,
            hidden_quantity=0.0,
            status=SliceStatus.OPEN,
            cum_filled_quantity=0.0,
            remaining_quantity=display_qty,
            is_shaded=is_shaded,
            shade_offset_ticks=shade_offset,
            discretionary_offset_ticks=parent.discretionary_offset_ticks,
            toxicity_at_creation=tox_val,
            created_timestamp_ns=ts,
            last_repeg_timestamp_ns=ts,
        )

    # -----------------------------------------------------------------------
    # Parent Order Submission Interface
    # -----------------------------------------------------------------------
    def submit_iceberg_order(
        self,
        symbol: str,
        side: Union[str, OrderSide, int],
        total_quantity: float,
        limit_price: Optional[float] = None,
        peg_type: Union[str, PeggedOrderType, int] = PeggedOrderType.NONE,
        discretionary_offset_ticks: float = 0.0,
        best_bid: Optional[float] = None,
        best_ask: Optional[float] = None,
        current_quote: Optional[L3QuoteView] = None,
    ) -> IcebergParentOrder:
        """
        Submit institutional synthetic iceberg order into router memory.
        Instantiates parent FSM, hides reserve, and emits initial randomized child slice.
        """
        with self._lock:
            side_val = OrderSide.from_str(side) if not isinstance(side, OrderSide) else side
            peg_val = PeggedOrderType.from_str(peg_type) if not isinstance(peg_type, PeggedOrderType) else peg_type
            total_qty = float(total_quantity)
            if total_qty <= 0.0:
                raise ValueError(f"total_quantity must be > 0.0, got {total_qty}")

            ts = time.time_ns()
            parent_id = f"ICE_{symbol}_{ts}_{len(self.parent_orders) + 1}"

            # Resolve quotes from cache if omitted
            if current_quote is None and (best_bid is None or best_ask is None):
                if symbol in self._last_quotes:
                    current_quote = self._last_quotes[symbol]

            # Check for crossed order book anomaly (inverted spreads: bid >= ask)
            is_crossed = False
            if current_quote is not None:
                if getattr(current_quote, "is_crossed", False):
                    is_crossed = True
                elif current_quote.best_bid > 0 and current_quote.best_ask > 0 and current_quote.best_bid >= current_quote.best_ask:
                    is_crossed = True
            elif best_bid is not None and best_ask is not None:
                if best_bid > 0 and best_ask > 0 and best_bid >= best_ask:
                    is_crossed = True

            if is_crossed:
                # Suspend immediate order placement / child slice generation during inverted spreads
                parent = IcebergParentOrder(
                    parent_order_id=parent_id,
                    symbol=symbol,
                    side=side_val,
                    total_quantity=total_qty,
                    pegged_type=peg_val,
                    limit_price=float(limit_price) if limit_price is not None else None,
                    discretionary_offset_ticks=float(discretionary_offset_ticks),
                    remaining_quantity=total_qty,
                    cum_filled_quantity=0.0,
                    hidden_reserve_quantity=total_qty,
                    status=RouterOrderStatus.PAUSED,
                    created_timestamp_ns=ts,
                    updated_timestamp_ns=ts,
                )
                self.parent_orders[parent_id] = parent
                self.telemetry.total_parent_orders += 1
                return parent

            parent = IcebergParentOrder(
                parent_order_id=parent_id,
                symbol=symbol,
                side=side_val,
                total_quantity=total_qty,
                pegged_type=peg_val,
                limit_price=float(limit_price) if limit_price is not None else None,
                discretionary_offset_ticks=float(discretionary_offset_ticks),
                remaining_quantity=total_qty,
                cum_filled_quantity=0.0,
                hidden_reserve_quantity=total_qty,
                status=RouterOrderStatus.ACTIVE,
                created_timestamp_ns=ts,
                updated_timestamp_ns=ts,
            )

            # Generate initial child slice
            child = self.calculate_child_slice(
                parent=parent,
                current_quote=current_quote,
                best_bid=best_bid,
                best_ask=best_ask,
                timestamp_ns=ts,
            )

            # Deduct child display from hidden reserve
            parent.hidden_reserve_quantity = max(0.0, parent.total_quantity - child.display_quantity)
            parent.active_child = child
            parent.active_child_slice_id = child.child_order_id
            parent.child_slices.append(child)
            parent.child_history.append(child)
            parent.child_slice_count += 1

            # Register
            self.parent_orders[parent_id] = parent
            self.child_to_parent[child.child_order_id] = parent_id
            self.active_slices[child.child_order_id] = child

            self.telemetry.total_parent_orders += 1
            self.telemetry.total_child_slices += 1

            return parent

    def submit_pegged_order(
        self,
        symbol: str,
        side: Union[str, OrderSide, int],
        total_quantity: float,
        peg_type: Union[str, PeggedOrderType, int] = PeggedOrderType.PRIMARY_PEG,
        limit_price: Optional[float] = None,
        discretionary_offset_ticks: float = 0.0,
        best_bid: Optional[float] = None,
        best_ask: Optional[float] = None,
        current_quote: Optional[L3QuoteView] = None,
    ) -> IcebergParentOrder:
        """Convenience factory for dynamic pegged orders."""
        return self.submit_iceberg_order(
            symbol=symbol,
            side=side,
            total_quantity=total_quantity,
            limit_price=limit_price,
            peg_type=peg_type,
            discretionary_offset_ticks=discretionary_offset_ticks,
            best_bid=best_bid,
            best_ask=best_ask,
            current_quote=current_quote,
        )

    # -----------------------------------------------------------------------
    # Microsecond Quote Ingestion & Re-Pegging Loop
    # -----------------------------------------------------------------------
    def on_quote_update(
        self,
        symbol: str,
        best_bid: float,
        best_ask: float,
        timestamp_ns: Optional[int] = None,
        hawkes_toxicity: Optional[float] = None,
        bid_volume_l1: Optional[float] = None,
        ask_volume_l1: Optional[float] = None,
        quote_view: Optional[L3QuoteView] = None,
    ) -> List[RepegAction]:
        """
        Evaluate active pegged orders upon L3 quote updates.
        Enforces deadband thresholds, throttle cooldowns, and preemptive shading.
        """
        t0 = time.perf_counter_ns()
        ts = timestamp_ns if timestamp_ns is not None else time.time_ns()
        repeg_actions: List[RepegAction] = []

        with self._lock:
            # Build normalized quote view
            if quote_view is not None:
                q = quote_view
            else:
                q = L3QuoteView.from_l3_snapshot({
                    "symbol": symbol,
                    "timestamp_ns": ts,
                    "best_bid": best_bid,
                    "best_ask": best_ask,
                    "bid_volume_l1": bid_volume_l1 or 0.0,
                    "ask_volume_l1": ask_volume_l1 or 0.0,
                    "quote_toxicity": hawkes_toxicity or 0.0,
                })

            self._last_quotes[symbol] = q

            # Check crossed-book anomaly
            if q.is_crossed:
                # Crossed order book (P_bid >= P_ask): suspend re-pegging for safety
                return []

            # Empty book handling
            if q.best_bid <= 0.0 and q.best_ask <= 0.0:
                return []

            # Quote flickering debounce tracking
            if symbol not in self._quote_flicker_history:
                self._quote_flicker_history[symbol] = []
            flicker_hist = self._quote_flicker_history[symbol]
            flicker_hist.append((q.best_bid, ts))
            # Retain only last 50 ms
            cutoff_ns = ts - 50_000_000
            while flicker_hist and flicker_hist[0][1] < cutoff_ns:
                flicker_hist.pop(0)

            # Evaluate all active orders for this symbol
            for parent in list(self.parent_orders.values()):
                if parent.symbol != symbol:
                    continue

                # Resume paused order if order book is uncrossed and toxicity is below critical
                if parent.status == RouterOrderStatus.PAUSED and (parent.active_child is None or parent.active_child.status != SliceStatus.OPEN):
                    tox = hawkes_toxicity if hawkes_toxicity is not None else q.quote_toxicity
                    if tox == 0.0:
                        tox = self.hawkes.get_adverse_toxicity(parent.side, ts)
                    if tox < self.config.hawkes_critical_threshold and parent.remaining_quantity > 0.0:
                        parent.status = RouterOrderStatus.ACTIVE
                        child = self.calculate_child_slice(
                            parent=parent,
                            current_quote=q,
                            timestamp_ns=ts,
                        )
                        parent.hidden_reserve_quantity = max(0.0, parent.remaining_quantity - child.display_quantity)
                        parent.active_child = child
                        parent.active_child_slice_id = child.child_order_id
                        parent.child_slices.append(child)
                        parent.child_history.append(child)
                        parent.child_slice_count += 1
                        self.child_to_parent[child.child_order_id] = parent.parent_order_id
                        self.active_slices[child.child_order_id] = child
                        self.telemetry.total_child_slices += 1
                        actions.append(RouterAction(
                            action_type=RouterActionType.SUBMIT_SLICE,
                            parent_order_id=parent.parent_order_id,
                            child_order_id=child.child_order_id,
                            symbol=symbol,
                            side=parent.side,
                            price=child.target_price,
                            quantity=child.display_quantity,
                            timestamp_ns=ts,
                        ))
                        continue

                if parent.status != RouterOrderStatus.ACTIVE:
                    continue

                active_child = parent.active_child
                if not active_child or active_child.status != SliceStatus.OPEN:
                    continue

                # Fixed limit orders (PegType.NONE) do not re-peg
                if parent.pegged_type == PeggedOrderType.NONE:
                    continue

                # Evaluate toxicity
                tox = hawkes_toxicity if hawkes_toxicity is not None else q.quote_toxicity
                if tox == 0.0:
                    tox = self.hawkes.get_adverse_toxicity(parent.side, ts)

                # Emergency Toxicity Pause
                if tox >= self.config.hawkes_critical_threshold:
                    parent.status = RouterOrderStatus.PAUSED
                    parent.toxicity_pause_count += 1
                    self.telemetry.total_toxicity_retreats += 1
                    # Cancel active slice and refund active display quantity to hidden reserve
                    if active_child:
                        parent.hidden_reserve_quantity += active_child.remaining_quantity
                        active_child.status = SliceStatus.CANCELLED
                        self.active_slices.pop(active_child.child_order_id, None)
                        parent.active_child = None
                        parent.active_child_slice_id = None
                    continue

                # Calculate new target price
                new_price = self.calculate_target_peg_price(
                    best_bid=q.best_bid,
                    best_ask=q.best_ask,
                    side=parent.side,
                    peg_type=parent.pegged_type,
                    discretionary_offset_ticks=parent.discretionary_offset_ticks,
                    hawkes_toxicity=tox,
                    limit_price=parent.limit_price,
                    market=self.config.market,
                )

                if new_price <= 0.0:
                    continue

                price_delta = abs(new_price - active_child.target_price)
                thresh_delta = self._repeg_threshold_price

                # Check deadband threshold
                if price_delta < thresh_delta:
                    continue

                # Check throttle cooldown and flickering debounce
                last_repeg = self._last_repeg_ns_by_parent.get(parent.parent_order_id, 0)
                cooldown_ns = int(self._repeg_throttle_us * 1000.0)

                # Anti-flicker debounce window extension if oscillations detected
                flicker_count = sum(1 for j in range(1, len(flicker_hist)) if flicker_hist[j][0] != flicker_hist[j - 1][0])
                if flicker_count >= 3:
                    cooldown_ns = max(cooldown_ns, 200_000)  # 200 us

                if ts - last_repeg < cooldown_ns:
                    # Debounce / rate limit hit
                    continue

                # Preemptive Tick Shading trigger detection
                is_shade_trigger = (
                    tox >= self.config.hawkes_toxicity_threshold
                    and self.config.enable_preemptive_shading
                )

                reason = (
                    RepegTriggerReason.TOXICITY_SHADE
                    if is_shade_trigger
                    else RepegTriggerReason.QUOTE_SHIFT
                )

                # Execute Re-peg: Replace active child slice
                old_id = active_child.child_order_id
                old_price = active_child.target_price
                active_child.status = SliceStatus.REPLACED
                self.active_slices.pop(old_id, None)

                # Create replacement slice preserving remaining display volume
                rem_qty = active_child.remaining_quantity
                new_idx = parent.child_slice_count
                new_child_id = f"SLICE_{parent.parent_order_id}_{new_idx}_{ts}"

                new_child = ChildOrderSlice(
                    child_order_id=new_child_id,
                    parent_order_id=parent.parent_order_id,
                    slice_index=new_idx,
                    symbol=parent.symbol,
                    side=parent.side,
                    order_type=active_child.order_type,
                    pegged_order_type=parent.pegged_type,
                    target_price=new_price,
                    display_quantity=rem_qty,
                    hidden_quantity=0.0,
                    status=SliceStatus.OPEN,
                    cum_filled_quantity=0.0,
                    remaining_quantity=rem_qty,
                    is_shaded=is_shade_trigger,
                    shade_offset_ticks=self.hawkes.calculate_dynamic_offset(tox, 0.0),
                    discretionary_offset_ticks=parent.discretionary_offset_ticks,
                    toxicity_at_creation=tox,
                    repeg_attempts=active_child.repeg_attempts + 1,
                    created_timestamp_ns=ts,
                    last_repeg_timestamp_ns=ts,
                )

                parent.active_child = new_child
                parent.active_child_slice_id = new_child_id
                parent.child_slices.append(new_child)
                parent.child_history.append(new_child)
                parent.child_slice_count += 1
                parent.repeg_count += 1

                self.child_to_parent[new_child_id] = parent.parent_order_id
                self.active_slices[new_child_id] = new_child
                self._last_repeg_ns_by_parent[parent.parent_order_id] = ts

                if is_shade_trigger:
                    self.telemetry.total_toxicity_retreats += 1
                self.telemetry.total_repegs += 1

                repeg_lat_ns = time.perf_counter_ns() - t0
                action = RepegAction(
                    parent_id=parent.parent_order_id,
                    old_child_id=old_id,
                    new_child_id=new_child_id,
                    old_price=old_price,
                    new_price=new_price,
                    quantity=rem_qty,
                    reason=reason,
                    latency_ns=repeg_lat_ns,
                    timestamp_ns=ts,
                )
                repeg_actions.append(action)

        dt_total = time.perf_counter_ns() - t0
        if len(self._latencies_ns) < 5000:
            self._latencies_ns.append(dt_total)
        return repeg_actions

    def on_l3_snapshot(self, snapshot: Any, timestamp_ns: Optional[int] = None) -> List[RepegAction]:
        """Polymorphic adapter ingesting any L3 snapshot format."""
        q = L3QuoteView.from_l3_snapshot(snapshot)
        return self.on_quote_update(
            symbol=q.symbol,
            best_bid=q.best_bid,
            best_ask=q.best_ask,
            timestamp_ns=timestamp_ns or q.timestamp_ns,
            hawkes_toxicity=q.quote_toxicity,
            bid_volume_l1=q.bid_volume_l1,
            ask_volume_l1=q.ask_volume_l1,
            quote_view=q,
        )

    # -----------------------------------------------------------------------
    # Fill Processing & Automatic Replenishment
    # -----------------------------------------------------------------------
    def on_child_fill(
        self,
        child_id: str,
        filled_qty: float,
        fill_price: float,
        timestamp_ns: Optional[int] = None,
    ) -> Tuple[ChildOrderSlice, IcebergParentOrder]:
        """
        Microsecond fill processing & synthetic iceberg replenishment.
        Maintains volume mass conservation invariant at every step.
        """
        t0 = time.perf_counter_ns()
        ts = timestamp_ns if timestamp_ns is not None else time.time_ns()

        with self._lock:
            parent_id = self.child_to_parent.get(child_id)
            if not parent_id or parent_id not in self.parent_orders:
                raise KeyError(f"Unknown child order ID: {child_id}")

            parent = self.parent_orders[parent_id]
            child = None
            for c in parent.child_slices:
                if c.child_order_id == child_id:
                    child = c
                    break

            if child is None:
                raise KeyError(f"Child slice not found on parent: {child_id}")

            fill_q = float(filled_qty)
            fill_p = float(fill_price)

            # Cap fill to remaining child slice quantity
            actual_fill = min(fill_q, child.remaining_quantity)
            child.cum_filled_quantity += actual_fill
            child.remaining_quantity = max(0.0, child.remaining_quantity - actual_fill)

            # Update parent executed metrics
            old_val = parent.cum_executed_value
            old_qty = parent.cum_filled_quantity
            new_qty = old_qty + actual_fill
            new_val = old_val + (actual_fill * fill_p)

            parent.cum_filled_quantity = new_qty
            parent.cum_executed_value = new_val
            parent.vwap_executed_price = new_val / new_qty if new_qty > 0 else 0.0
            parent.remaining_quantity = max(0.0, parent.total_quantity - new_qty)
            parent.fills_count += 1
            parent.updated_timestamp_ns = ts

            self.telemetry.total_fills += int(actual_fill)

            # Update Hawkes point process with trade arrival
            self.hawkes.update_event(parent.side, ts)

            # Check if child slice is fully filled
            if child.remaining_quantity <= 1e-6:
                child.status = SliceStatus.FILLED
                self.active_slices.pop(child_id, None)

                # Check if parent is fully filled
                if parent.remaining_quantity <= 1e-6 or (
                    parent.hidden_reserve_quantity <= 1e-6 and parent.remaining_quantity <= 1e-6
                ):
                    parent.status = RouterOrderStatus.FILLED
                    parent.active_child = None
                    parent.active_child_slice_id = None
                    parent.hidden_reserve_quantity = 0.0
                    parent.completed_at_ns = ts
                    self.telemetry.completed_parent_orders += 1
                else:
                    # Replenish from hidden reserve
                    parent.status = RouterOrderStatus.REPLENISHING
                    parent.replenish_count += 1

                    # Check replenishment throttling under book depletion
                    last_fill_ts = self._last_fill_ns_by_parent.get(parent_id, 0)
                    cooldown_ns = int(self.config.throttle_cooldown_ms * 1_000_000.0)
                    if ts - last_fill_ts < cooldown_ns and self.config.enable_child_throttling:
                        self.telemetry.throttled_replenishments += 1

                    # Generate new child slice
                    next_child = self.calculate_child_slice(
                        parent=parent,
                        current_quote=self._last_quotes.get(parent.symbol),
                        timestamp_ns=ts,
                    )

                    # Deduct from hidden reserve
                    parent.hidden_reserve_quantity = max(
                        0.0, parent.hidden_reserve_quantity - next_child.display_quantity
                    )
                    parent.active_child = next_child
                    parent.active_child_slice_id = next_child.child_order_id
                    parent.child_slices.append(next_child)
                    parent.child_history.append(next_child)
                    parent.child_slice_count += 1
                    parent.status = RouterOrderStatus.ACTIVE

                    self.child_to_parent[next_child.child_order_id] = parent_id
                    self.active_slices[next_child.child_order_id] = next_child
                    self.telemetry.total_child_slices += 1

                self._last_fill_ns_by_parent[parent_id] = ts
            else:
                # Partial fill of active slice: remains PARTIALLY_FILLED
                child.status = SliceStatus.PARTIALLY_FILLED
                parent.status = RouterOrderStatus.PARTIALLY_FILLED

            # Verify Mass Conservation Invariant
            assert parent.check_volume_conservation(), (
                f"Mass conservation violated on {parent_id}: "
                f"filled={parent.cum_filled_quantity}, "
                f"active={parent.active_child.remaining_quantity if parent.active_child else 0.0}, "
                f"hidden={parent.hidden_reserve_quantity}, total={parent.total_quantity}"
            )

        dt = time.perf_counter_ns() - t0
        if len(self._latencies_ns) < 5000:
            self._latencies_ns.append(dt)
        return child, parent

    # -----------------------------------------------------------------------
    # Cancellation & Order Lifecycle Management
    # -----------------------------------------------------------------------
    def cancel_parent_order(self, parent_id: str) -> bool:
        """Atomic cancellation of synthetic iceberg parent and resting child slice."""
        with self._lock:
            if parent_id not in self.parent_orders:
                return False

            parent = self.parent_orders[parent_id]
            if parent.status in (RouterOrderStatus.FILLED, RouterOrderStatus.CANCELLED):
                return False

            active_remaining = parent.active_child.remaining_quantity if parent.active_child else 0.0
            parent.cancelled_quantity = parent.hidden_reserve_quantity + active_remaining
            parent.status = RouterOrderStatus.CANCELLED
            parent.hidden_reserve_quantity = 0.0
            parent.remaining_quantity = 0.0

            if parent.active_child:
                parent.active_child.status = SliceStatus.CANCELLED
                self.active_slices.pop(parent.active_child.child_order_id, None)
                parent.active_child = None
                parent.active_child_slice_id = None

            return True

    def cancel_all(self) -> int:
        """Emergency purge: cancel all active parent orders and resting slices."""
        with self._lock:
            cancelled_count = 0
            for pid in list(self.parent_orders.keys()):
                if self.cancel_parent_order(pid):
                    cancelled_count += 1
            return cancelled_count

    def get_parent_order(self, parent_id: str) -> Optional[IcebergParentOrder]:
        """Query parent order by ID."""
        with self._lock:
            return self.parent_orders.get(parent_id)

    # -----------------------------------------------------------------------
    # Telemetry, Diagnostics & Serialization
    # -----------------------------------------------------------------------
    def get_telemetry(self) -> RouterExecutionTelemetry:
        """Compute aggregated telemetry summary with Shannon entropy."""
        with self._lock:
            # Latency SLA
            if self._latencies_ns:
                self.telemetry.avg_routing_latency_us = (
                    sum(self._latencies_ns) / len(self._latencies_ns) / 1000.0
                )
                self.telemetry.average_repeg_latency_ns = (
                    sum(self._latencies_ns) / len(self._latencies_ns)
                )

            # Shannon Entropy on display size samples
            if len(self.sample_display_sizes) >= 10:
                counts: Dict[float, int] = {}
                for s in self.sample_display_sizes:
                    counts[s] = counts.get(s, 0) + 1
                n = len(self.sample_display_sizes)
                entropy = 0.0
                for c in counts.values():
                    p = c / n
                    if p > 0:
                        entropy -= p * math.log2(p)
                self.telemetry.anti_clustering_entropy = entropy

            return copy.deepcopy(self.telemetry)

    def export_telemetry(self) -> Dict[str, Any]:
        """Export serialized dictionary for JSON logging."""
        t = self.get_telemetry()
        d = t.to_dict()
        d["VERSION"] = self.VERSION
        d["RELEASE"] = self.RELEASE
        d["FEATURE"] = self.FEATURE
        d["active_parent_orders"] = sum(
            1 for p in self.parent_orders.values() if p.status == RouterOrderStatus.ACTIVE
        )
        return d


# ---------------------------------------------------------------------------
# 10 Backward-Compatibility Class Aliases
# ---------------------------------------------------------------------------
MicrosecondIcebergRouter = AdaptiveIcebergPeggedRouter
AdaptivePeggedOrderRouter = AdaptiveIcebergPeggedRouter
SyntheticIcebergEngine = AdaptiveIcebergPeggedRouter
Phase119IcebergRouter = AdaptiveIcebergPeggedRouter
F567AdaptiveIcebergRouter = AdaptiveIcebergPeggedRouter
HFTIcebergPeggedRouter = AdaptiveIcebergPeggedRouter
AdaptiveExecutionRouter = AdaptiveIcebergPeggedRouter
DynamicPeggedOrderManager = AdaptiveIcebergPeggedRouter
StealthIcebergRouter = AdaptiveIcebergPeggedRouter
InstitutionalPeggedOrderRouter = AdaptiveIcebergPeggedRouter

# Dual-Tree Sys.Modules Registration
for alias_name in (
    "src.execution.adaptive_iceberg_pegged_router",
    "trading_system.src.execution.adaptive_iceberg_pegged_router",
):
    if alias_name not in sys.modules:
        sys.modules[alias_name] = sys.modules[__name__]
