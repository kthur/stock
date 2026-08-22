# In-Depth Analysis: Strategy #9 RIM Pipeline Execution, Background Fundamental Sync, and Multi-Market Generation

- **Author**: explorer_rim_2
- **Target**: Pipeline Execution, Async Fundamental Sync, Multi-Market Generation, and Error Remediation
- **Date**: 2026-08-22
- **Related Requirements**: R1, R2, R3, R4 in `ORIGINAL_REQUEST.md`

---

## 1. Executive Summary

This investigation analyzed the end-to-end execution path of Strategy #9 (RIM - Residual Income Model) across all 5 target markets (`KOSPI`, `KOSDAQ`, `SP500`, `NASDAQ`, `RUSSELL2000`).

We identified 4 root-cause mechanisms responsible for the pipeline crashes, missing market prediction files, artificial valuation distortions, and broken HTML dashboard reporting observed in Run 32496682187:

1. **Scalar vs. Series `AttributeError` in `rim_valuation.py:352`**:
   `shares = pd.to_numeric(df.get('shares_outstanding', 0.0), errors='coerce').fillna(0.0)` called `.fillna()` on scalar `float(0.0)` whenever `shares_outstanding` was absent from `df`. This crashed `compute_rim_scores` during NASDAQ and RUSSELL2000 inference runs, suppressing the generation of `rim_predictions_NASDAQ.txt` and `rim_predictions_RUSSELL2000.txt`.
2. **Artificial BPS Fabrication & Value Trap Inflation**:
   `run_pipeline.py:2656` (`fund_df.loc[no_bps, 'bps'] = fund_df.loc[no_bps, 'eps'] / 0.08`) and `rim_valuation.py:355, 366` invented fake BPS whenever book value was missing, inflating intrinsic value $V_0$ up to 500% for cyclical low-P/E stocks.
3. **Database Schema & Async Fundamental Synchronization**:
   `MarketIndicatorStorage` lacked auto-migration for `bps`, `total_debt`, and `cash_equivalents` in `stock_fundamentals`. The background fetching thread (`t2`) is properly joined at `run_pipeline.py:1815`, but if SQLite schema or network fetches miss columns, downstream consumers lacked defensive type handling.
4. **HTML Parser / Column Format Desynchronization**:
   `run_pipeline.py` writes a 12-column table (`Rank`, `Symbol`, `Name`, `Market`, `Price`, `Intrinsic V0`, `Discount %`, `ROE_raw`, `ROE_adj`, `EQ`, `Filter`, `RIM Score`), but `generate_report.py::parse_rim` only accepted 8/9 columns. Consequently, `parse_rim` failed completely (0 rows parsed), causing the HTML dashboard to display "데이터 없음" across all 5 markets.

---

## 2. Detailed Pipeline Execution & Async Sync Trace

### 2.1 Async Fundamental Ingestion (`_bg_fundamentals`)
In `trading_system/run_pipeline.py`:
- **Spawn (Line 1754)**:
  `t2 = threading.Thread(target=_bg_fundamentals, args=(all_symbols, "inference"), daemon=True)`
  `t2.start()` starts non-blocking streaming ingestion of balance sheet / income statement fundamentals.
- **Inference Price Fetch (Lines 1763–1793)**:
  Main thread concurrently fetches price history for all active universe symbols via `ThreadPoolExecutor` and `StockPriceDB` (`stock_prices.db`).
- **Join / Barrier Synchronization (Line 1815)**:
  ```python
  if all_symbols and t2 is not None:
      logger.info("Waiting for inference fundamentals fetch to complete...")
      t2.join()
  ```
  `t2.join()` guarantees that all SQLite writes to `market_indicators.db` by `fetch_and_store_fundamentals_batch` are finished before inference begins.
- **Batch Cache Retrieval (Lines 1818–1827)**:
  `all_infer_fund_df = storage.get_all_fundamentals(infer_symbols)` loads the unified fundamentals cache into RAM to prevent thread contention or SQLite read timeouts during model feature merging.

### 2.2 Strategy #9 RIM Execution Stage (Lines 2626–2742)
- **Input Assembly**: `df_rim_input` is constructed from the latest OHLCV price row of each symbol in `infer_data_dict`.
- **Fundamental Merge**:
  `fund_df = storage.get_all_fundamentals(df_rim_input['symbol'].tolist())`
  Applies 60-day regulatory filing lag (`date_available = date + 60d <= cutoff_date`) and dedupes to the latest available quarter.
- **Calculation Call**:
  `rim_df = rim_engine.compute_rim_scores(df_rim_input, symbol_market_map=symbol_market)`
- **Output File Writing**:
  Writes `trading_system/result/rim_predictions.txt` (all evaluated symbols) and loops over `['KOSPI', 'KOSDAQ', 'SP500', 'NASDAQ', 'RUSSELL2000']` to write `rim_predictions_{_m}.txt`.

---

## 3. Root Cause Analysis of Run 32496682187 Failure

### 3.1 Unsafe Scalar Method Call in `rim_valuation.py:352`
In `src/core/rim_valuation.py` lines 350–355:
```python
elif 'book_value' in df.columns:
    bv = pd.to_numeric(df['book_value'], errors='coerce').fillna(0.0)
    shares = pd.to_numeric(df.get('shares_outstanding', 0.0), errors='coerce').fillna(0.0)
    # When shares exist and book_value is aggregate equity, divide by shares
    calculated_bps = np.where(shares > 0, bv / np.maximum(shares, 1.0), bv)
```

**Failure Mechanism**:
1. When `df_rim_input` contains `'book_value'` (from SQLite or feature prep), but `'shares_outstanding'` is absent from `df_rim_input` (e.g. legacy DB table without `shares_outstanding` or omitted in query merge), `df.get('shares_outstanding', 0.0)` evaluates to python `float(0.0)`.
2. `pd.to_numeric(0.0, errors='coerce')` returns `np.float64(0.0)` or python `float(0.0)`.
3. Invoking `.fillna(0.0)` on a scalar float raises `AttributeError: 'float' object has no attribute 'fillna'`.

**Empirical Reproduction**:
```python
# Minimal test case reproduces 100% of the crash:
df = pd.DataFrame([{'symbol': 'AAPL', 'market': 'NASDAQ', 'Close': 150.0, 'book_value': 50000.0}])
engine.compute_rim_scores(df)
# Output: AttributeError: 'float' object has no attribute 'fillna' (line 352)
```

### 3.2 Blast Radius on GHA Artifacts
1. When `compute_rim_scores` raised `AttributeError`, `run_pipeline.py:2739` caught the exception:
   ```python
   except Exception as _rim_e:
       logger.warning(f"RIM valuation score calculation skipped: {_rim_e}")
       rim_df = pd.DataFrame()
   ```
2. `rim_df` became empty (`pd.DataFrame()`), so `if not rim_df.empty:` evaluated to `False`.
3. Lines 2728–2738 (`_write_rim_file`) were skipped. Neither `rim_predictions.txt` nor `rim_predictions_NASDAQ.txt` was written to disk.
4. GHA Step "Rename output files to avoid conflicts" (`pipeline.yml:241-246`) failed to find `trading_system/result/rim_predictions.txt`, so `result_split/rim_predictions_NASDAQ.txt` was never created.
5. In the `merge-and-release` job, `verify_gha_artifacts.py` failed artifact verification because `rim_predictions_NASDAQ.txt` was missing.

---

## 4. Value Trap & Artificial BPS Analysis

### 4.1 The Mechanism of Fake BPS Distortion
In `run_pipeline.py` line 2656:
```python
no_bps = fund_df['bps'].isna() & fund_df['eps'].notna()
fund_df.loc[no_bps, 'bps'] = fund_df.loc[no_bps, 'eps'] / 0.08
```
And in `rim_valuation.py` line 355 & line 366:
```python
calculated_bps = (df['eps'] / df['roe']).replace([np.inf, -np.inf, 0.0], np.nan)
```
When `book_value` was missing or 0, the pipeline assumed $BPS = EPS / r_e = EPS / 0.08 = 12.5 \times EPS$.

**Why this creates an artificial Value Trap**:
- Cyclical stocks in Korean construction, holding companies, and commodity sectors often experience single-year peak earnings with P/E ratios around 2~4 (e.g. Price = 10,000 KRW, EPS = 3,000 KRW).
- The formula synthesized $BPS = 3,000 / 0.08 = 37,500\text{ KRW}$.
- Decaying ROE RIM computed Intrinsic Value $V_0 = 37,500\text{ KRW}$, yielding an artificial discount of $+275\%$ to $+500\%$.
- Because `operating_income` was missing, `earnings_quality` defaulted to `1.0` (100%), bypassing the EQ filter.
- These phantom high scores distorted the dynamic ensemble ranking.

### 4.2 Remedy for R2
1. **Remove all artificial BPS synthesis**: Delete line 2656 in `run_pipeline.py` and delete `eps / roe` fallback in `rim_valuation.py`.
2. **Invalidate Missing Fundamentals Cleanly**:
   When legitimate balance sheet `book_value` or valid `bps` is unavailable, assign `bps = NaN`, `discount_ratio = NaN`, and `rim_score = NaN`.
3. **Ensemble Renormalization**:
   When `rim_score` is `NaN`, `EnsembleScoringEngine` automatically drops Strategy #9 for that stock and renormalizes weights across active strategies without distorting the composite score.

---

## 5. Multi-Market Generation & Artifact Verification

### 5.1 Per-Market Output File Guarantee
To guarantee that all 5 target market files (`rim_predictions_KOSPI.txt`, `rim_predictions_KOSDAQ.txt`, `rim_predictions_SP500.txt`, `rim_predictions_NASDAQ.txt`, `rim_predictions_RUSSELL2000.txt`) and the merged `rim_predictions.txt` are always produced:

1. **Unconditional Generation**:
   Even if a market has 0 valid fundamental scores or is running in single-market matrix mode, ensure that `_write_rim_file` is called for every target market, writing a clean report with `Total symbols evaluated: N` (or `데이터 없음` if empty).
2. **Safe Merging in `merge_predictions.py`**:
   `merge_generic_strategy_files` must strip duplicate table headers (`Rank Symbol Name...`), filter descriptions, and divider lines from incoming per-market files, writing a single unified table header.

### 5.2 HTML Dashboard Report Fix (`generate_report.py`)
In `trading_system/generate_report.py`:
- Update `RimRow` dataclass to hold `roe_raw`, `roe_adj`, `eq`, `filter_reason`.
- Update `parse_rim(text)` with a regex supporting the 12-column format produced by `run_pipeline.py`:
  `^\s*(\d+)\s+(\S+)\s+(.+?)\s+(KOSPI|KOSDAQ|SP500|NASDAQ|RUSSELL2000|\w+)\s+([-\d.nanNaN]+)\s+([-\d.nanNaN]+)\s+([-+\d.nanNaN%]+)(?:\s+([-+\d.nanNaN%]+|N/A)\s+([-+\d.nanNaN%]+|N/A)\s+([-+\d.nanNaN%]+|N/A))?(?:\s+(.*?))?\s+([-+\d.nanNaN%]+)$`
- Update `build_html` RIM section to render ROE raw/adj, EQ%, and Filter tags in the table columns.

---

## 6. Recommended Code Modifications Summary

| Component | Target File | Lines | Proposed Fix |
|---|---|---|---|
| **Type Safety** | `src/core/rim_valuation.py` | 352 | Replace `df.get('shares_outstanding', 0.0)` with safe Series check `df['shares_outstanding'] if 'shares_outstanding' in df.columns else pd.Series(0.0, index=df.index)` |
| **No Fake BPS** | `src/core/rim_valuation.py` | 355–356, 363–367 | Remove `eps / roe` BPS fallback; set `bps = np.nan` when `book_value` is missing |
| **No Fake BPS** | `trading_system/run_pipeline.py` | 2654–2656 | Remove `fund_df.loc[no_bps, 'bps'] = fund_df.loc[no_bps, 'eps'] / 0.08` |
| **DB Migrations** | `src/data_layer/indicator_storage.py` | 344, 490 | Add `bps`, `total_debt`, `cash_equivalents` to `CREATE TABLE` and `migrations` list |
| **HTML Report** | `trading_system/generate_report.py` | 125–134, 614–656 | Extend `RimRow` and `parse_rim` regex to parse 12-column output with ROE raw/adj, EQ, and Filter tags |
| **Artifact Merge** | `trading_system/merge_predictions.py` | 380–424 | Filter out duplicate headers and divider lines across merged per-market strategy files |
