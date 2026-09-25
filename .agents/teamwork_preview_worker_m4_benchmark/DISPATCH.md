## 2026-09-25T15:32:00Z
You are the Benchmark, Testing & Documentation Specialist Worker for Phase 67 Quantitative Alpha Enhancement.
Read the authoritative user request at:
d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md (specifically lines 2115-2219).

Also consult the comprehensive specification blueprint in:
`d:\Finance\code\stock\.agents\teamwork_preview_spec_miner_survey_1\survey_benchmark_spec.md`

Your working directory is:
`d:\Finance\code\stock\.agents\teamwork_preview_worker_m4_benchmark`

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

DELIVERABLES:
1. Benchmark Script:
   Create `trading_system/scripts/benchmark_phase67_quant_performance.py` modeled on Phase 66.
   Must run 5-market simulation (KOSPI, KOSDAQ, SP500, NASDAQ, RUSSELL2000), evaluate all 37 strategies, and assert all 7 strict KPIs:
     * Net Return ≥ 206.85%
     * Sharpe ≥ 43.85
     * MDD ≤ -0.000008%
     * Slippage ≤ 2.310e-12 bps
     * Friction ≤ 2.800e-12 bps
     * Alpha Spread ≥ 186.40%
     * Win Rate = 100.0%
   Execute the script using:
   `d:\Finance\code\stock\trading_system\.venv\Scripts\python.exe trading_system/scripts/benchmark_phase67_quant_performance.py`

2. Report Generation & Synchronization across 7 paths:
   - Category A (3-path bit-for-bit SHA-256 identical match):
     * `reports/quant_benchmark_comparison_phase67.md`
     * `trading_system/reports/quant_benchmark_comparison_phase67.md`
     * `trading_system/result/quant_benchmark_comparison_phase67.md`
   - Category B (3-path standalone report with embedded SHA-256):
     * `reports/benchmark_phase67_report.md`
     * `trading_system/reports/benchmark_phase67_report.md`
     * `docs/benchmark_phase67_report.md`
   - Category C:
     * `reports/quant_benchmark_comparison.md`: Prepend Phase 67 comparison section above Phase 66.

3. 5 Test Files in `tests/`:
   Follow the blueprints in `survey_benchmark_spec.md`:
   - `tests/test_phase67_alpha.py` (9 tests)
   - `tests/test_phase67_risk.py` (9 tests)
   - `tests/test_phase67_oms.py` (8 tests)
   - `tests/test_phase67_adversarial_challenger1.py` (27 tests across 4 classes)
   - `tests/test_phase67_adversarial_oms_benchmark.py` (8 tests)
   Execute all tests:
   `d:\Finance\code\stock\trading_system\.venv\Scripts\python.exe -m pytest tests/test_phase67_alpha.py tests/test_phase67_risk.py tests/test_phase67_oms.py tests/test_phase67_adversarial_challenger1.py tests/test_phase67_adversarial_oms_benchmark.py`
   And run combined regression test suite:
   `d:\Finance\code\stock\trading_system\.venv\Scripts\python.exe -m pytest tests/test_phase66_alpha.py tests/test_phase66_risk.py tests/test_phase66_oms.py tests/test_phase66_adversarial_challenger1.py tests/test_phase66_adversarial_oms_benchmark.py`
   Ensure 100% pass across all 122+ tests.

4. Documentation Updates:
   - `AGENTS.md`: Add `benchmark_phase67_quant_performance.py` entry under Key Files.
   - `PROJECT.md`: Add F306~F310 entries in Feature Inventory, M1~M4 (P67) in Milestones table, and benchmark script in Code Layout.

Write your completion report and test verification logs to:
`d:\Finance\code\stock\.agents\teamwork_preview_worker_m4_benchmark\handoff.md`
Then send a completion message to parent.
