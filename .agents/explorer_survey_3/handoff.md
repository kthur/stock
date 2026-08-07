# Price Fetch Hardening — Survey 3 Handoff Report

**Agent**: Explorer 3  
**Date**: 2026-08-06  
**Working Directory**: `d:\Finance\code\stock\.agents\explorer_survey_3`  

---

## 1. Observation

Direct observations from the codebase and existing automated test suite:

1. **Existing Test Suite Coverage**:
   - `trading_system/tests/test_database.py` (lines 245–294): Contains `TestStockPriceDBConcurrency`, which tests 5 concurrent threads executing `StockPriceDB.update_prices` using synthetic DataFrames (`Open`, `High`, `Low`, `Close`, `Volume`).
   - `tests/test_database_concurrency.py` (lines 33–74): Contains `test_stock_price_db_concurrency_zero_lock_errors` testing 20 concurrent threads on `StockPriceDB.update_prices`.
   - `tests/test_empirical_concurrency_m1_2.py` (lines 32–96): Tests high-concurrency SQLite WAL lock safety under 50 writer threads.
   - `trading_system/tests/test_data_validator.py` (lines 26–40): Contains `test_validate_price_data` testing `DataValidator.validate_price_data` with valid and all-NaN DataFrames.
   - **Zero existing tests** in `tests/` or `trading_system/tests/` test network fetching (`FinanceDataReader`, `yfinance`), retry handling, exponential backoff, circuit breaker transitions, ticker symbol normalization, or fallback data fetching.

2. **Strategy Dependencies & Row Minimums**:
   - **Strategies 1 & 2 (XGBoost Regression & Surge Classifier)**: `trading_system/src/ai/prediction_model.py` (line 1026: `if len(df) < 65: return pd.DataFrame()`; line 2098: `if df is None or len(df) < 65: return None`). Requires **65 rows**.
   - **Strategy 3 (Lead-Lag Shift)**: `trading_system/src/ai/prediction_model.py` (line 2619: `if df is None or len(df) < 2:`). Requires **2 rows**.
   - **Strategy 4 (VCP Rule Pattern)**: `trading_system/src/ai/vcp_detector.py` (line 87: `if df is None or len(df) < 200: return {'is_vcp': False, 'vcp_score': 0.0, ...}`). Requires **200 rows**.
   - **Strategy 5 (VCP ML Predictor)**: `trading_system/src/ai/vcp_ml_predictor.py` (line 132: `if df is None or len(df) < 65: return pd.DataFrame()`). Requires **65 rows**.
   - **Strategy 6 (Strict Causal LSTM)**: `trading_system/src/ai/lstm_predictor.py` (line 61: `if len(X_train) < 5:`). Requires **20 rows** sequence length.
   - **Strategy 7 (Stat-Arb Cointegration)**: `trading_system/src/core/stat_arb.py` (line 40: `if len(prices) < 10: return np.zeros(15)`). Requires **10 rows**. Uses `np.log(np.maximum(prices, 1e-5))` and `np.nan_to_num`.
   - **Strategy 8 (Sector Rotation)**: `trading_system/src/core/sector_rotation.py` (line 95: `if df is None or len(df) < 20:`). Requires **20 rows**.
   - **Strategy 9 (RIM Valuation)**: `trading_system/src/core/rim_valuation.py` (line 120). Requires **1 row**.
   - **Strategy 10 (Event-Driven)**: `trading_system/src/core/event_driven.py` (line 152: `if sym not in scores_map or df is None or len(df) < 5:`). Requires **5 rows**.
   - **Strategy 11 (Momentum Quality - MQ)**: `trading_system/src/core/mq_factor.py` (line 34: `if df is None or len(df) < 30:`). Requires **30 rows**.
   - **Strategy 12 (Options IV Skew)**: `trading_system/src/core/iv_skew.py` (line 102: `if df is not None and len(df) >= 20:`). Requires **20 rows**.
   - **Strategy 13 (Order Flow Imbalance)**: `trading_system/src/core/order_flow.py` (line 36: `if df is None or len(df) < 10:`). Requires **10 rows**.
   - **Strategy 14 (Short-Term Reversal)**: `trading_system/src/core/short_term_reversal.py` (line 35: `if df is None or len(df) < 20:`). Requires **20 rows**.
   - **Strategy 15 (Analyst Revision Momentum - ARM)**: `trading_system/src/core/arm_factor.py` (line 47: `if len(close) >= 20:`). Requires **20 rows**.
   - **Strategy 16 (Cross-Asset Divergence - CARD)**: `trading_system/src/core/card_factor.py` (line 66: `if len(close) < 5 or float(close.iloc[-5]) <= 0:`). Requires **5 rows**.
   - **Strategy 17 (Liquidity Tail Risk - LATR)**: `trading_system/src/core/latr_factor.py` (line 32: `if len(close) < 20:`). Requires **20 rows**.
   - **Strategy 18 (Inst & Foreign Sector)**: `trading_system/src/core/inst_foreign_sector.py` (line 101: `if df is None or len(df) < 15:`). Requires **15 rows**.

3. **Fetch & Retry Mechanisms**:
   - `trading_system/src/data_layer/market_data_handler.py` (lines 149–183): Implements `RateLimiter`, `CircuitBreaker`, and `@retry` on `_fetch_yf_with_retry`.
   - `trading_system/run_pipeline.py` (lines 382–426): Implements multi-tier fallback `fetch_data_fdr` (Tier 1 DB cache -> Tier 2 network -> Tier 3 stale DB fallback).

---

## 2. Logic Chain

1. **Observation 1** shows that existing tests focus almost exclusively on DB concurrency locks and basic static data validation.
2. Therefore, network failure modes (such as API rate limiting, network timeouts, circuit breaker open state, or ticker alias mismatches) are currently untested, creating a high risk of unexpected runtime failures during live pipelines or GHA runs.
3. **Observation 2** shows that price row requirements differ across strategies, with minimum row thresholds ranging from 1 to 200 rows.
4. Specifically, if a ticker returns `< 65` rows of price history, Strategies 1, 2, and 5 drop the ticker completely; if `< 200` rows, Strategy 4 scores 0.
5. If price fetching fails and returns 0 rows (empty DataFrame), all 18 strategies skip or default gracefully without throwing unhandled exceptions, but the symbol yields zero predictions in the final report.
6. Combining step 2 and step 5 leads to the **conclusion** that new targeted unit and integration tests are required for network retries, rate limiting, ticker normalization, multi-tier fallback fetching, and strategy resilience under zero-row / NaN data.

---

## 3. Caveats

- **External Network Dependency**: Unit tests for network retries and fallbacks must mock `yf.Ticker` and `fdr.DataReader` using `unittest.mock` to prevent tests from depending on live internet connections or external API availability.
- **Dynamic Ensemble Weighting**: When a symbol has `< 65` price rows, it receives zero predictions from Strategies 1, 2, and 5. The ensemble engine relies on dynamic weight re-normalization to score the remaining strategy outputs.

---

## 4. Conclusion

The current test suite provides strong coverage for database concurrency and multi-threaded SQLite WAL locks, but has critical test coverage gaps regarding network price fetching, retries, ticker symbol normalization, fallback fetchers, and edge cases across the 18 multi-factor strategies.

5 new test modules are recommended:
1. `tests/test_price_fetcher_retries.py` (Network retry, rate limiter, circuit breaker unit tests)
2. `tests/test_ticker_normalization.py` (Symbol alias conversion and KRX/US ticker normalization)
3. `tests/test_price_fetcher_fallback.py` (Multi-tier cache/network fallback integration tests)
4. `tests/test_strategy_price_resilience.py` (0-row, NaN, missing column, and short history edge case tests for all 18 strategies)
5. `tests/test_ensemble_partial_coverage.py` (Dynamic ensemble scoring under partial strategy availability)

---

## 5. Verification Method

To verify these findings and execute the unit test suite:

1. **Run Full Unit Test Suite**:
   ```bash
   .venv\Scripts\python.exe -m pytest tests/ -v
   .venv\Scripts\python.exe -m pytest trading_system/tests/ -v
   ```
2. **Inspect Findings File**:
   - Inspect `d:\Finance\code\stock\.agents\explorer_survey_3\analysis.md` for full strategy-by-strategy details and code line references.
3. **Invalidation Conditions**:
   - If any strategy throws an unhandled `IndexError`, `KeyError`, or `ValueError` when passed an empty DataFrame `pd.DataFrame()`, the strategy code must be updated with standard length checks (`if df is None or len(df) < MIN_ROWS: return ...`).
