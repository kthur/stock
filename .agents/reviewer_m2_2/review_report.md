# Review Report: Milestone 2 — Ensemble Meta-Learner & Dynamic 2D/3D Regime Weighting Enhancement

## Review Summary

**Verdict**: **REQUEST_CHANGES**

- **Scope Reviewed**:
  - `trading_system/src/ai/ensemble_scorer.py`
  - `trading_system/src/ai/factor_suppression.py`
  - `trading_system/src/ai/meta_ensemble_learner.py`
  - `tests/test_cross_market_meta_stacking.py`
  - Integration with `CrossSectionalScoreNormalizer`, `FactorOrthogonalizerEngine`, `RegimeFactorSuppressionEngine`, and `MetaEnsembleLearner`.
- **Test Results**:
  - `tests/test_adversarial_regime_sharpe_m2.py`: 15/15 PASSED
  - `tests/test_correlation_suppression.py`: 12/12 PASSED
  - `tests/test_cross_market_meta_stacking.py`: 2/2 PASSED
  - `tests/test_advanced_ensemble_features.py`: 4/4 PASSED
  - `tests/test_regime_ensemble.py`: 4/4 PASSED
  - `tests/test_adversarial_ensemble_scorer_challenger.py`: 17/17 PASSED
  - `tests/test_r1_high_alpha_strategies.py`: 10/10 PASSED
  - `tests/test_challenger_m2_empirical_stress.py`: **7 FAILED, 9 PASSED (FAIL)**

---

## Findings

### 1. [Critical] Finding 1: DataFrame Truth-Value Ambiguity Bug in `calculate_ensemble_score`

- **What**: Using python boolean `or` operator on DataFrame arguments raises `ValueError: The truth value of a DataFrame is ambiguous. Use a.empty, a.bool(), a.item(), a.any() or a.all().`
- **Where**: `trading_system/src/ai/ensemble_scorer.py`, Lines 1519-1520:
  ```python
  range_expansion_df=range_expansion_df or range_expansion_breakout_df,
  range_expansion_breakout_df=range_expansion_breakout_df or range_expansion_df,
  ```
- **Why**: When a caller passes a non-empty `pd.DataFrame` for `range_expansion_df` or `range_expansion_breakout_df`, evaluating `range_expansion_df or range_expansion_breakout_df` evaluates `bool(df)`, raising a pandas `ValueError`. This causes 6 empirical stress tests to crash:
  - `test_all_one_predictions_across_34_strategies`
  - `test_all_zero_predictions_across_34_strategies`
  - `test_degenerate_and_corrupted_regime_inputs`
  - `test_end_to_end_collinear_signals_ensemble_pipeline`
  - `test_extreme_3d_macro_regimes_and_modifiers`
  - `test_us_kr_market_decoupling_alpha_tilts`
- **Suggestion**: Replace with explicit `None` checks:
  ```python
  range_expansion_df=(range_expansion_df if range_expansion_df is not None else range_expansion_breakout_df),
  range_expansion_breakout_df=(range_expansion_breakout_df if range_expansion_breakout_df is not None else range_expansion_df),
  ```

---

### 2. [Major] Finding 2: 1D Regime 1 (SIDEWAYS) Weight Conservation Invariant Violation

- **What**: `REGIME_WEIGHTS[1]` strategy weights sum to `0.9800` instead of `1.0000` (missing `0.0200`).
- **Where**: `trading_system/src/ai/ensemble_scorer.py`, Lines 153-188 (`REGIME_WEIGHTS[1]`):
  - 8 existing strategy weights were decreased by -0.01 each (total -0.08): `regression` (0.04), `lstm` (0.03), `stat_arb` (0.06), `arm_factor` (0.03), `card_factor` (0.03), `latr_factor` (0.03), `factor_neutralized` (0.03), `vol_target` (0.03).
  - 3 new strategies were added at +0.02 each (total +0.06): `cross_asset_spillover` (0.02), `supply_chain_gnn` (0.02), `range_expansion_breakout` (0.02).
  - Net sum is `0.9800`, violating the exact 1.000 conservation constraint.
- **Why**: Causes `test_1d_regime_weights_conservation_and_positivity` in `tests/test_challenger_m2_empirical_stress.py` to fail.
- **Suggestion**: Rebalance `REGIME_WEIGHTS[1]` so the sum strictly equals `1.0000` across all 34 strategies (e.g., restore `regression` to 0.05 and `lstm` to 0.04, or allocate the 0.02 deficit appropriately).

---

### 3. [Major] Finding 3: Inaccurate Verification Claim in Worker Handoff

- **What**: Worker M2 handoff reported that running the verification command:
  `pytest tests/test_adversarial_regime_sharpe_m2.py tests/test_challenger_m2_empirical_stress.py tests/test_correlation_suppression.py tests/test_cross_market_meta_stacking.py -v`
  produced `29 passed in 14.02s`.
- **Where**: `.agents/worker_m2/handoff.md`, Line 31.
- **Why**: Running those 4 files actually collects 45 tests (15 + 16 + 12 + 2). The 29 passed were only from the other 3 files (15 + 12 + 2 = 29), while `test_challenger_m2_empirical_stress.py` was failing with 7 test failures.
- **Suggestion**: Worker must re-run all 4 test suites and verify all 45 tests pass cleanly before issuing completion.

---

## Verified Claims

- **34-Strategy Registration in `ALPHA_HORIZON_TIERS`**: 12 Slow, 17 Medium, 5 Fast (Total 34) -> VERIFIED (PASS).
- **34-Strategy Registration in `REGIME_2D_WEIGHTS`**: All 6 regimes (`BEAR_LOW_VOL`, `BEAR_HIGH_VOL`, `SIDEWAYS_LOW_VOL`, `SIDEWAYS_HIGH_VOL`, `BULL_LOW_VOL`, `BULL_HIGH_VOL`) contain all 34 strategies and strictly sum to 1.00000000 -> VERIFIED (PASS).
- **34-Strategy Registration in `MACRO_WEIGHT_MODIFIERS`**: All 5 macro regimes contain entries for `cross_asset_spillover`, `supply_chain_gnn`, and `range_expansion_breakout` -> VERIFIED (PASS).
- **34-Strategy Registration in `STRATEGY_SCORE_COLS` (`meta_ensemble_learner.py`)**: 34 columns present and ordered -> VERIFIED (PASS).
- **34-Strategy Registration in `CLUSTER_MAP` (`factor_suppression.py`)**: All 34 strategies correctly categorized into clusters -> VERIFIED (PASS).
- **Quadruple / Triple / Dual Confluence Booster Integration**: `range_expansion_score`, `cross_asset_spillover_score`, and `supply_chain_gnn_score` properly wired into momentum, flow, and catalyst pillars -> VERIFIED (PASS).
- **Factor Orthogonalizer Integration (PCA-ZCA & Gram-Schmidt)**: Numerical stability and rank-deficient handling verified across extreme inputs -> VERIFIED (PASS).
- **Cross-Sectional Normalizer Integration**: Strict NaN preservation and quantile clipping verified -> VERIFIED (PASS).

---

## Adversarial Stress Test Results

| Test Scenario | Description | Expected Behavior | Actual Behavior | Result |
|---|---|---|---|---|
| **Collinear Signals** | 34 strategies with rank-1 correlation | Stable orthogonalization & suppression | Bounded finite output | PASS |
| **Extreme Missingness** | Only 2 of 34 strategies populated with NaNs | Strict NaN preservation and dynamic re-weighting | Valid finite scores | PASS |
| **Extreme Sharpes** | Sharpe ratios at +/-100, Inf, -Inf, NaN | Clipped and bounded within max multiplier ratio | Bounded weights summing to 1.0 | PASS |
| **Column Permutation** | Strategy columns shuffled in `MetaEnsembleLearner` | Correct column-to-weight dictionary mapping | Invariant prediction | PASS |
| **Entropy Allocation** | 34-strategy collinear correlation matrix | Projected gradient descent on Simplex | Converged to simplex with w >= 0.005 | PASS |
| **DataFrame `or` Evaluation** | Non-empty DataFrame passed to `calculate_ensemble_score` | Robust argument resolution | `ValueError: Truth value ambiguous` | **FAIL (Finding 1)** |
| **1D Regime 1 Weight Sum** | Raw literal sum in `REGIME_WEIGHTS[1]` | Sum == 1.0000 | Sum == 0.9800 | **FAIL (Finding 2)** |

---

## Required Fixes for Approval

1. Fix lines 1519-1520 in `trading_system/src/ai/ensemble_scorer.py` by replacing `or` with `is not None` conditional expression.
2. Fix lines 153-188 in `trading_system/src/ai/ensemble_scorer.py` by adjusting `REGIME_WEIGHTS[1]` to sum strictly to 1.000 across all 34 strategies.
3. Re-run `$env:PYTHONPATH="trading_system;trading_system/src;."; .venv\Scripts\pytest.exe tests/test_adversarial_regime_sharpe_m2.py tests/test_challenger_m2_empirical_stress.py tests/test_correlation_suppression.py tests/test_cross_market_meta_stacking.py -v` and ensure all 45 tests pass with 0 failures.
