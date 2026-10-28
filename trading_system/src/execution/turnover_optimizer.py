"""
turnover_optimizer.py — Turnover Penalty Buffer & Signal Decay Optimizer

Phase 142 (Features F693 & F694):
  - Market-adaptive asymmetric Leland dynamic no-trade buffer bands.
  - Continuous winner expansion (m_upper in [1.0, 2.2]) and loser contraction (m_lower in [0.6, 1.0]).
  - Boundary rebalancing (rebalances to L_i or U_i, halving rebalance turnover).
  - Instant bypass triggers (fresh entry, full liquidation, severe drift >= 50%).
  - Gate 4 leveraged bandwidth expansion (1.0 + 0.40 * max(0, leverage - 1.0)).
"""

from __future__ import annotations

import logging
import math
from typing import Any, Dict, Optional, Tuple, Union

import numpy as np

logger = logging.getLogger(__name__)

VERSION = 142
RELEASE = "R142"
FEATURE = "F693_ASYMMETRIC_LELAND_DYNAMIC_BUFFER_BANDS"


class TurnoverOptimizer:
    """
    Market-Adaptive Asymmetric Leland Dynamic No-Trade Buffer & Turnover Optimizer.
    Filters target portfolio allocations against current holdings to reduce turnover and transaction drag.
    """

    MARKET_COST_BPS = {
        "KOSDAQ": 35.0,
        "KOSPI": 25.0,
        "KRX": 25.0,
        "RUSSELL2000": 16.0,
        "NASDAQ": 7.0,
        "SP500": 5.0,
        "US": 5.0,
    }

    def __init__(
        self,
        turnover_threshold_pct: float = 0.05,
        min_rebalance_delta_krw: float = 50000.0,
        market_thresholds: Optional[Dict[str, float]] = None,
        gamma: float = 3.0,
        risk_aversion: float = 1e-4,
    ) -> None:
        try:
            safe_thresh = (
                float(turnover_threshold_pct)
                if (turnover_threshold_pct is not None and math.isfinite(float(turnover_threshold_pct)))
                else 0.05
            )
        except (ValueError, TypeError):
            safe_thresh = 0.05
        self.turnover_threshold_pct = max(0.001, min(0.50, safe_thresh))

        try:
            safe_min_delta = (
                float(min_rebalance_delta_krw)
                if (min_rebalance_delta_krw is not None and math.isfinite(float(min_rebalance_delta_krw)))
                else 50000.0
            )
        except (ValueError, TypeError):
            safe_min_delta = 50000.0
        self.min_rebalance_delta_krw = max(0.0, safe_min_delta)

        self.gamma = float(gamma)
        self.risk_aversion = float(risk_aversion)

        # Market-specific turnover hysteresis thresholds (theta_US = 0.025, theta_KRX = 0.045)
        us_thresh = 0.025
        krx_thresh = 0.045
        if market_thresholds and isinstance(market_thresholds, dict):
            for k, v in market_thresholds.items():
                k_clean = str(k).upper().strip()
                try:
                    vf = float(v)
                    if math.isfinite(vf):
                        if k_clean == "US":
                            us_thresh = vf
                        elif k_clean == "KRX":
                            krx_thresh = vf
                except (ValueError, TypeError):
                    pass

        self.market_thresholds: Dict[str, float] = {
            "US": us_thresh,
            "SP500": us_thresh,
            "NASDAQ": us_thresh,
            "RUSSELL2000": us_thresh,
            "KRX": krx_thresh,
            "KOSPI": krx_thresh,
            "KOSDAQ": krx_thresh,
        }
        if market_thresholds and isinstance(market_thresholds, dict):
            for k, v in market_thresholds.items():
                try:
                    vf = float(v)
                    if math.isfinite(vf):
                        self.market_thresholds[str(k).upper().strip()] = vf
                except (ValueError, TypeError):
                    pass

    def resolve_threshold(
        self,
        symbol: str,
        currency: str = "KRW",
        market_map: Optional[Dict[str, str]] = None,
    ) -> float:
        """
        Resolves market-adaptive turnover hysteresis threshold theta_m for given symbol.
        Defaults to theta_US = 0.025 for US markets and theta_KRX = 0.045 for KRX markets.
        """
        sym_clean = str(symbol).strip().upper()
        if sym_clean in self.market_thresholds:
            return float(self.market_thresholds[sym_clean])
        if market_map and str(symbol).strip() in market_map:
            mkt = str(market_map[str(symbol).strip()]).upper().strip()
            if mkt in self.market_thresholds:
                return float(self.market_thresholds[mkt])
        # Auto-detect US vs KRX from symbol structure and currency
        if (
            sym_clean in ("SP500", "NASDAQ", "RUSSELL2000")
            or str(currency).upper() == "USD"
            or (not sym_clean.isdigit() and len(sym_clean) <= 5 and not sym_clean.startswith("0"))
        ):
            return float(self.market_thresholds.get("US", 0.025))
        if (
            sym_clean in ("KOSPI", "KOSDAQ")
            or (sym_clean.isdigit() and len(sym_clean) == 6)
            or sym_clean.endswith(".KS")
            or sym_clean.endswith(".KQ")
        ):
            return float(self.market_thresholds.get("KRX", 0.045))
        return float(self.turnover_threshold_pct)

    def resolve_cost_bps(self, symbol: str, market: Optional[str] = None) -> float:
        """Resolves market execution transaction cost c_i in basis points."""
        if market:
            m_clean = str(market).upper().strip()
            if m_clean in self.MARKET_COST_BPS:
                return self.MARKET_COST_BPS[m_clean]
        sym = str(symbol).upper().strip()
        if sym in self.MARKET_COST_BPS:
            return self.MARKET_COST_BPS[sym]
        if sym in ("SP500", "NASDAQ", "RUSSELL2000") or (
            not sym.isdigit() and len(sym) <= 5 and not sym.startswith("0")
        ):
            return self.MARKET_COST_BPS.get("US", 5.0)
        if (
            sym in ("KOSPI", "KOSDAQ")
            or (sym.isdigit() and len(sym) == 6)
            or sym.endswith(".KS")
            or sym.endswith(".KQ")
        ):
            return self.MARKET_COST_BPS.get("KRX", 25.0)
        return 10.0

    def compute_leland_bands(
        self,
        target_weights: Dict[str, float],
        volatilities: Optional[Dict[str, float]] = None,
        unrealized_returns: Optional[Dict[str, float]] = None,
        downside_volatilities: Optional[Dict[str, float]] = None,
        gamma: float = 3.0,
        leverage: float = 1.0,
        market_map: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Tuple[float, float, float]]:
        """
        Computes market-adaptive asymmetric Leland dynamic no-trade buffer bands:
            Delta_i = ((3/4) * c_i * w_i^* * (1 - w_i^*) * sigma_i^2 / gamma)^(1/3)
            with Gate 4 leveraged expansion (1.0 + 0.40 * max(0, leverage - 1.0)).
        Returns:
            Dict[symbol -> (L_i, w_i^*, U_i)]
        """
        bands: Dict[str, Tuple[float, float, float]] = {}
        lev_factor = 1.0 + 0.40 * max(0.0, float(leverage) - 1.0)
        safe_gamma = max(1e-6, float(gamma))

        for sym, raw_tgt in target_weights.items():
            tgt_w = float(raw_tgt) if (raw_tgt is not None and math.isfinite(float(raw_tgt))) else 0.0
            if tgt_w <= 1e-4:
                bands[sym] = (0.0, tgt_w, 0.0)
                continue

            # 1. Resolve transaction cost fraction c_i
            mkt = market_map.get(sym) if market_map else None
            c_bps = self.resolve_cost_bps(sym, mkt)
            c_i = c_bps / 10000.0

            # 2. Resolve annual volatility
            v_daily = 0.02
            if volatilities and sym in volatilities:
                try:
                    vf = float(volatilities[sym])
                    if math.isfinite(vf) and vf > 0:
                        v_daily = vf
                except (ValueError, TypeError):
                    v_daily = 0.02
            ann_var = 252.0 * (v_daily ** 2)

            # 3. Base half-width Delta_i
            w_fac = max(1e-6, tgt_w * (1.0 - min(0.9999, tgt_w)))
            cubic = (0.75 * c_i * w_fac * ann_var) / safe_gamma
            delta_i = float(np.clip(np.cbrt(cubic), 0.005, 0.045)) * lev_factor

            # 4. Asymmetric multipliers from normalized unrealized return Z-score
            u_ret = 0.0
            if unrealized_returns and sym in unrealized_returns:
                try:
                    urf = float(unrealized_returns[sym])
                    if math.isfinite(urf):
                        u_ret = urf
                except (ValueError, TypeError):
                    u_ret = 0.0

            if u_ret < 0.0 and downside_volatilities and sym in downside_volatilities:
                try:
                    dv = float(downside_volatilities[sym])
                    eff_v = max(0.005, dv) if math.isfinite(dv) else v_daily
                except (ValueError, TypeError):
                    eff_v = v_daily
            else:
                eff_v = v_daily

            vol_5d = eff_v * math.sqrt(5.0)
            z = (u_ret / vol_5d) if vol_5d > 0 else 0.0

            if z > 0.0:
                z_clip = min(max((z - 1.0) / 2.0, 0.0), 1.0)
                m_upper = 1.0 + 1.2 * z_clip  # Winner expansion in [1.0, 2.2]
                m_lower = 1.0
            elif z < 0.0:
                z_clip = min(max((-1.0 - z) / 2.0, 0.0), 1.0)
                m_upper = 1.0
                m_lower = 1.0 - 0.4 * z_clip  # Loser contraction in [0.6, 1.0]
            else:
                m_upper = 1.0
                m_lower = 1.0

            u_i = tgt_w + m_upper * delta_i
            l_i = max(0.0, tgt_w - m_lower * delta_i)
            bands[sym] = (float(l_i), float(tgt_w), float(u_i))

        return bands

    def optimize_allocations(
        self,
        current_holdings: Dict[str, float],
        target_allocations: Dict[str, float],
        total_capital: float = 100000000.0,
        currency: str = "KRW",
        use_leland_bands: bool = False,
        rebalance_mode: str = "boundary",
        **kwargs: Any,
    ) -> Dict[str, Dict[str, Any]]:
        """Filter target allocations against current holdings using turnover hysteresis & Leland bands."""
        try:
            cap = (
                float(total_capital)
                if (total_capital is not None and math.isfinite(float(total_capital)))
                else 100000000.0
            )
        except (ValueError, TypeError):
            cap = 100000000.0
        cap = max(0.0, cap)

        all_symbols = set(str(k).strip() for k in current_holdings.keys() if str(k).strip()) | set(
            str(k).strip() for k in target_allocations.keys() if str(k).strip()
        )
        optimized: Dict[str, Dict[str, Any]] = {}
        total_turnover_reduced = 0.0

        def _get_w(d: Dict[str, float], sym: str) -> float:
            if not isinstance(d, dict) or sym not in d:
                return 0.0
            try:
                val = float(d.get(sym, 0.0))
                return max(0.0, min(1.0, val)) if math.isfinite(val) else 0.0
            except (ValueError, TypeError):
                return 0.0

        curr_str = str(kwargs.get("currency", currency)).upper().strip()
        is_usd = curr_str == "USD" or (cap < 5_000_000.0 and any(not str(s).isdigit() for s in all_symbols))
        min_rebalance_delta = 50.0 if is_usd else self.min_rebalance_delta_krw

        # Compute or ingest Leland bands
        leland_bands = kwargs.get("leland_bands") or kwargs.get("buffer_bands")
        should_use_leland = use_leland_bands or kwargs.get("use_leland_bands", False)
        if leland_bands is None and should_use_leland:
            leland_bands = self.compute_leland_bands(
                target_weights=target_allocations,
                volatilities=kwargs.get("volatilities"),
                unrealized_returns=kwargs.get("unrealized_returns"),
                downside_volatilities=kwargs.get("downside_volatilities"),
                gamma=kwargs.get("gamma", self.gamma),
                leverage=kwargs.get("leverage", 1.0),
                market_map=kwargs.get("market_map"),
            )

        for sym in sorted(all_symbols):
            curr_w = _get_w(current_holdings, sym)
            raw_w = _get_w(target_allocations, sym)
            weight_delta = abs(raw_w - curr_w)
            amount_delta = weight_delta * cap

            # Instant Bypass Triggers (Priority 1)
            is_fresh_entry = (curr_w <= 1e-4 and raw_w > 1e-4)
            is_full_exit = (raw_w <= 1e-4 and curr_w > 1e-4)
            drift_ratio = (weight_delta / curr_w) if curr_w > 1e-4 else 0.0
            is_severe_drift = (curr_w > 1e-4 and drift_ratio >= 0.50 and amount_delta >= min_rebalance_delta * 2.0)

            if is_fresh_entry or is_full_exit or is_severe_drift:
                final_w = float(np.clip(raw_w, 0.0, 1.0))
                action = "BUY" if final_w > curr_w else ("SELL" if final_w < curr_w else "HOLD")
            elif leland_bands and sym in leland_bands:
                b_val = leland_bands[sym]
                if isinstance(b_val, (tuple, list)) and len(b_val) >= 2:
                    L_i = float(b_val[0])
                    U_i = float(b_val[-1])
                else:
                    L_i, U_i = raw_w, raw_w

                mode = str(kwargs.get("rebalance_mode", rebalance_mode)).lower()
                if L_i <= curr_w <= U_i:
                    final_w = curr_w
                    action = "HOLD"
                    total_turnover_reduced += amount_delta
                elif mode == "boundary":
                    if curr_w > U_i:
                        final_w = float(np.clip(U_i, 0.0, 1.0))
                        action = "SELL" if final_w < curr_w else "HOLD"
                    else:
                        final_w = float(np.clip(L_i, 0.0, 1.0))
                        action = "BUY" if final_w > curr_w else "HOLD"
                else:
                    final_w = float(np.clip(raw_w, 0.0, 1.0))
                    action = "BUY" if raw_w > curr_w else "SELL"
            else:
                thresh = self.resolve_threshold(sym, currency=curr_str, market_map=kwargs.get("market_map"))
                u_ret = 0.0
                unrealized_returns = kwargs.get("unrealized_returns")
                if isinstance(unrealized_returns, dict) and sym in unrealized_returns:
                    try:
                        val = float(unrealized_returns[sym])
                        if math.isfinite(val):
                            u_ret = val
                    except (ValueError, TypeError):
                        u_ret = 0.0
                if u_ret >= 0.08:
                    thresh *= 1.25

                if weight_delta < thresh or amount_delta < min_rebalance_delta:
                    final_w = curr_w
                    action = "HOLD"
                    total_turnover_reduced += amount_delta
                elif weight_delta < (thresh * 1.5):
                    decay_ratio = (weight_delta - thresh) / (0.5 * thresh + 1e-6)
                    decay_clipped = float(np.clip(decay_ratio if np.isfinite(decay_ratio) else 0.5, 0.2, 1.0))
                    final_w = curr_w + (raw_w - curr_w) * decay_clipped
                    final_w = float(np.clip(final_w if np.isfinite(final_w) else curr_w, 0.0, 1.0))
                    action = "BUY" if final_w > curr_w else ("SELL" if final_w < curr_w else "HOLD")
                else:
                    final_w = float(np.clip(raw_w, 0.0, 1.0))
                    action = "BUY" if raw_w > curr_w else "SELL"

            # Sub-minimum delta suppression (suppresses micro trades unless instant bypass triggered)
            actual_trade_delta = abs(final_w - curr_w) * cap
            if actual_trade_delta < min_rebalance_delta and not (is_fresh_entry or is_full_exit or is_severe_drift):
                final_w = curr_w
                action = "HOLD"
                actual_trade_delta = 0.0

            optimized[sym] = {
                "target_weight": final_w,
                "raw_target_weight": raw_w,
                "current_weight": curr_w,
                "action": action,
                "delta_amount": actual_trade_delta if action != "HOLD" else 0.0,
            }

        # Portfolio budget preservation and drift absorption
        raw_sum = sum(_get_w(target_allocations, s) for s in all_symbols)
        preserve_budget = kwargs.get("preserve_budget", abs(raw_sum - 1.0) < 1e-3)
        final_sum = sum(d["target_weight"] for d in optimized.values())

        if preserve_budget and abs(final_sum - raw_sum) > 1e-5 and final_sum > 1e-12:
            budget_drift = raw_sum - final_sum
            active_syms = [
                s for s in all_symbols if optimized[s]["action"] != "HOLD" and optimized[s]["target_weight"] > 0
            ]
            if active_syms:
                active_sum = sum(optimized[s]["target_weight"] for s in active_syms)
                if active_sum > 1e-12:
                    for s in active_syms:
                        alloc = budget_drift * (optimized[s]["target_weight"] / active_sum)
                        new_w = float(np.clip(optimized[s]["target_weight"] + alloc, 0.0, 1.0))
                        optimized[s]["target_weight"] = new_w
                        optimized[s]["delta_amount"] = abs(new_w - optimized[s]["current_weight"]) * cap
            else:
                nz_syms = [s for s in all_symbols if optimized[s]["target_weight"] > 0]
                if nz_syms:
                    for s in nz_syms:
                        new_w = float(optimized[s]["target_weight"] * (raw_sum / final_sum))
                        optimized[s]["target_weight"] = new_w
                        optimized[s]["delta_amount"] = abs(new_w - optimized[s]["current_weight"]) * cap

        logger.info(
            "[TurnoverOptimizer] Reduced turnover by %s %s across %d symbols.",
            f"{total_turnover_reduced:,.0f}",
            curr_str,
            len(all_symbols),
        )
        return optimized


# Institutional Architecture Aliases
Phase142TurnoverOptimizer = TurnoverOptimizer
AsymmetricLelandOptimizer = TurnoverOptimizer
