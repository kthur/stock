# Handoff Report: Milestone 1 Feature 1 & Feature 6
**Apex Quant Optimization (v9) - Pipeline Sequence Rectification & Statistically Calibrated Suppression**

**Author**: Explorer M1-1 (Pipeline Sequence & Factor Suppression Specialist)  
**Date**: 2026-09-04  
**Working Directory**: `d:\Finance\code\stock\.agents\explorer_m1_1_opt2`  
**Target Codebase**: `d:\Finance\code\stock`  
**Recipient**: Parent Orchestrator / Worker M1-1  

---

## 1. Observation

1. **Pipeline Sequence Inversion in `combine_predictions`**:
   - In `trading_system/src/ai/ensemble_scorer.py` (lines 2389–2445):
     ```python
     # Phase 3-B: Factor Orthogonalization (PCA ZCA / Gram-Schmidt)
     if getattr(self, 'orthogonalizer_enabled', True):
         ...
         merged = self.orthogonalizer.orthogonalize(...)

     # Phase 3-B.1: Strategy Correlation Orthogonalization Penalty
     if weights is not None and isinstance(weights, dict) and len(weights) > 1:
         weights = self.apply_correlation_orthogonalization_penalty(..., scores_df=merged)

     # Phase 3-C: Inter-Strategy Signal Correlation Monitoring & 2D Regime Noise Suppression
     if len(merged) >= 5:
         corr_df = self.correlation_monitor.update_correlation(merged)
         vif_dict = self.correlation_monitor.compute_vif(corr_df)
         suppressed_w = self.factor_suppression.suppress_weights(..., corr_matrix=corr_df)
     ```
     `self.orthogonalizer.orthogonalize` was executed in Phase 3-B before correlation monitoring in Phase 3-C.

2. **Empirical Correlation Collapse & Neutralized Penalties**:
   - When calculated on `_create_sample_17_strategy_df()` before orthogonalization:
     `SpearmanRankCorr(surge, vcp_ml) = 0.956536`
     `RegimeFactorSuppressionEngine.compute_penalties` returns:
     `surge: 0.757702, vcp_ml: 0.781163, regression: 0.851942`
   - When calculated after orthogonalization (Phase 3-C's input):
     `SpearmanRankCorr(surge, vcp_ml)` was collapsed to `0.728595` (and across all 31 strategies, off-diagonals average $< 0.25$).
     In `combine_predictions()`, post-ortho penalties evaluated to:
     `surge: 0.861232, vcp_ml: 0.890873, regression: 0.936334`
     Collinearity penalties were severely diluted, and for pairs below $\theta = 0.60 \sim 0.70$, penalties evaluated to $1.000000$ (no suppression).

3. **Static Correlation Cutoffs in `factor_suppression.py`**:
   - In `trading_system/src/ai/factor_suppression.py` (lines 108–145), `DEFAULT_REGIME_PARAMS` defined static $\theta_0$:
     `'SIDEWAYS_LOW_VOL': {'theta': 0.60, 'lambda': 1.20}`
     `'BULL_LOW_VOL': {'theta': 0.70, 'lambda': 0.80}`
   - `_get_regime_params()` had signature:
     `def _get_regime_params(self, regime_label: str, tuned_params: Optional[Dict[str, Any]] = None) -> Tuple[float, float]:`
     It lacked sample-size scaling, meaning a small sample of $N=50$ stocks used the same cutoff as $N=2000$ stocks despite a $6.5\times$ difference in sampling standard error ($1/\sqrt{47} \approx 0.146$ vs $1/\sqrt{1997} \approx 0.022$).

4. **Test Suite Baseline**:
   - Command: `.venv\Scripts\pytest tests/test_correlation_suppression.py tests/test_factor_orthogonalization.py -v`
   - Result: 18 passed in 14.34s (exited with code 0).
   - Command: `.venv\Scripts\pytest tests/test_adversarial_ensemble_scorer_challenger.py -v`
   - Result: 17 passed in 22.07s (exited with code 0).

---

## 2. Logic Chain

1. **Step 1 (Orthogonalization Decorrelates Matrix)**: Observation 1 shows that Phase 3-B replaces `merged` columns with orthogonalized values. Observation 2 shows that pairwise correlation is reduced (e.g. from 0.957 to 0.729 or $< 0.25$).
2. **Step 2 (Suppression Masking)**: In `factor_suppression.py`, excess correlation is $E_{ij} = \max(0, |\rho_{ij}| - \theta)$. When $\rho_{ij}$ is computed on orthogonalized data, it is lower than on raw data. If $|\rho_{ij}| \le \theta$, $E_{ij} = 0$, so suppression multiplier $P_i = 1.0$. Therefore, running orthogonalization before suppression blinds the suppression engine to raw signal collinearity.
3. **Step 3 (Pre-Orthogonalization Ordering)**: Placing correlation monitoring and factor suppression in Phase 3-B (before orthogonalization in Phase 3-C) ensures:
   - `corr_df` reflects raw cross-sectional factor correlation ($R^{\text{raw}}$).
   - $P_i(R)$ penalizes truly redundant strategies (e.g. surge penalty drops from 0.861 to 0.758 in sideways markets).
   - Suppressed weights $\tilde{w}$ are passed into `self.orthogonalizer.orthogonalize()`, ensuring weight-dependent decorrelation (e.g. Gram-Schmidt priority) uses penalized weights.
4. **Step 4 (Statistical Calibration Formula)**: Under Fisher's $z$-transformation, sample correlation standard error is $\sigma_r \approx 1/\sqrt{N-3}$. To guarantee $95\%$ one-sided confidence against sampling noise, the empirical threshold must be:
   $$\theta(R, N) = \text{clip}\left(\theta_0(R) + \frac{1.645}{\sqrt{\max(N - 3, 1)}}, 0.35, 0.85\right)$$
   For $N=50$, $\theta = 0.60 + 0.24 = 0.84$; for $N=500$, $\theta = 0.60 + 0.074 = 0.674$; for $N=2000$, $\theta = 0.60 + 0.037 = 0.637$. As $N \to \infty$, $\theta(R, N) \to \theta_0(R)$. For $N \le 3$ or $N$ is None, it defaults to $\theta_0(R)$ without error.

---

## 3. Caveats

1. **Other Milestones**: Milestone 1 Feature 2 (Dual-Consensus Spectral Whitening in `factor_orthogonalizer.py`) and Features 3–5 (Bessembinder power law, Bilinear synergy, 2D regime half-life) are scoped to peer explorers (M1-2, M1-3). The proposed pipeline sequence cleanly interfaces with them via Phase 3-C.
2. **Attrs Persistence**: Pandas `.copy()` generally retains `.attrs`, but to eliminate any edge-case drops during DataFrame transformations, `merged.attrs['correlation_report']` is explicitly assigned after orthogonalization.
3. **Optuna Tuner Parameter Passing**: `OptunaStrategyTuner.tune_correlation_suppression_params` explicitly passes `theta=th`. When `theta` is explicitly passed by callers/tests, explicit `theta` takes precedence over $\theta(R, N)$, preserving 100% backward compatibility for all existing HPO and unit tests.

---

## 4. Conclusion

1. **Feature 1**: In `trading_system/src/ai/ensemble_scorer.py`, move Correlation Monitoring & Factor Suppression to Phase 3-B (before Factor Orthogonalization in Phase 3-C).
2. **Feature 6**: In `trading_system/src/ai/factor_suppression.py`, implement `calibrate_cutoff(theta_0, n_samples)` and update `_get_regime_params`, `compute_penalties`, `suppress_weights`, and `get_suppression_report` to accept `n_samples`.
3. **Artifact Created**: Complete implementation blueprint, line-by-line diffs, and verification unit tests are documented in:
   `d:\Finance\code\stock\.agents\explorer_m1_1_opt2\plan_m1_1.md`.

---

## 5. Verification Method

### Test Commands
```bash
# Verify correlation suppression and factor orthogonalization unit tests
.venv\Scripts\pytest tests/test_correlation_suppression.py tests/test_factor_orthogonalization.py -v

# Verify adversarial and boundary stress tests
.venv\Scripts\pytest tests/test_adversarial_ensemble_scorer_challenger.py -v

# Verify full regression suite for ensemble scoring
.venv\Scripts\pytest tests/test_r1_ensemble_regime_fixes.py tests/test_score_normalizer.py tests/test_m1_1_fixes.py -v
```

### Invalidation Conditions
- If `rep['penalties']['surge'] >= 1.0` under high raw momentum correlation in `SIDEWAYS_LOW_VOL`.
- If `calibrate_cutoff(0.60, 50) <= calibrate_cutoff(0.60, 2000)` (violates sample-size monotonicity).
- If any of the existing 18 tests in `test_correlation_suppression.py` fail.
