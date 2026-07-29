## 2026-07-29T14:29:54Z
You are Worker 2 (remediation worker) for Milestone 2 of the Stock Trading System project.
Your Working Directory: d:\Finance\code\stock\.agents\teamwork_preview_worker_m2_remediation
Project Root: d:\Finance\code\stock
Scope Document: d:\Finance\code\stock\.agents\orchestrator_r8\PROJECT.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Python environment constraint:
ALWAYS use `.venv\Scripts\python.exe` on Windows to run builds, tests, or python scripts.

Reviewer Feedback & Required Fixes:
Reviewer 2 identified a critical bug in `EnsembleScoringEngine.combine_predictions` (`src/ai/ensemble_scorer.py`):
1. In `combine_predictions`, strategy DataFrames were pruned to `['symbol', score_col]`, which stripped crucial metadata columns (`name`, `market`, `volume`, `close`).
2. Because `name` was stripped, `_is_illiquid_or_preferred` evaluated `row.get('name', '')` as `''`. Preferred stocks (e.g. `'삼성전자우'`) and SPACs bypassed the liquidity filter.
3. Because `market` was stripped, `_get_cost_pct` evaluated `row.get('market', '')` as `''`. KOSDAQ and KONEX symbols fell back to KOSPI transaction cost rules.
4. `test_liquidity_and_preferred_stock_filter` failed.

Task:
1. Fix `combine_predictions` in `src/ai/ensemble_scorer.py`: Preserve metadata columns (`name`, `market`, `volume`, `close`) when merging strategy DataFrames into `merged`. Ensure `merged` retains `name`, `market`, and `volume` across all strategy merges.
2. Verify that `_is_illiquid_or_preferred` correctly filters out preferred stocks (`name.endswith('우')`), SPACs (`'스팩' in name`), and low-volume stocks.
3. Verify that `_get_cost_pct` correctly assigns transaction costs based on `market` (`KONEX`: 0.8% + 0.5% = 1.30%, `KOSDAQ`: 0.5% + 0.5% = 1.00%, `KOSPI`: 0.35% + 0.5% = 0.85%, `SP500`: 0.10% + 0.5% = 0.60%).
4. Execute unit tests using `.venv\Scripts\python.exe -m pytest trading_system/tests/test_r1_ensemble_regime_fixes.py` and `.venv\Scripts\python.exe -m pytest tests/`. Ensure ALL tests pass 100%.

Document all changes and test outputs in `d:\Finance\code\stock\.agents\teamwork_preview_worker_m2_remediation\handoff.md`.
Then send a summary message back to parent orchestrator.
