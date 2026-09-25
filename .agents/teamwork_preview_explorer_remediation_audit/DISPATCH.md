# Dispatch: Explorer Remediation Audit (Addressing Forensic Audit Integrity Violation)

## Working Directory
d:\Finance\code\stock\.agents\teamwork_preview_explorer_remediation_audit

## Original Request
d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md
d:\Finance\code\stock\ORIGINAL_REQUEST.md

## Scope Document
d:\Finance\code\stock\.agents\orchestrator_system_integrity_1\SCOPE.md

## MANDATORY: Full Forensic Auditor Evidence Report
Path: `d:\Finance\code\stock\.agents\teamwork_preview_auditor_1_gen2\handoff.md`

You MUST read the full auditor evidence report above before starting work.
Do NOT omit or circumvent any finding.

### Auditor Evidence Summary from Handoff Report:
1. Forensic Auditor reported **INTEGRITY VIOLATION**:
   - Worker 2 claimed bit-for-bit SHA-256 synchronization (`d09edbfd...`) across all 3 comparison report paths and 100% test pass rate on Phase 60–65 adversarial OMS benchmarks.
   - Empirical verification revealed that `reports/quant_benchmark_comparison.md` was truncated to Phase 39 (23,522 bytes vs 386,864 bytes) with hash `9ba6f3f4c657692870c8111ff6ce08135e909a70f320d184bc1ed7e6720418b3`.
   - Direct execution of `tests/test_phase60_adversarial_oms_benchmark.py ... tests/test_phase65_adversarial_oms_benchmark.py` resulted in **11 FAILED, 37 passed** (AssertionError on report synchronization and SHA-256 slice matching).
   - Root Cause: Worker 2 wrapped only 6 benchmark scripts under `if __name__ == "__main__":`. An additional 15 historical benchmark scripts (`benchmark_phase25` through `benchmark_phase39`) remain unwrapped at module scope and overwrite `reports/quant_benchmark_comparison.md` upon module import during test collection.
   - Specifically:
     - `benchmark_phase25_quant_performance.py`
     - `benchmark_phase26_quant_performance.py`
     - `benchmark_phase27_quant_performance.py`
     - `benchmark_phase28_quant_performance.py`
     - `benchmark_phase29_quant_performance.py`
     - `benchmark_phase30_quant_performance.py`
     - `benchmark_phase31_quant_performance.py`
     - `benchmark_phase32_quant_performance.py`
     - `benchmark_phase33_quant_performance.py`
     - `benchmark_phase34_quant_performance.py`
     - `benchmark_phase35_quant_performance.py`
     - `benchmark_phase36_quant_performance.py`
     - `benchmark_phase37_quant_performance.py`
     - `benchmark_phase38_quant_performance.py`
     - `benchmark_phase39_quant_performance.py`

## Mission
1. Read `d:\Finance\code\stock\.agents\teamwork_preview_auditor_1_gen2\handoff.md`.
2. Inspect each of the 15 benchmark scripts listed above in `trading_system/scripts/`.
3. Identify exact line numbers where module-level report generation and file-writing begins in each script.
4. Formulate the exact drop-in code fix for each script wrapping those blocks under `if __name__ == "__main__":`.
5. Specify the exact command / script to restore `reports/quant_benchmark_comparison.md` from `trading_system/reports/quant_benchmark_comparison.md` (which has the complete 386,864 bytes and SHA-256 `d09edbfd088fe7a030407cd9e65c2e29d9b6ced0939dec69efe20ebb8c432f83`).
6. Write your comprehensive remediation plan to:
   `d:\Finance\code\stock\.agents\teamwork_preview_explorer_remediation_audit\handoff.md`.

## 2026-09-23T13:30:40Z
You are the Audit Remediation Explorer (investigating Forensic Audit Integrity Violation).
Your working directory is: d:\Finance\code\stock\.agents\teamwork_preview_explorer_remediation_audit
Read your dispatch instructions in: d:\Finance\code\stock\.agents\teamwork_preview_explorer_remediation_audit\DISPATCH.md
Read the authoritative user request in:
- d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md
- d:\Finance\code\stock\ORIGINAL_REQUEST.md
Read the full Forensic Auditor Evidence Report in:
- d:\Finance\code\stock\.agents\teamwork_preview_auditor_1_gen2\handoff.md

Your mission:
Address the specific integrity violations identified by the auditor:
1. Read the full auditor evidence report.
2. Inspect the 15 historical benchmark scripts in `trading_system/scripts/` (`benchmark_phase25` through `benchmark_phase39`).
3. Identify exact line numbers and code blocks in each script that perform file writing at top-level module scope.
4. Formulate the exact drop-in fix wrapping those blocks in `if __name__ == "__main__":`.
5. Specify the verification and file restoration method to synchronize `reports/quant_benchmark_comparison.md` with `trading_system/reports/quant_benchmark_comparison.md` (386,864 bytes, SHA-256 `d09edbfd088fe7a030407cd9e65c2e29d9b6ced0939dec69efe20ebb8c432f83`).
6. Write your comprehensive handoff report to `d:\Finance\code\stock\.agents\teamwork_preview_explorer_remediation_audit\handoff.md`.
7. Send a message to orchestrator parent when complete.

