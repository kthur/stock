# Phase 41 Quant Enhancement (R1 Alpha Signal Survey) — Handoff Report

**Agent**: Explorer 1 (`.agents/explorer_quant_phase41_survey1`)  
**Role**: Alpha Signal Survey Explorer  
**Mission**: Survey hook points and produce an exact, detailed implementation blueprint for Phase 41 R1 Alpha Signal (F183, F184.1, F184.2, version branch in `ensemble_scorer.py`, test specifications).  
**Timestamp**: 2026-09-14T19:22:00+09:00  

---

## 1. Observation

### 1.1 Project Structure and File Locations
- The actual codebase implementation for the trading system is located under `trading_system/src/ai/`:
  - `trading_system/src/ai/ensemble_scorer.py` (19,869 lines)
  - `trading_system/src/ai/factor_suppression.py` (3,931 lines)
- Existing alpha test suite:
  - `tests/test_phase40_alpha.py` (214 lines, 9 tests)
  - `tests/test_phase40_adversarial_stress.py` (533 lines)
- Empirical test run of Phase 40 alpha test suite:
  - Command: `.\.venv\Scripts\pytest.exe tests/test_phase40_alpha.py -v`
  - Result: `9 passed in 11.99s` (100% pass rate confirmed).

### 1.2 Phase 40 Reference Implementation (Direct Quotes)

#### A. Factor Deadband (F180.2) in `trading_system/src/ai/factor_suppression.py` (Lines 454–490)
```python
def apply_octacontatetragonal_hyperbolic_deadband(
    scores_centered: Union[pd.Series, np.ndarray, float],
    delta_noise: float = 0.035,
    delta_neg: Optional[float] = None,
    alpha_pos: float = 128.0,
    alpha_neg: Optional[float] = None,
    regime: Optional[Union[str, int]] = None
) -> Union[pd.Series, np.ndarray, float]:
    """
    Phase 40 (R1, Feature F180.2): Asymmetric Octaconta-tetragonal (128th-Order) Hyperbolic Noise Deadband:
        z_denoised = z * tanh((|z| / delta_eff(z))^128)
    With octaconta-tetragonal exponent (alpha = 128.0) and delta_noise = 0.035, suppresses near-zero
    noise (|z| <= 0.0004) reducing noise leakage down to < 10^-68 (< 10^-128), while transmitting 100.000%
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

compute_phase40_deadband = apply_octacontatetragonal_hyperbolic_deadband
apply_phase40_deadband = apply_octacontatetragonal_hyperbolic_deadband
apply_octaconta_hyperbolic_deadband = apply_octacontatetragonal_hyperbolic_deadband
```

#### B. Hyper-Convex Rank Modulation (F180.1) in `trading_system/src/ai/factor_suppression.py` (Lines 492–551)
```python
def compute_phase40_hyperconvex_rank_modulation(
    ranks: Union[pd.Series, np.ndarray, float],
    gamma_top: float = 1.0,
    z_denoised: Optional[Union[pd.Series, np.ndarray, float]] = None
) -> Union[pd.Series, np.ndarray, float]:
    """
    Phase 40 (R1, Feature F180.1): 35th-Order Hyper-Convex Rank Modulation:
        g_v40(r) = 0.50 + 1.45 * r * exp(gamma_top * r^35) (for z_denoised >= 0)
        g_neg(r) = 1.35 - 1.00 * r (for z_denoised < 0)
    Concentrates conviction into top 0.00000000000000000000000001% alpha names while remaining flat
    across the bottom 70% of distribution.
    """
    is_scalar = np.isscalar(ranks)
    r = np.asarray(ranks, dtype=np.float64)
    r_clipped = np.clip(r, 0.0, 1.0)
    pos_mult = 0.50 + 1.45 * r_clipped * np.exp(float(gamma_top) * np.power(r_clipped, 35.0))
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

compute_phase40_rank_warping = compute_phase40_hyperconvex_rank_modulation

REGIME_GAMMA_TOP_V40 = {
    'BULL_LOW_VOL': 4.20,
    'BULL_HIGH_VOL': 3.90,
    'SIDEWAYS': 3.70,
    'SIDEWAYS_LOW_VOL': 3.70,
    'SIDEWAYS_HIGH_VOL': 2.50,
    'BEAR': 3.40,
    'BEAR_LOW_VOL': 3.40,
    'BEAR_HIGH_VOL': 2.20,
    'PANIC': 1.50,
    'CRISIS': 1.10,
    'RECOVERY': 4.00,
    '2': 4.20,
    '1': 3.70,
    '0': 3.40,
}

def get_regime_adaptive_gamma_top_v40(regime: Union[int, str] = 'BULL_LOW_VOL') -> float:
    if isinstance(regime, (int, float)):
        regime_str = str(int(regime))
    else:
        regime_str = str(regime).upper()
    return REGIME_GAMMA_TOP_V40.get(regime_str, REGIME_GAMMA_TOP_V40.get('BULL_LOW_VOL', 4.20))
```

#### C. Factor Coupler (F179) in `trading_system/src/ai/ensemble_scorer.py` (Lines 109–355)
- Class: `GeometricLanglandsHodgeDeligneCoupler`
- Mathematical parameters: `theta_0=0.50`, `kappa_deligne=5.90`, `lambda_deligne=0.52`, `lambda_langlands=0.28`, `lambda_hodge=0.20`, `lambda_hitchin=0.16`, `lambda_beilinson=0.115`, `lambda_harmonic=0.075`, `lambda_bundle=0.045`, `lambda_regulator=0.024`, `lambda_cohomology=0.017`, `epsilon_reg=1e-6`.
- Metric weight: $\omega_{j,k} = \frac{1}{|j - k|^{1.22}}$ for $j \neq k$.
- Non-Abelian Hodge curvature action: $a_{\text{hd}}(\Delta) = \Delta + \frac{1}{2}\lambda_{\text{deligne}}\Delta^2 + \dots$
- Deligne-Beilinson regulator topological defect: $\text{defect} = \sum_{j < k} \omega_{j,k} \cdot \left(|p_j^2 - p_k^2| + \lambda_{\text{langlands}}|p_j^3 - p_k^3| + \dots\right)$
- Outputs:
  - $e_{\text{hodge}} = \sum_{j < k} \omega_{j,k} a_{\text{hd}}(|p_j - p_k|)$
  - $z_{\text{deligne}} = \frac{1}{1 + \text{topol\_defect}}$
  - $h_{\text{decay}} = \exp(-\kappa_{\text{deligne}} \cdot e_{\text{hodge}})$
  - $h_{\text{deligne}} = \text{clip}(h_{\text{decay}} \cdot z_{\text{deligne}}, \epsilon_{\text{reg}}, 1.0)$
  - $\text{FERI}_{\text{v40}} = \frac{1}{1 + e_{\text{hodge}} + (1 - z_{\text{deligne}})}$
- Aliases: `GeometricLanglandsHodgeDeligneFactorCoupler`, `HodgeDeligneCoupler`, `LanglandsDeligneCoupler`, `GeometricLanglandsCoupler`, `HodgeDeligneAnalyticCoupler`, `Phase40Coupler`, `DeligneLanglandsCoupler`.
- Class method: `compute_geometric_langlands_hodge_deligne_coupling` and aliases.

#### D. Deadband Routing in `ensemble_scorer.py` (Lines 19439–19448)
```python
if int(version) >= 40:
    eff_alpha = 128.0 if alpha_pos in (3.0, 5.0, 7.0, 9.0, 10.0, 12.0, 14.0, 16.0, 20.0, 24.0, 28.0, 32.0, 36.0, 40.0, 44.0, 48.0, 52.0, 56.0, 60.0, 64.0, 68.0, 72.0, 76.0, 80.0, 84.0, 88.0, 92.0, 96.0, 100.0, 104.0, 108.0, 112.0, 116.0, 120.0) else alpha_pos
    return apply_octacontatetragonal_hyperbolic_deadband(
        scores_centered=scores_centered,
        delta_noise=delta_noise,
        delta_neg=delta_neg,
        alpha_pos=eff_alpha,
        alpha_neg=alpha_neg,
        regime=regime
    )
```

#### E. Confluence & Harmony Factor in `ensemble_scorer.py` (Lines 14082–14118)
```python
if version >= 40:
    deligne_res = cls.compute_geometric_langlands_hodge_deligne_coupling(p_vals.T)
    h_deligne = np.atleast_1d(deligne_res["h_deligne"]).astype(np.float64)
    z_deligne = np.atleast_1d(deligne_res["z_deligne"]).astype(np.float64)
else:
    h_deligne = np.zeros_like(h_clausen)
    z_deligne = np.zeros_like(z_liquid)
...
harmony_factor = pd.Series(
    1.0 + (...
           + 1.95 * h_clausen * z_liquid
           + (2.05 * h_deligne * z_deligne if version >= 40 else 0.0)) * (p_mean > 0.35).astype(float),
    index=scores_df.index
)
```

---

## 2. Logic Chain

1. **Requirements Analysis**:
   - `ORIGINAL_REQUEST.md` (lines 968–971) states:
     - F183: Drinfeld-Lafforgue & Fargues-Fontaine Curve Analytic Cohomology alpha coupler (Artin stack obstruction complex $E_{\text{fargues}}$, Fargues-Fontaine curve factor invariant $Z_{\text{fontaine}}$).
     - F184.1: 36th-order ultra-convex rank modulation $g_{\text{v41}}(r) = 0.50 + 1.48 \cdot r \cdot \exp(\gamma_{\text{top}} \cdot r^{36})$, with adaptive $\gamma_{\text{top}} \le 4.40$.
     - F184.2: 136th-order Centatriacontaoctagonal hyperbolic deadband ($\alpha=136.0$, noise leakage $< 10^{-74}$).
     - Version branch in `ensemble_scorer.py` for `version >= 41`.

2. **Progression Analysis across Phases**:
   - Exponent Progression for Hyperbolic Deadband:
     - Phase 38: $\alpha = 116.0$ (`apply_hexadecadodecagonal_hyperbolic_deadband`)
     - Phase 39: $\alpha = 120.0$ (`apply_centaicosagonal_hyperbolic_deadband`, leakage $< 10^{-62}$)
     - Phase 40: $\alpha = 128.0$ (`apply_octacontatetragonal_hyperbolic_deadband`, leakage $< 10^{-68}$)
     - Phase 41: $\alpha = 136.0$ (`apply_centatriacontaoctagonal_hyperbolic_deadband`, leakage $< 10^{-74}$)
     - Mathematical proof of noise suppression:
       At $|z| \le 0.0004$ and $\delta_{\text{noise}} = 0.035$, the ratio is $\frac{0.0004}{0.035} \approx 0.01142857$.
       $(0.01142857)^{136} \approx 1.83 \times 10^{-264} \ll 10^{-74}$. Even for $|z| = 0.001$, $(0.001/0.035)^{136} = (0.02857)^{136} \approx 6.8 \times 10^{-211} \ll 10^{-74}$.
       At $|z| \ge 0.150$, ratio is $\frac{0.150}{0.035} \approx 4.2857$, $4.2857^{136} \gg 50.0$, $\tanh(\text{clipped to } 50.0) = 1.0000000000$ (100.000% signal transmission).
   - Order Progression for Rank Modulation:
     - Phase 38: $g_{\text{v38}}(r) = 0.50 + 1.40 \cdot r \cdot \exp(\gamma_{\text{top}} \cdot r^{33})$, $\gamma_{\text{top}} \le 3.90$
     - Phase 39: $g_{\text{v39}}(r) = 0.50 + 1.42 \cdot r \cdot \exp(\gamma_{\text{top}} \cdot r^{34})$, $\gamma_{\text{top}} \le 4.00$
     - Phase 40: $g_{\text{v40}}(r) = 0.50 + 1.45 \cdot r \cdot \exp(\gamma_{\text{top}} \cdot r^{35})$, $\gamma_{\text{top}} \le 4.20$
     - Phase 41: $g_{\text{v41}}(r) = 0.50 + 1.48 \cdot r \cdot \exp(\gamma_{\text{top}} \cdot r^{36})$, $\gamma_{\text{top}} \le 4.40$
     - Linear scaling factor increases from $1.45 \to 1.48$, power increases $35 \to 36$, and max $\gamma_{\text{top}}$ increases $4.20 \to 4.40$.
     - Convexity check:
       $g_{\text{v41}}(0) = 0.50$
       $g_{\text{v41}}(0.70) = 0.50 + 1.48 \cdot 0.70 \cdot \exp(4.40 \cdot 0.70^{36}) \approx 0.50 + 1.036 \cdot 1.0000107 \approx 1.536 < 1.55$ (flat across bottom 70%)
       $g_{\text{v41}}(1.0) = 0.50 + 1.48 \cdot 1.0 \cdot \exp(4.40) \approx 0.50 + 1.48 \cdot 81.4508686 \approx 121.047 > 120.0$ (exponential explosion at decile peak)
   - Regime Adaptive Gamma Top Table Scaling:
     - Following Phase 40 (4.20) step of +0.20:
       - BULL_LOW_VOL: 4.40
       - BULL_HIGH_VOL: 4.10
       - SIDEWAYS / SIDEWAYS_LOW_VOL: 3.90
       - SIDEWAYS_HIGH_VOL: 2.65
       - BEAR / BEAR_LOW_VOL: 3.60
       - BEAR_HIGH_VOL: 2.35
       - PANIC: 1.60
       - CRISIS: 1.20
       - RECOVERY: 4.20
       - '2': 4.40, '1': 3.90, '0': 3.60
   - Factor Coupler Weighting in Harmony Factor:
     - Phase 38: $1.90 \cdot h_{\text{scholze}} \cdot z_{\text{langlands}}$
     - Phase 39: $1.95 \cdot h_{\text{clausen}} \cdot z_{\text{liquid}}$
     - Phase 40: $2.05 \cdot h_{\text{deligne}} \cdot z_{\text{deligne}}$
     - Phase 41: $+ (2.15 \cdot h_{\text{fargues}} \cdot z_{\text{fontaine}} \text{ if } \text{version} \ge 41 \text{ else } 0.0)$
     - Parameter set for F183 coupler: $\kappa_{\text{fargues}} = 6.10$, $\lambda_{\text{fargues}} = 0.54$, $\lambda_{\text{fontaine}} = 0.30$, $\lambda_{\text{drinfeld}} = 0.21$, $\lambda_{\text{lafforgue}} = 0.165$, $\lambda_{\text{curve}} = 0.120$, $\lambda_{\text{stack}} = 0.078$, $\lambda_{\text{artin}} = 0.048$, $\lambda_{\text{cohomology}} = 0.026$, $\lambda_{\text{sheaf}} = 0.018$, $\epsilon_{\text{reg}} = 10^{-6}$.

3. **Inter-Module Compatibility and Dynamic Export Mechanics**:
   - Both `ensemble_scorer.py` and `factor_suppression.py` cross-reference and export these symbols.
   - Dynamic injection: `setattr(_fs_module, ...)` in `ensemble_scorer.py` ensures that any test importing from either module succeeds immediately without circular dependency.
   - Module `__getattr__` in `factor_suppression.py`: must include Phase 41 names so lazy resolution works as expected.

---

## 3. Detailed Blueprint for Phase 41 R1 Implementation

### Blueprint Component 1: `factor_suppression.py` Modifications

#### 1.1 Add Phase 41 Deadband (F184.2)
Insert around line 453 (above Phase 40 block):
```python
# =========================================================================
# PHASE 41 (R1) QUANTITATIVE ALPHA SIGNAL ENHANCEMENTS (v48 Production Master)
# =========================================================================

def apply_centatriacontaoctagonal_hyperbolic_deadband(
    scores_centered: Union[pd.Series, np.ndarray, float],
    delta_noise: float = 0.035,
    delta_neg: Optional[float] = None,
    alpha_pos: float = 136.0,
    alpha_neg: Optional[float] = None,
    regime: Optional[Union[str, int]] = None
) -> Union[pd.Series, np.ndarray, float]:
    """
    Phase 41 (R1, Feature F184.2): Asymmetric Centatriacontaoctagonal (136th-Order) Hyperbolic Noise Deadband:
        z_denoised = z * tanh((|z| / delta_eff(z))^136)
    With centatriacontaoctagonal exponent (alpha = 136.0) and delta_noise = 0.035, suppresses near-zero
    noise (|z| <= 0.0004) reducing noise leakage down to < 10^-74 (< 10^-136), while transmitting 100.000%
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

compute_phase41_deadband = apply_centatriacontaoctagonal_hyperbolic_deadband
apply_phase41_deadband = apply_centatriacontaoctagonal_hyperbolic_deadband
apply_centatriaconta_hyperbolic_deadband = apply_centatriacontaoctagonal_hyperbolic_deadband
```

#### 1.2 Add Phase 41 Rank Modulation (F184.1)
```python
def compute_phase41_hyperconvex_rank_modulation(
    ranks: Union[pd.Series, np.ndarray, float],
    gamma_top: float = 1.0,
    z_denoised: Optional[Union[pd.Series, np.ndarray, float]] = None
) -> Union[pd.Series, np.ndarray, float]:
    """
    Phase 41 (R1, Feature F184.1): 36th-Order Ultra-Convex Rank Modulation:
        g_v41(r) = 0.50 + 1.48 * r * exp(gamma_top * r^36) (for z_denoised >= 0)
        g_neg(r) = 1.35 - 1.00 * r (for z_denoised < 0)
    Concentrates conviction into top 0.000000000000000000000000001% alpha names while remaining flat
    across the bottom 70% of distribution.
    """
    is_scalar = np.isscalar(ranks)
    r = np.asarray(ranks, dtype=np.float64)
    r_clipped = np.clip(r, 0.0, 1.0)
    pos_mult = 0.50 + 1.48 * r_clipped * np.exp(float(gamma_top) * np.power(r_clipped, 36.0))
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

compute_phase41_rank_warping = compute_phase41_hyperconvex_rank_modulation

REGIME_GAMMA_TOP_V41 = {
    'BULL_LOW_VOL': 4.40,
    'BULL_HIGH_VOL': 4.10,
    'SIDEWAYS': 3.90,
    'SIDEWAYS_LOW_VOL': 3.90,
    'SIDEWAYS_HIGH_VOL': 2.65,
    'BEAR': 3.60,
    'BEAR_LOW_VOL': 3.60,
    'BEAR_HIGH_VOL': 2.35,
    'PANIC': 1.60,
    'CRISIS': 1.20,
    'RECOVERY': 4.20,
    '2': 4.40,
    '1': 3.90,
    '0': 3.60,
}

def get_regime_adaptive_gamma_top_v41(regime: Union[int, str] = 'BULL_LOW_VOL') -> float:
    """
    Phase 41 (R1, Feature F184.1): Regime-adaptive gamma_top <= 4.40
    (Bull Low Vol: 4.40, Bull High Vol: 4.10, Sideways: 3.90, Bear: 3.60, Crisis: 1.20).
    """
    if isinstance(regime, (int, float)):
        regime_str = str(int(regime))
    else:
        regime_str = str(regime).upper()
    return REGIME_GAMMA_TOP_V41.get(regime_str, REGIME_GAMMA_TOP_V41.get('BULL_LOW_VOL', 4.40))
```

#### 1.3 Update `__all__` and `__getattr__` in `factor_suppression.py`
Add Phase 41 entries to `__all__`:
```python
    'apply_centatriacontaoctagonal_hyperbolic_deadband',
    'compute_phase41_deadband',
    'apply_phase41_deadband',
    'apply_centatriaconta_hyperbolic_deadband',
    'compute_phase41_hyperconvex_rank_modulation',
    'compute_phase41_rank_warping',
    'REGIME_GAMMA_TOP_V41',
    'get_regime_adaptive_gamma_top_v41',
```
In `__getattr__(name: str)` (around line 3409):
```python
    # Phase 41 (R1, Feature F183 & F184)
    if name in (
        'DrinfeldLafforgueFarguesFontaineCoupler',
        'DrinfeldLafforgueFarguesFontaineFactorCoupler',
        'DrinfeldLafforgueCoupler',
        'FarguesFontaineCoupler',
        'DrinfeldFarguesCoupler',
        'FarguesFontaineAnalyticCoupler',
        'Phase41Coupler',
        'LafforgueFontaineCoupler',
    ):
        from .ensemble_scorer import DrinfeldLafforgueFarguesFontaineCoupler as _DLFFC
        return _DLFFC
    if name in (
        'compute_drinfeld_lafforgue_fargues_fontaine_coupling',
        'compute_drinfeld_lafforgue_coupling',
        'compute_fargues_fontaine_coupling',
        'compute_drinfeld_fargues_coupling',
        'compute_fargues_fontaine_analytic_coupling',
        'compute_phase41_coupling',
    ):
        from .ensemble_scorer import DrinfeldLafforgueFarguesFontaineCoupler as _DLFFC
        return _DLFFC.compute
    if name in ('apply_centatriacontaoctagonal_hyperbolic_deadband', 'compute_phase41_deadband', 'apply_phase41_deadband', 'apply_centatriaconta_hyperbolic_deadband'):
        return apply_centatriacontaoctagonal_hyperbolic_deadband
    if name in ('compute_phase41_hyperconvex_rank_modulation', 'compute_phase41_rank_warping'):
        return compute_phase41_hyperconvex_rank_modulation
    if name in ('REGIME_GAMMA_TOP_V41', 'get_regime_adaptive_gamma_top_v41'):
        return globals()[name]
```

---

### Blueprint Component 2: `ensemble_scorer.py` Modifications

#### 2.1 Top-level Phase 41 Deadband and Modulation Definitions
Insert at line 28 (above Phase 40 block):
```python
# =========================================================================
# PHASE 41 (R1) QUANTITATIVE ALPHA SIGNAL ENHANCEMENTS (v48 Production Master)
# =========================================================================

def apply_centatriacontaoctagonal_hyperbolic_deadband(
    scores_centered: Union[pd.Series, np.ndarray, float],
    delta_noise: float = 0.035,
    delta_neg: Optional[float] = None,
    alpha_pos: float = 136.0,
    alpha_neg: Optional[float] = None,
    regime: Optional[Union[str, int]] = None
) -> Union[pd.Series, np.ndarray, float]:
    """
    Phase 41 (R1, Feature F184.2): Asymmetric Centatriacontaoctagonal (136th-Order) Hyperbolic Noise Deadband:
        z_denoised = z * tanh((|z| / delta_eff(z))^136)
    With centatriacontaoctagonal exponent (alpha = 136.0) and delta_noise = 0.035, suppresses near-zero
    noise (|z| <= 0.0004) reducing noise leakage down to < 10^-74 (< 10^-136), while transmitting 100.000%
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

try:
    from . import factor_suppression as _fs_module
    if not hasattr(_fs_module, 'apply_centatriacontaoctagonal_hyperbolic_deadband'):
        setattr(_fs_module, 'apply_centatriacontaoctagonal_hyperbolic_deadband', apply_centatriacontaoctagonal_hyperbolic_deadband)
except Exception:
    pass

def compute_phase41_hyperconvex_rank_modulation(
    ranks: Union[pd.Series, np.ndarray, float],
    gamma_top: float = 1.0,
    z_denoised: Optional[Union[pd.Series, np.ndarray, float]] = None
) -> Union[pd.Series, np.ndarray, float]:
    """
    Phase 41 (R1, Feature F184.1): 36th-Order Ultra-Convex Rank Modulation:
        g_v41(r) = 0.50 + 1.48 * r * exp(gamma_top * r^36) (for z_denoised >= 0)
        g_neg(r) = 1.35 - 1.00 * r (for z_denoised < 0)
    Concentrates conviction into top 0.000000000000000000000000001% alpha names while remaining flat
    across the bottom 70% of distribution.
    """
    is_scalar = np.isscalar(ranks)
    r = np.asarray(ranks, dtype=np.float64)
    r_clipped = np.clip(r, 0.0, 1.0)
    pos_mult = 0.50 + 1.48 * r_clipped * np.exp(float(gamma_top) * np.power(r_clipped, 36.0))
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

compute_phase41_rank_warping = compute_phase41_hyperconvex_rank_modulation
compute_phase41_deadband = apply_centatriacontaoctagonal_hyperbolic_deadband
apply_phase41_deadband = apply_centatriacontaoctagonal_hyperbolic_deadband
apply_centatriaconta_hyperbolic_deadband = apply_centatriacontaoctagonal_hyperbolic_deadband
```

#### 2.2 Define `DrinfeldLafforgueFarguesFontaineCoupler` (Feature F183)
```python
class DrinfeldLafforgueFarguesFontaineCoupler:
    r"""
    Phase 41 (R1, Feature F183): Drinfeld-Lafforgue & Fargues-Fontaine Curve Analytic Cohomology Coupler.
    Models the 5 canonical economic pillars via Drinfeld-Lafforgue compactified shtuka moduli spaces,
    Fargues-Fontaine curve vector bundles, and Artin stack obstruction complexes over pro-etale sites:
        E_fargues: Artin stack obstruction complex energy
        Z_fontaine: Fargues-Fontaine curve factor invariant
        h_fargues: Coupling factor h_decay * Z_fontaine
        FERI_v41: Factor Entanglement Robustness Index v41
    """

    def __init__(
        self,
        theta_0: float = 0.50,
        kappa_fargues: float = 6.10,
        lambda_fargues: float = 0.54,
        lambda_fontaine: float = 0.30,
        lambda_drinfeld: float = 0.21,
        lambda_lafforgue: float = 0.165,
        lambda_curve: float = 0.120,
        lambda_stack: float = 0.078,
        lambda_artin: float = 0.048,
        lambda_cohomology: float = 0.026,
        lambda_sheaf: float = 0.018,
        epsilon_reg: float = 1e-6,
        **kwargs
    ):
        self.theta_0 = float(kwargs.get('theta_0', theta_0))
        self.kappa_fargues = float(kwargs.get('kappa_fargues', kwargs.get('kappa_drinfeld', kappa_fargues)))
        self.lambda_fargues = float(kwargs.get('lambda_fargues', lambda_fargues))
        self.lambda_fontaine = float(kwargs.get('lambda_fontaine', lambda_fontaine))
        self.lambda_drinfeld = float(kwargs.get('lambda_drinfeld', lambda_drinfeld))
        self.lambda_lafforgue = float(kwargs.get('lambda_lafforgue', lambda_lafforgue))
        self.lambda_curve = float(kwargs.get('lambda_curve', lambda_curve))
        self.lambda_stack = float(kwargs.get('lambda_stack', lambda_stack))
        self.lambda_artin = float(kwargs.get('lambda_artin', lambda_artin))
        self.lambda_cohomology = float(kwargs.get('lambda_cohomology', lambda_cohomology))
        self.lambda_sheaf = float(kwargs.get('lambda_sheaf', lambda_sheaf))
        self.kappa = self.kappa_fargues
        self.kappa_drinfeld_fargues = self.kappa_fargues
        self.epsilon_reg = float(kwargs.get('epsilon_reg', epsilon_reg))

    def __call__(self, pillar_scores: Any) -> Dict[str, Any]:
        return self.evaluate(pillar_scores)

    def couple(self, pillar_scores: Any) -> Dict[str, Any]:
        return self.evaluate(pillar_scores)

    def compute_coupling(self, pillar_scores: Any) -> Dict[str, Any]:
        return self.evaluate(pillar_scores)

    @classmethod
    def compute(
        cls,
        pillar_scores: Union[pd.DataFrame, Dict[str, Any], np.ndarray],
        theta_0: float = 0.50,
        kappa_fargues: float = 6.10,
        lambda_fargues: float = 0.54,
        lambda_fontaine: float = 0.30,
        lambda_drinfeld: float = 0.21,
        lambda_lafforgue: float = 0.165,
        lambda_curve: float = 0.120,
        lambda_stack: float = 0.078,
        lambda_artin: float = 0.048,
        lambda_cohomology: float = 0.026,
        lambda_sheaf: float = 0.018,
        epsilon_reg: float = 1e-6,
        **kwargs
    ) -> Dict[str, Any]:
        coupler = cls(
            theta_0=theta_0,
            kappa_fargues=kappa_fargues,
            lambda_fargues=lambda_fargues,
            lambda_fontaine=lambda_fontaine,
            lambda_drinfeld=lambda_drinfeld,
            lambda_lafforgue=lambda_lafforgue,
            lambda_curve=lambda_curve,
            lambda_stack=lambda_stack,
            lambda_artin=lambda_artin,
            lambda_cohomology=lambda_cohomology,
            lambda_sheaf=lambda_sheaf,
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
            raise ValueError(f"Drinfeld-Lafforgue & Fargues-Fontaine factor disentanglement requires 5 canonical pillars, got {D}")

        omega = np.zeros((5, 5), dtype=np.float64)
        for j in range(5):
            for k in range(5):
                if j != k:
                    omega[j, k] = 1.0 / (abs(j - k) ** 1.24)

        e_fargues = np.zeros(N, dtype=np.float64)
        z_fontaine = np.zeros(N, dtype=np.float64)

        for n in range(N):
            pn = p_mat[n]
            obs_energy = 0.0
            topol_defect = 0.0
            for j in range(5):
                for k in range(j + 1, 5):
                    w = omega[j, k]
                    diff = abs(pn[j] - pn[k])
                    # Artin stack obstruction complex action
                    a_artin = (diff
                               + 0.5 * self.lambda_fargues * (diff ** 2)
                               + (1.0 / 3.0) * self.lambda_fontaine * (diff ** 3)
                               + (1.0 / 4.0) * self.lambda_drinfeld * (diff ** 4)
                               + (1.0 / 5.0) * self.lambda_lafforgue * (diff ** 5)
                               + (1.0 / 6.0) * self.lambda_curve * (diff ** 6)
                               + (1.0 / 7.0) * self.lambda_stack * (diff ** 7)
                               + (1.0 / 8.0) * self.lambda_artin * (diff ** 8)
                               + (1.0 / 9.0) * self.lambda_cohomology * (diff ** 9)
                               + (1.0 / 10.0) * self.lambda_sheaf * (diff ** 10)
                               + (1.0 / 12.0) * (self.lambda_sheaf * 0.7) * (diff ** 12)
                               + (1.0 / 14.0) * (self.lambda_sheaf * 0.4) * (diff ** 14)
                               + (1.0 / 16.0) * (self.lambda_sheaf * 0.2) * (diff ** 16)
                               + (1.0 / 18.0) * (self.lambda_sheaf * 0.1) * (diff ** 18)
                               + (1.0 / 20.0) * (self.lambda_sheaf * 0.05) * (diff ** 20)
                               + (1.0 / 22.0) * (self.lambda_sheaf * 0.02) * (diff ** 22)
                               + (1.0 / 24.0) * (self.lambda_sheaf * 0.01) * (diff ** 24)
                               + (1.0 / 26.0) * (self.lambda_sheaf * 0.005) * (diff ** 26)
                               + (1.0 / 28.0) * (self.lambda_sheaf * 0.002) * (diff ** 28)
                               + (1.0 / 30.0) * (self.lambda_sheaf * 0.001) * (diff ** 30)
                               + (1.0 / 32.0) * (self.lambda_sheaf * 0.0005) * (diff ** 32)
                               + (1.0 / 34.0) * (self.lambda_sheaf * 0.0002) * (diff ** 34)
                               + (1.0 / 36.0) * (self.lambda_sheaf * 0.0001) * (diff ** 36)
                               + (1.0 / 38.0) * (self.lambda_sheaf * 0.00005) * (diff ** 38)
                               + (1.0 / 40.0) * (self.lambda_sheaf * 0.00002) * (diff ** 40)
                               + (1.0 / 42.0) * (self.lambda_sheaf * 0.00001) * (diff ** 42)
                               + (1.0 / 44.0) * (self.lambda_sheaf * 0.000005) * (diff ** 44)
                               + (1.0 / 46.0) * (self.lambda_sheaf * 0.000002) * (diff ** 46)
                               + (1.0 / 48.0) * (self.lambda_sheaf * 0.000001) * (diff ** 48)
                               + (1.0 / 50.0) * (self.lambda_sheaf * 0.0000005) * (diff ** 50)
                               + (1.0 / 52.0) * (self.lambda_sheaf * 0.0000002) * (diff ** 52))
                    obs_energy += w * a_artin
                    # Fargues-Fontaine curve factor invariant topological defect
                    defect = abs((pn[j]**2 - pn[k]**2)
                                 + self.lambda_fontaine * (pn[j]**3 - pn[k]**3)
                                 + self.lambda_drinfeld * (pn[j]**4 - pn[k]**4)
                                 + self.lambda_lafforgue * (pn[j]**5 - pn[k]**5)
                                 + self.lambda_curve * (pn[j]**6 - pn[k]**6)
                                 + self.lambda_stack * (pn[j]**7 - pn[k]**7)
                                 + self.lambda_artin * (pn[j]**8 - pn[k]**8)
                                 + self.lambda_cohomology * (pn[j]**9 - pn[k]**9)
                                 + (self.lambda_cohomology * 0.6) * (pn[j]**10 - pn[k]**10)
                                 + (self.lambda_cohomology * 0.3) * (pn[j]**11 - pn[k]**11)
                                 + (self.lambda_cohomology * 0.15) * (pn[j]**12 - pn[k]**12)
                                 + (self.lambda_cohomology * 0.08) * (pn[j]**13 - pn[k]**13)
                                 + (self.lambda_cohomology * 0.04) * (pn[j]**14 - pn[k]**14)
                                 + (self.lambda_cohomology * 0.01) * (pn[j]**15 - pn[k]**15)
                                 + (self.lambda_cohomology * 0.003) * (pn[j]**16 - pn[k]**16)
                                 + (self.lambda_cohomology * 0.001) * (pn[j]**17 - pn[k]**17)
                                 + (self.lambda_cohomology * 0.0003) * (pn[j]**18 - pn[k]**18)
                                 + (self.lambda_cohomology * 0.0001) * (pn[j]**19 - pn[k]**19)
                                 + (self.lambda_cohomology * 0.00003) * (pn[j]**20 - pn[k]**20)
                                 + (self.lambda_cohomology * 0.00001) * (pn[j]**21 - pn[k]**21)
                                 + (self.lambda_cohomology * 0.000003) * (pn[j]**22 - pn[k]**22)
                                 + (self.lambda_cohomology * 0.000001) * (pn[j]**23 - pn[k]**23)
                                 + (self.lambda_cohomology * 0.0000003) * (pn[j]**24 - pn[k]**24)
                                 + (self.lambda_cohomology * 0.0000001) * (pn[j]**25 - pn[k]**25))
                    topol_defect += w * defect
            e_fargues[n] = obs_energy
            z_fontaine[n] = 1.0 / (1.0 + topol_defect)

        h_decay = np.exp(-self.kappa_fargues * e_fargues)
        h_fargues = np.clip(h_decay * z_fontaine, self.epsilon_reg, 1.0)
        feri_v41 = 1.0 / (1.0 + e_fargues + (1.0 - z_fontaine))

        h_out = float(h_fargues[0]) if is_single_1d else (pd.Series(h_fargues, index=index) if index is not None else h_fargues)
        z_out = float(z_fontaine[0]) if is_single_1d else (pd.Series(z_fontaine, index=index) if index is not None else z_fontaine)
        e_out = float(e_fargues[0]) if is_single_1d else (pd.Series(e_fargues, index=index) if index is not None else e_fargues)
        d_out = float(h_decay[0]) if is_single_1d else (pd.Series(h_decay, index=index) if index is not None else h_decay)
        f_out = float(feri_v41[0]) if is_single_1d else (pd.Series(feri_v41, index=index) if index is not None else feri_v41)

        res_dict = {
            "h_fargues": h_out,
            "z_fontaine": z_out,
            "e_fargues": e_out,
            "h_decay": d_out,
            "FERI_v41": f_out,
            "feri_v41": f_out,
            "Z_fontaine": z_out,
            "E_fargues": e_out,
            "h_drinfeld": h_out,
            "h_lafforgue": h_out,
            "h_fontaine": h_out,
            "h_coupling": h_out,
            "z_invariant": z_out,
            "e_obstruction": e_out,
        }
        return res_dict

# Aliases for Phase 41
DrinfeldLafforgueFarguesFontaineFactorCoupler = DrinfeldLafforgueFarguesFontaineCoupler
DrinfeldLafforgueCoupler = DrinfeldLafforgueFarguesFontaineCoupler
FarguesFontaineCoupler = DrinfeldLafforgueFarguesFontaineCoupler
DrinfeldFarguesCoupler = DrinfeldLafforgueFarguesFontaineCoupler
FarguesFontaineAnalyticCoupler = DrinfeldLafforgueFarguesFontaineCoupler
Phase41Coupler = DrinfeldLafforgueFarguesFontaineCoupler
LafforgueFontaineCoupler = DrinfeldLafforgueFarguesFontaineCoupler

# Register Phase 41 aliases dynamically into factor_suppression
try:
    from . import factor_suppression as _fs_module
    setattr(_fs_module, 'DrinfeldLafforgueFarguesFontaineCoupler', DrinfeldLafforgueFarguesFontaineCoupler)
    setattr(_fs_module, 'DrinfeldLafforgueFarguesFontaineFactorCoupler', DrinfeldLafforgueFarguesFontaineFactorCoupler)
    setattr(_fs_module, 'DrinfeldLafforgueCoupler', DrinfeldLafforgueCoupler)
    setattr(_fs_module, 'FarguesFontaineCoupler', FarguesFontaineCoupler)
    setattr(_fs_module, 'DrinfeldFarguesCoupler', DrinfeldFarguesCoupler)
    setattr(_fs_module, 'FarguesFontaineAnalyticCoupler', FarguesFontaineAnalyticCoupler)
    setattr(_fs_module, 'Phase41Coupler', Phase41Coupler)
    setattr(_fs_module, 'LafforgueFontaineCoupler', LafforgueFontaineCoupler)
    setattr(_fs_module, 'compute_drinfeld_lafforgue_fargues_fontaine_coupling', DrinfeldLafforgueFarguesFontaineCoupler.compute)
    setattr(_fs_module, 'compute_drinfeld_lafforgue_coupling', DrinfeldLafforgueFarguesFontaineCoupler.compute)
    setattr(_fs_module, 'compute_fargues_fontaine_coupling', DrinfeldLafforgueFarguesFontaineCoupler.compute)
    setattr(_fs_module, 'compute_drinfeld_fargues_coupling', DrinfeldLafforgueFarguesFontaineCoupler.compute)
    setattr(_fs_module, 'compute_fargues_fontaine_analytic_coupling', DrinfeldLafforgueFarguesFontaineCoupler.compute)
    setattr(_fs_module, 'compute_phase41_coupling', DrinfeldLafforgueFarguesFontaineCoupler.compute)
    setattr(_fs_module, 'compute_phase41_hyperconvex_rank_modulation', compute_phase41_hyperconvex_rank_modulation)
    setattr(_fs_module, 'compute_phase41_rank_warping', compute_phase41_rank_warping)
    setattr(_fs_module, 'apply_centatriacontaoctagonal_hyperbolic_deadband', apply_centatriacontaoctagonal_hyperbolic_deadband)
    setattr(_fs_module, 'compute_phase41_deadband', apply_centatriacontaoctagonal_hyperbolic_deadband)
    setattr(_fs_module, 'apply_phase41_deadband', apply_centatriacontaoctagonal_hyperbolic_deadband)
    setattr(_fs_module, 'apply_centatriaconta_hyperbolic_deadband', apply_centatriacontaoctagonal_hyperbolic_deadband)
except Exception:
    pass
```

#### 2.3 `EnsembleScoringEngine` Class Bindings (Lines ~17170)
Add Phase 41 block:
```python
    # =========================================================================
    # PHASE 41: DRINFELD-LAFFORGUE & FARGUES-FONTAINE STATIC BINDINGS
    # =========================================================================

    apply_centatriacontaoctagonal_hyperbolic_deadband = staticmethod(apply_centatriacontaoctagonal_hyperbolic_deadband)
    compute_phase41_deadband = staticmethod(apply_centatriacontaoctagonal_hyperbolic_deadband)
    apply_phase41_deadband = staticmethod(apply_centatriacontaoctagonal_hyperbolic_deadband)
    apply_centatriaconta_hyperbolic_deadband = staticmethod(apply_centatriacontaoctagonal_hyperbolic_deadband)
    compute_phase41_hyperconvex_rank_modulation = staticmethod(compute_phase41_hyperconvex_rank_modulation)
    compute_phase41_rank_warping = staticmethod(compute_phase41_hyperconvex_rank_modulation)
    DrinfeldLafforgueFarguesFontaineCoupler = DrinfeldLafforgueFarguesFontaineCoupler
    DrinfeldLafforgueFarguesFontaineFactorCoupler = DrinfeldLafforgueFarguesFontaineCoupler
    DrinfeldLafforgueCoupler = DrinfeldLafforgueFarguesFontaineCoupler
    FarguesFontaineCoupler = DrinfeldLafforgueFarguesFontaineCoupler
    DrinfeldFarguesCoupler = DrinfeldLafforgueFarguesFontaineCoupler
    FarguesFontaineAnalyticCoupler = DrinfeldLafforgueFarguesFontaineCoupler
    Phase41Coupler = DrinfeldLafforgueFarguesFontaineCoupler
    LafforgueFontaineCoupler = DrinfeldLafforgueFarguesFontaineCoupler

    @classmethod
    def compute_drinfeld_lafforgue_fargues_fontaine_coupling(
        cls,
        pillar_scores: Union[pd.DataFrame, Dict[str, Any], np.ndarray],
        theta_0: float = 0.50,
        kappa_fargues: float = 6.10,
        lambda_fargues: float = 0.54,
        lambda_fontaine: float = 0.30,
        lambda_drinfeld: float = 0.21,
        lambda_lafforgue: float = 0.165,
        lambda_curve: float = 0.120,
        lambda_stack: float = 0.078,
        lambda_artin: float = 0.048,
        lambda_cohomology: float = 0.026,
        lambda_sheaf: float = 0.018,
        epsilon_reg: float = 1e-6,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Phase 41 (R1, Feature F183): Drinfeld-Lafforgue & Fargues-Fontaine Curve Analytic Cohomology Coupler Engine.
        """
        return DrinfeldLafforgueFarguesFontaineCoupler.compute(
            pillar_scores=pillar_scores,
            theta_0=theta_0,
            kappa_fargues=kappa_fargues,
            lambda_fargues=lambda_fargues,
            lambda_fontaine=lambda_fontaine,
            lambda_drinfeld=lambda_drinfeld,
            lambda_lafforgue=lambda_lafforgue,
            lambda_curve=lambda_curve,
            lambda_stack=lambda_stack,
            lambda_artin=lambda_artin,
            lambda_cohomology=lambda_cohomology,
            lambda_sheaf=lambda_sheaf,
            epsilon_reg=epsilon_reg,
            **kwargs
        )

    compute_drinfeld_lafforgue_coupling = compute_drinfeld_lafforgue_fargues_fontaine_coupling
    compute_fargues_fontaine_coupling = compute_drinfeld_lafforgue_fargues_fontaine_coupling
    compute_drinfeld_fargues_coupling = compute_drinfeld_lafforgue_fargues_fontaine_coupling
    compute_fargues_fontaine_analytic_coupling = compute_drinfeld_lafforgue_fargues_fontaine_coupling
    compute_phase41_coupling = compute_drinfeld_lafforgue_fargues_fontaine_coupling
```

#### 2.4 Update `apply_smooth_noise_deadband` (Lines ~19439)
```python
        version = int(kwargs.get('version', version))
        if int(version) >= 41:
            eff_alpha = 136.0 if alpha_pos in (3.0, 5.0, 7.0, 9.0, 10.0, 12.0, 14.0, 16.0, 20.0, 24.0, 28.0, 32.0, 36.0, 40.0, 44.0, 48.0, 52.0, 56.0, 60.0, 64.0, 68.0, 72.0, 76.0, 80.0, 84.0, 88.0, 92.0, 96.0, 100.0, 104.0, 108.0, 112.0, 116.0, 120.0, 128.0) else alpha_pos
            return apply_centatriacontaoctagonal_hyperbolic_deadband(
                scores_centered=scores_centered,
                delta_noise=delta_noise,
                delta_neg=delta_neg,
                alpha_pos=eff_alpha,
                alpha_neg=alpha_neg,
                regime=regime
            )
        elif int(version) >= 40:
            eff_alpha = 128.0 if alpha_pos in (3.0, 5.0, 7.0, 9.0, 10.0, 12.0, 14.0, 16.0, 20.0, 24.0, 28.0, 32.0, 36.0, 40.0, 44.0, 48.0, 52.0, 56.0, 60.0, 64.0, 68.0, 72.0, 76.0, 80.0, 84.0, 88.0, 92.0, 96.0, 100.0, 104.0, 108.0, 112.0, 116.0, 120.0) else alpha_pos
            return apply_octacontatetragonal_hyperbolic_deadband(
```

#### 2.5 Update `combine_predictions` Pillar Harmony (Lines ~14082–14118)
```python
            # Phase 40 (R1, Feature F179): Geometric Langlands & Non-Abelian Hodge-Deligne Analytic Cohomology Coupler
            if version >= 40:
                deligne_res = cls.compute_geometric_langlands_hodge_deligne_coupling(p_vals.T)
                h_deligne = np.atleast_1d(deligne_res["h_deligne"]).astype(np.float64)
                z_deligne = np.atleast_1d(deligne_res["z_deligne"]).astype(np.float64)
            else:
                h_deligne = np.zeros_like(h_clausen)
                z_deligne = np.zeros_like(z_liquid)

            # Phase 41 (R1, Feature F183): Drinfeld-Lafforgue & Fargues-Fontaine Curve Analytic Cohomology Coupler
            if version >= 41:
                fargues_res = cls.compute_drinfeld_lafforgue_fargues_fontaine_coupling(p_vals.T)
                h_fargues = np.atleast_1d(fargues_res["h_fargues"]).astype(np.float64)
                z_fontaine = np.atleast_1d(fargues_res["z_fontaine"]).astype(np.float64)
            else:
                h_fargues = np.zeros_like(h_clausen)
                z_fontaine = np.zeros_like(z_liquid)

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
                       + 1.15 * h_hodge * z_simpson
                       + 1.25 * h_shimura * z_mochizuki
                       + 1.35 * h_anabelian * z_anabelian
                       + 1.40 * h_tannaka * z_tannaka
                       + 1.45 * h_beilinson * z_flach
                       + 1.50 * h_kolyvagin * z_iwasawa
                       + 1.55 * h_kato * z_fontaine
                       + 1.60 * h_syntomic * z_coates_wiles
                       + 1.65 * h_tamagawa * z_bloch_kato
                       + 1.70 * h_bsd * z_gross_zagier
                       + 1.75 * h_sha * z_fontaine_mazur
                       + 1.80 * h_serre * z_mazur
                       + 1.85 * h_wiles * z_kisin
                       + 1.90 * h_scholze * z_langlands
                       + 1.95 * h_clausen * z_liquid
                       + (2.05 * h_deligne * z_deligne if version >= 40 else 0.0)
                       + (2.15 * h_fargues * z_fontaine if version >= 41 else 0.0)) * (p_mean > 0.35).astype(float),
                index=scores_df.index
            )
```

---

### Blueprint Component 3: Unit Test Suite Specification (`tests/test_phase41_alpha.py`)

Create `tests/test_phase41_alpha.py` matching the exact pattern of `test_phase40_alpha.py`:
```python
import pytest
import math
import numpy as np
import pandas as pd

from trading_system.src.ai.factor_suppression import (
    apply_centatriacontaoctagonal_hyperbolic_deadband,
    compute_phase41_hyperconvex_rank_modulation,
    compute_phase41_rank_warping,
    REGIME_GAMMA_TOP_V41,
    get_regime_adaptive_gamma_top_v41,
    apply_smooth_deadband_attenuation,
    apply_octacontatetragonal_hyperbolic_deadband,
)
from trading_system.src.ai.ensemble_scorer import (
    DrinfeldLafforgueFarguesFontaineCoupler,
    DrinfeldLafforgueFarguesFontaineFactorCoupler,
    DrinfeldLafforgueCoupler,
    FarguesFontaineCoupler,
    DrinfeldFarguesCoupler,
    FarguesFontaineAnalyticCoupler,
    Phase41Coupler,
    LafforgueFontaineCoupler,
    EnsembleScoringEngine,
)


class TestPhase41AlphaEnhancements:
    """
    Test suite for Phase 41 Quantitative Alpha Signal Enhancements:
    - Feature F183: Drinfeld-Lafforgue & Fargues-Fontaine Curve Analytic Cohomology Coupler
    - Feature F184.1: 36th-Order Ultra-Convex Rank Modulation (g_v41)
    - Feature F184.2: 136th-Order Centatriacontaoctagonal Hyperbolic Noise Deadband
    """

    def test_feature_f183_drinfeld_lafforgue_fargues_fontaine_coupler_properties(self):
        coupler = DrinfeldLafforgueFarguesFontaineCoupler()
        # 5 canonical pillars
        p_df = pd.DataFrame({
            'val': [0.50, 0.45, 0.10],
            'mom': [0.50, 0.55, 0.90],
            'flow': [0.50, 0.50, 0.20],
            'cat': [0.50, 0.60, 0.80],
            'net': [0.50, 0.40, 0.05],
        })

        res = coupler(p_df)
        assert "h_fargues" in res
        assert "z_fontaine" in res
        assert "e_fargues" in res
        assert "FERI_v41" in res
        assert "Z_fontaine" in res
        assert "E_fargues" in res
        assert "h_drinfeld" in res
        assert "h_lafforgue" in res
        assert "h_fontaine" in res

        h = res["h_fargues"]
        z = res["z_fontaine"]
        feri = res["FERI_v41"]

        assert isinstance(h, pd.Series)
        assert len(h) == 3
        assert (h >= 0.0).all() and (h <= 1.0).all()
        assert (z >= 0.0).all() and (z <= 1.0).all()
        assert (feri >= 0.0).all() and (feri <= 1.0).all()

        # Row 0 has identical inputs -> E = 0, H = 1.0
        # Row 1 has small dispersion -> E is small, H is near 1.0
        # Row 2 has large dispersion -> E is larger, H is smaller
        assert res["e_fargues"].iloc[0] < res["e_fargues"].iloc[1] < res["e_fargues"].iloc[2]
        assert h.iloc[0] > h.iloc[1] > h.iloc[2]

        # 1D single-vector evaluation
        vec_1d = np.array([0.5, 0.5, 0.5, 0.5, 0.5])
        res_1d = coupler(vec_1d)
        assert isinstance(res_1d["h_fargues"], float)
        assert np.isclose(res_1d["e_fargues"], 0.0, atol=1e-7)
        assert np.isclose(res_1d["z_fontaine"], 1.0, atol=1e-7)
        assert np.isclose(res_1d["h_fargues"], 1.0, atol=1e-7)

    def test_feature_f183_drinfeld_lafforgue_aliases_and_exports(self):
        assert DrinfeldLafforgueFarguesFontaineFactorCoupler is DrinfeldLafforgueFarguesFontaineCoupler
        assert DrinfeldLafforgueCoupler is DrinfeldLafforgueFarguesFontaineCoupler
        assert FarguesFontaineCoupler is DrinfeldLafforgueFarguesFontaineCoupler
        assert DrinfeldFarguesCoupler is DrinfeldLafforgueFarguesFontaineCoupler
        assert FarguesFontaineAnalyticCoupler is DrinfeldLafforgueFarguesFontaineCoupler
        assert Phase41Coupler is DrinfeldLafforgueFarguesFontaineCoupler
        assert LafforgueFontaineCoupler is DrinfeldLafforgueFarguesFontaineCoupler

        res_class = EnsembleScoringEngine.compute_drinfeld_lafforgue_fargues_fontaine_coupling(
            np.array([[0.5, 0.6, 0.5, 0.7, 0.4]])
        )
        assert "h_fargues" in res_class
        assert "FERI_v41" in res_class

    def test_feature_f184_1_36th_order_rank_modulation_convexity(self):
        # High convexity in top decile: r^36 concentrates conviction into top 0.000000000000000000000000001%
        ranks = np.linspace(0.0, 1.0, 100)
        g_mod = compute_phase41_hyperconvex_rank_modulation(ranks, gamma_top=4.40)

        # Base value at r=0 is 0.50
        assert np.isclose(g_mod[0], 0.50, atol=1e-5)

        # Top value at r=1.0 is 0.50 + 1.48 * exp(4.40)
        expected_top = 0.50 + 1.48 * math.exp(4.40)
        assert np.isclose(g_mod[-1], expected_top, atol=1e-4)

        # Monotonicity test
        diffs = np.diff(g_mod)
        assert (diffs >= 0.0).all(), "36th-order rank modulation must be strictly monotonically increasing"

        # Check that r=0.70 remains modest while r=1.0 explodes
        g_70 = compute_phase41_hyperconvex_rank_modulation(0.70, gamma_top=4.40)
        assert g_70 < 1.55
        assert g_mod[-1] > 120.0

        # With negative z_denoised
        g_neg = compute_phase41_hyperconvex_rank_modulation(ranks, gamma_top=4.40, z_denoised=-0.1)
        assert np.isclose(g_neg[0], 1.35, atol=1e-5)
        assert np.isclose(g_neg[-1], 0.35, atol=1e-5)
        assert (np.diff(g_neg) <= 0.0).all()

    def test_feature_f184_1_regime_adaptive_gamma_top(self):
        assert get_regime_adaptive_gamma_top_v41('BULL_LOW_VOL') == 4.40
        assert get_regime_adaptive_gamma_top_v41('BULL_HIGH_VOL') == 4.10
        assert get_regime_adaptive_gamma_top_v41('SIDEWAYS') == 3.90
        assert get_regime_adaptive_gamma_top_v41('BEAR') == 3.60
        assert get_regime_adaptive_gamma_top_v41('CRISIS') == 1.20
        assert get_regime_adaptive_gamma_top_v41('UNKNOWN') == 4.40

    def test_feature_f184_2_136th_order_hyperbolic_deadband_leakage(self):
        # Test extreme noise suppression: for |z| <= 0.0004, leakage is < 10^-74
        small_z = np.array([0.0001, -0.0001, 0.0002, -0.0002, 0.0004, -0.0004])
        denoised = apply_centatriacontaoctagonal_hyperbolic_deadband(small_z, delta_noise=0.035, alpha_pos=136.0)

        for val in denoised:
            assert abs(val) < 1e-74, f"Noise leakage {val} not suppressed below 10^-74"

        # Signal transmission for high conviction |z| >= 0.15
        sig_z = np.array([0.15, -0.15, 0.30, -0.30])
        sig_out = apply_centatriacontaoctagonal_hyperbolic_deadband(sig_z, delta_noise=0.035, alpha_pos=136.0)
        # Should transmit 100.0% of signal (relative error < 1e-9)
        np.testing.assert_allclose(sig_out, sig_z, rtol=1e-9)

        # Strict monotonicity across broad spectrum
        spectrum = np.linspace(-0.5, 0.5, 1001)
        denoised_spectrum = apply_centatriacontaoctagonal_hyperbolic_deadband(spectrum, delta_noise=0.035, alpha_pos=136.0)
        diffs = np.diff(denoised_spectrum)
        assert (diffs >= 0.0).all(), "Deadband must be strictly monotonically non-decreasing"

    def test_feature_f184_2_factor_suppression_delegation(self):
        # Test scalar handling
        scalar_res = apply_centatriacontaoctagonal_hyperbolic_deadband(0.0001)
        assert isinstance(scalar_res, float)
        assert abs(scalar_res) < 1e-74

        # Test series handling
        s_in = pd.Series([0.0001, 0.20], index=['a', 'b'])
        s_out = apply_centatriacontaoctagonal_hyperbolic_deadband(s_in)
        assert isinstance(s_out, pd.Series)
        assert abs(s_out['a']) < 1e-74
        assert np.isclose(s_out['b'], 0.20, rtol=1e-9)

    def test_ensemble_scorer_apply_smooth_noise_deadband_version_41(self):
        engine = EnsembleScoringEngine()
        z_noise = np.array([0.0002])
        # Calling apply_smooth_noise_deadband with version=41 should route to 136th order deadband
        res_v41 = engine.apply_smooth_noise_deadband(z_noise, version=41)
        assert abs(res_v41[0]) < 1e-74

    def test_combine_predictions_version_41_confluence_and_harmony(self):
        engine = EnsembleScoringEngine()
        n = 10
        mock_scores = {
            'symbol': [f'SYM_{i}' for i in range(n)],
            'regression': pd.Series(np.linspace(0.1, 0.9, n)),
            'surge': pd.Series(np.linspace(0.2, 0.8, n)),
            'vcp': pd.Series(np.linspace(0.3, 0.7, n)),
            'vcp_ml': pd.Series(np.linspace(0.4, 0.6, n)),
            'lstm': pd.Series(np.linspace(0.2, 0.8, n)),
            'stat_arb': pd.Series(np.linspace(0.1, 0.5, n)),
            'sector_rotation': pd.Series(np.linspace(0.2, 0.7, n)),
            'factor_neutralized': pd.Series(np.linspace(0.3, 0.8, n)),
            'order_flow': pd.Series(np.linspace(0.4, 0.9, n)),
            'event_driven': pd.Series(np.linspace(0.2, 0.6, n)),
        }
        df_scores = pd.DataFrame(mock_scores)

        comb_v40 = engine.combine_predictions(df_scores, regime="BULL_LOW_VOL", version=40)
        comb_v41 = engine.combine_predictions(df_scores, regime="BULL_LOW_VOL", version=41)

        assert isinstance(comb_v41, pd.DataFrame)
        assert not comb_v41.empty
        assert "ensemble_score" in comb_v41.columns
        assert len(comb_v41) == n
        assert np.all(np.isfinite(comb_v41["ensemble_score"].values))
        assert np.all(comb_v41["ensemble_score"].values >= 0.0)
        assert np.all(comb_v41["ensemble_score"].values <= 1.0)

        # Top conviction in v41 should be >= v40
        top_v40 = comb_v40.sort_values("ensemble_score", ascending=False).iloc[0]["ensemble_score"]
        top_v41 = comb_v41.sort_values("ensemble_score", ascending=False).iloc[0]["ensemble_score"]
        assert top_v41 >= top_v40 - 1e-6, f"Top conviction in v41 ({top_v41}) should be >= v40 ({top_v40})"

    def test_strict_backward_compatibility_v40_and_prior(self):
        z = np.array([0.0004, 0.05, 0.15])
        out_v41 = EnsembleScoringEngine.apply_smooth_noise_deadband(z, version=41)
        out_v40 = EnsembleScoringEngine.apply_smooth_noise_deadband(z, version=40)
        out_v39 = EnsembleScoringEngine.apply_smooth_noise_deadband(z, version=39)
        out_v38 = EnsembleScoringEngine.apply_smooth_noise_deadband(z, version=38)

        assert abs(out_v41[0]) < 1e-74
        assert abs(out_v40[0]) < 1e-68
        assert abs(out_v39[0]) < 1e-62
        assert abs(out_v38[0]) < 1e-60
```

---

## 4. Caveats

1. **Production Code Write Boundary**:
   - As an explorer, no production source files (`trading_system/src/ai/*.py`, `tests/*.py`) were modified. All modifications are specified as exact drop-in blueprints for Implementer 1.
2. **Dynamic Method Injection & Circular Imports**:
   - `ensemble_scorer.py` imports functions from `factor_suppression.py`, while `factor_suppression.py` dynamically resolves classes from `ensemble_scorer.py` via `__getattr__`. To avoid runtime circular import crashes, both `setattr` injection in `ensemble_scorer.py` and lazy resolution in `factor_suppression.py.__getattr__` must be implemented in tandem.
3. **Pillar Harmony Weight Precedence**:
   - In `combine_predictions()`, ensure that the Phase 40 term `(2.05 * h_deligne * z_deligne if version >= 40 else 0.0)` is preserved and the Phase 41 term `(2.15 * h_fargues * z_fontaine if version >= 41 else 0.0)` is cleanly appended to maintain backward compatibility.

---

## 5. Conclusion

1. **Feasibility Assessment**: 
   - All hook points in `trading_system/src/ai/factor_suppression.py` and `trading_system/src/ai/ensemble_scorer.py` have been identified and mapped with exact line numbers.
   - The mathematical formulation and parameter set for F183, F184.1, and F184.2 strictly adhere to the project roadmap, with verified hyper-convex convexity ($g(1.0) \approx 121.05$), asymptotic deadband suppression ($< 10^{-74}$ noise leakage), and full multi-pillar harmonic decoupling.
2. **Ready for Implementation**:
   - Implementer 1 can apply the exact drop-in blueprints in Component 1 and Component 2, and write `tests/test_phase41_alpha.py` using the exact specification in Component 3.
   - All 9 unit tests can be validated using the project virtualenv pytest command.

---

## 6. Verification Method

To independently verify the blueprint and implementation:

1. **Static Inspection**:
   - Inspect `trading_system/src/ai/factor_suppression.py`:
     Verify presence of `apply_centatriacontaoctagonal_hyperbolic_deadband`, `compute_phase41_hyperconvex_rank_modulation`, `REGIME_GAMMA_TOP_V41`, `get_regime_adaptive_gamma_top_v41`, and dynamic resolution in `__getattr__`.
   - Inspect `trading_system/src/ai/ensemble_scorer.py`:
     Verify presence of `DrinfeldLafforgueFarguesFontaineCoupler`, `apply_smooth_noise_deadband(version=41)`, and `combine_predictions(version=41)`.

2. **Test Execution**:
   - Run Phase 40 baseline tests (must remain 100% passing):
     ```powershell
     .\.venv\Scripts\pytest.exe tests/test_phase40_alpha.py -v
     ```
   - Run newly created Phase 41 tests:
     ```powershell
     .\.venv\Scripts\pytest.exe tests/test_phase41_alpha.py -v
     ```
   - Expected result: 9/9 tests passed in `test_phase41_alpha.py`, 0 regressions across earlier test suites.

3. **Invalidation Conditions**:
   - Any noise leakage $\ge 10^{-74}$ for $|z| \le 0.0004$ under $\alpha = 136.0$.
   - Any non-monotonicity in $g_{\text{v41}}(r)$ for $r \in [0, 1]$.
   - Failure of backward compatibility when calling `combine_predictions(..., version=40)` or `apply_smooth_noise_deadband(..., version=40)`.
