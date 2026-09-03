# Handoff Report: Mathematical & Algorithmic Audit of System Improvement Plan v8

- **Agent ID**: Reviewer 1 (`reviewer_plan_math_v8`)
- **Target Plan**: `d:\Finance\code\stock\system_improvement_plan_v8.md`
- **Verdict**: **REQUEST_CHANGES**

---

## 1. Observation

Direct observations and evidence obtained during the audit:

1. **Active Test Suite Failure (HIGH-01)**:
   - Tool Command: `.venv\Scripts\pytest tests/test_institutional_portfolio_construction.py -v`
   - Result:
     ```
     FAILED tests/test_institutional_portfolio_construction.py::TestUnifiedPortfolioAllocatorEndToEnd::test_end_to_end_allocate - assert 1 == 10
     ======================== 1 failed, 7 passed in 10.55s =========================
     ```
   - In `tests/test_institutional_portfolio_construction.py:193`, `assert p_krx["lot_size"] == 10` failed because `unified_portfolio_allocator.py:501` correctly assigns `lot = 1 if is_krx else ...`.
   - In `system_improvement_plan_v8.md` lines 1536 and 1632, the summary text describes the fix as `(assert 1 == 1)` rather than asserting the actual property `assert p_krx["lot_size"] == 1`.

2. **Code Citations and Line Number Precision**:
   - `unified_portfolio_allocator.py:494-506`: `raw_shares = int(alloc_amt // px)` divides KRW by USD price directly without `fx_rate`.
   - `unified_portfolio_allocator.py:136-166`: `bounds = [(0.0, self.max_single_weight)...]`. For $n \le 4$, $\sum w_i \le 4 \times 0.20 = 0.80 < 1.0$, rendering SLSQP optimization 100% infeasible.
   - `portfolio_optimizer.py:202-213`: `Pi = risk_aversion * (horizon_cov @ w_eq)` where `horizon_cov` is daily ($\sim 0.0004$), whereas `predicted_returns` is 20-day cumulative ($\sim 0.05$).
   - `lstm_predictor.py:106-112`: `vals = group_sorted[f].fillna(0.0).values; std = np.std(vals); vals = (vals - np.mean(vals)) / std` standardizes across the entire multi-year series.
   - `rim_valuation.py:338-359`: `current_roe = roe` is set outside the loop and never updated within the projection loop, applying constant ROE for all $T$ years.
   - `indicator_storage.py:352, 1224, 1579`: Table schema and insert statements terminate at `earnings_tone_drift_score` (Strategy 31), omitting Strategies 32–37.
   - `card_factor.py:174`: `macro_impact = (... - model.params.get('VIX', 0.0) * vix_pct_shock)`. Double-negative sign bug verified.
   - `ensemble_scorer.py:967-969`: `subset_df = scores_df[...].dropna()`. If `len(subset_df) < 10`, silently returns unadjusted weights.
   - `ml_strategy_adapters.py:373-375`: `from src.core.hft_engine import MicrostructureImbalanceEngine`. Facade implementation confirmed.
   - `factor_orthogonalizer.py:226-235`: Code applies `whitening_filter = 1.0 / np.sqrt(lambdas_clean + ridge_eps)` to all components despite comment to retain PC1.

3. **Structural Completeness**:
   - Verified via Python AST parsing that all 43 items (13 Critical, 16 High, 14 Medium) contain the exact 4-stage headings: `1. 현황 및 문제점`, `2. 정량적/공학적 개선 방안`, `3. 수정 대상 파일`, `4. 검증 방안`.

4. **Flaws in Proposed Solutions**:
   - CRIT-06 proposes $w_i^{max} = \max(\text{max\_single\_weight}, \frac{1.05}{n})$. For $n=4$, $w_i^{max} = 0.2625$. The minimum possible weight for any asset is $1.0 - 3 \times 0.2625 = 0.2125$. The solver cannot assign $w=0$ to a high-tail-risk asset.
   - CRIT-03 proposes `.bfill()` on rolling statistics: `((df_s[feature_cols] - r_mean) / r_std).bfill().fillna(0.0)`. This backward-fills day-20 statistics into days 0–19.
   - CRIT-09 proposes pairwise complete correlation `.corr(min_periods=5)`. Pairwise correlation matrices with missing data are not guaranteed to be positive semi-definite; near-zero negative eigenvalues clipped to $10^{-6}$ will blow up $C^{-1/2}$ by $1000\times$.

---

## 2. Logic Chain

1. **Observation 1 & 2 $\to$ Diagnostic Accuracy**: The defects cataloged in `system_improvement_plan_v8.md` are genuine, critical, and precisely located in the codebase.
2. **Observation 4 (CRIT-06) $\to$ Optimization Impairment**: In portfolio optimization, risk management models must have the mathematical freedom to divest from high-risk assets ($w_i = 0$). Imposing $w_i^{max} = 1.05/n$ forces an artificial floor of $w_i \ge 1.0 - (n-1)\frac{1.05}{n}$ on all assets. When $n=4$, every asset must hold at least $21.25\%$, disabling CVaR tail-risk de-allocation.
3. **Observation 4 (CRIT-03) $\to$ Lookahead Leakage**: A "Strict Causal" LSTM model must not use any future data. Applying `.bfill()` to rolling window statistics leaks statistics from $t=20$ backward to $t < 20$.
4. **Observation 4 (CRIT-09) $\to$ Matrix Inversion Instability**: In Löwdin orthogonalization, $C^{-1/2} = V \Lambda^{-1/2} V^T$. When $C$ is computed from pairwise incomplete observations, negative eigenvalues violate PSD conditions. Clipping them to $10^{-6}$ results in an artificial $1000\times$ weight penalty along the noise eigenvector.
5. **Observation 1 $\to$ Phrasing Risk**: Summarizing test fixes as `(assert 1 == 1)` in executive roadmaps mimics tautological dummy test shortcuts.
6. **Steps 1–5 $\to$ Conclusion**: The plan is of exceptional quality but cannot be approved in its current form due to these mathematical and architectural flaws. It requires targeted revisions.

---

## 3. Caveats

- The reviewer did not run live execution OMS orders against broker testbeds (paper trading API keys), but verified OMS order sizing logic, tick rounding, and currency scaling statically.
- The 1,900+ test suite was evaluated selectively for affected components (`tests/test_institutional_portfolio_construction.py`), and full suite execution was deferred to implementation phase.
- The plan's proposed IR/Sharpe improvements (+0.50 IR, +0.45 Sharpe) are theoretical estimates based on removing known negative alpha leaks and corner solutions; actual live out-of-sample performance will depend on market regime.

---

## 4. Conclusion

**Verdict: REQUEST_CHANGES**

The master plan `system_improvement_plan_v8.md` is 95% complete and of institutional caliber. However, approval is withheld pending the remediation of 6 specific items:
1. **CRIT-06**: Revise $w^{max}$ to $\min(1.0, \max(\text{max\_single\_weight}, \frac{1.0}{\max(n - 1, 1)}))$ to ensure asset divestment freedom in small universes.
2. **CRIT-03**: Eliminate `.bfill()` from the rolling causal normalizer; use expanding window statistics during warm-up.
3. **CRIT-09**: Apply PSD projection / minimum eigenvalue floor ($\lambda \ge 0.05$) to pairwise correlation in Löwdin orthogonalization.
4. **HIGH-01**: Replace `(assert 1 == 1)` in lines 1536 and 1632 with `(assert p_krx["lot_size"] == 1)`.
5. **CRIT-01**: Add `base_currency` awareness to prevent 1,350x under-allocation on USD-denominated accounts.
6. **CRIT-04**: Reinstate the 2% minimum ROE decay floor (`eff_decay >= 0.02`) to prevent zero-decay valuation bubbles.

---

## 5. Verification Method

1. **Verify Line References & Diagnoses**:
   - `unified_portfolio_allocator.py`: lines 494–506 (shares), lines 136–166 (CVaR bounds), lines 259–277 (market impact).
   - `portfolio_optimizer.py`: lines 202–255 (BL daily vs 20d return scale).
   - `card_factor.py`: line 174 (OLS VIX sign).
   - `tests/test_institutional_portfolio_construction.py`: run `.venv\Scripts\pytest tests/test_institutional_portfolio_construction.py -v` to observe `assert 1 == 10` failure.
2. **Verify Mathematical Bounds**:
   - Evaluate $4 \times 0.2625 = 1.05$. If $w_4 = 0$, $\sum_{i=1}^3 w_i \le 0.7875 < 1.0$, proving infeasibility of zeroing out an asset under $1.05/n$.
3. **Invalidation Conditions**:
   - If the author proves that CVaR allocation on $n \le 4$ never requires setting an asset to 0, or implements the suggested $\frac{1}{n-1}$ formula, finding 1 is resolved.
