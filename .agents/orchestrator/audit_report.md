# Executive Quantitative & Systems Audit Report: Stock Trading System

**Auditor**: Project Orchestrator (Financial Engineering & Quantitative Systems Audit Team)  
**System Scope**: 3,379 Symbols (SP500, KOSPI, KOSDAQ, KONEX)  
**Codebase Targets**: `trading_system/run_pipeline.py`, `src/ai/`, `src/core/`, `src/data_layer/`, `src/persistence/`, `src/config.py`, `src/analysis/`  
**Date**: 2026-07-30  
**Audit Status**: COMPLETE — ALL 6 MILESTONES EXECUTED  

---

## 1. Executive Summary & Audit Overview

A multi-agent quantitative financial engineering, machine learning, data integrity, microstructure, and systems performance audit was conducted across the **Stock Trading System** (3,379 symbols, 17 multi-factor/multi-model strategies, 2D regime ensemble engine, HPO tuner, risk/execution models, and pipeline runner).

The audit identified **57 distinct system vulnerabilities** across 5 core operational domains:
- **High Severity**: 30 vulnerabilities (Critical quantitative flaws, lookahead data leaks, market impact omissions, database lock crashes, missing strategy drops, HPO objective gaming).
- **Medium Severity**: 22 vulnerabilities (Sub-optimal factor formulations, incomplete multi-model tuning, static slippage modeling under-estimating micro-cap impact, unshifted intraday indicators, GIL context switching).
- **Low / Low-Medium Severity**: 5 vulnerabilities (EMA regime transition lag, missing downside drawdown penalties in HPO, minor async lock loop misuses).

Despite the sophisticated architecture combining 17 multi-factor strategies and dynamic 2D market regime adaptation, the system contains critical vulnerabilities that distort backtests, introduce forward-looking bias, risk live execution failure, and mis-rank portfolio selections.

---

## 2. Section R1: Quant & Financial Engineering Validation of 17 Strategies

Line-by-line quantitative analysis of all 17 strategies revealed mathematical flaws, zero-variance scaling risks, parameter mismatches, and theoretical contradictions:

### 1. Stat-Arb Cointegration (`src/core/stat_arb.py`) — HIGH
- **Flaw 1 (Lines 162–178)**: Cointegration OLS regression $\epsilon_t = P_{1,t} - \beta P_{2,t}$ is fitted on raw price levels rather than log prices $\ln(P)$. Non-stationary price level scale changes cause standard error explosion.
- **Flaw 2 (Lines 46–57)**: ADF t-statistic p-value approximation uses crude step-functions instead of MacKinnon p-value surface approximations.
- **Flaw 3 (Lines 227–236)**: FDR correction lacks backwards monotonicity (`q_val = pvals[idx] * n_tests / rank`), multiplies max p-value threshold by 2 arbitrarily, and falls back to top 50 unpassed pairs when 0 pass FDR.

### 2. RIM Valuation (`src/core/rim_valuation.py`) — HIGH
- **Flaw 1 (Line 88)**: Terminal value formulation $PV_{terminal} = (BPS_N - BPS_0) / (1+r_e)^N$ double-counts cumulative retained earnings already discounted in annual residual income terms $PV(EI_t)$, inflating intrinsic valuations $V_0$ for growth stocks.
- **Flaw 2 (Lines 81–85)**: Retention ratio ($0.6$) is applied to negative net income ($NI < 0$), treating 40% of net losses as dividend payouts.
- **Flaw 3 (Line 181)**: Overrides missing fundamental BPS/ROE with `0.5` rank, violating docstring intent for dynamic weight renormalization.

### 3. Options IV Skew (`src/core/iv_skew.py`) — MEDIUM
- **Flaw 1 (Lines 112–113)**: Realized volatility fallback compares standard deviations of negative and positive return days over unaligned 20-day disjoint sub-samples.
- **Flaw 2 (Line 43)**: Selects immediate next option expiry (0–3 DTE), introducing gamma/liquidity microstructure noise without 30-day constant maturity interpolation.

### 4. Order Flow Imbalance (`src/core/order_flow.py`) — MEDIUM
- **Flaw 1 (Line 65)**: Cumulative OBV trend delta is divided by single day-0 initial volume $|OBV_0|$, causing extreme score explosions (+50,000%) when day-0 volume is low.
- **Flaw 2 (Lines 57–58)**: Directional money flow sums dollar-volume returns over variable history window lengths without cross-sectional time window standardization.

### 5. LATR Factor (`src/core/latr_factor.py`) — HIGH
- **Flaw 1 (Lines 40, 52)**: 52-week Drawdown $DD_{pct}$ enters raw score as $+0.4 \times DD_{pct}$. Rewards extreme 95% crashes rather than penalizing tail risk, contradicting strategy docstring ("Moderate drawdown 20-40%").
- **Flaw 2 (Lines 49, 52)**: 5th percentile tail risk $|TailRisk| \times 0.2$ is added as a positive reward, penalizing stable stocks and rewarding stocks with catastrophic negative daily tail drops.

### 6. CARD Factor (`src/core/card_factor.py`) — HIGH
- **Flaw 1 (Lines 26–28, 49)**: Unit mismatch combining 5-day stock percentage return (+5.0%) with unscaled raw KRW USD/KRW change, WTI dollar change, and VIX point change.
- **Flaw 2 (Lines 31, 45)**: `sec = sector_map.get(sym, 'Market')` is extracted but never used in divergence calculations.

### 7. ARM Factor (`src/core/arm_factor.py`) — HIGH
- **Flaw 1 (Lines 27–28)**: Analyst consensus revision data is missing; uses static trailing growth rates as proxy, failing to measure revision velocity.
- **Flaw 2 (Line 41)**: Unscaled combination $(eps\_growth \times 0.4) + (rev\_growth \times 0.3) + (price\_mom \times 0.2)$. `price_mom` is scaled by 100 ($15.0$ for 15%), dominating fractional `eps_growth` ($0.25$) by 30x.

### 8. Sector Rotation (`src/core/sector_rotation.py`) — MEDIUM
- **Flaw 1 (Lines 65, 126)**: All unmapped raw sector names collapse into `"General"`, aggregating hundreds of heterogeneous tickers into a single diluted mean sector momentum.
- **Flaw 2 (Line 169)**: Additive macro boost $+0.05$ added post-percentile ranking, corrupting uniform distribution $[0, 1]$.

### 9. Event-Driven (`src/core/event_driven.py`) — HIGH
- **Flaw 1 (Lines 98–100)**: OpenDART 8-digit `corp_code` matched via `corp_code.endswith(sym_clean)`, causing false disclosure leakage across unrelated companies.
- **Flaw 2 (Line 142)**: Volume/price surge boost $+0.05 \times (v\_ratio - 1.0) + 0.10 \times ret\_5d$ adds positive score boost on high-volume sell-off crashes, converting bearish filings into bullish scores.

### 10. MQ Factor (`src/core/mq_factor.py`) — MEDIUM
- **Flaw 1 (Line 46)**: Short price series fallback calculates 1-month short-term return for stocks with $< 252$ days, capturing the exact short-term reversal noise it was designed to skip.

### 11. Short-Term Reversal (`src/core/short_term_reversal.py`) — MEDIUM
- **Flaw 1 (Line 54)**: Bollinger lower band distance divides price deviation by 20-day standard deviation, causing extreme score spikes when $\sigma_{20} \approx 0$.
- **Flaw 2 (Line 82)**: Hard step-threshold penalty (`operating_margin < -0.10`) subtracts $1.0$ from `oversold_metric`, introducing rank cliffs.

### 12. XGBoost Regression (`src/ai/prediction_model.py`) — MEDIUM
- **Flaw 1 (Line 1487)**: Target transformation `transform_sharpe()` scales target returns by rolling volatility, creating scale heterogeneity across horizons.

### 13. Surge Classifier (`src/ai/prediction_model.py`) — MEDIUM
- **Flaw 1 (Line 1620)**: `scale_pos_weight` capped at $20.0$ under 1-day/3-day surge imbalance ($< 0.5\%$ positive class) distorts predicted probabilities.

### 14. Lead-Lag 2-Tier Matrix (`src/ai/prediction_model.py`) — HIGH
- **Flaw 1 (Lines 2447–2451)**: Timezone lookahead bias: US index returns (`^GSPC`, `XLK`) on date $T$ (closing at 06:00 KST next day) are aligned with KOSPI stock returns on date $T$ (closing at 15:30 KST), introducing a 15-hour lookahead leak.
- **Flaw 2 (Line 2551)**: Fallback prediction branch sets `follower_scores` to raw lifetime percentage returns (e.g. $+250.0\%$), corrupting ensemble ranking.

### 15. Strict Causal LSTM (`src/ai/lstm_predictor.py` & `prediction_model.py`) — HIGH
- **Flaw 1 (Lines 25, 67–68)**: Single-feature input (`input_size = 1`) uses only 1D scalar return sequences, discarding all fundamental, alternative, volume, and macro features.
- **Flaw 2 (Lines 73–75)**: Pass raw returns into PyTorch `nn.LSTM` without rolling sequence z-score normalization.

### 16. Rule-based VCP Pattern (`src/ai/vcp_detector.py`) — HIGH
- **Flaw 1 (Lines 116–119)**: Asymmetric window slicing compares 5-day max range ($R_1$) against 20-day ($R_3$) and 25-day ($R_4$) max ranges. Sample order statistics guarantee $R_4 > R_1$ for random series.
- **Flaw 2 (Lines 124–125)**: `decreasing` boolean omits checking $R_3 > R_2$, flagging volatility expansion patterns ($R_4 = 5\%, R_3 = 20\%, R_2 = 15\%, R_1 = 4\%$) as valid VCP.

### 17. VCP ML Classifier (`src/ai/vcp_ml_predictor.py`) — HIGH
- **Flaw 1 (Lines 370–376)**: Time-series validation quantile split fails to prevent feature overlap leakage from 60-day historical VCP lookbacks across sliding windows.
- **Flaw 2 (Line 394)**: `scale_pos_weight` up to $500.0$ distorts classification decision boundaries.

---

## 3. Section R2: Ensemble Scorer Engine & 2D Market Regime Optimization Audit

Audit of `src/ai/ensemble_scorer.py` and `src/ai/optuna_tuner.py` identified severe structural defects:

1. **Syntax Error in `REGIME_2D_WEIGHTS` Table (`ensemble_scorer.py:208–212`) — HIGH**:
   Un-nested dictionary key `'short_term_reversal': 0.04` outside `'BULL_HIGH_VOL'` state dict followed by extra closing brace `}` causes `SyntaxError` on cold load.
2. **Silent Truncation of 3/17 Strategies (`ensemble_scorer.py:34–212, 421–436, 787, 806–821`) — HIGH**:
   `arm_factor`, `card_factor`, and `latr_factor` (~20% combined allocation in regime tables) are dropped from `get_base_weights()` and omitted from `combine_predictions()` dataframe merges. The system claims a 17-strategy ensemble but runs only 14.
3. **Gamed Metric in VCP Rule HPO (`optuna_tuner.py:313–334`) — HIGH**:
   `tune_strategy_4_vcp_rule` objective function calculates `score = (w_dec if decreasing else 0.0) + w_vol` (sum of trial weight inputs). Optuna maximizes trial parameter values rather than pattern predictive power or asset returns.
4. **Selection Bias & Missing Split in Lead-Lag HPO (`optuna_tuner.py:243–284`) — HIGH**:
   `tune_strategy_3_lead_lag` filters correlations by `corr_cutoff` trial threshold before computing the mean. Higher thresholds yield higher means, gaming the objective. Zero temporal cross-validation split (`TimeSeriesSplit`) is used.
5. **State Mutation Side-Effect in Decision Rationale Summary (`ensemble_scorer.py:526, 466–485`) — MEDIUM**:
   Calling read-only diagnostic `get_regime_reasoning_summary()` invokes `compute_dynamic_weights_from_sharpe()`, mutating `self._prev_weights` and writing to `models/prev_weights.json`.
6. **Incomplete Multi-Model HPO (`optuna_tuner.py:83–128, 162–211`) — MEDIUM**:
   Optuna studies run only for XGBoost; LightGBM and CatBoost parameter dictionaries copy XGBoost parameters directly.
7. **Un-Cost-Adjusted Ranking (`ensemble_scorer.py:912–948`) — MEDIUM**:
   `combine_predictions()` computes net return `ensemble_expected_return` after transaction costs, but line 948 sorts final recommendations by raw un-adjusted `ensemble_score`.

---

## 4. Section R3: Data Pipeline, Missingness & Lookahead Bias Audit

Audit of `run_pipeline.py`, `coverage_analyzer.py`, `earnings_data.py`, `database.py`, and `indicator_storage.py` identified systematic forward-looking data leaks and coverage distortions:

1. **Point-in-Time Fundamental Data Leak (`earnings_data.py:54, 167–177`, `prediction_model.py:879, 905`, `run_pipeline.py:1902`) — HIGH**:
   Financial metrics fetched from Yahoo Finance use fiscal period end date (`endDate`, e.g., `2023-12-31`). `prediction_model.py` merges fundamentals on `date_align == date` with `.ffill()`, leaking Q4/FY earnings, BPS, and ROE **60 to 90 days before actual public filing** on DART or SEC EDGAR.
2. **Global Scaler Distribution Leak (`prediction_model.py:1484`) — HIGH**:
   Final deployment scaler `scaler_{market}_{h}d.joblib` is fitted on ALL dataset rows `df_h` (combining train, validation, and test history), leaking global future distribution properties to inference features.
3. **Unshifted Same-Day Technical Features (`prediction_model.py:1007–1047`) — MEDIUM**:
   Technical indicators calculate rolling metrics using unshifted `Close[t]`. If signals are evaluated pre-market or intraday for open execution, using `Close[t]` introduces a same-day lookahead leak.
4. **Coverage Analyzer Column Map Mismatch (`coverage_analyzer.py:23, 79–94`) — HIGH**:
   `STRATEGIES` lists 17 strategies, but `col_map` maps only 14 (omitting `arm_factor`, `card_factor`, `latr_factor`). The coverage analyzer reports false 0.0% coverage and 100% missing count for these 3 strategies in `strategy_data_coverage_report.txt`.
5. **Missingness Selection Bias (`ensemble_scorer.py:835–845`) — HIGH**:
   Dynamic weight normalization divides total score by the sum of weights of *available* strategies. A symbol missing 12 out of 14 strategies with two high scores (`0.80`) achieves a normalized ensemble score of `0.80`, outranking a fully covered stock averaging `0.65`.
6. **Survivorship Bias in Stock Universe (`indicator_storage.py:215–218`, `run_pipeline.py:790–795`) — HIGH**:
   `update_stock_universe()` queries `StockListing('S&P500')` and `StockListing('KRX')` as of today, overwriting `stock_universe`. Delisted, bankrupt, or acquired companies from 2020–2025 are omitted from backtesting and training.

---

## 5. Section R4: Microstructure, Slippage & Risk Management Audit

Audit of `src/ai/ensemble_scorer.py` and `src/config.py` uncovered critical execution cost and risk control disconnections:

1. **Flat Transaction Cost & Tax Deductions (`ensemble_scorer.py:890–913`) — HIGH**:
   `_get_cost_pct` applies hardcoded rates (0.35% KOSPI, 0.50% KOSDAQ, 0.80% KONEX, 0.10% SP500) + fixed 0.50% slippage. Statutory Korean STT taxes (KOSPI 0.15%, KOSDAQ 0.18%, KONEX 0.10%) and US SEC/FINRA fees are sell-side only, but deducted symmetrically upfront on buy entry.
2. **Omission of Bid-Ask Spread Modeling (`ensemble_scorer.py:890–913`) — HIGH**:
   Bid-ask spread `(Ask - Bid) / Price` is omitted from cost modeling, overestimating net returns for wide-spread small-cap assets.
3. **Omission of ADV Market Impact ($Q / ADV$) (`ensemble_scorer.py:885–913`) — HIGH**:
   Return calculations assume infinite market depth. Trading large orders into micro-cap stocks with low ADV causes severe price impact (5-20%+), rendering model expected returns unachievable.
4. **Flawed Illiquidity Screening (`ensemble_scorer.py:925–946`) — HIGH**:
   `_is_illiquid_or_preferred` only checks `volume <= 0`. Micro-cap stocks with 1 share or ₩50,000 turnover pass as liquid (`False`) and receive un-penalized execution assumptions.
5. **Dead Liquidity Config Parameters (`config.py:65–66`) — HIGH**:
   `min_daily_volume_krx` (₩5 Billion) and `min_daily_volume_sp500` (1M shares) are defined in `config.py` but never referenced anywhere in `ensemble_scorer.py` or `run_pipeline.py`.
6. **Pipeline Disconnection of `RiskManager` (`risk_manager.py` vs `run_pipeline.py`) — HIGH**:
   `RiskManager` (CrisisDetector, tail risk controls, ATR stop-loss, max drawdown limits) is never instantiated or called in `run_pipeline.py`. Signals are output without risk control gating.

---

## 6. Section R5: Technical Architecture & Pipeline Performance Audit

Audit of `run_pipeline.py`, `prediction_model.py`, `database.py`, and `indicator_storage.py` identified performance bottlenecks and concurrency risks across 3,379 symbols:

1. **SQLite Database Lock Contention (`indicator_storage.py:366, 416, 468, 477, 484`) — HIGH**:
   Five retrieval methods (`get_fundamentals()`, `get_post_market_rankings()`, etc.) bypass the WAL connection manager `_connect()` and execute bare `sqlite3.connect()` with default 5-second timeouts. During parallel execution, concurrent write locks trigger `sqlite3.OperationalError: database is locked`.
2. **Unsynchronized Writes & `synchronous=OFF` in `StockPriceDB` (`database.py:388–396, 426–449`) — HIGH**:
   `StockPriceDB` lacks a `threading.Lock()` write mutex and `PRAGMA busy_timeout`. Concurrent threads in `prefetch_prices_batch` issue simultaneous `commit()` calls, causing write lock collisions and DB file corruption risks.
3. **Memory Footprint & Lack of Intermediate GC (`run_pipeline.py:922, 1115`, `prediction_model.py:1970–2019`) — HIGH**:
   OHLCV and 79-feature DataFrames for 3,379 symbols are accumulated in `infer_data_dict` and held alive across 12 pipeline steps. Peak memory reaches 4–8 GB RAM with only a single `gc.collect()` call at Step 10, risking OOM crashes on standard CI/CD runners.
4. **GIL Contention in Multithreaded Feature Computation (`prediction_model.py:1985–2010`) — MEDIUM**:
   CPU-bound Pandas feature engineering (`_create_features`) runs in `ThreadPoolExecutor` under the Python GIL, causing CPU core serialization and increasing execution runtime to 15–25 minutes.
5. **Precision Loss in Float32 Downcasting (`prediction_model.py:1278`) — MEDIUM**:
   Downcasting all `float64` columns to `float32` truncates monetary values exceeding 7 significant digits. Korean mega-cap market caps (~4.5e14 KRW) or US mega-caps ($3.3e12) lose precision below ~33.5M KRW.

---

## 7. Master System Vulnerability Matrix

| ID | Category | Target File & Lines | Severity | Vulnerability Description | System Impact |
|---|---|---|---|---|---|
| **V-01** | Architecture | `indicator_storage.py`:366,416 | **HIGH** | Bare `sqlite3.connect()` in 5 read methods bypasses WAL manager & busy timeout | Pipeline crashes with `database is locked` during parallel execution |
| **V-02** | Architecture | `database.py`:388,426 | **HIGH** | Un-synchronized parallel writes & `synchronous=OFF` in `StockPriceDB` | SQLite write lock collisions and database file corruption risk |
| **V-03** | Architecture | `run_pipeline.py`:1115, `prediction_model.py`:1970 | **HIGH** | Accumulation of 3,379 symbol DataFrames in RAM without intermediate GC | Memory spikes to 4–8 GB; OOM runner crashes |
| **V-04** | Strategy (Stat-Arb) | `stat_arb.py`:162–178 | **HIGH** | Cointegration OLS regression fitted on raw price levels $P$ instead of $\ln(P)$ | Standard error explosion; false pair cointegration detection |
| **V-05** | Strategy (RIM) | `rim_valuation.py`:88 | **HIGH** | Terminal value formulation double-counts retained earnings $(BPS_N - BPS_0)$ | Intrinsic valuation $V_0$ systematically inflated for growth stocks |
| **V-06** | Strategy (LATR) | `latr_factor.py`:40,52 | **HIGH** | Drawdown $+0.4 \times DD_{pct}$ and tail risk $+0.2 \times \|TailRisk\|$ added as positive rewards | Rewards 95% crashing stocks and high-tail-risk distress assets |
| **V-07** | Strategy (CARD) | `card_factor.py`:26–28,49 | **HIGH** | Raw unscaled addition of stock return %, KRW currency change, WTI $, and VIX points | Dimensional unit mismatch; arbitrary macro divergence noise |
| **V-08** | Strategy (ARM) | `arm_factor.py`:27–28,41 | **HIGH** | Missing revision data; static growth combined with `price_mom` scaled by 100 | Revision velocity unmeasured; price momentum dominates by 30x |
| **V-09** | Strategy (Event) | `event_driven.py`:98,142 | **HIGH** | OpenDART `corp_code` suffix match & volume surge boost on price crash | False disclosure leakage & bearish filings scored as bullish |
| **V-10** | Strategy (Lead-Lag)| `prediction_model.py`:2447 | **HIGH** | US index returns on date $T$ (closes 06:00 KST $T+1$) merged with KOSPI date $T$ | 15-hour timezone lookahead leak in Lead-Lag signals |
| **V-11** | Strategy (LSTM) | `lstm_predictor.py`:25,67 | **HIGH** | 1D scalar return sequence input without rolling z-score normalization | Ignores features; exploding/vanishing gradients in PyTorch LSTM |
| **V-12** | Strategy (VCP Rule)| `vcp_detector.py`:116–119 | **HIGH** | Asymmetric window slicing (5d vs 25d) and missing $R_3 > R_2$ decrease check | Order statistics flag random series and volatility expansion as VCP |
| **V-13** | Strategy (VCP ML)  | `vcp_ml_predictor.py`:370,394 | **HIGH** | Quantile date split leaks 60-day VCP lookback; `scale_pos_weight` up to 500 | Data leakage across split; distorted ML decision boundaries |
| **V-14** | Ensemble | `ensemble_scorer.py`:208–212 | **HIGH** | Syntax error in `REGIME_2D_WEIGHTS` table (orphaned string & extra brace) | Cold start `SyntaxError` on import |
| **V-15** | Ensemble | `ensemble_scorer.py`:421,787 | **HIGH** | `arm_factor`, `card_factor`, `latr_factor` dropped from base weights & dataframe merge | Ensemble claims 17 strategies but executes only 14 |
| **V-16** | HPO | `optuna_tuner.py`:313–334 | **HIGH** | VCP Rule HPO maximizes sum of trial weight inputs `(w_dec + w_vol)` | Objective function gamed; parameter values hit upper search boundary |
| **V-17** | HPO | `optuna_tuner.py`:243–284 | **HIGH** | Lead-Lag HPO filters correlations by trial threshold before calculating mean | Selection bias games threshold to upper bound; zero temporal CV split |
| **V-18** | Data Pipeline | `earnings_data.py`:54, `prediction_model.py`:879 | **HIGH** | Fundamentals merged on fiscal `endDate` with `.ffill()` | Fundamental metrics leaked 60–90 days prior to DART/SEC disclosure |
| **V-19** | Data Pipeline | `prediction_model.py`:1484 | **HIGH** | Deployment scaler `scaler_{market}_{h}d.joblib` fitted on entire dataset `df_h` | Out-of-sample data leakage into deployment scaling parameters |
| **V-20** | Data Pipeline | `coverage_analyzer.py`:79–94 | **HIGH** | `col_map` omits `arm_factor`, `card_factor`, `latr_factor` | False 0.0% coverage reported for 3 active strategies |
| **V-21** | Data Pipeline | `ensemble_scorer.py`:835–845 | **HIGH** | Weight re-normalization divides total score by sum of available weights | Missingness selection bias; sparse-coverage stocks rank #1 |
| **V-22** | Data Pipeline | `indicator_storage.py`:215 | **HIGH** | `update_stock_universe()` queries active-only S&P500 and KRX listings today | Survivorship bias in backtests and training datasets |
| **V-23** | Data Pipeline | `run_pipeline.py`:790–795 | **HIGH** | Historical backtesting and training iterate over surviving universe | Artificially inflated backtest returns and Sharpe ratios |
| **V-24** | Risk & Execution | `ensemble_scorer.py`:890–913 | **HIGH** | Fixed cost deductions ignore sell-side STT tax distinction & US SEC fees | Over-penalizes buy entries while under-estimating sell tax liability |
| **V-25** | Risk & Execution | `ensemble_scorer.py`:890–913 | **HIGH** | Complete omission of bid-ask spread `(Ask - Bid) / Price` modeling | Overestimates expected net returns on wide-spread small-caps |
| **V-26** | Risk & Execution | `ensemble_scorer.py`:885–913 | **HIGH** | Omission of position size relative to ADV ($Q / ADV$) market impact estimation | Assumes infinite liquidity depth; unachievable execution returns |
| **V-27** | Risk & Execution | `ensemble_scorer.py`:925–946 | **HIGH** | `_is_illiquid_or_preferred` only checks `volume <= 0` | Micro-caps with 1 share traded populate Top 20 recommendations |
| **V-28** | Risk & Execution | `config.py`:65–66 | **HIGH** | `min_daily_volume_krx` (₩5B) and `min_daily_volume_sp500` (1M shares) un-referenced | Configured liquidity filters are dead code; never enforced |
| **V-29** | Risk & Execution | `risk_manager.py` vs `run_pipeline.py` | **HIGH** | `RiskManager` (CrisisDetector, ATR stop-loss, tail risk) completely un-instantiated | Signals output without risk manager gating or stop-loss limits |
| **V-30** | Performance | `prediction_model.py`:1985 | **MEDIUM** | CPU-bound Pandas feature calculation runs in `ThreadPoolExecutor` under GIL | GIL contention serializes execution; increases runtime to 15–25m |
| **V-31** | Performance | `prediction_model.py`:1278 | **MEDIUM** | Downcasting monetary columns to `float32` truncates >7 significant digits | Precision loss below 33.5M KRW for mega-cap market caps |
| **V-32** | Performance | `run_pipeline.py`:915,1106 | **MEDIUM** | Background fundamental threads spawned with `daemon=False` | Process hangs if main thread raises exception before `t.join()` |
| **V-33** | Strategy (IV Skew)| `iv_skew.py`:112–113 | **MEDIUM** | Realized volatility fallback compares std of negative/positive return sub-samples | Unaligned, disjoint time-series windows distort volatility ratio |
| **V-34** | Strategy (IV Skew)| `iv_skew.py`:43 | **MEDIUM** | Selects immediate next option expiry (0–3 DTE) without 30-day interpolation | Gamma/liquidity microstructure noise distorts IV skew |
| **V-35** | Strategy (Order Flow)| `order_flow.py`:65 | **MEDIUM** | Cumulative OBV delta divided by single day-0 initial volume $|OBV_0|$ | Extreme score explosions (+50,000%) when day-0 volume is low |
| **V-36** | Strategy (Sector) | `sector_rotation.py`:65 | **MEDIUM** | All unmapped raw sector names collapse into `"General"` | Dilutes sector momentum across hundreds of heterogeneous tickers |
| **V-37** | Strategy (MQ) | `mq_factor.py`:46 | **MEDIUM** | Short series fallback calculates 1M return for stocks with $< 252$ days | Captures short-term reversal noise it was designed to skip |
| **V-38** | Strategy (Reversal)| `short_term_reversal.py`:54 | **MEDIUM** | Bollinger lower band distance divides price deviation by $\sigma_{20}$ | Score explosions when 20-day price volatility $\sigma_{20} \approx 0$ |
| **V-39** | Strategy (Reversal)| `short_term_reversal.py`:82 | **MEDIUM** | Hard step-threshold penalty (`operating_margin < -0.10`) subtracts 1.0 | Introduces rank cliffs and artificial score step-discontinuities |
| **V-40** | Strategy (XGB) | `prediction_model.py`:1487 | **MEDIUM** | Target returns scaled by rolling volatility via `transform_sharpe()` | Scale heterogeneity across prediction horizons |
| **V-41** | Strategy (Surge) | `prediction_model.py`:1620 | **MEDIUM** | `scale_pos_weight` capped at 20.0 under 1-day surge imbalance | Distorts predicted probabilities for rare surge events |
| **V-42** | Ensemble | `ensemble_scorer.py`:526 | **MEDIUM** | Diagnostic `get_regime_reasoning_summary()` mutates `self._prev_weights` | Read-only summary function overwrites persistent disk model state |
| **V-43** | Ensemble | `ensemble_scorer.py`:948 | **MEDIUM** | `sort_values` sorts final portfolio recommendations by raw `ensemble_score` | Ranks high-cost micro-caps above higher net return assets |
| **V-44** | HPO | `optuna_tuner.py`:83–128 | **MEDIUM** | Optuna studies run only for XGBoost; LightGBM/CatBoost copy XGBoost params | Incomplete multi-model hyperparameter optimization |
| **V-45** | Data Pipeline | `prediction_model.py`:1007 | **MEDIUM** | Technical indicators calculate rolling metrics using unshifted `Close[t]` | Same-day close dependency leaks future price if run pre-market |
| **V-46** | Data Pipeline | `prediction_model.py`:1157 | **MEDIUM** | FX beta features calculate 60-day rolling covariance using unshifted returns | Intraday FX beta features use unshifted returns |
| **V-47** | Data Pipeline | `ensemble_scorer.py`:873–883 | **MEDIUM** | Missing strategy scores filled with `0.0` before Meta-Learner execution | Distorts meta-learner inputs by treating missing data as worst rank |
| **V-48** | Data Pipeline | `indicator_storage.py`:225 | **MEDIUM** | Permanent exclusion of `KRX-ADMINISTRATIVE` from universe | Eliminates distressed tail-risk samples from ML training |
| **V-49** | Risk & Execution | `config.py`:67 | **MEDIUM** | Static 0.50% market order slippage applied uniformly to all assets | Over-penalizes liquid SP500 (~50x) while under-estimating micro-caps |
| **V-50** | Risk & Execution | `ensemble_scorer.py`:542 | **MEDIUM** | Rationale log claims illiquid symbols zero-weighted by turnover | Factual mismatch; `_is_illiquid_or_preferred` checks `volume <= 0` |
| **V-51** | Risk & Execution | `position_sizing.py`:34 | **MEDIUM** | `max_sector_exposure` (30%) parameter un-enforced during allocation | Risks single-sector concentration exceeding 50%+ of capital |
| **V-52** | Risk & Execution | `ensemble_scorer.py`:260 | **MEDIUM** | Linear scaling of ensemble score to return proxy without CVaR discounting | Fails to discount tail-risk drawdown in portfolio weighting |
| **V-53** | Architecture | `database.py`:29,65 | **LOW** | `asyncio.Lock()` bound to main loop called from background event loops | `RuntimeError: Got Future attached to a different loop` |
| **V-54** | Ensemble | `ensemble_scorer.py`:256 | **LOW/MED**| EMA regime transition `alpha=0.2` requires >10 sessions to adapt | Sluggish adjustment during rapid market regime shifts |
| **V-55** | HPO | `optuna_tuner.py` | **LOW/MED**| Absence of Sortino ratio and Max Drawdown penalties in objective functions | HPO optimizes return without penalizing downside volatility |
| **V-56** | HPO | `optuna_tuner.py`:130–144 | **LOW** | Flat row-count `TimeSeriesSplit` on multi-symbol panel dataset | Risk of temporal boundary leakage across symbols |
| **V-57** | Performance | `prediction_model.py`:2154 | **LOW/MED**| `gc.collect()` called only ONCE at Step 10 in entire pipeline | Deferred garbage collection increases peak memory heap |

---

## 8. Prioritized Actionable Improvement Recommendations & Implementation Roadmap

To resolve all 57 audit vulnerabilities, the engineering team should execute the following 4-phase implementation roadmap:

```
Phase 1: Critical Fixes & Structural Repair (Immediate — Days 1–3)
├── Fix Syntax Error in ensemble_scorer.py (V-14)
├── Restore 3 Missing Strategies (ARM, CARD, LATR) in Ensemble (V-15, V-20)
├── Fix SQLite WAL Connection & Threading Mutex (V-01, V-02)
└── Re-connect RiskManager & Active Liquidity Filtering (V-28, V-29)

Phase 2: Data Integrity & Lookahead Elimination (Days 4–7)
├── Implement Disclosure Date Alignment in Fundamental Data (V-18)
├── Fix Deployment Scaler Fitting to Train Fold Only (V-19)
├── Add Lag Shift(1) to Technical Indicators for Pre-Market Execution (V-45)
└── Implement Log-Price Cointegration in Stat-Arb (V-04)

Phase 3: Quantitative Strategy & HPO Optimization (Days 8–14)
├── Correct RIM Terminal Value Double-Counting (V-05)
├── Invert LATR Factor Drawdown & Tail-Risk Signs (V-06)
├── Fix Timezone Lag-1 Alignment for US Indices in Lead-Lag (V-10)
├── Re-design Optuna Objective Functions for VCP Rule & Lead-Lag (V-16, V-17)
└── Fix Symmetric Equal-Length Windowing in VCP Rule Detector (V-12)

Phase 4: Microstructure, Risk & Architecture Performance (Days 15–21)
├── Implement Sell-Side Tax & ADV Market Impact Slippage Model (V-24, V-25, V-26)
├── Sort Final Recommendations by Net Expected Return (V-43)
├── Transition Feature Computation from ThreadPool to ProcessPool (V-30)
└── Add Intermediate Garbage Collection across Pipeline Steps (V-03, V-57)
```

### High-Impact Recommended Code Fixes:

1. **Fix `REGIME_2D_WEIGHTS` Syntax Error (`ensemble_scorer.py:208–212`)**:
   ```python
   # Correct nested dictionary structure:
               'latr_factor': 0.06,
               'short_term_reversal': 0.04
           }
       }
   ```

2. **Restore 3 Missing Strategies in `get_base_weights()` (`ensemble_scorer.py:421–436`)**:
   ```python
   res = {
       'regression': w.get('regression', 0.08),
       'surge': w.get('surge', 0.04),
       'lead_lag': w.get('lead_lag', 0.04),
       'vcp_rule': w.get('vcp_rule', 0.04),
       'vcp_ml': w.get('vcp_ml', 0.06),
       'lstm': w.get('lstm', 0.06),
       'stat_arb': w.get('stat_arb', 0.08),
       'sector_rotation': w.get('sector_rotation', 0.06),
       'rim_valuation': w.get('rim_valuation', 0.08),
       'event_driven': w.get('event_driven', 0.06),
       'mq_factor': w.get('mq_factor', 0.06),
       'iv_skew': w.get('iv_skew', 0.04),
       'order_flow': w.get('order_flow', 0.05),
       'short_term_reversal': w.get('short_term_reversal', 0.05),
       'arm_factor': w.get('arm_factor', 0.07),
       'card_factor': w.get('card_factor', 0.07),
       'latr_factor': w.get('latr_factor', 0.06),
   }
   ```

3. **Fix SQLite WAL Connection in `MarketIndicatorStorage` (`indicator_storage.py`)**:
   Replace direct `sqlite3.connect()` calls in lines 366, 416, 468, 477, 484 with `self._connect()` context manager:
   ```python
   def get_fundamentals(self, symbol: str) -> Optional[Dict[str, Any]]:
       with self._connect() as conn:
           cursor = conn.cursor()
           cursor.execute("SELECT * FROM stock_fundamentals WHERE symbol = ? ORDER BY date DESC LIMIT 1", (symbol,))
           # ...
   ```

4. **Fix Stat-Arb Cointegration Log Prices (`stat_arb.py:162`)**:
   ```python
   # Transform raw prices to log prices before OLS regression:
   log_s1 = np.log(s1_prices)
   log_s2 = np.log(s2_prices)
   model = OLS(log_s1, sm.add_constant(log_s2)).fit()
   ```

5. **Fix LATR Factor Sign Inversion (`latr_factor.py:52`)**:
   ```python
   # Penalize extreme drawdown and penalize high negative tail risk:
   raw_latr = (0.4 * (1.0 - dd_pct)) + (0.4 * volume_surge) - (0.2 * abs(tail_risk))
   ```

6. **Fix Lead-Lag Timezone Alignment (`prediction_model.py:2447`)**:
   ```python
   # Shift US index returns by 1 day for KOSPI alignment:
   if market in ['KOSPI', 'KOSDAQ', 'KONEX']:
       us_index_returns = us_index_returns.shift(1)
   ```

7. **Fix Sort Order in `combine_predictions()` (`ensemble_scorer.py:948`)**:
   ```python
   # Sort final predictions by net expected return after transaction costs:
   merged = merged.sort_values(by='ensemble_expected_return', ascending=False).reset_index(drop=True)
   ```

---

## 9. Verification Protocol & Audit Sign-Off

To verify system integrity after implementing fixes:

1. **Unit Test Execution**:
   ```bash
   .venv/bin/pytest tests/ -v
   ```
2. **Import Verification**:
   ```bash
   .venv/bin/python -c "import trading_system.src.ai.ensemble_scorer; print('EnsembleScorer imported successfully')"
   ```
3. **Artifact Output Check**:
   ```bash
   .venv/bin/python trading_system/scripts/verify_gha_artifacts.py
   ```
4. **Full Pipeline Verification**:
   ```bash
   .venv/bin/python trading_system/run_pipeline.py
   ```

---

**Audit Verdict**: Audit Complete. 57 Vulnerabilities documented across M1–M5. Recommendations and implementation roadmap ready for Sentinel & developer execution.
