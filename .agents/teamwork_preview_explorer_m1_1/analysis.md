# Quantitative Strategy & Ensemble Scoring Audit Report

## Executive Summary

This report documents a thorough quantitative financial engineering audit of all 18 trading strategies, the 2D regime-based dynamic ensemble weighting engine, hybrid Isotonic/Platt probability calibrators, Gram-Schmidt and PCA ZCA symmetric factor decorrelation, and decision rationale generation within the automated stock trading system (`d:/Finance/code/stock`).

---

## 1. Audit of 18 Quantitative Strategies & Ensemble Integration

All 18 quantitative strategies are correctly implemented, returning normalized scores bounded in $[0.0, 1.0]$, and fully integrated into the `EnsembleScoringEngine`.

### Strategy Inventory & Normalization Audit

| # | Strategy Name | Code File | Score Column | Normalization / Scaling Formula | Score Range | Integration Status |
|---|---------------|-----------|--------------|---------------------------------|-------------|--------------------|
| 1 | XGBoost Regression | `src/ai/prediction_model.py` | `reg_score` | `(reg_pred / max_ret_norm).clip(0.0, 1.0)` where `max_ret_norm` = 0.25 (for 20d) | $[0.0, 1.0]$ | Integrated |
| 2 | Surge Classifier | `src/ai/prediction_model.py` | `surge_score` | Calibrated probability of >20% gain in horizon | $[0.0, 1.0]$ | Integrated |
| 3 | Lead-Lag | `src/core/cross_border_lead_lag.py` | `ll_score` | `(ll_raw / scale_denom).clip(0.0, 1.0)` (scale_denom = 100.0 if max > 1.0) | $[0.0, 1.0]$ | Integrated |
| 4 | VCP Pattern (Rule) | `src/ai/vcp_detector.py` | `vcp_rule_score` | `vcp_score / 100.0` or `is_vcp.astype(float)` | $[0.0, 1.0]$ | Integrated |
| 5 | VCP ML Predictor | `src/ai/vcp_ml_predictor.py` | `vcp_ml_score` | Platt-scaled ensemble probability (XGB+LGB+Cat) | $[0.0, 1.0]$ | Integrated |
| 6 | Strict Causal LSTM | `src/ai/lstm_predictor.py` | `lstm_score` | Neural network prediction output mapped to score | $[0.0, 1.0]$ | Integrated |
| 7 | Stat-Arb Cointegration | `src/core/stat_arb.py` | `stat_arb_score` | Maps pair z-scores: $0.5 \pm \min(0.4, |Z| \times 0.1)$ for long/short legs | $[0.1, 0.9]$ | Integrated |
| 8 | Sector Rotation | `src/core/sector_rotation.py` | `sector_score` | Composite momentum ($0.6 \times R_{20d} + 0.4 \times R_{60d}$) rank + macro/regime boost | $[0.0, 1.0]$ | Integrated |
| 9 | RIM Valuation | `src/core/rim_valuation.py` | `rim_score` | Decaying ROE intrinsic value $V_0$, discount ratio percentile rank per market | $[0.0, 1.0]$ | Integrated (NaN on low quality) |
| 10 | Event-Driven | `src/core/event_driven.py` | `event_score` | Filings weight + volume/price boost $\times$ sentiment intensity $[0.5, 1.5]$ | $[0.0, 1.0]$ | Integrated |
| 11 | MQ Factor | `src/core/mq_factor.py` | `mq_score` | $w_{mom} \times \text{rank}(R_{12M-1M}) + w_{qual} \times \text{mean}(\text{quality ranks})$ | $[0.0, 1.0]$ | Integrated |
| 12 | Options IV Skew | `src/core/iv_skew.py` | `iv_skew_score` | Option Put/Call IV ratio or realized vol/return skewness proxy | $[0.0, 1.0]$ | Integrated |
| 13 | Order Flow Imbalance | `src/core/order_flow.py` | `order_flow_score` | Percentile rank of composite $0.6 \text{MFI} + 0.25 \text{OBV} + 0.15 \text{VolAccel} + \text{InstBoost}$ | $[0.0, 1.0]$ | Integrated |
| 14 | Short-Term Reversal | `src/core/short_term_reversal.py` | `reversal_score` | Percentile rank of $-1.0 R_{5d} - 0.2 \text{DistLowerBand}$, filtered for margin $<-10\%$ | $[0.0, 1.0]$ | Integrated |
| 15 | ARM Factor | `src/core/arm_factor.py` | `arm_score` | MinMax normalization of analyst revisions / fundamental growth + price momentum | $[0.0, 1.0]$ | Integrated |
| 16 | CARD Factor | `src/core/card_factor.py` | `card_score` | Logistic sigmoid $1 / (1 + e^{0.1 \times \text{divergence}})$ of stock return vs macro shock | $(0.0, 1.0)$ | Integrated |
| 17 | LATR Factor | `src/core/latr_factor.py` | `latr_score` | MinMax norm of Gaussian score at 35% drawdown + volume surge - tail risk | $[0.0, 1.0]$ | Integrated |
| 18 | Inst & Foreign Sector | `src/core/inst_foreign_sector.py` | `inst_foreign_sector_score` | Percentile rank of $0.60 \text{Accumulation}_{40d} + 0.40 \text{SectorCorrelation}$ | $[0.0, 1.0]$ | Integrated |

### Score Bounds & Missingness Integrity
- **Valid 0.0 Preservation**: In `src/ai/ensemble_scorer.py` (line 1060), valid $0.0$ scores are preserved using `valid_mask = merged[score_col].notna() & np.isfinite(merged[score_col])`.
- **Dynamic Renormalization**: If a strategy output is `np.nan` (e.g. RIM score invalidated due to non-operating one-off earnings), `total_weight_series` only sums weights of valid strategies and normalizes cleanly:
  $$\text{linear\_score} = \frac{\sum_{i \in \text{Valid}} w_i S_i}{\sum_{i \in \text{Valid}} w_i}$$
- **Coverage Penalization**: If valid strategy count is below 40% of present DataFrames, a coverage penalty $0.5 + 0.5 \times (\text{ratio} / 0.40)$ scales down the ensemble score.

---

## 2. Audit of Isotonic Regression & Platt Probability Calibrators

### Implementation Structure
In `src/ai/ensemble_scorer.py` (lines 335-396):
```python
if n_samples >= 50:
    cal = IsotonicRegression(out_of_bounds="clip", increasing=True)
    cal.fit(s[mask], y[mask])
    self._calibrators[strategy] = ('isotonic', cal)
else:
    cal = LogisticRegression(C=1.0, max_iter=100)
    cal.fit(s[mask].reshape(-1, 1), y[mask])
    self._calibrators[strategy] = ('platt', cal)
```

### Key Findings & Safeguards
1. **Sample Size Thresholding**:
   - $N < 20$: Fitting is safely skipped to avoid overfitting on small samples. Uncalibrated raw scores are preserved.
   - $20 \le N < 50$: Uses Platt Scaling (`LogisticRegression(C=1.0)`).
   - $N \ge 50$: Uses non-parametric `IsotonicRegression(out_of_bounds="clip", increasing=True)`.
2. **Monotonicity Constraint**: `increasing=True` ensures that higher raw scores map to equal or higher calibrated probabilities, preventing rank inversion artifact distortions.
3. **Single-Class Target Variance Check**: `len(np.unique(y[mask])) < 2` checks whether target labels have both 0 and 1 outcomes. If target labels have zero variance (e.g. all 0s), calibrator fitting is skipped, preventing score flattening.
4. **Out-of-Bounds & Range Clipping**: `out_of_bounds="clip"` clips test scores outside the training range to the minimum/maximum fitted values, and outputs are clipped to $[0.0, 1.0]$.
5. **Verification Test Suite**: `tests/test_isotonic_sharpe_calibration.py` passes all unit tests for Isotonic fitting, Platt fitting, zero-variance handling, and rolling Sharpe calculation.

---

## 3. Audit of Gram-Schmidt & PCA ZCA Symmetric Factor Orthogonalization

### Mathematical Formulation
In `src/ai/factor_orthogonalizer.py`:
- **PCA ZCA Symmetric Decorrelation (`_pca_zca_symmetric`)**:
  Computes Ledoit-Wolf shrunk covariance matrix:
  $$\hat{C} = (1 - \alpha) C + \alpha I \quad (\alpha = 0.01)$$
  Eigen-decomposes $\hat{C} = V \Lambda V^T$ with ridge regularization $\lambda_i = \max(\lambda_i, 10^{-6})$, and applies the ZCA whitening operator:
  $$C^{-1/2} = V \Lambda^{-1/2} V^T, \quad X_{decorr} = \bar{X} C^{-1/2}$$
  Rescales back to original mean $\mu$ and standard deviation $\sigma$:
  $$X_{ortho} = \mu + X_{decorr} \times \sigma$$
- **Gram-Schmidt Process (`_gram_schmidt`)**:
  Orders columns by strategy weight $w_k$. The highest-weight strategy remains unprojected, while subsequent strategies subtract projections onto higher-weight orthogonal bases:
  $$u_k = x_k - \sum_{j < k} \frac{\langle x_k, u_j \rangle}{\|u_j\|^2} u_j$$

### Key Findings & Empirical Performance
1. **Multicollinearity Reduction**: Empirically verified in `tests/test_factor_orthogonalization.py` to reduce mean off-diagonal correlation from $>0.65$ to $<0.30$.
2. **Rank & Variance Preservation**: Spearman rank correlation between raw sum scores and decorrelated sum scores is $\ge 0.70$.
3. **Numerical Robustness**: Handles NaNs (mean-imputed during matrix projection and restored at output), constant columns, duplicate columns (handled via Ledoit-Wolf shrinkage and ridge regularization), and small sample sizes ($N=5$).
4. **Latency Benchmark**: Decorrelates 3,379 symbols $\times$ 17 strategies in $< 50$ ms.

---

## 4. Audit of Decision Rationales & Report Formatting Gap

### Decision Rationale Generation (`get_regime_reasoning_summary`)
In `src/ai/ensemble_scorer.py` (lines 579-653), `get_regime_reasoning_summary` generates a comprehensive, transparent decision rationale:
- 2D Regime State (e.g. `BULL_LOW_VOL`, `BEAR_HIGH_VOL`), trend rationale, volatility state, macro modifiers.
- Dual Market correlation (S&P500 vs KOSPI 20d correlation) and decoupling warnings.
- 18-Strategy Dynamic Weight Allocation (Base weight, rolling 20d Sharpe ratio, exponential Sharpe multiplier $\exp(\gamma \times \text{Sharpe})$, EMA smoothing).
- Microstructure Execution & Transaction Cost Rationale (Almgren-Chriss order size hypotheses, STT, SEC fee, dynamic spread, market impact).
- Multicollinearity & Noise Suppression metrics ($N_{eff}$, highest VIF, collinear pairs).

### Identified Gap: 18th Strategy Column (`IFS`) Omitted in Report Table Formatting

#### Observation
In `trading_system/run_pipeline.py` (lines 2938 and 2957), the text report formatting string for `ensemble_predictions.txt` formats 17 strategy columns (`Reg`, `Srg`, `L-L`, `VCP-R`, `VCP-M`, `LSTM`, `S-Arb`, `Sec-R`, `RIM`, `Event`, `MQ`, `IV-Sk`, `Flow`, `Rev`, `ARM`, `CARD`, `LATR`), but omits the 18th strategy column `IFS` (`inst_foreign_sector_score`).

#### Line References
- Header line 2938:
  ```python
  f"{'Rank':<5}{'Symbol':<10}{'Name':<18}{'Ens Score':<12}{'Expected Ret':<14}{'Reg':<5}{'Srg':<5}{'L-L':<5}{'VCP-R':<6}{'VCP-M':<6}{'LSTM':<5}{'S-Arb':<6}{'Sec-R':<6}{'RIM':<5}{'Event':<6}{'MQ':<5}{'IV-Sk':<6}{'Flow':<5}{'Rev':<5}{'ARM':<5}{'CARD':<6}{'LATR':<5}\n"
  ```
- Row format line 2957:
  ```python
  f"{rank:<5}{row['symbol']:<10}{name_str:<18}{row['ensemble_score']*100:>10.1f}%{row['ensemble_expected_return']:>12.2f}%{row['reg_score']*100:>4.0f}%{row['surge_score']*100:>4.0f}%{row['ll_score']*100:>4.0f}%{vcp_rule_val*100:>5.0f}%{row['vcp_ml_score']*100:>5.0f}%{lstm_val*100:>4.0f}%{sa_val*100:>5.0f}%{sec_val*100:>5.0f}%{rim_val*100:>4.0f}%{ev_val*100:>5.0f}%{mq_val*100:>4.0f}%{iv_val*100:>5.0f}%{of_val*100:>4.0f}%{rev_val*100:>4.0f}%{arm_val*100:>4.0f}%{card_val*100:>5.0f}%{latr_val*100:>4.0f}%\n"
  ```

#### Impact
When `trading_system/generate_report.py` reads `ensemble_predictions.txt` (line 335):
```python
inst_foreign_sector=s_vals[17] if len(s_vals) > 17 else "-"
```
Because only 17 strategy values are written per row in `ensemble_predictions.txt`, `len(s_vals)` equals 17, causing `inst_foreign_sector` to evaluate to `"-"` in the generated `gh-pages/index.html` report.

#### Recommended Fix
Update lines 2938, 2955, and 2957 in `trading_system/run_pipeline.py`:
```python
# Extract ifs_val
ifs_val = row.get('inst_foreign_sector_score', 0.0)

# Header update (add IFS column)
f"{'Rank':<5}{'Symbol':<10}{'Name':<18}{'Ens Score':<12}{'Expected Ret':<14}{'Reg':<5}{'Srg':<5}{'L-L':<5}{'VCP-R':<6}{'VCP-M':<6}{'LSTM':<5}{'S-Arb':<6}{'Sec-R':<6}{'RIM':<5}{'Event':<6}{'MQ':<5}{'IV-Sk':<6}{'Flow':<5}{'Rev':<5}{'ARM':<5}{'CARD':<6}{'LATR':<5}{'IFS':<5}\n"

# Row format update
f"{rank:<5}{row['symbol']:<10}{name_str:<18}{row['ensemble_score']*100:>10.1f}%{row['ensemble_expected_return']:>12.2f}%{row['reg_score']*100:>4.0f}%{row['surge_score']*100:>4.0f}%{row['ll_score']*100:>4.0f}%{vcp_rule_val*100:>5.0f}%{row['vcp_ml_score']*100:>5.0f}%{lstm_val*100:>4.0f}%{sa_val*100:>5.0f}%{sec_val*100:>5.0f}%{rim_val*100:>4.0f}%{ev_val*100:>5.0f}%{mq_val*100:>4.0f}%{iv_val*100:>5.0f}%{of_val*100:>4.0f}%{rev_val*100:>4.0f}%{arm_val*100:>4.0f}%{card_val*100:>5.0f}%{latr_val*100:>4.0f}%{ifs_val*100:>4.0f}%\n"
```

---

## 5. Summary of Recommended Actions

1. **Format String Patch**: Apply the recommended fix in `run_pipeline.py` (lines 2938 and 2957) so `inst_foreign_sector_score` (`IFS`) is printed as the 18th column in `ensemble_predictions.txt`, allowing `generate_report.py` to display all 18 strategies cleanly in `gh-pages/index.html`.
2. **Maintain Verification Standards**: Retain existing unit tests (`test_isotonic_sharpe_calibration.py`, `test_factor_orthogonalization.py`, `test_r1_ensemble_regime_fixes.py`) as mandatory regression benchmarks.
