# Project: Phase 20 Quant Enhancement (v27 Production Master)

## Architecture
- **Data & Signal Layer**: `src/ai/ensemble_scorer.py` and `src/ai/factor_suppression.py` calculate 37-strategy factor signals, apply 44th-order Tetracontatetragonal deadband (F100.2), apply 15th-order ultra-convex rank warping (F100.1), and apply Perfectoid Space & Prismatic Cohomology factor coupler (F99) for version >= 20.
- **Risk Allocation Layer**: `src/risk/unified_portfolio_allocator.py` and `src/risk/portfolio_allocator.py` blend 4 models (BL, HERC, RP, CVaR) on the Fisher-Rao Riemannian manifold using Lurie Spectral Algebraic Geometry barycenters (F101.1) and budget tail risk using 16th-order cumulant expansion Ultra-Transcendent EVaR.
- **Microstructure OMS Layer**: `src/core/fast_lob_engine.py` implements Kerr-Newman-AdS black hole spacetime L3 hydrodynamics (F101.2). `src/execution/smart_order_router.py` enforces maker floor 0.00001, ATS 99.97%, Anti-Gaming 99.99%. `src/execution/oms_engine.py` enforces preemptive micro-tick shading `-0.997 * spread * (h - 0.06)` for Hawkes intensity $h > 0.06$.
- **Verification & Reporting Layer**: `trading_system/scripts/benchmark_phase20_quant_performance.py` (F102) evaluates 15 core metrics across 5 global markets (KOSPI, KOSDAQ, S&P 500, NASDAQ, RUSSELL 2000). Synchronizes 3 standard tables into `reports/` and `trading_system/result/`. `tests/test_phase20_*.py` executes dedicated unit, integration, and stress test suites. `AGENTS.md` records Key Files and Requirements History (R36).

## Feature Inventory
Every feature from the Survey phase appears here with its assigned milestone.
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | F99 | Perfectoid Space & Prismatic Cohomology factor coupler in ensemble_scorer.py and factor_suppression.py | M1 | ORIGINAL_REQUEST §R1 |
| 2 | F100.1 | 15th-order ultra-convex rank warping function g_v20(r) = 0.50 + 1.04 * r * exp(gamma_top * r^15) | M1 | ORIGINAL_REQUEST §R1 |
| 3 | F100.2 | 44th-order Tetracontatetragonal (alpha=44.0) hyperbolic deadband with noise leakage < 10^-24 | M1 | ORIGINAL_REQUEST §R1 |
| 4 | F100.3 | Version branching (version >= 20) across ensemble_scorer.py & factor_suppression.py | M1 | ORIGINAL_REQUEST §R1 |
| 5 | F101.1 | Lurie Spectral AG Fisher-Rao manifold barycenter blending for 4-model allocation (version >= 20) | M2 | ORIGINAL_REQUEST §R2 |
| 6 | F101.1.2 | 16th-order cumulant expansion Ultra-Transcendent EVaR tail risk budgeting | M2 | ORIGINAL_REQUEST §R2 |
| 7 | F101.2 | Kerr-Newman-AdS black hole spacetime L3 orderbook hydrodynamics model | M3 | ORIGINAL_REQUEST §R3 |
| 8 | F101.2.2 | Maker floor 0.00001 in smart_order_router.py | M3 | ORIGINAL_REQUEST §R3 |
| 9 | F101.2.3 | Tick shading -0.997 * spread * (h - 0.06), ATS routing 99.97%, Anti-Gaming MinQty 99.99% | M3 | ORIGINAL_REQUEST §R3 |
| 10 | F102 | 5-Market 15-Metric quantitative benchmark evaluation script benchmark_phase20_quant_performance.py | M4 | ORIGINAL_REQUEST §R4 |
| 11 | F102.2 | Dedicated test suite tests/test_phase20_*.py (100% pass) | M4 | ORIGINAL_REQUEST §R4 |
| 12 | F102.3 | 3 standard reporting tables sync to reports/ & trading_system/result/ | M4 | ORIGINAL_REQUEST §R4 |
| 13 | F102.4 | AGENTS.md Key Files and Requirements History (R36) update | M4 | ORIGINAL_REQUEST §R4 |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | M1: Alpha Signal Specialist (R1) | F99 Perfectoid Coupler, F100.1 15th-order rank warping, F100.2 44th-order deadband, version >= 20 branching in ensemble_scorer.py & factor_suppression.py | Survey completed | IN_PROGRESS (cdae1d70-2fca-4c17-8a82-5bb65a712154) |
| 2 | M2: Risk Allocation Specialist (R2) | F101.1 Lurie Spectral AG barycenter, 16th-order Ultra-Transcendent EVaR in unified_portfolio_allocator.py & portfolio_allocator.py | M1 interface defined | IN_PROGRESS (57dc7aeb-ceef-4117-942c-dd3bb17d79aa) |
| 3 | M3: Microstructure OMS Specialist (R3) | F101.2 Kerr-Newman-AdS L3 in fast_lob_engine.py, maker floor 0.00001 in smart_order_router.py, tick shading -0.997 * spread * (h - 0.06), ATS 99.97%, MinQty 99.99% in oms_engine.py | None (independent) | IN_PROGRESS (1a5e9052-abad-4748-b40c-b83452f3fe17) |
| 4 | M4: Quant Verification Specialist (R4) | benchmark_phase20_quant_performance.py (F102), tests/test_phase20_*.py, reports sync, AGENTS.md update, Victory Auditor verification | M1, M2, M3 | PLANNED |

## Interface Contracts

### M1: Alpha Signal Interface Contract
- `PerfectoidPrismaticCoupler.compute(pillar_scores, theta_0=0.24, kappa_prism=2.40, lambda_prism=0.14, lambda_tilt=0.06, lambda_frob=0.04, lambda_nygaard=0.02, epsilon_reg=1e-6) -> Dict[str, Any]`
  - Returns keys: `h_prism`, `z_prism`, `e_prism`, `h_decay`, `FERI_v20`, `Z_prism`, `E_prism`, `h_perfectoid`, `z_perfectoid`, `e_perfectoid`, `h_prismatic`, `z_prismatic`, `e_prismatic`.
- `compute_phase20_hyperconvex_rank_modulation(ranks, gamma_top=1.0, z_denoised=None) -> Union[pd.Series, np.ndarray, float]`
  - Pos: `0.50 + 1.04 * r * exp(gamma_top * r^15)`. Neg: `1.35 - 1.00 * r`.
- `apply_tetracontatetragonal_hyperbolic_deadband(scores_centered, delta_noise=0.035, delta_neg=None, alpha_pos=44.0, alpha_neg=None, regime=None) -> Union[pd.Series, np.ndarray, float]`
  - Leakage for $|z| \le 0.005$ is $< 10^{-24}$.
- `EnsembleScoringEngine.combine_predictions(..., version=20)` and `apply_smooth_noise_deadband(..., version=20)`.

### M2: Risk Allocation Interface Contract
- `UnifiedPortfolioAllocator.compute_lurie_spectral_ag_fisher_rao_barycenter_blend(model_weights, max_iter=50, tol=1e-6, step_size=0.50) -> Dict[str, float]`
  - Metric weights: `[1.80, 1.45, 1.40, 2.15]`.
- `UnifiedPortfolioAllocator.compute_ultra_transcendent_evar_risk_measure(returns, alpha=0.05, ...) -> Dict[str, Any]`
  - 16th-cumulant expansion: $16! = 20,922,789,888,000$, $\xi_{16} = 0.60$.
  - Returns key `ultra_transcendent_evar_value` (and alias `ultra_transcendent_evar`).
- `PortfolioAllocator` exposes static methods and aliases matching `UnifiedPortfolioAllocator`.

### M3: Microstructure OMS Interface Contract
- `FastOrderBookMatchingEngine.compute_kerr_newman_ads_queue_acceleration(charge_parameter=0.5, spin_parameter=0.5, ads_radius=10.0, ...) -> Dict[str, float]`
  - Returns keys: `kn_ads_hydrodynamic_acceleration`, `kn_ads_accelerated_qi`, `kn_ads_micro_price`, `kn_ads_tidal_force`, `frame_dragging_omega`, `ads_radius_L`, etc.
- `DeepHawkesArrivalProcess.compute_preemptive_dark_routing`: Preemptive ATS cap $= 0.9997$ for version >= 20.
- `SmartOrderRouter`:
  - Lit maker floor $= 0.00001$ when `is_phase20 and gamma_toxic > 0.80`.
  - Max dark cap $= 0.9997$ when `is_phase20`.
  - Anti-gaming MinQty cap $= 0.9999$ when `is_phase20`.
- `ExecutionOMSEngine` & `AlmgrenChrissScheduler`:
  - `calculate_peg_limit_price`: when `version >= 20` and $h_{val} > 0.06$, `hawkes_shift = -direction * 0.997 * spr * (h_val - 0.06)`.

### M4: Quant Verification Interface Contract
- Script: `trading_system/scripts/benchmark_phase20_quant_performance.py`
  - Classes: `Phase20QuantBenchmarkEngine`, `QuantBenchmarkEnginePhase20`
  - CLI: `--report-all`, `--run-all`, `--market <MKT>`
  - Reports: `reports/quant_benchmark_comparison_phase20.md`, `trading_system/result/quant_benchmark_comparison_phase20.md`, `reports/quant_benchmark_comparison.md`
- Tests: `tests/test_phase20_signal_enhancement.py`, `tests/test_phase20_microstructure_oms.py`, `tests/test_phase20_quant.py`, `tests/test_phase20_challenger_stress.py`.

## Code Layout
- `trading_system/src/ai/ensemble_scorer.py`: F99, F100.1, F100.2 static bindings, `version >= 20` branching.
- `trading_system/src/ai/factor_suppression.py`: F100.2 deadband, F99 imports/aliases.
- `trading_system/src/risk/unified_portfolio_allocator.py`: F101.1 barycenter, 16th-order EVaR, ambiguity tilting, headroom redistribution.
- `trading_system/src/risk/portfolio_allocator.py`: Objective 16 delegation static methods.
- `trading_system/src/core/fast_lob_engine.py`: F101.2 Kerr-Newman-AdS L3 hydrodynamics, Hawkes 0.9997 cap.
- `trading_system/src/execution/smart_order_router.py`: 0.00001 maker floor, 0.9997 ATS, 0.9999 MinQty.
- `trading_system/src/execution/oms_engine.py`: -0.997 * spread * (h - 0.06) tick shading.
- `trading_system/scripts/benchmark_phase20_quant_performance.py`: F102 benchmark engine.
- `tests/test_phase20_*.py`: Dedicated test suites.
- `reports/quant_benchmark_comparison_phase20.md` & `trading_system/result/quant_benchmark_comparison_phase20.md`: 3 standard tables.
- `AGENTS.md`: Key Files line 222 & Requirements History R36.
