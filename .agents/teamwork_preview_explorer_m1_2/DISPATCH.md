# Explorer M1-2 Dispatch: Pipeline Integration & Score Wiring Design

## Objective
Analyze the exact changes needed in `trading_system/run_pipeline.py` and `src/ai/ensemble_scorer.py` for Strategy 21 (`factor_neutralized`):
1. In `run_pipeline.py` (around line 2869): proper invocation of `fn_engine.compute_scores(universe=universe_df, raw_scores=...)` or passing appropriate inputs so all 3,379 symbols receive valid scores.
2. In `run_pipeline.py` (around line 2880): writing results into database / prediction maps with consistent column keys (`factor_neutralized_score` / `neutralized_score`).
3. Verifying that `strategy_data_coverage_report.txt` and `EnsembleScoringEngine` achieve $\ge 95\%$ coverage and prevent Strategy 21 from being falsely pruned with negative Sharpe.

## Inputs
- `d:\Finance\code\stock\ORIGINAL_REQUEST.md`
- `d:\Finance\code\stock\PROJECT.md`
- `trading_system/run_pipeline.py`
- `trading_system/src/ai/ensemble_scorer.py`

## Deliverables
- Detailed pipeline patch specification in `d:\Finance\code\stock\.agents\teamwork_preview_explorer_m1_2\analysis.md`.
- Handoff report in `d:\Finance\code\stock\.agents\teamwork_preview_explorer_m1_2\handoff.md`.

## 2026-08-14T09:26:45Z
You are Explorer M1-2 (Pipeline Integration Designer).
Your working directory is `d:\Finance\code\stock\.agents\teamwork_preview_explorer_m1_2`.
First, read `d:\Finance\code\stock\.agents\teamwork_preview_explorer_m1_2\DISPATCH.md`, `d:\Finance\code\stock\PROJECT.md`, and `d:\Finance\code\stock\ORIGINAL_REQUEST.md`.
Analyze the exact changes needed in `trading_system/run_pipeline.py` and `src/ai/ensemble_scorer.py` to wire Strategy 21 correctly and ensure >=95% universe coverage.
Write your analysis to `d:\Finance\code\stock\.agents\teamwork_preview_explorer_m1_2\analysis.md` and handoff report to `d:\Finance\code\stock\.agents\teamwork_preview_explorer_m1_2\handoff.md`.
When done, message the orchestrator via send_message.

