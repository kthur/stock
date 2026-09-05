# Phase 8 Sovereign Quantitative Enhancements (v15): M1 Signal & Alpha Architecture Handoff Report

**Author**: Survey Explorer 1 (M1: Signal & Alpha Architecture)  
**Date**: 2026-09-05T02:22:00Z  
**Status**: Complete Investigation & Technical Design  
**Target Milestone**: Phase 8 Sovereign Quantitative Enhancements (v15)  
**Assigned Scope**: Requirement R1 (Features F51 & F52) — Riemannian Manifold Geodesic 5-Pillar Synergy, Hyperexponential Convex Rank Modulation $g_{\text{v8}}(r)$, Hurst Exponent ($H$) Fractional Jump-Diffusion Regime Weights, and Asymmetric Wavelet Noise Deadband ($99.99\%$ noise suppression).

---

## Executive Summary

This investigation surveys the R1 codebase across `trading_system/src/ai/ensemble_scorer.py`, `trading_system/src/ai/factor_suppression.py`, and `trading_system/src/ai/score_normalizer.py`. We comprehensively analyzed the Phase 7 Zenith (v14) implementations (Features F47 & F48) and engineered the mathematical models, architectural interfaces, code diff proposals, and test specifications for Phase 8 Sovereign (v15) enhancements.

Phase 8 elevates alpha signal extraction through three foundational innovations:
1. **R1-1 (Feature F51.1)**: **Information Geometry Riemannian Manifold Geodesic 5-Pillar Mapping**: Upgrades the Euclidean coefficient-of-variation regularizer ($CV = \sigma / \mu$) into a Fisher-Rao Information Metric on the 4-simplex $\mathcal{S}^4$ isometrically mapped to the 4-hypersphere $\mathbb{S}^4$. Great-circle arc geodesic distance $d_R(p, p_0) = \arccos(\sum \sqrt{0.20 p_k})$ regularizes 5-pillar harmony via $H_{\text{Riemann}} = \exp(-2.40 d_R^2)$, boosting harmonious confluence up to $1.30\times$ and expanding Bull Low Vol cap to $0.250$ (from $0.220$).
2. **R1-2 (Feature F51.2)**: **Hyperexponential Convex Rank Modulation $g_{\text{v8}}(r) = r \cdot \exp(\gamma_{\text{top}} \cdot r^3)$**: Replaces the Phase 7 quartic polynomial $g_{\text{v7}}(r)$ for positive excess conviction assets ($z \ge 0$). With regime-adaptive $\gamma_{\text{top}}(R) \in [0.20, 0.85]$, this increases the alpha spread between the 90th percentile and 100th percentile by **$+44.2\%$**, isolating the top 1% sovereign alpha assets while strictly preserving $C^\infty$ monotonicity ($g' > 0$) and convexity ($g'' \ge 0$).
3. **R1-3 (Feature F52)**: **Hurst Exponent ($H$) Fractional Jump-Diffusion & Asymmetric Wavelet Deadband**: 
   - Modulates the Merton regime jump indicator by long-memory fractional persistence: $J_{\text{frac}} = J_{\text{regime}} \cdot (2H)^{1.5}$. When trending memory is strong ($H > 0.50$), jump responsiveness is boosted by up to $1.65\times$; when anti-persistent chop dominates ($H < 0.35$), false alarms are squashed by $41.5\%$.
   - Upgrades the quintic deadband ($\alpha = 5.0$, $0.054\%$ leakage) into an Asymmetric Septic Wavelet Deadband ($\alpha = 7.0$), reducing near-zero noise leakage to **$0.00267\%$** (suppressing **$99.997\%$** of noise — a **20-fold improvement over Phase 7** and **412-fold improvement over Phase 6**) while transmitting $100.000\%$ of high-conviction signals ($|z| \ge 0.150$).

All 12 baseline Phase 7 tests (`tests/test_phase7_signal_enhancement.py` and `tests/test_benchmark_phase7.py`) and 31 score normalization & adversarial tests currently pass with 100% success.

---

## 1. Direct Observations (Exact File Paths, Line Numbers, Verbatim Code)

### 1.1 `trading_system/src/ai/ensemble_scorer.py` (5,282 lines)

#### A. 5-Pillar Tensor Synergy & Pillar Harmony Regularizer (F47.1)
- **File**: `trading_system/src/ai/ensemble_scorer.py`
- **Lines 4570–4838**: `compute_quint_pillar_tensor_synergy(cls, scores_df, regime='SIDEWAYS_LOW_VOL', kappa=8.0, regime_adaptive_cap=True, max_cap=None, version=6, **kwargs)`
- **Verbatim Lines 4608–4631**:
  ```python
  clusters = {
      'val': ['rim_score', 'valueup_catalyst_score', 'accruals_quality_score', 'arm_score', 'factor_neutralized_score', 'reg_score'],
      'mom': ['surge_score', 'vcp_ml_score', 'trend_efficiency_score', 'sector_score', 'range_expansion_score', 'mq_score', 'll_score', 'vcp_rule_score', 'lstm_score'],
      'flow': ['order_flow_score', 'inst_foreign_sector_score', 'darkpool_score', 'microstructure_score', 'overnight_gap_score', 'stat_arb_score', 'iv_skew_score', 'reversal_score', 'vol_target_score'],
      'cat': ['event_score', 'sentiment_score', 'short_squeeze_score', 'gamma_squeeze_score', 'insider_buying_score', 'earnings_tone_drift_score'],
      'net': ['supply_chain_score', 'supply_chain_gnn_score', 'cross_asset_spillover_score', 'dual_correction_score', 'index_rebalance_score', 'card_score', 'latr_score']
  }
  ```
- **Verbatim Lines 4665, 4785–4792**:
  ```python
  reg_cap = 0.220 if version >= 7 else 0.180
  ...
  tri_multipliers = {
      ('val', 'mom', 'flow'): 1.40,
      ('flow', 'cat', 'net'): 1.20,
  }
  if w_tri > 0:
      if version >= 7:
          for trip_key, (t1, t2, t3) in named_triplets:
              mult_factor = tri_multipliers.get(trip_key, 1.00)
              tri_confluence += (w_tri * mult_factor) * (t1 * t2 * t3)
  ```
- **Verbatim Lines 4813–4828 (Phase 7 Pillar Harmony Regularizer)**:
  ```python
  # 5. Pillar Harmony Regularizer H_pillar (Phase 7 Zenith F47.1)
  if version >= 7:
      p_vals = np.array([p_val.values, p_mom.values, p_flow.values, p_cat.values, p_net.values])
      p_mean = np.mean(p_vals, axis=0)
      p_std = np.std(p_vals, axis=0)
      cv_p = p_std / (p_mean + 1e-4)
      cv_clipped = np.clip(cv_p, 0.0, 2.0)
      h_pillar = np.exp(-1.20 * np.square(cv_clipped))
      harmony_factor = pd.Series(
          1.0 + 0.25 * h_pillar * (p_mean > 0.40).astype(float),
          index=scores_df.index
      )
      total_confluence = raw_confluence * harmony_factor
  else:
      total_confluence = raw_confluence
  ```
- **Invocation in `combine_predictions` (Lines 3355–3364)**:
  ```python
  # Phase 2-B: Quint-Pillar High-Order Tensor Synergy Kernel (F41.1 & F47.1) vs Quad-Pillar Baseline
  if int(version) >= 6:
      synergy_mult = self.compute_quint_pillar_tensor_synergy(
          scores_df=merged,
          regime=regime,
          kappa=8.0,
          regime_adaptive_cap=True,
          version=version
      )
  ```

#### B. Merton Jump-Diffusion Regime Transition Base Weight Mixture (F47.3)
- **Lines 1215–1289**: Inside `get_base_weights(...)`:
  ```python
  # Feature F47: Merton Jump-Diffusion Regime Transition Base Weight Mixture (version >= 7)
  if int(version) >= 7:
      ...
      d_tv = 0.5 * sum(abs(curr_norm.get(s, 0.0) - prev_norm.get(s, 0.0)) for s in all_states)
      if d_tv > 0.25:
          # Empirical Jump Indicator J_regime in [0.0, 1.0]
          j_regime = float(np.clip((d_tv - 0.25) / 0.35, 0.0, 1.0))
          ...
          # w_Zenith^* = (1 - 0.60 * J_regime) * w_diffusion + 0.60 * J_regime * W_2D(R_jump)
          blend_jump = 0.60 * j_regime
          blend_diff = 1.0 - blend_jump
          all_strats = set(w_diffusion.keys()) | set(w_jump.keys())
          w_zenith = {}
          for strat in all_strats:
              w_zenith[strat] = blend_diff * float(w_diffusion.get(strat, 0.0)) + blend_jump * float(w_jump.get(strat, 0.0))
  ```

#### C. Noise Deadband Soft-Thresholding & Rank Modulation (F48.2 & F48.3)
- **Lines 3478–3512**: Inside `combine_predictions(...)`:
  ```python
  # Feature F36.2 & F42.2 & F48.2: Smooth Hyperbolic Tangent Noise Deadband Soft-Thresholding
  delta_noise = self.get_regime_adaptive_noise_deadband(regime, regime_probs=regime_probs)
  if int(version) >= 7:
      z_denoised = self.apply_smooth_noise_deadband(abs_centered, delta_noise=delta_noise, regime=regime, version=7)
      gamma_tail = self.get_regime_adaptive_gamma_tail(regime, version=7)
  elif int(version) >= 6:
      z_denoised = self.apply_smooth_noise_deadband(abs_centered, delta_noise=delta_noise, regime=regime, version=6)
      gamma_tail = self.get_regime_adaptive_gamma_tail(regime, version=6)
  else:
      z_denoised = self.apply_smooth_noise_deadband(abs_centered, delta_noise=delta_noise, alpha_pos=3.0, alpha_neg=3.0)
      gamma_tail = self.get_regime_adaptive_gamma_tail(regime, version=5)

  if len(ens_scores) >= 5:
      ranks = pd.Series(ens_scores).rank(pct=True).values
      reg_str = str(regime).upper()
      if 'BULL' in reg_str or str(regime) == '2':
          if int(version) >= 7:
              # Feature F48.3: Quartic rank modulation in Bull regimes: steepens convexity for top percentiles
              # g_v7(r) = 0.60 + 0.25*r + 0.25*r^2 + 0.40*r^3 + 0.35*r^4
              mult = np.where(
                  z_denoised >= 0.0,
                  0.60 + 0.25 * ranks + 0.25 * (ranks ** 2) + 0.40 * (ranks ** 3) + 0.35 * (ranks ** 4),
                  1.40 - 0.80 * ranks
              )
          elif int(version) >= 6:
              mult = np.where(z_denoised >= 0.0, 0.60 + 0.30 * ranks + 0.30 * (ranks ** 2) + 0.55 * (ranks ** 3), 1.40 - 0.80 * ranks)
          else:
              mult = np.where(z_denoised >= 0.0, 0.60 + 0.50 * ranks + 0.50 * (ranks ** 2), 1.40 - 0.80 * ranks)
      else:
          mult = np.where(z_denoised >= 0.0, 0.60 + 0.80 * ranks, 1.40 - 0.80 * ranks)
      unclipped_score = z_denoised * mult
  else:
      unclipped_score = z_denoised
  ```

#### D. Directional Volatility Markov Departure Penalty (F48.1)
- **Lines 4205–4215**: In `get_regime_adaptive_half_lives(...)`:
  ```python
  # For version >= 7: Directional Volatility Modulated Markov Departure Penalty
  if int(version) >= 7:
      high_vol_states = {'CRISIS', 'BEAR_HIGH_VOL', 'SIDEWAYS_HIGH_VOL', 'BULL_HIGH_VOL'}
      curr_high_vol = sum(prob for state, prob in pi_norm.items() if str(state).upper() in high_vol_states)
      stat_high_vol = sum(cls.PI_STATIONARY.get(s, 0.0) for s in high_vol_states)
      s_vol = float(curr_high_vol - stat_high_vol)
      kappa_markov = float(np.clip(0.25 * (1.0 + 0.80 * max(0.0, s_vol)), 0.25, 0.45))
      phi_kl = float(np.exp(-kappa_markov * max(0.0, d_kl)))
  else:
      phi_kl = float(np.exp(-0.25 * max(0.0, d_kl)))
  ```

#### E. Smooth Deadband Implementation (Lines 5204–5225)
- **Lines 5204–5225**:
  ```python
  version = int(kwargs.get('version', version))
  if int(version) >= 7:
      eff_alpha = 5.0 if alpha_pos == 3.0 else alpha_pos
      return apply_quintic_hyperbolic_deadband(
          scores_centered=scores_centered,
          delta_noise=delta_noise,
          delta_neg=delta_neg,
          alpha_pos=eff_alpha,
          alpha_neg=alpha_neg,
          regime=regime
      )
  ```

---

### 1.2 `trading_system/src/ai/factor_suppression.py` (542 lines)
- **Lines 35–41**: `QUINT_PILLAR_MAP` partitions 37 strategies across 5 disjoint pillars:
  - `'val'`: `['rim_valuation', 'valueup_catalyst', 'accruals_quality', 'arm_factor', 'factor_neutralized', 'regression']` (6)
  - `'mom'`: `['surge', 'vcp_ml', 'trend_efficiency', 'sector_rotation', 'range_expansion', 'mq_factor', 'lead_lag', 'vcp_rule', 'lstm']` (9)
  - `'flow'`: `['order_flow', 'inst_foreign_sector', 'darkpool', 'microstructure', 'overnight_gap', 'stat_arb', 'iv_skew', 'short_term_reversal', 'vol_target']` (9)
  - `'cat'`: `['event_driven', 'sentiment', 'short_squeeze', 'gamma_squeeze', 'insider_buying', 'earnings_tone_drift']` (6)
  - `'net'`: `['supply_chain', 'supply_chain_gnn', 'cross_asset_spillover', 'dual_correction', 'index_rebalance', 'card_factor', 'latr_factor']` (7)
- **Lines 44–100**: `apply_quintic_hyperbolic_deadband(...)`:
  ```python
  abs_z = np.abs(z)
  ratio = np.clip(abs_z / delta_eff, 0.0, 50.0)
  arg = np.clip(np.power(ratio, alpha_eff), 0.0, 50.0)
  denoised = z * np.tanh(arg)
  ```
  With $\alpha_{\text{eff}} = 5.0$, near-zero noise ($|z| \le 0.010$) is squashed to $0.054\%$ leakage ($>99.9\%$ suppression).

---

### 1.3 `trading_system/src/ai/score_normalizer.py` (282 lines)
- Cross-sectional score normalizer maps all strategy columns to $[0.005, 0.995]$ using either:
  - `winsorized_zscore`: $\Phi(z)$ via `erf(z / sqrt(2))`
  - `percentile_rank`: $(rank - 0.5) / N$
- Correctly preserves NaNs for missing strategies, handles small sector fallbacks ($N \ge 4$), and outputs scores centered at $0.50$.
- In Phase 8, this clean $[0.005, 0.995]$ scale directly feeds into the rank percentile calculation ($r \in [0, 1]$), providing pristine input for the hyperexponential rank modulation $g_{\text{v8}}(r)$.

---

## 2. Logic Chain: Analysis of Phase 7 (F47 & F48) & Need for Phase 8

1. **Pillar Harmony Geometry**:
   - *Observation*: Phase 7 uses Euclidean coefficient of variation $CV = \sigma / (\mu + 10^{-4})$ to measure pillar balance.
   - *Limitation*: The 5-pillar conviction vector $p \in \mathcal{S}^4$ lives on the statistical probability simplex, which possesses non-zero curvature under the Fisher-Rao information metric. Euclidean distance distorts near the boundary (sparse activation of 1 or 2 pillars) and fails to capture the true Riemannian distance along the geodesic.
   - *Phase 8 Solution*: By mapping the simplex to the 4-sphere $\mathbb{S}^4$ via $u_k = \sqrt{p_k}$, the Fisher-Rao geodesic distance from uninformative prior $p_0$ is the exact arc length $d_R(p, p_0) = \arccos(\sum \sqrt{0.20 p_k})$. Regularization via $H_{\text{Riemann}} = \exp(-\zeta_R d_R^2)$ delivers theoretically exact Information Geometry harmony, scaling synergy up to $1.30\times$ (cap $0.250$).

2. **Extreme Alpha Spread in the Top 1%**:
   - *Observation*: Phase 7 uses quartic polynomial $g_{\text{v7}}(r) = 0.60 + 0.25r + 0.25r^2 + 0.40r^3 + 0.35r^4$. At $r = 1.0$, $g_{\text{v7}}(1.0) = 1.85$, while at $r = 0.90$, $g_{\text{v7}}(0.90) = 1.549$.
   - *Limitation*: Polynomial growth decelerates in higher derivatives relative to exponential growth. For the top 1% ($r \in [0.99, 1.00]$), quartic growth does not create sufficient convexity separation from ordinary 85th–90th percentile assets.
   - *Phase 8 Solution*: Hyperexponential convex rank modulation $g_{\text{v8}}(r) = r \cdot \exp(\gamma_{\text{top}} r^3)$ introduces an exponential acceleration term that activates primarily for $r \ge 0.90$. At $r = 1.00$ with $\gamma_{\text{top}} = 0.85$, $g_{\text{v8}}(1.0) = 2.340$, expanding the spread between the 90th and 100th percentiles by **$+44.2\%$** while preserving strict $C^\infty$ monotonicity ($g' > 0$) and convexity ($g'' \ge 0$).

3. **Regime Transition Memory & Noise Leakage**:
   - *Observation*: Phase 7 Merton jump-diffusion assumes memoryless Brownian transitions ($H = 0.50$), and quintic deadband leaves $0.054\%$ noise leakage ($>99.9\%$ suppression).
   - *Limitation*: Real financial regimes exhibit long-memory fractal persistence ($H > 0.50$ during macroeconomic trends) or anti-persistent chop ($H < 0.50$ in sideways churn). Furthermore, institutional OMS requires suppressing **$99.99\%$** of noise (leakage $\le 0.01\%$) to eliminate micro-churn in execution.
   - *Phase 8 Solution*: Fractional jump-diffusion scales the jump indicator by $(2H)^{1.5}$, boosting persistent trend transitions while damping false-alarm chop. The Asymmetric Septic Wavelet Deadband ($\alpha = 7.0$) achieves $0.00267\%$ leakage (**$99.997\%$ suppression**, a 20-fold improvement) while ensuring $100.000\%$ signal transmission for conviction signals $|z| \ge 0.150$.

---

## 3. Technical Design for Phase 8 Sovereign Enhancements (v15)

### 3.1 R1-1: Information Geometry Riemannian Manifold Geodesic 5-Pillar Mapping

#### Mathematical Formulation
1. **Pillar Convictions**: $\psi_k \in [0, 1]$ for $k \in \{\text{val}, \text{mom}, \text{flow}, \text{cat}, \text{net}\}$.
2. **Probability Simplex Normalization**:
   $$p_k = \frac{\psi_k + \epsilon}{\sum_{m=1}^5 (\psi_m + \epsilon)}, \quad \epsilon = 10^{-6}$$
3. **Fisher-Rao Information Metric & Hypersphere Mapping**:
   The coordinates $u_k = \sqrt{p_k}$ map $\mathcal{S}^4$ isometrically to the unit hypersphere $\mathbb{S}^4$ ($\sum u_k^2 = 1$).
   The uninformative prior state is $p_0 = (0.20, 0.20, 0.20, 0.20, 0.20)^T$ ($u_{0, k} = \frac{1}{\sqrt{5}}$).
4. **Bhattacharyya Affinity Coefficient & Geodesic Arc Distance**:
   $$\text{BC}(p, p_0) = \sum_{k=1}^5 \sqrt{0.20 \cdot p_k}$$
   $$d_R(p, p_0) = \arccos\left(\text{clip}\left(\text{BC}(p, p_0), 0.0, 1.0\right)\right) \in [0, \arccos(1/\sqrt{5}) \approx 1.1071\text{ rad}]$$
5. **Riemannian Geodesic Pillar Harmony Regularizer**:
   $$H_{\text{Riemann}}(p) = \exp\left(-\zeta_R \cdot d_R(p, p_0)^2\right), \quad \zeta_R = 2.40$$
   $$\text{harmony\_factor}_{\text{v8}} = 1.0 + 0.30 \cdot H_{\text{Riemann}} \cdot \mathbf{1}_{\{\mu_\psi > 0.38\}}$$
6. **Geodesic-Weighted Tensor Contractions**:
   - Bilinear pairwise interactions: $\omega_{ij}^{\text{geo}} = \omega_{ij} \cdot (1.0 + 0.50 \sqrt{p_i p_j})$.
   - Core Triplet Multiplier $(\text{val}, \text{mom}, \text{flow})$: expanded from $1.40\times$ to **$1.50\times$**.
   - Secondary Triplet Multiplier $(\text{flow}, \text{cat}, \text{net})$: expanded from $1.20\times$ to **$1.25\times$**.
   - Maximum Cap in `BULL_LOW_VOL`: expanded from $0.220$ to **$0.250$** ($1.250\times$ max multiplier).
   - Maximum Cap in `CRISIS`: strictly preserved at **$0.040$** ($1.040\times$ max multiplier).

#### Proposed Interface & Implementation in `compute_quint_pillar_tensor_synergy`:
```python
# Feature F51.1: Information Geometry Riemannian Geodesic Pillar Mapping (version >= 8)
if version >= 8:
    p_vals = np.array([p_val.values, p_mom.values, p_flow.values, p_cat.values, p_net.values])  # shape (5, N)
    p_sum = np.sum(p_vals, axis=0, keepdims=True)
    p_norm = (p_vals + 1e-6) / (p_sum + 5e-6)  # Simplex S^4
    
    # Bhattacharyya Affinity BC(p, p0) with p0 = 0.20
    bc = np.sum(np.sqrt(0.20 * p_norm), axis=0)
    bc_clipped = np.clip(bc, 0.0, 1.0)
    d_riemann = np.arccos(bc_clipped)  # Geodesic distance on S^4
    
    h_riemann = np.exp(-2.40 * np.square(d_riemann))
    p_mean = np.mean(p_vals, axis=0)
    harmony_factor = pd.Series(
        1.0 + 0.30 * h_riemann * (p_mean > 0.38).astype(float),
        index=scores_df.index
    )
    # Geodesic-weighted confluence
    total_confluence = raw_confluence * harmony_factor
    reg_cap = 0.250 if 'BULL_LOW_VOL' in reg_str else (0.040 if 'CRISIS' in reg_str else reg_cap)
```

---

### 3.2 R1-2: Hyperexponential Convex Rank Modulation $g_{\text{v8}}(r) = r \cdot \exp(\gamma_{\text{top}} \cdot r^3)$

#### Mathematical Formulation
For assets with positive excess conviction ($z_{\text{denoised}} \ge 0.0$):
$$\text{mult}_{\text{v8}}(r) = 0.50 + 0.65 \cdot g_{\text{v8}}(r) = 0.50 + 0.65 \cdot r \cdot \exp\left(\gamma_{\text{top}}(R) \cdot r^3\right)$$
For assets with negative excess conviction ($z_{\text{denoised}} < 0.0$):
$$\text{mult}_{\text{v8}}(r) = 1.40 - 0.80 \cdot r$$

#### Mathematical Properties
1. **$C^\infty$ Smoothness**: Infinitely differentiable on $r \in [0, 1]$.
2. **Strict Monotonicity**:
   $$\frac{d}{dr} g_{\text{v8}}(r) = \left(1 + 3 \gamma_{\text{top}} r^3\right) \exp\left(\gamma_{\text{top}} r^3\right) > 0 \quad \forall r \in [0, 1], \gamma_{\text{top}} \ge 0$$
   Derivative is bounded below: $g'(r) \ge 1.0$ for all $r \ge 0$.
3. **Strict Convexity**:
   $$\frac{d^2}{dr^2} g_{\text{v8}}(r) = 3 \gamma_{\text{top}} r^2 \left(4 + 3 \gamma_{\text{top}} r^3\right) \exp\left(\gamma_{\text{top}} r^3\right) \ge 0$$
   $g''(r) > 0$ for all $r > 0$, guaranteeing strict convexity.
4. **Top 1% Alpha Spread Expansion**:
   Under $\gamma_{\text{top}} = 0.85$:
   - $g_{\text{v8}}(1.00) = 1.00 \cdot \exp(0.85) \approx 2.3396 \implies \text{mult} = 0.50 + 0.65(2.3396) = 2.0208$
   - $g_{\text{v8}}(0.90) = 0.90 \cdot \exp(0.85 \times 0.729) \approx 1.672 \implies \text{mult} = 0.50 + 0.65(1.672) = 1.5868$
   - Spread difference $\Delta_{\text{v8}} = 2.0208 - 1.5868 = 0.4340$
   - Phase 7 spread difference $\Delta_{\text{v7}} = 1.8500 - 1.5490 = 0.3010$
   - **Spread Expansion**: $\frac{0.4340 - 0.3010}{0.3010} = \mathbf{+44.19\%}$.

#### Regime-Adaptive $\gamma_{\text{top}}(R)$ Schedule:
```python
@classmethod
def get_regime_adaptive_gamma_top(
    cls,
    regime: Union[int, str] = 'BULL_LOW_VOL',
    version: int = 8
) -> float:
    """
    Returns regime-adaptive hyperexponential rank modulation parameter gamma_top(R).
    Higher values in Bull regimes accelerate top-percentile separation;
    conservative values in Crisis prevent spurious alpha explosion.
    """
    reg_str = str(regime).upper()
    if 'CRISIS' in reg_str:
        return 0.20
    elif 'BEAR_HIGH_VOL' in reg_str:
        return 0.25
    elif 'BEAR_LOW_VOL' in reg_str or reg_str == '0':
        return 0.35
    elif 'SIDEWAYS_HIGH_VOL' in reg_str:
        return 0.45
    elif 'SIDEWAYS_LOW_VOL' in reg_str or reg_str == '1':
        return 0.55
    elif 'BULL_HIGH_VOL' in reg_str:
        return 0.70
    elif 'BULL_LOW_VOL' in reg_str or reg_str == '2':
        return 0.85
    else:
        return 0.60
```

---

### 3.3 R1-3: Hurst Exponent ($H$) Fractional Jump-Diffusion & Asymmetric Wavelet Deadband

#### A. Fractional Jump-Diffusion Regime Weights
1. **Fractional Jump Indicator**:
   $$d_{\text{TV}} = \frac{1}{2} \sum_{s} |\pi_t(s) - \pi_{t-1}(s)|$$
   $$J_{\text{base}} = \text{clip}\left(\frac{d_{\text{TV}} - 0.25}{0.35}, 0.0, 1.0\right)$$
   $$J_{\text{frac}} = \text{clip}\left(J_{\text{base}} \cdot (2 H)^{1.50}, 0.0, 1.0\right)$$
   where $H \in [0.05, 0.95]$ is the market Hurst exponent (default $H = 0.50$).
   - When $H = 0.50$: $(2 \times 0.50)^{1.5} = 1.0 \implies J_{\text{frac}} = J_{\text{base}}$ (exact backward compatibility).
   - When $H = 0.70$ (strong trending memory): $J_{\text{frac}} = 1.656 \cdot J_{\text{base}}$ (accelerated jump protection).
   - When $H = 0.35$ (mean-reverting noise): $J_{\text{frac}} = 0.585 \cdot J_{\text{base}}$ (suppressing false alarms).
2. **Fractional Jump Weight Mixture**:
   $$\text{blend\_jump} = \min\left(0.85, 0.65 \cdot J_{\text{frac}}\right)$$
   $$w_{\text{Sovereign}} = (1 - \text{blend\_jump}) \cdot w_{\text{diffusion}} + \text{blend\_jump} \cdot W_{2D}(R_{\text{jump}})$$

#### B. Asymmetric Wavelet Noise Deadband Filter (Septic Kernel $\alpha = 7.0$)
1. **Mathematical Formulation**:
   $$z_{\text{wavelet}} = z \cdot \tanh\left(\left(\frac{|z|}{\delta_{\text{eff}}(z)}\right)^7\right)$$
   $$\delta_{\text{eff}}(z) = \begin{cases} \delta_{\text{neg}} = \delta_{\text{noise}} \cdot \chi_{\text{bear}} \cdot 1.10, & z < 0 \\ \delta_{\text{pos}} = \delta_{\text{noise}}, & z \ge 0 \end{cases}$$
2. **Noise Squashing Analysis**:
   At near-zero noise threshold $|z| = 0.010$ with $\delta = 0.045$:
   $$\text{ratio} = \frac{0.010}{0.045} = 0.22222$$
   $$\text{arg} = (0.22222)^7 = 0.00002667$$
   $$\text{Leakage} = \frac{|z_{\text{wavelet}}|}{0.010} = \tanh(0.00002667) \approx 0.002667\% \le \mathbf{0.010\%}$$
   **Noise Suppressed: $99.9973\% > 99.99\%$!**
3. **High Conviction Signal Transmission**:
   At conviction threshold $|z| = 0.150$ with $\delta = 0.045$:
   $$\text{ratio} = \frac{0.150}{0.045} = 3.3333$$
   $$\text{arg} = (3.3333)^7 = 4572.5$$
   $$\tanh(4572.5) = 1.0000000000000000000$$
   **Transmission: $100.0000\%$ with zero attenuation!**

---

## 4. Complete Inventory of Affected Code Locations

| File Path | Methods / Classes | Line Range | Changes for Phase 8 |
|-----------|-------------------|------------|----------------------|
| `trading_system/src/ai/ensemble_scorer.py` | `compute_quint_pillar_tensor_synergy` | 4570–4838 | Add `version >= 8` branch: Fisher-Rao geodesic distance $d_R(p, p_0)$, Riemannian harmony $H_{\text{Riemann}}$, geodesic-weighted contractions, cap expansion to 0.250 in Bull Low Vol. |
| `trading_system/src/ai/ensemble_scorer.py` | `combine_predictions` | 3478–3520 | Under `version >= 8`: call `apply_smooth_noise_deadband(..., version=8)` (septic deadband) and apply hyperexponential rank modulation $g_{\text{v8}}(r) = r \cdot \exp(\gamma_{\text{top}} r^3)$. |
| `trading_system/src/ai/ensemble_scorer.py` | `get_regime_adaptive_gamma_top` | New method (~5074) | Implement class method returning regime-specific $\gamma_{\text{top}} \in [0.20, 0.85]$. |
| `trading_system/src/ai/ensemble_scorer.py` | `get_base_weights` | 1215–1289 | Add Hurst exponent fractional jump-diffusion modulation $J_{\text{frac}} = J_{\text{regime}} \cdot (2H)^{1.5}$ when `version >= 8`. |
| `trading_system/src/ai/ensemble_scorer.py` | `get_regime_adaptive_half_lives` | 4205–4225 | Modulate Markov departure penalty with Hurst exponent $H$ under `version >= 8`. |
| `trading_system/src/ai/ensemble_scorer.py` | `apply_smooth_noise_deadband` | 5204–5260 | Under `version >= 8`: activate septic exponent $\alpha = 7.0$ via `apply_quintic_hyperbolic_deadband(..., alpha_pos=7.0)` or `apply_asymmetric_wavelet_deadband`. |
| `trading_system/src/ai/factor_suppression.py` | `apply_quintic_hyperbolic_deadband` / `apply_asymmetric_wavelet_deadband` | 44–100 | Support $\alpha = 7.0$ septic wavelet thresholding to achieve $< 0.003\%$ leakage (suppressing $99.997\%$ of noise). |
| `trading_system/src/ai/score_normalizer.py` | `CrossSectionalScoreNormalizer` | 182–281 | Verified: Preserves full floating-point precision in $[0.005, 0.995]$, providing optimal input resolution for $g_{\text{v8}}(r)$. No destructive edits required. |
| `tests/test_phase8_signal_enhancement.py` | New Test Suite | New (1–500) | Full unit and empirical stress tests for Features F51.1, F51.2, F52.1, F52.2, multi-market stress, and v6/v7 backward compatibility invariants. |

---

## 5. Unit Test Strategy for Phase 8

We specify a dedicated test suite `tests/test_phase8_signal_enhancement.py` containing 6 comprehensive test functions:

1. `test_feature_51_1_riemannian_manifold_geodesic_5pillar_mapping()`:
   - Verifies Bhattacharyya affinity coefficient $\text{BC}(p, p_0)$ and Fisher-Rao geodesic distance $d_R(p, p_0)$ on the unit 4-hypersphere.
   - Verifies Riemannian harmony factor $H_{\text{Riemann}} = \exp(-2.40 d_R^2)$: balanced 5-pillar asset receives $\sim 1.30\times$ boost; single-pillar asset collapses to $1.00\times$.
   - Strict hierarchy: $5\text{-Pillar} > 4\text{-Pillar} > 3\text{-Pillar} > 2\text{-Pillar} > 1\text{-Pillar} == \text{Baseline}$.
   - Bull Low Vol cap expands to $0.250$ ($1.250\times$), Crisis cap stays $\le 0.040$.
2. `test_feature_51_2_hyperexponential_convex_rank_modulation()`:
   - Verifies $g_{\text{v8}}(r) = r \cdot \exp(\gamma_{\text{top}} r^3)$ with regime-adaptive $\gamma_{\text{top}}$.
   - Verifies strict monotonicity: $\frac{d}{dr} g_{\text{v8}}(r) > 0$ across $r \in [0, 1]$.
   - Verifies top 1% spread expansion $\ge 25\%$ (target $+44.2\%$) relative to Phase 7 quartic $g_{\text{v7}}(r)$.
3. `test_feature_52_1_hurst_fractional_jump_diffusion_regime_weights()`:
   - Verifies fractional jump scaling: $J_{\text{frac}} = J_{\text{regime}} \cdot (2H)^{1.5}$.
   - At $H = 0.50$, $J_{\text{frac}} == J_{\text{regime}}$ (backward compatibility).
   - At $H = 0.70$ (trending), jump hedge allocation accelerates by $\sim 1.65\times$.
   - At $H = 0.35$ (chop), false jump alarm is attenuated by $>40\%$.
   - Simplex sum invariant: $\sum w_i == 1.0000$, all $w_i \ge 0$.
4. `test_feature_52_2_septic_wavelet_noise_deadband_9999_suppression()`:
   - Verifies near-zero noise leakage at $|z| = 0.010, \delta = 0.045$: leakage $\le 0.010\%$ ($0.0027\%$ target, suppressing **$99.997\%$** of noise).
   - Verifies 20-fold leakage reduction vs Phase 7 quintic deadband.
   - Verifies high-conviction signal transmission at $|z| = 0.150$: transmission $\ge 99.999\%$ ($100.0000\%$).
   - Verifies exact odd symmetry unconditioned: $f(-z) == -f(z)$ to within $10^{-12}$.
   - Verifies Spearman rank correlation $\rho_s == 1.0000$.
5. `test_feature_52_3_multi_market_5market_stress_v8()`:
   - Tests SP500, NASDAQ, RUSSELL2000, KOSPI, KOSDAQ across all 7 regimes under `version=8`.
   - Asserts 0 NaNs, 0 Infs in `ensemble_score` and `ensemble_expected_return`.
   - Asserts `ensemble_score` strictly in $[0.0, 1.0]$.
6. `test_feature_52_4_version_backward_compatibility_invariants()`:
   - Asserts passing `version=6` executes Phase 6 cubic logic and 0.180 cap.
   - Asserts passing `version=7` executes Phase 7 quartic logic, quintic deadband, and 0.220 cap.
   - Asserts passing `version=8` activates sovereign enhancements without breaking existing callers.

---

## 6. Self-Contained 5-Component Handoff Protocol

### 1. Observation
- Verified `trading_system/src/ai/ensemble_scorer.py`, `trading_system/src/ai/factor_suppression.py`, and `trading_system/src/ai/score_normalizer.py`.
- Phase 7 implementation contains:
  - F47.1 quint-pillar trilinear tensor and Euclidean $CV$ regularizer at lines 4581–4828.
  - F47.3 Merton jump-diffusion weight mixture at lines 1215–1285.
  - F48.1 directional Markov divergence penalty at lines 4205–4215.
  - F48.2 quintic deadband filter ($\alpha = 5.0$, $0.054\%$ leakage) at lines 5204–5225 and `factor_suppression.py` lines 44–100.
  - F48.3 quartic rank modulation $g_{\text{v7}}(r)$ at lines 3494–3501.
- Existing tests: Ran `.venv\Scripts\pytest.exe tests/test_phase7_signal_enhancement.py tests/test_benchmark_phase7.py tests/test_score_normalizer.py tests/test_adversarial_ensemble_scorer_challenger.py` — **43 tests executed and 100% passed**.

### 2. Logic Chain
- Step 1 (Observation 1.1A & 1.2): 5-pillar vector lives on $\mathcal{S}^4$ endowed with Fisher-Rao metric $\implies$ mapping to $\mathbb{S}^4$ via $u_k = \sqrt{p_k}$ yields true geodesic arc distance $d_R(p, p_0)$ $\implies$ regularizing via $H_{\text{Riemann}} = \exp(-2.40 d_R^2)$ eliminates Euclidean boundary distortion and geometrically rewards balanced 5-pillar confluence.
- Step 2 (Observation 1.1C): Top 1% alpha assets require steeper convexity than quartic polynomial $\implies$ hyperexponential modulation $g_{\text{v8}}(r) = r \cdot \exp(\gamma_{\text{top}} r^3)$ introduces an exponential acceleration term above the 90th percentile $\implies$ top alpha spread expands by $+44.2\%$ without inverting ranking ($g' > 0$).
- Step 3 (Observation 1.1B & 1.1E): Financial regimes exhibit fractal memory $\implies$ scaling jump total variation by $(2H)^{1.5}$ differentiates persistent macro trend shifts from transient chop $\implies$ septic wavelet deadband ($\alpha = 7.0$) drops leakage to $0.0027\%$, achieving institutional $99.99\%$ noise squashing.

### 3. Caveats
- When computing Hurst exponent $H$, market return series require at least 20 trading days for stable R/S calculation. If historical price data is unavailable, the model defaults to $H = 0.50$ (Brownian motion), seamlessly falling back to standard diffusion.
- The Riemannian distance function requires clipping $\text{BC}(p, p_0) \in [0.0, 1.0]$ before taking $\arccos$ to prevent floating-point NaN when $\text{BC} > 1.0 + 10^{-16}$.

### 4. Conclusion
The Phase 8 Sovereign Quantitative Enhancement architecture for Milestone 1 (Signal & Alpha Architecture) is fully formulated, mathematically proven, and ready for clean, backward-compatible implementation in `ensemble_scorer.py` and `factor_suppression.py`.

### 5. Verification Method
- Execute the test command:
  ```bash
  .venv/Scripts/pytest tests/test_phase7_signal_enhancement.py tests/test_benchmark_phase7.py tests/test_score_normalizer.py tests/test_adversarial_ensemble_scorer_challenger.py -v
  ```
- Post-implementation verification: run the new test suite `tests/test_phase8_signal_enhancement.py` verifying all assertions for F51.1, F51.2, F52.1, and F52.2.
- Inspect `trading_system/src/ai/ensemble_scorer.py` lines 4570–4838 and lines 3478–3520 to verify parameter branching on `version >= 8`.
