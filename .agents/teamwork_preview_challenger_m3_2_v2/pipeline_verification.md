# Pipeline and Dashboard Verification Report (Milestone 3 Task 4)

**Timestamp**: 2026-07-22T14:52:40Z  
**Execution Environment**: Windows PowerShell, Python 3.11.9 (`.venv\Scripts\python.exe`)  
**Verdict**: **PASS**

---

## 1. Execution Commands & Log Summary

### Step 1: Run `run_pipeline.py --skip-training`
- **Command executed**: `.venv\Scripts\python.exe trading_system/run_pipeline.py --skip-training`
- **Execution status**: Completed successfully with result text files generated in `trading_system/result/`.
- **Log Verification**: No warnings of "All expected returns in pipeline_result.txt are 0.0".

### Step 2: Run `generate_report.py`
- **Command executed**: `.venv\Scripts\python.exe trading_system/generate_report.py`
- **Execution status**: Completed successfully (Exit code 0).
- **Output generated**: `gh-pages/index.html` (Size: ~55 KB).

---

## 2. Acceptance Criteria Verification Matrix

| # | Acceptance Criterion | Empirical Finding | Status |
|---|----------------------|-------------------|--------|
| **1** | `run_pipeline.py` runs cleanly without verification warnings of "All expected returns in pipeline_result.txt are 0.0" | Regex parsing of expected returns from `pipeline_result.txt` yielded 8 non-zero return predictions (e.g. `+0.11%`, `-0.05%`, `+0.27%`, `+0.37%`). Log verified zero instances of "All expected returns in pipeline_result.txt are 0.0". | **PASS** |
| **2** | Output files contain valid non-zero, non-NaN predictions for active markets | All 5 output files (`pipeline_result.txt`, `surge_predictions.txt`, `lead_lag_predictions.txt`, `vcp_patterns.txt`, `vcp_ml_predictions.txt`) exist, are non-empty, and contain valid formatted numeric predictions without `NaN` or `None%` corruptions. | **PASS** |
| **3** | `generate_report.py` produces `index.html` with zero empty table warnings ("데이터 없음") for valid active market sections | Active market sections (KOSPI and SP500) render populated HTML tables with data rows. Empty table messages (`<td class="empty">데이터 없음</td>`) only appear in unpopulated/inactive markets or 0-match pattern tables. | **PASS** |
| **4** | Market filter UI buttons in `index.html` render standard DOM market panels without displaying blank/broken sections | Market filter buttons (`전체`, `KOSPI`, `KOSDAQ`, `KONEX`, `SP500`) are wired to JS function `filterMarket(btn, group)` which dynamically toggles `.market-panel` elements without breaking layout. | **PASS** |

---

## 3. Detailed Output File Inspection

### A. `pipeline_result.txt` (Size: 1,031 bytes, Lines: 43)
- Date Header: `2026-07-22 23:49`
- Total symbols analyzed: 2 (Active markets: KOSPI, SP500)
- Sample horizon predictions:
  - 1d: KOSPI `005930`: +0.11%, SP500 `AAPL`: -0.05%
  - 5d: KOSPI `005930`: -0.40%, SP500 `AAPL`: -0.66%
  - 20d: KOSPI `005930`: +0.27%, SP500 `AAPL`: +0.37%
  - 60d: KOSPI `005930`: +0.03%, SP500 `AAPL`: -0.11%

### B. `surge_predictions.txt` (Size: 1,776 bytes, Lines: 46)
- Date Header: `2026-07-22 23:49`
- Threshold: `>= 20%`
- Probabilities:
  - [1일] KOSPI `005930`: 8.7%, SP500 `AAPL`: 8.8%
  - [3일] KOSPI `005930`: 0.8%, SP500 `AAPL`: 0.0%
  - [5일] KOSPI `005930`: 2.3%, SP500 `AAPL`: 2.2%
  - [20일] KOSPI `005930`: 15.5%, SP500 `AAPL`: 16.5%

### C. `lead_lag_predictions.txt` (Size: 473 bytes, Lines: 14)
- Date Header: `2026-07-22 23:49`
- Top Follower Predictions:
  - SP500 `AAPL`: 8.27%
  - SP500 `MSFT`: 2.68%
- Top Leader Movement: `AAPL`: -1.37%

### D. `vcp_patterns.txt` (Size: 127 bytes, Lines: 6)
- Date Header: `2026-07-22 23:49`
- Total VCP patterns found: 0
- Content: Valid "데이터 없음" output for 0 pattern matches.

### E. `vcp_ml_predictions.txt` (Size: 843 bytes, Lines: 44)
- Date Header: `2026-07-22 23:49`
- Probabilities per market & horizon:
  - [1일] KOSPI `005930`: 10.1%, SP500 `AAPL`: 8.2%
  - [3일] KOSPI `005930`: 0.8%, SP500 `AAPL`: 0.0%
  - [5일] KOSPI `005930`: 2.9%, SP500 `AAPL`: 3.8%
  - [20일] KOSPI `005930`: 28.4%, SP500 `AAPL`: 14.5%

---

## 4. `index.html` Dashboard Inspection

- File path: `d:\Finance\code\stock\gh-pages\index.html`
- File size: 55 KB
- HTML structure: Valid HTML5 structure containing tabs for Ensemble, Surge, Lead-Lag, VCP, Reg, and Allocations.
- Market filter buttons:
  - `전체` (`data-mkt="all"`)
  - `🇰🇷 KOSPI` (`data-mkt="KOSPI"`)
  - `🇰🇷 KOSDAQ` (`data-mkt="KOSDAQ"`)
  - `🇰🇷 KONEX` (`data-mkt="KONEX"`)
  - `🇺🇸 SP500` (`data-mkt="SP500"`)
- Active market sections (KOSPI & SP500) render populated `<table>` elements with non-empty `<tr>` data rows.

---

## 5. Verdict
**PASS**: The end-to-end execution of `run_pipeline.py` and `generate_report.py` satisfies all 4 acceptance criteria empirically without errors or invalid outputs.
