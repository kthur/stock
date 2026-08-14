# Investigation Report: Pipeline Execution & GitHub Pages Report Generation

## 1. Observation

### Exact File Paths & Code References
- **Master Orchestrator**: `d:\Finance\code\stock\trading_system\run_pipeline.py` (4,026 lines)
  - CLI parser & argument definitions: `run_pipeline.py:3907-3959`
  - Master pipeline execution entrypoint: `run_pipeline.py:1085-3901` (`def execute_prediction_pipeline()`)
  - Global indicator ingestion & DB storage: `run_pipeline.py:1102-1125` (`MarketIndicatorStorage`, `GlobalMarketClient`)
  - Universe loading & market filtering: `run_pipeline.py:1127-1177` (`storage.get_universe()`, KONEX exclusion)
  - Training loop (Regression, Surge, Lead-Lag, VCP ML, Isotonic Calibration): `run_pipeline.py:1234-1495`
  - Inference data fetching & caching: `run_pipeline.py:1497-1622` (`prefetch_prices_batch`, `fetch_data_fdr`)
  - Strategy alpha computations (Strategies 1-30):
    - Strategy 1 (Regression) & 2 (Surge): `run_pipeline.py:1623-1640`
    - Strategy 4 (VCP Rule) & Breakout Trigger: `run_pipeline.py:1641-1722`
    - Strategy 3 (Lead-Lag): `run_pipeline.py:1723-1728`
    - Strategy 7 (Stat-Arb Cointegration): `run_pipeline.py:1730-1808`
    - Strategy 8 (Sector Rotation): `run_pipeline.py:2293-2349`
    - Strategy 9 (RIM Valuation): `run_pipeline.py:2351-2420`
    - Strategy 10 (Event-Driven Catalyst): `run_pipeline.py:2427-2474`
    - Strategy 11 (MQ Factor): `run_pipeline.py:2476-2510`
    - Strategy 12 (Options IV Skew): `run_pipeline.py:2512-2546`
    - Strategy 13 (Order Flow Imbalance MFI): `run_pipeline.py:2548-2582`
    - Strategy 14 (Short-Term Reversal): `run_pipeline.py:2584-2618`
    - Strategy 15 (ARM Factor): `run_pipeline.py:2672-2732`
    - Strategy 16 (CARD Factor): `run_pipeline.py:2734-2767`
    - Strategy 17 (LATR Factor): `run_pipeline.py:2769-2802`
    - Strategy 18 (Inst & Foreign Sector): `run_pipeline.py:2804-2837`
    - Strategy 19 (Supply Chain): `run_pipeline.py:2839-2857`
    - Strategy 20 (NLP Sentiment): `run_pipeline.py:2859-2877`
    - Strategy 21 (Factor Neutralized Pure Alpha): `run_pipeline.py:2879-2905`
    - Strategy 22 (Vol Targeting): `run_pipeline.py:2907-2925`
    - Strategy 23 (Microstructure Imbalance): `run_pipeline.py:2927-2945`
    - Strategies 24-30 (Accruals, Short Squeeze, ValueUp, Trend Efficiency, Gamma, Insider, Tone Drift): `run_pipeline.py:2946-3012`
  - Dynamic 2D Regime Ensemble & Microstructure Friction: `run_pipeline.py:3022-3057` (`scorer.calculate_ensemble_score`)
  - Risk Manager & Crisis Detector Gating: `run_pipeline.py:3227-3258`
  - Coverage & Missingness Report Generation: `run_pipeline.py:3380-3437` (`StrategyCoverageAnalyzer`)
  - Portfolio Allocation (HRP & Black-Litterman): `run_pipeline.py:3455-3472`, `3730-3772`
  - Execution OMS Order Plan Generation: `run_pipeline.py:3494-3526` (`ExecutionOMSEngine`)
  - GitHub Pages HTML Compilation call: `run_pipeline.py:3789-3811` (`generate_report.main`)
  - Post-pipeline verification checks: `run_pipeline.py:3813-3870`

- **Dashboard Compiler**: `d:\Finance\code\stock\trading_system\generate_report.py` (3,356 lines)
  - CLI parameters: `--result-dir` (default: `trading_system/result`), `--out` (default: `gh-pages/index.html`) (`generate_report.py:3171-3185`)
  - Data Parsers: `parse_ensemble`, `parse_surge`, `parse_vcp`, `parse_lead_lag`, `parse_vcp_ml`, `parse_regression`, `parse_stat_arb`, `parse_sector`, `parse_rim`, `parse_portfolio_allocation`, `parse_event_driven`, `parse_mq_factor`, `parse_iv_skew`, `parse_order_flow`, `parse_short_term_reversal`, `parse_arm_factor`, `parse_card_factor`, `parse_latr_factor`, `parse_inst_foreign_sector`, `parse_supply_chain`, `parse_sentiment`, `parse_factor_neutralized`, `parse_vol_target`, `parse_microstructure` (`generate_report.py:186-800+`)
  - HTML & CSS & JavaScript Builder: `build_html` (`generate_report.py:1000-3164`)
  - Scenario Simulator Universe Generator: `generate_report.py:3212-3258`

- **Artifact Verification Script**: `d:\Finance\code\stock\trading_system\scripts\verify_gha_artifacts.py` (530 lines)
  - CLI parameters: `--result-dir`, `--gh-pages-dir`, `--strict`, `--json`
  - Verified execution output:
    ```
    ================================================================================================================================================================
     🔍 Pipeline GHA Artifact Verification Report (23 Strategies & Dashboard)
    ================================================================================================================================================================
    Result Directory   : D:\Finance\code\stock\trading_system\result
    GitHub Pages Dir   : D:\Finance\code\stock\gh-pages
    ...
    🌐 GitHub Pages HTML Dashboard & 23 Strategy Panels:
      File Found     : Yes
      Valid Status   : ✅ Valid
      Markets in HTML: SP500, NASDAQ, RUSSELL2000, KOSPI, KOSDAQ
      Summary Message: GitHub Pages HTML generated cleanly with 5 markets and all 23 strategy panels populated with data
    ```

---

## 2. Logic Chain

1. **Pipeline Execution Flow & Control Invariants**:
   - `run_pipeline.py` starts by validating `.env` settings via `TradingConfig()`. It verifies SQLite WAL connections to `market_indicators.db` and `stock_prices.db`.
   - In Step 4 (`run_pipeline.py:1127-1177`), `KONEX` is explicitly pruned from active universe, leaving `KOSPI`, `KOSDAQ`, `SP500`, `NASDAQ`, `RUSSELL2000`.
   - When `--target <MARKET>` or `INFERENCE_TARGET=<MARKET>` is set, the universe is narrowed specifically to that market to allow matrix-based GHA execution.
   - If `--skip-training` or `SKIP_TRAINING=True` is provided, `OnDevicePredictionModel.load_models()` and `VCPSurgePredictor.load_models()` load pre-trained models from `trading_system/models/`.
   - If `--debug` is provided, training and inference samples are restricted to 3-5 symbols per market for lightning-fast dry-run verification.

2. **Prediction & Output File Generation**:
   - Every strategy engine computes predictions and writes both a unified report and individual per-market suffix files (`<strategy>_<MARKET>.txt`) into `trading_system/result/` (or `OUTPUT_RESULT_DIR`).
   - Strategy 21 (`MultiFactorNeutralizerEngine`) writes `factor_neutralized_predictions.txt`, outputting pure alpha scores after Fama-French 5-factor QR residualization.
   - `EnsembleScoringEngine` computes dynamic 2D regime weights (using exponential Sharpe multipliers and Almgren-Chriss microstructure friction) and writes `ensemble_predictions.txt`.
   - `StrategyCoverageAnalyzer` writes `strategy_data_coverage_report.txt`, analyzing coverage and missingness across all strategies.
   - `PortfolioAllocator` produces `portfolio_allocation.txt` (HRP) and `portfolio_allocation_black_litterman.txt`.

3. **Report Generation & Dashboard Compilation**:
   - Phase 6-D of `run_pipeline.py` automatically invokes `generate_report.main(["--result-dir", str(result_dir), "--out", str(gh_pages_dir / "index.html")])`.
   - `generate_report.py` parses all 23+ prediction text files in `result_dir`, extracts macro indicators, regime rationale, and backtest summary metrics, and generates a self-contained, interactive HTML file (`gh-pages/index.html`).
   - `verify_gha_artifacts.py` checks both the text prediction files across 5 markets and the DOM structure/tables inside `gh-pages/index.html`.

---

## 3. Caveats

- **Network vs. Offline Caching**: In network-disconnected or CI test environments, online fetchers (`yfinance`, `FinanceDataReader`, `ECOS`, `DART`) will fail if not mocked or cached. However, `run_pipeline.py` has built-in fallbacks to SQLite caches (`stock_prices.db` and `market_indicators.db`). When testing offline, setting `STOCK_PRICE_FRESHNESS_DAYS=none` (or negative) prevents network timeouts.
- **Model Cache Availability**: Running with `--skip-training` requires serialized model files (`cat_model_*`, `vcp_model_*`) to exist in `trading_system/models/`. If empty, the pipeline will fall back to training unless `PRESEED_MODE=true` is set.
- **Single-Market Matrix vs. Full-Market**: In GHA matrix jobs, each job writes per-market files (e.g. `ensemble_predictions_SP500.txt`). The merge step (`trading_system/merge_predictions.py`) combines them into the final unified files before running `generate_report.py`.

---

## 4. Conclusion

The pipeline architecture and dashboard generation are completely structured, deterministic, and modular:
1. `trading_system/run_pipeline.py` provides end-to-end orchestration with support for CLI flags (`--target`, `--skip-training`, `--skip-inference`, `--debug`) and environment variables (`INFERENCE_TARGET`, `SKIP_TRAINING`, `OUTPUT_RESULT_DIR`).
2. All expected pipeline output files (`pipeline_result.txt`, `surge_predictions.txt`, `ensemble_predictions.txt`, `factor_neutralized_predictions.txt`, `strategy_data_coverage_report.txt`, etc.) are written directly to `trading_system/result/`.
3. `trading_system/generate_report.py` compiles all outputs into `gh-pages/index.html`.
4. Verification can be performed programmatically via `trading_system/scripts/verify_gha_artifacts.py` and the full pytest suite.

---

## 5. Verification Method

### Exact Execution Commands

1. **Fast Dry-Run Pipeline Execution (Debug Mode)**:
   ```powershell
   .venv\Scripts\python.exe trading_system\run_pipeline.py --debug --skip-training
   ```
   *Unix/Linux:*
   ```bash
   .venv/bin/python trading_system/run_pipeline.py --debug --skip-training
   ```

2. **Single-Market Target Execution (e.g., SP500 / KOSPI)**:
   ```powershell
   .venv\Scripts\python.exe trading_system\run_pipeline.py --target SP500 --skip-training
   .venv\Scripts\python.exe trading_system\run_pipeline.py --target KOSPI --skip-training
   ```

3. **Standalone GitHub Pages Report Compilation**:
   ```powershell
   .venv\Scripts\python.exe trading_system\generate_report.py --result-dir trading_system\result --out gh-pages\index.html
   ```

4. **Automated Artifact & Dashboard Verification**:
   ```powershell
   .venv\Scripts\python.exe trading_system\scripts\verify_gha_artifacts.py --result-dir trading_system\result --gh-pages-dir gh-pages
   ```

5. **Pytest Regression Verification**:
   ```powershell
   .venv\Scripts\python.exe -m pytest trading_system\tests\test_e2e_consolidated.py -v
   .venv\Scripts\python.exe -m pytest trading_system\tests\test_report_generator_hrp.py trading_system\tests\test_kst_and_coverage_reasoning.py -v
   ```

### Verification Checks
- `trading_system/result/ensemble_predictions.txt`: exists, non-empty, contains 2D regime summary and TOP picks.
- `trading_system/result/factor_neutralized_predictions.txt`: exists, non-empty, contains Strategy 21 pure alpha scores.
- `trading_system/result/strategy_data_coverage_report.txt`: exists, non-empty, contains coverage percentages.
- `gh-pages/index.html`: exists, file size > 50KB, contains market tables for SP500, NASDAQ, RUSSELL2000, KOSPI, KOSDAQ without unrendered templates.
