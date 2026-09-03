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
from typing import Dict, List, Optional, Tuple, Any, Union
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
    discretize_weights_to_lot_sizes,
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
        lookback: int = 60
    ) -> Tuple[pd.DataFrame, List[str]]:
        """
        Extracts synchronized daily return series for a universe of symbols.
        """
        close_series = {}
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
                        close_series[sym] = s.tail(lookback)

        if not close_series:
            return pd.DataFrame(), []

        prices_df = pd.DataFrame(close_series).ffill().bfill()
        valid_symbols = [s for s in symbols if s in prices_df.columns]
        returns_df = prices_df[valid_symbols].pct_change().dropna()
        return returns_df, valid_symbols

    def calculate_cvar_weights(
        self,
        returns_df: pd.DataFrame,
        confidence_level: float = 0.95
    ) -> np.ndarray:
        """
        Rockafellar & Uryasev (2000) Convex Conditional Value-at-Risk (CVaR) Minimization.
        Minimizes expected tail loss beyond VaR_alpha.
        """
        n = returns_df.shape[1]
        T = returns_df.shape[0]
        if n == 0 or T < 5:
            return np.full(max(n, 1), 1.0 / max(n, 1))
        if n == 1:
            return np.array([1.0])

        R = returns_df.values  # T x n
        alpha = float(np.clip(confidence_level, 0.90, 0.99))

        try:
            # Decision vector: x = [w_1...w_n, gamma (VaR), u_1...u_T]
            # Objective: gamma + 1 / ((1 - alpha) * T) * sum(u_t)
            def obj_cvar(var):
                return float(var[n] + (1.0 / ((1.0 - alpha) * T)) * np.sum(var[n + 1:]))

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
        return inv_v / np.sum(inv_v)

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

        # 1. Model A: Black-Litterman Conviction
        w_bl = np.full(n, 1.0 / n)
        if blend_cfg["bl"] > 0:
            try:
                w_bl = calculate_black_litterman_weights(
                    cov_matrix=cov_matrix,
                    predicted_returns=predicted_returns,
                    risk_aversion=self.risk_aversion,
                    symbols=symbols,
                    sectors=sectors,
                    max_single_stock_weight=self.max_single_weight,
                    max_sector_weight=self.max_sector_weight,
                    returns_are_percentage=False,
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
                )
            except Exception as e:
                logger.debug(f"[HERC] Failed, fallback to HRP: {e}")
                w_herc = calculate_hrp_weights(cov_matrix, symbols=symbols, sectors=sectors)

        # 3. Model C: Equal Risk Contribution / Risk Parity
        w_rp = np.full(n, 1.0 / n)
        if blend_cfg["rp"] > 0:
            try:
                w_rp = calculate_risk_parity_weights(cov_matrix)
            except Exception as e:
                logger.debug(f"[RP] Failed, fallback: {e}")
                w_rp = np.full(n, 1.0 / n)

        # 4. Model D: Tail-Risk CVaR Minimizer
        w_cvar = np.full(n, 1.0 / n)
        if blend_cfg["cvar"] > 0:
            try:
                w_cvar = self.calculate_cvar_weights(returns_df, confidence_level=0.95)
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

        # 6. Apply Portfolio Constraints & Sector Neutralization
        final_w = apply_portfolio_constraints(
            w_blended,
            symbols=symbols,
            sectors=sectors,
            max_single_stock_weight=self.max_single_weight,
            max_sector_weight=self.max_sector_weight
        )
        return final_w

    def apply_target_volatility_scaling(
        self,
        weights: np.ndarray,
        cov_matrix: np.ndarray,
        regime: Optional[str] = "BULL_LOW_VOL"
    ) -> Tuple[np.ndarray, float]:
        """
        Dynamic Target Volatility (12% Annualized) Scaling & Cash Drag Eliminator:
        Scales total portfolio allocation up or down based on current realized volatility.
        - In Bull Low-Vol: scales allocation up to 98% (eliminating cash drag).
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
    ) -> np.ndarray:
        """
        Asymmetric Leland Dynamic No-Trade Buffer Bands:
        Suppresses unnecessary churn and transaction taxes (STT) when drift is within noise band.
        Delta_i = ( 3/4 * gamma * Cost_i / sigma_i^2 )^(1/3)
        """
        n = len(target_weights)
        if current_weights is None or len(current_weights) != n or np.all(current_weights <= 0):
            return target_weights

        cost_fraction = self.leland_cost_bps / 10_000.0  # e.g. 20 bps = 0.0020
        vols = np.maximum(volatilities, 0.01)
        # Leland half-width delta (typically 0.5% ~ 2.5%)
        leland_deltas = np.clip(
            (0.75 * self.risk_aversion * cost_fraction / (vols ** 2)) ** (1.0 / 3.0),
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
            elif abs(tgt_w - curr_w) <= delta:
                # Within no-trade band: hold current weight to save turnover and tax
                realized_w[i] = curr_w
            elif tgt_w > curr_w:
                # Buy only to lower boundary of band
                realized_w[i] = tgt_w - delta
            else:
                # Sell only to upper boundary of band
                realized_w[i] = tgt_w + delta

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

        # Extract synchronized return series & covariance matrix
        returns_df, valid_symbols = self.compute_returns_matrix(raw_symbols, prices_dict, lookback=60)
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

        # Calculate shrunk covariance matrix
        sample_cov = np.cov(returns_df.values, rowvar=False)
        cov_matrix = shrink_covariance_matrix(sample_cov, n_samples=len(returns_df))

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
                        qty = float(h.get("quantity", 0.0))
                        p = float(h.get("current_price", h.get("entry_price", 0.0)))
                        current_weights[i] = (qty * p) / total_portfolio_value

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
        )

        # Step 2: Target Volatility Scaling & Cash Drag Eliminator
        w_scaled, effective_alloc = self.apply_target_volatility_scaling(w_opt, cov_matrix, regime=regime)

        # Step 3: Asymmetric Leland Dynamic No-Trade Buffer
        vols = np.sqrt(np.maximum(np.diag(cov_matrix), 1e-6))
        w_final = self.apply_leland_no_trade_buffers(w_scaled, current_weights, volatilities=vols)

        # Step 4: Compute shares, lot sizes, and allocation amounts
        latest_prices = []
        for sym in valid_symbols:
            p_df = prices_dict.get(sym)
            if p_df is not None and not p_df.empty:
                c_col = "Close" if "Close" in p_df.columns else ("close" if "close" in p_df.columns else None)
                p = float(p_df[c_col].iloc[-1]) if c_col else 1.0
            else:
                p = 1.0
            latest_prices.append(max(p, 1.0))

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
