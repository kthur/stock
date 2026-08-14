# Explorer 1 Survey Report: Data Quality, Corporate Action Sanity Gates & API Retry Backoff Jitter

**Target Repository**: `d:/Finance/code/stock`  
**Date**: 2026-08-12  
**Investigator**: Explorer 1  
**Scope**: R1 (Data Quality & Corporate Action Sanity Gates, DataFrameCache) and R4 API (External API Retry Loops & Backoff Jitter)

---

## Executive Summary

1. **Data Quality & Corporate Action Sanity Gates (R1)**:
   - **Ingestion & Validation**: Price data is ingested across multi-tier networks (`yfinance`, `FinanceDataReader`, Naver Financial Chart XML, PyKRX, Stooq CSV) in `trading_system/run_pipeline.py` and validated by `DataValidator.validate_price_data` (`trading_system/src/data_layer/data_validator.py`).
   - **Corporate Action & Price Spike Handling Defect**: Stock split adjustment is handled by `CorporateActionAdjuster` (`trading_system/src/data_layer/price_adjuster.py:17-61`), but it is ONLY called when `tier_source == 'raw'`. It is bypassed for `yfinance` fetches and cached prices in SQLite (`StockPriceDB`). Furthermore, single-day abnormal price spikes (> 300% single-day jump or unadjusted split) pass `DataValidator.validate_price_data` because `DataValidator` only flags series where >5% of all rows have >100% returns (`extreme_ratio > 0.05`). Single isolated spikes pass unchecked and pollute `StockPriceDB` and downstream technical indicators.
   - **DataFrameCache Defect**: Implemented in `trading_system/src/utils/technical_cache.py:191-231`. Keyed on `(symbol, start_date)`. It relies on lazy expiration on lookup; stale entries (`age >= _ttl`) remain in memory until queried or evicted via LRU max capacity (`_max_items`). It lacks active background TTL auto-eviction and does not perform calendar date-change invalidation (e.g. crossing trading day / midnight).

2. **API Retry Backoff Jitter (R4 API Portion)**:
   - **External API Entry Points**: External calls are made via `earnings_data.py` (Yahoo Finance financials/quoteSummary), `market_data_handler.py` (yfinance, FDR, Naver, PyKRX, Stooq), `ecos_client.py` (BOK ECOS JSON), `fred_client.py` (FRED API JSON), `run_pipeline.py` (`_fetch_yf_primary`, `_download_indicator_yf`, `_download_indicator_network`), and `error_handler.py`.
   - **Retry & Backoff Defect**: Most retry logic uses `tenacity`'s `@retry(stop=..., wait=wait_exponential(...))` decorators or manual exponential backoffs (`await asyncio.sleep(2 ** attempt)`, `time.sleep(0.5 * (2 ** attempt))`). ALL of these backoffs are purely **deterministic** and lack randomized **jitter** (missing `jitter` parameter or `wait_random_exponential`). During concurrent requests (e.g. 50-100 parallel batch items hitting HTTP 429), all workers sleep and wake up at identical millisecond timestamps, creating thundering herd rate limit storms.

3. **Existing Unit Test Coverage**:
   - `trading_system/tests/test_data_validator.py`: Covers macro cleaning and basic price validation.
   - `tests/test_ecos_and_price_adjuster.py`: Covers 1:2 split detection in `CorporateActionAdjuster`.
   - `trading_system/tests/test_network_hardening.py`: Covers `_fetch_yf_primary` and `MarketDataHandler` retries.
   - `trading_system/tests/test_tuning_and_retry.py`: Covers rate limiter coordination and network indicator retry.
   - **Test Gap**: `DataFrameCache` has **NO** dedicated unit tests in the repository.

---

## 1. Deep-Dive Investigation: R1 (Data Quality & Corporate Action Sanity Gates)

### 1.1 Ingestion & Pipeline Cleaning Paths
- **Primary Ingestion Handler**: `trading_system/run_pipeline.py`
  - `_fetch_data_fdr_network(symbol, market, start_date)` (`lines 259-353`): Queries yfinance (Tier 1), FDR (Tier 2), Naver Direct XML (Tier 3 KRX), PyKRX (Tier 4 KRX), or Stooq CSV (Tier 3 US).
  - `fetch_data_fdr(symbol, market, start_date, price_db, ...)` (`lines 565-646`): Wraps data fetching inside `DataFrameCache.get_or_compute()`. Checks SQLite `StockPriceDB` first, falls back to network download, validates with `DataValidator.validate_price_data`, and upserts valid bars into `StockPriceDB`.
- **Database Persistence**: `trading_system/src/persistence/database.py`
  - `StockPriceDB` (`lines 387-590`): SQLite WAL-mode database (`stock_prices.db`) storing daily OHLCV bars indexed by `(symbol, date)`. Writes are serialized via `_write_lock` and `execute_sqlite_with_retry`.
- **Training Data Pre-filtering**: `trading_system/src/data_layer/pipeline_data_filter.py`
  - `filter_training_data(...)` (`lines 11-47`): Filters zero volume, 4-sigma return outliers, and symbols with history < 70 days before model training.

### 1.2 Flaw Analysis: Corporate Action & Price Spike Handling
- **Existing Logic**: `trading_system/src/data_layer/price_adjuster.py` (`lines 17-61`)
  ```python
  # CorporateActionAdjuster calculates overnight ratio: close / close.shift(1)
  split_mask = (ratios < (1.0 - self.split_threshold_pct)) | (ratios > (1.0 + 1.5 * self.split_threshold_pct))
  ```
  When triggered (ratio < 0.60 or > 1.60), `adjust_ohlcv` backward-adjusts prior prices (`df.loc[prior_mask, price_cols] *= r`) and adjusts volume (`df.loc[prior_mask, "Volume"] /= r`).
- **Defects & Uncaptured Scenarios**:
  1. **Selective Execution**: `CorporateActionAdjuster` is ONLY called inside `run_pipeline.py` at line 347 when `tier_source == 'raw'`. If data comes from `yfinance` or is read from SQLite `StockPriceDB`, `CorporateActionAdjuster` is NEVER executed.
  2. **Price Spike Gate Blindspot**: `DataValidator.validate_price_data` (`data_validator.py:144-153`):
     ```python
     daily_ret = valid_close.pct_change().abs().dropna()
     extreme_ratio = (daily_ret > 1.0).sum() / len(daily_ret)
     if extreme_ratio > 0.05:
         return False
     ```
     This check flags data ONLY if **more than 5% of all rows** have >100% daily change. A single single-day price spike (e.g. +300% to +1000% caused by unadjusted stock splits or bad data feed) in a 500-day series yields `extreme_ratio = 1/500 = 0.002` (0.2%), which passes `DataValidator` completely!
  3. **Data Contamination Propagation**: Corrupted single-day spikes pass validation, get stored into `StockPriceDB`, and pollute all calculated technical indicators (EMA, ATR, RSI, VCP) across the 23 strategies.

### 1.3 Flaw Analysis: `DataFrameCache` Implementation & Lifecycle
- **File Location**: `trading_system/src/utils/technical_cache.py` (`lines 191-231`)
- **Structure**:
  ```python
  class DataFrameCache:
      def __init__(self, ttl: float = 60.0, max_items: int = 200):
          self._ttl = ttl
          self._max_items = max_items
          self._cache: Dict[Tuple[str, str], pd.DataFrame] = {}
          self._timestamps: Dict[Tuple[str, str], float] = {}
          self._lock = threading.Lock()
  ```
- **Defects & Gaps**:
  1. **No Active Background TTL Eviction**: Expired items (`age >= self._ttl`) remain inside `self._cache` indefinitely until requested again or evicted when cache size exceeds `_max_items` (LRU eviction).
  2. **No Date-Change Invalidation**: Cache keys are `(symbol, start_date)`. When calendar date changes (e.g. midnight UTC/KST crossing or market open), `DataFrameCache` does not track date transitions. An entry stored under `(symbol, "2025-01-01")` will continue returning yesterday's cached DataFrame without re-querying fresh prices until `_ttl` seconds expire or cache is cleared manually.

### 1.4 Architectural Recommendations for R1
1. **Data Quality & Price Spike Sanity Filter**:
   - Enhance `DataValidator.validate_price_data` and/or `CorporateActionAdjuster` to detect single-day price spikes exceeding > 300% (`abs(pct_change) > 3.0`).
   - If an unadjusted split is detected (e.g., 1:2, 1:5, 1:10 split or reverse split ratio), automatically run split adjustment across the entire series before database persistence.
   - If a single-day non-split price spike > 300% is invalid/corrupted, reject or clamp the bar.
2. **`DataFrameCache` Hardening**:
   - Add TTL auto-eviction: implement an active sweep/purge method or purge expired keys during `_evict_if_needed()`.
   - Add Date-Change Invalidation: store the trading date or current calendar date alongside timestamps; automatically clear or invalidate cache entries when calendar date changes (`datetime.now().date() != cached_date`).

---

## 2. Deep-Dive Investigation: R4 API Portion (API Retry Backoff Jitter)

### 2.1 Inventory of External API Calls
| File | Function / Location | External API Target | Call Type |
|------|--------------------|---------------------|-----------|
| `src/data_layer/earnings_data.py` | `_fetch_fundamentals_network` (l.44) | Yahoo Finance (`yf.Ticker`) | Sync |
| `src/data_layer/earnings_data.py` | `async_fetch_fundamentals` (l.141) | `query2.finance.yahoo.com` REST API | Async (`aiohttp`) |
| `src/data_layer/market_data_handler.py` | `_fetch_yf_with_retry` (l.237), `_fetch_historical_yf_with_retry` (l.370) | `yfinance`, FDR, Naver, PyKRX, Stooq | Sync |
| `src/data_layer/ecos_client.py` | `fetch_statistic` (l.42), `fetch_korea_macro_rates` (l.104) | BOK ECOS API (`ecos.bok.or.kr`), FRED HTTP | Sync |
| `src/data_layer/fred_client.py` | `fetch_series_observations` (l.58) | FRED API (`api.stlouisfed.org`) | Sync |
| `run_pipeline.py` | `_fetch_yf_primary` (l.249), `_download_indicator_yf` (l.700), `_download_indicator_network` (l.716) | `yfinance`, FRED CSV, BOK ECOS | Sync |
| `src/utils/error_handler.py` | `retry_with_exponential_backoff` (l.46), `async_retry_with_exponential_backoff` (l.61) | Generic functions | Sync / Async |

### 2.2 Flaw Analysis: Deterministic Backoff & Lack of Jitter
- **Tenacity Decorators**:
  In `earnings_data.py:38`, `market_data_handler.py:231, 364`, `run_pipeline.py:243, 694, 710`, `llm_integration.py:253, 294, 321`:
  ```python
  @retry(
      stop=stop_after_attempt(3),
      wait=wait_exponential(multiplier=1, min=2, max=10),
      ...
  )
  ```
  `wait_exponential` computes deterministic backoff intervals ($2^0=1$, $2^1=2$, $2^2=4$, clamped to `min=2, max=10`).
- **Async Manual Retry Loop**:
  In `earnings_data.py:163, 233`:
  ```python
  if response.status in (429, 500, 502, 503, 504):
      if attempt < max_retries:
          await asyncio.sleep(2 ** attempt)
          continue
  ```
  `2 ** attempt` is completely deterministic (2s, 4s, 8s). When 10 concurrent async tasks hit Yahoo Finance rate limits (429), all 10 tasks sleep for exactly 2 seconds and retry at the exact same millisecond, triggering repeated 429 rate limit errors (thundering herd).
- **Sync Manual Retry Loops**:
  In `fred_client.py:103, 135` (`time.sleep(0.5 * (2 ** attempt))`) and `error_handler.py:52, 67` (`wait_time = self.retry_delay * (2 ** attempt)`).
- **Good Pattern Reference**:
  In `trading_system/src/data_layer/hybrid_storage.py:48`:
  ```python
  sleep_time = min(max_delay, base_delay * (2 ** attempt)) + random.uniform(0, 0.02)
  time.sleep(sleep_time)
  ```

### 2.3 Architectural Recommendations for R4 API
1. **Randomized Exponential Backoff Jitter for Tenacity**:
   Update `@retry` decorators to use tenacity's `wait_random_exponential` or add jitter:
   ```python
   from tenacity import wait_random_exponential
   @retry(stop=stop_after_attempt(3), wait=wait_random_exponential(min=1, max=10))
   ```
2. **Randomized Jitter in Async Retry Loops**:
   Update `async_fetch_fundamentals` in `earnings_data.py`:
   ```python
   sleep_sec = (2 ** attempt) + random.uniform(0.1, 1.0)
   await asyncio.sleep(sleep_sec)
   ```
3. **Randomized Jitter in Manual Sync Backoffs & `ErrorHandler`**:
   Add random jitter to `fred_client.py` and `error_handler.py`:
   ```python
   wait_time = (self.retry_delay * (2 ** attempt)) + random.uniform(0.05, 0.5)
   ```

---

## 3. Existing Unit Test Suite Inspection

### 3.1 Relevant Unit Tests Found
1. **Data Quality & Price Adjuster**:
   - `trading_system/tests/test_data_validator.py`: Tests `detect_shared_series_corruption`, `clean_macro_value`, and `validate_price_data`.
   - `tests/test_ecos_and_price_adjuster.py`: Tests `CorporateActionAdjuster` 1:2 stock split ratio detection and backward scaling.
2. **Network & Retry**:
   - `trading_system/tests/test_network_hardening.py`: Tests `_fetch_yf_primary` retries, fallback in `_fetch_data_fdr_network`, `MarketDataHandler` retries, CircuitBreaker OPEN state.
   - `trading_system/tests/test_tuning_and_retry.py`: Tests `_download_indicator_network` retries, `fetch_fundamentals` retry on empty data, and `GlobalRateLimiter` thread coordination.

### 3.2 Identified Unit Test Gaps
1. **No Tests for `DataFrameCache`**: There are zero unit tests verifying `DataFrameCache` thread-safety, TTL expiration, cache hit/miss behavior, or date-change invalidation.
2. **No Tests for Single-Day Price Spike (>300%) Filtering**: Existing tests only check basic DataFrame validity and 1:2 split adjustment in `CorporateActionAdjuster`, but do not test single-day price spike rejection or sanity gates.
3. **No Tests for Jitter Backoff Execution**: Existing retry tests mock `wait_exponential.__call__` to `0.001`, but do not verify jitter variance or anti-thundering-herd properties.

---

## 4. Summary Matrix of Required Fixes

| Item | File Path | Line Nos | Issue Description | Proposed Remediation |
|------|-----------|----------|-------------------|----------------------|
| **Price Spike Gate** | `src/data_layer/data_validator.py` | 144–153 | Single-day price spikes (>300%) or unadjusted splits pass if <5% of total rows | Add single-day price spike (>300%) detection and filtering gate in `validate_price_data` |
| **Split Adjuster Ingestion** | `run_pipeline.py` | 344–349 | `CorporateActionAdjuster` only runs when `tier_source == 'raw'`, bypassing yfinance & DB cache | Apply split/sanity check consistently on all fetched/cached DataFrames before DB storage |
| **DataFrameCache TTL** | `src/utils/technical_cache.py` | 191–231 | Expired TTL entries remain in cache indefinitely; no active eviction | Evict expired keys during `_evict_if_needed()` or periodic sweep |
| **DataFrameCache Date Invalidation** | `src/utils/technical_cache.py` | 200–214 | No calendar date-change tracking; stale data returned across trading days | Track trading/calendar date in cache key/metadata; auto-invalidate on date change |
| **Tenacity Retry Jitter** | `src/data_layer/earnings_data.py`, `src/data_layer/market_data_handler.py`, `run_pipeline.py` | Various | `wait_exponential` lacks jitter, causing thundering herd on rate limits | Replace `wait_exponential` with `wait_random_exponential` or add jitter |
| **Async API Retry Jitter** | `src/data_layer/earnings_data.py` | 163, 233 | `await asyncio.sleep(2 ** attempt)` is purely deterministic | Add `random.uniform(0.1, 1.0)` to async sleep duration |
| **Sync API Retry Jitter** | `src/data_layer/fred_client.py`, `src/utils/error_handler.py` | 103, 135; 52, 67 | `time.sleep(0.5 * (2 ** attempt))` lacks jitter | Add random jitter to manual sleep durations |
| **DataFrameCache Tests** | `tests/` / `trading_system/tests/` | New | Missing unit test coverage for `DataFrameCache` | Add `test_technical_cache.py` testing TTL, eviction, and date invalidation |
