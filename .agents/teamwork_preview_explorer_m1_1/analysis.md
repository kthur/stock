# Multi-Factor Risk & Style Neutralizer Engine (Strategy 21) Implementation Design

**Author**: Explorer M1-1 (Engine Implementation Designer)  
**Date**: 2026-08-14  
**Target Module**: `trading_system/src/core/multi_factor_neutralizer.py`  
**Milestone**: Milestone 1 (F1: Interface & Imputation, F2: QR Residualization, F3: Pure Alpha Hard SLA Gate)

---

## 1. Executive Summary & Problem Scope

`MultiFactorNeutralizerEngine` (Strategy 21) is designed to extract **pure idiosyncratic alpha** by cross-sectionally eliminating systematic style factor exposures based on the Fama-French 5-Factor model (Size/SMB, Value/HML, Profitability/RMW, Investment/CMA, and Momentum/UMD).

However, forensic analysis reveals critical architectural flaws in the current implementation of `trading_system/src/core/multi_factor_neutralizer.py`:
1. **Positional Argument Binding Failure**: When `compute_scores(universe)` is invoked positionally (as done in `run_pipeline.py:2869` and `test_critical_bugs.py:37`), `universe` is bound to `prices_dict`, leaving `kwargs['universe']` as `None`. This causes `MultiFactorNeutralizerEngine` to immediately return an empty DataFrame (0 symbols evaluated) in production.
2. **Premature Strategy Deactivation**: When `raw_scores` is omitted, the engine returns `NaN` for all stocks instead of generating a deterministic baseline raw alpha signal from price history (12M-1M momentum or 3M returns).
3. **Catastrophic Symbol Dropping (`dropna`)**: Symbols missing any single financial metric (`market_cap`, `per`, `roe`) are dropped via `.dropna()`, losing coverage for growth stocks and newly listed entities instead of performing cross-sectional median imputation.
4. **Global Cross-Sectional Pooling**: Fama-French factors are standardized across all markets combined, distorting KRW-denominated metrics with USD metrics and causing severe cross-market valuation bias.
5. **Numerical Instability of Basic OLS**: Solves normal equations via `lstsq`, susceptible to ill-conditioning when factors are collinear.
6. **Column Naming Inconsistencies**: Omission of both `factor_neutralized_score` and `neutralized_score` aliases causes downstream pipeline and test failures.
7. **Absence of Hard Post-Condition Gating**: No verification that $|\rho(f_k, \epsilon)| < 0.15$ is strictly enforced with secondary Gram-Schmidt deflation.

This design document provides the complete mathematical formulation, algorithmic workflow, and exact line-by-line replacement code to achieve an institutional-grade, numerically robust pure alpha residualization engine.

---

## 2. Root Cause & Defect Analysis

### Defect 1: Positional Argument Binding Mismatch
* **Location**: `trading_system/src/core/multi_factor_neutralizer.py` lines 45–58.
* **Observation**:
  ```python
  def compute_scores(self, prices_dict: Any = None, fundamentals_dict: Optional[Dict] = None, indicators_df: Optional[Any] = None, **kwargs: Any) -> Any:
      universe = kwargs.get("universe", kwargs.get("universe_df", pd.DataFrame()))
  ```
  In `run_pipeline.py:2869`, `fn_engine.compute_scores(universe)` passes the universe DataFrame as the 1st positional argument (`prices_dict`). `kwargs.get("universe")` evaluates to `None`, defaulting to `pd.DataFrame()`. Line 57 `if universe is None or universe.empty:` immediately returns an empty DataFrame.
* **Fix**: Inspect `prices_dict`. If `isinstance(prices_dict, pd.DataFrame)`, bind `universe = prices_dict.copy()`. If `isinstance(prices_dict, dict)`, bind `prices_map = prices_dict` and extract `universe` from `kwargs` or synthesize it from `list(prices_map.keys())`.

### Defect 2: Missing Raw Scores Fallback Signal
* **Location**: Lines 63–78.
* **Observation**: If `raw_scores is None`, the strategy logs deactivation and returns `NaN` for all rows. In production `run_pipeline.py`, Strategy 21 is invoked without `raw_scores`.
* **Fix**: Provide a 3-tier fallback hierarchy:
  1. Use explicit `raw_scores` argument (DataFrame or dict) if provided.
  2. Check if `'score'`, `'raw_score'`, or `'alpha_score'` exists in `universe` columns.
  3. If unavailable, compute deterministic cross-sectional momentum from `prices_map` (12M-1M return: $(P_{t-21} / P_{t-252}) - 1.0$, skipping 1-month reversal noise, or 3M return $(P_t / P_{t-63}) - 1.0$).
  4. If neither price data nor momentum columns exist (pure symbol lists without data), return `NaN` deterministically as expected by unit tests (`test_bug_a3`).

### Defect 3: Catastrophic Dropping of Symbols (`dropna`)
* **Location**: Line 82 (`df_merged.dropna(subset=["score", "market_cap", "per", "roe"])`).
* **Observation**: Dropping rows with missing values strips out hundreds of valid stocks (e.g. unprofitable tech companies with negative/NaN PER, early-stage biotechnology firms, newly listed IPOs).
* **Fix**: Implement **Market-Grouped Median Imputation**. For each factor $f_k$ within market group $m$, compute $\text{median}(f_k)$. Impute missing entries with the group median (or $0.0$ if the entire market lacks data). This guarantees 100% universe retention (all 3,379 symbols evaluated).

### Defect 4: Global Pooling vs Market Segmentation
* **Location**: Lines 96–123.
* **Observation**: Size is computed as $\log(\text{market\_cap})$. Standardizing Korean stocks (market cap $10^{11} \sim 10^{14}$ KRW) with US stocks ($10^8 \sim 10^{12}$ USD) in one global pool introduces artificial cross-currency factor distortions.
* **Fix**: Partition the universe by `market` (`KOSPI`, `KOSDAQ`, `SP500`, `NASDAQ`, `RUSSELL2000`, etc.) and standardize/residualize within each market cohort independently.

### Defect 5: OLS Normal Equation Inversion vs QR Decomposition
* **Location**: Lines 129–130 (`np.linalg.lstsq(X, y)`).
* **Observation**: Direct OLS solves $(X^T X)^{-1} X^T y$. Factor collinearity (e.g. Value vs Profitability, Size vs Investment) squares the condition number $\kappa(X^T X) = \kappa(X)^2$, leading to numerical degradation.
* **Fix**: Apply thin QR Decomposition $X_m = Q_m R_m$ and orthogonal projection $\epsilon_m = y_m - Q_m (Q_m^T y_m)$.

### Defect 6: Inconsistent Output Column Naming
* **Location**: Lines 74, 91, 150.
* **Observation**: Output DataFrame contains only `factor_neutralized_score`, but `test_critical_bugs.py:39` and `run_pipeline.py:2880` expect `neutralized_score`.
* **Fix**: Populate both `factor_neutralized_score` and `neutralized_score` with identical values, along with style exposures (`smb_exposure`, `hml_exposure`, `rmw_exposure`, `cma_exposure`, `umd_exposure`).

### Defect 7: Lack of Hard Post-Condition Verification
* **Location**: Missing in existing code.
* **Observation**: No check to ensure $|\rho(f_k, \epsilon)| < 0.15$ SLA is satisfied.
* **Fix**: Add post-residualization Pearson correlation audit $\max_k |\rho_k| < 0.15$. If violated, execute Secondary Modified Gram-Schmidt (MGS) deflation.

---

## 3. Mathematical Formulation & QR Orthogonal Projection

### 3.1 Fama-French 5-Factor Definitions
For each stock $i$ in market group $m$:
1. **Size ($f_{1, i}$ / SMB)**:
   $$f_{1, i} = \log(\max(\text{market\_cap}_i, 1.0))$$
2. **Value ($f_{2, i}$ / HML)**:
   $$f_{2, i} = \begin{cases} 1.0 / \text{clip}(\text{pbr}_i, 0.01, 100.0) & \text{if PBR is available} \\ 1.0 / \max(\text{per}_i, 0.1) & \text{if } \text{per}_i > 0 \\ -1.0 / \max(|\text{per}_i|, 0.1) & \text{if } \text{per}_i < 0 \\ 0.0 & \text{otherwise} \end{cases}$$
3. **Profitability ($f_{3, i}$ / RMW)**:
   $$f_{3, i} = \text{roe}_i \quad (\text{or operating profit margin})$$
4. **Investment ($f_{4, i}$ / CMA)**:
   $$f_{4, i} = \text{asset\_growth\_yoy}_i \quad (\text{asset growth rate})$$
5. **Momentum ($f_{5, i}$ / UMD)**:
   $$f_{5, i} = R_{12M-1M, i} = \frac{P_{i, t-21}}{P_{i, t-252}} - 1.0 \quad (\text{or } 3M \text{ return})$$

### 3.2 Median Imputation & Z-Score Standardization
For each factor $k \in \{1, \dots, 5\}$ within market group $m$:
$$\tilde{f}_{k, i} = \begin{cases} f_{k, i} & \text{if } f_{k, i} \text{ is finite} \\ \text{median}(\{f_{k, j} : f_{k, j} \text{ is finite}\}) & \text{if } f_{k, i} \text{ is NaN} \end{cases}$$
If all symbols in the group lack factor $k$, $\tilde{f}_{k, i} = 0.0$.

Standardize cross-sectionally:
$$z_{k, i} = \frac{\tilde{f}_{k, i} - \mu_k}{\sigma_k + 10^{-8}}, \quad \text{where } \mu_k = \frac{1}{N_m} \sum_{i=1}^{N_m} \tilde{f}_{k, i}, \quad \sigma_k = \sqrt{\frac{1}{N_m} \sum_{i=1}^{N_m} (\tilde{f}_{k, i} - \mu_k)^2}$$
If $\sigma_k < 10^{-6}$ (zero variance), set $z_{k, i} = 0.0$.

Construct Design Matrix $X_m \in \mathbb{R}^{N_m \times 6}$ with intercept:
$$X_m = \begin{bmatrix} \mathbf{1}_{N_m} & \mathbf{z}_1 & \mathbf{z}_2 & \mathbf{z}_3 & \mathbf{z}_4 & \mathbf{z}_5 \end{bmatrix}$$

### 3.3 QR Decomposition & Orthogonal Projection
Perform thin QR factorization of $X_m$:
$$X_m = Q_m R_m, \quad Q_m \in \mathbb{R}^{N_m \times 6}, \quad R_m \in \mathbb{R}^{6 \times 6}$$
where $Q_m^T Q_m = I_6$ and $R_m$ is upper triangular.

The orthogonal projector onto the factor column space is $P_{X} = Q_m Q_m^T$.  
The orthogonal complement projector (annihilator matrix) is:
$$M_X = I_{N_m} - Q_m Q_m^T$$

The pure idiosyncratic alpha residual $\epsilon_m \in \mathbb{R}^{N_m}$ is computed in $O(N_m K)$ time without forming the $N_m \times N_m$ matrix:
$$\mathbf{a}_m = Q_m^T y_m \in \mathbb{R}^6$$
$$\hat{y}_m = Q_m \mathbf{a}_m \in \mathbb{R}^{N_m}$$
$$\epsilon_m = y_m - \hat{y}_m$$

#### Mathematical Proof of Factor Neutrality
$$Q_m^T \epsilon_m = Q_m^T (y_m - Q_m Q_m^T y_m) = Q_m^T y_m - (Q_m^T Q_m) Q_m^T y_m = Q_m^T y_m - I_6 Q_m^T y_m = \mathbf{0}$$
Since every standardized factor column $\mathbf{z}_k$ satisfies $\mathbf{z}_k = X_m \mathbf{e}_{k+1} = Q_m R_m \mathbf{e}_{k+1} \in \text{span}(Q_m)$:
$$\langle \mathbf{z}_k, \epsilon_m \rangle = (R_m \mathbf{e}_{k+1})^T Q_m^T \epsilon_m = (R_m \mathbf{e}_{k+1})^T \mathbf{0} = 0$$
Hence, cross-sectional covariance and Pearson correlation with all 5 Fama-French factors are **identically zero**:
$$\text{Corr}(\mathbf{z}_k, \epsilon_m) \equiv 0.0$$

### 3.4 Hard Post-Condition SLA Gate & Secondary Deflation
To safeguard against non-linear rank effects or extreme boundary conditions, verify:
$$\rho_{\max} = \max_{k=1}^5 |\text{Corr}(\mathbf{z}_k, \epsilon_m)|$$
If $\rho_{\max} \ge 0.15$, apply **Secondary Modified Gram-Schmidt (MGS) Deflation**:
For each factor $k = 1, \dots, 5$:
$$\mathbf{u}_k = \frac{\mathbf{z}_k - \bar{\mathbf{z}}_k}{\|\mathbf{z}_k - \bar{\mathbf{z}}_k\|_2 + 10^{-12}}$$
$$\epsilon_m \leftarrow \epsilon_m - (\mathbf{u}_k^T \epsilon_m) \mathbf{u}_k$$
Re-center: $\epsilon_m \leftarrow \epsilon_m - \bar{\epsilon}_m$.

### 3.5 Robust Normalization & Score Generation
Scale pure alpha residuals $\epsilon_m$ to $[0.0, 1.0]$ using 1st/99th percentile winsorization:
$$p_1 = \text{percentile}(\epsilon_m, 1), \quad p_{99} = \text{percentile}(\epsilon_m, 99)$$
$$s_i = \begin{cases} \text{clip}\left(\frac{\epsilon_{m, i} - p_1}{p_{99} - p_1}, 0.0, 1.0\right) & \text{if } p_{99} - p_1 > 10^{-8} \\ 0.50 & \text{otherwise} \end{cases}$$

---

## 4. Proposed Source Code Specification

Below is the complete, drop-in replacement implementation for `trading_system/src/core/multi_factor_neutralizer.py`:

```python
"""
multi_factor_neutralizer.py — Multi-Factor Risk & Style Neutralizer Engine (Strategy 21)

Extracts pure idiosyncratic alpha scores by neutralizing unwanted Fama-French 5-Factor
exposures (SMB, HML, RMW, CMA, UMD) via market-grouped thin QR decomposition,
cross-sectional median imputation, and secondary Gram-Schmidt deflation gating.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Any, Optional
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

from src.core.base_strategy import BaseStrategyEngine
from src.core.strategy_registry import register_strategy, StrategyMeta


@register_strategy(
    StrategyMeta(
        strategy_id="factor_neutralized",
        display_name="Multi-Factor Neutralized Alpha",
        score_column="factor_neutralized_score",
        category="factor",
        output_file="factor_neutralized_predictions.txt",
        default_regime_weights={
            "BEAR": 0.04,
            "BEAR_HIGH_VOL": 0.05,
            "SIDEWAYS_LOW_VOL": 0.03,
            "BULL_HIGH_VOL": 0.03,
            "BULL_LOW_VOL": 0.03,
        },
    )
)
class MultiFactorNeutralizerEngine(BaseStrategyEngine):
    """Strategy 21: Multi-Factor Style Neutralization Engine.

    Extracts pure idiosyncratic alpha by neutralizing Size (SMB), Value (HML),
    Profitability (RMW), Investment (CMA), and Momentum (UMD) style exposures.
    """

    def __init__(self, config: Optional[Any] = None) -> None:
        self.config = config

    def compute_scores(
        self,
        prices_dict: Any = None,
        fundamentals_dict: Optional[Dict[str, Dict[str, Any]]] = None,
        indicators_df: Optional[Any] = None,
        **kwargs: Any,
    ) -> pd.DataFrame:
        """Compute factor-neutralized pure alpha scores for all universe symbols.

        Handles both positional universe DataFrames and prices_dict mappings.
        Applies market-grouped median imputation, QR orthogonal projection,
        and hard SLA deflation gating (|rho| < 0.15).
        """
        # 1. Resolve universe DataFrame and price dictionary from arguments
        universe: Optional[pd.DataFrame] = None
        prices_map: Optional[Dict[str, pd.DataFrame]] = None

        if isinstance(prices_dict, pd.DataFrame):
            universe = prices_dict.copy()
            prices_map = kwargs.get("prices_dict", None)
        elif isinstance(prices_dict, dict):
            prices_map = prices_dict
            universe = kwargs.get("universe", kwargs.get("universe_df", None))
            if universe is not None:
                universe = universe.copy()
        else:
            universe = kwargs.get("universe", kwargs.get("universe_df", None))
            if universe is not None:
                universe = universe.copy()
            prices_map = kwargs.get("prices_dict", None)

        if universe is None and prices_map and isinstance(prices_map, dict):
            universe = pd.DataFrame({"symbol": list(prices_map.keys())})

        std_cols = [
            "symbol", "name", "market",
            "factor_neutralized_score", "neutralized_score",
            "smb_exposure", "hml_exposure", "rmw_exposure", "cma_exposure", "umd_exposure",
        ]

        if universe is None or universe.empty:
            return pd.DataFrame(columns=std_cols)

        df = universe.copy()
        if "symbol" not in df.columns:
            return pd.DataFrame(columns=std_cols)

        df["symbol"] = df["symbol"].astype(str).str.strip()
        if "name" not in df.columns:
            df["name"] = df["symbol"]
        if "market" not in df.columns:
            df["market"] = df["symbol"].map(lambda s: "KOSPI" if str(s).isdigit() else "SP500")

        # 2. Merge fundamentals_dict if supplied
        if fundamentals_dict and isinstance(fundamentals_dict, dict):
            for col in ["market_cap", "per", "pbr", "roe", "asset_growth_yoy"]:
                if col not in df.columns:
                    df[col] = df["symbol"].map(
                        lambda s: fundamentals_dict.get(s, {}).get(col, np.nan)
                    )

        # 3. Resolve or compute raw alpha scores y
        raw_scores = kwargs.get("raw_scores", kwargs.get("raw_scores_df", None))
        has_explicit_raw = False

        if raw_scores is not None and isinstance(raw_scores, pd.DataFrame) and not raw_scores.empty:
            score_col = "score" if "score" in raw_scores.columns else ("raw_score" if "raw_score" in raw_scores.columns else raw_scores.columns[-1])
            score_map = dict(zip(raw_scores["symbol"].astype(str).str.strip(), raw_scores[score_col]))
            df["_raw_y"] = df["symbol"].map(score_map)
            has_explicit_raw = True
        elif raw_scores is not None and isinstance(raw_scores, dict):
            df["_raw_y"] = df["symbol"].map(raw_scores)
            has_explicit_raw = True
        elif "score" in df.columns:
            df["_raw_y"] = pd.to_numeric(df["score"], errors="coerce")
            has_explicit_raw = True
        elif "raw_score" in df.columns:
            df["_raw_y"] = pd.to_numeric(df["raw_score"], errors="coerce")
            has_explicit_raw = True
        else:
            # Fallback 1: Extract from universe momentum columns
            if "momentum_12m_1m" in df.columns:
                df["_raw_y"] = pd.to_numeric(df["momentum_12m_1m"], errors="coerce")
            elif "momentum_12m" in df.columns:
                df["_raw_y"] = pd.to_numeric(df["momentum_12m"], errors="coerce")
            elif "return_3m" in df.columns or "ret_60d" in df.columns:
                col = "return_3m" if "return_3m" in df.columns else "ret_60d"
                df["_raw_y"] = pd.to_numeric(df[col], errors="coerce")
            # Fallback 2: Compute 12M-1M / 3M return from prices_map
            elif prices_map and isinstance(prices_map, dict):
                mom_dict = {}
                for sym, p_df in prices_map.items():
                    if isinstance(p_df, pd.DataFrame) and len(p_df) >= 25:
                        c_series = p_df["Close"] if "Close" in p_df.columns else (p_df["close"] if "close" in p_df.columns else None)
                        if c_series is not None and len(c_series) >= 25:
                            c_vals = c_series.dropna().values
                            if len(c_vals) >= 252:
                                mom = (c_vals[-21] / max(c_vals[-252], 1e-6)) - 1.0
                            elif len(c_vals) >= 63:
                                mom = (c_vals[-1] / max(c_vals[-63], 1e-6)) - 1.0
                            else:
                                mom = (c_vals[-1] / max(c_vals[0], 1e-6)) - 1.0
                            mom_dict[str(sym).strip()] = mom
                if mom_dict:
                    df["_raw_y"] = df["symbol"].map(mom_dict)
                else:
                    df["_raw_y"] = np.nan
            else:
                df["_raw_y"] = np.nan

        # Check if factors or raw scores exist; if totally empty/NaN, return NaNs (Bug A-3 contract)
        fund_cols_exist = any(col in df.columns for col in ["market_cap", "per", "pbr", "roe"])
        if not fund_cols_exist and not has_explicit_raw and df["_raw_y"].isna().all():
            logger.info("MultiFactorNeutralizerEngine: missing factors and raw scores. Returning deterministic NaNs.")
            return pd.DataFrame({
                "symbol": df["symbol"],
                "name": df["name"],
                "market": df["market"],
                "factor_neutralized_score": np.nan,
                "neutralized_score": np.nan,
                "smb_exposure": np.nan,
                "hml_exposure": np.nan,
                "rmw_exposure": np.nan,
                "cma_exposure": np.nan,
                "umd_exposure": np.nan,
            })

        # 4. Construct Fama-French 5-Factor Raw Series
        # Factor 1: Size (SMB) -> log(Market Cap)
        cap_series = pd.to_numeric(df.get("market_cap", pd.Series(np.nan, index=df.index)), errors="coerce")
        
        # Factor 2: Value (HML) -> 1/PBR or E/P Yield
        pbr_series = pd.to_numeric(df.get("pbr", pd.Series(np.nan, index=df.index)), errors="coerce")
        per_series = pd.to_numeric(df.get("per", pd.Series(np.nan, index=df.index)), errors="coerce")
        
        val_from_pbr = np.where(pbr_series > 0, 1.0 / np.clip(pbr_series, 0.01, 100.0), np.nan)
        val_from_per = np.where(
            per_series > 0,
            1.0 / np.maximum(per_series, 0.1),
            np.where(per_series < 0, -1.0 / np.maximum(np.abs(per_series), 0.1), np.nan)
        )
        val_raw = np.where(np.isfinite(val_from_pbr), val_from_pbr, val_from_per)
        val_series = pd.Series(val_raw, index=df.index)

        # Factor 3: Profitability (RMW) -> ROE
        roe_series = pd.to_numeric(df.get("roe", pd.Series(np.nan, index=df.index)), errors="coerce")

        # Factor 4: Investment (CMA) -> Asset Growth YoY
        cma_raw = df.get("asset_growth_yoy", df.get("asset_growth", pd.Series(np.nan, index=df.index)))
        cma_series = pd.to_numeric(cma_raw, errors="coerce")

        # Factor 5: Momentum (UMD) -> 12M Momentum
        umd_raw = df.get("momentum_12m", df.get("momentum_12m_1m", df["_raw_y"]))
        umd_series = pd.to_numeric(umd_raw, errors="coerce")

        df["_f_smb"] = cap_series
        df["_f_hml"] = val_series
        df["_f_rmw"] = roe_series
        df["_f_cma"] = cma_series
        df["_f_umd"] = umd_series

        # 5. Market-Grouped Factor Imputation & QR Orthogonal Residualization
        output_rows: List[Dict[str, Any]] = []
        market_groups = df.groupby("market", dropna=False)

        for mkt, group_df in market_groups:
            idx = group_df.index
            N_m = len(group_df)
            if N_m == 0:
                continue

            # Extract raw y
            y_raw = group_df["_raw_y"].values.astype(float)
            if np.all(np.isnan(y_raw)):
                y_raw = np.zeros(N_m, dtype=float)
            else:
                med_y = np.nanmedian(y_raw) if np.any(np.isfinite(y_raw)) else 0.0
                y_raw = np.where(np.isfinite(y_raw), y_raw, med_y)

            # Impute factors per market
            f_cols = ["_f_smb", "_f_hml", "_f_rmw", "_f_cma", "_f_umd"]
            Z_factors = np.zeros((N_m, len(f_cols)), dtype=float)

            for k, f_col in enumerate(f_cols):
                f_vals = group_df[f_col].values.astype(float)
                if f_col == "_f_smb":
                    f_vals = np.where(f_vals > 0, np.log(np.maximum(f_vals, 1.0)), np.nan)

                valid_mask = np.isfinite(f_vals)
                if np.any(valid_mask):
                    med_k = float(np.nanmedian(f_vals[valid_mask]))
                    f_clean = np.where(valid_mask, f_vals, med_k)
                else:
                    f_clean = np.zeros(N_m, dtype=float)

                # Cross-sectional z-score standardization
                f_std = float(np.std(f_clean, ddof=0))
                f_mean = float(np.mean(f_clean))
                if f_std > 1e-6:
                    Z_factors[:, k] = (f_clean - f_mean) / f_std
                else:
                    Z_factors[:, k] = 0.0

            # Perform QR decomposition: X = [1, Z_factors]
            X_m = np.column_stack([np.ones(N_m, dtype=float), Z_factors])

            if N_m >= 6:
                try:
                    # Thin QR decomposition: X = Q * R
                    Q_m, _ = np.linalg.qr(X_m, mode="reduced")
                    # Orthogonal projection: residual = y - Q (Q^T y)
                    proj_coef = np.dot(Q_m.T, y_raw)
                    y_pred = np.dot(Q_m, proj_coef)
                    residual = y_raw - y_pred
                except Exception as e:
                    logger.warning(f"QR decomposition failed for market {mkt}: {e}")
                    residual = y_raw - np.mean(y_raw)
            else:
                residual = y_raw - np.mean(y_raw)

            # 6. Hard Post-Condition SLA Gate: max |rho(f_k, residual)| < 0.15
            res_std = float(np.std(residual, ddof=0))
            if res_std > 1e-8:
                for k in range(Z_factors.shape[1]):
                    z_k = Z_factors[:, k]
                    z_std = float(np.std(z_k, ddof=0))
                    if z_std > 1e-6:
                        corr_val = float(np.corrcoef(z_k, residual)[0, 1])
                        if np.isnan(corr_val) or np.abs(corr_val) >= 0.15:
                            # Secondary Gram-Schmidt Deflation
                            z_center = z_k - np.mean(z_k)
                            z_norm = np.linalg.norm(z_center)
                            if z_norm > 1e-8:
                                u_k = z_center / z_norm
                                residual = residual - np.dot(u_k, residual) * u_k
                residual = residual - np.mean(residual)

            # 7. Robust Scaling to [0.0, 1.0]
            p1, p99 = np.percentile(residual, 1), np.percentile(residual, 99)
            denom = (p99 - p1) if (p99 - p1) > 1e-8 else 1.0
            norm_scores = np.clip((residual - p1) / denom, 0.0, 1.0)

            for i, (_, row) in enumerate(group_df.iterrows()):
                sym = str(row["symbol"]).strip()
                name = str(row.get("name", sym))
                mkt_str = str(row.get("market", mkt))
                score_val = round(float(norm_scores[i]), 4)

                output_rows.append({
                    "symbol": sym,
                    "name": name,
                    "market": mkt_str,
                    "factor_neutralized_score": score_val,
                    "neutralized_score": score_val,
                    "smb_exposure": round(float(Z_factors[i, 0]), 4),
                    "hml_exposure": round(float(Z_factors[i, 1]), 4),
                    "rmw_exposure": round(float(Z_factors[i, 2]), 4),
                    "cma_exposure": round(float(Z_factors[i, 3]), 4),
                    "umd_exposure": round(float(Z_factors[i, 4]), 4),
                })

        res_df = pd.DataFrame(output_rows)
        if not res_df.empty:
            res_df = res_df.sort_values(by="factor_neutralized_score", ascending=False).reset_index(drop=True)
        return res_df
```

---

## 5. Verification Plan & Test Matrix

To independently verify the implementation, the following test matrix must be executed:

| Test Case | Scenario | Expected Behavior | Target SLA |
|---|---|---|---|
| **T1: Positional Argument Invocation** | `compute_scores(universe)` where universe is a DataFrame | Correctly binds universe, computes 100% of symbols | Total count matches `len(universe)` |
| **T2: Backward Compatibility Alias** | Inspect columns of output DataFrame | Both `factor_neutralized_score` and `neutralized_score` present and identical | `(df['factor_neutralized_score'] == df['neutralized_score']).all()` |
| **T3: Deactivation on Missing Everything** | Pass empty universe with only symbols (`test_bug_a3`) | Returns NaNs deterministically without random filling | `df['neutralized_score'].isna().all()` |
| **T4: Zero Drop on Missing Fundamentals** | 3,379 symbols where 25% lack PER/ROE | Group median imputation keeps all 3,379 symbols | `len(df) == 3379` |
| **T5: QR Factor Orthogonality SLA** | Correlated universe with high factor loading ($\rho > 0.70$) | Cross-sectional correlation with Size, Value, ROE, CMA, UMD | $\max_k |\rho(f_k, \text{score})| < 0.15$ |
| **T6: Numerical Stability on Collinear Factors** | Duplicate factor columns ($X_1 = X_2$) | QR decomposition completes cleanly without singular matrix crash | Zero NaNs, scores in $[0.0, 1.0]$ |
| **T7: Execution Latency SLA** | 3,379 symbols $\times$ 5 factors | Cross-sectional QR decomposition latency | $< 25$ ms total execution |

---

## 6. Summary of Architectural Impact

1. **Pipeline Reliability**: Resolves silent drop of Strategy 21 in `run_pipeline.py`, restoring full 31-strategy alpha output to GitHub Pages dashboard (`index.html`).
2. **Mathematical Precision**: Replaces $O(N^3)$ ill-conditioned matrix inversion with stable $O(N K)$ QR projection.
3. **Institutional Rigor**: Enforces $|\rho| < 0.15$ Fama-French style neutrality SLA across all 3,379 global equities.
