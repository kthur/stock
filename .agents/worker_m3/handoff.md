# Worker M3 Handoff Report: Next-Generation Quant Alpha Strategies & Phase 1~4 Advanced Roadmap

## 1. Observation

Direct observations from the current quantitative codebase (`trading_system/run_pipeline.py`, `trading_system/src/ai/ensemble_scorer.py`, `trading_system/src/ai/prediction_model.py`, `trading_system/src/risk/portfolio_optimizer.py`, `trading_system/src/execution/oms_engine.py`):

1. **Current System Scale & Architecture**:
   - The trading system manages **3,379 symbols** across 4 markets (`SP500`, `KOSPI`, `KOSDAQ`, `KONEX`).
   - The current dynamic ensemble scoring engine (`EnsembleScoringEngine` in `trading_system/src/ai/ensemble_scorer.py`, lines 29–1153) blends 17 strategies across 1D/2D market regimes.
2. **Current Pipeline Pipeline Sequence (`trading_system/run_pipeline.py`)**:
   - Indicator history fetching (line 41), fundamental data retrieval (`earnings_data.py`), model training for XGBoost Regression, Surge Classifier, Lead-Lag matrix, VCP ML, and factor scoring (Event-Driven, MQ Factor, IV Skew, Order Flow, Short-Term Reversal, ARM, CARD, LATR).
3. **Data & Execution Constraints**:
   - High data dimensionality requires memory downcasting (`float32`), rate-limited fundamental fetching, and robust DB concurrency (`StockPriceDB` in `src/persistence/database.py` and `MarketIndicatorStorage` in `src/data_layer/indicator_storage.py`).
   - Execution cost model in `EnsembleScoringEngine` accounts for transaction tax (STT: 0.18% KOSPI/KOSDAQ, 0.00% US), bid-ask spread, and market impact cost.

---

## 2. Logic Chain

1. **Next-Generation Alpha Imperative**:
   - Standard price/volume factors and quarterly financial ratios experience alpha decay as market efficiency increases.
   - To sustain superior risk-adjusted returns (Sharpe ratio > 2.0), the system must expand into non-linear, high-frequency, and unstructured alpha channels:
     1. *Unstructured Alternative Data*: LLM-driven disclosure and news sentiment (DART & SEC EDGAR).
     2. *Microstructure Data*: Real-time Orderbook Imbalance (OBI) and tick-level order flow dynamics.
     3. *Non-linear Macro Dynamics*: Hidden Markov Models (HMM) for regime switching replacing rigid static threshold matrices.

2. **System Roadmap Alignment (Phase 1 ~ Phase 4)**:
   - *Phase 1 (Integrity Stabilization)* establishes lookahead-free training, mathematically sound factor calculations (Stat-Arb, RIM, LATR), and thread-safe DB operations.
   - *Phase 2 (Portfolio Optimization)* optimizes capital allocation via Risk Parity & Ledoit-Wolf Covariance Shrinkage to maximize diversification benefits.
   - *Phase 3 (Execution Engine & OMS)* minimizes implementation shortfall (slippage) and scales feature computation to handle 3,379 symbols in real-time.
   - *Phase 4 (Next-Gen Alpha & AI)* deploys the three next-gen alpha strategies (LLM, OBI, HMM) into paper and live trading environments.

---

## 3. Next-Generation Quant Alpha Strategies (Detailed Proposals)

### Strategy 1: LLM Financial News & Disclosure Sentiment Scoring Engine

#### 1. Architecture & NLP Parser Setup
- **Target Feeds**:
  - **KRX (KOSPI/KOSDAQ/KONEX)**: DART (Data Analysis, Retrieval and Transfer System) Open API XML/JSON filings (Periodic Reports: 1/3/6/12M, Major Disclosures, Earnings Releases, Capital Adjustments).
  - **US (SP500)**: SEC EDGAR RSS feed & API (10-K, 10-Q, 8-K items: Item 1.01 Material Agreements, Item 2.02 Results of Operations, Item 7 MD&A).
- **Parser Pipeline**:
  - Uses `FinBERT` (for standardized financial sentiment classification) fine-tuned on Korean & English financial corpora, with optional fallback to `Claude 3.5 Sonnet / GPT-4o API` for complex unstructured disclosures.

#### 2. Text Parsing & Event Extraction
The parser extracts structural text chunks and categorizes disclosure events:
- Earnings Surprises / Guidance Changes
- M&A, Asset Sales, Supply Contracts
- Regulatory Actions, Litigation, Executive Changes

#### 3. Mathematical Formulation & Scoring Model
For stock $i$ at time $t$, let $\{c_1, c_2, \dots, c_K\}$ be the disclosures published within time window $[t - \tau, t]$. Each disclosure $k$ is assigned:
- Sentiment Polarity: $\text{Polarity}_k \in [-1.0, +1.0]$
- Surprise Event Magnitude: $\text{Magnitude}_k \in [0.0, 10.0]$
- Source Credibility Weight: $w_s(c_k) \in [0.5, 1.5]$ (Official DART/EDGAR = 1.5, Major Financial News = 1.0, Blog/Social = 0.5)

The raw sentiment score $S_{i, t}$ is calculated using an exponential decay function:
$$S_{i, t} = \sum_{k=1}^{K_{i, t}} w_s(c_k) \cdot \text{Polarity}_k \cdot \text{Magnitude}_k \cdot \exp\left(-\lambda \cdot (t - t_k)\right)$$
where $\lambda = \frac{\ln(2)}{T_{\text{half}}}$ with decay half-life $T_{\text{half}} = 3 \text{ days}$.

The raw sentiment score is standardized across the market universe:
$$Z(S_{i, t}) = \text{Clip}\left( \frac{S_{i, t} - \mu_S(t)}{\sigma_S(t)}, -3.0, 3.0 \right)$$

#### 4. Feature Logic Derived
1. **1-Day Disclosure Sentiment Score**: $F_{\text{sent\_1d}, i, t} = Z(S_{i, t})$.
2. **7-Day Cumulative Sentiment Momentum**: $F_{\text{sent\_7d\_mom}, i, t} = \sum_{j=0}^{6} Z(S_{i, t-j})$.
3. **Sentiment Surprise Delta**: $\Delta S_{i, t} = Z(S_{i, t}) - \text{EMA}_{20}(Z(S_{i, t}))$.
4. **Filing Uncertainty / Complexity Index**: Frequency ratio of hedging, modal, and uncertainty terms ($\text{Complexity}_{i, t} \in [0, 1]$). High complexity discounts positive sentiment polarity.

#### 5. Pipeline Integration
- **Data Fetcher**: `src/data_layer/llm_sentiment_fetcher.py` (Asynchronous HTTP polling of DART Open API & SEC EDGAR RSS).
- **Storage**: SQLite `llm_sentiment_cache` table managed by `MarketIndicatorStorage` in `src/data_layer/indicator_storage.py`.
- **Engine Module**: `src/core/llm_sentiment.py` (`LLMSentimentEngine`).
- **Ensemble Scorer**: Integrated as Strategy 18 in `src/ai/ensemble_scorer.py`. Weight dynamically increases during earnings disclosure windows ($\text{Weight} \uparrow 0.12$).

---

### Strategy 2: Real-Time Orderbook Imbalance (OBI) & Microstructure Flow

#### 1. Microstructure Level 2 Depth Queue Data Input
- High-frequency Level 2 orderbook feed capturing top $L$ depth levels ($L = 5$ or $10$):
  - Bids: Price $P_b^{(l)}$, Volume $V_b^{(l)}$ for $l = 1, \dots, L$
  - Asks: Price $P_a^{(l)}$, Volume $V_a^{(l)}$ for $l = 1, \dots, L$

#### 2. Orderbook Imbalance (OBI) Formulation
The Level-$L$ Orderbook Imbalance $\text{OBI}_t^{(L)}$ is defined as:
$$\text{OBI}_t^{(L)} = \frac{\sum_{l=1}^L w_l \cdot V_{b, t}^{(l)} - \sum_{l=1}^L w_l \cdot V_{a, t}^{(l)}}{\sum_{l=1}^L w_l \cdot V_{b, t}^{(l)} + \sum_{l=1}^L w_l \cdot V_{a, t}^{(l)}}$$
where depth decay weight $w_l = \frac{1}{l}$ or $w_l = \exp(-\eta (P^{(l)} - P_{\text{mid}}))$.

#### 3. Microstructure Flow Variables
1. **Trade Aggressor Volume Delta ($\Delta V_t$)**:
   $$\Delta V_t = V_{\text{buy, tick}} - V_{\text{sell, tick}}$$
   (Categorized using the Lee-Ready tick algorithm: trades at ask price or higher are buy-initiated; trades at bid price or lower are sell-initiated).
2. **Order Flow Acceleration ($\text{OFA}_t$)**:
   $$\text{OFA}_t = \frac{d}{dt}(\Delta V_t) \approx \text{EMA}_5(\Delta V_t) - \text{EMA}_{20}(\Delta V_t)$$
3. **Tick-Level Money Flow Index ($\text{Tick\_MFI}_N$)**:
   $$\text{Tick\_MFI}_N = \frac{\sum_{i=1}^N \mathbf{1}_{\{\Delta P_i > 0\}} \cdot (P_i \cdot V_i)}{\sum_{i=1}^N P_i \cdot V_i}$$

#### 4. Microstructure Noise Filtering & Daily Signal Aggregation
- Tick-level OBI and volume delta are noisy. Intraday signals are aggregated over 5-minute VWAP windows:
  $$\text{OBI}_{\text{5m}, k} = \frac{\sum_{m \in k} \text{VWAP}_m \cdot \text{OBI}_m}{\sum_{m \in k} \text{VWAP}_m}$$
- The daily end-of-day feature `OBI_EOD_Score` is computed as the volume-weighted average of the last 30 minutes of trading (closing auction imbalance sensitivity):
  $$F_{\text{OBI\_EOD}, i} = \text{Standardize}\left( \text{OBI}_{\text{close, 30m}, i} \right)$$

#### 5. Pipeline Integration
- **Data Streamer**: `src/data_layer/orderbook_websocket.py` (KIS API WebSocket for KOSPI/KOSDAQ L2 depth; Alpaca/Polygon L2 WebSocket for US equities).
- **Engine Module**: `src/core/orderbook_microstructure.py` (`OrderbookMicrostructureEngine`).
- **Ensemble Scorer**: Integrated as Strategy 19 in `src/ai/ensemble_scorer.py`. High predictive power for short-term (1-day horizon) execution and close-to-open return prediction.

---

### Strategy 3: Macro Regime Switching HMM (Hidden Markov Model)

#### 1. Gaussian Hidden Markov Model (HMM) Architecture
Replaces rigid static threshold regime rules with a probabilistic $K$-state Gaussian Hidden Markov Model ($K = 4$ latent market states):
- **State 0 (Bull / Risk-On)**: Low VIX, positive market returns, low credit spread, stable currency.
- **State 1 (Bear / Risk-Off)**: Negative market momentum, elevated VIX, currency depreciation.
- **State 2 (Sideways / Mean-Reverting)**: Low trend strength, moderate volatility, range-bound indices.
- **State 3 (High-Volatility / Crisis)**: Extreme VIX spikes, yield curve inversion/steepening stress, oil shocks.

#### 2. Input Macro Observation Vector
Input multivariate time series $X_t \in \mathbb{R}^4$:
$$X_t = \begin{bmatrix} \Delta \text{VIX}_t \\ \Delta \text{USDKRW}_t \\ \text{YieldCurve\_10Y2Y}_t \\ \Delta \ln(\text{WTI}_t) \end{bmatrix}$$

#### 3. Mathematical Formulation & Inference
- **State Transition Probability Matrix**: $A = (a_{ij})_{4 \times 4}$, where $a_{ij} = P(S_t = j \mid S_{t-1} = i)$.
- **Emission Likelihood**: For state $k \in \{0, 1, 2, 3\}$, the observations follow a multivariate Gaussian distribution:
  $$f(X_t \mid S_t = k) = \mathcal{N}(X_t \mid \boldsymbol{\mu}_k, \boldsymbol{\Sigma}_k)$$
- **Forward-Backward Algorithm**: Infers the posterior state probability distribution vector $\boldsymbol{\gamma}_t \in \mathbb{R}^4$:
  $$\gamma_{t, k} = P(S_t = k \mid X_1, X_2, \dots, X_t)$$
  where $\sum_{k=0}^3 \gamma_{t, k} = 1.0$.

#### 4. Dynamic Ensemble & Risk Integration Logic
The posterior probability vector $\boldsymbol{\gamma}_t$ replaces static 2D VIX/Trend regime flags in `EnsembleScoringEngine`:
- Strategy weights $\mathbf{w}(t)$ are dynamically re-calculated:
  $$\mathbf{w}(t) = \sum_{k=0}^3 \gamma_{t, k} \cdot \mathbf{W}_{\text{regime } k}$$
  - In State 0 (Bull): Boost weights for Momentum (MQ), Surge, XGBoost Regression.
  - In State 1 (Bear): Boost weights for Short-Term Reversal, Stat-Arb, RIM Valuation, and increase cash buffer.
  - In State 2 (Sideways): Boost weights for Stat-Arb, VCP Pattern, Lead-Lag.
  - In State 3 (Crisis): Trigger automated `RiskManager` Crisis Gating ($\gamma_{t, 3} > 0.40$), reducing gross equity exposure to defensive floor ($20\%$).

---

## 4. Phase 1 to Phase 4 Advanced Construction Roadmap

```
+-----------------------------------------------------------------------------------+
|                            4-PHASE INTEGRATION ROADMAP                           |
+-----------------------------------------------------------------------------------+
| Phase 1: Integrity Stabilization & Immediate Bug Fixes                            |
|   - 60-day Filing Lag | Stat-Arb Cointegration | RIM Discounting | DB WAL Safety    |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
| Phase 2: Portfolio Optimization & Risk Controls                                   |
|   - Ledoit-Wolf Shrinkage | Risk Parity | RiskManager Gating | Dynamic Re-weight |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
| Phase 3: Execution Engine & OMS Upgrade                                           |
|   - TWAP/VWAP Scheduler | trade_logs.db | Slippage/Tracking Error | PyArrow IPC    |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
| Phase 4: Next-Gen Alpha & AI Innovation                                           |
|   - LLM Sentiment (DART/SEC) | Real-Time OBI | Macro HMM | Live KIS/IB Trading     |
+-----------------------------------------------------------------------------------+
```

### Phase 1: Integrity Stabilization & Immediate Bug Fixes
- **Objective**: Eliminate lookahead biases, mathematically correct factor implementations, ensure database concurrency safety, and restore missing core strategy files.
- **Key Modules & Fixes**:
  1. **60-Day Fundamental Filing Lag**: Enforce strictly 60-day lag on quarterly accounting statements in `src/ai/prediction_model.py` and `src/data_layer/earnings_data.py` to eliminate lookahead bias.
  2. **Stat-Arb Cointegration Correctness**: Update `src/core/stat_arb.py` to compute Johansen / ADF cointegration on log prices $\ln(P_A), \ln(P_B)$ to avoid spurious regression on non-stationary price series.
  3. **RIM Valuation Discounting**: Fix `src/core/rim_valuation.py` formula to properly discount residual income stream using cost of equity $r_e$:
     $$V_0 = B_0 + \sum_{t=1}^T \frac{(ROE_t - r_e) \cdot B_{t-1}}{(1 + r_e)^t} + \frac{(ROE_T - r_e) \cdot B_{T-1}}{r_e (1 + r_e)^T}$$
  4. **LATR Factor Corrections**: Re-engineer `src/core/latr_factor.py` to combine 52-week drawdown ($DD_i$), 5-day volume surge ($S_i$), and tail risk downside beta.
  5. **Database Mutex & WAL Lock Safety**: Enhance `StockPriceDB` (`src/persistence/database.py`) and `MarketIndicatorStorage` (`src/data_layer/indicator_storage.py`) with explicit mutex locking, SQLite WAL mode, and dynamic retry backoff.
  6. **Missing Strategy Restoration**: Ensure proper loading of `src/core/arm_factor.py`, `src/core/card_factor.py`, and `src/core/latr_factor.py`.
- **Target Deliverable**: Pass all unit/integration tests (`pytest tests/`) with zero lookahead leaks.

---

### Phase 2: Portfolio Optimization & Risk Controls
- **Objective**: Transition from simple linear weight scaling to institutional-grade portfolio allocation and dynamic risk gating.
- **Key Modules & Upgrades**:
  1. **Ledoit-Wolf Covariance Shrinkage**: Implement Shrinkage Covariance estimator in `src/risk/portfolio_optimizer.py`:
     $$\boldsymbol{\Sigma}_{\text{LW}} = \delta \mathbf{F} + (1 - \delta) \mathbf{S}$$
     where $\mathbf{S}$ is the sample covariance matrix and $\mathbf{F}$ is the structured prior.
  2. **Equal Risk Contribution (Risk Parity) Optimization Engine**:
     Solve for portfolio weights $\mathbf{w}^*$:
     $$\min_{\mathbf{w}} \sum_{i=1}^N \sum_{j=1}^N \left( w_i (\boldsymbol{\Sigma} \mathbf{w})_i - w_j (\boldsymbol{\Sigma} \mathbf{w})_j \right)^2 \quad \text{s.t.} \quad \sum_{i=1}^N w_i = 1, \quad w_i \ge 0$$
  3. **Sector & Factor Neutrality Constraints**: Impose max sector exposure limits ($\pm 5\%$ relative to market benchmark) and market beta neutrality bounds ($\beta_P \in [0.90, 1.10]$).
  4. **RiskManager Crisis Gating Integration**: Connect `src/risk/risk_manager.py` directly into `run_pipeline.py`. Trigger automated cash shift (50–80% allocation to liquid cash/treasuries) when macro crisis score exceeds threshold.
  5. **Dynamic Missingness Re-Weighting**: Connect `src/analysis/coverage_analyzer.py` to `EnsembleScoringEngine` to dynamically re-distribute weight away from missing factors without distorting total ensemble scale.
- **Target Deliverable**: Portfolio Sharpe ratio improvement > 20%, maximum drawdown reduction > 30% under historical backtest stress periods.

---

### Phase 3: Execution Engine & OMS Upgrade
- **Objective**: Minimize execution slippage, track market impact, and achieve high-throughput parallel execution across 3,379 symbols.
- **Key Modules & Upgrades**:
  1. **OMS Execution Scheduler**: Build `src/execution/oms_engine.py` supporting TWAP (Time-Weighted Average Price) and VWAP order execution algorithms to minimize market impact on illiquid symbols.
  2. **Real-Time Trade Log Database (`trade_logs.db`)**: Store order lifecycle events (Order Placed, Partial Fill, Filled, Cancelled, Slippage, Commission).
  3. **Slippage & Tracking Error Monitoring**:
     $$\text{Slippage}_i = \frac{P_{\text{executed}, i} - P_{\text{decision}, i}}{P_{\text{decision}, i}}$$
     $$\text{Tracking Error} = \sqrt{\frac{1}{T-1} \sum_{t=1}^T \left( r_{\text{portfolio}, t} - r_{\text{target}, t} \right)^2}$$
  4. **Vectorized Multiprocessing & Shared Memory**: Optimize feature computation for 3,379 symbols using Python `ProcessPoolExecutor` / Ray and zero-copy `pyarrow` IPC memory buffers, cutting pipeline execution time from 45 minutes to < 8 minutes.
- **Target Deliverable**: Reduction of total execution cost (slippage + spread) by > 15 bps; sub-8-minute full-universe pipeline execution.

---

### Phase 4: Next-Gen Alpha & AI Innovation
- **Objective**: Full deployment of LLM sentiment, real-time microstructure, and HMM macro regime switching strategies into live trading operations.
- **Key Modules & Upgrades**:
  1. **Deploy Strategy 1 (LLM Disclosure Sentiment)**: Connect asynchronous DART & SEC EDGAR scrapers to FinBERT/Claude API parsing service.
  2. **Deploy Strategy 2 (Real-Time Orderbook Imbalance)**: Establish low-latency WebSocket connection to KIS and US broker Level 2 orderbook feeds.
  3. **Deploy Strategy 3 (Macro Regime HMM)**: Train and update 4-state Gaussian HMM weekly on global macro time series (VIX, USDKRW, Yield Curve, WTI).
  4. **Paper & Live Trading Deployment**: Connect `src/execution/oms_engine.py` to live brokerage APIs (KIS Open API for KRX, Interactive Brokers API for US SP500).
  5. **Automated CI/CD & GitHub Pages Reporting**: Continuous generation of daily execution logs, factor coverage reports (`strategy_data_coverage_report.txt`), and ensemble prediction rankings (`ensemble_predictions.txt`).
- **Target Deliverable**: 24/7 fully automated, end-to-end multi-asset trading system with multi-factor & multi-model alpha generation.

---

## 5. Caveats

1. **Network Constraint & Offline Simulation**:
   - Current agent environment runs in `CODE_ONLY` mode (no active external internet access). The LLM API and WebSocket feeds were designed theoretically with complete protocol specifications and offline fallback simulation interfaces.
2. **Computational Load of High-Frequency Microstructure Data**:
   - Strategy 2 (OBI) requires high-bandwidth Level 2 orderbook data streams. For full universe (3,379 symbols), streaming all depth updates requires substantial memory and bandwidth; production deployment should prioritize top liquid symbols (e.g., KOSPI 200 & SP 500).

---

## 6. Conclusion

The next-generation quant alpha strategies (LLM Sentiment, Real-Time OBI/Microstructure Flow, and Macro Regime HMM) provide strong, orthogonal alpha sources that complement the existing 17 strategies in the stock trading system.

The Phase 1 through Phase 4 construction roadmap delivers a structured, step-by-step path:
- **Phase 1**: Stabilize system integrity, eliminate lookahead bias, and fix factor formulas.
- **Phase 2**: Implement Risk Parity & Ledoit-Wolf Covariance Shrinkage portfolio optimization.
- **Phase 3**: Upgrade OMS execution engine, monitor slippage/tracking error, and vectorize processing.
- **Phase 4**: Productionize next-gen AI strategies, live broker APIs, and automated dashboard reporting.

---

## 7. Verification Method

1. **File Inspection**:
   - Verify handoff report: `view_file d:\Finance\code\stock\.agents\worker_m3\handoff.md`
   - Verify progress tracking: `view_file d:\Finance\code\stock\.agents\worker_m3\progress.md`
   - Verify briefing log: `view_file d:\Finance\code\stock\.agents\worker_m3\BRIEFING.md`
2. **System Unit & Integration Testing**:
   - Run pipeline test suite: `.venv/bin/pytest tests/ -v`
   - Verify portfolio optimizer tests: `.venv/bin/pytest tests/test_portfolio_risk.py -v`
   - Verify OMS engine tests: `.venv/bin/pytest tests/phase3/test_allocation.py -v`
