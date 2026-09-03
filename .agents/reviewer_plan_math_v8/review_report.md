# Comprehensive Review and Adversarial Audit Report: 37-Strategy Trading System Improvement Plan (v8)

- **Reviewer**: Reviewer 1 (Roles: Quality Reviewer & Adversarial Critic)
- **Review Date**: 2026-09-03
- **Target Deliverable**: `d:\Finance\code\stock\system_improvement_plan_v8.md`
- **Target Repository**: `d:\Finance\code\stock`
- **Working Directory**: `d:\Finance\code\stock\.agents\reviewer_plan_math_v8`

---

## 1. Executive Summary & Verdict

**Verdict**: **REQUEST_CHANGES**

### Verdict Rationale:
The `system_improvement_plan_v8.md` is an exceptionally detailed, technically sophisticated, and largely rigorous document spanning 43 identified defects (13 Critical, 16 High, 14 Medium). Its code citations, line number references, and problem diagnostics across the codebase are remarkably accurate (e.g., verifying the US 1,350x share blow-up in `unified_portfolio_allocator.py:494`, the 20d return vs daily covariance scale collapse in `portfolio_optimizer.py:202`, the global sequence lookahead in `lstm_predictor.py:106`, the missing ROE decay loop in `rim_valuation.py:338`, the database schema truncation in `indicator_storage.py:352`, the double-negative VIX sensitivity in `card_factor.py:174`, and the active test failure in `tests/test_institutional_portfolio_construction.py:193`).

However, from an **adversarial and mathematical rigor** standpoint, several proposed quantitative fixes contain subtle but dangerous mathematical flaws, unintended lookahead leaks, and phrasing risks that must be resolved before this plan can be approved as a production engineering blueprint:

1. **[Critical Math Flaw in CRIT-06] CVaR Small-Universe Bound Box-In**:
   The proposed upper bound $w_i \le \max(\text{max\_single\_weight}, \frac{1.05}{n})$ for $n \le 4$ forces every asset to have weight $w_i \ge 1.0 - (n-1)\frac{1.05}{n}$. For $n=4$, $w_i \ge 21.25\%$, completely depriving the optimizer of the ability to de-allocate (set to 0%) an asset with toxic tail risk.
2. **[Critical Lookahead Leak in CRIT-03] `.bfill()` in "Causal" Normalization**:
   The proposed code in CRIT-03 applies `.bfill()` to rolling mean and standard deviation for the first 20 days. Backward filling transfers day-20 statistics backward to days 0–19, introducing an unadulterated lookahead leak into a module claiming to be "Strict Causal".
3. **[Critical Inversion Explosion Risk in CRIT-09] Non-PSD Pairwise Correlation**:
   Pairwise complete correlation with missing observations produces a matrix that is not guaranteed to be positive semi-definite (PSD). Inverting small negative eigenvalues clipped to $10^{-6}$ will blow up the diagonal of $C^{-1/2}$ by $1000\times$, distorting strategy penalties.
4. **[Integrity / Quality Concern in HIGH-01 Phrasing] Dummy Assertion Representation**:
   While the body of HIGH-01 correctly specifies `assert p_krx["lot_size"] == 1`, the summary tables in lines 1536 and 1632 explicitly state `line 193 KRX 1주 규격 단언 수정 (assert 1 == 1)으로 기존 스위트 100% Pass 달성`. Writing `assert 1 == 1` creates the dangerous impression of introducing a tautological dummy assertion to force a test pass.
5. **[Multi-Currency Architecture Inconsistency] Base Currency Conflict between CRIT-01 and CRIT-07**:
   CRIT-01 assumes the portfolio base currency is KRW and unconditionally divides by USD/KRW for any non-KRX ticker. CRIT-07 introduces USD-denominated accounts ($100,000 USD). If an account is USD-denominated, dividing by USD/KRW again causes a 1,350x under-allocation.

---

## 2. Adversarial Findings & Mathematical Critique

### [Critical Finding 1] CRIT-06: The $1.05/n$ Bound Box-In Destroys CVaR Tail Risk Optimization
- **Location**: `system_improvement_plan_v8.md`, lines 471–476 (CRIT-06)
- **Analysis**:
  The plan correctly diagnoses that when $n \le 4$ and `max_single_weight = 0.20`, the feasible set for $\sum_{i=1}^n w_i = 1.0$ is empty because $\sum w_i \le 4 \times 0.20 = 0.80 < 1.0$.
  To fix this, the plan proposes:
  $$w_i^{max} = \max\left( \text{max\_single\_weight}, \frac{1.05}{n} \right)$$
  Let us stress-test this formula under adversarial conditions:
  - Suppose $n = 4$, and Asset 4 suffers a severe negative tail shock (extreme CVaR). The optimal risk-minimizing strategy is to assign $w_4 = 0$.
  - Under the plan's bound: $w_i^{max} = 1.05 / 4 = 0.2625$.
  - The maximum sum that the remaining 3 assets can achieve is $3 \times 0.2625 = 0.7875 < 1.0$.
  - To satisfy $\sum_{i=1}^4 w_i = 1.0$, Asset 4 **must** receive at least $1.0 - 0.7875 = 0.2125$ ($21.25\%$)!
  - In fact, every single asset is mathematically forced into the narrow band $[21.25\%, 26.25\%]$.
  - For $n=3$, $w_i^{max} = 1.05 / 3 = 0.35$. Each asset is forced into $[30.0\%, 35.0\%]$.
  - For $n=2$, $w_i^{max} = 1.05 / 2 = 0.525$. Each asset is forced into $[47.5\%, 52.5\%]$.
- **Consequence**:
  The proposed bound forces near equal-weighting and forbids the CVaR solver from eliminating high-risk assets from the portfolio.
- **Required Fix**:
  The single-asset bound for small universes must allow at least one asset to be completely excluded. The dynamic bound should be:
  $$w_i^{max} = \min\left( 1.0, \max\left( \text{max\_single\_weight}, \frac{1.0}{\max(n - 1, 1)} \right) \right)$$
  For $n=4$, $w^{max} = 0.3333$ (3 assets can hold 100%, allowing 1 asset to be zeroed out).
  For $n=3$, $w^{max} = 0.50$ (2 assets can hold 100%, allowing 1 asset to be zeroed out).
  For $n=2$, $w^{max} = 1.0$ (1 asset can hold 100%).

---

### [Critical Finding 2] CRIT-03: Backward Fill (`.bfill()`) Leaks Future Data in Causal Normalizer
- **Location**: `system_improvement_plan_v8.md`, line 311 (CRIT-03)
- **Analysis**:
  The plan proposes:
  ```python
  r_mean = df_s[feature_cols].rolling(window=60, min_periods=20).mean().shift(1)
  r_std = df_s[feature_cols].rolling(window=60, min_periods=20).std().shift(1)
  r_std = r_std.fillna(1.0).replace(0.0, 1.0)
  norm_df = ((df_s[feature_cols] - r_mean) / r_std).bfill().fillna(0.0)
  norm_vals = norm_df.values
  ```
  Look at `.bfill()`:
  For the first 20 rows of the historical series ($t < 20$), `r_mean` and `r_std` are `NaN` because `min_periods=20` and `shift(1)`.
  Applying `.bfill()` copies the normalized value from row 21 (which was computed using the mean and std of rows 1 through 20) backward to row 0, row 1, ..., row 20!
  This is a literal backward lookahead leak. In a model named **"Strict Causal LSTM"**, propagating day-20 statistics into day-0 inputs directly violates time-series causality.
- **Required Fix**:
  Replace `.bfill()` with expanding window statistics for the warm-up period, or simply fill initial warm-up NaNs with 0.0:
  ```python
  # True causal standardization without backward propagation
  r_mean = df_s[feature_cols].expanding(min_periods=5).mean().shift(1)
  r_std = df_s[feature_cols].expanding(min_periods=5).std().shift(1).fillna(1.0).replace(0.0, 1.0)
  norm_df = ((df_s[feature_cols] - r_mean) / r_std).fillna(0.0)
  ```

---

### [Critical Finding 3] CRIT-09: Pairwise Incomplete Correlation Matrix Inversion Explosion
- **Location**: `system_improvement_plan_v8.md`, lines 604–608 (CRIT-09)
- **Analysis**:
  The plan replaces `.dropna()` with:
  ```python
  corr_matrix = scores_df[list(valid_cols.values())].apply(pd.to_numeric, errors='coerce').corr(min_periods=5).abs().fillna(0.0)
  np.fill_diagonal(corr_matrix.values, 1.0)
  ```
  In mathematical linear algebra, a correlation matrix estimated from **pairwise complete observations with missing data is NOT guaranteed to be positive semi-definite (PSD)**.
  When some strategy pairs have overlapping observations while others do not, eigenvalues of `corr_matrix` can easily become negative (e.g., $\lambda = -0.08$).
  In `ensemble_scorer.py`:
  ```python
  evals, evecs = np.linalg.eigh(C)
  evals = np.maximum(evals + 1e-4, 1e-6)
  inv_sqrt_C = evecs @ np.diag(1.0 / np.sqrt(evals)) @ evecs.T
  ```
  If $\lambda + 10^{-4} \le 0$, `np.maximum(..., 1e-6)` clips the eigenvalue to $10^{-6}$.
  Then:
  $$\frac{1}{\sqrt{10^{-6}}} = 1,000.0$$
  This creates an enormous phantom penalty ($1000\times$) along the eigenvector associated with the pairwise inconsistency, severely corrupting strategy weights.
  Furthermore, applying `.abs()` blindly penalizes negatively correlated strategies, whereas negatively correlated strategies should be rewarded with higher weights for diversification.
- **Required Fix**:
  1. Project the pairwise correlation matrix to the nearest positive semi-definite matrix (Higham 2002) or apply spectral clipping/ridge regularization:
     `C = (corr_matrix.values + corr_matrix.values.T) * 0.5`
     `evals, evecs = np.linalg.eigh(C)`
     `evals = np.maximum(evals, 0.05)`  # Minimum positive eigenvalue floor to avoid inversion explosion
  2. Do not use `.abs()` on correlation if the objective is true multi-factor diversification.

---

### [Major Finding 4] HIGH-01: Phrasing Risk of Tautological Dummy Assertion (`assert 1 == 1`)
- **Location**: `system_improvement_plan_v8.md`, line 1536 (Section 4.1) and line 1632 (Appendix Checklist)
- **Analysis**:
  In Section 2 (lines 788–794), the plan correctly specifies:
  ```python
  assert p_krx["lot_size"] == 1
  assert p_krx["shares"] >= 0
  assert p_us["lot_size"] == 1
  ```
  However, in line 1536:
  `14. test_institutional_portfolio_construction.py: line 193 KRX 1주 규격 단언 수정 (assert 1 == 1)으로 기존 스위트 100% Pass 달성 (HIGH-01).`
  And in line 1632:
  `line 193 KRX 1주 규격 단언(assert 1 == 1) 수정`
  Writing `assert 1 == 1` in the implementation roadmap creates an appearance of an integrity violation (a dummy assertion that unconditionally passes without asserting the actual property).
- **Required Fix**:
  Update lines 1536 and 1632 to state explicitly:
  `line 193 KRX 1주 규격 단언 수정 (assert p_krx["lot_size"] == 1)` instead of `(assert 1 == 1)`.

---

### [Major Finding 5] CRIT-01 vs CRIT-07: Inconsistent Base Currency Assumptions
- **Location**: `system_improvement_plan_v8.md`, CRIT-01 (lines 130–147) and CRIT-07 (lines 510–522)
- **Analysis**:
  - In CRIT-01, the code assumes `total_portfolio_value` and `alloc_amt_krw` are always KRW, dividing by `usdkrw_rate` for any non-KRX market.
  - In CRIT-07, the system explicitly supports USD-denominated portfolios (`kwargs.get("currency", "KRW") == "USD"`).
  - If a user runs the system on an Interactive Brokers USD account with `total_portfolio_value = 100,000` (USD), `alloc_amt` for AAPL is $5,000 USD.
  - If CRIT-01 unconditionally runs `alloc_amt_local = alloc_amt_krw / usdkrw_rate`, it will divide $5,000 USD by 1,350, allocating only $3.70 USD (0 shares) instead of $5,000 USD!
  - Furthermore, `is_us = mkt in ["SP500", "NASDAQ", "RUSSELL2000", "US"] or not is_krx` assumes all non-KRX markets trade in USD. If Japanese or Hong Kong assets are evaluated, dividing JPY prices by USD/KRW rate will cause extreme currency distortions.
- **Required Fix**:
  In `unified_portfolio_allocator.py:allocate()`, pass `base_currency: str = "KRW"`.
  Only convert if `base_currency == "KRW"` and `asset_currency == "USD"`.

---

### [Major Finding 6] CRIT-04: Removal of the 2% Minimum ROE Decay Floor Allows Zero-Decay Perpetuity Bubble
- **Location**: `system_improvement_plan_v8.md`, line 360 (CRIT-04)
- **Analysis**:
  The existing code in `rim_valuation.py:336` enforced:
  `eff_decay = max(0.02, float(self.decay_rate)) if self.decay_rate > 0 else 0.05`
  The plan replaces this with:
  `eff_decay = float(np.clip(self.decay_rate, 0.0, 0.50))`
  If a configuration or environment variable sets `decay_rate = 0.0`:
  Then `eff_decay = 0.0`, `omega = 1.0`, and `denom_tv = 1.0 + r_e - 1.0 = r_e`.
  Terminal value becomes a perpetual stream of non-decaying excess income:
  $$TV = \frac{BPS_T (ROE_0 - r_e)}{r_e}$$
  For a high ROE firm ($ROE = 30\%$), this recreates the exact valuation bubble that the Ohlson decay model was designed to prevent.
- **Required Fix**:
  Maintain a non-zero floor for `eff_decay` (e.g., `np.clip(self.decay_rate, 0.02, 0.50)`).

---

## 3. Verification of Claims, Code Citations & Line Numbers

Each cited file was spot-checked against the actual repository codebase:

| File Cited in Plan | Plan Line Reference | Actual Codebase Line & Content | Verification Status | Notes |
|---|---|---|---|---|
| `src/risk/unified_portfolio_allocator.py` | Line 494–506 | Line 494–506: `raw_shares = int(alloc_amt // px)` | **VERIFIED (100% Exact)** | US shares calculated without FX scaling. |
| `src/risk/unified_portfolio_allocator.py` | Line 136–166 | Line 136–166: `bounds = [(0.0, self.max_single_weight)...]` | **VERIFIED (100% Exact)** | For $n \le 4$, $4 \times 0.20 = 0.80 < 1.0$, solver fails. |
| `src/risk/unified_portfolio_allocator.py` | Line 259–277 | Line 259–277: `w_damped / s_damp` | **VERIFIED (100% Exact)** | Market impact dampening neutralized by post-hoc re-normalization. |
| `src/analysis/portfolio_optimizer.py` | Line 202–255 | Line 202–255: `Pi = risk_aversion * (horizon_cov @ w_eq)` | **VERIFIED (100% Exact)** | Daily covariance combined with 20d return $Q$. |
| `src/ai/lstm_predictor.py` | Line 106–112 | Line 106–112: `std = np.std(vals); (vals - mean)/std` | **VERIFIED (100% Exact)** | Global normalization across entire multi-year series. |
| `src/core/rim_valuation.py` | Line 338–359 | Line 338–359: `current_roe = roe` outside loop | **VERIFIED (100% Exact)** | `current_roe` never updated inside the projection loop. |
| `src/data_layer/indicator_storage.py` | Line 352, 1224, 1579 | Line 352, 1224, 1579: Ends at `earnings_tone_drift_score` | **VERIFIED (100% Exact)** | Strategies 32–37 completely missing from DB persistence. |
| `src/core/card_factor.py` | Line 174 | Line 174: `- model.params.get('VIX', 0.0) * vix_pct_shock` | **VERIFIED (100% Exact)** | Double-negative sign bug confirmed. |
| `src/ai/ensemble_scorer.py` | Line 967–969 | Line 967–969: `subset_df = ... .dropna()` | **VERIFIED (100% Exact)** | Drops all rows if any strategy is NaN; bypasses if $<10$. |
| `src/ai/ml_strategy_adapters.py` | Line 373–375 | Line 373–375: Instantiates `MicrostructureImbalanceEngine` | **VERIFIED (100% Exact)** | Facade implementation confirmed. |
| `src/ai/factor_orthogonalizer.py` | Line 226–235 | Line 226–235: Comment states PC1=1.0, code applies $1/\sqrt{\lambda}$ | **VERIFIED (100% Exact)** | PC1 retention commented but not implemented. |
| `src/execution/oms_engine.py` | Line 768–773 | Line 768–773: `first_market = top_predictions[0]...` | **VERIFIED (100% Exact)** | Single-market bias for synthetic inverse hedge. |
| `src/execution/slippage_feedback.py` | Line 186–220 | Line 186–220: $N=1$ outlier triggers 8.0x multiplier | **VERIFIED (100% Exact)** | Lack of shrinkage on small sample confirmed. |
| `tests/test_institutional_portfolio_construction.py` | Line 193 | Line 193: `assert p_krx["lot_size"] == 10` | **VERIFIED (100% Exact)** | Test currently fails with `assert 1 == 10`. |

---

## 4. Completeness of the 4-Stage Structure

A programmatic audit of `system_improvement_plan_v8.md` verified that **every single one of the 43 items** (13 Critical, 16 High, 14 Medium) strictly adheres to the mandated 4-stage format:
- `#### 1. 현황 및 문제점`
- `#### 2. 정량적/공학적 개선 방안`
- `#### 3. 수정 대상 파일`
- `#### 4. 검증 방안`

Compliance rate: **100% (43 / 43 items)**.

---

## 5. Mathematical & Algorithmic Rigor Evaluation

| Item | Formula / Formulation Evaluated | Rigor Assessment | Finding |
|---|---|---|---|
| **CRIT-01** | $A_i^{local} = A_i^{KRW} / FX_i$, $S_i = \lfloor A_i^{local} / (P_i \cdot lot) \rfloor \cdot lot$ | Good, but needs base currency guard | See Major Finding 5 |
| **CRIT-02** | Black-Litterman 20d $Q$ vs daily $\Sigma$: $Q_{daily} = Q / 20$ | **Exact and mathematically sound** | Return scaling is linear ($1/20 Q$), not $\sqrt{20}$. Units match $\Sigma_{daily}$. |
| **CRIT-03** | Rolling causal normalization of LSTM sequences | **Flawed in `.bfill()`** | See Critical Finding 2 |
| **CRIT-04** | Ohlson 1995 ROE linear decay dynamics: $ROE_t = r_e + (ROE_{t-1} - r_e)(1 - \text{eff\_decay})$ | **Sound algebra, but decay floor needed** | See Major Finding 6 |
| **CRIT-06** | CVaR linear programming bound feasibility for $n \le 4$ | **Flawed in $1.05/n$** | See Critical Finding 1 |
| **CRIT-09** | Löwdin symmetric orthogonalization: $C^{-1/2} = V \Lambda^{-1/2} V^T$ | **Flawed in non-PSD inversion** | See Critical Finding 3 |
| **CRIT-11** | ZCA Whitening PC1 consensus retention: $\text{filter}[-1] = 1.0$, max condition cap 10.0 | **Exact and mathematically sound** | Eigenvalues from `eigh` are ascending; `[-1]` is $\lambda_{\max}$. |
| **CRIT-12** | OLS Macro sensitivity: $\Delta \hat{R} = \beta_{FX}\Delta FX + \beta_{WTI}\Delta WTI + \beta_{VIX}\Delta VIX$ | **Exact and mathematically sound** | Eliminates double-negative sign flip. |
| **HIGH-15** | EVT-CVaR Cornish-Fisher Expected Shortfall tail integration | **Exact and mathematically sound** | Correctly identifies that $VaR \ne CVaR$. |
| **HIGH-16** | Gatheral 3/2 power law cost: $I \sim v^{1.5}$, Hard participation cap $5\%$ ADV | **Exact and mathematically sound** | Replaces unstable heuristic dampening with hard constraint. |

---

## 6. Required Action Items for Approval

To achieve full approval, the plan author must apply the following revisions to `system_improvement_plan_v8.md`:

1. **Fix CRIT-06**:
   Revise $w_i^{max} = \max(\text{max\_single\_weight}, \frac{1.05}{n})$ to:
   $$w_i^{max} = \min\left(1.0, \max\left(\text{max\_single\_weight}, \frac{1.0}{\max(n - 1, 1)}\right)\right)$$
   and explain the degrees of freedom required for asset selection.
2. **Fix CRIT-03**:
   Remove `.bfill()` from the causal standardization snippet and replace with expanding window statistics during warm-up.
3. **Fix CRIT-09**:
   Add PSD projection / minimum eigenvalue floor ($\lambda_{min} \ge 0.05$) to prevent $1000\times$ inversion explosion on pairwise incomplete correlation matrices.
4. **Fix HIGH-01 Phrasing**:
   Replace `(assert 1 == 1)` in lines 1536 and 1632 with `(assert p_krx["lot_size"] == 1)`.
5. **Fix CRIT-01 Currency Architecture**:
   Add `base_currency: str = "KRW"` to `allocate()` and ensure conversion only occurs when converting between different currencies.
6. **Fix CRIT-04 Decay Floor**:
   Enforce a minimum decay floor of $0.02$ (`np.clip(self.decay_rate, 0.02, 0.50)`).

Once these 6 targeted adjustments are incorporated into `system_improvement_plan_v8.md`, the plan will meet the highest standards of institutional quantitative rigor.
