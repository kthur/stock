import logging

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
    if cov_matrix is None or not isinstance(cov_matrix, np.ndarray):
        logger.error("Invalid covariance matrix: not a numpy array.")
        return np.array([])

    n = cov_matrix.shape[0]
    if n == 0:
        return np.array([])
    if n == 1:
        return np.array([1.0])

    # Extract standard deviations (volatility) for fallback
    diag_vol = np.sqrt(np.diag(cov_matrix))
    diag_vol = np.where(np.isnan(diag_vol) | (diag_vol < 1e-8), 1e-8, diag_vol)

    weights = None

    try:
        # Check for non-finite values in covariance matrix
        if not np.all(np.isfinite(cov_matrix)):
            raise ValueError("Covariance matrix contains NaN or Inf values.")

        # Formulation B: Log-barrier optimization
        def objective(x):
            x = np.asarray(x)
            if np.any(x <= 1e-12):
                return 1e10
            # 0.5 * x^T * Sigma * x - sum(log(x))
            return 0.5 * float(x.T @ cov_matrix @ x) - float(np.sum(np.log(x)))

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
    prior_weights: np.ndarray = None,
    risk_aversion: float = 2.5,
    tau: float = 0.05,
    omega_scale: float = 0.1,
    risk_free_rate: float = 0.02,
) -> np.ndarray:
    """
    Computes optimal portfolio weights using the Black-Litterman model.
    Prior return: Pi = risk_aversion * cov_matrix @ prior_weights
    Views: Q = predicted_returns, P = Identity
    Uncertainty: Omega = diagonal of cov_matrix * omega_scale
    Updates expected returns and covariance matrix, then solves for tangency portfolio.
    """
    # Guard against invalid inputs
    if cov_matrix is None or not isinstance(cov_matrix, np.ndarray):
        logger.error("Invalid covariance matrix for Black-Litterman: not a numpy array.")
        return np.array([])

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

        # Prior returns Pi
        Pi = risk_aversion * (cov_matrix @ w_eq)

        # Views Q (predicted returns)
        Q = np.asarray(predicted_returns)
        if len(Q) != n:
            logger.warning("Length of predicted_returns does not match cov_matrix. Using flat returns.")
            Q = np.zeros(n)

        # Uncertainty Omega (diagonal of covariance matrix scaled)
        Omega = np.diag(np.maximum(np.diag(cov_matrix) * omega_scale, 1e-8))

        # Solve for posterior expected returns and covariance matrix
        # A = (tau * Sigma + Omega)
        A = tau * cov_matrix + Omega
        
        # mu_bl = Pi + tau * Sigma @ (tau * Sigma + Omega)^-1 @ (Q - Pi)
        inv_A_diff = np.linalg.solve(A, Q - Pi)
        mu_bl = Pi + tau * (cov_matrix @ inv_A_diff)

        # Sigma_bl = (1 + tau) * Sigma - tau^2 * Sigma @ (tau * Sigma + Omega)^-1 @ Sigma
        inv_A_Sigma = np.linalg.solve(A, cov_matrix)
        cov_bl = (1.0 + tau) * cov_matrix - (tau ** 2) * (cov_matrix @ inv_A_Sigma)

        # Check for non-finite values in updated values
        if not np.all(np.isfinite(mu_bl)) or not np.all(np.isfinite(cov_bl)):
            raise ValueError("Calculated BL expected returns or covariance contain NaN/Inf.")

        # Optimize weights (maximize Sharpe ratio)
        def objective(w):
            w = np.asarray(w)
            port_ret = float(w @ mu_bl)
            port_vol = float(np.sqrt(w @ cov_bl @ w))
            if port_vol < 1e-8:
                return 0.0
            # Maximize Sharpe ratio: minimize negative Sharpe ratio
            return - (port_ret - risk_free_rate) / port_vol

        w0 = np.full(n, 1.0 / n)
        cons = {"type": "eq", "fun": lambda w: float(np.sum(w) - 1.0)}
        bounds = [(0.0, 1.0) for _ in range(n)]

        res = minimize(objective, w0, method="SLSQP", bounds=bounds, constraints=cons)
        if res.success:
            weights = res.x
            # Normalize to sum to exactly 1.0 and clip
            weights = np.clip(weights, 0.0, 1.0)
            sum_w = np.sum(weights)
            if sum_w > 1e-12:
                weights /= sum_w
                return weights

        logger.warning(f"Black-Litterman optimization failed: {res.message}. Falling back to Risk Parity.")
    except Exception as e:
        logger.error(f"Exception during Black-Litterman optimization: {e}. Falling back to Risk Parity.")

    # Fallback to Risk Parity
    return calculate_risk_parity_weights(cov_matrix)
