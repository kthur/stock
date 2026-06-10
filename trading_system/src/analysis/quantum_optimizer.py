import logging
from typing import Dict, List

import numpy as np

logger = logging.getLogger(__name__)


class QuantumPortfolioOptimizer:
    """포트폴리오 최적화 - Mean-Variance / Risk-Parity"""

    def __init__(self, risk_free_rate: float = 0.03):
        self.risk_free_rate = risk_free_rate

    def optimize_allocation(
        self,
        symbols: List[str],
        current_weights: Dict[str, float],
        expected_returns: Dict[str, float] | None = None,
        cov_matrix: np.ndarray | None = None,
    ) -> Dict[str, float]:
        n = len(symbols)
        if n == 0:
            return current_weights
        if n == 1:
            return {symbols[0]: 1.0}
        if expected_returns is None:
            expected_returns = {s: 0.0 for s in symbols}
        if cov_matrix is None:
            cov_matrix = np.eye(n) * 0.04

        er = np.array([expected_returns.get(s, 0.0) for s in symbols])
        cov = np.asarray(cov_matrix, dtype=float)

        if np.linalg.cond(cov) > 1e12:
            cov += np.eye(n) * 0.001

        try:
            inv_cov = np.linalg.inv(cov)
        except np.linalg.LinAlgError:
            inv_cov = np.linalg.inv(cov + np.eye(n) * 0.01)

        ones = np.ones(n)
        A = ones @ inv_cov @ er
        B = er @ inv_cov @ er
        C = ones @ inv_cov @ ones
        D = B * C - A * A

        if abs(D) < 1e-10:
            raw_weights = np.full(n, 1.0 / n)
        else:
            mu_target = max(er.mean(), 0.0)
            lam = (C * mu_target - A) / D if D != 0 else 0.0
            gamma = (B - A * mu_target) / D if D != 0 else 1.0 / C
            raw_weights = inv_cov @ (lam * er + gamma * ones)

        raw_weights = np.maximum(raw_weights, 0.0)
        total = raw_weights.sum()
        if total > 0:
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
        n = len(symbols)
        if n <= 1:
            return {s: 1.0 for s in symbols}
        if cov_matrix is None:
            cov_matrix = np.eye(n) * 0.04

        cov = np.asarray(cov_matrix, dtype=float)
        if np.linalg.cond(cov) > 1e12:
            cov += np.eye(n) * 0.001

        sigma = np.sqrt(np.diag(cov))
        sigma = np.where(sigma < 1e-8, 1e-8, sigma)

        raw_weights = 1.0 / sigma
        total = raw_weights.sum()
        if total > 0:
            raw_weights /= total
        else:
            raw_weights = np.full(n, 1.0 / n)

        optimized = {sym: round(float(w), 4) for sym, w in zip(symbols, raw_weights)}
        logger.info(f"Risk-parity weights: {optimized}")
        return optimized

    def compute_covariance(self, historical_returns: Dict[str, List[float]]) -> np.ndarray:
        symbols = list(historical_returns.keys())
        n = len(symbols)
        min_len = min(len(v) for v in historical_returns.values())
        if min_len < 2:
            return np.eye(n) * 0.04
        arr = np.array([historical_returns[s][:min_len] for s in symbols])
        return np.cov(arr)
