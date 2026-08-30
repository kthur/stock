# Handoff Report: Pipeline Strategy Report Saving & Multi-Market File Output

- **Agent**: explorer_m1_3
- **Milestone**: Milestone 1 (Strategy Fallback Scoring & Report Saving)
- **Scope**: Pipeline strategy report saving and multi-market file output (`trading_system/run_pipeline.py`)
- **Date**: 2026-08-29

---

## 1. Observation

### 1.1 `_save_strategy_predictions_report()` Implementation in `trading_system/run_pipeline.py`
In `trading_system/run_pipeline.py` lines 2844–2886:
```python
def _save_strategy_predictions_report(
    df_strat: pd.DataFrame,
    score_col: str,
    title: str,
    output_filename: str,
    score_header: str = "Score",
    header_width: int = 14
) -> None:
    if df_strat is None or df_strat.empty or score_col not in df_strat.columns:
        return

    merged = df_strat.merge(universe[['symbol', 'name', 'market']], on='symbol', how='left') if 'market' not in df_strat.columns else df_strat.copy()
    if 'name' not in merged.columns and 'name' in universe.columns:
        merged = merged.merge(universe[['symbol', 'name']], on='symbol', how='left')
    merged[score_col] = pd.to_numeric(merged[score_col], errors='coerce')
    merged = merged.dropna(subset=[score_col]).sort_values(by=score_col, ascending=False)

    def _write_content(f_out, df_sub, market_label=None):
        f_out.write(f"=== {title} ===\n")
        f_out.write(f"Date: {kst_now_str}\n")
        f_out.write(f"Total symbols evaluated: {len(df_sub)}\n\n")
        f_out.write(f"{'Rank':<5}{'Symbol':<10}{'Name':<18}{'Market':<10}{score_header:<{header_width}}\n")
        f_out.write("-" * (43 + header_width) + "\n")
        for rank, (_, row) in enumerate(df_sub.head(100).iterrows(), 1):
            name_str = str(row.get('name', 'Unknown'))[:16] if pd.notna(row.get('name')) else "Unknown"
            mkt_str = str(row.get('market', 'KRX'))
            sc_raw = float(row[score_col])
            sc_val = sc_raw * 100.0 if sc_raw <= 1.0 else sc_raw
            f_out.write(f"{rank:<5}{str(row['symbol']):<10}{name_str:<18}{mkt_str:<10}{sc_val:>{header_width-2}.1f}%\n")

    main_path = os.path.join(result_dir, output_filename)
    with open(main_path, "w", encoding="utf-8") as f:
        _write_content(f, merged)
    logger.info(f"Saved {title} ({len(merged)} symbols) to {main_path}")

    base_name = output_filename.replace(".txt", "")
    for _m in _get_target_markets_to_save(df=merged, universe=universe):
        _m_df = merged[merged['market'] == _m]
        if _m_df.empty:
            continue
        with open(os.path.join(result_dir, f"{base_name}_{_m}.txt"), "w", encoding="utf-8") as _mf:
            _write_content(_mf, _m_df, market_label=_m)
```

### 1.2 Verbatim Examples of 0-Row Files in `trading_system/result/`
Direct inspection of current result artifacts in `trading_system/result/`:
- `sentiment_predictions.txt` (243 bytes, 7 lines):
  ```text
  === Strategy 20: NLP & FinBERT Sentiment Catalyst Predictions ===
  Date: 2026-08-28 18:49 KST
  Total symbols evaluated: 0

  Rank Symbol    Name              Market    Sent Score    
  ---------------------------------------------------------
  ```
- `accruals_quality_predictions.txt` (239 bytes, 7 lines):
  ```text
  === Strategy 24: Accruals Quality Anomaly Predictions ===
  Date: 2026-08-28 18:49 KST
  Total symbols evaluated: 0

  Rank Symbol    Name              Market    Accruals Score  
  -----------------------------------------------------------
  ```
- `earnings_tone_drift_predictions.txt` (238 bytes, 7 lines):
  ```text
  === Strategy 30: Earnings Tone Drift NLP Predictions ===
  Date: 2026-08-28 18:49 KST
  Total symbols evaluated: 0

  Rank Symbol    Name              Market    Tone Score      
  -----------------------------------------------------------
  ```
- `valueup_catalyst_predictions.txt` (243 bytes, 7 lines):
  ```text
  === Strategy 26: Value-Up & Shareholder Yield Predictions ===
  Date: 2026-08-28 18:49 KST
  Total symbols evaluated: 0

  Rank Symbol    Name              Market    ValueUp Score   
  -----------------------------------------------------------
  ```

### 1.3 Root Cause in Strategy Engines Producing All-NaN Outputs
1. **Accruals Quality Engine** (`trading_system/src/core/accruals_quality.py` lines 83–86):
   ```python
   if not fund_map:
       default_val = 0.50 if len(sym_strs) == 1 else np.nan
       df_acc = pd.DataFrame({'symbol': sym_strs, 'accruals_quality_score': default_val})
       return df_acc[['symbol', 'accruals_quality_score']]
   ```
   When `features_df` / `fund_map` is empty for a universe of >1 symbol, all rows receive `np.nan`.
2. **Value-Up Catalyst Engine** (`trading_system/src/core/valueup_catalyst.py` lines 174–176):
   ```python
   else:
       default_val = 0.50 if len(df_out) == 1 else np.nan
       df_out['valueup_catalyst_score'] = default_val
   ```
   When fundamental PBR/BPS is missing, `valid_mask.sum() == 0` and all rows receive `np.nan`.
3. **Earnings Tone Drift Engine** (`trading_system/src/core/earnings_tone_drift.py` lines 109–159):
   When `transcript_map` is empty and `features_df` is empty, every symbol retains `score = np.nan`. `prices_dict` is passed to `calculate_scores` but never used in `compute_tone_drift_scores`.
4. **Insider Buying Engine** (`trading_system/src/core/insider_buying.py` lines 79–125):
   ```python
   scores_map = {sym: np.nan for sym in symbols}
   ```
   When `insider_filings` is None/empty (e.g. no DART key or no recent filings), all symbols retain `np.nan`.
5. **RIM Valuation Engine** (`trading_system/src/core/rim_valuation.py` & `run_pipeline.py` lines 2771–2777):
   When fundamental BPS is missing, `rim_score` is `np.nan`. `run_pipeline.py` filters `valid_rim = df_rim[df_rim['rim_score'].notna() & (df_rim['rim_score'] > 0)]`. If `valid_rim` is empty, `_write_rim_file` writes `데이터 없음 (유효한 RIM 적정가 산출 대상 종목 없음)`.

### 1.4 Per-Market Split File Generation Logic in `run_pipeline.py`
In `run_pipeline.py` lines 1140–1155:
```python
def _get_target_markets_to_save(df: pd.DataFrame = None, universe: pd.DataFrame = None) -> list[str]:
    """Return all unique market identifiers to save individual reports for."""
    markets = set()
    if df is not None and not df.empty and 'market' in df.columns:
        markets.update(df['market'].dropna().unique())
    if universe is not None and not universe.empty and 'market' in universe.columns:
        markets.update(universe['market'].dropna().unique())
    target_env = os.environ.get("INFERENCE_TARGET", "").strip().upper()
    if target_env:
        for t in target_env.split(','):
            t_clean = t.strip()
            if t_clean and t_clean not in ['ALL', 'CORE_5', 'ASIA_DEV', 'ASIA_EMG', 'COMMODITY']:
                markets.add(t_clean)
    if not markets:
        markets = {'KOSPI', 'KOSDAQ', 'SP500', 'NASDAQ', 'RUSSELL2000'}
    return sorted(markets)
```
In `_save_strategy_predictions_report` (lines 2879–2886):
```python
base_name = output_filename.replace(".txt", "")
for _m in _get_target_markets_to_save(df=merged, universe=universe):
    _m_df = merged[merged['market'] == _m]
    if _m_df.empty:
        continue
    with open(os.path.join(result_dir, f"{base_name}_{_m}.txt"), "w", encoding="utf-8") as _mf:
        _write_content(_mf, _m_df, market_label=_m)
```
Because `merged` was stripped of all rows by `.dropna(subset=[score_col])`, `_m_df` is empty for all markets `_m`. Therefore, the per-market loop executes `continue` on line 2883, writing **zero per-market split files** (`<strategy>_<MARKET>.txt`).

---

## 2. Logic Chain

1. **Input State**: When running the pipeline offline, in CI/CD (GitHub Actions), or when external data sources (DART API, SEC EDGAR, quarterly fundamental balance sheets) are unavailable, strategy engines return DataFrames where `score_column` contains `NaN` for all or most symbols.
2. **`dropna` Cleansing**: In `_save_strategy_predictions_report()`, line 2858 coerces values to numeric and line 2859 executes `merged = merged.dropna(subset=[score_col])`.
3. **Empty Data Subsetting**: Because all scores were `NaN`, `dropna` removes 100% of rows from `merged` (`len(merged) == 0`).
4. **Header Writing Without Data**: `_write_content` is called with `len(df_sub) == 0`. It writes the file title, timestamp, `Total symbols evaluated: 0`, and column headers, but loop `for rank, (_, row) in enumerate(df_sub.head(100).iterrows(), 1)` has 0 iterations. This creates the 238–243 byte 0-row file.
5. **Skipping Market Splits**: In lines 2880–2886, `_m_df = merged[merged['market'] == _m]` is empty for all markets. `if _m_df.empty: continue` skips writing all per-market `<strategy>_<MARKET>.txt` files.
6. **Downstream Pipeline Cascade**:
   - In GitHub Actions (`pipeline.yml` lines 241–246), `cp "trading_system/result/${f}.txt" "trading_system/result_split/${f}_${{ matrix.target }}.txt"` copies the 0-row file into artifact storage.
   - `merge_predictions.py` (`merge_generic_strategy_files` lines 427–448) reads the per-market files, finds 0 data rows or "데이터 없음", and writes `데이터 없음` to the merged output.
   - `generate_report.py` (`parse_generic_strategy_table` / `_parse_simple_strategy`) parses the empty merged file and renders `<tr><td colspan="5" class="empty">데이터 없음</td></tr>` into `gh-pages/index.html`.

---

## 3. Caveats

1. **Statistical Arbitrage Special Case**: Unlike directional single-asset strategies, `stat_arb_predictions.txt` evaluates pairs. When no stock pairs pass cointegration p-value thresholds (p < 0.05, half-life > 0), 0 cointegrated pairs is mathematically expected behavior. However, it should format as `데이터 없음 (유의미한 공적분 페어 미발견)` or list top cointegration candidates under observation rather than failing silently.
2. **Matrix Target Market Scope**: In GHA matrix execution, each runner runs for one market (e.g. `INFERENCE_TARGET=SP500`). `_get_target_markets_to_save()` correctly limits saving to `SP500`, which is then merged by `merge_predictions.py`. In local standalone runs (`INFERENCE_TARGET=ALL` or full universe), all 5 markets are evaluated in one process.

---

## 4. Conclusion & Concrete Recommendations

### Recommendation 1: Engine Fallback Heuristics (Fix the Root Source of NaNs)
Ensure all strategy engines in `src/core/` implement robust heuristic proxy fallback calculations when external data is absent:
- **`accruals_quality.py`**: When `features_df` is missing, calculate cash flow / working capital proxies from price-volume metrics (e.g. MFI accumulation / OBV divergence) or return normalized percentile ranks so valid scores `[0.05, 0.95]` are always generated.
- **`valueup_catalyst.py`**: When BPS/PBR is missing, estimate value ranking proxy from dividend yield / price momentum / low volatility proxies so all universe symbols receive valid scores `[0.05, 0.95]`.
- **`earnings_tone_drift.py`**: Implement price-action earnings momentum fallback using `prices_dict` (e.g. 20d momentum drift `(close / sma20 - 1.0)`) or neutral baseline `0.50` when no call transcripts or earnings growth data exist.
- **`insider_buying.py`**: Default baseline score to `0.50` (Neutral) for all universe symbols when no insider disclosures are detected, rather than `np.nan`.
- **`llm_sentiment_engine.py`**: Ensure price gap & trend sentiment fallback covers all universe symbols and returns valid floats.
- **`rim_valuation.py`**: Provide relative valuation proxy ranks when fundamental BPS is absent to ensure non-empty ranking rows.

### Recommendation 2: Hardening `_save_strategy_predictions_report()` in `run_pipeline.py`
Modify `_save_strategy_predictions_report()` to defensively handle missing scores:
1. **Defensive Imputation Before Dropna**:
   ```python
   # Convert symbol types and impute missing scores before dropna
   merged['symbol'] = merged['symbol'].astype(str)
   merged[score_col] = pd.to_numeric(merged[score_col], errors='coerce')
   if merged[score_col].isna().all():
       logger.warning(f"[REPORT FALLBACK] Strategy '{title}' has all-NaN scores. Imputing baseline neutral score 0.50.")
       merged[score_col] = 0.50
   else:
       # Impute remaining sporadic NaNs with column median or neutral 0.50
       col_median = merged[score_col].median()
       fallback_val = col_median if pd.notna(col_median) and np.isfinite(col_median) else 0.50
       merged[score_col] = merged[score_col].fillna(fallback_val)
   ```
2. **Market Identifier Normalization**:
   Map generic `'KRX'` to `'KOSPI'` or `'KOSDAQ'` using symbol patterns (`str(sym).isdigit()`) so `generate_report.py`'s `KNOWN_MKTS` set matches accurately.
3. **Per-Market Split File Guarantee**:
   Iterate over all active markets in `_get_target_markets_to_save(df=merged, universe=universe)`. For any market with symbols in `merged`, write `<base_name>_<MARKET>.txt`.

### Recommendation 3: Standardize 31+ Strategy Output File Generation
Ensure all 31+ strategy blocks in `trading_system/run_pipeline.py` write both unified `.txt` and `<strategy>_<MARKET>.txt` files matching the names registered in `merge_predictions.py` and parsed in `generate_report.py`.

---

## 5. Verification Method

1. **Unit Verification of Report Saving**:
   Run pytest on merge and report generation suites:
   ```bash
   .venv/bin/pytest tests/test_merge_generic_strategies.py tests/ -v
   ```
2. **Pipeline Report Saving Inspection**:
   Execute `generate_report.py` against result directory to verify 0-row files no longer trigger "데이터 없음":
   ```bash
   .venv/bin/python trading_system/generate_report.py --result-dir trading_system/result --out gh-pages/index.html
   ```
3. **Verification Commands**:
   - Inspect generated files: `cat trading_system/result/sentiment_predictions.txt`
   - Check symbol counts: verify `Total symbols evaluated: > 0` and verify non-empty ranked lines exist for all 5 markets (`SP500`, `NASDAQ`, `RUSSELL2000`, `KOSPI`, `KOSDAQ`).
