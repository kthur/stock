"""
spectral_covariance.py — Ledoit-Péché Optimal Non-Linear Spectral Covariance Denoising

Implements non-linear asymptotic eigenvalue shrinkage for high-dimensional returns (N > T)
using Random Matrix Theory and Stieltjes transform inversion to eliminate Marchenko-Pastur
bulk noise while preserving pure factor variance.
"""

from __future__ import annotations

import logging
import numpy as np
import pandas as pd
from typing import Dict, Union

logger = logging.getLogger(__name__)


class NonLinearSpectralCovarianceEngine:
    """
    Random Matrix Theory Non-Linear Spectral Shrinkage Covariance Denoising.
    """

    def __init__(self, eps: float = 1e-4):
        self.eps = eps

    def denoise_covariance_matrix(
        self,
        returns_matrix: Union[pd.DataFrame, np.ndarray]
    ) -> np.ndarray:
        """
        Computes the asymptotically optimal non-linear shrunk covariance matrix:
        Sigma_clean = U * diag(d_1^*, ..., d_N^*) * U^T
        where d_i^* = lambda_i / |1 - c - c * z * m(z)|^2
        """
        if isinstance(returns_matrix, pd.DataFrame):
            X = returns_matrix.dropna().values.astype(np.float64)
        else:
            X = np.nan_to_num(np.asarray(returns_matrix, dtype=np.float64), nan=0.0)

        T, N = X.shape
        if T < 5 or N < 2:
            return np.asarray(np.cov(X, rowvar=False) if N >= 2 else np.eye(max(1, N)), dtype=np.float64)

        # Demean returns
        X_centered = X - np.mean(X, axis=0)
        # Sample covariance matrix S
        S = np.dot(X_centered.T, X_centered) / float(T)
        c = float(N) / float(T)

        # Eigenvalue Decomposition
        try:
            evals, evecs = np.linalg.eigh(S)
        except Exception:
            return np.asarray(S + 1e-4 * np.eye(N), dtype=np.float64)

        # Ensure sorted in ascending order
        idx_sort = np.argsort(evals)
        evals = np.maximum(evals[idx_sort], self.eps)
        evecs = evecs[:, idx_sort]

        # Ledoit-Péché non-linear shrinkage via discrete Stieltjes kernel transform
        # m(lambda_i + i*eta) = (1/N) * sum_j 1 / (lambda_j - (lambda_i + i*eta))
        eta = np.power(float(N), -0.35) * np.std(evals) if np.std(evals) > 0 else 1e-3
        d_shrunk = np.zeros(N, dtype=np.float64)

        for i in range(N):
            lam_i = evals[i]
            z = lam_i + 1j * eta

            # Stieltjes transform m(z)
            m_z = np.mean(1.0 / (evals - z))
            denom = np.abs(1.0 - c - c * z * m_z) ** 2

            if denom > 1e-6:
                d_val = float(lam_i / denom)
            else:
                d_val = float(lam_i)

            d_shrunk[i] = max(self.eps, d_val)

        # Trace preservation: sum(d_shrunk) = sum(evals)
        trace_ratio = np.sum(evals) / max(np.sum(d_shrunk), 1e-6)
        d_shrunk *= trace_ratio

        # Reconstruct clean covariance matrix
        Sigma_clean = evecs @ np.diag(d_shrunk) @ evecs.T
        # Symmetrize
        Sigma_clean = 0.5 * (Sigma_clean + Sigma_clean.T)
        return np.asarray(Sigma_clean, dtype=np.float64)

    def compute_spectral_shrunk_weights(
        self,
        expected_returns: pd.Series,
        returns_df: pd.DataFrame,
        risk_aversion: float = 2.5
    ) -> Dict[str, float]:
        """
        Computes minimum-variance / mean-variance optimal weights using non-linear spectral clean covariance.
        """
        symbols = list(expected_returns.index)
        if len(symbols) <= 1:
            return {symbols[0]: 1.0} if symbols else {}

        df_rets = returns_df[symbols].dropna()
        Sigma_clean = self.denoise_covariance_matrix(df_rets)

        N = len(symbols)
        mu = np.nan_to_num(expected_returns.values.astype(np.float64), nan=0.0)

        try:
            inv_sigma = np.linalg.pinv(Sigma_clean + 1e-4 * np.eye(N))
            raw_w = (1.0 / max(risk_aversion, 0.1)) * np.dot(inv_sigma, mu)
        except Exception:
            raw_w = np.ones(N) / N

        raw_w = np.maximum(0.0, raw_w)
        tot_w = np.sum(raw_w) or 1.0
        norm_w = raw_w / tot_w

        return {s: float(w) for s, w in zip(symbols, norm_w)}
