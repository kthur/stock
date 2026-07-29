# Orchestration Plan: Stock Trading System (14-Strategy Ensemble & Pipeline)

## Overview
This plan defines the step-by-step milestone execution for high-precision Stock Trading System enhancements across 3,379 symbols (KOSPI, KOSDAQ, KONEX, SP500).

## Milestones

### Milestone 1: Exploration & System Audit
- **Objective**: Thoroughly investigate codebase, test suites (`pytest tests/`), current implementation of 14 strategies, 2D regime engine, backtest module, and coverage analyzer.
- **Deliverable**: `exploration_report.md` by Explorer subagent.

### Milestone 2: 14-Strategy Ensemble & 2D Market Regime Engine Enhancement (R1)
- **Objective**: Enhance dynamic weighting, 2D market regime GMM scoring (VIX, US10Y-US2Y, USDKRW), transaction costs & liquidity filtering, and net-return decision rationale.
- **Deliverable**: Refactored & verified `ensemble_scorer.py`, `prediction_model.py`, and related modules with tests passing.

### Milestone 3: Backtest Engine & Risk Management Enhancement (R2)
- **Objective**: Enhance backtest engine metrics (Sharpe ratio, MDD, win rate, return after costs), liquidity screening, and volatility-based position sizing.
- **Deliverable**: Refactored & verified backtesting/risk management modules and unit tests.

### Milestone 4: Strategy Data Coverage Report & Automated Test Suite (R3)
- **Objective**: Verify coverage analysis for 3,379 universe symbols, ensure `strategy_data_coverage_report.txt` generation and 100% pytest suite pass rate.
- **Deliverable**: Refactored `coverage_analyzer.py` and passing test suite.

### Milestone 5: Full E2E Execution & Forensic Audit Gate
- **Objective**: Run full pipeline (`run_pipeline.py`) with `.venv\Scripts\python.exe`, verify prediction outputs (`ensemble_predictions.txt`, `strategy_data_coverage_report.txt`), run full `pytest tests/`, and pass Forensic Integrity Audit.
- **Deliverable**: Complete E2E verification report & victory claim.

## Execution Strategy
- Use Project Orchestration pattern.
- For each milestone: Explorer -> Worker -> Reviewer -> Challenger -> Forensic Auditor cycle.
- All code changes strictly implemented by Worker subagents.
- Verification executed via `.venv\Scripts\python.exe`.
