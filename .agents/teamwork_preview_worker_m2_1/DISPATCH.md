# DISPATCH: Worker M2 — Risk Allocation Specialist (Risk Engineer)

## Working Directory
d:\Finance\code\stock\.agents\teamwork_preview_worker_m2_1

## Role & Mission
You are the Risk Allocation Specialist (Risk Engineer) for Phase 55 Quantitative Alpha Enhancement.
Your mission is to implement Features F248.1 and F248.2 in `unified_portfolio_allocator.py` and `portfolio_allocator.py`, create `tests/test_phase55_risk.py`, and verify test pass.

## Mandatory Reading
1. `d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md` (Header: `## 2026-09-18T03:36:46Z`)
2. `d:\Finance\code\stock\.agents\teamwork_preview_explorer_survey_2\survey_report.md`
3. `d:\Finance\code\stock\.agents\teamwork_preview_explorer_survey_2\handoff.md`

## Exclusive Write Ownership
- `trading_system/src/risk/unified_portfolio_allocator.py`
- `trading_system/src/risk/portfolio_allocator.py`
- `tests/test_phase55_risk.py`
Do NOT edit any other files.

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Technical Requirements
1. **F248.1: Higher-Homology-5 Fisher-Rao Barycenter on Riemannian Probability Simplex (`unified_portfolio_allocator.py` & `portfolio_allocator.py`)**:
   - Implement `compute_fisher_rao_barycenter_lmbwdh5`:
     Metric curvature vector $\mu_{\text{lmbwdh5}} = [4.50, 3.25, 3.20, 5.05]$ across [Black-Litterman, HERC, Risk Parity, EVT-CVaR].
     Simplex conservation: strictly enforce $\sum q_i = 1.0, q_i \ge 0$.
   - Export 19 delegated method aliases on `UnifiedPortfolioAllocator` and `PortfolioAllocator`:
     `compute_fisher_rao_barycenter_lmbwdh5`, `compute_higher_homology_5_barycenter`, `compute_phase55_barycenter`, `lmbwdh5_barycenter`, `higher_homology_5_fisher_rao_blend`, `fisher_rao_higher_homology_5`, `barycenter_lmbwdh5`, `blend_weights_lmbwdh5`, `riemannian_higher_homology_5_barycenter`, `lmbwd_h5_barycenter`, `phase55_fisher_rao_barycenter`, `drinfeld_higher_homology_5_barycenter`, `borcherds_higher_homology_5_barycenter`, `monster_higher_homology_5_barycenter`, `whittaker_higher_homology_5_barycenter`, `moonshine_higher_homology_5_barycenter`, `lurie_higher_homology_5_barycenter`, `higher_homology_5_blend`, `phase55_homology_barycenter`.
   - Update `calculate_weights` and `compute_information_theoretic_blend_weights` in `unified_portfolio_allocator.py` under `version >= 55` to select Higher-Homology-5 barycenter.

2. **F248.2: 51st-Cumulant Expansion Trans-Singular EVaR Tail Risk Measure (`unified_portfolio_allocator.py` & `portfolio_allocator.py`)**:
   - Implement `calculate_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_evar_51st_cumulant`:
     Order = 51, $51! \approx 1.55112 \times 10^{66}$, $\xi_{\text{monster}} = 0.9999999999$.
     Bounding catastrophic downside risk under Student-t and heavy-tailed shocks.
   - Export 18 method aliases on both classes:
     `calculate_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_evar_51st_cumulant`, `compute_51st_cumulant_evar`, `compute_phase55_evar`, `evar_51st_cumulant`, `trans_singular_51st_cumulant_evar`, `eternal_omni_cosmic_51st_cumulant_evar`, `supreme_transcendent_evar_51`, `phase55_tail_risk_evar`, `calculate_phase55_evar_tail_risk`, `cumulant_51_evar_bound`, `trans_singular_evar_v55`, `transcendent_51st_cumulant_evar`, `infinite_supreme_51st_cumulant_evar`, `omni_cosmic_evar_51`, `monster_51st_cumulant_evar`, `higher_homology_5_evar`, `drinfeld_51st_cumulant_evar`, `phase55_evar_bound`.
   - Integrate ambiguity tilting in `calculate_weights` under `version >= 55`:
     $\epsilon_w = 0.550, \alpha_{\text{iep}} = 3.25$
     Regime shifts: $\delta_{\text{bl}} = -10.50, \delta_{\text{herc}} = +6.75, \delta_{\text{rp}} = -11.00, \delta_{\text{cvar}} = +15.70$
     Contagion damping: $\max(0.0, 1.0 - 10.0 \cdot \lambda_{\text{casc}})$.

3. **Testing & Verification**:
   - Create `tests/test_phase55_risk.py` following the 9 test specifications from Survey Explorer 2's report.
   - Execute:
     `.venv\Scripts\python.exe -m pytest tests/test_phase55_risk.py -v`
     `.venv\Scripts\python.exe -m pytest tests/test_phase54_risk.py -v`
   - Confirm 100% test pass and zero regressions.

4. **Deliverables**:
   - Document changes in `d:\Finance\code\stock\.agents\teamwork_preview_worker_m2_1\handoff.md`.
   - Report back with `send_message`.

## 2026-09-18T03:55:38Z
You are the Risk Allocation Specialist (Risk Engineer) for Phase 55. Your working directory is d:\Finance\code\stock\.agents\teamwork_preview_worker_m2_1.
Read your dispatch instructions in d:\Finance\code\stock\.agents\teamwork_preview_worker_m2_1\DISPATCH.md, the original request in d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md (header ## 2026-09-18T03:36:46Z), and Explorer 2's survey reports in d:\Finance\code\stock\.agents\teamwork_preview_explorer_survey_2\survey_report.md and handoff.md.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Implement Features F248.1 and F248.2 in trading_system/src/risk/unified_portfolio_allocator.py and trading_system/src/risk/portfolio_allocator.py with strict version >= 55 gating.
Create tests/test_phase55_risk.py.
Run the test suites:
.venv\Scripts\python.exe -m pytest tests/test_phase55_risk.py -v
.venv\Scripts\python.exe -m pytest tests/test_phase54_risk.py -v
Write your handoff.md and send a completion message with send_message.
