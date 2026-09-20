# DISPATCH: Milestone M1 Worker (Alpha Signal Disentanglement & Hyper-Convex Rank Modulation)

## Working Directory
d:\Finance\code\stock\.agents\teamwork_preview_worker_m1

## Exclusive File Ownership
You EXCLUSIVELY own and may modify:
- `src/ai/ensemble_scorer.py`
- `src/ai/factor_suppression.py`
- `tests/test_phase63_alpha.py`
DO NOT modify any files outside this exclusive list.

## Authoritative Inputs
- `d:\Finance\code\stock\ORIGINAL_REQUEST.md` (Read this first)
- Explorer 1 Handoff Report: `d:\Finance\code\stock\.agents\teamwork_preview_explorer_survey_alpha_1\handoff.md` (Contains exact line numbers, formulas, and blueprint)

## Objectives & Detailed Tasks
1. `src/ai/factor_suppression.py`:
   - Implement `apply_bicentatriacontahexagonal_hyperbolic_deadband` with `alpha_pos=312.0`, `delta_noise=0.035` and aliases (`compute_phase63_deadband`, `apply_phase63_deadband`, `apply_bicentatriacontahexagonal_deadband`, `bicentatriacontahexagonal_deadband`, `phase63_deadband`).
   - Implement `REGIME_GAMMA_TOP_V63` (base 15.00 for `BULL_LOW_VOL`) and `get_regime_adaptive_gamma_top_v63`.
   - Implement `compute_phase63_hyperconvex_rank_modulation`:
     $$g_{\text{v63}}(r) = 0.50 + 2.15 \cdot r \cdot \exp(\gamma_{\text{top}} \cdot r^{58})$$ for $z \ge 0$
     $$g_{\text{neg}}(r) = 1.35 - 1.00 \cdot r$$ for $z < 0$
     along with aliases (`compute_phase63_rank_warping`, `compute_phase63_rank_modulation`, `phase63_rank_modulation`, `phase63_hyperconvex_rank_modulation`).
2. `src/ai/ensemble_scorer.py`:
   - Inject Phase 63 deadband and rank modulation functions and aliases.
   - Update `QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler`:
     - Update defaults to `kappa_monster_whit: float = 18.00`, `lambda_monster: float = 0.99995`.
     - Extend `a_monster_whit` with 122nd and 124th order terms:
       `+ (1.0 / 122.0) * (self.lambda_conformal * 1e-19) * (diff ** 122)`
       `+ (1.0 / 124.0) * (self.lambda_conformal * 4e-20) * (diff ** 124)`
     - Extend `defect` with 61st and 62nd order terms:
       `+ (self.lambda_vertex * 1e-21) * (pn[j]**61 - pn[k]**61)`
       `+ (self.lambda_vertex * 4e-22) * (pn[j]**62 - pn[k]**62)`
     - Define `feri_v63` and export `"FERI_v63"` and `"feri_v63"`.
     - Export 30+ aliases for Phase 63 / HigherHomology13.
     - Update dynamic registration block `setattr(_fs_module, ...)`.
     - In `combine_predictions`: update harmony factor gating boost to `4.35 * h_monster_whit * z_monster_whit` when `version >= 63` and `p_mean > 0.35`.
     - In `apply_smooth_noise_deadband`: add `version >= 63` branch activating `eff_alpha = 312.0` and calling `apply_bicentatriacontahexagonal_hyperbolic_deadband`.
     - Add static bindings on `EnsembleScoringEngine`.
3. Create `tests/test_phase63_alpha.py` (mirrored from `tests/test_phase62_alpha.py` covering all 9 test dimensions).
4. Run build/tests:
   ```powershell
   .venv\Scripts\pytest.exe tests/test_phase63_alpha.py tests/test_phase62_alpha.py -v
   ```
   Ensure 100% pass rate.

## MANDATORY INTEGRITY WARNING
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Deliverable
Write a complete, self-contained `handoff.md` in your working directory summarizing:
- Exact changes made
- Test execution output
- Verification results

## 2026-09-20T13:04:17Z
You are Worker M1 specializing in Track A: Alpha Signal Disentanglement & Hyper-Convex Rank Modulation (Features F286, F287.1, F287.2).

Your working directory is:
d:\Finance\code\stock\.agents\teamwork_preview_worker_m1

Read the authoritative original request at:
d:\Finance\code\stock\ORIGINAL_REQUEST.md
and your dispatch instructions at:
d:\Finance\code\stock\.agents\teamwork_preview_worker_m1\DISPATCH.md
and the survey blueprint at:
d:\Finance\code\stock\.agents\teamwork_preview_explorer_survey_alpha_1\handoff.md

Your exclusive file ownership:
- `src/ai/ensemble_scorer.py`
- `src/ai/factor_suppression.py`
- `tests/test_phase63_alpha.py`

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Implement all Phase 63 features (F286, F287.1, F287.2), create `tests/test_phase63_alpha.py`, and run `pytest tests/test_phase63_alpha.py tests/test_phase62_alpha.py -v`.
Document all work and test outputs in `handoff.md` and send a message back to parent.
