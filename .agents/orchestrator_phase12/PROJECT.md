# Project: Phase 12 Genesis Quantitative Enhancement (v19 Production Master)

## Architecture
Integrated multi-factor, multi-model quantitative trading system operating across 5 global markets (KOSPI, KOSDAQ, SP500, NASDAQ, RUSSELL2000).
- **Data & Signal Layer**: 37 alpha strategies grouped into 5 pillars (`val`, `mom`, `flow`, `cat`, `net`).
- **Ensemble Scorer (`src/ai/ensemble_scorer.py`)**:
  - Non-Abelian Gauge Theory $SO(5)$ Yang-Mills Curvature Tensor $F_{12}$ and Stochastic Action Functional $\mathcal{S}_{\text{action}}$ coupling.
  - 7th-order hyperconvex rank modulation $g_{v12}(r) = 0.50 + 0.75 \cdot r \cdot \exp(\gamma_{top} \cdot r^7)$ for top 0.10% alpha conviction.
  - 14th-order (Tetradecagonal) hyperbolic deadband $z \cdot \tanh((|z|/\delta)^{14})$ for 99.999999% non-breakout noise attenuation.
- **Portfolio Construction Layer (`src/risk/unified_portfolio_allocator.py`)**:
  - 4-Model allocation (Black-Litterman, HERC, Risk Parity, EVT-CVaR) with Fisher-Rao manifold barycenter blending on $S^3$.
  - Higher-order Fréchet extreme value tail risk (Ultra-EVaR) with 14th-degree ultra-safety headroom redistribution.
- **Execution OMS & Smart Order Routing (`src/execution/smart_order_router.py`, `oms_engine.py`, `fast_lob_engine.py`)**:
  - Deep Hawkes L3 arrival intensity, 96% dark ATS preemption, 0.005 lit maker floor, 95% anti-gaming MinQty.
  - Preemptive tick shading $-0.60 \cdot spread \cdot (h - 0.25)$ at $h > 0.25$.
- **Benchmarking & Testing (`trading_system/scripts/benchmark_phase12_quant_performance.py`, `tests/`)**:
  - 15 core quantitative metrics across 5 markets, 3 canonical markdown comparison tables, and full 2,750+ test verification.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | F67 Non-Abelian Gauge Theory Coupling | Yang-Mills curvature tensor $F_{12}$ & Stochastic Action Functional $\mathcal{S}_{\text{action}}$ across 5 pillars | M1 | R1 |
| 2 | F68.1 7th-Order Hyperconvex Rank Modulation | $g_{v12}(r) = 0.50 + 0.75 \cdot r \cdot \exp(\gamma_{top} \cdot r^7)$ with $\gamma_{top} \le 1.35$ | M1 | R1 |
| 3 | F68.2 14th-Order Tetradecagonal Deadband | $z \cdot \tanh((|z|/\delta)^{14})$ with $\delta=0.045$, attenuation $< 10^{-8}$ | M1 | R1 |
| 4 | F69.1 Fisher-Rao Manifold Barycenter & Ultra-EVaR | Intrinsic spherical barycenter on $S^3$ & cubic Fréchet Ultra-EVaR tail risk budget | M2 | R2 |
| 5 | F69.2 Deep Hawkes L3 & 96% Dark Preemption | 96% dark ATS routing, 0.005 maker floor, 95% anti-gaming, $-0.60 \cdot spread \cdot (h - 0.25)$ peg | M2 | R2 |
| 6 | F70 Benchmark & 3 Canonical Tables | `benchmark_phase12_quant_performance.py`, [Table 1], [Table 2], [Table 3] in reports & results | M3 | R3 |
| 7 | F71 2,750+ Test Suite Zero Regression | 100% pass across all tests and dedicated Phase 12 unit tests | M3 | Acceptance |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | M1: Gauge Field Theory & Extreme Alpha Curvature | `src/ai/ensemble_scorer.py`, `tests/test_phase12_signal_enhancement.py` | none | PLANNED |
| 2 | M2: Information Manifold & L3 Deep Hawkes Execution | `src/risk/unified_portfolio_allocator.py`, `src/core/fast_lob_engine.py`, `src/execution/smart_order_router.py`, `src/execution/oms_engine.py`, `tests/test_phase12_portfolio_execution.py` | none | PLANNED |
| 3 | M3: Quantitative Benchmark & 15-Metric Report | `trading_system/scripts/benchmark_phase12_quant_performance.py`, `tests/test_benchmark_phase12.py`, reports generation, full test suite pass | M1, M2 | PLANNED |

## Code Layout & Write Boundaries
- **M1 Worker Ownership**:
  - `src/ai/ensemble_scorer.py`
  - `tests/test_phase12_signal_enhancement.py`
- **M2 Worker Ownership**:
  - `src/risk/unified_portfolio_allocator.py`
  - `src/core/fast_lob_engine.py`
  - `src/execution/smart_order_router.py`
  - `src/execution/oms_engine.py`
  - `tests/test_phase12_portfolio_execution.py`
- **M3 Worker Ownership**:
  - `trading_system/scripts/benchmark_phase12_quant_performance.py`
  - `tests/test_benchmark_phase12.py`
  - `reports/quant_benchmark_comparison_phase12.md`
  - `trading_system/result/quant_benchmark_comparison_phase12.md`
  - `reports/quant_benchmark_comparison.md`

## Interface Contracts
### `ensemble_scorer.py` -> `run_pipeline.py` & downstream:
- `EnsembleScoringEngine.score_ensemble`:
  - Returns `EnsembleScoringResult` with net expected return, alpha rankings, confidence metrics, and decision rationale.
  - Phase 12 mode triggered when `version=12` or enabled via trading config/defaults, preserving backward compatibility with `version <= 11`.
- `YangMillsGaugeFieldCoupler`:
  - Input: 5 pillar scores (`val`, `mom`, `flow`, `cat`, `net`), gauge coupling constant $g=0.85$, Higgs vacuum $v_0=1.0$.
  - Output: Regularizer $h_{gauge} \in (0, 1]$, action functional $\mathcal{S}_{\text{action}}$, curvature norm $\|F_{12}\|$.
- `compute_phase12_hyperconvex_rank_modulation`:
  - Input: normalized percentile rank $r \in [0, 1]$, regime-adaptive $\gamma_{top} \in [0.45, 1.35]$.
  - Output: modulated weight $g_{v12}(r) = 0.50 + 0.75 \cdot r \cdot \exp(\gamma_{top} \cdot r^7)$.
- `apply_tetradecagonal_hyperbolic_deadband`:
  - Input: raw z-score $z$, threshold $\delta=0.045$, power $\alpha=14.0$.
  - Output: denoised score $z \cdot \tanh((|z|/\delta)^{14})$.

### `unified_portfolio_allocator.py` -> Execution:
- `compute_fisher_rao_barycenter_blend`:
  - Input: paradigm weight matrix, importance weights $\lambda$, iterations, tolerance.
  - Output: barycenter weights $q^* \in \Delta^3$.
- `compute_ultra_evar_risk_measure`:
  - Input: loss array $L$, confidence level $\alpha=0.01$, $\xi_{jump}=0.5$, $\xi_{frechet}=0.2$.
  - Output: Ultra-EVaR coherent risk measure value $\ge \text{Super-EVaR}$.
- `calculate_peg_limit_price`:
  - Input: side, mid, spread, h (Hawkes intensity).
  - Output: pegged limit price with $-0.60 \cdot spread \cdot (h - 0.25)$ shading when $h > 0.25$.
