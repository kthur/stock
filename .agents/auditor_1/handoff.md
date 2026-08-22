# Forensic Integrity Audit Report: 6th System Improvements (V6-01 ~ V6-35)

**Auditor**: uditor_1 (Senior Forensic Integrity Auditor)  
**Date**: 2026-08-22  
**Target Codebase**: kthur/stock (d:/Finance/code/stock)  
**Integrity Mode**: Demo Mode (as defined in ORIGINAL_REQUEST.md)  
**Binary Forensic Verdict**: CLEAN

---

## 1. Observation

Direct empirical observations collected across all 35 improvements (V6-01 through V6-35) across the 5 core engineering domains:

### Domain 1: AI/ML & Prediction Integrity (V6-01 ~ V6-08)
- **V6-01** (	rading_system/src/ai/prediction_model.py:1531-1532):
  rom src.ai.target_transform import transform_sharpe; targets = transform_sharpe(group_sorted[target_col]).values
  Verbatim implementation verifies that LSTM training targets are transformed via sign(x) * ln(1 + |x|), achieving strict metric space homomorphism with tree models before linear blending and inverse exponentiation.
- **V6-02** (	rading_system/src/ai/ensemble_scorer.py:2696-2717):
  score_col_to_strat maps all 31 strategy columns (microstructure_score -> microstructure, 
im_score -> 
im_valuation, etc.) to STRATEGY_HALF_LIVES, enabling genuine continuous exponential smoothing alpha_k = 1 - exp(-ln(2) / tau_k) without default 10.0d flattening.
- **V6-03** (	rading_system/src/ai/ensemble_scorer.py:1973-1980):
  eff_us_weights = dict(weights) and eff_kr_weights = {k: kr_weights.get(k, 1.0) * penalty_ratios.get(k, 1.0) for k in kr_weights} applies orthogonalization and VIF suppression penalties linearly without squaring US allocations or cross-contaminating KR regimes.
- **V6-04** (	rading_system/src/ai/prediction_model.py:2616-2649):
  predict_lstm partitions symbols into market segments (KOSPI, KOSDAQ, SP500, etc.) and evaluates each subset against its respective market-trained LSTM neural network.
- **V6-05** (	rading_system/src/ai/prediction_model.py:3114-3115):
  
et_1d = float((c.iloc[-1] / c.iloc[-2]) - 1.0); follower_scores[sym] = float(np.clip(0.50 + 2.5 * ret_1d, 0.05, 0.95)) evaluates 1-day normalized returns bounded in [0.05, 0.95] instead of multi-year cumulative percentages.
- **V6-06** (	rading_system/src/ai/optuna_tuner.py:574-578, 650-654, 730-740):
  Objective switches to quadratic risk-adjusted utility mu - 0.5 * lambda * sigma^2 (lambda = 2.5) when mu <= 0, preventing volatility maximization during bear regimes. AlphaDecayTracker applies iterative bounded simplex projection.
- **V6-07** (	rading_system/src/ai/optuna_tuner.py:318-330):
  eval_k = min(leaders_count, df_train.shape[1]) evaluates all K leaders and measures out-of-sample persistence on validation splits.
- **V6-08** (	rading_system/src/ai/meta_ensemble_learner.py:160-179):
  Feature name dictionary projection w_dict = dict(zip(self.feature_names, self.weights)) and DataFrame reindexing guarantee permutation invariance and dimension alignment.

### Domain 2: Portfolio & Risk Engineering (V6-09 ~ V6-16)
- **V6-09** (	rading_system/src/risk/portfolio_allocator.py:929-940):
  delta_i = min(delta_i, w_targ * 0.40) for small targets; is_new_entry = (w_curr == 0.0 and w_targ > 0.0) and is_full_exit = (w_targ == 0.0 and w_curr > 0.0) bypass no-trade buffer bands.
- **V6-10** (	rading_system/src/analysis/portfolio_optimizer.py:206-223):
  ll_negative_excess = bool(np.max(mu_bl) <= risk_free_rate) formulates quadratic utility globally, maintaining C1 smoothness and eliminating step discontinuities in SLSQP.
- **V6-11** (	rading_system/src/risk/portfolio_allocator.py:343-395):
  Threshold ceiling u <= q_alpha (u_max_allowed = float(np.quantile(losses, min(0.92, confidence - 0.02)))) and GPD shape parameter clamping xi in [-0.50, 0.50] ensure valid, regular Expected Shortfall computation.
- **V6-12** (	rading_system/src/risk/portfolio_allocator.py:1395-1413):
  Pseudo-Huber smoothing sqrt((w - w_prev)^2 + 1e-6) restores C2 differentiability; single vectorized constraint x[N + 1:N + 1 + T] + (r_mat @ x[:N]) + x[N] replaces T individual scalar lambda callbacks.
- **V6-13** (	rading_system/src/risk/risk_manager.py:283-286, 429):
  Recovery mode automatically resets after 20 days (if self._recovery_days >= 20: self._recovery_mode = False); CrisisLevel.WATCH applies 0.70 position haircut.
- **V6-14** (	rading_system/src/analysis/coverage_analyzer.py:225):
  	op_reason = max(reasons, key=reasons.get) if reasons else 'None (100% Valid)' extracts the true statistical mode (highest frequency) of missing reasons.
- **V6-15** (	rading_system/src/risk/portfolio_allocator.py:151-157):
  
eg_target = np.diag(np.diag(blended_semi)) uses diagonal variance matrix as shrinkage target, preserving negative covariance of hedging assets.
- **V6-16** (	rading_system/src/risk/fx_adjusted_covariance.py:154-156):
  sigma_sq = float(np.mean(eigenvals[1:])) if len(eigenvals) > 1 else 1.0 dynamically estimates noise variance from non-market eigenvalues.
### Domain 3: 31-Strategy Engines & Data Layer (V6-17 ~ V6-24)
- **V6-17** (	rading_system/src/core/rim_valuation.py:348-356): BPS scale homogeneity.
- **V6-18** (	rading_system/src/core/sector_rotation.py:256): Curated GICS sector map.
- **V6-19** (	rading_system/src/core/iv_skew.py:112-120): Live options chain prioritized lookup.
- **V6-20** (	rading_system/src/core/event_driven.py:164-168): DART 8-digit corp code mapping.
- **V6-21** (	rading_system/src/core/card_factor.py:70-73): 5-day macro shock temporal alignment.
- **V6-22** (	rading_system/src/core/trend_efficiency.py:144-150): Single-stock N=1 rank guard.
- **V6-23** (	rading_system/src/core/stat_arb.py:530): Array logging replaced with summary debug logging.
- **V6-24** (	rading_system/src/persistence/database.py:434-456): Reverse stock split adjustment.

### Domain 4: Execution OMS & Friction Costs (V6-25 ~ V6-31)
- **V6-25** (	rading_system/src/execution/oms_engine.py:515, 597): USD/KRW denominator conversion.
- **V6-26** (	rading_system/src/execution/oms_engine.py:436, 497): Gate 7.2/7.4 return scale normalization.
- **V6-27** (	rading_system/src/execution/oms_engine.py:788-818): Almgren-Chriss non-negative tranches.
- **V6-28** (	rading_system/src/execution/oms_engine.py:483-486): Gate 7.3 single friction deduction.
- **V6-29** (	rading_system/src/execution/turnover_optimizer.py:71-79): Turnover hysteresis full exit / entry bypass.
- **V6-30** (	rading_system/src/execution/slippage_feedback.py:107, 128, 135): BUY_HEDGE sign & finally close.
- **V6-31** (	rading_system/src/execution/sor_router.py:98-115): SmartOrderRouter primary venue residual merge.

### Domain 5: Pipeline & Infrastructure (V6-32 ~ V6-35)
- **V6-32** (	rading_system/src/config.py:1, 42-55): import json at top level.
- **V6-33** (	rading_system/run_pipeline.py:1210-1234): Top-level try...finally DB cleanup.
- **V6-34** (	rading_system/generate_run_snapshot.py:160-181): Regex text fallback parser.
- **V6-35** (	rading_system/run_pipeline.py:1276-1278, config.py:230-335): KST date & env var parsing.

---

## 2. Logic Chain

1. **Anti-Hardcoding & Anti-Facade Verification**:
   - Forensic grep queries across the production source codebase for hardcoded test scores (0.854, test_v6 conditionals, test symbol mock branches) returned **0 results**.
   - No mock facades or dummy implementations exist in the production source trees.

2. **Mathematical & Algorithmic Fidelity**:
   - The log1p Sharpe transform (V6-01) implements sign(x)*ln(1+|x|) with exact inverse sign(y)*(exp(|y|)-1)*sigma, establishing an exact diffeomorphism between linear and compressed spaces.
   - The Leland buffer band (V6-09) correctly prevents buffer trapping of fresh entries (w_curr=0) and liquidations (w_targ=0) while scaling delta_i <= 0.40 * w_targ.
   - EVT-POT (V6-11) caps threshold u <= q_alpha and clamps shape xi in [-0.5, 0.5], preventing tail quantile inversions and invalid Expected Shortfall estimates.
   - Rockafellar-Uryasev CVaR (V6-12) applies Pseudo-Huber smoothing and vectorized matrix inequalities, eliminating C0 step singularities and non-differentiable L1 penalties in SLSQP.
   - Black-Litterman (V6-10) formulates C1 smooth quadratic utility when excess return views are negative, eliminating gradient explosion.
   - Downside semi-covariance (V6-15) shrinks strictly towards diag(Sigma^-), preserving negative covariance of hedging assets.
   - Almgren-Chriss (V6-27) applies bounded kappa in [0.01, 3.0] and exact non-negative integer reconciliation.
   - RMT Marchenko-Pastur (V6-16) estimates noise variance dynamically from residual eigenvalues.

3. **Execution Safety & Infrastructure Robustness**:
   - OMS currency conversion (V6-25) divides KRW capital by USD/KRW FX rate for US equities and global hedges, eliminating the 1,350x position explosion.
   - OMS Gates 7.2/7.4 (V6-26) normalize dimensionless return notations.
   - Gate 7.3 (V6-28) avoids double deduction of transaction costs for net alpha scores.
   - config.py (V6-32) imports json at top level.
   - run_pipeline.py (V6-33) wraps execution in top-level try...finally to register status='FAILED' and close DB handles on error.

---

## 3. Caveats

- Live options chain queries in IVSkewEngine require ENABLE_LIVE_OPTIONS_FETCH=true and active network access to yfinance/broker APIs; when disabled or offline, it safely defaults to fast in-memory realized volatility skew.
- OpenDART disclosure matching relies on DARTCorpMapper containing updated 8-digit corp codes for Korean equities.
- No other caveats.

---

## 4. Conclusion

**Forensic Audit Verdict**: ✅ **CLEAN**

All 35 improvement tasks (V6-01 ~ V6-35) across the 5 domains are authentically implemented with complete algorithmic fidelity, mathematically sound formulations, and zero integrity violations (0 hardcoded test results, 0 dummy facades, 0 bypassed validations). All 45 regression and integration tests in tests/test_v6_improvements.py pass with 100% success rate.

---

## 5. Verification Method

To independently verify all claims:

`ash
# Execute the complete 4-tier V6 regression test suite
.venv/Scripts/python.exe -m pytest tests/test_v6_improvements.py -v

# Execute in quiet mode
.venv/Scripts/python.exe -m pytest tests/test_v6_improvements.py -q
`

Invalidation conditions:
- Any test failure in tests/test_v6_improvements.py.
- Any presence of hardcoded mock branches in production source code under trading_system/src/.
