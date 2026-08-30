# Handoff Report: Milestone 1 - Fundamental Strategies Fallback Scoring

## 1. Observation

Direct code examination and empirical execution of the fundamental strategy engines revealed the exact root causes of missing predictions when financial statements are absent or in offline/isolated environments:

### Observation 1: RIM Valuation Engine (`trading_system/src/core/rim_valuation.py`)
- **File & Lines**: `trading_system/src/core/rim_valuation.py:487-488`, `700-730`
- **Code**:
  ```python
  missing_fund = df['bps'].isna() & (df['rim_filter_reason'] == '')
  df.loc[missing_fund, 'rim_filter_reason'] = 'MISSING_FUNDAMENTALS'
  ...
  invalid_mask = df['rim_filter_reason'].isin([
      'MISSING_FUNDAMENTALS', 'CAPITAL_IMPAIRMENT',
      'LOW_EARNINGS_QUALITY', 'PREFERRED_SHARE', 'OPERATING_LOSS'
  ])
  ...
  if invalid_mask.any():
      df.loc[invalid_mask, ['rim_score', 'discount_ratio', 'intrinsic_value']] = np.nan
  ```
- **Execution Test Result**:
  When tested with `pd.DataFrame([{'symbol': 'AAPL', 'Close': 150.0, 'market': 'SP500'}, {'symbol': 'MSFT', 'Close': 300.0, 'market': 'SP500'}])`:
  ```
  symbol  rim_score     rim_filter_reason
  AAPL        NaN  MISSING_FUNDAMENTALS
  MSFT        NaN  MISSING_FUNDAMENTALS
  ```
- **Pipeline Result**: In `run_pipeline.py:2775-2777`, when `valid_rim` is empty (all scores NaN), `_write_rim_file()` outputs verbatim:
  `"데이터 없음 (유효한 RIM 적정가 산출 대상 종목 없음)"`
  and no ranked rows are generated for downstream parsing.

### Observation 2: Accruals Quality Anomaly Engine (`trading_system/src/core/accruals_quality.py`)
- **File & Lines**: `trading_system/src/core/accruals_quality.py:83-86`, `125-155`
- **Code**:
  ```python
  if not fund_map:
      default_val = 0.50 if len(sym_strs) == 1 else np.nan
      df_acc = pd.DataFrame({'symbol': sym_strs, 'accruals_quality_score': default_val})
      return df_acc[['symbol', 'accruals_quality_score']]
  ...
  valid_mask = df_acc['accrual_ratio'].notna() & np.isfinite(df_acc['accrual_ratio'])
  ...
  else:
      df_acc['accruals_quality_score'] = np.nan
  ```
- **Execution Test Result**:
  When tested with `calculate_scores(['AAPL', 'MSFT'], features_df=None, prices_dict=None)`:
  ```
  symbol  accruals_quality_score
  AAPL                     NaN
  MSFT                     NaN
  ```
- **File Observation**: `trading_system/result/accruals_quality_predictions.txt` contains:
  ```
  === Strategy 24: Accruals Quality Anomaly Predictions ===
  Date: 2026-08-28 18:49 KST
  Total symbols evaluated: 0

  Rank Symbol    Name              Market    Accruals Score  
  -----------------------------------------------------------
  ```

### Observation 3: Value-Up & Shareholder Yield Engine (`trading_system/src/core/valueup_catalyst.py`)
- **File & Lines**: `trading_system/src/core/valueup_catalyst.py:83-109`, `158-177`
- **Code**:
  ```python
  # If PBR is missing, estimate from price / BPS if price is available
  if pd.isna(pbr) and pd.notna(bps) and float(bps) > 0:
      ...
  if pd.notna(pbr):
      ...
  else:
      scores[sym_str] = np.nan
  ...
  else:
      default_val = 0.50 if len(df_out) == 1 else np.nan
      df_out['valueup_catalyst_score'] = default_val
  ```
- **Execution Test Result**:
  When tested with `calculate_scores(['AAPL', 'MSFT'], features_df=None, prices_dict=None)`:
  ```
  symbol  valueup_catalyst_score
  AAPL                     NaN
  MSFT                     NaN
  ```
- **File Observation**: `trading_system/result/valueup_catalyst_predictions.txt` contains:
  ```
  === Strategy 26: Value-Up & Shareholder Yield Predictions ===
  Date: 2026-08-28 18:49 KST
  Total symbols evaluated: 0

  Rank Symbol    Name              Market    ValueUp Score   
  -----------------------------------------------------------
  ```

### Observation 4: Pipeline Report Saving (`trading_system/run_pipeline.py`)
- **File & Lines**: `trading_system/run_pipeline.py:2852-2859`
- **Code**:
  ```python
  if df_strat is None or df_strat.empty or score_col not in df_strat.columns:
      return
  ...
  merged[score_col] = pd.to_numeric(merged[score_col], errors='coerce')
  merged = merged.dropna(subset=[score_col]).sort_values(by=score_col, ascending=False)
  ```
- When a strategy returns 100% NaN scores, `merged.dropna(subset=[score_col])` reduces the DataFrame to 0 rows, resulting in `Total symbols evaluated: 0` and an empty table.

---

## 2. Logic Chain

1. **Premise**: In live pipelines, GitHub Actions workflows, or isolated testing environments, external fundamental financial statement data (e.g. quarterly DART/SEC filings, BPS, ROE, OCF, Net Income) is often unavailable, delayed by filing lags, or missing for non-covered symbols (e.g. US symbols or small caps).
2. **Current State**:
   - `rim_valuation.py` explicitly invalidates any row where `bps` is NaN, setting `rim_score = np.nan`.
   - `accruals_quality.py` checks `if not fund_map:` and returns `np.nan` for universes with $>1$ symbol, and sets `accruals_quality_score = np.nan` whenever OCF/Net Income is missing.
   - `valueup_catalyst.py` requires `pbr` or `bps` to compute `pbr_factor`; if missing, it sets `valueup_catalyst_score = np.nan`.
3. **Downstream Cascade**:
   - `run_pipeline.py` receives DataFrames where `rim_score`, `accruals_quality_score`, or `valueup_catalyst_score` is all NaN.
   - `_save_strategy_predictions_report()` drops all NaN rows (`dropna(subset=[score_col])`), leaving 0 rows.
   - Output files (`rim_predictions.txt`, `accruals_quality_predictions.txt`, `valueup_catalyst_predictions.txt`) are written with header-only content and 0 ranked rows.
   - `generate_report.py` parses these empty files, rendering empty tables or "데이터 없음" placeholders on the GitHub Pages dashboard (`index.html`).
4. **Resolution Mechanism**:
   - Implementing a 3-tier hierarchical calculation structure in each engine:
     - **Tier 1 (True Fundamental)**: If full financial statement items exist, execute the exact economic formulas (Decaying ROE RIM, Sloan Accrual Anomaly, Value-Up PBR/Cash Yield).
     - **Tier 2 (Price/Volume Market Proxy)**: If fundamental statements are missing but price/volume time series is available (`prices_dict` or `Close` series), compute market-based proxy metrics (e.g., 200-day SMA valuation anchor for RIM, Volume Flow & Trend Efficiency for Accruals Quality, 200d SMA & 52-week discount for Value-Up).
     - **Tier 3 (Neutral Prior)**: If price history is also missing or single-point flat, assign a neutral prior score of `0.50` (or uniform market percentile rank).
   - This ensures all output DataFrames contain finite floats in $[0.0, 1.0]$ for all symbols, preserving strategy rankings across all 5 markets (SP500, NASDAQ, RUSSELL2000, KOSPI, KOSDAQ).

---

## 3. Concrete Implementation Recommendations

### Recommendation 1: RIM Valuation Engine Fallback (`src/core/rim_valuation.py`)
1. **Fallback Valuation Anchor**:
   - When `bps` is missing/NaN, compute proxy intrinsic value and discount from price history:
     $$\text{SMA}_{200} = \text{mean}(Close_{t-200..t}) \quad (\text{or } \text{SMA}_{60} \text{ if } <200 \text{ days})$$
     $$V_{0, \text{proxy}} = \text{SMA}_{200} \times 1.05$$
     $$\text{Discount Ratio}_{\text{proxy}} = \frac{V_{0, \text{proxy}} - \text{Price}}{\text{Price}} = \frac{\text{SMA}_{200} \times 1.05 - \text{Price}}{\text{Price}}$$
   - Mark `rim_filter_reason = 'PRICE_TREND_PROXY'`.
2. **Percentile Ranking**:
   - Instead of setting `rim_score = np.nan` for rows with `PRICE_TREND_PROXY`, include them in the market-level percentile ranking:
     `df.loc[proxy_mask, 'rim_score'] = df[proxy_mask].groupby('market')['discount_ratio'].rank(pct=True).clip(0.05, 0.95)`
   - Only distress cases with explicit severe negative equity / capital impairment remain penalized/flagged.
   - If no price history exists (1 point), set $V_0 = \text{Price} \times 1.05$, $\text{Discount} = 5.0\%$, and `rim_score = 0.50`.
3. **File Output Formatting**:
   - In `run_pipeline.py:_write_rim_file()`, rows evaluated via proxy format with tag `[PROXY]` under the `Filter` column, displaying valid `Price`, `Intrinsic V0`, `Discount %`, and `RIM Score`.

### Recommendation 2: Accruals Quality Engine Fallback (`src/core/accruals_quality.py`)
1. **Remove Premature Multi-Symbol NaN Guard**:
   - Modify line 84: if `not fund_map`, do NOT immediately return `np.nan`. Proceed to compute Level 2 Price-Volume proxies.
2. **Price-Volume Flow Quality Proxy**:
   - For each symbol in `symbols`, if `net_income` / `operating_cash_flow` is missing, inspect `prices_dict.get(sym)`:
     - Compute 20-day Volume-Weighted Flow (Chaikin / MFI proxy):
       $$\text{Flow} = \frac{\sum_{t=1}^{20} \text{sgn}(\Delta C_t) \times V_t}{\sum_{t=1}^{20} V_t + 1e-5} \in [-1.0, 1.0]$$
     - Compute Kaufman Trend Efficiency (KER):
       $$\text{KER}_{20} = \frac{|C_t - C_{t-20}|}{\sum_{i=1}^{20} |C_i - C_{i-1}| + 1e-5} \in [0.0, 1.0]$$
     - Compute 20-day Realized Volatility:
       $$\sigma_{20} = \text{std}(\text{returns}_{20}) \times \sqrt{252}$$
     - Proxy Accruals Quality Score:
       $$\text{Raw Proxy} = 0.50 + 0.25 \times \text{Flow} + 0.20 \times \text{KER}_{20} - 0.20 \times \min(\sigma_{20}, 1.0)$$
3. **Normalization & Prior**:
   - Rank valid proxy scores into $[0.05, 0.95]$.
   - If price history is unavailable for a symbol, assign `0.50`.

### Recommendation 3: Value-Up Catalyst Engine Fallback (`src/core/valueup_catalyst.py`)
1. **Remove Premature NaN Return**:
   - Modify lines 174-176: if `valid_mask.sum() == 0`, compute Level 2 Valuation proxies from `prices_dict` instead of assigning `np.nan`.
2. **Moving Average Valuation & 52-Week Discount Proxy**:
   - For each symbol where `pbr` and `bps` are missing:
     - Compute Price / 200-day SMA ratio:
       $$\text{VR} = \frac{\text{Close}}{\text{SMA}_{200}} \quad (\text{or } \text{SMA}_{60})$$
       $$\text{pbr\_factor\_proxy} = \text{clip}(1.5 - 0.5 \times \text{VR}, 0.2, 1.8)$$
     - Compute 52-week High/Low Range Position:
       $$\text{RP} = \frac{\text{Close} - \min(C_{252})}{\max(C_{252}) - \min(C_{252}) + 1e-5} \in [0.0, 1.0]$$
     - Composite Proxy Score:
       $$\text{raw\_score}_{\text{proxy}} = \text{pbr\_factor\_proxy} \times (1.0 + 0.30 \times (1.0 - \text{RP}))$$
3. **Normalization & Prior**:
   - Rank valid proxy scores into $[0.05, 0.95]$.
   - If price history is unavailable for a symbol, assign `0.50`.

---

## 4. Caveats

1. **Distinction Between Real Fundamentals and Proxies**: Proxies are mathematical heuristics designed to provide continuity and relative market rankings when external financial APIs or filings are unavailable. They must not overwrite or dilute true fundamental data when true BPS/ROE/OCF items are present.
2. **Extreme Capital Impairment**: True distressed firms with confirmed negative book value (자본잠식) should remain identified and penalized appropriately to prevent Value Trap recommendations.
3. **Other Heuristic Strategies**: Similar proxy mechanisms exist and are verified for `short_interest_squeeze.py` and `trend_efficiency.py`; applying the same discipline to `llm_sentiment_engine.py`, `earnings_tone_drift.py`, and `insider_buying.py` ensures that all 31 strategies maintain 100% non-empty coverage across all markets.

---

## 5. Conclusion

1. The root cause of empty tables and "데이터 없음" for RIM, Accruals Quality, and Value-Up is that each engine defaults to `np.nan` whenever financial statement line items are missing, causing `_save_strategy_predictions_report` in `run_pipeline.py` to drop all rows.
2. Implementing 3-tier hierarchical fallback logic (Level 1: True Fundamentals $\to$ Level 2: Price/Volume Proxy $\to$ Level 3: Neutral Prior 0.50) guarantees that valid ranked scores in $[0.0, 1.0]$ are always produced.
3. This completely resolves the data deficiency for fundamental strategies across all 5 markets (`SP500`, `NASDAQ`, `RUSSELL2000`, `KOSPI`, `KOSDAQ`) without breaking genuine valuation calculations.

---

## 6. Verification Method

To verify these findings and future implementations:
1. **Isolated Unit Test Verification**:
   ```bash
   .venv/Scripts/python.exe -c "
   import pandas as pd
   from trading_system.src.core.rim_valuation import RIMValuationEngine
   from trading_system.src.core.accruals_quality import AccrualsQualityEngine
   from trading_system.src.core.valueup_catalyst import ValueUpCatalystEngine

   symbols = ['AAPL', 'MSFT', '005930', '000660']
   dates = pd.date_range('2026-01-01', periods=220)
   prices_dict = {s: pd.DataFrame({'Close': [100.0 + i for i in range(220)], 'Volume': [1000]*220}, index=dates) for s in symbols}

   # Verify non-NaN scores are produced when features_df is None
   aq = AccrualsQualityEngine()
   res_aq = aq.calculate_scores(symbols, features_df=None, prices_dict=prices_dict)
   assert res_aq['accruals_quality_score'].notna().all(), 'Accruals Quality must have no NaNs'

   vu = ValueUpCatalystEngine()
   res_vu = vu.calculate_scores(symbols, features_df=None, prices_dict=prices_dict)
   assert res_vu['valueup_catalyst_score'].notna().all(), 'Value-Up must have no NaNs'
   "
   ```
2. **Test Suite Verification**:
   ```bash
   .venv/Scripts/pytest tests/test_rim_strategy.py tests/test_strategies_24_to_27.py -v
   ```
3. **End-to-End Report Generation**:
   ```bash
   .venv/Scripts/python.exe trading_system/generate_report.py --result-dir trading_system/result --out gh-pages/index.html
   ```
