# Handoff Report — Explorer M2 (Ensemble Scorer Engine & Optuna HPO Tuner Quantitative Audit)

## Executive Summary

This quantitative audit evaluated `trading_system/src/ai/ensemble_scorer.py` (`EnsembleScoringEngine`) and `trading_system/src/ai/optuna_tuner.py` (`OptunaStrategyTuner`). 
10 vulnerabilities were identified and rated across mathematical soundness, strategy inclusion consistency, 2D regime matrix transitions, decision rationale integrity, and Optuna HPO objective function validity.

### Risk Summary Table
| # | Vulnerability | Severity | Target File | Line Numbers | Core Flaw |
|---|---------------|----------|-------------|--------------|-----------|
| 1 | Syntax Error in `REGIME_2D_WEIGHTS` Table | **HIGH** | `ensemble_scorer.py` | 208–212 | Un-nested dictionary key syntax error outside state dict |
| 2 | Silent Truncation of 3/17 Strategies (17 vs 14 Discrepancy) | **HIGH** | `ensemble_scorer.py` | 34–212, 421–436, 787, 806–821 | `arm_factor`, `card_factor`, `latr_factor` dropped from base weights & dataframe merging |
| 3 | Gamed / Invalid Objective Metric in VCP Rule HPO | **HIGH** | `optuna_tuner.py` | 313–334 | Maximizes sum of arbitrary weight constants rather than pattern accuracy or return |
| 4 | Selection Bias & Zero Cross-Validation in Lead-Lag HPO | **HIGH** | `optuna_tuner.py` | 243–284 | Filters correlation by trial threshold before computing mean; zero temporal split |
| 5 | State Mutation Side-Effect in Decision Rationale Summary | **MEDIUM** | `ensemble_scorer.py` | 526, 466–485 | Read-only summary function mutates `self._prev_weights` and writes to disk |
| 6 | Incomplete Multi-Model HPO (LightGBM/CatBoost Untuned) | **MEDIUM** | `optuna_tuner.py` | 83–128, 162–211 | Only tunes XGBoost; copies params blindly to LightGBM/CatBoost |
| 7 | Un-Cost-Adjusted Ranking in Multi-Market Selection | **MEDIUM** | `ensemble_scorer.py` | 912–948 | `sort_values` ranks by raw `ensemble_score` rather than cost-deducted net return |
| 8 | Sluggish EMA Regime Transition & Disk Persistence Lag | **LOW/MED** | `ensemble_scorer.py` | 256, 466–475 | `alpha=0.2` requires >10 sessions to adapt to regime shifts; anchors to stale disk state |
| 9 | Omission of Downside / Drawdown Risk Metrics in HPO | **LOW/MED** | `optuna_tuner.py` | Throughout | Absence of Sortino ratio and Max Drawdown penalties in objective functions |
| 10 | Potential Temporal Leakage in Panel Data `TimeSeriesSplit` | **LOW** | `optuna_tuner.py` | 130–144, 213–230 | Flat row-count splits on multi-symbol panel datasets without date-grouping safeguards |

---

## 1. Observation

### 1.1 Syntax Error in `REGIME_2D_WEIGHTS` Table (`ensemble_scorer.py:208-212`)
```python
208:             'latr_factor': 0.06
209:         }
210:             'short_term_reversal': 0.04
211:         }
212:     }
```
*Observation*: Line 209 closes the `'BULL_HIGH_VOL'` dictionary. Line 210 contains `'short_term_reversal': 0.04` outside of any key mapping. Line 211 closes `REGIME_2D_WEIGHTS`. Line 212 contains an extra closing brace `}`.

### 1.2 Strategy Count Discrepancy & Silent Data Truncation (`ensemble_scorer.py`)
- In `REGIME_WEIGHTS` (lines 34–92) & `REGIME_2D_WEIGHTS` (lines 95–212): 17 strategies are declared (`regression`, `surge`, `lead_lag`, `vcp_rule`, `vcp_ml`, `lstm`, `stat_arb`, `sector_rotation`, `rim_valuation`, `event_driven`, `mq_factor`, `iv_skew`, `order_flow`, `short_term_reversal`, `arm_factor`, `card_factor`, `latr_factor`).
- In `get_base_weights()` (lines 421–436):
```python
res = {
    'regression': w.get('regression', 0.10),
    'surge': w.get('surge', 0.05),
    'lead_lag': w.get('lead_lag', 0.05),
    'vcp_rule': w.get('vcp_rule', 0.05),
    'vcp_ml': w.get('vcp_ml', 0.08),
    'lstm': w.get('lstm', 0.08),
    'stat_arb': w.get('stat_arb', 0.10),
    'sector_rotation': w.get('sector_rotation', 0.08),
    'rim_valuation': w.get('rim_valuation', 0.10),
    'event_driven': w.get('event_driven', 0.07),
    'mq_factor': w.get('mq_factor', 0.08),
    'iv_skew': w.get('iv_skew', 0.04),
    'order_flow': w.get('order_flow', 0.06),
    'short_term_reversal': w.get('short_term_reversal', 0.06),
}
```
- In `combine_predictions()` (lines 787 & 806–821):
```python
dfs = [reg_df_copy, s_df_copy, ll_df_copy, vr_df, v_df, l_df, sa_df, sec_df, r_val_df, ev_df, m_df, iv_df, of_df, rev_df]
strategy_cols = [
    ('regression', 'reg_score'), ('surge', 'surge_score'), ('lead_lag', 'll_score'),
    ('vcp_rule', 'vcp_rule_score'), ('vcp_ml', 'vcp_ml_score'), ('lstm', 'lstm_score'),
    ('stat_arb', 'stat_arb_score'), ('sector_rotation', 'sector_score'), ('rim_valuation', 'rim_score'),
    ('event_driven', 'event_score'), ('mq_factor', 'mq_score'), ('iv_skew', 'iv_skew_score'),
    ('order_flow', 'order_flow_score'), ('short_term_reversal', 'reversal_score'),
]
```
`arm_factor`, `card_factor`, and `latr_factor` are omitted from `res`, omitted from `dfs`, and omitted from `strategy_cols`.

### 1.3 Metric Gaming in Strategy 4 VCP Rule HPO (`optuna_tuner.py:313-334`)
```python
318: w_dec = trial.suggest_float('decreasing_weight', 15.0, 35.0)
319: w_vol = trial.suggest_float('volume_weight', 10.0, 25.0)
...
330: s = (w_dec if decreasing else 0.0) + w_vol
331: scores.append(s)
332: return float(np.mean(scores)) if scores else 0.0
```
*Observation*: The objective function computes `s` as `(w_dec if decreasing else 0.0) + w_vol`, which is a linear combination of trial weight parameters. No future price target or return is evaluated.

### 1.4 Selection Bias in Strategy 3 Lead-Lag HPO (`optuna_tuner.py:243-284`)
```python
248: corr_cutoff = trial.suggest_float('corr_threshold', 0.1, 0.6)
...
280: if not np.isnan(r) and abs(r) >= corr_cutoff:
281:     corrs.append(abs(r))
282: return float(np.mean(corrs)) if corrs else 0.0
```
*Observation*: `corr_cutoff` is selected by Optuna. Only correlations `>= corr_cutoff` are appended to `corrs`. `np.mean(corrs)` is returned. No train/validation temporal split is used.

### 1.5 Rationale Builder State Mutation (`ensemble_scorer.py:526, 466-485`)
```python
526: dyn_weights = self.compute_dynamic_weights_from_sharpe(rolling_sharpes, regime)
```
Inside `compute_dynamic_weights_from_sharpe()`:
```python
474: self._prev_weights = dict(dynamic_weights)
...
481: with open(models_dir / "prev_weights.json", "w", encoding="utf-8") as f:
482:     json.dump(self._prev_weights, f, indent=2)
```
*Observation*: `get_regime_reasoning_summary` calls `compute_dynamic_weights_from_sharpe`, which mutates `self._prev_weights` and writes to `models/prev_weights.json`.

### 1.6 Incomplete Multi-Model Tuning (`optuna_tuner.py:83-128, 162-211`)
```python
104: study_xgb.optimize(xgb_objective, n_trials=n_trials)
106: best_xgb = study_xgb.best_params
110: best_lgb = {'n_estimators': best_xgb.get('n_estimators', 100), ...}
118: best_cat = {'iterations': best_xgb.get('n_estimators', 100), ...}
```
*Observation*: Optuna studies are created only for XGBoost (`study_xgb`, `study_surge`). LightGBM and CatBoost hyperparameter dictionaries are constructed by copying parameters from the XGBoost study result.

### 1.7 Sorting on Un-Cost-Adjusted Raw Score (`ensemble_scorer.py:912-948`)
```python
912: cost_series = merged.apply(_get_cost_pct, axis=1)
913: merged['ensemble_expected_return'] = (raw_exp_ret - cost_series * 100.0).clip(lower=0.0, upper=50.0)
...
948: merged = merged.sort_values(by='ensemble_score', ascending=False).reset_index(drop=True)
```
*Observation*: Transaction costs (0.60% to 1.30%) are deducted to compute `ensemble_expected_return`. However, `sort_values` sorts output rows by `ensemble_score` (raw un-adjusted score).

---

## 2. Logic Chain

1. **Syntax Error**:
   - `ensemble_scorer.py` lines 208-212 contain an unclosed dictionary block followed by an orphaned string key.
   - Parsing this block raises `SyntaxError`. In a standard execution environment without pre-cached byte code, module loading halts immediately.

2. **17 vs 14 Strategy Truncation**:
   - The regime matrices assign weights across 17 strategies. Specifically, `arm_factor`, `card_factor`, and `latr_factor` receive ~20% total weight allocation in `REGIME_WEIGHTS` and `REGIME_2D_WEIGHTS`.
   - `get_base_weights()` constructs a dictionary of only 14 hardcoded strategies, dropping the 3 strategies.
   - The remaining 14 strategy weights are re-normalized to 1.0, shifting allocation away from designed regime weights.
   - `combine_predictions()` receives `arm_df`, `card_df`, and `latr_df` in its signature, but never appends them to the dataframe merge list `dfs` nor adds them to `strategy_cols`.
   - As a result, data for ARM, CARD, and LATR strategies is completely ignored during inference, while documentation and config claim a 17-strategy ensemble.

3. **VCP Rule Objective Gaming**:
   - `tune_strategy_4_vcp_rule` aims to tune VCP rule detection parameters using Optuna.
   - The objective function returns `np.mean(scores)` where `score = (w_dec if decreasing else 0.0) + w_vol`.
   - `w_dec` and `w_vol` are the decision variable weights proposed by the trial (up to 35.0 and 25.0).
   - Because Optuna is instructed to `direction='maximize'`, the optimizer learns that higher trial inputs (`w_dec=35.0`, `w_vol=25.0`) yield higher objective values.
   - The optimization process does not evaluate pattern predictive power or asset returns. It is mathematically guaranteed to hit the upper search boundary of the trial parameters.

4. **Lead-Lag Selection Bias & Missing Split**:
   - In `tune_strategy_3_lead_lag`, Optuna proposes `corr_threshold` between 0.1 and 0.6.
   - The objective function calculates the mean of absolute correlations that exceed `corr_threshold`.
   - Setting `corr_threshold = 0.60` filters out all lower correlations (e.g., 0.2, 0.3), leaving only values >= 0.60. The mean of values >= 0.60 is higher than the mean of values >= 0.10.
   - Maximizing this mean forces Optuna to select the maximum threshold (0.60), introducing selection bias.
   - Furthermore, the correlation calculation runs over the full dataset without a temporal train-test split (`TimeSeriesSplit`), causing overfitting.

5. **Rationale Summary State Mutation**:
   - `get_regime_reasoning_summary()` is called during logging or report generation.
   - It invokes `compute_dynamic_weights_from_sharpe()`.
   - Inside `compute_dynamic_weights_from_sharpe()`, `self._prev_weights` is updated and saved to `models/prev_weights.json`.
   - Calling a diagnostic display function mutates the EMA state and overwrites persistent disk weights, altering subsequent live execution behavior.

6. **Un-Cost-Adjusted Portfolio Ranking**:
   - `combine_predictions()` computes market-specific transaction costs (`KONEX`: 1.30%, `KOSDAQ`: 1.00%, `KOSPI`: 0.85%, `SP500`: 0.60%).
   - The net expected return `ensemble_expected_return` correctly reflects these cost deductions.
   - However, the final ranking step sorts by `ensemble_score` (raw score prior to cost deduction).
   - High-cost market symbols (e.g., KONEX) with high raw scores will rank above low-cost market symbols (e.g., SP500) that offer higher net return after costs.

---

## 3. Caveats

1. **MetaEnsembleLearner Execution**: `MetaEnsembleLearner` fallback logic was inspected. If `MetaEnsembleLearner` fails, execution falls back to `linear_score`. The interactions between 2nd-stage meta-learner weights and 1st-stage linear weights depend on trained meta-weights.
2. **Optuna Execution Environment**: In the current test setup, Optuna studies were evaluated statically and via unit test scripts. Real-world execution behavior depends on `tuned_params.json` presence on disk.

---

## 4. Conclusion

The Ensemble Scorer Engine and Optuna Strategy Tuner provide a structured multi-factor framework, but contain critical defects:
1. **Critical Syntax & Truncation Defect**: `ensemble_scorer.py` contains a syntax error at line 210 and silently drops 3 out of 17 strategies (`arm_factor`, `card_factor`, `latr_factor`) from weight extraction and merging.
2. **HPO Objective Flaws**: Optuna tuning for Strategy 4 (VCP Rule) games its metric by optimizing trial parameter magnitudes rather than strategy returns. Strategy 3 (Lead-Lag) exhibits selection bias and lacks cross-validation splits. Multi-model tuning (LightGBM/CatBoost) is incomplete.
3. **State & Ranking Flaws**: Generating decision rationale summaries alters persistent model state on disk, and portfolio ranking uses raw score rather than cost-deducted net return.

---

## 5. Verification Method

### 5.1 Verification Commands
Run the following test commands from `.venv`:

1. **Verify Syntax & Import**:
   ```bash
   .venv/bin/python -c "import trading_system.src.ai.ensemble_scorer; print('Ensemble scorer import successful')"
   ```
   *Expected outcome*: Must import without `SyntaxError`.

2. **Verify 17-Strategy Inclusion**:
   Inspect `get_base_weights()` and `combine_predictions()` to verify that `arm_factor`, `card_factor`, and `latr_factor` are present in `res`, `dfs`, `strategy_cols`, and `fill_cols`.

3. **Verify Optuna Objective Functions**:
   Inspect `optuna_tuner.py` lines 313–334 (`tune_strategy_4_vcp_rule`) and lines 243–284 (`tune_strategy_3_lead_lag`). Ensure `tune_strategy_4_vcp_rule` evaluates forward returns or pattern hit rates, and `tune_strategy_3_lead_lag` uses fixed correlation evaluation with `TimeSeriesSplit`.

4. **Verify Cost-Adjusted Ranking**:
   Inspect `ensemble_scorer.py` line 948:
   ```python
   merged = merged.sort_values(by='ensemble_expected_return', ascending=False).reset_index(drop=True)
   ```
   Ensure sorting prioritizes net return after transaction costs and slippage.

### 5.2 Invalidation Conditions
- If `REGIME_2D_WEIGHTS` cannot be parsed due to syntax errors at line 210, the build is invalid.
- If `arm_factor`, `card_factor`, or `latr_factor` inputs are dropped during `combine_predictions()`, the 17-strategy ensemble claim is invalid.
- If `get_regime_reasoning_summary()` modifies `models/prev_weights.json`, the read-only reporting contract is violated.
