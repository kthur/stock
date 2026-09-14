# DISPATCH: Challenger 1 (Adversarial Stress Testing: Alpha & Risk - Phase 41)

## Target Scope
- `trading_system/src/ai/ensemble_scorer.py`
- `trading_system/src/ai/factor_suppression.py`
- `trading_system/src/risk/unified_portfolio_allocator.py`
- `trading_system/src/risk/portfolio_allocator.py`
- Authoritative Request: `d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md` (header `## 2026-09-14T10:14:28Z`)

## Adversarial Stress Testing Objectives
1. **Alpha Signal Stress Testing (F183, F184.1, F184.2)**:
   - Test `apply_centatriacontaoctagonal_hyperbolic_deadband` with extreme float values, near-zero $|z| = 0.0001$, large $|z| = 1000.0$, NaN arrays, mixed types, checking leakage $< 10^{-74}$ and strict rank preservation.
   - Test `compute_phase41_hyperconvex_rank_modulation` across entire rank grid $[0.0, 1.0]$, checking monotonicity $g'(r) > 0$, boundary $g(0) = 0.50$, negative score handling, and overflow resilience under extreme $\gamma_{\text{top}}$.
   - Test `DrinfeldLafforgueFarguesFontaineCoupler` with degenerate pillars (all equal, all zero, massive outliers, NaN arrays), asserting finite outputs, bounded harmony factor, and valid FERI_v41.
2. **Risk Allocation Stress Testing (F185.1)**:
   - Test `compute_lurie_fargues_fontaine_fisher_rao_barycenter_blend` with degenerate distributions (one model 100%, uniform, massive dimensionality, near-zero components), checking exact simplex projection $\sum q = 1.000000$ and strict order: CVaR > BL > HERC > RP.
   - Test 37th-cumulant EVaR risk measure with heavy-tailed Cauchy/Student-t/Pareto distributed returns, large positive returns, large negative returns, checking that $\text{EVaR}_{37} \ge \text{EVaR}_{36}$ unconditionally.
3. Execute stress tests and record empirical results.
4. Record explicit verdict (`APPROVE` or `REJECT`) in `d:\Finance\code\stock\.agents\challenger_phase41_1\handoff.md`.
