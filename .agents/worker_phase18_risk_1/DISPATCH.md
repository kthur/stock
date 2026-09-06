## 2026-09-05T23:24:14Z
You are Worker R2 (Risk Allocation Specialist) for Phase 18 Quant Enhancement.
Your working directory is: d:\Finance\code\stock\.agents\worker_phase18_risk_1
You MUST read the authoritative user request at: d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md before starting work.
Also review the handoff reports from:
- d:\Finance\code\stock\.agents\explorer_phase18_arch_1\handoff.md
- d:\Finance\code\stock\.agents\spec_miner_phase18_1\handoff.md
Project guidelines: d:\Finance\code\stock\AGENTS.md

WRITE OWNERSHIP:
You exclusively own:
- src/risk/unified_portfolio_allocator.py
- src/risk/portfolio_allocator.py
- 	ests/test_phase18_risk_allocation.py
DO NOT edit files outside this scope!

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

YOUR TASKS:
1. Feature F93.1.1: Implement compute_voevodsky_motivic_homotopy_fisher_rao_barycenter_blend (and alias compute_voevodsky_barycenter):
   - Geodesic Fisher-Rao barycenter minimization on $\Delta^3$ for models ['bl', 'herc', 'rp', 'cvar'] with metric weights $\mu_{\text{voevodsky}} = [1.60, 1.35, 1.30, 1.85]$.
   - Wire into compute_information_theoretic_blend_weights under ersion >= 18.
2. Feature F93.1.2: Implement compute_beyond_singularity_evar_risk_measure (and alias compute_beyond_singularity_evar):
   - Extend cumulant expansion generator to 13th (! = 6,227,020,800$) and 14th (! = 87,178,291,200$) orders with $\xi_{\text{beyond\_singularity}} = 0.50$.
   - Maintain strict coherent risk hierarchy: $\text{VaR} \le \text{CVaR} \le \text{EVaR} \le \dots \le \text{Beyond-Singularity-EVaR}$.
3. Ensure master allocation routing supports ersion >= 18 in calculate_cvar_weights and llocate.
4. Create comprehensive unit tests in 	ests/test_phase18_risk_allocation.py verifying barycenter convergence, cumulant scaling, risk hierarchy, and allocation.
5. Run tests via .venv\Scripts\pytest.exe -p no:cov tests/test_phase18_risk_allocation.py -v (and existing risk tests). Ensure all pass!
6. Write a complete handoff report to d:\Finance\code\stock\.agents\worker_phase18_risk_1\handoff.md and send a completion message to parent.
