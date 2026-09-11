## 2026-09-11T12:19:24Z
You are Worker 1 (Alpha Signal Specialist) for Phase 25 Quant Enhancement.
Your working directory is: d:\Finance\code\stock\.agents\worker_quant_phase25_alpha

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Authoritative User Request:
d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md (under header ## 2026-09-11T12:11:40Z)

Reference Architectural Survey & Blueprint:
d:\Finance\code\stock\.agents\explorer_quant_phase25_survey1\handoff.md

Exclusive Files Owned by You:
- `trading_system/src/ai/ensemble_scorer.py`
- `trading_system/src/ai/factor_suppression.py`
- `tests/test_phase25_alpha.py`

Your Tasks:
1. In `src/ai/factor_suppression.py` and `src/ai/ensemble_scorer.py`:
   - Implement Feature F119: Non-Abelian Hodge Theory & Deligne-Simpson Spectral Moduli Coupler (`NonAbelianHodgeCoupler`, solving Hitchin equations harmonic bundle obstruction $E_{\text{hodge}}$, Deligne-Simpson spectral moduli invariant $Z_{\text{simpson}}$, with complete aliases `DeligneSimpsonSpectralModuliCoupler`, `HodgeCoupler`, `DeligneSimpsonCoupler`, `HitchinEquationCoupler`, `HarmonicBundleCoupler`, `NonAbelianHodgeSpectralCoupler`).
   - Implement Feature F120.1: 20th-order hyperconvex rank modulation $g_{\text{v25}}(r) = 0.50 + 1.14 \cdot r \cdot \exp(\gamma_{\text{top}} \cdot r^{20})$ (`compute_phase25_hyperconvex_rank_modulation`, alias `compute_phase25_rank_warping`), with regime-adaptive $\gamma_{\text{top}}$ up to 2.60 (`get_regime_adaptive_gamma_top_v25`, `REGIME_GAMMA_TOP_V25`).
   - Implement Feature F120.2: 64th-order Hexatetrahedral ($\alpha=64.0$) hyperbolic deadband (`apply_hexatetrahedral_hyperbolic_deadband`) with noise leakage $< 10^{-34}$.
   - Add version >= 25 branching into `combine_predictions`, `compute_quint_pillar_tensor_synergy`, `get_regime_adaptive_gamma_top`, and `apply_smooth_noise_deadband`.
   - Wire all aliases, staticmethods, and dynamic registration onto `trading_system.src.ai.factor_suppression`.
2. Implement unit test suite `tests/test_phase25_alpha.py` (minimum 14 comprehensive tests covering all features, aliases, math properties, and regime adaptations).
3. Execute tests using `.venv/Scripts/python.exe -m pytest tests/test_phase25_alpha.py tests/test_phase24_alpha.py -v`. Ensure 100% pass and 0 regressions.
4. Write detailed handoff report to `d:\Finance\code\stock\.agents\worker_quant_phase25_alpha\handoff.md`.
5. Send completion message back to orchestrator.
