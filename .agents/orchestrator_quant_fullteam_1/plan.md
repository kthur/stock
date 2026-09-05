# Project Plan: Quantitative Full Team Optimization (Phase 15 Supreme / Master)

## Architecture
- **Alpha Signal Engine**: `trading_system/src/ai/ensemble_scorer.py`, `score_normalizer.py`, `factor_orthogonalizer.py`, `factor_suppression.py`.
- **Portfolio Risk Budgeting**: `trading_system/src/risk/unified_portfolio_allocator.py`, `portfolio_allocator.py`, `src/analysis/portfolio_optimizer.py`, `src/risk/risk_manager.py`.
- **Microstructure L3 OMS/SOR**: `trading_system/src/core/fast_lob_engine.py`, `src/execution/oms_engine.py`, `src/execution/smart_order_router.py`, `src/execution/slippage_feedback.py`.
- **Quant Benchmark & Verification**: `trading_system/scripts/benchmark_phase15_quant_performance.py`, `reports/quant_benchmark_comparison*.md`, `tests/`.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Factor Unentanglement | PCA-ZCA whitening with Marchenko-Pastur RMT spectral floor & sample-size Fisher z-SE correlation suppression | M1 | Survey E1 |
| 2 | Hyper-Convex Rank Modulation | 10th/11th-order hyper-convex rank modulation $g(r)$ for extreme capital concentration on top-decile alphas | M1 | Survey E1 |
| 3 | Hyperbolic Noise Deadband | 24th/30th-order hyperbolic tangent deadband soft-thresholding for complete micro noise removal | M1 | Survey E1 |
| 4 | Pipeline Version Plumbing | Fix version propagation in `run_pipeline.py` and `ensemble_scorer.py` to prevent version 5 fallback | M1 | Survey E1 |
| 5 | 4-Model Information Geometry | Langlands Automorphic Hecke Operator Fisher-Rao Barycenter on $S^3$ across 4 models (BL, HERC, RP, EVT-CVaR) | M2 | Survey E2 |
| 6 | Super-Coherent EVaR Budgeting | 6th-order cumulant expansion EVaR ($\psi_{\text{supra}}$) with Euler CCVaR headroom redistribution | M2 | Survey E2 |
| 7 | Asymmetric Leland Buffer Bands | Granular market cost calibration, asymmetric winner/loser multipliers, and boundary rebalancing | M2 | Survey E2 |
| 8 | Multi-Tier MDD Crisis Controls | Smooth sigmoid crisis gating, cash target scaling, and ATR trailing stop tightening | M2 | Survey E2 |
| 9 | L3 Order Book Fluid Dynamics | Distance-decayed $QI_{L3}^*$, 2nd-order acceleration $a_{QI}$, 3rd-order jerk $j_{QI}$, Deep-OFI, predictive micro-price | M3 | Survey E3 |
| 10 | Preemptive ATS Darkpool Routing | Preemptive dark volume shifting up to 99%, lit maker contraction (0.0005), and anti-gaming MinQty (99.5%) | M3 | Survey E3 |
| 11 | Toxic Flow Preemptive Shading | Multivariate Hawkes cross-excitation preemptive shading against adverse selection spikes | M3 | Survey E3 |
| 12 | Realized Slippage Feedback | Closed-loop Bayesian cost scaling and realized slippage tracking from `trade_logs.db` | M3 | Survey E3 |
| 13 | 5-Market Quant Benchmark | Production benchmark engine evaluating 15 core + 3 auxiliary metrics across KOSPI, KOSDAQ, SP500, NASDAQ, RUSSELL2000 | M4 | Survey E3 |
| 14 | 3 Standard Tables Output | Generation and report synchronization of [표 1] 15대 종합 지표, [표 2] 5대 시장별 성과, [표 3] 전략 팩터 기여도 | M4 | Survey E3 |
| 15 | Test Suite Verification | Pytest validation of unit/integration test suites ensuring 100% pass rate with zero regression | M4 | Survey E3 |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Alpha Signal & Dynamic Ensemble | Factor unentanglement, rank modulation, hyperbolic deadband, pipeline version plumbing | None | READY |
| M2 | Portfolio Risk Budgeting & Allocation | Fisher-Rao barycenter blending, super-coherent EVaR budgeting, Leland buffer bands | M1 contract | READY |
| M3 | Microstructure L3 OMS & Friction Minimization | L3 fluid dynamics, ATS preemptive routing, Hawkes toxic shading, slippage feedback | M2 contract | READY |
| M4 | 5-Market Quant Benchmark & Tables | 15-metric evaluation across 5 markets, 3 standard tables, report sync, pytest verification | M1, M2, M3 | READY |

## Interface Contracts
### Alpha Engine (M1) ↔ Portfolio Allocator (M2)
- Output DataFrame: `merged` containing `ensemble_score` $\in [0.0, 1.0]$, `ensemble_expected_return` (annualized net expected return in %), `Market`, `symbol`.
- Contract: Monotonic rank preservation, top-decile spread $\ge 65.0\%$, Rank-IC $\ge 0.400$.

### Portfolio Allocator (M2) ↔ Execution OMS (M3)
- Output DataFrame: Target weights $w_i \in [0.0, 0.05]$ normalized to $\sum w_i \le 1.0$, cash target $w_{\text{cash}}$, Leland lower/upper buffer bands $[w_i^{\text{lower}}, w_i^{\text{upper}}]$.
- Contract: Rebalancing orders generated only for symbols violating buffer boundaries (or new entry / total liquidation).

### Execution OMS (M3) ↔ Quant Benchmark (M4)
- Metrics contract: Realized slippage $\le 0.05$ bps, Total friction costs $\le 0.6$ bps.
- Execution logs: `trade_logs.db` schema compatible with `SlippageFeedbackEngine`.

## Acceptance Targets
1. Net Expected Return: $\ge 95.0\%$ (Current benchmark: 95.25%)
2. Annualized Sharpe Ratio: $\ge 12.0$ (Current benchmark: 12.25)
3. Maximum Drawdown (MDD): $\le -0.18\%$ (Current benchmark: -0.15%)
4. Trading & Friction Costs: $\le 0.6$ bps (Current benchmark: 0.5 bps)
5. Execution Slippage: $\le 0.05$ bps (Current benchmark: 0.03 bps)
6. Top-Decile Alpha Spread: $\ge 65.0\%$ (Current benchmark: 65.5%)
