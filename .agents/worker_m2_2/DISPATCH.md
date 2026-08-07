## 2026-08-05T16:03:37Z
<USER_REQUEST>
You are a teamwork_preview_worker implementing GitHub Actions workflow fixes for Milestone 2.
Your working directory is: d:\Finance\code\stock\.agents\worker_m2_2.
Read ORIGINAL_REQUEST.md at: d:\Finance\code\stock\ORIGINAL_REQUEST.md.
Read PROJECT.md at: d:\Finance\code\stock\.agents\orchestrator_readiness_audit\PROJECT.md.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Task Scope & Target Files:
1. `.github/workflows/pipeline.yml` & `.github/workflows/training.yml`:
   - Replace post-job DB cache saves in parallel matrix jobs with `actions/cache/restore@v4` to prevent cache key collisions when 5 matrix targets complete.
   - Update `SKIP_TRAINING` in `pipeline.yml` so it dynamically evaluates model cache hit status (`${{ steps.cache-models.outputs.cache-hit != 'true' }}`) rather than hardcoding `'True'`.
   - Update cron schedule in `pipeline.yml` to 22:00 UTC (07:00 KST) to ensure US market close data is processed.
2. `.github/workflows/realtime_monitor.yml`:
   - Append `${{ github.run_id }}` to cache save key so intraday state updates can save cleanly every 15 minutes.
3. `weekly_hpo.yml` & `trading_system/tune_models.py` (or optuna script):
   - Update script entry point to read `N_TRIALS = int(os.environ.get("N_TRIALS", 5))` so workflow environment variable is honored.

Execution & Verification:
- Implement all fixes cleanly.
- Verify YAML syntax and Python script parsing.
- Write `handoff.md` detailing modified files and line diffs. Send a message to parent when finished.
</USER_REQUEST>
