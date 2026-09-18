# DISPATCH: Phase 52 Quant Enhancement (Full Team)

## Working Directory
d:\Finance\code\stock\.agents\orchestrator_quant_phase52_1

## Context & Objectives
You are the Project Orchestrator leading a 4-specialist full team (Alpha Signal / Modeler, Risk Allocation / Risk Engineer, Microstructure OMS Specialist, Quant Verification / Benchmark Verifier) to deliver Phase 52 Quant Enhancement (v59 Production Master) across all 5 global equity markets (KOSPI, KOSDAQ, S&P 500, NASDAQ, RUSSELL 2000).

Authoritative user request is recorded in:
- `d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md` (Header: ## 2026-09-17T18:14:52Z)
- `d:\Finance\code\stock\ORIGINAL_REQUEST.md` (Header: ## 2026-09-17T18:14:52Z)

## Verbatim User Task & Requirements
Enhance institutional portfolio net return and risk-adjusted alpha across 5 global equity markets (KOSPI, KOSDAQ, S&P 500, NASDAQ, RUSSELL 2000) through Phase 52 Quantitative Alpha Enhancement (v59 Production Master), elevating Net Expected Return to ≥ 174.25% (Target: 174.29%, +2.10%p over Phase 51 baseline 172.19%), Sharpe Ratio to ≥ 34.55 (Target: 34.58, +0.60 over Phase 51 baseline 33.98), maintaining Maximum Drawdown (MDD) strictly ≤ -0.00001%, and halving execution friction costs without synthetic or hardcoded return numbers.

Working directory: d:\Finance\code\stock
Integrity mode: development

## Requirements

### R1. Alpha Signal Disentanglement & Ultra-Convex Rank Modulation (Features F231, F232.1, F232.2)
- Extend Quantum Geometric Langlands Chiral Affine Lie Superalgebra Borcherds-Moonshine Monster Whittaker Coupler with Monster module $V^\natural$ partition polynomial deformation up to 78th/80th order and topological invariant defect to 39th/40th order ($\kappa_{\text{monster\_whit}}=12.50$, $\lambda_{\text{monster}}=0.92$, $\text{FERI}_{\text{v52}}$), exporting 28+ backward-compatible aliases on `ensemble_scorer.py` and gating harmony factor boost $(3.25 \cdot h_{\text{monster\_whit}} \cdot z_{\text{monster\_whit}})$ for `version >= 52`.
- Implement 47th-order hyper-convex rank modulation $g_{\text{v52}}(r) = 0.50 + 1.70 \cdot r \cdot \exp(\gamma_{\text{top}} \cdot r^{47})$ with regime-adaptive $\gamma_{\text{top}}$ up to $8.40$ (`BULL_LOW_VOL`) in `factor_suppression.py`, dampening the lower 70% below 1.70 while expanding top 1% convexity $g(1.0) \approx 7552 > 500.0$.
- Implement 224th-order bicentatetracontagonal hyperbolic noise deadband $z_{\text{denoised}} = z \cdot \tanh((|z|/\delta_{\text{eff}})^{224})$ eliminating boundary noise leakage to $< 10^{-144}$ ($\alpha=224.0, \delta=0.035$) while preserving 100% of high-conviction alpha signals ($|z| \ge 0.15$).

### R2. Portfolio Risk Allocation & 48th-Cumulant EVaR Tail Budgeting (Features F233.1, F233.2)
- Implement Lurie-Borcherds-Monster-Moonshine-Whittaker-Drinfeld Higher-Homology Fisher-Rao Barycenter Blending on the Riemannian probability simplex with metric curvature $\mu_{\text{lmbwdh2}} = [4.20, 3.10, 3.05, 4.75]$ across Black-Litterman, HERC, Risk Parity, and EVT-CVaR in `unified_portfolio_allocator.py`, maintaining simplex conservation ($\sum q_i = 1.0$) and exporting 18 method aliases delegated in `portfolio_allocator.py`.
- Implement 48th-cumulant expansion Trans-Singular-Eternal-Omni-Cosmic-Infinite-Supreme-Transcendent EVaR Tail Risk Measure ($48! \approx 1.24139 \times 10^{61}$, $\xi_{\text{monster}} = 0.999999999$) bounding catastrophic downside risk under Student-t and heavy-tailed shocks.
- Integrate ambiguity tilting in `calculate_weights` under `version >= 52` with information-theoretic entropy scaling $\epsilon_w = 0.520, \alpha_{\text{iep}} = 3.10$ and regime shifts $(\delta_{\text{bl}} = -9.75, \delta_{\text{herc}} = +6.00, \delta_{\text{rp}} = -10.25, \delta_{\text{cvar}} = +14.50)$.

### R3. Microstructure L3 Spacetime Hydrodynamics & Preemptive OMS (Features F234.1, F234.2)
- Implement Kerr-Newman-Kiselev 31-dark-energy DAHA L3 Spacetime Hydrodynamics with 31st dark energy component ($w = -33/3 = -11.0, k_{\text{daha}} = 0.23, k_{\text{monster}} = 0.22, \text{daha\_31\_factor} = 3.54, c_{\text{monster}} = 0.00000000009765625$, repulsive acceleration $-16.5 \cdot c \cdot r^{32}$) in `fast_lob_engine.py`, with 28 method aliases and stack frame inspection for `"phase52"`.
- Contract primary exchange lit maker ratio floor down to $1 \times 10^{-24}$ with 24-decimal precision in `smart_order_router.py`.
- Scale preemptive dark ATS routing allocation cap up to $99.9999999999998\%$ and anti-gaming MinQty up to $99.9999999999998\%$ under severe toxic queue imbalance.
- Implement preemptive micro-tick shading in `oms_engine.py` (both `ExecutionOMSEngine` and `AlmgrenChrissScheduler`) activating at $h > 0.00003$:
  $$\text{hawkes\_shift} = -\text{direction} \cdot 0.9999999999999 \cdot \text{spread} \cdot (h - 0.00003)$$

### R4. Verification Benchmarking & Complete Backward Compatibility (Feature F235)
- Build `trading_system/scripts/benchmark_phase52_quant_performance.py` evaluating 15 institutional metrics across all 5 markets (KOSPI, KOSDAQ, S&P 500, NASDAQ, RUSSELL 2000) comparing Phase 51 baseline with Phase 52 achievements.
- Synchronize formatted markdown reports across all 4 canonical paths:
  1. `reports/quant_benchmark_comparison_phase52.md`
  2. `trading_system/result/quant_benchmark_comparison_phase52.md`
  3. `trading_system/reports/quant_benchmark_comparison_phase52.md`
  4. `reports/quant_benchmark_comparison.md` (prepended with Phase 52 section)
- Maintain 100% backward compatibility for all Phase 1~51 modules gated by `version >= 52`.
- Update `AGENTS.md` and `PROJECT.md` with Feature Inventory (F226~F235) and Phase 52 Milestones.

## Verification Resources
- Existing benchmark scripts: `trading_system/scripts/benchmark_phase51_quant_performance.py`
- Test suites: `tests/test_phase51_alpha.py`, `tests/test_phase51_risk.py`, `tests/test_phase51_oms.py`, `tests/test_phase51_adversarial_challenger1.py`, `tests/test_phase51_adversarial_oms_benchmark.py`
- Python runtime: `.venv\Scripts\python.exe`

## Acceptance Criteria

### 1. 5-Market Quantitative Benchmark Targets
- [ ] **Net Expected Return**: $\ge 174.25\%$ (Target: **174.29%**, $+2.10\%$p over Phase 51 baseline $172.19\%$).
- [ ] **Sharpe Ratio**: $\ge 34.55$ (Target: **34.58**, $+0.60$ over Phase 51 baseline $33.98$).
- [ ] **Maximum Drawdown (MDD)**: Strictly $\le -0.00001\%$ maintained across all 5 markets.
- [ ] **Trading & Friction Costs**: $\le 0.0000000234375\text{ bps}$ ($-50\%$ reduction from $0.000000046875\text{ bps}$).
- [ ] **Execution Slippage**: $\le 0.00000001953125\text{ bps}$ ($-50\%$ reduction from $0.0000000390625\text{ bps}$).
- [ ] **Top-Decile Alpha Spread**: $\ge 151.70\%$ (Target: **151.72%**, $+2.30\%$p over Phase 51 baseline $149.42\%$).
- [ ] **Win Rate**: $100.0\%$ (leakage $< 10^{-144}$).

### 2. Implementation Integrity & Modeling Rigor
- [ ] Zero mock data, zero synthetic return values, and zero artificial sleep/shortcuts.
- [ ] 100% genuine mathematical modeling across Lie superalgebras, Riemannian barycenters, cumulant expansions, and general relativistic black hole hydrodynamics.
- [ ] Complete set of method aliases (28 for Coupler, 18 for Barycenter, 28 for L3 queue acceleration).
- [ ] All code changes gated by `version >= 52` preserving 100% backward compatibility for Phase 1~51.

### 3. Automated Test Suites & Regression Verification
- [ ] `tests/test_phase52_alpha.py`: 100% pass (Coupler invariants, 47th-order modulation, 224th-order deadband leakage).
- [ ] `tests/test_phase52_risk.py`: 100% pass (Fisher-Rao simplex, 48th-cumulant EVaR bounds, ambiguity tilting).
- [ ] `tests/test_phase52_oms.py`: 100% pass (KNK 31-dark-energy DAHA, maker floor $10^{-24}$, dark cap $0.999999999999998$, tick shading at $h > 0.00003$).
- [ ] `tests/test_phase52_adversarial_challenger1.py`: 100% pass (subnormal deadband annihilation, odd symmetry, right-tail convexity, EVaR monotonicity).
- [ ] `tests/test_phase52_adversarial_oms_benchmark.py`: 100% pass (maker floor grid immunity, extreme routing, report SHA-256 hash synchronization).
- [ ] Full regression suite: `tests/test_phase51_*.py`, `tests/test_phase50_*.py`, `tests/test_phase49_*.py` pass with 100% success rate (zero regressions).

## Execution Discipline
- Python executable: `.venv/Scripts/python.exe` (or `.venv\Scripts\python.exe`)
- Maintain `progress.md` and `plan.md` in your working directory (`d:\Finance\code\stock\.agents\orchestrator_quant_phase52_1`).
- Decompose and orchestrate across 4 specialist roles:
  1. Alpha Signal Specialist (Modeler): F231, F232.1, F232.2 in `ensemble_scorer.py` and `factor_suppression.py`
  2. Risk Allocation Specialist (Risk Engineer): F233.1, F233.2 in `unified_portfolio_allocator.py` and `portfolio_allocator.py`
  3. Microstructure OMS Specialist (OMS Specialist): F234.1, F234.2 in `fast_lob_engine.py`, `smart_order_router.py`, and `oms_engine.py`
  4. Quant Verification Specialist (Benchmark Verifier): F235 benchmark script, test suite, reports 4-path sync, and doc updates
- Verify all tests pass before claiming completion.
- Complete backward compatibility with all prior phases (Phase 1~51).
- Once done, send a completion message to Sentinel with full deliverables summary so Victory Auditor can be dispatched.
