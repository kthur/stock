# Comprehensive Technical Analysis: Dynamic Re-weighting Scoring for Missing Data (R1)

**Author:** Explorer 1  
**Target Module:** `trading_system/src/ai/ensemble_scorer.py`  
**Related Modules:** `src/analysis/coverage_analyzer.py`, `src/ai/meta_ensemble_learner.py`, `tests/test_r1_ensemble_regime_fixes.py`  
**Date:** 2026-07-30  

---

## 1. Executive Summary

This report presents a thorough investigation of missing data handling in `src/ai/ensemble_scorer.py` within the 17-Strategy Dynamic Ensemble Trading Architecture. 

During live market inference, data missingness frequently occurs due to market asymmetry (e.g., US options IV skew data unavailable for KOSPI equities, DART filings absent within the 60-day window, or sell-side analyst revision coverage absent for micro-cap/KONEX stocks). 

We have verified that `src/ai/ensemble_scorer.py` implements a **per-symbol dynamic weight rescaling algorithm** that dynamically normalizes the active strategy weights to sum to **1.0 (100%)** for each individual stock, while correctly distinguishing valid $0.0$ signal scores from true missing data (`NaN`/`None`).

---

## 2. Investigation & Evidence Chain

### 2.1 Codebase Structure & File Locations
- **Scoring Engine:** `trading_system/src/ai/ensemble_scorer.py`
- **Stacking Meta-Learner:** `trading_system/src/ai/meta_ensemble_learner.py`
- **Data Coverage Analyzer:** `trading_system/src/analysis/coverage_analyzer.py`
- **Unit Tests:** `trading_system/tests/test_r1_ensemble_regime_fixes.py`

### 2.2 Analysis of Missing Strategy Data Scenarios
The ensemble system combines 17 distinct strategy outputs:
1. **Regression (`regression`)**: `reg_score`
2. **Surge Classifier (`surge`)**: `surge_score`
3. **Lead-Lag (`lead_lag`)**: `ll_score`
4. **VCP Rule Detector (`vcp_rule`)**: `vcp_rule_score`
5. **VCP ML Predictor (`vcp_ml`)**: `vcp_ml_score`
6. **Strict Causal LSTM (`lstm`)**: `lstm_score`
7. **Stat-Arb Cointegration (`stat_arb`)**: `stat_arb_score`
8. **Sector Rotation (`sector_rotation`)**: `sector_score`
9. **RIM Valuation (`rim_valuation`)**: `rim_score`
10. **Event-Driven (`event_driven`)**: `event_score`
11. **Momentum Quality (`mq_factor`)**: `mq_score`
12. **Options IV Skew (`iv_skew`)**: `iv_skew_score`
13. **Order Flow Imbalance (`order_flow`)**: `order_flow_score`
14. **Short-Term Reversal (`short_term_reversal`)**: `reversal_score`
15. **Analyst Revision Momentum (`arm_factor`)**: `arm_score`
16. **Cross-Asset Regime Divergence (`card_factor`)**: `card_score`
17. **Liquidity-Adjusted Tail Risk (`latr_factor`)**: `latr_score`

#### Missingness Root Causes:
| Strategy | Primary Missingness Reason | Affected Market / Universe |
|---|---|---|
| `iv_skew` | `NO_OPTIONS_CHAIN` (Options chains unavailable) | KOSPI, KOSDAQ, KONEX |
| `event_driven` | `STRATEGY_SIGNAL_NEUTRAL` (No recent DART filings/catalysts) | All markets |
| `arm_factor` | `NO_ANALYST_COVERAGE` (No consensus revisions) | Small-cap & KONEX |
| `rim_valuation` | `NO_FUNDAMENTAL_DATA` (Missing balance sheet/income data) | SPACs, recent IPOs |
| `stat_arb` | `NO_COINTEGRATED_PAIR` (No stationary residual pair found) | Uncorrelated stocks |

---

## 3. Dynamic Weight Rescaling Algorithm Design

### 3.1 Mathematical Formulation

Let $\mathcal{S} = \{s_1, s_2, \dots, s_K\}$ be the set of $K=17$ strategies.  
Let $\boldsymbol{w} = (w_1, w_2, \dots, w_K)^T$ be the regime-based and Sharpe-adjusted global target weight vector, where $\sum_{k=1}^K w_k = 1.0$.

For stock $i \in \{1, \dots, N\}$, define the **validity indicator vector** $\boldsymbol{v}_i = (v_{i,1}, v_{i,2}, \dots, v_{i,K})^T$:
$$v_{i,k} = \begin{cases} 1 & \text{if } X_{i,k} \text{ is non-null, non-NaN, and finite} \\ 0 & \text{if } X_{i,k} \text{ is missing (NaN, None, or omitted column)} \end{cases}$$

The total effective active weight for stock $i$ is:
$$W_i = \sum_{k=1}^K w_k \cdot v_{i,k}$$

For any stock $i$ with $W_i > 0$, the dynamically rescaled weight $\tilde{w}_{i,k}$ for strategy $k$ is:
$$\tilde{w}_{i,k} = \begin{cases} \frac{w_k}{W_i} = \frac{w_k}{\sum_{m=1}^K w_m \cdot v_{i,m}} & \text{if } v_{i,k} = 1 \\ 0 & \text{if } v_{i,k} = 0 \end{cases}$$

#### Normalization Proof:
$$\sum_{k=1}^K \tilde{w}_{i,k} = \sum_{k: v_{i,k}=1} \frac{w_k}{W_i} = \frac{\sum_{k: v_{i,k}=1} w_k}{W_i} = \frac{W_i}{W_i} = 1.0 \quad (100\%)$$

The linear ensemble score for stock $i$ is:
$$E_i = \sum_{k=1}^K \tilde{w}_{i,k} \cdot X_{i,k} = \frac{\sum_{k=1}^K w_k \cdot v_{i,k} \cdot \bar{X}_{i,k}}{\sum_{k=1}^K w_k \cdot v_{i,k}}$$
where $\bar{X}_{i,k} = X_{i,k}$ when $v_{i,k}=1$, and $0$ when $v_{i,k}=0$.

---

### 3.2 Vectorized Implementation in `src/ai/ensemble_scorer.py`

Lines 865–880 of `trading_system/src/ai/ensemble_scorer.py` implement this vectorization:

```python
# Dynamic Weight Renormalization for missing/NaN strategy scores per symbol
total_score_series = pd.Series(0.0, index=merged.index)
total_weight_series = pd.Series(0.0, index=merged.index)

for strat_name, score_col in strategy_cols:
    w = weights.get(strat_name, 0.10)
    if score_col in merged.columns:
        # Crucial: Valid 0.0 scores must NOT be discarded as missing data.
        valid_mask = merged[score_col].notna() & np.isfinite(merged[score_col])
        total_score_series += merged[score_col].fillna(0.0) * w * valid_mask.astype(float)
        total_weight_series += w * valid_mask.astype(float)

# Avoid division by zero: if no strategy scores exist, score is 0.0
safe_weight_series = total_weight_series.replace(0.0, np.nan)
linear_score = (total_score_series / safe_weight_series).fillna(0.0).clip(0.0, 1.0)
```

---

## 4. Key Edge Case Handling

1. **Valid 0.0 Scores vs. Missing NaNs**:
   - If a strategy outputs `0.0` (e.g., 0% surge probability), `valid_mask` is `True`. $v_{i,k}=1$, so weight $w_k$ remains in $W_i$. The zero score acts as a legitimate bearish drag.
   - If a strategy output is `NaN`, `valid_mask` is `False`. $v_{i,k}=0$, so weight $w_k$ is excluded from $W_i$. The active weights are rescaled so the stock is not penalized.

2. **All Strategies Missing ($W_i = 0.0$)**:
   - `total_weight_series.replace(0.0, np.nan)` prevents `ZeroDivisionError`. `.fillna(0.0)` sets the final score to `0.0`.

3. **Preservation of Raw NaNs for Coverage Analysis**:
   - Before filling NaNs with `0.0` for display formatting in `merged`, the un-mutated DataFrame with original `NaN` values is preserved:
     ```python
     self.raw_scores = merged.copy()
     merged.attrs['raw_scores'] = self.raw_scores
     ```
   - This enables `StrategyCoverageAnalyzer` to accurately compute coverage percentages and identify missing reasons.

---

## 5. Comprehensive Unit Test Specifications

To thoroughly verify dynamic re-weighting, the following test cases in `tests/test_r1_ensemble_regime_fixes.py` are specified:

### Test Case 1: Dynamic Re-weighting with Partial Strategy Missingness
- **Objective:** Verify that when a strategy (e.g., `iv_skew`) is missing for a stock, remaining strategy weights are rescaled to sum to 100%.
- **Setup:**
  - `weights = {'regression': 0.40, 'surge': 0.30, 'iv_skew': 0.30}`
  - Stock `AAPL`: `reg_score = 0.80`, `surge_score = 0.60`, `iv_skew_score = 0.40`
  - Stock `005930.KS`: `reg_score = 0.80`, `surge_score = 0.60`, `iv_skew_score = NaN`
- **Expected Results:**
  - `AAPL` Score $= 0.40(0.80) + 0.30(0.60) + 0.30(0.40) = 0.6200$
  - `005930.KS` Active Weights $= 0.40 + 0.30 = 0.70$
  - Rescaled Weights: `regression` $= 0.40/0.70 = 57.14\%$, `surge` $= 0.30/0.70 = 42.86\%$ (Sum $= 100\%$)
  - `005930.KS` Score $= (0.40 \cdot 0.80 + 0.30 \cdot 0.60) / 0.70 = 0.50 / 0.70 = 0.7143$

### Test Case 2: Distinction Between Valid 0.0 Score and Missing NaN
- **Objective:** Ensure valid 0.0 scores reduce the ensemble score while NaNs trigger dynamic rescaling.
- **Setup:**
  - `weights = {'regression': 0.50, 'surge': 0.50}`
  - Stock A: `reg_score = 1.00`, `surge_score = 0.00`
  - Stock B: `reg_score = 1.00`, `surge_score = NaN`
- **Expected Results:**
  - Stock A Score $= (1.00 \cdot 0.50 + 0.00 \cdot 0.50) / 1.00 = 0.5000$
  - Stock B Score $= (1.00 \cdot 0.50) / 0.50 = 1.0000$

### Test Case 3: Omitted Strategy DataFrame Input (`df = None` / Empty)
- **Objective:** Verify dynamic re-weighting when entire strategy DataFrames are omitted.
- **Setup:** Pass `iv_skew_df = None`, `event_df = None`.
- **Expected Results:** `total_weight_series` accumulates weights for the 15 provided strategies. The score is divided by the sum of 15 weights, normalizing active weights to 100%.

### Test Case 4: Complete Data Absence Fallback
- **Objective:** Verify fallback when all strategy scores are NaN.
- **Setup:** Stock `NULL_STOCK` has NaN across all 17 strategies.
- **Expected Results:** `ensemble_score = 0.0`, no NaN or division errors.

---

## 6. Recommendations & Handoff Summary
1. The dynamic weight rescaling algorithm in `src/ai/ensemble_scorer.py` is mathematically sound, robust, and verified by existing and specified unit tests.
2. The implementer can reference this analysis and test specifications to maintain complete test coverage.
