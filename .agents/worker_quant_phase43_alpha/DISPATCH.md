# DISPATCH: Worker 1 (Alpha Signal Specialist)

## Working Directory
d:\Finance\code\stock\.agents\worker_quant_phase43_alpha

## Authoritative User Request
d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md (Header: ## 2026-09-15T06:20:40Z)

## Technical Blueprint & Survey Report
Read and strictly follow:
`d:\Finance\code\stock\.agents\explorer_quant_phase43_survey1\handoff.md`

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Exclusive File Ownership
- `trading_system/src/ai/factor_suppression.py`
- `trading_system/src/ai/ensemble_scorer.py`
- `tests/test_phase43_alpha.py`

## Implementation Directives (Milestone R1)
1. In `trading_system/src/ai/factor_suppression.py`:
   - Implement `apply_centapentacontaduogonal_hyperbolic_deadband` (F192.2, 152th-order, $\alpha=152.0$, noise leakage $< 10^{-84}$) and aliases.
   - Implement `compute_phase43_hyperconvex_rank_modulation` (F192.1, 38th-order, $g_{\text{v43}}(r) = 0.50 + 1.52 \cdot r \cdot \exp(\gamma_{\text{top}} \cdot r^{38})$, adaptive $\gamma_{\text{top}} \le 4.70$), `REGIME_GAMMA_TOP_V43`, and `get_regime_adaptive_gamma_top_v43`.
   - Update `apply_smooth_deadband_attenuation` to branch `if version >= 43: eff_alpha = 152.0 ...`.
   - Update `__all__` and `__getattr__` with all new functions, class aliases, and coupler bindings.

2. In `trading_system/src/ai/ensemble_scorer.py`:
   - Implement `QuantumLanglandsAffineWAlgebraCoupler` (F191) with $E_{\text{w\_algebra}}$, $Z_{\text{quant\_langlands}}$, $\kappa_{\text{w\_alg}}=7.50$, $\text{FERI}_{\text{v43}}$, and all 10 aliases.
   - Bind deadband, rank modulation, and coupler aliases as static methods in `EnsembleScoringEngine`.
   - Update `apply_smooth_noise_deadband` to branch `if int(version) >= 43: eff_alpha = 152.0 ...`.
   - Update `combine_predictions` under `if version >= 43:` to compute `w_algebra_res`, extracting `h_w_algebra` and `z_quant_langlands`, and adding $+ (2.35 \cdot h_{\text{w\_algebra}} \cdot z_{\text{quant\_langlands}} \text{ if version >= 43 else 0.0})$ to `harmony_factor`.
   - Update `get_regime_adaptive_gamma_top` with version 43 scaling (Bull Low Vol: 4.70, Sideways: 4.20, Bear: 3.90, Crisis: 1.35).

3. In `tests/test_phase43_alpha.py`:
   - Implement the complete 9-test unit test suite as specified in the Survey 1 handoff report.
   - Run tests: `.venv/Scripts/python.exe -m pytest tests/test_phase43_alpha.py -v`
   - Run regression test: `.venv/Scripts/python.exe -m pytest tests/test_phase42_alpha.py -q`
   - Verify 100% pass rate.

4. Write completion report to:
   `d:\Finance\code\stock\.agents\worker_quant_phase43_alpha\handoff.md`
   and send a completion message to the orchestrator.

## 2026-09-15T06:29:13Z

You are Worker 1 (Alpha Signal Specialist Worker) for Phase 43 Quant Enhancement.
Your working directory is: d:\Finance\code\stock\.agents\worker_quant_phase43_alpha
Read your dispatch instructions at:
d:\Finance\code\stock\.agents\worker_quant_phase43_alpha\DISPATCH.md
Read the authoritative user request at:
d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md (Header: ## 2026-09-15T06:20:40Z)
Read the technical blueprint at:
d:\Finance\code\stock\.agents\explorer_quant_phase43_survey1\handoff.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Exclusive file ownership:
- trading_system/src/ai/factor_suppression.py
- trading_system/src/ai/ensemble_scorer.py
- tests/test_phase43_alpha.py

Implement F191, F192.1, F192.2, version >= 43 branching, and tests/test_phase43_alpha.py.
Execute tests: .venv/Scripts/python.exe -m pytest tests/test_phase43_alpha.py -v
Execute regression: .venv/Scripts/python.exe -m pytest tests/test_phase42_alpha.py -q
Write handoff report to:
d:\Finance\code\stock\.agents\worker_quant_phase43_alpha\handoff.md
Send a completion message back to orchestrator.
