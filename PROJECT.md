# Project: Stock Trading System Hardening & Optimization

## Architecture
The stock trading system is an autonomous multi-market, multi-factor algorithmic trading and quantitative prediction engine supporting 5 core markets (SP500, NASDAQ, RUSSELL2000, KOSPI, KOSDAQ).

### System Layers
1. **Data Ingestion & Storage**: `StockPriceDB` (SQLite WAL + Write Lock Mutex), `MarketIndicatorStorage`, `EarningsDataFetcher` with dynamic filing lag (KRX 45d, US 40d).
2. **31-Strategy Multi-Factor Alpha Engine**: `StrategyRegistry` with 31 alpha factors (Reg, Surge, Lead-Lag, VCP Rule/ML, LSTM, Stat-Arb, Sector Rotation, RIM, Event-Driven, MQ Factor, IV Skew, Order Flow, Reversal, ARM, CARD, LATR, Inst/Foreign, Supply Chain, Sentiment, Factor Neutralized, Vol Target, Microstructure, Accruals, Short Squeeze, Value-Up, Trend Efficiency, Gamma Squeeze, Insider Buying, Tone Drift, Darkpool HFT).
3. **Score Normalization & Dynamic Ensemble**: `CrossSectionalScoreNormalizer` (Percentile Rank / Winsorized Gaussian CDF), `FactorOrthogonalizerEngine` (PCA-ZCA, Gram-Schmidt), `FactorSuppressionEngine` (2D Regime VIF suppression), `EnsembleScoringEngine` (Dynamic active-weight zero-masking).
4. **Portfolio Optimization & Risk Allocation**: `PortfolioOptimizer` (HRP, Black-Litterman, Ledoit-Wolf Shrinkage), `PortfolioAllocator` (EVT-CVaR Tail Risk Budgeting, Leland dynamic buffer bands), `RiskManager` (2D Regime Matrix, Crisis Detector, VIX Velocity gating).
5. **Execution OMS**: `ExecutionOMSEngine` (7 Safety Gates, Limit Lock controls, VPIN maker routing, Overheat gap limits, Synthetic Beta Hedge), `AlmgrenChrissScheduler`, `SlippageFeedbackEngine`, `TurnoverOptimizer`.
6. **Reporting & CI/CD**: `generate_report.py` (GitHub Pages HTML dashboard), `.github/workflows/` (5-market matrix pipeline, pytest CI), `verify_gha_artifacts.py`.

---

## Feature Inventory
| # | Feature / Remediation Target | Description | Milestone | Source |
|---|-----------------------------|-------------|-----------|--------|
| 1 | SQLite Batch Price Upsert | Add `update_prices_batch` to `StockPriceDB` and integrate into `prefetch_prices_batch` | M1 | Survey Explorer 2 |
| 2 | In-Memory Scaler LRU Cache | Cache StandardScaler artifacts in `load_scaler` to eliminate disk I/O | M1 | Survey Explorer 2 |
| 3 | Dynamic ML Thread Allocation | Balance `n_jobs` per market worker during parallel training to prevent thread thrashing | M1 | Survey Explorer 2 |
| 4 | Float32 Inference Downcasting | Downcast price arrays in inference pipeline to halve RAM footprint (~1.4GB -> ~720MB) | M1 | Survey Explorer 2 |
| 5 | Parallel Factor Strategy Scoring | Concurrent execution of independent factor strategies in `run_pipeline.py` | M1 | Survey Explorer 2 |
| 6 | Portfolio Constraint & Safety Polish | Refine `apply_portfolio_constraints` locals cleanup and ADV floor calculation for micro-caps | M2 | Survey Explorer 1 |
| 7 | EVT-CVaR Adaptive Iterations | Optimize numerical stability and iteration convergence in EVT-CVaR optimizer | M2 | Survey Explorer 1 |
| 8 | Trailing Stop Volatility Scaling | Dynamic ATR volatility scaling in trailing stop plan calculation | M2 | Survey Explorer 1 |
| 9 | 31-Factor Strategy Fallback Audit | Verify 4-tier fallbacks, zero-weighting, and score normalizer across all 31 strategies | M3 | Survey Explorer 3 |
| 10 | Backtesting & CI Workflow Hardening | Verify walk-forward backtest friction models and GitHub Actions matrix workflows | M3 | Survey Explorer 3 |
| 11 | Full Test Suite 100% Verification | Run all 138 test files (1,777+ tests), adversarial stress checks, and verify zero regressions | M4 | Survey Explorer 1, 2, 3 |

---

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | M1: Pipeline Speed & Memory Hardening | Batch DB upsert, Scaler LRU cache, ML thread balance, Float32 downcast, Parallel factor scoring | None | DONE |
| 2 | M2: Portfolio Optimization & OMS Hardening | Constraint cleanup, ADV floor scaling, Trailing stop ATR scale, EVT-CVaR convergence | M1 | PLANNED |
| 3 | M3: Strategy Fallback & CI Verification | 31-strategy fallback integrity, zero-weighting isolation, CI workflow validation | M1 | PLANNED |
| 4 | M4: Final E2E Integration & 100% Test Pass | Full test suite execution (1,777+ tests), adversarial coverage hardening, audit gate | M1, M2, M3 | PLANNED |

---

## Interface Contracts

### Data Persistence ↔ Pipeline
- `StockPriceDB.update_prices_batch(price_data: Dict[str, pd.DataFrame]) -> int`: Single-transaction batch upsert across multiple tickers under write lock mutex.
- `load_scaler(model_dir: str, market: str, horizon: int) -> StandardScaler`: Thread-safe LRU-cached scaler loader.

### Model Training ↔ Resource Allocator
- `OnDevicePredictionModel.train(df: pd.DataFrame, market: str, n_jobs: Optional[int] = None)`: Dynamically allocated CPU worker threads.

### Portfolio Allocator ↔ Execution OMS
- `PortfolioAllocator.allocate(mu, cov, ...)`: Returns target weight dictionary $\mathbf{w}^*$.
- `ExecutionOMSEngine.generate_orders(current_weights, target_weights, prices, ...)`: Generates compliant, gate-checked execution order list.

---

## Code Layout
- `trading_system/run_pipeline.py`: Main unified pipeline entry point.
- `src/persistence/database.py`: `StockPriceDB` SQLite WAL database layer.
- `src/ai/feature_engineering.py`: Scaler loading and feature engineering functions.
- `src/ai/prediction_model.py`: On-device ML model training and inference.
- `src/ai/ensemble_scorer.py`: 31-strategy dynamic ensemble scoring engine.
- `src/analysis/portfolio_optimizer.py`: HRP, Ledoit-Wolf, Black-Litterman optimization.
- `src/risk/portfolio_allocator.py`: EVT-CVaR risk budgeting and Leland buffer bands.
- `src/execution/order_manager.py`: Execution OMS engine with 7 safety gates.
- `src/core/`: 31 individual strategy engines.
- `tests/`: 138 test files with 1,777+ comprehensive test cases.
