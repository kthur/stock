# Fundamental Data Fetching & Retry Logic Analysis Report

**Explorer 2 — Milestone 1**  
**Working Directory**: `d:\Finance\code\stock\.agents\explorer_m1_2`  
**Target Files Analyzed**:
- `trading_system/src/data_layer/earnings_data.py`
- `trading_system/src/data_layer/indicator_storage.py`
- `trading_system/src/persistence/database.py`
- `trading_system/src/ai/prediction_model.py`
- `trading_system/run_pipeline.py`
- `trading_system/tests/test_tuning_and_retry.py`

---

## Executive Summary

Fundamental financial metrics (`revenue`, `operating_income`, `net_income`, `eps`, `shares_outstanding`, `dividend_per_share`) are critical features used by the XGBoost regression and surge prediction models.

Currently, fundamental data is retrieved primarily via **Yahoo Finance** (both via async raw REST API endpoints and synchronous `yfinance.Ticker` library calls). **FinanceDataReader** is heavily utilized across the project for daily stock OHLCV prices and universe listings, but is **not currently connected** as a fundamental fallback in `earnings_data.py`.

This investigation identifies key vulnerability points in rate-limiting, retry logic, missing headers/User-Agent configurations, and offline DB fallbacks, and establishes a concrete design strategy for Milestone 2 implementation.

---

## Section 1: Detailed Findings & Code Structure Analysis

### 1. Fundamental Fetching Mechanics in `earnings_data.py`

`earnings_data.py` handles fetching corporate annual financial data and storing it in the `stock_fundamentals` table in `market_indicators.db`.

#### Symbol Normalization
- **Lines 23–28 (`_yf_ticker`)**:
  Maps local market symbols to Yahoo Finance format.
  - Korean stocks (numeric digits like `005930`): append `.KS` for KOSPI/KRX or `.KQ` for KOSDAQ/KONEX.
  - US/SP500 stocks (alphabetic symbols like `AAPL`): stripped and converted to uppercase.

#### Synchronous Network Fetching
- **Lines 45–82 (`_fetch_fundamentals_network`)**:
  - Direct call to `yfinance.Ticker(yf_sym).financials` and `ticker.info`.
  - Parses annual income statement columns (`Total Revenue`/`Revenue`, `Operating Income`, `Net Income`, `Diluted EPS`/`Basic EPS`).
  - Fetches `sharesOutstanding` and `dividendRate` / `dividendYield` from `ticker.info`.
  - Coerces missing fields to `0.0`.

#### Asynchronous Network Fetching
- **Lines 104–184 (`async_fetch_fundamentals`)**:
  - Sends direct HTTP GET to `https://query2.finance.yahoo.com/v10/finance/quoteSummary/{yf_sym}?modules=incomeStatementHistory,defaultKeyStatistics,summaryDetail`.
  - Sets custom User-Agent header (Chrome 120 on Windows 10).
  - Parses JSON response for annual `incomeStatementHistory`, `defaultKeyStatistics`, and `summaryDetail`.

#### Batch Orchestration & Synchronization
- **Lines 186–307 (`fetch_and_store_fundamentals_batch`)**:
  - Uses `storage.get_fundamental_meta()` to skip symbols fetched within `expiry_days` (default: 90 days from `TradingConfig`).
  - Spawns a dedicated thread with an `asyncio` event loop.
  - Controls concurrency via `asyncio.Semaphore(5)`.
  - Dual-attempt sequence per symbol:
    1. Try `async_fetch_fundamentals(sym, market)`.
    2. If `async_fetch_fundamentals` yields `None`, fall back to running synchronous `fetch_fundamentals` in a threadpool executor.
  - Updates `fundamental_cache_meta` table with today's date for every symbol attempted.
  - Performs batch insertion into `stock_fundamentals` SQLite table via `storage.save_fundamentals(df_fun)`.

---

### 2. Rate-Limiting, Retry Logic, and Error Handling Evaluation

#### Rate Limiting Architecture
- **Global Rate Limiter** (`src/utils/rate_limiter.py`):
  - Uses `GlobalRateLimiter` singleton initialized with `min_interval_seconds = 1.0`.
  - Sync call: `get_global_rate_limiter().wait()` (Thread lock + `time.sleep`).
  - Async call: `await get_global_rate_limiter().async_wait()` (Thread lock + `asyncio.sleep`).
- **Interaction with Batch Processing**:
  - `fetch_and_store_fundamentals_batch` uses `asyncio.Semaphore(5)`.
  - Because `async_wait()` enforces a 1.0s gap between requests across all threads and coroutines, total throughput is capped at 1 request per second regardless of the semaphore count.

#### Existing Retry Logic (`tenacity`)
- **Synchronous Path (`_fetch_fundamentals_network`, lines 39–44)**:
  ```python
  @retry(
      stop=stop_after_attempt(3),
      wait=wait_exponential(multiplier=1, min=2, max=10),
      retry=(retry_if_result(is_empty_result) | retry_if_exception_type(Exception)),
      reraise=False
  )
  ```
  - Up to 3 attempts with exponential backoff (2s, 4s, 8s...).
  - Retries on any empty result or unhandled exception.
- **Asynchronous Path (`async_fetch_fundamentals`, lines 104–184)**:
  - **No tenacity retry decorator present!**
  - Performs a single HTTP GET request without retry on network failure or HTTP rate limiting (429/503).
  - On non-200 response or timeout/parsing error, immediately logs debug message and returns `None`.

#### Gaps & Limitations
1. **Unprotected Asynchronous Calls**: `async_fetch_fundamentals` lacks retry/backoff wrappers, delegating failure handling directly to the synchronous fallback.
2. **Missing Custom Headers in Sync yfinance**: `_fetch_fundamentals_network` relies on `yfinance.Ticker`, which internally issues requests without standard browser headers unless yfinance session defaults are configured globally.
3. **Metadata Pollution on Failure**: `fetch_and_store_fundamentals_batch` (line 257) saves `save_fundamental_meta(sym, today)` even when `df_fun` is `None` (failed fetch). This marks failed tickers as "fetched today", suppressing re-attempt for the next 90 days.
4. **Lack of Alternative Online Data Source (FDR)**: If Yahoo Finance blocks calls or fails for a KRX symbol, there is currently no fallback attempt to FinanceDataReader or local KRX market listings.

---

### 3. Merging Fundamentals & Offline DB Cache Architecture

#### Feature Merging in AI Models (`prediction_model.py`)
- **Lines 761–830 (`merge_fundamentals`)**:
  - Merges historical fundamental statements onto daily price time series by forward-filling annual fiscal metrics (`revenue`, `operating_income`, `net_income`, `eps`, `dividend_per_share`).
  - Computes 1-year YoY growth rates:
    $$\text{revenue\_growth\_1y} = \frac{\text{revenue}_t - \text{revenue}_{t-1}}{|\text{revenue}_{t-1}|}$$
    $$\text{eps\_growth\_1y} = \frac{\text{eps}_t - \text{eps}_{t-1}}{|\text{eps}_{t-1}|}$$
  - Computes operational financial ratios:
    - `operating_margin` = $\text{operating\_income} / \text{revenue}$
    - `net_profit_margin` = $\text{net\_income} / \text{revenue}$
    - `eps_yield` = $\text{eps} / \text{Close}$
    - `revenue_to_market_cap` = $\text{revenue} / \text{market\_cap}$
    - `dividend_yield` = $\text{dividend\_per\_share} / \text{Close}$
  - Missing or un-fetched fundamental values default safely to `0.0`.

#### Database Storage Layer (`indicator_storage.py` & `database.py`)
- Table `stock_fundamentals`:
  - Primary Key: `(symbol, date)`
  - Columns: `symbol`, `date`, `revenue`, `operating_income`, `net_income`, `eps`, `shares_outstanding`, `dividend_per_share`.
- Table `fundamental_cache_meta`:
  - Primary Key: `symbol`
  - Column: `last_fetched` (YYYY-MM-DD)
- **Batch Query Performance**: `storage.get_all_fundamentals(symbols)` chunks queries into batches of 900 parameters to avoid SQLite maximum parameter limits, returning cached historical fundamentals rapidly.

---

## Section 2: Concrete Implementation Strategy for Milestone 2

To achieve complete resilience against network outages, rate limits, and service blocking, the following 4-tier fallback and session configuration strategy is recommended for Milestone 2:

```
[Tier 1: Async yfinance API + Custom Headers + Retry]
                     │ (Failure / Rate Limit 429)
                     ▼
[Tier 2: Sync yfinance Ticker + Rate Limiter]
                     │ (Failure / Empty Financials)
                     ▼
[Tier 3: Secondary Provider (FinanceDataReader / KRX Direct)]
                     │ (Failure / Missing)
                     ▼
[Tier 4: Local DB Cache Fallback (stock_fundamentals in market_indicators.db)]
```

### Strategic Action Items

1. **Centralized Browser User-Agent & Session Setup**:
   - Establish standard request headers mimicking modern desktop browsers:
     `User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36`
   - Apply headers to both `aiohttp` requests in `async_fetch_fundamentals` and configure yfinance default session headers globally.

2. **Add Async Retry Logic with Tenacity / Backoff**:
   - Wrap `async_fetch_fundamentals` with exponential backoff on HTTP 429/500/503 errors and network connection timeouts.

3. **Implement FinanceDataReader (FDR) / Secondary Fallback**:
   - Create a fallback parser for Korean and US symbols using `FinanceDataReader` or local snapshot data when yfinance calls fail completely.

4. **Sanitize Cache Metadata Logging**:
   - Only call `storage.save_fundamental_meta(sym, date)` when fundamental data is **successfully fetched** (`df_fun is not None and not df_fun.empty`).
   - If a fetch fails due to network error, do not write a fresh timestamp to metadata, allowing the system to retry on subsequent pipeline executions once network connectivity is restored.

5. **Offline Mode Enforcement**:
   - When `freshness_days < 0` or offline mode is flagged, bypass network attempts entirely and immediately rely on existing cached rows in `stock_fundamentals`.

---

## Section 3: Invalidation & Evidence Verification

- **Code Inspection**:
  - `earnings_data.py`: lines 45-82, 104-184, 186-307
  - `indicator_storage.py`: lines 94-111, 330-389, 436-450
  - `prediction_model.py`: lines 761-830
  - `run_pipeline.py`: lines 686-692, 799-801, 840-844, 967-970
- **Test Suite Verification**:
  - Executing `pytest trading_system/tests/test_tuning_and_retry.py -v` validates rate limiter coordination and retry mocks.
