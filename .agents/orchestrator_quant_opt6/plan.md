# Phase 6 Execution Plan

## Objective
Execute the 6th deep quantitative enhancement across 37 strategies in 5 global equity markets, achieving higher Net Expected Return, Sharpe Ratio, and Information Coefficient (Rank-IC) while keeping maximum drawdown and transaction costs tightly constrained.

## Milestone Decomposition

### Milestone 1 (M1 / R1): 37-Strategy Dynamic Alpha Coupling & Right-Tail Confidence Scaling
- **F41**: High-Order Tensor Signal Coupling & Right-Tail Confidence Scaling
  - Enhance non-linear multi-factor tensor coupling across Valuation, Momentum, Flow, and Catalyst pillars.
  - Scale right-tail conviction ($u > u_{\text{thresh}}$) using generalized Richards growth curve with parameter tuning for top-decile alpha expansion while strictly preserving monotonic ranking.
- **F42**: Adaptive Regime Transition Half-Life & Noise Deadband Precision
  - Implement probabilistic transition matrix weighting with Shannon entropy dampening and Total Variation jump penalty.
  - Fine-tune smooth $C^\infty$ hyperbolic tangent deadband soft-thresholding to suppress whipsaws during choppy sideways and crisis transitions.
- **Target Files**: `src/ai/ensemble_scorer.py`, `src/ai/factor_suppression.py`, `tests/test_phase6_signal_enhancement.py`
- **Cycle**: Explorer(s) -> Worker -> Reviewers -> Challengers -> Forensic Auditor -> Gate

### Milestone 2 (M2 / R2): 4-Model Portfolio Allocation & L3 Orderbook Friction Minimization
- **F43**: Regime-Adaptive 4-Model Reliability Optimization & Tail Risk Budgeting
  - Optimize dynamic mixing weights between Black-Litterman, HERC, Risk Parity, and EVT-CVaR across 2D regimes.
  - Advance higher-order co-moments (co-skewness and co-kurtosis) integration into Cornish-Fisher dynamic expansion and Diversification Ratio (DRP-DR) scaling.
- **F44**: L3 Micro-Price Pegging & Darkpool Liquidity Capture
  - Enhance SmartOrderRouter (SOR) with Level-3 orderbook micro-price pegging, continuous Hawkes process toxicity decay, and darkpool midpoint resting orders (MinQty >= 20%).
  - Refine market-specific Leland buffer bands and Gatheral volume smile execution slicing.
- **Target Files**: `src/risk/unified_portfolio_allocator.py`, `src/execution/smart_order_router.py`, `src/core/fast_lob_engine.py`, `src/execution/oms_engine.py`, `tests/test_phase6_portfolio_execution.py`
- **Cycle**: Explorer(s) -> Worker -> Reviewers -> Challengers -> Forensic Auditor -> Gate

### Milestone 3 (M3 / R3): Quantitative Benchmark Performance Engine & Reports Generation
- **F45**: Phase 6 Benchmark Engine & 15-Metric Quantitative Comparison
  - Build `trading_system/scripts/benchmark_phase6_quant_performance.py` and verification test `tests/test_benchmark_phase6.py`.
  - Benchmark 15 institutional metrics across all 5 markets (KOSPI, KOSDAQ, S&P 500, NASDAQ, RUSSELL 2000).
  - Synchronize Markdown comparison tables across:
    1. `reports/quant_benchmark_comparison_phase6.md`
    2. `trading_system/result/quant_benchmark_comparison_phase6.md`
    3. `reports/quant_benchmark_comparison.md`
- **Cycle**: Explorer(s) -> Worker -> Reviewers -> Challengers -> Forensic Auditor -> Gate

### Milestone 4 (M4 / F46): Full Repository Regression Verification
- Run full pytest test suite across 2,442+ tests.
- Ensure 100% pass rate (2 expected live broker socket test skips allowed).
- Synthesize all findings and prepare final handoff.
