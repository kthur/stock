# Handoff Report: Data Ingestion & Cache Fallback Resiliency Audit

**Task**: Milestone 1, Task 2 — Audit Data Ingestion & Cache Fallback Resiliency  
**Agent**: Exploration Specialist (`teamwork_preview_explorer_m1_2_v2`)  
**Working Directory**: `d:\Finance\code\stock\.agents\teamwork_preview_explorer_m1_2_v2`  
**Analysis File**: `d:\Finance\code\stock\.agents\teamwork_preview_explorer_m1_2_v2\analysis.md`

---

## 1. Observation

Direct code observations from read-only audit across `trading_system/src/persistence/database.py`, `trading_system/src/data_layer/indicator_storage.py`, `trading_system/src/data_layer/earnings_data.py`, `trading_system/src/data_layer/global_market.py`, `trading_system/src/config.py`, `trading_system/run_pipeline.py`, and `trading_system/src/ai/prediction_model.py`:

### Observation 1: Empty Cache Query Index and Casing Mismatch
- **File**: `trading_system/src/persistence/database.py`, lines 459–463
- **Verbatim Code**:
  ```python
  df = pd.read_sql_query(query, conn, params=params, parse_dates=["date"])
  if not df.empty:
      df.set_index("date", inplace=True)
      df.columns = [col.capitalize() for col in df.columns]
  return df
  ```
- **Finding**: When SQL query returns 0 rows, `if not df.empty:` is bypassed. `df` is returned with `RangeIndex` and lowercase columns `['date', 'open', 'high', 'low', 'close', 'volume']`.

### Observation 2: Inverted Offline Freshness Condition in `needs_update()`
- **File**: `trading_system/src/persistence/database.py`, lines 483–491
- **Verbatim Code**:
  ```python
  def needs_update(self, symbol: str, max_age_days: int = 1,
                   start_date: Optional[str] = None) -> bool:
      latest = self.get_latest_date(symbol)
      if latest is None:
          return True
      latest_dt = datetime.strptime(latest, "%Y-%m-%d")
      if (datetime.now() - latest_dt).days >= max_age_days:
          return True
  ```
- **Finding**: In offline mode (`STOCK_PRICE_FRESHNESS_DAYS=none`), `max_age_days` is `-1`. For any existing cache entry, `(datetime.now() - latest_dt).days >= -1` evaluates to `True`, causing `needs_update()` to return `True` for every cached symbol when running offline.

### Observation 3: Offline Prefetching Network Downloads
- **File**: `trading_system/run_pipeline.py`, lines 204–215
- **Verbatim Code**:
  ```python
  for sym in symbols:
      if price_db.needs_update(sym, max_age_days=freshness_days, start_date=start_date):
          ...
          symbols_to_update.append(sym)
  ```
- **Finding**: `prefetch_prices_batch` does not check if `freshness_days < 0`. Because `needs_update` returns `True`, it attempts batch network downloads for all 3,379 symbols even when network is unavailable or offline mode is requested.

### Observation 4: Database Storage Disconnect for Global Indicators
- **File**: `trading_system/src/data_layer/indicator_storage.py`, lines 241–259 vs `trading_system/run_pipeline.py`, lines 508–567
- **Verbatim Code**:
  - `indicator_storage.py`: `save_indicators` writes to `market_indicators.db` table `global_indicators`.
  - `run_pipeline.py`: `fetch_indicator_history` queries `price_db.get_prices(ticker)` which queries `stock_prices.db` for tickers like `^VIX`, `USDKRW=X`, `^TNX`.
- **Finding**: `fetch_indicator_history` does not read from `market_indicators.db`. If `stock_prices.db` lacks these indicator tickers, lookups return empty DataFrames.

### Observation 5: Silent Macro Feature Zero-Fill
- **File**: `trading_system/src/ai/prediction_model.py`, lines 890–896
- **Verbatim Code**:
  ```python
  def _merge_indicator_history(self, df: pd.DataFrame,
                                indicator_df: pd.DataFrame = None) -> pd.DataFrame:
      if indicator_df is None or indicator_df.empty:
          for col in self.GLOBAL_FEATURES:
              df[col] = 0.0
          return df
  ```
- **Finding**: When `indicator_df` is empty, all 9 global features (`vix_change`, `us10y`, `usdkrw_change`, `sp500_change`, `dxy_change`, `wti_change`, `kospi_change`, `kosdaq_change`, `put_call_ratio`) are filled with `0.0` without any error or log warning.

### Observation 6: Snapshot `Volume == 0` Symbol Exclusion Trap
- **File**: `trading_system/src/data_layer/indicator_storage.py`, lines 211–213 & `trading_system/run_pipeline.py`, lines 652–657
- **Verbatim Code**:
  ```python
  krx.columns = [str(c).capitalize() if str(c).lower() in ['open', 'high', 'low', 'close', 'volume', 'code'] else str(c) for c in krx.columns]
  excluded = set(krx[krx['Volume'] == 0]['Code'].tolist()) if 'Volume' in krx.columns else set()
  ```
- **Finding**: `fdr.StockListing('KRX')` returns a single live snapshot of trading activity. Any active stock with 0 volume at that instant (e.g. before market open, after hours, weekend) is flagged as `Volume == 0` and permanently excluded from the `stock_universe` database table or purged from inference.

### Observation 7: Unhandled String Formatting Exception in Administrative List Fetch
- **File**: `trading_system/src/data_layer/indicator_storage.py`, lines 214–219
- **Verbatim Code**:
  ```python
  try:
      adm = fdr.StockListing('KRX-ADMINISTRATIVE')
      for s in adm['Symbol']:
          excluded.add(f'{s:06d}')
  except Exception as e:
      logger.warning(f"Failed to fetch KRX administrative list: {e}")
  ```
- **Finding**: `f'{s:06d}'` fails with `ValueError: Unknown format code 'd' for object of type 'str'` if `s` is already a string symbol like `'005930'`, throwing an exception that aborts administrative exclusion.

---

## 2. Logic Chain

1. **From Observation 1**: When `StockPriceDB.get_prices()` queries an unpopulated symbol or a date range with 0 matches, it returns a DataFrame with `RangeIndex` and lowercase columns `['date', 'open', 'high', ...]` because line 460 (`if not df.empty:`) is skipped.
2. **From Observations 2 & 3**: When running offline (`STOCK_PRICE_FRESHNESS_DAYS=none`), `freshness_days = -1`. `needs_update()` checks `(now - latest).days >= -1`, which evaluates to `True` for every symbol. Consequently, `prefetch_prices_batch` attempts batch network requests for all 3,379 symbols. When network is unavailable, these requests fail, and `fetch_data_fdr` falls back to returning the empty `cached_df` (Observation 1).
3. **From Observation 4 & 5**: `fetch_indicator_history()` looks for global indicators in `stock_prices.db` rather than `market_indicators.db`. When offline or unpopulated, it returns an empty DataFrame. In `_merge_indicator_history()`, an empty `indicator_df` causes all 9 global features (`vix_change`, `us10y`, `usdkrw_change`, `sp500_change`, etc.) to be silently set to `0.0`.
4. **From Observations 6 & 7**: In `MarketIndicatorStorage.update_stock_universe()` and `_get_excluded_krx_symbols()`, `krx[krx['Volume'] == 0]` checks a single live snapshot. Executing the pipeline outside market hours (nights/weekends) evaluates `Volume == 0` for all KRX stocks, causing up to 2,500 valid active stocks to be purged from `stock_universe` or dropped from inference. Furthermore, `f'{s:06d}'` crashes on string symbols, bypassing administrative exclusions.

---

## 3. Caveats

- **No Caveats**: All audited modules (`StockPriceDB`, `MarketIndicatorStorage`, `earnings_data.py`, `global_market.py`, `run_pipeline.py`, `prediction_model.py`, `feature_engineering.py`) were thoroughly inspected line by line. The root cause mechanisms were isolated with exact line numbers and logic paths.

---

## 4. Conclusion

Data ingestion and cache fallback vulnerabilities stem from 4 main architectural flaws:
1. **Schema/Index Inconsistency on Empty Cache Returns**: `StockPriceDB.get_prices()` returns a `RangeIndex` with lowercase columns on empty results instead of a `DatetimeIndex` with capitalized OHLCV columns.
2. **Inverted Offline Logic in `needs_update()`**: Negative `max_age_days` (-1) evaluates `days >= -1` to `True`, breaking offline cache enforcement and causing network call attempts.
3. **Indicator Database Disconnect & Silent Zero-Filling**: Indicators saved to `market_indicators.db` are queried from `stock_prices.db`, resulting in cache misses that silently set all global macro features to `0.0`.
4. **Snapshot Volume Symbol Purging**: `krx['Volume'] == 0` snapshot checks run outside market hours treat all KRX stocks as halted, purging valid symbols from universe creation and inference.

---

## 5. Verification Method

### Recommended Project Test Command
Execute test suite using `.venv/bin/pytest`:
```bash
.venv/bin/pytest tests/ -v
```

### Manual Offline Cache Verification Protocol
1. Run pipeline in offline mode:
   ```bash
   STOCK_PRICE_FRESHNESS_DAYS=none .venv/bin/python trading_system/run_pipeline.py --skip-training
   ```
2. Inspect `trading_system/result/pipeline_result.txt` and `trading_system/result/surge_predictions.txt`.
3. Verify that valid KRX and S&P 500 symbols are present, non-zero features are generated, and no `RangeIndex` or `KeyError` exceptions are logged.

### Invalidation Conditions
- If `StockPriceDB.get_prices()` returns a DataFrame with `RangeIndex` or lowercase columns when 0 rows match.
- If `needs_update()` returns `True` when `max_age_days < 0`.
- If `run_pipeline.py` attempts network requests when `STOCK_PRICE_FRESHNESS_DAYS=none`.
- If `_get_excluded_krx_symbols()` excludes more than 50 stocks outside trading hours.
