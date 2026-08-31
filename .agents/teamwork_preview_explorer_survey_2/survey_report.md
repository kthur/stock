# Survey Report: 31-Strategy Canonical Sequence Unification (Requirement R2)

## Executive Summary

This survey report provides a comprehensive investigation of the **31-Strategy Multi-Factor Engine** architecture and its representation across the entire codebase (`AGENTS.md`, `trading_system/run_pipeline.py`, `src/ai/ensemble_scorer.py`, `src/pipeline/reporter.py`, `generate_report.py`, `trading_system/scripts/verify_gha_artifacts.py`, `skills/gha-artifact-verifier/SKILL.md`, `merge_predictions.py`, `correlation_monitor.py`, and `gh-pages/index.html`).

We established the **Canonical 31-Strategy Sequence (1 to 31)**, audited all naming conventions, score column mappings, text output artifacts, dashboard tabs, and verification scripts, and cataloged 5 major classes of discrepancies that currently exist across modules.

---

## 1. Canonical 31-Strategy Master Specification (1 to 31)

The unified canonical sequence, naming convention, score columns, and primary artifact mappings are established as follows:

| # | Canonical Strategy ID (`s_id`) | Display Name (KO / EN) | Category | Score Column | Primary Artifact File | Horizon Tier |
|---|---|---|---|---|---|---|
| **1** | `regression` | XGBoost 회귀 / XGBoost Regression | AI 예측 (ML) | `reg_score` (`expected_return_5d` / `20`) | `pipeline_result.txt` | Slow (1M~1Y) |
| **2** | `surge` | Surge 분류기 / Surge Classifier | AI 예측 (ML) | `surge_score` (`surge_20d`) | `surge_predictions.txt` | Medium (5D~20D) |
| **3** | `lead_lag` | Lead-Lag 후행주 / Lead-Lag Shift (+1d US) | 모멘텀/수급 | `ll_score` (`lead_lag_score`) | `lead_lag_predictions.txt` | Medium (5D~20D) |
| **4** | `vcp_rule` | VCP 패턴 (Rule) / VCP Rule Detector | 기술적 패턴 | `vcp_rule_score` (`vcp_score`) | `vcp_patterns.txt` | Medium (5D~20D) |
| **5** | `vcp_ml` | VCP ML 급등예측 / VCP ML Predictor | AI 예측 (ML) | `vcp_ml_score` (`vcp_20d`) | `vcp_ml_predictions.txt` | Medium (5D~20D) |
| **6** | `lstm` | Strict Causal LSTM / Causal LSTM Deep Learning | 딥러닝 | `lstm_score` (`lstm_return_20d`) | `lstm_predictions.txt` | Medium (5D~20D) |
| **7** | `stat_arb` | Stat-Arb 차익거래 / Stat-Arb Cointegration | 차익거래 | `stat_arb_score` | `stat_arb_predictions.txt` | Medium (5D~20D) |
| **8** | `sector_rotation` | Sector Rotation / Sector Relative Momentum | 모멘텀/수급 | `sector_score` | `sector_predictions.txt` | Medium (5D~20D) |
| **9** | `rim_valuation` | RIM Valuation / Residual Income Model | 가치평가 | `rim_score` | `rim_predictions.txt` | Slow (1M~1Y) |
| **10** | `event_driven` | Event-Driven 촉매 / Event-Driven Catalyst | 촉매/공시 | `event_score` | `event_driven_predictions.txt` | Medium (5D~20D) |
| **11** | `mq_factor` | MQ Factor (퀄리티) / Momentum Quality Factor | 퀄리티 | `mq_score` | `mq_factor_predictions.txt` | Slow (1M~1Y) |
| **12** | `iv_skew` | Options IV Skew / Options Put/Call IV Skew | 파생/역발상 | `iv_skew_score` | `iv_skew_predictions.txt` | Slow (1M~1Y) |
| **13** | `order_flow` | Order Flow 수급 / Order Flow Imbalance (MFI) | 수급/유동성 | `order_flow_score` | `order_flow_predictions.txt` | Fast (1D~3D) |
| **14** | `short_term_reversal` | ST Reversal 단기반등 / Short-Term Mean Reversal | 평균회귀 | `reversal_score` | `short_term_reversal_predictions.txt` | Fast (1D~3D) |
| **15** | `arm_factor` | ARM Factor (컨센서스) / Analyst Revision Momentum | 컨센서스 | `arm_score` | `arm_factor_predictions.txt` | Slow (1M~1Y) |
| **16** | `card_factor` | CARD Factor (크로스에셋) / Cross-Asset Divergence | 크로스에셋 | `card_score` | `card_factor_predictions.txt` | Slow (1M~1Y) |
| **17** | `latr_factor` | LATR Factor (꼬리위험) / Liquidity Tail Risk | 꼬리위험 | `latr_score` | `latr_factor_predictions.txt` | Slow (1M~1Y) |
| **18** | `inst_foreign_sector` | 외인/투신 수급 / Inst & Foreign Sector Flow | 수급/유동성 | `inst_foreign_sector_score` | `inst_foreign_sector_predictions.txt` | Medium (5D~20D) |
| **19** | `supply_chain` | Supply Chain 공급망 / Supply Chain Momentum | 공급망 | `supply_chain_score` | `supply_chain_predictions.txt` | Medium (5D~20D) |
| **20** | `sentiment` | NLP Sentiment (감성) / FinBERT Sentiment Catalyst | NLP 감성 | `sentiment_score` | `sentiment_predictions.txt` | Medium (5D~20D) |
| **21** | `factor_neutralized` | Factor Neutralized / Fama-French Style Neutralizer | 순수 알파 | `factor_neutralized_score` | `factor_neutralized_predictions.txt` | Slow (1M~1Y) |
| **22** | `vol_target` | Vol Targeting / Dynamic Volatility Targeting | 변동성 관리 | `vol_target_score` | `vol_target_predictions.txt` | Slow (1M~1Y) |
| **23** | `microstructure` | Microstructure 호가 / Order Book Imbalance | 미시구조 | `microstructure_score` | `microstructure_predictions.txt` | Fast (1D~3D) |
| **24** | `accruals_quality` | Accruals Quality (발생액) / Accruals Quality Anomaly | 회계 품질 | `accruals_quality_score` | `accruals_quality_predictions.txt` | Slow (1M~1Y) |
| **25** | `short_squeeze` | Short Squeeze 촉매 / Short Interest & Squeeze | 공매도 | `short_squeeze_score` | `short_squeeze_predictions.txt` | Medium (5D~20D) |
| **26** | `valueup_catalyst` | Value-Up Yield (주주환원) / Value-Up & Shareholder Yield | 주주환원 | `valueup_catalyst_score` | `valueup_catalyst_predictions.txt` | Slow (1M~1Y) |
| **27** | `trend_efficiency` | Trend Efficiency 추세 / Kaufman Trend Efficiency | 추세 필터 | `trend_efficiency_score` | `trend_efficiency_predictions.txt` | Medium (5D~20D) |
| **28** | `gamma_squeeze` | Gamma Squeeze (감마) / Options Gamma Squeeze | 파생/옵션 | `gamma_squeeze_score` | `gamma_squeeze_predictions.txt` | Medium (5D~20D) |
| **29** | `insider_buying` | Insider Buying (내부자) / Insider Buying Catalyst | 내부자 | `insider_buying_score` | `insider_buying_predictions.txt` | Medium (5D~20D) |
| **30** | `darkpool` | Darkpool & HFT Flow / HFT Order Flow & Dark Pool | 고빈도/다크풀 | `darkpool_score` (`hft_score`) | `darkpool_predictions.txt` (or `hft_order_flow_predictions.txt`) | Fast (1D~3D) |
| **31** | `earnings_tone_drift` | Tone Drift 어닝어조 / Earnings Tone Drift NLP | NLP 어조 | `earnings_tone_drift_score` | `earnings_tone_drift_predictions.txt` | Slow (1M~1Y) |

---

## 2. In-Depth Analysis of Discrepancies Across Modules

### 2.1. Ordering Discrepancy for Strategies #30 and #31
- **Observation**:
  - `AGENTS.md` (lines 42-43) lists #30 as "Earnings Tone Drift" and #31 as "High-Frequency Execution" (`darkpool_hft`).
  - In `run_pipeline.py` (lines 3222-3223), STRATEGY_REGISTRY numbers `earnings_tone_drift` as Strategy 30 and `darkpool` as Strategy 31.
  - BUT in `generate_report.py` `STRATEGY_METADATA` (lines 1403-1404):
    - Strategy 30 is `darkpool` ("Darkpool & HFT Flow")
    - Strategy 31 is `earnings_tone_drift` ("Tone Drift 어닝어조")
  - In `correlation_monitor.py` `ALL_31_STRATEGIES` (lines 22-23), `darkpool` is 30th (index 29) and `earnings_tone_drift` is 31st (index 30).
  - In `run_pipeline.py` `_STRAT_DISPLAY_MAP` (lines 4075-4076) and table columns header (line 4108): `darkpool` appears before `earnings_tone_drift` (`... | Darkpool | ToneDrift`).
- **Impact**: Slight contradiction between `AGENTS.md` table (#30 Tone Drift, #31 HFT) and the internal order in `generate_report.py` / `ensemble_predictions.txt` table columns.
- **Remediation**: Align `AGENTS.md`, `run_pipeline.py`, `generate_report.py`, and `verify_gha_artifacts.py` so that **#30 = Darkpool & HFT Flow (`darkpool`)** and **#31 = Earnings Tone Drift (`earnings_tone_drift`)** (or strictly synchronize both).

### 2.2. GHA Artifact Verification Coverage Gap (23 vs 31 strategies)
- **Observation**:
  - `trading_system/scripts/verify_gha_artifacts.py` (lines 29-35) defines:
    ```python
    STRATEGIES = [
        "surge", "vcp_ml", "regression", "vcp", "lead_lag", "lstm",
        "stat_arb", "sector", "rim", "event_driven", "mq_factor",
        "iv_skew", "order_flow", "short_term_reversal", "arm_factor",
        "card_factor", "latr_factor", "inst_foreign_sector",
        "supply_chain", "sentiment", "factor_neutralized", "vol_target", "microstructure"
    ]
    ```
  - It only validates 23 strategies, starting in non-canonical order (`surge`, `vcp_ml`, `regression`, `vcp`, `lead_lag`).
  - Strategies 24 to 31 (`accruals_quality`, `short_squeeze`, `valueup_catalyst`, `trend_efficiency`, `gamma_squeeze`, `insider_buying`, `darkpool`, `earnings_tone_drift`) are **completely omitted** from `verify_market_strategies()`, `files_map`, and `verify_gh_pages()`.
  - In `skills/gha-artifact-verifier/SKILL.md` (lines 14-39), table lists 23 numbered items and groups 24-31 as a single entry "Extended Alpha Factors".
- **Remediation**:
  - Update `verify_gha_artifacts.py` `STRATEGIES` list to contain all 31 strategies in exact canonical sequence (1 to 31).
  - Add check functions and file mappings for strategies 24-31 (`accruals_quality_predictions.txt`, `short_squeeze_predictions.txt`, `valueup_catalyst_predictions.txt`, `trend_efficiency_predictions.txt`, `gamma_squeeze_predictions.txt`, `insider_buying_predictions.txt`, `darkpool_predictions.txt`, `earnings_tone_drift_predictions.txt`).
  - Update `verify_gh_pages` `panels_to_check` to verify all 31 strategy HTML panels.

### 2.3. Dashboard Tabs Scope Discrepancy (31 vs 34 tabs in `generate_report.py`)
- **Observation**:
  - `generate_report.py` `STRATEGY_METADATA` (lines 1373-1405) defines 31 strategies.
  - However, in Row 2 strategy navigation bar (`<nav class="tabs">`, lines 3727-3762) and panel containers (lines 4078-4106), 3 extra tabs are appended:
    - Tab 32: `dualcorrection` (`Dual Correction`)
    - Tab 33: `indexrebalance` (`Index Rebalance`)
    - Tab 34: `overnightgap` (`Overnight Gap`)
  - These 3 extra strategies are auxiliary experimental modules that are not part of the 31-strategy ensemble or `AGENTS.md`.
- **Remediation**: Ensure the 31 canonical strategy tabs are cleanly numbered 1 to 31, and if auxiliary modules (32-34) are retained, separate them into an auxiliary/experimental section or prune them to preserve strict 31-strategy parity.

### 2.4. Key & Alias Divergence Across Subsystems
- **Observation**:
  Across `run_pipeline.py`, `generate_report.py`, `correlation_monitor.py`, and `merge_predictions.py`, heterogeneous short keys are used:
  - `vcp` vs `vcp_rule`
  - `sector` vs `sector_rotation`
  - `rim` vs `rim_valuation`
  - `event` vs `event_driven`
  - `mq` vs `mq_factor`
  - `reversal` vs `short_term_reversal`
  - `arm` vs `arm_factor`
  - `card` vs `card_factor`
  - `latr` vs `latr_factor`
  - `ifs` vs `inst_foreign_sector`
  - `supplychain` vs `supply_chain`
  - `neutralized` vs `factor_neutralized`
  - `voltarget` vs `vol_target`
  - `accruals` vs `accruals_quality`
  - `shortsqueeze` vs `short_squeeze`
  - `valueup` vs `valueup_catalyst` vs `value_up`
  - `trendeff` vs `trend_efficiency`
  - `gammasqueeze` vs `gamma_squeeze`
  - `insider` vs `insider_buying`
  - `darkpool` vs `darkpool_hft` vs `hft_order_flow`
  - `tonedrift` vs `tone_drift` vs `earnings_tone_drift`
- **Remediation**: Establish a canonical key lookup table in `src/core/strategy_registry.py` and `generate_report.py` that maps all aliases bi-directionally to standard `s_id`.

### 2.5. Text Prediction File Suffix & Standalone Exporter Integration
- **Observation**:
  - `run_pipeline.py` (lines 3200-3231) generates prediction text files for factors 10..31 in the parallel pool (`event_driven_predictions.txt`, `mq_factor_predictions.txt`, etc.).
  - `src/pipeline/reporter.py` (lines 40-92) currently only exports `ensemble_predictions.txt` and `strategy_data_coverage_report.txt`.
  - Strategy 30 uses two filenames interchangeably: `darkpool_predictions.txt` and `hft_order_flow_predictions.txt`.
  - `run_pipeline.py` line 4338 (`verification_files`) checks only 13 files, skipping strategies 10-14, 19-31.
- **Remediation**: Update `run_pipeline.py` `verification_files` to verify all 31 strategy prediction files (plus `ensemble_predictions.txt`, `strategy_data_coverage_report.txt`, `portfolio_allocation.txt`). Standardize Strategy 30 to `darkpool_predictions.txt` (maintaining symlink/alias compatibility for `hft_order_flow_predictions.txt`).

---

## 3. Detailed Per-Strategy Cross-Reference Matrix

| # | Strategy Key (`s_id`) | `AGENTS.md` Name | `run_pipeline.py` Key | `generate_report.py` tab_id | `verify_gha_artifacts.py` Status | Output Text File |
|---|---|---|---|---|---|---|
| 1 | `regression` | XGBoost 회귀 | `res_df` | `regression` | Checked (#3) | `pipeline_result.txt` |
| 2 | `surge` | Surge 분류기 | `surge_df` | `surge` | Checked (#1) | `surge_predictions.txt` |
| 3 | `lead_lag` | Lead-Lag | `lead_lag_df` | `leadlag` | Checked (#5) | `lead_lag_predictions.txt` |
| 4 | `vcp_rule` | VCP 패턴 | `vcp_results` | `vcp` | Checked (#4 as `vcp`) | `vcp_patterns.txt` |
| 5 | `vcp_ml` | VCP ML | `vcp_ml_df` | `vcpml` | Checked (#2) | `vcp_ml_predictions.txt` |
| 6 | `lstm` | Strict Causal LSTM | `lstm` | `lstm` | Checked (#6) | `lstm_predictions.txt` |
| 7 | `stat_arb` | Stat-Arb Cointegration | `stat_arb_df` | `stat-arb` | Checked (#7) | `stat_arb_predictions.txt` |
| 8 | `sector_rotation` | Sector Rotation | `sector_df` | `sector` | Checked (#8 as `sector`) | `sector_predictions.txt` |
| 9 | `rim_valuation` | RIM Valuation | `rim_df` | `rim` | Checked (#9 as `rim`) | `rim_predictions.txt` |
| 10 | `event_driven` | Event-Driven | `event` | `event` | Checked (#10) | `event_driven_predictions.txt` |
| 11 | `mq_factor` | Momentum Quality (MQ) | `mq` | `mq` | Checked (#11) | `mq_factor_predictions.txt` |
| 12 | `iv_skew` | Options IV Skew | `iv_skew` | `iv` | Checked (#12) | `iv_skew_predictions.txt` |
| 13 | `order_flow` | Order Flow Imbalance | `order_flow` | `flow` | Checked (#13) | `order_flow_predictions.txt` |
| 14 | `short_term_reversal` | Short-Term Reversal | `reversal` | `reversal` | Checked (#14) | `short_term_reversal_predictions.txt` |
| 15 | `arm_factor` | Analyst Revision Momentum (ARM) | `arm` | `arm` | Checked (#15) | `arm_factor_predictions.txt` |
| 16 | `card_factor` | Cross-Asset Regime Divergence (CARD) | `card` | `card` | Checked (#16) | `card_factor_predictions.txt` |
| 17 | `latr_factor` | Liquidity-Adjusted Tail Risk (LATR) | `latr` | `latr` | Checked (#17) | `latr_factor_predictions.txt` |
| 18 | `inst_foreign_sector` | Inst & Foreign Sector | `inst_foreign_sector` | `ifs` | Checked (#18) | `inst_foreign_sector_predictions.txt` |
| 19 | `supply_chain` | Supply Chain Momentum | `supply_chain` | `supplychain` | Checked (#19) | `supply_chain_predictions.txt` |
| 20 | `sentiment` | NLP Sentiment Catalyst | `sentiment` | `sentiment` | Checked (#20) | `sentiment_predictions.txt` |
| 21 | `factor_neutralized` | Multi-Factor Style Neutralizer | `factor_neutralized` | `neutralized` | Checked (#21) | `factor_neutralized_predictions.txt` |
| 22 | `vol_target` | Dynamic Volatility Targeting | `vol_target` | `voltarget` | Checked (#22) | `vol_target_predictions.txt` |
| 23 | `microstructure` | Microstructure Imbalance | `microstructure` | `microstructure` | Checked (#23) | `microstructure_predictions.txt` |
| 24 | `accruals_quality` | Accruals Quality Anomaly | `accruals_quality` | `accruals` | ⚠️ MISSING | `accruals_quality_predictions.txt` |
| 25 | `short_squeeze` | Short Interest & Squeeze | `short_squeeze` | `shortsqueeze` | ⚠️ MISSING | `short_squeeze_predictions.txt` |
| 26 | `valueup_catalyst` | Value-Up & Shareholder Yield | `valueup_catalyst` | `valueup` | ⚠️ MISSING | `valueup_catalyst_predictions.txt` |
| 27 | `trend_efficiency` | Kaufman Trend Efficiency | `trend_efficiency` | `trendeff` | ⚠️ MISSING | `trend_efficiency_predictions.txt` |
| 28 | `gamma_squeeze` | Gamma Squeeze | `gamma_squeeze` | `gammasqueeze` | ⚠️ MISSING | `gamma_squeeze_predictions.txt` |
| 29 | `insider_buying` | Insider Buying | `insider_buying` | `insider` | ⚠️ MISSING | `insider_buying_predictions.txt` |
| 30 | `darkpool` | High-Frequency Execution / Darkpool | `darkpool` | `darkpool` | ⚠️ MISSING | `darkpool_predictions.txt` |
| 31 | `earnings_tone_drift` | Earnings Tone Drift | `earnings_tone_drift` | `tonedrift` | ⚠️ MISSING | `earnings_tone_drift_predictions.txt` |

---

## 4. Proposed Implementation Architecture for Requirement R2

To satisfy Requirement R2 with complete end-to-end consistency:

1. **Central Strategy Definition**:
   Ensure `src/core/strategy_registry.py` and `generate_report.py` share the exact 31 canonical strategy definitions (IDs 1..31).
2. **`run_pipeline.py` Synchronization**:
   - Order pipeline execution logs and progress indicators sequentially from Strategy 1 to Strategy 31.
   - Expand `verification_files` list to include all 31 strategy `.txt` files.
3. **`verify_gha_artifacts.py` & SKILL.md Standardization**:
   - Update `STRATEGIES` list to 31 items in exact canonical order 1..31.
   - Include validation check methods for strategies 24..31.
   - Update `verify_gh_pages()` to validate all 31 tab panels.
4. **`generate_report.py` Dashboard Alignment**:
   - Align `<nav class="tabs">` buttons and tab panel generation to display the 31 canonical strategies numbered 1 to 31 with matching Korean labels, icons, and filter panels.
   - Harmonize tab IDs and alias resolution to prevent broken links or navigation mismatch.
