# DISPATCH — Worker M3: Backtest, Pytest Regression & Pipeline Validation Specialist

## Task Assignment
- Working Directory: `d:\Finance\code\stock\.agents\worker_m3`
- Reference Files:
  - `d:\Finance\code\stock\ORIGINAL_REQUEST.md` (MUST READ FIRST)
  - `d:\Finance\code\stock\PROJECT.md`
  - `d:\Finance\code\stock\TEST_INFRA.md`
  - `d:\Finance\code\stock\.agents\explorer_m3_1\handoff.md` (Backtest details)
  - `d:\Finance\code\stock\.agents\explorer_m3_2\handoff.md` (Pytest regression details)
  - `d:\Finance\code\stock\.agents\explorer_m3_3\handoff.md` (Pipeline & Dashboard details)

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Detailed Work Instructions
1. **Comparative Rolling Backtest Verification (F8)**:
   - Execute comparative backtest:
     ```powershell
     cd d:\Finance\code\stock\trading_system
     $env:BACKTEST_YEARS = "5"
     ..\.venv\Scripts\python.exe scripts\compare_backtests.py
     ```
   - Verify generation of `trading_system/scripts/backtest_comparison_results.csv` and inspect output metrics.
   - Run backtest unit tests:
     ```powershell
     cd d:\Finance\code\stock
     .venv\Scripts\python.exe -m pytest tests/test_backtest.py tests/test_cpcv_stress_tester.py -v
     ```

2. **Full Pytest Regression Suite Execution (F9)**:
   - Run the complete 1,600-test regression suite across `tests/` and `trading_system/tests/`:
     ```powershell
     .venv\Scripts\python.exe -m pytest -v --tb=short
     ```
   - Ensure 100% tests PASS (0 failures, 0 errors). Document exact test counts.

3. **Pipeline Execution & GitHub Pages Report Verification (F10)**:
   - Run the trading system prediction pipeline:
     ```powershell
     .venv\Scripts\python.exe trading_system\run_pipeline.py --debug --skip-training
     ```
   - Verify output prediction files in `trading_system/result/`:
     - `ensemble_predictions.txt`
     - `factor_neutralized_predictions.txt`
     - `strategy_data_coverage_report.txt`
     - `portfolio_allocation.txt`
     - `backtest_summary.json`
   - Verify `gh-pages/index.html` generation:
     ```powershell
     .venv\Scripts\python.exe trading_system\scripts\verify_gha_artifacts.py --result-dir trading_system\result --gh-pages-dir gh-pages
     ```

4. **Handoff Documentation**:
   - Write complete results, commands executed, terminal outputs, and metric summaries to `d:\Finance\code\stock\.agents\worker_m3\handoff.md`.
   - Send completion message to parent orchestrator.
