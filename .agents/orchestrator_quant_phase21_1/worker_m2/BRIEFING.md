# BRIEFING — 2026-09-10T01:23:37Z

## Mission
Implement Phase 21 Quantitative Enhancement for Risk Allocation Layer:
- Feature F105.1: Lurie Chromatic Homotopy Theory Fisher-Rao manifold barycenter blending (version >= 21) in unified_portfolio_allocator.py
- Feature F105.1.2: 17th-order cumulant expansion Hyper-Transcendent EVaR in unified_portfolio_allocator.py and portfolio_allocator.py

## 🔒 My Identity
- Archetype: Risk Allocation Specialist
- Roles: [implementer, qa, specialist]
- Working directory: d:\Finance\code\stock\.agents\orchestrator_quant_phase21_1\worker_m2
- Original parent: 71775911-987d-4377-a3ae-82e4a04c2ac3
- Milestone: M2 (Risk Allocation Specialist)

## 🔒 Key Constraints
- Exclusive write ownership of:
  * trading_system/src/risk/unified_portfolio_allocator.py
  * trading_system/src/risk/portfolio_allocator.py
- MUST NOT edit any AI ensemble, OMS, execution, or benchmark files.
- DO NOT CHEAT: genuine implementation, no dummy/facade implementations, no hardcoded values.
- All tests must pass 100% with no regressions.

## Current Parent
- Conversation ID: 71775911-987d-4377-a3ae-82e4a04c2ac3
- Updated: not yet

## Task Summary
- **What to build**:
  1. compute_lurie_chromatic_homotopy_fisher_rao_barycenter_blend(model_weights, max_iter=50, tol=1e-6, step_size=0.50) in UnifiedPortfolioAllocator (version >= 21). Metric weights: mu_chromatic = [1.90, 1.50, 1.45, 2.30]. Aliases: compute_chromatic_homotopy_fisher_rao_barycenter_blend, compute_lurie_chromatic_barycenter_blend, compute_lurie_chromatic_homotopy_barycenter, compute_chromatic_homotopy_barycenter.
  2. Integration in compute_regime_model_weights: version >= 21 ambiguity tilting (eps_w=0.255, alpha_iep=1.30, R-Vine copula shift) and barycenter refinement.
  3. 17th-order cumulant expansion Hyper-Transcendent EVaR in UnifiedPortfolioAllocator (compute_hyper_transcendent_evar_risk_measure, compute_hyper_transcendent_evar) with 17! = 355,687,428,096,000, xi_17=0.65, odd power |L|^17.
  4. Integration in _optimize_evt_cvar and obj_cvar for version >= 21.
  5. Static delegator methods in PortfolioAllocator for both F105.1 and F105.1.2.
- **Success criteria**:
  * Correct mathematical implementations
  * 100% passing tests
  * Verification of interface contracts and aliases
- **Interface contracts**: PROJECT.md § M2
- **Code layout**: PROJECT.md § Code Layout

## Change Tracker
- **Files modified**: none yet
- **Build status**: pending
- **Pending issues**: none

## Quality Status
- **Build/test result**: pending
- **Lint status**: pending
- **Tests added/modified**: pending

## Loaded Skills
- None required

## Key Decisions Made
- Follow exact mathematical formulas and parameter constants from survey report and existing Phase 20 / Phase 19 patterns.

## Artifact Index
- BRIEFING.md — persistent memory
- progress.md — liveness heartbeat
- handoff.md — completion report
