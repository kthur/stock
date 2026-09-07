## 2026-09-07T11:46:57Z
You are Worker M2 (Risk Allocation Specialist).
Your working directory is: d:\Finance\code\stock\.agents\orchestrator_quant_phase20_1\worker_m2

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

MANDATORY: Read d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md first (specifically section ## 2026-09-07T11:39:07Z).
Also read:
- d:\Finance\code\stock\.agents\orchestrator_quant_phase20_1\PROJECT.md
- d:\Finance\code\stock\.agents\orchestrator_quant_phase20_1\explorer_survey_2\handoff.md

Your exclusive write ownership:
- trading_system/src/risk/unified_portfolio_allocator.py
- trading_system/src/risk/portfolio_allocator.py

Tasks:
1. In unified_portfolio_allocator.py, implement compute_lurie_spectral_ag_fisher_rao_barycenter_blend (F101.1) with metric weights [1.80, 1.45, 1.40, 2.15] and aliases (compute_lurie_spectral_ag_barycenter, compute_spectral_ag_fisher_rao_barycenter, compute_spectral_ag_barycenter).
2. In unified_portfolio_allocator.py, implement compute_ultra_transcendent_evar_risk_measure (F101.1.2) with 16th-cumulant expansion (16! = 20,922,789,888,000, xi_16 = 0.60) and alias compute_ultra_transcendent_evar.
3. In unified_portfolio_allocator.py, update compute_information_theoretic_blend_weights for is_phase20 = int(version) >= 20 with Lurie Spectral AG ambiguity tilting (eps_w = 0.240, delta_sag deltas, alpha_iep = 1.20, R-Vine cascade tilting) and dispatch to compute_lurie_spectral_ag_fisher_rao_barycenter_blend.
4. In unified_portfolio_allocator.py, update calculate_cvar_weights with 16th-cumulant tail calibration (k_alpha_w in [2.25, 3.70]) and 44th-degree ultra-safety headroom redistribution.
5. In portfolio_allocator.py, add Objective 16 static methods and aliases delegating to UnifiedPortfolioAllocator.
6. Verify by running tests:
   .venv\Scripts\python.exe -m pytest tests/test_portfolio_allocator_and_oms.py tests/test_phase19_quant.py -v
7. Write your handoff report to:
   d:\Finance\code\stock\.agents\orchestrator_quant_phase20_1\worker_m2\handoff.md
   and notify the orchestrator via send_message.
