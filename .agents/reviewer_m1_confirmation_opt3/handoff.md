# Milestone 1 Confirmation Review & Adversarial Challenge Report

**Agent**: Reviewer M1 Confirmation (`reviewer`, `critic`)  
**Working Directory**: `d:\Finance\code\stock\.agents\reviewer_m1_confirmation_opt3`  
**Verdict**: **APPROVE**  

---

## 1. Observation

### 1.1 Code Inspection of Remediation Fixes (`trading_system/src/ai/ensemble_scorer.py`)

1. **Fix 1: Index Preservation in Multi-Market Slices (`ensemble_scorer.py:821-848, 3824-3875`)**:
   - **`apply_exponential_decay_filter`** (lines 3837, 3874-3875):
     ```python
     orig_idx = df_filtered.index
     ...
     df_filtered = curr_indexed.reset_index()
     df_filtered.index = orig_idx
     ```
     Preserves the input DataFrame's original index and restores it after resetting the index on `curr_indexed`.
   - **`_apply_decay_filtering_with_cache`** (lines 821-848):
     ```python
     sub_df = df_out.loc[mkt_mask].copy()
     orig_sub_idx = sub_df.index
     ...
     sub_filtered = self.apply_exponential_decay_filter(
         current_scores=sub_df,
         previous_scores=prev_scores,
         regime=mkt_regime
     )
     sub_filtered.index = orig_sub_idx
     ...
     filtered_chunks.append(sub_filtered)
     ...
     df_out = pd.concat(filtered_chunks, axis=0).reindex(df_out.index)
     ```
     Guarantees that each market chunk retains its exact, disjoint row indices from `df_out`. `pd.concat(filtered_chunks, axis=0)` produces an index with unique labels, enabling `.reindex(df_out.index)` to execute cleanly without `ValueError: cannot reindex on an axis with duplicate labels`.

2. **Fix 2: Instance-Level Deepcopy of `REGIME_2D_WEIGHTS` (`ensemble_scorer.py:613`)**:
   - In `EnsembleScoringEngine.__init__` (line 613):
     ```python
     self.REGIME_2D_WEIGHTS = {k: dict(v) for k, v in self.__class__.REGIME_2D_WEIGHTS.items()}
     self._load_tuned_regime_weights()
     ```
     Prevents in-place mutation of the shared class-level dictionary `EnsembleScoringEngine.REGIME_2D_WEIGHTS`.
   - Direct verification via 100 repeated instantiations:
     - Class-level weight for `overnight_gap_reversal` in `BULL_LOW_VOL`: `0.010000` (unchanged).
     - Instance 100 weight for `overnight_gap_reversal`: `0.008696` (strictly `>= 0.005` floor).
     - Zero cumulative decay observed across 100 instantiations.

3. **Fix 3: Defensive Column Deduplication (`ensemble_scorer.py:2159-2161, 3825-3826`)**:
   - In `combine_predictions` (lines 2159-2161):
     ```python
     reg_df_copy = reg_df.copy()
     if not reg_df_copy.empty and reg_df_copy.columns.has_duplicates:
         reg_df_copy = reg_df_copy.loc[:, ~reg_df_copy.columns.duplicated(keep='first')]
     ```
     Eliminates `TypeError: arg must be a list, tuple, 1-d array, or Series` when `pd.to_numeric(reg_df_copy[target_col], errors='coerce')` is invoked on inputs with duplicate columns.
   - In `apply_exponential_decay_filter` (lines 3825-3826):
     ```python
     df_filtered = current_scores.copy()
     if df_filtered.columns.has_duplicates:
         df_filtered = df_filtered.loc[:, ~df_filtered.columns.duplicated(keep='first')]
     ```
     Ensures `curr_indexed[col]` evaluates strictly to a 1D `pd.Series`, so `pd.api.types.is_numeric_dtype(curr_indexed[col])` returns `True` and exponential smoothing is never silently bypassed.

### 1.2 Test Execution Results

1. **Milestone 1 Primary & Adversarial Stress Suites (Task-55)**:
   - Command: `.venv\Scripts\pytest.exe tests/test_m1_quant_enhancements.py tests/test_adversarial_m1_stress.py tests/test_adversarial_m1_2_opt3_stress.py -v`
   - Result: **61 passed, 0 failed, 1 warning in 18.06s (100% pass rate)**.
     - `tests/test_m1_quant_enhancements.py`: 15/15 passed (including `test_f04_multi_market_warm_start_preserves_unique_indices_and_smooths`).
     - `tests/test_adversarial_m1_stress.py`: 33/33 passed (including `test_adversarial_instance_isolation_weight_decay`).
     - `tests/test_adversarial_m1_2_opt3_stress.py`: 13/13 passed (including duplicate column and chaotic universe stress tests).

2. **Regression Test Suites (Task-65)**:
   - Command: `.venv\Scripts\pytest.exe tests/test_regime_ensemble.py tests/test_factor_orthogonalization.py tests/test_correlation_suppression.py tests/test_hpo_and_2d_ensemble.py -v`
   - Result: **35 passed, 0 failed in 16.89s (100% pass rate)**.

3. **Combined Test Execution**:
   - Total passed: **96 / 96 tests (100% pass rate)**.

4. **Integrity Audit**:
   - No hardcoded test responses or bypasses detected in `trading_system/src/ai/ensemble_scorer.py`.
   - Implementations are general, resilient algorithms adhering to project architectural standards.

---

## 2. Logic Chain

1. **Reviewer M1-2 Issue (Multi-market Index Clobbering Bug)**:
   - *Observation*: Previously, `df_filtered = curr_indexed.reset_index()` reset the DataFrame slice index to `0..N-1`. Slicing multiple markets in `_apply_decay_filtering_with_cache` caused each slice to have identical labels `0..k`. Concatenating them created duplicate labels in `filtered_chunks`, resulting in an unconditional `ValueError` during `.reindex(df_out.index)`.
   - *Fix Verification*: With `orig_idx = df_filtered.index` and `df_filtered.index = orig_idx` in `apply_exponential_decay_filter`, coupled with `sub_filtered.index = orig_sub_idx` in `_apply_decay_filtering_with_cache`, slice indices are faithfully preserved throughout filtering. The concatenated DataFrame retains the exact unique indices of `df_out`.
   - *Inference*: Multi-market warm-start executions across KOSPI, KOSDAQ, and US markets run seamlessly without index collisions.

2. **Challenger M1-1 Issue (Class-Level Weight Mutation and Weight Decay)**:
   - *Observation*: Previously, `self.REGIME_2D_WEIGHTS` referenced the class dictionary. `_load_tuned_regime_weights()` iteratively mutated and re-normalized the shared dictionary on every engine instantiation, causing untuned strategies (32-37) to decay below the 0.005 floor.
   - *Fix Verification*: In `__init__`, `self.REGIME_2D_WEIGHTS = {k: dict(v) for k, v in self.__class__.REGIME_2D_WEIGHTS.items()}` deepcopies the dictionary onto the instance before `_load_tuned_regime_weights()` runs.
   - *Inference*: Repeated instantiations leave `EnsembleScoringEngine.REGIME_2D_WEIGHTS` pristine. After 100 instantiations, base weights for strategies 32-37 remain securely above the 0.005 floor (`0.008696 >= 0.005`).

3. **Challenger M1-2 Issue (Defensive Column Deduplication)**:
   - *Observation*: Duplicated column names in input DataFrames caused `pd.to_numeric` in `combine_predictions` to receive a 2D DataFrame (raising `TypeError`) and caused `curr_indexed[col]` in `apply_exponential_decay_filter` to be non-numeric (silently skipping smoothing).
   - *Fix Verification*: Defensive deduplication `.loc[:, ~df.columns.duplicated(keep='first')]` was added in both functions. Adversarial tests confirm `combine_predictions` processes duplicate columns without crashing and `apply_exponential_decay_filter` smoothly filters values from `0.80` down to `0.21` (alpha=0.034) rather than skipping.
   - *Inference*: The scoring engine is now defensively shielded against upstream column duplication defects.

---

## 3. Caveats

- `self.REGIME_2D_WEIGHTS` is now an instance dictionary. External code expecting modifications to an instance's `REGIME_2D_WEIGHTS` to affect other instances will observe isolation (which is the intended design).
- `_prev_filtered_scores` cache maintains per-market caches for fast multi-market warm starts; callers resetting state can use `engine.reset_decay_filter_state(market=...)`.

---

## 4. Conclusion

All 3 defects reported in Iteration 1 have been completely, cleanly, and genuinely resolved. Independent code analysis, automated adversarial stress testing, and regression suite execution confirm:
1. Zero index clobbering or duplicate label errors in multi-market warm starts.
2. Complete instance isolation of `REGIME_2D_WEIGHTS` with zero cumulative weight decay.
3. Robust column deduplication preventing runtime crashes and silent filter skipping.
4. 100% test pass rate across all 96 primary, adversarial, and regression tests.

**Verdict**: **APPROVE** for Milestone 1 Completion.

---

## 5. Verification Method

To independently reproduce and verify this review:

```powershell
# 1. Multi-market warm-start direct reproduction
.venv\Scripts\python.exe -c "import sys; sys.path.insert(0, 'trading_system'); import pandas as pd; from src.ai.ensemble_scorer import EnsembleScoringEngine; e = EnsembleScoringEngine(); df1 = pd.DataFrame({'symbol': ['A', 'B'], 'market': ['KOSPI', 'KOSDAQ'], 'reg_score': [0.5, 0.6]}); e._apply_decay_filtering_with_cache(df1, [('regression', 'reg_score')]); df2 = pd.DataFrame({'symbol': ['A', 'B'], 'market': ['KOSPI', 'KOSDAQ'], 'reg_score': [0.7, 0.8]}); out = e._apply_decay_filtering_with_cache(df2, [('regression', 'reg_score')]); print('SUCCESS: shape=', out.shape, 'indices=', list(out.index))"

# 2. 100-instance weight isolation test
.venv\Scripts\python.exe -c "import sys; sys.path.insert(0, 'trading_system'); from src.ai.ensemble_scorer import EnsembleScoringEngine; engines = [EnsembleScoringEngine() for _ in range(100)]; w = EnsembleScoringEngine.REGIME_2D_WEIGHTS['BULL_LOW_VOL']; inst_w = engines[-1].REGIME_2D_WEIGHTS['BULL_LOW_VOL']; print('Class weight:', w['overnight_gap_reversal'], 'Instance 100 weight:', inst_w['overnight_gap_reversal']); assert inst_w['overnight_gap_reversal'] >= 0.005; print('ISOLATION PASSED')"

# 3. Duplicate column combine_predictions & decay filter test
.venv\Scripts\python.exe -c "import sys; sys.path.insert(0, 'trading_system'); import pandas as pd; from src.ai.ensemble_scorer import EnsembleScoringEngine; e = EnsembleScoringEngine(); reg = pd.DataFrame([['AAPL', 0.1, 0.1]], columns=['symbol', 'expected_return', 'expected_return']); surge = pd.DataFrame([['AAPL', 0.8]], columns=['symbol', 'surge_probability']); res = e.combine_predictions(reg, surge, regime='BULL_LOW_VOL'); print('combine_predictions dup cols OK, score=', res['ensemble_score'].iloc[0])"

# 4. Run Milestone 1 primary and adversarial suites (61 passed)
.venv\Scripts\pytest.exe tests/test_m1_quant_enhancements.py tests/test_adversarial_m1_stress.py tests/test_adversarial_m1_2_opt3_stress.py -v

# 5. Run regression suites (35 passed)
.venv\Scripts\pytest.exe tests/test_regime_ensemble.py tests/test_factor_orthogonalization.py tests/test_correlation_suppression.py tests/test_hpo_and_2d_ensemble.py -v
```
