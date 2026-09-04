# Phase 5 Technical Specification & Forensic Investigation: Requirement R1
# 37-Strategy Dynamic Alpha Signal Quality & Top Alpha Identification 5th Maximization (Features F35, F36)

**Author**: Explorer 1 (`explorer_survey_1`)  
**Date**: 2026-09-04  
**Target Version**: Phase 5 Deep Quantitative Enhancement  
**Scope**: Requirement R1 (Features F35, F36) across 37 Multi-Factor Strategies & 5 Operating Equity Markets (KOSPI, KOSDAQ, S&P 500, NASDAQ, RUSSELL 2000)

---

## 1. Executive Summary

In Phase 4 (v11 Apex), the trading system achieved landmark performance improvements:
- **Net Expected Return**: 36.20% $\to$ **42.00% (+5.80%p / +16.0%)**
- **Annualized Sharpe Ratio**: 3.81 $\to$ **4.42 (+0.61 / +16.0%)**
- **Spearman Rank-IC**: 0.141 $\to$ **0.168 (+0.027 / +19.1%)**
- **Top-Decile Alpha Spread**: 19.3% $\to$ **24.8% (+5.5%p / +28.5%)**

This was unlocked by solving the historical 0.833 alpha compression bottleneck (Feature F21), introducing softplus continuous conviction gating (F22), tri-linear synergy confluence (F23), sideways 2D regime rebalancing (F24), Kaufman Trend Efficiency dynamic switching (F25), asymmetric half-life decay (F26), and regime-adaptive Bessembinder tail thresholds (F27).

For **Phase 5 Deep Quantitative Enhancements**, Requirement R1 mandates advancing dynamic signal quality and top alpha identification to its 5th maximization level:
1. **Feature F35**: High-Order Non-Linear Alpha Interaction & Right-Tail Convexity Expansion.
   - Objective: Further expand top-decile alpha spread (targeting $\ge 28.5\%$, Net Expected Return $\ge 46.5\%$, Sharpe $\ge 4.85$) while preserving **strict monotonic rank order** ($\rho_s = 1.0000$) and avoiding premature saturation.
   - Mathematical mechanism: Regime-adaptive Richards right-tail curvature ($\gamma_{\text{tail}}(R) \in [1.00, 1.30]$), quadratic rank modulation ($0.60 + 0.50 r + 0.50 r^2$), Quad-Pillar confluence kernel ($\Xi_{\text{quad}} = \Omega_{\text{quad}} \cdot \psi_{\text{val}} \psi_{\text{mom}} \psi_{\text{flow}} \psi_{\text{cat}}$) with regime-adaptive synergy caps (up to 1.15x in Bull Low Vol), Hölder $p=2.0$ quadratic mean top-$k$ boosting, and asymmetric Bessembinder tail scaling ($\eta_{\text{right}} = 2.0$).
2. **Feature F36**: Regime Transition Uncertainty & Entropy Noise Filtering.
   - Objective: Suppress whipsaw losses and turnover friction in sideways/turbulent markets and during regime shifts.
   - Mathematical mechanism: Transition matrix Shannon entropy $H_{\text{norm}}(\boldsymbol{\pi})$ and Total Variation jump penalty $d_{\text{TV}}$ modulating strategy half-life decay ($\phi_{\text{entropy}} \cdot \phi_{\text{jump}}$), continuous probabilistic regime half-life expectation ($\sum \pi_m \tau_k(R_m)$), and a $C^\infty$-smooth hyperbolic tangent deadzone soft-thresholding filter ($z \cdot \tanh((|z|/\delta_{\text{noise}})^3)$) that squashes near-0.50 Brownian noise by $> 85\%$ while maintaining 100% transmission for high-conviction signals ($|s - 0.50| \ge 0.15$).

---

## 2. Forensic Code Audit & Phase 4 Baseline Analysis

### 2.1 File & Module Inventory
The core files investigated include:
- `trading_system/src/ai/ensemble_scorer.py` (4,283 lines, 229,466 bytes): Primary orchestration for 37-strategy score normalization, 2D regime weighting, synergy kernels, Bessembinder power laws, and return conversion.
- `trading_system/src/ai/score_normalizer.py` (282 lines, 14,235 bytes): Cross-sectional Gaussian CDF and percentile ranking with sparse factor zero-isolation.
- `trading_system/src/ai/factor_suppression.py` (452 lines, 19,877 bytes): Collinearity suppression cutoff $\theta(R, N)$ with Fisher $z$-calibration and single-stage entropy program.
- `trading_system/src/ai/factor_orthogonalizer.py` (592 lines, 24,711 bytes): PCA-ZCA symmetric whitening and Gram-Schmidt decorrelation with consensus PC1/PC2 preservation.
- `tests/test_phase4_signal_enhancement.py` (418 lines, 19,093 bytes): 8 comprehensive unit and property tests verifying Phase 4 signal enhancements (100% pass in 13.78s).

---

### 2.2 Forensic Inspection of Key Methods in `ensemble_scorer.py`

#### A. The 0.833 Ceiling Unlock & Current Return Transformation (Lines 3275–3295)
```python
# Lines 3275-3285 in ensemble_scorer.py
ens_scores = merged['ensemble_score'].values
abs_centered = np.clip(ens_scores - 0.50, -0.50, 0.50)
if len(ens_scores) >= 5:
    ranks = pd.Series(ens_scores).rank(pct=True).values
    # Phase 4 (F21): Rank-modulated dynamic scaling without premature 0.50 clipping
    mult = np.where(abs_centered >= 0.0, 0.60 + 0.80 * ranks, 1.40 - 0.80 * ranks)
    unclipped_score = abs_centered * mult
else:
    unclipped_score = abs_centered
# Phase 4 (F21): Power-law convex transformation restoring steep right-tail curvature for top decile
convex_alpha = np.sign(unclipped_score) * np.clip((np.abs(unclipped_score * 2.0) ** 1.15) / 1.15, 0.0, 1.0)
```
- **How Phase 4 unlocked the ceiling**:
  Prior to Phase 4, the code executed:
  `unclipped_score = np.clip(abs_centered * mult, -0.50, 0.50)`
  For top-decile stocks, `ens_score` reached $\ge 0.8333 \implies \text{abs\_centered} \ge 0.3333$.
  With $\text{rank} = 1.0 \implies \text{mult} = 1.40$ (or 1.50 in earlier code):
  $0.3333 \times 1.50 = 0.500$.
  All stocks with score $\ge 0.8333$ were clipped at 0.50. When scaled by 2.0, $(0.50 \times 2.0) = 1.0$.
  Consequently, all top-decile stocks (0.84, 0.88, 0.92, 0.96) collapsed onto an identical flat plateau with `convex_alpha = 1.0 / 1.15 = 0.869` or 1.0.
  Phase 4 removed the premature clipping, allowing `unclipped_score` to reach $0.47 \times 1.40 = 0.658$, so $(0.658 \times 2.0)^{1.15} / 1.15 = 1.000$ (smooth saturation at score 0.97, with strictly separated values for 0.85, 0.89, 0.93, 0.97).
- **Phase 5 Bottleneck Identified**:
  1. The exponent `1.15` is static across all market regimes. In strong trending bull markets (`BULL_LOW_VOL`), momentum persistence is high and right-tail alpha spread can safely expand to higher curvature ($\gamma \ge 1.30$). In contrast, in `CRISIS` or `BEAR_HIGH_VOL`, a 1.15 power exponent over-amplifies long conviction into adverse drawdowns.
  2. The rank multiplier is purely linear: $\text{mult} = 0.60 + 0.80 \cdot r$. A linear rank slope treats the jump from the 40th to 50th percentile with the exact same marginal multiplier (+0.08) as the jump from the 90th to 100th percentile (+0.08). In quantitative finance (Grinold-Kahn), the top 5% of signals contain exponential information density.

---

#### B. Continuous Bilinear Cross-Pillar Synergy Kernel (Lines 4030–4166)
```python
# Lines 4057-4079 in ensemble_scorer.py
clusters = {
    'val': ['rim_score', 'valueup_catalyst_score', 'accruals_quality_score', 'arm_score', 'factor_neutralized_score', 'reg_score'],
    'mom': ['surge_score', 'vcp_ml_score', 'trend_efficiency_score', 'sector_score', 'range_expansion_score', 'mq_score', 'll_score', 'vcp_rule_score', 'lstm_score'],
    'flow': ['order_flow_score', 'inst_foreign_sector_score', 'darkpool_score', 'microstructure_score', 'overnight_gap_score', 'stat_arb_score', 'iv_skew_score', 'reversal_score', 'vol_target_score'],
    'cat': ['event_score', 'sentiment_score', 'short_squeeze_score', 'gamma_squeeze_score', 'supply_chain_score', 'supply_chain_gnn_score', 'cross_asset_spillover_score', 'dual_correction_score', 'index_rebalance_score', 'insider_buying_score', 'earnings_tone_drift_score', 'card_score', 'latr_score']
}
# Lines 4160-4165:
tri_confluence = omega_tri * (pillar_convictions['val'] * pillar_convictions['mom'] * pillar_convictions['flow'])
synergy_multiplier = 1.0 + (synergy_sum + tri_confluence).clip(0.0, 0.100)
```
- **Phase 5 Bottleneck Identified**:
  1. The 4th pillar (`cat` = Catalysts) contains the most critical event and timing triggers (DART filings, earnings tone drift, insider buying, supply chain shocks, range expansion breakouts). Yet `cat` is completely excluded from tri-linear confluence!
  2. When an asset displays simultaneous strength across all 4 pillars (**Valuation + Momentum + Flow + Catalyst**), it represents the pinnacle institutional alpha setup (e.g. undervalued firm with insider accumulation, momentum breakout, and positive earnings catalyst). Currently, it receives no quad-factor bonus.
  3. The synergy cap of `0.100` (1.10x) is rigid across regimes, artificially constraining high-conviction names in `BULL_LOW_VOL` while being too permissive in `CRISIS`.

---

#### C. Top-Decile Convex Boost (Lines 1683–1718)
```python
# Lines 1708-1718 in ensemble_scorer.py
if vals.shape[1] >= top_k:
    top_k_vals = np.partition(vals, -top_k, axis=1)[:, -top_k:]
    top_k_mean = np.mean(top_k_vals, axis=1)
else:
    top_k_mean = np.mean(vals, axis=1)

gate_arg = np.clip(15.0 * (top_k_mean - 0.60), -20.0, 20.0)
gate_weight = 1.0 / (1.0 + np.exp(-gate_arg))
boosted = (1.0 - lambda_boost * gate_weight) * base_scores.values + (lambda_boost * gate_weight) * top_k_mean
```
- **Phase 5 Bottleneck Identified**:
  1. `top_k_mean` uses an arithmetic mean ($p=1.0$). If a stock has an extraordinary surge score of 0.98, but the 2nd and 3rd rank factors are 0.65 and 0.62, the arithmetic average is 0.75, penalizing the peak conviction.
  2. `lambda_boost` is hardcoded at 0.35 across all 7 regimes. In Bull regimes, a higher boost ($\lambda = 0.40$) is warranted, whereas in Bear/Crisis, $\lambda$ should be dialed back to $0.20$ to prevent false breakout whipsaws.

---

#### D. Bessembinder Tail Thresholding & S-Curve Scaling (Lines 4174–4283)
```python
# Lines 4272-4281 in ensemble_scorer.py
u = np.clip(2.0 * (arr - 0.50), -1.0, 1.0)
abs_u = np.abs(u)
excess = np.maximum(0.0, (abs_u - eff_u_thresh) / max(1e-4, 1.0 - eff_u_thresh))
tail_boost = 1.0 + eff_beta * np.power(excess, eta)
u_tilde = np.sign(u) * np.power(abs_u, eff_gamma) * tail_boost
scale = max(1.0 + eff_beta, float(np.max(np.abs(u_tilde)))) if len(u_tilde) > 0 else (1.0 + eff_beta)
rescaled = 0.50 + 0.50 * (u_tilde / max(scale, 1e-4))
```
- **Phase 5 Bottleneck Identified**:
  1. $\eta = 1.60$ is symmetric for both upside and downside tails. However, right-tail distribution in stock returns exhibits positive skewness and kurtosis (fat right tail). Right-tail acceleration should feature higher curvature ($\eta_{\text{right}} = 2.0$) in Bull regimes.
  2. `u_thresh` in `BULL_LOW_VOL` is 0.45. By lowering it to 0.40, the top 15% of stocks begin entering the convex amplification zone earlier, broadening top-decile dispersion.

---

#### E. Dynamic Half-Life Decay & Transition Uncertainty (Lines 3813–3870)
```python
# Lines 3813-3837 in ensemble_scorer.py
@classmethod
def get_regime_adaptive_half_lives(
    cls,
    regime: Union[int, str] = 'SIDEWAYS_LOW_VOL'
) -> Dict[str, float]:
    reg_str = str(regime).upper()
    if 'CRISIS' in reg_str:
        kappa_regime = 0.30
    elif 'BEAR_HIGH_VOL' in reg_str: ...
```
- **Phase 5 Bottleneck Identified**:
  1. `get_regime_adaptive_half_lives` only accepts a discrete regime label. When passed a Markov posterior distribution $\boldsymbol{\pi} = \{\text{state}: \text{prob}\}$, it converts the dictionary to a string, fails all regime substrings, and falls back to $\kappa_{\text{regime}} = 1.00$.
  2. Regime transition uncertainty (Shannon entropy $H(\boldsymbol{\pi})$) and jump magnitude ($d_{\text{TV}}$) are not incorporated into half-life calculation. During a messy transition from Bull to High Vol, older trend signals linger too long, creating severe whipsaw losses.

---

#### F. Noise in Sideways/Turbulent Regimes
In sideways and turbulent regimes, dozens of stocks have scores in the neutral band $s \in [0.47, 0.53]$.
Currently, these near-zero alphas are converted directly to expected returns:
$(0.51 - 0.50) \times \text{mult} \times \text{multiplier} \approx +0.8\% \sim +1.2\%$.
In aggregate, these Brownian fluctuations cause the portfolio optimizer (Black-Litterman, HERC, CVaR) to rebalance minor position shifts, racking up SEC fees, STT tax, and bid-ask spread drag.

---

## 3. Mathematical Specifications for Phase 5 Enhancements

### 3.1 Feature F35: High-Order Non-Linear Alpha Interaction & Right-Tail Convexity Expansion

#### Mathematical Component 1: Regime-Adaptive Richards Right-Tail Exponent $\gamma_{\text{tail}}(R)$ & Quadratic Rank Modulation
In `combine_predictions()`, replace the static 1.15 exponent and linear rank multiplier with:
1. **Regime-Adaptive Right-Tail Exponent**:
   $$\gamma_{\text{tail}}(R) = \begin{cases}
   1.30, & \text{if } R = \text{BULL\_LOW\_VOL} \\
   1.22, & \text{if } R = \text{BULL\_HIGH\_VOL} \\
   1.15, & \text{if } R = \text{SIDEWAYS\_LOW\_VOL} \\
   1.10, & \text{if } R = \text{SIDEWAYS\_HIGH\_VOL} \\
   1.08, & \text{if } R = \text{BEAR\_LOW\_VOL} \\
   1.00, & \text{if } R \in \{\text{BEAR\_HIGH\_VOL}, \text{CRISIS}\}
   \end{cases}$$
2. **Quadratic Rank Modulation for Positive Conviction**:
   For centered score $z = s - 0.50 \ge 0$ and cross-sectional rank $r \in [0.0, 1.0]$:
   $$\text{mult}(r, R) = \begin{cases}
   0.60 + 0.50 \cdot r + 0.50 \cdot r^2, & \text{if } R \in \{\text{BULL\_LOW\_VOL}, \text{BULL\_HIGH\_VOL}\} \quad (\text{at } r=1, \text{mult}=1.60) \\
   0.60 + 0.80 \cdot r, & \text{otherwise} \quad (\text{at } r=1, \text{mult}=1.40)
   \end{cases}$$
   For negative conviction ($z < 0$): $\text{mult}(r) = 1.40 - 0.80 \cdot r$.
3. **Convex Alpha Mapping**:
   $$\alpha_{\text{convex}}(u) = \text{sign}(u) \cdot \min\left(1.0, \frac{|2u|^{\gamma_{\text{tail}}(R)}}{\gamma_{\text{tail}}(R)}\right)$$
   where $u = z \cdot \text{mult}(r, R)$.
   - **Monotonicity Invariant Proof**:
     Let $s_1 > s_2 \ge 0.50 \implies z_1 > z_2 \ge 0$ and $r_1 > r_2$.
     Since $\text{mult}(r)$ is strictly increasing in $r$ ($\frac{d}{dr}\text{mult} = 0.50 + 1.00 r > 0$ for $r \ge 0$), $u(s_1) > u(s_2) \ge 0$.
     Since $f(x) = \frac{x^\gamma}{\gamma}$ has $f'(x) = x^{\gamma - 1} > 0$ for all $x > 0, \gamma \ge 1.0$, the composite function is strictly monotonic:
     $$s_1 > s_2 \implies \alpha_{\text{convex}}(s_1) > \alpha_{\text{convex}}(s_2)$$
     Rank correlation $\rho_s = 1.0000$ is preserved across the entire range $[0.0, 1.0]$.

---

#### Mathematical Component 2: Quad-Pillar Confluence Kernel ($\Xi_{\text{quad}}$) & Catalyst Synergy
In `compute_bilinear_cross_pillar_synergy()`, enhance the multi-pillar kernel:
1. **Quad-Pillar Confluence Term**:
   $$\Xi_{\text{quad}} = \Omega_{\text{quad}}(R) \cdot \left( \psi_{\text{val}} \cdot \psi_{\text{mom}} \cdot \psi_{\text{flow}} \cdot \psi_{\text{cat}} \right)$$
2. **Tri-Pillar Catalyst Confluence Term**:
   $$\Xi_{\text{tri,cat}} = \Omega_{\text{tri,cat}}(R) \cdot \left( \psi_{\text{mom}} \cdot \psi_{\text{flow}} \cdot \psi_{\text{cat}} \right)$$
3. **Regime Coupling Matrix Parameters**:
   | Regime | $\Omega_{\text{quad}}$ | $\Omega_{\text{tri,cat}}$ | $\Omega_{\text{tri}}$ (Val-Mom-Flow) | Synergy Cap $\text{Cap}(R)$ | Max Multiplier |
   |---|---|---|---|---|---|
   | `BULL_LOW_VOL` | 0.050 | 0.025 | 0.030 | **0.150** | **1.150x** |
   | `BULL_HIGH_VOL` | 0.035 | 0.015 | 0.020 | **0.125** | **1.125x** |
   | `SIDEWAYS_LOW_VOL` | 0.020 | 0.010 | 0.015 | **0.100** | **1.100x** |
   | `SIDEWAYS_HIGH_VOL` | 0.000 | 0.000 | 0.000 | **0.060** | **1.060x** |
   | `BEAR_LOW_VOL` | 0.010 | 0.005 | 0.005 | **0.075** | **1.075x** |
   | `BEAR_HIGH_VOL` | 0.000 | 0.000 | 0.000 | **0.040** | **1.040x** |
   | `CRISIS` | 0.000 | 0.000 | 0.000 | **0.040** | **1.040x** |

   Total synergy multiplier:
   $$\text{Mult}_{\text{synergy}} = 1.0 + \min\left(\text{Cap}(R), \sum_{p < q} \Omega_{pq} \psi_p \psi_q + \Xi_{\text{tri}} + \Xi_{\text{tri,cat}} + \Xi_{\text{quad}} \right)$$
   Strictly bounded in $[1.00, 1.0 + \text{Cap}(R)]$.

---

#### Mathematical Component 3: Hölder Quadratic Mean Top-Decile Convex Boost
In `apply_top_decile_convex_boost()`, enhance the top-$k$ aggregation from arithmetic mean ($p=1.0$) to **Hölder Quadratic Mean ($p=2.0$)**:
$$M_{p=2}(S_{\text{top\_k}}) = \sqrt{\frac{1}{K} \sum_{k=1}^K S_{(k)}^2}$$
And parameterize $\lambda_{\text{boost}}$ by regime:
$$\lambda_{\text{boost}}(R) = \begin{cases}
0.40, & \text{if } R \in \{\text{BULL\_LOW\_VOL}, \text{BULL\_HIGH\_VOL}\} \\
0.35, & \text{if } R = \text{SIDEWAYS\_LOW\_VOL} \\
0.25, & \text{if } R \in \{\text{SIDEWAYS\_HIGH\_VOL}, \text{BEAR\_LOW\_VOL}\} \\
0.20, & \text{if } R \in \{\text{BEAR\_HIGH\_VOL}, \text{CRISIS}\}
\end{cases}$$
The smooth sigmoid gate remains continuous:
$$\text{gate\_weight} = \frac{1}{1 + \exp(-15.0 \cdot (M_2 - 0.60))}$$
$$S_{\text{boosted}} = (1 - \lambda_{\text{boost}}(R) \cdot \text{gate\_weight}) \cdot S_{\text{base}} + (\lambda_{\text{boost}}(R) \cdot \text{gate\_weight}) \cdot M_2$$
Bounded strictly in $[0.0, 1.0]$.

---

#### Mathematical Component 4: Asymmetric Bessembinder Richards Scaling
In `apply_bessembinder_convex_power_law()`:
1. Apply asymmetric tail curvature exponent:
   $$\eta(u) = \begin{cases}
   2.0, & \text{if } u > 0 \text{ and } R \in \{\text{BULL\_LOW\_VOL}, \text{BULL\_HIGH\_VOL}, \text{SIDEWAYS\_LOW\_VOL}\} \\
   1.60, & \text{otherwise}
   \end{cases}$$
2. Update regime-adaptive parameters in `get_regime_adaptive_bessembinder_params()`:
   - `BULL_LOW_VOL`: $(\gamma=1.75, \beta=0.55, u_{\text{thresh}}=0.40)$
   - `BULL_HIGH_VOL`: $(\gamma=1.60, \beta=0.48, u_{\text{thresh}}=0.50)$
   - `SIDEWAYS_LOW_VOL`: $(\gamma=1.45, \beta=0.40, u_{\text{thresh}}=0.58)$
   - `SIDEWAYS_HIGH_VOL`: $(\gamma=1.35, \beta=0.30, u_{\text{thresh}}=0.70)$
   - `BEAR_LOW_VOL`: $(\gamma=1.30, \beta=0.30, u_{\text{thresh}}=0.65)$
   - `BEAR_HIGH_VOL`: $(\gamma=1.20, \beta=0.20, u_{\text{thresh}}=0.70)$
   - `CRISIS`: $(\gamma=1.20, \beta=0.20, u_{\text{thresh}}=0.78)$

---

### 3.2 Feature F36: Regime Transition Uncertainty & Entropy Noise Filtering

#### Mathematical Component 1: Continuous Probabilistic Regime Half-Life Expectation with Entropy & Jump Penalties
In `get_regime_adaptive_half_lives()`:
Accept `regime: Union[int, str, Dict[str, float]]` and optional `regime_probs: Optional[Dict[str, float]]`.
1. **Regime Expectation**:
   If $\boldsymbol{\pi} = (\pi_1, \dots, \pi_M)$ is provided:
   $$\bar{\tau}_k(\boldsymbol{\pi}) = \sum_{m=1}^M \pi_m \tau_k(R_m)$$
2. **Shannon Transition Entropy Penalty**:
   $$H(\boldsymbol{\pi}) = - \sum_{m=1}^M \pi_m \ln(\pi_m + 10^{-12})$$
   $$H_{\text{norm}}(\boldsymbol{\pi}) = \frac{H(\boldsymbol{\pi})}{\ln(M)} \in [0.0, 1.0]$$
   $$\phi_{\text{entropy}}(\boldsymbol{\pi}) = \exp\left( - 0.35 \cdot H_{\text{norm}}(\boldsymbol{\pi})^2 \right)$$
3. **Total Variation Jump Penalty**:
   If historical $\boldsymbol{\pi}_{t-1}$ is tracked:
   $$d_{\text{TV}} = \frac{1}{2} \sum_{m=1}^M |\pi_{m, t} - \pi_{m, t-1}| \in [0.0, 1.0]$$
   $$\phi_{\text{jump}}(d_{\text{TV}}) = \exp\left( - 0.50 \cdot \max(0.0, d_{\text{TV}} - 0.25) \right)$$
4. **Effective Half-Life**:
   $$\tau_k^*(\boldsymbol{\pi}) = \max\left( 0.10, \text{round}\left( \bar{\tau}_k(\boldsymbol{\pi}) \cdot \phi_{\text{entropy}}(\boldsymbol{\pi}) \cdot \phi_{\text{jump}}(d_{\text{TV}}), 2 \right) \right)$$

---

#### Mathematical Component 2: Continuous Hyperbolic Tangent Noise Deadband Soft-Thresholding
In `combine_predictions()`, before applying rank modulation and return conversion, apply continuous smooth soft-thresholding to centered scores $z = s - 0.50$:
1. **Regime-Adaptive Noise Deadband $\delta_{\text{noise}}(R, \boldsymbol{\pi})$**:
   $$\delta_{\text{noise}}(R, \boldsymbol{\pi}) = \delta_0(R) \cdot \left( 1.0 + 0.50 \cdot H_{\text{norm}}(\boldsymbol{\pi}) \right)$$
   Where $\delta_0(R)$:
   - `BULL_LOW_VOL`: $0.020$
   - `BULL_HIGH_VOL`: $0.035$
   - `SIDEWAYS_LOW_VOL`: $0.045$
   - `SIDEWAYS_HIGH_VOL`: $0.060$
   - `BEAR_LOW_VOL`: $0.040$
   - `BEAR_HIGH_VOL`: $0.055$
   - `CRISIS`: $0.070$
2. **$C^\infty$-Smooth Non-Linear Attenuation**:
   $$z_{\text{denoised}} = z \cdot \tanh\left( \left( \frac{|z|}{\delta_{\text{noise}}} \right)^3 \right)$$
   - **Properties**:
     * Zero-point stability: $z = 0 \implies z_{\text{denoised}} = 0$.
     * Strong signal preservation: for $|z| \ge 0.15$ with $\delta = 0.05$, $(0.15/0.05)^3 = 27 \implies \tanh(27) = 1.00000000$, resulting in $0.0000\%$ attenuation.
     * Noise elimination: for $|z| = 0.01$ with $\delta = 0.05$, $(0.01/0.05)^3 = 0.008 \implies \tanh(0.008) \approx 0.008$, attenuating Brownian noise by **99.2%**.
     * Strictly monotonic:
       $$\frac{d z_{\text{denoised}}}{dz} = \tanh(u) + 3u \cdot \text{sech}^2(u) > 0 \quad \text{where } u = \left(\frac{z}{\delta}\right)^3 \ge 0$$
       Guarantees $\rho_s = 1.0000$ across all assets.

---

## 4. Pipeline Integration & Cross-Module Interactions

### 4.1 Upstream: `score_normalizer.py`
- `CrossSectionalScoreNormalizer` standardizes raw factor scores into the range $[0.005, 0.995]$ via Winsorized Gaussian CDF ($\Phi(Z)$) and uniform percentile ranks.
- `_normalize_matrix()` isolates exact zeros on sparse factors ($N \ge 4$), ensuring inactive factors don't receive negative $Z$-scores.
- **Phase 5 Compatibility**: All Phase 5 non-linear kernels in `ensemble_scorer.py` receive standardized, outlier-resistant $[0.005, 0.995]$ inputs.

### 4.2 Midstream: `factor_suppression.py` and `factor_orthogonalizer.py`
- `RegimeFactorSuppressionEngine` applies Fisher $z$-sample-calibrated correlation thresholds $\theta(R, N)$ and single-stage convex entropy allocation:
  $$\min_{\mathbf{w}} \left[ \frac{1}{2} \mathbf{w}^T \mathbf{R} \mathbf{w} - \tau_{\text{entropy}} \sum_i \ln(w_i) + \gamma_{\text{anchor}} \|\mathbf{w} - \mathbf{w}_0\|^2 \right]$$
- `FactorOrthogonalizerEngine` decorrelates score matrices via PCA-ZCA whitening while preserving `top_k=2` consensus leading eigenvalues.
- **Phase 5 Compatibility**: Collinearity suppression and orthogonalization occur *prior* to dynamic ensemble scoring, feeding clean orthogonal signals into the Quad-Pillar kernel and Hölder convex boost.

### 4.3 Downstream: Portfolio Allocator & Execution OMS
- The Phase 5 expanded right-tail alpha spread directly feeds `UnifiedPortfolioAllocator` (Sortino EVT-CVaR + Black-Litterman + HERC).
- The noise deadband filtering suppresses spurious turnover around neutral names, allowing Leland buffer bands (25 bps KRX / 8 bps US) to operate with even greater friction efficiency.

---

## 5. Concrete Parameter Proposals for Phase 5 (F35, F36)

| # | Feature | Parameter Name | Location in Code | Phase 4 Value | Phase 5 Proposed Value | Quantitative Rationale |
|---|---|---|---|---|---|---|
| 1 | **F35** | `gamma_tail` | `ensemble_scorer.py:3285` | Static 1.15 | Regime-Adaptive: Bull Low 1.30, Bull High 1.22, Sideways Low 1.15, Sideways High 1.10, Bear 1.08, Crisis 1.00 | Maximizes right-tail alpha spread in persistent bull regimes while maintaining conservative discipline during market stress. |
| 2 | **F35** | `mult` (Rank modulation) | `ensemble_scorer.py:3280` | Linear $0.60 + 0.80 r$ | Quadratic in Bull: $0.60 + 0.50 r + 0.50 r^2$ | Steepens convexity for top 5% percentiles ($r \ge 0.95 \implies \text{mult} \to 1.60$). |
| 3 | **F35** | Quad-Pillar Confluence $\Omega_{\text{quad}}$ | `ensemble_scorer.py:4104` | Not present (0.0) | Bull Low: 0.050, Bull High: 0.035, Sideways Low: 0.020, Bear Low: 0.010, High Vol/Crisis: 0.000 | Rewards rare 4-factor alignment (Valuation + Momentum + Flow + Catalyst). |
| 4 | **F35** | Tri-Catalyst Confluence $\Omega_{\text{tri,cat}}$ | `ensemble_scorer.py:4104` | Not present (0.0) | Bull Low: 0.025, Bull High: 0.015, Sideways Low: 0.010, Bear Low: 0.005, High Vol/Crisis: 0.000 | Rewards momentum and order flow validated by positive catalysts. |
| 5 | **F35** | Synergy Cap | `ensemble_scorer.py:4164` | Static 0.100 (1.10x) | Bull Low: 0.150, Bull High: 0.125, Sideways Low: 0.100, Sideways High: 0.060, Bear: 0.075, Crisis: 0.040 | Allows top alpha names in bull markets to expand conviction up to 1.15x. |
| 6 | **F35** | Top-$k$ Aggregation Norm | `ensemble_scorer.py:1708` | Arithmetic Mean ($p=1.0$) | Hölder Quadratic Mean ($p=2.0$) | Preserves peak single-factor conviction from being diluted by the 3rd rank factor. |
| 7 | **F35** | `lambda_boost` | `ensemble_scorer.py:1688,3222` | Static 0.35 | Bull: 0.40, Sideways: 0.35, Bear/Crisis: 0.20 | Stronger convex alpha concentration in trending markets. |
| 8 | **F35** | Asymmetric Richards $\eta_{\text{right}}$ | `ensemble_scorer.py:4221` | Static 1.60 | Upside: 2.0 (Bull/Sideways), Downside: 1.60 | Asymmetric right-tail expansion reflecting empirical positive skewness. |
| 9 | **F35** | Bessembinder $u_{\text{thresh}}$ | `ensemble_scorer.py:4182` | Bull Low: 0.45, Crisis: 0.75 | Bull Low: 0.40, Bull High: 0.50, Sideways Low: 0.58, Sideways High: 0.70, Crisis: 0.78 | Lowers entry threshold in bull markets so top 15% begin experiencing convex boost. |
| 10 | **F36** | Probabilistic Half-Life Blending | `ensemble_scorer.py:3813` | Discrete lookup only | Accepts `regime_probs`, computes expectation $\sum \pi_m \tau_k(R_m)$ | Continuous half-life transitions across probabilistic regime distributions. |
| 11 | **F36** | Transition Entropy Penalty $\phi_{\text{entropy}}$ | `ensemble_scorer.py:3859` | None | $\exp(-0.35 \cdot H_{\text{norm}}^2)$ | Accelerates factor decay when regime transition ambiguity is elevated. |
| 12 | **F36** | TV Jump Penalty $\phi_{\text{jump}}$ | `ensemble_scorer.py:3859` | None | $\exp(-0.50 \cdot \max(0, d_{\text{TV}} - 0.25))$ | Rapidly compresses half-lives upon sudden macro regime transitions. |
| 13 | **F36** | Smooth Noise Deadzone $\delta_{\text{noise}}$ | `ensemble_scorer.py:3275` | None | $z \cdot \tanh((|z|/\delta_{\text{noise}})^3)$ with $\delta_0 \in [0.02, 0.07]$ | Attenuates near-0.50 Brownian noise in sideways/turbulent markets by $>85\%$. |

---

## 6. Test Design & Acceptance Verification Plan

To verify Phase 5 R1 without regressing any of the 2,351 existing tests:
1. **Test 1: Top-Decile Alpha Spread 5th Expansion (`test_feature_35_top_decile_spread_5th_expansion`)**:
   - Verify that in `BULL_LOW_VOL`, the top-decile return spread expands significantly over Phase 4 baseline.
   - Verify that all top-decile expected returns are strictly monotonic ($\Delta \text{ret} > 0.06$).
   - Verify that Spearman rank correlation equals $1.0000$.
2. **Test 2: Quad-Pillar & Catalyst Confluence Kernel (`test_feature_35_quad_pillar_synergy_kernel`)**:
   - Create assets with 1, 2, 3, and 4 pillar strength.
   - Assert that 4-pillar asset receives higher synergy multiplier than 3-pillar asset.
   - Verify that in `BULL_LOW_VOL`, synergy multiplier reaches up to $1.15$, while in `CRISIS` it is strictly capped at $1.04$.
   - Verify bounds $[1.00, 1.15]$ across all 7 regimes.
3. **Test 3: Hölder $p=2.0$ Quadratic Mean Convex Boost (`test_feature_35_holder_p2_convex_boost`)**:
   - Compare asset with single extreme factor (0.95, 0.60, 0.60) against equal mean (0.716, 0.716, 0.716).
   - Verify Hölder quadratic mean awards higher conviction to the extreme single-factor setup.
   - Verify continuity across the gate.
4. **Test 4: Asymmetric Bessembinder Richards Scaling (`test_feature_35_asymmetric_bessembinder_scaling`)**:
   - Verify that $\eta_{\text{right}} = 2.0$ expands right-tail spread compared to symmetric $\eta = 1.60$.
   - Verify strict bounds $[0.0, 1.0]$ and $\rho_s = 1.0000$.
5. **Test 5: Probabilistic Regime Half-Life Blending & Entropy Penalty (`test_feature_36_probabilistic_half_life_entropy_penalty`)**:
   - Pass 50/50 mixture of Bull Low Vol and Sideways High Vol.
   - Verify half-lives are smoothly blended between the two regimes.
   - Verify that increasing Shannon entropy or TV jump strictly compresses half-lives ($\tau^* < \bar{\tau}$).
   - Verify $\tau^* \ge 0.10$ days.
6. **Test 6: Continuous Hyperbolic Tangent Noise Deadband (`test_feature_36_tanh_noise_deadband`)**:
   - Pass noisy scores close to 0.50 ($s = 0.505, 0.510, 0.520$).
   - Verify that near-0.50 scores are attenuated by $>85\%$ towards zero excess.
   - Pass strong conviction scores ($s = 0.75, 0.90$) and verify $>98\%$ signal transmission.
   - Verify strict rank preservation: $\rho_s = 1.0000$.
7. **Test 7: Repository Invariant & Stress Suite**:
   - Full test suite run across all 2,351+ collected tests.
   - Target: 100% pass rate, 0 failures, 0 regressions.
