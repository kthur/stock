# Execution Plan: Price Data Fetching & Network Exception Hardening

## Overview
Hardening and verifying stock price data fetching across 3,379 symbols (KOSPI, KOSDAQ, KONEX, SP500, NASDAQ, RUSSELL2000) for all 18 multi-factor trading strategies.

## Milestones

### Milestone 0: Architectural Survey & Codebase Investigation
- Dispatch Explorers to inspect `trading_system/run_pipeline.py`, `src/persistence/database.py` (StockPriceDB), `src/ai/prediction_model.py`, `src/data_layer/`, FinanceDataReader usage, yfinance usage, Naver/KRX price fetchers, ticker symbol mappings, retry mechanisms, rate limit backoff, and existing tests in `trading_system/tests/` and `tests/`.

### Milestone 1: Network Retries & Rate-Limit Backoff (R1)
- Implement robust exponential backoff, retry decorator/logic, timeout handling for both KRX (FinanceDataReader/Naver) and US (yfinance) markets.
- Handle rate-limit responses (HTTP 429, timeouts, connection resets) gracefully.

### Milestone 2: Ticker Normalization & Fallback Data Handling (R1 & R2)
- Ensure active universe symbols in all 6 markets resolve correctly (e.g. KRX ticker 6-digit zero-padding, US ticker suffix handling, Yahoo vs FinanceDataReader ticker formats).
- Provide fallback data sources (e.g., Naver direct scraping / PyKRX / Yahoo fallback) if primary API returns empty or fails.
- Guarantee clean OHLCV histories without unhandled NaNs or missing trading days for active symbols.

### Milestone 3: End-to-End Pipeline & Strategy Verification (R2)
- Verify all 18 multi-factor strategies produce non-zero predictions across target markets.
- Ensure 100% pass on automated pytest suite (`pytest trading_system/tests/ -v` and `pytest tests/ -v`).
- Execute Forensic Audit for code integrity & clean verification.
