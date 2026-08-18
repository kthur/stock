import logging
from typing import Optional


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
    prior_weights: np.ndarray | None = None,
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

    risk_aversion = float(risk_aversion) if (risk_aversion is not None and np.isfinite(risk_aversion)) else 2.5
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

        # Optimize weights (maximize Sharpe ratio or Quadratic Utility if excess return is negative)
        eq_ret = float(np.mean(mu_bl))
        is_negative_excess = (eq_ret <= risk_free_rate)
        lambda_aversion = 2.5

        def objective(w):
            w = np.asarray(w)
            port_ret = float(w @ mu_bl)
            port_var = float(w @ cov_bl @ w)
            port_vol = float(np.sqrt(max(1e-8, port_var)))
            
            if is_negative_excess:
                # Quadratic utility maximization: max (w^T mu - 0.5 * lambda * w^T Sigma w)
                return - (port_ret - 0.5 * lambda_aversion * port_var)
            else:
                # Maximize Sharpe ratio: minimize negative Sharpe ratio
                return - (port_ret - risk_free_rate) / port_vol

        w0 = np.full(n, 1.0 / n)
        cons = {"type": "eq", "fun": lambda w: float(np.sum(w) - 1.0)}
        bounds = [(0.0, 1.0) for _ in range(n)]

        res = minimize(objective, w0, method="SLSQP", bounds=bounds, constraints=cons)
        if res.success:
            weights = np.asarray(res.x)
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


def shrink_covariance_matrix(cov_matrix: np.ndarray, shrink_factor: float = 0.15) -> np.ndarray:
    """Ledoit-Wolf style covariance shrinkage towards diagonal variance target.
    Stabilizes covariance matrix and mitigates sample noise in portfolio optimization.
    """
    if cov_matrix is None or not isinstance(cov_matrix, np.ndarray) or cov_matrix.size == 0:
        return cov_matrix
    n = cov_matrix.shape[0]
    if n <= 1:
        return cov_matrix
    diag_target = np.diag(np.diag(cov_matrix))
    shrunk_cov = (1.0 - shrink_factor) * cov_matrix + shrink_factor * diag_target
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
    tail_stress: bool = True
) -> np.ndarray:
    """
    Computes Hierarchical Risk Parity (HRP) weights based on Marcos Lopez de Prado's algorithm.
    1. Distance matrix computation from correlation matrix (with optional Tail-Stressed Covariance).
    2. Hierarchical clustering (single linkage).
    3. Quasi-diagonalization & Recursive Bisection.
    """
    if cov_matrix is None or not isinstance(cov_matrix, np.ndarray):
        logger.error("Invalid covariance matrix for HRP: not a numpy array.")
        return np.array([])

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

        # Apply Tail Stress Covariance if returns_matrix is provided
        if tail_stress and returns_matrix is not None:
            cov_matrix = compute_tail_stressed_covariance(cov_matrix, returns_matrix=returns_matrix)

        # Replace non-finite entries safely.
        # Avoid filling diagonal with a tiny constant (e.g. 1e-4) which makes missing data look "risk-free",
        # causing HRP inverse-variance to over-allocate to missing assets.
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
        np.fill_diagonal(dist, 0.0)

        # Linkage matrix
        dist_condensed = squareform(dist, checks=False)
        link = linkage(dist_condensed, method='single')

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

        # Recursive Bisection
        weights = np.ones(n)
        cluster_items = [quasi_diag]

        while len(cluster_items) > 0:
            cluster_items = [
                c[i:j]
                for c in cluster_items
                for i, j in ((0, len(c) // 2), (len(c) // 2, len(c)))
                if len(c) > 1
            ]
            for i in range(0, len(cluster_items), 2):
                c_left = cluster_items[i]
                c_right = cluster_items[i + 1]

                # Variance of left & right clusters
                cov_left = cov_matrix[np.ix_(c_left, c_left)]
                vols_left = np.maximum(np.sqrt(np.diag(cov_left)), 1e-8)
                inv_vol_left = 1.0 / (vols_left ** 2)
                w_left = inv_vol_left / np.sum(inv_vol_left)
                var_left = float(w_left @ cov_left @ w_left)

                cov_right = cov_matrix[np.ix_(c_right, c_right)]
                vols_right = np.maximum(np.sqrt(np.diag(cov_right)), 1e-8)
                inv_vol_right = 1.0 / (vols_right ** 2)
                w_right = inv_vol_right / np.sum(inv_vol_right)
                var_right = float(w_right @ cov_right @ w_right)

                # Allocation factor alpha
                alpha = 1.0 - var_left / (var_left + var_right + 1e-12)

                weights[c_left] *= alpha
                weights[c_right] *= (1.0 - alpha)

        weights = np.clip(weights, 0.0, 1.0)
        sum_w = np.sum(weights)
        if sum_w > 1e-12:
            weights = weights / sum_w
            return apply_portfolio_constraints(weights, symbols=symbols, sectors=sectors if 'sectors' in locals() else None)

    except Exception as e:
        logger.error(f"HRP optimization exception: {e}. Falling back to Risk Parity.")

    fallback_w = calculate_risk_parity_weights(cov_matrix)
    return apply_portfolio_constraints(fallback_w, symbols=symbols if 'symbols' in locals() else [])


def apply_portfolio_constraints(
    weights: np.ndarray,
    symbols: Optional[list] = None,
    sectors: Optional[list] = None,
    max_single_stock_weight: float = 0.10,
    max_sector_weight: float = 0.25
) -> np.ndarray:
    """
    Applies single stock cap (default 10.0%) and sector cap (default 25.0%) constraints
    with iterative redistribution.
    """
    if weights is None or len(weights) == 0:
        return np.array([])

    n = len(weights)
    w = np.copy(weights)

    # 1. Single stock weight capping (max 10.0%, at least 1.0/n for small portfolio sizes)
    cap_weight = max(max_single_stock_weight, 1.0 / n) if n > 0 else max_single_stock_weight
    for _ in range(10):
        over_mask = w > cap_weight
        if not np.any(over_mask):
            break
        excess = np.sum(w[over_mask] - cap_weight)
        w[over_mask] = cap_weight
        under_mask = ~over_mask
        if np.any(under_mask) and np.sum(w[under_mask]) > 1e-12:
            w[under_mask] += excess * (w[under_mask] / np.sum(w[under_mask]))
        else:
            break

    # 2. Sector weight capping (max 25.0%) if sectors provided
    if sectors and len(sectors) == n:
        import pandas as pd
        sec_series = pd.Series(sectors)
        for _ in range(10):
            df_w = pd.DataFrame({'weight': w, 'sector': sec_series})
            sec_sums = df_w.groupby('sector')['weight'].sum()
            over_sectors = sec_sums[sec_sums > max_sector_weight + 1e-6]
            if over_sectors.empty:
                break
            
            excess_total = 0.0
            for sec, total_s in over_sectors.items():
                scale = max_sector_weight / total_s
                sec_mask = (sec_series == sec).values
                excess_total += float(np.sum(w[sec_mask] * (1.0 - scale)))
                w[sec_mask] *= scale

            under_mask = ~sec_series.isin(over_sectors.index).values
            if np.any(under_mask) and np.sum(w[under_mask]) > 1e-12:
                w[under_mask] += excess_total * (w[under_mask] / np.sum(w[under_mask]))
            else:
                break

    w = np.nan_to_num(w, nan=0.0, posinf=0.0, neginf=0.0)
    w = np.clip(w, 0.0, 1.0)
    sum_w = float(np.sum(w))
    if sum_w > 1e-12:
        w /= sum_w
    else:
        w = np.full(n, 1.0 / n) if n > 0 else w

    return w


