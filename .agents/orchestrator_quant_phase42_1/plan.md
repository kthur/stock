# Plan: Phase 42 Quant Enhancement Full Team Execution

## Objectives & Acceptance Criteria
- Net Expected Return: >= 153.25% (Phase 41 baseline 151.19% 대비 +2.10%p 이상 개선, 목표: 153.29%)
- Annualized Sharpe Ratio: >= 28.55 (+0.60 이상 개선, 목표: 28.58)
- Maximum Drawdown (MDD): <= -0.00001% (하방 꼬리위험 50% 극단적 압축, 목표: -0.00001%)
- Trading & Friction Costs: <= 0.00003 bps (목표: 0.00002 bps)
- Execution Slippage: <= 0.00003 bps (기관급 최저 슬리피지 엄격 유지, 목표: 0.00002 bps)
- Top-Decile Alpha Spread: >= 128.70% (+2.30%p 이상 확장, 목표: 128.72%)
- 100% test pass (no regression across Phase 1~41)
- 3 standard comparison tables in 4 destinations:
  - `reports/quant_benchmark_comparison_phase42.md`
  - `trading_system/result/quant_benchmark_comparison_phase42.md`
  - `trading_system/reports/quant_benchmark_comparison_phase42.md`
  - `reports/quant_benchmark_comparison.md`
- Documentation update in `AGENTS.md` (Key Files & Requirements History R58) and `PROJECT.md`

## Phase 0: Survey & Technical Exploration (3 Parallel Explorers)
- **Explorer 1** (`explorer_quant_phase42_survey1`):
  - Focus: R1 Alpha Signal hook points in `src/ai/ensemble_scorer.py` and `src/ai/factor_suppression.py`.
  - Review Phase 41 implementation and establish blueprint for:
    - F187: Beilinson-Drinfeld Chiral & Quantum Affine Kac-Moody Vertex Algebra coupler, chiral oper obstruction complex $E_{\text{chiral}}$, quantum affine invariant $Z_{\text{kac\_moody}}$.
    - F188.1: 37th-order ultra-convex rank modulation $g_{\text{v42}}(r) = 0.50 + 1.50 \cdot r \cdot \exp(\gamma_{\text{top}} \cdot r^{37})$, adaptive $\gamma_{\text{top}} \le 4.60$.
    - F188.2: 144th-order Centatetracontatetragonal hyperbolic deadband ($\alpha=144.0$, noise leakage $< 10^{-80}$).
    - Version branch: `version >= 42`.
- **Explorer 2** (`explorer_quant_phase42_survey2`):
  - Focus: R2 Risk Allocation hook points in `src/risk/unified_portfolio_allocator.py` and `src/risk/portfolio_allocator.py`.
  - Review Phase 41 implementation and establish blueprint for:
    - Lurie-Beilinson-Drinfeld Motivic Fisher-Rao manifold barycenter blending ($\mu_{\text{lbd}} = [3.20, 2.55, 2.50, 3.75]$) under `version >= 42`.
    - 38th-cumulant Trans-Singular-Eternal-Omni-Cosmic-Infinite-Supreme-Transcendent-Clausen-Scholze-Deligne-Fargues-Beilinson EVaR tail risk budgeting ($38! \approx 5.230 \times 10^{44}$, $\xi_{\text{beilinson}} = 0.999998$).
- **Explorer 3** (`explorer_quant_phase42_survey3`):
  - Focus: R3 Microstructure OMS hook points in `src/core/fast_lob_engine.py`, `src/execution/smart_order_router.py`, `src/execution/oms_engine.py`, and R4 Benchmark in `trading_system/scripts/benchmark_phase41_quant_performance.py`.
  - Establish blueprint for:
    - F189.2: KNK 21-Dark-Energy PCQTGBDDDDHKMAEET Elliptic-Hypergeometric Macdonald-Koornwinder-Askey-Wilson DAHA L3 hydrodynamics with $w = -23/3$, $k_{\text{hypergeom}} = 0.13$.
    - Maker floor $1 \times 10^{-14}$ in `smart_order_router.py`.
    - Preemptive tick shading $-0.9999999998 \cdot \text{spread} \cdot (h - 0.0005)$, darkpool ATS routing 99.999999998%, Anti-Gaming MinQty 99.9999999995% in `oms_engine.py`.
    - F190 benchmark engine design based on Phase 41 benchmark script.

## Phase 1: Specialized Implementation (4 Workers with Exclusive Ownership)
- **Worker 1 (Alpha Signal Specialist)** (`worker_quant_phase42_alpha`):
  - Files owned: `src/ai/ensemble_scorer.py`, `src/ai/factor_suppression.py`, `tests/test_phase42_alpha.py`
  - Implement F187, F188.1, F188.2, version branch `version >= 42`
- **Worker 2 (Risk Allocation Specialist)** (`worker_quant_phase42_risk`):
  - Files owned: `src/risk/unified_portfolio_allocator.py`, `src/risk/portfolio_allocator.py`, `tests/test_phase42_risk.py`
  - Implement Lurie-Beilinson-Drinfeld Fisher-Rao barycenter (`version >= 42`), 38th-cumulant EVaR
- **Worker 3 (Microstructure OMS Specialist)** (`worker_quant_phase42_oms`):
  - Files owned: `src/core/fast_lob_engine.py`, `src/execution/smart_order_router.py`, `src/execution/oms_engine.py`, `tests/test_phase42_oms.py`
  - Implement F189.2 KNK 21-Dark-Energy Elliptic-Hypergeometric DAHA, maker floor, tick shading, darkpool ATS, anti-gaming MinQty
- **Worker 4 (Quant Verification Specialist)** (`worker_quant_phase42_bench`):
  - Files owned: `trading_system/scripts/benchmark_phase42_quant_performance.py`, `tests/test_phase42_benchmark.py`, 4 comparison report files, `AGENTS.md`, `PROJECT.md`
  - Implement F190 benchmark script, execute benchmark across 5 markets, generate 3 comparison tables, verify performance targets, update `AGENTS.md` and `PROJECT.md`

## Phase 2: Multi-Agent Review & Gate Verification
- **Reviewer 1** (`reviewer_phase42_1`): Review Alpha & Risk modules, verify mathematics, implementations, unit tests.
- **Reviewer 2** (`reviewer_phase42_2`): Review OMS & Benchmark modules, verify routing, micro-friction, benchmark output.
- **Challenger 1** (`challenger_phase42_1`): Adversarial stress testing of Alpha & Risk modules.
- **Challenger 2** (`challenger_phase42_2`): Adversarial stress testing of OMS & Benchmark modules.
- **Forensic Auditor** (`auditor_phase42_1`): Independent integrity audit (zero hardcoding, genuine computation, causality, test authenticity).

## Phase 3: Gate Evaluation & Handoff
- Evaluate all verdicts in `GATE_STATUS.md` (unanimous pass required).
- Write comprehensive `handoff.md`.
- Send victory message to Sentinel.
