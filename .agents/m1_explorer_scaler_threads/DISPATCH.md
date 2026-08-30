## 2026-08-29T22:07:18Z

You are M1 Explorer 2: Scaler Caching & ML Thread Allocation Specialist.
Working directory: d:\Finance\code\stock\.agents\m1_explorer_scaler_threads

Read:
- ORIGINAL_REQUEST.md at: d:\Finance\code\stock\ORIGINAL_REQUEST.md
- PROJECT.md at: d:\Finance\code\stock\PROJECT.md
- Previous survey findings at: d:\Finance\code\stock\.agents\explorer_pipeline_perf\analysis.md

Milestone 1 Scope for your investigation:
1. `src/ai/feature_engineering.py`:
   - Design thread-safe in-memory caching for `load_scaler(model_dir, market, horizon)` using `@functools.lru_cache(maxsize=128)` or dict cache with cache clearing helper.
2. `src/ai/prediction_model.py`:
   - In `train()`, dynamically compute `intra_n_jobs = max(1, (os.cpu_count() or 4) // max_workers)` when multi-market training is active in `run_pipeline.py`.
   - Pass `n_jobs=intra_n_jobs` to XGBoost/LightGBM and `thread_count=intra_n_jobs` to CatBoost to eliminate thread thrashing.
3. Check existing tests in `tests/test_prediction_model.py`.

Deliverables:
- Write exact code specifications and test verification commands to `d:\Finance\code\stock\.agents\m1_explorer_scaler_threads\analysis.md`
- Write `handoff.md` and send message to orchestrator.
