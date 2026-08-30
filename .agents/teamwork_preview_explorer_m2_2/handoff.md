# Milestone 2 Investigation Report: 31+ Strategy File Mapping, Schema Consistency, and Merge Tests

## 1. Observation

### 1.1 Complete 31+ Strategy File & Schema Audit Matrix
We performed a systematic code audit across the pipeline generation (`trading_system/run_pipeline.py`), multi-market merge synchronization (`trading_system/merge_predictions.py`), GitHub Actions workflow (`.github/workflows/pipeline.yml`), and dashboard report generation (`trading_system/generate_report.py`).

The complete 31+ strategy mapping matrix is summarized below:

| # | Strategy Name | Internal ID | Engine Class | Pipeline Output (`run_pipeline.py`) | Per-Market Split File | Merged Output File | Merge Routine (`merge_predictions.py`) | Report Parser (`generate_report.py`) | Header Format & Key Columns |
|---|---|---|---|---|---|---|---|---|---|
| **1** | XGBoost Regression | `regression` | `OnDevicePredictionModel` | `pipeline_result.txt` (line 4409) | `pipeline_result_{M}.txt` | `pipeline_result.txt` | `merge_pipeline_result` (line 59) | `parse_regression` (line 334) | `[1d]`, `[3d]`, `[5d]`, `[10d]`, `[20d]`, `[60d]`, `[120d]`, `[200d]` |
| **2** | Surge Classifier | `surge` | `OnDevicePredictionModel` | `surge_predictions.txt` (line 2233) | `surge_predictions_{M}.txt` | `surge_predictions.txt` | `merge_surge_predictions` (line 164) | `parse_surge` (line 396) | `[1일] MARKET Top 20`, `[3일]`, `[5일]`, `[20일]` |
| **3** | Lead-Lag Flow | `lead_lag` | `OnDevicePredictionModel` | `lead_lag_predictions.txt` (line 2307) | `lead_lag_predictions_{M}.txt` | `lead_lag_predictions.txt` | `merge_lead_lag_predictions` (line 346) | `parse_lead_lag` (line 467) | `--- MARKET Top 100 ---`<br>`1. [MKT] SYM (Name): Score%` |
| **4** | VCP Pattern (Rule) | `vcp_rule` | `VCPPatternDetector` | `vcp_patterns.txt` | `vcp_patterns_{M}.txt` | `vcp_patterns.txt` | `merge_vcp_patterns` (line 296) | `parse_vcp` (line 527) | `--- MARKET (N patterns) ---`<br>`1. [SYM] Name (Contractions: ...)` |
| **5** | VCP ML Predictor | `vcp_ml` | `VCPMLPredictor` | `vcp_ml_predictions.txt` (line 2444) | `vcp_ml_predictions_{M}.txt` | `vcp_ml_predictions.txt` | `merge_vcp_ml_predictions` (line 232) | `parse_vcp_ml` (line 573) | `[1일] MARKET TOP 5` ... |
| **6** | Strict Causal LSTM | `lstm` | `LSTMStrategyAdapter` | `lstm_predictions.txt` (line 4278) | `lstm_predictions_{M}.txt` | `lstm_predictions.txt` | `merge_generic_strategy_files` (line 715) | `parse_lstm` (line 847) | `Rank  Symbol  Name  Market  LSTM Score` |
| **7** | Stat-Arb Cointegration | `stat_arb` | `StatisticalArbitrageEngine` | `stat_arb_predictions.txt` (line 2080) | `stat_arb_predictions_{M}.txt` | `stat_arb_predictions.txt` | `merge_generic_strategy_files` (line 723) | `parse_stat_arb` (line 621) | `Pair  Z-Score  Correlation  Beta/Hedge  Signal` |
| **8** | Sector Rotation | `sector_rotation` | `SectorRotationEngine` | `sector_predictions.txt` (line 2647) | `sector_predictions_{M}.txt` | `sector_predictions.txt` | `merge_generic_strategy_files` (line 716) | `parse_sector` (line 644) | `Rank  Symbol  Name  Market  Sector  Sector Score` |
| **9** | RIM Valuation | `rim_valuation` | `RIMValuationEngine` | `rim_predictions.txt` (line 2765) | `rim_predictions_{M}.txt` | `rim_predictions.txt` | `merge_generic_strategy_files` (line 717) | `parse_rim` (line 697) | `Filters: ...`<br>`Rank Symbol Name Market Price Intrinsic Discount ROE_raw ROE_adj EQ Filter RIM Score` |
| **10** | Event-Driven | `event_driven` | `EventDrivenEngine` | `event_driven_predictions.txt` (line 2929) | `event_driven_predictions_{M}.txt` | `event_driven_predictions.txt` | `merge_generic_strategy_files` (line 718) | `parse_event_driven` (line 851) | `Rank  Symbol  Name  Market  Event Score` |
| **11** | Momentum Quality (MQ) | `mq_factor` | `MQFactorEngine` | `mq_factor_predictions.txt` (line 2945) | `mq_factor_predictions_{M}.txt` | `mq_factor_predictions.txt` | `merge_generic_strategy_files` (line 719) | `parse_mq_factor` (line 855) | `Rank  Symbol  Name  Market  MQ Score` |
| **12** | Options IV Skew | `iv_skew` | `IVSkewEngine` | `iv_skew_predictions.txt` (line 2961) | `iv_skew_predictions_{M}.txt` | `iv_skew_predictions.txt` | `merge_generic_strategy_files` (line 720) | `parse_iv_skew` (line 859) | `Rank  Symbol  Name  Market  IV Skew Score` |
| **13** | Order Flow Imbalance | `order_flow` | `OrderFlowEngine` | `order_flow_predictions.txt` (line 2977) | `order_flow_predictions_{M}.txt` | `order_flow_predictions.txt` | `merge_generic_strategy_files` (line 721) | `parse_order_flow` (line 863) | `Rank  Symbol  Name  Market  Order Flow Score` |
| **14** | Short-Term Reversal | `short_term_reversal` | `ShortTermReversalEngine` | `short_term_reversal_predictions.txt` (line 2993) | `short_term_reversal_predictions_{M}.txt` | `short_term_reversal_predictions.txt` | `merge_generic_strategy_files` (line 722) | `parse_short_term_reversal` (line 867) | `Rank  Symbol  Name  Market  Reversal Score` |
| **15** | Analyst Revision (ARM) | `arm_factor` | `ARMFactorEngine` | `arm_factor_predictions.txt` (line 3105) | `arm_factor_predictions_{M}.txt` | `arm_factor_predictions.txt` | `merge_generic_strategy_files` (line 724) | `parse_arm_factor` (line 871) | `Rank  Symbol  Name  Market  ARM Score` |
| **16** | Cross-Asset Divergence | `card_factor` | `CARDFactorEngine` | `card_factor_predictions.txt` (line 3125) | `card_factor_predictions_{M}.txt` | `card_factor_predictions.txt` | `merge_generic_strategy_files` (line 725) | `parse_card_factor` (line 875) | `Rank  Symbol  Name  Market  CARD Score` |
| **17** | Liquidity Tail Risk (LATR) | `latr_factor` | `LATRFactorEngine` | `latr_factor_predictions.txt` (line 3143) | `latr_factor_predictions_{M}.txt` | `latr_factor_predictions.txt` | `merge_generic_strategy_files` (line 726) | `parse_latr_factor` (line 879) | `Rank  Symbol  Name  Market  LATR Score` |
| **18** | Inst & Foreign Sector | `inst_foreign_sector` | `InstForeignSectorEngine` | `inst_foreign_sector_predictions.txt` (line 3158) | `inst_foreign_sector_predictions_{M}.txt` | `inst_foreign_sector_predictions.txt` | `merge_generic_strategy_files` (line 727) | `parse_inst_foreign_sector` (line 882) | `Rank  Symbol  Name  Market  IFS Score` |
| **19** | Supply Chain | `supply_chain` | `SupplyChainEngine` | `supply_chain_predictions.txt` (line 3172) | `supply_chain_predictions_{M}.txt` | `supply_chain_predictions.txt` | `merge_generic_strategy_files` (line 728) | `parse_supply_chain` (line 886) | `Rank  Symbol  Name  Market  SC Score` |
| **20** | FinBERT Sentiment | `sentiment` | `DARTSECSentimentEngine` | `sentiment_predictions.txt` (line 3201) | `sentiment_predictions_{M}.txt` | `sentiment_predictions.txt` | `merge_generic_strategy_files` (line 729) | `parse_sentiment` (line 890) | `Rank  Symbol  Name  Market  Sent Score` |
| **21** | Factor Neutralized | `factor_neutralized` | `MultiFactorNeutralizerEngine` | `factor_neutralized_predictions.txt` (line 3221) | `factor_neutralized_predictions_{M}.txt` | `factor_neutralized_predictions.txt` | `merge_generic_strategy_files` (line 730) | `parse_factor_neutralized` (line 894) | `Rank  Symbol  Name  Market  FN Score` |
| **22** | Vol Targeting | `vol_target` | `VolTargetingEngine` | `vol_target_predictions.txt` (line 3235) | `vol_target_predictions_{M}.txt` | `vol_target_predictions.txt` | `merge_generic_strategy_files` (line 731) | `parse_vol_target` (line 898) | `Rank  Symbol  Name  Market  VT Score` |
| **23** | Microstructure | `microstructure` | `MicrostructureImbalanceEngine` | `microstructure_predictions.txt` (line 3249) | `microstructure_predictions_{M}.txt` | `microstructure_predictions.txt` | `merge_generic_strategy_files` (line 732) | `parse_microstructure` (line 902) | `Rank  Symbol  Name  Market  Micro Score` |
| **24** | Accruals Quality | `accruals_quality` | `AccrualsQualityEngine` | `accruals_quality_predictions.txt` (line 3264) | `accruals_quality_predictions_{M}.txt` | `accruals_quality_predictions.txt` | `merge_generic_strategy_files` (line 733) | `parse_accruals_quality` (line 906) | `Rank  Symbol  Name  Market  Accruals Score` |
| **25** | Short Squeeze | `short_squeeze` | `ShortInterestSqueezeEngine` | `short_squeeze_predictions.txt` (line 3279) | `short_squeeze_predictions_{M}.txt` | `short_squeeze_predictions.txt` | `merge_generic_strategy_files` (line 734) | `parse_short_squeeze` (line 910) | `Rank  Symbol  Name  Market  Squeeze Score` |
| **26** | Value-Up & Yield | `valueup_catalyst` | `ValueUpCatalystEngine` | `valueup_catalyst_predictions.txt` (line 3294) | `valueup_catalyst_predictions_{M}.txt` | `valueup_catalyst_predictions.txt` | `merge_generic_strategy_files` (line 735) | `parse_valueup_catalyst` (line 914) | `Rank  Symbol  Name  Market  ValueUp Score` |
| **27** | Trend Efficiency | `trend_efficiency` | `TrendEfficiencyEngine` | `trend_efficiency_predictions.txt` (line 3309) | `trend_efficiency_predictions_{M}.txt` | `trend_efficiency_predictions.txt` | `merge_generic_strategy_files` (line 736) | `parse_trend_efficiency` (line 918) | `Rank  Symbol  Name  Market  Trend Score` |
| **28** | Gamma Squeeze | `gamma_squeeze` | `OptionsGammaSqueezeEngine` | `gamma_squeeze_predictions.txt` (line 3323) | `gamma_squeeze_predictions_{M}.txt` | `gamma_squeeze_predictions.txt` | `merge_generic_strategy_files` (line 737) | `parse_gamma_squeeze` (line 922) | `Rank  Symbol  Name  Market  Gamma Score` |
| **29** | Insider Buying | `insider_buying` | `InsiderBuyingEngine` | `insider_buying_predictions.txt` (line 3343) | `insider_buying_predictions_{M}.txt` | `insider_buying_predictions.txt` | `merge_generic_strategy_files` (line 738) | `parse_insider_buying` (line 926) | `Rank  Symbol  Name  Market  Insider Score` |
| **30** | Earnings Tone Drift | `earnings_tone_drift` | `EarningsToneDriftEngine` | `earnings_tone_drift_predictions.txt` (line 3369) | `earnings_tone_drift_predictions_{M}.txt` | `earnings_tone_drift_predictions.txt` | `merge_generic_strategy_files` (line 740) | `parse_earnings_tone_drift` (line 934) | `Rank  Symbol  Name  Market  Tone Score` |
| **31** | Dark Pool & HFT | `darkpool` | `DarkPoolTrackerEngine` | `hft_order_flow_predictions.txt` (line 3387) | `hft_order_flow_predictions_{M}.txt` | `hft_order_flow_predictions.txt` | `merge_generic_strategy_files` (line 739) | `parse_darkpool` (line 930) | `Rank  Symbol  Name  Market  HFT Score` |
| **-** | Extended 32 (Dual Correction) | `dual_correction` | `DualCorrectionEngine` | `dual_correction_predictions.txt` (line 3405) | `dual_correction_predictions_{M}.txt` | `dual_correction_predictions.txt` | `merge_generic_strategy_files` (line 741) | - | `Rank  Symbol  Name  Market  Dual Score` |
| **-** | Extended 33 (Index Rebalance) | `index_rebalance` | `IndexRebalanceEngine` | `index_rebalance_predictions.txt` (line 3423) | `index_rebalance_predictions_{M}.txt` | `index_rebalance_predictions.txt` | `merge_generic_strategy_files` (line 742) | - | `Rank  Symbol  Name  Market  Rebal Score` |
| **-** | Extended 34 (Overnight Gap) | `overnight_gap` | `OvernightGapReversalEngine` | `overnight_gap_predictions.txt` (line 3441) | `overnight_gap_predictions_{M}.txt` | `overnight_gap_predictions.txt` | `merge_generic_strategy_files` (line 743) | - | `Rank  Symbol  Name  Market  Gap Score` |
| **Ensemble** | 31-Strategy Ensemble | `ensemble` | `EnsembleScoringEngine` | `ensemble_predictions.txt` (line 3969) | `ensemble_predictions_{M}.txt` (line 4224) | `ensemble_predictions.txt` | `merge_ensemble_predictions` (line 87) | `parse_ensemble` (line 267) | Macro Indicators + 2D Rationale + Weights + `[MARKET] Top 100` (36 columns) |
| **Allocation** | Portfolio Allocation (HRP) | `allocation` | `PortfolioAllocator` | `portfolio_allocation.txt` (line 4320) | `portfolio_allocation_{M}.txt` | `portfolio_allocation.txt` | `merge_portfolio_allocation` (line 459) | `parse_portfolio_allocation` (line 947) | `No.  Symbol  Name  Market  Return  Volatility  Weight  Amount` |
| **Coverage** | Data Coverage & Missingness | `coverage` | `StrategyCoverageAnalyzer` | `strategy_data_coverage_report.txt` (line 3915) | `strategy_data_coverage_report_{M}.txt` | `strategy_data_coverage_report.txt` | `merge_coverage_report` (line 639) | `_read(strategy_data_coverage_report.txt)` | `[MARKET]` section headers with Strategy, Valid, Missing, Reason |

---

### 1.2 Identified Bugs and Structural Deficiencies in Merge Layer

#### Defect 1: Market Discovery Single-Probe Gating Bug (`trading_system/merge_predictions.py:684–702`)
In `merge_predictions.py`:
```python
684:    for m in markets:
685:        # Prefer market-specific split directory; fall back to unified result dir
686:        split_path = base_dir / f"result_{m}"
687:        if split_path.exists() and any(split_path.iterdir()):
688:            target_dirs[m] = split_path
689:        elif result_dir.exists():
690:            # Check if market-suffixed files exist inside result_dir itself
691:            probe = result_dir / f"surge_predictions_{m}.txt"
692:            if probe.exists():
693:                target_dirs[m] = result_dir
694:
695:    if not target_dirs:
696:        print("Warning: No per-market result directories found. Checking result/ for suffix files.")
697:        for m in markets:
698:            probe = result_dir / f"pipeline_result_{m}.txt"
699:            if probe.exists():
700:                target_dirs[m] = result_dir
```
- **Direct observation**: In GHA runs, split files are placed directly into `trading_system/result/`. The loop at line 684 checks ONLY `surge_predictions_{m}.txt`. If `surge_predictions_NASDAQ.txt` or `surge_predictions_RUSSELL2000.txt` is missing (e.g. 0 surge candidates), `target_dirs[m]` is NOT set for that market.
- If at least one other market (e.g. KOSPI) exists, `target_dirs` is not empty, so fallback line 695 is NEVER reached.
- Consequently, `target_dirs` completely drops `NASDAQ` / `RUSSELL2000` from ALL subsequent merge routines (`merge_ensemble_predictions`, `merge_generic_strategy_files`, etc.).

#### Defect 2: Statistical Arbitrage Header Leak in `merge_generic_strategy_files()` (`trading_system/merge_predictions.py:433`)
In `merge_predictions.py`:
```python
433:            if line.startswith("Filters:") or line.startswith("Rank ") or line.startswith("---") or line.startswith("───"):
434:                prefix = line[:5]
435:                if not any(h.startswith(prefix) for h in header_lines):
436:                    header_lines.append(line + "\n")
437:                continue
438:            data_lines.append(line + "\n")
```
- **Direct observation**: `stat_arb_predictions.txt` is generated in `run_pipeline.py:2070` with header:
  `Pair                     Z-Score   Correlation    Beta/Hedge  Signal              `
- Because this line starts with `"Pair"`, it does NOT match `line.startswith("Rank ")` or `line.startswith("Filters:")`.
- It is erroneously appended to `data_lines` for every market, while the top of `stat_arb_predictions.txt` lacks the proper column header in `header_lines`.

#### Defect 3: Release Upload Omission in GitHub Actions (`.github/workflows/pipeline.yml:333–344`)
- In `.github/workflows/pipeline.yml` line 241, `lstm_predictions` is copied to `result_split/lstm_predictions_${{ matrix.target }}.txt`.
- However, in line 333 of `pipeline.yml` (the `gh release upload` loop), `lstm_predictions.txt` is missing from the list of uploaded release assets.

---

## 2. Logic Chain

1. **Premise 1 (File Generation)**: `run_pipeline.py` generates 31+ multi-factor strategy files using `_save_strategy_predictions_report()` and custom writers (`_write_rim_file`, `_write_stat_arb_file`, `_write_sector_file`, `_write_lstm_file`). Each writes both a unified `<strategy>.txt` and per-market split files `<strategy>_<MARKET>.txt`.
2. **Premise 2 (GHA Split & Download)**: GHA splits files per matrix target into `result-SP500`, `result-NASDAQ`, `result-RUSSELL2000`, `result-KOSPI`, `result-KOSDAQ` artifacts, and then downloads them all into `trading_system/result/`.
3. **Premise 3 (Merge Execution)**: `merge_predictions.py` is invoked to merge all split files into unified outputs (`trading_system/result/<strategy>.txt`).
4. **Deduction 1**: When `merge_predictions.py` fails to discover a market in `target_dirs` (due to Defect 1), or drops header schemas (due to Defect 2), the merged output files become truncated or missing market segments.
5. **Deduction 2**: When `generate_report.py` executes, it parses the merged outputs. Any missing market segments or unmerged strategies result in empty rows (`mkt_rows = []`), generating `<tr><td colspan="5" class="empty">데이터 없음</td></tr>` on the dashboard.
6. **Conclusion**: Robust multi-probe market discovery in `merge_predictions.py`, expanded header detection in `merge_generic_strategy_files()`, and a comprehensive 31-strategy unit test suite in `tests/test_merge_generic_strategies.py` are strictly required to guarantee 100% multi-market merge parity.

---

## 3. Caveats

1. **Read-Only Explorer Investigation**: This report is purely an investigation and architectural synthesis; no source or test files were modified during this investigation.
2. **Offline Fallback Data**: In offline developer environments without live external filing keys (DART/SEC) or full options chains, heuristic fallback proxy values (baseline 0.50 or historical median) ensure that non-empty rows are generated and merged across all 5 core markets.
3. **Extended Strategies (32-34)**: Extended strategies (`dual_correction_predictions.txt`, `index_rebalance_predictions.txt`, `overnight_gap_predictions.txt`) are merged cleanly by `merge_generic_strategy_files()`. They can be ingested by any future dashboard extension without merge schema changes.

---

## 4. Conclusion & Concrete Implementation Recommendations

### 4.1 Recommended Code Fixes in `trading_system/merge_predictions.py`

#### Recommendation 1: Robust Multi-Probe Market Discovery in `main()`
Modify `trading_system/merge_predictions.py` lines 684–702 to probe multiple candidate files or use glob pattern matching:

```python
    markets = KNOWN_MARKETS
    target_dirs: dict[str, Path] = {}
    for m in markets:
        # 1. Prefer market-specific split directory
        split_path = base_dir / f"result_{m}"
        if split_path.exists() and any(split_path.iterdir()):
            target_dirs[m] = split_path
            continue

        # 2. Check if market-suffixed files exist inside result_dir itself (multi-probe)
        if result_dir.exists():
            probes = [
                result_dir / f"surge_predictions_{m}.txt",
                result_dir / f"pipeline_result_{m}.txt",
                result_dir / f"ensemble_predictions_{m}.txt",
                result_dir / f"rim_predictions_{m}.txt",
                result_dir / f"sentiment_predictions_{m}.txt",
                result_dir / f"backtest_summary_{m}.json",
            ]
            if any(p.exists() for p in probes) or any(result_dir.glob(f"*_{m}.*")):
                target_dirs[m] = result_dir
```

#### Recommendation 2: Expand Header Line Matching in `merge_generic_strategy_files()`
Modify `trading_system/merge_predictions.py` lines 433–437:

```python
            # Header lines (Filters:, column headers with Rank/Pair/No./Symbol, divider dashes)
            if (line.startswith("Filters:") or line.startswith("Rank") or line.startswith("Pair") or
                line.startswith("No.") or line.startswith("Symbol") or line.startswith("---") or line.startswith("───")):
                prefix = line[:5]
                if not any(h.startswith(prefix) for h in header_lines):
                    header_lines.append(line + "\n")
                continue
            data_lines.append(line + "\n")
```

#### Recommendation 3: Standardize Darkpool Alias Merging
Ensure both `hft_order_flow_predictions.txt` and `darkpool_predictions.txt` are merged:
```python
    merge_generic_strategy_files(result_dir, target_dirs, "hft_order_flow_predictions.txt", "HFT Order Flow & Dark Pool Predictions")
    merge_generic_strategy_files(result_dir, target_dirs, "darkpool_predictions.txt", "Dark Pool & Off-Exchange Volume Divergence Predictions")
```

---

### 4.2 Comprehensive Test Plan for `tests/test_merge_generic_strategies.py`

Expand `tests/test_merge_generic_strategies.py` from 3 tests to a full parity test suite:

1. **Parameterized Parity Test Across ALL 31+ Strategies (`test_all_31_strategies_merge_parity`)**:
   - Iterates through all 31 strategy files (`rim_predictions.txt`, `sentiment_predictions.txt`, `earnings_tone_drift_predictions.txt`, `accruals_quality_predictions.txt`, `valueup_catalyst_predictions.txt`, `insider_buying_predictions.txt`, `stat_arb_predictions.txt`, `sector_predictions.txt`, `lstm_predictions.txt`, `mq_factor_predictions.txt`, etc.).
   - Generates 5 per-market files (`KOSPI`, `KOSDAQ`, `SP500`, `NASDAQ`, `RUSSELL2000`) with 2 distinct mock rows per market.
   - Executes `merge_generic_strategy_files()`.
   - Asserts:
     - Merged file exists and is non-empty.
     - Exact 1 Title header, 1 Date header, 1 Column header, 1 Divider.
     - All 10 data rows (2 per market * 5 markets) are present.
     - Korean company names (e.g. `삼성전자`, `SK하이닉스`) preserve UTF-8 encoding.
     - Downstream parser in `generate_report.py` parses all 10 rows with 100% success.

2. **Edge-Case Tests**:
   - **`test_merge_all_markets_empty_no_data`**: When all 5 market split files contain `"데이터 없음"`, merged file outputs exact `"데이터 없음\n"` and parser returns 0 rows without exception.
   - **`test_merge_partial_markets_data_and_empty`**: When 2 markets have valid data and 3 have `"데이터 없음"`, merged file includes only the valid rows and filters out `"데이터 없음"`.
   - **`test_merge_self_referencing_safety`**: When `target_dirs` points directly to `result_dir`, asserts existing files are not wiped or truncated.
   - **`test_market_discovery_multi_probe`**: Mocks a directory where `surge_predictions_NASDAQ.txt` is missing but `pipeline_result_NASDAQ.txt` exists, verifying `NASDAQ` is correctly discovered and included.
   - **`test_stat_arb_pair_header_preservation`**: Verifies `stat_arb_predictions.txt` with `Pair ...` column header deduplicates cleanly and places the header once at top.

---

## 5. Verification Method

To independently verify 100% strategy merge parity and test suite execution:

1. **Run Generic Strategy Merge Test Suite**:
   ```powershell
   .venv\Scripts\python.exe -m pytest tests/test_merge_generic_strategies.py -v
   ```
   *Expected*: 100% PASS with 0 failures or warnings.

2. **Run Report Generator & Parser Verification**:
   ```powershell
   .venv\Scripts\python.exe -m pytest tests/test_report_generator_hrp.py tests/test_challenger_rim_2_stress.py -v
   ```
   *Expected*: 100% PASS.

3. **Verify Full Pipeline Merge Script Standalone**:
   ```powershell
   .venv\Scripts\python.exe trading_system/merge_predictions.py
   ```
   *Expected*: Merges all prediction files cleanly and logs `All prediction files successfully merged.`

4. **Verify Report Generator HTML Build**:
   ```powershell
   .venv\Scripts\python.exe trading_system/generate_report.py --result-dir trading_system/result --out gh-pages/index.html
   ```
   *Expected*: Builds `gh-pages/index.html` with populated tables across all 5 markets.
