# DISPATCH - Explorer M2-3

## Scope: Milestone 2 - OMS Delta Rebalancing & Tranche Slicing
Files owned: `trading_system/src/execution/oms_engine.py`, `trading_system/run_pipeline.py`
Input documents:
- `d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md` (read section ## 2026-09-03T15:32:22Z)
- `d:\Finance\code\stock\AGENTS.md`
- `d:\Finance\code\stock\.agents\teamwork_preview_orchestrator_quant_opt2\PROJECT.md`
- `d:\Finance\code\stock\.agents\explorer_survey_2_opt2\survey_r2.md`

Objective:
Formulate exact, step-by-step code modification recommendations for:
1. Feature 10: Enforcing $\Delta Q = Q_{\text{target}} - Q_{\text{current}}$ in `oms_engine.py:generate_order_plan()` to eliminate redundant buying of already-held buffer-retained positions.
2. Feature 11: Integrating `AlmgrenChrissScheduler.compute_trajectory()` directly into order plan generation to produce concrete child execution tranches with designated execution tags (`MIDPOINT_PEG` for maker rebates vs `AGGRESSIVE_TAKER` for final clearance) to eliminate spread-crossing drag.
3. Verification: Ensure all tests in `tests/test_order_manager.py`, `tests/test_portfolio_optimizer_and_oms.py`, and `tests/test_oms_synthetic_inverse_hedge.py` pass.
Output report: `d:\Finance\code\stock\.agents\explorer_m2_3_opt2\plan_m2_3.md`
Handoff report: `d:\Finance\code\stock\.agents\explorer_m2_3_opt2\handoff.md`
