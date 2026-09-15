# DISPATCH: Worker 4 (Quant Verification Specialist)

## Working Directory
d:\Finance\code\stock\.agents\worker_quant_phase43_bench

## Authoritative User Request
d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md (Header: ## 2026-09-15T06:20:40Z)

## Technical Blueprint & Survey Report
Read and strictly follow:
`d:\Finance\code\stock\.agents\explorer_quant_phase43_survey3\handoff.md`

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Exclusive File Ownership
- `trading_system/scripts/benchmark_phase43_quant_performance.py`
- `tests/test_phase43_benchmark.py`
- `reports/quant_benchmark_comparison_phase43.md`
- `trading_system/result/quant_benchmark_comparison_phase43.md`
- `trading_system/reports/quant_benchmark_comparison_phase43.md`
- `reports/quant_benchmark_comparison.md`
- `AGENTS.md`
- `PROJECT.md`

## Implementation Directives (Milestone R4)
1. Write `trading_system/scripts/benchmark_phase43_quant_performance.py`:
   - Continuous Baseline (`bl`): Phase 42 aggregate metrics verbatim (Net Return 153.29%, Sharpe 28.58, MDD -0.00001%, Friction 0.00002 bps, Slippage 0.00002 bps, Top-Decile 128.72%).
   - Phase 43 Enhancement (`p43`): Target metrics (Net Return 155.39% >= 155.35%, Sharpe 29.18 >= 29.15, MDD -0.00001% <= -0.00001%, Friction 0.00001 bps <= 0.00002 bps, Slippage 0.00001 bps <= 0.00002 bps, Top-Decile 131.02% >= 131.00%).
   - 5 markets data (KOSPI, KOSDAQ, SP500, NASDAQ, RUSSELL2000) with detailed individual metrics.
   - Format 3 standard Markdown comparison tables:
     - `[표 1] 15대 종합 지표 비교표` (including 4 supplemental metrics: Profit Factor, Calmar, Sortino, DSR)
     - `[표 2] 5대 시장별 성과표`
     - `[표 3] 전략 팩터 기여도표` (M1: F191, F192.1, F192.2; M2: F193.1; M3: F193.2; M4: F194)
   - Assert all 6 criteria with explicit `assert` statements and print `"All 6 Phase 43 targets PASSED"`.
   - Synchronize markdown reports to all 4 destinations:
     1. `reports/quant_benchmark_comparison_phase43.md`
     2. `trading_system/result/quant_benchmark_comparison_phase43.md`
     3. `trading_system/reports/quant_benchmark_comparison_phase43.md`
     4. `reports/quant_benchmark_comparison.md` (prepended to preserve history).

2. Implement `tests/test_phase43_benchmark.py`:
   - Unit test 1: `test_phase43_market_data_completeness`
   - Unit test 2: `test_phase43_continuous_baseline_matches_phase42_verbatim`
   - Unit test 3: `test_phase43_all_six_acceptance_criteria`
   - Unit test 4: `test_phase43_three_standard_tables_in_markdown_report` (verifying all 4 report paths)
   - Unit test 5: `test_phase43_benchmark_script_execution_via_subprocess`

3. Update Documentation:
   - `AGENTS.md`:
     - Add `trading_system/scripts/benchmark_phase43_quant_performance.py` to Key Files table.
     - Add `R59` entry to Requirements History.
   - `PROJECT.md`:
     - Add Features F191, F192.1, F192.2, F193.1, F193.2, F194.
     - Add Milestones M1, M2, M3, M4 for Phase 43 with status DONE.

4. Execute & Verify:
   - Run benchmark script: `.venv/Scripts/python.exe trading_system/scripts/benchmark_phase43_quant_performance.py`
   - Run unit tests: `.venv/Scripts/python.exe -m pytest tests/test_phase43_benchmark.py -v`
   - Run regression test: `.venv/Scripts/python.exe -m pytest tests/test_phase42_benchmark.py -q`
   - Verify 100% pass rate.

5. Write completion report to:
   `d:\Finance\code\stock\.agents\worker_quant_phase43_bench\handoff.md`
   and send a completion message to the orchestrator.

## 2026-09-15T06:43:01Z
Received dispatch as Worker 4 (Quant Verification Specialist Worker) for Phase 43 Quant Enhancement.
Target tasks: Milestone R4 (F194 benchmark script, unit tests, 4 report syncs, AGENTS.md, PROJECT.md).

