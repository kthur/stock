# Investigation Report: Milestone 2 (R2: Dashboard & Merge Sequence Synchronization)

**Author:** teamwork_preview_explorer (m2_3)  
**Date:** 2026-09-01T00:13:00+09:00  
**Scope:** Verification of 31-strategy canonical sequence across `generate_report.py`, `merge_predictions.py`, `correlation_monitor.py`, and related pipeline components.

---

## 1. Executive Summary

An exhaustive codebase inspection and automated test audit was conducted to verify the alignment of the **31-Strategy Canonical Master Sequence** across reporting, merging, correlation monitoring, and pipeline execution modules.

- **`generate_report.py`**: **100% Fully Synchronized.** `STRATEGY_METADATA`, table column headers (`<th>` & `<td>`), navigation tab IDs, stock drawer decomposition dictionaries, and autocomplete search indices strictly adhere to the 1..31 canonical sequence.
- **`merge_predictions.py`**: **Functionally Complete with Sequence Optimization Opportunity.** `ALL_31_STRATEGIES` list and `KNOWN_STRATEGY_PREFIXES` include all 31 strategies in canonical order. All 31 strategy outputs are merged across markets without data loss. The merge function call order in `main()` can be sorted to strictly follow 1..31 for maximum architectural consistency.
- **`correlation_monitor.py`**: **100% Fully Synchronized.** Both `src/ai/correlation_monitor.py` and `src/analysis/strategy_correlation_monitor.py` support the full 31 strategies, with complete score column mappings (`STRATEGY_SCORE_COL_MAP`), rolling correlation estimation, VIF calculations, and Meucci Effective Strategy Count (ESC) metrics.
- **Verification Suite & CI Alignment**: Unit tests (`test_merge_generic_strategies.py`, `test_strategy_correlation_monitor.py`, `test_merge_predictions_stress.py`) passed **92/92 tests (100%)**. Downstream CI scripts (`verify_gha_artifacts.py` and `run_pipeline.py:verification_files`) contain legacy 23-strategy lists ready for planned Milestone 2 expansion (F04, F05).

---

## 2. 31-Strategy Canonical Master Sequence Reference

The canonical specification defined in `PROJECT.md` and `AGENTS.md` is as follows:

| # | Strategy ID (`strategy_id`) | Display Name / Korean Label | Output File | Score Column |
|---|-----------------------------|-----------------------------|-------------|--------------|
| **1** | `regression` | 1. XGBoost 회귀 | `pipeline_result.txt` | `reg_score` |
| **2** | `surge` | 2. Surge 분류기 | `surge_predictions.txt` | `surge_score` |
| **3** | `lead_lag` | 3. Lead-Lag 후행주 | `lead_lag_predictions.txt` | `ll_score` |
| **4** | `vcp_rule` | 4. VCP 패턴 (Rule) | `vcp_patterns.txt` | `vcp_rule_score` |
| **5** | `vcp_ml` | 5. VCP ML 급등예측 | `vcp_ml_predictions.txt` | `vcp_ml_score` |
| **6** | `lstm` | 6. Strict Causal LSTM | `lstm_predictions.txt` | `lstm_score` |
| **7** | `stat_arb` | 7. Stat-Arb 차익거래 | `stat_arb_predictions.txt` | `stat_arb_score` |
| **8** | `sector_rotation` | 8. Sector Rotation | `sector_predictions.txt` | `sector_score` |
| **9** | `rim_valuation` | 9. RIM Valuation | `rim_predictions.txt` | `rim_score` |
| **10** | `event_driven` | 10. Event-Driven 촉매 | `event_driven_predictions.txt` | `event_score` |
| **11** | `mq_factor` | 11. MQ Factor (퀄리티) | `mq_factor_predictions.txt` | `mq_score` |
| **12** | `iv_skew` | 12. Options IV Skew | `iv_skew_predictions.txt` | `iv_skew_score` |
| **13** | `order_flow` | 13. Order Flow 수급 | `order_flow_predictions.txt` | `order_flow_score` |
| **14** | `short_term_reversal` | 14. ST Reversal 단기반등 | `short_term_reversal_predictions.txt` | `reversal_score` |
| **15** | `arm_factor` | 15. ARM Factor (컨센서스) | `arm_factor_predictions.txt` | `arm_score` |
| **16** | `card_factor` | 16. CARD Factor (크로스에셋) | `card_factor_predictions.txt` | `card_score` |
| **17** | `latr_factor` | 17. LATR Factor (꼬리위험) | `latr_factor_predictions.txt` | `latr_score` |
| **18** | `inst_foreign_sector` | 18. 외인/투신 수급 | `inst_foreign_sector_predictions.txt` | `inst_foreign_sector_score` |
| **19** | `supply_chain` | 19. Supply Chain 공급망 | `supply_chain_predictions.txt` | `supply_chain_score` |
| **20** | `sentiment` | 20. NLP Sentiment (감성) | `sentiment_predictions.txt` | `sentiment_score` |
| **21** | `factor_neutralized` | 21. Factor Neutralized | `factor_neutralized_predictions.txt` | `factor_neutralized_score` |
| **22** | `vol_target` | 22. Vol Targeting | `vol_target_predictions.txt` | `vol_target_score` |
| **23** | `microstructure` | 23. Microstructure 호가 | `microstructure_predictions.txt` | `microstructure_score` |
| **24** | `accruals_quality` | 24. Accruals Quality (발생액) | `accruals_quality_predictions.txt` | `accruals_quality_score` |
| **25** | `short_squeeze` | 25. Short Squeeze 촉매 | `short_squeeze_predictions.txt` | `short_squeeze_score` |
| **26** | `valueup_catalyst` | 26. Value-Up Yield (주주환원) | `valueup_catalyst_predictions.txt` | `valueup_catalyst_score` |
| **27** | `trend_efficiency` | 27. Trend Efficiency 추세 | `trend_efficiency_predictions.txt` | `trend_efficiency_score` |
| **28** | `gamma_squeeze` | 28. Gamma Squeeze (감마) | `gamma_squeeze_predictions.txt` | `gamma_squeeze_score` |
| **29** | `insider_buying` | 29. Insider Buying (내부자) | `insider_buying_predictions.txt` | `insider_buying_score` |
| **30** | `darkpool` | 30. Darkpool & HFT Flow | `darkpool_predictions.txt` / `hft_order_flow_predictions.txt` | `darkpool_score` |
| **31** | `earnings_tone_drift` | 31. Tone Drift 어닝어조 | `earnings_tone_drift_predictions.txt` | `earnings_tone_drift_score` |

---

## 3. Deep-Dive Inspection: `trading_system/generate_report.py`

### 3.1. `STRATEGY_METADATA` (Lines 1373–1405)
```python
STRATEGY_METADATA = [
    ("regression", 1, "XGBoost 회귀", "AI 예측", "regression"),
    ("surge", 2, "Surge 분류기", "AI 예측", "surge"),
    ("lead_lag", 3, "Lead-Lag 후행주", "모멘텀/수급", "leadlag"),
    ("vcp_rule", 4, "VCP 패턴 (Rule)", "기술적 패턴", "vcp"),
    ("vcp_ml", 5, "VCP ML 급등예측", "AI 예측", "vcpml"),
    ("lstm", 6, "Strict Causal LSTM", "딥러닝", "lstm"),
    ("stat_arb", 7, "Stat-Arb 차익거래", "차익거래", "stat-arb"),
    ("sector_rotation", 8, "Sector Rotation", "모멘텀/수급", "sector"),
    ("rim_valuation", 9, "RIM Valuation", "가치평가", "rim"),
    ("event_driven", 10, "Event-Driven 촉매", "촉매/공시", "event"),
    ("mq_factor", 11, "MQ Factor (퀄리티)", "퀄리티", "mq"),
    ("iv_skew", 12, "Options IV Skew", "파생/역발상", "iv"),
    ("order_flow", 13, "Order Flow 수급", "수급/유동성", "flow"),
    ("short_term_reversal", 14, "ST Reversal 단기반등", "평균회귀", "reversal"),
    ("arm_factor", 15, "ARM Factor (컨센서스)", "컨센서스", "arm"),
    ("card_factor", 16, "CARD Factor (크로스에셋)", "크로스에셋", "card"),
    ("latr_factor", 17, "LATR Factor (꼬리위험)", "꼬리위험", "latr"),
    ("inst_foreign_sector", 18, "외인/투신 수급", "수급/유동성", "ifs"),
    ("supply_chain", 19, "Supply Chain 공급망", "공급망", "supplychain"),
    ("sentiment", 20, "NLP Sentiment (감성)", "NLP 감성", "sentiment"),
    ("factor_neutralized", 21, "Factor Neutralized", "순수 알파", "neutralized"),
    ("vol_target", 22, "Vol Targeting", "변동성 관리", "voltarget"),
    ("microstructure", 23, "Microstructure 호가", "미시구조", "microstructure"),
    ("accruals_quality", 24, "Accruals Quality (발생액)", "회계 품질", "accruals"),
    ("short_squeeze", 25, "Short Squeeze 촉매", "공매도", "shortsqueeze"),
    ("valueup_catalyst", 26, "Value-Up Yield (주주환원)", "주주환원", "valueup"),
    ("trend_efficiency", 27, "Trend Efficiency 추세", "추세 필터", "trendeff"),
    ("gamma_squeeze", 28, "Gamma Squeeze (감마)", "파생/옵션", "gammasqueeze"),
    ("insider_buying", 29, "Insider Buying (내부자)", "내부자", "insider"),
    ("darkpool", 30, "Darkpool & HFT Flow", "고빈도/다크풀", "darkpool"),
    ("earnings_tone_drift", 31, "Tone Drift 어닝어조", "NLP 어조", "tonedrift"),
]
```
- **Status:** **Verified (100% Match).** Exact 1..31 order with correct tuple fields `(strategy_id, num, name_ko, category, tab_id)`.

### 3.2. Ensemble Table Column Headers & Row Data (Lines 2014–2045 & 2085–2116)
- **Table Headers (`<thead>`):** 1. Reg, 2. Surge, 3. L-L, 4. VCP-R, 5. VCP-M, 6. LSTM, 7. S-Arb, 8. Sec-R, 9. RIM, 10. Event, 11. MQ, 12. IV-Sk, 13. Flow, 14. Rev, 15. ARM, 16. CARD, 17. LATR, 18. I&F, 19. Supply, 20. NLP, 21. Neutral, 22. Vol-T, 23. Micro, 24. Accrual, 25. S-Sq, 26. ValueUp, 27. TrendEff, 28. GammaSq, 29. Insider, 30. Darkpool, 31. ToneDrift.
- **Table Row Data (`<td>`):** `erow.reg` through `erow.earnings_tone_drift` in identical positional correspondence.
- **Status:** **Verified (100% Match).**

### 3.3. Individual Strategy Tabs & Panels (Lines 3728–3761 & 3766–4076)
- **Tab Buttons:** 1: `regression`, 2: `surge`, 3: `leadlag`, 4: `vcp`, 5: `vcpml`, 6: `lstm`, 7: `stat-arb`, 8: `sector`, 9: `rim`, 10: `event`, 11: `mq`, 12: `iv`, 13: `flow`, 14: `reversal`, 15: `arm`, 16: `card`, 17: `latr`, 18: `ifs`, 19: `supplychain`, 20: `sentiment`, 21: `neutralized`, 22: `voltarget`, 23: `microstructure`, 24: `accruals`, 25: `shortsqueeze`, 26: `valueup`, 27: `trendeff`, 28: `gammasqueeze`, 29: `insider`, 30: `darkpool`, 31: `tonedrift`.
- **Panel IDs:** `panel-regression` through `panel-tonedrift`.
- **Status:** **Verified (100% Match).**

### 3.4. Stock Drawer Factor Breakdown & Autocomplete (Lines 1970–2002 & 4941–4973)
- `factors_dict` encoded and parsed in the mobile/desktop slide-in drawer includes all 31 keys `"1. XGBoost 회귀"` through `"31. Tone Drift"`.
- **Status:** **Verified (100% Match).**

---

## 4. Deep-Dive Inspection: `trading_system/merge_predictions.py`

### 4.1. Strategy Key List & Prefix Discovery (Lines 12–21 & 774–788)
- `ALL_31_STRATEGIES` list contains 31 elements from `regression` to `earnings_tone_drift` in exact canonical sequence.
- `KNOWN_STRATEGY_PREFIXES` contains all 31 filename stems plus helper and legacy prefixes.
- **Status:** **Verified.**

### 4.2. Main Execution Merge Sequence (Lines 863–903)
In `main()`:
1. `merge_pipeline_result(result_dir, target_dirs)` [1. regression]
2. `merge_ensemble_predictions(result_dir, target_dirs)`
3. `merge_surge_predictions(result_dir, target_dirs)` [2. surge]
4. `merge_vcp_ml_predictions(result_dir, target_dirs)` [5. vcp_ml]
5. `merge_vcp_patterns(result_dir, target_dirs)` [4. vcp_rule]
6. `merge_lead_lag_predictions(result_dir, target_dirs)` [3. lead_lag]
7. `merge_generic_strategy_files` (calls for strategies 6, 8, 9, 10, 11, 12, 13, 14, 7, 15, ..., 31)

**Observation & Recommendation:**  
While all files are merged correctly, reordering the calls in `main()` to follow strict 1..31 sequence (1: pipeline_result, 2: surge, 3: lead_lag, 4: vcp_patterns, 5: vcp_ml, 6: lstm, 7: stat_arb, 8: sector, 9: rim, 10: event_driven, ..., 31: earnings_tone_drift) will enhance architectural elegance and clean logging output.

---

## 5. Deep-Dive Inspection: Correlation Monitors

### 5.1. `trading_system/src/ai/correlation_monitor.py`
- `ALL_31_STRATEGIES` (lines 14–23): 31 strategies in canonical order.
- `STRATEGY_SCORE_COL_MAP` (lines 27–59): Exact mapping of 31 strategy keys to DataFrame score columns (`reg_score`, `surge_score`, ..., `earnings_tone_drift_score`).
- `SCORE_COL_STRATEGY_MAP` (line 62): Inverse mapping.
- Rolling correlation smoothing, VIF computation, and Effective Strategy Count $N_{eff} = \frac{(\sum w_i)^2}{\sum_{i,j} w_i w_j \rho_{ij}}$ fully operational.

### 5.2. `trading_system/src/analysis/strategy_correlation_monitor.py`
- Implements Meucci (2009) PCA Entropy Effective Strategy Count:
  $$p_i = \frac{\lambda_i}{\sum \lambda}, \quad \text{ESC} = \exp\left(-\sum p_i \ln p_i\right)$$
- Computes Spearman rank correlation matrix across all active strategy score columns and writes `strategy_correlation_matrix.json`.

---

## 6. Verification of CI Scripts & Pipeline Verification Lists

| File | Current State | Target Alignment (Milestone 2 F04/F05) |
|---|---|---|
| `trading_system/scripts/verify_gha_artifacts.py` | Lists 23 strategies (`STRATEGIES` lines 29-35) | Expand to all 31 strategies in canonical 1..31 order |
| `.agents/skills/gha-artifact-verifier/SKILL.md` | Lists 23 strategies | Expand strategy catalog to all 31 strategies |
| `trading_system/run_pipeline.py:STRATEGY_REGISTRY` | Strategy 30 & 31 labels swapped (`earnings_tone_drift` 30, `darkpool` 31) | Align labels: 30: `darkpool`, 31: `earnings_tone_drift` |
| `trading_system/run_pipeline.py:verification_files` | Checks 13 files (lines 4338-4352) | Expand to check all 31 strategy files in canonical order |

---

## 7. Test Suite Execution & Verification

Ran pytest on test suites:
- `tests/test_merge_generic_strategies.py` (30 strategy merge tests, header preservation, edge cases)
- `tests/test_strategy_correlation_monitor.py` (ESC orthogonal/collinear, correlation summary)
- `tests/test_merge_predictions_stress.py` (38 adversarial stress tests on corrupted input, BOM, mixed line endings, extreme floats)

**Results:**
- `test_merge_generic_strategies.py` & `test_strategy_correlation_monitor.py`: **54 passed in 32.78s**
- `test_merge_predictions_stress.py`: **38 passed in 1.72s**
- **Total: 92 passed, 0 failed, 100% green.**

---

## 8. Conclusion

Milestone 2 core components (`generate_report.py`, `merge_predictions.py`, and `correlation_monitor.py`) have sound foundations with `generate_report.py` already 100% synchronized to the 1..31 canonical master sequence. The remaining tasks for Milestone 2 implementation are clearly scoped to:
1. Reordering merge calls in `merge_predictions.py:main()`.
2. Swapping the 30/31 display labels in `run_pipeline.py:STRATEGY_REGISTRY`.
3. Expanding `verify_gha_artifacts.py`, `SKILL.md`, and `run_pipeline.py:verification_files` to encompass all 31 strategies in 1..31 order.
