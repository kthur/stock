# Handoff Report: Explorer M1-3 — Features F06, F07, F08 Implementation Blueprint
**Author**: Explorer M1-3 (`explorer_m1_3_opt3`)  
**Target Milestone**: Milestone 1 (Features F06, F07, F08)  
**Date**: 2026-09-04T06:05:00+09:00  
**Target Consumer**: Worker M1 / Orchestrator  
**Status**: Investigation Complete — Implementation Blueprint Ready  

---

## 1. Observation

### 1.1 F06: Bilinear Pillar Synergy & Bessembinder Tail Power-Law in `ensemble_scorer.py`
1. **Omitted Strategies in 4-Pillar Cluster Map (`ensemble_scorer.py:3539-3550`)**:
   ```python
   3539: clusters = {
   3540:     'val': ['rim_score', 'valueup_catalyst_score', 'accruals_quality_score', 'arm_score'],
   3541:     'mom': ['surge_score', 'vcp_ml_score', 'trend_efficiency_score', 'sector_score',
   3542:             'range_expansion_score', 'mq_score', 'll_score', 'vcp_rule_score'],
   3543:     'flow': ['order_flow_score', 'inst_foreign_sector_score', 'darkpool_score',
   3544:              'microstructure_score', 'overnight_gap_score', 'stat_arb_score'],
   3545:     'cat': ['event_score', 'sentiment_score', 'short_squeeze_score', 'gamma_squeeze_score',
   3546:             'supply_chain_score', 'supply_chain_gnn_score', 'cross_asset_spillover_score',
   3547:             'dual_correction_score', 'index_rebalance_score', 'insider_buying_score',
   3548:             'earnings_tone_drift_score']
   3549: }
   ```
   **Exact Defect**: Only 29 strategies are included in `clusters`. Exactly 8 strategies are omitted:
   - `regression` (`reg_score`)
   - `lstm` (`lstm_score`)
   - `iv_skew` (`iv_skew_score`)
   - `card_factor` (`card_score`)
   - `latr_factor` (`latr_score`)
   - `factor_neutralized` (`factor_neutralized_score`)
   - `vol_target` (`vol_target_score`)
   - `short_term_reversal` (`reversal_score`)
   These 8 strategies receive 0 synergy coupling, violating multi-factor confluence.

2. **Static Bessembinder Tail Power-Law Parameters (`ensemble_scorer.py:3608-3618`, `2722-2733`)**:
   In `apply_bessembinder_convex_power_law`:
   ```python
   3615: gamma_tail: float = 1.45,
   3616: beta_tail: float = 0.40,
   ```
   In `combine_predictions`:
   ```python
   2724: blended_score = pd.Series(
   2725:     self.apply_bessembinder_convex_power_law(
   2726:         scores=blended_score.values,
   2727:         symmetric=True,
   2728:         power_gamma=1.60,
   2729:         max_boost=0.50
   2730:     ),
   2731:     index=merged.index
   2732: )
   ```
   **Exact Defect**: `gamma_tail` and `beta_tail` are completely hardcoded/static. `regime` is not passed at line 2725. In trending regimes (`BULL_LOW_VOL`), top alpha spreads are under-amplified; in crisis regimes (`CRISIS`, `BEAR_HIGH_VOL`), extreme tails risk over-concentration.

---

### 1.2 F07: Single-Stage Entropy Redundancy Allocation in `factor_suppression.py` & `ensemble_scorer.py`
1. **Dormant Entropy Program in Pipeline (`ensemble_scorer.py:2420-2426`)**:
   In `combine_predictions`:
   ```python
   2420: suppressed_w = self.factor_suppression.suppress_weights(
   2421:     base_weights=base_w,
   2422:     corr_matrix=corr_df,
   2423:     regime_label=str(regime),
   2424:     tuned_params=tuned_p,
   2425:     n_samples=n_cross_section
   2426: )
   ```
   **Exact Defect**: `use_entropy_allocation` is never passed, so it defaults to `False` (`factor_suppression.py:292`).
2. **Fragility to Missing Strategies (`factor_suppression.py:320-322`)**:
   In `suppress_weights`:
   ```python
   320: strats = [s for s in base_weights.keys() if s in corr_matrix.columns]
   321: missing_strats = [s for s in base_weights.keys() if s not in corr_matrix.columns]
   322: if len(strats) >= 2 and not missing_strats:
   ```
   **Exact Defect**: `StrategyCorrelationMonitor` tracks strategies 1–31, while `base_weights` contains 37 strategies. Therefore, `missing_strats` is non-empty (`len(missing_strats) == 6`), which causes `not missing_strats` to evaluate to `False`! The solver is skipped completely even when `use_entropy_allocation=True` is requested.

---

### 1.3 F08: Factor Orthogonalizer Singularity Protection in `factor_orthogonalizer.py`
1. **Zero-Variance Columns in `_pca_zca_symmetric` (`factor_orthogonalizer.py:241-246, 298-305`)**:
   ```python
   243: X_bar = (X - means) / stds
   246: C = np.dot(X_bar.T, X_bar) / max(N - 1, 1)
   ...
   305: X_decorr = np.dot(X_bar, C_inv_sqrt)
   308: X_ortho = means + X_decorr * stds
   ```
   When missing strategies are imputed via median (`orthogonalize:80-95`), constant columns (e.g. all 0.50) have `std = 0`. Line 101 clamps `stds` to `1e-6`, resulting in `X_bar[:, j] = 0.0`. Consequently, `C[j, j] = 0.0`, violating the unit-diagonal correlation matrix property.
   During decorrelation, cross-terms in $C^{-1/2}$ bleed other active features into the constant column:
   $X_{\text{decorr}}[i, j] = \sum_{k \neq j} X_{\text{bar}}[i, k] C^{-1/2}[k, j] \neq 0$.
   This injects artificial cross-feature noise into previously constant columns and corrupts the eigenvalue spectrum.

---

## 2. Logic Chain

### Logic Chain 1: Canonical 37-Strategy 4-Pillar Disjoint Partition (F06)
- *Premise*: Every strategy must belong to exactly one pillar so that intra-pillar redundancy does not trigger cross-pillar synergy, while multi-pillar confluence receives up to a 10% multiplier ($\Xi \in [1.00, 1.10]$).
- *Deduction*:
  * **Valuation (6)**: `rim_valuation` (`rim_score`), `valueup_catalyst` (`valueup_catalyst_score`), `accruals_quality` (`accruals_quality_score`), `arm_factor` (`arm_score`), plus omitted: `factor_neutralized` (`factor_neutralized_score`), `regression` (`reg_score`).
  * **Momentum (9)**: `surge` (`surge_score`), `vcp_ml` (`vcp_ml_score`), `trend_efficiency` (`trend_efficiency_score`), `sector_rotation` (`sector_score`), `range_expansion_breakout` (`range_expansion_score`), `mq_factor` (`mq_score`), `lead_lag` (`ll_score`), `vcp_rule` (`vcp_rule_score`), plus omitted: `lstm` (`lstm_score`).
  * **Flow (9)**: `order_flow` (`order_flow_score`), `inst_foreign_sector` (`inst_foreign_sector_score`), `darkpool` (`darkpool_score`), `microstructure` (`microstructure_score`), `overnight_gap_reversal` (`overnight_gap_score`), `stat_arb` (`stat_arb_score`), plus omitted: `iv_skew` (`iv_skew_score`), `short_term_reversal` (`reversal_score`), `vol_target` (`vol_target_score`).
  * **Catalyst (13)**: `event_driven` (`event_score`), `sentiment` (`sentiment_score`), `short_squeeze` (`short_squeeze_score`), `gamma_squeeze` (`gamma_squeeze_score`), `supply_chain` (`supply_chain_score`), `supply_chain_gnn` (`supply_chain_gnn_score`), `cross_asset_spillover` (`cross_asset_spillover_score`), `dual_correction` (`dual_correction_score`), `index_rebalance` (`index_rebalance_score`), `insider_buying` (`insider_buying_score`), `earnings_tone_drift` (`earnings_tone_drift_score`), plus omitted: `card_factor` (`card_score`), `latr_factor` (`latr_score`).
  * Total: $6 + 9 + 9 + 13 = 37$. Disjoint and collectively exhaustive.

### Logic Chain 2: Regime-Adaptive Bessembinder S-Curve (F06)
- *Premise*: Bessembinder power law modifies normalized conviction $u_i = 2(s_i - 0.50) \in [-1, 1]$:
  $$\tilde{u}_i = \text{sgn}(u_i) |u_i|^{\gamma_{\text{tail}}(R)} \left[ 1 + \beta_{\text{tail}}(R) \left( \frac{\max(0, |u_i| - u_{\text{thresh}})}{1 - u_{\text{thresh}}} \right)^{\eta} \right]$$
- *Deduction*:
  * In calm trending regimes (`BULL_LOW_VOL`): Signal-to-noise ratio is high. Increase $\gamma_{\text{tail}} = 1.70, \beta_{\text{tail}} = 0.50$ to concentrate weights onto top-decile winners and suppress near-neutral noise ($S=0.55 \rightarrow 0.5066$).
  * In turbulent/crisis regimes (`CRISIS`, `BEAR_HIGH_VOL`): High volatility induces false breakouts. Set $\gamma_{\text{tail}} = 1.20, \beta_{\text{tail}} = 0.20$ to dampen tail concentration and maintain diversification.
  * When `regime is None`: Preserve default $\gamma_{\text{tail}} = 1.45, \beta_{\text{tail}} = 0.40$ for 100% backward compatibility.

### Logic Chain 3: Single-Stage Entropy Allocation with Partial Missingness (F07)
- *Premise*: Solving $\min_{\mathbf{w}} \frac{1}{2} \mathbf{w}^T \mathbf{R} \mathbf{w} - \tau \sum \ln(w_i) + \gamma \|\mathbf{w} - \mathbf{w}_0\|^2$ penalizes collinear factor clusters while maintaining diversification ($w_i \ge 0.005$).
- *Deduction*:
  * In `ensemble_scorer.py`: Set `use_entropy_allocation=(n_cross_section >= 10)` in `combine_predictions`.
  * In `factor_suppression.py`: If some strategies are missing from $\mathbf{R}$ (`len(missing_strats) > 0`), solve the entropy program on available strategies $\mathcal{S}_{\text{present}}$, then scale available weights by $P_{\text{present}} = \sum_{j \in \mathcal{S}_{\text{present}}} w_{0, j}$ and missing strategies by $P_{\text{missing}} = \sum_{k \in \mathcal{S}_{\text{missing}}} w_{0, k}$. This prevents fallback to heuristic damping.

### Logic Chain 4: Active-Subspace Isolation for PCA-ZCA Whitening (F08)
- *Premise*: Zero-variance columns cannot be standardized ($0/0$) and create singular eigenvalues that distort the full ZCA matrix $C^{-1/2}$.
- *Deduction*:
  * Before computing covariance, identify singular columns: `is_singular = (std < 1e-8) | (~np.isfinite(std))`.
  * If singular columns exist, isolate the active submatrix $X[:, \text{active}]$, run `_pca_zca_symmetric` on active columns only, and assign constant values directly to singular columns without cross-contamination: $X_{\text{ortho}}[:, \text{singular}] = X[:, \text{singular}]$.

---

## 3. Exact Code Replacement Blocks for Worker

### File 1: `trading_system/src/ai/ensemble_scorer.py`

#### Edit 1.1: Expand 4-Pillar Cluster Map to All 37 Strategies
**Target Lines**: 3538–3550  
**Replace**:
```python
<<<<
        # Define 4 mutually exclusive strategy clusters
        clusters = {
            'val': ['rim_score', 'valueup_catalyst_score', 'accruals_quality_score', 'arm_score'],
            'mom': ['surge_score', 'vcp_ml_score', 'trend_efficiency_score', 'sector_score',
                    'range_expansion_score', 'mq_score', 'll_score', 'vcp_rule_score'],
            'flow': ['order_flow_score', 'inst_foreign_sector_score', 'darkpool_score',
                     'microstructure_score', 'overnight_gap_score', 'stat_arb_score'],
            'cat': ['event_score', 'sentiment_score', 'short_squeeze_score', 'gamma_squeeze_score',
                    'supply_chain_score', 'supply_chain_gnn_score', 'cross_asset_spillover_score',
                    'dual_correction_score', 'index_rebalance_score', 'insider_buying_score',
                    'earnings_tone_drift_score']
        }
====
        # Define 4 mutually exclusive strategy clusters (all 37 strategies covered without omission)
        clusters = {
            'val': [
                'rim_score', 'valueup_catalyst_score', 'accruals_quality_score', 'arm_score',
                'factor_neutralized_score', 'reg_score'
            ],
            'mom': [
                'surge_score', 'vcp_ml_score', 'trend_efficiency_score', 'sector_score',
                'range_expansion_score', 'mq_score', 'll_score', 'vcp_rule_score',
                'lstm_score'
            ],
            'flow': [
                'order_flow_score', 'inst_foreign_sector_score', 'darkpool_score',
                'microstructure_score', 'overnight_gap_score', 'stat_arb_score',
                'iv_skew_score', 'reversal_score', 'vol_target_score'
            ],
            'cat': [
                'event_score', 'sentiment_score', 'short_squeeze_score', 'gamma_squeeze_score',
                'supply_chain_score', 'supply_chain_gnn_score', 'cross_asset_spillover_score',
                'dual_correction_score', 'index_rebalance_score', 'insider_buying_score',
                'earnings_tone_drift_score', 'card_score', 'latr_score'
            ]
        }
>>>>
```

#### Edit 1.2: Add `get_regime_adaptive_bessembinder_params` and Update `apply_bessembinder_convex_power_law`
**Target Lines**: 3607–3635  
**Replace**:
```python
<<<<
    @staticmethod
    def apply_bessembinder_convex_power_law(
        scores: Union[pd.Series, np.ndarray, List[float]],
        top_percentile: float = 90.0,
        power_gamma: float = 1.60,
        max_boost: float = 0.50,
        symmetric: bool = False,
        u_thresh: float = 0.60,
        gamma_tail: float = 1.45,
        beta_tail: float = 0.40,
        eta: float = 1.60
    ) -> np.ndarray:
        """
        Applies Bessembinder Right-Tail or Symmetric Richards Power-Law Convex Scaling:
        - When symmetric=False:
            s_tilde_i = s_i * [ 1 + max_boost * ((s_i - P90) / (P99 - P90))^gamma ] for s_i > P90
        - When symmetric=True:
            Applies Generalized Symmetric Richards / Bessembinder Power-Law S-Curve:
            u_i = 2 * (s_i - 0.50) in [-1.0, 1.0]
            excess_i = max(0, (|u_i| - u_thresh) / (1 - u_thresh))
            u_tilde_i = sgn(u_i) * |u_i|^gamma_tail * [ 1 + beta_tail * excess_i^eta ]
            s_tilde_i = 0.50 + 0.50 * (u_tilde_i / scale)
        Concentrates risk budget onto top-decile consensus winners while simultaneously
        steepening bottom-decile penalties without rank inversion (rho_s = 1.0000).
        """
        arr = np.nan_to_num(np.asarray(scores, dtype=np.float64), nan=0.0)
        if len(arr) < 5:
            return arr
====
    @staticmethod
    def get_regime_adaptive_bessembinder_params(
        regime: Optional[Union[str, int]] = None,
        default_gamma: float = 1.45,
        default_beta: float = 0.40
    ) -> Tuple[float, float]:
        """
        Returns regime-adaptive (gamma_tail, beta_tail) for Bessembinder convex power-law:
        - BULL_LOW_VOL: (1.70, 0.50)  - High persistence, steep tail spread expansion
        - BULL_HIGH_VOL: (1.55, 0.45) - Strong trend with moderate tail boost
        - SIDEWAYS_LOW_VOL: (1.45, 0.40) - Balanced baseline
        - SIDEWAYS_HIGH_VOL: (1.35, 0.30) - Choppy, compressed tail
        - BEAR_LOW_VOL: (1.30, 0.30) - Defensives, moderate tail dampening
        - BEAR_HIGH_VOL: (1.20, 0.20) - Panic selloff, conservative tail bounds
        - CRISIS: (1.20, 0.20) - Extreme tail protection, prevents over-concentration
        """
        if regime is None:
            return default_gamma, default_beta
        reg_str = str(regime).upper()
        if 'CRISIS' in reg_str:
            return 1.20, 0.20
        elif 'BEAR_HIGH_VOL' in reg_str or ('BEAR' in reg_str and 'HIGH_VOL' in reg_str):
            return 1.20, 0.20
        elif 'BEAR_LOW_VOL' in reg_str or reg_str == '0' or reg_str == 'BEAR':
            return 1.30, 0.30
        elif 'SIDEWAYS_HIGH_VOL' in reg_str:
            return 1.35, 0.30
        elif 'SIDEWAYS_LOW_VOL' in reg_str or reg_str == '1' or reg_str == 'SIDEWAYS':
            return 1.45, 0.40
        elif 'BULL_HIGH_VOL' in reg_str:
            return 1.55, 0.45
        elif 'BULL_LOW_VOL' in reg_str or reg_str == '2' or reg_str == 'BULL':
            return 1.70, 0.50
        else:
            return default_gamma, default_beta

    @classmethod
    def apply_bessembinder_convex_power_law(
        cls,
        scores: Union[pd.Series, np.ndarray, List[float]],
        top_percentile: float = 90.0,
        power_gamma: float = 1.60,
        max_boost: float = 0.50,
        symmetric: bool = False,
        u_thresh: float = 0.60,
        gamma_tail: Optional[float] = None,
        beta_tail: Optional[float] = None,
        eta: float = 1.60,
        regime: Optional[Union[str, int]] = None
    ) -> np.ndarray:
        """
        Applies Bessembinder Right-Tail or Symmetric Richards Power-Law Convex Scaling:
        - When symmetric=False:
            s_tilde_i = s_i * [ 1 + max_boost * ((s_i - P90) / (P99 - P90))^gamma ] for s_i > P90
        - When symmetric=True:
            Applies Generalized Symmetric Richards / Bessembinder Power-Law S-Curve:
            u_i = 2 * (s_i - 0.50) in [-1.0, 1.0]
            excess_i = max(0, (|u_i| - u_thresh) / (1 - u_thresh))
            u_tilde_i = sgn(u_i) * |u_i|^gamma_tail * [ 1 + beta_tail * excess_i^eta ]
            s_tilde_i = 0.50 + 0.50 * (u_tilde_i / scale)
        Concentrates risk budget onto top-decile consensus winners while simultaneously
        steepening bottom-decile penalties without rank inversion (rho_s = 1.0000).
        """
        arr = np.nan_to_num(np.asarray(scores, dtype=np.float64), nan=0.0)
        if len(arr) < 5:
            return arr

        eff_gamma = gamma_tail
        eff_beta = beta_tail
        if regime is not None:
            adapt_gamma, adapt_beta = cls.get_regime_adaptive_bessembinder_params(regime)
            if eff_gamma is None:
                eff_gamma = adapt_gamma
            if eff_beta is None:
                eff_beta = adapt_beta
        if eff_gamma is None:
            eff_gamma = 1.45
        if eff_beta is None:
            eff_beta = 0.40
>>>>
```
*(Note: inside `apply_bessembinder_convex_power_law`, replace `gamma_tail` and `beta_tail` with `eff_gamma` and `eff_beta` in lines 3653–3657).*

#### Edit 1.3: Pass `use_entropy_allocation=(n_cross_section >= 10)` in `combine_predictions`
**Target Lines**: 2417–2427  
**Replace**:
```python
<<<<
                # 4. Regime factor noise suppression with sample-size calibration
                tuned_p = getattr(self, '_tuned_params', None)
                base_w = weights if weights else self.get_base_weights(regime)
                suppressed_w = self.factor_suppression.suppress_weights(
                    base_weights=base_w,
                    corr_matrix=corr_df,
                    regime_label=str(regime),
                    tuned_params=tuned_p,
                    n_samples=n_cross_section
                )
====
                # 4. Regime factor noise suppression with sample-size calibration & single-stage entropy program
                tuned_p = getattr(self, '_tuned_params', None)
                base_w = weights if weights else self.get_base_weights(regime)
                suppressed_w = self.factor_suppression.suppress_weights(
                    base_weights=base_w,
                    corr_matrix=corr_df,
                    regime_label=str(regime),
                    tuned_params=tuned_p,
                    use_entropy_allocation=(n_cross_section >= 10),
                    vif_dict=vif_dict,
                    n_samples=n_cross_section
                )
>>>>
```

#### Edit 1.4: Pass `regime=regime` to `apply_bessembinder_convex_power_law`
**Target Lines**: 2722–2733  
**Replace**:
```python
<<<<
        # Phase 2-E: Bessembinder Symmetric Tail Convex Scaling (Top/Bottom Decile Tilt)
        if len(merged) >= 5:
            blended_score = pd.Series(
                self.apply_bessembinder_convex_power_law(
                    scores=blended_score.values,
                    symmetric=True,
                    power_gamma=1.60,
                    max_boost=0.50
                ),
                index=merged.index
            )
====
        # Phase 2-E: Bessembinder Symmetric Tail Convex Scaling (Top/Bottom Decile Tilt with 2D Regime Adaptation)
        if len(merged) >= 5:
            blended_score = pd.Series(
                self.apply_bessembinder_convex_power_law(
                    scores=blended_score.values,
                    symmetric=True,
                    power_gamma=1.60,
                    max_boost=0.50,
                    regime=regime
                ),
                index=merged.index
            )
>>>>
```

---

### File 2: `trading_system/src/ai/factor_suppression.py`

#### Edit 2.1: Robust Single-Stage Entropy Allocation with Partial Missingness Support
**Target Lines**: 284–348  
**Replace**:
```python
<<<<
    def suppress_weights(
        self,
        base_weights: Dict[str, float],
        corr_matrix: pd.DataFrame,
        regime_label: str,
        theta: Optional[float] = None,
        lambda_penalty: Optional[float] = None,
        tuned_params: Optional[Dict[str, Any]] = None,
        use_entropy_allocation: bool = False,
        vif_dict: Optional[Dict[str, float]] = None,
        consensus_precision: Optional[Dict[str, float]] = None,
        cluster_sharpes: Optional[Dict[str, float]] = None,
        n_samples: Optional[int] = None,
    ) -> Dict[str, float]:
        """
        Applies regime-specific correlation factor noise dampening penalties to base strategy weights.
        Returns renormalized suppressed strategy weight dictionary.
        """
        if not base_weights:
            return {}

        if corr_matrix is None or corr_matrix.empty:
            tot = sum(base_weights.values())
            return {k: v / tot for k, v in base_weights.items()} if tot > 0 else {}

        eff_n = n_samples
        if eff_n is None and hasattr(corr_matrix, 'attrs') and 'n_samples' in corr_matrix.attrs:
            eff_n = corr_matrix.attrs.get('n_samples')

        # Determine theta and lambda
        default_t, default_l = self._get_regime_params(regime_label, tuned_params=tuned_params, n_samples=eff_n)
        eff_theta = theta if theta is not None else default_t
        eff_lambda = lambda_penalty if lambda_penalty is not None else default_l

        if use_entropy_allocation:
            try:
                strats = [s for s in base_weights.keys() if s in corr_matrix.columns]
                missing_strats = [s for s in base_weights.keys() if s not in corr_matrix.columns]
                if len(strats) >= 2 and not missing_strats:
                    penalties = self.compute_penalties(
                        corr_matrix=corr_matrix,
                        regime_label=regime_label,
                        theta=eff_theta,
                        lambda_penalty=eff_lambda,
                        consensus_precision=consensus_precision,
                        vif_dict=vif_dict,
                        cluster_sharpes=cluster_sharpes,
                        n_samples=eff_n,
                    )
                    w0_vec = np.array([float(base_weights[s] * penalties.get(s, 1.0)) for s in strats], dtype=np.float64)
                    w0_sum = float(np.sum(w0_vec))
                    w0_vec = w0_vec / max(w0_sum, 1e-8)
                    R_sub = corr_matrix.loc[strats, strats].to_numpy(dtype=np.float64)

                    opt_w = solve_single_stage_entropy_allocation(
                        R=R_sub,
                        w0=w0_vec,
                        tau_entropy=0.05,
                        gamma_anchor=1.0 / max(0.1, eff_lambda),
                        w_min=0.005
                    )
                    return {s: float(w) for s, w in zip(strats, opt_w)}
            except Exception as _ent_e:
                logger.debug(f"[ENTROPY ALLOCATION] Fallback to standard penalty model: {_ent_e}")
====
    def suppress_weights(
        self,
        base_weights: Dict[str, float],
        corr_matrix: pd.DataFrame,
        regime_label: str,
        theta: Optional[float] = None,
        lambda_penalty: Optional[float] = None,
        tuned_params: Optional[Dict[str, Any]] = None,
        use_entropy_allocation: Optional[bool] = None,
        vif_dict: Optional[Dict[str, float]] = None,
        consensus_precision: Optional[Dict[str, float]] = None,
        cluster_sharpes: Optional[Dict[str, float]] = None,
        n_samples: Optional[int] = None,
    ) -> Dict[str, float]:
        """
        Applies regime-specific correlation factor noise dampening penalties to base strategy weights.
        Returns renormalized suppressed strategy weight dictionary.
        """
        if not base_weights:
            return {}

        if corr_matrix is None or corr_matrix.empty:
            tot = sum(base_weights.values())
            return {k: v / tot for k, v in base_weights.items()} if tot > 0 else {}

        eff_n = n_samples
        if eff_n is None and hasattr(corr_matrix, 'attrs') and 'n_samples' in corr_matrix.attrs:
            eff_n = corr_matrix.attrs.get('n_samples')

        # Determine theta and lambda
        default_t, default_l = self._get_regime_params(regime_label, tuned_params=tuned_params, n_samples=eff_n)
        eff_theta = theta if theta is not None else default_t
        eff_lambda = lambda_penalty if lambda_penalty is not None else default_l

        # Enable entropy allocation if explicitly True, or auto-enable when N >= 10 and not explicitly False
        eff_use_entropy = use_entropy_allocation
        if eff_use_entropy is None:
            eff_use_entropy = (eff_n is not None and np.isfinite(eff_n) and eff_n >= 10)

        if eff_use_entropy:
            try:
                strats = [s for s in base_weights.keys() if s in corr_matrix.columns]
                missing_strats = [s for s in base_weights.keys() if s not in corr_matrix.columns]
                if len(strats) >= 2:
                    penalties = self.compute_penalties(
                        corr_matrix=corr_matrix,
                        regime_label=regime_label,
                        theta=eff_theta,
                        lambda_penalty=eff_lambda,
                        consensus_precision=consensus_precision,
                        vif_dict=vif_dict,
                        cluster_sharpes=cluster_sharpes,
                        n_samples=eff_n,
                    )
                    w0_vec = np.array([float(base_weights[s] * penalties.get(s, 1.0)) for s in strats], dtype=np.float64)
                    w0_sum = float(np.sum(w0_vec))
                    w0_vec = w0_vec / max(w0_sum, 1e-8)
                    R_sub = corr_matrix.loc[strats, strats].to_numpy(dtype=np.float64)

                    opt_w = solve_single_stage_entropy_allocation(
                        R=R_sub,
                        w0=w0_vec,
                        tau_entropy=0.05,
                        gamma_anchor=1.0 / max(0.1, eff_lambda),
                        w_min=0.005
                    )
                    if not missing_strats:
                        return {s: float(w) for s, w in zip(strats, opt_w)}
                    else:
                        # Proportionately combine active entropy-optimized weights with missing strategies
                        sum_present_base = sum(base_weights[s] for s in strats)
                        sum_missing_base = sum(base_weights[s] for s in missing_strats)
                        total_base = sum_present_base + sum_missing_base
                        p_share = sum_present_base / total_base if total_base > 0 else 1.0
                        m_share = sum_missing_base / total_base if total_base > 0 else 0.0

                        res = {}
                        for s, w in zip(strats, opt_w):
                            res[s] = float(w * p_share)
                        for s in missing_strats:
                            m_w = base_weights[s] * penalties.get(s, 1.0)
                            res[s] = float((m_w / max(sum_missing_base, 1e-8)) * m_share)

                        tot_res = sum(res.values())
                        return {k: float(v / tot_res) for k, v in res.items()} if tot_res > 0 else res
            except Exception as _ent_e:
                logger.debug(f"[ENTROPY ALLOCATION] Fallback to standard penalty model: {_ent_e}")
>>>>
```

---

### File 3: `trading_system/src/ai/factor_orthogonalizer.py`

#### Edit 3.1: Guard `_pca_zca_symmetric` against Zero-Variance Singular Columns
**Target Lines**: 232–246  
**Replace**:
```python
<<<<
    @safe_matrix_precision_guard
    def _pca_zca_symmetric(
        self,
        X: np.ndarray,
        means: np.ndarray,
        stds: np.ndarray,
        preserve_pc1: bool = False,
        preserve_top_k: int = 0
    ) -> np.ndarray:
        N, K = X.shape
        # Standardize matrix to zero mean, unit variance
        X_bar = (X - means) / stds

        # Compute sample covariance matrix
        C = np.dot(X_bar.T, X_bar) / max(N - 1, 1)
====
    @safe_matrix_precision_guard
    def _pca_zca_symmetric(
        self,
        X: np.ndarray,
        means: np.ndarray,
        stds: np.ndarray,
        preserve_pc1: bool = False,
        preserve_top_k: int = 0
    ) -> np.ndarray:
        N, K = X.shape
        if K <= 1 or N < 2:
            return np.copy(X)

        # Detect zero-variance / singular columns (e.g. constant columns from missingness/imputation)
        raw_stds = np.std(X, axis=0)
        is_singular = (raw_stds < 1e-8) | (stds < 1e-8) | (~np.isfinite(raw_stds)) | (~np.isfinite(stds))

        # If all columns are singular, return untouched
        if np.all(is_singular):
            return np.copy(X)

        # If any columns are singular, isolate non-singular active columns for ZCA whitening
        if np.any(is_singular):
            active_idx = np.where(~is_singular)[0]
            singular_idx = np.where(is_singular)[0]

            X_ortho = np.copy(X)
            if len(active_idx) > 1:
                eff_top = min(preserve_top_k, len(active_idx) - 1) if preserve_top_k > 0 else 0
                X_active_ortho = self._pca_zca_symmetric(
                    X[:, active_idx],
                    means[active_idx],
                    stds[active_idx],
                    preserve_pc1=preserve_pc1 if eff_top > 0 or preserve_pc1 else False,
                    preserve_top_k=eff_top
                )
                X_ortho[:, active_idx] = X_active_ortho
            else:
                X_ortho[:, active_idx] = X[:, active_idx]

            # Preserve singular/constant columns untouched without noise bleed
            for s_col in singular_idx:
                X_ortho[:, s_col] = X[:, s_col]

            return np.asarray(X_ortho, dtype=np.float64)

        # Standardize matrix to zero mean, unit variance
        X_bar = (X - means) / stds

        # Compute sample covariance matrix
        C = np.dot(X_bar.T, X_bar) / max(N - 1, 1)
>>>>
```

---

## 4. Unit Test Suite Specification for Worker

Write dedicated test class `TestM1QuantEnhancementsF06F07F08` in `tests/test_m1_quant_enhancements.py` or dedicated file:

```python
import numpy as np
import pandas as pd
import pytest
from trading_system.src.ai.ensemble_scorer import EnsembleScoringEngine
from trading_system.src.ai.factor_suppression import RegimeFactorSuppressionEngine, solve_single_stage_entropy_allocation
from trading_system.src.ai.factor_orthogonalizer import FactorOrthogonalizerEngine

class TestM1QuantEnhancementsF06F07F08:
    """Unit tests for Features F06, F07, and F08."""

    # -------------------------------------------------------------------------
    # F06: 37-Strategy 4-Pillar Synergy & Regime-Adaptive Bessembinder
    # -------------------------------------------------------------------------
    def test_f06_all_37_strategies_partition_and_isolation(self):
        """Verify all 37 strategies are partitioned across 4 pillars with 0 overlaps and intra-pillar isolation."""
        clusters = {
            'val': ['rim_score', 'valueup_catalyst_score', 'accruals_quality_score', 'arm_score', 'factor_neutralized_score', 'reg_score'],
            'mom': ['surge_score', 'vcp_ml_score', 'trend_efficiency_score', 'sector_score', 'range_expansion_score', 'mq_score', 'll_score', 'vcp_rule_score', 'lstm_score'],
            'flow': ['order_flow_score', 'inst_foreign_sector_score', 'darkpool_score', 'microstructure_score', 'overnight_gap_score', 'stat_arb_score', 'iv_skew_score', 'reversal_score', 'vol_target_score'],
            'cat': ['event_score', 'sentiment_score', 'short_squeeze_score', 'gamma_squeeze_score', 'supply_chain_score', 'supply_chain_gnn_score', 'cross_asset_spillover_score', 'dual_correction_score', 'index_rebalance_score', 'insider_buying_score', 'earnings_tone_drift_score', 'card_score', 'latr_score']
        }
        all_cols = []
        for p, cols in clusters.items():
            all_cols.extend(cols)
        assert len(all_cols) == 37
        assert len(set(all_cols)) == 37  # Disjoint

        # Intra-pillar isolation on Valuation (including regression and factor_neutralized)
        df_val = pd.DataFrame({c: [0.95] * 5 for c in clusters['val']})
        mult = EnsembleScoringEngine.compute_bilinear_cross_pillar_synergy(df_val, regime='BULL_LOW_VOL')
        np.testing.assert_allclose(mult.values, 1.000, atol=1e-5)

        # Cross-pillar synergy with previously omitted strategies (reg_score in val x lstm_score in mom)
        df_cross = pd.DataFrame({
            'reg_score': [0.90] * 5,
            'lstm_score': [0.90] * 5,
        })
        mult_cross = EnsembleScoringEngine.compute_bilinear_cross_pillar_synergy(df_cross, regime='BULL_LOW_VOL')
        assert np.all(mult_cross > 1.01), f"Expected cross synergy, got {mult_cross.iloc[0]}"

    def test_f06_regime_adaptive_bessembinder_parameters(self):
        """Verify regime-adaptive gamma and beta scaling."""
        g_bull, b_bull = EnsembleScoringEngine.get_regime_adaptive_bessembinder_params('BULL_LOW_VOL')
        g_crisis, b_crisis = EnsembleScoringEngine.get_regime_adaptive_bessembinder_params('CRISIS')
        g_def, b_def = EnsembleScoringEngine.get_regime_adaptive_bessembinder_params(None)

        assert g_bull == 1.70 and b_bull == 0.50
        assert g_crisis == 1.20 and b_crisis == 0.20
        assert g_def == 1.45 and b_def == 0.40

        scores = np.array([0.05, 0.50, 0.55, 0.95, 1.00])
        out_bull = EnsembleScoringEngine.apply_bessembinder_convex_power_law(scores, symmetric=True, regime='BULL_LOW_VOL')
        out_crisis = EnsembleScoringEngine.apply_bessembinder_convex_power_law(scores, symmetric=True, regime='CRISIS')

        # Bull compresses center noise (0.55) closer to 0.50 than Crisis
        assert abs(out_bull[2] - 0.50) < abs(out_crisis[2] - 0.50)
        # Monotonicity preserved in both
        assert np.all(np.diff(out_bull) > 0)
        assert np.all(np.diff(out_crisis) > 0)

    # -------------------------------------------------------------------------
    # F07: Single-Stage Entropy Redundancy Allocation
    # -------------------------------------------------------------------------
    def test_f07_entropy_allocation_active_for_large_n_and_missingness(self):
        """Verify entropy allocation runs when N >= 10 and handles partial missingness gracefully."""
        engine = RegimeFactorSuppressionEngine()
        corr_matrix = pd.DataFrame(
            [[1.0, 0.85, 0.1], [0.85, 1.0, 0.1], [0.1, 0.1, 1.0]],
            index=['s1', 's2', 's3'],
            columns=['s1', 's2', 's3']
        )
        base_w = {'s1': 0.25, 's2': 0.25, 's3': 0.25, 's_missing': 0.25}

        # With N=50 (N >= 10), entropy allocation activates
        suppressed = engine.suppress_weights(
            base_weights=base_w,
            corr_matrix=corr_matrix,
            regime_label='SIDEWAYS_LOW_VOL',
            n_samples=50
        )
        assert abs(sum(suppressed.values()) - 1.0) < 1e-5
        # s1 and s2 are collinear (0.85), s3 is independent (0.1)
        assert suppressed['s1'] < suppressed['s3']
        assert suppressed['s2'] < suppressed['s3']
        assert 's_missing' in suppressed and suppressed['s_missing'] > 0.0

    # -------------------------------------------------------------------------
    # F08: Factor Orthogonalizer Singularity Protection
    # -------------------------------------------------------------------------
    def test_f08_orthogonalizer_protects_zero_variance_singular_columns(self):
        """Verify orthogonalizer does not crash or corrupt constant columns under median imputation."""
        ortho = FactorOrthogonalizerEngine()
        N = 50
        df = pd.DataFrame({
            'reg_score': np.linspace(0.1, 0.9, N),
            'surge_score': np.linspace(0.2, 0.8, N),
            'const_imputed': [0.50] * N,  # 0 variance
            'all_zero': [0.0] * N         # 0 variance
        })
        cols = ['reg_score', 'surge_score', 'const_imputed', 'all_zero']
        res = ortho.orthogonalize(df, cols, method='pca_symmetric')

        # Check that constant columns are preserved without noise bleed
        np.testing.assert_allclose(res['const_imputed'].values, 0.50, atol=1e-5)
        np.testing.assert_allclose(res['all_zero'].values, 0.00, atol=1e-5)
        # Check that active columns are valid and within [0, 1]
        assert res['reg_score'].between(0.0, 1.0).all()
        assert res['surge_score'].between(0.0, 1.0).all()
        assert not res.isna().any().any()
```

---

## 5. Caveats & Assumptions

1. **Strategy Correlation Monitor Strategy Set**:
   - `StrategyCorrelationMonitor` tracks 31 strategies by default (`ALL_31_STRATEGIES`). Our partial-missingness proportional scaling in `suppress_weights` ensures that 37-strategy base weights are safely combined even when only 31 are monitored in the correlation matrix.
2. **Backward Compatibility**:
   - When `regime=None` is passed to `apply_bessembinder_convex_power_law`, parameters remain $\gamma_{\text{tail}}=1.45, \beta_{\text{tail}}=0.40$, ensuring all existing tests (e.g. `test_feature_3_bessembinder_symmetric_properties`) continue to pass without deviation.
3. **Computational Overhead**:
   - The single-stage entropy program runs 150 gradient iterations on a 37x37 matrix, taking $\approx 2.5\text{ms}$ in pure NumPy. This adds negligible overhead to `combine_predictions`.

---

## 6. Verification Method

### Test Execution Commands:
```powershell
# 1. Verify existing baseline suite (45/45 pass)
.venv\Scripts\pytest.exe tests/test_regime_ensemble.py tests/test_factor_orthogonalization.py tests/test_correlation_suppression.py tests/test_factor_momentum_and_available_normalization.py tests/test_r1_ensemble_regime_fixes.py tests/test_m1_quant_enhancements.py -v

# 2. Verify adversarial stress tests
.venv\Scripts\pytest.exe tests/test_adversarial_m1_2_empirical_stress.py tests/test_adversarial_ensemble_scorer_challenger.py -v

# 3. Verify new M1 test suite
.venv\Scripts\pytest.exe tests/test_m1_quant_enhancements.py -k "f06 or f07 or f08 or feature" -v
```

### Invalidation Conditions:
1. If $\sum w_i \neq 1.0000 \pm 1e-5$ in `suppress_weights`.
2. If any constant column in `orthogonalize` picks up non-zero variance $> 1e-5$.
3. If intra-pillar conviction produces $\Xi > 1.0001$ for any of the 4 clusters.
4. If any existing unit test in the 45-test baseline fails.
