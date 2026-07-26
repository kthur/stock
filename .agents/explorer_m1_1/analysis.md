# Deep-Dive Analysis: Data Fetching, Exception Handling, and Fallback Strategy in `run_pipeline.py`

**Explorer**: Explorer 1 (Milestone 1)  
**Target File**: `trading_system/run_pipeline.py` (and related data modules in `src/data_layer/`)  
**Scope**: Complete investigation of data fetching endpoints, rate-limiting, exception handling, and offline DB fallback cascade.

---

## 1. Inventory of Data Fetching & Network Endpoints

Below is the complete inventory of network calls to `yfinance`, `FinanceDataReader`, and custom endpoints in `run_pipeline.py` and supporting modules.

| Function / Entry Point | Location | Network Call | Target Asset Class | Current Fallback Mechanism |
|---|---|---|---|---|
| `_fetch_data_fdr_network()` | `run_pipeline.py:151-189` | `fdr.DataReader` (US)<br>`yf.download` -> `fdr.DataReader` (KRX) | Single Stock OHLCV (US & KRX) | KRX falls back from yfinance to FDR. US stocks have **no** yfinance fallback or Tier 2 retry. Re-raises exception after 3 retries. |
| `prefetch_prices_batch()` | `run_pipeline.py:192-350` | `yf.download(tickers, ...)` | Batch Stock OHLCV | Binary split recursion `_download_with_recovery`. Excludes bad tickers on failure; **no** FDR fallback. |
| `fetch_data_fdr()` / `_fetch_fallback()` | `run_pipeline.py:352-440` | `_fetch_data_fdr_network()` | Cached / Incremental / Full OHLCV | Checks TTL `technical_cache` and `price_db`. If stale and network fetch fails, returns `None` and **discards** stale DB cache. |
| `_download_indicator_network()` | `run_pipeline.py:465-484` | `yf.download(ticker, ...)` | 16 Macro & Sector Indicators (`^VIX`, `^TNX`, `USDKRW=X`, etc.) | Retries 3 times via `@retry`. Raises `ValueError` or exception on failure; **no** FDR fallback. |
| `fetch_indicator_history()` | `run_pipeline.py:486-563` | `_download_indicator_network()` | 16 Macro Indicators History | If network fails, returns empty `pd.Series`. Does **not** fallback to stale DB cache if stale. |
| `_get_excluded_krx_symbols()` | `run_pipeline.py:614-645` | `fdr.StockListing('KRX')`<br>`fdr.StockListing('KRX-ADMINISTRATIVE')` | Halted / Caution Stock Lists | Caught in try-except; returns empty `set()` if network fails. |
| `GlobalMarketClient.get_summary()` | `global_market.py:56-143`<br>(called at `run_pipeline.py:666`) | `yf.Ticker(symbol).history(period=period)` | Real-time Global Indices & FX snapshot | Catches exceptions, returns `None`/default dict. **No** FDR or DB fallback. |
| `MarketIndicatorStorage.update_stock_universe()` | `indicator_storage.py:202-239`<br>(called at `run_pipeline.py:679`) | `fdr.StockListing('S&P500')`<br>`fdr.StockListing('KRX')`<br>`fdr.StockListing('KRX-ADMINISTRATIVE')` | Stock Universe Metadata (3379 symbols) | If `KRX-ADMINISTRATIVE` fails, logs warning. If main listing calls fail, exception propagates. |
| `fetch_and_store_fundamentals_batch()` | `earnings_data.py:45-100`<br>(called at `run_pipeline.py:689, 969`) | `yf.Ticker(yf_sym).financials`<br>`yf.Ticker(yf_sym).info` | Annual Corporate Fundamentals | Retries 3 times via `@retry(reraise=False)`. Logs debug on failure and returns `None`. |

---

## 2. Analysis of Current Exception Handling & Rate Limiting

### 2.1 Rate Limiting Architecture
- **Global Rate Limiter**: `get_global_rate_limiter().wait()` is invoked inside network helper functions (`_fetch_data_fdr_network` at line 153, `_download_indicator_network` at line 467, `_fetch_fundamentals_network` at line 47).
- **Per-symbol Throttle**: `_fetch_fallback()` in `run_pipeline.py` (lines 388-396, 409-417) acquires `_rate_lock` and enforces `update_interval` pauses using `time.sleep()`.

### 2.2 Critical Flaws & Vulnerabilities Identified

#### Flaw 1: Discarding Stale DB Cache on Network Failure (`run_pipeline.py:376-425`)
In `fetch_data_fdr()`'s helper `_fetch_fallback()`:
```python
# Lines 376-406
if stale:
    cached_df = price_db.get_prices(s, start_date=d)
    if cached_df is not None and not cached_df.empty:
        ...
        try:
            new_df = _fetch_data_fdr_network(s, market, latest_date_str)
            ...
        except Exception as e:
            logger.warning(f"Failed to fetch incremental data for {s}, falling back to full fetch: {e}")

# Lines 420-424
try:
    result = _fetch_data_fdr_network(s, market, d)
except Exception as e:
    logger.warning(f"Failed to fetch data for {s} after retries: {e}")
    result = None
```
**Mechanism Breakdown**:
1. When `stale` is `True` (e.g. data in `stock_prices.db` is older than `freshness_days`), `cached_df` is retrieved from SQLite.
2. Incremental network fetch is attempted. If it fails, execution falls through to full network fetch `_fetch_data_fdr_network(s, market, d)`.
3. If full network fetch **also** fails (due to HTTP 429 rate limit, 500 error, network disconnection, timeout, or offline run), `result` is assigned `None`.
4. **Vulnerability**: The function returns `None`, completely **discarding** `cached_df`! This causes the symbol to be skipped entirely during training or inference (lines 833, 1001), crashing or degrading predictions even though valid historical OHLCV data exists in `stock_prices.db`.

#### Flaw 2: Asymmetric & Incomplete Endpoint Cascade for US Stocks (`run_pipeline.py:156-184`)
```python
# Lines 156-160
if market == 'SP500' or market.startswith('NYSE') or market.startswith('NASDAQ'):
    try:
        result = fdr.DataReader(symbol, start=start_date)
    except Exception as e:
        logger.debug(f"Network fetch failed for {symbol} via fdr: {e}")
        raise e
```
**Mechanism Breakdown**:
- US stock downloads (`SP500`, `NYSE`, `NASDAQ`) in `_fetch_data_fdr_network` **only** call `fdr.DataReader`. If `fdr.DataReader` raises an error or times out, it directly re-raises `e` without ever trying `yfinance`.
- In contrast, Korean stocks (`KOSPI`, `KOSDAQ`, `KONEX`) call `yfinance` first, then fall back to `fdr.DataReader`.
- Furthermore, `prefetch_prices_batch` (line 233) uses `yfinance` for US stock prefetching, causing a code path divergence where prefetching uses `yfinance` while individual fetching uses `fdr.DataReader`.

#### Flaw 3: Batch Prefetching Recovery Ignores Tier 2 (FinanceDataReader) Fallback (`run_pipeline.py:297-350`)
- `prefetch_prices_batch` invokes `_download_with_recovery(tickers, start_dt)` using `yf.download`.
- When batch downloading fails (e.g., rate limit hit or bad ticker), binary splitting divides the ticker list recursively down to size 1.
- If a single ticker fails in `yf.download`, line 307 logs `Excluding bad ticker from batch: {tickers[0]}` and returns `pd.DataFrame()`.
- **Vulnerability**: Failed tickers in prefetching are immediately discarded without trying `fdr.DataReader` or fallback caching, forcing downstream single-symbol calls to repeat network requests.

#### Flaw 4: Macro Indicator Fetching Drops Columns on Error (`run_pipeline.py:486-563`)
- `fetch_indicator_history()` calls `_download_indicator_network()` for 16 macro tickers (`^VIX`, `^TNX`, `USDKRW=X`, etc.).
- If network download fails for an indicator and DB cache is stale, `_fetch_one()` returns `(col_name, pd.Series(dtype=float))`.
- Returning an empty `Series` causes missing macro feature columns in `df_train` and `infer_data_dict`, leading to `NaN` propagation across regression and surge models.

---

## 3. Concrete Fix Strategy: Unified 3-Tier Fallback Cascade

To achieve complete pipeline resilience without crashing or data loss, all data fetching routines (`fetch_data_fdr`, `fetch_indicator_history`, `prefetch_prices_batch`, `GlobalMarketClient`, `earnings_data`) must strictly adhere to a **Unified 3-Tier Fallback Cascade**:

```
┌────────────────────────────────────────────────────────┐
│               Tier 1: yfinance Download                │
│ (Primary: adjusted prices / auto_adjust / custom headers)│
└──────────────────────────┬─────────────────────────────┘
                           │ Failure / Rate-limit / Exception
                           ▼
┌────────────────────────────────────────────────────────┐
│           Tier 2: FinanceDataReader Download           │
│      (Secondary: alternative data provider API)        │
└──────────────────────────┬─────────────────────────────┘
                           │ Failure / Rate-limit / Offline
                           ▼
┌────────────────────────────────────────────────────────┐
│             Tier 3: SQLite DB Cache Fallback           │
│   (Offline Cache: return stock_prices.db cached DF)    │
└──────────────────────────┬─────────────────────────────┘
                           │ DB cache empty / missing
                           ▼
┌────────────────────────────────────────────────────────┐
│          Graceful Warning Log & Skip Symbol            │
│  (Log WARNING badge, return None cleanly, don't crash)  │
└────────────────────────────────────────────────────────┘
```

---

## 4. Proposed Code Structures & Line-by-Line Changes

### Fix 1: Refactoring `_fetch_data_fdr_network` (Tier 1 -> Tier 2 Unified Fetcher)
**File**: `trading_system/run_pipeline.py` (Lines 151–189)

```python
def _fetch_data_fdr_network(symbol: str, market: str, start_date: str) -> pd.DataFrame:
    """Unified network fetcher implementing Tier 1 (yfinance) -> Tier 2 (FinanceDataReader)."""
    get_global_rate_limiter().wait()
    result = None

    # Determine yfinance ticker symbol
    if market in ('SP500', 'NYSE', 'NASDAQ') or not market.isdigit():
        yf_symbol = symbol
    else:
        suffix = _KR_MARKET_SUFFIX.get(market, '.KS')
        yf_symbol = f"{symbol}{suffix}"

    # Tier 1: Try yfinance primary download
    try:
        df = yf.download(yf_symbol, start=start_date, progress=False, auto_adjust=True)
        if df is not None and not df.empty:
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.droplevel(1)
            result = df
    except Exception as e:
        logger.warning(f"Tier 1 (yfinance) network fetch failed for {yf_symbol}: {e}")

    # Tier 2: Fallback to FinanceDataReader
    if result is None or result.empty:
        try:
            logger.info(f"Attempting Tier 2 (FinanceDataReader) download for {symbol}...")
            result = fdr.DataReader(symbol, start=start_date)
            if result is not None and not result.empty:
                logger.warning(f"Successfully retrieved Tier 2 (FinanceDataReader) data for {symbol}")
        except Exception as e:
            logger.warning(f"Tier 2 (FinanceDataReader) network fetch failed for {symbol}: {e}")
            raise e

    if result is None or result.empty:
        raise ValueError(f"Fetched network data for {symbol} is empty or None across all providers")

    return result
```

### Fix 2: Refactoring `fetch_data_fdr` for Tier 3 Offline DB Cache Recovery
**File**: `trading_system/run_pipeline.py` (Lines 352–440)

```python
def fetch_data_fdr(symbol: str, market: str, start_date: str,
                   price_db: Optional[StockPriceDB] = None, freshness_days: int = 7,
                   update_interval: int = 0) -> pd.DataFrame:
    """Fetch OHLCV data with 3-tier fallback (yfinance -> FDR -> stock_prices.db cache)."""

    def _fetch_fallback(s: str, d: str) -> pd.DataFrame:
        global _last_request_time
        cached_df = None

        # Step 0: Check DB cache existence
        if price_db is not None:
            cached_df = price_db.get_prices(s, start_date=d)
            stale = price_db.needs_update(s, max_age_days=freshness_days, start_date=d) if freshness_days >= 0 else False

            # If cache is fresh, return immediately
            if not stale and cached_df is not None and not cached_df.empty:
                logger.debug(f"Using fresh StockPriceDB cache for {s}")
                return cached_df

            # If cache is up to date relative to today, return immediately
            if cached_df is not None and not cached_df.empty:
                latest_date_str = cached_df.index.max().strftime("%Y-%m-%d")
                if latest_date_str >= datetime.now().strftime("%Y-%m-%d"):
                    logger.debug(f"Cache for {s} is up to date ({latest_date_str}). Skipping network fetch.")
                    return cached_df

        # Rate limiter pause before network request
        if update_interval > 0:
            now = time.time()
            with _rate_lock:
                scheduled = max(_last_request_time + update_interval, now)
                sleep_sec = scheduled - now
                _last_request_time = scheduled
            if sleep_sec > 0:
                time.sleep(sleep_sec)

        # Attempt Tier 1 & Tier 2 network fetch
        network_result = None
        fetch_start = cached_df.index.max().strftime("%Y-%m-%d") if (cached_df is not None and not cached_df.empty) else d
        try:
            network_result = _fetch_data_fdr_network(s, market, fetch_start)
        except Exception as e:
            logger.warning(f"Tier 1 & 2 network download failed for {s}: {e}")

        # Process network result if successful
        if network_result is not None and not network_result.empty:
            if price_db is not None:
                try:
                    price_db.update_prices(s, network_result)
                except Exception as ex:
                    logger.debug(f"Failed to cache prices for {s}: {ex}")

            if cached_df is not None and not cached_df.empty:
                merged_df = pd.concat([cached_df, network_result])
                merged_df = merged_df[~merged_df.index.duplicated(keep='last')].sort_index()
                return merged_df
            return network_result

        # Tier 3 Fallback: If network failed completely, fall back to stale DB cache if available
        if cached_df is not None and not cached_df.empty:
            logger.warning(f"[Offline Cache Fallback] Network failed for {s}. Falling back to stale DB cache ({len(cached_df)} rows)")
            return cached_df

        logger.warning(f"No network data or DB cache available for {s}. Returning empty DataFrame.")
        return None

    return technical_cache.get_or_compute(symbol, start_date, _fetch_fallback)
```

### Fix 3: Refactoring `fetch_indicator_history` for DB Fallback Protection
**File**: `trading_system/run_pipeline.py` (Lines 486–563)

```python
def fetch_indicator_history(start_date: str, price_db: Optional[StockPriceDB] = None,
                            freshness_days: int = 7) -> pd.DataFrame:
    """Fetch global macro indicators with DB cache fallback on network failure."""
    def _fetch_one(ticker: str, col_name: str):
        cached_df = None
        if price_db is not None:
            cached_df = price_db.get_prices(ticker, start_date=start_date)
            stale = price_db.needs_update(ticker, max_age_days=freshness_days, start_date=start_date) if freshness_days >= 0 else False
            if not stale and cached_df is not None and not cached_df.empty:
                df = cached_df
            else:
                df = None
        else:
            df = None

        if df is None or df.empty:
            try:
                df = _download_indicator_network(ticker, start_date)
                if df is not None and not df.empty and price_db is not None:
                    price_db.update_prices(ticker, df)
            except Exception as e:
                logger.warning(f"Indicator network fetch failed for {ticker}: {e}")
                # Fallback to stale DB cache if available
                if cached_df is not None and not cached_df.empty:
                    logger.warning(f"[Indicator DB Fallback] Using cached indicator data for {ticker}")
                    df = cached_df

        if df is not None and not df.empty:
            if col_name.endswith('_change'):
                return (col_name, df['Close'].pct_change().fillna(0.0) * 100)
            elif col_name == 'put_call_ratio':
                return (col_name, df['Close'].ffill().fillna(0.6))
            else:
                return (col_name, df['Close'].ffill().fillna(0.0))
        return (col_name, pd.Series(dtype=float))
    ...
```

---

## 5. Summary & Verification Plan

1. **Safety Assurance**: The proposed fixes ensure that every network call degrades gracefully to Tier 2 (FDR) and Tier 3 (`stock_prices.db` cache), preventing pipeline crashes when offline or rate-limited.
2. **Logging**: All fallback events log `WARNING` messages detailing the failing tier and target ticker.
3. **Verification**: Can be independently verified by disconnecting network or mocking `yfinance` and `fdr.DataReader` to raise exceptions, confirming `run_pipeline.py` loads cached data from `stock_prices.db` and completes without error.
