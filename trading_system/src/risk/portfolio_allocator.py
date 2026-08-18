"""
Portfolio Allocator Module:
- Tail-Risk EVT-CVaR Budgeting (Peaks-Over-Threshold GPD fitting & 3-tier fallback)
- Dynamic Band-Based Rebalancing (Leland optimal no-trade buffer zones)
- Microstructure Transaction Cost Sizing (STT tax, dynamic spread, market impact)
- Non-linear SLSQP Portfolio Risk Budget Optimization
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any, Union
from pathlib import Path
from scipy.stats import genpareto, norm, skew, kurtosis
from scipy.optimize import minimize

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class PortfolioAllocator:
    """
    Portfolio Allocator Engine implementing:
    1. EVT-GPD CVaR Estimation & Non-linear SLSQP Risk Budget Constraint Optimization.
    2. Dynamic Asset-Specific Microstructure Cost Sizing (KOSPI/KOSDAQ/SP500 STT, Spread, Market Impact).
    3. Leland Dynamic Band-Based No-Trade Buffer Zones for Transaction Drag Suppression.
    """

    def __init__(
        self,
        config: Optional[Any] = None,
        default_max_weight: float = 0.20,
        default_max_sector_weight: float = 0.35,
        risk_aversion: float = 1.0,
        delta_floor: float = 0.005,
        delta_cap: float = 0.050,
        rebalance_mode: str = "boundary",
        min_tail_samples: int = 15,
        target_horizon: int = 20
    ):
        self.config = config
        self.target_horizon = int(target_horizon) if target_horizon is not None else 20
        safe_max_w = float(default_max_weight) if (default_max_weight is not None and np.isfinite(default_max_weight)) else 0.20
        self.default_max_weight = max(0.01, min(1.0, safe_max_w))
        safe_sec_w = float(default_max_sector_weight) if (default_max_sector_weight is not None and np.isfinite(default_max_sector_weight)) else 0.35
        self.default_max_sector_weight = max(0.01, min(1.0, safe_sec_w))
        safe_ra = float(risk_aversion) if (risk_aversion is not None and np.isfinite(risk_aversion)) else 1.0
        self.risk_aversion = max(0.01, safe_ra)
        safe_df = float(delta_floor) if (delta_floor is not None and np.isfinite(delta_floor)) else 0.005
        self.delta_floor = max(0.0001, min(0.5, safe_df))
        safe_dc = float(delta_cap) if (delta_cap is not None and np.isfinite(delta_cap)) else 0.050
        self.delta_cap = max(self.delta_floor, min(0.5, safe_dc))
        self.rebalance_mode = str(rebalance_mode).lower() if rebalance_mode is not None else "boundary"
        self.min_tail_samples = max(2, int(min_tail_samples)) if min_tail_samples is not None else 15

    @staticmethod
    def compute_tail_stress_cov(
        returns_matrix: np.ndarray,
        base_cov: np.ndarray,
        tail_quantile: float = 0.10,
        stress_weight: float = 0.30,
        use_clayton_copula: bool = True
    ) -> np.ndarray:
        """
        Computes tail-stressed covariance matrix reflecting lower tail dependence in crisis regimes.
        Blends standard Ledoit-Wolf covariance with lower tail joint covariance matrix and
        Clayton Copula asymmetric lower-tail dependence.
        """
        if returns_matrix is None or len(returns_matrix) < 10 or returns_matrix.shape[1] < 2:
            return base_cov

        N, K = returns_matrix.shape
        mkt_ret = np.mean(returns_matrix, axis=1)
        tail_cutoff = np.quantile(mkt_ret, tail_quantile)
        tail_mask = mkt_ret <= tail_cutoff

        if tail_mask.sum() >= 3:
            tail_returns = returns_matrix[tail_mask]
            tail_cov = np.cov(tail_returns, rowvar=False)
            if tail_cov.shape == base_cov.shape and np.all(np.isfinite(tail_cov)):
                k_eff = float(np.clip(stress_weight, 0.0, 0.70))
                stressed_cov = (1.0 - k_eff) * base_cov + k_eff * tail_cov

                # Asymmetric Downside Clayton Copula adjustment (lower tail correlation boost)
                if use_clayton_copula:
                    stds = np.sqrt(np.maximum(np.diag(stressed_cov), 1e-8))
                    outer_std = np.outer(stds, stds)
                    outer_std = np.where(outer_std > 0, outer_std, 1e-8)
                    corr = np.clip(stressed_cov / outer_std, -1.0, 1.0)
                    # Clayton lower-tail dependence coefficient lambda_L
                    lambda_l = 0.25
                    asym_corr = (1.0 - lambda_l) * corr + lambda_l * np.ones_like(corr)
                    np.fill_diagonal(asym_corr, 1.0)
                    stressed_cov = asym_corr * outer_std

                w_diag = np.diag(np.diag(stressed_cov))
                res: np.ndarray = np.asarray(stressed_cov + 1e-6 * w_diag)
                return res

        return base_cov

    # =========================================================================
    # OBJECTIVE 1: EVT-CVaR LOSS BUDGET CONSTRAINTS & 3-TIER FALLBACK HIERARCHY
    # =========================================================================

    def estimate_evt_cvar(
        self,
        returns: Union[List[float], np.ndarray, pd.Series],
        confidence: float = 0.95,
        quantile_threshold: float = 0.90
    ) -> Dict[str, Any]:
        """
        Calculates Conditional Value-at-Risk (CVaR) using Extreme Value Theory (EVT)
        Peaks-Over-Threshold (POT) Generalized Pareto Distribution (GPD) fitting.

        Implements 3-Tier Fallback Hierarchy:
        - Tier 1: EVT-GPD POT Estimator (when N_u >= min_tail_samples and GPD converges).
        - Tier 2: Cornish-Fisher Expansion CVaR (skewness & kurtosis tail adjustment).
        - Tier 3: Empirical Quantile / Gaussian Parametric CVaR (when sample N < 10 or exceptions).

        Returns:
            Dict containing: 'var', 'cvar', 'xi', 'beta', 'method'
        """
        if returns is None:
            return {"var": 0.0, "cvar": 0.0, "xi": 0.0, "beta": 0.0, "method": "zero_fallback"}

        returns_arr = np.asarray(returns, dtype=np.float64)
        returns_arr = returns_arr[~np.isnan(returns_arr)]

        N = len(returns_arr)
        if N < 5:
            return {"var": 0.0, "cvar": 0.0, "xi": 0.0, "beta": 0.0, "method": "zero_fallback"}

        # Portfolio Loss L = -R
        losses = -returns_arr

        # Tier 3 check for extremely small sample size
        if N < 10:
            mu_l = float(np.mean(losses))
            sigma_l = float(np.std(losses, ddof=1)) if N > 1 else 0.01
            z_alpha = float(norm.ppf(confidence))
            cvar_gauss = max(0.0, mu_l + sigma_l * (norm.pdf(z_alpha) / (1.0 - confidence)))
            var_gauss = max(0.0, mu_l + sigma_l * z_alpha)
            return {
                "var": float(var_gauss),
                "cvar": float(cvar_gauss),
                "xi": 0.0,
                "beta": 0.0,
                "method": "gaussian_fallback_small_n"
            }

        # Adaptive threshold u selection: max of quantile and mean + 1.5 sigma to prevent noise fitting in quiet regimes
        sigma_l = float(np.std(losses, ddof=1)) if N > 1 else 0.01
        u_quantile = float(np.quantile(losses, quantile_threshold))
        u_volatility = float(np.mean(losses) + 1.5 * sigma_l)
        u = max(u_quantile, u_volatility)
        exceedances = losses[losses > u] - u
        n_u = len(exceedances)

        # Base Fallback: Tier 3 Empirical Quantile
        var_emp = float(np.quantile(losses, confidence))
        worse_losses = losses[losses >= var_emp]
        cvar_emp = float(np.mean(worse_losses)) if len(worse_losses) > 0 else var_emp

        # Tier 2: Cornish-Fisher Expansion
        var_cf, cvar_cf = var_emp, cvar_emp
        cf_valid = False
        try:
            mu_l = float(np.mean(losses))
            sigma_l = float(np.std(losses, ddof=1))
            if sigma_l > 1e-8:
                s_loss = float(skew(losses))
                k_loss = float(kurtosis(losses))  # excess kurtosis
                z_a = float(norm.ppf(confidence))
                z_cf = z_a + (s_loss / 6.0) * (z_a**2 - 1.0) + (k_loss / 24.0) * (z_a**3 - 3.0 * z_a) - (s_loss**2 / 36.0) * (2.0 * z_a**3 - 5.0 * z_a)
                z_cf = float(np.clip(z_cf, 0.5, 6.0))
                var_cf = max(0.0, mu_l + sigma_l * z_cf)
                pdf_cf = norm.pdf(z_cf)
                cvar_cf_raw = mu_l + sigma_l * (pdf_cf / (1.0 - confidence)) * (1.0 + (s_loss / 6.0) * z_cf**3 + (k_loss / 24.0) * (z_cf**4 - 2.0 * z_cf**2 - 1.0))
                if np.isfinite(cvar_cf_raw) and cvar_cf_raw > 0:
                    cvar_cf = max(0.0, float(cvar_cf_raw))
                    cf_valid = True
        except Exception:
            pass

        # Tier 1: EVT-GPD Fit
        var_evt, cvar_evt = var_cf, cvar_cf
        xi_val, beta_val = 0.0, 0.0
        gpd_valid = False
        if n_u >= 3 and u > -1e-6:
            try:
                xi, _, beta = genpareto.fit(exceedances, floc=0)
                xi = float(xi)
                beta = float(beta)
                if beta > 1e-8 and xi < 0.95 and np.isfinite(xi) and np.isfinite(beta):
                    xi_clamped = min(xi, 0.50)
                    tail_ratio = (N / n_u) * (1.0 - confidence)
                    if abs(xi_clamped) < 1e-4:
                        var_evt = u - beta * np.log(tail_ratio)
                        cvar_evt = var_evt + beta
                    else:
                        var_evt = u + (beta / xi_clamped) * (np.power(tail_ratio, -xi_clamped) - 1.0)
                        cvar_evt = (var_evt + beta - xi_clamped * u) / (1.0 - xi_clamped)
                    if np.isfinite(var_evt) and np.isfinite(cvar_evt):
                        var_evt = max(0.0, float(var_evt))
                        cvar_evt = max(0.0, float(cvar_evt))
                        xi_val, beta_val = xi_clamped, beta
                        gpd_valid = True
            except Exception as e:
                logger.debug(f"EVT-GPD fitting non-convergent: {e}")

        # Continuous Sigmoid Blending Kernel (eliminates step discontinuity at n_u = 15)
        if gpd_valid:
            lambda_gpd = 1.0 / (1.0 + np.exp(-0.5 * (n_u - self.min_tail_samples)))
            var_smooth = lambda_gpd * var_evt + (1.0 - lambda_gpd) * var_cf
            cvar_smooth = lambda_gpd * cvar_evt + (1.0 - lambda_gpd) * cvar_cf
            used_method = "evt_gpd_sigmoid_blended" if (0.01 < lambda_gpd < 0.99) else ("evt_gpd" if lambda_gpd >= 0.99 else "cornish_fisher")
        elif cf_valid:
            var_smooth = var_cf
            cvar_smooth = cvar_cf
            used_method = "cornish_fisher"
        else:
            var_smooth = var_emp
            cvar_smooth = cvar_emp
            used_method = "empirical_fallback"

        return {
            "var": float(max(0.0, var_smooth)),
            "cvar": float(max(0.0, cvar_smooth)),
            "xi": float(xi_val),
            "beta": float(beta_val),
            "method": used_method
        }

    def estimate_portfolio_evt_cvar(
        self,
        weights: np.ndarray,
        returns_matrix: np.ndarray,
        confidence: float = 0.95
    ) -> float:
        """
        Calculates portfolio-level EVT-CVaR for a weight vector w and return matrix R.
        """
        port_returns = np.dot(returns_matrix, weights)
        res = self.estimate_evt_cvar(port_returns, confidence=confidence)
        return float(res["cvar"])

    def optimize_with_evt_cvar_constraint(
        self,
        expected_returns: pd.Series,
        returns_df: pd.DataFrame,
        max_cvar: float = 0.04,
        confidence: float = 0.95,
        max_weight: Optional[float] = None
    ) -> Dict[str, float]:
        """
        Mean-Variance Optimization subject to EVT-CVaR loss budget constraint.
        Constraint: EVT_CVaR_alpha(w) <= max_cvar
        """
        if max_weight is None:
            max_weight = self.default_max_weight

        symbols = list(expected_returns.index)
        n_assets = len(symbols)
        if n_assets == 0:
            return {}
        if n_assets == 1:
            return {symbols[0]: 1.0}

        returns_sub = returns_df[symbols] if not returns_df.empty else pd.DataFrame()
        if returns_sub.empty or len(returns_sub) < 5:
            return {sym: 1.0 / n_assets for sym in symbols}

        returns_matrix = returns_sub.values
        mu = expected_returns.values

        # Ledoit-Wolf Covariance Shrinkage for numerical stability & lower estimation error
        try:
            from sklearn.covariance import LedoitWolf
            if len(returns_matrix) >= 5 and n_assets > 1:
                cov_shrunk = LedoitWolf().fit(returns_matrix).covariance_
            else:
                cov_shrunk = np.cov(returns_matrix, rowvar=False)
                if cov_shrunk.ndim == 0:
                    cov_shrunk = np.array([[float(cov_shrunk)]])
        except Exception:
            cov_shrunk = np.cov(returns_matrix, rowvar=False) if len(returns_matrix) > 1 else np.eye(n_assets) * 0.0004
            if cov_shrunk.ndim == 0:
                cov_shrunk = np.array([[float(cov_shrunk)]])

        # Lower tail dependence stress covariance blending
        cov_shrunk = self.compute_tail_stress_cov(returns_matrix, cov_shrunk)

        def objective(w):
            ret = np.dot(w, mu)
            p_rets = np.dot(returns_matrix, w)
            downside_losses = np.minimum(0.0, p_rets)
            semi_var = float(np.mean(downside_losses ** 2))
            var_p = float(w.T @ cov_shrunk @ w) if cov_shrunk.shape == (n_assets, n_assets) else float(np.var(p_rets, ddof=1))
            # Sortino-guided Downside Risk Penalty
            total_risk = 0.5 * self.risk_aversion * (0.6 * var_p + 0.4 * semi_var)
            return -(ret - total_risk)

        def cvar_constraint(w):
            cvar_val = self.estimate_portfolio_evt_cvar(w, returns_matrix, confidence)
            return max_cvar - cvar_val

        init_weights = np.ones(n_assets) / n_assets
        eff_max_w = max(max_weight, 1.05 / n_assets)
        bounds = tuple((0.0, eff_max_w) for _ in range(n_assets))
        constraints = [
            {'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0},
            {'type': 'ineq', 'fun': cvar_constraint}
        ]

        res = minimize(
            objective,
            init_weights,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints,
            options={'maxiter': 500, 'ftol': 1e-6}
        )

        if not res.success:
            logger.warning(f"EVT-CVaR constrained optimization status: {res.message}. Normalizing initial weights.")
            weights = init_weights
        else:
            weights = res.x / np.sum(res.x)

        return {sym: float(w) for sym, w in zip(symbols, weights)}

    def optimize_turnover_regularized_portfolio(
        self,
        expected_returns: pd.Series,
        returns_df: pd.DataFrame,
        previous_weights: Optional[Dict[str, float]] = None,
        turnover_penalty_l1: float = 0.05,
        turnover_penalty_l2: float = 0.02,
        max_weight: Optional[float] = None,
        sector_map: Optional[Dict[str, str]] = None,
        max_sector_weight: Optional[float] = None,
    ) -> Dict[str, float]:
        """
        Convex Portfolio Optimization with Explicit Turnover Cost Regularization:
        Objective:
            min_w [ -w^T mu + (lambda/2) w^T Sigma w + gamma_1 sum(c_i |w_i - w_prev_i|) + (gamma_2 / 2) ||w - w_prev||^2 ]
        subject to:
            sum(w_i) = 1.0,  0 <= w_i <= max_weight,  sum_{i in Sector_k} w_i <= max_sector_weight.
        Eliminates portfolio churning on noisy marginal alpha changes while maximizing net realized compound CAGR.
        """
        if max_weight is None:
            max_weight = self.default_max_weight
        if max_sector_weight is None:
            max_sector_weight = self.default_max_sector_weight

        symbols = list(expected_returns.index)
        n_assets = len(symbols)
        if n_assets == 0:
            return {}
        if n_assets == 1:
            return {symbols[0]: 1.0}

        returns_sub = returns_df[symbols] if (not returns_df.empty and all(s in returns_df.columns for s in symbols)) else pd.DataFrame()
        if returns_sub.empty or len(returns_sub) < 5:
            return {sym: 1.0 / n_assets for sym in symbols}

        returns_matrix = returns_sub.values
        mu = np.nan_to_num(expected_returns.values.astype(float), nan=0.0)

        # Ledoit-Wolf Shrinkage Covariance
        try:
            from sklearn.covariance import LedoitWolf
            cov_shrunk = LedoitWolf().fit(returns_matrix).covariance_
        except Exception:
            cov_shrunk = np.cov(returns_matrix, rowvar=False) if len(returns_matrix) > 1 else np.eye(n_assets) * 0.0004

        cov_shrunk = self.compute_tail_stress_cov(returns_matrix, cov_shrunk)

        # Build w_prev vector
        w_prev_vec = np.zeros(n_assets, dtype=float)
        if previous_weights:
            for i, sym in enumerate(symbols):
                w_prev_vec[i] = float(previous_weights.get(sym, 0.0))

        gamma_1 = float(max(0.0, turnover_penalty_l1))
        gamma_2 = float(max(0.0, turnover_penalty_l2))

        def objective(w):
            ret = np.dot(w, mu)
            var_p = float(w.T @ cov_shrunk @ w) if cov_shrunk.shape == (n_assets, n_assets) else float(np.var(np.dot(returns_matrix, w), ddof=1))
            turnover_l1 = float(np.sum(np.abs(w - w_prev_vec)))
            turnover_l2 = float(np.sum((w - w_prev_vec) ** 2))
            total_obj = -ret + (0.5 * self.risk_aversion * var_p) + (gamma_1 * turnover_l1) + (0.5 * gamma_2 * turnover_l2)
            return total_obj

        init_weights = w_prev_vec if (np.sum(w_prev_vec) > 0.90 and np.all(w_prev_vec >= 0)) else np.ones(n_assets) / n_assets
        init_weights = init_weights / np.sum(init_weights)

        eff_max_w = max(max_weight, 1.05 / n_assets)
        bounds = tuple((0.0, eff_max_w) for _ in range(n_assets))
        constraints = [{'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0}]

        # Add sector capacity constraints if sector_map is provided
        if sector_map:
            sectors = set(sector_map.values())
            for sec in sectors:
                sec_indices = [i for i, s in enumerate(symbols) if sector_map.get(s) == sec]
                if sec_indices:
                    constraints.append({
                        'type': 'ineq',
                        'fun': lambda w, idxs=sec_indices: max_sector_weight - np.sum(w[idxs])
                    })

        res = minimize(
            objective,
            init_weights,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints,
            options={'maxiter': 500, 'ftol': 1e-7}
        )

        if not res.success:
            weights = init_weights
        else:
            weights = res.x / np.sum(res.x)

        return {sym: float(w) for sym, w in zip(symbols, weights)}

    def allocate_quarter_kelly(
        self,
        expected_returns: pd.Series,
        volatilities: Optional[pd.Series] = None,
        max_weight: Optional[float] = None,
        kelly_fraction: float = 0.25,
        risk_free_rate: float = 0.035
    ) -> Dict[str, float]:
        """
        Allocates portfolio weights using Fractional Kelly (Quarter-Kelly) Sizing:
        w_i = kelly_fraction * (mu_i - r_f) / (sigma_i^2)
        subject to 0 <= w_i <= max_weight and sum(w_i) <= 1.0.

        Guarantees optimal long-term geometric compounding while suppressing drawdown risk.
        """
        if expected_returns.empty:
            return {}

        symbols = list(expected_returns.index)
        n_assets = len(symbols)
        if n_assets == 1:
            return {symbols[0]: min(1.0, max_weight or self.default_max_weight)}

        cap = max_weight or self.default_max_weight

        # Clean expected returns (handle horizon vs annualized excess returns)
        raw_mu = np.nan_to_num(expected_returns.values.astype(float), nan=0.0, posinf=0.0, neginf=0.0)
        # Determine horizon scaling: if mu mean < 0.20, assume 20d horizon return and scale rf accordingly
        rf_scaled = risk_free_rate * (self.target_horizon / 252.0) if np.mean(raw_mu) < 0.50 else risk_free_rate
        excess_mu = np.maximum(0.0, raw_mu - rf_scaled)

        if volatilities is not None and not volatilities.empty:
            raw_vols = volatilities.reindex(symbols).fillna(0.02).values.astype(float)
            raw_vols = np.nan_to_num(raw_vols, nan=0.02, posinf=0.02, neginf=0.02)
            vols = np.maximum(0.005, raw_vols)
        else:
            vols = np.full(n_assets, 0.02)

        # Raw Kelly score: kelly_fraction * (excess_mu / sigma_i^2)
        raw_kelly = float(kelly_fraction) * (excess_mu / (vols ** 2))
        total_k = np.sum(raw_kelly)

        if total_k <= 1e-8:
            equal_w = 1.0 / float(n_assets)
            return {sym: float(min(equal_w, cap)) for sym in symbols}

        # Normalize to 1.0
        norm_w = raw_kelly / total_k

        # Iterative water-filling projection to guarantee weights <= cap and sum(weights) == 1.0
        eff_cap = max(cap, 1.0 / n_assets)
        cur_w = np.clip(norm_w, 0.0, eff_cap)
        for _ in range(10):
            cur_sum = np.sum(cur_w)
            if abs(cur_sum - 1.0) < 1e-6 or cur_sum <= 0:
                break
            excess = 1.0 - cur_sum
            uncapped_mask = cur_w < (eff_cap - 1e-6)
            if not np.any(uncapped_mask):
                cur_w = cur_w / cur_sum
                break
            uncapped_sum = np.sum(cur_w[uncapped_mask])
            if uncapped_sum > 0:
                additions = excess * (cur_w[uncapped_mask] / uncapped_sum)
                cur_w[uncapped_mask] = np.clip(cur_w[uncapped_mask] + additions, 0.0, eff_cap)
            else:
                cur_w[uncapped_mask] += excess / np.sum(uncapped_mask)

        final_w = cur_w if np.sum(cur_w) > 0 else np.ones(n_assets) / n_assets
        return {sym: float(w) for sym, w in zip(symbols, final_w)}

    def allocate_volatility_targeted_kelly(
        self,
        expected_returns: pd.Series,
        volatilities: Optional[pd.Series] = None,
        target_annual_vol: float = 0.15,
        max_weight: Optional[float] = None,
        kelly_fraction: float = 0.25
    ) -> Dict[str, float]:
        """
        Allocates portfolio weights combining Fractional Kelly with Volatility Targeting:
        1. Calculates relative Kelly asset weights w_raw_i = (mu_i / sigma_i^2).
        2. Computes aggregate portfolio expected volatility sigma_port.
        3. Scales portfolio leverage by (target_annual_vol / sigma_port) to maintain steady risk.
        4. Clamps individual asset weights to max_weight and ensures sum(w_i) <= 1.0.
        """
        base_weights = self.allocate_quarter_kelly(
            expected_returns=expected_returns,
            volatilities=volatilities,
            max_weight=max_weight,
            kelly_fraction=kelly_fraction
        )
        if not base_weights:
            return {}

        symbols = list(base_weights.keys())
        w_vec = np.array([base_weights[s] for s in symbols])

        if volatilities is not None and not volatilities.empty:
            daily_vols = volatilities.reindex(symbols).fillna(0.02).values.astype(float)
        else:
            daily_vols = np.full(len(symbols), 0.02)

        # Estimate weighted annual volatility proxy: sqrt(252) * sum(w_i * sigma_i)
        port_ann_vol = float(np.sqrt(252) * np.dot(w_vec, daily_vols))
        if port_ann_vol > 1e-4:
            vol_scale = float(np.clip(target_annual_vol / port_ann_vol, 0.40, 1.25))
        else:
            vol_scale = 1.0

        scaled_weights = {s: float(np.clip(w * vol_scale, 0.0, max_weight or self.default_max_weight)) for s, w in base_weights.items()}
        tot = sum(scaled_weights.values())
        if tot > 1.0:
            scaled_weights = {s: w / tot for s, w in scaled_weights.items()}

        return scaled_weights

    # =========================================================================
    # OBJECTIVE 2: DYNAMIC LELAND BAND-BASED REBALANCING & MICROSTRUCTURE COSTS
    # =========================================================================

    def estimate_transaction_cost_rate(
        self,
        symbol: str,
        market: str,
        target_weight: float,
        portfolio_value: float = 100_000_000.0,
        volatility_20d: float = 0.020,
        adv: float = 1_000_000_000.0,
        is_sell: Optional[bool] = None,
        slippage_multiplier: float = 1.0
    ) -> float:
        """
        Estimates asset-specific one-way transaction cost rate (c_i):
        c_i = Tax & Fees + 0.5 * Spread + Market Impact
        incorporating dynamic slippage feedback multiplier from real execution logs.

        Specific Rules:
        - KOSPI: Sell STT tax = 0.15% (0.0015), Brokerage fee = 0.03% (0.0003). Base spread = 0.06%.
        - KOSDAQ: Sell STT tax = 0.18% (0.0018), Brokerage fee = 0.03% (0.0003). Base spread = 0.10%.
        - NASDAQ: SEC fee = 0.003% (0.00003), Brokerage fee = 0.005% (0.00005). Base spread = 0.03%.
        - RUSSELL2000: SEC fee = 0.003% (0.00003), Brokerage fee = 0.005% (0.00005). Base spread = 0.08%.
        - SP500: SEC fee = 0.003% (0.00003), Brokerage fee = 0.005% (0.00005). Base spread = 0.02%.
        """
        market_upper = str(market).upper()
        is_us_stock = market_upper in ('SP500', 'NASDAQ', 'RUSSELL2000') or (symbol.isalpha() and len(symbol) <= 5)

        slip_mult = max(0.5, float(slippage_multiplier))

        if market_upper in ['KOSDAQ', 'KQ'] or symbol.endswith('.KQ'):
            stt_tax = 0.0018
            brokerage_fee = 0.0003
            base_spread = getattr(self.config, 'base_spread_kosdaq', 0.0010) if self.config else 0.0010
            spread_min, spread_max = 0.0003, 0.0250
            adv_ref = 1_000_000_000.0
            impact_coeff = getattr(self.config, 'market_impact_coeff_krx', 0.75) if self.config else 0.75
        elif market_upper == 'NASDAQ':
            stt_tax = 0.00003
            brokerage_fee = 0.00005
            base_spread = getattr(self.config, 'base_spread_nasdaq', 0.0003) if self.config else 0.0003
            spread_min, spread_max = 0.0001, 0.0080
            adv_ref = 1_000_000.0
            impact_coeff = getattr(self.config, 'market_impact_coeff_sp500', 0.50) if self.config else 0.50
        elif market_upper == 'RUSSELL2000':
            stt_tax = 0.00003
            brokerage_fee = 0.00005
            base_spread = getattr(self.config, 'base_spread_russell2000', 0.0008) if self.config else 0.0008
            spread_min, spread_max = 0.0002, 0.0150
            adv_ref = 500_000.0
            impact_coeff = getattr(self.config, 'market_impact_coeff_sp500', 0.50) if self.config else 0.50
        elif is_us_stock:
            stt_tax = 0.00003
            brokerage_fee = 0.00005
            base_spread = getattr(self.config, 'base_spread_sp500', 0.0002) if self.config else 0.0002
            spread_min, spread_max = 0.0001, 0.0050
            adv_ref = 1_000_000.0
            impact_coeff = getattr(self.config, 'market_impact_coeff_sp500', 0.50) if self.config else 0.50
        else:  # KOSPI default
            stt_tax = 0.0015
            brokerage_fee = 0.0003
            base_spread = getattr(self.config, 'base_spread_kospi', 0.0006) if self.config else 0.0006
            spread_min, spread_max = 0.0002, 0.0150
            adv_ref = 1_000_000_000.0
            impact_coeff = getattr(self.config, 'market_impact_coeff_krx', 0.75) if self.config else 0.75

        # Direct STT application depending on order side
        if is_sell is True:
            tax_fee = stt_tax + brokerage_fee
        elif is_sell is False:
            tax_fee = brokerage_fee
        else:
            tax_fee = 0.5 * stt_tax + brokerage_fee

        is_sp500 = (market_upper == 'SP500')
        min_adv = 10_000.0 if is_sp500 else 10_000_000.0
        adv_clean = max(adv, min_adv)
        base_vol = 0.015 if is_sp500 else 0.020
        vol_clean = max(volatility_20d, 0.005)

        # Dynamic spread formula with real-time slippage multiplier scaling
        adv_ratio = adv_ref / adv_clean
        vol_ratio = vol_clean / base_vol
        dynamic_spread = base_spread * (adv_ratio ** 0.25) * (vol_ratio ** 0.50) * slip_mult
        if np.isnan(dynamic_spread) or np.isinf(dynamic_spread):
            dynamic_spread = base_spread * slip_mult
        clamped_spread = min(max(dynamic_spread, spread_min), spread_max * slip_mult)
        half_spread = 0.5 * clamped_spread

        # Square-root market impact formula with slippage feedback scaling
        order_val = max(1.0, target_weight * portfolio_value)
        participation = order_val / adv_clean
        impact_one_way = impact_coeff * slip_mult * vol_clean * np.sqrt(participation)
        if participation > 0.10:
            impact_one_way += 0.50 * (participation - 0.10) * slip_mult

        total_cost_rate = tax_fee + half_spread + impact_one_way
        return float(total_cost_rate)

    def calculate_dynamic_buffer_band(
        self,
        symbol: str,
        target_weight: float,
        cost_rate: float,
        volatility_20d: float,
        risk_aversion: Optional[float] = None
    ) -> float:
        """
        Calculates Leland optimal no-trade buffer threshold delta_i:
        delta_i = [ (3 * c_i * w_target_i * sigma_i^2) / (2 * gamma_risk) ]^(1/3)
        clamped to [delta_floor, delta_cap].
        """
        gamma = risk_aversion if risk_aversion is not None else self.risk_aversion
        if target_weight <= 0.0 or cost_rate <= 0.0:
            return self.delta_floor

        vol_clean = max(0.005, volatility_20d)
        ann_variance = 252.0 * (vol_clean ** 2)

        # Leland's transaction cost buffer bandwidth: delta_i = [ (3 * c_i * w_i * sigma_ann^2) / (2 * gamma) ]^(1/3)
        cubic_term = (3.0 * cost_rate * target_weight * ann_variance) / (2.0 * max(1e-4, gamma))
        delta_raw = np.cbrt(cubic_term)
        if np.isnan(delta_raw) or np.isinf(delta_raw):
            return self.delta_floor
        return float(min(max(delta_raw, self.delta_floor), self.delta_cap))

    def compute_portfolio_rebalance(
        self,
        current_weights: Dict[str, float],
        target_weights: Dict[str, float],
        market_map: Dict[str, str],
        volatility_map: Dict[str, float],
        adv_map: Dict[str, float],
        portfolio_value: float = 100_000_000.0,
        rebalance_mode: Optional[str] = None,
        slippage_multiplier: float = 1.0,
        slippage_map: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        Evaluates dynamic buffer bands [w_target - delta_i, w_target + delta_i]:
        - If current_weight is INSIDE band: returns action HOLD with 0 trade weight.
        - If current_weight BREACHES band: triggers BUY/SELL rebalancing trade.
        """
        mode = (rebalance_mode or self.rebalance_mode).lower()
        all_symbols = set(current_weights.keys()).union(set(target_weights.keys()))

        new_weights: Dict[str, float] = {}
        buffer_bands: Dict[str, Tuple[float, float, float]] = {}
        trades: Dict[str, Dict[str, Any]] = {}
        total_cost_saved = 0.0
        traded_count = 0
        skipped_count = 0

        for sym in all_symbols:
            w_curr = current_weights.get(sym, 0.0)
            w_targ = target_weights.get(sym, 0.0)
            mkt = market_map.get(sym, "KOSPI")
            vol = volatility_map.get(sym, 0.020)
            adv = adv_map.get(sym, 1_000_000_000.0)
            sym_slip = (slippage_map.get(sym, slippage_multiplier) if slippage_map else slippage_multiplier)

            cost_rate = self.estimate_transaction_cost_rate(
                symbol=sym,
                market=mkt,
                target_weight=w_targ if w_targ > 0 else w_curr,
                portfolio_value=portfolio_value,
                volatility_20d=vol,
                adv=adv,
                is_sell=(w_curr > w_targ),
                slippage_multiplier=sym_slip
            )

            delta_i = self.calculate_dynamic_buffer_band(
                symbol=sym,
                target_weight=w_targ,
                cost_rate=cost_rate,
                volatility_20d=vol
            )

            L_i = max(0.0, w_targ - delta_i)
            U_i = w_targ + delta_i
            buffer_bands[sym] = (L_i, U_i, delta_i)

            # Check inside buffer band [L_i, U_i]
            if L_i <= w_curr <= U_i:
                new_weights[sym] = w_curr
                skipped_count += 1
                prevented_trade_size = abs(w_curr - w_targ) * portfolio_value
                saved_cost = prevented_trade_size * cost_rate
                total_cost_saved += saved_cost
                trades[sym] = {
                    "action": "HOLD",
                    "w_current": w_curr,
                    "w_target": w_targ,
                    "w_new": w_curr,
                    "delta": delta_i,
                    "band": (L_i, U_i),
                    "trade_weight": 0.0,
                    "cost_saved_krw": saved_cost
                }
            else:
                traded_count += 1
                if w_targ == 0.0:
                    w_exec = 0.0
                    action = "SELL"
                elif w_curr < L_i:
                    w_exec = L_i if mode == "boundary" else w_targ
                    action = "BUY"
                else:
                    w_exec = U_i if mode == "boundary" else w_targ
                    action = "SELL"
                new_weights[sym] = w_exec
                trades[sym] = {
                    "action": action,
                    "w_current": w_curr,
                    "w_target": w_targ,
                    "w_new": w_exec,
                    "delta": delta_i,
                    "band": (L_i, U_i),
                    "trade_weight": w_exec - w_curr,
                    "cost_saved_krw": 0.0
                }

        tot_asset_w = sum(new_weights.values())
        if tot_asset_w > 1.0:
            scale = 1.0 / tot_asset_w
            new_weights = {s: w * scale for s, w in new_weights.items()}

        return {
            "new_weights": new_weights,
            "buffer_bands": buffer_bands,
            "trades": trades,
            "summary": {
                "total_symbols": len(all_symbols),
                "traded_count": traded_count,
                "skipped_count": skipped_count,
                "total_cost_saved_krw": total_cost_saved,
                "total_asset_weight": sum(new_weights.values()),
                "cash_weight": max(0.0, 1.0 - sum(new_weights.values()))
            }
        }

    # =========================================================================
    # OBJECTIVE 3: SECTOR EXPOSURE CAPPING & FACTOR NEUTRALITY CONSTRAINTS
    # =========================================================================

    def apply_sector_and_factor_constraints(
        self,
        weights: Dict[str, float],
        sector_map: Optional[Dict[str, str]] = None,
        regime: Optional[Union[int, str]] = None,
        max_sector_cap: Optional[float] = None,
        renormalize: Optional[bool] = None
    ) -> Dict[str, float]:
        """
        Enforces Sector Exposure Cap and Factor Risk Budgeting:
        - Sector Cap: <= 25% in BEAR/SIDEWAYS regimes, <= 35% in BULL market regimes.
        - Rank Preservation: Iteratively rescales over-concentrated sectors while preserving relative rank.
        - Cash/Re-allocation: If renormalize is True (default when max_sector_cap is explicitly provided),
          re-distributes excess weight proportionally across compliant sectors.
        """
        if not weights:
            return {}

        # Determine Regime-Dependent Sector Cap
        if max_sector_cap is not None:
            sector_cap = max_sector_cap
            should_renormalize = True if renormalize is None else bool(renormalize)
        elif regime in [2, 'BULL', 'BULL_LOW_VOL', 'BULL_HIGH_VOL']:
            sector_cap = 0.35  # Dynamic relaxation in BULL market
            should_renormalize = False if renormalize is None else bool(renormalize)
        else:
            sector_cap = 0.25  # Defensive 25% cap in BEAR/SIDEWAYS
            should_renormalize = False if renormalize is None else bool(renormalize)

        if not sector_map:
            # Fallback if no sector mapping is available
            s_sum = sum(weights.values())
            return {s: w / s_sum for s, w in weights.items()} if s_sum > 0 else weights

        cleaned_weights = dict(weights)
        target_total = sum(weights.values()) if sum(weights.values()) > 0 else 1.0

        # Iterative Sector Cap Enforcement (up to 10 passes for convergence)
        for _ in range(10):
            sector_totals: Dict[str, float] = {}
            for sym, w in cleaned_weights.items():
                sec = sector_map.get(sym, "UNKNOWN")
                sector_totals[sec] = sector_totals.get(sec, 0.0) + w

            over_sectors = {sec: tot for sec, tot in sector_totals.items() if tot > sector_cap + 1e-6}
            if not over_sectors:
                break

            # Rescale symbols in over-concentrated sectors
            for sec, tot in over_sectors.items():
                scale_factor = sector_cap / tot
                for sym, w in cleaned_weights.items():
                    if sector_map.get(sym, "UNKNOWN") == sec:
                        cleaned_weights[sym] = w * scale_factor

            if should_renormalize:
                # Re-distribute excess weight proportionally across compliant sectors
                non_over_sum = sum(w for sym, w in cleaned_weights.items() if sector_map.get(sym, "UNKNOWN") not in over_sectors)
                if non_over_sum > 0:
                    cur_sum = sum(cleaned_weights.values())
                    excess = target_total - cur_sum
                    if excess > 0:
                        for sym, w in cleaned_weights.items():
                            if sector_map.get(sym, "UNKNOWN") not in over_sectors:
                                cleaned_weights[sym] += excess * (w / non_over_sum)
                else:
                    # If all sectors are capped, normalize directly
                    s_sum = sum(cleaned_weights.values())
                    if s_sum > 0:
                        cleaned_weights = {s: (w / s_sum) * target_total for s, w in cleaned_weights.items()}
                    break

        if should_renormalize:
            # Final safety normalization if needed to preserve target_total
            s_sum = sum(cleaned_weights.values())
            if s_sum > 0 and abs(s_sum - target_total) > 1e-4:
                cleaned_weights = {s: (w / s_sum) * target_total for s, w in cleaned_weights.items()}

        return cleaned_weights

    # =========================================================================
    # OBJECTIVE 4: REAL-TIME OMS SLIPPAGE FEEDBACK & ATR TRAILING STOP
    # =========================================================================

    def calibrate_slippage_from_trade_logs(self, db_path: Optional[str] = None) -> float:
        """
        Reads realized execution logs from trade_logs.db and calculates empirical
        realized slippage ratio vs predicted Almgren-Chriss cost, returning a
        calibrated cost scaling factor (default = 1.0 if insufficient trades).
        """
        import sqlite3

        target_db = Path(db_path) if db_path else _PROJECT_ROOT / "trade_logs.db"
        if not target_db.exists():
            return 1.0

        try:
            conn = sqlite3.connect(str(target_db), timeout=30.0)
            conn.execute("PRAGMA journal_mode = WAL;")
            conn.execute("PRAGMA busy_timeout = 30000;")
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('execution_logs', 'order_plans', 'trade_logs', 'orders');")
            tables = [r[0] for r in cursor.fetchall()]

            if not tables:
                conn.close()
                return 1.0

            if 'execution_logs' in tables and 'order_plans' in tables:
                df = pd.read_sql_query(
                    "SELECT o.target_price AS order_price, e.executed_price AS executed_price "
                    "FROM order_plans o JOIN execution_logs e ON o.order_id = e.order_id "
                    "WHERE o.target_price > 0 AND e.executed_price > 0 LIMIT 500;", conn
                )
            elif 'orders' in tables and 'executions' in tables:
                df = pd.read_sql_query(
                    "SELECT o.price AS order_price, e.price AS executed_price "
                    "FROM orders o JOIN executions e ON o.order_id = e.order_id "
                    "WHERE o.price > 0 AND e.price > 0 LIMIT 500;", conn
                )
            else:
                tbl = 'trade_logs' if 'trade_logs' in tables else tables[0]
                cursor.execute(f"PRAGMA table_info({tbl});")  # nosec B608
                cols = [r[1] for r in cursor.fetchall()]
                p_col = 'order_price' if 'order_price' in cols else ('price' if 'price' in cols else ('target_price' if 'target_price' in cols else None))
                exec_col = 'executed_price' if 'executed_price' in cols else ('price' if 'price' in cols else None)
                if not p_col or not exec_col:
                    conn.close()
                    return 1.0
                df = pd.read_sql_query(
                    f"SELECT {p_col} AS order_price, {exec_col} AS executed_price FROM {tbl} LIMIT 500;",  # nosec B608
                    conn
                )
            conn.close()

            if df.empty or len(df) < 5:
                return 1.0

            df['order_price'] = pd.to_numeric(df['order_price'], errors='coerce')
            df['executed_price'] = pd.to_numeric(df['executed_price'], errors='coerce')
            valid = df.dropna(subset=['order_price', 'executed_price'])
            valid = valid[valid['order_price'] > 0]

            if len(valid) < 5:
                return 1.0

            slippage_pct = (np.abs(valid['executed_price'] - valid['order_price']) / valid['order_price']).mean()
            # Normalize relative to benchmark 0.10% (10 bps)
            calibrated_factor = float(np.clip(slippage_pct / 0.0010, 0.5, 3.0))
            logger.info(f"[OMS SLIPPAGE FEEDBACK] Calibrated slippage factor = {calibrated_factor:.2f}x (from {len(valid)} trades)")
            return calibrated_factor
        except Exception as e:
            logger.warning(f"[OMS SLIPPAGE FEEDBACK] Failed to calibrate slippage: {e}")
            return 1.0

    def calculate_atr_trailing_stop(
        self,
        symbol: str,
        current_price: float,
        atr_20d: float,
        is_long: bool = True,
        multiplier: float = 2.5,
        highest_price: Optional[float] = None
    ) -> Dict[str, float]:
        """
        Calculates intraday dynamic ATR-based trailing stop-loss and take-profit levels:
        - Stop Loss: peak_price - (multiplier * ATR_20d)
        - Take Profit: current_price + (1.5 * multiplier * ATR_20d)
        """
        if current_price <= 0.0 or atr_20d <= 0.0:
            return {
                "stop_loss": max(0.0, current_price * 0.95),
                "take_profit": current_price * 1.10,
                "risk_pct": 0.05
            }

        atr_clean = max(atr_20d, current_price * 0.005)
        stop_dist = multiplier * atr_clean

        safe_ref = None
        try:
            if highest_price is not None:
                hp = float(highest_price)
                if hp > 0 and not np.isnan(hp) and not np.isinf(hp):
                    safe_ref = hp
        except (ValueError, TypeError):
            safe_ref = None

        if is_long:
            ref_price = max(safe_ref, current_price) if safe_ref is not None else current_price
            stop_loss = max(0.0, ref_price - stop_dist)
            take_profit = current_price + (1.5 * stop_dist)
        else:
            ref_price = min(safe_ref, current_price) if safe_ref is not None else current_price
            stop_loss = ref_price + stop_dist
            take_profit = max(0.0, current_price - (1.5 * stop_dist))

        risk_pct = float(abs(current_price - stop_loss) / current_price)
        return {
            "stop_loss": float(stop_loss),
            "take_profit": float(take_profit),
            "risk_pct": float(risk_pct)
        }

    # =========================================================================
    # OBJECTIVE 5: DYNAMIC VOLATILITY TARGETING (DVT) MACRO CASH OVERLAY
    # =========================================================================

    def compute_dynamic_volatility_target_weights(
        self,
        target_weights: Dict[str, float],
        returns_matrix: Optional[np.ndarray] = None,
        target_annual_vol: float = 0.12,
        min_gross_exposure: float = 0.20,
        max_gross_exposure: float = 1.00
    ) -> Tuple[Dict[str, float], float]:
        """
        Computes portfolio gross exposure and cash buffer ratio based on realized portfolio volatility:
        Gross Exposure = clip(target_annual_vol / max(realized_vol_annual, 0.04), min_gross, max_gross)
        Cash Buffer Ratio = 1.0 - Gross Exposure

        Returns:
            Tuple of (scaled_weights_dict, cash_buffer_ratio)
        """
        if not target_weights:
            return {}, 1.0

        if returns_matrix is None or len(returns_matrix) < 15 or returns_matrix.shape[1] != len(target_weights):
            return dict(target_weights), 0.0

        try:
            w_vec = np.array(list(target_weights.values()), dtype=np.float64)
            w_sum = np.sum(w_vec)
            if w_sum > 0:
                w_norm = w_vec / w_sum
            else:
                return dict(target_weights), 0.0

            port_daily_ret = returns_matrix @ w_norm

            # RiskMetrics EWMA conditional volatility (lambda = 0.94 / span = 20)
            n_obs = len(port_daily_ret)
            weights_ewma = np.exp(-np.arange(n_obs)[::-1] / 20.0)
            weights_ewma /= np.sum(weights_ewma)

            realized_var_daily = float(np.sum(weights_ewma * (port_daily_ret ** 2)))
            realized_vol_annual = float(np.sqrt(max(1e-8, realized_var_daily * 252.0)))

            gross_exposure = float(np.clip(
                target_annual_vol / max(realized_vol_annual, 0.04),
                min_gross_exposure,
                max_gross_exposure
            ))
            cash_ratio = max(0.0, 1.0 - gross_exposure)

            scaled_weights = {k: float(v * gross_exposure) for k, v in target_weights.items()}
            logger.info(
                f"[DVT CASH OVERLAY] Realized Ann Vol={realized_vol_annual:.2%}, Target Vol={target_annual_vol:.2%}, "
                f"Gross Exposure={gross_exposure:.2%}, Cash Buffer={cash_ratio:.2%}"
            )
            return scaled_weights, cash_ratio
        except Exception as e:
            logger.warning(f"[DVT CASH OVERLAY] Failed to compute DVT weights: {e}")
            return dict(target_weights), 0.0

    # =========================================================================
    # OBJECTIVE 6: CLOSED-LOOP REALIZED SLIPPAGE FEEDBACK SIZING HAIRCUT
    # =========================================================================

    def apply_slippage_feedback_haircut(
        self,
        weights_dict: Dict[str, float],
        realized_slippage_map: Optional[Dict[str, float]] = None,
        max_slippage_bps_threshold: float = 30.0
    ) -> Dict[str, float]:
        """
        Applies dynamic position haircut based on realized execution slippage from trade_logs.db.
        If an asset's realized slippage exceeds threshold (e.g. 30 bps = 0.30%),
        its allocation is scaled down by kappa_slip = max(0.50, 1.0 - (excess_bps / 100.0) * 2.0).
        """
        if not weights_dict or not realized_slippage_map:
            return dict(weights_dict)

        adjusted_weights = {}
        for sym, w in weights_dict.items():
            slip_bps = float(realized_slippage_map.get(sym, 0.0))
            if slip_bps > max_slippage_bps_threshold:
                excess_bps = slip_bps - max_slippage_bps_threshold
                haircut = max(0.50, 1.0 - (excess_bps / 100.0) * 2.0)
                adj_w = w * haircut
                adjusted_weights[sym] = float(adj_w)
                logger.info(
                    f"[SLIPPAGE SIZING HAIRCUT] Symbol {sym}: Realized Slippage {slip_bps:.1f} bps > {max_slippage_bps_threshold} bps threshold "
                    f"-> Haircut multiplier {haircut:.2f} applied (Weight: {w:.3f} -> {adj_w:.3f})"
                )
            else:
                adjusted_weights[sym] = float(w)

        return adjusted_weights


