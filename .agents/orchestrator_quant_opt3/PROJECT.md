# Project: 3rd Deep Quantitative Enhancement

## Architecture
Multi-factor quantitative trading system for 5 markets (SP500, NASDAQ, RUSSELL2000, KOSPI, KOSDAQ) integrating 37 quantitative strategies.

```
[37-Strategy Factor Engines]
          │
          ▼
[CrossSectionalScoreNormalizer] (Winsorized Gaussian CDF & Percentile Rank)
          │
          ▼
[EnsembleScoringEngine] (Markov 7-State 2D Regime, Adaptive Alpha Smoothing, Half-Life Decay, Inertia & 37-Strategy Synergy)
          │
          ▼
[UnifiedPortfolioAllocator] (4-Model Dynamic Blending: BL + HERC + RP + EVT-CVaR, Clayton Copula, Dark-Adjusted Gatheral Impact, Leland Bands)
          │
          ▼
[ExecutionOMSEngine] (8 Safety Gates, Almgren-Chriss Trajectory, 3-Tier SOR Venue Routing, Dynamic Dark Probing, OBI Peg Pricing)
          │
          ▼
[SmartOrderRouter & Fast LOB] (Dark ATS Midpoint -> Primary Peg Maker -> Lit Sweeper)
```

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| F01 | 7-State 2D Regime Matrix | Add dedicated `CRISIS` base weights dictionary (sum = 1.0000) eliminating fallback to `SIDEWAYS_LOW_VOL` | M1 | Survey Explorer 1 |
| F02 | Markov Regime Soft-Blending | Posterior regime probability weighting $\mathbf{w}_{base}(t) = \sum \pi_{t, m} \mathbf{w}^{(m)}$ | M1 | Survey Explorer 1 |
| F03 | Continuous TV-Distance & VIX Entropy Smoothing | Dynamic weight smoothing parameter $\alpha_t$ modulated by Total Variation distance and VIX entropy | M1 | Survey Explorer 1 |
| F04 | Live Alpha Convolutional Decay Filter | Hook `apply_exponential_decay_filter` and `apply_rank_ic_decay_calibration` into live pipeline with state caching | M1 | Survey Explorer 1 |
| F05 | Trend Inertia vs Crash Protection | Factor rank autocorrelation boost in `BULL_LOW_VOL` vs crash-protected momentum in `BULL_HIGH_VOL` | M1 | Survey Explorer 1 |
| F06 | 37-Strategy 4-Pillar Synergy & S-Curve | Expand bilinear synergy clustering from 29 to all 37 strategies; regime-adaptive Bessembinder tail power-law | M1 | Survey Explorer 1 |
| F07 | Single-Stage Entropy Program Activation | Enable `solve_single_stage_entropy_allocation` when $N \ge 10$ for optimal convex factor redundancy | M1 | Survey Explorer 1 |
| F08 | Orthogonalizer Singularity Protection | Guard `FactorOrthogonalizerEngine` against zero-variance singular columns under partial missingness | M1 | Survey Explorer 1 |
| F09 | Continuous 4-Model Regime Blending | Continuous Markov/VIX/Crisis weighting $[w_{BL}, w_{HERC}, w_{RP}, w_{CVaR}]$ with 5-day EMA smoothing | M2 | Survey Explorer 2 |
| F10 | EVT Clayton Copula Tail Covariance Injection | Inject Clayton copula tail-stressed covariance $\Sigma_{stressed}$ and dynamic alpha tilt $\lambda_\alpha(R)$ in CVaR | M2 | Survey Explorer 2 |
| F11 | Dark-Pool-Adjusted Gatheral Impact | Effective impact parameter $\kappa_{eff, i} = \kappa_0(1 - 0.75 \delta_{dark, i})$ allowing faster convergence | M2 | Survey Explorer 2 |
| F12 | Dynamic Dark Probing Ratio ($\delta_{dark}$) | Strategy #30 driven dark pool probing ratio $\delta_{dark} \in [0.10, 0.75]$ in OMS order planning | M2 | Survey Explorer 2 |
| F13 | 3-Tier Multi-Venue SOR Routing in OMS | Attach 3-tier SOR routing legs (`DARK_ATS_MIDPOINT`, `PRIMARY_EXCHANGE_MAKER`, `LIT_EXCHANGE_SWEEPER`) and bps savings | M2 | Survey Explorer 2 |
| F14 | HFT OBI-Driven Midpoint Peg Pricing | Strategy #23 Orderbook Imbalance ($OBI$) and toxicity driven midpoint peg limit pricing in Almgren-Chriss | M2 | Survey Explorer 2 |
| F15 | Phase 3 Benchmark Generator Script | `trading_system/scripts/benchmark_phase3_quant_performance.py` for automated multi-market simulation | M3 | Survey Explorer 3 |
| F16 | Phase 3 Comprehensive Markdown Report | `reports/quant_benchmark_comparison_phase3.md` with 3-tier executive, market-by-market, and attribution tables | M3 | Survey Explorer 3 |
| F17 | Full Pytest Regression Verification | Verify 100% pass rate across all 2,230+ tests in `tests/` (`.venv\Scripts\pytest.exe tests/ -v`) | M3 | Survey Explorer 3 |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | 37-Strategy Dynamic Alpha Weights & Nonlinear Factor Coupling | F01, F02, F03, F04, F05, F06, F07, F08 | None | DONE |
| M2 | Portfolio 4-Model Dynamic Blending & Darkpool/HFT OMS Optimization | F09, F10, F11, F12, F13, F14 | M1 | DONE |
| M3 | Quantitative Benchmark Comparison & Regression Verification | F15, F16, F17 | M1, M2 | IN_PROGRESS |

## Interface Contracts

### M1 ↔ M2 Contract
- `EnsembleScoringEngine.calculate_ensemble_score` and `combine_predictions` output standard DataFrame containing:
  * `symbol`: str
  * `market`: str
  * `ensemble_score`: float in [0.0, 1.0]
  * `ensemble_expected_return`: float in [0.0, 50.0]
  * `friction_cost_pct`: float
  * `regime_multiplier`: float
  * `darkpool_score`: float in [0.0, 1.0] (from Strategy #30)
  * `microstructure_score`: float in [0.0, 1.0] (from Strategy #23)
  * `obi`: float in [-1.0, 1.0] (Orderbook Imbalance)
- `UnifiedPortfolioAllocator.allocate` and `ExecutionOMSEngine.generate_order_plan` consume these standardized columns without breaking backwards compatibility.

### M2 ↔ M3 Contract
- `ExecutionOMSEngine.generate_order_plan` attaches:
  * `sor_routing`: Dict containing `dark_ats_midpoint`, `primary_exchange_maker`, `lit_exchange_sweeper`, and `expected_cost_saving_bps`.
- Benchmark generator scripts can read simulated trade logs and calculate accurate slippage reduction and friction drag.

## Code Layout
- `trading_system/src/ai/ensemble_scorer.py`: Ensemble scoring, 2D regime matrix, Markov smoothing, half-life decay, factor synergy
- `trading_system/src/ai/factor_orthogonalizer.py`: PCA-ZCA whitening and Marchenko-Pastur bound
- `trading_system/src/ai/factor_suppression.py`: VIF suppression and single-stage entropy program
- `trading_system/src/risk/unified_portfolio_allocator.py`: 4-Model blending, Gatheral impact, Leland buffer bands
- `trading_system/src/risk/portfolio_allocator.py`: EVT-CVaR, Clayton copula tail covariance
- `trading_system/src/execution/oms_engine.py`: 8 safety gates, Almgren-Chriss scheduler, order planning
- `trading_system/src/execution/smart_order_router.py`: 3-tier multi-venue routing
- `trading_system/scripts/benchmark_phase3_quant_performance.py`: Benchmark comparison generator
- `reports/quant_benchmark_comparison_phase3.md`: Official benchmark comparison report
- `tests/test_m1_quant_enhancements.py`, `tests/test_m2_portfolio_execution.py`: Dedicated test suites
