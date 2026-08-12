## 2026-08-12T14:41:18Z
Task: Implement Milestone 1 (Data Quality & Corporate Action Sanity Gates):
1. Corporate Action Sanity Gates:
   - Inspect trading_system/src/data_layer/data_validator.py and trading_system/src/data_layer/price_adjuster.py.
   - Update DataValidator.validate_price_data to detect and handle abnormal corporate action price spikes (e.g. single-day price changes > 300% or unadjusted splits).
   - Add a sanity filter function/method filter_price_spikes(df: pd.DataFrame) -> pd.DataFrame (or incorporate into DataValidator/CorporateActionAdjuster) that cleans/adjusts/filters single-day abnormal spikes (> 300%) or unadjusted splits from price series before DB storage and indicator calculation.
   - Ensure sanity check is applied consistently in trading_system/run_pipeline.py or market_data_handler.py.
2. DataFrameCache TTL Auto-Eviction & Date Invalidation:
   - Inspect trading_system/src/utils/technical_cache.py (class DataFrameCache).
   - Implement active TTL auto-eviction: automatically purge expired entries (age >= ttl) during lookup/eviction and expose an explicit evict_expired() method.
   - Implement calendar date-change invalidation: track current trading/calendar date (datetime.now().date() or date string) alongside timestamps, and automatically invalidate/clear cached entries when the date changes across midnight/trading days.
3. Unit Tests:
   - Create new unit test file trading_system/tests/test_technical_cache.py to test DataFrameCache TTL eviction, LRU capacity, cache hit/miss, thread safety, and date-change invalidation.
   - Update trading_system/tests/test_data_validator.py to test >300% price spike filtering and corporate action sanity checks.
   - Execute tests using .venv\Scripts\python.exe -m pytest trading_system/tests/test_technical_cache.py trading_system/tests/test_data_validator.py -v.
   - Ensure all existing unit tests in trading_system/tests/ continue to pass.
