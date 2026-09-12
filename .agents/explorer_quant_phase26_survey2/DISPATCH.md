# DISPATCH: Survey 2 — Risk Allocation Exploration (Phase 26)

## 2026-09-11T13:22:24Z

## Working Directory
`d:\Finance\code\stock\.agents\explorer_quant_phase26_survey2`

## Role
Risk Allocation Specialist Explorer

## Context & Objectives
You are Explorer 2 surveying the codebases for Phase 26 R2 Risk Allocation Enhancement.
Authoritative user request is in:
`d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md` (Header: `## 2026-09-11T13:18:53Z`)
Also read:
`d:\Finance\code\stock\PROJECT.md`
`d:\Finance\code\stock\.agents\orchestrator_quant_phase26_1\plan.md`

## Your Mission
1. Investigate existing hook points in:
   - `src/risk/unified_portfolio_allocator.py`
   - `src/risk/portfolio_allocator.py`
   - Existing Phase 24 and Phase 25 implementations (F117.1, F121.1, cumulant EVaR expansions)
2. Detail the exact design and implementation blueprint for:
   - F125.1: Lurie Mochizuki IUT Fisher-Rao manifold barycenter blending with metric weights $\mu_{\text{mochizuki}} = [2.25, 1.75, 1.70, 2.80]$ in `unified_portfolio_allocator.py` under version branch `version >= 26`.
   - F125.1 / EVaR: 22nd-order cumulant expansion-based Trans-Singular-Hyper EVaR tail risk budgeting in `portfolio_allocator.py` ($22! = 1,124,000,727,777,607,680,000$, $\xi_{\text{singular\_hyper}} = 0.90$).
   - Headroom redistribution, semi-covariance Sortino preservation, MDD compression ($\le -0.011\%$), Annualized Sharpe Ratio ($\ge 18.95$).
3. Provide concrete line numbers, exact equations, class/method signatures, and unit test specifications for `tests/test_phase26_risk.py`.
4. Output your complete analysis to:
   `d:\Finance\code\stock\.agents\explorer_quant_phase26_survey2\handoff.md`
   And send a completion message to the Orchestrator (`23291457-ea26-4c49-8433-2bc79a9280cf`).
