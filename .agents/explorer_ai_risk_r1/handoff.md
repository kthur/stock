# Handoff Report — AI/ML & Portfolio Risk Deep Explorer

## 1. Observation
- **AIR-01**: `src/ai/factor_orthogonalizer.py:147-163` — `min_allowed_eig = max(max_eig / 1e6, self.ridge_epsilon)` clips zero eigenvalues to $10^{-6}$, yielding $1000\times$ noise amplification in degenerate directions when $N < K$.
- **AIR-02**: `src/ai/factor_orthogonalizer.py:242-276` — `BtWB = np.dot(B.T, B_weighted)` and `np.dot(B.T, y_weighted)` applies $W^{1/2}$ once rather than $W$, solving $(B^T W^{1/2} B)\beta = B^T W^{1/2} y$.
- **AIR-03**: `src/ai/factor_suppression.py:27-39, 137-147` — `CLUSTER_MAP` lacks short pipeline aliases (`rim`, `vcp`, `value_up`, `darkpool_hft`, `tone_drift`), causing strategies to be categorized as `'OTHER'` and bypassing high-risk regime factor suppression.
- **AIR-04**: `src/ai/ensemble_scorer.py:937-943` — `_vmin_floor = _vmax / max_total_ratio` is calculated at line 941 but unused at line 942, allowing dynamic Sharpe weight ratios to diverge up to 150:1.
- **AIR-05**: `src/ai/optuna_tuner.py:354-396` — 4 suggested hyperparameters (`vol_declining_threshold`, `min_vcp_score`, `decreasing_weight`, `volume_weight`) are completely disconnected from the trial evaluation loop in `tune_strategy_4_vcp_rule`.
- **AIR-06**: `src/ai/vcp_ml_predictor.py:608-619` — Platt scaling calibration treats model coefficients as log-odds multiplier (`coef * log_odds + intercept`) even though `prediction_model.py:2137` fitted `LogisticRegression` on linear probabilities $[0, 1]$, collapsing probabilities to near zero.
- **AIR-07**: `src/analysis/portfolio_optimizer.py:170-178, 204-220` — Prior return $\Pi$ is daily decimal ($\sim 0.001$) while view $Q$ is percentage return ($5.0 = 5\%$), causing $5000:1$ view distortion. In addition, negative excess return in Sharpe objective causes the solver to maximize portfolio volatility.
- **AIR-08**: `src/risk/portfolio_allocator.py:106-112` — Clayton Copula asymmetric correlation adds a rank-1 matrix of ones without positive semi-definiteness (PSD) projection, causing solver failures during market stress.
- **AIR-09**: `src/ai/prediction_model.py:156-170` — `DateAwareTimeSeriesSplit` indexes backwards from `n_dates`, discarding 60–80% of historical dates in early folds.
- **AIR-10**: `src/analysis/portfolio_optimizer.py:406-422` — HRP recursive bisection computes inverse variance without numerical floor, leading to overflow and `NaN` weight vector corruption on zero-volatility clusters.
- **AIR-11**: `src/risk/risk_manager.py:226-231, 311-315` — `np.isnan(None)` raises `TypeError` when evaluating VIX ROC on missing values, and intermittent indicator logging desynchronizes macro history queues.
- **AIR-12**: `src/analysis/coverage_analyzer.py:37-41, 165-170` — `_has_symbol_fundamental_data` misses normalized fundamental feature names, generating false `'NO_FUNDAMENTAL_DATA'` missingness reports.

## 2. Logic Chain
1. **Mathematical & Statistical Consistency**: In multivariate quantitative systems, orthogonalization and factor neutralizers must strictly adhere to the linear algebra definitions (ZCA-cor ridge conditioning and WLS normal equations $(B^T W B)\beta = B^T W y$). Deviations amplify noise or skew the factor neutralization.
2. **Model Training & Inference Parity**: Calibration coefficients saved during training must be evaluated on the exact same feature domain during inference. Passing logit $[-13.8, 13.8]$ to a linear $[0, 1]$ model causes catastrophic probability collapse.
3. **Hyperparameter Optimization Integrity**: In Optuna HPO, all suggested trial parameters must participate in the objective computation; otherwise, random noise is committed to production configs.
4. **Portfolio Optimization Robustness**: Numerical optimization (HRP, Black-Litterman, EVT-CVaR) requires guaranteed PSD matrices, bounded variance denominators, and dimensionally consistent views.

## 3. Caveats
- The audit focused on mathematical, architectural, and algorithmic integrity across 11 core AI/ML and risk files.
- GPU-specific CUDA kernel implementations for CatBoost/XGBoost were audited via their Python wrappers and fallback behavior.

## 4. Conclusion
- Discovered **12 brand-new, non-overlapping defects** (2 CRITICAL, 7 HIGH, 3 MEDIUM).
- Complete source code diffs, root cause analyses, and mathematical rationales have been compiled in `d:\Finance\code\stock\.agents\explorer_ai_risk_r1\ai_risk_findings.md`.
- All fixes are non-breaking, drop-in mathematical corrections that restore algorithmic integrity across AI/ML predictions, HPO tuning, and portfolio risk systems.

## 5. Verification Method
- Codebase inspection via `view_file`.
- Python test suite execution:
  ```bash
  .venv/bin/pytest tests/ -v
  ```
