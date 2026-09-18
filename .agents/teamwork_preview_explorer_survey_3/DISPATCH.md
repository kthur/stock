# DISPATCH: Survey Explorer 3 — Benchmark & Quantitative Verification

## Working Directory
d:\Finance\code\stock\.agents\teamwork_preview_explorer_survey_3

## Role & Mission
You are Survey Explorer 3. Your mission is to explore and analyze the authoritative codebase for Phase 55 Verification Benchmarking (F250), 5 test suites, 4-path markdown report synchronization, and document updates.

## Authoritative Files to Read
1. `d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md` (Header: `## 2026-09-18T03:36:46Z`)
2. `d:\Finance\code\stock\.agents\orchestrator_quant_phase55_1\DISPATCH.md`
3. `trading_system/scripts/benchmark_phase54_quant_performance.py`: Inspect the structure of the Phase 54 benchmark engine, 15 metrics across 5 markets, comparison tables, and report outputs.
4. `reports/quant_benchmark_comparison_phase54.md` and `reports/quant_benchmark_comparison.md`: Inspect the formatting, markdown table structures, and report conventions.
5. `tests/test_phase54_alpha.py`, `tests/test_phase54_risk.py`, `tests/test_phase54_oms.py`, `tests/test_phase54_adversarial_challenger1.py`, `tests/test_phase54_adversarial_oms_benchmark.py`: Inspect test suites and structure.
6. `AGENTS.md` and `PROJECT.md`: Inspect where Phase 54 was documented and where Phase 55 features F246~F250 must be appended.

## Deliverables
Write a comprehensive report to `d:\Finance\code\stock\.agents\teamwork_preview_explorer_survey_3\survey_report.md` detailing:
1. Exact structure and implementation plan for `trading_system/scripts/benchmark_phase55_quant_performance.py`:
   - 15 metrics across 5 markets (KOSPI, KOSDAQ, S&P 500, NASDAQ, RUSSELL 2000).
   - Baseline: Phase 54 (Net Return 178.49%, Sharpe 35.78, MDD -0.00001%, Costs 0.000000005859375 bps, Slippage 0.0000000048828125 bps, Alpha Spread 156.32%).
   - Target: Phase 55 (Net Return >= 180.55%, Target 180.59%; Sharpe >= 36.35, Target 36.38; MDD <= -0.00001%; Costs <= 0.0000000029296875 bps; Slippage <= 0.00000000244140625 bps; Alpha Spread >= 158.60%, Target 158.62%; Win Rate 100.0%).
2. Report generation and synchronization requirements across 4 canonical paths:
   - `reports/quant_benchmark_comparison_phase55.md`
   - `trading_system/result/quant_benchmark_comparison_phase55.md`
   - `trading_system/reports/quant_benchmark_comparison_phase55.md`
   - `reports/quant_benchmark_comparison.md` (prepended with Phase 55 section)
3. Specifications for the 5 automated test suites:
   - `tests/test_phase55_alpha.py`
   - `tests/test_phase55_risk.py`
   - `tests/test_phase55_oms.py`
   - `tests/test_phase55_adversarial_challenger1.py`
   - `tests/test_phase55_adversarial_oms_benchmark.py`
4. Required updates to `AGENTS.md` and `PROJECT.md`.
5. Write `handoff.md` and send completion message back to orchestrator.
