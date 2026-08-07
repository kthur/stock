# Handoff Report — Milestone 2 (Pipeline Architecture & Robustness Audit)

**Agent**: teamwork_preview_explorer_m2_1  
**Working Directory**: `d:\Finance\code\stock\.agents\teamwork_preview_explorer_m2_1`  
**Date**: 2026-08-06  
**Handoff Type**: Hard (Task Complete)  

---

## 1. Observation

Direct observations from inspecting `trading_system/run_pipeline.py`, `src/data_layer/indicator_storage.py`, `src/ai/prediction_model.py`, `src/ai/ensemble_scorer.py`, and `src/persistence/database.py`:

1. **Step 2 & 4 Startup Exception Handling**:
   - `run_pipeline.py:794-797`: `market_client = GlobalMarketClient(); market_summary = market_client.get_summary()` is invoked at top level without a `try...except` block.
   - `run_pipeline.py:810`: `storage.update_stock_universe()` calls `fdr.StockListing()` without a `try...except` block.
   - Quotation (`run_pipeline.py:796-810`):
     ```python
     market_client = GlobalMarketClient()
     market_summary = market_client.get_summary()
     ...
     if universe.empty:
         storage.update_stock_universe()
     ```

2. **Step 7c Training Exception Safety Gap**:
   - `run_pipeline.py:1074-1076`:
     ```python
     with storage.pipeline_stage("train_lead_lag_vcp"):
         if not df_train.empty and len(df_train) > 1000:
             model.compute_lead_lag(df_train, indicator_df=indicator_train, symbol_to_market=symbol_market)
     ```
   - `model.compute_lead_lag` is called inside `pipeline_stage`. If an exception occurs, `pipeline_stage` logs `status='FAILED'` to SQLite `pipeline_runs` table and re-raises `exc`, crashing the entire training step without catching it locally.

3. **Step 10 Main ML Inference Exception Safety Gap**:
   - `run_pipeline.py:1245-1246`:
     ```python
     with storage.pipeline_stage("inference_regression_surge"):
         res_df, surge_df = model.predict_all(infer_data_dict, indicator_infer, symbol_to_market_lower, storage=storage, fundamentals_cache=infer_fund_cache)
     ```
   - `run_pipeline.py:1337`: `lead_lag_df = model.predict_lead_lag(infer_data_dict, indicator_df=indicator_infer)`
   - `run_pipeline.py:1749`: `vcp_ml_df = vcp_ml.predict(infer_data_dict, indicator_infer, universe)`
   - None of these three ML prediction invocations are wrapped in a local `try...except` block.

4. **Step 11 GMM Market Regime Detection & Ensemble Scoring Exception Safety Gap**:
   - `run_pipeline.py:1431-1439`: `regime_detector.train(...)` and `regime_detector.predict_2d_regime(...)` run without `try...except`.
   - `run_pipeline.py:2430`: `ensemble_df = scorer.calculate_ensemble_score(...)` runs without `try...except`.
   - `run_pipeline.py:3045`: `alloc_df = allocator.allocate(...)` runs without `try...except`.

5. **3-Tier Data Architecture & Graceful Degradation**:
   - `run_pipeline.py:177-200` (`_fetch_data_fdr_network`), `lines 382-443` (`fetch_data_fdr`), `lines 521-600` (`fetch_indicator_history`): Implements 3 tiers: Tier 1 (`yfinance`) -> Tier 2 (`FinanceDataReader`) -> Tier 3 (`StockPriceDB` / `MarketIndicatorStorage` SQLite WAL cache).
   - `run_pipeline.py:310-346` (`_download_with_recovery`): Binary split download algorithm isolates bad/delisted tickers during batch fetching.
   - `run_pipeline.py:2561-2617`: Macro data distinctness check (`detect_shared_series_corruption`) and plausible bounds gate (`_plausible_bounds`) substitutes safe defaults (`vix=18.5`, `usdkrw=1380.0`, `us10y=4.25%`, `wti=$75.0`, `gold=$220.0`) when indicator inputs are corrupted or missing.
   - `run_pipeline.py:735-776`: `_get_excluded_krx_symbols` purges admin and halted stocks.

6. **Multi-Market Failure Isolation & Output File Generation**:
   - `run_pipeline.py:1038-1071`: Model training for `SP500`, `NASDAQ`, `RUSSELL2000`, `KOSPI`, `KOSDAQ` runs in parallel threads; individual market training failures are logged to `_train_failures` without interrupting other markets.
   - `run_pipeline.py:3160-3201`: CLI parameter `--target MARKET` sets `INFERENCE_TARGET` for single-market matrix GHA runs.
   - `run_pipeline.py:1405-3085`: Generates 23+ prediction text files, per-market suffix files (`*_KOSPI.txt`, etc.), CSV/JSONL files, coverage reports, portfolio allocation plans, and `gh-pages/index.html`.

7. **Pipeline State Tracking & Resumability Gap**:
   - `src/data_layer/indicator_storage.py:207-256`: `pipeline_stage(stage)` records execution telemetry into `pipeline_runs` table (`stage`, `start_time`, `end_time`, `status`, `error_message`).
   - `run_pipeline.py` currently uses `pipeline_stage()` for logging only, and does not inspect `pipeline_runs` to auto-skip completed stages upon re-execution (resumability gap).

---

## 2. Logic Chain

1. **Premise 1 (From Observation 1 & 2)**: When network calls in startup steps (Steps 2 & 4) or Lead-Lag training (Step 7c) throw an exception, the absence of local `try...except` blocks causes the exception to propagate directly to the top-level handler, terminating execution before any cached price data or alternative model training can take place.
2. **Premise 2 (From Observation 3 & 4)**: If `predict_all`, `predict_lead_lag`, `vcp_ml.predict`, GMM regime detection, or `calculate_ensemble_score` throws an error due to unexpected missing columns or numerical issues in a single market, uncaught exceptions will crash the entire pipeline before rule-based/quant factor strategies (VCP, Stat-Arb, Sector Rotation, RIM, Event-Driven, MQ, IV Skew, Order Flow, Reversal, ARM, CARD, LATR, Inst-Foreign) can write their output files.
3. **Premise 3 (From Observation 5 & 6)**: The data layer is highly resilient once data fetch begins due to Tier 1/2/3 fallbacks, binary split batch recovery, macro distinctness bounds checking, halted stock purging, and per-market training isolation.
4. **Premise 4 (From Observation 7)**: While pipeline state is tracked in `pipeline_runs`, lack of a checkpoint resume check forces full pipeline re-runs on failure recovery unless CLI flags are manually passed.
5. **Conclusion**: Applying targeted `try...except` guards around Steps 2, 4, 7c, 10a, 10d, 10e, 11b, 11d, and Portfolio Allocation will eliminate all remaining single-point failure risks in `run_pipeline.py`, achieving complete exception safety and step isolation.

---

## 3. Caveats

- **No Source Code Edits**: Per investigation rules, no direct modifications were made to the python source files during this read-only audit. All recommended patches are documented in `analysis.md`.
- **Live Network Behavior**: External network behavior (yfinance rate limits, FDR scraping alterations, Open DART API key availability) depends on external services; audit validated fallbacks based on code analysis and unit test patterns.

---

## 4. Conclusion

`trading_system/run_pipeline.py` possesses an exceptionally strong multi-tier data engine, macro data integrity sanitization gate, and per-market training isolation. To achieve 100% exception safety and step isolation across all 12 pipeline steps, the missing `try...except` blocks identified in Steps 2, 4, 7c, 10a, 10d, 10e, 11b, 11d, and Portfolio Allocation should be applied as specified in `analysis.md`.

---

## 5. Verification Method

1. **Run Full Pytest Suite**:
   ```powershell
   .venv\Scripts\python.exe -m pytest tests/ -v
   ```
2. **Verify Pipeline Dry-Run Execution**:
   ```powershell
   .venv\Scripts\python.exe trading_system/run_pipeline.py --debug
   ```
3. **Verify Output Artifact Generation**:
   Check that files exist and are non-empty in `trading_system/result/`:
   - `ensemble_predictions.txt`
   - `strategy_data_coverage_report.txt`
   - `pipeline_result.txt`
   - `surge_predictions.txt`
   - `lead_lag_predictions.txt`
   - `vcp_patterns.txt`
   - `vcp_ml_predictions.txt`
   - `stat_arb_predictions.txt`
   - `inst_foreign_sector_predictions.txt`
   - `gh-pages/index.html`
4. **Inspect Pipeline State Tracking**:
   Verify SQLite `market_indicators.db` table `pipeline_runs` records stage completion records.
