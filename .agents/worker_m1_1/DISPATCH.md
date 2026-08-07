## 2026-08-05T15:55:55Z
<USER_REQUEST>
You are a teamwork_preview_worker implementing financial engineering and quantitative risk fixes for Milestone 1.
Your working directory is: d:\Finance\code\stock\.agents\worker_m1_1.
Read ORIGINAL_REQUEST.md at: d:\Finance\code\stock\ORIGINAL_REQUEST.md.
Read PROJECT.md at: d:\Finance\code\stock\.agents\orchestrator_readiness_audit\PROJECT.md.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Task Scope & Target Files:
1. `src/analysis/portfolio_optimizer.py`: In `calculate_hrp_weights`, change inverse volatility weighting `1.0 / vols_left` to inverse variance weighting `1.0 / (vols_left ** 2)`.
2. `src/ai/ensemble_scorer.py`: In microstructure cost calculation (`_get_cost_pct`), change `(2.0 * clamped_spread)` to `(1.0 * clamped_spread)` to avoid double-deducting full bid-ask spread.
3. `src/ai/prediction_model.py`: In `merge_fundamentals`, fix DatetimeIndex column detection when `df.reset_index()` results in column named `'index'` or unnamed DatetimeIndex, ensuring `date_available` (+60-day filing lag) is always enforced via `pd.merge_asof` rather than bypassing to `join()`. Add `'book_value'` to `FUND_COLS`.
4. `trading_system/run_pipeline.py`: Enforce 60-day filing lag on RIM fundamental fetching (`fund_df`), and add conservative VIX crisis fallback in the `except Exception` handler around RiskManager evaluation (lines ~2643) so missing macro data fails safe rather than bypassing risk controls.
5. `src/analysis/statistics.py`: In `annual_return` calculation, clamp `(1 + total_return)` to a minimum positive float (e.g. `max(1e-6, 1 + total_return)`) to prevent complex number outputs when `total_return < -1.0`. Clamp `float("inf")` in `calculate_sortino_ratio()` to a finite float max (e.g. `999.0`). Ensure consistent VaR/CVaR sign conventions across statistics and portfolio allocator modules.

Execution & Verification:
- Implement all fixes cleanly.
- Run the test suite: `.venv/bin/pytest tests/ -v` (or `.venv\Scripts\python.exe -m pytest tests/ -v` on Windows). Ensure all core tests pass.
- Write a complete `handoff.md` in `d:\Finance\code\stock\.agents\worker_m1_1` detailing all modified files, exact line diffs, test execution outputs, and verification results.
- Send a message to parent when finished.
</USER_REQUEST>

## 2026-08-05T15:56:00Z
<PARENT_MESSAGE>
Context: Additional Milestone 1 fix requirement from Explorer 1 report.
Content: Explorer 1 identified a reporting format gap in `trading_system/run_pipeline.py` (around lines 2938 and 2957), where the table text format string for writing `ensemble_predictions.txt` formats only 17 strategy columns, omitting the 18th strategy `IFS` (`inst_foreign_sector_score`). Consequently, `generate_report.py` line 335 evaluates `len(s_vals)` as 17 and falls back to "-" for `inst_foreign_sector` in `gh-pages/index.html`.
Action: Please include this fix in your task: update `trading_system/run_pipeline.py` lines ~2938/2957 to format all 18 strategy scores including `IFS` (`inst_foreign_sector_score`) into `ensemble_predictions.txt`.
</PARENT_MESSAGE>
