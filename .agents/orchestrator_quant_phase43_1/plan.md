# Plan: Phase 43 Quant Enhancement Full Team Execution

## Objectives & Acceptance Criteria
- Net Expected Return: >= 155.35% (Phase 42 baseline 153.29% 대비 +2.10%p 이상 개선, 목표: 155.39%)
- Annualized Sharpe Ratio: >= 29.15 (+0.60 이상 개선, 목표: 29.18)
- Maximum Drawdown (MDD): <= -0.00001% (극단 꼬리위험 억제 지속, 목표: -0.00001%)
- Trading & Friction Costs: <= 0.00002 bps (50% 추가 절감, 목표: 0.00001 bps)
- Execution Slippage: <= 0.00002 bps (기관급 극초미세 슬리피지 엄격 유지, 목표: 0.00001 bps)
- Top-Decile Alpha Spread: >= 131.00% (+2.30%p 이상 확장, 목표: 131.02%)
- 100% test pass (no regression across Phase 1~42)
- 3 standard comparison tables in 4 destinations:
  - `reports/quant_benchmark_comparison_phase43.md`
  - `trading_system/result/quant_benchmark_comparison_phase43.md`
  - `trading_system/reports/quant_benchmark_comparison_phase43.md`
  - `reports/quant_benchmark_comparison.md`
- Documentation updates:
  - `AGENTS.md` Key Files table (`benchmark_phase43_quant_performance.py`) & Requirements History (R59)
  - `PROJECT.md` Phase 43 addition

## Phase 0: Survey & Technical Exploration (3 Parallel Explorers)
- **Explorer 1** (`explorer_quant_phase43_survey1`):
  - Focus: R1 Alpha Signal hook points in `src/ai/ensemble_scorer.py` and `src/ai/factor_suppression.py`.
  - Review Phase 42 implementation (F187, F188.1, F188.2) and map:
    - F191: Quantum Langlands Duality & Affine W-Algebra Chiral Oper Homology coupler, $E_{\text{w\_algebra}}$, $Z_{\text{quant\_langlands}}$, $\kappa_{\text{w\_alg}}=7.50$.
    - F192.1: 38th-order ultra-convex rank modulation $g_{\text{v43}}(r) = 0.50 + 1.52 \cdot r \cdot \exp(\gamma_{\text{top}} \cdot r^{38})$, adaptive $\gamma_{\text{top}} \le 4.70$.
    - F192.2: 152th-order Centapentacontaduo-gonal hyperbolic deadband ($\alpha=152.0$, noise leakage $< 10^{-84}$).
    - Version branch: `version >= 43`.
- **Explorer 2** (`explorer_quant_phase43_survey2`):
  - Focus: R2 Risk Allocation hook points in `src/risk/unified_portfolio_allocator.py` and `src/risk/portfolio_allocator.py`.
  - Review Phase 42 implementation and map:
    - F193.1: Lurie-W-Algebra Motivic Fisher-Rao manifold barycenter blending ($\mu_{\text{lwa}} = [3.30, 2.60, 2.55, 3.85]$) under `version >= 43`.
    - 39th-cumulant Trans-Singular-Eternal-Omni-Cosmic-Infinite-Supreme-Transcendent-Clausen-Scholze-Deligne-Beilinson-W-Algebra EVaR tail risk budgeting ($39! \approx 2.040 \times 10^{46}$, $\xi_{\text{w\_alg}} = 0.999999$).
- **Explorer 3** (`explorer_quant_phase43_survey3`):
  - Focus: R3 Microstructure OMS hook points in `src/core/fast_lob_engine.py`, `src/execution/smart_order_router.py`, `src/execution/oms_engine.py`, and R4 Benchmark in `trading_system/scripts/benchmark_phase42_quant_performance.py`.
  - Map:
    - F193.2: KNK 22-Dark-Energy PCQTGBDDDDHKMAEETU Elliptic-Hypergeometric-Askey-Wilson ($w = -24/3 = -8$, $k_{\text{daha}} = 0.14$) DAHA L3 hydrodynamics.
    - Maker floor $1 \times 10^{-15}$ in `smart_order_router.py`.
    - Preemptive tick shading $-0.9999999999 \cdot \text{spread} \cdot (h - 0.0004)$, darkpool ATS routing 99.999999999%, Anti-Gaming MinQty 99.9999999998% in `oms_engine.py`.
    - F194 benchmark script structure based on Phase 42 script.

## Phase 1: Specialized Implementation (4 Workers with Exclusive Ownership)
- **Worker 1 (Alpha Signal Specialist)** (`worker_quant_phase43_alpha`):
  - Files owned: `src/ai/ensemble_scorer.py`, `src/ai/factor_suppression.py`, `tests/test_phase43_alpha.py`
  - Implement F191, F192.1, F192.2, version branch `version >= 43`
- **Worker 2 (Risk Allocation Specialist)** (`worker_quant_phase43_risk`):
  - Files owned: `src/risk/unified_portfolio_allocator.py`, `src/risk/portfolio_allocator.py`, `tests/test_phase43_risk.py`
  - Implement Lurie-W-Algebra Fisher-Rao barycenter (`version >= 43`), 39th-cumulant EVaR
- **Worker 3 (Microstructure OMS Specialist)** (`worker_quant_phase43_oms`):
  - Files owned: `src/core/fast_lob_engine.py`, `src/execution/smart_order_router.py`, `src/execution/oms_engine.py`, `tests/test_phase43_oms.py`
  - Implement F193.2 KNK 22-Dark-Energy DAHA, maker floor $1 \times 10^{-15}$, tick shading, darkpool ATS, anti-gaming MinQty
- **Worker 4 (Quant Verification Specialist)** (`worker_quant_phase43_bench`):
  - Files owned: `trading_system/scripts/benchmark_phase43_quant_performance.py`, `tests/test_phase43_benchmark.py`, 4 comparison report files, `AGENTS.md`, `PROJECT.md`
  - Implement F194 benchmark script, execute benchmark across 5 markets, generate 3 comparison tables, verify performance targets, update documentation

## Phase 2: Multi-Agent Review & Gate Verification
- **Reviewer 1** (`reviewer_phase43_1`): Review Alpha & Risk modules, verify mathematics, implementations, unit tests.
- **Reviewer 2** (`reviewer_phase43_2`): Review OMS & Benchmark modules, verify routing, micro-friction, benchmark output.
- **Challenger 1** (`challenger_phase43_1`): Adversarial stress testing of Alpha & Risk modules.
- **Challenger 2** (`challenger_phase43_2`): Adversarial stress testing of OMS & Benchmark modules.
- **Forensic Auditor** (`auditor_phase43_1`): Independent integrity audit (zero hardcoding, genuine computation, causality, test authenticity).

## Phase 3: Gate Evaluation & Handoff
- Evaluate all verdicts in `GATE_STATUS.md` (unanimous pass required).
- Write comprehensive `handoff.md`.
- Send victory message to Sentinel.
