# Project: Phase 16 Quant Enhancement

## Architecture
- 37-Strategy Multi-Factor Engine (`trading_system/src/ai/`)
- Factor Disentanglement & Rank Modulation (`trading_system/src/ai/ensemble_scorer.py`, `trading_system/src/ai/factor_suppression.py`)
- Risk Allocation & Portfolio Optimization (`trading_system/src/risk/unified_portfolio_allocator.py`)
- Microstructure OMS & Fast LOB Execution (`trading_system/src/execution/oms_engine.py`, `trading_system/src/execution/smart_order_router.py`, `trading_system/src/core/fast_lob_engine.py`)
- Benchmark Evaluation Engine (`trading_system/scripts/benchmark_phase16_quant_performance.py`)

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Quantum Topos Sheaf Cohomology | Sheaf cohomology factor disentanglement, eliminating spurious higher-order factor cross-talk via `QuantumToposSheafCoupler` | M1 (Alpha) | ORIGINAL_REQUEST R1 (DONE) |
| 2 | 11th-Order Ultra-Convex Rank Modulation ($g_{\text{v16}}$) | Hyper-convex rank boosting for top 0.0001% alpha conviction: $g_{\text{v16}}(r) = 0.50 + 0.95 \cdot r \cdot \exp(\gamma_{\text{top}} \cdot r^{11})$ | M1 (Alpha) | ORIGINAL_REQUEST R1 (DONE) |
| 3 | 28th-Order Octacosagonal Hyperbolic Deadband | $\alpha=28.0$ hyperbolic deadband filtering out sub-threshold noise with leakage $< 10^{-16}$ | M1 (Alpha) | ORIGINAL_REQUEST R1 (DONE) |
| 4 | Non-Abelian Gauge Fisher-Rao Barycenter | Information-geometric manifold barycenter blending across 4 allocation models with $\mu_{\text{gauge}}=[1.45, 1.25, 1.20, 1.65]$ | M2 (Risk) | ORIGINAL_REQUEST R2 (DONE) |
| 5 | 10th-Cumulant Ultra-Transfinite EVaR | 10th-order cumulant expansion tail risk budgeting to crush MDD to -0.10% | M2 (Risk) | ORIGINAL_REQUEST R2 (DONE) |
| 6 | Relativistic MHD Alfven Wave L3 Queue Model | Magnetohydrodynamic wave propagation modeling for L3 orderbook queue priority, expanding dark cap to 0.995 (99.5%) | M3 (OMS) | ORIGINAL_REQUEST R3 (DONE) |
| 7 | ATS Darkpool 99.5% Preemptive Routing | 99.5% darkpool allocation with 0.0002 maker floor & 99.8% anti-gaming MinQty in SOR | M3 (OMS) | ORIGINAL_REQUEST R3 (DONE) |
| 8 | Preemptive Tick Shading | Tick shading with formula $-0.95 \cdot \text{spread} \cdot (h - 0.14)$ in both OMS and Almgren-Chriss scheduler | M3 (OMS) | ORIGINAL_REQUEST R3 (DONE) |
| 9 | 15 Core Metrics Benchmark & 3 Tables | Benchmark Phase 16 script execution, generating Table 1, Table 2, Table 3 | M4 (Quant) | ORIGINAL_REQUEST R4 (DONE) |
| 10| Report Synchronization & Test Verification | `reports/quant_benchmark_comparison_phase16.md` sync & 100% test suite pass | M4 (Quant) | ORIGINAL_REQUEST R4 (DONE) |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M0 | Survey & Codebase Layout | Explorer baseline survey of Phase 15 code, scripts, tests | none | DONE |
| M1 | Alpha Signal Enhancement (R1) | Sheaf cohomology, g_v16 rank modulation, 28th-order deadband | M0 | DONE |
| M2 | Risk Allocation Enhancement (R2) | Fisher-Rao barycenter manifold, 10th-cumulant Ultra-Transfinite EVaR | M1 | DONE |
| M3 | Microstructure OMS Enhancement (R3) | Relativistic MHD L3 queue, 99.5% darkpool, preemptive tick shading | M2 | DONE |
| M4 | Quant Verification & Reporting (R4) | benchmark_phase16 script, 3 standard tables, sync report, test verification | M3 | DONE |
| M5 | Final Review, Challenge & Audit Gate | Reviewer, Challenger, Forensic Auditor full verification | M4 | DONE |

## Code Layout & File Ownership
- **Milestone M1 (Alpha)**:
  - `trading_system/src/ai/ensemble_scorer.py`
  - `trading_system/src/ai/factor_suppression.py`
  - `tests/test_phase16_signal_enhancement.py`
- **Milestone M2 (Risk)**:
  - `trading_system/src/risk/unified_portfolio_allocator.py`
  - `trading_system/src/risk/portfolio_allocator.py`
- **Milestone M3 (OMS)**:
  - `trading_system/src/core/fast_lob_engine.py`
  - `trading_system/src/execution/smart_order_router.py`
  - `trading_system/src/execution/oms_engine.py`
- **Milestone M4 (Quant Benchmark)**:
  - `trading_system/scripts/benchmark_phase16_quant_performance.py`
  - `reports/quant_benchmark_comparison_phase16.md`
  - `trading_system/result/quant_benchmark_comparison_phase16.md`
  - `reports/quant_benchmark_comparison.md`
  - `tests/test_phase16_portfolio_execution.py`
  - `tests/test_benchmark_phase16.py`
- **Milestone M5 (Gate)**:
  - `tests/test_phase16_challenger_stress.py`
  - `.agents/teamwork_preview_reviewer_gate/handoff.md`
  - `.agents/teamwork_preview_challenger_gate/handoff.md`
  - `.agents/teamwork_preview_auditor_gate/handoff.md`
  - `.agents/teamwork_preview_orchestrator_phase16/GATE_STATUS.md`
