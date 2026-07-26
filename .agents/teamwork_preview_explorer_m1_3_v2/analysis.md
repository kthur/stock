# Pipeline Execution & Report Assembly Integrity Audit Report

**Audit Target**: `trading_system/run_pipeline.py`, `trading_system/generate_report.py`, `trading_system/src/persistence/database.py`, `trading_system/src/data_layer/indicator_storage.py`, `trading_system/src/ai/prediction_model.py`, and output text formatters.
**Auditor**: Exploration Specialist (Milestone 1, Task 3)
**Date**: 2026-07-21

---

## Executive Summary

A comprehensive, read-only audit of the prediction pipeline, database persistence layer, text output formatters, and HTML report assembly in the Stock Trading System was conducted.

Four major categories of integrity failures were identified and traced to exact code mechanisms and line numbers:
1. **Zero Expected Returns (0.0%) & Verification Failures**: Missing pre-trained models during `SKIP_TRAINING` runs, model loading key mismatches, or zero volatility scaling (`vol_20d`) cause `_predict_regression` to output default `0.0` for all symbols, triggering verification warnings in `run_pipeline.py`.
2. **Parser & Text Formatter Breakdown**:
   - Stock names containing parentheses (e.g. `Alphabet Inc. (Class A)`) break non-greedy regex matches (`\((.+?)\):`) across ALL parsers in `generate_report.py`.
   - Internal double spaces in stock names break `parse_ensemble` regex (`(.+?)\s{2,}`).
   - Header string mismatches (`[1일] KOSPI - (no symbols)`) break `parse_vcp_ml`.
3. **HTML Warning Blocks ("데이터 없음") for Active Markets**:
   - Single-market or partial pipeline executions (`INFERENCE_TARGET`) skip writing empty markets to text files.
   - `build_html` in `generate_report.py` either renders explicit `"데이터 없음"` rows or fails to create DOM market panels, causing missing market filter views.
4. **Data Flow & Persistence Decoupling**:
   - `generate_report.py` reads exclusively from static text files in `result/` and lacks any fallback to SQLite DB persistence.
   - SQLite DB (`MarketIndicatorStorage`) only stores regression (`ai_predictions`) and ensemble (`ensemble_predictions`), completely dropping `surge_df`, `vcp_results`, `lead_lag_df`, and `vcp_ml_df`.

---

## Detailed Root Cause Analysis

### Question 1: Root causes why `run_pipeline.py` outputs verification warnings ("All expected returns in pipeline_result.txt are 0.0")

#### Finding 1.1: Missing Model Fallback to Default 0.0
- **Location**: `trading_system/src/ai/prediction_model.py`, lines 1938 & 2044; `trading_system/run_pipeline.py`, lines 733-753, 1085-1093, 1572-1589.
- **Observation**:
  In `_predict_regression()` (lines 1937–2045):
  ```python
  res_df[h] = 0.0
  ...
  if preds:
      ...
      res_df.loc[idx, h] = blend_pred_inv
  else:
      res_df.loc[idx, h] = 0.0
      logger.warning(f"Regression prediction for market={mkt}, horizon={h} defaulted to 0.0 due to missing models.")
  ```
  When `--skip-training` is used or when pre-trained model files are missing from disk (`trading_system/models/*.json`), model loading yields `xgb_m is None`, `lgb_m is None`, `cat_m is None`, `lstm_m is None`. `preds` is empty, so `res_df` defaults to `0.0`.
- **Formatting Impact**:
  In `run_pipeline.py` lines 1225 & 1233:
  `f.write(f"  {rank}. {row['symbol']} ({name}): {row[h]*100:+.2f}%\n")`
  All rows write `+0.00%`.
- **Verification Trigger**:
  In `run_pipeline.py` lines 1577–1585:
  ```python
  returns = re.findall(r'\):\s*([+-]?\d+\.\d+)%', content)
  if returns:
      all_zero = all(float(r) == 0.0 for r in returns)
      if all_zero:
          logger.warning("Verification failed: All expected returns in pipeline_result.txt are 0.0.")
  ```
  Since all parsed returns are `0.0`, the pipeline logs a verification failure.

#### Finding 1.2: Volatility Scale Multiplier Zeroing (`vol_20d`)
- **Location**: `trading_system/src/ai/prediction_model.py`, lines 2035–2042 & `trading_system/src/ai/target_transform.py`, lines 28–46.
- **Observation**:
  In `_predict_regression()`:
  ```python
  if 'vol_20d' in X_mkt_raw.columns:
      vol_scale = X_mkt_raw['vol_20d'].reset_index(drop=True)
  blend_pred_inv = inverse_transform_sharpe(pd.Series(blend_pred), vol_scale).values
  ```
  In `inverse_transform_sharpe`: `raw_ret = sharpe * vol_scale.values`.
  If `vol_20d` is 0.0 (e.g. halted/flat stocks) or NaN, the raw return calculation multiplies prediction by 0.0 or NaN, resulting in 0.0% or NaN predictions.

---

### Question 2: Root causes why text file formatters or DB saving logic write empty tables, 0.0 returns, or NaN predictions

#### Finding 2.1: Regex Parser Destruction by Parentheses in Stock Names
- **Location**: `trading_system/generate_report.py`, lines 205, 231, 278, 290, 317, 353.
- **Observation**:
  Every parser function in `generate_report.py` uses non-greedy regex matching with `\((.+?)\)` to extract stock names:
  - `parse_surge`: `r"(\d+)\.\s+\[(\w+)\]\s+(\S+)\s+\((.+?)\):\s*([-\d.]+|nan|NaN|None)%"`
  - `parse_vcp`: `r"(\d+)\.\s+\[(\w+)\]\s+(\S+)\s+\((.+?)\)"`
  - `parse_lead_lag`: `r"(\d+)\.\s+\[(\w+)\]\s+(\S+)\s+\((.+?)\):\s*([-+]?(?:[\d.]+|nan|NaN|None)\s*%)"`
  - `parse_vcp_ml`: `r"(\d+)\.\s+\[(\w+)\]\s+(\S+)\s+\((.+?)\):\s*([-\d.]+|nan|NaN|None)%"`
  - `parse_regression`: `r"(\d+)\.\s+(\S+)\s+\((.+?)\):\s*([-+]?(?:[\d.]+|nan|NaN|None)%)"`
- **Failure Mechanism**:
  When a stock name contains internal parentheses (e.g., `Alphabet Inc. (Class A)`, `Berkshire Hathaway (Class B)`, `삼성스팩6호(합병)`), the non-greedy `\((.+?)\)` matches up to the FIRST closing parenthesis `)`. The remainder of the line retains trailing parentheses and colons (e.g., `): 15.2%`), causing the regex match against the rest of the pattern to fail. The line is silently skipped, resulting in truncated or empty table rows.

#### Finding 2.2: Internal Double Space Breakdown in `parse_ensemble`
- **Location**: `trading_system/generate_report.py`, line 166.
- **Observation**:
  `parse_ensemble` uses `r"(\d+)\s+(\S+)\s+(.+?)\s{2,}([-\d.]+%|nan%|NaN%|None%)..."` to parse `ensemble_predictions.txt`.
  If a stock name contains two consecutive internal spaces (e.g. `"POWER  TECH"`), non-greedy `(.+?)` terminates at the internal double space. `\s{2,}` consumes the double space inside the name, and the subsequent numerical group attempts to match the remaining text (`"TECH"`), failing the regex.

#### Finding 2.3: Header Pattern Mismatch for Empty VCP ML Sections
- **Location**: `trading_system/run_pipeline.py`, line 1428; `trading_system/generate_report.py`, line 311.
- **Observation**:
  When a market has no VCP ML predictions, `run_pipeline.py` writes:
  `[1일] KOSPI - (no symbols)`
  `parse_vcp_ml` in `generate_report.py` line 311 looks for:
  `r"\[(\d+일)\]\s+(\w+)\s+(TOP|Top)"`
  Because `(no symbols)` does not match `(TOP|Top)`, the section is ignored, preventing the creation of market metadata objects.

---

### Question 3: Root causes why `generate_report.py` renders HTML sections with warning blocks stating "데이터 없음" for active markets

#### Finding 3.1: Single-Market Pipeline Execution (`INFERENCE_TARGET`)
- **Location**: `trading_system/run_pipeline.py`, lines 960–976; `trading_system/generate_report.py`, lines 414–449, 473–503, 513–550, 558–582.
- **Observation**:
  When `run_pipeline.py` is invoked with `--target KOSPI` or `INFERENCE_TARGET=KOSPI`, only `KOSPI` symbols are analyzed.
  The pipeline text formatters skip writing blocks for empty markets (`KOSDAQ`, `KONEX`, `SP500`).

#### Finding 3.2: Asymmetric Market Panel Construction in HTML Generator
- **Location**: `trading_system/generate_report.py`, lines 414-450 vs 473-506 vs 663-702.
- **Observation**:
  - In **Ensemble**, **VCP**, and **Lead-Lag** tabs, `build_html` explicitly iterates over `["KOSPI", "KOSDAQ", "KONEX", "SP500"]`. If a market has no parsed data, it generates a panel containing:
    `<tr><td colspan="..." class="empty">데이터 없음</td></tr>`
  - In **Surge**, **VCP ML**, and **Regression** tabs, `build_html` ONLY creates market panels for sections that were present in the parsed text files. If `KOSDAQ`, `KONEX`, or `SP500` were omitted from text files, NO DOM elements are rendered for those markets.
  - When the user clicks the market filter buttons (`KOSDAQ`, `KONEX`, `SP500`) on Surge/VCP ML/Regression tabs, `filterMarket(this, group)` searches for `.market-panel` elements matching `data-market="KOSDAQ"`. Since none exist, the UI displays an empty, blank section without error feedback.

---

### Question 4: Root causes why data flow breaks or loses prediction rows across Model Prediction -> Text Output -> DB Persistence -> `generate_report.py`

#### Finding 4.1: Database Persistence Bypass & Unidirectional Reliance on Text Files
- **Location**: `trading_system/generate_report.py`, lines 960–988; `trading_system/src/data_layer/indicator_storage.py`, lines 271–289 & 451–474.
- **Observation**:
  - `generate_report.py` relies 100% on reading raw text files from `trading_system/result/`. It has zero integration with `MarketIndicatorStorage` or SQLite DB.
  - `run_pipeline.py` saves `res_df` to `ai_predictions` table and `ensemble_df` to `ensemble_predictions` table, but COMPLETELY DISCARDS `surge_df`, `vcp_results`, `lead_lag_df`, and `vcp_ml_df` (they are never persisted to SQLite).
  - If a text file is truncated, missing, or fails regex parsing, `generate_report.py` cannot recover predictions from the database.

#### Finding 4.2: Data Format Disconnect Between DB and Text Summaries
- **Location**: `trading_system/src/data_layer/indicator_storage.py`, lines 275–280; `trading_system/run_pipeline.py`, lines 1204–1235.
- **Observation**:
  `save_predictions` stores `ai_predictions` in long format (`date, symbol, horizon, expected_return`).
  `pipeline_result.txt` is written as a human-readable top-20 summary filtered to key horizons (`1d`, `5d`, `20d`, `60d`).
  Because `generate_report.py` expects formatted text strings rather than querying the database schema directly, any mismatch between file writing and parsing breaks report assembly.

---

## Summary Table of Issues & Root Cause Mapping

| Strategy / Component | Problem Observed | Exact File Path & Lines | Underlying Root Cause Mechanism |
|---|---|---|---|
| **Regression (All)** | 0.0% predictions & verification warning | `run_pipeline.py:1577-1585`, `prediction_model.py:1938,2044` | Missing pre-trained models default to 0.0; post-pipeline verification regex flags all-zero returns |
| **Ensemble** | Row skipping / "데이터 없음" | `generate_report.py:166`, `run_pipeline.py:1503-1515` | Regex `(.+?)\s{2,}` breaks on stock names with internal double spaces; missing markets render explicit empty warning row |
| **Surge / VCP ML** | Filter button blank view / dropped rows | `generate_report.py:205,317,473-506,605-636`, `run_pipeline.py:1428` | Stock names with parentheses fail `\((.+?)\):` regex; `[1일] KOSPI - (no symbols)` header fails `(TOP|Top)` regex; missing markets produce no DOM panel |
| **VCP Rule** | "패턴 없음" warning for active markets | `generate_report.py:231,513-550` | Stock names with parentheses fail `\((.+?)\)` regex; `build_html` renders explicit empty row for unpopulated markets |
| **Lead-Lag** | Missing follower / leader rows | `generate_report.py:278,290,558-582` | Non-greedy regex `\((.+?)\):` fails when stock names contain parentheses; leader returns with `nan` names fail regex |
| **DB & Report Layer** | Data loss & lack of fallback | `generate_report.py:960-988`, `indicator_storage.py:271-289,451-474` | `generate_report.py` bypasses DB entirely; `indicator_storage.py` does not persist Surge, VCP, Lead-Lag, or VCP ML to DB |
