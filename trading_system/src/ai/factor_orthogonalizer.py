import functools
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, cast

logger = logging.getLogger(__name__)

# Mandatory Integrity Warning
# DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results,
# create dummy/facade implementations, or circumvent the intended task. A Forensic
# Auditor will independently verify your work. Integrity violations WILL be detected
# and your work WILL be rejected.


def safe_matrix_precision_guard(func):
    """Decorator ensuring that matrix calculations are performed in float64 precision."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        new_args = [
            a.astype(np.float64) if isinstance(a, np.ndarray) and a.dtype == np.float32 else a
            for a in args
        ]
        new_kwargs = {
            k: v.astype(np.float64) if isinstance(v, np.ndarray) and v.dtype == np.float32 else v
            for k, v in kwargs.items()
        }
        res = func(*new_args, **new_kwargs)
        return res
    return wrapper


class FactorOrthogonalizerEngine:
    """
    Gram-Schmidt & Equalized Spectral Residual Whitening (ESRW) Decorrelation Engine (R2).
    Orthogonalizes multi-strategy score matrix X in R^(N x K) to reduce pairwise strategy correlation
    while preserving directional alpha and [0.0, 1.0] score bounds without sign-inversion distortion.
    """

    def __init__(self, default_method: str = 'pca_symmetric', ridge_epsilon: float = 1e-6, shrinkage_alpha: float = 0.01):
        self.default_method = default_method
        self.ridge_epsilon = ridge_epsilon
        self.shrinkage_alpha = shrinkage_alpha

    def orthogonalize(
        self,
        score_df: pd.DataFrame,
        strategy_cols: List[str],
        weights: Optional[Dict[str, float]] = None,
        method: Optional[str] = None,
        scaling_method: Optional[str] = None
    ) -> pd.DataFrame:
        eff_method = method or self.default_method
        valid_cols = [c for c in strategy_cols if c in score_df.columns]
        if len(valid_cols) < 2 or len(score_df) < 3:
            return score_df.copy()

        # Extract numeric matrix X (N, K) efficiently
        X_raw = score_df[valid_cols].to_numpy(dtype=np.float64, copy=False)
        N, K = X_raw.shape

        nan_mask = np.isnan(X_raw)
        has_nans = nan_mask.any()
        if has_nans:
            # Handle potential completely empty columns safely
            col_means = np.zeros(K, dtype=np.float64)
            for j in range(K):
                col_j = X_raw[:, j]
                valid_j = col_j[~np.isnan(col_j)]
                col_means[j] = float(np.mean(valid_j)) if len(valid_j) > 0 else 0.5
            col_means = np.nan_to_num(col_means, nan=0.5)
            X_clean = X_raw.copy()
            inds = np.where(nan_mask)
            X_clean[inds] = np.take(col_means, inds[1])
        else:
            X_clean = X_raw
            col_means = np.mean(X_clean, axis=0)

        col_stds = np.std(X_clean, axis=0)
        col_stds = np.where(np.isnan(col_stds) | (col_stds < 1e-8), 1e-6, col_stds)

        use_dispersion = (
            scaling_method is None or
            scaling_method == 'dispersion' or
            'dispersion' in str(eff_method).lower() or
            scaling_method == 'sigmoid'
        ) and (scaling_method != 'rank')

        if str(eff_method).startswith('gram_schmidt'):
            X_ortho = self._gram_schmidt(X_clean, valid_cols, weights, col_means, col_stds)
        else:
            X_ortho = self._pca_zca_symmetric(X_clean, col_means, col_stds)

        if has_nans:
            X_ortho[nan_mask] = np.nan

        out_df = score_df.copy()
        if use_dispersion:
            # Sigmoid-Tanh Dispersion-Preserving Conviction Scaling
            # Preserves relative distance, fat tails, and non-uniform conviction without flat rank collapse
            X_centered = (X_ortho - col_means) / col_stds
            X_disp = col_means + col_stds * np.tanh(X_centered)
            out_df[valid_cols] = np.clip(X_disp, 0.0, 1.0)
        elif len(out_df) >= 5:
            ranks = pd.DataFrame(X_ortho, index=out_df.index, columns=valid_cols).rank(pct=True)
            out_df[valid_cols] = ranks.values
        else:
            out_df[valid_cols] = np.clip(X_ortho, 0.0, 1.0)
        return out_df

    def _gram_schmidt(
        self,
        X: np.ndarray,
        cols: List[str],
        weights: Optional[Dict[str, float]],
        means: np.ndarray,
        stds: np.ndarray
    ) -> np.ndarray:
        N, K = X.shape
        if weights:
            order = sorted(range(K), key=lambda i: weights.get(cols[i], 0.0), reverse=True)
        else:
            order = list(range(K))

        X_centered = X - means
        U = np.zeros_like(X_centered)
        X_ortho = np.zeros_like(X)

        for idx, k in enumerate(order):
            x_k = X_centered[:, k]
            u_k = x_k.copy()
            for prev_idx in range(idx):
                u_j = U[:, prev_idx]
                denom = np.dot(u_j, u_j)
                if denom > 1e-8:
                    proj = (np.dot(u_k, u_j) / denom) * u_j  # Sequential Orthogonal Projection (MGS)
                    u_k -= proj
            U[:, idx] = u_k

            u_std = np.std(u_k)
            if u_std > 1e-8:
                rescaled = means[k] + (u_k / u_std) * stds[k]
            else:
                rescaled = means[k] * np.ones(N)
            X_ortho[:, k] = rescaled

        return X_ortho

    @safe_matrix_precision_guard
    def _esrw_whitening(self, X_bar: np.ndarray, C_shrunk: np.ndarray) -> np.ndarray:
        """
        Equalized Spectral Residual Whitening (ESRW).
        Soft-shrinks collinear noise eigenvalues towards mean eigenvalue lambda=1.0,
        preserving leading shared momentum/value alpha while eliminating sign-inversion distortion.
        """
        N, K = X_bar.shape
        C_sym = (C_shrunk + C_shrunk.T) * 0.5
        eigenvalues, eigenvectors = np.linalg.eigh(C_sym.astype(np.float64))

        mean_eig = float(np.mean(eigenvalues)) if len(eigenvalues) > 0 else 1.0
        shrinkage = 1.0 / (1.0 + np.exp((eigenvalues - 1.0) / 0.30))
        lambdas_reg = (1.0 - shrinkage) * eigenvalues + shrinkage * mean_eig + self.ridge_epsilon

        inv_sqrt_lambda = np.diag(1.0 / np.sqrt(np.maximum(lambdas_reg, 1e-6)))
        W_esrw = np.dot(eigenvectors, np.dot(inv_sqrt_lambda, eigenvectors.T))

        diag_signs = np.sign(np.diag(W_esrw))
        diag_signs[diag_signs == 0] = 1.0
        W_esrw = W_esrw * diag_signs[:, np.newaxis]

        return np.asarray(np.dot(X_bar, W_esrw), dtype=np.float64)

    @safe_matrix_precision_guard
    def _pca_zca_symmetric(
        self,
        X: np.ndarray,
        means: np.ndarray,
        stds: np.ndarray
    ) -> np.ndarray:
        N, K = X.shape
        # Standardize matrix to zero mean, unit variance
        X_bar = (X - means) / stds

        # Compute sample covariance matrix
        C = np.dot(X_bar.T, X_bar) / max(N - 1, 1)

        # Dynamic Ledoit-Wolf Shrinkage or fallback
        C_shrunk = self._compute_ledoit_wolf_covariance(X_bar, C)
        C_sym = (C_shrunk + C_shrunk.T) * 0.5

        # Eigen-decomposition of symmetric correlation matrix
        eigenvalues, eigenvectors = np.linalg.eigh(C_sym.astype(np.float64))

        # Continuous Ridge Regularization & Floor to prevent null-space amplification (N < K)
        mean_eig = float(np.mean(eigenvalues)) if len(eigenvalues) > 0 else 1.0
        ridge_floor = max(0.01 * mean_eig, self.ridge_epsilon)
        lambdas_reg = np.maximum(eigenvalues, 0.0) + ridge_floor

        # Compute ZCA whitening operator: C^(-1/2) = V * diag(lambda^(-1/2)) * V^T
        inv_sqrt_lambda = np.diag(1.0 / np.sqrt(lambdas_reg))
        C_inv_sqrt = np.dot(eigenvectors, np.dot(inv_sqrt_lambda, eigenvectors.T))

        # Positive diagonal alignment constraint to ensure positive factor self-affinity
        diag_signs = np.sign(np.diag(C_inv_sqrt))
        diag_signs[diag_signs == 0] = 1.0
        C_inv_sqrt = C_inv_sqrt * diag_signs[:, np.newaxis]

        # ZCA decorrelation
        X_decorr = np.dot(X_bar, C_inv_sqrt)

        # Variance-preserving rescaling back to original mean and standard deviation
        X_ortho = means + X_decorr * stds
        return cast(np.ndarray, X_ortho)

    def _compute_ledoit_wolf_covariance(self, X_bar: np.ndarray, C_sample: np.ndarray) -> np.ndarray:
        N, K = X_bar.shape
        try:
            from sklearn.covariance import LedoitWolf
            lw = LedoitWolf(store_precision=False, assume_centered=True)
            return cast(np.ndarray, lw.fit(X_bar).covariance_)
        except Exception:
            pass

        mu = np.trace(C_sample) / max(K, 1)
        target = mu * np.eye(K)
        d2 = float(np.sum((C_sample - target) ** 2))
        if d2 < 1e-12:
            return cast(np.ndarray, C_sample + self.ridge_epsilon * np.eye(K))

        delta = self.shrinkage_alpha if self.shrinkage_alpha > 0 else 0.01
        C_shrunk = (1.0 - delta) * C_sample + delta * target
        return cast(np.ndarray, C_shrunk + self.ridge_epsilon * np.eye(K))


class CrossSectionalFactorNeutralizer:
    """
    Pre-Ensemble Cross-Sectional Factor Neutralizer.
    Orthogonalizes raw alpha factor scores across symbols against Market Beta, Size,
    Volatility, and Sector risk exposures via Weighted Generalized Least Squares (GLS).
    """

    def __init__(
        self,
        risk_factors: Optional[List[str]] = None,
        mad_threshold: float = 3.0,
        ridge_epsilon: float = 1e-6
    ):
        self.risk_factors = risk_factors or ["beta", "log_mcap", "volatility_60d"]
        self.mad_threshold = float(mad_threshold)
        self.ridge_epsilon = float(ridge_epsilon)

    def winsorize_mad(self, series: pd.Series) -> pd.Series:
        """Applies Median Absolute Deviation (MAD) winsorization to eliminate fat-tail outlier distortions."""
        valid = series.dropna()
        if len(valid) < 5:
            return series
        med = float(valid.median())
        mad = float((valid - med).abs().median() * 1.4826)
        if mad < 1e-8:
            return series
        lower = med - self.mad_threshold * mad
        upper = med + self.mad_threshold * mad
        return series.clip(lower=lower, upper=upper)

    def neutralize_cross_section(
        self,
        scores: pd.Series,
        factor_loadings: Optional[pd.DataFrame] = None,
        sector_series: Optional[pd.Series] = None,
        weights: Optional[pd.Series] = None
    ) -> pd.Series:
        """
        Neutralizes a single strategy score series across the symbol cross-section.
        """
        if scores is None or len(scores) < 4:
            return scores

        # Winsorize raw factor inputs
        clean_scores = self.winsorize_mad(scores)
        valid_idx = clean_scores.dropna().index
        if len(valid_idx) < 4:
            return scores

        y = clean_scores.loc[valid_idx].to_numpy(dtype=np.float64)
        N = len(valid_idx)

        # Build Design Matrix B
        cols_to_concat = [pd.Series(1.0, index=valid_idx, name="intercept")]
        if factor_loadings is not None and not factor_loadings.empty:
            avail_factors = [f for f in self.risk_factors if f in factor_loadings.columns]
            if avail_factors:
                f_df = factor_loadings.reindex(index=valid_idx, columns=avail_factors).fillna(0.0)
                # Standardize factor loadings safely
                f_std = ((f_df - f_df.mean()) / (f_df.std().fillna(1.0).replace(0.0, 1.0) + 1e-6)).fillna(0.0)
                cols_to_concat.append(f_std)

        if sector_series is not None and len(sector_series) > 0:
            sec_aligned = sector_series.reindex(valid_idx).fillna("UNKNOWN")
            if sec_aligned.nunique() > 1:
                dummies = pd.get_dummies(sec_aligned, drop_first=True, dtype=float)
                cols_to_concat.append(dummies)

        B_df = pd.concat(cols_to_concat, axis=1)
        B = B_df.to_numpy(dtype=np.float64)
        K_cols = B.shape[1]

        # Weights matrix W (e.g. sqrt(MarketCap) or Identity)
        if weights is not None and len(weights) > 0:
            w_aligned = weights.reindex(valid_idx).fillna(1.0).to_numpy(dtype=np.float64)
            w_aligned = np.clip(w_aligned, 1e-4, np.inf)
            W_diag = np.sqrt(w_aligned)
            W_diag /= (np.mean(W_diag) + 1e-8)
        else:
            W_diag = np.ones(N, dtype=np.float64)

        # WLS Projection: (B_weighted^T B_weighted + eps I)^(-1) B_weighted^T y_weighted
        B_weighted = B * W_diag[:, np.newaxis]
        y_weighted = y * W_diag
        BtWB = np.dot(B_weighted.T, B_weighted) + self.ridge_epsilon * np.eye(K_cols)

        try:
            beta_hat = np.linalg.solve(BtWB, np.dot(B_weighted.T, y_weighted))
        except np.linalg.LinAlgError:
            beta_hat = np.dot(np.linalg.pinv(BtWB), np.dot(B_weighted.T, y_weighted))

        fitted = np.dot(B, beta_hat)
        residuals = y - fitted

        res_std = np.std(residuals)
        if res_std > 1e-8:
            z_scores = residuals / res_std
            # Map back to [0.0, 1.0] using Sigmoid dispersion preservation
            pure_scores = 1.0 / (1.0 + np.exp(-z_scores))
        else:
            pure_scores = np.full(N, 0.5, dtype=np.float64)

        result = scores.copy()
        result.loc[valid_idx] = pure_scores
        return result

    def neutralize_dataframe(
        self,
        score_df: pd.DataFrame,
        strategy_cols: List[str],
        factor_loadings: Optional[pd.DataFrame] = None,
        sector_col: Optional[str] = None,
        weights_col: Optional[str] = None
    ) -> pd.DataFrame:
        """Neutralizes all specified strategy columns in a DataFrame."""
        if score_df is None or score_df.empty:
            return score_df

        out_df = score_df.copy()
        sector_s = out_df[sector_col] if (sector_col and sector_col in out_df.columns) else None
        weight_s = out_df[weights_col] if (weights_col and weights_col in out_df.columns) else None

        for col in strategy_cols:
            if col in out_df.columns:
                out_df[col] = self.neutralize_cross_section(
                    scores=out_df[col],
                    factor_loadings=factor_loadings,
                    sector_series=sector_s,
                    weights=weight_s
                )
        return out_df



