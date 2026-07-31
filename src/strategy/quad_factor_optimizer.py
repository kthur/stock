"""
Quad-Factor Neutral QP Portfolio Risk Optimizer.

Formulation:
    min_w  1/2 * w^T * Sigma * w - lambda * mu^T * w + gamma * ||w - w_0||_2^2
    s.t.   sum(w_i) = 1.0
           0 <= w_i <= max_weight (default 0.10)
           |factor_k^T * w| <= factor_eps (default 0.05 for beta, size, vol, mom)
           sum_{i in Sector_k}(w_i) <= max_sector_weight (default 0.25)
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Union, Any
from scipy.optimize import minimize

try:
    import cvxpy as cp
    HAS_CVXPY = True
except ImportError:
    HAS_CVXPY = False

logger = logging.getLogger(__name__)


def _apply_bounded_normalization(
    weights: np.ndarray,
    symbols: List[str],
    sector_map: Dict[str, str],
    max_w: float,
    max_sec_w: float
) -> np.ndarray:
    """
    Applies bounded normalization / iterative water-filling to weight vector w.
    Guarantees:
    - w_i <= max_w + 1e-5 for all i
    - sum_{i in Sector_k} w_i <= max_sec_w + 1e-5 for all k
    - sum(w) <= 1.0 + 1e-5 (and close to 1.0 if capacity permits)
    """
    n_assets = len(symbols)
    if n_assets == 0 or weights is None:
        return weights

    weights = np.clip(weights, 0.0, max_w)
    sectors = sorted(list(set(sector_map.get(s, "Unknown") for s in symbols)))

    for _ in range(10):
        # 1. Cap sector weights at max_sec_w
        for sec in sectors:
            idx = [i for i, s in enumerate(symbols) if sector_map.get(s, "Unknown") == sec]
            if idx:
                s_sum = np.sum(weights[idx])
                if s_sum > max_sec_w + 1e-8:
                    weights[idx] *= (max_sec_w / s_sum)

        # 2. Cap asset bounds at max_w
        weights = np.clip(weights, 0.0, max_w)

        # 3. Check total sum
        w_tot = np.sum(weights)
        if abs(w_tot - 1.0) < 1e-6 or w_tot <= 0:
            break

        if w_tot > 1.0:
            weights /= w_tot
        else:
            # w_tot < 1.0: scale up uncapped sectors / assets
            eligible = []
            for sec in sectors:
                idx = [i for i, s in enumerate(symbols) if sector_map.get(s, "Unknown") == sec]
                s_sum = np.sum(weights[idx])
                if s_sum < max_sec_w - 1e-8:
                    for i in idx:
                        if weights[i] < max_w - 1e-8:
                            eligible.append(i)

            if not eligible:
                break

            needed = 1.0 - w_tot
            el_sum = np.sum(weights[eligible])
            if el_sum > 1e-8:
                scale = 1.0 + (needed / el_sum)
                weights[eligible] *= scale
            else:
                add_w = needed / len(eligible)
                weights[eligible] += add_w

    # Final pass: strictly cap sectors and assets
    for sec in sectors:
        idx = [i for i, s in enumerate(symbols) if sector_map.get(s, "Unknown") == sec]
        if idx:
            s_sum = np.sum(weights[idx])
            if s_sum > max_sec_w + 1e-8:
                weights[idx] *= (max_sec_w / s_sum)
    weights = np.clip(weights, 0.0, max_w)

    w_tot = np.sum(weights)
    if w_tot > 1.0 + 1e-8:
        weights /= w_tot

    return weights


class QuadFactorOptimizer:
    """
    Quadratic Programming (QP) Portfolio Risk Optimizer enforcing Quad-Factor Neutrality,
    sector concentration caps, and single-asset bounds.
    """

    def __init__(
        self,
        risk_aversion: float = 1.0,
        turnover_penalty: float = 0.01,
        default_max_weight: float = 0.10,
        default_max_sector_weight: float = 0.25,
        default_factor_tolerance: float = 0.05,
        use_cvxpy_if_available: bool = True
    ):
        self.risk_aversion = risk_aversion
        self.turnover_penalty = turnover_penalty
        self.default_max_weight = default_max_weight
        self.default_max_sector_weight = default_max_sector_weight
        self.default_factor_tolerance = default_factor_tolerance
        self.use_cvxpy_if_available = use_cvxpy_if_available

    def optimize(
        self,
        expected_returns: pd.Series,
        cov_matrix: Union[pd.DataFrame, np.ndarray],
        factor_df: pd.DataFrame,
        sector_map: Dict[str, str],
        w_initial: Optional[Dict[str, float]] = None,
        max_weight: Optional[float] = None,
        max_sector_weight: Optional[float] = None,
        factor_tolerances: Optional[Union[Dict[str, float], float]] = None
    ) -> Dict[str, float]:
        """
        Solves the Quad-Factor Neutral QP Portfolio Risk Optimization problem.

        Parameters:
            expected_returns: Expected returns per asset (Series indexed by symbol).
            cov_matrix: Assets covariance matrix (DataFrame or 2D array).
            factor_df: Factor matrix (DataFrame indexed by symbol, columns: 'beta', 'size', 'volatility', 'momentum').
            sector_map: Dict mapping symbol -> sector string.
            w_initial: Optional initial portfolio weights for turnover penalty (defaults to equal weights).
            max_weight: Maximum single-asset weight bound (default: 0.10).
            max_sector_weight: Maximum sector weight bound (default: 0.25).
            factor_tolerances: Dict of tolerance limits per factor or float limit for all factors.

        Returns:
            Dict[str, float]: Optimized asset weight vector mapping symbol -> weight.
        """
        symbols = list(expected_returns.index)
        n_assets = len(symbols)
        if n_assets == 0:
            return {}
        if n_assets == 1:
            return {symbols[0]: 1.0}

        max_w = max_weight if max_weight is not None else self.default_max_weight
        max_sec_w = max_sector_weight if max_sector_weight is not None else self.default_max_sector_weight

        # Align inputs to symbols order
        mu = expected_returns.loc[symbols].values.astype(np.float64)
        if isinstance(cov_matrix, np.ndarray):
            cov_df = pd.DataFrame(cov_matrix, index=symbols, columns=symbols)
        else:
            cov_df = cov_matrix
        Sigma = cov_df.loc[symbols, symbols].values.astype(np.float64)

        # Parse initial weights w0
        if w_initial is not None:
            w0 = np.array([w_initial.get(s, 0.0) for s in symbols], dtype=np.float64)
            w0_sum = np.sum(w0)
            if w0_sum > 1e-6:
                w0 = w0 / w0_sum
            else:
                w0 = np.ones(n_assets) / n_assets
        else:
            w0 = np.ones(n_assets) / n_assets

        # Standardize Factors (Z-score normalization)
        factors = ['beta', 'size', 'volatility', 'momentum']
        tol_dict = {}
        if isinstance(factor_tolerances, dict):
            tol_dict = dict(factor_tolerances)
        elif isinstance(factor_tolerances, (int, float)):
            tol_dict = {f: float(factor_tolerances) for f in factors}
        else:
            tol_dict = {f: self.default_factor_tolerance for f in factors}

        col_map = {str(c).lower(): c for c in factor_df.columns}
        standardized_factors = {}

        for f in factors:
            target_col = col_map.get(f.lower())
            if target_col is not None and symbols[0] in factor_df.index:
                raw_f = factor_df.loc[symbols, target_col].values.astype(np.float64)
                std_f = np.nan_to_num(raw_f, nan=0.0, posinf=0.0, neginf=0.0)
                std_val = np.std(std_f)
                if std_val > 1e-8:
                    norm_f = (std_f - np.mean(std_f)) / std_val
                else:
                    norm_f = np.zeros(n_assets)
                standardized_factors[f] = norm_f
            else:
                standardized_factors[f] = np.zeros(n_assets)

        # 2. Primary Solver Selection (CVXPY vs SciPy SLSQP)
        weights = None
        if self.use_cvxpy_if_available and HAS_CVXPY:
            weights = self._solve_cvxpy(
                symbols, mu, Sigma, standardized_factors, sector_map,
                w0, max_w, max_sec_w, tol_dict
            )

        if weights is None:
            weights = self._solve_scipy_slsqp(
                symbols, mu, Sigma, standardized_factors, sector_map,
                w0, max_w, max_sec_w, tol_dict
            )

        # 3. Robust 3-Tier Fallback Hierarchy if optimization fails or is infeasible
        if weights is None:
            logger.warning("QuadFactorOptimizer primary QP solver failed. Triggering Tier 1 Fallback (Relaxed Factor Bounds).")
            relaxed_tols = {f: tol_dict.get(f, self.default_factor_tolerance) * 2.0 for f in factors}
            weights = self._solve_scipy_slsqp(
                symbols, mu, Sigma, standardized_factors, sector_map,
                w0, max_w, max_sec_w, relaxed_tols
            )

        if weights is None:
            logger.warning("Tier 1 Fallback failed. Triggering Tier 2 Fallback (Mean-Variance / Sector Capped MVO).")
            weights = self._solve_scipy_slsqp(
                symbols, mu, Sigma, {}, sector_map,
                w0, max_w, max_sec_w, {}
            )

        if weights is None:
            logger.warning("Tier 2 Fallback failed. Triggering Tier 3 Fallback (Equal Weight with Sector Caps).")
            weights = self._fallback_equal_weight(symbols, sector_map, max_w, max_sec_w)

        # Final Bounded Normalization & Cleaning
        weights = _apply_bounded_normalization(weights, symbols, sector_map, max_w, max_sec_w)

        return {sym: float(w) for sym, w in zip(symbols, weights)}

    def optimize_portfolio(
        self,
        expected_returns: pd.Series,
        cov_matrix: Union[pd.DataFrame, np.ndarray],
        factor_df: pd.DataFrame,
        sector_map: Dict[str, str],
        max_asset_weight: float = 0.10,
        max_sector_weight: float = 0.25,
        factor_neutral_tol: float = 0.05,
        w_initial: Optional[Dict[str, float]] = None
    ) -> Dict[str, float]:
        """
        Convenience method matching task prompt parameter naming.
        """
        return self.optimize(
            expected_returns=expected_returns,
            cov_matrix=cov_matrix,
            factor_df=factor_df,
            sector_map=sector_map,
            w_initial=w_initial,
            max_weight=max_asset_weight,
            max_sector_weight=max_sector_weight,
            factor_tolerances=factor_neutral_tol
        )

    def _solve_scipy_slsqp(
        self,
        symbols: List[str],
        mu: np.ndarray,
        Sigma: np.ndarray,
        factors: Dict[str, np.ndarray],
        sector_map: Dict[str, str],
        w0: np.ndarray,
        max_w: float,
        max_sec_w: float,
        tolerances: Dict[str, float]
    ) -> Optional[np.ndarray]:
        """
        Solves QP formulation using scipy.optimize.minimize with SLSQP solver.
        """
        n_assets = len(symbols)

        # Objective Function f(w) = 0.5 * w^T * Sigma * w - lambda * mu^T * w + gamma * ||w - w0||^2
        def objective(w):
            risk_term = 0.5 * np.dot(w.T, np.dot(Sigma, w))
            return_term = self.risk_aversion * np.dot(w, mu)
            turnover_term = self.turnover_penalty * np.sum((w - w0) ** 2)
            return risk_term - return_term + turnover_term

        # Analytical Gradient df(w)/dw = Sigma * w - lambda * mu + 2 * gamma * (w - w0)
        def jacobian(w):
            return np.dot(Sigma, w) - self.risk_aversion * mu + 2.0 * self.turnover_penalty * (w - w0)

        # Constraints Construction
        constraints = []

        # 1. Sum of weights == 1.0 (Equality)
        constraints.append({
            'type': 'eq',
            'fun': lambda w: np.sum(w) - 1.0,
            'jac': lambda w: np.ones(n_assets)
        })

        # 2. Factor Neutrality Bounds (-eps <= f^T * w <= eps)
        for fname, fvec in factors.items():
            eps = tolerances.get(fname, self.default_factor_tolerance)
            constraints.append({
                'type': 'ineq',
                'fun': lambda w, f=fvec, e=eps: e - np.dot(f, w),
                'jac': lambda w, f=fvec, e=eps: -f
            })
            constraints.append({
                'type': 'ineq',
                'fun': lambda w, f=fvec, e=eps: np.dot(f, w) + e,
                'jac': lambda w, f=fvec, e=eps: f
            })

        # 3. Sector Concentration Caps (sum_{i in Sector_k}(w_i) <= max_sec_w)
        sectors = set(sector_map.get(s, "Unknown") for s in symbols)
        for sec in sectors:
            indices = [i for i, s in enumerate(symbols) if sector_map.get(s, "Unknown") == sec]
            if indices:
                indices_arr = np.array(indices)
                jac_vec = np.zeros(n_assets)
                jac_vec[indices_arr] = -1.0
                constraints.append({
                    'type': 'ineq',
                    'fun': lambda w, idx=indices, m=max_sec_w: m - np.sum(w[idx]),
                    'jac': lambda w, jv=jac_vec: jv
                })

        # 4. Long-Only Bounds (0 <= w_i <= max_w)
        bounds = tuple((0.0, max_w) for _ in range(n_assets))

        init_w = self._fallback_equal_weight(symbols, sector_map, max_w, max_sec_w)

        try:
            res = minimize(
                objective,
                init_w,
                method='SLSQP',
                jac=jacobian,
                bounds=bounds,
                constraints=constraints,
                options={'maxiter': 1000, 'ftol': 1e-8}
            )

            w_opt = res.x
            if w_opt is not None and not np.isnan(w_opt).any():
                # Verify key constraints feasibility
                if abs(np.sum(w_opt) - 1.0) < 0.05:
                    return w_opt

            logger.debug(f"SciPy SLSQP failed to converge: {res.message if hasattr(res, 'message') else 'unsuccessful'}")
            return None
        except Exception as e:
            logger.debug(f"SciPy SLSQP solver exception: {e}")
            return None

    def _solve_cvxpy(
        self,
        symbols: List[str],
        mu: np.ndarray,
        Sigma: np.ndarray,
        factors: Dict[str, np.ndarray],
        sector_map: Dict[str, str],
        w0: np.ndarray,
        max_w: float,
        max_sec_w: float,
        tolerances: Dict[str, float]
    ) -> Optional[np.ndarray]:
        """
        Solves QP formulation using CVXPY if available.
        """
        if not HAS_CVXPY:
            return None

        n_assets = len(symbols)
        w = cp.Variable(n_assets)

        risk_term = 0.5 * cp.quad_form(w, Sigma)
        return_term = self.risk_aversion * (mu @ w)
        turnover_term = self.turnover_penalty * cp.sum_squares(w - w0)
        objective = cp.Minimize(risk_term - return_term + turnover_term)

        constraints = [
            cp.sum(w) == 1.0,
            w >= 0.0,
            w <= max_w
        ]

        for fname, fvec in factors.items():
            eps = tolerances.get(fname, self.default_factor_tolerance)
            constraints.append(fvec @ w <= eps)
            constraints.append(fvec @ w >= -eps)

        sectors = set(sector_map.get(s, "Unknown") for s in symbols)
        for sec in sectors:
            indices = [i for i, s in enumerate(symbols) if sector_map.get(s, "Unknown") == sec]
            if indices:
                constraints.append(cp.sum(w[indices]) <= max_sec_w)

        try:
            prob = cp.Problem(objective, constraints)
            prob.solve(solver=cp.OSQP, verbose=False)

            if prob.status in [cp.OPTIMAL, cp.OPTIMAL_INACCURATE] and w.value is not None:
                return w.value
            else:
                logger.debug(f"CVXPY solver status: {prob.status}")
                return None
        except Exception as e:
            logger.debug(f"CVXPY solver exception: {e}")
            return None

    def _fallback_equal_weight(
        self,
        symbols: List[str],
        sector_map: Dict[str, str],
        max_w: float,
        max_sec_w: float
    ) -> np.ndarray:
        """
        Calculates equal weight allocation subject to single asset and sector caps
        via iterative water-filling / bounded projection.
        """
        n_assets = len(symbols)
        if n_assets == 0:
            return np.array([], dtype=np.float64)

        weights = np.ones(n_assets, dtype=np.float64) / n_assets
        return _apply_bounded_normalization(weights, symbols, sector_map, max_w, max_sec_w)
