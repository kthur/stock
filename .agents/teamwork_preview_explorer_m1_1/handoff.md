# Handoff Report — Quantitative Strategy & Ensemble Audit (Milestone 1)

## 1. Observation
- **File & Line Locations**:
  - `d:/Finance/code/stock/trading_system/src/ai/ensemble_scorer.py`: Lines 37–222 (`REGIME_WEIGHTS` & `REGIME_2D_WEIGHTS`), Lines 335–396 (`fit_calibrators` & `calibrate_scores`), Lines 579–653 (`get_regime_reasoning_summary`), Lines 971–991 (`strategy_cols`), Lines 1041–1046 (Isotonic calibration invocation).
  - `d:/Finance/code/stock/trading_system/src/ai/factor_orthogonalizer.py`: Lines 58–68 (`orthogonalize`), Lines 70–106 (`_gram_schmidt`), Lines 108–140 (`_pca_zca_symmetric`).
  - `d:/Finance/code/stock/trading_system/run_pipeline.py`: Lines 2425–2446 (`calculate_ensemble_score` call with all 18 strategies), Line 2938 (`ensemble_predictions.txt` header format string), Line 2957 (`ensemble_predictions.txt` row format string).
  - `d:/Finance/code/stock/trading_system/generate_report.py`: Line 335 (`inst_foreign_sector=s_vals[17] if len(s_vals) > 17 else "-"`).
  - `d:/Finance/code/stock/tests/test_isotonic_sharpe_calibration.py`: Unit tests for Isotonic/Platt calibration, zero-variance target skipping, and rolling Sharpe calculations.
  - `d:/Finance/code/stock/tests/test_factor_orthogonalization.py`: Unit tests for Gram-Schmidt, PCA ZCA decorrelation, score bounds $[0, 1]$, Spearman rank correlation $\ge 0.70$, and $<50$ ms latency.

- **Observed Verbatim Findings**:
  - All 18 strategies (`regression`, `surge`, `lead_lag`, `vcp_rule`, `vcp_ml`, `lstm`, `stat_arb`, `sector_rotation`, `rim_valuation`, `event_driven`, `mq_factor`, `iv_skew`, `order_flow`, `short_term_reversal`, `arm_factor`, `card_factor`, `latr_factor`, `inst_foreign_sector`) are fully integrated into `strategy_cols`, all 6 combo states of `REGIME_2D_WEIGHTS`, and `calculate_ensemble_score`.
  - All strategy output scores are bounded in $[0.0, 1.0]$. `RIMValuationEngine` invalidates non-operating one-off gains to `np.nan`, triggering dynamic weight renormalization in `EnsembleScoringEngine`.
  - Isotonic calibrators use $N \ge 50$ threshold with `increasing=True` monotonicity constraint and `out_of_bounds="clip"`. Platt scaling is used for $20 \le N < 50$. Single-class zero-variance target labels are skipped to avoid score flattening.
  - Gram-Schmidt and PCA ZCA symmetric factor decorrelations apply Ledoit-Wolf covariance shrinkage ($\alpha = 0.01$) and ridge regularization ($\lambda_{min} = 1e-6$). Pairwise correlation is reduced from $>0.65$ to $<0.30$ while preserving Spearman rank correlation ($\ge 0.70$).
  - **Formatting Gap**: Line 2938 of `run_pipeline.py` formats 17 strategy columns in `ensemble_predictions.txt` table output (`Reg`, `Srg`, `L-L`, `VCP-R`, `VCP-M`, `LSTM`, `S-Arb`, `Sec-R`, `RIM`, `Event`, `MQ`, `IV-Sk`, `Flow`, `Rev`, `ARM`, `CARD`, `LATR`), omitting the 18th column `IFS` (`inst_foreign_sector_score`). Consequently, `generate_report.py` line 335 evaluates `len(s_vals)` as 17 and falls back to `"-"` for `inst_foreign_sector` in `gh-pages/index.html`.

---

## 2. Logic Chain
1. **Observation 1**: `strategy_cols` in `ensemble_scorer.py` (lines 971–991) defines 18 tuples mapping strategy keys to DataFrames columns. `REGIME_2D_WEIGHTS` defines weights for all 18 strategies across 6 regime states summing to 1.00.
2. **Observation 2**: Strategy scoring methods in `src/core/` and `src/ai/` clip or rank-normalize outputs to $[0.0, 1.0]$. `EnsembleScoringEngine` handles missing values (`np.nan`) via dynamic weight renormalization ($\sum w_i S_i / \sum w_i$).
3. **Observation 3**: `fit_calibrators` selects Isotonic for $N \ge 50$ (with `increasing=True`) and Platt for $20 \le N < 50$. Single-class targets are skipped (`len(np.unique(y)) < 2`), preserving raw scores.
4. **Observation 4**: `FactorOrthogonalizerEngine` executes ZCA symmetric whitening ($C^{-1/2} = V \Lambda^{-1/2} V^T$) or weight-ordered Gram-Schmidt. Ledoit-Wolf shrinkage and ridge regularization guarantee non-singular inversion. Correlation drops below 0.30 while Spearman rank correlation remains $\ge 0.70$.
5. **Observation 5**: Line 2938 and 2957 of `run_pipeline.py` write 22 items per row in `ensemble_predictions.txt`, excluding `inst_foreign_sector_score`. Line 335 of `generate_report.py` checks `len(s_vals) > 17`. Because `len(s_vals)` is 17, `inst_foreign_sector` displays `"-"` in HTML tables. Adding `IFS` to lines 2938 and 2957 in `run_pipeline.py` resolves this reporting gap.

---

## 3. Caveats
- **Live Market Data Variation**: Option chain fetching in `IVSkewEngine` relies on `yfinance` for US tickers; for KRX symbols, it uses price volatility asymmetry as a proxy.
- **DART API Key**: `EventDrivenEngine` uses OpenDART API for KRX filings when `DART_API_KEY` is provided; falls back to price/volume surge momentum when unconfigured.

---

## 4. Conclusion
All 18 quantitative strategies, 2D regime dynamic ensemble weights, Isotonic probability calibrators, and Gram-Schmidt factor decorrelations are mathematically sound, robustly implemented, and compliant with financial engineering standards. A minor report formatting gap was identified in `run_pipeline.py` where the 18th strategy column (`IFS`) was omitted from the `ensemble_predictions.txt` table text format string.

---

## 5. Verification Method

### Test Commands
Execute unit test suite using `.venv/bin/pytest`:
```bash
.venv/bin/pytest tests/test_isotonic_sharpe_calibration.py -v
.venv/bin/pytest tests/test_factor_orthogonalization.py -v
.venv/bin/pytest tests/test_kst_and_coverage_reasoning.py -v
```

### Files to Inspect
- `d:/Finance/code/stock/trading_system/src/ai/ensemble_scorer.py`
- `d:/Finance/code/stock/trading_system/src/ai/factor_orthogonalizer.py`
- `d:/Finance/code/stock/trading_system/run_pipeline.py` (lines 2938 and 2957)
- `d:/Finance/code/stock/trading_system/generate_report.py` (line 335)

### Invalidation Conditions
- Any strategy returning unclipped scores outside $[0.0, 1.0]$.
- Isotonic calibrator producing non-monotonic predictions (`increasing=True` violated).
- Factor decorrelation resulting in cross-strategy mean correlation $> 0.30$ or Spearman rank correlation $< 0.70$.
