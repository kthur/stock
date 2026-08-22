# Requirement R1 Technical Survey & Architectural Design Report
**Document ID**: `SURVEY-R1-31STRAT-NORM-20260822`  
**Target Requirement**: R1. 31-Strategy Score Scale Normalization & Missing Signal Re-normalization  
**Author**: `explorer_survey_1` (Teamwork Explorer)  
**Date**: 2026-08-22  
**Status**: COMPLETE / TECHNICAL SPECIFICATION  

---

## 1. Executive Summary

### 1.1 Problem Statement
The stock trading system incorporates **31 multi-factor and multi-model quantitative strategies** across five major equity markets (SP500, NASDAQ, RUSSELL2000, KOSPI, KOSDAQ). In the current implementation, predictions from these 31 strategies are merged into `EnsembleScoringEngine` (`trading_system/src/ai/ensemble_scorer.py`), processed through `FactorOrthogonalizerEngine` (`src/ai/factor_orthogonalizer.py`) and `RegimeFactorSuppressionEngine` (`src/ai/factor_suppression.py`), and aggregated into a linear/hierarchical ensemble score.

Forensic examination of the codebase reveals two critical structural flaws:
1. **Severe Score Scale & Variance Disparities**: Raw strategy signals originate from wildly disparate mathematical domains—including continuous expected returns (clipped at $20\times$), highly skewed class probabilities ($\text{mean} \approx 0.08$), unbounded cointegration Z-scores, unbounded residual income valuation discounts ($-90\%$ to $+500\%$), and polarity sentiment scores ($-1.0$ to $+1.0$). When combined or orthogonalized without cross-sectional distribution normalization, high-variance strategies overwhelmingly dominate portfolio selection, destroying the intended 2D market regime factor allocations.
2. **Artificial Default Injection & Weight Distortion**: In multiple pipeline stages and core strategy engines, uncalculated, unavailable, or missing strategy signals are assigned hardcoded default values of `0.50` (or `0.5` via `.fillna(0.50)`). Because `0.50` is a valid floating-point number, downstream dynamic weighting treats missing signals as actual mediocre signals rather than "NO DATA", pulling high-conviction alphas toward $0.50$, contaminating covariance matrices, and preventing genuine ticker-level active factor re-normalization.

### 1.2 Proposed Resolution
1. **Cross-Sectional Percentile Rank / Winsorized Gaussian Z-Score Normalizer**: Introduce a standardized normalization engine that transforms all 31 active strategy signals into a unified distribution (uniform $[0.0, 1.0]$ or Gaussian $\Phi(Z) \in [0.0, 1.0]$) per market partition prior to orthogonalization and ensemble weighting.
2. **Strict Missing Signal Zero-Weighting & Dynamic Re-normalization**: Purge all artificial `0.50` fallbacks across all 31 strategy modules and pipeline scripts. Maintain `np.nan` for all missing/uncalculated signals, dynamically set missing strategy weights to $0.0$ for each individual stock, and automatically re-normalize active weights so $\sum_{k \in \text{Active}(i)} \tilde{w}_{i,k} = 1.0$.

---

## 2. Comprehensive Inventory & Current State of all 31 Strategies

The table below catalogs all 31 strategies currently registered and evaluated in the pipeline:

| # | Strategy ID | Display Name | Native Output Type | Current Transformation in `ensemble_scorer.py` | Missing Value Handling in Strategy Engine | Scale Disparity Impact |
|---|---|---|---|---|---|---|
| **1** | `regression` | XGBoost Regression | Expected Return $\in [-0.20, +0.80]$ | `(expected_return * 20.0).clip(0.0, 1.0)` | Missing col $\to 0.5$ | Extreme: Returns $>5\%$ clip to 1.0; negative returns clip to 0.0; bimodal saturation |
| **2** | `surge` | Surge Classifier | Probability $\in [0.0, 1.0]$ | `.clip(0.0, 1.0)` | Missing col $\to 0.5$ | High skewness: Mean $\approx 0.08$, variance is suppressed relative to other factors |
| **3** | `lead_lag` | Lead-Lag Shift | Follower score $\in [0.0, 1.0]$ | `.clip(0.0, 1.0)` | Missing col $\to 0.5$ | Moderate |
| **4** | `vcp_rule` | VCP Rule Pattern | Pattern score $(0 \sim 100)$ or list | `/ 100.0` or `1.0`; `.clip(0.0, 1.0)` | Omitted $\to \text{NaN}$ | Binary/Sparse: Only matched stocks have signal |
| **5** | `vcp_ml` | VCP ML Predictor | Probability $\in [0.0, 1.0]$ | `.clip(0.0, 1.0)` | Missing col $\to 0.5$ | Moderate skewness |
| **6** | `lstm` | Strict Causal LSTM | Expected Return $\in [-0.10, +0.30]$ | `(expected_return * 20.0).clip(0.0, 1.0)` | Missing col $\to 0.5$ | Bimodal clipping at 0.0 and 1.0; 1.08x trend booster if $\ge 0.70$ |
| **7** | `stat_arb` | Statistical Arbitrage | Cointegration $Z \in (-\infty, +\infty)$ | `0.5 + min(0.40, z * 0.10 * z_mult)` or `(\|z\| / 3.0).clip(0.0, 1.0)` | Non-pair $\to$ omitted ($\text{NaN}$) | Highly sparse: Only cointegrated pairs present |
| **8** | `sector_rotation` | Sector Rotation | Momentum score $\in [0.0, 1.0]$ | `.clip(0.0, 1.0)` | Missing col $\to 0.5$ | Moderate |
| **9** | `rim_valuation` | RIM Valuation | Discount Ratio $(V_0 - P)/P \in [-0.90, +5.0]$ | Market Percentile Rank $[0.02, 0.98]$ + 1.05x MoS boost | Invalidation $\to \text{NaN}$ | Well-behaved: Already uses market percentile rank and $\text{NaN}$ invalidation |
| **10** | `event_driven` | Event-Driven | Score $\in [0.0, 1.0]$ | `.clip(0.0, 1.0)` | Missing $\to \text{NaN}$ (or empty) | Sparse |
| **11** | `mq_factor` | Momentum Quality | Score $\in [0.0, 1.0]$ | `.clip(0.0, 1.0)` | Missing $\to \text{NaN}$ | Composite score |
| **12** | `iv_skew` | Options IV Skew | IV Skew Score $\in [0.0, 1.0]$ | `.clip(0.0, 1.0)` | Missing $\to 0.50$ fallback | Fallback $0.50$ pollutes non-optionable / KR stocks |
| **13** | `order_flow` | Order Flow Imbalance | Score $\in [0.0, 1.0]$ | `.clip(0.0, 1.0)` | Missing $\to \text{NaN}$ | Moderate |
| **14** | `short_term_reversal`| Short-Term Reversal | Score $\in [0.0, 1.0]$ | `.clip(0.0, 1.0)` | Missing $\to \text{NaN}$ | Moderate |
| **15** | `arm_factor` | Analyst Revision (ARM) | Score $\in [0.0, 1.0]$ | `.clip(0.0, 1.0)` | Missing $\to \text{NaN}$ | Moderate |
| **16** | `card_factor` | Cross-Asset Divergence| Score $\in [0.0, 1.0]$ | `.clip(0.0, 1.0)` | Missing $\to \text{NaN}$ | Moderate |
| **17** | `latr_factor` | Liquidity Tail Risk | Score $\in [0.0, 1.0]$ | `.clip(0.0, 1.0)` | Missing $\to \text{NaN}$ | Moderate |
| **18** | `inst_foreign_sector`| Inst & Foreign Sector | Score $\in [0.0, 1.0]$ | `.clip(0.0, 1.0)` | Missing $\to \text{NaN}$ | Moderate |
| **19** | `supply_chain` | Supply Chain Momentum | Score $\in [0.0, 1.0]$ (or $0 \sim 100$) | `if max > 1.0: / 100.0; .clip(0.0, 1.0)` | Missing $\to \text{NaN}$ | Moderate |
| **20** | `sentiment` | NLP FinBERT Sentiment | Polarity $\in [-1.0, +1.0]$ or $[0, 1]$ | `if max > 1.0: / 100.0; .clip(0.0, 1.0)` | Missing $\to \text{NaN}$ | Truncation: Negative sentiment $[-1, 0]$ clips to $0.0$, losing negative information |
| **21** | `factor_neutralized` | Style Neutralizer | Pure Alpha Rank $\in [0.0, 1.0]$ | `if max > 1.0: / 100.0; .clip(0.0, 1.0)` | Missing $\to \text{NaN}$ | Percentile ranked |
| **22** | `vol_target` | Volatility Targeting | Risk Parity Score $\in [0.0, 1.0]$ | `if max > 1.0: / 100.0; .clip(0.0, 1.0)` | Missing $\to \text{NaN}$ | Moderate |
| **23** | `microstructure` | Microstructure Imbalance | Imbalance Score $\in [0.0, 1.0]$ | `if max > 1.0: / 100.0; .clip(0.0, 1.0)` | Missing $\to \text{NaN}$ | Moderate |
| **24** | `accruals_quality` | Accruals Quality | Sloan Accrual Ratio | `.fillna(0.50)` inside engine | Missing $\to 0.50$ fillna | Artificial $0.50$ prevents missing weight zeroing |
| **25** | `short_squeeze` | Short Squeeze Catalyst | Short Ratio $\times$ DTC | `.fillna(0.50)` inside engine | Missing $\to 0.50$ fillna | Artificial $0.50$ prevents missing weight zeroing |
| **26** | `valueup_catalyst` | Value-Up / Shareholder | PBR + ROE + Div + Cash | `.fillna(0.50)` inside engine | Missing $\to 0.50$ fillna | Artificial $0.50$ prevents missing weight zeroing |
| **27** | `trend_efficiency` | Trend Efficiency | Kaufman KER + Hurst | `.fillna(0.50)` inside engine | Missing $\to 0.50$ fillna | Artificial $0.50$ prevents missing weight zeroing |
| **28** | `gamma_squeeze` | Options Gamma Squeeze | GEX / Call Wall $\in [0.0, 1.0]$ | `if max > 1.0: / 100.0; .clip(0.0, 1.0)` | Fallback $0.50$ | Artificial $0.50$ baseline |
| **29** | `insider_buying` | Insider Buying Catalyst | Net Buy Score $\in [0.0, 1.0]$ | `if max > 1.0: / 100.0; .clip(0.0, 1.0)` | Fallback $0.50$ | Artificial $0.50$ baseline |
| **30** | `earnings_tone_drift`| Earnings Tone Drift | Tone Delta Score $\in [0.0, 1.0]$ | `if max > 1.0: / 100.0; .clip(0.0, 1.0)` | Fallback $0.50$ | Artificial $0.50$ baseline |
| **31** | `darkpool` | Dark Pool / HFT Flow | Proxy Score $\in [0.0, 1.0]$ | `if max > 1.0: / 100.0; .clip(0.0, 1.0)` | Fallback $0.50$ in pipeline | Artificial $0.50$ baseline |

---

## 3. Deep Analysis of Scale Disparities & Pipeline Distortions

### 3.1 Mathematical Analysis of Scale Heterogeneity
When combining $K$ strategy signals $\{X_1, X_2, \dots, X_K\}$ with weights $\{w_1, w_2, \dots, w_K\}$, the variance of the resulting ensemble score $S = \sum_{k=1}^K w_k X_k$ is:
$$\text{Var}(S) = \sum_{k=1}^K w_k^2 \text{Var}(X_k) + 2 \sum_{j < k} w_j w_k \text{Cov}(X_j, X_k)$$

If strategy $A$ has standard deviation $\sigma_A = 0.35$ (e.g. regression return clipped between 0 and 1) and strategy $B$ has standard deviation $\sigma_B = 0.05$ (e.g. surge classifier probability tightly concentrated near 0.05~0.15), then the variance contribution of strategy $A$ relative to $B$ is:
$$\frac{w_A^2 \sigma_A^2}{w_B^2 \sigma_B^2} = \left(\frac{w_A}{w_B}\right)^2 \times \left(\frac{0.35}{0.05}\right)^2 = 49 \times \left(\frac{w_A}{w_B}\right)^2$$
Even if the regime weight $w_B$ is larger than $w_A$, Strategy $A$ completely dominates the ensemble ranking simply because of its unscaled variance.

### 3.2 Impact on Factor Orthogonalization (`FactorOrthogonalizerEngine`)
In `src/ai/factor_orthogonalizer.py`:
1. The engine constructs matrix $X \in \mathbb{R}^{N \times K}$.
2. If columns have different native scales, their sample covariance $C = \frac{1}{N-1} X_{\text{std}}^T X_{\text{std}}$ operates on standardized values $X_{\text{std}} = (X - \mu) / \sigma$.
3. When restoring the orthogonalized matrix via Gram-Schmidt or PCA-ZCA:
   $$X_{\text{ortho}, k} = \mu_k + \frac{u_k}{\sigma(u_k)} \cdot \sigma_k$$
   the outputs retain their original column means $\mu_k$ and standard deviations $\sigma_k$.
4. Consequently, if `surge_score` had a mean of $0.08$ and `reg_score` had a mean of $0.55$, the orthogonalized values remain shifted around $0.08$ and $0.55$, causing downstream linear sum distortions.

### 3.3 The Artificial 0.50 Fallback Hazard
When a strategy lacks data for ticker $i$:
- **Ideal behavior**: $X_{i,k} = \text{NaN}$, $m_{i,k} = 0$, $w_{i,k}^{\text{eff}} = 0$. The score is computed using the remaining available strategies, with their weights normalized to sum to $1.0$.
- **Current buggy behavior**: $X_{i,k} = 0.50$. $m_{i,k} = 1$. The calculation computes $S_i = \dots + 0.50 \cdot w_k$.
  - For a top-tier stock with active signals averaging $0.85$, the missing strategy injects $0.50$, reducing its score by $(0.85 - 0.50) \cdot w_k$.
  - For a low-ranked stock with active signals averaging $0.15$, the missing strategy injects $0.50$, artificially inflating its score by $(0.50 - 0.15) \cdot w_k$.
  - Furthermore, in correlation monitoring (`StrategyCorrelationMonitor`) and covariance shrinkage, rows filled with $0.50$ generate zero-variance spikes and artificial spurious collinearity.

---

## 4. Target Architecture & Mathematical Specification

### 4.1 Cross-Sectional Score Normalizer Architecture

We specify a dedicated, high-performance normalization module: `CrossSectionalScoreNormalizer` located in `src/ai/score_normalizer.py` (and integrated directly into `EnsembleScoringEngine`).

#### Mathematical Formulas
For each strategy $k \in \{1, \dots, K\}$ and each market partition $M \in \{\text{KOSPI}, \text{KOSDAQ}, \text{SP500}, \text{NASDAQ}, \text{RUSSELL2000}\}$:
Let $V_k = \{X_{i,k} \mid i \in M, X_{i,k} \text{ is not NaN and finite}\}$, and $N_k = |V_k|$.

**Method 1: Cross-Sectional Percentile Ranking (Default & Recommended)**
$$X_{i,k}^{\text{norm}} = \frac{\text{Rank}(X_{i,k}) - 0.5}{N_k} \in [0.005, 0.995]$$
- **Rank Invariance**: Completely immune to monotonic non-linear distortions (e.g. exponential returns, log valuations, power-law distributions).
- **Uniform Variance**: Guarantees that every strategy has an identical theoretical variance $\text{Var}(X^{\text{norm}}) = \frac{1}{12} \approx 0.0833$, restoring exact proportionality to the 2D regime weights $w_k$.
- **NaN Preservation**: If $X_{i,k}$ is NaN, $X_{i,k}^{\text{norm}} = \text{NaN}$.

**Method 2: Cross-Sectional Winsorized Gaussian Z-Score CDF (Dispersion-Preserving Option)**
For strategies where exact tail extremity distance should be preserved:
1. Winsorize at $p_{1\%}$ and $p_{99\%}$:
   $$X_{i,k}^{\text{win}} = \text{clip}(X_{i,k}, q_{0.01}(V_k), q_{0.99}(V_k))$$
2. Compute robust median and Median Absolute Deviation (MAD):
   $$\text{Median}_k = \text{median}(X_{i,k}^{\text{win}}), \quad \text{MAD}_k = \text{median}(|X_{i,k}^{\text{win}} - \text{Median}_k|)$$
   $$\sigma_k^{\text{robust}} = \max(1.4826 \times \text{MAD}_k, 1e-6)$$
3. Compute robust Z-score:
   $$Z_{i,k} = \frac{X_{i,k}^{\text{win}} - \text{Median}_k}{\sigma_k^{\text{robust}}}$$
4. Map through standard normal Gaussian CDF $\Phi$:
   $$X_{i,k}^{\text{norm}} = \Phi(Z_{i,k}) = \frac{1}{2} \left[1 + \text{erf}\left(\frac{Z_{i,k}}{\sqrt{2}}\right)\right] \in (0, 1)$$

#### Market Partitioning Rules
- If $N_M \ge 10$, normalize independently within market partition $M$ (e.g., KOSPI stocks ranked only against KOSPI; SP500 ranked only against SP500).
- If $N_M < 10$, fallback to regional partition ($\text{KR} = \{\text{KOSPI}, \text{KOSDAQ}\}$, $\text{US} = \{\text{SP500}, \text{NASDAQ}, \text{RUSSELL2000}\}$) or global universe.

---

### 4.2 Dynamic Zero-Weighting & Active Re-normalization

#### Mathematical Formulation
For each ticker $i \in \{1, \dots, N\}$:
1. Base regime weights: $w_k^{(i)} = \begin{cases} w_k^{\text{KR}}(R) & \text{if } i \in \text{KRX} \\ w_k^{\text{US}}(R) & \text{if } i \in \text{US} \end{cases}$
2. Availability mask:
   $$m_{i,k} = \begin{cases} 1 & \text{if } X_{i,k}^{\text{norm}} \text{ is finite and not NaN} \\ 0 & \text{if } X_{i,k}^{\text{norm}} \text{ is NaN, None, or uncalculated} \end{cases}$$
3. Active weight sum:
   $$W_i = \sum_{k=1}^K m_{i,k} \cdot w_k^{(i)}$$
4. Dynamic Re-normalized strategy weight:
   $$\tilde{w}_{i,k} = \begin{cases} \frac{m_{i,k} \cdot w_k^{(i)}}{W_i} & \text{if } W_i > 0 \\ 0.0 & \text{if } W_i = 0 \end{cases}$$
   Note that $\sum_{k=1}^K \tilde{w}_{i,k} = 1.0$ whenever $W_i > 0$.
5. Weighted Linear Ensemble Score:
   $$S_i = \sum_{k=1}^K \tilde{w}_{i,k} X_{i,k}^{\text{norm}} = \frac{\sum_{k=1}^K m_{i,k} w_k^{(i)} X_{i,k}^{\text{norm}}}{W_i}$$
6. Quorum & Coverage Protection:
   $$\text{CoreCount}_i = \sum_{k \in \text{Core}} m_{i,k}, \quad \text{CoverageRatio}_i = \frac{\sum_{k=1}^K m_{i,k}}{K_{\text{effective}}}$$
   $$\text{Penalty}_i = \begin{cases} 0.70 + 0.30 \times \left(\frac{\text{CoverageRatio}_i}{0.25}\right) & \text{if } \text{CoreCount}_i < 3 \text{ and } \text{CoverageRatio}_i < 0.25 \\ 1.00 & \text{otherwise} \end{cases}$$
   $$S_i^{\text{penalized}} = \text{clip}(S_i \times \text{Penalty}_i, 0.0, 1.0)$$

---

## 5. Code Layout & Interface Specification

### 5.1 Affected Files & Exact Functions

| Source File | Function / Section | Line Numbers | Required Modification |
|---|---|---|---|
| `trading_system/src/ai/ensemble_scorer.py` | `combine_predictions` | Lines 1330–1835 | Remove all fallback `df['..._score'] = 0.5`; preserve empty DataFrames / NaNs for uncalculated strategies. |
| `trading_system/src/ai/ensemble_scorer.py` | `combine_predictions` (Phase 3-A) | Lines 1887–1897 | Replace raw quantile clipping with call to `CrossSectionalScoreNormalizer` before orthogonalization. |
| `trading_system/src/ai/ensemble_scorer.py` | `combine_predictions` (Linear scoring) | Lines 1998–2032 | Ensure `valid_mask` strictly checks `notna() & isfinite()`, correctly divides by `safe_weight_series`, and handles zero-weight cases. |
| `trading_system/src/ai/factor_orthogonalizer.py` | `orthogonalize` | Lines 44–90 | Ensure standardized inputs do not collapse dispersion; preserve NaNs strictly through PCA/Gram-Schmidt. |
| `trading_system/src/core/accruals_quality.py` | `calculate_scores` | Lines 145–148 | Remove `.fillna(0.50)`; return genuine `NaN` for symbols with missing financial statements. |
| `trading_system/src/core/valueup_catalyst.py` | `calculate_scores` | Lines 154–157 | Remove `.fillna(0.50)`; return genuine `NaN` for missing fundamental ratios. |
| `trading_system/src/core/short_interest_squeeze.py` | `calculate_scores` | Lines 144–146 | Remove `.fillna(0.50)`; return genuine `NaN` for symbols without short interest data. |
| `trading_system/src/core/trend_efficiency.py` | `calculate_scores` | Lines 150–152 | Remove `.fillna(0.50)`; return genuine `NaN` for symbols with insufficient price history. |
| `trading_system/src/core/insider_buying.py` | `compute_insider_buying_scores` | Lines 78–105 | Do not assign $0.50$ baseline to symbols with no filings; leave as `NaN` or omit from returned DataFrame. |
| `trading_system/src/core/earnings_tone_drift.py` | `compute_tone_drift_scores` | Lines 97–115 | Do not assign $0.50$ baseline to symbols with no conference call transcripts; leave as `NaN`. |
| `trading_system/src/core/iv_skew.py` | `compute_skew_for_ticker` / `compute_iv_skew_scores` | Lines 51, 89, 108 | Do not force $0.50$ on non-optionable / uncalculated symbols; allow `NaN`. |
| `trading_system/src/core/gamma_squeeze.py` | `calculate_scores` | Lines 110–127 | Allow `NaN` when neither price proxy nor options GEX is available. |
| `trading_system/run_pipeline.py` | Strategy 31 (Darkpool) | Lines 3251–3264 | Remove fake `darkpool_score: 0.50` dataframe generation; use genuine proxy or empty DataFrame. |
| `trading_system/run_pipeline.py` | `_save_strategy_predictions_report` | Line 2769 | Do not `.fillna(0.5)` when sorting/saving; drop or format NaNs cleanly as `N/A`. |

---

### 5.2 Proposed Class Interface: `CrossSectionalScoreNormalizer`

```python
"""
src/ai/score_normalizer.py
Cross-Sectional Score Normalization Engine for 31 Multi-Factor Strategies.
"""
import logging
from typing import List, Optional, Union, Dict
import numpy as np
import pandas as pd
from scipy.special import erf

logger = logging.getLogger(__name__)

class CrossSectionalScoreNormalizer:
    """
    Normalizes multi-factor strategy scores across stock cross-sections
    to eliminate scale and variance disparities while strictly preserving NaNs.
    """

    def __init__(self, method: str = 'rank_percentile', min_symbols_per_market: int = 10):
        """
        Parameters:
        -----------
        method : str
            'rank_percentile' : Uniform CDF ranking in [0.005, 0.995]
            'winsorized_zscore' : Gaussian CDF mapping Phi(Z) in (0, 1)
        min_symbols_per_market : int
            Minimum symbol count to perform per-market partitioning before falling back to global.
        """
        self.method = method
        self.min_symbols_per_market = min_symbols_per_market

    def normalize_scores(
        self,
        df: pd.DataFrame,
        strategy_cols: List[str],
        market_col: Optional[str] = 'market',
        method: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Applies cross-sectional normalization to specified strategy score columns.
        NaN values are preserved strictly as NaN.
        """
        eff_method = method or self.method
        if df.empty:
            return df.copy()

        out_df = df.copy()
        valid_cols = [c for c in strategy_cols if c in out_df.columns]
        if not valid_cols:
            return out_df

        # Partition by market if market_col is available and has sufficient observations
        has_market = market_col in out_df.columns and out_df[market_col].notna().any()
        
        if has_market:
            for market_val, group_idx in out_df.groupby(market_col).groups.items():
                if len(group_idx) >= self.min_symbols_per_market:
                    sub_df = out_df.loc[group_idx, valid_cols]
                    out_df.loc[group_idx, valid_cols] = self._normalize_matrix(sub_df, eff_method)
                else:
                    # Small market group fallback: will normalize across all combined small groups
                    pass
        else:
            out_df[valid_cols] = self._normalize_matrix(out_df[valid_cols], eff_method)

        return out_df

    def _normalize_matrix(self, sub_df: pd.DataFrame, method: str) -> pd.DataFrame:
        norm_df = pd.DataFrame(index=sub_df.index, columns=sub_df.columns, dtype=float)

        for col in sub_df.columns:
            s = pd.to_numeric(sub_df[col], errors='coerce')
            valid_mask = s.notna() & np.isfinite(s)
            n_valid = int(valid_mask.sum())

            if n_valid == 0:
                norm_df[col] = np.nan
            elif n_valid == 1:
                norm_df.loc[valid_mask, col] = 0.50
            else:
                vals = s.loc[valid_mask].values
                if method == 'rank_percentile':
                    # Rank in [0.005, 0.995]
                    ranks = pd.Series(vals, index=s.loc[valid_mask].index).rank(pct=True, ascending=True)
                    # Rescale to avoid extreme 0.0 or 1.0 boundary spikes
                    norm_df.loc[valid_mask, col] = (ranks * (1.0 - 1.0 / n_valid) + 0.5 / n_valid).clip(0.005, 0.995)
                elif method == 'winsorized_zscore':
                    q01 = np.percentile(vals, 1.0)
                    q99 = np.percentile(vals, 99.0)
                    w_vals = np.clip(vals, q01, q99)
                    med = np.median(w_vals)
                    mad = np.median(np.abs(w_vals - med))
                    robust_std = max(1.4826 * mad, 1e-6)
                    z = (w_vals - med) / robust_std
                    # Gaussian CDF Phi(z)
                    phi_z = 0.5 * (1.0 + erf(z / np.sqrt(2.0)))
                    norm_df.loc[valid_mask, col] = np.clip(phi_z, 0.005, 0.995)
                else:
                    norm_df.loc[valid_mask, col] = np.clip(vals, 0.0, 1.0)

        return norm_df
```

---

## 6. Verification & Test Suite Matrix

### 6.1 Existing Key Test Coverage
- `tests/test_factor_momentum_and_available_normalization.py`: Validates that stock with 5 core strategies is not penalized compared to stock with 31 strategies.
- `tests/test_factor_orthogonalization.py`: Validates PCA ZCA and Gram-Schmidt decorrelation.
- `tests/test_adversarial_ensemble_scorer_challenger.py`: Stress tests ensemble scoring with adversarial NaNs and extreme inputs.
- `tests/test_correlation_suppression.py`: Validates VIF and regime correlation penalties.
- `tests/test_r1_ensemble_regime_fixes.py`: Validates regime switching and dynamic Sharpe weighting.

### 6.2 New Test Specifications Required for R1 Acceptance
1. **`test_cross_sectional_score_normalizer_uniform_variance()`**:
   - Input: 31 strategy columns with synthetic distributions (Exponential, Beta(0.1, 0.9), Normal, Uniform, Discrete).
   - Assert: All normalized active columns have mean $\approx 0.50 \pm 0.02$ and standard deviation $\approx \sqrt{1/12} \pm 0.02$.
   - Assert: NaNs remain 100% strictly NaN.
2. **`test_dynamic_zero_weighting_no_05_pollution()`**:
   - Stock A has Strategy 1=0.90, Strategy 2=0.90, Strategies 3..31=NaN.
   - Stock B has Strategy 1=0.90, Strategy 2=0.90, Strategies 3..31=0.50 (polluted).
   - Assert: Stock A's ensemble score is $0.90$ (not dragged down by missing factors).
   - Assert: Total active weight for Stock A is exactly $w_1 + w_2$, and re-normalized weights are $w_1/(w_1+w_2)$ and $w_2/(w_1+w_2)$.
3. **`test_strategy_engines_return_genuine_nans()`**:
   - Run `accruals_quality`, `valueup_catalyst`, `short_interest_squeeze`, `trend_efficiency`, `iv_skew`, `insider_buying`, `earnings_tone_drift` on empty/missing datasets.
   - Assert: Returned score columns contain `NaN`, NOT `0.50`.

---

## 7. Conclusion & Next Steps

This survey delivers the complete theoretical, mathematical, and architectural foundation for Requirement R1. The implementer can directly execute these specifications:
1. Create `src/ai/score_normalizer.py` implementing `CrossSectionalScoreNormalizer`.
2. Cleanse all 31 strategy engines of `.fillna(0.50)` and default `0.50` mappings.
3. Integrate `CrossSectionalScoreNormalizer` in `EnsembleScoringEngine.combine_predictions` prior to orthogonalization and active weight re-normalization.
4. Execute `pytest tests/ -v` to ensure 100% PASS across the entire test suite.
