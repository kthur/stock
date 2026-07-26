# Handoff Report — Explorer 1 (Milestone 1)

## 1. Observation
- **Network Call Locations**:
  - `_fetch_data_fdr_network` (`trading_system/run_pipeline.py:151-189`): US stocks use `fdr.DataReader` directly without yfinance attempt/fallback. KRX stocks use `yf.download` with fallback to `fdr.DataReader`.
  - `prefetch_prices_batch` (`trading_system/run_pipeline.py:192-350`): Uses `yf.download` with binary split `_download_with_recovery`. Failed single-ticker downloads log warning and return empty DataFrame without attempting `fdr.DataReader` or fallback cache retrieval.
  - `fetch_data_fdr` / `_fetch_fallback` (`trading_system/run_pipeline.py:352-440`): Queries `StockPriceDB` (`price_db`). If data is stale and incremental/full network fetches raise exceptions (e.g. rate-limit/offline), `result` becomes `None` (line 424), **discarding** existing cached data in `price_db`.
  - `_download_indicator_network` & `fetch_indicator_history` (`trading_system/run_pipeline.py:465-563`): Network calls to `yf.download` for 16 macro indicator tickers. On network exception, `_fetch_one` returns an empty `pd.Series` instead of falling back to stale DB cache.
  - `_get_excluded_krx_symbols` (`trading_system/run_pipeline.py:614-645`): Network calls to `fdr.StockListing('KRX')` and `fdr.StockListing('KRX-ADMINISTRATIVE')`.
  - `GlobalMarketClient.get_summary` (`src/data_layer/global_market.py:56-143`, called at `run_pipeline.py:666`): Network calls to `yf.Ticker(symbol).history(period=period)`.
  - `MarketIndicatorStorage.update_stock_universe` (`src/data_layer/indicator_storage.py:202-239`, called at `run_pipeline.py:679`): Network calls to `fdr.StockListing`.
  - `fetch_and_store_fundamentals_batch` (`src/data_layer/earnings_data.py:45-100`, called at `run_pipeline.py:689, 969`): Network calls to `yf.Ticker(yf_sym).financials` and `.info`.

## 2. Logic Chain
1. Observations at `run_pipeline.py:376-424` show that `_fetch_fallback()` queries `price_db` for cached OHLCV data. However, if data is flagged as `stale` (e.g. older than `freshness_days`), a network request via `_fetch_data_fdr_network()` is triggered.
2. If the network call throws an exception (HTTP 429 rate limit, 500 server error, socket timeout, offline environment), line 424 catches the exception and sets `result = None`.
3. The function returns `None` to callers in the training loop (`line 827`) and inference loop (`line 995`), dropping the symbol from `train_data_dict` and `infer_data_dict`.
4. Therefore, even when valid historical price data exists in `stock_prices.db`, network failure causes the pipeline to drop the symbol rather than utilizing the offline DB cache.
5. Furthermore, observations at lines 156–160 show US stock price fetching directly invokes `fdr.DataReader` without attempting `yfinance` primary fetch or Tier 2 recovery, producing an inconsistent download architecture across market segments.

## 3. Caveats
- **Offline Data Freshness**: If network downloading fails, fallback to `stock_prices.db` returns existing cached rows up to the latest available cached date. In long-running offline environments, model predictions will reflect the cached timestamp.
- **Scope Restriction**: Investigation was strictly read-only per constraints; code refactoring proposals are fully documented in `analysis.md` for Implementation in Milestone 2.

## 4. Conclusion
The current data fetching implementation in `run_pipeline.py` lacks a unified 3-tier fallback architecture (yfinance -> FinanceDataReader -> `stock_prices.db` cache). On rate-limiting or network failure, stale cached DB data is discarded instead of served, and US stocks bypass yfinance entirely. Cleanly implementing the 3-tier cascade described in `analysis.md` will resolve pipeline fragility and guarantee graceful degradation under offline or rate-limited conditions.

## 5. Verification Method
1. **Source Inspection**: Inspect `analysis.md` in `d:\Finance\code\stock\.agents\explorer_m1_1\analysis.md` to review line numbers, failure mode matrix, and code structures.
2. **Offline Fallback Simulation**: Mock network functions (`yf.download` and `fdr.DataReader`) to raise `requests.exceptions.HTTPError` or `socket.timeout`.
3. **Execution Verification**: Run `.venv/bin/pytest tests/ -v` or run `.venv/bin/python trading_system/run_pipeline.py --debug --skip-training` while offline to verify warnings are logged and cached data from `stock_prices.db` is returned cleanly without pipeline failure.
