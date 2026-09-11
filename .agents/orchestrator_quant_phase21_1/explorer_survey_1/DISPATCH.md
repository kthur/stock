# DISPATCH — explorer_survey_1 (Alpha Signal Survey)

## Task Description
You are the Alpha Signal Explorer for Phase 21 Quant Enhancement.
Your working directory is: `d:\Finance\code\stock\.agents\orchestrator_quant_phase21_1\explorer_survey_1`.
You MUST read `d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md` (specifically section ## 2026-09-10T01:13:45Z) before beginning.

## Investigation Scope
Investigate `src/ai/ensemble_scorer.py` and `src/ai/factor_suppression.py` to examine:
1. Existing Phase 19 (F95, F96.1, F96.2) and Phase 20 (F99 PerfectoidPrismaticCoupler, F100.1 15th-order rank modulation `g_v20(r)`, F100.2 44th-order deadband `apply_tetracontatetragonal_hyperbolic_deadband`, `version >= 20` branching) implementations.
2. Requirements for Phase 21:
   - F103: Derived Motivic Homotopy Type Theory factor coupler in `ensemble_scorer.py` and `factor_suppression.py`.
   - F104.1: 16th-order ultra-convex rank warping function `g_v21(r) = 0.50 + 1.06 * r * exp(gamma_top * r^16)`.
   - F104.2: 48th-order Octatetracontagonal (alpha=48.0) hyperbolic deadband with noise leakage < 10^-26 in `factor_suppression.py`.
   - Version branching (`version >= 21`) in `ensemble_scorer.py` (`combine_predictions`, `apply_smooth_noise_deadband`, etc.).
3. Identify exact file paths, line numbers, function signatures, constants, and interface contracts needed for the implementation worker.

## Output Requirements
- Write your complete survey report to:
  `d:\Finance\code\stock\.agents\orchestrator_quant_phase21_1\explorer_survey_1\survey_report.md`
- Write `handoff.md` in your working directory.
- Send a completion message via `send_message` to orchestrator.
