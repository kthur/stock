# Plan: Phase 24 Quant Enhancement Full Team Execution

## Objectives & Acceptance Criteria
- Net Expected Return: >= 115.45% (Phase 23 baseline 113.38% 대비 +2.07%p 이상 개선)
- Annualized Sharpe Ratio: >= 17.75 (+0.57 이상)
- Maximum Drawdown (MDD): <= -0.018%
- Trading & Friction Costs: <= 0.018 bps (-0.006 bps 이하)
- Execution Slippage: <= 0.0010 bps
- Top-Decile Alpha Spread: >= 87.2% (+2.3%p 이상)
- 100% test pass (no regression, pytest suites)
- 3 standard comparison tables in `reports/quant_benchmark_comparison_phase24.md` and `trading_system/result/quant_benchmark_comparison_phase24.md`
- Documentation update in `AGENTS.md` (Key Files & Requirements History R40) and `PROJECT.md`

## Phase 0: Survey & Technical Exploration (3 Parallel Explorers)
- **Explorer 1** (`explorer_quant_phase24_survey1`): Survey R1 Alpha Signal hook points in `src/ai/ensemble_scorer.py` and `src/ai/factor_suppression.py`, Phase 23 Langlands implementation (F111, F112.1, F112.2), and design F115, F116.1, F116.2.
- **Explorer 2** (`explorer_quant_phase24_survey2`): Survey R2 Risk Allocation hook points in `src/risk/unified_portfolio_allocator.py` and `src/risk/portfolio_allocator.py`, Phase 23 Fisher-Rao barycenter (F113.1) and 19th-cumulant EVaR, and design F117.1, F117.2.
- **Explorer 3** (`explorer_quant_phase24_survey3`): Survey R3 Microstructure OMS hook points in `src/core/fast_lob_engine.py`, `src/execution/smart_order_router.py`, `src/execution/oms_engine.py`, and R4 Benchmark engine in `trading_system/scripts/benchmark_phase23_quant_performance.py`.

## Phase 1: Specialized Implementation (4 Workers with Exclusive Ownership)
- **Worker 1 (Alpha Signal Specialist)** (`worker_quant_phase24_alpha`):
  - Files owned: `src/ai/ensemble_scorer.py`, `src/ai/factor_suppression.py`, `tests/test_phase24_alpha.py`
  - Implement F115 Derived Arithmetic Topology & Étale-Motivic Spectral Homotopy Coupler
  - Implement F116.1 19th-order hyperconvex rank modulation $g_{\text{v24}}(r)$
  - Implement F116.2 60th-order Hexacontagonal hyperbolic deadband ($\alpha=60.0$)
  - Version branch `version >= 24`
- **Worker 2 (Risk Allocation Specialist)** (`worker_quant_phase24_risk`):
  - Files owned: `src/risk/unified_portfolio_allocator.py`, `src/risk/portfolio_allocator.py`, `tests/test_phase24_risk.py`
  - Implement F117.1 Lurie Arithmetic Spectral Fisher-Rao manifold barycenter blending ($\mu_{\text{arithmetic}} = [2.15, 1.65, 1.60, 2.70]$) under `version >= 24`
  - Implement F117.2 20th-order cumulant Trans-Super-Hyper EVaR ($20! = 2,432,902,008,176,640,000$, $\xi_{\text{super\_hyper}} = 0.80$)
- **Worker 3 (Microstructure OMS Specialist)** (`worker_quant_phase24_oms`):
  - Files owned: `src/core/fast_lob_engine.py`, `src/execution/smart_order_router.py`, `src/execution/oms_engine.py`, `tests/test_phase24_oms.py`
  - Implement F117.2 Kerr-Newman-Kiselev Quintessence-Phantom-Tachyon 3-dark-energy ($w_{\text{tachyon}} = -5/3$) L3 hydrodynamics
  - Implement maker floor $0.0000005$ in `smart_order_router.py`
  - Implement tick shading $-0.9998 \cdot \text{spread} \cdot (h - 0.030)$, darkpool ATS 99.998%, anti-gaming 99.9995% in `oms_engine.py`
- **Worker 4 (Quant Verification Specialist)** (`worker_quant_phase24_bench`):
  - Files owned: `trading_system/scripts/benchmark_phase24_quant_performance.py`, `tests/test_phase24_benchmark.py`, `reports/quant_benchmark_comparison_phase24.md`, `trading_system/result/quant_benchmark_comparison_phase24.md`, `reports/quant_benchmark_comparison.md`, `AGENTS.md`, `PROJECT.md`
  - Implement F118 benchmark script, execute 5-market quant benchmark, generate 3 comparison tables
  - Verify all 6 performance targets pass
  - Update `AGENTS.md` and `PROJECT.md`

## Phase 2: Multi-Agent Review & Gate Verification
- **Reviewer 1** (`reviewer_phase24_1`): Review Alpha & Risk modules, verify math, implementation, unit tests.
- **Reviewer 2** (`reviewer_phase24_2`): Review OMS & Benchmark modules, verify routing, micro-friction, benchmark output.
- **Challenger 1** (`challenger_phase24_1`): Adversarial stress testing of Alpha & Risk modules (extreme values, NaNs, edge cases).
- **Challenger 2** (`challenger_phase24_2`): Adversarial stress testing of OMS & Benchmark modules (high volatility, order book inversion, illiquid conditions).
- **Forensic Auditor** (`auditor_phase24_1`): Independent integrity audit (zero hardcoding, genuine computation, causality, test authenticity).

## Phase 3: Gate Evaluation & Handoff
- Evaluate all verdicts in `GATE_STATUS.md` (unanimous pass required).
- Write comprehensive `handoff.md`.
- Send victory message to Sentinel.
