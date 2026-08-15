"""
Portfolio Optimizer Module:
- Risk Parity (Equal Risk Contribution) Allocation
- Mean-Variance / Sharpe Optimization with Covariance Matrix & EVT-CVaR Loss Budget Constraints
- Dynamic Factor & Sector Exposure Control (Neutralization & Constraint)
- Dynamic Band Rebalancing Signal Trigger Evaluation
"""

import numpy as np
import pandas as pd
import logging
from typing import Dict, Optional, Union
from scipy.optimize import minimize

logger = logging.getLogger(__name__)


class PortfolioOptimizer:
    """
    Portfolio Optimization Engine implementing Risk Parity, Mean-Variance,
    EVT-CVaR Tail Loss Constraints, and Factor/Sector Exposure Constraints.
    """
    def __init__(self, default_max_weight: float = 0.15, default_max_sector_weight: float = 0.30):
        safe_max_w = float(default_max_weight) if (default_max_weight is not None and np.isfinite(default_max_weight)) else 0.15
        self.default_max_weight = max(0.01, min(1.0, safe_max_w))
        safe_sec_w = float(default_max_sector_weight) if (default_max_sector_weight is not None and np.isfinite(default_max_sector_weight)) else 0.30
        self.default_max_sector_weight = max(0.01, min(1.0, safe_sec_w))

    def calculate_covariance_matrix(self, returns_df: pd.DataFrame, shrinkage: float = 0.1) -> pd.DataFrame:
        """
        Calculate sample covariance matrix with Ledoit-Wolf-like shrinkage for stability.
        """
        safe_shrinkage = float(shrinkage) if (shrinkage is not None and np.isfinite(shrinkage)) else 0.1
        safe_shrinkage = max(0.0, min(1.0, safe_shrinkage))

        if returns_df.empty or len(returns_df) < 5:
            n_assets = len(returns_df.columns) if not returns_df.empty else 1
            cols = returns_df.columns if not returns_df.empty else ["ASSET"]
            return pd.DataFrame(np.eye(n_assets) * 0.0004, index=cols, columns=cols)

        cov_sample = returns_df.cov().fillna(0.0)
        n_assets = cov_sample.shape[0]
        prior = np.eye(n_assets) * np.trace(cov_sample.values) / max(n_assets, 1)
        shrunk_cov = (1.0 - safe_shrinkage) * cov_sample.values + safe_shrinkage * prior
        return pd.DataFrame(shrunk_cov, index=returns_df.columns, columns=returns_df.columns)

    def optimize_risk_parity(
        self,
        returns_df: pd.DataFrame,
        max_weight: Optional[float] = None
    ) -> Dict[str, float]:
        """
        Equal Risk Contribution (ERC) Risk Parity Optimizer.
        Finds asset weights such that each asset contributes equally to total portfolio risk.
        """
        if max_weight is None:
            max_weight = self.default_max_weight

        symbols = list(returns_df.columns)
        n_assets = len(symbols)
        if n_assets == 0:
            return {}
        if n_assets == 1:
            return {symbols[0]: 1.0}

        cov_matrix = self.calculate_covariance_matrix(returns_df).values

        def risk_budget_objective(weights, cov):
            portfolio_vol = np.sqrt(np.dot(weights.T, np.dot(cov, weights)))
            if portfolio_vol < 1e-8:
                return 0.0
            marginal_contrib = np.dot(cov, weights) / portfolio_vol
            risk_contrib = weights * marginal_contrib
            target_risk = portfolio_vol / n_assets
            return np.sum((risk_contrib - target_risk) ** 2)

        init_weights = np.ones(n_assets) / n_assets
        bounds = tuple((0.0, max_weight) for _ in range(n_assets))
        constraints = ({'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0})

        res = minimize(
            risk_budget_objective,
            init_weights,
            args=(cov_matrix,),
            method='SLSQP',
            bounds=bounds,
            constraints=constraints,
            options={'maxiter': 500, 'ftol': 1e-9}
        )

        if not res.success:
            weights = init_weights
        else:
            weights = res.x / np.sum(res.x)

        return {sym: float(w) for sym, w in zip(symbols, weights)}

    def optimize_mean_variance(
        self,
        expected_returns: pd.Series,
        returns_df: pd.DataFrame,
        risk_aversion: float = 1.0,
        max_weight: Optional[float] = None,
        max_cvar_limit: Optional[float] = None,
        cvar_confidence: float = 0.95
    ) -> Dict[str, float]:
        """
        Mean-Variance Optimization balancing expected net return vs portfolio variance,
        optionally constrained by EVT-CVaR loss budget limit (EVT_CVaR(w) <= max_cvar_limit).
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
        cov_matrix = self.calculate_covariance_matrix(returns_sub).values
        mu = expected_returns.values

        def mvo_objective(weights):
            ret = np.dot(weights, mu)
            vol = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
            utility = ret - 0.5 * risk_aversion * (vol ** 2)
            return -utility

        init_weights = np.ones(n_assets) / n_assets
        bounds = tuple((0.0, max_weight) for _ in range(n_assets))
        constraints = [{'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0}]

        if max_cvar_limit is not None and not returns_sub.empty and len(returns_sub) >= 5:
            from trading_system.src.risk.portfolio_allocator import PortfolioAllocator
            allocator = PortfolioAllocator()
            returns_matrix = returns_sub.values

            def cvar_constraint(w):
                evt_cvar = allocator.estimate_portfolio_evt_cvar(w, returns_matrix, confidence=cvar_confidence)
                return max_cvar_limit - evt_cvar

            constraints.append({'type': 'ineq', 'fun': cvar_constraint})

        res = minimize(
            mvo_objective,
            init_weights,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints,
            options={'maxiter': 500, 'ftol': 1e-9}
        )

        if not res.success:
            weights = init_weights
        else:
            weights = res.x / np.sum(res.x)

        return {sym: float(w) for sym, w in zip(symbols, weights)}

    def apply_factor_and_sector_constraints(
        self,
        weights: Dict[str, float],
        sector_map: Dict[str, str],
        max_sector_weight: Optional[float] = None
    ) -> Dict[str, float]:
        """
        Applies sector exposure capping to avoid over-concentration in a single industry.
        Overloaded sectors exceeding max_sector_weight are capped without inflating
        under-loaded sectors past max_sector_weight. Total sum is maintained <= 1.0.
        """
        if max_sector_weight is None:
            max_sector_weight = self.default_max_sector_weight

        if not weights:
            return {}

        total_w = sum(weights.values())
        if total_w < 1e-8:
            return dict(weights)

        symbols = list(weights.keys())
        w_arr = np.array([weights[s] for s in symbols], dtype=np.float64)
        if total_w > 1.0 + 1e-8:
            w_arr /= total_w

        sectors = sorted(list(set(sector_map.get(s, "Unknown") for s in symbols)))

        for _ in range(10):
            # 1. Cap sector weights at max_sector_weight
            for sec in sectors:
                idx = [i for i, s in enumerate(symbols) if sector_map.get(s, "Unknown") == sec]
                if idx:
                    s_sum = np.sum(w_arr[idx])
                    if s_sum > max_sector_weight + 1e-8:
                        w_arr[idx] *= (max_sector_weight / s_sum)

            # 2. Check total sum
            w_tot = np.sum(w_arr)
            if abs(w_tot - 1.0) < 1e-6 or w_tot <= 0:
                break

            if w_tot > 1.0:
                w_arr /= w_tot
            else:
                # w_tot < 1.0: scale up only sectors that have s_sum < max_sector_weight - 1e-8
                eligible_secs = []
                for sec in sectors:
                    idx = [i for i, s in enumerate(symbols) if sector_map.get(s, "Unknown") == sec]
                    if idx:
                        s_sum = np.sum(w_arr[idx])
                        if s_sum < max_sector_weight - 1e-8:
                            eligible_secs.append(sec)

                if not eligible_secs:
                    break

                needed = 1.0 - w_tot
                eligible_idx = [i for i, s in enumerate(symbols) if sector_map.get(s, "Unknown") in eligible_secs]
                el_sum = np.sum(w_arr[eligible_idx])

                if el_sum > 1e-8:
                    scale = 1.0 + (needed / el_sum)
                    w_arr[eligible_idx] *= scale
                else:
                    add_w = needed / len(eligible_idx)
                    w_arr[eligible_idx] += add_w

        # Final pass: strictly cap sectors at max_sector_weight
        for sec in sectors:
            idx = [i for i, s in enumerate(symbols) if sector_map.get(s, "Unknown") == sec]
            if idx:
                s_sum = np.sum(w_arr[idx])
                if s_sum > max_sector_weight + 1e-8:
                    w_arr[idx] *= (max_sector_weight / s_sum)

        w_tot = np.sum(w_arr)
        if w_tot > 1.0 + 1e-8:
            w_arr /= w_tot

        return {sym: float(w) for sym, w in zip(symbols, w_arr)}

    def check_rebalance_trigger(
        self,
        current_weights: Optional[Dict[str, float]],
        target_weights: Optional[Dict[str, float]],
        buffer_band: float = 0.03
    ) -> bool:
        """
        Emits rebalance signal only when allocation drift breaches no-trade buffer bands.
        """
        curr = current_weights or {}
        targ = target_weights or {}
        all_keys = set(curr.keys()).union(set(targ.keys()))
        if not all_keys:
            return False

        max_drift = 0.0
        for k in all_keys:
            w_curr = float(curr.get(k, 0.0)) if np.isfinite(curr.get(k, 0.0)) else 0.0
            w_targ = float(targ.get(k, 0.0)) if np.isfinite(targ.get(k, 0.0)) else 0.0
            max_drift = max(max_drift, abs(w_curr - w_targ))
        return max_drift > buffer_band

    def optimize_quad_factor_portfolio(
        self,
        expected_returns: pd.Series,
        cov_matrix: Union[pd.DataFrame, np.ndarray],
        factor_df: pd.DataFrame,
        sector_map: Dict[str, str],
        w_initial: Optional[Dict[str, float]] = None,
        risk_aversion: float = 1.0,
        turnover_penalty: float = 0.01,
        max_weight: Optional[float] = None,
        max_sector_weight: Optional[float] = None,
        factor_tolerances: Optional[Union[Dict[str, float], float]] = None
    ) -> Dict[str, float]:
        """
        Quad-Factor Neutral QP Portfolio Risk Optimization integration method.

        Parameters:
            expected_returns: Expected net returns per asset (Series indexed by symbol).
            cov_matrix: Asset covariance matrix (DataFrame or 2D array).
            factor_df: Factor DataFrame with columns 'beta', 'size', 'volatility', 'momentum'.
            sector_map: Mapping of symbol -> sector name.
            w_initial: Optional dictionary of current asset weights.
            risk_aversion: Risk aversion parameter lambda.
            turnover_penalty: Turnover penalty gamma.
            max_weight: Single asset weight cap.
            max_sector_weight: Sector weight cap.
            factor_tolerances: Dict of tolerance thresholds per factor or single float threshold.

        Returns:
            Dict[str, float]: Optimized asset weights.
        """
        if expected_returns is None or expected_returns.empty:
            return {}

        from src.strategy.quad_factor_optimizer import QuadFactorOptimizer
        optimizer = QuadFactorOptimizer(
            default_max_weight=max_weight if max_weight is not None else self.default_max_weight,
            default_max_sector_weight=max_sector_weight if max_sector_weight is not None else self.default_max_sector_weight
        )
        return optimizer.optimize(
            expected_returns=expected_returns,
            cov_matrix=cov_matrix,
            factor_df=factor_df,
            sector_mapping=sector_map,
            max_weight=max_weight,
            max_sector_weight=max_sector_weight,
            risk_aversion=risk_aversion
        )
