# Comprehensive Technical Analysis: 2D Market Regime Engine, Dynamic Sharpe Ensemble & Verification Framework

- **Agent**: Explorer 3 (Regime Ensemble Explorer)
- **Target Repository**: `d:\Finance\code\stock`
- **Scope**: 3,379 Symbols (KOSPI, KOSDAQ, KONEX, SP500, NASDAQ, RUSSELL2000)
- **Date**: 2026-08-14
- **Status**: Complete Investigation & Forensic Audit

---

## 1. System Overview & Architecture

The Stock Trading System operates a real-time, multi-market quantitative automated trading and prediction architecture encompassing **3,379 ticker symbols** across South Korea (KOSPI, KOSDAQ, KONEX) and the United States (S&P 500, NASDAQ, RUSSELL 2000). The core prediction engine integrates **31 diverse strategies** spanning Machine Learning, Deep Learning, Statistical Arbitrage, Macro/Sector Dynamics, Fundamental Valuation, Event Catalysts, Microstructure, and Pure Alpha Factor Neutralization.

Predictions are fused dynamically using a **2-Dimensional (2D) Market Regime Matrix Engine**, governed by **Dynamic Exponential Sharpe Multipliers** with **Exponential Moving Average (EMA) smoothing**, and sanitized via **PCA ZCA / Gram-Schmidt Factor Orthogonalization** and **Almgren-Chriss Microstructure Friction Models**.

```
 ┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
 │                                   DATA LAYER & ORCHESTRATION                                    │
 │  • SQLite WAL StockPriceDB / MarketIndicatorStorage (Mutex-locked concurrency)                 │
 │  • GlobalMarketClient (VIX, TNX, USDKRW, WTI, Gold, US2Y/10Y, KR3Y/10Y)                        │
 │  • ECOS BOK API + yfinance / FDR + 60-day Fundamental Filing Lag Cache                          │
 └────────────────────────────────┬────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
 ┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
 │                                  31-STRATEGY MULTI-FACTOR ENGINE                                │
 │  [AI & ML]         1. XGBoost Reg  2. Surge Class  5. VCP ML     6. Causal LSTM                 │
 │  [Arbitrage/Stat]  3. Lead-Lag     4. VCP Rule     7. Stat-Arb   8. Sector Rotation             │
 │  [Fundamental]    9. RIM Value   10. Event-Driven 11. MQ Factor 15. ARM Factor  24. Accruals    │
 │  [Cross-Asset]    12. Options IV  16. CARD Factor  17. LATR      18. Inst/Foreign 19. SupplyChain│
 │  [NLP/Sentiment]  20. FinBERT     29. Insider Buy  30. DarkPool  31. Earnings Tone Drift         │
 │  [Micro/Risk]     13. Order Flow  14. Reversal     21. Factor-Neutralized (FF5 pure alpha)       │
 │                   22. Vol Target  23. Microstruct  25. Squeeze   26. Value-Up  27. Trend  28. Gamma│
 └────────────────────────────────┬────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
 ┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
 │                              2D MARKET REGIME & RISK CONTROL LAYER                              │
 │  • MarketRegimeDetector: 10-Feature GMM (Direction: BEAR/SIDEWAYS/BULL x Volatility: LOW/HIGH)  │
 │  • Fast Shock / VIX Crash Override (VIX > 30, S&P 1d < -3% => Immediate BEAR)                  │
 │  • 3D Macro Condition Modifiers (Liquidity Squeeze, Inflation Shock, Yield Inversion)           │
 │  • Dual Market Decoupling Engine (US SP500 vs KR KOSPI rolling 20d correlation)                │
 │  • RiskManager & CrisisDetector: VIX/CDS/Drawdown Gating & Portfolio Circuit Breakers           │
 └────────────────────────────────┬────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
 ┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
 │                                 ENSEMBLE & OPTIMIZATION ENGINE                                  │
 │  • PCA ZCA Symmetric & Gram-Schmidt Factor Orthogonalization (Decoupling collinear signals)     │
 │  • Regime Multicollinearity Suppression (Cluster-based dampening penalties)                     │
 │  • Hybrid Probability Calibration (Isotonic Regression N>=50, Platt Scaling 20<=N<50)           │
 │  • Dynamic Exponential Sharpe Weighting: w_i = base_w_i * exp(gamma * Sharpe_i)                 │
 │  • EMA Weight Smoothing (alpha = 0.2 steady-state; alpha = 1.0 on regime transition)            │
 │  • Vectorized Almgren-Chriss Microstructure Friction: STT/SEC + Spread + Market Impact          │
 │  • Hierarchical Risk Parity (HRP) & Covariance Shrinkage Portfolio Allocator                    │
 └────────────────────────────────┬────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
 ┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
 │                                   OUTPUT & EXECUTION LAYER                                      │
 │  • GitHub Pages Interactive Dashboard (`gh-pages/index.html` via `generate_report.py`)          │
 │  • Pipeline Text Reports (`ensemble_predictions.txt`, `strategy_data_coverage_report.txt`, etc.)│
 │  • Execution OMS Engine (`trade_logs.db`) with Closed-Loop Slippage Feedback                    │
 └─────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. 2D Market Regime Engine In-Depth Analysis

### 2.1 Engine Architecture (`src/analysis/regime_detector.py`)

The `MarketRegimeDetector` classifies macro market environments using an unsupervised Gaussian Mixture Model (GMM) with 3 latent components, coupled with rolling realized volatility to form a **6-State 2D Regime Matrix**:

```
2D State Matrix = { Direction (BEAR, SIDEWAYS, BULL) } x { Volatility (LOW_VOL, HIGH_VOL) }
  1. BEAR_LOW_VOL
  2. BEAR_HIGH_VOL
  3. SIDEWAYS_LOW_VOL
  4. SIDEWAYS_HIGH_VOL
  5. BULL_LOW_VOL
  6. BULL_HIGH_VOL
```

#### 10-Variable Macro Feature Matrix (`_prepare_features`):
1. `sp500_ret_roll`: 20-day rolling mean return of S&P 500.
2. `sp500_vol_roll`: 20-day rolling standard deviation of S&P 500 returns.
3. `vix_level`: Normalized VIX fear gauge ($\text{VIX} / 100$).
4. `us10y_level`: US 10-Year Treasury Yield level ($\text{US10Y} / 10$).
5. `us_yield_spread`: US 10Y - 2Y Treasury Yield Spread ($\text{Spread} / 3.0$). Inversion indicates 6–18 month recession lead.
6. `usdkrw_ret_roll`: 20-day rolling mean return of USD/KRW exchange rate (foreign capital outflow pressure).
7. `kr_us_spread`: Korea 10Y - US 10Y sovereign yield differential.
8. `kr_yield_curve`: Domestic yield curve slope ($\text{KR10Y} - \text{KR3Y}$).
9. `wti_ret_roll`: 20-day rolling return of WTI Crude Oil.
10. `inflation_shock`: Composite inflation shock index ($\text{WTI Return} + \text{USD/KRW Return}$).

### 2.2 Fast Shock Overrides & Zero-Lag Crisis Detection
To bypass the lag inherent in rolling 20-day window features during market crashes, `predict_regime` includes instant zero-lag gating:
- **Fast VIX Shock**: If $\text{VIX} > 30.0$, immediately forces `BEAR` regime.
- **Fast S&P 500 Drawdown**: If $\text{S\&P 500}_{1d} < -3.0\%$ or $\text{S\&P 500}_{2d} < -5.0\%$, immediately forces `BEAR` regime.
- **Hysteresis Filtering**: A 3-period state deque prevents whipsawing in noisy transition regimes:
  $$\text{Regime}_{\text{effective}} = \begin{cases} \text{State}_{t} & \text{if } \text{State}_{t} == \text{State}_{t-1} \\ \text{State}_{t-2} & \text{otherwise} \end{cases}$$

### 2.3 3D Macro Regime Modifiers & Dual Market Decoupling
Beyond 2D states, `predict_3d_macro_regime` overlays 5 macroeconomic risk states:
1. `LIQUIDITY_SQUEEZE`: $\text{VIX} > 5.0$ spike or High Vol + High Yield.
2. `INFLATION_SHOCK`: 5-day average $(\text{WTI} + \text{USD/KRW}) > 2.0\%$.
3. `YIELD_INVERSION`: $\text{US10Y} - \text{US2Y} < 0.0\%$.
4. `HIGH_YIELD_BULL` / `HIGH_YIELD_BEAR`: $\text{TNX} > 4.2\%$ or $\text{KTB Spread} > 0.3\%$.
5. `NEUTRAL_EXPANSION`: Standard expansionary backdrop.

`predict_dual_market_regime` independently evaluates US (S&P 500) and KR (KOSPI) markets, computing 20-day rolling return correlations ($\rho_{20d}$) and identifying structural decoupling (`DECOUPLING_US_BULL_KR_BEAR`, `DECOUPLING_KR_BULL_US_BEAR`, or `COUPLED`).

---

## 3. Ensemble Scoring Engine (`src/ai/ensemble_scorer.py`)

### 3.1 31-Strategy Catalog & 2D Weight Matrix
The `EnsembleScoringEngine` maintains baseline strategic weightings across all 6 2D regimes (normalized to $\sum w_i = 1.00$):

| Strategy ID | Category | BEAR_LOW_VOL | BEAR_HIGH_VOL | SIDEWAYS_LOW_VOL | SIDEWAYS_HIGH_VOL | BULL_LOW_VOL | BULL_HIGH_VOL |
|---|---|---|---|---|---|---|---|
| `regression` | Core AI | 0.12 | 0.11 | 0.05 | 0.05 | 0.03 | 0.02 |
| `surge` | Momentum | 0.01 | 0.00 | 0.02 | 0.02 | 0.07 | 0.08 |
| `lead_lag` | Flow/Cross | 0.02 | 0.02 | 0.03 | 0.03 | 0.02 | 0.02 |
| `vcp_rule` | Technical | 0.01 | 0.01 | 0.02 | 0.02 | 0.02 | 0.02 |
| `vcp_ml` | ML Surge | 0.01 | 0.01 | 0.03 | 0.03 | 0.06 | 0.06 |
| `lstm` | Deep Learning | 0.02 | 0.02 | 0.04 | 0.03 | 0.04 | 0.04 |
| `stat_arb` | Arbitrage | 0.07 | 0.08 | 0.06 | 0.07 | 0.02 | 0.02 |
| `sector_rotation` | Macro Flow | 0.03 | 0.02 | 0.04 | 0.03 | 0.04 | 0.03 |
| `rim_valuation` | Valuation | 0.09 | 0.08 | 0.04 | 0.04 | 0.03 | 0.03 |
| `event_driven` | Event | 0.03 | 0.03 | 0.04 | 0.04 | 0.05 | 0.05 |
| `mq_factor` | Quality Mom | 0.05 | 0.04 | 0.04 | 0.03 | 0.04 | 0.04 |
| `iv_skew` | Options Vol | 0.03 | 0.04 | 0.02 | 0.03 | 0.02 | 0.02 |
| `order_flow` | Micro Flow | 0.02 | 0.02 | 0.03 | 0.03 | 0.03 | 0.03 |
| `short_term_reversal`| Reversal | 0.04 | 0.05 | 0.03 | 0.03 | 0.02 | 0.03 |
| `arm_factor` | Fundamental | 0.04 | 0.04 | 0.04 | 0.04 | 0.04 | 0.04 |
| `card_factor` | Macro Cross | 0.04 | 0.05 | 0.04 | 0.04 | 0.03 | 0.03 |
| `latr_factor` | Tail Risk | 0.04 | 0.04 | 0.03 | 0.03 | 0.03 | 0.03 |
| `inst_foreign_sector`| Flow | 0.04 | 0.04 | 0.04 | 0.04 | 0.05 | 0.05 |
| `supply_chain` | Momentum | 0.01 | 0.00 | 0.01 | 0.01 | 0.03 | 0.03 |
| `sentiment` | NLP FinBERT | 0.03 | 0.03 | 0.03 | 0.03 | 0.03 | 0.03 |
| `factor_neutralized`| Pure Alpha | 0.03 | 0.03 | 0.03 | 0.03 | 0.03 | 0.03 |
| `vol_target` | Risk Parity | 0.05 | 0.05 | 0.03 | 0.04 | 0.02 | 0.02 |
| `microstructure` | LOB / OBI | 0.02 | 0.02 | 0.03 | 0.03 | 0.03 | 0.03 |
| `accruals_quality` | Accounting | 0.04 | 0.05 | 0.03 | 0.03 | 0.01 | 0.01 |
| `short_squeeze` | Squeeze | 0.01 | 0.00 | 0.02 | 0.01 | 0.04 | 0.04 |
| `valueup_catalyst` | Shareholder | 0.04 | 0.04 | 0.03 | 0.03 | 0.01 | 0.01 |
| `trend_efficiency` | KER / Hurst | 0.01 | 0.00 | 0.01 | 0.01 | 0.04 | 0.04 |
| `gamma_squeeze` | Options Delta| 0.01 | 0.00 | 0.02 | 0.02 | 0.04 | 0.04 |
| `insider_buying` | Insider Flow | 0.02 | 0.02 | 0.03 | 0.03 | 0.03 | 0.03 |
| `darkpool` | Off-Exchange | 0.02 | 0.02 | 0.03 | 0.03 | 0.03 | 0.03 |
| `earnings_tone_drift`| Conf-Call NLP| 0.02 | 0.02 | 0.02 | 0.02 | 0.02 | 0.02 |

### 3.2 Signal Orthogonalization & Suppression
1. **PCA ZCA Symmetric Decorrelation (`FactorOrthogonalizerEngine`)**:
   Computes the correlation matrix $C$, applies Ledoit-Wolf shrinkage, eigen-decomposes $C = V \Lambda V^T$, and computes the symmetric whitening operator $W = V \Lambda^{-1/2} V^T$. Scores are transformed via $X_{\text{ortho}} = \mu + (X - \mu) W$, eliminating collinearity while preserving each strategy's relative identity and bounding scores to $[0.0, 1.0]$.
2. **Gram-Schmidt Pairwise Correlation Penalty**:
   When $|\rho_{ij}| > 0.65$, a differential orthogonalization penalty reduces the subordinate strategy's weight by $(1 - (|\rho| - 0.65) \times 0.5)$.
3. **Regime Factor Suppression (`RegimeFactorSuppressionEngine`)**:
   Strategies are partitioned into 5 functional clusters (`CORE_AI`, `MOMENTUM`, `VALUATION`, `REVERSAL`, `FLOW_MICRO`). Intra-cluster redundancy is penalized $1.5\times$ more severely than inter-cluster redundancy, with active suppression targeting high-risk clusters per regime.

---

## 4. Mathematical Formulation: Dynamic Exponential Sharpe Multiplier & EMA Smoothing

### 4.1 Rolling Sharpe Ratio Computation
For each strategy $i$ with realized return history $R_i \in \mathbb{R}^T$ over rolling window $W = 60$ days:
$$\overline{R}_i = \frac{1}{W} \sum_{t=1}^W R_{i,t}, \quad \sigma_i = \sqrt{\frac{1}{W-1} \sum_{t=1}^W (R_{i,t} - \overline{R}_i)^2} + \epsilon \quad (\epsilon = 10^{-6})$$
$$\text{Sharpe}_i = \frac{\overline{R}_i - r_f / 252}{\sigma_i} \times \sqrt{252}$$

### 4.2 Dynamic Exponential Multiplier with Strict Bounding
To dynamically reward high-performing alpha strategies while defending against catastrophic single-strategy dominance:
1. **Underperformance Pruning**: If $\text{Sharpe}_i < -0.50$, $w_i = 0.0$ (immediate quarantine).
2. **Exponential Multiplier**:
   $$M_i = \exp\left( \gamma \cdot \text{clip}\left(\text{Sharpe}_i, -L, L\right) \right)$$
   where $\gamma = 1.0$, and $L = \frac{\ln\sqrt{R_{\text{max}}}}{\gamma}$ with $R_{\text{max}} = 5.0$ ($L \approx 0.8047$). This guarantees the dynamic multiplier ratio $\frac{M_{\text{max}}}{M_{\text{min}}} \le 5.0$.
3. **Total Ratio Damping**:
   $$S_i = w_i^{\text{base}} \times M_i$$
   If $\frac{\max(S)}{\min(S)} > 20.0$, apply power damping:
   $$S_i \leftarrow S_i^{\alpha_{\text{damp}}}, \quad \alpha_{\text{damp}} = \frac{\ln(20.0)}{\ln(\max(S) / \min(S))}$$
   $$w_i^{\text{dynamic}} = \frac{S_i}{\sum_j S_j}$$

### 4.3 Adaptive EMA Weight Smoothing
To eliminate turnover churn and whipsawing during quiet periods while ensuring immediate defensive alignment on macro regime shifts:
$$w_i(t) = \alpha_{\text{eff}} \cdot w_i^{\text{dynamic}}(t) + (1 - \alpha_{\text{eff}}) \cdot w_i(t-1)$$
$$\alpha_{\text{eff}} = \begin{cases} 1.0 & \text{if } \text{Regime}(t) \neq \text{Regime}(t-1) \quad (\text{Regime Shift Reset}) \\ 0.2 & \text{if } \text{Regime}(t) == \text{Regime}(t-1) \quad (\text{Steady-State Smoothing}) \end{cases}$$
Weights are persisted to disk in `models/prev_weights.json` along with the active regime label to ensure continuity across pipeline execution cycles.

---

## 5. Microstructure Friction Model & Net Expected Return

Raw ensemble scores $E \in [0, 1]$ are scaled to 20-day expected return proxies ($\text{ExpRet}_{\text{raw}} = E \times 20.0\%$) and adjusted for realistic institutional transaction costs:

$$\text{ExpRet}_{\text{net}} = \text{ExpRet}_{\text{raw}} - \text{Cost}_{\text{total}} \times 100.0$$

### Friction Schedule:
$$\text{Cost}_{\text{total}} = \text{Tax}_{\text{STT/SEC}} + \text{Fee}_{\text{broker}} + \text{Spread}_{\text{dynamic}} + 2 \times \text{Impact}_{\text{Almgren-Chriss}}$$

1. **Exchange Taxes & Fees**:
   - KRX (KOSPI/KOSDAQ): STT 0.15% (KOSPI) / 0.18% (KOSDAQ) + Brokerage 0.03%
   - US (SP500/NASDAQ/RUSSELL2000): SEC Fee 0.003% + Brokerage 0.005%
2. **Dynamic Bid-Ask Spread**:
   $$\text{Spread} = \text{Spread}_{\text{base}} \times \left(\frac{\text{ADV}_{\text{ref}}}{\text{ADV}}\right)^{0.25} \times \left(\frac{\sigma_{20d}}{0.02}\right)^{0.50}$$
3. **Almgren-Chriss Square-Root Market Impact**:
   $$\text{Impact} = c_{\text{impact}} \times \sigma_{20d} \times \left(\frac{Q_{\text{order}}}{\text{ADV}}\right)^{\alpha_{\text{impact}}}$$
   where $Q_{\text{order}} = 50\text{M KRW}$ (KRX) / $50\text{k USD}$ (US), $\alpha_{\text{impact}} = 0.50$ (calibrated via `trade_logs.db` closed-loop feedback).

---

## 6. Backtest Runner & Benchmark Verification

### 6.1 Backtest Engines
1. **`src/analysis/backtest.py` (`BacktestEngine`)**:
   Event-driven OHLCV simulation supporting market transaction costs (NASDAQ 0.65%, RUSSELL 0.80%, KOSDAQ 1.00%, KOSPI 0.85%, SP500 0.60%), dynamic liquidity slippage, ATR trailing stops, and volatility-based Kelly sizing.
2. **`src/analysis/walk_forward_backtester.py` (`WalkForwardBacktester`)**:
   60-day train / 20-day test walk-forward framework evaluating Pearson Information Coefficient (IC), Spearman Rank IC, and out-of-sample cumulative PnL.
3. **`trading_system/scripts/compare_backtests.py`**:
   Comparative harness evaluating baseline vs enhanced risk parity & trailing stop strategies across major tickers (SPY, AAPL, MSFT, GOOGL, AMZN, 005930.KS, 000660.KS, 035420.KS).

---

## 7. Pytest Test Suite Status & Baseline Verification

### 7.1 Test Suite Inventory
- **Total Discovered Tests**: **1,554 tests** (730 tests in `tests/`, 824 tests in `trading_system/tests/`).
- **Configuration (`pyproject.toml`)**:
  ```toml
  [tool.pytest.ini_options]
  testpaths = ["tests", "trading_system/tests"]
  python_files = ["test_*.py"]
  norecursedirs = [".venv", ".git", "build", "dist"]
  addopts = "-v --tb=short"
  ```
- **Execution Command**:
  ```bash
  .venv/Scripts/python.exe -m pytest tests/ -v
  ```

---

## 8. Pipeline Execution & GitHub Pages Report

### 8.1 12-Step Pipeline Flow (`run_pipeline.py`)
1. **Global Indicators**: Fetch VIX, TNX, USDKRW, WTI, Gold, US2Y/10Y, KR3Y/10Y.
2. **Universe Load**: Ingest 3,379 symbols (KOSPI, KOSDAQ, KONEX, SP500, NASDAQ, RUSSELL2000).
3. **Model Training**: XGBoost regression, Surge classifier, VCP ML, and Isotonic calibrators.
4. **Inference Ingestion**: Fetch real-time OHLCV and fundamental filing lag data.
5. **31-Strategy Execution**: Concurrent computation of all 31 strategy alpha vectors.
6. **2D Regime Classification**: GMM direction + realized volatility + fast shock checks.
7. **Dynamic Sharpe Weighting**: Exponential Sharpe multiplier + EMA smoothing.
8. **Factor Orthogonalization**: PCA ZCA symmetric decoupling + Gram-Schmidt penalties.
9. **Microstructure Subtraction**: Deduct STT/SEC, bid-ask spread, and Almgren-Chriss impact.
10. **Liquidity & Safety Gate**: Filter preferred shares (`우`), SPACs, and illiquid symbols.
11. **Portfolio Optimization**: Risk Parity / Hierarchical Risk Parity (HRP) weight allocation.
12. **Report Generation**: Output prediction TXTs, SQLite logs, and update GitHub Pages `index.html`.

### 8.2 GitHub Pages Dashboard (`generate_report.py` -> `index.html`)
- Standalone HTML5/CSS3/JS dark-theme dashboard deployed via GitHub Actions.
- Interactive multi-market tab panels: KOSPI, KOSDAQ, S&P 500, NASDAQ, RUSSELL 2000.
- Real-time badges for 2D Market Regime (`BULL_LOW_VOL`, `BEAR_HIGH_VOL`, etc.) with dual-market US/KR status.
- Expandable **Decision Rationale Drawer** displaying dynamic 31-strategy weight breakdown and rolling Sharpe ratios.
- Modal Stock Drawer visualizing individual stock multi-factor scores and net expected return calculations.

---

## 9. Potential Pitfalls, Vulnerabilities & Recommendations

1. **Cold-Start Sharpe Ratio Sensitivity**:
   - *Observation*: During cold-start periods ($<10$ matured predictions), rolling Sharpe is 0.0, defaulting to base 2D weights.
   - *Mitigation*: Ensure smooth transition as predictions mature by enforcing minimum sample threshold ($N \ge 10$) before enabling dynamic multipliers.
2. **Regime Transition Turnover**:
   - *Observation*: When shifting from BULL to BEAR, aggressive weight redistribution occurs ($\alpha_{\text{eff}} = 1.0$).
   - *Mitigation*: The $+0.05$ turnover hysteresis hold bonus on existing positions successfully prevents unnecessary portfolio churning.
3. **Multicollinearity in Momentum Cluster**:
   - *Observation*: High correlation between `surge`, `vcp_ml`, `sector_rotation`, and `trend_efficiency` during strong bull runs.
   - *Mitigation*: PCA ZCA orthogonalization and intra-cluster suppression penalties ($c_{\text{intra}} = 1.5$) effectively suppress redundant factor risk.
