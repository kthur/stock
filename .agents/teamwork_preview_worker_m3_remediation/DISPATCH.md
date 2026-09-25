# Dispatch: Worker 3 (Final Benchmark Reports & Script Guarding Remediation)

## Working Directory
d:\Finance\code\stock\.agents\teamwork_preview_worker_m3_remediation

## Original Request
d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md
d:\Finance\code\stock\ORIGINAL_REQUEST.md

## Reference Audit and Diff Specifications
- Forensic Auditor Report: `d:\Finance\code\stock\.agents\teamwork_preview_auditor_1_gen2\handoff.md`
- Remediation Table: `d:\Finance\code\stock\.agents\teamwork_preview_explorer_remediation_audit\table_summary.txt`
- Exact Drop-in Diffs: `d:\Finance\code\stock\.agents\teamwork_preview_explorer_remediation_audit\diff_analysis.txt`

## Exclusive File Ownership
You have exclusive write ownership over:
- `trading_system/scripts/benchmark_phase25_quant_performance.py`
- `trading_system/scripts/benchmark_phase26_quant_performance.py`
- `trading_system/scripts/benchmark_phase27_quant_performance.py`
- `trading_system/scripts/benchmark_phase28_quant_performance.py`
- `trading_system/scripts/benchmark_phase29_quant_performance.py`
- `trading_system/scripts/benchmark_phase30_quant_performance.py`
- `trading_system/scripts/benchmark_phase31_quant_performance.py`
- `trading_system/scripts/benchmark_phase32_quant_performance.py`
- `trading_system/scripts/benchmark_phase33_quant_performance.py`
- `trading_system/scripts/benchmark_phase34_quant_performance.py`
- `trading_system/scripts/benchmark_phase35_quant_performance.py`
- `trading_system/scripts/benchmark_phase36_quant_performance.py`
- `trading_system/scripts/benchmark_phase37_quant_performance.py`
- `trading_system/scripts/benchmark_phase38_quant_performance.py`
- `trading_system/scripts/benchmark_phase39_quant_performance.py`
- `reports/quant_benchmark_comparison.md`
- `trading_system/reports/quant_benchmark_comparison.md`
- `trading_system/result/quant_benchmark_comparison.md`

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Tasks
1. Apply the exact drop-in `if __name__ == "__main__":` diffs specified in `d:\Finance\code\stock\.agents\teamwork_preview_explorer_remediation_audit\diff_analysis.txt` to all 15 benchmark scripts (`benchmark_phase25` through `benchmark_phase39`).
2. Restore `reports/quant_benchmark_comparison.md` from `trading_system/reports/quant_benchmark_comparison.md` (which has the full 386,864 bytes and SHA-256 `d09edbfd088fe7a030407cd9e65c2e29d9b6ced0939dec69efe20ebb8c432f83`). Verify all 3 paths (`reports/`, `trading_system/reports/`, `trading_system/result/`) have identical SHA-256 digests.
3. Test Verification:
   - Run `.venv\Scripts\python.exe -m pytest tests/test_phase60_adversarial_oms_benchmark.py tests/test_phase61_adversarial_oms_benchmark.py tests/test_phase62_adversarial_oms_benchmark.py tests/test_phase63_adversarial_oms_benchmark.py tests/test_phase64_adversarial_oms_benchmark.py tests/test_phase65_adversarial_oms_benchmark.py tests/test_phase66_adversarial_oms_benchmark.py --tb=short` -> verify 56/56 passed.
   - Verify collection isolation: run tests importing earlier benchmark tests (e.g. `test_phase39_adversarial_oms_benchmark.py`) and re-check that `reports/quant_benchmark_comparison.md` is NOT truncated.
   - Verify `trading_system/run_pipeline.py` imports and compiles without error.
4. Write your full handoff report to `d:\Finance\code\stock\.agents\teamwork_preview_worker_m3_remediation\handoff.md`.
## 2026-09-23T16:38:56Z
Received dispatch matching initial dispatch.
