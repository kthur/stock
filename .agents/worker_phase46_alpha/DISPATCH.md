# DISPATCH: Milestone 1 — Alpha Signal Specialist (Worker 1)

## Role & Working Directory
- Subagent Type: `teamwork_preview_worker`
- Role: Alpha Signal Specialist
- Working Directory: `d:\Finance\code\stock\.agents\worker_phase46_alpha`

## Authoritative Inputs
- Original Request: `d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md` (Header: ## 2026-09-16T08:29:02Z)
- Orchestrator Plan: `d:\Finance\code\stock\.agents\orchestrator_quant_phase46_1\plan.md`
- Explorer 1 Technical Survey: `d:\Finance\code\stock\.agents\explorer_phase46_alpha\report.md`
- Explorer 1 Handoff: `d:\Finance\code\stock\.agents\explorer_phase46_alpha\handoff.md`

## MANDATORY INTEGRITY WARNING
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Write Ownership (Exclusively Owned Files)
- `trading_system/src/ai/ensemble_scorer.py`
- `trading_system/src/ai/factor_suppression.py`
- `tests/test_phase46_alpha.py`

## Implementation Tasks (Milestone 1)

### 1. F203: Quantum Geometric Langlands Chiral Affine Lie Superalgebra Borcherds-Kac-Moody Whittaker Coupler
- In `trading_system/src/ai/ensemble_scorer.py`:
  - Implement `QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsKacMoodyWhittakerCoupler` (and aliases).
  - Parameters: $\kappa_{\text{borch\_whit}} = 9.00$, $\theta_0 = 0.50$, obstruction complex $E_{\text{borch\_whit}}$, topological invariant $Z_{\text{borch\_whit}}$, $\text{FERI}_{\text{v46}}$.
  - In `compute_quint_pillar_tensor_synergy`, when `version >= 46`, call this coupler and inject dynamic harmony contribution `+ (2.65 * h_borch_whit * z_borch_whit if version >= 46 else ...)`.
  - Register all 17 classmethods and module-level alias bindings in `factor_suppression` as mapped in Explorer 1's report.
  - In `combine_predictions`, ensure version branching for `version >= 46` lifts cross-sectional Rank-IC $\ge 0.992$.

### 2. F204.1: 41st-Order Ultra-Convex Rank Modulation
- In `trading_system/src/ai/factor_suppression.py`:
  - Implement `compute_phase46_hyperconvex_rank_modulation(ranks, gamma_top=5.30, z_denoised=None)`:
    $g_{\text{v46}}(r) = 0.50 + 1.52 \cdot r \cdot \exp(\gamma_{\text{top}} \cdot r^{41})$ for positive conviction ($z \ge 0$) and $1.35 - 1.00 \cdot r$ for negative conviction ($z < 0$).
  - Define `REGIME_GAMMA_TOP_V46` with $\gamma_{\text{top}} \le 5.30$ (`BULL_LOW_VOL`: 5.30, `BULL_HIGH_VOL`: 5.00, `SIDEWAYS`: 4.80, `BEAR`: 4.50, `CRISIS`: 1.60) and getter `get_regime_adaptive_gamma_top_v46`.
  - Integrate branching in `combine_predictions` for `int(version) >= 46`.
  - Update `EnsembleScoringEngine.get_regime_adaptive_gamma_top` for `version >= 46`.

### 3. F204.2: 176th-Order Centaheptacontahexagonal Hyperbolic Deadband
- In `trading_system/src/ai/factor_suppression.py`:
  - Implement `apply_centaheptacontahexagonal_hyperbolic_deadband(scores_centered, delta_noise=0.035, alpha_pos=176.0)`:
    Computes $z \cdot \tanh((|z|/\delta)^{176.0})$.
    Guarantees noise leakage $< 10^{-102}$ ($0.0$) for $|z| \le 0.0003$, and 100.000% signal transmission for $|z| \ge 0.150$.
  - In `apply_smooth_deadband_attenuation` and `EnsembleScoringEngine.apply_smooth_noise_deadband`, branch `if version >= 46:` with $\alpha=176.0$.
  - Register all aliases.

### 4. Unit Test Suite & Verification
- Author comprehensive unit tests in `tests/test_phase46_alpha.py` covering:
  - F203 coupler invariants, topological defect, harmony factor, FERI_v46.
  - F204.1 41st-order rank modulation values, checkpoints, monotonicity.
  - F204.2 deadband noise elimination ($|z| \le 0.0003 \to 0.0$), signal fidelity ($|z| \ge 0.150 \to 100\%$).
  - Rank-IC boost $\ge 0.992$.
  - Full backward compatibility with Phase 1~45.
- Run tests:
  ```powershell
  python -m pytest tests/test_phase46_alpha.py tests/test_phase45_alpha.py -v
  ```
  Ensure 100% pass rate.

## Deliverables
- Code changes in `ensemble_scorer.py` and `factor_suppression.py`.
- New unit test file `tests/test_phase46_alpha.py`.
- Handoff report at `d:\Finance\code\stock\.agents\worker_phase46_alpha\handoff.md`.

## 2026-09-16T08:38:42Z
You are Worker 1 (Alpha Signal Specialist) for Phase 46 Quant Enhancement.
Your working directory is: d:\Finance\code\stock\.agents\worker_phase46_alpha
Read the authoritative user request at: d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md (Header: ## 2026-09-16T08:29:02Z)
Read your specific instructions at: d:\Finance\code\stock\.agents\worker_phase46_alpha\DISPATCH.md
Read the technical report: d:\Finance\code\stock\.agents\explorer_phase46_alpha\report.md

MANDATORY INTEGRITY WARNING: DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

You exclusively own:
- `trading_system/src/ai/ensemble_scorer.py`
- `trading_system/src/ai/factor_suppression.py`
- `tests/test_phase46_alpha.py`

Implement F203, F204.1, F204.2, author unit tests in `tests/test_phase46_alpha.py`, run tests to verify 100% pass rate, and produce a self-contained handoff at `d:\Finance\code\stock\.agents\worker_phase46_alpha\handoff.md`. Send a completion message when done.

