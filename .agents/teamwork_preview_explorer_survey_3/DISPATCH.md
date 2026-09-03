## 2026-09-03T11:56:34Z
You are an Explorer agent (teamwork_preview_explorer) surveying the codebase for Milestone 3 / Requirement 3 (R3 & Test Suite).
Your identity: Explorer Survey 3 (Test Suite & Quantitative Benchmark Expert)
Your working directory: d:\Finance\code\stock\.agents\teamwork_preview_explorer_survey_3
Parent conversation ID: 9f89ea60-abb5-4468-88df-62eb0473f19b

MANDATORY FIRST STEP:
Read d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md and d:\Finance\code\stock\system_improvement_plan_v8.md.

TASK:
Investigate and produce a detailed, actionable blueprint for R3 & Test Suite Verification:
1. Investigate the current test suite under `tests/`:
   - Identify total test count and test files.
   - Inspect the known failing assertion in `tests/test_institutional_portfolio_construction.py:193` (HIGH-01: KRX 1-share lot reform assert `assert p_krx["lot_size"] == 10` -> `1`).
   - Identify any other potential test regressions or fragile test assertions.
2. Investigate how system performance is evaluated and measured:
   - Check how expected returns, Sharpe ratio, Information Coefficient (IC/Rank-IC), MDD, turnover, and transaction costs are computed in `run_pipeline.py`, `reporter.py`, `generate_report.py`, and `coverage_analyzer.py`.
   - Design a clean, reproducible quantitative benchmarking script/methodology (e.g. `scripts/benchmark_quant_performance.py` or similar) that evaluates the system before and after optimizations across the 5 markets (KOSPI, KOSDAQ, SP500, NASDAQ, RUSSELL2000).
   - Design the exact schema for the Quantitative Comparison Table required by R3 (Expected Return, Sharpe Ratio, IC/Rank-IC, MDD, Turnover %, Friction Cost Reduction %, etc.).
3. For each item, provide: exact file path, line numbers, current behavior vs required behavior, and exact implementation guidance.

OUTPUT:
Write your comprehensive investigation report to `d:\Finance\code\stock\.agents\teamwork_preview_explorer_survey_3\handoff.md`.
Update `d:\Finance\code\stock\.agents\teamwork_preview_explorer_survey_3\progress.md` with timestamps.
Send a message back to parent when complete.
