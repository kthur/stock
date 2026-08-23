import logging
from typing import Optional, Any


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
) -> np.ndarray:
    """
    Computes optimal portfolio weights using the Black-Litterman model.
    Prior return: Pi = risk_aversion * cov_matrix @ prior_weights
    Views: Q = predicted_returns, P = Identity
    Uncertainty: Omega = diagonal of cov_matrix * omega_scale
    Updates expected returns and covariance matrix, then solves for tangency portfolio.
    Combines market equilibrium prior returns with strategy views and dynamic meta conviction.
    """
    if cov_matrix is None or predicted_returns is None:
        return np.array([])

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
            diag_omega = (np.diag(cov_matrix) * omega_scale) / conv_scale
            Omega = np.diag(np.maximum(diag_omega, 1e-8))
        else:
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

        # Problem-level regime formulation: Determine globally whether excess return is achievable
        lambda_aversion = 2.5
        all_negative_excess = bool(np.max(mu_bl) <= risk_free_rate)

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
                excess = port_ret - risk_free_rate
                return - excess / port_vol if excess > 0 else (0.5 * lambda_aversion * port_var - excess * 10.0)

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


def shrink_covariance_matrix(cov_matrix: np.ndarray, shrink_factor: Optional[float] = None) -> np.ndarray:
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
        # Analytical Frobenius-norm Ledoit-Wolf Shrinkage Intensity Estimation
        d2 = float(np.sum((cov_matrix - diag_target) ** 2))
        if d2 < 1e-12:
            return cov_matrix
        asy_var = float(np.sum(np.diag(cov_matrix) ** 2)) / float(max(n, 1))
        delta = float(np.clip(asy_var / (d2 + asy_var), 0.05, 0.40))

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
    use_rmt_denoising: bool = True
) -> np.ndarray:
    """
    Computes Hierarchical Risk Parity (HRP) weights based on Marcos Lopez de Prado's algorithm.
    Enhanced with:
    1. RMT Marchenko-Pastur Spectral Denoising.
    2. Ward / Complete hierarchical clustering (eliminates single-linkage chaining artifacts).
    3. Quasi-diagonalization & Hierarchical Recursive Bisection.
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

                # Variance of left & right clusters (R9-1 Fix: High precision without artificial 1e-8 floor distortion)
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

                # Allocation factor alpha
                tot_var = var_left + var_right
                if tot_var < 1e-12:
                    alpha = 0.50
                else:
                    alpha = float(np.clip(1.0 - (var_left / tot_var), 0.01, 0.99))

                weights[c_left] *= alpha
                weights[c_right] *= (1.0 - alpha)

        weights = np.clip(weights, 0.0, 1.0)
        sum_w = np.sum(weights)
        if sum_w > 1e-12:
            weights = weights / sum_w
            return apply_portfolio_constraints(weights, symbols=symbols, sectors=sectors if 'sectors' in locals() else None)

    except Exception as e:
        logger.error(f"HRP optimization exception: {e}. Falling back to Risk Parity.")
        return calculate_risk_parity_weights(cov_matrix)

    return calculate_risk_parity_weights(cov_matrix)


def calculate_herc_weights(
    cov_matrix: np.ndarray,
    symbols: Optional[list] = None,
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
                max_single_stock_weight=0.20,
                max_sector_weight=0.35
            )
        return np.full(n, 1.0 / n)
    except Exception as e:
        logger.debug(f"[HERC] Fallback to HRP: {e}")
        return calculate_hrp_weights(cov_matrix, symbols=symbols)


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
                            f_col = f_mat[:, f_idx]
                            high_loading = np.abs(f_col) > np.median(np.abs(f_col))
                            w[high_loading] *= target_scale
                        sum_w = np.sum(w)
                        if sum_w > 1e-12:
                            w /= sum_w
        except Exception as _fe:
            logger.debug(f"Factor constraint application skipped: {_fe}")

    w = np.nan_to_num(w, nan=0.0, posinf=0.0, neginf=0.0)
    w = np.clip(w, 0.0, 1.0)
    sum_w = float(np.sum(w))
    if sum_w > 1e-12:
        w /= sum_w
    else:
        w = np.full(n, 1.0 / n) if n > 0 else w

    return w


