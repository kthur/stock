# Milestone 2 Review Report

## Review Summary

**Verdict**: REQUEST_CHANGES

The implementation of `src/utils/http_session.py`, global User-Agent configuration, and fundamental cache logic is solid. However, the 3-tier fallback logic in `run_pipeline.py` introduces side-effects that cause existing unit tests in `trading_system/tests/test_tuning_and_retry.py` to fail. Specifically:
1. `_fetch_data_fdr_network()` executes `yfinance.download()` before falling back to `FinanceDataReader.DataReader()`. Unit tests mocking `FinanceDataReader.DataReader` fail because `yfinance` intercepts the request over the live network, reducing `mock_fdr.call_count` to 0 instead of expected retries.
2. `_download_indicator_network()` catches and swallows exceptions from Tier 1 (`yf.download()`), immediately triggering Tier 2 (`fdr.DataReader()`) within a single attempt. This prevents Tenacity's `@retry` decorator on `_download_indicator_network()` from retrying Tier 1 operations, causing retry test assertions (`mock_yf.call_count == 2`) to fail.

---

## Findings

### [Major] Finding 1: Broken Retry Test Assertions & Exception Swallowing in Indicator Download

- **What**: `_download_indicator_network()` catches `yf.download()` exceptions internally and falls through to `fdr.DataReader()`.
- **Where**: `trading_system/run_pipeline.py`, lines 463-485 (`_download_indicator_network`)
- **Why**: Swallow of Tier 1 exception prevents Tenacity's `@retry` from triggering a retry attempt on Tier 1 `yf.download`. Instead, Tier 2 is called on attempt 1, returning data and short-circuiting the retry decorator. This causes unit test `test_fetch_indicator_history_retry` in `test_tuning_and_retry.py` to fail (`mock_yf.call_count` is 1 instead of 2).
- **Suggestion**: Ensure retry decorator behavior and fallback strategy are correctly decoupled or structured so that transient errors on the primary provider trigger provider-level retries before initiating secondary provider fallbacks, or re-raise network exceptions appropriately.

### [Major] Finding 2: Unhandled Unmocked `yfinance` in `fetch_data_fdr()` Unit Tests

- **What**: Calls to `fetch_data_fdr()` execute `yf.download()` as Tier 1 before reaching `fdr.DataReader()`.
- **Where**: `trading_system/run_pipeline.py`, lines 168-186 (`_fetch_data_fdr_network`) and `test_tuning_and_retry.py`
- **Why**: In `test_fetch_data_fdr_retry_success` and `test_fetch_data_fdr_max_retries_fail`, `FinanceDataReader.DataReader` is mocked, but `yf.download` is unmocked. `yf.download` succeeds over live network requests, causing Tier 2 `mock_fdr` never to be called (`call_count == 0` instead of 3).
- **Suggestion**: Ensure `fetch_data_fdr()` test cases in `test_tuning_and_retry.py` mock both `yfinance.download` and `FinanceDataReader.DataReader` or respect data provider precedence flags, ensuring test suite passes cleanly without network leaks.

---

## Verified Claims

- Custom browser `User-Agent` (`Chrome/124.0.0.0`) in `http_session.py` → verified via inspection and monkeypatch execution → **PASS**
- Centralized `requests.Session` header monkeypatching via `setup_global_http_headers()` → verified via code inspection and safety guards (`_GLOBAL_PATCHED`) → **PASS**
- Fundamental metadata cache update hygiene (`save_fundamental_meta` only called on valid non-empty fundamental fetch) in `earnings_data.py` → verified via inspection → **PASS**
- Offline mode bypass (`expiry_days < 0`) in `earnings_data.py` and `fetch_data_fdr()` → verified via inspection → **PASS**
- Unit test suite execution (`test_tuning_and_retry.py`) → executed via `pytest` → **FAIL** (3 failed tests in `test_tuning_and_retry.py`)

---

## Coverage Gaps

- Secondary network provider error handling under rate limits — medium risk — recommend verifying provider exception propagation under full offline/simulated HTTP 429 conditions.

---

## Unverified Items

- Live real-world rate limit throttling under simultaneous 3379 symbol load — requires real-world pipeline run.
