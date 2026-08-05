"""
Process Exit Code Resilience Harness — Testing run_pipeline.py Partial Success Logic
"""

import os
import sys
import tempfile
import shutil

def evaluate_current_pipeline_exit_logic(result_dir: str, exc: Exception) -> int:
    """Replicates current run_pipeline.py lines 3180-3206 logic."""
    essential_file = os.path.join(result_dir, "pipeline_result.txt")
    has_results = os.path.exists(essential_file) and os.path.getsize(essential_file) > 0
    if has_results:
        return 0
    else:
        return 1

def evaluate_proposed_report_exit_logic(result_dir: str, exc: Exception) -> int:
    """Replicates SYSTEM_IMPROVEMENT_REPORT.md Section 4.1 logic."""
    essential_reg = os.path.join(result_dir, "pipeline_result.txt")
    essential_ens = os.path.join(result_dir, "ensemble_predictions.txt")
    has_reg = os.path.exists(essential_reg) and os.path.getsize(essential_reg) > 0
    has_ens = os.path.exists(essential_ens) and os.path.getsize(essential_ens) > 0
    has_results = has_reg and has_ens
    if has_results:
        return 0
    else:
        return 1

def test_scenarios():
    test_dir = tempfile.mkdtemp()
    results = []

    try:
        # Scenario A: Regression result exists (100 bytes), Ensemble predictions MISSING
        reg_file = os.path.join(test_dir, "pipeline_result.txt")
        with open(reg_file, "w") as f:
            f.write("000001,0.15\n")

        curr_code = evaluate_current_pipeline_exit_logic(test_dir, RuntimeError("Ensemble scoring crashed"))
        prop_code = evaluate_proposed_report_exit_logic(test_dir, RuntimeError("Ensemble scoring crashed"))

        results.append({
            "scenario": "A. Regression exists, Ensemble MISSING",
            "current_exit_code": curr_code,
            "proposed_exit_code": prop_code,
            "current_verdict": "FALSE SUCCESS (Masks Failure)" if curr_code == 0 else "FAIL",
            "proposed_verdict": "DETECTED FAILURE (Process Exit 1)" if prop_code == 1 else "FAIL",
        })

        # Scenario B: Regression result exists (100 bytes), Ensemble predictions TRUNCATED (0 bytes)
        ens_file = os.path.join(test_dir, "ensemble_predictions.txt")
        open(ens_file, "w").close() # 0 bytes

        curr_code_b = evaluate_current_pipeline_exit_logic(test_dir, RuntimeError("Write truncated"))
        prop_code_b = evaluate_proposed_report_exit_logic(test_dir, RuntimeError("Write truncated"))

        results.append({
            "scenario": "B. Regression exists, Ensemble 0-BYTES",
            "current_exit_code": curr_code_b,
            "proposed_exit_code": prop_code_b,
            "current_verdict": "FALSE SUCCESS (Masks Truncation)" if curr_code_b == 0 else "FAIL",
            "proposed_verdict": "DETECTED FAILURE (Process Exit 1)" if prop_code_b == 1 else "FAIL",
        })

        # Scenario C: Both Regression and Ensemble exist (>0 bytes)
        with open(ens_file, "w") as f:
            f.write("000001,0.85,0.12\n")

        curr_code_c = evaluate_current_pipeline_exit_logic(test_dir, RuntimeError("Minor warning"))
        prop_code_c = evaluate_proposed_report_exit_logic(test_dir, RuntimeError("Minor warning"))

        results.append({
            "scenario": "C. Both Regression and Ensemble exist (>0 bytes)",
            "current_exit_code": curr_code_c,
            "proposed_exit_code": prop_code_c,
            "current_verdict": "PARTIAL SUCCESS (Exit 0)",
            "proposed_verdict": "PARTIAL SUCCESS (Exit 0)",
        })

    finally:
        shutil.rmtree(test_dir, ignore_errors=True)

    return results

if __name__ == "__main__":
    print("=== Pipeline Exit Code Logic Challenge ===")
    scenarios = test_scenarios()
    for s in scenarios:
        print(f"\nScenario: {s['scenario']}")
        print(f"  Current logic:  Exit {s['current_exit_code']} -> {s['current_verdict']}")
        print(f"  Proposed logic: Exit {s['proposed_exit_code']} -> {s['proposed_verdict']}")
