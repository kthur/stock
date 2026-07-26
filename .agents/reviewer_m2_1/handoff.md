# Milestone 2 Review Handoff Report

**Reviewer**: Reviewer 1 (Milestone 2 Review)  
**Working Directory**: `d:\Finance\code\stock\.agents\reviewer_m2_1`  
**Verdict**: **REQUEST_CHANGES**  

---

## 1. Observation

- **HTTP Session Implementation (`trading_system/src/utils/http_session.py`)**:
  - Exported `DEFAULT_USER_AGENT`, `get_configured_session()`, and `setup_global_http_headers()`.
  - Monkeypatching of `requests.Session.__init__` correctly injects desktop Chrome `User-Agent` and `Accept-Language` headers without breaking `requests` initialization semantics.
  - Rate limiting, retries, and pooled adapters (20 connections) properly initialized.

- **Data Fetch & Indicator Cascade (`trading_system/run_pipeline.py`)**:
  - Added startup execution of `setup_global_http_headers()`.
  - Tier 1 -> Tier 2 -> Tier 3 DB cache fallback structure added to `_fetch_data_fdr_network()` and `_download_indicator_network()`.
  - In `_download_indicator_network()`, exceptions from Tier 1 (`yf.download`) are caught internally on lines 473-475, bypassing Tenacity's `@retry` decorator on `_download_indicator_network` and jumping straight to Tier 2 (`fdr.DataReader`) on the first iteration.

- **Fundamental Storage & Offline Mode (`trading_system/src/data_layer/earnings_data.py`)**:
  - `save_fundamental_meta()` condition updated to only trigger when `df_fun is not None and not df_fun.empty`.
  - `expiry_days < 0` offline check implemented.

- **Test Suite Execution Results (`trading_system/tests/test_tuning_and_retry.py`)**:
  Execution of `.venv\Scripts\python.exe -m pytest trading_system/tests/test_tuning_and_retry.py` resulted in 3 test failures out of 6 tests:
  - `test_fetch_data_fdr_retry_success`: FAILED (`mock_fdr.call_count` was 0 instead of 3 because unmocked `yf.download` intercepted network calls).
  - `test_fetch_data_fdr_max_retries_fail`: FAILED (`mock_fdr.call_count` was 0 instead of 3).
  - `test_fetch_indicator_history_retry`: FAILED (`mock_yf.call_count` was 1 instead of 2 because Tier 1 exception swallowing short-circuits Tenacity retry).

---

## 2. Logic Chain

1. **Test Failure Mechanism**: Unit tests in `test_tuning_and_retry.py` expect `fetch_data_fdr()` to retry via Tenacity when network calls fail and mock `FinanceDataReader.DataReader`. Introducing `yf.download()` as Tier 1 without updating test mocks causes `yf.download()` to issue unmocked live network requests, returning data and skipping `FinanceDataReader` calls entirely.
2. **Retry Short-circuiting**: In `_download_indicator_network()`, catching `yf.download` errors and executing `fdr.DataReader()` inside the function prevents the function from throwing an exception to Tenacity. Tenacity sees attempt 1 return valid FDR data, so it never attempts retry #2, breaking `test_fetch_indicator_history_retry`.
3. **Requirement Violation**: Milestone 2 scope and verification requirements mandate that all existing unit tests in `test_tuning_and_retry.py` pass cleanly. Therefore, the verdict must be `REQUEST_CHANGES`.

---

## 3. Caveats

- `http_session.py` logic and `earnings_data.py` metadata hygiene logic are verified to be correct and clean.
- Fixing the issue requires adjusting Tier 1/2 exception propagation in `run_pipeline.py` and/or updating mock expectations in `test_tuning_and_retry.py` so that both provider tiers are correctly mocked and retried during tests.

---

## 4. Conclusion

The Milestone 2 code changes require revision (`REQUEST_CHANGES`). Implementation of `http_session.py` and `earnings_data.py` passes review, but `run_pipeline.py` fallback integration breaks 3 unit tests in `test_tuning_and_retry.py`.

---

## 5. Verification Method

To re-verify after Worker remedies the issue:
1. Run `.venv\Scripts\python.exe -m pytest trading_system/tests/test_tuning_and_retry.py -v`
2. Verify all 6 tests in `test_tuning_and_retry.py` pass with 100% success.
3. Inspect `_download_indicator_network` and `_fetch_data_fdr_network` to confirm exception propagation triggers Tenacity retries properly.
