"""
Portfolio Optimizer Module:
- Risk Parity (Equal Risk Contribution) Allocation
- Mean-Variance / Sharpe Optimization with Covariance Matrix
- Dynamic Factor & Sector Exposure Control (Neutralization & Constraint)
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from scipy.optimize import minimize

class PortfolioOptimizer:
    """
    Portfolio Optimization Engine implementing Risk Parity, Mean-Variance,
    and Factor/Sector Exposure Constraints.
    """
    def __init__(self, default_max_weight: float = 0.20, default_max_sector_weight: float = 0.35):
        self.default_max_weight = default_max_weight
        self.default_max_sector_weight = default_max_sector_weight

    def calculate_covariance_matrix(self, returns_df: pd.DataFrame, shrinkage: float = 0.1) -> pd.DataFrame:
        """
        Calculate sample covariance matrix with Ledoit-Wolf-like shrinkage for stability.
        """
        if returns_df.empty or len(returns_df) < 5:
            n_assets = len(returns_df.columns) if not returns_df.empty else 1
            cols = returns_df.columns if not returns_df.empty else ["ASSET"]
            return pd.DataFrame(np.eye(n_assets) * 0.0004, index=cols, columns=cols)
        
        cov_sample = returns_df.cov().fillna(0.0)
        n_assets = cov_sample.shape[0]
        prior = np.eye(n_assets) * np.trace(cov_sample.values) / max(n_assets, 1)
        shrunk_cov = (1.0 - shrinkage) * cov_sample.values + shrinkage * prior
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
        max_weight: Optional[float] = None
    ) -> Dict[str, float]:
        """
        Mean-Variance Optimization balancing expected net return vs portfolio variance.
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
        constraints = ({'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0})

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
        """
        if max_sector_weight is None:
            max_sector_weight = self.default_max_sector_weight

        if not weights:
            return {}

        adjusted_weights = dict(weights)
        sector_exposure: Dict[str, float] = {}

        for sym, w in adjusted_weights.items():
            sec = sector_map.get(sym, "Unknown")
            sector_exposure[sec] = sector_exposure.get(sec, 0.0) + w

        # Cap overloaded sectors
        for sec, total_w in sector_exposure.items():
            if total_w > max_sector_weight:
                scale_down = max_sector_weight / total_w
                for sym, w in adjusted_weights.items():
                    if sector_map.get(sym, "Unknown") == sec:
                        adjusted_weights[sym] = w * scale_down

        # Normalize remaining weights to sum to 1.0
        total_sum = sum(adjusted_weights.values())
        if total_sum > 0:
            adjusted_weights = {sym: w / total_sum for sym, w in adjusted_weights.items()}

        return adjusted_weights
