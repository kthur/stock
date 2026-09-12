# DISPATCH: Worker 2 — Risk Allocation Specialist Implementation (Phase 26)

## Working Directory
`d:\Finance\code\stock\.agents\worker_quant_phase26_risk`

## Role
Risk Allocation Specialist Implementation Worker (`teamwork_preview_worker`)

## Context & Objectives
You are Worker 2 implementing the Phase 26 R2 Risk Allocation Enhancement.
Authoritative user request:
`d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md` (Header: `## 2026-09-11T13:18:53Z`)
Full architectural survey and implementation blueprint:
`d:\Finance\code\stock\.agents\explorer_quant_phase26_survey2\handoff.md`

## MANDATORY INTEGRITY WARNING
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Exclusive Write Ownership
You EXCLUSIVELY own and modify:
- `src/risk/unified_portfolio_allocator.py`
- `src/risk/portfolio_allocator.py`
- `tests/test_phase26_risk.py`

DO NOT modify any other files.

## Technical Tasks
1. Implement Feature F125.1: Lurie Mochizuki IUT Fisher-Rao Manifold Barycenter Blending in `src/risk/unified_portfolio_allocator.py`:
   - Define `compute_lurie_mochizuki_iut_fisher_rao_barycenter_blend(model_weights, max_iter=50, tol=1e-6, step_size=0.50)` with metric weights $\mu_{\text{mochizuki}} = [2.25, 1.75, 1.70, 2.80]$ for `["bl", "herc", "rp", "cvar"]`.
   - Provide all 14 aliases as specified in Explorer 2's report.
   - In `compute_information_theoretic_blend_weights()`, branch for `is_phase26 = (int(version) >= 26)` and apply the Mochizuki barycenter blending.
2. Implement Feature F125.1 / EVaR: 22nd-order cumulant expansion Trans-Singular-Hyper EVaR ($22! = 1,124,000,727,777,607,680,000$, $\xi_{\text{singular\_hyper}} = 0.90$):
   - Define `compute_trans_singular_hyper_evar_risk_measure` in `src/risk/unified_portfolio_allocator.py`.
   - Even-order exponent 22 allows $(t \cdot L)^{22}$ or $t^{22} |L|^{22}$.
   - Add static delegations and aliases in `src/risk/portfolio_allocator.py`.
3. Ensure Sortino downside semi-covariance integration and tail calibration preserving MDD compression ($\le -0.011\%$) and Annualized Sharpe Ratio ($\ge 18.95$).
4. Implement `tests/test_phase26_risk.py` with all 14 unit test cases specified in Explorer 2's handoff report.
5. Run tests using `.venv/Scripts/python.exe -m pytest tests/test_phase26_risk.py tests/test_phase25_risk.py -v`. Ensure 100% pass and 0 regressions.
6. Write your completion report to `d:\Finance\code\stock\.agents\worker_quant_phase26_risk\handoff.md` and send a message to Orchestrator (`23291457-ea26-4c49-8433-2bc79a9280cf`).
