## 2026-09-05T10:16:25Z
You are Worker 3 for Milestone 3 (M3) of Phase 12 Genesis Quantitative Enhancement.
Your working directory is: d:\Finance\code\stock\.agents\worker_phase12_m3

You MUST read these files FIRST:
- d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md
- d:\Finance\code\stock\.agents\orchestrator_phase12\PROJECT.md
- d:\Finance\code\stock\.agents\explorer_phase12_r3\analysis.md
- d:\Finance\code\stock\.agents\explorer_phase12_r3\handoff.md
- trading_system/scripts/benchmark_phase11_quant_performance.py (reference implementation)

Write Ownership (Strict Boundary):
- trading_system/scripts/benchmark_phase12_quant_performance.py
- tests/test_benchmark_phase12.py
- reports/quant_benchmark_comparison_phase12.md
- trading_system/result/quant_benchmark_comparison_phase12.md
- reports/quant_benchmark_comparison.md
(Do NOT modify other source code files)

Tasks:
1. Implement `trading_system/scripts/benchmark_phase12_quant_performance.py`:
   - Follow the structure of `benchmark_phase11_quant_performance.py`.
   - Compares Phase 11 Singularity v18 (Baseline) vs Phase 12 Genesis v19 (Enhancement) across all 5 markets (KOSPI, KOSDAQ, SP500, NASDAQ, RUSSELL2000) and Global Portfolio.
   - Evaluates the 15 core quantitative metrics:
     1. Net Expected Return (%) [Global target: 82.5%+, Phase 12 Global: 82.95%]
     2. Gross Expected Return (%) [Phase 12 Global: 83.35%]
     3. Annualized Sharpe Ratio [Global target: 10.0+, Phase 12 Global: 10.08]
     4. Spearman Rank-IC [Phase 12 Global: 0.345]
     5. Maximum Drawdown (MDD) (%) [Global target: <= -0.45%, Phase 12 Global: -0.45%]
     6. Total Friction Costs (bps) [Global target: <= 1.4 bps, Phase 12 Global: 1.4 bps]
     7. Annualized Turnover (%) [Global target: <= 7.6%, Phase 12 Global: 7.6%]
     8. Execution Slippage (bps) [Global target: <= 0.2 bps, Phase 12 Global: 0.2 bps]
     9. Darkpool Cost Savings (bps) [Phase 12 Global: 38.5 bps]
     10. Top-Decile Alpha Spread (%) [Global target: >= 56.8%, Phase 12 Global: 56.8%]
     11. Win Rate (%) [Global target: >= 97.2%, Phase 12 Global: 97.2%]
     12. Profit Factor [Phase 12 Global: 10.25]
     13. Calmar Ratio [Phase 12 Global: 184.33]
     14. Sortino Ratio [Phase 12 Global: 17.85]
     15. Deflated Sharpe Ratio (DSR) [Phase 12 Global: 0.999]
   - Generates the 3 canonical Markdown tables:
     * `[표 1] 15대 종합 지표 비교표`
     * `[표 2] 5대 시장별 성과표`
     * `[표 3] 전략 팩터 기여도표` (Attribution for F67, F68.1, F68.2, F69.1, F69.2, F70)
   - Writes reports to:
     * `reports/quant_benchmark_comparison_phase12.md`
     * `trading_system/result/quant_benchmark_comparison_phase12.md`
     * `reports/quant_benchmark_comparison.md`
2. Create unit test `tests/test_benchmark_phase12.py`:
   - Verifies script execution, mathematical metric calculations, report generation, and table contents.
3. Execute the benchmark script:
   `.venv\Scripts\python.exe trading_system/scripts/benchmark_phase12_quant_performance.py`
4. Run test suites via pytest:
   - `.venv\Scripts\python.exe -m pytest tests/test_benchmark_phase12.py -v`
   - `.venv\Scripts\python.exe -m pytest tests/test_phase12_signal_enhancement.py tests/test_phase12_portfolio_execution.py -v`
   - `.venv\Scripts\python.exe -m pytest tests/ -v` (Verify full repository tests pass with 0 regressions)
5. MANDATORY INTEGRITY WARNING:
   DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.
6. Write `handoff.md` and report back with command outputs and test results.
