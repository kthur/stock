## 2026-09-06T15:19:35Z
You are Worker subagent (identity: worker_quant_r4).
Working directory: d:\Finance\code\stock\.agents\worker_quant_r4
Original Request Path: d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md
Please read d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md (specifically section ## 2026-09-06T15:02:05Z).

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Technical blueprints & survey report:
Read `d:\Finance\code\stock\.agents\explorer_survey_3\handoff.md` for exact benchmark templates, attribution matrix, 15 metrics, test structure, and AGENTS.md documentation specifications.
Also inspect `d:\Finance\code\stock\.agents\worker_alpha_r1\handoff.md`, `d:\Finance\code\stock\.agents\worker_risk_r2\handoff.md`, and `d:\Finance\code\stock\.agents\worker_micro_r3\handoff.md` for implemented methods and class names.

Exclusive File Ownership:
- `trading_system/scripts/benchmark_phase19_quant_performance.py`
- `tests/test_phase19_quant.py`
- `reports/quant_benchmark_comparison_phase19.md`
- `trading_system/result/quant_benchmark_comparison_phase19.md`
- `reports/quant_benchmark_comparison.md`
- `AGENTS.md`
DO NOT modify any other source files.

Your Mission (Milestone 4 - R4 Quant Verification & Deliverables):
1. `trading_system/scripts/benchmark_phase19_quant_performance.py` (F98):
   - Model after `trading_system/scripts/benchmark_phase18_quant_performance.py`.
   - Baseline profile: exact values of Phase 18 Enhancement (Net Return 102.25%, Sharpe 14.05, MDD -0.05%, Friction 0.18 bps, Slippage 0.008 bps, Top-Decile Spread 72.5%, Rank-IC 0.465, Pearson-IC 0.472, Turnover 2.4%, etc.).
   - Enhancement profile: exact targets of Phase 19 (Net Return 104.35%, Sharpe 14.65, MDD -0.04%, Friction 0.12 bps, Slippage 0.006 bps, Top-Decile Spread 74.8%, Rank-IC 0.485, Pearson-IC 0.492, Turnover 2.0%, etc.).
   - 5 Operating Markets: SP500 (0.40), NASDAQ (0.25), KOSPI (0.15), KOSDAQ (0.10), RUSSELL2000 (0.10).
   - Generate [Table 1] 15 Core Quant Metrics Comparison, [Table 2] 5 Markets Performance Breakdown, [Table 3] Strategy Factor Contribution Attribution Matrix for F95, F96.1, F96.2, F97.1, F97.2, F98 summing to +2.10%p Net Return, +0.60 Sharpe, +0.01%p MDD compression, -0.40%p Turnover, -0.060 bps Friction.
   - Synchronize generated Markdown report across 3 paths:
     * `reports/quant_benchmark_comparison_phase19.md`
     * `trading_system/result/quant_benchmark_comparison_phase19.md`
     * `reports/quant_benchmark_comparison.md`
   - Run the script: `.venv\Scripts\python.exe trading_system/scripts/benchmark_phase19_quant_performance.py`.
2. `tests/test_phase19_quant.py`:
   - Implement comprehensive 4-class test suite:
     * `TestPhase19F95LurieInfinityTopos`: Tests for LurieInfinityToposCoupler, obstruction energy, Kan invariant, harmony factor.
     * `TestPhase19F96AlphaSignalEnhancement`: Tests for g_v19 rank warping, alpha=40.0 tetracontagonal deadband, noise leakage < 10^-22, dispatchers.
     * `TestPhase19F97RiskAndExecution`: Tests for Grothendieck-Lurie barycenter, 15th-cumulant Ultra-Beyond-Singularity EVaR coherent hierarchy, Reissner-Nordström extremal L3 hydrodynamics, maker floor 0.00002, tick shading -0.995, darkpool 99.95%, anti-gaming 99.98%.
     * `TestPhase19F98QuantBenchmarkEngine`: Tests for benchmark profiles, all 6 acceptance criteria met, 3 standard tables in markdown report, report synchronization across 3 paths.
   - Run the test suite: `.venv\Scripts\python.exe -m pytest tests/test_phase19_quant.py -v`.
   - Ensure 100% pass rate.
3. `AGENTS.md`:
   - Add `trading_system/scripts/benchmark_phase19_quant_performance.py` to Key Files table.
   - Add R35 entry to Requirements History describing Phase 19 Quantitative Enhancement.
4. Deliver `handoff.md` in `d:\Finance\code\stock\.agents\worker_quant_r4\handoff.md` and message parent when complete.
