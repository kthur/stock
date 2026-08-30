# Comprehensive Investigation Report: Pipeline Result Files, Strategy Output Schema, and Merge Synchronization

## 1. Observation

### 1.1 Architecture & Pipeline File Dataflow
We examined the full dataflow from strategy score calculation (`src/core/`, `src/ai/`), pipeline orchestration (`trading_system/run_pipeline.py`), GHA matrix split artifact generation (`.github/workflows/pipeline.yml`), multi-market output merging (`trading_system/merge_predictions.py`), and GitHub Pages HTML report generation (`trading_system/generate_report.py`).

1. **Pipeline Execution (`trading_system/run_pipeline.py`)**:
   - Orchestrates all 31+ multi-factor strategies.
   - Strategy reports are saved to `trading_system/result/<filename>.txt` via `_save_strategy_predictions_report()` (lines 2845–2886) and per-market suffixed files `<base_name>_<MARKET>.txt`.
   - The 31-strategy ensemble is scored by `EnsembleScoringEngine` (`src/ai/ensemble_scorer.py`) and saved to `ensemble_predictions.txt` and `ensemble_predictions_<MARKET>.txt`.
   - Coverage report is saved to `strategy_data_coverage_report.txt` and `strategy_data_coverage_report_<MARKET>.txt`.
   - Portfolio allocation is saved to `portfolio_allocation.txt` and `portfolio_allocation_<MARKET>.txt`.

2. **GHA Matrix Output Split (`.github/workflows/pipeline.yml:237–260`)**:
   - Each matrix target (`SP500`, `NASDAQ`, `RUSSELL2000`, `KOSPI`, `KOSDAQ`) copies generated files to `trading_system/result_split/<filename>_<TARGET>.txt`.
   - Uploads artifact `result-${TARGET}`.

3. **Merge Synchronization (`trading_system/merge_predictions.py`)**:
   - In `merge-and-release` job, downloads all `result-*` artifacts into `trading_system/result/`.
   - Merges per-market files into unified output files using `merge_pipeline_result()`, `merge_ensemble_predictions()`, `merge_surge_predictions()`, `merge_vcp_ml_predictions()`, `merge_vcp_patterns()`, `merge_lead_lag_predictions()`, `merge_portfolio_allocation()`, `merge_coverage_report()`, and `merge_generic_strategy_files()`.

4. **Dashboard Generation (`trading_system/generate_report.py`)**:
   - Reads merged `.txt` and `.json` files from `trading_system/result/`.
   - Parses each strategy into structured dataclass rows (`parse_ensemble`, `parse_regression`, `parse_surge`, `parse_lead_lag`, `parse_vcp`, `parse_vcp_ml`, `parse_lstm`, `parse_stat_arb`, `parse_sector`, `parse_rim`, `parse_portfolio_allocation`, `parse_event_driven`, `parse_mq_factor`, `parse_iv_skew`, `parse_order_flow`, `parse_short_term_reversal`, `parse_arm_factor`, `parse_card_factor`, `parse_latr_factor`, `parse_inst_foreign_sector`, `parse_supply_chain`, `parse_sentiment`, `parse_factor_neutralized`, `parse_vol_target`, `parse_microstructure`, `parse_accruals_quality`, `parse_short_squeeze`, `parse_valueup_catalyst`, `parse_trend_efficiency`, `parse_gamma_squeeze`, `parse_insider_buying`, `parse_darkpool`, `parse_earnings_tone_drift`).
   - Dynamically builds HTML tables and status banners per market panel (`data-market="<MARKET>"`).
   - Generates interactive client-side JavaScript for market filtering (`filterMarket()`), tab switching (`switchTab()`), search autocomplete (`filterStockTables()`), column sorting (`sortTable()`), and Scenario Simulation.

---

### 1.2 Strategy Schema, File Naming, and Column Mapping Audit (All 31+ Strategies)

| # | Strategy Name | Internal ID | Engine Class | Pipeline Output File | Merged File | Data Schema & Headers | Parser in `generate_report.py` |
|---|---|---|---|---|---|---|---|
| **1** | XGBoost Regression | `regression` | `OnDevicePredictionModel` | `pipeline_result.txt` | `pipeline_result.txt` | `[1d]`, `[3d]`, `[5d]`, `[10d]`, `[20d]`, `[60d]`, `[120d]`, `[200d]` | `parse_regression` |
| **2** | Surge Classifier | `surge` | `OnDevicePredictionModel` | `surge_predictions.txt` | `surge_predictions.txt` | `[1일] MARKET Top 20`, `[3일]`, `[5일]`, `[20일]` | `parse_surge` |
| **3** | Lead-Lag Flow | `lead_lag` | `OnDevicePredictionModel` | `lead_lag_predictions.txt` | `lead_lag_predictions.txt` | `--- MARKET Top 100 ---`<br>`1. [MKT] SYM (Name): Score%` | `parse_lead_lag` |
| **4** | VCP Pattern (Rule) | `vcp_rule` | `VCPPatternDetector` | `vcp_patterns.txt` | `vcp_patterns.txt` | `--- MARKET (N patterns) ---`<br>`1. [SYM] Name (Contractions: ...)` | `parse_vcp` |
| **5** | VCP ML Predictor | `vcp_ml` | `VCPMLPredictor` | `vcp_ml_predictions.txt` | `vcp_ml_predictions.txt` | `[1일] MARKET TOP 5` ... | `parse_vcp_ml` |
| **6** | Strict Causal LSTM | `lstm` | `LSTMStrategyAdapter` | `lstm_predictions.txt` | `lstm_predictions.txt` | `Rank  Symbol  Name  Market  Score` | `parse_lstm` |
| **7** | Stat-Arb Cointegration | `stat_arb` | `StatisticalArbitrageEngine` | `stat_arb_predictions.txt` | `stat_arb_predictions.txt` | `Pair: SYM1 (MKT1) - SYM2 (MKT2) ...` | `parse_stat_arb` |
| **8** | Sector Rotation | `sector_rotation` | `SectorRotationEngine` | `sector_predictions.txt` | `sector_predictions.txt` | `Rank  Symbol  Name  Market  Sector  Sector Score` | `parse_sector` |
| **9** | RIM Valuation | `rim_valuation` | `RIMValuationEngine` | `rim_predictions.txt` | `rim_predictions.txt` | `Rank  Symbol  Name  Market  Price  Intrinsic V0  Discount %  ROE_raw  ROE_adj  EQ  Filter  RIM Score` | `parse_rim` |
| **10** | Event-Driven Catalyst | `event_driven` | `EventDrivenEngine` | `event_driven_predictions.txt` | `event_driven_predictions.txt` | `Rank  Symbol  Name  Market  Event Score` | `parse_event_driven` |
| **11** | Momentum Quality (MQ) | `mq_factor` | `MQFactorEngine` | `mq_factor_predictions.txt` | `mq_factor_predictions.txt` | `Rank  Symbol  Name  Market  MQ Score` | `parse_mq_factor` |
| **12** | Options IV Skew | `iv_skew` | `IVSkewEngine` | `iv_skew_predictions.txt` | `iv_skew_predictions.txt` | `Rank  Symbol  Name  Market  IV Skew Score` | `parse_iv_skew` |
| **13** | Order Flow Imbalance | `order_flow` | `OrderFlowEngine` | `order_flow_predictions.txt` | `order_flow_predictions.txt` | `Rank  Symbol  Name  Market  Order Flow Score` | `parse_order_flow` |
| **14** | Short-Term Reversal | `short_term_reversal` | `ShortTermReversalEngine` | `short_term_reversal_predictions.txt` | `short_term_reversal_predictions.txt` | `Rank  Symbol  Name  Market  Reversal Score` | `parse_short_term_reversal` |
| **15** | Analyst Revision (ARM) | `arm_factor` | `ARMFactorEngine` | `arm_factor_predictions.txt` | `arm_factor_predictions.txt` | `Rank  Symbol  Name  Market  ARM Score` | `parse_arm_factor` |
| **16** | Cross-Asset Divergence | `card_factor` | `CARDFactorEngine` | `card_factor_predictions.txt` | `card_factor_predictions.txt` | `Rank  Symbol  Name  Market  CARD Score` | `parse_card_factor` |
| **17** | Liquidity Tail Risk (LATR) | `latr_factor` | `LATRFactorEngine` | `latr_factor_predictions.txt` | `latr_factor_predictions.txt` | `Rank  Symbol  Name  Market  LATR Score` | `parse_latr_factor` |
| **18** | Inst & Foreign Sector | `inst_foreign_sector` | `InstForeignSectorEngine` | `inst_foreign_sector_predictions.txt` | `inst_foreign_sector_predictions.txt` | `Rank  Symbol  Name  Market  IFS Score` | `parse_inst_foreign_sector` |
| **19** | Supply Chain Momentum | `supply_chain` | `SupplyChainEngine` | `supply_chain_predictions.txt` | `supply_chain_predictions.txt` | `Rank  Symbol  Name  Market  SC Score` | `parse_supply_chain` |
| **20** | FinBERT Sentiment | `sentiment` | `DARTSECSentimentEngine` | `sentiment_predictions.txt` | `sentiment_predictions.txt` | `Rank  Symbol  Name  Market  Sent Score` | `parse_sentiment` |
| **21** | Factor Neutralized | `factor_neutralized` | `MultiFactorNeutralizerEngine` | `factor_neutralized_predictions.txt` | `factor_neutralized_predictions.txt` | `Rank  Symbol  Name  Market  FN Score` | `parse_factor_neutralized` |
| **22** | Dynamic Vol Targeting | `vol_target` | `VolTargetingEngine` | `vol_target_predictions.txt` | `vol_target_predictions.txt` | `Rank  Symbol  Name  Market  VT Score` | `parse_vol_target` |
| **23** | Microstructure Imbalance | `microstructure` | `MicrostructureImbalanceEngine` | `microstructure_predictions.txt` | `microstructure_predictions.txt` | `Rank  Symbol  Name  Market  Micro Score` | `parse_microstructure` |
| **24** | Accruals Quality | `accruals_quality` | `AccrualsQualityEngine` | `accruals_quality_predictions.txt` | `accruals_quality_predictions.txt` | `Rank  Symbol  Name  Market  Accruals Score` | `parse_accruals_quality` |
| **25** | Short Squeeze | `short_squeeze` | `ShortInterestSqueezeEngine` | `short_squeeze_predictions.txt` | `short_squeeze_predictions.txt` | `Rank  Symbol  Name  Market  Squeeze Score` | `parse_short_squeeze` |
| **26** | Value-Up & Shareholder Yield | `valueup_catalyst` | `ValueUpCatalystEngine` | `valueup_catalyst_predictions.txt` | `valueup_catalyst_predictions.txt` | `Rank  Symbol  Name  Market  ValueUp Score` | `parse_valueup_catalyst` |
| **27** | Trend Efficiency | `trend_efficiency` | `TrendEfficiencyEngine` | `trend_efficiency_predictions.txt` | `trend_efficiency_predictions.txt` | `Rank  Symbol  Name  Market  Trend Score` | `parse_trend_efficiency` |
| **28** | Options Gamma Squeeze | `gamma_squeeze` | `OptionsGammaSqueezeEngine` | `gamma_squeeze_predictions.txt` | `gamma_squeeze_predictions.txt` | `Rank  Symbol  Name  Market  Gamma Score` | `parse_gamma_squeeze` |
| **29** | Insider Buying Catalyst | `insider_buying` | `InsiderBuyingEngine` | `insider_buying_predictions.txt` | `insider_buying_predictions.txt` | `Rank  Symbol  Name  Market  Insider Score` | `parse_insider_buying` |
| **30** | Earnings Tone Drift | `earnings_tone_drift` | `EarningsToneDriftEngine` | `earnings_tone_drift_predictions.txt` | `earnings_tone_drift_predictions.txt` | `Rank  Symbol  Name  Market  Tone Score` | `parse_earnings_tone_drift` |
| **31** | Darkpool & HFT Flow | `darkpool` | `DarkPoolTrackerEngine` | `hft_order_flow_predictions.txt` | `hft_order_flow_predictions.txt` | `Rank  Symbol  Name  Market  HFT Score` | `parse_darkpool` |
| **Ensemble** | 31-Strategy Dynamic Ensemble | `ensemble` | `EnsembleScoringEngine` | `ensemble_predictions.txt` | `ensemble_predictions.txt` | Macro Indicators + 2D Rationale + Strategy Weights + `[MARKET] Top 100` (36 columns) | `parse_ensemble` |
| **Allocation** | Portfolio Allocation (HRP) | `allocation` | `PortfolioAllocator` | `portfolio_allocation.txt` | `portfolio_allocation.txt` | `No.  Symbol  Name  Market  Return  Volatility  Weight  Amount` | `parse_portfolio_allocation` |
| **Coverage** | Data Coverage & Missingness | `coverage` | `StrategyCoverageAnalyzer` | `strategy_data_coverage_report.txt` | `strategy_data_coverage_report.txt` | `Strategy  Valid Count  Missing Count  Coverage %  Primary Missing Reason` | `parse_strategy_coverage_report` |

---

## 2. Logic Chain

### 2.1 Why Certain Strategy Tables Appeared Empty ("데이터 없음")
Through empirical code inspection and execution of the parsing pipelines against `trading_system/result/`:

1. **Fundamental Dependency & NaN Filtering**:
   - In `run_pipeline.py` line 2859:
     ```python
     merged[score_col] = pd.to_numeric(merged[score_col], errors='coerce')
     merged = merged.dropna(subset=[score_col]).sort_values(by=score_col, ascending=False)
     ```
   - When fundamental data is missing (e.g. offline runs or SQLite cache misses):
     - `AccrualsQualityEngine` returns all NaN because `net_income` and `operating_cash_flow` are absent.
     - `ValueUpCatalystEngine` returns all NaN because `bps` / `pbr` are absent.
     - `EarningsToneDriftEngine` returns all NaN because transcripts and fundamental earnings growth are absent.
     - `DARTSECSentimentEngine` returns all NaN when filings are absent and prices dictionary was not provided.
   - When all rows are NaN, `merged.dropna(subset=[score_col])` becomes an empty DataFrame.
   - `_write_content` then writes `Total symbols evaluated: 0` and **0 data rows**.
   - When `generate_report.py` reads these files, `_parse_simple_strategy` parses 0 rows.
   - `generate_report.py` checks `mkt_rows = [r for r in rows_list if r.market == mkt]`. Because `mkt_rows` is empty, it displays `<tr><td colspan="5" class="empty">데이터 없음</td></tr>` and a status banner.

2. **Merge Discovery Gate Bug in `merge_predictions.py`**:
   - In `merge_predictions.py` lines 684–702, the target directory detection logic for `result_dir` used:
     ```python
     probe = result_dir / f"surge_predictions_{m}.txt"
     if probe.exists():
         target_dirs[m] = result_dir
     ```
   - If `surge_predictions_{m}.txt` was missing for market `m` (e.g. NASDAQ or RUSSELL2000), `target_dirs[m]` was not set.
   - This caused `merge_predictions.py` to completely skip that market during the merge of all other strategy files (`ensemble_predictions.txt`, `vcp_ml_predictions.txt`, `lead_lag_predictions.txt`, and all generic strategy files).

3. **Active Markets Dynamic Filtering in `generate_report.py`**:
   - In `generate_report.py` lines 1890–1930, `active_markets_ordered` was constructed solely from markets that had at least one populated row across all parsed files (`all_seen_markets`).
   - If markets like `NASDAQ` and `RUSSELL2000` had 0 populated rows in the existing result files, they were omitted from `active_markets_ordered`, causing the UI to only show `KOSPI`, `KOSDAQ`, `SP500`, `KONEX`.

---

## 3. Caveats

1. **Read-Only Explorer Scope**: This investigation was conducted in strict read-only mode without modifying source code files directly.
2. **Offline Data Constraints**: In local developer environments without live OpenDART / SEC API keys, filing-based engines (`EventDrivenEngine`, `InsiderBuyingEngine`, `DARTSECSentimentEngine`) rely on fallback heuristics (price/volume action, gap volatility) rather than live regulatory XML parsing.
3. **Historical Split Files**: Some older files in `trading_system/result/` (e.g. from early August) had fewer strategy columns (18 or 31 strategies) than the current 33-strategy pipeline header. When re-running the full pipeline, all files are regenerated consistently with the 36-column schema.

---

## 4. Conclusion & Actionable Recommendations

### 4.1 Root Causes Identified
1. **Fallback Score Population in Strategy Engines**:
   When external/fundamental APIs return empty data, engines should compute valid heuristic baseline scores (price action, volume volatility, historical growth estimates) rather than emitting 100% NaNs that get dropped by `_save_strategy_predictions_report()`.
2. **Merge Discovery Gate in `merge_predictions.py`**:
   Replace the single `surge_predictions_{m}.txt` probe with a robust check for any market-suffixed file (`result_dir.glob(f"*_{m}.*")` or checking `pipeline_result_{m}.txt` / `ensemble_predictions_{m}.txt`).
3. **Guaranteed Core Market Inclusion in `generate_report.py`**:
   Ensure `active_markets_ordered` always includes `["KOSPI", "KOSDAQ", "SP500", "NASDAQ", "RUSSELL2000"]` so all 5 core market tabs are permanently available and rendered on the dashboard.
4. **Filename Consistency**:
   Standardize `darkpool` vs `hft_order_flow_predictions.txt` across all merge and release steps.

---

## 5. Verification Method

To independently verify the pipeline output files, schema alignment, and report generation:

1. **Verify Report Generator**:
   ```bash
   .venv/bin/python trading_system/generate_report.py --result-dir trading_system/result --out gh-pages/index.html
   ```
   *Expected*: Generates `gh-pages/index.html` cleanly with 0 errors.

2. **Verify Multi-Market Prediction Merge**:
   ```bash
   .venv/bin/python trading_system/merge_predictions.py
   ```
   *Expected*: Merges all 31+ strategies and 5 markets without skipping `SP500`, `NASDAQ`, `RUSSELL2000`, `KOSPI`, or `KOSDAQ`.

3. **Verify Full Unit & Integration Test Suite**:
   ```bash
   .venv/bin/pytest tests/test_report_generator_hrp.py tests/test_report_ux_and_rounding.py tests/test_merge_generic_strategies.py tests/test_challenger2_dashboard_parser_stress.py -v
   ```
   *Expected*: 100% pass across all tests.
