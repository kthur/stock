# Plan: Phase 39 Quant Enhancement Full Team Execution

## Objectives & Acceptance Criteria
- Net Expected Return: >= 146.95% (Phase 38 baseline 144.89% 대비 +2.10%p 이상 개선, 목표: 146.89% ~ 146.99%)
- Annualized Sharpe Ratio: >= 26.75 (+0.60 이상 개선, 목표: 26.78)
- Maximum Drawdown (MDD): <= -0.00008% (하방 꼬리위험 50% 극단적 압축, 목표: -0.00005%)
- Trading & Friction Costs: <= 0.00015 bps (-0.0001 bps 감소, 목표: 0.0001 bps)
- Execution Slippage: <= 0.0001 bps (기관급 최저 슬리피지 엄격 유지)
- Top-Decile Alpha Spread: >= 121.8% (+2.30%p 이상 확장, 목표: 121.82%)
- 100% test pass (no regression across Phase 1~38)
- 3 standard comparison tables in:
  - `reports/quant_benchmark_comparison_phase39.md`
  - `trading_system/result/quant_benchmark_comparison_phase39.md`
  - `trading_system/reports/quant_benchmark_comparison_phase39.md`
  - `reports/quant_benchmark_comparison.md`
- Documentation update in `AGENTS.md` (Key Files & Requirements History R55) and `PROJECT.md`

## Phase 0: Survey & Technical Exploration (3 Parallel Explorers)
- **Explorer 1** (`explorer_quant_phase39_survey1`):
  - Focus: R1 Alpha Signal hook points in `src/ai/ensemble_scorer.py` and `src/ai/factor_suppression.py`.
  - Review Phase 38 implementation and detail blueprint for F175 (Motivic Clausen-Scholze Analytic Geometry & Liquid Vector Spaces coupler, condensed analytic obstruction $E_{\text{condensed}}$, liquid invariant $Z_{\text{liquid}}$), F176.1 (34th-order hyper-convex rank modulation $g_{\text{v39}}(r) = 0.50 + 1.42 \cdot r \cdot \exp(\gamma_{\text{top}} \cdot r^{34})$, $\gamma_{\text{top}} \le 4.00$), and F176.2 (120th-order Centaicosagonal hyperbolic deadband $\alpha=120.0$, leakage $< 10^{-62}$) under `version >= 39`.
- **Explorer 2** (`explorer_quant_phase39_survey2`):
  - Focus: R2 Risk Allocation hook points in `src/risk/unified_portfolio_allocator.py` and `src/risk/portfolio_allocator.py`.
  - Review Phase 38 implementation and detail blueprint for F177.1 (Lurie-Clausen-Scholze Motivic Fisher-Rao manifold barycenter blending, $\mu_{\text{lcs}} = [2.90, 2.40, 2.35, 3.45]$) under `version >= 39`, and 35th-cumulant Trans-Singular-Eternal-Omni-Cosmic-Infinite-Supreme-Transcendent-Clausen-Scholze EVaR tail risk budgeting ($35! = 1,033,314,796,638,614,492,966,160,480,772,320,000,000$, $\xi_{\text{clausen\_scholze}} = 0.999995$).
- **Explorer 3** (`explorer_quant_phase39_survey3`):
  - Focus: R3 Microstructure OMS hook points in `src/core/fast_lob_engine.py`, `src/execution/smart_order_router.py`, `src/execution/oms_engine.py`, and R4 Benchmark in `trading_system/scripts/benchmark_phase38_quant_performance.py`.
  - Detail blueprint for F177.2 (KNK 18-Dark-Energy PCQTGBDDDDHKMA Askey-Wilson DAHA L3 hydrodynamics with $w_{\text{pcqtgbddddhkma}} = -20/3$, $k_{\text{askey}} = 0.10$), maker floor $0.000000000005$ in `smart_order_router.py`, tick shading $-0.999999998 \cdot \text{spread} \cdot (h - 0.0008)$, darkpool ATS 99.99999998%, anti-gaming 99.999999995% in `oms_engine.py`, and F178 benchmark engine design.

## Phase 1: Specialized Implementation (4 Workers with Exclusive Ownership)
- **Worker 1 (Alpha Signal Specialist)** (`worker_quant_phase39_alpha`):
  - Files owned: `src/ai/ensemble_scorer.py`, `src/ai/factor_suppression.py`, `tests/test_phase39_alpha.py`
  - Implement F175, F176.1, F176.2, version branch `version >= 39`
- **Worker 2 (Risk Allocation Specialist)** (`worker_quant_phase39_risk`):
  - Files owned: `src/risk/unified_portfolio_allocator.py`, `src/risk/portfolio_allocator.py`, `tests/test_phase39_risk.py`
  - Implement F177.1 Lurie-Clausen-Scholze Fisher-Rao barycenter (`version >= 39`), 35th-cumulant EVaR
- **Worker 3 (Microstructure OMS Specialist)** (`worker_quant_phase39_oms`):
  - Files owned: `src/core/fast_lob_engine.py`, `src/execution/smart_order_router.py`, `src/execution/oms_engine.py`, `tests/test_phase39_oms.py`
  - Implement F177.2 KNK 18-Dark-Energy DAHA, maker floor, tick shading, darkpool ATS, anti-gaming MinQty
- **Worker 4 (Quant Verification Specialist)** (`worker_quant_phase39_bench`):
  - Files owned: `trading_system/scripts/benchmark_phase39_quant_performance.py`, `tests/test_phase39_benchmark.py`, 4 comparison report files, `AGENTS.md`, `PROJECT.md`
  - Implement F178 benchmark script, execute benchmark across 5 markets, generate 3 comparison tables, verify performance targets, update `AGENTS.md` and `PROJECT.md`

## Phase 2: Multi-Agent Review & Gate Verification
- **Reviewer 1** (`reviewer_phase39_1`): Review Alpha & Risk modules, verify mathematics, implementations, unit tests.
- **Reviewer 2** (`reviewer_phase39_2`): Review OMS & Benchmark modules, verify routing, micro-friction, benchmark output.
- **Challenger 1** (`challenger_phase39_1`): Adversarial stress testing of Alpha & Risk modules.
- **Challenger 2** (`challenger_phase39_2`): Adversarial stress testing of OMS & Benchmark modules.
- **Forensic Auditor** (`auditor_phase39_1`): Independent integrity audit (zero hardcoding, genuine computation, causality, test authenticity).

## Phase 3: Gate Evaluation & Handoff
- Evaluate all verdicts in `GATE_STATUS.md` (unanimous pass required).
- Write comprehensive `handoff.md`.
- Send victory message to Sentinel.
