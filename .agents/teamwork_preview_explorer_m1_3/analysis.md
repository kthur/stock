# Strategy Data Coverage & Automated Test Suite (R3) Audit Report

**Author**: Explorer 3 (Milestone 1)  
**Date**: 2026-07-29  
**Target Scope**: R3 Strategy Data Coverage & Automated Test Suite  
**Working Directory**: `d:\Finance\code\stock\.agents\teamwork_preview_explorer_m1_3`  

---

## 1. Executive Summary

This audit examined the **Strategy Data Coverage & Missingness Analyzer** (`trading_system/src/analysis/coverage_analyzer.py`), the main orchestration pipeline (`trading_system/run_pipeline.py`), the dynamic ensemble scorer (`trading_system/src/ai/ensemble_scorer.py`), output files (`strategy_data_coverage_report.txt`, `ensemble_predictions.txt`), and the automated pytest test suite (`trading_system/tests/`).

### Key Discoveries:
1. **Critical Defect in Coverage Metrics**: `StrategyCoverageAnalyzer` consistently reports **100.0% coverage across all 14 strategies** (with 0 missing symbols), even when strategies fail or lack data. This is caused by `EnsembleScoringEngine.calculate_ensemble_score()` mutating all missing NaN strategy scores to `0.0` (for output report formatting) *before* `run_pipeline.py` passes `ensemble_df` to `coverage_analyzer.py`. Because `0.0` is non-null and finite, the analyzer counts missing strategy outputs as valid predictions.
2. **Fundamental Missingness Scope Flaw**: In `coverage_analyzer.py`, `has_fund` checks whether the global `features_df` DataFrame contains fundamental columns as a whole, rather than checking if an individual symbol `sym` actually has non-NaN fundamental data. Consequently, `NO_FUNDAMENTAL_DATA` is never reported when `features_df` exists.
3. **Macro Indicator Formatting Anomalies**: In `ensemble_predictions.txt`, global macro indicator fields (e.g. `VIX Index`, `US 10Y Yield`, `USD/KRW FX`) frequently output `nan` or fallback values (`0.18 KRW`) due to column name mismatches in `indicator_infer` (`vix` vs `vix_change`, etc.).
4. **Test Suite Status & Gaps**: The project contains over 550 test cases across `trading_system/tests/`. Cache inspection (`.pytest_cache/v/cache/lastfailed`) identified existing failures in E2E tests (`test_e2e.py`) and macro stress tests (`test_macro_stress.py`). Crucially, no integration tests exist for testing coverage analysis on real `ensemble_df` outputs, nor are there tests auditing coverage across all 3,379 universe symbols.

---

## 2. Core Audit Findings & Evidence Chains

### Finding 1: Premature NaN Mutation Masking Data Coverage Defect

#### Observation:
- `trading_system/result/strategy_data_coverage_report.txt` shows 100.0% coverage across all 14 strategies for all evaluated symbols:
```text
=== 14-Strategy Data Coverage & Missingness Report ===
Date: 2026-07-27 17:21 KST
Total Evaluated Symbols: 898

Strategy              Valid Count    Missing Count  Coverage %     Primary Missing Reason        
-------------------------------------------------------------------------------------------------
regression            898            0               100.0%          None (100% Valid)             
surge                 898            0               100.0%          None (100% Valid)             
lead_lag              898            0               100.0%          None (100% Valid)             
...
```

#### Code Evidence & Logic Chain:
1. In `trading_system/src/ai/ensemble_scorer.py`, lines 699-709:
```python
# Fill raw NaNs with 0.0 for report formatting after ensemble score calculation
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
2. In `trading_system/run_pipeline.py`, line 2109, `ensemble_df` is computed by calling `scorer.calculate_ensemble_score(...)`.
3. In `run_pipeline.py`, lines 2201-2202, `ensemble_df` is passed to `cov_analyzer.analyze_coverage(ensemble_df, prices_dict=infer_data_dict)`.
4. In `trading_system/src/analysis/coverage_analyzer.py`, lines 62-67:
```python
series = ensemble_df[c_col]
# Valid if non-null and finite
valid_mask = series.notna() & np.isfinite(series)
valid_cnt = int(valid_mask.sum())
```
5. Because `fillna(0.0)` was applied inside `calculate_ensemble_score()`, `series.notna()` evaluates to `True` for every single cell in `ensemble_df`, even for symbols where a strategy was not evaluated or failed. Thus `valid_cnt == total_symbols` (100.0% coverage).

---

### Finding 2: Per-Symbol Fundamental Missingness Check Flaw

#### Observation:
In `trading_system/src/analysis/coverage_analyzer.py`, lines 83-93:
```python
fund_cols = ['bps', 'roe', 'operating_margin', 'net_profit_margin']
has_fund = (features_df is not None and not features_df.empty and any(c in features_df.columns for c in fund_cols))

for sym in missing_syms:
    p_df = prices_dict.get(sym) if prices_dict else None
    if p_df is None or len(p_df) < 200:
        no_price_cnt += 1
    elif strat in ['rim_valuation', 'mq_factor'] and not has_fund:
        no_fund_cnt += 1
    else:
        other_cnt += 1
```

#### Logic Chain:
- `has_fund` evaluates whether the *DataFrame table* `features_df` has columns named `bps`, `roe`, etc.
- If `features_df` is passed to `analyze_coverage()` with these columns present, `has_fund` evaluates to `True` for every symbol.
- If symbol `A` is missing BPS/ROE data (e.g. `NaN` in `features_df.loc['A', 'bps']`), `has_fund` remains `True`. Therefore, `not has_fund` evaluates to `False`, and missingness for fundamental-dependent strategies (`rim_valuation`, `mq_factor`) is incorrectly classified as `STRATEGY_SIGNAL_NEUTRAL` instead of `NO_FUNDAMENTAL_DATA`.

---

### Finding 3: Formatting & Data Integrity of Report Artifacts

#### Output Files Inspected:
1. `trading_system/result/strategy_data_coverage_report.txt`
2. `trading_system/ensemble_predictions.txt`

#### Key Formatting Observations:
- **`strategy_data_coverage_report.txt`**:
  - Contains overall header and single summary table.
  - Lacks market-segmented breakdown (KOSPI, KOSDAQ, KONEX, SP500) within the report file.
  - Reports only the single `Primary Missing Reason` string per strategy instead of showing a frequency distribution (e.g. `INSUFFICIENT_PRICE_HISTORY: 45, NO_FUNDAMENTAL_DATA: 12`).
- **`ensemble_predictions.txt`**:
  - Global Macro section contains `nan` or erroneous default values when price DB queries fall back.
  - Recent pipeline updates in `run_pipeline.py` (lines 2264-2279) format all 14 strategy score columns in the Top 100 picks table. However, older generated output files on disk had only 4 strategy columns (`Reg`, `Surge`, `L-L`, `VCP`).

---

## 3. Automated Test Suite Audit (Pytest)

### Current Suite Architecture:
- Test files located in `trading_system/tests/` (55+ test files, 550+ test functions).
- Categories:
  - Unit tests for indicators, risk management, regime detection, HPO, portfolio sizing.
  - Core strategy tests (`test_new_5_strategies.py`, `test_rim_strategy.py`, `test_lead_lag_index.py`, `test_vcp_ml_predictor.py`, etc.).
  - Coverage & Report tests (`test_kst_and_coverage_reasoning.py`).

### Recorded Test Failures (`.pytest_cache/v/cache/lastfailed`):
Inspection of pytest's cache file `.pytest_cache/v/cache/lastfailed` revealed failures in the following suites from prior runs:
1. `tests/phase3/e2e/test_e2e.py::TestSentimentAnalysis`
2. `tests/phase3/e2e/test_e2e.py::TestRLTradingModel`
3. `tests/phase3/e2e/test_e2e.py::TestAssetAllocation`
4. `tests/phase3/e2e/test_e2e.py::TestPDFReport`
5. `tests/phase3/e2e/test_e2e.py::TestBrokerAPI`
6. `tests/phase3/e2e/test_e2e.py::TestSentimentAnalysisNegative`
7. `tests/phase3/e2e/test_e2e.py::TestRLTradingModelNegative`
8. `tests/phase3/e2e/test_e2e.py::TestAssetAllocationNegative`
9. `tests/phase3/e2e/test_e2e.py::TestPDFReportNegative`
10. `tests/phase3/e2e/test_e2e.py::TestBrokerAPINegative`
11. `tests/phase3/e2e/test_e2e.py::TestPairwiseInteraction`
12. `tests/phase3/e2e/test_e2e.py::TestRealWorldScenarios`
13. `tests/test_macro_stress.py::TestMacroStress::test_screener_predictions_identical`

### Coverage Gaps Relative to Requirement R3:
1. **No Pipeline-Ensemble Integration Coverage Test**: `test_strategy_coverage_analyzer` in `test_kst_and_coverage_reasoning.py` tests `analyze_coverage` using a mock DataFrame with literal `np.nan` values. Because it bypasses `EnsembleScoringEngine`, it fails to catch the `fillna(0.0)` bug.
2. **No Full Universe Data Coverage Test**: No automated test validates coverage ratios across all 3,379 symbols (KOSPI 898, KOSDAQ 1,684, KONEX 127, S&P 500 503).
3. **No Granular Missingness Reason Validation**: No test asserts the correctness of per-symbol missingness categorization (insufficient price history vs missing fundamental data vs missing option chain).

---

## 4. Proposed Code Fixes & Improvements

### Fix 1: Preserve Unfilled NaNs in `EnsembleScoringEngine` or Conduct Coverage Analysis Prior to `fillna(0.0)`

In `trading_system/src/ai/ensemble_scorer.py`:
Keep a clean copy of `merged` before applying `fillna(0.0)`, or return raw scores with NaNs when requested:

```python
# In calculate_ensemble_score:
merged['ensemble_score'] = (total_score_series / safe_weight_series).fillna(0.0).clip(0.0, 1.0)

# Store raw score copy before fillna for coverage analyzer
self.last_raw_merged_scores = merged.copy()
```

Alternatively, in `trading_system/run_pipeline.py`:
Pass raw strategy DataFrames or raw un-filled ensemble scores to `StrategyCoverageAnalyzer`:

```python
cov_data = cov_analyzer.analyze_coverage(
    ensemble_df,
    prices_dict=infer_data_dict,
    features_df=df_rim_input if 'df_rim_input' in locals() else None,
    treat_zero_as_missing_for_strats=['surge', 'vcp_rule', 'stat_arb'] # or use raw NaNs
)
```

### Fix 2: Enhance `StrategyCoverageAnalyzer` Per-Symbol Missingness Attribution

In `trading_system/src/analysis/coverage_analyzer.py`:
Check per-symbol fundamental missingness in `features_df`:

```python
# In analyze_coverage:
for sym in missing_syms:
    p_df = prices_dict.get(sym) if prices_dict else None
    if p_df is None or len(p_df) < 200:
        no_price_cnt += 1
    elif strat in ['rim_valuation', 'mq_factor']:
        # Check per-symbol fundamental validity
        if features_df is not None and sym in features_df.index:
            sym_fund = features_df.loc[sym]
            if sym_fund[['bps', 'roe']].isna().any():
                no_fund_cnt += 1
            else:
                other_cnt += 1
        else:
            no_fund_cnt += 1
    else:
        other_cnt += 1
```

### Fix 3: Add Comprehensive Integration Tests for R3

Create `trading_system/tests/test_r3_coverage_and_universe.py`:
1. `test_coverage_analyzer_with_ensemble_scorer_output()`: Runs `EnsembleScoringEngine.calculate_ensemble_score()` with partial strategy DataFrames and verifies `StrategyCoverageAnalyzer` correctly detects missing strategies (non-100% coverage).
2. `test_per_symbol_fundamental_missingness_reasons()`: Verifies that missing fundamental data for a specific symbol produces `NO_FUNDAMENTAL_DATA` reason.
3. `test_full_universe_symbol_coverage_report_generation()`: Verifies report generation across mock KOSPI/KOSDAQ/KONEX/SP500 symbols.

---

## 5. Summary Table of Audit Findings

| ID | Component | Issue Description | Severity | Impact |
|---|---|---|---|---|
| **BUG-01** | `ensemble_scorer.py` / `coverage_analyzer.py` | `calculate_ensemble_score()` converts NaNs to `0.0` before passing `ensemble_df` to `coverage_analyzer.py`, masking all missing data as 100% coverage. | **HIGH** | False coverage metrics in pipeline reports |
| **BUG-02** | `coverage_analyzer.py` | `has_fund` checks column existence in table rather than per-symbol values, failing to report missing fundamental data. | **MEDIUM** | Misclassified missingness reasons |
| **BUG-03** | `coverage_analyzer.py` | `generate_coverage_report()` only prints top primary reason string rather than reason counts/ratios. | **LOW** | Missing granular insight in text report |
| **GAP-01** | `tests/` | Unit tests for `coverage_analyzer` pass NaN DataFrames directly, missing the integration defect with `ensemble_scorer`. | **HIGH** | Test suite false positive |
| **GAP-02** | `tests/` | E2E tests in `test_e2e.py` and `test_macro_stress.py` have recorded failures in `.pytest_cache/v/cache/lastfailed`. | **MEDIUM** | Incomplete test suite pass |
