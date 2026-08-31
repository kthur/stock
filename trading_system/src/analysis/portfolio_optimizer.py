"""
Portfolio Optimization Engine (Functional APIs):
Canonical analytical engine providing functional implementations of:
- Equal Risk Contribution / Risk Parity (calculate_risk_parity_weights)
- 2D Regime-Adaptive Black-Litterman (calculate_black_litterman_weights)
- Ledoit-Wolf Covariance Shrinkage & Spectral Denoising (shrink_covariance_matrix)
- Hierarchical Risk Parity (HRP) & Return-Tilted HRP (calculate_hrp_weights)
- Hierarchical Equal Risk Contribution (HERC) (calculate_herc_weights)
- Portfolio Constraints & Multi-Factor Neutralization (apply_portfolio_constraints)

For object-oriented risk wrapper, see `src.risk.portfolio_optimizer.PortfolioOptimizer`.
"""

import logging
from typing import Optional, Any, Union, List, Dict


import numpy as np
from scipy.optimize import minimize

logger = logging.getLogger(__name__)


def calculate_risk_parity_weights(cov_matrix: np.ndarray) -> np.ndarray:
    """
    Computes true Equal Risk Contribution (ERC) weights using a numerical solver.
    Ensures weights sum to 1.0 and each weight is between 0.0 and 1.0.
    In case of optimizer failure, falls back to inverse-volatility weighting,
    and if that fails, equal weighting.
    """
    # Guard against invalid inputs
    if cov_matrix is None or not isinstance(cov_matrix, (np.ndarray, list)):
        logger.error("Invalid covariance matrix: not a numpy array.")
        return np.array([])
    cov_matrix = np.asarray(cov_matrix, dtype=np.float64)

    n = cov_matrix.shape[0]
    if n == 0:
        return np.array([])
    if n == 1:
        return np.array([1.0])

    # Extract standard deviations (volatility) for fallback
    diag_vol = np.sqrt(np.maximum(np.diag(cov_matrix), 1e-8))

    # Check for non-finite values in covariance matrix
    if not np.all(np.isfinite(cov_matrix)):
        logger.error("Covariance matrix contains NaN or Inf values.")
        return np.array([])

    # Apply adaptive Tikhonov regularization (epsilon * I) only when ill-conditioned (cond_num > 1e4)
    cond_num = np.linalg.cond(cov_matrix) if n <= 200 else 1.0
    if cond_num > 1e4:
        logger.debug(f"High covariance condition number ({cond_num:.1e}); applying Tikhonov regularization.")
        cov_trace = float(np.trace(cov_matrix)) / max(n, 1)
        adaptive_eps = max(1e-6, 1e-5 * cov_trace) if np.isfinite(cov_trace) and cov_trace > 0 else 1e-6
        reg_cov = cov_matrix + adaptive_eps * np.eye(n)
    else:
        reg_cov = cov_matrix

    weights = None

    try:
        # Formulation B: Log-barrier optimization
        def objective(x):
            x = np.asarray(x)
            if np.any(x <= 1e-12):
                return 1e10
            # 0.5 * x^T * Sigma * x - sum(log(x))
            return 0.5 * float(x.T @ reg_cov @ x) - float(np.sum(np.log(x)))

        # Initial guess: equal weight scaled
        x0 = np.full(n, 1.0 / n)
        bounds = [(1e-8, None) for _ in range(n)]

        res = minimize(objective, x0, method="L-BFGS-B", bounds=bounds)

        if res.success:
            x_opt = res.x
            sum_x = np.sum(x_opt)
            if sum_x > 1e-12:
                weights = x_opt / sum_x
            else:
                logger.warning("Log-barrier optimal weights sum to zero. Trying Formulation A.")

        if weights is None:
            logger.warning(
                "Log-barrier optimization failed: "
                f"{res.message if 'res' in locals() else 'Unknown'}."
                " Trying Formulation A."
            )

            # Formulation A: Direct RC Variance Minimization
            def obj_variance(w):
                w = np.asarray(w)
                rc = w * (cov_matrix @ w)
                rc_diff = rc[:, np.newaxis] - rc[np.newaxis, :]
                return float(np.sum(rc_diff**2))

            w0 = np.full(n, 1.0 / n)
            cons = {"type": "eq", "fun": lambda w: float(np.sum(w) - 1.0)}
            bounds_a = [(0.0, 1.0) for _ in range(n)]

            res_a = minimize(obj_variance, w0, method="SLSQP", bounds=bounds_a, constraints=cons)
            if res_a.success:
                weights = res_a.x
            else:
                logger.error(f"Formulation A SLSQP optimization failed: {res_a.message}.")
    except Exception as e:
        logger.error(f"Exception during risk parity optimization: {e}")

    # Fallback 1: Inverse Volatility Weighting
    if weights is None:
        logger.warning("Attempting fallback to inverse-volatility weighting.")
        try:
            inv_vol = 1.0 / diag_vol
            sum_inv_vol = np.sum(inv_vol)
            if sum_inv_vol > 1e-12 and np.all(np.isfinite(inv_vol)):
                weights = inv_vol / sum_inv_vol
            else:
                weights = None
        except Exception as e:
            logger.error(f"Inverse volatility fallback failed: {e}")
            weights = None

    # Fallback 2: Equal Weighting
    if weights is None:
        logger.warning("Attempting fallback to equal weighting.")
        weights = np.full(n, 1.0 / n)

    # Float precision correction (ensure exact sum to 1.0 and clip to [0, 1])
    weights = np.where(np.isfinite(weights), weights, 1.0 / n)
    weights = np.clip(weights, 0.0, 1.0)
    sum_w = np.sum(weights)
    if sum_w > 1e-12:
        weights /= sum_w
    else:
        weights = np.full(n, 1.0 / n)

    return weights


def calculate_black_litterman_weights(
    cov_matrix: np.ndarray,
    predicted_returns: np.ndarray,
    prior_weights: np.ndarray | None = None,
    risk_aversion: float = 2.5,
    tau: float = 0.05,
    omega_scale: float = 0.1,
    risk_free_rate: float = 0.02,
    meta_convictions: np.ndarray | None = None,
    symbols: Optional[list] = None,
    sectors: Optional[list] = None,
    regime: Optional[Any] = None,
) -> np.ndarray:
    """
    Computes optimal portfolio weights using the Black-Litterman model.
    Prior return: Pi = risk_aversion * cov_matrix @ prior_weights
    Views: Q = predicted_returns, P = Identity
    Uncertainty: Omega = diagonal of cov_matrix * omega_scale
    Updates expected returns and covariance matrix, then solves for tangency portfolio.
    Combines market equilibrium prior returns with strategy views and dynamic meta conviction.
    Supports 2D Regime-Adaptive Bayesian Uncertainty adjustment.
    """
    if cov_matrix is None or predicted_returns is None:
        return np.array([])

    # 2D Regime-Adaptive Bayesian Prior / View Uncertainty adjustment
    regime_str = str(regime).upper() if regime is not None else ""
    if "BEAR" in regime_str or "CRISIS" in regime_str:
        # In crisis/bear, discount views and anchor more to equilibrium prior
        tau = (tau or 0.05) * 0.50
        omega_scale = (omega_scale or 0.1) * 2.0
    elif "BULL" in regime_str:
        # In bull markets, give higher weight to predictive views
        tau = (tau or 0.05) * 1.50
        omega_scale = (omega_scale or 0.1) * 0.70

    tau = max(1e-4, float(tau)) if (tau is not None and np.isfinite(tau)) else 0.05
    omega_scale = max(1e-4, float(omega_scale)) if (omega_scale is not None and np.isfinite(omega_scale)) else 0.1
    risk_free_rate = float(risk_free_rate) if (risk_free_rate is not None and np.isfinite(risk_free_rate)) else 0.02

    n = cov_matrix.shape[0]
    if n == 0:
        return np.array([])
    if n == 1:
        return np.array([1.0])

    try:
        # Check for non-finite values in covariance matrix
        if not np.all(np.isfinite(cov_matrix)):
            raise ValueError("Covariance matrix contains NaN or Inf values.")

        # Prior weights (default to equal weights)
        if prior_weights is None:
            w_eq = np.full(n, 1.0 / n)
        else:
            w_eq = np.asarray(prior_weights)
            if len(w_eq) != n:
                w_eq = np.full(n, 1.0 / n)

        # Prior returns Pi: Pi = delta * Sigma @ w_eq
        horizon_cov = cov_matrix
        Pi = risk_aversion * (horizon_cov @ w_eq)

        # Views Q (predicted returns)
        Q = np.asarray(predicted_returns, dtype=float)
        if len(Q) != n:
            logger.warning("Length of predicted_returns does not match cov_matrix. Using flat returns.")
            Q = np.zeros(n)
        # Normalize units: if Q is in percentage (> 0.5 mean), scale to decimal matching Pi
        if np.nanmean(np.abs(Q)) > 0.50:
            Q = Q / 100.0

        # Uncertainty Omega (diagonal of covariance matrix scaled by dynamic meta conviction)
        if meta_convictions is not None and len(meta_convictions) == n:
            conv_scale = np.clip(np.asarray(meta_convictions, dtype=float), 0.10, 1.50)
            diag_omega = (np.diag(horizon_cov) * omega_scale) / conv_scale
            Omega = np.diag(np.maximum(diag_omega, 1e-8))
        else:
            Omega = np.diag(np.maximum(np.diag(horizon_cov) * omega_scale, 1e-8))

        # Solve for posterior expected returns and covariance matrix
        # A = (tau * Sigma + Omega)
        A = tau * horizon_cov + Omega

        # mu_bl = Pi + tau * Sigma @ (tau * Sigma + Omega)^-1 @ (Q - Pi)
        inv_A_diff = np.linalg.solve(A, Q - Pi)
        mu_bl = Pi + tau * (horizon_cov @ inv_A_diff)

        # Sigma_bl = (1 + tau) * Sigma - tau^2 * Sigma @ (tau * Sigma + Omega)^-1 @ Sigma
        inv_A_Sigma = np.linalg.solve(A, horizon_cov)
        cov_bl = (1.0 + tau) * horizon_cov - (tau ** 2) * (horizon_cov @ inv_A_Sigma)

        # Check for non-finite values in updated values
        if not np.all(np.isfinite(mu_bl)) or not np.all(np.isfinite(cov_bl)):
            raise ValueError("Calculated BL expected returns or covariance contain NaN/Inf.")

        # Convert annualized risk-free rate to daily equivalent if in annual scale (> 0.005)
        rf_daily = (1.0 + risk_free_rate) ** (1.0 / 252.0) - 1.0 if risk_free_rate > 0.005 else risk_free_rate
        all_negative_excess = bool(np.max(mu_bl) <= rf_daily)
        lambda_aversion = max(0.1, float(risk_aversion))

        def objective(w):
            w = np.asarray(w)
            port_ret = float(w @ mu_bl)
            port_var = float(w @ cov_bl @ w)
            port_vol = float(np.sqrt(max(1e-8, port_var)))

            if all_negative_excess:
                # Quadratic utility maximization: max (w^T mu - 0.5 * lambda * w^T Sigma w)
                return - (port_ret - 0.5 * lambda_aversion * port_var)
            else:
                # Maximize Sharpe ratio with smooth quadratic penalty if below r_f
                excess = port_ret - rf_daily
                if excess > 0:
                    return - (excess / port_vol)
                else:
                    return 0.5 * lambda_aversion * port_var - (excess / port_vol)

        w0 = np.full(n, 1.0 / n)
        cons = {"type": "eq", "fun": lambda w: float(np.sum(w) - 1.0)}
        bounds = [(0.0, 1.0) for _ in range(n)]

        res = minimize(objective, w0, method="SLSQP", bounds=bounds, constraints=cons)
        if res.success:
            weights = np.asarray(res.x)
            # Normalize to sum to exactly 1.0 and clip
            weights = np.clip(weights, 0.0, 1.0)
            sum_w = np.sum(weights)
            if sum_w > 0:
                weights = weights / sum_w
                return apply_portfolio_constraints(weights, symbols=symbols, sectors=sectors)

    except Exception as e:
        logger.error(f"Black-Litterman optimization exception: {e}. Falling back to Risk Parity.")
        return calculate_risk_parity_weights(cov_matrix)

    # Fallback to Risk Parity
    return calculate_risk_parity_weights(cov_matrix)


def shrink_covariance_matrix(
    cov_matrix: np.ndarray,
    shrink_factor: Optional[float] = None,
    n_samples: Optional[int] = None
) -> np.ndarray:
    """
    Analytical Ledoit-Wolf optimal covariance shrinkage towards diagonal variance target F = mean(diag(S)) * I.
    Stabilizes covariance matrix, mitigates sample noise, and minimizes Frobenius loss in portfolio optimization.
    """
    if cov_matrix is None or not isinstance(cov_matrix, np.ndarray) or cov_matrix.size == 0:
        return cov_matrix
    n = cov_matrix.shape[0]
    if n <= 1:
        return cov_matrix

    mean_var = float(np.mean(np.diag(cov_matrix)))
    diag_target = mean_var * np.eye(n, dtype=np.float64)

    if shrink_factor is not None:
        delta = float(np.clip(shrink_factor, 0.0, 1.0))
    else:
        # Analytical Frobenius-norm Ledoit-Wolf Shrinkage Intensity Estimation scaled by observation count T
        d2 = float(np.sum((cov_matrix - diag_target) ** 2))
        if d2 < 1e-12:
            return cov_matrix
        t_eff = max(2, int(n_samples)) if n_samples is not None else 60
        asy_var = float(np.sum(cov_matrix ** 2)) / float(t_eff)
        delta = float(np.clip(asy_var / max(d2 + asy_var, 1e-8), 0.0, 1.0))

    shrunk_cov = (1.0 - delta) * cov_matrix + delta * diag_target

    # R11-5 Fix: Enforce strict positive definiteness and maximum condition number clamp <= 1000
    try:
        eigvals, eigvecs = np.linalg.eigh(shrunk_cov)
        min_eigval = float(np.max(eigvals) * 1e-6)
        eigvals = np.maximum(eigvals, max(min_eigval, 1e-8))
        max_cond = 1000.0
        max_eig = float(np.max(eigvals))
        if max_eig / float(np.min(eigvals)) > max_cond:
            eigvals = np.maximum(eigvals, max_eig / max_cond)
        shrunk_cov = (eigvecs * eigvals) @ eigvecs.T
        shrunk_cov = 0.5 * (shrunk_cov + shrunk_cov.T)
    except Exception:
        np.fill_diagonal(shrunk_cov, np.diag(shrunk_cov) + 1e-4)

    return shrunk_cov


def compute_tail_stressed_covariance(
    cov_matrix: np.ndarray,
    returns_matrix: Optional[np.ndarray] = None,
    tail_quantile: float = 0.10,
    stress_blend: float = 0.30
) -> np.ndarray:
    """
    Blends Ledoit-Wolf regularized covariance with Lower-Tail joint covariance matrix
    to protect portfolio during market contagion / drawdown regimes.
    """
    if returns_matrix is None or len(returns_matrix) < 20 or returns_matrix.shape[1] < 2:
        return cov_matrix

    try:
        mkt_returns = np.mean(returns_matrix, axis=1)
        threshold = np.quantile(mkt_returns, tail_quantile)
        tail_mask = mkt_returns <= threshold

        if np.sum(tail_mask) >= 5:
            tail_cov = np.cov(returns_matrix[tail_mask], rowvar=False)
            if tail_cov.shape == cov_matrix.shape and np.all(np.isfinite(tail_cov)):
                k_eff = float(np.clip(stress_blend, 0.0, 0.70))
                stressed = (1.0 - k_eff) * cov_matrix + k_eff * tail_cov
                np.fill_diagonal(stressed, np.diag(stressed) + 1e-6)
                return stressed
    except Exception as e:
        logger.debug(f"Tail-stressed covariance calculation fallback: {e}")

    return cov_matrix


def calculate_hrp_weights(
    cov_matrix: np.ndarray,
    symbols: Optional[list] = None,
    sectors: Optional[list] = None,
    returns_matrix: Optional[np.ndarray] = None,
    tail_stress: bool = True,
    linkage_method: str = "ward",
    use_rmt_denoising: bool = True,
    expected_returns: Optional[np.ndarray] = None,
    alpha_tilt_exponent: float = 1.0,
    prices: Optional[Union[np.ndarray, List[float], Dict[str, float]]] = None,
    total_capital: Optional[float] = None,
    lot_sizes: Optional[Union[np.ndarray, List[int], Dict[str, int], int]] = None
) -> Union[np.ndarray, Dict[str, Any]]:
    """
    Computes Hierarchical Risk Parity (HRP) weights based on Marcos Lopez de Prado's algorithm.
    Enhanced with:
    1. RMT Marchenko-Pastur Spectral Denoising.
    2. Ward / Complete hierarchical clustering (eliminates single-linkage chaining artifacts).
    3. Quasi-diagonalization & Hierarchical Recursive Bisection.
    4. Return-Tilted HRP (R-HRP): Conviction alpha tilting based on risk-adjusted expected returns.
    5. Discrete Lot-Size Sizing: Accounts for minimum order quantities and lot sizes when prices/capital provided.
    """
    if cov_matrix is None or not isinstance(cov_matrix, (np.ndarray, list)):
        logger.error("Invalid covariance matrix for HRP: not a numpy array.")
        return np.array([])
    cov_matrix = np.asarray(cov_matrix, dtype=np.float64)

    n = cov_matrix.shape[0]
    if n == 0:
        return np.array([])
    if n == 1:
        return np.array([1.0])

    try:
        from scipy.cluster.hierarchy import linkage
        from scipy.spatial.distance import squareform

        # Apply Ledoit-Wolf covariance shrinkage
        cov_matrix = shrink_covariance_matrix(cov_matrix, shrink_factor=0.15)

        # Apply RMT Marchenko-Pastur Denoising if sufficient historical sample available
        if use_rmt_denoising and returns_matrix is not None and returns_matrix.shape[0] > n and n >= 3:
            try:
                from src.risk.fx_adjusted_covariance import FXAdjustedCovarianceEngine
                cov_matrix = FXAdjustedCovarianceEngine.denoise_covariance_marchenko_pastur(
                    cov_matrix=cov_matrix,
                    t_obs=returns_matrix.shape[0],
                    n_assets=n
                )
            except Exception as _rmt_e:
                logger.debug(f"[HRP] RMT Denoising fallback: {_rmt_e}")

        # Apply Tail Stress Covariance if returns_matrix is provided
        if tail_stress and returns_matrix is not None:
            cov_matrix = compute_tail_stressed_covariance(cov_matrix, returns_matrix=returns_matrix)

        # Replace non-finite entries safely.
        if not np.all(np.isfinite(cov_matrix)):
            finite_mask = np.isfinite(cov_matrix)
            diag_finite = np.diag(cov_matrix)[np.isfinite(np.diag(cov_matrix))]
            safe_diag_default = float(np.nanmedian(diag_finite)) if len(diag_finite) > 0 and np.nanmedian(diag_finite) > 0 else 0.04  # ~20% vol
            with np.errstate(invalid="ignore", divide="ignore"):
                col_fill = np.where(
                    finite_mask.any(axis=0),
                    np.nanmean(np.where(finite_mask, cov_matrix, np.nan), axis=0),
                    0.0,
                )
            cov_matrix = np.where(finite_mask, cov_matrix, col_fill)
            np.fill_diagonal(cov_matrix, np.nan_to_num(np.diag(cov_matrix), nan=safe_diag_default))

        # Standard deviation & correlation matrix
        vols = np.sqrt(np.abs(np.diag(cov_matrix)))
        diag_vols = vols[np.isfinite(vols) & (vols >= 1e-4)]
        median_vol = float(np.median(diag_vols)) if len(diag_vols) > 0 else 0.20
        vols = np.where((vols < 1e-4) | ~np.isfinite(vols), median_vol, vols)
        outer_vols = np.outer(vols, vols)
        corr = cov_matrix / outer_vols
        corr = np.nan_to_num(corr, nan=0.0)
        corr = np.clip(corr, -1.0, 1.0)
        np.fill_diagonal(corr, 1.0)

        # Distance matrix d_ij = sqrt(0.5 * (1 - corr_ij))
        dist = np.sqrt(np.maximum(0.0, 0.5 * (1.0 - corr)))
        dist = 0.5 * (dist + dist.T)
        np.fill_diagonal(dist, 0.0)

        # Linkage matrix: Ward / Complete avoids seriation chaining
        dist_condensed = squareform(dist, checks=False)
        method_choice = str(linkage_method).lower()
        if method_choice not in ["ward", "complete", "average", "single"]:
            method_choice = "ward"
        try:
            link = linkage(dist_condensed, method=method_choice)
        except Exception:
            link = linkage(dist_condensed, method="average")

        # Quasi-diagonalization
        def get_quasi_diag(link_mat, num_items):
            sort_ix = [int(link_mat[-1, 0]), int(link_mat[-1, 1])]
            num_clusters = link_mat.shape[0]
            for i in range(num_clusters - 1, -1, -1):
                cluster_id = num_items + i
                if cluster_id in sort_ix:
                    idx = sort_ix.index(cluster_id)
                    sort_ix[idx:idx+1] = [int(link_mat[i, 0]), int(link_mat[i, 1])]
            return sort_ix

        quasi_diag = get_quasi_diag(link, n)

        # Recursive Bisection via Queue
        weights = np.ones(n)
        items = [quasi_diag]

        while len(items) > 0:
            new_items = []
            for c in items:
                if len(c) > 1:
                    mid = len(c) // 2
                    c_left = c[:mid]
                    c_right = c[mid:]

                    # Variance of left & right clusters
                    cov_left = cov_matrix[np.ix_(c_left, c_left)]
                    vols_left = np.maximum(np.sqrt(np.maximum(np.diag(cov_left), 1e-12)), 1e-6)
                    inv_vol_left = 1.0 / (vols_left ** 2)
                    w_left = inv_vol_left / max(float(np.sum(inv_vol_left)), 1e-12)
                    var_left = max(float(w_left @ cov_left @ w_left), 1e-16)

                    cov_right = cov_matrix[np.ix_(c_right, c_right)]
                    vols_right = np.maximum(np.sqrt(np.maximum(np.diag(cov_right), 1e-12)), 1e-6)
                    inv_vol_right = 1.0 / (vols_right ** 2)
                    w_right = inv_vol_right / max(float(np.sum(inv_vol_right)), 1e-12)
                    var_right = max(float(w_right @ cov_right @ w_right), 1e-16)

                    # Return-Tilted HRP (R-HRP) conviction scoring
                    if expected_returns is not None and len(expected_returns) == n and alpha_tilt_exponent > 0:
                        er_arr = np.nan_to_num(np.asarray(expected_returns, dtype=float), nan=0.0)
                        mu_left = float(w_left @ er_arr[c_left])
                        mu_right = float(w_right @ er_arr[c_right])
                        sharpe_left = (max(mu_left, -0.02) + 0.02) / np.sqrt(var_left)
                        sharpe_right = (max(mu_right, -0.02) + 0.02) / np.sqrt(var_right)
                        score_left = (max(sharpe_left, 1e-4)) ** alpha_tilt_exponent
                        score_right = (max(sharpe_right, 1e-4)) ** alpha_tilt_exponent
                        tilt_var_left = var_left / max(score_left, 1e-4)
                        tilt_var_right = var_right / max(score_right, 1e-4)
                        tot_tilt_var = tilt_var_left + tilt_var_right
                        ratio = tilt_var_left / tot_tilt_var if tot_tilt_var > 1e-12 else 0.50
                        alpha = float(np.clip(1.0 - ratio if np.isfinite(ratio) else 0.50, 0.01, 0.99))
                    else:
                        tot_var = var_left + var_right
                        if tot_var < 1e-12 or not np.isfinite(tot_var):
                            alpha = 0.50
                        else:
                            ratio = var_left / tot_var
                            alpha = float(np.clip(1.0 - ratio if np.isfinite(ratio) else 0.50, 0.01, 0.99))

                    weights[c_left] *= alpha
                    weights[c_right] *= (1.0 - alpha)

                    new_items.extend([c_left, c_right])
            items = [c for c in new_items if len(c) > 1]

        weights = np.where(np.isfinite(weights), weights, 1.0 / n)
        weights = np.clip(weights, 0.0, 1.0)
        sum_w = float(np.sum(weights))
        if sum_w > 1e-12 and np.isfinite(sum_w):
            weights = weights / sum_w
            constrained_weights = apply_portfolio_constraints(weights, symbols=symbols, sectors=sectors)
            if prices is not None and total_capital is not None and float(total_capital) > 0:
                disc = discretize_weights_to_lot_sizes(
                    constrained_weights,
                    prices=prices,
                    total_capital=float(total_capital),
                    lot_sizes=lot_sizes,
                    max_single_cap=0.20
                )
                return disc['realized_weights']
            return constrained_weights

    except Exception as e:
        logger.error(f"HRP optimization exception: {e}. Falling back to Risk Parity.")
        return calculate_risk_parity_weights(cov_matrix)

    return calculate_risk_parity_weights(cov_matrix)


def calculate_herc_weights(
    cov_matrix: np.ndarray,
    symbols: Optional[list] = None,
    sectors: Optional[list] = None,
    linkage_method: str = "ward",
    max_k: int = 5,
    risk_measure: str = "volatility"
) -> np.ndarray:
    """
    Computes Hierarchical Equal Risk Contribution (HERC) portfolio weights (Raffinot 2017, Lopez de Prado 2020).
    1. Computes Ward/Complete linkage hierarchical clustering on correlation distance matrix.
    2. Determines optimal cluster partition via cophenetic/gap tree slicing.
    3. Allocates Equal Risk Contribution (ERC) across top-level macro clusters:
       w_k = (1 / sigma_k) / sum(1 / sigma_m).
    4. Allocates inverse-variance / risk parity within each cluster.
    """
    if cov_matrix is None or not isinstance(cov_matrix, np.ndarray):
        return np.array([])
    n = cov_matrix.shape[0]
    if n == 0:
        return np.array([])
    if n == 1:
        return np.ones(n)

    try:
        from scipy.cluster.hierarchy import linkage, fcluster
        from scipy.spatial.distance import squareform

        # Ensure valid correlation matrix
        stds = np.sqrt(np.maximum(np.diag(cov_matrix), 1e-8))
        corr = cov_matrix / np.outer(stds, stds)
        corr = np.nan_to_num(corr, nan=0.0)
        corr = np.clip(corr, -1.0, 1.0)
        np.fill_diagonal(corr, 1.0)

        # Distance matrix
        dist = np.sqrt(np.maximum(0.0, 0.5 * (1.0 - corr)))
        dist = 0.5 * (dist + dist.T)
        np.fill_diagonal(dist, 0.0)
        dist_condensed = squareform(dist, checks=False)

        link_method = str(linkage_method).lower()
        if link_method not in ["ward", "complete", "average", "single"]:
            link_method = "ward"
        try:
            link = linkage(dist_condensed, method=link_method)
        except Exception:
            link = linkage(dist_condensed, method="average")

        # Determine optimal number of clusters K (2 <= K <= min(n, max_k))
        k = max(2, min(n, int(max_k)))
        cluster_labels = fcluster(link, t=k, criterion="maxclust")

        # Cluster level variance & weights
        cluster_weights = np.zeros(n)
        cluster_vols = {}

        for c_id in np.unique(cluster_labels):
            idx = np.where(cluster_labels == c_id)[0]
            cov_c = cov_matrix[np.ix_(idx, idx)]
            stds_c = np.maximum(np.sqrt(np.maximum(np.diag(cov_c), 1e-8)), 1e-4)
            inv_var = 1.0 / (stds_c ** 2)
            w_intra = inv_var / max(np.sum(inv_var), 1e-12)
            var_c = float(w_intra.T @ cov_c @ w_intra)
            cluster_vols[c_id] = np.sqrt(max(var_c, 1e-8))

        # Equal Risk Contribution (ERC) across clusters
        inv_cluster_vols = {c_id: 1.0 / max(v, 1e-6) for c_id, v in cluster_vols.items()}
        sum_inv_vols = sum(inv_cluster_vols.values())
        cluster_capital = {c_id: (inv_v / sum_inv_vols) for c_id, inv_v in inv_cluster_vols.items()}

        for c_id in np.unique(cluster_labels):
            idx = np.where(cluster_labels == c_id)[0]
            cov_c = cov_matrix[np.ix_(idx, idx)]
            stds_c = np.maximum(np.sqrt(np.maximum(np.diag(cov_c), 1e-8)), 1e-4)
            inv_var = 1.0 / (stds_c ** 2)
            w_intra = inv_var / max(np.sum(inv_var), 1e-12)
            cluster_weights[idx] = w_intra * cluster_capital[c_id]

        sum_w = np.sum(cluster_weights)
        if sum_w > 1e-12:
            herc_w = cluster_weights / sum_w
            return apply_portfolio_constraints(
                herc_w,
                symbols=symbols,
                sectors=sectors,
                max_single_stock_weight=0.20,
                max_sector_weight=0.35
            )
        return np.full(n, 1.0 / n)
    except Exception as e:
        logger.debug(f"[HERC] Fallback to HRP: {e}")
        return calculate_hrp_weights(cov_matrix, symbols=symbols, sectors=sectors)


def apply_portfolio_constraints(
    weights: np.ndarray,
    symbols: Optional[list] = None,
    sectors: Optional[list] = None,
    max_single_stock_weight: float = 0.20,  # A-1 Fix: aligned with PortfolioAllocator (was 0.10)
    max_sector_weight: float = 0.35,        # A-1 Fix: aligned with PortfolioAllocator (was 0.25)
    factor_loadings: Optional[Any] = None,
    max_factor_exposure: float = 0.35
) -> np.ndarray:
    """
    Applies single stock cap (default 10.0%), sector cap (default 25.0%),
    and optional multi-factor exposure constraints (default |beta| <= 0.35) with iterative redistribution.
    """
    if weights is None or len(weights) == 0:
        return np.array([])

    n = len(weights)
    w = np.copy(weights)

    # 1. Single stock weight capping and Sector weight capping with joint iterative convergence
    cap_weight = max_single_stock_weight if (n * max_single_stock_weight > 1.0) else 1.0

    for _outer in range(5):
        changed = False

        # Single stock weight capping
        for _ in range(10):
            over_mask = w > cap_weight + 1e-8
            if not np.any(over_mask):
                break
            changed = True
            excess = np.sum(w[over_mask] - cap_weight)
            w[over_mask] = cap_weight
            under_mask = ~over_mask
            if np.any(under_mask) and np.sum(w[under_mask]) > 1e-12:
                available_room = np.maximum(0.0, cap_weight - w[under_mask])
                if np.sum(available_room) > 1e-12:
                    alloc = excess * (available_room / np.sum(available_room))
                    w[under_mask] += np.minimum(available_room, alloc)
                else:
                    w[under_mask] += excess * (w[under_mask] / np.sum(w[under_mask]))
            else:
                break

        # Sector weight capping if sectors provided
        if sectors and len(sectors) == n:
            import pandas as pd
            sec_series = pd.Series(sectors)
            num_unique_sectors = max(1, len(sec_series.unique()))
            eff_max_sec = max_sector_weight if (num_unique_sectors * max_sector_weight > 1.0) else 1.0
            for _ in range(10):
                df_w = pd.DataFrame({'weight': w, 'sector': sec_series})
                sec_sums = df_w.groupby('sector')['weight'].sum()
                over_sectors = sec_sums[sec_sums > eff_max_sec + 1e-6]
                if over_sectors.empty:
                    break
                changed = True
                excess_total = 0.0
                for sec, total_s in over_sectors.items():
                    scale = eff_max_sec / total_s
                    sec_mask = (sec_series == sec).values
                    excess_total += float(np.sum(w[sec_mask] * (1.0 - scale)))
                    w[sec_mask] *= scale

                under_mask = ~sec_series.isin(over_sectors.index).values
                if np.any(under_mask) and np.sum(w[under_mask]) > 1e-12:
                    available_room = np.maximum(0.0, cap_weight - w[under_mask])
                    if np.sum(available_room) > 1e-12:
                        alloc = excess_total * (available_room / np.sum(available_room))
                        w[under_mask] += np.minimum(available_room, alloc)
                    else:
                        w[under_mask] += excess_total * (w[under_mask] / np.sum(w[under_mask]))
                else:
                    break

        if not changed:
            break

    # 3. Factor exposure capping (e.g. Beta, Size, Value <= max_factor_exposure)
    if factor_loadings is not None:
        try:
            import pandas as pd
            if isinstance(factor_loadings, pd.DataFrame) and not factor_loadings.empty:
                f_df = factor_loadings.reindex(symbols).fillna(0.0) if symbols else factor_loadings.fillna(0.0)
                f_mat = f_df.values
                if f_mat.shape[0] == n:
                    for _ in range(5):
                        exposures = w @ f_mat
                        breaches = np.abs(exposures) > max_factor_exposure
                        if not np.any(breaches):
                            break
                        for f_idx in np.where(breaches)[0]:
                            target_scale = max_factor_exposure / max(1e-6, abs(exposures[f_idx]))
                            # V7-12: Use damped reduction (1 + target_scale)/2 to avoid over-suppressing multi-factor loading stocks
                            damped_scale = (1.0 + target_scale) * 0.50
                            f_col = f_mat[:, f_idx]
                            high_loading = np.abs(f_col) > np.median(np.abs(f_col))
                            w[high_loading] *= damped_scale
                        sum_w = np.sum(w)
                        if sum_w > 1e-12:
                            w /= sum_w
        except Exception as _fe:
            logger.debug(f"Factor constraint application skipped: {_fe}")

    w = np.nan_to_num(w, nan=0.0, posinf=0.0, neginf=0.0)
    w = np.clip(w, 0.0, cap_weight)
    sum_w = float(np.sum(w))
    if sum_w > 1e-12:
        w /= sum_w
    else:
        w = np.full(n, 1.0 / n) if n > 0 else w

    for _ in range(5):
        over = w > cap_weight + 1e-6
        if not np.any(over):
            break
        excess = np.sum(w[over] - cap_weight)
        w[over] = cap_weight
        under = ~over
        if np.any(under) and np.sum(w[under]) > 1e-12:
            room = np.maximum(0.0, cap_weight - w[under])
            if np.sum(room) > 1e-12:
                w[under] += excess * (room / np.sum(room))
            else:
                break
        else:
            break

    return w


def discretize_weights_to_lot_sizes(
    weights: Union[np.ndarray, List[float], Dict[str, float]],
    prices: Union[np.ndarray, List[float], Dict[str, float]],
    total_capital: float,
    lot_sizes: Optional[Union[np.ndarray, List[int], Dict[str, int], int]] = None,
    min_order_quantities: Optional[Union[np.ndarray, List[int], Dict[str, int], int]] = None,
    max_single_cap: float = 0.20,
    allow_greedy_remainder: bool = True
) -> Dict[str, Any]:
    """
    Converts continuous portfolio weights into executable discrete lot-sized integer shares.

    Parameters
    ----------
    weights : array-like or dict of symbol -> weight
    prices : array-like or dict of symbol -> latest close price
    total_capital : float, total cash/portfolio capital available
    lot_sizes : array-like or dict or int, lot size per asset (e.g. 1 for US/KRX, 100 for JP/VN)
    min_order_quantities : array-like or dict or int, minimum order shares per asset
    max_single_cap : float, maximum allowed weight per single asset (e.g. 0.20)
    allow_greedy_remainder : bool, whether to allocate residual cash to top remaining lots

    Returns
    -------
    Dict with:
      - 'shares': np.ndarray of discrete integer shares
      - 'amounts': np.ndarray of discrete capital allocated per asset (shares * price)
      - 'realized_weights': np.ndarray of actual weights (amounts / total_capital)
      - 'lot_sizes': np.ndarray of lot size applied per asset
      - 'min_order_quantities': np.ndarray of min order qty per asset
      - 'unallocated_cash': float, leftover cash
      - 'total_allocated': float, total cash allocated
      - 'is_executable': np.ndarray of bool, whether asset received >= min_order_quantity
    """
    if isinstance(weights, dict):
        symbols = list(weights.keys())
        w_arr = np.array([float(weights[s]) for s in symbols], dtype=float)
        if isinstance(prices, dict):
            p_arr = np.array([float(prices.get(s, 0.0) or 0.0) for s in symbols], dtype=float)
        else:
            p_arr = np.asarray(prices, dtype=float)
        if isinstance(lot_sizes, dict):
            l_arr = np.array([int(lot_sizes.get(s, 1) or 1) for s in symbols], dtype=int)
        elif isinstance(lot_sizes, (int, float)):
            l_arr = np.full(len(symbols), max(1, int(lot_sizes)), dtype=int)
        elif lot_sizes is not None:
            l_arr = np.asarray(lot_sizes, dtype=int)
        else:
            l_arr = np.ones(len(symbols), dtype=int)

        if isinstance(min_order_quantities, dict):
            m_arr = np.array([int(min_order_quantities.get(s, l_arr[i]) or l_arr[i]) for i, s in enumerate(symbols)], dtype=int)
        elif isinstance(min_order_quantities, (int, float)):
            m_arr = np.full(len(symbols), max(1, int(min_order_quantities)), dtype=int)
        elif min_order_quantities is not None:
            m_arr = np.asarray(min_order_quantities, dtype=int)
        else:
            m_arr = np.copy(l_arr)
    else:
        w_arr = np.asarray(weights, dtype=float)
        p_arr = np.asarray(prices, dtype=float) if prices is not None else np.zeros_like(w_arr)
        n = len(w_arr)
        if isinstance(lot_sizes, (int, float)):
            l_arr = np.full(n, max(1, int(lot_sizes)), dtype=int)
        elif lot_sizes is not None:
            l_arr = np.asarray(lot_sizes, dtype=int)
        else:
            l_arr = np.ones(n, dtype=int)

        if isinstance(min_order_quantities, (int, float)):
            m_arr = np.full(n, max(1, int(min_order_quantities)), dtype=int)
        elif min_order_quantities is not None:
            m_arr = np.asarray(min_order_quantities, dtype=int)
        else:
            m_arr = np.copy(l_arr)

    n = len(w_arr)
    if n == 0 or total_capital <= 0:
        return {
            'shares': np.array([], dtype=int),
            'amounts': np.array([]),
            'realized_weights': np.array([]),
            'lot_sizes': np.array([], dtype=int),
            'min_order_quantities': np.array([], dtype=int),
            'unallocated_cash': float(total_capital),
            'total_allocated': 0.0,
            'is_executable': np.array([], dtype=bool)
        }

    # Ensure clean price and lot arrays
    p_arr = np.where(np.isfinite(p_arr) & (p_arr > 0), p_arr, 0.0)
    l_arr = np.maximum(1, np.where(np.isfinite(l_arr), l_arr, 1))
    m_arr = np.maximum(l_arr, np.where(np.isfinite(m_arr), m_arr, l_arr))
    w_arr = np.nan_to_num(w_arr, nan=0.0)
    w_arr = np.clip(w_arr, 0.0, max_single_cap)

    # 1. Compute initial raw and lot-sized share quantities
    target_capital = w_arr * float(total_capital)
    raw_shares = np.where(p_arr > 0, target_capital / p_arr, 0.0)
    shares = np.where(p_arr > 0, (raw_shares // l_arr) * l_arr, 0).astype(int)

    # 2. Check minimum order feasibility & rounding up for high-conviction borderline allocations
    max_single_amount = float(total_capital * max_single_cap * 1.15)
    for i in range(n):
        if p_arr[i] <= 0:
            shares[i] = 0
            continue
        min_order_cost = float(m_arr[i] * p_arr[i])
        if shares[i] < m_arr[i]:
            # If target capital covers at least 50% of the minimum lot cost and does not exceed cap
            if target_capital[i] >= 0.50 * min_order_cost and min_order_cost <= max_single_amount:
                shares[i] = int(m_arr[i])
            else:
                shares[i] = 0

    # 3. Budget enforcement: ensure sum(shares * price) <= total_capital
    allocated_amounts = shares.astype(float) * p_arr
    total_allocated = float(np.sum(allocated_amounts))

    if total_allocated > total_capital:
        # Scale down or prune assets starting from lowest relative allocation / lowest weight
        sort_indices = np.argsort(w_arr)  # Smallest weights first
        for idx in sort_indices:
            if total_allocated <= total_capital:
                break
            if shares[idx] > 0 and p_arr[idx] > 0:
                cost_i = float(shares[idx] * p_arr[idx])
                shares[idx] = 0
                total_allocated -= cost_i

    # 4. Composite remainder lot allocation: distribute residual cash to top assets with highest composite conviction (V7-13)
    target_budget_sum = float(np.sum(w_arr) * total_capital)
    max_budget = min(total_capital, target_budget_sum) if target_budget_sum < (total_capital * 0.95) else total_capital
    remaining_cash = float(max_budget - np.sum(shares.astype(float) * p_arr))
    if allow_greedy_remainder and remaining_cash > 0:
        lot_costs = l_arr.astype(float) * p_arr
        valid_mask = (p_arr > 0) & (lot_costs > 0) & (shares >= m_arr)
        if np.any(valid_mask):
            # Composite priority: 50% fractional lot remainder + 50% target weight conviction
            remainders = np.where(valid_mask, ((raw_shares - shares.astype(float)) / l_arr.astype(float) * 0.50) + (w_arr * 0.50), -1.0)
            priority_order = np.argsort(-remainders)  # Highest remainder first

            for p_idx in priority_order:
                if remaining_cash <= 0:
                    break
                if not valid_mask[p_idx]:
                    continue
                lot_cost = float(lot_costs[p_idx])
                pos_cap_i = min(float(total_capital * max_single_cap), float(target_capital[p_idx] + lot_cost))
                curr_pos_val = float(shares[p_idx] * p_arr[p_idx])

                while remaining_cash >= lot_cost and (curr_pos_val + lot_cost) <= pos_cap_i:
                    shares[p_idx] += int(l_arr[p_idx])
                    remaining_cash -= lot_cost
                    curr_pos_val += lot_cost

    final_amounts = shares.astype(float) * p_arr
    final_total_alloc = float(np.sum(final_amounts))
    realized_weights = final_amounts / max(float(total_capital), 1e-6)
    is_executable = (shares >= m_arr) & (shares > 0)

    return {
        'shares': shares,
        'amounts': final_amounts,
        'realized_weights': realized_weights,
        'lot_sizes': l_arr,
        'min_order_quantities': m_arr,
        'unallocated_cash': float(total_capital - final_total_alloc),
        'total_allocated': final_total_alloc,
        'is_executable': is_executable
    }



