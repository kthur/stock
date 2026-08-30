# BRIEFING — 2026-08-29T13:33:00Z

## Mission
Investigate dashboard HTML generator (`generate_report.py`) and strategy data parsing logic, focusing on why strategy tables (RIM, Sentiment, Tone Drift, Accruals Quality, Value-Up, Insider Buying, etc.) fail to parse or display "데이터 없음" across the 5 markets.

## 🔒 My Identity
- Archetype: explorer
- Roles: investigation, analysis, synthesis
- Working directory: d:\Finance\code\stock\.agents\teamwork_preview_explorer_survey_1
- Original parent: 4a57e5b5-0c64-4358-b369-c7c1f1986502
- Milestone: survey_1

## 🔒 Key Constraints
- Read-only investigation — do NOT implement changes to source code outside .agents
- Investigate files, line numbers, exact parsing issues, schema mismatches, and provide actionable recommendations.

## Current Parent
- Conversation ID: 4a57e5b5-0c64-4358-b369-c7c1f1986502
- Updated: 2026-08-29T13:33:00Z

## Investigation State
- **Explored paths**:
  - `trading_system/generate_report.py` (lines 1-5099, parsers, `build_html`, `_parse_simple_strategy`, `parse_rim`, `format_metric_cell`, `_build_simple_panels`, `build_tab_status_banner`, JavaScript logic)
  - `trading_system/merge_predictions.py` (merging logic, `merge_generic_strategy_files`, `merge_ensemble_predictions`, section regex extraction)
  - `trading_system/run_pipeline.py` (strategy computation calls, `df_rim_input` generation, `_save_strategy_predictions_report`, NaN dropping behavior)
  - Strategy engines: `src/core/llm_sentiment_engine.py`, `src/core/earnings_tone_drift.py`, `src/core/accruals_quality.py`, `src/core/valueup_catalyst.py`, `src/core/insider_buying.py`, `src/core/rim_valuation.py`
  - Result files in `trading_system/result/` (`rim_predictions.txt`, `sentiment_predictions.txt`, `earnings_tone_drift_predictions.txt`, `accruals_quality_predictions.txt`, `valueup_catalyst_predictions.txt`, `insider_buying_predictions.txt`, `ensemble_predictions.txt`)
  - Tests: `tests/test_report_generator_hrp.py`, `tests/test_report_ux_and_rounding.py`
- **Key findings**:
  1. `generate_report.py`'s table rendering correctly groups rows by `row.market` matching `active_markets_ordered`. When rows for a market exist, interactive tables with links and formatted cells render cleanly.
  2. When strategy output files contain 0 data rows (e.g. `Total symbols evaluated: 0`), `_parse_simple_strategy` returns `[]`, and `generate_report.py` renders `<tr><td colspan="5" class="empty">데이터 없음</td></tr>` alongside a warning banner with reason codes (`NO_CORPORATE_FILING`, `NO_FUNDAMENTAL_DATA`, `NO_INSIDER_FILING`, `NO_EARNINGS_TRANSCRIPT`).
  3. The root cause for empty strategy files in `trading_system/result/` is upstream data missingness in `run_pipeline.py`: when external disclosure/fundamental data is absent and proxy fallbacks are not populated, strategy engines produce `np.nan` scores for all symbols. In `run_pipeline.py:2859`, `merged.dropna(subset=[score_col])` drops all rows before saving, creating files with 0 symbols.
  4. In `merge_predictions.py`, `merge_ensemble_predictions()` relies on a strict header pattern `rf"(==={{10,}}\s*\n\[{re.escape(market)}\][^\n]*\n==={{10,}}\s*\n.*?)(?=\n==={{10,}}|\Z)"`. If single-market runs produce mismatched headers (e.g. `[KOSPI]` and `[KOSDAQ]` in `ensemble_predictions_NASDAQ.txt`), section extraction fails, leaving those markets out of `ensemble_predictions.txt` and lowering market coverage in the dashboard.
- **Unexplored areas**: None for survey scope.

## Key Decisions Made
- Fully documented all 5 focus areas with exact code locations, regex behavior, failure modes, and systematic recommendations.

## Artifact Index
- `d:\Finance\code\stock\.agents\teamwork_preview_explorer_survey_1\handoff.md` — Final 5-component report
- `d:\Finance\code\stock\.agents\teamwork_preview_explorer_survey_1\progress.md` — Progress tracker
