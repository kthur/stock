# Changes Summary — Milestone 2 (Worker M2)

## Modified Files

1. **`trading_system/src/persistence/database.py`**:
   - Implemented `normalize_symbol(symbol: str) -> str`: Standardizes KRX numeric tickers with 6-digit zero-padding (`zfill(6)` if numeric and len <= 6), while preserving US canonical keys (`BRK.B`, `AAPL`).
   - Integrated `normalize_symbol` across `StockPriceDB` methods (`update_prices`, `get_prices`, `get_latest_date`, `_get_earliest_date`, `needs_update`, `count_rows`), ensuring database queries and storage always use canonical ticker keys.

2. **`trading_system/src/data_layer/indicator_storage.py`**:
   - Updated `_is_krx_symbol` heuristic to handle unpadded numeric symbols (1 to 6 digits) gracefully (`s.isdigit() and 1 <= len(s) <= 6`).
   - Standardized KRX symbol insertions into `stock_universe` table with 6-digit zero-padding.

3. **`trading_system/run_pipeline.py`**:
   - Updated `_KR_MARKET_SUFFIX` dictionary to include `'KONEX': '.KS'`.
   - Implemented multi-tier fallback retrieval functions:
     - `_fetch_naver_direct`: Naver Financial Chart XML API fallback.
     - `_fetch_pykrx`: PyKRX API fallback.
     - `_fetch_stooq_or_yahoo_direct`: Stooq & Yahoo Direct CSV fallback.
   - Refactored `_fetch_data_fdr_network` to execute structured multi-tier fetching:
     - **KRX Order**: yfinance -> FinanceDataReader -> Naver Direct API -> PyKRX -> StockPriceDB cache fallback.
     - **US Order**: yfinance -> FinanceDataReader -> Stooq / Yahoo Direct -> StockPriceDB cache fallback.
   - Standardized US tickers for yfinance by converting dots to hyphens (`BRK.B` -> `BRK-B`), while retaining canonical keys in `StockPriceDB`.
   - Updated `fetch_data_fdr` with `DataValidator.validate_price_data` gate before calling `price_db.update_prices`, ensuring corrupted payloads never enter the SQLite cache.
   - Applied `ffill()` date contiguity to OHLCV DataFrames before returning them to strategy feature engines.

4. **`trading_system/src/data_layer/market_data_handler.py`**:
   - Added multi-tier fallback helpers (`_fetch_naver_direct`, `_fetch_pykrx`, `_fetch_stooq_or_yahoo_direct`).
   - Refactored `_fetch_historical_yf_with_retry` with multi-tier fallback chain and ticker symbol normalization.
   - Updated `_df_to_price_bars` to apply `ffill()` date contiguity on OHLCV columns before converting DataFrame rows into `PriceBar` objects.

5. **`trading_system/src/ai/prediction_model.py`**:
   - Applied `ffill()` on OHLCV columns in `_create_features` before calculating technical indicator features.

6. **`trading_system/tests/test_milestone2_m2.py`**:
   - Created comprehensive unit tests validating ticker symbol normalization, KONEX suffix, multi-tier fallback mechanism, DataValidator gate, and `ffill()` date contiguity.
