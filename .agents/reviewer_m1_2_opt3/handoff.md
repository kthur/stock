# Review and Adversarial Challenge Report: Milestone 1 (F04, F06, F07, F08)

**Reviewer**: Reviewer M1-2 (`reviewer_critic`)  
**Verdict**: **REQUEST_CHANGES**  
**Overall Risk Assessment**: **HIGH** (Functional failure of Feature F04 in multi-market production operations)

---

## 1. Observation

### 1.1 Integrity Check
- **Source Code Verification**: Checked `trading_system/src/ai/ensemble_scorer.py`, `trading_system/src/ai/factor_suppression.py`, and `trading_system/src/ai/factor_orthogonalizer.py`.
  - No hardcoded test values, facade implementations, or bypass shortcuts were detected.
  - Mathematical formulations for F06 (4-pillar clustering, Bessembinder S-curve), F07 (convex entropy allocation), and F08 (active subspace isolation) are fully implemented.

### 1.2 Baseline Test Suite Results
- Executed:
  ```bash
  .venv\Scripts\pytest.exe tests/test_m1_quant_enhancements.py tests/test_factor_orthogonalization.py tests/test_correlation_suppression.py tests/test_regime_ensemble.py -v
  ```
  - Result: `36 passed in 28.52s (exit code 0)`
- Extended regression suite:
  ```bash
  .venv\Scripts\pytest.exe tests/test_m1_quant_enhancements.py tests/test_factor_orthogonalization.py tests/test_correlation_suppression.py tests/test_regime_ensemble.py tests/test_hpo_and_2d_ensemble.py tests/test_system_wide_world_class_improvements.py -v
  ```
  - Result: `55 passed in 65.93s (exit code 0)`

### 1.3 Critical Finding Observation: F04 Multi-Market Index Clobbering Bug
- **Location**:
  - `trading_system/src/ai/ensemble_scorer.py`, line 3851 in `apply_exponential_decay_filter()`:
    ```python
    df_filtered = curr_indexed.reset_index()
    ```
  - `trading_system/src/ai/ensemble_scorer.py`, lines 814–845 in `_apply_decay_filtering_with_cache()`:
    ```python
    if has_market_col:
        unique_markets = df_out['market'].dropna().unique()
        filtered_chunks = []
        for mkt in unique_markets:
            mkt_key = str(mkt).lower()
            mkt_mask = (df_out['market'] == mkt)
            sub_df = df_out.loc[mkt_mask].copy()
            ...
            sub_filtered = self.apply_exponential_decay_filter(
                current_scores=sub_df,
                previous_scores=prev_scores,
                regime=mkt_regime
            )
            ...
            filtered_chunks.append(sub_filtered)
        ...
        df_out = pd.concat(filtered_chunks, axis=0).reindex(df_out.index)
    ```
  - `trading_system/src/ai/ensemble_scorer.py`, lines 2781–2794 in `combine_predictions()`:
    ```python
    # Phase 3-A.2: Multi-Horizon Exponential Convolutional Decay Filtering (Feature F04)
    if getattr(self, 'enable_decay_filter', True) and not merged.empty and 'symbol' in merged.columns:
        try:
            merged = self._apply_decay_filtering_with_cache(...)
        except Exception as _dfe:
            logger.warning(f"Decay filter application warning (clean fallback to unfiltered): {_dfe}")
    ```

- **Verbatim Error Reproduction**:
  Running a 2-market universe (`KOSPI` and `KOSDAQ`) on consecutive runs:
  ```python
  import pandas as pd
  from src.ai.ensemble_scorer import EnsembleScoringEngine

  e = EnsembleScoringEngine()
  df1 = pd.DataFrame({'symbol': ['A', 'B'], 'market': ['KOSPI', 'KOSDAQ'], 'reg_score': [0.5, 0.6]})
  out1 = e._apply_decay_filtering_with_cache(df1, [('regression', 'reg_score')])

  df2 = pd.DataFrame({'symbol': ['A', 'B'], 'market': ['KOSPI', 'KOSDAQ'], 'reg_score': [0.7, 0.8]})
  out2 = e._apply_decay_filtering_with_cache(df2, [('regression', 'reg_score')])
  ```
  Result:
  ```
  Traceback (most recent call last):
    File "<string>", line 1, in <module>
    File "D:\Finance\code\stock\trading_system\src\ai\ensemble_scorer.py", line 845, in _apply_decay_filtering_with_cache
      df_out = pd.concat(filtered_chunks, axis=0).reindex(df_out.index)
    File "...\pandas\core\indexes\base.py", line 4436, in reindex
      raise ValueError("cannot reindex on an axis with duplicate labels")
  ValueError: cannot reindex on an axis with duplicate labels
  ```

- **Why the existing test suite passed**:
  In `tests/test_m1_quant_enhancements.py::test_f04_exponential_decay_warm_start_smoothing_and_clipping`:
  Line 164: `"market": ["KOSPI", "KOSPI"]`
  The test only checked a single market, so `unique_markets` had length 1, creating only 1 chunk with unique indices. When processing multiple markets (which the production trading system always does across 5 markets: KOSPI, KOSDAQ, SP500, NASDAQ, RUSSELL2000), `filtered_chunks` has multiple chunks each reset to `[0, 1, ...]`, causing duplicate index labels upon `pd.concat`, and `.reindex(df_out.index)` fails immediately.
  Because of the `try...except Exception as _dfe:` block in `combine_predictions()`, this exception is silently caught, logging a warning and falling back to raw, unfiltered scores on every single day after day 1!

---

## 2. Logic Chain

1. **Premise 1**: In production, `combine_predictions()` processes cross-sectional DataFrames containing multiple markets (`market` column has `'KOSPI'`, `'KOSDAQ'`, `'SP500'`, `'NASDAQ'`, `'RUSSELL2000'`).
2. **Premise 2**: On day 1 (cold start), `self._prev_filtered_scores` is empty (`previous_scores is None`). `apply_exponential_decay_filter()` returns `sub_df.copy()` without index modification. `sub_filtered` retains its original slice indices from `df_out`.
3. **Premise 3**: On day 2+ (warm start), `self._prev_filtered_scores` is populated for each market. `apply_exponential_decay_filter()` executes `curr_indexed = df_filtered.set_index(sym_col)` and then `df_filtered = curr_indexed.reset_index()`.
4. **Premise 4**: Calling `reset_index()` on each market slice resets each slice's index to `RangeIndex(0, len(sub_df))`. Every slice now starts with index label `0`.
5. **Premise 5**: `pd.concat(filtered_chunks, axis=0)` creates a DataFrame with duplicate index labels (e.g. index `[0, 0]`).
6. **Premise 6**: Calling `.reindex(df_out.index)` on a DataFrame with duplicate index labels unconditionally raises `ValueError: cannot reindex on an axis with duplicate labels`.
7. **Premise 7**: In `combine_predictions()` line 2792, `except Exception as _dfe:` catches this error and cleanly falls back to raw scores without applying decay filtering.
8. **Conclusion**: Feature F04 (Multi-Horizon Exponential Convolutional Decay Filtering) is completely neutralized and disabled in multi-market production operations on all warm starts. This constitutes a Critical finding requiring changes.

---

## 3. Review Findings by Feature

### [Critical] Finding 1 (Feature F04): Multi-Market Index Clobbering in `_apply_decay_filtering_with_cache`
- **What**: In `apply_exponential_decay_filter`, calling `curr_indexed.reset_index()` clobbers the DataFrame slice's original index. When `_apply_decay_filtering_with_cache` concatenates slices across multiple markets, the resulting DataFrame has duplicate index labels, causing `pd.concat(filtered_chunks, axis=0).reindex(df_out.index)` to crash with `ValueError: cannot reindex on an axis with duplicate labels`.
- **Where**: `trading_system/src/ai/ensemble_scorer.py`: lines 845 & 3851.
- **Why**: Silently breaks alpha exponential decay filtering across all multi-market daily runs after cold start.
- **Suggested Fix**:
  - In `apply_exponential_decay_filter()`:
    ```python
    sym_col = 'symbol' if 'symbol' in df_filtered.columns else None
    if sym_col and sym_col in previous_scores.columns:
        orig_idx = df_filtered.index  # Preserve original index
        ...
        df_filtered = curr_indexed.reset_index()
        df_filtered.index = orig_idx  # Restore original index
    ```
  - And in `_apply_decay_filtering_with_cache()`:
    ```python
    for mkt in unique_markets:
        mkt_mask = (df_out['market'] == mkt)
        sub_df = df_out.loc[mkt_mask].copy()
        orig_sub_idx = sub_df.index
        ...
        sub_filtered = self.apply_exponential_decay_filter(...)
        sub_filtered.index = orig_sub_idx  # Explicit index safety
        ...
    ```
  - In `tests/test_m1_quant_enhancements.py`: Update `test_f04_exponential_decay_warm_start_smoothing_and_clipping` to explicitly test multi-market DataFrames (e.g. `['KOSPI', 'KOSDAQ']`).

---

### [Verified / Approved] Feature F06: 37-Strategy 4-Pillar Cluster Map & Regime-Adaptive Bessembinder S-Curve
- **Verified**:
  - 4 clusters (`val`: 6, `mom`: 9, `flow`: 9, `cat`: 13) encompass all 37 strategies without omissions.
  - The partition is strictly disjoint: $\text{val} \cap \text{mom} \cap \text{flow} \cap \text{cat} = \emptyset$.
  - Softplus excess conviction $\psi_p(s_{ip})$ and 2D regime coupling matrix $\Omega(R)$ bounded within $[1.00, 1.10]$.
  - `get_regime_adaptive_bessembinder_params()` correctly maps all 7 regimes (`BULL_LOW_VOL` $(1.70, 0.50)$ down to `CRISIS` $(1.20, 0.20)$).
  - `apply_bessembinder_convex_power_law()` preserves strict monotonicity (Spearman $\rho_s = 1.0000$) and bounds outputs strictly in $[0.0, 1.0]$.
  - Adversarial stress tests with all NaNs, $\pm\infty$, unknown regime strings, and constant scores $[0.0, 0.5, 1.0]$ all passed.

---

### [Verified / Approved] Feature F07: Single-Stage Entropy Program for Correlation Suppression
- **Verified**:
  - Auto-activates when $N \ge 10$ and `use_entropy_allocation is not False`.
  - Handles partial missingness gracefully: isolates strategies present in `corr_matrix.columns`, runs `solve_single_stage_entropy_allocation()`, and combines with missing strategies using relative base weight proportions `p_share` and `m_share`.
  - Renormalized weights sum strictly to $1.0000$ with $w_k \ge 0.005$.
  - Adversarial stress tests with empty correlation matrices and ill-conditioned near-singular correlation matrices ($\kappa \approx 10^{15}$) passed without exception.

---

### [Verified / Approved] Feature F08: Active-Subspace Isolation in Factor Orthogonalizer
- **Verified**:
  - In `_pca_zca_symmetric()`, detects zero-variance/singular columns via `(raw_stds < 1e-8) | (stds < 1e-8) | (~np.isfinite(raw_stds)) | (~np.isfinite(stds))`.
  - If all columns singular, returns copy of $X$ directly.
  - If subset singular, isolates active subspace for ZCA whitening and preserves singular/constant columns untouched without cross-feature noise bleed.
  - Automatically bounds `eff_top = min(preserve_top_k, len(active_idx) - 1)` preventing out-of-bounds eigen-slicing.
  - Adversarial stress tests with all-constant matrices and `preserve_top_k > active_columns` passed without exception.

---

## 4. Caveats

- Milestone 1 tests (`test_m1_quant_enhancements.py`) passed all 14 tests initially because the warm-start test only included a single market (`"KOSPI"`), failing to exercise the multi-market partition logic.
- All other features (F01, F02, F03, F05, F06, F07, F08) are fully functional and pass both standard and adversarial stress tests.

---

## 5. Conclusion

- **Verdict**: **REQUEST_CHANGES**
- Worker M1 must fix the index clobbering bug in `apply_exponential_decay_filter` and `_apply_decay_filtering_with_cache` so that multi-market cross-sectional data preserves original indices, enabling warm-start decay filtering to run without crashing or falling back.
- Worker M1 must add a multi-market warm-start test case to `tests/test_m1_quant_enhancements.py` to prevent regression.

---

## 6. Verification Method

### How to independently verify the defect and fix:
```bash
# Reproduce the defect:
.venv\Scripts\python.exe -c "import pandas as pd; from src.ai.ensemble_scorer import EnsembleScoringEngine; e = EnsembleScoringEngine(); df1 = pd.DataFrame({'symbol': ['A', 'B'], 'market': ['KOSPI', 'KOSDAQ'], 'reg_score': [0.5, 0.6]}); e._apply_decay_filtering_with_cache(df1, [('regression', 'reg_score')]); df2 = pd.DataFrame({'symbol': ['A', 'B'], 'market': ['KOSPI', 'KOSDAQ'], 'reg_score': [0.7, 0.8]}); e._apply_decay_filtering_with_cache(df2, [('regression', 'reg_score')])"

# Run adversarial stress test suite:
.venv\Scripts\python.exe .agents/reviewer_m1_2_opt3/stress_test_m1.py

# Run full M1 test suite:
.venv\Scripts\pytest.exe tests/test_m1_quant_enhancements.py tests/test_factor_orthogonalization.py tests/test_correlation_suppression.py tests/test_regime_ensemble.py -v
```
