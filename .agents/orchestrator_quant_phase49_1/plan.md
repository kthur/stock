# Project Plan: Phase 49 Quantitative Alpha Enhancement (v56 Production Master)

## Architecture & Scope
Institutional quantitative enhancement across 5 global equity markets (KOSPI, KOSDAQ, S&P 500, NASDAQ, RUSSELL 2000).

### Module Boundaries
1. **Alpha Engine**: `src/ai/ensemble_scorer.py` & `src/ai/factor_suppression.py`
2. **Portfolio Risk Layer**: `src/risk/unified_portfolio_allocator.py` & `src/risk/portfolio_allocator.py`
3. **Execution OMS / LOB**: `src/core/fast_lob_engine.py`, `src/execution/smart_order_router.py`, `src/execution/oms_engine.py`
4. **Verification & Benchmark**: `trading_system/scripts/benchmark_phase49_quant_performance.py`, `tests/test_phase49_*.py`, reports synchronization & docs

---

## Feature Inventory
| # | Feature ID | Name | Description | Module | Milestone | Status |
|---|---|---|---|---|---|---|
| 1 | F216 | Borcherds-Moonshine Monster Whittaker Coupler | Chiral affine coupler, higher-order partition polynomial deformation to 68th order, topological defect to 34th order, 26 aliases, harmony boost for version >= 49 | `ensemble_scorer.py` | M1 | Planned |
| 2 | F217.1 | 44th-Order Hyper-Convex Rank Modulation | $g_{\text{v49}}(r) = 0.50 + 1.58 \cdot r \cdot \exp(\gamma_{\text{top}} \cdot r^{44})$, $\gamma_{\text{top}} \le 6.50$, lower 70% dampened below 1.62, top 1% $g(1.0) > 460.0$ | `factor_suppression.py` | M1 | Planned |
| 3 | F217.2 | 200th-Order Bicentagonal Hyperbolic Noise Deadband | $z_{\text{denoised}} = z \cdot \tanh((|z|/\delta_{\text{eff}})^{200})$, leakage $< 10^{-120}$ ($\alpha=200, \delta=0.035$) | `factor_suppression.py` | M1 | Planned |
| 4 | F218.1 | Lurie-Borcherds-Monster Fisher-Rao Barycenter & 45th-Cumulant EVaR | Riemannian simplex barycenter with $\mu_{\text{lmbw}}=[3.90, 2.95, 2.90, 4.45]$, 15 aliases, 45th-cumulant EVaR ($45! \approx 1.196 \times 10^{56}$), ambiguity tilting $\alpha_{\text{iep}}=2.95$ | `unified_portfolio_allocator.py`, `portfolio_allocator.py` | M2 | Planned |
| 5 | F219.1 | KNK 28-Dark-Energy DAHA L3 Spacetime Hydrodynamics | 28th dark energy component ($w=-10.0, k_{\text{daha}}=0.20, k_{\text{monster}}=0.19$, repulsive acceleration $-15 \cdot c \cdot r^{29}$), 21 aliases, phase49 stack inspection | `fast_lob_engine.py` | M3 | Planned |
| 6 | F219.2 | Preemptive Dark ATS Routing & Micro-Tick Shading | Lit maker floor $10^{-21}$, dark ATS cap $99.999999999998\%$, tick shading at $h > 0.00006$ in `ExecutionOMSEngine` & `AlmgrenChrissScheduler` | `smart_order_router.py`, `oms_engine.py` | M3 | Planned |
| 7 | F220 | 5-Market Quantitative Benchmark & Report Sync | 15 institutional metrics across 5 markets, 4-path report sync, test suite creation, AGENTS.md & PROJECT.md update | `benchmark_phase49_quant_performance.py`, `tests/` | M4 | Planned |

---

## Milestone Breakdown

### Milestone 1 (M1): Alpha Signal Disentanglement & Ultra-Convex Rank Modulation
- **Features**: F216, F217.1, F217.2
- **Files**: `src/ai/ensemble_scorer.py`, `src/ai/factor_suppression.py`
- **Tests**: `tests/test_phase49_alpha.py`, `tests/test_phase48_alpha.py` (backward compatibility)
- **Role**: Alpha Signal Specialist (`teamwork_preview_worker` with Explorer guidance)

### Milestone 2 (M2): Portfolio Risk Allocation & 45th-Cumulant EVaR Tail Budgeting
- **Features**: F218.1
- **Files**: `src/risk/unified_portfolio_allocator.py`, `src/risk/portfolio_allocator.py`
- **Tests**: `tests/test_phase49_risk.py`, `tests/test_phase48_risk.py` (backward compatibility)
- **Role**: Risk Allocation Specialist (`teamwork_preview_worker` with Explorer guidance)

### Milestone 3 (M3): Microstructure L3 Spacetime Hydrodynamics & Preemptive OMS
- **Features**: F219.1, F219.2
- **Files**: `src/core/fast_lob_engine.py`, `src/execution/smart_order_router.py`, `src/execution/oms_engine.py`
- **Tests**: `tests/test_phase49_oms.py`, `tests/test_phase48_oms.py` (backward compatibility)
- **Role**: Microstructure OMS Specialist (`teamwork_preview_worker` with Explorer guidance)

### Milestone 4 (M4): Verification Benchmarking, Test Suites, Report Sync & Docs
- **Features**: F220
- **Files**: `trading_system/scripts/benchmark_phase49_quant_performance.py`, `tests/test_phase49_*.py`, reports, `AGENTS.md`, `PROJECT.md`
- **Role**: Quant Verification Specialist (`teamwork_preview_worker`), followed by Reviewer, Adversarial Challenger, and Forensic Auditor.

---

## Acceptance Criteria Targets
1. Net Expected Return $\ge 167.95\%$ (Target: 167.99%)
2. Sharpe Ratio $\ge 32.75$ (Target: 32.78)
3. MDD strictly $\le -0.00001\%$ across all 5 markets
4. Trading & Friction Costs $\le 0.0000001875\text{ bps}$ ($-50\%$)
5. Execution Slippage $\le 0.00000015625\text{ bps}$ ($-50\%$)
6. Top-Decile Alpha Spread $\ge 144.80\%$ (Target: 144.82%)
7. Win Rate: $100.0\%$ (leakage $< 10^{-120}$)
8. 100% test pass across all `test_phase49_*.py` and regression test suites.
