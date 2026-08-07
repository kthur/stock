# Project: Stock Trading System - Price Fetch Hardening

## Architecture
- Target Scope: 3,379 symbols across 6 markets (KOSPI, KOSDAQ, KONEX, SP500, NASDAQ, RUSSELL2000).
- Storage: `StockPriceDB` (SQLite WAL mode with thread-local connection pool and `_write_lock` mutex).
- Data Layer: Multi-tier fallback price fetcher (`yfinance` with Tenacity exponential retries -> `FinanceDataReader` -> Naver Direct / PyKRX / Stooq -> DB cache fallback).
- Data Quality: `DataValidator.validate_price_data` gate applied before SQLite write locks. Forward-fill (`ffill()`) OHLCV date contiguity applied across strategy feature engines.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Network Exception Hardening | Tenacity exponential retries on yfinance timeouts / HTTP 429 rate limits | M1 | Survey |
| 2 | Batch Prefetching Resilience | Exponential backoff on batch rate limits instead of instant binary splits | M1 | Survey |
| 3 | KRX 6-Digit Ticker Normalization | Mandatory `zfill(6)` on numeric KRX symbols across all layers | M2 | Survey |
| 4 | KONEX Suffix & US Dot Class Mapping | Mapping KONEX to `.KS` and US dot share classes (`BRK.B` -> `BRK-B`) | M2 | Survey |
| 5 | Multi-Tier Fallback Retrieval | 5-tier KRX and 4-tier US fallback cascades when primary APIs fail/return 0 rows | M2 | Survey |
| 6 | DataValidator Quality Gate | Validate payload integrity before writing to `StockPriceDB` | M2 | Survey |
| 7 | Contiguous OHLCV & Date Alignment | Forward-fill (`ffill()`) missing trading days across 18 strategy feature engines | M2 | Survey |
| 8 | Strategy Execution Verification | Clean execution & non-zero factor scores across 18 multi-factor strategies | M3 | Survey |
| 9 | 100% Automated Test Suite Pass Rate | Zero test failures across `trading_system/tests/` and `tests/` | M3 | Survey |
| 10 | Forensic Integrity Audit | Systematic audit verifying genuine logic, clean fallback cascades, zero facades | M3 | Survey |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Network Exception Hardening & Retries | Exponential backoff retries, yfinance exception decoupling in `run_pipeline.py` & `market_data_handler.py` | None | DONE |
| M2 | Ticker Normalization, Fallbacks & Data Quality | KRX/US ticker normalization, 5-tier/4-tier fallback cascades, DataValidator DB gate, `ffill()` contiguity | M1 | DONE |
| M3 | Verification, Test Suite & Forensic Audit | 18-strategy execution check, 100% test pass, Final Forensic Auditor CLEAN verdict | M2 | DONE |

## Interface Contracts
### `run_pipeline.py` ↔ `StockPriceDB`
- `_fetch_yf_primary(symbol, start_date)`: Decorated with `@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)`.
- `_fetch_data_fdr_network(symbol, start_date, market)`: Executes 5-tier KRX cascade (yf -> FDR -> Naver -> PyKRX -> DB cache) or 4-tier US cascade (yf -> FDR -> Stooq -> DB cache).
- Ticker normalization: Canonical keys in DB preserve dot format (`'BRK.B'`), while yfinance query translates to dash format (`'BRK-B'`). KRX numeric tickers padded to 6 digits (`'005930'`).
- `DataValidator.validate_price_data(symbol, df)`: Validates Close column presence, NaN ratio, non-positive prices, extreme daily return jumps, and zero volume before calling `price_db.update_prices`.
