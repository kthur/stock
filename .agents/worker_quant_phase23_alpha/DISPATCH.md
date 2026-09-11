# Worker Dispatch: R1 Alpha Signal Specialist (Phase 23)

## Mission
Implement Feature F111, F112.1, and F112.2 in `src/ai/ensemble_scorer.py` and `src/ai/factor_suppression.py`.

## Reference Documents
- `d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md` (Section ## 2026-09-11T07:03:36Z)
- `d:\Finance\code\stock\.agents\explorer_quant_phase23_survey1\handoff.md` (Architecture blueprint)
- `d:\Finance\code\stock\AGENTS.md`

## Exclusive File Ownership
You exclusively own and may edit:
- `src/ai/ensemble_scorer.py` (or `trading_system/src/ai/ensemble_scorer.py` depending on repo structure)
- `src/ai/factor_suppression.py` (or `trading_system/src/ai/factor_suppression.py`)
Do NOT touch files owned by other workers.

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A forensic auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Technical Requirements
1. **F111 Toposic Geometric Langlands & Derived Satake Equivalence Coupler**:
   - Implement `ToposicGeometricLanglandsCoupler` (and aliases `ToposicLanglandsCoupler`, `DerivedSatakeCoupler`, `GeometricLanglandsCoupler`, `HeckeEigensheafCoupler`) in `ensemble_scorer.py` and register it in `factor_suppression.py`.
   - Compute Bun_G bundle stack obstruction energy $E_{\text{langlands}}$, Satake spectrum homotopy invariant $Z_{\text{satake}}$, coupling factor $h_{\text{langlands}}$, and Factor Entanglement Reduction Index $\text{FERI\_v23} = \frac{1}{1.0 + E_{\text{langlands}} + (1.0 - Z_{\text{satake}})}$.
   - In `compute_quint_pillar_tensor_synergy`: under `if version >= 23:`, compute `langlands_res`, extract `h_langlands` and `z_satake`, and add `+ 0.95 * h_langlands * z_satake` into `harmony_factor`.
   - Add classmethod/static bindings in `EnsembleScoringEngine` (`compute_toposic_geometric_langlands_coupling`, `compute_derived_satake_coupling`, etc.).
2. **F112.1 18th-Order Hyper-Convex Rank Modulation $g_{v23}(r)$**:
   - Implement `compute_phase23_hyperconvex_rank_modulation(ranks, gamma_top=1.0, z_denoised=None)` in `ensemble_scorer.py` (and alias `compute_phase23_rank_warping`).
   - Formula: for $z_{\text{denoised}} \ge 0$: $0.50 + 1.10 \cdot r \cdot \exp(\gamma_{\text{top}} \cdot r^{18})$. For $z_{\text{denoised}} < 0$: $1.35 - 1.00 \cdot r$.
   - In `get_regime_adaptive_gamma_top`: add `if int(version) >= 23:` branch returning:
     - CRISIS: 0.48
     - BEAR_HIGH_VOL: 0.70
     - BEAR_LOW_VOL: 1.00
     - SIDEWAYS_HIGH_VOL: 1.40
     - SIDEWAYS_LOW_VOL: 1.85
     - BULL_HIGH_VOL: 2.10
     - BULL_LOW_VOL: 2.40 (peak expansion)
     - default: 1.90
   - In `combine_predictions`: under `if int(version) >= 23:`, call the 18th-order rank modulation.
3. **F112.2 56th-Order Hexaquinquagintagonal Hyperbolic Deadband**:
   - Implement `apply_hexaquinquagintagonal_hyperbolic_deadband` with $\alpha_{\text{pos}} = 56.0$ in `factor_suppression.py` and register it in `ensemble_scorer.py`.
   - Verify noise leakage $< 10^{-30}$ for $|z| \le 0.005$.
   - In `apply_smooth_noise_deadband`: under `if int(version) >= 23:`, dispatch to 56th-order deadband with `eff_alpha = 56.0`.

## Verification & Output
- Run pytest on signal enhancement tests (e.g. `.venv/bin/pytest tests/test_phase22_signal_enhancement.py` or existing tests) to verify no regressions.
- Document all changes, line numbers, formulas, and test results in `d:\Finance\code\stock\.agents\worker_quant_phase23_alpha\handoff.md`.
- Send a completion message when done.

## 2026-09-11T07:12:44Z
You are Worker 1: Alpha Signal Specialist for Phase 23 Full Team Quantitative Enhancement.
Your working directory: d:\Finance\code\stock\.agents\worker_quant_phase23_alpha
Dispatch task file: d:\Finance\code\stock\.agents\worker_quant_phase23_alpha\DISPATCH.md
Original user request: d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md (See section ## 2026-09-11T07:03:36Z)
Survey report: d:\Finance\code\stock\.agents\explorer_quant_phase23_survey1\handoff.md
Project rules: d:\Finance\code\stock\AGENTS.md

Exclusive write ownership:
- `src/ai/ensemble_scorer.py` (and `trading_system/src/ai/ensemble_scorer.py`)
- `src/ai/factor_suppression.py` (and `trading_system/src/ai/factor_suppression.py`)
DO NOT edit files owned by other workers.

Mandatory Integrity Warning:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A forensic auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Tasks:
1. Implement F111 Toposic Geometric Langlands & Derived Satake Equivalence Coupler in `ensemble_scorer.py` and `factor_suppression.py` (Bun_G stack, D(Gr_G), Hecke eigensheaf E_langlands, Satake spectrum homotopy invariant Z_satake, FERI_v23, harmony_factor weight + 0.95 * h_langlands * z_satake).
2. Implement F112.1 18th-Order Hyper-Convex Rank Modulation g_v23(r) = 0.50 + 1.10 * r * exp(gamma_top * r^18) with regime-adaptive gamma_top up to 2.40 (BULL_LOW_VOL 2.40, BULL_HIGH_VOL 2.10, SIDEWAYS_LOW_VOL 1.85, SIDEWAYS_HIGH_VOL 1.40, BEAR_LOW_VOL 1.00, BEAR_HIGH_VOL 0.70, CRISIS 0.48) in `ensemble_scorer.py` under version >= 23.
3. Implement F112.2 56th-Order Hexaquinquagintagonal (alpha=56.0) Hyperbolic Deadband in `factor_suppression.py` and hook into `apply_smooth_noise_deadband` under version >= 23.
4. Run build/tests using `.venv/bin/pytest tests/test_phase22_signal_enhancement.py` to verify 100% pass and no regressions.
5. Write your complete handoff report to `d:\Finance\code\stock\.agents\worker_quant_phase23_alpha\handoff.md` and send a completion message.

