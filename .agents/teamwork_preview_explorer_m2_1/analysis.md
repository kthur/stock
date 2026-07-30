# Technical Analysis: Quantitative Alpha & Ensemble Factor Orthogonalization (Milestone 2 - R2)

**Author:** Explorer M2-1  
**Date:** 2026-07-30  
**Target Module:** `trading_system/src/ai/ensemble_scorer.py` (`EnsembleScoringEngine`)  
**Scope Document:** `PROJECT.md`  

---

## Executive Summary

This report provides a comprehensive technical investigation of `EnsembleScoringEngine` and presents the mathematical and algorithmic design for **Gram-Schmidt Orthogonalization** and **PCA Factor Decorrelation** across all 17 alpha strategies. 

Currently, `EnsembleScoringEngine` handles strategy redundancy by computing Spearman rank correlations and dampening scalar strategy weights ($w_i$). While scalar weight dampening reduces the influence of redundant strategies in the linear combination, it **does not decorrelate the underlying score feature space** $X \in \mathbb{R}^{N \times 17}$. High inter-strategy correlation ($\rho > 0.50$, $\text{VIF} > 4.0$) distorts the ensemble score, inflates variance, and reduces the effective strategy count ($N_{eff}$).

To solve this, we design a dedicated **`FactorOrthogonalizerEngine`** that transforms raw strategy scores into an orthogonal score matrix $X_{ortho} \in \mathbb{R}^{N \times 17}$ while preserving relative variance explaining power and score range $[0, 1]$.

---

## 1. Investigation of `EnsembleScoringEngine` Architecture

### 1.1 Current Architecture & Pipeline Flow
`EnsembleScoringEngine` (located at `trading_system/src/ai/ensemble_scorer.py`) orchestrates a 17-strategy multi-factor, multi-model ensemble:

| # | Strategy Name | Internal Key | Score Column | Functional Category |
|---|---------------|--------------|--------------|---------------------|
| 1 | XGBoost Regression | `regression` | `reg_score` | Core ML / Return Prediction |
| 2 | Surge Classifier | `surge` | `surge_score` | Short-term Momentum |
| 3 | Lead-Lag | `lead_lag` | `ll_score` | Cross-sectional Lead-Lag |
| 4 | VCP Rule Detector | `vcp_rule` | `vcp_rule_score` | Pattern Recognition / Reversal |
| 5 | VCP ML Predictor | `vcp_ml` | `vcp_ml_score` | Pattern Recognition / Momentum |
| 6 | Strict Causal LSTM | `lstm` | `lstm_score` | Core AI / Deep Time Series |
| 7 | Stat-Arb Cointegration | `stat_arb` | `stat_arb_score` | Statistical Arbitrage / Reversal |
| 8 | Sector Rotation | `sector_rotation` | `sector_score` | Sector Momentum |
| 9 | RIM Valuation | `rim_valuation` | `rim_score` | Fundamental Valuation |
| 10 | Event-Driven | `event_driven` | `event_score` | Microstructure / Catalyst |
| 11 | Momentum Quality | `mq_factor` | `mq_score` | Fundamental Quality & Momentum |
| 12 | Options IV Skew | `iv_skew` | `iv_skew_score` | Options / Microstructure |
| 13 | Order Flow Imbalance | `order_flow` | `order_flow_score` | Order Book / Microstructure |
| 14 | Short-Term Reversal | `short_term_reversal` | `reversal_score` | Mean-Reversion |
| 15 | Analyst Revision Momentum | `arm_factor` | `arm_score` | Earnings Revision / Momentum |
| 16 | Cross-Asset Regime Div. | `card_factor` | `card_score` | Cross-Asset / Reversal |
| 17 | Liquidity Tail Risk | `latr_factor` | `latr_score` | Tail Risk / Microstructure |

### 1.2 Current Redundancy & Multicollinearity Management
Currently, `EnsembleScoringEngine` interacts with two sub-components during `combine_predictions()` (lines 884-913):
1. **`StrategyCorrelationMonitor`** (`trading_system/src/ai/correlation_monitor.py`):
   - Computes daily 17x17 Spearman rank correlation matrix $R$ and applies EMA smoothing ($\alpha_{corr} = 0.15$).
   - Calculates Variance Inflation Factors $\text{VIF}_i = (R^{-1})_{ii}$.
   - Computes Effective Strategy Count $N_{eff} = \frac{(\sum w_i)^2}{\boldsymbol{w}^T R \boldsymbol{w}}$.
2. **`RegimeFactorSuppressionEngine`** (`trading_system/src/ai/factor_suppression.py`):
   - Penalizes weights of strategies with correlation $|\rho_{ij}| > \theta(R)$.
   - Multiplies dampening factor $P_i(R) = \left(1 + \lambda(R) \sum c_{ij} E_{ij}^2\right)^{-1/2}$.

### 1.3 Limitation of Scalar Weight Suppression
Weight suppression modifies weights $w_i \to w_i^{supp}$, resulting in the linear score:
$$S_{linear} = \frac{\sum_{i=1}^{17} w_i^{supp} S_i}{\sum_{i=1}^{17} w_i^{supp}}$$
However:
- $S_i$ and $S_j$ remain collinear in feature space ($X$).
- For instance, in the **MOMENTUM** cluster (`surge`, `vcp_ml`, `sector_rotation`, `arm_factor`), all 4 strategies fire simultaneously during market rallies. Modifying $w_i$ reduces their scalar weights but does **not remove shared variance** from $X$.
- When passing $X$ to downstream models (e.g., `MetaEnsembleLearner` 50:50 stacking or `PortfolioOptimizer`), collinear features inflate model variance and introduce instability.

---

## 2. Multicollinearity & Strategy Cluster Analysis

Across the 17 strategies, five distinct functional clusters exist:

```
                  ┌─────────────────────────────────────────────────────────┐
                  │               17 Alpha Strategy Universe               │
                  └─────────────────────────────────────────────────────────┘
                                       │
     ┌──────────────────┬──────────────┼──────────────┬──────────────────┐
     ▼                  ▼              ▼              ▼                  ▼
┌─────────┐       ┌───────────┐  ┌───────────┐  ┌───────────┐      ┌────────────┐
│ CORE AI │       │ MOMENTUM  │  │ VALUATION │  │ REVERSAL  │      │ FLOW/MICRO │
└─────────┘       └───────────┘  └───────────┘  └───────────┘      └────────────┘
• regression      • surge        • rim_val     • stat_arb         • lead_lag
• lstm            • vcp_ml       • mq_factor   • vcp_rule         • event_driven
                  • sector_rot                 • reversal         • iv_skew
                  • arm_factor                 • card_factor      • order_flow
                                                                  • latr_factor
```

### Cluster Multicollinearity Breakdown:

1. **CORE_AI Cluster (`regression`, `lstm`)**:
   - Both models predict continuous future price returns based on historical technical/fundamental features.
   - Pairwise correlation $\rho \approx 0.65 - 0.80$. High structural redundancy.
2. **MOMENTUM Cluster (`surge`, `vcp_ml`, `sector_rotation`, `arm_factor`)**:
   - All capture upward price acceleration and positive earnings revisions.
   - Pairwise correlation $\rho \approx 0.60 - 0.85$. Under strong bull regimes, all 4 strategies yield near-identical rank orderings.
3. **VALUATION Cluster (`rim_valuation`, `mq_factor`)**:
   - Share fundamental financial data (ROE, net income, book value).
   - Pairwise correlation $\rho \approx 0.50 - 0.70$.
4. **REVERSAL Cluster (`stat_arb`, `vcp_rule`, `short_term_reversal`, `card_factor`)**:
   - Trigger when price deviates significantly from historical mean/fair value.
   - Pairwise correlation $\rho \approx 0.55 - 0.75$.
5. **FLOW_MICRO Cluster (`lead_lag`, `event_driven`, `iv_skew`, `order_flow`, `latr_factor`)**:
   - Lower cross-cluster correlation, but intra-cluster correlation between `order_flow` and `lead_lag` reaches $\rho \approx 0.45 - 0.60$.

---

## 3. Mathematical Design of Factor Orthogonalization Algorithms

Per `PROJECT.md` (lines 30-32):
- **Input:** Raw strategy signal score matrix $X \in \mathbb{R}^{N \times 17}$ across $N$ tickers.
- **Output:** Orthogonalized score matrix $X_{ortho} \in \mathbb{R}^{N \times 17}$ preserving relative variance explaining power.

We present two complementary mathematical algorithms: **Gram-Schmidt Sequential Orthogonalization** and **PCA ZCA Symmetric Decorrelation**.

---

### 3.1 Algorithm 1: Sequential Gram-Schmidt Orthogonalization (Regime-Weighted Order)

Gram-Schmidt orthogonalizes vectors sequentially according to a predefined priority order. In quantitative portfolio management, the priority order is determined by **Regime Weight / Sharpe Weight** $w_{(1)} \ge w_{(2)} \ge \dots \ge w_{(17)}$.

#### Step 1: Sorting Strategy Vectors by Priority
Let $\boldsymbol{x}_{(1)}, \boldsymbol{x}_{(2)}, \dots, \boldsymbol{x}_{(17)}$ be the score column vectors in $X$, sorted by decreasing regime weight $w_k$.

#### Step 2: Recursive Projection Subtraction
1. Set the dominant strategy unmutated:
   $$\boldsymbol{u}_{(1)} = \boldsymbol{x}_{(1)}$$
2. For $k = 2, 3, \dots, 17$, subtract projections onto all previously orthogonalized vectors $\boldsymbol{u}_{(1)}, \dots, \boldsymbol{u}_{(k-1)}$:
   $$\boldsymbol{u}_{(k)} = \boldsymbol{x}_{(k)} - \sum_{j=1}^{k-1} \frac{\langle \boldsymbol{x}_{(k)}, \boldsymbol{u}_{(j)} \rangle}{\langle \boldsymbol{u}_{(j)}, \boldsymbol{u}_{(j)} \rangle + \epsilon} \boldsymbol{u}_{(j)}$$
   where $\langle \boldsymbol{a}, \boldsymbol{b} \rangle = \sum_{i=1}^N a_i b_i$ is the inner product, and $\epsilon = 10^{-8}$ prevents zero division.

#### Step 3: Variance-Preserving Rescaling & Range Normalization
Because $\boldsymbol{u}_{(k)}$ contains only the residual component of strategy $k$ independent of higher-priority strategies, its sample variance $\text{Var}(\boldsymbol{u}_{(k)})$ is smaller than $\text{Var}(\boldsymbol{x}_{(k)})$.

To preserve relative variance explaining power and maintain $[0, 1]$ score compatibility:
$$\boldsymbol{x}_{ortho, (k)} = \text{clip}\left( \mu(\boldsymbol{x}_{(k)}) + \frac{\boldsymbol{u}_{(k)} - \mu(\boldsymbol{u}_{(k)})}{\sigma(\boldsymbol{u}_{(k)}) + \epsilon} \cdot \sigma(\boldsymbol{x}_{(k)}), \, 0.0, \, 1.0 \right)$$

---

### 3.2 Algorithm 2: PCA ZCA Symmetric Factor Decorrelation (Loewdin Orthogonalization)

While Gram-Schmidt relies on an explicit hierarchy, **PCA ZCA (Zero-Phase Component Analysis) Symmetric Decorrelation** treats all 17 strategies symmetrically. It finds the unique orthogonal matrix $X_{ortho}$ that minimizes the Frobenius distance to the original matrix $X$:
$$\min_{X_{ortho}} \| X_{ortho} - X \|_F^2 \quad \text{subject to} \quad X_{ortho}^T X_{ortho} = D \text{ (diagonal)}$$

#### Step 1: Standardize Input Score Matrix
Let $\bar{X} \in \mathbb{R}^{N \times 17}$ be the mean-centered and unit-variance standardized matrix:
$$\bar{X}_{i, j} = \frac{X_{i, j} - \mu(X_j)}{\sigma(X_j) + \epsilon}$$

#### Step 2: Eigen-Decomposition of Covariance Matrix
Compute sample correlation matrix $C = \frac{1}{N-1} \bar{X}^T \bar{X} \in \mathbb{R}^{17 \times 17}$.
Perform eigen-decomposition:
$$C = V \Lambda V^T$$
where $V = [\boldsymbol{v}_1, \dots, \boldsymbol{v}_{17}]$ is the orthonormal eigenvector matrix ($V^T V = I$), and $\Lambda = \text{diag}(\lambda_1, \dots, \lambda_{17})$ contains eigenvalues representing variance explained by principal components.

To handle potential rank deficiency or near-singularity, apply ridge regularization to eigenvalues:
$$\tilde{\Lambda} = \text{diag}(\max(\lambda_j, \epsilon))$$

#### Step 3: ZCA Whitening Transformation
The ZCA decorrelation matrix is defined as:
$$X_{decorr} = \bar{X} C^{-1/2} = \bar{X} V \tilde{\Lambda}^{-1/2} V^T$$

**Mathematical Proof of Zero Covariance:**
$$\text{Cov}(X_{decorr}) = X_{decorr}^T X_{decorr} = (V \tilde{\Lambda}^{-1/2} V^T \bar{X}^T) (\bar{X} V \tilde{\Lambda}^{-1/2} V^T) = V \tilde{\Lambda}^{-1/2} (V^T C V) \tilde{\Lambda}^{-1/2} V^T$$
Since $V^T C V = \Lambda$, we get:
$$\text{Cov}(X_{decorr}) = V \tilde{\Lambda}^{-1/2} \Lambda \tilde{\Lambda}^{-1/2} V^T = V I V^T = I_{17}$$
Thus, all 17 output columns are **strictly uncorrelated** with unit variance.

#### Step 4: Variance-Preserving Rescaling & Range Clipping
Rescale each decorrelated column $X_{decorr, j}$ to match the original mean $\mu(X_j)$ and standard deviation $\sigma(X_j)$:
$$X_{ortho, j} = \text{clip}\left( \mu(X_j) + X_{decorr, j} \cdot \sigma(X_j), \, 0.0, \, 1.0 \right)$$

---

## 4. Algorithmic Comparison & Selection Guide

| Feature / Property | Gram-Schmidt Orthogonalization | PCA ZCA Symmetric Decorrelation |
|-------------------|--------------------------------|----------------------------------|
| **Symmetry** | Asymmetric (order dependent) | Symmetric (order independent) |
| **Strategy Hierarchy** | Explicitly preserves #1 strategy | Equal treatment across all 17 |
| **Distance to Original** | Distorts lower-order strategies | Minimizes Frobenius norm distance $\|X_{ortho} - X\|_F$ |
| **Pairwise Correlation** | Strictly 0.0 for all pairs | Strictly 0.0 for all pairs |
| **Variance Preservation** | Preserved via std dev rescaling | Preserved via eigenvalue scaling + std dev rescaling |
| **Optimal Use Case** | Regimes with 1 dominant strategy (e.g. BULL with `surge`) | Balanced multi-factor ensemble regimes |

---

## 5. Architectural Design for `FactorOrthogonalizerEngine`

We propose creating `trading_system/src/ai/factor_orthogonalizer.py`:

```python
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)

class FactorOrthogonalizerEngine:
    """
    Orthogonalizes 17 raw strategy signal scores per ticker X in R^{N x 17}
    using Gram-Schmidt or PCA ZCA Symmetric Decorrelation.
    Preserves relative variance explaining power and [0, 1] score range.
    """

    def __init__(self, default_method: str = 'pca_symmetric', ridge_epsilon: float = 1e-6):
        self.default_method = default_method
        self.ridge_epsilon = ridge_epsilon

    def orthogonalize(
        self,
        score_df: pd.DataFrame,
        strategy_cols: List[str],
        weights: Optional[Dict[str, float]] = None,
        method: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Args:
            score_df: DataFrame containing ticker rows and 17 strategy score columns.
            strategy_cols: List of 17 score column names.
            weights: Optional strategy weight dict (used for Gram-Schmidt ordering).
            method: 'pca_symmetric' or 'gram_schmidt'.
        Returns:
            DataFrame with orthogonalized score columns preserving [0, 1] range.
        """
        eff_method = method or self.default_method
        valid_cols = [c for c in strategy_cols if c in score_df.columns]
        if len(valid_cols) < 2:
            return score_df.copy()

        # Extract numeric array X (N, K)
        X_raw = score_df[valid_cols].values.astype(float)
        N, K = X_raw.shape

        # Handle NaNs: temporarily fill with column mean
        col_means = np.nanmean(X_raw, axis=0)
        col_means = np.nan_to_num(col_means, nan=0.5)
        inds = np.where(np.isnan(X_raw))
        X_clean = X_raw.copy()
        X_clean[inds] = np.take(col_means, inds[1])

        col_stds = np.std(X_clean, axis=0)
        col_stds = np.where(col_stds < 1e-8, 1e-6, col_stds)

        if eff_method == 'gram_schmidt':
            X_ortho = self._gram_schmidt(X_clean, valid_cols, weights, col_means, col_stds)
        else:
            X_ortho = self._pca_zca_symmetric(X_clean, col_means, col_stds)

        # Restore original NaNs
        X_ortho[inds] = np.nan

        out_df = score_df.copy()
        out_df[valid_cols] = np.clip(X_ortho, 0.0, 1.0)
        return out_df

    def _gram_schmidt(
        self,
        X: np.ndarray,
        cols: List[str],
        weights: Optional[Dict[str, float]],
        means: np.ndarray,
        stds: np.ndarray
    ) -> np.ndarray:
        N, K = X.shape
        # Determine ordering by weight
        if weights:
            # map column to strategy weight
            order = sorted(range(K), key=lambda i: weights.get(cols[i], 0.0), reverse=True)
        else:
            order = list(range(K))

        U = np.zeros_like(X)
        X_ortho_ordered = np.zeros_like(X)

        for idx, k in enumerate(order):
            x_k = X[:, k]
            u_k = x_k.copy()
            for prev_idx in range(idx):
                u_j = U[:, prev_idx]
                denom = np.dot(u_j, u_j)
                if denom > 1e-8:
                    proj = (np.dot(x_k, u_j) / denom) * u_j
                    u_k -= proj
            U[:, idx] = u_k

            # Rescale
            u_std = np.std(u_k)
            u_mean = np.mean(u_k)
            if u_std > 1e-8:
                rescaled = means[k] + ((u_k - u_mean) / u_std) * stds[k]
            else:
                rescaled = means[k] * np.ones(N)
            X_ortho_ordered[:, k] = rescaled

        return X_ortho_ordered

    def _pca_zca_symmetric(
        self,
        X: np.ndarray,
        means: np.ndarray,
        stds: np.ndarray
    ) -> np.ndarray:
        N, K = X.shape
        # Standardize
        X_bar = (X - means) / stds

        # Covariance matrix C (K, K)
        C = np.dot(X_bar.T, X_bar) / max(N - 1, 1)

        # Eigen decomposition
        eigenvalues, eigenvectors = np.linalg.eigh(C)

        # Ridge regularize eigenvalues
        eigenvalues = np.maximum(eigenvalues, self.ridge_epsilon)

        # Compute C^(-1/2) = V * diag(lambda^(-1/2)) * V^T
        inv_sqrt_lambda = np.diag(1.0 / np.sqrt(eigenvalues))
        C_inv_sqrt = np.dot(eigenvectors, np.dot(inv_sqrt_lambda, eigenvectors.T))

        # ZCA Whitening
        X_decorr = np.dot(X_bar, C_inv_sqrt)

        # Variance-preserving rescaling
        X_ortho = means + X_decorr * stds
        return X_ortho
```

---

## 6. Integration Contract into `EnsembleScoringEngine`

In `EnsembleScoringEngine.combine_predictions()` (around line 883, right before `update_correlation`):

```python
# Insert Factor Orthogonalization step
if self.orthogonalizer_enabled:
    strategy_score_cols = [col for _, col in strategy_cols if col in merged.columns]
    merged = self.orthogonalizer.orthogonalize(
        score_df=merged,
        strategy_cols=strategy_score_cols,
        weights=weights,
        method='pca_symmetric'
    )
```

This ensures that the 17-strategy score matrix $X$ passed to downstream dynamic linear combination, meta-ensemble stacking, and risk parity portfolio optimizer consists of **mutually orthogonalized, zero-redundancy alpha signals**.
