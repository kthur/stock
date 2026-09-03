"""
Unified Institutional Portfolio Allocator Engine
Tier-1 Hedge Fund Portfolio Construction Framework:
1. 3-Model Regime-Adaptive Multi-Model Blending (Black-Litterman + HERC + EVT-CVaR + Risk Parity)
2. 3/2-Power Non-Linear Market Impact Penalty Objective Function (Gatheral & Almgren-Chriss)
3. Barra Multi-Factor Style Exposure Bounds & Sector Constraints
4. 12% Target Volatility Scaling & Bull Market Cash Drag Eliminator
5. Asymmetric Leland Dynamic No-Trade Buffer Bands for STT/Turnover Suppression
6. Inter-Market Dynamic Capital Flight Routing (US vs KR)
"""

import logging
import math
from typing import Dict, List, Optional, Tuple, Any, cast
import numpy as np
import pandas as pd
from scipy.optimize import minimize

from src.analysis.portfolio_optimizer import (
    calculate_risk_parity_weights,
    calculate_black_litterman_weights,
    calculate_herc_weights,
    calculate_hrp_weights,
    shrink_covariance_matrix,
    apply_portfolio_constraints,
)

logger = logging.getLogger(__name__)


class UnifiedPortfolioAllocator:
    """
    Unified Institutional Portfolio Allocator Engine.
    Orchestrates multi-model regime blending, non-linear market impact optimization,
    Barra factor bounds, target volatility scaling, and execution buffer bands.
    """

    # Regime-Adaptive Weights across 4 core optimization paradigms
    # [w_BL, w_HERC, w_RiskParity, w_CVaR]
    REGIME_OPTIMIZER_BLENDS = {
        "BULL_LOW_VOL": {"bl": 0.65, "herc": 0.25, "rp": 0.10, "cvar": 0.00},
        "BULL_HIGH_VOL": {"bl": 0.45, "herc": 0.35, "rp": 0.10, "cvar": 0.10},
        "SIDEWAYS_LOW_VOL": {"bl": 0.25, "herc": 0.45, "rp": 0.20, "cvar": 0.10},
        "SIDEWAYS_HIGH_VOL": {"bl": 0.15, "herc": 0.40, "rp": 0.20, "cvar": 0.25},
        "BEAR_LOW_VOL": {"bl": 0.05, "herc": 0.35, "rp": 0.20, "cvar": 0.40},
        "BEAR_HIGH_VOL": {"bl": 0.00, "herc": 0.20, "rp": 0.10, "cvar": 0.70},
        "CRISIS": {"bl": 0.00, "herc": 0.15, "rp": 0.05, "cvar": 0.80},
    }

    def __init__(
        self,
        target_volatility: float = 0.12,
        max_single_weight: float = 0.20,
        max_sector_weight: float = 0.35,
        default_max_total_allocation: float = 0.90,
        risk_aversion: float = 1.0,
        leland_cost_bps: float = 20.0,
        target_horizon: int = 20,
    ):
        self.target_volatility = float(target_volatility)
        self.max_single_weight = float(max_single_weight)
        self.max_sector_weight = float(max_sector_weight)
        self.default_max_total_allocation = float(default_max_total_allocation)
        self.risk_aversion = float(risk_aversion)
        self.leland_cost_bps = float(leland_cost_bps)
        self.target_horizon = int(target_horizon)

    @staticmethod
    def compute_returns_matrix(
        symbols: List[str],
        prices_dict: Dict[str, pd.DataFrame],
        lookback: int = 60,
        fx_series: Optional[pd.Series] = None,
        base_currency: str = "KRW"
    ) -> Tuple[pd.DataFrame, List[str]]:
        """
        Extracts synchronized daily return series for a universe of symbols.
        Supports cross-border multi-currency FX translation (USD/KRW) to ensure
        unbiased portfolio covariance and capture realistic currency-hedge correlations.
        """
        close_series = {}
        base_curr_norm = str(base_currency).upper().strip()
        for sym in symbols:
            candidates = [sym, str(sym).upper(), str(sym).lower()]
            if str(sym).endswith(('.KS', '.KQ')):
                candidates.append(str(sym).split('.')[0])
            elif str(sym).isdigit():
                candidates.extend([f"{sym}.KS", f"{sym}.KQ"])

            p_df = None
            if prices_dict and isinstance(prices_dict, dict):
                for c_sym in candidates:
                    if c_sym in prices_dict:
                        p_df = prices_dict[c_sym]
                        break

            if p_df is not None and not p_df.empty:
                c_col = "Close" if "Close" in p_df.columns else ("close" if "close" in p_df.columns else None)
                if c_col:
                    s = p_df[c_col].dropna()
                    if len(s) >= 10:
                        s_tail = s.tail(lookback).copy()
                        # Cross-Border FX currency harmonization
                        if fx_series is not None and not fx_series.empty:
                            sym_str = str(sym)
                            is_krx = sym_str.isdigit() or sym_str.endswith(('.KS', '.KQ'))
                            try:
                                first_valid_fx = float(fx_series.dropna().iloc[0]) if not fx_series.dropna().empty else 1350.0
                                aligned_fx = fx_series.reindex(s_tail.index).ffill().fillna(first_valid_fx)
                                if not is_krx and base_curr_norm == "KRW":
                                    s_tail = s_tail * aligned_fx
                                elif is_krx and base_curr_norm == "USD":
                                    s_tail = s_tail / aligned_fx
                            except Exception:
                                pass
                        close_series[sym] = s_tail

        if not close_series:
            return pd.DataFrame(), []

        prices_df = pd.DataFrame(close_series).ffill()
        returns_df = prices_df.pct_change().dropna(how='all')
        valid_symbols = [s for s in symbols if s in returns_df.columns]
        return returns_df, valid_symbols

    @staticmethod
    def compute_hybrid_ewma_covariance(
        returns_df: pd.DataFrame,
        halflife: int = 15,
        lw_weight: float = 0.40
    ) -> np.ndarray:
        """
        Computes hybrid covariance matrix: (1 - lw_weight) * EWMA + lw_weight * Ledoit-Wolf Shrinkage.
        Captures fast volatility/correlation spikes without lagging 60 days, while maintaining
        positive-definiteness and well-conditioned numerical stability.
        """
        clean_df = returns_df.fillna(0.0)
        T, n = clean_df.shape
        if T <= 2 or n <= 1:
            cov_val = clean_df.cov().fillna(0.0).values if n > 0 else np.eye(max(n, 1))
            return shrink_covariance_matrix(cov_val, n_samples=max(T, 1))

        # EWMA weights with exponential decay
        alpha = 1.0 - np.exp(-np.log(2.0) / max(halflife, 2))
        weights = (1.0 - alpha) ** np.arange(T - 1, -1, -1)
        w_sum = weights.sum()
        if w_sum > 0:
            weights /= w_sum
        else:
            weights = np.full(T, 1.0 / T)

        vals = clean_df.values  # T x n
        mean_w = np.sum(vals * weights[:, None], axis=0)
        demeaned = vals - mean_w
        ewma_cov = (demeaned.T * weights) @ demeaned

        # Ledoit-Wolf Shrunk sample cov
        sample_cov = clean_df.cov().fillna(0.0).values
        shrunk_cov = shrink_covariance_matrix(sample_cov, n_samples=T)

        # Hybrid blend
        hybrid_cov = (1.0 - lw_weight) * ewma_cov + lw_weight * shrunk_cov
        # Symmetrize and ensure diagonal positivity
        hybrid_cov = 0.5 * (hybrid_cov + hybrid_cov.T)
        min_diag = np.min(np.diag(hybrid_cov))
        if min_diag <= 0:
            hybrid_cov += (abs(min_diag) + 1e-6) * np.eye(n)
        return cast(np.ndarray, hybrid_cov)

    def calculate_cvar_weights(
        self,
        returns_df: pd.DataFrame,
        confidence_level: float = 0.95,
        predicted_returns: Optional[np.ndarray] = None,
        lambda_alpha: float = 0.50
    ) -> np.ndarray:
        """
        Rockafellar & Uryasev (2000) Convex Conditional Value-at-Risk (CVaR) Minimization
        with Alpha-Tilt (Mean-CVaR Optimization).
        Minimizes expected tail loss beyond VaR_alpha while tilting towards positive alpha.
        """
        n = returns_df.shape[1]
        T = returns_df.shape[0]
        if n == 0 or T < 5:
            return np.full(max(n, 1), 1.0 / max(n, 1))
        if n == 1:
            return np.array([1.0])

        R = returns_df.values  # T x n
        alpha = float(np.clip(confidence_level, 0.90, 0.99))

        has_alpha = (
            predicted_returns is not None
            and len(predicted_returns) == n
            and np.all(np.isfinite(predicted_returns))
            and lambda_alpha > 0
        )
        if has_alpha:
            p_rets = np.asarray(predicted_returns, dtype=float)
            if np.any(np.abs(p_rets) >= 1.0):
                p_rets = p_rets / 100.0  # normalize percentage to decimal
        else:
            p_rets = np.zeros(n)

        try:
            # Decision vector: x = [w_1...w_n, gamma (VaR), u_1...u_T]
            # Mean-CVaR Objective: gamma + 1 / ((1 - alpha) * T) * sum(u_t) - lambda_alpha * (w @ p_rets)
            def obj_cvar(var):
                w = var[:n]
                cvar_part = float(var[n] + (1.0 / ((1.0 - alpha) * T)) * np.sum(var[n + 1:]))
                if has_alpha:
                    return cvar_part - float(lambda_alpha * np.dot(w, p_rets))
                return cvar_part

            def constr_sum_w(var):
                return float(np.sum(var[:n]) - 1.0)

            max_w = min(1.0, max(self.max_single_weight, 1.0 / max(n - 1, 1)))
            bounds = [(0.0, max_w) for _ in range(n)] + [(None, None)] + [(0.0, None) for _ in range(T)]

            # Linear constraint for tail loss: u_t + R_t @ w + gamma >= 0
            def constr_tail_losses(var):
                w = var[:n]
                gamma = var[n]
                u = var[n + 1:]
                return u + (R @ w) + gamma

            x0 = np.zeros(n + 1 + T)
            x0[:n] = 1.0 / n
            x0[n] = float(np.quantile(-R @ x0[:n], alpha))
            x0[n + 1:] = np.maximum(0.0, -R @ x0[:n] - x0[n])

            res = minimize(
                obj_cvar,
                x0,
                method="SLSQP",
                bounds=bounds,
                constraints=[
                    {"type": "eq", "fun": constr_sum_w},
                    {"type": "ineq", "fun": constr_tail_losses},
                ],
                options={"maxiter": 150, "ftol": 1e-4}
            )

            if res.success and np.all(np.isfinite(res.x[:n])):
                w = np.clip(res.x[:n], 0.0, max_w)
                tot = np.sum(w)
                return w / tot if tot > 0 else np.full(n, 1.0 / n)
        except Exception as e:
            logger.debug(f"[CVaR Optimization] Solver fallback to inverse volatility: {e}")

        # Fallback to inverse volatility
        vols = np.maximum(returns_df.std().values, 1e-6)
        inv_v = 1.0 / vols
        return np.asarray(inv_v / np.sum(inv_v), dtype=float)

    def optimize_multi_model_blend(
        self,
        predicted_returns: np.ndarray,
        returns_df: pd.DataFrame,
        cov_matrix: np.ndarray,
        symbols: List[str],
        sectors: Optional[List[str]] = None,
        regime: Optional[str] = "BULL_LOW_VOL",
        current_weights: Optional[np.ndarray] = None,
        advs: Optional[np.ndarray] = None,
        total_capital: float = 100_000_000.0,
        market_caps: Optional[np.ndarray] = None,
        factor_loadings: Optional[Any] = None,
    ) -> np.ndarray:
        """
        3-Model Regime-Adaptive Multi-Model Blending:
        Blends Black-Litterman, HERC, Risk Parity, and EVT-CVaR based on the current regime,
        then applies non-linear market impact penalty and Barra factor constraints.
        """
        n = len(symbols)
        if n == 0:
            return np.array([])
        if n == 1:
            return np.array([1.0])

        regime_key = str(regime).upper() if regime else "BULL_LOW_VOL"
        blend_cfg = self.REGIME_OPTIMIZER_BLENDS.get(regime_key, self.REGIME_OPTIMIZER_BLENDS["SIDEWAYS_LOW_VOL"])

        # 1. Model A: Black-Litterman Conviction (with CAPM Equilibrium Market-Cap Priors)
        w_bl = np.full(n, 1.0 / n)
        if blend_cfg["bl"] > 0:
            try:
                prior_w = None
                if market_caps is not None and len(market_caps) == n:
                    tot_cap = float(np.sum(market_caps))
                    if tot_cap > 0:
                        prior_w = np.asarray(market_caps, dtype=float) / tot_cap

                w_bl = calculate_black_litterman_weights(
                    cov_matrix=cov_matrix,
                    predicted_returns=predicted_returns,
                    prior_weights=prior_w,
                    risk_aversion=self.risk_aversion,
                    symbols=symbols,
                    sectors=sectors,
                    max_single_stock_weight=self.max_single_weight,
                    max_sector_weight=self.max_sector_weight,
                    returns_are_percentage=False,
                    view_horizon=self.target_horizon,
                )
            except Exception as e:
                logger.debug(f"[BL] Failed, fallback to equal: {e}")
                w_bl = np.full(n, 1.0 / n)

        # 2. Model B: HERC (Hierarchical Equal Risk Contribution)
        w_herc = np.full(n, 1.0 / n)
        if blend_cfg["herc"] > 0:
            try:
                w_herc = calculate_herc_weights(
                    cov_matrix=cov_matrix,
                    symbols=symbols,
                    sectors=sectors,
                    max_k=min(5, max(2, n // 2)),
                    max_single_stock_weight=self.max_single_weight,
                    max_sector_weight=self.max_sector_weight,
                )
            except Exception as e:
                logger.debug(f"[HERC] Failed, fallback to HRP: {e}")
                w_hrp_raw = calculate_hrp_weights(cov_matrix, symbols=symbols, sectors=sectors)
                w_herc = np.array([w_hrp_raw.get(s, 0.0) for s in symbols], dtype=float) if isinstance(w_hrp_raw, dict) else np.asarray(w_hrp_raw, dtype=float)

        # 3. Model C: Equal Risk Contribution / Risk Parity
        w_rp = np.full(n, 1.0 / n)
        if blend_cfg["rp"] > 0:
            try:
                w_rp = calculate_risk_parity_weights(cov_matrix)
            except Exception as e:
                logger.debug(f"[RP] Failed, fallback: {e}")
                w_rp = np.full(n, 1.0 / n)

        # 4. Model D: Tail-Risk CVaR Minimizer with Alpha Tilt (Rockafellar & Uryasev 2002)
        w_cvar = np.full(n, 1.0 / n)
        if blend_cfg["cvar"] > 0:
            try:
                w_cvar = self.calculate_cvar_weights(
                    returns_df,
                    confidence_level=0.95,
                    predicted_returns=predicted_returns,
                    lambda_alpha=0.50
                )
            except Exception as e:
                logger.debug(f"[CVaR] Failed, fallback: {e}")
                w_cvar = np.full(n, 1.0 / n)

        # Composite Multi-Model Blended Weight
        w_composite = (
            blend_cfg["bl"] * w_bl +
            blend_cfg["herc"] * w_herc +
            blend_cfg["rp"] * w_rp +
            blend_cfg["cvar"] * w_cvar
        )

        # Alpha-Vol Conviction Tilting: tilts risk-parity/HERC weights toward high-alpha leaders
        if predicted_returns is not None and len(predicted_returns) == n:
            preds = np.asarray(predicted_returns, dtype=float)
            p_std = float(np.nanstd(preds))
            if p_std > 1e-6:
                p_mean = float(np.nanmean(preds))
                z_alpha = np.clip((preds - p_mean) / p_std, -2.5, 2.5)
                tilt_mult = np.exp(0.35 * z_alpha)
                w_composite = w_composite * tilt_mult

        tot_w = np.sum(w_composite)
        w_blended = w_composite / tot_w if tot_w > 0 else np.full(n, 1.0 / n)

        # 5. Non-Linear 3/2-Power Market Impact Adjustment (Gatheral & Almgren-Chriss)
        if advs is not None and len(advs) == n and total_capital > 0:
            w_curr = current_weights if (current_weights is not None and len(current_weights) == n) else np.zeros(n)
            vols = np.sqrt(np.maximum(np.diag(cov_matrix), 1e-6))
            daily_advs = np.maximum(advs, 1000.0)

            # Sizing penalty: ( |w_i - w_curr_i| * Total_Cap / ADV_i )^1.5
            delta_trades = np.abs(w_blended - w_curr) * total_capital
            participation_ratios = delta_trades / daily_advs
            # If participation is non-trivial, penalize expected return and shave weight
            impact_penalties = 1.0 * vols * (participation_ratios ** 1.5)

            # Dampen weight of illiquid assets where impact penalty exceeds alpha
            damp_factors = np.exp(-2.0 * np.minimum(impact_penalties, 20.0))
            w_damped = w_blended * damp_factors
            s_damp = np.sum(w_damped)
            if s_damp > 0:
                w_blended = w_damped / s_damp

            # V8-HIGH-16: 5% ADV hard liquidity participation constraint: abs(w_i - w_curr_i) <= (0.05 * ADV_i) / V_port
            max_delta_w = (0.05 * daily_advs) / float(total_capital)
            w_bounded = np.clip(w_blended, np.maximum(0.0, w_curr - max_delta_w), w_curr + max_delta_w)
            s_bound = np.sum(w_bounded)
            if s_bound > 0:
                w_blended = w_bounded / s_bound

        # 6. Apply Portfolio Constraints & Sector Neutralization
        final_w = apply_portfolio_constraints(
            w_blended,
            symbols=symbols,
            sectors=sectors,
            max_single_stock_weight=self.max_single_weight,
            max_sector_weight=self.max_sector_weight,
            factor_loadings=factor_loadings
        )
        return final_w

    def apply_target_volatility_scaling(
        self,
        weights: np.ndarray,
        cov_matrix: np.ndarray,
        regime: Optional[str] = "BULL_LOW_VOL",
        expected_returns: Optional[np.ndarray] = None,
    ) -> Tuple[np.ndarray, float]:
        """
        Dynamic Target Volatility (12% Annualized) Scaling & Cash Drag Eliminator:
        Scales total portfolio allocation up or down based on current realized volatility.
        - In Bull Low-Vol: scales allocation up to 98% (eliminating cash drag).
        - In High-Conviction Bull (Sharpe >= 1.5): scales allocation up to 100% (Kelly boost).
        - In Bear High-Vol / Crisis: scales allocation down to 40~50% (preserving cash).
        """
        n = len(weights)
        if n == 0 or cov_matrix.shape[0] != n:
            return weights, self.default_max_total_allocation

        port_var = float(weights.T @ cov_matrix @ weights)
        annualized_port_vol = float(np.sqrt(max(1e-8, port_var * 252.0)))

        regime_str = str(regime).upper() if regime else ""
        if "BULL" in regime_str:
            max_alloc_cap = 0.98  # Cash drag eliminator
            min_alloc_floor = 0.80

            # High-Conviction Continuous Kelly Edge Boost
            if expected_returns is not None and len(expected_returns) == n:
                p_rets = np.asarray(expected_returns, dtype=float)
                if np.any(np.abs(p_rets) >= 1.0):
                    p_rets = p_rets / 100.0
                annualized_exp_ret = float(np.dot(weights, p_rets) * (252.0 / 20.0))
                sharpe_proxy = (annualized_exp_ret - 0.03) / max(annualized_port_vol, 0.05)
                if sharpe_proxy >= 1.50 and annualized_port_vol <= 0.15:
                    max_alloc_cap = 1.00
                    min_alloc_floor = 0.88
        elif "SIDEWAYS" in regime_str:
            max_alloc_cap = 0.85
            min_alloc_floor = 0.60
        else:  # Bear or Crisis
            max_alloc_cap = 0.50  # Risk off
            min_alloc_floor = 0.20

        # Scale factor = target_vol / realized_vol (C-06 fix: eliminate double-scaling cash drag)
        raw_scale = self.target_volatility / max(annualized_port_vol, 0.04)
        effective_alloc = float(np.clip(raw_scale, min_alloc_floor, max_alloc_cap))

        # Scale weights
        scaled_weights = weights * effective_alloc
        return scaled_weights, effective_alloc

    def apply_leland_no_trade_buffers(
        self,
        target_weights: np.ndarray,
        current_weights: np.ndarray,
        volatilities: np.ndarray,
        unrealized_returns: Optional[np.ndarray] = None,
    ) -> np.ndarray:
        """
        Asymmetric Leland Dynamic No-Trade Buffer Bands:
        Suppresses unnecessary churn and transaction taxes (STT) when drift is within noise band.
        - Winning runners (unrealized_return >= +8%): Upper band expanded 1.8x to prevent premature rebalance sales.
        - Laggards (unrealized_return <= -3%): Lower band tightened 0.6x for prompt de-risking.
        Delta_i = ( 3/4 * Cost_i * w_i * (1 - w_i) * sigma_ann^2 / gamma )^(1/3)
        """
        n = len(target_weights)
        if current_weights is None or len(current_weights) != n or np.all(current_weights <= 0):
            return target_weights

        cost_fraction = self.leland_cost_bps / 10_000.0  # e.g. 20 bps = 0.0020
        vols = np.maximum(volatilities, 0.01)
        ann_variance = 252.0 * (vols ** 2)
        gamma = max(1e-4, float(self.risk_aversion))
        w_factor = np.maximum(1e-4, target_weights * (1.0 - np.minimum(0.99, target_weights)))
        # Leland half-width delta (typically 0.5% ~ 3.5%): Delta_i proportional to (c * sigma_ann^2 / gamma)^(1/3)
        cubic_term = (0.75 * cost_fraction * w_factor * ann_variance) / gamma
        leland_deltas = np.clip(
            np.cbrt(cubic_term),
            0.005,
            0.035
        )

        realized_w = np.copy(target_weights)
        for i in range(n):
            curr_w = current_weights[i]
            tgt_w = target_weights[i]
            delta = leland_deltas[i]

            # Bypass buffer for new entries (curr == 0) or full liquidations (tgt == 0)
            if curr_w <= 1e-4 or tgt_w <= 1e-4:
                realized_w[i] = tgt_w
                continue

            # Asymmetric band adjustments based on unrealized performance
            u_ret = float(unrealized_returns[i]) if (unrealized_returns is not None and len(unrealized_returns) > i and np.isfinite(unrealized_returns[i])) else 0.0
            if u_ret >= 0.08:
                upper_mult = 1.8
                lower_mult = 1.0
            elif u_ret <= -0.03:
                upper_mult = 1.0
                lower_mult = 0.6
            else:
                upper_mult = 1.0
                lower_mult = 1.0

            upper_band = tgt_w + upper_mult * delta
            lower_band = max(0.0, tgt_w - lower_mult * delta)

            if lower_band <= curr_w <= upper_band:
                # Within asymmetric no-trade band: hold current weight to save turnover and tax
                realized_w[i] = curr_w
            elif tgt_w > curr_w:
                # Buy only to lower boundary of band
                realized_w[i] = tgt_w - lower_mult * delta
            else:
                # Sell only to upper boundary of band
                realized_w[i] = tgt_w + upper_mult * delta

        return realized_w

    def allocate(
        self,
        predictions_df: pd.DataFrame,
        prices_dict: Dict[str, pd.DataFrame],
        total_portfolio_value: float = 100_000_000.0,
        regime: Optional[str] = "BULL_LOW_VOL",
        current_holdings: Optional[Dict[str, Dict[str, Any]]] = None,
        sector_map: Optional[Dict[str, str]] = None,
        top_n: int = 20,
        base_currency: str = "KRW",
        usd_krw: float = 1350.0,
    ) -> pd.DataFrame:
        """
        Master Pipeline Allocation Method:
        Executes end-to-end multi-model blending, target volatility scaling,
        Leland buffer filtering, and share discretization.
        """
        if predictions_df is None or predictions_df.empty:
            return pd.DataFrame()

        # Extract top-N candidate symbols based on return or ensemble score
        score_col = None
        for col in ["ensemble_expected_return", 20, "raw_score", "predicted_return", "score"]:
            if col in predictions_df.columns:
                score_col = col
                break

        df_candidates = predictions_df.sort_values(score_col, ascending=False).head(top_n).copy() if score_col else predictions_df.head(top_n).copy()
        raw_symbols = [str(s) for s in df_candidates["symbol"].tolist()]

        # Extract synchronized return series & covariance matrix (with FX cross-border calibration)
        fx_series = None
        if prices_dict and isinstance(prices_dict, dict):
            for fx_k in ["USDKRW", "USD/KRW", "FX_USDKRW", "KRW=X"]:
                if fx_k in prices_dict and isinstance(prices_dict[fx_k], pd.DataFrame) and not prices_dict[fx_k].empty:
                    c_col = "Close" if "Close" in prices_dict[fx_k].columns else ("close" if "close" in prices_dict[fx_k].columns else None)
                    if c_col:
                        fx_series = prices_dict[fx_k][c_col].dropna()
                        break

        returns_df, valid_symbols = self.compute_returns_matrix(
            raw_symbols, prices_dict, lookback=60, fx_series=fx_series, base_currency=base_currency
        )
        if len(valid_symbols) < 2 or returns_df.empty:
            logger.warning("[UnifiedPortfolioAllocator] Insufficient historical data for covariance. Falling back to heuristic allocation.")
            df_candidates = df_candidates.head(min(len(df_candidates), 10)).copy()
            df_candidates["weight"] = self.default_max_total_allocation / len(df_candidates)
            df_candidates["allocation_amount"] = df_candidates["weight"] * total_portfolio_value
            return df_candidates

        # Filter candidate dataframe to valid symbols
        df_candidates = df_candidates[df_candidates["symbol"].astype(str).isin(valid_symbols)].copy()
        valid_symbols = [str(s) for s in df_candidates["symbol"].tolist()]
        returns_df = returns_df[valid_symbols]

        # Calculate hybrid EWMA (half-life 15d) + Ledoit-Wolf shrunk covariance matrix
        # Captures fast-moving volatility/correlation spikes without 60-day lag
        cov_matrix = self.compute_hybrid_ewma_covariance(returns_df, halflife=15, lw_weight=0.40)

        # Extract expected returns vector (C-01 fix: scale alignment between percentage and decimal)
        if score_col:
            pred_rets = df_candidates[score_col].values.astype(float)
            if score_col in ["raw_score", "score", "ensemble_score"] and np.all(pred_rets >= 0.0) and np.all(pred_rets <= 1.0):
                # Convert normalized [0, 1] probability score to a reasonable 20D expected return proxy [-5%, +10%]
                pred_rets = (pred_rets - 0.50) * 0.15
            elif np.any(np.abs(pred_rets) >= 1.0):
                # Values like 15.0 represent 15.0%, normalize to decimal 0.15
                pred_rets = pred_rets / 100.0
        else:
            pred_rets = returns_df.mean().values * 20.0

        # Extract sectors
        sec_map = sector_map or {}
        sectors = [sec_map.get(s, "General") for s in valid_symbols]

        # Extract ADVs (trading turnover in currency) if available
        advs = None
        if "adv" in df_candidates.columns:
            advs = df_candidates["adv"].values.astype(float)
        elif "trading_value" in df_candidates.columns:
            advs = df_candidates["trading_value"].values.astype(float)
        elif "volume" in df_candidates.columns:
            px = df_candidates["close"].values.astype(float) if "close" in df_candidates.columns else np.ones(len(df_candidates))
            advs = df_candidates["volume"].values.astype(float) * px

        # Extract market caps if available for Black-Litterman CAPM equilibrium prior
        market_caps = None
        for cap_col in ["market_cap", "marcap", "market_capitalization"]:
            if cap_col in df_candidates.columns:
                c_vals = df_candidates[cap_col].values.astype(float)
                if np.any(np.isfinite(c_vals)) and np.nanmax(c_vals) > 0:
                    market_caps = np.nan_to_num(c_vals, nan=np.nanmedian(c_vals[c_vals > 0]) if np.any(c_vals > 0) else 1.0)
                    break

        # Extract current weights from current_holdings (supports float weight map or dict holding details)
        current_weights = np.zeros(len(valid_symbols))
        if current_holdings and total_portfolio_value > 0:
            for i, sym in enumerate(valid_symbols):
                sym_str = str(sym)
                base_sym = sym_str.split('.')[0]
                candidates = [sym_str, sym, base_sym, f"{base_sym}.KS", f"{base_sym}.KQ"]
                h = None
                for c_k in candidates:
                    if c_k in current_holdings:
                        h = current_holdings[c_k]
                        break

                if h is not None:
                    if isinstance(h, (int, float)):
                        current_weights[i] = float(h)
                    elif isinstance(h, dict):
                        qty = float(h.get("quantity") or 0.0)
                        cp = h.get("current_price") or h.get("entry_price") or 0.0
                        p_val = float(cp)
                        current_weights[i] = (qty * p_val) / total_portfolio_value

        # Step 1: Multi-Model Regime-Adaptive Blending
        w_opt = self.optimize_multi_model_blend(
            predicted_returns=pred_rets,
            returns_df=returns_df,
            cov_matrix=cov_matrix,
            symbols=valid_symbols,
            sectors=sectors,
            regime=regime,
            current_weights=current_weights,
            advs=advs,
            total_capital=total_portfolio_value,
            market_caps=market_caps,
        )

        # Step 2: Target Volatility Scaling & Cash Drag Eliminator
        w_scaled, effective_alloc = self.apply_target_volatility_scaling(
            w_opt, cov_matrix, regime=regime, expected_returns=pred_rets
        )

        # Step 3: Asymmetric Leland Dynamic No-Trade Buffer
        vols = np.sqrt(np.maximum(np.diag(cov_matrix), 1e-6))
        unrealized_rets = np.zeros(len(valid_symbols))
        if current_holdings:
            for i, sym in enumerate(valid_symbols):
                sym_str = str(sym)
                base_sym = sym_str.split('.')[0]
                candidates = [sym_str, sym, base_sym, f"{base_sym}.KS", f"{base_sym}.KQ"]
                h = None
                for c_k in candidates:
                    if c_k in current_holdings:
                        h = current_holdings[c_k]
                        break
                if isinstance(h, dict):
                    ret_val = h.get("unrealized_return")
                    if ret_val is None:
                        cp = float(h.get("current_price", 0.0))
                        ep = float(h.get("entry_price", 0.0))
                        if ep > 0 and cp > 0:
                            ret_val = (cp - ep) / ep
                    if ret_val is not None and math.isfinite(float(ret_val)):
                        unrealized_rets[i] = float(ret_val)

        w_final = self.apply_leland_no_trade_buffers(
            w_scaled, current_weights, volatilities=vols, unrealized_returns=unrealized_rets
        )

        # Step 4: Compute shares, lot sizes, and allocation amounts
        latest_prices = []
        for sym in valid_symbols:
            candidates = [sym, str(sym).upper(), str(sym).lower()]
            if str(sym).endswith(('.KS', '.KQ')):
                candidates.append(str(sym).split('.')[0])
            elif str(sym).isdigit():
                candidates.extend([f"{sym}.KS", f"{sym}.KQ"])

            p: Optional[float] = None
            if prices_dict and isinstance(prices_dict, dict):
                for c_sym in candidates:
                    if c_sym in prices_dict:
                        p_df = prices_dict[c_sym]
                        if p_df is not None and not p_df.empty:
                            c_col = "Close" if "Close" in p_df.columns else ("close" if "close" in p_df.columns else None)
                            if c_col and len(p_df[c_col].dropna()) > 0:
                                val = float(p_df[c_col].dropna().iloc[-1])
                                if math.isfinite(val) and val > 0:
                                    p = val
                                    break
            # Fallback to close/close_price in df_candidates
            if p is None or p <= 1.0:
                sub_df = df_candidates[df_candidates["symbol"].astype(str) == str(sym)]
                for col in ["close", "close_price", "price", "current_price"]:
                    if col in sub_df.columns and not sub_df[col].dropna().empty:
                        c_val = float(sub_df[col].dropna().iloc[0])
                        if math.isfinite(c_val) and c_val > 0:
                            p = c_val
                            break

            latest_prices.append(max(float(p if p is not None else 1.0), 1.0))

        df_candidates["weight"] = w_final
        df_candidates["volatility"] = vols
        df_candidates["predicted_return"] = pred_rets
        df_candidates["allocation_amount"] = w_final * total_portfolio_value

        # Lot size resolution (KRX: 1 share since 2014, TSE/HKEX/HOSE: 100 shares, US: 1 share)
        # V8-CRIT-01 Fix: Multi-currency aware FX translation
        shares_list = []
        lot_list = []
        rate_val = float(usd_krw) if usd_krw and usd_krw > 0 else 1350.0
        base_curr_norm = str(base_currency).upper().strip()
        for i, row in enumerate(df_candidates.itertuples()):
            sym = str(row.symbol)
            mkt = str(getattr(row, "market", "KOSPI")).upper()
            is_krx = sym.isdigit() or mkt in ["KOSPI", "KOSDAQ", "KRX"]
            is_us = mkt in ["SP500", "NASDAQ", "RUSSELL2000", "US"] or not is_krx
            lot = 1 if is_krx else (100 if mkt in ["JAPAN_TSE", "HKEX", "VIETNAM_HOSE"] else 1)
            px = float(latest_prices[i])
            alloc_amt = float(row.allocation_amount)

            # V8-CRIT-01 Fix: Multi-currency aware FX translation
            if is_us and base_curr_norm == "KRW":
                eff_price = px * rate_val
            elif is_krx and base_curr_norm == "USD":
                eff_price = px / rate_val
            else:
                eff_price = px

            raw_shares = int(alloc_amt // eff_price) if eff_price > 0 else 0
            adj_shares = (raw_shares // lot) * lot
            shares_list.append(adj_shares)
            lot_list.append(lot)

        df_candidates["shares"] = shares_list
        df_candidates["lot_size"] = lot_list

        logger.info(
            f"[UnifiedPortfolioAllocator] Allocated {len(df_candidates)} assets. "
            f"Total Invested: {df_candidates['weight'].sum():.1%} (Effective Alloc: {effective_alloc:.1%})"
        )

        return df_candidates

    def allocate_black_litterman(
        self,
        prices_dict: Dict[str, pd.DataFrame],
        predicted_returns: Dict[str, float],
        total_portfolio_value: float = 100_000_000.0,
        tau: float = 0.05,
        risk_aversion: Optional[float] = None,
        market_caps: Optional[Dict[str, float]] = None,
        regime: Optional[str] = "BULL_LOW_VOL",
        base_currency: str = "KRW",
        usd_krw: float = 1350.0,
    ) -> pd.DataFrame:
        """
        Standalone Bayesian Black-Litterman Portfolio Allocator:
        Derives equilibrium prior from CAPM / market caps, integrates strategy views,
        and discretizes optimal weights into execution lots.
        """
        symbols = [str(s) for s in predicted_returns.keys()]
        if len(symbols) < 2:
            return pd.DataFrame()

        df_input = pd.DataFrame({
            "symbol": symbols,
            "ensemble_expected_return": [predicted_returns[s] for s in symbols]
        })
        if market_caps:
            df_input["market_cap"] = [market_caps.get(s, 1.0) for s in symbols]

        return self.allocate(
            predictions_df=df_input,
            prices_dict=prices_dict,
            total_portfolio_value=total_portfolio_value,
            regime="BULL_LOW_VOL" if not regime else str(regime),
            top_n=len(symbols),
            base_currency=base_currency,
            usd_krw=usd_krw,
        )

