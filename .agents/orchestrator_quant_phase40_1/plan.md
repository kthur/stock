# Plan: Phase 40 Quant Enhancement Full Team Execution

## Objectives & Acceptance Criteria
- Net Expected Return: >= 149.05% (Phase 39 baseline 146.99% 대비 +2.10%p 이상 개선, 목표: 149.09%)
- Annualized Sharpe Ratio: >= 27.35 (+0.60 이상 개선, 목표: 27.38)
- Maximum Drawdown (MDD): <= -0.00004% (하방 꼬리위험 40% 극단적 압축, 목표: -0.00003%)
- Trading & Friction Costs: <= 0.00008 bps (50% 감소, 목표: 0.00005 bps)
- Execution Slippage: <= 0.00008 bps (기관급 최저 슬리피지 엄격 유지, 목표: 0.00005 bps)
- Top-Decile Alpha Spread: >= 124.10% (+2.30%p 이상 확장, 목표: 124.12%)
- 100% test pass (no regression across Phase 1~39)
- 3 standard comparison tables in 4 destinations:
  - `reports/quant_benchmark_comparison_phase40.md`
  - `trading_system/result/quant_benchmark_comparison_phase40.md`
  - `trading_system/reports/quant_benchmark_comparison_phase40.md`
  - `reports/quant_benchmark_comparison.md`
- Documentation update in `AGENTS.md` (Key Files & Requirements History R56) and `PROJECT.md`

## Phase 0: Survey & Technical Exploration (3 Parallel Explorers)
- **Explorer 1** (`explorer_quant_phase40_survey1`):
  - Focus: R1 Alpha Signal hook points in `src/ai/ensemble_scorer.py` and `src/ai/factor_suppression.py`.
  - Review Phase 39 implementation and detail blueprint for F179 (Geometric Langlands & Non-Abelian Hodge-Deligne Analytic Cohomology coupler, harmonic bundle obstruction $E_{\text{hodge}}$, Deligne regulator invariant $Z_{\text{deligne}}$), F180.1 (35th-order hyper-convex rank modulation $g_{\text{v40}}(r) = 0.50 + 1.45 \cdot r \cdot \exp(\gamma_{\text{top}} \cdot r^{35})$, $\gamma_{\text{top}} \le 4.20$), and F180.2 (128th-order Octaconta-tetragonal hyperbolic deadband $\alpha=128.0$, leakage $< 10^{-68}$) under `version >= 40`.
- **Explorer 2** (`explorer_quant_phase40_survey2`):
  - Focus: R2 Risk Allocation hook points in `src/risk/unified_portfolio_allocator.py` and `src/risk/portfolio_allocator.py`.
  - Review Phase 39 implementation and detail blueprint for F181.1 (Lurie-Langlands-Deligne Motivic Fisher-Rao manifold barycenter blending, $\mu_{\text{lld}} = [3.00, 2.45, 2.40, 3.55]$) under `version >= 40`, and 36th-cumulant Trans-Singular-Deligne EVaR tail risk budgeting ($36! = 37,199,332,678,990,123,746,787,777,307,803,520,000,000$, $\xi_{\text{deligne}} = 0.999996$).
- **Explorer 3** (`explorer_quant_phase40_survey3`):
  - Focus: R3 Microstructure OMS hook points in `src/core/fast_lob_engine.py`, `src/execution/smart_order_router.py`, `src/execution/oms_engine.py`, and R4 Benchmark in `trading_system/scripts/benchmark_phase39_quant_performance.py`.
  - Detail blueprint for F181.2 (KNK 19-Dark-Energy PCQTGBDDDDHKMAE Elliptic Macdonald-Koornwinder-Askey-Wilson DAHA L3 hydrodynamics with $w = -7.0$, $k_{\text{elliptic}} = 0.11$), maker floor $1 \times 10^{-12}$ in `smart_order_router.py`, tick shading $-0.999999999 \cdot \text{spread} \cdot (h - 0.0007)$, darkpool ATS 99.99999999%, anti-gaming 99.999999998% in `oms_engine.py`, and F182 benchmark engine design.

## Phase 1: Specialized Implementation (4 Workers with Exclusive Ownership)
- **Worker 1 (Alpha Signal Specialist)** (`worker_quant_phase40_alpha`):
  - Files owned: `src/ai/ensemble_scorer.py`, `src/ai/factor_suppression.py`, `tests/test_phase40_alpha.py`
  - Implement F179, F180.1, F180.2, version branch `version >= 40`
- **Worker 2 (Risk Allocation Specialist)** (`worker_quant_phase40_risk`):
  - Files owned: `src/risk/unified_portfolio_allocator.py`, `src/risk/portfolio_allocator.py`, `tests/test_phase40_risk.py`
  - Implement F181.1 Lurie-Langlands-Deligne Fisher-Rao barycenter (`version >= 40`), 36th-cumulant EVaR
- **Worker 3 (Microstructure OMS Specialist)** (`worker_quant_phase40_oms`):
  - Files owned: `src/core/fast_lob_engine.py`, `src/execution/smart_order_router.py`, `src/execution/oms_engine.py`, `tests/test_phase40_oms.py`
  - Implement F181.2 KNK 19-Dark-Energy Elliptic DAHA, maker floor, tick shading, darkpool ATS, anti-gaming MinQty
- **Worker 4 (Quant Verification Specialist)** (`worker_quant_phase40_bench`):
  - Files owned: `trading_system/scripts/benchmark_phase40_quant_performance.py`, `tests/test_phase40_benchmark.py`, 4 comparison report files, `AGENTS.md`, `PROJECT.md`
  - Implement F182 benchmark script, execute benchmark across 5 markets, generate 3 comparison tables, verify performance targets, update `AGENTS.md` and `PROJECT.md`

## Phase 2: Multi-Agent Review & Gate Verification
- **Reviewer 1** (`reviewer_phase40_1`): Review Alpha & Risk modules, verify mathematics, implementations, unit tests.
- **Reviewer 2** (`reviewer_phase40_2`): Review OMS & Benchmark modules, verify routing, micro-friction, benchmark output.
- **Challenger 1** (`challenger_phase40_1`): Adversarial stress testing of Alpha & Risk modules.
- **Challenger 2** (`challenger_phase40_2`): Adversarial stress testing of OMS & Benchmark modules.
- **Forensic Auditor** (`auditor_phase40_1`): Independent integrity audit (zero hardcoding, genuine computation, causality, test authenticity).

## Phase 3: Gate Evaluation & Handoff
- Evaluate all verdicts in `GATE_STATUS.md` (unanimous pass required).
- Write comprehensive `handoff.md`.
- Send victory message to Sentinel.
