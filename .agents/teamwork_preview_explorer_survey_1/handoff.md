# Handoff Report — Dashboard HTML Generator & Strategy Data Parsing Survey

## 1. Observation

### 1.1 `generate_report.py` Strategy Discovery, Parsers, and Table Rendering Logic
- **Entry Point and File Loading** (`trading_system/generate_report.py:4779-4830`):
  - `generate_report.py` reads files from `--result-dir` (`trading_system/result/`) using helper `_read(path: Path)` (lines 262-272).
  - Main parser invocations:
    - Line 4795: `parse_ensemble(_read(result_dir / "ensemble_predictions.txt"))`
    - Line 4804: `parse_rim(_read(result_dir / "rim_predictions.txt"))`
    - Line 4816: `parse_sentiment(_read(result_dir / "sentiment_predictions.txt"))`
    - Line 4820: `parse_accruals_quality(_read(result_dir / "accruals_quality_predictions.txt"))`
    - Line 4822: `parse_valueup_catalyst(_read(result_dir / "valueup_catalyst_predictions.txt"))`
    - Line 4825: `parse_insider_buying(_read(result_dir / "insider_buying_predictions.txt"))`
    - Line 4828: `parse_earnings_tone_drift(_read(result_dir / "earnings_tone_drift_predictions.txt"))`
- **Generic Simple Strategy Parser** (`trading_system/generate_report.py:785-844`):
  - `_parse_simple_strategy(text, score_col)` parses lines formatted as `<rank> <symbol> <name> <market> <score>%`.
  - Splits each data line via `parts = line.split()`. If `parts[-2].upper() in KNOWN_MKTS`, extracts `market = parts[-2].upper()` and `name = " ".join(parts[2:-2])`.
  - If a file contains only headers or `Total symbols evaluated: 0` (no data rows starting with an integer rank), `_parse_simple_strategy` returns `(date, [])`.
- **RIM Valuation Parser** (`trading_system/generate_report.py:697-773`):
  - `parse_rim(text)` uses multi-tier regex matching:
    - 12-column format (`m12`, lines 712-738): `^(\d+)\s+(\S+)\s+(.+?)\s+(KOSPI|KOSDAQ|SP500|NASDAQ|RUSSELL2000|KONEX|[A-Za-z0-9_]+)\s+([-\d.]+|N/A|-|nan|NaN)\s+([-\d.]+|N/A|-|nan|NaN)\s+([-+\d.%]+|N/A|-|nan%|NaN%)\s+([-+\d.%]+|N/A|-|nan%|NaN%)\s+([-+\d.%]+|N/A|-|nan%|NaN%)\s+([-+\d.%]+|N/A|-|nan%|NaN%)(?:\s+(.*?))?\s+([-+\d.%]+|N/A|-|nan%|NaN%)$`
    - 9-column format (`m9`, lines 740-756): `Rank Symbol Name Market Price Intrinsic Discount EQ RIM_Score`
    - 8-column format (`m8`, lines 758-772): `Rank Symbol Name Market Price Intrinsic Discount RIM_Score`
- **Market Panels & Empty State Handling** (`trading_system/generate_report.py:2648-2775`):
  - `build_html` iterates over `active_markets_ordered` (`['KOSPI', 'KOSDAQ', 'SP500', 'NASDAQ', 'RUSSELL2000', ...]`).
  - For each market `mkt`, rows are filtered: `mkt_rows = [r for r in rows if r.market == mkt]`.
  - If `mkt_rows` is empty:
    ```python
    banner_html = build_tab_status_banner(strategy_name=st_name, market=mkt, status_type="empty", reason_code=missing_reason_code)
    rows_html = '<tr><td colspan="5" class="empty">데이터 없음</td></tr>'
    ```
- **Universal Cell Sanitizer** (`trading_system/generate_report.py:1252-1297`):
  - `format_metric_cell()` converts raw `"nan"`, `"NaN"`, `"none"`, `"undefined"`, `""`, `"-"` into `<span class="badge-na">N/A</span>`, preventing raw JavaScript undefined or literal NaN from appearing on the dashboard.

### 1.2 Upstream Pipeline File Generation & NaN Dropping
- In `trading_system/run_pipeline.py:2844-2878` (`_save_strategy_predictions_report`):
  ```python
  merged = df_strat.merge(universe[['symbol', 'name', 'market']], on='symbol', how='left') ...
  merged[score_col] = pd.to_numeric(merged[score_col], errors='coerce')
  merged = merged.dropna(subset=[score_col]).sort_values(by=score_col, ascending=False)
  ```
  - When all scores in `df_strat` are `np.nan` (due to missing fundamental cache, transcripts, or disclosures), `merged.dropna(subset=[score_col])` drops 100% of rows.
  - Line 2864 writes: `f_out.write(f"Total symbols evaluated: {len(df_sub)}\n\n")` -> `Total symbols evaluated: 0` with zero data rows.
- Current contents of files in `trading_system/result/`:
  - `sentiment_predictions.txt`: `Total symbols evaluated: 0` (0 data rows)
  - `earnings_tone_drift_predictions.txt`: `Total symbols evaluated: 0` (0 data rows)
  - `accruals_quality_predictions.txt`: `Total symbols evaluated: 0` (0 data rows)
  - `valueup_catalyst_predictions.txt`: `Total symbols evaluated: 0` (0 data rows)
  - `insider_buying_predictions.txt`: 100 data rows (1 KOSPI, 99 SP500, 0 KOSDAQ, 0 NASDAQ, 0 RUSSELL2000)
  - `rim_predictions.txt`: Prior to merge, contained only 1 KOSPI row (`057050`) with `nan` intrinsic values.

### 1.3 `merge_predictions.py` Multi-Market Synchronization
- `trading_system/merge_predictions.py:402-457` (`merge_generic_strategy_files`):
  - Merges `f"{stem}_{market}.txt"` from all target markets into unified `f"{filename}"`.
  - When all per-market files have 0 data rows, line 444 reports: `Only self-referencing fallbacks available; leaving {filename} untouched.`
- In `merge_ensemble_predictions` (lines 145-155):
  - Uses strict regex: `pattern = rf"(==={{10,}}\s*\n\[{re.escape(market)}\][^\n]*\n==={{10,}}\s*\n.*?)(?=\n==={{10,}}|\Z)"`.
  - In `ensemble_predictions_NASDAQ.txt` and `ensemble_predictions_RUSSELL2000.txt`, the internal table headers contained `[KOSPI]` and `[KOSDAQ]` instead of `[NASDAQ]` / `[RUSSELL2000]`, emitting warnings: `Could not extract section [NASDAQ]`.

---

## 2. Logic Chain

1. **[From Obs 1.1 & 1.2]** When `run_pipeline.py` executes strategies without external data feeds (DART API key absent, SEC transcripts unavailable, or fundamental DB cache unpopulated for certain markets), engines in `src/core/` (`llm_sentiment_engine.py`, `earnings_tone_drift.py`, `accruals_quality.py`, `valueup_catalyst.py`, `insider_buying.py`) assign `np.nan` to symbols without data.
2. **[From Obs 1.2]** In `_save_strategy_predictions_report()`, `merged.dropna(subset=[score_col])` removes all NaN rows. Consequently, `len(df_sub) == 0`, and the output text file contains only the header with `Total symbols evaluated: 0`.
3. **[From Obs 1.1]** When `generate_report.py` invokes `_parse_simple_strategy()` or `parse_rim()` on these 0-row files, the parser finds no data lines starting with an integer rank and returns an empty list `[]`.
4. **[From Obs 1.1]** In `build_html()`, `_build_simple_panels()` and `rim_panels` filter parsed rows by `row.market == mkt` for each of the 5 markets (`SP500`, `NASDAQ`, `RUSSELL2000`, `KOSPI`, `KOSDAQ`). Because the parsed list is empty (or only contains 1 market like SP500 for Insider Buying), `mkt_rows` evaluates to empty for all (or unrepresented) markets.
5. **[From Obs 1.1 & 1.3]** When `mkt_rows` is empty, `generate_report.py` renders `<tr><td colspan="5" class="empty">데이터 없음</td></tr>` along with the appropriate `strategy-status-banner` (`NO_CORPORATE_FILING`, `NO_FUNDAMENTAL_DATA`, etc.).
6. **[From Obs 1.3]** When `merge_predictions.py` runs across markets where per-market split files exist, `merge_generic_strategy_files()` merges non-empty files (e.g. `rim_predictions_*.txt`) into unified files with mixed column formats (12-col, 9-col, 8-col), which `parse_rim()` successfully parses and distributes to their respective market panels.

---

## 3. Caveats

- **No Caveats regarding HTML rendering**: `generate_report.py` executes without Python exceptions or JavaScript syntax errors.
- **Data Availability Constraint**: Strategies relying on fundamental accounting statements (Accruals, Value-Up, RIM) or regulatory text filings (Sentiment, Tone Drift, Insider Buying) require valid inputs in `market_indicators.db` / `infer_fund_cache` or price proxies to produce non-NaN scores. When offline/isolated, fallback proxy generation must be enabled to populate rows across all 5 markets.

---

## 4. Conclusion

The "데이터 없음" display across strategy tables for RIM, Sentiment, Tone Drift, Accruals Quality, Value-Up, and Insider Buying is caused by a two-stage cascade:
1. **Upstream Zero-Row Generation**: `run_pipeline.py:2859` drops all NaN scores before saving. In environments lacking external corporate filings / transcripts / fundamental databases, the calculated scores default to `np.nan`, producing files with `Total symbols evaluated: 0`.
2. **Strict Parser & Market Separation**: `generate_report.py` strictly categorizes rows by `market`. If a market has no rows in the parsed strategy file, that market's panel correctly shows "데이터 없음".

### Key Recommendations:
1. **Pipeline Fallback & Default Score Handling**:
   - In `llm_sentiment_engine.py`, `earnings_tone_drift.py`, `accruals_quality.py`, `valueup_catalyst.py`, and `insider_buying.py`, ensure quantitative proxy fallbacks (e.g. price-trend proxy, neutral 0.50 prior with neutral confidence) are calculated whenever external filings are absent, so that valid ranking rows are always produced for all 5 markets.
   - In `_save_strategy_predictions_report()`, ensure that when `df_strat` is empty or all-NaN, a calibrated neutral baseline (e.g. 50.0% ranking) or informative placeholder entries with explicit tags are provided instead of writing an empty 0-row table.
2. **Multi-Market Merge Verification**:
   - In `merge_predictions.py`, ensure `merge_ensemble_predictions()` handles flexible market header variations across all 5 markets (`SP500`, `NASDAQ`, `RUSSELL2000`, `KOSPI`, `KOSDAQ`) without failing on section extractions.
3. **HTML Generator Enhancements**:
   - Ensure `parse_rim()` continues supporting mixed 12-column, 9-column, and 8-column formats across merged multi-market files.
   - Maintain `format_metric_cell()` sanitization so that raw `nan` strings are cleanly rendered as `<span class="badge-na">N/A</span>`.

---

## 5. Verification Method

### 5.1 Command Line Verifications
Run the HTML report generator and verify successful build and file size:
```bash
.venv\Scripts\python.exe trading_system/generate_report.py --result-dir trading_system/result --out gh-pages/index.html
```
- Assert process exits with returncode `0`.
- Assert `gh-pages/index.html` exists and size is > 1.5 MB.

### 5.2 Unit & Regression Test Verification
Run the report generator test suite:
```bash
.venv\Scripts\python.exe -m pytest tests/test_report_generator_hrp.py tests/test_report_ux_and_rounding.py -v
```
- All 23 tests in `test_report_generator_hrp.py` and `test_report_ux_and_rounding.py` must pass with 100% success rate.
