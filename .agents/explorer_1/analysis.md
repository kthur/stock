# Technical Analysis & Forensic Audit Report: Domain 1 & Domain 5

**Audit Date**: 2026-08-22  
**Target Project**: `kthur/stock` (`d:\Finance\code\stock`)  
**Auditor**: `explorer_1` (Survey Agent for Domain 1 & Domain 5)  
**Scope**: 
- **Domain 1: AI/ML & Prediction Integrity (V6-01 ~ V6-08)**
- **Domain 5: Pipeline Orchestration, CI/CD & Infrastructure (V6-32 ~ V6-35)**

---

## 1. Executive Summary & Baseline Test Audit

### 1.1 Baseline Test Suite Execution
- **Command**: `.venv\Scripts\python.exe -m pytest tests/ -q`
- **Total Test Items Collected**: 1,279 items across 143 test files.
- **Observed Baseline Characteristics**:
  - The repository has an extensive existing regression test suite covering quantitative strategies, optimization engines, and execution layers.
  - Test files in `tests/` span unit tests, integration tests, adversarial stress tests, and end-to-end verification.
  - Standalone verification scripts in `tests/` that define parameterized helper functions starting with `test_` (such as `test_challenger_2_math_verification.py`) are collected by pytest and require isolation/refactoring.

### 1.2 Audit Mission & Core Findings
Our forensic investigation audited all 12 tasks across Domain 1 (V6-01 through V6-08) and Domain 5 (V6-32 through V6-35):
- **Domain 1 (8 Tasks)**: Resolves critical target domain homomorphism mismatches between LSTM and tree models, column name schema mismatches in multi-horizon decay filtering, dual-regime weight squaring and cross-market contamination, LSTM model hijacking across markets, multi-year cumulative return scaling distortions in lead-lag fallbacks, Optuna bear-market volatility maximization anomalies, Lead-Lag HPO 10-symbol bottlenecks, and meta-ensemble feature permutation corruption.
- **Domain 5 (4 Tasks)**: Eliminates unhandled `NameError: name 'json' is not defined` bootstrap failure in `src/config.py`, adds top-level `try...finally` lifecycle and DB lock management in `run_pipeline.py`, corrects malformed regex fallback parsing in `generate_run_snapshot.py`, and aligns KST timestamps and dynamic liquidity/friction environment configuration in `TradingConfig`.

---

## 2. Domain 1 Forensic Investigation (AI/ML & Prediction Integrity: V6-01 ~ V6-08)

### V6-01: Strict Causal LSTM Training Target Log1p Domain Disconnect
- **Severity**: 🔴 CRITICAL (P0)
- **Target File & Lines**: `trading_system/src/ai/prediction_model.py:1514, 1775-1784, 2487-2505`
- **Root Cause**:
  In `prediction_model.py`, tree-based regression models (XGBoost, LightGBM, CatBoost) are trained on Sharpe-transformed returns via non-linear mapping:
  $$y_{\text{tree}} = \text{transform\_sharpe}(target) = \text{sign}(x) \cdot \ln(1 + |x|)$$
  However, in `_prepare_lstm_data()` (line 1514), the LSTM training target is read directly without transformation:
  $$y_{\text{lstm}} = \text{group\_sorted}[target\_col].\text{values} = x$$
  During inference in `_predict_regression()` (lines 2487-2488), tree predictions ($\hat{y}_{\text{tree}} \in \text{log1p space}$) and LSTM predictions ($\hat{y}_{\text{lstm}} \in \text{linear space}$) are convexly blended into $\hat{y}_{\text{blend}}$, and `inverse_transform_sharpe()` is applied to the blended prediction:
  $$\hat{R} = \text{sign}(\hat{y}_{\text{blend}}) \cdot \left(\exp(|\hat{y}_{\text{blend}}|) - 1\right) \cdot \sigma_{20d}$$
  Because $\hat{y}_{\text{lstm}}$ was already in linear space, exponentiating it ($\exp(\hat{y}_{\text{lstm}}) - 1$) produces an exponential explosion (e.g. Sharpe 3.0 becomes $\exp(3.0)-1 = 19.086$, a 636% distortion).
- **Remedy**:
  In `_prepare_lstm_data()`, map targets through `transform_sharpe(group_sorted[target_col]).values` to guarantee target space homomorphism across all regressors.
- **Proposed Git Diff**:
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

### V6-02: Multi-Horizon Exponential Decay Filter Key-Column Schema Mismatch
- **Severity**: 🔴 CRITICAL (P0)
- **Target File & Lines**: `trading_system/src/ai/ensemble_scorer.py:2559-2591, 2620-2625`
- **Root Cause**:
  `STRATEGY_HALF_LIVES` defines continuous exponential convolutional half-lives $\tau_k \in [0.5, 60.0]$ indexed by canonical strategy names (`"microstructure": 0.5`, `"short_term_reversal": 1.5`, `"lead_lag": 5.0`, `"rim_valuation": 45.0`, etc.).
  In `apply_exponential_decay_filter()`, the loop checks `tau = half_lives.get(col, 10.0)` where `col` is the actual score column name (`'microstructure_score'`, `'reversal_score'`, `'ll_score'`, `'rim_score'`, etc.).
  Because none of the score column names match canonical dictionary keys, `half_lives.get(col, 10.0)` always evaluated to `None` and defaulted to `tau = 10.0` for **every strategy**, and non-strategy numeric metadata columns (`close`, `volume`) were smoothed.
- **Remedy**:
  Add an explicit alias adapter `score_col_to_strat` mapping all 31 score columns to canonical strategy identifiers, and apply filtering only when `strat_key in half_lives`.
- **Proposed Git Diff**:
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

### V6-03: Dual-Regime Weight Squaring & US-KR Weight Cross-Contamination
- **Severity**: 🟠 HIGH (P1)
- **Target File & Lines**: `trading_system/src/ai/ensemble_scorer.py:1900-1915`
- **Root Cause**:
  In `EnsembleScoringEngine.combine_predictions()`, `weights` is initialized with US regime weights and modified by VIF factor suppression ($w_{\text{suppressed}}$).
  Then lines 1900-1914 executed:
  `eff_us_weights = {k: us_weights[k] * weights[k]}` (which squares US weights)
  `eff_kr_weights = {k: kr_weights[k] * weights[k]}` (which multiplies Korean weights by US suppressed weights).
  This caused extreme weight concentration in US equity rankings and contaminated Korean defensive regimes with aggressive US momentum weights.
- **Remedy**:
  Set `eff_us_weights = dict(weights)` and extract relative penalty ratios $P_k = \frac{w_{\text{suppressed}, k}}{w_{\text{us}, k} + \epsilon}$, applying $P_k$ linearly to `kr_weights` before normalizing.
- **Proposed Git Diff**:
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

### V6-04: Cross-Market Model Hijacking in `predict_lstm`
- **Severity**: 🟠 HIGH (P1)
- **Target File & Lines**: `trading_system/src/ai/prediction_model.py:2593-2615`
- **Root Cause**:
  In `predict_lstm()`, the model search loop picked the first trained model in `self.lstm_models` (e.g. `sp500`) and evaluated ALL symbols across all markets (including KOSPI, KOSDAQ, RUSSELL2000) against it in a single batch `X_batch`, ignoring the market-specific models fitted in `train()`.
- **Remedy**:
  Partition `valid_symbols` by market (`sym_to_mkt`), and evaluate each market subset against its respective market-specific LSTM model (`self.lstm_models[mkt][horizon]`), falling back to `KRX` for KOSPI/KOSDAQ and then global fallback.
- **Proposed Git Diff**:
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

### V6-05: Multi-Year Cumulative Return Scaling Distortion in `predict_lead_lag` Fallback
- **Severity**: 🟠 HIGH (P1)
- **Target File & Lines**: `trading_system/src/ai/prediction_model.py:3064-3065`
- **Root Cause**:
  When `predict_lead_lag()` triggered fallback, it calculated `ret = (c.iloc[-1] / c.iloc[0]) - 1.0` (multi-year cumulative return) and scaled by 100 (`follower_scores[sym] = max(0.001, round(ret * 100, 4))`). A stock with +300% return received 300.0, saturating `ll_score` at 1.0 and destroying cross-sectional variance.
- **Remedy**:
  Compute 1-day return `ret_1d = (c.iloc[-1] / c.iloc[-2]) - 1.0` and map into normalized $[0.05, 0.95]$ domain via `follower_scores[sym] = float(np.clip(0.50 + 2.5 * ret_1d, 0.05, 0.95))`.
- **Proposed Git Diff**:
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

### V6-06: Volatility Maximization Anomaly in Optuna 2D Regime and Factor Suppression Objective Functions & Alpha Decay Tracker Bounds
- **Severity**: 🟠 HIGH (P1)
- **Target File & Lines**: `trading_system/src/ai/optuna_tuner.py:553-558, 624-628, 698-705`
- **Root Cause**:
  In `tune_regime_2d_weights()` and `tune_correlation_suppression_params()`, the objective maximized Sharpe ratio $\frac{\mu}{\sigma}\sqrt{252}$. During market downturns where $\mu \le 0$, maximizing negative Sharpe ratio $-\frac{|\mu|}{\sigma}$ maximized portfolio volatility $\sigma$ in the denominator.
  In addition, `AlphaDecayTracker.calculate_decay_adjusted_weights()` divided clamped weights by `tot`, causing normalized weights to exceed `max_weight_bound` when `tot < 1.0`.
- **Remedy**:
  When $\mu > 0$, maximize Sharpe; when $\mu \le 0$, transition to quadratic risk-adjusted utility $(\mu - 0.5 \cdot \lambda \sigma^2) \times 252.0$ with $\lambda = 2.5$.
  In `AlphaDecayTracker`, apply iterative bounded simplex projection.
- **Proposed Git Diff**:
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
@@ -700,7 +705,22 @@ class AlphaDecayTracker:
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

### V6-07: Selection Threshold Inflation & 10-Symbol Bottleneck in Lead-Lag HPO
- **Severity**: 🟠 HIGH (P1)
- **Target File & Lines**: `trading_system/src/ai/optuna_tuner.py:317-324`
- **Root Cause**:
  In `tune_strategy_3_lead_lag()`, the correlation loop was hardcoded to `min(10, df_train.shape[1])` (ignoring `leaders_count` values up to 50), and averaged only $|r| \ge \text{corr\_cutoff}$, creating threshold inflation that encouraged discarding valid lead-lag correlations. Out-of-sample persistence on `df_val` was omitted.
- **Remedy**:
  Evaluate $K = \min(\text{leaders\_count}, df\_train.shape[1])$, evaluate correlation persistence on validation partition `df_val`, and average across candidates.
- **Proposed Git Diff**:
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

### V6-08: Feature Permutation Corruption in `MetaEnsembleLearner`
- **Severity**: 🟠 HIGH (P1)
- **Target File & Lines**: `trading_system/src/ai/meta_ensemble_learner.py:158-183`
- **Root Cause**:
  `MetaEnsembleLearner.predict()` checked `if len(self.weights) == len(available_cols): ridge_pred = np.dot(X, self.weights)`, which blindly multiplied weights against columns without checking column name ordering. For LightGBM models, `predict(X)` failed when input column order or subset differed from training features.
- **Remedy**:
  Explicitly map weights via `w_dict = dict(zip(self.feature_names, self.weights))` against `available_cols`, and reindex DataFrame columns via `strategy_df.reindex(columns=self.feature_names, fill_value=0.0).values` for tree predictions.
- **Proposed Git Diff**:
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

## 3. Domain 5 Forensic Investigation (Pipeline Orchestration & Infrastructure: V6-32 ~ V6-35)

### V6-32: Unhandled `NameError: name 'json' is not defined` in `src/config.py`
- **Severity**: 🔴 CRITICAL (P0)
- **Target File & Lines**: `trading_system/src/config.py:1-15, 41-62`
- **Root Cause**:
  `_build_market_lookup_table()` executes at module import time (line 62) to parse `MARKET_COSTS_JSON` environment variables. Line 46 uses `json.loads(env_costs)`, but `import json` was omitted from lines 1-15, causing an immediate fatal `NameError: name 'json' is not defined` whenever custom cost JSON is injected.
- **Remedy**:
  Add `import json` to top-level imports in `src/config.py`.
- **Proposed Git Diff**:
```diff
--- a/trading_system/src/config.py
+++ b/trading_system/src/config.py
@@ -1,4 +1,5 @@
+import json
 import logging
 import math
 import os
 from dataclasses import dataclass, field
 from pathlib import Path
 from typing import Optional, Any
```

---

### V6-33: Missing Top-Level `try...finally` DB Lock & State Cleanup in `run_pipeline.py`
- **Severity**: 🔴 CRITICAL (P0)
- **Target File & Lines**: `trading_system/run_pipeline.py:1193-1224, 4161-4212`
- **Root Cause**:
  In `execute_prediction_pipeline()`, `storage.start_pipeline_run(...)` registers a pipeline run. If an exception occurs at any point during pipeline execution, `storage.finish_pipeline_run(...)` is never called, leaving the run in `RUNNING` status permanently, and `price_db.close()` / `storage.close()` are bypassed, leaving dangling SQLite WAL file locks.
- **Remedy**:
  Wrap the entire execution body in a comprehensive `try...except...finally` block. On unhandled exceptions, mark `status="FAILED"` in `pipeline_run_history`, and guarantee `price_db.close()` / `storage.close()` in `finally`.
- **Proposed Git Diff**:
```diff
--- a/trading_system/run_pipeline.py
+++ b/trading_system/run_pipeline.py
@@ -1194,6 +1194,10 @@ def execute_prediction_pipeline():
     _pipeline_start_time = time.time()
     logger.info("Starting consolidated market indicator and prediction pipeline...")

+    storage = None
+    price_db = None
+    current_run_id = None
+    try:
         # Ensure result directory exists early
         result_dir = os.environ.get("OUTPUT_RESULT_DIR", os.path.join(os.path.dirname(__file__), "result"))
         os.makedirs(result_dir, exist_ok=True)
@@ -4180,33 +4184,39 @@ def execute_prediction_pipeline():
         except Exception as e:
             logger.warning(f"Verification failed: Error reading/parsing pipeline_result.txt: {e}")

-        # Finalize pipeline run tracking in DB
-        if 'current_run_id' in locals() and current_run_id and storage is not None:
-            try:
-                total_syms = len(universe) if 'universe' in locals() and universe is not None else 0
-                dur_secs = time.time() - _pipeline_start_time if '_pipeline_start_time' in locals() else 0.0
-                active_mkts = list(universe['market'].unique()) if 'universe' in locals() and universe is not None and 'market' in universe.columns else []
-                regime_name = current_2d_regime if 'current_2d_regime' in locals() else ""
-                storage.finish_pipeline_run(
-                    run_id=current_run_id,
-                    status="SUCCESS",
-                    markets=active_mkts,
-                    total_symbols=total_syms,
-                    duration_seconds=dur_secs,
-                    regime_detected=regime_name
-                )
-                storage.prune_old_history(keep_days=180)
-                logger.info(f"[RUN HISTORY] Finalized run_id={current_run_id} (duration={dur_secs:.1f}s, symbols={total_syms})")
-            except Exception as _fin_e:
-                logger.warning(f"[RUN HISTORY] Failed to finalize pipeline run history: {_fin_e}")
-
+        return res_df, message_text
+    except Exception as _pipe_err:
+        if current_run_id and storage is not None:
+            try:
+                storage.finish_pipeline_run(
+                    run_id=current_run_id,
+                    status="FAILED",
+                    duration_seconds=time.time() - _pipeline_start_time,
+                    error_summary=str(_pipe_err)[:500]
+                )
+            except Exception:
+                pass
+        raise
+    finally:
+        if current_run_id and storage is not None and 'res_df' in locals() and not res_df.empty:
+            try:
+                total_syms = len(universe) if 'universe' in locals() and universe is not None else 0
+                dur_secs = time.time() - _pipeline_start_time
+                active_mkts = list(universe['market'].unique()) if 'universe' in locals() and universe is not None and 'market' in universe.columns else []
+                regime_name = current_2d_regime if 'current_2d_regime' in locals() else ""
+                storage.finish_pipeline_run(
+                    run_id=current_run_id,
+                    status="SUCCESS",
+                    markets=active_mkts,
+                    total_symbols=total_syms,
+                    duration_seconds=dur_secs,
+                    regime_detected=regime_name
+                )
+                storage.prune_old_history(keep_days=180)
+            except Exception:
+                pass
         try:
             if hasattr(price_db, 'close') and price_db is not None:
                 price_db.close()
             if hasattr(storage, 'close') and storage is not None:
                 storage.close()
         except Exception as e:
             logger.debug(f"DB close during pipeline cleanup: {e}")
```

---

### V6-34: Malformed Text Fallback Parser in `generate_run_snapshot.py`
- **Severity**: 🟠 HIGH (P1)
- **Target File & Lines**: `trading_system/generate_run_snapshot.py:118-142`
- **Root Cause**:
  When `market_indicators.db` is absent in CI/CD release jobs, `generate_snapshot()` falls back to parsing `ensemble_predictions.txt`. The fallback split lines by whitespace and checked `parts[2].isdigit()`. Because `parts[2]` was the Korean company name string (`"삼성전자"`), `isdigit()` evaluated to `False`, forcing a default `ensemble_score: 0.50` and empty `strategy_scores: {}` for all 50 top picks.
- **Remedy**:
  Parse lines with regex matching `r"^\s*(\d+)\.\s+(\S+)\s+(.+?)\s+([+-]?\d+\.?\d*)%\s+([+-]?\d+\.?\d*)%"`, extracting rank, symbol, company name, ensemble score percentage, net expected return, and individual strategy factor scores.
- **Proposed Git Diff**:
```diff
--- a/trading_system/generate_run_snapshot.py
+++ b/trading_system/generate_run_snapshot.py
@@ -124,16 +124,37 @@ def generate_snapshot(result_dir: Path, db_path: Path, output_file: Path) -> Di
                 rank = 1
                 for line in content.splitlines():
-                    if re.match(r"^\s*\d+\s+[A-Za-z0-9.]+", line):
-                        parts = line.split()
-                        if len(parts) >= 3:
+                    m = re.match(r"^\s*(\d+)\.\s+(\S+)\s+(.+?)\s+([+-]?\d+\.?\d*)%\s+([+-]?\d+\.?\d*)%", line)
+                    if m:
+                        r_num, sym, name, ens_sc_str, exp_ret_str = m.groups()
+                        rest = line[m.end():].split()
+                        strat_map = {}
+                        score_keys = [
+                            'reg_score', 'surge_score', 'll_score', 'vcp_rule_score', 'vcp_ml_score',
+                            'lstm_score', 'stat_arb_score', 'sector_score', 'rim_score', 'event_score',
+                            'mq_score', 'iv_skew_score', 'order_flow_score', 'reversal_score',
+                            'arm_score', 'card_score', 'latr_score', 'inst_foreign_sector_score',
+                            'supply_chain_score', 'sentiment_score', 'factor_neutralized_score',
+                            'vol_target_score', 'microstructure_score', 'accruals_quality_score',
+                            'short_squeeze_score', 'valueup_catalyst_score', 'trend_efficiency_score',
+                            'gamma_squeeze_score', 'insider_buying_score', 'darkpool_score',
+                            'earnings_tone_drift_score'
+                        ]
+                        for idx, k in enumerate(score_keys):
+                            if idx < len(rest):
+                                val_s = rest[idx].rstrip('%')
+                                try:
+                                    strat_map[k] = round(float(val_s) / 100.0, 4)
+                                except ValueError:
+                                    pass
                         top_picks.append({
-                                "rank": rank,
-                                "symbol": parts[1],
-                                "ensemble_score": float(parts[2]) if parts[2].replace('.', '', 1).isdigit() else 0.5,
-                                "net_expected_return_pct": 0.0,
+                                "rank": int(r_num),
+                                "symbol": sym,
+                                "ensemble_score": round(float(ens_sc_str) / 100.0, 4),
+                                "net_expected_return_pct": round(float(exp_ret_str), 2),
                                 "regime": regime_detected,
                                 "portfolio_weight": 0.0,
-                                "strategy_scores": {}
+                                "strategy_scores": strat_map
                             })
                             rank += 1
                             if rank > 50:
```

---

### V6-35: Ingestion Timestamp vs Report Header Timezone Desynchronization
- **Severity**: 🟡 MEDIUM (P2)
- **Target File & Lines**: `trading_system/run_pipeline.py:1233, 2698-2701` and `trading_system/src/config.py:230-335`
- **Root Cause**:
  `run_pipeline.py:1233` used `datetime.now().strftime('%Y-%m-%d')` (naive UTC in container environments) to record market indicators and predictions, while output reports bound `KST` (UTC+9), causing date desynchronization between database records and published text headers.
  Additionally, several critical configuration parameters (`min_daily_volume_krx`, `min_daily_volume_sp500`, `slippage_krx_market_order`, `portfolio_capital_krw`, `oms_net_alpha_safety_margin`, `oms_limit_up_lock_threshold`) were declared on `TradingConfig` but omitted from `__post_init__` environment variable parsing.
- **Remedy**:
  Bind `KST = timezone(timedelta(hours=9))` on line 1233 for indicator storage dates, and add environment variable parsing for all liquidity and safety parameters in `TradingConfig.__post_init__`.
- **Proposed Git Diff**:
```diff
--- a/trading_system/run_pipeline.py
+++ b/trading_system/run_pipeline.py
@@ -1230,7 +1230,9 @@ def execute_prediction_pipeline():
         market_summary = storage.get_latest_global_indicators()

     # 3. Store indicators
-    date_str = datetime.now().strftime('%Y-%m-%d')
+    from datetime import timezone, timedelta
+    KST = timezone(timedelta(hours=9))
+    date_str = datetime.now(KST).strftime('%Y-%m-%d')
     with storage.pipeline_stage("global_indicators"):
         storage.save_indicators(market_summary, date_str)
     logger.info("Saved market indicators to database.")
```

---

## 4. Test Coverage & Gap Analysis for Domain 1 & Domain 5

| Task ID | Target Module | Existing Test Files | Existing Test Coverage | New Test Cases Required |
|---|---|---|---|---|
| **V6-01** | `src.ai.prediction_model` | `tests/test_prediction_model.py`, `tests/test_lstm_predictor.py` | Basic LSTM model vectorization | Test `_prepare_lstm_data` target transform equality with `transform_sharpe` and test regression blend output bounds |
| **V6-02** | `src.ai.ensemble_scorer` | `tests/test_hpo_and_2d_ensemble.py`, `tests/test_adversarial_ensemble_scorer_challenger.py` | Calibration and 5-strategy scoring | Test `apply_exponential_decay_filter` with fast-tier (`microstructure_score`), slow-tier (`rim_score`), and non-strategy numeric columns |
| **V6-03** | `src.ai.ensemble_scorer` | `tests/test_dual_regime_weighting.py` | Basic dual regime weight assignment | Test `combine_predictions` with decoupled US (`BULL`) and KR (`BEAR`) regimes, verifying no weight squaring and no cross-contamination |
| **V6-04** | `src.ai.prediction_model` | `tests/test_prediction_model.py` | Single LSTM prediction | Test `predict_lstm` with multiple market models (KOSPI, SP500) and verify proper market-partitioned batch evaluation |
| **V6-05** | `src.ai.prediction_model` | `tests/test_prediction_model.py` | Empty leader fallback check | Test `predict_lead_lag` fallback with 5-year price series (+300% cumulative, +1% 1-day), asserting score $\in [0.05, 0.95]$ |
| **V6-06** | `src.ai.optuna_tuner` | `tests/test_hpo_and_2d_ensemble.py` | Positive returns HPO | Test `tune_regime_2d_weights` and `tune_correlation_suppression_params` under negative mean returns ($\mu \le 0$) to verify quadratic utility risk penalty, and test `AlphaDecayTracker` iterative simplex projection |
| **V6-07** | `src.ai.optuna_tuner` | `tests/test_hpo_and_2d_ensemble.py` | 5-symbol Lead-Lag HPO | Test `tune_strategy_3_lead_lag` with 25 symbols and `leaders_count=15`, verifying all $K$ symbols evaluated and validation persistence |
| **V6-08** | `src.ai.meta_ensemble_learner` | `tests/test_meta_and_hybrid_ensemble.py`, `tests/test_cross_market_meta_stacking.py` | In-order feature prediction | Test `MetaEnsembleLearner.predict` with shuffled / permuted / subset columns, asserting invariant output |
| **V6-32** | `src.config` | `tests/test_config.py` | Basic env overrides | Test `MARKET_COSTS_JSON` environment override parsing in `_build_market_lookup_table()` |
| **V6-33** | `run_pipeline` | `tests/test_pipeline_integration.py` | Normal pipeline execution | Test pipeline crash recovery, verifying `status="FAILED"` recorded and SQLite connections closed in `finally` |
| **V6-34** | `generate_run_snapshot` | None | None | Test `generate_snapshot` text fallback parser with regex pattern matching Korean and US equity output lines |
| **V6-35** | `run_pipeline`, `src.config` | `tests/test_config.py` | Basic spread configs | Test `TradingConfig.__post_init__` parsing of `MIN_DAILY_VOLUME_KRX`, `SLIPPAGE_KRX_MARKET_ORDER`, etc., and KST date alignment |

---

## 5. Concrete Implementation & Verification Plan

### 5.1 Phased Implementation Order
1. **Phase 1: Critical Bootstrap & Syntax Fixes (P0)**:
   - Apply V6-32 (`src/config.py`: `import json`) to guarantee configuration parsing reliability.
   - Apply V6-01 (`src/ai/prediction_model.py`: `transform_sharpe` in `_prepare_lstm_data()`).
   - Apply V6-02 (`src/ai/ensemble_scorer.py`: `score_col_to_strat` alias map in `apply_exponential_decay_filter()`).
2. **Phase 2: High-Severity AI/ML Logic Corrections (P1)**:
   - Apply V6-03 (`src/ai/ensemble_scorer.py`: linear US weights and decoupled Korean suppression penalty).
   - Apply V6-04 (`src/ai/prediction_model.py`: market-aware LSTM batch prediction).
   - Apply V6-05 (`src/ai/prediction_model.py`: 1-day return normalized fallback in `predict_lead_lag()`).
   - Apply V6-06 (`src/ai/optuna_tuner.py`: quadratic bear utility and iterative bounded simplex projection).
   - Apply V6-07 (`src/ai/optuna_tuner.py`: Lead-Lag HPO $K$-symbol expansion and validation persistence).
   - Apply V6-08 (`src/ai/meta_ensemble_learner.py`: explicit column projection and DataFrame reindexing).
3. **Phase 3: Pipeline Lifecycle & Infrastructure Refinements (P0/P1/P2)**:
   - Apply V6-33 (`trading_system/run_pipeline.py`: top-level `try...except...finally` lifecycle and DB lock management).
   - Apply V6-34 (`trading_system/generate_run_snapshot.py`: regex-based text fallback parser).
   - Apply V6-35 (`trading_system/run_pipeline.py` & `src/config.py`: KST indicator dates & liquidity env vars).

### 5.2 Verification Methodology
- **Unit Verification Commands**:
  - `python -m pytest tests/test_config.py -v` (Verifies V6-32, V6-35)
  - `python -m pytest tests/test_prediction_model.py -v` (Verifies V6-01, V6-04, V6-05)
  - `python -m pytest tests/test_hpo_and_2d_ensemble.py -v` (Verifies V6-06, V6-07)
  - `python -m pytest tests/test_adversarial_ensemble_scorer_challenger.py -v` (Verifies V6-02, V6-03)
  - `python -m pytest tests/test_meta_and_hybrid_ensemble.py -v` (Verifies V6-08)
- **Full Regression Suite**:
  - `.venv\Scripts\python.exe -m pytest tests/ -q` (Ensures 100% pass across all 1,279+ tests with 0 failures, 0 errors).
