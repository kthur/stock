"""
trading_system/src/risk/intraday_risk_monitor.py — Institutional Intraday Risk Monitor & Flash-Crash Circuit Breaker.

Phase 106 / Feature F502 / Release R122 (v113 Production Master)
Milestone 3: Institutional Intraday Risk Monitor & Flash-Crash Circuit Breaker.

This module provides institutional-grade intraday risk governance across 5 global markets
(KOSPI, KOSDAQ, SP500, NASDAQ, RUSSELL2000):
1. 3-Tier Profit Taking (+5.0% partial exit & breakeven lock at entry+0.3%,
   +10.0% partial exit & ratchet trailing stop to entry+5.0%,
   +20.0% runner exit).
2. Leland Volatility-Adaptive Trailing Stop Bands:
   - Baseline hard stop: -6.0% from entry price.
   - Peak trailing stop: -10.0% from highest high price achieved.
   - Asymmetric Leland multiplier: expands band up to 1.8x for high positive momentum/volatility,
     tightens to 0.6x for slowing momentum/calm market.
3. Automated Flash-Crash Circuit Breakers:
   - Single-asset intraday drop >= 7.0% from max(open, prev_close) -> Emergency liquidation order.
   - Macro VIX surge > 20.0% within 1 hour -> Immediate Gate 8 synthetic inverse hedge order
     ('114800' for KRX, 'PSQ' for NASDAQ, 'SH' for SP500/RUSSELL2000).
4. Full batch portfolio evaluation compatible with ExecutionOMSEngine and PaperTradingDaemon.
"""

from __future__ import annotations

import collections
import datetime
import logging
import math
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

import numpy as np

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Structured Output Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class RiskAction:
    """Structured risk mitigation order emitted by InstitutionalIntradayRiskMonitor.

    Compatible with ExecutionOMSEngine and PaperTradingDaemon order pipelines.
    """
    action_id: str
    symbol: str
    market: str
    action: str                       # SELL | BUY_HEDGE | HOLD | UPDATE_STOP
    quantity: int
    ratio: float                      # Fraction of position (e.g. 0.30, 0.40, 1.0)
    trigger_price: float              # Price or threshold that caused the trigger
    current_price: float              # Current asset price at trigger
    stop_price: float                 # Effective stop price associated with action
    reason: str                       # Machine-readable trigger reason
    severity: str = "INFO"            # INFO | WARN | CRITICAL
    force_liquidate: bool = False     # Emergency execution flag
    is_hedge: bool = False            # True for Gate 8 synthetic inverse hedges
    target_hedge_instrument: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert RiskAction to a standard dictionary representation."""
        return {
            "action_id": self.action_id,
            "symbol": self.symbol,
            "market": self.market,
            "action": self.action,
            "quantity": int(self.quantity),
            "ratio": float(self.ratio),
            "trigger_price": float(self.trigger_price),
            "current_price": float(self.current_price),
            "stop_price": float(self.stop_price),
            "reason": self.reason,
            "severity": self.severity,
            "force_liquidate": bool(self.force_liquidate),
            "is_hedge": bool(self.is_hedge),
            "target_hedge_instrument": self.target_hedge_instrument,
            "timestamp": self.timestamp,
            "details": self.details,
        }


@dataclass
class PositionRiskState:
    """Internal state tracking for an actively monitored portfolio holding."""
    symbol: str
    market: str
    entry_price: float
    initial_quantity: int
    current_quantity: int
    peak_price: float
    volatility_20d: float = 0.02
    momentum_factor: float = 0.0
    tier1_executed: bool = False
    tier2_executed: bool = False
    tier3_executed: bool = False
    breakeven_locked: bool = False
    breakeven_price: float = 0.0
    ratchet_locked: bool = False
    ratchet_price: float = 0.0
    baseline_stop_price: float = 0.0
    trailing_stop_price: float = 0.0
    effective_stop_price: float = 0.0
    last_price: float = 0.0
    last_updated: str = field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Convert PositionRiskState to a serializable dictionary."""
        return {
            "symbol": self.symbol,
            "market": self.market,
            "entry_price": float(self.entry_price),
            "initial_quantity": int(self.initial_quantity),
            "current_quantity": int(self.current_quantity),
            "peak_price": float(self.peak_price),
            "volatility_20d": float(self.volatility_20d),
            "momentum_factor": float(self.momentum_factor),
            "tier1_executed": bool(self.tier1_executed),
            "tier2_executed": bool(self.tier2_executed),
            "tier3_executed": bool(self.tier3_executed),
            "breakeven_locked": bool(self.breakeven_locked),
            "breakeven_price": float(self.breakeven_price),
            "ratchet_locked": bool(self.ratchet_locked),
            "ratchet_price": float(self.ratchet_price),
            "baseline_stop_price": float(self.baseline_stop_price),
            "trailing_stop_price": float(self.trailing_stop_price),
            "effective_stop_price": float(self.effective_stop_price),
            "last_price": float(self.last_price),
            "last_updated": self.last_updated,
        }


# ---------------------------------------------------------------------------
# Institutional Intraday Risk Monitor Engine
# ---------------------------------------------------------------------------

class InstitutionalIntradayRiskMonitor:
    """Institutional Real-Time Intraday Risk Monitor & Flash-Crash Circuit Breaker.

    Provides multi-market intraday portfolio oversight, continuous profit-taking
    ratcheting, Leland volatility-adaptive trailing stop protection, and automated
    flash-crash emergency liquidation and Gate 8 inverse hedging.
    """

    DEFAULT_INVERSE_HEDGE_INSTRUMENTS: Dict[str, str] = {
        "KRX": "114800",       # KODEX 200 선물인버스2X (-2x leverage)
        "KOSPI": "114800",
        "KOSDAQ": "114800",
        "NASDAQ": "PSQ",       # ProShares Short QQQ (-1x leverage)
        "SP500": "SH",         # ProShares Short S&P 500 (-1x leverage)
        "RUSSELL2000": "SH",   # Benchmark fallback
        "US": "SH",
        "GLOBAL": "SH",
    }

    def __init__(
        self,
        baseline_stop_pct: float = -0.06,
        peak_trailing_stop_pct: float = -0.10,
        tier1_profit_pct: float = 0.05,
        tier1_ratio: float = 0.30,
        tier1_breakeven_offset: float = 0.003,
        tier2_profit_pct: float = 0.10,
        tier2_ratio: float = 0.30,
        tier2_ratchet_offset: float = 0.050,
        tier3_profit_pct: float = 0.20,
        tier3_ratio: float = 0.40,
        leland_min_mult: float = 0.60,
        leland_max_mult: float = 1.80,
        volatility_base: float = 0.02,
        vol_sensitivity: float = 0.50,
        mom_sensitivity: float = 0.80,
        flash_crash_asset_drop_pct: float = -0.07,
        flash_crash_vix_surge_pct: float = 0.20,
        vix_hedge_instruments: Optional[Dict[str, str]] = None,
        max_symbols: int = 2000,
    ):
        """Initialize the InstitutionalIntradayRiskMonitor with institutional parameters.

        Parameters
        ----------
        baseline_stop_pct : float
            Baseline hard stop-loss distance from entry price (default -0.06 = -6.0%).
        peak_trailing_stop_pct : float
            Baseline trailing stop distance from highest price achieved (default -0.10 = -10.0%).
        tier1_profit_pct : float
            Return threshold for Tier 1 partial take profit (default 0.05 = +5.0%).
        tier1_ratio : float
            Position fraction to exit at Tier 1 (default 0.30 = 30%).
        tier1_breakeven_offset : float
            Lock-in offset for breakeven stop at Tier 1 (default 0.003 = entry + 0.3%).
        tier2_profit_pct : float
            Return threshold for Tier 2 partial take profit (default 0.10 = +10.0%).
        tier2_ratio : float
            Position fraction to exit at Tier 2 (default 0.30 = 30%).
        tier2_ratchet_offset : float
            Ratchet trailing stop offset at Tier 2 (default 0.050 = entry + 5.0%).
        tier3_profit_pct : float
            Return threshold for Tier 3 runner take profit (default 0.20 = +20.0%).
        tier3_ratio : float
            Position fraction to exit at Tier 3 (default 0.40 = 40% / remaining).
        leland_min_mult : float
            Lower bound for Leland volatility multiplier (default 0.60).
        leland_max_mult : float
            Upper bound for Leland volatility multiplier (default 1.80).
        volatility_base : float
            Reference daily volatility for Leland scaling (default 0.02 = 2.0% daily).
        vol_sensitivity : float
            Sensitivity of Leland multiplier to volatility deviations (default 0.50).
        mom_sensitivity : float
            Sensitivity of Leland multiplier to momentum (default 0.80).
        flash_crash_asset_drop_pct : float
            Threshold for single-asset flash crash from reference price (default -0.07 = -7.0%).
        flash_crash_vix_surge_pct : float
            Threshold for 1-hour macro VIX surge (default 0.20 = +20.0%).
        vix_hedge_instruments : Optional[Dict[str, str]]
            Mapping of market to target Gate 8 synthetic inverse hedge instrument.
        max_symbols : int
            Maximum number of active positions to track in memory.
        """
        self.baseline_stop_pct = float(baseline_stop_pct)
        self.peak_trailing_stop_pct = float(peak_trailing_stop_pct)
        self.tier1_profit_pct = float(tier1_profit_pct)
        self.tier1_ratio = float(tier1_ratio)
        self.tier1_breakeven_offset = float(tier1_breakeven_offset)
        self.tier2_profit_pct = float(tier2_profit_pct)
        self.tier2_ratio = float(tier2_ratio)
        self.tier2_ratchet_offset = float(tier2_ratchet_offset)
        self.tier3_profit_pct = float(tier3_profit_pct)
        self.tier3_ratio = float(tier3_ratio)
        self.leland_min_mult = float(leland_min_mult)
        self.leland_max_mult = float(leland_max_mult)
        self.volatility_base = max(1e-6, float(volatility_base))
        self.vol_sensitivity = float(vol_sensitivity)
        self.mom_sensitivity = float(mom_sensitivity)
        self.flash_crash_asset_drop_pct = float(flash_crash_asset_drop_pct)
        self.flash_crash_vix_surge_pct = float(flash_crash_vix_surge_pct)
        self.max_symbols = int(max_symbols)

        self.vix_hedge_instruments = dict(self.DEFAULT_INVERSE_HEDGE_INSTRUMENTS)
        if vix_hedge_instruments:
            self.vix_hedge_instruments.update(vix_hedge_instruments)

        self.positions: Dict[str, PositionRiskState] = collections.OrderedDict()
        self.vix_history: collections.deque = collections.deque(maxlen=240)
        self.executed_actions: List[RiskAction] = []

    # -----------------------------------------------------------------------
    # Helper & State Management
    # -----------------------------------------------------------------------

    def resolve_hedge_instrument(self, market: Optional[str] = None, symbol: Optional[str] = None) -> str:
        """Resolve the Gate 8 synthetic inverse hedge instrument for a given market or symbol."""
        if market:
            m_up = str(market).upper()
            if m_up in self.vix_hedge_instruments:
                return self.vix_hedge_instruments[m_up]
            if "KR" in m_up or "KOS" in m_up:
                return "114800"
            if "NAS" in m_up:
                return "PSQ"
            if "SP" in m_up or "US" in m_up:
                return "SH"

        if symbol:
            s_clean = str(symbol).strip()
            if s_clean.isdigit() or s_clean.endswith((".KS", ".KQ")):
                return "114800"
            return "SH"

        return "SH"

    def register_position(
        self,
        symbol: str,
        entry_price: float,
        quantity: int,
        market: str = "KOSPI",
        volatility_20d: float = 0.02,
        momentum_factor: float = 0.0,
        peak_price: Optional[float] = None,
    ) -> PositionRiskState:
        """Register or update an actively monitored position."""
        sym = str(symbol).strip()
        safe_entry = float(entry_price) if math.isfinite(float(entry_price)) and float(entry_price) > 0 else 1.0
        safe_qty = max(0, int(quantity))
        safe_peak = float(peak_price) if (peak_price is not None and math.isfinite(float(peak_price)) and float(peak_price) > 0) else safe_entry
        safe_vol = max(1e-6, float(volatility_20d)) if math.isfinite(float(volatility_20d)) else self.volatility_base
        safe_mom = float(momentum_factor) if math.isfinite(float(momentum_factor)) else 0.0

        baseline_stop = safe_entry * (1.0 + self.baseline_stop_pct)
        leland_m = self.compute_leland_multiplier(safe_vol, safe_mom)
        trailing_stop = safe_peak * (1.0 - abs(self.peak_trailing_stop_pct) * leland_m)
        effective_stop = max(baseline_stop, trailing_stop)

        state = PositionRiskState(
            symbol=sym,
            market=market,
            entry_price=safe_entry,
            initial_quantity=safe_qty,
            current_quantity=safe_qty,
            peak_price=max(safe_peak, safe_entry),
            volatility_20d=safe_vol,
            momentum_factor=safe_mom,
            baseline_stop_price=baseline_stop,
            trailing_stop_price=trailing_stop,
            effective_stop_price=effective_stop,
            last_price=safe_entry,
        )

        if len(self.positions) >= self.max_symbols and sym not in self.positions:
            self.positions.pop(next(iter(self.positions)))

        self.positions[sym] = state
        return state

    def get_position(self, symbol: str) -> Optional[PositionRiskState]:
        """Retrieve tracking state for a monitored symbol."""
        return self.positions.get(str(symbol).strip())

    def reset_state(self) -> None:
        """Clear all active positions, VIX history, and recorded actions."""
        self.positions.clear()
        self.vix_history.clear()
        self.executed_actions.clear()

    def get_active_stops(self) -> Dict[str, Dict[str, float]]:
        """Return a snapshot of active stops across all monitored positions."""
        return {
            sym: {
                "entry_price": p.entry_price,
                "peak_price": p.peak_price,
                "baseline_stop": p.baseline_stop_price,
                "trailing_stop": p.trailing_stop_price,
                "breakeven_stop": p.breakeven_price,
                "ratchet_stop": p.ratchet_price,
                "effective_stop": p.effective_stop_price,
                "current_quantity": p.current_quantity,
            }
            for sym, p in self.positions.items()
        }

    def _extract_holding_fields(self, holding: Any) -> PositionRiskState:
        """Safely extract or adapt holding into a PositionRiskState."""
        if isinstance(holding, PositionRiskState):
            return holding

        if isinstance(holding, dict):
            sym = str(holding.get("symbol", "")).strip()
            existing = self.positions.get(sym)
            if existing is not None:
                # Update current quantity and parameters if provided
                if "quantity" in holding or "shares" in holding or "position_qty" in holding:
                    q = holding.get("quantity", holding.get("shares", holding.get("position_qty", existing.current_quantity)))
                    existing.current_quantity = max(0, int(q))
                if "volatility_20d" in holding or "volatility" in holding:
                    v = holding.get("volatility_20d", holding.get("volatility", existing.volatility_20d))
                    if math.isfinite(float(v)):
                        existing.volatility_20d = float(v)
                if "momentum_factor" in holding or "momentum" in holding:
                    m = holding.get("momentum_factor", holding.get("momentum", existing.momentum_factor))
                    if math.isfinite(float(m)):
                        existing.momentum_factor = float(m)
                return existing

            # Register as new position
            entry_p = float(holding.get("entry_price", holding.get("price", holding.get("target_price", 1.0))))
            qty = int(holding.get("quantity", holding.get("shares", holding.get("position_qty", holding.get("initial_quantity", 0)))))
            mkt = str(holding.get("market", "KOSPI"))
            vol = float(holding.get("volatility_20d", holding.get("volatility", self.volatility_base)))
            mom = float(holding.get("momentum_factor", holding.get("momentum", 0.0)))
            peak = holding.get("peak_price", None)
            return self.register_position(
                symbol=sym,
                entry_price=entry_p,
                quantity=qty,
                market=mkt,
                volatility_20d=vol,
                momentum_factor=mom,
                peak_price=peak,
            )

        # Attribute-based object adapter
        sym = getattr(holding, "symbol", str(holding))
        existing = self.positions.get(sym)
        if existing is not None:
            return existing

        entry_p = float(getattr(holding, "entry_price", getattr(holding, "price", 1.0)))
        qty = int(getattr(holding, "quantity", getattr(holding, "shares", getattr(holding, "position_qty", 0))))
        mkt = getattr(holding, "market", "KOSPI")
        vol = float(getattr(holding, "volatility_20d", getattr(holding, "volatility", self.volatility_base)))
        mom = float(getattr(holding, "momentum_factor", getattr(holding, "momentum", 0.0)))
        return self.register_position(
            symbol=sym,
            entry_price=entry_p,
            quantity=qty,
            market=mkt,
            volatility_20d=vol,
            momentum_factor=mom,
        )

    # -----------------------------------------------------------------------
    # Leland Volatility-Adaptive Multiplier
    # -----------------------------------------------------------------------

    def compute_leland_multiplier(
        self,
        volatility_20d: float,
        momentum_factor: float = 0.0,
    ) -> float:
        """Calculate asymmetric Leland trailing stop distance multiplier.

        Mathematical Invariant:
        - Scaled by volatility deviation from base volatility (sigma_20d - sigma_base) / sigma_base.
        - Augmented by positive momentum to give running winners breathing room.
        - Compressed by slowing momentum to protect paper gains quickly.
        - Bounded strictly within [leland_min_mult, leland_max_mult] = [0.60, 1.80].

        Parameters
        ----------
        volatility_20d : float
            20-day historical volatility of the asset.
        momentum_factor : float
            Normalized short/medium-term momentum (e.g. 5D/20D return or trend efficiency).

        Returns
        -------
        float
            Multiplier in [0.60, 1.80].
        """
        if math.isnan(volatility_20d):
            volatility_20d = self.volatility_base
        elif volatility_20d == float("inf"):
            return self.leland_max_mult
        elif volatility_20d == float("-inf") or volatility_20d < 0:
            volatility_20d = self.volatility_base

        if math.isnan(momentum_factor):
            momentum_factor = 0.0
        elif momentum_factor == float("inf"):
            return self.leland_max_mult
        elif momentum_factor == float("-inf"):
            return self.leland_min_mult

        vol_dev = (volatility_20d - self.volatility_base) / max(self.volatility_base, 1e-6)
        raw_multiplier = 1.0 + self.vol_sensitivity * vol_dev + self.mom_sensitivity * momentum_factor
        return float(np.clip(raw_multiplier, self.leland_min_mult, self.leland_max_mult))

    # -----------------------------------------------------------------------
    # 3-Tier Profit Taking Logic
    # -----------------------------------------------------------------------

    def evaluate_profit_taking(
        self,
        holding: Any,
        current_price: float,
    ) -> Optional[RiskAction]:
        """Evaluate 3-tier partial profit taking against current market price.

        Tiers:
        - Tier 1 (+5.0% return): 30% partial exit, locks breakeven stop at entry + 0.3%.
        - Tier 2 (+10.0% return): 30% partial exit, ratchets trailing stop to entry + 5.0%.
        - Tier 3 (+20.0% return): 40% (remaining runner) exit.

        Parameters
        ----------
        holding : Union[Dict, PositionRiskState, Any]
            Target holding information.
        current_price : float
            Current market price for the asset.

        Returns
        -------
        Optional[RiskAction]
            Action to execute, or None if no tier threshold crossed.
        """
        if not math.isfinite(current_price) or current_price <= 0.0:
            return None

        pos = self._extract_holding_fields(holding)
        if pos.current_quantity <= 0 or pos.entry_price <= 0.0:
            return None

        # Update peak price
        if current_price > pos.peak_price:
            pos.peak_price = current_price
        pos.last_price = current_price
        pos.last_updated = datetime.datetime.now(datetime.timezone.utc).isoformat()

        # Compute return from entry
        ret = (current_price - pos.entry_price) / pos.entry_price

        # Tier 1 (+5.0%)
        if ret >= self.tier1_profit_pct and not pos.tier1_executed:
            pos.tier1_executed = True
            pos.breakeven_locked = True
            pos.breakeven_price = pos.entry_price * (1.0 + self.tier1_breakeven_offset)
            pos.effective_stop_price = max(pos.effective_stop_price, pos.breakeven_price)

            exit_qty = max(1, int(math.floor(pos.initial_quantity * self.tier1_ratio)))
            exit_qty = min(exit_qty, pos.current_quantity)
            pos.current_quantity -= exit_qty

            action = RiskAction(
                action_id=f"RA_TP1_{pos.symbol}_{uuid.uuid4().hex[:8]}",
                symbol=pos.symbol,
                market=pos.market,
                action="SELL",
                quantity=exit_qty,
                ratio=self.tier1_ratio,
                trigger_price=pos.entry_price * (1.0 + self.tier1_profit_pct),
                current_price=current_price,
                stop_price=pos.breakeven_price,
                reason="PROFIT_TAKING_TIER1_5PCT",
                severity="INFO",
                force_liquidate=False,
                details={
                    "tier": 1,
                    "return_pct": ret,
                    "breakeven_stop_locked": True,
                    "breakeven_price": pos.breakeven_price,
                    "remaining_quantity": pos.current_quantity,
                },
            )
            self.executed_actions.append(action)
            return action

        # Tier 2 (+10.0%)
        if ret >= self.tier2_profit_pct and not pos.tier2_executed:
            pos.tier2_executed = True
            pos.ratchet_locked = True
            pos.ratchet_price = pos.entry_price * (1.0 + self.tier2_ratchet_offset)
            pos.effective_stop_price = max(pos.effective_stop_price, pos.ratchet_price)

            exit_qty = max(1, int(math.floor(pos.initial_quantity * self.tier2_ratio)))
            exit_qty = min(exit_qty, pos.current_quantity)
            pos.current_quantity -= exit_qty

            action = RiskAction(
                action_id=f"RA_TP2_{pos.symbol}_{uuid.uuid4().hex[:8]}",
                symbol=pos.symbol,
                market=pos.market,
                action="SELL",
                quantity=exit_qty,
                ratio=self.tier2_ratio,
                trigger_price=pos.entry_price * (1.0 + self.tier2_profit_pct),
                current_price=current_price,
                stop_price=pos.ratchet_price,
                reason="PROFIT_TAKING_TIER2_10PCT",
                severity="INFO",
                force_liquidate=False,
                details={
                    "tier": 2,
                    "return_pct": ret,
                    "ratchet_stop_locked": True,
                    "ratchet_price": pos.ratchet_price,
                    "remaining_quantity": pos.current_quantity,
                },
            )
            self.executed_actions.append(action)
            return action

        # Tier 3 (+20.0%)
        if ret >= self.tier3_profit_pct and not pos.tier3_executed:
            pos.tier3_executed = True
            # Runner exit: takes remaining quantity
            exit_qty = pos.current_quantity
            pos.current_quantity = 0

            action = RiskAction(
                action_id=f"RA_TP3_{pos.symbol}_{uuid.uuid4().hex[:8]}",
                symbol=pos.symbol,
                market=pos.market,
                action="SELL",
                quantity=exit_qty,
                ratio=self.tier3_ratio,
                trigger_price=pos.entry_price * (1.0 + self.tier3_profit_pct),
                current_price=current_price,
                stop_price=current_price,
                reason="PROFIT_TAKING_TIER3_20PCT",
                severity="INFO",
                force_liquidate=False,
                details={
                    "tier": 3,
                    "return_pct": ret,
                    "is_runner_exit": True,
                    "remaining_quantity": 0,
                },
            )
            self.executed_actions.append(action)
            return action

        return None

    # -----------------------------------------------------------------------
    # Leland Volatility-Adaptive Trailing Stop Bands
    # -----------------------------------------------------------------------

    def evaluate_leland_trailing_stop(
        self,
        holding: Any,
        current_price: float,
        peak_price: Optional[float] = None,
        volatility_20d: Optional[float] = None,
        momentum_factor: float = 0.0,
    ) -> Optional[RiskAction]:
        """Evaluate Leland volatility-adaptive trailing stop and baseline stops.

        Stop Levels Evaluated:
        1. Baseline hard stop: entry_price * (1 + baseline_stop_pct) [-6.0%].
        2. Leland dynamic trailing stop: peak_price * (1 - |trailing_stop_pct| * leland_mult) [-10.0% * M].
        3. Breakeven lock: entry_price * (1 + 0.003) if Tier 1 triggered.
        4. Ratchet lock: entry_price * (1 + 0.050) if Tier 2 triggered.

        Effective stop is the maximum of all valid stop boundaries.
        If current_price <= effective_stop, full liquidation is emitted.
        """
        if not math.isfinite(current_price) or current_price <= 0.0:
            return None

        pos = self._extract_holding_fields(holding)
        if pos.current_quantity <= 0 or pos.entry_price <= 0.0:
            return None

        # Resolve parameters
        resolved_peak = float(peak_price) if (peak_price is not None and math.isfinite(float(peak_price)) and float(peak_price) > 0) else pos.peak_price
        resolved_peak = max(resolved_peak, pos.peak_price, current_price, pos.entry_price)
        pos.peak_price = resolved_peak

        resolved_vol = float(volatility_20d) if (volatility_20d is not None and math.isfinite(float(volatility_20d))) else pos.volatility_20d
        resolved_vol = max(1e-6, resolved_vol)
        pos.volatility_20d = resolved_vol

        resolved_mom = float(momentum_factor) if math.isfinite(float(momentum_factor)) else pos.momentum_factor
        pos.momentum_factor = resolved_mom

        # 1. Baseline Hard Stop
        baseline_stop = pos.entry_price * (1.0 + self.baseline_stop_pct)
        pos.baseline_stop_price = baseline_stop

        # 2. Leland Trailing Stop
        leland_m = self.compute_leland_multiplier(resolved_vol, resolved_mom)
        trailing_distance = abs(self.peak_trailing_stop_pct) * leland_m
        trailing_stop = resolved_peak * (1.0 - trailing_distance)
        pos.trailing_stop_price = trailing_stop

        # 3. Breakeven & Ratchet Stops
        breakeven_stop = pos.breakeven_price if pos.breakeven_locked else 0.0
        ratchet_stop = pos.ratchet_price if pos.ratchet_locked else 0.0

        # Effective Stop (highest protection level)
        effective_stop = max(baseline_stop, trailing_stop, breakeven_stop, ratchet_stop)
        pos.effective_stop_price = effective_stop
        pos.last_price = current_price
        pos.last_updated = datetime.datetime.now(datetime.timezone.utc).isoformat()

        # Check if stop is breached
        if current_price <= effective_stop:
            # Determine specific trigger cause
            if pos.ratchet_locked and math.isclose(effective_stop, ratchet_stop, rel_tol=1e-5):
                reason = "RATCHET_STOP_5PCT"
                severity = "INFO"
            elif pos.breakeven_locked and math.isclose(effective_stop, breakeven_stop, rel_tol=1e-5):
                reason = "BREAKEVEN_STOP_LOCK"
                severity = "INFO"
            elif math.isclose(effective_stop, trailing_stop, rel_tol=1e-5) and trailing_stop > baseline_stop:
                reason = "LELAND_TRAILING_STOP"
                severity = "WARN"
            else:
                reason = "BASELINE_HARD_STOP_6PCT"
                severity = "CRITICAL"

            exit_qty = pos.current_quantity
            pos.current_quantity = 0

            action = RiskAction(
                action_id=f"RA_STOP_{pos.symbol}_{uuid.uuid4().hex[:8]}",
                symbol=pos.symbol,
                market=pos.market,
                action="SELL",
                quantity=exit_qty,
                ratio=1.0,
                trigger_price=effective_stop,
                current_price=current_price,
                stop_price=effective_stop,
                reason=reason,
                severity=severity,
                force_liquidate=True if severity == "CRITICAL" else False,
                details={
                    "effective_stop": effective_stop,
                    "baseline_stop": baseline_stop,
                    "trailing_stop": trailing_stop,
                    "breakeven_stop": breakeven_stop,
                    "ratchet_stop": ratchet_stop,
                    "leland_multiplier": leland_m,
                    "peak_price": resolved_peak,
                    "entry_price": pos.entry_price,
                    "volatility_20d": resolved_vol,
                    "momentum_factor": resolved_mom,
                },
            )
            self.executed_actions.append(action)
            return action

        return None

    # -----------------------------------------------------------------------
    # Flash-Crash Circuit Breakers
    # -----------------------------------------------------------------------

    def evaluate_asset_flash_crash(
        self,
        symbol: str,
        current_price: float,
        open_price: float,
        prev_close: float,
        market: str = "KOSPI",
        quantity: int = 0,
    ) -> Optional[RiskAction]:
        """Evaluate single-asset intraday flash crash drop >= 7.0% from max(open, prev_close)."""
        if not math.isfinite(current_price) or current_price <= 0.0:
            return None

        ref_price = max(
            float(open_price) if (math.isfinite(float(open_price)) and float(open_price) > 0) else 0.0,
            float(prev_close) if (math.isfinite(float(prev_close)) and float(prev_close) > 0) else 0.0,
        )
        if ref_price <= 0.0:
            return None

        drop_pct = (current_price - ref_price) / ref_price
        if drop_pct <= self.flash_crash_asset_drop_pct:
            pos = self.positions.get(str(symbol).strip())
            qty = quantity
            if qty <= 0 and pos is not None:
                qty = pos.current_quantity
            if pos is not None:
                pos.current_quantity = 0

            action = RiskAction(
                action_id=f"RA_CRASH_ASSET_{symbol}_{uuid.uuid4().hex[:8]}",
                symbol=symbol,
                market=market,
                action="SELL",
                quantity=max(1, qty) if qty > 0 else 1,
                ratio=1.0,
                trigger_price=ref_price,
                current_price=current_price,
                stop_price=current_price,
                reason="FLASH_CRASH_ASSET_DROP_7PCT",
                severity="CRITICAL",
                force_liquidate=True,
                is_hedge=False,
                details={
                    "drop_pct": drop_pct,
                    "threshold_pct": self.flash_crash_asset_drop_pct,
                    "reference_price": ref_price,
                    "open_price": open_price,
                    "prev_close": prev_close,
                },
            )
            self.executed_actions.append(action)
            return action

        return None

    def evaluate_macro_vix_surge(
        self,
        vix_current: Optional[float],
        vix_1h_ago: Optional[float],
        market: str = "KOSPI",
        capital: float = 100_000_000.0,
    ) -> Optional[RiskAction]:
        """Evaluate macro volatility surge: VIX surging > 20.0% within 1 hour.

        Emits Gate 8 synthetic inverse hedge order.
        """
        if vix_current is None or vix_1h_ago is None:
            return None
        try:
            curr_vix = float(vix_current)
            prev_vix = float(vix_1h_ago)
        except (ValueError, TypeError):
            return None

        if not math.isfinite(curr_vix) or not math.isfinite(prev_vix) or prev_vix <= 0.0:
            return None

        surge_pct = (curr_vix - prev_vix) / prev_vix
        if surge_pct > self.flash_crash_vix_surge_pct:
            instrument = self.resolve_hedge_instrument(market)
            # Default target hedge quantity
            approx_hedge_amount = float(capital) * 0.20
            unit_price = 10000.0 if str(instrument).isdigit() else 50.0
            hedge_qty = max(1, int(approx_hedge_amount / unit_price))

            action = RiskAction(
                action_id=f"RA_CRASH_VIX_{instrument}_{uuid.uuid4().hex[:8]}",
                symbol=instrument,
                market=market,
                action="BUY_HEDGE",
                quantity=hedge_qty,
                ratio=0.20,
                trigger_price=curr_vix,
                current_price=curr_vix,
                stop_price=0.0,
                reason="FLASH_CRASH_VIX_SURGE_20PCT",
                severity="CRITICAL",
                force_liquidate=False,
                is_hedge=True,
                target_hedge_instrument=instrument,
                details={
                    "vix_current": curr_vix,
                    "vix_1h_ago": prev_vix,
                    "surge_pct": surge_pct,
                    "threshold_pct": self.flash_crash_vix_surge_pct,
                    "hedge_instrument": instrument,
                },
            )
            self.executed_actions.append(action)
            return action

        return None

    def evaluate_flash_crash(
        self,
        symbol: str,
        current_price: float,
        open_price: float,
        prev_close: float,
        vix_current: Optional[float] = None,
        vix_1h_ago: Optional[float] = None,
        market: str = "KOSPI",
        quantity: int = 0,
    ) -> Optional[RiskAction]:
        """Unified flash-crash circuit breaker evaluator.

        Evaluates single-asset drop first; if not triggered, evaluates macro VIX surge.
        """
        asset_action = self.evaluate_asset_flash_crash(
            symbol=symbol,
            current_price=current_price,
            open_price=open_price,
            prev_close=prev_close,
            market=market,
            quantity=quantity,
        )
        if asset_action is not None:
            return asset_action

        if vix_current is not None and vix_1h_ago is not None:
            return self.evaluate_macro_vix_surge(
                vix_current=vix_current,
                vix_1h_ago=vix_1h_ago,
                market=market,
            )

        return None

    # -----------------------------------------------------------------------
    # Portfolio Batch Evaluation
    # -----------------------------------------------------------------------

    def evaluate_portfolio(
        self,
        holdings: Union[Dict[str, Any], List[Any]],
        market_data: Dict[str, Dict[str, float]],
        vix_data: Optional[Dict[str, float]] = None,
        capital: float = 100_000_000.0,
    ) -> List[RiskAction]:
        """Batch evaluate all positions in portfolio against market and VIX data.

        Returns
        -------
        List[RiskAction]
            List of structured risk actions generated during the cycle.
        """
        actions: List[RiskAction] = []

        # 1. Macro VIX Flash-Crash Check
        if vix_data:
            v_curr = vix_data.get("vix_current", vix_data.get("vix", None))
            v_1h = vix_data.get("vix_1h_ago", vix_data.get("vix_prev", None))
            macro_action = self.evaluate_macro_vix_surge(
                vix_current=v_curr,
                vix_1h_ago=v_1h,
                market=vix_data.get("market", "GLOBAL"),
                capital=capital,
            )
            if macro_action is not None:
                actions.append(macro_action)

        # 2. Iterate Holdings
        holding_list: List[Any] = []
        if isinstance(holdings, dict):
            for k, v in holdings.items():
                if isinstance(v, dict):
                    v_copy = dict(v)
                    v_copy.setdefault("symbol", k)
                    holding_list.append(v_copy)
                else:
                    holding_list.append(v)
        elif isinstance(holdings, (list, tuple)):
            holding_list = list(holdings)

        for h in holding_list:
            pos = self._extract_holding_fields(h)
            sym = pos.symbol
            m_info = market_data.get(sym, {})
            curr_p = float(m_info.get("current_price", m_info.get("price", m_info.get("close", pos.last_price))))
            open_p = float(m_info.get("open_price", m_info.get("open", curr_p)))
            prev_c = float(m_info.get("prev_close", m_info.get("previous_close", open_p)))
            vol = float(m_info.get("volatility_20d", m_info.get("volatility", pos.volatility_20d)))
            mom = float(m_info.get("momentum_factor", m_info.get("momentum", pos.momentum_factor)))
            peak = float(m_info.get("peak_price", pos.peak_price))

            # A. Single-asset flash crash check
            crash_action = self.evaluate_asset_flash_crash(
                symbol=sym,
                current_price=curr_p,
                open_price=open_p,
                prev_close=prev_c,
                market=pos.market,
                quantity=pos.current_quantity,
            )
            if crash_action is not None:
                actions.append(crash_action)
                continue

            # B. Profit taking check
            tp_action = self.evaluate_profit_taking(pos, current_price=curr_p)
            if tp_action is not None:
                actions.append(tp_action)

            # C. Trailing & Hard stop check
            stop_action = self.evaluate_leland_trailing_stop(
                pos,
                current_price=curr_p,
                peak_price=peak,
                volatility_20d=vol,
                momentum_factor=mom,
            )
            if stop_action is not None:
                actions.append(stop_action)

        return actions


# ---------------------------------------------------------------------------
# Backward Compatibility & Alias Trees
# ---------------------------------------------------------------------------

IntradayRiskMonitor = InstitutionalIntradayRiskMonitor
Phase106IntradayRiskMonitor = InstitutionalIntradayRiskMonitor
FlashCrashCircuitBreaker = InstitutionalIntradayRiskMonitor
