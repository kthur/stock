# DISPATCH - Explorer M2-1

## Scope: Milestone 2 - Dynamic Half-Life Convergence & Cash Buffer
Files owned: `trading_system/src/risk/unified_portfolio_allocator.py`
Input documents:
- `d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md` (read section ## 2026-09-03T15:32:22Z)
- `d:\Finance\code\stock\AGENTS.md`
- `d:\Finance\code\stock\.agents\teamwork_preview_orchestrator_quant_opt2\PROJECT.md`
- `d:\Finance\code\stock\.agents\explorer_survey_2_opt2\survey_r2.md`

Objective:
Formulate exact, step-by-step code modification recommendations for:
1. Feature 7: Implementing closed-form optimal convergence velocity $\theta_i^* \in (0, 1]$ balancing perishable alpha decay ($\tau_{1/2}$) against Gatheral 3/2-power liquidity impact penalty:
   $w_{t+1, i} = w_{t, i} + \theta_i^* (w^*_i - w_{t, i})$.
2. Feature 8: Routing unallocated liquidity-constrained capital to cash buffer rather than re-normalizing and inflating other asset weights ($w_{\text{cash}} = 1.0 - \sum w_i$).
3. Verification: Ensure all tests in `tests/test_unified_portfolio_engine.py` and `tests/test_portfolio_allocator.py` pass.
Output report: `d:\Finance\code\stock\.agents\explorer_m2_1_opt2\plan_m2_1.md`
Handoff report: `d:\Finance\code\stock\.agents\explorer_m2_1_opt2\handoff.md`

## 2026-09-03T16:05:41Z
You are Explorer M2-1 (Half-Life Convergence & Cash Buffer Specialist).
Your working directory is: d:\Finance\code\stock\.agents\explorer_m2_1_opt2
Project root / codebase directory is: d:\Finance\code\stock
Authoritative request file: d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md (specifically read section ## 2026-09-03T15:32:22Z)
Project rules and architecture: d:\Finance\code\stock\AGENTS.md
Project plan: d:\Finance\code\stock\.agents\teamwork_preview_orchestrator_quant_opt2\PROJECT.md
Survey analysis: d:\Finance\code\stock\.agents\explorer_survey_2_opt2\survey_r2.md
Your dispatch instructions: d:\Finance\code\stock\.agents\explorer_m2_1_opt2\DISPATCH.md

Your mission:
Recommend the exact fix strategy and code-level design for Milestone 2 Feature 7 & Feature 8:
1. Formulate closed-form optimal convergence velocity $\theta_i^* \in (0, 1]$ in `trading_system/src/risk/unified_portfolio_allocator.py` balancing perishable alpha decay against Gatheral 3/2-power liquidity impact penalty: $w_{t+1, i} = w_{t, i} + \theta_i^* (w^*_i - w_{t, i})$.
2. Route unallocated liquidity-constrained capital to cash buffer rather than re-normalizing and inflating other asset weights.
3. Provide exact code diffs and test verification commands.

Write your technical plan to: `d:\Finance\code\stock\.agents\explorer_m2_1_opt2\plan_m2_1.md`
And a self-contained handoff report at: `d:\Finance\code\stock\.agents\explorer_m2_1_opt2\handoff.md`
Update `progress.md` with timestamps as your liveness heartbeat.
When finished, send a brief message with your handoff report path.

