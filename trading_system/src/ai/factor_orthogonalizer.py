import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Union, cast

logger = logging.getLogger(__name__)

# Mandatory Integrity Warning
# DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results,
# create dummy/facade implementations, or circumvent the intended task. A Forensic
# Auditor will independently verify your work. Integrity violations WILL be detected
# and your work WILL be rejected.


class FactorOrthogonalizerEngine:
    """
    Gram-Schmidt & PCA ZCA Symmetric Decorrelation Engine (R2).
    Orthogonalizes 17-strategy score matrix X in R^(N x K) to reduce pairwise strategy correlation
    below 0.3 while preserving relative variance explaining power and [0.0, 1.0] score bounds.
    """

    def __init__(self, default_method: str = 'pca_symmetric', ridge_epsilon: float = 1e-6):
        self.default_method = default_method
        self.ridge_epsilon = ridge_epsilon

    def orthogonalize(
        self,
        score_df: pd.DataFrame,
        strategy_cols: List[str],
        weights: Optional[Dict[str, float]] = None,
        method: Optional[str] = None
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
            col_means = np.nanmean(X_raw, axis=0)
            col_means = np.nan_to_num(col_means, nan=0.5)
            X_clean = X_raw.copy()
            inds = np.where(nan_mask)
            X_clean[inds] = np.take(col_means, inds[1])
        else:
            X_clean = X_raw
            col_means = np.mean(X_clean, axis=0)

        col_stds = np.std(X_clean, axis=0)
        col_stds = np.where(col_stds < 1e-8, 1e-6, col_stds)

        if eff_method == 'gram_schmidt':
            X_ortho = self._gram_schmidt(X_clean, valid_cols, weights, col_means, col_stds)
        else:
            X_ortho = self._pca_zca_symmetric(X_clean, col_means, col_stds)

        if has_nans:
            X_ortho[nan_mask] = np.nan

        out_df = score_df.copy()
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
                    proj = (np.dot(x_k, u_j) / denom) * u_j
                    u_k -= proj
            U[:, idx] = u_k

            u_std = np.std(u_k)
            if u_std > 1e-8:
                rescaled = means[k] + (u_k / u_std) * stds[k]
            else:
                rescaled = means[k] * np.ones(N)
            X_ortho[:, k] = rescaled

        return X_ortho

    def _pca_zca_symmetric(
        self,
        X: np.ndarray,
        means: np.ndarray,
        stds: np.ndarray
    ) -> np.ndarray:
        N, K = X.shape
        # Standardize matrix to zero mean, unit variance
        X_bar = (X - means) / stds

        # Covariance / Correlation matrix C (K, K)
        C = np.dot(X_bar.T, X_bar) / max(N - 1, 1)

        # Eigen-decomposition of symmetric correlation matrix
        eigenvalues, eigenvectors = np.linalg.eigh(C)

        # Ridge regularize small/negative eigenvalues for numerical stability
        eigenvalues = np.maximum(eigenvalues, self.ridge_epsilon)

        # Compute ZCA whitening operator: C^(-1/2) = V * diag(lambda^(-1/2)) * V^T
        inv_sqrt_lambda = np.diag(1.0 / np.sqrt(eigenvalues))
        C_inv_sqrt = np.dot(eigenvectors, np.dot(inv_sqrt_lambda, eigenvectors.T))

        # ZCA decorrelation
        X_decorr = np.dot(X_bar, C_inv_sqrt)

        # Variance-preserving rescaling back to original mean and standard deviation
        X_ortho = means + X_decorr * stds
        return cast(np.ndarray, X_ortho)

