# DISPATCH — Challenger M1-2

**Task**: Quantitative Spread Expansion & Noise Deadband Challenge for Milestone 1 (F41 & F42).
**Authoritative Reference**: `d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md` (see ## 2026-09-04T13:40:12Z)
**Worker Handoff**: `d:\Finance\code\stock\.agents\worker_m1\handoff.md`
**Target Files**:
- `src/ai/ensemble_scorer.py`
- `src/ai/factor_suppression.py`

**Objectives**:
1. Adversarially challenge the top-decile alpha spread claim: does Version 6 expand top-decile spread by $\ge 15\%$ compared to Phase 5 across 500-stock randomized portfolios?
2. Adversarially challenge the noise deadband claim: does asymmetric kurtosis deadband squash $\ge 90\%$ of noise for $|z| \le 0.010$ while preserving $\ge 98.5\%$ of conviction signals for $|z| \ge 0.150$?
3. Verify Markov half-life elasticity: do microstructure signals decay faster than fundamental signals under regime transitions?
4. Execute empirical tests via Python.
5. Report verdict (CONFIRM / REJECT) with quantitative test metrics in `d:\Finance\code\stock\.agents\challenger_m1_2\handoff.md`.

## 2026-09-04T14:17:17Z
You are challenger_m1_2.
Your working directory is: d:\Finance\code\stock\.agents\challenger_m1_2\
Read d:\Finance\code\stock\.agents\challenger_m1_2\DISPATCH.md and d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md (mandatory).
Read d:\Finance\code\stock\.agents\worker_m1\handoff.md.
Adversarially challenge top-decile spread expansion (>= 15% vs Phase 5), noise deadband squashing (>= 90% for |z| <= 0.010), and signal transmission (>= 98.5% for |z| >= 0.150).
Run empirical verification tests.
Deliver your challenger report and verdict (CONFIRM or REJECT) to: d:\Finance\code\stock\.agents\challenger_m1_2\handoff.md
Send completion message back to parent.
