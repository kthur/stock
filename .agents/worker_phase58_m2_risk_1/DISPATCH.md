## 2026-09-19T13:29:39Z

You are the Risk Allocation Specialist Risk Engineer for Phase 58 Quantitative Alpha Enhancement (v65 Production Master).
Your working directory is: d:\Finance\code\stock\.agents\worker_phase58_m2_risk_1
Your parent orchestrator conversation ID: 6ec7eafc-8b42-4415-9793-92ec10afc894

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

MANDATORY FIRST STEPS:
1. Read the authoritative user request at:
d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md (Header: ## 2026-09-19T13:19:44Z)
2. Read your dispatch context at:
d:\Finance\code\stock\.agents\orchestrator_quant_phase58_1\DISPATCH.md
3. Read the detailed engineering and mathematical blueprint report prepared by your explorer:
d:\Finance\code\stock\.agents\explorer_phase58_risk_1\handoff.md

EXCLUSIVE FILE OWNERSHIP:
You have exclusive write ownership over:
- d:\Finance\code\stock\trading_system\src\risk\unified_portfolio_allocator.py
- d:\Finance\code\stock\trading_system\src\risk\portfolio_allocator.py
- d:\Finance\code\stock\tests\test_phase58_risk.py
Do NOT touch or modify any files outside these paths.

CORE IMPLEMENTATION REQUIREMENTS:
1. F263.1: In trading_system/src/risk/unified_portfolio_allocator.py and portfolio_allocator.py:
   - Implement Lurie-Borcherds-Monster-Moonshine-Whittaker-Drinfeld Higher-Homology-8 Fisher-Rao Barycenter Blending on the Riemannian probability simplex with metric curvature mu_lmbwdh8 = [4.80, 3.40, 3.35, 5.35] across Black-Litterman, HERC, Risk Parity, and EVT-CVaR.
   - Maintain simplex conservation (sum q_i = 1.0) and ordering q_cvar > q_bl > q_herc > q_rp.
   - Export 19+ (37 recommended) method aliases on UnifiedPortfolioAllocator, delegate staticmethod in PortfolioAllocator with matching aliases, and export module-level functions.
2. F263.2: In trading_system/src/risk/unified_portfolio_allocator.py and portfolio_allocator.py:
   - Implement 54th-cumulant expansion Trans-Singular-Eternal-Omni-Cosmic-Infinite-Supreme-Transcendent EVaR Tail Risk Measure:
     order = 54, 54! ~ 2.30843697e71, xi_monster = 0.99999999999.
     Bounding catastrophic downside risk under Student-t and heavy-tailed shocks.
   - Integrate ambiguity tilting in compute_information_theoretic_blend_weights / calculate_weights under version >= 58:
     epsilon_w = 0.580 (default), alpha_iep = 3.40,
     delta_bl = -11.25 * eps_w - 6.10 * (u_entropy ** 2),
     delta_herc = +7.50 * eps_w + 5.00 * u_entropy,
     delta_rp = -11.75 * eps_w,
     delta_cvar = +16.90 * eps_w + 6.80 * c_crisis,
     contagion_damp = max(0.0, 1.0 - 11.5 * lam_casc),
     log-odds boost = (1.0 + 0.27 * alpha_iep),
     and apply Higher-Homology-8 barycenter refinement when version >= 58.
   - Provide staticmethod delegations in PortfolioAllocator and class aliases (35 aliases).
3. Backward Compatibility:
   - Maintain 100% backward compatibility for version < 58.
4. Verification Test Suite:
   - Create tests/test_phase58_risk.py modeled after tests/test_phase57_risk.py covering basic properties, simplex conservation, ordering, EVaR 54th cumulant, aliases, version 58 weighting, and fat-tailed Student-t sensitivity.
   - Run tests using:
     .venv\Scripts\pytest tests/test_phase58_risk.py -v
     .venv\Scripts\pytest tests/test_phase57_risk.py -v
   - Ensure 100% tests pass.

DELIVERABLE:
Write a comprehensive handoff report to:
d:\Finance\code\stock\.agents\worker_phase58_m2_risk_1\handoff.md
Include exact commands executed, test outputs, and verified metrics.
Update d:\Finance\code\stock\.agents\worker_phase58_m2_risk_1\progress.md
Send completion message back to parent orchestrator.
