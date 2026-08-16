# Orchestration Plan: Stock Trading System Optimization

## Overview
Optimize 31-strategy multi-factor equity trading system (`kthur/stock`), including quantitative alpha engines, ensemble scoring, portfolio risk parity/allocation, microstructure cost models, pipeline concurrency & performance, 100% test suite verification, and Git deployment.

## Milestones
1. **Survey & System Blueprinting**
   - Survey Alpha Engines & Ensemble Scorer (R1)
   - Survey Portfolio Allocation, Microstructure Costs & Execution (R2)
   - Survey Pipeline Architecture, Data Layer, Test Suite & Git Status (R3 & R4)
   - Synthesize survey findings into `PROJECT.md`

2. **Milestone 1: Alpha Engines & Ensemble Scoring Optimization (R1)**
   - Verify 31 alpha strategy engines coverage, math/scoring integrity, Information Coefficient and Sharpe optimization
   - Verify lookahead bias prevention (60d filing lag, cross-timezone lag shifts), multicollinearity reduction (PCA orthogonalization, VIF filters), outlier winsorization

3. **Milestone 2: Portfolio Asset Allocation & Microstructure Execution (R2)**
   - HRP (Hierarchical Risk Parity), Ledoit-Wolf Shrinkage covariance, EVT-CVaR risk budgeting
   - Almgren-Chriss/Kyle market impact costs, dynamic spread, STT/SEC fee models, Leland turnover buffer bands

4. **Milestone 3: System Pipeline Concurrency & Memory Optimization (R3)**
   - 3,379 symbols vectorization, ThreadPoolExecutor parallelization, float32 memory downcasting
   - SQLite WAL mode write mutex protection, NaN handling and crisis gateway safety

5. **Milestone 4: Full Test Suite Verification & Git Deployment (R4)**
   - Run `.venv\Scripts\python.exe -m pytest tests/ -v --tb=short` to ensure 100% passing rate
   - Final review and verification
   - Stage, commit with detailed summary, and push to `origin/main`
