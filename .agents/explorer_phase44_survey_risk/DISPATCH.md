# Task Assignment: Phase 44 Survey Explorer — Risk Allocation Scope (F197.1)

## Identity & Working Directory
- Role: Survey Explorer (Risk Allocation Scope)
- Working Directory: d:\Finance\code\stock\.agents\explorer_phase44_survey_risk

## Context & Inputs
- Authoritative Request: d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md (Header: ## 2026-09-15T12:29:31Z)
- Orchestrator Dispatch: d:\Finance\code\stock\.agents\orchestrator_quant_phase44_1\DISPATCH.md
- Scope Document: d:\Finance\code\stock\PROJECT.md

## Target Files (ONLY 2 Files to Investigate)
- `src/risk/unified_portfolio_allocator.py`
- `src/risk/portfolio_allocator.py`
- Test reference: `tests/test_phase43_risk.py`

## Objectives
1. Inspect Phase 43 implementation:
   - Lurie-W-Algebra Motivic Fisher-Rao Barycenter in `unified_portfolio_allocator.py` (search `version >= 43`, `mu_w_alg`, etc.)
   - 39th-cumulant Trans-Singular-W-Algebra EVaR in `portfolio_allocator.py`
2. Specify exact Phase 44 implementation design for F197.1:
   - Lurie-Virasoro-Whittaker Motivic Fisher-Rao manifold barycenter blending ($\mu_{\text{lvw}} = [3.40, 2.65, 2.60, 3.95]$) in `unified_portfolio_allocator.py` under version branch `version >= 44`
   - 40th-cumulant Trans-Singular-Virasoro EVaR ($40! \approx 8.159 \times 10^{47}$, $\xi_{\text{vir}} = 0.9999995$) in `portfolio_allocator.py`
   - Performance goals: composite MDD $\le -0.00001\%$, Sharpe $\ge 29.75$
   - Specify all method names, aliases, signatures, line numbers, and backward compatibility hooks.

## Output
Write your report to: `d:\Finance\code\stock\.agents\explorer_phase44_survey_risk\handoff.md` and send a completion message.

## 2026-09-15T13:41:57Z
You are Survey Explorer (Risk Allocation Scope) for Phase 44 Quant Enhancement.
Your working directory is: d:\Finance\code\stock\.agents\explorer_phase44_survey_risk
Read your instructions at: d:\Finance\code\stock\.agents\explorer_phase44_survey_risk\DISPATCH.md
Authoritative request is at: d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md (Header: ## 2026-09-15T12:29:31Z)

Scope: ONLY 2 files:
- `src/risk/unified_portfolio_allocator.py`
- `src/risk/portfolio_allocator.py`
- Reference: `tests/test_phase43_risk.py`

Investigate Phase 43 implementation and specify exact Phase 44 designs for F197.1:
- Lurie-Virasoro-Whittaker Motivic Fisher-Rao barycenter (mu_lvw = [3.40, 2.65, 2.60, 3.95]) in unified_portfolio_allocator.py under version >= 44
- 40th-cumulant Trans-Singular-Virasoro EVaR (40! ~ 8.159e47, xi_vir = 0.9999995) in portfolio_allocator.py (MDD <= -0.00001%, Sharpe >= 29.75)

Write your report to `d:\Finance\code\stock\.agents\explorer_phase44_survey_risk\handoff.md` and use send_message to report completion.

