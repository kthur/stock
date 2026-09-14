# Plan: Phase 41 Quant Enhancement Full Team Execution

## Objectives & Acceptance Criteria
- Net Expected Return: >= 151.15% (Phase 40 baseline 149.09% 대비 +2.10%p 이상 개선, 목표: 151.19%)
- Annualized Sharpe Ratio: >= 27.95 (+0.60 이상 개선, 목표: 27.98)
- Maximum Drawdown (MDD): <= -0.00002% (하방 꼬리위험 33.3% 극단적 압축, 목표: -0.00002%)
- Trading & Friction Costs: <= 0.00004 bps (목표: 0.00003 bps)
- Execution Slippage: <= 0.00004 bps (기관급 최저 슬리피지 엄격 유지, 목표: 0.00003 bps)
- Top-Decile Alpha Spread: >= 126.40% (+2.30%p 이상 확장, 목표: 126.42%)
- 100% test pass (no regression across Phase 1~40)
- 3 standard comparison tables in 4 destinations:
  - `reports/quant_benchmark_comparison_phase41.md`
  - `trading_system/result/quant_benchmark_comparison_phase41.md`
  - `trading_system/reports/quant_benchmark_comparison_phase41.md`
  - `reports/quant_benchmark_comparison.md`
- Documentation update in `AGENTS.md` (Key Files & Requirements History R57) and `PROJECT.md`

## Phase 0: Survey & Technical Exploration (3 Parallel Explorers)
- **Explorer 1** (`explorer_quant_phase41_survey1`):
  - Focus: R1 Alpha Signal hook points in `src/ai/ensemble_scorer.py` and `src/ai/factor_suppression.py`.
  - Review Phase 40 implementation and establish blueprint for:
    - F183: Drinfeld-Lafforgue & Fargues-Fontaine Curve Analytic Cohomology coupler, Artin stack obstruction complex $E_{\text{fargues}}$, Fargues-Fontaine curve factor invariant $Z_{\text{fontaine}}$.
    - F184.1: 36th-order ultra-convex rank modulation $g_{\text{v41}}(r) = 0.50 + 1.48 \cdot r \cdot \exp(\gamma_{\text{top}} \cdot r^{36})$, adaptive $\gamma_{\text{top}} \le 4.40$.
    - F184.2: 136th-order Centatriacontaoctagonal hyperbolic deadband ($\alpha=136.0$, noise leakage $< 10^{-74}$).
    - Version branch: `version >= 41`.
- **Explorer 2** (`explorer_quant_phase41_survey2`):
  - Focus: R2 Risk Allocation hook points in `src/risk/unified_portfolio_allocator.py` and `src/risk/portfolio_allocator.py`.
  - Review Phase 40 implementation and establish blueprint for:
    - F185.1: Lurie-Fargues-Fontaine Motivic Fisher-Rao manifold barycenter blending ($\mu_{\text{lff}} = [3.10, 2.50, 2.45, 3.65]$) under `version >= 41`.
    - 37th-cumulant Trans-Singular-Eternal-Omni-Cosmic-Infinite-Supreme-Transcendent-Clausen-Scholze-Deligne-Fargues EVaR tail risk budgeting ($37! = 1,376,375,309,122,634,578,631,147,760,388,730,240,000,000$, $\xi_{\text{fargues}} = 0.999997$).
- **Explorer 3** (`explorer_quant_phase41_survey3`):
  - Focus: R3 Microstructure OMS hook points in `src/core/fast_lob_engine.py`, `src/execution/smart_order_router.py`, `src/execution/oms_engine.py`, and R4 Benchmark in `trading_system/scripts/benchmark_phase40_quant_performance.py`.
  - Establish blueprint for:
    - F185.2: KNK 20-Dark-Energy PCQTGBDDDDHKMAEE Elliptic-Trigonometric Macdonald-Koornwinder-Askey-Wilson DAHA L3 hydrodynamics with $w = -22/3$, $k_{\text{elliptic\_trig}} = 0.12$.
    - Maker floor $1 \times 10^{-13}$ in `smart_order_router.py`.
    - Preemptive tick shading $-0.9999999995 \cdot \text{spread} \cdot (h - 0.0006)$, darkpool ATS routing 99.999999995%, Anti-Gaming MinQty 99.999999999% in `oms_engine.py`.
    - F186 benchmark engine design based on Phase 40 benchmark script.

## Phase 1: Specialized Implementation (4 Workers with Exclusive Ownership)
- **Worker 1 (Alpha Signal Specialist)** (`worker_quant_phase41_alpha`):
  - Files owned: `src/ai/ensemble_scorer.py`, `src/ai/factor_suppression.py`, `tests/test_phase41_alpha.py`
  - Implement F183, F184.1, F184.2, version branch `version >= 41`
- **Worker 2 (Risk Allocation Specialist)** (`worker_quant_phase41_risk`):
  - Files owned: `src/risk/unified_portfolio_allocator.py`, `src/risk/portfolio_allocator.py`, `tests/test_phase41_risk.py`
  - Implement F185.1 Lurie-Fargues-Fontaine Fisher-Rao barycenter (`version >= 41`), 37th-cumulant EVaR
- **Worker 3 (Microstructure OMS Specialist)** (`worker_quant_phase41_oms`):
  - Files owned: `src/core/fast_lob_engine.py`, `src/execution/smart_order_router.py`, `src/execution/oms_engine.py`, `tests/test_phase41_oms.py`
  - Implement F185.2 KNK 20-Dark-Energy Elliptic-Trigonometric DAHA, maker floor, tick shading, darkpool ATS, anti-gaming MinQty
- **Worker 4 (Quant Verification Specialist)** (`worker_quant_phase41_bench`):
  - Files owned: `trading_system/scripts/benchmark_phase41_quant_performance.py`, `tests/test_phase41_benchmark.py`, 4 comparison report files, `AGENTS.md`, `PROJECT.md`
  - Implement F186 benchmark script, execute benchmark across 5 markets, generate 3 comparison tables, verify performance targets, update `AGENTS.md` and `PROJECT.md`

## Phase 2: Multi-Agent Review & Gate Verification
- **Reviewer 1** (`reviewer_phase41_1`): Review Alpha & Risk modules, verify mathematics, implementations, unit tests.
- **Reviewer 2** (`reviewer_phase41_2`): Review OMS & Benchmark modules, verify routing, micro-friction, benchmark output.
- **Challenger 1** (`challenger_phase41_1`): Adversarial stress testing of Alpha & Risk modules.
- **Challenger 2** (`challenger_phase41_2`): Adversarial stress testing of OMS & Benchmark modules.
- **Forensic Auditor** (`auditor_phase41_1`): Independent integrity audit (zero hardcoding, genuine computation, causality, test authenticity).

## Phase 3: Gate Evaluation & Handoff
- Evaluate all verdicts in `GATE_STATUS.md` (unanimous pass required).
- Write comprehensive `handoff.md`.
- Send victory message to Sentinel.
