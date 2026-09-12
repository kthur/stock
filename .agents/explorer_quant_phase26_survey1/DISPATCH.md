# DISPATCH: Survey 1 — Alpha Signal Exploration (Phase 26)

## Working Directory
`d:\Finance\code\stock\.agents\explorer_quant_phase26_survey1`

## Role
Alpha Signal Specialist Explorer

## Context & Objectives
You are Explorer 1 surveying the codebases for Phase 26 R1 Alpha Signal Enhancement.
Authoritative user request is in:
`d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md` (Header: `## 2026-09-11T13:18:53Z`)
Also read:
`d:\Finance\code\stock\PROJECT.md`
`d:\Finance\code\stock\.agents\orchestrator_quant_phase26_1\plan.md`

## Your Mission
1. Investigate existing hook points in:
   - `src/ai/ensemble_scorer.py`
   - `src/ai/factor_suppression.py`
   - Existing Phase 24 and Phase 25 implementations (F115/F116, F119/F120)
2. Detail the exact design and implementation blueprint for:
   - F123: Perfectoid Shimura Variety & Mochizuki Inter-Universal Teichmüller (IUT) Reconstruction factor disentanglement coupler ($E_{\text{shimura}}$, $Z_{\text{mochizuki}}$).
   - F124.1: 21st-order hyperconvex rank modulation $g_{\text{v26}}(r) = 0.50 + 1.16 \cdot r \cdot \exp(\gamma_{\text{top}} \cdot r^{21})$ with regime-adaptive $\gamma_{\text{top}} \le 2.70$.
   - F124.2: 68th-order Hexaoctagonal ($\alpha=68.0$) hyperbolic deadband with noise leakage $< 10^{-36}$.
   - Version branching (`version >= 26`) in `combine_predictions`, `compute_quint_pillar_tensor_synergy`, and dynamic registration in `factor_suppression.py`.
3. Provide concrete line numbers, exact equations, class/method signatures, and unit test specifications for `tests/test_phase26_alpha.py`.
4. Output your complete analysis to:
   `d:\Finance\code\stock\.agents\explorer_quant_phase26_survey1\handoff.md`
   And send a completion message to the Orchestrator (`23291457-ea26-4c49-8433-2bc79a9280cf`).

## 2026-09-11T13:22:24Z
<USER_REQUEST>
You are Explorer 1 (Alpha Signal Specialist Explorer).
Your working directory is: d:\Finance\code\stock\.agents\explorer_quant_phase26_survey1
Read your dispatch instructions in: d:\Finance\code\stock\.agents\explorer_quant_phase26_survey1\DISPATCH.md
Read the authoritative user request in: d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md (Header: ## 2026-09-11T13:18:53Z)
Also review:
- `d:\Finance\code\stock\PROJECT.md`
- `d:\Finance\code\stock\.agents\explorer_quant_phase25_survey1\handoff.md`
- `d:\Finance\code\stock\src\ai\ensemble_scorer.py`
- `d:\Finance\code\stock\src\ai\factor_suppression.py`

Conduct a comprehensive survey of R1 Alpha Signal requirements:
1. Detail F123: Perfectoid Shimura Variety & Mochizuki Inter-Universal Teichmüller (IUT) Reconstruction factor disentanglement coupler (Hodge-Tate filtration obstruction complex $E_{\text{shimura}}$, Mochizuki theta-link invariant $Z_{\text{mochizuki}}$) to be implemented in `ensemble_scorer.py` and registered in `factor_suppression.py`.
2. Detail F124.1: 21st-order ultra-convex rank modulation function $g_{\text{v26}}(r) = 0.50 + 1.16 \cdot r \cdot \exp(\gamma_{\text{top}} \cdot r^{21})$ with regime-adaptive $\gamma_{\text{top}} \le 2.70$.
3. Detail F124.2: 68th-order Hexaoctagonal ($\alpha=68.0$) hyperbolic deadband with noise leakage $< 10^{-36}$.
4. Examine hook points in `src/ai/ensemble_scorer.py` (version >= 26 branching in `combine_predictions`, `compute_quint_pillar_tensor_synergy`, `get_regime_adaptive_gamma_top`) and aliases/registration in `src/ai/factor_suppression.py`.
5. Provide precise line references, mathematical formulas, class and function signatures, and 14 unit test specifications for `tests/test_phase26_alpha.py`.

Write your complete survey report to:
`d:\Finance\code\stock\.agents\explorer_quant_phase26_survey1\handoff.md`
When finished, send a message to the Orchestrator (Recipient: 23291457-ea26-4c49-8433-2bc79a9280cf) reporting your findings and handoff file path.
</USER_REQUEST>

