# Handoff Report: Milestone 2 Testing Strategy (R2)

## 1. Observation
- **Inspected Files**:
  - `PROJECT.md`: Defines Milestone 2 scope (R2), Gram-Schmidt & PCA factor orthogonalization across 17 strategies (`src/ai/ensemble_scorer.py`), and cluster-accelerated cointegration scanner (K-Means/OPTICS) (`src/core/stat_arb.py`).
  - `trading_system/src/ai/ensemble_scorer.py` (lines 1-120): Defines `EnsembleScoringEngine` with 17 strategies (`regression`, `surge`, `lead_lag`, `vcp_rule`, `vcp_ml`, `lstm`, `stat_arb`, `sector_rotation`, `rim_valuation`, `event_driven`, `mq_factor`, `iv_skew`, `order_flow`, `short_term_reversal`, `arm_factor`, `card_factor`, `latr_factor`).
  - `trading_system/src/ai/correlation_monitor.py` (lines 1-100): Implements `StrategyCorrelationMonitor` computing 17x17 Spearman rank correlation matrix $R$.
  - `trading_system/src/ai/factor_suppression.py` (lines 1-100): Implements `RegimeFactorSuppressionEngine` calculating factor noise dampening penalties $P_i(R)$.
  - `trading_system/src/core/stat_arb.py` (lines 83-247): Implements `StatisticalArbitrageEngine.find_cointegrated_pairs()` with 2-stage correlation + ADF test.
  - `trading_system/tests/test_hpo_and_2d_ensemble.py` (lines 164-254): Tests 2D regime weights and dynamic Sharpe weighting, but lacks factor orthogonalization tests (GS/PCA) and correlation reduction checks (< 0.30).
  - `trading_system/tests/test_stat_arb_execution.py` (lines 19-46): Tests 2-pair `find_cointegrated_pairs` unit test on AAPL/MSFT, but lacks 3,379 symbol scale benchmarks and K-Means/OPTICS pre-clustering performance checks (< 30.0s target).

## 2. Logic Chain
1. **Factor Orthogonalization SLA Requirement**: The 17 strategy prediction scores exhibit baseline cross-strategy correlation ($\bar{\rho} \approx 0.50 \sim 0.75$). Gram-Schmidt / PCA factor orthogonalization must reduce average off-diagonal cross-strategy correlation to $< 0.30$ while preserving signal rank ordering and $[0, 1]$ score bounds.
2. **Fast Cointegration Scanning SLA Requirement**: Scanning 3,379 symbols pairwise without acceleration requires $\frac{3379 \times 3378}{2} = 5,707,131$ tests, which takes $> 10$ minutes in Python. Pre-clustering into $K=40$ clusters using K-Means/OPTICS and pre-screening via log-price Pearson correlation reduces candidate pairs to $\le 15,000$, enabling complete scanning in $< 30.0$ seconds ($O(N \log N)$ complexity).
3. **Test Blueprint Design**: Unit tests cover mathematical correctness (orthogonality $\langle q_i, q_j \rangle \approx 0$, variance preservation $\ge 95\%$, half-life accuracy, edge cases). Benchmark tests enforce SLA thresholds ($|R_{ortho}| < 0.30$, latency $< 50\text{ ms}$ for orthogonalization; scan time $< 30.0\text{ s}$ for 3,379 symbols).

## 3. Caveats
- **Read-Only Scope**: This investigation did not modify project source code in `src/` or `tests/`. Test implementation will be executed by Implementer agents.
- **Hardware Performance Variance**: The $< 30.0$ seconds SLA benchmark assumes multi-core CPU execution (standard CI runner). On single-core constrained environments, vectorised NumPy / SciPy operations remain required for optimal performance.
- **Synthetic Data Fidelity**: Benchmark tests use synthetic correlated score matrices and synthetic daily price series with planted cointegrated pairs to guarantee deterministic and reproducible test runs.

## 4. Conclusion
- The test blueprint for **Milestone 2 (R2)** has been authored and saved to `d:\Finance\code\stock\.agents\teamwork_preview_explorer_m2_3\analysis.md`.
- Specifications cover both Gram-Schmidt / PCA factor orthogonalization (verifying mean cross-strategy correlation $< 0.30$) and fast cointegration scanning (verifying execution time $< 30.0$s for 3,379 symbols).

## 5. Verification Method
1. Inspect the test blueprint file:
   `view_file` at `d:\Finance\code\stock\.agents\teamwork_preview_explorer_m2_3\analysis.md`
2. Once test files are implemented, run:
   `.venv/bin/pytest tests/test_factor_orthogonalization.py tests/test_fast_cointegration.py -v`
3. Verify benchmark targets:
   `.venv/bin/pytest tests/test_factor_orthogonalization.py tests/test_fast_cointegration.py -m benchmark -v`
