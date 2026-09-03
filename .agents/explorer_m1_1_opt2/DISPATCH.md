# DISPATCH - Explorer M1-1

## Scope: Milestone 1 - Pipeline Sequence & Factor Suppression
Files owned: `trading_system/src/ai/factor_suppression.py`, `trading_system/src/ai/ensemble_scorer.py`
Input documents:
- `d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md` (read section ## 2026-09-03T15:32:22Z)
- `d:\Finance\code\stock\AGENTS.md`
- `d:\Finance\code\stock\.agents\teamwork_preview_orchestrator_quant_opt2\PROJECT.md`
- `d:\Finance\code\stock\.agents\explorer_survey_1_opt2\survey_r1.md`

Objective:
Formulate exact, step-by-step code modification recommendations for:
1. Moving raw correlation monitoring and factor suppression BEFORE ZCA orthogonalization in `combine_predictions()`.
2. Implementing statistically calibrated suppression cutoffs $\theta(R, N) = \theta_0(R) + 1.645/\sqrt{N-3}$.
3. Ensuring all tests in `tests/test_correlation_suppression.py` and `tests/test_factor_orthogonalization.py` remain 100% passing.
Output report: `d:\Finance\code\stock\.agents\explorer_m1_1_opt2\plan_m1_1.md`
Handoff report: `d:\Finance\code\stock\.agents\explorer_m1_1_opt2\handoff.md`

## 2026-09-03T15:42:14Z
You are Explorer M1-1 (Pipeline Sequence & Factor Suppression Specialist).
Your working directory is: d:\Finance\code\stock\.agents\explorer_m1_1_opt2
Project root / codebase directory is: d:\Finance\code\stock
Authoritative request file: d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md (specifically read section ## 2026-09-03T15:32:22Z)
Project rules and architecture: d:\Finance\code\stock\AGENTS.md
Project plan: d:\Finance\code\stock\.agents\teamwork_preview_orchestrator_quant_opt2\PROJECT.md
Survey analysis: d:\Finance\code\stock\.agents\explorer_survey_1_opt2\survey_r1.md
Your dispatch instructions: d:\Finance\code\stock\.agents\explorer_m1_1_opt2\DISPATCH.md

Your mission:
Recommend the exact fix strategy and code-level design for Milestone 1 Feature 1 & Feature 6:
1. Move raw correlation monitoring and factor suppression BEFORE ZCA orthogonalization in `combine_predictions()` so collinearity penalties operate on raw signals.
2. Implement statistically calibrated suppression cutoffs $\theta(R, N) = \theta_0(R) + 1.645/\sqrt{N-3}$ in `factor_suppression.py`.
3. Provide exact code diffs/guidelines for the Worker and verify test suite coverage.

Write your technical plan to: `d:\Finance\code\stock\.agents\explorer_m1_1_opt2\plan_m1_1.md`
And a self-contained handoff report at: `d:\Finance\code\stock\.agents\explorer_m1_1_opt2\handoff.md`
Update `progress.md` with timestamps as your liveness heartbeat.
When finished, send a brief message with your handoff report path.

