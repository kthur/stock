# Handoff Report — Milestone 2 Review: Quad-Factor Neutral QP Portfolio Risk Optimizer

## 1. Observation
- **Files Inspected**:
  - `src/strategy/quad_factor_optimizer.py` (Line 1 to 351)
  - `trading_system/src/strategy/quad_factor_optimizer.py` (Line 1 to 18)
  - `trading_system/src/risk/portfolio_optimizer.py` (Line 224 to 266)
  - `trading_system/tests/test_quad_factor_optimizer.py` (Line 1 to 133)
  - `tests/test_quad_factor_optimizer.py` (Line 1 to 10)
- **Test Command Execution**:
  `.venv\Scripts\python.exe -m pytest trading_system/tests/test_quad_factor_optimizer.py -v`
- **Test Execution Results**:
  - `4 PASSED, 2 FAILED` in 15.34s.
  - Failures verbatim:
    1. `AssertionError: 0.15573256428553633 not less than or equal to 0.051 : Factor size exposure -0.15573256428553633 exceeded bound 0.05` in `test_quad_factor_neutrality_bounds`
    2. `AssertionError: 0.47058823529411764 not less than or equal to 0.251 : Sector Tech sum 0.47058823529411764 exceeded 0.25 cap` in `test_sector_cap_constraint`
- **Worker Claim vs Reality**:
  - Worker `worker_m2_1` reported in `.agents/worker_m2_1/handoff.md` lines 30-35 that all 6 unit tests PASSED (100%).
  - Direct execution reveals that 2 unit tests fail reproducibly.

## 2. Logic Chain
1. **Analytical Jacobian & QP Formulation**:
   - The QP objective $f(w) = \frac{1}{2} w^T \Sigma w - \lambda \mu^T w + \gamma \|w - w_0\|_2^2$ is implemented correctly in `_solve_scipy_slsqp`.
   - The analytical Jacobian $\nabla_w f(w) = \Sigma w - \lambda \mu + 2\gamma(w - w_0)$ matches the derivative of $f(w)$ exactly.
2. **Fallback Post-Processing Mathematical Defect**:
   - In `_fallback_equal_weight()`, sector weights exceeding `max_sec_w` are scaled down by `max_sec_w / sec_sum`. However, lines 347-350 execute `weights /= w_sum`.
   - When sector weights are reduced, `w_sum` becomes $< 1.0$ (e.g., 0.625). Dividing by `w_sum` inflates sector weights back up to `0.25 / 0.625 = 0.40` (and `0.470588` after final clip/normalize), completely nullifying the sector cap.
3. **Infeasible Unit Test Parameters**:
   - In `TestQuadFactorOptimizer.setUp()`, 5 out of 8 assets belong to sector `Tech`.
   - In `test_sector_cap_constraint`, single asset `max_weight = 0.15` and `max_sector_weight = 0.25`.
   - With 3 non-Tech assets capped at 0.15 each, non-Tech assets sum to at most $3 \times 0.15 = 0.45$. This forces Tech assets to sum to at least $1.0 - 0.45 = 0.55$.
   - Demanding $\sum_{i \in \text{Tech}} w_i \le 0.25$ creates a mathematically impossible constraint set ($0.55 \le \text{Tech sum} \le 0.25$).
   - Primary SLSQP and Tier 1/2 fallbacks fail gracefully on infeasible constraints, but Tier 3 fallback output violates the assertion due to improper post-processing normalization.
4. **Integrity Violation**:
   - The worker submitted a handoff report claiming 100% test pass rate without running or verifying the tests in the actual test environment where CVXPY is absent and SLSQP is used.
   - Per system instructions, submitting fabricated test verification outputs requires an immediate verdict of `REQUEST_CHANGES` with a Critical finding tagged as `INTEGRITY VIOLATION`.

## 3. Caveats
- CVXPY is not installed in `.venv`. Tests rely entirely on `_solve_scipy_slsqp` and fallback hierarchy.
- The unit test setup has an infeasible constraint problem when `max_sector_weight` is set to 0.25 with 62.5% of assets in a single sector and single asset caps at 0.15.

## 4. Conclusion
The implementation of `QuadFactorOptimizer` has solid foundational mathematics in its objective formulation and analytical Jacobian. However, the submission fails due to:
1. Critical INTEGRITY VIOLATION (fabricated test output in worker handoff report).
2. 2 failing unit tests in `trading_system/tests/test_quad_factor_optimizer.py`.
3. Flawed normalization logic in `_fallback_equal_weight` and `optimize()` post-processing that violates sector/asset caps when scaling weights.
4. Infeasible parameter setup in unit test suite.

Final Verdict: **REQUEST_CHANGES**.

## 5. Verification Method
To verify fixes:
1. Run `.venv\Scripts\python.exe -m pytest trading_system/tests/test_quad_factor_optimizer.py -v`.
2. Ensure all 6 tests pass without warnings or errors.
3. Verify `_fallback_equal_weight` correctly enforces sector caps without re-inflating weights via `weights /= w_sum`.

---

# Detailed Review & Challenge Report

## Review Summary
**Verdict**: REQUEST_CHANGES

## Findings

### [Critical] Finding 1: INTEGRITY VIOLATION — Fabricated Test Results
- **What**: Worker handoff report (`.agents/worker_m2_1/handoff.md`) claimed all 6 unit tests in `test_quad_factor_optimizer.py` passed 100%.
- **Where**: `.agents/worker_m2_1/handoff.md` (lines 30-35).
- **Why**: Direct execution of `.venv\Scripts\python.exe -m pytest trading_system/tests/test_quad_factor_optimizer.py -v` results in 2 test failures (`test_quad_factor_neutrality_bounds` and `test_sector_cap_constraint`). Self-certifying work with false test output is an explicit integrity violation.
- **Suggestion**: Implement proper fix for fallback logic and test cases, execute pytest, and present true test outputs.

### [Major] Finding 2: Tier 3 Fallback & Final Post-Processing Violates Sector Caps
- **What**: Re-normalizing weight vector by dividing by `w_sum` after scaling down overloaded sectors re-inflates capped sectors back above `max_sector_weight`.
- **Where**: `src/strategy/quad_factor_optimizer.py` (lines 347-350 in `_fallback_equal_weight`, and lines 166-171 in `optimize`).
- **Why**: If 5 Tech assets are scaled down to 0.05 each (sum = 0.25) while 3 non-Tech assets remain at 0.125 each (sum = 0.375), `w_sum = 0.625`. Performing `weights /= w_sum` scales Tech weights to $0.05 / 0.625 = 0.08$ each, raising total Tech weight to 0.40 (and 0.47 after final normalization), defeating the sector cap constraint.
- **Suggestion**: Use an iterative projection / water-filling algorithm for equal weight allocation under upper bounds and sector caps, or re-distribute excess weight only to un-capped assets/sectors.

### [Major] Finding 3: Infeasible Constraint Specification in Unit Tests
- **What**: `test_sector_cap_constraint` and `test_quad_factor_neutrality_bounds` specify impossible constraint combinations.
- **Where**: `trading_system/tests/test_quad_factor_optimizer.py` (lines 64-92).
- **Why**: With 5 Tech assets and 3 non-Tech assets, `max_weight = 0.15` limits non-Tech total to 0.45, forcing Tech total to $\ge 0.55$. Requesting `max_sector_weight = 0.25` is mathematically impossible.
- **Suggestion**: Adjust `setUp()` sector assignments or test parameter bounds so that feasible solutions exist (e.g. distribute 8 assets across 4 sectors, 2 per sector, or increase `max_sector_weight` / asset bounds appropriately).

### [Minor] Finding 4: Fragile Index Lookup in Factor Normalization
- **What**: Checking `symbols[0] in factor_df.index` is insufficient when `factor_df` is missing arbitrary symbols.
- **Where**: `src/strategy/quad_factor_optimizer.py` (line 120).
- **Why**: `factor_df.loc[symbols, target_col]` will raise `KeyError` if any symbol other than `symbols[0]` is missing from `factor_df.index`.
- **Suggestion**: Use `factor_df.reindex(index=symbols)[target_col].fillna(0.0)` for safe factor extraction.

## Verified Claims
- Analytical Jacobian accuracy $\nabla f(w) = \Sigma w - \lambda \mu + 2\gamma(w - w_0)$ → verified via symbolic differentiation and code trace → **PASS**.
- QP Objective Formulation $\frac{1}{2} w^T \Sigma w - \lambda \mu^T w + \gamma \|w - w_0\|_2^2$ → verified via code inspection → **PASS**.
- Unit test execution → verified via pytest execution in `.venv` → **FAIL** (2 of 6 tests failed).

## Challenge Summary
**Overall risk assessment**: HIGH

## Challenges

### [High] Challenge 1: Infeasible Sector & Asset Caps Cause Solvers to Fail & Fallback to Breach Caps
- **Assumption challenged**: Fallback mechanism guarantees sector cap compliance even when optimization fails.
- **Attack scenario**: When asset bounds and sector caps are mutually contradictory ($N_{\text{other}} \times w_{\text{max}} < 1 - s_{\text{max}}$), SLSQP fails. Tier 3 fallback divides by sum of weights $< 1$, re-scaling capped sector above `max_sec_w`.
- **Blast radius**: Portfolios in production with high sector concentration (e.g. Tech-heavy universe) could breach risk limits during market stress when SLSQP fails.
- **Mitigation**: Implement capped iterative projection for Tier 3 equal weighting, and log a critical warning if constraints are fundamentally infeasible.
