# Summary of Changes — Milestone 1: Network Exception Hardening & Retries

## Modified Files

### 1. `trading_system/run_pipeline.py`
- **Decoupled Tier 1 Exception Swallowing**: Introduced `_fetch_yf_primary(yf_symbol, start_date)` helper decorated with Tenacity's `@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), retry=(retry_if_result(is_empty_result) | retry_if_exception_type(Exception)), reraise=True)`.
  - Ensures transient network errors and empty responses in `yf.download` undergo up to 3 automatic exponential backoff retries on Tier 1 before `_fetch_data_fdr_network` falls back to Tier 2 (`FinanceDataReader`).
- **Batch Download Retries & Exponential Backoff**: Added `_download_yf_batch_with_retry(tickers, start_dt, max_attempts=3)` helper in `prefetch_prices_batch` / `_download_with_recovery`.
  - On HTTP 429 rate limit errors or network exceptions, retries the batch up to 3 times with exponential backoff delay (2s -> 4s -> 8s -> 10s max) before resorting to binary splitting, preventing IP block escalation.

### 2. `trading_system/src/data_layer/market_data_handler.py`
- **Hardened `MarketDataHandler`**: Added `_fetch_historical_yf_with_retry(symbol, start_date, yf_period, period)` decorated with `@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), retry=retry_if_exception_type(Exception) & retry_if_not_exception_type(CircuitBreakerOpenException), reraise=True)`.
  - Ensures historical data fetches handle HTTP 429 rate limits, connection timeouts, and empty responses with 3 exponential backoff retries.
  - Refactored `fetch_historical_data` to delegate yfinance calls to `_fetch_historical_yf_with_retry`.

### 3. `trading_system/tests/test_network_hardening.py`
- Added new test file with 5 dedicated unit test cases validating:
  - `_fetch_yf_primary` retries on network exception and empty DataFrame.
  - `_fetch_data_fdr_network` falls back to Tier 2 only after Tier 1 retries are exhausted.
  - `MarketDataHandler._fetch_historical_yf_with_retry` retries on empty/failed response.
  - `MarketDataHandler` circuit breaker open status immediately blocks API calls without retrying.
