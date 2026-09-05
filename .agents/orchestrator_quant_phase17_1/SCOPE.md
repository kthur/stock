# Scope: Phase 17 Quant Enhancement across 5 Global Stock Markets

## Architecture
- **Alpha Signal Engine**: `src/ai/factor_suppression.py`, `src/ai/ensemble_scorer.py`, `src/ai/score_normalizer.py`.
- **Portfolio & Risk Allocation Layer**: `src/risk/unified_portfolio_allocator.py`, `src/risk/portfolio_allocator.py`.
- **Microstructure & Institutional Execution Layer**: `src/core/fast_lob_engine.py`, `src/execution/smart_order_router.py`, `src/execution/oms_engine.py`.
- **Benchmarking & Report Synchronization**: `trading_system/scripts/benchmark_phase17_quant_performance.py`, `reports/quant_benchmark_comparison_phase17.md`, `trading_system/result/quant_benchmark_comparison_phase17.md`, `reports/quant_benchmark_comparison.md`.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| F87 | Homological Mirror Symmetry & Fukaya Category | `HomologicalMirrorSymmetryCoupler` modeling 5 canonical pillars as Lagrangian submanifolds with symplectic flux $\Omega_{jk}$, Floer intersection instanton area $\mathcal{A}_{jk}$, mirror Ext discrepancy $\Delta_{\text{HMS}, jk}$, and topological invariant $Z_{\text{HMS}}$ | M1 | ORIGINAL_REQUEST R1 / Explorer 1 Survey |
| F88.1 | 12th-Order Ultra-Convex Rank Modulation $g_{\text{v17}}(r)$ | $g_{\text{v17}}(r) = 0.50 + 1.00 \cdot r \cdot \exp(\gamma_{\text{top}} \cdot r^{12})$ concentrating capital on top 0.00001% conviction alphas with regime-adaptive $\gamma_{\text{top}}$ | M1 | ORIGINAL_REQUEST R1 / Explorer 1 Survey |
| F88.2 | 32nd-Order Dotriacontagonal Hyperbolic Deadband | $z_{\text{denoised}} = z \cdot \tanh((|z|/\delta_{\text{eff}})^{32})$ extinguishing sub-threshold noise leakage to $< 10^{-20}$ while preserving 100% transmission at $|z| \ge 0.150$ | M1 | ORIGINAL_REQUEST R1 / Explorer 1 Survey |
| F89.1 | Noncommutative Motive Barycenter & Trans-Singularity EVaR | Noncommutative motive spectral triad $(\mathcal{A}, \mathcal{H}, \mathcal{D})$ Fisher-Rao manifold barycenter blending ($\mu_{\text{spectral\_triad}} = [1.50, 1.30, 1.25, 1.70]$) & 12th-cumulant Trans-Singularity EVaR bounds containing extreme heavy tails | M2 | ORIGINAL_REQUEST R2 / Explorer 2 Survey |
| F89.2 | Kerr Spacetime Ergosphere L3 & 99.8% ATS Preemption | Kerr spacetime ergosphere rotational queue acceleration, 99.8% dark ATS routing, 0.0001 maker floor, 99.9% anti-gaming MinQty, and $-0.98 \cdot \text{spread} \cdot (h - 0.12)$ preemptive tick shading | M3 | ORIGINAL_REQUEST R3 / Explorer 2 Survey |
| F90 | Phase 17 Quantitative Verification Engine | 5-market 15-metric benchmarking in `benchmark_phase17_quant_performance.py`, [표 1] 종합 지표, [표 2] 시장별 성과, [표 3] 팩터 기여도 3대 표준 표 산출, 3-path report synchronization, and test suite `tests/test_benchmark_phase17.py` | M4 | ORIGINAL_REQUEST R4 / Explorer 3 Survey |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Alpha Signal Specialist (R1) | F87, F88.1, F88.2 in `factor_suppression.py` and `ensemble_scorer.py`, `test_phase17_signal_enhancement.py` | Survey | DONE |
| M2 | Risk Allocation Specialist (R2) | F89.1 in `unified_portfolio_allocator.py`, `portfolio_allocator.py`, `test_phase17_risk_allocation.py` | Survey | DONE |
| M3 | Microstructure OMS Specialist (R3) | F89.2 in `fast_lob_engine.py`, `smart_order_router.py`, `oms_engine.py`, `test_phase17_microstructure_oms.py` | Survey | DONE |
| M4 | Quant Verification Specialist (R4) | F90 in `benchmark_phase17_quant_performance.py`, `test_benchmark_phase17.py`, 3 reports sync | M1, M2, M3 | DONE |
| M5 | Comprehensive Verification & Forensic Audit | Multi-agent Reviewers, Challengers, and Forensic Auditor verification across all 5 markets | M1, M2, M3, M4 | DONE |
