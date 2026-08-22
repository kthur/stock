# Handoff Report: Strategy #9 RIM Pipeline & Multi-Market Investigation

- **Author**: explorer_rim_2
- **Recipient**: orchestrator_rim_1 / parent (e3936fc1-57bc-49a5-8374-de53439674c7)
- **Date**: 2026-08-22
- **Status**: Completed (Hard Handoff)

---

## 1. Observation

Direct code and empirical evidence from investigation:

1. **Unsafe Scalar Method in `src/core/rim_valuation.py:352`**:
   ```python
   # Line 352
   shares = pd.to_numeric(df.get('shares_outstanding', 0.0), errors='coerce').fillna(0.0)
   ```
   When `shares_outstanding` is not a column in `df`, `df.get('shares_outstanding', 0.0)` returns scalar float `0.0`. `pd.to_numeric(0.0)` returns `0.0`. Invoking `.fillna(0.0)` on a float raised verbatim:
   `AttributeError: 'float' object has no attribute 'fillna'`.
   Empirical reproduction via:
   `.venv\Scripts\python.exe -c "import sys; sys.path.insert(0, 'trading_system'); import pandas as pd; from src.core.rim_valuation import RIMValuationEngine; engine = RIMValuationEngine(); df = pd.DataFrame([{'symbol': 'AAPL', 'market': 'NASDAQ', 'Close': 150.0, 'book_value': 50000.0}]); engine.compute_rim_scores(df)"`
   reproduced the exact `AttributeError` at line 352.

2. **Pipeline Blast Radius in `trading_system/run_pipeline.py:2739`**:
   ```python
   except Exception as _rim_e:
       logger.warning(f"RIM valuation score calculation skipped: {_rim_e}")
       rim_df = pd.DataFrame()
   ```
   When `compute_rim_scores` raised `AttributeError`, `run_pipeline.py` caught it and set `rim_df = pd.DataFrame()`. The file-writing block (lines 2680–2738) was skipped, so neither `rim_predictions.txt` nor `rim_predictions_{MARKET}.txt` was created in `trading_system/result/`. Consequently, GHA matrix jobs for NASDAQ and RUSSELL2000 had 0 RIM artifact files.

3. **Artificial BPS Fabrication in `trading_system/run_pipeline.py:2656` & `rim_valuation.py:355`**:
   ```python
   # run_pipeline.py:2656
   no_bps = fund_df['bps'].isna() & fund_df['eps'].notna()
   fund_df.loc[no_bps, 'bps'] = fund_df.loc[no_bps, 'eps'] / 0.08
   ```
   ```python
   # rim_valuation.py:355-356, 366
   elif 'eps' in df.columns and 'roe' in df.columns:
       calculated_bps = (df['eps'] / df['roe']).replace([np.inf, -np.inf, 0.0], np.nan)
   ```
   When `book_value` was missing or zero, the pipeline invented artificial `bps = eps / 0.08`. For cyclical low-P/E stocks (e.g. Price = 10,000, EPS = 3,000), `bps` was inflated to 37,500 (+275% discount ratio), generating phantom 100% scores and top ranks.

4. **Background Thread Synchronization in `trading_system/run_pipeline.py:1754, 1815`**:
   `t2 = threading.Thread(target=_bg_fundamentals, args=(all_symbols, "inference"), daemon=True)` is spawned at line 1754 and joined at line 1815 (`t2.join()`). The fundamental write operations to SQLite WAL are finished before `storage.get_all_fundamentals(infer_symbols)` is called at line 1821.

5. **Missing SQLite Column Migrations in `src/data_layer/indicator_storage.py`**:
   `stock_fundamentals` table creation schema (lines 336–347) and `migrations` list (lines 485–503) lacked auto-migration for `bps`, `total_debt`, and `cash_equivalents`.

6. **HTML Report Desynchronization in `trading_system/generate_report.py:614`**:
   `parse_rim` expected 8 or 9 columns, but `run_pipeline.py:2723-2726` produces 12 columns. Tested experimentally, `parse_rim` failed on actual pipeline output and returned `('', [])`, causing the HTML report to render "데이터 없음" for all 5 markets.

---

## 2. Logic Chain

1. **Premise**: In US markets (NASDAQ, RUSSELL2000), SQLite fundamentals frequently contain `book_value` while omitting `shares_outstanding` (or `shares_outstanding` is not merged).
2. **Observation**: When `shares_outstanding` is missing from `df`, `df.get('shares_outstanding', 0.0)` in `rim_valuation.py:352` yields scalar float `0.0`. Calling `pd.to_numeric(0.0).fillna(0.0)` raises `AttributeError: 'float' object has no attribute 'fillna'`.
3. **Observation**: In `run_pipeline.py:2739`, the unhandled `AttributeError` caused the exception handler to set `rim_df = pd.DataFrame()`, skipping file generation for `rim_predictions.txt` and `rim_predictions_{MARKET}.txt`.
4. **Inference**: In GHA matrix jobs for NASDAQ/RUSSELL2000, missing `rim_predictions.txt` prevented the split-artifact step from creating `result_split/rim_predictions_{TARGET}.txt`. This caused artifact verification in `merge-and-release` to fail or skip these markets.
5. **Premise**: When `book_value` was absent, `run_pipeline.py:2656` divided `eps` by `0.08` to fabricate BPS.
6. **Observation**: Cyclical stocks with low P/E had inflated BPS up to 12.5x EPS, causing RIM to compute 300~500% discounts and assign top ranking to distressed or cyclical stocks.
7. **Conclusion**: Eliminating fake BPS fallbacks (`eps / 0.08` and `eps / roe`), fixing scalar/Series method calls in `rim_valuation.py`, migrating SQLite columns in `indicator_storage.py`, and updating `generate_report.py::parse_rim` to parse 12 columns completely resolves the failure chain across all 5 target markets.

---

## 3. Caveats

- **Network-Level Fundamental Data Availability**: Yahoo Finance may return empty financials for certain thinly traded or micro-cap US stocks. The pipeline must gracefully handle empty fundamental sets by producing valid `NaN` RIM scores without throwing exceptions.
- **Ensemble Dynamic Renormalization**: When `rim_score` is `NaN`, `EnsembleScoringEngine` automatically drops the strategy and renormalizes weights across active strategies. This is the intended mathematical behavior.
- No other caveats.

---

## 4. Conclusion & Recommended Action Plan

The implementation plan for the Workers / Implementers consists of 5 targeted edits:

1. **`src/core/rim_valuation.py`**:
   - Replace line 352 with:
     ```python
     shares = pd.to_numeric(df['shares_outstanding'], errors='coerce').fillna(0.0) if 'shares_outstanding' in df.columns else pd.Series(0.0, index=df.index)
     ```
   - Delete fake BPS fallback from `eps / roe` (lines 355–356 and 363–367).
   - In `compute_scores` and `compute_rim_scores`, ensure all inputs return valid DataFrames with `NaN` for missing BPS stocks.

2. **`trading_system/run_pipeline.py`**:
   - Remove fake BPS fallback `fund_df.loc[no_bps, 'bps'] = fund_df.loc[no_bps, 'eps'] / 0.08` (lines 2654–2656).
   - Ensure `_write_rim_file` is called for each target market (`KOSPI`, `KOSDAQ`, `SP500`, `NASDAQ`, `RUSSELL2000`) and the combined file, even if a market has only `NaN` scores, producing clean formatted tables.

3. **`src/data_layer/indicator_storage.py`**:
   - Add `bps`, `total_debt`, `cash_equivalents` to `CREATE TABLE IF NOT EXISTS stock_fundamentals` and the `migrations` list.
   - Update `save_fundamentals` to persist `bps`, `total_debt`, `cash_equivalents` safely.

4. **`trading_system/merge_predictions.py`**:
   - Update `merge_generic_strategy_files` to filter duplicate table headers (`Rank Symbol Name...`), filter descriptions, and divider lines when merging per-market text files.

5. **`trading_system/generate_report.py`**:
   - Extend `RimRow` dataclass with `roe_raw`, `roe_adj`, `eq`, `filter_reason`.
   - Update `parse_rim` regex to cleanly parse both 12-column and legacy 8/9-column formats.
   - Update HTML template to render ROE raw/adj, EQ%, and Filter tags in the RIM panel table.

---

## 5. Verification Method

To independently verify these fixes once implemented:

1. **Unit & Edge Case Test**:
   ```bash
   .venv/Scripts/python.exe -m pytest tests/test_rim_strategy.py -v
   ```
2. **Partial DataFrame / Scalar Bug Regression Test**:
   ```bash
   .venv/Scripts/python.exe -c "import sys; sys.path.insert(0, 'trading_system'); import pandas as pd; from src.core.rim_valuation import RIMValuationEngine; engine = RIMValuationEngine(); df = pd.DataFrame([{'symbol': 'AAPL', 'market': 'NASDAQ', 'Close': 150.0, 'book_value': 50000.0}]); res = engine.compute_rim_scores(df); assert not res.empty"
   ```
3. **Fake BPS Elimination Test**:
   ```bash
   .venv/Scripts/python.exe -c "import sys; sys.path.insert(0, 'trading_system'); import pandas as pd; from src.core.rim_valuation import RIMValuationEngine; engine = RIMValuationEngine(); df = pd.DataFrame([{'symbol': 'CYCLIC', 'market': 'KOSPI', 'Close': 10000.0, 'eps': 3000.0, 'roe': 0.08}]); res = engine.compute_rim_scores(df); assert pd.isna(res.iloc[0]['rim_score'])"
   ```
4. **HTML Report Parser Test**:
   ```bash
   .venv/Scripts/python.exe -c "import sys; sys.path.insert(0, 'trading_system'); from generate_report import parse_rim; sample = '1    005930    삼성전자            KOSPI     70000.00    93750.00      +33.9%     15.0%    15.0%  100%  [ADJ]                         95.0%'; d, r = parse_rim(sample); assert len(r) == 1 and r[0].symbol == '005930'"
   ```
5. **Full Test Suite Execution**:
   ```bash
   .venv/Scripts/python.exe -m pytest tests/ -q
   ```
