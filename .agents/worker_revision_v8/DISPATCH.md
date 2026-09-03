## 2026-09-03T01:05:10Z
You are the Plan Revision Worker for the 37-Strategy Trading System Improvement Plan (v8).
Your working directory is: d:\Finance\code\stock\.agents\worker_revision_v8
Make sure to initialize your BRIEFING.md, progress.md, and update:
`d:\Finance\code\stock\system_improvement_plan_v8.md`

Read the detailed adversarial feedback from both reviewers:
1. Reviewer 1 (Math & Algorithms): `d:\Finance\code\stock\.agents\reviewer_plan_math_v8\review_report.md`
2. Reviewer 2 (QA & Safety): `d:\Finance\code\stock\.agents\reviewer_plan_qa_v8\review_report.md`
3. Orchestrator Gate Status: `d:\Finance\code\stock\.agents\teamwork_preview_orchestrator_v8\GATE_STATUS.md`

Your Task:
Incorporate all 10 reviewer remediations into `d:\Finance\code\stock\system_improvement_plan_v8.md` with extreme precision:

1. **CRIT-01 (UnifiedPortfolioAllocator Signature & FX Translation)**:
   - Restore and preserve the EXACT method signature of `UnifiedPortfolioAllocator.allocate`:
     `allocate(self, predictions_df, prices_dict, total_portfolio_value=100_000_000.0, regime='BULL_LOW_VOL', current_holdings=None, sector_map=None, top_n=20, base_currency='KRW', usd_krw=1350.0)`
   - Embed the FX translation in the share sizing loop:
     `effective_price_krw = price * usd_krw if (is_us and base_currency == 'KRW') else price`
     `shares = int(allocated_capital / effective_price_krw)`
   - Support both KRW-denominated and USD-denominated accounts gracefully.

2. **CRIT-02 (Black-Litterman Return Type, Signature & Scale Auto-Detection)**:
   - Retain the exact return type: `np.ndarray` (NOT `pd.Series`).
   - Retain original argument names: `calculate_black_litterman_weights(self, expected_returns, cov_matrix, views=None, P=None, Q=None, tau=0.05, risk_aversion=2.5, ...)`
   - Implement dynamic scale auto-detection for $Q$:
     If `np.all(np.abs(Q) < 1.0)` (decimal views such as in `test_adversarial_challenger_1.py:320-328`), do NOT divide by 100. If `np.any(np.abs(Q) >= 1.0)`, convert percentage views to decimal ($Q / 100$).
   - Convert 20-day horizon returns to daily equivalent: $Q_{daily} = Q / 20.0$ (or $Q / \sqrt{20}$ depending on volatility scaling) to align with daily covariance matrix $\Sigma$.

3. **CRIT-03 (LSTM Expanding Window Normalization)**:
   - In `lstm_predictor.py`, eliminate `.bfill()` on rolling window stats. Use expanding window initialization (`min_periods=1`) so that days 0–19 are normalized strictly causally using available historical bars without lookahead.

4. **CRIT-04 (Ohlson ROE Decay Floor)**:
   - In `rim_valuation.py`, preserve the 2% floor on decay rate:
     `decay_rate = max(0.02, min(0.15, ...))` to prevent a 0.0% decay rate and perpetual excess income bubble.

5. **CRIT-06 (CVaR Bound Box-In Remediation)**:
   - In `unified_portfolio_allocator.py`, replace $w_i \le \max(0.20, \frac{1.05}{n})$ with:
     `max_w = min(1.0, max(self.max_single_weight, 1.0 / max(n - 1, 1)))`
     `bounds = [(0.0, max_w) for _ in range(n)]`
   - This ensures the feasibility condition $\sum w_i^{max} \ge 1.0$ while allowing the solver to allocate 0.0% to toxic assets.

6. **CRIT-09 (Löwdin Pairwise Non-PSD Projection)**:
   - In `ensemble_scorer.py`, when computing pairwise correlation on missing data, apply an eigenvalue floor ($\lambda \ge 0.05$) or nearest positive semi-definite projection before computing $C^{-1/2} = V \text{diag}(\max(\lambda_i, 0.05)^{-1/2}) V^T$.

7. **HIGH-01 (Test Phrasing & Checklist Completeness for Lines 193 & 194)**:
   - Update test phrasing from dummy `(assert 1 == 1)` to the actual production assertion:
     `assert p_krx["lot_size"] == 1`
     `assert p_krx["shares"] % 1 == 0`
   - Ensure all roadmap checklists and summary tables explicitly reference both line 193 and line 194 of `test_institutional_portfolio_construction.py`.

8. **Test File Path Precision**:
   - In Section 4 and across all items, clarify existing test files vs proposed new test files. Consolidate new unit/integration tests into a dedicated suite: `tests/test_v8_remediation.py`.