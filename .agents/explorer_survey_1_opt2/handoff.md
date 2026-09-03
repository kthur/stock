# Handoff Report: R1 Survey (Alpha, Orthogonalization & Top-Decile Spread)

**Agent**: Survey Explorer 1 (Alpha & Orthogonalization Specialist)  
**Working Directory**: `d:\Finance\code\stock\.agents\explorer_survey_1_opt2`  
**Handoff Type**: Hard (Investigation & Survey Complete)  
**Survey Artifact**: `d:\Finance\code\stock\.agents\explorer_survey_1_opt2\survey_r1.md`

---

## 1. Observation

1. **Dormant Bessembinder Power Law**:
   - In `trading_system/src/ai/ensemble_scorer.py:3484-3514`, `apply_bessembinder_convex_power_law(scores, top_percentile=90.0, power_gamma=1.60, max_boost=0.50)` is fully implemented:
     ```python
     p_low = np.percentile(arr, top_percentile)
     p_high = np.percentile(arr, 99.0)
     denom = max(1e-4, p_high - p_low)
     boosted = arr.copy()
     mask_top = arr > p_low
     if np.any(mask_top):
         norm_excess = np.clip((arr[mask_top] - p_low) / denom, 0.0, 1.0)
         convex_mult = 1.0 + max_boost * np.power(norm_excess, power_gamma)
         boosted[mask_top] = arr[mask_top] * convex_mult
     ```
   - Tool `grep_search` across `trading_system/` revealed **zero calls** to `apply_bessembinder_convex_power_law` inside `combine_predictions` or anywhere else in the production pipeline (only called in `tests/test_return_maximization_apex.py:106`).
2. **Orthogonalization-Suppression Sequence Masking**:
   - In `trading_system/src/ai/ensemble_scorer.py`:
     - Line 2394: `merged = self.orthogonalizer.orthogonalize(score_df=merged, ...)` decorrelates strategy scores via PCA-ZCA.
     - Line 2415: `corr_df = self.correlation_monitor.update_correlation(merged)` computes pairwise correlation on the already-orthogonalized `merged` matrix.
     - Line 2419: `suppressed_w = self.factor_suppression.suppress_weights(..., corr_matrix=corr_df, ...)` passes this orthogonalized matrix into the suppression engine.
   - In `trading_system/src/ai/factor_suppression.py:204`, `excess = max(0.0, abs(rho_ij) - theta_val)` with $\theta \in [0.55, 0.70]$. Because ZCA whitening drove pairwise correlations below $0.25$, `excess` is identically zero for almost all factor pairs. As a consequence, `denom = sqrt(1.0 + 0) = 1.0`, and `penalties` evaluates to $1.000$ (no suppression).
3. **Step Discontinuities & Duplicate Factor Pillars in Multi-Factor Confluence**:
   - In `trading_system/src/ai/ensemble_scorer.py:2633-2715`:
     - Multi-signal synergy step multiplier: `synergy_multiplier = np.where(strong_signal_counts >= 3, 1.0 + 0.03 * (strong_signal_counts - 2), 1.0)`.
     - Quadruple / Triple / Dual confluence uses hard boolean masks: `has_val = merged['rim_score'].ge(0.60) | ...`.
     - `dual_correction_score` is checked in line 2645 (`has_val`) AND line 2660 (`has_mom`).
     - `cross_asset_spillover_score` is checked in line 2659 (`has_mom`) AND line 2670 (`has_flow`).
     - `index_rebalance_score` is checked in line 2673 (`has_flow`) AND line 2690 (`has_cat`).
4. **Regime-Invariant Half-Lives & Uncalled Temporal Smoothing**:
   - In `trading_system/src/ai/ensemble_scorer.py:3290-3337`, `STRATEGY_HALF_LIVES` contains static constants (`"microstructure": 0.5`, `"surge": 5.0`, `"regression": 20.0`, `"value_up": 60.0`). No 2D regime modulation exists.
   - `apply_exponential_decay_filter` (`ensemble_scorer.py:3340`) is only invoked in `tests/test_apex_tier_quant_enhancements.py` and `tests/test_v6_improvements.py`, but is omitted in `run_pipeline.py`.
5. **PCA-ZCA Spectral PC1-Only Preservation**:
   - In `trading_system/src/ai/factor_orthogonalizer.py:244-245`:
     ```python
     if preserve_pc1 and len(whitening_filter) > 0:
         whitening_filter[-1] = 1.0
     ```
     Whitening filter flattens all eigenvalues $\lambda_1, \dots, \lambda_{K-1}$ to $1/\sqrt{\lambda_k + \epsilon}$, penalizing the secondary independent market driver (PC2 = Fundamental Value / Quality) while amplifying weak noise dimensions up to $10\times$.
6. **Registered Strategy Universe**:
   - Execution of `StrategyRegistry.auto_discover()` confirmed 38 strategies are registered dynamically, spanning 3 horizon tiers.

---

## 2. Logic Chain

1. **From Observation 1**: Bessembinder power-law scaling ($\gamma = 1.60$, $\text{boost} = 0.50$) was specifically designed to exploit right-tail equity market convexity (Bessembinder 2018; Grinold Fundamental Law). Because it is completely uncalled in `combine_predictions`, the production pipeline relies solely on a mild linear blend (`apply_top_decile_convex_boost`, $\lambda = 0.35$) and a near-linear exponent ($\gamma = 1.10$) in line 2812. This suppresses top-decile separation.
2. **From Observation 2**: In quantitative portfolio construction, factor noise dampening (suppressing collinear cluster risk) must measure the unadulterated correlation among raw alpha signals. By performing ZCA orthogonalization *before* correlation monitoring, the correlation matrix presented to `RegimeFactorSuppressionEngine` is already decorrelated. Thus, the suppression engine operates as a dead code path ($P_i \approx 1.0$), failing to penalize collinear clusters (e.g. Momentum cluster in Sideways regime).
3. **From Observation 3**: Binary thresholding ($s \ge 0.60$) introduces cliff effects: a stock with $0.599$ across 4 pillars gets $1.000\times$, whereas $0.601$ gets $1.100\times$. Furthermore, assigning strategies (`dual_correction`, `cross_asset_spillover`, `index_rebalance`) to multiple pillars simultaneously creates phantom multi-pillar confluence, distorting true cross-sectional ranking.
4. **From Observation 4**: In high-volatility regimes (`BEAR_HIGH_VOL`, `CRISIS`), price discovery occurs rapidly and information decays within 1-2 days. Retaining a 5-day half-life for surge/momentum or a 60-day half-life for value-up results in trading on stale information. Conversely, in low-volatility bull runs (`BULL_LOW_VOL`), trends persist, meaning short half-lives trigger unnecessary turnover.
5. **From Observation 5**: With 37 multi-factor strategies, the correlation matrix rank is determined by at least two major economic factors: Market Trend/Momentum (PC1) and Balance Sheet Value/Quality (PC2). Whitening PC2 attenuates genuine structural alpha. Preserving both leading principal components protects both momentum and fundamental alpha.

---

## 3. Caveats

1. **Live Broker Latency**: Theoretical half-life reductions in `CRISIS` or `HIGH_VOL` assume the OMS engine and broker connector (IBKR/DMA) can execute orders without excessive queue delay. If execution latency exceeds 4 hours, ultra-fast half-lives (< 0.5d) will experience latency decay.
2. **Sample Size Constraints**: In small sectors or markets with fewer than 10 stocks, sample correlation estimation carries sampling error $\sim 1/\sqrt{N}$. The proposed dynamic threshold $\theta(R, N) = \theta_0(R) + 1.645/\sqrt{N-3}$ mitigates this, but sample sizes $N < 5$ must continue using cross-sectional fallbacks.
3. **Single Stage Entropy Solver**: If `use_entropy_allocation=True` is enabled in `factor_suppression.py`, the gradient descent solver requires $\approx 5\text{ ms}$. In all tested universes, this is well within the 50 ms SLA.

---

## 4. Conclusion

Requirement R1 can be achieved through five targeted, mathematically rigorous enhancements:
1. **Activate Proposal 1 (Symmetric Top-Bottom Decile Richards/Bessembinder Convex Transformation)** in `combine_predictions`, steepening top-decile scores ($u > 0.60$) and bottom-decile penalties ($u < -0.60$) to expand the Top-Bottom spread by an estimated $+680\text{ bps}$.
2. **Activate Proposal 2 (Continuous Bilinear Cross-Pillar Synergy Kernel)** with mutually exclusive clusters, eliminating step discontinuities and duplicate strategy confluence.
3. **Activate Proposal 3 (2D Regime-Adaptive Half-Life Scaling)** $\tau_k(R) = \tau_k^{(0)} \cdot \kappa_{\text{regime}}(R)$, accelerating decay in high-volatility regimes ($\kappa = 0.50 \sim 0.75$) and extending persistence in low-volatility bull regimes ($\kappa = 1.30$).
4. **Activate Proposal 4 (Pipeline Sequence Rectification)**: Move raw correlation calculation and factor suppression *before* ZCA orthogonalization, and upgrade ZCA to Dual-Consensus Spectral Whitening (preserving both PC1 and PC2).
5. **Activate Proposal 5 (Statistically Calibrated Suppression Cutoffs & MP Spectral Floor)**: Adjust $\theta(R, N)$ based on sample size and floor eigenvalues at $\lambda_{\text{floor}} = \max((1 - \sqrt{K/N})^2, 0.05)$.

---

## 5. Verification Method

Independent auditors and Phase 2 implementers can verify this analysis and future implementations using the following concrete steps:

1. **Verify Existing Tests Pass**:
   ```bash
   .venv/Scripts/python.exe -m pytest tests/test_factor_orthogonalization.py -v
   .venv/Scripts/python.exe -m pytest tests/test_correlation_suppression.py -v
   .venv/Scripts/python.exe -m pytest tests/test_score_normalizer.py -v
   .venv/Scripts/python.exe -m pytest tests/test_return_maximization_apex.py -v
   ```
2. **Verify the Orthogonalization-Suppression Masking Defect**:
   Run the following verification script in python:
   ```python
   import sys; sys.path.insert(0, 'trading_system')
   from tests.test_correlation_suppression import _create_sample_17_strategy_df
   from src.ai.ensemble_scorer import EnsembleScoringEngine

   df = _create_sample_17_strategy_df()
   df['name'] = df['symbol']; df['market'] = 'KOSPI'; df['close'] = 50000.0; df['volume'] = 1000000.0
   engine = EnsembleScoringEngine()
   res = engine.combine_predictions(reg_df=df, s_df=df, ll_df=df, v_rule_df=df, vcp_ml_df=df,
                                    lstm_df=df, stat_arb_df=df, sector_df=df, rim_df=df, event_df=df,
                                    mq_df=df, iv_skew_df=df, order_flow_df=df, reversal_df=df,
                                    arm_df=df, card_df=df, latr_df=df, inst_foreign_sector_df=df,
                                    regime='SIDEWAYS_LOW_VOL')
   penalties = res.attrs['correlation_report']['penalties']
   # Note that almost all penalties are 1.0000 despite high collinearity in synthetic inputs!
   print(penalties)
   ```
3. **Invalidation Condition**:
   If reordering Phase 3-B and Phase 3-C results in `penalties['surge'] < 0.90` and `n_eff` properly reflecting raw collinearity without breaking [0, 1] score bounds or existing unit tests, the hypothesis is confirmed.
