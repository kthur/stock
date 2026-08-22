# Comprehensive Forensic Analysis: Strategy #9 RIM (Residual Income Model) Valuation Engine

**Author**: Explorer 1 (`explorer_rim_1`)  
**Date**: 2026-08-22  
**Target Milestone**: Strategy #9 RIM Valuation Engine & Multi-Market Pipeline Fix  
**Scope**: `trading_system/src/core/rim_valuation.py`, `trading_system/run_pipeline.py`, `trading_system/src/data_layer/earnings_data.py`, `trading_system/src/data_layer/indicator_storage.py`, `trading_system/generate_report.py`, `trading_system/merge_predictions.py`

---

## 1. Executive Summary

Strategy #9 RIM (Residual Income Model / 초과이익모형) is an institutional fundamental valuation engine that computes stock intrinsic value ($V_0$) and margin of safety (discount ratio) using a finite-horizon decaying ROE model with retained earnings accumulation:
$$V_0 = \text{BPS}_0 + \sum_{t=1}^N \frac{\text{Excess Income}_t}{(1+r_e)^t}$$
where $\text{Excess Income}_t = \text{BPS}_{t-1} \times (\text{ROE}_{t-1} - r_e)$, $\text{BPS}_t = \text{BPS}_{t-1} + \text{Net Income}_t \times \text{retention\_ratio}$, and $\text{ROE}_t$ decays geometrically toward $r_e$.

In GitHub Actions Run 32496682187, two critical systemic defects corrupted Strategy #9:
1. **Runtime Crash in US Markets (`AttributeError: 'float' object has no attribute 'fillna'`)**:
   In `trading_system/src/core/rim_valuation.py` line 352, `shares = pd.to_numeric(df.get('shares_outstanding', 0.0), errors='coerce').fillna(0.0)` assumed `df.get()` returns a pandas Series. When `shares_outstanding` was absent from `df.columns` (as in NASDAQ and RUSSELL2000 jobs), `df.get('shares_outstanding', 0.0)` returned scalar float `0.0`. Calling `.fillna(0.0)` on a float raised `AttributeError`, causing RIM calculation to skip entirely and leaving `rim_predictions_NASDAQ.txt` and `rim_predictions_RUSSELL2000.txt` missing from build artifacts.
2. **Artificial Value Trap from Synthetic BPS Fabrication (`bps = eps / 0.08`)**:
   In `trading_system/run_pipeline.py` line 2656, when balance sheet `book_value` was missing or zero, the pipeline invented artificial BPS via `bps = eps / 0.08`. For cyclical low-P/E stocks (e.g. 성창기업지주, 계룡건설, HDC현대EP), this hardcoded a $12.5\times$ P/E multiple assumption, generating phantom intrinsic values up to $5\times$ above market price (+300~500% phantom discounts) with 100% Earnings Quality (EQ), severely corrupting cross-sectional rankings.

This report provides the exhaustive forensic evidence, mathematical mechanics, and drop-in code fixes.

---

## 2. Forensic Investigation of Defects

### 2.1 Bug 1: Scalar vs Series Type Failure (`AttributeError: 'float' object has no attribute 'fillna'`)

#### Direct Observation & Root Cause
In `trading_system/src/core/rim_valuation.py` (lines 350–355):
```python
        elif 'book_value' in df.columns:
            bv = pd.to_numeric(df['book_value'], errors='coerce').fillna(0.0)
            shares = pd.to_numeric(df.get('shares_outstanding', 0.0), errors='coerce').fillna(0.0)
            # When shares exist and book_value is aggregate equity, divide by shares
            calculated_bps = np.where(shares > 0, bv / np.maximum(shares, 1.0), bv)
```

- When `shares_outstanding` is **present** in `df.columns`: `df.get('shares_outstanding', 0.0)` returns `df['shares_outstanding']` (a `pd.Series`). `pd.to_numeric(Series)` returns a `pd.Series`, and `.fillna(0.0)` succeeds.
- When `shares_outstanding` is **absent** from `df.columns`: `df.get('shares_outstanding', 0.0)` returns the scalar default `0.0` (a `float`). `pd.to_numeric(0.0, errors='coerce')` returns `0.0` (a `float` or `np.float64`).
- Calling `.fillna(0.0)` on float `0.0` triggers:
  ```
  AttributeError: 'float' object has no attribute 'fillna'
  ```

#### Downstream Pipeline Blast Radius
In `trading_system/run_pipeline.py` (lines 2626–2742):
```python
    try:
        ...
        rim_df = rim_engine.compute_rim_scores(df_rim_input, symbol_market_map=symbol_market)
        ...
        # Per-market suffix files
        for _m in ['KOSPI', 'KOSDAQ', 'SP500', 'NASDAQ', 'RUSSELL2000']:
            ...
            with open(os.path.join(result_dir, f"rim_predictions_{_m}.txt"), "w", encoding="utf-8") as _mf:
                _write_rim_file(_mf, _m_df)
    except Exception as _rim_e:
        logger.warning(f"RIM valuation score calculation skipped: {_rim_e}")
        rim_df = pd.DataFrame()
```
When `compute_rim_scores` crashed on US market data, the `except Exception as _rim_e:` block caught the error and set `rim_df = pd.DataFrame()`. Consequently, neither `rim_predictions.txt` nor `rim_predictions_NASDAQ.txt` nor `rim_predictions_RUSSELL2000.txt` were generated.

#### Additional Type-Unsafe Locations Identified in `rim_valuation.py`
1. **Line 345: Unsafe Close Price Extraction**:
   ```python
   if 'Close' not in df.columns:
       df['Close'] = df.get('price', np.nan)
   ```
   If `'close'` (lowercase) is passed (common in raw OHLCV dicts), it is ignored and `df['Close']` is filled with `NaN`. Must check `['Close', 'close', 'price', 'Close_price']`.
2. **Line 356: Non-Coerced Division**:
   ```python
   elif 'eps' in df.columns and 'roe' in df.columns:
       calculated_bps = (df['eps'] / df['roe']).replace([np.inf, -np.inf, 0.0], np.nan)
   ```
   If `df['eps']` or `df['roe']` has `object` dtype (e.g. string numbers from database or JSON), python raises `TypeError: unsupported operand type(s) for /: 'str' and 'str'`.
3. **Lines 378, 383: Missing Pre-Coercion on ROE**:
   ```python
   df['roe'] = df['roe'].replace([np.inf, -np.inf], np.nan).fillna(self.default_required_return)
   ```
   If `df['roe']` is object dtype, `.clip(-0.5, 0.5)` raises `TypeError: '<=' not supported between instances of 'float' and 'str'`.
4. **Lines 394–395: Operating/Net Income Coercion**:
   `df['operating_income']` and `df['net_income']` must be explicitly coerced with `pd.to_numeric(..., errors='coerce')` before numpy array operations.
5. **Lines 323–326: Schema Discrepancy on Empty DataFrame**:
   Empty DataFrame returns only 10 columns instead of all 15 output columns (`bps_adjusted`, `earnings_quality`, `holding_co_flag`, `net_debt_per_share`, `rim_filter_reason` missing).

---

### 2.2 Bug 2: Synthetic BPS Fabrication (`bps = eps / 0.08`) & The 300~500% Phantom Discount Value Trap

#### Exact Code Locations
1. **`trading_system/run_pipeline.py` (lines 2654–2656)**:
   ```python
   # Fallback BPS from eps when book_value unavailable
   no_bps = fund_df['bps'].isna() & fund_df['eps'].notna()
   fund_df.loc[no_bps, 'bps'] = fund_df.loc[no_bps, 'eps'] / 0.08
   ```
2. **`trading_system/src/core/rim_valuation.py` (lines 355–357, 362–367)**:
   ```python
   elif 'eps' in df.columns and 'roe' in df.columns:
       calculated_bps = (df['eps'] / df['roe']).replace([np.inf, -np.inf, 0.0], np.nan)
   ...
   nan_mask = df['bps'].isna()
   if nan_mask.any() and 'eps' in df.columns and 'roe' in df.columns:
       pos_mask = nan_mask & (df['eps'] > 0) & (df['roe'] > 0)
       if pos_mask.any():
           fallback = (df.loc[pos_mask, 'eps'] / df.loc[pos_mask, 'roe']).replace([np.inf, -np.inf], np.nan)
           df.loc[pos_mask, 'bps'] = fallback
   ```

#### Mathematical Anatomy of the Phantom Discount Trap
Consider a cyclical or deep-value stock (e.g. 건설/화학/지주사, such as 성창기업지주, 계룡건설, HDC현대EP) trading at a low P/E:
- Market Price: $P = 2,000\text{ KRW}$
- Actual P/E Ratio: $\text{P/E} = 2.5$
- Genuine $\text{EPS} = \frac{P}{\text{P/E}} = 800\text{ KRW}$
- Balance sheet data (`book_value`) is temporarily missing in SQLite cache.

**What the flawed code did:**
1. Fabricated BPS:
   $$\text{BPS}_{\text{synthetic}} = \frac{\text{EPS}}{0.08} = \frac{800}{0.08} = 10,000\text{ KRW}$$
2. Because `book_value` was missing, `fund_df['roe']` was NaN. In `rim_valuation.py` line 378, missing ROE defaulted to $r_e = 0.08$ ($8.0\%$).
3. Under $\text{ROE} = r_e = 0.08$, excess residual income is zero ($\text{ROE} - r_e = 0$). Intrinsic value collapses to:
   $$V_0 = \text{BPS}_{\text{synthetic}} = 10,000\text{ KRW}$$
4. Computed Discount Ratio:
   $$\text{Discount Ratio} = \frac{V_0 - P}{P} = \frac{10,000 - 2,000}{2,000} = +400.0\% !$$
5. Because `operating_income` was not joined (missing balance sheet / income row), `earnings_quality` defaulted to $1.0$ ($100\%$), evading the Earnings Quality filter!

**Why this is catastrophic:**
- The formula $\text{BPS} = \text{EPS} / 0.08$ is algebraically identical to assuming every stock has an intrinsic P/E multiple of $\frac{1}{0.08} = 12.5\times$.
- Any company trading at $\text{P/E} < 12.5$ gets an artificial intrinsic value $V_0 = 12.5 \times \text{EPS} = 12.5 \times \frac{P}{\text{P/E}} = P \times \frac{12.5}{\text{P/E}}$.
- For $\text{P/E} = 2.5$, $V_0 = 5.0 \times P \implies \text{Discount} = +400\%$.
- For $\text{P/E} = 2.0$, $V_0 = 6.25 \times P \implies \text{Discount} = +525\%$.
- Cross-sectional ranking was severely corrupted: authentic high-ROE quality compounders (e.g. Samsung Electronics, Apple) were relegated to lower percentiles, while phantom companies with missing balance sheets swept the top-10 slots with $300\sim 500\%$ discounts.

#### Clean Invalidation Logic
1. **Eliminate All Synthetic BPS**: Delete `fund_df.loc[no_bps, 'bps'] = fund_df.loc[no_bps, 'eps'] / 0.08` from `run_pipeline.py`. Delete `eps / roe` heuristic fallback from `rim_valuation.py`.
2. **Strict BPS Derivation**: BPS must ONLY be accepted if derived from:
   - Genuine `bps` column ($> 0$), OR
   - Genuine `book_value` and `shares_outstanding` ($> 0$), where $\text{BPS} = \frac{\text{book\_value}}{\text{shares\_outstanding}}$.
3. **Invalidation**: When genuine BPS is unavailable, non-positive, or NaN:
   - Set $\text{bps} = \text{NaN}$, $V_0 = \text{NaN}$, $\text{discount\_ratio} = \text{NaN}$, $\text{rim\_score} = \text{NaN}$.
   - The multi-factor `EnsembleScoringEngine` automatically detects NaN and renormalizes the weights of the remaining active strategies without cross-sectional ranking pollution.

---

### 2.3 Value Trap Protections: ROE Normalization, Holding Company SOTP Discount, and Earnings Quality

#### 1. Earnings Quality (EQ) Filtering
- **Formula**:
  $$\text{EQ} = \begin{cases} \text{clip}\left(\frac{\text{Operating Income}}{\text{Net Income}}, 0.0, 1.0\right) & \text{if } \text{Net Income} > 0 \\ 1.0 & \text{otherwise} \end{cases}$$
- **Filtering Rules**:
  - `OPERATING_LOSS`: $\text{Operating Income} < 0$ or $\text{Net Income} < 0 \implies \text{rim\_score} = \text{NaN}$, $\text{roe} = 0.0$.
  - `LOW_EARNINGS_QUALITY`: $\text{Operating Income} \le 0$ and $\text{Net Income} > 0 \implies \text{rim\_score} = \text{NaN}$ (flags companies surviving on one-off asset sales/windfalls).
  - `QUALITY_ADJUSTED`: $\text{EQ} < \text{EARNINGS\_QUALITY\_MIN\_RATIO} (0.50) \implies \text{ROE}_{\text{adj}} = \text{ROE}_{\text{raw}} \times \text{EQ}$.

#### 2. Extreme ROE Normalization
- **Purpose**: Prevent one-off accounting gains (e.g. 염가매수차익, bargain purchase gain on M&A, asset revaluation) from causing perpetual high-ROE compounding in RIM.
- **Stage 1 (Nonrecurring Income Replacement)**:
  - Trigger: $\text{ROE}_{\text{raw}} > \text{EXTREME\_ROE\_THRESHOLD} (20\%)$ AND $\text{EQ} < \text{EXTREME\_EQ\_THRESHOLD} (40\%)$.
  - Action: Replace $\text{ROE}$ with sustainable operating-income-based ROE:
    $$\text{ROE}_{\text{op}} = \text{clip}\left(\frac{\text{Operating Income}}{\text{Book Value}}, 0.0, 0.20\right)$$
    If $\text{ROE}_{\text{op}} < \text{ROE}$, use $\text{ROE}_{\text{op}}$ and tag `[ADJ]`.
- **Stage 2 (Absolute Cap)**:
  - Unconditional upper bound: $\text{ROE} \le \text{ABSOLUTE\_ROE\_CAP} = 0.25$ ($25\%$).

#### 3. Holding Company SOTP Discount (지주사 이중 카운팅 할인)
- **Identification**:
  - Name matches `r"(지주|홀딩스|holding|holdings|그룹|지배구조|HD\b)"` (case-insensitive) OR
  - Sector code in `{"6020", "CGLC", "20202020"}`.
- **Adjustments**:
  1. **Net Debt Deduction**:
     $$\text{BPS}_{\text{adj}} = \max\left(\text{BPS} - \text{Net Debt Per Share}, \text{BPS} \times 0.30\right)$$
     where $\text{Net Debt Per Share} = \frac{\max(0, \text{Total Debt} - \text{Cash Equivalents})}{\text{Shares Outstanding}}$.
  2. **Double-Counting SOTP Discount on Excess Value**:
     $$V_{0, \text{adj}} = \text{BPS}_{\text{adj}} + \max(0, V_{0, \text{raw}} - \text{BPS}) \times (1 - \text{HOLDING\_CO\_DISCOUNT})$$
     where $\text{HOLDING\_CO\_DISCOUNT} = 0.40$ ($40\%$).
  - Tagged with `[HC]`.

---

### 2.4 HTML Report & Downstream Tool Compatibility

#### Investigation of `generate_report.py:parse_rim`
In `trading_system/generate_report.py` lines 625–656:
- `parse_rim` used regex matching 9-column or 8-column text.
- However, `_write_rim_file` in `run_pipeline.py` writes a 12-column format:
  `Rank Symbol Name Market Price Intrinsic Discount ROE_raw ROE_adj EQ Filter RIM_Score`
- Because the regex expected `$` right after Discount and EQ/Score, it could fail to parse rows containing the expanded ROE_raw/ROE_adj/Filter columns.
- **Fix Requirement**: Update `parse_rim` regex to cleanly parse both the 12-column enhanced format (with ROE_raw, ROE_adj, EQ, Filter, and RIM Score) and legacy formats without line loss.

#### Investigation of `indicator_storage.py` Migration
In `trading_system/src/data_layer/indicator_storage.py`:
- `migrations` list in `_init_db` (lines 485–500) has `net_income`, `eps`, `shares_outstanding`, `book_value`, `bps`.
- Missing from migrations: `total_debt`, `cash_equivalents`.
- **Fix Requirement**: Add `("stock_fundamentals", "total_debt", "REAL DEFAULT 0")` and `("stock_fundamentals", "cash_equivalents", "REAL DEFAULT 0")` to `migrations` to ensure legacy SQLite DBs in GHA runners auto-migrate safely.

---

## 3. Recommended Code Changes

### 3.1 `trading_system/src/core/rim_valuation.py`

```python
# In RIMValuationEngine.compute_rim_scores:

        # Ensure Market Column
        if 'market' not in df.columns:
            if symbol_market_map:
                df['market'] = df['symbol'].map(symbol_market_map).fillna('KOSPI')
            else:
                df['market'] = 'KOSPI'
        else:
            df['market'] = df['market'].fillna('KOSPI')

        # Ensure Close / Price with robust column fallback
        if 'Close' not in df.columns:
            for _p_col in ['close', 'price', 'Close_price', 'close_price']:
                if _p_col in df.columns:
                    df['Close'] = pd.to_numeric(df[_p_col], errors='coerce')
                    break
            else:
                df['Close'] = np.nan
        else:
            df['Close'] = pd.to_numeric(df['Close'], errors='coerce')

        # Handle BPS: Strict validation, NO fake eps/0.08 fallback
        if 'bps' in df.columns and pd.to_numeric(df['bps'], errors='coerce').notna().any():
            calculated_bps = pd.to_numeric(df['bps'], errors='coerce')
        elif 'book_value' in df.columns:
            bv = pd.to_numeric(df['book_value'], errors='coerce').fillna(0.0)
            if 'shares_outstanding' in df.columns:
                shares = pd.to_numeric(df['shares_outstanding'], errors='coerce').fillna(0.0)
            else:
                shares = pd.Series(0.0, index=df.index)
            # When shares exist and book_value is aggregate equity, divide by shares
            calculated_bps = np.where(shares > 0, bv / np.maximum(shares, 1.0), bv)
        else:
            calculated_bps = np.nan

        df['bps'] = pd.to_numeric(pd.Series(calculated_bps, index=df.index), errors='coerce').replace([np.inf, -np.inf, 0.0, 0], np.nan)
        df.loc[df['bps'] <= 0, 'bps'] = np.nan

        # Handle ROE
        if 'roe' not in df.columns:
            if 'eps' in df.columns and 'bps' in df.columns:
                eps_num = pd.to_numeric(df['eps'], errors='coerce')
                bps_num = pd.to_numeric(df['bps'], errors='coerce')
                with np.errstate(divide='ignore', invalid='ignore'):
                    df['roe'] = np.where(bps_num > 0, eps_num / bps_num, np.nan)
            else:
                df['roe'] = np.nan
        else:
            df['roe'] = pd.to_numeric(df['roe'], errors='coerce')
        
        df['roe'] = df['roe'].replace([np.inf, -np.inf], np.nan).fillna(self.default_required_return)
        df['roe_raw'] = df['roe'].copy()
        df['roe'] = df['roe'].clip(-0.5, 0.5)
```

### 3.2 `trading_system/run_pipeline.py`

```python
# In run_pipeline.py around line 2650:

        # Compute BPS = book_value / shares_outstanding; 0 book_value → None
        fund_df['bps'] = (pd.to_numeric(fund_df['book_value'], errors='coerce') / 
                          pd.to_numeric(fund_df['shares_outstanding'], errors='coerce')).replace([float('inf'), float('-inf'), 0.0, 0], None)
        # Compute ROE = net_income / book_value; 0 book_value → None
        fund_df['roe'] = (pd.to_numeric(fund_df['net_income'], errors='coerce') / 
                          pd.to_numeric(fund_df['book_value'], errors='coerce')).replace([float('inf'), float('-inf')], None)
        # ELIMINATED: fund_df.loc[no_bps, 'bps'] = fund_df.loc[no_bps, 'eps'] / 0.08 (Fabricated BPS Value Trap)
```

### 3.3 `trading_system/src/data_layer/indicator_storage.py`

```python
# In MarketIndicatorStorage._init_db migrations:
            migrations = [
                ("stock_fundamentals", "net_income", "REAL DEFAULT 0"),
                ("stock_fundamentals", "eps", "REAL DEFAULT 0"),
                ("stock_fundamentals", "shares_outstanding", "REAL DEFAULT 0"),
                ("stock_fundamentals", "book_value", "REAL DEFAULT 0"),
                ("stock_fundamentals", "bps", "REAL DEFAULT 0"),
                ("stock_fundamentals", "total_debt", "REAL DEFAULT 0"),
                ("stock_fundamentals", "cash_equivalents", "REAL DEFAULT 0"),
                ("stock_universe", "sector", "TEXT DEFAULT ''"),
                ("stock_universe", "industry", "TEXT DEFAULT ''"),
                ("stock_universe", "currency", "TEXT DEFAULT 'USD'"),
                ...
            ]
```

### 3.4 `trading_system/generate_report.py`

```python
# Update parse_rim to robustly match 12-column, 9-column, and 8-column formats:
def parse_rim(text: str) -> tuple[str, list[RimRow]]:
    if not text:
        return "", []
    date = ""
    rows: list[RimRow] = []
    for line in text.splitlines():
        line = line.strip()
        m = re.match(r"Date:\s*(.+)", line)
        if m:
            date = m.group(1).strip()
            continue
        if not line or line.startswith("===") or line.startswith("Total") or line.startswith("Filters") or line.startswith("Rank") or line.startswith("---"):
            continue
        parts = line.split()
        if len(parts) >= 8 and parts[0].isdigit():
            try:
                rank = int(parts[0])
                symbol = parts[1]
                score_str = parts[-1] if parts[-1].endswith("%") else parts[-1] + "%"
                # Find market index
                mkt_idx = -1
                for idx, token in enumerate(parts[2:], 2):
                    if token in ("KOSPI", "KOSDAQ", "SP500", "NASDAQ", "RUSSELL2000", "KRX", "US"):
                        mkt_idx = idx
                        break
                if mkt_idx > 2:
                    name = " ".join(parts[2:mkt_idx])
                    market = parts[mkt_idx]
                    price = parts[mkt_idx + 1] if len(parts) > mkt_idx + 1 else "nan"
                    intrinsic = parts[mkt_idx + 2] if len(parts) > mkt_idx + 2 else "nan"
                    discount = parts[mkt_idx + 3] if len(parts) > mkt_idx + 3 else "nan"
                    rows.append(RimRow(
                        rank=rank,
                        symbol=symbol,
                        name=name,
                        market=market,
                        price=price,
                        intrinsic_value=intrinsic,
                        discount=discount,
                        score=score_str
                    ))
            except Exception:
                continue
    return date, rows
```

---

## 4. Verification & Validation Strategy

1. **Unit Test Suite**:
   - Run `.venv/Scripts/python.exe -m pytest tests/test_rim_strategy.py -v` to ensure 100% pass rate.
   - Add new tests:
     - `test_rim_missing_shares_outstanding_column_no_crash`: Verifies DataFrame with `book_value` but no `shares_outstanding` executes cleanly without `AttributeError: 'float' object has no attribute 'fillna'`.
     - `test_rim_missing_bps_invalidation_no_phantom_discount`: Verifies stock with missing `bps` and `book_value` gets `NaN` `rim_score` and `discount_ratio` rather than fabricated $+400\%$ discount.
     - `test_rim_empty_dataframe_schema`: Verifies empty input DataFrame returns all 15 expected output columns.
     - `test_parse_rim_12_column_format`: Verifies `parse_rim` accurately parses 12-column text with `[ADJ]`, `[HC]`, ROE, EQ columns.
2. **Regression & Full Suite**:
   - Run `.venv/Scripts/python.exe -m pytest tests/ -q` to confirm zero regressions across all 1,124+ project unit tests.
3. **Multi-Market Simulation**:
   - Simulate 5-market inference with synthetic/cached prices to verify `rim_predictions_{MARKET}.txt` is cleanly written for all 5 markets (`KOSPI`, `KOSDAQ`, `SP500`, `NASDAQ`, `RUSSELL2000`).
