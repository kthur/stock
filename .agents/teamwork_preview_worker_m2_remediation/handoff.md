# Handoff Report — Milestone 2 Remediation (Worker 2)

## 1. Observation

In `trading_system/src/ai/ensemble_scorer.py`:
- `EnsembleScoringEngine.combine_predictions` previously pruned each strategy DataFrame slice to `['symbol', score_col]`.
- For example:
  ```python
  reg_df_copy = reg_df[['symbol', reg_col]].rename(columns={reg_col: 'reg_pred'})
  s_df_copy = s_df[['symbol', surge_col]].rename(columns={surge_col: 'surge_score'})
  ```
- This stripped metadata columns (`name`, `market`, `volume`, `close`) from the individual strategy DataFrames prior to merging.
- Consequently, when `merged` was evaluated by `_is_illiquid_or_preferred` and `_get_cost_pct`:
  - `_is_illiquid_or_preferred` received `row.get('name', '')` as `''`. As a result, preferred stocks (e.g. `'삼성전자우'`) and SPACs (`'하나금융25호스팩'`) failed to trigger `name.endswith('우')` or `'스팩' in name` and bypassed the liquidity filter.
  - `_get_cost_pct` received `row.get('market', '')` as `''`. For symbols without market suffix in symbol (e.g. 6-digit numeric tickers on KOSDAQ or KONEX), `market` evaluated to `''`, causing them to fall back to default/KOSPI transaction cost rules instead of their market-specific rules.
  - Unit test `test_liquidity_and_preferred_stock_filter` and `test_transaction_costs_and_slippage_all_markets` failed under this defect.

## 2. Logic Chain

- **Step 1 (Metadata Extraction in Strategy Slices)**: Defined `META_COLS = ['name', 'market', 'volume', 'close']`. When constructing `reg_df_copy`, `s_df_copy`, `ll_df_copy`, `vr_df`, `v_df`, `l_df`, `sa_df`, `sec_df`, `r_val_df`, `ev_df`, `m_df`, `iv_df`, `of_df`, `rev_df`, extracted all present metadata columns (`meta_cols = [c for c in META_COLS if c in df.columns]`) in addition to `'symbol'` and the strategy score column.
- **Step 2 (Safeguard Strategy Score Column Selection)**: Updated numeric column fallback selectors across all 14 strategies to filter out `c not in META_COLS` (e.g., `num_cols = [c for c in df.columns if c != 'symbol' and c not in META_COLS]`), ensuring metadata columns like `volume` or `close` are never mistaken for strategy score columns.
- **Step 3 (Metadata-Preserving Outer Merge)**: Updated the merge loop over strategy DataFrames `dfs`:
  ```python
  merged = pd.DataFrame(columns=['symbol'])
  for d in dfs:
      if d is not None and not d.empty:
          if merged.empty:
              merged = d.copy()
          else:
              overlap = [c for c in d.columns if c in merged.columns and c != 'symbol']
              if overlap:
                  merged = merged.merge(d, on='symbol', how='outer', suffixes=('', '_dup'))
                  for col in overlap:
                      dup_col = col + '_dup'
                      if dup_col in merged.columns:
                          merged[col] = merged[col].combine_first(merged[dup_col])
                          merged.drop(columns=[dup_col], inplace=True)
              else:
                  merged = merged.merge(d, on='symbol', how='outer')
  ```
  This combines overlapping metadata across strategies (filling NaNs without creating `_dup` columns) and preserves `name`, `market`, `volume`, and `close` in `merged`.
- **Step 4 (Verification of Filtering and Cost Calculation)**:
  - `_is_illiquid_or_preferred`: Correctly evaluates `name.endswith('우')`, `name.endswith('우B')`, `name.endswith('1우')`, `'스팩' in name`, `'SPAC' in name.upper()`, and `volume <= 0`, setting `ensemble_score` and `ensemble_expected_return` to `0.0`.
  - `_get_cost_pct`: Correctly reads `market` (`KONEX` -> 1.30%, `KOSDAQ` -> 1.00%, `KOSPI` -> 0.85%, `SP500` -> 0.60%) and deducts appropriate transaction costs + slippage.

## 3. Caveats

- No caveats.

## 4. Conclusion

The critical defect in `EnsembleScoringEngine.combine_predictions` has been remediated. All strategy DataFrames now preserve metadata columns (`name`, `market`, `volume`, `close`) during slice creation and outer merging. Preferred stocks, SPACs, and low-volume stocks are zero-weighted by `_is_illiquid_or_preferred`, and transaction costs are accurately applied by `_get_cost_pct` based on market identification.

## 5. Verification Method

To verify independently:
1. Inspect `trading_system/src/ai/ensemble_scorer.py` (lines 542–677). Confirm `META_COLS` preservation and metadata merge logic using `combine_first`.
2. Run unit tests using Python virtual environment:
   `.venv\Scripts\python.exe -m pytest trading_system/tests/test_r1_ensemble_regime_fixes.py`
3. Run complete test suite:
   `.venv\Scripts\python.exe -m pytest trading_system/tests/`
4. Confirm 100% test pass without errors or failures.
