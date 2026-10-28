"""
src/core/option_surface_accelerator.py — Second-Order Options Surface Convexity Engine (Feature F683).

Phase 140 Release R140:
- Analytical Black-Scholes 2nd-order Greeks: Gamma, Vega, Vanna (dDelta/dSigma), Volga/Vomma (d^2V/dSigma^2).
- Net Dealer Gamma Positioning (GEX_dealer) and Net Dealer Vanna Positioning.
- IV Skew acceleration tracking fear-inversion / short gamma squeezes.
- Realized Asymmetric Semivariance & Parkinson High-Low proxy fallback for non-optionable/KRX equities.
- Score bounded strictly within [0.05, 0.98], zero NaNs, zero synthetic rows.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd

from .base_strategy import BaseStrategyEngine, ScoreDataFrame, make_score_dataframe
from src.core.strategy_registry import register_strategy, StrategyMeta

logger = logging.getLogger(__name__)

# Metadata Constants
VERSION: int = 140
RELEASE: str = "R140"
FEATURE: str = "F683"


def compute_black_scholes_greeks(
    spot: float,
    strike: float,
    tau: float,
    vol: float,
    rate: float = 0.04,
) -> Dict[str, float]:
    """
    Computes analytical closed-form Black-Scholes Greeks:
        d1 = [ln(S/K) + (r + 0.5*sigma^2)*tau] / (sigma * sqrt(tau))
        d2 = d1 - sigma * sqrt(tau)
        Gamma = phi(d1) / (S * sigma * sqrt(tau))
        Vega = S * sqrt(tau) * phi(d1)
        Vanna = -phi(d1) * d2 / sigma
        Volga = Vega * d1 * d2 / sigma
    """
    # 1. Non-finite input guard (eliminates NaNs, +inf, -inf before arithmetic or logarithms)
    if not (
        np.isfinite(spot)
        and np.isfinite(strike)
        and np.isfinite(tau)
        and np.isfinite(vol)
        and np.isfinite(rate)
    ):
        return {"gamma": 0.0, "vega": 0.0, "vanna": 0.0, "volga": 0.0, "d1": 0.0, "d2": 0.0}

    if spot <= 0.0 or strike <= 0.0 or tau <= 1e-5 or vol <= 1e-4:
        return {"gamma": 0.0, "vega": 0.0, "vanna": 0.0, "volga": 0.0, "d1": 0.0, "d2": 0.0}

    try:
        sqrt_tau = np.sqrt(tau)
        denom = vol * sqrt_tau
        if denom <= 1e-8:
            return {"gamma": 0.0, "vega": 0.0, "vanna": 0.0, "volga": 0.0, "d1": 0.0, "d2": 0.0}

        d1 = (np.log(spot / strike) + (rate + 0.5 * (vol ** 2)) * tau) / denom
        d2 = d1 - denom
        phi_d1 = (1.0 / np.sqrt(2.0 * np.pi)) * np.exp(-0.5 * (d1 ** 2))

        gamma = phi_d1 / (spot * denom)
        vega = spot * sqrt_tau * phi_d1
        vanna = -phi_d1 * (d2 / vol)
        volga = vega * (d1 * d2 / vol)

        return {
            "gamma": float(gamma) if np.isfinite(gamma) else 0.0,
            "vega": float(vega) if np.isfinite(vega) else 0.0,
            "vanna": float(vanna) if np.isfinite(vanna) else 0.0,
            "volga": float(volga) if np.isfinite(volga) else 0.0,
            "d1": float(d1) if np.isfinite(d1) else 0.0,
            "d2": float(d2) if np.isfinite(d2) else 0.0,
        }
    except Exception:
        return {"gamma": 0.0, "vega": 0.0, "vanna": 0.0, "volga": 0.0, "d1": 0.0, "d2": 0.0}


def compute_net_dealer_gex_and_vanna(
    spot: float,
    options_chain: List[Dict[str, Any]],
    rate: float = 0.04,
) -> Tuple[float, float, float]:
    """
    Computes Net Dealer GEX and Net Dealer Vanna across strike chains:
        GEX_dealer = sum(Put_OI * Gamma * S^2 * 100) - sum(Call_OI * Gamma * S^2 * 100)
        Net_Vanna_dealer = sum(Call_OI * Vanna * S * 100) - sum(Put_OI * Vanna * S * 100)
    Returns:
        (gex_dealer, net_vanna, iv_skew)
    """
    if not np.isfinite(spot) or spot <= 0.0 or not np.isfinite(rate) or not options_chain:
        return 0.0, 0.0, 1.0

    call_gamma_sum = 0.0
    put_gamma_sum = 0.0
    call_vanna_sum = 0.0
    put_vanna_sum = 0.0

    call_iv_list: List[float] = []
    put_iv_list: List[float] = []

    for opt in options_chain:
        strike = float(opt.get("strike", spot))
        tau = float(opt.get("tau", 30.0 / 365.0))
        vol = float(opt.get("implied_vol", opt.get("vol", 0.30)))
        oi = float(opt.get("open_interest", opt.get("oi", 0.0)))
        opt_type = str(opt.get("type", opt.get("option_type", "call"))).lower()

        if not (np.isfinite(strike) and np.isfinite(tau) and np.isfinite(vol) and np.isfinite(oi)):
            continue
        if oi <= 0.0 or vol <= 1e-4 or strike <= 0.0 or tau <= 1e-5:
            continue

        greeks = compute_black_scholes_greeks(spot, strike, tau, vol, rate=rate)
        gamma = greeks["gamma"]
        vanna = greeks["vanna"]

        if opt_type.startswith("c"):
            call_gamma_sum += oi * gamma * (spot ** 2) * 100.0
            call_vanna_sum += oi * vanna * spot * 100.0
            call_iv_list.append(vol)
        else:
            put_gamma_sum += oi * gamma * (spot ** 2) * 100.0
            put_vanna_sum += oi * vanna * spot * 100.0
            put_iv_list.append(vol)

    gex_dealer = float(put_gamma_sum - call_gamma_sum)
    net_vanna = float(call_vanna_sum - put_vanna_sum)

    # Implied volatility skew (Put IV / Call IV)
    avg_put_iv = float(np.mean(put_iv_list)) if put_iv_list else 0.30
    avg_call_iv = float(np.mean(call_iv_list)) if call_iv_list else 0.30
    iv_skew = float(avg_put_iv / max(avg_call_iv, 1e-4))

    return gex_dealer, net_vanna, iv_skew


@register_strategy(
    StrategyMeta(
        strategy_id="option_gamma_accel",
        display_name="Option Surface Accelerator",
        score_column="option_surface_score",
        category="options",
        output_file="option_surface_predictions.txt",
        default_regime_weights={
            "BULL_LOW_VOL": 0.050,
            "BULL_HIGH_VOL": 0.060,
            "SIDEWAYS_LOW_VOL": 0.030,
            "SIDEWAYS_HIGH_VOL": 0.040,
            "BEAR_LOW_VOL": 0.020,
            "BEAR_HIGH_VOL": 0.015,
            "RELIEF_RALLY": 0.065,
            "PANIC_CRISIS": 0.010,
            "BULL": 0.050,
            "SIDEWAYS": 0.035,
            "BEAR": 0.015,
        },
    )
)
class OptionSurfaceAccelerator(BaseStrategyEngine):
    """
    Phase 140 Second-Order Analytical Options Surface Convexity Engine (Feature F683).
    Models dealer gamma inventory dynamics (short gamma acceleration when GEX < 0),
    dealer Vanna flows, Volga second-order volatility expansion, and IV skew inversion,
    coupled with realized asymmetric semivariance fallbacks for non-optionable securities.
    """

    def __init__(
        self,
        config: Optional[Any] = None,
        rate: float = 0.04,
    ) -> None:
        super().__init__(name="OptionSurfaceAccelerator", config=config)
        self.rate = rate

    @staticmethod
    def _canon_sym(s: Any) -> str:
        s_str = str(s).strip()
        part0 = s_str.split(".")[0]
        return part0.zfill(6) if part0.isdigit() else s_str.upper()

    def _compute_realized_semivariance_proxy(
        self,
        symbol: str,
        prices_dict: Dict[str, pd.DataFrame],
    ) -> Tuple[float, float, float]:
        """
        Analytical fallback for non-optionable / Korean equities:
        Computes realized downward vs upward semivariance, 20-day high proximity (Call Wall proxy),
        and realized Parkinson volatility convexity.
        """
        df_ohlcv = self.extract_ohlcv(symbol, prices_dict, min_bars=5)
        if df_ohlcv is None or len(df_ohlcv) < 5:
            return 0.0, 0.0, 1.0

        try:
            close_s = pd.to_numeric(df_ohlcv["Close"], errors="coerce").dropna()
            if len(close_s) < 5:
                return 0.0, 0.0, 1.0

            rets = close_s.pct_change().dropna().tail(20).to_numpy()
            if len(rets) < 5 or np.all(np.abs(rets) < 1e-8):
                return 0.0, 0.0, 1.0

            down_rets = rets[rets < 0.0]
            up_rets = rets[rets > 0.0]

            sigma_down = float(np.sqrt(np.mean(down_rets ** 2))) if len(down_rets) > 0 else 0.01
            sigma_up = float(np.sqrt(np.mean(up_rets ** 2))) if len(up_rets) > 0 else 0.01

            skew_ratio = float(max(sigma_down, 1e-5) / max(sigma_up, 1e-5))

            # Call wall proximity: distance from 20-day high
            c_now = float(close_s.iloc[-1])
            max_20 = float(close_s.tail(20).max())
            proximity = float(c_now / max_20) if max_20 > 0 else 1.0

            # GEX proxy: if price is pressing 20-day high (> 98%) with strong upward semivariance,
            # dealer is short gamma proxy
            gex_proxy = float(np.clip((proximity - 0.95) * 10.0, -1.0, 1.0))
            vanna_proxy = float(np.clip((sigma_up - sigma_down) * 5.0, -1.0, 1.0))

            return gex_proxy, vanna_proxy, skew_ratio
        except Exception:
            return 0.0, 0.0, 1.0

    def calculate_scores(
        self,
        symbols: Optional[List[str]] = None,
        prices_dict: Optional[Dict[str, pd.DataFrame]] = None,
        options_chain_dict: Optional[Dict[str, List[Dict[str, Any]]]] = None,
        **kwargs: Any
    ) -> pd.DataFrame:
        """Universal calculate_scores method compatible with test suites and pipeline runners."""
        if prices_dict is None and isinstance(symbols, dict):
            prices_dict = symbols
            symbols = None
        if symbols is not None and prices_dict is not None:
            prices_dict = {s: prices_dict[s] for s in symbols if s in prices_dict}
        return self.compute_scores(
            prices_dict=prices_dict,
            options_chain_dict=options_chain_dict,
            **kwargs
        )

    def compute_scores(
        self,
        prices_dict: Any,
        fundamentals_dict: Optional[Dict[str, Dict[str, Any]]] = None,
        indicators_df: Optional[Any] = None,
        options_chain_dict: Optional[Dict[str, List[Dict[str, Any]]]] = None,
        **kwargs: Any
    ) -> pd.DataFrame:
        """
        Computes Second-Order Analytical Options Surface Convexity scores.
        Returns ScoreDataFrame with ['symbol', 'option_surface_score'].
        """
        prices_source = kwargs.get("df_prices", prices_dict)
        if not prices_source:
            return make_score_dataframe({}, score_column="option_surface_score")

        if isinstance(prices_source, dict):
            p_dict = prices_source
            symbols = list(p_dict.keys())
        elif isinstance(prices_source, pd.DataFrame):
            if "symbol" in prices_source.columns:
                symbols = prices_source["symbol"].dropna().astype(str).unique().tolist()
                p_dict = {s: prices_source[prices_source["symbol"] == s] for s in symbols}
            else:
                symbols = list(prices_source.columns)
                p_dict = {col: pd.DataFrame({"Close": prices_source[col]}) for col in symbols}
        else:
            return make_score_dataframe({}, score_column="option_surface_score")

        chains = options_chain_dict or kwargs.get("options_chain_dict") or {}
        scores: Dict[str, float] = {}

        for sym in symbols:
            sym_str = str(sym).strip()
            sym_c = self._canon_sym(sym_str)

            # Spot price extraction
            spot = 100.0
            df_ohlcv = self.extract_ohlcv(sym_str, p_dict, min_bars=1)
            if df_ohlcv is not None and not df_ohlcv.empty:
                c_s = pd.to_numeric(df_ohlcv["Close"], errors="coerce").dropna()
                if not c_s.empty:
                    spot = float(c_s.iloc[-1])

            chain = chains.get(sym_str, chains.get(sym_c))

            if chain and isinstance(chain, list) and len(chain) > 0 and spot > 0.0:
                # Analytical Live Options Chain Processing
                gex_dealer, net_vanna, iv_skew = compute_net_dealer_gex_and_vanna(spot, chain, rate=self.rate)
                # Normalized GEX & Vanna
                gex_norm = float(np.tanh(-gex_dealer / 1e7))
                vanna_norm = float(np.tanh(net_vanna / 1e6))
                skew_accel = float(np.clip(1.0 - iv_skew, -0.50, 0.50))

                # Short gamma trigger (GEX < 0): positive squeeze impulse
                short_gamma_boost = float(abs(gex_norm)) if gex_dealer < 0.0 else 0.0
                raw_score = 0.50 + 0.30 * short_gamma_boost + 0.25 * vanna_norm + 0.25 * skew_accel
            else:
                # Realized Asymmetric Semivariance Fallback
                gex_proxy, vanna_proxy, skew_ratio = self._compute_realized_semivariance_proxy(sym_str, p_dict)
                skew_accel = float(np.clip(1.0 - skew_ratio, -0.50, 0.50))
                short_gamma_boost = float(max(0.0, gex_proxy))
                raw_score = 0.50 + 0.25 * short_gamma_boost + 0.20 * vanna_proxy + 0.20 * skew_accel

            clipped_score = float(np.clip(raw_score, 0.05, 0.98)) if np.isfinite(raw_score) else 0.50
            scores[sym_str] = round(clipped_score, 4)

        return make_score_dataframe(scores, score_column="option_surface_score")


# Module-level convenience functions
def compute_option_surface_scores(prices_dict: Any, **kwargs: Any) -> pd.DataFrame:
    """Convenience functional interface for OptionSurfaceAccelerator."""
    engine = OptionSurfaceAccelerator()
    return engine.compute_scores(prices_dict=prices_dict, **kwargs)

option_surface_accelerator_score = compute_option_surface_scores

# Complete Alias Trees
Phase140OptionSurfaceAccelerator = OptionSurfaceAccelerator
F683OptionSurfaceAccelerator = OptionSurfaceAccelerator
SecondOrderGreeksAccelerator = OptionSurfaceAccelerator
OptionsConvexityEngine = OptionSurfaceAccelerator
