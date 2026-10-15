"""
src/risk/borrow_dynamics_model.py
Release R127 / Phase 111 Production Master / v118 (Feature F527).

Institutional Short Squeeze Borrow Dynamics & Hard-to-Borrow (HTB) Fee Modeling:
1. Dynamic Non-Linear Loan Utilization Curve: U(t) = Loan Shares / Lendable Shares.
2. Dynamic Borrow Fee Rate Formulation:
   f_borrow(t) = f_GC + alpha_util * (U / (1 - U + epsilon))^gamma_util + beta_dep * max(0, v_dep).
3. SEC Rule 203(b)(1) Affirmative Locate Availability & Inventory Depletion Velocity.
4. Calibrated Multi-Factor Recall Risk Logistic Model.
5. Days-to-Cover (DTC) and Short Interest Ratio (SIR) Diagnostics.
6. Negative Carry Drag Subtraction and Short Hurdle Economic Viability.
7. Explosive Short Squeeze Catalyst Trigger (Composite Squeeze Score S_squeeze >= 0.75).
8. ExecutionOMSEngine Gate 8.1 (Short Squeeze Guard & Borrow Liquidity Gate) evaluation.
9. Comprehensive Alias Trees and Version Metadata (VERSION = 111, RELEASE = "R127").
"""

from __future__ import annotations

import logging
import math
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


# =============================================================================
# Data Structures & Result Containers
# =============================================================================

@dataclass
class BorrowFeeQuote:
    """
    Standard securities lending borrow fee and inventory quote.
    """
    symbol: str
    market: str = "SP500"
    borrow_fee_annual: float = 0.005           # Annual borrow fee (e.g. 0.045 = 4.5%)
    utilization_rate: float = 0.0              # U(t) in [0.0, 1.0]
    lendable_shares: float = 0.0               # Total inventory available to lend
    shares_on_loan: float = 0.0                # Shares currently borrowed / on loan
    locate_available: bool = True              # SEC Rule 203(b)(1) locate flag
    locate_fraction: float = 1.0               # Availability score in [0.0, 1.0]
    days_to_cover: float = 0.0                 # Short Interest / ADV20
    short_interest_ratio: float = 0.0          # Short Interest / Float
    depletion_velocity: float = 0.0            # dU/dt (day^-1)
    recall_risk_score: float = 0.0             # Logistic recall probability in [0.0, 1.0]
    is_hard_to_borrow: bool = False            # True if fee >= 10% or U >= 85%
    timestamp: float = field(default_factory=time.time)

    @property
    def is_gc(self) -> bool:
        """True if asset trades at General Collateral fee rates."""
        return not self.is_hard_to_borrow

    def to_dict(self) -> Dict[str, Any]:
        """Serializes quote to standard dictionary."""
        return {
            "symbol": self.symbol,
            "market": self.market,
            "borrow_fee_annual": float(self.borrow_fee_annual),
            "utilization_rate": float(self.utilization_rate),
            "lendable_shares": float(self.lendable_shares),
            "shares_on_loan": float(self.shares_on_loan),
            "locate_available": bool(self.locate_available),
            "locate_fraction": float(self.locate_fraction),
            "days_to_cover": float(self.days_to_cover),
            "short_interest_ratio": float(self.short_interest_ratio),
            "depletion_velocity": float(self.depletion_velocity),
            "recall_risk_score": float(self.recall_risk_score),
            "is_hard_to_borrow": bool(self.is_hard_to_borrow),
            "timestamp": float(self.timestamp),
        }


# BorrowState is a full interoperability alias for BorrowFeeQuote
BorrowState = BorrowFeeQuote


@dataclass
class LocateResult:
    """
    Result of an affirmative locate verification query under SEC Rule 203(b)(1).
    """
    symbol: str
    requested_shares: float
    locate_approved: bool
    available_shares: float
    locate_id: str
    locate_fraction: float
    timestamp: float = field(default_factory=time.time)
    borrow_fee_annual: float = 0.005
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "requested_shares": float(self.requested_shares),
            "locate_approved": bool(self.locate_approved),
            "available_shares": float(self.available_shares),
            "locate_id": self.locate_id,
            "locate_fraction": float(self.locate_fraction),
            "timestamp": float(self.timestamp),
            "borrow_fee_annual": float(self.borrow_fee_annual),
            "reason": self.reason,
        }


@dataclass
class NegativeCarryResult:
    """
    Detailed negative carry analysis for short positions.
    """
    daily_cost_bps: float
    holding_period_cost: float
    gross_alpha: float
    net_alpha: float
    is_economically_viable: bool
    annual_borrow_fee: float = 0.005


@dataclass
class SqueezeEvaluationResult:
    """
    Output of the explosive short squeeze catalyst detector.
    """
    symbol: str
    market: str
    squeeze_score: float                       # S_squeeze in [0.0, 1.0]
    is_squeeze_triggered: bool                 # True if S_squeeze >= 0.75
    negative_carry_bps: float                  # Daily carry cost in bps
    net_alpha_after_carry: float               # Gross alpha minus borrow drag
    recall_risk: float                         # Recall risk score in [0.0, 1.0]
    recommended_action: str                    # "PASS" | "BLOCK_SHORT" | "ACCELERATE_LONG" | "RECALL_COVER"
    gate_8_1_status: str                       # "APPROVED" | "REJECTED" | "MODIFIED"
    rejection_reason: Optional[str] = None
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "market": self.market,
            "squeeze_score": float(self.squeeze_score),
            "is_squeeze_triggered": bool(self.is_squeeze_triggered),
            "negative_carry_bps": float(self.negative_carry_bps),
            "net_alpha_after_carry": float(self.net_alpha_after_carry),
            "recall_risk": float(self.recall_risk),
            "recommended_action": self.recommended_action,
            "gate_8_1_status": self.gate_8_1_status,
            "rejection_reason": self.rejection_reason,
            "timestamp": float(self.timestamp),
        }


@dataclass
class Gate8_1Verdict:
    """
    Decision verdict from ExecutionOMSEngine Gate 8.1 (Short Squeeze & Borrow Liquidity Gate).
    """
    symbol: str
    action: str                                # "BUY" | "SELL" | "SHORT" | "SELL_SHORT" | "CASH_OVERLAY"
    status: str                                # "APPROVED" | "REJECTED" | "MODIFIED"
    reason: Optional[str] = None               # Rejection / modification explanation code
    recommended_sleeve: str = "CORE"           # "CORE" | "MOMENTUM_SQUEEZE" | "DEFENSIVE_SHORT" | "CASH_OVERLAY"
    recommended_exec_strategy: str = "DIRECT"  # "DIRECT" | "AGGRESSIVE_TAKER" | "FAST_LIMIT" | "PASSIVE_LIMIT"
    target_stop_loss: Optional[float] = None   # Adjusted protective stop level
    target_price_adjustment: float = 1.0       # Limit price adjustment factor
    slice_count_multiplier: float = 1.0        # Tranche slicing acceleration
    borrow_quote: Optional[BorrowFeeQuote] = None
    squeeze_eval: Optional[SqueezeEvaluationResult] = None
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "action": self.action,
            "status": self.status,
            "reason": self.reason,
            "recommended_sleeve": self.recommended_sleeve,
            "recommended_exec_strategy": self.recommended_exec_strategy,
            "target_stop_loss": self.target_stop_loss,
            "target_price_adjustment": float(self.target_price_adjustment),
            "slice_count_multiplier": float(self.slice_count_multiplier),
            "borrow_quote": self.borrow_quote.to_dict() if self.borrow_quote else None,
            "squeeze_eval": self.squeeze_eval.to_dict() if self.squeeze_eval else None,
            "timestamp": float(self.timestamp),
        }


# =============================================================================
# Core Engine: BorrowDynamicsModel
# =============================================================================

class BorrowDynamicsModel:
    """
    Institutional Short Squeeze Borrow Dynamics & Hard-to-Borrow (HTB) Fee Engine.
    Release R127 / Phase 111 Production Master (Feature F527).
    """
    VERSION: int = 111
    RELEASE: str = "R127"

    # Market Base General Collateral (GC) Annual Rates
    MARKET_GC_RATES: Dict[str, float] = {
        "SP500": 0.0030,        # 30 bps base US Large-Cap
        "NASDAQ": 0.0040,       # 40 bps base US Tech
        "RUSSELL2000": 0.0060,  # 60 bps base US Small-Cap
        "KOSPI": 0.0100,        # 100 bps base KRX Main Board
        "KOSDAQ": 0.0120,       # 120 bps base KRX Tech/Growth
        "DEFAULT": 0.0050,      # 50 bps baseline fallback
    }

    def __init__(
        self,
        default_gc_rate: Optional[float] = None,
        alpha_util: float = 0.015,
        gamma_util: float = 1.75,
        epsilon_util: float = 0.02,
        beta_depletion: float = 0.10,
        htb_fee_threshold: float = 0.10,
        htb_util_threshold: float = 0.85,
        squeeze_trigger_threshold: float = 0.75,
        squeeze_block_threshold: float = 0.70,
        min_net_alpha_hurdle: float = 0.0010,   # 10 bps minimum net hurdle
        version: int = 111,
    ) -> None:
        """
        Initializes the institutional borrow dynamics engine.

        Args:
            default_gc_rate: Custom baseline GC annual rate (None = market-specific)
            alpha_util: Non-linear fee ascent coefficient
            gamma_util: Utilization exponent
            epsilon_util: Boundary denominator stabilizer (prevents division by zero at U=1.0)
            beta_depletion: Depletion velocity fee markup factor
            htb_fee_threshold: Fee rate threshold for HTB classification (0.10 = 10%)
            htb_util_threshold: Utilization threshold for HTB classification (0.85 = 85%)
            squeeze_trigger_threshold: S_squeeze score threshold to trigger long momentum squeeze
            squeeze_block_threshold: S_squeeze score threshold to block new short sales
            min_net_alpha_hurdle: Minimum net expected alpha hurdle after borrow carry drag
            version: Production version (111)
        """
        self.default_gc_rate = default_gc_rate
        self.alpha_util = float(alpha_util)
        self.gamma_util = float(gamma_util)
        self.epsilon_util = float(epsilon_util)
        self.beta_depletion = float(beta_depletion)
        self.htb_fee_threshold = float(htb_fee_threshold)
        self.htb_util_threshold = float(htb_util_threshold)
        self.squeeze_trigger_threshold = float(squeeze_trigger_threshold)
        self.squeeze_block_threshold = float(squeeze_block_threshold)
        self.min_net_alpha_hurdle = float(min_net_alpha_hurdle)
        self.version = int(version)

        # Internal stateful ledger for SEC Rule 203(b)(1) affirmative locate compliance tracking
        self._locate_ledger: Dict[str, List[LocateResult]] = {}

    # -------------------------------------------------------------------------
    # 1. Non-Linear Loan Utilization Curve
    # -------------------------------------------------------------------------
    def calculate_loan_utilization(
        self,
        shares_on_loan: float,
        lendable_inventory: float,
    ) -> float:
        """
        Computes the loan utilization curve U(t) in [0.0, 1.0].
        U(t) = Shares on Loan / Total Lendable Inventory.

        Handles degenerate boundaries:
        - lendable_inventory <= 0 and shares_on_loan > 0: saturated (1.0)
        - lendable_inventory <= 0 and shares_on_loan <= 0: empty (0.0)
        """
        # Infinite lendable inventory yields zero loan utilization
        if math.isinf(lendable_inventory) and lendable_inventory > 0:
            return 0.0

        loan = float(shares_on_loan) if math.isfinite(shares_on_loan) else 0.0
        lendable = float(lendable_inventory) if math.isfinite(lendable_inventory) else 0.0

        if lendable <= 0.0:
            return 1.0 if loan > 0.0 else 0.0

        if loan <= 0.0:
            return 0.0

        u = loan / lendable
        return float(np.clip(u, 0.0, 1.0))

    # -------------------------------------------------------------------------
    # 2. Dynamic Borrow Inventory Depletion Velocity
    # -------------------------------------------------------------------------
    def calculate_inventory_depletion_velocity(
        self,
        historical_utilization: Union[List[float], np.ndarray, float],
        dt_days: float = 1.0,
    ) -> float:
        """
        Computes the rate of loan inventory depletion v_dep(t) in day^-1.
        v_dep(t) = (U(t) - U(t - Delta t)) / Delta t.

        Accepts:
        - Float: scalar velocity provided directly.
        - List/Array: historical utilization series.
        """
        if isinstance(historical_utilization, (int, float)):
            val = float(historical_utilization)
            return val if math.isfinite(val) else 0.0

        arr = np.asarray(historical_utilization, dtype=float).flatten()
        arr = arr[np.isfinite(arr)]
        if len(arr) < 2:
            return 0.0

        dt = float(dt_days) if dt_days > 0 else 1.0
        # If multiple points, compute delta over the window or latest step
        delta = float(arr[-1] - arr[0]) / max(1.0, (len(arr) - 1) * dt)
        return float(np.clip(delta, -1.0, 2.0))

    # -------------------------------------------------------------------------
    # 3. Dynamic Borrow Fee Rate Formulation
    # -------------------------------------------------------------------------
    def calculate_borrow_fee(
        self,
        utilization: float,
        market: str = "SP500",
        depletion_velocity: float = 0.0,
        is_gc: bool = False,
    ) -> float:
        """
        Calculates dynamic annual borrow fee rate f_borrow(t):
        f_borrow(t) = f_GC + alpha_util * (U / (1 - U + epsilon))^gamma_util + beta_dep * max(0, v_dep).

        When U -> 1.0, the non-linear denominator drives explosive HTB fee expansion.
        """
        u = float(np.clip(utilization, 0.0, 1.0))

        # Determine General Collateral base rate
        if self.default_gc_rate is not None:
            f_gc = self.default_gc_rate
        else:
            f_gc = self.MARKET_GC_RATES.get(market.upper(), self.MARKET_GC_RATES["DEFAULT"])

        if is_gc or u < 0.60:
            # Under unconstrained regime, borrow fee equals base GC rate
            return float(f_gc)

        # Non-linear utilization penalty
        denom = 1.0 - u + self.epsilon_util
        scaled_ratio = u / max(1e-6, denom)
        util_penalty = self.alpha_util * (scaled_ratio ** self.gamma_util)

        # Depletion surge markup
        dep_velocity = max(0.0, float(depletion_velocity))
        dep_markup = self.beta_depletion * dep_velocity

        total_fee = f_gc + util_penalty + dep_markup
        return float(max(f_gc, total_fee))

    # -------------------------------------------------------------------------
    # 4. Affirmative Locate Availability (SEC Rule 203(b)(1))
    # -------------------------------------------------------------------------
    def check_locate_availability(
        self,
        symbol: str,
        requested_shares: float = 1.0,
        lendable_shares: float = 1_000_000.0,
        shares_on_loan: float = 0.0,
        depletion_velocity: float = 0.0,
        market: str = "SP500",
    ) -> LocateResult:
        """
        Verifies affirmative locate eligibility under SEC Rule 203(b)(1).
        L_avail(t) = max(0.0, 1.0 - U(t)/0.98) * exp(-2.5 * max(0, v_dep)).

        If U(t) >= 0.98 or L_avail < 0.02, locate is strictly rejected.
        """
        req_shares = max(0.0, float(requested_shares))
        u = self.calculate_loan_utilization(shares_on_loan, lendable_shares)
        v_dep = max(0.0, float(depletion_velocity))

        # Continuous availability score
        if u >= 0.98:
            l_avail = 0.0
        else:
            base_decay = max(0.0, 1.0 - (u / 0.98))
            velocity_drag = math.exp(-2.5 * v_dep)
            l_avail = base_decay * velocity_drag

        l_avail = float(np.clip(l_avail, 0.0, 1.0))

        # Effective lendable shares remaining
        remaining_pool = max(0.0, float(lendable_shares) - float(shares_on_loan))
        available_shares = remaining_pool * l_avail

        borrow_fee = self.calculate_borrow_fee(
            utilization=u,
            market=market,
            depletion_velocity=v_dep,
        )

        # Rule 203(b)(1) approval decision
        if u >= 0.98:
            approved = False
            reason = f"Inventory saturated: utilization={u:.2%} >= 98.0%"
        elif l_avail < 0.02:
            approved = False
            reason = f"Locate pool exhausted: availability score={l_avail:.4f} < 0.02"
        elif req_shares > 0 and req_shares > available_shares:
            approved = False
            reason = f"Insufficient lendable volume: requested {req_shares:,.0f} > available {available_shares:,.0f}"
        else:
            approved = True
            reason = f"Affirmative locate confirmed ({available_shares:,.0f} shares available at {borrow_fee:.2%} p.a.)"

        locate_id = f"LOC_{symbol}_{int(time.time() * 1000)}_{uuid.uuid4().hex[:6].upper()}"

        result = LocateResult(
            symbol=symbol,
            requested_shares=req_shares,
            locate_approved=approved,
            available_shares=available_shares,
            locate_id=locate_id,
            locate_fraction=l_avail,
            borrow_fee_annual=borrow_fee,
            reason=reason,
        )

        # Audit ledger logging
        if symbol not in self._locate_ledger:
            self._locate_ledger[symbol] = []
        self._locate_ledger[symbol].append(result)

        return result

    # -------------------------------------------------------------------------
    # 5. Days-to-Cover (DTC) and Short Interest Ratio (SIR)
    # -------------------------------------------------------------------------
    def calculate_short_interest_metrics(
        self,
        short_interest_shares: float,
        public_float_shares: float,
        adv_20d: float,
    ) -> Tuple[float, float]:
        """
        Calculates:
        1. SIR (Short Interest Ratio) = Short Interest / Public Float in [0.0, 1.0]
        2. DTC (Days to Cover) = Short Interest / ADV_20d in days
        """
        si = max(0.0, float(short_interest_shares)) if math.isfinite(short_interest_shares) else 0.0
        flt = max(0.0, float(public_float_shares)) if math.isfinite(public_float_shares) else 0.0
        adv = max(0.0, float(adv_20d)) if math.isfinite(adv_20d) else 0.0

        sir = float(np.clip(si / flt, 0.0, 1.0)) if flt > 0.0 else 0.0
        dtc = float(si / adv) if adv > 0.0 else (99.0 if si > 0.0 else 0.0)

        return sir, dtc

    # -------------------------------------------------------------------------
    # 6. Multi-Factor Recall Risk Scoring (Logistic Model)
    # -------------------------------------------------------------------------
    def calculate_recall_risk_score(
        self,
        utilization: float,
        depletion_velocity: float = 0.0,
        dtc: float = 0.0,
        upward_momentum: float = 0.0,
    ) -> float:
        """
        Evaluates prime broker borrow recall risk R_recall(t) via calibrated logistic model:
        z_recall = w_u * (U - 0.85)/0.10 + w_v * (v_dep/0.05) + w_dtc * (DTC - 5.0)/3.0 + w_mom * max(0, 5 * r_5d)
        R_recall(t) = 1 / (1 + exp(-z_recall)).
        """
        u = float(np.clip(utilization, 0.0, 1.0))
        v = float(depletion_velocity)
        d = max(0.0, float(dtc))
        r5 = float(upward_momentum)

        # Calibrated model weights (sum = 1.0)
        w_u = 0.35
        w_v = 0.25
        w_dtc = 0.20
        w_mom = 0.20

        z = (
            w_u * ((u - 0.85) / 0.10)
            + w_v * (v / 0.05)
            + w_dtc * ((d - 5.0) / 3.0)
            + w_mom * max(0.0, 5.0 * r5)
        )

        # Numerically stable sigmoid
        if z >= 30.0:
            return 1.0
        elif z <= -30.0:
            return 0.0
        else:
            return float(1.0 / (1.0 + math.exp(-z)))

    # -------------------------------------------------------------------------
    # 7. Negative Carry Drag Subtraction
    # -------------------------------------------------------------------------
    def calculate_negative_carry(
        self,
        borrow_fee_annual: float,
        position_value: float = 1.0,
        holding_days: float = 20.0,
        expected_alpha: float = 0.0,
        hurdle_rate: Optional[float] = None,
    ) -> NegativeCarryResult:
        """
        Quantifies holding drag and net alpha viability after borrow costs:
        - Daily carry cost = (f_borrow / 365) * 10,000 bps
        - Total holding drag = f_borrow * (holding_days / 252)
        - Net alpha = expected_alpha - holding_drag
        """
        fee = max(0.0, float(borrow_fee_annual))
        h_days = max(1.0, float(holding_days))
        alpha = float(expected_alpha)
        hurdle = hurdle_rate if hurdle_rate is not None else self.min_net_alpha_hurdle

        daily_bps = (fee / 365.0) * 10000.0
        holding_drag = fee * (h_days / 252.0)
        net_alpha = alpha - holding_drag
        is_viable = net_alpha > hurdle

        return NegativeCarryResult(
            daily_cost_bps=daily_bps,
            holding_period_cost=holding_drag,
            gross_alpha=alpha,
            net_alpha=net_alpha,
            is_economically_viable=is_viable,
            annual_borrow_fee=fee,
        )

    # -------------------------------------------------------------------------
    # 8. Explosive Short Squeeze Catalyst Trigger
    # -------------------------------------------------------------------------
    def calculate_squeeze_score(
        self,
        sir: float,
        dtc: float,
        utilization: float,
        upward_momentum: float = 0.0,
        relative_volume: float = 1.0,
    ) -> float:
        """
        Computes composite short squeeze score S_squeeze in [0.0, 1.0]:
        S_squeeze = clip(0.25*(SIR/0.25) + 0.20*(DTC/6.0) + 0.20*(U/0.90) + 0.20*tanh(4*r_5d) + 0.15*min(2.0, RVOL/1.5), 0.0, 1.0)
        """
        s_sir = max(0.0, float(sir))
        s_dtc = max(0.0, float(dtc))
        s_u = float(np.clip(utilization, 0.0, 1.0))
        s_mom = float(upward_momentum)
        s_rvol = max(0.0, float(relative_volume))

        score = (
            0.25 * (s_sir / 0.25)
            + 0.20 * (s_dtc / 6.0)
            + 0.20 * (s_u / 0.90)
            + 0.20 * math.tanh(4.0 * s_mom)
            + 0.15 * min(2.0, s_rvol / 1.5)
        )
        return float(np.clip(score, 0.0, 1.0))

    # -------------------------------------------------------------------------
    # 9. Comprehensive Borrow State & Quote Evaluation
    # -------------------------------------------------------------------------
    def evaluate_borrow_quote(
        self,
        symbol: str,
        market: str = "SP500",
        loan_shares: float = 0.0,
        lendable_shares: float = 1_000_000.0,
        dtc: Optional[float] = None,
        sir: Optional[float] = None,
        short_interest_shares: Optional[float] = None,
        public_float_shares: Optional[float] = None,
        adv_20d: Optional[float] = None,
        historical_utilization: Optional[Union[List[float], np.ndarray, float]] = None,
        upward_momentum: float = 0.0,
    ) -> BorrowFeeQuote:
        """
        Evaluates full securities lending borrow fee quote and availability metrics.
        """
        u = self.calculate_loan_utilization(loan_shares, lendable_shares)
        v_dep = self.calculate_inventory_depletion_velocity(
            historical_utilization if historical_utilization is not None else 0.0
        )

        # Derive SIR and DTC if not passed directly
        if sir is None or dtc is None:
            if short_interest_shares is not None:
                flt = public_float_shares if public_float_shares is not None else lendable_shares
                adv = adv_20d if adv_20d is not None else 100_000.0
                calc_sir, calc_dtc = self.calculate_short_interest_metrics(
                    short_interest_shares=short_interest_shares,
                    public_float_shares=flt,
                    adv_20d=adv,
                )
                sir_val = sir if sir is not None else calc_sir
                dtc_val = dtc if dtc is not None else calc_dtc
            else:
                sir_val = sir if sir is not None else 0.05
                dtc_val = dtc if dtc is not None else 2.0
        else:
            sir_val = float(sir)
            dtc_val = float(dtc)

        locate_res = self.check_locate_availability(
            symbol=symbol,
            requested_shares=0.0,
            lendable_shares=lendable_shares,
            shares_on_loan=loan_shares,
            depletion_velocity=v_dep,
            market=market,
        )

        borrow_fee = self.calculate_borrow_fee(
            utilization=u,
            market=market,
            depletion_velocity=v_dep,
        )

        recall_risk = self.calculate_recall_risk_score(
            utilization=u,
            depletion_velocity=v_dep,
            dtc=dtc_val,
            upward_momentum=upward_momentum,
        )

        is_htb = (borrow_fee >= self.htb_fee_threshold) or (u >= self.htb_util_threshold)

        return BorrowFeeQuote(
            symbol=symbol,
            market=market,
            borrow_fee_annual=borrow_fee,
            utilization_rate=u,
            lendable_shares=lendable_shares,
            shares_on_loan=loan_shares,
            locate_available=locate_res.locate_approved,
            locate_fraction=locate_res.locate_fraction,
            days_to_cover=dtc_val,
            short_interest_ratio=sir_val,
            depletion_velocity=v_dep,
            recall_risk_score=recall_risk,
            is_hard_to_borrow=is_htb,
        )

    def evaluate_borrow_state(
        self,
        symbol: str,
        market: str = "SP500",
        short_interest: float = 0.0,
        float_shares: float = 1_000_000.0,
        loan_shares: float = 0.0,
        lendable_shares: float = 1_000_000.0,
        adv_30d: float = 100_000.0,
        upward_mom_5d: float = 0.0,
    ) -> BorrowState:
        """
        Interface contract alias adhering to SCOPE.md specification.
        """
        return self.evaluate_borrow_quote(
            symbol=symbol,
            market=market,
            loan_shares=loan_shares,
            lendable_shares=lendable_shares,
            short_interest_shares=short_interest,
            public_float_shares=float_shares,
            adv_20d=adv_30d,
            upward_momentum=upward_mom_5d,
        )

    # -------------------------------------------------------------------------
    # 10. Comprehensive Short Squeeze Catalyst Evaluation
    # -------------------------------------------------------------------------
    def evaluate_squeeze_catalyst(
        self,
        symbol: str,
        market: str = "SP500",
        borrow_quote: Optional[BorrowFeeQuote] = None,
        price_history: Optional[Union[List[float], np.ndarray, pd.Series]] = None,
        volume_history: Optional[Union[List[float], np.ndarray, pd.Series]] = None,
        expected_alpha: float = 0.0,
        holding_days: float = 20.0,
        upward_momentum: Optional[float] = None,
        relative_volume: Optional[float] = None,
    ) -> SqueezeEvaluationResult:
        """
        Evaluates composite squeeze score and negative carry for an asset.
        """
        quote = borrow_quote if borrow_quote is not None else self.evaluate_borrow_quote(symbol, market)

        # Derive momentum and RVOL from histories if not explicitly passed
        mom = 0.0
        if upward_momentum is not None:
            mom = float(upward_momentum)
        elif price_history is not None:
            px = np.asarray(price_history, dtype=float).flatten()
            px = px[np.isfinite(px)]
            if len(px) >= 6 and px[-6] > 0:
                mom = float((px[-1] - px[-6]) / px[-6])
            elif len(px) >= 2 and px[0] > 0:
                mom = float((px[-1] - px[0]) / px[0])

        rvol = 1.0
        if relative_volume is not None:
            rvol = float(relative_volume)
        elif volume_history is not None:
            vol = np.asarray(volume_history, dtype=float).flatten()
            vol = vol[np.isfinite(vol)]
            if len(vol) >= 20 and np.mean(vol[-20:]) > 0:
                recent_5d = np.mean(vol[-5:]) if len(vol) >= 5 else vol[-1]
                rvol = float(recent_5d / np.mean(vol[-20:]))

        squeeze_score = self.calculate_squeeze_score(
            sir=quote.short_interest_ratio,
            dtc=quote.days_to_cover,
            utilization=quote.utilization_rate,
            upward_momentum=mom,
            relative_volume=rvol,
        )

        is_triggered = squeeze_score >= self.squeeze_trigger_threshold

        carry_analysis = self.calculate_negative_carry(
            borrow_fee_annual=quote.borrow_fee_annual,
            holding_days=holding_days,
            expected_alpha=expected_alpha,
        )

        # Recommended Action & OMS Gate Status
        rejection_reason: Optional[str] = None
        if not quote.locate_available or quote.locate_fraction <= 0.02:
            recommended_action = "BLOCK_SHORT"
            gate_status = "REJECTED"
            rejection_reason = "NO_AFFIRMATIVE_LOCATE"
        elif is_triggered or (squeeze_score >= self.squeeze_block_threshold and mom > 0.02):
            recommended_action = "BLOCK_SHORT"
            gate_status = "REJECTED"
            rejection_reason = "SHORT_SQUEEZE_BREAKOUT_RISK"
        elif quote.recall_risk_score >= 0.80:
            recommended_action = "RECALL_COVER"
            gate_status = "REJECTED"
            rejection_reason = "ACUTE_RECALL_RISK"
        elif carry_analysis.net_alpha <= self.min_net_alpha_hurdle:
            recommended_action = "BLOCK_SHORT"
            gate_status = "REJECTED"
            rejection_reason = "NEGATIVE_CARRY_DRAG"
        else:
            recommended_action = "PASS"
            gate_status = "APPROVED"

        return SqueezeEvaluationResult(
            symbol=symbol,
            market=market,
            squeeze_score=squeeze_score,
            is_squeeze_triggered=is_triggered,
            negative_carry_bps=carry_analysis.daily_cost_bps,
            net_alpha_after_carry=carry_analysis.net_alpha,
            recall_risk=quote.recall_risk_score,
            recommended_action=recommended_action,
            gate_8_1_status=gate_status,
            rejection_reason=rejection_reason,
        )

    # -------------------------------------------------------------------------
    # 11. ExecutionOMSEngine Gate 8.1 Integration
    # -------------------------------------------------------------------------
    def evaluate_gate_8_1(
        self,
        order: Union[Dict[str, Any], Any],
        borrow_quote: Optional[BorrowFeeQuote] = None,
        squeeze_eval: Optional[SqueezeEvaluationResult] = None,
        net_alpha_bps: Optional[float] = None,
        hurdle_rate_bps: float = 10.0,
    ) -> Gate8_1Verdict:
        """
        Executes Gate 8.1 (Short Squeeze Guard & Borrow Liquidity Gate) for an order:
        - Check 1: Affirmative Locate Verification (SEC Rule 203(b)(1))
        - Check 2: Hard-to-Borrow Negative Carry Drag
        - Check 3: Short Squeeze Avalanche Blocking (S_squeeze >= 0.70)
        - Check 4: Acute Recall Risk (R_recall >= 0.80)
        - Check 5: Long Squeeze Acceleration (S_squeeze >= 0.75 -> MOMENTUM_SQUEEZE sleeve)
        """
        # Normalize order attributes
        if isinstance(order, dict):
            sym = str(order.get("symbol", "") or "")
            action = str(order.get("action", "") or "BUY").upper()
            market = str(order.get("market", "") or "SP500")
            target_price = order.get("target_price")
            exp_ret = float(order.get("expected_return", order.get("ensemble_expected_return", 0.0)) or 0.0)
            is_explicit_short = bool(order.get("is_short", False) or action in ["SHORT", "SELL_SHORT"])
        else:
            sym = getattr(order, "symbol", "")
            action = str(getattr(order, "action", "BUY")).upper()
            market = str(getattr(order, "market", "SP500"))
            target_price = getattr(order, "target_price", None)
            exp_ret = float(getattr(order, "expected_return", 0.0) or 0.0)
            is_explicit_short = bool(getattr(order, "is_short", False) or action in ["SHORT", "SELL_SHORT"])

        # Fetch / compute quotes if absent
        b_quote = borrow_quote if borrow_quote is not None else self.evaluate_borrow_quote(sym, market)
        s_eval = squeeze_eval if squeeze_eval is not None else self.evaluate_squeeze_catalyst(
            sym, market, borrow_quote=b_quote, expected_alpha=exp_ret
        )

        hurdle = (hurdle_rate_bps / 10000.0) if hurdle_rate_bps is not None else self.min_net_alpha_hurdle
        alpha_val = (net_alpha_bps / 10000.0) if net_alpha_bps is not None else s_eval.net_alpha_after_carry

        # --- A. Short Order Gating ---
        if is_explicit_short or action in ["SHORT", "SELL_SHORT"]:
            # Check 1: SEC Rule 203(b)(1) Affirmative Locate
            if not b_quote.locate_available or b_quote.locate_fraction <= 0.02:
                logger.warning(
                    f"[OMS GATE 8.1] {sym} Short order REJECTED: No affirmative locate available "
                    f"(utilization={b_quote.utilization_rate:.1%}, locate_fraction={b_quote.locate_fraction:.4f})."
                )
                return Gate8_1Verdict(
                    symbol=sym,
                    action=action,
                    status="REJECTED",
                    reason="NO_AFFIRMATIVE_LOCATE",
                    recommended_sleeve="CASH_OVERLAY",
                    recommended_exec_strategy="DIRECT",
                    borrow_quote=b_quote,
                    squeeze_eval=s_eval,
                )

            # Check 2: Short Squeeze Avalanche Blocking
            if s_eval.is_squeeze_triggered or s_eval.squeeze_score >= self.squeeze_block_threshold:
                logger.warning(
                    f"[OMS GATE 8.1] {sym} Short order BLOCKED: High Short Squeeze Risk "
                    f"(score={s_eval.squeeze_score:.2f}, DTC={b_quote.days_to_cover:.1f})."
                )
                return Gate8_1Verdict(
                    symbol=sym,
                    action=action,
                    status="REJECTED",
                    reason="SHORT_SQUEEZE_BREAKOUT_RISK",
                    recommended_sleeve="CASH_OVERLAY",
                    recommended_exec_strategy="DIRECT",
                    borrow_quote=b_quote,
                    squeeze_eval=s_eval,
                )

            # Check 3: Acute Recall Risk
            if b_quote.recall_risk_score >= 0.80:
                logger.warning(
                    f"[OMS GATE 8.1] {sym} Short order REJECTED: Acute borrow recall risk "
                    f"(recall_score={b_quote.recall_risk_score:.2f} >= 0.80)."
                )
                return Gate8_1Verdict(
                    symbol=sym,
                    action=action,
                    status="REJECTED",
                    reason="ACUTE_RECALL_RISK",
                    recommended_sleeve="CASH_OVERLAY",
                    recommended_exec_strategy="DIRECT",
                    borrow_quote=b_quote,
                    squeeze_eval=s_eval,
                )

            # Check 4: Excessive Negative Carry Drag Hurdle
            if alpha_val <= hurdle:
                logger.warning(
                    f"[OMS GATE 8.1] {sym} Short order REJECTED: Excessive HTB borrow fee "
                    f"({b_quote.borrow_fee_annual:.2%}) yields negative net alpha ({alpha_val:.4%})."
                )
                return Gate8_1Verdict(
                    symbol=sym,
                    action=action,
                    status="REJECTED",
                    reason="NEGATIVE_CARRY_DRAG",
                    recommended_sleeve="CASH_OVERLAY",
                    recommended_exec_strategy="DIRECT",
                    borrow_quote=b_quote,
                    squeeze_eval=s_eval,
                )

            # Approved Short Order
            return Gate8_1Verdict(
                symbol=sym,
                action=action,
                status="APPROVED",
                reason=None,
                recommended_sleeve="DEFENSIVE_SHORT",
                recommended_exec_strategy="FAST_LIMIT",
                borrow_quote=b_quote,
                squeeze_eval=s_eval,
            )

        # --- B. Buy Order Handling ---
        elif action in ["BUY", "LONG"]:
            # Check 5: Long Squeeze Acceleration
            if s_eval.is_squeeze_triggered or s_eval.squeeze_score >= self.squeeze_trigger_threshold:
                logger.info(
                    f"[OMS GATE 8.1] {sym} Explosive Short Squeeze Catalyst detected "
                    f"(score={s_eval.squeeze_score:.2f}). Upgrading to MOMENTUM_SQUEEZE sleeve."
                )
                exec_strat = "AGGRESSIVE_TAKER" if b_quote.depletion_velocity > 0.05 else "FAST_LIMIT"
                stop_loss = (float(target_price) * 0.95) if target_price is not None else None

                return Gate8_1Verdict(
                    symbol=sym,
                    action=action,
                    status="MODIFIED",
                    reason=None,
                    recommended_sleeve="MOMENTUM_SQUEEZE",
                    recommended_exec_strategy=exec_strat,
                    target_stop_loss=stop_loss,
                    slice_count_multiplier=0.5,  # Accelerate slicing execution
                    borrow_quote=b_quote,
                    squeeze_eval=s_eval,
                )

            # Standard Long Buy Order
            return Gate8_1Verdict(
                symbol=sym,
                action=action,
                status="APPROVED",
                reason=None,
                recommended_sleeve="CORE",
                recommended_exec_strategy="DIRECT",
                borrow_quote=b_quote,
                squeeze_eval=s_eval,
            )

        # Standard Sell / Exit Order
        return Gate8_1Verdict(
            symbol=sym,
            action=action,
            status="APPROVED",
            reason=None,
            recommended_sleeve="CORE",
            recommended_exec_strategy="DIRECT",
            borrow_quote=b_quote,
            squeeze_eval=s_eval,
        )

    def check_oms_gate_8_1(
        self,
        order_plan_entry: Union[Dict[str, Any], Any],
        borrow_quote: Optional[BorrowFeeQuote] = None,
        squeeze_eval: Optional[SqueezeEvaluationResult] = None,
    ) -> Gate8_1Verdict:
        """Functional alias for evaluate_gate_8_1."""
        return self.evaluate_gate_8_1(
            order=order_plan_entry,
            borrow_quote=borrow_quote,
            squeeze_eval=squeeze_eval,
        )


# =============================================================================
# Backward Compatibility & Alias Trees
# =============================================================================

BorrowDynamicsModel = BorrowDynamicsModel
HardToBorrowFeeModel = BorrowDynamicsModel
ShortSqueezeBorrowRisk = BorrowDynamicsModel
Phase111BorrowModel = BorrowDynamicsModel
ShortSqueezeBorrowModel = BorrowDynamicsModel
HardToBorrowFeeEngine = BorrowDynamicsModel
Phase111BorrowDynamicsEngine = BorrowDynamicsModel
InstitutionalBorrowRiskModel = BorrowDynamicsModel
ShortSqueezeGuardGate = BorrowDynamicsModel


# =============================================================================
# Functional Convenience Interfaces
# =============================================================================

def calculate_borrow_fee(
    utilization: float,
    market: str = "SP500",
    depletion_velocity: float = 0.0,
    is_gc: bool = False,
    default_gc_rate: Optional[float] = None,
) -> float:
    """Convenience functional interface for dynamic borrow fee calculation."""
    model = BorrowDynamicsModel(default_gc_rate=default_gc_rate)
    return model.calculate_borrow_fee(
        utilization=utilization,
        market=market,
        depletion_velocity=depletion_velocity,
        is_gc=is_gc,
    )


def evaluate_short_squeeze_risk(
    symbol: str,
    market: str = "SP500",
    loan_shares: float = 0.0,
    lendable_shares: float = 1_000_000.0,
    short_interest: float = 0.0,
    public_float: float = 1_000_000.0,
    adv_20d: float = 100_000.0,
    upward_momentum: float = 0.0,
    relative_volume: float = 1.0,
) -> SqueezeEvaluationResult:
    """Convenience functional interface for squeeze risk evaluation."""
    model = BorrowDynamicsModel()
    quote = model.evaluate_borrow_quote(
        symbol=symbol,
        market=market,
        loan_shares=loan_shares,
        lendable_shares=lendable_shares,
        short_interest_shares=short_interest,
        public_float_shares=public_float,
        adv_20d=adv_20d,
        upward_momentum=upward_momentum,
    )
    return model.evaluate_squeeze_catalyst(
        symbol=symbol,
        market=market,
        borrow_quote=quote,
        upward_momentum=upward_momentum,
        relative_volume=relative_volume,
    )
