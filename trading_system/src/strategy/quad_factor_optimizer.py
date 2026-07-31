"""
Quad-Factor Neutral QP Portfolio Risk Optimizer
Optimizes portfolio allocation maximizing expected Sharpe ratio while constraining
Market Beta, Size, Volatility, and Momentum factor exposures close to zero, with sector caps.
"""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np
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
        max_sector_exposure: float = 0.25,
        max_single_weight: float = 0.10,
        factor_penalty_weight: float = 10.0,
    ):
        self.max_sector_exposure = max_sector_exposure
        self.max_single_weight = max_single_weight
        self.factor_penalty_weight = factor_penalty_weight

    def optimize(
        self,
        expected_returns: Dict[str, float],
        cov_matrix: np.ndarray,
        factor_exposures: Dict[str, FactorExposures],
        sector_mapping: Dict[str, str],
        risk_aversion: float = 1.0,
    ) -> Dict[str, float]:
        """
        Optimizes weights w for assets maximizing w^T r - (risk_aversion/2) w^T Cov w - penalty * ||F^T w||^2
        subject to sum(w) = 1, 0 <= w_i <= max_single_weight, and sector sum <= max_sector_exposure.
        """
        symbols = list(expected_returns.keys())
        n = len(symbols)
        if n == 0:
            return {}
        if n == 1:
            return {symbols[0]: 1.0}

        r = np.array([expected_returns[s] for s in symbols], dtype=np.float64)

        # Build Factor Matrix F (n x 4)
        F = np.zeros((n, 4), dtype=np.float64)
        for i, s in enumerate(symbols):
            fe = factor_exposures.get(s, FactorExposures())
            F[i, 0] = fe.beta
            F[i, 1] = fe.size
            F[i, 2] = fe.volatility
            F[i, 3] = fe.momentum

        # Sector mapping matrix S (n x num_sectors)
        unique_sectors = list(set(sector_mapping.values())) if sector_mapping else ["Default"]
        sector_indices = {sec: idx for idx, sec in enumerate(unique_sectors)}

        def objective(w: np.ndarray) -> float:
            port_ret = float(np.dot(w, r))
            port_risk = float(w.T @ cov_matrix @ w)
            factor_net = F.T @ w  # 4-dim
            factor_penalty = float(np.sum(factor_net**2))
            # Objective to MINIMIZE: -utility
            utility = port_ret - (risk_aversion / 2.0) * port_risk - (self.factor_penalty_weight / 2.0) * factor_penalty
            return -utility

        # Constraints: sum(w) == 1
        constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]

        # Sector constraints: sum_{i in sec} w_i <= max_sector_exposure
        for sec in unique_sectors:
            sec_indices = [i for i, s in enumerate(symbols) if sector_mapping.get(s, "Default") == sec]
            if sec_indices:
                constraints.append({
                    "type": "ineq",
                    "fun": lambda w, idxs=sec_indices: self.max_sector_exposure - np.sum(w[idxs]),
                })

        # Bounds: 0 <= w_i <= max_single_weight
        effective_max_w = max(1.0 / n, self.max_single_weight)
        bounds = [(0.0, effective_max_w) for _ in range(n)]

        # Initial weights: equal weight
        w0 = np.full(n, 1.0 / n, dtype=np.float64)

        res = minimize(
            objective,
            w0,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
            options={"maxiter": 300, "ftol": 1e-6},
        )

        if not res.success:
            logger.warning(f"QP Optimization warning: {res.message}. Falling back to normalized weights.")
            w_opt = np.maximum(0, res.x)
            w_sum = np.sum(w_opt)
            if w_sum > 0:
                w_opt /= w_sum
            else:
                w_opt = w0
        else:
            w_opt = res.x

        # Normalize to ensure sum == 1
        w_opt = np.clip(w_opt, 0.0, 1.0)
        w_sum = np.sum(w_opt)
        if w_sum > 0:
            w_opt /= w_sum

        return {symbols[i]: float(w_opt[i]) for i in range(n)}
