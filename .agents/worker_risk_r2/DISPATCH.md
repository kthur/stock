## 2026-09-06T15:02:05Z
You are Worker subagent (identity: worker_risk_r2).
Working directory: d:\Finance\code\stock\.agents\worker_risk_r2
Original Request Path: d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md
Please read d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md (specifically section ## 2026-09-06T15:02:05Z).

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Technical blueprints & explorer survey report:
Read d:\Finance\code\stock\.agents\explorer_survey_1\handoff.md (Section 1.3 & 1.4) for exact line numbers, formulas, and architecture.

Exclusive File Ownership:
- 	rading_system/src/risk/unified_portfolio_allocator.py
- 	rading_system/src/risk/portfolio_allocator.py
DO NOT touch any other source files.

Your Mission (Milestone 2 - R2 Risk Allocation Enhancement):
1. 	rading_system/src/risk/unified_portfolio_allocator.py:
   - Implement compute_grothendieck_lurie_infinity_fisher_rao_barycenter_blend(self, model_weights, max_iter=50, tol=1e-6, step_size=0.50) on Delta^3 with metric weights mu_lurie = np.array([1.70, 1.40, 1.35, 2.00], dtype=float) across ["bl", "herc", "rp", "cvar"].
     Add aliases: compute_grothendieck_lurie_barycenter, compute_lurie_fisher_rao_barycenter.
   - Implement compute_ultra_beyond_singularity_evar_risk_measure(returns, alpha=0.05, ...) with 15th-order cumulant expansion:
     15! = 1,307,674,368,000, xi_15 = 0.55, ensuring strict coherent tail risk hierarchy: Beyond-Singularity <= Ultra-Beyond-Singularity.
     Alias: compute_ultra_beyond_singularity_evar.
   - In compute_information_theoretic_blend_weights: add is_phase19 = int(version) >= 19 with ambiguity tilting epsilon_w = 0.220 and call compute_grothendieck_lurie_infinity_fisher_rao_barycenter_blend.
   - In _solve_single_cluster_cvar: add is_phase19 = (int(version) >= 19) branch for 15th-cumulant EVaR bound and 40th-degree ultra-safety headroom redistribution (power=4.0, headroom^2.40).
   - In llocate(): set default ersion: int = 19.
2. 	rading_system/src/risk/portfolio_allocator.py:
   - Expose and delegate compute_grothendieck_lurie_infinity_fisher_rao_barycenter_blend and compute_ultra_beyond_singularity_evar_risk_measure (and their aliases) to UnifiedPortfolioAllocator.
3. Verification:
   Run unit tests via .venv\Scripts\python.exe -m pytest tests/test_portfolio_allocator.py tests/test_unified_portfolio_allocator.py -v (or related test files).
   Ensure 100% pass rate.
4. Deliver handoff.md in d:\Finance\code\stock\.agents\worker_risk_r2\handoff.md and message parent when complete.
