# DISPATCH: Worker 1 (Alpha Signal Specialist - R1)

## Identity & Role
- Archetype: teamwork_preview_worker
- Role: Alpha Signal Specialist
- Working directory: `d:\Finance\code\stock\.agents\worker_quant_phase24_alpha`

## Strict File Ownership
You exclusively own and may edit/create ONLY these files:
- `src/ai/ensemble_scorer.py`
- `src/ai/factor_suppression.py`
- `tests/test_phase24_alpha.py`
Do NOT edit any other files.

## Reference Inputs
- Authoritative User Request: `d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md` (Header `## 2026-09-11T10:54:49Z`)
- Explorer 1 Blueprint: `d:\Finance\code\stock\.agents\explorer_quant_phase24_survey1\handoff.md`
- Project Scope: `d:\Finance\code\stock\PROJECT.md`

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Technical Requirements (R1)
1. **Feature F115: Derived Arithmetic Topology & Étale-Motivic Spectral Homotopy Coupler**:
   - Implement `DerivedArithmeticTopologyCoupler` in `src/ai/ensemble_scorer.py` and `src/ai/factor_suppression.py`.
   - Incorporate étale-motivic spectral cohomology $H^*_{\text{ét-mot}}$, Artin-Verdier duality obstruction complex $E_{\text{arithmetic}}$, and motivic L-function spectral invariant $Z_{\text{spectral}}$ ($\theta_0=0.32$, $\kappa=3.20$, degree-16 obstruction action functional).
   - In `compute_quint_pillar_tensor_synergy`, couple with $+ 1.05 \cdot h_{\text{arith}} \cdot z_{\text{spectral}}$.
2. **Feature F116.1: 19th-Order Hyper-Convex Rank Modulation**:
   - Implement $g_{\text{v24}}(r) = 0.50 + 1.12 \cdot r \cdot \exp(\gamma_{\text{top}} \cdot r^{19})$ in `src/ai/factor_suppression.py`.
   - Regime-adaptive $\gamma_{\text{top}} \le 2.50$ (Bull Low Vol: 2.50, Bull High Vol: 2.30, Sideways: 2.10, Bear: 1.85, Crisis: 1.50).
   - Dynamic alias table and export via `__all__` and `__getattr__`.
3. **Feature F116.2: 60th-Order Hexacontagonal Hyperbolic Noise Deadband**:
   - Implement 60th-order Hexacontagonal deadband ($\alpha=60.0$) in `src/ai/factor_suppression.py`.
   - Attenuation $z \cdot \tanh((|z|/\delta)^{60})$, ensuring noise leakage $< 10^{-32}$ on $[-0.005, 0.005]$ and 100.000% transmission for $|z| \ge 0.150$.
   - Integration in `apply_smooth_noise_deadband` under `version >= 24`.
4. **Version Branching (`version >= 24`) in `src/ai/ensemble_scorer.py`**:
   - In `combine_predictions`: dispatch `g_v24` and `compute_derived_arithmetic_topology_coupler`.
   - Maintain 100% backwards compatibility for versions 13–23.
5. **Unit Test Suite (`tests/test_phase24_alpha.py`)**:
   - Implement 14 comprehensive unit tests verifying F115, F116.1, F116.2, aliases, version branching, and extreme convexity.
   - Run tests via `.venv\Scripts\python.exe -m pytest tests/test_phase24_alpha.py tests/test_phase23_*.py -v` to ensure 100% pass and 0 regressions.

Deliver your detailed report in `handoff.md`.

## 2026-09-11T11:03:06Z
You are Worker 1 (Alpha Signal Specialist).
Your working directory is: d:\Finance\code\stock\.agents\worker_quant_phase24_alpha
Read your dispatch at: d:\Finance\code\stock\.agents\worker_quant_phase24_alpha\DISPATCH.md
Read the authoritative user request at: d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md (Header ## 2026-09-11T10:54:49Z).
Read Explorer 1's blueprint at: d:\Finance\code\stock\.agents\explorer_quant_phase24_survey1\handoff.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Strict File Ownership:
You may edit/create ONLY:
- src/ai/ensemble_scorer.py
- src/ai/factor_suppression.py
- tests/test_phase24_alpha.py

Implement:
1. Feature F115: Derived Arithmetic Topology & Étale-Motivic Spectral Homotopy Coupler (`DerivedArithmeticTopologyCoupler`, $H^*_{\text{ét-mot}}$, $E_{\text{arithmetic}}$, $Z_{\text{spectral}}$, $\theta_0=0.32$, $\kappa=3.20$) in `ensemble_scorer.py` and `factor_suppression.py`.
2. Feature F116.1: 19th-Order Hyper-Convex Rank Modulation ($g_{\text{v24}}(r) = 0.50 + 1.12 \cdot r \cdot \exp(\gamma_{\text{top}} \cdot r^{19})$, $\gamma_{\text{top}} \le 2.50$) in `factor_suppression.py`.
3. Feature F116.2: 60th-Order Hexacontagonal Hyperbolic Noise Deadband ($\alpha=60.0$, leakage $< 10^{-32}$) in `factor_suppression.py`.
4. Version branch `version >= 24` in `ensemble_scorer.py`.
5. Unit test suite `tests/test_phase24_alpha.py`.

Run build/tests using:
`.venv\Scripts\python.exe -m pytest tests/test_phase24_alpha.py tests/test_phase23_*.py -v`
Verify 100% pass and no regressions.
Write full report with test results to `d:\Finance\code\stock\.agents\worker_quant_phase24_alpha\handoff.md` and send a message when done.

