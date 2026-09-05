# Dispatch to Risk Allocation Specialist (Worker M2)

## Mission: Milestone M2 — Risk Allocation Enhancement (R2)
You are the Risk Allocation Specialist. Implement Phase 16 Risk Allocation innovations according to:
- `d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md` (specifically request `## 2026-09-05T14:24:02Z`)
- `d:\Finance\code\stock\.agents\teamwork_preview_explorer_survey\handoff.md` (specifically Section 1.2, 2.2, 4.1)
- `d:\Finance\code\stock\.agents\teamwork_preview_orchestrator_phase16\PROJECT.md`

## File Ownership (Exclusively Owned)
- `trading_system/src/risk/unified_portfolio_allocator.py`
- `trading_system/src/risk/portfolio_allocator.py`
DO NOT touch any other files outside your ownership.

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Technical Specifications
1. **Non-Abelian Gauge Fisher-Rao Barycenter Blending**:
   - Implement `compute_nonabelian_gauge_fisher_rao_barycenter_blend(self, model_weights, max_iter=50, tol=1e-6, step_size=0.50)` in `UnifiedPortfolioAllocator`.
   - Use metric $\mu_{\text{gauge}} = [1.45, 1.25, 1.20, 1.65]$ across `['bl', 'herc', 'rp', 'cvar']`.
   - Provide alias `compute_nonabelian_gauge_barycenter`.
   - In `compute_information_theoretic_blend_weights`:
     - Wire `is_phase16 = int(version) >= 16`.
     - Implement gauge ambiguity tilting with $\epsilon_w = 0.170$:
       `delta_gauge = {"bl": -2.25*eps_w - 0.80*(u_entropy**2), "herc": +1.10*eps_w + 0.65*u_entropy, "rp": -2.55*eps_w, "cvar": +3.55*eps_w + 1.20*c_crisis}`, $\alpha_{\text{iep}} = 1.00$.
     - Call: `if is_phase16: res_weights = self.compute_nonabelian_gauge_fisher_rao_barycenter_blend(res_weights)`.
2. **10th-Cumulant Expansion Ultra-Transfinite EVaR**:
   - Implement `compute_ultra_transfinite_evar_risk_measure(self, returns, alpha=0.05, ...)` in `UnifiedPortfolioAllocator`.
   - Expand cumulants from 7th to 10th order:
     $$\psi_{\text{ultra\_trans}}(t, L) = \psi_{\text{supra}}(t, L) + \frac{1}{5040}\xi_7 t^7 |L|^7 + \frac{1}{40320}\xi_8 t^8 L^8 + \frac{1}{362880}\xi_9 t^9 |L|^9 + \frac{1}{3628800}\xi_{10} t^{10} L^{10}$$
     where $\xi_{\text{ultra\_trans}} = 0.40$.
   - Clip arguments to $[-500.0, 500.0]$ for numerical stability.
   - Strictly maintain ordering: $\text{VaR} \le \dots \le \text{Supra-Transfinite-EVaR} \le \text{Ultra-Transfinite-EVaR}$.
3. **Verification**:
   - Verify with `.venv\Scripts\pytest tests/test_phase15_portfolio_execution.py -v`.
   - Ensure 100% test pass rate and zero regressions.

## Deliverable
Write your completion report to `d:\Finance\code\stock\.agents\teamwork_preview_worker_risk\handoff.md`.
Send completion message to orchestrator via `send_message`.

## 2026-09-05T14:40:23Z
You are teamwork_preview_worker acting as Risk Allocation Specialist for Milestone M2.
Your working directory is: d:\Finance\code\stock\.agents\teamwork_preview_worker_risk
You MUST read:
- d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md (specifically request ## 2026-09-05T14:24:02Z)
- d:\Finance\code\stock\.agents\teamwork_preview_worker_risk\DISPATCH.md
- d:\Finance\code\stock\.agents\teamwork_preview_explorer_survey\handoff.md
- d:\Finance\code\stock\.agents\teamwork_preview_orchestrator_phase16\PROJECT.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

File Ownership:
- trading_system/src/risk/unified_portfolio_allocator.py
- trading_system/src/risk/portfolio_allocator.py

Execute the implementation of Milestone M2 per the blueprint in handoff.md:
1. Non-Abelian gauge Fisher-Rao barycenter blending (compute_nonabelian_gauge_fisher_rao_barycenter_blend).
2. 10th-cumulant expansion Ultra-Transfinite EVaR tail risk measure (compute_ultra_transfinite_evar_risk_measure).
3. Ambiguity tilting delta_gauge in compute_information_theoretic_blend_weights for version >= 16.
4. Run verification tests via .venv\Scripts\pytest tests/test_phase15_portfolio_execution.py -v.
5. Ensure 100% tests pass with 0 regressions.

Document your work in d:\Finance\code\stock\.agents\teamwork_preview_worker_risk\handoff.md and notify the orchestrator via send_message.
