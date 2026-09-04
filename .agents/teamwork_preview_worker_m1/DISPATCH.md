## 2026-09-04T00:40:15Z
You are Worker 1: M1 Signal Quality Worker.
Your working directory: d:\Finance\code\stock\.agents\teamwork_preview_worker_m1
Maintain progress.md in your working directory.

MANDATORY FIRST STEP:
Read d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md completely before starting any work.
Also read the detailed engineering blueprint from Explorer 2 at:
d:\Finance\code\stock\.agents\teamwork_preview_explorer_survey_2\handoff.md
And the scope document at:
d:\Finance\code\stock\.agents\orchestrator_quant_opt4\SCOPE.md

WRITE OWNERSHIP:
You EXCLUSIVELY own and are permitted to modify:
1. `trading_system/src/ai/ensemble_scorer.py`
2. `tests/test_phase4_signal_enhancement.py` (new test suite)
Do NOT modify any other files.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Your Tasks for Milestone 1 (R1):
1. Unlock Top-Decile Spread (The 0.833 Alpha Ceiling in `combine_predictions`, lines ~3215-3236):
   - Replace the premature `np.clip(abs_centered * mult, -0.50, 0.50)` clipping before power-law exponent.
   - Use rank-modulated dynamic scaling: `mult = np.where(abs_centered >= 0.0, 0.60 + 0.80 * ranks, 1.40 - 0.80 * ranks)`.
   - Scale `unclipped_score = abs_centered * mult` and pass through power-law exponent (`np.sign(unclipped_score) * np.clip((np.abs(unclipped_score * 2.0) ** 1.15) / 1.15, 0.0, 1.0)`), restoring steep right-tail curvature for premier top-decile stocks while preserving smooth bounds.
2. NaN-Aware & Softplus Smooth Convex Boost (`apply_top_decile_convex_boost`, lines ~1646-1681):
   - Instead of filling NaNs with 0.0 which penalizes sparse factors, impute NaNs with the asset's own row-wise valid mean (`sub_df.mean(axis=1).fillna(0.50)`).
   - Replace the hard Heaviside step (`top_k_mean >= 0.60`) with a smooth continuous sigmoid/softplus conviction gate: `gate_weight = 1.0 / (1.0 + np.exp(-np.clip(15.0 * (top_k_mean - 0.60), -20.0, 20.0)))`.
3. Tri-Linear Synergy Kernel & Full 6-Regime Coupling (`compute_bilinear_cross_pillar_synergy`, lines ~3964-4065):
   - Differentiate all 6 2D regimes (`BULL_LOW_VOL`, `BULL_HIGH_VOL`, `SIDEWAYS_LOW_VOL`, `SIDEWAYS_HIGH_VOL`, `BEAR_LOW_VOL`, `BEAR_HIGH_VOL` / `CRISIS`).
   - Add tri-linear confluence term `tri_confluence = omega_tri * (pillar_convictions['val'] * pillar_convictions['mom'] * pillar_convictions['flow'])` to reward stocks exhibiting simultaneous strength across Valuation, Momentum, and Institutional Order Flow.
4. Sideways 2D Regime Weight Rebalancing (`REGIME_2D_WEIGHTS`, lines ~316-393):
   - In `SIDEWAYS_LOW_VOL` and `SIDEWAYS_HIGH_VOL`:
     - Trim whipsaw false-breakout momentum traps: `surge`: 0.015, `vcp_ml`: 0.015, `vcp_rule`: 0.020, `range_expansion_breakout`: 0.015.
     - Reallocate into high-win-rate sideways alpha engines: `stat_arb`: 0.050, `dual_correction`: 0.050, `short_term_reversal`: 0.040, `overnight_gap_reversal`: 0.040, `vol_target`: 0.050.
     - Strictly verify that the sum of weights across all 37 strategies equals 1.0000.
5. Kaufman Trend Efficiency (KER) Dynamic Alpha Switching (`combine_predictions`):
   - Hook `apply_ker_dynamic_alpha_switching` into `combine_predictions` when `trend_efficiency_score` is present in `merged` (or via fallback).
6. Strategy-Class Asymmetric Decay in Dynamic Half-Life Filtering (`get_regime_adaptive_half_lives`, lines ~3754-3804):
   - In `SIDEWAYS` regimes, halve momentum strategy half-lives ($\tau_{\text{mom}} \times 0.50$) to wash out noise spikes quickly.
   - In `BULL` regimes, extend momentum half-lives ($\tau_{\text{mom}} \times 1.35$) to let genuine compounding trend winners run.
7. Regime-Adaptive `u_thresh` in Bessembinder Convex Scaling (`get_regime_adaptive_bessembinder_params`, lines ~4073-4107):
   - Return `(gamma_tail, beta_tail, u_thresh)` where `u_thresh` is 0.45 in `BULL_LOW_VOL`, 0.55 in `BULL_HIGH_VOL`, 0.60 in `SIDEWAYS_LOW_VOL`, 0.70 in `SIDEWAYS_HIGH_VOL`, and 0.75 in `CRISIS`.
8. Write comprehensive unit/property tests in `tests/test_phase4_signal_enhancement.py` verifying all 7 features, score bounds [0.0, 1.0], weight normalization $\sum w = 1.0000$, and rank preservation.
9. Verify all tests pass cleanly:
   Run: `.venv\Scripts\python.exe -m pytest tests/test_phase4_signal_enhancement.py tests/test_score_normalizer.py tests/test_factor_orthogonalization.py tests/test_correlation_suppression.py tests/test_adversarial_ensemble_scorer_challenger.py tests/test_r1_ensemble_regime_fixes.py tests/test_regime_ensemble.py tests/test_advanced_ensemble_features.py tests/test_adversarial_normalizer_m1.py -v`
10. Write `handoff.md` in `d:\Finance\code\stock\.agents\teamwork_preview_worker_m1\handoff.md` detailing changes, before/after logic, test commands, and passing results. Notify caller via send_message.
