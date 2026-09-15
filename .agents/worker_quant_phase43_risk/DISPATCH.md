# DISPATCH: Worker 2 (Risk Allocation Specialist)

## Working Directory
d:\Finance\code\stock\.agents\worker_quant_phase43_risk

## Authoritative User Request
d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md (Header: ## 2026-09-15T06:20:40Z)

## Technical Blueprint & Survey Report
Read and strictly follow:
`d:\Finance\code\stock\.agents\explorer_quant_phase43_survey2\handoff.md`

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Exclusive File Ownership
- `trading_system/src/risk/unified_portfolio_allocator.py`
- `trading_system/src/risk/portfolio_allocator.py`
- `tests/test_phase43_risk.py`

## Implementation Directives (Milestone R2)
1. In `trading_system/src/risk/unified_portfolio_allocator.py`:
   - Implement `compute_lurie_w_algebra_fisher_rao_barycenter_blend` (F193.1) with $\mu_{\text{lwa}} = [3.30, 2.60, 2.55, 3.85]$ and its 12 aliases.
   - Implement `compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_evar_risk_measure` (39th-cumulant expansion, $39! \approx 2.040 \times 10^{46}$, $\xi_{\text{w\_alg}} = 0.999999$) with monotonic bounding $\max(\text{best\_ts}, \text{trans\_beilinson\_val})$ and its 22 aliases.
   - Update `compute_information_theoretic_blend_weights` with `is_phase43 = int(version) >= 43`, $\epsilon_w = 0.465$, $\Delta_{\text{w\_algebra}}$, $\alpha_{\text{iep}} = 2.50$, R-Vine tilting, and post-refinement call to `compute_lurie_w_algebra_fisher_rao_barycenter_blend`.

2. In `trading_system/src/risk/portfolio_allocator.py`:
   - Implement static method `compute_lurie_w_algebra_fisher_rao_barycenter_blend` delegating to `UnifiedPortfolioAllocator` with all 12 aliases.
   - Implement static method `compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_evar_risk_measure` delegating to `UnifiedPortfolioAllocator` with all 22 aliases.

3. In `tests/test_phase43_risk.py`:
   - Implement the complete 7-test unit test suite as specified in the Survey 2 handoff report.
   - Run tests: `.venv/Scripts/python.exe -m pytest tests/test_phase43_risk.py -v`
   - Run regression test: `.venv/Scripts/python.exe -m pytest tests/test_phase42_risk.py -q`
   - Verify 100% pass rate.

4. Write completion report to:
   `d:\Finance\code\stock\.agents\worker_quant_phase43_risk\handoff.md`
   and send a completion message to the orchestrator.

## 2026-09-15T06:29:13Z
You are Worker 2 (Risk Allocation Specialist Worker) for Phase 43 Quant Enhancement.
Your working directory is: d:\Finance\code\stock\.agents\worker_quant_phase43_risk
Read your dispatch instructions at:
d:\Finance\code\stock\.agents\worker_quant_phase43_risk\DISPATCH.md
Read the authoritative user request at:
d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md (Header: ## 2026-09-15T06:20:40Z)
Read the technical blueprint at:
d:\Finance\code\stock\.agents\explorer_quant_phase43_survey2\handoff.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Exclusive file ownership:
- trading_system/src/risk/unified_portfolio_allocator.py
- trading_system/src/risk/portfolio_allocator.py
- tests/test_phase43_risk.py

Implement F193.1 Lurie-W-Algebra Motivic Fisher-Rao barycenter (mu=[3.30, 2.60, 2.55, 3.85]), 39th-cumulant Trans-Singular-W-Algebra EVaR (39! ~ 2.040e46, xi=0.999999), version >= 43 branching, and tests/test_phase43_risk.py.
Execute tests: .venv/Scripts/python.exe -m pytest tests/test_phase43_risk.py -v
Execute regression: .venv/Scripts/python.exe -m pytest tests/test_phase42_risk.py -q
Write handoff report to:
d:\Finance\code\stock\.agents\worker_quant_phase43_risk\handoff.md
Send a completion message back to orchestrator.
