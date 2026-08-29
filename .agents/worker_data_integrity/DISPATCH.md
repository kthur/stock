## 2026-08-29T07:53:00Z

You are a Worker implementing the Data Integrity, RIM Valuation Engine Fix, and Dashboard Health Monitor requirements.

DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Authoritative Inputs
Read:
1. `ORIGINAL_REQUEST.md` at `d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md` (specifically requirements R1, R2, R3).
2. Explorer handoff reports:
   - `d:\Finance\code\stock\.agents\explorer_survey_rim\handoff.md`
   - `d:\Finance\code\stock\.agents\explorer_survey_pipeline\handoff.md`
   - `d:\Finance\code\stock\.agents\explorer_survey_dashboard\handoff.md`

## Concrete Tasks to Implement

### 1. RIM Valuation Engine Fix (`trading_system/src/core/rim_valuation.py`)
- Explicit filter reason tagging in `compute_rim_scores`:
  - Tag `MISSING_FUNDAMENTALS` when BPS / book value is missing or NaN.
  - Tag `CAPITAL_IMPAIRMENT` when equity is non-positive (`bps <= 0` or `book_value <= 0`).
  - Do NOT default ROE to 8.0% or EQ to 1.0 when fundamentals are missing (leave raw values as NaN).
  - Invalidate scores (`rim_score`, `discount_ratio`, `intrinsic_value` -> `np.nan`) for invalid filter reasons (`MISSING_FUNDAMENTALS`, `CAPITAL_IMPAIRMENT`, `LOW_EARNINGS_QUALITY`, `PREFERRED_SHARE`, `OPERATING_LOSS`).

### 2. Pipeline Prediction Output Formatting (`trading_system/run_pipeline.py`)
- In `_write_rim_file`:
  - Filter `valid_rim = df_rim[df_rim['rim_score'].notna() & (df_rim['rim_score'] > 0)]`.
  - If `valid_rim.empty`, write `"데이터 없음 (유효한 RIM 적정가 산출 대상 종목 없음)"` and return.
  - Replace all hardcoded `"nan%"`, `"   nan%"`, and `"nan"` strings with `"N/A"` or explicit tags.
  - Check `np.isfinite()` for all numeric columns before formatting.
- Ensure all other 31 strategy file writers similarly format valid numeric values and do not output raw `"nan%"` strings.

### 3. Strategy Column Alignment (`trading_system/src/ai/ml_strategy_adapters.py`)
- Update `StrategyMeta` for `vcp_rule` so `score_column="vcp_rule_score"` matches `EnsembleScoringEngine`.

### 4. Coverage Analyzer Symbol Normalization & Reasons (`trading_system/src/analysis/coverage_analyzer.py`)
- In `analyze_coverage` and `_has_symbol_fundamental_data`:
  - Strip market suffixes (e.g. `.KS`, `.KQ`) from symbol strings when matching against `prices_dict` and `features_df`.
  - Handle `zfill(6)` for numeric KRX symbols so dictionary lookups succeed.
  - Refine missingness reasons with granular categories (`NO_CORPORATE_FILING`, `NO_INSIDER_FILING`, `NO_EARNINGS_TRANSCRIPT`, `NO_LEAD_LAG_LEADER`, `NO_SUPPLY_CHAIN_MAPPING`, `NO_FUNDAMENTAL_DATA`, `LOW_EARNINGS_QUALITY`, `NO_OPTIONS_CHAIN`, `NON_US_MARKET_SCOPE`, `NO_COINTEGRATED_PAIR`, `INSUFFICIENT_PRICE_HISTORY`, `STRATEGY_SIGNAL_NEUTRAL`).

### 5. Dashboard Health Monitor & NaN-Free Tables (`trading_system/generate_report.py`)
- Update `parse_rim` regex to support `N/A`, `-`, and valid numbers across price, intrinsic value, discount, ROE, EQ, and score columns.
- Add `StrategyHealthInfo` data model and `parse_strategy_coverage_report()` to parse `strategy_data_coverage_report.txt` (with dynamic fallback if file not yet generated).
- Add `build_strategy_health_monitor_html()` rendering hero card with summary pills, 31 strategy health cards with progress bars and status badges, and interactive click-to-tab navigation.
- Add `format_metric_cell()` and `build_tab_status_banner()`.
- Inject the Strategy Data Health Monitor into the dashboard HTML above the main tabs.
- Replace raw `nan` / `None` / `undefined` across all tables, drawer, and macro strip with styled badges (`.badge-na`, `.badge-need-data`, `.badge-filtered`, `.badge-fallback`, `.badge-healthy`, `.badge-partial`).
- Add tab-level notice / warning banners for empty / partial strategy tabs.
- Add JavaScript for `switchTabById` and safe stock drawer formatting.

### 6. Build, Tests & Verification
- Run `.venv\Scripts\pytest tests/ -v` to ensure all tests pass 100% (0 failures, 0 errors).
- If any test cases need updating or new test cases are needed for RIM missingness, coverage reasons, or report generation, update/add tests in `tests/`.
- Test running `generate_report.py` to confirm clean HTML generation without exceptions.
