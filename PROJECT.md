# Project: 31-Strategy Multi-Factor Equity Trading System (`kthur/stock`)

## Architecture

The system is an autonomous quantitative trading platform covering 3,379 equity symbols across South Korea (KOSPI, KOSDAQ, KONEX) and the United States (S&P 500, NASDAQ, Russell 2000).

```
[Data Ingestion & Storage Layer]
  ├── StockPriceDB (SQLite WAL, per-thread local, write lock mutex, 2GB mmap)
  ├── MarketIndicatorStorage (Global macro & sector indicators, WAL checkpointing)
  └── EarningsDataFetcher (60d filing lag, rate-limit retry backoff)
           │
           ▼
[31-Strategy Alpha Generation Engine]
  ├── Core Machine Learning: (1) XGBoost Reg, (2) Surge Clf, (3) Lead-Lag, (4) VCP Rule, (5) VCP ML, (6) Causal LSTM
  ├── Cross-Sectional & Stat-Arb: (7) Stat-Arb Coint, (8) Sector Rotation, (9) RIM Valuation, (10) Event-Driven
  ├── Factor Momentum & Reversal: (11) MQ Factor, (12) IV Skew, (13) Order Flow, (14) Short-Term Reversal
  ├── Revision & Macro Divergence: (15) ARM Factor, (16) CARD Factor, (17) LATR Factor, (18) Inst & Foreign Sector
  ├── Fundamental & Sentiment: (19) Supply Chain, (20) NLP FinBERT Sentiment, (21) Style Neutralizer, (22) Vol Target
  └── Microstructure & Flow: (23) Microstructure, (24) Accruals Quality, (25) Short Squeeze, (26) Value-Up,
                             (27) Trend Efficiency, (28) Gamma Squeeze, (29) Insider Buying, (30) Tone Drift, (31) Darkpool / HFT
           │
           ▼
[Statistical Hygiene & Ensemble Scoring Engine]
  ├── PCA ZCA Symmetric Whitening & Modified Gram-Schmidt Decorrelation
  ├── 2D Market Regime Engine (6 States: Bear/Sideways/Bull x Low/High Vol)
  ├── Dynamic Sharpe & Isotonic Monotonic Probability Calibration
  ├── Collinearity & VIF Factor Noise Suppression
  └── Missingness-Aware Renormalization & Coverage Penalization
           │
           ▼
[Portfolio Optimization & Execution OMS Layer]
  ├── Hierarchical Risk Parity (HRP) & Ledoit-Wolf Covariance Shrinkage
  ├── EVT-CVaR Extreme Value Tail Risk Budgeting (POT-GPD 3-Tier Hierarchy)
  ├── Microstructure Friction Cost Deduction (STT, SEC, Dynamic Spread, Kyle/Almgren-Chriss Impact)
  ├── Leland Optimal No-Trade Buffer Bands (Turnover Hysteresis)
  └── ExecutionOMSEngine & SlippageFeedbackEngine (6 Safety Gates, trade_logs.db)
           │
           ▼
[Reporting & Continuous Deployment]
  ├── Output Text Reports (ensemble_predictions.txt, strategy_data_coverage_report.txt, etc.)
  ├── GitHub Pages HTML Visual Dashboard (KST Timezone, 31 Strategy Panels, Scenario Simulator)
  └── CI/CD Pytest Verification & Git Remote Sync (origin/main)
```

---

## Feature Inventory

| # | Feature | Description | Milestone | Status |
|---|---------|-------------|-----------|--------|
| F01 | 31-Strategy Engine Integration | Full coverage and execution of all 31 quantitative alpha engines across KRX and US universes. | M1 | COMPLETED |
| F02 | Lookahead Bias Prevention | 60-day calendar filing lag for fundamental data and 1-day lag shifts for cross-timezone US indicators on Asian assets. | M1 | COMPLETED |
| F03 | Collinearity & Decorrelation | PCA ZCA whitening, Modified Gram-Schmidt, Spearman rank VIF filtering, and 2D regime factor suppression. | M1 | COMPLETED |
| F04 | Factor Suppression Granularity | Full `CLUSTER_MAP` in `factor_suppression.py` assigning all 31 strategies to designated factor clusters. | M1 | COMPLETED |
| F05 | Monotonic Scoring Calibration | Isotonic Regression calibration, winsorization (0.5%–99.5%), confluence boosts, and missingness dynamic renormalization. | M1 | COMPLETED |
| F06 | Hierarchical Risk Parity (HRP) | Lopez de Prado HRP algorithm with Ledoit-Wolf shrinkage ($\delta=0.15$) and concentration caps (10% asset, 25% sector). | M2 | COMPLETED |
| F07 | EVT-CVaR Tail Risk Budgeting | 3-tier fallback hierarchy (EVT-GPD $\to$ Cornish-Fisher $\to$ Gaussian/Empirical) and SLSQP non-linear tail constraint solver. | M2 | COMPLETED |
| F08 | Microstructure Friction Model | Statutory tax rates (KOSPI 0.15%, KOSDAQ 0.18%, KONEX 0.08%, US SEC 0.003%), dynamic spread, and Kyle square-root market impact deduction. | M2 | COMPLETED |
| F09 | Leland No-Trade Buffer Bands | Dynamic turnover hysteresis bands $\delta_i \in [0.5\%, 5.0\%]$ delivering $\ge 60\%$ transaction cost reduction. | M2 | COMPLETED |
| F10 | Execution OMS & Slippage Feedback | 6 live-money safety gates, SQLite WAL `trade_logs.db` logging, and closed-loop slippage parameter adaptation. | M2 | COMPLETED |
| F11 | Pipeline Thread Concurrency | Separation of network I/O workers (up to 32) and CPU feature workers (`CPU * 2`), socket timeouts (5s), symbol timeouts (30s). | M3 | COMPLETED |
| F12 | SQLite WAL Concurrency & Mutex | SQLite WAL mode, 30s busy timeout, 500MB page cache, 2GB mmap, `threading.local` connections, and write lock retry backoff. | M3 | COMPLETED |
| F13 | Memory & Numerical Safeguards | float32 dataframe downcasting, intermediate garbage collection, Sharpe-scaled return target clipping ($\pm 5\sqrt{h}$), and CrisisDetector level scaling. | M3 | COMPLETED |
| F14 | Comprehensive Pytest Suite | Full unified test suite (`pytest tests/ -v`) verifying 100% test pass rate across all 1,124+ unit, integration, and challenger tests with zero regressions. | M4 | COMPLETED |
| F15 | Production Git Deployment | Continuous integration and deployment via GitHub Actions (matrix inference + Pages build) synced to `origin/main`. | M4 | COMPLETED |

---

## Milestones

| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| **M1** | Alpha Engines & Ensemble Scorer | Features F01–F05: 31 Alpha strategy verification, lookahead bias audit, factor suppression cluster mapping, and ensemble scoring calibration. | none | COMPLETED |
| **M2** | Portfolio Allocation & Microstructure Execution | Features F06–F10: HRP, Ledoit-Wolf shrinkage, EVT-CVaR tail risk budgeting, microstructure friction cost deductions, Leland buffer bands, and OMS slippage feedback. | M1 | COMPLETED |
| **M3** | Pipeline Concurrency & Memory Optimization | Features F11–F13: Thread pool scaling, SQLite WAL persistence mutex, float32 memory downcasting, and CrisisDetector safety gating. | M2 | COMPLETED |
| **M4** | Comprehensive Verification & Git Push | Features F14–F15: 100% full test suite execution (`pytest tests/`), forensic audit validation, and Git commit/push to `origin/main`. | M3 | COMPLETED |

---

## Interface Contracts

### 1. `StrategyRegistry` ↔ `EnsembleScoringEngine`
- **Interface**: Strategy classes registered via `@register_strategy(name="...")` implementing `.compute_signals(df, fundamentals)` or `.score(symbol_data)`.
- **Data Types**: Returns `pd.DataFrame` containing indexed `symbol` with strategy score column (e.g. `reg_score`, `surge_score`, `ll_score`, ..., `darkpool_score`). All scores bounded in $[0.0, 1.0]$.
- **Error Handling**: Missing values represented as `np.nan` or omitted rows. Valid zeros preserved as `0.0`. Missingness dynamic renormalization handles sparse symbols without distortion.

### 2. `EnsembleScoringEngine` ↔ `PortfolioAllocator` / `MicrostructureCost`
- **Interface**: `EnsembleScoringEngine.combine_predictions(...)` $\to$ outputs `DataFrame` with `ensemble_score`, `ensemble_expected_return` (net of transaction friction), `regime_name`, and `decision_rationale`.
- **Data Types**: `ensemble_expected_return` in percentage points (clipped to $[0.0, 50.0]$).
- **Error Handling**: Costs calculated per market exchange using statutory STT/SEC rates and dynamic spread models.

### 3. `PortfolioAllocator` ↔ `ExecutionOMSEngine`
- **Interface**: `ExecutionOMSEngine.create_order_plan(current_weights, target_weights, portfolio_value, prices, ...)`
- **Data Types**: Returns list of `OrderPlan` objects logged into `trade_logs.db`.
- **Error Handling**: 6 safety gates (Severe crisis blocking, kill switch, ticker regex sanitization, price bounds $[1.0, 10^8]$, 10-share lot rounding).

---

## Code Layout

- `trading_system/run_pipeline.py`: Main pipeline orchestration entry point
- `trading_system/src/core/`: 31 Alpha strategy factor engines & registry
- `trading_system/src/ai/`: Prediction models, ensemble scorer, factor orthogonalizer, factor suppression, correlation monitor, isotonic calibrators
- `trading_system/src/risk/`: Portfolio allocator, EVT-CVaR, position sizing, crisis detector, risk manager
- `trading_system/src/analysis/`: Portfolio optimizer (HRP), coverage analyzer
- `trading_system/src/execution/`: Execution OMS engine, slippage feedback engine, kill switch
- `trading_system/src/persistence/`: StockPriceDB (SQLite WAL)
- `trading_system/src/data_layer/`: MarketIndicatorStorage, EarningsDataFetcher
- `trading_system/src/config.py`: System configuration, fee parameters, and thresholds
- `tests/`: 1,124+ Unit, Integration, and Challenger test suites
