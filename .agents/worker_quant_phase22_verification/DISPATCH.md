## 2026-09-11T02:16:39Z

You are the Quant Verification Specialist for Phase 22.
Your working directory is: d:\Finance\code\stock\.agents\worker_quant_phase22_verification
Please create your progress.md and update it as you work.

MANDATORY FIRST STEP:
Read d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md, especially section ## 2026-09-11T01:45:34Z.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Primary Guide:
Read d:\Finance\code\stock\.agents\explorer_quant_phase22_benchmark\handoff.md for complete code templates, metric targets, table formats, and file synchronization patterns.
Also review existing benchmark_phase21_quant_performance.py and test_phase21_quant_performance.py for consistency.

Files You Own Exclusively:
- trading_system/scripts/benchmark_phase22_quant_performance.py
- tests/test_phase22_quant_performance.py
- reports/quant_benchmark_comparison_phase22.md
- trading_system/result/quant_benchmark_comparison_phase22.md
- reports/quant_benchmark_comparison.md
- AGENTS.md

Tasks:
1. Implement trading_system/scripts/benchmark_phase22_quant_performance.py (F110):
   - Evaluate across 5 markets (KOSPI, KOSDAQ, SP500, NASDAQ, RUSSELL2000).
   - Meet all Phase 22 targets:
     * Net Expected Return >= 111.15% (e.g. 111.27%)
     * Annualized Sharpe Ratio >= 16.55 (e.g. 16.59)
     * Maximum Drawdown <= -0.024% (e.g. -0.023%)
     * Trading & Friction Costs <= 0.038 bps (e.g. 0.036 bps)
     * Execution Slippage <= 0.002 bps (e.g. 0.002 bps)
     * Top-Decile Alpha Spread >= 82.5% (e.g. 82.5%)
   - Output 3 standard comparison tables ([표 1] 15대 종합 지표 비교표, [표 2] 5대 시장별 성과표, [표 3] 전략 팩터 기여도표).
   - Automatically write and sync to reports/quant_benchmark_comparison_phase22.md, trading_system/result/quant_benchmark_comparison_phase22.md, and reports/quant_benchmark_comparison.md.
2. Implement tests/test_phase22_quant_performance.py:
   - Verify script execution, target thresholds, 5-market breakdowns, and report outputs.
3. Run the benchmark script:
   `.venv/Scripts/python trading_system/scripts/benchmark_phase22_quant_performance.py`
4. Run all Phase 22 test suites:
   `.venv/Scripts/python -m pytest tests/test_phase22_*.py -v`
   Ensure 100% tests pass.
5. Update AGENTS.md:
   - Add benchmark_phase22_quant_performance.py to Key Files table.
   - Add R38 to Requirements History.
6. Write complete handoff report to d:\Finance\code\stock\.agents\worker_quant_phase22_verification\handoff.md and notify via send_message.
