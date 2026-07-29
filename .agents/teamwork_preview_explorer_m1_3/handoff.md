# Handoff Report — Strategy Data Coverage & Automated Test Suite Audit (R3)

**Author**: Explorer 3 (Milestone 1)  
**Date**: 2026-07-29  
**Working Directory**: `d:\Finance\code\stock\.agents\teamwork_preview_explorer_m1_3`  

---

## 1. Observation

- **Premature NaN Mutation to 0.0**: In `trading_system/src/ai/ensemble_scorer.py` (lines 705-709), `calculate_ensemble_score()` executes:
  ```python
  fill_cols = [
      'reg_pred', 'reg_score', 'surge_score', 'll_raw', 'll_score',
      'vcp_rule_score', 'vcp_ml_score', 'lstm_score', 'stat_arb_score',
      'sector_score', 'rim_score', 'event_score', 'mq_score',
      'iv_skew_score', 'order_flow_score', 'reversal_score'
  ]
  for col in fill_cols:
      if col in merged.columns:
          merged[col] = merged[col].fillna(0.0)
  ```
- **False 100% Coverage Output**: In `trading_system/src/analysis/coverage_analyzer.py` (lines 62-67), `analyze_coverage()` calculates validity via:
  ```python
  series = ensemble_df[c_col]
  valid_mask = series.notna() & np.isfinite(series)
  valid_cnt = int(valid_mask.sum())
  ```
  Because all NaNs were converted to `0.0`, `series.notna()` returns `True` for every symbol. Thus `strategy_data_coverage_report.txt` records 100.0% coverage across all 14 strategies regardless of missing data.
- **Global Table Missingness Check Flaw**: In `coverage_analyzer.py` (line 84), `has_fund = (features_df is not None and not features_df.empty and any(c in features_df.columns for c in fund_cols))` checks table columns rather than checking per-symbol missing values (`features_df.loc[sym]`), causing missing fundamental data reasons to be misclassified.
- **Pytest Suite Failures**: `.pytest_cache/v/cache/lastfailed` contains 13 failing test node IDs from prior executions, including E2E phase 3 tests (`tests/phase3/e2e/test_e2e.py`) and macro stress test (`tests/test_macro_stress.py::TestMacroStress::test_screener_predictions_identical`).
- **Test Suite Integration Gap**: Existing unit test `test_strategy_coverage_analyzer()` in `trading_system/tests/test_kst_and_coverage_reasoning.py` feeds raw mock DataFrames with NaNs directly to `analyze_coverage()`, missing the integration bug caused by `ensemble_scorer.py`.

---

## 2. Logic Chain

1. `run_pipeline.py` calls `EnsembleScoringEngine.calculate_ensemble_score()` to compute `ensemble_df`.
2. `calculate_ensemble_score()` merges outputs from all 14 strategies via outer join. Where a strategy lacks predictions for a symbol, the resulting merged column is `NaN`.
3. Before returning `merged` as `ensemble_df`, `calculate_ensemble_score()` applies `fillna(0.0)` to all strategy score columns to prepare for downstream string formatting.
4. `run_pipeline.py` then passes this mutated `ensemble_df` to `StrategyCoverageAnalyzer.analyze_coverage()`.
5. `analyze_coverage()` checks `series.notna() & np.isfinite(series)`. Since `0.0` is non-null and finite, it marks every symbol as having a valid score.
6. The analyzer outputs 100.0% coverage across all strategies, rendering the coverage report blind to missing data and strategy evaluation failures.
7. Furthermore, when analyzing missingness reasons for fundamental strategies (`rim_valuation`, `mq_factor`), checking `features_df.columns` instead of `features_df.loc[sym]` prevents `NO_FUNDAMENTAL_DATA` from being reported when `features_df` exists.

---

## 3. Caveats

- **Sandbox Execution Limit**: Direct invocation of pytest via `run_command` returned a host sandbox environment error (`sandbox configuration error: readwrite stock: non-absolute file path`). Test failure node IDs were extracted directly from pytest's cache file (`.pytest_cache/v/cache/lastfailed`).
- **Read-Only Scope**: In accordance with Explorer role instructions, no source files outside the working directory `.agents/teamwork_preview_explorer_m1_3/` were edited.

---

## 4. Conclusion

The Strategy Data Coverage system suffers from a critical integration defect where `EnsembleScoringEngine` mutates missing strategy scores (NaN) to `0.0` prior to calling `StrategyCoverageAnalyzer`. This results in false 100.0% coverage figures. In addition, `coverage_analyzer.py` misclassifies per-symbol fundamental missingness reasons, and the pytest test suite lacks integration tests connecting `ensemble_scorer` outputs with `coverage_analyzer`.

Implementing the recommended fixes (preserving raw score NaNs for coverage analysis and checking per-symbol fundamental missingness) will restore full accuracy to the strategy data coverage report for all 3,379 universe symbols.

---

## 5. Verification Method

To verify these findings independently:
1. **Inspect NaN Mutation in Ensemble Scorer**:
   View `trading_system/src/ai/ensemble_scorer.py` lines 705-709 to confirm `merged[col] = merged[col].fillna(0.0)`.
2. **Inspect Coverage Analyzer Logic**:
   View `trading_system/src/analysis/coverage_analyzer.py` lines 62-67 to confirm validity check `series.notna() & np.isfinite(series)`.
3. **Inspect Saved Report Artifacts**:
   View `trading_system/result/strategy_data_coverage_report.txt` and `scratch/run_30272907164/merged-results/strategy_data_coverage_report_KOSPI.txt` to confirm that reported coverage is 100.0% for all strategies despite missing underlying predictions.
4. **Inspect Test Cache for Failures**:
   View `trading_system/.pytest_cache/v/cache/lastfailed` to observe recorded failures in `test_e2e.py` and `test_macro_stress.py`.
5. **Verify Fix**:
   Pass a DataFrame containing `np.nan` values from `calculate_ensemble_score()` (without `fillna(0.0)`) into `analyze_coverage()` to confirm that valid count and coverage percentages accurately reflect missing values.
