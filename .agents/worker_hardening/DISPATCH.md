## 2026-08-28T23:10:47Z
You are a Worker applying a defensive hardening patch to `trading_system/src/core/rim_valuation.py` as recommended by Challenger 1 (BUG-CH1-01).

DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Task Details:
1. In `trading_system/src/core/rim_valuation.py`:
   - In `compute_rim_scores`: write back the coerced numeric series for `operating_income`, `net_income`, and `book_value` to `df` so that any dirty raw string values (e.g. `'N/A'`, `'None'`, `'null'`) are safely converted to numeric floats / NaN:
     ```python
     if has_op_inc:
         df['operating_income'] = op_inc
     if has_net_inc:
         df['net_income'] = net_inc
     if 'book_value' in df.columns:
         df['book_value'] = bv
     ```
   - In `_apply_roe_normalization`: defensively parse `book_value` with a safe float converter:
     ```python
     def _safe_float(val):
         if val is None:
             return None
         try:
             v = float(val)
             return v if np.isfinite(v) else None
         except (ValueError, TypeError):
             return None
     ```
     and use `book_value=_safe_float(row.get('book_value'))` when instantiating `RIMStockData`.

2. Run the test suites:
   `.venv\Scripts\pytest tests/test_rim_strategy.py tests/test_challenger_rim_coverage_stress.py tests/test_challenger2_dashboard_parser_stress.py tests/test_report_ux_and_rounding.py tests/test_report_generator_hrp.py tests/test_kst_and_coverage_reasoning.py -v`

3. Verify HTML dashboard generation:
   `.venv\Scripts\python.exe trading_system/generate_report.py --result-dir trading_system/result --out gh-pages/index.html`

Your working directory is: `d:\Finance\code\stock\.agents\worker_hardening`.
Write your completion report to `d:\Finance\code\stock\.agents\worker_hardening\handoff.md`.
Use `send_message` when done.
