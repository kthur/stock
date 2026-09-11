# DISPATCH: Explorer 2 (Risk Allocation Survey)

## Identity & Role
- Archetype: teamwork_preview_explorer
- Role: Risk Allocation Investigator
- Working directory: `d:\Finance\code\stock\.agents\explorer_quant_phase24_survey2`

## Inputs
- Authoritative User Request: `d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md` (Header `## 2026-09-11T10:54:49Z`)
- Project Scope: `d:\Finance\code\stock\PROJECT.md`
- Key target files to inspect:
  - `src/risk/unified_portfolio_allocator.py`
  - `src/risk/portfolio_allocator.py`
  - `tests/test_phase23_*.py` or previous risk tests

## Objective
Investigate the exact implementation patterns of Phase 23 (F113.1 Lurie Geometric Langlands Fisher-Rao barycenter blending, 19th-cumulant Ultra-Trans-Hyper EVaR) and formulate the concrete implementation blueprint for Phase 24 R2:
1. Lurie Arithmetic Spectral Fisher-Rao manifold barycenter blending (F117.1, metric weights $\mu_{\text{arithmetic}} = [2.15, 1.65, 1.60, 2.70]$) under `version >= 24` in `src/risk/unified_portfolio_allocator.py`.
2. 20th-order cumulant expansion Trans-Super-Hyper EVaR tail risk budgeting ($20! = 2,432,902,008,176,640,000$, $\xi_{\text{super\_hyper}} = 0.80$) in `src/risk/portfolio_allocator.py`.
3. Verify targets: MDD $\le -0.018\%$, Annualized Sharpe Ratio $\ge 17.75$.
4. Unit test design for `tests/test_phase24_risk.py`.

Deliver a detailed report to `handoff.md` in your working directory.
