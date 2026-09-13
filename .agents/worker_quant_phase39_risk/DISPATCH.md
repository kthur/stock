# DISPATCH: Worker 2 (Risk Allocation Specialist)

## Identity
- Role: Risk Allocation Specialist
- Archetype: teamwork_preview_worker
- Working directory: `d:\Finance\code\stock\.agents\worker_quant_phase39_risk`
- Original request: `d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md` (Header: `## 2026-09-13T20:29:00Z`)
- Survey blueprint: `d:\Finance\code\stock\.agents\explorer_quant_phase39_survey2\handoff.md`

## Exclusive File Ownership
- `trading_system/src/risk/unified_portfolio_allocator.py`
- `trading_system/src/risk/portfolio_allocator.py`
- `tests/test_phase39_risk.py`
DO NOT touch any other files.

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Objectives
1. Read the blueprint in `d:\Finance\code\stock\.agents\explorer_quant_phase39_survey2\handoff.md`.
2. In `trading_system/src/risk/unified_portfolio_allocator.py`:
   - Implement `compute_lurie_clausen_scholze_fisher_rao_barycenter_blend` and all 11 aliases under Feature F177.1 with metric weights $\mu_{\text{lcs}} = [2.90, 2.40, 2.35, 3.45]$.
   - Implement `compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_evar_risk_measure` and all 11 aliases under Feature F177.2 with $35! = 1,033,314,796,638,614,492,966,160,480,772,320,000,000$ and $\xi_{\text{clausen\_scholze}} = 0.999995$.
   - Update `compute_information_theoretic_blend_weights` with `is_phase39 = int(version) >= 39`, ambiguity tilting ($\epsilon_w = 0.445$, hyper-IEP, R-Vine), and post-softmax manifold projection.
3. In `trading_system/src/risk/portfolio_allocator.py`:
   - Add static methods and aliases for `compute_lurie_clausen_scholze_fisher_rao_barycenter_blend` and `compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_evar_risk_measure`, delegating to `UnifiedPortfolioAllocator`.
4. Create `tests/test_phase39_risk.py` containing the 7 test cases specified in the blueprint.
5. Run the tests using `.venv\Scripts\pytest tests/test_phase39_risk.py tests/test_phase38_risk.py -v` to ensure 100% pass and no regression.
6. Write your completion report to `d:\Finance\code\stock\.agents\worker_quant_phase39_risk\handoff.md`.

## 2026-09-13T20:37:12Z
You are worker_quant_phase39_risk (Risk Allocation Specialist).
Your working directory is: d:\Finance\code\stock\.agents\worker_quant_phase39_risk
Read your instructions in: d:\Finance\code\stock\.agents\worker_quant_phase39_risk\DISPATCH.md
Read the original user request in: d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md (Header: ## 2026-09-13T20:29:00Z)
Read the survey blueprint in: d:\Finance\code\stock\.agents\explorer_quant_phase39_survey2\handoff.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Exclusive file ownership:
- trading_system/src/risk/unified_portfolio_allocator.py
- trading_system/src/risk/portfolio_allocator.py
- tests/test_phase39_risk.py
Do NOT touch any other files.

Implement F177.1 (Lurie-Clausen-Scholze Fisher-Rao barycenter, mu=[2.90, 2.40, 2.35, 3.45]), F177.2 (35th-cumulant Trans-Singular-Eternal-Omni-Cosmic-Infinite-Supreme-Transcendent-Clausen-Scholze EVaR), version >= 39 branching, and author tests/test_phase39_risk.py (7 tests).
Execute pytest on tests/test_phase39_risk.py and tests/test_phase38_risk.py using .venv\Scripts\python.exe -m pytest.
When tests pass, document your results and commands in:
d:\Finance\code\stock\.agents\worker_quant_phase39_risk\handoff.md
Send a completion message back.
