# Plan: Phase 26 Quant Enhancement Full Team Execution

## Objectives & Acceptance Criteria
- Net Expected Return: >= 119.65% (Phase 25 baseline 117.59% 대비 +2.06%p 이상 개선)
- Annualized Sharpe Ratio: >= 18.95 (+0.57 이상)
- Maximum Drawdown (MDD): <= -0.011% (하방 꼬리위험 극단적 압축)
- Trading & Friction Costs: <= 0.010 bps (-0.002 bps 이하)
- Execution Slippage: <= 0.0005 bps
- Top-Decile Alpha Spread: >= 91.8% (+2.2%p 이상)
- 100% test pass (no regression, pytest suites)
- 3 standard comparison tables in `reports/quant_benchmark_comparison_phase26.md` and `trading_system/result/quant_benchmark_comparison_phase26.md`
- Documentation update in `AGENTS.md` (Key Files & Requirements History R42) and `PROJECT.md`

## Phase 0: Survey & Technical Exploration (3 Parallel Explorers)
- **Explorer 1** (`explorer_quant_phase26_survey1`):
  - Focus: R1 Alpha Signal hook points in `src/ai/ensemble_scorer.py` and `src/ai/factor_suppression.py`.
  - Review Phase 25 implementation (F119 Non-Abelian Hodge, F120.1 20th-order modulation, F120.2 64th-order deadband).
  - Detail blueprint for F123 (Perfectoid Shimura Variety & Mochizuki IUT Reconstruction coupler, Hodge-Tate filtration obstruction $E_{\text{shimura}}$, Mochizuki theta-link invariant $Z_{\text{mochizuki}}$), F124.1 (21st-order hyperconvex rank modulation $g_{\text{v26}}(r) = 0.50 + 1.16 \cdot r \cdot \exp(\gamma_{\text{top}} \cdot r^{21})$, $\gamma_{\text{top}} \le 2.70$), and F124.2 (68th-order Hexaoctagonal hyperbolic deadband $\alpha=68.0$, leakage $< 10^{-36}$).
- **Explorer 2** (`explorer_quant_phase26_survey2`):
  - Focus: R2 Risk Allocation hook points in `src/risk/unified_portfolio_allocator.py` and `src/risk/portfolio_allocator.py`.
  - Review Phase 25 implementation (F121.1 Lurie Non-Abelian Hodge barycenter, 21st-cumulant EVaR).
  - Detail blueprint for F125.1 (Lurie Mochizuki IUT Fisher-Rao manifold barycenter blending, $\mu_{\text{mochizuki}} = [2.25, 1.75, 1.70, 2.80]$) under `version >= 26`, and 22nd-cumulant Trans-Singular-Hyper EVaR ($22! = 1,124,000,727,777,607,680,000$, $\xi_{\text{singular\_hyper}} = 0.90$).
- **Explorer 3** (`explorer_quant_phase26_survey3`):
  - Focus: R3 Microstructure OMS hook points in `src/core/fast_lob_engine.py`, `src/execution/smart_order_router.py`, `src/execution/oms_engine.py`, and R4 Benchmark in `trading_system/scripts/benchmark_phase25_quant_performance.py`.
  - Detail blueprint for F125.2 (Kerr-Newman-Kiselev Chameleon 5-dark-energy $w_{\text{chameleon}} = -7/3$ L3 hydrodynamics), maker floor $0.0000001$ in `smart_order_router.py`, tick shading $-0.99995 \cdot \text{spread} \cdot (h - 0.020)$, darkpool ATS 99.9995%, anti-gaming 99.9999% in `oms_engine.py`, and F126 benchmark engine design.

## Phase 1: Specialized Implementation (4 Workers with Exclusive Ownership)
- **Worker 1 (Alpha Signal Specialist)** (`worker_quant_phase26_alpha`):
  - Files owned: `src/ai/ensemble_scorer.py`, `src/ai/factor_suppression.py`, `tests/test_phase26_alpha.py`
  - Implement F123, F124.1, F124.2, version branch `version >= 26`
- **Worker 2 (Risk Allocation Specialist)** (`worker_quant_phase26_risk`):
  - Files owned: `src/risk/unified_portfolio_allocator.py`, `src/risk/portfolio_allocator.py`, `tests/test_phase26_risk.py`
  - Implement F125.1 Lurie Mochizuki IUT Fisher-Rao barycenter (`version >= 26`), 22nd-cumulant Trans-Singular-Hyper EVaR
- **Worker 3 (Microstructure OMS Specialist)** (`worker_quant_phase26_oms`):
  - Files owned: `src/core/fast_lob_engine.py`, `src/execution/smart_order_router.py`, `src/execution/oms_engine.py`, `tests/test_phase26_oms.py`
  - Implement F125.2 KNK Chameleon 5-dark-energy, maker floor, tick shading, darkpool ATS, anti-gaming MinQty
- **Worker 4 (Quant Verification Specialist)** (`worker_quant_phase26_bench`):
  - Files owned: `trading_system/scripts/benchmark_phase26_quant_performance.py`, `tests/test_phase26_benchmark.py`, `reports/quant_benchmark_comparison_phase26.md`, `trading_system/result/quant_benchmark_comparison_phase26.md`, `reports/quant_benchmark_comparison.md`, `AGENTS.md`, `PROJECT.md`
  - Implement F126 benchmark script, execute benchmark across 5 markets, generate 3 comparison tables, verify performance targets, update `AGENTS.md` and `PROJECT.md`

## Phase 2: Multi-Agent Review & Gate Verification
- **Reviewer 1** (`reviewer_phase26_1`): Review Alpha & Risk modules, verify mathematics, implementations, unit tests.
- **Reviewer 2** (`reviewer_phase26_2`): Review OMS & Benchmark modules, verify routing, micro-friction, benchmark output.
- **Challenger 1** (`challenger_phase26_1`): Adversarial stress testing of Alpha & Risk modules (extreme values, NaNs, edge cases).
- **Challenger 2** (`challenger_phase26_2`): Adversarial stress testing of OMS & Benchmark modules (high volatility, order book inversion, illiquid conditions).
- **Forensic Auditor** (`auditor_phase26_1`): Independent integrity audit (zero hardcoding, genuine computation, causality, test authenticity).

## Phase 3: Gate Evaluation & Handoff
- Evaluate all verdicts in `GATE_STATUS.md` (unanimous pass required).
- Write comprehensive `handoff.md`.
- Send victory message to Sentinel.
