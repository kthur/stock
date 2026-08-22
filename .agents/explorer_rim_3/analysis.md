# Comprehensive Investigation Analysis: Database Schema Migration, Artifact Merging, Dashboard Reporting & Test Coverage (Strategy #9 RIM)

**Explorer**: Explorer 3 (`bf7d1cba-bc8e-4e02-b9cc-084136f70477`)  
**Mission**: Strategy #9 RIM Valuation — Storage Schema Migration, Artifact Merging, Dashboard Reporting, and Test Coverage Audit  
**Date**: 2026-08-22  
**Target Files Analyzed**:
- `trading_system/src/data_layer/indicator_storage.py`
- `trading_system/src/persistence/database.py`
- `trading_system/src/data_layer/earnings_data.py`
- `trading_system/src/core/rim_valuation.py`
- `trading_system/run_pipeline.py`
- `trading_system/merge_predictions.py`
- `trading_system/scripts/verify_gha_artifacts.py`
- `trading_system/generate_report.py`
- `.agents/skills/gha-artifact-verifier/SKILL.md`
- `tests/test_rim_strategy.py`
- `tests/test_e2e_consolidated.py`
- `tests/test_pipeline_integration.py`
- `tests/test_indicator_storage.py`
- `tests/test_report_generator_hrp.py`

---

## Executive Summary

Our investigation uncovered critical systemic gaps across the RIM valuation data lifecycle:
1. **Database Schema & Migration Blind Spot**: `MarketIndicatorStorage._init_db()` defines `stock_fundamentals` with only 8 basic columns. While it migrated `book_value` and `bps`, it **completely omitted `total_debt` and `cash_equivalents`** from both `CREATE TABLE` and the `migrations` list. Furthermore, `save_fundamentals()` hardcodes column insertion lists that completely drop `total_debt` and `cash_equivalents`. Legacy SQLite databases in GHA or fresh runs cannot store or query debt/cash data needed for holding company SOTP net debt deductions.
2. **Scalar / Series Method Crash in US Markets (`AttributeError`)**: In `src/core/rim_valuation.py` line 352, `shares = pd.to_numeric(df.get('shares_outstanding', 0.0), errors='coerce').fillna(0.0)` calls `.fillna()` directly on the scalar float default `0.0` when `'shares_outstanding'` is not present in `df`. In NASDAQ and RUSSELL2000 runs, this raised `AttributeError: 'float' object has no attribute 'fillna'`, crashing the entire RIM strategy and preventing `rim_predictions_NASDAQ.txt` and `rim_predictions_RUSSELL2000.txt` from being generated.
3. **Artificial BPS Fabrication & Value Trap Distortion**: In `run_pipeline.py` (lines 2654–2656), `fund_df.loc[no_bps, 'bps'] = fund_df.loc[no_bps, 'eps'] / 0.08` fabricated artificial book value for stocks with zero/missing `book_value`. For cyclical stocks with low P/E ratios, this produced phantom discounts of 300%~500% and assigned 100% EQ across rows.
4. **Dashboard HTML Parsing Regex Mismatch**: `run_pipeline.py` outputs a **12-column** format (`Rank Symbol Name Market Price Intrinsic V0 Discount % ROE_raw ROE_adj EQ Filter RIM Score`). However, `generate_report.py`'s `parse_rim()` only contains regex patterns for **8-column and 9-column** legacy formats with strict end-of-line anchors (`$`). As a result, `parse_rim()` fails to parse any data rows from valid 12-column `rim_predictions.txt` files, rendering empty tables in the HTML dashboard.
5. **Artifact Merging Multi-Market Alignment**: `merge_predictions.py` merges `rim_predictions_{MARKET}.txt` via `merge_generic_strategy_files()`. When US market jobs crashed and skipped creating per-market files, `merge_predictions.py` fell back to whatever partial files existed.
6. **Test Coverage Deficits**: `tests/test_rim_strategy.py` only tests 9 happy-path unit scenarios and tests `parse_rim()` with the old 8-column format. It lacks tests for missing/empty DataFrames, scalar default safety, legacy SQLite schema migration of all 4 columns (`bps`, `book_value`, `total_debt`, `cash_equivalents`), and 12-column HTML generation.

---

## 1. Deep Dive: Database Storage & Schema Migration

### 1.1 Table Definition and Query Mechanics in `MarketIndicatorStorage`
In `trading_system/src/data_layer/indicator_storage.py`:

```python
# Lines 336-347: Initial Table Creation
CREATE TABLE IF NOT EXISTS stock_fundamentals (
    symbol TEXT,
    date TEXT,
    revenue REAL,
    operating_income REAL,
    net_income REAL DEFAULT 0,
    eps REAL DEFAULT 0,
    shares_outstanding REAL DEFAULT 0,
    dividend_per_share REAL DEFAULT 0,
    PRIMARY KEY (symbol, date)
)
```

```python
# Lines 485-504: Schema Migrations
migrations = [
    ("stock_fundamentals", "net_income", "REAL DEFAULT 0"),
    ("stock_fundamentals", "eps", "REAL DEFAULT 0"),
    ("stock_fundamentals", "shares_outstanding", "REAL DEFAULT 0"),
    ("stock_fundamentals", "book_value", "REAL DEFAULT 0"),
    ("stock_fundamentals", "bps", "REAL DEFAULT 0"),
    ("stock_universe", "sector", "TEXT DEFAULT ''"),
    ("stock_universe", "industry", "TEXT DEFAULT ''"),
    ("stock_universe", "currency", "TEXT DEFAULT 'USD'"),
    ("ensemble_prediction_history", "actual_return_1d", "REAL"),
    ...
]
for tbl, col, col_def in migrations:
    if not _column_exists(conn, tbl, col):
        conn.execute(f"ALTER TABLE {tbl} ADD COLUMN {col} {col_def}")
conn.commit()
```

### 1.2 Identified Bugs & Root Causes
1. **Missing `total_debt` and `cash_equivalents`**:
   - `total_debt` and `cash_equivalents` are never added to `stock_fundamentals` either in initial creation or in `migrations`.
   - When `run_pipeline.py` requests these columns for holding company SOTP net debt calculations (`merge_cols = ['symbol', 'bps', 'roe', 'operating_income', 'net_income', 'book_value', 'total_debt', 'cash_equivalents', 'shares_outstanding']`), SQLite returns only the columns that exist.
2. **`save_fundamentals()` Dropping Columns**:
   - In `indicator_storage.py` lines 994–1006, `save_fundamentals()` branches only on `has_bps`.
   - Even if `df_fundamentals` contains `total_debt` or `cash_equivalents`, they are ignored and omitted from `INSERT OR REPLACE INTO stock_fundamentals`.
3. **Empty Query Column Schema**:
   - Line 1056 in `get_all_fundamentals([])` returns an empty DataFrame with columns:
     `['symbol', 'date', 'revenue', 'operating_income', 'net_income', 'eps', 'shares_outstanding', 'dividend_per_share', 'book_value']`.
     It is missing `bps`, `total_debt`, `cash_equivalents`.

### 1.3 Recommended Fix for `indicator_storage.py`
1. Update `CREATE TABLE IF NOT EXISTS stock_fundamentals` to include:
   `book_value REAL DEFAULT 0, bps REAL DEFAULT 0, total_debt REAL DEFAULT 0, cash_equivalents REAL DEFAULT 0`.
2. Add explicit migration entries to `migrations`:
   ```python
   ("stock_fundamentals", "book_value", "REAL DEFAULT 0"),
   ("stock_fundamentals", "bps", "REAL DEFAULT 0"),
   ("stock_fundamentals", "total_debt", "REAL DEFAULT 0"),
   ("stock_fundamentals", "cash_equivalents", "REAL DEFAULT 0"),
   ```
3. Update `save_fundamentals()` to dynamically or explicitly insert `book_value`, `bps`, `total_debt`, and `cash_equivalents`.
4. Update `get_all_fundamentals([])` fallback column list to include all fundamental columns.

---

## 2. Deep Dive: Artifact Merging, Dashboard Reporting & Verifier Skill

### 2.1 Artifact Merging (`merge_predictions.py`)
- `merge_predictions.py` defines `merge_generic_strategy_files(result_dir, target_dirs, "rim_predictions.txt", "RIM Intrinsic Valuation Predictions")`.
- It iterates through all 5 markets in `target_dirs` (`SP500`, `NASDAQ`, `RUSSELL2000`, `KOSPI`, `KOSDAQ`) and reads `rim_predictions_{MARKET}.txt`.
- When individual market runs succeed, `merge_generic_strategy_files()` successfully merges all rows into unified `rim_predictions.txt` with a KST timestamp header.
- **Why US markets were missing in Run 32496682187**:
  Because the NASDAQ and RUSSELL2000 runner jobs crashed during `rim_engine.compute_rim_scores()`, `rim_predictions_NASDAQ.txt` and `rim_predictions_RUSSELL2000.txt` were never created on disk. Thus `merge_predictions.py` only had KOSPI, KOSDAQ, and SP500 to merge.

### 2.2 Dashboard Generation Bug (`generate_report.py`)
In `trading_system/generate_report.py`:
- `RimRow` is currently defined at lines 125–133 as:
  ```python
  @dataclass
  class RimRow:
      rank: int
      symbol: str
      name: str
      market: str
      price: str
      intrinsic_value: str
      discount: str
      score: str
  ```
- `parse_rim()` at lines 614–657 uses regexes:
  ```python
  # Match 9-column format: Rank Symbol Name Market Price Intrinsic Discount EQ RIM_Score
  m9 = re.match(r"^(\d+)\s+(\S+)\s+(.+?)\s+(\w+)\s+([-\d.nanNaN]+)\s+([-\d.nanNaN]+)\s+([-+\d.nanNaN%]+)\s+(\S+)\s+([-+\d.nanNaN%]+)$", line)
  # Fallback to 8-column format:
  m8 = re.match(r"^(\d+)\s+(\S+)\s+(.+?)\s+(\w+)\s+([-\d.nanNaN]+)\s+([-\d.nanNaN]+)\s+([-+\d.nanNaN%]+)\s+([-+\d.nanNaN%]+)$", line)
  ```
- In `run_pipeline.py` lines 2693–2726, `_write_rim_file()` formats 12 columns:
  `Rank Symbol Name Market Price Intrinsic V0 Discount % ROE_raw ROE_adj EQ Filter RIM Score`
  e.g.:
  `1    005930    삼성전자               KOSPI     70000.00    93750.00           33.9%    15.0%    15.0%  100%   [ADJ]           100.0%`
- **Result**: Because neither `m9` nor `m8` matches the 12-column line (with `ROE_raw`, `ROE_adj`, `EQ`, `Filter`), `parse_rim()` returns an empty list `[]` of rows!
- In `generate_report.py` lines 2099–2132 (`rim_panels`), when `mkt_rim_rows` is empty, it writes:
  `<tr><td colspan="7" class="empty">데이터 없음</td></tr>`
  across all 5 markets on the HTML dashboard.

### 2.3 `verify_gha_artifacts.py` & `gha-artifact-verifier` Skill
- `verify_gha_artifacts.py` checks `rim` via `check_generic_strategy(content, market, "rim")`.
- It expects non-comment, non-header data lines >= 10 (`MIN_ITEMS_PER_STRATEGY = 10`) with non-zero numeric values.
- When `rim_predictions_{MARKET}.txt` or `rim_predictions.txt` is populated with >= 10 rows, `check_generic_strategy()` marks `valid=True`.
- The `gha-artifact-verifier` skill correctly specifies verification requirements for Strategy 9 RIM across all 5 markets.

---

## 3. Deep Dive: Pipeline Execution & Robustness Bugs

### 3.1 Scalar vs Series Crash in `rim_valuation.py`
In `trading_system/src/core/rim_valuation.py`:
- Line 352:
  ```python
  shares = pd.to_numeric(df.get('shares_outstanding', 0.0), errors='coerce').fillna(0.0)
  ```
  `df.get('shares_outstanding', 0.0)` returns `0.0` (float) when `'shares_outstanding'` is not a column in `df`. `pd.to_numeric(0.0)` is `0.0`, which has no `.fillna()` method.
- **Fix**:
  ```python
  if 'shares_outstanding' in df.columns:
      shares = pd.to_numeric(df['shares_outstanding'], errors='coerce').fillna(0.0)
  else:
      shares = pd.Series(0.0, index=df.index)
  ```
  Apply this same pattern consistently across all column extractions: `book_value`, `total_debt`, `cash_equivalents`, `operating_income`, `net_income`, `eps`, `roe`, `bps`.

### 3.2 Elimination of Fake BPS Fallback
- In `trading_system/run_pipeline.py` lines 2654–2656:
  ```python
  # DELETE THIS FAKE FALLBACK:
  # no_bps = fund_df['bps'].isna() & fund_df['eps'].notna()
  # fund_df.loc[no_bps, 'bps'] = fund_df.loc[no_bps, 'eps'] / 0.08
  ```
- In `trading_system/src/core/rim_valuation.py` lines 355–356 and lines 361–367:
  ```python
  # DELETE THESE FALLBACKS THAT INVENT BPS FROM EPS:
  # elif 'eps' in df.columns and 'roe' in df.columns:
  #     calculated_bps = (df['eps'] / df['roe']).replace([np.inf, -np.inf, 0.0], np.nan)
  # ...
  # if nan_mask.any() and 'eps' in df.columns and 'roe' in df.columns:
  #     ...
  ```
- When `bps` / `book_value` is missing or non-positive:
  - `bps` must remain `NaN`.
  - `intrinsic_value` and `discount_ratio` evaluate to `NaN`.
  - `rim_score` evaluates to `NaN`.
  - `EnsembleScoringEngine` automatically renormalizes weights across the remaining valid strategies for that stock, rather than injecting a corrupted 300%~500% phantom discount.

### 3.3 Async Background Fundamentals Synchronization
- In `run_pipeline.py` (lines 1754 and 1814), `t2 = threading.Thread(target=_bg_fundamentals, args=(all_symbols, "inference"), daemon=True)` is spawned.
- The pipeline joins `t2.join(timeout=300)` before running Strategy 1 Regression and Strategy 2 Surge.
- However, Strategy 9 RIM runs later at line 2630 and calls `storage.get_all_fundamentals(df_rim_input['symbol'].tolist())`.
- To guarantee that all background insertions from `fetch_and_store_fundamentals_batch` are committed and visible:
  1. Verify `t2.is_alive()` has completed prior to Strategy 9 RIM.
  2. Call `storage.checkpoint_wal()` or ensure fresh read connection to prevent SQLite stale snapshot reads.

---

## 4. Test Suite Audit & Identified Coverage Gaps

### 4.1 Current Test Suite Status
Running `.venv\Scripts\python.exe -m pytest tests/test_rim_strategy.py -v`:
- 9 tests passed in 23.56s.

### 4.2 Current Tests in `test_rim_strategy.py`
1. `test_rim_valuation_calculation`: 3 synthetic stocks (high, neutral, low ROE).
2. `test_rim_earnings_quality_filter`: Operating loss (-), low EQ ratio.
3. `test_rim_preferred_share_exclusion`: Preferred share symbols (`005935`, `00680K`).
4. `test_ensemble_scorer_9_strategies`: 9-strategy ensemble weighting.
5. `test_parse_rim_and_build_html`: Legacy 8-column text format HTML rendering.
6. `test_extreme_roe_normalization`: ROE > 20% & EQ < 0.4 normalization.
7. `test_holding_company_discount`: Holding company SOTP net debt discount.
8. `test_nonrecurring_income_trap`: Nonrecurring net income spike with low operating income.
9. `test_rim_small_cap_and_high_nominal_bps_scaling`: Small-cap equity and high-nominal BPS stocks.

### 4.3 Missing Test Scenarios (Critical Gaps)
The following test suites are missing and must be added:
1. **Empty & Partial DataFrame Robustness Test**:
   - `compute_rim_scores(pd.DataFrame())` returns empty DataFrame with expected columns without exception.
   - `compute_rim_scores(df_missing_cols)` where `df` lacks `'shares_outstanding'`, `'book_value'`, `'total_debt'`, `'cash_equivalents'`, `'operating_income'`, `'net_income'`, or `'roe'` executes cleanly without `AttributeError` or unhandled exceptions and yields `NaN` for missing valuation fields.
2. **Elimination of Fake BPS Fallback Test**:
   - Stock with `eps=5000`, `price=10000`, but `book_value=None`/`bps=None` produces `rim_score=NaN` and `intrinsic_value=NaN`, NEVER an artificial discount > 200%.
3. **Database Schema Auto-Migration Test (`tests/test_indicator_storage.py`)**:
   - Create a legacy SQLite table `stock_fundamentals` missing `bps`, `book_value`, `total_debt`, `cash_equivalents`.
   - Initialize `MarketIndicatorStorage(legacy_db_path)` and verify all 4 columns are safely auto-migrated via `ALTER TABLE`.
   - Save fundamentals with `total_debt` and `cash_equivalents`, query via `get_fundamentals` and `get_all_fundamentals`, and assert all fields are accurately retrieved.
4. **Multi-Market 5-Market Artifact Merging Test (`tests/test_report_generator_hrp.py` or new test file)**:
   - Create mock `rim_predictions_{MARKET}.txt` files for all 5 markets (`KOSPI`, `KOSDAQ`, `SP500`, `NASDAQ`, `RUSSELL2000`).
   - Run `merge_generic_strategy_files()` and assert `rim_predictions.txt` is created with sections from all 5 markets.
5. **12-Column `parse_rim` and Dashboard Rendering Test**:
   - Parse authentic 12-column text containing `Rank Symbol Name Market Price Intrinsic V0 Discount % ROE_raw ROE_adj EQ Filter RIM Score`.
   - Verify `parse_rim()` extracts `rank`, `symbol`, `name`, `market`, `price`, `intrinsic_value`, `discount`, `roe_raw`, `roe_adj`, `eq`, `filter_tags`, `score`.
   - Verify `build_html()` renders table rows for all 5 markets with proper styling (`.pos`, `.neg`, filter badges).

---

## 5. Summary of Recommended Code Modifications

| File | Proposed Change | Purpose |
|------|-----------------|---------|
| `trading_system/src/data_layer/indicator_storage.py` | Add `book_value`, `bps`, `total_debt`, `cash_equivalents` to `CREATE TABLE stock_fundamentals`, `migrations` list, and `save_fundamentals()` SQL INSERT. | Guarantee complete DB schema migration and persistence across legacy GHA caches. |
| `trading_system/src/core/rim_valuation.py` | Fix scalar `.fillna()` calls (line 352) to use `pd.Series(0.0, index=df.index)` fallbacks. Delete fake BPS fallbacks (`eps/roe` and `eps/0.08`). Return clean `NaN` when BPS is absent. | Prevent US market runtime crashes and eliminate phantom 300%~500% value trap discounts. |
| `trading_system/run_pipeline.py` | Remove fake BPS fallback `fund_df.loc[no_bps, 'bps'] = fund_df.loc[no_bps, 'eps'] / 0.08` at lines 2654–2656. | Stop injecting fake BPS into RIM input DataFrame. |
| `trading_system/generate_report.py` | Expand `RimRow` dataclass to include `roe_raw`, `roe_adj`, `eq`, `filter_tags`. Update `parse_rim()` regex to support 12-column format with fallback to 9/8-column legacy. Update `rim_panels` HTML table headers and cells. | Fix empty table bug on GitHub Pages dashboard and display authentic valuation metrics. |
| `tests/test_rim_strategy.py` | Add comprehensive unit tests for empty/partial DataFrames, no-fake-BPS gating, 12-column parsing, and multi-market evaluation. | Ensure 100% test coverage and prevent regression. |
| `tests/test_indicator_storage.py` | Add legacy SQLite database auto-migration test for `bps`, `total_debt`, `cash_equivalents`. | Ensure database migration resilience across CI/CD environments. |
