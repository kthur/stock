# Technical Survey Report: Inference Vectorization & SQLite Concurrency Protection (Requirement R2)

**Author:** Explorer 2  
**Working Directory:** `d:/Finance/code/stock/.agents/explorer_survey_2/`  
**Date:** 2026-08-12  
**Target Codebase:** `d:/Finance/code/stock/trading_system/`  

---

## 1. Executive Summary

This investigation analyzed the Stock Trading System codebase (`d:/Finance/code/stock/`) for Requirement R2 of the 31-Strategy Multi-Factor Engine enhancement project:
1. **Inference Vectorization**: Identifying symbol-level loop bottlenecks during model and strategy scoring inference across 3,379 symbols (KOSPI, KOSDAQ, KONEX, S&P 500, NASDAQ, Russell 2000) that can be refactored to NumPy/Pandas matrix operations.
2. **SQLite Concurrency Protection**: Reviewing SQLite database connection setups in `StockPriceDB`, `MarketIndicatorStorage`, `UnifiedStorageEngine`, and auxiliary execution modules to verify `PRAGMA busy_timeout = 30000;` and WAL mode configuration across all connections and thread pools.
3. **Existing Test Coverage**: Cataloging unit tests in `tests/` and `trading_system/tests/` covering inference models, strategy scorers, and multi-threaded SQLite database concurrency.

---

## 2. Inference Vectorization Analysis

### 2.1 `OnDevicePredictionModel` (`trading_system/src/ai/prediction_model.py`)

#### Bottleneck 1: Item-by-Item LSTM Model Inference Loop
* **Location:** `trading_system/src/ai/prediction_model.py`, Lines 2319–2338 in `_predict_regression()`
* **Current Implementation:**
  ```python
  if lstm_m is not None and w_lstm_val > 0 and prices_dict is not None:
      lstm_preds = []
      for idx_val in idx:
          sym = symbols_list[idx_val]
          df_price = prices_dict.get(sym)
          if df_price is not None and len(df_price) >= 20:
              close_series = df_price['Close']
              if isinstance(close_series, pd.DataFrame):
                  close_series = close_series.iloc[:, 0]
              ret_seq = close_series.pct_change().dropna().tail(20).values
              if len(ret_seq) == 20:
                  x_in = ret_seq.reshape(1, 20, 1)
                  pred_val = lstm_m.predict(x_in)[0]  # <--- Individual model call inside Python loop!
                  lstm_preds.append(pred_val)
              else:
                  lstm_preds.append(0.0)
          else:
              lstm_preds.append(0.0)
      preds.append(np.array(lstm_preds))
      weights.append(w_lstm_val)
  ```
* **Performance Impact:** For $N = 3,379$ symbols, `lstm_m.predict(x_in)` is invoked 3,379 separate times with single-sample shape `(1, 20, 1)`, incurring immense Python function call overhead and disabling PyTorch/Keras batch GPU/CPU acceleration.
* **Vectorized Refactoring Plan:**
  Construct a single 3D NumPy array batch `X_batch` of shape `(N, 20, 1)` for all valid symbols in `idx`, and run `lstm_m.predict(X_batch)` in a single vectorized operation:
  ```python
  valid_indices = []
  seq_list = []
  for i, idx_val in enumerate(idx):
      sym = symbols_list[idx_val]
      df_price = prices_dict.get(sym)
      if df_price is not None and len(df_price) >= 20:
          close_series = df_price['Close']
          if isinstance(close_series, pd.DataFrame):
              close_series = close_series.iloc[:, 0]
          ret_seq = close_series.pct_change().dropna().tail(20).values
          if len(ret_seq) == 20:
              valid_indices.append(i)
              seq_list.append(ret_seq.reshape(20, 1))

  lstm_preds = np.zeros(len(idx), dtype=np.float32)
  if seq_list:
      X_batch = np.array(seq_list, dtype=np.float32)  # Shape: (N_valid, 20, 1)
      batch_preds = lstm_m.predict(X_batch, verbose=0).ravel()
      lstm_preds[valid_indices] = batch_preds
  preds.append(lstm_preds)
  ```

#### Bottleneck 2: Sequential Symbol Loop in Lead-Lag Prediction
* **Location:** `trading_system/src/ai/prediction_model.py`, Lines 2715–2723 in `predict_lead_lag()`
* **Current Implementation:**
  ```python
  today_returns = {}
  for sym, df in prices_dict.items():
      if df is None or len(df) < 2:
          continue
      close = df['Close']
      if isinstance(close, pd.DataFrame):
          close = close.iloc[:, 0]
      ret_1d = (close.iloc[-1] / close.iloc[-2]) - 1
      today_returns[sym] = ret_1d
  ```
* **Performance Impact:** Iterates over thousands of DataFrames to compute simple 1-day percentage returns.
* **Vectorized Refactoring Plan:** Construct a 2-row DataFrame of `Close` prices for all symbols and calculate daily returns across columns vectorized:
  ```python
  last2_df = pd.DataFrame({
      sym: df['Close'].iloc[-2:].values if (df is not None and len(df) >= 2) else [np.nan, np.nan]
      for sym, df in prices_dict.items()
  })
  today_returns_series = (last2_df.iloc[-1] / last2_df.iloc[-2] - 1.0).fillna(0.0)
  today_returns = today_returns_series.to_dict()
  ```

---

### 2.2 Strategy Engine Scorers (`trading_system/src/core/`)

#### Bottleneck 3: `TrendEfficiencyEngine` (`trading_system/src/core/trend_efficiency.py`)
* **Location:** Lines 77–109 in `calculate_scores()`
* **Current Code:**
  ```python
  for sym in symbols:
      p_df = prices_dict.get(sym_str)
      c_series = p_df[close_col].dropna()
      ker5 = self._compute_ker(c_series, 5)
      ker10 = self._compute_ker(c_series, 10)
      ker20 = self._compute_ker(c_series, 20)
      avg_ker = (ker5 + ker10 + ker20) / 3.0
      ret_20d = (c_series.iloc[-1] / c_series.iloc[-21]) - 1.0
      ...
  ```
* **Analysis & Bottleneck:** Inside `_compute_ker()`, `series.iloc[-window-1:].diff().abs().sum()` is called 3 times per symbol. For 3,379 symbols, this executes over 10,000 Series slice and diff calls.
* **Vectorized Refactoring Plan:** Extract 21-day close prices for all symbols into a single 2D DataFrame (dates x symbols) `close_matrix`. Compute Kaufman Efficiency Ratios across axis 0:
  ```python
  change_5 = (close_matrix.iloc[-1] - close_matrix.iloc[-6]).abs()
  vol_5 = close_matrix.iloc[-6:].diff().abs().sum(axis=0)
  ker5 = (change_5 / vol_5).replace([np.inf, -np.inf], 0.0).fillna(0.0)
  
  change_10 = (close_matrix.iloc[-1] - close_matrix.iloc[-11]).abs()
  vol_10 = close_matrix.iloc[-11:].diff().abs().sum(axis=0)
  ker10 = (change_10 / vol_10).replace([np.inf, -np.inf], 0.0).fillna(0.0)
  
  change_20 = (close_matrix.iloc[-1] - close_matrix.iloc[-21]).abs()
  vol_20 = close_matrix.iloc[-21:].diff().abs().sum(axis=0)
  ker20 = (change_20 / vol_20).replace([np.inf, -np.inf], 0.0).fillna(0.0)
  
  avg_ker = (ker5 + ker10 + ker20) / 3.0
  ret_20d = (close_matrix.iloc[-1] / close_matrix.iloc[-21]) - 1.0
  scores = np.where(ret_20d > 0, avg_ker * (1.0 + np.minimum(1.0, ret_20d * 2.0)), avg_ker * np.maximum(0.1, 1.0 + ret_20d))
  ```

#### Bottleneck 4: `ShortTermReversalEngine` (`trading_system/src/core/short_term_reversal.py`)
* **Location:** Lines 67–100 in `compute_reversal_scores()`
* **Current Code:**
  ```python
  for sym, df in prices_dict.items():
      close = df['Close'].dropna()
      ret_5d = float(close.iloc[-1] / close.iloc[-6] - 1.0)
      sma_20 = float(close.iloc[-20:].mean())
      std_20 = float(close.iloc[-20:].std())
      lower_band = sma_20 - 2.0 * std_20
      dist_lower_band = (cur_price - lower_band) / (std_20 + 1e-8)
  ```
* **Vectorized Refactoring Plan:** Construct a 20-day close price matrix `close_2d` (20 rows x $N$ columns). Compute 20-day mean, std, 5-day return, and Bollinger lower band distance across columns simultaneously.

#### Bottleneck 5: `AccrualsQualityEngine` (`trading_system/src/core/accruals_quality.py`)
* **Location:** Lines 81–106 in `calculate_scores()`
* **Current Code:** Iterates `for sym in symbols:` pulling fundamental dictionary keys (`net_income`, `operating_cash_flow`, `total_assets`) row by row.
* **Vectorized Refactoring Plan:** Convert `fund_map` dictionary to a single Pandas DataFrame indexed by `symbol`, and compute accrual ratios vectorized:
  ```python
  df_fund = pd.DataFrame.from_dict(fund_map, orient='index')
  net_inc = df_fund['net_income'].fillna(df_fund.get('net_profit', np.nan))
  ocf = df_fund['operating_cash_flow'].fillna(df_fund.get('ocf', df_fund.get('operating_income', 0.0) * 0.9))
  assets = df_fund['total_assets'].fillna(df_fund.get('assets', net_inc.abs() * 10.0 + 1e-5))
  accrual_ratio = (net_inc - ocf) / assets
  ```

---

### 2.3 `EnsembleScoringEngine` (`trading_system/src/ai/ensemble_scorer.py`)

* **Assessment:** Lines 1570–1745 in `combine_predictions()` already implement vectorized NumPy/Pandas operations across strategy score columns in the `merged` DataFrame. Merging strategy scores, applying missingness coverage penalties, isotonic calibration, and executing the 4-tier microstructure cost model (`stt_tax`, `brokerage_fee`, dynamic spread, Kyle/Almgren-Chriss market impact) are fully vectorized.

---

## 3. SQLite Concurrency Protection & `PRAGMA busy_timeout` Audit

### 3.1 Audit Findings across SQLite Connection Sites

| File | Connection Setup | Current `busy_timeout` | Status | Fix Required |
|------|------------------|-----------------------|--------|--------------|
| `trading_system/src/data_layer/indicator_storage.py` (Line 77) | `MarketIndicatorStorage._connect()` | `PRAGMA busy_timeout=5000;` | ⚠️ Non-compliant (5s) | Set `PRAGMA busy_timeout=30000;` |
| `trading_system/src/persistence/database.py` (Lines 430, 441) | `StockPriceDB._get_conn()` & `_init_db()` | `PRAGMA busy_timeout=60000;` | ✅ Compliant (60s) | Standardize to `30000` |
| `trading_system/src/persistence/database.py` (Lines 36, 47, 56) | `_DBConnection` (aiosqlite) | `PRAGMA busy_timeout=60000;` | ✅ Compliant (60s) | Standardize to `30000` |
| `trading_system/src/persistence/unified_db.py` (Line 81) | `UnifiedStorageEngine` | `PRAGMA busy_timeout=60000;` | ✅ Compliant (60s) | Standardize to `30000` |
| `trading_system/src/execution/oms_engine.py` (Lines 34, 119, 213) | `OMSEngine` direct sqlite3.connect | ❌ Missing | 🚨 Crash Risk | Add WAL & `PRAGMA busy_timeout=30000;` |
| `trading_system/src/ai/trading_agent.py` (Lines 112, 282, 560, 587, 635, 697, 714, 730) | `TradingAgent` direct sqlite3.connect | ❌ Missing | 🚨 Crash Risk | Add WAL & `PRAGMA busy_timeout=30000;` |
| `trading_system/src/data_layer/trade_journal.py` (Line 34) | `TradeJournal` direct sqlite3.connect | ❌ Missing | 🚨 Crash Risk | Add WAL & `PRAGMA busy_timeout=30000;` |
| `trading_system/src/execution/slippage_feedback.py` (Line 66) | `SlippageTracker` direct sqlite3.connect | ❌ Missing | 🚨 Crash Risk | Add WAL & `PRAGMA busy_timeout=30000;` |
| `trading_system/src/risk/portfolio_allocator.py` (Line 555) | `PortfolioAllocator` target DB connection | `timeout=5.0` | ⚠️ Non-compliant | Add `PRAGMA busy_timeout=30000;` |
| `trading_system/src/realtime/state_store.py` (Line 39) | `StateStore` direct sqlite3.connect | ❌ Missing | 🚨 Crash Risk | Add WAL & `PRAGMA busy_timeout=30000;` |

### 3.2 Key Database Recommendation
In `MarketIndicatorStorage._connect()` (`indicator_storage.py`:77), `busy_timeout` is set to `5000` ms (5s), which causes `sqlite3.OperationalError: database is locked` during concurrent multi-threaded execution when 20+ threads update indicators simultaneously. Updating this to `PRAGMA busy_timeout=30000;` and enforcing `PRAGMA busy_timeout=30000;` across ALL SQLite helper functions fixes concurrency locks under stress.

---

## 4. Existing Unit Test Inventory & Execution Verification

### 4.1 Test Suites Catalog

1. **Inference Models**:
   * `trading_system/tests/test_ml_ensemble.py`: Tests XGBoost, LightGBM, CatBoost model loading, feature alignment, and prediction.
   * `trading_system/tests/test_lstm_predictor.py`: Tests Strict Causal LSTM 20-day return sequence prediction.
   * `trading_system/tests/test_hpo_and_2d_ensemble.py`: Tests `EnsembleScoringEngine` 2D regime matrix weighting, Optuna hyperparameter tuning, Platt scaling, Gram-Schmidt factor orthogonalization, and HRP asset allocation. (**14/14 PASSED in 2.11s**).
   * `trading_system/tests/test_e2e_consolidated.py`: End-to-end integration test of `OnDevicePredictionModel`, `predict_all`, `_batch_compute_inference_features`, `_predict_regression`, `_predict_surge`, `predict_lead_lag`.

2. **Strategy Engine Scorers**:
   * `trading_system/tests/test_new_strategies.py` & `test_new_5_strategies.py`: Comprehensive test suites for all 31 strategy engines.
   * `trading_system/tests/test_stat_arb.py`: Log price cointegration pair scanning & Z-score mean-reversion signal generation.
   * `trading_system/tests/test_lead_lag_index.py`: 2-Tier leader-follower matrix generation and shift inference.
   * `trading_system/tests/test_rim_valuation.py`: Residual Income Model intrinsic valuation scoring.
   * `trading_system/tests/test_microstructure.py`: Microstructure imbalance scoring & 4-tier friction model.

3. **Database Concurrency & Operations**:
   * `tests/test_database_concurrency.py`: Multi-threaded 20-worker write stress test verifying `StockPriceDB` zero lock errors and lock-free Parquet WAL buffer flushing. (**2/2 PASSED in 0.95s**).
   * `tests/test_empirical_concurrency_m1_2.py`: Stress tests SQLite WAL mode concurrency under process and thread contention.
   * `trading_system/tests/test_database.py`: Tests schema initialization, logging, and retrieval for `TradeLogger`, `AssetHistoryDB`, `AIPredictionDB`, `StockPriceDB`, and `MarketIndicatorStorage`.

---

## 5. Summary of Recommended Actions for Implementer

1. **Vectorization (M2 Implementer)**:
   - Batch LSTM sequence inference in `OnDevicePredictionModel._predict_regression()` (`prediction_model.py`:2319–2338).
   - Refactor `TrendEfficiencyEngine.calculate_scores()` (`trend_efficiency.py`:77–109) to close price matrix vectorization.
   - Refactor `ShortTermReversalEngine.compute_reversal_scores()` (`short_term_reversal.py`:67–100) to matrix Bollinger Band calculations.
   - Refactor `AccrualsQualityEngine.calculate_scores()` (`accruals_quality.py`:81–106) to DataFrame vectorization.
2. **SQLite Concurrency (M2 Implementer)**:
   - Change `PRAGMA busy_timeout=5000` to `PRAGMA busy_timeout=30000` in `MarketIndicatorStorage._connect()` (`indicator_storage.py`:77).
   - Standardize `PRAGMA busy_timeout=30000;` and `PRAGMA journal_mode=WAL;` across bare `sqlite3.connect()` calls in `oms_engine.py`, `trading_agent.py`, `trade_journal.py`, `slippage_feedback.py`, `portfolio_allocator.py`, and `state_store.py`.
