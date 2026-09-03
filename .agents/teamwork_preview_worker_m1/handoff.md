# Handoff Report — Milestone 1: Alpha Signal Quality & Strategy Engine Remediation (R1)

**Agent**: `teamwork_preview_worker_m1` (Alpha Strategy Worker)  
**Parent Conversation ID**: `9f89ea60-abb5-4468-88df-62eb0473f19b`  
**Date**: 2026-09-03  
**Handoff Type**: Hard (Task Complete)

---

## 1. Observation

Direct code inspections, modifications, and execution outputs:

1. **Multi-Horizon Alpha Scaling & Exponential Decay (`src/ai/ensemble_scorer.py`)**:
   - `STRATEGY_HALF_LIVES` lacked Strategy 35 (`dual_correction`: 4.0d) and Strategy 37 (`overnight_gap_reversal`: 0.5d), and had `index_rebalance` at 20.0d instead of 15.0d.
   - `score_col_to_strat` lacked mappings for `dual_correction_score`, `index_rebalance_score`, `overnight_gap_score`, and `overnight_gap_reversal_score`.
   - In `ensemble_scorer.py:1771`, regression score conversion had a hardcoded $2 \times 0.20$ denominator: `(0.50 + frac_vals / (2.0 * 0.20)).clip(0.0, 1.0)`. This compressed short-horizon (1d, 3d, 5d) signals into an ultra-narrow band around 0.50.
   - Applied adaptive horizon scaling: $E_{\max}(h) = 0.20 \times \sqrt{\max(1, h) / 20.0}$ with a safety floor of 0.02, scaling short-horizon resolution while leaving 20d invariant ($E_{\max}(20) = 0.20$).

2. **Cross-Sectional Normalization & Sparse Factor Isolation (`src/ai/score_normalizer.py`)**:
   - `rank_percentile` contained $N \ge 4$ zero-block isolation (MED-09), mapping 0-scores to neutral 0.50 and non-zeros to $[0.52, 0.995]$.
   - `winsorized_zscore` lacked this zero-block protection, causing inactive zero-score stocks in sparse factors (Event-Driven, Short Squeeze, Darkpool) to receive negative z-scores and artificially low Gaussian CDF percentiles (0.15~0.35).
   - Added zero-block isolation to `winsorized_zscore` for $N \ge 4$, mapping inactive zero-score stocks to exact 0.50 and non-zeros via Winsorized Z-score CDF into $[0.52, 0.995]$.
   - Extended `normalize_scores`, `normalize_cross_section`, and `normalize` with `sector_col: Optional[str] = None` and hierarchical fallback: `(market, sector) -> market -> regional/global`.

3. **Orthogonalization & Consensus Alpha Preservation (`src/ai/factor_orthogonalizer.py`, `src/ai/ensemble_scorer.py`)**:
   - In `factor_orthogonalizer.py`, `preserve_consensus_pc1` defaulted to `False`, allowing ZCA whitening to compress PC1 (consensus alpha) by ~68%. Changed default to `preserve_consensus_pc1=True` in both `__init__` and `_pca_zca_symmetric`.
   - In `ensemble_scorer.py`, `enable_coverage_shrinkage` was not initialized in `__init__` (defaulting to `False`). Set `self.enable_coverage_shrinkage = getattr(config, 'enable_coverage_shrinkage', True)`. In `combine_predictions`, Bayesian coverage shrinkage now shrinks stocks with valid weight $< 0.60$ toward the cross-sectional mean ($CS_{\text{mean}}$) rather than a rigid 0.50.
   - In `ensemble_scorer.py:2837`, verified the US ticker regex `r'^[A-Z]{1,5}(\.[A-Z])?$'` correctly identifies dot-delimited tickers like `BRK.B` and applies SEC fee (0.003%) rather than Korean STT (0.15%).
   - In `factor_suppression.py`, verified `CLUSTER_MAP` properly maps `dual_correction` to `REVERSAL`, `overnight_gap_reversal` to `REVERSAL`, and `index_rebalance` to `FLOW_MICRO`.

4. **Strategy Defect Remediations (`src/core/`)**:
   - `src/core/strategy_registry.py` & `src/core/dual_correction.py`: Added explicit `is_standalone=False` to `StrategyMeta` for `dual_correction`.
   - `src/core/arm_factor.py`: In `compute_scores` and added `calculate_scores` alias, missing revision data and missing symbols return `np.nan` instead of 0.50 (MED-04).
   - `src/core/short_interest_squeeze.py`: Fixed missing data fallback in `calculate_scores` so single-symbol and multi-symbol missing data strictly produce `np.nan` instead of 0.50 (HIGH-12), and added `fundamentals_dict` keyword support.

5. **Test Execution Results**:
   - Command: `.venv\Scripts\python.exe -m pytest tests/test_score_normalizer.py tests/test_correlation_suppression.py tests/test_adversarial_ensemble_scorer_challenger.py tests/test_v8_remediation.py -v`
   - Result: `64 passed in 38.87s` (100% pass, 0 failures, 0 regressions).
   - Additional Adversarial Verification: `tests/test_adversarial_normalizer_m1.py` -> `31 passed in 30.58s`.

---

## 2. Logic Chain

1. **Multi-Horizon Scaling**:
   - Volatility scales with $\sqrt{h}$. A 20% return in 1 day is a $10\sigma$ event, whereas in 20 days it is a $2\sigma$ event.
   - Scaling the denominator by $E_{\max}(h) = 0.20 \times \sqrt{h / 20.0}$ normalizes signal conviction dynamically across time horizons without distorting the canonical 20-day horizon benchmark.

2. **Inactive Zero-Score Isolation**:
   - In sparse catalysts (short squeeze, M&A/event driven, darkpool block trades), a score of 0.0 indicates *no catalyst detected*, which should be economically neutral ($S = 0.50$).
   - Standard z-scoring treats 0.0 as a negative tail outlier when all active signals are positive ($x > 0$), severely penalizing neutral assets.
   - Partitioning the cross-section into inactive zeros ($S = 0.50$) and active positive signals mapped to $[0.52, 0.995]$ preserves neutrality and relative conviction simultaneously.

3. **Consensus PC1 & Bayesian Coverage**:
   - Factor orthogonalization should eliminate collinear noise without dampening unanimous multi-strategy consensus (PC1). Setting `preserve_consensus_pc1=True` locks the leading eigenvector multiplier to 1.0.
   - For stocks with scarce data coverage ($W_{\text{valid}} < 0.60$), shrinking toward the cross-sectional mean prevents lucky single-factor outliers from dominating fully corroborated 37-strategy stocks while preserving broad market alignment.

4. **Missing Data NaN Discipline**:
   - Returning 0.50 for missing data corrupts rank normalizers and bypasses dynamic weight renormalization.
   - Strict `np.nan` propagation triggers dynamic weight renormalization, redistributing weight to genuinely observed strategies.

---

## 3. Caveats

- All changes strictly adhere to EXCLUSIVE WRITE OWNERSHIP across the 8 designated files.
- Sector neutralization (`sector_col`) defaults to `None` in existing call chains, ensuring complete backward compatibility while enabling sector-neutral ranking when sector metadata is provided.

---

## 4. Conclusion

All Requirement 1 (R1) Milestone 1 task objectives are implemented, tested, and verified:
1. Multi-horizon alpha scaling and half-life decay mapping completed.
2. Cross-sectional normalizer enhanced with winsorized z-score 0-block isolation and sector neutralization.
3. Factor orthogonalizer PC1 preservation and Bayesian coverage shrinkage activated by default.
4. Strategy defects in `dual_correction`, `arm_factor`, and `short_interest_squeeze` remediated.
5. All 64 primary and 31 adversarial tests pass with 100% success and zero regressions.

---

## 5. Verification Method

To independently reproduce and verify this implementation:

```powershell
# 1. Execute the primary R1 test suite
.venv\Scripts\python.exe -m pytest tests/test_score_normalizer.py tests/test_correlation_suppression.py tests/test_adversarial_ensemble_scorer_challenger.py tests/test_v8_remediation.py -v

# 2. Execute the adversarial normalizer test suite
.venv\Scripts\python.exe -m pytest tests/test_adversarial_normalizer_m1.py -v

# 3. Inspect git diff for the 8 modified files
git diff trading_system/src/ai/score_normalizer.py trading_system/src/ai/ensemble_scorer.py trading_system/src/ai/factor_orthogonalizer.py trading_system/src/core/arm_factor.py trading_system/src/core/dual_correction.py trading_system/src/core/short_interest_squeeze.py
```

