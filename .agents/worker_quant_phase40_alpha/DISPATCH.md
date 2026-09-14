# DISPATCH: Worker 1 — Alpha Signal Specialist (Phase 40)

## Working Directory
d:\Finance\code\stock\.agents\worker_quant_phase40_alpha

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Mandatory References
1. `d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md` (Header: `## 2026-09-14T05:30:34Z`)
2. `d:\Finance\code\stock\.agents\explorer_quant_phase40_survey1\handoff.md`
3. `d:\Finance\code\stock\PROJECT.md`

## Exclusive File Ownership
- `src/ai/ensemble_scorer.py`
- `src/ai/factor_suppression.py`
- `tests/test_phase40_alpha.py`

## Implementation Tasks
1. In `src/ai/ensemble_scorer.py`:
   - Verify `GeometricLanglandsHodgeDeligneCoupler` and aliases.
   - At line ~19439 in `apply_smooth_noise_deadband`, add `if int(version) >= 40:` branch routing to `apply_octacontatetragonal_hyperbolic_deadband` with $\alpha = 128.0$.
2. In `src/ai/factor_suppression.py`:
   - In `def __getattr__(name: str) -> Any:`, add Phase 40 symbols (`GeometricLanglandsHodgeDeligneCoupler`, aliases, `apply_octacontatetragonal_hyperbolic_deadband`, `compute_phase40_hyperconvex_rank_modulation`, `REGIME_GAMMA_TOP_V40`, etc.) to prevent import-order AttributeError.
3. Write `tests/test_phase40_alpha.py` covering all 9 test scenarios described in Explorer 1's blueprint.
4. Execute tests via:
   `$env:BYPASS_TORCH="1"; python -m pytest tests/test_phase40_alpha.py -v`
   Verify 100% pass rate.
5. Write your completion report in `d:\Finance\code\stock\.agents\worker_quant_phase40_alpha\handoff.md` and send a message back to orchestrator (`d589c15d-8af5-4fdc-85b9-702f9839272f`).

## 2026-09-14T05:39:50Z
You are Worker 1 (Alpha Signal Specialist) for Phase 40 Quant Enhancement. Your working directory is d:\Finance\code\stock\.agents\worker_quant_phase40_alpha. Read your dispatch instructions at d:\Finance\code\stock\.agents\worker_quant_phase40_alpha\DISPATCH.md, the authoritative user request at d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md (Header: ## 2026-09-14T05:30:34Z), and Explorer 1's report at d:\Finance\code\stock\.agents\explorer_quant_phase40_survey1\handoff.md.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Exclusive File Ownership:
- src/ai/ensemble_scorer.py
- src/ai/factor_suppression.py
- tests/test_phase40_alpha.py

Implementation Tasks:
1. In src/ai/ensemble_scorer.py line ~19439, add the version >= 40 branch in apply_smooth_noise_deadband routing to apply_octacontatetragonal_hyperbolic_deadband with alpha=128.0.
2. In src/ai/factor_suppression.py, add Phase 40 symbols to __getattr__ (GeometricLanglandsHodgeDeligneCoupler, aliases, deadband, rank modulation, REGIME_GAMMA_TOP_V40).
3. Write tests/test_phase40_alpha.py with all 9 test scenarios from Explorer 1's handoff.
4. Execute tests via: $env:BYPASS_TORCH="1"; python -m pytest tests/test_phase40_alpha.py -v. Verify 100% pass rate.
5. Write your handoff report to d:\Finance\code\stock\.agents\worker_quant_phase40_alpha\handoff.md and send a completion message back to orchestrator (ID: d589c15d-8af5-4fdc-85b9-702f9839272f).
