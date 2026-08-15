# Project: Autonomous Continuous Quantitative Strategy & Execution Platform (`kthur/stock`)

## Architecture
- **Data & Storage Layer**: `StockPriceDB`, `MarketIndicatorStorage`, `CorporateActionAdjuster`, `ParquetWALBuffer`, `hybrid_storage.py` (SQLite WAL mode, 30s timeout, thread-local connections, write mutex).
- **31-Strategy Multi-Factor Engine**: 31 registered quantitative alpha engines spanning ML (XGBoost, Strict Causal LSTM, VCP ML), Technical/Factor (Lead-Lag, Stat-Arb, Sector Rotation, MQ Factor, Short-Term Reversal, ARM, CARD, LATR, Inst & Foreign, Supply Chain, Multi-Factor Neutralizer, Vol Target, Accruals Quality, Value-Up Catalyst, Trend Efficiency), Event/Sentiment (Event-Driven, NLP FinBERT Sentiment, Insider Buying, Earnings Tone Drift), Options (IV Skew, Gamma Squeeze, Short Squeeze), and Microstructure (Microstructure Imbalance, DMA Darkpool HFT).
- **Regime & Calibration Engine**: 2D Market Regime Matrix (6 states), 3D Macro Overrides, Quantile Winsorization, PCA ZCA Factor Orthogonalization, Regime Factor Suppression, Isotonic Regression & Platt Scaling probability calibration.
- **Risk & Portfolio Optimization Layer**: EVT-CVaR (POT GPD with 3-Tier fallback), Leland Dynamic Buffer Band Rebalancing, Ledoit-Wolf Covariance Shrinkage, Hierarchical Risk Parity (HRP), Equal Risk Contribution (ERC), Constrained MVO, Fractional Kelly with Volatility Targeting.
- **Execution & Friction Layer**: Asset-specific Microstructure Cost Model (STT 0.15% KOSPI / 0.18% KOSDAQ, SEC fee 0.003%, dynamic spread, square-root market impact), Execution OMS Engine (`trade_logs.db`, 6 live-money safety gates), Closed-Loop Slippage Feedback Engine (`cost_scaling_factor` calibration), Turnover Optimizer with hysteresis buffer.
- **Reporting & Pipeline Layer**: `run_pipeline.py` orchestration across 3,379 symbols (SP500, NASDAQ, RUSSELL2000, KOSPI, KOSDAQ, KONEX), Strategy Coverage Analyzer, KST HTML Dashboard Generator (`index.html`), Pipeline Text Outputs.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | 31 Alpha Strategy Engines | All 31 quantitative strategy engines registered, normalized $[0.0, 1.0]$, and executing cleanly. | M1 | Survey (R1) |
| 2 | Data Hygiene & Anti-Lookahead | 60-day fundamental filing lag, US-to-KRX 1-day indicator shift, and corporate action split adjustment. | M1 | Survey (R1) |
| 3 | Factor Orthogonalization & Calibration | PCA ZCA symmetric decorrelation, Gram-Schmidt residualization, and Isotonic probability calibration across all strategies. | M1 | Survey (R1) |
| 4 | EVT-CVaR Risk Budgeting | Peaks-Over-Threshold (POT) GPD tail modeling with 3-tier fallback and non-linear SLSQP optimization. | M2 | Survey (R2) |
| 5 | Leland Dynamic Buffer Bands | Optimal no-trade buffer bands $\delta_i = (3 c_i w_i \sigma_i / 2\gamma)^{1/3}$ achieving $\ge 60\%$ friction cost reduction. | M2 | Survey (R2) |
| 6 | Microstructure & Closed-Loop OMS | Directional STT tax, SEC fees, dynamic spread, square-root impact, 6 live-money safety gates, and `trade_logs.db` slippage feedback. | M2 | Survey (R2) |
| 7 | Logging & Friction Remediation | Fix `turnover_optimizer.py` string formatting bug (`%,.0f` -> `%s`), and resolve legacy test assertions in `test_critical_bugs.py`, `test_m1_1_fixes.py`, `test_r3_coverage_and_universe.py`. | M2 | Survey (R2, R4) |
| 8 | High-Throughput SQLite WAL & Threading | SQLite WAL concurrency with thread-local pooling, retry cascades, and `np.float32` memory optimization across 3,379 symbols. | M3 | Survey (R3) |
| 9 | Comprehensive Verification & CI Suite | Full automated execution of primary acceptance tests (`test_portfolio_allocator.py`, `test_new_27_strategies.py`), modular risk/factor suites, and coverage reporting. | M3 | Survey (R4) |
| 10 | Version Control Deployment | Git synchronization and clean push to `origin/main` (`1a8b4fc`). | M4 | Survey (R4) |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Alpha Engine & Calibration Optimization | Expand calibrator registration in `run_pipeline.py` to all 31 strategies; verify causal data hygiene and factor orthogonalization. | None | DONE |
| M2 | Portfolio Allocator & Friction Remediation | Fix `turnover_optimizer.py` logger format bug; update legacy test assertions (`test_critical_bugs.py`, `test_m1_1_fixes.py`, `test_r3_coverage_and_universe.py`); verify EVT-CVaR, Leland bands, and OMS. | None | DONE |
| M3 | End-to-End Test Suite Verification | Run and verify 100% pass across primary acceptance tests (`test_portfolio_allocator.py`, `test_new_27_strategies.py`) and all secondary modular suites. | M1, M2 | DONE |
| M4 | Final Audit & Git Push Deployment | Forensic integrity audit, final documentation, and push to `origin/main` (`1a8b4fc`). | M3 | DONE |

## Interface Contracts
### `PortfolioAllocator` (`trading_system/src/risk/portfolio_allocator.py`)
- `calculate_evt_cvar(returns: np.ndarray, alpha: float = 0.95, u_quantile: float = 0.90) -> float`
- `calculate_leland_buffer_band(current_weight: float, target_weight: float, transaction_cost: float, volatility: float, risk_aversion: float = 3.0) -> LelandBand`
- `estimate_microstructure_cost(symbol: str, market: str, order_qty: float, price: float, adv: float, volatility: float, is_sell: bool = True) -> float`
- `allocate_portfolio(signals: pd.DataFrame, covariance_matrix: np.ndarray, current_weights: Dict[str, float]) -> AllocationResult`

### `TurnoverOptimizer` (`trading_system/src/execution/turnover_optimizer.py`)
- `filter_target_portfolio(current_portfolio: Dict[str, Any], target_portfolio: Dict[str, Any], prices: Dict[str, float]) -> Tuple[Dict[str, Any], float]`

### `EnsembleScoringEngine` (`trading_system/src/ai/ensemble_scorer.py`)
- `fit_calibrators(historical_scores: pd.DataFrame, realized_outcomes: pd.Series) -> None`
- `calculate_ensemble_score(strategy_scores: pd.DataFrame, market_indicators: Dict[str, Any], regime: str) -> pd.DataFrame`

## Code Layout
- `trading_system/run_pipeline.py`: Pipeline execution and orchestration.
- `trading_system/src/ai/`: ML models, VCP detectors, LSTM, factor orthogonalization, ensemble scorer.
- `trading_system/src/core/`: 31 Alpha strategy engines, strategy registry, base strategy classes.
- `trading_system/src/risk/`: Portfolio allocator, EVT-CVaR, Leland bands, risk manager, position sizing.
- `trading_system/src/execution/`: Execution OMS engine, slippage feedback, turnover optimizer.
- `trading_system/src/analysis/`: Strategy coverage analyzer, portfolio optimizer algorithms.
- `trading_system/src/persistence/`: SQLite database manager, trade logger.
- `trading_system/src/data_layer/`: Market indicator storage, hybrid storage, price adjuster, earnings data.
- `tests/`: Automated pytest suites.
