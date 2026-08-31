# Handoff Report — Milestone 2 Explorer (R2 Canonical Strategy Sequence)

**Author**: `teamwork_preview_explorer_m2_1`  
**Date**: 2026-09-01 (KST)  
**Parent Conversation ID**: `b672d6c7-56c6-40df-9cff-af49d8b4ec1c`  
**Handoff Type**: Hard (Investigation Complete)  

---

## 1. Observation

1. **`run_pipeline.py:3201-3231` (`STRATEGY_REGISTRY`)**:
   - `STRATEGY_REGISTRY` contains entries from Strategy 10 to 37, placing `earnings_tone_drift` as Strategy 30 (line 3222) and `darkpool` as Strategy 31 (line 3223, file: `hft_order_flow_predictions.txt`).
   - Strategy 6 `lstm` is appended at line 3230 at the very bottom after Strategy 37.
2. **`run_pipeline.py:4338-4352` (`verification_files`)**:
   - Lists only 13 files (`pipeline_result.txt`, `surge_predictions.txt`, `lead_lag_predictions.txt`, `vcp_patterns.txt`, `vcp_ml_predictions.txt`, `stat_arb_predictions.txt`, `sector_predictions.txt`, `rim_predictions.txt`, `arm_factor_predictions.txt`, `card_factor_predictions.txt`, `latr_factor_predictions.txt`, `inst_foreign_sector_predictions.txt`, `ensemble_predictions.txt`).
   - Completely omits Strategies 6, 10–14, 19–31, `strategy_data_coverage_report.txt`, and `portfolio_allocation.txt`.
3. **`run_pipeline.py:4045-4077, 4108, 4173` (`_STRAT_DISPLAY_MAP` & Table Headers)**:
   - `_STRAT_DISPLAY_MAP` defines 31 strategies in exact order 1..31 with `darkpool` at #30 and `earnings_tone_drift` at #31.
   - Table header and data rows in lines 4108, 4147-4151, 4173, 4210-4215 format columns in 1..31 canonical order.
4. **`AGENTS.md:38-39, 119-120, 193-194`**:
   - Lines 38–39 list `| **30** | Earnings Tone Drift | ...` and `| **31** | High-Frequency Execution | ...`.
   - Mermaid diagram lines 119–120 define `ToneDrift["30. Earnings Tone Drift"]` and `HFT["31. HFT Order Flow"]`.
   - Key Files table lines 193–194 list `tone_drift.py` before `darkpool_tracker.py`.
5. **`trading_system/scripts/verify_gha_artifacts.py:29-35`**:
   - `STRATEGIES` list only contains 23 strategies, omitting Strategies 24–31 (`accruals_quality`, `short_squeeze`, `valueup_catalyst`, `trend_efficiency`, `gamma_squeeze`, `insider_buying`, `darkpool`, `earnings_tone_drift`).
6. **`merge_predictions.py:860-905`**:
   - Already includes dedicated merge handlers for all 31 strategies plus darkpool aliases (`hft_order_flow_predictions.txt` and `darkpool_predictions.txt`).

---

## 2. Logic Chain

1. From **Observation 4**, `AGENTS.md` inverts the sequence of Strategies 30 and 31 relative to `PROJECT.md:40` (`30: darkpool, 31: earnings_tone_drift`). Updating `AGENTS.md` lines 38–39, 119–120, and 193–194 aligns project documentation with the canonical master sequence.
2. From **Observation 1**, `STRATEGY_REGISTRY` in `run_pipeline.py` currently inverts Strategies 30 and 31 and appends Strategy 6 `lstm` at the end. Swapping `darkpool` to #30 (`file: darkpool_predictions.txt`), `earnings_tone_drift` to #31 (`file: earnings_tone_drift_predictions.txt`), and placing `lstm` at Strategy 6 ensures deterministic evaluation order and naming consistency.
3. From **Observation 2**, `verification_files` in `run_pipeline.py` only validates 13 out of 34 expected outputs, leaving 18 strategy outputs unverified at pipeline completion. Expanding `verification_files` to all 31 strategy `.txt` files plus `ensemble_predictions.txt`, `strategy_data_coverage_report.txt`, and `portfolio_allocation.txt` guarantees full end-to-end artifact integrity.
4. From **Observation 5**, expanding `verify_gha_artifacts.py` from 23 to 31 strategies satisfies acceptance criterion F04, enabling CI and local scripts to verify 100% of strategy artifacts.

---

## 3. Caveats

- `stat_arb_predictions.txt` is generated only when statistically cointegrated pairs are detected. In `run_pipeline.py`, non-critical files log a warning rather than raising a critical exception if empty or missing, preventing pipeline crashes during non-cointegrated market regimes.
- Backward compatibility for `hft_order_flow_predictions.txt` alias is preserved in `generate_report.py`, `merge_predictions.py`, and `pipeline.yml`.

---

## 4. Conclusion

Milestone 2 requires targeted edits across three primary files (`run_pipeline.py`, `AGENTS.md`, `verify_gha_artifacts.py`):
1. Align `STRATEGY_REGISTRY` to canonical order: `lstm` as #6, `darkpool` as #30 (`darkpool_predictions.txt`), `earnings_tone_drift` as #31 (`earnings_tone_drift_predictions.txt`).
2. Expand `verification_files` in `run_pipeline.py:4338` from 13 to all 31 strategy files + 3 system files (34 files total).
3. Align `AGENTS.md` lines 38–39, 119–120, and 193–194 to #30 Darkpool & HFT and #31 Earnings Tone Drift.
4. Expand `verify_gha_artifacts.py` and `SKILL.md` from 23 to all 31 strategies.

---

## 5. Verification Method

To independently verify after implementation:
1. `pytest tests/test_merge_generic_strategies.py -v`
2. `pytest tests/test_report_ux_and_rounding.py -v`
3. `python trading_system/scripts/verify_gha_artifacts.py --result-dir trading_system/result --gh-pages-dir gh-pages`
4. Inspect `trading_system/run_pipeline.py` lines 3201–3231 and 4338–4354 to confirm exact canonical order and file list expansion.
