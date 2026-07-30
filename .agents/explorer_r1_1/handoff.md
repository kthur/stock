# Handoff Report — Explorer 1 (R1: Dynamic Re-weighting Scoring for Missing Data)

## 1. Observation
- **Inspected Files:**
  - `trading_system/src/ai/ensemble_scorer.py` (lines 837–889):
    - `strategy_cols` maps 17 strategy names to prediction DataFrame column names:
      `regression` -> `reg_score`, `surge` -> `surge_score`, `lead_lag` -> `ll_score`, `vcp_rule` -> `vcp_rule_score`, `vcp_ml` -> `vcp_ml_score`, `lstm` -> `lstm_score`, `stat_arb` -> `stat_arb_score`, `sector_rotation` -> `sector_score`, `rim_valuation` -> `rim_score`, `event_driven` -> `event_score`, `mq_factor` -> `mq_score`, `iv_skew` -> `iv_skew_score`, `order_flow` -> `order_flow_score`, `short_term_reversal` -> `reversal_score`, `arm_factor` -> `arm_score`, `card_factor` -> `card_score`, `latr_factor` -> `latr_score`.
    - Per-symbol vectorized weight accumulation (lines 866–879):
      ```python
      total_score_series = pd.Series(0.0, index=merged.index)
      total_weight_series = pd.Series(0.0, index=merged.index)

      for strat_name, score_col in strategy_cols:
          w = weights.get(strat_name, 0.10)
          if score_col in merged.columns:
              valid_mask = merged[score_col].notna() & np.isfinite(merged[score_col])
              total_score_series += merged[score_col].fillna(0.0) * w * valid_mask.astype(float)
              total_weight_series += w * valid_mask.astype(float)

      safe_weight_series = total_weight_series.replace(0.0, np.nan)
      linear_score = (total_score_series / safe_weight_series).fillna(0.0).clip(0.0, 1.0)
      ```
    - Preservation of raw NaNs for coverage analysis (lines 900–904):
      ```python
      self.raw_scores = merged.copy()
      merged.attrs['raw_scores'] = self.raw_scores
      ```
  - `trading_system/src/analysis/coverage_analyzer.py` (lines 101–160):
    - `StrategyCoverageAnalyzer` uses `raw_scores` (or `ensemble_df.attrs['raw_scores']`) to check `series.notna() & np.isfinite(series)` for exact valid/missing counts and categorizes missingness reasons (`INSUFFICIENT_PRICE_HISTORY`, `NO_FUNDAMENTAL_DATA`, `NO_OPTIONS_CHAIN`, `NO_COINTEGRATED_PAIR`, `STRATEGY_SIGNAL_NEUTRAL`).
  - `trading_system/tests/test_r1_ensemble_regime_fixes.py` (lines 18–84):
    - Contains unit tests `test_valid_zero_scores_not_discarded` and `test_raw_scores_preserves_nans_for_coverage_analyzer`.

## 2. Logic Chain
1. **Observation 1**: In `combine_predictions`, `strategy_cols` lists all 17 strategies, and for each strategy $k$, $w_k$ is added to `total_weight_series` only when `valid_mask` is `True` (`merged[score_col].notna() & np.isfinite(merged[score_col])`).
2. **Observation 2**: If a score is missing (`NaN`, `None`, or omitted DataFrame column), `valid_mask` is `False`. The weight $w_k$ is NOT added to `total_weight_series`, and $0.0$ is added to `total_score_series`.
3. **Observation 3**: Dividing `total_score_series` by `total_weight_series` calculates:
   $$E_i = \frac{\sum_{k \in V_i} w_k \cdot X_{i,k}}{\sum_{k \in V_i} w_k} = \sum_{k \in V_i} \tilde{w}_{i,k} \cdot X_{i,k} \quad \text{where } \tilde{w}_{i,k} = \frac{w_k}{\sum_{m \in V_i} w_m}$$
   where $V_i$ is the set of valid strategies for symbol $i$.
4. **Conclusion**: $\sum_{k \in V_i} \tilde{w}_{i,k} = 1.0$ (100%), which guarantees that valid non-missing strategy weights are normalized to sum to 100% per symbol, while valid $0.0$ scores are retained in $V_i$ to provide accurate bearish signal weighting.

## 3. Caveats
- If `MetaEnsembleLearner` (2nd stage stacking Ridge model) is fitted, its `predict(merged)` method fills NaNs with 0.0 before dot product prediction. The linear score `linear_score` (which undergoes dynamic re-weighting) is blended 50:50 with `meta_score`. If `MetaEnsembleLearner` is not fitted, the system falls back directly to `linear_score`.
- If all 17 strategies are missing for a symbol ($V_i = \emptyset$), $W_i = 0.0$, resulting in a fallback score of $0.0$.

## 4. Conclusion
The dynamic weight rescaling algorithm in `src/ai/ensemble_scorer.py` correctly and robustly re-normalizes active strategy weights to 100% on a per-symbol basis when strategy predictions are missing, without penalizing stocks with missing optional features (e.g. Options IV Skew or DART filings). Raw scores are preserved for `StrategyCoverageAnalyzer` to provide full transparency on data missingness.

## 5. Verification Method
- **Unit Test Command:**
  `.venv\Scripts\python.exe -m pytest tests/test_r1_ensemble_regime_fixes.py -v`
- **Files to Inspect:**
  - `trading_system/src/ai/ensemble_scorer.py`
  - `trading_system/src/analysis/coverage_analyzer.py`
  - `trading_system/tests/test_r1_ensemble_regime_fixes.py`
- **Invalidation Conditions:**
  - If `valid_mask` is changed to exclude valid `0.0` scores (e.g., `series > 0.0`), valid zero-scores will be incorrectly treated as missing data.
  - If `raw_scores` with NaNs is overwritten before being attached to `merged.attrs['raw_scores']`, `StrategyCoverageAnalyzer` will falsely report 100% coverage across all strategies.
