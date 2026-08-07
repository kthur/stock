# Handoff Report — M1-2 Empirical Challenge (Financial Engineering & Risk Audit)

**Verdict**: `REQUEST_CHANGES`

## 1. Observation

Empirical testing was executed using `.venv\Scripts\python.exe -m pytest tests/test_challenger_m1_2.py -v`. The test harness evaluated microstructure costs, score calibration, CrisisDetector gating, and 18-strategy text output formatting.

### Observations by Item:

1. **Microstructure Cost Calculations (`_get_cost_pct` in `trading_system/src/ai/ensemble_scorer.py:1137-1224`)**:
   - Command: `.venv\Scripts\python.exe -m pytest tests/test_challenger_m1_2.py::test_microstructure_cost_calculation -v`
   - Result: `PASSED`
   - Verified that `_get_cost_pct` calculates positive, non-negative total cost percentages across KOSPI, KOSDAQ, SP500, NASDAQ, and RUSSELL2000. Under high volatility (`volatility_20d = 0.15`) and low ADV (`volume = 10`, `close = 50,000`), Kyle/Almgren-Chriss market impact calculation properly adds participation rate overflow penalties (+50% per unit above 10% ADV), resulting in high cost deductions that safely suppress net return expectations without producing NaN, infinity, or negative expected return values.

2. **Raw Score Calibration to Expected Return (`trading_system/src/ai/ensemble_scorer.py:1118-1126`)**:
   - Command: `.venv\Scripts\python.exe -m pytest tests/test_challenger_m1_2.py::test_raw_score_calibration_to_expected_return -v`
   - Result: `PASSED`
   - Verified that ensemble scores in `[0, 1]` are multiplied by `_return_multiplier` (20.0% default) to map raw scores into realistic expected returns. The return is clipped to `[0.0, 50.0]`, preventing unrealistic >100% exponential expectations.

3. **CrisisDetector Gating & VIX Override (`trading_system/src/risk/risk_manager.py:124-140`, `trading_system/src/ai/ensemble_scorer.py:424-442`)**:
   - Command: `.venv\Scripts\python.exe -m pytest tests/test_challenger_m1_2.py::test_crisis_detector_vix_override_and_gating_behavior -v`
   - Result: `PASSED` (with vulnerability identified)
   - **Ensemble Scorer VIX Override**: `apply_vix_override()` correctly reduces speculative weights (`surge` -0.10) and boosts defensive weights (`stat_arb` +0.05) when VIX > 30, and zeros out `surge` / `vcp_ml` when VIX > 40.
   - **Vulnerability Found (`VULN-M1-2-01: CrisisDetector Insensitive Gating`)**: In `CrisisDetector.evaluate()`, `vix_score` carries only a 25% weight (`composite = vix_score * 0.25 + dd_score * 0.25 + volume_score * 0.15 + trend_score * 0.10 + macro_score * 0.25`). When VIX spikes to 35.0 alone (without concurrent 20% drawdown or historical macro spike), `composite` evaluates to `0.125`, which is below the `0.25` threshold for `CrisisLevel.WATCH`. Consequently, `CrisisDetector` remains in `CrisisLevel.NONE` state during single-factor VIX market shocks.

4. **18-Strategy Formatting String in `trading_system/run_pipeline.py:2938, 2957, 2979, 2993-2994`**:
   - Command: `.venv\Scripts\python.exe -m pytest tests/test_challenger_m1_2.py::test_18_strategy_formatting_string_inspection -v`
   - Result: `PASSED` (confirming defect existence)
   - **Defect Found (`VULN-M1-2-02: Missing Strategy 18 (IFS) in Prediction Text File Formatting`)**:
     - Line 2938 & Line 2979 header formatting string:
       ```python
       f"{'Rank':<5}{'Symbol':<10}{'Name':<18}{'Ens Score':<12}{'Expected Ret':<14}{'Reg':<5}{'Srg':<5}{'L-L':<5}{'VCP-R':<6}{'VCP-M':<6}{'LSTM':<5}{'S-Arb':<6}{'Sec-R':<6}{'RIM':<5}{'Event':<6}{'MQ':<5}{'IV-Sk':<6}{'Flow':<5}{'Rev':<5}{'ARM':<5}{'CARD':<6}{'LATR':<5}\n"
       ```
       Header contains only 17 strategy column names. Strategy 18 `IFS` (`Inst & Foreign Sector`) is completely missing.
     - Line 2957 & Lines 2993-2994 row format string:
       ```python
       f"{rank:<5}{row['symbol']:<10}{name_str:<18}{row['ensemble_score']*100:>10.1f}%{row['ensemble_expected_return']:>12.2f}%{row['reg_score']*100:>4.0f}%{row['surge_score']*100:>4.0f}%{row['ll_score']*100:>4.0f}%{vcp_rule_val*100:>5.0f}%{row['vcp_ml_score']*100:>5.0f}%{lstm_val*100:>4.0f}%{sa_val*100:>5.0f}%{sec_val*100:>5.0f}%{rim_val*100:>4.0f}%{ev_val*100:>5.0f}%{mq_val*100:>4.0f}%{iv_val*100:>5.0f}%{of_val*100:>4.0f}%{rev_val*100:>4.0f}%{arm_val*100:>4.0f}%{card_val*100:>5.0f}%{latr_val*100:>4.0f}%\n"
       ```
       Row format prints only 17 strategy values and omits `inst_foreign_sector_score` / `IFS`.

---

## 2. Logic Chain

1. **Microstructure & Calibration (Items 1 & 2)**:
   - Observation: `_get_cost_pct` applies STT, SEC fees, bid-ask spread clamping, and Almgren-Chriss participation impact.
   - Inference: In low ADV assets, participation ratio > 10% penalizes trades severely, driving net expected return down and zeroing out top picks for illiquid stocks.
   - Conclusion: Microstructure cost calculation and return calibration function correctly and realistically.

2. **CrisisDetector Composite Gating (Item 3)**:
   - Observation: `vix_score` carries a 0.25 multiplier in `CrisisDetector.evaluate()`.
   - Inference: At VIX = 35.0 (fear level), `vix_score` is 0.50. `0.50 * 0.25 = 0.125`, which is less than the `0.25` WATCH threshold.
   - Conclusion: Unless accompanied by active portfolio drawdown or sudden FX spike, VIX fear spikes alone fail to elevate `CrisisDetector` out of `NONE` status.

3. **18-Strategy Output Column Truncation (Item 4)**:
   - Observation: `run_pipeline.py` lines 2938, 2957, 2979, and 2993-2994 format only 17 strategies (`Reg` through `LATR`).
   - Inference: `ensemble_predictions.txt` and `ensemble_predictions_{MARKET}.txt` fail to display Strategy 18 `IFS` (`Inst & Foreign Sector`).
   - Conclusion: The pipeline output format violates the requirement that all 18 strategy columns are printed to `ensemble_predictions.txt`.

---

## 3. Caveats

- `EnsembleScoringEngine`'s `apply_vix_override()` directly alters strategy ensemble weights when VIX > 30 even if `CrisisDetector` remains in `NONE` state, providing partial risk mitigation at the strategy level.
- Multi-factor severe crises (VIX + FX spike + Drawdown) correctly trigger `ACTIVE` / `SEVERE` crisis gating.

---

## 4. Conclusion

The quantitative financial engineering model (microstructure transaction costs and expected return scaling) is sound and accurate. However, **`REQUEST_CHANGES`** is issued due to two defects:
1. `VULN-M1-2-01`: Insensitive single-factor VIX threshold in `CrisisDetector.evaluate()` (VIX > 30 alone fails to trigger `WATCH` level due to 25% composite weight).
2. `VULN-M1-2-02`: Missing 18th strategy `IFS` (`inst_foreign_sector_score`) column in both table header and row formatting strings in `trading_system/run_pipeline.py`.

---

## 5. Verification Method

To verify these empirical findings:
1. Execute pytest suite:
   ```powershell
   .venv\Scripts\python.exe -m pytest tests/test_challenger_m1_2.py -v
   ```
2. Inspect `trading_system/run_pipeline.py` lines 2938 & 2957:
   - Confirm table header string ends at `LATR` and omits `IFS`.
   - Confirm row formatting string ends at `{latr_val*100:>4.0f}%` and omits `{ifs_val*100}` / `{inst_foreign_sector_score}`.
