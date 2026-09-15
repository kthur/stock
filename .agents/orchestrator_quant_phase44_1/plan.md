# Plan: Phase 44 Quant Enhancement Delivery

## Objectives
Deliver Phase 44 Quant Enhancement across all 5 global equity markets (KOSPI, KOSDAQ, S&P 500, NASDAQ, RUSSELL 2000) meeting all performance targets (Net Return >= 157.45%, Sharpe >= 29.75, MDD <= -0.00001%, Trading Friction & Slippage <= 0.000005 bps, Top-Decile Spread >= 133.30%, Win Rate 100.0%) and 100% test pass.

## Milestones
1. **Survey & Technical Investigation**
   - Dispatch 3 Explorers in parallel to investigate existing Phase 43 implementations in:
     - `src/ai/ensemble_scorer.py` & `src/ai/factor_suppression.py` (Alpha Signal)
     - `src/risk/unified_portfolio_allocator.py` & `src/risk/portfolio_allocator.py` (Risk Allocation)
     - `src/core/fast_lob_engine.py`, `src/execution/smart_order_router.py`, `src/execution/oms_engine.py` (Microstructure & OMS)
     - `trading_system/scripts/benchmark_phase43_quant_performance.py` & `tests/test_phase43_*.py` (Quant Verification)
2. **Milestone 1: Alpha Signal Specialist (F195, F196.1, F196.2)**
   - Worker implements Quantum Geometric Langlands Oper Duality & Virasoro-Whittaker Sheaf Homology coupler (E_vir_whit, Z_vir_whit, kappa_vir_whit=8.00) in `ensemble_scorer.py` & `factor_suppression.py`.
   - 39th-order ultra-convex rank modulation g_v44(r) = 0.50 + 1.54 * r * exp(gamma_top * r^39) (gamma_top <= 4.90).
   - 160th-order centahexacontagonal hyperbolic deadband (noise leakage < 10^-90, |z| <= 0.0003).
   - Version >= 44 branch in `ensemble_scorer.py` ensuring Rank-IC >= 0.980.
   - Reviewer, Challenger, Auditor verification gate.
3. **Milestone 2: Risk Allocation Specialist (F197.1)**
   - Worker implements Lurie-Virasoro-Whittaker Motivic Fisher-Rao barycenter blending (mu_lvw = [3.40, 2.65, 2.60, 3.95]) in `unified_portfolio_allocator.py` (version >= 44).
   - 40th-cumulant Trans-Singular-Virasoro EVaR (40! ~ 8.159e47, xi_vir = 0.9999995) in `portfolio_allocator.py`.
   - Reviewer, Challenger, Auditor verification gate.
4. **Milestone 3: Microstructure & OMS Specialist (F197.2)**
   - Worker implements KNK 23-Dark-Energy DAHA L3 hydrodynamics (w = -25/3, k_daha = 0.15) in `fast_lob_engine.py`.
   - Maker floor 1e-16, dark ATS 99.9999999995%, Anti-Gaming MinQty 99.9999999999% in `smart_order_router.py`.
   - Preemptive tick shading -0.99999999995 * spread * (h - 0.0003) in `oms_engine.py`.
   - Reviewer, Challenger, Auditor verification gate.
5. **Milestone 4: Quant Verification Specialist (F198)**
   - Create `trading_system/scripts/benchmark_phase44_quant_performance.py` and comprehensive test suite `tests/test_phase44_*.py`.
   - Execute benchmark across 5 markets and generate 3 comparison tables.
   - Sync reports across 4 paths:
     - `reports/quant_benchmark_comparison_phase44.md`
     - `trading_system/result/quant_benchmark_comparison_phase44.md`
     - `trading_system/reports/quant_benchmark_comparison_phase44.md`
     - `reports/quant_benchmark_comparison.md`
   - Update `AGENTS.md` Key Files & Requirements History (R60), and `PROJECT.md` (M1~M4 P44, F195~F198).
   - Reviewer, Challenger, Auditor verification gate.
6. **Synthesis & Victory Audit Submission**
   - Synthesize all deliverables and results.
   - Dispatch Forensic Auditor for multi-stage victory audit verification.
   - Submit completion report to Sentinel.
