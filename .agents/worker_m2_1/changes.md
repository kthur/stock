# Detailed Implementation Changes — Milestone 2 (Worker 1)

## Summary of Changes

Milestone 2 addresses network resilience, HTTP User-Agent session headers, and a robust 3-tier fallback data architecture (yfinance -> FinanceDataReader -> SQLite Cache) across the stock trading system.

---

## Files Created & Modified

### 1. `trading_system/src/utils/http_session.py` (New File)
- **`DEFAULT_USER_AGENT`**: Defined browser User-Agent string `"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"`.
- **`get_configured_session()`**: Returns a global `requests.Session` configured with:
  - Custom browser headers (`User-Agent`, `Accept`, `Accept-Language`, `Connection`).
  - `HTTPAdapter` with `pool_connections=20`, `pool_maxsize=20`.
  - `urllib3.util.Retry(total=3, backoff_factor=1.0, status_forcelist=[429, 500, 502, 503, 504])`.
- **`setup_global_http_headers()`**: Dynamically patches `requests.Session.__init__` default headers globally so both `yfinance` and `FinanceDataReader` HTTP calls automatically transmit browser headers system-wide.

### 2. `trading_system/run_pipeline.py` (Modified)
- **Global Headers Initialization**: Invoked `setup_global_http_headers()` at pipeline module import/startup.
- **Unified Network Fetcher (`_fetch_data_fdr_network`)**:
  - Refactored to execute Tier 1 (`yfinance`) -> Tier 2 (`FinanceDataReader`) fallback across all market tickers (US & Korean stocks).
- **Tier 3 Offline Cache Fallback (`fetch_data_fdr`)**:
  - Eliminated the critical flaw where stale DB cache was discarded when network download failed.
  - Returns cached OHLCV data from `StockPriceDB` (`stock_prices.db`) if network requests fail or hit rate limits, logging a `WARNING` banner and continuing execution without crashing.
- **Global Macro Indicators Fallback (`_download_indicator_network` & `fetch_indicator_history`)**:
  - Implemented Tier 1 (`yfinance`) -> Tier 2 (`FinanceDataReader`) -> Tier 3 (`StockPriceDB` cached indicator data) fallback chain for macro indicator series (`vix_change`, `us10y`, `usdkrw_change`, etc.).

### 3. `trading_system/src/data_layer/earnings_data.py` (Modified)
- **Async Retries & Headers (`async_fetch_fundamentals`)**:
  - Standardized request headers using `DEFAULT_USER_AGENT`.
  - Added async retry loop with exponential backoff on HTTP rate limit (429), server errors (500, 502, 503, 504), connection failures, and timeouts.
- **Sanitized Cache Metadata (`fetch_and_store_fundamentals_batch`)**:
  - Updated `storage.save_fundamental_meta(sym, date)` to execute ONLY when `df_fun is not None and not df_fun.empty`.
  - Prevents transient network failures from locking symbols out of retry attempts for 90 days.
- **Offline Mode Bypass**:
  - Added immediate return check when `expiry_days < 0` to bypass fundamental network calls and rely entirely on cached rows in `market_indicators.db`.
