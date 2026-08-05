## 2026-08-05T02:23:18Z

<USER_REQUEST>
You are Worker 3 (Remediation & Code Enhancement Specialist) for the Stock Trading System Deep Audit.

Working directory: `d:\Finance\code\stock\.agents\worker_m3_remediation`
Original request file: `d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md`

Your task:
Apply the code enhancements and test fixture remediations identified by the Reviewers and Challengers to achieve a 100% pytest pass rate and complete system alignment.

Specific tasks:
1. **Test Suite Remediation (Achieve 100% Pytest Pass Rate)**:
   - Fix `tests/test_correlation_suppression.py`: Update the `sample_17_strategy_df` fixture (or add `inst_foreign_sector_score` column) so all 5 correlation suppression tests pass with the 18-strategy matrix.
   - Fix `tests/test_phase1_target_and_walkforward.py` & `tests/test_target_labeling_and_walkforward.py`: Ensure `transform_sharpe` handles/imputes `NaN` values to `0.0`.
   - Fix `tests/test_dag_pipeline_stress_m1.py`: Adjust `test_concurrent_parquet_saves_same_filename_race_condition` Windows file permission retry loop.
   - Fix `tests/test_fast_cointegration.py`: Adjust `test_two_stage_filtering_recall` recall threshold tolerance.

2. **Codebase Enhancements (Section 4 Implementation)**:
   - Update `trading_system/scripts/verify_gha_artifacts.py`: Extend `files_map` / `check_funcs` to include all 18 strategies (`arm_factor`, `card_factor`, `latr_factor`, `inst_foreign_sector`), fix table header formatting (18 columns), and update HTML panel regex for `panel-vcpml`.
   - Update `trading_system/run_pipeline.py`: Modify process return code logic to require both `pipeline_result.txt` AND `ensemble_predictions.txt` existence before returning exit code 0.
   - Update `trading_system/generate_report.py`: Add sticky table header CSS (`thead th { position: sticky; top: 44px; background: var(--surface2); z-index: 10; }`).
   - Update `SYSTEM_IMPROVEMENT_REPORT.md`: In Section 4.3, update the sticky header CSS recommendation to specify `top: 44px` to account for the sticky mobile navigation bar (`.tabs`).

3. **Execution & Verification**:
   - Re-run `.venv\Scripts\python.exe -m pytest tests/ -v` and confirm 100% pass rate (0 failures).
   - Re-run `.venv\Scripts\python.exe trading_system/scripts/verify_gha_artifacts.py --result-dir trading_system/result --gh-pages-dir gh-pages` and confirm valid status.
   - Document all changes and execution logs in `d:\Finance\code\stock\.agents\worker_m3_remediation\remediation_results.md`.
   - Write your complete handoff report to `d:\Finance\code\stock\.agents\worker_m3_remediation\handoff.md`.
   - Send a completion message back to parent with test pass rates and verification outputs.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.
</USER_REQUEST>
