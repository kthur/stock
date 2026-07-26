# Comprehensive Audit Report: Data Ingestion & Cache Fallback Resiliency

**Milestone 1, Task 2: Data Ingestion & Cache Fallback Resiliency Audit**  
**Agent Workspace**: `d:\Finance\code\stock\.agents\teamwork_preview_explorer_m1_2_v2`  
**Target Files Audited**:
- `trading_system/src/persistence/database.py` (`StockPriceDB`, `TradeLogger`, `AssetHistoryDB`, `AIPredictionDB`)
- `trading_system/src/data_layer/indicator_storage.py` (`MarketIndicatorStorage`)
- `trading_system/src/data_layer/earnings_data.py` (`fetch_fundamentals`, `async_fetch_fundamentals`, `fetch_and_store_fundamentals_batch`)
- `trading_system/src/data_layer/global_market.py` (`GlobalMarketClient`)
- `trading_system/src/utils/http_session.py` (`setup_global_http_headers`)
- `trading_system/src/config.py` (`TradingConfig`)
- `trading_system/run_pipeline.py` (Pipeline orchestration, prefetching, network fetchers, indicator history, symbol filtering)
- `trading_system/src/ai/prediction_model.py` (`OnDevicePredictionModel`, `merge_fundamentals`, `_merge_indicator_history`, `_create_features`)
- `trading_system/src/ai/feature_engineering.py` (`compute_vcp_features`, scalers)

---

## Executive Summary

An in-depth code audit was conducted on the data ingestion, cache persistence, global indicator tracking, corporate fundamentals loading, and symbol filtering components of the stock trading system.

The investigation uncovered **16 distinct root cause mechanisms** spanning 4 primary failure categories that cause:
1. Historical price queries or indicator calculations to return empty DataFrames or drop valid dates.
2. Offline mode (`STOCK_PRICE_FRESHNESS_DAYS=none` or network unavailable) to fail cache lookups or silently fill features with `0.0` or `NaN`.
3. Global market indicators (VIX, TNX, USDKRW, SP500, DXY, WTI, KOSPI, KOSDAQ) and corporate fundamentals to fail or default to zeroes.
4. Active, valid stocks to be inadvertently purged from the universe or inference pipeline due to snapshot timing traps and unhandled exceptions.

---

## Category 1: Historical Price Data & Indicator History Failure Mechanisms

### Root Cause 1.1: `StockPriceDB.get_prices()` Returns Mismatched Index Type and Column Casing on Empty Cache Query
- **Location**: `trading_system/src/persistence/database.py`, lines 446–463
- **Observation**:
  ```python
  df = pd.read_sql_query(query, conn, params=params, parse_dates=["date"])
  if not df.empty:
      df.set_index("date", inplace=True)
      df.columns = [col.capitalize() for col in df.columns]
  return df
  ```
- **Mechanism**: When `get_prices()` finds 0 matching rows in `stock_prices.db`, `if not df.empty:` is skipped. The returned empty `DataFrame` has a standard `RangeIndex` (instead of `DatetimeIndex`) and lowercase column names (`['date', 'open', 'high', 'low', 'close', 'volume']`).
- **Impact**: Downstream callers in `run_pipeline.py` (e.g. lines 380, 401, 528) calling `cached_df.index.max().strftime("%Y-%m-%d")` crash with `AttributeError: 'RangeIndex' object has no attribute 'strftime'`, or callers looking for uppercase `'Close'` raise `KeyError: 'Close'`.

### Root Cause 1.2: ISO Date String Comparison Flaws in SQLite Queries
- **Location**: `trading_system/src/persistence/database.py`, lines 452–457
- **Observation**:
  ```python
  if start_date:
      query += " AND date >= ?"
      params.append(start_date)
  if end_date:
      query += " AND date <= ?"
      params.append(end_date)
  ```
- **Mechanism**: In `stock_prices.db`, if dates were inserted as full ISO timestamps (e.g. `2024-01-15 00:00:00`), querying `date <= '2024-01-15'` fails to match records timestamped `2024-01-15 09:30:00` because string comparison evaluates `'2024-01-15 09:30:00' > '2024-01-15'`.
- **Impact**: Queries for date ranges truncate the final day of historical data or return empty DataFrames when querying exact date bounds.

### Root Cause 1.3: Database Disconnect Between Indicator Storage and Indicator History Querying
- **Location**: `trading_system/run_pipeline.py`, lines 508–567 vs `trading_system/src/data_layer/indicator_storage.py`, lines 241–259
- **Observation**:
  - `GlobalMarketClient` snapshot indicators are saved by `MarketIndicatorStorage.save_indicators()` into `market_indicators.db` under the table `global_indicators`.
  - However, `fetch_indicator_history()` in `run_pipeline.py` attempts to fetch history from `price_db` (`StockPriceDB`, pointing to `stock_prices.db`) using ticker strings like `'^VIX'`, `'^TNX'`, `'USDKRW=X'`, `'^GSPC'`, `'DX-Y.NYB'`, `'CL=F'`, `'^KS11'`, `'^KQ11'`, `'^CPC'`.
- **Mechanism**: `stock_prices.db` does not automatically store global market index history unless explicitly downloaded as price tickers. When offline or on a fresh DB, `price_db.get_prices('^VIX')` returns an empty DataFrame because the indicators were stored in `market_indicators.db`, not `stock_prices.db`.
- **Impact**: `fetch_indicator_history()` fails to find cached indicator data in `stock_prices.db` and returns an empty DataFrame or series of `0.0`s for all global indicators.

### Root Cause 1.4: Multi-Threaded Indicator Fetch Failure Silence
- **Location**: `trading_system/run_pipeline.py`, lines 569–581
- **Observation**:
  ```python
  futures = {pool.submit(_fetch_one, t, c): c for t, c in _INDICATOR_TICKERS.items()}
  for f in as_completed(futures):
      try:
          col_name, series = f.result()
          combined[col_name] = series
      except Exception as e:
          logger.debug(f"Indicator fetch failed for {futures[f]}: {e}")
  ```
- **Mechanism**: If `_fetch_one` encounters a network error and `cached_df` is missing/empty, `_fetch_one` returns `(col_name, pd.Series(dtype=float))`. `pd.concat(combined, axis=1)` creates columns containing all NaNs.
- **Impact**: Indicator history returns empty or NaN-filled columns, silently propagating into feature calculation.

---

## Category 2: DB Cache Fallback & Offline Mode Failure Mechanisms

### Root Cause 2.1: Inverted Logic Bug in `StockPriceDB.needs_update()` for Negative Freshness Days
- **Location**: `trading_system/src/persistence/database.py`, lines 483–500
- **Observation**:
  ```python
  def needs_update(self, symbol: str, max_age_days: int = 1, start_date: Optional[str] = None) -> bool:
      latest = self.get_latest_date(symbol)
      if latest is None:
          return True
      latest_dt = datetime.strptime(latest, "%Y-%m-%d")
      if (datetime.now() - latest_dt).days >= max_age_days:
          return True
  ```
- **Mechanism**: When running offline (`STOCK_PRICE_FRESHNESS_DAYS=none`), `TradingConfig.get_freshness_days()` returns `-1`. The elapsed days `(datetime.now() - latest_dt).days` for any existing cache entry is a non-negative integer (e.g. `0`, `1`, `10`). The expression `days >= -1` is **`True` for all non-negative integers**!
- **Impact**: `needs_update()` returns `True` for EVERY cached symbol when `freshness_days = -1`. The system incorrectly marks all cache entries as stale in offline mode!

### Root Cause 2.2: `prefetch_prices_batch` Unconditionally Attempts Network Requests in Offline Mode
- **Location**: `trading_system/run_pipeline.py`, lines 194–215
- **Observation**:
  ```python
  for sym in symbols:
      if price_db.needs_update(sym, max_age_days=freshness_days, start_date=start_date):
          ...
          symbols_to_update.append(sym)
  ```
- **Mechanism**: Because `needs_update()` returns `True` when `freshness_days = -1` (Root Cause 2.1), `prefetch_prices_batch` places all 3,379 universe symbols into `symbols_to_update`. It then attempts `yf.download()` batch calls across all symbols. When network is disabled or unavailable, every batch fails, triggering binary-split retries, logging hundreds of error lines, and wasting minutes before giving up.

### Root Cause 2.3: `fetch_data_fdr` Cache Miss Handling in Offline Mode
- **Location**: `trading_system/run_pipeline.py`, lines 365–387
- **Observation**:
  ```python
  if price_db is not None:
      stale = True if freshness_days >= 0 else False
      ...
      cached_df = price_db.get_prices(s, start_date=d)
      ...
  if freshness_days < 0:
      return cached_df
  ```
- **Mechanism**: If `freshness_days < 0` (offline mode) and symbol `s` is not present in `stock_prices.db`, `cached_df` is an empty DataFrame (with `RangeIndex` and lowercase columns). Line 386 returns `cached_df` directly.
- **Impact**: Downstream in `run_pipeline.py` (line 1039), `infer_data_dict` filters `len(df) >= 200`. All symbols with empty cache are immediately dropped, resulting in truncated or empty inference data dicts.

### Root Cause 2.4: Silent Zero-Fill of Global Features in `_merge_indicator_history()`
- **Location**: `trading_system/src/ai/prediction_model.py`, lines 890–905
- **Observation**:
  ```python
  def _merge_indicator_history(self, df: pd.DataFrame, indicator_df: pd.DataFrame = None) -> pd.DataFrame:
      if indicator_df is None or indicator_df.empty:
          for col in self.GLOBAL_FEATURES:
              df[col] = 0.0
          return df
  ```
- **Mechanism**: When running offline or when indicator history fetch fails, `indicator_df` is empty. `_merge_indicator_history` silently sets all 9 global features (`vix_change`, `us10y`, `usdkrw_change`, `sp500_change`, `dxy_change`, `wti_change`, `kospi_change`, `kosdaq_change`, `put_call_ratio`) to `0.0`.
- **Impact**: Machine learning models (XGBoost / LightGBM / CatBoost) receive `0.0` for all macro indicators, causing prediction accuracy degradation without any warning emitted.

### Root Cause 2.5: Corporate Fundamental Cache Expiry & Offline Fallback to NaNs
- **Location**: `trading_system/src/data_layer/earnings_data.py`, lines 228–231 & `trading_system/src/ai/prediction_model.py`, lines 852–870
- **Observation**:
  - In `earnings_data.py`:
    ```python
    if expiry_days < 0:
        logger.info("[Offline Mode] Skipping fundamental network fetching...")
        return 0
    ```
  - In `prediction_model.py`:
    ```python
    meta = FALLBACK_METADATA[symbol]
    for col in FUND_COLS:
        df[col] = meta[col] # meta contains np.nan for all symbols outside 16 benchmarks
    ```
- **Mechanism**: `FALLBACK_METADATA` contains hardcoded values for only 16 ticker symbols. For all other 3,363 universe symbols, `FALLBACK_METADATA` returns `np.nan` for `revenue`, `operating_income`, `net_income`, `eps`, and `dividend_per_share`.
- **Impact**: In offline mode or when fundamentals haven't been pre-cached in SQLite, 99.5% of symbols have their fundamental features set to `NaN` and `has_fundamental` set to `0.0`.

---

## Category 3: Corporate Fundamentals & Global Market Indicator Failures

### Root Cause 3.1: Snapshot `None` Price Skips in `MarketIndicatorStorage.save_indicators()`
- **Location**: `trading_system/src/data_layer/global_market.py`, lines 70–130 & `trading_system/src/data_layer/indicator_storage.py`, lines 249–258
- **Observation**:
  - `GlobalMarketClient.get_index_current()` returns `{"price": None}` if yfinance ticker download fails.
  - `MarketIndicatorStorage.save_indicators()` executes:
    ```python
    for sym, info in data.get('indices', {}).items():
        if info.get('price') is not None:
            conn.execute(sql, ...)
    ```
- **Mechanism**: If `price` is `None` due to a temporary network glitch or off-market hours, `save_indicators` silently skips inserting rows into `global_indicators`.
- **Impact**: `market_indicators.db` table `global_indicators` has missing dates with zero error indication.

### Root Cause 3.2: Yahoo Finance Rate Limiting & Blocking on Korean Fundamental API
- **Location**: `trading_system/src/data_layer/earnings_data.py`, lines 45–82 & 104–198
- **Observation**: `_fetch_fundamentals_network` and `async_fetch_fundamentals` query Yahoo Finance (`query2.finance.yahoo.com/v10/finance/quoteSummary`).
- **Mechanism**: Yahoo Finance frequently rate-limits (HTTP 429) or blocks requests for Korean stocks (e.g. `005930.KS`). When `quoteSummary` returns empty JSON `result: []`, `async_fetch_fundamentals` returns `None`.
- **Impact**: Fundamental data fails to load for Korean stocks, defaulting to `FALLBACK_METADATA` (`NaN`).

### Root Cause 3.3: Fundamental YoY Growth Rate Calculation Zero-Division & Missing Prior History
- **Location**: `trading_system/src/ai/prediction_model.py`, lines 821–827
- **Observation**:
  ```python
  if gr_col in df_fun.columns and len(df_fun) >= 2:
      prev = df_fun[gr_col].shift(1)
      df_fun[f'{gr_col}_growth_1y'] = df_fun[gr_col].sub(prev).div(prev.abs().replace(0, float('nan'))).fillna(0.0).replace([float('inf'), -float('inf')], 0.0)
  ```
- **Mechanism**: If `df_fun` has only 1 annual statement available in DB, `len(df_fun) >= 2` evaluates to `False`. `eps_growth_1y` and `revenue_growth_1y` default to `0.0`.
- **Impact**: Newly listed companies or companies with sparse financial history always have 0% YoY growth features.

---

## Category 4: Symbol Filtering & Inadvertent Purging Mechanisms

### Root Cause 4.1: `Volume == 0` Snapshot Trap in `MarketIndicatorStorage.update_stock_universe()`
- **Location**: `trading_system/src/data_layer/indicator_storage.py`, lines 211–213
- **Observation**:
  ```python
  krx.columns = [str(c).capitalize() if str(c).lower() in ['open', 'high', 'low', 'close', 'volume', 'code'] else str(c) for c in krx.columns]
  excluded = set(krx[krx['Volume'] == 0]['Code'].tolist()) if 'Volume' in krx.columns else set()
  ```
- **Mechanism**: `fdr.StockListing('KRX')` returns a single live snapshot of current market trading. `Volume` in this DataFrame is the traded volume *at that exact moment*. If `update_stock_universe()` runs before market open, on weekends/holidays, or after market close when snapshot volume is reported as 0, `krx['Volume'] == 0` matches thousands of active stocks!
- **Impact**: Valid active stocks are added to `excluded` and **permanently omitted from the `stock_universe` database table**!

### Root Cause 4.2: String Format Exception in `KRX-ADMINISTRATIVE` List Fetch
- **Location**: `trading_system/src/data_layer/indicator_storage.py`, lines 214–219
- **Observation**:
  ```python
  try:
      adm = fdr.StockListing('KRX-ADMINISTRATIVE')
      for s in adm['Symbol']:
          excluded.add(f'{s:06d}')
  except Exception as e:
      logger.warning(f"Failed to fetch KRX administrative list: {e}")
  ```
- **Mechanism**: If `adm['Symbol']` contains string values (e.g. `'005930'`), `f'{s:06d}'` throws `ValueError: Unknown format code 'd' for object of type 'str'`. Alternatively, if FDR returns column `'Code'` instead of `'Symbol'`, `adm['Symbol']` throws `KeyError`.
- **Impact**: The exception handler catches the error and logs a warning, but fails to exclude actual administrative stocks.

### Root Cause 4.3: Off-Market Hour `Volume == 0` Filtering in `_get_excluded_krx_symbols()`
- **Location**: `trading_system/run_pipeline.py`, lines 639–670
- **Observation**:
  ```python
  def _get_excluded_krx_symbols() -> set:
      ...
      krx = fdr.StockListing('KRX')
      halted = set(krx[krx['Volume'] == 0]['Code'].tolist()) if 'Volume' in krx.columns else set()
      excluded |= halted
  ```
- **Mechanism**: In `run_pipeline.py` (lines 979–983), `_get_excluded_krx_symbols()` is called to exclude halted stocks from inference. If the pipeline is executed outside market hours (e.g. night, weekend), `krx['Volume'] == 0` matches ALL KRX stocks!
- **Impact**: Up to 2,500 valid KRX stocks are dynamically excluded from `all_symbols` during pipeline execution, resulting in empty or severely truncated prediction outputs!

### Root Cause 4.4: Over-Aggressive Zero-Volume Ratio Check in Data Quality Gate
- **Location**: `trading_system/run_pipeline.py`, lines 290–295
- **Observation**:
  ```python
  if volume_col is not None:
      volume = df[volume_col].astype(float)
      zero_vol_ratio = (volume == 0).sum() / total_rows
      if zero_vol_ratio > 0.90:
          logger.debug(f"[DataQualityGate] {sym}: Volume zero ratio={zero_vol_ratio:.1%} > 90% (halted), skipping")
          return False
  ```
- **Mechanism**: `_validate_price_data()` rejects price DataFrames if >90% of rows have `Volume == 0`.
- **Impact**: Illiquid stocks, preferred shares, or KONEX stocks with low trading frequency are rejected by the Data Quality Gate and never written to `stock_prices.db`.

### Root Cause 4.5: Hardcoded 200-Day History Threshold Truncation
- **Location**: `trading_system/run_pipeline.py`, lines 1038–1043
- **Observation**:
  ```python
  infer_data_dict = {s: df for s, df in infer_data_dict.items()
                     if df is not None and len(df) >= 200}
  ```
- **Mechanism**: Any symbol with fewer than 200 daily OHLCV rows is purged from `infer_data_dict`.
- **Impact**: Newly listed stocks (IPO < 1 year) or symbols with recent listing dates are discarded prior to model inference.

---

## Remediation & Implementation Plan

### 1. Fix `StockPriceDB.get_prices()` for Empty Cache Returns
In `trading_system/src/persistence/database.py`:
```python
def get_prices(self, symbol: str, start_date: Optional[str] = None,
               end_date: Optional[str] = None) -> pd.DataFrame:
    conn = self._get_conn()
    query = "SELECT date, open, high, low, close, volume FROM stock_prices WHERE symbol = ?"
    params: list = [symbol]
    if start_date:
        query += " AND date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND date <= ?"
        params.append(end_date)
    query += " ORDER BY date ASC"
    df = pd.read_sql_query(query, conn, params=params, parse_dates=["date"])
    if not df.empty:
        df.set_index("date", inplace=True)
        df.columns = [col.capitalize() for col in df.columns]
    else:
        # Return empty DataFrame with proper DatetimeIndex and capitalized columns
        df = pd.DataFrame(columns=['Open', 'High', 'Low', 'Close', 'Volume'])
        df.index = pd.DatetimeIndex([], name='date')
    return df
```

### 2. Fix `StockPriceDB.needs_update()` for Negative Freshness Days
In `trading_system/src/persistence/database.py`:
```python
def needs_update(self, symbol: str, max_age_days: int = 1,
                 start_date: Optional[str] = None) -> bool:
    if max_age_days < 0:
        return False  # Offline mode: never force update if cache exists
    latest = self.get_latest_date(symbol)
    if latest is None:
        return True
    latest_dt = datetime.strptime(latest, "%Y-%m-%d")
    if (datetime.now() - latest_dt).days >= max_age_days:
        return True
    if start_date is not None:
        earliest = self._get_earliest_date(symbol)
        if earliest is None:
            return True
        earliest_dt = datetime.strptime(earliest, "%Y-%m-%d")
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        if (earliest_dt - start_dt).days > 7:
            return True
    return False
```

### 3. Disable `prefetch_prices_batch` Network Operations in Offline Mode
In `trading_system/run_pipeline.py`:
```python
def prefetch_prices_batch(symbols: list, symbol_market: dict, start_date: str,
                          price_db: Optional[StockPriceDB], freshness_days: int = 1):
    if price_db is None or not symbols or freshness_days < 0:
        logger.info("[Offline Mode] Skipping prefetch_prices_batch network downloads.")
        return
    ...
```

### 4. Fix KRX Symbol Filtering & Administrative List Formatting
In `trading_system/src/data_layer/indicator_storage.py` and `trading_system/run_pipeline.py`:
- Remove snapshot `Volume == 0` filtering from `update_stock_universe()` and `_get_excluded_krx_symbols()`. Trading volume snapshot at any single instant should NEVER be used to determine long-term symbol active status.
- Safely parse administrative list:
  ```python
  try:
      adm = fdr.StockListing('KRX-ADMINISTRATIVE')
      code_col = 'Code' if 'Code' in adm.columns else ('Symbol' if 'Symbol' in adm.columns else None)
      if code_col:
          for s in adm[code_col]:
              code_str = str(s).zfill(6)
              excluded.add(code_str)
  except Exception as e:
      logger.warning(f"Failed to fetch KRX administrative list: {e}")
  ```

---
*End of Audit Report.*
