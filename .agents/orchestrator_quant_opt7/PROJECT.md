# Project: Phase 7 Zenith Quantitative Enhancements (7차 심화 퀀트 개선, v14)

## Architecture
- **Multi-Factor Alpha Layer**: 37 diversification strategies mapped into 5 disjoint orthogonal pillars (`val`, `mom`, `flow`, `cat`, `net`).
- **High-Order Tensor & Convexity Engine**: 5-pillar economically-weighted trilinear tensors, pillar harmony regularization ($\mathcal{H}_{\text{pillar}} = \exp(-1.20 \text{CV}_\psi^2)$), Merton jump-diffusion regime weight blending, asymmetric directional Markov departure penalties, and true $C^\infty$ quintic noise deadband.
- **Portfolio Allocation Layer**: 4-model blending (Black-Litterman, HERC, Risk Parity, EVT-CVaR) enhanced with Archimedean Clayton ($\lambda_L$) & Gumbel ($\lambda_U$) copula tail dependency log-odds updates, cross-asset copula lower-tail contagion drag in Downside Sortino Tilting, and tail-stressed Euler CCVaR budgeting with residual risk headroom redistribution.
- **Microstructure & Institutional Execution Layer**: Physical distance-decayed Level-3 Queue Imbalance ($\text{QI}_{\text{L3}}^*$), Bivariate Hawkes directional arrival intensity imbalance ($\Delta \lambda_{\text{dir}}$) with toxicity-dampened peg concessions and toxic shading offsets, and SmartOrderRouter preemption to darkpool ATS with maker ratio floor at 0.10.
- **Benchmarking & Reporting Layer**: Phase 7 quantitative benchmark engine evaluating 15 institutional metrics across 5 equity markets (KOSPI, KOSDAQ, S&P 500, NASDAQ, RUSSELL 2000), using Phase 6 Apex (v13) as the baseline and generating 3-way synchronized markdown reports.

## Feature Inventory
Every feature from the Survey phase is mapped to a designated milestone.
| # | Feature | Description | Milestone | Source |
|---|---|---|---|---|
| F47 | 5-Pillar Economically-Weighted Trilinear Tensors & Jump-Diffusion Mixture | Economically-weighted triplet contractions ($\Omega_{\text{tri}}(\text{val}, \text{mom}, \text{flow}) = 1.40 w_{\text{tri}}$), Pillar Harmony Regularizer $\mathcal{H}_{\text{pillar}}$, Bull Low Vol cap expansion to 0.220 ($1.220\times$), and Merton Jump-Diffusion regime transition base weight mixture when $d_{TV} > 0.25$. | M1 | Survey R1 |
| F48 | Directional Markov Departure Penalty & True Quintic Deadband | Directional volatility Markov stationary departure penalty $\kappa_{\text{Markov}}(S_{\text{vol}}) \in [0.25, 0.45]$, true $C^\infty$ quintic-hyperbolic deadband filter $z \cdot \tanh((|z|/\delta)^5)$, and Quartic Rank Modulation $g_{\text{v7}}(r)$ expanding Top-Decile spread by $+18\%\sim+22\%$. | M1 | Survey R1 |
| F49 | 4-Model Copula Tail Dependency Blending & Tail-Stressed Euler CCVaR | Archimedean Clayton ($\lambda_L$) & Gumbel ($\lambda_U$) copula log-odds updates $\Delta \ell_{\text{copula}}$, cross-asset copula lower-tail contagion drag in Sortino tilting, and tail-stressed Euler CCVaR budgeting with residual risk headroom redistribution. | M2 | Survey R2 |
| F50 | Level-3 Queue Imbalance & Hawkes Directional Toxicity Pegging | Distance-decayed and fragmentation-adjusted Queue Imbalance ($\text{QI}_{\text{L3}}^*$), Bivariate Hawkes arrival intensity imbalance ($\Delta \lambda_{\text{dir}}$) and directional toxicity ($\gamma_{\text{toxic}}$) pegging in `ExecutionOMSEngine` and `AlmgrenChrissScheduler`, and SOR lit queue exhaustion preemption. | M2 | Survey R2 |
| F51 | Phase 7 Quantitative Benchmark Performance Engine & Reports | 15-metric quantitative simulation engine (`benchmark_phase7_quant_performance.py`) modeling 5 markets, 5 unit/integration tests (`test_benchmark_phase7.py`), and 3-way synchronized reports. | M3 | Survey R3 |
| F52 | Full Repository Test Census & Zero-Regression Verification | Comprehensive 2,536+ test execution across 271 modules ensuring 100% pass rate, 0 regressions, and clean forensic audit. | M4 | Survey R3 |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|---|---|---|---|
| M1 | Dynamic Alpha Signal Synergy & Right-Tail Confidence 7th Deepening | F47, F48 | none | PLANNED |
| M2 | 4-Model Copula Portfolio Allocation & L3 Execution Friction Optimization | F49, F50 | none | PLANNED |
| M3 | Phase 7 Zenith Quantitative Benchmark Performance Engine & Reporting | F51 | M1, M2 | PLANNED |
| M4 | Full Repository Test Census & Zero-Regression Verification | F52 | M1, M2, M3 | PLANNED |

## Interface Contracts

### 1. `ensemble_scorer.py` & `factor_suppression.py` (M1)
- `compute_quint_pillar_tensor_synergy(scores_df, regime=None, kappa=8.0, regime_adaptive_cap=True, version=7, ...)`:
  - For `version >= 7`: activates economically-weighted triplets and $\mathcal{H}_{\text{pillar}}$, sets Bull Low Vol cap to 0.220.
  - For `version <= 6`: preserves existing Phase 6 cap (0.180) and uniform weighting.
- `get_regime_adaptive_half_lives(regime, transition_velocity=0.0, current_entropy=None, base_entropy=1.5, version=7, ...)`:
  - For `version >= 7`: modulates $\kappa_{\text{Markov}}(S_{\text{vol}}) = 0.25(1 + 0.80 \max(0, S_{\text{vol}}))$.
- `apply_quintic_hyperbolic_deadband(z, delta, alpha=5.0, ...)`:
  - Standalone in `factor_suppression.py`, aliased or integrated into `apply_smooth_noise_deadband`.
- `apply_bessembinder_convex_power_law(score, regime=None, version=7, ...)`:
  - Quartic rank modulation $g_{\text{v7}}(r) = 0.60 + 0.25 r + 0.25 r^2 + 0.40 r^3 + 0.35 r^4$ for version 7.

### 2. `unified_portfolio_allocator.py` & `fast_lob_engine.py` & `oms_engine.py` (M2)
- `compute_information_theoretic_blend_weights(..., copula_tail_dep=None, version=7)`:
  - If `copula_tail_dep` is provided (tuple of `(lambda_L, lambda_U)` or dict), updates log-odds for BL, HERC, RP, CVaR.
- `optimize_multi_model_blend(..., cross_asset_copula_lower_tail=None, ...)`:
  - Downside Sortino Tilting includes copula lower-tail contagion penalty.
  - Euler CCVaR budgeting uses tail-stressed covariance $\Sigma_{\text{eff}}$ and residual headroom weighted redistribution.
- `FastOrderBookMatchingEngine.compute_l3_queue_imbalance(decay_factor=0.35, distance_weighting=True)`:
  - Calculates distance-decayed $\text{QI}_{\text{L3}}^*$.
- `calculate_peg_limit_price(..., hawkes_toxicity=None, hawkes_arrival_imbalance=None, queue_imbalance=None)`:
  - Implemented with bit-level mathematical parity in both `ExecutionOMSEngine` and `AlmgrenChrissScheduler`.
- `SmartOrderRouter.route_order(..., lit_queue_imbalance=None)`:
  - Routes up to 75% to dark ATS on heavy lit queue exhaustion.

### 3. `benchmark_phase7_quant_performance.py` (M3)
- Command-line interface: `--seed 42 --output reports/quant_benchmark_comparison_phase7.md`
- Generates 3 synchronized files and calculates 15 institutional metrics across 5 equity markets.

## Code Layout
- `src/ai/ensemble_scorer.py`: Alpha combination, tensor synergy, rank modulation, jump-diffusion weights.
- `src/ai/factor_suppression.py`: Quintic-hyperbolic noise deadband.
- `src/risk/unified_portfolio_allocator.py`: Copula tail dependency allocation & Euler CCVaR budgeting.
- `src/core/fast_lob_engine.py`: Level-3 Queue Imbalance & Bivariate Hawkes arrival processes.
- `src/execution/oms_engine.py`: Micro-price pegging with toxicity damping.
- `src/execution/smart_order_router.py`: Darkpool ATS preemption and toxicity maker compression.
- `src/execution/almgren_chriss.py`: Synchronized peg pricing parity.
- `trading_system/scripts/benchmark_phase7_quant_performance.py`: Phase 7 simulation benchmark engine.
- `tests/test_phase7_signal_enhancement.py`: Phase 7 M1 feature tests.
- `tests/test_phase7_portfolio_execution.py`: Phase 7 M2 feature tests.
- `tests/test_benchmark_phase7.py`: Phase 7 M3 benchmark tests.
- `reports/quant_benchmark_comparison_phase7.md`: Master Phase 7 comparison report.
