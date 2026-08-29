# Implementation Plan — Data Integrity, RIM Engine Fix & Dashboard Health Monitor

## Overview
Address all requirements from the latest user request (2026-08-29T07:46:48Z) in ORIGINAL_REQUEST.md:
1. R1: 31-Strategy Pipeline Data Quality & Normalization Audit
2. R2: RIM Valuation Engine Fix & Missing Metric Handling
3. R3: GitHub Pages Dashboard Missingness & Health Status Display
4. Verification: 100% test pass rate on `tests/`, clean non-NaN pipeline & report outputs across all 5 markets.

## Execution Steps

### Phase 0: Survey & Codebase Mapping
- Explorer 1: Inspect `trading_system/src/core/rim_valuation.py`, its unit tests in `tests/`, and callers in `run_pipeline.py`. Identify how `nan` / `nan%` arises and how missing BPS/ROE/equity are currently handled.
- Explorer 2: Inspect all 31 strategy modules in `trading_system/src/core/` and `trading_system/src/ai/`, checking data generation, fallback/missingness handling, and missingness reason code reporting in `src/analysis/coverage_analyzer.py` and `strategy_data_coverage_report.txt`.
- Explorer 3: Inspect `trading_system/generate_report.py`, `gh-pages/index.html`, and CSS/JS templates for table rendering, NaN/None handling, Strategy Data Status Summary Card / Health Monitor, and missingness warning banners per tab.

### Phase 1 (Milestone 1): RIM Valuation Engine Fix & NaN Removal
- Fix `rim_valuation.py` so uncomputable intrinsic values (negative equity, missing BPS, invalid divisors) are excluded from ranking or assigned explicit neutral fallback status (e.g. `재무데이터미비`, `자본잠식/적자`), with zero `nan` or `nan%` string output.
- Update/add unit tests in `tests/test_rim_valuation.py` (or relevant test files).
- Verification via Reviewers, Challengers, and Forensic Auditor.

### Phase 2 (Milestone 2): 31-Strategy Pipeline Data Quality & Normalization Audit
- Ensure all 31 strategies across SP500, NASDAQ, RUSSELL2000, KOSPI, KOSDAQ execute reliably without uncaught exceptions or raw `nan` propagation.
- Ensure fallback imputation and explicit missingness reasons are consistently assigned in `coverage_analyzer.py` and output reports.
- Verify with Reviewers, Challengers, and Forensic Auditor.

### Phase 3 (Milestone 3): GitHub Pages Dashboard Missingness & Health Status Display
- Enhance `trading_system/generate_report.py` to add Strategy Data Status Summary Card / Health Monitor at dashboard top.
- Replace any raw `nan`/`None`/`undefined` in tables with clean badges (`<span class="badge-na">N/A</span>` / `데이터 수집필요`).
- Add warning/notice banners in tabs with 0 or incomplete data.
- Verify generated HTML.

### Phase 4 (Milestone 4): End-to-End Regression Verification & Final Deliverables
- Run all tests in `tests/` (`.venv/Scripts/pytest tests/ -v`).
- Execute E2E report generation and verify generated output files in `trading_system/result/`.
- Prepare final report and handoff to parent.
