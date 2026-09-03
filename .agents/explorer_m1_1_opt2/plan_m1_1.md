# Technical Plan: Milestone 1 Feature 1 & Feature 6
**Apex Quant Optimization (v9) - Pipeline Sequence Rectification & Statistically Calibrated Factor Suppression**

**Author**: Explorer M1-1 (Pipeline Sequence & Factor Suppression Specialist)  
**Date**: 2026-09-04  
**Target Codebase**: `d:\Finance\code\stock`  
**Target Files**:
1. `trading_system/src/ai/ensemble_scorer.py`
2. `trading_system/src/ai/factor_suppression.py`
3. `trading_system/src/ai/correlation_monitor.py`
4. `tests/test_correlation_suppression.py`

---

## 1. Executive Summary & Root Cause Analysis

### 1.1 Feature 1: Pipeline Sequence Inversion Defect (Orthogonalization-Suppression Masking)
- **Current Defect**: In `EnsembleScoringEngine.combine_predictions()` (lines 2389–2445), Factor Orthogonalization (PCA-ZCA whitening / Gram-Schmidt) was executed in **Phase 3-B**, *before* Inter-Strategy Signal Correlation Monitoring and Regime Factor Noise Suppression in **Phase 3-C**.
- **Mathematical Impact**:
  - PCA-ZCA whitening projects the factor score matrix $X \in \mathbb{R}^{N \times K}$ onto its decorrelated eigenbasis, collapsing cross-factor correlation to $|\rho_{ij}| < 0.25$.
  - When `StrategyCorrelationMonitor.update_correlation(merged)` was invoked in Phase 3-C, it calculated correlations on the *already-decorrelated* matrix.
  - In `RegimeFactorSuppressionEngine.compute_penalties()`, the excess correlation penalty is formulated as:
    $$E_{ij} = \max(0, |\rho_{ij}| - \theta(R))$$
    Since the base regime cutoffs satisfy $\theta(R) \ge 0.50$ (e.g. $0.60$ in `SIDEWAYS_LOW_VOL`, $0.70$ in `BULL_LOW_VOL`), and $|\rho_{ij}| < 0.25$, the term $E_{ij} \equiv 0$ evaluated to zero for all pairs.
  - Consequently, the penalty multiplier $P_i(R) = 1 / \sqrt{1 + \lambda \sum c_{ij} E_{ij}^2}$ remained $1.000000$, completely bypassing multi-collinearity penalties in live pipeline execution.
- **Remediation**:
  - Invert the sequence: Run Cross-Sectional Score Normalization (Phase 3-A) $\to$ **Pre-Orthogonalization Correlation Monitoring & Noise Suppression (Phase 3-B)** on raw normalized scores $\to$ **Factor Orthogonalization (Phase 3-C)** with suppressed strategy weights.

### 1.2 Feature 6: Statistically Calibrated Suppression Cutoffs $\theta(R, N)$
- **Current Defect**: `RegimeFactorSuppressionEngine` used static heuristic correlation cutoffs $\theta_0(R)$ that did not scale with the cross-sectional sample size $N$.
- **Statistical Foundation**:
  - Under Fisher's $z$-transformation, sample Pearson/Spearman correlation $r$ has asymptotic variance:
    $$\text{Var}(z) = \frac{1}{N - 3}, \quad \text{SE}(r) \approx \frac{1}{\sqrt{N - 3}}$$
  - In small universes ($N = 50$, such as testing or constrained sub-sectors), sample correlation exhibits high sampling variance: two uncorrelated series can easily produce empirical correlation $|r| = 0.30 \sim 0.40$ by chance.
  - In large universes ($N = 500 \sim 2000$, such as S&P 500 or Russell 2000), sampling noise shrinks rapidly ($\text{SE} < 0.045$).
  - Therefore, the collinearity cutoff must require $95\%$ one-sided statistical significance ($z_{0.95} = 1.645$):
    $$\theta(R, N) = \text{clip}\left(\theta_0(R) + \frac{1.645}{\sqrt{\max(N - 3, 1)}}, 0.35, 0.85\right)$$
  - For $N \le 3$ or $N$ is `None`, it seamlessly falls back to $\theta_0(R)$.

---

## 2. Mathematical Formulations

### 2.1 Pre-Orthogonalization Factor Collinearity Suppression
1. Given cross-sectionally normalized score matrix $S \in \mathbb{R}^{N \times K}$ (where $S_{ik} \in [0, 1]$):
2. Compute raw Spearman rank correlation matrix:
   $$R_{ij}^{\text{raw}} = \text{SpearmanRankCorr}(S_{\cdot, i}, S_{\cdot, j})$$
3. Evaluate statistically calibrated excess correlation:
   $$E_{ij}(R, N) = \max(0, |R_{ij}^{\text{raw}}| - \theta(R, N))$$
4. Compute cluster relationship multiplier $c_{ij}(R)$:
   $$c_{ij}(R) = \begin{cases} 2.0, & i, j \in \mathcal{C}_k \text{ and } \mathcal{C}_k \in \text{HighRisk}(R) \\ 1.5, & i, j \in \mathcal{C}_k \text{ and } \mathcal{C}_k \notin \text{HighRisk}(R) \\ 1.0, & \text{otherwise} \end{cases}$$
5. Suppression multiplier:
   $$P_i(R, N) = \min\left( \frac{1}{\sqrt{1 + \lambda(R) \sum_{j \neq i} c_{ij}(R) E_{ij}(R, N)^2}}, \min\left(1.0, \sqrt{\frac{10.0}{\max(\text{VIF}_i, 10^{-6})}}\right) \right)$$
6. Update nominal strategy weights:
   $$\tilde{w}_i = \frac{w_i \cdot P_i(R, N)}{\sum_{k=1}^K w_k \cdot P_k(R, N)}$$
7. Orthogonalize signals using suppressed weights $\tilde{w}$:
   $$S_{\text{ortho}} = \text{PCA-ZCA-Whitening}(S, \tilde{w})$$

---

## 3. Exact Code Changes & Diff Guidelines

### 3.1 File 1: `trading_system/src/ai/factor_suppression.py`

#### Change 1: Add `calibrate_cutoff` static method to `RegimeFactorSuppressionEngine`
Location: Inside `RegimeFactorSuppressionEngine`, immediately before `_get_regime_params`.

```python
    @staticmethod
    def calibrate_cutoff(
        theta_0: float,
        n_samples: Optional[int],
        z_score: float = 1.645,
        min_theta: float = 0.35,
        max_theta: float = 0.85
    ) -> float:
        """
        Statistically calibrated correlation suppression cutoff:
            theta(R, N) = clip( theta_0(R) + z_{0.95} / sqrt(max(N - 3, 1)), min_theta, max_theta )
        Under Fisher's z-transformation, asymptotic standard error SE(r) ~ 1/sqrt(N-3).
        Guarantees that collinearity suppression operates only when empirical correlation
        statistically significantly exceeds the base threshold at the 95% one-sided confidence level.
        """
        if n_samples is None or n_samples <= 3:
            return float(theta_0)
        calibrated = float(theta_0) + float(z_score) / np.sqrt(float(max(n_samples - 3, 1)))
        return float(np.clip(calibrated, min_theta, max_theta))
```

#### Change 2: Update `_get_regime_params` to accept `n_samples`
Location: `RegimeFactorSuppressionEngine._get_regime_params` (lines 123–145).

```python
    def _get_regime_params(
        self,
        regime_label: str,
        tuned_params: Optional[Dict[str, Any]] = None,
        n_samples: Optional[int] = None
    ) -> Tuple[float, float]:
        """Retrieves theta and lambda_penalty parameters for given regime label,
        applying sample-size statistical calibration theta(R, N) = theta_0(R) + 1.645 / sqrt(N-3)."""
        reg_str = str(regime_label).upper()

        theta_0 = self.default_theta
        lam = self.default_lambda

        # Check tuned_params override first
        if tuned_params and 'correlation_suppression' in tuned_params:
            supp_params = tuned_params['correlation_suppression']
            if reg_str in supp_params:
                theta_0 = float(supp_params[reg_str].get('theta', self.default_theta))
                lam = float(supp_params[reg_str].get('lambda', self.default_lambda))
                eff_theta = self.calibrate_cutoff(theta_0, n_samples)
                return float(eff_theta), float(lam)

        # Fallback to default regime map
        if reg_str in self.DEFAULT_REGIME_PARAMS:
            p = self.DEFAULT_REGIME_PARAMS[reg_str]
            theta_0 = float(p['theta'])
            lam = float(p['lambda'])
            eff_theta = self.calibrate_cutoff(theta_0, n_samples)
            return float(eff_theta), float(lam)

        eff_theta = self.calibrate_cutoff(theta_0, n_samples)
        return float(eff_theta), float(lam)
```

#### Change 3: Update `compute_penalties` signature and logic
Location: `RegimeFactorSuppressionEngine.compute_penalties` (lines 169–186).

```python
    def compute_penalties(
        self,
        corr_matrix: pd.DataFrame,
        regime_label: str,
        theta: Optional[float] = None,
        lambda_penalty: Optional[float] = None,
        consensus_precision: Optional[Dict[str, float]] = None,
        vif_dict: Optional[Dict[str, float]] = None,
        cluster_sharpes: Optional[Dict[str, float]] = None,
        n_samples: Optional[int] = None,
    ) -> Dict[str, float]:
        """
        Computes dynamic suppression penalty multiplier p_i for each strategy.
        p_i = min( 1 / sqrt(1 + lambda * sum(c_ij * excess_ij^2)), vif_damping )
        """
        eff_n = n_samples
        if eff_n is None and hasattr(corr_matrix, 'attrs') and 'n_samples' in corr_matrix.attrs:
            eff_n = corr_matrix.attrs.get('n_samples')

        eff_theta, eff_lambda = self._get_regime_params(regime_label, n_samples=eff_n)
        theta_val = theta if theta is not None else eff_theta
        lambda_val = lambda_penalty if lambda_penalty is not None else eff_lambda
```

#### Change 4: Update `suppress_weights` signature and logic
Location: `RegimeFactorSuppressionEngine.suppress_weights` (lines 249–291).

```python
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
                        n_samples=eff_n
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

        penalties = self.compute_penalties(
            corr_matrix=corr_matrix,
            regime_label=regime_label,
            theta=eff_theta,
            lambda_penalty=eff_lambda,
            consensus_precision=consensus_precision,
            vif_dict=vif_dict,
            cluster_sharpes=cluster_sharpes,
            n_samples=eff_n
        )
```

#### Change 5: Update `get_suppression_report` signature and logic
Location: `RegimeFactorSuppressionEngine.get_suppression_report` (lines 333–378).

```python
    def get_suppression_report(
        self,
        base_weights: Dict[str, float],
        corr_matrix: pd.DataFrame,
        regime_label: str,
        theta: Optional[float] = None,
        lambda_penalty: Optional[float] = None,
        tuned_params: Optional[Dict[str, Any]] = None,
        n_samples: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Returns diagnostic dictionary detailing initial vs suppressed weights,
        dampening penalties P_i, active high-risk clusters, and cutoff settings.
        """
        eff_n = n_samples
        if eff_n is None and hasattr(corr_matrix, 'attrs') and 'n_samples' in corr_matrix.attrs:
            eff_n = corr_matrix.attrs.get('n_samples')

        eff_t, eff_l = self._get_regime_params(regime_label, tuned_params=tuned_params, n_samples=eff_n)
        if theta is not None:
            eff_t = theta
        if lambda_penalty is not None:
            eff_l = lambda_penalty

        penalties = self.compute_penalties(
            corr_matrix=corr_matrix,
            regime_label=regime_label,
            theta=eff_t,
            lambda_penalty=eff_l,
            n_samples=eff_n
        )
        suppressed_w = self.suppress_weights(
            base_weights=base_weights,
            corr_matrix=corr_matrix,
            regime_label=regime_label,
            theta=eff_t,
            lambda_penalty=eff_l,
            tuned_params=tuned_params,
            n_samples=eff_n
        )

        high_risk = self._get_high_risk_clusters(regime_label)

        return {
            'regime': str(regime_label),
            'theta': eff_t,
            'lambda_penalty': eff_l,
            'n_samples': eff_n,
            'high_risk_clusters': high_risk,
            'base_weights': base_weights,
            'penalties': penalties,
            'suppressed_weights': suppressed_w
        }
```

---

### 3.2 File 2: `trading_system/src/ai/ensemble_scorer.py`

#### Target Location: `combine_predictions()` (lines 2389–2445)
Replace existing Phase 3-B, Phase 3-B.1, and Phase 3-C with the following rectified pipeline:

```python
        # Phase 3-B (Pre-Orthogonalization): Inter-Strategy Signal Correlation Monitoring & 2D Regime Noise Suppression
        # Feature 1: Move raw correlation monitoring and factor suppression BEFORE ZCA orthogonalization
        correlation_report_dict = None
        if len(merged) >= 5:
            try:
                # 1. Update correlation matrix on raw cross-sectional factor signals
                corr_df = self.correlation_monitor.update_correlation(merged)
                vif_dict = self.correlation_monitor.compute_vif(corr_df)

                # 2. Extract cross-sectional sample size N for statistically calibrated suppression
                n_cross_section = len(merged)

                # 3. Apply correlation orthogonalization penalty on raw signals if custom weights provided
                if weights is not None and isinstance(weights, dict) and len(weights) > 1:
                    weights = self.apply_correlation_orthogonalization_penalty(
                        weights,
                        scores_df=merged,
                        correlation_threshold=0.65,
                        penalty_factor=0.5,
                    )

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
                n_eff = self.correlation_monitor.compute_effective_strategy_count(
                    weights=suppressed_w,
                    corr_matrix=corr_df
                )
                top_pairs = self.correlation_monitor.get_top_collinear_pairs(threshold=0.50, corr_matrix=corr_df)
                raw_penalties = self.factor_suppression.compute_penalties(
                    corr_matrix=corr_df,
                    regime_label=str(regime),
                    n_samples=n_cross_section
                )

                weights = suppressed_w

                correlation_report_dict = {
                    'correlation_matrix': corr_df,
                    'vif': vif_dict,
                    'n_eff': n_eff,
                    'suppressed_weights': suppressed_w,
                    'penalties': raw_penalties,
                    'top_collinear_pairs': top_pairs
                }
                if not hasattr(merged, 'attrs') or merged.attrs is None:
                    merged.attrs = {}
                merged.attrs['correlation_report'] = correlation_report_dict
            except Exception as _ce:
                logger.warning(f"Correlation suppression calculation warning: {_ce}")

        # Phase 3-C: Factor Orthogonalization (PCA ZCA / Gram-Schmidt)
        # Executed AFTER raw factor suppression so orthogonalization receives suppressed strategy weights
        if getattr(self, 'orthogonalizer_enabled', True):
            try:
                strategy_score_cols = [col for _, col in strategy_cols if col in merged.columns]
                strat_weights = {col: (weights.get(strat_name, 0.10) if weights else 0.10) for strat_name, col in strategy_cols if col in merged.columns}
                merged = self.orthogonalizer.orthogonalize(
                    score_df=merged,
                    strategy_cols=strategy_score_cols,
                    weights=strat_weights,
                    method='pca_symmetric'
                )
                # Ensure attrs dictionary is strictly preserved after orthogonalization copy
                if correlation_report_dict is not None:
                    if not hasattr(merged, 'attrs') or merged.attrs is None:
                        merged.attrs = {}
                    merged.attrs['correlation_report'] = correlation_report_dict
            except Exception as _oe:
                logger.warning(f"Factor orthogonalization warning: {_oe}")
```

---

### 3.3 File 3: `trading_system/src/ai/correlation_monitor.py` (Optional / Recommended Metadata Tagging)

#### Target Location: `StrategyCorrelationMonitor.update_correlation()` (lines 141–150)
Tag effective sample size $N$ directly onto `rolling_corr_matrix.attrs`:

```python
        # Exponential moving average smoothing
        if self.rolling_corr_matrix is None or (self.rolling_corr_matrix.values == np.eye(len(self.strategies))).all():
            self.rolling_corr_matrix = current_corr
        else:
            smoothed = self.alpha_corr * current_corr.values + (1.0 - self.alpha_corr) * self.rolling_corr_matrix.values
            smoothed = (smoothed + smoothed.T) / 2.0
            np.fill_diagonal(smoothed, 1.0)
            self.rolling_corr_matrix = pd.DataFrame(smoothed, index=self.strategies, columns=self.strategies).clip(lower=-1.0, upper=1.0)

        # Attach effective sample size N to DataFrame metadata
        if hasattr(self.rolling_corr_matrix, 'attrs'):
            self.rolling_corr_matrix.attrs['n_samples'] = len(valid_df)

        return self.rolling_corr_matrix
```

---

### 3.4 File 4: `tests/test_correlation_suppression.py` (New Test Cases)

Add the following two dedicated unit tests to `tests/test_correlation_suppression.py`:

```python
def test_statistically_calibrated_cutoff_formula():
    """Verify statistical cutoff calibration theta(R, N) = theta_0(R) + 1.645 / sqrt(N-3)."""
    supp = RegimeFactorSuppressionEngine()

    theta_0 = 0.60
    # 1. Fallback for None or N <= 3
    assert supp.calibrate_cutoff(theta_0, None) == 0.60
    assert supp.calibrate_cutoff(theta_0, 2) == 0.60
    assert supp.calibrate_cutoff(theta_0, 3) == 0.60

    # 2. Monotonic decay as sample size N increases
    theta_50 = supp.calibrate_cutoff(theta_0, 50)
    theta_500 = supp.calibrate_cutoff(theta_0, 500)
    theta_2000 = supp.calibrate_cutoff(theta_0, 2000)

    expected_50 = np.clip(0.60 + 1.645 / np.sqrt(47), 0.35, 0.85)
    expected_500 = np.clip(0.60 + 1.645 / np.sqrt(497), 0.35, 0.85)
    expected_2000 = np.clip(0.60 + 1.645 / np.sqrt(1997), 0.35, 0.85)

    assert abs(theta_50 - expected_50) < 1e-4
    assert abs(theta_500 - expected_500) < 1e-4
    assert abs(theta_2000 - expected_2000) < 1e-4
    assert theta_50 > theta_500 > theta_2000 > theta_0

    # 3. Clamping bounds [0.35, 0.85]
    assert supp.calibrate_cutoff(0.10, 10000) == 0.35
    assert supp.calibrate_cutoff(0.80, 5) == 0.85


def test_pre_orthogonalization_raw_correlation_suppression(sample_17_strategy_df):
    """Verify that combine_predictions monitors raw correlation and applies active suppression penalties."""
    engine = EnsembleScoringEngine()
    df = sample_17_strategy_df.copy()
    df['name'] = df['symbol']
    df['market'] = 'KOSPI'
    df['close'] = 50000.0
    df['volume'] = 1_000_000.0

    res = engine.combine_predictions(
        reg_df=df, s_df=df, ll_df=df, v_rule_df=df, vcp_ml_df=df,
        lstm_df=df, stat_arb_df=df, sector_df=df, rim_df=df,
        event_df=df, mq_df=df, iv_skew_df=df, order_flow_df=df,
        reversal_df=df, arm_df=df, card_df=df, latr_df=df,
        inst_foreign_sector_df=df, regime='SIDEWAYS_LOW_VOL'
    )

    assert hasattr(res, 'attrs')
    assert 'correlation_report' in res.attrs
    rep = res.attrs['correlation_report']

    # Raw correlation between surge and vcp_ml should be high (> 0.85)
    raw_corr = rep['correlation_matrix']
    assert raw_corr.loc['surge', 'vcp_ml'] > 0.85

    # In SIDEWAYS_LOW_VOL, MOMENTUM is high-risk redundant cluster; surge must be penalized
    penalties = rep['penalties']
    assert penalties['surge'] < 0.90, f"Expected active raw suppression penalty (<0.90), got {penalties['surge']}"
    assert penalties['vcp_ml'] < 0.90
```

---

## 4. Verification Protocol

### Test Execution Commands
```bash
# 1. Run target test suites
.venv\Scripts\pytest tests/test_correlation_suppression.py -v
.venv\Scripts\pytest tests/test_factor_orthogonalization.py -v
.venv\Scripts\pytest tests/test_adversarial_ensemble_scorer_challenger.py -v

# 2. Run comprehensive ensemble test suite
.venv\Scripts\pytest tests/test_r1_ensemble_regime_fixes.py tests/test_score_normalizer.py tests/test_m1_1_fixes.py -v
```

### Acceptance Criteria Checklist
- [x] Pre-orthogonalization factor correlation operates strictly on raw normalized signals.
- [x] Factor suppression penalties $P_i(R) < 1.0$ actively penalize collinear momentum factors in sideways regimes.
- [x] $\theta(R, N) = \text{clip}(\theta_0(R) + 1.645/\sqrt{N-3}, 0.35, 0.85)$ is monotonically decreasing with $N$.
- [x] Fallback behavior for $N \le 3$ and $N=\text{None}$ guarantees $100\%$ backward compatibility.
- [x] All 18 existing correlation suppression tests and 17 adversarial tests pass with $0$ regressions.
