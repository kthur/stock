## 2026-09-03T20:55:14Z

<USER_REQUEST>
You are Explorer M1-1 for Milestone 1 of the 3rd Deep Quantitative Enhancement.
Your working directory: d:\Finance\code\stock\.agents\explorer_m1_1_opt3
Read-only exploration agent.

MANDATORY INPUTS:
- Read ORIGINAL_REQUEST.md at: d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md
- Read PROJECT.md at: d:\Finance\code\stock\.agents\orchestrator_quant_opt3\PROJECT.md
- Read Survey Explorer 1 report at: d:\Finance\code\stock\.agents\explorer_survey_1_opt3\handoff.md

SCOPE & TASKS (Features F01, F02, F03 in `trading_system/src/ai/ensemble_scorer.py`):
1. F01: Formulate the exact 37-strategy dictionary for `CRISIS` in `REGIME_2D_WEIGHTS` ensuring the sum strictly equals 1.0000 and every weight >= 0.005. Check `get_base_weights()` line 882-890 so `CRISIS` never falls back to `SIDEWAYS_LOW_VOL`.
2. F02: Design support for posterior regime probability vector $\boldsymbol{\pi}_t$ (or 1-hot regime fallback) computing Markov-blended base weights $\mathbf{w}_{base}(t) = \sum \pi_{t, m} \mathbf{w}^{(m)}$.
3. F03: Design continuous TV-distance & VIX entropy adaptive weight smoothing $\alpha_t$ in `compute_dynamic_weights_from_sharpe` replacing piecewise VIX step thresholds, preventing turnover spikes during regime transitions while allowing responsive adaptation during crisis spikes.
4. Prepare exact code replacement blocks, line numbers, and unit test assertions for the Worker.

OUTPUT:
- Update progress.md at: d:\Finance\code\stock\.agents\explorer_m1_1_opt3\progress.md
- Write comprehensive handoff report to: d:\Finance\code\stock\.agents\explorer_m1_1_opt3\handoff.md
</USER_REQUEST>
