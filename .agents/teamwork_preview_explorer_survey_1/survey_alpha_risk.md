# Phase 66 Alpha & Risk Components Codebase Survey

**Date**: 2026-09-26  
**Investigator**: Teamwork Explorer (Survey Agent 1)  
**Target Milestone**: Phase 67 Quantitative Alpha Enhancement Preparation  
**Scope**:  
1. `trading_system/src/ai/ensemble_scorer.py`
2. `trading_system/src/ai/factor_suppression.py`
3. `trading_system/src/risk/unified_portfolio_allocator.py` & `trading_system/src/risk/portfolio_allocator.py`

---

## 1. Executive Summary

This report delivers a thorough architectural and source-level investigation of the current Phase 66 quantitative alpha and risk allocation implementations within the stock trading system. It provides precise line numbers, function signatures, mathematical expressions, parameter configurations, and alias trees to establish the exact baseline required for the Phase 67 Quantitative Alpha Enhancement (Features F306, F307.1, F307.2, F308.1, F308.2).

### Key Baseline Takeaways
- **Ensemble Coupler**: Currently implemented in `QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler` (`trading_system/src/ai/ensemble_scorer.py`: lines 2299–2702).
  - Coupler parameters: $\kappa_{\text{monster\_whit}} = 19.90$ (used in evaluation/tests; class default 18.50), $\lambda_{\text{monster}} = 0.999995$ (class default 0.99998).
  - Partition action series: 132nd order (`(1.0 / 132.0) * (self.lambda_conformal * 4e-22) * (diff ** 132)` at line 2527).
  - Defect invariant series: 66th order (`(self.lambda_vertex * 4e-24) * (pn[j]**66 - pn[k]**66)` at line 2591).
  - Entanglement output: `FERI_v66` and `feri_v66` computed via $1 / (1 + E + (1 - Z))$ (lines 2598, 2622, 2642–2643).
  - Harmony boost coefficient: Line 21142 currently gates version up to 65 (`4.55 if version >= 65`); Phase 66 specifies $4.65$ and Phase 67 will advance to $4.75$.
- **Noise Deadband & Rank Modulation**: Implemented in both `ensemble_scorer.py` (lines 35–115) and `factor_suppression.py` (lines 567–684).
  - Deadband: `apply_bihexacontatetraoctagonal_hyperbolic_deadband` with $\alpha = 336.0$ (336th order) and $\delta = 0.035$, delivering leakage $< 10^{-252}$ for $|z| \le 0.00035$.
  - Rank Modulation: `compute_phase66_hyperconvex_rank_modulation` with 63rd-order exponent and coefficient $2.30$: $g_{v66}(r) = 0.50 + 2.30 \cdot r \cdot \exp(\gamma_{\text{top}} \cdot r^{63})$ for $z_{\text{denoised}} \ge 0$.
  - Regime Gamma Table: `REGIME_GAMMA_TOP_V66` with `BULL_LOW_VOL`: 16.30, `BULL_HIGH_VOL`: 13.10, `SIDEWAYS`: 9.85, `SIDEWAYS_HIGH_VOL`: 6.55, `BEAR`: 3.30, `BEAR_HIGH_VOL`: 2.50, `CRISIS`: 1.65.
- **Risk Allocation & Tail Measurement**:
  - Higher-Homology Fisher-Rao Barycenter: Implemented as `compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_16_fisher_rao_barycenter_blend` (`unified_portfolio_allocator.py`: lines 1014–1088; `portfolio_allocator.py`: lines 3427–3446) with $\mu = [5.60, 3.80, 3.55, 6.25]$, satisfying $\text{CVaR} > \text{BL} > \text{HERC} > \text{RP}$.
  - Trans-Singular EVaR Risk Measure: Implemented as `compute_trans_singular_..._higher_homology_16_evar_risk_measure` (`unified_portfolio_allocator.py`: lines 6504–6580; `portfolio_allocator.py`: lines 4403–4417) with 64th-cumulant expansion ($64! \approx 1.269 \times 10^{89}$) and $\xi_{\text{monster}} = 0.99999999999997$.
  - Ambiguity Tilting Shifts: `unified_portfolio_allocator.py` lines 15413–15430 with `is_phase66 = int(version) >= 66`, $\epsilon_w = 0.660$, $\delta_{\text{bl}} = -13.50 \epsilon_w - 6.90 u^2$, $\delta_{\text{herc}} = +9.50 \epsilon_w + 5.80 u$, $\delta_{\text{rp}} = -14.00 \epsilon_w$, $\delta_{\text{cvar}} = +20.50 \epsilon_w + 9.00 c_{\text{crisis}}$, $\alpha_{\text{iep}} = 3.80$, $\text{contagion\_damp} = \max(0, 1 - 15.5 \lambda_{\text{casc}})$.

---

## 2. Component 1: `trading_system/src/ai/ensemble_scorer.py`

### 2.1 Class Definition & Parameters
- **Class Name**: `QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler` (line 2299)
- **Primary Method**: `evaluate(self, pillar_scores: Union[pd.DataFrame, Dict[str, Any], np.ndarray]) -> Dict[str, Any]` (line 2394)
- **Class Method**: `compute(...) -> Dict[str, Any]` (line 2356)
- **Parameters**:
  - `theta_0`: float = 0.50 (line 2313)
  - `kappa_monster_whit`: float = 18.50 default (line 2314); Phase 66 production value = 19.90
  - `lambda_monster`: float = 0.99998 default (line 2315); Phase 66 production value = 0.999995
  - `lambda_moonshine`: float = 0.72 (line 2316)
  - `lambda_borcherds`: float = 0.48 (line 2317)
  - `lambda_whittaker`: float = 0.32 (line 2318)
  - `lambda_geometric_langlands`: float = 0.22 (line 2319)
  - `lambda_superalgebra`: float = 0.160 (line 2320)
  - `lambda_chiral_affine`: float = 0.120 (line 2321)
  - `lambda_categorical`: float = 0.080 (line 2322)
  - `lambda_chiral`: float = 0.050 (line 2323)
  - `lambda_vertex`: float = 0.030 (line 2324)
  - `lambda_conformal`: float = 0.020 (line 2325)
  - `epsilon_reg`: float = 1e-6 (line 2326)

### 2.2 Pillar Inputs & Partition Action Expansion
- **Canonical Pillars** (5-dimensional): `['val', 'mom', 'flow', 'cat', 'net']` (lines 2402, 2413).
- **Spatial Metric Matrix**:
  ```python
  omega[j, k] = 1.0 / (abs(j - k) ** 1.35)  # for j != k
  ```
- **Obstruction Action Expansion (`a_monster_whit`)** (lines 2460–2527):
  Taylor-series complex action for pairwise pillar differences $\text{diff} = |p_j - p_k|$:
  - Linear order: $\text{diff}$
  - Quadratic order: $+ 0.5 \cdot \lambda_{\text{monster}} \cdot \text{diff}^2$
  - Up to 12th order: polynomials in $\text{diff}^3, \dots, \text{diff}^{12}$ with conformal scaling.
  - Higher-order terms continue to 132nd order:
    - Line 2526: `+ (1.0 / 130.0) * (self.lambda_conformal * 1e-21) * (diff ** 130)`
    - Line 2527: `+ (1.0 / 132.0) * (self.lambda_conformal * 4e-22) * (diff ** 132))`
  - Total Obstruction Energy:
    ```python
    obs_energy += w * a_monster_whit
    ```

### 2.3 Topological Defect Invariant Series
- **Defect Series (`defect`)** (lines 2530–2592):
  Difference-of-powers across pillar coordinates:
  - 2nd order: $|p_j^2 - p_k^2|$
  - 3rd order: $+ \lambda_{\text{monster}} (p_j^3 - p_k^3)$
  - Higher-order terms through 66th order:
    - Line 2588: `+ (self.lambda_vertex * 1e-22) * (pn[j]**63 - pn[k]**63)`
    - Line 2589: `+ (self.lambda_vertex * 4e-23) * (pn[j]**64 - pn[k]**64)`
    - Line 2590: `+ (self.lambda_vertex * 1e-23) * (pn[j]**65 - pn[k]**65)`
    - Line 2591: `+ (self.lambda_vertex * 4e-24) * (pn[j]**66 - pn[k]**66))`
  - Total Defect:
    ```python
    topol_defect += w * defect
    ```

### 2.4 FERI Computation & Output Formatting
- **Formulas** (lines 2596–2599):
  ```python
  h_decay = np.exp(-self.kappa_monster_whit * e_monster_whit)
  h_monster_whit = np.clip(h_decay * z_monster_whit, self.epsilon_reg, 1.0)
  feri_v66 = 1.0 / (1.0 + e_monster_whit + (1.0 - z_monster_whit))
  feri_v65 = feri_v66
  ```
- **Return Formatting** (lines 2618–2636):
  Scalar for 1D single vector, `pd.Series` for indexed inputs, `np.ndarray` otherwise:
  - `f_out_66 = float(feri_v66[0]) if is_single_1d else (pd.Series(feri_v66, index=index) if index is not None else feri_v66)`
- **Dictionary Keys** (lines 2637–2701):
  Returns `"FERI_v66"`, `"feri_v66"`, `"FERI_v65"`, ..., `"h_monster_whit"`, `"z_monster_whit"`, `"e_monster_whit"`, `"Z_monster_whit"`, `"E_monster_whit"`.

### 2.5 Integration into Ensemble Scoring Pipeline
1. **Pillar Confluence / Coupler Call** (`trading_system/src/ai/ensemble_scorer.py`: lines 21056–21063):
   ```python
   # Phase 48 (R1, Feature F211): Quantum Geometric Langlands Chiral Affine Lie Superalgebra Borcherds-Moonshine-Monster Whittaker Coupler
   if version >= 48:
       monster_whit_res = cls.compute_quantum_geometric_langlands_borcherds_moonshine_monster_whittaker_coupling(p_vals.T)
       h_monster_whit = np.atleast_1d(monster_whit_res["h_monster_whit"]).astype(np.float64)
       z_monster_whit = np.atleast_1d(monster_whit_res["z_monster_whit"]).astype(np.float64)
   else:
       h_monster_whit = np.zeros_like(h_clausen)
       z_monster_whit = np.zeros_like(z_liquid)
   ```
2. **Harmony Boost Multiplier** (lines 21110–21142):
   Line 21142 currently implements:
   ```python
   + ((4.55 if version >= 65 else (4.45 if version >= 64 else (4.35 if version >= 63 else (4.25 if version >= 62 else (4.15 if version >= 61 else (4.05 if version >= 60 else (3.95 if version >= 59 else (3.85 if version >= 58 else (3.75 if version >= 57 else (3.65 if version >= 56 else (3.55 if version >= 55 else (3.45 if version >= 54 else (3.35 if version >= 53 else (3.25 if version >= 52 else (3.15 if version >= 51 else (3.05 if version >= 50 else 2.95 if version >= 49 else 2.85)))))))))))))))) * h_monster_whit * z_monster_whit if version >= 48 else 0.0)) * (p_mean > 0.35).astype(float)
   ```
   *Note for Phase 67*: Line 21142 needs to be prepended with `(4.75 if version >= 67 else (4.65 if version >= 66 else (4.55 if version >= 65 ...)))`.
3. **Cross-Sectional Rank Modulation Gating** (lines 19206–19210):
   ```python
   ranks = pd.Series(ens_scores).rank(pct=True).values
   if int(version) >= 66:
       mult = compute_phase66_hyperconvex_rank_modulation(ranks, z_denoised=z_denoised, regime=regime)
   elif int(version) >= 65:
       mult = compute_phase65_hyperconvex_rank_modulation(ranks, z_denoised=z_denoised, regime=regime)
   ```
4. **Regime Adaptive Gamma Top Gating** (lines 27219–27222):
   ```python
   if int(version) >= 66:
       return get_regime_adaptive_gamma_top_v66(regime)
   elif int(version) >= 65:
       return get_regime_adaptive_gamma_top_v65(regime)
   ```
5. **Noise Deadband Gating** (lines 27926–27935):
   Currently, line 27926 has `if int(version) >= 65: return apply_bicentatetracontaoctagonal_hyperbolic_deadband(...)`.
   *Note for Phase 67*: Should cleanly gate `if int(version) >= 67: return apply_..._v67(...) elif int(version) >= 66: return apply_bihexacontatetraoctagonal_hyperbolic_deadband(...)`.

### 2.6 Full Coupler Alias Trees in `ensemble_scorer.py`
- Module-level Phase 66 aliases (lines 2704–2708):
  - `Phase66Coupler = QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler`
  - `Phase66WhittakerDrinfeldCoupler = QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler`
  - `Phase66BorcherdsMoonshineCoupler = QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler`
  - `Phase66MonsterWhittakerCoupler = QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler`
- Class-level static bindings inside `EnsembleScoringEngine` (lines 24210–24213):
  - `EnsembleScoringEngine.Phase66Coupler`
  - `EnsembleScoringEngine.Phase66WhittakerDrinfeldCoupler`
  - `EnsembleScoringEngine.Phase66BorcherdsMoonshineCoupler`
  - `EnsembleScoringEngine.Phase66MonsterWhittakerCoupler`

---

## 3. Component 2: `trading_system/src/ai/factor_suppression.py`

### 3.1 Asymmetric Bihexacontatetraoctagonal Hyperbolic Deadband
- **Location**: `trading_system/src/ai/factor_suppression.py`: lines 567–609. (Also defined in `ensemble_scorer.py`: lines 35–58).
- **Signature**:
  ```python
  def apply_bihexacontatetraoctagonal_hyperbolic_deadband(
      scores_centered: Union[pd.Series, np.ndarray, float],
      delta_noise: float = 0.035,
      delta_neg: Optional[float] = None,
      alpha_pos: float = 336.0,
      alpha_neg: Optional[float] = None,
      regime: Optional[Union[str, int]] = None,
      **kwargs
  ) -> Union[pd.Series, np.ndarray, float]:
  ```
- **Mathematical Form**:
  $$z_{\text{denoised}} = z \cdot \tanh\left( \left(\frac{|z|}{\delta_{\text{eff}}(z)}\right)^{336} \right)$$
- **Leakage & Monotonicity Properties**:
  - Exponent: $\alpha = 336.0$
  - Threshold: $\delta = 0.035$
  - Near-zero noise: for $|z| \le 0.00035$ ($z / \delta \le 0.01$), $(0.01)^{336} = 10^{-672} \to 0.0$ under IEEE 754 float64 (noise leakage strictly $< 10^{-252}$).
  - Signal transmission: for $|z| \ge 0.150$ ($z / \delta \ge 4.285$), $\tanh(4.285^{336}) = 1.0000000000 \to 100.000\%$ transmission.
  - Odd symmetry: $f(-z) = -f(z)$.
- **Alias Tree in `factor_suppression.py`** (lines 601–608):
  - `compute_phase66_deadband = apply_bihexacontatetraoctagonal_hyperbolic_deadband`
  - `apply_phase66_deadband = apply_bihexacontatetraoctagonal_hyperbolic_deadband`
  - `apply_bihexacontatetraoctagonal_deadband = apply_bihexacontatetraoctagonal_hyperbolic_deadband`
  - `bihexacontatetraoctagonal_deadband = apply_bihexacontatetraoctagonal_hyperbolic_deadband`
  - `phase66_deadband = apply_bihexacontatetraoctagonal_hyperbolic_deadband`
  - `apply_bihexacontatetra_hyperbolic_deadband = apply_bihexacontatetraoctagonal_hyperbolic_deadband`
  - `apply_bihexacontadecaoctagonal_hyperbolic_deadband = apply_bihexacontatetraoctagonal_hyperbolic_deadband`
  - `apply_bihexacontatetraicosaoctagonal_hyperbolic_deadband = apply_bihexacontatetraoctagonal_hyperbolic_deadband`

### 3.2 Regime Gamma Top Table & Lookup Function
- **Location**: lines 611–640.
- **Table Definition**:
  ```python
  REGIME_GAMMA_TOP_V66 = {
      'BULL_LOW_VOL': 16.30,
      'BULL_HIGH_VOL': 13.10,
      'SIDEWAYS': 9.85,
      'SIDEWAYS_LOW_VOL': 9.85,
      'SIDEWAYS_HIGH_VOL': 6.55,
      'BEAR': 3.30,
      'BEAR_LOW_VOL': 3.30,
      'BEAR_HIGH_VOL': 2.50,
      'PANIC': 1.65,
      'CRISIS': 1.65,
      'RECOVERY': 13.10,
      '2': 16.30,
      '1': 9.85,
      '0': 3.30,
      'UNKNOWN': 16.30,
  }
  ```
- **Lookup Function**:
  ```python
  def get_regime_adaptive_gamma_top_v66(regime: Union[int, str] = 'BULL_LOW_VOL') -> float:
      if isinstance(regime, (int, float)):
          regime_str = str(int(regime))
      else:
          regime_str = str(regime).upper()
      return REGIME_GAMMA_TOP_V66.get(regime_str, REGIME_GAMMA_TOP_V66.get('BULL_LOW_VOL', 16.30))
  ```

### 3.3 63rd-Order Hyper-Convex Rank Modulation
- **Location**: lines 643–682.
- **Signature**:
  ```python
  def compute_phase66_hyperconvex_rank_modulation(
      ranks: Union[pd.Series, np.ndarray, float],
      gamma_top: Optional[float] = None,
      z_denoised: Optional[Union[pd.Series, np.ndarray, float]] = None,
      regime: Optional[Union[str, int]] = None,
      **kwargs
  ) -> Union[pd.Series, np.ndarray, float]:
  ```
- **Formulas**:
  - Positive conviction ($z_{\text{denoised}} \ge 0$):
    $$g_{v66}(r) = 0.50 + 2.30 \cdot r \cdot \exp(\gamma_{\text{top}} \cdot r^{63})$$
  - Negative conviction ($z_{\text{denoised}} < 0$):
    $$g_{\text{neg}}(r) = 1.35 - 1.00 \cdot r$$
  - Order: 63rd order
  - Coefficient: $2.30$
  - Base: $0.50$
  - Boundary values:
    - At $r = 0$: $g(0) = 0.50$
    - At $r = 0.70$: $g(0.70) \le 2.20$
    - At $r = 1.00$ under `BULL_LOW_VOL` ($\gamma_{\text{top}} = 16.30$):
      $$g(1.00) = 0.50 + 2.30 \cdot \exp(16.30) \approx 2.766 \times 10^7 > 10^7$$
- **Alias Tree in `factor_suppression.py`** (lines 679–682):
  - `compute_phase66_rank_warping = compute_phase66_hyperconvex_rank_modulation`
  - `compute_phase66_rank_modulation = compute_phase66_hyperconvex_rank_modulation`
  - `phase66_rank_modulation = compute_phase66_hyperconvex_rank_modulation`
  - `phase66_hyperconvex_rank_modulation = compute_phase66_hyperconvex_rank_modulation`

---

## 4. Component 3: Risk Allocation & Portfolio Allocators

### 4.1 Higher-Homology-16 Fisher-Rao Barycenter Blending
- **Target Files**:
  - `trading_system/src/risk/unified_portfolio_allocator.py`: lines 1014–1099
  - `trading_system/src/risk/portfolio_allocator.py`: lines 3427–3458
- **Signature (`UnifiedPortfolioAllocator`)**:
  ```python
  def compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_16_fisher_rao_barycenter_blend(
      self,
      model_weights: Union[Dict[str, float], List[Dict[str, float]], np.ndarray],
      max_iter: int = 50,
      tol: float = 1e-6,
      step_size: float = 0.50,
  ) -> Dict[str, float]:
  ```
- **Curvature Vector**:
  $$\mu_{\text{lmbwdh16}} = [5.60, 3.80, 3.55, 6.25]$$
  Ordering: $\text{CVaR} (6.25) > \text{BL} (5.60) > \text{HERC} (3.80) > \text{RP} (3.55)$.
- **Mathematical Form**:
  $$q^* = \arg\min_{q \in \Delta^3} \sum_m \alpha_m D_{\text{FR}}^2(q, p^{(m)})$$
  Optimized via Riemannian gradient ascent/descent:
  ```python
  grad = 2.0 * mu_sq * (q - q_target) / (np.sqrt(q) + 1e-8)
  q_new = q * np.exp(-step_size * grad)
  q_new /= np.sum(q_new)
  ```
- **Simplex Invariant**:
  $$\sum_{k \in \{\text{bl, herc, rp, cvar}\}} q_k = 1.000000 \quad (\text{rel\_tol} \le 10^{-5})$$
- **Alias Tree in `unified_portfolio_allocator.py`** (lines 1089–1098):
  - `compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_16_barycenter`
  - `compute_lurie_drinfeld_higher_homology_16_barycenter`
  - `compute_phase66_fisher_rao_barycenter`
  - `compute_phase66_barycenter_blend`
  - `compute_phase66_barycenter`
  - `compute_higher_homology_16_barycenter`
  - `phase66_fisher_rao_barycenter`
  - `phase66_homology_barycenter`
  - `higher_homology_16_fisher_rao_blend`
  - `higher_homology_16_blend`
- **Alias Tree in `portfolio_allocator.py`** (lines 3448–3457):
  - `compute_lmbmwdh16_fisher_rao_barycenter_blend`
  - `compute_homology_16_barycenter`
  - `compute_phase66_barycenter`
  - `phase66_barycenter_blend`
  - `compute_higher_homology_16_barycenter`
  - `lmbmwdh16_barycenter`
  - `drinfeld_higher_homology_16_barycenter`
  - `monster_moonshine_higher_homology_16_barycenter`
  - `borcherds_higher_homology_16_barycenter`
  - `compute_phase66_fisher_rao_barycenter`

### 4.2 64th-Cumulant Expansion Trans-Singular EVaR
- **Target Files**:
  - `trading_system/src/risk/unified_portfolio_allocator.py`: lines 6504–6594
  - `trading_system/src/risk/portfolio_allocator.py`: lines 4403–4428
- **Signature (`UnifiedPortfolioAllocator`)**:
  ```python
  def compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_16_evar_risk_measure(
      self,
      returns: Union[np.ndarray, pd.Series, List[float]],
      alpha: float = 0.05,
      t_grid: Optional[Union[np.ndarray, List[float]]] = None,
      xi_monster: float = 0.99999999999997,
      order: int = 64,
      **kwargs
  ) -> Dict[str, float]:
  ```
- **Mathematical Form**:
  $$\text{EVaR}_\alpha(X) = \inf_{t > 0} \left\{ \frac{K_X(t) + \ln(1/\alpha)}{t} \right\}$$
  where the 64th-order cumulant generates:
  $$\text{cumulant\_high} = \xi_{\text{monster}} \cdot \frac{\mu_{64}}{64!} \cdot t^{64}$$
  with $64! \approx 1.268869321858841 \times 10^{89}$ and $\xi_{\text{monster}} = 0.99999999999997$.
- **Alias Tree in `unified_portfolio_allocator.py`** (lines 6582–6593):
  - `compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_16_evar`
  - `compute_phase66_evar`
  - `compute_phase66_evar_risk_measure`
  - `compute_evar_order64`
  - `compute_64th_cumulant_evar`
  - `higher_homology_16_evar`
  - `phase66_tail_risk_evar`
  - `compute_lmbmwdh16_evar`
  - `lmbmwdh16_evar`
  - `evar_64th_cumulant`
  - `phase66_evar_bound`
  - `trans_singular_evar_v66`
- **Alias Tree in `portfolio_allocator.py`** (lines 4419–4427):
  - `compute_phase66_evar`
  - `compute_phase66_evar_risk_measure`
  - `compute_evar_order64`
  - `higher_homology_16_evar`
  - `phase66_tail_risk_evar`
  - `compute_lmbmwdh16_evar`
  - `lmbmwdh16_evar`
  - `evar_64th_cumulant`
  - `phase66_evar_bound`

### 4.3 Ambiguity Tilting & Dynamic Gating in Allocator Pipeline
- **Method**: `compute_information_theoretic_blend_weights` (`unified_portfolio_allocator.py`: lines 15300–15600)
- **Version Gating Flag** (line 15351):
  ```python
  is_phase66 = int(version) >= 66
  is_phase65 = (int(version) >= 65) or is_phase66
  ```
- **Ambiguity Shifting Block** (lines 15413–15430):
  ```python
  if is_phase66:
      # Phase 66 (Feature F301.1/F301.2): Lurie-Borcherds-Monster-Moonshine-Whittaker-Drinfeld Higher-Homology-16 Motivic Fisher-Rao Ambiguity Tilting
      eps_w = float(wasserstein_radius) if (wasserstein_radius is not None and math.isfinite(float(wasserstein_radius))) else 0.660
      delta_monster_whittaker = {
          "bl": -13.50 * eps_w - 6.90 * (u_entropy ** 2),
          "herc": +9.50 * eps_w + 5.80 * u_entropy,
          "rp": -14.00 * eps_w,
          "cvar": +20.50 * eps_w + 9.00 * c_crisis,
      }
      for k in delta_ell:
          delta_ell[k] += delta_monster_whittaker[k]

      # Hyper-Information Entropy Parity (Phase 66)
      alpha_iep = 3.80
      contagion_damp = max(0.0, 1.0 - 15.5 * lam_casc)
      for k in delta_ell:
          delta_ell[k] *= (1.0 + 0.33 * alpha_iep)
  ```
- **Refinement inside `calculate_weights`** (lines 16852–16854):
  ```python
  if is_phase66:
      # Phase 66 (Feature F301.1): Apply Lurie-Borcherds-Monster-Moonshine-Whittaker-Drinfeld Higher-Homology-16 Motivic Fisher-Rao Barycenter refinement
      res_weights = self.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_16_fisher_rao_barycenter_blend(res_weights)
  ```

---

## 5. Phase 66 → Phase 67 Progression Mapping

The following table provides the exact quantitative progression mapping from Phase 66 to Phase 67 across all surveyed components:

| Component / Parameter | Phase 66 Specification | Phase 67 Target | Target File(s) & Line Reference |
|---|---|---|---|
| **Coupler $\kappa_{\text{monster\_whit}}$** | $19.90$ | $20.60$ | `ensemble_scorer.py`: lines 2314, 2360 |
| **Coupler $\lambda_{\text{monster}}$** | $0.999995$ | $0.999998$ | `ensemble_scorer.py`: lines 2315, 2361 |
| **Partition Actions Order** | 130th / 132nd order | 134th / 136th order | `ensemble_scorer.py`: lines 2526–2527 |
| **Defect Invariants Order** | 65th / 66th order | 67th / 68th order | `ensemble_scorer.py`: lines 2590–2591 |
| **Harmony Boost Coeff** | $4.65$ | $4.75$ | `ensemble_scorer.py`: line 21142 |
| **FERI Output Keys** | `FERI_v66`, `feri_v66` | `FERI_v67`, `feri_v67` | `ensemble_scorer.py`: lines 2598, 2622, 2642 |
| **Deadband Exponent $\alpha$** | $336.0$ | $344.0$ | `factor_suppression.py`: lines 571, 578; `ensemble_scorer.py`: line 39 |
| **Deadband Leakage Floor** | $< 10^{-252}$ | $< 10^{-258}$ | `factor_suppression.py`: lines 580, 703 |
| **Rank Modulation Order** | 63rd order | 65th order | `factor_suppression.py`: lines 652, 666; `ensemble_scorer.py`: line 94 |
| **Rank Modulation Coeff** | $2.30$ | $2.35$ | `factor_suppression.py`: lines 652, 666; `ensemble_scorer.py`: line 94 |
| **gamma_top BULL_LOW_VOL** | $16.30$ | $16.65$ | `factor_suppression.py`: line 612; `ensemble_scorer.py`: line 68 |
| **gamma_top BULL_HIGH_VOL** | $13.10$ | $13.40$ | `factor_suppression.py`: line 613; `ensemble_scorer.py`: line 69 |
| **gamma_top SIDEWAYS** | $9.85$ | $10.10$ | `factor_suppression.py`: line 614; `ensemble_scorer.py`: line 68 |
| **gamma_top SIDEWAYS_HIGH_VOL** | $6.55$ | $6.70$ | `factor_suppression.py`: line 616; `ensemble_scorer.py`: line 69 |
| **gamma_top BEAR** | $3.30$ | $3.40$ | `factor_suppression.py`: line 617; `ensemble_scorer.py`: line 69 |
| **gamma_top BEAR_HIGH_VOL** | $2.50$ | $2.60$ | `factor_suppression.py`: line 619; `ensemble_scorer.py`: line 69 |
| **gamma_top CRISIS** | $1.65$ | $1.70$ | `factor_suppression.py`: line 621; `ensemble_scorer.py`: line 70 |
| **Barycenter Vector $\mu$** | `[5.60, 3.80, 3.55, 6.25]` | `[5.70, 3.85, 3.50, 6.40]` | `unified_portfolio_allocator.py`: line 1032 |
| **Barycenter Homology Name** | Higher-Homology-16 | Higher-Homology-17 | `unified_portfolio_allocator.py`: lines 1014, 1022 |
| **EVaR Cumulant Order** | 64th ($64! \approx 1.27 \times 10^{89}$) | 66th ($66! \approx 5.44 \times 10^{92}$) | `unified_portfolio_allocator.py`: lines 6510, 6517 |
| **EVaR $\xi_{\text{monster}}$** | $0.99999999999997$ | $0.99999999999998$ | `unified_portfolio_allocator.py`: lines 6509, 6517 |
| **Regime $\epsilon_w$** | $0.660$ | $0.670$ | `unified_portfolio_allocator.py`: line 15415 |
| **$\delta_{\text{bl}}$ Shift** | $-13.50 \epsilon_w - 6.90 u^2$ | $-14.00 \epsilon_w - 7.00 u^2$ | `unified_portfolio_allocator.py`: line 15417 |
| **$\delta_{\text{herc}}$ Shift** | $+9.50 \epsilon_w + 5.80 u$ | $+10.00 \epsilon_w + 5.90 u$ | `unified_portfolio_allocator.py`: line 15418 |
| **$\delta_{\text{rp}}$ Shift** | $-14.00 \epsilon_w$ | $-14.50 \epsilon_w$ | `unified_portfolio_allocator.py`: line 15419 |
| **$\delta_{\text{cvar}}$ Shift** | $+20.50 \epsilon_w + 9.00 c_{\text{crisis}}$ | $+21.50 \epsilon_w + 9.50 c_{\text{crisis}}$ | `unified_portfolio_allocator.py`: line 15420 |
| **Hyper-IEP $\alpha_{\text{iep}}$** | $3.80$ | $3.85$ | `unified_portfolio_allocator.py`: line 15426 |
| **Contagion Damping** | $15.5$ ($\max(0, 1 - 15.5 \lambda_{\text{casc}})$) | $16.0$ ($\max(0, 1 - 16.0 \lambda_{\text{casc}})$) | `unified_portfolio_allocator.py`: line 15427 |
| **Version Gating Flag** | `is_phase66 = int(version) >= 66` | `is_phase67 = int(version) >= 67` | `unified_portfolio_allocator.py`: line 15351 |

---

## 6. Implementation Notes for Subsequent Phases

1. **Deadband Function Naming**:
   - Phase 65: `apply_bicentatetracontaoctagonal_hyperbolic_deadband` ($\alpha = 328.0$)
   - Phase 66: `apply_bihexacontatetraoctagonal_hyperbolic_deadband` ($\alpha = 336.0$)
   - Phase 67: Exponent $\alpha = 344.0$ corresponds to order 344 (tetra-tetraconta-tria-centagonal or similar polygon prefix convention, e.g. `apply_bicentatetratetracontaoctagonal_hyperbolic_deadband` or standardized alias `apply_phase67_deadband`). Complete alias trees will ensure robust access.
2. **Rank Modulation Order**:
   - Phase 66: 63rd order ($r^{63}$)
   - Phase 67: 65th order ($r^{65}$) with coefficient $2.35$.
3. **Higher-Homology Indexing**:
   - Phase 65: Higher-Homology-15
   - Phase 66: Higher-Homology-16
   - Phase 67: Higher-Homology-17
4. **Backward Compatibility**:
   - Ensure all existing versions ($50 \le v \le 66$) retain exact numerical results and simplex properties.
   - All tests in `test_phase66_alpha.py` and `test_phase66_risk.py` must remain 100% passing when Phase 67 code is added.
