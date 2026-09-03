# Track A Comprehensive Forensic Audit Report: Data Layer & Strategies 1-19
**Project**: Autonomous Multi-Factor Quant Trading System (37-Strategy Pipeline)  
**Track**: Explorer Track A (Data Layer, Persistence, Market Indicators, Filing Lag, & Strategies 1–19)  
**Date**: 2026-09-03  
**Status**: COMPLETE  

---

## Executive Summary

As part of the 37-Strategy Trading System Integrity & Operational Audit, Track A performed a comprehensive code-level and mathematical audit of the data ingestion pipelines, SQLite persistence layer, market indicators, statutory filing lags, and Strategies 1 through 19 (`src/persistence/database.py`, `src/data_layer/indicator_storage.py`, `src/data_layer/earnings_data.py`, `src/data_layer/dart_corp_mapper.py`, `src/ai/prediction_model.py`, `src/ai/lstm_predictor.py`, `src/ai/score_normalizer.py`, and `src/core/strategy_1_to_19`).

The investigation revealed **5 Critical Issues**, **6 High-Priority Issues**, and **6 Medium-Priority Issues** that directly induce lookahead bias, numerical distortions, database truncation, and mathematical breakdown in strategy scoring and portfolio allocation.

### Priority Matrix
| Severity | Count | Key Affected Modules | Impact Summary |
|---|---|---|---|
| **CRITICAL** | 5 | `lstm_predictor.py`, `rim_valuation.py`, `indicator_storage.py`, `earnings_data.py` / `prediction_model.py`, `card_factor.py` | Full-sample normalization lookahead; missing ROE decay exploding intrinsic value; database schema dropping Strategies 32–37; 45d annual filing lag lookahead; inverted OLS VIX sign predicting market crashes as stock surges. |
| **HIGH** | 6 | `supply_chain.py`, `run_pipeline.py` (ARM / CARD / LATR), `prediction_model.py` (Lead-Lag & FX Beta), `database.py` (`DataValidator`), `latr_factor.py` | Forward-fill timezone bug zeroing US returns; consensus data disconnected from ARM; missing sector mapping in CARD; non-US currencies distorted up to 155x; lookahead in outlier price filter. |
| **MEDIUM** | 6 | `database.py` (`StockPriceDB`), `dart_corp_mapper.py`, `event_driven.py`, `arm_factor.py`, `short_term_reversal.py`, `stat_arb.py` | Connection leak in thread pool; cache eviction bug on stale XML; 2,600 synchronous SEC requests; 0.50 score masking missing strategy dropout; 19-bar Wilder's RMA warmup; pair subset percentile boost. |

---

## 1. Critical Priority Issues

### Issue A-CRIT-01: Full-Sample Standardization Lookahead in Strict Causal LSTM
- **Category**: Lookahead Bias / Machine Learning Causality Violation
- **Target File**: `trading_system/src/ai/lstm_predictor.py` (Lines 106–112)
- **[현황 및 문제점]**:
  `LSTMPredictor.prepare_multivariate_sequences()` claims to be a "Strict Causal LSTM" that avoids data leakage. However, in lines 106–112, the sequence generation calculates mean and standard deviation across the **entire multi-year historical series** of each stock:
  ```python
  # lstm_predictor.py lines 106-112
  for sym, df_s in stock_data.items():
      ...
      vals = df_s[feature_cols].values  # Entire historical series up to T
      # Global series mean/std across entire history
      s_mean = np.nanmean(vals, axis=0)
      s_std = np.nanstd(vals, axis=0)
      s_std = np.where(s_std < 1e-6, 1.0, s_std)
      norm_vals = (vals - s_mean) / s_std
  ```
  When computing sequence $t$ (e.g. in 2021), `norm_vals[t]` uses $s\_mean$ and $s\_std$ computed with data all the way through 2025/2026. This leaks future market regimes, price levels, and volatility into past input tensors, creating severe lookahead bias during Walk-Forward cross-validation and extreme train-serve distribution shift.
- **[정량적/공학적 개선 방안]**:
  Replace global series normalization with an expanding window or causal rolling window standardizer (`RollingCausalNormalizer`). For each time step $t$, normalize features using only statistics available up to $t$:
  $$\mu_t = \frac{1}{W} \sum_{k=1}^{W} x_{t-k}, \quad \sigma_t = \sqrt{\frac{1}{W} \sum_{k=1}^{W} (x_{t-k} - \mu_t)^2 + \epsilon}$$
  For inference on day $T$, standardize the sequence window $[T - \text{seq\_len}, T]$ using trailing rolling statistics computed strictly up to $T - \text{seq\_len}$ or trailing 60 days before the prediction window:
  ```python
  # Causal expanding / rolling standardization
  r_mean = df_s[feature_cols].rolling(window=60, min_periods=20).mean().shift(1)
  r_std = df_s[feature_cols].rolling(window=60, min_periods=20).std().shift(1).replace(0, 1.0)
  norm_vals = ((df_s[feature_cols] - r_mean) / r_std).bfill().values
  ```
- **[수정 대상 파일]**: `trading_system/src/ai/lstm_predictor.py`
- **[검증 방안]**: Unit test checking that shifting or altering future rows in `stock_data` does not change the sequence tensor or inference output for past dates.

---

### Issue A-CRIT-02: Finite-Horizon Decaying ROE Never Decays in RIM Valuation Engine
- **Category**: Mathematical Formulation & Quantitative Implementation Bug
- **Target File**: `trading_system/src/core/rim_valuation.py` (Lines 338–359)
- **[현황 및 문제점]**:
  The module docstring (lines 8–14) and Ohlson (1995) specification state:
  $$\text{ROE}_t = r_e + (\text{ROE}_{t-1} - r_e) \times (1 - \text{decay\_rate})$$
  $$\text{BPS}_t = \text{BPS}_{t-1} + \text{NetIncome}_t \times \text{retention\_ratio}$$
  However, in `calculate_intrinsic_value()` (lines 338–359):
  ```python
  current_bps = bps
  current_roe = roe  # Initialized once
  for t in range(1, years + 1):
      if current_bps <= 0.0:
          excess_income = 0.0
          current_bps = 0.0
      else:
          net_income = current_bps * current_roe
          excess_income = current_bps * (current_roe - r_e)
          retention = self.retention_ratio if net_income > 0 else 1.0
          current_bps += net_income * retention
      pv_excess += excess_income / ((1.0 + r_e) ** t)
  # Terminal value calculation uses current_roe:
  tv_excess = (current_bps * (current_roe - r_e) * omega) / max(denom_tv, 1e-4)
  ```
  `current_roe` is **never updated inside the loop**. As a result, ROE remains fixed at the initial year's level for all 8 years and in the terminal perpetuity annuity. A company with 25% ROE compounds its book value at $25\% \times 0.6 = 15\%$ annually for 8 years (growing BPS by $3.06\times$), generating huge phantom excess returns that inflate $V_0$ by $300\% \sim 500\%$.
- **[정량적/공학적 개선 방안]**:
  Update `current_roe` at the end of each iteration of the loop according to the decaying residual income model:
  ```python
  # Correct finite-horizon ROE decay update
  current_roe = r_e + (current_roe - r_e) * (1.0 - eff_decay)
  ```
- **[수정 대상 파일]**: `trading_system/src/core/rim_valuation.py`
- **[검증 방안]**: Assert that for $\text{ROE} = 0.25, r_e = 0.08, \text{eff\_decay} = 0.10$, $\text{calculate\_intrinsic\_value}$ produces an intrinsic value substantially lower than the non-decaying constant ROE case, and that $V_0 \to \text{BPS}$ as $\text{decay\_rate} \to 1.0$.

---

### Issue A-CRIT-03: SQLite Schema Truncation Dropping Strategies 32–37
- **Category**: Data Persistence / Schema Mismatch
- **Target File**: `trading_system/src/data_layer/indicator_storage.py` (Lines 341–395, 483–515, 1206–1260, 1563–1612)
- **[현황 및 문제점]**:
  The SQLite tables `ensemble_predictions` and `ensemble_prediction_history` were only created with columns up to Strategy 31 (`earnings_tone_drift_score`).
  Strategies 32 through 37:
  - Strategy 32: `dual_correction_score`
  - Strategy 33: `index_rebalance_score`
  - Strategy 34: `overnight_gap_score`
  - Strategy 35: `cross_asset_spillover_score`
  - Strategy 36: `supply_chain_gnn_score`
  - Strategy 37: `range_expansion_score`
  are completely absent from the table schema, missing from table migration routines (`_init_db`), and missing from the parameterized `INSERT INTO` queries in `save_ensemble_predictions()` and `save_ensemble_history()`.
  Consequently, all predictions for Strategies 32–37 generated by `run_pipeline.py` are silently dropped during database persistence, breaking historical tracking, post-market backtests, and Deflated Sharpe Ratio validation.
- **[정량적/공학적 개선 방안]**:
  1. Add columns for all 6 missing strategies in `_init_db()` table creation statements.
  2. Implement an automatic `ALTER TABLE ADD COLUMN` migration in `_init_db()` for existing databases.
  3. Expand `save_ensemble_predictions()` and `save_ensemble_history()` SQL statements and parameter bindings to include all 37 strategy scores.
- **[수정 대상 파일]**: `trading_system/src/data_layer/indicator_storage.py`
- **[검증 방안]**: Execute `storage.save_ensemble_predictions(df_with_37_strats)` and query back `SELECT * FROM ensemble_predictions`; assert non-null values for all 37 strategy columns.

---

### Issue A-CRIT-04: Static 45-Day Regulatory Filing Lag Lookahead on Annual Financials
- **Category**: Lookahead Bias / Point-in-Time Accounting Data
- **Target File**: `trading_system/src/ai/prediction_model.py` (Lines 1082–1087) & `trading_system/src/data_layer/indicator_storage.py` (Lines 290–310)
- **[현황 및 문제점]**:
  In `indicator_storage.py`, the `stock_fundamentals` table stores only the fiscal period end date (`date`, e.g. `2024-12-31`), but does NOT store `date_available` (the statutory public disclosure filing date) or `period_type` (quarterly vs. annual).
  When merging fundamentals with prices during training (`prediction_model.py` lines 1082–1087):
  ```python
  lag_days = 45 if is_krx else 40
  fund_df['date_available'] = fund_df['date'] + pd.to_timedelta(lag_days, unit='D')
  ```
  In South Korea (KRX), quarterly reports have a 45-day statutory filing period, but **annual 12-month reports have a 90-day statutory filing deadline (March 31)**. In the US (SEC), 10-K annual reports have a 60-day deadline for large accelerated filers.
  By applying a flat 45-day lag to all records:
  - 2024-12-31 annual audit data is made available on 2025-02-14 in backtesting/training, whereas the actual audit report was filed in late March (e.g. 2025-03-31).
  - This introduces a **45-day lookahead bias on annual financial figures (revenue, net income, ROE, BPS)** across all historical training samples.
- **[정량적/공학적 개선 방안]**:
  1. Alter `stock_fundamentals` schema in `indicator_storage.py` to persist `date_available` and `period_type` calculated by `compute_regulatory_filing_lag()` in `earnings_data.py`.
  2. If `date_available` is null, parse the fiscal quarter:
     $$\text{lag} = \begin{cases} 90 \text{ days} & \text{if Month} = 12 \text{ and KRX} \\ 60 \text{ days} & \text{if Month} = 12 \text{ and US} \\ 45 \text{ days} & \text{if KRX quarterly} \\ 40 \text{ days} & \text{if US 10-Q} \end{cases}$$
- **[수정 대상 파일]**: `trading_system/src/data_layer/indicator_storage.py`, `trading_system/src/data_layer/earnings_data.py`, `trading_system/src/ai/prediction_model.py`
- **[검증 방안]**: Verify that a fundamental row with `date = '2024-12-31'` in KRX has `date_available >= '2025-03-31'`, and cannot be merged with stock prices in February 2025.

---

### Issue A-CRIT-05: Inverted OLS VIX Sign in CARDFactorEngine Predicting Crashes as Surges
- **Category**: Quantitative Sign Reversal / Logic Error
- **Target File**: `trading_system/src/core/card_factor.py` (Line 174)
- **[현황 및 문제점]**:
  In `CARDFactorEngine`, the OLS regression fits:
  $$R_i = \alpha + \beta_{\text{FX}} \text{FX} + \beta_{\text{WTI}} \text{WTI} + \beta_{\text{VIX}} \text{VIX}$$
  Empirically, when market volatility rises, equities fall, so $\beta_{\text{VIX}}$ is estimated as a negative coefficient (e.g. $-0.45$).
  In line 174, when computing predicted macro impact:
  ```python
  # card_factor.py line 174
  macro_impact = (
      model.params.get('FX', 0.0) * usdkrw_chg
      + model.params.get('WTI', 0.0) * wti_chg
      - model.params.get('VIX', 0.0) * vix_pct_shock  # <-- DOUBLE NEGATIVE ERROR!
  )
  ```
  The author subtracted `model.params['VIX'] * vix_pct_shock` instead of adding it. Since `model.params['VIX']` is already negative, this results in:
  $$- (-0.45) \times (+10\%) = +4.5\%$$
  During a volatility spike (VIX surges by 10%), the model calculates that the stock should have **gained +4.5%**!
  Then, `divergence = stock_ret - macro_impact`:
  If the stock fell $-4.5\%$, `divergence = -4.5% - (+4.5%) = -9.0\%`.
  The model interprets this as an extreme undervaluation divergence (thinking the stock lagged a macro boom) and triggers high contrarian buy signals on collapsing stocks!
- **[정량적/공학적 개선 방안]**:
  Fix the sign in line 174:
  ```python
  macro_impact = (
      model.params.get('FX', 0.0) * usdkrw_chg
      + model.params.get('WTI', 0.0) * wti_chg
      + model.params.get('VIX', 0.0) * vix_pct_shock  # Standard OLS prediction summation
  )
  ```
- **[수정 대상 파일]**: `trading_system/src/core/card_factor.py`
- **[검증 방안]**: Unit test where $R$ and $\text{VIX}$ are negatively correlated. With positive `vix_pct_shock`, verify that `macro_impact` is negative.

---

## 2. High Priority Issues

### Issue A-HIGH-01: Timezone Forward-Fill Zero-Return Bug in SupplyChainEngine
- **Category**: Asynchronous Multi-Market Timezone Flaw
- **Target File**: `trading_system/src/core/supply_chain.py` (Lines 248–254)
- **[현황 및 문제점]**:
  `SupplyChainEngine` builds a wide matrix of closes across all global symbols and fills missing values using `close_pivot.ffill()`.
  When the pipeline executes post-market in Korea (16:00 KST, date $T$):
  - Korean stocks have closed for trading day $T$.
  - US markets have NOT yet opened for trading day $T$ (they open at 22:30 KST).
  - The latest row for US stocks (NVDA, AAPL, TSLA, MSFT) is date $T-1$.
  When `close_pivot.ffill()` runs, row $T$ for US stocks is filled with row $T-1$'s closing price.
  Then in line 251:
  ```python
  returns_1d = close_pivot_filled.pct_change(1).iloc[-1]
  ```
  Because row $T$ equals row $T-1$ for US stocks, `returns_1d` evaluates to **0.0000% for every single US customer stock**!
  Korean suppliers (Samsung Electronics, SK Hynix, Hanmi Semiconductor, LG Energy Solution) receive 0.0% spillover returns from their primary US customers on every Korean trading run.
- **[정량적/공학적 개선 방안]**:
  Compute return series individually for each symbol on its own valid trading dates before aligning:
  ```python
  # Per-symbol return computation preserving latest active trading day
  latest_1d_rets = {}
  latest_3d_rets = {}
  for sym, df_p in df_prices.items():
      c = df_p['Close'].dropna()
      if len(c) >= 2:
          latest_1d_rets[sym] = float(c.iloc[-1] / c.iloc[-2] - 1.0)
      if len(c) >= 4:
          latest_3d_rets[sym] = float(c.iloc[-1] / c.iloc[-4] - 1.0)
  ```
- **[수정 대상 파일]**: `trading_system/src/core/supply_chain.py`
- **[검증 방안]**: Mock an input where US stocks have dates up to $T-1$ with $+5\%$ return, and KRX stocks have dates up to $T$. Assert that `SupplyChainEngine` reads $+5\%$ for the US leader, not $0\%$.

---

### Issue A-HIGH-02: Missing Consensus Feed & Target Price Data in ARMFactorEngine
- **Category**: Strategy Parameter Disconnect / Feature Deprivation
- **Target File**: `trading_system/run_pipeline.py` (Lines 3100–3121, 3148–3153)
- **[현황 및 문제점]**:
  `ARMFactorEngine` was engineered to score analyst revisions (EPS estimate changes, target price revisions, earnings surprises).
  However, in `run_pipeline.py`:
  ```python
  _arm_fund[_sym] = {
      'eps_revision_pct': None,
      'tp_revision_pct': None,
      'eps_growth': _eps_g,
      'revenue_growth': _rev_g,
      'per': None,
  }
  ```
  `run_pipeline.py` hardcodes `eps_revision_pct: None` and `tp_revision_pct: None`.
  Consequently, `ARMFactorEngine` never receives real consensus upgrade data. It falls back to historical trailing `eps_growth` from backward-looking financial statements, or returns `0.50` for stocks lacking 2 consecutive quarters of data, turning a forward-looking consensus momentum strategy into a crippled trailing growth metric.
- **[정량적/공학적 개선 방안]**:
  Connect consensus revision data from Yahoo Finance / OpenDART consensus endpoints in `earnings_data.py` into `_arm_fund`, or derive revision proxies from analyst price targets (`targetMeanPrice` vs. current price from `yf.Ticker.info`).
- **[수정 대상 파일]**: `trading_system/run_pipeline.py`, `trading_system/src/data_layer/earnings_data.py`
- **[검증 방안]**: Verify that `_arm_fund` populates `eps_revision_pct` or `tp_revision_pct` for major stocks (e.g. 005930, AAPL), and that `ARMFactorEngine` outputs varied scores rather than flat fallback values.

---

### Issue A-HIGH-03: Missing Sector Map Argument in CARDFactorEngine Invocation
- **Category**: Pipeline Integration Oversight
- **Target File**: `trading_system/run_pipeline.py` (Line 3157) & `trading_system/src/core/card_factor.py` (Lines 140–188)
- **[현황 및 문제점]**:
  `CARDFactorEngine` relies heavily on `sector_map` to assign specific commodity/FX/volatility weights:
  - Energy: 60% WTI, 20% FX, 20% VIX
  - Tech/Semiconductor: 45% FX, 40% VIX, 15% WTI
  - Utilities/Defensive: 60% VIX, 20% FX, 20% WTI
  However, in `run_pipeline.py` line 3157:
  ```python
  res = CARDFactorEngine().compute_scores(
      prices_dict=infer_data_dict,
      indicators_df=indicator_infer if 'indicator_infer' in locals() else pd.DataFrame()
  )
  ```
  `sector_map=sector_mapping` is **completely omitted**!
  Because `sector_map` is empty, `card_factor.py` assigns `sec = 'Market'` to 100% of symbols in the universe, using a generic `w_fx=0.35, w_wti=0.35, w_vix=0.30`. All specialized macro sensitivities for energy, tech, and utility sectors are completely neutralized.
- **[정량적/공학적 개선 방안]**:
  Pass `sector_map=sector_mapping` to `compute_scores`:
  ```python
  res = CARDFactorEngine().compute_scores(
      prices_dict=infer_data_dict,
      indicators_df=indicator_infer if 'indicator_infer' in locals() else pd.DataFrame(),
      sector_map=sector_mapping
  )
  ```
- **[수정 대상 파일]**: `trading_system/run_pipeline.py`
- **[검증 방안]**: Check that an energy stock (e.g. XOM, 010950) receives WTI weight 0.60, while a tech stock (e.g. NVDA, 005930) receives FX/VIX weights when called from `run_pipeline.py`.

---

### Issue A-HIGH-04: Non-US Currency Scale Distortion in PredictionModel & LATRFactorEngine
- **Category**: Currency Conversion & Scale Invariance Bug
- **Target File**: `trading_system/src/ai/prediction_model.py` (Line 1396) & `trading_system/src/core/latr_factor.py` (Lines 120–124)
- **[현황 및 문제점]**:
  Both modules use a binary check:
  ```python
  # prediction_model.py line 1396
  fx_conv = 1350.0 if is_krx_symbol else 1.0

  # latr_factor.py line 120-121
  is_kr = str(sym).isdigit() or str(sym).endswith(('.KS', '.KQ'))
  fx_norm = usdkrw_rate if is_kr else 1.0
  turnover_usd = (vol.tail(20) * close.tail(20) / fx_norm)
  ```
  This hardcodes the assumption that any stock that is not KRX trades in USD.
  For international markets supported by the trading system:
  - **Japan (TSE)**: Prices are in JPY ($\approx 155$ JPY per USD). Dividing by $1.0$ inflates turnover by $155\times$, causing Amihud illiquidity to be **deflated by 155x**!
  - **Taiwan (TWSE)**: Prices in TWD ($\approx 32$ TWD per USD), deflated by $32\times$.
  - **Brazil (B3)**: Prices in BRL ($\approx 5.5$ BRL per USD).
  - Furthermore, for KRX, `1350.0` is hardcoded even when the actual exchange rate moves to 1400 or 1250.
- **[정량적/공학적 개선 방안]**:
  Use a market-aware FX dictionary dynamically fetched from `indicators_df` (e.g. `usdjpy`, `usdkrw`, `usdtwd`, `eurusd`), defaulting to actual historical FX rather than a binary switch.
- **[수정 대상 파일]**: `trading_system/src/ai/prediction_model.py`, `trading_system/src/core/latr_factor.py`
- **[검증 방안]**: Verify that a Japanese stock with $10,000$ JPY price and $1,000$ shares volume calculates $\approx \$64,500$ USD turnover, not $\$10,000,000$.

---

### Issue A-HIGH-05: Lookahead in DataValidator Transient Price Spike Cleaning
- **Category**: Lookahead Bias in Data Cleansing
- **Target File**: `trading_system/src/persistence/database.py` (Lines 448–460)
- **[현황 및 문제점]**:
  In `DataValidator.validate_and_clean_price_series()`:
  ```python
  # database.py line 452
  fwd_pct = df['Close'].pct_change(-1).abs()
  rev_pct = df['Close'].pct_change(1).abs()
  spike_mask = (rev_pct > 0.40) & (fwd_pct > 0.40)
  ```
  `pct_change(-1)` references row $t+1$ (tomorrow's closing price).
  If used during offline historical data cleaning, this is standard spike detection. But if invoked on live inference streaming or online bar updates, row $t$ cannot observe row $t+1$. More importantly, running this over an entire historical series retroactively modifies past prices using future prices, corrupting backtest point-in-time realism.
- **[정량적/공학적 개선 방안]**:
  Guard with a strict `is_historical_cleaning: bool = False` flag. During live or walk-forward inference, replace future-looking spike detection with a causal rolling median/IQR filter:
  $$\text{Deviation}_t = \frac{|P_t - \text{Median}(P_{t-5:t-1})|}{\text{IQR}(P_{t-5:t-1})}$$
- **[수정 대상 파일]**: `trading_system/src/persistence/database.py`
- **[검증 방안]**: Test that for any bar $t$, cleaning output does not change if $P_{t+1}$ is modified.

---

### Issue A-HIGH-06: Asymmetric Lead-Lag Lag Shift Between S&P 500 and US Sector ETFs
- **Category**: Synchronization / Lead-Lag Lookahead Hazard
- **Target File**: `trading_system/src/ai/prediction_model.py` (Lines 3168–3174)
- **[현황 및 문제점]**:
  In `compute_lead_lag()`:
  ```python
  for col in us_etfs:
      if col in df_lead.columns:
          df_lead[col] = df_lead[col].shift(1)  # Shift US Sector ETFs by 1 day
  ```
  However, `sp500_change` (`^GSPC`) and `nasdaq_change` (`^IXIC`) in `df_lead` are **NOT shifted by 1 day**!
  Both S&P 500 and Sector ETFs (XLK, XLF, XLE) trade during identical US market hours (09:30–16:00 EST).
  Shifting XLK by 1 day while leaving ^GSPC unshifted means that on Korean day $T$, the Lead-Lag model correlates Korean stocks with today's $T$ S&P 500 (which may not have closed yet or is contemporaneous) but yesterday's $T-1$ sector ETF!
- **[정량적/공학적 개선 방안]**:
  Apply consistent shift logic across all US-originated market instruments trading in the US time zone:
  ```python
  us_origin_cols = [c for c in df_lead.columns if c in self.US_ORIGIN_INDICATOR_COLS or c in us_etfs]
  for col in us_origin_cols:
      df_lead[col] = df_lead[col].shift(1)
  ```
- **[수정 대상 파일]**: `trading_system/src/ai/prediction_model.py`
- **[검증 방안]**: Verify that S&P 500 and XLK share the identical lag alignment relative to KRX trading dates.

---

## 3. Medium Priority Issues

### Issue A-MED-01: Thread Pool Connection Leak in StockPriceDB
- **Category**: Resource Management / Concurrency Hazard
- **Target File**: `trading_system/src/persistence/database.py` (Lines 550–575)
- **[현황 및 문제점]**:
  `StockPriceDB` maintains a set `self._all_conns = set()` to track active SQLite connections across threads. When worker threads in a `ThreadPoolExecutor` terminate, their thread-local connection remains in `self._all_conns`. Under heavy multi-factor pipeline runs, orphaned SQLite connection handles accumulate, exhausting OS file descriptors.
- **[정량적/공학적 개선 방안]**: Use a `weakref.WeakSet()` for `self._all_conns`, or register explicit connection close handlers on thread teardown.

---

### Issue A-MED-02: Silent Cache Eviction Bug in DARTCorpMapper
- **Category**: Cache Invalidation & Network Resilience
- **Target File**: `trading_system/src/data_layer/dart_corp_mapper.py` (Lines 80–108)
- **[현황 및 문제점]**:
  When the local XML cache file exceeds 7 days, `DARTCorpMapper` calls `_download_corp_codes()`. If network connection fails or DART API key is unset, `_mapping` is reset to `{}` rather than keeping the expired cache. All DART corp code lookups fail silently for the remainder of the run.
- **[정량적/공학적 개선 방안]**: Retain the stale cache in memory and log a warning if download fails, ensuring zero interruption to KRX disclosure matching.

---

### Issue A-MED-03: Catastrophic SEC Rate-Limit Hazard in EventDrivenEngine
- **Category**: API Rate Limiting / DoS Vulnerability
- **Target File**: `trading_system/src/core/event_driven.py` (Lines 173–175, 91–120)
- **[현황 및 문제점]**:
  If `compute_event_scores` is invoked with `filings=None` (default standalone call), lines 173–175 iterate through all US symbols (up to 2,600 symbols) and issue synchronous HTTP requests to SEC EDGAR with a 5-second timeout. SEC EDGAR strictly bans IPs exceeding 10 requests per second.
- **[정량적/공학적 개선 방안]**: Fetch SEC 8-K filings once in bulk via the SEC daily RSS feed or company tickers JSON, rather than issuing 2,600 serial requests.

---

### Issue A-MED-04: ARMFactorEngine Missing Data Masked as 0.50
- **Category**: Ensemble Strategy Dropout Masking
- **Target File**: `trading_system/src/core/arm_factor.py` (Lines 87–90)
- **[현황 및 문제점]**:
  When consensus revision data is unavailable for a symbol, `arm_factor.py` assigns `raw_scores[sym] = 0.50` instead of `np.nan`.
  The `EnsembleScoringEngine` uses `isna()` to detect missing strategies and zero-out their weights. By outputting `0.50`, the ARM factor pretends to have valid signal coverage, diluting high-conviction alpha signals with uninformative 0.50 scores.
- **[정량적/공학적 개선 방안]**: Return `np.nan` for symbols without consensus coverage to let the dynamic ensemble renormalize weights among active strategies.

---

### Issue A-MED-05: Truncated 19-Bar Wilder's RMA in ShortTermReversalEngine
- **Category**: Numerical Precision in Technical Indicators
- **Target File**: `trading_system/src/core/short_term_reversal.py` (Lines 88, 145–160)
- **[현황 및 문제점]**:
  `close_2d` is sliced to `tail(20)`, leaving only 19 differential bars for `ewm(alpha=1/14)` Wilder's smoothing. Wilder's exponential smoothing requires at least 50–100 bars to converge to steady-state precision, causing RSI-14 to exhibit substantial discretization error.
- **[정량적/공학적 개선 방안]**: Slice trailing 80 bars for indicator calculation before taking the final row for scoring.

---

### Issue A-MED-06: Pair Subset Percentile Rank Distortion in StatisticalArbitrageEngine
- **Category**: Cross-Sectional Score Distortion
- **Target File**: `trading_system/src/core/stat_arb.py` (Lines 747–753, 784–792)
- **[현황 및 문제점]**:
  `get_symbol_stat_arb_scores` computes percentile ranks and multi-tier boosts (1.15x for top 5%) only on symbols that formed cointegrated pairs, before merging with the 2,000 neutral universe symbols (0.50). If only 2 symbols have cointegrated pairs, the higher one is automatically treated as the 100th percentile and boosted by 1.15x regardless of signal strength.
- **[정량적/공학적 개선 방안]**: Populate universe neutral scores (0.50) before computing cross-sectional ranks and boosts.

---

## 4. Implementation & Verification Roadmap

| Phase | Priority | Target Modules | Primary Deliverable |
|---|---|---|---|
| **Phase 1** | Critical Fixes | `lstm_predictor.py`, `rim_valuation.py`, `card_factor.py` | Eliminate lookahead, restore ROE decay math, fix OLS VIX prediction sign |
| **Phase 2** | Persistence & Integrations | `indicator_storage.py`, `supply_chain.py`, `run_pipeline.py` | Add SQLite columns for Strategies 32–37, fix US timezone forward-fill, connect sector_map and indicators |
| **Phase 3** | Data Ingestion & Scales | `indicator_storage.py`, `earnings_data.py`, `prediction_model.py`, `latr_factor.py` | Persist statutory filing dates (90d annual lag), implement multi-currency FX normalization |
| **Phase 4** | Refinements | `database.py`, `dart_corp_mapper.py`, `event_driven.py`, `arm_factor.py`, `short_term_reversal.py`, `stat_arb.py` | Weakref connections, stale cache fallback, bulk 8-K parsing, NaN missing signal dropout |
