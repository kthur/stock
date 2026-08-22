# Handoff Report — Requirement R1 Survey & Technical Investigation

## 1. Observation
- **Ensemble Scorer Pipeline**: In `trading_system/src/ai/ensemble_scorer.py` (lines 1330–1835), raw predictions from 31 strategies are collected with heterogeneous transformations:
  - Regression (line 1417): `(reg_df_copy[target_col] * ret_multiplier).clip(0.0, 1.0)` with `_return_multiplier = 20.0`.
  - Surge Classifier (line 1442): `s_df_copy[target_col_surge].clip(0.0, 1.0)`.
  - Strict Causal LSTM (line 1517): `(l_df[target_col] * self._return_multiplier).clip(0.0, 1.0)`.
  - Stat-Arb (line 1536): `(np.abs(sa_df[target_col]) / 3.0).clip(0.0, 1.0)`.
  - Missing column fallbacks (lines 1419, 1444, 1453, 1507, 1526, 1540, 1551): Assign hardcoded `0.5` directly to the DataFrame.
- **Factor Orthogonalizer**: In `trading_system/src/ai/factor_orthogonalizer.py` (lines 44–90), PCA ZCA and Gram-Schmidt process raw inputs whose column variances and means vary widely, and restore original scales via $X_{\text{ortho}, k} = \mu_k + \frac{u_k}{\sigma(u_k)} \cdot \sigma_k$.
- **Hardcoded 0.50 Fallbacks in Strategy Engines**:
  - `src/core/accruals_quality.py` line 148: `df_acc['accruals_quality_score'] = df_acc['accruals_quality_score'].fillna(0.50).astype(float)`
  - `src/core/valueup_catalyst.py` line 157: `df_out['valueup_catalyst_score'] = df_out['valueup_catalyst_score'].fillna(0.50).astype(float)`
  - `src/core/short_interest_squeeze.py` line 146: `df_out['short_squeeze_score'] = df_out['short_squeeze_score'].fillna(0.50).astype(float)`
  - `src/core/trend_efficiency.py` line 152: `df_out['trend_efficiency_score'] = df_out['trend_efficiency_score'].fillna(0.50).astype(float)`
  - `src/core/insider_buying.py` line 78: `scores_map = {sym: 0.50 for sym in symbols}`
  - `src/core/earnings_tone_drift.py` line 97: `score = 0.50`
  - `run_pipeline.py` line 3261: `'darkpool_score': 0.50`
  - `run_pipeline.py` line 2769: `merged[score_col] = pd.to_numeric(merged[score_col], errors='coerce').fillna(0.5)`
- **Dynamic Weighting Mechanism**: In `ensemble_scorer.py` (lines 2003–2014), the denominator `total_weight_series` accumulates weights only when `merged[score_col].notna() & np.isfinite()`. Injecting `0.50` causes missing signals to be treated as valid, destroying the ticker-level re-normalization.

## 2. Logic Chain
1. **Observation 1 & 2 $\to$ Variance Domination**: Strategies with large standard deviations and clipped bimodal extremes (Regression, LSTM) contribute disproportionately to the linear sum variance $\text{Var}(S) = \sum w_k^2 \text{Var}(X_k)$, overpowering low-mean/low-variance signals like Surge probability.
2. **Observation 3 & 4 $\to$ Re-normalization Failure**: Because missing signals are populated with `0.50` instead of `np.nan`, `valid_mask` evaluates to `True`. As a result, the missing strategy is not zero-weighted, injecting an artificial $0.50 \cdot w_k$ component that pulls high-conviction alphas down and inflates low-conviction stocks.
3. **Synthesis $\to$ Solution**:
   - Applying `CrossSectionalScoreNormalizer` (percentile rank $U(0, 1)$ or winsorized Gaussian CDF $\Phi(Z) \in [0, 1]$) per market prior to orthogonalization homogenizes all 31 strategy variances to a common scale.
   - Purging all `.fillna(0.50)` and default `0.50` mappings across core engines allows `valid_mask` to properly identify missing signals, zero-out their weights, and re-normalize active weights so $\sum_{k \in \text{Active}(i)} \tilde{w}_{i,k} = 1.0$.

## 3. Caveats
- For markets or subsets with very small sample sizes ($N < 10$), per-market percentile ranking has discrete step increments. The normalizer must fallback to combined regional (KR vs US) or global cross-sections.
- Invalidation masks (such as RIM's operating loss or negative BPS filter) must continue to output strict `NaN` to participate seamlessly in dynamic zero-weighting.

## 4. Conclusion
Requirement R1 requires two coordinated modifications:
1. Implementation and insertion of `CrossSectionalScoreNormalizer` in `src/ai/score_normalizer.py` and `EnsembleScoringEngine.combine_predictions`.
2. Removal of artificial `0.50` defaults in `accruals_quality.py`, `valueup_catalyst.py`, `short_interest_squeeze.py`, `trend_efficiency.py`, `insider_buying.py`, `earnings_tone_drift.py`, `iv_skew.py`, `run_pipeline.py`, and `ensemble_scorer.py`.

The full technical specification is detailed in `survey_r1.md`.

## 5. Verification Method
- Inspect `d:\Finance\code\stock\.agents\explorer_survey_1\survey_r1.md`.
- Run unit test suite: `.venv\Scripts\pytest tests/ -v`.
- Verify new test cases covering:
  - `test_cross_sectional_score_normalizer_uniform_variance`
  - `test_dynamic_zero_weighting_no_05_pollution`
  - `test_strategy_engines_return_genuine_nans`
