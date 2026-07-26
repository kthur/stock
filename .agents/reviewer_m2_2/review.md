# Milestone 2 Review Report — Reviewer 2

**Reviewer**: Reviewer 2 (`reviewer_m2_2`)  
**Date**: 2026-07-15  
**Scope**: Milestone 2 Fundamental Data Fetching, Async Retries, Header Injection, Metadata Sanitization, Offline Mode & Test Suite Verification  
**Verdict**: **FAIL / REQUEST_CHANGES**

---

## 1. Executive Summary

Reviewer 2 evaluated the Milestone 2 changes in `trading_system/src/data_layer/earnings_data.py` and executed the test command `.venv\Scripts\python.exe -m pytest trading_system/tests/test_tuning_and_retry.py`. 

While the implementation in `earnings_data.py` (async retries, header injection, metadata sanitization, and offline mode) is correctly implemented, the test suite execution **FAILED** with 3 test failures out of 6 tests. The failure is caused by an architectural mismatch between Worker 1's Tier 1 (`yfinance`) -> Tier 2 (`FinanceDataReader`) fallback refactoring in `run_pipeline.py` and the un-updated mock assumptions in `test_tuning_and_retry.py`.

Per reviewer guidelines, work products with failing test verification must receive a **FAIL / REQUEST_CHANGES** verdict.

---

## 2. Verification Findings

### Requirement 1: Async Retry Logic, Exponential Backoff, and Custom User-Agent Injection
- **Status**: **PASS**
- **Location**: `trading_system/src/data_layer/earnings_data.py`, `async_fetch_fundamentals()` (lines 104–199)
- **Observations**:
  - Sets custom User-Agent header: `headers = {"User-Agent": DEFAULT_USER_AGENT}` using `DEFAULT_USER_AGENT` from `src.utils.http_session`.
  - Coordinates global rate limiter with `await get_global_rate_limiter().async_wait()`.
  - Implements exponential backoff loop (`2 ** attempt`) for transient HTTP status codes `(429, 500, 502, 503, 504)` and connection exceptions.

### Requirement 2: Metadata Sanitization in Batch Fetching
- **Status**: **PASS**
- **Location**: `trading_system/src/data_layer/earnings_data.py`, `fetch_and_store_fundamentals_batch()` (lines 272–282)
- **Observations**:
  - `storage.save_fundamental_meta(sym, current_time.strftime("%Y-%m-%d"))` is executed strictly inside `if df_fun is not None and not df_fun.empty:`.
  - Prevents writing corrupt cache metadata timestamps when data fetches fail or return empty datasets.

### Requirement 3: Offline Mode Support (`expiry_days < 0`)
- **Status**: **PASS**
- **Location**: `trading_system/src/data_layer/earnings_data.py`, `fetch_and_store_fundamentals_batch()` (lines 228–231)
- **Observations**:
  - Guard `if expiry_days < 0:` logs `"[Offline Mode] Skipping fundamental network fetching..."` and returns `0` immediately.
  - Complesly bypasses async task creation and external network calls in offline mode.

### Requirement 4: Test Suite Execution Verification
- **Status**: **FAIL**
- **Command**: `.venv\Scripts\python.exe -m pytest trading_system/tests/test_tuning_and_retry.py`
- **Output Summary**: 3 passed, 3 failed (out of 6 tests).

#### Failure Details:

1. **`test_fetch_data_fdr_retry_success` (FAIL)**
   - **Error**: `AssertionError: 0 != 3` (`mock_fdr.call_count` was 0 instead of 3).
   - **Root Cause**: `fetch_data_fdr` was refactored by Worker 1 to attempt Tier 1 (`yfinance`) first before Tier 2 (`FinanceDataReader`). The test only patched `FinanceDataReader.DataReader`, so unmocked `yfinance` succeeded or bypassed Tier 2, leaving `mock_fdr` uncalled.

2. **`test_fetch_data_fdr_max_retries_fail` (FAIL)**
   - **Error**: `AssertionError: False is not true` (`result is None` evaluated to `False`).
   - **Root Cause**: Unmocked Tier 1 (`yfinance`) returned data when `FinanceDataReader` was mocked to fail, preventing `fetch_data_fdr` from returning `None`.

3. **`test_fetch_indicator_history_retry` (FAIL)**
   - **Error**: `AssertionError: 1 != 2` (`mock_yf.call_count` was 1 instead of 2).
   - **Root Cause**: `_download_indicator_network` was refactored to fall back to Tier 2 (`FinanceDataReader`) on the first `yfinance` failure rather than retrying `yfinance`. Tier 2 succeeded on the first attempt, so `mock_yf` was only called once.

---

## 3. Required Action Items for Worker 1

1. **Update Unit Test Mocks in `test_tuning_and_retry.py`**:
   - Update `test_fetch_data_fdr_retry_success` and `test_fetch_data_fdr_max_retries_fail` to mock both Tier 1 (`yfinance.download`) and Tier 2 (`FinanceDataReader.DataReader`) to properly simulate tier fallback and retry counts.
   - Update `test_fetch_indicator_history_retry` to reflect the multi-tier fallback architecture (or mock Tier 2 failure if testing multiple Tier 1 retries).
2. **Re-run Test Suite**: Confirm all 6 tests in `test_tuning_and_retry.py` pass cleanly.

---

## 4. Verdict

**Verdict**: **REQUEST_CHANGES** (FAIL)
