# BRIEFING — 2026-09-03T15:42:30Z

## Mission
Formulate exact fix strategy and code-level design for Milestone 1 Feature 1 (Pipeline Sequence: raw correlation & suppression before ZCA) & Feature 6 (Sample-size calibrated suppression cutoffs).

## 🔒 My Identity
- Archetype: explorer
- Roles: Pipeline Sequence & Factor Suppression Specialist
- Working directory: d:\Finance\code\stock\.agents\explorer_m1_1_opt2
- Original parent: 31b60ad6-8c74-4119-a790-2b2e694a292d
- Milestone: Milestone 1

## 🔒 Key Constraints
- Read-only investigation — do NOT implement code in src/
- Follow Handoff Protocol (Observation, Logic Chain, Caveats, Conclusion, Verification Method)
- Write only in .agents/explorer_m1_1_opt2/

## Current Parent
- Conversation ID: 31b60ad6-8c74-4119-a790-2b2e694a292d
- Updated: 2026-09-03T15:49:30Z

## Investigation State
- **Explored paths**:
  - `trading_system/src/ai/factor_suppression.py`: analyzed `RegimeFactorSuppressionEngine`, `_get_regime_params`, `compute_penalties`, `suppress_weights`.
  - `trading_system/src/ai/ensemble_scorer.py`: analyzed `combine_predictions` Phase 3-A, 3-B, 3-B.1, 3-C sequence inversion defect.
  - `trading_system/src/ai/correlation_monitor.py`: analyzed Spearman correlation update and `attrs` handling.
  - `tests/test_correlation_suppression.py`: verified existing 12 test methods pass.
  - `tests/test_factor_orthogonalization.py`: verified 6 test methods pass.
  - `tests/test_adversarial_ensemble_scorer_challenger.py`: verified 17 test methods pass.
- **Key findings**:
  - In `combine_predictions()`, ZCA factor orthogonalization ran *before* correlation monitoring and factor suppression, flattening correlations below 0.25 and causing `excess = max(0, |rho| - theta)` to evaluate to 0, completely muting suppression penalties.
  - Moving correlation monitoring and factor suppression before orthogonalization produces active penalties (e.g. surge penalty 0.758 raw vs 0.861 post-ortho).
  - Statistically calibrated cutoff $\theta(R, N) = \text{clip}(\theta_0(R) + 1.645/\sqrt{N-3}, 0.35, 0.85)$ smoothly adapts to universe sample size $N$ with backward compatibility when $N$ is None or $N \le 3$.
- **Unexplored areas**: Milestone 2 and Milestone 3 features (delegated to subsequent specialists).

## Key Decisions Made
- Reorder Phase 3 in `combine_predictions()`: Phase 3-A (Normalization) -> Phase 3-B (Pre-Orthogonalization Correlation Monitoring & Suppression) -> Phase 3-C (Factor Orthogonalization with suppressed weights).
- Implement `calibrate_cutoff` static method on `RegimeFactorSuppressionEngine` and integrate with `_get_regime_params`, `compute_penalties`, `suppress_weights`.
- Pass sample size $N = \text{len}(merged)$ from `combine_predictions()` into `suppress_weights()` and `compute_penalties()`.
- Add defensive attribute retention for `merged.attrs['correlation_report']` across DataFrame copies.

## Artifact Index
- d:\Finance\code\stock\.agents\explorer_m1_1_opt2\plan_m1_1.md — Technical design & diffs
- d:\Finance\code\stock\.agents\explorer_m1_1_opt2\handoff.md — 5-component handoff report
- d:\Finance\code\stock\.agents\explorer_m1_1_opt2\progress.md — Liveness heartbeat

