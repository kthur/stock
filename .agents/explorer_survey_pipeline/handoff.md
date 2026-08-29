# 31-Strategy Pipeline Data Quality, Normalization & Missingness Investigation Report

**Investigation Target**: 31-Strategy Multi-Factor Pipeline & Cross-Market Data Quality Audit (SP500, NASDAQ, RUSSELL2000, KOSPI, KOSDAQ)  
**Investigator**: Teamwork Explorer (`explorer_survey_pipeline`)  
**Date**: 2026-08-29  
**Status**: COMPLETE  

---

## 1. Observation

### 1.1 Pipeline Orchestration & Execution Flow
- **Orchestrator**: `trading_system/run_pipeline.py` (lines 2750–3450, 3770–3835)
  - Executes all 31 strategies concurrently or sequentially across 5 markets (`KOSPI`, `KOSDAQ`, `SP500`, `NASDAQ`, `RUSSELL2000`).
  - Merges strategy predictions into `scorer.calculate_ensemble_score()` with dynamic market regime weighting (2D US/KR Dual Regimes).
  - Saves individual prediction text reports (`*_predictions.txt`), `ensemble_predictions.txt`, and `strategy_data_coverage_report.txt`.
  - Generates the GitHub Pages interactive dashboard (`index.html`).

### 1.2 Identified Code Observations & Flaws

#### A. Strategy 9 (RIM Valuation) Formatting & Filter Reason Handling
- **File**: `trading_system/run_pipeline.py` (lines 2772–2800, `_write_rim_file`)
```python
# Verbatim from run_pipeline.py:2780-2795
f.write(
    f"{rank:<5} {sym:<12} {name:<20} {mkt:<10} "
    f"{p_str:<12} {iv_str:<12} {disc:<10.1f}% "
    f"{roe_str:<10} {req_r:<10.1f}% {s_str:<10.2f} "
    f"{score_pct:<10.1f}% {status}\n"
)
```
- **Flaw**: When `discount_ratio` or `score_pct` is `np.nan`, `f"{disc:<10.1f}%"` formats as `"       nan%"`.
- **File**: `trading_system/src/core/rim_valuation.py` (lines 650–675)
```python
# Verbatim from rim_valuation.py:650-660
invalid_mask = np.isnan(bps_arr) | (bps_arr <= 0) | is_distress | is_pref
# When BPS is missing/NaN, rim_filter_reason is left empty or not populated with a descriptive code
```
- When BPS is missing, `rim_filter_reason` was left as `""` instead of `'NO_FUNDAMENTAL_DATA'` or `'CAPITAL_IMPAIRMENT'`.

#### B. Strategy Column Name Discrepancy in `vcp_rule` Strategy
- **File**: `trading_system/src/ai/ml_strategy_adapters.py` (line 180)
```python
@register_strategy(
    StrategyMeta(
        strategy_id="vcp_rule",
        display_name="VCP Rule Pattern",
        score_column="vcp_score",   # <-- DISCREPANCY: StrategyMeta registered 'vcp_score'
        category="technical",
        output_file="vcp_patterns.txt",
    )
)
```
- **File**: `trading_system/src/ai/ensemble_scorer.py` (line 2116)
```python
('vcp_rule', 'vcp_rule_score'),     # <-- EnsembleScoringEngine outputs 'vcp_rule_score'
```
- **Flaw**: `StrategyCoverageAnalyzer` queried `col_map.get('vcp_rule')` which returned `'vcp_score'`. Because `target_df` contains `'vcp_rule_score'`, `coverage_analyzer` failed to find the column and incorrectly reported **0.0% coverage (0 valid / 948 missing)** for `vcp_rule`.

#### C. Symbol Key Matching & Missingness Classification in `StrategyCoverageAnalyzer`
- **File**: `trading_system/src/analysis/coverage_analyzer.py` (lines 154–175)
```python
for sym in missing_syms:
    sym_str = str(sym)
    p_df = prices_dict.get(sym_str) if prices_dict else None
    if p_df is None and prices_dict:
        if sym_str.isdigit():
            p_df = prices_dict.get(sym_str.zfill(6))
        if p_df is None:
            p_df = prices_dict.get(sym)

    has_price = (p_df is not None and len(p_df) >= 20)

    if not has_price:
        no_price_cnt += 1
    elif strat in ['rim_valuation', 'rim'] and self._has_symbol_fundamental_data(features_df, sym_str):
        low_eq_cnt += 1
    elif strat in [...] and not self._has_symbol_fundamental_data(features_df, sym_str):
        no_fund_cnt += 1
    else:
        other_cnt += 1
```
- **Flaw**: In `ensemble_df`, Korean symbols frequently carry `.KS` or `.KQ` suffixes (e.g. `'005930.KS'`). 
  - `sym_str.isdigit()` evaluates to `False` for `'005930.KS'`.
  - `prices_dict` lookup failed because keys were stripped `'005930'`.
  - As a result, `has_price` evaluated to `False` for valid symbols, wrongly accumulating into `no_price_cnt` and outputting `INSUFFICIENT_PRICE_HISTORY` as the primary reason for all missing strategies.
  - In `_has_symbol_fundamental_data(features_df, sym_str)`, suffix stripping (`sym_str.split('.')[0]`) was similarly missing.

#### D. Strategy Coverage & Missingness Reason Granularity
- **File**: `trading_system/src/analysis/coverage_analyzer.py` (lines 185–200)
- `other_cnt` was grouped into `STRATEGY_SIGNAL_NEUTRAL` for event-driven, sentiment, and catalyst strategies.
- Non-disclosed filings (DART/SEC) or missing transcripts should be categorized as `NO_CORPORATE_FILING`, `NO_INSIDER_FILING`, and `NO_EARNINGS_TRANSCRIPT`.

---

## 2. Logic Chain

1. **Pipeline Execution Consistency**:
   - `run_pipeline.py` executes 31 core strategies across all 5 markets.
   - For all strategies, output DataFrames must have consistent column naming and types matching `StrategyRegistry` and `EnsembleScoringEngine`.
   - When strategy scores are generated, missing data falls into two intentional design patterns:
     - **Explicit NaN Propagation**: Required for dynamic weight redistribution in `EnsembleScoringEngine` (e.g. RIM valuation, options IV skew, accruals quality, sentiment, insider buying, stat-arb).
     - **Neutral Fallback (0.50)**: Used where a neutral baseline is appropriate without penalizing or tilting the stock (e.g. ARM revision, CARD divergence, LATR tail risk, microstructure, darkpool).

2. **Reporting & UI Layer Integrity**:
   - The reporting layer (`_write_rim_file`, `PipelineReporter`, `generate_report.py`) consumes the DataFrames produced by the engines.
   - If missing values (`np.nan`) are formatted using raw string interpolations (`f"{val:.1f}%"`), python outputs `"nan%"`.
   - The reporting and UI layer must check `pd.isna()` and output formatted badges (`N/A`, `재무데이터미비`, `이익질부적합`, `우선주제외`).

3. **Coverage Reason Diagnostic Accuracy**:
   - `StrategyCoverageAnalyzer` exists to diagnose *why* data is missing per strategy and per market.
   - Robust symbol normalization (stripping `.KS`/`.KQ`, applying `zfill(6)` for digits) is required so symbol keys match across `prices_dict`, `features_df`, and `ensemble_df`.
   - Matching `StrategyMeta.score_column` to `vcp_rule_score` restores accurate coverage counting for `vcp_rule`.

---

## 3. Caveats

1. **Market Scope Limitations**:
   - **Options Strategies** (`iv_skew`, `gamma_squeeze`): Real-time options chains are primarily available for US equities (`SP500`, `NASDAQ`, `RUSSELL2000`). For Korean equities, fallback proxy volatility and price skewness are applied.
   - **Dark Pool Strategy** (`darkpool`): FINRA TRF volume data applies to US markets; KRX uses tick/volume accumulation proxies.
   - **DART Filings** (`event_driven`, `insider_buying`, `sentiment`): Requires `DART_API_KEY`. In environments without the API key, fallback price/volume breakout catalyst detection is used.
2. **Dynamic Weight Renormalization Dependency**:
   - Do NOT replace `np.nan` with `0.50` in engines designed for dynamic weighting (e.g. `rim_valuation.py`, `accruals_quality.py`, `insider_buying.py`), as doing so would dilute active weights. `EnsembleScoringEngine` relies on `NaN` to detect missing strategies and dynamically re-normalize active weights to sum to 100%.

---

## 4. Conclusion & Concrete Proposals

### Summary Table of All 31 Strategies

| # | Strategy ID | Engine Class | Score Column | Missing Data Pattern | Primary Missing Reason Code |
|---|-------------|--------------|--------------|----------------------|------------------------------|
| 1 | `regression` | `OnDevicePredictionModel` | `reg_score` | Insufficient price (<65d) -> NaN | `INSUFFICIENT_PRICE_HISTORY` |
| 2 | `surge` | `OnDevicePredictionModel` | `surge_score` | Insufficient price (<65d) -> NaN | `INSUFFICIENT_PRICE_HISTORY` |
| 3 | `lead_lag` | `OnDevicePredictionModel` | `ll_score` | Uncorrelated / Insufficient price -> NaN | `NO_LEAD_LAG_LEADER` |
| 4 | `vcp_rule` | `VCPPatternDetector` | `vcp_rule_score` | No contraction / <50d -> NaN | `NO_VCP_PATTERN` |
| 5 | `vcp_ml` | `VCPSurgePredictor` | `vcp_ml_score` | Insufficient price (<60d) -> NaN | `INSUFFICIENT_PRICE_HISTORY` |
| 6 | `lstm` | `OnDevicePredictionModel` | `lstm_score` | Insufficient price (<60d) -> NaN | `INSUFFICIENT_PRICE_HISTORY` |
| 7 | `stat_arb` | `StatisticalArbitrageEngine` | `stat_arb_score` | No cointegrated pair -> NaN | `NO_COINTEGRATED_PAIR` |
| 8 | `sector_rotation` | `SectorRotationEngine` | `sector_score` | Insufficient price (<20d) -> NaN | `INSUFFICIENT_PRICE_HISTORY` |
| 9 | `rim_valuation` | `RIMValuationEngine` | `rim_score` | Missing BPS/Distress/Preferred -> NaN | `NO_FUNDAMENTAL_DATA` / `LOW_EARNINGS_QUALITY` |
| 10 | `event_driven` | `EventDrivenEngine` | `event_score` | No disclosure / breakout -> 0.50 | `STRATEGY_SIGNAL_NEUTRAL` |
| 11 | `mq_factor` | `MQFactorEngine` | `mq_score` | Insufficient price (<250d) -> NaN | `INSUFFICIENT_PRICE_HISTORY` |
| 12 | `iv_skew` | `IVSkewEngine` | `iv_skew_score` | No options chain / <20d -> NaN | `NO_OPTIONS_CHAIN` |
| 13 | `order_flow` | `OrderFlowEngine` | `order_flow_score` | Insufficient price (<20d) -> NaN | `INSUFFICIENT_PRICE_HISTORY` |
| 14 | `short_term_reversal` | `ShortTermReversalEngine` | `reversal_score` | Insufficient price (<20d) -> NaN | `INSUFFICIENT_PRICE_HISTORY` |
| 15 | `arm_factor` | `ARMFactorEngine` | `arm_score` | Missing revision -> 0.50 fallback | `NO_FUNDAMENTAL_DATA` / `STRATEGY_SIGNAL_NEUTRAL` |
| 16 | `card_factor` | `CARDFactorEngine` | `card_score` | Missing macro -> 0.50 fallback | `STRATEGY_SIGNAL_NEUTRAL` |
| 17 | `latr_factor` | `LATRFactorEngine` | `latr_score` | Missing price -> 0.50 fallback | `INSUFFICIENT_PRICE_HISTORY` |
| 18 | `inst_foreign_sector`| `InstForeignSectorEngine`| `inst_foreign_sector_score` | Insufficient price (<20d) -> NaN | `INSUFFICIENT_PRICE_HISTORY` |
| 19 | `supply_chain` | `SupplyChainEngine` | `supply_chain_score` | No customer link -> 0.50 fallback | `NO_SUPPLY_CHAIN_MAPPING` |
| 20 | `sentiment` | `DARTSECSentimentEngine` | `sentiment_score` | No filing text -> NaN | `NO_CORPORATE_FILING` |
| 21 | `factor_neutralized`| `MultiFactorNeutralizerEngine` | `factor_neutralized_score` | Imputed median -> [0, 1] | `STRATEGY_SIGNAL_NEUTRAL` |
| 22 | `vol_target` | `VolTargetingEngine` | `vol_target_score` | Default 25% vol -> [0, 1] | `STRATEGY_SIGNAL_NEUTRAL` |
| 23 | `microstructure` | `MicrostructureImbalanceEngine` | `microstructure_score` | Missing price -> 0.50 fallback | `INSUFFICIENT_PRICE_HISTORY` |
| 24 | `accruals_quality` | `AccrualsQualityEngine` | `accruals_quality_score` | Missing NI/OCF -> NaN | `NO_FUNDAMENTAL_DATA` |
| 25 | `short_squeeze` | `ShortInterestSqueezeEngine` | `short_squeeze_score` | Missing short/price -> NaN / Proxy | `INSUFFICIENT_PRICE_HISTORY` |
| 26 | `valueup_catalyst`| `ValueUpCatalystEngine` | `valueup_catalyst_score` | Missing PBR -> NaN | `NO_FUNDAMENTAL_DATA` |
| 27 | `trend_efficiency` | `TrendEfficiencyEngine` | `trend_efficiency_score` | Insufficient price (<21d) -> NaN | `INSUFFICIENT_PRICE_HISTORY` |
| 28 | `gamma_squeeze` | `OptionsGammaSqueezeEngine` | `gamma_squeeze_score` | Missing options -> 0.50 proxy | `NO_OPTIONS_CHAIN` |
| 29 | `insider_buying` | `InsiderBuyingEngine` | `insider_buying_score` | No insider filing -> NaN | `NO_INSIDER_FILING` |
| 30 | `earnings_tone_drift`| `EarningsToneDriftEngine` | `earnings_tone_drift_score` | No transcript -> NaN | `NO_EARNINGS_TRANSCRIPT` |
| 31 | `darkpool` | `DarkPoolTrackerEngine` | `darkpool_score` | Missing ATS -> 0.50 proxy | `NON_US_MARKET_SCOPE` |

---

### Implementation Action Plan

#### 1. Fix `_write_rim_file` in `trading_system/run_pipeline.py`
- Replace raw `f"{disc:.1f}%"` and `f"{score_pct:.1f}%"` with safe formatters checking `np.isfinite()`.
- If NaN or filtered, display user-friendly Korean badges (`N/A`, `재무데이터미비`, `이익질부적합`, `우선주제외`).

#### 2. Update `StrategyMeta` for `vcp_rule` in `trading_system/src/ai/ml_strategy_adapters.py`
- Change `score_column="vcp_score"` to `score_column="vcp_rule_score"`.

#### 3. Enhance Symbol Key Matching & Missingness Reasons in `StrategyCoverageAnalyzer`
- Normalize symbols by extracting base code (`sym_str.split('.')[0]`) and matching against both stripped and raw keys in `prices_dict` and `features_df`.
- Refine missing reason assignment to distinguish `NO_CORPORATE_FILING`, `NO_INSIDER_FILING`, `NO_EARNINGS_TRANSCRIPT`, `NO_LEAD_LAG_LEADER`, and `NO_SUPPLY_CHAIN_MAPPING`.

#### 4. Dashboard Badge & Filter Rendering (`index.html` via `generate_report.py`)
- Enhance HTML generator to display status badges (`정상`, `재무미비`, `수급중립`, `N/A`) with color coding instead of raw `nan` strings.

---

## 5. Verification Method

To independently verify these findings:

1. **Verify Strategy Registry Score Columns**:
   ```bash
   .venv/Scripts/python.exe -c "from src.core.strategy_registry import get_registry; reg = get_registry(); reg.auto_discover(['src.core', 'src.ai']); print('Count:', len(reg.get_all_ids())); print('Score cols:', reg.get_all_score_columns())"
   ```
2. **Run Existing Test Suite for Coverage & Normalization**:
   ```bash
   .venv/Scripts/pytest tests/test_kst_and_coverage_reasoning.py tests/test_r3_coverage_and_universe.py -v
   ```
3. **Inspect Output Files for `nan%` strings**:
   ```powershell
   Select-String -Path trading_system\result\*.txt -Pattern "nan%"
   ```
