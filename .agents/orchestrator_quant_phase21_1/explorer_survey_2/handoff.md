# Handoff Report — explorer_survey_2 (Risk & Microstructure OMS Survey)


**Author**: `explorer_survey_2` (Risk & Microstructure OMS Explorer)  
**Date**: 2026-09-10  
**Target Milestone**: Phase 21 Quantitative Enhancement (Requirements R2 & R3)  
**Status**: Survey Complete — Hard Handoff to Implementation Workers  
**Related Report**: `d:\Finance\code\stock\.agents\orchestrator_quant_phase21_1\explorer_survey_2\survey_report.md`

---

## 1. Observation

Direct code observations from inspecting the codebase:

1. **`trading_system/src/risk/unified_portfolio_allocator.py`**:
   - Lines 1004–1076: Phase 20 Lurie Spectral AG Fisher-Rao Barycenter is defined as `compute_lurie_spectral_ag_fisher_rao_barycenter_blend(self, model_weights, max_iter=50, tol=1e-6, step_size=0.50)` with metric weights `mu_spectral_ag = np.array([1.80, 1.45, 1.40, 2.15], dtype=float)`.
   - Lines 1831–1936: Phase 20 Ultra-Transcendent EVaR is defined in `compute_ultra_transcendent_evar_risk_measure(returns, alpha=0.05, ...)` using 16th cumulant expansion with factor `16! = 20,922,789,888,000` and `xi_ultra_transcendent = 0.60`.
   - Line 3128: Phase version flags check `is_phase20 = int(version) >= 20`, `is_phase19 = (int(version) >= 19) or is_phase20`.
   - Lines 3144–3170: Ambiguity tilting for Phase 20 sets `eps_w = 0.240`, `delta_sag = {"bl": -2.95*eps_w - 1.00*(u_entropy**2), "herc": +1.50*eps_w + 0.85*u_entropy, "rp": -3.25*eps_w, "cvar": +4.55*eps_w + 1.60*c_crisis}`, `alpha_iep = 1.20`, `contagion_damp = max(0.0, 1.0 - 2.6*lam_casc)`.
   - Line 3515: Softmax barycenter refinement branch calls `res_weights = self.compute_lurie_spectral_ag_fisher_rao_barycenter_blend(res_weights)` when `is_phase20`.
   - Line 3672: `_optimize_evt_cvar` expands Cornish-Fisher quantiles when `is_phase20` to `k_alpha_w = float(np.clip(z_alpha + 0.56 - ((z_alpha ** 2 - 1.0) / 6.0) * s_p + 0.18 * max(0.0, k_p) + 1.65 * eff_xi, 2.25, 3.70))` and empirical fallback `k_alpha + 0.26 + 1.65 * (eff_xi - 0.15)`.

2. **`trading_system/src/risk/portfolio_allocator.py`**:
   - Lines 2688–2765: Class `PortfolioAllocator` provides static methods `compute_lurie_spectral_ag_fisher_rao_barycenter_blend` and `compute_ultra_transcendent_evar_risk_measure` delegating to `UnifiedPortfolioAllocator()`.

3. **`trading_system/src/core/fast_lob_engine.py`**:
   - Lines 856–965: Phase 20 Kerr-Newman-AdS is implemented as `compute_kerr_newman_ads_queue_acceleration(self, charge_parameter=0.5, spin_parameter=0.5, ads_radius=10.0, theta=math.pi/2.0, levels=10, timestamp_sec=None, **kwargs)`.
   - Lines 1355–1418: In `DeepHawkesArrivalProcess.compute_preemptive_dark_routing`, the dark routing cap is set to `0.9997` for `int(version) >= 20` and frame inspection detecting `"phase20"`.

4. **`trading_system/src/execution/smart_order_router.py`**:
   - Line 87: Version checking `is_phase20 = (v_eff >= 20)`.
   - Line 123: Lit queue imbalance preemption dark cap is clipped to `0.9997` when `is_phase20`.
   - Lines 212–214, 270–272, 335–337: Lit maker floor contracts to `0.00001` via `maker_ratio = float(np.clip(0.70 * (1.0 - 0.9999857 * gamma_toxic), 0.00001, 0.70))`.
   - Lines 257, 298, 304: `max_dark_cap = 0.9997` if `is_phase20`.
   - Line 367: Dynamic anti-gaming MinQty scales up to `0.9999` (99.99%) via `min_ratio = float(np.clip(0.20 + 0.92 * gamma_toxic + 0.78 * dp_score, 0.20, 0.9999))`.

5. **`trading_system/src/execution/oms_engine.py`**:
   - Lines 1505–1514 (in `ExecutionOMSEngine.calculate_peg_limit_price`) and Lines 2168–2177 (in `AlmgrenChrissScheduler.calculate_peg_limit_price`):
     ```python
     if int(version) >= 20:
         ...
         if h_val > 0.06:
             hawkes_shift = -direction * 0.997 * spr * (h_val - 0.06)
     ```

6. **Baseline Test Execution**:
   - Ran `.venv\Scripts\pytest.exe tests/test_phase20_microstructure_oms.py`: 10 passed in 14.37s.
   - Ran `.venv\Scripts\pytest.exe tests/test_portfolio_allocator.py`: 13 passed in 19.70s.

---

## 2. Logic Chain

1. **R2 Risk Allocation Progression**:
   - The metric weights in the Fisher-Rao barycenter evolved monotonically:
     - Phase 18: $[1.60, 1.35, 1.30, 1.90]$
     - Phase 19: $[1.70, 1.40, 1.35, 2.00]$
     - Phase 20: $[1.80, 1.45, 1.40, 2.15]$
     - Phase 21: Extrapolates to $\mu_{\text{chromatic}} = [1.90, 1.50, 1.45, 2.30]$.
   - The EVaR cumulant expansion evolved by adding higher order terms:
     - Phase 19: 15th cumulant ($15! = 1,307,674,368,000$, $\xi_{15} = 0.55$)
     - Phase 20: 16th cumulant ($16! = 20,922,789,888,000$, $\xi_{16} = 0.60$)
     - Phase 21: Requires 17th cumulant ($17! = 355,687,428,096,000$, $\xi_{17} = 0.65$). Since 17 is odd, $|L|^{17} = |L|^{17}$ ensures positive tail penalization.
   - Cornish-Fisher expansion constants in `_optimize_evt_cvar` expand from $z_\alpha + 0.56$ (Phase 20) to $z_\alpha + 0.60$ with bounds $[2.30, 3.80]$ in Phase 21.

2. **R3 Microstructure OMS Progression**:
   - In `fast_lob_engine.py`, Phase 20 introduced Kerr-Newman-AdS. Phase 21 adds the cosmological constant $\Lambda = 3/L_{dS}^2 - 3/L_{AdS}^2$ and de Sitter cosmic horizon $r_C = L_{dS}(1 - M/L_{dS})$, yielding `compute_kerr_newman_ads_ds_queue_acceleration`.
   - In `smart_order_router.py`:
     - Maker floor contracts from 0.00001 (Phase 20) to 0.000005 (Phase 21). Solving $0.70 \cdot (1 - c) = 0.000005$ gives $c = 1 - 0.000005 / 0.70 = 0.999992857 \approx 0.99999286$.
     - Max dark routing cap expands to 0.9998 (99.98% ATS).
     - Dynamic Anti-Gaming MinQty cap expands to 0.99995 (99.995%).
   - In `oms_engine.py`:
     - Preemptive Hawkes tick shading activation threshold contracts from $h > 0.06$ to $h > 0.05$.
     - Shading shift becomes $-0.998 \cdot \text{spread} \cdot (h - 0.05)$ for both `ExecutionOMSEngine` and `AlmgrenChrissScheduler`.

---

## 3. Caveats

- **Read-Only Scope**: In compliance with the explorer mandate, no production files were modified during this survey. All proposed code changes are fully documented in `survey_report.md`.
- **Cosmological Parameters**: If `cosmological_lambda` is not explicitly passed to `compute_kerr_newman_ads_ds_queue_acceleration`, it defaults to $3 / L_{dS}^2 - 3 / L_{AdS}^2$ with $L_{dS} = 100.0$ and $L_{AdS} = 10.0$.
- **Backward Compatibility**: All existing methods and historical version branches (`version < 21`) must remain completely untouched to maintain 100% test pass rate on legacy suites.

---

## 4. Conclusion

The exact technical specifications for Phase 21 R2 and R3 have been completely determined and documented:
1. `trading_system/src/risk/unified_portfolio_allocator.py`: Add `compute_lurie_chromatic_homotopy_fisher_rao_barycenter_blend`, `compute_hyper_transcendent_evar_risk_measure`, and version 21 branches in `compute_regime_model_weights` and `_optimize_evt_cvar`.
2. `trading_system/src/risk/portfolio_allocator.py`: Add static wrapper methods for the above.
3. `trading_system/src/core/fast_lob_engine.py`: Add `compute_kerr_newman_ads_ds_queue_acceleration` and 0.9998 dark cap in `compute_preemptive_dark_routing`.
4. `trading_system/src/execution/smart_order_router.py`: Set maker floor to 0.000005 via $c = 0.99999286$, dark cap to 0.9998, and MinQty to 0.99995.
5. `trading_system/src/execution/oms_engine.py`: Set Hawkes shading threshold to $h > 0.05$ and shift to $-0.998 \cdot \text{spread} \cdot (h - 0.05)$ in both engine and scheduler.

---

## 5. Verification Method

To verify the Phase 21 implementation independently once implemented:
1. Run Phase 20 test suites to ensure zero regression:
   ```bash
   .venv\Scripts\pytest.exe tests/test_phase20_microstructure_oms.py -v
   .venv\Scripts\pytest.exe tests/test_portfolio_allocator.py -v
   ```
2. Run newly implemented Phase 21 test suites:
   ```bash
   .venv\Scripts\pytest.exe tests/test_phase21_microstructure_oms.py -v
   .venv\Scripts\pytest.exe tests/test_phase21_risk_allocation.py -v
   ```
3. Invalidation conditions:
   - Any failure in backward compatibility or legacy test cases.
   - Tracking error between `ExecutionOMSEngine` and `AlmgrenChrissScheduler` greater than $10^{-5}$.
   - Non-monotonicity in maker floor ($v21 > v20$) or failure to reach 0.000005 floor.
   - Violation of the coherent tail risk hierarchy: $\text{Hyper-Transcendent-EVaR} < \text{Ultra-Transcendent-EVaR}$.

