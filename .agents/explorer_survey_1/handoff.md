# Soft Handoff Report — Explorer 1

**Agent Directory**: `d:/Finance/code/stock/.agents/explorer_survey_1`  
**Milestone**: Stock Trading System Survey Phase 1 (R1 & R4 API)  
**Date**: 2026-08-12  

---

## 1. Observation

1. **Price Data Cleaning & Ingestion**:
   - `trading_system/run_pipeline.py` (lines 259–353, 565–646): Price data is fetched in `_fetch_data_fdr_network` across 4 network tiers and cached in SQLite via `fetch_data_fdr`.
   - `trading_system/src/data_layer/data_validator.py` (lines 144–153):
     ```python
     daily_ret = valid_close.pct_change().abs().dropna()
     if len(daily_ret) > 0:
         extreme_ratio = (daily_ret > 1.0).sum() / len(daily_ret)
         if extreme_ratio > 0.05:
             return False
     ```
     Observed that single-day abnormal price spikes (>300% single-day change or unadjusted stock splits) pass `DataValidator` when `extreme_ratio <= 0.05` (e.g., 1 spike out of 500 rows = 0.2%).
   - `trading_system/src/data_layer/price_adjuster.py` (lines 17–61): `CorporateActionAdjuster.adjust_ohlcv` detects stock split gaps (`ratios < 0.60` or `ratios > 1.60`). However, in `run_pipeline.py` (line 347), it is ONLY called when `tier_source == 'raw'`, skipping `yfinance` fetches and `StockPriceDB` cached reads.

2. **DataFrameCache Lifecycle**:
   - `trading_system/src/utils/technical_cache.py` (lines 191–231): `DataFrameCache` stores DataFrames in `self._cache` keyed on `(symbol, start_date)`.
   - Observed that TTL check (`now - self._timestamps.get(key, 0) < self._ttl`) occurs lazily on `get_or_compute` lookup. Stale keys (`age >= _ttl`) remain stored in `self._cache` indefinitely unless re-queried or evicted via max item capacity (`_max_items`).
   - Observed no trading date / calendar date-change invalidation (e.g., crossing midnight or new trading day).

3. **External API Calls & Retry Backoffs**:
   - Tenacity decorators in `trading_system/src/data_layer/earnings_data.py` (line 38), `trading_system/src/data_layer/market_data_handler.py` (lines 231, 364), and `trading_system/run_pipeline.py` (lines 243, 694, 710):
     ```python
     @retry(
         stop=stop_after_attempt(3),
         wait=wait_exponential(multiplier=1, min=2, max=10),
         ...
     )
     ```
     Observed that `wait_exponential` lacks a `jitter` parameter, calculating deterministic power-of-two delays (1s, 2s, 4s, 8s).
   - Async retry loops in `trading_system/src/data_layer/earnings_data.py` (lines 163, 233): `await asyncio.sleep(2 ** attempt)` is purely deterministic without random jitter.
   - Sync backoff loops in `trading_system/src/data_layer/fred_client.py` (lines 103, 135) and `trading_system/src/utils/error_handler.py` (lines 52, 67): use deterministic `2 ** attempt` multipliers without random jitter.

4. **Unit Test Coverage**:
   - Relevant existing tests: `trading_system/tests/test_data_validator.py`, `tests/test_ecos_and_price_adjuster.py`, `trading_system/tests/test_network_hardening.py`, `trading_system/tests/test_tuning_and_retry.py`.
   - Test gap observed: zero unit tests exist for `DataFrameCache` in `tests/` or `trading_system/tests/`.

---

## 2. Logic Chain

1. In `run_pipeline.py`, price data fetched from network or loaded from SQLite is validated via `DataValidator.validate_price_data`.
2. Because `DataValidator.validate_price_data` only flags DataFrames where `extreme_ratio > 0.05` (>5% of rows having >100% daily returns), single-day price spikes (>300%) or unadjusted splits that affect 1-2 bars pass validation.
3. Because `CorporateActionAdjuster` is only invoked when `tier_source == 'raw'`, unadjusted splits or single-day price spikes from yfinance or stored in `StockPriceDB` pass uncorrected into `StockPriceDB` and downstream feature engineering, corrupting EMA, ATR, RSI, and strategy calculations.
4. In `DataFrameCache`, stale items are not actively purged upon expiration or date change, allowing stale data to persist across trading day boundaries unless cache capacity overflows or manual invalidation is called.
5. In external API fetching (`earnings_data.py`, `market_data_handler.py`, `run_pipeline.py`, `fred_client.py`), deterministic `wait_exponential` and `2 ** attempt` sleep durations cause all parallel batch tasks hitting rate limits (HTTP 429) to retry at exact identical millisecond timestamps, creating thundering herd retry storms.

---

## 3. Caveats

- Investigation was strictly read-only; no code files outside `.agents/explorer_survey_1/` were modified.
- Live external API endpoint behavior (e.g. rate limit response times from Yahoo Finance or FRED) was analyzed via codebase inspection and test mocks, not by making un-throttled live API requests.

---

## 4. Conclusion

1. **R1 (Data Sanity & DataFrameCache)**: Data quality gates must be upgraded to detect single-day price spikes (>300%) and enforce `CorporateActionAdjuster` across all ingestion paths before storing into `StockPriceDB`. `DataFrameCache` requires active TTL auto-eviction and calendar date-change invalidation.
2. **R4 (API Retry Jitter)**: Retry loops across `earnings_data.py`, `market_data_handler.py`, `fred_client.py`, `error_handler.py`, and `run_pipeline.py` must be upgraded with randomized exponential backoff jitter (`wait_random_exponential` or `random.uniform`) to eliminate thundering herd rate limit collisions.
3. Comprehensive investigation details, line numbers, and architectural proposals are recorded in `d:/Finance/code/stock/.agents/explorer_survey_1/report.md`.

---

## 5. Verification Method

- Run pytest command:
  ```bash
  .venv/bin/pytest tests/test_ecos_and_price_adjuster.py trading_system/tests/test_data_validator.py trading_system/tests/test_network_hardening.py trading_system/tests/test_tuning_and_retry.py -v
  ```
- Inspect findings in `d:/Finance/code/stock/.agents/explorer_survey_1/report.md`.
- Invalidation condition: If `DataValidator` or `DataFrameCache` behaves differently than documented in `report.md`, re-verify line references in `trading_system/src/data_layer/data_validator.py` and `trading_system/src/utils/technical_cache.py`.

---

## Remaining Work (Soft Handoff Next Steps)

1. Implement R1 Data Quality Sanity Gates & Corporate Action Split Adjuster integration across all ingestion paths in `src/data_layer/data_validator.py` and `run_pipeline.py`.
2. Implement TTL auto-eviction and date-change invalidation in `DataFrameCache` (`src/utils/technical_cache.py`).
3. Add randomized jitter to tenacity decorators and manual sleep backoffs in `src/data_layer/earnings_data.py`, `src/data_layer/market_data_handler.py`, `src/data_layer/fred_client.py`, `src/utils/error_handler.py`, and `run_pipeline.py`.
4. Create dedicated unit tests for `DataFrameCache` in `tests/test_technical_cache.py`.
