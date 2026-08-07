## 2026-08-06T21:50:30Z
You are Worker 1 for Milestone 1: Network Exception Hardening & Retries.

Working directory: d:\Finance\code\stock\.agents\worker_m1
Original request file: d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md

OBJECTIVE:
Implement network exception hardening, exponential backoff retries, and timeout handling across `trading_system/run_pipeline.py` and `trading_system/src/data_layer/market_data_handler.py`.

TASKS:
1. **Decouple Tier 1 Exception Swallowing in `run_pipeline.py`**:
   - In `_fetch_data_fdr_network` (lines ~163–195), `try/except Exception as e:` catches `yf.download` errors and swallows them into log debug statements. This prevents Tenacity's `@retry` decorator from retrying yfinance on transient errors.
   - Refactor Tier 1 fetch into a helper `_fetch_yf_primary(symbol, start_date)` decorated with `@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), retry=(retry_if_result(is_empty_result) | retry_if_exception_type(Exception)), reraise=True)` so network timeouts/errors trigger automatic exponential backoff retries on Tier 1 before falling back to Tier 2 (`FinanceDataReader`).
2. **Add Retries & Backoff to Batch Prefetching (`run_pipeline.py`)**:
   - In `prefetch_prices_batch` / `_download_with_recovery` (lines ~310–347), wrap `yf.download(tickers, ...)` with exponential backoff retry logic. Replace immediate binary splitting on HTTP 429 rate limits with exponential backoff delay to avoid escalating IP blocks.
3. **Harden `MarketDataHandler` (`trading_system/src/data_layer/market_data_handler.py`)**:
   - Ensure `_fetch_yf_with_retry` and `fetch_historical_data` handle rate limits (HTTP 429), connection timeouts, and empty responses with exponential backoff retries.
4. **Verification**:
   - Run the test suite using `.venv\Scripts\python.exe -m pytest trading_system/tests/ -v` and `.venv\Scripts\python.exe -m pytest tests/ -v`.
   - Ensure all existing tests pass 100%.
