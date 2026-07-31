# Execution Plan: 5 Key Institutional-Grade Quantitative Enhancements

## Phase 0: System Exploration & Test Infrastructure Baseline (Milestone 0)
1. Spawn Explorer agent (`explorer_m0`) to map existing project structure, inspect existing tests in `tests/`, review `src/risk/risk_manager.py`, `src/ai/ensemble_scorer.py`, `src/core/event_driven.py`, and `trading_system/run_pipeline.py`.
2. Confirm python environment `.venv/Scripts/python.exe` and test command setup.
3. Spawn Explorer/Worker to audit existing pytest suite and generate initial test runner setup.

## Phase 1: Milestone Execution Loop (R1 to R5)
For each requirement (R1 to R5):
1. **Explorer Step**: Explore existing integration points, define complete technical design and test spec.
2. **Worker Step**: Implement module code and corresponding pytest file in `tests/`. Include mandatory integrity warning. Run unit tests and verify build.
3. **Reviewer Step**: Spawn 2 independent Reviewers to review code quality, edge cases, financial logic soundness, and test coverage.
4. **Challenger Step**: Spawn 2 Challengers to stress test and attempt to break the implementation with synthetic edge cases.
5. **Forensic Auditor Step**: Spawn Forensic Auditor to verify zero cheating / genuine implementation.
6. **Gate Check**: Proceed only when all pass & Forensic Auditor verdict is CLEAN.

## Milestone Schedule:
- **Milestone 1 (R1)**: Intraday Microstructure & Dynamic Stop-Loss Engine (`src/risk/intraday_stop_loss.py`, `RiskManager`, `run_pipeline.py`)
- **Milestone 2 (R2)**: Quad-Factor Neutral QP Portfolio Risk Optimizer (`src/strategy/quad_factor_optimizer.py`, Sharpe optimization, CVXPY/scipy.optimize QP solver, factor exposures, sector caps)
- **Milestone 3 (R3)**: CPCV & Historical Stress Testing Engine (`src/ai/cpcv_stress_tester.py`, Combinatorial Purged Cross Validation, 2008/2020/2022 historical stress tests)
- **Milestone 4 (R4)**: Closed-Loop Realized Slippage Execution Feedback (`src/execution/slippage_feedback.py`, `trade_logs.db`, `ensemble_scorer.py` dynamic cost update)
- **Milestone 5 (R5)**: LLM/NLP DART & SEC Filing Sentiment Engine (`src/core/llm_sentiment_engine.py`, FinBERT/LLM, `event_driven.py` catalyst integration)

## Phase 2: Final End-to-End Pipeline & System Acceptance (Milestone 6)
1. Run full pytest suite across all tests (`.venv/bin/pytest tests/ -v`).
2. Run end-to-end dry run verification of `run_pipeline.py` or synthetic test runs.
3. Verify output files (`ensemble_predictions.txt`, `pipeline_result.txt`, etc.) are updated without breaking any of the existing 18 strategies.
4. Deliver comprehensive completion report to Sentinel/User.
