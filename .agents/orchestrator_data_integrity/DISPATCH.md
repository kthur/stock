## 2026-08-28T22:47:21Z

You are the Project Orchestrator for the stock trading system data integrity, RIM engine fix, and dashboard health monitor task.

## Your Identity & Workspace
- Working directory: d:\Finance\code\stock\.agents\orchestrator_data_integrity
- Project root: d:\Finance\code\stock
- Authoritative User Request: d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md
- Python interpreter: .venv\Scripts\python.exe (or .venv\Scripts\pytest)

## Objective & Requirements
Fulfill all requirements outlined in the latest section of `ORIGINAL_REQUEST.md`:

### R1. 31-Strategy Pipeline Data Quality & Normalization Audit
- Inspect data generation for all 31 strategies across all 5 markets (SP500, NASDAQ, RUSSELL2000, KOSPI, KOSDAQ).
- Ensure that every strategy pipeline step (`run_pipeline.py`, core engine modules) executes reliably and produces valid output without unhandled exceptions, raw `nan` values, or data pipeline drops.
- When input data (e.g. order flow, options skew, fundamentals) is absent for certain tickers or markets, apply consistent neutral/fallback imputation and assign explicit missingness reason codes.

### R2. RIM Valuation Engine Fix & Missing Metric Handling
- Resolve `NaN` output in `trading_system/src/core/rim_valuation.py` and output reports (`rim_predictions.txt`):
  - Fix calculations where missing BPS, non-positive equity, or zero/negative divisor produces `nan` or `inf`.
  - Distinguish between valid valuations, filtered value traps, and missing fundamental data.
  - Exclude tickers with uncomputable intrinsic values from ranking or assign neutral scores with explicit status tags (e.g. `재무데이터미비`).
  - Eliminate any string output of `nan` or `nan%` in output text files.

### R3. GitHub Pages Dashboard Missingness & Health Status Display
- Enhance `trading_system/generate_report.py` and GitHub Pages (`gh-pages/index.html`):
  - Add a Strategy Data Status Summary Card / Health Monitor at the top of the dashboard showing coverage/validity rate for each strategy.
  - Replace any raw `nan` or `None` table cells across all tabs with user-friendly badges (e.g. `<span class="badge-na">N/A</span>` or `데이터 수집필요`).
  - If a strategy or market has 0 or incomplete data, display a clear warning/notice banner within that strategy tab explaining the status.

### Acceptance Criteria
- Running pipeline or strategy test suites across all 5 markets generates clean, non-empty, non-`nan` output files in `trading_system/result/`.
- RIM predictions for all markets contain valid numeric values, proper formatting, and explicit filter/status reasons without `nan` or `nan%`.
- `strategy_data_coverage_report.txt` correctly reports coverage and missingness reasons for all 31 strategies.
- GitHub Pages report generated via `generate_report.py` contains no raw `nan` or `undefined` text.
- Visual status badges/health summary cards are rendered indicating strategy data availability.
- Strategy tabs display clear visual indicators when data is missing or in fallback mode.
- All automated unit tests in `tests/` pass with 0 failures (`.venv/Scripts/pytest tests/ -v`).
- End-to-end report generation executes cleanly without runtime errors.
