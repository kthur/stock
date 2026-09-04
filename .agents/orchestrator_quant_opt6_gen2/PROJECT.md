# Project: Phase 6 Deep Quantitative Enhancements (6차 심화 퀀트 개선) — Gen 2

## Architecture
- **Layer 1: 37-Strategy Dynamic Alpha Engine & Noise Suppression**
  - High-order tensor signal combination and cross-sectional right-tail confidence scaling in `src/ai/ensemble_scorer.py`.
  - Probabilistic Markov regime transition uncertainty, continuous half-life decay, and $C^\infty$ hyperbolic tangent noise deadband in `src/ai/ensemble_scorer.py` and `src/ai/factor_suppression.py`.
- **Layer 2: 4-Model Portfolio Adaptive Allocation & Execution Friction Optimization**
  - Black-Litterman, HERC, Risk Parity, and EVT-CVaR regime-adaptive blending with co-moment tail risk budgeting in `src/risk/unified_portfolio_allocator.py`.
  - SmartOrderRouter (SOR) with continuous Hawkes toxicity modulation, Level-3 micro-price pegging, and darkpool liquidity capture in `src/execution/smart_order_router.py`, `src/core/fast_lob_engine.py`, and `src/execution/oms_engine.py`.
- **Layer 3: Quantitative Benchmark & Reporting Engine**
  - Dedicated benchmark script `trading_system/scripts/benchmark_phase6_quant_performance.py` evaluating 15 institutional metrics across 5 markets (KOSPI, KOSDAQ, S&P 500, NASDAQ, RUSSELL 2000).
  - Synchronized reports in `reports/quant_benchmark_comparison_phase6.md`, `trading_system/result/quant_benchmark_comparison_phase6.md`, and `reports/quant_benchmark_comparison.md`.
- **Layer 4: Full Repository Regression Verification**
  - Comprehensive 2,442+ test suite verification ensuring zero regressions.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---|---|---|---|
| 1 | F41 | High-Order Tensor Signal Coupling & Right-Tail Confidence Scaling | M1 | ORIGINAL_REQUEST §R1 |
| 2 | F42 | Adaptive Regime Transition Half-Life & Noise Deadband Precision | M1 | ORIGINAL_REQUEST §R1 |
| 3 | F43 | Regime-Adaptive 4-Model Reliability Optimization & Tail Risk Budgeting | M2 | ORIGINAL_REQUEST §R2 |
| 4 | F44 | L3 Micro-Price Pegging & Darkpool Liquidity Capture | M2 | ORIGINAL_REQUEST §R2 |
| 5 | F45 | Phase 6 Quantitative Benchmark Performance Engine & 5-Market Tables | M3 | ORIGINAL_REQUEST §R3 |
| 6 | F46 | Full Repository Regression Verification across 2,442+ Tests | M4 | Acceptance Criteria |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|---|---|---|---|
| 1 | Milestone 1 (M1 / R1) | 37-Strategy Dynamic Alpha Coupling & Right-Tail Confidence (F41, F42) | None | DONE |
| 2 | Milestone 2 (M2 / R2) | 4-Model Portfolio Allocation & L3 Orderbook Friction Minimization (F43, F44) | M1 Interface | DONE |
| 3 | Milestone 3 (M3 / R3) | Quantitative Benchmark Performance Engine & Comparative Reports (F45) | M1, M2 | DONE |
| 4 | Milestone 4 (M4 / F46) | Full Repository Regression Verification (2,442+ tests) | M1, M2, M3 | IN_PROGRESS |

## Code Layout
- `trading_system/src/ai/ensemble_scorer.py`: 37-strategy weighting, tensor signal combination, right-tail scaling, regime half-life
- `trading_system/src/ai/factor_suppression.py`: Factor noise deadband, entropy-weighted VIF suppression
- `trading_system/src/risk/unified_portfolio_allocator.py`: 4-Model regime weights, co-moments EVT-CVaR, DRP-DR scaling, F43 Information-Theoretic reliability
- `trading_system/src/execution/smart_order_router.py`: Hawkes toxicity modulation, Level-3 micro-pegging, darkpool midpoint resting, F44 anti-gaming
- `trading_system/src/core/fast_lob_engine.py`: L3 orderbook matching, Bivariate Hawkes intensity tracking, FIFO queue position estimation
- `trading_system/src/execution/oms_engine.py`: 8-safety gates, execution slicing, Leland buffer bands, L3 peg price calculation
- `trading_system/scripts/benchmark_phase6_quant_performance.py`: Phase 6 benchmark evaluation script
- `tests/test_phase6_signal_enhancement.py`: Phase 6 signal enhancement unit tests (M1)
- `tests/test_phase6_m1_challenger1_adversarial.py`: Phase 6 adversarial stress harness (M1)
- `tests/test_phase6_portfolio_execution.py`: Phase 6 portfolio & execution unit tests (M2)
- `reports/quant_benchmark_comparison_phase5.md`: Baseline comparison reference
- `reports/quant_benchmark_comparison_phase6.md`: Phase 6 authoritative quantitative comparison report
- `trading_system/result/quant_benchmark_comparison_phase6.md`: Synced benchmark report
- `reports/quant_benchmark_comparison.md`: Master benchmark report
