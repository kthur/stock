# DISPATCH: Explorer 2 (Risk Allocation Survey)

## Identity
- Role: Codebase Researcher (Risk Allocation)
- Archetype: teamwork_preview_explorer
- Working directory: `d:\Finance\code\stock\.agents\explorer_quant_phase39_survey2`
- Original request: `d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md` (Header: `## 2026-09-13T20:29:00Z`)

## Objectives
1. Inspect `src/risk/unified_portfolio_allocator.py` and `src/risk/portfolio_allocator.py` to analyze how Phase 38 (and previous phases) implemented Fisher-Rao manifold barycenter blending and high-order cumulant EVaR tail risk budgeting.
2. Specifically analyze:
   - F177.1: Lurie-Clausen-Scholze Motivic Fisher-Rao manifold barycenter blending with metric weights $\mu_{\text{lcs}} = [2.90, 2.40, 2.35, 3.45]$ under version branch `version >= 39` in `unified_portfolio_allocator.py`.
   - F177.2 (tail risk budgeting): 35th-cumulant expansion Trans-Singular-Eternal-Omni-Cosmic-Infinite-Supreme-Transcendent-Clausen-Scholze EVaR tail risk budgeting ($35! = 1,033,314,796,638,614,492,966,160,480,772,320,000,000$, $\xi_{\text{clausen\_scholze}} = 0.999995$) in `portfolio_allocator.py`.
   - Target metrics: MDD $\le -0.00008\%$, Annualized Sharpe Ratio $\ge 26.75$.
3. Check `tests/test_phase38_risk.py` to understand the unit test patterns for risk allocation, and formulate test requirements for `tests/test_phase39_risk.py`.
4. Output a comprehensive report to `d:\Finance\code\stock\.agents\explorer_quant_phase39_survey2\handoff.md`.

## 2026-09-13T20:31:00Z
You are explorer_quant_phase39_survey2 (Risk Allocation Researcher).
Your working directory is: d:\Finance\code\stock\.agents\explorer_quant_phase39_survey2
Task:
1. Inspect src/risk/unified_portfolio_allocator.py and src/risk/portfolio_allocator.py to see how Phase 38 (and previous phases) implemented Fisher-Rao manifold barycenter blending and high-order cumulant EVaR tail risk budgeting.
2. Detail the exact design blueprint for Phase 39:
   - F177.1: Lurie-Clausen-Scholze Motivic Fisher-Rao manifold barycenter blending with metric weights mu_lcs = [2.90, 2.40, 2.35, 3.45] under version branch version >= 39 in unified_portfolio_allocator.py.
   - F177.2: 35th-cumulant expansion Trans-Singular-Eternal-Omni-Cosmic-Infinite-Supreme-Transcendent-Clausen-Scholze EVaR tail risk budgeting (35! = 1,033,314,796,638,614,492,966,160,480,772,320,000,000, xi_clausen_scholze = 0.999995) in portfolio_allocator.py.
   - Targets: MDD <= -0.00008%, Annualized Sharpe Ratio >= 26.75.
3. Inspect tests/test_phase38_risk.py and formulate unit test specification for tests/test_phase39_risk.py.
4. Write your full findings and blueprint to:
   d:\Finance\code\stock\.agents\explorer_quant_phase39_survey2\handoff.md
Update progress.md in your directory as you work.
When finished, send a completion message back.
