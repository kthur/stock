# DISPATCH: Worker 1 (Alpha Signal Specialist - Phase 41)

## Assigned Files (Exclusive Write Ownership)
- `trading_system/src/ai/ensemble_scorer.py` (and `src/ai/ensemble_scorer.py` if separate)
- `trading_system/src/ai/factor_suppression.py` (and `src/ai/factor_suppression.py` if separate)
- `tests/test_phase41_alpha.py`

## Authoritative Inputs
1. `d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md` (header `## 2026-09-14T10:14:28Z`)
2. Blueprint and exact code specifications in `d:\Finance\code\stock\.agents\explorer_quant_phase41_survey1\handoff.md`

## Implementation Scope
1. **F183: Drinfeld-Lafforgue & Fargues-Fontaine Curve Analytic Cohomology Coupler**:
   - Class `DrinfeldLafforgueFarguesFontaineCoupler` with Artin stack obstruction complex $E_{\text{fargues}}$, Fargues-Fontaine curve factor invariant $Z_{\text{fontaine}}$, metric weights $\omega_{j,k} = 1.0 / (|j-k|^{1.24})$, decay rate $\kappa_{\text{fargues}} = 6.10$.
   - Register all aliases and bind to `EnsembleScoringEngine` and `factor_suppression.py`.
   - Incorporate into harmony factor under `version >= 41`: $+ 2.15 \cdot h_{\text{fargues}} \cdot z_{\text{fontaine}}$.
2. **F184.1: 36th-Order Ultra-Convex Rank Modulation**:
   - $g_{\text{v41}}(r) = 0.50 + 1.48 \cdot r \cdot \exp(\gamma_{\text{top}} \cdot r^{36})$ with regime adaptive $\gamma_{\text{top}} \le 4.40$.
   - Implement `compute_phase41_hyperconvex_rank_modulation`, `REGIME_GAMMA_TOP_V41`, and `get_regime_adaptive_gamma_top_v41`.
3. **F184.2: 136th-Order Centatriacontaoctagonal Hyperbolic Deadband**:
   - $z_{\text{denoised}} = z \cdot \tanh((|z| / \delta_{\text{eff}}(z))^{136})$ with $\alpha = 136.0$ and $\delta_{\text{noise}} = 0.035$.
   - Noise leakage $< 10^{-74}$ for $|z| \le 0.0004$, 100.000% transmission for $|z| \ge 0.150$.
   - Route in `apply_smooth_noise_deadband` under `version >= 41`.
4. **Unit Tests**:
   - Implement `tests/test_phase41_alpha.py` covering all 9 tests specified in Explorer 1's blueprint.
   - Run tests via `.venv\Scripts\python.exe -m pytest tests/test_phase41_alpha.py -v` and ensure 100% pass.
   - Verify that Phase 40 tests `tests/test_phase40_alpha.py` continue to pass 100% without regression.

## Output
Write your handoff report to `d:\Finance\code\stock\.agents\worker_quant_phase41_alpha\handoff.md`.

## 2026-09-14T10:25:50Z
You are Worker 1 (Alpha Signal Specialist) for Phase 41 Quant Enhancement.
Your working directory is d:\Finance\code\stock\.agents\worker_quant_phase41_alpha.

DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

You have EXCLUSIVE write ownership of:
- trading_system/src/ai/ensemble_scorer.py (and src/ai/ensemble_scorer.py if separate)
- trading_system/src/ai/factor_suppression.py (and src/ai/factor_suppression.py if separate)
- tests/test_phase41_alpha.py
Do NOT touch any risk, OMS, or benchmark files.

