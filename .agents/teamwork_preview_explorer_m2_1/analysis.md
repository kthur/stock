# End-to-End Pipeline Execution & Architecture Robustness Audit

**Module**: `trading_system/run_pipeline.py`  
**Milestone**: Milestone 2 (Software Architecture & Pipeline Robustness Audit)  
**Date**: 2026-08-06  
**Auditor**: teamwork_preview_explorer_m2_1  

---

## 1. Executive Summary

This report presents an end-to-end audit of `trading_system/run_pipeline.py` and supporting modules (`src/data_layer/indicator_storage.py`, `src/ai/prediction_model.py`, `src/ai/ensemble_scorer.py`, `src/persistence/database.py`). 

The audit focused on four major areas:
1. **Exception Safety, Step Isolation, and Failure Recovery** across the 12 pipeline steps.
2. **Graceful Degradation** when market data providers (yfinance, FinanceDataReader, Open DART) fail, delay, or return empty DataFrames.
3. **Multi-Market Execution Handling** across 6 target markets (KOSPI, KOSDAQ, KONEX, SP500, NASDAQ, RUSSELL2000).
4. **Output File Generation and Pipeline State Tracking / Resumability**.

Overall, the pipeline exhibits strong data resiliency (3-tier data architecture, macro data sanitization gate, parallel symbol/market execution, and partial success recovery on exit). However, critical exception handling gaps exist in specific pipeline steps where unhandled exceptions will crash the entire pipeline before subsequent independent strategies or report generators can run.

---

## 2. Audit Findings by Pipeline Step (12 Steps)

### Pipeline Step Overview & Exception Safety Matrix

| Step | Description | Code Location | Exception Safety & Isolation Status | Issues / Vulnerabilities |
|------|-------------|---------------|--------------------------------------|--------------------------|
| **Step 1** | Config Loading & Validation | `run_pipeline.py:781-784` | Top-level unhandled | Exception in `cfg.validate()` halts pipeline. (Acceptable for config validation) |
| **Step 2** | Global Market Indicators Fetch | `run_pipeline.py:794-797` | **Lacks local try/except** | Failure in `market_client.get_summary()` halts pipeline before offline cache check. |
| **Step 3** | Global Market Indicators Store | `run_pipeline.py:799-804` | Logged via `pipeline_stage`, re-raises | DB write lock error halts pipeline. |
| **Step 4** | Stock Universe Load & Sync | `run_pipeline.py:806-816` | **Lacks local try/except** | `storage.update_stock_universe()` network error halts startup. |
| **Step 5** | Indicator History Fetch (Train/Infer) | `run_pipeline.py:829-874` | **Isolated & Safe** | `fetch_indicator_history` uses 3-tier fallback (yfinance -> FDR -> SQLite DB). Returns empty/partial DF safely. |
| **Step 6** | Training Data Preparation | `run_pipeline.py:875-1017` | **Isolated & Safe** | ThreadPoolExecutor per symbol with 30s timeout; background thread for fundamentals; batch fundamental merge handles errors per symbol. |
| **Step 7** | Model Training (Regression, Surge, Lead-Lag, VCP ML, Calibration) | `run_pipeline.py:1018-1114` | **Partially Isolated** | Regression (7a) & Surge (7b) isolated per market. **Lead-Lag (7c) lacks try/except** and halts training if correlation fails. Calibrator (7e) is wrapped in try/except. |
| **Step 8** | Inference Fundamentals Fetch | `run_pipeline.py:1115-1157` | **Isolated & Safe** | Non-blocking background thread `_bg_fundamentals` logs warning on error. |
| **Step 9** | Inference Price Data Fetch & Merge | `run_pipeline.py:1158-1241` | **Isolated & Safe** | Parallel symbol fetch with 30s timeout; `<200d` symbol purging; parallel fundamental merge pops failed symbols cleanly. |
| **Step 10** | Prediction & 18 Strategy Executions | `run_pipeline.py:1243-2427` | **Partially Isolated** | Strategies 7,9,10-18 wrapped in try/except. **Main ML Infer (`predict_all`), Lead-Lag infer, and VCP ML infer lack try/except**. |
| **Step 11** | Ensemble Scoring, Portfolio Alloc, Output File Generation | `run_pipeline.py:2430-3085` | **Partially Isolated** | **Market Regime GMM, `calculate_ensemble_score`, main output write, and HRP `allocator.allocate` lack try/except**. Coverage/Attribution/OMS/HTML reports are wrapped in try/except. |
| **Step 12** | Post-pipeline Verification & State Tracking | `run_pipeline.py:3097-3144` | **Isolated & Safe** | Checks file existence and non-zero size. Top-level try/except recovers exit code 0 if output files were created. |

---

## 3. Detailed Findings & Recommended Patch Code

### Finding 1: Unhandled Global Indicators & Universe Sync at Startup
* **File**: `trading_system/run_pipeline.py`
* **Lines**: 794-816
* **Issue**:
  ```python
  # 2. Fetch current global market indicators
  logger.info("Fetching global market indicators...")
  market_client = GlobalMarketClient()
  market_summary = market_client.get_summary()  # <--- Unhandled exception if network fails!

  # 3. Store indicators
  date_str = datetime.now().strftime('%Y-%m-%d')
  storage = MarketIndicatorStorage(db_path=cfg.db_path)
  with storage.pipeline_stage("global_indicators"):
      storage.save_indicators(market_summary, date_str)

  # 4. Update stock universe if needed
  universe = storage.get_universe()
  if universe.empty:
      logger.info("Universe is empty. Syncing stock universe...")
      storage.update_stock_universe()  # <--- Unhandled exception if FDR fails!
      universe = storage.get_universe()
  ```
* **Impact**: If network connection is offline or intermittent at startup, `market_client.get_summary()` or `storage.update_stock_universe()` throws an uncaught exception, immediately crashing the pipeline before it can use cached DB data.
* **Proposed Patch**:
  ```python
  # 2. Fetch current global market indicators with offline fallback
  logger.info("Fetching global market indicators...")
  market_summary = {}
  try:
      market_client = GlobalMarketClient()
      market_summary = market_client.get_summary()
  except Exception as e:
      logger.warning(f"Failed to fetch real-time global indicators: {e}. Falling back to cached database indicators.")

  date_str = datetime.now().strftime('%Y-%m-%d')
  storage = MarketIndicatorStorage(db_path=cfg.db_path)
  if market_summary:
      try:
          with storage.pipeline_stage("global_indicators"):
              storage.save_indicators(market_summary, date_str)
          logger.info("Saved market indicators to database.")
      except Exception as e:
          logger.warning(f"Failed to save market indicators: {e}")

  # 4. Update stock universe if needed with offline fallback
  universe = storage.get_universe()
  if universe.empty:
      logger.info("Universe is empty. Syncing stock universe...")
      try:
          storage.update_stock_universe()
          universe = storage.get_universe()
      except Exception as e:
          logger.error(f"Failed to sync stock universe: {e}")
  ```

---

### Finding 2: Unhandled Exception in Lead-Lag Matrix Training (Step 7c)
* **File**: `trading_system/run_pipeline.py`
* **Lines**: 1074-1076
* **Issue**:
  ```python
  # 7c. Compute lead-lag correlation matrix (which stocks follow which)
  with storage.pipeline_stage("train_lead_lag_vcp"):
      if not df_train.empty and len(df_train) > 1000:
          model.compute_lead_lag(df_train, indicator_df=indicator_train, symbol_to_market=symbol_market)
  ```
* **Impact**: `model.compute_lead_lag` is called inside `storage.pipeline_stage("train_lead_lag_vcp")`. If pandas indexing or correlation calculation fails, `pipeline_stage` catches the exception, marks the stage as FAILED in SQLite, and re-raises the exception. Because there is no local `try...except`, the entire pipeline training phase crashes.
* **Proposed Patch**:
  ```python
  with storage.pipeline_stage("train_lead_lag_vcp"):
      if not df_train.empty and len(df_train) > 1000:
          try:
              model.compute_lead_lag(df_train, indicator_df=indicator_train, symbol_to_market=symbol_market)
          except Exception as _ll_e:
              logger.warning(f"Lead-lag correlation matrix training failed: {_ll_e}")
  ```

---

### Finding 3: Unhandled ML Inference Calls (`model.predict_all`, `model.predict_lead_lag`, `vcp_ml.predict`)
* **File**: `trading_system/run_pipeline.py`
* **Lines**: 1245-1250, 1337, 1749
* **Issue**:
  - Line 1246: `res_df, surge_df = model.predict_all(infer_data_dict, indicator_infer, symbol_to_market_lower, storage=storage, fundamentals_cache=infer_fund_cache)`
  - Line 1337: `lead_lag_df = model.predict_lead_lag(infer_data_dict, indicator_df=indicator_infer)`
  - Line 1749: `vcp_ml_df = vcp_ml.predict(infer_data_dict, indicator_infer, universe)`
* **Impact**: If any of these ML prediction methods raises an exception (e.g. missing column in single market run, unexpected dtype mismatch, missing model file), the exception propagates and halts execution before rule-based and quant factor strategies (VCP, Stat-Arb, Sector Rotation, RIM, Event-Driven, MQ, IV Skew, Order Flow, Reversal, ARM, CARD, LATR, Inst-Foreign) can run.
* **Proposed Patch**:
  Wrap each ML inference call in a `try...except` block that logs a warning and returns an empty `pd.DataFrame()` on failure:
  ```python
  with storage.pipeline_stage("inference_regression_surge"):
      try:
          res_df, surge_df = model.predict_all(infer_data_dict, indicator_infer, symbol_to_market_lower, storage=storage, fundamentals_cache=infer_fund_cache)
      except Exception as _pred_e:
          logger.error(f"Main regression/surge inference failed: {_pred_e}")
          res_df, surge_df = pd.DataFrame(), pd.DataFrame()

  try:
      lead_lag_df = model.predict_lead_lag(infer_data_dict, indicator_df=indicator_infer)
  except Exception as _ll_infer_e:
      logger.warning(f"Lead-lag inference failed: {_ll_infer_e}")
      lead_lag_df = pd.DataFrame()

  try:
      if vcp_ml is not None:
          vcp_ml_df = vcp_ml.predict(infer_data_dict, indicator_infer, universe)
  except Exception as _vcp_ml_e:
      logger.warning(f"VCP ML inference failed: {_vcp_ml_e}")
      vcp_ml_df = pd.DataFrame()
  ```

---

### Finding 4: Unhandled GMM Market Regime Detection & Ensemble Scoring
* **File**: `trading_system/run_pipeline.py`
* **Lines**: 1426-1440, 2430-2451
* **Issue**:
  - Lines 1431-1439: `regime_detector.train(...)` and `regime_detector.predict_2d_regime(...)` run without exception guards.
  - Lines 2430-2451: `ensemble_df = scorer.calculate_ensemble_score(...)` runs without exception guards.
* **Impact**: If GMM clustering encounters singular matrices or NaN inputs, or if ensemble score computation throws an unexpected KeyError/ValueError, the entire pipeline crashes before creating `ensemble_predictions.txt` and report files.
* **Proposed Patch**:
  ```python
  # 11b. Market Regime Detection with Fallback
  logger.info("Running GMM Market Regime Detection...")
  current_2d_regime = 'SIDEWAYS_LOW_VOL'
  current_regime_label = 'SIDEWAYS'
  current_regime = 1
  try:
      regime_detector = MarketRegimeDetector()
      if not indicator_train.empty:
          regime_detector.train(indicator_train)
      elif not indicator_infer.empty:
          regime_detector.train(indicator_infer)

      current_regime_label = regime_detector.predict_regime_label(indicator_infer)
      current_regime = regime_detector.predict_regime(indicator_infer)
      regime_2d_info = regime_detector.predict_2d_regime(indicator_infer)
      current_2d_regime = regime_2d_info['combo_label']
  except Exception as _reg_e:
      logger.warning(f"Market regime detection failed: {_reg_e}. Using fallback: {current_2d_regime}")

  # 11d. Ensemble Scoring with Fallback
  try:
      ensemble_df = scorer.calculate_ensemble_score(
          regime=current_2d_regime,
          regression_df=res_df,
          surge_df=surge_df,
          lead_lag_df=lead_lag_df,
          vcp_rule_df=vcp_results,
          vcp_ml_df=vcp_ml_df,
          stat_arb_df=stat_arb_df,
          sector_df=sector_df,
          rim_df=rim_df,
          event_df=event_df,
          mq_df=mq_df,
          iv_skew_df=iv_skew_df,
          order_flow_df=order_flow_df,
          reversal_df=reversal_df,
          arm_df=arm_df,
          card_df=card_df,
          latr_df=latr_df,
          inst_foreign_sector_df=inst_foreign_sector_df,
          rolling_sharpes=rolling_sharpes,
          target_horizon=20
      )
  except Exception as _ens_e:
      logger.error(f"Ensemble scoring failed: {_ens_e}")
      ensemble_df = pd.DataFrame()
  ```

---

### Finding 5: Pipeline State Tracking vs Resumability Gap
* **File**: `trading_system/src/data_layer/indicator_storage.py` (lines 207-256) & `trading_system/run_pipeline.py`
* **Issue**: `MarketIndicatorStorage.pipeline_stage(stage)` records stage executions into SQLite `pipeline_runs` table (`stage`, `start_time`, `end_time`, `status`, `error_message`). However, `run_pipeline.py` does not check `pipeline_runs` upon startup to skip previously completed stages if a pipeline run is restarted after a failure.
* **Impact**: On failure recovery, the pipeline must re-run all previous steps from scratch (fetching price data, retraining models) unless manual CLI flags (`--skip-training`, `--skip-inference`) are supplied.
* **Recommended Feature Proposal**: Add a check in `pipeline_stage` or `run_pipeline.py` to check `storage.is_stage_completed(stage_name, date_str)` when `--resume` flag is passed.

---

## 4. Graceful Degradation & Data Resilience Audit Findings

1. **3-Tier Fallback Data Handler (`fetch_data_fdr` & `fetch_indicator_history`)**:
   - Tier 1: `yfinance` download (with Tenacity exponential backoff retries).
   - Tier 2: `FinanceDataReader` download.
   - Tier 3: Local SQLite DB offline cache (`stock_prices.db` and `market_indicators.db`).
   - If network fails and DB cache is available, the system proceeds seamlessly with cached data and logs an offline warning.

2. **Binary Split Download Recovery (`_download_with_recovery`)**:
   - Batch downloads of 100 tickers use a recursive binary split to isolate delisted, suspended, or corrupt tickers without failing the entire batch download.

3. **Data Quality Gate & Macro Integrity Sanitization**:
   - `DataValidator.validate_price_data`: Rejects tickers with >50% NaN, non-positive close prices, or >90% zero volume (halted stocks).
   - Macro Data Sanitization (`_plausible_bounds` lines 2585-2617): Detects out-of-bounds or shared-series DB cache contamination (e.g. VIX, WTI, Gold, US10Y taking identical values) and substitutes safe, conservative defaults (`vix=18.5`, `usdkrw=1380.0`, `us10y=4.25%`, `wti=$75.0`, `gold=$220.0`).

4. **Delisted / Halted KRX Stock Filter (`_get_excluded_krx_symbols`)**:
   - Purges KRX administrative stocks (관리종목) and halted stocks (Volume=0 during active market hours) before running inference.

---

## 5. Multi-Market Execution & Output Verification Findings

1. **Parallel Market Execution & Model Isolation**:
   - Model training for `SP500`, `NASDAQ`, `RUSSELL2000`, `KOSPI`, `KOSDAQ` runs in parallel threads. Failure in one market is captured in `_train_failures` without interrupting training for other markets.
   - `--target MARKET` CLI flag enables single-market execution for GitHub Actions matrix jobs.

2. **Output File Generation & Matrix Merge Support**:
   - Generates 23+ prediction and report files in `trading_system/result/`.
   - Produces per-market suffix files (e.g. `ensemble_predictions_KOSPI.txt`, `pipeline_result_SP500.txt`) for all 18 strategies so matrix GHA jobs can run targets independently and merge outputs.

3. **Post-Pipeline Verification Gate**:
   - Validates existence and non-zero byte size for 13 core output files.
   - Parses `pipeline_result.txt` via regex to confirm expected returns are not stuck at `0.0`.
   - Top-level exception block (`lines 3230-3261`) checks if output files exist even after an unhandled error, logging a partial success warning and exiting with code `0`.

---

## 6. Actionable Recommendations

1. **Apply Exception Isolation Patches**: Wrap Steps 2, 4, 7c, 10a, 10d, 10e, 11b, 11d, and Portfolio Allocation in local `try...except` blocks as specified in Section 3.
2. **Implement Resumability Checkpoint Engine**: Enhance `pipeline_stage()` in `indicator_storage.py` to allow skipping already-completed stages when a `--resume` flag is passed.
3. **Add Validation Unit Tests**: Add unit tests in `tests/test_run_pipeline_robustness.py` asserting that pipeline steps degrade gracefully when external APIs return empty data or throw network exceptions.
