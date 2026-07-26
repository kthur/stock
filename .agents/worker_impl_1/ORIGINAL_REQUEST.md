## 2026-07-04T03:26:16Z
You are the Implementation Worker. Your mission is to modify the codebase and GHA workflows to resolve the identified bugs.
Working directory: `d:\Finance\code\stock\.agents\worker_impl_1\`

DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Please make the following changes:

1. **GitHub Actions Workflows Caching & Skip Logic**:
   - In `.github/workflows/pipeline.yml` and `.github/workflows/training.yml`, update the `Cache AI models` step to use a dynamic key:
     `key: ai-models-v2-${{ steps.date.outputs.date }}-${{ github.run_id }}`
     `restore-keys: ai-models-v2-`
   - In `.github/workflows/pipeline.yml`, insert a step before the `Run prediction pipeline` step to dynamically set `SKIP_TRAINING` based on whether the models are actually restored from cache:
     ```yaml
     - name: Determine if training should be skipped
       id: check-training
       run: |
         if [ -d "trading_system/models" ] && [ "$(ls -A trading_system/models 2>/dev/null)" ]; then
           echo "SKIP_TRAINING=True" >> $GITHUB_ENV
           echo "Models found on disk. Skipping training."
         else
           echo "SKIP_TRAINING=False" >> $GITHUB_ENV
           echo "Models not found on disk. Will run training."
         fi
     ```
     And update the prediction run step's env to pass `SKIP_TRAINING: ${{ env.SKIP_TRAINING }}`.
   - In `.github/workflows/preseed.yml`:
     - Update the `Cache AI models` step to use the same key/restore-keys format.
     - Move the `Get current date` and database cache steps to be *before* the `Run preseed` step, so that the databases are restored prior to the pipeline execution.

2. **run_pipeline.py**:
   - Fix `SKIP_TRAINING` fallback: if pre-trained models are missing, set `should_skip = False` so training is performed automatically.
   - Implement post-pipeline verification checking that the 6 output prediction files exist and are not empty, and check if all expected returns in `pipeline_result.txt` are `0.0`. Log warnings on failure.

3. **prediction_model.py**:
   - Handle missing global feature columns in `_merge_indicator_history` by populating missing columns with `0.0` before ffill.
   - Implement case-insensitive market tag lookups for XGB/LGB/Cat/LSTM models, weights, and calibration dicts.
   - Fix the int vs str key mismatch when loading regression ensemble weights (look up using `str(h)` and fallback to `h`).
   - Log warnings when prediction defaults to `0.0` due to missing models.

4. **vcp_ml_predictor.py**:
   - Align feature columns strictly to `ALL_FEATURES + VCP_FEATURES` and pad missing columns with `0.0`.
   - Implement dynamic weights lookup from `ensemble_weights.json` for VCP ML models instead of hardcoding `[0.4, 0.3, 0.3]`, with fallbacks.
   - Log warnings when prediction defaults to `0.0` due to missing models.

After implementing these fixes, run the existing unit tests with:
`.venv/bin/pytest tests/ -v` (inside `trading_system` folder or root, ensuring you run it using the virtual environment).

Write a detailed handoff.md in your working directory `d:\Finance\code\stock\.agents\worker_impl_1\handoff.md` with:
1. Observation (what was changed)
2. Logic Chain (rationale for the changes)
3. Caveats
4. Conclusion (summary of results)
5. Verification Method (command run and outputs showing tests pass)

Report back when complete.
