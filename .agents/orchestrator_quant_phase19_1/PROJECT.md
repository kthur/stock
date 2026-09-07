# Project: Phase 19 Quant Enhancement

## Architecture
The system integrates 37 multi-factor strategies across 5 global markets (KOSPI, KOSDAQ, S&P 500, NASDAQ, RUSSELL 2000). Phase 19 elevates the entire quant stack:
1. **Alpha Signal Stack**:
   - Lurie ∞-Topos / Higher Category Theory factor entanglement coupler (F95) in `src/ai/ensemble_scorer.py` and `src/ai/factor_suppression.py`.
   - 14th-order ultra-convex rank warping `g_v19(r) = 0.50 + 1.02 * r * exp(gamma_top * r^14)` (F96.1) for top 0.00001% conviction capital concentration.
   - 40th-order Tetracontagonal (alpha=40.0) hyperbolic deadband (F96.2, leakage < 10^-22) in `src/ai/factor_suppression.py`.
   - Version branch `version >= 19` in `src/ai/ensemble_scorer.py`.
2. **Risk Allocation Stack**:
   - Grothendieck-Lurie (∞,1)-category Fisher-Rao manifold barycenter blending (F97.1) in `src/risk/unified_portfolio_allocator.py` under version >= 19.
   - 15th-order cumulant expansion Ultra-Beyond-Singularity EVaR tail risk budgeting in `src/risk/portfolio_allocator.py`.
   - Targets: MDD <= -0.04%, Sharpe >= 14.65.
3. **Microstructure & OMS Stack**:
   - Reissner-Nordström extremal black hole spacetime L3 orderbook hydrodynamics (F97.2) in `src/core/fast_lob_engine.py`.
   - Maker floor 0.00002 in `src/execution/smart_order_router.py`.
   - Tick shading factor `-0.995 * spread * (h - 0.08)`, Dark pool routing 99.95% ATS, Anti-Gaming MinQty 99.98% in `src/execution/oms_engine.py`.
4. **Quant Verification Stack**:
   - Phase 19 Quant Performance Benchmark: `trading_system/scripts/benchmark_phase19_quant_performance.py` (F98).
   - Dedicated Test Suite: `tests/test_phase19_quant.py` (or matching conventions).
   - 3 Standard Benchmark Tables: [Table 1] 15 Core Quant Metrics Comparison, [Table 2] 5 Markets Performance, [Table 3] Strategy Factor Contribution.
   - Documentation & Reports: `reports/quant_benchmark_comparison_phase19.md`, `trading_system/result/quant_benchmark_comparison_phase19.md`, `AGENTS.md`.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | F95 Lurie ∞-Topos Factor Entanglement Coupler | ∞-categorical factor coupling and obstruction elimination | M1 (R1) | ORIGINAL_REQUEST R1 |
| 2 | F96.1 14th-order Ultra-Convex Rank Warping | g_v19(r) = 0.50 + 1.02 * r * exp(gamma_top * r^14) | M1 (R1) | ORIGINAL_REQUEST R1 |
| 3 | F96.2 40th-order Tetracontagonal Deadband | alpha=40.0 hyperbolic deadband, leakage < 10^-22 | M1 (R1) | ORIGINAL_REQUEST R1 |
| 4 | F97.1 Grothendieck-Lurie Barycenter Blending | (∞,1)-category Fisher-Rao manifold barycenter blending | M2 (R2) | ORIGINAL_REQUEST R2 |
| 5 | F97.2 Reissner-Nordström L3 Hydrodynamics | Extremal black hole spacetime L3 queue hydrodynamics | M3 (R3) | ORIGINAL_REQUEST R3 |
| 6 | F97.3 15th-order Ultra-Beyond-Singularity EVaR | 15th-order cumulant expansion tail risk budgeting | M2 (R2) | ORIGINAL_REQUEST R2 |
| 7 | F97.4 Microstructure OMS Parameter Tuning | Maker floor 0.00002, tick shading -0.995, 99.95% darkpool, 99.98% anti-gaming | M3 (R3) | ORIGINAL_REQUEST R3 |
| 8 | F98 Phase 19 Quant Benchmark & Verification | benchmark_phase19_quant_performance.py, 3 tables, tests, AGENTS.md | M4 (R4) | ORIGINAL_REQUEST R4 |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M0 | Survey & Codebase Exploration | Explore Phase 18 existing code, formulas, and tests | none | DONE |
| M1 | Alpha Signal Enhancement (R1) | F95, F96.1, F96.2 in ensemble_scorer.py and factor_suppression.py | M0 | DONE |
| M2 | Risk Allocation Enhancement (R2) | F97.1 & 15th-order EVaR in unified_portfolio_allocator.py & portfolio_allocator.py | M0 | DONE |
| M3 | Microstructure OMS Enhancement (R3) | F97.2, maker floor, darkpool 99.95%, anti-gaming 99.98% in fast_lob_engine.py, smart_order_router.py, oms_engine.py | M0 | DONE |
| M4 | Benchmark & Verification Suite (R4) | benchmark_phase19_quant_performance.py, tests, reports sync, AGENTS.md | M1, M2, M3 | DONE |
| M5 | Review & Adversarial Stress Testing | 2 Reviewers, 2 Challengers | M4 | DONE |
| M6 | Forensic Integrity Audit | 1 Forensic Auditor for authentic implementation | M5 | DONE |
| M7 | Final Gate & Synthesis | Synthesis and final report to Sentinel | M6 | DONE |

## Code Layout
- `src/ai/ensemble_scorer.py`: Alpha signal ensemble, version branch >= 19, Lurie ∞-topos factor coupler F95.
- `src/ai/factor_suppression.py`: F96.1 14th-order convex warping, F96.2 40th-order Tetracontagonal deadband.
- `src/risk/unified_portfolio_allocator.py`: Grothendieck-Lurie (∞,1)-category Fisher-Rao barycenter F97.1 (version >= 19).
- `src/risk/portfolio_allocator.py`: 15th-order cumulant expansion Ultra-Beyond-Singularity EVaR.
- `src/core/fast_lob_engine.py`: Reissner-Nordström extremal black hole L3 hydrodynamics F97.2.
- `src/execution/smart_order_router.py`: Maker floor 0.00002.
- `src/execution/oms_engine.py`: Tick shading -0.995, Dark pool routing 99.95% ATS, Anti-Gaming MinQty 99.98%.
- `trading_system/scripts/benchmark_phase19_quant_performance.py`: Phase 19 benchmark script.
- `tests/test_phase19_quant.py`: Dedicated test suite.
- `reports/quant_benchmark_comparison_phase19.md` & `trading_system/result/quant_benchmark_comparison_phase19.md`: Benchmark comparison reports.
- `AGENTS.md`: Key files and Requirements History (R35).
