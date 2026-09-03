# DISPATCH - Explorer M2-2

## Scope: Milestone 2 - Volatility-Normalized Asymmetric Leland Buffers
Files owned: `trading_system/src/risk/unified_portfolio_allocator.py`, `trading_system/src/risk/portfolio_allocator.py`
Input documents:
- `d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md` (read section ## 2026-09-03T15:32:22Z)
- `d:\Finance\code\stock\AGENTS.md`
- `d:\Finance\code\stock\.agents\teamwork_preview_orchestrator_quant_opt2\PROJECT.md`
- `d:\Finance\code\stock\.agents\explorer_survey_2_opt2\survey_r2.md`

Objective:
Formulate exact, step-by-step code modification recommendations for:
1. Feature 9: Standardizing asymmetric Leland no-trade buffers using continuous Z-scores $z_{\text{unrealized}} = u_{\text{ret}} / (\sigma_{20\text{d}} \sqrt{5})$ instead of static $+8\% / -3\%$ thresholds.
2. Boundary rebalancing: when current weight breaches buffer band, rebalance to the boundary ($L_i$ or $U_i$) rather than target, minimizing unnecessary turnover while controlling tracking error.
3. Verification: Ensure all tests in `tests/test_portfolio_allocator.py` and `tests/test_unified_portfolio_engine.py` pass.
Output report: `d:\Finance\code\stock\.agents\explorer_m2_2_opt2\plan_m2_2.md`
Handoff report: `d:\Finance\code\stock\.agents\explorer_m2_2_opt2\handoff.md`

## 2026-09-03T16:05:41Z
You are Explorer M2-2 (Volatility-Normalized Leland Buffers Specialist).
Your working directory is: d:\Finance\code\stock\.agents\explorer_m2_2_opt2
Project root / codebase directory is: d:\Finance\code\stock
Authoritative request file: d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md (specifically read section ## 2026-09-03T15:32:22Z)
Project rules and architecture: d:\Finance\code\stock\AGENTS.md
Project plan: d:\Finance\code\stock\.agents\teamwork_preview_orchestrator_quant_opt2\PROJECT.md
Survey analysis: d:\Finance\code\stock\.agents\explorer_survey_2_opt2\survey_r2.md
Your dispatch instructions: d:\Finance\code\stock\.agents\explorer_m2_2_opt2\DISPATCH.md

Your mission:
Recommend the exact fix strategy and code-level design for Milestone 2 Feature 9:
1. Standardize asymmetric Leland no-trade buffers in `trading_system/src/risk/unified_portfolio_allocator.py` and `portfolio_allocator.py` using continuous Z-scores $z_{\text{unrealized}} = u_{\text{ret}} / (\sigma_{20\text{d}} \sqrt{5})$ instead of static $+8\% / -3\%$ thresholds.
2. Formulate boundary rebalancing: when current weight breaches buffer band, rebalance to the boundary ($L_i$ or $U_i$) rather than target, minimizing unnecessary turnover while controlling tracking error.
3. Provide exact code diffs and test verification commands.

Write your technical plan to: `d:\Finance\code\stock\.agents\explorer_m2_2_opt2\plan_m2_2.md`
And a self-contained handoff report at: `d:\Finance\code\stock\.agents\explorer_m2_2_opt2\handoff.md`
Update `progress.md` with timestamps as your liveness heartbeat.
When finished, send a brief message with your handoff report path.
