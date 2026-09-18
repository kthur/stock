# DISPATCH: Worker M1 — Alpha Signal Specialist (Modeler)

## Working Directory
d:\Finance\code\stock\.agents\teamwork_preview_worker_m1_1

## Role & Mission
You are the Alpha Signal Specialist (Modeler) for Phase 55 Quantitative Alpha Enhancement.
Your mission is to implement Features F246, F247.1, and F247.2, and create `tests/test_phase55_alpha.py`.

## Mandatory Reading
1. `d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md` (Header: `## 2026-09-18T03:36:46Z`)
2. `d:\Finance\code\stock\.agents\teamwork_preview_explorer_survey_1\survey_report.md`
3. `d:\Finance\code\stock\.agents\teamwork_preview_explorer_survey_1\handoff.md`

## Exclusive Write Ownership
- `trading_system/src/ai/ensemble_scorer.py`
- `trading_system/src/ai/factor_suppression.py`
- `tests/test_phase55_alpha.py`
Do NOT edit any other files.

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Technical Requirements
1. **F246: Quantum Geometric Langlands Chiral Affine Lie Superalgebra Borcherds-Moonshine Monster Whittaker Coupler (`src/ai/ensemble_scorer.py`)**:
   - Monster module $V^\natural$ partition polynomial deformation up to 90th/92nd order:
     - 90th order: `+ (1.0 / 90.0) * (self.lambda_conformal * 0.000000000001) * (diff ** 90)`
     - 92nd order: `+ (1.0 / 92.0) * (self.lambda_conformal * 0.0000000000004) * (diff ** 92)`
   - Topological defect invariant terms up to 45th/46th order:
     - 45th order: `+ (self.lambda_vertex * 0.00000000000001) * (pn[j]**45 - pn[k]**45)`
     - 46th order: `+ (self.lambda_vertex * 0.000000000000004) * (pn[j]**46 - pn[k]**46)`
   - Compute and export `FERI_v55` and `feri_v55`:
     `feri_v55 = 1.0 / (1.0 + e_monster_whit + (1.0 - z_monster_whit))`
   - Gated harmony factor boost in `combine_predictions`:
     `3.55 if version >= 55 else (3.45 if version >= 54 else ...)`
   - Export 28+ backward-compatible aliases on `ensemble_scorer.py` and `_fs_module` (`Phase55Coupler`, `QuantumGeometricLanglandsBorcherdsMoonshineMonsterWhittakerDrinfeldHigherHomology5Coupler`, `LieSuperalgebraBorcherdsMoonshineMonsterWhittakerCouplerV55`, etc.).

2. **F247.1: 50th-Order Hyper-Convex Rank Modulation (`src/ai/factor_suppression.py`)**:
   - Implement `compute_phase55_hyperconvex_rank_modulation`:
     $g_{\text{v55}}(r) = 0.50 + 1.82 \cdot r \cdot \exp(\gamma_{\text{top}} \cdot r^{50})$
   - Implement `REGIME_GAMMA_TOP_V55` with `BULL_LOW_VOL: 10.20`, `BULL_HIGH_VOL: 7.14`, `SIDEWAYS_LOW_VOL: 5.10`, `SIDEWAYS_HIGH_VOL: 3.57`, `BEAR_LOW_VOL: 2.04`, `BEAR_HIGH_VOL: 1.53`, `CRISIS: 1.02`.
   - Implement `get_regime_adaptive_gamma_top_v55(regime_name: str) -> float`.
   - Ensure $g(1.0) \approx 48964.28 > 500.0$ and lower 70% is dampened below 1.82.
   - Export aliases and static bindings in `RegimeFactorSuppressionEngine`.

3. **F247.2: 248th-Order Bicentaoctatetracontagonal Hyperbolic Noise Deadband (`src/ai/factor_suppression.py` and `src/ai/ensemble_scorer.py`)**:
   - Implement `apply_bicentaoctatetracontagonal_hyperbolic_deadband(z, delta_eff=0.035, alpha=248.0)`.
   - Update `apply_smooth_noise_deadband` in `ensemble_scorer.py` for `int(version) >= 55` to select `eff_alpha = 248.0` and invoke `apply_bicentaoctatetracontagonal_hyperbolic_deadband`.
   - Ensure noise leakage for $|z| \le 0.00035$ is strictly $< 10^{-168}$ (underflows to 0.0 in float64) and signal preservation for $|z| \ge 0.150$ is 100.0%.

4. **Testing & Verification**:
   - Create `tests/test_phase55_alpha.py` following the 9 test specifications from Survey Explorer 1's report.
   - Execute:
     `.venv\Scripts\python.exe -m pytest tests/test_phase55_alpha.py -v`
     `.venv\Scripts\python.exe -m pytest tests/test_phase54_alpha.py -v`
   - Confirm 100% test pass and zero regressions.

5. **Deliverables**:
   - Document changes in `d:\Finance\code\stock\.agents\teamwork_preview_worker_m1_1\handoff.md`.
   - Report back with `send_message`.

## 2026-09-18T03:48:12Z
You are the Alpha Signal Specialist (Modeler) for Phase 55. Your working directory is d:\Finance\code\stock\.agents\teamwork_preview_worker_m1_1.
Read your dispatch instructions in d:\Finance\code\stock\.agents\teamwork_preview_worker_m1_1\DISPATCH.md, the original request in d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md (header ## 2026-09-18T03:36:46Z), and Explorer 1's survey reports in d:\Finance\code\stock\.agents\teamwork_preview_explorer_survey_1\survey_report.md and handoff.md.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Implement Features F246, F247.1, F247.2 in trading_system/src/ai/ensemble_scorer.py and trading_system/src/ai/factor_suppression.py with strict version >= 55 gating.
Create tests/test_phase55_alpha.py.
Run the test suites:
.venv\Scripts\python.exe -m pytest tests/test_phase55_alpha.py -v
.venv\Scripts\python.exe -m pytest tests/test_phase54_alpha.py -v
Write your handoff.md and send a completion message with send_message.
