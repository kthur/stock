# Alpha Strategy Engines Comprehensive Survey & Technical Architecture Report

**Explorer**: Strategy Alpha Explorer (Explorer 1)  
**Target Working Directory**: `d:\Finance\code\stock\.agents\teamwork_preview_explorer_survey_1`  
**Date**: 2026-08-14  
**Scope**: In-depth architectural, mathematical, and algorithmic investigation of all 31 strategy engines in `trading_system/src/core/`, `trading_system/src/ai/`, and associated orchestration layers, with deep dives into alpha scoring formulations, noise filtering mechanisms, statistical calibration, and signal precision enhancements.

---

## 1. Executive Summary & Core Architectural Findings

The trading system implements an end-to-end multi-factor, multi-model algorithmic alpha generation platform operating across **3,379 symbols** in 5 primary markets (KOSPI, KOSDAQ, KONEX, S&P 500, NASDAQ, RUSSELL 2000). The engine integrates **31 diverse strategies** categorized into:
1. **Machine Learning / Deep Learning Models** (Regression, Surge, VCP ML, Strict Causal LSTM)
2. **Cross-Asset & Sector Relative Momentum** (Lead-Lag, Sector Rotation, CARD, Supply Chain)
3. **Statistical Arbitrage & Microstructure** (Stat-Arb Cointegration, Order Flow Imbalance, Trend Efficiency, Microstructure/HFT)
4. **Fundamental & Accounting Quality** (RIM Valuation, Momentum Quality, ARM, Style Neutralizer, Accruals Quality, Value-Up)
5. **Corporate Catalysts & Alternative Data** (Event-Driven, NLP Sentiment, Short Squeeze, Options IV Skew, Gamma Squeeze, Insider Buying, Earnings Tone Drift)

### Key Architectural Strengths:
1. **2D Regime-Conditioned Dynamic Sharpe Weighting**: Base weights in a $6 \times 31$ regime matrix (`BEAR_LOW_VOL`, `BEAR_HIGH_VOL`, `SIDEWAYS_LOW_VOL`, `SIDEWAYS_HIGH_VOL`, `BULL_LOW_VOL`, `BULL_HIGH_VOL`) are adaptively modulated by rolling 60-day out-of-sample Sharpe ratios via an exponential multiplier $w_i = \text{base\_w}_i \cdot \exp(\gamma \cdot \text{clip}(\text{Sharpe}_i, -1.5, 1.5))$ and gated by 3D Macro Modifiers (`LIQUIDITY_SQUEEZE`, `HIGH_YIELD_BEAR`, `INFLATION_SHOCK`, `YIELD_INVERSION`).
2. **Orthogonalization & Collinearity Defense**: Gram-Schmidt and Löwdin Symmetric (PCA ZCA) whitening operators are applied to decorrelate collinear strategy scores, guaranteeing cross-strategy pairwise correlations $|r| < 0.30$.
3. **Hybrid Probability Calibration**: Robust probability calibration using Isotonic Regression for sample sizes $N \ge 50$ and Platt Logistic Scaling for $20 \le N < 50$, with isotonic monotonicity fallbacks.
4. **Realistic Microstructure Cost Deduction**: Every alpha prediction undergoes non-linear Kyle/Almgren-Chriss square-root market impact and bid-ask spread friction modeling before expected return ranking.

---

## 2. In-Depth Technical Catalog & Analysis of All 31 Strategy Engines

### Strategy 1: XGBoost/LGBM/CatBoost Multi-Horizon Regression (`src/ai/prediction_model.py`)
- **Alpha Scoring Formulation**: Predicts continuous expected forward returns across 8 horizons ($h \in \{1, 5, 10, 20, 30, 60, 120, 200\}$ trading days). Uses a weighted multi-horizon composite:
  $$\text{Expected Return} = \sum_{h} w_h \cdot \hat{y}_h$$
- **Noise Filtering & Anti-Leakage**:
  - 60-day financial filing lag strictly enforced on fundamental data.
  - Float32 memory downcasting prevents floating-point divergence.
  - Cross-market feature normalization: features are z-scored per market partition (`SP500`, `NASDAQ`, `KOSPI`, `KOSDAQ`) to prevent macro structural skew.
- **Precision Opportunities**: Incorporate Huber loss ($\delta=1.35$) or quantile regression to dampen extreme single-day outlier returns.

---

### Strategy 2: Multi-Model Surge Classifier (`src/ai/prediction_model.py`)
- **Alpha Scoring Formulation**: Predicts probability of $\ge 20\%$ upward breakout over 1, 3, 5, and 20-day horizons:
  $$P(\text{Surge} = 1 \mid X) = \sigma\left(\text{Blend}(\hat{p}_{XGB}, \hat{p}_{LGB}, \hat{p}_{CAT})\right)$$
- **Noise Filtering & Anti-Leakage**:
  - Capped positive class weight: $\text{scale\_pos\_weight} = \min\left(\frac{N_{neg}}{N_{pos}}, 20.0\right)$ eliminates severe false-positive inflation in highly imbalanced market regimes.
  - 20-day training embargo between cross-validation splits to prevent multi-day target label overlap.
  - Platt Logistic scaling calibration metadata applied per market.
- **Precision Opportunities**: Regime-conditional probability thresholding—raise decision boundary from $0.20$ to $0.35$ in `BEAR_HIGH_VOL` to suppress trap breakouts.

---

### Strategy 3: 2-Tier / 3-Tier Lead-Lag Momentum (`src/ai/prediction_model.py`, `src/core/lead_lag_3tier.py`)
- **Alpha Scoring Formulation**: Evaluates lag-1 cross-correlation between tier-1 industry leaders / sector ETFs and tier-2/3 laggards:
  $$\text{LL\_Score}_i = \sigma\left(\sum_{k \in \text{Leaders}} \rho_{i,k}^{(\tau=1)} \cdot R_{k, t-1}\right)$$
- **Noise Filtering & Anti-Leakage**:
  - Explicit US market 1-day lag shift for Asian equities: prevents look-ahead bias caused by timezone offsets between NYSE/NASDAQ close and KRX open.
  - Statistically insignificant cross-correlations ($|\rho| < 0.25$ or $p > 0.05$) are zeroed out.
- **Precision Opportunities**: Dynamic leader selection based on rolling 20-day Granger causality F-test rather than static market cap rankings.

---

### Strategy 4: Volatility Contraction Pattern (VCP) Rule Engine (`src/ai/vcp_detector.py`)
- **Alpha Scoring Formulation**: Mark Minervini 4-step progressive volatility contraction algorithm:
  - Contraction verification: $R_1 \le c \cdot R_2 \le c^2 \cdot R_3 \le c^3 \cdot R_4$ across non-overlapping windows $[-5:], [-15:-5], [-35:-15], [-60:-35]$ with $c = 0.85$.
  - Volume dry-up confirmation: $\text{Vol}_{20d} < 0.85 \cdot \text{Vol}_{60d}$.
  - Trend template filter: Price $> \text{SMA}_{50} > \text{SMA}_{200}$ and Price within $15\%$ of 52-week high.
- **Noise Filtering**:
  - Non-overlapping contraction windows eliminate rolling slice correlation artifacts.
  - Minimum VCP score gate ($\ge 50.0 / 100.0$) before signal emission.
- **Precision Opportunities**: Add volume linear regression slope check ($\beta_{vol} < 0$) over the final contraction phase.

---

### Strategy 5: VCP ML Surge Predictor (`src/ai/vcp_ml_predictor.py`)
- **Alpha Scoring Formulation**: Market-segmented gradient boosting classifier trained on 11 domain-specific contraction features (`range_5v20`, `vol_20v60`, `dist_ma50`, `dist_ma200`, `range_pos_10d`, `atr_14d_norm`, `monotonic_flag`).
- **Noise Filtering**:
  - Optuna hyperparameter optimization on 5-day forward return metrics.
  - Dynamic class balancing and Isotonic probability calibration.
- **Precision Opportunities**: Incorporate intraday bar tightness (high-to-low spread normalized by open-close body).

---

### Strategy 6: Strict Causal LSTM Sequence Model (`src/ai/lstm_predictor.py`)
- **Alpha Scoring Formulation**: 20-day historical sequence encoder producing point forecasts of 5-day expected returns:
  $$\hat{y}_{t+5} = W_{fc} h_{t} + b_{fc}, \quad h_t = \text{LSTM}(x_{t-19:t})$$
- **Noise Filtering & Anti-Leakage**:
  - Strictly causal rolling z-score normalization: $\mu_t, \sigma_t$ calculated strictly on $[t-60, t]$ with zero forward window exposure.
  - PyTorch inference wrapped in deterministic evaluation mode (`model.eval()`, `torch.no_grad()`).
- **Precision Opportunities**: Multi-head temporal attention mechanism to weight turning-point days over steady trending bars.

---

### Strategy 7: Statistical Arbitrage & Cointegration Engine (`src/core/stat_arb.py`)
- **Alpha Scoring Formulation**: Fast hierarchical cointegration pipeline:
  1. 15D Feature Extraction (mean return, std, skewness, kurtosis, returns 5/20/60d, downside std, max drawdown, lag-1 autocorrelation, SMA20/60 ratios, high-low spread, volume ratio).
  2. MiniBatch K-Means / OPTICS clustering reducing search complexity from $O(N^2)$ to $O(N \log N)$.
  3. BLAS-accelerated log-price correlation filter ($|r| \ge 0.70$).
  4. Two-step Engle-Granger ADF test: $\ln P_{1,t} - \beta \ln P_{2,t} - \alpha = \epsilon_t$.
  5. Ornstein-Uhlenbeck (OU) Mean-Reversion Half-Life: $\Delta \epsilon_t = \lambda \epsilon_{t-1} + \eta_t \Rightarrow t_{1/2} = -\frac{\ln 2}{\ln(1+\lambda)}$.
  6. Signal generation: $Z = \frac{\epsilon_t - \bar{\epsilon}}{\sigma_\epsilon}$. Long asset 1 / Short asset 2 when $Z < -1.5$; exit at $Z = 0$.
- **Noise Filtering**:
  - Benjamini-Hochberg False Discovery Rate (FDR) control at $q = 0.10$.
  - Half-life gating: $2.0 \le t_{1/2} \le 40.0$ days.
  - Structural break stop-loss: $|Z| > 3.2$ triggers immediate liquidation and pair blacklist.
- **Precision Opportunities**: Dynamic Kalman Filter state-space tracking for time-varying hedge ratio $\beta_t$.

---

### Strategy 8: Sector Rotation & GICS Relative Momentum (`src/core/sector_rotation.py`)
- **Alpha Scoring Formulation**:
  $$\text{Mom}_{raw} = 0.60 \cdot R_{20d} + 0.40 \cdot R_{60d}$$
  - Standardized 11 GICS sector mapping (`GICS_SECTOR_MAP`).
  - Adaptive Intra-Sector Dispersion Weighting:
    $$\text{Score} = (1 - w_{stock}) \cdot \text{Rank}_{sector} + w_{stock} \cdot \text{Rank}_{stock}$$
    where $w_{stock} = 0.60$ if $\sigma_{sector} > 0.05$ (stock-picking dispersion regime), else $0.35$.
- **Noise Filtering & Macro Sensitivity**:
  - Macro boosts: USD/KRW spike ($>0.5\%$) boosts IT/Auto; WTI spike ($>2.0\%$) boosts Energy/Materials and penalizes Bio/Staples; US10Y ($>4.2\%$) boosts Financials.
  - 2D Regime conditioning: BEAR boosts Utilities/Health Care (+6%); BULL boosts IT/Financials (+5%).
- **Precision Opportunities**: Subtract 5-day reversal noise from 20-day return to eliminate transient overbought spikes.

---

### Strategy 9: Residual Income Model (RIM) Valuation Engine (`src/core/rim_valuation.py`)
- **Alpha Scoring Formulation**: Finite-horizon decaying ROE with retained earnings accumulation:
  $$V_0 = \text{BPS}_0 + \sum_{t=1}^8 \frac{\text{BPS}_{t-1} \cdot (\text{ROE}_{t-1} - r_e)}{(1 + r_e)^t}$$
  $$\text{BPS}_t = \text{BPS}_{t-1} + \text{NetIncome}_t \cdot \text{retention\_ratio}$$
  $$\text{ROE}_t = r_e + (\text{ROE}_{t-1} - r_e) \cdot (1 - \text{decay\_rate})^t$$
  - Dynamic required return $r_e = \text{US10Y} + \text{ERP}$ ($5\%$ US, $6\%$ KR).
- **Noise Filtering & Accounting Safeguards**:
  - **Earnings Quality Filter**: $\text{EQ} = \text{clip}\left(\frac{\text{Operating Income}}{\text{Net Income}}, 0, 1\right)$. If $\text{EQ} < 0.5$, ROE is proportionally discounted.
  - **Operating Loss Disqualification**: If $\text{Operating Income} \le 0$ but $\text{Net Income} > 0$ (one-off non-operating windfall), RIM score is invalidated (`NaN`), triggering automatic dynamic ensemble weight re-normalization.
  - **Preferred Share Disqualification**: Preferred shares (`005935`, `00680K`, etc.) are filtered out due to capital structure discrepancies.
- **Precision Opportunities**: Multi-stage dividend payout ratio modeling based on historical 3-year cash dividends.

---

### Strategy 10: Event-Driven Momentum & Filing Catalyst (`src/core/event_driven.py`)
- **Alpha Scoring Formulation**: OpenDART & disclosure parser assigning directional catalyst weights:
  - Bullish: Stock splits ($0.90$), Treasury share buyback/cancellation ($0.85$), Earnings turnaround ($0.75$).
  - Bearish: Capital increase / Rights offering ($0.20$), CB/BW issuance ($0.20$), Treasury share disposal ($0.20$), Operating loss conversion ($0.30$).
- **Noise Filtering & Risk Sandboxes**:
  - **CB/BW Overhang Trap Sandbox**: Flags dilution $> 5.0\%$ of float, triggering strict risk blacklisting.
  - **Margin Loan Risk Penalty**: Margin debt rate $> 9.0\%$ applies penalty factor $\text{clip}(1.0 - (\text{rate}-9.0)\times 0.05, 0.50, 1.0)$.
- **Precision Opportunities**: NLP sentiment intensity multiplier ($0.5\times \dots 1.5\times$) integration.

---

### Strategy 11: Momentum Quality (MQ) Factor Engine (`src/core/mq_factor.py`)
- **Alpha Scoring Formulation**: 12M-1M price momentum (skipping recent 21 trading days to remove short-term reversal noise):
  $$\text{Mom}_{12M-1M} = \frac{P_{t-21}}{P_{t-252}} - 1.0$$
  Combined with fundamental quality composite: Operating Margin Rank ($33\%$), 1Y EPS Growth Rank ($33\%$), ROE Stability Rank ($33\%$).
- **Noise Filtering**:
  - Adaptive weighting: $w_{qual} = 0.40 \cdot \frac{N_{valid}}{3}$, $w_{mom} = 1.0 - w_{qual}$.
- **Precision Opportunities**: Add cash-flow momentum (quarter-over-quarter OCF acceleration).

---

### Strategy 12: Options Implied Volatility (IV) Skew (`src/core/iv_skew.py`)
- **Alpha Scoring Formulation**: Evaluates 25-delta Put IV vs Call IV skew ratio on near-the-money options:
  $$\text{Skew Ratio} = \frac{\text{IV}_{Put}}{\text{IV}_{Call}}$$
  Extreme Put skew ($>1.40$) indicates institutional panic hedging $\Rightarrow$ contrarian bullish buying score: $\text{Score} = 0.5 + (\text{Skew} - 1.1) \cdot 0.5$.
- **Noise Filtering**:
  - Zero-network in-memory fallback using realized downside-to-upside return volatility and return skewness proxy:
    $$\text{Proxy Skew} = \frac{\sigma_{\text{down}}}{\sigma_{\text{up}}}, \quad \text{Score} = \text{clip}(0.5 + (\text{Skew} - 1.0)\cdot 0.25 - \text{Skewness}\cdot 0.15, 0, 1)$$
- **Precision Opportunities**: Term-structure slope adjustment (front-month IV vs 3-month IV).

---

### Strategy 13: Order Flow Imbalance & Supply Acceleration (`src/core/order_flow.py`)
- **Alpha Scoring Formulation**: Multi-component volume flow imbalance:
  $$\text{Score} = 0.45 \cdot \text{MFI} + 0.20 \cdot \text{OBV\_Trend} + 0.15 \cdot \text{Vol\_Accel} + 0.20 \cdot \text{VWAP\_Dev}$$
- **Noise Filtering**:
  - Institutional/Foreign net buy 5-day flow boost ($+0.10$ Foreign, $+0.10$ Trust).
  - VWAP deviation scaled non-linearly to prevent outlier price distortion.
- **Precision Opportunities**: Level-2 Order Book Imbalance (OBI) depth integration.

---

### Strategy 14: Short-Term Reversal & Oversold Bounce (`src/core/short_term_reversal.py`)
- **Alpha Scoring Formulation**: Detects extreme oversold exhaustion in fundamentally sound stocks:
  $$\text{Oversold Metric} = -1.0 \cdot R_{5d} + 0.10 \cdot \text{Consecutive Down Days} - 0.20 \cdot \frac{P_t - \text{BB}_{lower}}{\sigma_{20d}}$$
- **Noise Filtering**:
  - Value Trap Defense: Stocks with Operating Margin $< -10\%$ receive severe penalty ($-1.0$), disqualifying chronic distress companies from mean-reversion buying.
- **Precision Opportunities**: RSI divergence confirmation (lower price low with higher RSI low).

---

### Strategy 15: Analyst Revision Momentum (ARM) (`src/core/arm_factor.py`)
- **Alpha Scoring Formulation**: Quantifies 60-day consensus EPS and Target Price revision momentum:
  $$\text{ARM}_{raw} = 0.50 \cdot \Delta \text{EPS}_{rev} + 0.50 \cdot \Delta \text{TP}_{rev} + 0.20 \cdot R_{20d}$$
  Fallback to fundamental growth penalized by excessive valuation: $0.40 \cdot \text{EPS}_{growth} + 0.30 \cdot \text{Rev}_{growth} - 0.01 \cdot \text{PER}$.
- **Noise Filtering**: 1st/99th percentile winsorization before percentile normalization.
- **Precision Opportunities**: Analyst dispersion weighting (high analyst consensus agreement increases confidence).

---

### Strategy 16: Cross-Asset Regime Divergence (CARD) (`src/core/card_factor.py`)
- **Alpha Scoring Formulation**: Evaluates abnormal divergence between stock return and macro asset basket:
  $$\text{Macro Impact} = (0.30 \cdot \Delta \text{USDKRW} + 0.30 \cdot \Delta \text{WTI} + 0.40 \cdot \text{VIX}_{norm}) \cdot \beta_{sector} \cdot 10.0$$
  $$\text{CARD\_Score} = \frac{1}{1 + \exp(0.10 \cdot (R_{5d} - \text{Macro Impact}))}$$
- **Noise Filtering**: Sector beta scaling prevents penalizing low-beta defensives during market turmoil.
- **Precision Opportunities**: Dynamic rolling 60-day sector beta estimation via OLS.

---

### Strategy 17: Liquidity-Adjusted Tail Risk (LATR) (`src/core/latr_factor.py`)
- **Alpha Scoring Formulation**: Identifies panic selling exhaustion bounces:
  $$\text{LATR} = 0.35 \cdot \exp\left(-\frac{(\text{DD}_{52W} - 0.35)^2}{2 \cdot 0.15^2}\right) + 0.35 \cdot \min(\text{Vol\_Surge}, 3.0) - 0.15 \cdot |\text{VaR}_{5\%}| + 0.15 \cdot \text{Amihud}$$
- **Noise Filtering**: Gaussian scoring centered at optimal $35\%$ drawdown; excludes irrecoverable $>70\%$ collapses.
- **Precision Opportunities**: Expected Shortfall (CVaR) substitution for VaR 5%.

---

### Strategy 18: Institutional & Foreign Trust 2-Month Accumulation (`src/core/inst_foreign_sector.py`)
- **Alpha Scoring Formulation**: Separately calculates Foreigner and Investment Trust (투신) 40-day net accumulation:
  $$\text{Accumulation} = 0.50 \cdot \text{Foreign\_Acc} + 0.50 \cdot \text{Trust\_Acc}$$
  $$\text{Composite} = 0.60 \cdot \text{Accumulation} + 0.40 \cdot \text{Sector Leader Correlation}$$
- **Noise Filtering**: Peer group leader correlation identifies laggards poised for institutional catch-up.
- **Precision Opportunities**: Institutional flow concentration ratio (Herfindahl index of buying brokers).

---

### Strategy 19: Supply Chain Lead-Lag Momentum (`src/core/supply_chain.py`)
- **Alpha Scoring Formulation**: Propagates 1D ($60\%$) and 3D ($40\%$) return signals from global tier-1 anchor customers (e.g. NVDA, AAPL, TSLA, Samsung, Hyundai) to domestic supply chain vendors.
- **Noise Filtering**: Clean symbol normalization with key supplier mapping table.
- **Precision Opportunities**: Dynamic customer revenue dependency weighting.

---

### Strategy 20: NLP FinBERT Sentiment Catalyst (`src/core/llm_sentiment_engine.py`)
- **Alpha Scoring Formulation**: Bilingual (Korean/English) corporate disclosure text sentiment parser:
  $$\text{Sentiment Score} = \frac{N_{pos} - N_{neg}}{N_{pos} + N_{neg} + 1}$$
- **Noise Filtering**: Domain-specific financial lexicons (`흑자전환`, `자사주소각` vs `적자전환`, `횡령`, `배임`, `유상증자`). Returns `NaN` when no filing text exists to prevent false neutral score pollution.
- **Precision Opportunities**: Sentence-level transformer FinBERT embeddings.

---

### Strategy 21: Multi-Factor Style Neutralizer (`src/core/multi_factor_neutralizer.py`)
- **Alpha Scoring Formulation**: Cross-sectional OLS regression on Fama-French 5-Factor exposures:
  $$y_i = \alpha_i + \beta_{SMB} \text{Size}_i + \beta_{HML} \text{Value}_i + \beta_{RMW} \text{Profitability}_i + \beta_{CMA} \text{Investment}_i + \beta_{MOM} \text{Momentum}_i + \epsilon_i$$
  Extracts pure idiosyncratic alpha score from normalized residual $\epsilon_i$.
- **Noise Filtering**: Automatically deactivates (`NaN`) when fundamental factor columns are missing.
- **Precision Opportunities**: WLS (Weighted Least Squares) weighted by square root of market cap.

---

### Strategy 22: Dynamic Volatility Targeting (`src/core/vol_target.py`)
- **Alpha Scoring Formulation**: Scales scores inversely proportional to realized conditional volatility:
  $$\sigma_{EWMA, t}^2 = \lambda \sigma_{t-1}^2 + (1 - \lambda) r_t^2, \quad \text{Score} = \text{clip}\left(\frac{\sigma_{target}}{\sigma_{realized}} \cdot 0.50, 0, 1\right)$$
- **Noise Filtering**: Floor volatility at $5\%$ to prevent division-by-zero leverage explosions.
- **Precision Opportunities**: GARCH(1,1) volatility forecasting.

---

### Strategy 23: Order Book Microstructure Imbalance (`src/core/hft_engine.py`, `src/core/lob_obi.py`)
- **Alpha Scoring Formulation**: Close location value (CLV) in daily bar range + closing auction volume acceleration predicting overnight gap edge:
  $$\text{CLV} = \frac{\text{Close} - \text{Low}}{\text{High} - \text{Low}}, \quad \text{Score} = \text{clip}(0.50 + 0.30 \cdot (2\text{CLV} - 1) + 0.15 \cdot (\text{Vol\_Accel} - 1), 0, 1)$$
- **Noise Filtering**: Minimum 3-bar and 5-bar volume historical smoothing.
- **Precision Opportunities**: Intraday tick data bid-ask spread and order book depth imbalance.

---

### Strategy 24: Sloan Accruals Quality Anomaly (`src/core/accruals_quality.py`)
- **Alpha Scoring Formulation**: Sloan (1996) accounting quality ratio:
  $$\text{Accrual Ratio} = \frac{\text{Net Income} - \text{Operating Cash Flow}}{\text{Total Assets}}$$
  $$\text{Score} = 1.0 - \text{Rank}(\text{Accrual Ratio})$$
- **Noise Filtering**: No artificial OCF imputation; missing cash flows yield neutral $0.50$.
- **Precision Opportunities**: Dechow-Dichev working capital accruals estimation.

---

### Strategy 25: Short Interest & Squeeze Potential (`src/core/short_interest_squeeze.py`)
- **Alpha Scoring Formulation**:
  $$\text{Squeeze Metric} = \text{Short Ratio} \cdot \text{Days-to-Cover} \cdot (1 + 2 \cdot \max(0, R_{5d}))$$
  Fallback: Volume surge $\times (1 + 3 \cdot R_{5d})$ oversold bounce proxy.
- **Noise Filtering**: Ranks clipped to $[0.05, 0.95]$.
- **Precision Opportunities**: Exchange loanable inventory fee rate tracking.

---

### Strategy 26: Value-Up & Shareholder Yield Catalyst (`src/core/valueup_catalyst.py`)
- **Alpha Scoring Formulation**: Prime Korean Value-Up catalyst scoring:
  $$\text{Score} = \text{PBR\_Factor} \cdot \left(1.0 + 1.5 \cdot \frac{\text{Net Cash}}{\text{MCap}} + 5.0 \cdot \text{Dividend Yield}\right)$$
  where $\text{PBR\_Factor} = 1.5 - 0.5 \cdot \text{PBR}$ for $\text{PBR} < 1.0$.
- **Noise Filtering**: Fallback PBR estimation via Price / BPS when PBR is unpopulated.
- **Precision Opportunities**: Inclusion of 3-year historical treasury share cancellation yield.

---

### Strategy 27: Kaufman Trend Efficiency & Fractal Noise Filter (`src/core/trend_efficiency.py`)
- **Alpha Scoring Formulation**: Multi-window Kaufman Efficiency Ratio ($5, 10, 20$ days) + Rescaled Range (R/S) Hurst Exponent:
  $$\text{KER}_n = \frac{|P_t - P_{t-n}|}{\sum_{i=1}^n |P_{t-i+1} - P_{t-i}|}, \quad H = \frac{\ln(R/S)}{\ln n}$$
  $$\text{Score} = 0.5 \pm 0.5 \cdot \overline{\text{KER}} \cdot \frac{H}{0.50}$$
- **Noise Filtering**: Choppy sideways regimes ($H \approx 0.5$, $\text{KER} \to 0$) gravitate to neutral $0.50$; directional high-purity trends receive high alpha conviction.
- **Precision Opportunities**: Wavelet multiresolution decomposition noise thresholding.

---

### Strategy 28: Options Gamma Squeeze & Call Wall Acceleration (`src/core/gamma_squeeze.py`)
- **Alpha Scoring Formulation**:
  $$\text{Score} = 0.40 \cdot \frac{P_t}{\text{High}_{20d}} + 0.30 \cdot \max(0, 5 R_{5d}) + 0.15 \cdot \text{Vol\_Surge}$$
  Live options chain net GEX override when in short gamma zone near Call Wall strike ($+0.35$ boost).
- **Noise Filtering**: Distance to call wall thresholding ($<3\%$).
- **Precision Opportunities**: Real-time dealer gamma profile calculation across all open strikes.

---

### Strategy 29: Corporate Insider Net Buying Anomaly (`src/core/insider_buying.py`)
- **Alpha Scoring Formulation**: OpenDART / SEC Form 4 insider transaction parser:
  - C-Suite / Chairman / Controlling shareholder open market purchases: $+0.35$ score boost.
  - Other executive purchases: $+0.20$ score boost.
  - Insider disposals / sales: $-0.25$ penalty.
- **Noise Filtering**: Pre-indexed $O(M)$ stock code hashing with exact symbol sanitization.
- **Precision Opportunities**: Transaction size relative to executive total compensation or company market cap.

---

### Strategy 30: Earnings Tone Drift & Guidance Shift (`src/core/earnings_tone_drift.py`)
- **Alpha Scoring Formulation**: Quarterly tone polarity shift:
  $$\Delta \text{Tone} = (\text{Tone}_{current} - \text{Tone}_{previous}) \cdot \text{Confidence}, \quad \text{Score} = \text{clip}(0.50 + 1.0 \cdot \Delta \text{Tone}, 0, 1)$$
- **Noise Filtering**: Confidence scaling downweights short or ambiguous disclosure transcripts.
- **Precision Opportunities**: Audio acoustic pitch / hesitation tone analysis on conference call audio.

---

### Strategy 31: High-Frequency Dark Pool & Block Flow Imbalance (`src/core/hft_engine.py`, `src/ai/ml_strategy_adapters.py`)
- **Alpha Scoring Formulation**: Combines off-exchange dark pool volume percentage with institutional block trade net buying:
  $$\text{DarkPool\_Score} = 0.50 \cdot \text{DPI} + 0.50 \cdot \text{Block\_Buy\_Ratio}$$
- **Noise Filtering**: Algorithmic execution slippage (TWAP / VWAP Almgren-Chriss impact modeling) deducted.
- **Precision Opportunities**: FINRA TRF volume feed integration for US equity flows.

---

## 3. Comparative Alpha Scoring & Precision Matrix (31 Strategies)

| # | Strategy Name | Code Location | Category | Primary Score Column | Default Regime Weights (Bear / Side / Bull) | Core Noise Filter | Recommended Precision Enhancement |
|---|---|---|---|---|---|---|---|
| **1** | XGBoost Regression | `src/ai/prediction_model.py` | ML | `reg_score` | 0.12 / 0.05 / 0.03 | 60d Filing Lag + Float32 downcast | Huber Loss / Quantile objective |
| **2** | Surge Classifier | `src/ai/prediction_model.py` | ML | `surge_score` | 0.01 / 0.02 / 0.07 | scale_pos_weight $\le 20$ cap + 20d Embargo | Regime-adaptive probability thresholds |
| **3** | Lead-Lag Shift | `src/ai/prediction_model.py` | Cross-Asset | `ll_score` | 0.02 / 0.03 / 0.02 | US 1d lag shift + $|\rho| \ge 0.25$ cutoff | Granger causality dynamic leader weights |
| **4** | VCP Rule Pattern | `src/ai/vcp_detector.py` | Technical | `vcp_rule_score` | 0.01 / 0.02 / 0.02 | 4 Non-overlapping contraction windows | Volume regression slope $\beta_{vol} < 0$ gate |
| **5** | VCP ML Predictor | `src/ai/vcp_ml_predictor.py` | ML | `vcp_ml_score` | 0.01 / 0.03 / 0.06 | Optuna 5d forward HPO + Isotonic calib | Intraday bar tightness feature |
| **6** | Strict Causal LSTM | `src/ai/lstm_predictor.py` | ML | `lstm_score` | 0.02 / 0.04 / 0.04 | Strictly causal rolling z-scores | Temporal multi-head attention layer |
| **7** | Stat-Arb Cointegration | `src/core/stat_arb.py` | Stat-Arb | `stat_arb_score` | 0.07 / 0.06 / 0.02 | 15D clustering + FDR $q=0.10$ + OU $t_{1/2}$ | Dynamic Kalman Filter hedge ratio $\beta_t$ |
| **8** | Sector Rotation | `src/core/sector_rotation.py` | Factor | `sector_score` | 0.03 / 0.04 / 0.04 | GICS 11 mapping + Intra-sector dispersion | 5-day reversal noise subtraction |
| **9** | RIM Valuation | `src/core/rim_valuation.py` | Factor | `rim_score` | 0.09 / 0.04 / 0.03 | Earnings quality filter + Preferred filter | 3Y historical dividend payout modeling |
| **10** | Event-Driven | `src/core/event_driven.py` | Event | `event_score` | 0.03 / 0.04 / 0.05 | CB/BW overhang sandbox + Margin rate gate | NLP sentiment intensity multiplier |
| **11** | Momentum Quality | `src/core/mq_factor.py` | Factor | `mq_score` | 0.05 / 0.04 / 0.04 | 12M-1M (1M reversal noise skipped) | QoQ Operating Cash Flow acceleration |
| **12** | Options IV Skew | `src/core/iv_skew.py` | Factor | `iv_skew_score` | 0.03 / 0.02 / 0.02 | Realized down/up vol proxy fallback | Front-month vs 3M term structure slope |
| **13** | Order Flow Imbalance | `src/core/order_flow.py` | Factor | `order_flow_score` | 0.02 / 0.03 / 0.03 | MFI + OBV slope + VWAP deviation | Level-2 Order Book Imbalance (OBI) depth |
| **14** | Short-Term Reversal | `src/core/short_term_reversal.py` | Factor | `reversal_score` | 0.04 / 0.03 / 0.02 | Op Margin $< -10\%$ distress penalty | RSI bullish divergence confirmation |
| **15** | Analyst Revision (ARM) | `src/core/arm_factor.py` | Factor | `arm_score` | 0.04 / 0.04 / 0.04 | 1%/99% percentile winsorization | Analyst consensus agreement dispersion |
| **16** | Cross-Asset CARD | `src/core/card_factor.py` | Factor | `card_score` | 0.04 / 0.04 / 0.03 | Sector beta macro scaling | Rolling 60d OLS sector beta |
| **17** | Liquidity Tail LATR | `src/core/latr_factor.py` | Factor | `latr_score` | 0.04 / 0.03 / 0.03 | Gaussian 35% DD centering + Amihud | Expected Shortfall (CVaR) substitution |
| **18** | Inst & Foreign Sector | `src/core/inst_foreign_sector.py` | Flow | `inst_foreign_sector_score` | 0.04 / 0.04 / 0.05 | Separate Foreign/Trust 40d tracking | Institutional broker concentration index |
| **19** | Supply Chain Momentum | `src/core/supply_chain.py` | Factor | `supply_chain_score` | 0.01 / 0.01 / 0.03 | Lead customer 1D/3D return spillover | Dynamic customer revenue dependency weight |
| **20** | NLP Sentiment Catalyst | `src/core/llm_sentiment_engine.py` | Sentiment | `sentiment_score` | 0.03 / 0.03 / 0.03 | Domain-specific lexicon + Missing NaN | Sentence-level FinBERT embeddings |
| **21** | Style Neutralizer | `src/core/multi_factor_neutralizer.py` | Factor | `factor_neutralized_score` | 0.03 / 0.03 / 0.03 | 5-Factor cross-sectional OLS residual | WLS weighted by square-root market cap |
| **22** | Volatility Targeting | `src/core/vol_target.py` | Factor | `vol_target_score` | 0.05 / 0.03 / 0.02 | EWMA $\lambda=0.94$ + 5% volatility floor | GARCH(1,1) volatility forecasting |
| **23** | Microstructure Imbalance | `src/core/hft_engine.py` | Factor | `microstructure_score` | 0.02 / 0.03 / 0.03 | Bar CLV + Closing auction acceleration | Level-2 depth order imbalance |
| **24** | Accruals Quality | `src/core/accruals_quality.py` | Factor | `accruals_quality_score` | 0.04 / 0.03 / 0.01 | Sloan ratio + No artificial OCF impute | Dechow-Dichev working capital model |
| **25** | Short Interest Squeeze | `src/core/short_interest_squeeze.py` | Catalyst | `short_squeeze_score` | 0.01 / 0.02 / 0.04 | Short Ratio $\times$ DTC $\times (1+2R_{5d})$ | Loanable inventory fee rate tracking |
| **26** | Value-Up Catalyst | `src/core/valueup_catalyst.py` | Valuation | `valueup_catalyst_score` | 0.04 / 0.03 / 0.01 | Low PBR ($<1.0$) + Net Cash + Div Yield | 3Y historical treasury share cancellation |
| **27** | Kaufman Efficiency | `src/core/trend_efficiency.py` | Factor | `trend_efficiency_score` | 0.01 / 0.01 / 0.04 | Multi-window KER + R/S Hurst filter | Wavelet multiresolution noise threshold |
| **28** | Options Gamma Squeeze | `src/core/gamma_squeeze.py` | Options | `gamma_squeeze_score` | 0.01 / 0.02 / 0.04 | Call Wall proximity ($<3\%$) + GEX | Multi-strike full dealer gamma profile |
| **29** | Insider Buying | `src/core/insider_buying.py` | Catalyst | `insider_buying_score` | 0.02 / 0.03 / 0.03 | C-Suite open market buy vs disposal | Transaction size relative to market cap |
| **30** | Earnings Tone Drift | `src/core/earnings_tone_drift.py` | Sentiment | `earnings_tone_drift_score` | 0.02 / 0.02 / 0.02 | Polarity $\Delta$ tone $\times$ confidence | Acoustic audio tone and cadence analysis |
| **31** | High-Frequency Block | `src/core/hft_engine.py` | Microstructure | `darkpool_score` | 0.02 / 0.03 / 0.03 | Dark pool ratio + Almgren-Chriss impact | FINRA TRF real-time feed integration |

---

## 4. Empirical Test Suite Validation & Forensic Findings

A full execution of the 730-test master verification suite was performed:
- **Passing Tests**: 728 / 730 ($99.73\%$ pass rate) across unit, integration, stress, and forensic suites (`test_m1_master_suite.py`, `test_factor_orthogonalization.py`, `test_hpo_and_2d_ensemble.py`, `test_stat_arb.py`, `test_vcp_detector.py`, etc.).
- **Discrepancies Observed**:
  1. `tests/test_phase5_expansion.py::test_earnings_tone_drift_engine`: The test expects column name `tone_drift_score`, whereas `EarningsToneDriftEngine` registers and outputs `earnings_tone_drift_score` matching the 31-strategy registry convention.
  2. `tests/test_phase1_improvements.py::test_sector_exposure_cap_bear_and_bull`: PortfolioAllocator renormalization behavior in bear markets renormalizes capped weights to $1.0$ (or un-allocated cash), while the legacy test asserts an un-normalized raw sum of $0.70$.

---

## 5. Key Recommendations & Implementation Roadmap for Downstream Specialists

1. **Surge Classifier Precision Boost**: Transition from static 0.20 probability cutoff to dynamic F1/Precision@K thresholds loaded from `models/optimal_thresholds.json` per horizon and market regime.
2. **Stat-Arb Cointegration Modernization**: Introduce Kalman Filter state-space dynamic $\beta_t$ tracking to accommodate structural shifts without triggering false stops.
3. **Sector Rotation Refinement**: Introduce 5-day reversal noise cancellation from 20-day momentum to prevent chasing climax tops.
4. **Gram-Schmidt vs Löwdin Adaptive Selection**: Automatically employ Löwdin Symmetric orthogonalization when strategy count $K > 15$ to preserve equal variance distribution, falling back to Weighted Modified Gram-Schmidt when high-conviction ML anchor weights dominate.
5. **Column Name Consistency**: Alias `tone_drift_score` $\leftrightarrow$ `earnings_tone_drift_score` in `EarningsToneDriftEngine` output DataFrame to satisfy legacy test assertions while maintaining registry uniformity.
