# Audit Report: 14-Strategy Dynamic Weighted Ensemble & 2D Market Regime Engine (Requirement R1)

## Executive Summary

This audit evaluates the implementation of Requirement R1 in the Stock Trading System project (`d:\Finance\code\stock`). The scope encompasses:
1. `src/ai/ensemble_scorer.py` (`EnsembleScoringEngine`) and `src/ai/prediction_model.py` (`OnDevicePredictionModel`).
2. Weighting, normalization, and combination of all 14 strategies.
3. The Gaussian Mixture Model (GMM) 2D Market Regime Engine (`src/analysis/regime_detector.py`).
4. Transaction cost subtraction (fees, tax, slippage) and liquidity filtering (SPACs, preferred stocks).
5. Formatting of `ensemble_predictions.txt` with decision rationale.
6. Test suite status and gap analysis.

---

## 1. 14-Strategy Architecture & Score Combination

The 14 strategies evaluated in `EnsembleScoringEngine.calculate_ensemble_score()` are:

| # | Strategy Key | Source Score Column | Normalization / Scaling Method |
|---|--------------|---------------------|--------------------------------|
| 1 | `regression` | `reg_pred` | Percentile ranking `reg_df['reg_pred'].rank(pct=True)` |
| 2 | `surge` | `surge_20d` | Direct probability output `[0.0, 1.0]` |
| 3 | `lead_lag` | `lead_lag_score` | Min-Max normalization `(x - min) / (max - min)` |
| 4 | `vcp_rule` | `vcp_score` / `is_vcp` | Scaled `vcp_score / 100.0` or binary float |
| 5 | `vcp_ml` | `vcp_20d` | Direct probability output `[0.0, 1.0]` |
| 6 | `lstm` | `lstm_score` | Direct probability / score output `[0.0, 1.0]` |
| 7 | `stat_arb` | `stat_arb_score` | Z-score mean-reversion score `[0.0, 1.0]` |
| 8 | `sector_rotation` | `sector_score` | Relative momentum score `[0.0, 1.0]` |
| 9 | `rim_valuation` | `rim_score` | Fundamental Residual Income valuation score `[0.0, 1.0]` |
| 10 | `event_driven` | `event_score` | Corporate event/catalyst score `[0.0, 1.0]` |
| 11 | `mq_factor` | `mq_score` | Momentum Quality & fundamental quality score `[0.0, 1.0]` |
| 12 | `iv_skew` | `iv_skew_score` | Options put/call IV skew contrarian score `[0.0, 1.0]` |
| 13 | `order_flow` | `order_flow_score` | Net institutional money flow acceleration score `[0.0, 1.0]` |
| 14 | `short_term_reversal` | `reversal_score` | Oversold/Overbought mean-reversion score `[0.0, 1.0]` |

### Score Integration Workflow
- Strategy outputs are outer-merged on `symbol`.
- Optional `IsotonicRegression` calibrators (`fit_calibrators`, `calibrate_scores`) calibrate raw strategy scores to true empirical probabilities (`>20%` gain outcome).
- Weighted summation across valid scores:
  `ensemble_score = (sum(score_i * w_i)) / (sum(w_i_valid))` clipped to `[0.0, 1.0]`.

---

## 2. 2D Market Regime Engine & Dynamic Weighting

### GMM Market Regime Engine (`src/analysis/regime_detector.py`)
- **Macro Feature Matrix**: S&P500 20d rolling return, S&P500 20d rolling volatility, VIX index level (`vix_change / 100`), US 10Y yield (`us10y / 10`), USD/KRW rolling return (`usdkrw_change`), and yield curve spread (`yield_curve_10y3m / 5`).
- **GMM Components**: 3 direction states (0=BEAR, 1=SIDEWAYS, 2=BULL) sorted by Sharpe ratio score (`mean_ret / mean_vol`).
- **2D Regime States**: Direction (BEAR/SIDEWAYS/BULL) + Volatility (LOW_VOL/HIGH_VOL based on S&P500 rolling std vs median).
  6 Discrete States: `BEAR_LOW_VOL`, `BEAR_HIGH_VOL`, `SIDEWAYS_LOW_VOL`, `SIDEWAYS_HIGH_VOL`, `BULL_LOW_VOL`, `BULL_HIGH_VOL`.
- **Fast Shock Overrides**:
  - `vix_change > 30.0` forces immediate `BEAR` regime.
  - S&P 500 1d return < -3.0% or 2d return < -5.0% forces immediate `BEAR` regime.
- **3D Macro Modifiers**: Applies override deltas for `LIQUIDITY_SQUEEZE`, `HIGH_YIELD_BULL`, `HIGH_YIELD_BEAR`.

### Dynamic Performance Weighting & EMA Smoothing
- **Exponential Sharpe Weighting**: `w_i_dynamic = base_w_i * exp(gamma * clip(Sharpe_i, -3, 3))` (gamma=1.0).
- **EMA Weight Smoothing**: `smoothed_w = alpha * dynamic_w + (1 - alpha) * prev_w` (alpha=0.2). Prevents regime transition whipsaws across daily executions. Persisted to `models/prev_weights.json`.

---

## 3. Transaction Costs, Net Returns, & Liquidity Filtering

### Transaction Cost Deduction
- Net expected return proxy calculated as:
  `raw_exp_ret = ensemble_score * return_multiplier * 100.0`
  `ensemble_expected_return = (raw_exp_ret - cost_pct * 100.0).clip(0.0, 50.0)`
- `cost_pct` schedule:
  - KONEX (`.KN`): 0.80% tax/fee + 0.50% slippage = 1.30%
  - KOSDAQ (`.KQ`): 0.50% tax/fee + 0.50% slippage = 1.00%
  - KOSPI (`.KS` / 6 digits): 0.35% tax/fee + 0.50% slippage = 0.85%
  - SP500 / US: 0.10% tax/fee

### Liquidity & Safety Filters
- **Preferred Stocks**: Flags symbol names ending with `우`, `우B`, `1우`, `2우B`, `3우B` or 6-digit symbols ending in `K..O`.
- **SPACs**: Flags symbol names containing `스팩` or `SPAC`.
- Flagged stocks receive `ensemble_score = 0.0` and `ensemble_expected_return = 0.0`, excluding them from Top 20 recommendations.
- **Sentiment Blacklist**: Zero-weights symbols flagged with high disclosure risk.

---

## 4. Decision Rationale & Report Formatting

- Written to `trading_system/result/ensemble_predictions.txt`:
  1. Executive Summary & Timestamp (KST timezone).
  2. Judgment Basis (Global Macro Indicators: S&P500 return/vol, KOSPI return/vol, VIX, USD/KRW, US10Y, KR10Y, WTI, Gold).
  3. `get_regime_reasoning_summary()` text detailing market trend rationale, volatility state rationale, and 14 strategy weight distribution.
  4. Top 100 Ensemble Picks per market (`KOSPI`, `KOSDAQ`, `KONEX`, `SP500`) with raw scores for all 14 strategies and net expected return.

---

## 5. Identification of Bugs, Gaps, & Improvement Opportunities

### Critical Bug
1. **Zero-Score Exclusion Bug in `ensemble_scorer.py` (Line 690)**:
   - **Location**: `src/ai/ensemble_scorer.py:690`
   - **Code**: `valid_mask = merged[score_col].notna() & (merged[score_col] > 0.0)`
   - **Impact**: Any valid score of `0.0` (e.g. no reversal signal, 0.0 probability, neutral factor score) is treated as *missing data* and excluded from the total weight denominator `total_weight_series`.
   - **Consequence**: If a stock scores `0.0` on 13 strategies and `0.05` on 1 strategy, its weight denominator becomes only `w_1`, resulting in `ensemble_score = 0.05` instead of `0.05 * w_1 / 1.0`.
   - **Recommended Fix**: Change `valid_mask` to `merged[score_col].notna()`. If NaN values indicate missing evaluation, `notna()` preserves valid `0.0` scores.

### Gaps & Minor Issues
2. **Transaction Cost Suffix Dependency**:
   - `_get_cost_pct(symbol)` checks string suffixes `.KQ` and `.KN`. If KOSDAQ/KONEX tickers are passed without suffix (e.g., pure 6-digit numeric tickers or custom symbol strings), `.isdigit()` defaults to the KOSPI rate (`0.0035 + slippage`).
   - **Recommended Fix**: Pass universe metadata (`market` column) into cost calculation so that `market == 'KOSDAQ'` or `market == 'KONEX'` dictates the cost rate regardless of ticker string format.
3. **Environment Command Execution Constraint**:
   - Sub-process invocation via `run_command` in this sandbox environment throws `sandbox configuration error: readwrite stock: non-absolute file path`. Code and unit tests were audited via direct file view.
