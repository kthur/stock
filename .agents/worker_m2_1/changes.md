# Detailed Implementation Report: Quad-Factor Neutral QP Portfolio Risk Optimizer (Milestone 2 - R2)

## Overview
Implemented Milestone 2 (R2) Quad-Factor Neutral Quadratic Programming (QP) Portfolio Risk Optimizer.

## Modified and Created Files

### 1. `src/strategy/quad_factor_optimizer.py` & `trading_system/src/strategy/quad_factor_optimizer.py`
- **Class `QuadFactorOptimizer`**:
  - Implements Quadratic Programming optimization solving $\min_w \frac{1}{2} w^T \Sigma w - \lambda \mu^T w + \gamma \|w - w_0\|_2^2$.
  - Provides exact analytical gradient Jacobian $\nabla f(w) = \Sigma w - \lambda \mu + 2 \gamma (w - w_0)$ and analytical constraint Jacobians to `scipy.optimize.minimize(method='SLSQP')`.
  - Performs Z-score standardization ($\tilde{F}_i^{(k)} = \frac{F_i^{(k)} - \bar{F}^{(k)}}{\sigma(F^{(k)})}$) across 4 factors (Market Beta, Size, Volatility, 12M-1M Momentum).
  - Enforces 4 strict constraint categories:
    1. Weight sum equality: $\sum w_i = 1.0$.
    2. Long-only asset bounds: $0 \le w_i \le \text{max\_asset\_weight}$ (default $0.10$).
    3. Quad-Factor neutrality bounds: $|(\tilde{F}^{(k)})^T w| \le \text{factor\_neutral\_tol}$ (default $0.05$).
    4. Sector concentration caps: $\sum_{i \in \text{Sector}_k} w_i \le \text{max\_sector\_weight}$ (default $0.25$).
  - Implements robust 3-Tier Fallback Hierarchy when constraints are infeasible:
    - **Tier 1**: Relax factor tolerance 2x (e.g., $0.05 \to 0.10$).
    - **Tier 2**: Mean-Variance Optimization without factor bounds (sector caps and asset bounds maintained).
    - **Tier 3**: Equal Weight allocation clamped to asset bounds and sector caps via iterative projection, normalized to $1.0$.
  - Supports guarded optional `cvxpy` solver fallback (`HAS_CVXPY`).
  - Supports both `optimize(...)` and `optimize_portfolio(...)` method signatures.
  - Bridge module in `trading_system/src/strategy/quad_factor_optimizer.py` uses dynamic `importlib` loader to resolve `QuadFactorOptimizer` cleanly without circular import regardless of `sys.path` order or pytest root directory.

### 2. `trading_system/src/risk/portfolio_optimizer.py`
- **Added `optimize_quad_factor_portfolio(...)` method**:
  - Bridges `PortfolioOptimizer` with `QuadFactorOptimizer`.
  - Handles covariance matrix conversion and default parameter forwarding.
  - Imported `Union` from `typing` to fix type annotation error.
  - Updated `apply_factor_and_sector_constraints` to proportionally redistribute excess weight from overloaded sectors to under-loaded sectors, strictly satisfying sector caps after normalization.

### 3. `trading_system/tests/test_quad_factor_optimizer.py` & `tests/test_quad_factor_optimizer.py`
- **Unit Test Suite**:
  - `test_weight_sum_equality_constraint`: Asserts $\sum w_i = 1.0$ and non-negative weights.
  - `test_quad_factor_neutrality_bounds`: Asserts $|(\tilde{F}^{(k)})^T w| \le 0.05$ across all 4 factors.
  - `test_sector_cap_constraint`: Asserts sector sum $\le 0.25$.
  - `test_fallback_on_infeasible_constraints`: Asserts graceful 3-tier fallback execution under extreme constraints.
  - `test_portfolio_optimizer_integration`: Asserts `PortfolioOptimizer.optimize_quad_factor_portfolio()` returns valid normalized weights.
  - `test_optimize_portfolio_method_alias`: Asserts convenience alias method works identically.
