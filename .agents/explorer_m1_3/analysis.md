# HTTP Header Configuration & Test Architecture Analysis Report

## Executive Summary
This investigation analyzes the HTTP network layer (`yfinance` and `FinanceDataReader`) and the test suite architecture across the stock trading system (`d:\Finance\code\stock`). 

Key discoveries:
1. **Header Initialization Status**: Neither `yfinance` nor `FinanceDataReader` currently receives customized `User-Agent` headers or shared HTTP sessions. `yfinance` defaults to its generic internal headers or standard Python requests strings, and `FinanceDataReader` uses default `requests`/`urllib` parameters.
2. **Global Custom Header Strategy**: A global session initialization utility (`src/utils/http_session.py`) paired with global patching of `requests.Session` headers at application startup ensures that browser-like `User-Agent` headers are transmitted for all outgoing requests across both `yfinance` and `FinanceDataReader`.
3. **Test Architecture Review**: Existing pytest files (`test_tuning_and_retry.py`, `test_system.py`, `test_e2e_consolidated.py`) patch `FinanceDataReader.DataReader` and `yfinance.download` individually. However, complete fallback chain behavior (`yfinance` -> `FinanceDataReader` -> `StockPriceDB` cache -> graceful degrade) and global header injection are not currently asserted in the test suite.

---

## 1. Current Network Initialization Analysis

### yfinance Initialization
- **Code Locations**:
  - `trading_system/run_pipeline.py` (lines 167, 301, 475)
  - `trading_system/src/data_layer/earnings_data.py` (line 48)
  - `trading_system/src/data_layer/indicator_storage.py` (line 205)
  - `trading_system/src/data_layer/market_data_handler.py` (line 160)
  - `trading_system/src/data_layer/global_market.py` (line 64)
  - `trading_system/src/data_layer/alt_data.py` (line 22)
  - `trading_system/src/analysis/macro_analyzer.py` (line 175)
  - `trading_system/src/analysis/market_scanner.py` (line 66)
- **Mechanism**:
  - Calls `yf.download(tickers, ...)` and `yf.Ticker(symbol)` without supplying an explicit `session` parameter.
  - Defaults to uncustomized Python HTTP requests headers (`python-requests/...` or `Python-urllib`), increasing rate-limiting and HTTP 429/403 blocking risks in CI/CD environments.

### FinanceDataReader Initialization
- **Code Locations**:
  - `trading_system/run_pipeline.py` (lines 158, 179, 626, 636)
  - `trading_system/scripts/post_market_scoring.py` (line 74)
  - `trading_system/scripts/postmarket_rankings.py` (line 162)
  - `trading_system/scripts/predict_best_stock.py` (lines 38, 58)
  - `trading_system/src/utils/stock_list.py` (line 25)
- **Mechanism**:
  - Functions `fdr.DataReader(...)` and `fdr.StockListing(...)` internally construct HTTP requests using `requests` and `urllib` without accepting a `session` argument.
  - Requests inherit standard global `requests` headers unless `requests.Session` default headers are configured system-wide.

---

## 2. Recommended Global User-Agent & Session Configuration

To configure browser-like `User-Agent` headers and connection pooling globally without modifying standard library internals:

### Strategy 1: Centralized Session Utility (`src/utils/http_session.py`)
Create a central utility that defines a standard browser User-Agent and connection session manager:

```python
"""Centralized HTTP session and User-Agent configuration helper."""

import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

_GLOBAL_SESSION = None

def get_configured_session() -> requests.Session:
    global _GLOBAL_SESSION
    if _GLOBAL_SESSION is None:
        session = requests.Session()
        session.headers.update({
            "User-Agent": DEFAULT_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,ko;q=0.8",
            "Connection": "keep-alive"
        })
        adapter = HTTPAdapter(
            pool_connections=20,
            pool_maxsize=20,
            max_retries=Retry(
                total=3,
                backoff_factor=1.0,
                status_forcelist=[429, 500, 502, 503, 504]
            )
        )
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        _GLOBAL_SESSION = session
    return _GLOBAL_SESSION

def setup_global_http_headers():
    """Inject browser User-Agent default headers into all requests.Session instances globally."""
    session = get_configured_session()
    # Patch requests.Session default headers so FDR and un-sessioned yfinance calls transmit browser headers
    original_init = requests.Session.__init__
    def new_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        self.headers.update({
            "User-Agent": DEFAULT_USER_AGENT,
            "Accept-Language": "en-US,en;q=0.9,ko;q=0.8",
        })
    requests.Session.__init__ = new_init
```

### Strategy 2: Integration Points
1. **Pipeline & Application Entrypoints**:
   Call `setup_global_http_headers()` at startup in `trading_system/run_pipeline.py` and `scripts/post_market_scoring.py`.
2. **yfinance Parameter Passing**:
   Update `_fetch_data_fdr_network`, `prefetch_prices_batch`, and `fetch_fundamentals` to supply `session=get_configured_session()` to `yf.download` and `yf.Ticker`.
3. **Async Network Calls (`aiohttp`)**:
   Reference `DEFAULT_USER_AGENT` in `src/data_layer/earnings_data.py` (`async_fetch_fundamentals`) to ensure header consistency.

---

## 3. Test Suite Architecture Review

### Review of `trading_system/tests/test_tuning_and_retry.py`
- **Current Behavior**:
  - Line 64: Mocks `FinanceDataReader.DataReader` to verify retry mechanism on transient errors (`side_effect = [Exception, Exception, mock_df]`).
  - Line 92: Mocks `yfinance.download` to verify retry on rate limit errors.
  - Line 104: Mocks `yfinance.Ticker` to verify retry on empty financials.
  - Line 118: Tests global rate limiter thread coordination.
- **Coverage Deficits**:
  - Lacks test coverage verifying fallback execution from `yfinance` to `FinanceDataReader` when `yfinance` fails.
  - Lacks test coverage verifying fallback to `StockPriceDB` cache when both network callers fail.
  - Lacks test coverage asserting that outgoing requests transmit custom `User-Agent` headers.

### Review of `trading_system/tests/test_system.py`
- Tests components like `MarketDataHandler`, `PortfolioManager`, `NLPEngine`, and `OrderManagementSystem`.
- `MarketDataHandler` tests use internal simulation methods (`simulate_api_call`) rather than testing live network wrapper layers.

---

## 4. Test Suite Enhancements & Mock Strategy

To verify offline and online fallback behavior without breaking test speed or relying on live external networks:

### Proposed Tests to Add in `test_tuning_and_retry.py`
1. **`test_global_user_agent_configuration()`**:
   Asserts that `requests.Session()` instantiates with `DEFAULT_USER_AGENT` and custom headers after `setup_global_http_headers()` is invoked.
2. **`test_fallback_chain_yf_to_fdr()`**:
   Mock `yf.download` to raise `Exception("HTTP 429 Too Many Requests")`, mock `fdr.DataReader` to return valid DataFrame. Assert that `fetch_data_fdr` succeeds via `fdr.DataReader` and logs warning.
3. **`test_fallback_chain_network_to_db_cache()`**:
   Mock both `yf.download` and `fdr.DataReader` to raise exceptions. Provide pre-existing data in `StockPriceDB`. Assert that `fetch_data_fdr` returns stored data from `StockPriceDB`.
4. **`test_fallback_chain_offline_empty_degrade()`**:
   Mock all network calls to raise exceptions and supply an empty `StockPriceDB`. Assert that `fetch_data_fdr` returns `None` or an empty DataFrame cleanly without crashing.

---

## Conclusion & Actionable Steps for Implementation Phase
- **M2 Task**: Create `src/utils/http_session.py` with session pool and header patcher. Wire `setup_global_http_headers()` into `run_pipeline.py`.
- **M3 Task**: Update `test_tuning_and_retry.py` with the 4 target fallback and header assertion tests. Ensure 100% test execution offline without network calls.
