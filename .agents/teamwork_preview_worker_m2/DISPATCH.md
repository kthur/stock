## 2026-09-20T13:04:17Z

# DISPATCH: Milestone M2 Worker (Portfolio Risk Allocation & 59th-Cumulant EVaR Tail Budgeting)

## Working Directory
d:\Finance\code\stock\.agents\teamwork_preview_worker_m2

## Exclusive File Ownership
You EXCLUSIVELY own and may modify:
- `src/risk/unified_portfolio_allocator.py`
- `src/risk/portfolio_allocator.py`
- `tests/test_phase63_risk.py`
DO NOT modify any files outside this exclusive list.

## Authoritative Inputs
- `d:\Finance\code\stock\ORIGINAL_REQUEST.md` (Read this first)
- Explorer 2 Handoff Report: `d:\Finance\code\stock\.agents\teamwork_preview_explorer_survey_risk_2\handoff.md` (Contains exact code, lines, formulas, and blueprint)

## Objectives & Detailed Tasks
1. `src/risk/unified_portfolio_allocator.py`:
   - Implement `compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_13_fisher_rao_barycenter_blend` with $\mu_{\text{lmbwdh13}} = [5.30, 3.65, 3.60, 5.85]$ across BL, HERC, RP, EVT-CVaR, simplex conservation ($\sum q_i = 1.0, q_i > 0$), and all 37 aliases on `UnifiedPortfolioAllocator`.
   - Implement `compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_13_evar_risk_measure` with order 59, $\xi_{\text{monster}} = 0.9999999999999$, $59! \approx 1.38683 \times 10^{80}$, and all 37 aliases on `UnifiedPortfolioAllocator`.
   - In `compute_information_theoretic_blend_weights`:
     - Add `is_phase63 = int(version) >= 63` and update `is_phase62 = (int(version) >= 62) or is_phase63`.
     - Implement Phase 63 ambiguity tilting: $\epsilon_w = 0.630$, $\alpha_{\text{iep}} = 3.65$, regime shifts ($\delta_{\text{bl}} = -12.50\epsilon_w - 6.60 u_H^2$, $\delta_{\text{herc}} = +8.75\epsilon_w + 5.50 u_H$, $\delta_{\text{rp}} = -13.00\epsilon_w$, $\delta_{\text{cvar}} = +19.00\epsilon_w + 8.25 c_{\text{crisis}}$), contagion damping $\max(0.0, 1.0 - 14.0\lambda_{\text{casc}})$, and scaling $(1.0 + 0.31\alpha_{\text{iep}})$.
     - Post-softmax refinement: if `is_phase63`, invoke `compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_13_fisher_rao_barycenter_blend`.
2. `src/risk/portfolio_allocator.py`:
   - Add static delegation method for Higher-Homology-13 barycenter blend and all 37 aliases.
   - Add static delegation method for 59th-cumulant EVaR and all 37 aliases.
3. Create `tests/test_phase63_risk.py` (mirrored from `tests/test_phase62_risk.py` with 8 comprehensive test cases).
4. Run build/tests:
   ```powershell
   .venv\Scripts\pytest.exe tests/test_phase63_risk.py tests/test_phase62_risk.py -v
   ```
   Ensure 100% pass rate.

## MANDATORY INTEGRITY WARNING
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Deliverable
Write a complete, self-contained `handoff.md` in your working directory summarizing:
- Exact changes made
- Test execution output
- Verification results
When complete, send a message back to parent.
