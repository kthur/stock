# Price Fetch Hardening — Survey 3: Automated Test Suite & Strategy Dependencies Analysis

**Investigator**: Explorer 3  
**Date**: 2026-08-06  
**Working Directory**: `d:\Finance\code\stock\.agents\explorer_survey_3`  
**Target Project**: Stock Trading System (`d:\Finance\code\stock`)  

---

## Executive Summary

This report delivers a comprehensive audit of the automated test suite and strategy dependencies on price data for the **Price Fetch Hardening Project**. 

Key Findings:
1. **Existing Test Suite Audit**: Existing database and caching tests (`trading_system/tests/test_database.py`, `tests/test_database_concurrency.py`, `tests/test_empirical_concurrency_m1_2.py`, `trading_system/tests/test_data_validator.py`) focus heavily on SQLite WAL multi-threaded write lock concurrency and macro data cleaning. However, **zero unit or integration tests exist** for network price fetching (FinanceDataReader, yfinance), network retries, exponential backoff, circuit breakers, ticker symbol normalization, or multi-tier fallback hierarchies.
2. **Strategy Dependency Audit**: Each of the 18 multi-factor strategies consumes price data with specific row-length thresholds ranging from 1 row to 200 rows. If price data is missing, zero-length, or has `< 65 rows`, Strategies 1 (XGBoost Regression), 2 (Surge Classifier), and 5 (VCP ML) drop the symbol entirely from output. If `< 200 rows`, Strategy 4 (VCP Rule) returns score 0.
3. **Test Gap Identification & Actionable Recommendations**: Detailed specifications for 5 new unit and integration test modules covering network retry, ticker symbol normalization, multi-tier fallback, 18-strategy zero-row/NaN resilience, and dynamic ensemble partial coverage.

---

## 1. Audit of Existing Test Suite (`trading_system/tests/` and `tests/`)

### 1.1 Summary of Existing Tests Related to Price & Persistence

| Test File | Target Module | Scope & What Is Tested | Price Fetching / Retry Coverage |
|---|---|---|---|
| `trading_system/tests/test_database.py` | `StockPriceDB`, `MarketIndicatorStorage`, `TradeLogger`, `AssetHistoryDB` | Tests multi-threaded writes (`update_prices`) with 5 threads x 15 writes, `save_fundamentals`, `save_indicators` concurrency lock safety. | ❌ No network fetch / retry / fallback tests |
| `tests/test_database_concurrency.py` | `StockPriceDB`, `HybridDataEngine`, `ParquetWALBuffer` | Tests 20 concurrent threads writing `StockPriceDB.update_prices` and WAL buffer staging/flushing. | ❌ No network fetch / retry / fallback tests |
| `tests/test_empirical_concurrency_m1_2.py` | `StockPriceDB`, `HybridDataEngine` | High-load stress test with 50 writer threads x 3,379 symbols + 10 reader threads verifying SQLite WAL performance. | ❌ No network fetch / retry / fallback tests |
| `trading_system/tests/test_data_validator.py` | `DataValidator` | Verifies `detect_shared_series_corruption`, `clean_macro_value`, and `validate_price_data` for all-NaN DataFrames. | ❌ Tests static validation only |

### 1.2 Identified Test Suite Deficiencies

1. **No Network Failure or Retry Tests**:
   - `MarketDataHandler` (`trading_system/src/data_layer/market_data_handler.py:149-183`) implements `@retry` via `tenacity`, `RateLimiter` (token bucket), and `CircuitBreaker`.
   - **Finding**: There are zero tests simulating network timeouts, HTTP 429 Rate Limit responses, or verifying circuit breaker transitions (CLOSED -> OPEN -> HALF-OPEN).
2. **No Ticker Normalization Tests**:
   - The system handles symbols across 6 markets (`SP500`, `NASDAQ`, `RUSSELL2000`, `KOSPI`, `KOSDAQ`, `KONEX`). Tickers differ by platform (e.g., KRX numeric codes `005930` vs `005930.KS`, US tickers `BRK.B` vs `BRK-B`, index symbols `^GSPC`, `^KS11`).
   - **Finding**: No unit tests exist for symbol mapping, prefix/suffix handling, or alias conversion.
3. **No Multi-Tier Fallback Tests**:
   - `run_pipeline.py:382-426` (`fetch_data_fdr`) uses a 3-tier fallback strategy:
     - Tier 1: Fresh `StockPriceDB` cache
     - Tier 2: Network fetch (yfinance / FinanceDataReader)
     - Tier 3: Stale `StockPriceDB` cache fallback
   - **Finding**: No test verifies that if Tier 2 network fetch fails due to network outage, the pipeline falls back gracefully to Tier 3 without throwing an unhandled exception.

---

## 2. Audit of Strategy Dependencies on Price History (18 Multi-Factor Strategies)

A detailed code audit was conducted across all strategy implementations in `trading_system/src/ai/` and `trading_system/src/core/`.

### 2.1 Strategy-by-Strategy Price Consumption & Threshold Matrix

| # | Strategy Name | Implementation File | Key Columns Consumed | Min Rows Required | Behavior on Inadequate Data / Zero Rows / NaNs |
|---|---|---|---|---|---|
| **1** | XGBoost Regression | `src/ai/prediction_model.py:1026, 2098` | `Open`, `High`, `Low`, `Close`, `Volume` | **65 rows** | If `< 65` rows or empty/None, `_create_features` returns empty DataFrame and `_process_one` returns `None`. Symbol is **silently omitted** from predictions. |
| **2** | Surge Classifier | `src/ai/prediction_model.py:1026, 2098` | `Open`, `High`, `Low`, `Close`, `Volume` | **65 rows** | Shares feature computation with Strategy 1. If `< 65` rows or empty/None, symbol returns `None` and is dropped from `surge_predictions.txt`. |
| **3** | Lead-Lag Shift | `src/ai/prediction_model.py:2619` | `Close` | **2 rows** | If `< 2` rows or None, symbol skipped (`continue`). Fallback mode uses 2-row return `(c.iloc[-1]/c.iloc[0]) - 1`. |
| **4** | VCP Rule Pattern | `src/ai/vcp_detector.py:87` | `High`, `Low`, `Close`, `Volume` | **200 rows** | If `< 200` rows or None/empty, safely returns `{is_vcp: False, vcp_score: 0.0, pivot_price: ...}`. |
| **5** | VCP ML Predictor | `src/ai/vcp_ml_predictor.py:132` | 11 VCP features from OHLCV | **65 rows** | If `< 65` rows or None/empty, returns empty DataFrame; symbol excluded from VCP ML surge predictions. |
| **6** | Strict Causal LSTM | `src/ai/lstm_predictor.py:61, 118` | `Close` sequence (len=20) | **20 rows** | If untrained or sample count `< 5`, returns array of zeros (`np.zeros`). |
| **7** | Stat-Arb Cointegration | `src/core/stat_arb.py:40, 106` | Log `Close` prices, `High`, `Low` | **10 rows** | If `< 10` rows, `_extract_15d_features` returns zero vector `np.zeros(15)`. Clamps zero/negative prices with `np.maximum(prices, 1e-5)` and cleans NaNs with `np.nan_to_num`. |
| **8** | Sector Rotation | `src/core/sector_rotation.py:95, 102` | `Close` | **20 rows** | If `< 20` rows or None/empty, symbol skipped (`continue`). Uses 20d return as fallback for 60d return if rows between 20 and 59. |
| **9** | RIM Valuation | `src/core/rim_valuation.py:120` | `Close.iloc[-1]` | **1 row** | Compares current price vs intrinsic value $V_0$. If price missing or `<= 0`, discount calculation avoids div-by-zero. |
| **10** | Event-Driven | `src/core/event_driven.py:152` | `Close`, `Volume` | **5 rows** | If `< 5` rows or None/empty, symbol skipped (`continue`). Computes 5-day volume ratio and 5-day return surge. |
| **11** | Momentum Quality (MQ) | `src/core/mq_factor.py:34, 41` | `Close` | **30 rows** | If `< 30` rows or None/empty, symbol skipped (`continue`). Uses `iloc[0]` as fallback for $t-252$ price if rows between 30 and 251. |
| **12** | Options IV Skew | `src/core/iv_skew.py:102, 108` | `Close` | **20 rows** | Uses 20-day historical volatility as fallback if options IV fetch fails. If `< 20` rows, returns default neutral score (0.5). |
| **13** | Order Flow Imbalance | `src/core/order_flow.py:36, 49` | `Close`, `Volume` | **10 rows** | If `< 10` rows or None/empty, symbol skipped (`continue`). Calculates 10-day Money Flow Index (MFI). |
| **14** | Short-Term Reversal | `src/core/short_term_reversal.py:35, 42` | `Close` | **20 rows** | If `< 20` rows or None/empty, symbol skipped (`continue`). Computes 5-day return and 20-day Bollinger Band lower distance. |
| **15** | Analyst Revision (ARM) | `src/core/arm_factor.py:47` | `Close` | **20 rows** | If `< 20` rows, returns base consensus score without price trend acceleration adjustment. |
| **16** | Cross-Asset Divergence | `src/core/card_factor.py:66` | `Close` | **5 rows** | If `< 5` rows or `close <= 0`, returns default neutral score (0.5). |
| **17** | Liquidity Tail Risk | `src/core/latr_factor.py:32, 37` | `Close` | **20 rows** | If `< 20` rows or None/empty, symbol skipped (`continue`). Dynamically adjusts lookback window to `min(len(close), 252)`. |
| **18** | Inst & Foreign Sector | `src/core/inst_foreign_sector.py:101, 114` | `Close` | **15 rows** | If `< 15` rows or None/empty, symbol skipped (`continue`). |

### 2.2 Failure Modes & Impact Analysis

1. **Silent Dropping of Tickers (Short Price History)**:
   - Newly listed IPOs or newly added universe tickers with `< 65` trading days will be **silently excluded** from Regression, Surge, and VCP ML predictions.
   - While this prevents fitting models on insufficient data, it causes missing strategy entries in `ensemble_predictions.txt` unless the ensemble layer handles partial inputs.
2. **NaN Propagation Mitigation**:
   - Key modules (`stat_arb.py`, `prediction_model.py`, `vcp_detector.py`) protect against NaNs using `fillna(0.0)`, `replace([np.inf, -np.inf], 0.0)`, `np.nan_to_num`, or division smoothing (`+ 1e-9` / `+ 1e-10`).
3. **Zero-Row Price Data Vulnerability**:
   - If network fetching returns an empty DataFrame (0 rows) and DB cache is empty, all strategies safely skip or return default scores. However, if price fetching fails silently for active tickers, those tickers receive no signals across all strategies, producing zero predictions in final output reports.

---

## 3. Test Gap Analysis & Recommended Test Implementations

To ensure 100% test coverage and prevent regressions during price fetch hardening, the following 5 new test modules are recommended:

### 3.1 `tests/test_price_fetcher_retries.py` (Unit Tests for Network Resilience)
- **Objective**: Verify that `MarketDataHandler` retry, rate limiter, and circuit breaker logic perform as expected under network stress.
- **Test Cases**:
  1. `test_yf_retry_on_network_failure`: Mock `yf.Ticker.fast_info` / `.history` to raise `ConnectionError` or `Timeout` on attempts 1-2, succeeding on attempt 3. Assert fetch succeeds.
  2. `test_circuit_breaker_opens_after_5_failures`: Mock network calls to fail 5 consecutive times. Assert circuit breaker transitions to `is_open = True` and raises `CircuitBreakerOpenException` without executing subsequent network calls.
  3. `test_circuit_breaker_resets_after_timeout`: Advance system clock past `reset_timeout` (60s). Assert circuit breaker transitions to HALF-OPEN and permits retry.
  4. `test_rate_limiter_throttling`: Call `RateLimiter.wait()` rapidly 10 times in multi-threaded environment. Assert token bucket enforces configured rate limit.

### 3.2 `tests/test_ticker_normalization.py` (Unit Tests for Symbol Aliasing)
- **Objective**: Ensure seamless ticker symbol conversion across Korean (KRX) and US markets.
- **Test Cases**:
  1. `test_krx_ticker_formatting`: Test inputs `"5930"`, `"005930"`, `"005930.KS"`, `"091990.KQ"`. Assert proper normalization to 6-digit zero-padded codes and market assignment.
  2. `test_us_ticker_dot_dash_conversion`: Test inputs `"BRK.B"`, `"BRK-B"`, `"BF.B"`, `"BF-B"`. Assert conversion to yfinance compatible dash notation (`BRK-B`) and database dot notation (`BRK.B`).
  3. `test_index_symbol_mapping`: Test index tickers (`^GSPC`, `^IXIC`, `^RUT`, `^KS11`, `^KQ11`). Assert valid market mapping and indicator feature merging.

### 3.3 `tests/test_price_fetcher_fallback.py` (Integration Tests for Multi-Tier Fetching)
- **Objective**: Validate the 3-tier fallback hierarchy in `fetch_data_fdr` / `fetch_indicator_history`.
- **Test Cases**:
  1. `test_db_cache_hit_bypasses_network`: Pre-populate `StockPriceDB` with fresh price data. Mock network calls. Assert data returned directly from DB without calling network.
  2. `test_network_fetch_updates_db_cache`: With empty `StockPriceDB`, mock network fetch to return valid OHLCV. Assert `StockPriceDB` is updated and fresh data returned.
  3. `test_network_failure_falls_back_to_stale_db_cache`: Pre-populate `StockPriceDB` with stale price data (>1 day old). Mock network fetch to raise network timeout. Assert fetcher catches exception and falls back to stale `StockPriceDB` data.

### 3.4 `tests/test_strategy_price_resilience.py` (Unit Tests for Strategy Edge Cases)
- **Objective**: Verify all 18 multi-factor strategies handle invalid, empty, NaN, or short price histories gracefully.
- **Test Cases**:
  1. `test_strategies_zero_rows_resilience`: Pass empty DataFrame (`pd.DataFrame()`) to all 18 strategies. Assert 0 unhandled exceptions (`IndexError`, `KeyError`, `ValueError`).
  2. `test_strategies_nan_prices_resilience`: Pass DataFrame with `np.nan` values in `Close`, `High`, `Low`, `Volume`. Assert no crash or unhandled NaN propagation.
  3. `test_strategies_short_history_resilience`: Pass DataFrames with 1, 5, 19, 64, and 199 rows. Verify strategies respect minimum row thresholds (65 for Regression/Surge/VCP ML, 200 for VCP Rule) without throwing errors.
  4. `test_strategies_missing_columns_resilience`: Pass DataFrames missing non-essential columns. Verify fallback computation or graceful skipping.

### 3.5 `tests/test_ensemble_partial_coverage.py` (Integration Test for Dynamic Ensemble under Missing Data)
- **Objective**: Ensure `EnsembleScoringEngine` computes valid, non-zero ensemble scores when subset of strategies (e.g. 10 of 18) are present for a given symbol due to price length limitations.
- **Test Cases**:
  1. `test_ensemble_scoring_with_missing_strategy_inputs`: Provide mock predictions for a symbol where 5 strategies are missing. Verify dynamic weight normalization scales remaining strategy weights to sum to 1.0 and yields a valid ensemble score.
