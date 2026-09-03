# Track A Handoff Report: 37-Strategy Trading System Integrity & Operational Audit

**Agent Identity**: Explorer Track A  
**Working Directory**: `d:\Finance\code\stock\.agents\explorer_track_a`  
**Target Scope**: Data Ingestion, SQLite Storage, Market Indicators, Statutory Filing Lags, & Strategies 1–19  
**Date**: 2026-09-03  
**Handoff Type**: Hard (Task Complete)  

---

## 1. Observation

### Exact Code & Schema Findings
1. **`trading_system/src/ai/lstm_predictor.py` lines 106–112**:
   `LSTMPredictor.prepare_multivariate_sequences()` computes `s_mean = np.nanmean(vals, axis=0)` and `s_std = np.nanstd(vals, axis=0)` on the full multi-year history of each stock `df_s[feature_cols].values`. Sequence generation normalizes historical time steps using future data.
2. **`trading_system/src/core/rim_valuation.py` lines 338–359**:
   Inside `calculate_intrinsic_value()`, `current_roe = roe` is initialized before the 8-year loop (`for t in range(1, years + 1)`). Inside the loop, `current_roe` is never decayed. It remains constant for all 8 projection years and enters the terminal perpetuity annuity calculation unchanged.
3. **`trading_system/src/data_layer/indicator_storage.py` lines 341–395, 483–515, 1206–1260, 1563–1612**:
   Tables `ensemble_predictions` and `ensemble_prediction_history` end their column list at `earnings_tone_drift_score`. Strategies 32 through 37 (`dual_correction_score`, `index_rebalance_score`, `overnight_gap_score`, `cross_asset_spillover_score`, `supply_chain_gnn_score`, `range_expansion_score`) are missing from table schemas and SQL insert statements.
4. **`trading_system/src/ai/prediction_model.py` lines 1082–1087 & `indicator_storage.py` lines 290–310**:
   `stock_fundamentals` schema stores only fiscal period end `date`. `merge_fundamentals()` assigns `lag_days = 45 if is_krx else 40` to all rows. Annual 12-month reports (legally filed with 90-day statutory deadline in KRX and 60-day in US) receive a 45-day lag, creating a 45-day lookahead bias on annual financial figures.
5. **`trading_system/src/core/card_factor.py` line 174 & `run_pipeline.py` line 3157**:
   In `card_factor.py` line 174, `macro_impact = model.params.get('FX', 0.0) * usdkrw_chg + model.params.get('WTI', 0.0) * wti_chg - model.params.get('VIX', 0.0) * vix_pct_shock`. Subtracting `model.params['VIX']` (which is already negative) causes positive VIX spikes to predict positive stock returns. In `run_pipeline.py` line 3157, `sector_map` is not passed to `CARDFactorEngine`, defaulting all symbols to `'Market'`.
6. **`trading_system/src/core/supply_chain.py` lines 248–254**:
   `close_pivot.ffill()` forward-fills US closing prices into row $T$ (Korea post-market close, when US market has not yet opened). `returns_1d = close_pivot_filled.pct_change(1).iloc[-1]` evaluates to 0.0% for all US leader stocks (NVDA, AAPL, TSLA).
7. **`trading_system/src/ai/prediction_model.py` line 1396 & `latr_factor.py` line 120**:
   `fx_conv = 1350.0 if is_krx_symbol else 1.0` and `fx_norm = usdkrw_rate if is_kr else 1.0` assume all non-KRX stocks trade in USD, distorting Japanese (JPY, 155x) and Taiwanese (TWD, 32x) turnover and block trades.
8. **`trading_system/src/persistence/database.py` line 452**:
   `DataValidator.validate_and_clean_price_series()` uses `df['Close'].pct_change(-1).abs()`, referencing tomorrow's price $t+1$.

---

## 2. Logic Chain

1. **Strict Causal LSTM Lookahead Chain**:
   - `prepare_multivariate_sequences()` receives `stock_data` dictionary.
   - `vals` is extracted from the entire historical slice up to date $T$.
   - `s_mean` and `s_std` are computed using `np.nanmean(vals, axis=0)`.
   - Sequence window $[t - L, t]$ (for $t \ll T$) is scaled by statistics that include data from $(t, T]$.
   - $\therefore$ The model accesses future mean and volatility during training and evaluation, violating strict causality.

2. **RIM Valuation Mathematical Breakdown Chain**:
   - The economic model requires ROE to mean-revert toward the cost of equity $r_e$ over time due to competitive dynamics.
   - In `calculate_intrinsic_value()`, `current_roe` remains fixed at `roe`.
   - High initial ROE (up to 25%) causes BPS to compound at $25\% \times 0.6 = 15\%$ annually for 8 years, increasing book value by $3.06\times$.
   - The residual income $(current\_roe - r_e) \times current\_bps$ grows exponentially rather than decaying.
   - The terminal value calculation continues to use `current_roe` rather than decayed ROE.
   - $\therefore$ Intrinsic value $V_0$ is massively overstated, distorting value rankings.

3. **Database Truncation Chain**:
   - The system was upgraded from 31 to 37 strategies in recent releases.
   - `run_pipeline.py` successfully computes scores for Strategies 32–37.
   - However, `indicator_storage.py` schemas for `ensemble_predictions` and `ensemble_prediction_history` were not updated past Strategy 31.
   - `save_ensemble_predictions()` executes parameterized `INSERT INTO` queries matching the old schema.
   - $\therefore$ Strategies 32–37 scores are omitted from database writes and lost upon pipeline completion.

4. **CARD Factor Sign Inversion Chain**:
   - OLS regression estimates $\Delta R = \alpha + \beta_{FX} \Delta FX + \beta_{WTI} \Delta WTI + \beta_{VIX} \Delta VIX$.
   - When volatility increases, stock prices decrease ($\beta_{VIX} < 0$).
   - `macro_impact` computes $\dots - \beta_{VIX} \times \Delta VIX$.
   - A $+10\%$ VIX jump produces a positive predicted return: $- (-0.45) \times 10\% = +4.5\%$.
   - The actual stock drops $-4.5\%$, yielding a divergence of $-4.5\% - (+4.5\%) = -9.0\%$.
   - $\therefore$ The model perceives severe undervaluation during market crashes and triggers false buy signals.

---

## 3. Caveats

1. **Live vs. Offline Data Execution Context**:
   - Some issues (e.g. `DataValidator` using `pct_change(-1)`) are standard practice when backtesting over immutable historical dumps to eliminate dirty data spikes, but represent unacceptable lookahead bias if invoked on streaming live market updates.
2. **Strategy 10 SEC Scraping Fallback**:
   - `EventDrivenEngine.fetch_recent_sec_filings()` makes serial requests only when `filings` is `None`. In normal `run_pipeline.py` execution, `filings` is populated, bypassing the serial loop. However, standalone invocations or unit tests remain exposed to rate limiting.
3. **Consensus Feed Availability**:
   - Yahoo Finance API does not guarantee free, clean consensus revision percentage fields for all small-cap KRX stocks. A proxy based on target price or quarterly EPS changes may be required as a practical substitute.

---

## 4. Conclusion

The audit identifies **5 Critical, 6 High, and 6 Medium priority defects**. The core algorithmic trading engine possesses sophisticated multi-factor designs (2D regime matrices, Winsorized Gaussian score normalization, and HRP portfolio optimization), but its operational efficacy is severely compromised by:
1. Future information leakage in LSTM sequence standardization and annual financial statement lags.
2. Computational sign errors in the CARD macro factor and missing ROE decay in the RIM model.
3. Data truncation of Strategies 32–37 in the SQLite persistence layer.
4. Asynchronous timezone forward-fill flaws zeroing US customer returns in the Supply Chain factor.

All issues have been traced to exact source files and line numbers with quantitative mathematical formulations and concrete code fixes provided in `audit_report.md`.

---

## 5. Verification Method

1. **Strict Causal LSTM Verification**:
   - Modify future prices in `stock_data` for dates $> t_0$; assert that output tensors from `prepare_multivariate_sequences()` for dates $\le t_0$ remain bitwise identical.
2. **RIM Engine Verification**:
   - Execute:
     ```python
     from src.core.rim_valuation import RIMValuationEngine
     eng = RIMValuationEngine(default_required_return=0.08, decay_rate=0.10)
     v0 = eng.calculate_intrinsic_value(bps=10000, roe=0.25, required_return=0.08, years=8)
     ```
     Verify that $v0$ reflects decayed ROE year-by-year ($ROE_1 = 0.233, ROE_2 = 0.218, \dots$) and matches analytical finite-horizon values ($\approx 21,500$ instead of non-decaying $\approx 45,000$).
3. **Database Schema Verification**:
   - Run `python -c "from src.data_layer.indicator_storage import MarketIndicatorStorage; s = MarketIndicatorStorage(); ..."` and verify that `PRAGMA table_info(ensemble_predictions)` contains columns for all 37 strategies.
4. **CARD Factor Sign Verification**:
   - Execute unit test with synthetic dataset having negative correlation with VIX; assert `macro_impact < 0` when `vix_pct_shock > 0`.
5. **Supply Chain Timezone Verification**:
   - Input mock price data where US stocks end on date $T-1$ and KRX stocks end on date $T$; verify that `SupplyChainEngine` calculates non-zero $1D$ customer return from day $T-1$.
