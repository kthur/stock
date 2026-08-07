## 2026-08-05T16:01:54Z
You are a teamwork_preview_worker applying targeted edge-case hardening fixes for Milestone 1.
Your working directory is: d:\Finance\code\stock\.agents\worker_m1_remediation.
Read ORIGINAL_REQUEST.md at: d:\Finance\code\stock\ORIGINAL_REQUEST.md.
Read PROJECT.md at: d:\Finance\code\stock\.agents\orchestrator_readiness_audit\PROJECT.md.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Target Files & Fixes:
1. `trading_system/src/data_layer/hybrid_storage.py`:
   - In `ParquetWALBuffer.write_symbol_wal`, ensure `df_copy.index.name = "date"` if index name is missing or named `"index"` before `reset_index()`.
   - In `flush_staging_to_master`, handle both `"date"` and `"index"` column names explicitly:
     ```python
     if "index" in combined.columns and "date" not in combined.columns:
         combined.rename(columns={"index": "date"}, inplace=True)
     ```
2. `trading_system/dag_pipeline.py`:
   - In `CheckpointManager._load_manifest`, ensure loaded JSON is a `dict` (e.g., `if not isinstance(data, dict): return {"completed_tasks": {}, "failed_tasks": {}}`).
   - In `CheckpointManager.is_valid`, verify that artifact files exist AND have non-zero size (`art_path.stat().st_size > 0`).
   - In `DAGRunner.run()`, preserve task registered artifacts when calling `mark_completed()` or pass artifacts through.

Verification:
- Run pytest suites: `.venv/bin/pytest tests/ -v` (or `.venv\Scripts\python.exe -m pytest tests/ -v`).
- Write `handoff.md` detailing the changes and test execution output.
- Send a message to parent when finished.

## 2026-08-05T16:03:58Z
**Context**: Additional stress-test fixes from Challenger 1.

**Content**: Challenger 1 identified 3 edge-case items:
1. In `prediction_model.py`: Handle `'book_value'` safely (e.g. `df.get('book_value', np.nan)`) to prevent `KeyError`.
2. In `statistics.py`: Handle `ZeroDivisionError` when equity drops to 0, and clamp `profit_factor` `float("inf")` to finite float (e.g., `999.0`).
3. In `intraday_stop_loss.py`: Replace `[np.inf, -np.inf]` with `np.nan` before `.dropna()` on price DataFrames.

**Action**: Please incorporate these 3 quick fixes into your code changes and verify with pytest.


## 2026-08-05T16:02:23Z
**Context**: Additional hardening item for CrisisDetector in `src/risk/risk_manager.py`.

**Content**: Challenger 2 identified that when VIX spikes above 30.0 or 40.0 alone without compound FX/drawdown spikes, the 25% weighted composite score in `CrisisDetector.evaluate()` stays below the 0.25 threshold.

**Action**: Add a standalone VIX override check in `CrisisDetector.evaluate()`:
- If `vix >= 40.0`, force `crisis_level = max(crisis_level, CrisisLevel.SEVERE)` (or return SEVERE).
- If `vix >= 30.0`, force `crisis_level = max(crisis_level, CrisisLevel.ACTIVE)` (or return ACTIVE).
Also ensure lines 2938, 2957, 2979, 2993-2994 in `trading_system/run_pipeline.py` format all 18 strategy columns including `IFS`. Run pytest tests to verify.

