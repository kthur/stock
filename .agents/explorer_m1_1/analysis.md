# Technical Analysis: Phase 6 Quantitative Signal Enhancements (F41 & F42)

**Author**: explorer_m1_1  
**Target Milestone**: Phase 6 Milestone 1 (R1)  
**Subject**: High-Order Tensor Signal Coupling (F41) & Adaptive Regime Transition Half-Life and Noise Deadband Precision (F42)  
**Date**: 2026-09-04T13:47:00Z  

---

## 1. Executive Overview & Problem Context

Phase 5 Deep Quantitative Enhancements established high-water mark benchmarks across 5 global markets (KOSPI, KOSDAQ, S&P 500, NASDAQ, RUSSELL 2000):
- Net Expected Return: 47.85%
- Sharpe Ratio: 5.12
- Spearman Rank-IC: 0.194
- Top-Decile Alpha Spread: 29.8%
- Friction Costs: 20.4 bps
- Annualized Turnover: 38.4%

Under Phase 6 (`ORIGINAL_REQUEST.md`, `## 2026-09-04T13:40:12Z`), Requirement R1 mandates:
1. **F41: High-Order Tensor Signal Coupling & Right-Tail Confidence Scaling**:
   - Further expand Top-Decile Alpha Spread beyond 29.8% (+15% relative expansion, targeting >34.0%).
   - Model high-order cross-pillar non-linear interactions via multi-linear tensor contraction.
   - Decompose 37 strategies into 5 canonical economic pillars (Quint-Pillar) to eliminate the overloaded, heterogeneous 13-strategy "catalyst" bucket.
   - Implement adaptive Hölder $p$-norm ($p \in [1.25, 2.50]$) with factor dispersion-adaptive gating.
   - Upgrade Bessembinder/Richards power-law scaling to Version 6 (Bilateral Asymmetric Generalized Richards S-Curve) with strict mathematical rank preservation ($\rho_s \equiv 1.0000$).
2. **F42: Adaptive Regime Transition Half-Life & Noise Deadband Precision**:
   - Refine continuous Markov transition half-life adaptation using Kullback-Leibler divergence from the ergodic stationary distribution $\pi_\infty$ and transition flux dissimilarity.
   - Introduce 4-tier strategy-class elasticity ($\nu_A=1.30$ for ultra-fast microstructure vs $\nu_D=0.40$ for slow accounting fundamentals) to prevent destructive memory loss on structural balance-sheet alpha.
   - Implement bilateral asymmetric kurtosis-adaptive noise deadband ($\delta_{\text{noise}}^+$, $\delta_{\text{noise}}^-$) with exponent $\alpha(z) \in [3.0, 4.0]$ to eliminate >90% of Brownian noise and false-breakout bear traps while preserving >98.5% of true alpha transmission.

---

## 2. Mathematical Specification of Feature F41: High-Order Tensor Signal Coupling & Right-Tail Confidence Scaling

### 2.1 Quint-Pillar Economic Factor Decomposition
In Phase 5, strategies were partitioned into 4 clusters: `val` (6), `mom` (9), `flow` (9), and `cat` (13). The `cat` cluster grouped fundamentally disparate signals (earnings conference call NLP, executive filings, options gamma, supply chain graph propagation, macro cross-asset spillovers, and index ETF rebalances).

Phase 6 institutes a canonical **5-Pillar Economic Decomposition** covering all 37 strategies without overlap or omission:

| Pillar | Economic Domain | Strategy Members (37 Total) | Aggregate Formula |
|:---|:---|:---|:---|
| $\mathcal{P}_1$ **VAL_QUAL** (6) | Fundamental Value & Accounting Quality | `rim_score`, `valueup_catalyst_score`, `accruals_quality_score`, `arm_score`, `factor_neutralized_score`, `reg_score` | $s_1 = 0.70 \max(S) + 0.30 \text{mean}(S)$ |
| $\mathcal{P}_2$ **MOM_TREND** (9) | Momentum & Volatility Breakout | `surge_score`, `vcp_ml_score`, `trend_efficiency_score`, `sector_score`, `range_expansion_score`, `mq_score`, `ll_score`, `vcp_rule_score`, `lstm_score` | $s_2 = 0.70 \max(S) + 0.30 \text{mean}(S)$ |
| $\mathcal{P}_3$ **MICRO_FLOW** (9) | Microstructure, Order Flow & Mean Reversion | `order_flow_score`, `inst_foreign_sector_score`, `darkpool_score`, `microstructure_score`, `overnight_gap_score`, `stat_arb_score`, `iv_skew_score`, `reversal_score`, `vol_target_score` | $s_3 = 0.70 \max(S) + 0.30 \text{mean}(S)$ |
| $\mathcal{P}_4$ **CORP_CAT** (6) | Corporate Disclosures, Filings & Squeeze Catalysts | `event_score`, `sentiment_score`, `short_squeeze_score`, `gamma_squeeze_score`, `insider_buying_score`, `earnings_tone_drift_score` | $s_4 = 0.70 \max(S) + 0.30 \text{mean}(S)$ |
| $\mathcal{P}_5$ **NETWORK_MACRO** (7) | Value Chain Networks & Macro Asset Spillovers | `supply_chain_score`, `supply_chain_gnn_score`, `cross_asset_spillover_score`, `dual_correction_score`, `index_rebalance_score`, `card_score`, `latr_score` | $s_5 = 0.70 \max(S) + 0.30 \text{mean}(S)$ |

### 2.2 Pillar Excess Conviction Function
For each pillar $p \in \{1, 2, 3, 4, 5\}$, softplus excess conviction is evaluated with steepness $\kappa = 8.0$:
$$\psi_p = \text{clip}\left( \frac{\ln(1 + e^{\kappa(s_p - 0.50)}) - \ln(2)}{\ln(1 + e^{0.50\kappa}) - \ln(2)}, 0.0, 1.0 \right) \cdot \mathbf{1}_{\{s_p > 0.50\}}$$

### 2.3 High-Order Multi-Linear Tensor Interaction Program
The multi-order interaction tensor is defined by:
$$\Xi_{\text{tensor}} = \sum_{1 \le i < j \le 5} \Omega_{ij}(R) \psi_i \psi_j + \sum_{1 \le i < j < k \le 5} \mathcal{T}_{ijk}(R) \psi_i \psi_j \psi_k + \sum_{1 \le i < j < k < l \le 5} \mathcal{Q}_{ijkl}(R) \psi_i \psi_j \psi_k \psi_l + \Omega_{\text{quint}}(R) \prod_{m=1}^5 \psi_m$$

Where:
- $\Omega \in \mathbb{R}^{5 \times 5}$ holds $\binom{5}{2} = 10$ bilinear weights.
- $\mathcal{T} \in \mathbb{R}^{5 \times 5 \times 5}$ holds $\binom{5}{3} = 10$ trilinear weights.
- $\mathcal{Q} \in \mathbb{R}^{5 \times 5 \times 5 \times 5}$ holds $\binom{5}{4} = 5$ 4-way quadruplet weights.
- $\Omega_{\text{quint}}(R)$ is the 5-way hyper-confluence parameter.

#### Regime-Adaptive Coupling Parameters & Synergy Caps:

| Market Regime | 2nd-Order Scale $\bar{\Omega}$ | 3rd-Order Scale $\bar{\mathcal{T}}$ | 4th-Order Scale $\bar{\mathcal{Q}}$ | 5th-Order $\Omega_{\text{quint}}$ | Maximum Synergy Cap $\text{Cap}(R)$ | Max Multiplier |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| `BULL_LOW_VOL` | 0.025 ~ 0.040 | 0.020 ~ 0.030 | 0.035 | 0.060 | **0.180** | **1.180x** |
| `BULL_HIGH_VOL` | 0.020 ~ 0.035 | 0.015 ~ 0.025 | 0.025 | 0.045 | **0.145** | **1.145x** |
| `SIDEWAYS_LOW_VOL` | 0.015 ~ 0.030 | 0.010 ~ 0.020 | 0.015 | 0.030 | **0.115** | **1.115x** |
| `SIDEWAYS_HIGH_VOL` | 0.010 ~ 0.025 | 0.005 ~ 0.010 | 0.005 | 0.015 | **0.070** | **1.070x** |
| `BEAR_LOW_VOL` | 0.010 ~ 0.030 | 0.005 ~ 0.012 | 0.008 | 0.020 | **0.085** | **1.085x** |
| `BEAR_HIGH_VOL` | 0.005 ~ 0.020 | 0.000 ~ 0.005 | 0.000 | 0.000 | **0.045** | **1.045x** |
| `CRISIS` | 0.005 ~ 0.025 | 0.000 | 0.000 | 0.000 | **0.040** | **1.040x** |

Total effective synergy multiplier:
$$\text{Multiplier}_{\text{tensor}} = 1.0 + \text{clip}\left( \Xi_{\text{tensor}}, 0.0, \text{Cap}(R) \right)$$

### 2.4 Adaptive Hölder $p$-Norm with Cross-Sectional Dispersion Gating
In `apply_top_decile_convex_boost`:
1. **Regime-Adaptive Hölder Exponent $p(R)$**:
   $$p(R) = \begin{cases}
   2.50 & \text{for BULL\_LOW\_VOL} \\
   2.25 & \text{for BULL\_HIGH\_VOL} \\
   2.00 & \text{for SIDEWAYS\_LOW\_VOL} \\
   1.75 & \text{for SIDEWAYS\_HIGH\_VOL} \\
   1.80 & \text{for BEAR\_LOW\_VOL} \\
   1.50 & \text{for BEAR\_HIGH\_VOL} \\
   1.25 & \text{for CRISIS}
   \end{cases}$$
2. **Dispersion-Adaptive Sigmoid Gate**:
   Given cross-sectional factor dispersion $\sigma_{\text{cross}} = \text{std}(\mathbf{S}_{\text{base}})$:
   $$\theta_{\text{gate}}(\sigma_{\text{cross}}) = \text{clip}\left( 0.60 - 0.40 \cdot (\sigma_{\text{cross}} - 0.12), 0.55, 0.65 \right)$$
   $$\text{Gate}(M_p) = \frac{1}{1 + \exp\left( -16.0 \cdot (M_p - \theta_{\text{gate}}) \right)}$$
   $$\mathbf{S}_{\text{boosted}} = (1 - \lambda_{\text{boost}} \cdot \text{Gate}) \mathbf{S}_{\text{base}} + (\lambda_{\text{boost}} \cdot \text{Gate}) M_p$$
   where $M_p = \left( \frac{1}{k} \sum_{i=1}^k S_{(i)}^p \right)^{1/p}$.

### 2.5 Bilateral Asymmetric Generalized Richards S-Curve (Version 6)
Let $u = 2(s - 0.50) \in [-1.0, 1.0]$.
Excess metrics:
$$\text{excess}_{\text{right}} = \max\left( 0.0, \frac{u - u_{\text{thresh,right}}}{1.0 - u_{\text{thresh,right}}} \right), \quad \text{excess}_{\text{left}} = \max\left( 0.0, \frac{-u - u_{\text{thresh,left}}}{1.0 - u_{\text{thresh,left}}} \right)$$

Curvature scaling:
$$\tilde{u} = \begin{cases}
+ u^{\gamma} \cdot \left[ 1.0 + \beta_{\text{right}} \cdot \text{excess}_{\text{right}}^{\eta_{\text{right}}} \right] & \text{if } u \ge 0 \\
- |u|^{\gamma} \cdot \left[ 1.0 + \beta_{\text{left}} \cdot \text{excess}_{\text{left}}^{\eta_{\text{left}}} \right] & \text{if } u < 0
\end{cases}$$

Rescaling to $[0.0, 1.0]$:
$$\tilde{s} = 0.50 + 0.50 \cdot \frac{\tilde{u}}{\text{Scale}}, \quad \text{Scale} = \max\left( 1.0 + \beta_{\text{right}}, \max_i |\tilde{u}_i| \right)$$

#### Version 6 Parameter Matrix:

| Regime | $\gamma$ | $\beta_{\text{right}}$ | $\beta_{\text{left}}$ | $u_{\text{thresh,right}}$ | $u_{\text{thresh,left}}$ | $\eta_{\text{right}}$ | $\eta_{\text{left}}$ |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `BULL_LOW_VOL` | 1.85 | 0.60 | 0.35 | 0.38 | 0.60 | 2.40 | 1.40 |
| `BULL_HIGH_VOL` | 1.70 | 0.52 | 0.35 | 0.45 | 0.60 | 2.20 | 1.50 |
| `SIDEWAYS_LOW_VOL` | 1.50 | 0.42 | 0.35 | 0.55 | 0.60 | 2.00 | 1.60 |
| `SIDEWAYS_HIGH_VOL` | 1.35 | 0.30 | 0.35 | 0.68 | 0.65 | 1.80 | 1.70 |
| `BEAR_LOW_VOL` | 1.30 | 0.30 | 0.40 | 0.65 | 0.55 | 1.80 | 1.80 |
| `BEAR_HIGH_VOL` | 1.20 | 0.20 | 0.45 | 0.70 | 0.50 | 1.60 | 1.90 |
| `CRISIS` | 1.20 | 0.20 | 0.50 | 0.78 | 0.45 | 1.50 | 2.00 |

#### Rank Preservation Monotonicity Proof:
Let $g(u) = \text{sgn}(u) |u|^\gamma [1 + \beta \text{excess}(u)^\eta]$.
For $u > 0$:
$$g'(u) = \gamma u^{\gamma - 1} [1 + \beta \text{excess}^\eta] + u^\gamma \beta \eta \text{excess}^{\eta - 1} \frac{1}{1 - u_{\text{th}}} > 0$$
For $u < 0$, by odd symmetry of the piecewise components, $g'(u) > 0$.
At $u = 0$, $\lim_{u \to 0^+} g'(u) = \lim_{u \to 0^-} g'(u) \ge 0$.
Since $g'(u) > 0$ almost everywhere on $[-1, 1]$, $g$ is strictly monotonic increasing.
Therefore:
$$\rho_{\text{Spearman}}(s, \tilde{s}) \equiv 1.000000$$

---

## 3. Mathematical Specification of Feature F42: Adaptive Regime Transition Half-Life & Noise Deadband Precision

### 3.1 Stationary Distribution Divergence $\phi_{\text{KL}}$
Let $\pi_\infty = [0.20, 0.15, 0.25, 0.15, 0.12, 0.08, 0.05]^T$ be the ergodic stationary probability vector across the 7 regimes.
The Kullback-Leibler divergence from stationary equilibrium is:
$$D_{\text{KL}}(\pi \,\|\, \pi_\infty) = \sum_{m=1}^7 \pi_m \ln\left( \frac{\pi_m + 10^{-12}}{\pi_{\infty, m} + 10^{-12}} \right)$$
The **Equilibrium Divergence Damping Factor**:
$$\phi_{\text{KL}}(\pi) = \exp\left( -0.25 \cdot D_{\text{KL}}(\pi \,\|\, \pi_\infty) \right) \in (0, 1]$$

### 3.2 Transition Flux Dissimilarity $\phi_{\text{flux}}$
Given previous posterior belief $\pi_{\text{prev}}$ and 1-step empirical transition kernel $\mathbf{P} \in \mathbb{R}^{7 \times 7}$:
$$d_{\text{flux}} = \frac{1}{2} \|\pi - \pi_{\text{prev}} \mathbf{P}\|_1$$
$$\phi_{\text{flux}} = \exp\left( -0.40 \cdot \max(0.0, d_{\text{flux}} - 0.15) \right) \in (0, 1]$$

### 3.3 Strategy-Class Elasticity Partitioning
All 37 strategies are grouped into 4 distinct **Half-Life Elasticity Classes**:

1. **Class A: Ultra-Fast Microstructure & High-Turnover Signals ($\nu_A = 1.30$)**
   - Members: `order_flow`, `microstructure`, `darkpool`, `overnight_gap`, `stat_arb`, `iv_skew`, `surge`, `gamma_squeeze`
   - Behavior: Under uncertainty, half-life contracts rapidly ($e.g. \tau \to 0.25$ days) to avoid stale toxic executions.
2. **Class B: Medium-Fast Momentum & Trend Breakout Signals ($\nu_B = 1.00$)**
   - Members: `vcp_ml`, `trend_efficiency`, `sector_rotation`, `range_expansion`, `mq_factor`, `short_squeeze`, `lead_lag`, `supply_chain`
   - Behavior: Standard probabilistic contraction.
3. **Class C: Tactical Catalysts & Macro Flow Networks ($\nu_C = 0.75$)**
   - Members: `event_driven`, `sentiment`, `dual_correction`, `index_rebalance`, `insider_buying`, `earnings_tone_drift`, `card_factor`, `latr_factor`, `cross_asset_spillover`, `supply_chain_gnn`
   - Behavior: Retains moderate memory of announcement drift and network transmission.
4. **Class D: Slow Accounting Fundamentals & Structural Risk Parity ($\nu_D = 0.40$)**
   - Members: `rim_valuation`, `valueup_catalyst`, `accruals_quality`, `arm_factor`, `factor_neutralized`, `vol_target`, `regression`, `lstm`
   - Behavior: Anchored memory. Quarterly balance sheet quality does not vanish during transient VIX spikes.

For strategy $k \in \text{Class } c(k)$ with mixture expectation $\bar{\tau}_k = \sum_m \pi_m \tau_k(R_m)$:
$$\tau_k^*(\pi) = \max\left( 0.10, \text{round}\left( \bar{\tau}_k \cdot \left[ \phi_{\text{entropy}}(\pi) \cdot \phi_{\text{jump}}(d_{\text{TV}}) \cdot \phi_{\text{KL}}(\pi) \right]^{\nu_{c(k)}}, 2 \right) \right)$$

### 3.4 Asymmetric Kurtosis-Adaptive Noise Deadband
Let $z = s - 0.50 \in [-0.50, 0.50]$.
Threshold calculation:
$$\delta_{\text{noise}}^+(R, \pi) = \delta_0(R) \cdot \left( 1.0 + 0.40 H_{\text{norm}}(\pi) \right)$$
$$\delta_{\text{noise}}^-(R, \pi) = \delta_{\text{noise}}^+(R, \pi) \cdot \chi_{\text{bear}}(R)$$

Where $\chi_{\text{bear}}(R)$:
- `CRISIS`: $1.40$
- `BEAR_HIGH_VOL`: $1.35$
- `BEAR_LOW_VOL`: $1.20$
- `SIDEWAYS_HIGH_VOL`: $1.15$
- Others: $1.00$

Effective parameters:
$$\delta_{\text{eff}}(z) = \begin{cases} \delta_{\text{noise}}^+ & \text{if } z \ge 0 \\ \delta_{\text{noise}}^- & \text{if } z < 0 \end{cases}, \quad \alpha_{\text{eff}}(z) = \begin{cases} 3.5 & \text{if } z \ge 0 \\ 4.0 & \text{if } z < 0 \text{ and } (\text{CRISIS} \text{ or } \text{HIGH\_VOL}) \\ 3.2 & \text{if } z < 0 \text{ otherwise} \end{cases}$$

Soft-thresholding operation:
$$z_{\text{denoised}} = z \cdot \tanh\left( \left( \frac{|z|}{\delta_{\text{eff}}(z)} \right)^{\alpha_{\text{eff}}(z)} \right)$$

#### Invariant Verification:
1. At $|z| \le 0.010$ (Brownian noise), attenuation is:
   $$1 - \frac{z_{\text{denoised}}}{z} = 1 - \tanh\left( (0.01 / 0.05)^{3.5} \right) \approx 1 - \tanh(0.0035) \ge 99.6\% > 90.0\%$$
2. At $|z| \ge 0.150$ (high conviction signal), transmission is:
   $$\frac{z_{\text{denoised}}}{z} = \tanh\left( (0.15 / 0.045)^{3.5} \right) \approx \tanh(68.2) = 1.0000 > 98.5\%$$
3. Monotonicity: $\frac{d}{dz}[z \tanh(u(z)^\alpha)] > 0$ for all $z \ne 0$, so rank order is invariant.

---

## 4. Code Modification Targets & Mapping

### 4.1 Target: `trading_system/src/ai/ensemble_scorer.py`
1. **Lines 89-122 (`BessembinderParams`)**:
   - Add properties `eta_right`, `eta_left` with default fallback to ensure seamless backward compatibility.
2. **Lines 1715-1741 (`apply_top_decile_convex_boost`)**:
   - Implement regime-adaptive Hölder $p(R)$ selection.
   - Compute factor dispersion $\sigma_{\text{cross}}$ and adapt gate threshold $\theta_{\text{gate}}$.
3. **Lines 3194-3201 (`combine_predictions` synergy integration)**:
   - Call `compute_high_order_tensor_cross_pillar_synergy` with Quint-Pillar decomposition and Phase 6 synergy caps (up to 0.180).
4. **Lines 3240-3250 (`apply_top_decile_convex_boost` in `combine_predictions`)**:
   - Pass `p_norm=None` to trigger auto regime-adaptive $p(R)$ selection ($p \in [1.25, 2.50]$).
5. **Lines 3252-3265 (`apply_bessembinder_convex_power_law` in `combine_predictions`)**:
   - Set `version=6` to activate Bilateral Asymmetric Generalized Richards S-Curve.
6. **Lines 3306-3325 (`combine_predictions` noise deadband & return scaling)**:
   - Wire in asymmetric deadband $(\delta^+, \delta^-)$ and kurtosis exponent $\alpha(z)$.
   - Connect $\gamma_{\text{tail}}(R) \in [1.00, 1.35]$ with cubic rank modulation for top-decile spread expansion.
7. **Lines 3908-3970 (`get_regime_adaptive_half_lives`)**:
   - Add $\phi_{\text{KL}}$ calculation and 4-tier strategy class elasticity $\nu_{c(k)}$.
8. **Lines 4160-4315 (`compute_bilinear_cross_pillar_synergy` / `compute_high_order_tensor_cross_pillar_synergy`)**:
   - Implement 5-pillar structure, 3rd-order tensor $\mathcal{T}$, 4th-order quadruplets $\mathcal{Q}$, and 5th-order $\Omega_{\text{quint}}$.
9. **Lines 4320-4385 (`get_regime_adaptive_bessembinder_params`)**:
   - Add `version=6` branch.
10. **Lines 4400-4473 (`apply_bessembinder_convex_power_law`)**:
    - Support Version 6 asymmetric $(\eta_{\text{right}}, \eta_{\text{left}})$ and bilateral $u_{\text{thresh}}$.
11. **Lines 4475-4503 (`get_regime_adaptive_gamma_tail`)**:
    - Add Phase 6 exponent scale ($1.35$ in Bull Low Vol).
12. **Lines 4505-4573 (`get_regime_adaptive_noise_deadband` and `apply_smooth_noise_deadband`)**:
    - Implement bilateral thresholds $(\delta^+, \delta^-)$ and kurtosis exponent $\alpha_{\text{eff}}(z)$.

### 4.2 Target: `trading_system/src/ai/factor_suppression.py`
1. **Lines 74-80 (`CLUSTER_MAP`)**:
   - Preserve existing cluster names for backward compatibility while adding cross-reference aliases for `CORP_CAT` and `NETWORK_MACRO`.
2. **Lines 107-117 (`DEFAULT_REGIME_PARAMS`)**:
   - Ensure cutoff thresholds $\theta_0(R)$ and $\lambda_{\text{penalty}}(R)$ align with the 6 2D regimes + Crisis.
3. **Lines 124-142 (`calibrate_cutoff`)**:
   - Ensure statistical calibration $\theta(R, N) = \theta_0 + 1.645 / \sqrt{\max(N-3, 1)}$ seamlessly supports high-dimensional covariance matrices.

---

## 5. Test Case Design for `tests/test_phase6_signal_enhancement.py`

Six comprehensive test cases are specified:
1. `test_feature_41_1_quint_pillar_tensor_synergy_kernel`:
   - Verify 5-Pillar > 4-Pillar > 3-Pillar > 2-Pillar > 1-Pillar ordering.
   - Verify synergy multiplier reaches cap $1.180\times$ in `BULL_LOW_VOL` and strictly $\le 1.040\times$ in `CRISIS`.
   - Verify bounds $[1.00, 1.18]$ across all 7 regimes.
2. `test_feature_41_2_adaptive_holder_p_norm_boost`:
   - Verify $M_{2.5} > M_{2.0} > M_{1.0}$ on convex setup.
   - Verify regime adaptation: $p=2.50$ in Bull Low Vol, $p=2.00$ in Sideways, $p=1.25$ in Crisis.
   - Verify dispersion-adaptive gating shifts $\theta_{\text{gate}}$ appropriately.
3. `test_feature_41_3_asymmetric_richards_v6_scaling_and_monotonicity`:
   - Verify Phase 6 top-spread exceeds Phase 5 top-spread by $\ge 15\%$.
   - Verify strict Spearman rank correlation $\rho_s \equiv 1.0000$.
   - Verify bounds in $[0.0, 1.0]$.
4. `test_feature_42_1_markov_stationary_divergence_and_class_elasticity`:
   - Verify $\phi_{\text{KL}}$ dampens half-lives when belief $\pi$ diverges from stationary $\pi_\infty$.
   - Verify Class A (microstructure, $\nu_A = 1.30$) contracts half-life more aggressively than Class D (fundamentals, $\nu_D = 0.40$).
   - Verify all half-lives remain $\ge 0.10$ days.
5. `test_feature_42_2_asymmetric_kurtosis_noise_deadband`:
   - Verify $>90\%$ attenuation for near-zero noise ($|z| \le 0.010$).
   - Verify $>98.5\%$ transmission for strong conviction ($|z| \ge 0.150$).
   - Verify asymmetric suppression: negative noise in Bear/Crisis is squashed more aggressively than in Bull.
   - Verify strict rank correlation $\rho_s \equiv 1.0000$.
6. `test_feature_42_3_multi_market_randomized_stress_all_regimes`:
   - Randomized 30-asset universe across SP500, NASDAQ, RUSSELL2000, KOSPI, KOSDAQ across all 7 regimes.
   - Verify 0 NaNs, 0 Infs, valid $[0.0, 1.0]$ bounds, and finite expected returns.
