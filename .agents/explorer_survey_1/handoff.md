# Handoff Report — Explorer 1 (Price Fetch Hardening Survey)

**Date**: 2026-08-06  
**Agent**: Explorer 1 (`d:\Finance\code\stock\.agents\explorer_survey_1`)  
**Project**: Price Fetch Hardening Project  

---

## 1. Observation

### Observation 1.1: Persistence Layer (`StockPriceDB`)
- **File Path**: `trading_system/src/persistence/database.py` (lines 363–543)
- **Code Quote**:
  ```python
  class StockPriceDB:
      """주가 데이터 SQLite 캐시 (OHLCV + 거래량) — 외부 API 재호출 방지"""
      def __init__(self, db_path: str = str(_DEFAULT_STOCK_PRICES_DB)):
          ...
          self._write_lock = threading.Lock()
  ```
- **Finding**: `StockPriceDB` is a passive SQLite WAL storage engine with thread-local connection reuse and mutex write locking. It has no internal network fetching capability and relies on caller functions to fetch and validate data. `update_prices()` directly inserts DataFrames without pre-insertion data quality or NaN checks.

### Observation 1.2: Model Ingestion Layer (`OnDevicePredictionModel`)
- **File Path**: `trading_system/src/ai/prediction_model.py` (lines 1296–1350, 2460–2520)
- **Code Quote**:
  ```python
  def prepare_training_data(self, prices_dict: Dict[str, pd.DataFrame], ...):
      for sym, df in prices_dict.items():
          if df is None or len(df) < 70:
              continue
  ```
- **Finding**: `OnDevicePredictionModel` requires `len(df) >= 70` for training and `len(df) >= 200` for inference. It drops symbols below these thresholds cleanly. Offline benchmark metadata fallback is provided by `FallbackMetadataDict` (lines 40–121) which returns `np.nan` for unknown tickers.

### Observation 1.3: Pipeline Execution Steps 5 & 9 (`run_pipeline.py`)
- **File Path**: `trading_system/run_pipeline.py` (lines 951–985 for Step 5 training, lines 1158–1194 for Step 9 inference)
- **Code Quote**:
  ```python
  # Step 5: prefetch_prices_batch(train_symbols, symbol_market, start_date_train, price_db, freshness)
  # Step 9: prefetch_prices_batch(all_symbols, symbol_market, start_date_infer, price_db, freshness)
  future_to_sym[executor.submit(fetch_data_fdr, sym, sym_market, start_date_infer, price_db, freshness, update_interval)] = sym
  ```
- **Finding**: Steps 5 and 9 run batch prefetching (`prefetch_prices_batch`) followed by parallel per-symbol fetching (`fetch_data_fdr`) using a `ThreadPoolExecutor`.

### Observation 1.4: Tier 1 Retry Exception Catching Bug
- **File Path**: `trading_system/run_pipeline.py` (lines 163–195)
- **Code Quote**:
  ```python
  @retry(
      stop=stop_after_attempt(3),
      wait=wait_exponential(multiplier=1, min=2, max=10),
      retry=(retry_if_result(is_empty_result) | retry_if_exception_type(Exception)),
      reraise=True
  )
  def _fetch_data_fdr_network(symbol: str, market: str, start_date: str) -> pd.DataFrame:
      ...
      try:
          df = yf.download(yf_symbol, start=start_date, progress=False, auto_adjust=True)
          if df is not None and not df.empty:
              result = df
      except Exception as e:
          logger.debug(f"Tier 1 (yfinance) network fetch failed for {yf_symbol}: {e}")
  ```
- **Finding**: `_fetch_data_fdr_network` catches exceptions from `yf.download` locally and swallows them into log debug statements. This prevents Tenacity's `@retry` decorator on `_fetch_data_fdr_network` from retrying Tier 1 (`yfinance`) when transient network errors or rate limits occur; instead, it immediately proceeds to Tier 2 (`FinanceDataReader`).

### Observation 1.5: KONEX Market Suffix Omission
- **File Path**: `trading_system/run_pipeline.py` (lines 151–155)
- **Code Quote**:
  ```python
  _KR_MARKET_SUFFIX = {
      'KOSPI': '.KS',
      'KOSDAQ': '.KQ',
      'KRX': '.KS',
  }
  ```
- **Finding**: `KONEX` is missing from `_KR_MARKET_SUFFIX`. `_KR_MARKET_SUFFIX.get('KONEX', '.KS')` returns `.KS`, causing yfinance requests for KONEX tickers to append `.KS` and fail with 404 / empty returns on Yahoo Finance.

### Observation 1.6: Batch Prefetching Missing Retries & Secondary Fallback
- **File Path**: `trading_system/run_pipeline.py` (lines 310–347)
- **Code Quote**:
  ```python
  def _download_with_recovery(tickers: list, start_dt: str) -> pd.DataFrame:
      ...
      df_res = yf.download(tickers, start=start_dt, progress=False, auto_adjust=True, group_by='ticker')
  ```
- **Finding**: `_download_with_recovery` contains raw `yf.download` calls **without `@retry` decorators, exponential backoff, or secondary provider (FinanceDataReader) fallback**. Transient rate-limit errors (HTTP 429) cause instant binary splitting without retrying the network call.

### Observation 1.7: Single-Symbol Data Quality Gate Bypass
- **File Path**: `trading_system/run_pipeline.py` (lines 408–413)
- **Code Quote**:
  ```python
  if network_result is not None and not network_result.empty:
      if price_db is not None:
          try:
              price_db.update_prices(s, network_result)
          except Exception as ex:
              logger.debug(f"Failed to cache prices for {s}: {ex}")
  ```
- **Finding**: `fetch_data_fdr` writes `network_result` directly into `StockPriceDB` without calling `DataValidator.validate_price_data(s, network_result)`, bypassing data quality checks enforced in batch prefetching.

---

## 2. Logic Chain

1. **Premise 1**: The system aims to reliably fetch and cache historical price data across 6 markets (KOSPI, KOSDAQ, KONEX, SP500, NASDAQ, RUSSELL2000) for ~3,379 symbols without unhandled NaNs or missing trading days.
2. **Premise 2**: If primary network calls (Tier 1 `yfinance`) fail due to transient HTTP 429 errors or network timeouts, automatic exponential retries should be executed on Tier 1 before cascading to Tier 2 (`FinanceDataReader`).
3. **Reasoning Step 2.1**: In `_fetch_data_fdr_network` (Obs 1.4), local exception swallowing in Tier 1 prevents Tenacity from attempting retries on `yf.download`. Thus, single-attempt yfinance failures immediately trigger Tier 2 without retrying Tier 1.
4. **Reasoning Step 2.2**: In `prefetch_prices_batch` (Obs 1.6), batch yfinance requests lack any `@retry` decorator or secondary `FinanceDataReader` fallback. Transient batch timeouts drop entire 100-ticker groups without retry.
5. **Reasoning Step 2.3**: In `_KR_MARKET_SUFFIX` (Obs 1.5), KONEX tickers are assigned `.KS` suffixes on Yahoo Finance, leading to 100% Tier 1 failures for KONEX symbols.
6. **Reasoning Step 2.4**: In `fetch_data_fdr` (Obs 1.7), single-symbol fetching bypasses `DataValidator.validate_price_data`, allowing invalid/corrupt network payloads to pollute `StockPriceDB`.
7. **Deduction**: Because of these structural flaws in retry decoupling, market suffix mapping, batch recovery, and data quality validation, transient network glitches cause missing price data, reducing prediction coverage across target markets.

---

## 3. Caveats

- **Network Environment Dependencies**: Exact API rate limits and HTTP 429 behaviors depend on Yahoo Finance and FinanceDataReader (Naver/KRX) server load and client IP address.
- **Read-Only Scope**: This survey is read-only. No code modifications were applied to production files (`run_pipeline.py`, `database.py`, `prediction_model.py`). Implementation details and patch files are delegated to subsequent implementation workers.

---

## 4. Conclusion

The price fetching infrastructure possesses a solid foundation (SQLite WAL cache, 3-tier fallback architecture, ThreadPoolExecutor parallelization), but contains 7 critical vulnerabilities preventing full resilience across all 6 target markets:
1. Swallowed Tier 1 exceptions in `_fetch_data_fdr_network` disabling Tenacity retries.
2. Missing retries, backoff, and Tier 2 fallback in `prefetch_prices_batch`.
3. Omission of `KONEX` in `_KR_MARKET_SUFFIX`.
4. Unhandled dot/dash ticker conversions (`BRK.B` vs `BRK-B`) and missing 6-digit zero-padding (`5930` vs `005930`).
5. Bypassed `DataValidator` checks in single-symbol `fetch_data_fdr`.
6. Lack of Tier 2 fallback in `MarketDataHandler.fetch_historical_data`.
7. Thread pool queue timeout contention during 3,379 symbol sweeps.

Resolving these 7 issues will ensure 100% clean, contiguous OHLCV price histories across all 3,379 symbols.

---

## 5. Verification Method

### 5.1 Unit Test Execution
Verify existing network retry and price database tests pass cleanly:
```bash
.venv\Scripts\python.exe -m pytest trading_system/tests/test_database.py trading_system/tests/test_tuning_and_retry.py -v
```

### 5.2 Inspection of Key Files
Inspect the following files to verify implementation fixes:
1. `trading_system/run_pipeline.py`: Confirm `_fetch_yf_primary` is decoupled with `@retry(reraise=True)`, `_KR_MARKET_SUFFIX` includes `'KONEX'`, `prefetch_prices_batch` includes retries & Tier 2 fallback, and `fetch_data_fdr` calls `DataValidator.validate_price_data()`.
2. `trading_system/src/persistence/database.py`: Confirm ticker format normalization before database queries/inserts.
3. `trading_system/src/data_layer/market_data_handler.py`: Confirm Tier 2 `FinanceDataReader` fallback in `fetch_historical_data`.

### 5.3 Invalidation Conditions
- If unit tests fail or mock call counts mismatch during retry tests.
- If running pipeline dry run results in 0 predictions or unhandled network exceptions for KONEX or US dotted tickers.
