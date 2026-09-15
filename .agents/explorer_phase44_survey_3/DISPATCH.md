# Task Assignment: Phase 44 Survey Explorer 3 — Quant Verification & Reporting Scope

## Identity & Working Directory
- Role: Survey Explorer 3 (Quant Verification, Benchmark & Reporting Suite Investigation)
- Working Directory: d:\Finance\code\stock\.agents\explorer_phase44_survey_3

## Context & Inputs
- Authoritative Request: d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md (Header: ## 2026-09-15T12:29:31Z)
- Orchestrator Dispatch: d:\Finance\code\stock\.agents\orchestrator_quant_phase44_1\DISPATCH.md
- Scope Document: d:\Finance\code\stock\PROJECT.md

## Target Files to Investigate
- `trading_system/scripts/benchmark_phase43_quant_performance.py` (and earlier benchmarks if needed)
- `tests/test_phase43_*.py`
- `reports/quant_benchmark_comparison_phase43.md`
- `trading_system/result/quant_benchmark_comparison_phase43.md`
- `trading_system/reports/quant_benchmark_comparison_phase43.md`
- `reports/quant_benchmark_comparison.md`
- `AGENTS.md` and `PROJECT.md`

## Investigation Objectives
1. Inspect how Phase 43 benchmark engine and reports are structured:
   - Command-line arguments, 5 markets simulation, 15 core quant metrics computation
   - Table formats: [표 1] 15대 종합 지표 비교표, [표 2] 5대 시장별 성과표, [표 3] 전략 팩터 기여도표
   - Report synchronization across 4 paths
   - Test suite structure in `tests/test_phase43_*.py`
2. Specify exact implementation design for Phase 44:
   - F198: `trading_system/scripts/benchmark_phase44_quant_performance.py`
   - Phase 44 performance targets: Net Return >= 157.45% (target 157.49%), Sharpe >= 29.75 (target 29.78), MDD <= -0.00001%, Trading Friction <= 0.000005 bps, Slippage <= 0.000005 bps, Top-Decile Spread >= 133.30% (target 133.32%), Win Rate 100.0%
   - Dedicated test suite `tests/test_phase44_*.py` covering unit, integration, stress, and backward compatibility
   - 4 sync destination report paths for Phase 44 comparison markdown
   - Required updates to `AGENTS.md` (Key Files, Requirements History R60) and `PROJECT.md` (Milestones M1~M4 P44, Feature Inventory F195~F198)

## Output
Write your comprehensive investigation report to:
`d:\Finance\code\stock\.agents\explorer_phase44_survey_3\handoff.md`
and send a completion message back with summary.

## 2026-09-15T12:43:16Z
You are Survey Explorer 3 for Phase 44 Quant Enhancement.
Your working directory is: d:\Finance\code\stock\.agents\explorer_phase44_survey_3
Read your instructions at: d:\Finance\code\stock\.agents\explorer_phase44_survey_3\DISPATCH.md
Also read the authoritative user request at: d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md (Header: ## 2026-09-15T12:29:31Z)

Scope:
Investigate `trading_system/scripts/benchmark_phase43_quant_performance.py`, `tests/test_phase43_*.py`, benchmark comparison reports, and documentation (`AGENTS.md`, `PROJECT.md`). Specify the exact design for:
- F198: `trading_system/scripts/benchmark_phase44_quant_performance.py` and dedicated test suite `tests/test_phase44_*.py`
- Phase 44 targets: Net Return >= 157.45% (target 157.49%), Sharpe >= 29.75 (target 29.78), MDD <= -0.00001%, Friction <= 0.000005 bps, Slippage <= 0.000005 bps, Top-Decile Spread >= 133.30% (target 133.32%), Win Rate 100.0%
- Generating 3 comparison tables and syncing to 4 paths:
  1. `reports/quant_benchmark_comparison_phase44.md`
  2. `trading_system/result/quant_benchmark_comparison_phase44.md`
  3. `trading_system/reports/quant_benchmark_comparison_phase44.md`
  4. `reports/quant_benchmark_comparison.md`
- Updates to `AGENTS.md` (Key Files, Requirements History R60) and `PROJECT.md` (M1~M4 P44, F195~F198)

Write your findings to `d:\Finance\code\stock\.agents\explorer_phase44_survey_3\handoff.md` and use send_message to report back.

