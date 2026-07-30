# Original User Request

## Initial Request — 2026-07-30T23:20:24+09:00

You are the Project Orchestrator for the Stock Trading System Full-scale Optimization project.

Working directory: d:\Finance\code\stock\.agents\orchestrator
Original request file: d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md

Please create your workspace directory at `d:\Finance\code\stock\.agents\orchestrator`, create your `BRIEFING.md` and `plan.md`, and orchestrate subagent specialists to execute the full-scale system architecture & quantitative financial engineering optimization across all requirements (R1-R4):

### R1. Architecture Modularization & Data Engine Upgrade
- Refactor monolithic `run_pipeline.py` into a DAG-based modular pipeline architecture with checkpointing & resumability.
- Upgrade SQLite database layer to Parquet/TimescaleDB hybrid schema to eliminate write-lock bottlenecks during multi-asset streaming.

### R2. Quantitative Alpha & Ensemble Orthogonalization
- Implement Gram-Schmidt / PCA Factor Orthogonalization in `EnsembleScoringEngine` to remove multicollinearity and alpha overlap across 17 strategies.
- Add K-Means/OPTICS pre-clustering to `StatisticalArbitrageEngine` to cut cointegration scanning from O(N^2) to O(N log N).

### R3. Risk Management & Portfolio Optimization Enhancement
- Integrate Extreme Value Theory (EVT) CVaR constraints into `PortfolioAllocator`.
- Implement dynamic band-based rebalancing to minimize STT and transaction cost drag.

### R4. Execution Engine & MLOps Monitoring
- Add TWAP/VWAP Order Slicing to the OMS Engine for low-liquidity stocks.
- Implement real-time slippage feedback loop to dynamic ensemble weights and MLflow drift triggers for continuous retraining.

### Acceptance Criteria
- [ ] All unit tests in `tests/` pass cleanly via `.venv\Scripts\python.exe -m pytest`.
- [ ] Pipeline execution allows resuming from checkpointed tasks upon failure.
- [ ] Cointegration pair scanning runs in under 30 seconds for 3,379 symbols.
- [ ] Portfolio backtest demonstrates reduced turnover and zero write-lock concurrency errors.

Instructions:
1. Break down work into clear milestones with verification steps.
2. Delegate tasks to specialized subagents or execute them carefully, ensuring tests are updated and passing.
3. Update `progress.md` continuously as milestones progress.
4. When ALL milestones are complete and verified by unit tests, notify Sentinel with a completion report.
