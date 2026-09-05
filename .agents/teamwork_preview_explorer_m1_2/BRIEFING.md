# BRIEFING — 2026-09-04T23:28:30Z

## Mission
Detailed code investigation and implementation strategy for Feature F47 (Jump-Diffusion Merton blend) and F48 (Directional Volatility Markov Departure Penalty) in M1 for Phase 7 Zenith Quantitative Enhancements.

## 🔒 My Identity
- Archetype: explorer
- Roles: investigation, analysis, synthesis
- Working directory: d:\Finance\code\stock\.agents\teamwork_preview_explorer_m1_2
- Original parent: e1532581-bf40-4631-af87-80cf978d298b
- Milestone: M1

## 🔒 Key Constraints
- Read-only investigation — do NOT implement directly in production files
- Strictly preserve Phase 6 behavior when version <= 6
- For version >= 7, support jump-diffusion regime blend (F47) and directional volatility Markov penalty (F48)
- Produce exploration_report.md and handoff.md

## Current Parent
- Conversation ID: e1532581-bf40-4631-af87-80cf978d298b
- Updated: 2026-09-04T23:28:30Z

## Investigation State
- **Explored paths**:
  - `d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md` (## 2026-09-04T23:18:21Z)
  - `d:\Finance\code\stock\.agents\orchestrator_quant_opt7\PROJECT.md`
  - `d:\Finance\code\stock\.agents\teamwork_preview_explorer_survey_1\survey_report.md`
  - `d:\Finance\code\stock\trading_system\src\ai\ensemble_scorer.py` (lines 1160–1288, 1360–1635, 3935–4114)
  - `d:\Finance\code\stock\tests\test_phase6_signal_enhancement.py` (verified 6/6 tests passing)
- **Key findings**:
  - F47 Jump-Diffusion Mixture: in `get_base_weights`, when `int(version) >= 7` and $d_{TV} > 0.25$, compute $J_{\text{regime}} = \text{clip}((d_{TV} - 0.25)/0.35, 0.0, 1.0)$ and blend $w_{\text{Zenith}}^* = (1 - 0.60 J_{\text{regime}}) w_{\text{diffusion}} + 0.60 J_{\text{regime}} W_{2D}(R_{\text{jump}})$.
  - F48 Directional Volatility Markov Departure: in `get_regime_adaptive_half_lives`, when `int(version) >= 7`, compute $S_{\text{vol}} = \Pi_{\text{high}} - 0.43$, $\kappa_{\text{Markov}} = \text{clip}(0.25(1 + 0.80 \max(0, S_{\text{vol}})), 0.25, 0.45)$, and $\phi_{KL} = \exp(-\kappa_{\text{Markov}} D_{KL})$.
  - In calm regimes ($S_{\text{vol}} \le 0$), $\kappa_{\text{Markov}} = 0.25$ exactly matches Phase 6.
  - For `version <= 6`, both functions strictly execute Phase 6 logic without divergence.
- **Unexplored areas**: Milestone M2 (4-model copula allocation and L3 OMS execution).

## Key Decisions Made
- Proposed non-breaking signature extensions for `get_base_weights` and `get_regime_adaptive_half_lives` with default `version=6`.
- Verified mathematical invariants and designed 5 unit test cases for `tests/test_phase7_signal_enhancement.py`.

## Artifact Index
- `DISPATCH.md` — record of task assignment
- `BRIEFING.md` — persistent situational awareness
- `progress.md` — liveness heartbeat
- `exploration_report.md` — detailed technical exploration and strategy report
- `handoff.md` — 5-component handoff report
