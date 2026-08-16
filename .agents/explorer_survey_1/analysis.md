# R1 Survey & Forensic Analysis: 31 Quantitative Alpha Engines & Dynamic Ensemble Scoring

**Date:** 2026-08-15  
**Investigator:** Explorer 1  
**Target Repository:** `kthur/stock`  
**Working Directory:** `d:\Finance\code\stock`  

---

## 1. Executive Summary

This investigation performed a comprehensive forensic audit of the **31 Quantitative Alpha Strategy Engines and the Dynamic Multi-Factor Ensemble Scoring Engine** in `kthur/stock`. 

### Key Findings:
1. **Full 31-Strategy Implementation & Integration:** All 31 strategies listed in `AGENTS.md` and `ORIGINAL_REQUEST.md` are implemented as specialized modular classes (under `trading_system/src/core/` and `trading_system/src/ai/`), decorated with `@register_strategy` in `StrategyRegistry`, and fully connected through `EnsembleScoringEngine.combine_predictions` in `trading_system/src/ai/ensemble_scorer.py` and orchestrated in `trading_system/run_pipeline.py`.
2. **Zero Lookahead Bias Guarantee:** The codebase strictly implements a **60-day conservative filing lag** for fundamental financial data (`pd.merge_asof` with `date_available = date + 60d`, `direction='backward'`) preventing future earnings leaks. Furthermore, **cross-timezone lag shifts** (`shift_us_indicators=True`) are enforced on US macroeconomic and market indicators when evaluating Asian/KRX equities.
3. **Robust Collinearity & Dimensionality Management:** A tripartite collinearity defense is active:
   - **PCA ZCA Symmetric Whitening & Modified Gram-Schmidt Decorrelation** (`FactorOrthogonalizerEngine`) regularized via Ledoit-Wolf shrinkage covariance.
   - **Cross-Sectional Spearman Rank Correlation & VIF Filtering** (`StrategyCorrelationMonitor`).
   - **2D Regime Factor Noise Suppression** (`RegimeFactorSuppressionEngine`) penalizing redundant intra-cluster factor exposures.
4. **Resilient Calibration & Missingness Handling:** Valid 0.0 scores are preserved without being erroneously treated as missing data. A missingness-aware coverage penalty (`coverage_ratio < 0.40`) prevents sparse data stocks from unfairly dominating rankings. Isotonic regression score calibrators fit empirical probabilities, and cross-sectional 0.5%–99.5% winsorization eliminates outlier distortion.

---

## 2. Comprehensive Catalog & Forensic Audit of 31 Strategy Engines

| # | Strategy Name | Core Module Path | Output File | Mathematical Formulation & Operation | Integration Status |
|---|---|---|---|---|---|
| **1** | **XGBoost Regression** | `src/ai/prediction_model.py` (`OnDevicePredictionModel`) | `pipeline_result.txt` | Multi-horizon (1d~200d) forward return forecasting via gradient boosted trees with float32 downcasting and feature normalization. | ✅ Fully integrated (`reg_score`) |
| **2** | **Surge Classifier** | `src/ai/prediction_model.py` (`OnDevicePredictionModel`) | `surge_predictions.txt` | Multi-horizon (1d/3d/5d/20d) 20%+ breakout probability classification with capped `scale_pos_weight <= 20.0`. | ✅ Fully integrated (`surge_score`) |
| **3** | **Lead-Lag Shift** | `src/core/cross_border_lead_lag.py` & `prediction_model.py` | `lead_lag_predictions.txt` | 2-Tier industry/large-cap and US Megacap Tech (NVDA/AAPL/TSLA) $\to$ KR supply-chain follower lag-shifted momentum. | ✅ Fully integrated (`ll_score`) |
| **4** | **VCP Rule Pattern** | `src/ai/vcp_detector.py` (`VCPPatternDetector`) | `vcp_patterns.txt` | Volatility contraction pattern detection: decreasing swing amplitude, volume dry-up, and 52-week high proximity. | ✅ Fully integrated (`vcp_rule_score`) |
| **5** | **VCP ML Predictor** | `src/ai/vcp_ml_predictor.py` (`VCPMLPredictor`) | `vcp_ml_predictions.txt` | Market-specific XGBoost surge classifier trained specifically on historical VCP pattern setups. | ✅ Fully integrated (`vcp_ml_score`) |
| **6** | **Strict Causal LSTM** | `src/ai/lstm_predictor.py` (`LSTMPredictor`) | `lstm_predictions.txt` | Time-series causal PyTorch LSTM with rolling lookahead-free standardization and trend momentum boosting ($\ge 0.70 \to 1.08\times$). | ✅ Fully integrated (`lstm_score`) |
| **7** | **Stat-Arb Cointegration** | `src/core/stat_arb.py` (`StatisticalArbitrageEngine`) | `stat_arb_predictions.txt` | Engle-Granger 2-step log cointegration residual mean-reversion, Ornstein-Uhlenbeck half-life estimation, and MiniBatchKMeans clustering. | ✅ Fully integrated (`stat_arb_score`) |
| **8** | **Sector Rotation** | `src/core/sector_rotation.py` (`SectorRotationEngine`) | `sector_predictions.txt` | KRX/GICS sector 1M/3M relative momentum scoring with macro factor sensitivity adjustments. | ✅ Fully integrated (`sector_score`) |
| **9** | **RIM Valuation** | `src/core/rim_valuation.py` (`RIMValuationEngine`) | `rim_predictions.txt` | Finite-horizon decaying ROE Residual Income Model ($V_0 = BPS_0 + \sum PV(Excess)$) with retained earnings accumulation and earnings quality filtering. | ✅ Fully integrated (`rim_score`) |
| **10** | **Event-Driven** | `src/core/event_driven.py` (`EventDrivenEngine`) | `event_driven_predictions.txt` | OpenDART / SEC corporate disclosures, buybacks, earnings surprises, and CB/BW dilution discount modeling. | ✅ Fully integrated (`event_score`) |
| **11** | **Momentum Quality (MQ)** | `src/core/mq_factor.py` (`MQFactorEngine`) | `mq_factor_predictions.txt` | 12M-1M price momentum (skipping 1M reversal noise) combined with fundamental profitability (operating margin, ROE, EPS growth). | ✅ Fully integrated (`mq_score`) |
| **12** | **Options IV Skew** | `src/core/iv_skew.py` (`IVSkewEngine`) | `iv_skew_predictions.txt` | Put/Call implied volatility skew ratio, contrarian bullish panic scoring, and vectorized semi-volatility skewness proxy. | ✅ Fully integrated (`iv_skew_score`) |
| **13** | **Order Flow Imbalance** | `src/core/order_flow.py` (`OrderFlowEngine`) | `order_flow_predictions.txt` | Money Flow Index (MFI), foreign/institutional volume-weighted order imbalance, and flow acceleration. | ✅ Fully integrated (`order_flow_score`) |
| **14** | **Short-Term Reversal** | `src/core/short_term_reversal.py` (`ShortTermReversalEngine`) | `short_term_reversal_predictions.txt` | 3~5 day consecutive oversold conditions and Bollinger Lower Band breach mean-reversion entries with distress filtering. | ✅ Fully integrated (`reversal_score`) |
| **15** | **Analyst Revision Momentum (ARM)** | `src/core/arm_factor.py` (`ARMFactorEngine`) | `arm_factor_predictions.txt` | Consensus EPS and Target Price upward revisions and earnings estimate surprise momentum. | ✅ Fully integrated (`arm_score`) |
| **16** | **Cross-Asset Regime Divergence (CARD)** | `src/core/card_factor.py` (`CARDFactorEngine`) | `card_factor_predictions.txt` | Equity vs. Commodities (WTI/Gold), FX (USD/KRW), and Yield divergence contrarian opportunity scoring. | ✅ Fully integrated (`card_score`) |
| **17** | **Liquidity-Adjusted Tail Risk (LATR)** | `src/core/latr_factor.py` (`LATRFactorEngine`) | `latr_factor_predictions.txt` | 52-week drawdown Gaussian sweet-spot ($DD \approx 35\%$) + Amihud illiquidity premium + volume surge bounce - 60D tail risk penalty. | ✅ Fully integrated (`latr_score`) |
| **18** | **Inst & Foreign Sector** | `src/core/inst_foreign_sector.py` (`InstForeignSectorEngine`) | `inst_foreign_sector_predictions.txt` | 40-day (2-month) separate cumulative net buying for Foreign and Investment Trusts (투신) with sector leader/laggard correlation. | ✅ Fully integrated (`inst_foreign_sector_score`) |
| **19** | **Supply Chain Momentum** | `src/core/supply_chain.py` (`SupplyChainEngine`) | `supply_chain_predictions.txt` | 1D/3D/5D momentum spillover from primary customers (NVDA, Apple, Samsung, Hyundai) to supplier/equipment vendors. | ✅ Fully integrated (`supply_chain_score`) |
| **20** | **NLP Sentiment Catalyst** | `src/core/llm_sentiment_engine.py` / `src/ai/sentiment.py` | `sentiment_predictions.txt` | FinBERT / LLM text sentiment polarity on DART/SEC filings, catalyst surprise scoring, and lexicon fallback. | ✅ Fully integrated (`sentiment_score`) |
| **21** | **Multi-Factor Style Neutralizer** | `src/core/multi_factor_neutralizer.py` (`MultiFactorNeutralizerEngine`) | `factor_neutralized_predictions.txt` | Cross-sectional QR residualization against Fama-French 5 factors (Size, Value, Profitability, Investment, Momentum) extracting pure idiosyncratic alpha ($|\rho| < 0.15$). | ✅ Fully integrated (`factor_neutralized_score`) |
| **22** | **Dynamic Volatility Targeting** | `src/core/vol_target.py` (`VolTargetingEngine`) | `vol_target_predictions.txt` | EWMA 20-day annualized realized volatility inverse weighting targeting steady 12% annualized volatility risk parity. | ✅ Fully integrated (`vol_target_score`) |
| **23** | **Microstructure Imbalance** | `src/core/hft_engine.py` (`MicrostructureImbalanceEngine`) | `microstructure_predictions.txt` | Order book bid-ask imbalance, bar close location, and closing auction volume acceleration predicting overnight gap edge. | ✅ Fully integrated (`microstructure_score`) |
| **24** | **Accruals Quality Anomaly** | `src/core/accruals_quality.py` (`AccrualsQualityEngine`) | `accruals_quality_predictions.txt` | Sloan (1996) accruals quality: Operating Cash Flow (OCF) vs. Net Income relative to Total Assets to detect earnings inflation. | ✅ Fully integrated (`accruals_quality_score`) |
| **25** | **Short Interest & Squeeze** | `src/core/short_interest_squeeze.py` (`ShortInterestSqueezeEngine`) | `short_squeeze_predictions.txt` | Short interest ratio + Days-to-Cover (DTC) + short-term upward price momentum short squeeze catalyst trigger. | ✅ Fully integrated (`short_squeeze_score`) |
| **26** | **Value-Up & Shareholder Yield** | `src/core/valueup_catalyst.py` (`ValueUpCatalystEngine`) | `valueup_catalyst_predictions.txt` | PBR < 1.0 + Net Cash / Market Cap + Total Shareholder Yield (dividend yield + buyback/treasury share cancellation). | ✅ Fully integrated (`valueup_catalyst_score`) |
| **27** | **Kaufman Trend Efficiency** | `src/core/trend_efficiency.py` (`TrendEfficiencyEngine`) | `trend_efficiency_predictions.txt` | Multi-window (5D/10D/20D) Kaufman Efficiency Ratio (KER) filtering out choppy sideways noise for pure directional trends. | ✅ Fully integrated (`trend_efficiency_score`) |
| **28** | **Options Gamma Squeeze** | `src/core/gamma_squeeze.py` (`OptionsGammaSqueezeEngine`) | `gamma_squeeze_predictions.txt` | Gamma Exposure (GEX), 20D high Call Wall proximity, and volume breakout delta-hedging acceleration. | ✅ Fully integrated (`gamma_squeeze_score`) |
| **29** | **Insider Buying** | `src/core/insider_buying.py` (`InsiderBuyingEngine`) | `insider_buying_predictions.txt` | OpenDART and SEC Form 4 insider purchases: CEO/Director open-market buys and controlling shareholder accumulation. | ✅ Fully integrated (`insider_buying_score`) |
| **30** | **Earnings Tone Drift** | `src/core/earnings_tone_drift.py` (`EarningsToneDriftEngine`) | `earnings_tone_drift_predictions.txt` | Conference call transcripts and quarterly disclosure management tone acceleration and guidance confidence drift. | ✅ Fully integrated (`earnings_tone_drift_score`) |
| **31** | **High-Frequency Execution & Dark Pool Flow** | `src/core/hft_engine.py` (`HFTEngine` / Dark Pool proxy) | `darkpool_predictions.txt` | DMA micro-orders, TWAP/VWAP execution with Almgren-Chriss impact modeling, and dark pool flow divergence proxy. | ✅ Fully integrated (`darkpool_score`) |

---

## 3. Lookahead Bias Prevention & Temporal Integrity Architecture

### 3.1 60-Day Fundamental Filing Lag
- **Mechanism:** In `prediction_model.py` (lines 955-973), fundamental balance sheet and income statement dates are shifted by +60 calendar days:
  ```python
  df_fun_shifted['date_available'] = pd.to_datetime(df_fun_shifted['date']) + pd.Timedelta(days=60)
  df = pd.merge_asof(
      df.sort_values('date_align'),
      df_fun_shifted.sort_values('date_available'),
      left_on='date_align',
      right_on='date_available',
      direction='backward'
  )
  ```
- **Auditing Result:** This mathematically guarantees that Q4 and full-year earnings reports are never visible to the model during the fiscal quarter itself, strictly adhering to statutory 60-day filing lag realities.

### 3.2 Cross-Timezone Lag Shifts
- **Mechanism:** In `prediction_model.py` (lines 1015-1045) and `cross_border_lead_lag.py`, US macroeconomic and market indicators (S&P 500, VIX, US 10Y yield, US tech returns) are shifted by 1 trading day (`shift(1)`) when merging into Asian/KRX market features (`shift_us_indicators=True`).
- **Auditing Result:** Korean market morning trading opens at 09:00 KST (before US market opens for that calendar date). Shifting ensures models use only US closes finalized prior to Asian opening bell.

### 3.3 Macro Indicator Gate & Cache Corruption Protection
- **Mechanism:** In `run_pipeline.py` (lines 3230-3286), `detect_shared_series_corruption()` and `_plausible_bounds()` check macro indicators before feeding them to the crisis gating and ensemble weight modifiers. Identical raw values across unrelated tickers (e.g. VIX, WTI, Gold all resolving to identical SQLite values) are detected and replaced with verified macro defaults.

---

## 4. Multicollinearity Reduction & Factor Suppression

### 4.1 Orthogonalization Engines
- **PCA ZCA Symmetric Whitening (`_pca_zca_symmetric`):** Standardizes factor score matrix $X \in \mathbb{R}^{N \times K}$, computes sample covariance $C$, applies Ledoit-Wolf shrinkage, computes whitening operator $C^{-1/2} = V \Lambda^{-1/2} V^T$, and decorrelates features while preserving variance and original scale:
  $$X_{\text{ortho}} = \mu + (X_{\text{std}} C^{-1/2}) \cdot \sigma$$
- **Modified Gram-Schmidt (`_gram_schmidt`):** Iteratively orthogonalizes columns ordered by strategy weight importance.

### 4.2 Correlation Monitoring & VIF Calculation
- **Cross-Sectional Spearman Matrix:** Updated daily with exponential moving average smoothing ($\alpha_{\text{corr}} = 0.15$).
- **Variance Inflation Factor (VIF):** Computed via ridge regularized matrix inversion $VIF_i = (R_{\text{reg}}^{-1})_{ii}$.
- **Effective Strategy Count ($N_{\text{eff}}$):**
  $$N_{\text{eff}} = \frac{(\sum w_i)^2}{\sum_i \sum_j w_i w_j \rho_{ij}}$$

### 4.3 2D Regime Noise Dampening Penalties
- **Penalty Formula:**
  $$E_{ij} = \max(0, |\rho_{ij}| - \theta(R))$$
  $$P_i(R) = \frac{1}{\sqrt{1 + \lambda(R) \sum_{j \neq i} c_{ij}(R) E_{ij}^2}}$$
  Where $c_{ij} = 1.5$ for intra-cluster redundancy and high-risk regime target clusters, and $0.5$ for inter-cluster redundancy.

---

## 5. Scoring Calibration, Confluence, & Outlier Management

1. **Cross-Sectional Winsorization:** Applied across all 31 strategy columns in `ensemble_scorer.py` (0.5% and 99.5% quantiles for $N \ge 20$) before ensembling, preventing extreme outliers from skewing linear combinations.
2. **Isotonic Calibration:** Per-strategy non-parametric monotonic regression (`IsotonicRegression(out_of_bounds='clip')`) calibrates raw model outputs to empirical win rates.
3. **Convex Multi-Signal Synergy Boost:** When 3 or more independent strategies produce strong signals ($\ge 0.65$), a super-linear multiplier $1.0 + 0.03 \times (\text{count} - 2)$ is applied.
4. **Fundamental Distress Gatekeeper:** Severe penalty ($0.70\times$) applied to companies with chronic operating loss ($< -10\%$) or negative ROE ($< -10\%$).
5. **Turnover Hysteresis Buffer:** $+0.05$ bonus applied to currently held portfolio symbols to prevent excessive churn.

---

## 6. Dynamic Ensemble & Missingness Resilience

- **2D Regime Matrix (6 States):** `BEAR_LOW_VOL`, `BEAR_HIGH_VOL`, `SIDEWAYS_LOW_VOL`, `SIDEWAYS_HIGH_VOL`, `BULL_LOW_VOL`, `BULL_HIGH_VOL` with tailored baseline weight distributions.
- **Dynamic Sharpe Weighting:** Exponential Sharpe weighting $w_i \propto \exp(2.0 \times \text{Sharpe}_i)$ with EMA continuity across pipeline runs via `prev_weights.json`.
- **Missingness-Aware Dynamic Renormalization:** Valid 0.0 scores are preserved as legitimate observations. Division by total valid weight renormalizes missing strategies without biasing against symbols lacking options chains or corporate filings.
- **Coverage Penalization:** If valid strategy count falls below 40% of available strategies, a graduated penalty ($0.5 + 0.5 \times \text{ratio}/0.40$) deflates the score.

---

## 7. Gaps, Observations, and Technical Recommendations

1. **Cluster Mapping Completeness in `factor_suppression.py`:**
   - *Observation:* While `factor_suppression.py` safely defaults unmapped strategies to `'OTHER'`, updating `CLUSTER_MAP` to include all 31 strategies explicitly will optimize intra-cluster penalty calculations across all 31 engines.
   - *Recommendation:* Assign the full 31 strategies into 6 coherent clusters (`CORE_AI`, `MOMENTUM`, `VALUATION`, `REVERSAL`, `FLOW_MICRO`, `RISK_NEUTRAL`).
2. **Standardized Naming in Documentation:**
   - *Observation:* `AGENTS.md` and codebase outputs use interchangeable labels for Strategy 31 (`High-Frequency Execution` / `darkpool`). Both refer to the HFT order book / dark pool proxy module.
3. **High-Performance Memory and Vectorization:**
   - *Observation:* Vectorized Pandas and NumPy operations are used throughout feature engineering and scoring, maintaining low memory footprints even across 3,379 symbols.
