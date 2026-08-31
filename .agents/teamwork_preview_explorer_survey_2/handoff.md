# Handoff Report: Survey and Investigation of Requirement R2 (31-Strategy Canonical Sequence Unification)

## 1. Observation

Direct code observations across relevant repositories and source files:

1. **`AGENTS.md` (lines 10-43)**:
   - Lists 31 Multi-Factor strategies numbered 1 to 31.
   - Strategy 30 is listed as `Earnings Tone Drift`, Strategy 31 is listed as `High-Frequency Execution` (`darkpool_hft`).
2. **`trading_system/generate_report.py`**:
   - `STRATEGY_METADATA` (lines 1373-1405): Lists 31 strategies with `darkpool` as #30 and `earnings_tone_drift` as #31.
   - HTML Navigation Tabs (lines 3727-3762): Defines 34 strategy tabs (`regression`..`tonedrift`, plus extra 32: `dualcorrection`, 33: `indexrebalance`, 34: `overnightgap`).
   - Strategy Tab Panels (lines 3766-4106): Renders individual panels for all 34 strategies.
   - File loading in `main()` (lines 4850-4885): Reads text files for all strategies.
3. **`trading_system/run_pipeline.py`**:
   - `STRATEGY_REGISTRY` (lines 3200-3231): Configures parallel scoring for strategies 10 to 37, placing `lstm` (Strategy 6) at the bottom.
   - `_STRAT_DISPLAY_MAP` (lines 4045-4077): Prints 31 strategies with `darkpool` as #30 and `earnings_tone_drift` as #31.
   - `ensemble_predictions.txt` header (line 4108): Formats 31 strategy columns `... | Darkpool | ToneDrift`.
   - `verification_files` (lines 4338-4352): Only includes 13 files, skipping strategies 10-14, 19-31.
4. **`trading_system/scripts/verify_gha_artifacts.py`**:
   - `STRATEGIES` list (lines 29-35): Only contains 23 strategies, ordered `["surge", "vcp_ml", "regression", "vcp", "lead_lag", ...]`.
   - `verify_market_strategies()` (lines 270-335) and `verify_gh_pages()` (lines 374-424): Only validate 23 strategies, omitting strategies 24-31 (`accruals_quality`, `short_squeeze`, `valueup_catalyst`, `trend_efficiency`, `gamma_squeeze`, `insider_buying`, `darkpool`, `earnings_tone_drift`).
5. **`skills/gha-artifact-verifier/SKILL.md` (lines 14-39)**:
   - Table lists 23 numbered strategies and collapses 24-31 into a single row "Extended Alpha Factors".
6. **`trading_system/src/ai/correlation_monitor.py` (lines 14-23)**:
   - `ALL_31_STRATEGIES`: Lists the 31 canonical strategy keys with `darkpool` as 30th and `earnings_tone_drift` as 31st.

---

## 2. Logic Chain

1. **Premise**: Requirement R2 mandates unifying the 31 strategies so that calculation, normalization, ensemble weighting, prediction text outputs, and GitHub Pages dashboard tabs follow a single canonical sequence (1 to 31).
2. **Analysis of Core Sequence**:
   - 29 of 31 strategies (1 to 29) are identical in order across `AGENTS.md`, `generate_report.py`, `correlation_monitor.py`, and `ensemble_predictions.txt`.
   - The only swap is between #30 and #31: `AGENTS.md` table lists #30 Tone Drift / #31 HFT Darkpool, while internal metadata and table formatting in `generate_report.py`, `correlation_monitor.py`, `_STRAT_DISPLAY_MAP`, and `ensemble_predictions.txt` columns use #30 Darkpool / #31 Tone Drift.
3. **Analysis of Verification Gaps**:
   - `verify_gha_artifacts.py` and `SKILL.md` were left at 23 strategies from an earlier development phase and need to be updated to the full 31 strategies in 1..31 canonical order.
   - `run_pipeline.py`'s `verification_files` list only checks 13 files and should be updated to check all 31 strategy files.
4. **Analysis of Dashboard Extra Tabs**:
   - `generate_report.py` has 34 tabs in the UI because 3 experimental modules (dual correction, index rebalance, overnight gap) were appended. Unification requires either standardizing to the 31 canonical strategies or explicitly categorizing auxiliary modules.

---

## 3. Caveats

1. **Read-Only Investigation**: No source code changes were made during this turn. Proposed modifications are documented for the implementation team.
2. **Experimental Strategies**: Strategies 32 (`dual_correction`), 33 (`index_rebalance`), and 34 (`overnight_gap_reversal`) exist in `src/core/` and are registered in `strategy_registry.py`. Downstream implementers should ensure removing/collapsing these UI tabs does not break any tests expecting their presence.
3. **Alias Compatibility**: Multiple subsystems accept both short and long names (e.g. `darkpool_predictions.txt` vs `hft_order_flow_predictions.txt`, `vcp` vs `vcp_rule`). Backward compatibility aliases should be preserved.

---

## 4. Conclusion

The 31-strategy sequence is now fully mapped and cataloged. Requirement R2 can be completely fulfilled by applying the unified 1..31 canonical specification detailed in `survey_report.md` across `AGENTS.md`, `run_pipeline.py`, `verify_gha_artifacts.py`, `SKILL.md`, `generate_report.py`, and `reporter.py`.

---

## 5. Verification Method

To independently verify the survey findings:

1. **Inspect strategy sequences and metadata**:
   ```bash
   # Check strategy metadata in generate_report.py
   python -c "from generate_report import STRATEGY_METADATA; print(len(STRATEGY_METADATA), [s[0] for s in STRATEGY_METADATA])"
   
   # Check strategy list in correlation monitor
   python -c "from src.ai.correlation_monitor import ALL_31_STRATEGIES; print(len(ALL_31_STRATEGIES), ALL_31_STRATEGIES)"
   
   # Check verify_gha_artifacts strategies list
   python -c "from scripts.verify_gha_artifacts import STRATEGIES; print(len(STRATEGIES), STRATEGIES)"
   ```
2. **Run verification script**:
   ```bash
   .venv/bin/python trading_system/scripts/verify_gha_artifacts.py --result-dir trading_system/result --gh-pages-dir trading_system/gh-pages
   ```
3. **Run existing test suite**:
   ```bash
   .venv/bin/pytest tests/test_all_16_markets_31_strategies.py tests/test_merge_generic_strategies.py -v
   ```
