# Comprehensive Analysis: Price Data Fetching, Ticker Normalization, Network Resilience & Strategy Data Integrity

**Author**: Explorer 2 (Price Fetch Hardening Specialist)  
**Date**: 2026-08-06  
**Target Universe**: All 3,379 symbols across 6 markets (KOSPI, KOSDAQ, KONEX, S&P 500, NASDAQ, RUSSELL 2000)  
**Working Directory**: `d:\Finance\code\stock\.agents\explorer_survey_2`

---

## Executive Summary

This investigation audits the price data fetching pipeline across all 3,379 universe symbols and 18 multi-factor trading strategies. The audit evaluates network resilience, ticker symbol normalization, multi-tier fallback data sources (Naver Finance, PyKRX, Stooq, Yahoo Web Direct), and contiguous OHLCV price history construction.

Key findings include:
1. **Ticker Symbol Normalization Gaps**: KRX 6-digit codes lose leading zeros when parsed as integers, causing `_is_krx_symbol()` to misclassify 4/5-digit codes (e.g. `'5930'`) as US symbols. S&P 500 tickers with dots (e.g. `'BRK.B'`, `'CWEN.A'`) fail in `yfinance` because Yahoo requires hyphens (`'BRK-B'`). Market suffix mappings lack explicit support for KONEX (`.KX`).
2. **Network Resilience & Rate Limit Vulnerabilities**: `prefetch_prices_batch()` in `run_pipeline.py` uses binary splitting recovery when `yfinance` fails. Under rate limiting (HTTP 429), binary splitting doubles requests, accelerating rate-limit bans. FDR calls lack explicit HTTP timeouts.
3. **Fallback Strategy Deficits**: When primary providers (yfinance, FDR) fail, the pipeline falls back only to local SQLite cache (`StockPriceDB`). If local cache is empty or stale, 0 rows are returned and the symbol is dropped. Direct Naver APIs, PyKRX, Stooq CSV APIs, and Yahoo Chart JSON APIs are not currently integrated as active fallbacks.
4. **Contiguous OHLCV & Strategy NaN Handling**: Pipeline currently drops symbols with `< 200` price rows. Short-history stocks and transient network failures cause missing strategy scores. While `ensemble_scorer.py` handles missing scores via coverage penalties, missing price rows cause zero-coverage drops for active universe symbols.

---

## 1. Ticker Symbol Normalization Audit

### 1.1 Current Implementation & Code References

Universe symbols are loaded from `market_indicators.db` (`stock_universe` table) populated in `src/data_layer/indicator_storage.py`. Price data fetching is coordinated in `run_pipeline.py` and `src/data_layer/market_data_handler.py`.

#### Key References:
- `run_pipeline.py`: Lines 150–175 (`_KR_MARKET_SUFFIX` and `_fetch_data_fdr_network`)
- `src/data_layer/indicator_storage.py`: Lines 18–30 (`_is_krx_symbol`)
- `src/ai/prediction_model.py`: Lines 650–653 (`is_krx_symbol`)
- `src/utils/stock_list.py`: Lines 28–37 (KRX stock list mapping)

### 1.2 Identified Inconsistencies & Failure Modes

#### Issue A: Zero-Padding Truncation (KRX)
- **Mechanism**: KRX stock codes are 6-digit numeric strings (e.g. `'005930'`). If converted to `int` during data processing, leading zeros are lost (e.g. `5930`).
- **Code Impact**: In `_is_krx_symbol(symbol)` (`indicator_storage.py:28`):
  ```python
  if len(s) == 6 and s.isdigit():
      return True
  ```
  A 4-digit or 5-digit code string like `'5930'` fails `len(s) == 6`. The symbol is misclassified as a US market symbol, resulting in invalid provider calls.
- **Fix Required**: Enforce `symbol.zfill(6)` for all numeric KRX symbols before checking length or querying APIs.

#### Issue B: US Share Class Symbol Format Discrepancies (`.` vs `-`)
- **Mechanism**: S&P 500 listing sources (e.g. iShares CSV or FDR `StockListing('S&P500')`) represent class A/B shares with dots (e.g. `BRK.B`, `BF.B`, `CWEN.A`).
- **Code Impact**: `yfinance` requires hyphens for US tickers (`BRK-B`, `BF-B`). In `_fetch_data_fdr_network()` (`run_pipeline.py:171`):
  `yf_symbol = symbol` passes `BRK.B` directly to `yf.download('BRK.B')`, causing Yahoo Finance to return empty data or HTTP 404.
- **Fix Required**: Automatic translation from `.` to `-` for US market symbols before `yfinance` calls, while preserving `.` for FDR/Stooq where needed.

#### Issue C: Missing KONEX Market Suffix
- **Mechanism**: `_KR_MARKET_SUFFIX` in `run_pipeline.py:151-155`:
  ```python
  _KR_MARKET_SUFFIX = {
      'KOSPI': '.KS',
      'KOSDAQ': '.KQ',
      'KRX': '.KS',
  }
  ```
  `KONEX` is not mapped in `_KR_MARKET_SUFFIX`. Default `.KS` fallback is applied, but KONEX symbols on Yahoo Finance are not under `.KS`.
- **Fix Required**: Map `KONEX` to `.KX` or route KONEX queries directly to Naver/PyKRX fallbacks.

#### Issue D: Database Key Inconsistency & Fragmentation
- **Mechanism**: In `database.py`, `StockPriceDB` uses `(symbol, date)` as primary key.
- **Code Impact**: If `prefetch_prices_batch` saves price data under symbol `'005930'`, but an external script or test saves under `'005930.KS'`, SQLite stores duplicate rows under two distinct symbol keys.
- **Fix Required**: Enforce a single canonical symbol format across all internal databases and factor engines:
  - KRX: 6-digit zero-padded string (`'005930'`).
  - US: Clean uppercase string with hyphens (`'BRK-B'`).

---

## 2. Dependencies, Rate Limits & Failure Modes Audit

### 2.1 Provider Vulnerability Matrix

| Provider | Method / API | Failure Mode | Root Cause | Current Handling |
|----------|--------------|--------------|------------|------------------|
| **yfinance** | `yf.download()` | HTTP 429 Rate Limit | High-frequency bulk batch queries | Binary split retry increases request count |
| **yfinance** | `yf.download()` | HTTP 404 / YFTzMissingError | Delisted ticker or symbol format mismatch (`BRK.B`) | Handled via try-except, falls back to FDR |
| **yfinance** | `yf.download()` | 20-30s Hang / Timeout | Network instability / GHA runner connection drop | No per-request timeout parameter in `yf.download` |
| **FinanceDataReader** | `fdr.DataReader()` | HTTP 403 / 500 / Empty DF | Naver Finance HTML/JSON scraper layout changes | `@retry` decorator up to 3 attempts |
| **FinanceDataReader** | `fdr.StockListing()` | URL Timeout / KeyError | External URL schema change (iShares/Wikipedia) | Swallowed in try-except, returns empty DF |
| **StockPriceDB** | `update_prices()` | `database is locked` | Parallel thread writes during batch prefetching | Mutex lock `_write_lock` + busy timeout 60s |

### 2.2 Critical Vulnerability: Binary Split Request Escalation
In `run_pipeline.py` (`prefetch_prices_batch`, lines 332–346):
```python
# Binary split to isolate bad tickers
mid = len(tickers) // 2
left_tickers = tickers[:mid]
right_tickers = tickers[mid:]
df_left = _download_with_recovery(left_tickers, start_dt)
df_right = _download_with_recovery(right_tickers, start_dt)
```
When Yahoo Finance returns HTTP 429 (Rate Limit Exceeded), `_download_with_recovery` treats the HTTP error as a batch failure and splits the batch into two halves. This doubles the number of HTTP requests sent to Yahoo, escalating rate-limit blocks into IP-level blacklists.

**Solution**: Differentiate between ticker-level data errors (delisted symbol) and network-level rate limits (HTTP 429/503). On rate-limit response, sleep with exponential backoff rather than binary splitting.

---

## 3. Fallback Historical Data Sources Architecture

To guarantee 100% data availability across all 3,379 symbols, a 5-tier fallback cascade is designed:

### 3.1 KRX Fallback Architecture (KOSPI, KOSDAQ, KONEX)

```
[Tier 1: yfinance]  --->  [Tier 2: FinanceDataReader]  --->  [Tier 3: Naver Direct API]  --->  [Tier 4: PyKRX]  --->  [Tier 5: StockPriceDB Cache]
```

1. **Tier 1: `yfinance`** (`005930.KS`, `086520.KQ`) — Fast batch downloading.
2. **Tier 2: `FinanceDataReader`** (`005930`) — Scraping fallback via FDR.
3. **Tier 3: Naver Finance Direct API** — Zero-dependency direct HTTP call:
   - Endpoint: `https://fchart.stock.naver.com/sise.nhn?symbol={code}&timeframe=day&count=500&requestType=0`
   - Returns clean XML/CSV chart data containing Open, High, Low, Close, Volume.
4. **Tier 4: `PyKRX`** — Direct KRX data system query:
   - Method: `pykrx.stock.get_market_ohlcv_by_date(start_date, end_date, code)`
   - Authoritative official price history for all KRX symbols including KONEX.
5. **Tier 5: `StockPriceDB`** — Local SQLite WAL offline cache.

### 3.2 US Fallback Architecture (SP500, NASDAQ, RUSSELL2000)

```
[Tier 1: yfinance]  --->  [Tier 2: FinanceDataReader]  --->  [Tier 3: Stooq Direct API]  --->  [Tier 4: Yahoo Direct Web API]  --->  [Tier 5: StockPriceDB Cache]
```

1. **Tier 1: `yfinance`** (`AAPL`, `BRK-B`) — Batch primary fetcher.
2. **Tier 2: `FinanceDataReader`** (`AAPL`) — FDR secondary fetcher.
3. **Tier 3: Stooq Direct CSV API**:
   - Endpoint: `https://stooq.com/q/d/l/?s={symbol}.us&i=d`
   - Returns direct CSV stream parsed by `pd.read_csv()`. Free, no API key, high uptime.
4. **Tier 4: Yahoo Direct Chart JSON API**:
   - Endpoint: `https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=2y`
   - Bypasses `yfinance` library overhead using standard Python `urllib`/`requests` with custom User-Agent.
5. **Tier 5: `StockPriceDB`** — Local SQLite WAL offline cache.

---

## 4. Contiguous OHLCV & Strategy NaN Handling Audit

### 4.1 18 Strategy Requirements & Price Sensitivity Matrix

| # | Strategy Name | Source File | Minimum Bars | Primary Data Columns | Sensitivity to NaNs / Gaps |
|---|---------------|-------------|--------------|----------------------|----------------------------|
| 1 | XGBoost Regression | `src/ai/prediction_model.py` | 200 | OHLCV + Indicators | High (Rolling features up to 200d) |
| 2 | Surge Classifier | `src/ai/vcp_ml_predictor.py` | 60 | OHLCV | High (Volume surge calculation) |
| 3 | Lead-Lag | `src/ai/prediction_model.py` | 60 | Close | Medium (Cross-correlation matrix) |
| 4 | VCP Pattern Rule | `src/ai/vcp_detector.py` | 50 | OHLCV | High (Volatility contraction min/max) |
| 5 | VCP ML Predictor | `src/ai/vcp_ml_predictor.py` | 60 | OHLCV | High (Classifier feature alignment) |
| 6 | Strict Causal LSTM | `src/ai/lstm_predictor.py` | 60 | Close, Volume | High (Fixed sequence length window) |
| 7 | Stat-Arb Cointegration | `src/core/stat_arb.py` | 60 | Log Close | High (Log prices diff & Z-score) |
| 8 | Sector Rotation | `src/core/sector_rotation.py` | 60 | Close | Medium (1M/3M momentum ranking) |
| 9 | RIM Valuation | `src/core/rim_valuation.py` | 1 | Close, Fundamentals | Low (Point-in-time Close price) |
| 10 | Event-Driven | `src/core/event_driven.py` | 20 | Close, Volume | Medium (Volume spike ratio) |
| 11 | Momentum Quality (MQ) | `src/core/mq_factor.py` | 252 | Close | High (12M-1M momentum lookback) |
| 12 | Options IV Skew | `src/core/iv_skew.py` | 1 | Close, Option Chain | Low (Options IV delta) |
| 13 | Order Flow Imbalance | `src/core/order_flow.py` | 20 | Close, MFI | Medium (MFI volume acceleration) |
| 14 | Short-Term Reversal | `src/core/short_term_reversal.py` | 20 | Close, Low, High | High (Bollinger lower band distance) |
| 15 | Analyst Revision (ARM) | `src/core/arm_factor.py` | 20 | Close, Consensus | Medium (Target price gap) |
| 16 | Cross-Asset CARD | `src/core/card_factor.py` | 60 | Close, FX, Oil, Gold | High (Macro divergence correlation) |
| 17 | Liquidity Tail Risk (LATR)| `src/core/latr_factor.py` | 252 | Close, Volume | High (52W Max Drawdown & Tail Risk) |
| 18 | Inst & Foreign Sector | `src/core/inst_foreign_sector.py`| 40 | Close, Net Buying | Medium (2M institutional accumulation) |

### 4.2 Data Integrity Gaps & Recommendations

1. **Intermediate Date Alignment**: Trading calendar gaps (e.g. holidays or suspended days) produce NaNs in rolling indicators (`sma_20`, `rsi_14`, `atr_14`).
   - **Recommendation**: Apply `.asfreq('D').ffill()` or align against market trading calendar index before calculating rolling indicators.
2. **Short History Handling**: Newly listed symbols with `< 200` rows are currently excluded in `run_pipeline.py:1197`.
   - **Recommendation**: For newly listed symbols (IPO), compute available horizon returns dynamically and apply a missingness coverage penalty in `ensemble_scorer.py` rather than hard-dropping the symbol.
3. **Data Quality Gate Reinforcement**: DataValidator in `run_pipeline.py:258-308` validates price data before DB insertion. Add explicit check for contiguous dates and zero-volume suspensions.

---

## Conclusion & Proposed Architecture

Implementing a unified `TickerNormalizer` module, a 5-tier multi-fallback data retriever (`MultiSourcePriceFetcher`), and strict contiguous OHLCV alignment will eliminate price data gaps, resolve rate limits, and guarantee reliable execution across all 3,379 symbols and 18 multi-factor strategies.
