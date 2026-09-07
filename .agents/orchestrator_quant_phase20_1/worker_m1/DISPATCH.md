## 2026-09-07T11:47:00Z
You are Worker M1 (Alpha Signal Specialist).
Your working directory is: d:\Finance\code\stock\.agents\orchestrator_quant_phase20_1\worker_m1

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

MANDATORY: Read d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md first (specifically section ## 2026-09-07T11:39:07Z).
Also read:
- d:\Finance\code\stock\.agents\orchestrator_quant_phase20_1\PROJECT.md
- d:\Finance\code\stock\.agents\orchestrator_quant_phase20_1\explorer_survey_1\handoff.md

Your exclusive write ownership:
- trading_system/src/ai/factor_suppression.py
- trading_system/src/ai/ensemble_scorer.py
- tests/test_phase20_signal_enhancement.py

Tasks:
1. Implement F100.2 44th-order Tetracontatetragonal hyperbolic deadband apply_tetracontatetragonal_hyperbolic_deadband (alpha=44.0, delta_noise=0.035, noise leakage < 10^-24) in factor_suppression.py and ensemble_scorer.py. Update apply_smooth_deadband_attenuation and apply_smooth_noise_deadband for version >= 20.
2. Implement F100.1 15th-order ultra-convex rank warping compute_phase20_hyperconvex_rank_modulation with g_v20(r) = 0.50 + 1.04 * r * exp(gamma_top * r^15) and regime-adaptive gamma_top up to 1.95 in ensemble_scorer.py.
3. Implement F99 Perfectoid Space & Prismatic Cohomology factor coupler PerfectoidPrismaticCoupler (with aliases PerfectoidSpaceCoupler, PrismaticCohomologyCoupler) in ensemble_scorer.py and export in factor_suppression.py. Add static binding compute_perfectoid_prismatic_coupling to EnsembleScoringEngine.
4. Implement version >= 20 branching in combine_predictions and compute_quint_pillar_tensor_synergy (+ 0.65 * h_prism * z_prism).
5. Create tests/test_phase20_signal_enhancement.py verifying noise leakage < 10^-24, 100% pass-through, monotonicity, invariants, and backward compatibility.
6. Verify by running tests:
   .venv\Scripts\python.exe -m pytest tests/test_phase20_signal_enhancement.py tests/test_phase19_signal_enhancement.py -v
7. Write your handoff report to:
   d:\Finance\code\stock\.agents\orchestrator_quant_phase20_1\worker_m1\handoff.md
   and notify the orchestrator via send_message.
