# BRIEFING — 2026-09-04T06:00:00+09:00

## Mission
Deep dive and prepare exact code changes and unit tests for Features F06 (37-strategy bilinear pillar synergy & regime-adaptive Bessembinder tail power-law), F07 (entropy allocation activation for N >= 10 in factor suppression & ensemble), and F08 (zero-variance protection in PCA-ZCA whitening).

## 🔒 My Identity
- Archetype: explorer
- Roles: explorer, investigator, synthesizer
- Working directory: d:\Finance\code\stock\.agents\explorer_m1_3_opt3
- Original parent: b46202ea-01da-4d8b-b60e-9285cbf907d4
- Milestone: Milestone 1

## 🔒 Key Constraints
- Read-only investigation — do NOT implement
- Scope restricted to Features F06, F07, F08

## Current Parent
- Conversation ID: b46202ea-01da-4d8b-b60e-9285cbf907d4
- Updated: not yet

## Investigation State
- **Explored paths**:
  * `trading_system/src/ai/ensemble_scorer.py`: `compute_bilinear_cross_pillar_synergy` (lines 3512-3602), `apply_bessembinder_convex_power_law` (lines 3607-3660), caller integration in `combine_predictions` (lines 2667, 2725).
  * `trading_system/src/ai/factor_suppression.py`: `solve_single_stage_entropy_allocation` (lines 15-60), `suppress_weights` (lines 284-374), caller integration in `ensemble_scorer.py` (line 2420).
  * `trading_system/src/ai/factor_orthogonalizer.py`: `_pca_zca_symmetric` (lines 232-310), `orthogonalize` (lines 54-160).
  * Existing unit tests in `tests/test_m1_quant_enhancements.py`, `tests/test_adversarial_m1_2_empirical_stress.py`, `tests/test_factor_orthogonalization.py`, `tests/test_correlation_suppression.py`.
- **Key findings**:
  * F06: 8 strategies currently omitted from 4-pillar synergy cluster map. Disjoint partition completed (Val: 6, Mom: 9, Flow: 9, Cat: 13 = 37 total). Bessembinder parameters mapped to all 7 market regimes.
  * F07: Single-stage entropy solver was dormant due to hardcoded default False in `combine_predictions` and `not missing_strats` check. Enhanced to support partial missingness and automatic activation when N >= 10.
  * F08: Singular/constant columns from median imputation caused invalid correlation matrix diagonals (C_jj = 0) and cross-feature noise bleed. Active subspace isolation with constant preservation eliminates singularities.
- **Unexplored areas**: None within scope.

## Key Decisions Made
- All 37 strategies mapped to exactly 1 pillar with 0 overlaps and 0 omissions.
- Bessembinder defaults kept at (1.45, 0.40) when regime is None for strict backward compatibility with existing unit tests.
- Single-stage entropy allocation seamlessly handles partial missingness by optimizing present subset and scaling missing subset.
- Zero-variance columns in `_pca_zca_symmetric` isolated before ZCA decomposition, preventing noise contamination and zero-division errors.

## Artifact Index
- progress.md — Liveness and progress tracking
- handoff.md — 5-component handoff report for Worker
