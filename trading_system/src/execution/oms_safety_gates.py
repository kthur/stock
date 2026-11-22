"""
src/execution/oms_safety_gates.py

Pre-Trade Safety Gates & Institutional Risk Compliance Gatekeeper.
Extracted from ExecutionOMSEngine for modularity, clean separation of concerns,
and focused pre-trade risk compliance.

Provides:
- 12 Institutional Pre-Trade Safety Gates (Gates 1 through 12)
- Idiosyncratic Risk Ratio (IRR) Safeguard (Gate 11)
- Factor Crowding Shock Circuit Breaker (Gate 12)
- Physical Capital Conservation Invariant Verification (Gate 9)
- OMSSafetyGatekeeper facade
"""

from __future__ import annotations
import math
import logging
import numpy as np
from typing import Dict, List, Any, Optional, Tuple, Union

logger = logging.getLogger(__name__)

__all__ = [
    "OMSSafetyGatekeeper",
    "_is_invalid_or_nonpositive_price",
    "check_gate11_idiosyncratic_risk_ratio",
    "check_gate12_factor_crowding_shock",
    "evaluate_gate11_and_gate12",
]

VERSION_PHASE175: int = 175
RELEASE_PHASE175: str = "R175"
FEATURE_PHASE175: str = "F859"

VERSION_PHASE179: int = 179
RELEASE_PHASE179: str = "R179"
FEATURE_PHASE179: str = "F878_9_SAFETY_GATE_OMS_GATEWAY"

VERSION_PHASE183: int = 183
RELEASE_PHASE183: str = "R180"
FEATURE_PHASE183: str = "F898_10_SAFETY_GATE_OMS_GATEWAY"

VERSION_PHASE191: int = 191
RELEASE_PHASE191: str = "R182"
FEATURE_PHASE191: str = "F938_12_SAFETY_GATE_OMS_GATEWAY"

VERSION_R183: int = 183
RELEASE_R183: str = "R183"
FEATURE_F945: str = "F945_12_GATE_INSTITUTIONAL_OMS_CAPITAL_CONSERVATION"


def _is_invalid_or_nonpositive_price(p: Any) -> bool:
    """Safely checks if a price is None, empty string, non-numeric, non-finite, or <= 0."""
    if p is None or p == "":
        return True
    try:
        fp = float(p)
        return not (math.isfinite(fp) and fp > 0.0)
    except (ValueError, TypeError):
        return True



def check_gate11_idiosyncratic_risk_ratio(
    w_target: np.ndarray,
    B_loadings: np.ndarray,
    Omega_F: Optional[np.ndarray] = None,
    D_idio: Optional[np.ndarray] = None,
    min_irr: float = 0.70,
    cov_matrix: Optional[np.ndarray] = None,
) -> Tuple[bool, float, str]:
    """
    Gate 11: Idiosyncratic Risk Ratio (IRR) Safeguard.
    Rejects order batches where:
        IRR = sigma^2_idio / sigma^2_total < min_irr (default 0.70)
    Ensures portfolio variance is dominated by stock-specific alpha rather than systematic factor beta.

    Formula:
        beta_p = B^T w
        sigma^2_factor = beta_p^T Omega_F beta_p
        sigma^2_idio = w^T D w = sum(w_i^2 * D_i)
        sigma^2_total = sigma^2_factor + sigma^2_idio
        IRR = sigma^2_idio / sigma^2_total

    Returns:
        (passed: bool, irr: float, reason: str)
    """
    w = np.nan_to_num(np.asarray(w_target, dtype=np.float64).flatten(), nan=0.0, posinf=0.0, neginf=0.0)
    N = len(w)
    if N == 0:
        return True, 1.0, "Zero/negligible total risk: safe default"

    B = np.nan_to_num(np.asarray(B_loadings, dtype=np.float64), nan=0.0, posinf=0.0, neginf=0.0)
    if B.ndim == 1:
        B = B.reshape(N, -1) if len(B) == N else B.reshape(-1, 1)

    if B.size == 0:
        return True, 1.0, "Zero/negligible total risk: safe default"

    if B.shape[0] != N:
        return False, 0.0, f"Gate 11 Breached: Dimension mismatch weights N={N} != B rows={B.shape[0]}"

    K = B.shape[1] if B.ndim == 2 else 0
    if K == 0:
        return True, 1.0, "Zero/negligible total risk: safe default"

    cov = None
    if cov_matrix is not None:
        cov = np.nan_to_num(np.asarray(cov_matrix, dtype=np.float64), nan=0.0, posinf=0.0, neginf=0.0)

    if Omega_F is None:
        if cov is not None and cov.shape == (N, N):
            pinv_B = np.linalg.pinv(B)
            Omega = pinv_B @ cov @ pinv_B.T
            Omega = (Omega + Omega.T) / 2.0
        else:
            Omega = np.eye(K, dtype=np.float64)
    else:
        Omega = np.nan_to_num(np.asarray(Omega_F, dtype=np.float64), nan=0.0, posinf=0.0, neginf=0.0)
        if Omega.ndim == 1:
            Omega = np.diag(Omega)
        elif Omega.ndim == 0:
            Omega = np.array([[float(Omega)]], dtype=np.float64)
        Omega = (Omega + Omega.T) / 2.0

    # Spectral clipping / PSD projection for factor covariance
    if Omega.size > 0:
        try:
            vals, vecs = np.linalg.eigh(Omega)
            if np.any(vals < 0):
                Omega = vecs @ np.diag(np.maximum(vals, 0.0)) @ vecs.T
                Omega = (Omega + Omega.T) / 2.0
        except Exception:
            pass

    if D_idio is None:
        if cov is not None and cov.shape == (N, N):
            sys_cov = B @ Omega @ B.T
            D_diag = np.maximum(np.diag(cov - sys_cov), 0.0)
        else:
            D_diag = np.zeros(N, dtype=np.float64)
    else:
        D_arr = np.nan_to_num(np.asarray(D_idio, dtype=np.float64), nan=0.0, posinf=0.0, neginf=0.0)
        if D_arr.ndim == 2:
            if D_arr.shape == (N, N):
                D_diag = np.diag(D_arr)
            else:
                D_diag = D_arr.flatten()
        elif D_arr.ndim == 1:
            D_diag = D_arr.flatten()
        else:
            D_diag = np.array([float(D_arr)], dtype=np.float64)
        D_diag = np.maximum(D_diag, 0.0)
        if len(D_diag) < N:
            D_diag = np.pad(D_diag, (0, N - len(D_diag)), mode='constant')
        elif len(D_diag) > N:
            D_diag = D_diag[:N]

    beta_p = B.T @ w
    factor_var = max(0.0, float(beta_p.T @ Omega @ beta_p))
    idio_var = max(0.0, float(np.sum((w ** 2) * D_diag)))
    total_var = factor_var + idio_var

    if total_var <= 1e-12 or not np.isfinite(total_var):
        return True, 1.0, "Zero/negligible total risk: safe default"

    irr = float(np.clip(idio_var / total_var, 0.0, 1.0))
    m_irr = float(min_irr) if (min_irr is not None and math.isfinite(float(min_irr))) else 0.70

    # Exact 0.70 passes, 0.6999 fails, 0.7001 passes
    passed = bool(round(irr, 9) >= round(m_irr, 9))
    if passed:
        return True, irr, "PASSED"
    else:
        return False, irr, f"Gate 11 Breached: IRR {irr:.4f} < {m_irr:.4f} (Factor Crowding Risk)"


def check_gate12_factor_crowding_shock(
    crowding_shock_z: float,
    max_shock_z: float = 3.0,
) -> Tuple[bool, Dict[str, Any]]:
    """
    Gate 12: Factor Crowding Shock Circuit Breaker.
    Triggers execution throttling when cross-sectional crowding shock Z-score >= max_shock_z (default 3.0).

    Returns:
        (is_throttled: bool, throttling_params: Dict[str, Any])
    """
    if crowding_shock_z is None:
        z = 0.0
    else:
        try:
            fz = float(crowding_shock_z)
            if not math.isfinite(fz):
                z = 0.0
            else:
                z = fz
        except (ValueError, TypeError):
            z = 0.0

    mz = float(max_shock_z) if (max_shock_z is not None and math.isfinite(float(max_shock_z))) else 3.0
    is_throttled = bool(z >= mz)

    if is_throttled:
        params: Dict[str, Any] = {
            "throttled": True,
            "urgency": "passive_twap",
            "max_adv_participation": 0.0050,
            "leland_buffer_multiplier": 2.0,
            "reason": f"Gate 12 Breached: Factor Crowding Shock Z={z:.2f} >= {mz:.2f} (Throttling Triggered)",
            "shock_z": z,
            "max_shock_z": mz,
            "synthetic_rows": 0,
        }
        return True, params
    else:
        params: Dict[str, Any] = {
            "throttled": False,
            "urgency": "normal",
            "max_adv_participation": 0.0150,
            "leland_buffer_multiplier": 1.0,
            "reason": "PASSED",
            "shock_z": z,
            "max_shock_z": mz,
            "synthetic_rows": 0,
        }
        return False, params


def evaluate_gate11_and_gate12(
    w_target: np.ndarray,
    B_loadings: np.ndarray,
    Omega_F: Optional[np.ndarray] = None,
    D_idio: Optional[np.ndarray] = None,
    factor_shock_z: float = 0.0,
    min_irr: float = 0.70,
    max_shock_z: float = 3.0,
    cov_matrix: Optional[np.ndarray] = None,
) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Feasibility Report §5.5 combined factor risk gate evaluation:
    Evaluates both Gate 11 (IRR Safeguard) and Gate 12 (Factor Crowding Shock Circuit Breaker).

    Returns:
        (passed: bool, message: str, details: Dict[str, Any])
    """
    g11_pass, irr, g11_msg = check_gate11_idiosyncratic_risk_ratio(
        w_target=w_target,
        B_loadings=B_loadings,
        Omega_F=Omega_F,
        D_idio=D_idio,
        min_irr=min_irr,
        cov_matrix=cov_matrix,
    )
    g12_throttled, g12_params = check_gate12_factor_crowding_shock(
        crowding_shock_z=factor_shock_z,
        max_shock_z=max_shock_z,
    )

    details: Dict[str, Any] = {
        "irr": irr,
        "gate11_passed": g11_pass,
        "gate11_reason": g11_msg,
        "gate12_throttled": g12_throttled,
        "gate12_params": g12_params,
        "throttling_params": g12_params,
        "synthetic_rows": 0,
    }

    if not g11_pass:
        return False, g11_msg, details
    if g12_throttled:
        return False, g12_params["reason"], details
    return True, "PASSED", details



class OMSSafetyGatekeeper:
    """
    Pre-Trade Safety Compliance Gatekeeper.
    Houses the 12 institutional risk gates, capital conservation invariants,
    and factor risk throttling logic.
    """
    VERSION = VERSION_R183
    RELEASE = RELEASE_R183
    FEATURE = FEATURE_F945

    def __init__(self, owner: Optional[Any] = None):
        self._owner = owner
        self.factor_crowding_shock_z: float = 0.0
        self.is_factor_crowding_throttled: bool = False
        self.throttling_params: Dict[str, Any] = {
            "throttled": False,
            "urgency": "normal",
            "max_adv_participation": 0.0150,
            "leland_buffer_multiplier": 1.0,
            "reason": "PASSED",
            "synthetic_rows": 0,
        }

    def _is_invalid_or_nonpositive_price(self, price: Any) -> bool:
        """Gate 2 check method: rejects invalid, NaN, inf, zero, or nonpositive price."""
        return _is_invalid_or_nonpositive_price(price)

    def evaluate_gate8_inverse_hedge(self, regime: str, market: str = "KOSPI") -> Dict[str, Any]:
        """
        Gate 8: Synthetic Inverse Hedge Evaluation.
        Under BEAR_HIGH_VOL or PANIC_CRISIS, activates synthetic inverse hedge:
        - KRX (KOSPI/KOSDAQ): 114800 (Kodex Inverse) or 252670 (Kodex 200 Futures Inverse 2X)
        - US (SP500/NASDAQ/RUSSELL2000): PSQ or SH
        """
        reg = str(regime).upper().strip()
        mkt = str(market).upper().strip()
        is_crisis = reg in (
            "BEAR_HIGH_VOL",
            "PANIC_CRISIS",
            "PANIC_LIQUIDITY_SQUEEZE",
            "SYSTEMIC_CRISIS",
            "TIER_PANIC_LIQUIDITY_SQUEEZE",
            "TIER_SYSTEMIC_CRISIS",
        )

        if is_crisis:
            if mkt in ("KOSPI", "KOSDAQ", "KRX"):
                hedge_sym = "114800"
            else:
                hedge_sym = "PSQ"
            return {
                "hedge_active": True,
                "symbol": hedge_sym,
                "hedge_symbol": hedge_sym,
                "target_hedge_weight": 0.15,
                "regime": reg,
                "market": mkt,
            }
        return {
            "hedge_active": False,
            "symbol": "",
            "hedge_symbol": "",
            "target_hedge_weight": 0.0,
            "regime": reg,
            "market": mkt,
        }

    def dispatch_synthetic_inverse_hedge(
        self,
        market: str = "KRX",
        hedge_ratio: float = 0.30,
    ) -> dict:
        """Feature F834: Dispatches synthetic inverse hedge order during crisis regime."""
        mkt = str(market).upper().strip()
        ticker = "114800" if mkt in ("KRX", "KOSPI", "KOSDAQ") else "SH"
        return {
            "ticker": ticker,
            "market": mkt,
            "hedge_ratio": hedge_ratio,
            "action": "BUY_HEDGE",
            "order_type": "MARKET",
            "status": "DISPATCHED",
        }

    def check_circuit_breaker_gate(self, symbol: str, change_pct: float) -> bool:
        """
        Gate 4: Circuit breaker price limit move rejection.
        Rejects orders for stocks reaching or locking at the daily price limit move (+/- 30% in KRX).
        Returns True if gate passed (normal move), False if rejected (limit move reached).
        """
        chg = abs(float(change_pct)) if (change_pct is not None and math.isfinite(float(change_pct))) else 0.0
        if chg >= 29.5 or (0.295 <= chg <= 1.0 and chg >= 0.295):
            return False
        return True

    def check_adv_participation_gate(self, order_qty: float, adv: float) -> bool:
        """
        Gate 6: ADV liquidity participation cap gate.
        Rejects orders exceeding 1.5% (0.015) of 20-day ADV to protect against excessive market impact.
        Returns True if gate passed (<= 1.5%), False if rejected (> 1.5% or adv <= 0).
        """
        adv_val = float(adv) if (adv is not None and math.isfinite(float(adv))) else 0.0
        qty_val = float(order_qty) if (order_qty is not None and math.isfinite(float(order_qty))) else 0.0
        if adv_val <= 0.0 or qty_val <= 0.0:
            return False
        participation = qty_val / adv_val
        if participation > 0.015:
            return False
        return True

    def check_capital_slice_gate(self, order_val: float, max_slice: float = 20_000_000.0) -> bool:
        """
        Gate 1: Capital slice size cap gate.
        Rejects orders exceeding maximum slice size.
        """
        val = float(order_val) if (order_val is not None and math.isfinite(float(order_val))) else 0.0
        ms = float(max_slice) if (max_slice is not None and math.isfinite(float(max_slice))) else 20_000_000.0
        return val <= ms

    def check_single_stock_weight_gate(self, weight: float, max_weight: float = 0.05) -> bool:
        """
        Gate 3: Single-stock weight cap gate.
        Rejects orders that would cause single-stock weight to exceed 5.00% (0.05).
        """
        w = float(weight) if (weight is not None and math.isfinite(float(weight))) else 0.0
        mw = float(max_weight) if (max_weight is not None and math.isfinite(float(max_weight))) else 0.05
        return w <= (mw + 1e-6)

    def check_sector_concentration_gate(self, sector_weight: float, max_sector_weight: float = 0.25) -> bool:
        """
        Gate 5: Sector concentration cap gate.
        Rejects orders that would cause sector concentration to exceed 25.00% (0.25).
        """
        sw = float(sector_weight) if (sector_weight is not None and math.isfinite(float(sector_weight))) else 0.0
        msw = float(max_sector_weight) if (max_sector_weight is not None and math.isfinite(float(max_sector_weight))) else 0.25
        return sw <= (msw + 1e-6)

    def check_cash_reserve_gate(
        self,
        required_cash: float,
        available_cash: float,
        min_reserve_ratio: float = 0.05,
        total_equity: Optional[float] = None,
    ) -> bool:
        """
        Gate 7: Cash reserve invariant & margin integrity check.
        Ensures orders do not exhaust required cash reserves or breach margin integrity.
        """
        req = float(required_cash) if (required_cash is not None and math.isfinite(float(required_cash))) else 0.0
        avail = float(available_cash) if (available_cash is not None and math.isfinite(float(available_cash))) else 0.0
        if avail < req:
            return False
        if total_equity is not None and total_equity > 0:
            remaining_cash = avail - req
            min_reserve = total_equity * float(min_reserve_ratio)
            if remaining_cash < min_reserve - 1e-4:
                return False
        return True

    def verify_physical_capital_conservation(
        self,
        net_equity: float,
        gross_equity: float,
        friction: float = 0.0,
        available_cash: float = 0.0,
    ) -> bool:
        """
        Gate 9: Physical Capital Conservation Invariant Verification.
        Enforces Net Equity <= Gross Equity (within numerical precision),
        non-negative friction drag (friction >= -1e-6), and non-negative available cash (cash >= -1e-4).
        """
        if (
            net_equity is None or not math.isfinite(float(net_equity)) or
            gross_equity is None or not math.isfinite(float(gross_equity)) or
            (friction is not None and not math.isfinite(float(friction))) or
            (available_cash is not None and not math.isfinite(float(available_cash)))
        ):
            return False

        ne = float(net_equity)
        ge = float(gross_equity)
        fric = float(friction) if friction is not None else 0.0
        cash = float(available_cash) if available_cash is not None else 0.0

        if ne > ge + 1e-4:
            return False
        if ne < -1e-4:
            return False
        if fric < -1e-6:
            return False
        if cash < -1e-4:
            return False
        return True

    def evaluate_gate9_capital_conservation(
        self,
        net_equity: float,
        gross_equity: float,
        friction: float = 0.0,
        available_cash: float = 0.0,
    ) -> Dict[str, Any]:
        """
        Gate 9: Detailed evaluation dictionary for Physical Capital Conservation.
        Invariant: Net Equity <= Gross Equity + 1e-4, friction >= -1e-6, cash >= -1e-4.
        """
        ne_finite = net_equity is not None and math.isfinite(float(net_equity))
        ge_finite = gross_equity is not None and math.isfinite(float(gross_equity))
        fric_finite = friction is None or math.isfinite(float(friction))
        cash_finite = available_cash is None or math.isfinite(float(available_cash))

        if not (ne_finite and ge_finite and fric_finite and cash_finite):
            ne = float(net_equity) if ne_finite else 0.0
            ge = float(gross_equity) if ge_finite else 0.0
            fric = float(friction) if (friction is not None and math.isfinite(float(friction))) else 0.0
            cash = float(available_cash) if (available_cash is not None and math.isfinite(float(available_cash))) else 0.0
            passed_equity = False
            passed_friction = False
            passed_cash = False
            all_passed = False
        else:
            ne = float(net_equity)
            ge = float(gross_equity)
            fric = float(friction) if friction is not None else 0.0
            cash = float(available_cash) if available_cash is not None else 0.0

            passed_equity = (ne <= ge + 1e-4) and (ne >= -1e-4)
            passed_friction = fric >= -1e-6
            passed_cash = cash >= -1e-4
            all_passed = passed_equity and passed_friction and passed_cash

        equity_diff = ge - ne

        return {
            "gate": 9,
            "gate_name": "PHYSICAL_CAPITAL_CONSERVATION",
            "passed": all_passed,
            "net_equity": ne,
            "gross_equity": ge,
            "equity_diff": equity_diff,
            "friction": fric,
            "available_cash": cash,
            "passed_equity_conservation": passed_equity,
            "passed_friction_nonnegativity": passed_friction,
            "passed_cash_solvency": passed_cash,
            "status": "PASS" if all_passed else "REJECTED",
        }

    def evaluate_9_safety_gates(
        self,
        order_candidate: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Feature F878: Evaluates 9 discrete institutional safety gates on an order candidate:
        - Gate 1: Capital slice cap (<= 20M KRW per order slice)
        - Gate 2: Non-positive / invalid price filter
        - Gate 3: Single-stock weight cap (<= 5.00%)
        - Gate 4: Circuit breaker price limit move rejection (>= 29.5%)
        - Gate 5: Sector concentration cap (<= 25.00%)
        - Gate 6: ADV liquidity participation cap (<= 1.50% of 20-day ADV)
        - Gate 7: Cash reserve invariant & margin integrity check
        - Gate 8: Crisis synthetic inverse hedge overlay
        - Gate 9: Physical capital conservation (Net Equity <= Gross Equity)
        """
        ctx = context or {}
        sym = str(order_candidate.get("symbol", "DEFAULT"))
        price = order_candidate.get("price", order_candidate.get("target_price", order_candidate.get("close_price", 0.0)))
        qty = float(order_candidate.get("quantity", order_candidate.get("shares", 0.0)))
        order_val = float(order_candidate.get("order_val", price * qty if price and qty else 0.0))
        weight = float(order_candidate.get("weight", order_candidate.get("target_weight", 0.0)))
        change_pct = float(order_candidate.get("change_pct", ctx.get("change_pct", 0.0)))
        sector_weight = float(order_candidate.get("sector_weight", ctx.get("sector_weight", 0.0)))
        adv = float(order_candidate.get("adv", ctx.get("adv", 1_000_000.0)))
        req_cash = float(order_candidate.get("required_cash", order_val))
        avail_cash = float(ctx.get("available_cash", 100_000_000.0))
        total_equity = float(ctx.get("total_equity", 100_000_000.0))
        regime = str(ctx.get("regime", "BULL_LOW_VOL"))
        mkt = str(ctx.get("market", order_candidate.get("market", "KOSPI")))
        net_eq = float(ctx.get("net_equity", total_equity))
        gross_eq = float(ctx.get("gross_equity", total_equity))
        fric = float(ctx.get("friction", order_candidate.get("friction", 0.0)))

        g1 = self.check_capital_slice_gate(order_val, max_slice=float(ctx.get("max_slice", 20_000_000.0)))
        g2 = not self._is_invalid_or_nonpositive_price(price)
        g3 = self.check_single_stock_weight_gate(weight, max_weight=float(ctx.get("max_weight", 0.05)))
        g4 = self.check_circuit_breaker_gate(sym, change_pct)
        g5 = self.check_sector_concentration_gate(sector_weight, max_sector_weight=float(ctx.get("max_sector_weight", 0.25)))
        g6 = self.check_adv_participation_gate(qty, adv) if adv > 0 else True
        g7 = self.check_cash_reserve_gate(req_cash, avail_cash, min_reserve_ratio=float(ctx.get("min_reserve_ratio", 0.05)), total_equity=total_equity)
        g8_res = self.evaluate_gate8_inverse_hedge(regime, market=mkt)
        g8 = True  # Advisory crisis inverse hedge assessment succeeds
        g9_res = self.evaluate_gate9_capital_conservation(net_eq, gross_eq, friction=fric, available_cash=avail_cash)
        g9 = g9_res["passed"]

        gates = {1: g1, 2: g2, 3: g3, 4: g4, 5: g5, 6: g6, 7: g7, 8: g8, 9: g9}
        passed_gates = [k for k, v in gates.items() if v]
        failed_gates = [k for k, v in gates.items() if not v]
        all_passed = len(failed_gates) == 0

        return {
            "symbol": sym,
            "all_passed": all_passed,
            "passed_gates": passed_gates,
            "failed_gates": failed_gates,
            "status": "APPROVED" if all_passed else "REJECTED",
            "gate_results": {
                "gate1_capital_slice": g1,
                "gate2_price_validity": g2,
                "gate3_single_stock_weight": g3,
                "gate4_circuit_breaker": g4,
                "gate5_sector_concentration": g5,
                "gate6_adv_participation": g6,
                "gate7_cash_reserve": g7,
                "gate8_inverse_hedge": g8_res,
                "gate9_capital_conservation": g9_res,
            },
        }

    def check_adverse_impact_gate(self, adverse_impact_bps: float, max_impact_bps: float = 45.0) -> bool:
        """
        Gate 10 check: Adverse price impact cap gate.
        Rejects orders if estimated adverse price impact exceeds 45.0 bps.
        """
        if adverse_impact_bps is None or not math.isfinite(float(adverse_impact_bps)):
            return False
        imp = float(adverse_impact_bps)
        max_imp = float(max_impact_bps) if (max_impact_bps is not None and math.isfinite(float(max_impact_bps))) else 45.0
        return imp <= max_imp

    def check_stale_quote_gate(self, quote_age_ms: float, max_quote_age_ms: float = 500.0) -> bool:
        """
        Gate 10 check: Stale quote latency age gate.
        Rejects orders if top-of-book market quote age exceeds 500.0 ms.
        """
        if quote_age_ms is None or not math.isfinite(float(quote_age_ms)):
            return False
        age = float(quote_age_ms)
        max_age = float(max_quote_age_ms) if (max_quote_age_ms is not None and math.isfinite(float(max_quote_age_ms))) else 500.0
        return age <= max_age

    def check_gate10_adverse_impact_and_stale_quote(
        self,
        adverse_impact_bps: float,
        quote_age_ms: float,
        max_impact_bps: float = 45.0,
        max_quote_age_ms: float = 500.0,
    ) -> bool:
        """
        Gate 10: Adverse Price Impact and Stale Quote Dual Gate.
        """
        return self.check_adverse_impact_gate(adverse_impact_bps, max_impact_bps) and self.check_stale_quote_gate(quote_age_ms, max_quote_age_ms)

    check_adverse_impact_and_stale_quote_gate = check_gate10_adverse_impact_and_stale_quote

    def evaluate_gate10_adverse_impact_stale_quote(
        self,
        adverse_impact_bps: float,
        quote_age_ms: float,
        max_impact_bps: float = 45.0,
        max_quote_age_ms: float = 500.0,
    ) -> Dict[str, Any]:
        """
        Gate 10: Detailed evaluation dictionary for Adverse Impact and Stale Quote Dual Gate.
        """
        imp_finite = adverse_impact_bps is not None and math.isfinite(float(adverse_impact_bps))
        age_finite = quote_age_ms is not None and math.isfinite(float(quote_age_ms))
        imp = float(adverse_impact_bps) if imp_finite else float('inf')
        age = float(quote_age_ms) if age_finite else float('inf')
        max_imp = float(max_impact_bps) if (max_impact_bps is not None and math.isfinite(float(max_impact_bps))) else 45.0
        max_age = float(max_quote_age_ms) if (max_quote_age_ms is not None and math.isfinite(float(max_quote_age_ms))) else 500.0

        p_impact = imp_finite and (imp <= max_imp)
        p_stale = age_finite and (age <= max_age)
        all_passed = p_impact and p_stale

        rejection_reason = None
        if not p_impact and not p_stale:
            rejection_reason = "ADVERSE_IMPACT_AND_STALE_QUOTE_EXCEEDED"
        elif not p_impact:
            rejection_reason = "ADVERSE_IMPACT_EXCEEDED"
        elif not p_stale:
            rejection_reason = "STALE_QUOTE_EXCEEDED"

        return {
            "gate": 10,
            "gate_name": "ADVERSE_IMPACT_AND_STALE_QUOTE",
            "passed": all_passed,
            "adverse_impact_bps": imp,
            "max_impact_bps": max_imp,
            "passed_impact": p_impact,
            "quote_age_ms": age,
            "max_quote_age_ms": max_age,
            "passed_stale_quote": p_stale,
            "rejection_reason": rejection_reason,
            "status": "PASS" if all_passed else "REJECTED",
        }

    def evaluate_10_safety_gates(
        self,
        order_candidate: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Feature F898: Evaluates 10 discrete institutional safety gates on an order candidate:
        - Gate 1: Capital slice cap (<= 20M KRW per order slice)
        - Gate 2: Non-positive / invalid price filter
        - Gate 3: Single-stock weight cap (<= 5.00%)
        - Gate 4: Circuit breaker price limit move rejection (>= 29.5%)
        - Gate 5: Sector concentration cap (<= 25.00%)
        - Gate 6: ADV liquidity participation cap (<= 1.50% of 20-day ADV)
        - Gate 7: Cash reserve invariant & margin integrity check
        - Gate 8: Crisis synthetic inverse hedge overlay
        - Gate 9: Physical capital conservation (Net Equity <= Gross Equity)
        - Gate 10: Adverse impact (<= 45.0 bps) & Stale quote (<= 500.0 ms)
        """
        ctx = context or {}
        sym = str(order_candidate.get("symbol", "DEFAULT"))
        price = order_candidate.get("price", order_candidate.get("target_price", order_candidate.get("close_price", 0.0)))
        qty = float(order_candidate.get("quantity", order_candidate.get("shares", 0.0)))
        order_val = float(order_candidate.get("order_val", price * qty if price and qty else 0.0))
        weight = float(order_candidate.get("weight", order_candidate.get("target_weight", 0.0)))
        change_pct = float(order_candidate.get("change_pct", ctx.get("change_pct", 0.0)))
        sector_weight = float(order_candidate.get("sector_weight", ctx.get("sector_weight", 0.0)))
        adv = float(order_candidate.get("adv", ctx.get("adv", 1_000_000.0)))
        req_cash = float(order_candidate.get("required_cash", order_val))
        avail_cash = float(ctx.get("available_cash", 100_000_000.0))
        total_equity = float(ctx.get("total_equity", 100_000_000.0))
        regime = str(ctx.get("regime", "BULL_LOW_VOL"))
        mkt = str(ctx.get("market", order_candidate.get("market", "KOSPI")))
        net_eq = float(ctx.get("net_equity", total_equity))
        gross_eq = float(ctx.get("gross_equity", total_equity))
        fric = float(ctx.get("friction", order_candidate.get("friction", 0.0)))

        # Gate 10 inputs
        adverse_impact = float(order_candidate.get("adverse_impact_bps", ctx.get("adverse_impact_bps", order_candidate.get("impact_bps", 0.0))))
        quote_age = float(order_candidate.get("quote_age_ms", ctx.get("quote_age_ms", order_candidate.get("latency_ms", 0.0))))
        max_impact = float(ctx.get("max_adverse_impact_bps", ctx.get("max_impact_bps", 45.0)))
        max_quote_age = float(ctx.get("max_quote_age_ms", 500.0))

        g1 = self.check_capital_slice_gate(order_val, max_slice=float(ctx.get("max_slice", 20_000_000.0)))
        g2 = not self._is_invalid_or_nonpositive_price(price)
        g3 = self.check_single_stock_weight_gate(weight, max_weight=float(ctx.get("max_weight", 0.05)))
        g4 = self.check_circuit_breaker_gate(sym, change_pct)
        g5 = self.check_sector_concentration_gate(sector_weight, max_sector_weight=float(ctx.get("max_sector_weight", 0.25)))
        g6 = self.check_adv_participation_gate(qty, adv) if adv > 0 else True
        g7 = self.check_cash_reserve_gate(req_cash, avail_cash, min_reserve_ratio=float(ctx.get("min_reserve_ratio", 0.05)), total_equity=total_equity)
        g8_res = self.evaluate_gate8_inverse_hedge(regime, market=mkt)
        g8 = True  # Advisory crisis inverse hedge assessment succeeds
        g9_res = self.evaluate_gate9_capital_conservation(net_eq, gross_eq, friction=fric, available_cash=avail_cash)
        g9 = g9_res["passed"]
        g10_res = self.evaluate_gate10_adverse_impact_stale_quote(adverse_impact, quote_age, max_impact_bps=max_impact, max_quote_age_ms=max_quote_age)
        g10 = g10_res["passed"]

        gates = {1: g1, 2: g2, 3: g3, 4: g4, 5: g5, 6: g6, 7: g7, 8: g8, 9: g9, 10: g10}
        passed_gates = [k for k, v in gates.items() if v]
        failed_gates = [k for k, v in gates.items() if not v]
        all_passed = len(failed_gates) == 0

        rejection_reasons = []
        if not g1:
            rejection_reasons.append("CAPITAL_SLICE_EXCEEDED")
        if not g2:
            rejection_reasons.append("INVALID_OR_NONPOSITIVE_PRICE")
        if not g3:
            rejection_reasons.append("SINGLE_STOCK_WEIGHT_EXCEEDED")
        if not g4:
            rejection_reasons.append("CIRCUIT_BREAKER_LIMIT_MOVE")
        if not g5:
            rejection_reasons.append("SECTOR_CONCENTRATION_EXCEEDED")
        if not g6:
            rejection_reasons.append("ADV_PARTICIPATION_EXCEEDED")
        if not g7:
            rejection_reasons.append("CASH_RESERVE_BREACHED")
        if not g9:
            rejection_reasons.append("CAPITAL_CONSERVATION_BREACHED")
        if not g10:
            rejection_reasons.append(g10_res.get("rejection_reason", "ADVERSE_IMPACT_OR_STALE_QUOTE_EXCEEDED"))

        rejection_reason_str = "; ".join(rejection_reasons) if rejection_reasons else None

        return {
            "symbol": sym,
            "all_passed": all_passed,
            "passed_gates": passed_gates,
            "failed_gates": failed_gates,
            "status": "APPROVED" if all_passed else "REJECTED",
            "rejection_reasons": rejection_reasons,
            "rejection_reason": rejection_reason_str,
            "gate_results": {
                "gate1_capital_slice": g1,
                "gate2_price_validity": g2,
                "gate3_single_stock_weight": g3,
                "gate4_circuit_breaker": g4,
                "gate5_sector_concentration": g5,
                "gate6_adv_participation": g6,
                "gate7_cash_reserve": g7,
                "gate8_inverse_hedge": g8_res,
                "gate9_capital_conservation": g9_res,
                "gate10_adverse_impact_stale_quote": g10_res,
            },
        }

    def check_hawkes_vpin_gate(
        self,
        vpin: float,
        hawkes_intensity: float,
        max_vpin: float = 0.82,
        max_hawkes: float = 5.0,
    ) -> bool:
        """
        Gate 11 check: Real-time L3 Hawkes order flow toxicity gate.
        Rejects orders if VPIN toxicity exceeds 0.82 or Hawkes intensity exceeds 5.0.
        """
        v_finite = vpin is not None and math.isfinite(float(vpin))
        h_finite = hawkes_intensity is not None and math.isfinite(float(hawkes_intensity))
        if not (v_finite and h_finite):
            return False
        v = float(vpin)
        h = float(hawkes_intensity)
        mv = float(max_vpin) if (max_vpin is not None and math.isfinite(float(max_vpin))) else 0.82
        mh = float(max_hawkes) if (max_hawkes is not None and math.isfinite(float(max_hawkes))) else 5.0
        return (v <= mv) and (h <= mh)

    check_gate11_hawkes_vpin = check_hawkes_vpin_gate

    def evaluate_gate11_hawkes_vpin(
        self,
        vpin: float,
        hawkes_intensity: float,
        max_vpin: float = 0.82,
        max_hawkes: float = 5.0,
    ) -> Dict[str, Any]:
        """
        Gate 11: Detailed evaluation dictionary for L3 Hawkes Order Flow Toxicity Gate.
        """
        v_finite = vpin is not None and math.isfinite(float(vpin))
        h_finite = hawkes_intensity is not None and math.isfinite(float(hawkes_intensity))
        v = float(vpin) if v_finite else float('inf')
        h = float(hawkes_intensity) if h_finite else float('inf')
        mv = float(max_vpin) if (max_vpin is not None and math.isfinite(float(max_vpin))) else 0.82
        mh = float(max_hawkes) if (max_hawkes is not None and math.isfinite(float(max_hawkes))) else 5.0

        p_vpin = v_finite and (v <= mv)
        p_hawkes = h_finite and (h <= mh)
        passed = p_vpin and p_hawkes

        rejection_reason = None
        if not p_vpin and not p_hawkes:
            rejection_reason = "HAWKES_AND_VPIN_TOXICITY_EXCEEDED"
        elif not p_vpin:
            rejection_reason = "VPIN_TOXICITY_EXCEEDED"
        elif not p_hawkes:
            rejection_reason = "HAWKES_ARRIVAL_INTENSITY_EXCEEDED"

        return {
            "gate": 11,
            "gate_name": "L3_HAWKES_VPIN_TOXICITY",
            "passed": passed,
            "vpin": v,
            "max_vpin": mv,
            "passed_vpin": p_vpin,
            "hawkes_intensity": h,
            "max_hawkes_intensity": mh,
            "passed_hawkes": p_hawkes,
            "rejection_reason": rejection_reason,
            "status": "PASS" if passed else "REJECTED",
        }

    def check_settlement_collateral_gate(
        self,
        settlement_days: int = 2,
        collateral_ratio: float = 1.0,
        min_collateral_ratio: float = 1.0,
        currency_valid: bool = True,
    ) -> bool:
        """
        Gate 12 check: Cross-market settlement & multi-currency collateral alignment gate.
        Rejects orders if settlement latency exceeds T+2, collateral ratio < 1.0, or currency invalid.
        """
        s_days = int(settlement_days) if settlement_days is not None else 2
        c_finite = collateral_ratio is not None and math.isfinite(float(collateral_ratio))
        if not c_finite:
            return False
        c_rat = float(collateral_ratio)
        min_c = float(min_collateral_ratio) if (min_collateral_ratio is not None and math.isfinite(float(min_collateral_ratio))) else 1.0
        return (s_days <= 2) and (c_rat >= min_c) and bool(currency_valid)

    check_gate12_settlement_collateral = check_settlement_collateral_gate

    def evaluate_gate12_settlement_collateral(
        self,
        settlement_days: int = 2,
        collateral_ratio: float = 1.0,
        min_collateral_ratio: float = 1.0,
        currency_valid: bool = True,
    ) -> Dict[str, Any]:
        """
        Gate 12: Detailed evaluation dictionary for Settlement and Collateral Alignment Gate.
        """
        s_days = int(settlement_days) if settlement_days is not None else 2
        c_finite = collateral_ratio is not None and math.isfinite(float(collateral_ratio))
        c_rat = float(collateral_ratio) if c_finite else -1.0
        min_c = float(min_collateral_ratio) if (min_collateral_ratio is not None and math.isfinite(float(min_collateral_ratio))) else 1.0
        cv = bool(currency_valid)

        p_settlement = (s_days <= 2)
        p_collateral = c_finite and (c_rat >= min_c)
        p_currency = cv
        passed = p_settlement and p_collateral and p_currency

        rejection_reasons = []
        if not p_settlement:
            rejection_reasons.append("SETTLEMENT_DAYS_EXCEEDED")
        if not p_collateral:
            rejection_reasons.append("COLLATERAL_RATIO_DEFICIENT")
        if not p_currency:
            rejection_reasons.append("CURRENCY_CONVERSION_INVALID")

        rejection_reason = "; ".join(rejection_reasons) if rejection_reasons else None

        return {
            "gate": 12,
            "gate_name": "SETTLEMENT_COLLATERAL_ALIGNMENT",
            "passed": passed,
            "settlement_days": s_days,
            "collateral_ratio": c_rat,
            "min_collateral_ratio": min_c,
            "currency_valid": cv,
            "passed_settlement": p_settlement,
            "passed_collateral": p_collateral,
            "passed_currency": p_currency,
            "rejection_reason": rejection_reason,
            "status": "PASS" if passed else "REJECTED",
        }

    def evaluate_12_safety_gates(
        self,
        order_candidate: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Feature F938: Evaluates 12 discrete institutional safety gates on an order candidate:
        - Gate 1: Capital slice cap (<= 20M KRW per order slice)
        - Gate 2: Non-positive / invalid price filter
        - Gate 3: Single-stock weight cap (<= 5.00%)
        - Gate 4: Circuit breaker price limit move rejection (>= 29.5%)
        - Gate 5: Sector concentration cap (<= 25.00%)
        - Gate 6: ADV liquidity participation cap (<= 1.50% of 20-day ADV)
        - Gate 7: Cash reserve invariant & margin integrity check
        - Gate 8: Crisis synthetic inverse hedge overlay
        - Gate 9: Physical capital conservation (Net Equity <= Gross Equity)
        - Gate 10: Adverse impact (<= 45.0 bps) & Stale quote (<= 500.0 ms)
        - Gate 11: Real-time L3 Hawkes order flow toxicity (VPIN <= 0.82, Hawkes <= 5.0)
        - Gate 12: Cross-market settlement & multi-currency collateral alignment
        """
        ctx = context or {}
        sym = str(order_candidate.get("symbol", "DEFAULT"))
        price = order_candidate.get("price", order_candidate.get("target_price", order_candidate.get("close_price", 0.0)))
        qty = float(order_candidate.get("quantity", order_candidate.get("shares", 0.0)))
        order_val = float(order_candidate.get("order_val", price * qty if price and qty else 0.0))
        weight = float(order_candidate.get("weight", order_candidate.get("target_weight", 0.0)))
        change_pct = float(order_candidate.get("change_pct", ctx.get("change_pct", 0.0)))
        sector = order_candidate.get("sector", "")
        sector_weights_dict = ctx.get("sector_weights", {})
        if sector and sector in sector_weights_dict:
            sector_weight = float(sector_weights_dict[sector])
        elif "sector_weight" in order_candidate:
            sector_weight = float(order_candidate["sector_weight"])
        elif "sector_weight" in ctx:
            sector_weight = float(ctx["sector_weight"])
        else:
            sector_weight = 0.0
        adv = float(order_candidate.get("adv", ctx.get("adv", 1_000_000.0)))
        req_cash = float(order_candidate.get("required_cash", order_val))
        avail_cash = float(ctx.get("available_cash", 100_000_000.0))
        total_equity = float(ctx.get("total_equity", ctx.get("portfolio_capital", 100_000_000.0)))
        regime = str(ctx.get("regime", "BULL_LOW_VOL"))
        mkt = str(ctx.get("market", order_candidate.get("market", "KOSPI")))
        net_eq = float(ctx.get("net_equity", total_equity))
        gross_eq = float(ctx.get("gross_equity", total_equity))
        fric = float(ctx.get("friction", order_candidate.get("friction", 0.0)))

        # Gate 10 inputs
        adverse_impact = float(order_candidate.get("expected_impact_bps", order_candidate.get("adverse_impact_bps", ctx.get("adverse_impact_bps", order_candidate.get("impact_bps", 0.0)))))
        quote_age = float(order_candidate.get("quote_age_ms", ctx.get("quote_age_ms", order_candidate.get("latency_ms", 0.0))))
        max_impact = float(ctx.get("max_adverse_impact_bps", ctx.get("max_impact_bps", 45.0)))
        max_quote_age = float(ctx.get("max_quote_age_ms", 500.0))

        # Gate 11 inputs
        vpin = float(order_candidate.get("vpin", ctx.get("vpin", 0.0)))
        hawkes_intensity = float(order_candidate.get("hawkes_intensity", ctx.get("hawkes_intensity", ctx.get("lambda_hawkes", 0.0))))
        max_vpin = float(ctx.get("max_vpin", 0.82))
        max_hawkes = float(ctx.get("max_hawkes_intensity", ctx.get("max_hawkes", 5.0)))

        # Gate 12 inputs
        settlement_days = int(order_candidate.get("settlement_days", ctx.get("settlement_days", 2)))
        collateral_ratio = float(order_candidate.get("collateral_ratio", ctx.get("collateral_ratio", 1.0)))
        min_collateral_ratio = float(ctx.get("min_collateral_ratio", 1.0))
        currency_valid = bool(order_candidate.get("currency_valid", ctx.get("currency_valid", True)))

        g1 = self.check_capital_slice_gate(order_val, max_slice=float(ctx.get("max_slice", 20_000_000.0)))
        g2 = not self._is_invalid_or_nonpositive_price(price)
        g3 = self.check_single_stock_weight_gate(weight, max_weight=float(ctx.get("max_weight", 0.05)))
        g4 = self.check_circuit_breaker_gate(sym, change_pct)
        g5 = self.check_sector_concentration_gate(sector_weight, max_sector_weight=float(ctx.get("max_sector_weight", 0.25)))
        g6 = self.check_adv_participation_gate(qty, adv)

        cash_ratio = ctx.get("cash_ratio")
        if cash_ratio is not None and float(cash_ratio) < float(ctx.get("min_reserve_ratio", 0.05)):
            g7 = False
        else:
            g7 = self.check_cash_reserve_gate(req_cash, avail_cash, min_reserve_ratio=float(ctx.get("min_reserve_ratio", 0.05)), total_equity=total_equity)

        # Gate 8: Crisis synthetic inverse hedge overlay
        g8_res = self.evaluate_gate8_inverse_hedge(regime, market=mkt)
        g8 = True  # Advisory crisis inverse hedge assessment succeeds
        action_override = None
        crisis_lvl = str(ctx.get("crisis_level", "")).upper()
        raw_act = str(order_candidate.get("action", "")).upper()
        reg_upper = str(regime).upper()
        is_crisis = (
            crisis_lvl in ["SEVERE", "CRISIS", "PANIC_CRISIS", "PANIC"]
            or reg_upper in [
                "PANIC_CRISIS", "CRISIS", "PANIC",
                "BEAR_HIGH_VOL", "PANIC_LIQUIDITY_SQUEEZE", "SYSTEMIC_CRISIS",
                "TIER_PANIC_LIQUIDITY_SQUEEZE", "TIER_SYSTEMIC_CRISIS"
            ]
        )
        if is_crisis:
            g8_res = self.evaluate_gate8_inverse_hedge("PANIC_CRISIS", market=mkt)
            if raw_act in ["SELL_SHORT", "SHORT"]:
                action_override = "CASH_OVERLAY"

        # Gate 9: Physical capital conservation invariant
        avail_cash_val = float(ctx.get("available_cash", ctx.get("cash", avail_cash)))
        g9_res = self.evaluate_gate9_capital_conservation(net_eq, gross_eq, friction=fric, available_cash=avail_cash_val)
        g9 = bool(g9_res["passed"])

        g10_res = self.evaluate_gate10_adverse_impact_stale_quote(adverse_impact, quote_age, max_impact_bps=max_impact, max_quote_age_ms=max_quote_age)
        g10 = g10_res["passed"]
        g11_res = self.evaluate_gate11_hawkes_vpin(vpin, hawkes_intensity, max_vpin=max_vpin, max_hawkes=max_hawkes)
        g11 = g11_res["passed"]
        g12_res = self.evaluate_gate12_settlement_collateral(settlement_days, collateral_ratio, min_collateral_ratio=min_collateral_ratio, currency_valid=currency_valid)
        g12 = g12_res["passed"]

        gates = {1: g1, 2: g2, 3: g3, 4: g4, 5: g5, 6: g6, 7: g7, 8: g8, 9: g9, 10: g10, 11: g11, 12: g12}
        passed_gates = [k for k, v in gates.items() if v]
        failed_gates = [k for k, v in gates.items() if not v]
        all_passed = len(failed_gates) == 0

        rejection_reasons = []
        if not g1:
            rejection_reasons.append("GATE1_MAX_SLICE_EXCEEDED")
        if not g2:
            rejection_reasons.append("GATE2_INVALID_PRICE")
        if not g3:
            rejection_reasons.append("GATE3_WEIGHT_LIMIT_EXCEEDED")
        if not g4:
            rejection_reasons.append("GATE4_CIRCUIT_BREAKER_LIMIT")
        if not g5:
            rejection_reasons.append("GATE5_SECTOR_CONCENTRATION_EXCEEDED")
        if not g6:
            rejection_reasons.append("GATE6_ADV_PARTICIPATION_EXCEEDED")
        if not g7:
            rejection_reasons.append("GATE7_INSUFFICIENT_CASH_RESERVE")
        if not g9:
            rejection_reasons.append("GATE9_PHYSICAL_CAPITAL_CONSERVATION_BREACH")
        if not g10:
            if not g10_res["passed_impact"]:
                rejection_reasons.append("GATE10_EXCESSIVE_MARKET_IMPACT")
            if not g10_res["passed_stale_quote"]:
                rejection_reasons.append("GATE10_STALE_QUOTE_LATENCY")
        if not g11:
            if not g11_res["passed_vpin"]:
                rejection_reasons.append("GATE11_VPIN_TOXICITY_BREACH")
            if not g11_res["passed_hawkes"]:
                rejection_reasons.append("GATE11_HAWKES_SURGE_BREACH")
        if not g12:
            if not g12_res["passed_settlement"]:
                rejection_reasons.append("GATE12_INVALID_SETTLEMENT_CYCLE")
            if not g12_res["passed_collateral"]:
                rejection_reasons.append("GATE12_INSUFFICIENT_COLLATERAL")
            if not g12_res.get("passed_currency", True):
                rejection_reasons.append("GATE12_CURRENCY_CONVERSION_INVALID")

        rejection_reason_str = "; ".join(rejection_reasons) if rejection_reasons else ""

        return {
            "symbol": sym,
            "passed": all_passed,
            "all_passed": all_passed,
            "passed_gates": passed_gates,
            "failed_gates": failed_gates,
            "status": "APPROVED" if all_passed else "REJECTED",
            "action_override": action_override,
            "info": "GATE8_CRISIS_INVERSE_HEDGE_OVERLAY" if action_override else ("GATE8_ACTIVE" if is_crisis else ""),
            "rejection_reasons": rejection_reasons,
            "rejection_reason": rejection_reason_str,
            "gate_results": {
                "gate1_capital_slice": g1,
                "gate2_price_validity": g2,
                "gate3_single_stock_weight": g3,
                "gate4_circuit_breaker": g4,
                "gate5_sector_concentration": g5,
                "gate6_adv_participation": g6,
                "gate7_cash_reserve": g7,
                "gate8_inverse_hedge": g8_res,
                "gate9_capital_conservation": g9_res,
                "gate10_adverse_impact_stale_quote": g10_res,
                "gate11_hawkes_vpin": g11_res,
                "gate12_settlement_collateral": g12_res,
            },
            "synthetic_rows": 0,
        }

    evaluate_safety_gates = evaluate_12_safety_gates

    def evaluate_batch_factor_risk_gates(
        self,
        portfolio_weights: Union[Dict[str, float], np.ndarray, List[float]],
        factor_loadings: Optional[np.ndarray] = None,
        factor_covariance: Optional[np.ndarray] = None,
        idiosyncratic_vars: Optional[np.ndarray] = None,
        factor_shock_z: float = 0.0,
        min_irr: float = 0.70,
        max_shock_z: float = 3.0,
        cov_matrix: Optional[np.ndarray] = None,
    ) -> Dict[str, Any]:
        """
        Batch / Target Portfolio Factor Risk Gate Evaluation.
        Evaluates Gate 11 (Idiosyncratic Risk Ratio Safeguard) and Gate 12 (Crowding Shock Circuit Breaker).
        """
        if isinstance(portfolio_weights, dict):
            w_arr = np.array(list(portfolio_weights.values()), dtype=np.float64)
        else:
            w_arr = np.asarray(portfolio_weights, dtype=np.float64).flatten()

        N = len(w_arr)
        if factor_loadings is None or (isinstance(factor_loadings, np.ndarray) and factor_loadings.size == 0):
            B_loadings = np.zeros((N, 1), dtype=np.float64)
            Omega_F = np.eye(1, dtype=np.float64)
            D_idio = np.ones(N, dtype=np.float64)
        else:
            B_loadings = factor_loadings
            Omega_F = factor_covariance
            D_idio = idiosyncratic_vars

        passed, reason, details = evaluate_gate11_and_gate12(
            w_target=w_arr,
            B_loadings=B_loadings,
            Omega_F=Omega_F,
            D_idio=D_idio,
            factor_shock_z=factor_shock_z,
            min_irr=min_irr,
            max_shock_z=max_shock_z,
            cov_matrix=cov_matrix,
        )

        return {
            "passed": passed,
            "status": "APPROVED" if passed else "REJECTED",
            "reason": reason,
            "irr": details.get("irr", 1.0),
            "gate11_passed": details.get("gate11_passed", True),
            "gate11_reason": details.get("gate11_reason", "PASSED"),
            "gate12_throttled": details.get("gate12_throttled", False),
            "gate12_reason": details.get("throttling_params", {}).get("reason", "PASSED"),
            "throttling_params": details.get("throttling_params", {}),
            "synthetic_rows": 0,
        }

    def update_factor_crowding_state(
        self,
        crowding_shock_z: float,
        max_shock_z: float = 3.0,
    ) -> Tuple[bool, Dict[str, Any]]:
        """Updates internal factor crowding throttling state based on Gate 12."""
        is_throttled, params = check_gate12_factor_crowding_shock(crowding_shock_z, max_shock_z)
        self.factor_crowding_shock_z = float(params.get("shock_z", 0.0))
        self.is_factor_crowding_throttled = bool(is_throttled)
        self.throttling_params = dict(params)
        if self._owner is not None:
            self._owner.factor_crowding_shock_z = self.factor_crowding_shock_z
            self._owner.is_factor_crowding_throttled = self.is_factor_crowding_throttled
            self._owner.throttling_params = self.throttling_params
        return is_throttled, params

    def reset_factor_crowding_state(self) -> None:
        """Resets factor crowding throttling state to normal."""
        self.factor_crowding_shock_z = 0.0
        self.is_factor_crowding_throttled = False
        self.throttling_params = {
            "throttled": False,
            "urgency": "normal",
            "max_adv_participation": 0.0150,
            "leland_buffer_multiplier": 1.0,
            "reason": "PASSED",
            "synthetic_rows": 0,
        }
        if self._owner is not None:
            self._owner.factor_crowding_shock_z = 0.0
            self._owner.is_factor_crowding_throttled = False
            self._owner.throttling_params = dict(self.throttling_params)

