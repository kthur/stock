# Phase 4 Plan (Gen 2 Orchestrator)

## Objective
Drive Phase 4 Quantitative Trading System Enhancement to 100% completion:
1. Complete Milestone 2 Gating (verify Features F28~F33 with Reviewers, Challengers, Forensic Auditor).
2. Execute Milestone 3: Quantitative Benchmark Comparison Report across 5 markets (KOSPI, KOSDAQ, SP500, NASDAQ, RUSSELL2000), update AGENTS.md and PROJECT.md.
3. Execute Milestone 4: Full Test Suite Verification (2,333+ tests 100% pass) and Final Forensic Audit.
4. Final Handoff and Sentinel Notification.

## Work Breakdown
- **Milestone 2 Gating**:
  - Dispatch Reviewers, Challengers, and Forensic Auditor to independently test and audit `tests/test_phase4_portfolio_execution.py`, `src/risk/unified_portfolio_allocator.py`, `src/execution/smart_order_router.py`, `src/execution/oms_engine.py`.
  - Evaluate verdicts and record M2 PASS in `GATE_STATUS.md`.
- **Milestone 3: Benchmark Quantification & Report Generation**:
  - Dispatch Worker to run/implement `trading_system/scripts/benchmark_phase4_quant_performance.py`.
  - Generate comprehensive comparison Markdown tables covering: Net Expected Return, Total Return, Sharpe Ratio, Information Coefficient (Rank-IC), Maximum Drawdown (MDD), Turnover & Trading Costs, Top-Decile Spread & Execution Slippage.
  - Save to:
    - `reports/quant_benchmark_comparison_phase4.md`
    - `trading_system/result/quant_benchmark_comparison_phase4.md`
    - `reports/quant_benchmark_comparison.md`
  - Update `AGENTS.md` and `PROJECT.md` to reflect Phase 4 completion.
  - Gate M3 with Reviewer and Challenger.
- **Milestone 4: Full Test Suite Verification & Audit**:
  - Dispatch Worker / Test Writer to run full pytest suite (`.venv\Scripts\python.exe -m pytest tests/ -q`).
  - Confirm 2,333+ tests pass 100% with zero regressions.
  - Final Forensic Audit confirming clean code with zero cheating.
- **Handoff**:
  - Write `handoff.md` and send victory message to sentinel.
