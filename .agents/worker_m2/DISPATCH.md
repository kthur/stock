## 2026-08-06T12:55:00Z

OBJECTIVE:
Implement ticker symbol normalization, multi-tier fallback data fetching, DataValidator caching gate, and contiguous OHLCV date alignment.

TASKS:
1. **Ticker Symbol Normalization**:
   - In `trading_system/run_pipeline.py`, `trading_system/src/persistence/database.py`, and `trading_system/src/data_layer/indicator_storage.py`:
     - Standardize KRX numeric tickers with 6-digit zero-padding (`str(code).zfill(6)` if numeric and len <= 6). Ensure `_is_krx_symbol` handles unpadded strings gracefully.
     - Update `_KR_MARKET_SUFFIX` in `run_pipeline.py` to include `'KONEX': '.KS'` (or appropriate fallback suffix).
     - Standardize US tickers by converting dots to hyphens (`BRK.B` -> `BRK-B`, `BF.B` -> `BF-B`) when querying yfinance while retaining clean canonical keys in `StockPriceDB`.
2. **Multi-Tier Fallback Data Fetching**:
   - Implement multi-tier historical price retrieval for KRX (yfinance -> FinanceDataReader -> Naver Direct API -> PyKRX -> StockPriceDB cache fallback) and US (yfinance -> FinanceDataReader -> Stooq/Yahoo Direct -> StockPriceDB cache fallback) in `run_pipeline.py` and `market_data_handler.py`.
   - Ensure that if primary network APIs return 0 rows or fail, the fallback providers are invoked seamlessly.
3. **DataValidator Gate in `fetch_data_fdr`**:
   - In single-symbol `fetch_data_fdr` (`run_pipeline.py`), pass network payloads to `DataValidator.validate_price_data` before calling `price_db.update_prices`, ensuring corrupted payloads never enter `StockPriceDB`.
4. **Contiguous OHLCV & Date Contiguity (`ffill`)**:
   - Apply `ffill()` date contiguity to OHLCV DataFrames before passing them to strategy feature engines, eliminating intermediate NaNs.
5. **Verification**:
   - Run tests: `.venv\Scripts\python.exe -m pytest trading_system/tests/ -v` and `.venv\Scripts\python.exe -m pytest tests/ -v`.
   - Ensure 100% pass rate.
