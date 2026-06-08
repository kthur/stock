# Project Plan: Phase 4 Trading System Upgrade

## Overview
This plan details the steps required to implement the 5 backend strategy logics (R1-R4) and 3 Dash UI improvements (R5), passing the 60 E2E tests and forensic integrity verification.

## Milestones

### Milestone 1: Environment & Codebase Exploration
- **Objectives**: Inspect existing source code and tests. Run the test suite to establish a baseline.
- **Steps**:
  1. Spawn Explorer to analyze:
     - `src/analysis/backtest.py`
     - `src/core/strategy_engine.py`
     - `trading_system.py`
     - `src/analysis/screener.py`
     - `src/web/dashboard.py`
     - `tests/phase4/e2e/test_e2e.py`
  2. Spawn Worker to run the current pytest suite and report failing/passing test cases.

### Milestone 2: Backend Logic Implementation (R1, R2, R3, R4)
- **Objectives**: Complete implementation of parameter optimization, market regime detection, trailing stop, and stock screener.
- **Steps**:
  1. Complete Grid Search parameter optimization (R1) and ensure JSON caching (`data/optimized_params.json`).
  2. Implement/complete Market Regime Detection (R2) in `HybridStrategyEngine` using EMA200, ATR ratio, and ROC momentum.
  3. Implement Trailing Stop (R3) in `trading_system.py` using high watermark and ATR * 2.
  4. Implement `StockScreener` (R4) in `src/analysis/screener.py` with criteria filtering.
  5. Spawn Worker to implement these changes.
  6. Spawn Reviewer to inspect the backend changes.

### Milestone 3: Web UI Dash Improvements (R5)
- **Objectives**: Implement the 3 required tabs/sections in `src/web/dashboard.py` and run dashboard verification.
- **Steps**:
  1. Implement Strategy Performance Comparison tab.
  2. Implement Real-Time Position & P&L Status tab.
  3. Implement Backtest Result Viewer tab.
  4. Spawn Worker to update the dashboard.
  5. Spawn Reviewer to verify UI components and callbacks.

### Milestone 4: Verification, Adversarial Hardening & Forensic Audit
- **Objectives**: Pass all E2E tests and forensic audit.
- **Steps**:
  1. Spawn Worker to run E2E test suite (`python -m pytest tests/phase4/e2e/test_e2e.py -v`).
  2. Spawn Challenger to perform stress/adversarial testing.
  3. Spawn Forensic Auditor to run integrity checks.
  4. Verify clean audit status and 100% test pass.
