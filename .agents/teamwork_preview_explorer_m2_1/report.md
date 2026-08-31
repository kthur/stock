# Milestone 2 Investigation Report: 31-Strategy Canonical Sequence Unification (R2)

**Explorer**: `teamwork_preview_explorer_m2_1`  
**Date**: 2026-09-01 (KST)  
**Target Milestone**: Milestone 2 (F03, F04, F05)  
**Corpus / Working Directory**: `d:\Finance\code\stock`  

---

## 1. Executive Summary

Milestone 2 establishes a single, deterministic **Canonical Strategy Master Sequence (1~31)** across the entire trading pipeline, artifact verification layer, CI/CD workflows, documentation, and reporting dashboards. 

Our investigation confirmed the following key findings:
1. **Canonical Strategy Order (1~31)**:
   - Strategies 1~29 are already consistently ordered across the codebase.
   - **Strategy 30** must be canonically designated as **HFT Order Flow & Dark Pool (`darkpool`)** with output file `darkpool_predictions.txt` (and backward-compatible alias `hft_order_flow_predictions.txt`).
   - **Strategy 31** must be canonically designated as **Earnings Tone Drift NLP (`earnings_tone_drift`)** with output file `earnings_tone_drift_predictions.txt`.
2. **`AGENTS.md` Discrepancies**:
   - Lines 38–39, Mermaid diagram lines 119–120, and Key Files lines 193–194 inverted Strategies 30 and 31 (listing Tone Drift as #30 and HFT/Darkpool as #31). These must be updated to reflect #30 Darkpool and #31 Earnings Tone Drift.
3. **`run_pipeline.py` Discrepancies**:
   - `STRATEGY_REGISTRY` (lines 3201–3231) currently lists `earnings_tone_drift` as Strategy 30 and `darkpool` as Strategy 31, while `lstm` (Strategy 6) is appended at the bottom after Strategy 37.
   - `verification_files` (lines 4338–4352) only checks **13 files**, completely missing Strategies 6, 10–14, 19–31, as well as `strategy_data_coverage_report.txt` and `portfolio_allocation.txt`.
   - `_STRAT_DISPLAY_MAP` (lines 4045–4077) and the Top 100 table headers (lines 4108, 4173) already correctly follow the canonical 1..31 sequence (#30 Darkpool, #31 ToneDrift).
4. **`verify_gha_artifacts.py` & `SKILL.md`**:
   - Currently verify only 23 strategies, omitting Strategies 24–31 (`accruals_quality`, `short_squeeze`, `valueup_catalyst`, `trend_efficiency`, `gamma_squeeze`, `insider_buying`, `darkpool`, `earnings_tone_drift`). Must be expanded to full 31 canonical strategy coverage.

---

## 2. Canonical Strategy Master Specification (1~31)

| # | Strategy Key | Canonical Name (Display) | Engine / Module | Score Column | Output File | Horizon Tier |
|---|--------------|--------------------------|-----------------|--------------|-------------|--------------|
| **1** | `regression` | XGBoost Regression Fundamentals | `src/ai/prediction_model.py` | `reg_score` | `pipeline_result.txt` | Slow (1M~1Y) |
| **2** | `surge` | Surge Classifier (XGBoost) | `src/ai/prediction_model.py` | `surge_score` | `surge_predictions.txt` | Medium (5D~20D) |
| **3** | `lead_lag` | Index & Sector Lead-Lag Flow | `src/ai/prediction_model.py` | `ll_score` | `lead_lag_predictions.txt` | Medium (5D~20D) |
| **4** | `vcp_rule` | VCP Rule Pattern Detector | `src/ai/vcp_detector.py` | `vcp_rule_score` | `vcp_patterns.txt` | Medium (5D~20D) |
| **5** | `vcp_ml` | VCP Machine Learning Predictor | `src/ai/vcp_ml_predictor.py` | `vcp_ml_score` | `vcp_ml_predictions.txt` | Medium (5D~20D) |
| **6** | `lstm` | Strict Causal LSTM Deep Learning | `src/ai/prediction_model.py` | `lstm_score` | `lstm_predictions.txt` | Medium (5D~20D) |
| **7** | `stat_arb` | Stat-Arb Cointegration Mean Rev | `src/core/stat_arb.py` | `stat_arb_score` | `stat_arb_predictions.txt` | Medium (5D~20D) |
| **8** | `sector_rotation` | Sector Rotation Relative Momentum | `src/core/sector_rotation.py` | `sector_score` | `sector_predictions.txt` | Medium (5D~20D) |
| **9** | `rim_valuation` | RIM Valuation (Residual Income) | `src/core/rim_valuation.py` | `rim_score` | `rim_predictions.txt` | Slow (1M~1Y) |
| **10** | `event_driven` | Event-Driven Disclosure Catalyst | `src/core/event_driven.py` | `event_score` | `event_driven_predictions.txt` | Medium (5D~20D) |
| **11** | `mq_factor` | Momentum Quality (MQ) Factor | `src/core/mq_factor.py` | `mq_score` | `mq_factor_predictions.txt` | Slow (1M~1Y) |
| **12** | `iv_skew` | Options Put/Call IV Skew | `src/core/iv_skew.py` | `iv_skew_score` | `iv_skew_predictions.txt` | Slow (1M~1Y) |
| **13** | `order_flow` | Order Flow Imbalance (MFI) | `src/core/order_flow.py` | `order_flow_score` | `order_flow_predictions.txt` | Fast (1D~3D) |
| **14** | `short_term_reversal`| Short-Term Mean Reversal | `src/core/short_term_reversal.py` | `reversal_score` | `short_term_reversal_predictions.txt`| Fast (1D~3D) |
| **15** | `arm_factor` | Analyst Revision Momentum (ARM) | `src/core/arm_factor.py` | `arm_score` | `arm_factor_predictions.txt` | Slow (1M~1Y) |
| **16** | `card_factor` | Cross-Asset Regime Divergence(CARD)| `src/core/card_factor.py` | `card_score` | `card_factor_predictions.txt` | Slow (1M~1Y) |
| **17** | `latr_factor` | Liquidity-Adjusted Tail Risk (LATR)| `src/core/latr_factor.py` | `latr_score` | `latr_factor_predictions.txt` | Slow (1M~1Y) |
| **18** | `inst_foreign_sector`| Inst & Foreign Sector Flow | `src/core/inst_foreign_sector.py` | `inst_foreign_sector_score` | `inst_foreign_sector_predictions.txt`| Medium (5D~20D) |
| **19** | `supply_chain`| Supply Chain Spillover Momentum | `src/core/supply_chain.py` | `supply_chain_score` | `supply_chain_predictions.txt` | Medium (5D~20D) |
| **20** | `sentiment` | NLP FinBERT Sentiment Catalyst | `src/core/llm_sentiment_engine.py` | `sentiment_score` | `sentiment_predictions.txt` | Medium (5D~20D) |
| **21** | `factor_neutralized`| Multi-Factor Style Neutral Alpha | `src/core/multi_factor_neutralizer.py`| `factor_neutralized_score` | `factor_neutralized_predictions.txt` | Slow (1M~1Y) |
| **22** | `vol_target` | Dynamic Volatility Targeting | `src/core/vol_target.py` | `vol_target_score` | `vol_target_predictions.txt` | Slow (1M~1Y) |
| **23** | `microstructure`| Order Book Microstructure Imbalance| `src/core/hft_engine.py` | `microstructure_score` | `microstructure_predictions.txt` | Fast (1D~3D) |
| **24** | `accruals_quality`| Accruals Quality Accounting Pure | `src/core/accruals_quality.py` | `accruals_quality_score` | `accruals_quality_predictions.txt` | Slow (1M~1Y) |
| **25** | `short_squeeze`| Short Interest & Squeeze Catalyst | `src/core/short_interest_squeeze.py` | `short_squeeze_score` | `short_squeeze_predictions.txt` | Medium (5D~20D) |
| **26** | `valueup_catalyst`| Value-Up & Shareholder Yield | `src/core/valueup_catalyst.py` | `valueup_catalyst_score` | `valueup_catalyst_predictions.txt` | Slow (1M~1Y) |
| **27** | `trend_efficiency`| Kaufman Trend Efficiency Filter | `src/core/trend_efficiency.py` | `trend_efficiency_score` | `trend_efficiency_predictions.txt` | Medium (5D~20D) |
| **28** | `gamma_squeeze`| Options Gamma & Delta Squeeze | `src/core/gamma_squeeze.py` | `gamma_squeeze_score` | `gamma_squeeze_predictions.txt` | Medium (5D~20D) |
| **29** | `insider_buying`| Executive & Insider Buying Catalyst| `src/core/insider_buying.py` | `insider_buying_score` | `insider_buying_predictions.txt` | Medium (5D~20D) |
| **30** | `darkpool` | HFT Order Flow & Dark Pool | `src/data_layer/darkpool_tracker.py` | `darkpool_score` | `darkpool_predictions.txt` | Fast (1D~3D) |
| **31** | `earnings_tone_drift`| Earnings Tone Drift NLP Quant | `src/core/earnings_tone_drift.py` | `earnings_tone_drift_score` | `earnings_tone_drift_predictions.txt`| Slow (1M~1Y) |

---

## 3. Exact Code Changes Required

### 3.1 `trading_system/run_pipeline.py`

#### A. STRATEGY_REGISTRY Alignment (Lines 3201–3231)
- **Problem**: `STRATEGY_REGISTRY` contains `earnings_tone_drift` before `darkpool` (labeled as Strategy 30 & 31 respectively), while `lstm` (Strategy 6) is placed at line 3230 at the very bottom.
- **Fix**: Re-order entries to place `lstm` (Strategy 6) cleanly, and set Strategy 30 to `darkpool` (`darkpool_predictions.txt`) and Strategy 31 to `earnings_tone_drift` (`earnings_tone_drift_predictions.txt`).

```python
<<<< BEFORE (lines 3201-3231)
    # Strategy Configuration Registry
    STRATEGY_REGISTRY = [
        {'key': 'event', 'fn': _eval_event_driven, 'col': 'event_score', 'title': 'Strategy 10: Event-Driven Disclosure Catalyst Predictions', 'file': 'event_driven_predictions.txt', 'hdr': 'Event Score', 'w': 14},
        ...
        {'key': 'insider_buying', 'fn': _eval_insider_buying, 'col': 'insider_buying_score', 'title': 'Strategy 29: Insider Buying Catalyst Predictions', 'file': 'insider_buying_predictions.txt', 'hdr': 'Insider Score', 'w': 16},
        {'key': 'earnings_tone_drift', 'fn': _eval_earnings_tone_drift, 'col': 'earnings_tone_drift_score', 'title': 'Strategy 30: Earnings Tone Drift NLP Predictions', 'file': 'earnings_tone_drift_predictions.txt', 'hdr': 'Tone Score', 'w': 16},
        {'key': 'darkpool', 'fn': _eval_darkpool, 'col': 'darkpool_score', 'title': 'Strategy 31: HFT Order Flow & Dark Pool Predictions', 'file': 'hft_order_flow_predictions.txt', 'hdr': 'HFT Score', 'w': 16},
        {'key': 'dual_correction', 'fn': _eval_dual_correction, 'col': 'dual_correction_score', 'title': 'Strategy 32: Dual Correction Predictions', 'file': 'dual_correction_predictions.txt', 'hdr': 'Dual Score', 'w': 16},
        {'key': 'index_rebalance', 'fn': _eval_index_rebalance, 'col': 'index_rebalance_score', 'title': 'Strategy 33: Index Rebalance Predictions', 'file': 'index_rebalance_predictions.txt', 'hdr': 'Rebal Score', 'w': 16},
        {'key': 'overnight_gap_reversal', 'fn': _eval_overnight_gap_reversal, 'col': 'overnight_gap_score', 'title': 'Strategy 34: Overnight Gap Reversal Predictions', 'file': 'overnight_gap_predictions.txt', 'hdr': 'Gap Score', 'w': 16},
        {'key': 'cross_asset_spillover', 'fn': _eval_cross_asset_spillover, 'col': 'cross_asset_spillover_score', 'title': 'Strategy 35: Cross-Asset Spillover Momentum Predictions', 'file': 'cross_asset_spillover_predictions.txt', 'hdr': 'Spillover Score', 'w': 16},
        {'key': 'supply_chain_gnn', 'fn': _eval_supply_chain_gnn, 'col': 'supply_chain_gnn_score', 'title': 'Strategy 36: Supply Chain GNN & Sector Flow Predictions', 'file': 'supply_chain_gnn_predictions.txt', 'hdr': 'SC GNN Score', 'w': 16},
        {'key': 'range_expansion_breakout', 'fn': _eval_range_expansion_breakout, 'col': 'range_expansion_score', 'title': 'Strategy 37: Range Expansion Breakout Predictions', 'file': 'range_expansion_predictions.txt', 'hdr': 'Breakout Score', 'w': 16},
        {'key': 'lstm', 'fn': _eval_lstm, 'col': 'lstm_score', 'title': 'Strategy 6: Strict Causal LSTM Predictions', 'file': 'lstm_predictions.txt', 'hdr': 'LSTM Score', 'w': 14},
    ]
====
>>>> AFTER
    # Strategy Configuration Registry
    STRATEGY_REGISTRY = [
        {'key': 'lstm', 'fn': _eval_lstm, 'col': 'lstm_score', 'title': 'Strategy 6: Strict Causal LSTM Predictions', 'file': 'lstm_predictions.txt', 'hdr': 'LSTM Score', 'w': 14},
        {'key': 'event', 'fn': _eval_event_driven, 'col': 'event_score', 'title': 'Strategy 10: Event-Driven Disclosure Catalyst Predictions', 'file': 'event_driven_predictions.txt', 'hdr': 'Event Score', 'w': 14},
        {'key': 'mq', 'fn': _eval_mq_factor, 'col': 'mq_score', 'title': 'Strategy 11: Momentum Quality (MQ) Factor Predictions', 'file': 'mq_factor_predictions.txt', 'hdr': 'MQ Score', 'w': 14},
        {'key': 'iv_skew', 'fn': _eval_iv_skew, 'col': 'iv_skew_score', 'title': 'Strategy 12: Options Put/Call IV Skew Predictions', 'file': 'iv_skew_predictions.txt', 'hdr': 'IV Skew Score', 'w': 14},
        {'key': 'order_flow', 'fn': _eval_order_flow, 'col': 'order_flow_score', 'title': 'Strategy 13: Order Flow Imbalance (MFI) Predictions', 'file': 'order_flow_predictions.txt', 'hdr': 'Order Flow Score', 'w': 16},
        {'key': 'reversal', 'fn': _eval_short_term_reversal, 'col': 'reversal_score', 'title': 'Strategy 14: Short-Term Mean Reversal Predictions', 'file': 'short_term_reversal_predictions.txt', 'hdr': 'Reversal Score', 'w': 16},
        {'key': 'arm', 'fn': _eval_arm_factor, 'col': 'arm_score', 'title': 'Strategy 15: Analyst Revision Momentum (ARM) Factor Predictions', 'file': 'arm_factor_predictions.txt', 'hdr': 'ARM Score', 'w': 12},
        {'key': 'card', 'fn': _eval_card_factor, 'col': 'card_score', 'title': 'Strategy 16: Cross-Asset Regime Divergence (CARD) Factor Predictions', 'file': 'card_factor_predictions.txt', 'hdr': 'CARD Score', 'w': 14},
        {'key': 'latr', 'fn': _eval_latr_factor, 'col': 'latr_score', 'title': 'Strategy 17: Liquidity-Adjusted Tail Risk (LATR) Factor Predictions', 'file': 'latr_factor_predictions.txt', 'hdr': 'LATR Score', 'w': 14},
        {'key': 'inst_foreign_sector', 'fn': _eval_inst_foreign_sector, 'col': 'inst_foreign_sector_score', 'title': 'Strategy 18: Inst & Foreign 2-Month Accumulation & Sector Correlation Predictions', 'file': 'inst_foreign_sector_predictions.txt', 'hdr': 'IFS Score', 'w': 14},
        {'key': 'supply_chain', 'fn': _eval_supply_chain, 'col': 'supply_chain_score', 'title': 'Strategy 19: Supply Chain Lead-Lag Momentum Predictions', 'file': 'supply_chain_predictions.txt', 'hdr': 'SC Score', 'w': 14},
        {'key': 'sentiment', 'fn': _eval_sentiment, 'col': 'sentiment_score', 'title': 'Strategy 20: NLP & FinBERT Sentiment Catalyst Predictions', 'file': 'sentiment_predictions.txt', 'hdr': 'Sent Score', 'w': 14},
        {'key': 'factor_neutralized', 'fn': _eval_factor_neutralized, 'col': 'factor_neutralized_score', 'title': 'Strategy 21: Multi-Factor Style Neutralized Pure Alpha Predictions', 'file': 'factor_neutralized_predictions.txt', 'hdr': 'FN Score', 'w': 14},
        {'key': 'vol_target', 'fn': _eval_vol_target, 'col': 'vol_target_score', 'title': 'Strategy 22: Dynamic Volatility Targeting Risk Parity Predictions', 'file': 'vol_target_predictions.txt', 'hdr': 'VT Score', 'w': 14},
        {'key': 'microstructure', 'fn': _eval_microstructure, 'col': 'microstructure_score', 'title': 'Strategy 23: Order Book Microstructure Imbalance Predictions', 'file': 'microstructure_predictions.txt', 'hdr': 'Micro Score', 'w': 14},
        {'key': 'accruals_quality', 'fn': _eval_accruals_quality, 'col': 'accruals_quality_score', 'title': 'Strategy 24: Accruals Quality Anomaly Predictions', 'file': 'accruals_quality_predictions.txt', 'hdr': 'Accruals Score', 'w': 16},
        {'key': 'short_squeeze', 'fn': _eval_short_squeeze, 'col': 'short_squeeze_score', 'title': 'Strategy 25: Short Interest & Squeeze Catalyst Predictions', 'file': 'short_squeeze_predictions.txt', 'hdr': 'Squeeze Score', 'w': 16},
        {'key': 'valueup_catalyst', 'fn': _eval_valueup_catalyst, 'col': 'valueup_catalyst_score', 'title': 'Strategy 26: Value-Up & Shareholder Yield Predictions', 'file': 'valueup_catalyst_predictions.txt', 'hdr': 'ValueUp Score', 'w': 16},
        {'key': 'trend_efficiency', 'fn': _eval_trend_efficiency, 'col': 'trend_efficiency_score', 'title': 'Strategy 27: Kaufman Trend Efficiency Predictions', 'file': 'trend_efficiency_predictions.txt', 'hdr': 'Trend Score', 'w': 16},
        {'key': 'gamma_squeeze', 'fn': _eval_gamma_squeeze, 'col': 'gamma_squeeze_score', 'title': 'Strategy 28: Options Gamma Squeeze Predictions', 'file': 'gamma_squeeze_predictions.txt', 'hdr': 'Gamma Score', 'w': 16},
        {'key': 'insider_buying', 'fn': _eval_insider_buying, 'col': 'insider_buying_score', 'title': 'Strategy 29: Insider Buying Catalyst Predictions', 'file': 'insider_buying_predictions.txt', 'hdr': 'Insider Score', 'w': 16},
        {'key': 'darkpool', 'fn': _eval_darkpool, 'col': 'darkpool_score', 'title': 'Strategy 30: HFT Order Flow & Dark Pool Predictions', 'file': 'darkpool_predictions.txt', 'hdr': 'Darkpool Score', 'w': 16},
        {'key': 'earnings_tone_drift', 'fn': _eval_earnings_tone_drift, 'col': 'earnings_tone_drift_score', 'title': 'Strategy 31: Earnings Tone Drift NLP Predictions', 'file': 'earnings_tone_drift_predictions.txt', 'hdr': 'Tone Score', 'w': 16},
        {'key': 'dual_correction', 'fn': _eval_dual_correction, 'col': 'dual_correction_score', 'title': 'Strategy 32: Dual Correction Predictions', 'file': 'dual_correction_predictions.txt', 'hdr': 'Dual Score', 'w': 16},
        {'key': 'index_rebalance', 'fn': _eval_index_rebalance, 'col': 'index_rebalance_score', 'title': 'Strategy 33: Index Rebalance Predictions', 'file': 'index_rebalance_predictions.txt', 'hdr': 'Rebal Score', 'w': 16},
        {'key': 'overnight_gap_reversal', 'fn': _eval_overnight_gap_reversal, 'col': 'overnight_gap_score', 'title': 'Strategy 34: Overnight Gap Reversal Predictions', 'file': 'overnight_gap_predictions.txt', 'hdr': 'Gap Score', 'w': 16},
        {'key': 'cross_asset_spillover', 'fn': _eval_cross_asset_spillover, 'col': 'cross_asset_spillover_score', 'title': 'Strategy 35: Cross-Asset Spillover Momentum Predictions', 'file': 'cross_asset_spillover_predictions.txt', 'hdr': 'Spillover Score', 'w': 16},
        {'key': 'supply_chain_gnn', 'fn': _eval_supply_chain_gnn, 'col': 'supply_chain_gnn_score', 'title': 'Strategy 36: Supply Chain GNN & Sector Flow Predictions', 'file': 'supply_chain_gnn_predictions.txt', 'hdr': 'SC GNN Score', 'w': 16},
        {'key': 'range_expansion_breakout', 'fn': _eval_range_expansion_breakout, 'col': 'range_expansion_score', 'title': 'Strategy 37: Range Expansion Breakout Predictions', 'file': 'range_expansion_predictions.txt', 'hdr': 'Breakout Score', 'w': 16},
    ]
```

#### B. Full verification_files Expansion (Lines 4338–4354)
- **Problem**: Only checks 13 files.
- **Fix**: Expand to all 31 strategy `.txt` files + ensemble, coverage, and portfolio files.

```python
<<<< BEFORE (lines 4338-4354)
    verification_files = [
        "pipeline_result.txt",
        "surge_predictions.txt",
        "lead_lag_predictions.txt",
        "vcp_patterns.txt",
        "vcp_ml_predictions.txt",
        "stat_arb_predictions.txt",
        "sector_predictions.txt",
        "rim_predictions.txt",
        "arm_factor_predictions.txt",
        "card_factor_predictions.txt",
        "latr_factor_predictions.txt",
        "inst_foreign_sector_predictions.txt",
        "ensemble_predictions.txt",
    ]
    critical_files = ["pipeline_result.txt", "surge_predictions.txt", "ensemble_predictions.txt"]
====
>>>> AFTER
    verification_files = [
        "pipeline_result.txt",
        "surge_predictions.txt",
        "lead_lag_predictions.txt",
        "vcp_patterns.txt",
        "vcp_ml_predictions.txt",
        "lstm_predictions.txt",
        "stat_arb_predictions.txt",
        "sector_predictions.txt",
        "rim_predictions.txt",
        "event_driven_predictions.txt",
        "mq_factor_predictions.txt",
        "iv_skew_predictions.txt",
        "order_flow_predictions.txt",
        "short_term_reversal_predictions.txt",
        "arm_factor_predictions.txt",
        "card_factor_predictions.txt",
        "latr_factor_predictions.txt",
        "inst_foreign_sector_predictions.txt",
        "supply_chain_predictions.txt",
        "sentiment_predictions.txt",
        "factor_neutralized_predictions.txt",
        "vol_target_predictions.txt",
        "microstructure_predictions.txt",
        "accruals_quality_predictions.txt",
        "short_squeeze_predictions.txt",
        "valueup_catalyst_predictions.txt",
        "trend_efficiency_predictions.txt",
        "gamma_squeeze_predictions.txt",
        "insider_buying_predictions.txt",
        "darkpool_predictions.txt",
        "earnings_tone_drift_predictions.txt",
        "ensemble_predictions.txt",
        "strategy_data_coverage_report.txt",
        "portfolio_allocation.txt",
    ]
    critical_files = ["pipeline_result.txt", "surge_predictions.txt", "ensemble_predictions.txt"]
```

---

### 3.2 `AGENTS.md` Alignment

#### A. Table of 31 Strategies (Lines 38–39)
```markdown
<<<< BEFORE (lines 38-39)
| **30** | Earnings Tone Drift | 실적 발표 콘퍼런스콜 텍스트 톤 변화 감성 퀀트 | 앙상블 피처 결합 |
| **31** | High-Frequency Execution | 호가 불균형 & 마이크로스프레드 고빈도 모멘텀 | 앙상블 피처 결합 |
====
>>>> AFTER
| **30** | Darkpool & HFT Flow | 다크풀 블록트레이드 & HFT 마이크로스프레드 모멘텀 | `darkpool_predictions.txt` |
| **31** | Earnings Tone Drift | 실적 발표 콘퍼런스콜 텍스트 톤 변화 감성 퀀트 | `earnings_tone_drift_predictions.txt` |
```

#### B. Architecture Mermaid Diagram (Lines 119–120)
```mermaid
<<<< BEFORE (lines 119-120)
ToneDrift["30. Earnings Tone Drift"]
HFT["31. HFT Order Flow"]
====
>>>> AFTER
Darkpool["30. Darkpool & HFT Flow"]
ToneDrift["31. Earnings Tone Drift"]
```

#### C. Key Files Table (Lines 193–194)
```markdown
<<<< BEFORE (lines 193-194)
| `src/core/tone_drift.py` | ToneDriftEngine: 실적 발표 콘퍼런스콜 텍스트 톤 변화 감성 퀀트 |
| `src/core/darkpool_tracker.py` | DarkpoolTrackerEngine: 다크풀 블록트레이드 & HFT 마이크로스프레드 모멘텀 |
====
>>>> AFTER
| `src/core/darkpool_tracker.py` | DarkpoolTrackerEngine: 다크풀 블록트레이드 & HFT 마이크로스프레드 모멘텀 |
| `src/core/tone_drift.py` | ToneDriftEngine: 실적 발표 콘퍼런스콜 텍스트 톤 변화 감성 퀀트 |
```

---

### 3.3 `trading_system/scripts/verify_gha_artifacts.py` & `SKILL.md` (F04)

- **`STRATEGIES` list** must be expanded from 23 to all 31 in canonical order:
  ```python
  STRATEGIES = [
      "regression", "surge", "lead_lag", "vcp", "vcp_ml", "lstm",
      "stat_arb", "sector", "rim", "event_driven", "mq_factor",
      "iv_skew", "order_flow", "short_term_reversal", "arm_factor",
      "card_factor", "latr_factor", "inst_foreign_sector",
      "supply_chain", "sentiment", "factor_neutralized", "vol_target",
      "microstructure", "accruals_quality", "short_squeeze", "valueup_catalyst",
      "trend_efficiency", "gamma_squeeze", "insider_buying", "darkpool", "earnings_tone_drift"
  ]
  ```
- **`files_map` and `check_funcs`** in `verify_market_strategies()`:
  - Add mappings for:
    - `"accruals_quality"`: `["accruals_quality_{market}.txt", "accruals_quality_predictions_{market}.txt", "accruals_quality_predictions.txt"]`
    - `"short_squeeze"`: `["short_squeeze_{market}.txt", "short_squeeze_predictions_{market}.txt", "short_squeeze_predictions.txt"]`
    - `"valueup_catalyst"`: `["valueup_catalyst_{market}.txt", "valueup_catalyst_predictions_{market}.txt", "valueup_catalyst_predictions.txt"]`
    - `"trend_efficiency"`: `["trend_efficiency_{market}.txt", "trend_efficiency_predictions_{market}.txt", "trend_efficiency_predictions.txt"]`
    - `"gamma_squeeze"`: `["gamma_squeeze_{market}.txt", "gamma_squeeze_predictions_{market}.txt", "gamma_squeeze_predictions.txt"]`
    - `"insider_buying"`: `["insider_buying_{market}.txt", "insider_buying_predictions_{market}.txt", "insider_buying_predictions.txt"]`
    - `"darkpool"`: `["darkpool_{market}.txt", "darkpool_predictions_{market}.txt", "darkpool_predictions.txt", "hft_order_flow_predictions_{market}.txt", "hft_order_flow_predictions.txt"]`
    - `"earnings_tone_drift"`: `["earnings_tone_drift_{market}.txt", "earnings_tone_drift_predictions_{market}.txt", "earnings_tone_drift_predictions.txt"]`
- Update table printing in `print_report()` and headers to include all 31 strategies.

---

## 4. Verification & Testing Strategy

1. **Unit & Integration Testing**:
   - Run `pytest tests/test_merge_generic_strategies.py` and `tests/test_report_ux_and_rounding.py` to ensure strategy file parsing and merging succeed without regression.
2. **Artifact Verification**:
   - Run `python trading_system/scripts/verify_gha_artifacts.py --result-dir trading_system/result --gh-pages-dir gh-pages` confirming all 31 strategy panels and output files are validated.
3. **Pipeline Dry-Run**:
   - Simulate `run_pipeline.py` execution and confirm all 34 files in `verification_files` pass validation.
