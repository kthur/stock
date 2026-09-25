# DISPATCH: Milestone 2 — Risk Allocation Specialist

## Working Directory
`d:\Finance\code\stock\.agents\teamwork_preview_worker_m2_risk`

## Authoritative User Request
`d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md` (Header `## 2026-09-15T21:55:02Z`)

## Architectural Reference
`d:\Finance\code\stock\.agents\teamwork_preview_explorer_survey_2\handoff.md`

## Files Exclusively Owned
- `trading_system/src/risk/unified_portfolio_allocator.py`
- `trading_system/src/risk/portfolio_allocator.py`
- `tests/test_phase45_risk.py`

## Mandate & Detailed Requirements (F201.1)
1. **`unified_portfolio_allocator.py`**:
   - Implement `compute_lurie_kac_moody_whittaker_fisher_rao_barycenter_blend(self, model_weights, max_iter=50, tol=1e-6, step_size=0.50)` with metric weights $\mu_{\text{lkmw}} = [3.50, 2.70, 2.65, 4.05]$ for `["bl", "herc", "rp", "cvar"]`.
   - Implement Riemannian exponential map iteration and 3-simplex projection.
   - Define all 15 aliases as detailed in `handoff.md` Section 4.1.
   - Implement `compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_evar_risk_measure(self, returns, alpha=0.05, t_grid=None, ..., xi_km=0.9999998, xi_kac_moody=0.9999998, xi_41=None, **kwargs)` with $41! \approx 3.34525 \times 10^{49}$ (`33452526613163807108170062053440751665152000000000.0`), moment $m_{41} = \mathbb{E}[(r - \mu)^{41}]$, cumulant term $\xi_{\text{km}} \cdot \frac{m_{41}}{41!} \cdot t^{41}$, and monotonic lower bound `max(best_ts, trans_vir_val)`.
   - Define all 22 aliases for EVaR.
   - In `compute_information_theoretic_blend_weights`:
     - Add `is_phase45 = int(version) >= 45`.
     - In ambiguity tilting: $\epsilon_w = 0.475$, $\delta_{\text{kac\_moody\_whittaker}} = \{\text{bl}: -8.70 \epsilon_w - 4.60 u_H^2, \text{herc}: +5.00 \epsilon_w + 3.50 u_H, \text{rp}: -9.20 \epsilon_w, \text{cvar}: +12.60 \epsilon_w + 5.30 c_{\text{crisis}}\}$.
     - Hyper-information entropy parity: $\alpha_{\text{iep}} = 2.60$, $\text{contagion\_damp} = \max(0, 1 - 7.4 \lambda_{\text{casc}})$.
     - Cascade tilting: $\delta_{\text{rvine}}$ with weights $\text{bl}: -7.20, \text{herc}: +3.70, \text{rp}: -7.60, \text{cvar}: +10.80$.
     - At exit: if `is_phase45`, call `compute_lurie_kac_moody_whittaker_fisher_rao_barycenter_blend(res_weights)`.

2. **`portfolio_allocator.py`**:
   - Add `@staticmethod compute_lurie_kac_moody_whittaker_fisher_rao_barycenter_blend` delegating to `UnifiedPortfolioAllocator` + all aliases.
   - Add `@staticmethod compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_evar_risk_measure` delegating to `UnifiedPortfolioAllocator` with losses fallback, parameter resolution + all aliases.

3. **`tests/test_phase45_risk.py`**:
   - Implement 7 tests as specified in `handoff.md` Section 4.1.
   - Run: `python -m pytest tests/test_phase45_risk.py -v` and `python -m pytest tests/test_phase44_risk.py -q`.
   - Ensure 100% pass rate and zero regressions.

## Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## 2026-09-25T15:19:54Z
You are the Risk Specialist Worker for Phase 67 Quantitative Alpha Enhancement.
Read the authoritative user request at:
d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md (specifically lines 2115-2219).

Also consult the survey findings in:
`d:\Finance\code\stock\.agents\teamwork_preview_explorer_survey_1\survey_alpha_risk.md`

Your working directory is:
`d:\Finance\code\stock\.agents\teamwork_preview_worker_m2_risk`

EXCLUSIVE FILE OWNERSHIP (Only you may modify these files):
- `trading_system/src/risk/unified_portfolio_allocator.py`
- `trading_system/src/risk/portfolio_allocator.py`

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

REQUIREMENTS:
1. Higher-Homology-17 Fisher-Rao barycenter μ:
   - Advance μ from `[5.60, 3.80, 3.55, 6.25]` to `[5.70, 3.85, 3.50, 6.40]`.
   - Maintain strict ordering: CVaR > BL > HERC > RP and simplex sum=1.0 (rel_tol=1e-5).
2. EVaR Cumulant:
   - Advance from 64th-cumulant (64! ≈ 1.27e89) to 66th-cumulant (66! ≈ 5.44e92).
   - Advance ξ_monster from 0.99999999999997 to 0.99999999999998.
   - Update regime shifts:
     * eps_w = 0.670
     * delta_bl = -14.00
     * delta_herc = +10.00
     * delta_rp = -14.50
     * delta_cvar = +21.50 + 9.50 * c
     * alpha_iep = 3.85
     * contagion_damp = 16.0
   - Full alias trees for all new functions/classes and `is_phase67` gating. Maintain backward compatibility for Phase 50~66.

VERIFICATION:
Execute tests using the project virtual environment:
`d:\Finance\code\stock\trading_system\.venv\Scripts\python.exe -m pytest tests/test_phase66_risk.py`
Verify imports and syntax of `unified_portfolio_allocator.py` and `portfolio_allocator.py`.

Write your completion report and test verification logs to:
`d:\Finance\code\stock\.agents\teamwork_preview_worker_m2_risk\handoff.md`
Then send a completion message to parent.
