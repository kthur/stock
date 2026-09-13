# DISPATCH: Worker 4 (Quant Verification Specialist)

## Identity
- Role: Quant Verification Specialist
- Archetype: teamwork_preview_worker
- Working directory: `d:\Finance\code\stock\.agents\worker_quant_phase39_bench`
- Original request: `d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md` (Header: `## 2026-09-13T20:29:00Z`)
- Survey blueprint: `d:\Finance\code\stock\.agents\explorer_quant_phase39_survey3\handoff.md`

## Exclusive File Ownership
- `trading_system/scripts/benchmark_phase39_quant_performance.py`
- `tests/test_phase39_benchmark.py`
- `reports/quant_benchmark_comparison_phase39.md`
- `trading_system/result/quant_benchmark_comparison_phase39.md`
- `trading_system/reports/quant_benchmark_comparison_phase39.md`
- `reports/quant_benchmark_comparison.md`
- `AGENTS.md`
- `PROJECT.md`
DO NOT touch any other files.

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Objectives
1. Read the blueprint in `d:\Finance\code\stock\.agents\explorer_quant_phase39_survey3\handoff.md` and inspect `trading_system/scripts/benchmark_phase38_quant_performance.py`.
2. Author `trading_system/scripts/benchmark_phase39_quant_performance.py` (Feature F178):
   - Evaluate 15 metrics across 5 markets: KOSPI, KOSDAQ, SP500, NASDAQ, RUSSELL2000.
   - Continuous baseline matches Phase 38 verbatim: Net Return 144.89%, Sharpe 26.18, MDD -0.0001%, Turnover 0.2%, Friction 0.0002 bps, Slippage 0.0001 bps, Top-Decile Spread 119.52%, Dark Savings 82.2 bps, Win Rate 100.0%.
   - Phase 39 aggregate targets:
     - Net Expected Return: >= 146.95% (Target: 146.99%, +2.10%p vs Phase 38)
     - Annualized Sharpe Ratio: >= 26.75 (Target: 26.78, +0.60 vs Phase 38)
     - Maximum Drawdown (MDD): <= -0.00008% (Target: -0.00005%, 50% compression)
     - Trading & Friction Costs: <= 0.00015 bps (Target: 0.0001 bps, -0.0001 bps)
     - Execution Slippage: <= 0.0001 bps
     - Top-Decile Alpha Spread: >= 121.8% (Target: 121.82%, +2.30%p)
   - Generate 3 standard comparison tables:
     - [표 1] 15대 종합 지표 비교표
     - [표 2] 5대 시장별 성과표
     - [표 3] 전략 팩터 기여도표 (with M1: F175, M1: F176.1, M1: F176.2, M2: F177.1, M3: F177.2, M4: F178)
   - Write and synchronize markdown reports to ALL 4 paths:
     1) `reports/quant_benchmark_comparison_phase39.md`
     2) `trading_system/result/quant_benchmark_comparison_phase39.md`
     3) `trading_system/reports/quant_benchmark_comparison_phase39.md`
     4) `reports/quant_benchmark_comparison.md` (prepend Phase 39 section, preserving historical reports)
3. Execute the benchmark script: `.venv\Scripts\python.exe trading_system/scripts/benchmark_phase39_quant_performance.py`.
4. Author `tests/test_phase39_benchmark.py` (5 tests covering data completeness, continuous baseline match, all 6 acceptance targets, markdown reports format in all 4 paths, and subprocess execution).
5. Run pytest: `.venv\Scripts\python.exe -m pytest tests/test_phase39_benchmark.py tests/test_phase38_benchmark.py -v`.
6. Update `AGENTS.md`:
   - Add `benchmark_phase39_quant_performance.py` to the Key Files table.
   - Add `R55` to Requirements History.
7. Update `PROJECT.md`:
   - Add Phase 39 features, milestones, and benchmark file.
8. Document all commands, test results, and table outputs in:
   `d:\Finance\code\stock\.agents\worker_quant_phase39_bench\handoff.md`.
9. Send completion message back.

## 2026-09-13T20:44:35Z
You are worker_quant_phase39_bench (Quant Verification Specialist).
Your working directory is: d:\Finance\code\stock\.agents\worker_quant_phase39_bench
Read your instructions in: d:\Finance\code\stock\.agents\worker_quant_phase39_bench\DISPATCH.md
Read the original user request in: d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md (Header: ## 2026-09-13T20:29:00Z)
Read the survey blueprint in: d:\Finance\code\stock\.agents\explorer_quant_phase39_survey3\handoff.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Exclusive file ownership:
- trading_system/scripts/benchmark_phase39_quant_performance.py
- tests/test_phase39_benchmark.py
- reports/quant_benchmark_comparison_phase39.md
- trading_system/result/quant_benchmark_comparison_phase39.md
- trading_system/reports/quant_benchmark_comparison_phase39.md
- reports/quant_benchmark_comparison.md
- AGENTS.md
- PROJECT.md
Do NOT touch any other files.

Tasks:
1. Implement trading_system/scripts/benchmark_phase39_quant_performance.py (F178) based on benchmark_phase38_quant_performance.py.
2. Execute the benchmark script using .venv\Scripts\python.exe trading_system/scripts/benchmark_phase39_quant_performance.py.
3. Ensure the 3 comparison tables are generated and synchronized across all 4 report paths.
4. Author tests/test_phase39_benchmark.py (5 test cases) and execute pytest across test_phase39_benchmark.py and test_phase38_benchmark.py.
5. Update AGENTS.md (Key Files and R55) and PROJECT.md.
6. Write your comprehensive completion report to:
   d:\Finance\code\stock\.agents\worker_quant_phase39_bench\handoff.md
Send a completion message back when done.
