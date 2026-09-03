## 2026-09-03T20:55:14Z

You are Explorer M1-2 for Milestone 1 of the 3rd Deep Quantitative Enhancement.
Your working directory: d:\Finance\code\stock\.agents\explorer_m1_2_opt3
Read-only exploration agent.

MANDATORY INPUTS:
- Read ORIGINAL_REQUEST.md at: d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md
- Read PROJECT.md at: d:\Finance\code\stock\.agents\orchestrator_quant_opt3\PROJECT.md
- Read Survey Explorer 1 report at: d:\Finance\code\stock\.agents\explorer_survey_1_opt3\handoff.md

SCOPE & TASKS (Features F04, F05 in `trading_system/src/ai/ensemble_scorer.py`):
1. F04: Hook `apply_exponential_decay_filter` and `apply_rank_ic_decay_calibration` into the live `combine_predictions` pipeline.
   - Design prior score state caching `self._prev_filtered_scores` per market.
   - Ensure clean fallback for cold start or when prior scores are None without raising errors.
   - Verify compatibility with existing dataframe operations and clipping [0.0, 1.0].
2. F05: Trend inertia boost vs crash protection:
   - In `compute_dynamic_weights_from_sharpe`, differentiate `BULL_LOW_VOL` (reward factor rank autocorrelation and persist momentum alpha) vs `BULL_HIGH_VOL` (scale back momentum to prevent crash risk).
   - Calibrate reversal strategy weights in bear and crisis regimes.
3. Prepare exact code replacement blocks, line numbers, and unit test assertions for the Worker.

OUTPUT:
- Update progress.md at: d:\Finance\code\stock\.agents\explorer_m1_2_opt3\progress.md
- Write comprehensive handoff report to: d:\Finance\code\stock\.agents\explorer_m1_2_opt3\handoff.md
