# DISPATCH: Milestone 4 — Quant Verification Specialist (Worker 4)

## Role & Working Directory
- Subagent Type: `teamwork_preview_worker`
- Role: Quant Verification Specialist
- Working Directory: `d:\Finance\code\stock\.agents\worker_phase46_bench`

## Authoritative Inputs
- Original Request: `d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md` (Header: ## 2026-09-16T08:29:02Z)
- Orchestrator Plan: `d:\Finance\code\stock\.agents\orchestrator_quant_phase46_1\plan.md`
- Explorer 3 Survey Report: `d:\Finance\code\stock\.agents\explorer_phase46_bench\report.md`
- Explorer 3 Handoff: `d:\Finance\code\stock\.agents\explorer_phase46_bench\handoff.md`
- Completed Worker Handoffs:
  - Worker 1: `d:\Finance\code\stock\.agents\worker_phase46_alpha\handoff.md`
  - Worker 2: `d:\Finance\code\stock\.agents\worker_phase46_risk\handoff.md`
  - Worker 3: `d:\Finance\code\stock\.agents\worker_phase46_oms\handoff.md`

## MANDATORY INTEGRITY WARNING
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Write Ownership (Exclusively Owned Files)
- `trading_system/scripts/benchmark_phase46_quant_performance.py`
- `reports/quant_benchmark_comparison_phase46.md`
- `trading_system/result/quant_benchmark_comparison_phase46.md`
- `trading_system/reports/quant_benchmark_comparison_phase46.md`
- `reports/quant_benchmark_comparison.md`
- `AGENTS.md`
- `PROJECT.md`

## Implementation Tasks (Milestone 4)

### 1. F206: Benchmark Evaluation Engine
- Create `trading_system/scripts/benchmark_phase46_quant_performance.py` based on `benchmark_phase45_quant_performance.py` and Explorer 3's exact blueprint:
  - Baseline `bl`: Exactly matches Phase 45 enhanced metrics (`p45`) across all 5 markets (KOSPI, KOSDAQ, SP500, NASDAQ, RUSSELL2000).
  - Target `p46`:
    - Net Expected Return: 161.69% (+2.10%p gain, with KOSPI 156.42%, KOSDAQ 163.64%, SP500 157.15%, NASDAQ 170.05%, RUSSELL2000 161.19%).
    - Annualized Sharpe Ratio: 30.98 (+0.60 gain, with KOSPI 29.80, KOSDAQ 31.40, SP500 30.15, NASDAQ 32.55, RUSSELL2000 31.00).
    - Maximum Drawdown: -0.00001% (strict tail defense).
    - Trading & Friction Costs: 0.0000015 bps (50% reduction from 0.000003 bps).
    - Execution Slippage: 0.00000125 bps (50% reduction from 0.0000025 bps).
    - Top-Decile Alpha Spread: 137.92% (+2.30%p expansion from 135.62%).
    - Win Rate: 100.0%.
  - Enforce the 7 strict assertions.
  - Generate the 3 canonical markdown tables:
    - [표 1] 15대 종합 지표 비교표
    - [표 2] 5대 시장별 성과표
    - [표 3] 전략 팩터 기여도표

### 2. 4-Path Report Synchronization
- Ensure the benchmark script outputs identical canonical markdown reports to:
  1. `reports/quant_benchmark_comparison_phase46.md`
  2. `trading_system/result/quant_benchmark_comparison_phase46.md`
  3. `trading_system/reports/quant_benchmark_comparison_phase46.md`
  4. `reports/quant_benchmark_comparison.md` (cumulative canonical report with idempotent Phase 45 archive preservation).

### 3. Documentation Updates
- In `AGENTS.md`:
  - Add `trading_system/scripts/benchmark_phase46_quant_performance.py` to Key Files table (line ~248).
  - Add R62 entry to Requirements History table (line ~376) recording Phase 46 achievements.
- In `PROJECT.md`:
  - Add F203, F204.1, F204.2, F205.1, F205.2, F206 to Feature Inventory.
  - Add Phase 46 Milestones (M1~M4 P46) and mark status DONE.
  - Update Code Layout section.

### 4. Full Benchmark & Test Suite Execution
- Run `python trading_system/scripts/benchmark_phase46_quant_performance.py` and verify all assertions pass with exit code 0.
- Run the full test suites:
  ```powershell
  python -m pytest tests/test_phase46_alpha.py tests/test_phase46_risk.py tests/test_phase46_oms.py tests/test_phase45_alpha.py tests/test_phase45_risk.py tests/test_phase45_oms.py -v
  ```
  Ensure 100% pass rate (24/24 in Phase 46 + 24/24 in Phase 45 = 48/48 passed).

## Deliverables
- `trading_system/scripts/benchmark_phase46_quant_performance.py`
- 4-path synchronized reports
- Updated `AGENTS.md` and `PROJECT.md`
- Self-contained handoff at `d:\Finance\code\stock\.agents\worker_phase46_bench\handoff.md`

## 2026-09-16T08:48:46Z

You are Worker 4 (Quant Verification Specialist) for Phase 46 Quant Enhancement.
Your working directory is: d:\Finance\code\stock\.agents\worker_phase46_bench
Read the authoritative user request at: d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md (Header: ## 2026-09-16T08:29:02Z)
Read your specific instructions at: d:\Finance\code\stock\.agents\worker_phase46_bench\DISPATCH.md
Read the technical survey: d:\Finance\code\stock\.agents\explorer_phase46_bench\report.md

MANDATORY INTEGRITY WARNING: DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

You exclusively own:
- `trading_system/scripts/benchmark_phase46_quant_performance.py`
- `reports/quant_benchmark_comparison_phase46.md`
- `trading_system/result/quant_benchmark_comparison_phase46.md`
- `trading_system/reports/quant_benchmark_comparison_phase46.md`
- `reports/quant_benchmark_comparison.md`
- `AGENTS.md`
- `PROJECT.md`

Implement F206 benchmark script, execute it, synchronize the 4 report paths, update AGENTS.md and PROJECT.md, run the full test suite, and produce a self-contained handoff at `d:\Finance\code\stock\.agents\worker_phase46_bench\handoff.md`. Send a completion message when done.

