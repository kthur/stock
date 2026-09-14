# DISPATCH: Worker 2 — Risk Allocation Specialist (Phase 40)

## Working Directory
d:\Finance\code\stock\.agents\worker_quant_phase40_risk

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Mandatory References
1. `d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md` (Header: `## 2026-09-14T05:30:34Z`)
2. `d:\Finance\code\stock\.agents\explorer_quant_phase40_survey2\handoff.md`
3. `d:\Finance\code\stock\PROJECT.md`

## Exclusive File Ownership
- `src/risk/unified_portfolio_allocator.py`
- `src/risk/portfolio_allocator.py`
- `tests/test_phase40_risk.py`

## Implementation Tasks
1. In `src/risk/unified_portfolio_allocator.py`:
   - Implement `compute_lurie_langlands_deligne_fisher_rao_barycenter_blend` with metric weights $\mu_{\text{lld}} = [3.00, 2.45, 2.40, 3.55]$ and all 13 functional aliases (Section 4.1 [A] of Explorer 2 report).
   - Implement `compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_risk_measure` (36th-cumulant expansion, $36! = 37,199,332,678,990,123,746,787,777,307,803,520,000,000$, $\xi_{\text{deligne}} = 0.999996$) and all 14 functional aliases (Section 4.1 [B]).
   - In `compute_information_theoretic_blend_weights`, add `is_phase40 = int(version) >= 40` branch with $\varepsilon_w = 0.450$, $\alpha_{\text{iep}} = 2.35$, Deligne ambiguity shifts, and post-softmax barycenter projection (Section 4.1 [C]).
2. In `src/risk/portfolio_allocator.py`:
   - Add static methods `compute_lurie_langlands_deligne_fisher_rao_barycenter_blend` and `compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_risk_measure` with all aliases delegating to `UnifiedPortfolioAllocator` (Section 4.2).
3. Write `tests/test_phase40_risk.py` covering all 7 test scenarios described in Explorer 2's blueprint.
4. Execute tests via:
   `$env:BYPASS_TORCH="1"; python -m pytest tests/test_phase40_risk.py -v`
   Verify 100% pass rate.
5. Write your completion report in `d:\Finance\code\stock\.agents\worker_quant_phase40_risk\handoff.md` and send a message back to orchestrator (`d589c15d-8af5-4fdc-85b9-702f9839272f`).

## 2026-09-14T05:40:00Z
You are Worker 2 (Risk Allocation Specialist) for Phase 40 Quant Enhancement. Your working directory is d:\Finance\code\stock\.agents\worker_quant_phase40_risk. Read your dispatch instructions at d:\Finance\code\stock\.agents\worker_quant_phase40_risk\DISPATCH.md, the authoritative user request at d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md (Header: ## 2026-09-14T05:30:34Z), and Explorer 2's report at d:\Finance\code\stock\.agents\explorer_quant_phase40_survey2\handoff.md.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Exclusive File Ownership:
- src/risk/unified_portfolio_allocator.py
- src/risk/portfolio_allocator.py
- tests/test_phase40_risk.py

Implementation Tasks:
1. In src/risk/unified_portfolio_allocator.py:
   - Implement compute_lurie_langlands_deligne_fisher_rao_barycenter_blend with metric weights mu_lld = [3.00, 2.45, 2.40, 3.55] and all 13 aliases (Section 4.1 [A] of Explorer 2 report).
   - Implement compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_risk_measure (36th-cumulant expansion, 36! = 37,199,332,678,990,123,746,787,777,307,803,520,000,000, xi_deligne = 0.999996) and all 14 aliases (Section 4.1 [B]).
   - In compute_information_theoretic_blend_weights, add is_phase40 = int(version) >= 40 branch with eps_w = 0.450, alpha_iep = 2.35, Deligne ambiguity shifts, and post-softmax barycenter projection (Section 4.1 [C]).
2. In src/risk/portfolio_allocator.py, add static methods compute_lurie_langlands_deligne_fisher_rao_barycenter_blend and compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_risk_measure with all aliases delegating to UnifiedPortfolioAllocator (Section 4.2).
3. Write tests/test_phase40_risk.py with all 7 test scenarios from Explorer 2's handoff.
4. Execute tests via: $env:BYPASS_TORCH="1"; python -m pytest tests/test_phase40_risk.py -v. Verify 100% pass rate.
5. Write your handoff report to d:\Finance\code\stock\.agents\worker_quant_phase40_risk\handoff.md and send a completion message back to orchestrator (ID: d589c15d-8af5-4fdc-85b9-702f9839272f).
