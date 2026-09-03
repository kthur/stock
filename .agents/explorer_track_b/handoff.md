# Track B Handoff Report: 37-Strategy Trading System Integrity & Operational Audit

**Working Directory**: `d:\Finance\code\stock\.agents\explorer_track_b`  
**Report Artifact**: `d:\Finance\code\stock\.agents\explorer_track_b\audit_report.md`  
**Date**: 2026-09-03  
**Auditor**: Explorer Track B  

---

## 1. Observation

1. **`trading_system/src/ai/ensemble_scorer.py` Lines 967-969**:
   ```python
   subset_df = scores_df[list(valid_cols.values())].apply(pd.to_numeric, errors='coerce').dropna()
   if len(subset_df) < 10:
       return weights
   ```
   Executing `.dropna()` across all 37 strategy columns drops every row containing any NaN, causing `len(subset_df) < 10` in typical cross-sections and silently returning unpenalized weights.

2. **`trading_system/src/ai/ml_strategy_adapters.py` Lines 373-375**:
   ```python
   from src.core.hft_engine import MicrostructureImbalanceEngine
   engine = MicrostructureImbalanceEngine()
   res = engine.compute_scores(prices_dict=prices_dict, **kwargs)
   ```
   `DarkPoolStrategyAdapter` for Strategy 30 instantiates `MicrostructureImbalanceEngine` (Strategy 23) instead of `DarkPoolTrackerEngine` from `src.data_layer.darkpool_tracker`.

3. **`trading_system/src/ai/factor_orthogonalizer.py` Lines 226-235**:
   ```python
   # Multi-model consensus preservation (V7-03):
   # Do not compress the leading principal component (PC1 = shared multi-strategy consensus).
   # For lambda_max (last eigen-pair in ascending eigh), keep whitening filter = 1.0.
   # For residual eigenvalues, apply smooth spectral Tikhonov damping.
   lambdas_clean = np.maximum(eigenvalues, 0.0)
   ridge_eps = float(np.clip(self.ridge_epsilon, 1e-6, 1e-3))
   whitening_filter = 1.0 / np.sqrt(lambdas_clean + ridge_eps)
   ```
   The code does not set `whitening_filter[-1] = 1.0`, uniformly compressing PC1 consensus alpha by up to 68% and amplifying near-zero noise eigenvalues by up to 1000x without condition number capping.

4. **`trading_system/src/ai/factor_suppression.py` Lines 74-80**:
   `CLUSTER_MAP` contains only 34 strategies. Strategies 35 (`dual_correction`), 36 (`index_rebalance`), and 37 (`overnight_gap_reversal`) are absent and fall back to cluster `'OTHER'`, evading intra-cluster penalties and 2D regime high-risk cluster suppression.

5. **`trading_system/src/ai/ensemble_scorer.py` Lines 2504-2511, 2566**:
   `_calc_tier_score` computes `sub_sums / np.maximum(v_counts, 1)` (unweighted average) and blends 30% into `linear_score`, diluting dynamic regime weights by 30%.

6. **`trading_system/src/ai/ensemble_scorer.py` Lines 2801-2803**:
   `is_us_stock` uses `sym_col.str.isalpha() & (sym_col.str.len() <= 5)`, which evaluates to `False` for tickers with periods like `BRK.B`, causing Korean STT (0.18%) and Korean order sizing (50,000,000 KRW) to be misapplied.

---

## 2. Logic Chain

1. **Correlation Penalty Failure (Obs 1 $\rightarrow$ C-01)**:
   In real production universes, non-price strategies naturally have missing data for some tickers. By enforcing `.dropna()` across all 37 strategy columns simultaneously, the intersection of complete observations is less than 10 symbols. Because `len(subset_df) < 10` triggers an immediate early return, Löwdin symmetric orthogonalization penalty is never computed in practice.

2. **Darkpool Strategy Inversion (Obs 2 $\rightarrow$ C-02)**:
   `DarkPoolStrategyAdapter` is registered as `darkpool` in `StrategyRegistry`. Any consumer calling the strategy via the registry or modular pipelines receives `MicrostructureImbalanceEngine` results. This produces duplicated Strategy 23 scores, corrupts factor diversification, and violates strategy isolation.

3. **Consensus Suppression in ZCA (Obs 3 $\rightarrow$ C-03)**:
   When 37 strategies agree on top picks, $\lambda_{\max}$ is large ($> 8.0$). Since $1 / \sqrt{\lambda_{\max}} \approx 0.35$, the consensus signal is dampened by 65%. Simultaneously, collinear null space eigenvalues near 0 receive $1 / \sqrt{10^{-6}} = 1000$ multipliers, amplifying numerical precision noise into artificial factor bets.

4. **Cluster Map Evasion (Obs 4 $\rightarrow$ H-01)**:
   Strategies 35, 36, and 37 not being in `CLUSTER_MAP` results in `cluster == 'OTHER'`. Thus, `is_same_cluster` is always `False`, and `is_high_risk_i` is always `False`. As a result, mean-reversion and flow strategies escape noise dampening in trending and high-vol regimes.

5. **Tier Alpha Dilution (Obs 5 $\rightarrow$ H-02)**:
   `linear_score = 0.70 * linear_score + 0.30 * hierarchical_score`. Because `hierarchical_score` uses unweighted averages inside each tier, 30% of the final signal is equal-weighted noise, undermining Sharpe-optimized regime weights.

---

## 3. Caveats

- **Track Scope Boundary**: Track B focuses exclusively on Strategies 20–37, normalization, ZCA whitening, suppression, and dynamic ensemble. Portfolio allocation algorithms (HRP/Ledoit-Wolf/CVaR) and OMS order routing were audited only at the interface level where ensemble expected returns and friction costs are consumed.
- **Assumed Data Availability**: It is assumed that daily OHLCV and market indicators (`indicators_df`) are available in SQLite WAL databases for inference runs.
- **No Direct Source Code Edits**: Consistent with the read-only exploration mandate, no production files were modified directly. All findings are documented with exact lines and targeted code snippets in `audit_report.md`.

---

## 4. Conclusion

The 37-strategy mathematical weighting matrix in `ensemble_scorer.py` satisfies normalization to 1.0000 across all 1D and 2D regimes. However, three critical engineering defects (C-01: `.dropna()` correlation bypass, C-02: darkpool adapter miswiring, and C-03: consensus alpha suppression in ZCA) prevent the system from operating as designed. Addressing the prioritized 12 issues (3 Critical, 5 High, 4 Medium) according to the phased remediation plan will restore full algorithmic fidelity and improve expected risk-adjusted returns (Sharpe ratio).

---

## 5. Verification Method

1. **Verify Regime Weight Normalization**:
   ```bash
   .venv/Scripts/python.exe -c "import sys; sys.path.insert(0, 'trading_system'); from src.ai.ensemble_scorer import EnsembleScoringEngine; e = EnsembleScoringEngine(); assert all(abs(sum(w.values()) - 1.0) < 1e-6 for w in e.REGIME_WEIGHTS.values()); assert all(abs(sum(w.values()) - 1.0) < 1e-6 for w in e.REGIME_2D_WEIGHTS.values()); print('ALL 37-STRATEGY REGIME WEIGHTS SUM TO 1.000000')"
   ```
2. **Run Existing Test Suite**:
   ```bash
   .venv/Scripts/pytest tests/test_score_normalizer.py -v
   ```
3. **Verify ZCA Consensus Preservation Fix**:
   Execute synthetic whitening test checking that `whitening_filter[-1] == 1.0` and PC1 variance is preserved.
4. **Inspect Audit Report Artifact**:
   Review detailed findings and diff proposals at `d:\Finance\code\stock\.agents\explorer_track_b\audit_report.md`.
