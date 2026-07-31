# Remediation Changes Report — Worker M2-2 (R2: Quad-Factor Neutral QP Portfolio Risk Optimizer)

## Overview
Remediated normalization flaws and test suite setup for Milestone 2 (R2): Quad-Factor Neutral QP Portfolio Risk Optimizer based on Reviewer findings.

## Modified Files
1. `src/strategy/quad_factor_optimizer.py`
   - Added `_apply_bounded_normalization()` helper implementing iterative water-filling bounded normalization.
   - Fixed `_fallback_equal_weight()` to apply bounded normalization instead of naive `weights /= w_sum`, ensuring that sector caps (`max_sector_weight`) and single asset bounds (`max_weight`) are strictly enforced without inflation.
   - Updated `QuadFactorOptimizer.optimize()` post-processing to apply bounded normalization, maintaining inequality constraints $w_i \le max\_w$ and $\sum_{i \in Sector_k} w_i \le max\_sec\_w$ when scaling uncapped sectors/assets.

2. `trading_system/src/risk/portfolio_optimizer.py`
   - Refactored `apply_factor_and_sector_constraints()` to use bounded iterative water-filling.
   - Prevented underloaded sectors from being artificially inflated past `max_sector_weight` when scaling remaining budget, keeping sector weights strictly $\le max\_sector\_weight + 1e-5$ and total weight sum $\le 1.0$.

3. `trading_system/tests/test_quad_factor_optimizer.py`
   - Updated `self.sector_map` in `setUp()` to map the 8 assets across 5 distinct sectors (`Tech`, `Consumer`, `Financials`, `Healthcare`, `Industrial`) so that $\sum \text{sec\_cap} = 5 \times 0.25 = 1.25 \ge 1.0$, rendering the optimization problem mathematically FEASIBLE for the primary SLSQP / CVXPY QP solvers.
   - Added new test case `test_overconstrained_infeasible_sector_caps()` to explicitly test overconstrained infeasible sector cap setups (e.g. 3 sectors with cap 0.25, total capacity = 0.75 < 1.0), verifying that fallback triggers cleanly, total weight sum remains $\le 1.0$, and sector caps are NEVER violated.

4. `trading_system/tests/test_portfolio_optimizer_and_oms.py`
   - Updated `test_factor_and_sector_constraints()` test fixture to include 3 sectors (`Semiconductors`, `Tech`, `Software`) with `max_sector_weight = 0.40`, ensuring total sector capacity ($3 \times 0.40 = 1.20 \ge 1.0$) supports $\sum w_i = 1.0$ while strictly enforcing sector caps.

## Verification Results
- `trading_system/tests/test_quad_factor_optimizer.py`: 7 passed in 0.49s (100% pass rate).
- `tests/test_quad_factor_optimizer.py`: 7 passed in 32.55s (100% pass rate).
- `trading_system/tests/test_portfolio_optimizer_and_oms.py`: 3 passed in 3.10s (100% pass rate).
