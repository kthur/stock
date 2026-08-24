import logging
from typing import Dict, List

import numpy as np

logger = logging.getLogger(__name__)


class QuantumPortfolioOptimizer:
    """포트폴리오 최적화 - Mean-Variance / Risk-Parity"""

    def __init__(self, risk_free_rate: float = 0.03):
        self.risk_free_rate = float(risk_free_rate) if (risk_free_rate is not None and np.isfinite(risk_free_rate)) else 0.03

    def optimize_allocation(
        self,
        symbols: List[str],
        current_weights: Dict[str, float],
        expected_returns: Dict[str, float] | None = None,
        cov_matrix: np.ndarray | None = None,
    ) -> Dict[str, float]:
        if symbols is None or len(symbols) == 0:
            return current_weights if current_weights is not None else {}
        n = len(symbols)
        if n == 1:
            return {symbols[0]: 1.0}
        if expected_returns is None:
            expected_returns = {s: 0.0 for s in symbols}
        if cov_matrix is None:
            cov_matrix = np.eye(n) * 0.04

        er = np.array([float(expected_returns.get(s, 0.0) or 0.0) for s in symbols])
        er = np.nan_to_num(er, nan=0.0, posinf=0.0, neginf=0.0)
        cov = np.asarray(cov_matrix, dtype=float)
        cov = np.nan_to_num(cov, nan=0.04, posinf=0.04, neginf=0.04)

        try:
            if np.linalg.cond(cov) > 1e12:
                cov += np.eye(n) * 0.001
        except Exception:
            cov += np.eye(n) * 0.001

        try:
            inv_cov = np.linalg.inv(cov)
        except Exception:
            inv_cov = np.linalg.inv(cov + np.eye(n) * 0.01)

        ones = np.ones(n)
        A = float(ones @ inv_cov @ er)
        B = float(er @ inv_cov @ er)
        C = float(ones @ inv_cov @ ones)
        D = B * C - A * A

        if abs(D) < 1e-10 or not np.isfinite(D) or abs(C) < 1e-10 or not np.isfinite(C):
            raw_weights = np.full(n, 1.0 / n)
        else:
            mu_target = max(float(er.mean()), 0.0)
            lam = (C * mu_target - A) / D if (D != 0 and np.isfinite((C * mu_target - A) / D)) else 0.0
            gamma = (B - A * mu_target) / D if (D != 0 and np.isfinite((B - A * mu_target) / D)) else 1.0 / C
            raw_weights = inv_cov @ (lam * er + gamma * ones)

        raw_weights = np.nan_to_num(raw_weights, nan=0.0, posinf=0.0, neginf=0.0)
        raw_weights = np.maximum(raw_weights, 0.0)
        total = float(raw_weights.sum())
        if total > 1e-12 and np.isfinite(total):
            raw_weights /= total
        else:
            raw_weights = np.full(n, 1.0 / n)

        optimized = {sym: round(float(w), 4) for sym, w in zip(symbols, raw_weights)}
        logger.info(f"Optimized weights: {optimized}")
        return optimized

    def risk_parity_allocation(
        self,
        symbols: List[str],
        cov_matrix: np.ndarray | None = None,
    ) -> Dict[str, float]:
        if symbols is None or len(symbols) == 0:
            return {}
        n = len(symbols)
        if n == 1:
            return {symbols[0]: 1.0}
        if cov_matrix is None:
            cov_matrix = np.eye(n) * 0.04

        cov = np.asarray(cov_matrix, dtype=float)
        cov = np.nan_to_num(cov, nan=0.04, posinf=0.04, neginf=0.04)
        try:
            if np.linalg.cond(cov) > 1e12:
                cov += np.eye(n) * 0.001
        except Exception:
            cov += np.eye(n) * 0.001

        sigma = np.sqrt(np.diag(cov))
        sigma = np.nan_to_num(sigma, nan=0.20, posinf=0.20, neginf=0.20)
        sigma = np.where(sigma < 1e-8, 1e-8, sigma)

        raw_weights = 1.0 / sigma
        total = float(raw_weights.sum())
        if total > 1e-12:
            raw_weights /= total
        else:
            raw_weights = np.full(n, 1.0 / n)

        optimized = {sym: round(float(w), 4) for sym, w in zip(symbols, raw_weights)}
        logger.info(f"Risk-parity weights: {optimized}")
        return optimized

    def compute_covariance(self, historical_returns: Dict[str, List[float]]) -> np.ndarray:
        if not historical_returns:
            return np.array([[]])
        symbols = list(historical_returns.keys())
        n = len(symbols)
        if n == 0:
            return np.array([[]])
        lengths = [len(v) for v in historical_returns.values() if v is not None]
        if not lengths or min(lengths) < 2:
            return np.eye(n) * 0.04
        min_len = min(lengths)
        arr = np.array([historical_returns[s][:min_len] for s in symbols], dtype=float)
        cov = np.cov(arr)
        if cov.ndim == 0:
            cov = np.array([[float(cov)]])
        cov = np.nan_to_num(cov, nan=0.04, posinf=0.04, neginf=0.04)
        return cov
