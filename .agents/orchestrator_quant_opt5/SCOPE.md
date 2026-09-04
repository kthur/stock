# Scope: Phase 5 Deep Quantitative Enhancements (5차 심화 퀀트 개선)

## Architecture
- **Alpha & Ensemble Layer**: `src/ai/ensemble_scorer.py`, `src/ai/score_normalizer.py`, `src/ai/factor_suppression.py`, `src/ai/factor_orthogonalizer.py`
- **Portfolio & Risk Layer**: `src/risk/unified_portfolio_allocator.py`, `src/risk/portfolio_allocator.py`, `src/risk/risk_manager.py`
- **Execution & Routing Layer**: `src/execution/smart_order_router.py`, `src/execution/oms_engine.py`, `src/execution/slippage_feedback.py`
- **Benchmarking & Reporting Layer**: `trading_system/scripts/benchmark_phase5_quant_performance.py`, `reports/quant_benchmark_comparison_phase5.md`
- **Verification Layer**: `tests/test_phase5_signal_enhancement.py`, `tests/test_phase5_portfolio_execution.py`, `tests/test_benchmark_phase5.py`, full test suite (2,351+ tests)

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| F35 | High-Order Non-Linear Signal Combination & Right-Tail Convexity | Regime-adaptive Richards exponent $\gamma_{\text{tail}} \in [1.00, 1.30]$, quadratic rank modulation, Quad-Pillar confluence kernel $\Xi_{\text{quad}}$, Hölder $p=2.0$ quadratic mean boost, asymmetric Richards tail scaling ($\eta_{\text{right}}=2.0$) | M15 | ORIGINAL_REQUEST R1 |
| F36 | Regime Transition Half-Life Dynamic Decay & Downside Noise Filtering | Probabilistic regime half-life expectation with Shannon entropy factor $\phi_{\text{entropy}}$ & TV jump penalty $\phi_{\text{jump}}$, and smooth tanh noise deadband attenuation $z \cdot \tanh((|z|/\delta)^3)$ | M15 | ORIGINAL_REQUEST R1 |
| F37 | 4-Model Portfolio Allocation & Capital Efficiency 5th Deepening | Higher-order co-skewness/co-kurtosis alpha conviction tilt, dynamic Cornish-Fisher EVT-CVaR tail expansion, DRP-DR scaling, and Shannon entropy-weighted adaptive target volatility scaling | M16 | ORIGINAL_REQUEST R2 |
| F38 | SOR & Darkpool/HFT OBI Pegging & Micro-Friction Slippage Minimization | Continuous Hawkes toxicity modulation, Darkpool midpoint resting with MinQty $\ge 20\%$, volatility/depth-adaptive L2 OBI micro-price curvature, ADV-adaptive Gatheral slice count with volume smile, and 5-market Leland buffer bands | M16 | ORIGINAL_REQUEST R2 |
| F39 | Phase 5 Benchmark Performance Engine & Multi-Market Comparison Reports | Build `benchmark_phase5_quant_performance.py`, generate 5-market comparison tables across 15 metrics, sync to 3 report destinations, and build `test_benchmark_phase5.py` | M17 | ORIGINAL_REQUEST R3 |
| F40 | Phase 5 Full Test Suite & Multi-Agent Forensic Verification | Scale test suite to 2,380+ tests with 100% pass rate, zero regressions, and multi-agent forensic integrity audit | M18 | ORIGINAL_REQUEST Acceptance Criteria |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M15 | Phase 5 Dynamic Alpha Signal Quality & Top Alpha (R1) | F35, F36: `ensemble_scorer.py`, `test_phase5_signal_enhancement.py` | Survey Complete | **DONE** |
| M16 | Phase 5 Portfolio Allocation & Execution Friction (R2) | F37, F38: `unified_portfolio_allocator.py`, `smart_order_router.py`, `oms_engine.py`, `test_phase5_portfolio_execution.py` | M15 | **DONE** |
| M17 | Phase 5 Quantitative Benchmark Engine & Multi-Market Reports (R3) | F39: `benchmark_phase5_quant_performance.py`, sync reports across 3 paths, `test_benchmark_phase5.py` | M15, M16 | **DONE** |
| M18 | Phase 5 Full Test Suite & Forensic Verification (R4) | F40: 2,380+ test suite 100% pass rate, zero regressions, multi-agent review, challenger & forensic audit | M15, M16, M17 | **IN_PROGRESS** |

## Interface Contracts
### `ensemble_scorer.py` (M15 / F35, F36) — COMPLETED
- `combine_predictions`: receives `predictions_dict`, `regime_weights`, `market_regime`, `regime_probs` (optional), and returns DataFrame with `ensemble_score`, `expected_return`, `confidence`.
- Mathematical guarantee: strict rank monotonicity ($\rho_s = 1.0000$) on `convex_alpha` and bounded outputs in $[0.0, 1.0]$.
- Backward compatibility: when single string/int regime is provided, all Phase 4 behaviors and signatures remain valid.

### `unified_portfolio_allocator.py` & Execution Engines (M16 / F37, F38) — COMPLETED
- `optimize_multi_model_blend`: blends BL, HERC, RP, CVaR with higher-order co-moments, DRP-DR, and regime entropy scaling.
- `route_order` & `calculate_peg_limit_price`: continuous Hawkes toxicity gating, darkpool midpoint resting, and 5-market Leland buffer bands.

### Benchmarking & Reporting (M17 / F39) — COMPLETED
- `trading_system/scripts/benchmark_phase5_quant_performance.py`: computes and compares Phase 4 baseline vs Phase 5 enhanced across all 15 metrics in 5 markets and institutional capital-weighted aggregate.
- Output synchronized to:
  * `reports/quant_benchmark_comparison_phase5.md`
  * `trading_system/result/quant_benchmark_comparison_phase5.md`
  * `reports/quant_benchmark_comparison.md`
