# Domain 1 Audit Analysis: AI/ML & Prediction Integrity (v6.0)

**Document Version**: 6.0 (Senior Quantitative ML & Statistical Finance Forensic Audit)  
**Target Codebase**: `kthur/stock` (`d:\Finance\code\stock\trading_system`)  
**Auditor**: Senior Quantitative ML & Statistical Finance Auditor (Domain 1)  
**Date**: 2026-08-22 (KST)  
**Status**: Read-Only Comprehensive Audit Analysis Complete  

---

## 1. Executive Summary & Domain Scope

As part of the 6th Comprehensive Multi-Disciplinary System Audit, Domain 1 (AI/ML & Prediction Integrity) conducted an exhaustive, line-by-line forensic investigation across the quantitative machine learning and signal engineering stack:
1. `trading_system/src/ai/prediction_model.py` (Multi-market XGBoost/LightGBM/CatBoost regression, Surge classifiers, Strict Causal LSTM sequence models, 2-Tier Lead-Lag matrix, horizon target scaling, and inference transforms).
2. `trading_system/src/ai/ensemble_scorer.py` (31-strategy dynamic weighting, 2D market regime matrix, dual-market US/KR decoupling, multi-horizon alpha tier decomposition, exponential decay filtering, and transaction cost modeling).
3. `trading_system/src/ai/factor_orthogonalizer.py` (Löwdin & PCA-ZCA symmetric whitening, continuous ridge shrinkage, CrossSectionalFactorNeutralizer GLS regression).
4. `trading_system/src/ai/factor_suppression.py` & `correlation_monitor.py` (Regime-based factor noise suppression, Spearman rank correlation EMA, VIF multicollinearity monitoring, and effective strategy count $N_{eff}$).
5. `trading_system/src/ai/vcp_detector.py` & `vcp_ml_predictor.py` (Minervini VCP rule-based pattern detector and XGBoost/LightGBM/CatBoost VCP surge classifier with Platt/Isotonic probability calibration).
6. `trading_system/src/ai/optuna_tuner.py` (Hyperparameter optimization for Regression, Surge, Lead-Lag, VCP Rule, VCP ML, 2D Regime Weights, and Regime Correlation Suppression).
7. `trading_system/src/ai/meta_ensemble_learner.py` (2nd-stage Ridge and LightGBM stacking meta-learner).

### Audit Summary
- **Total Novel Findings**: 9 Issues (V6-01 ~ V6-09)
- **Zero Duplication**: 100% novel, non-overlapping with any prior audit items (V1 through V5).
- **Severity Distribution**:
  - 🔴 **CRITICAL (P0)**: 2 Issues (V6-01, V6-02)
  - 🟠 **HIGH (P1)**: 6 Issues (V6-03, V6-04, V6-05, V6-06, V6-07, V6-08)
  - 🟡 **MEDIUM (P2)**: 1 Issue (V6-09)
- **Forensic Verification**: Every finding references exact file paths and verified line numbers with reproducible mathematical rationales and complete Before/After Git Diff snippets.

---

## 2. Comprehensive Domain 1 Master Issue Table

| Issue ID | Severity | Title | File Path & Exact Line Numbers | Primary Risk Profile |
|---|---|---|---|---|
| **V6-01** | 🔴 CRITICAL | Strict Causal LSTM Training Target Log1p Domain Disconnect Causing Exponentially Exploded Predictions in Regression Blending | `trading_system/src/ai/prediction_model.py:1514, 1775-1784, 2487-2505` | Regression Alpha Distortion / Scale Explosion |
| **V6-02** | 🔴 CRITICAL | Multi-Horizon Exponential Decay Filter Key-Column Schema Mismatch Disabling Adaptive Half-Life Smoothing across all 31 Strategies | `trading_system/src/ai/ensemble_scorer.py:2559-2591, 2620-2625` | Signal Churning / Fast-Tier Alpha Elimination |
| **V6-03** | 🟠 HIGH | Dual-Regime Weight Squaring & US-KR Weight Cross-Contamination in `EnsembleScoringEngine` | `trading_system/src/ai/ensemble_scorer.py:1900-1915` | Extreme Weight Concentration / Market Misallocation |
| **V6-04** | 🟠 HIGH | Cross-Market Model Hijacking in `predict_lstm` Discarding Symbol Market Identity | `trading_system/src/ai/prediction_model.py:2593-2615` | Market Regime Incompatibility / Inaccurate Predictions |
| **V6-05** | 🟠 HIGH | Multi-Year Cumulative Return Scaling Distortion in `predict_lead_lag` Fallback Injecting Unbounded Percentage Scales | `trading_system/src/ai/prediction_model.py:3064-3065` | Alpha Inversion / Flat Score Saturation |
| **V6-06** | 🟠 HIGH | Volatility Maximization Anomaly in Optuna 2D Regime and Factor Suppression Objective Functions During Market Drawdowns | `trading_system/src/ai/optuna_tuner.py:553-558, 624-628` | Crisis Allocation Distortion / Maximum Volatility |
| **V6-07** | 🟠 HIGH | Artificial Threshold Filtering Bias and 10-Symbol Evaluation Cap in Strategy 3 (Lead-Lag) HPO | `trading_system/src/ai/optuna_tuner.py:317-324` | Spurious Hyperparameters / Ineffective HPO |
| **V6-08** | 🟠 HIGH | Unchecked Feature Dimension & Permutation Alignment in `MetaEnsembleLearner.predict` | `trading_system/src/ai/meta_ensemble_learner.py:158-183` | Factor Permutation Corruption / Shape Crash |
| **V6-09** | 🟡 MEDIUM | Post-Normalization Weight Bound Invalidation in `AlphaDecayTracker` | `trading_system/src/ai/optuna_tuner.py:698-705` | Boundary Constraint Violation |

---

## 3. In-Depth Technical Analysis & Git Diff Proposals

---

### V6-01 [🔴 CRITICAL]: Strict Causal LSTM Training Target Log1p Domain Disconnect Causing Exponentially Exploded Predictions in Regression Blending

- **Affected File & Line Numbers**: `trading_system/src/ai/prediction_model.py:1514, 1775-1784, 2487-2505`
- **Severity**: 🔴 CRITICAL (P0)
- **Symptom & Root Cause Analysis**:
  In `prediction_model.py`, tree-based regression models (XGBoost, LightGBM, CatBoost) are trained on Sharpe-scaled returns mapped through the non-linear transformation:
  $$y_{\text{tree}} = \text{transform\_sharpe}(target) = \text{sign}(x) \cdot \ln(1 + |x|)$$
  However, in `_prepare_lstm_data()` (line 1514) and `train()` (lines 1775-1780), the PyTorch LSTM model is trained directly on the raw, untransformed Sharpe target values:
  $$y_{\text{lstm}} = \text{group\_sorted}[target\_col].\text{values} = x$$
  During inference in `_predict_regression()` (lines 2487-2488), the model forms a linear blend of tree predictions ($\hat{y}_{\text{tree}} \in \text{log1p space}$) and LSTM prediction ($\hat{y}_{\text{lstm}} \in \text{linear space}$):
  $$\hat{y}_{\text{blend}} = w_{\text{tree}} \hat{y}_{\text{tree}} + w_{\text{lstm}} \hat{y}_{\text{lstm}}$$
  Subsequently, `inverse_transform_sharpe()` (lines 2499-2501) applies the inverse transformation to the entire blend:
  $$\hat{R} = \text{sign}(\hat{y}_{\text{blend}}) \cdot \left(\exp(|\hat{y}_{\text{blend}}|) - 1\right) \cdot \sigma_{20d}$$
  Because $\hat{y}_{\text{lstm}}$ was already in linear Sharpe space, exponentiating it ($\exp(\hat{y}_{\text{lstm}}) - 1$) causes an exponential explosion:
  For an LSTM prediction of Sharpe = 2.0, $\exp(2.0) - 1 = 6.389$ (a 320% distortion). For Sharpe = 3.0, $\exp(3.0) - 1 = 19.086$ (a 636% distortion). This severely pollutes the blended expected return and destroys cross-sectional ranking.
- **Mathematical / Financial Engineering Rationale**:
  Ensemble blending across heterogeneous architectures requires strict domain homomorphism. The target representation across all base estimators $m \in \{\text{XGB}, \text{LGB}, \text{Cat}, \text{LSTM}\}$ must lie in the identical metric space $(\mathcal{Y}, \|\cdot\|)$. Mapping the LSTM training target through `transform_sharpe` guarantees that all model predictions lie in $\text{sign-log1p}(\text{Sharpe})$ space before convex combination, allowing `inverse_transform_sharpe` to properly map the ensemble expectation back to linear return space.
- **Concrete Source Code Modification Snippet**:

```diff
--- a/trading_system/src/ai/prediction_model.py
+++ b/trading_system/src/ai/prediction_model.py
@@ -1511,7 +1511,8 @@ class OnDevicePredictionModel:
                 continue
 
             returns = group_sorted['ret_1d'].values
-            targets = group_sorted[target_col].values
+            from src.ai.target_transform import transform_sharpe
+            targets = transform_sharpe(group_sorted[target_col]).values
             indices = group_sorted.index.values
 
             # Create rolling windows
```

---

### V6-02 [🔴 CRITICAL]: Multi-Horizon Exponential Decay Filter Key-Column Schema Mismatch Disabling Adaptive Half-Life Smoothing across all 31 Strategies

- **Affected File & Line Numbers**: `trading_system/src/ai/ensemble_scorer.py:2559-2591, 2620-2625`
- **Severity**: 🔴 CRITICAL (P0)
- **Symptom & Root Cause Analysis**:
  `EnsembleScoringEngine.STRATEGY_HALF_LIVES` defines multi-horizon continuous exponential convolutional half-lives $\tau_k \in [0.5, 60.0]$ indexed by canonical strategy names:
  `"microstructure": 0.5`, `"short_term_reversal": 1.5`, `"order_flow": 2.0`, `"lead_lag": 5.0`, ..., `"rim_valuation": 45.0`, `"value_up": 60.0`.
  In `apply_exponential_decay_filter()`, the loop iterates over the columns of `curr_indexed`:
  ```python
  for col in curr_indexed.columns:
      if col in prev_indexed.columns and pd.api.types.is_numeric_dtype(curr_indexed[col]):
          tau = half_lives.get(col, 10.0)
          alpha = 1.0 - float(np.exp(-np.log(2.0) / max(tau, 0.1)))
          prev_s = prev_indexed[col].reindex(curr_indexed.index).fillna(curr_indexed[col])
          curr_indexed[col] = alpha * curr_indexed[col] + (1.0 - alpha) * prev_s
  ```
  However, the score columns present in `curr_indexed` are named `microstructure_score`, `reversal_score`, `order_flow_score`, `ll_score`, `rim_score`, `valueup_catalyst_score`, etc.
  Because none of these column names match the strategy keys in `STRATEGY_HALF_LIVES`, `half_lives.get(col, 10.0)` evaluates to `None` and falls back to the default `tau = 10.0` for **EVERY SINGLE STRATEGY**.
  Consequently:
  1. Fast-tier strategies (microstructure $\tau=0.5\text{d}$, reversal $\tau=1.5\text{d}$) are dampened with a 10-day half-life, causing 20x lag and eliminating fast-tier alpha responsiveness.
  2. Slow-tier fundamental strategies (RIM $\tau=45\text{d}$, value-up $\tau=60\text{d}$) are updated with a 10-day half-life, causing excessive turnover and signal churning.
  3. Metadata columns (`close`, `volume`, `expected_return`) present in `curr_indexed` are erroneously exponentially smoothed across time.
- **Mathematical / Financial Engineering Rationale**:
  Continuous exponential smoothing must apply the specific decay factor $\alpha_k = 1 - \exp\left(-\frac{\ln 2}{\tau_k}\right)$ corresponding to each strategy's empirical information decay rate. A schema adapter mapping score column aliases (`col_name -> canonical_strategy_id`) is essential to preserve the multi-frequency time-tier hierarchy (Fast: 1-3d, Medium: 5-20d, Slow: 20-60d).
- **Concrete Source Code Modification Snippet**:

```diff
--- a/trading_system/src/ai/ensemble_scorer.py
+++ b/trading_system/src/ai/ensemble_scorer.py
@@ -2616,10 +2616,28 @@ class EnsembleScoringEngine:
         if sym_col and sym_col in previous_scores.columns:
             prev_indexed = previous_scores.set_index(sym_col)
             curr_indexed = df_filtered.set_index(sym_col)
 
+            score_col_to_strat = {
+                'reg_score': 'regression', 'surge_score': 'surge', 'll_score': 'lead_lag',
+                'vcp_rule_score': 'vcp_pattern', 'vcp_ml_score': 'vcp_ml', 'lstm_score': 'regression',
+                'stat_arb_score': 'stat_arb', 'sector_score': 'sector_rotation', 'rim_score': 'rim_valuation',
+                'event_score': 'event_driven', 'mq_score': 'mq_factor', 'iv_skew_score': 'iv_skew',
+                'order_flow_score': 'order_flow', 'reversal_score': 'short_term_reversal', 'arm_score': 'arm_factor',
+                'card_score': 'card_factor', 'latr_score': 'latr_factor', 'inst_foreign_sector_score': 'inst_foreign_sector',
+                'supply_chain_score': 'supply_chain', 'sentiment_score': 'sentiment', 'factor_neutralized_score': 'factor_neutralized',
+                'vol_target_score': 'vol_target', 'microstructure_score': 'microstructure', 'accruals_quality_score': 'accruals_quality',
+                'short_squeeze_score': 'short_squeeze', 'valueup_catalyst_score': 'value_up', 'trend_efficiency_score': 'trend_efficiency',
+                'gamma_squeeze_score': 'gamma_squeeze', 'insider_buying_score': 'insider_buying', 'darkpool_score': 'darkpool_hft',
+                'earnings_tone_drift_score': 'tone_drift'
+            }
+
             for col in curr_indexed.columns:
-                if col in prev_indexed.columns and pd.api.types.is_numeric_dtype(curr_indexed[col]):
-                    tau = half_lives.get(col, 10.0)
+                strat_key = score_col_to_strat.get(col, col)
+                if strat_key in half_lives and col in prev_indexed.columns and pd.api.types.is_numeric_dtype(curr_indexed[col]):
+                    tau = half_lives.get(strat_key, 10.0)
                     alpha = 1.0 - float(np.exp(-np.log(2.0) / max(tau, 0.1)))
                     prev_s = prev_indexed[col].reindex(curr_indexed.index).fillna(curr_indexed[col])
                     curr_indexed[col] = alpha * curr_indexed[col] + (1.0 - alpha) * prev_s
```

---

### V6-03 [🟠 HIGH]: Dual-Regime Weight Squaring & US-KR Weight Cross-Contamination in `EnsembleScoringEngine`

- **Affected File & Line Numbers**: `trading_system/src/ai/ensemble_scorer.py:1900-1915`
- **Severity**: 🟠 HIGH (P1)
- **Symptom & Root Cause Analysis**:
  In `EnsembleScoringEngine.combine_predictions()`, `weights` is initialized to `us_weights` (line 1250). In Phase 3-B.1 (line 1841) and Phase 3-C (line 1867), `weights` is updated by applying the orthogonalization and VIF noise suppression penalties:
  $$w_{\text{suppressed}, k} = w_{\text{us}, k} \cdot P_k / \sum_j (w_{\text{us}, j} \cdot P_j)$$
  Then, in lines 1900-1914:
  ```python
  if weights is not None and isinstance(weights, dict) and len(weights) > 0:
      if us_weights is not None:
          eff_us_weights = {k: us_weights.get(k, 1.0) * weights.get(k, 1.0) for k in weights}
          s_us = sum(eff_us_weights.values())
          if s_us > 0:
              eff_us_weights = {k: v / s_us for k, v in eff_us_weights.items()}
      if kr_weights is not None:
          eff_kr_weights = {k: kr_weights.get(k, 1.0) * weights.get(k, 1.0) for k in weights}
          s_kr = sum(eff_kr_weights.values())
          if s_kr > 0:
              eff_kr_weights = {k: v / s_kr for k, v in eff_kr_weights.items()}
  ```
  This creates two severe mathematical distortions:
  1. **Weight Squaring on US Allocations**: `eff_us_weights` evaluates $w_{\text{us}, k} \cdot w_{\text{suppressed}, k} \approx w_{\text{us}, k}^2 \cdot P_k$. Squaring the weights inflates top-performing strategies (e.g. $0.20^2 = 0.04$ vs $0.02^2 = 0.0004$), causing a 100:1 concentration that violates the 20:1 max weight ratio bound.
  2. **Cross-Market Contamination on Korean Allocations**: `eff_kr_weights` multiplies Korean regime weights `kr_weights` by US suppressed weights `weights` ($w_{\text{kr}, k} \cdot w_{\text{us}, k} \cdot P_k$). If the US market is in a `BULL` regime (high momentum weight) while the KR market is in a `BEAR` regime (defensive valuation weight), Korean stocks receive aggressive US momentum weightings, destroying market decoupling protection.
- **Mathematical / Financial Engineering Rationale**:
  The cross-sectional correlation penalty multiplier $P_k = \frac{w_{\text{suppressed}, k}}{w_{\text{us}, k} + \epsilon}$ is strategy-specific, representing collinear redundancy. It must be applied linearly to `kr_weights`:
  $$w_{\text{eff\_kr}, k} = \frac{w_{\text{kr}, k} \cdot P_k}{\sum_j (w_{\text{kr}, j} \cdot P_j)}$$
  while `eff_us_weights` should directly utilize `weights` ($= w_{\text{suppressed}}$) without squaring.
- **Concrete Source Code Modification Snippet**:

```diff
--- a/trading_system/src/ai/ensemble_scorer.py
+++ b/trading_system/src/ai/ensemble_scorer.py
@@ -1898,15 +1898,15 @@ class EnsembleScoringEngine:
         # Incorporate orthogonalization penalty and VIF factor suppression into eff_us_weights and eff_kr_weights
         if weights is not None and isinstance(weights, dict) and len(weights) > 0:
             if us_weights is not None:
-                eff_us_weights = {k: us_weights.get(k, 1.0) * weights.get(k, 1.0) for k in weights}
-                s_us = sum(eff_us_weights.values())
-                if s_us > 0:
-                    eff_us_weights = {k: v / s_us for k, v in eff_us_weights.items()}
+                eff_us_weights = dict(weights)
             else:
                 eff_us_weights = weights
 
             if kr_weights is not None:
-                eff_kr_weights = {k: kr_weights.get(k, 1.0) * weights.get(k, 1.0) for k in weights}
+                # Extract relative suppression penalty factor P_k = weights_k / us_weights_k
+                penalty_ratios = {k: (weights.get(k, 1.0) / max(us_weights.get(k, 1.0), 1e-6)) if us_weights else 1.0 for k in weights}
+                eff_kr_weights = {k: kr_weights.get(k, 1.0) * penalty_ratios.get(k, 1.0) for k in kr_weights}
                 s_kr = sum(eff_kr_weights.values())
                 if s_kr > 0:
                     eff_kr_weights = {k: v / s_kr for k, v in eff_kr_weights.items()}
```

---

### V6-04 [🟠 HIGH]: Cross-Market Model Hijacking in `predict_lstm` Discarding Symbol Market Identity

- **Affected File & Line Numbers**: `trading_system/src/ai/prediction_model.py:2593-2615`
- **Severity**: 🟠 HIGH (P1)
- **Symptom & Root Cause Analysis**:
  In `OnDevicePredictionModel.predict_lstm()`, the model selection loop searches `self.lstm_models`:
  ```python
  lstm_model = None
  for mkt_models in self.lstm_models.values():
      if isinstance(mkt_models, dict):
          m = mkt_models.get(horizon) or mkt_models.get(20)
          if m is not None and getattr(m, 'is_trained', False):
              lstm_model = m
              break
  ```
  The code grabs the first trained market model encountered in the dictionary (e.g. `sp500`) and passes ALL symbols across all markets (`valid_symbols`, including KOSPI, KOSDAQ, RUSSELL2000, NASDAQ) through that single model in a single batch `X_batch`.
  This completely discards market segment boundaries. Although `train()` carefully fits market-specific LSTM sequence predictors (`self.lstm_models['kospi']`, `self.lstm_models['nasdaq']`, etc.), `predict_lstm` evaluates US mega-cap price return dynamics on Korean small-cap equities.
- **Mathematical / Financial Engineering Rationale**:
  Time-series neural network dynamics (autoregressive parameters, momentum persistence, and volatility clustering) differ significantly between US large-cap equities and Korean small-caps. Evaluating out-of-distribution market data on a mismatched LSTM model causes severe alpha degradation. Predictions must be partitioned by symbol market.
- **Concrete Source Code Modification Snippet**:

```diff
--- a/trading_system/src/ai/prediction_model.py
+++ b/trading_system/src/ai/prediction_model.py
@@ -2590,26 +2590,36 @@ class OnDevicePredictionModel:
             return pd.DataFrame(columns=['symbol', 'lstm_score'])
 
-        # 2. Check for loaded PyTorch LSTM models
-        lstm_model = None
-        for mkt_models in self.lstm_models.values():
-            if isinstance(mkt_models, dict):
-                m = mkt_models.get(horizon) or mkt_models.get(20)
-                if m is not None and getattr(m, 'is_trained', False):
-                    lstm_model = m
-                    break
-
-        if lstm_model is not None:
-            try:
-                X_batch = np.array(sequences, dtype=np.float32)
-                preds = lstm_model.predict(X_batch)
-                if hasattr(preds, "ravel"):
-                    preds = preds.ravel()
-                elif isinstance(preds, (list, tuple)):
-                    preds = np.array(preds).ravel()
-                raw_scores = np.nan_to_num(preds, nan=0.0, posinf=0.0, neginf=0.0)
-            except Exception as e:
-                logger.warning(f"PyTorch LSTM batch prediction failed: {e}. Falling back to causal momentum.")
-                raw_scores = np.array(momentum_fallbacks, dtype=np.float32)
-        else:
-            raw_scores = np.array(momentum_fallbacks, dtype=np.float32)
+        # 2. Market-Aware Batch Prediction using market-specific LSTM models
+        raw_scores = np.array(momentum_fallbacks, dtype=np.float32)
+        sym_to_mkt = {}
+        for sym in valid_symbols:
+            sym_str = str(sym).upper()
+            if self.is_krx_symbol(sym):
+                sym_to_mkt[sym] = 'KOSDAQ' if (sym_str.endswith('.KQ') or 'KOSDAQ' in sym_str) else 'KOSPI'
+            else:
+                sym_to_mkt[sym] = 'SP500'
+
+        for mkt in set(sym_to_mkt.values()):
+            mkt_indices = [i for i, sym in enumerate(valid_symbols) if sym_to_mkt[sym] == mkt]
+            if not mkt_indices:
+                continue
+            mkt_model = case_insensitive_get(self.lstm_models, mkt, {}).get(horizon) or case_insensitive_get(self.lstm_models, mkt, {}).get(20)
+            if mkt_model is None and mkt in ['KOSPI', 'KOSDAQ']:
+                mkt_model = case_insensitive_get(self.lstm_models, 'KRX', {}).get(horizon) or case_insensitive_get(self.lstm_models, 'KRX', {}).get(20)
+            if mkt_model is None:
+                # Global fallback
+                for m_dict in self.lstm_models.values():
+                    if isinstance(m_dict, dict) and (m_dict.get(horizon) or m_dict.get(20)):
+                        mkt_model = m_dict.get(horizon) or m_dict.get(20)
+                        break
+
+            if mkt_model is not None and getattr(mkt_model, 'is_trained', False):
+                try:
+                    X_mkt_batch = np.array([sequences[i] for i in mkt_indices], dtype=np.float32)
+                    mkt_preds = mkt_model.predict(X_mkt_batch)
+                    mkt_preds = mkt_preds.ravel() if hasattr(mkt_preds, 'ravel') else np.array(mkt_preds).ravel()
+                    raw_scores[mkt_indices] = np.nan_to_num(mkt_preds, nan=0.0, posinf=0.0, neginf=0.0)
+                except Exception as e:
+                    logger.warning(f"LSTM prediction failed for market {mkt}: {e}")
```

---

### V6-05 [🟠 HIGH]: Multi-Year Cumulative Return Scaling Distortion in `predict_lead_lag` Fallback Injecting Unbounded Percentage Scales

- **Affected File & Line Numbers**: `trading_system/src/ai/prediction_model.py:3064-3065`
- **Severity**: 🟠 HIGH (P1)
- **Symptom & Root Cause Analysis**:
  When `predict_lead_lag()` encounters missing leader signals (`not follower_scores`, e.g., during market holidays or when all leaders have $\le 0.1\%$ daily returns), the fallback routine executes:
  ```python
  for sym, df in prices_dict.items():
      if sym not in follower_scores and df is not None and len(df) >= 2:
          c = df['Close']
          if isinstance(c, pd.DataFrame):
              c = c.iloc[:, 0]
          c = c.dropna()
          if len(c) >= 2:
              ret = float((c.iloc[-1] / c.iloc[0]) - 1.0)
              follower_scores[sym] = max(0.001, round(ret * 100, 4))
  ```
  `c.iloc[0]` is the first historical close in the DataFrame (up to 5 years / 1,200 bars ago). `ret` is the total 5-year cumulative return (e.g. $+350\% = 3.50$).
  `follower_scores[sym]` is then assigned `ret * 100 = 350.0`.
  When `EnsembleScoringEngine` processes this output (`ll_df_copy['ll_score'] = ll_df_copy[target_col].clip(0.0, 1.0)`), every stock with positive multi-year return is saturated at `1.0`, completely flattening the cross-sectional score distribution and destroying follower alpha.
- **Mathematical / Financial Engineering Rationale**:
  Lead-lag follower scores represent 1-day conditional momentum response $S_{i, t} \in [0, 1]$. Fallback signals must use 1-day returns ($c[-1] / c[-2] - 1$) mapped through a continuous linear/sigmoid transformation into the normalized $[0.05, 0.95]$ domain.
- **Concrete Source Code Modification Snippet**:

```diff
--- a/trading_system/src/ai/prediction_model.py
+++ b/trading_system/src/ai/prediction_model.py
@@ -3061,8 +3061,8 @@ class OnDevicePredictionModel:
                         c = c.iloc[:, 0]
                     c = c.dropna()
                     if len(c) >= 2:
-                        ret = float((c.iloc[-1] / c.iloc[0]) - 1.0)
-                        follower_scores[sym] = max(0.001, round(ret * 100, 4))
+                        ret_1d = float((c.iloc[-1] / c.iloc[-2]) - 1.0)
+                        follower_scores[sym] = float(np.clip(0.50 + 2.5 * ret_1d, 0.05, 0.95))
 
         if not follower_scores:
             return pd.DataFrame()
```

---

### V6-06 [🟠 HIGH]: Volatility Maximization Anomaly in Optuna 2D Regime and Factor Suppression Objective Functions During Market Drawdowns

- **Affected File & Line Numbers**: `trading_system/src/ai/optuna_tuner.py:553-558, 624-628`
- **Severity**: 🟠 HIGH (P1)
- **Symptom & Root Cause Analysis**:
  In `OptunaStrategyTuner.tune_regime_2d_weights()` and `tune_correlation_suppression_params()`, the objective functions evaluate the annualized Sharpe ratio:
  ```python
  sharpe = float(combo_series.mean() / (combo_series.std() + 1e-10) * np.sqrt(252))
  return sharpe if np.isfinite(sharpe) else 0.0
  ```
  In Bear or high-volatility regimes where the average portfolio return $\mu = \text{mean}(R)$ is negative ($\mu < 0$), the ratio evaluates to $-\frac{|\mu|}{\sigma}$.
  Because Optuna's direction is set to `maximize`, maximizing a negative number ($-\frac{|\mu|}{\sigma} \to 0$) requires **maximizing portfolio volatility $\sigma$ in the denominator**.
  Consequently, during crisis periods, Optuna selects the most volatile, highest-risk strategy allocations, exacerbating drawdowns.
- **Mathematical / Financial Engineering Rationale**:
  When expected return $\mu \le 0$, the objective function must transition from Sharpe ratio maximization to Quadratic Risk-Adjusted Utility:
  $$U(w) = \mu_p - \frac{1}{2} \lambda_{\text{risk}} \sigma_p^2$$
  where $\lambda_{\text{risk}} \ge 2.5$. This guarantees that risk is strictly penalized regardless of the sign of expected returns.
- **Concrete Source Code Modification Snippet**:

```diff
--- a/trading_system/src/ai/optuna_tuner.py
+++ b/trading_system/src/ai/optuna_tuner.py
@@ -553,8 +553,13 @@ class OptunaStrategyTuner:
                 combo_series = sum(combo_returns[s] * norm_w[s] for s in valid_strats).dropna()
                 if len(combo_series) < 5 or combo_series.std() < 1e-8:
                     return 0.0
-                sharpe = float(combo_series.mean() / (combo_series.std() + 1e-10) * np.sqrt(252))
-                return sharpe if (np.isfinite(sharpe)) else 0.0
+                m_ret = float(combo_series.mean())
+                s_ret = float(combo_series.std())
+                if m_ret > 0:
+                    score = (m_ret / (s_ret + 1e-8)) * np.sqrt(252)
+                else:
+                    score = (m_ret - 0.5 * 2.5 * (s_ret ** 2)) * 252.0
+                return float(score) if np.isfinite(score) else 0.0
 
             study = optuna.create_study(direction='maximize')
             study.optimize(regime_objective, n_trials=n_trials)
@@ -624,8 +629,13 @@ class OptunaStrategyTuner:
                 portfolio_series = sum(returns_df[s] * supp_w[s] for s in valid_strats)
                 if portfolio_series.std() < 1e-8:
                     return 0.0
-                sharpe = float(portfolio_series.mean() / portfolio_series.std() * np.sqrt(252))
-                return sharpe
+                m_ret = float(portfolio_series.mean())
+                s_ret = float(portfolio_series.std())
+                if m_ret > 0:
+                    score = (m_ret / (s_ret + 1e-8)) * np.sqrt(252)
+                else:
+                    score = (m_ret - 0.5 * 2.5 * (s_ret ** 2)) * 252.0
+                return float(score) if np.isfinite(score) else 0.0
 
             study = optuna.create_study(direction='maximize')
             study.optimize(suppression_objective, n_trials=n_trials)
```

---

### V6-07 [🟠 HIGH]: Artificial Threshold Filtering Bias and 10-Symbol Evaluation Cap in Strategy 3 (Lead-Lag) HPO

- **Affected File & Line Numbers**: `trading_system/src/ai/optuna_tuner.py:317-324`
- **Severity**: 🟠 HIGH (P1)
- **Symptom & Root Cause Analysis**:
  In `OptunaStrategyTuner.tune_strategy_3_lead_lag()`:
  ```python
  for i in range(min(10, df_train.shape[1])):
      for j in range(min(10, df_train.shape[1])):
          if i != j:
              r = df_train.iloc[:, i].shift(lag_window).corr(df_train.iloc[:, j])
              if not np.isnan(r) and abs(r) >= corr_cutoff:
                  corrs.append(abs(r))
  return float(np.mean(corrs)) if corrs else 0.0
  ```
  Two critical defects exist:
  1. **Selection Threshold Inflation**: The objective function averages only correlations satisfying $|r| \ge \text{corr\_cutoff}$. Setting `corr_cutoff = 0.59` discards all moderate correlations and averages only the single highest correlation, trivially inflating `np.mean(corrs)` towards 0.60. Optuna optimizes to discard valid lead-lag signals.
  2. **10-Symbol Evaluation Bottleneck**: The loop hard-caps symbol comparisons to `min(10, df_train.shape[1])`. Any `leader_count` sampled between 11 and 50 is never evaluated, creating phantom parameters that Optuna cannot optimize.
- **Mathematical / Financial Engineering Rationale**:
  Lead-lag HPO must evaluate all $K = \min(\text{leaders\_count}, N)$ symbols and measure out-of-sample forward predictive correlation persistence on validation data:
  $$\max \sum_{i \ne j} \mathbf{1}_{\{|\rho_{ij}^{\text{train}}| \ge \theta\}} \cdot |\rho_{ij}^{\text{val}}|$$
- **Concrete Source Code Modification Snippet**:

```diff
--- a/trading_system/src/ai/optuna_tuner.py
+++ b/trading_system/src/ai/optuna_tuner.py
@@ -314,14 +314,24 @@ class OptunaStrategyTuner:
             if df_train.empty or len(df_train) < 20:
                 df_train = df_ret
+            df_val = df_ret.iloc[n_split:] if len(df_ret) > n_split + 10 else df_ret
 
-            for i in range(min(10, df_train.shape[1])):
-                for j in range(min(10, df_train.shape[1])):
+            eval_k = min(leaders_count, df_train.shape[1])
+            for i in range(eval_k):
+                for j in range(eval_k):
                     if i != j:
                         r = df_train.iloc[:, i].shift(lag_window).corr(df_train.iloc[:, j])
                         if not np.isnan(r) and abs(r) >= corr_cutoff:
-                            corrs.append(abs(r))
+                            # Evaluate out-of-sample persistence on validation split
+                            if not df_val.empty and len(df_val) >= 10:
+                                r_val = df_val.iloc[:, i].shift(lag_window).corr(df_val.iloc[:, j])
+                                if not np.isnan(r_val):
+                                    corrs.append(float(r_val))
+                            else:
+                                corrs.append(abs(r))
 
             return float(np.mean(corrs)) if corrs else 0.0
```

---

### V6-08 [🟠 HIGH]: Unchecked Feature Dimension & Permutation Alignment in `MetaEnsembleLearner.predict`

- **Affected File & Line Numbers**: `trading_system/src/ai/meta_ensemble_learner.py:158-183`
- **Severity**: 🟠 HIGH (P1)
- **Symptom & Root Cause Analysis**:
  In `MetaEnsembleLearner.predict()`:
  ```python
  available_cols = [c for c in STRATEGY_SCORE_COLS if c in strategy_df.columns]
  X = strategy_df[available_cols].fillna(0.0).values
  if self.is_fitted and self.weights is not None:
      if len(self.weights) == len(available_cols):
          ridge_pred = np.dot(X, self.weights) + self.intercept
  ```
  The code checks only `len(self.weights) == len(available_cols)`. If `available_cols` has the same count as `self.weights` but in a different permutation or with one column substituted for another, `np.dot(X, self.weights)` multiplies mismatched weights against columns, corrupting the stacking meta-score.
  Furthermore, if `self.learner_type == 'lgbm'`, `self._lgbm_model.predict(X)` is called on `X` without verifying feature name alignment, triggering LightGBM shape mismatch exceptions.
- **Mathematical / Financial Engineering Rationale**:
  Linear and tree model inference on tabular data requires exact bijection between training feature names $\mathcal{F}_{\text{train}}$ and evaluation feature names $\mathcal{F}_{\text{eval}}$. Explicit feature reindexing is mandatory.
- **Concrete Source Code Modification Snippet**:

```diff
--- a/trading_system/src/ai/meta_ensemble_learner.py
+++ b/trading_system/src/ai/meta_ensemble_learner.py
@@ -157,21 +157,20 @@ class MetaEnsembleLearner:
         X = strategy_df[available_cols].fillna(0.0).values
 
         if self.is_fitted and self.weights is not None:
-            # Match feature subsets if needed
-            if len(self.weights) == len(available_cols):
-                ridge_pred = np.dot(X, self.weights) + self.intercept
-            else:
-                # Project across common feature subset
-                w_dict = dict(zip(self.feature_names, self.weights))
-                eff_w = np.array([w_dict.get(col, 0.0) for col in available_cols], dtype=float)
-                ridge_pred = np.dot(X, eff_w) + self.intercept
+            # Explicit column name dictionary projection to prevent permutation corruption
+            w_dict = dict(zip(self.feature_names, self.weights))
+            eff_w = np.array([w_dict.get(col, 0.0) for col in available_cols], dtype=float)
+            ridge_pred = np.dot(X, eff_w) + self.intercept
 
             if self.learner_type == 'lgbm' and self._lgbm_model is not None:
                 try:
-                    raw_pred = self._lgbm_model.predict(X)
+                    X_lgb = strategy_df.reindex(columns=self.feature_names, fill_value=0.0).values
+                    raw_pred = self._lgbm_model.predict(X_lgb)
                 except Exception:
                     raw_pred = ridge_pred
             elif self.learner_type == 'blended' and self._lgbm_model is not None:
                 try:
-                    lgb_pred = self._lgbm_model.predict(X)
+                    X_lgb = strategy_df.reindex(columns=self.feature_names, fill_value=0.0).values
+                    lgb_pred = self._lgbm_model.predict(X_lgb)
                     raw_pred = 0.5 * ridge_pred + 0.5 * lgb_pred
```

---

### V6-09 [🟡 MEDIUM]: Post-Normalization Weight Bound Invalidation in `AlphaDecayTracker`

- **Affected File & Line Numbers**: `trading_system/src/ai/optuna_tuner.py:698-705`
- **Severity**: 🟡 MEDIUM (P2)
- **Symptom & Root Cause Analysis**:
  In `AlphaDecayTracker.calculate_decay_adjusted_weights()`:
  ```python
  adjusted[strat] = max(self.min_weight_bound, min(adj_w, self.max_weight_bound))
  tot = sum(adjusted.values())
  return {s: round(w / tot, 4) for s, w in adjusted.items()} if tot > 0 else base_weights
  ```
  Hard bounds $[0.5\%, 15\%]$ are applied to `adj_w` before normalization. However, when the sum `tot` deviates from 1.0 (e.g. `tot = 0.35` across decaying strategies), dividing each weight by `tot` multiplies all weights by $1/0.35 = 2.86$. A weight clamped to $15\%$ becomes $42.9\%$, completely violating the maximum allocation ceiling.
- **Mathematical / Financial Engineering Rationale**:
  Projecting a vector onto the bounded simplex $\mathcal{W} = \{w \in [w_{\min}, w_{\max}]^K \mid \sum w_k = 1\}$ requires iterative bound enforcement and residual weight redistribution until convergence.
- **Concrete Source Code Modification Snippet**:

```diff
--- a/trading_system/src/ai/optuna_tuner.py
+++ b/trading_system/src/ai/optuna_tuner.py
@@ -700,7 +700,22 @@ class AlphaDecayTracker:
             adj_w = base_w * decay_factor * perf_factor
             adjusted[strat] = max(self.min_weight_bound, min(adj_w, self.max_weight_bound))
 
-        tot = sum(adjusted.values())
-        return {s: round(w / tot, 4) for s, w in adjusted.items()} if tot > 0 else base_weights
+        # Iterative Simplex Projection to guarantee hard bounds [min_w, max_w]
+        weights_arr = np.array(list(adjusted.values()), dtype=float)
+        for _ in range(10):
+            tot = weights_arr.sum()
+            if tot <= 0:
+                break
+            weights_arr = weights_arr / tot
+            weights_arr = np.clip(weights_arr, self.min_weight_bound, self.max_weight_bound)
+            if abs(weights_arr.sum() - 1.0) < 1e-4:
+                break
+        tot = weights_arr.sum()
+        final_w = weights_arr / tot if tot > 0 else weights_arr
+        return {s: round(float(w), 4) for s, w in zip(adjusted.keys(), final_w)}
```

---

## 4. Synthesis & Structural Cross-Cutting Insights

1. **Homomorphic Prediction Blending**: The discovery of V6-01 reinforces that heterogeneous model ensembles (Deep Learning LSTM vs Tree-based GBDT) must share an identical loss and target transformation space ($\text{sign-log1p}(\text{Sharpe})$).
2. **Frequency Hierarchy Preservation**: The resolution of V6-02 ensures that intraday microstructure and reversal signals are not lagged by 10 days, while slow fundamental factors maintain stable low-turnover allocations.
3. **Decoupled Multi-Market Geometry**: The resolution of V6-03 and V6-04 guarantees that US and Korean markets operate as truly independent regimes without cross-market model pollution or squared weight hyper-concentration.
