# DISPATCH: Worker 1 — Alpha Signal Specialist Implementation (Phase 26)

## Working Directory
`d:\Finance\code\stock\.agents\worker_quant_phase26_alpha`

## Role
Alpha Signal Specialist Implementation Worker (`teamwork_preview_worker`)

## Context & Objectives
You are Worker 1 implementing the Phase 26 R1 Alpha Signal Enhancement.
Authoritative user request:
`d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md` (Header: `## 2026-09-11T13:18:53Z`)
Full architectural survey and implementation blueprint:
`d:\Finance\code\stock\.agents\explorer_quant_phase26_survey1\handoff.md`

## MANDATORY INTEGRITY WARNING
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Exclusive Write Ownership
You EXCLUSIVELY own and modify:
- `src/ai/ensemble_scorer.py`
- `src/ai/factor_suppression.py`
- `tests/test_phase26_alpha.py`

DO NOT modify any other files.

## Technical Tasks
1. Implement Feature F123: Perfectoid Shimura Variety & Mochizuki Inter-Universal Teichmüller (IUT) Reconstruction factor disentanglement coupler ($E_{\text{shimura}}$, $Z_{\text{mochizuki}}$):
   - Define `PerfectoidShimuraIUTCoupler` and aliases in `src/ai/ensemble_scorer.py`.
   - Implement `@classmethod def compute_perfectoid_shimura_iut_coupling(...)` in `EnsembleScoringEngine`.
   - Register classes and aliases onto `src/ai/factor_suppression.py`.
2. Implement Feature F124.1: 21st-order hyperconvex rank modulation function $g_{\text{v26}}(r) = 0.50 + 1.16 \cdot r \cdot \exp(\gamma_{\text{top}} \cdot r^{21})$:
   - Define `compute_phase26_hyperconvex_rank_modulation` and alias `compute_phase26_rank_warping`.
   - Update `get_regime_adaptive_gamma_top` for `int(version) >= 26` (CRISIS: 1.60, BEAR_HIGH_VOL: 0.85, BEAR_LOW_VOL/'0': 2.00, SIDEWAYS_HIGH_VOL: 1.55, SIDEWAYS_LOW_VOL/'1': 2.30, BULL_HIGH_VOL: 2.50, BULL_LOW_VOL/'2': 2.70).
   - In `combine_predictions()`, branch for `if int(version) >= 26:`.
3. Implement Feature F124.2: 68th-order Hexaoctagonal ($\alpha=68.0$) hyperbolic deadband:
   - Define `apply_hexaoctagonal_hyperbolic_deadband` ($z_{\text{denoised}} = z \cdot \tanh((|z|/\delta_{\text{eff}})^{68})$).
   - In `compute_quint_pillar_tensor_synergy()`, branch for `if version >= 26:` incorporating $1.25 \cdot h_{\text{shimura}} \cdot z_{\text{mochizuki}}$.
4. Implement `tests/test_phase26_alpha.py` with all 14 unit test cases specified in Explorer 1's handoff report.
5. Run tests using `.venv/Scripts/python.exe -m pytest tests/test_phase26_alpha.py tests/test_phase25_alpha.py -v`. Ensure 100% pass and 0 regressions.
6. Write your completion report to `d:\Finance\code\stock\.agents\worker_quant_phase26_alpha\handoff.md` and send a message to Orchestrator (`23291457-ea26-4c49-8433-2bc79a9280cf`).
