## 2026-09-06T15:11:33Z

You are Worker subagent (identity: worker_alpha_r1).
Working directory: d:\Finance\code\stock\.agents\worker_alpha_r1
Original Request Path: d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md
Please read d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md (specifically section ## 2026-09-06T15:02:05Z).

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Technical blueprints & explorer survey report:
Read `d:\Finance\code\stock\.agents\explorer_survey_1\handoff.md` for exact line numbers, formulas, and architecture.

Exclusive File Ownership:
- `trading_system/src/ai/ensemble_scorer.py`
- `trading_system/src/ai/factor_suppression.py`
DO NOT touch any other source files.

Your Mission (Milestone 1 - R1 Alpha Signal Enhancement):
1. `trading_system/src/ai/factor_suppression.py`:
   - Implement `apply_tetracontagonal_hyperbolic_deadband`: Exponent alpha=40.0, delta_noise=0.035, noise leakage < 10^-22 in |z| <= 0.005.
   - Update `apply_smooth_deadband_attenuation` and `apply_smooth_noise_deadband` with `if version >= 19:` branch dispatching to `apply_tetracontagonal_hyperbolic_deadband`.
2. `trading_system/src/ai/ensemble_scorer.py`:
   - Implement class `LurieInfinityToposCoupler` (and alias `LurieInfinityToposCoupler` / `LurieToposCoupler`) with hypercompletion obstruction energy E_lurie (6th-degree polynomial), Kan fibrational homotopy cycle invariant Z_lurie, and coupling factor h_lurie.
   - Add method `compute_lurie_infinity_topos_coupling` on `EnsembleScoringEngine`.
   - Update `compute_quint_pillar_tensor_synergy` with `if version >= 19:` branch:
     `harmony_factor = pd.Series(1.0 + (... + 0.55 * h_lurie * z_lurie) * (p_mean > 0.35).astype(float), index=scores_df.index)`.
   - Implement `compute_phase19_hyperconvex_rank_modulation`: g_v19(r) = 0.50 + 1.02 * r * exp(gamma_top * r^14) for z >= 0, and 1.35 - 1.00 * r for z < 0.
   - Update `combine_predictions` with `if int(version) >= 19:` rank modulation branch.
   - Update `get_regime_adaptive_gamma_top` with `version >= 19` branch: CRISIS: 0.38, BEAR_HIGH_VOL: 0.58, BEAR_LOW_VOL: 0.85, SIDEWAYS_HIGH_VOL: 1.10, SIDEWAYS_LOW_VOL: 1.45, BULL_HIGH_VOL: 1.65, BULL_LOW_VOL: 1.90, Default: 1.50.
   - Add static method bindings and module registrations (`apply_tetracontagonal_hyperbolic_deadband`, `compute_phase19_hyperconvex_rank_modulation`, etc.).
3. Verification:
   Run unit tests via `.venv\Scripts\python.exe -m pytest tests/test_factor_orthogonalization.py tests/test_correlation_suppression.py -v` (and any related tests).
   Ensure 100% pass rate.
4. Deliver `handoff.md` in `d:\Finance\code\stock\.agents\worker_alpha_r1\handoff.md` and message parent when complete.
