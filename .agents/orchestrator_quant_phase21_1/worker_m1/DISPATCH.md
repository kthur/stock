# DISPATCH — worker_m1 (Alpha Signal Specialist - Milestone M1)

## Mandatory Reading
You MUST read `d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md` (specifically section ## 2026-09-10T01:13:45Z) and `d:\Finance\code\stock\.agents\orchestrator_quant_phase21_1\PROJECT.md` before starting work.
Also read the detailed survey findings in `d:\Finance\code\stock\.agents\orchestrator_quant_phase21_1\explorer_survey_1\survey_report.md`.

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Write Ownership & Exclusivity
You have EXCLUSIVE write ownership of:
- `trading_system/src/ai/ensemble_scorer.py`
- `trading_system/src/ai/factor_suppression.py`
You MUST NOT edit any risk, OMS, execution, or benchmark files.

## Technical Specifications & Requirements
1. **Feature F103: Derived Motivic Homotopy Type Theory Coupler**:
   - Implement `DerivedMotivicHomotopyTypeTheoryCoupler` in `ensemble_scorer.py` (and export in `factor_suppression.py`).
   - Aliases: `DerivedMotivicCoupler`, `MotivicHomotopyTypeTheoryCoupler`, `MotivicHomotopyCoupler`.
   - Method: `compute(pillar_scores, theta_0=0.25, kappa_motivic=2.60, lambda_motivic=0.16, lambda_univalent=0.07, lambda_frob=0.045, lambda_slice=0.025, epsilon_reg=1e-6) -> Dict[str, Any]`.
   - Output dictionary keys: `h_motivic`, `z_motivic`, `e_motivic`, `h_decay`, `FERI_v21`, `Z_motivic`, `E_motivic`, `h_derived`, `z_derived`, `e_derived`, `h_homotopy`, `z_homotopy`, `e_homotopy`.
   - In `compute_quint_pillar_tensor_synergy`: Version $\ge 21$ adds `+ 0.75 * h_motivic * z_motivic` to `harmony_factor`.
2. **Feature F104.1: 16th-Order Ultra-Convex Rank Warping**:
   - Function: `compute_phase21_hyperconvex_rank_modulation(ranks, gamma_top=1.0, z_denoised=None) -> Union[pd.Series, np.ndarray, float]`.
   - Formula: For $z_{\text{denoised}} \ge 0$, $g_{v21}(r) = 0.50 + 1.06 \cdot r \cdot \exp(\gamma_{\text{top}} \cdot r^{16})$. For $z_{\text{denoised}} < 0$, $1.35 - 1.00 \cdot r$.
   - Regime adaptive $\gamma_{\text{top}}$ schedule for Phase 21: BULL_LOW_VOL (2.00), BULL_HIGH_VOL (1.75), SIDEWAYS_LOW_VOL (1.55), SIDEWAYS_HIGH_VOL (1.20), BEAR_LOW_VOL (0.90), BEAR_HIGH_VOL (0.62), CRISIS (0.42), default (1.60).
3. **Feature F104.2: 48th-Order Octatetracontagonal Hyperbolic Deadband**:
   - Function: `apply_octatetracontagonal_hyperbolic_deadband(scores_centered, delta_noise=0.035, delta_neg=None, alpha_pos=48.0, alpha_neg=None, regime=None)`.
   - Formula: $z_{\text{denoised}} = z \cdot \tanh((|z| / \delta_{\text{eff}})^{48})$.
   - Leakage for $|z| \le 0.005$ must be $< 10^{-26}$.
4. **Version $\ge 21$ Engine Dispatch**:
   - Branch in `EnsembleScoringEngine.combine_predictions(..., version=21)` and `apply_smooth_noise_deadband(..., version=21)`.
   - Ensure all static bindings and backward compatibility for versions 1..20 remain intact.
5. **Testing & Verification**:
   - Run tests using `.venv\Scripts\python.exe -m pytest tests/test_phase20_signal_enhancement.py` (or newly created unit tests for phase 21 signals) to verify 100% pass without breaking existing tests.

## Deliverables
- Genuine implementation of M1 in `src/ai/ensemble_scorer.py` and `src/ai/factor_suppression.py`.
- Write `handoff.md` with:
  * Files modified and line numbers
  * Test execution commands and passing output
  * Verification of all interface contracts and mathematical formulas

## 2026-09-10T01:23:37Z
You are worker_m1, the Alpha Signal Specialist for Phase 21 Quant Enhancement.
Your working directory is: d:\Finance\code\stock\.agents\orchestrator_quant_phase21_1\worker_m1
Read d:\Finance\code\stock\.agents\orchestrator_quant_phase21_1\worker_m1\DISPATCH.md, d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md (specifically ## 2026-09-10T01:13:45Z), and d:\Finance\code\stock\.agents\orchestrator_quant_phase21_1\PROJECT.md before starting.
Also inspect d:\Finance\code\stock\.agents\orchestrator_quant_phase21_1\explorer_survey_1\survey_report.md for technical details.
Implement Feature F103 (Derived Motivic Homotopy Type Theory coupler), Feature F104.1 (16th-order ultra-convex rank warping g_v21(r)), Feature F104.2 (48th-order Octatetracontagonal deadband), and version >= 21 branching in src/ai/ensemble_scorer.py and src/ai/factor_suppression.py.
DO NOT CHEAT. All implementations must be genuine.
Run tests using .venv\Scripts\python.exe -m pytest to verify 100% pass without regressions.
Write handoff.md in your working directory and send a completion message to the orchestrator.
