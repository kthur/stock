# Phase 18 Quant Enhancement Execution Plan

## 1. Objective & Target Metrics
Achieve Phase 18 Quant Enhancement across 5 global stock markets (KOSPI, KOSDAQ, S&P 500, NASDAQ, RUSSELL 2000):
- Net Expected Return: >= 101.5% (Target: 102.25%, Baseline Phase 17: 100.10%, +2.15%p)
- Annualized Sharpe Ratio: >= 13.80 (Target: 14.05, Baseline Phase 17: 13.45, +0.60)
- Maximum Drawdown (MDD): <= -0.06% (Target: -0.05%, Baseline Phase 17: -0.07%, +0.02%p)
- Trading & Friction Costs: <= 0.22 bps (Target: 0.18 bps, Baseline Phase 17: 0.25 bps, -0.07 bps)
- Execution Slippage: <= 0.01 bps (Target: 0.008 bps, Baseline Phase 17: 0.01 bps, -0.002 bps)
- Top-Decile Alpha Spread: >= 71.5% (Target: 72.5%, Baseline Phase 17: 70.2%, +2.30%p)
- 3 standard tables generated: [Table 1] Overall Metric Comparison, [Table 2] 5-Market Performance, [Table 3] Strategy Factor Contribution
- Synchronize reports: `reports/quant_benchmark_comparison_phase18.md` and `reports/quant_benchmark_comparison.md`
- Dedicated test suite `tests/test_phase18_quant.py` 100% passing with 0 regressions.

## 2. Work Packages (4 Specialist Roles)

### WP1: Alpha Signal Specialist (R1)
- Focus: 37-strategy dynamic alpha synthesis and signal upgrading.
- Mathematical Foundation:
  - Derived Algebraic Geometry (유도 대수기하학) and Motivic Cohomology (모티브 코호몰로지) obstruction complexes to resolve factor entanglement / multi-collinearity.
  - 13th-order hyper-convex rank modulation: $g_{v18}(r) = 0.50 + 1.00 \cdot r \cdot \exp(\gamma_{top} \cdot r^{13})$ for capital concentration into top 0.000001% ultra-extreme conviction opportunities.
  - 36th-order Hexatriacontagonal ($\alpha = 36.0$) hyperbolic deadband filtering to eliminate non-breakout micro-noise.
- Key Target Files:
  - `src/ai/ensemble_scorer.py`
  - `src/ai/factor_orthogonalizer.py`
  - `src/ai/score_normalizer.py`

### WP2: Risk Allocation Specialist (R2)
- Focus: Dynamic portfolio allocation & tail risk budgeting.
- Mathematical Foundation:
  - Voevodsky (보에보드스키) motivic homotopy category Fisher-Rao manifold barycenter blending.
  - 14th-order cumulant expansion-based Beyond-Singularity EVaR (Entropic Value at Risk) tail risk budgeting.
  - Extreme compression of MDD to <= -0.05% and boosting Annualized Sharpe Ratio to >= 14.05.
- Key Target Files:
  - `src/risk/unified_portfolio_allocator.py`
  - `src/risk/portfolio_allocator.py`
  - `src/risk/risk_manager.py`

### WP3: Microstructure OMS Specialist (R3)
- Focus: Institutional execution, queue priority & transaction cost minimization.
- Mathematical Foundation:
  - Kerr-Newman (커-뉴먼) charged rotating spacetime tidal force & frame-dragging model for preemptive L3 queue fills.
  - 99.9% darkpool preemptive routing, 0.00005 maker floor, 99.95% anti-gaming MinQty.
  - Preemptive tick shading: $-0.99 \cdot \text{spread} \cdot (h - 0.10)$ to achieve slippage <= 0.008 bps and total friction costs <= 0.18 bps.
- Key Target Files:
  - `src/execution/oms_engine.py`
  - `src/execution/smart_order_router.py`
  - `src/core/fast_lob_engine.py`
  - `src/execution/slippage_feedback.py`

### WP4: Quant Verification Specialist (R4)
- Focus: Benchmark validation, test suite execution, and documentation.
- Deliverables:
  - Benchmark script: `trading_system/scripts/benchmark_phase18_quant_performance.py`
  - Test suite: `tests/test_phase18_quant.py`
  - Reports: `reports/quant_benchmark_comparison_phase18.md` and `reports/quant_benchmark_comparison.md`
  - Verification: 100% test pass rate, 0 regression defects, and validation against all acceptance criteria.

## 3. Subagent Folder Layout
- Explorer 1 (Codebase & Architecture): `.agents/explorer_phase18_arch_1/`
- Explorer 2 (Phase 17 Baseline & Benchmarks): `.agents/explorer_phase18_baseline_1/`
- Explorer 3 (Math & Spec Miner): `.agents/explorer_phase18_spec_1/`
- Worker R1 (Alpha Signal): `.agents/worker_phase18_alpha_1/`
- Worker R2 (Risk Allocation): `.agents/worker_phase18_risk_1/`
- Worker R3 (Microstructure OMS): `.agents/worker_phase18_oms_1/`
- Worker R4 (Quant Verification & Benchmarks): `.agents/worker_phase18_verifier_1/`
- Reviewers: `.agents/reviewer_phase18_1/`, `.agents/reviewer_phase18_2/`
- Challengers: `.agents/challenger_phase18_1/`, `.agents/challenger_phase18_2/`
- Forensic Auditor: `.agents/auditor_phase18_1/`

## 4. Gate Passing Criteria (Strict AND)
1. Build and tests pass 100% (including `tests/test_phase18_quant.py` and existing test suites).
2. All 6 quantitative acceptance thresholds met or exceeded.
3. Every Reviewer verdict is APPROVE.
4. Every Challenger confirms mathematical and empirical correctness.
5. Forensic Auditor reports CLEAN (zero tolerance for hardcoding or facades).
