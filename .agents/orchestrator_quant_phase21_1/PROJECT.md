# Project: Phase 21 Quant Enhancement (v28 Production Master)

## Architecture
- **Data & Signal Layer**: `src/ai/ensemble_scorer.py` and `src/ai/factor_suppression.py` calculate 37-strategy factor signals, apply 48th-order Octatetracontagonal deadband (F104.2), apply 16th-order ultra-convex rank warping (F104.1), and apply Derived Motivic Homotopy Type Theory factor coupler (F103) for `version >= 21`.
- **Risk Allocation Layer**: `src/risk/unified_portfolio_allocator.py` and `src/risk/portfolio_allocator.py` blend 4 models (BL, HERC, RP, CVaR) on the Fisher-Rao Riemannian manifold using Lurie Chromatic Homotopy Theory barycenters (F105.1) and budget tail risk using 17th-order cumulant expansion Hyper-Transcendent EVaR.
- **Microstructure OMS Layer**: `src/core/fast_lob_engine.py` implements Kerr-Newman-AdS-dS cosmological black hole spacetime L3 hydrodynamics (F105.2). `src/execution/smart_order_router.py` enforces maker floor 0.000005, ATS 99.98%, Anti-Gaming 99.995%. `src/execution/oms_engine.py` enforces preemptive micro-tick shading `-0.998 * spread * (h - 0.05)` for Hawkes intensity $h > 0.05$.
- **Verification & Reporting Layer**: `trading_system/scripts/benchmark_phase21_quant_performance.py` (F106) evaluates 15 core metrics across 5 global markets (KOSPI, KOSDAQ, S&P 500, NASDAQ, RUSSELL 2000). Synchronizes 3 standard tables into `reports/` and `trading_system/result/`. `tests/test_phase21_*.py` executes dedicated unit, integration, and stress test suites. `AGENTS.md` records Key Files and Requirements History (R37).

## Feature Inventory
Every feature from the Survey phase appears here with its assigned milestone.
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | F103 | Derived Motivic Homotopy Type Theory factor coupler in ensemble_scorer.py and factor_suppression.py | M1 | ORIGINAL_REQUEST §R1 |
| 2 | F104.1 | 16th-order ultra-convex rank warping function g_v21(r) = 0.50 + 1.06 * r * exp(gamma_top * r^16) | M1 | ORIGINAL_REQUEST §R1 |
| 3 | F104.2 | 48th-order Octatetracontagonal (alpha=48.0) hyperbolic deadband with noise leakage < 10^-26 | M1 | ORIGINAL_REQUEST §R1 |
| 4 | F104.3 | Version branching (version >= 21) across ensemble_scorer.py & factor_suppression.py | M1 | ORIGINAL_REQUEST §R1 |
| 5 | F105.1 | Lurie Chromatic Homotopy Theory Fisher-Rao manifold barycenter blending for 4-model allocation (version >= 21) | M2 | ORIGINAL_REQUEST §R2 |
| 6 | F105.1.2 | 17th-order cumulant expansion Hyper-Transcendent EVaR tail risk budgeting | M2 | ORIGINAL_REQUEST §R2 |
| 7 | F105.2 | Kerr-Newman-AdS-dS cosmological black hole spacetime L3 orderbook hydrodynamics model | M3 | ORIGINAL_REQUEST §R3 |
| 8 | F105.2.2 | Maker floor 0.000005 in smart_order_router.py | M3 | ORIGINAL_REQUEST §R3 |
| 9 | F105.2.3 | Dark pool routing 99.98% ATS, Anti-Gaming MinQty 99.995%, tick shading -0.998 * spread * (h - 0.05) | M3 | ORIGINAL_REQUEST §R3 |
| 10 | F106 | 5-Market 15-Metric quantitative benchmark evaluation script benchmark_phase21_quant_performance.py | M4 | ORIGINAL_REQUEST §R4 |
| 11 | F106.2 | Dedicated test suite tests/test_phase21_*.py (100% pass) | M4 | ORIGINAL_REQUEST §R4 |
| 12 | F106.3 | 3 standard reporting tables sync to reports/ & trading_system/result/ | M4 | ORIGINAL_REQUEST §R4 |
| 13 | F106.4 | AGENTS.md Key Files and Requirements History (R37) update | M4 | ORIGINAL_REQUEST §R4 |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | M1: Alpha Signal Specialist (R1) | F103 Derived Motivic Coupler, F104.1 16th-order rank warping, F104.2 48th-order deadband, version >= 21 branching in ensemble_scorer.py & factor_suppression.py | Survey completed | PLANNED |
| 2 | M2: Risk Allocation Specialist (R2) | F105.1 Lurie Chromatic barycenter, 17th-order Hyper-Transcendent EVaR in unified_portfolio_allocator.py & portfolio_allocator.py | M1 interface defined | PLANNED |
| 3 | M3: Microstructure OMS Specialist (R3) | F105.2 Kerr-Newman-AdS-dS L3 in fast_lob_engine.py, maker floor 0.000005 in smart_order_router.py, tick shading -0.998 * spread * (h - 0.05), ATS 99.98%, MinQty 99.995% in oms_engine.py | None (independent) | PLANNED |
| 4 | M4: Quant Verification Specialist (R4) | benchmark_phase21_quant_performance.py (F106), tests/test_phase21_*.py, reports sync, AGENTS.md update, Victory Auditor verification | M1, M2, M3 | PLANNED |

## Interface Contracts

### M1: Alpha Signal Interface Contract
- `DerivedMotivicHomotopyTypeTheoryCoupler.compute(pillar_scores, theta_0=0.25, kappa_motivic=2.60, lambda_motivic=0.16, lambda_univalent=0.07, lambda_frob=0.045, lambda_slice=0.025, epsilon_reg=1e-6) -> Dict[str, Any]`
  - Returns keys: `h_motivic`, `z_motivic`, `e_motivic`, `h_decay`, `FERI_v21`, `Z_motivic`, `E_motivic`, `h_derived`, `z_derived`, `e_derived`, `h_homotopy`, `z_homotopy`, `e_homotopy`.
  - Aliases: `DerivedMotivicCoupler`, `MotivicHomotopyTypeTheoryCoupler`, `MotivicHomotopyCoupler`.
- `compute_phase21_hyperconvex_rank_modulation(ranks, gamma_top=1.0, z_denoised=None) -> Union[pd.Series, np.ndarray, float]`
  - Pos: `0.50 + 1.06 * r * exp(gamma_top * r^16)`. Neg: `1.35 - 1.00 * r`.
- `apply_octatetracontagonal_hyperbolic_deadband(scores_centered, delta_noise=0.035, delta_neg=None, alpha_pos=48.0, alpha_neg=None, regime=None) -> Union[pd.Series, np.ndarray, float]`
  - Leakage for $|z| \le 0.005$ is $< 10^{-26}$.
- `EnsembleScoringEngine.combine_predictions(..., version=21)` and `apply_smooth_noise_deadband(..., version=21)`.
- In `compute_quint_pillar_tensor_synergy`: Version $\ge 21$ adds `+ 0.75 * h_motivic * z_motivic` to `harmony_factor`.

### M2: Risk Allocation Interface Contract
- `UnifiedPortfolioAllocator.compute_lurie_chromatic_homotopy_fisher_rao_barycenter_blend(model_weights, max_iter=50, tol=1e-6, step_size=0.50) -> Dict[str, float]`
  - Metric weights: `[1.90, 1.50, 1.45, 2.30]`.
  - Aliases: `compute_chromatic_homotopy_fisher_rao_barycenter_blend`, `compute_lurie_chromatic_barycenter_blend`.
- `UnifiedPortfolioAllocator.compute_hyper_transcendent_evar_risk_measure(returns, alpha=0.05, ...) -> Dict[str, Any]`
  - 17th-cumulant expansion: $17! = 355,687,428,096,000$, $\xi_{17} = 0.65$.
  - Returns key `hyper_transcendent_evar_value` (and alias `hyper_transcendent_evar`).
- `PortfolioAllocator` exposes static methods and aliases matching `UnifiedPortfolioAllocator`.

### M3: Microstructure OMS Interface Contract
- `FastOrderBookMatchingEngine.compute_kerr_newman_ads_ds_queue_acceleration(charge_parameter=0.5, spin_parameter=0.5, ads_radius=10.0, ds_radius=20.0, cosmological_lambda=None, ...) -> Dict[str, float]`
  - Returns keys: `kn_ads_ds_hydrodynamic_acceleration`, `kn_ads_ds_accelerated_qi`, `kn_ads_ds_micro_price`, `kn_ads_ds_tidal_force`, `frame_dragging_omega`, `cosmological_lambda`, etc.
  - Aliases: `compute_kerr_newman_ads_ds_acceleration`.
- `DeepHawkesArrivalProcess.compute_preemptive_dark_routing`: Preemptive ATS cap $= 0.9998$ for version >= 21.
- `SmartOrderRouter`:
  - Lit maker floor $= 0.000005$ when `is_phase21 and gamma_toxic > 0.80`.
  - Max dark cap $= 0.9998$ when `is_phase21`.
  - Anti-gaming MinQty cap $= 0.99995$ when `is_phase21`.
- `ExecutionOMSEngine` & `AlmgrenChrissScheduler`:
  - `calculate_peg_limit_price`: when `version >= 21` and $h_{val} > 0.05$, `hawkes_shift = -direction * 0.998 * spr * (h_val - 0.05)`.

### M4: Quant Verification Interface Contract
- Script: `trading_system/scripts/benchmark_phase21_quant_performance.py`
  - Classes: `Phase21QuantBenchmarkEngine`, `QuantBenchmarkEnginePhase21`
  - Targets: Net Return $\ge 108.85\%$, Sharpe $\ge 15.92$, MDD $\le -0.028\%$, Friction $\le 0.055$ bps, Slippage $\le 0.004$ bps, Top-Decile Spread $\ge 79.8\%$.
  - CLI: `--report-all`, `--run-all`, `--market <MKT>`
  - Reports: `reports/quant_benchmark_comparison_phase21.md`, `trading_system/result/quant_benchmark_comparison_phase21.md`, `reports/quant_benchmark_comparison.md`
- Tests: `tests/test_phase21_signal_enhancement.py`, `tests/test_phase21_microstructure_oms.py`, `tests/test_phase21_quant.py`.
- `AGENTS.md` Key Files table line and Requirements History R37.

## Code Layout
- `trading_system/src/ai/ensemble_scorer.py`: F103, F104.1, F104.2 static bindings, `version >= 21` branching.
- `trading_system/src/ai/factor_suppression.py`: F104.2 deadband, F103 imports/aliases.
- `trading_system/src/risk/unified_portfolio_allocator.py`: F105.1 barycenter, 17th-order EVaR, ambiguity tilting, headroom redistribution.
- `trading_system/src/risk/portfolio_allocator.py`: Objective 17 delegation static methods.
- `trading_system/src/core/fast_lob_engine.py`: F105.2 Kerr-Newman-AdS-dS L3 hydrodynamics, Hawkes 0.9998 cap.
- `trading_system/src/execution/smart_order_router.py`: 0.000005 maker floor, 0.9998 ATS, 0.99995 MinQty.
- `trading_system/src/execution/oms_engine.py`: -0.998 * spread * (h - 0.05) tick shading.
- `trading_system/scripts/benchmark_phase21_quant_performance.py`: F106 benchmark engine.
- `tests/test_phase21_*.py`: Dedicated test suites.
- `reports/quant_benchmark_comparison_phase21.md` & `trading_system/result/quant_benchmark_comparison_phase21.md`: 3 standard tables.
- `AGENTS.md`: Key Files line & Requirements History R37.
