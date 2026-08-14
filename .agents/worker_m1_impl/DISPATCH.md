## 2026-08-12T23:42:20Z
Task: Implement Milestone 1 (R1: Data Quality & Corporate Action Sanity Gates + DataFrameCache TTL Auto-Eviction):
Read d:/Finance/code/stock/.agents/explorer_m1/report.md, d:/Finance/code/stock/ORIGINAL_REQUEST.md, and d:/Finance/code/stock/PROJECT.md.

1. Corporate Action Sanity Gates:
   - In trading_system/src/data_layer/data_validator.py:
     - Add single-day price spike filtering to validate_price_data and add a new method sanitize_and_validate_price_data(df: pd.DataFrame) -> Tuple[bool, pd.DataFrame] or filter_price_spikes(df: pd.DataFrame) -> pd.DataFrame.
     - Single-day price spike threshold: detect any single-day return magnitude > 300% (abs(pct_change) > 3.0) or unadjusted splits.
     - Integrate CorporateActionAdjuster (from trading_system/src/data_layer/price_adjuster.py) into the validation pipeline to backward-adjust stock splits before persistence.
   - In trading_system/src/persistence/database.py (StockPriceDB.update_prices):
     - Ensure price data is validated against single-day price spikes before DB insertion.
   - In trading_system/run_pipeline.py:
     - Use DataValidator consistently for price prefetching and single-symbol price caching.

2. DataFrameCache TTL Auto-Eviction & Date Invalidation:
   - In trading_system/src/utils/technical_cache.py (class DataFrameCache):
     - Add active TTL eviction: purge expired keys (now - timestamp >= self._ttl) during get(), set(), get_or_compute(), and expose evict_expired() -> int returning count of evicted items.
     - Add date-change invalidation: track _last_date (e.g. datetime.now().date()). Whenever get(), set(), or get_or_compute() is called, if the current calendar date is greater than _last_date, automatically invalidate/clear all cache entries and update _last_date.
     - Expose invalidate_symbol(symbol: str) and invalidate_all().

3. Unit Tests & Verification:
   - Create new test file trading_system/tests/test_technical_cache.py testing:
     - Basic cache hit / miss / LRU capacity
     - Active TTL auto-eviction (evict_expired)
     - Date-change invalidation (mocking date transition)
     - Thread safety under concurrent gets/sets.
   - Update trading_system/tests/test_data_validator.py testing:
     - Single-day price spike > 300% detection and filtering.
     - Unadjusted split detection and adjustment.
   - Run tests: .venv\Scripts\python.exe -m pytest trading_system/tests/test_technical_cache.py trading_system/tests/test_data_validator.py -v.
   - Run full pytest suite: .venv\Scripts\python.exe -m pytest tests/ and .venv\Scripts\python.exe -m pytest trading_system/tests/.

Document implementation details in handoff.md and send soft handoff via send_message to parent when complete.
