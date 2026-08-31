# Handoff Report: Milestone 2 (R2: Dashboard & Merge Sequence Synchronization)

## 1. Observation
- **`trading_system/generate_report.py`**:
  - Lines 1373–1405: `STRATEGY_METADATA` lists exactly 31 strategies from `("regression", 1, ...)` to `("earnings_tone_drift", 31, ...)` in exact canonical sequence 1..31.
  - Lines 2014–2045 and Lines 2085–2116: Table headers `<th>` (1. Reg to 31. ToneDrift) and table row cells `<td>` (`erow.reg` to `erow.earnings_tone_drift`) match the 31 canonical strategies in 1:1 order.
  - Lines 3728–3761 and Lines 3766–4076: Individual strategy tab navigation buttons (`regression` to `tonedrift`) and tab panels (`panel-regression` to `panel-tonedrift`) match the 31 canonical strategies in exact 1..31 sequence.
  - Lines 1970–2002 and Lines 4941–4973: Stock drawer factor decomposition dictionary and autocomplete search index map all 31 strategies from `"1. XGBoost 회귀"` to `"31. Tone Drift"`.
- **`trading_system/merge_predictions.py`**:
  - Lines 12–21: `ALL_31_STRATEGIES` list contains 31 strategy keys in exact canonical sequence 1..31.
  - Lines 774–788: `KNOWN_STRATEGY_PREFIXES` covers all 31 strategy prefixes.
  - Lines 863–903: `main()` function merges all 31 strategy outputs across markets, though merge function invocations are executed in historical order rather than strictly 1..31 (e.g. `merge_surge_predictions` [2] then `merge_vcp_ml_predictions` [5] then `merge_vcp_patterns` [4] then `merge_lead_lag_predictions` [3], with `stat_arb_predictions.txt` [7] after `short_term_reversal` [14]).
- **`trading_system/src/ai/correlation_monitor.py` & `src/analysis/strategy_correlation_monitor.py`**:
  - `src/ai/correlation_monitor.py` Lines 14–23: `ALL_31_STRATEGIES` defines the canonical 1..31 sequence.
  - `src/ai/correlation_monitor.py` Lines 27–59: `STRATEGY_SCORE_COL_MAP` maps all 31 strategies to dataframe score columns (`reg_score` to `earnings_tone_drift_score`).
  - `src/analysis/strategy_correlation_monitor.py`: Computes Meucci (2009) PCA Entropy Effective Strategy Count across numeric score columns.
- **CI / Verification Scripts**:
  - `trading_system/scripts/verify_gha_artifacts.py` Lines 29–35: `STRATEGIES` currently has 23 strategies in non-canonical order.
  - `trading_system/run_pipeline.py` Lines 3222–3223: `earnings_tone_drift` is titled "Strategy 30" and `darkpool` is titled "Strategy 31" (swapped relative to canonical order).
  - `trading_system/run_pipeline.py` Lines 4338–4352: `verification_files` checks 13 files.
- **Automated Tests**:
  - Command: `.venv\Scripts\python -m pytest tests/test_merge_generic_strategies.py tests/test_strategy_correlation_monitor.py` -> 54 passed in 32.78s.
  - Command: `.venv\Scripts\python -m pytest tests/test_merge_predictions_stress.py` -> 38 passed in 1.72s.

## 2. Logic Chain
1. *From Observation 1:* `generate_report.py` already possesses full 1..31 canonical sequence alignment across metadata, table columns, navigation tabs, and stock drawer decomposition dictionaries. Therefore, dashboard generation logic is already synchronized and requires no sequence fixes.
2. *From Observation 2:* `merge_predictions.py` already recognizes all 31 strategies in its master list and handles all 31 strategy outputs during merging without data loss. Reordering the function calls in `main()` to follow 1..31 order will establish complete execution parity with the canonical specification.
3. *From Observation 3:* Both correlation monitors already support the full 31 strategies and have full score mappings, ensuring accurate rolling correlation matrices, VIF metrics, and Meucci ESC calculation across all 31 factors.
4. *From Observation 4:* The discrepancies in `verify_gha_artifacts.py`, `SKILL.md`, and `run_pipeline.py:verification_files` precisely match the planned tasks for Milestone 2 (Features F04 and F05).

## 3. Caveats
- No caveats regarding 31-strategy sequence definitions. All 31 strategies have consistent IDs across `PROJECT.md`, `generate_report.py`, `merge_predictions.py`, and `correlation_monitor.py`.
- Darkpool strategy file naming supports both `darkpool_predictions.txt` and `hft_order_flow_predictions.txt` for backwards compatibility.

## 4. Conclusion
Milestone 2 (R2: Dashboard & Merge Sequence Synchronization) is well-aligned with canonical specifications. The dashboard generator (`generate_report.py`) is already 100% compliant with the 1..31 sequence. Milestone 2 implementation should focus on:
1. Reordering merge function calls in `merge_predictions.py:main()` to 1..31 canonical order.
2. Swapping the 30/31 display labels in `run_pipeline.py:STRATEGY_REGISTRY` (30: `darkpool`, 31: `earnings_tone_drift`).
3. Expanding `verify_gha_artifacts.py` and `SKILL.md` from 23 to 31 strategies in canonical order (F04).
4. Expanding `run_pipeline.py:verification_files` to check all 31 strategy output files (F05).

## 5. Verification Method
- Run pytest verification suite:
  ```powershell
  .venv\Scripts\python -m pytest tests/test_merge_generic_strategies.py tests/test_strategy_correlation_monitor.py tests/test_merge_predictions_stress.py -v
  ```
- Inspect files:
  - `trading_system/generate_report.py` (lines 1373–1405, 2085–2116, 3728–3761)
  - `trading_system/merge_predictions.py` (lines 12–21, 863–903)
  - `trading_system/src/ai/correlation_monitor.py` (lines 14–23, 27–59)
- Invalidation Condition: Any divergence in strategy numbering, missing strategy keys, or failed test assertions in `tests/`.
