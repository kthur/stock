"""
intraday_toxicity_filter.py — Real-Time Microstructure Liquidity Toxicity Filter

Phase 110 (Release R126 / v117 Production Master, Feature F522)
Calculates continuous Volume-Synchronized Probability of Toxicity (VPIN) over standardized volume
buckets and multi-level Order Flow Imbalance (OFI) to detect informed order flow surges,
adverse selection threats, and pre-crash liquidity evaporation in sub-second intervals.
Integrates into OMS (Safety Gate 7.8) and SmartOrderRouter (quote shading & dark probing).
"""

from __future__ import annotations

import collections
from dataclasses import dataclass, field
import logging
import math
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np

logger = logging.getLogger(__name__)


def _norm_cdf(z: float) -> float:
    """Standard normal cumulative distribution function using math.erf."""
    if not math.isfinite(z):
        return 0.5
    return 0.5 * (1.0 + math.erf(z / 1.4142135623730951))


@dataclass
class VolumeBucket:
    """Continuous volume bucket tracking accumulated buy and sell volume."""
    bucket_id: int
    target_volume: float
    accumulated_volume: float = 0.0
    buy_volume: float = 0.0
    sell_volume: float = 0.0
    is_complete: bool = False
    start_timestamp: Optional[float] = None
    end_timestamp: Optional[float] = None

    @property
    def imbalance(self) -> float:
        """Absolute order flow imbalance within bucket."""
        return abs(self.buy_volume - self.sell_volume)


@dataclass
class ToxicityEvaluationResult:
    """Comprehensive microstructure liquidity toxicity evaluation result."""
    symbol: str
    vpin_score: float                     # [0.0, 1.0]
    ofi_score: float                      # [-1.0, 1.0]
    composite_toxicity: float             # [0.0, 1.0]
    is_toxic: bool                        # composite_toxicity >= threshold (0.70 standard, 0.65 small-cap)
    is_evaporating: bool                  # pre-crash liquidity evaporation detected (>= 0.85)
    quote_shade_offset_bps: float         # dynamic quote shading offset in basis points [0.0, 50.0]
    recommended_strategy: str             # "PASSIVE_LIMIT", "FAST_VWAP", "HALT_OR_DELAY", "NORMAL"
    slice_count_multiplier: float         # slice expansion / contraction multiplier
    order_side: str = "BUY"
    spread_bps: float = 5.0
    vpin_threshold: float = 0.70

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary representation."""
        return {
            "symbol": self.symbol,
            "vpin_score": round(self.vpin_score, 4),
            "ofi_score": round(self.ofi_score, 4),
            "composite_toxicity": round(self.composite_toxicity, 4),
            "is_toxic": self.is_toxic,
            "is_evaporating": self.is_evaporating,
            "quote_shade_offset_bps": round(self.quote_shade_offset_bps, 2),
            "recommended_strategy": self.recommended_strategy,
            "slice_count_multiplier": round(self.slice_count_multiplier, 2),
            "order_side": self.order_side,
            "spread_bps": round(self.spread_bps, 2),
            "vpin_threshold": round(self.vpin_threshold, 2),
        }

    def __getitem__(self, item: str) -> Any:
        """Dictionary-like item access."""
        return getattr(self, item)

    def get(self, item: str, default: Any = None) -> Any:
        """Dictionary-like get access."""
        return getattr(self, item, default)


class IntradayToxicityFilter:
    """
    Real-Time Microstructure Liquidity Toxicity (VPIN + OFI) Filter Engine.

    Features:
      1. Continuous Volume-Synchronized Probability of Toxicity (VPIN) over standardized volume buckets:
         V = max(100, ADV / N_buckets), with Bulk Volume Classification (BVC) via Gaussian CDF.
      2. Multi-Level Order Flow Imbalance (OFI) across depth levels m=1..M with exponential decay w_m = exp(-lambda*(m-1)).
      3. Composite Toxicity Metric:
         T = clip(0.55 * VPIN + 0.35 * AdverseDirection + 0.10 * min(1.0, Spread / Spread_baseline), 0.0, 1.0).
      4. Pre-Crash Liquidity Evaporation Detection:
         Depth < 0.20 * Baseline_Depth or Spread > 3 * Baseline_Spread -> T_evap = max(T, 0.88).
      5. Dynamic Quote Shading & Execution Modulation:
         quote_shade_offset_bps = clip((T - 0.50) * 2.0 * spread_bps, 0.0, 50.0).
         Modulates slice count and recommends execution strategy.
    """

    def __init__(
        self,
        bucket_volume: float = 1000.0,
        num_buckets: int = 50,
        depth_levels: int = 5,
        decay_lambda: float = 0.5,
        toxicity_threshold_standard: float = 0.70,
        toxicity_threshold_smallcap: float = 0.65,
        evaporation_threshold: float = 0.85,
        default_adv: float = 50000.0,
        baseline_spread_bps: float = 5.0,
        **kwargs: Any,
    ) -> None:
        self.default_bucket_volume = max(100.0, float(bucket_volume))
        self.num_buckets = max(5, int(num_buckets))
        self.depth_levels = max(1, int(depth_levels))
        self.decay_lambda = max(0.0, float(decay_lambda))
        self.toxicity_threshold_standard = float(toxicity_threshold_standard)
        self.toxicity_threshold_smallcap = float(toxicity_threshold_smallcap)
        self.evaporation_threshold = float(evaporation_threshold)
        self.default_adv = max(1000.0, float(default_adv))
        self.baseline_spread_bps = max(0.1, float(baseline_spread_bps))

        # Exponential weights for orderbook levels: w_m = exp(-lambda * (m - 1))
        self._level_weights = np.array(
            [math.exp(-self.decay_lambda * (m - 1)) for m in range(1, self.depth_levels + 1)],
            dtype=np.float64
        )

        # Per-symbol state tracking
        self._states: Dict[str, Dict[str, Any]] = {}

    def _get_or_create_symbol_state(self, symbol: str) -> Dict[str, Any]:
        """Retrieves or initializes internal state tracking for a specific symbol."""
        sym = str(symbol).strip().upper()
        if sym not in self._states:
            target_vol = max(100.0, self.default_bucket_volume)
            self._states[sym] = {
                "adv": self.default_adv,
                "bucket_volume": target_vol,
                "current_bucket": VolumeBucket(bucket_id=0, target_volume=target_vol),
                "completed_buckets": collections.deque(maxlen=self.num_buckets),
                "bucket_counter": 0,
                "last_trade_price": None,
                "price_diffs": collections.deque(maxlen=100),
                "last_bids": [],  # List[Tuple[float, float]] (price, volume)
                "last_asks": [],  # List[Tuple[float, float]] (price, volume)
                "latest_ofi": 0.0,
                "depth_history": collections.deque(maxlen=50),
                "spread_history": collections.deque(maxlen=50),
                "baseline_depth": 0.0,
                "baseline_spread_bps": self.baseline_spread_bps,
                "is_evaporating": False,
            }
        return self._states[sym]

    def set_symbol_adv(self, symbol: str, adv: float) -> None:
        """Sets symbol Average Daily Volume (ADV) and standardizes bucket size V = max(100, ADV / N_buckets)."""
        state = self._get_or_create_symbol_state(symbol)
        safe_adv = max(1000.0, float(adv))
        state["adv"] = safe_adv
        new_bucket_vol = max(100.0, safe_adv / float(self.num_buckets))
        state["bucket_volume"] = new_bucket_vol
        state["current_bucket"].target_volume = new_bucket_vol

    def reset(self, symbol: Optional[str] = None) -> None:
        """Resets state for a specific symbol or all symbols."""
        if symbol is not None:
            sym = str(symbol).strip().upper()
            if sym in self._states:
                del self._states[sym]
        else:
            self._states.clear()

    def update_trade(
        self,
        symbol: str,
        price: float,
        volume: float,
        timestamp: Optional[float] = None,
    ) -> Optional[VolumeBucket]:
        """
        Ingests a continuous trade tick and updates standardized volume buckets with Bulk Volume Classification.
        Returns the completed VolumeBucket if one was sealed during this trade tick, else None.
        """
        p = float(price)
        v = float(volume)
        if not math.isfinite(p) or p <= 0.0 or not math.isfinite(v) or v <= 0.0:
            return None

        state = self._get_or_create_symbol_state(symbol)
        last_px = state["last_trade_price"]

        if last_px is None:
            state["last_trade_price"] = p
            delta_p = 0.0
        else:
            delta_p = p - last_px
            state["price_diffs"].append(delta_p)
            state["last_trade_price"] = p

        # Estimate rolling price change volatility
        if len(state["price_diffs"]) >= 2:
            arr_diffs = np.asarray(state["price_diffs"], dtype=np.float64)
            sigma = float(np.std(arr_diffs))
        else:
            sigma = max(0.0005 * p, 1e-4)

        if not math.isfinite(sigma) or sigma < 1e-6:
            sigma = max(0.0005 * p, 1e-4)

        # Bulk Volume Classification (BVC) via Gaussian CDF
        z_score = float(np.clip(delta_p / sigma, -8.0, 8.0))
        buy_ratio = _norm_cdf(z_score)
        sell_ratio = 1.0 - buy_ratio

        # Volume Bucketing Accumulation across continuous volume buckets
        v_rem = v
        last_completed: Optional[VolumeBucket] = None

        while v_rem > 0:
            cur_bucket = state["current_bucket"]
            if cur_bucket.start_timestamp is None:
                cur_bucket.start_timestamp = timestamp

            needed = cur_bucket.target_volume - cur_bucket.accumulated_volume

            if v_rem < needed:
                cur_bucket.buy_volume += v_rem * buy_ratio
                cur_bucket.sell_volume += v_rem * sell_ratio
                cur_bucket.accumulated_volume += v_rem
                v_rem = 0.0
            else:
                cur_bucket.buy_volume += needed * buy_ratio
                cur_bucket.sell_volume += needed * sell_ratio
                cur_bucket.accumulated_volume = cur_bucket.target_volume
                cur_bucket.is_complete = True
                cur_bucket.end_timestamp = timestamp

                state["completed_buckets"].append(cur_bucket)
                last_completed = cur_bucket

                state["bucket_counter"] += 1
                state["current_bucket"] = VolumeBucket(
                    bucket_id=state["bucket_counter"],
                    target_volume=state["bucket_volume"],
                    start_timestamp=timestamp,
                )
                v_rem -= needed

        return last_completed

    def _normalize_book_side(self, side_data: Any) -> List[Tuple[float, float]]:
        """Normalizes orderbook bids or asks into a list of (price, volume) tuples."""
        out: List[Tuple[float, float]] = []
        if not side_data:
            return out

        for item in side_data:
            try:
                if isinstance(item, (list, tuple)) and len(item) >= 2:
                    px = float(item[0])
                    sz = max(0.0, float(item[1]))
                elif isinstance(item, dict):
                    px = float(item.get("price", item.get("px", 0.0)))
                    sz = max(0.0, float(item.get("volume", item.get("size", item.get("vol", item.get("qty", 0.0))))))
                else:
                    continue
                if math.isfinite(px) and px > 0.0 and math.isfinite(sz) and sz >= 0.0:
                    out.append((px, sz))
            except (ValueError, TypeError):
                continue
        return out

    def update_orderbook(
        self,
        symbol: str,
        bids: Any,
        asks: Any,
        timestamp: Optional[float] = None,
    ) -> float:
        """
        Ingests orderbook snapshots and computes multi-level Order Flow Imbalance (OFI).
        Also monitors book depth and spread to identify pre-crash liquidity evaporation.
        Returns the latest normalized OFI score in [-1.0, 1.0].
        """
        state = self._get_or_create_symbol_state(symbol)

        norm_bids = self._normalize_book_side(bids)
        norm_asks = self._normalize_book_side(asks)

        # Sort bids descending, asks ascending
        norm_bids.sort(key=lambda x: x[0], reverse=True)
        norm_asks.sort(key=lambda x: x[0])

        m_levels = min(len(norm_bids), len(norm_asks), self.depth_levels)
        if m_levels == 0:
            return state["latest_ofi"]

        curr_bids = norm_bids[:m_levels]
        curr_asks = norm_asks[:m_levels]
        prev_bids = state["last_bids"]
        prev_asks = state["last_asks"]

        level_ofis = []
        level_vols = []

        for m in range(m_levels):
            p_b, v_b = curr_bids[m]
            p_a, v_a = curr_asks[m]

            # Bid side queue delta
            if m < len(prev_bids):
                p_b_prev, v_b_prev = prev_bids[m]
                if p_b > p_b_prev:
                    delta_v_b = v_b
                elif p_b == p_b_prev:
                    delta_v_b = v_b - v_b_prev
                else:
                    delta_v_b = -v_b_prev
            else:
                delta_v_b = v_b

            # Ask side queue delta
            if m < len(prev_asks):
                p_a_prev, v_a_prev = prev_asks[m]
                if p_a < p_a_prev:
                    delta_v_a = v_a
                elif p_a == p_a_prev:
                    delta_v_a = v_a - v_a_prev
                else:
                    delta_v_a = -v_a_prev
            else:
                delta_v_a = v_a

            ofi_m = delta_v_b - delta_v_a
            level_ofis.append(ofi_m)
            level_vols.append(0.5 * (v_b + v_a))

        weights = self._level_weights[:m_levels]
        arr_ofis = np.array(level_ofis, dtype=np.float64)
        arr_vols = np.array(level_vols, dtype=np.float64)

        weighted_ofi = float(np.sum(weights * arr_ofis))
        weighted_vol = float(np.sum(weights * arr_vols))

        norm_ofi = float(np.clip(weighted_ofi / max(1.0, weighted_vol), -1.0, 1.0))
        state["latest_ofi"] = norm_ofi
        state["last_bids"] = curr_bids
        state["last_asks"] = curr_asks

        # Pre-crash liquidity evaporation monitoring
        top_depth = float(sum(b[1] for b in curr_bids) + sum(a[1] for a in curr_asks))
        has_depth_baseline = len(state["depth_history"]) >= 3 and state["baseline_depth"] > 0
        depth_collapse = bool(has_depth_baseline and top_depth < 0.20 * state["baseline_depth"])

        state["depth_history"].append(top_depth)
        if len(state["depth_history"]) >= 3:
            state["baseline_depth"] = float(np.mean(state["depth_history"]))

        best_bid = curr_bids[0][0]
        best_ask = curr_asks[0][0]
        if best_bid > 0 and best_ask >= best_bid:
            mid = 0.5 * (best_bid + best_ask)
            spread_bps = max(0.1, (best_ask - best_bid) / mid * 10000.0)

            has_spread_baseline = len(state["spread_history"]) >= 3 and state["baseline_spread_bps"] > 0
            spread_blowout = bool(has_spread_baseline and spread_bps > 3.0 * state["baseline_spread_bps"])

            state["spread_history"].append(spread_bps)
            if len(state["spread_history"]) >= 3:
                state["baseline_spread_bps"] = float(np.mean(state["spread_history"]))

            # Pre-crash liquidity evaporation condition:
            # 1. Depth collapses to < 20% of baseline depth
            # 2. Spread widens to > 3x baseline spread
            state["is_evaporating"] = depth_collapse or spread_blowout
        else:
            state["is_evaporating"] = False

        return norm_ofi

    def compute_vpin(self, symbol: str) -> float:
        """
        Calculates rolling Volume-Synchronized Probability of Toxicity (VPIN) in [0.0, 1.0].
        VPIN = sum(|V_tau^B - V_tau^S|) / (N * V).
        """
        state = self._get_or_create_symbol_state(symbol)
        completed = state["completed_buckets"]

        if len(completed) > 0:
            tot_imbalance = sum(b.imbalance for b in completed)
            tot_volume = sum(b.accumulated_volume for b in completed)
            if tot_volume > 0:
                vpin_val = tot_imbalance / tot_volume
                return float(np.clip(vpin_val, 0.0, 1.0))

        cur = state["current_bucket"]
        if cur.accumulated_volume > 0:
            vpin_val = cur.imbalance / cur.accumulated_volume
            return float(np.clip(vpin_val, 0.0, 1.0))

        return 0.0

    def compute_ofi(self, symbol: str) -> float:
        """Returns the latest normalized Order Flow Imbalance (OFI) in [-1.0, 1.0]."""
        state = self._get_or_create_symbol_state(symbol)
        return float(state["latest_ofi"])

    def evaluate_toxicity(
        self,
        symbol: str,
        order_side: str = "BUY",
        current_spread_bps: float = 5.0,
        is_small_cap: bool = False,
        action: Optional[str] = None,
    ) -> ToxicityEvaluationResult:
        """
        Evaluates comprehensive microstructure toxicity for order routing and risk gating.
        Combines continuous VPIN, multi-level OFI, spread elevation, and pre-crash evaporation.
        """
        side = str(action if action is not None else order_side).strip().upper()
        spread_bps = max(0.1, float(current_spread_bps))
        state = self._get_or_create_symbol_state(symbol)

        vpin = self.compute_vpin(symbol)
        ofi = self.compute_ofi(symbol)

        # Directional adverse order flow alignment
        if side in ["BUY", "BID", "LONG"]:
            # For BUY orders, aggressive selling pressure (negative OFI) causes adverse selection
            adverse_dir = max(0.0, -ofi)
        elif side in ["SELL", "ASK", "SHORT"]:
            # For SELL orders, aggressive buying pressure (positive OFI) causes adverse selection
            adverse_dir = max(0.0, ofi)
        else:
            adverse_dir = abs(ofi)

        base_spread = max(0.1, state["baseline_spread_bps"])
        spread_ratio = min(1.0, spread_bps / base_spread)

        # Composite toxicity metric:
        # T = clip(0.55 * VPIN + 0.35 * AdverseDirection + 0.10 * min(1.0, Spread / Spread_baseline), 0.0, 1.0)
        t_raw = 0.55 * vpin + 0.35 * adverse_dir + 0.10 * spread_ratio
        t_comp = float(np.clip(t_raw, 0.0, 1.0))

        # Check pre-crash liquidity evaporation:
        # Triggered when book depth collapses (< 20% baseline) or spread blows out (> 3x baseline)
        evap_detected = bool(state["is_evaporating"])
        if evap_detected:
            t_comp = max(t_comp, 0.88)

        # Threshold check: small-cap (0.65) vs standard (0.70)
        threshold = self.toxicity_threshold_smallcap if is_small_cap else self.toxicity_threshold_standard
        is_toxic = bool(t_comp >= threshold)

        # Dynamic quote shading offset:
        # quote_shade_offset_bps = clip((T - 0.50) * 2.0 * spread_bps, 0.0, 50.0)
        if t_comp > 0.50:
            shade_bps = float(np.clip((t_comp - 0.50) * 2.0 * spread_bps, 0.0, 50.0))
        else:
            shade_bps = 0.0

        # Execution strategy modulation and slice multiplier
        if evap_detected:
            rec_strategy = "HALT_OR_DELAY"
            slice_multiplier = 3.0
        elif is_toxic:
            if side in ["BUY", "BID", "LONG"]:
                rec_strategy = "PASSIVE_LIMIT"
                slice_multiplier = 2.0
            else:
                rec_strategy = "FAST_VWAP"
                slice_multiplier = 0.5
        else:
            rec_strategy = "NORMAL"
            slice_multiplier = 1.0

        return ToxicityEvaluationResult(
            symbol=str(symbol).strip().upper(),
            vpin_score=vpin,
            ofi_score=ofi,
            composite_toxicity=t_comp,
            is_toxic=is_toxic,
            is_evaporating=evap_detected,
            quote_shade_offset_bps=shade_bps,
            recommended_strategy=rec_strategy,
            slice_count_multiplier=slice_multiplier,
            order_side=side,
            spread_bps=spread_bps,
            vpin_threshold=threshold,
        )

    def get_quote_shade_price(
        self,
        symbol: str,
        target_price: float,
        order_side: str = "BUY",
        current_spread_bps: float = 5.0,
    ) -> float:
        """
        Computes shaded target execution price based on dynamic toxicity offset.
        For BUY: shades price down to avoid paying aggressive ask.
        For SELL: shades price up to capture spread or rapid liquidation.
        """
        target_px = float(target_price)
        if not math.isfinite(target_px) or target_px <= 0.0:
            return target_px

        eval_res = self.evaluate_toxicity(symbol, order_side=order_side, current_spread_bps=current_spread_bps)
        shade_bps = eval_res.quote_shade_offset_bps

        if eval_res.is_evaporating and eval_res.order_side in ["BUY", "BID", "LONG"]:
            # Pre-crash evaporation: apply protective 1.5% discount
            return target_px * 0.985

        if shade_bps <= 0.0:
            return target_px

        frac = shade_bps / 10000.0
        if eval_res.order_side in ["BUY", "BID", "LONG"]:
            return target_px * (1.0 - frac)
        else:
            return target_px * (1.0 + frac)


# Alias tree for backward compatibility and architectural specifications
MicrostructureLiquidityToxicityFilter = IntradayToxicityFilter
VPINOrderFlowImbalanceFilter = IntradayToxicityFilter
Phase110ToxicityFilter = IntradayToxicityFilter
RealTimeToxicityFilter = IntradayToxicityFilter
RealTimeMicrostructureToxicityFilter = IntradayToxicityFilter
MicrostructureToxicityFilter = IntradayToxicityFilter
VPINOFIToxicityFilter = IntradayToxicityFilter

__all__ = [
    "VolumeBucket",
    "ToxicityEvaluationResult",
    "IntradayToxicityFilter",
    "MicrostructureLiquidityToxicityFilter",
    "VPINOrderFlowImbalanceFilter",
    "Phase110ToxicityFilter",
    "RealTimeToxicityFilter",
    "RealTimeMicrostructureToxicityFilter",
    "MicrostructureToxicityFilter",
    "VPINOFIToxicityFilter",
]
