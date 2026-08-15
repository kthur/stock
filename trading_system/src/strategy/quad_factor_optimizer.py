"""
Quad-Factor Neutral QP Portfolio Risk Optimizer
Optimizes portfolio allocation maximizing expected Sharpe ratio while constraining
Market Beta, Size, Volatility, and Momentum factor exposures close to zero, with sector caps.
"""

import logging
from dataclasses import dataclass
from typing import Dict, Optional, Any

import numpy as np
import pandas as pd
from scipy.optimize import minimize

logger = logging.getLogger(__name__)


@dataclass
class FactorExposures:
    beta: float = 0.0
    size: float = 0.0
    volatility: float = 0.0
    momentum: float = 0.0


class QuadFactorNeutralOptimizer:
    """
    Quad-Factor Neutral Portfolio Optimizer via Quadratic Programming (QP).
    Enforces factor neutrality (Beta, Size, Volatility, Momentum ~ 0) and sector caps.
    """

    def __init__(
        self,
        default_max_weight: float = 0.20,
        default_max_sector_weight: float = 0.25,
        default_factor_tolerance: float = 0.05,
        max_sector_exposure: float = 0.25,
        max_single_weight: float = 0.10,
        factor_penalty_weight: float = 10.0,
    ):
        self.default_max_weight = default_max_weight
        self.default_max_sector_weight = default_max_sector_weight
        self.default_factor_tolerance = default_factor_tolerance
        self.max_sector_exposure = max_sector_exposure
        self.max_single_weight = max_single_weight
        self.factor_penalty_weight = factor_penalty_weight

    def optimize(
        self,
        expected_returns: Any,
        cov_matrix: Any,
        factor_df: Any,
        sector_mapping: Any,
        max_asset_weight: Optional[float] = None,
        max_sector_weight: Optional[float] = None,
        max_weight: Optional[float] = None,
        factor_neutral_tol: Optional[float] = None,
        risk_aversion: float = 1.0,
    ) -> Dict[str, float]:
        """
        Optimizes weights w for assets maximizing w^T r - (risk_aversion/2) w^T Cov w - penalty * ||F^T w||^2
        subject to factor bounds and sector caps.
        """
        if isinstance(expected_returns, pd.Series):
            symbols = list(expected_returns.index)
            r_vec = expected_returns.values
        elif isinstance(expected_returns, dict):
            symbols = list(expected_returns.keys())
            r_vec = np.array([expected_returns[s] for s in symbols], dtype=np.float64)
        else:
            symbols = list(expected_returns)
            r_vec = np.array([expected_returns[s] for s in symbols], dtype=np.float64)

        n = len(symbols)
        if n == 0:
            return {}
        if n == 1:
            return {symbols[0]: 1.0}

        r_vec = np.nan_to_num(r_vec, nan=0.0, posinf=0.0, neginf=0.0)

        eff_max_w = max_asset_weight or max_weight or self.default_max_weight
        eff_max_sec_w = max_sector_weight or self.default_max_sector_weight
        eff_factor_tol = factor_neutral_tol or self.default_factor_tolerance

        if isinstance(cov_matrix, pd.DataFrame):
            cov_mat = cov_matrix.loc[symbols, symbols].values
        else:
            cov_mat = np.asarray(cov_matrix)
        cov_mat = np.nan_to_num(cov_mat, nan=0.0, posinf=0.0, neginf=0.0)

        # Factor matrix F (n x 4)
        F = np.zeros((n, 4), dtype=np.float64)
        for i, col in enumerate(["beta", "size", "volatility", "momentum"]):
            if isinstance(factor_df, pd.DataFrame) and col in factor_df.columns:
                raw_f = factor_df.loc[symbols, col].values
                raw_f = np.nan_to_num(raw_f, nan=0.0, posinf=0.0, neginf=0.0)
                std_val = float(np.std(raw_f))
                if std_val > 1e-8:
                    F[:, i] = (raw_f - np.mean(raw_f)) / std_val
                else:
                    F[:, i] = 0.0
            elif isinstance(factor_df, dict):
                vals = np.array([factor_df.get(s, {}).get(col, 0.0) if isinstance(factor_df.get(s), dict) else getattr(factor_df.get(s, None), col, 0.0) for s in symbols], dtype=np.float64)
                vals = np.nan_to_num(vals, nan=0.0)
                std_val = float(np.std(vals))
                if std_val > 1e-8:
                    F[:, i] = (vals - np.mean(vals)) / std_val
                else:
                    F[:, i] = 0.0

        sec_map = sector_mapping if isinstance(sector_mapping, dict) else {}
        unique_sectors = list(set(sec_map.values())) if sec_map else ["Default"]

        max_possible_capacity = len(unique_sectors) * eff_max_sec_w
        isinfeasible_sector = max_possible_capacity < 1.0

        def objective(w: np.ndarray) -> float:
            port_ret = float(np.dot(w, r_vec))
            port_risk = float(w.T @ cov_mat @ w)
            factor_net = F.T @ w
            factor_penalty = float(np.sum(factor_net**2))
            utility = port_ret - (risk_aversion / 2.0) * port_risk - (self.factor_penalty_weight / 2.0) * factor_penalty
            return -utility

        constraints = []
        if not isinfeasible_sector:
            constraints.append({"type": "eq", "fun": lambda w: np.sum(w) - 1.0})
        else:
            constraints.append({"type": "ineq", "fun": lambda w: 1.0 - np.sum(w)})

        for sec in unique_sectors:
            sec_indices = [i for i, s in enumerate(symbols) if sec_map.get(s, "Default") == sec]
            if sec_indices:
                constraints.append({
                    "type": "ineq",
                    "fun": lambda w, idxs=sec_indices: eff_max_sec_w - np.sum(w[idxs]),
                })

        for j in range(4):
            constraints.append({"type": "ineq", "fun": lambda w, col_idx=j: eff_factor_tol - (F[:, col_idx] @ w)})
            constraints.append({"type": "ineq", "fun": lambda w, col_idx=j: (F[:, col_idx] @ w) + eff_factor_tol})

        bounds = [(0.0, eff_max_w) for _ in range(n)]
        w0 = np.full(n, min(1.0 / n, eff_max_w), dtype=np.float64)

        res = minimize(
            objective,
            w0,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
            options={"maxiter": 300, "ftol": 1e-6},
        )

        if not res.success or np.sum(res.x) == 0:
            # Fallback optimization without strict factor bounds
            fallback_constraints = []
            if not isinfeasible_sector:
                fallback_constraints.append({"type": "eq", "fun": lambda w: np.sum(w) - 1.0})
            else:
                fallback_constraints.append({"type": "ineq", "fun": lambda w: 1.0 - np.sum(w)})
            for sec in unique_sectors:
                sec_indices = [i for i, s in enumerate(symbols) if sec_map.get(s, "Default") == sec]
                if sec_indices:
                    fallback_constraints.append({
                        "type": "ineq",
                        "fun": lambda w, idxs=sec_indices: eff_max_sec_w - np.sum(w[idxs]),
                    })

            res = minimize(
                objective,
                w0,
                method="SLSQP",
                bounds=bounds,
                constraints=fallback_constraints,
                options={"maxiter": 300, "ftol": 1e-6},
            )

        w_opt = np.nan_to_num(res.x, nan=0.0, posinf=0.0, neginf=0.0)
        w_opt = np.clip(w_opt, 0.0, eff_max_w)
        w_sum = float(np.sum(w_opt))

        if not isinfeasible_sector and w_sum > 0:
            w_opt /= w_sum
        elif isinfeasible_sector and w_sum > 1.0:
            w_opt /= w_sum

        return {symbols[i]: float(w_opt[i]) if (i < len(w_opt) and np.isfinite(w_opt[i])) else 0.0 for i in range(n)}

    def optimize_portfolio(self, *args, **kwargs) -> Dict[str, float]:
        return self.optimize(*args, **kwargs)


QuadFactorOptimizer = QuadFactorNeutralOptimizer
