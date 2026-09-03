# Milestone 1 Review and Verification Report (Features 1, 2, 6)

**Reviewer**: Reviewer M1-1 (Roles: reviewer, critic)  
**Date**: 2026-09-04T01:03:00+09:00 (UTC 2026-09-03T16:03:00Z)  
**Verdict**: **APPROVE**  
**Integrity Audit**: **CLEAN (0 violations)**

---

## 1. Observation

### 1.1 Direct Source Code Inspection
- **Feature 1 (Pipeline Sequence Rectification)**:
  In `trading_system/src/ai/ensemble_scorer.py` (lines 2396–2475):
  ```python
  # Phase 3-B (Pre-Orthogonalization): Inter-Strategy Signal Correlation Monitoring & 2D Regime Noise Suppression
  # Feature 1: Move raw correlation monitoring and factor suppression BEFORE ZCA orthogonalization
  if len(merged) >= 5:
      corr_df = self.correlation_monitor.update_correlation(merged)
      vif_dict = self.correlation_monitor.compute_vif(corr_df)
      n_cross_section = len(merged)
      ...
      suppressed_w = self.factor_suppression.suppress_weights(
          base_weights=base_w,
          corr_matrix=corr_df,
          regime_label=str(regime),
          tuned_params=tuned_p,
          n_samples=n_cross_section
      )
      weights = suppressed_w
      ...
  # Phase 3-C: Factor Orthogonalization (PCA ZCA / Gram-Schmidt)
  if getattr(self, 'orthogonalizer_enabled', True):
      merged = self.orthogonalizer.orthogonalize(
          score_df=merged,
          strategy_cols=strategy_score_cols,
          weights=strat_weights,
          method='pca_symmetric',
          preserve_top_k=2
      )
  ```
  The sequence has been rectified so correlation monitoring and factor suppression run on raw cross-sectional factor scores BEFORE PCA-ZCA whitening. The suppressed weights are fed into orthogonalization, and the diagnostic dictionary is preserved in `merged.attrs['correlation_report']`.

- **Feature 6 (Statistically Calibrated Suppression Cutoffs $\theta(R, N)$)**:
  In `trading_system/src/ai/factor_suppression.py` (lines 124–142):
  ```python
  @staticmethod
  def calibrate_cutoff(
      theta_0: float,
      n_samples: Optional[int],
      z_score: float = 1.645,
      min_theta: float = 0.35,
      max_theta: float = 0.85
  ) -> float:
      if n_samples is None or n_samples <= 3:
          return float(theta_0)
      calibrated = float(theta_0) + float(z_score) / np.sqrt(float(max(n_samples - 3, 1)))
      return float(np.clip(calibrated, min_theta, max_theta))
  ```
  `_get_regime_params`, `compute_penalties`, `suppress_weights`, and `get_suppression_report` accept `n_samples: Optional[int] = None` and apply dynamic Fisher $z$-distribution standard error calibration $\text{SE}(r) \approx 1/\sqrt{N-3}$.

- **Feature 2 (Dual-Consensus Spectral Whitening & Noise-Scaled Marchenko-Pastur Floor)**:
  In `trading_system/src/ai/factor_orthogonalizer.py` (lines 42–53, 120–136, 256–292):
  ```python
  # Determine effective top components to preserve (Feature 2 / R1)
  eff_top_k = preserve_top_k
  if eff_top_k <= 0 and preserve_pc1:
      eff_top_k = 1

  # Estimate noise subspace variance sigma2 for Marchenko-Pastur lower spectral edge
  if eff_top_k > 0 and K > eff_top_k:
      noise_evals = eigenvalues[:-eff_top_k]
  elif K > 1:
      noise_evals = eigenvalues[:-1]
  else:
      noise_evals = eigenvalues

  sigma2 = float(np.mean(noise_evals)) if len(noise_evals) > 0 else 1.0
  sigma2 = max(sigma2, 1e-4)

  # Marchenko-Pastur spectral floor for weak noise eigenvalues
  q = min(K, N) / max(max(K, N), 1)
  mp_lower = sigma2 * ((1.0 - np.sqrt(q)) ** 2) if N >= K else 0.0
  lambda_floor = float(np.clip(max(mp_lower, 0.01 * sigma2), 1e-4, 1.0))

  lambdas_clean = np.maximum(eigenvalues, lambda_floor)
  ridge_eps = float(np.clip(self.ridge_epsilon, 1e-6, 1e-3))
  whitening_filter = 1.0 / np.sqrt(lambdas_clean + ridge_eps)

  # Preserve top_k leading eigenvalues (PC1 Trend, PC2 Value/Quality) uncompressed (filter = 1.0)
  if eff_top_k > 0 and K > 1:
      num_to_preserve = min(eff_top_k, max(K - 1, 0))
      for i in range(1, num_to_preserve + 1):
          whitening_filter[-i] = 1.0

  whitening_filter = np.minimum(whitening_filter, 10.0)
  ```
  Dual-Consensus Spectral Whitening preserves both PC1 (Trend) and PC2 (Value/Quality) without whitening compression, floors noise bulk eigenvalues at the Marchenko-Pastur lower edge, and caps amplification at 10.0.

### 1.2 Automated Pytest Verification
- **Required Dispatch Suite**:
  ```powershell
  .venv\Scripts\pytest tests/test_correlation_suppression.py tests/test_factor_orthogonalization.py tests/test_factor_ortho_empirical_stress.py tests/test_m1_quant_enhancements.py -v
  ```
  Result: **36 passed in 17.67s** (100% pass rate, 0 failures, 0 warnings).

- **Extended Full Regression Suite**:
  ```powershell
  .venv\Scripts\pytest tests/test_correlation_suppression.py tests/test_factor_orthogonalization.py tests/test_factor_ortho_empirical_stress.py tests/test_m1_quant_enhancements.py tests/test_score_normalizer.py tests/test_return_maximization_apex.py tests/test_world_class_quant_enhancements.py tests/test_adversarial_ensemble_scorer_challenger.py tests/test_r1_ensemble_regime_fixes.py -q
  ```
  Result: **95 passed in 24.85s** (100% pass rate across 9 comprehensive suites).

### 1.3 Adversarial Stress Testing Results
- **Boundary $N$ on $\theta(R, N)$**: Tested $N \in \{\text{None}, -10, 0, 1, 2, 3, 4, 5, 50, 1000, 10^6\}$. All evaluations returned finite values strictly bounded in $[0.35, 0.85]$. No divide-by-zero or imaginary square roots occurred.
- **Rank Deficient & Extreme Collinearity ($N < K$, all 1s matrix)**: Handled stably by Marchenko-Pastur lower floor $\lambda_{\text{floor}} \ge 0.01 \sigma^2$ and maximum whitening filter cap (10.0), outputting finite scores in $[0.0, 1.0]$.
- **Over-range `preserve_top_k` ($k=100 > K=5$)**: Guarded by `min(eff_top_k, max(K - 1, 0))`, ensuring at least one noise dimension is whitened rather than returning an unwhitened identity.
- **Feature 1 Pipeline End-to-End Test**: Generated synthetic cross-section with raw collinearity $\rho(\text{surge}, \text{vcp\_ml}) = 0.9977$. Verified that raw correlation was detected prior to orthogonalization, collinear momentum penalties dropped to $0.950832$, non-collinear factors remained $1.0$, and final ensemble scores remained finite, monotonic, and bounded in $[0.0, 1.0]$.

---

## 2. Logic Chain

1. **Pipeline Ordering Proof (Feature 1)**:
   - Observation 1.1 shows Phase 3-B executes at lines 2396–2453, updating correlation and computing factor suppression penalties $P_i(R)$ on raw cross-sectional factor columns.
   - Phase 3-C executes subsequently at lines 2454–2475, passing the suppressed weights `weights=strat_weights` to `FactorOrthogonalizerEngine.orthogonalize()`.
   - In our adversarial test (Observation 1.3), raw correlation was detected at $\rho = 0.9977$ and penalties were triggered ($P_{\text{surge}} = 0.950832$). If orthogonalization had run first, PCA-ZCA would have decorrelated the signals to $|\rho| < 0.25$, causing excess correlation $\max(0, |\rho| - 0.60) = 0$ and completely bypassing collinearity penalties.
   - Therefore, the pipeline sequence rectification is mathematically and functionally effective.

2. **Dual-Consensus Spectral Whitening & Floor (Feature 2)**:
   - In NumPy `np.linalg.eigh(C)`, eigenvalues are sorted in ascending order ($\lambda_0 \le \lambda_1 \le \dots \le \lambda_{K-1}$).
   - In `_pca_zca_symmetric`, setting `whitening_filter[-i] = 1.0` for $i \in \{1, 2\}$ sets the multiplier for PC1 ($\lambda_{K-1}$) and PC2 ($\lambda_{K-2}$) to $1.0$.
   - Because coordinates along PC1 and PC2 are multiplied by $1.0$ rather than $1/\sqrt{\lambda}$, their variance $\text{Var}(X v_k) = \lambda_k$ is preserved uncompressed, protecting market trend (PC1) and value/quality (PC2) from signal erosion.
   - Noise eigenvalues are floored at $\lambda_- = \sigma^2(1 - \sqrt{q})^2$ with $q = \min(K,N)/\max(K,N)$, and the filter is capped at 10.0, preventing near-zero eigenvalues from inverting into numerical explosions.

3. **Sample-Size Calibrated Cutoff (Feature 6)**:
   - The estimator standard error of Pearson correlation $r$ under Fisher's $z$-transformation is $\text{Var}(z) = 1/(N-3)$, so $\text{SE}(r) \approx 1/\sqrt{N-3}$.
   - For a 95% one-sided confidence interval, $z_{0.95} = 1.645$.
   - The formula $\theta(R, N) = \text{clip}\left(\theta_0(R) + \frac{1.645}{\sqrt{\max(N-3, 1)}}, 0.35, 0.85\right)$ widens the threshold in small sample sizes (e.g. $\theta(R, 50) \approx 0.840$), preventing false positive dampening from small-sample noise, while converging to $\theta_0(R)$ for large market universes ($N \ge 1000$).
   - Fallback logic for $N \le 3$ cleanly returns $\theta_0(R)$ without raising exceptions.

4. **Integrity & Code Quality Verification**:
   - Grep searches for `test_`, `SYM_`, or hardcoded mock constants yielded zero matches in all production code files.
   - All tests in `tests/test_m1_quant_enhancements.py` construct realistic synthetic DataFrames and test mathematical invariants (monotonicity, eigenvalues, rank preservation, condition numbers).
   - No facades, cheats, or shortcuts were found.

---

## 3. Caveats

- In universes with $K=2$ strategies, `preserve_top_k=2` is clamped to $K-1=1$ by `min(eff_top_k, max(K - 1, 0))` so that whitening can perform decorrelation on the remaining component; this is the intended and mathematically necessary behavior.
- No other caveats.

---

## 4. Conclusion

Milestone 1 implementation strictly satisfies all requirements and acceptance criteria for Features 1, 2, and 6:
- Feature 1: Pre-orthogonalization raw correlation monitoring and factor suppression is correctly positioned before PCA-ZCA whitening and receives/preserves correlation reports.
- Feature 2: Dual-Consensus Spectral Whitening (`preserve_top_k=2`) and noise-scaled Marchenko-Pastur flooring operate robustly and prevent both consensus compression and noise explosion.
- Feature 6: Statistically calibrated cutoff $\theta(R, N)$ dynamically adapts to cross-sectional universe size with Fisher $z$-distribution rigor.
- Regression & Adversarial: All 95 regression tests and all independent adversarial edge-case tests pass 100%.

**Final Verdict**: **APPROVE**

---

## 5. Verification Method

To independently reproduce and verify this review:

1. **Run Dispatched Test Suite**:
   ```powershell
   .venv\Scripts\pytest tests/test_correlation_suppression.py tests/test_factor_orthogonalization.py tests/test_factor_ortho_empirical_stress.py tests/test_m1_quant_enhancements.py -v
   ```
   *Expected result: 36 passed in ~18s.*

2. **Run Extended 9-Suite Regression Test**:
   ```powershell
   .venv\Scripts\pytest tests/test_correlation_suppression.py tests/test_factor_orthogonalization.py tests/test_factor_ortho_empirical_stress.py tests/test_m1_quant_enhancements.py tests/test_score_normalizer.py tests/test_return_maximization_apex.py tests/test_world_class_quant_enhancements.py tests/test_adversarial_ensemble_scorer_challenger.py tests/test_r1_ensemble_regime_fixes.py -q
   ```
   *Expected result: 95 passed in ~25s.*

3. **Inspect Core Files**:
   - `trading_system/src/ai/factor_suppression.py`: Lines 124–142 (`calibrate_cutoff`)
   - `trading_system/src/ai/factor_orthogonalizer.py`: Lines 255–292 (`_pca_zca_symmetric`, `preserve_top_k`, MP floor)
   - `trading_system/src/ai/ensemble_scorer.py`: Lines 2396–2475 (Phase 3-B before Phase 3-C)

4. **Invalidation Conditions**:
   - Any test failure in `tests/test_m1_quant_enhancements.py`.
   - Any non-finite (NaN / Inf) output in `FactorOrthogonalizerEngine.orthogonalize()`.
   - Collinearity penalties failing to apply when raw inter-strategy correlation exceeds the calibrated threshold $\theta(R, N)$.
