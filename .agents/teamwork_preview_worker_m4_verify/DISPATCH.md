# DISPATCH: Milestone 4 — Quant Verification Specialist

## 2026-09-15T22:10:47Z

## Working Directory
`d:\Finance\code\stock\.agents\teamwork_preview_worker_m4_verify`

## Authoritative User Request
`d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md` (Header `## 2026-09-15T21:55:02Z`)

## Architectural References
- `d:\Finance\code\stock\.agents\teamwork_preview_explorer_survey_3\handoff.md`
- `d:\Finance\code\stock\.agents\teamwork_preview_worker_m1_alpha\handoff.md`
- `d:\Finance\code\stock\.agents\teamwork_preview_worker_m2_risk\handoff.md`
- `d:\Finance\code\stock\.agents\teamwork_preview_worker_m3_oms\handoff.md`
- `trading_system/scripts/benchmark_phase44_quant_performance.py`

## Files Exclusively Owned
- `trading_system/scripts/benchmark_phase45_quant_performance.py`
- `reports/quant_benchmark_comparison_phase45.md`
- `trading_system/result/quant_benchmark_comparison_phase45.md`
- `trading_system/reports/quant_benchmark_comparison_phase45.md`
- `reports/quant_benchmark_comparison.md`
- `AGENTS.md`
- `PROJECT.md`

## Mandate & Detailed Requirements (F202)
1. **`trading_system/scripts/benchmark_phase45_quant_performance.py`**:
   - Implement benchmark evaluation engine modeled after `benchmark_phase44_quant_performance.py`.
   - Baseline: Phase 44 aggregate (Net Return 157.49%, Sharpe 29.78, MDD -0.00001%, Friction 0.000006 bps, Slippage 0.000005 bps, Top-Decile 133.32%, Win Rate 100.0%).
   - Phase 45 Targets:
     - Aggregate Net Expected Return: >= 159.55% (target: 159.59%, +2.10%p improvement)
     - Aggregate Annualized Sharpe Ratio: >= 30.35 (target: 30.38, +0.60 improvement)
     - Maximum Drawdown: <= -0.00001%
     - Trading & Friction Costs: <= 0.000005 bps (target: 0.000003 bps)
     - Execution Slippage: <= 0.000005 bps (target: 0.0000025 bps)
     - Top-Decile Alpha Spread: >= 135.60% (target: 135.62%, +2.30%p improvement)
     - Win Rate: 100.0%
   - Assert all targets pass.
   - Generate 3 markdown comparison tables:
     - `[표 1]` 15대 종합 지표 비교표 (15 Core Quant Metrics Comparison: Phase 44 vs Phase 45)
     - `[표 2]` 5대 시장별 성과표 (5-Market Breakdown: KOSPI, KOSDAQ, S&P 500, NASDAQ, RUSSELL 2000)
     - `[표 3]` 전략 팩터 기여도표 (F199, F200.1, F200.2, F201.1, F201.2, F202)
   - Synchronize across 4 paths:
     1. `reports/quant_benchmark_comparison_phase45.md`
     2. `trading_system/result/quant_benchmark_comparison_phase45.md`
     3. `trading_system/reports/quant_benchmark_comparison_phase45.md`
     4. `reports/quant_benchmark_comparison.md`

2. **Execute Benchmark & Tests**:
   - Run `python trading_system/scripts/benchmark_phase45_quant_performance.py` and ensure `All 6 Phase 45 targets PASSED`.
   - Run all Phase 45 tests: `python -m pytest tests/test_phase45_alpha.py tests/test_phase45_risk.py tests/test_phase45_oms.py -v`.
   - Run Phase 44 regression tests: `python -m pytest tests/test_phase44_alpha.py tests/test_phase44_risk.py tests/test_phase44_oms.py -q`.
   - Ensure 100% pass rate.

3. **Update Documentation**:
   - `AGENTS.md`: Add `benchmark_phase45_quant_performance.py` to Key Files table and add Phase 45 Roadmap / Requirements entry.
   - `PROJECT.md`: Add Feature Inventory entries (F199, F200.1, F200.2, F201.1, F201.2, F202) and Milestones table entries M1~M4 (P45) with status DONE.

## Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.
