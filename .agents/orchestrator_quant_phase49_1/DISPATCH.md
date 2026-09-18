# DISPATCH: Phase 49 Quant Enhancement (Full Team)

## Working Directory
d:\Finance\code\stock\.agents\orchestrator_quant_phase49_1

## Context & Objectives
You are the Project Orchestrator leading a 4-specialist full team (Alpha Signal, Risk Allocation, Microstructure OMS, Quant Verification) to deliver Phase 49 Quant Enhancement (v56 Production Master) across all 5 global equity markets (KOSPI, KOSDAQ, S&P 500, NASDAQ, RUSSELL 2000).

Authoritative user request is recorded in:
- `d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md` (Header: ## 2026-09-17T12:06:49Z)
- `d:\Finance\code\stock\ORIGINAL_REQUEST.md` (Header: ## 2026-09-17T12:06:49Z)

## Verbatim User Task & Requirements
Enhance institutional portfolio net return and risk-adjusted alpha across 5 equity markets (KOSPI, KOSDAQ, S&P 500, NASDAQ, RUSSELL 2000) through Phase 49 Quantitative Alpha Enhancement (v56 Production Master), elevating Net Expected Return to ≥ 167.95% (+2.06%p over Phase 48 baseline 165.89%), Sharpe Ratio to ≥ 32.75 (+0.57 over Phase 48 baseline 32.18), maintaining MDD strictly ≤ -0.00001%, and halving execution friction costs without synthetic or hardcoded return numbers.

Working directory: d:\Finance\code\stock
Integrity mode: development

## Requirements

### R1. Alpha Signal Disentanglement & Ultra-Convex Rank Modulation (Feature F216, F217.1, F217.2)
- Implement Quantum Geometric Langlands Chiral Affine Borcherds-Moonshine Monster Whittaker Coupler with higher-order partition polynomial deformation to 68th order and topological invariant defect to 34th order ($\kappa_{\text{monster\_whit}}=10.50$, $\lambda_{\text{monster}}=0.82$, $\text{FERI}_{\text{v49}}$), exporting 26 backward-compatible aliases on `ensemble_scorer.py` and gating harmony factor boost $(2.95 \cdot h_{\text{monster\_whit}} \cdot z_{\text{monster\_whit}})$ for `version >= 49`.
- Implement 44th-order hyper-convex rank modulation $g_{\text{v49}}(r) = 0.50 + 1.58 \cdot r \cdot \exp(\gamma_{\text{top}} \cdot r^{44})$ with regime-adaptive $\gamma_{\text{top}}$ up to $6.50$ (`BULL_LOW_VOL`) in `factor_suppression.py`, dampening the lower 70% below 1.62 while expanding top 1% convexity $g(1.0) > 460.0$.
- Implement 200th-order bicentagonal hyperbolic noise deadband $z_{\text{denoised}} = z \cdot \tanh((|z|/\delta_{\text{eff}})^{200})$ eliminating boundary noise leakage to $< 10^{-120}$ ($\alpha=200.0, \delta=0.035$) while preserving 100% of high-conviction alpha signals ($|z| \ge 0.15$).

### R2. Portfolio Risk Allocation & 45th-Cumulant EVaR Tail Budgeting (Feature F218.1)
- Implement Lurie-Borcherds-Monster-Moonshine-Whittaker Motivic Fisher-Rao Barycenter Blending on the Riemannian probability simplex with metric curvature $\mu_{\text{lmbw}} = [3.90, 2.95, 2.90, 4.45]$ across Black-Litterman, HERC, Risk Parity, and EVT-CVaR in `unified_portfolio_allocator.py`, maintaining simplex conservation ($\sum q_i = 1.0$) and exporting 15 method aliases delegated in `portfolio_allocator.py`.
- Implement 45th-cumulant expansion Trans-Singular-Eternal-Omni-Cosmic-Infinite-Supreme-Transcendent EVaR Tail Risk Measure ($45! \approx 1.19622 \times 10^{56}$, $\xi_{\text{monster}} = 0.99999999$) bounding catastrophic downside risk under Student-t and heavy-tailed shocks.
- Integrate ambiguity tilting in `calculate_weights` under `version >= 49` with information-theoretic entropy scaling $\alpha_{\text{iep}} = 2.95$.

### R3. Microstructure L3 Spacetime Hydrodynamics & Preemptive OMS (Feature F219.1, F219.2)
- Implement Kerr-Newman-Kiselev 28-dark-energy DAHA L3 Spacetime Hydrodynamics with 28th dark energy component ($w = -10.0 = -30/3, k_{\text{daha}} = 0.20, k_{\text{monster}} = 0.19, \text{daha\_28\_factor} = 2.92, c_{\text{monster}} = 0.00000000078125$, repulsive acceleration $-15.0 \cdot c \cdot r^{29}$) in `fast_lob_engine.py`, with 21 method aliases and stack frame inspection for `"phase49"`.
- Contract primary exchange lit maker ratio floor down to $1 \times 10^{-21}$ via $0.70 \cdot (1.0 - 0.999999999999999999986 \cdot \gamma_{\text{toxic}})$ in `smart_order_router.py`.
- Scale preemptive dark ATS routing allocation cap up to $99.999999999998\%$ and anti-gaming MinQty up to $99.999999999998\%$ under severe toxic queue imbalance.
- Implement preemptive micro-tick shading in `oms_engine.py` (both `ExecutionOMSEngine` and `AlmgrenChrissScheduler`) activating at $h > 0.00006$:
  $$\text{hawkes\_shift} = -\text{direction} \cdot 0.999999999999 \cdot \text{spread} \cdot (h - 0.00006)$$

### R4. Verification Benchmarking & Complete Backward Compatibility (Feature F220)
- Build `trading_system/scripts/benchmark_phase49_quant_performance.py` evaluating 15 institutional metrics across all 5 markets (KOSPI, KOSDAQ, S&P 500, NASDAQ, RUSSELL 2000) comparing Phase 48 baseline with Phase 49 achievements.
- Synchronize formatted markdown reports across all 4 canonical paths:
  1. `reports/quant_benchmark_comparison_phase49.md`
  2. `trading_system/result/quant_benchmark_comparison_phase49.md`
  3. `trading_system/reports/quant_benchmark_comparison_phase49.md`
  4. `reports/quant_benchmark_comparison.md` (prepended with Phase 49 section)
- Maintain 100% backward compatibility for all Phase 1~48 modules gated by `version >= 49`.
- Update `AGENTS.md` and `PROJECT.md` with Feature Inventory (F216~F220) and Phase 49 Milestones.

## Verification Resources
- Existing benchmark scripts: `trading_system/scripts/benchmark_phase48_quant_performance.py`
- Test suites: `tests/test_phase48_alpha.py`, `tests/test_phase48_risk.py`, `tests/test_phase48_oms.py`, `tests/test_phase48_adversarial_challenger1.py`, `tests/test_phase48_adversarial_oms_benchmark.py`
- Python runtime: `.venv\Scripts\python.exe`

## Acceptance Criteria

### 1. 5-Market Quantitative Benchmark Targets
- [ ] **Net Expected Return**: $\ge 167.95\%$ (Target: **167.99%**, $+2.10\%$p over Phase 48 baseline $165.89\%$).
- [ ] **Sharpe Ratio**: $\ge 32.75$ (Target: **32.78**, $+0.60$ over Phase 48 baseline $32.18$).
- [ ] **Maximum Drawdown (MDD)**: Strictly $\le -0.00001\%$ maintained across all 5 markets.
- [ ] **Trading & Friction Costs**: $\le 0.0000001875\text{ bps}$ ($-50\%$ reduction from $0.000000375\text{ bps}$).
- [ ] **Execution Slippage**: $\le 0.00000015625\text{ bps}$ ($-50\%$ reduction from $0.0000003125\text{ bps}$).
- [ ] **Top-Decile Alpha Spread**: $\ge 144.80\%$ (Target: **144.82%**, $+2.30\%$p over Phase 48 baseline $140.22\%$).
- [ ] **Win Rate**: $100.0\%$ (leakage $< 10^{-120}$).

### 2. Implementation Integrity & Modeling Rigor
- [ ] Zero mock data, zero synthetic return values, and zero artificial sleep/shortcuts.
- [ ] 100% genuine mathematical modeling across Lie superalgebras, Riemannian barycenters, cumulant expansions, and general relativistic black hole hydrodynamics.
- [ ] Complete set of method aliases (26 for Coupler, 15 for Barycenter, 21 for L3 queue acceleration).
- [ ] All code changes gated by `version >= 49` preserving 100% backward compatibility for Phase 1~48.

### 3. Automated Test Suites & Regression Verification
- [ ] `tests/test_phase49_alpha.py`: 100% pass (Coupler invariants, 44th-order modulation, 200th-order deadband leakage).
- [ ] `tests/test_phase49_risk.py`: 100% pass (Fisher-Rao simplex, 45th-cumulant EVaR bounds, ambiguity tilting).
- [ ] `tests/test_phase49_oms.py`: 100% pass (KNK 28-dark-energy DAHA, maker floor $10^{-21}$, dark cap $0.99999999999998$, tick shading at $h > 0.00006$).
- [ ] `tests/test_phase49_adversarial_challenger1.py`: 100% pass (subnormal deadband annihilation, odd symmetry, right-tail convexity, EVaR monotonicity).
- [ ] `tests/test_phase49_adversarial_oms_benchmark.py`: 100% pass (maker floor grid immunity, 100 quintillion share extreme routing, report SHA-256 hash synchronization).
- [ ] Full regression suite: `tests/test_phase48_*.py` and historical suites pass with 100% success rate (zero regressions).

## Execution Discipline
- Python executable: `.venv/Scripts/python.exe` (or `.venv\Scripts\python.exe`)
- Maintain `progress.md` and `plan.md` in your working directory (`d:\Finance\code\stock\.agents\orchestrator_quant_phase49_1`).
- Decompose and orchestrate across 4 specialist roles:
  1. Alpha Signal Specialist: F216, F217.1, F217.2 in `ensemble_scorer.py` and `factor_suppression.py`
  2. Risk Allocation Specialist: F218.1 in `unified_portfolio_allocator.py` and `portfolio_allocator.py`
  3. Microstructure OMS Specialist: F219.1, F219.2 in `fast_lob_engine.py`, `smart_order_router.py`, and `oms_engine.py`
  4. Quant Verification Specialist: F220 benchmark script, test suite, reports 4-path sync, and doc updates
- Verify all tests pass before claiming completion.
- Complete backward compatibility with all prior phases (Phase 1~48).
- Once done, send a completion message to Sentinel with full deliverables summary so Victory Auditor can be dispatched.
