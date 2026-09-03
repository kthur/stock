# DISPATCH - Worker M1

## Mission
Implement Milestone 1 Features (Requirement R1):
- Feature 1 & 6: Pipeline Sequence Rectification & Statistically Calibrated Suppression in `trading_system/src/ai/factor_suppression.py` and `trading_system/src/ai/ensemble_scorer.py` (per `d:\Finance\code\stock\.agents\explorer_m1_1_opt2\plan_m1_1.md`).
- Feature 2: Dual-Consensus Spectral Whitening (`preserve_top_k=2`) and Noise-Scaled Marchenko-Pastur Flooring in `trading_system/src/ai/factor_orthogonalizer.py` (per `d:\Finance\code\stock\.agents\explorer_m1_2_opt2\plan_m1_2.md`).
- Feature 3, 4, 5: Symmetric Richards/Bessembinder Convex Transformation, Continuous Bilinear Cross-Pillar Synergy Kernel, and 2D Regime-Adaptive Half-Life Decay in `trading_system/src/ai/ensemble_scorer.py` (per `d:\Finance\code\stock\.agents\explorer_m1_3_opt2\plan_m1_3.md`).

## Exclusive Write Ownership
- `trading_system/src/ai/factor_suppression.py`
- `trading_system/src/ai/factor_orthogonalizer.py`
- `trading_system/src/ai/ensemble_scorer.py`
- `tests/test_m1_quant_enhancements.py` (or new dedicated test file)

## Verification
Run tests via `.venv\Scripts\pytest`:
- `.venv\Scripts\pytest tests/test_correlation_suppression.py tests/test_factor_orthogonalization.py -v`
- `.venv\Scripts\pytest tests/test_factor_ortho_empirical_stress.py tests/test_score_normalizer.py tests/test_return_maximization_apex.py -v`
- `.venv\Scripts\pytest tests/test_world_class_quant_enhancements.py tests/test_adversarial_ensemble_scorer_challenger.py -v`
- Pass rate must be 100% with 0 failures and 0 regressions.

## 2026-09-03T15:50:34Z
You are Worker M1 (Alpha & Orthogonalization Implementer).
Your working directory is: d:\Finance\code\stock\.agents\teamwork_preview_worker_m1_opt2
Project root / codebase directory is: d:\Finance\code\stock
Authoritative request file: d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md (specifically read section ## 2026-09-03T15:32:22Z)
Project rules and architecture: d:\Finance\code\stock\AGENTS.md
Project plan: d:\Finance\code\stock\.agents\teamwork_preview_orchestrator_quant_opt2\PROJECT.md
Your dispatch instructions: d:\Finance\code\stock\.agents\teamwork_preview_worker_m1_opt2\DISPATCH.md

Input technical implementation plans:
1. `d:\Finance\code\stock\.agents\explorer_m1_1_opt2\plan_m1_1.md` (Pipeline Sequence Rectification & Statistically Calibrated Suppression)
2. `d:\Finance\code\stock\.agents\explorer_m1_2_opt2\plan_m1_2.md` (Dual-Consensus Spectral Whitening & Noise-Scaled Marchenko-Pastur Floor)
3. `d:\Finance\code\stock\.agents\explorer_m1_3_opt2\plan_m1_3.md` (Tail Convexity, Continuous Bilinear Synergy Kernel & 2D Regime Half-Life Decay)

Your write ownership:
- `trading_system/src/ai/factor_suppression.py`
- `trading_system/src/ai/factor_orthogonalizer.py`
- `trading_system/src/ai/ensemble_scorer.py`
- `tests/test_m1_quant_enhancements.py` (write comprehensive tests for M1 features)

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Mission:
Implement all 6 features of Milestone 1 according to the detailed plans.
Run the test suites using `.venv\Scripts\pytest` to verify that all new features function correctly and all existing tests pass with 100% pass rate and 0 regressions.
Document your changes, build/test commands, and results in `d:\Finance\code\stock\.agents\teamwork_preview_worker_m1_opt2\handoff.md`.
Update `progress.md` with timestamps as your liveness heartbeat.
When finished, send a brief message with your handoff report path.

