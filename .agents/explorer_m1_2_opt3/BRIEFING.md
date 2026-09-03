# BRIEFING — 2026-09-04T06:01:00+09:00

## Mission
Investigate and design exact implementation for Features F04 & F05 in `trading_system/src/ai/ensemble_scorer.py`: live multi-horizon exponential decay filtering with prior score state caching, rank IC latency calibration, and regime-adaptive trend inertia boost vs crash protection & reversal calibration.

## 🔒 My Identity
- Archetype: Explorer (Read-only investigation)
- Roles: Quantitative analysis, code investigation, algorithm design, specification for Worker
- Working directory: d:\Finance\code\stock\.agents\explorer_m1_2_opt3
- Original parent: b46202ea-01da-4d8b-b60e-9285cbf907d4
- Milestone: Milestone 1 (3rd Deep Quantitative Enhancement)

## 🔒 Key Constraints
- Read-only investigation — do NOT modify production source code in `trading_system/` or tests directly
- Write only to own folder `d:\Finance\code\stock\.agents\explorer_m1_2_opt3`
- Provide exact code replacement blocks, line numbers, and unit test assertions for the Worker
- Send all results, reports, and coordination to caller via `send_message`

## Current Parent
- Conversation ID: b46202ea-01da-4d8b-b60e-9285cbf907d4
- Updated: 2026-09-04T05:55:00+09:00

## Investigation State
- **Explored paths**:
  * `trading_system/src/ai/ensemble_scorer.py` (lines 539-575, 1002-1270, 1418-1605, 2370-2510, 3300-3440)
  * `tests/test_hpo_and_2d_ensemble.py`, `tests/test_factor_momentum_and_available_normalization.py`, `tests/test_adversarial_regime_sharpe_m2.py`, `tests/test_sector_and_ensemble_audit_fixes.py`, `tests/test_regime_ensemble.py`, `tests/test_r1_ensemble_regime_fixes.py` (36 + 16 tests passing, 100%)
- **Key findings**:
  * F04: `apply_exponential_decay_filter` and `apply_rank_ic_decay_calibration` existed as orphaned classmethods. We have designed clean integration hooks into `combine_predictions` Phase 3-A.2 and Phase 3-B.2, with per-market prior score caching (`self._prev_filtered_scores`), cold-start identity preservation, defensive duplicate column/index handling, and strict `[0.0, 1.0]` clipping.
  * F05: `compute_dynamic_weights_from_sharpe` previously applied a flat 1.40x turbo across all bull regimes regardless of volatility, and had zero reversal calibration in bear/crisis regimes. We designed full regime-adaptive differentiation: `BULL_LOW_VOL` rewards factor rank autocorrelation up to 1.60x; `BULL_HIGH_VOL` scales back momentum to 1.15x for crash protection; `BEAR_HIGH_VOL` and `CRISIS` slash momentum to 0.50x while boosting reversal strategies up to 1.68x via VIX stress.
- **Unexplored areas**: None for M1-2 scope.

## Key Decisions Made
- Caching structure: `self._prev_filtered_scores` keyed by lowercase market string (`'sp500'`, `'nasdaq'`, `'russell2000'`, `'kospi'`, `'kosdaq'`, `'us'`, `'kr'`, `'global'`).
- Hook locations: Decay filtering at Phase 3-A.2 (after cross-sectional score normalization, before orthogonalization and factor suppression); Rank IC calibration at Phase 3-B.2 (on effective US and KR regime weights).
- Full backward compatibility: Cold starts (None prior scores) return identical un-decayed scores, preserving 100% test compatibility.

## Artifact Index
- `progress.md` — Liveness and task tracker
- `DISPATCH.md` — Received dispatch records
- `BRIEFING.md` — Situational awareness
- `handoff.md` — 5-component handoff report for Worker
