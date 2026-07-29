# Quantitative Financial Engineering Audit Handoff Report

**Agent**: Explorer M1 (Quant Strategy Specialist)  
**Workspace**: `d:\Finance\code\stock\.agents\explorer_m1`  
**Target System**: Stock Trading System (17 Strategies Audit)  
**Date**: 2026-07-30  

---

## 1. Observation

Direct observations from line-by-line quantitative and mathematical audit across all 17 strategy source files in `trading_system/src/core/`, `trading_system/src/ai/prediction_model.py`, `trading_system/src/ai/lstm_predictor.py`, `trading_system/src/ai/vcp_detector.py`, and `trading_system/src/ai/vcp_ml_predictor.py`:

### Strategy 1: Stat-Arb Cointegration (`trading_system/src/core/stat_arb.py`)
- **Lines 46–57**: Discretized ADF t-statistic p-value approximation using crude step-functions (`t_stat < -3.90: 0.01`, `elif t_stat < -3.34: 0.03`, `elif t_stat < -2.86: 0.05`, `elif t_stat < -2.57: 0.09`, `else: 0.50`).
- **Lines 162–178**: Cointegration OLS regression fitted on raw price levels ($s1\_prices, s2\_prices$) rather than log prices $\ln(P)$, violating stationarity under price level variance scale changes.
- **Lines 227–236**: Benjamini-Hochberg FDR correction implementation lacks backwards monotonicity (`q_val = pvals[idx] * n_tests / rank`), multiplies threshold by 2 arbitrarily (`max_pvalue * 2`), and fallback accepts top 50 unpassed pairs when 0 pass FDR.
- **Lines 262–272**: Symbol score adaptation uses dict lookup overwrites (`max`/`min`) without correlation/hedge-ratio volume weighting.
- **Vulnerability Rating**: **HIGH**

### Strategy 2: RIM Valuation (`trading_system/src/core/rim_valuation.py`)
- **Line 88**: Terminal value formulation `pv_terminal = (current_bps - bps) / ((1.0 + r_e) ** years)`. Adds cumulative retained earnings ($BPS_N - BPS_0$) as terminal value, double-counting retained net income already discounted in annual residual income terms $PV(EI_t)$.
- **Lines 81–85**: Retention ratio ($0.6$) applied to negative net income ($NI < 0$), treating remaining 40% loss as dividend payout for loss-making companies.
- **Line 181**: `df.groupby('market')['discount_ratio'].rank(pct=True).fillna(0.5)` overrides missing fundamental BPS/ROE with neutral score `0.5`, violating docstring intent (*"Missing fundamental BPS yields NaN rim_score for dynamic ensemble weight renormalization"*).
- **Vulnerability Rating**: **HIGH**

### Strategy 3: Options IV Skew (`trading_system/src/core/iv_skew.py`)
- **Lines 112–113**: Realized volatility fallback calculates `down_vol` and `up_vol` via `down_ret.iloc[-20:].std()` and `up_ret.iloc[-20:].std()`, comparing standard deviations over unaligned, disjoint time-series windows of negative and positive return days.
- **Line 43**: Selects `expirations[0]` (immediate next option expiry, e.g. 0–3 days to expiry), introducing gamma/liquidity micro-structure noise without 30-day constant maturity interpolation.
- **Lines 51–52**: ATM option filter takes median of all strikes within $\pm 8\%$ of price, averaging calls and puts near the money and masking out-of-the-money delta skew.
- **Vulnerability Rating**: **MEDIUM**

### Strategy 4: Order Flow Imbalance (`trading_system/src/core/order_flow.py`)
- **Line 65**: `obv_trend = float((obv.iloc[-1] - obv.iloc[0]) / (abs(obv.iloc[0]) + 1e-6))` divides cumulative OBV delta by single day-0 initial volume $|OBV_0|$, causing extreme score explosions (e.g. $+50,000\%$) when day-0 volume is low.
- **Lines 57–58**: Directional money flow sums dollar-volume returns over variable price history window lengths `len(df)` without cross-sectional time window standardization.
- **Lines 90 & 100**: Institutional boost $+0.10$ added directly as raw constant before percentile ranking.
- **Vulnerability Rating**: **MEDIUM**

### Strategy 5: LATR Factor (`trading_system/src/core/latr_factor.py`)
- **Lines 40 & 52**: 52-week Drawdown $DD_{pct} = (P_{max} - P_{curr}) / P_{max}$ enters raw score linearly as $+0.4 \times DD_{pct}$. Contradicts strategy docstring (*"Moderate drawdown 20-40%"*) by strictly rewarding extreme 95% drops.
- **Lines 49 & 52**: 5th percentile tail risk `abs(tail_risk) * 0.2` added as positive reward, penalizing stable stocks and rewarding stocks with catastrophic negative tail drops.
- **Lines 60–64**: Global min-max scaling `(v - min_v) / (max_v - min_v)` compresses cross-sectional score distribution when single outlier spikes volume surge.
- **Vulnerability Rating**: **HIGH**

### Strategy 6: CARD Factor (`trading_system/src/core/card_factor.py`)
- **Lines 26–28 & 49**: Unit mismatch combining 5-day stock percentage return (e.g. $+5.0$) with unscaled raw KRW USD/KRW change, dollar WTI change, and VIX point change.
- **Lines 31 & 45**: Variable `sec = sector_map.get(sym, 'Market')` extracted but NEVER used in divergence calculation, treating all sectors identically regardless of macro directionality.
- **Lines 26–28 & 44**: Time horizon mismatch between 5-day stock return (`close.iloc[-1] - close.iloc[-5]`) and 1-day macro change (`indicator_df.iloc[-1]`).
- **Vulnerability Rating**: **HIGH**

### Strategy 7: ARM Factor (`trading_system/src/core/arm_factor.py`)
- **Lines 27–28**: Missing analyst consensus revision data; uses static trailing growth rates (`eps_growth`, `revenue_growth`) as proxy, failing to measure revision velocity.
- **Line 41**: Unscaled combination `(eps_growth * 0.4) + (rev_growth * 0.3) + (price_mom * 0.2) - (per * 0.01)`. `price_mom` is scaled by 100 ($15.0$ for 15%), dominating fractional `eps_growth` ($0.25$) by 30x.
- **Line 30**: Variable `pbr` extracted but never used in `arm_raw`.
- **Lines 50–54**: Global min-max normalization vulnerable to single extreme outlier.
- **Vulnerability Rating**: **HIGH**

### Strategy 8: Sector Rotation (`trading_system/src/core/sector_rotation.py`)
- **Lines 65 & 126**: All unmapped raw sector names collapse into `"General"`, aggregating hundreds of heterogeneous tickers into a single diluted mean sector momentum.
- **Lines 71–74**: Substring match in `normalize_sector` depends on dictionary key insertion order, risking misclassification.
- **Line 169**: Additive macro boost $+0.05$ added post-percentile ranking, corrupting uniform distribution $[0, 1]$.
- **Vulnerability Rating**: **MEDIUM**

### Strategy 9: Event-Driven (`trading_system/src/core/event_driven.py`)
- **Lines 98–100**: OpenDART 8-digit `corp_code` matched via `corp_code.endswith(sym_clean)`, causing false disclosure leakage across unrelated companies.
- **Lines 104–119**: Text keyword check order short-circuits composite disclosure titles.
- **Line 142**: Volume/price surge boost `0.05 * (v_ratio - 1.0) + 0.10 * ret_5d` adds positive boost on high-volume sell-off crashes, converting bearish filings into bullish scores.
- **Vulnerability Rating**: **HIGH**

### Strategy 10: MQ Factor (`trading_system/src/core/mq_factor.py`)
- **Line 46**: Short price series lookback fallback (`p_t252 = close.iloc[0]`) calculates 1-month short-term return for stocks with $< 252$ days, capturing the exact short-term reversal noise it was designed to skip.
- **Lines 80, 83, 86**: Missing quality metrics filled with `0.5`, pulling overall score towards neutral regardless of fundamental quality.
- **Vulnerability Rating**: **MEDIUM**

### Strategy 11: Short-Term Reversal (`trading_system/src/core/short_term_reversal.py`)
- **Line 54**: Bollinger lower band distance `(cur_price - lower_band) / (std_20 + 1e-8)` divides price deviation by 20-day standard deviation, causing extreme score spikes when $\sigma_{20} \approx 0$.
- **Line 82**: Hard step-threshold penalty (`operating_margin < -0.10`) subtracts $1.0$ from `oversold_metric`, introducing rank cliffs.
- **Line 46**: 5-day return index slicing `len(close) >= 6` returns 0.0 for 5-day series.
- **Vulnerability Rating**: **MEDIUM**

### Strategy 12: XGBoost Regression (`trading_system/src/ai/prediction_model.py`)
- **Line 1487**: Target transformation `transform_sharpe(df_h[target_col])` scales target returns by rolling volatility, creating scale heterogeneity across horizons.
- **Lines 1539–1551**: Ensemble weighting `1.0 / max(avg_mse, 1e-6)` without target variance normalization yields unbalanced model weights.
- **Vulnerability Rating**: **MEDIUM**

### Strategy 13: Surge Classifier (`trading_system/src/ai/prediction_model.py`)
- **Line 1620**: `scale_pos_weight` capped at $20.0$ under 1-day/3-day surge imbalance ($< 0.5\%$ positive class) distorts predicted probabilities.
- **Lines 1630–1640**: Isotonic calibration fitted in-sample on training set causes probability over-confidence.
- **Vulnerability Rating**: **MEDIUM**

### Strategy 14: Lead-Lag 2-Tier Matrix (`trading_system/src/ai/prediction_model.py`)
- **Lines 2447–2451**: Timezone lookahead bias: US index returns (`^GSPC`, `XLK`) on date $T$ (closing at 06:00 KST next day) aligned with KOSPI stock returns on date $T$ (closing at 15:30 KST).
- **Line 2462**: Zero standard deviation division for suspended tickers produces `ret_z` of magnitude $10^{10}$.
- **Line 2470**: Cross-correlation `(lead_arr.T @ follow_arr) / (n_time - 1)` on truncated slices fails exact correlation bounds $[-1, 1]$.
- **Line 2551**: Fallback prediction branch sets `follower_scores` to raw lifetime percentage returns (e.g. $+250.0\%$), corrupting ensemble ranking.
- **Vulnerability Rating**: **HIGH**

### Strategy 15: Strict Causal LSTM (`trading_system/src/ai/lstm_predictor.py` & `prediction_model.py`)
- **Lines 25 & 67–68 (`lstm_predictor.py`)**: Single-feature input (`input_size = 1`) uses only 1D scalar return sequences, discarding all fundamental, alternative, volume, and macro features.
- **Lines 73–75 (`lstm_predictor.py`)**: Raw returns passed into PyTorch `nn.LSTM` without rolling sequence z-score normalization.
- **Lines 83–102 (`lstm_predictor.py`)**: Fixed 5 training epochs without early stopping, learning rate decay, or dropout regularization.
- **Vulnerability Rating**: **HIGH**

### Strategy 16: Rule-based VCP Pattern (`trading_system/src/ai/vcp_detector.py`)
- **Lines 116–119**: Asymmetric window slicing compares 5-day max range ($R_1$) against 20-day ($R_3$) and 25-day ($R_4$) max ranges. Extreme value order statistics guarantee $R_4 > R_1$ regardless of volatility contraction.
- **Lines 124–125**: `decreasing` boolean omits checking $R_3 > R_2$, flagging volatility expansion patterns ($R_4 = 5\%, R_3 = 20\%, R_2 = 15\%, R_1 = 4\%$) as valid VCP.
- **Vulnerability Rating**: **HIGH**

### Strategy 17: VCP ML Classifier (`trading_system/src/ai/vcp_ml_predictor.py`)
- **Lines 370–376**: Time-series validation quantile split (`m_df['date'] <= cutoff`) fails to prevent feature overlap leakage from 60-day historical VCP lookbacks across sliding windows.
- **Line 394**: `scale_pos_weight` up to $500.0$ distorts classification decision boundaries and uncalibrates output probabilities.
- **Line 343**: Merging whole-dataframe base features (`all_base`) leaks future window data into historical training windows.
- **Vulnerability Rating**: **HIGH**

---

## 2. Logic Chain

1. **Observation**: Stat-Arb Cointegration (`stat_arb.py:162-178`) performs OLS regression on raw stock prices.
   - **Reasoning**: Raw stock price series are non-stationary with variance proportional to price level. Evaluating spread $\epsilon_t = P_{1,t} - \beta P_{2,t}$ on raw prices causes standard error explosion as stock prices appreciate.
   - **Conclusion**: Cointegration scanning must use log prices $\ln(P_1) - \beta \ln(P_2)$.

2. **Observation**: RIM Valuation (`rim_valuation.py:88`) calculates $PV_{terminal} = (BPS_N - BPS_0) / (1+r_e)^N$.
   - **Reasoning**: Residual Income Model discounts residual earnings $PV(EI_t) = BPS_{t-1}(ROE_t - r_e) / (1+r_e)^t$. Retained net income accumulates into $BPS_t$. Adding total accumulated retained earnings $(BPS_N - BPS_0)$ at terminal horizon counts retained earnings twice.
   - **Conclusion**: Intrinsic values $V_0$ are systematically inflated for dividend-retaining growth companies.

3. **Observation**: LATR Factor (`latr_factor.py:52`) adds $+0.4 \times DD_{pct} + 0.2 \times |TailRisk|$ to raw score.
   - **Reasoning**: Larger 52-week drawdown (e.g. 95% drop) and larger 5th-percentile negative daily crash magnitude increase score linearly. This rewards bankrupt/crashing stocks rather than filtering moderate dips (20–40%).
   - **Conclusion**: LATR score selects high-tail-risk distress stocks.

4. **Observation**: CARD Factor (`card_factor.py:49-50`) subtracts raw sum of USD/KRW change, WTI change, and VIX change from stock return percentage.
   - **Reasoning**: Adding raw KRW currency change (+15 KRW) to dollar WTI change (+2.5 USD) and VIX point change (+4.0 points) without z-scoring creates dimensional unit corruption. Furthermore, `sector_map` is ignored.
   - **Conclusion**: Macro divergence scores produce arbitrary noise across non-export sectors.

5. **Observation**: Lead-Lag Matrix (`prediction_model.py:2447-2451`) aligns US index returns on date $T$ with KOSPI stock returns on date $T$.
   - **Reasoning**: KOSPI market closes at 15:30 KST (02:30 AM EST date $T$). US equity market trades from 23:30 KST to 06:00 KST (date $T+1$ KST).
   - **Conclusion**: Assigning US index return of date $T$ to date $T$ KOSPI prices introduces a severe 15-hour lookahead bias.

6. **Observation**: Rule-based VCP (`vcp_detector.py:116-119`) compares max range over 5 days ($R_1$) vs max range over 25 days ($R_4$).
   - **Reasoning**: By sample size order statistics, $\max(X_{1..25}) \ge \max(X_{1..5})$ holds for almost any random stationary time series.
   - **Conclusion**: The rule flags normal random price series as "volatility contraction".

---

## 3. Caveats

1. **Live Data Stream Variations**: Audit evaluated logic on codebase static code paths; dynamic runtime inputs (e.g., live yfinance API response structure changes for options chains) were not executed against live broker APIs during this read-only audit.
2. **Optuna Hyperparameter Overrides**: Parameter dictionaries (`tuned_params.json`) can dynamically override default parameters at runtime; line-by-line audit focused on the algorithmic equations and fallback parameters.

---

## 4. Conclusion

The Stock Trading System features an advanced 17-strategy multi-factor architecture. However, quantitative financial engineering audit reveals critical vulnerabilities across theory, mathematical logic, and code implementations:

- **10 HIGH Vulnerability Strategies**: Stat-Arb Cointegration, RIM Valuation, LATR Factor, CARD Factor, ARM Factor, Event-Driven, Lead-Lag 2-Tier Matrix, Strict Causal LSTM, Rule-based VCP Pattern, VCP ML Classifier.
- **7 MEDIUM Vulnerability Strategies**: Options IV Skew, Order Flow Imbalance, Sector Rotation, MQ Factor, Short-Term Reversal, XGBoost Regression, Surge Classifier.

Fixing these quantitative defects (log-price cointegration, terminal RIM double-counting correction, tail risk sign inversion, timezone lag-1 alignment, and symmetric VCP windowing) will significantly enhance signal accuracy and operational alpha.

---

## 5. Verification Method

To independently verify the audited findings and execute unit tests for all 17 strategies:

1. **Run Full Test Suite**:
   ```bash
   .venv/bin/pytest tests/ -v
   ```
2. **Inspect Strategy Source Code Files**:
   - `trading_system/src/core/stat_arb.py` (Lines 46–57, 162–178, 227–236)
   - `trading_system/src/core/rim_valuation.py` (Line 88, 181)
   - `trading_system/src/core/iv_skew.py` (Lines 43, 51–52, 112–113)
   - `trading_system/src/core/order_flow.py` (Lines 57–58, 65)
   - `trading_system/src/core/latr_factor.py` (Lines 40, 49, 52, 60–64)
   - `trading_system/src/core/card_factor.py` (Lines 26–28, 31, 45, 49)
   - `trading_system/src/core/arm_factor.py` (Lines 27–28, 41)
   - `trading_system/src/core/sector_rotation.py` (Lines 65, 126, 169)
   - `trading_system/src/core/event_driven.py` (Lines 98–100, 142)
   - `trading_system/src/core/mq_factor.py` (Lines 46, 80)
   - `trading_system/src/core/short_term_reversal.py` (Lines 46, 54, 82)
   - `trading_system/src/ai/prediction_model.py` (Lines 1487, 1620, 2447–2451, 2462, 2470)
   - `trading_system/src/ai/lstm_predictor.py` (Lines 25, 67–68, 83–102)
   - `trading_system/src/ai/vcp_detector.py` (Lines 116–119, 124–125)
   - `trading_system/src/ai/vcp_ml_predictor.py` (Lines 343, 370–376, 394)

3. **Invalidation Condition**: If log-prices are adopted in `stat_arb.py`, terminal value double-counting is removed in `rim_valuation.py`, tail risk sign is inverted in `latr_factor.py`, timezone shift $T-1$ is applied to US indices in `prediction_model.py`, and symmetric equal-length windows are used in `vcp_detector.py`, the identified mathematical vulnerabilities will be invalidated/resolved.
