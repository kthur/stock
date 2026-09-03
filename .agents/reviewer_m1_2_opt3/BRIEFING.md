# BRIEFING — 2026-09-04T06:45:15+09:00

## Mission
Independent review and adversarial challenge for Milestone 1 of 3rd Deep Quantitative Enhancement (Features F04, F06, F07, F08).

## 🔒 My Identity
- Archetype: reviewer_critic
- Roles: reviewer, critic
- Working directory: d:\Finance\code\stock\.agents\reviewer_m1_2_opt3
- Original parent: b46202ea-01da-4d8b-b60e-9285cbf907d4
- Milestone: Milestone 1 (M1)
- Instance: 2 of 2 (Reviewer M1-2)

## 🔒 Key Constraints
- Review-only — do NOT modify implementation code
- Evidence-based review and adversarial challenge
- Active checks for integrity violations (hardcoded tests, facade implementations, shortcuts, bypasses)
- Unambiguous verdict: APPROVE or REQUEST_CHANGES

## Current Parent
- Conversation ID: b46202ea-01da-4d8b-b60e-9285cbf907d4
- Updated: 2026-09-04T06:40:18+09:00

## Review Scope
- **Files to review**:
  - `src/ai/ensemble_scorer.py` (F04 Alpha Convolutional Decay, F06 4-Pillar Cluster Map & Bessembinder tail power transform)
  - `src/ai/factor_suppression.py` (F07 Single-stage entropy program for correlation suppression)
  - `src/ai/factor_orthogonalizer.py` (F08 Active-subspace isolation in PCA-ZCA whitening)
  - `tests/test_m1_quant_enhancements.py`
  - `tests/test_factor_orthogonalization.py`
  - `tests/test_correlation_suppression.py`
  - `tests/test_regime_ensemble.py`
- **Interface contracts**: `PROJECT.md`, `ORIGINAL_REQUEST.md`
- **Review criteria**: Correctness, Logical Completeness, Code Quality, Risk & Adversarial Attack Surface, Integrity

## Key Decisions Made
- Confirmed F06, F07, F08 implementations are mathematically sound, genuine, and resilient against edge cases.
- Discovered Critical Defect in F04: index clobbering in `apply_exponential_decay_filter` (`curr_indexed.reset_index()`) causes `ValueError: cannot reindex on an axis with duplicate labels` during multi-market warm starts in `_apply_decay_filtering_with_cache`.
- Issued verdict: REQUEST_CHANGES due to functional failure of F04 in multi-market production operations.

## Artifact Index
- DISPATCH.md — incoming instructions log
- BRIEFING.md — persistent state and identity
- progress.md — liveness heartbeat
- stress_test_m1.py — adversarial challenge reproduction script
- handoff.md — final review and adversarial challenge report

## Review Checklist
- **Items reviewed**: F04, F06, F07, F08 across source code and test files
- **Verdict**: REQUEST_CHANGES
- **Unverified claims**: None (all tested independently)

## Attack Surface
- **Hypotheses tested**:
  - H1: F04 multi-market warm-start caching and index integrity -> FAILED (reproduced ValueError on duplicate labels)
  - H2: F04 Rank IC with NaNs, Infs, extreme latency -> PASSED
  - H3: F06 37-strategy 4-pillar clustering disjoint partition and synergy under NaNs -> PASSED
  - H4: F06 Bessembinder S-curve under constant inputs and 7 regimes -> PASSED
  - H5: F07 entropy allocation under all missing strategies and near-singular correlation -> PASSED
  - H6: F08 PCA-ZCA orthogonalizer under all-constant columns and preserve_top_k > active columns -> PASSED
- **Vulnerabilities found**:
  - F04 Multi-Market Reindex Crash on Warm Start: `apply_exponential_decay_filter` resets DataFrame index to `RangeIndex`, causing duplicate index labels across concatenated market chunks in `_apply_decay_filtering_with_cache`, which throws `ValueError` in `.reindex(df_out.index)` and silently disables decay filtering in `combine_predictions`.
- **Untested angles**: Cross-asset macro regime transition speed in production GHA runner environment.
