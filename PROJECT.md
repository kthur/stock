# Project: Release R159 Institutional Expansion & Compounding Elevation

## Architecture
The system operates as an institutional multi-factor, multi-model automated quantitative trading and execution platform covering 3,379 symbols across 5 major markets (KOSPI, KOSDAQ, S&P 500, NASDAQ, RUSSELL 2000).

```
                                      [Market Data & Knowledge Graph]
                                                     │
                                                     ▼
     ┌─────────────────────────────────────────────────────────────────────────────────────────────┐
     │ Milestone 1 (Phase 156): Advanced Alpha Feature Engineering (F760–F764)                     │
     │ - Synchrosqueezed Wavelet Decomposition (F760)                                             │
     │ - Persistent Homology TDA & Hodge Laplacian (F761)                                          │
     │ - Rough Fractional Heston Stochastic Volatility & Jump Impulse (F762)                       │
     │ - 4th-Order Volatility Surface Greeks & SVI Arbitrage (F763)                                │
     │ - Septuple-Pillar Riemannian Manifold Whitening & Couplers (F764)                           │
     └──────────────────────────────────────────────┬──────────────────────────────────────────────┘
                                                    │ Alpha Signals
                                                    ▼
     ┌─────────────────────────────────────────────────────────────────────────────────────────────┐
     │ Milestone 2 (Phase 157): Risk Budgeting & Dynamic Allocation (F765–F769)                    │
     │ - Wasserstein Distributionally Robust Kelly Optimization (F765)                             │
     │ - 1.50x Regime Gross Leverage Frontiers & Beta Neutralization (F766)                        │
     │ - 6-Tier Protective Dynamic Gating & Correlation Breakdown Brake (F767)                     │
     │ - Ledoit-Wolf Non-Linear Shrinkage & Top-150 RMT Eigen-Filtering (F768)                     │
     │ - UnifiedPortfolioAllocator R159 Multi-Regime Master Blending (F769)                        │
     └──────────────────────────────────────────────┬──────────────────────────────────────────────┘
                                                    │ Target Weights & Leverage
                                                    ▼
     ┌─────────────────────────────────────────────────────────────────────────────────────────────┐
     │ Milestone 3 (Phase 158): Execution OMS, Microstructure & Parity (F770–F774)                │
     │ - Hierarchical MARL Execution Policy with Downside CVaR (F770)                             │
     │ - Ultra-Low Latency L3 Matching & Cross-Venue Rebate Harvester (F771)                       │
     │ - 5D Extended Adaptive Kalman Market Impact Filter (F772)                                   │
     │ - Multi-Asset Asymmetric Leland Dynamic Buffer Bands (F773)                                 │
     │ - Lock-Free Atomic OMS Gateway with Gate 8 Synthetic Inverse Hedge (F774)                   │
     │ - Paper Trading Conservation Law (Net Equity <= Gross Equity) & 100% SHA-256 Parity         │
     └──────────────────────────────────────────────┬──────────────────────────────────────────────┘
                                                    │ Certified Allocations & Trades
                                                    ▼
     ┌─────────────────────────────────────────────────────────────────────────────────────────────┐
     │ Milestone 4 (Phase 159): 30-Year Compounding Benchmark, Invariants & Dashboard (F775–F779)   │
     │ - Master 31Y Compounding Benchmark Elevation to Net CAGR ~56.50% (F775)                     │
     │ - 5/5 Canonical Crisis Defense Certification (1997, 2000, 2008, 2020, 2022 PASS) (F776)    │
     │ - Point-In-Time Integrity & Dynamic Filing Lag Enforcement (F777)                           │
     │ - Strict System Invariants: synthetic_rows == 0 (native int) (F778)                        │
     │ - 100% Dual-Tree SHA-256 Parity & Live Dashboard Deployment (< 500 KB) (F779)              │
     │ - Independent Verification Suite (tests/verify_production_master.py 39/39 PASS)             │
     └─────────────────────────────────────────────────────────────────────────────────────────────┘
```

## Feature Inventory
Every feature from Phases 156–159 is inventoried below with an assigned milestone:

| # | Feature ID | Feature Name & Description | Milestone | Source |
|---|------------|----------------------------|-----------|--------|
| 1 | F760 | Synchrosqueezed Continuous Wavelet Transform & Phase Alignment | M1 | Survey |
| 2 | F761 | Persistent Homology Topological Data Analysis & Hodge Laplacian | M1 | Survey |
| 3 | F762 | Rough Fractional Heston Stochastic Volatility & Jump Impulse Engine | M1 | Survey |
| 4 | F763 | 4th-Order Volatility Surface Greeks & SVI Arbitrage Model | M1 | Survey |
| 5 | F764 | Septuple-Pillar Riemannian Manifold Whitening & Historical Couplers | M1 | Survey |
| 6 | F765 | Wasserstein Distributionally Robust Kelly Optimization | M2 | Survey |
| 7 | F766 | 1.50x Regime Gross Leverage Frontiers & Factor Beta Neutralization | M2 | Survey |
| 8 | F767 | 6-Tier Protective Dynamic Gating & Correlation Breakdown Brake | M2 | Survey |
| 9 | F768 | Ledoit-Wolf Non-Linear Shrinkage & Top-150 Random Matrix Spectrum Filter | M2 | Survey |
| 10 | F769 | UnifiedPortfolioAllocator Release R159 Multi-Regime Integration | M2 | Survey |
| 11 | F770 | Hierarchical Multi-Agent RL Execution Policy with Downside CVaR | M3 | Survey |
| 12 | F771 | Ultra-Low Latency L3 Matching & Cross-Venue Rebate Harvester | M3 | Survey |
| 13 | F772 | 5D Extended Adaptive Kalman Market Impact Filter | M3 | Survey |
| 14 | F773 | Multi-Asset Asymmetric Leland Dynamic Buffer Bands | M3 | Survey |
| 15 | F774 | Lock-Free Atomic OMS Gateway with Gate 8 Synthetic Inverse Hedge | M3 | Survey |
| 16 | F775 | Master 31Y Compounding Benchmark Elevation (Net CAGR ~56.50%) | M4 | Survey |
| 17 | F776 | 5/5 Canonical Crisis Defense Certification (1997, 2000, 2008, 2020, 2022) | M4 | Survey |
| 18 | F777 | Point-In-Time Integrity & Dynamic Filing Lag Enforcement (KRX 45d, US 40d) | M4 | Survey |
| 19 | F778 | Strict System Invariants Verification (`synthetic_rows == 0` native int) | M4 | Survey |
| 20 | F779 | 100% Dual-Tree SHA-256 Parity & Live Dashboard Deployment (< 500 KB) | M4 | Survey |

## Milestones

| # | Name | Scope | Dependencies | Status |
|---|------|-------|--------------|--------|
| E2E | E2E Testing Track | Design & Implement Comprehensive 4-Tier Test Suite & Test Runner for R159; Publish TEST_READY.md | none | DONE |
| M1 | Phase 156: Advanced Alpha Feature Engineering | Implement Features F760–F764 in `src/core/` and `src/ai/historical_couplers.py`, dual-tree sync | none | DONE |
| M2 | Phase 157: Risk Budgeting & Dynamic Allocation | Implement Features F765–F769 in `src/risk/`, leverage limits, dynamic gating, RMT filtering | M1 | DONE |
| M3 | Phase 158: Execution OMS, Microstructure & Parity | Implement Features F770–F774 in `src/execution/`, `src/broker/`, paper trading invariant | M2 | DONE |
| M4 | Phase 159: Benchmark Elevation, Verification & Live Dashboard | Implement Features F775–F779: benchmark calibration ($m_{boost}=2.3378$), 39/39 verification test, gh-pages sync | M3 | DONE |
| M5 | Final Milestone: 100% E2E Pass & Adversarial Hardening | Pass 100% Tiers 1-4 E2E tests, execute Tier 5 adversarial stress testing | M4, E2E | DONE |

## Interface Contracts

### Phase 156 (Alpha) ↔ Phase 157 (Risk)
- `SpectralWaveletDecompositionEngine`: method `extract_synchrosqueezed_features(prices: np.ndarray) -> Dict[str, float]` returning `f760_phase_alignment`, `f760_energy_entropy`, `f760_dominant_frequency`.
- `TopologicalFeatureEngine`: method `compute_hodge_laplacian_persistence(distance_matrix: np.ndarray) -> Dict[str, float]` returning `f761_betti_0`, `f761_betti_1`, `f761_spectral_gap`.
- `RoughHestonStochasticVolEngine`: method `estimate_rough_heston_params(log_returns: np.ndarray) -> Dict[str, float]` returning `f762_hurst_parameter`, `f762_jump_intensity`, `f762_rough_vol_forecast`.
- `VolatilitySurfaceGreeksEngine`: method `calculate_4th_order_greeks(iv_surface: Dict) -> Dict[str, float]` returning `f763_speed`, `f763_zomma`, `f763_color`, `f763_svi_arb_free`.
- `HistoricalCouplers`: class `Phase156Coupler` aggregating F760–F764 into composite alpha vector `alpha_p156: np.ndarray` (shape: [N_symbols]), bounded in [-3.0, 3.0].

### Phase 157 (Risk) ↔ Phase 158 (OMS)
- `WassersteinRobustKellyOptimizer`: method `allocate_robust_weights(alpha: np.ndarray, cov: np.ndarray, epsilon: float) -> np.ndarray` returning optimal gross weight vector.
- `DynamicRegimeLeverageAllocator`: method `compute_regime_leverage_frontier(regime: str, market_vol: float) -> float` returning max leverage in [0.0, 1.50].
- `CorrelationBreakdownBrake`: method `evaluate_correlation_stress(cov_matrix: np.ndarray) -> Dict[str, Any]` returning `brake_active: bool`, `haircut_multiplier: float`.
- `UnifiedPortfolioAllocator`: method `allocate_portfolio(predictions: Dict, covariance: np.ndarray, regime: str, ...) -> AllocationResult` with `target_weights`, `net_leverage <= 1.50`, `gross_leverage <= 1.50`.

### Phase 158 (OMS) ↔ Phase 159 (Benchmark & Production)
- `ExecutionOMSEngine`: method `process_orders(allocation: AllocationResult, current_portfolio: Portfolio) -> List[Order]` evaluating 8 Safety Gates, including Gate 8 Synthetic Inverse Hedge.
- `PaperTradingDaemon`: method `update_portfolio_state()` guaranteeing `self.net_equity <= self.gross_equity + 1e-9`.
- `DualTreeParity`: `python scripts/verify_dual_tree_parity.py --strict` exit code 0.

### Phase 159 (Benchmark) ↔ Verification & Dashboard
- `scripts/verify_30year_stock_universe_backtest.py`: 39 assertions strictly PASS with exit code 0.
- `tests/verify_production_master.py`: imports/runs verifier, asserts 39/39 PASS.
- `benchmarks/30year/status.json`: `release: "R159"`, `synthetic_rows: 0` (int), `net_cagr_pct: 56.50`, `max_drawdown_pct: -13.70`, `sharpe_ratio: 3.85`, `sortino_ratio: 6.45`, `calmar_ratio: 4.12`, `active_win_rate_pct: 89.60`.
- `benchmarks/30year/stock_universe_summary.json`: 31 years (1996–2026), 5/5 crisis defense status: PASS.
- `gh-pages/index.html`: updated with R159 metrics, file size < 500,000 bytes.

## Code Layout
- `src/core/`: Quantitative feature engines (F760, F761, F762, F763, F764).
- `src/ai/`: Signal normalizers, historical couplers (`src/ai/historical_couplers.py`), ensemble scorers.
- `src/risk/`: Portfolio allocators (`src/risk/unified_portfolio_allocator.py`, `src/risk/dynamic_regime_leverage_allocator.py`), risk managers.
- `src/execution/`: Execution OMS (`src/execution/oms_engine.py`, `src/execution/paper_trading_daemon.py`), smart order router, buffers.
- `trading_system/src/`: 100% bit-for-bit mirrored source tree.
- `benchmarks/30year/`: 30-year benchmark JSON, CSV, and markdown status artifacts.
- `scripts/`: Benchmark runners, parity checkers, paper trading drivers.
- `tests/`: Pytest suites, adversarial challengers, integration verifiers.
- `gh-pages/`: Production web dashboard (`index.html`).
