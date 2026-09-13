# DISPATCH: Worker 1 (Alpha Signal Specialist)

## Identity
- Role: Alpha Signal Specialist
- Archetype: teamwork_preview_worker
- Working directory: `d:\Finance\code\stock\.agents\worker_quant_phase39_alpha`
- Original request: `d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md` (Header: `## 2026-09-13T20:29:00Z`)
- Survey blueprint: `d:\Finance\code\stock\.agents\explorer_quant_phase39_survey1\handoff.md`

## Exclusive File Ownership
- `trading_system/src/ai/ensemble_scorer.py`
- `trading_system/src/ai/factor_suppression.py`
- `tests/test_phase39_alpha.py`
DO NOT touch any other files.

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Objectives
1. Read the blueprint in `d:\Finance\code\stock\.agents\explorer_quant_phase39_survey1\handoff.md`.
2. In `trading_system/src/ai/ensemble_scorer.py`:
   - Implement `MotivicClausenScholzeCoupler` and all aliases (`MotivicClausenCoupler`, `ClausenScholzeLiquidCoupler`, `MotivicLiquidCoupler`, `LiquidVectorSpaceCoupler`, `ScholzeLiquidCoupler`, `CondensedLiquidCoupler_v39`) under F175.
   - Implement `compute_phase39_hyperconvex_rank_modulation` and alias `compute_phase39_rank_warping` under F176.1.
   - Bind static methods and class method `compute_motivic_clausen_scholze_coupling` to `EnsembleScoringEngine`.
   - Update `apply_smooth_noise_deadband` with version 39 Centaicosagonal deadband ($\alpha=120.0$).
   - Update `combine_predictions` under `if version >= 39:` with Motivic Clausen-Scholze coupling (`+ 1.95 * h_clausen * z_liquid`).
3. In `trading_system/src/ai/factor_suppression.py`:
   - Ensure `apply_centaicosagonal_hyperbolic_deadband` and aliases (`compute_phase39_deadband`, `apply_phase39_deadband`, `apply_centaicosa_hyperbolic_deadband`) and `compute_phase39_hyperconvex_rank_modulation` are fully integrated and exported.
4. Create `tests/test_phase39_alpha.py` containing the 9 test cases specified in the blueprint.
5. Run the tests using `.venv\Scripts\pytest tests/test_phase39_alpha.py tests/test_phase38_alpha.py -v` to ensure 100% pass and no regression.
6. Write your completion report to `d:\Finance\code\stock\.agents\worker_quant_phase39_alpha\handoff.md`.
