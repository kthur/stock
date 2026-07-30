# Project: Stock Trading System Full-scale Optimization

## Architecture
- **DAG Pipeline**: Task graph execution with state serialization & resume capability (`trading_system/dag_pipeline.py`).
- **Hybrid Data Engine**: SQLite/Parquet hybrid storage for high-concurrency multi-asset streaming (`src/data_layer/`).
- **Ensemble Engine**: Gram-Schmidt & PCA factor orthogonalization across 17 strategies (`src/ai/ensemble_scorer.py`).
- **Stat-Arb Engine**: Cluster-accelerated cointegration scanner (K-Means / OPTICS) (`src/core/stat_arb.py`).
- **Portfolio Allocator**: EVT-CVaR risk budget constraints & dynamic band-based rebalancing (`src/risk/portfolio_allocator.py`).
- **OMS Engine**: TWAP/VWAP order slicing & real-time slippage feedback loop (`src/execution/oms_engine.py`).
- **MLOps Monitor**: MLflow model drift detector & auto-retrain triggers (`src/monitoring/mlops_monitor.py`).

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | Architecture Modularization & Data Engine Upgrade | R1 | None | DONE |
| 2 | Quantitative Alpha & Ensemble Orthogonalization | R2 | M1 | DONE |
| 3 | Risk Management & Portfolio Optimization Enhancement | R3 | M1 | IN_PROGRESS |
| 4 | Execution Engine & MLOps Monitoring | R4 | M1, M3 | PLANNED |
| 5 | E2E Integration, Verification & Forensic Audit | Acceptance | M1, M2, M3, M4 | PLANNED |

## Interface Contracts
### DAG Pipeline ↔ Task Modules
- Tasks implement `Task` interface with `name`, `dependencies`, `execute(context)`, `checkpoint()`/`restore()`.
- Pipeline state saved to `.checkpoints/pipeline_state.json` / parquet frames.

### Data Storage ↔ Multi-Asset Streamers
- Concurrent writes routed through Parquet append-log / Timescale WAL engine.
- Zero SQLite `database is locked` OperationalErrors under multi-threading.

### Factor Orthogonalizer ↔ Ensemble Scorer
- Input: matrix of 17 raw strategy signal scores per ticker $X \in \mathbb{R}^{N \times 17}$.
- Output: orthogonalized score matrix $X_{ortho} \in \mathbb{R}^{N \times 17}$ preserving relative variance explaining power.

### Stat-Arb Scanner ↔ Cointegration Engine
- Pre-clustering partitions 3,379 symbols into $K$ feature clusters (K-Means/OPTICS).
- Cointegration test performed only within/adjacent clusters ($O(N \log N)$ complexity).

### Portfolio Allocator ↔ Dynamic Rebalancer
- Tail-risk CVaR estimated via GPD (Generalized Pareto Distribution) fitting.
- Rebalance signal emitted only when allocation drift breaches no-trade buffer bands.

### OMS Slicer ↔ Slippage Feedback
- TWAP/VWAP slices orders into sub-blocks across time buckets.
- Real-time execution slippage fed back to `EnsembleScoringEngine` dynamic weights.

## Code Layout
- `trading_system/`: Pipeline entry points and DAG orchestration.
- `src/ai/`: ML models, prediction pipelines, ensemble scoring.
- `src/analysis/`: Coverage and performance analytics.
- `src/core/`: Quantitative strategy engines (Stat-Arb, Sector Rotation, Event-Driven, etc.).
- `src/data_layer/`: Database storage, hybrid Parquet engine, indicator management.
- `src/risk/`: Risk manager, crisis detector, portfolio allocator.
- `src/execution/`: OMS engine, order slicing, trade log persistence.
- `src/monitoring/`: MLOps drift triggers, metrics reporting.
- `tests/`: Pytest suite.
