# Milestone 1 Challenger M1-2 Empirical Stress Testing Handoff Report

## 1. Observation

### Verification Environment & Test Executions
- **Working Directory**: `d:\Finance\code\stock`
- **Python Environment**: `.venv\Scripts\python.exe` (Python 3.11.9, pytest-9.1.1)
- **Adversarial Test Suite**: `tests/test_adversarial_m1_2_opt3_stress.py` (13 tests authored and executed)

### Test Command & Results
```powershell
.venv\Scripts\pytest.exe tests/test_adversarial_m1_2_opt3_stress.py -v
```

Output:
```
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-9.1.1, pluggy-1.6.0 -- D:\Finance\code\stock\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: D:\Finance\code\stock
configfile: pyproject.toml
plugins: anyio-4.14.0, dash-2.18.2, cov-7.1.0, github-actions-annotate-failures-0.4.2
collecting ... collected 13 items

tests/test_adversarial_m1_2_opt3_stress.py::TestChaoticUniverseAndDecayFiltering::test_dynamic_universe_churn_and_bounded_memory PASSED [  7%]
tests/test_adversarial_m1_2_opt3_stress.py::TestChaoticUniverseAndDecayFiltering::test_duplicate_symbol_rows_graceful_handling PASSED [ 15%]
tests/test_adversarial_m1_2_opt3_stress.py::TestChaoticUniverseAndDecayFiltering::test_apply_exponential_decay_filter_duplicate_columns_skipping_vulnerability FAILED [ 23%]
tests/test_adversarial_m1_2_opt3_stress.py::TestChaoticUniverseAndDecayFiltering::test_combine_predictions_duplicate_columns_crash_vulnerability FAILED [ 30%]
tests/test_adversarial_m1_2_opt3_stress.py::TestChaoticUniverseAndDecayFiltering::test_extreme_boundary_all_zero_and_all_one_scores PASSED [ 38%]
tests/test_adversarial_m1_2_opt3_stress.py::TestChaoticUniverseAndDecayFiltering::test_pathological_nans_and_infinities_resilience PASSED [ 46%]
tests/test_adversarial_m1_2_opt3_stress.py::TestPathologicalCollinearityOrthogonalizer::test_five_constant_columns_isolation PASSED [ 53%]
tests/test_adversarial_m1_2_opt3_stress.py::TestPathologicalCollinearityOrthogonalizer::test_multiple_pairwise_identical_duplicate_columns PASSED [ 61%]
tests/test_adversarial_m1_2_opt3_stress.py::TestPathologicalCollinearityOrthogonalizer::test_severe_singularity_n5_k37 PASSED [ 69%]
tests/test_adversarial_m1_2_opt3_stress.py::TestPathologicalCollinearityOrthogonalizer::test_top_level_orthogonalize_dataframe_under_pathological_conditions PASSED [ 76%]
tests/test_adversarial_m1_2_opt3_stress.py::TestIllConditionedEntropySolver::test_synthetic_correlation_condition_number_exceeding_1e6 PASSED [ 84%]
tests/test_adversarial_m1_2_opt3_stress.py::TestIllConditionedEntropySolver::test_ill_conditioned_entropy_with_extreme_partial_missingness PASSED [ 92%]
tests/test_adversarial_m1_2_opt3_stress.py::TestIllConditionedEntropySolver::test_pathological_singular_all_ones_correlation_matrix PASSED [100%]

================================== FAILURES ===================================
_ TestChaoticUniverseAndDecayFiltering.test_apply_exponential_decay_filter_duplicate_columns_skipping_vulnerability _
tests\test_adversarial_m1_2_opt3_stress.py:166: in test_apply_exponential_decay_filter_duplicate_columns_skipping_vulnerability
    assert is_smoothed, (
E   AssertionError: Decay filtering was silently skipped on duplicate column: reg_score remains unsmoothed at reg_score    0.8
E     reg_score    0.8
E     Name: 0, dtype: float64
E   assert False
_ TestChaoticUniverseAndDecayFiltering.test_combine_predictions_duplicate_columns_crash_vulnerability _
tests\test_adversarial_m1_2_opt3_stress.py:191: in test_combine_predictions_duplicate_columns_crash_vulnerability
    res = engine.combine_predictions(
trading_system\src\ai\ensemble_scorer.py:2160: in combine_predictions
    raw_vals = pd.to_numeric(reg_df_copy[target_col], errors='coerce')
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.venv\Lib\site-packages\pandas\core\tools\numeric.py:209: in to_numeric
    raise TypeError("arg must be a list, tuple, 1-d array, or Series")
E   TypeError: arg must be a list, tuple, 1-d array, or Series
============================== warnings summary ===============================
tests/test_adversarial_m1_2_opt3_stress.py::TestChaoticUniverseAndDecayFiltering::test_pathological_nans_and_infinities_resilience
  D:\Finance\code\stock\.venv\Lib\site-packages\numpy\lib\nanfunctions.py:1215: RuntimeWarning: Mean of empty slice
    return np.nanmean(a, axis, out=out, keepdims=keepdims)

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ===========================
FAILED tests/test_adversarial_m1_2_opt3_stress.py::TestChaoticUniverseAndDecayFiltering::test_apply_exponential_decay_filter_duplicate_columns_skipping_vulnerability - AssertionError: Decay filtering was silently skipped on duplicate column: reg_score remains unsmoothed at reg_score    0.8
  reg_score    0.8
  Name: 0, dtype: float64
assert False
FAILED tests/test_adversarial_m1_2_opt3_stress.py::TestChaoticUniverseAndDecayFiltering::test_combine_predictions_duplicate_columns_crash_vulnerability - TypeError: arg must be a list, tuple, 1-d array, or Series
================== 2 failed, 11 passed, 1 warning in 24.59s ===================
```

### Direct Source Code Observations
1. **`trading_system/src/ai/ensemble_scorer.py` lines 3805–3818**:
```python
3805:         df_filtered = current_scores.copy()
...
3813:         sym_col = 'symbol' if 'symbol' in df_filtered.columns else None
3814:         if sym_col and sym_col in previous_scores.columns:
3815:             prev_clean = previous_scores.drop_duplicates(subset=[sym_col])
3816:             if prev_clean.columns.has_duplicates:
3817:                 prev_clean = prev_clean.loc[:, ~prev_clean.columns.duplicated(keep='first')]
3818:             prev_indexed = prev_clean.set_index(sym_col)
3819:             curr_indexed = df_filtered.set_index(sym_col)
```
Worker M1 explicitly added column deduplication for `previous_scores` (`prev_clean = prev_clean.loc[:, ~prev_clean.columns.duplicated(keep='first')]`), but **omitted** column deduplication for `df_filtered` (`current_scores`).

2. **`trading_system/src/ai/ensemble_scorer.py` line 3845**:
```python
3845:                 if strat_key in half_lives and col in prev_indexed.columns and pd.api.types.is_numeric_dtype(curr_indexed[col]):
```
When `current_scores` has duplicate columns, `curr_indexed[col]` returns a 2-D `DataFrame` instead of a 1-D `Series`. In pandas, `pd.api.types.is_numeric_dtype(df)` returns `False`. Hence, exponential decay filtering is silently skipped on that column, returning unsmoothed raw scores.

3. **`trading_system/src/ai/ensemble_scorer.py` line 2160**:
```python
2159:             if target_col is not None and target_col in reg_df_copy.columns:
2160:                 raw_vals = pd.to_numeric(reg_df_copy[target_col], errors='coerce')
```
When `reg_df` has duplicate columns (e.g. from upstream merges or data join concatenations), `reg_df_copy[target_col]` yields a 2-D DataFrame. `pd.to_numeric` crashes with verbatim `TypeError: arg must be a list, tuple, 1-d array, or Series`.

4. **Successful Baseline Robustness**:
- **F08 (Orthogonalizer Singularity Protection)**:
  * 5 constant columns (`0.0, 0.5, 1.0, -2.5, 100.0`) are isolated in the active subspace and preserved with exact precision ($< 10^{-6}$ error) without noise bleed (`test_five_constant_columns_isolation` PASSED).
  * Pairwise duplicate identical columns do not trigger division-by-zero or numerical explosion (`test_multiple_pairwise_identical_duplicate_columns` PASSED).
  * Extreme rank deficiency ($N=5, K=37, N \ll K$) executes cleanly without `LinAlgError` or NaNs (`test_severe_singularity_n5_k37` PASSED).
  * End-to-end `FactorOrthogonalizerEngine.orthogonalize(df, strategy_cols=cols)` returns finite scores strictly in $[0.0, 1.0]$ (`test_top_level_orthogonalize_dataframe_under_pathological_conditions` PASSED).
- **F07 (Ill-Conditioned Entropy Solver)**:
  * Synthetic correlation matrix with condition number $> 10^6$ converges to strictly normalized weights summing to $1.0000$ (`test_synthetic_correlation_condition_number_exceeding_1e6` PASSED).
  * Extreme partial missingness (10 active strategies with condition number $> 10^7$ and 27 missing strategies) successfully produces 37 positive finite weights summing strictly to $1.0000$ (`test_ill_conditioned_entropy_with_extreme_partial_missingness` PASSED).
  * Pathological rank-1 all-ones correlation matrix handles singular state gracefully (`test_pathological_singular_all_ones_correlation_matrix` PASSED).
- **Dynamic Universe Churn & Memory**:
  * 15 consecutive rounds of churning universes (entering, exiting, oscillating between 5 and 45 symbols) run cleanly.
  * Scores remain strictly within $[0.0, 1.0]$.
  * Memory in `_prev_filtered_scores['global']` is strictly bounded to the size of the active round universe (length matches current universe, confirming no accumulation of dead symbols).

---

## 2. Logic Chain

1. **Observation**: In `test_combine_predictions_duplicate_columns_crash_vulnerability`, passing a DataFrame with duplicate columns to `combine_predictions` raises `TypeError: arg must be a list, tuple, 1-d array, or Series` at line 2160 of `ensemble_scorer.py`.
2. **Inference**: In production quantitative data pipelines, joins, feature merges, and legacy column mappings frequently create duplicated column names. Without defensive column deduplication at the entry of `combine_predictions` or in `reg_df_copy`, the entire pipeline crashes on `pd.to_numeric()`.
3. **Observation**: In `test_apply_exponential_decay_filter_duplicate_columns_skipping_vulnerability`, `apply_exponential_decay_filter` contains `if prev_clean.columns.has_duplicates: prev_clean = prev_clean.loc[:, ~prev_clean.columns.duplicated(keep='first')]` for `previous_scores`, but no equivalent deduplication for `df_filtered` (`current_scores`).
4. **Inference**: When `current_scores` has duplicate column names, `curr_indexed[col]` evaluates to a 2D DataFrame. In pandas, `pd.api.types.is_numeric_dtype` returns `False` for DataFrames. Consequently, line 3845 evaluates to `False`, and exponential decay filtering is silently skipped. Raw factor signals pass through unfiltered, breaking the feature guarantee of F04.
5. **Deduction**: Both failure modes are directly triggered by duplicate column names in the input DataFrames—an explicit adversarial stress test requirement defined in the Challenger Mission ("repeated runs of combine_predictions with dynamically changing universes... duplicate columns...").
6. **Required Remediation by Worker M1**:
   - In `apply_exponential_decay_filter()`: Add `if df_filtered.columns.has_duplicates: df_filtered = df_filtered.loc[:, ~df_filtered.columns.duplicated(keep='first')]` right after `df_filtered = current_scores.copy()`.
   - In `combine_predictions()`: Add defensive deduplication for input prediction DataFrames (e.g. `if not reg_df.empty and reg_df.columns.has_duplicates: reg_df = reg_df.loc[:, ~reg_df.columns.duplicated(keep='first')]` and similarly for `merged`), ensuring `reg_df_copy[target_col]` is always a 1-D Series.

---

## 3. Caveats

- All other 11 stress test cases (F07 entropy solver with condition number $> 10^7$ and missingness, F08 orthogonalizer with 5 constant columns and $N=5, K=37$, chaotic universe churn across 15 rounds, duplicate symbol rows, boundary zero/one scores, and NaNs) passed 100% without issues.
- The existing test suite (`tests/test_m1_quant_enhancements.py`, 14 tests) continues to pass 100% in 16.63s.
- The issue is isolated to column deduplication in `apply_exponential_decay_filter` and `combine_predictions`.

---

## 4. Conclusion

**Verdict: REQUEST_CHANGES**

Worker M1 must address the two empirical vulnerabilities:
1. **Deduplicate `current_scores` in `apply_exponential_decay_filter`**:
   Ensure `df_filtered` deduplicates columns (`df_filtered = df_filtered.loc[:, ~df_filtered.columns.duplicated(keep='first')]`) so that `curr_indexed[col]` is a Series and exponential smoothing is not skipped when duplicate columns exist.
2. **Deduplicate input columns in `combine_predictions`**:
   Ensure input DataFrames (`reg_df`, `s_df`, `merged`) deduplicate columns to prevent `TypeError: arg must be a list, tuple, 1-d array, or Series` at line 2160 (`pd.to_numeric`).

---

## 5. Verification Method

### Test Command
```powershell
.venv\Scripts\pytest.exe tests/test_adversarial_m1_2_opt3_stress.py -v
```

### Expected Results After Fix
- All 13 tests in `tests/test_adversarial_m1_2_opt3_stress.py` must PASS 100% (13 passed, 0 failed).
- `test_apply_exponential_decay_filter_duplicate_columns_skipping_vulnerability` must verify `reg_score` is properly smoothed to $< 0.50$.
- `test_combine_predictions_duplicate_columns_crash_vulnerability` must execute without `TypeError` and return valid `ensemble_score`.

### Invalidation Conditions
- Any failure or unhandled exception in `tests/test_adversarial_m1_2_opt3_stress.py`.
- Any regression in `tests/test_m1_quant_enhancements.py` (14 tests).
