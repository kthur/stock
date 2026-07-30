# Multicollinearity Suppression & Regime Dynamic Ensemble Analysis (R3)

**Author:** Explorer 3  
**Target:** Requirement 3 (R3: Multicollinearity Suppression & Regime Dynamic Ensemble across 17 Strategies)  
**Date:** 2026-07-30  
**Working Directory:** `D:\Finance\code\stock\.agents\explorer_r3_1`  

---

## Executive Summary

The Stock Trading System currently operates 17 multi-factor and multi-model quantitative strategies spanning machine learning regression, classification, pattern detection, valuation models, cross-asset macro indicators, and market microstructure. While `EnsembleScoringEngine` effectively implements 2D market regime matrix weighting, dynamic exponential Sharpe scaling, Isotonic probability calibration, and microstructure transaction cost deductions, it currently treats the 17 strategy signals as conditionally independent. 

Our investigation reveals that without real-time inter-strategy correlation monitoring, strategy signal redundancy (multicollinearity) causes severe factor clustering—particularly between momentum/breakout models (`surge`, `vcp_ml`, `sector_rotation`, `arm_factor`) during range-bound (sideways) markets, and between mean-reversion factors (`stat_arb`, `short_term_reversal`) during strong trend regimes. 

This analysis presents a comprehensive design for **Inter-Strategy Signal Correlation Monitoring**, **2D Regime-Based Dynamic Factor Noise Suppression**, and **Optuna HPO Integration**, providing exact mathematical formulations, software class structures, and pipeline execution flows.

---

## 1. Codebase Investigation Findings

### 1.1 Strategy Ensemble Architecture (`src/ai/ensemble_scorer.py`)
- **Strategy Universe (17 Strategies)**: `regression`, `surge`, `lead_lag`, `vcp_rule`, `vcp_ml`, `lstm`, `stat_arb`, `sector_rotation`, `rim_valuation`, `event_driven`, `mq_factor`, `iv_skew`, `order_flow`, `short_term_reversal`, `arm_factor`, `card_factor`, `latr_factor`.
- **Regime Weighting Scheme**:
  - *1D Regimes* (0: BEAR, 1: SIDEWAYS, 2: BULL).
  - *2D Regimes* (6 Combo States): `BEAR_LOW_VOL`, `BEAR_HIGH_VOL`, `SIDEWAYS_LOW_VOL`, `SIDEWAYS_HIGH_VOL`, `BULL_LOW_VOL`, `BULL_HIGH_VOL`.
  - *3D Macro Modifiers*: `LIQUIDITY_SQUEEZE`, `HIGH_YIELD_BULL`, `HIGH_YIELD_BEAR`, `INFLATION_SHOCK`, `YIELD_INVERSION`.
- **Dynamic Weight Adjustments**:
  $$w_{i, \text{dynamic}} = \frac{w_{i, \text{base}} \cdot \exp(\gamma \cdot \text{Sharpe}_i)}{\sum_{j=1}^{17} w_{j, \text{base}} \cdot \exp(\gamma \cdot \text{Sharpe}_j)}$$
  Followed by Exponential Moving Average (EMA) weight smoothing ($\alpha_{\text{smoothing}} = 0.2$) persisted to `models/prev_weights.json`.
- **Stacking Meta-Learner Blend**: 50:50 hybrid blend of linear score and `MetaEnsembleLearner` decision tree score.
- **Probability Calibration**: `fit_calibrators()` fits Isotonic Regression ($N \ge 50$) or Platt Scaling ($20 \le N < 50$) per strategy.
- **Missingness Renormalization**: Scores are dynamically normalized per stock by dividing by active non-NaN strategy weight sums.

### 1.2 Optuna Strategy Tuner (`src/ai/optuna_tuner.py`)
- `OptunaStrategyTuner` executes TimeSeriesSplit hyperparameter optimization for strategies 1-5 and `tune_regime_2d_weights()`.
- `tune_regime_2d_weights()` maximizes out-of-sample portfolio Sharpe ratios independently per 2D regime state. Parameters are saved to `models/tuned_params.json` and auto-loaded by `EnsembleScoringEngine`.

### 1.3 Risk Manager & Crisis Detector (`src/risk/risk_manager.py`)
- `CrisisDetector` monitors VIX, drawdown speed, volume spike ratios, trend breakdown, and macro indicators (USD/KRW, WTI, TNX, DXY) to assign `CrisisLevel` (`NONE`, `WATCH`, `ACTIVE`, `SEVERE`).
- `RiskManager` enforces portfolio exposure gating and position size scaling based on crisis levels.

### 1.4 Market Regime Detector (`src/analysis/regime_detector.py`)
- `MarketRegimeDetector` trains a Gaussian Mixture Model (GMM) on 10 macro features (S&P500 return/volatility, VIX, US10Y level, US10Y-US2Y yield spread, USD/KRW returns, KR/US 10Y spread, KR yield curve, WTI returns, inflation shock index).
- Outputs 2D regime combo labels and 3D macro conditions.

---

## 2. Inter-Strategy Signal Correlation & Multicollinearity Analysis

### 2.1 The Multicollinearity Problem in 17-Strategy Ensembling
Currently, `EnsembleScoringEngine` assumes strategy outputs are orthogonal. However, the 17 strategies naturally group into 5 functional factor clusters:

| Cluster | Strategies Included | Underlying Driving Alpha Factor |
|---|---|---|
| **1. Core AI / Time-Series** | `regression`, `lstm` | Deep/ML non-linear price history patterns |
| **2. Momentum & Breakout** | `surge`, `vcp_ml`, `sector_rotation`, `arm_factor` | Price momentum, trend continuation, earnings revisions |
| **3. Valuation & Quality** | `rim_valuation`, `mq_factor` | Fundamental safety margin, ROE, operating margin |
| **4. Mean-Reversion & Arb** | `stat_arb`, `vcp_rule`, `short_term_reversal`, `card_factor` | Residual mean-reversion, overbought/oversold bouncing |
| **5. Microstructure & Flow** | `lead_lag`, `event_driven`, `iv_skew`, `order_flow`, `latr_factor` | Foreign/institutional flow, options skew, tail risk |

When strategies within the same cluster (e.g. `surge` and `vcp_ml` in Cluster 2) output highly correlated prediction vectors ($\rho_{ij} > 0.70$), their linear combination double-counts the same underlying alpha signal. This creates:
1. **Unintended Factor Over-concentration**: Inflated weights on redundant factors.
2. **False Signal Amplification**: High confidence scores generated merely by duplicated logic.
3. **Elevated Drawdowns during Regime Shifts**: Failure to suppress redundant momentum during sideways chop.

### 2.2 Mathematical Formulation for Signal Correlation Monitoring

#### A. Daily Cross-Sectional Spearman Rank Correlation
For trading day $t$ across stock universe $K$, given prediction score vector $\mathbf{S}_i = [s_{i,1}, s_{i,2}, \dots, s_{i,K}]^T$ for strategy $i$:
$$\rho_{ij, t} = \frac{\sum_{k=1}^K (R_{i,k} - \bar{R}_i)(R_{j,k} - \bar{R}_j)}{\sqrt{\sum_{k=1}^K (R_{i,k} - \bar{R}_i)^2 \sum_{k=1}^K (R_{j,k} - \bar{R}_j)^2}}$$
where $R_{i,k} = \text{rank}(s_{i,k})$.

#### B. Rolling Correlation Matrix Smoothing
To prevent daily noise instability:
$$\mathbf{\bar{R}}_t = \alpha_{\text{corr}} \mathbf{\mathbf{R}}_t + (1 - \alpha_{\text{corr}}) \mathbf{\bar{R}}_{t-1}, \quad \alpha_{\text{corr}} = 0.15$$

#### C. Variance Inflation Factor (VIF) & Effective Strategy Count ($N_{\text{eff}}$)
For each strategy $i$, the Variance Inflation Factor $VIF_i$ measures multicollinearity severity against all other strategies:
$$VIF_i = \frac{1}{1 - R_i^2}$$
where $R_i^2$ is the coefficient of determination from regressing $\mathbf{S}_i$ on $\mathbf{S}_{-i}$.

The overall **Effective Strategy Count** ($N_{\text{eff}}$) of the 17-strategy ensemble is:
$$N_{\text{eff}} = \frac{\left( \sum_{i=1}^{17} w_i \right)^2}{\sum_{i=1}^{17} \sum_{j=1}^{17} w_i w_j \bar{\rho}_{ij}}$$
When all 17 strategies are perfectly uncorrelated ($\bar{\rho}_{ij} = 0$ for $i \neq j$), $N_{\text{eff}} = 17$. If high correlation exists, $N_{\text{eff}}$ drops significantly (e.g., $N_{\text{eff}} \approx 6.5$).

---

## 3. Regime-Based Dynamic Factor Noise Suppression Design

Different market regimes require suppressing distinct types of factor redundancy:

```
                  ┌──────────────────────────────────────────────┐
                  │          2D Market Regime Classification     │
                  └──────────────────────┬───────────────────────┘
                                         │
                 ┌───────────────────────┴───────────────────────┐
                 │                                               │
                 ▼                                               ▼
       SIDEWAYS REGIMES                                  BULL REGIMES
  (SIDEWAYS_LOW_VOL / HIGH_VOL)                    (BULL_LOW_VOL / HIGH_VOL)
  • False Breakout Noise High                      • Anti-trend Reversal Noise High
  • Suppress Momentum Cluster                      • Suppress Counter-trend Reversal
    (surge, vcp_ml, sector_rotation)                 (short_term_reversal, stat_arb)
  • Boost Stat-Arb & RIM Valuation                 • Boost Acceleration & Trend
                 │                                               │
                 └───────────────────────┬───────────────────────┘
                                         │
                                         ▼
                               HIGH VOLATILITY REGIMES
                              (vix_val >= 20.0 or HIGH_VOL)
                              • Low-Liquidity Factor Decay
                              • Suppress High-Beta Collinear Factors
                              • Preserve Tail Risk (LATR) & Stat-Arb
```

### 3.1 Regime-Specific Suppression Behavior Matrix

| 2D Regime State | High Risk Redundant Cluster | Target Suppressed Factors | Preserved / Amplified Factors |
|---|---|---|---|
| **SIDEWAYS_LOW_VOL** | Momentum & Breakout | `surge`, `vcp_ml`, `sector_rotation` | `stat_arb`, `rim_valuation`, `mq_factor`, `vcp_rule` |
| **SIDEWAYS_HIGH_VOL** | Breakout & High-Beta | `surge`, `vcp_ml`, `order_flow` | `stat_arb`, `short_term_reversal`, `rim_valuation`, `card_factor` |
| **BULL_LOW_VOL** | Counter-Trend Reversal | `short_term_reversal`, `stat_arb` | `surge`, `vcp_ml`, `arm_factor`, `sector_rotation`, `mq_factor` |
| **BULL_HIGH_VOL** | Low-Liquidity Reversal | `short_term_reversal`, `lead_lag` | `surge`, `vcp_ml`, `latr_factor`, `event_driven` |
| **BEAR_LOW_VOL** | Overvalued Growth | `vcp_ml`, `sector_rotation`, `surge` | `regression`, `rim_valuation`, `stat_arb`, `card_factor` |
| **BEAR_HIGH_VOL** | All Uncalibrated Momentum | `surge`, `vcp_ml`, `sector_rotation`, `order_flow` | `regression`, `stat_arb`, `rim_valuation`, `card_factor`, `latr_factor` |

### 3.2 Mathematical Factor Dampening Penalty Algorithm

For strategy $i$ under 2D regime state $R$:

1. Compute pairwise correlation excess matrix $E_{ij}$:
   $$E_{ij} = \max(0, |\bar{\rho}_{ij}| - \theta(R))$$
   where $\theta(R) \in [0.50, 0.75]$ is the regime-specific correlation cutoff threshold.

2. Compute factor correlation penalty factor $P_i(R)$:
   $$P_i(R) = \frac{1}{\sqrt{1 + \lambda(R) \cdot \sum_{j \neq i} c_{ij}(R) \cdot E_{ij}^2}}$$
   where $\lambda(R) > 0$ is the regime dampening intensity parameter, and $c_{ij}(R) \in [0.5, 2.0]$ is a cluster relationship coefficient (higher penalty for intra-cluster redundancy than inter-cluster).

3. Apply penalty to exponential Sharpe dynamic weights $w_i^{\text{sharpe}}$:
   $$\tilde{w}_i = w_i^{\text{sharpe}} \cdot P_i(R)$$

4. Renormalize final weights:
   $$w_i^{\text{final}} = \frac{\tilde{w}_i}{\sum_{k=1}^{17} \tilde{w}_k}$$

---

## 4. Integration Architecture Design

### 4.1 System Component Overview

```
                      [Stock Universe Prices & Fundamentals]
                                        │
                                        ▼
                           MarketRegimeDetector (GMM)
                                        │
                                        ▼ 2D Regime (e.g. SIDEWAYS_HIGH_VOL)
 17 Strategy Engines ────────► StrategyCorrelationMonitor
 (reg, surge, ll, ...)                  │
                                        ▼ 17x17 Correlation Matrix R & VIFs
                              RegimeFactorSuppressionEngine
                                        │ (Applies θ(R), λ(R), P_i(R))
                                        ▼
                               OptunaStrategyTuner ──► Tunes θ(R), λ(R), W_2D in tuned_params.json
                                        │
                                        ▼
                             EnsembleScoringEngine
                                        │ (Linear + MetaEnsembleLearner 50:50)
                                        ▼
                          Microstructure Cost & Liquidity Gate
                                        │
                                        ▼ Net Expected Return Predictions
```

### 4.2 Class Specifications

#### Component A: `StrategyCorrelationMonitor` (`src/ai/correlation_monitor.py`)
```python
class StrategyCorrelationMonitor:
    """Computes daily cross-sectional Spearman rank correlation matrix R,

    rolling correlation history, VIF per strategy, and effective strategy count N_eff.
    """
    def __init__(self, window: int = 20, alpha_corr: float = 0.15):
        self.window = window
        self.alpha_corr = alpha_corr
        self.rolling_corr_matrix: Optional[pd.DataFrame] = None

    def update_correlation(self, strategy_scores_df: pd.DataFrame) -> pd.DataFrame:
        # Extract rank correlation across 17 strategy score columns
        ...

    def compute_vif(self) -> Dict[str, float]:
        # Compute Variance Inflation Factor per strategy
        ...

    def compute_effective_strategy_count(self, weights: Dict[str, float]) -> float:
        # Compute N_eff = (sum w_i)^2 / sum(w_i w_j rho_ij)
        ...
```

#### Component B: `RegimeFactorSuppressionEngine` (`src/ai/factor_suppression.py`)
```python
class RegimeFactorSuppressionEngine:
    """Applies 2D regime-based factor noise suppression penalties to raw Sharpe dynamic weights

    based on inter-strategy signal correlation matrix R.
    """
    CLUSTER_MAP = {
        'CORE_AI': ['regression', 'lstm'],
        'MOMENTUM': ['surge', 'vcp_ml', 'sector_rotation', 'arm_factor'],
        'VALUATION': ['rim_valuation', 'mq_factor'],
        'REVERSAL': ['stat_arb', 'vcp_rule', 'short_term_reversal', 'card_factor'],
        'FLOW_MICRO': ['lead_lag', 'event_driven', 'iv_skew', 'order_flow', 'latr_factor']
    }

    def suppress_weights(
        self,
        base_weights: Dict[str, float],
        corr_matrix: pd.DataFrame,
        regime_label: str,
        theta: float = 0.65,
        lambda_penalty: float = 1.0
    ) -> Dict[str, float]:
        ...
```

#### Component C: Extended `OptunaStrategyTuner` (`src/ai/optuna_tuner.py`)
- Add method `tune_correlation_suppression_params()` to tune regime-specific correlation thresholds $\theta(R) \in [0.40, 0.80]$ and dampening intensities $\lambda(R) \in [0.20, 2.50]$ alongside 2D regime weights.
- Store tuned parameters under key `'correlation_suppression'` in `models/tuned_params.json`.

#### Component D: Enhanced `EnsembleScoringEngine` (`src/ai/ensemble_scorer.py`)
- Integrate `StrategyCorrelationMonitor` and `RegimeFactorSuppressionEngine` directly into `calculate_ensemble_score()` flow.
- Record correlation metrics ($N_{\text{eff}}$, top collinear pairs) into `attrs['correlation_report']` and log decision rationale summaries.

---

## 5. Verification & Test Plan

1. **Unit Verification (`tests/test_correlation_suppression.py`)**:
   - Verify `StrategyCorrelationMonitor` returns symmetric positive semi-definite $17 \times 17$ matrix with unit diagonals.
   - Verify `RegimeFactorSuppressionEngine` correctly reduces weights for collinear momentum pairs ($\rho > 0.70$) under `SIDEWAYS` regimes while preserving `stat_arb` and `rim_valuation`.
   - Verify $N_{\text{eff}}$ calculation matches theoretical limits ($1.0 \le N_{\text{eff}} \le 17.0$).

2. **Integration Verification**:
   - Run pipeline execution check with 17 strategies enabled and verify `strategy_data_coverage_report.txt` and decision rationale in `ensemble_predictions.txt` accurately reflect correlation suppression metrics.

---

## 6. Summary of Actionable Implementation Steps (For Implementer Agent)

1. Create `src/ai/correlation_monitor.py` implementing `StrategyCorrelationMonitor`.
2. Create `src/ai/factor_suppression.py` implementing `RegimeFactorSuppressionEngine`.
3. Update `src/ai/ensemble_scorer.py` to ingest correlation suppression during dynamic weight calculation.
4. Update `src/ai/optuna_tuner.py` to include correlation suppression parameters in `tuned_params.json`.
5. Add comprehensive test suite in `tests/test_correlation_suppression.py`.
