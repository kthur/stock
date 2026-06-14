## 2026-06-12T10:46:55Z
You are teamwork_preview_worker. Your mission is to fix the bugs and vulnerabilities identified by the Challengers in their verification reports.

Please write your coordination files to:
- Progress heartbeat: d:\Finance\code\stock\.agents\worker_fundamental_2\progress.md
- Handoff report: d:\Finance\code\stock\.agents\worker_fundamental_2\handoff.md

Please review the findings in:
1. d:\Finance\code\stock\.agents\challenger_fundamental_1\challenge.md
2. d:\Finance\code\stock\.agents\challenger_fundamental_2\challenge.md
3. d:\Finance\code\stock\.agents\reviewer_fundamental_1\review.md

Implement the following fixes in the codebase:
1. Lookahead Leakage: In `merge_fundamentals` inside `trading_system/src/ai/prediction_model.py`, explicitly sort the price DataFrame (`df_prices`) in ascending chronological order before performing the merge and forward-filling operations.
2. Row Duplication: In `merge_fundamentals`, deduplicate the fundamentals DataFrame (`df_fun`) by grouping/deduplicating by date/symbol (e.g. keeping the last entry per date/symbol) before merging, so that price rows are never duplicated.
3. Duplicate Symbol Column: Drop the `symbol` column from `df_fun` before merging in `merge_fundamentals` (or merge on `['date_align', 'symbol']` if `symbol` is in `df_prices` columns) to avoid generating duplicate `symbol_x` and `symbol_y` columns.
4. KeyError on Partial Features: In `predict_current` inside `trading_system/src/ai/prediction_model.py`, check if all 12 required features are present in the columns (rather than just checking if 'ret_1d' is in columns). If any of the 12 features are missing, proceed to compute/regenerate them.
5. Missing Columns: In `apply_market_normalization` inside `trading_system/src/ai/prediction_model.py`, check if `Close` and `Volume` columns are present in the input DataFrame. If missing, log a warning and return or handle gracefully (e.g. raise a clear ValueError).
6. Constant/Halted Prices dropna: In `_create_features` inside `trading_system/src/ai/prediction_model.py`, handle return calculations for halted or constant price stocks. Specifically, fill NaNs in return columns (`ret_1d`, `ret_5d`, `ret_20d`, `ret_60d`, `vol_20d`) with `0.0` before executing `dropna()` so they are not silently dropped.
7. Stale Prediction Warning: In `predict_current` or `_create_features`, if the latest row is dropped during feature calculation (meaning we predict on a stale day), log a warning.

After implementing these fixes, execute the target test suites and the new adversarial tests:
- `trading_system/tests/test_database.py`
- `trading_system/tests/test_feature_normalization.py`
- `trading_system/tests/test_feature_normalization_stress.py`
- `trading_system/tests/test_post_market_scoring.py`
- `trading_system/tests/test_fundamental_prediction_adversarial.py`
- `trading_system/tests/test_adversarial_fundamental.py`

Verify that all tests pass successfully.

⚠️ MANDATORY INTEGRITY WARNING — include this verbatim in your implementation:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Write progress.md and handoff.md and send a message when done.
