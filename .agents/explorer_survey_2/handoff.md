# Handoff Report: Price Data Fetching, Ticker Normalization & Fallback Hardening Survey

**Agent**: Explorer 2  
**Working Directory**: `d:\Finance\code\stock\.agents\explorer_survey_2`  
**Date**: 2026-08-06  
**Status**: Hard Handoff (Investigation Complete)

---

## 1. Observation

Direct code observations from `d:\Finance\code\stock`:

1. **Ticker Normalization Deficits**:
   - `src/data_layer/indicator_storage.py:28`: `_is_krx_symbol` tests `len(s) == 6 and s.isdigit()`. If a KRX code loses leading zeros (e.g. `'5930'`), it fails the length check and is misclassified as a US ticker.
   - `run_pipeline.py:151-155`: `_KR_MARKET_SUFFIX` maps `KOSPI` -> `.KS`, `KOSDAQ` -> `.KQ`, `KRX` -> `.KS`. Market `KONEX` is missing, defaulting to `.KS` which fails on Yahoo.
   - `run_pipeline.py:171`: `yf_symbol = symbol` passes US tickers directly to `yf.download`. S&P 500 tickers with dots (e.g. `BRK.B`, `BF.B`) are not converted to hyphens (`BRK-B`), causing Yahoo Finance to return empty data or HTTP 404.

2. **Network Resilience & Rate Limit Vulnerabilities**:
   - `run_pipeline.py:332-346`: `_download_with_recovery` performs binary splitting on batch download failure. When Yahoo Finance returns HTTP 429 (Rate Limit), binary splitting splits the batch into halves and retries immediately, doubling HTTP request volume and accelerating rate-limit IP bans.
   - `run_pipeline.py:164-196`: `_fetch_data_fdr_network` uses `@retry` with 3 attempts, but Tier 2 FDR calls lack explicit HTTP timeout controls.

3. **Fallback Data Source Strategy Gaps**:
   - Current fallback flow: Tier 1 (`yfinance`) -> Tier 2 (`FinanceDataReader`) -> Tier 3 (`StockPriceDB` local cache).
   - If local cache is empty or stale, fetching returns 0 rows and the symbol is dropped.
   - Public APIs available for fallback (Naver Finance Direct API, PyKRX, Stooq CSV API, Yahoo Direct Web API) are not currently wired into the pipeline.

4. **Contiguous OHLCV & Strategy Execution**:
   - `run_pipeline.py:1197`: Pipeline hard-drops symbols with `< 200` price rows.
   - `src/ai/ensemble_scorer.py:1086-1102`: Strategy scorer handles missing strategy scores via dynamic weight renormalization and coverage penalties, but zero-row symbol drops prevent strategy execution entirely.

---

## 2. Logic Chain

1. **Premise 1**: 3,379 symbols span 6 distinct markets (KOSPI, KOSDAQ, KONEX, S&P 500, NASDAQ, RUSSELL 2000), each with specific ticker formatting requirements across different data providers (Yahoo, FDR, Naver, PyKRX, Stooq).
2. **Premise 2**: Inconsistent symbol formatting (e.g. unpadded KRX codes `'5930'`, missing KONEX suffix, dot-vs-hyphen `'BRK.B'`) causes primary API calls to fail silently or return 0 rows.
3. **Premise 3**: When batch downloads fail due to rate limits (HTTP 429), binary splitting retries increase request pressure, worsening API bans.
4. **Premise 4**: Relying solely on local SQLite cache when network providers fail means new or uncached symbols cannot be fetched when primary APIs fail.
5. **Conclusion**: Introducing a centralized `TickerNormalizer` module, a exponential backoff retry mechanism (replacing rate-limit binary splits), and a 5-tier multi-source fallback retriever (integrating Naver API, PyKRX, Stooq CSV, Yahoo Direct API) will guarantee contiguous OHLCV price histories and 100% strategy execution across all 3,379 symbols.

---

## 3. Caveats

- **Network Environment**: Investigation was performed in read-only code audit mode. Live network rate limits against Yahoo Finance, Naver, Stooq, and PyKRX may vary based on deployment IP and execution frequency.
- **Scope Boundary**: No production code was modified during this survey. Proposals and architectural recommendations are provided in `analysis.md` for implementation by the implementer agent.

---

## 4. Conclusion

To achieve price fetch hardening and guarantee non-zero price histories for all 3,379 symbols across all 18 multi-factor strategies:

1. **Implement `TickerNormalizer`**:
   - Standardize KRX codes with 6-digit zero-padding (`str(code).zfill(6)`).
   - Add explicit market suffix mapping (`KOSPI` -> `.KS`, `KOSDAQ` -> `.KQ`, `KONEX` -> `.KX`).
   - Automatically convert US class share dots to hyphens for `yfinance` (`BRK.B` -> `BRK-B`).
   - Maintain clean canonical keys (`005930`, `BRK-B`) in `StockPriceDB`.

2. **Implement 5-Tier Fallback Retriever (`MultiSourcePriceFetcher`)**:
   - **KRX**: Tier 1 (`yfinance`) -> Tier 2 (`FinanceDataReader`) -> Tier 3 (`Naver Finance Direct Chart API`) -> Tier 4 (`PyKRX`) -> Tier 5 (`StockPriceDB` Cache).
   - **US**: Tier 1 (`yfinance`) -> Tier 2 (`FinanceDataReader`) -> Tier 3 (`Stooq Direct CSV API`) -> Tier 4 (`Yahoo Direct Chart JSON API`) -> Tier 5 (`StockPriceDB` Cache).

3. **Harden Rate Limiting & Retry Strategy**:
   - Replace binary splitting on HTTP 429 with token-bucket rate-limiting and exponential backoff (`wait_exponential(min=2, max=30)`).
   - Set explicit per-request timeout (e.g. 10s) on all HTTP requests to prevent process hangs.

4. **Contiguous OHLCV Date Alignment**:
   - Perform forward-fill (`ffill()`) on price DataFrames to eliminate intermediate missing trading date NaNs before feature engineering and strategy scoring.

---

## 5. Verification Method

To verify the proposed implementation once created:

1. **Automated Test Suite Execution**:
   ```bash
   .venv\Scripts\python.exe -m pytest tests/ -v
   ```
2. **Ticker Normalization Unit Test Verification**:
   Verify conversion of edge-case symbols (`'5930'` -> `'005930'`, `'BRK.B'` -> `'BRK-B'`, `'KONEX'` symbols).
3. **Pipeline Data Completeness Verification**:
   Run `run_pipeline.py` or inspect DB count across all 6 markets to ensure zero missing symbols:
   ```bash
   .venv\Scripts\python.exe -c "from src.data_layer.indicator_storage import MarketIndicatorStorage; s = MarketIndicatorStorage(); print(len(s.get_universe()))"
   ```
