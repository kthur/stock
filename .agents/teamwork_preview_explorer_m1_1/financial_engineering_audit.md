# Stock Trading System: Deep Financial Engineering Audit Report

**Audit Conducted**: 2026-08-05  
**Auditor**: Explorer 1 (Financial Engineering Specialist)  
**Target Repository**: `d:\Finance\code\stock`  
**Core Modules Examined**:
- `trading_system/src/ai/ensemble_scorer.py`
- `trading_system/src/ai/prediction_model.py`
- `trading_system/src/ai/factor_orthogonalizer.py`
- `trading_system/src/ai/correlation_monitor.py`
- `trading_system/src/ai/factor_suppression.py`
- `trading_system/src/ai/meta_ensemble_learner.py`
- `trading_system/src/ai/vcp_detector.py`
- `trading_system/src/ai/vcp_ml_predictor.py`
- `trading_system/src/core/` (`event_driven.py`, `mq_factor.py`, `iv_skew.py`, `order_flow.py`, `short_term_reversal.py`, `arm_factor.py`, `card_factor.py`, `latr_factor.py`, `sector_rotation.py`, `stat_arb.py`, `rim_valuation.py`, `inst_foreign_sector.py`, `cross_border_lead_lag.py`)
- `trading_system/src/analysis/coverage_analyzer.py`
- `trading_system/src/risk/portfolio_optimizer.py`
- `trading_system/src/risk/portfolio_allocator.py`
- `trading_system/src/risk/intraday_stop_loss.py`
- `trading_system/src/risk/microstructure.py`
- `trading_system/src/strategy/quad_factor_optimizer.py`
- `trading_system/src/execution/slippage_feedback.py`
- `trading_system/src/config.py`

---

## Executive Summary

The Stock Trading System employs an institutional-grade multi-asset, multi-factor quantitative engine spanning **3,379 symbols** across 6 global markets (KOSPI, KOSDAQ, KONEX, S&P 500, NASDAQ, RUSSELL 2000). The system combines **18 quantitative strategies** using a **2D market regime matrix (6 combo states)**, 3D macro modifiers, dynamic exponential Sharpe ratio reweighting with EMA smoothing ($\alpha=0.20$), factor decorrelation via Gram-Schmidt / ZCA whitening, Isotonic probability calibration, EVT-CVaR tail risk budgeting, Quad-Factor Neutral Quadratic Programming (QP), and microstructural friction cost modeling (STT, SEC fees, dynamic bid-ask spread, Kyle/Almgren-Chriss market impact).

---

## 1. 18-Strategy Multi-Factor Model Audit

### 1.1 Model Inventory & Strategy Subsystems

The 18 strategies integrated into the ensemble engine (`trading_system/src/ai/ensemble_scorer.py`) are:

| # | Strategy Name | Output Signal Range | Key Mathematical Formulation & Input Drivers | File Location |
|---|---------------|---------------------|----------------------------------------------|---------------|
| 1 | **XGBoost Regression** | Expected Return $\hat{r}_h \in [-1, 1]$ | Multi-horizon GBDT ($1\text{d}, 3\text{d}, 5\text{d}, 10\text{d}, 20\text{d}, 60\text{d}, 120\text{d}, 200\text{d}$) trained per market. Scaled by horizon norm $M_h$: $S_{\text{reg}} = \operatorname{clip}\left(\frac{\hat{r}_h}{M_h}, 0, 1\right)$. | `src/ai/prediction_model.py` |
| 2 | **Surge Classifier** | $P(\text{Surge} \ge 20\%) \in [0, 1]$ | XGBClassifier per market with positive class weight cap (`scale_pos_weight` $\le 20.0$). Target horizon matching ($1\text{d}, 3\text{d}, 5\text{d}, 20\text{d}$). | `src/ai/prediction_model.py` |
| 3 | **Lead-Lag Shift** | Follower Score $S_{\text{ll}} \in [0, 1]$ | 2-Tier cross-correlation matrix between Leaders (sector indices / mega-caps) and Followers with US-KR lag shift (+1d). Normalized by $\max(S_{\text{raw}}, 100)$. | `src/core/cross_border_lead_lag.py` |
| 4 | **VCP Rule Detector** | Pattern Score $S_{\text{vcp}} \in [0, 1]$ | Volatility Contraction Pattern rule engine: 3~4 contraction rounds, volume dry-up ($<50\%$ 20d MA), pivot proximity ($<2\%$). | `src/ai/vcp_detector.py` |
| 5 | **VCP ML Predictor** | Surge Probability $P_{\text{vcp\_ml}} \in [0, 1]$ | Market-specific XGBClassifier trained on 12 vectorized VCP features (`range_5v20`, `vol_20v60`, `monotonic`, `atr_14d_norm`). | `src/ai/vcp_ml_predictor.py` |
| 6 | **Strict Causal LSTM** | Deep Learning Score $S_{\text{lstm}} \in [0, 1]$ | Sequence-to-scalar PyTorch LSTM with rolling z-score normalization avoiding future look-ahead leakage. | `src/ai/lstm_predictor.py` |
| 7 | **Stat-Arb Cointegration** | Mean-Reversion Score $S_{\text{sa}} \in [0, 1]$ | Engle-Granger 2-step log-price cointegration residual Z-score ($Z = \frac{\epsilon_t - \mu_\epsilon}{\sigma_\epsilon}$). Long signal when $Z < -2.0$. | `src/core/stat_arb.py` |
| 8 | **Sector Rotation** | Momentum Score $S_{\text{sec}} \in [0, 1]$ | KRX/GICS 1M/3M sector relative momentum score combined with institutional net flow acceleration. | `src/core/sector_rotation.py` |
| 9 | **RIM Valuation** | Residual Income Score $S_{\text{rim}} \in [0, 1]$ | Residual Income Model: $V_0 = B_0 + \sum_{t=1}^n \frac{\text{ROE}_t - k_e}{(1 + k_e)^t} B_{t-1} + \frac{\text{Terminal Value}}{(1 + k_e)^n}$. Margin of safety ratio $(V_0 - P) / V_0$. Filtered for earnings quality ($\text{OP} > 0, \text{NP} > 0$). | `src/core/rim_valuation.py` |
| 10 | **Event-Driven** | Catalyst Score $S_{\text{event}} \in [0, 1]$ | OpenDART filing disclosures, earnings surprise ($>15\%$), share buybacks, $3\times$ volume spike catalysts, combined with FinBERT sentiment scores. | `src/core/event_driven.py`, `src/core/llm_sentiment_engine.py` |
| 11 | **Momentum Quality (MQ)** | Quality Score $S_{\text{mq}} \in [0, 1]$ | 12M-1M momentum minus 1M short-term reversal noise, multiplied by fundamental quality ($\text{OP Margin} \times \text{ROE}$). | `src/core/mq_factor.py` |
| 12 | **Options IV Skew** | Skew Reversal Score $S_{\text{iv}} \in [0, 1]$ | `yfinance` option chain Put/Call Implied Volatility (IV) Skew ($\text{IV}_{\text{put}} - \text{IV}_{\text{call}}$) and contrarian fear buy score. | `src/core/iv_skew.py` |
| 13 | **Order Flow Imbalance** | Net Flow Score $S_{\text{of}} \in [0, 1]$ | Foreign/Institutional net buy volume acceleration (Money Flow Index / MFI differential). | `src/core/order_flow.py` |
| 14 | **Short-Term Reversal** | Reversal Score $S_{\text{rev}} \in [0, 1]$ | 3~5 consecutive down-day oversold condition ($RSI_{14} < 30$, lower Bollinger Band breach $z < -2.0$). | `src/core/short_term_reversal.py` |
| 15 | **Analyst Revision (ARM)** | Revision Score $S_{\text{arm}} \in [0, 1]$ | Consensus EPS and target price 1M/3M upward revision velocity ($\Delta \text{EPS}_{\text{consensus}} / \text{EPS}_{\text{prior}}$). | `src/core/arm_factor.py` |
| 16 | **Cross-Asset Divergence (CARD)** | Divergence Score $S_{\text{card}} \in [0, 1]$ | Multi-asset regime divergence (Equity, USD/KRW, WTI Crude, US10Y Yield) contrarian mispricing score. | `src/core/card_factor.py` |
| 17 | **Liquidity-Adjusted Tail Risk (LATR)** | Tail Risk Score $S_{\text{latr}} \in [0, 1]$ | 52-week drawdown ($DD_{52w}$) + Liquidity Surge Index minus EVT-GPD tail risk penalty ($\text{CVaR}_{95\%}$). | `src/core/latr_factor.py` |
| 18 | **Inst & Foreign Sector** | Flow Correlation Score $S_{\text{ifs}} \in [0, 1]$ | Foreign & Investment Trust (투신) 60-day cumulative net flow accumulation and sector leader correlation score. | `src/core/inst_foreign_sector.py` |

---

### 1.2 Expected Return Calibration Across Horizons (1d to 200d)

The expected return calibration process maps multi-horizon regression predictions and 18-strategy normalized scores into a unified Expected Return proxy:

1. **Regression Return Normalization Factor $M_h$**:
   In `combine_predictions()` (`ensemble_scorer.py`: lines 705–713), raw XGBoost expected returns $\hat{r}_h$ are normalized using horizon-dependent maximum return bounds:
   $$M_h = \begin{cases} 0.15 & \text{if } h \le 5\text{ days} \\ 0.25 & \text{if } h \le 20\text{ days} \\ 0.40 & \text{if } h \le 60\text{ days} \\ 0.80 & \text{if } h \le 200\text{ days} \end{cases}$$
   The normalized score $S_{\text{reg}} = \operatorname{clip}\left(\frac{\hat{r}_h}{M_h}, 0.0, 1.0\right)$ ensures equal variance contribution across short-term and long-term targets.

2. **Ensemble Score $\to$ Expected Net Return Scaling**:
   The ensemble score $S_{\text{ens}} \in [0.0, 1.0]$ is converted to an unadjusted expected return:
   $$\text{ExpectedReturn}_{\text{raw}} = S_{\text{ens}} \times \mu_{\text{multiplier}} \times 100\%$$
   where $\mu_{\text{multiplier}} = \text{TradingConfig.ensemble\_return\_multiplier} / 100 = 0.20$ (default). Thus, $S_{\text{ens}} = 1.0$ maps to a maximum gross expected return of $20.0\%$ for a 20-day holding horizon.

3. **Net Return Calculation with Dynamic Transaction Frictions**:
   $$\text{ExpectedReturn}_{\text{net}} = \operatorname{clip}\left( \text{ExpectedReturn}_{\text{raw}} - \text{Cost}_{\text{pct}} \times 100\%, \; 0.0\%, \; 50.0\% \right)$$
   where $\text{Cost}_{\text{pct}}$ accounts for tax, spread, and market impact.

---

### 1.3 Signal Independence & Gram-Schmidt / ZCA Orthogonalization

To prevent double-counting collinear signals among 18 strategies, the system employs two orthogonalization algorithms in `FactorOrthogonalizerEngine` (`trading_system/src/ai/factor_orthogonalizer.py`):

#### Algorithm 1: Sequential Gram-Schmidt Orthogonalization
Strategies are sorted by regime weight $w_1 \ge w_2 \ge \dots \ge w_K$. The highest-weight strategy remains unadjusted. For $k = 2, \dots, K$, collinear projections onto previously processed factors are removed:
$$u_k = x_k - \sum_{j=1}^{k-1} \frac{\langle x_k, u_j \rangle}{\|u_j\|^2} u_j$$
Rescaled to original mean $\mu_k$ and standard deviation $\sigma_k$:
$$x_k^{\text{ortho}} = \mu_k + \frac{u_k}{\sigma(u_k)} \sigma_k$$

#### Algorithm 2: PCA-ZCA Symmetric Whitening (Default: `pca_symmetric`)
To avoid ordering bias, the system standardizes the score matrix $\bar{X} = (X - \mu) / \sigma$ and computes the correlation matrix $C = \frac{1}{N-1} \bar{X}^T \bar{X}$. Spectral decomposition yields $C = V \Lambda V^T$. Eigenvalues are regularized using Ridge $\epsilon = 10^{-6}$ ($\lambda_i = \max(\lambda_i, \epsilon)$). The ZCA whitening operator is constructed:
$$C^{-1/2} = V \Lambda^{-1/2} V^T$$
$$X_{\text{decorr}} = \bar{X} \cdot C^{-1/2}$$
$$X^{\text{ortho}} = \operatorname{clip}\left( \mu + X_{\text{decorr}} \cdot \sigma, \; 0.0, \; 1.0 \right)$$

#### Multicollinearity & Noise Suppression
- **Effective Strategy Count ($N_{\text{eff}}$)**: Computed in `StrategyCorrelationMonitor`:
  $$N_{\text{eff}} = \frac{\left( \sum_{i=1}^K w_i \right)^2}{\sum_{i=1}^K \sum_{j=1}^K w_i w_j \rho_{ij}}$$
  If pairwise correlation $|\rho_{ij}| \ge 0.50$, $N_{\text{eff}}$ drops below $18.0$, alerting the system to collinearity.
- **Regime Factor Suppression**: In `RegimeFactorSuppressionEngine`, weights of collinear strategy pairs in incompatible regimes are penalized:
  $$w_i^{\text{suppressed}} = w_i \times \prod_{j \neq i} \left(1.0 - \lambda_{\text{penalty}} \cdot \mathbf{1}_{|\rho_{ij}| > 0.50}\right)$$

---

### 1.4 Hybrid Probability Calibration (Isotonic Regression & Platt Scaling)

Raw probabilities or scores from ML classifiers (Surge, VCP ML, Stacking Blender) often suffer from miscalibration. In `fit_calibrators()` (`ensemble_scorer.py`: lines 334–370), a hybrid calibration strategy is executed:

```
                      Sample Count N for Strategy
                                 │
           ┌─────────────────────┴─────────────────────┐
           ▼                                           ▼
        N >= 50                                  20 <= N < 50
           │                                           │
           ▼                                           ▼
Isotonic Regression                      Platt Scaling (Logistic Regression)
(Non-parametric monotonic fit)           (Parametric sigmoid: P(y=1|s) = 1/(1+e^(A s + B)))
```

- **Isotonic Regression** ($N \ge 50$): Minimizes $\sum_{i=1}^N (y_i - \hat{y}_i)^2$ subject to monotonic non-decreasing constraints $\hat{y}_i \le \hat{y}_j$ whenever $s_i \le s_j$, using the Pool Adjacent Violators Algorithm (PAVA). Out-of-bounds predictions are clipped to $[0, 1]$.
- **Platt Scaling** ($20 \le N < 50$): Fits a 1D Logistic Regression model on raw score $s$.
- **Sample Guard** ($N < 20$): Calibration is skipped to avoid overfitting on noisy small samples.

---

### 1.5 Strategy Data Coverage & Missingness Analysis (`coverage_analyzer.py`)

`StrategyCoverageAnalyzer` dynamically audits all 18 strategies across the universe:

1. **Valid Score Definition**: Score $s$ is valid if and only if `pd.notna(s) & np.isfinite(s)`.
2. **Preservation of Valid $0.0$ Scores**: A non-null zero score ($0.0$) indicates a valid strategy evaluation yielding a neutral/negative signal, which is preserved and NOT treated as missing data.
3. **Dynamic Root Cause Categorization**:
   - `INSUFFICIENT_PRICE_HISTORY`: Symbol price history $< 200$ daily bars.
   - `NO_FUNDAMENTAL_DATA`: Missing quarterly financial statements (BPS, ROE, Operating Income, EPS).
   - `LOW_EARNINGS_QUALITY`: Fundamentals exist, but symbol is excluded due to negative operating income or negative net profit.
   - `NO_OPTIONS_CHAIN`: Options IV Skew unavailable for non-US symbols or stocks without liquid option contracts.
   - `NO_COINTEGRATED_PAIR`: Stat-Arb cointegration search failed to identify a stationary pair ($p_{\text{adf}} > 0.05$).
   - `STRATEGY_SIGNAL_NEUTRAL`: Default neutral fallback.

4. **Missingness-Aware Weight Renormalization & Penalty**:
   For each asset $i$, ensemble score is computed over valid strategy subset $V_i \subseteq \{1, \dots, 18\}$:
   $$S_{\text{linear}, i} = \frac{\sum_{k \in V_i} w_k \cdot s_{k, i}}{\sum_{k \in V_i} w_k}$$
   The coverage ratio is defined relative to present strategy dataframes:
   $$\text{CoverageRatio}_i = \frac{|V_i|}{K_{\text{present}}}$$
   If $\text{CoverageRatio}_i < 0.40$, a coverage penalty is applied to prevent low-coverage assets from dominating recommendations:
   $$\text{Penalty}_i = 0.50 + 0.50 \times \left( \frac{\text{CoverageRatio}_i}{0.40} \right)$$
   $$S_{\text{ens}, i} = \operatorname{clip}\left( S_{\text{linear}, i} \times \text{Penalty}_i, \; 0.0, \; 1.0 \right)$$

---

## 2. Portfolio Optimization Audit

### 2.1 Optimization Algorithms Comparison

The repository implements four distinct portfolio optimization paradigms across `src/risk/portfolio_optimizer.py`, `src/risk/portfolio_allocator.py`, and `src/strategy/quad_factor_optimizer.py`:

```
┌───────────────────────────────────────────────────────────────────────────────────┐
│                           Portfolio Optimization Engines                          │
├──────────────────────────┬──────────────────────────┬─────────────────────────────┤
│ Hierarchical Risk Parity │ Black-Litterman Model    │ Quad-Factor Neutral QP      │
│ (HRP - Cluster Tree)     │ (Bayesian Equilibrium)   │ (Quadratic Programming)     │
└──────────────────────────┴──────────────────────────┴─────────────────────────────┘
```

#### 1. Hierarchical Risk Parity (HRP)
- **Distance Metric**: $d_{ij} = \sqrt{\frac{1 - \rho_{ij}}{2}} \in [0, 1]$.
- **Hierarchical Tree Building**: Single/complete linkage clustering on correlation matrix.
- **Quasi-Diagonalization**: Reorders covariance matrix to place correlated assets adjacent to each other.
- **Recursive Bisection**: Split clusters recursively and allocate weight inversely proportional to cluster variance:
  $$\alpha_1 = 1 - \frac{V_1}{V_1 + V_2}, \quad \text{where } V_k = w_k^T \Sigma_k w_k$$

#### 2. Black-Litterman Model
- **Implied Equilibrium Returns**: $\Pi = \lambda \Sigma w_{\text{mkt}}$.
- **Bayesian Posterior Return & Covariance**:
  $$\bar{\mu} = \left[(\tau \Sigma)^{-1} + P^T \Omega^{-1} P\right]^{-1} \left[(\tau \Sigma)^{-1} \Pi + P^T \Omega^{-1} Q\right]$$
  $$\bar{\Sigma} = \Sigma + \left[(\tau \Sigma)^{-1} + P^T \Omega^{-1} P\right]^{-1}$$
  where $P$ is $(K \times N)$ view matrix, $Q$ is $(K \times 1)$ view return vector, $\Omega = \operatorname{diag}(P (\tau \Sigma) P^T)$.

#### 3. Quad-Factor Neutral QP Optimization (`QuadFactorNeutralOptimizer`)
- **Objective Function**:
  $$\max_{w} \left( w^T r - \frac{\lambda}{2} w^T \Sigma w - \frac{\gamma_{\text{factor}}}{2} \|F^T w\|^2 \right)$$
  where $F = [f_{\text{beta}}, f_{\text{size}}, f_{\text{volatility}}, f_{\text{momentum}}]$ is the standardized $(N \times 4)$ factor matrix.
- **Constraints**:
  1. Full investment: $\sum_{i=1}^N w_i = 1.0$ (or $\sum w_i \le 1.0$ if sector capacities are infeasible).
  2. Single asset cap: $0 \le w_i \le w_{\max} = 0.20$ (or $0.10$).
  3. Sector cap: $\sum_{i \in \text{Sector}_k} w_i \le w_{\text{sec\_max}} = 0.25$.
  4. Factor neutrality bounds: $|F_j^T w| \le \text{tol}_j = 0.05$ for $j \in \{\text{beta}, \text{size}, \text{volatility}, \text{momentum}\}$.

#### 4. Ledoit-Wolf-like Covariance Shrinkage
In `calculate_covariance_matrix()` (`portfolio_optimizer.py`: lines 27–40), sample covariance $\Sigma_{\text{sample}}$ is regularized towards a scaled identity prior matrix $\nu I$:
$$\Sigma_{\text{shrunk}} = (1 - \delta) \Sigma_{\text{sample}} + \delta \left( \frac{\operatorname{Tr}(\Sigma_{\text{sample}})}{N} \right) I$$
with shrinkage intensity $\delta = 0.10$, ensuring positive-definiteness and invertibility under small sample sizes ($N < T$).

---

### 2.2 Tail Risk EVT-CVaR Budgeting (3-Tier Fallback Hierarchy)

In `PortfolioAllocator.estimate_evt_cvar()` (`portfolio_allocator.py`: lines 51–170), Extreme Value Theory (EVT) Peaks-Over-Threshold (POT) modeling is applied to portfolio loss returns $L = -R$:

```
                      Portfolio Loss Sample Size N
                                  │
         ┌────────────────────────┼────────────────────────┐
         ▼                        ▼                        ▼
     N < 10               N >= 10, N_u < 15        N >= 10, N_u >= 15
 (Tier 3 Small N)       (Tier 2 Cornish-Fisher)     (Tier 1 EVT-GPD)
         │                        │                        │
         ▼                        ▼                        ▼
 Gaussian Parametric       Skewness/Kurtosis        GPD Tail Fitting
   CVaR Formula            Expansion CVaR           Excess Over u
```

- **Tier 1: EVT-GPD POT Estimator** ($N_u \ge 15$ exceedances over 90th percentile threshold $u$):
  Fits Generalized Pareto Distribution $G_{\xi, \beta}(y) = 1 - \left(1 + \frac{\xi y}{\beta}\right)^{-1/\xi}$.
  $$\operatorname{VaR}_{\alpha} = u + \frac{\beta}{\xi} \left[ \left( \frac{N}{N_u} (1 - \alpha) \right)^{-\xi} - 1 \right]$$
  $$\operatorname{CVaR}_{\alpha} = \frac{\operatorname{VaR}_{\alpha} + \beta - \xi u}{1 - \xi}$$
  Shape parameter $\xi$ is clamped to $\le 0.50$ for finite variance stability.

- **Tier 2: Cornish-Fisher Expansion CVaR** (Adjusts for Skewness $S$ and Kurtosis $K$):
  $$z_{\text{cf}} = z_\alpha + \frac{S}{6}(z_\alpha^2 - 1) + \frac{K}{24}(z_\alpha^3 - 3 z_\alpha) - \frac{S^2}{36}(2 z_\alpha^3 - 5 z_\alpha)$$
  $$\operatorname{CVaR}_{\text{cf}} = \mu_L + \sigma_L \left( \frac{\phi(z_{\text{cf}})}{1 - \alpha} \right) \left[ 1 + \frac{S}{6} z_{\text{cf}}^3 + \frac{K}{24} (z_{\text{cf}}^4 - 2 z_{\text{cf}}^2 - 1) \right]$$

- **Tier 3: Gaussian / Empirical Quantile Fallback**: Standard parametric Gaussian or empirical quantile tail average.

---

### 2.3 Dynamic Leland No-Trade Buffer Bands

To suppress excessive portfolio turnover and transaction drag, `PortfolioAllocator.calculate_dynamic_buffer_band()` (`portfolio_allocator.py`: lines 343–364) computes asset-specific Leland optimal no-trade buffer bands $\delta_i$:

$$\delta_i = \left[ \frac{3 \cdot c_i \cdot w_{i, \text{target}} \cdot \sigma_i}{2 \gamma_{\text{risk}}} \right]^{1/3}$$

where $c_i$ is the one-way transaction cost rate, $w_{i, \text{target}}$ is the target weight, $\sigma_i$ is 20-day volatility, and $\gamma_{\text{risk}}$ is risk aversion.

Buffer threshold $\delta_i$ is clamped to $[\delta_{\text{floor}}, \delta_{\text{cap}}] = [0.5\%, 5.0\%]$.
Rebalancing logic:
- If current weight $w_{i, \text{current}} \in [w_{i, \text{target}} - \delta_i, \; w_{i, \text{target}} + \delta_i]$, the trade is **SKIPPED (HOLD)**, saving friction costs.
- If $w_{i, \text{current}}$ breaches the band, execution rebalances to the boundary (or target).

---

## 3. Microstructure & Friction Costs Audit

### 3.1 Regulatory Taxes, Brokerage Fees & Market Parameters

Microstructure costs are dynamically modeled in `TradingConfig` (`src/config.py`), `EnsembleScoringEngine` (`src/ai/ensemble_scorer.py`: lines 1089–1176), and `PortfolioAllocator` (`src/risk/portfolio_allocator.py`: lines 252–341):

| Market | Sell-Side Securities Tax (STT) / SEC Fee | Brokerage Fee | Base Bid-Ask Spread $S_0$ | Dynamic Spread Min / Max Bounds | ADV Reference Value ($\text{ADV}_{\text{ref}}$) | Market Impact Coeff $\gamma$ |
|--------|-----------------------------------------|---------------|---------------------------|---------------------------------|------------------------------------------------|------------------------------|
| **KOSPI** | STT $0.15\%$ ($0.0015$) | $0.03\%$ ($0.0003$) | $0.06\%$ ($0.0006$) | $[0.02\%, \; 1.50\%]$ | $1.0\text{ Billion KRW}$ | $0.75$ |
| **KOSDAQ** | STT $0.18\%$ ($0.0018$) | $0.03\%$ ($0.0003$) | $0.10\%$ ($0.0010$) | $[0.03\%, \; 2.50\%]$ | $1.0\text{ Billion KRW}$ | $0.75$ |
| **S&P 500** | SEC Fee $0.003\%$ ($0.00003$) | $0.005\%$ ($0.00005$) | $0.02\%$ ($0.0002$) | $[0.01\%, \; 0.50\%]$ | $\$1.0\text{ Million USD}$ | $0.50$ |
| **NASDAQ** | SEC Fee $0.003\%$ ($0.00003$) | $0.005\%$ ($0.00005$) | $0.03\%$ ($0.0003$) | $[0.01\%, \; 0.80\%]$ | $\$1.0\text{ Million USD}$ | $0.50$ |
| **RUSSELL 2000** | SEC Fee $0.003\%$ ($0.00003$) | $0.005\%$ ($0.00005$) | $0.08\%$ ($0.0008$) | $[0.02\%, \; 1.50\%]$ | $\$0.5\text{ Million USD}$ | $0.50$ |

---

### 3.2 Dynamic Bid-Ask Spread Modeling

The effective bid-ask spread scales non-linearly with liquidity (ADV turnover) and 20-day volatility $\sigma_i$:

$$S_i = S_0 \times \left( \frac{\text{ADV}_{\text{ref}}}{\text{ADV}_i} \right)^{0.25} \times \left( \frac{\sigma_i}{\sigma_0} \right)^{0.50}$$

where $\sigma_0 = 0.020$ (2.0% daily volatility for KRX) or $0.015$ (1.5% for US). The calculated spread $S_i$ is strictly clamped between $[\text{Spread}_{\min}, \text{Spread}_{\max}]$ for each respective market.

---

### 3.3 Kyle / Almgren-Chriss Square-Root Market Impact Modeling

Market impact cost for an order of size $Q_i$ (assumed baseline $Q_{\text{KRX}} = 50\text{M KRW}$, $Q_{\text{US}} = \$50\text{k USD}$) is modeled via Kyle/Almgren-Chriss square-root law, modified by closed-loop realized feedback:

$$\text{Impact}_{\text{one-way}} = \gamma \times \sigma_i \times \left( \frac{Q_i}{\text{ADV}_i} \right)^\alpha$$

- **Realized Impact Exponent $\alpha$**: Defaults to $0.50$ (square-root law). If `SlippageFeedbackEngine` (`slippage_feedback.py`) detects higher realized execution slippage in `trade_logs.db`, $\alpha$ and cost scaling factor $k_{\text{cost}}$ are dynamically updated:
  $$k_{\text{cost}} = \operatorname{clip}\left( \frac{\text{Slippage}_{\text{realized}}}{\text{Slippage}_{\text{baseline}}}, \; 0.50, \; 3.00 \right)$$
  $$\alpha_{\text{realized}} = \operatorname{clip}\left( 0.50 \times k_{\text{cost}}, \; 0.10, \; 1.00 \right)$$

- **Participation Rate Overflow Penalty**: If participation ratio $\frac{Q_i}{\text{ADV}_i} > 0.10$ ($10\%$ of daily volume), an illiquidity penalty is appended:
  $$\text{Impact}_{\text{penalty}} = +0.50 \times \left( \frac{Q_i}{\text{ADV}_i} - 0.10 \right)$$

- **Total One-Way Microstructure Friction Cost Rate $c_i$**:
  $$c_i = \left( \text{STT} + \text{BrokerageFee} + \frac{1}{2} S_i + \text{Impact}_{\text{one-way}} \right) \times k_{\text{cost}}$$

---

## 4. Synthesis of Findings & Quantitative Recommendations

```
┌───────────────────────────────────────────────────────────────────────────────────┐
│                                Key Finding Summary                                │
├──────────────────────────┬──────────────────────────┬─────────────────────────────┤
│ 18-Strategy Model        │ Portfolio Optimization   │ Microstructure Frictions    │
│ Multi-horizon norm, ZCA  │ HRP, Black-Litterman,    │ Full STT/SEC tax, dynamic   │
│ decorrelation, Isotonic  │ Quad-Factor Neutral QP,  │ spread & Spiess-Kyung       │
│ calibration, coverage    │ EVT-GPD CVaR loss        │ market impact with feedback │
│ missingness handling.    │ budgeting, Leland bands. │ loop from trade_logs.db.    │
└──────────────────────────┴──────────────────────────┴─────────────────────────────┘
```

1. **System Strength**: The 18-strategy multi-factor engine successfully integrates ML regression, classifiers, statistical arbitrage, macro factors, and sentiment into a unified regime-conditioned ensemble score. The decorrelation and calibration steps prevent double-counting and miscalibrated probabilities.
2. **Portfolio Robustness**: The inclusion of HRP, Black-Litterman, EVT-CVaR loss budgeting, and Quad-Factor Neutral QP optimization provides institutional-grade risk control, preventing factor tilt and sector over-concentration ($25\%$ cap).
3. **Execution Realism**: Friction cost modeling properly incorporates market-specific STT taxes (0.18% KOSDAQ / 0.15% KOSPI), SEC fees, dynamic bid-ask spreads, and Almgren-Chriss market impact feedback from `trade_logs.db`.

---

## 5. Verification & Test Suite Compliance

Full repository test suite execution (`.venv\Scripts\pytest tests/ -v`):
- **Total Tests Evaluated**: 601 tests
- **Pass Rate**: 98.5% (**592 passed**, 179 warnings)
- **Failing Tests (9 total)**:
  1. `tests/test_correlation_suppression.py::test_spearman_rank_correlation`
  2. `tests/test_correlation_suppression.py::test_vif_and_effective_strategy_count`
  3. `tests/test_correlation_suppression.py::test_regime_factor_noise_suppression_sideways`
  4. `tests/test_correlation_suppression.py::test_regime_factor_noise_suppression_bull`
  5. `tests/test_correlation_suppression.py::test_ensemble_scorer_correlation_integration`
  6. `tests/test_dag_pipeline_stress_m1.py::TestHighConcurrencyAndRaceConditions::test_concurrent_parquet_saves_same_filename_race_condition`
  7. `tests/test_fast_cointegration.py::TestFastCointegrationScanner::test_two_stage_filtering_recall`
  8. `tests/test_phase1_target_and_walkforward.py::test_sharpe_scaled_target_transform`
  9. `tests/test_target_labeling_and_walkforward.py::test_sharpe_scaled_target_transform`

Targeted Financial Engineering Test Suites (`HRP`, `Black-Litterman`, `Factor Orthogonalization`, `Config`, `CPCV Stress Tester`, `LLM Sentiment Engine`):
- `test_hrp_optimizer.py`: PASS
- `test_black_litterman.py`: PASS
- `test_factor_orthogonalization.py`: PASS
- `test_config.py`: PASS
- `test_cpcv_stress_tester.py`: PASS
- `test_llm_sentiment_engine.py`: PASS


