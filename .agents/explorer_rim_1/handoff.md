# Handoff Report: Strategy #9 RIM Valuation Engine Bug Investigation

**Agent**: Explorer 1 (`explorer_rim_1`)  
**Date**: 2026-08-22  
**Handoff Type**: Hard (Investigation Complete)  
**Target Recipient**: Orchestrator / Worker Agent

---

## 1. Observation

### Obs 1: Scalar vs Series Crash in US Markets
- **File**: `trading_system/src/core/rim_valuation.py:350-355`
- **Code**:
  ```python
  elif 'book_value' in df.columns:
      bv = pd.to_numeric(df['book_value'], errors='coerce').fillna(0.0)
      shares = pd.to_numeric(df.get('shares_outstanding', 0.0), errors='coerce').fillna(0.0)
      # When shares exist and book_value is aggregate equity, divide by shares
      calculated_bps = np.where(shares > 0, bv / np.maximum(shares, 1.0), bv)
  ```
- **Error**: When `shares_outstanding` is absent from `df.columns` (e.g. NASDAQ / RUSSELL2000 jobs or minimal feature DataFrames), `df.get('shares_outstanding', 0.0)` returns scalar float `0.0`. Calling `.fillna(0.0)` on a float raises verbatim:
  `AttributeError: 'float' object has no attribute 'fillna'`
- **Effect in Pipeline**: In `trading_system/run_pipeline.py:2739`, the calculation is caught by `except Exception as _rim_e:` and skips writing `rim_predictions_NASDAQ.txt` and `rim_predictions_RUSSELL2000.txt`.

### Obs 2: Synthetic BPS Fabrication (`bps = eps / 0.08`)
- **File**: `trading_system/run_pipeline.py:2654-2656`
- **Code**:
  ```python
  # Fallback BPS from eps when book_value unavailable
  no_bps = fund_df['bps'].isna() & fund_df['eps'].notna()
  fund_df.loc[no_bps, 'bps'] = fund_df.loc[no_bps, 'eps'] / 0.08
  ```
- **File**: `trading_system/src/core/rim_valuation.py:355-357, 362-367`
- **Effect**: For cyclical low-P/E stocks with missing balance sheets (e.g., P/E = 2.5, Price = 2,000 KRW, EPS = 800 KRW), `bps` was fabricated as $800 / 0.08 = 10,000\text{ KRW}$. Because ROE defaulted to $r_e = 0.08$, intrinsic value became $V_0 = 10,000\text{ KRW}$, producing an artificial $(10,000 - 2,000)/2,000 = +400\%$ discount ratio with $100\%$ EQ, severely polluting cross-sectional percentiles.

### Obs 3: Database Schema Migration Missing Columns
- **File**: `trading_system/src/data_layer/indicator_storage.py:485-504`
- **Code**: `migrations` list contains `net_income`, `eps`, `shares_outstanding`, `book_value`, `bps`, but omits `total_debt` and `cash_equivalents`. Legacy SQLite databases in GHA runners lack these columns, degrading holding company net debt calculations.

### Obs 4: HTML Parser Column Mismatch
- **File**: `trading_system/generate_report.py:625-656`
- **Code**: `parse_rim` regex matches 8-column or 9-column lines, while `run_pipeline.py:2692-2726` writes a 12-column line (`Rank Symbol Name Market Price Intrinsic Discount ROE_raw ROE_adj EQ Filter RIM_Score`).

---

## 2. Logic Chain

1. **[From Obs 1]** `df.get('shares_outstanding', 0.0)` returns `0.0` when the column is missing $\to$ `pd.to_numeric(0.0)` returns float `0.0` $\to$ `0.0.fillna(0.0)` raises `AttributeError: 'float' object has no attribute 'fillna'` $\to$ Caught by broad try/except in `run_pipeline.py` $\to$ Returns empty DataFrame $\to$ `rim_predictions_{MARKET}.txt` files are skipped for markets missing `shares_outstanding`.
   - **Remedy**: Replace with `shares = pd.to_numeric(df['shares_outstanding'], errors='coerce').fillna(0.0) if 'shares_outstanding' in df.columns else pd.Series(0.0, index=df.index)`.
2. **[From Obs 2]** `bps = eps / 0.08` asserts a static intrinsic multiple of $12.5\times$ EPS on any stock without balance sheet data $\to$ For deep-value or cyclical stocks trading at P/E 2.0~3.5, this creates artificial $3.5\times \sim 6.25\times$ valuation ratios ($+250\% \sim +525\%$ discount) $\to$ The absence of balance sheet income statements leads to default EQ = 1.0 $\to$ Fabricated stocks occupy top ranks and depress valid stocks.
   - **Remedy**: Remove `fund_df.loc[no_bps, 'bps'] = fund_df.loc[no_bps, 'eps'] / 0.08` and all synthetic BPS heuristics. If genuine BPS cannot be computed from `bps` or `book_value / shares_outstanding`, set `bps = np.nan`, `intrinsic_value = np.nan`, `discount_ratio = np.nan`, `rim_score = np.nan`.
3. **[From Obs 3]** SQLite databases created in prior pipeline runs lack `total_debt` and `cash_equivalents` $\to$ Queries in GHA runners fail or omit debt data $\to$ Holding company net debt deduction fails.
   - **Remedy**: Add `("stock_fundamentals", "total_debt", "REAL DEFAULT 0")` and `("stock_fundamentals", "cash_equivalents", "REAL DEFAULT 0")` to `MarketIndicatorStorage._init_db`.
4. **[From Obs 4]** Enhanced 12-column RIM predictions written by `run_pipeline.py` are rejected by `parse_rim` regex expecting 8 or 9 columns $\to$ HTML report generator fails to parse RIM rows or displays empty tables.
   - **Remedy**: Update `parse_rim` in `generate_report.py` to use whitespace splitting and dynamically locate columns.

---

## 3. Caveats

- **Network-Level Missing Fundamentals**: Some international micro-cap tickers on NASDAQ / RUSSELL2000 legitimately lack Yahoo Finance balance sheet filings. Invalidation (`NaN` score) is the strictly correct quant behavior, allowing dynamic ensemble weight renormalization.
- **Holding Company Scope**: Holding company detection uses regex patterns and GICS/KRX codes. Companies that are de-facto holding companies without '지주'/'홀딩스' in their name or sector code will be valued using standard RIM rather than SOTP discount.

---

## 4. Conclusion

1. The NASDAQ/RUSSELL2000 GHA failures were caused by scalar float `.fillna(0.0)` invocation when `shares_outstanding` was absent.
2. The 300~500% phantom discounts were caused by synthetic BPS imputation (`eps / 0.08`) coupled with default ROE = 0.08.
3. Clean NaN invalidation when balance sheet book value is absent completely cures the value trap and enables pure multi-factor ensemble re-weighting.
4. Database migration and HTML parsing updates ensure end-to-end pipeline robustness across all 5 markets.

---

## 5. Verification Method

1. **Unit Test Verification**:
   ```bash
   .venv/Scripts/python.exe -m pytest tests/test_rim_strategy.py -v
   ```
2. **Missing Column & Empty DataFrame Stress Test**:
   Execute `compute_rim_scores` on:
   - `pd.DataFrame()` (empty DataFrame)
   - `pd.DataFrame([{'symbol': 'US01', 'market': 'NASDAQ', 'Close': 100.0, 'book_value': 50000.0}])` (no `shares_outstanding`)
   - `pd.DataFrame([{'symbol': 'NO_BV', 'market': 'KOSPI', 'Close': 5000.0, 'eps': 2000.0}])` (no BPS / book value)
   Verify no exceptions are raised and `NO_BV` receives `np.nan` `rim_score` and `discount_ratio`.
3. **Full Project Test Suite**:
   ```bash
   .venv/Scripts/python.exe -m pytest tests/ -q
   ```
