# Technical Implementation Specification & Unit Test Design: Quad-Factor Neutral QP Portfolio Risk Optimizer (Milestone 2 - R2)

## Executive Summary

This document details the exact technical implementation specification and unit test design for **Milestone 2 (R2): Quad-Factor Neutral Quadratic Programming (QP) Portfolio Risk Optimizer**.

The `QuadFactorOptimizer` provides institutional-grade portfolio weight optimization by minimizing portfolio risk (variance) while maximizing expected return, penalizing portfolio turnover, and enforcing strict long-only asset bounds, sector concentration caps, and 4-factor exposure neutrality bounds (Market Beta, Size/Log Market Cap, Volatility, and 12M-1M Momentum).

---

## 1. System Architecture & File Layout

The module follows the dual-layer architecture of the trading system, featuring a primary implementation module in `src/strategy/quad_factor_optimizer.py`, a bridge module in `trading_system/src/strategy/quad_factor_optimizer.py`, integration into `PortfolioOptimizer` in `trading_system/src/risk/portfolio_optimizer.py`, and complete unit tests in `trading_system/tests/test_quad_factor_optimizer.py` (bridged to `tests/test_quad_factor_optimizer.py`).

```
d:\Finance\code\stock\
├── src/
│   └── strategy/
│       └── quad_factor_optimizer.py         [Primary Implementation Class: QuadFactorOptimizer]
├── trading_system/
│   ├── src/
│   │   ├── strategy/
│   │   │   └── quad_factor_optimizer.py     [Bridge file importing QuadFactorOptimizer]
│   │   └── risk/
│   │       └── portfolio_optimizer.py       [Enhanced with optimize_quad_factor_portfolio]
│   └── tests/
│       └── test_quad_factor_optimizer.py    [Unit Test Suite]
└── tests/
    └── test_quad_factor_optimizer.py        [Bridge test file importing trading_system test]
```

---

## 2. Mathematical Formulation

### 2.1 Objective Function

The optimizer solves the following Quadratic Programming (QP) problem:

$$\min_{w \in \mathbb{R}^N} f(w) = \frac{1}{2} w^T \Sigma w - \lambda \mu^T w + \gamma \|w - w_0\|_2^2$$

Where:
- $w = [w_1, w_2, \dots, w_N]^T \in \mathbb{R}^N$: Vector of portfolio weights for $N$ assets.
- $\Sigma \in \mathbb{R}^{N \times N}$: Estimated covariance matrix (shrunk/Ledoit-Wolf covariance).
- $\mu \in \mathbb{R}^N$: Expected net returns vector (from 18-strategy ensemble model).
- $\lambda \ge 0$: Risk aversion coefficient balancing return vs. portfolio variance (default: $1.0$).
- $w_0 \in \mathbb{R}^N$: Initial/current portfolio weights vector (for turnover control; defaults to equal weights $1/N$ if not provided).
- $\gamma \ge 0$: Regularization / Turnover penalty parameter ($\|w - w_0\|_2^2 = \sum_{i=1}^N (w_i - w_{0,i})^2$; default: $0.01$).

#### Gradient and Hessian (Analytical Form):
$$\nabla f(w) = \Sigma w - \lambda \mu + 2 \gamma (w - w_0)$$
$$\nabla^2 f(w) = \Sigma + 2 \gamma I_N$$

Since $\Sigma$ is symmetric positive semi-definite and $\gamma \ge 0$, $\nabla^2 f(w)$ is strictly positive definite, guaranteeing a strictly convex optimization domain with a unique global minimum.

---

### 2.2 Constraints Specification

#### Constraint 1: Weight Sum Equality (Gross Exposure Budget)
$$\sum_{i=1}^N w_i = 1.0 \quad \left(\text{or } \mathbf{1}^T w = W_{\text{target}} = 1.0\right)$$

#### Constraint 2: Long-Only Non-Negativity and Single Asset Caps
$$0.0 \le w_i \le w_{\text{max}} \quad \forall i=1, \dots, N \quad (\text{default } w_{\text{max}} = 0.10 \text{ i.e. 10\%})$$

#### Constraint 3: Quad-Factor Neutrality Bounds
Prior to optimization, each raw factor $F^{(k)} \in \mathbb{R}^N$ ($k \in \{\text{beta}, \text{size}, \text{volatility}, \text{momentum}\}$) across all $N$ assets is standardized to zero-mean and unit-variance Z-scores:

$$\tilde{F}_i^{(k)} = \frac{F_i^{(k)} - \bar{F}^{(k)}}{\sigma(F^{(k)})}$$

The portfolio's normalized factor exposure is constrained within $[-\epsilon_k, \epsilon_k]$:

$$-\epsilon_k \le (\tilde{F}^{(k)})^T w \le \epsilon_k \quad \forall k \in \{\text{beta}, \text{size}, \text{volatility}, \text{momentum}\}$$

- **Market Beta Factor** ($\beta$): $|\beta^T w| \le \epsilon_{\text{beta}}$ (default $\epsilon_{\text{beta}} = 0.05$).
- **Size Factor** ($S$, Log Market Cap): $|S^T w| \le \epsilon_{\text{size}}$ (default $\epsilon_{\text{size}} = 0.05$).
- **Volatility Factor** ($V$, 20-day Historical Volatility): $|V^T w| \le \epsilon_{\text{vol}}$ (default $\epsilon_{\text{vol}} = 0.05$).
- **Momentum Factor** ($M$, 12M-1M Momentum): $|M^T w| \le \epsilon_{\text{mom}}$ (default $\epsilon_{\text{mom}} = 0.05$).

#### Constraint 4: Sector Concentration Caps
For each unique sector $S_k$ in sector mapping dictionary $\text{sector\_map}$:

$$\sum_{i \in \text{Sector}_k} w_i \le \text{MaxSectorWeight} \quad (\text{default } 0.25 \text{ i.e. 25\%})$$

---

## 3. Detailed Class Specification (`QuadFactorOptimizer`)

### 3.1 Class Header & Initialization

```python
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
```

---

### 3.2 Main Optimization Method (`optimize`)

```python
    def optimize(
        self,
        expected_returns: pd.Series,
        cov_matrix: pd.DataFrame,
        factor_df: pd.DataFrame,
        sector_map: Dict[str, str],
        w_initial: Optional[Dict[str, float]] = None,
        max_weight: Optional[float] = None,
        max_sector_weight: Optional[float] = None,
        factor_tolerances: Optional[Dict[str, float]] = None
    ) -> Dict[str, float]:
        """
        Solves the Quad-Factor Neutral QP Portfolio Risk Optimization problem.

        Parameters:
            expected_returns: Expected returns per asset (Series indexed by symbol).
            cov_matrix: Assets covariance matrix (DataFrame indexed/columns by symbol).
            factor_df: Factor matrix (DataFrame indexed by symbol, columns: 'beta', 'size', 'volatility', 'momentum').
            sector_map: Dict mapping symbol -> sector string.
            w_initial: Optional initial portfolio weights for turnover penalty (defaults to equal weights).
            max_weight: Maximum single-asset weight bound (default: 0.10).
            max_sector_weight: Maximum sector weight bound (default: 0.25).
            factor_tolerances: Dict of tolerance limits per factor (e.g. {'beta': 0.05, ...}).

        Returns:
            Dict[str, float]: Optimized asset weight vector mapping symbol -> weight.
        """
        # 1. Input Alignment & Validation
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
        Sigma = cov_matrix.loc[symbols, symbols].values.astype(np.float64)
        
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
        tol_dict = factor_tolerances or {}
        factors = ['beta', 'size', 'volatility', 'momentum']
        standardized_factors = {}
        eps_vec = []
        
        for f in factors:
            eps = tol_dict.get(f, self.default_factor_tolerance)
            eps_vec.append(eps)
            if f in factor_df.columns:
                raw_f = factor_df.loc[symbols, f].values.astype(np.float64)
                std_f = np.nan_to_num(raw_f, nan=0.0)
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
            # Tier 1: Relax factor tolerances by 2x (e.g. 0.05 -> 0.10)
            relaxed_tols = {f: tol_dict.get(f, self.default_factor_tolerance) * 2.0 for f in factors}
            weights = self._solve_scipy_slsqp(
                symbols, mu, Sigma, standardized_factors, sector_map,
                w0, max_w, max_sec_w, relaxed_tols
            )

        if weights is None:
            logger.warning("Tier 1 Fallback failed. Triggering Tier 2 Fallback (Mean-Variance / Sector Capped MVO).")
            # Tier 2: Mean-Variance Optimization without Factor Bounds
            weights = self._solve_scipy_slsqp(
                symbols, mu, Sigma, {}, sector_map,
                w0, max_w, max_sec_w, {}
            )

        if weights is None:
            logger.warning("Tier 2 Fallback failed. Triggering Tier 3 Fallback (Equal Weight with Sector Caps).")
            # Tier 3: Equal Weight clamped to max_w & max_sec_w
            weights = self._fallback_equal_weight(symbols, sector_map, max_w, max_sec_w)

        # Final Normalization & Cleaning
        weights = np.clip(weights, 0.0, max_w)
        w_sum = np.sum(weights)
        if w_sum > 1e-8:
            weights = weights / w_sum

        return {sym: float(w) for sym, w in zip(symbols, weights)}
```

---

### 3.3 SciPy SLSQP Solver Implementation (`_solve_scipy_slsqp`)

```python
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
        constraints.append({'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0})

        # 2. Factor Neutrality Bounds (-eps <= f^T * w <= eps)
        for fname, fvec in factors.items():
            eps = tolerances.get(fname, self.default_factor_tolerance)
            # Upper: eps - f^T * w >= 0
            constraints.append({'type': 'ineq', 'fun': lambda w, f=fvec, e=eps: e - np.dot(f, w)})
            # Lower: f^T * w + eps >= 0
            constraints.append({'type': 'ineq', 'fun': lambda w, f=fvec, e=eps: np.dot(f, w) + e})

        # 3. Sector Concentration Caps (sum_{i in Sector_k}(w_i) <= max_sec_w)
        sectors = set(sector_map.get(s, "Unknown") for s in symbols)
        for sec in sectors:
            indices = [i for i, s in enumerate(symbols) if sector_map.get(s, "Unknown") == sec]
            if indices:
                constraints.append({'type': 'ineq', 'fun': lambda w, idx=indices, m=max_sec_w: m - np.sum(w[idx])})

        # 4. Long-Only Bounds (0 <= w_i <= max_w)
        bounds = tuple((0.0, max_w) for _ in range(n_assets))

        init_w = np.ones(n_assets) / n_assets

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
            if res.success and not np.isnan(res.x).any():
                return res.x
            else:
                logger.debug(f"SciPy SLSQP failed to converge: {res.message}")
                return None
        except Exception as e:
            logger.debug(f"SciPy SLSQP solver exception: {e}")
            return None
```

---

### 3.4 CVXPY Solver Implementation (`_solve_cvxpy`)

```python
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

        # Objective Function
        risk_term = 0.5 * cp.quad_form(w, Sigma)
        return_term = self.risk_aversion * (mu @ w)
        turnover_term = self.turnover_penalty * cp.sum_squares(w - w0)
        objective = cp.Minimize(risk_term - return_term + turnover_term)

        # Constraints
        constraints = [
            cp.sum(w) == 1.0,
            w >= 0.0,
            w <= max_w
        ]

        # Factor bounds
        for fname, fvec in factors.items():
            eps = tolerances.get(fname, self.default_factor_tolerance)
            constraints.append(fvec @ w <= eps)
            constraints.append(fvec @ w >= -eps)

        # Sector caps
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
```

---

### 3.5 Tier 3 Fallback Implementation (`_fallback_equal_weight`)

```python
    def _fallback_equal_weight(
        self,
        symbols: List[str],
        sector_map: Dict[str, str],
        max_w: float,
        max_sec_w: float
    ) -> np.ndarray:
        """
        Calculates equal weight allocation subject to single asset and sector caps.
        """
        n_assets = len(symbols)
        weights = np.ones(n_assets) / n_assets
        weights = np.clip(weights, 0.0, max_w)

        # Apply sector caps
        sectors = set(sector_map.get(s, "Unknown") for s in symbols)
        for sec in sectors:
            indices = [i for i, s in enumerate(symbols) if sector_map.get(s, "Unknown") == sec]
            sec_sum = np.sum(weights[indices])
            if sec_sum > max_sec_w:
                weights[indices] *= (max_sec_w / sec_sum)

        w_sum = np.sum(weights)
        if w_sum > 1e-8:
            weights /= w_sum
        return weights
```

---

## 4. Bridge Module Specification

The bridge module `trading_system/src/strategy/quad_factor_optimizer.py` re-exports `QuadFactorOptimizer`:

```python
"""
Quad-Factor Optimizer Bridge Module.
"""

from src.strategy.quad_factor_optimizer import QuadFactorOptimizer

__all__ = ["QuadFactorOptimizer"]
```

---

## 5. Integration into `PortfolioOptimizer`

In `trading_system/src/risk/portfolio_optimizer.py`, add method `optimize_quad_factor_portfolio`:

```python
    def optimize_quad_factor_portfolio(
        self,
        expected_returns: pd.Series,
        cov_matrix: Union[pd.DataFrame, np.ndarray],
        factor_df: pd.DataFrame,
        sector_map: Dict[str, str],
        w_initial: Optional[Dict[str, float]] = None,
        risk_aversion: float = 1.0,
        turnover_penalty: float = 0.01,
        max_weight: Optional[float] = None,
        max_sector_weight: Optional[float] = None,
        factor_tolerances: Optional[Dict[str, float]] = None
    ) -> Dict[str, float]:
        """
        Quad-Factor Neutral QP Portfolio Risk Optimization integration method.

        Parameters:
            expected_returns: Expected net returns per asset (Series indexed by symbol).
            cov_matrix: Asset covariance matrix (DataFrame or 2D array).
            factor_df: Factor DataFrame with columns 'beta', 'size', 'volatility', 'momentum'.
            sector_map: Mapping of symbol -> sector name.
            w_initial: Optional dictionary of current asset weights.
            risk_aversion: Risk aversion parameter lambda.
            turnover_penalty: Turnover penalty gamma.
            max_weight: Single asset weight cap.
            max_sector_weight: Sector weight cap.
            factor_tolerances: Dict of tolerance thresholds per factor.

        Returns:
            Dict[str, float]: Optimized asset weights.
        """
        from src.strategy.quad_factor_optimizer import QuadFactorOptimizer

        symbols = list(expected_returns.index)
        if isinstance(cov_matrix, np.ndarray):
            cov_df = pd.DataFrame(cov_matrix, index=symbols, columns=symbols)
        else:
            cov_df = cov_matrix

        optimizer = QuadFactorOptimizer(
            risk_aversion=risk_aversion,
            turnover_penalty=turnover_penalty,
            default_max_weight=max_weight or self.default_max_weight,
            default_max_sector_weight=max_sector_weight or self.default_max_sector_weight
        )

        return optimizer.optimize(
            expected_returns=expected_returns,
            cov_matrix=cov_df,
            factor_df=factor_df,
            sector_map=sector_map,
            w_initial=w_initial,
            max_weight=max_weight,
            max_sector_weight=max_sector_weight,
            factor_tolerances=factor_tolerances
        )
```

---

## 6. Unit Test Specification (`test_quad_factor_optimizer.py`)

The test suite in `trading_system/tests/test_quad_factor_optimizer.py` must test all constraints, fallback logic, and integration.

```python
"""
Unit Test Suite for Quad-Factor Neutral QP Portfolio Risk Optimizer (Milestone 2 - R2).
"""

import unittest
import numpy as np
import pandas as pd
from src.strategy.quad_factor_optimizer import QuadFactorOptimizer
from trading_system.src.risk.portfolio_optimizer import PortfolioOptimizer


class TestQuadFactorOptimizer(unittest.TestCase):
    """
    Test suite for QuadFactorOptimizer.
    """

    def setUp(self):
        self.symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TSLA', 'META', 'BRK.B']
        self.n_assets = len(self.symbols)

        # Expected Returns
        self.expected_returns = pd.Series(
            [0.12, 0.10, 0.15, 0.08, 0.20, 0.18, 0.14, 0.06],
            index=self.symbols
        )

        # Covariance Matrix
        np.random.seed(42)
        random_matrix = np.random.randn(self.n_assets, self.n_assets) * 0.02
        cov = np.dot(random_matrix, random_matrix.T) + np.diag([0.04] * self.n_assets)
        self.cov_df = pd.DataFrame(cov, index=self.symbols, columns=self.symbols)

        # Factors DataFrame
        self.factor_df = pd.DataFrame({
            'beta': [1.2, 0.9, 1.1, 1.0, 1.5, 1.8, 1.3, 0.6],
            'size': [12.5, 12.4, 12.2, 12.3, 11.8, 11.5, 12.0, 12.1],
            'volatility': [0.22, 0.18, 0.20, 0.21, 0.35, 0.45, 0.28, 0.14],
            'momentum': [0.15, 0.10, 0.05, -0.02, 0.40, 0.30, 0.12, -0.05]
        }, index=self.symbols)

        # Sector Mapping (2 sectors)
        self.sector_map = {
            'AAPL': 'Tech', 'MSFT': 'Tech', 'GOOGL': 'Tech', 'AMZN': 'Consumer',
            'NVDA': 'Tech', 'TSLA': 'Consumer', 'META': 'Tech', 'BRK.B': 'Financials'
        }

    def test_weight_sum_equality_constraint(self):
        """
        Verify sum of weights equals 1.0 (within 1e-5).
        """
        optimizer = QuadFactorOptimizer(default_max_weight=0.25)
        weights = optimizer.optimize(
            self.expected_returns, self.cov_df, self.factor_df, self.sector_map
        )
        total_w = sum(weights.values())
        self.assertAlmostEqual(total_w, 1.0, places=5)
        for sym, w in weights.items():
            self.assertGreaterEqual(w, 0.0)

    def test_quad_factor_neutrality_bounds(self):
        """
        Verify factor exposures strictly satisfy |f^T * w| <= 0.05.
        """
        optimizer = QuadFactorOptimizer(default_max_weight=0.25, default_factor_tolerance=0.05)
        weights = optimizer.optimize(
            self.expected_returns, self.cov_df, self.factor_df, self.sector_map
        )
        w_vec = np.array([weights[s] for s in self.symbols])

        for col in ['beta', 'size', 'volatility', 'momentum']:
            raw_f = self.factor_df[col].values
            std_f = (raw_f - np.mean(raw_f)) / np.std(raw_f)
            exp = float(np.dot(std_f, w_vec))
            self.assertLessEqual(abs(exp), 0.051, f"Factor {col} exposure {exp} exceeded bound 0.05")

    def test_sector_cap_constraint(self):
        """
        Verify sector weight exposure sum <= 25% (or max_sector_weight).
        """
        optimizer = QuadFactorOptimizer(default_max_weight=0.15, default_max_sector_weight=0.25)
        weights = optimizer.optimize(
            self.expected_returns, self.cov_df, self.factor_df, self.sector_map, max_sector_weight=0.25
        )

        sec_sums = {}
        for sym, w in weights.items():
            sec = self.sector_map[sym]
            sec_sums[sec] = sec_sums.get(sec, 0.0) + w

        for sec, total_w in sec_sums.items():
            self.assertLessEqual(total_w, 0.251, f"Sector {sec} sum {total_w} exceeded 0.25 cap")

    def test_fallback_on_infeasible_constraints(self):
        """
        Verify graceful fallback to Tier 1/2/3 when factor bounds are impossibly tight (e.g. 0.00001).
        """
        optimizer = QuadFactorOptimizer(default_max_weight=0.15, default_factor_tolerance=0.00001)
        weights = optimizer.optimize(
            self.expected_returns, self.cov_df, self.factor_df, self.sector_map
        )
        self.assertEqual(len(weights), self.n_assets)
        self.assertAlmostEqual(sum(weights.values()), 1.0, places=4)

    def test_portfolio_optimizer_integration(self):
        """
        Test integration with PortfolioOptimizer.optimize_quad_factor_portfolio().
        """
        po = PortfolioOptimizer()
        weights = po.optimize_quad_factor_portfolio(
            self.expected_returns, self.cov_df, self.factor_df, self.sector_map,
            max_weight=0.20, max_sector_weight=0.30
        )
        self.assertIsInstance(weights, dict)
        self.assertEqual(len(weights), self.n_assets)
        self.assertAlmostEqual(sum(weights.values()), 1.0, places=5)


if __name__ == '__main__':
    unittest.main()
```

---

## 7. Forensic Verification & Acceptance Protocol

To verify Milestone 2 (R2) implementation:

1. **Python Command Verification**:
   ```bash
   .venv\Scripts\python.exe -m pytest trading_system/tests/test_quad_factor_optimizer.py -v
   ```
2. **Acceptance Criteria**:
   - All tests pass with zero errors.
   - Weights sum exactly to $1.0 \pm 10^{-5}$.
   - All factor exposure standard deviations satisfy $|F^T w| \le 0.05$.
   - No sector weight exceeds $0.25$.
   - Fallback hierarchy handles infeasible constraints smoothly.
