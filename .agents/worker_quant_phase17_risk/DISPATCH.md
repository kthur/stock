## 2026-09-06T07:34:05Z
You are Worker 2 (Risk Allocation Specialist) for Phase 17 Quant Enhancement.
Your working directory is: d:\Finance\code\stock\.agents\worker_quant_phase17_risk\
The authoritative original request is located at: d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md
The detailed Survey Handoff Report is located at: d:\Finance\code\stock\.agents\explorer_quant_phase17_risk_oms\handoff.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Scope & Exclusive File Ownership:
- src/risk/unified_portfolio_allocator.py
- src/risk/portfolio_allocator.py
- tests/test_phase17_risk_allocation.py

Task Instructions:
1. Read d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md and d:\Finance\code\stock\.agents\explorer_quant_phase17_risk_oms\handoff.md.
2. In src/risk/unified_portfolio_allocator.py and src/risk/portfolio_allocator.py:
   - Implement Feature F89.1:
     * Noncommutative Motive Spectral Triad Fisher-Rao Manifold Barycenter Blending:
       `compute_noncommutative_motive_spectral_triad_fisher_rao_barycenter_blend` (alias: `compute_noncommutative_motive_barycenter`) with metric parameters $\mu_{\text{spectral\_triad}} = [1.50, 1.30, 1.25, 1.70]$, $\varepsilon_w = 0.185$, $\alpha_{\text{iep}} = 1.05$, and cascade contagion updates in log-odds.
     * Trans-Singularity EVaR Tail Risk Measure (12th-cumulant expansion):
       `compute_trans_singularity_evar_risk_measure` (alias: `compute_trans_singularity_evar`) adding 11th order term $(1/39,916,800) \xi_{11} t^{11} |L|^{11}$ and 12th order term $(1/479,001,600) \xi_{12} t^{12} L^{12}$ with $\xi_{\text{trans\_singularity}} = 0.45$.
     * Integrate version 17 routing in `UnifiedPortfolioAllocator.allocate` and `calculate_cvar_weights` when `is_phase17 = (int(version) >= 17)`.
3. Create comprehensive test suite `tests/test_phase17_risk_allocation.py` verifying:
   - Noncommutative motive barycenter convergence, properties, and weighting bounds.
   - Trans-Singularity EVaR cumulant expansion hierarchy ($\text{VaR} \le \text{CVaR} \le \text{EVaR} \le \dots \le \text{Trans-Singularity EVaR}$).
   - UnifiedPortfolioAllocator version=17 execution and backward compatibility.
4. Execute tests using `.venv\Scripts\pytest.exe tests/test_phase17_risk_allocation.py -v`.
5. Write your handoff report to `d:\Finance\code\stock\.agents\worker_quant_phase17_risk\handoff.md` detailing changes, formulas, test commands and passing output.
6. When done, send a message back to the orchestrator.
