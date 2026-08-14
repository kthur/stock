## 2026-08-12T14:40:20Z
<USER_REQUEST>
You are Explorer for Milestone 1 (Data Quality & Corporate Action Sanity Gates).
Your working directory is d:/Finance/code/stock/.agents/explorer_m1.

Task:
Read d:/Finance/code/stock/ORIGINAL_REQUEST.md and d:/Finance/code/stock/PROJECT.md.
Investigate the codebase to design the implementation for Milestone 1:
1. Corporate Action Sanity Gates:
   - Locate where price data validation and ingestion occur (e.g. `trading_system/src/data_layer/data_validator.py`, `trading_system/src/data_layer/market_data_handler.py`, `trading_system/src/persistence/database.py`, `trading_system/run_pipeline.py`).
   - Specify exact logic to filter out abnormal corporate action price spikes (e.g. single-day price changes > 300% or unadjusted stock split price jumps/drops).
   - Specify where and how this sanity check should be hooked into price loading and DB insertion/caching.
2. Technical Indicator Cache TTL Auto-Eviction:
   - Locate `DataFrameCache` implementation (e.g. in `trading_system/src/data_layer/feature_engineering.py`, `trading_system/src/data_layer/indicator_storage.py`, or wherever `DataFrameCache` lives).
   - Inspect its current caching mechanism, TTL settings, and date-change handling.
   - Design TTL auto-eviction (e.g., configurable `ttl_seconds`, auto-eviction on access if expired) and automatic cache invalidation when trading date changes.
3. Unit Tests:
   - Check existing tests in `trading_system/tests/` (e.g. `test_database.py`, `test_feature_engineering.py`, `test_data_validator.py`).
   - Specify new unit tests to be added for price spike filtering and `DataFrameCache` TTL eviction.

Do NOT write or edit production code. Document your findings, exact line numbers, function signatures, and step-by-step implementation guide in d:/Finance/code/stock/.agents/explorer_m1/report.md and send a soft handoff via send_message to parent when complete.
</USER_REQUEST>
