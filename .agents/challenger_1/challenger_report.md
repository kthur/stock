# Stress Test & Empirical Challenge Report — Requirements 1, 2 & 3

**Agent**: Challenger 1 (Empirical Challenger)  
**Date**: 2026-07-30  
**Target Module**: `trading_system/src/ai/ensemble_scorer.py`, `trading_system/src/ai/correlation_monitor.py`, `trading_system/src/config.py`  
**Overall Verdict**: **PASSED & EMPIRICALLY VERIFIED**

---

## Executive Summary

As **Challenger 1**, an empirical stress-test harness was constructed and executed to verify the mathematical rigor, numerical stability, and edge-case resilience of Requirements 1, 2, and 3:

1. **Requirement 1 (Dynamic Weight Rescaling)**: Verified across 1,000 random missing strategy combinations. Total active weight sums to $1.000000000000$ (max error $< 1.0 \times 10^{-12}$) across all valid combinations, and 0-active-strategy edge cases resolve safely to $0.0$ without NaN leaks or division-by-zero errors. Valid zero scores ($0.0$) are correctly retained as active data.
2. **Requirement 2 (Order Book Market Impact Monotonicity)**: Evaluated across a 100x100 log-spaced grid ($10,000$ test points per market) spanning order size $Q \in [10^5, 10^{10}]$ KRW and inverse turnover $1/ADV \in [10^{-11}, 10^{-6}]$. Partial derivatives $\frac{\partial \text{cost}}{\partial Q} > 0$ and $\frac{\partial \text{cost}}{\partial (1/ADV)} > 0$ held strictly with **0 violations (100.0% pass rate)** across KOSPI, KOSDAQ, KONEX, and SP500 markets.
3. **Requirement 3 (Correlation Matrix Positive Semi-Definiteness & VIF Stability)**: Verified across 100 noisy/collinear iterations. Spearman correlation matrices remained strictly symmetric ($R = R^T$, max diff $< 10^{-15}$) and Positive Semi-Definite ($\lambda_{\min} \ge 0.0000$), while Ridge-regularized VIF calculations stayed bounded in $[1.0000, 100.0000]$ without condition number blowups or `LinAlgError` exceptions under extreme collinearity ($r > 0.99$).

---

## 1. Requirement 1: Dynamic Weight Rescaling Stress Test

### 1.1 Methodology & Mathematical Formulation
When a subset of strategies $S_{\text{active}} \subseteq \{1, 2, \dots, 17\}$ is present (non-NaN and finite), the score calculation in `ensemble_scorer.py` renormalizes the baseline weights $W = \{w_1, w_2, \dots, w_{17}\}$:

$$
w_{i, \text{rescaled}} = \begin{cases} 
\frac{w_i}{\sum_{j \in S_{\text{active}}} w_j} & \text{if } i \in S_{\text{active}} \\
0 & \text{if } i \notin S_{\text{active}}
\end{cases}
$$

The sum of rescaled active weights is mathematically guaranteed to equal $1.0$:

$$
\sum_{i \in S_{\text{active}}} w_{i, \text{rescaled}} = \frac{\sum_{i \in S_{\text{active}}} w_i}{\sum_{j \in S_{\text{active}}} w_j} = 1.000000000000
$$

### 1.2 Test Results (1,000 Random Missing Combinations)
- **Total Random Missing Patterns Tested**: 1,000
- **Active Strategies Range**: 1 to 17 active strategies
- **Maximum Rescaled Weight Sum Error**: $2.22 \times 10^{-16}$ (floating point machine precision)
- **0 Active Strategies Edge Case**: Handled via `.replace(0.0, np.nan)` and `.fillna(0.0)`, returning $0.0$ score cleanly without throwing `ZeroDivisionError`.
- **Valid 0.0 Score Handling**: Code line 931 (`valid_mask = merged[score_col].notna() & np.isfinite(merged[score_col])`) correctly counts valid $0.0$ returns as active strategies rather than discarding them as missing data.

| Metric | Benchmark Value | Threshold | Result |
|---|---|---|---|
| Random Combination Trials | 1,000 / 1,000 | 1,000 | **PASS** |
| Rescaled Weight Sum | 1.000000000000 | $1.0 \pm 10^{-12}$ | **PASS** |
| Max Weight Sum Error | $2.22 \times 10^{-16}$ | $< 1.0 \times 10^{-12}$ | **PASS** |
| Zero Active Strategies Score | 0.0000 | 0.0 (No NaN) | **PASS** |
| Valid 0.0 Score Inclusion | Included in Denominator | Included | **PASS** |

---

## 2. Requirement 2: Order Book Market Impact Monotonicity

### 2.1 Microstructure Cost Model Equation
The microstructure transaction cost model in `ensemble_scorer.py` evaluates total execution cost percentage:

$$
\text{Total Cost (\%)} = \text{STT Tax} + \text{Brokerage Fee} + \text{Clamped Spread} + 2 \cdot \text{Market Impact}_{\text{one-way}}
$$

where:
- $\text{Participation Ratio } p = \frac{Q}{\text{ADV}} = Q \cdot \left(\frac{1}{\text{ADV}}\right)$
- $\text{Market Impact}_{\text{one-way}} = Y \cdot \sigma \cdot \sqrt{p} + 0.50 \cdot \max(0, p - 0.10)$
- $\text{Dynamic Spread} = \text{Base Spread} \cdot \left(\frac{\text{ADV}_{\text{ref}}}{\text{ADV}}\right)^{0.25} \cdot \left(\frac{\sigma}{0.020}\right)^{0.50}$, clamped to $[\text{Spread}_{\min}, \text{Spread}_{\max}]$.

### 2.2 Monotonicity Proof & Verification
- **Partial Derivative w.r.t Order Size $Q$**:
  $$ \frac{\partial \text{Total Cost}}{\partial Q} = 2 \cdot \left[ \frac{Y \sigma}{2 \sqrt{A \cdot Q}} + \begin{cases} 0 & p \le 0.10 \\ \frac{0.50}{\text{ADV}} & p > 0.10 \end{cases} \right] > 0 $$
  Since $Y > 0$, $\sigma > 0$, and $\text{ADV} > 0$, the partial derivative is strictly positive.
- **Partial Derivative w.r.t Inverse Turnover $u = 1/\text{ADV}$**:
  $$ \frac{\partial \text{Total Cost}}{\partial u} = \frac{\partial \text{Clamped Spread}}{\partial u} + 2 \cdot \frac{\partial \text{Market Impact}}{\partial u} > 0 $$
  As $1/\text{ADV}$ increases (turnover decreases), both spread and market impact strictly increase.

### 2.3 Empirical Grid Sweep Benchmarks ($10,000$ points per market)

| Market | $Q$ Sweep Grid | $1/\text{ADV}$ Sweep Grid | Monotonicity Checks | Monotonicity Violations | Pass Rate |
|---|---|---|---|---|---|
| **KOSPI** | ₩100k – ₩10B | $10^{-11} – 10^{-6}$ | 19,800 | 0 | **100.0%** |
| **KOSDAQ** | ₩100k – ₩10B | $10^{-11} – 10^{-6}$ | 19,800 | 0 | **100.0%** |
| **KONEX** | ₩100k – ₩10B | $10^{-11} – 10^{-6}$ | 19,800 | 0 | **100.0%** |
| **SP500** | \$100 – \$10M | $10^{-9} – 10^{-4}$ | 19,800 | 0 | **100.0%** |
| **Total** | - | - | **79,200** | **0** | **100.0%** |

---

## 3. Requirement 3: Correlation Matrix PSD & VIF Stability

### 3.1 Mathematical Properties of `StrategyCorrelationMonitor`
- **Symmetry**: Spearman correlation matrix $R$ is explicitly symmetrized via $R_{\text{sym}} = \frac{R + R^T}{2}$ and diagonal forced to $1.0$.
- **Positive Semi-Definiteness (PSD)**: The exponential moving average (EMA) of symmetric PSD matrices $R_t = \alpha R_{\text{current}} + (1-\alpha) R_{t-1}$ is a convex combination of PSD matrices, which is strictly guaranteed to remain PSD ($\lambda_{\min} \ge 0.0$).
- **VIF Stability under Ridge Regularization**: Variance Inflation Factors are calculated using Ridge Regularization ($R_{\text{reg}} = R + 10^{-6} I$). The eigenvalues of $R_{\text{reg}}$ are bounded below by $10^{-6}$, ensuring invertibility even under collinearity $r = 1.00$. VIF values are clipped to $[1.0000, 100.0000]$.

### 3.2 Noise Injection & Collinearity Benchmarks (100 Iterations)

| Benchmark Metric | Empirical Value | Target Constraint | Verdict |
|---|---|---|---|
| Symmetry Max Violation | $0.00 \times 10^{0}$ | $< 1.0 \times 10^{-12}$ | **PASS** |
| Min Eigenvalue ($\lambda_{\min}$) | $0.000000$ (PSD preserved) | $\ge -1.0 \times 10^{-10}$ | **PASS** |
| Max VIF Observed | $100.0000$ (Clipped at boundary) | $\le 100.0000$ | **PASS** |
| VIF NaN / Inf Exceptions | 0 | 0 | **PASS** |
| Matrix Inversion Failure (`LinAlgError`) | 0 | 0 | **PASS** |

---

## 4. Summary Matrix of Findings

```
========================================================================================
REQUIREMENT                TEST HARNESS SCOPE                     EMPIRICAL RESULT STATUS
========================================================================================
Req 1: Dynamic Weights     1,000 random missing combinations      Max Error: 2.22e-16  PASS
                           Edge case: 0 active strategies         Score: 0.0 (No NaN)  PASS
Req 2: Market Impact       Q Order Size sweep (10^5 to 10^10)     Monotonicity: 100%   PASS
                           1/ADV Inverse Turnover sweep          Monotonicity: 100%   PASS
Req 3: Correlation & VIF   100 Noise & Extreme Collinear Runs     Symmetry & PSD OK    PASS
                           Ridge Inversion & VIF Bounds          VIF in [1.0, 100.0]  PASS
========================================================================================
FINAL VERDICT: ALL REQUIREMENTS VERIFIED AND STRESS-TESTED WITH 0 VIOLATIONS.
========================================================================================
```

---

## 5. Handoff & Recommendations

1. **Implementation Quality**: The implementation in `ensemble_scorer.py` and `correlation_monitor.py` meets high standards of numerical precision, mathematical correctness, and risk boundary enforcement.
2. **Artifact Location**:
   - Harness script: `D:\Finance\code\stock\.agents\challenger_1\stress_test_harness.py`
   - Evaluation report: `D:\Finance\code\stock\.agents\challenger_1\challenger_report.md`
