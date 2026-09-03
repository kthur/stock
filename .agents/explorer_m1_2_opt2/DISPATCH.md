# DISPATCH - Explorer M1-2

## Scope: Milestone 1 - Dual-Consensus Spectral Whitening
Files owned: `trading_system/src/ai/factor_orthogonalizer.py`
Input documents:
- `d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md` (read section ## 2026-09-03T15:32:22Z)
- `d:\Finance\code\stock\AGENTS.md`
- `d:\Finance\code\stock\.agents\teamwork_preview_orchestrator_quant_opt2\PROJECT.md`
- `d:\Finance\code\stock\.agents\explorer_survey_1_opt2\survey_r1.md`

Objective:
Formulate exact, step-by-step code modification recommendations for:
1. Upgrading `_pca_zca_symmetric` to support preserving both PC1 and PC2 eigenvalues (`preserve_top_k=2`) while properly whitening remaining noise dimensions.
2. Marchenko-Pastur spectral flooring for weak noise eigenvalues $\lambda_{\text{floor}} = \max((1 - \sqrt{K/N})^2, 0.05)$.
3. Ensuring full backward compatibility with existing tests in `tests/test_factor_orthogonalization.py`.
Output report: `d:\Finance\code\stock\.agents\explorer_m1_2_opt2\plan_m1_2.md`
Handoff report: `d:\Finance\code\stock\.agents\explorer_m1_2_opt2\handoff.md`

## 2026-09-03T15:42:14Z
User dispatch:
You are Explorer M1-2 (Dual-Consensus Spectral Whitening Specialist).
Your working directory is: d:\Finance\code\stock\.agents\explorer_m1_2_opt2
Project root / codebase directory is: d:\Finance\code\stock
Authoritative request file: d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md (specifically read section ## 2026-09-03T15:32:22Z)
Project rules and architecture: d:\Finance\code\stock\AGENTS.md
Project plan: d:\Finance\code\stock\.agents\teamwork_preview_orchestrator_quant_opt2\PROJECT.md
Survey analysis: d:\Finance\code\stock\.agents\explorer_survey_1_opt2\survey_r1.md
Your dispatch instructions: d:\Finance\code\stock\.agents\explorer_m1_2_opt2\DISPATCH.md

Your mission:
Recommend the exact fix strategy and code-level design for Milestone 1 Feature 2:
1. Upgrade `_pca_zca_symmetric` in `factor_orthogonalizer.py` to support `preserve_top_k=2` (preserving PC1 market trend and PC2 fundamental value/quality leading eigenvalues).
2. Apply Marchenko-Pastur spectral flooring for weak noise eigenvalues.
3. Provide exact code diffs/guidelines for the Worker and verify test suite coverage.

Write your technical plan to: `d:\Finance\code\stock\.agents\explorer_m1_2_opt2\plan_m1_2.md`
And a self-contained handoff report at: `d:\Finance\code\stock\.agents\explorer_m1_2_opt2\handoff.md`
Update `progress.md` with timestamps as your liveness heartbeat.
When finished, send a brief message with your handoff report path.
