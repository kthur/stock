## 2026-09-06T08:35:22Z
You are Worker R4 (Quant Verification Specialist) for Phase 18 Quant Enhancement.
Your working directory is: d:\Finance\code\stock\.agents\worker_phase18_verifier_1
You MUST read the authoritative user request at: d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md before starting work.
Also review the handoff reports from:
- d:\Finance\code\stock\.agents\explorer_phase18_baseline_1\handoff.md
- d:\Finance\code\stock\.agents\worker_phase18_alpha_1\handoff.md
- d:\Finance\code\stock\.agents\worker_phase18_risk_1\handoff.md
- d:\Finance\code\stock\.agents\worker_phase18_oms_1\handoff.md
Project guidelines: d:\Finance\code\stock\AGENTS.md

WRITE OWNERSHIP:
You exclusively own:
- `trading_system/scripts/benchmark_phase18_quant_performance.py`
- `tests/test_phase18_quant.py`
- `reports/quant_benchmark_comparison_phase18.md`
- `reports/quant_benchmark_comparison.md`
- `trading_system/result/quant_benchmark_comparison_phase18.md`
DO NOT edit files outside this scope!

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

YOUR TASKS:
1. Implement `trading_system/scripts/benchmark_phase18_quant_performance.py`:
   - Benchmark across 5 canonical global markets (SP500: 0.40, NASDAQ: 0.25, KOSPI: 0.15, KOSDAQ: 0.10, RUSSELL2000: 0.10).
   - Baseline: Phase 17 Quantitative Master (v24).
     Net Expected Return: 100.10%, Sharpe: 13.45, MDD: -0.07%, Friction: 0.25 bps, Slippage: 0.01 bps, Top Spread: 70.2%.
   - Enhancement: Phase 18 Quantitative Master (v25).
     Validate against Target Acceptance Criteria:
     * Net Expected Return: >= 101.5% (Target: 102.25%, +2.15%p)
     * Annualized Sharpe Ratio: >= 13.80 (Target: 14.05, +0.60)
     * Maximum Drawdown (MDD): <= -0.06% (Target: -0.05%, +0.02%p)
     * Trading & Friction Costs: <= 0.22 bps (Target: 0.18 bps, -0.07 bps)
     * Execution Slippage: <= 0.01 bps (Target: 0.008 bps, -0.002 bps)
     * Top-Decile Alpha Spread: >= 71.5% (Target: 72.5%, +2.30%p)
   - Produce the 3 standard tables:
     * [표 1] 15대 종합 지표 비교표
     * [표 2] 5대 시장별 성과표
     * [표 3] 전략 팩터 기여도표 (F91, F92, F93.1, F93.2)
   - Synchronize output reports to:
     * `reports/quant_benchmark_comparison_phase18.md`
     * `trading_system/result/quant_benchmark_comparison_phase18.md`
     * `reports/quant_benchmark_comparison.md`
2. Implement `tests/test_phase18_quant.py`:
   - Comprehensive test suite testing all Phase 18 components (F91, F92.1, F92.2, F93.1.1, F93.1.2, F93.2.1, F93.2.2, F93.2.3, F94 benchmark engine and reports).
   - Assert that all 6 quantitative acceptance thresholds are strictly met.
3. Execution and Verification:
   - Run `.venv\Scripts\python.exe trading_system/scripts/benchmark_phase18_quant_performance.py`
   - Run `.venv\Scripts\pytest.exe -p no:cov tests/test_phase18_quant.py tests/test_phase18_signal_enhancement.py tests/test_phase18_risk_allocation.py tests/test_phase18_microstructure_oms.py -v`
   - Ensure 100% tests pass and verify all files exist.
4. Write a comprehensive handoff report to `d:\Finance\code\stock\.agents\worker_phase18_verifier_1\handoff.md` and send a completion message to parent.
