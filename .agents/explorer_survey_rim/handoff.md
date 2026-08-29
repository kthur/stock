# Handoff Report — RIM Valuation Engine & NaN/Formatting Diagnostic

**Working Directory**: `d:\Finance\code\stock\.agents\explorer_survey_rim`  
**Target Milestone**: Strategy 9 RIM Valuation NaN/Formatting & Data Integrity Audit  
**Date**: 2026-08-29 (UTC: 2026-08-28T22:50:00Z)

---

## 1. Observation

### 1.1 Direct Inspection of `src/core/rim_valuation.py`
- **Location**: `trading_system/src/core/rim_valuation.py:410-447`
  - When `bps` and `book_value` are absent/missing, `df['bps']` is assigned `np.nan`.
  - In line 441: `df['roe'] = df['roe'].replace([np.inf, -np.inf], np.nan).fillna(self.default_required_return)` blindly fills missing ROE with `0.08` (8.0%), creating synthetic ROE metrics for stocks that have no fundamentals.
  - In line 451: `df['earnings_quality']` defaults to `1.0` (100%) and `df['rim_filter_reason'] = ''`.
  - When a stock has `book_value <= 0` (Capital Impairment / 자본잠식) or completely missing financial statements, `df['rim_filter_reason']` remains `''` (empty string) unless `operating_income < 0` or `net_income < 0` is explicitly present.
- **Location**: `trading_system/src/core/rim_valuation.py:651-675`
  - In line 651:
    ```python
    invalid_mask = df['rim_filter_reason'].isin(['LOW_EARNINGS_QUALITY', 'PREFERRED_SHARE', 'OPERATING_LOSS'])
    if 'bps' in df.columns:
        bps_numeric = pd.to_numeric(df['bps'], errors='coerce')
        invalid_mask = invalid_mask | bps_numeric.isna() | (bps_numeric <= 0)
    ```
  - In line 672:
    ```python
    if invalid_mask.any():
        df.loc[invalid_mask, ['rim_score', 'discount_ratio', 'intrinsic_value']] = np.nan
    ```
  - For invalid stocks (missing BPS, capital impairment, preferred shares, operating loss), `rim_score`, `discount_ratio`, and `intrinsic_value` are set to `np.nan`.
  - However, `df['rim_filter_reason']` is never updated with explicit reasons such as `'MISSING_FUNDAMENTALS'` or `'CAPITAL_IMPAIRMENT'` for missing BPS / negative equity stocks.

### 1.2 Direct Inspection of `run_pipeline.py` & Text File Generation
- **Location**: `trading_system/run_pipeline.py:2761-2804` (`_write_rim_file`)
  - Lines 2774-2795:
    ```python
    disc_val = row.get('discount_ratio', np.nan)
    disc_str = f"{disc_val*100:>9.1f}%" if pd.notna(disc_val) else "       nan%"
    ...
    rim_score_val = row.get('rim_score', np.nan)
    rim_score_str = f"{rim_score_val*100:.1f}%" if pd.notna(rim_score_val) else "   nan%"
    intrinsic = row.get('intrinsic_value', np.nan)
    intrinsic_str = f"{intrinsic:<14.2f}" if pd.notna(intrinsic) else f"{'nan':<14}"
    ```
  - Lines 2796-2800:
    ```python
    f_out.write(
        f"{rank:<5}{row['symbol']:<10}{name_str:<20}{row['market']:<10}"
        f"{row['Close']:<12.2f}{intrinsic_str}{disc_str}"
        f"{roe_raw_str:>8} {roe_adj_str:>8} {eq_str:>5}  {filter_str:<32}{rim_score_str:>10}\n"
    )
    ```
  - Notice that `"nan%"`, `"   nan%"`, and `"nan"` are hardcoded fallback strings in `_write_rim_file`.
  - Furthermore, `rim_merged` is sorted by `rim_score` descending (`na_position='last'`). If a market contains fewer than 100 valid stocks (or 0 valid stocks), `df_rim.head(100)` includes all the NaN rows, ranking them as Rank 1, 2, 3... and outputting lines with literal `nan` and `nan%`.
- **Direct Evidence from Disk**:
  - `trading_system/result/rim_predictions.txt` line 8 contains:
    `1    057050    현대홈쇼핑               KOSPI     87300.00    nan                  nan%    8.0%     8.0%  100%                                        nan%`
  - `trading_system/result/rim_predictions_KOSPI.txt` line 8 contains the exact same verbatim text.

### 1.3 Direct Inspection of `generate_report.py` (HTML Report Generator)
- **Location**: `trading_system/generate_report.py:712-718` (`parse_rim`)
  ```python
  m12 = re.match(
      r"^(\d+)\s+(\S+)\s+(.+?)\s+(KOSPI|KOSDAQ|SP500|NASDAQ|RUSSELL2000|KONEX|[A-Za-z0-9_]+)\s+"
      r"([-\d.nanNaN]+)\s+([-\d.nanNaN]+)\s+([-+\d.nanNaN%]+)\s+"
      r"([-+\d.nanNaN%]+|N/A)\s+([-+\d.nanNaN%]+|N/A)\s+([-+\d.nanNaN%]+|N/A)"
      r"(?:\s+(.*?))?\s+([-+\d.nanNaN%]+)$",
      line
  )
  ```
  - The regex explicitly matches `nan` and `NaN` because the output text previously contained `nan`.
  - In columns 5 (Price), 6 (Intrinsic), 7 (Discount), and 12 (RIM Score), the pattern `([-\d.nanNaN]+)` does NOT include `N/A` or `-`. If `N/A` is output instead of `nan`, the existing regex would fail to match those rows.
- **Location**: `trading_system/generate_report.py:2309-2316`
  - HTML table rows insert `{rim_r.price}`, `{rim_r.intrinsic_value}`, `{rim_r.discount}`, `{score_display}` verbatim without badge formatting when values are `N/A` or missing.

### 1.4 Direct Inspection of Test Suites (`tests/`)
- `tests/test_rim_strategy.py` tests:
  - Basic RIM valuation calculation
  - Earnings quality filter (`LOW_EARNINGS_QUALITY`)
  - Preferred share exclusion (`PREFERRED_SHARE`)
  - Extreme ROE normalization (`EXTREME_ROE_NORMALIZED`, `ABSOLUTE_ROE_CAP = 0.25`)
  - Holding company SOTP discount (`HOLDING_CO_DISCOUNT = 0.40`)
  - Small-cap scaling and high-nominal KRX stock scaling
  - Empty/None input handling
  - Fake BPS gating
  - 12-column parsing
- `tests/test_challenger_rim_2_stress.py` tests:
  - Auto-migration and multi-threaded persistence in `MarketIndicatorStorage`
  - `parse_rim` robustness across 12-col, 9-col, and 8-col formats
  - `merge_generic_strategy_files` multi-market merging and header deduplication

---

## 2. Logic Chain

1. **[From Obs 1.1]** When a ticker lacks fundamental data (no `bps` or `book_value` in DB), `compute_rim_scores` leaves `rim_filter_reason` as `''` and blindly defaults `roe` to `0.08` and `earnings_quality` to `1.0`.
2. **[From Obs 1.1]** When a ticker suffers capital impairment (`bps <= 0` or `book_value <= 0`), `compute_rim_scores` treats it as invalid but does not tag `rim_filter_reason` with `'CAPITAL_IMPAIRMENT'`.
3. **[From Obs 1.2]** In `run_pipeline.py`, `_write_rim_file` takes `df_rim.head(100)` without filtering out NaN `rim_score` rows. When invalid rows are encountered, lines 2775, 2793, and 2795 format them as `"       nan%"`, `"   nan%"`, and `"nan"`.
4. **[From Obs 1.2]** If a market has no valid computable RIM valuations (e.g. initial run with 1 ticker lacking fundamental DB entries like `057050`), the single invalid row is ranked as `#1` and printed with raw `nan` and `nan%` values in `rim_predictions.txt` and `rim_predictions_KOSPI.txt`.
5. **[From Obs 1.3]** In `generate_report.py`, `parse_rim` regex expects `nanNaN` in price, intrinsic value, discount, and score columns. If `_write_rim_file` is updated to output clean `N/A` strings instead of `nan`, `parse_rim` regex must be updated to accept `N/A` across all numeric columns.
6. **[From Obs 1.1 & 1.2]** By:
   - (a) Explicitly tagging missing fundamentals (`'MISSING_FUNDAMENTALS'`) and capital impairment (`'CAPITAL_IMPAIRMENT'`) in `compute_rim_scores`,
   - (b) Leaving uncomputable metrics as `np.nan` rather than fake `8.0%` / `100%`,
   - (c) Filtering `_write_rim_file` to only rank valid computable stocks (`df_rim['rim_score'].notna() & (df_rim['rim_score'] > 0)`),
   - (d) Replacing any fallback text strings `"nan"` / `"nan%"` with `"N/A"` or `"데이터 없음"`, and
   - (e) Updating `generate_report.py` regex and UI badges,
   we completely eliminate all `nan` and `nan%` outputs and establish clean, mathematically sound valuation status handling.

---

## 3. Caveats

1. **Fundamental Data Availability**: In newly initialized testing environments or markets with minimal test universes (e.g., single ticker without seeded `stock_fundamentals` database records), RIM valuation will legitimately have 0 valid computable stocks. The pipeline must gracefully output `"데이터 없음 (재무데이터 미비 또는 산출 불가)"` without crashing or printing `nan`.
2. **Ensemble Dynamic Re-normalization**: In `src/ai/ensemble_scorer.py`, `rim_score = np.nan` correctly drops `rim_valuation` from the active strategy set for that symbol, dynamically re-normalizing weights across the remaining active strategies. This must remain intact (i.e., uncomputable RIM stocks must maintain `rim_score = np.nan` in dataframes passed to the ensemble).
3. **Multi-Market Scope**: The fix must apply uniformly across all 5 markets (`KOSPI`, `KOSDAQ`, `SP500`, `NASDAQ`, `RUSSELL2000`) and the merged `rim_predictions.txt`.

---

## 4. Conclusion & Concrete Implementation Recommendations

### 4.1 Taxonomy of RIM Valuation Statuses
We recommend standardizing the following 4 valuation classifications:

| Status Code | Tag Display | Condition | Intrinsic $V_0$ | Discount % | RIM Score | Ensemble Action |
|-------------|-------------|-----------|-----------------|------------|-----------|-----------------|
| `VALID` / `QUALITY_ADJUSTED` | `[OK]` / `[ADJ]` | $BPS > 0, P > 0, \text{OpInc} > 0, \text{NetInc} > 0$ | Numeric | Numeric | $0.02 \sim 0.98$ | Included |
| `HOLDING_COMPANY` | `[HC]` | Holding co. name/sector pattern | Adjusted | Adjusted | $0.02 \sim 0.98$ | Included |
| `OPERATING_LOSS` | `OPERATING_LOSS` | $\text{OpInc} < 0$ or $\text{NetInc} < 0$ | `np.nan` | `np.nan` | `np.nan` | Excluded (Weight 0) |
| `LOW_EARNINGS_QUALITY` | `LOW_EARNINGS_QUALITY` | $\text{OpInc} \le 0$ & $\text{NetInc} > 0$ | `np.nan` | `np.nan` | `np.nan` | Excluded (Weight 0) |
| `CAPITAL_IMPAIRMENT` | `CAPITAL_IMPAIRMENT` | $BPS \le 0$ or $\text{BookValue} \le 0$ | `np.nan` | `np.nan` | `np.nan` | Excluded (Weight 0) |
| `PREFERRED_SHARE` | `PREFERRED_SHARE` | Preferred symbol pattern | `np.nan` | `np.nan` | `np.nan` | Excluded (Weight 0) |
| `MISSING_FUNDAMENTALS` | `MISSING_FUNDAMENTALS` | No $BPS$ or fundamental data | `np.nan` | `np.nan` | `np.nan` | Excluded (Weight 0) |

---

### 4.2 Concrete Code Refactoring Proposals

#### Proposal 1: Refactor `src/core/rim_valuation.py`
1. **Explicit Status Tagging in `compute_rim_scores`**:
   ```python
   # Capital Impairment (자본잠식) Detection
   has_negative_equity = pd.Series(False, index=df.index)
   if 'bps' in df.columns:
       bps_raw = pd.to_numeric(df['bps'], errors='coerce')
       has_negative_equity = has_negative_equity | (bps_raw <= 0)
   if 'book_value' in df.columns:
       bv_raw = pd.to_numeric(df['book_value'], errors='coerce')
       has_negative_equity = has_negative_equity | (bv_raw <= 0)
   df.loc[has_negative_equity & (df['rim_filter_reason'] == ''), 'rim_filter_reason'] = 'CAPITAL_IMPAIRMENT'

   # Missing Fundamentals (재무데이터미비) Detection
   missing_fund = df['bps'].isna() & (df['rim_filter_reason'] == '')
   df.loc[missing_fund, 'rim_filter_reason'] = 'MISSING_FUNDAMENTALS'
   ```
2. **Prevent Misleading ROE / EQ Imputation on Missing Fundamentals**:
   - Keep `roe_raw = np.nan` and `earnings_quality = np.nan` when `rim_filter_reason == 'MISSING_FUNDAMENTALS'`.
3. **Ensure All Invalid Filter Reasons Invalidate Scores**:
   ```python
   invalid_mask = df['rim_filter_reason'].isin([
       'MISSING_FUNDAMENTALS', 'CAPITAL_IMPAIRMENT',
       'LOW_EARNINGS_QUALITY', 'PREFERRED_SHARE', 'OPERATING_LOSS'
   ]) | df['bps'].isna() | (df['bps'] <= 0)

   df.loc[invalid_mask, ['rim_score', 'discount_ratio', 'intrinsic_value']] = np.nan
   ```

---

#### Proposal 2: Refactor `run_pipeline.py` (`_write_rim_file`)
1. **Filter to Valid Computable Stocks for Ranking**:
   ```python
   def _write_rim_file(f_out, df_rim):
       f_out.write("=== Strategy 9: RIM (Residual Income Model) Valuation Predictions ===\n")
       f_out.write(f"Date: {date_str}\n")
       valid_rim = df_rim[df_rim['rim_score'].notna() & (df_rim['rim_score'] > 0)]
       f_out.write(f"Total symbols evaluated: {len(df_rim)} (Valid: {len(valid_rim)})\n")
       f_out.write("Filters: EQ=Earnings Quality | [ADJ]=Extreme ROE normalized | [HC]=Holding Co. discount\n\n")
       
       if valid_rim.empty:
           f_out.write("데이터 없음 (유효한 RIM 적정가 산출 대상 종목 없음)\n")
           return

       f_out.write(
           f"{'Rank':<5}{'Symbol':<10}{'Name':<20}{'Market':<10}"
           f"{'Price':<12}{'Intrinsic V0':<14}{'Discount %':<12}"
           f"{'ROE_raw':<9}{'ROE_adj':<9}{'EQ':<6}{'Filter':<32}{'RIM Score':<12}\n"
       )
       f_out.write("-" * 142 + "\n")
       for rank, (_, row) in enumerate(valid_rim.head(100).iterrows(), 1):
           name_str = str(row.get('name', 'Unknown'))[:18] if pd.notna(row.get('name')) else "Unknown"
           price_val = row.get('Close', np.nan)
           price_str = f"{price_val:<12.2f}" if pd.notna(price_val) and np.isfinite(price_val) else f"{'N/A':<12}"
           
           intrinsic = row.get('intrinsic_value', np.nan)
           intrinsic_str = f"{intrinsic:<14.2f}" if pd.notna(intrinsic) and np.isfinite(intrinsic) else f"{'N/A':<14}"
           
           disc_val = row.get('discount_ratio', np.nan)
           disc_str = f"{disc_val*100:>9.1f}%" if pd.notna(disc_val) and np.isfinite(disc_val) else "      N/A"
           
           roe_raw = row.get('roe_raw', np.nan)
           roe_adj = row.get('roe', np.nan)
           roe_raw_str = f"{roe_raw*100:>7.1f}%" if pd.notna(roe_raw) and np.isfinite(roe_raw) else "    N/A"
           roe_adj_str = f"{roe_adj*100:>7.1f}%" if pd.notna(roe_adj) and np.isfinite(roe_adj) else "    N/A"
           
           eq = row.get('earnings_quality', np.nan)
           eq_str = f"{eq*100:>5.0f}%" if pd.notna(eq) and np.isfinite(eq) else "  N/A"
           
           filter_reason = str(row.get('rim_filter_reason', ''))
           hc_flag = bool(row.get('holding_co_flag', False))
           tag_parts = []
           if 'ROE_NORMALIZED' in filter_reason or 'QUALITY_ADJUSTED' in filter_reason:
               tag_parts.append('[ADJ]')
           if hc_flag:
               tag_parts.append('[HC]')
           if filter_reason and filter_reason not in ('', 'QUALITY_ADJUSTED', 'EXTREME_ROE_NORMALIZED', 'QUALITY_ADJUSTED+ROE_NORMALIZED'):
               tag_parts.append(filter_reason[:22])
           filter_str = ' '.join(tag_parts)[:30]
           
           rim_score_val = row.get('rim_score', np.nan)
           rim_score_str = f"{rim_score_val*100:>9.1f}%" if pd.notna(rim_score_val) and np.isfinite(rim_score_val) else "      N/A"
           
           f_out.write(
               f"{rank:<5}{row['symbol']:<10}{name_str:<20}{row['market']:<10}"
               f"{price_str}{intrinsic_str}{disc_str}"
               f" {roe_raw_str} {roe_adj_str} {eq_str}  {filter_str:<32}{rim_score_str}\n"
           )
   ```

---

#### Proposal 3: Refactor `generate_report.py` (`parse_rim`)
Update `parse_rim` regular expression to match both valid numbers, `N/A`, and `-` gracefully:
```python
m12 = re.match(
    r"^(\d+)\s+(\S+)\s+(.+?)\s+(KOSPI|KOSDAQ|SP500|NASDAQ|RUSSELL2000|KONEX|[A-Za-z0-9_]+)\s+"
    r"([-\d.]+|N/A|-|nan|NaN)\s+([-\d.]+|N/A|-|nan|NaN)\s+([-+\d.%]+|N/A|-|nan%|NaN%)\s+"
    r"([-+\d.%]+|N/A|-|nan%|NaN%)\s+([-+\d.%]+|N/A|-|nan%|NaN%)\s+([-+\d.%]+|N/A|-|nan%|NaN%)"
    r"(?:\s+(.*?))?\s+([-+\d.%]+|N/A|-|nan%|NaN%)$",
    line
)
```

---

## 5. Verification Method

### 5.1 Automated Unit & Stress Tests
1. Run full test suite:
   ```bash
   .venv\Scripts\pytest tests\test_rim_strategy.py tests\test_challenger_rim_2_stress.py tests\test_kst_and_coverage_reasoning.py -v
   ```
2. Verify:
   - All 26+ tests pass with 0 failures.
   - Text output generated by `_write_rim_file` contains 0 instances of `"nan"` or `"nan%"`.
   - `parse_rim` parses both valid numeric rows and `N/A` fields without data corruption.

### 5.2 Output Artifact File Verification
1. Inspect generated text files:
   - `trading_system/result/rim_predictions.txt`
   - `trading_system/result/rim_predictions_*.txt`
2. Assert:
   - No occurrences of the substring `"nan"` or `"nan%"` in any prediction line.
   - For empty markets, display clean `"데이터 없음 (유효한 RIM 적정가 산출 대상 종목 없음)"`.
