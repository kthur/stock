# Task Assignment: Phase 44 Survey Explorer 1 — Alpha Signal Specialist Scope

## Identity & Working Directory
- Role: Survey Explorer 1 (Alpha Signal & Suppression Investigation)
- Working Directory: d:\Finance\code\stock\.agents\explorer_phase44_survey_1

## Context & Inputs
- Authoritative Request: d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md (Header: ## 2026-09-15T12:29:31Z)
- Orchestrator Dispatch: d:\Finance\code\stock\.agents\orchestrator_quant_phase44_1\DISPATCH.md
- Scope Document: d:\Finance\code\stock\PROJECT.md

## Target Files to Investigate
- `src/ai/ensemble_scorer.py`
- `src/ai/factor_suppression.py`
- Related tests: `tests/test_phase43_*.py` or relevant alpha tests

## Investigation Objectives
1. Inspect how Phase 43 (F191, F192.1, F192.2) is currently implemented:
   - Quantum Langlands Coupler in `ensemble_scorer.py` & `factor_suppression.py`
   - 38th-order rank modulation function $g_{\text{v43}}(r)$
   - 152nd-order hyperbolic deadband
   - Version branch `version >= 43`
2. Specify exact implementation design for Phase 44 (F195, F196.1, F196.2):
   - Quantum Geometric Langlands Categorical Oper Duality & Virasoro-Whittaker Sheaf Homology coupler ($E_{\text{vir\_whit}}$, $Z_{\text{vir\_whit}}$, $\kappa_{\text{vir\_whit}} = 8.00$)
   - 39th-order ultra-convex rank modulation $g_{\text{v44}}(r) = 0.50 + 1.54 \cdot r \cdot \exp(\gamma_{\text{top}} \cdot r^{39})$ ($\gamma_{\text{top}} \le 4.90$)
   - 160th-order ($\alpha=160.0$) Centahexacontagonal hyperbolic deadband (noise leakage $< 10^{-90}$, threshold $|z| \le 0.0003$)
   - Version branch `version >= 44` in `ensemble_scorer.py` and ensure Rank-IC $\ge 0.980$
3. Document exact function names, signatures, math formulas, line numbers, and backward compatibility hooks.

## Output
Write your comprehensive investigation report to:
`d:\Finance\code\stock\.agents\explorer_phase44_survey_1\handoff.md`
and send a completion message back with summary.

## 2026-09-15T12:43:16Z
You are Survey Explorer 1 for Phase 44 Quant Enhancement.
Your working directory is: d:\Finance\code\stock\.agents\explorer_phase44_survey_1
Read your instructions at: d:\Finance\code\stock\.agents\explorer_phase44_survey_1\DISPATCH.md
Also read the authoritative user request at: d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md (Header: ## 2026-09-15T12:29:31Z)

Scope:
Investigate `src/ai/ensemble_scorer.py` and `src/ai/factor_suppression.py` for how Phase 43 (F191, F192.1, F192.2) is implemented, and specify the exact Phase 44 implementation design for F195, F196.1, F196.2:
- Quantum Geometric Langlands Categorical Oper Duality & Virasoro-Whittaker Sheaf Homology coupler (E_vir_whit, Z_vir_whit, kappa_vir_whit = 8.00)
- 39th-order ultra-convex rank modulation g_v44(r) = 0.50 + 1.54 * r * exp(gamma_top * r^39) (gamma_top <= 4.90)
- 160th-order centahexacontagonal hyperbolic deadband (noise leakage < 10^-90, |z| <= 0.0003)
- version >= 44 branch in ensemble_scorer.py ensuring Rank-IC >= 0.980

Write your findings to `d:\Finance\code\stock\.agents\explorer_phase44_survey_1\handoff.md` and use send_message to report back.

## 2026-09-15T13:08:35Z
**Context**: Survey Explorer 1 for Phase 44 Quant Enhancement (Alpha Signal Scope)
**Content**: Checking in on your status. Please report your current progress on investigating `ensemble_scorer.py` and `factor_suppression.py`.
**Action**: If your analysis is complete, write your handoff.md and send a completion message. If still working, send a quick status update.
