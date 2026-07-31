# Review Handoff Report — Milestone 2 (R2: Quad-Factor Neutral QP Portfolio Risk Optimizer)

## 1. Observation

### 1.1 Test Execution Output
Command executed:
```powershell
.venv\Scripts\python.exe -m pytest trading_system/tests/test_quad_factor_optimizer.py -v
```

Execution result (2 FAILED, 4 PASSED in 17.93s):
```
=========================== short test summary info ===========================
FAILED trading_system\tests\test_quad_factor_optimizer.py::TestQuadFactorOptimizer::test_quad_factor_neutrality_bounds
FAILED trading_system\tests\test_quad_factor_optimizer.py::TestQuadFactorOptimizer::test_sector_cap_constraint
======================== 2 failed, 4 passed in 17.93s =========================
```

Verbatim Failure Details:

1. `test_quad_factor_neutrality_bounds`:
```
AssertionError: 0.15573256428553633 not less than or equal to 0.051 : Factor size exposure -0.15573256428553633 exceeded bound 0.05
Captured stderr call:
2026-07-31 19:01:42,647 - _root_quad_factor_optimizer - WARNING - QuadFactorOptimizer primary QP solver failed. Triggering Tier 1 Fallback (Relaxed Factor Bounds).
2026-07-31 19:01:43,276 - _root_quad_factor_optimizer - WARNING - Tier 1 Fallback failed. Triggering Tier 2 Fallback (Mean-Variance / Sector Capped MVO).
2026-07-31 19:01:43,502 - _root_quad_factor_optimizer - WARNING - Tier 2 Fallback failed. Triggering Tier 3 Fallback (Equal Weight with Sector Caps).
```

2. `test_sector_cap_constraint`:
```
AssertionError: 0.47058823529411764 not less than or equal to 0.251 : Sector Tech sum 0.47058823529411764 exceeded 0.25 cap
Captured stderr call:
2026-07-31 19:01:51,220 - _root_quad_factor_optimizer - WARNING - QuadFactorOptimizer primary QP solver failed. Triggering Tier 1 Fallback (Relaxed Factor Bounds).
2026-07-31 19:01:51,690 - _root_quad_factor_optimizer - WARNING - Tier 1 Fallback failed. Triggering Tier 2 Fallback (Mean-Variance / Sector Capped MVO).
2026-07-31 19:01:51,712 - _root_quad_factor_optimizer - WARNING - Tier 2 Fallback failed. Triggering Tier 3 Fallback (Equal Weight with Sector Caps).
```

### 1.2 Code Inspection Observations

#### `src/strategy/quad_factor_optimizer.py` (lines 166-172, 332-349)
Lines 166-172:
```python
        # Final Normalization & Cleaning
        weights = np.clip(weights, 0.0, max_w)
        w_sum = np.sum(weights)
        if w_sum > 1e-8:
            weights = weights / w_sum

        return {sym: float(w) for sym, w in zip(symbols, weights)}
```

Lines 336-349 in `_fallback_equal_weight`:
```python
        n_assets = len(symbols)
        weights = np.ones(n_assets) / n_assets
        weights = np.clip(weights, 0.0, max_w)

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

#### `trading_system/src/risk/portfolio_optimizer.py` (lines 179-191)
```python
        # Cap overloaded sectors
        for sec, total_w in sector_exposure.items():
            if total_w > max_sector_weight:
                scale_down = max_sector_weight / total_w
                for sym, w in adjusted_weights.items():
                    if sector_map.get(sym, "Unknown") == sec:
                        adjusted_weights[sym] = w * scale_down

        # Normalize remaining weights to sum to 1.0
        total_sum = sum(adjusted_weights.values())
        if total_sum > 0:
            adjusted_weights = {sym: w / total_sum for sym, w in adjusted_weights.items()}
```

#### `trading_system/tests/test_quad_factor_optimizer.py` (lines 18, 42-45)
```python
        self.symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TSLA', 'META', 'BRK.B']
        self.sector_map = {
            'AAPL': 'Tech', 'MSFT': 'Tech', 'GOOGL': 'Tech', 'AMZN': 'Consumer',
            'NVDA': 'Tech', 'TSLA': 'Consumer', 'META': 'Tech', 'BRK.B': 'Financials'
        }
```
Number of assets: 8. Number of unique sectors: 3 (Tech, Consumer, Financials).

---

## 2. Logic Chain

1. **Infeasible Constraint Setup in Test Suite**:
   In `test_sector_cap_constraint`, `max_sector_weight` is set to `0.25`. The asset pool consists of 8 assets divided into 3 sectors (`Tech`: 5, `Consumer`: 2, `Financials`: 1).
   If sector caps are enforced: $\sum_{i \in Tech} w_i \le 0.25$, $\sum_{i \in Consumer} w_i \le 0.25$, $\sum_{i \in Financials} w_i \le 0.25$.
   The maximum possible total portfolio weight is $\sum w_i \le 0.25 + 0.25 + 0.25 = 0.75$.
   However, the optimization problem requires $\sum w_i = 1.0$.
   Because $0.75 < 1.0$, the equality constraint $\sum w_i = 1.0$ cannot be satisfied simultaneously with sector caps $\le 0.25$.
   This causes the primary QP solver (CVXPY/SciPy), Tier 1 fallback, and Tier 2 fallback to return `None` due to infeasibility.

2. **Flawed Sector Cap Re-normalization Logic**:
   When primary/Tier 1/Tier 2 solvers fail, Tier 3 fallback (`_fallback_equal_weight`) is triggered.
   In `_fallback_equal_weight` (and similarly in `PortfolioOptimizer.apply_factor_and_sector_constraints`), overloaded sectors are scaled down so their sum equals `max_sec_w`.
   This reduces total weight sum $w_{sum}$ below $1.0$ (in this test, $w_{sum} = 0.625$).
   The code then unconditionally re-normalizes all weights by dividing by $w_{sum}$ (`weights /= w_sum`).
   Mathematically, dividing by $w_{sum} < 1.0$ multiplies every sector weight by $1 / w_{sum} > 1.0$.
   Thus, the scaled Tech sector weight (which was 0.25) becomes $0.25 / 0.625 = 0.40$ (40%).
   Subsequent clipping to `max_w = 0.15` in `optimize()` and re-dividing by the new sum (0.85) further inflates Tech sector weight to $0.08 / 0.85 \times 5 = 0.4706$ (47.06%).
   Consequently, the final Tech sector exposure (47.06%) severely violates the 25% cap, leading to the assertion failure in `test_sector_cap_constraint`.

3. **Loss of Neutrality in Fallback**:
   In `test_quad_factor_neutrality_bounds`, the infeasibility triggered Tier 3 fallback, which allocates equal weights without enforcing factor neutrality bounds ($|f^T w| \le 0.05$). Factor size exposure resulted in -0.1557, failing the test.

---

## 3. Caveats

- No code modifications were made during this review (review-only constraint).
- CVXPY environment was available and tested; both CVXPY and SciPy SLSQP primary solvers correctly reported infeasibility when presented with mathematically over-constrained inputs.
- No integrity violations or intentional cheating (hardcoded test results or facade mocks) were found.

---

## 4. Conclusion & Review Summary

**Verdict**: **`REQUEST_CHANGES`**

### Findings Summary

| ID | Severity | Category | Description | Location |
|---|---|---|---|---|
| F-01 | **Critical** | Correctness / Bug | Post-scaling re-normalization in `_fallback_equal_weight` and `apply_factor_and_sector_constraints` multiplies capped sector weights by $1/w_{sum} > 1.0$, breaching sector cap constraints ($\sum_{i \in Sector_k} w_i \le 0.25$). | `src/strategy/quad_factor_optimizer.py:348`, `trading_system/src/risk/portfolio_optimizer.py:191` |
| F-02 | **Critical** | Correctness / Bug | Post-optimization clipping and re-normalization in `QuadFactorOptimizer.optimize()` invalidates single-asset caps `max_weight` and sector caps `max_sector_weight`. | `src/strategy/quad_factor_optimizer.py:167-171` |
| F-03 | **Major** | Test Quality | Test fixture in `test_quad_factor_optimizer.py` specifies 3 sectors with cap 0.25 ($3 \times 0.25 = 0.75 < 1.0$), creating an inherently infeasible constraint problem that guarantees primary QP solver failure. | `trading_system/tests/test_quad_factor_optimizer.py:42-45,81` |

### Required Action Items before Re-review

1. **Fix `_fallback_equal_weight` and `apply_factor_and_sector_constraints`**:
   Implement proper iterative projection / water-filling allocation that redistributes remaining weight capacity to un-capped sectors without re-scaling capped sectors beyond `max_sector_weight`.
2. **Fix `QuadFactorOptimizer.optimize()` post-processing**:
   Ensure normalization preserves inequality bounds ($w_i \le max\_w$ and $\sum_{i \in Sector_k} w_i \le max\_sec\_w$).
3. **Fix `test_quad_factor_optimizer.py` Test Setup**:
   Ensure test sector maps have enough sectors (or appropriate cap parameters) so that $\sum_{k} max\_sec\_w \ge 1.0$ for feasible tests, or explicitly test infeasible behavior separately.

---

## 5. Verification Method

To independently verify the issue and test the fix in future iterations:

1. Execute test suite:
```powershell
.venv\Scripts\python.exe -m pytest trading_system/tests/test_quad_factor_optimizer.py -v
```
2. Verify all 6 tests pass without warnings of fallback failure on feasible test cases.
3. Check that for any output weight dictionary $w$, $\max_k (\sum_{i \in Sector_k} w_i) \le max\_sec\_w + 1e-5$ and $\max_i w_i \le max\_w + 1e-5$.
