# DISPATCH: Alpha Signal Specialist Worker (Phase 54)

## Working Directory
d:\Finance\code\stock\.agents\worker_phase54_alpha

## Mission
Implement Phase 54 Alpha Signal Disentanglement & Ultra-Convex Rank Modulation (Features F241, F242.1, F242.2).

## Exclusive Write Ownership
You EXCLUSIVELY own and may modify:
- `trading_system/src/ai/ensemble_scorer.py` (or `src/ai/ensemble_scorer.py`)
- `trading_system/src/ai/factor_suppression.py` (or `src/ai/factor_suppression.py`)
You MUST NOT modify any other files.

## Technical Requirements & Specifications
Follow the survey report at: `d:\Finance\code\stock\.agents\explorer_phase54_alpha\handoff.md`

### 1. F241: Lie Superalgebra Borcherds-Moonshine Monster Whittaker Coupler
- Extend `QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler` in `ensemble_scorer.py`:
  - Support Monster module $V^\natural$ partition polynomial deformation up to 86th/88th order:
    `+ (1.0 / 86.0) * (self.lambda_conformal * 0.00000000001) * (diff ** 86)`
    `+ (1.0 / 88.0) * (self.lambda_conformal * 0.000000000004) * (diff ** 88)`
  - Extend topological invariant defect up to 43rd/44th order:
    `+ (self.lambda_vertex * 0.0000000000001) * (pn[j]**43 - pn[k]**43)`
    `+ (self.lambda_vertex * 0.00000000000004) * (pn[j]**44 - pn[k]**44)`
  - Parameters: $\kappa_{\text{monster\_whit}}=13.50, \lambda_{\text{monster}}=0.96$
  - Expose `feri_v54` in output dict: `1.0 / (1.0 + e_monster_whit + (1.0 - z_monster_whit))`
  - Export all 28+ backward-compatible method aliases on `EnsembleScoringEngine` and module level
  - In `combine_predictions`: Harmony factor boost $(3.45 \cdot h_{\text{monster\_whit}} \cdot z_{\text{monster\_whit}})$ gated by `version >= 54`.

### 2. F242.1: 49th-Order Hyper-Convex Rank Modulation
- Implement in `factor_suppression.py`:
  `compute_phase54_hyperconvex_rank_modulation(ranks, gamma_top=9.60, z_denoised=None)`
  $$g_{\text{v54}}(r) = 0.50 + 1.78 \cdot r \cdot \exp(\gamma_{\text{top}} \cdot r^{49})$$
  (for $z_{\text{denoised}} < 0$, use $1.35 - 1.00 \cdot r$)
  `REGIME_GAMMA_TOP_V54` table: `BULL_LOW_VOL: 9.60`, `BULL_HIGH_VOL: 7.68`, `SIDEWAYS: 5.76`, `BEAR: 1.92`, `CRISIS: 0.96`, etc.
  Dampens lower 70% below 1.78 while expanding top 1% convexity $g(1.0) \approx 26282 > 500.0$.
  Export functions, staticmethod bindings on `EnsembleScoringEngine` and `RegimeFactorSuppressionEngine`.

### 3. F242.2: 240th-Order Bicentatetracontagonal Hyperbolic Noise Deadband
- Implement `apply_bicentatetracontagonal_hyperbolic_deadband`:
  $$z_{\text{denoised}} = z \cdot \tanh((|z|/\delta_{\text{eff}})^{240})$$
  with $\alpha=240.0, \delta=0.035$, eliminating boundary noise leakage to $< 10^{-160}$ while preserving 100% of high-conviction alpha signals ($|z| \ge 0.15$).
  Integrate into `apply_smooth_noise_deadband` and `RegimeFactorSuppressionEngine.apply_hyperbolic_noise_deadband` for `version >= 54`.

### 4. Verification & Testing
- Run test suite: `.venv\Scripts\pytest.exe tests/test_phase53_alpha.py` to ensure zero regression.
- Create or test Phase 54 alpha tests if needed.

## MANDATORY INTEGRITY WARNING
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Output your handoff report to: `d:\Finance\code\stock\.agents\worker_phase54_alpha\handoff.md`.

## 2026-09-18T02:04:52Z
You are the Alpha Signal Specialist Worker for Phase 54 Quantitative Alpha Enhancement.
Your working directory is: d:\Finance\code\stock\.agents\worker_phase54_alpha
Read the authoritative user request at: d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md
Read your dispatch instructions at: d:\Finance\code\stock\.agents\worker_phase54_alpha\DISPATCH.md
Read the technical specification handoff at: d:\Finance\code\stock\.agents\explorer_phase54_alpha\handoff.md

EXCLUSIVE WRITE OWNERSHIP:
You EXCLUSIVELY own and may modify:
- `trading_system/src/ai/ensemble_scorer.py` (or `src/ai/ensemble_scorer.py`)
- `trading_system/src/ai/factor_suppression.py` (or `src/ai/factor_suppression.py`)
You MUST NOT modify any other files.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Implement Features F241, F242.1, and F242.2:
1. F241: Lie superalgebra Borcherds-Moonshine Monster Whittaker Coupler in ensemble_scorer.py (86th/88th partition deformation, 43rd/44th topological defect, kappa=13.50, lambda=0.96, feri_v54, 28+ aliases, harmony factor boost 3.45 * h * z for version >= 54).
2. F242.1: 49th-order hyper-convex rank modulation g_v54(r) = 0.50 + 1.78 * r * exp(gamma_top * r^49) with gamma_top up to 9.60 (BULL_LOW_VOL) in factor_suppression.py.
3. F242.2: 240th-order bicentatetracontagonal hyperbolic deadband z_denoised = z * tanh((|z|/delta_eff)^240) in factor_suppression.py and ensemble_scorer.py for version >= 54.

Verify by running:
`.venv\Scripts\pytest.exe tests/test_phase53_alpha.py`
Document commands, code changes, and test results in `d:\Finance\code\stock\.agents\worker_phase54_alpha\handoff.md`.
Send a completion message when finished.

