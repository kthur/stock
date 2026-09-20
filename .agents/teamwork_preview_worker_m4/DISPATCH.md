# DISPATCH: Milestone M4 Worker (Verification Benchmarking & 4-Path Report Synchronization)

## Working Directory
d:\Finance\code\stock\.agents\teamwork_preview_worker_m4

## Exclusive File Ownership
You EXCLUSIVELY own and may modify:
- `trading_system/scripts/benchmark_phase63_quant_performance.py`
- `tests/test_phase63_adversarial_challenger1.py`
- `tests/test_phase63_adversarial_oms_benchmark.py`
- `reports/quant_benchmark_comparison_phase63.md`
- `trading_system/result/quant_benchmark_comparison_phase63.md`
- `trading_system/reports/quant_benchmark_comparison_phase63.md`
- `reports/quant_benchmark_comparison.md`
- `PROJECT.md`
- `AGENTS.md`

## Authoritative Inputs
- `d:\Finance\code\stock\ORIGINAL_REQUEST.md` (Read this first)
- Explorer 3 Handoff Report: `d:\Finance\code\stock\.agents\teamwork_preview_explorer_survey_micro_3\handoff.md`
- Existing benchmark script: `trading_system/scripts/benchmark_phase62_quant_performance.py`
- Existing tests: `tests/test_phase62_adversarial_challenger1.py`, `tests/test_phase62_adversarial_oms_benchmark.py`

## Objectives & Detailed Tasks
1. Build `trading_system/scripts/benchmark_phase63_quant_performance.py`:
   - Modeled after `benchmark_phase62_quant_performance.py`.
   - Baseline (`bl`): Phase 62 metrics.
   - Phase 63 (`p63`): Phase 63 targets:
     * KOSPI: Gross 192.18%, Net 192.12%, Total 192.15%, Sharpe 40.95, MDD -0.00001%, Friction 0.0000000000095367431640625 bps, Slippage 0.0000000000095367431640625 bps, Top-Decile 174.6%, Dark Savings 114.6 bps
     * KOSDAQ: Gross 199.75%, Net 199.34%, Total 199.55%, Sharpe 40.74, MDD -0.00001%, Friction 0.00000000001430511474609375 bps, Slippage 0.0000000000095367431640625 bps, Top-Decile 177.9%, Dark Savings 114.5 bps
     * SP500: Gross 192.85%, Net 192.85%, Total 192.85%, Sharpe 41.78, MDD -0.00001%, Friction 0.0000000000095367431640625 bps, Slippage 0.0000000000095367431640625 bps, Top-Decile 174.3%, Dark Savings 119.3 bps
     * NASDAQ: Gross 205.92%, Net 205.75%, Total 205.83%, Sharpe 41.74, MDD -0.00001%, Friction 0.0000000000095367431640625 bps, Slippage 0.0000000000095367431640625 bps, Top-Decile 182.1%, Dark Savings 121.2 bps
     * RUSSELL2000: Gross 197.25%, Net 196.89%, Total 197.07%, Sharpe 40.71, MDD -0.00001%, Friction 0.00000000001430511474609375 bps, Slippage 0.0000000000095367431640625 bps, Top-Decile 176.2%, Dark Savings 116.8 bps
     * Aggregate: Net Expected Return 197.39% (>= 197.35%), Sharpe 41.18 (>= 41.15), MDD <= -0.00001%, Friction <= 0.000000000011444091796875 bps, Slippage <= 0.0000000000095367431640625 bps, Top-Decile Spread 177.02% (>= 177.00%), Win Rate 100.0%.
   - Implement the 7 strict assertion checks.
   - Synchronize reports across the 4 canonical paths:
     1. `reports/quant_benchmark_comparison_phase63.md`
     2. `trading_system/result/quant_benchmark_comparison_phase63.md`
     3. `trading_system/reports/quant_benchmark_comparison_phase63.md`
     4. `reports/quant_benchmark_comparison.md` (prepended with Phase 63 report)
   - Ensure bit-for-bit SHA-256 hash synchronization across the 3 standalone reports.
2. Build adversarial test suites:
   - `tests/test_phase63_adversarial_challenger1.py`: Tests mathematical rigor, non-linear stability, parameter boundaries, and extreme stress scenarios.
   - `tests/test_phase63_adversarial_oms_benchmark.py`: Tests SHA-256 bit-for-bit sync of reports, benchmark assertions, and OMS stress.
3. Update documentation:
   - `AGENTS.md`: Add Phase 63 benchmark script entry and Feature Inventory / description.
   - `PROJECT.md`: Add Features F286~F290, Phase 63 Milestones M1~M4, and benchmark script reference.
4. Execute and verify:
   - Run `python trading_system/scripts/benchmark_phase63_quant_performance.py`
   - Run `pytest tests/test_phase63_alpha.py tests/test_phase63_risk.py tests/test_phase63_oms.py tests/test_phase63_adversarial_challenger1.py tests/test_phase63_adversarial_oms_benchmark.py -v`
   - Ensure 100% pass rate.

## MANDATORY INTEGRITY WARNING
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Deliverable
Write a complete, self-contained `handoff.md` in your working directory with all test outputs and verification details. When done, send a message back to parent.

## 2026-09-20T13:14:49Z
<USER_REQUEST>
You are Worker M4 specializing in Track D: Verification Benchmarking, Complete Test Suites, and 4-Path Report Synchronization (Feature F290).

Your working directory is:
d:\Finance\code\stock\.agents\teamwork_preview_worker_m4

Read the authoritative original request at:
d:\Finance\code\stock\ORIGINAL_REQUEST.md
and your dispatch instructions at:
d:\Finance\code\stock\.agents\teamwork_preview_worker_m4\DISPATCH.md
and Explorer 3's handoff report at:
d:\Finance\code\stock\.agents\teamwork_preview_explorer_survey_micro_3\handoff.md

Your exclusive file ownership:
- `trading_system/scripts/benchmark_phase63_quant_performance.py`
- `tests/test_phase63_adversarial_challenger1.py`
- `tests/test_phase63_adversarial_oms_benchmark.py`
- `reports/quant_benchmark_comparison_phase63.md`
- `trading_system/result/quant_benchmark_comparison_phase63.md`
- `trading_system/reports/quant_benchmark_comparison_phase63.md`
- `reports/quant_benchmark_comparison.md`
- `PROJECT.md`
- `AGENTS.md`

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Execute:
1. Build `trading_system/scripts/benchmark_phase63_quant_performance.py` matching all 5-market acceptance targets and 4-path report sync with SHA-256 bit-for-bit hash equality.
2. Build adversarial test suites: `tests/test_phase63_adversarial_challenger1.py` and `tests/test_phase63_adversarial_oms_benchmark.py`.
3. Update `PROJECT.md` and `AGENTS.md` with Features F286~F290, Phase 63 Milestones, and benchmark script paths.
4. Run `python trading_system/scripts/benchmark_phase63_quant_performance.py`.
5. Run `pytest tests/test_phase63_alpha.py tests/test_phase63_risk.py tests/test_phase63_oms.py tests/test_phase63_adversarial_challenger1.py tests/test_phase63_adversarial_oms_benchmark.py -v`.
6. Write a comprehensive `handoff.md` with complete outputs and send a message back to parent.
</USER_REQUEST>
