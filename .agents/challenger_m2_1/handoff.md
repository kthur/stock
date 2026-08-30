# Milestone 2 Empirical Stress Test Handoff Report

## 1. Observation

### Test Execution Command
```powershell
$env:PYTHONPATH="trading_system;trading_system/src;."
.venv\Scripts\pytest.exe tests/test_advanced_ensemble_features.py tests/test_regime_ensemble.py tests/test_challenger_m2_empirical_stress.py -v
```

### Test Results Summary
- **Total Tests Run**: 24 tests
- **Passed**: 17 tests
- **Failed**: 7 tests
- **Exit Code**: 1

### Verbatim Error Logs & Defect Observations

#### Defect 1: Ambiguous DataFrame Truth Value in `calculate_ensemble_score`
- **File**: `trading_system/src/ai/ensemble_scorer.py`
- **Lines**: 1519-1520
- **Verbatim Code**:
```python
range_expansion_df=range_expansion_df or range_expansion_breakout_df,
range_expansion_breakout_df=range_expansion_breakout_df or range_expansion_df,
```
- **Verbatim Error**:
```
ValueError: The truth value of a DataFrame is ambiguous. Use a.empty, a.bool(), a.item(), a.any() or a.all().
```
- **Impact**:
When `range_expansion_df` or `range_expansion_breakout_df` is supplied as a valid `pd.DataFrame`, evaluating `df1 or df2` implicitly invokes `bool(df1)`, which raises a fatal `ValueError` and causes `calculate_ensemble_score` to crash on runtime execution.


#### Defect 2: 1D Regime 1 (SIDEWAYS) Weights Mathematical Conservation Violation
- **File**: `trading_system/src/ai/ensemble_scorer.py`
- **Lines**: 153-188 (`REGIME_WEIGHTS[1]`)
- **Verbatim Error**:
```
AssertionError: 0.9800000000000004 != 1.0 within 5 places (0.019999999999999574 difference) : 1D Regime 1 weights sum to 0.9800000000000004, expected 1.000
```
- **Impact**:
The sum of all 34 strategy weights in `REGIME_WEIGHTS[1]` is `0.980000`, failing the mathematical constraint that weights across all strategies must strictly sum to `1.000`.


### Verified Resilient Features
1. **Singular Matrix & Tikhonov Regularizer**:
   - `test_singular_covariance_matrix_tikhonov_regularizer_pca_zca`: PASSED. PCA-ZCA whitening (`_pca_zca_symmetric`), Gram-Schmidt (`_gram_schmidt`), and Equalized Spectral Residual Whitening (`_esrw_whitening`) successfully handled strictly rank-1 singular covariance matrices across all 34 strategies without NaN/Inf generation.
2. **High-Dimensional Singularity (N < K)**:
   - `test_n_less_than_k_high_dimensional_singularity`: PASSED. N=5 stocks vs K=34 strategies executed cleanly with output scores bounded in [0.0, 1.0].
3. **Zero-Variance Columns**:
   - `test_zero_variance_columns_in_whitening`: PASSED. Constant score columns (0.0, 0.5, 1.0) were processed safely without division by zero.
4. **2D Regime Matrix Weights**:
   - `test_2d_regime_weights_conservation_and_positivity`: PASSED. All 6 2D regimes (`BEAR_LOW_VOL`, `BEAR_HIGH_VOL`, `SIDEWAYS_LOW_VOL`, `SIDEWAYS_HIGH_VOL`, `BULL_LOW_VOL`, `BULL_HIGH_VOL`) strictly sum to `1.00000` with strictly positive weights.
5. **Sparse Missingness & Zero-Weighting**:
   - `test_sparse_random_missingness_across_34_strategies`: PASSED. Missing strategies were gracefully zero-weighted and renormalized.
6. **Meta-Ensemble Learner & Factor Suppression**:
   - `test_meta_ensemble_learner_with_all_34_strategies`: PASSED. `MetaEnsembleLearner` successfully accepts and rolling-trains across all 34 strategy columns.
   - `test_factor_suppression_with_34_strategies_and_momentum_cluster`: PASSED. Momentum cluster suppression correctly penalizes correlated strategies while conserving weight sum = 1.000.

---

## 2. Logic Chain

1. **Premise 1**: In `worker_m2/handoff.md`, the worker claimed that all 34 strategy weights strictly sum to 1.000 in `REGIME_WEIGHTS` and that `calculate_ensemble_score` correctly handles `range_expansion_df` and `range_expansion_breakout_df`.
2. **Observation 1**: Mathematical summation of `REGIME_WEIGHTS[1]` yields `0.980`, demonstrating that 0.02 of weight is missing and violates the 1.000 conservation law.
3. **Observation 2**: Lines 1519-1520 of `ensemble_scorer.py` evaluate `range_expansion_df or range_expansion_breakout_df`. In Python, the `or` operator evaluates the boolean truth value of `range_expansion_df`. For pandas DataFrames, `bool(df)` non-emptiness check raises `ValueError: The truth value of a DataFrame is ambiguous`.
4. **Conclusion from Observations**: Because `calculate_ensemble_score` crashes on valid DataFrame inputs and 1D sideways regime weights do not conserve the unit sum, Milestone 2 cannot be approved in its current state.

---

## 3. Caveats

- All matrix orthogonalization algorithms (PCA-ZCA, ESRW, Gram-Schmidt) and 2D regime weights are mathematically sound and resilient to extreme singularity.
- The two identified defects are localized implementation bugs in `trading_system/src/ai/ensemble_scorer.py` and can be rapidly rectified by the worker.

---

## 4. Conclusion & Verdict

**Verdict**: **`REQUEST_CHANGES`**

### Required Action Items for Worker:
1. **Fix DataFrame boolean evaluation in `trading_system/src/ai/ensemble_scorer.py:1519-1520`**:
   Replace:
   ```python
   range_expansion_df=range_expansion_df or range_expansion_breakout_df,
   range_expansion_breakout_df=range_expansion_breakout_df or range_expansion_df,
   ```
   With:
   ```python
   range_expansion_df=range_expansion_df if range_expansion_df is not None else range_expansion_breakout_df,
   range_expansion_breakout_df=range_expansion_breakout_df if range_expansion_breakout_df is not None else range_expansion_df,
   ```
2. **Rebalance `REGIME_WEIGHTS[1]` (SIDEWAYS) in `trading_system/src/ai/ensemble_scorer.py:153-188`**:
   Ensure the sum of all 34 strategy weights equals exactly `1.000` (e.g. adjust `regression` to 0.05 and `stat_arb` to 0.07, or allocate the missing 0.02 across rotation strategies).

---

## 5. Verification Method

To re-verify after applying the fixes:
```powershell
$env:PYTHONPATH="trading_system;trading_system/src;."
.venv\Scripts\pytest.exe tests/test_advanced_ensemble_features.py tests/test_regime_ensemble.py tests/test_challenger_m2_empirical_stress.py -v
```
Ensure all 24 tests pass with exit code 0.
