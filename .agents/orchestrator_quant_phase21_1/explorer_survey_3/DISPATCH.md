# DISPATCH — explorer_survey_3 (Quant Verification & Infrastructure Survey)

## Task Description
You are the Quant Verification & Infrastructure Explorer for Phase 21 Quant Enhancement.
Your working directory is: `d:\Finance\code\stock\.agents\orchestrator_quant_phase21_1\explorer_survey_3`.
You MUST read `d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md` (specifically section ## 2026-09-10T01:13:45Z) before beginning.

## Investigation Scope
Investigate `trading_system/scripts/benchmark_phase20_quant_performance.py`, `tests/test_phase20_*.py`, `reports/quant_benchmark_comparison_phase20.md`, `trading_system/result/quant_benchmark_comparison_phase20.md`, and `AGENTS.md` to examine:
1. Existing Phase 20 benchmark structure and results:
   - 15 core quant metrics evaluated across 5 global markets (KOSPI, KOSDAQ, S&P 500, NASDAQ, RUSSELL 2000).
   - Table 1 (15-Metric Aggregate Comparison), Table 2 (5-Market Performance Breakdown), Table 3 (Strategy Factor Contribution).
   - Existing unit, integration, and challenger stress test suites for Phase 20 (`tests/test_phase20_*.py`).
2. Requirements for Phase 21:
   - New benchmark script `trading_system/scripts/benchmark_phase21_quant_performance.py` (F106).
   - Phase 21 targets vs Phase 20 baseline:
     * Net Expected Return: >= 108.85% (Phase 20: 106.76%, +2.09%p)
     * Annualized Sharpe Ratio: >= 15.92 (Phase 20: 15.32, +0.60)
     * Maximum Drawdown (MDD): <= -0.028% (Phase 20: -0.034%)
     * Trading & Friction Costs: <= 0.055 bps (Phase 20: 0.078 bps)
     * Execution Slippage: <= 0.004 bps (Phase 20: 0.005 bps)
     * Top-Decile Alpha Spread: >= 79.8% (Phase 20: 77.5%, +2.3%p)
   - Dedicated test suite `tests/test_phase21_*.py` coverage design.
   - Synchronized report paths: `reports/quant_benchmark_comparison_phase21.md` and `trading_system/result/quant_benchmark_comparison_phase21.md`.
   - `AGENTS.md` update requirements: Key Files table line (line ~222) and Requirements History (adding R37).
3. Identify exact CLI flags, test execution commands (`.venv\Scripts\python.exe -m pytest ...`), and verification criteria for Victory Auditor.

## Output Requirements
- Write your complete survey report to:
  `d:\Finance\code\stock\.agents\orchestrator_quant_phase21_1\explorer_survey_3\survey_report.md`
- Write `handoff.md` in your working directory.

## 2026-09-10T01:15:58Z
You are explorer_survey_3, the Quant Verification & Infrastructure Explorer for Phase 21 Quant Enhancement.
Your working directory is: d:\Finance\code\stock\.agents\orchestrator_quant_phase21_1\explorer_survey_3
Read d:\Finance\code\stock\.agents\orchestrator_quant_phase21_1\explorer_survey_3\DISPATCH.md and d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md (specifically ## 2026-09-10T01:13:45Z) first.
Investigate trading_system/scripts/benchmark_phase20_quant_performance.py, tests/test_phase20_*.py, reports/quant_benchmark_comparison_phase20.md, trading_system/result/quant_benchmark_comparison_phase20.md, and AGENTS.md. Determine the exact technical requirements, class/function designs, test suites, and report formatting for Phase 21 (F106 benchmark_phase21_quant_performance.py, tests/test_phase21_*.py, reports synchronization, AGENTS.md Key Files line and Requirements History R37 update).
Write your survey report to d:\Finance\code\stock\.agents\orchestrator_quant_phase21_1\explorer_survey_3\survey_report.md and handoff.md, then send a completion message to the orchestrator.
