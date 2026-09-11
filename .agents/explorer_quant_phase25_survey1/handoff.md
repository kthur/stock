# Phase 25 Quant Enhancement — Survey 1 Handoff Report: Alpha Signal Specialist

**Target Role**: Worker (Alpha Signal Specialist Implementation)  
**Author**: Explorer 1 (Alpha Signal Specialist Explorer)  
**Date**: 2026-09-11  
**Working Directory**: `d:\Finance\code\stock\.agents\explorer_quant_phase25_survey1`  
**Milestone**: Milestone R1 (Phase 25 Alpha Signal Innovations: F119, F120.1, F120.2)

---

## 1. Observation

Direct inspection of the codebase yielded the following observations:

### 1.1 System Request Specifications (`ORIGINAL_REQUEST.md` lines 785–828)
```markdown
### R1. 37대 전략 다이나믹 알파 결합 및 신호 고도화 (Phase 25)
Non-Abelian Hodge Theory & Deligne-Simpson Spectral Moduli 기반 팩터 얽힘 해소 커플러(F119, 히친 방정식 \bar{\partial}_E \Phi = 0, F_A + [\Phi, \Phi^*] = 0 조화 다발 장애 복합체 E_hodge, 들리뉴-심슨 스펙트럼 모듈라이 불변량 Z_simpson)를 ensemble_scorer.py와 factor_suppression.py에 구현합니다.
상위 0.00000000001% 초극단 확신 자본 집중을 위한 20차 초볼록 순위 변조 함수:
    g_v25(r) = 0.50 + 1.14 * r * exp(gamma_top * r^20)
(F120.1, 레짐 적응형 gamma_top 최대 2.60)와 64차 Hexatetrahedral(alpha=64.0) 쌍곡선 데드밴드(F120.2, 노이즈 누출률 < 10^-34)를 factor_suppression.py에 추가하고, ensemble_scorer.py의 버전 분기(version >= 25)에서 이를 호출하여 Rank-IC와 선형 예측력을 추가 개선합니다.
```

### 1.2 Existing Phase 24 Hook Points in `trading_system/src/ai/ensemble_scorer.py`
1. **Module Header & Registration (Lines 28–324)**:
   - Defines `apply_hexacontagonal_hyperbolic_deadband` (alpha=60.0, leakage < 10^-32).
   - Defines `compute_phase24_hyperconvex_rank_modulation` and alias `compute_phase24_rank_warping`.
   - Defines `DerivedArithmeticTopologyCoupler` and aliases (`EtaleMotivicSpectralHomotopyCoupler`, `DerivedArithmeticCoupler`, `EtaleMotivicCoupler`, `ArtinVerdierDualityCoupler`, `MotivicSpectralHomotopyCoupler`, `ArithmeticTopologyCoupler`).
   - Dynamically registers all classes and methods onto `trading_system.src.ai.factor_suppression` using `setattr`.

2. **Rank Modulation Branch in `combine_predictions` (Line 6999)**:
   ```python
   # Line 6999
   if int(version) >= 24:
       gamma_top = self.get_regime_adaptive_gamma_top(regime, version=version)
       mult = np.where(
           z_denoised >= 0.0,
           0.50 + 1.12 * ranks * np.exp(gamma_top * (ranks ** 19)),
           1.35 - 1.00 * ranks
       )
   elif int(version) >= 23:
   ```

3. **Harmony Factor / Synergy Branch in `compute_quint_pillar_tensor_synergy` (Line 8533)**:
   ```python
   # Line 8533
   if version >= 24:
       ...
       arith_res = cls.compute_derived_arithmetic_topology_coupling(p_vals.T)
       h_arith = np.atleast_1d(arith_res["h_arithmetic"]).astype(np.float64)
       z_spectral = np.atleast_1d(arith_res["z_spectral"]).astype(np.float64)
       ...
       harmony_factor = pd.Series(
           1.0 + (... + 0.95 * h_langlands * z_satake
                  + 1.05 * h_arith * z_spectral) * (p_mean > 0.35).astype(float),
           index=scores_df.index
       )
   elif version >= 23:
   ```

4. **Class Attributes & Methods in `EnsembleScoringEngine` (Lines 9702–9748)**:
   ```python
   apply_hexacontagonal_hyperbolic_deadband = staticmethod(apply_hexacontagonal_hyperbolic_deadband)
   compute_phase24_hyperconvex_rank_modulation = staticmethod(compute_phase24_hyperconvex_rank_modulation)
   compute_phase24_rank_warping = staticmethod(compute_phase24_hyperconvex_rank_modulation)
   DerivedArithmeticTopologyCoupler = DerivedArithmeticTopologyCoupler
   ...
   @classmethod
   def compute_derived_arithmetic_topology_coupling(cls, pillar_scores, ...):
       return DerivedArithmeticTopologyCoupler.compute(...)
   ```

5. **Regime-Adaptive Gamma Top in `get_regime_adaptive_gamma_top` (Lines 10499–10522)**:
   ```python
   if int(version) >= 24:
       if 'CRISIS' in reg_str: return 1.50
       elif 'BEAR_HIGH_VOL' in reg_str: return 0.75
       elif 'BEAR_LOW_VOL' in reg_str or reg_str == '0': return 1.85
       elif 'BEAR' in reg_str: return 1.85
       elif 'SIDEWAYS_HIGH_VOL' in reg_str: return 1.45
       elif 'SIDEWAYS_LOW_VOL' in reg_str or reg_str == '1': return 2.10
       elif 'SIDEWAYS' in reg_str: return 2.10
       elif 'BULL_HIGH_VOL' in reg_str: return 2.30
       elif 'BULL_LOW_VOL' in reg_str or reg_str == '2': return 2.50
       elif 'BULL' in reg_str: return 2.50
       else: return 2.00
   ```

6. **Smooth Deadband Dispatch in `apply_smooth_noise_deadband` (Lines 10889–10898)**:
   ```python
   if int(version) >= 24:
       eff_alpha = 60.0 if alpha_pos in (...) else alpha_pos
       return apply_hexacontagonal_hyperbolic_deadband(...)
   ```

### 1.3 Existing Phase 24 Implementation in `trading_system/src/ai/factor_suppression.py`
1. **Deadband Definition (Lines 450–482)**:
   `apply_hexacontagonal_hyperbolic_deadband` with `alpha_pos=60.0`.
2. **Rank Modulation & Tables (Lines 484–558)**:
   `compute_phase24_hyperconvex_rank_modulation`, `compute_phase24_rank_warping`, `REGIME_GAMMA_TOP_V24`, `get_regime_adaptive_gamma_top_v24`.
3. **Deadband Attenuation Dispatch (Lines 687–696)**:
   `if version >= 24:` dispatches to `apply_hexacontagonal_hyperbolic_deadband`.
4. **Export Declarations (Lines 1301–1371)**:
   `__all__` list and `__getattr__` hook for dynamic lazy loading of Phase 24 couplers.

### 1.4 Test Suite Baseline Verification (`tests/test_phase24_alpha.py`)
- Executed `.venv\Scripts\pytest tests/test_phase24_alpha.py -v`.
- Result: **14 passed in 15.97s** (code 0).
- Confirmed test coverage structure:
  1. Deadband noise leakage (< 10^-32) and pass-through/monotonicity
  2. Coupler invariant boundedness, zero obstruction on coherent inputs, adversarial conflict suppression, input formats (1D, 2D, dict, DataFrame)
  3. Synergy integration in `compute_quint_pillar_tensor_synergy`
  4. 19th-order rank modulation values, convexity ($d^2/dr^2 \ge 0$), regime gamma table
  5. Full pipeline `combine_predictions` execution under version=24 and backward compatibility from v13 to v24.

---

## 2. Logic Chain

1. **Architecture Continuity**:
   Every phase follows an exact mathematical progression for three core alpha signal components:
   - **Hyperbolic Deadband Order**:
     Phase 20 (44th) $\to$ Phase 21 (48th) $\to$ Phase 22 (52nd) $\to$ Phase 23 (56th) $\to$ Phase 24 (60th) $\to$ **Phase 25 (64th Hexatetrahedral, $\alpha = 64.0$)**.
   - **Hyperconvex Rank Modulation**:
     Phase 20 (15th, coeff 1.04) $\to$ Phase 21 (16th, coeff 1.06) $\to$ Phase 22 (17th, coeff 1.08) $\to$ Phase 23 (18th, coeff 1.10) $\to$ Phase 24 (19th, coeff 1.12) $\to$ **Phase 25 (20th-order, coeff 1.14, formula $g_{\text{v25}}(r) = 0.50 + 1.14 \cdot r \cdot \exp(\gamma_{\text{top}} \cdot r^{20})$)**.
   - **Regime-Adaptive Maximum $\gamma_{\text{top}}$**:
     Phase 22 (2.25) $\to$ Phase 23 (2.40) $\to$ Phase 24 (2.50) $\to$ **Phase 25 (2.60)**.
   - **Pillar Disentanglement Coupler**:
     Phase 23 (Toposic Geometric Langlands) $\to$ Phase 24 (Derived Arithmetic Topology) $\to$ **Phase 25 (Non-Abelian Hodge Theory & Deligne-Simpson Spectral Moduli, Feature F119)**.
   - **Synergy Harmony Weight in `compute_quint_pillar_tensor_synergy`**:
     Phase 22 (+0.85) $\to$ Phase 23 (+0.95) $\to$ Phase 24 (+1.05) $\to$ **Phase 25 (+1.15 $\cdot h_{\text{hodge}} \cdot z_{\text{simpson}}$)**.

2. **Exact Mathematical Modeling for F119**:
   - **Non-Abelian Hodge Theory (Hitchin–Simpson Correspondence)**:
     Higgs bundle $(E, \bar{\partial}_E, \Phi)$ satisfies Hitchin's equations:
     $$\bar{\partial}_E \Phi = 0, \quad F_A + [\Phi, \Phi^*] = 0$$
     When economic pillars $P = (p_{\text{val}}, p_{\text{mom}}, p_{\text{flow}}, p_{\text{cat}}, p_{\text{net}})$ agree, the Higgs field is proportional to scalar gauge sections, curvature $F_A = 0$, and the commutator $[\Phi, \Phi^*] = 0$, yielding **zero obstruction**:
     $$E_{\text{hodge}} = 0, \quad Z_{\text{simpson}} = 1.0, \quad h_{\text{hodge}} = 1.0, \quad \text{FERI}_{\text{v25}} = 1.0$$
   - **20th-Degree Hitchin Harmonic Bundle Obstruction Action**:
     Across pillar pairs $(j, k)$ with difference $\Delta = p_j - p_k$ and coupling weight $w_{jk} = |\Omega_{j, k}| = \theta_0 \cdot \frac{|j - k|}{1 + |j - k|}$ ($\theta_0 = 0.34$):
     $$a_{\text{hodge}}(\Delta) = 0.5 \Delta^2 + \lambda_{\text{hodge}} (1 - \cos(\pi \Delta)) + \frac{1}{4} \lambda_{\text{simpson}} \Delta^4 + \frac{1}{6} \lambda_{\text{hitchin}} \Delta^6 + \frac{1}{8} \lambda_{\text{harmonic}} \Delta^8 + \frac{1}{10} \lambda_{\text{spectral}} \Delta^{10} + \frac{1}{12} (0.6 \lambda_{\text{spectral}}) \Delta^{12} + \frac{1}{16} (0.3 \lambda_{\text{spectral}}) \Delta^{16} + \frac{1}{20} (0.15 \lambda_{\text{spectral}}) \Delta^{20}$$
     Parameters: $\kappa_{\text{hodge}} = 3.40, \lambda_{\text{hodge}} = 0.24, \lambda_{\text{simpson}} = 0.11, \lambda_{\text{hitchin}} = 0.075, \lambda_{\text{harmonic}} = 0.050, \lambda_{\text{spectral}} = 0.030$.
     $$E_{\text{hodge}} = \sum_{j < k} w_{jk} \cdot a_{\text{hodge}}(p_j - p_k)$$
   - **Deligne-Simpson Spectral Moduli Cycle Defect**:
     $$\text{defect}_{jk} = |(p_j^2 - p_k^2) + \lambda_{\text{simpson}} (p_j^3 - p_k^3) + \lambda_{\text{hitchin}} (p_j^4 - p_k^4) + \lambda_{\text{harmonic}} (p_j^5 - p_k^5) + \lambda_{\text{spectral}} (p_j^6 - p_k^6) + (0.6 \lambda_{\text{spectral}}) (p_j^7 - p_k^7) + (0.3 \lambda_{\text{spectral}}) (p_j^8 - p_k^8) + (0.15 \lambda_{\text{spectral}}) (p_j^9 - p_k^9)|$$
     $$\text{topol\_defect} = \sum_{j < k} w_{jk} \cdot \text{defect}_{jk}$$
     $$Z_{\text{simpson}} = \frac{1.0}{1.0 + \text{topol\_defect}}$$
   - **Coupling & Invariant Outputs**:
     $$h_{\text{decay}} = \exp(-\kappa_{\text{hodge}} \cdot E_{\text{hodge}})$$
     $$h_{\text{hodge}} = \text{clip}(h_{\text{decay}} \cdot Z_{\text{simpson}}, 10^{-6}, 1.0)$$
     $$\text{FERI}_{\text{v25}} = \frac{1.0}{1.0 + E_{\text{hodge}} + (1.0 - Z_{\text{simpson}})}$$

3. **Mathematical Proof for F120.2 Noise Leakage Rate**:
   For near-zero noise $|z| \le 0.005$ with $\delta = 0.035$:
   $$\frac{|z|}{\delta} \le \frac{0.005}{0.035} = \frac{1}{7} \approx 0.142857$$
   $$\left(\frac{1}{7}\right)^{64} = 10^{64 \cdot \log_{10}(1/7)} \approx 10^{64 \cdot (-0.845098)} \approx 10^{-54.086}$$
   Since $\tanh(x) \le x$:
   $$|z_{\text{denoised}}| \le |z| \cdot \tanh(10^{-54}) \le 0.005 \cdot 10^{-54} = 5 \times 10^{-57} \ll 10^{-34}$$
   Therefore, noise leakage is guaranteed to be $< 10^{-34}$ under standard float64 precision.

---

## 3. Caveats

1. **Coupler Parameter Sensitivity**:
   Ensure `epsilon_reg = 1e-6` is used when clipping $h_{\text{hodge}}$ so it never returns $0.0$, maintaining numerical stability in division/logarithms.
2. **Dynamic Cross-Module Attribute Registration**:
   Tests import both from `ensemble_scorer` directly AND from `factor_suppression`. Therefore, the Worker MUST both:
   - Export through `__getattr__` and `__all__` in `factor_suppression.py`.
   - Execute dynamic registration via `try: from . import factor_suppression as _fs_module; setattr(...)` in `ensemble_scorer.py`.
3. **Sign-Preserving Rank Warping in `combine_predictions`**:
   The multiplier $g_{\text{v25}}(r)$ applies only when $z_{\text{denoised}} \ge 0.0$; when $z_{\text{denoised}} < 0.0$, the standard downward damping $1.35 - 1.00 \cdot r$ MUST be preserved.
4. **Scope Boundaries**:
   This survey strictly covers R1 (Alpha Signal Innovations). Risk allocation (R2: Lurie Non-Abelian Hodge Barycenter $\mu_{\text{hodge}} = [2.20, 1.70, 1.65, 2.75]$ and 21st-cumulant EVaR $21! = 51,090,942,171,709,440,000, \xi = 0.85$), OMS execution (R3: KNK Quintom $w_{\text{quintom}} = -2$), and benchmark engine (R4) belong to other roles.

---

## 4. Conclusion & Concrete Worker Implementation Guide

### 4.1 Target File 1: `trading_system/src/ai/ensemble_scorer.py`

#### Code Snippet A: Add Phase 25 Top-Level Definitions (Lines 28–32)
Insert right before or after the Phase 24 block (around line 28):

```python
# =========================================================================
# PHASE 25 (R1) QUANTITATIVE ALPHA SIGNAL ENHANCEMENTS (v32 Production Master)
# =========================================================================

def apply_hexatetrahedral_hyperbolic_deadband(
    scores_centered: Union[pd.Series, np.ndarray, float],
    delta_noise: float = 0.035,
    delta_neg: Optional[float] = None,
    alpha_pos: float = 64.0,
    alpha_neg: Optional[float] = None,
    regime: Optional[Union[str, int]] = None
) -> Union[pd.Series, np.ndarray, float]:
    """
    Phase 25 (R1, Feature F120.2): Asymmetric Hexatetrahedral (64th-Order) Hyperbolic Noise Deadband:
        z_denoised = z * tanh((|z| / delta_eff(z))^64)
    With hexatetrahedral exponent (alpha = 64.0) and delta_noise = 0.035, suppresses near-zero
    noise (|z| <= 0.005) reducing noise leakage down to < 10^-34 (< 10^-56), while transmitting 100.000%
    of high conviction signals (|z| >= 0.150) with strict rank monotonicity (Spearman rho == 1.0000).
    """
    is_scalar = np.isscalar(scores_centered)
    if is_scalar:
        arr_in = np.array([scores_centered], dtype=np.float64)
    else:
        arr_in = scores_centered

    res = apply_quintic_hyperbolic_deadband(
        scores_centered=arr_in,
        delta_noise=delta_noise,
        delta_neg=delta_neg,
        alpha_pos=alpha_pos,
        alpha_neg=alpha_neg,
        regime=regime
    )
    if is_scalar:
        return float(res[0])
    return res


# Register into factor_suppression module dynamically
try:
    from . import factor_suppression as _fs_module
    if not hasattr(_fs_module, 'apply_hexatetrahedral_hyperbolic_deadband'):
        setattr(_fs_module, 'apply_hexatetrahedral_hyperbolic_deadband', apply_hexatetrahedral_hyperbolic_deadband)
except Exception:
    pass


def compute_phase25_hyperconvex_rank_modulation(
    ranks: Union[pd.Series, np.ndarray, float],
    gamma_top: float = 1.0,
    z_denoised: Optional[Union[pd.Series, np.ndarray, float]] = None
) -> Union[pd.Series, np.ndarray, float]:
    """
    Phase 25 (R1, Feature F120.1): 20th-Order Hyper-Convex Rank Modulation:
        g_v25(r) = 0.50 + 1.14 * r * exp(gamma_top * r^20) (for z_denoised >= 0)
        g_neg(r) = 1.35 - 1.00 * r (for z_denoised < 0)
    Concentrates conviction into top 0.00000000001% alpha names while remaining flat
    across the bottom 70% of distribution.
    """
    is_scalar = np.isscalar(ranks)
    r = np.asarray(ranks, dtype=np.float64)
    r_clipped = np.clip(r, 0.0, 1.0)
    pos_mult = 0.50 + 1.14 * r_clipped * np.exp(float(gamma_top) * np.power(r_clipped, 20.0))
    if z_denoised is not None:
        z = np.asarray(z_denoised, dtype=np.float64)
        mult = np.where(z >= 0.0, pos_mult, 1.35 - 1.00 * r_clipped)
    else:
        mult = pos_mult

    if is_scalar:
        return float(mult.item() if hasattr(mult, 'item') else mult)
    if isinstance(ranks, pd.Series):
        return pd.Series(mult, index=ranks.index)
    return mult

compute_phase25_rank_warping = compute_phase25_hyperconvex_rank_modulation


class NonAbelianHodgeCoupler:
    r"""
    Phase 25 (R1, Feature F119): Non-Abelian Hodge Theory & Deligne-Simpson Spectral Moduli Factor Disentanglement Engine.
    Models the 5 canonical economic pillars via Hitchin equations \bar{\partial}_E \Phi = 0, F_A + [\Phi, \Phi^*] = 0,
    harmonic bundle obstruction complex E_hodge, Deligne-Simpson spectral moduli invariant Z_simpson,
    coupling factor h_hodge, and FERI_v25.
    """

    def __init__(
        self,
        theta_0: float = 0.34,
        kappa_hodge: float = 3.40,
        lambda_hodge: float = 0.24,
        lambda_simpson: float = 0.11,
        lambda_hitchin: float = 0.075,
        lambda_harmonic: float = 0.050,
        lambda_spectral: float = 0.030,
        epsilon_reg: float = 1e-6,
        **kwargs
    ):
        self.theta_0 = float(kwargs.get('theta_0', theta_0))
        self.kappa_hodge = float(kwargs.get('kappa_hodge', kappa_hodge))
        self.lambda_hodge = float(kwargs.get('lambda_hodge', lambda_hodge))
        self.lambda_simpson = float(kwargs.get('lambda_simpson', lambda_simpson))
        self.lambda_hitchin = float(kwargs.get('lambda_hitchin', lambda_hitchin))
        self.lambda_harmonic = float(kwargs.get('lambda_harmonic', lambda_harmonic))
        self.lambda_spectral = float(kwargs.get('lambda_spectral', lambda_spectral))
        self.epsilon_reg = float(kwargs.get('epsilon_reg', epsilon_reg))

    def __call__(self, pillar_scores: Any) -> Dict[str, Any]:
        return self.evaluate(pillar_scores)

    def couple(self, pillar_scores: Any) -> Dict[str, Any]:
        return self.evaluate(pillar_scores)

    @classmethod
    def compute(
        cls,
        pillar_scores: Union[pd.DataFrame, Dict[str, Any], np.ndarray],
        theta_0: float = 0.34,
        kappa_hodge: float = 3.40,
        lambda_hodge: float = 0.24,
        lambda_simpson: float = 0.11,
        lambda_hitchin: float = 0.075,
        lambda_harmonic: float = 0.050,
        lambda_spectral: float = 0.030,
        epsilon_reg: float = 1e-6,
        **kwargs
    ) -> Dict[str, Any]:
        coupler = cls(
            theta_0=theta_0,
            kappa_hodge=kappa_hodge,
            lambda_hodge=lambda_hodge,
            lambda_simpson=lambda_simpson,
            lambda_hitchin=lambda_hitchin,
            lambda_harmonic=lambda_harmonic,
            lambda_spectral=lambda_spectral,
            epsilon_reg=epsilon_reg,
            **kwargs
        )
        return coupler.evaluate(pillar_scores)

    def evaluate(
        self,
        pillar_scores: Union[pd.DataFrame, Dict[str, Any], np.ndarray]
    ) -> Dict[str, Any]:
        index = None
        is_single_1d = False

        if isinstance(pillar_scores, pd.DataFrame):
            cols = ['val', 'mom', 'flow', 'cat', 'net']
            if all(c in pillar_scores.columns for c in cols):
                p_mat = pillar_scores[cols].values.astype(np.float64)
            elif pillar_scores.shape[1] == 5:
                p_mat = pillar_scores.values.astype(np.float64)
            elif pillar_scores.shape[0] == 5:
                p_mat = pillar_scores.values.T.astype(np.float64)
            else:
                p_mat = pillar_scores.iloc[:, :5].values.astype(np.float64)
            index = pillar_scores.index
        elif isinstance(pillar_scores, dict):
            cols = ['val', 'mom', 'flow', 'cat', 'net']
            if all(c in pillar_scores for c in cols):
                arr_list = [np.asarray(pillar_scores[c], dtype=np.float64) for c in cols]
                p_mat = np.column_stack(arr_list)
            else:
                vals = list(pillar_scores.values())[:5]
                p_mat = np.column_stack([np.asarray(v, dtype=np.float64) for v in vals])
            val_item = pillar_scores.get('val', None)
            if isinstance(val_item, pd.Series) or (hasattr(val_item, 'index') and not callable(getattr(val_item, 'index'))):
                index = getattr(val_item, 'index')
        else:
            p_mat = np.asarray(pillar_scores, dtype=np.float64)
            if p_mat.ndim == 1:
                if len(p_mat) == 5:
                    p_mat = p_mat.reshape(1, 5)
                    is_single_1d = True
                else:
                    raise ValueError(f"1D pillar vector must have length 5, got {len(p_mat)}")
            elif p_mat.ndim == 2:
                if p_mat.shape[1] != 5 and p_mat.shape[0] == 5:
                    p_mat = p_mat.T

        if np.any(np.isnan(p_mat)):
            p_mat = np.nan_to_num(p_mat, nan=0.0)

        N, D = p_mat.shape
        if D != 5:
            raise ValueError(f"Non-Abelian Hodge factor disentanglement requires 5 canonical pillars, got {D}")

        omega = np.zeros((5, 5), dtype=np.float64)
        for j in range(5):
            for k in range(5):
                if j != k:
                    omega[j, k] = self.theta_0 * (j - k) / (1.0 + abs(j - k))

        e_hodge = np.zeros(N, dtype=np.float64)
        z_simpson = np.zeros(N, dtype=np.float64)

        for n in range(N):
            pn = p_mat[n]
            obs_energy = 0.0
            topol_defect = 0.0
            for j in range(5):
                for k in range(j + 1, 5):
                    w = abs(omega[j, k])
                    diff = pn[j] - pn[k]
                    # 20th-degree Hitchin harmonic bundle obstruction action
                    a_hodge = (0.5 * (diff ** 2)
                               + self.lambda_hodge * (1.0 - np.cos(np.pi * diff))
                               + 0.25 * self.lambda_simpson * (diff ** 4)
                               + (1.0 / 6.0) * self.lambda_hitchin * (diff ** 6)
                               + (1.0 / 8.0) * self.lambda_harmonic * (diff ** 8)
                               + (1.0 / 10.0) * self.lambda_spectral * (diff ** 10)
                               + (1.0 / 12.0) * (self.lambda_spectral * 0.6) * (diff ** 12)
                               + (1.0 / 16.0) * (self.lambda_spectral * 0.3) * (diff ** 16)
                               + (1.0 / 20.0) * (self.lambda_spectral * 0.15) * (diff ** 20))
                    obs_energy += w * a_hodge
                    # Deligne-Simpson spectral moduli cycle defect
                    defect = abs((pn[j]**2 - pn[k]**2)
                                 + self.lambda_simpson * (pn[j]**3 - pn[k]**3)
                                 + self.lambda_hitchin * (pn[j]**4 - pn[k]**4)
                                 + self.lambda_harmonic * (pn[j]**5 - pn[k]**5)
                                 + self.lambda_spectral * (pn[j]**6 - pn[k]**6)
                                 + (self.lambda_spectral * 0.6) * (pn[j]**7 - pn[k]**7)
                                 + (self.lambda_spectral * 0.3) * (pn[j]**8 - pn[k]**8)
                                 + (self.lambda_spectral * 0.15) * (pn[j]**9 - pn[k]**9))
                    topol_defect += w * defect
            e_hodge[n] = obs_energy
            z_simpson[n] = 1.0 / (1.0 + topol_defect)

        h_decay = np.exp(-self.kappa_hodge * e_hodge)
        h_hodge = np.clip(h_decay * z_simpson, self.epsilon_reg, 1.0)
        feri_v25 = 1.0 / (1.0 + e_hodge + (1.0 - z_simpson))

        h_out = float(h_hodge[0]) if is_single_1d else (pd.Series(h_hodge, index=index) if index is not None else h_hodge)
        z_out = float(z_simpson[0]) if is_single_1d else (pd.Series(z_simpson, index=index) if index is not None else z_simpson)
        e_out = float(e_hodge[0]) if is_single_1d else (pd.Series(e_hodge, index=index) if index is not None else e_hodge)
        d_out = float(h_decay[0]) if is_single_1d else (pd.Series(h_decay, index=index) if index is not None else h_decay)
        f_out = float(feri_v25[0]) if is_single_1d else (pd.Series(feri_v25, index=index) if index is not None else feri_v25)

        res_dict = {
            "h_hodge": h_out,
            "z_simpson": z_out,
            "e_hodge": e_out,
            "h_decay": d_out,
            "FERI_v25": f_out,
            "feri_v25": f_out,
            "Z_simpson": z_out,
            "E_hodge": e_out,
            "H_hodge": h_out,
            "h_deligne_simpson": h_out,
            "z_deligne_simpson": z_out,
            "e_deligne_simpson": e_out,
            "h_hitchin": h_out,
            "z_hitchin": z_out,
            "e_hitchin": e_out,
            "h_harmonic_bundle": h_out,
            "z_harmonic_bundle": z_out,
            "e_harmonic_bundle": e_out,
            "h_spectral_moduli": h_out,
            "z_spectral_moduli": z_out,
            "e_spectral_moduli": e_out,
            "h_non_abelian_hodge": h_out,
            "z_non_abelian_hodge": z_out,
            "e_non_abelian_hodge": e_out,
        }
        return res_dict

DeligneSimpsonSpectralModuliCoupler = NonAbelianHodgeCoupler
HitchinHarmonicBundleCoupler = NonAbelianHodgeCoupler
NonAbelianHodgeTheoryCoupler = NonAbelianHodgeCoupler
SimpsonSpectralModuliCoupler = NonAbelianHodgeCoupler
HitchinEquationsCoupler = NonAbelianHodgeCoupler

# Dynamically register Phase 25 into factor_suppression module
try:
    from . import factor_suppression as _fs_module
    setattr(_fs_module, 'NonAbelianHodgeCoupler', NonAbelianHodgeCoupler)
    setattr(_fs_module, 'DeligneSimpsonSpectralModuliCoupler', DeligneSimpsonSpectralModuliCoupler)
    setattr(_fs_module, 'HitchinHarmonicBundleCoupler', HitchinHarmonicBundleCoupler)
    setattr(_fs_module, 'NonAbelianHodgeTheoryCoupler', NonAbelianHodgeTheoryCoupler)
    setattr(_fs_module, 'SimpsonSpectralModuliCoupler', SimpsonSpectralModuliCoupler)
    setattr(_fs_module, 'HitchinEquationsCoupler', HitchinEquationsCoupler)
    setattr(_fs_module, 'compute_non_abelian_hodge_coupling', NonAbelianHodgeCoupler.compute)
    setattr(_fs_module, 'compute_deligne_simpson_spectral_moduli_coupling', NonAbelianHodgeCoupler.compute)
    setattr(_fs_module, 'compute_hitchin_harmonic_bundle_coupling', NonAbelianHodgeCoupler.compute)
    setattr(_fs_module, 'compute_non_abelian_hodge_theory_coupling', NonAbelianHodgeCoupler.compute)
    setattr(_fs_module, 'compute_simpson_spectral_moduli_coupling', NonAbelianHodgeCoupler.compute)
    setattr(_fs_module, 'compute_hitchin_equations_coupling', NonAbelianHodgeCoupler.compute)
    setattr(_fs_module, 'compute_phase25_hyperconvex_rank_modulation', compute_phase25_hyperconvex_rank_modulation)
    setattr(_fs_module, 'compute_phase25_rank_warping', compute_phase25_rank_warping)
    setattr(_fs_module, 'apply_hexatetrahedral_hyperbolic_deadband', apply_hexatetrahedral_hyperbolic_deadband)
except Exception:
    pass
```

#### Code Snippet B: Branch in `combine_predictions` (Around Line 6999)
```python
        if len(ens_scores) >= 5:
            ranks = pd.Series(ens_scores).rank(pct=True).values
            reg_str = str(regime).upper()
            if int(version) >= 25:
                gamma_top = self.get_regime_adaptive_gamma_top(regime, version=version)
                # Phase 25 (R1, Feature F120.1): 20th-Order Hyper-Convex Rank Modulation across regimes
                # g_v25(r) = 0.50 + 1.14 * r * exp(gamma_top * r^20) for positive excess conviction
                mult = np.where(
                    z_denoised >= 0.0,
                    0.50 + 1.14 * ranks * np.exp(gamma_top * (ranks ** 20)),
                    1.35 - 1.00 * ranks
                )
            elif int(version) >= 24:
                ...
```

#### Code Snippet C: Branch in `compute_quint_pillar_tensor_synergy` (Around Line 8533)
```python
        if version >= 25:
            # Phase 25 (R1, Feature F119): Non-Abelian Hodge Theory & Deligne-Simpson Spectral Moduli Disentanglement
            p_vals = np.array([p_val.values, p_mom.values, p_flow.values, p_cat.values, p_net.values])  # shape (5, N)
            p_sum = np.sum(p_vals, axis=0, keepdims=True)
            p_norm = (p_vals + 1e-6) / (p_sum + 5e-6)

            bc = np.sum(np.sqrt(0.20 * p_norm), axis=0)
            bc_clipped = np.clip(bc, 0.0, 1.0)
            d_riemann = np.arccos(bc_clipped)
            h_riemann = np.exp(-2.50 * np.square(d_riemann))

            q_disp = np.array([p_val.values, p_net.values])
            p_flow_mom = np.array([p_mom.values, p_flow.values, p_cat.values])
            v_potential = 0.5 * (1.5 * np.square(q_disp[0]) + 1.2 * np.square(q_disp[1]))
            t_kinetic = 0.5 * (1.2 * np.square(p_flow_mom[0]) + 1.0 * np.square(p_flow_mom[1]) + 0.8 * np.square(p_flow_mom[2]))
            hamiltonian = t_kinetic + v_potential
            e_symplectic = np.exp(-np.square(hamiltonian - 0.45) / (2.0 * (0.25 ** 2)))

            dp = np.diff(p_vals, axis=0)
            sobolev_norm = np.sum(np.square(dp), axis=0)
            m_stability = np.exp(-1.80 * sobolev_norm)

            mfg_res = cls.compute_mckean_vlasov_mean_field_coupling(p_vals.T)
            m_mfg = float(np.mean(mfg_res["decoupling_alpha_boost"]))

            gauge_res = cls.compute_non_abelian_gauge_curvature(p_vals.T)
            h_gauge = np.atleast_1d(gauge_res["h_gauge"]).astype(np.float64)

            cy_res = cls.compute_calabi_yau_holonomy_coupling(p_vals.T)
            h_cy = np.atleast_1d(cy_res["h_cy"]).astype(np.float64)

            holo_res = cls.compute_holographic_adscft_coupling(p_vals.T)
            h_holo = np.atleast_1d(holo_res["h_holo"]).astype(np.float64)
            z_topo = np.atleast_1d(holo_res["z_topo"]).astype(np.float64)

            ncqft_res = cls.compute_ncqft_moyal_weyl_coupling(p_vals.T)
            h_ncqft = np.atleast_1d(ncqft_res["h_ncqft"]).astype(np.float64)
            z_index = np.atleast_1d(ncqft_res["z_index"]).astype(np.float64)

            sheaf_res = cls.compute_quantum_topos_sheaf_coupling(p_vals.T)
            h_sheaf = np.atleast_1d(sheaf_res["h_sheaf"]).astype(np.float64)
            z_sheaf = np.atleast_1d(sheaf_res["z_sheaf"]).astype(np.float64)

            hms_res = cls.compute_homological_mirror_symmetry_coupling(p_vals.T)
            h_hms = np.atleast_1d(hms_res["h_hms"]).astype(np.float64)
            z_hms = np.atleast_1d(hms_res["z_hms"]).astype(np.float64)

            dag_res = cls.compute_derived_algebraic_geometry_coupling(p_vals.T)
            h_dag = np.atleast_1d(dag_res["h_derived"]).astype(np.float64)
            z_dag = np.atleast_1d(dag_res["z_derived"]).astype(np.float64)

            lurie_res = cls.compute_lurie_infinity_topos_coupling(p_vals.T)
            h_lurie = np.atleast_1d(lurie_res["h_lurie"]).astype(np.float64)
            z_lurie = np.atleast_1d(lurie_res["z_lurie"]).astype(np.float64)

            prism_res = cls.compute_perfectoid_prismatic_coupling(p_vals.T)
            h_prism = np.atleast_1d(prism_res["h_prism"]).astype(np.float64)
            z_prism = np.atleast_1d(prism_res["z_prism"]).astype(np.float64)

            motivic_res = cls.compute_derived_motivic_homotopy_type_theory_coupling(p_vals.T)
            h_motivic = np.atleast_1d(motivic_res["h_motivic"]).astype(np.float64)
            z_motivic = np.atleast_1d(motivic_res["z_motivic"]).astype(np.float64)

            condensed_res = cls.compute_condensed_analytic_geometry_coupling(p_vals.T)
            h_condensed = np.atleast_1d(condensed_res["h_condensed"]).astype(np.float64)
            z_condensed = np.atleast_1d(condensed_res["z_condensed"]).astype(np.float64)

            langlands_res = cls.compute_toposic_geometric_langlands_coupling(p_vals.T)
            h_langlands = np.atleast_1d(langlands_res["h_langlands"]).astype(np.float64)
            z_satake = np.atleast_1d(langlands_res["z_satake"]).astype(np.float64)

            arith_res = cls.compute_derived_arithmetic_topology_coupling(p_vals.T)
            h_arith = np.atleast_1d(arith_res["h_arithmetic"]).astype(np.float64)
            z_spectral = np.atleast_1d(arith_res["z_spectral"]).astype(np.float64)

            # Phase 25 (R1, Feature F119): Non-Abelian Hodge Coupler
            hodge_res = cls.compute_non_abelian_hodge_coupling(p_vals.T)
            h_hodge = np.atleast_1d(hodge_res["h_hodge"]).astype(np.float64)
            z_simpson = np.atleast_1d(hodge_res["z_simpson"]).astype(np.float64)

            p_mean = np.mean(p_vals, axis=0)
            harmony_factor = pd.Series(
                1.0 + (0.10 * h_riemann + 0.06 * e_symplectic + 0.05 * m_stability + 0.05 * (m_mfg - 1.0)
                       + 0.10 * h_gauge + 0.12 * h_cy + 0.16 * h_holo * z_topo + 0.20 * h_ncqft * z_index
                       + 0.26 * h_sheaf * z_sheaf + 0.35 * h_hms * z_hms + 0.45 * h_dag * z_dag
                       + 0.55 * h_lurie * z_lurie + 0.65 * h_prism * z_prism
                       + 0.75 * h_motivic * z_motivic
                       + 0.85 * h_condensed * z_condensed
                       + 0.95 * h_langlands * z_satake
                       + 1.05 * h_arith * z_spectral
                       + 1.15 * h_hodge * z_simpson) * (p_mean > 0.35).astype(float),
                index=scores_df.index
            )
            total_confluence = raw_confluence * harmony_factor
        elif version >= 24:
            ...
```

#### Code Snippet D: Class Attributes & Methods on `EnsembleScoringEngine` (Around Line 9702)
```python
    apply_hexatetrahedral_hyperbolic_deadband = staticmethod(apply_hexatetrahedral_hyperbolic_deadband)
    compute_phase25_hyperconvex_rank_modulation = staticmethod(compute_phase25_hyperconvex_rank_modulation)
    compute_phase25_rank_warping = staticmethod(compute_phase25_hyperconvex_rank_modulation)
    NonAbelianHodgeCoupler = NonAbelianHodgeCoupler
    DeligneSimpsonSpectralModuliCoupler = NonAbelianHodgeCoupler
    HitchinHarmonicBundleCoupler = NonAbelianHodgeCoupler
    NonAbelianHodgeTheoryCoupler = NonAbelianHodgeCoupler
    SimpsonSpectralModuliCoupler = NonAbelianHodgeCoupler
    HitchinEquationsCoupler = NonAbelianHodgeCoupler

    @classmethod
    def compute_non_abelian_hodge_coupling(
        cls,
        pillar_scores: Union[pd.DataFrame, Dict[str, Any], np.ndarray],
        theta_0: float = 0.34,
        kappa_hodge: float = 3.40,
        lambda_hodge: float = 0.24,
        lambda_simpson: float = 0.11,
        lambda_hitchin: float = 0.075,
        lambda_harmonic: float = 0.050,
        lambda_spectral: float = 0.030,
        epsilon_reg: float = 1e-6,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Phase 25 (R1, Feature F119): Non-Abelian Hodge Theory & Deligne-Simpson Spectral Moduli Factor Disentanglement Engine.
        """
        return NonAbelianHodgeCoupler.compute(
            pillar_scores=pillar_scores,
            theta_0=theta_0,
            kappa_hodge=kappa_hodge,
            lambda_hodge=lambda_hodge,
            lambda_simpson=lambda_simpson,
            lambda_hitchin=lambda_hitchin,
            lambda_harmonic=lambda_harmonic,
            lambda_spectral=lambda_spectral,
            epsilon_reg=epsilon_reg,
            **kwargs
        )

    compute_deligne_simpson_spectral_moduli_coupling = compute_non_abelian_hodge_coupling
    compute_hitchin_harmonic_bundle_coupling = compute_non_abelian_hodge_coupling
    compute_non_abelian_hodge_theory_coupling = compute_non_abelian_hodge_coupling
    compute_simpson_spectral_moduli_coupling = compute_non_abelian_hodge_coupling
    compute_hitchin_equations_coupling = compute_non_abelian_hodge_coupling
```

#### Code Snippet E: Branch in `get_regime_adaptive_gamma_top` (Around Line 10499)
```python
        if int(version) >= 25:
            if 'CRISIS' in reg_str:
                return 1.55
            elif 'BEAR_HIGH_VOL' in reg_str:
                return 0.80
            elif 'BEAR_LOW_VOL' in reg_str or reg_str == '0':
                return 1.90
            elif 'BEAR' in reg_str:
                return 1.90
            elif 'SIDEWAYS_HIGH_VOL' in reg_str:
                return 1.50
            elif 'SIDEWAYS_LOW_VOL' in reg_str or reg_str == '1':
                return 2.20
            elif 'SIDEWAYS' in reg_str:
                return 2.20
            elif 'BULL_HIGH_VOL' in reg_str:
                return 2.40
            elif 'BULL_LOW_VOL' in reg_str or reg_str == '2':
                return 2.60
            elif 'BULL' in reg_str:
                return 2.60
            else:
                return 2.10

        if int(version) >= 24:
            ...
```

#### Code Snippet F: Branch in `apply_smooth_noise_deadband` (Around Line 10889)
```python
        if int(version) >= 25:
            eff_alpha = 64.0 if alpha_pos in (3.0, 5.0, 7.0, 9.0, 10.0, 12.0, 14.0, 16.0, 20.0, 24.0, 28.0, 32.0, 36.0, 40.0, 44.0, 48.0, 52.0, 56.0, 60.0) else alpha_pos
            return apply_hexatetrahedral_hyperbolic_deadband(
                scores_centered=scores_centered,
                delta_noise=delta_noise,
                delta_neg=delta_neg,
                alpha_pos=eff_alpha,
                alpha_neg=alpha_neg,
                regime=regime
            )
        elif int(version) >= 24:
            ...
```

---

### 4.2 Target File 2: `trading_system/src/ai/factor_suppression.py`

#### Code Snippet G: Add Deadband, Modulation & Regime Functions
Add around line 450:
```python
def apply_hexatetrahedral_hyperbolic_deadband(
    scores_centered: Union[pd.Series, np.ndarray, float],
    delta_noise: float = 0.035,
    delta_neg: Optional[float] = None,
    alpha_pos: float = 64.0,
    alpha_neg: Optional[float] = None,
    regime: Optional[Union[str, int]] = None
) -> Union[pd.Series, np.ndarray, float]:
    """
    Phase 25 (R1, Feature F120.2): Asymmetric Hexatetrahedral (64th-Order) Hyperbolic Noise Deadband:
        z_denoised = z * tanh((|z| / delta_eff(z))^64)
    With hexatetrahedral exponent (alpha = 64.0) and delta_noise = 0.035, suppresses near-zero
    noise (|z| <= 0.005) reducing noise leakage down to < 10^-34 (< 10^-56), while transmitting 100.000%
    of high conviction signals (|z| >= 0.150) with strict rank monotonicity (Spearman rho == 1.0000).
    """
    is_scalar = np.isscalar(scores_centered)
    if is_scalar:
        arr_in = np.array([scores_centered], dtype=np.float64)
    else:
        arr_in = scores_centered

    res = apply_quintic_hyperbolic_deadband(
        scores_centered=arr_in,
        delta_noise=delta_noise,
        delta_neg=delta_neg,
        alpha_pos=alpha_pos,
        alpha_neg=alpha_neg,
        regime=regime
    )
    if is_scalar:
        return float(res[0])
    return res


def compute_phase25_hyperconvex_rank_modulation(
    ranks: Union[pd.Series, np.ndarray, float],
    gamma_top: float = 1.0,
    z_denoised: Optional[Union[pd.Series, np.ndarray, float]] = None
) -> Union[pd.Series, np.ndarray, float]:
    """
    Phase 25 (R1, Feature F120.1): 20th-Order Hyper-Convex Rank Modulation:
        g_v25(r) = 0.50 + 1.14 * r * exp(gamma_top * r^20) (for z_denoised >= 0)
        g_neg(r) = 1.35 - 1.00 * r (for z_denoised < 0)
    Concentrates conviction into top 0.00000000001% alpha names while remaining flat
    across the bottom 70% of distribution.
    """
    is_scalar = np.isscalar(ranks)
    r = np.asarray(ranks, dtype=np.float64)
    r_clipped = np.clip(r, 0.0, 1.0)
    pos_mult = 0.50 + 1.14 * r_clipped * np.exp(float(gamma_top) * np.power(r_clipped, 20.0))
    if z_denoised is not None:
        z = np.asarray(z_denoised, dtype=np.float64)
        mult = np.where(z >= 0.0, pos_mult, 1.35 - 1.00 * r_clipped)
    else:
        mult = pos_mult

    if is_scalar:
        return float(mult.item() if hasattr(mult, 'item') else mult)
    if isinstance(ranks, pd.Series):
        return pd.Series(mult, index=ranks.index)
    return mult

compute_phase25_rank_warping = compute_phase25_hyperconvex_rank_modulation


REGIME_GAMMA_TOP_V25 = {
    'BULL_LOW_VOL': 2.60,
    'BULL_HIGH_VOL': 2.40,
    'SIDEWAYS': 2.20,
    'SIDEWAYS_LOW_VOL': 2.20,
    'SIDEWAYS_HIGH_VOL': 1.50,
    'BEAR': 1.90,
    'BEAR_LOW_VOL': 1.90,
    'BEAR_HIGH_VOL': 0.80,
    'CRISIS': 1.55,
    '2': 2.60,
    '1': 2.20,
    '0': 1.90,
}


def get_regime_adaptive_gamma_top_v25(regime: Union[int, str] = 'BULL_LOW_VOL') -> float:
    """
    Phase 25 (R1, Feature F120.1): Regime-adaptive gamma_top <= 2.60
    (Bull Low Vol: 2.60, Bull High Vol: 2.40, Sideways: 2.20, Bear: 1.90, Crisis: 1.55).
    """
    reg_str = str(regime).upper()
    if 'CRISIS' in reg_str:
        return 1.55
    elif 'BEAR_HIGH_VOL' in reg_str:
        return 0.80
    elif 'BEAR_LOW_VOL' in reg_str or reg_str == '0':
        return 1.90
    elif 'BEAR' in reg_str:
        return 1.90
    elif 'SIDEWAYS_HIGH_VOL' in reg_str:
        return 1.50
    elif 'SIDEWAYS_LOW_VOL' in reg_str or reg_str == '1':
        return 2.20
    elif 'SIDEWAYS' in reg_str:
        return 2.20
    elif 'BULL_HIGH_VOL' in reg_str:
        return 2.40
    elif 'BULL_LOW_VOL' in reg_str or reg_str == '2':
        return 2.60
    elif 'BULL' in reg_str:
        return 2.60
    return 2.10
```

#### Code Snippet H: Branch in `apply_smooth_deadband_attenuation` (Around Line 687)
```python
    version = int(kwargs.get('version', version))
    if version >= 25:
        eff_alpha = 64.0 if alpha_pos in (3.0, 5.0, 7.0, 9.0, 10.0, 12.0, 14.0, 16.0, 20.0, 24.0, 28.0, 32.0, 36.0, 40.0, 44.0, 48.0, 52.0, 56.0, 60.0) else alpha_pos
        return apply_hexatetrahedral_hyperbolic_deadband(
            scores_centered=scores_centered,
            delta_noise=delta_noise,
            delta_neg=delta_neg,
            alpha_pos=eff_alpha,
            alpha_neg=alpha_neg,
            regime=regime
        )
    elif version >= 24:
        ...
```

#### Code Snippet I: Update `__all__` and `__getattr__` (Around Line 1300–1370)
In `__all__`:
```python
__all__ = [
    'apply_hexatetrahedral_hyperbolic_deadband',
    'compute_phase25_hyperconvex_rank_modulation',
    'compute_phase25_rank_warping',
    'REGIME_GAMMA_TOP_V25',
    'get_regime_adaptive_gamma_top_v25',
    'NonAbelianHodgeCoupler',
    'DeligneSimpsonSpectralModuliCoupler',
    'HitchinHarmonicBundleCoupler',
    'NonAbelianHodgeTheoryCoupler',
    'SimpsonSpectralModuliCoupler',
    'HitchinEquationsCoupler',
    'compute_non_abelian_hodge_coupling',
    'compute_deligne_simpson_spectral_moduli_coupling',
    'compute_hitchin_harmonic_bundle_coupling',
    'compute_non_abelian_hodge_theory_coupling',
    'compute_simpson_spectral_moduli_coupling',
    'compute_hitchin_equations_coupling',
    # ... previous exports ...
]
```

In `__getattr__`:
```python
def __getattr__(name: str) -> Any:
    # Phase 25 Non-Abelian Hodge Coupler Exports
    if name in (
        'NonAbelianHodgeCoupler',
        'DeligneSimpsonSpectralModuliCoupler',
        'HitchinHarmonicBundleCoupler',
        'NonAbelianHodgeTheoryCoupler',
        'SimpsonSpectralModuliCoupler',
        'HitchinEquationsCoupler',
    ):
        from .ensemble_scorer import NonAbelianHodgeCoupler as _NAHC
        return _NAHC
    if name in (
        'compute_non_abelian_hodge_coupling',
        'compute_deligne_simpson_spectral_moduli_coupling',
        'compute_hitchin_harmonic_bundle_coupling',
        'compute_non_abelian_hodge_theory_coupling',
        'compute_simpson_spectral_moduli_coupling',
        'compute_hitchin_equations_coupling',
    ):
        from .ensemble_scorer import NonAbelianHodgeCoupler as _NAHC
        return _NAHC.compute
    if name == 'apply_hexatetrahedral_hyperbolic_deadband':
        return apply_hexatetrahedral_hyperbolic_deadband
    if name in ('compute_phase25_hyperconvex_rank_modulation', 'compute_phase25_rank_warping'):
        return compute_phase25_hyperconvex_rank_modulation
    if name in ('REGIME_GAMMA_TOP_V25', 'get_regime_adaptive_gamma_top_v25'):
        return globals()[name]

    # ... Phase 24 and previous getattr logic ...
```

---

### 4.3 Target File 3: `tests/test_phase25_alpha.py` (Test Suite Blueprint)

The Worker should create `tests/test_phase25_alpha.py` with 14 comprehensive tests:
1. `test_hexatetrahedral_hyperbolic_deadband_noise_leakage`: Assert leakage $< 10^{-34}$ for $|z| \le 0.005$ with $\delta = 0.035$, zero at $z = 0$.
2. `test_hexatetrahedral_hyperbolic_deadband_pass_through_and_monotonicity`: Assert 100% transmission for $|z| \ge 0.150$ and Spearman $\rho \ge 0.99999$.
3. `test_hexatetrahedral_deadband_symmetry_and_regimes`: Assert odd symmetry $f(-z) = -f(z)$, heavier suppression in `CRISIS` vs `BULL_LOW_VOL`, cross-module import equality between `ensemble_scorer` and `factor_suppression`.
4. `test_smooth_deadband_attenuation_version25_dispatch`: Assert `version=25` dispatches to $\alpha = 64.0$.
5. `test_non_abelian_hodge_coupler_invariants_bounded`: Assert $E_{\text{hodge}} \ge 0, 0 < Z_{\text{simpson}} \le 1.0, 0 < h_{\text{hodge}} \le 1.0, 0 < \text{FERI}_{\text{v25}} \le 1.0$.
6. `test_non_abelian_hodge_coupler_zero_obstruction_on_coherent_sections`: Coherent sections give $E_{\text{hodge}} = 0, Z_{\text{simpson}} = 1.0, h_{\text{hodge}} = 1.0, \text{FERI}_{\text{v25}} = 1.0$.
7. `test_non_abelian_hodge_coupler_adversarial_conflict`: Severe discordance gives $E_{\text{hodge}} > 1.0, Z_{\text{simpson}} \le 1.0, h_{\text{hodge}} < 0.05, \text{FERI}_{\text{v25}} < 0.50$.
8. `test_non_abelian_hodge_coupler_input_formats`: Validates DataFrame, dict, 2D array, 1D array of length 5, classmethod `compute_non_abelian_hodge_coupling`, all 5 aliases, and cross-module re-exports in `factor_suppression`.
9. `test_quint_pillar_tensor_synergy_version25`: Validates `compute_quint_pillar_tensor_synergy` incorporates $+ 1.15 \cdot h_{\text{hodge}} \cdot z_{\text{simpson}}$ and produces $\ge$ synergy than v24 on coherent pillars.
10. `test_20th_order_rank_modulation_percentiles`: Baseline $r=0 \implies 0.50$, flat across bottom $r=0.50 \implies < 1.08$, right-tail concentration $r=1.0 \implies > 14.50$, negative branch $z < 0 \implies 1.35 - 1.00 \cdot r$.
11. `test_20th_order_rank_modulation_strict_convexity`: Monotonic increasing ($d1 > 0$) and strict convexity ($d2 \ge -10^{-7}$ for $r \ge 0.30$).
12. `test_regime_adaptive_gamma_top_version25`: `BULL_LOW_VOL: 2.60`, `BULL_HIGH_VOL: 2.40`, `SIDEWAYS: 2.20`, `BEAR: 1.90`, `CRISIS: 1.55`.
13. `test_combine_predictions_version25_full_pipeline`: Non-empty DataFrame, `ensemble_score` $\in [0, 1]$, top conviction in v25 $\ge$ top conviction in v24.
14. `test_backward_compatibility_v13_through_v25`: Versions 13 through 25 run cleanly without exceptions or shape regressions.

---

## 5. Verification Method

To verify the Worker's implementation independently:

1. **Unit & Integration Test Command**:
   ```bash
   .venv\Scripts\pytest tests/test_phase25_alpha.py -v
   ```
   *Expected outcome*: 14 passed in < 20s.

2. **Regression Check on Existing Alpha Tests**:
   ```bash
   .venv\Scripts\pytest tests/test_phase24_alpha.py tests/test_phase23_alpha.py -v
   ```
   *Expected outcome*: 100% passed with zero regressions.

3. **Invariants Verification**:
   - For $|z| \le 0.005$, `apply_hexatetrahedral_hyperbolic_deadband(z, delta_noise=0.035, alpha_pos=64.0) < 1e-34`.
   - On coherent sections, `NonAbelianHodgeCoupler.compute(...)["e_hodge"] == 0.0` and `["z_simpson"] == 1.0`.
   - On extreme conviction, `compute_phase25_hyperconvex_rank_modulation(1.0, gamma_top=2.60) > 14.50`.
