"""
src/risk/hyper_compounding_leverage.py
======================================
Feature F952 (Phase 193 / Release R184):
Hyper-Compounding Super-Exponential Dynamic Leverage Coupler.

Provides institutional regime-adaptive dynamic leverage allocation with:
1. 10-day VIX Contango Lock verification (VIX1M < VIX3M for 10 consecutive trading days).
2. Regime-dependent leverage ceiling matrix:
   - BULL_STABLE: 2.50x (active contango lock required)
   - BULL_VOLATILE: 1.80x
   - SIDEWAYS_STABLE: 1.50x
   - SIDEWAYS_VOLATILE: 1.00x
   - BEAR_STABLE: 0.80x
   - BEAR_VOLATILE: 0.50x
   - PANIC_CRISIS: 0.20x
3. Emergency crisis failsafe: drops leverage to <= 0.40x (or <= 0.20x on extreme shocks)
   when VIX > 32.0, backwardation (VIX1M >= VIX3M) is detected, or in PANIC_CRISIS.
4. Super-exponential compounding formula:
   L_target = base_lev * exp(0.131 * (confluence_score / 3.0))
   strictly clamped between 0.10x and the regime frontier ceiling (up to 2.50x).
5. Dynamic rate-of-change limiter (Delta L <= 0.25x per rebalance interval).
"""

from __future__ import annotations

import logging
import math
from typing import Any, Dict, List, Optional, Sequence, Union

import numpy as np

logger = logging.getLogger(__name__)

# Metadata Constants
VERSION: int = 193
RELEASE: str = "R184"
FEATURE: str = "F952"

VERSION_PHASE193: int = 193
RELEASE_PHASE193: str = "R184"
FEATURE_F952: str = "F952"

VERSION_R184: int = 193
RELEASE_R184: str = "R184"


def evaluate_10d_contango_lock(history: Sequence[Any]) -> bool:
    """
    Evaluates whether the 10-day VIX term structure contango lock invariant holds.
    Requires that VIX1M < VIX3M for all 10 consecutive entries in the provided history.

    Parameters:
        history: Sequence of length >= 10 containing daily VIX term structure observations.
                 Each element may be a dict with keys ('vix1m', 'vix3m') or ('vix_1m', 'vix_3m'),
                 or a tuple/list (vix1m, vix3m), or an object with vix1m, vix3m attributes.

    Returns:
        bool: True if history contains at least 10 observations and all the last 10 entries
              satisfy vix1m < vix3m. False otherwise.
    """
    if history is None or not isinstance(history, (list, tuple, Sequence)):
        return False

    if len(history) < 10:
        return False

    # Evaluate the most recent 10 entries
    recent_10 = history[-10:] if len(history) > 10 else history

    for entry in recent_10:
        vix1m: Optional[float] = None
        vix3m: Optional[float] = None

        if isinstance(entry, dict):
            vix1m = entry.get("vix1m", entry.get("vix_1m", entry.get("VIX1M", entry.get("VIX_1M"))))
            vix3m = entry.get("vix3m", entry.get("vix_3m", entry.get("VIX3M", entry.get("VIX_3M"))))
        elif isinstance(entry, (list, tuple)) and len(entry) >= 2:
            vix1m = entry[0]
            vix3m = entry[1]
        elif hasattr(entry, "vix1m") and hasattr(entry, "vix3m"):
            vix1m = getattr(entry, "vix1m")
            vix3m = getattr(entry, "vix3m")

        if vix1m is None or vix3m is None:
            return False

        try:
            val_1m = float(vix1m)
            val_3m = float(vix3m)
        except (ValueError, TypeError):
            return False

        if math.isnan(val_1m) or math.isnan(val_3m):
            return False

        if val_1m >= val_3m:
            return False

    return True


class HyperCompoundingSuperExponentialLeverageCoupler:
    """
    Feature F952: Institutional Hyper-Compounding Super-Exponential Dynamic Leverage Coupler.
    Dynamically adjusts portfolio gross leverage based on 2D market regime, VIX term structure,
    contango lock, and multi-factor confluence score.
    """

    # Authoritative Regime Leverage Ceiling Matrix
    REGIME_LIMITS: Dict[str, float] = {
        "BULL_STABLE": 2.50,
        "BULL_VOLATILE": 1.80,
        "SIDEWAYS_STABLE": 1.50,
        "SIDEWAYS_VOLATILE": 1.00,
        "BEAR_STABLE": 0.80,
        "BEAR_VOLATILE": 0.50,
        "PANIC_CRISIS": 0.20,
    }

    # Extended regime alias mappings across trading system naming conventions
    _REGIME_ALIASES: Dict[str, str] = {
        "BULL_LOW_VOL": "BULL_STABLE",
        "BULL_HIGH_VOL": "BULL_VOLATILE",
        "SIDEWAYS_LOW_VOL": "SIDEWAYS_STABLE",
        "SIDEWAYS_HIGH_VOL": "SIDEWAYS_VOLATILE",
        "BEAR_LOW_VOL": "BEAR_STABLE",
        "BEAR_HIGH_VOL": "BEAR_VOLATILE",
        "RELIEF_RALLY": "SIDEWAYS_STABLE",
        "CRISIS": "PANIC_CRISIS",
        "PANIC": "PANIC_CRISIS",
    }

    def __init__(
        self,
        alpha_boost: float = 0.131,
        max_frontier_leverage: float = 2.50,
        min_frontier_leverage: float = 0.10,
        failsafe_leverage: float = 0.40,
        vix_panic_threshold: float = 32.0,
        vix_spike_threshold: float = 60.0,
        max_daily_delta: float = 0.25,
        **kwargs: Any,
    ):
        self.alpha_boost = float(alpha_boost)
        self.max_frontier_leverage = float(max_frontier_leverage)
        self.min_frontier_leverage = float(min_frontier_leverage)
        self.failsafe_leverage = float(failsafe_leverage)
        self.vix_panic_threshold = float(vix_panic_threshold)
        self.vix_spike_threshold = float(vix_spike_threshold)
        self.max_daily_delta = float(max_daily_delta)
        self.regime_limits = dict(self.REGIME_LIMITS)

    def calculate_compounding_leverage(
        self,
        regime: str,
        vix_term_structure: Optional[Dict[str, Any]] = None,
        confluence_score: float = 0.0,
        prev_leverage: Optional[float] = None,
        apply_rate_limit: bool = False,
    ) -> float:
        """
        Calculates dynamic compounding leverage subject to regime constraints, VIX term structure,
        10-day contango lock, emergency failsafe drop, and super-exponential compounding boost.

        Parameters:
            regime: Current market regime identifier (e.g. 'BULL_STABLE', 'PANIC_CRISIS').
            vix_term_structure: Dict containing term structure info: 'vix1m', 'vix3m', 'contango_days',
                                or 'history'.
            confluence_score: Composite multi-factor conviction / confluence score (typically in [-3.0, 3.0]).
            prev_leverage: Optional previous period leverage for rate-of-change smoothing.
            apply_rate_limit: If True and prev_leverage is provided, limits step change to max_daily_delta.

        Returns:
            float: Certified gross portfolio leverage clamped between 0.10x and 2.50x.
        """
        regime_norm = str(regime).strip().upper().replace(" ", "_")
        canonical_regime = self._REGIME_ALIASES.get(regime_norm, regime_norm)

        # Baseline ceiling from regime matrix
        base_limit = self.regime_limits.get(canonical_regime, 1.00)

        # Extract VIX term structure metrics
        vix_dict = vix_term_structure if isinstance(vix_term_structure, dict) else {}
        vix1m = float(vix_dict.get("vix1m", vix_dict.get("vix_1m", vix_dict.get("vix", 18.0))))
        vix3m = float(vix_dict.get("vix3m", vix_dict.get("vix_3m", vix1m + 2.0)))
        contango_days = int(vix_dict.get("contango_days", 10 if vix1m < vix3m else 0))
        history = vix_dict.get("history")

        is_backwardation = (vix1m >= vix3m)
        is_high_vix = (vix1m > self.vix_panic_threshold or vix3m > self.vix_panic_threshold)
        is_extreme_vix = (vix1m >= self.vix_spike_threshold or vix3m >= self.vix_spike_threshold)
        is_panic = (canonical_regime == "PANIC_CRISIS")

        # Evaluate 10-day contango lock
        if history is not None and isinstance(history, (list, tuple)) and len(history) >= 10:
            is_contango_locked = evaluate_10d_contango_lock(history)
        else:
            is_contango_locked = (contango_days >= 10) and not is_backwardation

        # Determine effective regime ceiling
        ceiling = base_limit

        # 1. Contango lock requirement in BULL_STABLE
        if canonical_regime == "BULL_STABLE":
            if not is_contango_locked:
                # Without active 10d contango lock, drop BULL ceiling to volatile level
                ceiling = min(ceiling, self.regime_limits.get("BULL_VOLATILE", 1.80))
            else:
                ceiling = self.max_frontier_leverage  # 2.50

        # 2. Backwardation lockout: backwardation limits leverage strictly <= 1.00x
        if is_backwardation:
            ceiling = min(ceiling, 1.00)

        # 3. Emergency Crisis Failsafe Drop: VIX > 32.0 or Backwardation or PANIC_CRISIS
        if is_panic or is_backwardation or is_high_vix:
            ceiling = min(ceiling, self.failsafe_leverage)  # <= 0.40x

        # 4. Extreme VIX Spike (VIX >= 60.0): collapse to panic crisis level <= 0.20x
        if is_extreme_vix:
            ceiling = min(ceiling, self.regime_limits.get("PANIC_CRISIS", 0.20))

        # 5. Super-Exponential Compounding Boost Formula
        # base_lev is regime baseline clamped to ceiling
        base_lev = min(base_limit, ceiling)
        conf_clamped = float(np.clip(confluence_score, -3.0, 3.0))

        # Super-exponential factor: base_lev * exp(alpha_boost * (confluence_score / 3.0))
        boost_exponent = self.alpha_boost * (conf_clamped / 3.0)
        boosted_leverage = base_lev * math.exp(boost_exponent)

        # In BULL_STABLE with full contango lock and strong conviction, ensure frontier reach
        if canonical_regime == "BULL_STABLE" and is_contango_locked and conf_clamped >= 2.5:
            # Full frontier reach allowed
            boosted_leverage = max(boosted_leverage, 2.50)

        # Strict clamping between min frontier (0.10x) and effective regime ceiling
        clamped_leverage = float(np.clip(boosted_leverage, self.min_frontier_leverage, ceiling))

        # Optional rate-of-change smoothing
        if apply_rate_limit and prev_leverage is not None:
            clamped_leverage = self.apply_rate_of_change_limiter(
                current_leverage=float(prev_leverage),
                target_leverage=clamped_leverage,
                max_delta=self.max_daily_delta,
            )

        return round(clamped_leverage, 4)

    def apply_rate_of_change_limiter(
        self,
        current_leverage: float,
        target_leverage: float,
        max_delta: Optional[float] = None,
    ) -> float:
        """
        Limits daily leverage rate of change to Delta L <= max_delta (default 0.25x) per rebalance.
        """
        delta_bound = self.max_daily_delta if max_delta is None else float(max_delta)
        delta = float(np.clip(target_leverage - current_leverage, -delta_bound, delta_bound))
        return float(current_leverage + delta)


# Backward Compatibility and Domain Aliases
DynamicCompoundingLeverageCoupler = HyperCompoundingSuperExponentialLeverageCoupler
Phase193DynamicLeverageCoupler = HyperCompoundingSuperExponentialLeverageCoupler
F952DynamicLeverageCoupler = HyperCompoundingSuperExponentialLeverageCoupler
SuperExponentialLeverageCoupler = HyperCompoundingSuperExponentialLeverageCoupler
Phase184DynamicLeverageCoupler = HyperCompoundingSuperExponentialLeverageCoupler

__all__ = [
    "VERSION",
    "RELEASE",
    "FEATURE",
    "VERSION_PHASE193",
    "RELEASE_PHASE193",
    "FEATURE_F952",
    "VERSION_R184",
    "RELEASE_R184",
    "evaluate_10d_contango_lock",
    "HyperCompoundingSuperExponentialLeverageCoupler",
    "DynamicCompoundingLeverageCoupler",
    "Phase193DynamicLeverageCoupler",
    "F952DynamicLeverageCoupler",
    "SuperExponentialLeverageCoupler",
    "Phase184DynamicLeverageCoupler",
]
