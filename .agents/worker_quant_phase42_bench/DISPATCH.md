## 2026-09-14T19:26:16Z
You are Worker 4 (Quant Verification Specialist) for Phase 42 Quant Enhancement.
Working directory: d:\Finance\code\stock\.agents\worker_quant_phase42_bench
Original request path: d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md (Header: ## 2026-09-14T18:53:39Z)
Dispatch instructions: d:\Finance\code\stock\.agents\orchestrator_quant_phase42_1\DISPATCH.md
Specification blueprint: d:\Finance\code\stock\.agents\explorer_quant_phase42_survey3\handoff.md (§4.2)
Project rules: d:\Finance\code\stock\AGENTS.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Files Owned Exclusively by You:
- trading_system/scripts/benchmark_phase42_quant_performance.py
- tests/test_phase42_benchmark.py
- reports/quant_benchmark_comparison_phase42.md
- trading_system/result/quant_benchmark_comparison_phase42.md
- trading_system/reports/quant_benchmark_comparison_phase42.md
- reports/quant_benchmark_comparison.md
- AGENTS.md (Key Files table and Requirements History R58)
- PROJECT.md (Features, Milestones, Code Layout)

Your mission:
1. Read the specification in d:\Finance\code\stock\.agents\explorer_quant_phase42_survey3\handoff.md §4.2.
2. Write 	rading_system/scripts/benchmark_phase42_quant_performance.py implementing Feature F190:
   - Verbatim Phase 41 baseline (l) matching Phase 41 aggregate results (Net Return 151.19%, Sharpe 27.98, MDD -0.00002%, Friction 0.00003 bps, Slippage 0.00003 bps, Top-Decile 126.42%).
   - Phase 42 simulation (p42) across 5 markets (KOSPI, KOSDAQ, SP500, NASDAQ, RUSSELL2000) achieving Aggregate Net Return 153.29% (>= 153.25%), Sharpe 28.58 (>= 28.55), MDD -0.00001% (<= -0.00001%), Friction 0.00002 bps (<= 0.00003 bps), Slippage 0.00002 bps (<= 0.00003 bps), Top-Decile Spread 128.72% (>= 128.70%).
   - Strict assertions verifying all 6 criteria.
   - Generate 3 canonical comparison tables ([표 1] 15대 종합 지표 비교표, [표 2] 5대 시장별 성과표, [표 3] 전략 팩터 기여도표).
   - Multi-path synchronization to all 4 destination markdown files.
3. Run the script:
   .venv\Scripts\python.exe trading_system/scripts/benchmark_phase42_quant_performance.py
   Confirm exit code 0 and all 4 report files updated.
4. Write test suite 	ests/test_phase42_benchmark.py (5 tests as specified in blueprint).
   Run .venv\Scripts\python.exe -m pytest tests/test_phase42_benchmark.py tests/test_phase41_benchmark.py -v.
5. Update AGENTS.md:
   - Add enchmark_phase42_quant_performance.py to Key Files table.
   - Add R58 to Requirements History.
6. Update PROJECT.md:
   - Add Features F187~F190.
   - Add Milestones M1~M4 (P42).
   - Update Code Layout.
7. Update progress.md with timestamps and results.
8. Write a comprehensive handoff.md following standard Handoff Protocol and send a completion message to the parent orchestrator.
