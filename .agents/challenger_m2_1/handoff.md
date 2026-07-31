# Empirical Challenge Handoff Report: `QuadFactorOptimizer`

**Agent ID**: `challenger_m2_1`  
**Role**: EMPIRICAL CHALLENGER (critic, specialist)  
**Target Module**: `src/strategy/quad_factor_optimizer.py`  
**Test Suite**: `trading_system/tests/test_quad_factor_optimizer.py`  

---

## 1. Observation

### 1.1 Unit Test Execution Results
Command executed:
```powershell
.venv\Scripts\python.exe -m pytest trading_system/tests/test_quad_factor_optimizer.py -v
```

Verbatim Output (2 FAILED, 4 PASSED):
```text
FAILED trading_system\tests\test_quad_factor_optimizer.py::TestQuadFactorOptimizer::test_quad_factor_neutrality_bounds
AssertionError: 0.15573256428553633 not less than or equal to 0.051 : Factor size exposure -0.15573256428553633 exceeded bound 0.05

FAILED trading_system\tests\test_quad_factor_optimizer.py::TestQuadFactorOptimizer::test_sector_cap_constraint
AssertionError: 0.47058823529411764 not less than or equal to 0.251 : Sector Tech sum 0.47058823529411764 exceeded 0.25 cap

Passed:
- test_weight_sum_equality_constraint
- test_fallback_on_infeasible_constraints
- test_portfolio_optimizer_integration
- test_optimize_portfolio_method_alias
```

Log Warnings during test execution:
```text
WARNING _root_quad_factor_optimizer:quad_factor_optimizer.py:148 QuadFactorOptimizer primary QP solver failed. Triggering Tier 1 Fallback (Relaxed Factor Bounds).
WARNING _root_quad_factor_optimizer:quad_factor_optimizer.py:156 Tier 1 Fallback failed. Triggering Tier 2 Fallback (Mean-Variance / Sector Capped MVO).
WARNING _root_quad_factor_optimizer:quad_factor_optimizer.py:163 Tier 3 Fallback failed. Triggering Tier 3 Fallback (Equal Weight with Sector Caps).
```

---

### 1.2 Direct Code Observations in `src/strategy/quad_factor_optimizer.py`

#### Observation A (Lines 118–121): Incomplete Index Validation in Factor Normalization
```python
118:        for f in factors:
119:            target_col = col_map.get(f.lower())
120:            if target_col is not None and symbols[0] in factor_df.index:
121:                raw_f = factor_df.loc[symbols, target_col].values.astype(np.float64)
```
- Line 120 only checks `symbols[0] in factor_df.index`.
- If `symbols[0]` exists but any subsequent symbol in `symbols` is missing from `factor_df.index`, line 121 raises `KeyError: "['<missing_symbol>'] not in index"`.

#### Observation B (Lines 347–349 & 167–170): Post-Processing Normalization Overwriting Bounds
```python
# In _fallback_equal_weight (lines 347-349):
347:        w_sum = np.sum(weights)
348:        if w_sum > 1e-8:
349:            weights /= w_sum

# In optimize() (lines 167-170):
167:        weights = np.clip(weights, 0.0, max_w)
168:        w_sum = np.sum(weights)
169:        if w_sum > 1e-8:
170:            weights = weights / w_sum
```
- When clipping or sector caps reduce total weight sum $w_{\text{sum}} < 1.0$, dividing by $w_{\text{sum}}$ multiplies all asset weights by $\frac{1}{w_{\text{sum}}} > 1.0$.
- This step scales up weights and directly breaches both `max_weight` asset caps and `max_sector_weight` sector caps.

---

### 1.3 Synthetic Harness Empirical Results

Command executed: `.venv\Scripts\python.exe .agents\challenger_m2_1\stress_harness.py`

1. **Infeasible Sector Cap Violation**:
   - Setting `max_sector_weight = 0.25` with 8 assets (5 Tech, 2 Consumer, 1 Financials) yields maximum possible portfolio sum of $0.25 + 0.25 + 0.25 = 0.75 < 1.0$.
   - Output sector sums: Tech = `0.4706` (cap `0.25`), Consumer = `0.3529` (cap `0.25`).
   - Single-asset weights for AMZN, TSLA, BRK.B reached `0.1765` (violating `max_w = 0.15`).

2. **Feasible Sector Cap & Factor Neutrality Execution**:
   - When `max_sector_weight = 0.70` (so sum of sector caps $= 2.1 \ge 1.0$), SciPy SLSQP primary solver converges cleanly in < 0.05 seconds.
   - Resulting factor exposures:
     - Beta: `0.0500` ($\le 0.05$)
     - Size: `-0.0500` ($\le 0.05$)
     - Volatility: `-0.0026` ($\le 0.05$)
     - Momentum: `0.0500` ($\le 0.05$)

3. **Ill-conditioned and Non-PSD Covariance Matrices**:
   - Condition number $10^{14}$: SLSQP converged cleanly without NaNs, weight sum = 1.0000.
   - Non-positive semidefinite covariance matrix: SLSQP converged without NaNs, weight sum = 1.0000.

4. **Extreme Expected Return Vectors**:
   - $\mu \times 10^8$ and $\mu \times 10^{-12}$: SLSQP converged, outputting valid weight vectors summing to 1.0.

5. **100-Asset Universe Scale**:
   - 100 stocks across 5 sectors (`max_w=0.05`, `max_sec_w=0.30`): SLSQP converged in 0.17 seconds, strictly enforcing factor bounds $\le 0.05$.

---

## 2. Logic Chain

1. **Premise 1**: SciPy SLSQP minimizes $f(w) = \frac{1}{2} w^T \Sigma w - \lambda \mu^T w + \gamma \|w - w_0\|_2^2$ subject to equality constraint $\sum w_i = 1.0$, single-asset bounds $0 \le w_i \le \text{max\_w}$, factor bounds $|f_k^T w| \le \epsilon$, and sector caps $\sum_{i \in S_k} w_i \le \text{max\_sec\_w}$.
2. **Premise 2**: If the sum of sector caps across all sectors $\sum_k \text{max\_sec\_w} < 1.0$, the equality constraint $\sum w_i = 1.0$ and sector cap inequalities are mathematically contradictory.
3. **Step 1 (Observation 1.1 & 1.3)**: In the standard unit test setup (8 assets, 3 sectors: Tech [5], Consumer [2], Financials [1]), `default_max_sector_weight` is 0.25. The maximum total weight achievable across the 3 sectors is $3 \times 0.25 = 0.75$.
4. **Step 2**: Because $0.75 < 1.0$, SLSQP primary solver fails to find a feasible solution and returns `None`. Tier 1 (relaxed factor bounds) and Tier 2 (MVO without factor bounds) also fail because sector caps remain infeasible.
5. **Step 3 (Observation 1.2, Observation B)**: Control falls through to Tier 3 Fallback (`_fallback_equal_weight`). Tier 3 caps Tech sector sum at 0.25, bringing the unnormalized portfolio sum to $w_{\text{sum}} = 0.53125$.
6. **Step 4**: Tier 3 performs `weights /= w_sum`, dividing every asset weight by $0.53125$. This scales Tech sector total weight from $0.25$ up to $\frac{0.25}{0.53125} = 0.4706$, directly violating the $0.25$ sector cap constraint.
7. **Step 5 (Observation 1.1 & 1.2, Observation A)**: In addition, factor normalization checks only `symbols[0] in factor_df.index`. When a symbol is missing from `factor_df`, `factor_df.loc[symbols, target_col]` throws an unhandled `KeyError`.
8. **Conclusion**: Primary solver failure in the test suite is caused by an infeasible sector cap configuration, and Tier 3 fallback contains a normalization logic flaw that breaches sector and asset weight limits. When sector caps are mathematically feasible ($\ge 0.70$), SLSQP demonstrates high numerical stability and exact factor neutrality.

---

## 3. Challenge Summary & Risk Assessment

**Overall Risk Assessment**: **HIGH**

### Challenges

#### [Critical] Challenge 1: Post-Processing Weight Normalization Destroys Bounds
- **Assumption challenged**: Dividing weights by $w_{\text{sum}}$ preserves constraint compliance.
- **Attack scenario**: Any situation where single-asset clipping or sector capping reduces total portfolio weight below 1.0 (e.g., concentrated sectors, small asset universe).
- **Blast radius**: Assets and sectors receive allocations significantly exceeding risk limits (e.g. 47% in Tech instead of 25%, 17.6% per stock instead of 15%).
- **Mitigation**: Post-normalization should use iterative projection onto the simplex with bounded box constraints, or re-allocate residual weight only to un-capped assets/sectors.

#### [High] Challenge 2: Mutually Infeasible Constraints Cause Uncontrolled Fallback Cascade
- **Assumption challenged**: Default sector cap (0.25) is always feasible.
- **Attack scenario**: Portfolios with few sectors (e.g. 2 or 3 sectors). Sum of sector caps ($3 \times 0.25 = 0.75$) is less than required sum of weights (1.0).
- **Blast radius**: Primary SLSQP QP solver fails 100% of the time, bypassing factor neutrality and MVO optimization completely.
- **Mitigation**: Validate $\sum_{\text{sectors}} \text{max\_sec\_w} \ge 1.0$ before optimization; dynamically scale sector caps if infeasible.

#### [High] Challenge 3: Unhandled `KeyError` on Missing/Mismatched Factor Index
- **Assumption challenged**: All target symbols exist in `factor_df.index` if `symbols[0]` exists.
- **Attack scenario**: Missing stock in fundamental/factor database or index ordering mismatch.
- **Blast radius**: Complete exception crash during live pipeline run (`KeyError: "['BRK.B'] not in index"`).
- **Mitigation**: Use `factor_df.reindex(symbols).fillna(0.0)` for safe index alignment.

#### [Medium] Challenge 4: CVXPY Dependency Missing in Default Environment
- **Assumption challenged**: System relies on CVXPY as primary QP solver.
- **Attack scenario**: `HAS_CVXPY` evaluates to `False` in standard `.venv`.
- **Blast radius**: System relies solely on SciPy SLSQP, which is less robust than dedicated interior-point QP solvers (OSQP/ECOS) under tight inequality bounds.
- **Mitigation**: Add `cvxpy` to `.venv` dependencies or enhance SLSQP constraint pre-validation.

---

## 4. Caveats

- **No modifications made to implementation code**: In accordance with the Review-Only constraint, no source code in `src/strategy/quad_factor_optimizer.py` was altered.
- **CVXPY performance unverified in local `.venv`**: Because `cvxpy` is not installed in `.venv`, CVXPY execution was simulated via code inspection; all empirical tests ran against SciPy SLSQP.

---

## 5. Conclusion

`QuadFactorOptimizer` provides a solid mathematical foundation for quad-factor neutral portfolio optimization via SciPy SLSQP. When constraints are mathematically feasible, the SLSQP solver demonstrates high numerical stability across extreme return scales ($\mu \times 10^8$), ill-conditioned covariance matrices (condition number $10^{14}$), non-PSD covariance matrices, collinear factor matrices, and large asset universes (100+ stocks).

However, two critical failure modes were empirically demonstrated:
1. Default sector caps (0.25) in portfolios with $\le 3$ sectors create mutually infeasible constraints with $\sum w_i = 1.0$, forcing primary solver failure.
2. The Tier 3 fallback normalization (`weights /= w_sum`) breaches both single-asset weight limits ($0.1765 > 0.15$) and sector concentration caps ($0.4706 > 0.25$).

---

## 6. Verification Method

To independently verify all findings:

1. **Run Unit Test Suite**:
   ```powershell
   .venv\Scripts\python.exe -m pytest trading_system/tests/test_quad_factor_optimizer.py -v
   ```
   *Expected Result*: 2 failures (`test_quad_factor_neutrality_bounds` and `test_sector_cap_constraint`).

2. **Execute Empirical Stress Test Harness**:
   ```powershell
   .venv\Scripts\python.exe .agents\challenger_m2_1\stress_harness.py
   ```
   *Expected Result*:
   - Test 1: Diagnostic log showing primary SLSQP failure and Tier 3 fallback.
   - Test 5: `KeyError: "['BRK.B'] not in index"`.
   - Test 6: Tech sector weight = `0.4706` breaching `0.25` cap.

3. **Execute Deep Stress Test Harness**:
   ```powershell
   .venv\Scripts\python.exe .agents\challenger_m2_1\deep_stress_test.py
   ```
   *Expected Result*: Clean SLSQP convergence when `max_sector_weight = 0.70` and clean scaling for 100 assets.
