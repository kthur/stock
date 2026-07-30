# Test Blueprint: Milestone 2 Quantitative Alpha & Ensemble Orthogonalization (R2)

## 1. Executive Summary & Scope

This blueprint defines the comprehensive unit and benchmark test specification for **Milestone 2 (R2)** of the Stock Trading System. Milestone 2 enhances the quantitative alpha engine through two core innovations:
1. **Gram-Schmidt & PCA Factor Orthogonalization** in `src/ai/ensemble_scorer.py`: De-correlations of 17 raw strategy prediction signals to eliminate cross-strategy multicollinearity, ensuring mean cross-strategy correlation $|R_{ortho}| < 0.30$.
2. **Fast Cluster-Accelerated Cointegration Scanning** in `src/core/stat_arb.py`: Hierarchical $O(N \log N)$ K-Means/OPTICS pre-clustering + correlation screening scanner for statistical arbitrage, executing full 3,379 symbol cointegration discovery in **$< 30.0$ seconds**.

---

## 2. Current Test Suite Audit

An audit of existing test files in `tests/` and `trading_system/tests/` revealed the following baseline state:

| Existing Test File | Scope Covered | Missing / Gap for M2 R2 |
|-------------------|---------------|-------------------------|
| `test_hpo_and_2d_ensemble.py` | 2D market regime weights, dynamic Sharpe exponential weighting, 5-strategy score bounds | Does not test Gram-Schmidt or PCA matrix orthogonalization across 17 strategies; no cross-strategy correlation reduction verification ($< 0.30$). |
| `test_stat_arb_execution.py` | Basic 2-pair `find_cointegrated_pairs` unit test on 2 synthetic series (AAPL, MSFT), TWAP/VWAP order slicing | Only tests pairwise scanning on 2 symbols ($N=2$). Does not benchmark 3,379 symbol scale; does not test K-Means/OPTICS pre-clustering or $O(N \log N)$ performance ($< 30.0$s target). |
| `test_correlation_suppression.py` | Regime-based factor noise suppression penalty weights ($P_i(R)$) | Tests weight dampening multipliers, but does not perform matrix factor orthogonalization (Gram-Schmidt / PCA decomposition). |
| `test_ml_ensemble.py` | Stacking blender, meta-labeling score combination | Lacks factor orthogonalization tests and cluster-accelerated scanning benchmarks. |

---

## 3. Component Specification 1: Gram-Schmidt / PCA Factor Orthogonalization

### 3.1 Mathematical Specification & Contract
- **Input Matrix**: Raw signal matrix $X \in \mathbb{R}^{N \times 17}$ where $N$ is symbol count and columns represent 17 strategy scores in $[0, 1]$.
- **Target Transformation**:
  - **Gram-Schmidt**: Standardize $X \to \tilde{X}$, apply modified Gram-Schmidt (or QR decomposition $\tilde{X} = Q R$) to yield orthogonal basis $Q \in \mathbb{R}^{N \times 17}$. Rescale $Q$ back to $[0, 1]$ quantile domain.
  - **PCA Orthogonalization**: Compute covariance matrix $\Sigma = \frac{1}{N} \tilde{X}^T \tilde{X}$, diagonalize $\Sigma = V \Lambda V^T$, transform $Z = \tilde{X} V \Lambda^{-1/2}$, and project back to decorrelated feature space $X_{ortho}$.
- **Acceptance Criterion**:
  $$\text{Mean Off-Diagonal Correlation } \bar{\rho}_{off} = \frac{1}{K(K-1)} \sum_{i \neq j} |R_{ij, ortho}| < 0.30$$
  $$\text{95th Percentile Off-Diagonal Correlation } \rho_{95} < 0.40$$

### 3.2 Unit Test Specification (`TestFactorOrthogonalization`)

```python
import pytest
import numpy as np
import pandas as pd
from typing import Dict, List

class TestFactorOrthogonalization:

    def test_gram_schmidt_orthogonality(self):
        """
        Verify that Gram-Schmidt orthogonalization produces column vectors with near-zero pairwise dot products.
        Formula check: <q_i, q_j> approx 0 for i != j.
        """
        # Given: Correlated 17-strategy matrix (N=500, K=17)
        # Action: Call orthogonalize_factors(X, method="gram_schmidt")
        # Assert: max(|Q^T Q - I|) < 1e-6
        pass

    def test_pca_variance_preservation(self):
        """
        Verify that PCA factor orthogonalization preserves at least 95% of total signal variance.
        """
        # Given: Synthetic 17-strategy scores
        # Action: Call orthogonalize_factors(X, method="pca", variance_threshold=0.95)
        # Assert: cumulative explained variance ratio sum(lambda_i / sum(lambda)) >= 0.95
        pass

    def test_cross_strategy_correlation_reduction(self):
        """
        Primary M2 R2 SLA Test: Verifies reduced cross-strategy correlation < 0.30.
        """
        # Given: High-correlation synthetic input matrix (rho_raw in [0.60, 0.85])
        # Action: Compute R_raw vs R_ortho
        # Assert: mean(|R_ortho_offdiag|) < 0.30
        # Assert: max(|R_ortho_offdiag|) < 0.45
        pass

    def test_score_range_and_rank_preservation(self):
        """
        Verify that orthogonalized scores remain valid probabilities in [0.0, 1.0] and preserve relative stock rankings.
        """
        # Assert: min(X_ortho) >= 0.0, max(X_ortho) <= 1.0
        # Assert: Spearman rank correlation between raw sum score and ortho sum score >= 0.70
        pass

    def test_orthogonalization_edge_cases(self):
        """
        Edge cases:
        1. Rank deficient input matrix (e.g. strategy 3 is identical to strategy 1).
        2. Zero variance column (strategy produces constant 0.5 for all stocks).
        3. Small N (N = 5 symbols < 17 strategies).
        4. Input DataFrame containing NaNs.
        """
        pass
```

### 3.3 Benchmark Test Specification (`BenchmarkFactorOrthogonalization`)

```python
class BenchmarkFactorOrthogonalization:

    def test_benchmark_orthogonalization_latency(self):
        """
        Benchmark latency of factor orthogonalization for 3,379 symbols x 17 strategies.
        SLA Target: Execution time < 50 ms.
        """
        # Generate N=3379, K=17 random matrix
        # Measure start = time.perf_counter()
        # Call orthogonalize_factors(X)
        # elapsed = time.perf_counter() - start
        # Assert elapsed < 0.050 seconds (50 ms)
        pass

    def test_benchmark_orthogonalization_memory(self):
        """
        Verify float32 in-place memory efficiency.
        SLA Target: Memory consumption growth < 50 MB for full matrix orthogonalization.
        """
        pass
```

---

## 4. Component Specification 2: Fast Cointegration Scanner

### 4.1 Architectural Specification & Contract
- **Problem Context**: Pairwise cointegration testing on 3,379 symbols equals $\frac{3379 \times 3378}{2} = 5,707,131$ candidate pairs. Naive scanning takes $> 10$ minutes.
- **Hierarchical Clustering Pipeline**:
  1. **Feature Extraction**: Extract 120-day return vectors, log-price normalized profiles, and GICS/KRX sector codes.
  2. **K-Means / OPTICS Partitioning**: Cluster 3,379 symbols into $K = 40$ clusters ($\sim 85$ symbols per cluster).
  3. **Cluster & Correlation Pre-Screening**: Filter candidate pairs within clusters + top 3 nearest adjacent clusters using vectorized Pearson log-price correlation $|r| \ge 0.70$. Pair count drops from 5.7M to $\le 15,000$.
  4. **Engle-Granger ADF & OU Half-life Test**: Run vectorised linear regression and ADF test ($p \le 0.05$) + Ornstein-Uhlenbeck half-life validation ($2.0 \le t_{1/2} \le 40.0$).
- **Acceptance Criterion**: Full scan across 3,379 symbols completed in **$< 30.0$ seconds**.

### 4.2 Unit Test Specification (`TestFastCointegrationScanner`)

```python
class TestFastCointegrationScanner:

    def test_kmeans_optics_pre_clustering(self):
        """
        Verify that K-Means/OPTICS pre-clustering partitions 3,379 symbols into balanced clusters.
        """
        # Assert: Number of non-empty clusters == K
        # Assert: Every symbol assigned to exactly 1 cluster
        # Assert: Cluster centroid distance matrix is symmetric
        pass

    def test_two_stage_filtering_recall(self):
        """
        Verify that pre-clustering + correlation filtering does NOT miss true cointegrated pairs.
        SLA Target: Planted pair recall >= 95%.
        """
        # Given: Universe with 10 synthetic cointegrated pairs planted across different stocks
        # Action: Run find_cointegrated_pairs_fast()
        # Assert: At least 9 out of 10 planted pairs (>=95% recall) are detected
        pass

    def test_log_price_adf_and_half_life(self):
        """
        Verify Engle-Granger ADF t-stat, p-value, and OU half-life calculation accuracy on log-transformed prices.
        """
        # Given: Synthetically generated stationary spread with known half-life = 10.0 days
        # Action: Compute compute_half_life(spread)
        # Assert: abs(estimated_hl - 10.0) < 2.0
        pass

    def test_fast_scan_edge_cases(self):
        """
        Edge cases:
        1. Universe with missing price data / short history (< 30 days).
        2. Zero volatility / suspended trading stocks.
        3. Single sector dominated universe.
        4. Symbol names with special characters or mismatched lengths.
        """
        pass
```

### 4.3 Benchmark Test Specification (`BenchmarkFastCointegrationScanner`)

```python
class BenchmarkFastCointegrationScanner:

    def test_benchmark_3379_symbols_under_30s(self):
        """
        Primary M2 R2 SLA Benchmark: Full universe (3,379 symbols x 120 days) scan execution time < 30.0 seconds.
        """
        # Given: Synthetic prices_dict with 3,379 symbols x 120 days
        # Action: t0 = time.perf_counter()
        #         pairs = stat_arb.find_cointegrated_pairs_fast(prices_dict)
        #         elapsed = time.perf_counter() - t0
        # Assert: elapsed < 30.0 seconds
        # Assert: len(pairs) > 0
        pass

    def test_benchmark_complexity_scaling(self):
        """
        Verify sub-quadratic scalability curve O(N log N) across N in [100, 500, 1000, 2000, 3379].
        """
        # Assert: Time ratio T(3379) / T(1000) < (3379/1000)^1.5  (sub-quadratic scaling)
        pass

    def test_benchmark_memory_peak(self):
        """
        Verify peak memory usage during 3,379 symbol scanning remains under 500 MB.
        """
        pass
```

---

## 5. Synthetic Mock Data Generation Strategy

To ensure deterministic, reproducible, and leak-free unit and benchmark execution:

### 5.1 Correlated 17-Strategy Matrix Generator
```python
def make_synthetic_strategy_matrix(n_symbols: int = 3379, base_corr: float = 0.70, seed: int = 42) -> pd.DataFrame:
    """
    Generates an (N x 17) score matrix with controllable base correlation.
    """
    np.random.seed(seed)
    # Common latent factor
    latent = np.random.normal(0, 1, size=n_symbols)
    scores = {}
    strategies = [
        'reg_score', 'surge_score', 'll_score', 'vcp_rule_score', 'vcp_ml_score',
        'lstm_score', 'stat_arb_score', 'sector_score', 'rim_score', 'event_score',
        'mq_score', 'iv_skew_score', 'order_flow_score', 'reversal_score',
        'arm_score', 'card_score', 'latr_score'
    ]
    for strat in strategies:
        noise = np.random.normal(0, 1, size=n_symbols)
        raw = np.sqrt(base_corr) * latent + np.sqrt(1 - base_corr) * noise
        # Scale to [0, 1] sigmoid
        scores[strat] = 1.0 / (1.0 + np.exp(-raw))
    return pd.DataFrame(scores)
```

### 5.2 3,379 Symbol Stock Price History Generator
```python
def make_synthetic_stock_universe(n_symbols: int = 3379, n_days: int = 120, planted_pairs: int = 10, seed: int = 42) -> Dict[str, pd.DataFrame]:
    """
    Generates 3,379 synthetic stock price DataFrames with 120 days of OHLCV history and planted cointegrated pairs.
    """
    np.random.seed(seed)
    dates = pd.date_range("2026-01-01", periods=n_days, freq="B")
    universe = {}
    
    # Generate independent random walks
    for i in range(n_symbols):
        sym = f"SYM_{i:04d}"
        returns = np.random.normal(0.0003, 0.018, size=n_days)
        price = 100.0 * np.exp(np.cumsum(returns))
        df = pd.DataFrame({
            "Open": price,
            "High": price * 1.01,
            "Low": price * 0.99,
            "Close": price,
            "Volume": np.random.randint(50000, 5000000, size=n_days)
        }, index=dates)
        universe[sym] = df
        
    # Plant cointegrated pairs
    for p in range(planted_pairs):
        s1 = f"SYM_{p:04d}"
        s2 = f"SYM_{p+1000:04d}"
        # Make s2 cointegrated with s1: s2 = 1.5 * s1 + noise
        p1 = universe[s1]["Close"].values
        noise = np.random.normal(0, 0.5, size=n_days)
        p2 = 1.5 * p1 + noise
        universe[s2]["Close"] = p2
        universe[s2]["Open"] = p2
        universe[s2]["High"] = p2 * 1.01
        universe[s2]["Low"] = p2 * 0.99

    return universe
```

---

## 6. Test Suite Structure & Pytest Integration

The tests will be organized in two dedicated test files co-located in `tests/`:

```
tests/
├── test_factor_orthogonalization.py  # Unit & Benchmark tests for GS/PCA Orthogonalization
└── test_fast_cointegration.py        # Unit & Benchmark tests for Cluster Cointegration Scanner
```

### Pytest Execution Commands
```bash
# Run unit tests only
.venv/bin/pytest tests/test_factor_orthogonalization.py tests/test_fast_cointegration.py -m unit -v

# Run 3379-symbol performance benchmark tests
.venv/bin/pytest tests/test_factor_orthogonalization.py tests/test_fast_cointegration.py -m benchmark -v --durations=10
```

---

## 7. Summary Table of Test Specifications & Metrics

| Component | Target Metric / Requirement | Unit Test Method | Benchmark Test Method | SLA Acceptance Threshold |
|-----------|----------------------------|------------------|-----------------------|--------------------------|
| **Factor Orthogonalization** | Cross-Strategy Correlation | `test_cross_strategy_correlation_reduction` | `test_benchmark_orthogonalization_latency` | Mean $\|R_{ortho}\| < 0.30$; Latency $< 50\text{ ms}$ for $N=3,379$ |
| **Factor Orthogonalization** | Rank & Score Integrity | `test_score_range_and_rank_preservation` | N/A | Min $\ge 0.0$, Max $\le 1.0$; Spearman $\rho \ge 0.70$ |
| **Fast Cointegration Scanner** | Execution Speed | `test_kmeans_optics_pre_clustering` | `test_benchmark_3379_symbols_under_30s` | Scan execution time $< 30.0\text{ s}$ for 3,379 symbols |
| **Fast Cointegration Scanner** | Pair Detection Recall | `test_two_stage_filtering_recall` | `test_benchmark_complexity_scaling` | Planted cointegrated pair recall $\ge 95\%$; $O(N \log N)$ complexity |
