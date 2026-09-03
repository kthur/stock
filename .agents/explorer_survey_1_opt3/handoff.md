# Handoff Report: Survey Explorer 1 — 3rd Deep Quantitative Enhancement (Requirement R1)
**Author**: Survey Explorer 1 (`explorer_survey_1_opt3`)  
**Target Milestone**: Milestone 1 (37-Strategy Dynamic Alpha Weights & Nonlinear Factor Coupling under 2D Market Regimes)  
**Date**: 2026-09-04T05:53:30+09:00  
**Status**: Read-Only Survey Complete

---

## 1. Observation

### 1.1 Scope & Codebase Architecture
The multi-factor scoring and ensemble system integrates **37 quantitative strategies** across 5 equity markets (KOSPI, KOSDAQ, SP500, NASDAQ, RUSSELL2000). The core logic resides within:
- `trading_system/src/ai/ensemble_scorer.py` (3,661 lines, `EnsembleScoringEngine`)
- `trading_system/src/ai/factor_orthogonalizer.py` (556 lines, `FactorOrthogonalizerEngine`)
- `trading_system/src/ai/factor_suppression.py` (429 lines, `RegimeFactorSuppressionEngine`)
- `trading_system/src/ai/score_normalizer.py` (`CrossSectionalScoreNormalizer`)
- `trading_system/src/analysis/regime_detector.py` (`MarketRegimeDetector`)
- `trading_system/run_pipeline.py` (Orchestration of 37-strategy inference, scoring, and allocation)

---

### 1.2 Observation on 2D Market Regime Matrix & Regime Weights (`ensemble_scorer.py`)
1. **Current Regime States (`ensemble_scorer.py:237-472`)**:
   - `REGIME_2D_WEIGHTS` defines baseline weights across 37 strategies for **only 6 states**:
     * `BEAR_LOW_VOL` (lines 238–276, sum = 1.00)
     * `BEAR_HIGH_VOL` (lines 277–315, sum = 1.00)
     * `SIDEWAYS_LOW_VOL` (lines 316–354, sum = 1.00)
     * `SIDEWAYS_HIGH_VOL` (lines 355–393, sum = 1.00)
     * `BULL_LOW_VOL` (lines 394–432, sum = 1.00)
     * `BULL_HIGH_VOL` (lines 433–471, sum = 1.00)
   - `MACRO_WEIGHT_MODIFIERS` (lines 477–537) specifies delta overlays for 5 macroeconomic conditions: `LIQUIDITY_SQUEEZE`, `HIGH_YIELD_BULL`, `HIGH_YIELD_BEAR`, `INFLATION_SHOCK`, `YIELD_INVERSION`.

2. **The `CRISIS` Regime Blind Spot (`ensemble_scorer.py:879-890`)**:
   In `get_base_weights(self, regime: Union[int, str], ...)`:
   ```python
   882: if isinstance(regime, str) and regime in self.REGIME_2D_WEIGHTS:
   883:     w = dict(self.REGIME_2D_WEIGHTS[regime])
   884: elif str(regime).isdigit() and int(regime) in self.REGIME_WEIGHTS:
   885:     w = dict(self.REGIME_WEIGHTS[int(regime)])
   886: elif isinstance(regime, int) and regime in self.REGIME_WEIGHTS:
   887:     w = dict(self.REGIME_WEIGHTS[regime])
   888: else:
   889:     w = dict(self.REGIME_2D_WEIGHTS.get(str(regime), self.REGIME_2D_WEIGHTS['SIDEWAYS_LOW_VOL']))
   ```
   **Defect**: When `regime = 'CRISIS'`, it is not in `REGIME_2D_WEIGHTS`. The fallback at line 889 assigns `SIDEWAYS_LOW_VOL` base weights! Although lines 2786 (`regime_multiplier = 10.0`) and 3321 (`kappa_regime = 0.30`) recognize `'CRISIS'`, the actual factor allocation defaults to calm, rotation-oriented weights instead of an ultra-defensive crisis profile.

---

### 1.3 Observation on Markov Transition Probabilities & Dynamic Smoothing (`ensemble_scorer.py:1157-1193`)
1. **Hard Reset on Regime Transition**:
   In `compute_dynamic_weights_from_sharpe`:
   ```python
   1161: is_regime_shift = (prev_reg_mkt is not None) and (str(prev_reg_mkt) != current_regime_str)
   ...
   1165: if is_regime_shift:
   1166:     # Instant reset on regime transition to avoid carrying over obsolete regime dynamics
   1167:     self._prev_weights[market] = dict(dynamic_weights)
   1168:     return dynamic_weights
   ```
   When market regime oscillates (e.g. `BULL_HIGH_VOL` $\leftrightarrow$ `BEAR_HIGH_VOL`), this instant reset induces high rebalancing turnover and whipsawing.
2. **Piecewise Heuristic Smoothing**:
   Lines 1169–1177 compute EMA smoothing factor `eff_alpha`:
   ```python
   1169: elif vix_val is not None and float(vix_val) >= 30.0:
   1170:     eff_alpha = 0.60
   1171: elif has_explicit_tilting:
   1172:     eff_alpha = 0.45
   1173: elif vix_val is not None and float(vix_val) > 22.0:
   1174:     eff_alpha = 0.35
   1175: else:
   1176:     eff_alpha = self.alpha_smoothing # 0.20
   ```
   This is a discrete step function, lacking continuous information-entropy modulation or transition-probability weighting.
3. **Disconnection from Regime Detector Probabilities**:
   `MarketRegimeDetector.predict_regime_transition_probabilities` (`regime_detector.py:250-308`) computes $\{p_{\text{bear}}, p_{\text{sideways}}, p_{\text{bull}}\}$, but this distribution is neither expanded to 2D nor utilized in `ensemble_scorer.py`.

---

### 1.4 Observation on Alpha Decay Rates & Half-Life Acceleration
1. **Regime-Adaptive Half-Lives (`ensemble_scorer.py:3310-3359`)**:
   `get_regime_adaptive_half_lives` scales base half-lives $\tau_k^{(0)}$ by:
   - `CRISIS`: $\kappa_{\text{regime}} = 0.30$
   - `BEAR_HIGH_VOL`: $\kappa_{\text{regime}} = 0.50$
   - `SIDEWAYS_HIGH_VOL`: $\kappa_{\text{regime}} = 0.70$
   - `BULL_HIGH_VOL`: $\kappa_{\text{regime}} = 0.75$
   - `BEAR_LOW_VOL`: $\kappa_{\text{regime}} = 0.85$
   - `BULL_LOW_VOL`: $\kappa_{\text{regime}} = 1.30$
   - Fast tier: $\kappa_{\text{tier}} = \min(1.0, \kappa_{\text{regime}}^{1.2})$
   - Slow tier: $\kappa_{\text{tier}} = \max(0.60, \sqrt{\kappa_{\text{regime}}})$
2. **Orphaned / Unhooked Core Methods**:
   - `apply_exponential_decay_filter` (lines 3362–3424): Implements multi-horizon continuous exponential convolutional decay filtering: $\tilde{s}_k(t) = \alpha_k s_k(t) + (1 - \alpha_k) \tilde{s}_k(t-1)$. **Grep search confirms this method is NEVER called anywhere in the pipeline**.
   - `apply_rank_ic_decay_calibration` (lines 1215–1255): Implements Rank IC exponential latency decay. **NEVER called in `run_pipeline.py` or `calculate_ensemble_score`**.
   - `apply_ker_dynamic_alpha_switching` (lines 3462–3506): Dynamic trend vs reversal switching based on Kaufman Efficiency Ratio (KER). **NEVER called in `combine_predictions`**.

---

### 1.5 Observation on Momentum Inertia vs Reversal in Trending Regimes
1. **Regime-Adaptive Momentum Turbo (`ensemble_scorer.py:1112-1128`)**:
   ```python
   1116: is_bull_regime = 'BULL' in str(regime).upper() or str(regime) == '2'
   1117: if is_bull_regime:
   1118:     MOMENTUM_TURBO_STRATEGIES = {'surge', 'vcp_ml', 'mq_factor', 'order_flow', ...}
   1124:     if strategy in MOMENTUM_TURBO_STRATEGIES:
   1125:         turbo_mult = 1.40
   ```
   **Defect**: Applies an identical 1.40x turbo whether the regime is `BULL_LOW_VOL` (placid, high signal-to-noise ratio trend) or `BULL_HIGH_VOL` (elevated momentum crash risk). It lacks factor persistence autocorrelation tracking.

---

### 1.6 Observation on Nonlinear Factor Interaction & Top-Decile Spread Maximization
1. **Incomplete 4-Pillar Cluster Mapping (`ensemble_scorer.py:3540-3549`)**:
   In `compute_bilinear_cross_pillar_synergy`:
   - `val`: `rim_score`, `valueup_catalyst_score`, `accruals_quality_score`, `arm_score` (4)
   - `mom`: `surge_score`, `vcp_ml_score`, `trend_efficiency_score`, `sector_score`, `range_expansion_score`, `mq_score`, `ll_score`, `vcp_rule_score` (8)
   - `flow`: `order_flow_score`, `inst_foreign_sector_score`, `darkpool_score`, `microstructure_score`, `overnight_gap_score`, `stat_arb_score` (6)
   - `cat`: `event_score`, `sentiment_score`, `short_squeeze_score`, `gamma_squeeze_score`, `supply_chain_score`, `supply_chain_gnn_score`, `cross_asset_spillover_score`, `dual_correction_score`, `index_rebalance_score`, `insider_buying_score`, `earnings_tone_drift_score` (11)
   Total: 29 strategy columns mapped.
   **Defect: 8 strategies are omitted**: `regression`, `lstm`, `iv_skew`, `card_factor`, `latr_factor`, `factor_neutralized`, `vol_target`, `short_term_reversal`. These 8 strategies receive 0 synergy coupling.
2. **Bessembinder Convex Power-Law (`ensemble_scorer.py:3608-3659`)**:
   Richards/Bessembinder symmetric tail scaling is active (lines 2722–2733), but its power parameters ($\gamma_{\text{tail}} = 1.45, \beta_{\text{tail}} = 0.40$) are completely static across regimes.

---

### 1.7 Observation on Factor Orthogonalization & Suppression
1. **Factor Orthogonalizer (`factor_orthogonalizer.py:233-310`)**:
   - Implements `_pca_zca_symmetric` with Ledoit-Wolf shrinkage, Marchenko-Pastur lower spectral floor, and Dual-Consensus top-$k$ eigenvalue preservation.
   - When NaN or missing strategies exist (e.g. Korean symbols lacking US option skew), median imputation can create artificial zero-variance vectors if not carefully handled.
2. **Factor Suppression (`factor_suppression.py`)**:
   - `solve_single_stage_entropy_allocation` (lines 15–59) is implemented with gradient descent on the simplex.
   - **Defect**: In `ensemble_scorer.py:2420`, `suppress_weights` is called with `use_entropy_allocation=False` (default), so the entropy program is never used in the live pipeline.

---

### 1.8 Existing Test Suite Baseline
Execution of test targets (`test_regime_ensemble.py`, `test_factor_orthogonalization.py`, `test_correlation_suppression.py`, `test_factor_momentum_and_available_normalization.py`, `test_r1_ensemble_regime_fixes.py`) confirmed **36 / 36 tests PASSING (100%)** in 20.31s.

---

## 2. Logic Chain & Proposed Mathematical / Algorithmic Design

### Logic Chain Step 1: Explicit 7-State 2D Regime Matrix Definition
*Premise*: Observation 1.2 proved that `CRISIS` falls back to `SIDEWAYS_LOW_VOL` base weights.  
*Inference*: A distinct `CRISIS` weight dictionary must be added directly to `REGIME_2D_WEIGHTS` and `REGIME_WEIGHTS`.
*Mathematical Specification*:
Let $\mathbf{w}_{\text{CRISIS}} \in \mathbb{R}^{37}$ satisfy $\sum_{k=1}^{37} w_{k, \text{CRISIS}} = 1.0000$ with $w_{k, \text{CRISIS}} \ge 0.005$:
$$\mathbf{w}_{\text{CRISIS}} = \begin{cases}
\text{vol\_target}: 0.08, \; \text{stat\_arb}: 0.08, \; \text{rim\_valuation}: 0.07, \; \text{accruals\_quality}: 0.06, \\
\text{regression}: 0.06, \; \text{card\_factor}: 0.05, \; \text{short\_term\_reversal}: 0.05, \; \text{mq\_factor}: 0.04, \\
\text{factor\_neutralized}: 0.05, \; \text{latr\_factor}: 0.05, \; \dots \\
\text{surge}: 0.005, \; \text{vcp\_ml}: 0.005, \; \text{short\_squeeze}: 0.005, \; \text{gamma\_squeeze}: 0.005, \\
\text{trend\_efficiency}: 0.005, \; \text{range\_expansion\_breakout}: 0.005
\end{cases}$$

---

### Logic Chain Step 2: Markov Regime-Switching (MRS) Transition Dynamics
*Premise*: Observation 1.3 demonstrated that hard resets upon regime change induce turnover spikes.  
*Inference*: We must define a 7-state Markov transition probability matrix $\mathbf{P} \in \mathbb{R}^{7 \times 7}$ and perform continuous Bayesian soft-blending.  
*Mathematical Specification*:
Let the regime state space be:
$$\mathcal{S} = \{ \text{BLV}, \text{BHV}, \text{SLV}, \text{SHV}, \text{BLV}_{\text{bear}}, \text{BHV}_{\text{bear}}, \text{CRISIS} \}$$
Given posterior probabilities $\boldsymbol{\pi}_t = [\pi_{t, 1}, \dots, \pi_{t, 7}]^T \in \Delta^6$, the blended base weight vector is:
$$\mathbf{w}_{\text{base}}(t) = \sum_{m=1}^7 \pi_{t, m} \mathbf{w}^{(m)}$$
where $\mathbf{w}^{(m)}$ is the canonical weight vector for regime $m$.
If only a single regime $R_t$ is supplied, construct $\boldsymbol{\pi}_t$ via Gaussian kernel smoothing over volatility and trend z-scores:
$$\pi_{t, m} \propto \exp\left( - \frac{1}{2} (\mathbf{z}_t - \boldsymbol{\mu}_m)^T \boldsymbol{\Sigma}_m^{-1} (\mathbf{z}_t - \boldsymbol{\mu}_m) \right)$$

---

### Logic Chain Step 3: Information-Entropy Adaptive Weight Smoothing
*Premise*: Observation 1.3 highlighted heuristic piecewise step functions on VIX.  
*Inference*: Replace step thresholds with continuous information-entropy and transition-distance modulation.  
*Mathematical Specification*:
Define the dynamic smoothing parameter $\alpha_t$:
$$\alpha_t = \text{clip}\left( \alpha_0 + \beta_{\text{trans}} \cdot d_{\text{TV}}(\boldsymbol{\pi}_t, \boldsymbol{\pi}_{t-1}) + \beta_{\text{vix}} \cdot \sigma_{\text{vix}}(t), \; \alpha_{\min}, \; \alpha_{\max} \right)$$
where:
- $d_{\text{TV}}(\boldsymbol{\pi}_t, \boldsymbol{\pi}_{t-1}) = \frac{1}{2} \sum_{m=1}^7 |\pi_{t, m} - \pi_{t-1, m}|$ (Total Variation distance)
- $\sigma_{\text{vix}}(t) = \text{clip}\left( \frac{\text{VIX}_t - 18.0}{22.0}, 0.0, 1.0 \right)$
- Parameters: $\alpha_0 = 0.20, \beta_{\text{trans}} = 0.40, \beta_{\text{vix}} = 0.35, \alpha_{\min} = 0.15, \alpha_{\max} = 0.85$.
Update rule:
$$\mathbf{w}_{\text{smooth}}(t) = \alpha_t \mathbf{w}_{\text{target}}(t) + (1 - \alpha_t) \mathbf{w}_{\text{smooth}}(t-1)$$

---

### Logic Chain Step 4: Hooking Multi-Horizon Exponential Filtering in Pipeline
*Premise*: Observation 1.4 revealed `apply_exponential_decay_filter` and `apply_rank_ic_decay_calibration` are orphaned.  
*Inference*: Wire these methods into `combine_predictions` prior to cross-sectional linear combination.  
*Mathematical Specification*:
For each stock $i$ and strategy $k$:
$$\alpha_k(R_t) = 1 - \exp\left( - \frac{\ln(2)}{\tau_k(R_t)} \right)$$
Filtered signal:
$$\tilde{s}_{i, k}(t) = \alpha_k(R_t) s_{i, k}(t) + (1 - \alpha_k(R_t)) \tilde{s}_{i, k}(t-1)$$
where $\tau_k(R_t) = \tau_k^{(0)} \cdot \kappa_{\text{regime}}(R_t) \cdot \kappa_{\text{tier}}(k, R_t)$ from `get_regime_adaptive_half_lives`.
This smoothly filters out high-frequency noise in slow valuation factors while allowing fast execution strategies to respond instantaneously.

---

### Logic Chain Step 5: Momentum Inertia Tracking vs Reversal in Trending Regimes
*Premise*: Observation 1.5 showed uncalibrated momentum multipliers in high-volatility environments.  
*Inference*: In `BULL_LOW_VOL`, reward factors showing high positive rank autocorrelation; in `BULL_HIGH_VOL`, scale back momentum to prevent crash risk.  
*Mathematical Specification*:
Compute 20-day factor rank autocorrelation:
$$\rho_k^{\text{autocorr}} = \text{Corr}\left( s_{i, k}(t), s_{i, k}(t-1) \right)_{i=1}^N$$
For $k \in \text{MOMENTUM}$:
$$M_k^{\text{inertia}} = \begin{cases}
1.0 + 0.40 \cdot \max(0, \tanh(2 \cdot \text{IC}_k)) \cdot \max(0, \rho_k^{\text{autocorr}}), & \text{if } R_t = \text{BULL\_LOW\_VOL} \\
1.0 + 0.15 \cdot \max(0, \tanh(2 \cdot \text{IC}_k)), & \text{if } R_t = \text{BULL\_HIGH\_VOL} \\
0.50, & \text{if } R_t \in \{\text{BEAR\_HIGH\_VOL}, \text{CRISIS}\}
\end{cases}$$
For $k \in \text{REVERSAL}$:
$$M_k^{\text{reversal}} = \begin{cases}
0.30, & \text{if } R_t = \text{BULL\_LOW\_VOL} \\
1.50 \cdot (1.0 + 0.20 \cdot \text{vix\_stress}), & \text{if } R_t \in \{\text{BEAR\_HIGH\_VOL}, \text{CRISIS}\}
\end{cases}$$

---

### Logic Chain Step 6: Complete 37-Strategy 4-Pillar Synergy & Regime-Adaptive Bessembinder S-Curve
*Premise*: Observation 1.6 identified 8 omitted strategies in `compute_bilinear_cross_pillar_synergy`.  
*Inference*: Expand cluster definitions to encompass all 37 strategies, and make Bessembinder power-law scaling regime-dependent.  
*Mathematical Specification*:
1. **Cluster Partition ($\bigcup_{p=1}^4 \mathcal{C}_p = \{1, \dots, 37\}$)**:
   - $\mathcal{C}_{\text{val}}$ (7): `rim_valuation`, `valueup_catalyst`, `accruals_quality`, `arm_factor`, `factor_neutralized`, `mq_factor`, `regression`
   - $\mathcal{C}_{\text{mom}}$ (10): `surge`, `vcp_ml`, `trend_efficiency`, `sector_rotation`, `range_expansion_breakout`, `lead_lag`, `vcp_rule`, `lstm`, `supply_chain`, `supply_chain_gnn`
   - $\mathcal{C}_{\text{flow}}$ (9): `order_flow`, `inst_foreign_sector`, `darkpool`, `microstructure`, `overnight_gap_reversal`, `stat_arb`, `iv_skew`, `short_term_reversal`, `vol_target`
   - $\mathcal{C}_{\text{cat}}$ (11): `event_driven`, `sentiment`, `short_squeeze`, `gamma_squeeze`, `cross_asset_spillover`, `dual_correction`, `index_rebalance`, `insider_buying`, `earnings_tone_drift`, `card_factor`, `latr_factor`
2. **Regime-Adaptive Bessembinder S-Curve**:
   $$\tilde{u}_i = \text{sgn}(u_i) \cdot |u_i|^{\gamma_{\text{tail}}(R)} \cdot \left[ 1 + \beta_{\text{tail}}(R) \cdot \left( \frac{\max(0, |u_i| - u_{\text{thresh}})}{1 - u_{\text{thresh}}} \right)^{\eta} \right]$$
   - In `BULL_LOW_VOL`: $\gamma_{\text{tail}} = 1.70, \beta_{\text{tail}} = 0.50$ (Steep tail spread maximization)
   - In `CRISIS` / `BEAR_HIGH_VOL`: $\gamma_{\text{tail}} = 1.20, \beta_{\text{tail}} = 0.20$ (Conservative, prevents tail over-concentration)

---

### Logic Chain Step 7: Factor Orthogonalization & Single-Stage Entropy Redundancy Allocation
*Premise*: Observation 1.7 proved that `solve_single_stage_entropy_allocation` is never enabled in the live pipeline.  
*Inference*: Enable `use_entropy_allocation = True` in `EnsembleScoringEngine.combine_predictions` and enhance `FactorOrthogonalizerEngine` against zero-variance singular columns.  
*Mathematical Specification*:
Solve the convex optimization program:
$$\min_{\mathbf{w}} \left[ \frac{1}{2} \mathbf{w}^T \mathbf{R} \mathbf{w} - \tau_{\text{entropy}} \sum_{i=1}^{37} \ln(w_i) + \gamma_{\text{anchor}} \|\mathbf{w} - \mathbf{w}_0\|^2 \right] \quad \text{s.t.} \quad \mathbf{w} \ge w_{\min} \mathbf{1}, \quad \mathbf{1}^T \mathbf{w} = 1$$
This balances correlation redundancy reduction ($\mathbf{w}^T \mathbf{R} \mathbf{w}$), factor entropy diversification ($-\sum \ln w_i$), and macroeconomic regime fidelity ($\|\mathbf{w} - \mathbf{w}_0\|^2$).

---

## 3. Caveats & Risk Analysis

1. **Cold Start & History Availability**:
   - Continuous exponential decay filtering requires previous period score state $\tilde{\mathbf{s}}_{t-1}$. When running cold or in test mode without persisted prior scores, the system must gracefully fall back to raw contemporaneous scores $\mathbf{s}_t$ without error.
2. **Computational Latency**:
   - `solve_single_stage_entropy_allocation` runs iterative projected gradient descent ($K=37$). At 150 iterations, it takes $\sim 2.5\text{ms}$ in pure NumPy, which is well within the real-time budget ($< 50\text{ms}$).
3. **Eigenvalue Flooring in Small Universes**:
   - In tests with $N < K$ (fewer stocks than strategies), the sample covariance matrix is singular. The existing Marchenko-Pastur bound and Ledoit-Wolf shrinkage handle this, but an explicit check for $N < 5$ must bypass full PCA-ZCA to preserve raw scores.
4. **Backward Compatibility**:
   - Existing unit tests check specific weight outputs (e.g. `test_bear_regime_ensemble`, `test_bull_regime_ensemble`). Default parameters must maintain exact backward compatibility when advanced options are not explicitly triggered.

---

## 4. Conclusion & Milestone 1 Implementation Blueprint

### Key Findings Summary
1. The 2D regime matrix currently omits `CRISIS`, causing dangerous fallback to `SIDEWAYS_LOW_VOL`.
2. Regime transitions trigger abrupt hard weight resets rather than smooth Markov-blended transitions.
3. Sophisticated decay filtering (`apply_exponential_decay_filter`, `apply_rank_ic_decay_calibration`) and KER switching (`apply_ker_dynamic_alpha_switching`) exist in the codebase but are **completely disconnected from the execution path**.
4. The 4-pillar cross-synergy kernel omits 8 of 37 strategies.
5. Single-stage entropy redundancy allocation is implemented but dormant (`use_entropy_allocation=False`).

### Concrete Implementation Blueprint for Milestone 1
| Item | Target File & Class | Method to Modify / Add | Description |
|---|---|---|---|
| **M1-01** | `ensemble_scorer.py`: `EnsembleScoringEngine` | `REGIME_2D_WEIGHTS` | Add dedicated `'CRISIS'` entry across all 37 strategies (sum = 1.0000). |
| **M1-02** | `ensemble_scorer.py`: `EnsembleScoringEngine` | `get_base_weights`, `compute_dynamic_weights_from_sharpe` | Support posterior regime vector $\boldsymbol{\pi}_t$ and compute Markov-blended base weights $\sum \pi_{t, m} \mathbf{w}^{(m)}$. |
| **M1-03** | `ensemble_scorer.py`: `EnsembleScoringEngine` | `compute_dynamic_weights_from_sharpe` | Replace piecewise VIX step rules with continuous TV-distance & VIX entropy adaptive smoothing $\alpha_t$. |
| **M1-04** | `ensemble_scorer.py`: `EnsembleScoringEngine` | `combine_predictions` | Hook `apply_exponential_decay_filter` and `apply_rank_ic_decay_calibration` into the live scoring pipeline with prior state caching. |
| **M1-05** | `ensemble_scorer.py`: `EnsembleScoringEngine` | `compute_dynamic_weights_from_sharpe` | Differentiate `BULL_LOW_VOL` (pure momentum inertia) vs `BULL_HIGH_VOL` (momentum crash risk control). |
| **M1-06** | `ensemble_scorer.py`: `EnsembleScoringEngine` | `compute_bilinear_cross_pillar_synergy` | Expand cluster definitions from 29 to all 37 strategies; make Bessembinder tail power-law parameters regime-adaptive. |
| **M1-07** | `ensemble_scorer.py`, `factor_suppression.py` | `combine_predictions`, `suppress_weights` | Enable `use_entropy_allocation=True` when $N \ge 10$ to solve optimal convex factor redundancy. |
| **M1-08** | `factor_orthogonalizer.py` | `_pca_zca_symmetric`, `orthogonalize` | Protect against zero-variance singular columns under partial missingness. |

---

## 5. Verification Method

### Test Commands to Run:
```bash
# Core Ensemble & Factor Tests
.venv\Scripts\python.exe -m pytest tests/test_regime_ensemble.py tests/test_factor_orthogonalization.py tests/test_correlation_suppression.py tests/test_factor_momentum_and_available_normalization.py tests/test_r1_ensemble_regime_fixes.py -v

# Adversarial Stress Test Suite
.venv\Scripts\python.exe -m pytest tests/test_adversarial_ensemble_scorer_challenger.py -v

# Full Regression Suite
.venv\Scripts\python.exe -m pytest tests/ -k "ensemble or factor or orthogonal" -v
```

### Invalidation Conditions:
1. If adding `'CRISIS'` causes sum of weights in any regime $\neq 1.0000 \pm 10^{-6}$.
2. If hooking `apply_exponential_decay_filter` introduces NaN/Inf values or alters scores when previous scores are None.
3. If Markov transition blending causes any strategy weight to drop below $0.005$ (deadlock threshold).
4. If any of the existing 36 baseline unit tests fail.
