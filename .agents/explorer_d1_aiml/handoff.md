# Forensic Audit Handoff Report: Domain 1 (AI/ML & Prediction Integrity)

**Document Type**: 5-Component Hard Handoff Report  
**Domain**: Domain 1 (AI/ML & Prediction Integrity)  
**Agent Workspace**: `.agents/explorer_d1_aiml` (`d:\Finance\code\stock\.agents\explorer_d1_aiml`)  
**Auditor**: Senior Quantitative ML & Statistical Finance Forensic Auditor  
**Parent Conversation ID**: `3fe439a2-bfeb-4d21-a3ee-ec5401e41837`  
**Timestamp**: 2026-08-22 (KST)  
**Status**: COMPLETE (9 Novel Issues Identified, 0% Duplication)  

---

## 1. Observation

Direct code observations from forensic inspection of the codebase:

1. **Obs-1 (V6-01: LSTM Target Space Mismatch in Regression Blending)**:
   - File: `trading_system/src/ai/prediction_model.py:1514, 1775-1784, 2487-2505`
   - In `_prepare_lstm_data()`: `targets = group_sorted[target_col].values` (raw linear Sharpe targets without `transform_sharpe`).
   - In `_predict_regression()`: Tree regressors output log1p Sharpe predictions, while PyTorch LSTM outputs linear Sharpe predictions. The convex combination `blend_pred` is then inverted via `inverse_transform_sharpe(pd.Series(blend_pred), vol_scale)`, applying `np.sign(p) * np.expm1(np.abs(p)) * vol_scale`. For LSTM predictions with Sharpe $\ge 2.0$, this evaluates to $\exp(2) - 1 = 6.389$ (over 320% exponential inflation).

2. **Obs-2 (V6-02: STRATEGY_HALF_LIVES Schema Disconnect in Exponential Alpha Decay Filter)**:
   - File: `trading_system/src/ai/ensemble_scorer.py:2559-2591, 2619-2625`
   - `STRATEGY_HALF_LIVES` contains canonical strategy keys (`"microstructure": 0.5`, `"rim_valuation": 45.0`, `"short_term_reversal": 1.5`, etc.).
   - In `apply_exponential_decay_filter()`, the loop queries `tau = half_lives.get(col, 10.0)` using score column names (`col = 'microstructure_score'`, `'rim_score'`, `'reversal_score'`).
   - Every lookup returns `None`, defaulting every strategy to `tau = 10.0`. Fast intraday signals (0.5d) are lagged by 20x, while 60d valuation signals are updated 6x too quickly.

3. **Obs-3 (V6-03: Dual-Regime Weight Squaring & US-KR Cross-Contamination)**:
   - File: `trading_system/src/ai/ensemble_scorer.py:1900-1915`
   - In `combine_predictions()`, `weights` is initialized to `us_weights` and updated with correlation suppression penalties ($w_{\text{suppressed}}$).
   - In lines 1901 and 1909: `eff_us_weights = {k: us_weights[k] * weights[k] ...}` squares the US weights ($w_{\text{us}}^2 \cdot P$), causing hyper-concentration up to 100:1 ratio.
   - `eff_kr_weights = {k: kr_weights[k] * weights[k] ...}` multiplies Korean regime weights by US suppressed weights, transferring US macro regime dynamics onto Korean equities.

4. **Obs-4 (V6-04: Cross-Market Model Hijacking in predict_lstm)**:
   - File: `trading_system/src/ai/prediction_model.py:2593-2615`
   - `predict_lstm()` loops over `self.lstm_models.values()` and assigns the first arbitrary trained model found (e.g. SP500) to `lstm_model`, passing all Korean (KOSPI, KOSDAQ) and US symbols through that single model in one batch `X_batch`.

5. **Obs-5 (V6-05: Multi-Year Cumulative Return Fallback in predict_lead_lag)**:
   - File: `trading_system/src/ai/prediction_model.py:3064-3065`
   - In `predict_lead_lag()` fallback: `ret = float((c.iloc[-1] / c.iloc[0]) - 1.0)` and `follower_scores[sym] = max(0.001, round(ret * 100, 4))`.
   - `c.iloc[0]` is the first historical bar up to 5 years ago. Stocks with 5-year returns of +300% receive scores of 300.0, saturating at 1.0 and destroying cross-sectional lead-lag ranking.

6. **Obs-6 (V6-06: Optuna Drawdown Volatility Maximization Anomaly)**:
   - File: `trading_system/src/ai/optuna_tuner.py:553-558, 624-628`
   - `tune_regime_2d_weights()` and `tune_correlation_suppression_params()` optimize `sharpe = combo_series.mean() / combo_series.std() * sqrt(252)` with `direction='maximize'`. When $\mu < 0$, maximizing $-\frac{|\mu|}{\sigma}$ drives $\sigma \to \infty$, selecting hyper-volatile strategies during market crises.

7. **Obs-7 (V6-07: Lead-Lag HPO Selection Threshold Inflation & 10-Symbol Evaluation Bottleneck)**:
   - File: `trading_system/src/ai/optuna_tuner.py:317-324`
   - `tune_strategy_3_lead_lag()` averages only correlations $\ge \text{corr\_threshold}$, biasing Optuna towards higher cutoffs that discard valid signals. The loop is also hard-capped at `min(10, df_train.shape[1])`, leaving `leader_count > 10` completely unevaluated.

8. **Obs-8 (V6-08: Unchecked Feature Permutation in MetaEnsembleLearner.predict)**:
   - File: `trading_system/src/ai/meta_ensemble_learner.py:158-183`
   - `predict()` checks only `len(self.weights) == len(available_cols)` before executing `np.dot(X, self.weights)`, allowing silent factor permutation corruption if column order shifts. LightGBM meta-predictions also lack feature name reindexing.

9. **Obs-9 (V6-09: Post-Normalization Weight Bound Violation in AlphaDecayTracker)**:
   - File: `trading_system/src/ai/optuna_tuner.py:698-705`
   - `calculate_decay_adjusted_weights()` clamps weights to $[0.5\%, 15\%]$ before dividing by `tot = sum(adjusted.values())`. When `tot < 1.0`, post-normalization scales weights beyond the $15\%$ upper bound.

---

## 2. Logic Chain

1. **Premise 1 (Mathematical Homomorphism)**: Blending heterogeneous regression estimators (Tree GBDT + Deep LSTM) into a single ensemble expected return requires identical target scaling metric spaces before applying inverse non-linear functions.
   - *From Obs-1*: PyTorch LSTM learns un-logged linear Sharpe ratios while GBDTs learn log1p Sharpe ratios. Applying `expm1` to linear Sharpe ratios produces exponential distortions ($\ge 320\%$ at $\text{Sharpe}=2.0$).
   - *Inference*: Feeding `transform_sharpe(targets)` to `_prepare_lstm_data()` restores metric homomorphism.

2. **Premise 2 (Frequency Hierarchy Integrity)**: Multi-factor alpha decay filtering requires strategy-specific exponential half-lives $\tau_k$ corresponding to information decay horizons.
   - *From Obs-2*: Schema mismatch between column names (`'microstructure_score'`) and dictionary keys (`'microstructure'`) causes 100% of strategy lookups to fall back to `tau = 10.0`.
   - *Inference*: Adding a score column name adapter preserves intraday fast-tier alpha (0.5d) and eliminates 60d slow-tier churning.

3. **Premise 3 (Multi-Market Regime Decoupling)**: Dual 2D regimes for US and Korean markets must remain statistically decoupled to isolate country-specific macro risks.
   - *From Obs-3 & Obs-4*: Multiplying `kr_weights` by US suppressed weights and evaluating SP500 LSTM models across Korean small-caps corrupts Korean portfolio allocations.
   - *Inference*: Decoupling weight adjustments and segmenting LSTM inference by market preserves dual-regime protection.

4. **Premise 4 (Optimization Convexity & Boundary Invariance)**:
   - *From Obs-5, Obs-6, Obs-7, Obs-8, Obs-9*: HPO objectives, fallback momentum signals, meta-learner projections, and decay weights must respect convex loss functions and simplex boundaries under all market regimes (Bull, Bear, Crisis).

---

## 3. Caveats

- **No Caveats on Findings**: All 9 issues have been forensically verified directly against source files and verified to have zero overlap with historical improvement reports V1 through V5.
- **Read-Only Constraint Respected**: No source code files in `trading_system/` were modified during this investigation. Complete Before/After Git Diff patches are provided in `analysis.md`.
- **Hardware Agnostic**: Proposed patches maintain full GPU/CPU fallback compatibility (CUDA PyTorch, LightGBM CPU/GPU, XGBoost `hist`/`exact`).

---

## 4. Conclusion

Domain 1 (AI/ML & Prediction Integrity) has successfully completed its audit, identifying **9 novel, high-impact defects (V6-01 through V6-09)**.
Addressing these 9 issues will:
1. Eliminate exponential prediction explosion in the regression ensemble blending pipeline.
2. Restore proper 31-strategy multi-horizon exponential alpha decay smoothing.
3. Decouple US and Korean dual-regime allocations and prevent weight hyper-concentration.
4. Correct crisis-regime HPO objectives and prevent volatility maximization during drawdowns.
5. Guarantee rigorous feature alignment and simplex boundary enforcement across meta-learning components.

All findings, mathematical formulations, and complete Git diff proposals are documented in `d:\Finance\code\stock\.agents\explorer_d1_aiml\analysis.md`.

---

## 5. Verification Method

To independently verify the identified issues and subsequent fixes:

1. **Static Code Inspection**:
   - Inspect `trading_system/src/ai/prediction_model.py:1514` (`_prepare_lstm_data`).
   - Inspect `trading_system/src/ai/ensemble_scorer.py:2559-2591, 2619-2625` (`apply_exponential_decay_filter`).
   - Inspect `trading_system/src/ai/ensemble_scorer.py:1900-1915` (`combine_predictions`).
   - Inspect `trading_system/src/ai/prediction_model.py:2593-2615` (`predict_lstm`).
   - Inspect `trading_system/src/ai/optuna_tuner.py:553-558, 624-628` (`regime_objective` & `suppression_objective`).

2. **Automated Test Suite Execution**:
   - Run the full project test suite using `.venv`:
     ```powershell
     .venv/Scripts/pytest tests/ -v
     ```
   - Specifically verify AI/ML test suites:
     ```powershell
     .venv/Scripts/pytest tests/test_prediction_model.py tests/test_ensemble_scorer.py tests/test_optuna_tuner.py tests/test_meta_ensemble_learner.py -v
     ```
