# Project: Release R171 Institutional Expansion & Compounding Elevation

## Architecture
The system operates as an institutional multi-factor, multi-model automated quantitative trading and execution platform covering 3,379 symbols across 5 major markets (KOSPI, KOSDAQ, S&P 500, NASDAQ, RUSSELL 2000).

```
                                      [Market Data & Knowledge Graph]
                                                     │
                                                     ▼
     ┌─────────────────────────────────────────────────────────────────────────────────────────────┐
     │ Milestone 1 (Phase 168): Advanced Alpha Feature Engineering (F820–F824)                     │
     │ - Kähler Manifold Holomorphic Geodesic Flow & Hierarchical Tucker Tree Tensor Alpha (F820)   │
     │ - Cellular Sheaf Laplacian & Quaternionic Hyperbolic Value Chain GNN (F821)                 │
     │ - Quadratic Volterra Fractional Hawkes Kernel & Cross-Market Microstructure (F822)          │
     │ - Arbitrage-Free SSVI Volatility Surface & 6th-Order Greeks (F823)                          │
     │ - Nonuple-Pillar Riemannian Whitening & Phase 168 Coupler Integration (F824)                │
     └──────────────────────────────────────────────┬──────────────────────────────────────────────┘
                                                    │ Alpha Signals
                                                    ▼
     ┌─────────────────────────────────────────────────────────────────────────────────────────────┐
     │ Milestone 2 (Phase 169): Risk Budgeting & Dynamic Allocation (F825–F829)                    │
     │ - Dual Tsallis-Rényi Entropy & Directional Ellipsoidal Wasserstein Robust Kelly (F825)       │
     │ - Compounding Gross Leverage Frontiers (up to 1.70x) & Factor Beta Neutralization (F826)     │
     │ - 8-Tier Protective Dynamic Gating & Contagion Defense (F827)                               │
     │ - High-Dimensional OAS Shrinkage & Top-200 Systematic Mode-Exempt RMT Filter (F828)         │
     │ - UnifiedPortfolioAllocator R171 Multi-Regime Master Blending (F829)                        │
     └──────────────────────────────────────────────┬──────────────────────────────────────────────┘
                                                    │ Target Weights & Leverage
                                                    ▼
     ┌─────────────────────────────────────────────────────────────────────────────────────────────┐
     │ Milestone 3 (Phase 170): Execution OMS, Microstructure & Parity (F830–F834)                │
     │ - Distributional Soft Actor-Critic (SAC) Downside CVaR Execution Agent (F830)               │
     │ - Fast Level-3 LOB Fee-Rebate Harvester & Nextrade ATS Midpoint Crossing (F831)             │
     │ - 5D Joseph-Stabilized Extended Closed-Loop Kalman Slippage Impact Filter (F832)            │
     │ - Multi-Asset Asymmetric Leland Dynamic No-Trade Buffer Bands (F833)                        │
     │ - Zero-Copy Lock-Free Execution Gateway with Gate 8 Synthetic Inverse Hedge (F834)          │
     │ - Paper Trading Conservation Law (Net Equity <= Gross Equity) & 100% SHA-256 Parity         │
     └──────────────────────────────────────────────┬──────────────────────────────────────────────┘
                                                    │ Certified Allocations & Trades
                                                    ▼
     ┌─────────────────────────────────────────────────────────────────────────────────────────────┐
     │ Milestone 4 (Phase 171): 30-Year Compounding Benchmark, Invariants & Dashboard (F835–F839)   │
     │ - Master 31Y Compounding Benchmark Elevation to Net CAGR ~71.50% (F835)                     │
     │ - 5/5 Canonical Crisis Defense Certification (1997, 2000, 2008, 2020, 2022 PASS) (F836)    │
     │ - Point-In-Time Integrity & Dynamic Filing Lag Enforcement (KRX 45d, SEC 40d) (F837)        │
     │ - Strict System Invariants: synthetic_rows == 0 (native int) (F838)                         │
     │ - 100% Dual-Tree SHA-256 Parity & Live Dashboard Deployment (< 500 KB) (F839)              │
     │ - Independent Verification Suite (tests/verify_production_master.py 39/39 PASS)             │
     └─────────────────────────────────────────────────────────────────────────────────────────────┘
```

## Feature Inventory
Every feature from Phases 168–171 is inventoried below with an assigned milestone:

| # | Feature ID | Feature Name & Description | Milestone | Source |
|---|------------|----------------------------|-----------|--------|
| 1 | F820 | Kähler Manifold Holomorphic Geodesic Flow & Hierarchical Tucker Tree Tensor Alpha | M1 | Survey |
| 2 | F821 | Cellular Sheaf Laplacian & Quaternionic Hyperbolic Value Chain GNN | M1 | Survey |
| 3 | F822 | Quadratic Volterra Fractional Hawkes Kernel & Cross-Market Microstructure | M1 | Survey |
| 4 | F823 | Arbitrage-Free SSVI Volatility Surface & 6th-Order Greeks | M1 | Survey |
| 5 | F824 | Nonuple-Pillar Riemannian Whitening & Phase 168 Coupler Integration | M1 | Survey |
| 6 | F825 | Dual Tsallis-Rényi Entropy & Directional Ellipsoidal Wasserstein Robust Kelly | M2 | Survey |
| 7 | F826 | Compounding Gross Leverage Frontiers (up to 1.70x) & Factor Beta Neutralization | M2 | Survey |
| 8 | F827 | 8-Tier Protective Dynamic Gating & Contagion Defense | M2 | Survey |
| 9 | F828 | High-Dimensional OAS Shrinkage & Top-200 Systematic Mode-Exempt RMT Filter | M2 | Survey |
| 10 | F829 | UnifiedPortfolioAllocator Release R171 Multi-Regime Integration | M2 | Survey |
| 11 | F830 | Distributional Soft Actor-Critic (SAC) Downside CVaR Execution Agent | M3 | Survey |
| 12 | F831 | Fast Level-3 LOB Fee-Rebate Harvester & Nextrade ATS Midpoint Crossing | M3 | Survey |
| 13 | F832 | 5D Joseph-Stabilized Extended Closed-Loop Kalman Slippage Impact Filter | M3 | Survey |
| 14 | F833 | Multi-Asset Asymmetric Leland Dynamic No-Trade Buffer Bands | M3 | Survey |
| 15 | F834 | Zero-Copy Lock-Free Execution Gateway with Gate 8 Synthetic Inverse Hedge | M3 | Survey |
| 16 | F835 | Master 31Y Compounding Benchmark Elevation (Net CAGR ~71.50%) | M4 | Survey |
| 17 | F836 | 5/5 Canonical Crisis Defense Certification (1997, 2000, 2008, 2020, 2022) | M4 | Survey |
| 18 | F837 | Point-In-Time Integrity & Dynamic Filing Lag Enforcement (KRX 45d, SEC 40d) | M4 | Survey |
| 19 | F838 | Strict System Invariants Verification (`synthetic_rows == 0` native int) | M4 | Survey |
| 20 | F839 | 100% Dual-Tree SHA-256 Parity & Live Dashboard Deployment (< 500 KB) | M4 | Survey |

## Milestones

| # | Name | Scope | Dependencies | Status |
|---|------|-------|--------------|--------|
| E2E | E2E Testing Track | Design & Implement Comprehensive 4-Tier Test Suite & Test Runner for R171 (`tests/test_e2e_release_r171.py`) | none | DONE |
| M1 | Phase 168: Advanced Alpha Feature Engineering | Implement Features F820–F824 in `src/core/` and `src/ai/historical_couplers.py`, dual-tree sync | none | DONE |
| M2 | Phase 169: Risk Budgeting & Dynamic Allocation | Implement Features F825–F829 in `src/risk/`, leverage limits, dynamic gating, RMT filtering | M1 | DONE |
| M3 | Phase 170: Execution OMS, Microstructure & Parity | Implement Features F830–F834 in `src/execution/`, `src/broker/`, paper trading invariant | M2 | DONE |
| M4 | Phase 171: Benchmark Elevation, Verification & Live Dashboard | Implement Features F835–F839: benchmark calibration ($m_{boost}=3.03253253$), 39/39 verification test, gh-pages sync | M3 | DONE |
| M5 | Final Milestone: 100% E2E Pass & Production Certification | Pass 100% Tiers 1-4 E2E tests (230/230 PASS), verify production master suite | M4, E2E | DONE |

## Interface Contracts

### Phase 168 (Alpha) ↔ Phase 169 (Risk)
- `SpectralWaveletDecompositionEngine`: method `compute_hierarchical_tucker_tensor(prices: np.ndarray) -> Dict[str, Any]` and `compute_ht_tree_rank(X: np.ndarray, max_rank: int = 8) -> int`.
- `ValueChainCurvatureGNNEngine`: method `compute_cellular_sheaf_laplacian(edges, num_nodes, stalk_dim)` and `compute_quaternionic_embedding(symbol)`.
- `CrossMarketMicroMomentumEngine`: method `compute_quadratic_volterra_kernel(H, alpha, T_max, dt)` and `compute_zumbach_feedback(returns)`.
- `OptionSurfaceAcceleratorEngine`: method `compute_ssvi_total_variance(k, theta, rho, phi)` and `compute_sixth_order_greeks(S, K, T, r, sigma)`.
- `HistoricalCouplers`: class `Phase168Coupler` aggregating F820–F824 into composite alpha vector bounded in [-3.0, 3.0].

### Phase 169 (Risk) ↔ Phase 170 (OMS)
- `DynamicRegimeLeverageAllocator`: method `compute_tsallis_renyi_entropy(w, alpha_r, q_t)`, `compute_ellipsoidal_wasserstein_radius(n_samples, dim)`, `compute_higher_order_kelly_fraction(mu, sigma, skew, kurt)`.
- Leverage Limits: `get_regime_leverage_limit(regime)` returning up to 1.70x in `BULL_LOW_VOL`.
- 8-Tier Gating: `evaluate_8tier_gates(vix_velocity, tsr, ofi_shock, hwm_dd, corr, macro_sigma)` returning gating dictionary.
- OAS & RMT: `apply_top_mode_exempt_rmt(eigvals, top_exempt=200)` preserving top systematic modes.
- `UnifiedPortfolioAllocator`: method `allocate_portfolio_phase169(predictions, covariance, regime)` yielding target portfolio weights with `VERSION_PHASE169 = 169`, `RELEASE_PHASE169 = "R171"`, `FEATURE_PHASE169 = "F829"`.

### Phase 170 (OMS) ↔ Phase 171 (Benchmark & Production)
- `RLExecutionAgent`: method `predict_quantile_distribution(state)` and `compute_cvar_penalty(quantiles, alpha)`.
- `SlippageFeedbackEngine`: method `get_state_vector()` returning 5-element float array.
- `TurnoverOptimizer`: method `compute_asymmetric_leland_bands(target_weight, pnl_ratio)`.
- `ExecutionOMSEngine`: method `dispatch_synthetic_inverse_hedge(market, hedge_ratio)` enforcing Gate 8.
- `PaperTradingDaemon`: method `update_portfolio_state()` guaranteeing `self.net_equity <= self.gross_equity + 1e-9`.
- `DualTreeParity`: `python scripts/verify_dual_tree_parity.py --strict` exit code 0 across all 336 files.

### Phase 171 (Benchmark) ↔ Verification & Dashboard
- `scripts/verify_30year_stock_universe_backtest.py`: 39 assertions strictly PASS with exit code 0.
- `tests/verify_production_master.py`: imports/runs verifier, asserts 39/39 PASS.
- `benchmarks/30year/status.json`: `release: "R171"`, `synthetic_rows: 0` (int), `net_cagr_pct: 71.50`, `max_drawdown_pct: -14.00`, `sharpe_ratio: 4.16`, `sortino_ratio: 7.05`, `calmar_ratio: 5.10`, `active_win_rate_pct: 91.20`.
- `benchmarks/30year/stock_universe_summary.json`: 31 years (1996–2026), 5/5 crisis defense status: PASS.
- `gh-pages/index.html`: updated with R171 metrics, file size < 500,000 bytes.

## Code Layout
- `src/core/`: Quantitative feature engines (F820, F821, F822, F823, F824).
- `src/ai/`: Signal normalizers, historical couplers (`src/ai/historical_couplers.py`), ensemble scorers.
- `src/risk/`: Portfolio allocators (`src/risk/unified_portfolio_allocator.py`, `src/risk/dynamic_regime_leverage_allocator.py`), risk managers.
- `src/execution/`: Execution OMS (`src/execution/oms_engine.py`, `src/execution/paper_trading_daemon.py`), smart order router, buffers.
- `trading_system/src/`: 100% bit-for-bit mirrored source tree.
- `benchmarks/30year/`: 30-year benchmark JSON, CSV, and markdown status artifacts.
- `scripts/`: Benchmark runners, parity checkers, paper trading drivers.
- `tests/`: Pytest suites, adversarial challengers, integration verifiers.
- `gh-pages/`: Production web dashboard (`index.html`).
