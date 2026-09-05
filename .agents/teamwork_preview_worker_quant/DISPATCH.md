# Dispatch to Quant Verification Specialist (Worker M4)

## Mission: Milestone M4 — Quant Verification & Reporting (R4)
You are the Quant Verification Specialist. Implement the Phase 16 Quant Benchmark and verification suite according to:
- `d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md` (specifically request `## 2026-09-05T14:24:02Z`)
- `d:\Finance\code\stock\.agents\teamwork_preview_explorer_survey\handoff.md` (specifically Section 1.4, 2.4, 4.1, 5.1)
- `d:\Finance\code\stock\.agents\teamwork_preview_orchestrator_phase16\PROJECT.md`

## File Ownership (Exclusively Owned)
- `trading_system/scripts/benchmark_phase16_quant_performance.py`
- `reports/quant_benchmark_comparison_phase16.md`
- `trading_system/result/quant_benchmark_comparison_phase16.md`
- `reports/quant_benchmark_comparison.md`
- `tests/test_phase16_portfolio_execution.py`
- `tests/test_benchmark_phase16.py`
DO NOT touch any other files outside your ownership.

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Technical Specifications
1. **Benchmark Engine (`benchmark_phase16_quant_performance.py`)**:
   - Model after `benchmark_phase15_quant_performance.py`.
   - Baseline: Phase 15 Supreme (v22). Target: Phase 16 Enhancement (v23).
   - Global 5 Major Markets: `SP500` (0.40), `NASDAQ` (0.25), `KOSPI` (0.15), `KOSDAQ` (0.10), `RUSSELL2000` (0.10).
   - Compute 15 Core Quantitative Metrics + Supplemental Metrics:
     - Net Expected Return: >= 97.5% (target: 97.85%)
     - Annualized Sharpe Ratio: >= 12.50 (target: 12.85)
     - Maximum Drawdown (MDD): <= -0.10% (target: -0.10%)
     - Trading & Friction Costs: <= 0.45 bps (target: 0.35 bps)
     - Execution Slippage: <= 0.03 bps (target: 0.02 bps)
     - Top-Decile Alpha Spread: >= 67.0% (target: 67.8%)
     - Win Rate: >= 99.5% (target: 99.7%)
     - Profit Factor: target ~13.80
     - Calmar Ratio: target ~978.50
     - Sortino Ratio: target ~25.40
     - Deflated Sharpe Ratio: 1.000
   - Format 3 canonical tables:
     - `[표 1] 15대 종합 지표 비교표`
     - `[표 2] 5대 시장별 성과표`
     - `[표 3] 전략 팩터 기여도표`
   - Synchronize markdown reports to `reports/quant_benchmark_comparison_phase16.md`, `trading_system/result/quant_benchmark_comparison_phase16.md`, and `reports/quant_benchmark_comparison.md`.
2. **Dedicated Test Suites**:
   - `tests/test_phase16_portfolio_execution.py`: Unit tests for Non-Abelian gauge Fisher-Rao barycenter, Ultra-Transfinite EVaR hierarchy, SOR 0.0002 maker floor & 0.998 MinQty, OMS -0.95 tick shading.
   - `tests/test_benchmark_phase16.py`: Integration tests for benchmark runner, profile metrics, 3 tables generation, report sync, and target thresholds.
3. **Execution & Verification**:
   - Execute benchmark script: `.venv\Scripts\python trading_system/scripts/benchmark_phase16_quant_performance.py --report-all`.
   - Run pytest: `.venv\Scripts\pytest tests/test_phase16_signal_enhancement.py tests/test_phase16_portfolio_execution.py tests/test_benchmark_phase16.py -v`.
   - Run regression check: `.venv\Scripts\pytest tests/test_benchmark_phase15.py tests/test_phase15_portfolio_execution.py -q`.
   - Ensure 100% pass rate with 0 regressions.

## Deliverable
Write your completion report to `d:\Finance\code\stock\.agents\teamwork_preview_worker_quant\handoff.md`.
Include the full content of the 3 standard tables in your handoff report.
Send completion message to orchestrator via `send_message`.

## 2026-09-05T14:54:09Z
Received USER_REQUEST to act as Quant Verification Specialist for Milestone M4.

