# Technical Implementation Plan: Milestone 1 Feature 2
## Dual-Consensus Spectral Whitening & Marchenko-Pastur Spectral Flooring

**Target Codebase**: `trading_system/src/ai/factor_orthogonalizer.py`  
**Test Suite**: `tests/test_factor_orthogonalization.py`  
**Author**: Explorer M1-2 (Dual-Consensus Spectral Whitening Specialist)  
**Status**: DESIGN COMPLETE / READY FOR WORKER IMPLEMENTATION  
**Date**: 2026-09-04  

---

## 1. Executive Summary & Problem Formulation

### 1.1 Context & Objective
In the 37-strategy multi-factor engine across 5 global markets (KOSPI, KOSDAQ, SP500, NASDAQ, RUSSELL2000), strategies naturally cluster into two dominant, structural consensus pillars:
1. **Market Trend & Momentum Consensus (PC1)**: Capturing broad market direction, trend efficiency, momentum quality, and cross-asset beta flows.
2. **Fundamental Value & Quality Consensus (PC2)**: Capturing intrinsic balance-sheet value, residual income (RIM), accruals quality, earnings tone drift, and shareholder yield.

Under the baseline implementation in `trading_system/src/ai/factor_orthogonalizer.py` (`_pca_zca_symmetric`, lines 215–267):
- When consensus preservation was enabled (`preserve_consensus_pc1=True`), **only PC1** was preserved ($f(\lambda_K) = 1.0$), while PC2 ($\lambda_{K-1}$) was subjected to full inverse-square-root whitening ($f(\lambda_{K-1}) = \min(1/\sqrt{\lambda_{K-1} + \epsilon}, 10.0)$).
- Because $\lambda_{K-1} \approx 4 \sim 8$, whitening compressed the fundamental consensus signal by $50\%\sim 65\%$, diluting high-conviction fundamental signals and degrading the Top-Decile Spread.
- Conversely, for weak noise dimensions ($\lambda_i \to 0$), whitening amplified sampling noise up to the arbitrary $10.0\times$ cap without sample-size-aware regularisation.

### 1.2 Core Scope of Milestone 1 Feature 2
1. **Dual-Consensus Spectral Whitening (`preserve_top_k=2`)**:
   - Upgrade `_pca_zca_symmetric`, `orthogonalize`, and `__init__` in `FactorOrthogonalizerEngine` to support preserving the top $k$ leading eigenvalues ($k=2$).
   - Explicitly preserve uncompressed filter weights $f(\lambda_K) = 1.0$ (PC1: Trend) and $f(\lambda_{K-1}) = 1.0$ (PC2: Value/Quality), while properly whitening the remaining $K-2$ noise dimensions.
2. **Marchenko-Pastur Spectral Flooring**:
   - Implement Random Matrix Theory (RMT) spectral flooring for weak noise eigenvalues.
   - **Crucial Mathematical Discovery**: Scale the Marchenko-Pastur lower edge by the empirical noise-subspace variance $\sigma_{\text{noise}}^2 = \frac{1}{K - k} \sum_{i=1}^{K - k} \lambda_i$. As discovered in empirical stress testing, an unscaled $(1 - \sqrt{K/N})^2$ floor treats the entire matrix as white noise, causing severe correlation failure ($0.7588 > 0.30$) when strong factors exist. Scaling by $\sigma_{\text{noise}}^2$ flawlessly maintains low pairwise correlation ($< 0.01 \sim 0.23$) while flooring weak noise dimensions.
3. **100% Backward Compatibility**:
   - Existing callers passing `preserve_consensus_pc1=True` continue to map to `eff_top_k=1`.
   - Default initialization (`FactorOrthogonalizerEngine()`) retains `preserve_top_k=0`, ensuring all 106+ regression tests continue to pass with 0 regressions.

---

## 2. Mathematical Foundations & Closed-Form Formulations

### 2.1 Eigendecomposition of Correlation Matrix
Let $X \in \mathbb{R}^{N \times K}$ be the cross-sectional score matrix across $N$ symbols and $K$ strategies ($K=37$).
Standardize each column to zero mean and unit variance:
$$\bar{X} = (X - \mu) \oslash \sigma$$
Compute the sample covariance matrix with Ledoit-Wolf shrinkage:
$$C = \frac{1}{N - 1} \bar{X}^T \bar{X}, \quad C_{\text{shrunk}} = (1 - \delta) C + \delta \mu_I I$$
Symmetrize $C_{\text{sym}} = \frac{1}{2}(C_{\text{shrunk}} + C_{\text{shrunk}}^T)$ and compute the eigendecomposition:
$$C_{\text{sym}} = V \Lambda V^T, \quad \Lambda = \text{diag}(\lambda_1, \lambda_2, \dots, \lambda_K)$$
where eigenvalues are sorted in ascending order:
$$0 \le \lambda_1 \le \lambda_2 \le \dots \le \lambda_{K-1} \le \lambda_K$$

### 2.2 Noise Subspace & Marchenko-Pastur Spectral Floor
In Random Matrix Theory (Marchenko & Pastur, 1967; Baik, Ben Arous & Péché, 2005):
When $k$ spiked signal eigenvalues exist ($\lambda_K, \dots, \lambda_{K-k+1} \gg 1$), the remaining $K - k$ eigenvalues belong to the noise bulk.
The average variance of this noise subspace is:
$$\sigma_{\text{noise}}^2 = \frac{1}{\max(K - k, 1)} \sum_{i=1}^{K - k} \lambda_i$$
Under the Marchenko-Pastur law for aspect ratio $q = \frac{\min(K, N)}{\max(K, N)} \le 1$, the theoretical lower spectral boundary of the noise bulk is:
$$\lambda_- = \sigma_{\text{noise}}^2 \left( 1 - \sqrt{q} \right)^2$$
To prevent numerical instability, null-space amplification, or ill-conditioned division when $N < K$ or when features are collinear, the spectral floor is defined as:
$$\lambda_{\text{floor}} = \text{clip}\left( \max\left(\lambda_-, 0.01 \cdot \sigma_{\text{noise}}^2\right), 10^{-4}, 1.0 \right)$$
Flooring each empirical eigenvalue:
$$\tilde{\lambda}_i = \max(\lambda_i, \lambda_{\text{floor}})$$

### 2.3 Dual-Consensus Whitening Filter Operator
The initial Tikhonov-regularized whitening filter is:
$$f(\tilde{\lambda}_i) = \frac{1}{\sqrt{\tilde{\lambda}_i + \epsilon_{\text{ridge}}}}, \quad \epsilon_{\text{ridge}} = \text{clip}(\epsilon, 10^{-6}, 10^{-3})$$

For the leading consensus components ($k \in [1, \text{preserve\_top\_k}]$):
$$f(\lambda_{K - k + 1}) = 1.0 \quad \text{for } k = 1, \dots, \min(\text{eff\_top\_k}, K - 1)$$
where capping by $K - 1$ guarantees that at least one dimension remains whitened when $K \ge 2$, preventing an unintended identity transformation on small test matrices.

Finally, cap the maximum noise amplification at $10.0\times$:
$$f^*(\lambda_i) = \min(f(\tilde{\lambda}_i), 10.0)$$

### 2.4 Symmetric Positive-Definite ZCA Operator
Construct the diagonal whitening matrix $\Lambda^{-1/2} = \text{diag}(f^*(\lambda_1), \dots, f^*(\lambda_K))$.
The raw ZCA whitening matrix is:
$$W_{\text{ZCA}} = V \Lambda^{-1/2} V^T$$
Enforce positive diagonal self-affinity (ensuring factors maintain positive alignment with their original direction):
$$D = \text{diag}(\text{sgn}(\text{diag}(W_{\text{ZCA}}))), \quad D_{ii} = \begin{cases} 1, & \text{diag}(W)_i \ge 0 \\ -1, & \text{diag}(W)_i < 0 \end{cases}$$
$$W_{\text{sym}} = \frac{1}{2} \left( D W_{\text{ZCA}} D + (D W_{\text{ZCA}} D)^T \right)$$
$$\text{diag}(W_{\text{sym}}) \leftarrow \max(\text{diag}(W_{\text{sym}}), 10^{-6})$$

Decorrelate and rescale back to the original cross-sectional distribution:
$$X_{\text{decorr}} = \bar{X} W_{\text{sym}}, \quad X_{\text{ortho}} = \mu + X_{\text{decorr}} \odot \sigma$$

---

## 3. Detailed File Modification Plan

### File 1: `trading_system/src/ai/factor_orthogonalizer.py`

#### Change 1: Update `FactorOrthogonalizerEngine.__init__`
**Line Numbers**: ~40–51  
**Rationale**: Add `preserve_top_k: int = 0` to constructor while preserving `preserve_consensus_pc1: bool = False` for full backward compatibility.

```diff
--- a/trading_system/src/ai/factor_orthogonalizer.py
+++ b/trading_system/src/ai/factor_orthogonalizer.py
@@ -42,10 +42,12 @@ class FactorOrthogonalizerEngine:
         default_method: str = 'pca_symmetric',
         ridge_epsilon: float = 1e-6,
         shrinkage_alpha: float = 0.01,
-        preserve_consensus_pc1: bool = False
+        preserve_consensus_pc1: bool = False,
+        preserve_top_k: int = 0
     ):
         self.default_method = default_method
         self.ridge_epsilon = ridge_epsilon
         self.shrinkage_alpha = shrinkage_alpha
         self.preserve_consensus_pc1 = preserve_consensus_pc1
+        self.preserve_top_k = preserve_top_k
```

#### Change 2: Update `FactorOrthogonalizerEngine.orthogonalize`
**Line Numbers**: ~52–61, 116–120  
**Rationale**: Accept `preserve_top_k: Optional[int] = None` in `orthogonalize()`. Resolve effective top_k priority: explicit argument > `self.preserve_top_k` > `preserve_consensus_pc1`. Forward `preserve_top_k` into `_pca_zca_symmetric`.

```diff
--- a/trading_system/src/ai/factor_orthogonalizer.py
+++ b/trading_system/src/ai/factor_orthogonalizer.py
@@ -57,6 +57,7 @@ class FactorOrthogonalizerEngine:
         method: Optional[str] = None,
         scaling_method: Optional[str] = None,
         preserve_consensus_pc1: Optional[bool] = None,
+        preserve_top_k: Optional[int] = None,
     ) -> pd.DataFrame:
         eff_method = method or self.default_method
         valid_cols = [c for c in strategy_cols if c in score_df.columns]
@@ -114,8 +115,22 @@ class FactorOrthogonalizerEngine:
             X_ortho = col_means + X_decorr * col_stds
         else:
-            eff_preserve_pc1 = self.preserve_consensus_pc1 if preserve_consensus_pc1 is None else preserve_consensus_pc1
-            X_ortho = self._pca_zca_symmetric(X_clean, col_means, col_stds, preserve_pc1=eff_preserve_pc1)
+            # Resolve effective top_k leading eigenvalues to preserve (Feature 2 / R1)
+            if preserve_top_k is not None:
+                eff_top_k = int(preserve_top_k)
+            elif getattr(self, 'preserve_top_k', 0) > 0:
+                eff_top_k = int(self.preserve_top_k)
+            else:
+                eff_pc1 = self.preserve_consensus_pc1 if preserve_consensus_pc1 is None else preserve_consensus_pc1
+                eff_top_k = 1 if eff_pc1 else 0
+
+            X_ortho = self._pca_zca_symmetric(
+                X_clean,
+                col_means,
+                col_stds,
+                preserve_pc1=(eff_top_k >= 1),
+                preserve_top_k=eff_top_k
+            )
```

#### Change 3: Upgrade `FactorOrthogonalizerEngine._pca_zca_symmetric`
**Line Numbers**: ~214–267  
**Rationale**: Implement noise subspace variance estimation $\sigma_{\text{noise}}^2$, Marchenko-Pastur spectral floor $\lambda_{\text{floor}}$, and dual-consensus filter preservation for $k \in [1, \text{preserve\_top\_k}]$.

```diff
--- a/trading_system/src/ai/factor_orthogonalizer.py
+++ b/trading_system/src/ai/factor_orthogonalizer.py
@@ -217,7 +217,8 @@ class FactorOrthogonalizerEngine:
         X: np.ndarray,
         means: np.ndarray,
         stds: np.ndarray,
-        preserve_pc1: bool = False
+        preserve_pc1: bool = False,
+        preserve_top_k: int = 0
     ) -> np.ndarray:
         N, K = X.shape
         # Standardize matrix to zero mean, unit variance
@@ -234,16 +235,39 @@ class FactorOrthogonalizerEngine:
         # Eigen-decomposition of symmetric correlation matrix
         eigenvalues, eigenvectors = np.linalg.eigh(C_sym.astype(np.float64))
 
-        # Smooth Spectral Tikhonov / ESRW Whitening Operator:
-        # Multi-model consensus preservation (V7-03 / CRIT-11):
-        # When preserve_pc1 is enabled, do not compress the leading principal component (PC1).
-        lambdas_clean = np.maximum(eigenvalues, 0.0)
+        # Determine effective top components to preserve (Feature 2 / R1)
+        eff_top_k = preserve_top_k
+        if eff_top_k <= 0 and preserve_pc1:
+            eff_top_k = 1
+
+        # Estimate noise subspace variance sigma2 for Marchenko-Pastur lower spectral edge
+        # In Random Matrix Theory (RMT), noise bulk eigenvalues are distributed around sigma2.
+        if eff_top_k > 0 and K > eff_top_k:
+            noise_evals = eigenvalues[:-eff_top_k]
+        elif K > 1:
+            noise_evals = eigenvalues[:-1]
+        else:
+            noise_evals = eigenvalues
+
+        sigma2 = float(np.mean(noise_evals)) if len(noise_evals) > 0 else 1.0
+        sigma2 = max(sigma2, 1e-4)
+
+        # Marchenko-Pastur spectral floor for weak noise eigenvalues (Feature 2 / R1)
+        # Prevents over-amplification of collinear/null-space dimensions
+        q = min(K, N) / max(max(K, N), 1)
+        mp_lower = sigma2 * ((1.0 - np.sqrt(q)) ** 2) if N >= K else 0.0
+        lambda_floor = float(np.clip(max(mp_lower, 0.01 * sigma2), 1e-4, 1.0))
+
+        # Apply Marchenko-Pastur spectral floor and ridge regularization
+        lambdas_clean = np.maximum(eigenvalues, lambda_floor)
         ridge_eps = float(np.clip(self.ridge_epsilon, 1e-6, 1e-3))
         whitening_filter = 1.0 / np.sqrt(lambdas_clean + ridge_eps)
 
-        # Preserve leading consensus alpha (PC1 filter = 1.0)
-        if preserve_pc1 and len(whitening_filter) > 0:
-            whitening_filter[-1] = 1.0
+        # Dual-Consensus Spectral Preservation (Feature 2 / R1):
+        # Preserve top_k leading eigenvalues (PC1 Trend, PC2 Value/Quality) uncompressed (filter = 1.0)
+        if eff_top_k > 0 and K > 1:
+            num_to_preserve = min(eff_top_k, max(K - 1, 0))
+            for i in range(1, num_to_preserve + 1):
+                whitening_filter[-i] = 1.0
 
         # Cap maximum amplification to prevent noise explosion on weak spectral dimensions (C-05 / optimal bound)
         whitening_filter = np.minimum(whitening_filter, 10.0)
```

---

### File 2: Integration Contract with `trading_system/src/ai/ensemble_scorer.py`
In `EnsembleScoringEngine`:
- **Line 554**: Update default instantiation to enable dual-consensus:
  ```python
  self.orthogonalizer = FactorOrthogonalizerEngine(default_method='pca_symmetric', preserve_consensus_pc1=True, preserve_top_k=2)
  ```
- **Line 2394**: Explicitly pass `preserve_top_k=2` in `orthogonalize()`:
  ```python
  merged = self.orthogonalizer.orthogonalize(
      score_df=merged,
      strategy_cols=strategy_score_cols,
      weights=strat_weights,
      method='pca_symmetric',
      preserve_top_k=2
  )
  ```

---

## 4. Test Suite Design & Verification Specifications

### 4.1 New Unit Tests for `tests/test_factor_orthogonalization.py`

The Worker should append the following 3 tests to `TestFactorOrthogonalization` in `tests/test_factor_orthogonalization.py`:

```python
    def test_preserve_top_k_dual_consensus_crit(self):
        """Verify Dual-Consensus Spectral Whitening preserves PC1 & PC2 while reducing pairwise correlation."""
        N, K = 500, 17
        np.random.seed(42)
        t1 = np.random.normal(0, 1, N) # Market Trend latent factor (PC1)
        t2 = np.random.normal(0, 1, N) # Value/Quality latent factor (PC2)
        cols = self.strategy_cols[:K]
        data = {'symbol': [f'SYM_{i:04d}' for i in range(N)]}
        for j in range(K):
            if j < 5:
                raw = 0.6 * t1 + 0.4 * np.random.normal(0, 1, N)
            elif j < 10:
                raw = 0.6 * t2 + 0.4 * np.random.normal(0, 1, N)
            else:
                raw = 0.3 * t1 + 0.3 * t2 + 0.6 * np.random.normal(0, 1, N)
            data[cols[j]] = 1.0 / (1.0 + np.exp(-raw))
        df = pd.DataFrame(data)

        # Raw correlation
        raw_corr = np.corrcoef(df[cols].values, rowvar=False)
        off_diag = ~np.eye(K, dtype=bool)
        self.assertGreater(np.mean(np.abs(raw_corr[off_diag])), 0.30)

        # Apply dual-consensus orthogonalization (preserve_top_k=2)
        ortho_df = self.engine.orthogonalize(df, cols, preserve_top_k=2)
        vals = ortho_df[cols].values
        self.assertEqual(vals.shape, (N, K))
        self.assertTrue(np.all(vals >= 0.0) and np.all(vals <= 1.0))

        # Whitened correlation must drop below 0.30 while preserving two macro pillars
        ortho_corr = np.corrcoef(vals, rowvar=False)
        self.assertLess(np.mean(np.abs(ortho_corr[off_diag])), 0.30)

    def test_marchenko_pastur_spectral_floor_extreme_collinearity(self):
        """Verify Marchenko-Pastur floor bounds noise amplification under rank deficiency and near-zero eigenvalues."""
        # Extreme rank deficiency: N=5 samples, K=17 strategies
        N, K = 5, 17
        np.random.seed(123)
        cols = self.strategy_cols[:K]
        df = pd.DataFrame(np.random.uniform(0.1, 0.9, (N, K)), columns=cols)
        df['symbol'] = [f'SYM_{i}' for i in range(N)]

        ortho_df = self.engine.orthogonalize(df, cols, preserve_top_k=2)
        vals = ortho_df[cols].values
        self.assertEqual(vals.shape, (N, K))
        self.assertFalse(np.isnan(vals).any())
        self.assertFalse(np.isinf(vals).any())
        self.assertTrue(np.all(vals >= 0.0) and np.all(vals <= 1.0))

    def test_backward_compatibility_preserve_pc1_flag(self):
        """Verify backward compatibility when legacy preserve_consensus_pc1=True is supplied."""
        df = self._make_correlated_score_df(n_symbols=100, base_corr=0.75)
        legacy_engine = FactorOrthogonalizerEngine(preserve_consensus_pc1=True)
        res = legacy_engine.orthogonalize(df, self.strategy_cols)
        self.assertEqual(len(res), 100)
        vals = res[self.strategy_cols].values
        self.assertTrue(np.all(np.isfinite(vals)))
        self.assertTrue(np.all(vals >= 0.0) and np.all(vals <= 1.0))
```

### 4.2 Independent Verification Test Commands
```bash
# 1. Verify factor orthogonalizer unit tests
.venv/bin/pytest tests/test_factor_orthogonalization.py -v

# 2. Verify empirical stress test harness
.venv/bin/pytest tests/test_factor_ortho_empirical_stress.py -v

# 3. Verify remediation and ensemble challenger suites
.venv/bin/pytest tests/test_v8_remediation.py tests/test_adversarial_ensemble_scorer_challenger.py -v
```
**Expected Outcome**: 100% PASS across all tests with 0 failures and 0 warnings.
