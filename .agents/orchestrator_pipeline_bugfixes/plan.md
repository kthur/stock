# Execution Plan - Pipeline Bug Fixes (R1-R5)

## Phase 1: Exploration
1. Spawn 3 `teamwork_preview_explorer` agents to independently locate and analyze the 5 target issues:
   - Explorer 1 focuses on:
     - `src/data_layer/indicator_storage.py` (R1) - locate `save_predictions` and check horizons.
     - `src/persistence/database.py` (R5) - locate `_get_conn` and identify the race condition/connection leaks.
   - Explorer 2 focuses on:
     - `src/ai/prediction_model.py` (R2 and R4) - locate `merge_fundamentals` and `pct_change()` calls.
   - Explorer 3 focuses on:
     - `trading_system/run_pipeline.py` (R3) - locate the VCP universe map construction and investigate usage of `universe.get()`.
2. Synthesize explorer results and confirm the exact code blocks that need replacement.

## Phase 2: Implementation
1. Spawn 1 `teamwork_preview_worker` agent.
2. Direct the Worker to modify the 4 files:
   - Change horizon list in `indicator_storage.py`'s `save_predictions` to `[1, 5, 10, 20, 30, 60, 120, 200]`.
   - Add `errors='ignore'` to the drop operation on `date_fund` in `prediction_model.py`'s `merge_fundamentals`.
   - Modify `run_pipeline.py`'s VCP universe map construction to use direct column access like `universe['symbol']`.
   - Remove `fill_method=None` from all `pct_change()` calls in `prediction_model.py`.
   - Implement thread-safe connection initialization in `database.py`'s `StockPriceDB._get_conn` using a threading Lock.
3. Direct the Worker to run the existing unit tests (`pytest tests/ -v`) and verify they all pass.

## Phase 3: Review and Adversarial Verification
1. Spawn 2 `teamwork_preview_reviewer` agents.
2. Reviewers independently review the modified code for:
   - Syntax correctness.
   - Robustness and side-effects.
   - Alignment with original signatures and requirements.
3. Spawn 2 `teamwork_preview_challenger` agents.
4. Challengers write or run tests specifically targeting:
   - Thread-safety of `StockPriceDB._get_conn`.
   - `merge_fundamentals` with missing `date_fund` column.
   - Predictions saved for 120 and 200 day horizons.
5. Spawn 1 `teamwork_preview_auditor` agent to run the integrity audit.
6. Verify all gate conditions:
   - All tests pass (including challenger-written regression tests).
   - Reviewer verdicts are positive.
   - Auditor reports CLEAN.

## Phase 4: Final Pipeline Execution & Report
1. Verify `run_pipeline.py` executes successfully.
2. Verify predictions for 120d and 200d are correctly cached/saved in the SQLite DB.
3. Write `handoff.md` and report completion back to the Sentinel.
