# DISPATCH: Survey Phase - Explorer 2 (Risk Allocation)

## Mission
Survey the codebase for Milestone 2 (Risk Allocation):
- Inspect Phase 44 implementation in `src/risk/unified_portfolio_allocator.py` and `src/risk/portfolio_allocator.py` (look for F197.1, 40th-order Virasoro EVaR, version >= 44).
- Analyze exact formula requirements for Phase 45:
  1. Lurie-Kac-Moody-Whittaker Motivic Fisher-Rao manifold barycenter blending (F201.1, metric weights $\mu_{\text{lkmw}} = [3.50, 2.70, 2.65, 4.05]$) in `unified_portfolio_allocator.py` (version >= 45).
  2. 41st-order cumulant expansion Trans-Singular-Eternal-Omni-Cosmic-Infinite-Supreme-Transcendent-Clausen-Scholze-Deligne-Beilinson-W-Algebra-Virasoro-Kac-Moody EVaR tail risk budgeting ($41! \approx 3.345 \times 10^{49}$, $\xi_{\text{km}} = 0.9999998$) in `portfolio_allocator.py`.
  3. Preservation of MDD <= -0.00001% and Sharpe ratio >= 30.35 (target 30.38).
- Read `ORIGINAL_REQUEST.md` (Header `## 2026-09-15T21:55:02Z`).
- Write comprehensive report to your working directory: `handoff.md`.

## 2026-09-15T21:56:56Z
Investigate how Phase 44 (F197.1, 40th-order Virasoro EVaR) was implemented and how Phase 45 (F201.1) should be structured:
1. Lurie-Kac-Moody-Whittaker Motivic Fisher-Rao manifold barycenter blending (F201.1, metric weights mu_lkmw = [3.50, 2.70, 2.65, 4.05]) in unified_portfolio_allocator.py with version >= 45 branching.
2. 41st-order cumulant expansion Trans-Singular-Eternal-Omni-Cosmic-Infinite-Supreme-Transcendent-Clausen-Scholze-Deligne-Beilinson-W-Algebra-Virasoro-Kac-Moody EVaR tail risk budgeting (41! approx 3.345e49, xi_km = 0.9999998) in portfolio_allocator.py.
3. Maintaining MDD <= -0.00001% and annual Sharpe ratio >= 30.35 (target: 30.38).
Write findings, exact code locations, lines to modify or add, and recommended implementation strategy to handoff.md.
