# GitHub Actions Workflows & Automation Setup Audit Report

**Working Directory**: `d:\Finance\code\stock\.agents\teamwork_preview_explorer_m2_2`  
**Milestone**: Milestone 2 — Software Architecture & Pipeline Robustness Audit  
**Target Workflows**:
- `.github/workflows/pipeline.yml`
- `.github/workflows/training.yml`
- `.github/workflows/preseed.yml`
- `.github/workflows/pytest.yml`
- `.github/workflows/realtime_monitor.yml`
- `.github/workflows/weekly_hpo.yml`

---

## Executive Summary

A comprehensive audit of the 6 GitHub Actions workflow files in `.github/workflows/` was conducted to evaluate cron schedule timing, trigger conditions, runner OS, Python environment setup, artifact upload/download pipelines, GitHub Pages deployment, secret management, failure recovery, and potential race conditions.

Key findings include:
1. **Critical Cache Save Race Condition in Parallel Matrix Jobs**: Both `pipeline.yml` and `training.yml` run 5 matrix targets in parallel (`SP500`, `NASDAQ`, `RUSSELL2000`, `KOSPI`, `KOSDAQ`) using `actions/cache@v4` (restore AND save) for shared database files (`stock_prices.db` and `market_indicators.db`). Because all 5 parallel matrix runners try to write to the identical cache key `stock-prices-db-${date}` upon completion, only the first runner to finish succeeds. The remaining 4 runners fail post-step cache upload with immutable key collisions, causing newly fetched price and indicator history for those 4 markets to be permanently lost from the cache.
2. **Critical Intraday Cache Immutability Bug in `realtime_monitor.yml`**: `realtime_monitor.yml` runs every 15 minutes during trading hours and saves state to key `realtime-state-${date}`. Because GHA cache keys are immutable once created, the key saved by the 09:00 KST run blocks all 27 subsequent runs that day from saving updated `realtime_state.db` files. Stop-loss and take-profit trigger histories recorded during intraday runs are lost.
3. **Cron Schedule Misalignment for US Markets in `pipeline.yml`**: The daily pipeline is scheduled at `30 11 * * 1-5` (11:30 UTC / 20:30 KST). At 11:30 UTC, US equity markets (NYSE/NASDAQ) have not opened for the day (opening at 13:30/14:30 UTC). As a result, daily prediction runs executed at 11:30 UTC predict US markets using price data from the previous trading day rather than today's market close.
4. **Hardcoded `SKIP_TRAINING: 'True'` vs Model Cache Misses**: In `pipeline.yml`, `SKIP_TRAINING: 'True'` is hardcoded in the step environment variables, preventing automatic fallback model retraining when an AI model cache miss occurs.
5. **Hyperparameter Tuning Environment Override Ignored**: `weekly_hpo.yml` passes `N_TRIALS: '30'`, but `trading_system/scripts/tune_models.py` hardcodes `n_trials=5` when executed as a script, ignoring the environment variable.

---

## Detailed Audit Findings by Workflow

### 1. Daily Pipeline Workflow (`.github/workflows/pipeline.yml`)

#### Line Numbers & Code Snippet: Cron & Triggers (Lines 3-12)
```yaml
on:
  push:
    branches: [ main, master ]
  schedule:
    - cron: '30 11 * * 1-5'
  workflow_dispatch:

concurrency:
  group: pipeline-${{ github.ref }}
  cancel-in-progress: true
```
- **Issue 1.1 (Timing Misalignment for US Markets)**:
  - Cron `30 11 * * 1-5` executes at 11:30 UTC (20:30 KST).
  - KRX markets close at 15:30 KST (06:30 UTC), so Korean market price data for the day is complete.
  - However, US markets open at 13:30 UTC (22:30 KST in EDT) or 14:30 UTC (23:30 KST in EST) and close at 20:00/21:00 UTC (05:00/06:00 KST next morning).
  - Running at 11:30 UTC means US markets (SP500, NASDAQ, RUSSELL2000) have not yet traded for the calendar day.
  - **Recommended Fix**: Shift cron schedule to `0 22 * * 1-5` (22:00 UTC / 07:00 KST next morning) or `0 0 * * 2-6` (00:00 UTC / 09:00 KST Tuesday-Saturday), ensuring all global market sessions (both KRX and US) have closed before pipeline execution.

- **Issue 1.2 (Concurrency Cancellation Hazard on Push)**:
  - `concurrency.cancel-in-progress: true` cancels any currently running daily pipeline when a new push to `main` occurs.
  - Because the matrix pipeline takes 15–30+ minutes, code pushes cancel active runs mid-job, leading to incomplete cache saves, missing GHA release assets, and partial dashboard updates.
  - **Recommended Fix**: Set `cancel-in-progress: false` or restrict `push` triggers with path filters (`paths-ignore: ['**.md', 'docs/**']`).

#### Line Numbers & Code Snippet: Shared Database Cache Save Collision (Lines 46-65)
```yaml
- name: Cache stock_prices.db
  uses: actions/cache@v4
  id: db-cache
  with:
    path: trading_system/stock_prices.db
    key: stock-prices-db-${{ steps.date.outputs.date }}
    restore-keys: |
      stock-prices-db-

- name: Cache market_indicators.db
  uses: actions/cache@v4
  id: indicators-cache
  with:
    path: trading_system/market_indicators.db
    key: market-indicators-db-${{ steps.date.outputs.date }}
    restore-keys: |
      market-indicators-db-
```
- **Issue 1.3 (Parallel Matrix DB Cache Save Collision)**:
  - The `run-pipeline` job uses a 5-target matrix (`SP500`, `NASDAQ`, `RUSSELL2000`, `KOSPI`, `KOSDAQ`).
  - `actions/cache@v4` performs both **restore** at step start and **save** at post-job completion.
  - All 5 parallel runners restore `stock-prices-db-${date}` and `market-indicators-db-${date}`.
  - During execution, each matrix runner fetches price data for its specific target market and updates its local SQLite DB files.
  - At job completion, all 5 runners attempt to write their local SQLite file to the exact same cache key `stock-prices-db-${date}`.
  - Whichever matrix target finishes first (e.g., `SP500`) saves its cache key. The other 4 matrix targets fail post-step cache upload with `Cache key stock-prices-db-... already exists`.
  - Data fetched by the other 4 matrix runners during that run is discarded and never saved to the repository cache.
  - **Recommended Fix**: Replace `actions/cache@v4` with `actions/cache/restore@v4` in matrix pipeline jobs so matrix runners only restore the cache and do not attempt post-job cache saves. Persisting updated databases should be handled exclusively by single-runner jobs like `preseed.yml`.

#### Line Numbers & Code Snippet: Static `SKIP_TRAINING: 'True'` (Lines 67-98)
```yaml
- name: Cache AI models (Restore only)
  uses: actions/cache/restore@v4
  id: models-cache
  with:
    path: trading_system/models
    key: ai-models-${{ matrix.target }}-${{ steps.date.outputs.date }}
    restore-keys: |
      ai-models-${{ matrix.target }}-

- name: Run prediction pipeline for ${{ matrix.target }}
  id: run
  env:
    ...
    SKIP_TRAINING: 'True'
```
- **Issue 1.4 (Hardcoded `SKIP_TRAINING: 'True'`)**:
  - Line 94 statically sets `SKIP_TRAINING: 'True'`.
  - If a model cache miss occurs (e.g. `steps.models-cache.outputs.cache-hit != 'true'`), `run_pipeline.py` is invoked with `SKIP_TRAINING: 'True'`.
  - Missing model files will cause predictions to fall back to `0.0` or trigger warnings rather than automatically initiating retraining as required by project criteria.
  - **Recommended Fix**: Compute `SKIP_TRAINING` dynamically:
    ```yaml
    SKIP_TRAINING: ${{ steps.models-cache.outputs.cache-hit == 'true' && 'True' || 'False' }}
    ```

#### Line Numbers & Code Snippet: Artifact Merging & GitHub Release (Lines 191-302)
```yaml
merge-and-release:
  runs-on: ubuntu-latest
  needs: run-pipeline
  if: always()
  permissions:
    contents: write
  steps:
    - uses: actions/checkout@v4
    ...
    - name: Guard - require at least one successful market
      run: |
        FOUND=0
        for m in SP500 NASDAQ RUSSELL2000 KOSPI KOSDAQ; do
          if ls trading_system/result_${m}/*.txt >/dev/null 2>&1; then FOUND=1; break; fi
        done
        if [ "$FOUND" != "1" ]; then
          echo "::error::All market pipelines failed - no prediction files. Skipping release & deploy."
          exit 1
        fi

    - name: Merge and reconstruct outputs
      run: |
        mkdir -p trading_system/result
        cp trading_system/result_SP500/*_SP500.txt trading_system/result/ 2>/dev/null || true
        ...
        python3 trading_system/merge_predictions.py
```
- **Evaluation 1.5 (Artifact & Release Architecture)**:
  - `run-pipeline` matrix steps copy generated prediction files into `result_split/${f}_${matrix.target}.txt` and upload artifacts `result-${matrix.target}`.
  - `merge-and-release` uses `if: always()`, downloads all matrix artifacts with `continue-on-error: true`, and verifies via the `Guard` step that at least one market succeeded.
  - `merge_predictions.py` is executed using system Python 3 (standard library only: `json`, `re`, `datetime`, `pathlib`), cleanly avoiding external dependency requirements.
  - GitHub Release creation uses `gh release create "v${date}"` and `gh release upload --clobber`.
  - Telegram failure notifications (`Notify Telegram on Failure`) safely verify `[ -n "$TOKEN" ] && [ -n "$CHAT" ]` before issuing HTTP requests via `curl`, preventing step failures when secrets are unconfigured.

#### Line Numbers & Code Snippet: GitHub Pages Deployment (Lines 303-364)
```yaml
deploy-pages:
  runs-on: ubuntu-latest
  needs: merge-and-release
  if: needs.merge-and-release.result == 'success'
  permissions:
    pages: write
    id-token: write
    contents: read
  environment:
    name: github-pages
    url: ${{ steps.deployment.outputs.page_url }}
  steps:
    - uses: actions/checkout@v4
    - name: Download merged results artifact
      uses: actions/download-artifact@v4
      with:
        name: merged-results
        path: trading_system/result
    - name: Verify merged results present (abort stale deploys)
      run: |
        if ! ls trading_system/result/*.txt >/dev/null 2>&1; then
          echo "::error::Merged result files missing - refusing to deploy a stale/fabricated dashboard."
          exit 1
        fi
    ...
    - name: Generate HTML dashboard
      run: |
        uv python install 3.12
        uv venv --python 3.12 .venv
        uv pip sync trading_system/requirements.lock
        .venv/bin/python trading_system/generate_report.py \
          --result-dir trading_system/result \
          --out gh-pages/index.html
    - name: Setup Pages
      uses: actions/configure-pages@v5
    - name: Upload Pages artifact
      uses: actions/upload-pages-artifact@v3
      with:
        path: gh-pages/
    - name: Deploy to GitHub Pages
      id: deployment
      uses: actions/deploy-pages@v4
```
- **Evaluation 1.6 (GitHub Pages Deployment)**:
  - GHA native deployment (`actions/configure-pages@v5`, `actions/upload-pages-artifact@v3`, `actions/deploy-pages@v4`) is properly configured with `permissions: pages: write, id-token: write`.
  - Line 325 verifies that merged prediction files are present before generating HTML, aborting execution to prevent deploying stale or empty dashboards if prediction generation failed.

---

### 2. Model Training Pipeline Workflow (`.github/workflows/training.yml`)

#### Line Numbers & Code Snippet: Matrix Model Caching & Shared DB Cache Race (Lines 43-68)
```yaml
- name: Cache stock_prices.db (Restore and Save)
  uses: actions/cache@v4
  id: db-cache
  with:
    path: trading_system/stock_prices.db
    key: stock-prices-db-${{ steps.date.outputs.date }}
    restore-keys: |
      stock-prices-db-

- name: Cache AI models (Save after training)
  uses: actions/cache@v4
  id: models-cache
  with:
    path: trading_system/models
    key: ai-models-${{ matrix.target }}-${{ steps.date.outputs.date }}
```
- **Issue 2.1 (Shared DB Cache Collision in Training Matrix)**:
  - Like `pipeline.yml`, `training.yml` runs 5 matrix targets concurrently and uses `actions/cache@v4` (restore AND save) for `stock_prices.db` and `market_indicators.db`.
  - Parallel runners collide on post-step cache upload for `stock-prices-db-${date}`.
  - **Recommended Fix**: Use `actions/cache/restore@v4` for database files in `training.yml`.
- **Evaluation 2.2 (Target-Scoped Model Cache Key)**:
  - Model caching uses target-scoped keys (`key: ai-models-${{ matrix.target }}-${{ steps.date.outputs.date }}`).
  - Each market target (`SP500`, `KOSPI`, etc.) saves its trained model artifacts under a separate key.
  - `pipeline.yml` matches this key structure on restore (`key: ai-models-${{ matrix.target }}-${{ steps.date.outputs.date }}` with restore key `ai-models-${{ matrix.target }}-`).

---

### 3. Preseed Database Cache Workflow (`.github/workflows/preseed.yml`)

#### Line Numbers & Code Snippet: Unread Model Cache Upload (Lines 57-70)
```yaml
- name: Cache AI models
  uses: actions/cache@v4
  id: models-cache
  with:
    path: trading_system/models
    key: ai-models-preseed-${{ steps.date.outputs.date }}
    restore-keys: |
      ai-models-KOSPI-
      ai-models-KOSDAQ-
      ai-models-SP500-
      ai-models-NASDAQ-
      ai-models-RUSSELL2000-
      ai-models-
```
- **Issue 3.1 (Unread Preseed Model Cache Key)**:
  - `preseed.yml` saves model directory under key `ai-models-preseed-${date}`.
  - Neither `pipeline.yml` nor `training.yml` uses `ai-models-preseed-` as a restore key (they restore `ai-models-${matrix.target}-`).
  - As a result, `ai-models-preseed-${date}` occupies cache storage without ever being restored by downstream workflows.
  - **Recommended Fix**: Change step in `preseed.yml` to `actions/cache/restore@v4` or remove model caching from `preseed.yml`.

---

### 4. Testing & Security Audit Workflow (`.github/workflows/pytest.yml`)

#### Line Numbers & Code Snippet: Setup & Steps (Lines 11-73)
```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.12"]
    steps:
    - name: Checkout repository
      uses: actions/checkout@v4
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v5
      with:
        python-version: ${{ matrix.python-version }}
        cache: 'pip'
        cache-dependency-path: trading_system/requirements.lock
```
- **Issue 4.1 (Tooling Discrepancy)**:
  - `pytest.yml` uses `actions/setup-python@v5` + `pip install`, whereas all other 5 workflows use `astral-sh/setup-uv@v5` + `uv pip sync`.
  - **Recommended Fix**: Standardize `pytest.yml` to use `astral-sh/setup-uv@v5` for faster, fully reproducible dependency installation.
- **Issue 4.2 (Missing Concurrency Group)**:
  - `pytest.yml` lacks a `concurrency:` block. Concurrent commits trigger redundant, overlapping test runs.
  - **Recommended Fix**: Add `concurrency: group: pytest-${{ github.ref }}, cancel-in-progress: true`.

---

### 5. Realtime Monitor Workflow (`.github/workflows/realtime_monitor.yml`)

#### Line Numbers & Code Snippet: Cache Key Immutability Failure (Lines 41-48, 88-94)
```yaml
- name: Restore realtime state cache
  uses: actions/cache/restore@v4
  id: state-cache
  with:
    path: trading_system/realtime_state.db
    key: realtime-state-${{ steps.date.outputs.date }}
    restore-keys: |
      realtime-state-

...

- name: Save realtime state cache
  if: always()
  uses: actions/cache/save@v4
  with:
    path: trading_system/realtime_state.db
    key: realtime-state-${{ steps.date.outputs.date }}
```
- **Issue 5.1 (Intraday State Cache Immutability Bug)**:
  - `realtime_monitor.yml` runs every 15 minutes (28 runs per day during KRX trading hours: 09:00 to 15:45 KST).
  - The first run at 09:00 KST creates cache key `realtime-state-YYYY-MM-DD`.
  - GitHub Actions cache keys are **immutable**. Once created, any subsequent upload attempt with the exact same key string fails.
  - At 09:15, 09:30, 09:45..., `actions/cache/save@v4` attempts to save to `realtime-state-YYYY-MM-DD` and is rejected by the GitHub API.
  - All stop-loss/take-profit alerts recorded in `realtime_state.db` during intermediate runs are discarded.
  - Subsequent runs restore the 09:00 KST baseline cache, leading to duplicate notification alerts.
  - **Recommended Fix**: Append `github.run_id` or `github.run_number` to the save key:
    ```yaml
    # Save step:
    key: realtime-state-${{ steps.date.outputs.date }}-${{ github.run_id }}

    # Restore step:
    key: realtime-state-${{ steps.date.outputs.date }}-${{ github.run_id }}
    restore-keys: |
      realtime-state-${{ steps.date.outputs.date }}-
      realtime-state-
    ```
    This ensures that each 15-minute execution restores the state saved by the immediately preceding run.

---

### 6. Weekly HPO Workflow (`.github/workflows/weekly_hpo.yml`)

#### Line Numbers & Code Snippet: HPO Execution (Lines 59-74)
```yaml
- name: Run Optuna Hyperparameter Optimization
  env:
    INFERENCE_TARGET: ${{ matrix.target }}
    N_TRIALS: '30'
    LOG_LEVEL: INFO
    FORCE_CPU: '1'
  run: |
    .venv/bin/python trading_system/scripts/tune_models.py

- name: Upload Tuned Parameters Artifact
  uses: actions/upload-artifact@v4
  with:
    name: tuned-params-${{ matrix.target }}
    path: trading_system/models/*.json
    retention-days: 7
```
- **Issue 6.1 (`N_TRIALS` Environment Variable Ignored)**:
  - `weekly_hpo.yml` sets `N_TRIALS: '30'`.
  - `trading_system/scripts/tune_models.py` line 304 executes `tune_hyperparameters(n_trials=5)` without reading `os.environ.get('N_TRIALS')`.
  - The workflow runs only 5 Optuna trials instead of the intended 30 trials.
  - **Recommended Fix**: Update `tune_models.py` entry point:
    ```python
    n_trials = int(os.environ.get("N_TRIALS", "5"))
    tune_hyperparameters(n_trials=n_trials)
    ```
- **Issue 6.2 (Un-suffixed Parameters JSON Output)**:
  - `tune_models.py` writes to `trading_system/models/tuned_params.json` without target prefixing.
  - When uploaded as `tuned-params-${matrix.target}`, the artifact contains generic `tuned_params.json`.
  - **Recommended Fix**: Output target-specific files `tuned_params_${target}.json` or merge tuned parameter files before training.

---

## Actionable Recommendations & Fix Plan

| Workflow | Finding / Bug | Severity | Recommended Fix |
|----------|---------------|----------|-----------------|
| `pipeline.yml` & `training.yml` | Parallel Matrix DB Cache Save Collision | **High** | Change `actions/cache@v4` to `actions/cache/restore@v4` for `stock_prices.db` and `market_indicators.db` in matrix jobs. |
| `realtime_monitor.yml` | Intraday Cache Immutability State Loss | **High** | Append `${{ github.run_id }}` to cache save key and use `realtime-state-${date}-` in restore-keys. |
| `pipeline.yml` | US Market Cron Timing Misalignment | **Medium** | Adjust cron from `30 11 * * 1-5` (11:30 UTC) to `0 22 * * 1-5` (22:00 UTC) so both KRX and US sessions are closed. |
| `pipeline.yml` | Hardcoded `SKIP_TRAINING: 'True'` | **Medium** | Set `SKIP_TRAINING` dynamically based on model cache hit status: `${{ steps.models-cache.outputs.cache-hit == 'true' && 'True' \|\| 'False' }}`. |
| `weekly_hpo.yml` | `N_TRIALS: '30'` Ignored in `tune_models.py` | **Medium** | Update `tune_models.py` main block to read `os.environ.get("N_TRIALS", 5)`. |
| `preseed.yml` | Model Cache Key `ai-models-preseed-` Unread | **Low** | Use `actions/cache/restore@v4` or remove model cache step from `preseed.yml`. |
| `pytest.yml` | Tooling Discrepancy & Missing Concurrency | **Low** | Switch to `astral-sh/setup-uv@v5` and add `concurrency` block. |

---
*Report generated by `teamwork_preview_explorer_m2_2` for Milestone 2 Audit.*
