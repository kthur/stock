# Handoff Report — Software Architecture & Pipeline Robustness Audit (GitHub Actions & Automation)

**Agent**: `teamwork_preview_explorer_m2_2`  
**Milestone**: Milestone 2 (Software Architecture & Pipeline Robustness Audit)  
**Working Directory**: `d:\Finance\code\stock\.agents\teamwork_preview_explorer_m2_2`  
**Handoff Type**: Hard Handoff (Task Complete)

---

## 1. Observation

### Observation 1: Parallel Matrix Cache Save Race Condition in `pipeline.yml` & `training.yml`
- **File**: `.github/workflows/pipeline.yml` (lines 46-65) & `.github/workflows/training.yml` (lines 43-60)
- **Code Quote**:
  ```yaml
  - name: Cache stock_prices.db
    uses: actions/cache@v4
    id: db-cache
    with:
      path: trading_system/stock_prices.db
      key: stock-prices-db-${{ steps.date.outputs.date }}
      restore-keys: |
        stock-prices-db-
  ```
- **Context**: The job `run-pipeline` runs as a matrix across 5 targets (`SP500`, `NASDAQ`, `RUSSELL2000`, `KOSPI`, `KOSDAQ`). `actions/cache@v4` attempts post-job cache save on all 5 parallel matrix runners for key `stock-prices-db-${date}`.

### Observation 2: Intraday Cache Immutability State Loss in `realtime_monitor.yml`
- **File**: `.github/workflows/realtime_monitor.yml` (lines 41-48, 88-94)
- **Code Quote**:
  ```yaml
  - name: Save realtime state cache
    if: always()
    uses: actions/cache/save@v4
    with:
      path: trading_system/realtime_state.db
      key: realtime-state-${{ steps.date.outputs.date }}
  ```
- **Context**: `realtime_monitor.yml` runs every 15 minutes during trading hours (28 times/day). GitHub Actions cache keys are immutable. The key `realtime-state-${date}` is saved by the first run at 09:00 KST, causing all 27 subsequent runs that day to fail post-step cache upload with key collision warnings.

### Observation 3: Cron Schedule Misalignment for US Markets in `pipeline.yml`
- **File**: `.github/workflows/pipeline.yml` (lines 6-7)
- **Code Quote**:
  ```yaml
  schedule:
    - cron: '30 11 * * 1-5'
  ```
- **Context**: 11:30 UTC is 20:30 KST. US equity markets open at 13:30/14:30 UTC (22:30/23:30 KST). Running the pipeline at 11:30 UTC means US target predictions (`SP500`, `NASDAQ`, `RUSSELL2000`) execute before today's US trading session begins, fetching price data from the previous trading day.

### Observation 4: Static `SKIP_TRAINING: 'True'` in `pipeline.yml`
- **File**: `.github/workflows/pipeline.yml` (line 94)
- **Code Quote**:
  ```yaml
  SKIP_TRAINING: 'True'
  ```
- **Context**: Line 94 statically hardcodes `SKIP_TRAINING: 'True'`. If AI model cache restore fails (`cache-hit != 'true'`), `run_pipeline.py` does not automatically retrain missing models.

### Observation 5: Hardcoded `n_trials=5` in `tune_models.py` Ignoring `N_TRIALS` Env Var
- **File**: `.github/workflows/weekly_hpo.yml` (line 62) & `trading_system/scripts/tune_models.py` (line 304)
- **Code Quote**:
  - `weekly_hpo.yml`: `N_TRIALS: '30'`
  - `tune_models.py`: `tune_hyperparameters(n_trials=5)`
- **Context**: `weekly_hpo.yml` specifies `N_TRIALS: '30'`, but `tune_models.py` hardcodes `5` when executed as `__main__`.

---

## 2. Logic Chain

1. **Step 1 (Parallel Matrix Cache Collision)**:
   - *From Observation 1*: In `pipeline.yml` and `training.yml`, 5 parallel matrix runners execute simultaneously. Each runner restores `stock-prices-db-${date}`, fetches new market prices, updates local `stock_prices.db`, and executes post-job `actions/cache@v4` save.
   - *Deduction*: Because GHA cache keys are immutable per exact string, whichever matrix runner finishes first (e.g. `SP500`) saves `stock-prices-db-${date}`. The remaining 4 runners fail post-step cache upload. Consequently, price updates fetched by the other 4 matrix targets are dropped and never cached.
   - *Conclusion*: Matrix workflow steps MUST use `actions/cache/restore@v4` instead of `actions/cache@v4` for shared database files.

2. **Step 2 (Intraday Realtime Monitor State Loss)**:
   - *From Observation 2*: `realtime_monitor.yml` runs every 15 minutes (28 runs/day) and saves state to key `realtime-state-${date}`.
   - *Deduction*: The first run at 09:00 KST creates `realtime-state-${date}`. Subsequent runs at 09:15, 09:30, ... fail to save cache because the key already exists. Each subsequent run restores the stale 09:00 KST cache baseline, losing all recorded stop-loss/take-profit triggers and risking duplicate alerts.
   - *Conclusion*: Save key MUST include `${{ github.run_id }}` and restore-keys MUST prefix match `realtime-state-${date}-`.

3. **Step 3 (Cron Schedule Misalignment)**:
   - *From Observation 3*: `pipeline.yml` cron is set to `30 11 * * 1-5` (11:30 UTC).
   - *Deduction*: 11:30 UTC is prior to US market opening (13:30/14:30 UTC). US stock data fetched at 11:30 UTC represents yesterday's close, rendering daily predictions for US markets out-of-date relative to post-market expectations.
   - *Conclusion*: Adjust cron to `0 22 * * 1-5` (22:00 UTC / 07:00 KST next morning) or `0 0 * * 2-6` (00:00 UTC) so all global markets (KRX and US) have closed.

4. **Step 4 (Model Cache Miss Fallback)**:
   - *From Observation 4*: `pipeline.yml` sets `SKIP_TRAINING: 'True'`.
   - *Deduction*: On model cache miss, models are missing from disk. With `SKIP_TRAINING: 'True'`, `run_pipeline.py` skips model training and outputs uncalibrated or zero return predictions.
   - *Conclusion*: `SKIP_TRAINING` should be conditionally set to `'True'` ONLY when model cache restore succeeds (`cache-hit == 'true'`).

5. **Step 5 (HPO Environment Parameter Bypass)**:
   - *From Observation 5*: `weekly_hpo.yml` sets `N_TRIALS: '30'`, but `tune_models.py` calls `tune_hyperparameters(n_trials=5)`.
   - *Deduction*: HPO terminates after 5 trials instead of exploring 30 trials, producing suboptimal hyperparameter configurations.
   - *Conclusion*: `tune_models.py` must read `os.environ.get("N_TRIALS", 5)`.

---

## 3. Caveats

- **No Workflow File Modifications Made**: Per the read-only investigation constraint, no modifications were made directly to `.github/workflows/` files or Python scripts.
- **Assumptions on Runner Concurrency**: GHA free/team tiers run matrix jobs in parallel up to default concurrency limits (5 parallel jobs for Linux runners). If matrix execution is serialized by runner quota limits, the DB cache race condition still occurs because the first completed target creates the cache key for that date.

---

## 4. Conclusion

The GitHub Actions workflows (`pipeline.yml`, `training.yml`, `preseed.yml`, `pytest.yml`, `realtime_monitor.yml`, `weekly_hpo.yml`) provide a functional CI/CD and automated daily prediction setup, but suffer from **two critical race/immutability bugs** (matrix shared DB cache overwrite & realtime state cache immutability state loss) and **two timing/parameter misalignments** (US market pre-market cron run & ignored HPO `N_TRIALS`).

Fixing these issues requires:
1. Updating matrix DB cache steps to `actions/cache/restore@v4` in `pipeline.yml` and `training.yml`.
2. Adding `${{ github.run_id }}` to the cache key in `realtime_monitor.yml`.
3. Updating cron timing in `pipeline.yml` to `0 22 * * 1-5` (22:00 UTC).
4. Dynamically evaluating `SKIP_TRAINING` based on `cache-hit`.
5. Enabling `os.environ.get("N_TRIALS")` in `tune_models.py`.

Full analysis details and code snippets are documented in `d:\Finance\code\stock\.agents\teamwork_preview_explorer_m2_2\analysis.md`.

---

## 5. Verification Method

To independently verify these findings:
1. **Matrix Cache Collision Verification**:
   - Inspect `.github/workflows/pipeline.yml` lines 46-65 and `.github/workflows/training.yml` lines 43-60 using `view_file`. Observe `uses: actions/cache@v4` with identical key `stock-prices-db-${{ steps.date.outputs.date }}` across all matrix targets.
2. **Realtime Monitor Immutability Verification**:
   - Inspect `.github/workflows/realtime_monitor.yml` lines 88-94. Observe `uses: actions/cache/save@v4` with static key `realtime-state-${{ steps.date.outputs.date }}` without run ID scoping.
3. **Cron Schedule Verification**:
   - Check line 7 of `.github/workflows/pipeline.yml` (`cron: '30 11 * * 1-5'`). Convert 11:30 UTC to EST/EDT and verify US market trading hours (09:30-16:00 EST).
4. **HPO Parameter Verification**:
   - Check line 62 of `.github/workflows/weekly_hpo.yml` (`N_TRIALS: '30'`) and line 304 of `trading_system/scripts/tune_models.py` (`tune_hyperparameters(n_trials=5)`).

---
*Report submitted by `teamwork_preview_explorer_m2_2` for Milestone 2 Audit.*
