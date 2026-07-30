# Quantitative & Financial Engineering Audit Report: 17 Alpha Strategies, Return Metrics, & Transaction Cost Modeling

**Author**: Explorer M1-1 (Quant & Financial Engineering Specialist)  
**Working Directory**: `d:\Finance\code\stock\.agents\explorer_m1_1`  
**Date**: 2026-07-30  
**Target Codebase**: `trading_system/src/`

---

## Executive Summary

An exhaustive line-by-line quantitative and financial engineering audit was conducted across all 17 alpha strategies, return metrics, risk-adjusted scoring, and transaction cost modeling in the Stock Trading System codebase.

Key findings include:
1. **High Severity**: **Lead-Lag Score Scale Mismatch** (`src/ai/ensemble_scorer.py:690` vs `src/ai/prediction_model.py:2549`). Standard Lead-Lag output ($\approx 0.01$) is divided by 100 in the ensemble scorer, reducing the signal to $\approx 0.0001$ (99.9% signal suppression).
2. **High Severity**: **Rolling Sharpe Annualization Mismatch** (`src/ai/ensemble_scorer.py:378`). Multi-day 20-day horizon returns are annualized with $\sqrt{252}$ instead of $\sqrt{252/20} = \sqrt{12.6}$, artificially inflating rolling Sharpe ratios by $\sqrt{20} \approx 4.47\times$ and distorting dynamic exponential Sharpe weights.
3. **Medium Severity**: **Fixed Order Size ADV Overflow Penalty** (`src/ai/ensemble_scorer.py:1062-1067`). Fixed 50M KRW ($Q$) assumption per order causes small-cap participation ratios ($Q/ADV$) to exceed 10%, triggering a severe artificial penalty ($0.50 \times (Q/ADV - 0.10)$) up to +20% market impact cost.
4. **Medium Severity**: **US Index Timezone Alignment in Lead-Lag** (`src/ai/prediction_model.py:2457-2463`). `sp500_change` (`^GSPC`) is not shifted by 1 day relative to Korean trading dates, unlike US ETFs.
5. **Medium Severity**: **MinMax Outlier Distortion in ARM & LATR Factors** (`src/core/arm_factor.py:50-54`, `src/core/latr_factor.py:61-65`). MinMax normalization across symbols squashes non-outlier stock scores into narrow bands due to single extreme outliers.

---

## 1. Observation

### Observation 1.1: Lead-Lag Score Division Mismatch
- **File**: `trading_system/src/ai/prediction_model.py` (Lines 2549–2550 & 2565)
  ```python
  2549: weight = leader_ret * corr
  2550: follower_scores[follower] = follower_scores.get(follower, 0.0) + max(0.0, weight)
  ...
  2565: follower_scores[sym] = max(0.001, round(ret * 100, 4)) # Fallback score
  ```
- **File**: `trading_system/src/ai/ensemble_scorer.py` (Line 690)
  ```python
  690: ll_df_copy['ll_score'] = (ll_df_copy['ll_raw'] / 100.0).clip(0.0, 1.0)
  ```
- **Direct Evidence**: Normal `predict_lead_lag` generates `ll_raw` $\approx 0.01 \text{ to } 0.05$. Dividing by 100 in `ensemble_scorer.py` produces `ll_score` $\approx 0.0001 \text{ to } 0.0005$, whereas the fallback mechanism generates `ret * 100` ($\approx 15.0$), which divides to $0.15$.

### Observation 1.2: Rolling Sharpe Horizon Scaling Error
- **File**: `trading_system/src/ai/ensemble_scorer.py` (Line 378)
  ```python
  378: sharpe = ((mean_ret - rf_daily) / std_ret) * np.sqrt(252)
  ```
- **Direct Evidence**: The input `strategy_returns` series consists of 20-day horizon returns ($R_{20d}$), not 1-day returns. Applying $\sqrt{252}$ annualization assumes daily frequency. For 20-day returns, the correct annualization multiplier is $\sqrt{252 / 20} = \sqrt{12.6} \approx 3.55$. Multiplying by $\sqrt{252} \approx 15.87$ inflates the Sharpe ratio by $\sqrt{20} \approx 4.472$.

### Observation 1.3: Fixed Order Size & ADV Impact Overflow
- **File**: `trading_system/src/config.py` (Lines 70–71)
  ```python
  70: order_size_krx: float = 50_000_000.0        # KRX 기본 주문 금액 가설 (5천만원)
  71: order_size_sp500: float = 50_000.0          # SP500 기본 주문 금액 가설 ($50,000)
  ```
- **File**: `trading_system/src/ai/ensemble_scorer.py` (Lines 1062–1068)
  ```python
  1062: participation_ratio = q_order / adv
  1063: impact_one_way = impact_coeff * volatility * np.sqrt(participation_ratio)
  1064: 
  1065: # 3. Participation Rate Overflow Penalty (> 10% ADV)
  1066: if participation_ratio > 0.10:
  1067:     impact_one_way += 0.50 * (participation_ratio - 0.10)
  ```
- **Direct Evidence**: `q_order` is static ($50,000,000$ KRW). For illiquid stocks with daily turnover $\text{ADV} = 100,000,000$ KRW, $\text{participation\_ratio} = 0.50$. The overflow penalty adds $0.50 \times (0.50 - 0.10) = 0.20$ ($20\%$ one-way cost, $40\%$ round-trip deduction), causing the stock's net expected return to be clipped to $0.0\%$.

### Observation 1.4: US Market Index Timezone Shift Omission in Lead-Lag
- **File**: `trading_system/src/ai/prediction_model.py` (Lines 2436–2463)
  ```python
  2436: index_sector_mapping = {
  2437:     'sp500_change': '^GSPC',
  2438:     'kospi_change': '^KS11',
  ...
  2442:     'xlk_change': 'XLK',
  2443:     'xlf_change': 'XLF',
  ...
  2457: us_etfs = {'XLK', 'XLF', 'XLV', 'XLE'}
  2458: for src_col, target_sym in index_sector_mapping.items():
  2459:     if src_col in ind_df.columns:
  2460:         ret_series = ind_df[src_col] / 100.0
  2461:         if target_sym in us_etfs:
  2462:             ret_series = ret_series.shift(1)
  2463:         ret_pivot[target_sym] = ret_series
  ```
- **Direct Evidence**: `^GSPC` (`sp500_change`) is NOT in `us_etfs`. Therefore, `sp500_change` is NOT shifted by 1 day when evaluating lead-lag relationships for Korean equities, creating an unshifted timezone alignment bug between US close and KR open.

### Observation 1.5: Outlier Vulnerability in MinMax Normalization (ARM & LATR)
- **File**: `trading_system/src/core/arm_factor.py` (Lines 41 & 50–54)
  ```python
  41: arm_raw = (eps_growth * 0.4) + (rev_growth * 0.3) + (price_mom * 0.2) - (per * 0.01)
  ...
  50: vals = np.array(list(scores.values()))
  51: min_v, max_v = np.min(vals), np.max(vals)
  52: range_v = max_v - min_v if max_v != min_v else 1.0
  53: return {k: float(np.clip((v - min_v) / range_v, 0.0, 1.0)) for k, v in scores.items()}
  ```
- **File**: `trading_system/src/core/latr_factor.py` (Lines 53 & 61–65)
  ```python
  53: latr_score = ((1.0 - dd_pct) * 0.4) + (min(vol_surge, 3.0) * 0.4) - (abs(tail_risk) * 0.2)
  ...
  61: vals = np.array(list(scores.values()))
  62: min_v, max_v = np.min(vals), np.max(vals)
  63: range_v = max_v - min_v if max_v != min_v else 1.0
  64: return {k: float(np.clip((v - min_v) / range_v, 0.0, 1.0)) for k, v in scores.items()}
  ```
- **Direct Evidence**: Unbounded PER or EPS growth values (e.g. $\text{PER} = 2500$ or $\text{EPS}_{\text{growth}} = 1000\%$) cause `max_v` or `min_v` to explode, compressing all normal stocks into a tight band around $0.50$.

---

## 2. Logic Chain

1. **Lead-Lag Signal Suppression**:
   - `predict_lead_lag` calculates `leader_ret * corr` where `leader_ret` is daily return (e.g. $0.02$) and `corr` is correlation (e.g. $0.5$). The result is $0.01$.
   - In `ensemble_scorer.py:690`, `ll_score` is computed as `ll_raw / 100.0`.
   - $0.01 / 100 = 0.0001$.
   - Therefore, the Lead-Lag strategy score is zeroed out for all valid lead-lag predictions, neutralizing Strategy 3 in the ensemble.

2. **Sharpe Weight Distortion**:
   - `compute_rolling_sharpe` receives a 60-row window of 20-day horizon returns ($R_{20d}$).
   - `mean_ret` is $\mathbb{E}[R_{20d}]$ and `std_ret` is $\sigma(R_{20d})$.
   - Multiplying $\frac{\mathbb{E}[R_{20d}]}{\sigma(R_{20d})}$ by $\sqrt{252}$ assumes 252 independent daily observations.
   - Over a 20-day horizon, there are only $252 / 20 = 12.6$ non-overlapping periods per year.
   - The factor $\sqrt{252} / \sqrt{12.6} = \sqrt{20} \approx 4.472$ scales up the Sharpe ratio exponentially.
   - In `compute_dynamic_weights_from_sharpe`, multiplier is $\exp(\gamma \cdot \text{Sharpe})$. An artificially inflated Sharpe ratio of $3.0$ (clipped) vs $0.67$ (actual) causes exponential weight distortion.

3. **Fixed Order Size Market Impact Distortion**:
   - Microstructure cost model calculates $Q / \text{ADV}$.
   - $Q$ is fixed at 50M KRW regardless of position sizing or portfolio total capital.
   - For an illiquid stock with $\text{ADV} = 50\text{M KRW}$, $Q / \text{ADV} = 1.0$.
   - Line 1067 applies penalty: $0.50 \times (1.0 - 0.10) = 0.45$ ($45\%$ one-way impact cost).
   - This subtracts $45\%$ from expected return, driving `ensemble_expected_return` to $0.0\%$ for all small-cap stocks regardless of alpha quality.

4. **Timezone Alignment Discrepancy**:
   - US stock market closes at 05:00 AM KST.
   - Korean stock market opens at 09:00 AM KST on the same calendar date.
   - Thus, SP500 return from date $T_{\text{US}}$ is available before KOSPI open on date $T_{\text{KR}} = T_{\text{US}} + 1$.
   - Shifting US ETFs (`XLK`, `XLF`) by 1 day aligns date $T_{\text{US}}$ with $T_{\text{KR}}$.
   - Omitting `^GSPC` (`sp500_change`) from the `us_etfs` shift list causes `sp500_change` to align with $T_{\text{KR}} - 1$, introducing a 1-day lag error.

---

## 3. Audit Matrix of All 17 Alpha Strategies

| # | Strategy Name | Module Path | Mathematical Validity | Data Leak / Lookahead | Score Scale | Severity | Key Audit Finding |
|---|---------------|-------------|-----------------------|-----------------------|-------------|----------|-------------------|
| 1 | XGBoost Regression | `src/ai/prediction_model.py` | Valid | None (60d Filing Lag applied) | $[0, 1]$ (via `reg_pred / 0.25`) | Low | Fixed 0.25 divisor assumes 20d horizon; short horizons map to lower score scale. |
| 2 | Surge Classifier | `src/ai/prediction_model.py` | Valid | None | $[0, 1]$ | Passed | `scale_pos_weight` capped at 20.0 to prevent gradient explosion. |
| 3 | Lead-Lag 2-Tier | `src/ai/prediction_model.py` | Valid | Timezone mismatch (`^GSPC` unshifted) | $[0, 1]$ (Mismatched) | **HIGH** | `ll_raw` ($\approx 0.01$) divided by 100 in scorer $\rightarrow$ $0.0001$ score (99.9% signal loss). |
| 4 | VCP Rule | `src/ai/vcp_detector.py` | Valid | None | $[0, 1]$ | Passed | Minervini non-overlapping range contraction & volume decay validated. |
| 5 | VCP ML | `src/ai/vcp_ml_predictor.py` | Valid | None | $[0, 1]$ | Passed | 11 vectorized VCP features ensemble-trained per market with Platt scaling. |
| 6 | Strict Causal LSTM | `src/ai/lstm_predictor.py` | Valid | None | $[0, 1]$ | Low | 1D single-feature input (`ret_1d`); causal sequence windowing validated. |
| 7 | Stat-Arb Cointegration | `src/core/stat_arb.py` | Valid | None (fitted on $t-1$ history) | $[0, 1]$ | Passed | Log price Engle-Granger ADF test & OU half-life Z-score mapping validated. |
| 8 | Sector Rotation | `src/core/sector_rotation.py` | Valid | None | $[0, 1]$ | Passed | GICS 11 normalization + intra-sector dispersion weighting validated. |
| 9 | RIM Valuation | `src/core/rim_valuation.py` | Valid | None | $[0, 1]$ | Passed | Dynamic $r_e = \text{US10Y} + \text{ERP}$, 8-year decaying ROE with retained earnings accumulation validated. |
| 10 | Event-Driven | `src/core/event_driven.py` | Valid | None | $[0, 1]$ | Passed | OpenDART filing type weights + dilution/buyback keyword directionality validated. |
| 11 | Momentum Quality (MQ) | `src/core/mq_factor.py` | Valid | None | $[0, 1]$ | Passed | 12M-1M momentum (skipping 1M reversal noise) + ROE/OpMargin quality overlay. |
| 12 | Options IV Skew | `src/core/iv_skew.py` | Valid | None | $[0, 1]$ | Passed | Put/Call IV ratio ATM ($\pm 8\%$) + realized downside/upside vol skew fallback. |
| 13 | Order Flow Imbalance | `src/core/order_flow.py` | Valid | None | $[0, 1]$ | Passed | MFI ratio + OBV trend slope + 5d/20d volume acceleration validated. |
| 14 | Short-Term Reversal | `src/core/short_term_reversal.py` | Valid | None | $[0, 1]$ | Passed | 5d drop + Bollinger lower band breach with loss-making quality filter. |
| 15 | Analyst Revision (ARM) | `src/core/arm_factor.py` | Minor Issue | None | $[0, 1]$ (MinMax) | **MEDIUM** | Raw PER subtraction in score + MinMax normalization vulnerable to outliers. |
| 16 | CARD Factor | `src/core/card_factor.py` | Valid | None | $[0, 1]$ | Passed | Cross-asset (USDKRW, WTI, VIX) vs stock divergence sigmoid score. |
| 17 | LATR Factor | `src/core/latr_factor.py` | Minor Issue | None | $[0, 1]$ (MinMax) | **MEDIUM** | 52w drawdown + volume surge - 5% VaR tail risk; MinMax scaling vulnerable to outliers. |

---

## 4. Caveats

- **No Caveats**: All 17 strategy modules, risk metrics, ensemble scorer, and configuration parameters were inspected line-by-line.

---

## 5. Conclusion

The quantitative architecture of the Stock Trading System is sound and advanced, featuring 60-day fundamental filing lag protection, log-price cointegration, GICS 11 sector mapping, and dynamic 2D/3D macro regime weighting.

However, three primary quantitative defects must be remediated to unlock optimal trading performance:
1. Fix the `/ 100.0` divisor in `ensemble_scorer.py:690` for Lead-Lag scores so that fractional Lead-Lag output is correctly scaled to $[0, 1]$.
2. Correct the rolling Sharpe annualization multiplier in `ensemble_scorer.py:378` from $\sqrt{252}$ to $\sqrt{252 / \text{horizon\_days}}$.
3. Dynamicize the order size hypothesis $Q$ in `ensemble_scorer.py:1062` to scale with target portfolio allocation rather than a fixed 50M KRW constant.

---

## 6. Verification Method

### 6.1 Automated Test Execution
Run the full test suite using the project virtual environment:
```bash
.venv/bin/pytest tests/ -v
```

### 6.2 Inspection Commands for Verification
1. **Lead-Lag Scale Check**:
   Inspect `trading_system/src/ai/ensemble_scorer.py` line 690:
   `view_file` at `d:\Finance\code\stock\trading_system\src\ai\ensemble_scorer.py` lines 685–695.
2. **Sharpe Annualization Check**:
   Inspect `trading_system/src/ai/ensemble_scorer.py` line 378:
   `view_file` at `d:\Finance\code\stock\trading_system\src\ai\ensemble_scorer.py` lines 370–385.
3. **Market Impact Overflow Check**:
   Inspect `trading_system/src/ai/ensemble_scorer.py` lines 1060–1070:
   `view_file` at `d:\Finance\code\stock\trading_system\src\ai\ensemble_scorer.py` lines 1060–1070.

### 6.3 Invalidation Conditions
- If Lead-Lag score outputs from `predict_lead_lag` are refactored to $[0, 100]$, the `/ 100.0` division in `ensemble_scorer.py` is valid.
- If daily returns (1-day frequency) are passed to `compute_rolling_sharpe`, $\sqrt{252}$ annualization is valid.
