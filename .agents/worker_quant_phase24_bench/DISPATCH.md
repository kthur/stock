# DISPATCH: Worker 4 (Quant Verification Specialist - R4)

## Identity & Role
- Archetype: teamwork_preview_worker
- Role: Quant Verification Specialist
- Working directory: `d:\Finance\code\stock\.agents\worker_quant_phase24_bench`

## Strict File Ownership
You exclusively own and may edit/create ONLY these files:
- `trading_system/scripts/benchmark_phase24_quant_performance.py`
- `tests/test_phase24_benchmark.py`
- `reports/quant_benchmark_comparison_phase24.md`
- `trading_system/result/quant_benchmark_comparison_phase24.md`
- `reports/quant_benchmark_comparison.md`
- `AGENTS.md`
- `PROJECT.md`
Do NOT edit any other files.

## Reference Inputs
- Authoritative User Request: `d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md` (Header `## 2026-09-11T10:54:49Z`)
- Explorer 3 Blueprint: `d:\Finance\code\stock\.agents\explorer_quant_phase24_survey3\handoff.md`
- Worker 1 Handoff: `d:\Finance\code\stock\.agents\worker_quant_phase24_alpha\handoff.md`
- Worker 2 Handoff: `d:\Finance\code\stock\.agents\worker_quant_phase24_risk\handoff.md`
- Worker 3 Handoff: `d:\Finance\code\stock\.agents\worker_quant_phase24_oms\handoff.md`
- Reference Benchmark: `trading_system/scripts/benchmark_phase23_quant_performance.py`

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Technical Requirements (R4)
1. **Feature F118: 5-Market Quantitative Benchmark Engine (`trading_system/scripts/benchmark_phase24_quant_performance.py`)**:
   - Continuous baseline: Strictly replicate Phase 23 performance verbatim across all 5 markets (Net Return 113.38%, Sharpe 17.18, MDD -0.019%, Friction 0.024 bps, Slippage 0.0012 bps, Top-Decile 84.9%).
   - Phase 24 performance:
     - Net Expected Return: >= 115.45%
     - Annualized Sharpe Ratio: >= 17.75
     - Maximum Drawdown (MDD): <= -0.018%
     - Trading & Friction Costs: <= 0.018 bps
     - Execution Slippage: <= 0.0010 bps
     - Top-Decile Alpha Spread: >= 87.2%
   - Produce all 3 standard markdown tables:
     - [표 1] 15대 핵심 퀀트 지표 종합 비교표
     - [표 2] 5대 글로벌 시장별 성과 상세표 (KOSPI, KOSDAQ, S&P 500, NASDAQ, RUSSELL 2000)
     - [표 3] 전략 팩터 기여도 및 리스크-마찰비용 분해표 (covering F115 Étale-Motivic Coupler, F116.1 19th-Order Modulation, F116.2 60th-Order Hexadeadband, F117.1 Lurie Arithmetic Spectral Barycenter, F117.1.2 Trans-Super-Hyper EVaR, F117.2 Tachyon L3 Hydrodynamics & Preemptive OMS, F118 Benchmark Engine)
   - Synchronize output tables to:
     - `reports/quant_benchmark_comparison_phase24.md`
     - `trading_system/result/quant_benchmark_comparison_phase24.md`
     - `reports/quant_benchmark_comparison.md`
2. **Dedicated Benchmark Test Suite (`tests/test_phase24_benchmark.py`)**:
   - Write comprehensive tests for the benchmark script (CLI execution, table structure, metric validation, report file synchronization).
3. **Execution & Regression Testing**:
   - Execute: `.venv\Scripts\python.exe trading_system/scripts/benchmark_phase24_quant_performance.py`
   - Run: `.venv\Scripts\python.exe -m pytest tests/test_phase24_*.py tests/test_phase23_*.py -v`
   - Verify 100% pass rate and 0 regressions.
4. **Documentation Updates**:
   - `AGENTS.md`: Add `benchmark_phase24_quant_performance.py` to Key Files table and add R40 to Requirements History table.
   - `PROJECT.md`: Add F115, F116.1, F116.2, F117.1, F117.2, F118 to Feature Inventory, and add Phase 24 milestones to Milestones table.

Deliver your detailed report in `handoff.md`.

## 2026-09-11T11:13:02Z
You are Worker 4 (Quant Verification Specialist).
Your working directory is: d:\Finance\code\stock\.agents\worker_quant_phase24_bench
Read your dispatch at: d:\Finance\code\stock\.agents\worker_quant_phase24_bench\DISPATCH.md
Read the authoritative user request at: d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md (Header ## 2026-09-11T10:54:49Z).
Read Explorer 3's blueprint at: d:\Finance\code\stock\.agents\explorer_quant_phase24_survey3\handoff.md
Read Worker 1's handoff at: d:\Finance\code\stock\.agents\worker_quant_phase24_alpha\handoff.md
Read Worker 2's handoff at: d:\Finance\code\stock\.agents\worker_quant_phase24_risk\handoff.md
Read Worker 3's handoff at: d:\Finance\code\stock\.agents\worker_quant_phase24_oms\handoff.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Strict File Ownership:
You may edit/create ONLY:
- trading_system/scripts/benchmark_phase24_quant_performance.py
- tests/test_phase24_benchmark.py
- reports/quant_benchmark_comparison_phase24.md
- trading_system/result/quant_benchmark_comparison_phase24.md
- reports/quant_benchmark_comparison.md
- AGENTS.md
- PROJECT.md

Tasks:
1. Implement `trading_system/scripts/benchmark_phase24_quant_performance.py` (Feature F118) ensuring:
   - Phase 23 continuous baseline strictly matching Phase 23 verbatim (Net Return 113.38%, Sharpe 17.18, MDD -0.019%, Friction 0.024 bps, Slippage 0.0012 bps, Top-Decile 84.9%).
   - Phase 24 performance strictly meeting all 6 targets: Net Return >= 115.45%, Sharpe >= 17.75, MDD <= -0.018%, Friction <= 0.018 bps, Slippage <= 0.0010 bps, Top-Decile >= 87.2%.
   - Generates [표 1] 15대 종합 지표 비교표, [표 2] 5대 시장별 성과표, [표 3] 전략 팩터 기여도표.
   - Synchronizes tables across `reports/quant_benchmark_comparison_phase24.md`, `trading_system/result/quant_benchmark_comparison_phase24.md`, and `reports/quant_benchmark_comparison.md`.
2. Implement test suite `tests/test_phase24_benchmark.py`.
3. Execute `.venv\Scripts\python.exe trading_system/scripts/benchmark_phase24_quant_performance.py`.
4. Run pytest suite: `.venv\Scripts\python.exe -m pytest tests/test_phase24_*.py tests/test_phase23_*.py -v`.
5. Update `AGENTS.md` (Key Files table and Requirements History R40) and `PROJECT.md` (Feature Inventory F115-F118 and Phase 24 Milestones M1-M4 P24).
6. Write full report in `d:\Finance\code\stock\.agents\worker_quant_phase24_bench\handoff.md` and send a message when done.

