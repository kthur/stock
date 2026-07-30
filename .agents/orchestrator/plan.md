# Orchestrator Execution Plan: Stock Trading System Optimization

## Milestone Breakdown & Execution Steps

### Milestone 1: Architecture Modularization & Data Engine Upgrade (R1)
- **Goal**: Refactor `run_pipeline.py` into a DAG modular pipeline (`trading_system/dag_pipeline.py` or modular DAG task graph) with JSON/Parquet checkpointing and resumability on failure. Upgrade `src/data_layer/indicator_storage.py` & `src/persistence/database.py` to a hybrid Parquet/WAL schema to eliminate SQLite write-lock OperationalErrors under multi-asset concurrent streaming.
- **Verification**:
  - DAG task execution succeeds with resume capabilities upon mock interruption.
  - Multi-threaded streaming data ingestion writes to hybrid Parquet storage with zero write-lock errors.
  - Unit tests for DAG pipeline & Parquet storage pass cleanly.

### Milestone 2: Quantitative Alpha & Ensemble Orthogonalization (R2)
- **Goal**: Implement Gram-Schmidt and PCA factor orthogonalization in `src/ai/ensemble_scorer.py` to strip out multicollinearity across all 17 strategies. Upgrade `src/core/stat_arb.py` with K-Means / OPTICS pre-clustering to partition 3,379 universe stocks and reduce cointegration pair scanning from O(N^2) to O(N log N).
- **Verification**:
  - Orthogonalized strategy weights maintain rank power while reducing pairwise feature correlation below 0.3.
  - Cointegration pair scanning completes in under 30 seconds for 3,379 symbols.
  - Unit tests in `tests/test_ensemble_scorer.py` and `tests/test_stat_arb.py` pass cleanly.

### Milestone 3: Risk Management & Portfolio Optimization Enhancement (R3)
- **Goal**: Integrate EVT (Extreme Value Theory) CVaR tail-risk budget constraints into `src/risk/portfolio_allocator.py` via Generalized Pareto Distribution (GPD) fitting. Implement dynamic band-based rebalancing (no-trade buffer zones) to minimize Securities Transaction Tax (STT) and transaction cost drag.
- **Verification**:
  - Portfolio allocator produces optimal weights satisfying EVT-CVaR loss limits.
  - Backtesting shows significant reduction in portfolio turnover and transaction costs.
  - Unit tests in `tests/test_portfolio_allocator.py` and risk manager tests pass cleanly.

### Milestone 4: Execution Engine & MLOps Monitoring (R4)
- **Goal**: Add TWAP (Time-Weighted Average Price) and VWAP (Volume-Weighted Average Price) algorithmic order slicing to `src/execution/oms_engine.py` for low-liquidity assets. Implement real-time execution slippage feedback loop to update dynamic ensemble scoring weights, and MLflow model drift triggers in `src/monitoring/mlops_monitor.py` for continuous auto-retraining.
- **Verification**:
  - OMS slicer generates valid TWAP/VWAP child order schedules.
  - Slippage feedback dynamically adjusts strategy weights based on execution impact.
  - MLflow drift detector triggers retraining signals upon concept drift.
  - Unit tests in `tests/test_oms_engine.py` and `tests/test_mlops_monitor.py` pass cleanly.

### Milestone 5: E2E Integration, Verification & Forensic Audit
- **Goal**: Run complete test suite (`.venv\Scripts\python.exe -m pytest tests/ -v`), benchmark cointegration scanner performance (<30s), verify zero write-lock concurrency errors and reduced portfolio turnover, execute Forensic Auditor integrity verification.
- **Verification**:
  - 100% unit tests passing.
  - Forensic Auditor verdict is CLEAN (no hardcoding, no facade implementations).
  - All acceptance criteria satisfied.
