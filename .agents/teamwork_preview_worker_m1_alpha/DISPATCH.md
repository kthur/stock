# DISPATCH: Milestone 1 — Alpha Signal Specialist

## Working Directory
`d:\Finance\code\stock\.agents\teamwork_preview_worker_m1_alpha`

## Authoritative User Request
`d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md` (Header `## 2026-09-15T21:55:02Z`)

## Architectural Reference
`d:\Finance\code\stock\.agents\teamwork_preview_explorer_survey_1\handoff.md`

## Files Exclusively Owned
- `trading_system/src/ai/factor_suppression.py`
- `trading_system/src/ai/ensemble_scorer.py`
- `tests/test_phase45_alpha.py`

## Mandate & Detailed Requirements (F199, F200.1, F200.2)
1. **`factor_suppression.py`**:
   - Implement `apply_centahexaoctagonal_hyperbolic_deadband(z, delta_noise=0.035, alpha_pos=168.0, regime=None, **kwargs)` with $\alpha=168.0$, noise leakage $< 10^{-96}$ for $|z| \le 0.0003$, and 100% transmission for $|z| \ge 0.150$.
   - Add aliases: `compute_phase45_deadband`, `apply_phase45_deadband`, `apply_centahexaocta_hyperbolic_deadband`, `centahexaoctagonal_deadband`, `phase45_deadband`.
   - Implement `compute_phase45_hyperconvex_rank_modulation(ranks, gamma_top=5.10, z_denoised=None)`:
     $g_{\text{v45}}(r) = 0.50 + 1.52 \cdot r \cdot \exp(\gamma_{\text{top}} \cdot r^{40})$ when $z \ge 0$, and $1.35 - 1.00 \cdot r$ when $z < 0$.
   - Define `REGIME_GAMMA_TOP_V45`: `BULL_LOW_VOL`: 5.10, `RECOVERY`: 4.90, `BULL_HIGH_VOL`: 4.80, `SIDEWAYS_LOW_VOL`: 4.60, `BEAR_LOW_VOL`: 4.30, `SIDEWAYS_HIGH_VOL`: 3.30, `BEAR_HIGH_VOL`: 3.00, `PANIC`: 1.95, `CRISIS`: 1.55, Default: 5.10.
   - Implement `get_regime_adaptive_gamma_top_v45(regime)`.
   - Update `apply_smooth_deadband_attenuation` version dispatching: for `version >= 45`, use $\alpha=168.0$.
   - Update `__all__` and `__getattr__` dynamic resolution hooks.

2. **`ensemble_scorer.py`**:
   - Add safe definition of `apply_centahexaoctagonal_hyperbolic_deadband` and `compute_phase45_hyperconvex_rank_modulation`.
   - Implement `QuantumGeometricLanglandsKacMoodyWhittakerCoupler` class (F199):
     - Constructor: $\kappa_{\text{km\_whit}}=8.50$, $\theta_0=0.50$, parameters: $\lambda_{\text{kac\_moody}}=0.62$, $\lambda_{\text{whittaker}}=0.38$, $\lambda_{\text{geometric\_langlands}}=0.26$, $\lambda_{\text{superalgebra}}=0.190$, $\lambda_{\text{chiral\_affine}}=0.140$, $\lambda_{\text{categorical}}=0.090$, $\lambda_{\text{chiral}}=0.056$, $\lambda_{\text{vertex}}=0.034$, $\lambda_{\text{conformal}}=0.025$.
     - Pairwise matrix $\omega_{jk} = 1.0 / (|j - k|^{1.30})$.
     - Compute obstruction complex $E_{\text{km\_whit}}$, topological defect invariant $Z_{\text{km\_whit}}$, coupling factor $h_{\text{km\_whit}} = \text{clip}(\exp(-\kappa \cdot E) \cdot Z, 10^{-6}, 1.0)$, and $\text{FERI}_{\text{v45}} = 1.0 / (1.0 + E + (1.0 - Z))$.
     - Define aliases and classmethod `compute_quantum_geometric_langlands_kac_moody_whittaker_coupling` on `EnsembleScoringEngine`.
   - In `combine_predictions`:
     - Version >= 45 branch: $g_{\text{v45}}(r) = 0.50 + 1.52 \cdot r \cdot \exp(\gamma_{\text{top}} \cdot r^{40})$.
     - Coupler evaluation: compute `h_km_whit` and `z_km_whit`.
     - Harmony expansion: add $+ (2.55 \cdot h_{\text{km\_whit}} \cdot z_{\text{km\_whit}} \text{ if version } \ge 45 \text{ else } 0.0)$.
   - In `get_regime_adaptive_gamma_top`: add `version >= 45` dispatching to `REGIME_GAMMA_TOP_V45`.
   - In `apply_smooth_noise_deadband`: add `version >= 45` dispatching to `apply_centahexaoctagonal_hyperbolic_deadband`.

3. **`tests/test_phase45_alpha.py`**:
   - Implement 9 tests as specified in `handoff.md` Section 5.1.
   - Run: `python -m pytest tests/test_phase45_alpha.py -v` and `python -m pytest tests/test_phase44_alpha.py -q`.
   - Ensure 100% pass rate.

## Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## 2026-09-15T22:02:30Z
You are Worker 1 (Alpha Signal Specialist) for Phase 45 Full Team Quant Enhancement.
Your working directory is: d:\Finance\code\stock\.agents\teamwork_preview_worker_m1_alpha
Your task assignment is in: d:\Finance\code\stock\.agents\teamwork_preview_worker_m1_alpha\DISPATCH.md
Architectural reference: d:\Finance\code\stock\.agents\teamwork_preview_explorer_survey_1\handoff.md
Mandatory user request: d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md (Header ## 2026-09-15T21:55:02Z)

Files you exclusively own:
- trading_system/src/ai/factor_suppression.py
- trading_system/src/ai/ensemble_scorer.py
- tests/test_phase45_alpha.py

Implement F199, F200.1, F200.2, and write tests/test_phase45_alpha.py as specified in DISPATCH.md.
Execute unit tests using python -m pytest tests/test_phase45_alpha.py -v and ensure 100% pass rate.
Verify backward compatibility with tests/test_phase44_alpha.py.
