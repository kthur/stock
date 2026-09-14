# Comprehensive Survey & Architectural Blueprint: Phase 40 Quant Alpha Enhancements

**Date**: 2026-09-14  
**Author**: Explorer 1 (Alpha Signal Hook Points & Architecture Investigation)  
**Target Scope**: 
- Feature F179: Geometric Langlands & Non-Abelian Hodge-Deligne Analytic Cohomology Coupler
- Feature F180.1: 35th-Order Hyper-Convex Rank Modulation ($g_{\text{v40}}(r)$, $\gamma_{\text{top}} \le 4.20$)
- Feature F180.2: 128th-Order Octaconta-tetragonal Hyperbolic Deadband ($\alpha = 128.0$, leakage $< 10^{-68}$)
- Version $\ge 40$ Branch Points in `src/ai/ensemble_scorer.py` and `src/ai/factor_suppression.py`
- Verification Suite Design: `tests/test_phase40_alpha.py`

---

## 1. Observation

Direct code examination and execution within `d:\Finance\code\stock` revealed the following concrete architectural facts:

### 1.1 Baseline Phase 39 Implementation
- **Test Baseline** (`tests/test_phase39_alpha.py`):
  - All 9 unit tests pass in 11.73s when running `pytest` with `$env:BYPASS_TORCH="1"`.
  - Verifies F175 (`MotivicClausenScholzeCoupler`), F176.1 (`compute_phase39_hyperconvex_rank_modulation`, $g_{\text{v39}}(r) = 0.50 + 1.42 \cdot r \cdot \exp(\gamma_{\text{top}} \cdot r^{34})$), and F176.2 (`apply_centaicosagonal_hyperbolic_deadband`, $\alpha = 120.0$, noise leakage $< 10^{-62}$).
  - Confirms strict backward compatibility across versions 36, 37, 38, and 39.

### 1.2 Feature F179 (Geometric Langlands & Non-Abelian Hodge-Deligne Coupler)
- **Implementation in `trading_system/src/ai/ensemble_scorer.py`**:
  - Defined at lines 109–346: `class GeometricLanglandsHodgeDeligneCoupler`.
  - Constructor parameters (lines 120–135):
    - `theta_0 = 0.50`
    - `kappa_deligne = 5.90` (alias `kappa_hodge`)
    - Curvature action coefficients:
      - $\lambda_{\text{deligne}} = 0.52$
      - $\lambda_{\text{langlands}} = 0.28$
      - $\lambda_{\text{hodge}} = 0.20$
      - $\lambda_{\text{hitchin}} = 0.16$
      - $\lambda_{\text{beilinson}} = 0.115$
      - $\lambda_{\text{harmonic}} = 0.075$
      - $\lambda_{\text{bundle}} = 0.045$
      - $\lambda_{\text{regulator}} = 0.024$
      - $\lambda_{\text{cohomology}} = 0.017$
    - Regularization: $\epsilon_{\text{reg}} = 10^{-6}$.
  - Interaction Matrix & Action (lines 243–318):
    - Weight matrix: $\Omega_{j,k} = \frac{1}{|j-k|^{1.22}}$ across 5 canonical pillars (`val`, `mom`, `flow`, `cat`, `net`).
    - Curvature action $A_{\text{hd}}(\Delta)$: high-degree polynomial up to $\Delta^{50}$.
    - Obstruction complex: $E_{\text{hodge}} = \sum_{j < k} \Omega_{j,k} \cdot A_{\text{hd}}(|p_j - p_k|)$.
    - Deligne-Beilinson regulator topological defect:
      $$\text{defect} = |(p_j^2 - p_k^2) + \lambda_{\text{langlands}}(p_j^3 - p_k^3) + \dots + 3 \times 10^{-7}(p_j^{24} - p_k^{24})|$$
    - Deligne invariant: $Z_{\text{deligne}} = \frac{1}{1 + \sum \Omega_{j,k} \cdot \text{defect}}$.
    - Decay factor: $h_{\text{decay}} = \exp(-\kappa_{\text{deligne}} \cdot E_{\text{hodge}})$.
    - Coupling factor: $h_{\text{deligne}} = \text{clip}(h_{\text{decay}} \cdot Z_{\text{deligne}}, \epsilon_{\text{reg}}, 1.0)$.
    - Robustness index: $\text{FERI}_{\text{v40}} = \frac{1}{1 + E_{\text{hodge}} + (1 - Z_{\text{deligne}})}$.
  - Output dictionary keys (lines 330–345):
    `h_deligne`, `z_deligne`, `e_hodge`, `h_decay`, `FERI_v40`, `feri_v40`, `Z_deligne`, `E_hodge`, `h_hodge_deligne`, `h_langlands`, `h_coupling`, `z_invariant`, `e_obstruction`.
  - Exported aliases (lines 348–354):
    `GeometricLanglandsHodgeDeligneFactorCoupler`, `HodgeDeligneCoupler`, `LanglandsDeligneCoupler`, `GeometricLanglandsCoupler`, `HodgeDeligneAnalyticCoupler`, `Phase40Coupler`, `DeligneLanglandsCoupler`.
  - Static bindings on `EnsembleScoringEngine` (lines 17188–17231):
    `compute_geometric_langlands_hodge_deligne_coupling`, `compute_geometric_langlands_coupling`, `compute_hodge_deligne_coupling`, `compute_langlands_deligne_coupling`, `compute_hodge_deligne_analytic_coupling`, `compute_phase40_coupling`.

### 1.3 Feature F180.1 (35th-Order Hyper-Convex Rank Modulation)
- **Definitions in `trading_system/src/ai/factor_suppression.py` & `ensemble_scorer.py`**:
  - Lines 492–519 in `factor_suppression.py` and lines 75–101 in `ensemble_scorer.py`:
    $$g_{\text{v40}}(r) = 0.50 + 1.45 \cdot r \cdot \exp(\gamma_{\text{top}} \cdot r^{35}) \quad (z_{\text{denoised}} \ge 0)$$
    $$g_{\text{neg}}(r) = 1.35 - 1.00 \cdot r \quad (z_{\text{denoised}} < 0)$$
  - Regime-adaptive parameter table `REGIME_GAMMA_TOP_V40` (lines 523–538 in `factor_suppression.py`):
    - `BULL_LOW_VOL`: 4.20
    - `BULL_HIGH_VOL`: 3.90
    - `SIDEWAYS` / `SIDEWAYS_LOW_VOL`: 3.70
    - `SIDEWAYS_HIGH_VOL`: 2.50
    - `BEAR` / `BEAR_LOW_VOL`: 3.40
    - `BEAR_HIGH_VOL`: 2.20
    - `PANIC`: 1.50
    - `CRISIS`: 1.10
    - `RECOVERY`: 4.00
    - Numerical fallbacks: `'2'`: 4.20, `'1'`: 3.70, `'0'`: 3.40. Default: 4.20.
  - Helper: `get_regime_adaptive_gamma_top_v40(regime='BULL_LOW_VOL')` (lines 541–550 in `factor_suppression.py`).

### 1.4 Feature F180.2 (128th-Order Octaconta-tetragonal Hyperbolic Deadband)
- **Definitions in `factor_suppression.py` & `ensemble_scorer.py`**:
  - `apply_octacontatetragonal_hyperbolic_deadband` (lines 454–486 in `factor_suppression.py`, lines 32–64 in `ensemble_scorer.py`):
    $$z_{\text{denoised}} = z \cdot \tanh\left(\left(\frac{|z|}{\delta_{\text{eff}}(z)}\right)^{128}\right)$$
    with $\alpha_{\text{pos}} = 128.0$ and $\delta_{\text{noise}} = 0.035$.
  - In `factor_suppression.py::apply_smooth_deadband_attenuation` (lines 2430–2439):
    ```python
    if version >= 40:
        eff_alpha = 128.0 if alpha_pos in (...) else alpha_pos
        return apply_octacontatetragonal_hyperbolic_deadband(...)
    ```
    Already present and properly routed for `version >= 40`.

### 1.5 Identified Branch Point Gaps
1. **Critical Gap 1: `EnsembleScoringEngine.apply_smooth_noise_deadband`** (`ensemble_scorer.py`, line 19439):
   ```python
   version = int(kwargs.get('version', version))
   if int(version) >= 39:
       eff_alpha = 120.0 if alpha_pos in (...) else alpha_pos
       return apply_centaicosagonal_hyperbolic_deadband(...)
   ```
   **Observation**: The check `if int(version) >= 40:` is missing. If called with `version=40`, it falls into `version >= 39` and erroneously uses the 120th-order centaicosagonal deadband instead of the 128th-order octaconta-tetragonal deadband!
2. **Critical Gap 2: Lazy Attribute Resolution in `factor_suppression.py::__getattr__`** (lines 3407–3900):
   ```
   Traceback (most recent call last):
   ImportError: cannot import name 'GeometricLanglandsHodgeDeligneCoupler' from 'trading_system.src.ai.factor_suppression'
   ```
   **Observation**: When `factor_suppression` is imported before `ensemble_scorer`, accessing Phase 40 coupler classes or functions triggers `__getattr__`, which lacks Phase 40 handlers and raises an `AttributeError`.

---

## 2. Logic Chain

1. **Premise 1 (Mathematical Conviction Scaling)**:
   - For Phase 40, to compress MDD to $\le -0.00004\%$ and increase Sharpe to $\ge 27.35$, the alpha pipeline requires extreme separation between genuine alpha and random noise.
   - The 35th-order exponent $r^{35}$ in $g_{\text{v40}}(r)$ keeps the bottom 70% of distribution virtually linear and modest ($g(0.70) \approx 1.515$), while exploding the top percentile ($r=1.0$) to $0.50 + 1.45 \cdot e^{4.20} \approx 97.195$.
   - The 128th-order deadband exponent suppresses noise below $|z| \le 0.0004$ to $< 10^{-68}$, eradicating micro-noise churn while transmitting 100.000% of signals with $|z| \ge 0.150$.

2. **Premise 2 (Factor Disentanglement via Geometric Langlands)**:
   - The 5 canonical pillars (`val`, `mom`, `flow`, `cat`, `net`) can suffer from localized factor collapse during sudden regime shifts.
   - $E_{\text{hodge}}$ measures curvature misalignment across pillars. When all 5 pillars agree, $E_{\text{hodge}} = 0$, $Z_{\text{deligne}} = 1.0$, and $h_{\text{deligne}} = 1.0$.
   - In `combine_predictions` (lines 14083–14116), the harmony factor injects:
     $$+ (2.05 \cdot h_{\text{deligne}} \cdot Z_{\text{deligne}} \text{ if version} \ge 40 \text{ else } 0.0)$$
     This guarantees higher confluence weighting for names exhibiting geometric harmonic alignment across all 5 economic pillars.

3. **Premise 3 (Backward Compatibility & Robust Dispatch)**:
   - Phase 1~39 execution must remain 100% byte-identical and regression-free.
   - For `EnsembleScoringEngine.apply_smooth_noise_deadband`, inserting `if int(version) >= 40:` immediately before `elif int(version) >= 39:` preserves existing behaviour for all $V \le 39$.
   - Adding Phase 40 symbols to `factor_suppression.py::__getattr__` prevents import-order fragility between `factor_suppression` and `ensemble_scorer`.

---

## 3. Caveats

1. **PyTorch DLL Access Violation on Windows**:
   - In the Windows Python 3.11 environment, importing `trading_system.src` without `BYPASS_TORCH=1` triggers an unhandled memory access violation in `torch._load_dll_libraries`.
   - All pytest runs must prepend `$env:BYPASS_TORCH="1"`.
2. **File Size of `ensemble_scorer.py`**:
   - `ensemble_scorer.py` exceeds 19,800 lines (~1.02 MB). Text searches via standard ripgrep without explicit includes or path scope can skip lines due to size limits. Direct targeted line slice viewing or scoped ripgrep must be used.
3. **Scope Discipline**:
   - As an explorer, no changes have been applied to production files (`ensemble_scorer.py` or `factor_suppression.py`). All proposed modifications are formally detailed in Section 4.

---

## 4. Conclusion & Implementation Blueprint

### 4.1 Required Fix 1: `EnsembleScoringEngine.apply_smooth_noise_deadband`
**File**: `trading_system/src/ai/ensemble_scorer.py`  
**Target Location**: Around line 19439  
**Modification**: Prepend the `version >= 40` branch:

```python
        version = int(kwargs.get('version', version))
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
        elif int(version) >= 39:
            eff_alpha = 120.0 if alpha_pos in (3.0, 5.0, 7.0, 9.0, 10.0, 12.0, 14.0, 16.0, 20.0, 24.0, 28.0, 32.0, 36.0, 40.0, 44.0, 48.0, 52.0, 56.0, 60.0, 64.0, 68.0, 72.0, 76.0, 80.0, 84.0, 88.0, 92.0, 96.0, 100.0, 104.0, 108.0, 112.0, 116.0) else alpha_pos
            return apply_centaicosagonal_hyperbolic_deadband(
                scores_centered=scores_centered,
                delta_noise=delta_noise,
                delta_neg=delta_neg,
                alpha_pos=eff_alpha,
                alpha_neg=alpha_neg,
                regime=regime
            )
```

### 4.2 Required Fix 2: Lazy Attribute Resolution in `factor_suppression.py`
**File**: `trading_system/src/ai/factor_suppression.py`  
**Target Location**: Inside `def __getattr__(name: str) -> Any:` (before `raise AttributeError`)  
**Modification**: Add Phase 40 attribute dispatch:

```python
    # Phase 40 (R1, Feature F179 & F180)
    if name in (
        'GeometricLanglandsHodgeDeligneCoupler',
        'GeometricLanglandsHodgeDeligneFactorCoupler',
        'HodgeDeligneCoupler',
        'LanglandsDeligneCoupler',
        'GeometricLanglandsCoupler',
        'HodgeDeligneAnalyticCoupler',
        'Phase40Coupler',
        'DeligneLanglandsCoupler',
    ):
        from .ensemble_scorer import GeometricLanglandsHodgeDeligneCoupler as _GLHDC
        return _GLHDC
    if name in (
        'compute_geometric_langlands_hodge_deligne_coupling',
        'compute_geometric_langlands_coupling',
        'compute_hodge_deligne_coupling',
        'compute_langlands_deligne_coupling',
        'compute_hodge_deligne_analytic_coupling',
        'compute_phase40_coupling',
    ):
        from .ensemble_scorer import GeometricLanglandsHodgeDeligneCoupler as _GLHDC
        return _GLHDC.compute
    if name in ('apply_octacontatetragonal_hyperbolic_deadband', 'compute_phase40_deadband', 'apply_phase40_deadband', 'apply_octaconta_hyperbolic_deadband'):
        return apply_octacontatetragonal_hyperbolic_deadband
    if name in ('compute_phase40_hyperconvex_rank_modulation', 'compute_phase40_rank_warping'):
        return compute_phase40_hyperconvex_rank_modulation
    if name in ('REGIME_GAMMA_TOP_V40', 'get_regime_adaptive_gamma_top_v40'):
        return globals()[name]
```

### 4.3 Test Suite Specification: `tests/test_phase40_alpha.py`
The comprehensive test suite must be placed in `tests/test_phase40_alpha.py` containing 9 discrete validation scenarios:

1. `test_feature_f179_geometric_langlands_hodge_deligne_coupler_properties`:
   - Validates 5 canonical pillars input (`pd.DataFrame`).
   - Asserts dictionary keys: `h_deligne`, `z_deligne`, `e_hodge`, `FERI_v40`, `Z_deligne`, `E_hodge`, `h_langlands`.
   - Asserts bounded range $[0.0, 1.0]$.
   - Asserts dispersion monotonicity ($E_{\text{hodge}}$ strictly increases and $h_{\text{deligne}}$ strictly decreases with greater cross-pillar divergence).
   - Validates 1D vector shape `(5,)` evaluation.
2. `test_feature_f179_langlands_deligne_aliases_and_exports`:
   - Asserts class identity across all 7 alias symbols (`GeometricLanglandsCoupler`, `HodgeDeligneCoupler`, etc.).
   - Asserts classmethod `compute_geometric_langlands_hodge_deligne_coupling` on `EnsembleScoringEngine`.
3. `test_feature_f180_1_35th_order_rank_modulation_convexity`:
   - Tests base value $g_{\text{v40}}(0.0) = 0.50$.
   - Tests top value $g_{\text{v40}}(1.0) = 0.50 + 1.45 \cdot e^{4.20} \approx 97.195$ (within $10^{-4}$).
   - Verifies strict monotonicity ($\Delta g \ge 0$).
   - Verifies subdued conviction at median/top-30% ($g(0.70) < 1.55$).
   - Tests negative branch: $z < 0 \implies g(0) = 1.35, g(1) = 0.35$, monotonically decreasing.
4. `test_feature_f180_1_regime_adaptive_gamma_top`:
   - Verifies all regime mappings: `BULL_LOW_VOL`: 4.20, `BULL_HIGH_VOL`: 3.90, `SIDEWAYS`: 3.70, `BEAR`: 3.40, `CRISIS`: 1.10.
5. `test_feature_f180_2_128th_order_hyperbolic_deadband_leakage`:
   - Verifies noise suppression for $|z| \le 0.0004$: leakage strictly $< 10^{-68}$.
   - Verifies 100.000% signal transmission for $|z| \ge 0.15$: relative tolerance $< 10^{-9}$.
   - Verifies strict monotonicity across 1,001 points in $[-0.5, 0.5]$.
6. `test_feature_f180_2_factor_suppression_delegation`:
   - Tests scalar evaluation and `pd.Series` evaluation.
7. `test_ensemble_scorer_apply_smooth_noise_deadband_version_40`:
   - Verifies `EnsembleScoringEngine.apply_smooth_noise_deadband(..., version=40)` routes to 128th-order deadband with leakage $< 10^{-68}$.
8. `test_combine_predictions_version_40_confluence_and_harmony`:
   - Generates mock scores for 10 symbols.
   - Evaluates `combine_predictions(..., version=39)` and `combine_predictions(..., version=40)`.
   - Asserts non-empty, finite, valid $[0.0, 1.0]$ bounds.
   - Verifies top conviction in v40 is greater than or equal to v39 ($\text{top}_{\text{v40}} \ge \text{top}_{\text{v39}} - 10^{-6}$).
9. `test_strict_backward_compatibility_v39_and_prior`:
   - Verifies deadband leakages for versions 40 ($< 10^{-68}$), 39 ($< 10^{-62}$), 38 ($< 10^{-60}$), 37 ($< 10^{-60}$).

---

## 5. Verification Method

To independently reproduce and verify the findings:

1. **Verify Baseline Phase 39 Tests**:
   ```powershell
   $env:BYPASS_TORCH="1"
   python -m pytest tests/test_phase39_alpha.py -v
   ```
   *Expected Result*: 9 passed in ~12 seconds.

2. **Verify Coupler Classes & Static Bindings**:
   ```powershell
   python -c "from trading_system.src.ai.ensemble_scorer import GeometricLanglandsHodgeDeligneCoupler, EnsembleScoringEngine; print(GeometricLanglandsHodgeDeligneCoupler, hasattr(EnsembleScoringEngine, 'compute_geometric_langlands_hodge_deligne_coupling'))"
   ```
   *Expected Result*: `<class '...GeometricLanglandsHodgeDeligneCoupler'> True`.

3. **Verify Deadband Leakage and Order**:
   ```powershell
   python -c "import numpy as np; from trading_system.src.ai.factor_suppression import apply_octacontatetragonal_hyperbolic_deadband; z = np.array([0.0004]); out = apply_octacontatetragonal_hyperbolic_deadband(z); print('Leakage:', out[0], 'Suppressed < 1e-68:', abs(out[0]) < 1e-68)"
   ```
   *Expected Result*: Leakage suppressed $< 10^{-68}$ is `True`.

4. **Verify Rank Modulation Top Value**:
   ```powershell
   python -c "import math; from trading_system.src.ai.factor_suppression import compute_phase40_hyperconvex_rank_modulation; top = compute_phase40_hyperconvex_rank_modulation(1.0, gamma_top=4.20); expected = 0.50 + 1.45 * math.exp(4.20); print(f'Top: {top:.4f}, Expected: {expected:.4f}')"
   ```
   *Expected Result*: `Top: 97.1952, Expected: 97.1952`.

5. **Verify Version 40 Execution Post-Fix**:
   Once Fix 1 and Fix 2 are applied by the implementer, run:
   ```powershell
   $env:BYPASS_TORCH="1"
   python -m pytest tests/test_phase40_alpha.py -v
   ```
   *Expected Result*: 9 passed, 0 failures, 0 regressions.
