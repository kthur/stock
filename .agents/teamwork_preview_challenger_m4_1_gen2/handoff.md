# Handoff Report — Challenger M4_1 (StrategyCoverageAnalyzer Stress-Test)

## 1. Observation

### Codebase Inspection & Line References
Target file: `trading_system/src/analysis/coverage_analyzer.py` (`StrategyCoverageAnalyzer`)

- **Observation 1 (Missing Reasons Dict Insertion & Price History Fallback)**:
  Lines 128–138 of `coverage_analyzer.py`:
  ```python
  for sym in missing_syms:
      sym_str = str(sym)
      p_df = prices_dict.get(sym_str) if prices_dict else None
      has_price = (p_df is not None and len(p_df) >= 200)

      if not has_price:
          no_price_cnt += 1
      elif strat in ['rim_valuation', 'mq_factor'] and not self._has_symbol_fundamental_data(features_df, sym_str):
          no_fund_cnt += 1
      else:
          other_cnt += 1
  ```
  When `prices_dict` is `None` (which is default if omitted in caller options), `p_df` is `None` and `has_price` is `False`. As a result, `if not has_price:` is evaluated FIRST for every missing symbol, incrementing `no_price_cnt`. The `elif` branch checking `_has_symbol_fundamental_data` is NEVER reached.

- **Observation 2 (Absence of `STRATEGY_NOT_COMPUTED` and Mislabeling as `STRATEGY_SIGNAL_NEUTRAL`)**:
  Lines 143–149 of `coverage_analyzer.py`:
  ```python
  if other_cnt > 0:
      if strat == 'iv_skew':
          reasons['NO_OPTIONS_CHAIN'] = other_cnt
      elif strat == 'stat_arb':
          reasons['NO_COINTEGRATED_PAIR'] = other_cnt
      else:
          reasons['STRATEGY_SIGNAL_NEUTRAL'] = other_cnt
  ```
  The reason string `'STRATEGY_NOT_COMPUTED'` does NOT exist anywhere in `coverage_analyzer.py`. When a strategy score is `NaN` (uncomputed score) but the symbol has valid price history, `coverage_analyzer.py` classifies the missing reason as `STRATEGY_SIGNAL_NEUTRAL` (for 12 of 14 strategies).

- **Observation 3 (Primary Missing Reason Reporting Bug)**:
  Lines 181–183 of `coverage_analyzer.py`:
  ```python
  reasons = s_info.get('reasons', {})
  top_reason = list(reasons.keys())[0] if reasons else "None (100% Valid)"
  lines.append(f"{s_name:<22}{v_cnt:<15}{m_cnt:<15}{cov:>6.1f}%          {top_reason:<30}")
  ```
  `top_reason` takes `list(reasons.keys())[0]`, which relies strictly on Python dictionary insertion order (where `INSUFFICIENT_PRICE_HISTORY` is inserted first, followed by `NO_FUNDAMENTAL_DATA`, followed by `STRATEGY_SIGNAL_NEUTRAL`). It does NOT select the reason with the maximum count (`max(reasons, key=reasons.get)`).

- **Observation 4 (Target DataFrame Length Mismatch)**:
  Lines 76 & 104 of `coverage_analyzer.py`:
  ```python
  total_symbols = len(ensemble_df)
  ...
  missing_cnt = total_symbols - valid_cnt
  cov_pct = (valid_cnt / total_symbols * 100.0) if total_symbols > 0 else 0.0
  ```
  If `raw_scores` (`target_df`) has a higher row count than `ensemble_df`, `valid_cnt` can exceed `total_symbols`, leading to negative `missing_cnt` and `cov_pct > 100.0%`.

- **Observation 5 (Pytest Command Environment)**:
  Executing `.venv\Scripts\python.exe -m pytest tests/` via container runner produced system-level error:
  `CORTEX_STEP_TYPE_RUN_COMMAND: sandbox configuration error: readwrite stock: non-absolute file path`

---

## 2. Logic Chain

1. **Fundamental Data Missingness Suppression**:
   From Observation 1, when `prices_dict` is omitted or `None`, `has_price` evaluates to `False`. The `if not has_price:` condition short-circuits execution before `_has_symbol_fundamental_data` can be evaluated. Therefore, even when `features_df` is supplied and lacks fundamental data for symbols, `no_fund_cnt` remains `0` and `NO_FUNDAMENTAL_DATA` is never populated. All fundamental missingness is falsely reported as `INSUFFICIENT_PRICE_HISTORY`.

2. **Misclassification of Missing Strategy Computations**:
   From Observation 2, `STRATEGY_NOT_COMPUTED` is entirely absent from the code. For uncomputed strategy models (where output score is `NaN` despite having 200+ price bars), `coverage_analyzer.py` defaults to `STRATEGY_SIGNAL_NEUTRAL`. This misrepresents missing predictions (NaN) as neutral model evaluations (0.0).

3. **Inaccurate Primary Missing Reason Selection**:
   From Observation 3, `list(reasons.keys())[0]` takes the first key inserted into the `reasons` dictionary. Since `no_price_cnt` is processed before `no_fund_cnt`, if even 1 symbol out of 1000 is missing price data while 999 symbols are missing fundamental data, `INSUFFICIENT_PRICE_HISTORY` is inserted first. `list(reasons.keys())[0]` will report `INSUFFICIENT_PRICE_HISTORY` as the primary reason for the strategy, misinforming users about the actual dominant data bottleneck.

4. **Inexact Missingness Counts under Data Mismatch**:
   From Observation 4, `total_symbols` is derived solely from `len(ensemble_df)`, while `valid_cnt` is calculated over `target_df`. If `target_df` (raw scores) contains unaligned rows or candidates omitted from `ensemble_df`, `valid_cnt` can exceed `total_symbols`, producing invalid negative missing counts and illegal percentages (> 100%).

---

## 3. Caveats

- `run_command` tool execution was blocked by the system runtime's sandbox configuration error (`sandbox configuration error: readwrite stock: non-absolute file path`). All tests were constructed as clean, standalone pytest and empirical test files in the agent working directory (`.agents/teamwork_preview_challenger_m4_1_gen2/`).
- Real-world database connections to DART / yfinance were not queried live during this challenger execution; synthetic DataFrames matching exact production schemas were used.

---

## 4. Conclusion

`StrategyCoverageAnalyzer` successfully implements basic 14-strategy coverage counting, but exhibits **4 significant flaws in missingness reason categorization and report output**:
1. **`NO_FUNDAMENTAL_DATA` is suppressed** when `prices_dict` is `None` (the default call mode in `run_pipeline.py`).
2. **`STRATEGY_NOT_COMPUTED` is missing**, causing uncomputed strategy scores to be miscategorized as `STRATEGY_SIGNAL_NEUTRAL`.
3. **`generate_coverage_report` misreports the primary missing reason** due to dictionary insertion order rather than picking the maximum count.
4. **Potential overflow/negative missing counts** when `raw_scores` length differs from `ensemble_df`.

### Recommended Fixes for Implementation Team:
1. Check fundamental data availability regardless of whether `prices_dict` is `None` (or order price checks and fundamental checks logically).
2. Add explicit `STRATEGY_NOT_COMPUTED` reason when a strategy column has NaN scores for symbols with sufficient price history.
3. Update `top_reason = max(reasons, key=reasons.get)` in `generate_coverage_report`.
4. Ensure `total_symbols` equals `len(target_df)` or align `target_df` and `ensemble_df` indices before analyzing.

---

## 5. Verification Method

To verify these empirical observations and test results, run the created empirical test harness and pytest suite using Python in the project root:

1. **Run Empirical Stress Test Harness**:
   ```bash
   .venv\Scripts\python.exe .agents\teamwork_preview_challenger_m4_1_gen2\stress_test_coverage_analyzer.py
   ```
2. **Run Pytest Suite**:
   ```bash
   .venv\Scripts\python.exe -m pytest .agents\teamwork_preview_challenger_m4_1_gen2\test_coverage_analyzer_empirical.py -v
   .venv\Scripts\python.exe -m pytest trading_system/tests/test_kst_and_coverage_reasoning.py -v
   .venv\Scripts\python.exe -m pytest tests/ -v
   .venv\Scripts\python.exe -m pytest trading_system/tests/ -v
   ```
3. **Inspect Output Files**:
   - `d:\Finance\code\stock\.agents\teamwork_preview_challenger_m4_1_gen2\stress_test_coverage_analyzer.py`
   - `d:\Finance\code\stock\.agents\teamwork_preview_challenger_m4_1_gen2\test_coverage_analyzer_empirical.py`
   - `d:\Finance\code\stock\trading_system\src\analysis\coverage_analyzer.py`

---

## Challenge Summary

**Overall risk assessment**: MEDIUM

## Challenges

### [Medium] Challenge 1: Fundamental Missingness Mislabeled as Price History Missingness
- **Assumption challenged**: `analyze_coverage` correctly identifies `NO_FUNDAMENTAL_DATA` when `features_df` is passed.
- **Attack scenario**: Call `analyzer.analyze_coverage(df, features_df=features_df, prices_dict=None)`.
- **Blast radius**: `NO_FUNDAMENTAL_DATA` is 0; 100% of missingness for `rim_valuation` and `mq_factor` is mislabeled as `INSUFFICIENT_PRICE_HISTORY`.
- **Mitigation**: Evaluate `_has_symbol_fundamental_data(features_df, sym_str)` independently of `prices_dict`.

### [Medium] Challenge 2: Missing Strategy Calculations Mislabeled as `STRATEGY_SIGNAL_NEUTRAL`
- **Assumption challenged**: Missing strategy scores (NaN) are distinct from neutral strategy evaluations.
- **Attack scenario**: Feed DataFrame with NaN scores for `vcp_ml` or `regression` for valid symbols.
- **Blast radius**: System reports `STRATEGY_SIGNAL_NEUTRAL` rather than `STRATEGY_NOT_COMPUTED`, giving false impression that model evaluated symbol as neutral.
- **Mitigation**: Introduce `STRATEGY_NOT_COMPUTED` key in `reasons` dict when score is NaN and no price/fundamental defect exists.

### [Low] Challenge 3: Primary Missing Reason Uses Insertion Order Instead of Max Count
- **Assumption challenged**: `generate_coverage_report` displays the most dominant missing reason.
- **Attack scenario**: 1 symbol missing price data, 99 symbols missing fundamental data.
- **Blast radius**: Report output displays `INSUFFICIENT_PRICE_HISTORY` as the primary reason because it was inserted first.
- **Mitigation**: Change `list(reasons.keys())[0]` to `max(reasons, key=reasons.get)`.
