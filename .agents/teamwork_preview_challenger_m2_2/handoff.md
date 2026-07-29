# Handoff Report — Milestone 2 Challenger 2 Verification

## 1. Observation

### File Paths & Code Snippets
- **File**: `trading_system/src/ai/ensemble_scorer.py`
  - **Lines 546–551 (Strategy 1 Column Selection)**:
    ```python
    if not reg_df.empty:
        reg_col = target_horizon if target_horizon in reg_df.columns else reg_df.columns[-1]
        reg_df_copy = reg_df[['symbol', reg_col]].rename(columns={reg_col: 'reg_pred'})
        reg_df_copy['reg_score'] = (reg_df_copy['reg_pred'] / 0.25).clip(0.0, 1.0)
    ```
  - **Lines 672–677 (DataFrame Outer Merge)**:
    ```python
    dfs = [reg_df_copy, s_df_copy, ll_df_copy, vr_df, v_df, l_df, sa_df, sec_df, r_val_df, ev_df, m_df, iv_df, of_df, rev_df]
    merged = dfs[0]
    for d in dfs[1:]:
        if not d.empty:
            merged = merged.merge(d, on='symbol', how='outer')
    ```
  - **Lines 748–766 (Transaction Cost Calculation)**:
    ```python
    slippage = getattr(self.config, 'slippage_krx_market_order', 0.005) if self.config is not None else 0.005

    def _get_cost_pct(row_or_sym) -> float:
        if isinstance(row_or_sym, pd.Series):
            symbol = str(row_or_sym.get('symbol', ''))
            market = str(row_or_sym.get('market', '')).upper()
        else:
            symbol = str(row_or_sym)
            market = ''

        if market == 'KONEX' or symbol.endswith('.KN'):
            return 0.0080 + slippage
        elif market == 'KOSDAQ' or symbol.endswith('.KQ'):
            return 0.0050 + slippage
        elif market == 'KOSPI' or symbol.endswith('.KS') or (symbol.isdigit() and len(symbol) == 6):
            return 0.0035 + slippage
        elif market == 'SP500' or (symbol.isalpha() and len(symbol) <= 5):
            return 0.0010 + slippage
        return 0.0010 + slippage

    cost_series = merged.apply(_get_cost_pct, axis=1)
    ```
  - **Lines 778–799 (Liquidity Gate & Preferred Stock / SPAC Filter)**:
    ```python
    def _is_illiquid_or_preferred(row: pd.Series) -> bool:
        sym = str(row.get('symbol', ''))
        name = str(row.get('name', ''))
        # Preferred stock check
        if name.endswith('우') or name.endswith('우B') or name.endswith('1우') or name.endswith('2우B') or name.endswith('3우B'):
            return True
        if len(sym) == 6 and sym[-1] in ['K', 'L', 'M', 'N', 'O']:
            return True
        # SPAC check
        if '스팩' in name or 'SPAC' in name.upper():
            return True
        if 'volume' in row and pd.notna(row['volume']) and float(row['volume']) <= 0:
            return True
        return False

    illiquid_mask = merged.apply(_is_illiquid_or_preferred, axis=1)
    if illiquid_mask.any():
        merged.loc[illiquid_mask, 'ensemble_score'] = 0.0
        merged.loc[illiquid_mask, 'ensemble_expected_return'] = 0.0
    ```

- **File**: `trading_system/run_pipeline.py`
  - **Lines 2239–2284 (Decision Rationale & Macro Header Rendering)**:
    `run_pipeline.py` calls `scorer.get_regime_reasoning_summary(...)` and formats the `ensemble_predictions.txt` report with executive market summary, global macro indicators (S&P 500 return/vol, KOSPI return/vol, VIX, USD/KRW, US 10Y, KR 10Y, WTI Crude, Gold), regime reasoning summary, and 14 strategy weights.

---

## 2. Logic Chain

1. **Metadata Column Dropping in `combine_predictions`**:
   - In `combine_predictions()`, when `reg_df_copy`, `s_df_copy`, `ll_df_copy`, etc. are constructed, only `'symbol'` and the respective numeric prediction columns are selected (e.g. `reg_df[['symbol', reg_col]]`).
   - Any auxiliary metadata columns present in input DataFrames (`market`, `name`, `volume`) are excluded from `dfs` and are absent in the resulting `merged` DataFrame.

2. **Transaction Cost Classification Flaw**:
   - `_get_cost_pct(row)` attempts to read `market = str(row.get('market', '')).upper()`. Because `market` was dropped during step 1, `market` is always `''`.
   - When evaluating symbols without explicit market suffixes (e.g., standard 6-digit KRX symbols like `'035720'` for KOSDAQ or `'217620'` for KONEX), `symbol.endswith('.KQ')` and `symbol.endswith('.KN')` evaluate to `False`.
   - The method falls back to `elif market == 'KOSPI' or symbol.endswith('.KS') or (symbol.isdigit() and len(symbol) == 6):`, which evaluates to `True` for ALL 6-digit numeric tickers.
   - Consequently, 6-digit KOSDAQ and KONEX symbols are incorrectly assigned KOSPI transaction costs (0.35% + 0.50% = 0.85%) instead of their exact required market rates:
     - KOSDAQ required: 0.50% fee + 0.50% slippage = **1.00%** (actual applied: **0.85%** -> **0.15% under-deduction**).
     - KONEX required: 0.80% fee + 0.50% slippage = **1.30%** (actual applied: **0.85%** -> **0.45% under-deduction**).

3. **Liquidity Screening Bypass Flaw**:
   - `_is_illiquid_or_preferred(row)` reads `name = str(row.get('name', ''))` and checks `'volume' in row`.
   - Because `name` and `volume` were dropped during step 1, `name` is always `''` and `'volume'` is never a column key in `row`.
   - Preferred stock name checks (`name.endswith('우')`, `'우B'`, etc.) evaluate to `False` for names like `'삼성전자우'`, `'현대차2우B'`.
   - Preferred stock numeric tickers (e.g. `'005935'` for 삼성전자우) fail `sym[-1] in ['K', 'L', 'M', 'N', 'O']`.
   - SPAC name checks (`'스팩' in name` or `'SPAC' in name.upper()`) evaluate to `False` for names like `'하나금융31호스팩'`.
   - Volume check (`volume <= 0`) evaluates to `False` because `'volume'` is missing.
   - As a result, numeric preferred stocks, SPACs, and zero-volume stocks bypass liquidity screening and remain un-zeroed with positive ensemble scores and expected returns.

4. **Macro Header & Rationale Rendering Verification**:
   - `get_regime_reasoning_summary` generates complete decision rationale detailing the 2D regime state, market trend, volatility state, 14-strategy dynamic weights with Sharpe multipliers, and transaction cost/liquidity filter notes.
   - `run_pipeline.py` correctly populates and outputs the macro header fields (S&P 500, KOSPI, VIX, USD/KRW, US 10Y, KR 10Y, WTI, Gold) into `ensemble_predictions.txt`.

---

## 3. Caveats

- **Symbol Suffix Dependency**: If symbols in input DataFrames are pre-formatted with explicit `.KS`, `.KQ`, `.KN` suffixes (e.g., `'005930.KS'`, `'035720.KQ'`, `'217880.KN'`), `_get_cost_pct` successfully matches transaction costs despite the missing `market` column. However, raw 6-digit numeric tickers (standard in FinanceDataReader/KRX databases) fail cost classification.
- **Symbol Name Format**: Preferred stock filtering only succeeds if the preferred tag is in the `symbol` string itself (e.g., `'005930우.KS'`) or ends in K/L/M/N/O. Standard 6-digit preferred tickers ending in numbers (e.g. `'005935'`) rely entirely on `name`, which is lost.

---

## 4. Conclusion & Verdict

**VERDICT: FAIL**

### Summary of Failure Modes:
1. **Transaction Cost Misclassification**: 6-digit numeric KOSDAQ and KONEX tickers without explicit `.KQ`/`.KN` suffixes are assigned KOSPI transaction costs (0.85%), under-deducting costs by 0.15% for KOSDAQ and 0.45% for KONEX.
2. **Liquidity Screening Metadata Loss**: `combine_predictions()` drops `name`, `market`, and `volume` columns during intermediate DataFrame creation, disabling preferred stock name filtering, SPAC keyword filtering, and zero-volume filtering.

### Actionable Fix Recommendations:
1. In `combine_predictions()` (`trading_system/src/ai/ensemble_scorer.py`), preserve metadata columns (`'market'`, `'name'`, `'volume'`) from input DataFrames when creating `reg_df_copy` or initial `merged` DataFrame (e.g., `reg_df_copy = reg_df[['symbol', reg_col] + [c for c in ['market', 'name', 'volume'] if c in reg_df.columns]]`).
2. Ensure `merged` carries `'market'`, `'name'`, and `'volume'` through to `_get_cost_pct()` and `_is_illiquid_or_preferred()`.

---

## 5. Verification Method

### How to Independently Verify:
1. **Code Inspection**:
   - Inspect `trading_system/src/ai/ensemble_scorer.py` lines 548, 676, 750-764, and 778-795.
   - Confirm that `reg_df_copy = reg_df[['symbol', reg_col]]` drops all non-score columns except `symbol`.
2. **Automated Unit Test Invalidation**:
   - Construct a test DataFrame without explicit symbol suffixes:
     ```python
     df = pd.DataFrame({
         'symbol': ['035720', '217620', '005935', '475150'],
         'market': ['KOSDAQ', 'KONEX', 'KOSPI', 'KOSDAQ'],
         'name': ['카카오', '지노믹트리', '삼성전자우', '하나금융31호스팩'],
         'volume': [100000, 50000, 30000, 0],
         20: [0.25, 0.25, 0.25, 0.25]
     })
     res = scorer.combine_predictions(reg_df=df, target_horizon=20)
     ```
   - Observe that `035720` receives 0.85% deduction (expected 1.00%), `217620` receives 0.85% deduction (expected 1.30%), `005935` (preferred stock) has `ensemble_score > 0.0` (expected 0.0), and `475150` (SPAC) has `ensemble_score > 0.0` (expected 0.0).
