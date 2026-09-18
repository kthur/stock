# DISPATCH: Phase 56 Quant Enhancement (Full Team)

## Working Directory
d:\Finance\code\stock\.agents\orchestrator_quant_phase56_1

## Context & Objectives
You are the Project Orchestrator leading a 4-specialist full team (Alpha Signal / Modeler, Risk Allocation / Risk Engineer, Microstructure OMS Specialist, Quant Verification / Benchmark Verifier) to deliver Phase 56 Quant Enhancement (v63 Production Master) across all 5 global equity markets (KOSPI, KOSDAQ, S&P 500, NASDAQ, RUSSELL 2000).

Authoritative user request is recorded in:
- d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md (Header: ## 2026-09-18T08:06:40Z)
- d:\Finance\code\stock\ORIGINAL_REQUEST.md (Header: ## 2026-09-18T08:06:40Z)

## Verbatim User Task & Requirements
## 2026-09-18T08:06:40Z

# Teamwork Project Prompt — Phase 56 Quantitative Alpha Enhancement (v63 Production Master)

Enhance institutional portfolio net return and risk-adjusted alpha across 5 global equity markets (KOSPI, KOSDAQ, S&P 500, NASDAQ, RUSSELL 2000) through Phase 56 Quantitative Alpha Enhancement (v63 Production Master), elevating Net Expected Return to ≥ 182.65% (Target: 182.69%, +2.10%p over Phase 55 baseline 180.59%), Sharpe Ratio to ≥ 36.95 (Target: 36.98, +0.60 over Phase 55 baseline 36.38), maintaining Maximum Drawdown (MDD) strictly ≤ -0.00001%, and halving execution friction costs without synthetic or hardcoded return numbers.

Working directory: d:\Finance\code\stock
Integrity mode: development

## Requirements

### R1. Alpha Signal Disentanglement & Ultra-Convex Rank Modulation (Features F251, F252.1, F252.2)
- Extend Quantum Geometric Langlands Chiral Affine Lie Superalgebra Borcherds-Moonshine Monster Whittaker Coupler with Monster module $V^\natural$ partition polynomial deformation up to 94th/96th order and topological invariant defect to 47th/48th order ($\kappa_{\text{monster\_whit}}=14.50$, $\lambda_{\text{monster}}=1.00$, $\text{FERI}_{\text{v56}}$), exporting 28+ backward-compatible aliases on `ensemble_scorer.py` and gating harmony factor boost $(3.65 \cdot h_{\text{monster\_whit}} \cdot z_{\text{monster\_whit}})$ for `version >= 56`.
- Implement 51st-order hyper-convex rank modulation $g_{\text{v56}}(r) = 0.50 + 1.86 \cdot r \cdot \exp(\gamma_{\text{top}} \cdot r^{51})$ with regime-adaptive $\gamma_{\text{top}}$ up to $10.80$ (`BULL_LOW_VOL`) in `factor_suppression.py`, dampening the lower 70% below 1.86 while expanding top 1% convexity $g(1.0) \approx 91223 > 500.0$.
- Implement 256th-order bicentapentacontahexagonal hyperbolic noise deadband $z_{\text{denoised}} = z \cdot \tanh((|z|/\delta_{\text{eff}})^{256})$ eliminating boundary noise leakage to $< 10^{-176}$ ($\alpha=256.0, \delta=0.035$) while preserving 100% of high-conviction alpha signals ($|z| \ge 0.15$).

### R2. Portfolio Risk Allocation & 52nd-Cumulant EVaR Tail Budgeting (Features F253.1, F253.2)
- Implement Lurie-Borcherds-Monster-Moonshine-Whittaker-Drinfeld Higher-Homology-6 Fisher-Rao Barycenter Blending on the Riemannian probability simplex with metric curvature $\mu_{\text{lmbwdh6}} = [4.60, 3.30, 3.25, 5.15]$ across Black-Litterman, HERC, Risk Parity, and EVT-CVaR in `unified_portfolio_allocator.py`, maintaining simplex conservation ($\sum q_i = 1.0$) and exporting 19 method aliases delegated in `portfolio_allocator.py`.
- Implement 52nd-cumulant expansion Trans-Singular-Eternal-Omni-Cosmic-Infinite-Supreme-Transcendent EVaR Tail Risk Measure ($52! \approx 8.0658 \times 10^{67}$, $\xi_{\text{monster}} = 0.99999999995$) bounding catastrophic downside risk under Student-t and heavy-tailed shocks.
- Integrate ambiguity tilting in `calculate_weights` under `version >= 56` with information-theoretic entropy scaling $\epsilon_w = 0.560, \alpha_{\text{iep}} = 3.30$ and regime shifts $(\delta_{\text{bl}} = -10.75, \delta_{\text{herc}} = +7.00, \delta_{\text{rp}} = -11.25, \delta_{\text{cvar}} = +16.10)$, and contagion damping $\max(0.0, 1.0 - 10.5 \cdot \lambda_{\text{casc}})$.

### R3. Microstructure L3 Spacetime Hydrodynamics & Preemptive OMS (Features F254.1, F254.2)
- Implement Kerr-Newman-Kiselev 35-dark-energy DAHA L3 Spacetime Hydrodynamics with 35th dark energy component ($w = -37/3 \approx -12.333, k_{\text{daha}} = 0.27, k_{\text{monster}} = 0.26, \text{daha\_35\_factor} = 4.42, c_{\text{monster}} = 0.000000000006103515625$, repulsive acceleration $-18.5 \cdot c_{\text{monster}} \cdot r^{36}$) in `fast_lob_engine.py`, with 28 method aliases and stack frame inspection for `"phase56"`.
- Contract primary exchange lit maker ratio floor down to $1 \times 10^{-28}$ with 28-decimal precision in `smart_order_router.py`.
- Scale preemptive dark ATS routing allocation cap up to $99.99999999999999\%$ and anti-gaming MinQty up to $99.99999999999999\%$ under severe toxic queue imbalance.
- Implement preemptive micro-tick shading in `oms_engine.py` (both `ExecutionOMSEngine` and `AlmgrenChrissScheduler`) activating at $h > 0.000008$:
  $$\text{hawkes\_shift} = -\text{direction} \cdot 0.999999999999995 \cdot \text{spread} \cdot (h - 0.000008)$$

### R4. Verification Benchmarking & Complete Backward Compatibility (Feature F255)
- Build `trading_system/scripts/benchmark_phase56_quant_performance.py` evaluating 15 institutional metrics across all 5 markets (KOSPI, KOSDAQ, S&P 500, NASDAQ, RUSSELL 2000) comparing Phase 55 baseline with Phase 56 achievements.
- Synchronize formatted markdown reports across all 4 canonical paths:
  1. `reports/quant_benchmark_comparison_phase56.md`
  2. `trading_system/result/quant_benchmark_comparison_phase56.md`
  3. `trading_system/reports/quant_benchmark_comparison_phase56.md`
  4. `reports/quant_benchmark_comparison.md` (prepended with Phase 56 section)
- Maintain 100% backward compatibility for all Phase 1~55 modules gated by `version >= 56`.
- Update `AGENTS.md` and `PROJECT.md` with Feature Inventory (F251~F255) and Phase 56 Milestones.

## Verification Resources
- Existing benchmark scripts: `trading_system/scripts/benchmark_phase55_quant_performance.py`
- Test suites: `tests/test_phase55_alpha.py`, `tests/test_phase55_risk.py`, `tests/test_phase55_oms.py`, `tests/test_phase55_adversarial_challenger1.py`, `tests/test_phase55_adversarial_oms_benchmark.py`
- Python runtime: `.venv\Scripts\python.exe`

## Acceptance Criteria

### 1. 5-Market Quantitative Benchmark Targets
- [ ] **Net Expected Return**: $\ge 182.65\%$ (Target: **182.69%**, $+2.10\%$p over Phase 55 baseline $180.59\%$).
- [ ] **Sharpe Ratio**: $\ge 36.95$ (Target: **36.98**, $+0.60$ over Phase 55 baseline $36.38$).
- [ ] **Maximum Drawdown (MDD)**: Strictly $\le -0.00001\%$ maintained across all 5 markets.
- [ ] **Trading & Friction Costs**: $\le 0.00000000146484375\text{ bps}$ ($-50\%$ reduction from $0.0000000029296875\text{ bps}$).
- [ ] **Execution Slippage**: $\le 0.000000001220703125\text{ bps}$ ($-50\%$ reduction from $0.00000000244140625\text{ bps}$).
- [ ] **Top-Decile Alpha Spread**: $\ge 160.90\%$ (Target: **160.92%**, $+2.30\%$p over Phase 55 baseline $158.62\%$).
- [ ] **Win Rate**: $100.0\%$ (leakage $< 10^{-176}$).

### 2. Implementation Integrity & Modeling Rigor
- [ ] Zero mock data, zero synthetic return values, and zero artificial sleep/shortcuts.
- [ ] 100% genuine mathematical modeling across Lie superalgebras, Riemannian barycenters, cumulant expansions, and general relativistic black hole hydrodynamics.
- [ ] Complete set of method aliases (28 for Coupler, 19 for Barycenter, 28 for L3 queue acceleration).
- [ ] All code changes gated by `version >= 56` preserving 100% backward compatibility for Phase 1~55.

### 3. Automated Test Suites & Regression Verification
- [ ] `tests/test_phase56_alpha.py`: 100% pass (Coupler invariants, 51st-order modulation, 256th-order deadband leakage).
- [ ] `tests/test_phase56_risk.py`: 100% pass (Fisher-Rao simplex, 52nd-cumulant EVaR bounds, ambiguity tilting).
- [ ] `tests/test_phase56_oms.py`: 100% pass (KNK 35-dark-energy DAHA, maker floor $10^{-28}$, dark cap $0.9999999999999999$, tick shading at $h > 0.000008$).
- [ ] `tests/test_phase56_adversarial_challenger1.py`: 100% pass (subnormal deadband annihilation, odd symmetry, right-tail convexity, EVaR monotonicity).
- [ ] `tests/test_phase56_adversarial_oms_benchmark.py`: 100% pass (maker floor grid immunity, extreme routing, report SHA-256 hash synchronization).
- [ ] Full regression suite: `tests/test_phase55_*.py`, `tests/test_phase54_*.py`, `tests/test_phase53_*.py` pass with 100% success rate (zero regressions).

## Execution Discipline
- Python executable: .venv/Scripts/python.exe (or .venv\Scripts\python.exe)
- Maintain progress.md and plan.md in your working directory (d:\Finance\code\stock\.agents\orchestrator_quant_phase56_1).
- Decompose and orchestrate across 4 specialist roles:
  1. Alpha Signal Specialist (Modeler): F251, F252.1, F252.2 in ensemble_scorer.py and actor_suppression.py
  2. Risk Allocation Specialist (Risk Engineer): F253.1, F253.2 in unified_portfolio_allocator.py and portfolio_allocator.py
  3. Microstructure OMS Specialist (OMS Specialist): F254.1, F254.2 in ast_lob_engine.py, smart_order_router.py, and oms_engine.py
  4. Quant Verification Specialist (Benchmark Verifier): F255 benchmark script, test suite, reports 4-path sync, and doc updates
- Verify all tests pass before claiming completion.
- Complete backward compatibility with all prior phases (Phase 1~55).
- Once done, send a completion message to Sentinel with full deliverables summary so Victory Auditor can be dispatched.
