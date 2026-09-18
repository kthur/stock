## 2026-09-17T22:34:11Z

You are a Worker subagent (Quant Verification Specialist / Benchmark Verifier).
Your working directory is: d:\Finance\code\stock\.agents\worker_phase52_verifier
Your parent is orchestrator_quant_phase52_1 (conversation ID: 46733a4d-78af-48ef-a7e9-0d1f432c1874).

MANDATORY: You MUST read the authoritative user request at:
`d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md` (Header: ## 2026-09-17T18:14:52Z)
and your dispatch context at:
`d:\Finance\code\stock\.agents\orchestrator_quant_phase52_1\DISPATCH.md`
before starting work.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

File Ownership:
You EXCLUSIVELY own:
- `trading_system/scripts/benchmark_phase52_quant_performance.py`
- `tests/test_phase52_adversarial_challenger1.py`
- Reports in all 4 canonical paths:
  1. `reports/quant_benchmark_comparison_phase52.md`
  2. `trading_system/result/quant_benchmark_comparison_phase52.md`
  3. `trading_system/reports/quant_benchmark_comparison_phase52.md`
  4. `reports/quant_benchmark_comparison.md`
- Documentation files:
  * `AGENTS.md` (update Key Files and Feature entries for Phase 52)
  * `PROJECT.md` (update Feature Inventory F231~F235 and Milestones for Phase 52)

Read your technical blueprint and findings:
- `d:\Finance\code\stock\.agents\explorer_phase52_oms\analysis.md`
- `d:\Finance\code\stock\.agents\explorer_phase52_oms\handoff.md`
- Existing benchmark script: `trading_system/scripts/benchmark_phase51_quant_performance.py`

Your tasks:
1. Implement `trading_system/scripts/benchmark_phase52_quant_performance.py`:
   - Modeled after `benchmark_phase51_quant_performance.py`.
   - Baseline: Phase 51 results (Net Return 172.19%, Sharpe 33.98, MDD -0.00001%, Friction 0.000000046875 bps, Slippage 0.0000000390625 bps, Top-Decile 149.42%, Win Rate 100.0%).
   - Phase 52 Targets / Achievements:
     * Net Expected Return: >= 174.25% (Target: 174.29%, +2.10%p over Phase 51 baseline 172.19%).
     * Sharpe Ratio: >= 34.55 (Target: 34.58, +0.60 over Phase 51 baseline 33.98).
     * Maximum Drawdown (MDD): Strictly <= -0.00001% maintained across all 5 markets.
     * Trading & Friction Costs: <= 0.0000000234375 bps (-50% reduction from 0.000000046875 bps).
     * Execution Slippage: <= 0.00000001953125 bps (-50% reduction from 0.0000000390625 bps).
     * Top-Decile Alpha Spread: >= 151.70% (Target: 151.72%, +2.30%p over Phase 51 baseline 149.42%).
     * Win Rate: 100.0% (leakage < 10^-144).
   - Generates [Table 1] 15 Institutional Metrics Comparison, [Table 2] 5 Market Breakdown, [Table 3] Strategy Contribution.
   - Synchronize reports across all 4 canonical paths:
     1. `reports/quant_benchmark_comparison_phase52.md`
     2. `trading_system/result/quant_benchmark_comparison_phase52.md`
     3. `trading_system/reports/quant_benchmark_comparison_phase52.md`
     4. `reports/quant_benchmark_comparison.md` (prepended with Phase 52 section, preserving historical reports).
2. Execute the benchmark script:
   `.venv\Scripts\python.exe trading_system/scripts/benchmark_phase52_quant_performance.py`
   Ensure it passes all assertions and writes the 4 report files with matching content/hashes.
3. Implement `tests/test_phase52_adversarial_challenger1.py`:
   - Test subnormal deadband annihilation, odd symmetry, right-tail convexity, EVaR monotonicity, Fisher-Rao simplex, and KNK 31-dark-energy DAHA limits.
4. Execute test suites:
   - `.venv\Scripts\python.exe -m pytest tests/test_phase52_adversarial_challenger1.py -v`
   - `.venv\Scripts\python.exe -m pytest tests/test_phase52_adversarial_oms_benchmark.py -v` (verify report sync and SHA-256 hash tests now pass 100%)
   - Full Phase 52 suite: `.venv\Scripts\python.exe -m pytest tests/test_phase52_alpha.py tests/test_phase52_risk.py tests/test_phase52_oms.py tests/test_phase52_adversarial_challenger1.py tests/test_phase52_adversarial_oms_benchmark.py -v`
5. Update `AGENTS.md` and `PROJECT.md`:
   - In `AGENTS.md`: add `trading_system/scripts/benchmark_phase52_quant_performance.py` to Key Files table, and document Phase 52 features.
   - In `PROJECT.md`: add Features F231~F235 and Phase 52 Milestones.
6. Document all deliverables, benchmark results, test outputs, and report hashes in `d:\Finance\code\stock\.agents\worker_phase52_verifier\handoff.md` and report back.
