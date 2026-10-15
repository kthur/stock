"""
trading_system/src/risk/dynamic_fx_hedging_engine.py — Global Cross-Market FX Hedging Engine.

Phase 107 / Feature F506 / Release R123 (v114 Production Master)
Milestone 2: Global Cross-Market FX Hedging Engine.

This module provides an institutional continuous currency overlay hedging engine for
multi-market portfolios holding both KRW (KRX) and USD (US) equities:
1. Ingests USDKRW spot exchange rates, forward-rate premiums, and covered interest parity
   (CIP) theoretical forward pricing and deviations.
2. Dynamically computes optimal currency hedge ratios strictly bounded in [0.0, 1.0] based on
   macro regime, USD depreciation momentum, FX volatility scaling, and interest rate carry drag.
3. Evaluates portfolio USD equity exposure in KRW and enforces cash collateral constraints
   (<= available_cash * 0.85) and gross portfolio leverage constraints (<= 1.20).
4. Generates structured hedge orders compatible with ExecutionOMSEngine and PaperTradingDaemon
   utilizing KRX inverse dollar ETF ('261250') or synthetic forward overlays.
"""

from __future__ import annotations

import datetime
import logging
import math
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Input & Output Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class FXMacroInput:
    """Continuous macro and foreign exchange indicators for FX hedge ratio calculation."""
    usdkrw_spot: float
    us_rate: float = 0.045               # US risk-free benchmark yield (e.g. 10Y/3M Treasury, 4.5%)
    kr_rate: float = 0.035               # KR risk-free benchmark yield (e.g. CD 91d/3Y KTB, 3.5%)
    forward_rate: Optional[float] = None # Market observed forward rate (if None, CIP forward is used)
    tenor_days: int = 30                 # Forward tenor in calendar days (tau = tenor_days / 365.0)
    fx_volatility_20d: float = 0.08      # 20-day annualized USDKRW volatility (default 8.0%)
    fx_momentum_20d: float = 0.0         # 20-day USDKRW return (spot - MA20)/MA20 (<0 = USD deprec)
    regime_label: str = "BULL_LOW_VOL"   # 2D market regime label

    @property
    def tau(self) -> float:
        """Tenor in years (day count convention Actual/365)."""
        return max(1e-6, float(self.tenor_days) / 365.0)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return asdict(self)


@dataclass
class FXHedgeResult:
    """Structured evaluation result produced by DynamicFXHedgingEngine."""
    hedge_ratio: float                   # Optimal hedge ratio h* strictly in [0.0, 1.0]
    us_exposure_krw: float               # Total USD equity exposure converted to KRW
    hedge_notional_krw: float            # Required hedge notional in KRW (us_exposure * h*)
    hedge_weight: float                  # Hedge weight as fraction of total portfolio capital
    forward_premium_bps: float           # Theoretical or observed forward premium in basis points
    cip_deviation_bps: float             # Covered interest parity basis in basis points
    collateral_required_krw: float       # Margin collateral required (hedge_notional * margin_req)
    leverage_ratio: float                # Total gross portfolio leverage after hedge allocation
    hedge_order_symbol: str              # Instrument symbol ('261250' for KODEX 미국달러선물인버스)
    hedge_action: str                    # 'BUY_HEDGE' | 'HOLD' | 'NO_HEDGE'
    reason: str                          # Human- and machine-readable execution rationale
    timestamp: str                       # ISO UTC timestamp
    details: Dict[str, Any] = field(default_factory=dict) # Diagnostic metrics breakdown

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return asdict(self)


# ---------------------------------------------------------------------------
# Core Engine Implementation
# ---------------------------------------------------------------------------

class DynamicFXHedgingEngine:
    """Institutional Dynamic FX Hedging & Currency Overlay Engine.

    Features:
    - Covered Interest Parity (CIP) pricing: F = S * (1 + r_kr * tau) / (1 + r_us * tau)
    - CIP deviation / cross-currency basis estimation
    - Regime-aware and momentum-adaptive optimal hedge ratio h* in [0.0, 1.0]
    - Safe-haven crisis protection (USD long retention in flight-to-safety episodes)
    - Cash collateral limit enforcement (<= available_cash * 0.85)
    - Gross leverage limit enforcement (<= 1.20)
    - ExecutionOMSEngine & PaperTradingDaemon compatible hedge order generation
    """

    def __init__(
        self,
        base_currency: str = "KRW",
        target_tenor_days: int = 30,
        margin_requirement: float = 0.10,
        max_gross_leverage: float = 1.20,
        max_collateral_ratio: float = 0.85,
        hedge_symbol: str = "261250",
        baseline_hedge_ratio: float = 0.30,
        target_fx_volatility: float = 0.08,
    ):
        """Initialize DynamicFXHedgingEngine with institutional risk bounds."""
        self.base_currency = str(base_currency).upper()
        self.target_tenor_days = int(target_tenor_days)
        self.margin_requirement = float(margin_requirement)
        self.max_gross_leverage = float(max_gross_leverage)
        self.max_collateral_ratio = float(max_collateral_ratio)
        self.hedge_symbol = str(hedge_symbol)
        self.baseline_hedge_ratio = float(np.clip(baseline_hedge_ratio, 0.0, 1.0))
        self.target_fx_volatility = max(0.01, float(target_fx_volatility))

    # -----------------------------------------------------------------------
    # Quantitative CIP & Forward Pricing Methods
    # -----------------------------------------------------------------------

    def compute_cip_forward_rate(
        self,
        spot: float,
        r_kr: float,
        r_us: float,
        tenor_days: int = 30,
    ) -> float:
        """Compute theoretical forward rate under Covered Interest Parity (CIP).

        Formula:
            tau = tenor_days / 365.0
            F_CIP = S * (1 + r_kr * tau) / (1 + r_us * tau)

        Args:
            spot: USDKRW spot exchange rate.
            r_kr: Korean annualized risk-free interest rate (decimal, e.g. 0.035).
            r_us: US annualized risk-free interest rate (decimal, e.g. 0.045).
            tenor_days: Forward contract tenor in calendar days.

        Returns:
            Theoretical forward exchange rate F_CIP.
        """
        if spot <= 0.0 or not math.isfinite(spot):
            return 0.0

        tau = max(1e-6, float(tenor_days) / 365.0)
        denom = 1.0 + float(r_us) * tau
        if denom <= 0.0 or not math.isfinite(denom):
            return float(spot)

        numer = 1.0 + float(r_kr) * tau
        if numer < 0.0 or not math.isfinite(numer):
            numer = 1.0

        f_cip = float(spot) * (numer / denom)
        return float(f_cip) if math.isfinite(f_cip) else float(spot)

    def compute_forward_premium(
        self,
        spot: float,
        forward: float,
        tenor_days: int = 30,
    ) -> float:
        """Compute forward exchange rate premium or discount in basis points (bps).

        Formula:
            Premium (bps) = ((F - S) / S) * 10,000.0

        Args:
            spot: USDKRW spot exchange rate.
            forward: Forward exchange rate (theoretical or observed).
            tenor_days: Forward tenor (used for validation).

        Returns:
            Forward premium in basis points (positive = forward premium, negative = discount).
        """
        if spot <= 0.0 or not math.isfinite(spot) or not math.isfinite(forward):
            return 0.0

        prem_bps = ((float(forward) - float(spot)) / float(spot)) * 10000.0
        return float(prem_bps) if math.isfinite(prem_bps) else 0.0

    def compute_cip_deviation(
        self,
        spot: float,
        forward_market: Optional[float],
        r_kr: float,
        r_us: float,
        tenor_days: int = 30,
    ) -> float:
        """Compute Covered Interest Parity (CIP) deviation / cross-currency basis in bps.

        Formula:
            Delta_CIP = ((F_market - F_CIP) / S) * 10,000.0

        Args:
            spot: USDKRW spot exchange rate.
            forward_market: Observed market forward rate (if None, CIP holds exactly -> 0.0 bps).
            r_kr: Korean annualized interest rate.
            r_us: US annualized interest rate.
            tenor_days: Tenor in calendar days.

        Returns:
            CIP deviation / basis in basis points.
        """
        if spot <= 0.0 or forward_market is None or not math.isfinite(spot) or not math.isfinite(forward_market):
            return 0.0

        f_cip = self.compute_cip_forward_rate(spot, r_kr, r_us, tenor_days)
        if f_cip <= 0.0:
            return 0.0

        dev_bps = ((float(forward_market) - float(f_cip)) / float(spot)) * 10000.0
        return float(dev_bps) if math.isfinite(dev_bps) else 0.0

    # -----------------------------------------------------------------------
    # Dynamic Optimal Hedge Ratio Computation
    # -----------------------------------------------------------------------

    def calculate_optimal_hedge_ratio(self, macro_input: FXMacroInput) -> float:
        """Calculate dynamic optimal FX hedge ratio h* strictly bounded in [0.0, 1.0].

        Quantitative Modulation Architecture:
        1. USD Depreciation Momentum:
           If r_FX < 0 (USD weakening vs KRW), unhedged USD hurts KRW returns.
           I_deprec = clip(-r_FX / 0.03, 0.0, 1.0) accelerates hedge ratio upwards.
           If r_FX > 0 (USD strengthening), I_apprec = clip(r_FX / 0.03, 0.0, 1.0) dampens hedge.
        2. FX Volatility Scaling:
           nu_vol = clip(sigma_FX / sigma_target, 0.5, 1.8).
           Elevated FX volatility widens risk envelope, increasing required hedge.
        3. Interest Rate Differential (Carry Drag):
           When r_US > r_KR, holding short USD forward contracts incurs negative carry.
           carry_drag = max(0.0, r_US - r_KR) * 2.0 penalizes over-hedging.
        4. CIP Deviation Impact:
           Negative CIP basis (Delta_CIP < -25 bps) indicates USD funding strain, adding
           precautionary liquidity protection.
        5. Macro Regime Specialization:
           - BULL_LOW_VOL: Baseline calm market, moderate hedge ratio (0.20 ~ 0.50).
           - BULL_HIGH_VOL / SIDEWAYS: Volatility-adjusted responsive hedging (0.35 ~ 0.75).
           - BEAR_HIGH_VOL: Strong downside protection, expanding hedge ratio (0.50 ~ 0.90).
           - CRISIS: Safe-haven dynamics. If USD is appreciating (flight-to-safety),
             hedge ratio is dampened (0.0 ~ 0.15) allowing USD appreciation to buffer equity drawdown.
             If USD is depreciating even in crisis, hedge ratio expands aggressively (0.60 ~ 1.00).

        Returns:
            h* strictly bounded in [0.0, 1.0].
        """
        # Defensive validation
        spot = float(macro_input.usdkrw_spot)
        if spot <= 0.0 or not math.isfinite(spot):
            return 0.0

        r_fx = float(macro_input.fx_momentum_20d) if math.isfinite(macro_input.fx_momentum_20d) else 0.0
        vol_fx = float(macro_input.fx_volatility_20d) if math.isfinite(macro_input.fx_volatility_20d) else self.target_fx_volatility
        r_us = float(macro_input.us_rate) if math.isfinite(macro_input.us_rate) else 0.045
        r_kr = float(macro_input.kr_rate) if math.isfinite(macro_input.kr_rate) else 0.035
        regime = str(macro_input.regime_label).upper()

        # 1. USD Depreciation / Appreciation Momentum
        i_deprec = float(np.clip(-r_fx / 0.03, 0.0, 1.0))
        i_apprec = float(np.clip(r_fx / 0.03, 0.0, 1.0))

        # 2. FX Volatility Factor
        nu_vol = float(np.clip(vol_fx / self.target_fx_volatility, 0.5, 1.8))
        delta_vol = nu_vol - 1.0  # Range [-0.5, 0.8]

        # 3. Carry Cost Drag (penalty when US yields exceed KR yields)
        carry_drag = max(0.0, r_us - r_kr) * 2.0

        # 4. CIP Basis Liquidity Adjustment
        cip_adj = 0.0
        if macro_input.forward_rate is not None and math.isfinite(macro_input.forward_rate):
            cip_dev = self.compute_cip_deviation(
                spot, macro_input.forward_rate, r_kr, r_us, macro_input.tenor_days
            )
            if cip_dev < -25.0:
                # Funding tightness: scale up hedge proportionally up to +0.15
                cip_adj = float(np.clip(-cip_dev / 1000.0, 0.0, 0.15))

        # 5. Regime-Specific Base & Modulation
        if "CRISIS" in regime or "SEVERE" in regime:
            # Safe-haven flight-to-safety dynamics:
            if r_fx > 0.005 or i_apprec > 0.15:
                # USD is acting as a natural crisis hedge for KRW investors; keep unhedged
                h_raw = max(0.0, 0.15 - 0.30 * i_apprec)
            else:
                # USD is weakening or flat in crisis; protect capital vigorously
                h_raw = 0.55 + 0.35 * i_deprec + 0.20 * delta_vol + cip_adj
        elif "BEAR_HIGH_VOL" in regime:
            h_raw = 0.50 + 0.40 * i_deprec + 0.20 * delta_vol + cip_adj
        elif "BEAR" in regime:
            h_raw = 0.45 + 0.35 * i_deprec + 0.10 * delta_vol + cip_adj
        elif "SIDEWAYS_HIGH_VOL" in regime:
            h_raw = 0.40 + 0.35 * i_deprec + 0.15 * delta_vol - 0.5 * carry_drag + cip_adj
        elif "SIDEWAYS" in regime:
            h_raw = 0.35 + 0.35 * i_deprec - 0.10 * i_apprec - 0.5 * carry_drag + cip_adj
        elif "BULL_HIGH_VOL" in regime:
            h_raw = 0.35 + 0.40 * i_deprec + 0.15 * delta_vol - carry_drag + cip_adj
        else:  # BULL_LOW_VOL / Default
            h_raw = self.baseline_hedge_ratio + 0.40 * i_deprec - 0.15 * i_apprec - carry_drag + cip_adj

        # 6. Invariant Guarantee: Strictly bounded in [0.0, 1.0]
        if not math.isfinite(h_raw):
            h_raw = self.baseline_hedge_ratio

        h_star = float(np.clip(h_raw, 0.0, 1.0))
        return h_star

    # -----------------------------------------------------------------------
    # Asset Classification Helper
    # -----------------------------------------------------------------------

    @staticmethod
    def is_us_asset(symbol: str) -> bool:
        """Classify whether an equity asset belongs to US equity markets (USD exposure).

        Rules:
        - Korean symbols (KRX): 6-digit codes (e.g. '005930', '000660', '261250') or '.KS'/'.KQ'.
        - US symbols: Alphabetic tickers (e.g. 'AAPL', 'MSFT', 'SPY', 'QQQ', 'BRK.B').
        """
        s = str(symbol).strip().upper()
        if not s:
            return False
        if s in ("USD", "US", "SP500", "NASDAQ", "RUSSELL2000"):
            return True
        if s.endswith(".KS") or s.endswith(".KQ"):
            return False
        if s.isdigit() and len(s) in (6, 7):
            return False
        # If string contains alphabetic characters and no KRX suffix, treat as US equity
        return any(c.isalpha() for c in s)

    # -----------------------------------------------------------------------
    # Portfolio FX Hedge Evaluation & Constraints
    # -----------------------------------------------------------------------

    def evaluate_portfolio_fx_hedge(
        self,
        portfolio_capital_krw: float,
        portfolio_allocations: Dict[str, float],
        macro_input: FXMacroInput,
        available_cash_krw: Optional[float] = None,
    ) -> FXHedgeResult:
        """Evaluate portfolio-level FX risk and determine constrained hedge position.

        Enforces:
        1. US Equity Exposure Identification: E_USD = sum_{i in US} w_i * V_portfolio.
        2. Optimal Hedge Ratio calculation h* in [0.0, 1.0].
        3. Collateral Limit Guard: Margin requirement <= available_cash * 0.85.
        4. Gross Leverage Cap: Gross equity + hedge weight <= 1.20.

        Args:
            portfolio_capital_krw: Total portfolio value in KRW base currency.
            portfolio_allocations: Dict of symbol -> weight or symbol -> value.
            macro_input: FXMacroInput instance containing market rates and regime.
            available_cash_krw: Available cash collateral in KRW. If None, defaults to
                                portfolio_capital_krw * 0.10.

        Returns:
            FXHedgeResult with constrained optimal hedge ratio, notional, and order details.
        """
        v_port = max(0.0, float(portfolio_capital_krw))
        now_ts = datetime.datetime.now(datetime.timezone.utc).isoformat()

        if available_cash_krw is None:
            avail_cash = v_port * 0.10
        else:
            avail_cash = max(0.0, float(available_cash_krw))

        # Parse allocations: detect if weights (sum <= 2.0) or values (sum > 2.0)
        total_alloc_sum = sum(abs(float(v)) for v in portfolio_allocations.values()) if portfolio_allocations else 0.0
        is_value_dict = total_alloc_sum > 2.5 and v_port > 0.0

        normalized_weights: Dict[str, float] = {}
        for sym, val in portfolio_allocations.items():
            if not math.isfinite(val):
                continue
            w = (float(val) / v_port) if (is_value_dict and v_port > 0.0) else float(val)
            normalized_weights[sym] = w

        # Calculate US exposure
        us_weights: Dict[str, float] = {
            sym: w for sym, w in normalized_weights.items() if self.is_us_asset(sym) and w > 0.0
        }
        w_us = sum(us_weights.values())
        e_usd = w_us * v_port
        w_gross_equity = sum(abs(w) for w in normalized_weights.values())

        # Forward pricing & CIP metrics
        spot = max(1.0, float(macro_input.usdkrw_spot))
        f_cip = self.compute_cip_forward_rate(spot, macro_input.kr_rate, macro_input.us_rate, macro_input.tenor_days)
        f_prem_bps = self.compute_forward_premium(spot, f_cip, macro_input.tenor_days)
        cip_dev_bps = self.compute_cip_deviation(
            spot, macro_input.forward_rate, macro_input.kr_rate, macro_input.us_rate, macro_input.tenor_days
        )

        # Early exit if no US exposure
        if e_usd <= 1.0 or w_us <= 1e-5:
            return FXHedgeResult(
                hedge_ratio=0.0,
                us_exposure_krw=0.0,
                hedge_notional_krw=0.0,
                hedge_weight=0.0,
                forward_premium_bps=f_prem_bps,
                cip_deviation_bps=cip_dev_bps,
                collateral_required_krw=0.0,
                leverage_ratio=w_gross_equity,
                hedge_order_symbol=self.hedge_symbol,
                hedge_action="NO_HEDGE",
                reason="NO_US_EQUITY_EXPOSURE",
                timestamp=now_ts,
                details={
                    "w_us": 0.0,
                    "w_gross_equity": w_gross_equity,
                    "unconstrained_h": 0.0,
                    "collateral_limit_hit": False,
                    "leverage_limit_hit": False,
                },
            )

        # Compute unconstrained optimal hedge ratio
        unconstrained_h = self.calculate_optimal_hedge_ratio(macro_input)
        h_star = unconstrained_h

        # Constraint 1: Cash Collateral Limit (Required margin <= available_cash * max_collateral_ratio)
        max_allowed_collateral = avail_cash * self.max_collateral_ratio
        req_margin = (e_usd * h_star) * self.margin_requirement
        collateral_hit = False

        if req_margin > max_allowed_collateral:
            collateral_hit = True
            if (e_usd * self.margin_requirement) > 0.0:
                h_col_cap = max_allowed_collateral / (e_usd * self.margin_requirement)
            else:
                h_col_cap = 0.0
            h_star = min(h_star, h_col_cap)

        # Constraint 2: Gross Portfolio Leverage Cap (Gross equity + hedge weight <= max_gross_leverage)
        max_allowed_hedge_w = max(0.0, self.max_gross_leverage - w_gross_equity)
        max_allowed_hedge_notional = max_allowed_hedge_w * v_port
        candidate_notional = e_usd * h_star
        leverage_hit = False

        if candidate_notional > max_allowed_hedge_notional:
            leverage_hit = True
            if e_usd > 0.0:
                h_star = min(h_star, max_allowed_hedge_notional / e_usd)
            else:
                h_star = 0.0

        # Strict boundedness invariant
        h_star = float(np.clip(h_star, 0.0, 1.0))
        hedge_notional = e_usd * h_star
        hedge_w = (hedge_notional / v_port) if v_port > 0.0 else 0.0
        final_margin = hedge_notional * self.margin_requirement
        total_leverage = w_gross_equity + hedge_w

        # Formulate reason and action
        action = "BUY_HEDGE" if h_star >= 0.01 and hedge_notional >= 1000.0 else "NO_HEDGE"
        reasons = [f"regime={macro_input.regime_label}", f"unconstrained_h={unconstrained_h:.4f}"]
        if collateral_hit:
            reasons.append("COLLATERAL_CAPPED")
        if leverage_hit:
            reasons.append("LEVERAGE_CAPPED")
        if action == "BUY_HEDGE":
            reasons.append(f"ACTIVE_HEDGE: h={h_star:.4f}, notional={hedge_notional:,.0f} KRW")
        else:
            reasons.append("HEDGE_DE_MINIMIS")

        reason_str = "; ".join(reasons)

        return FXHedgeResult(
            hedge_ratio=h_star,
            us_exposure_krw=float(e_usd),
            hedge_notional_krw=float(hedge_notional),
            hedge_weight=float(hedge_w),
            forward_premium_bps=float(f_prem_bps),
            cip_deviation_bps=float(cip_dev_bps),
            collateral_required_krw=float(final_margin),
            leverage_ratio=float(total_leverage),
            hedge_order_symbol=self.hedge_symbol,
            hedge_action=action,
            reason=reason_str,
            timestamp=now_ts,
            details={
                "w_us": float(w_us),
                "w_gross_equity": float(w_gross_equity),
                "unconstrained_h": float(unconstrained_h),
                "collateral_limit_hit": bool(collateral_hit),
                "leverage_limit_hit": bool(leverage_hit),
                "available_cash_krw": float(avail_cash),
                "max_allowed_collateral_krw": float(max_allowed_collateral),
                "max_gross_leverage": float(self.max_gross_leverage),
            },
        )

    # -----------------------------------------------------------------------
    # Order Emission Interface
    # -----------------------------------------------------------------------

    def generate_fx_hedge_order(self, hedge_result: FXHedgeResult) -> Optional[Dict[str, Any]]:
        """Generate structured execution order for KRX inverse dollar ETF or synthetic forward.

        Compatible with ExecutionOMSEngine and PaperTradingDaemon.

        Args:
            hedge_result: FXHedgeResult generated by evaluate_portfolio_fx_hedge.

        Returns:
            Dictionary containing order execution payload, or None if no hedge is required.
        """
        if hedge_result.hedge_notional_krw <= 0.0 or hedge_result.hedge_ratio < 0.005:
            return None

        order_id = f"FX_HEDGE_{uuid.uuid4().hex[:8].upper()}"
        return {
            "order_id": order_id,
            "symbol": hedge_result.hedge_order_symbol,  # '261250'
            "market": "KRX",
            "side": "BUY",
            "action": "BUY_HEDGE",
            "order_type": "MARKET",
            "notional_krw": float(hedge_result.hedge_notional_krw),
            "hedge_weight": float(hedge_result.hedge_weight),
            "hedge_ratio": float(hedge_result.hedge_ratio),
            "collateral_required_krw": float(hedge_result.collateral_required_krw),
            "reason": hedge_result.reason,
            "timestamp": hedge_result.timestamp,
        }

    # -----------------------------------------------------------------------
    # Backward Compatibility Helper
    # -----------------------------------------------------------------------

    @classmethod
    def calculate_optimal_fx_overlay(
        cls,
        us_portfolio_weight: float,
        usdkrw_series: Any = None,
        us_yield: float = 0.0425,
        kr_yield: float = 0.0350,
        regime: str = "BULL_LOW_VOL",
    ) -> Dict[str, Any]:
        """Backward-compatible overlay evaluator matching legacy delta_beta_hedge prototype."""
        if us_portfolio_weight <= 0.01:
            return {"fx_hedge_ratio": 0.0, "fx_hedge_weight": 0.0, "status": "NO_US_EXPOSURE"}

        spot = 1350.0
        fx_mom = 0.0
        fx_vol = 0.08
        if usdkrw_series is not None:
            try:
                import pandas as pd
                s = pd.to_numeric(usdkrw_series, errors="coerce").dropna()
                if len(s) >= 20:
                    ma20 = float(s.tail(20).mean())
                    curr = float(s.iloc[-1])
                    spot = curr
                    if ma20 > 0:
                        fx_mom = (curr - ma20) / ma20
                    returns = s.pct_change().dropna()
                    if len(returns) >= 10:
                        fx_vol = float(returns.std() * math.sqrt(252))
            except Exception:
                pass

        engine = cls()
        macro_in = FXMacroInput(
            usdkrw_spot=spot,
            us_rate=us_yield,
            kr_rate=kr_yield,
            fx_momentum_20d=fx_mom,
            fx_volatility_20d=fx_vol,
            regime_label=regime,
        )
        h_star = engine.calculate_optimal_hedge_ratio(macro_in)
        hedge_w = float(np.clip(us_portfolio_weight * h_star, 0.0, 1.0))

        rate_diff = us_yield - kr_yield
        return {
            "us_portfolio_weight": float(us_portfolio_weight),
            "fx_hedge_ratio": float(h_star),
            "fx_hedge_weight": float(hedge_w),
            "is_usd_downtrend": bool(fx_mom < 0.0),
            "rate_diff_bps": float(rate_diff * 10000.0),
            "status": "ACTIVE_FX_OVERLAY",
        }


# ---------------------------------------------------------------------------
# Complete Alias Trees
# ---------------------------------------------------------------------------

GlobalCrossMarketFXHedgingEngine = DynamicFXHedgingEngine
Phase107DynamicFXHedgingEngine = DynamicFXHedgingEngine
FXHedgingEngine = DynamicFXHedgingEngine
CurrencyOverlayHedgingEngine = DynamicFXHedgingEngine

__all__ = [
    "FXMacroInput",
    "FXHedgeResult",
    "DynamicFXHedgingEngine",
    "GlobalCrossMarketFXHedgingEngine",
    "Phase107DynamicFXHedgingEngine",
    "FXHedgingEngine",
    "CurrencyOverlayHedgingEngine",
]
