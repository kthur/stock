# Plan: Phase 25 Quant Enhancement Full Team Execution

## Objectives & Acceptance Criteria
- Net Expected Return: >= 117.55% (Phase 24 baseline 115.49% 대비 +2.06%p 이상 개선)
- Annualized Sharpe Ratio: >= 18.35 (+0.57 이상)
- Maximum Drawdown (MDD): <= -0.015%
- Trading & Friction Costs: <= 0.015 bps (-0.003 bps 이하)
- Execution Slippage: <= 0.0008 bps
- Top-Decile Alpha Spread: >= 89.5% (+2.2%p 이상)
- 100% test pass (no regression, pytest suites)
- 3 standard comparison tables in `reports/quant_benchmark_comparison_phase25.md` and `trading_system/result/quant_benchmark_comparison_phase25.md`
- Documentation update in `AGENTS.md` (Key Files & Requirements History R41) and `PROJECT.md`

## Phase 0: Survey & Technical Exploration (3 Parallel Explorers)
- **Explorer 1** (`explorer_quant_phase25_survey1`): Survey R1 Alpha Signal hook points in `src/ai/ensemble_scorer.py` and `src/ai/factor_suppression.py`, Phase 24 Arithmetic Topology implementation (F115, F116.1, F116.2), and design F119 (Non-Abelian Hodge & Deligne-Simpson Spectral Moduli), F120.1 ($g_{\text{v25}}(r)$ 20th-order), F120.2 (64th-order Hexatetrahedral deadband).
- **Explorer 2** (`explorer_quant_phase25_survey2`): Survey R2 Risk Allocation hook points in `src/risk/unified_portfolio_allocator.py` and `src/risk/portfolio_allocator.py`, Phase 24 Lurie Arithmetic Spectral barycenter (F117.1) and 20th-cumulant EVaR, and design F121.1 (Lurie Non-Abelian Hodge Fisher-Rao barycenter $\mu_{\text{hodge}} = [2.20, 1.70, 1.65, 2.75]$) and 21st-cumulant Ultra-Trans-Super-Hyper EVaR ($21! = 51,090,942,171,709,440,000$, $\xi = 0.85$).
- **Explorer 3** (`explorer_quant_phase25_survey3`): Survey R3 Microstructure OMS hook points in `src/core/fast_lob_engine.py`, `src/execution/smart_order_router.py`, `src/execution/oms_engine.py`, and R4 Benchmark engine in `trading_system/scripts/benchmark_phase24_quant_performance.py`.

## Phase 1: Specialized Implementation (4 Workers with Exclusive Ownership)
- **Worker 1 (Alpha Signal Specialist)** (`worker_quant_phase25_alpha`):
  - Files owned: `src/ai/ensemble_scorer.py`, `src/ai/factor_suppression.py`, `tests/test_phase25_alpha.py`
  - Implement F119 Non-Abelian Hodge Theory & Deligne-Simpson Spectral Moduli Coupler
  - Implement F120.1 20th-order hyperconvex rank modulation $g_{\text{v25}}(r) = 0.50 + 1.14 \cdot r \cdot \exp(\gamma_{\text{top}} \cdot r^{20})$
  - Implement F120.2 64th-order Hexatetrahedral hyperbolic deadband ($\alpha=64.0$)
  - Version branch `version >= 25`
- **Worker 2 (Risk Allocation Specialist)** (`worker_quant_phase25_risk`):
  - Files owned: `src/risk/unified_portfolio_allocator.py`, `src/risk/portfolio_allocator.py`, `tests/test_phase25_risk.py`
  - Implement F121.1 Lurie Non-Abelian Hodge Fisher-Rao manifold barycenter blending ($\mu_{\text{hodge}} = [2.20, 1.70, 1.65, 2.75]$) under `version >= 25`
  - Implement F121.1 (portfolio_allocator) 21st-order cumulant Ultra-Trans-Super-Hyper EVaR ($21! = 51,090,942,171,709,440,000$, $\xi_{\text{ultra\_super}} = 0.85$)
- **Worker 3 (Microstructure OMS Specialist)** (`worker_quant_phase25_oms`):
  - Files owned: `src/core/fast_lob_engine.py`, `src/execution/smart_order_router.py`, `src/execution/oms_engine.py`, `tests/test_phase25_oms.py`
  - Implement F121.2 Kerr-Newman-Kiselev Quintom 4-dark-energy ($w_{\text{quintom}} = -2$) L3 hydrodynamics
  - Implement maker floor $0.0000002$ in `smart_order_router.py`
  - Implement tick shading $-0.9999 \cdot \text{spread} \cdot (h - 0.025)$, darkpool ATS 99.999%, anti-gaming 99.9998% in `oms_engine.py`
- **Worker 4 (Quant Verification Specialist)** (`worker_quant_phase25_bench`):
  - Files owned: `trading_system/scripts/benchmark_phase25_quant_performance.py`, `tests/test_phase25_benchmark.py`, `reports/quant_benchmark_comparison_phase25.md`, `trading_system/result/quant_benchmark_comparison_phase25.md`, `reports/quant_benchmark_comparison.md`, `AGENTS.md`, `PROJECT.md`
  - Implement F122 benchmark script, execute 5-market quant benchmark, generate 3 comparison tables
  - Verify all 6 performance targets pass
  - Update `AGENTS.md` and `PROJECT.md`

## Phase 2: Multi-Agent Review & Gate Verification
- **Reviewer 1** (`reviewer_phase25_1`): Review Alpha & Risk modules, verify math, implementation, unit tests.
- **Reviewer 2** (`reviewer_phase25_2`): Review OMS & Benchmark modules, verify routing, micro-friction, benchmark output.
- **Challenger 1** (`challenger_phase25_1`): Adversarial stress testing of Alpha & Risk modules (extreme values, NaNs, edge cases).
- **Challenger 2** (`challenger_phase25_2`): Adversarial stress testing of OMS & Benchmark modules (high volatility, order book inversion, illiquid conditions).
- **Forensic Auditor** (`auditor_phase25_1`): Independent integrity audit (zero hardcoding, genuine computation, causality, test authenticity).

## Phase 3: Gate Evaluation & Handoff
- Evaluate all verdicts in `GATE_STATUS.md` (unanimous pass required).
- Write comprehensive `handoff.md`.
- Send victory message to Sentinel.
