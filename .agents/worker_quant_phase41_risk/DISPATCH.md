# DISPATCH: Worker 2 (Risk Allocation Specialist - Phase 41)

## Assigned Files (Exclusive Write Ownership)
- `trading_system/src/risk/unified_portfolio_allocator.py` (and `src/risk/unified_portfolio_allocator.py` if separate)
- `trading_system/src/risk/portfolio_allocator.py` (and `src/risk/portfolio_allocator.py` if separate)
- `tests/test_phase41_risk.py`

## Authoritative Inputs
1. `d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md` (header `## 2026-09-14T10:14:28Z`)
2. Blueprint and exact code specifications in `d:\Finance\code\stock\.agents\explorer_quant_phase41_survey2\handoff.md`

## Implementation Scope
1. **F185.1: Lurie-Fargues-Fontaine Motivic Fisher-Rao Barycenter Blending**:
   - Implement `compute_lurie_fargues_fontaine_fisher_rao_barycenter_blend` with metric weights $\mu_{\text{lff}} = [3.10, 2.50, 2.45, 3.65]$ across `["bl", "herc", "rp", "cvar"]`.
   - Register all 16 class aliases on `UnifiedPortfolioAllocator` and delegation methods on `PortfolioAllocator`.
2. **F185.1: 37th-Cumulant Trans-Singular-Eternal-Omni-Cosmic-Infinite-Supreme-Transcendent-Clausen-Scholze-Deligne-Fargues EVaR**:
   - Implement `compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_fargues_evar_risk_measure`.
   - $37! = 1,376,375,309,122,634,578,631,147,760,388,730,240,000,000$, $\xi_{\text{fargues}} = 0.999997$.
   - Register all 18 aliases on `UnifiedPortfolioAllocator` and `PortfolioAllocator`.
3. **Ambiguity Tilting & Refinement Dispatch**:
   - In `compute_information_theoretic_blend_weights`:
     - Add `is_phase41 = int(version) >= 41`.
     - Ambiguity tilting: default $\epsilon_w = 0.455$, $\alpha_{\text{iep}} = 2.40$, contagion damp factor $1.0 - 6.6 \lambda_{\text{casc}}$, $\Delta_{\text{fargues\_fontaine}}$.
     - Refinement dispatch under `is_phase41`: call `compute_lurie_fargues_fontaine_fisher_rao_barycenter_blend`.
4. **Unit Tests**:
   - Implement `tests/test_phase41_risk.py` covering all 7 unit tests specified in Explorer 2's blueprint.
   - Run tests via `.venv\Scripts\python.exe -m pytest tests/test_phase41_risk.py -v` and ensure 100% pass.
   - Verify that Phase 40 tests `tests/test_phase40_risk.py` continue to pass 100% without regression.

## Output
Write your handoff report to `d:\Finance\code\stock\.agents\worker_quant_phase41_risk\handoff.md`.

## 2026-09-14T10:25:50Z
You are Worker 2 (Risk Allocation Specialist) for Phase 41 Quant Enhancement.
Your working directory is d:\Finance\code\stock\.agents\worker_quant_phase41_risk.

