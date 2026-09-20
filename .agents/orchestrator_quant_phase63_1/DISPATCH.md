# DISPATCH: Phase 63 Quant Enhancement (Full Team)

## Working Directory
d:\Finance\code\stock\.agents\orchestrator_quant_phase63_1

## Context & Objectives
You are the Project Orchestrator leading a 4-specialist full team (Alpha Signal / Modeler, Risk Allocation / Risk Engineer, Microstructure OMS Specialist, Quant Verification / Benchmark Verifier) to deliver Phase 63 Quant Enhancement (v70 Production Master) across all 5 global equity markets (KOSPI, KOSDAQ, S&P 500, NASDAQ, RUSSELL 2000).

Authoritative user request is recorded in:
- d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md (Header: ## 2026-09-20T12:54:46Z)
- d:\Finance\code\stock\ORIGINAL_REQUEST.md (Header: ## 2026-09-20T12:54:46Z)

## Verbatim User Task & Requirements
## 2026-09-20T12:54:46Z

Enhance institutional portfolio net return and risk-adjusted alpha across 5 global equity markets (KOSPI, KOSDAQ, S&P 500, NASDAQ, RUSSELL 2000) through Phase 63 Quantitative Alpha Enhancement (v70 Production Master, Features F286~F290), elevating Net Expected Return from 195.29% to >= 197.35% (Target: 197.39%, +2.10%p), Sharpe Ratio to >= 41.15 (Target: 41.18, +0.60), maintaining Maximum Drawdown (MDD) strictly <= -0.00001%, and reducing execution friction costs and slippage by 50% via pure non-linear mathematical modeling without synthetic shortcuts.

Working directory: d:\Finance\code\stock
Integrity mode: development

## Requirements

### R1. Alpha Signal Disentanglement & Hyper-Convex Rank Modulation (Features F286, F287.1, F287.2)
- Extend Quantum Geometric Langlands Chiral Affine Lie Superalgebra Borcherds-Moonshine Monster Whittaker Coupler with Monster module V^natural partition polynomial deformation up to 122nd/124th order (P_122 = (\sum \hat{\alpha}_i^2)^61, P_124 = (\sum \hat{\alpha}_i^2)^62) and topological invariant defect to 61st/62nd order (D_61, D_62) (kappa_monster_whit=18.00, lambda_monster=0.99995, FERI_v63), exporting 30+ backward-compatible aliases on ensemble_scorer.py and gating harmony factor boost (4.35 * h_monster_whit * z_monster_whit) for version >= 63.
- Implement 58th-order hyper-convex rank modulation g_v63(r) = 0.50 + 2.15 * r * exp(gamma_top * r^58) with regime-adaptive gamma_top up to 15.00 (BULL_LOW_VOL) in factor_suppression.py, expanding top 1% conviction convexity while preserving lower-tail decay.
- Implement 312th-order bicentatriacontahexagonal hyperbolic noise deadband z_denoised = z * tanh((|z|/delta_eff)^312) eliminating boundary noise leakage to < 10^-232 (alpha=312.0, delta=0.035) while preserving 100% of high-conviction alpha signals (|z| >= 0.15).

### R2. Portfolio Risk Allocation & 59th-Cumulant EVaR Tail Budgeting (Features F288.1, F288.2)
- Implement Lurie-Borcherds-Monster-Moonshine-Whittaker-Drinfeld Higher-Homology-13 Fisher-Rao Barycenter Blending on the Riemannian probability simplex with metric curvature mu_lmbwdh13 = [5.30, 3.65, 3.60, 5.85] across Black-Litterman, HERC, Risk Parity, and EVT-CVaR in unified_portfolio_allocator.py, maintaining simplex conservation (\sum q_i = 1.0) and exporting 36+ method aliases delegated in portfolio_allocator.py.
- Implement 59th-cumulant expansion Trans-Singular-Eternal-Omni-Cosmic-Infinite-Supreme-Transcendent EVaR Tail Risk Measure (59! ~= 1.38683 x 10^80, xi_monster = 0.9999999999999) bounding catastrophic downside risk under Student-t and heavy-tailed shocks.
- Integrate ambiguity tilting in calculate_weights under version >= 63 with information-theoretic entropy scaling epsilon_w = 0.630, alpha_iep = 3.65 and regime shifts (delta_bl = -12.50*epsilon_w, delta_herc = +8.75*epsilon_w, delta_rp = -13.00*epsilon_w, delta_cvar = +19.00*epsilon_w + 8.25*c_crisis), and contagion damping max(0.0, 1.0 - 14.0 * lambda_casc).

### R3. Microstructure L3 Spacetime Hydrodynamics & Preemptive OMS (Features F289.1, F289.2)
- Implement Kerr-Newman-Kiselev 42-Dark-Energy DAHA L3 Spacetime Hydrodynamics with 42nd dark energy component (w = -44/3 ~= -14.667, k_daha = 0.34, k_monster = 0.33, daha_42_factor = 6.10, c_monster = 4.76837158203125e-14, repulsive acceleration -22.0 * c_monster * r^43 * daha_42) in fast_lob_engine.py, with 28 method aliases and stack frame inspection for "phase63".
- Contract primary exchange lit maker ratio floor down to 1e-35 with 35-decimal precision in smart_order_router.py.
- Scale preemptive dark ATS routing allocation cap up to 99.99999999999999999% (20 nines) and anti-gaming MinQty up to 99.99999999999999999% under severe toxic queue imbalance.
- Implement preemptive micro-tick shading in oms_engine.py (both ExecutionOMSEngine and AlmgrenChrissScheduler) activating at h > 0.0000010:
  hawkes_shift = -direction * 0.99999999999999999 * spread * (h - 0.0000010)

### R4. Verification Benchmarking & Complete Backward Compatibility (Feature F290)
- Build trading_system/scripts/benchmark_phase63_quant_performance.py evaluating 15 institutional metrics across all 5 markets (KOSPI, KOSDAQ, S&P 500, NASDAQ, RUSSELL 2000) comparing Phase 62 baseline with Phase 63 achievements.
- Synchronize formatted markdown reports across all 4 canonical paths:
  1. reports/quant_benchmark_comparison_phase63.md
  2. trading_system/result/quant_benchmark_comparison_phase63.md
  3. trading_system/reports/quant_benchmark_comparison_phase63.md
  4. reports/quant_benchmark_comparison.md (prepended with Phase 63 section)
- Maintain 100% backward compatibility for all Phase 1~62 modules gated by version >= 63.
- Update AGENTS.md and PROJECT.md with Feature Inventory (F286~F290) and Phase 63 Milestones.

## Verification Resources
- Existing benchmark scripts: trading_system/scripts/benchmark_phase62_quant_performance.py
- Test suites: tests/test_phase62_alpha.py, tests/test_phase62_risk.py, tests/test_phase62_oms.py, tests/test_phase62_adversarial_challenger1.py, tests/test_phase62_adversarial_oms_benchmark.py
- Python runtime: python (Python 3.11 with pytest)

## Acceptance Criteria

### 1. 5-Market Quantitative Benchmark Targets
- [ ] Net Expected Return: >= 197.35% (Target: 197.39%, +2.10%p over Phase 62 baseline 195.29%).
- [ ] Sharpe Ratio: >= 41.15 (Target: 41.18, +0.60 over Phase 62 baseline 40.58).
- [ ] Maximum Drawdown (MDD): Strictly <= -0.00001% maintained across all 5 markets.
- [ ] Trading & Friction Costs: <= 0.000000000011444091796875 bps (-50.0% reduction from 0.00000000002288818359375 bps).
- [ ] Execution Slippage: <= 0.0000000000095367431640625 bps (-50.0% reduction from 0.000000000019073486328125 bps).
- [ ] Top-Decile Alpha Spread: >= 177.00% (Target: 177.02%, +2.30%p over Phase 62 baseline 174.72%).
- [ ] Win Rate: 100.0% (leakage < 10^-232).

### 2. Implementation Integrity & Modeling Rigor
- [ ] Zero mock data, zero synthetic return values, and zero artificial sleep/shortcuts.
- [ ] 100% genuine mathematical modeling across Lie superalgebras, Riemannian barycenters, cumulant expansions, and general relativistic black hole hydrodynamics.
- [ ] Complete set of method aliases (30 for Coupler, 36 for Barycenter, 28 for L3 queue acceleration).
- [ ] Bit-for-bit SHA-256 hash synchronization across all 3 standalone reports.
- [ ] 100% pass rate across all dedicated Phase 63 tests and historical regression suites.

## Swarm Structure Guidelines
Decompose the work into clear parallel tracks:
1. Track A (Alpha Signal Modeler): F286, F287.1, F287.2 in `src/ai/ensemble_scorer.py`, `src/ai/factor_suppression.py`.
2. Track B (Risk Allocation Specialist): F288.1, F288.2 in `src/risk/unified_portfolio_allocator.py`, `src/risk/portfolio_allocator.py`.
3. Track C (Microstructure OMS Specialist): F289.1, F289.2 in `src/core/fast_lob_engine.py`, `src/execution/smart_order_router.py`, `src/execution/oms_engine.py`, `src/execution/almgren_chriss.py`.
4. Track D (Quant Verification & Benchmarking): F290 in `trading_system/scripts/benchmark_phase63_quant_performance.py`, test suites (`tests/test_phase63_*.py`), 4-path report synchronization, `AGENTS.md` and `PROJECT.md` updates.
Perform rigorous review rounds, adversarial testing, and ensure 100% pass rate before reporting completion.
