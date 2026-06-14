# Project Plan - Fundamental Data Integration (Gen2)

## Objective
Address the 7 bugs/vulnerabilities identified by the Challengers in `trading_system/src/ai/prediction_model.py` and verify using the complete suite of tests and a Forensic Audit.

## Target Fixes
1. **Lookahead Leakage**: Explicitly sort `df_prices` chronologically in ascending order before merging and forward-filling in `merge_fundamentals`.
2. **Row Duplication**: Deduplicate the fundamentals DataFrame (`df_fun`) by grouping/deduplicating by date/symbol (keeping the last entry) before merging to avoid duplicate price rows.
3. **Duplicate Symbol Column**: Drop the `symbol` column from `df_fun` before merging to avoid duplicate `symbol_x` and `symbol_y` columns.
4. **KeyError on Partial Features**: Check if all 12 required features are present in the columns in `predict_current` rather than just checking if `ret_1d` is present.
5. **Missing Columns**: Check if `Close` and `Volume` columns are present in the input DataFrame in `apply_market_normalization`. If missing, handle gracefully (e.g. raise ValueError or return default).
6. **Constant/Halted Prices dropna**: Fill returns NaNs (`ret_1d`, `ret_5d`, `ret_20d`, `ret_60d`, `vol_20d`) with `0.0` before running `dropna()` in `_create_features`.
7. **Stale Prediction Warning**: Log a warning in `predict_current` if the latest row is dropped during feature calculation.

## Planned Milestones
- **Milestone 1: Exploration & Verification of Fix Strategies**
  - Spawn 3 Explorers to analyze the codebase, review existing challenger reports, and propose specific fix strategies.
- **Milestone 2: Fix Implementation**
  - Spawn a Worker to apply the fixes to `trading_system/src/ai/prediction_model.py`.
- **Milestone 3: Verification & Review**
  - Spawn 2 Reviewers, 2 Challengers, and a Forensic Auditor to inspect the changes, run stress/adversarial tests, and perform a Forensic Integrity Audit.

## Verification Protocol
For the iteration loop:
1. All tests must pass (including new adversarial tests).
2. Reviewer verdicts must be APPROVE.
3. Challenger verdicts must confirm no vulnerabilities remaining.
4. Forensic Auditor verdict must be CLEAN.
