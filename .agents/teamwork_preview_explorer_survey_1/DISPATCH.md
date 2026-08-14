# Explorer 1 Survey Dispatch

## Objective
Investigate the 31 strategy engines in the codebase (located in `src/core/`, `src/ai/`, etc.) focusing on alpha scoring, noise filtering, and signal precision for Surge, VCP, Stat-Arb, Sector Rotation, and all 31 strategies.

## Scope & Inputs
- `d:\Finance\code\stock\ORIGINAL_REQUEST.md`
- `d:\Finance\code\stock\AGENTS.md`
- `src/ai/prediction_model.py`
- `src/core/` strategy files
- `trading_system/run_pipeline.py`

## Instructions
1. Read `ORIGINAL_REQUEST.md`.
2. Inspect how the 31 strategies are currently implemented, registered, and scored.
3. Identify how noise filtering and signal precision can be improved for Surge classifier, VCP, Stat-Arb, Sector Rotation, and other core strategies.
4. Document the exact file locations, method signatures, mathematical/algorithmic formulation, and test locations.
5. Write your complete findings to `d:\Finance\code\stock\.agents\teamwork_preview_explorer_survey_1\analysis.md` and a handoff report at `d:\Finance\code\stock\.agents\teamwork_preview_explorer_survey_1\handoff.md`.

## 2026-08-14T09:22:05Z
User/Parent Request:
You are Explorer 1 (Strategy Alpha Explorer).
Your working directory is `d:\Finance\code\stock\.agents\teamwork_preview_explorer_survey_1`.
First, read `d:\Finance\code\stock\.agents\teamwork_preview_explorer_survey_1\DISPATCH.md` and `d:\Finance\code\stock\ORIGINAL_REQUEST.md`.
Investigate the 31 strategy engines in `src/core/`, `src/ai/`, etc., focusing on alpha scoring, noise filtering, and signal precision for Surge classifier, VCP, Stat-Arb, Sector Rotation, and all 31 strategies.
Write your analysis to `d:\Finance\code\stock\.agents\teamwork_preview_explorer_survey_1\analysis.md` and your final handoff to `d:\Finance\code\stock\.agents\teamwork_preview_explorer_survey_1\handoff.md`.
When done, message the orchestrator via send_message.
