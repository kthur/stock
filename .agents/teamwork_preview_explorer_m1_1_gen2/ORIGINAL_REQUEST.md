## 2026-06-12T13:02:13Z
You are teamwork_preview_explorer. Your mission is to analyze the prediction model implementation in `trading_system/src/ai/prediction_model.py` and recommend a fix strategy for the following 7 issues identified in the previous verification run:
1. Lookahead Leakage: In `merge_fundamentals` inside `trading_system/src/ai/prediction_model.py`, explicitly sort the price DataFrame (`df_prices`) in ascending chronological order before performing the merge and forward-filling operations.
2. Row Duplication: In `merge_fundamentals`, deduplicate the fundamentals DataFrame (`df_fun`) by grouping/deduplicating by date/symbol (e.g. keeping the last entry per date/symbol) before merging, so that price rows are never duplicated.
3. Duplicate Symbol Column: Drop the `symbol` column from `df_fun` before merging in `merge_fundamentals` (or merge on `['date_align', 'symbol']` if `symbol` is in `df_prices` columns) to avoid generating duplicate `symbol_x` and `symbol_y` columns.
4. KeyError on Partial Features: In `predict_current` inside `trading_system/src/ai/prediction_model.py`, check if all 12 required features are present in the columns (rather than just checking if 'ret_1d' is in columns). If any of the 12 features are missing, proceed to compute/regenerate them.
5. Missing Columns: In `apply_market_normalization` inside `trading_system/src/ai/prediction_model.py`, check if `Close` and `Volume` columns are present in the input DataFrame. If missing, log a warning and return or handle gracefully (e.g. raise a clear ValueError).
6. Constant/Halted Prices dropna: In `_create_features` inside `trading_system/src/ai/prediction_model.py`, handle return calculations for halted or constant price stocks. Specifically, fill NaNs in return columns (`ret_1d`, `ret_5d`, `ret_20d`, `ret_60d`, `vol_20d`) with `0.0` before executing `dropna()` so they are not silently dropped.
7. Stale Prediction Warning: In `predict_current` or `_create_features`, if the latest row is dropped during feature calculation (meaning we predict on a stale day), log a warning.

Please write your analysis to your working directory:
- Working directory: d:\Finance\code\stock\.agents\teamwork_preview_explorer_m1_1_gen2\
- Handoff report: d:\Finance\code\stock\.agents\teamwork_preview_explorer_m1_1_gen2\handoff.md

Do NOT modify any source code files. Recommend concrete change strategies.
