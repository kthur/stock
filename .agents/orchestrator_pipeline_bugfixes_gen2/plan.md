# Execution Plan - Pipeline Bug Fixes (R1-R5) - Generation 2

## Phase 1: Review Existing Changes & Status
1. Inspect the codebase files directly using file viewing tools to confirm R1-R5 are implemented in:
   - `trading_system/src/data_layer/indicator_storage.py` (R1)
   - `trading_system/src/ai/prediction_model.py` (R2, R4)
   - `trading_system/run_pipeline.py` (R3)
   - `trading_system/src/persistence/database.py` (R5)
2. Verify that the previous worker's changes match the requirements.

## Phase 2: Implementation Track & Testing Verification
1. Spawn 1 `teamwork_preview_worker` agent.
2. Direct the Worker to run the existing unit tests (`.venv/bin/pytest tests/ -v`) and verify they all pass.
3. Direct the Worker to run the pipeline (`.venv/bin/python trading_system/run_pipeline.py`) to verify everything is executing successfully and that predictions for 120d and 200d are correctly cached/saved in the SQLite DB.
4. Wait for the Worker's handoff report containing the execution output and test verification.

## Phase 3: Review and Adversarial Verification
1. Spawn 2 `teamwork_preview_reviewer` agents to independently review the modified code.
2. Spawn 2 `teamwork_preview_challenger` agents to verify:
   - Thread-safety of `StockPriceDB._get_conn`
   - `merge_fundamentals` with missing `date_fund` column
   - Expected return predictions saved for 120 and 200 day horizons
3. Spawn 1 `teamwork_preview_auditor` agent to run the integrity audit.
4. Gate checklist verification:
   - All tests pass (including challenger-written tests).
   - Reviewer verdicts are positive.
   - Auditor reports CLEAN.

## Phase 4: Final Reporting & Handoff
1. Write the final `handoff.md` in `d:\Finance\code\stock\.agents\orchestrator_pipeline_bugfixes_gen2`.
2. Report completion back to the Sentinel.
