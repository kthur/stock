# DISPATCH: Forensic Auditor — Integrity Forensics (Phase 40)

## Working Directory
d:\Finance\code\stock\.agents\auditor_phase40_1

## Mandatory References
1. `d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md` (Header: `## 2026-09-14T05:30:34Z`)
2. `d:\Finance\code\stock\.agents\worker_quant_phase40_alpha\handoff.md`
3. `d:\Finance\code\stock\.agents\worker_quant_phase40_risk\handoff.md`
4. `d:\Finance\code\stock\.agents\worker_quant_phase40_oms\handoff.md`
5. `d:\Finance\code\stock\.agents\worker_quant_phase40_bench\handoff.md`
6. `d:\Finance\code\stock\PROJECT.md`

## Forensic Audit Scope
Perform an independent, uncompromising forensic integrity audit across all Phase 40 code, tests, and deliverables:
1. **Anti-Cheating & Static Analysis**:
   - Inspect `src/ai/ensemble_scorer.py`, `src/ai/factor_suppression.py`, `src/risk/unified_portfolio_allocator.py`, `src/risk/portfolio_allocator.py`, `src/core/fast_lob_engine.py`, `src/execution/smart_order_router.py`, `src/execution/oms_engine.py`, and `trading_system/scripts/benchmark_phase40_quant_performance.py`.
   - Verify that NO hardcoded test results, dummy facades, mocked calculation bypasses, or shortcuts exist in production source code.
   - Verify that all physics equations, Riemannian manifold updates, 36th cumulant expansions, and order slicing algorithms execute genuine mathematical operations.
2. **Test Authenticity & Non-Tautology**:
   - Inspect `tests/test_phase40_alpha.py`, `tests/test_phase40_risk.py`, `tests/test_phase40_oms.py`, and `tests/test_phase40_benchmark.py`.
   - Verify that assertions test true mathematical properties, boundaries, and logic rather than `assert True` or tautologies.
3. **Execution Validation**:
   - Run all Phase 40 test suites and baseline regression suites:
     `$env:BYPASS_TORCH="1"; python -m pytest tests/test_phase40_alpha.py tests/test_phase40_risk.py tests/test_phase40_oms.py tests/test_phase40_benchmark.py -v`
   - Run `python trading_system/scripts/benchmark_phase40_quant_performance.py` and inspect console output.
4. **Documentation & Deliverables Integrity**:
   - Inspect `reports/quant_benchmark_comparison_phase40.md`, mirror paths, `AGENTS.md`, and `PROJECT.md`.
5. **Verdict**:
   - State clearly: `CLEAN` (zero integrity violations) or `INTEGRITY VIOLATION` (with full evidence).
   - Note: Clean audit is non-negotiable binary veto.
6. Output: Write report to `d:\Finance\code\stock\.agents\auditor_phase40_1\handoff.md` and send completion message to orchestrator (`d589c15d-8af5-4fdc-85b9-702f9839272f`).
