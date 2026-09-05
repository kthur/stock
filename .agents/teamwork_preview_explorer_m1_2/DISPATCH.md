## 2026-09-04T23:25:00Z
You are M1 Explorer 2 (Jump-Diffusion & Markov Penalty) for Phase 7 Zenith Quantitative Enhancements (v14).
Your working directory: d:\Finance\code\stock\.agents\teamwork_preview_explorer_m1_2
Project root: d:\Finance\code\stock
Authoritative user request: d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md (see ## 2026-09-04T23:18:21Z). You MUST read this file first.
Also read:
- d:\Finance\code\stock\.agents\orchestrator_quant_opt7\PROJECT.md
- d:\Finance\code\stock\.agents\teamwork_preview_explorer_survey_1\survey_report.md
- d:\Finance\code\stock\src\ai\ensemble_scorer.py
- d:\Finance\code\stock\tests\test_phase6_signal_enhancement.py

Mission:
Detailed code investigation and implementation strategy for Feature F47/F48 in M1:
1. Formulate exact code modification in `trading_system/src/ai/ensemble_scorer.py`:
   - `get_base_weights`: add `version=7` support. For `version >= 7`, when total variation distance d_TV between current probabilistic regime and prior exceeds 0.25, blend with Merton jump weights: w_Zenith^* = (1 - 0.60 J_regime) w_diffusion + 0.60 J_regime W_2D(R_jump).
   - `get_regime_adaptive_half_lives`: add `version=7` support. For `version >= 7`, modulate Markov departure penalty by directional volatility: kappa_Markov(S_vol) = 0.25(1 + 0.80 max(0, S_vol)) in [0.25, 0.45], accelerating decay into volatile regimes while preserving momentum in calm regimes.
2. Ensure for `version <= 6`, exact Phase 6 behavior is preserved.
3. Outline test verification cases for these specific invariants.
Deliver your findings in d:\Finance\code\stock\.agents\teamwork_preview_explorer_m1_2\exploration_report.md and complete handoff in d:\Finance\code\stock\.agents\teamwork_preview_explorer_m1_2\handoff.md.
