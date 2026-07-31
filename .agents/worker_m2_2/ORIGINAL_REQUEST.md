## 2026-07-31T19:03:38Z

Task: Remediate normalization flaws and test suite setup for Milestone 2 (R2): Quad-Factor Neutral QP Portfolio Risk Optimizer based on Reviewer findings.

Files to update:
- `src/strategy/quad_factor_optimizer.py`
- `trading_system/src/strategy/quad_factor_optimizer.py`
- `trading_system/src/risk/portfolio_optimizer.py`
- `trading_system/tests/test_quad_factor_optimizer.py`
- `tests/test_quad_factor_optimizer.py`

Fix Directives:
1. **Fix Post-Scaling Re-Normalization in `_fallback_equal_weight()` and `apply_factor_and_sector_constraints()`**:
   - Issue: When sector weights are capped to `max_sector_weight` (or weights clipped), $w_{sum}$ drops below 1.0. Dividing by $w_{sum} < 1.0$ multiplies capped sector weights by $1/w_{sum} > 1.0$, breaching sector caps (e.g. 25% sector cap inflates to 47.06%).
   - Fix: Implement iterative water-filling / bounded normalization:
     Ensure no sector weight sum EVER exceeds `max_sector_weight + 1e-5` and no asset weight EVER exceeds `max_asset_weight + 1e-5`.

2. **Fix `QuadFactorOptimizer.optimize()` Post-Processing**:
   - Ensure post-processing normalization strictly maintains inequality constraints: $w_i \le max\_w$ and $\sum_{i \in Sector_k} w_i \le max\_sec\_w$.

3. **Fix Test Fixture Setup in `test_quad_factor_optimizer.py`**:
   - In `test_quad_factor_optimizer.py`, `self.symbols` previously had 8 assets across 3 sectors (`Tech`: 5, `Consumer`: 2, `Financials`: 1) with `max_sector_weight = 0.25`. Max possible sum across 3 sectors was $3 \times 0.25 = 0.75 < 1.0$, which is mathematically impossible for $\sum w_i = 1.0$.
   - Update `self.sector_map` to include 5 sectors (e.g. `Tech`, `Consumer`, `Financials`, `Healthcare`, `Industrial`) so that $\sum \text{sec\_cap} = 5 \times 0.25 = 1.25 \ge 1.0$, making the test problem FEASIBLE for the primary SLSQP / CVXPY solver!
   - Add a separate test case `test_overconstrained_infeasible_sector_caps()` that explicitly tests infeasible setup where total sector capacity $< 1.0$, verifying that fallback triggers cleanly and sector caps are NEVER violated.

4. **Verify Test Suite**:
   - Run `.venv\Scripts\python.exe -m pytest trading_system/tests/test_quad_factor_optimizer.py -v`.
   - Run `.venv\Scripts\python.exe -m pytest tests/test_quad_factor_optimizer.py -v`.
   - Run `.venv\Scripts\python.exe -m pytest trading_system/tests/ -v`.
   - Confirm 100% pass rate with zero failures.
