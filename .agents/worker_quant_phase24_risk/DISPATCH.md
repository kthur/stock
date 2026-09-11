# DISPATCH: Worker 2 (Risk Allocation Specialist - R2)

## Identity & Role
- Archetype: teamwork_preview_worker
- Role: Risk Allocation Specialist
- Working directory: `d:\Finance\code\stock\.agents\worker_quant_phase24_risk`

## Strict File Ownership
You exclusively own and may edit/create ONLY these files:
- `src/risk/unified_portfolio_allocator.py`
- `src/risk/portfolio_allocator.py`
- `tests/test_phase24_risk.py`
Do NOT edit any other files.

## Reference Inputs
- Authoritative User Request: `d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md` (Header `## 2026-09-11T10:54:49Z`)
- Explorer 2 Blueprint: `d:\Finance\code\stock\.agents\explorer_quant_phase24_survey2\handoff.md`
- Project Scope: `d:\Finance\code\stock\PROJECT.md`

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Technical Requirements (R2)
1. **Feature F117.1: Lurie Arithmetic Spectral Fisher-Rao Manifold Barycenter Blending**:
   - Implement `compute_lurie_arithmetic_spectral_fisher_rao_barycenter_blend` in `src/risk/unified_portfolio_allocator.py` with metric weights $\mu_{\text{arithmetic}} = [2.15, 1.65, 1.60, 2.70]$ across `["bl", "herc", "rp", "cvar"]`.
   - Natural gradient descent on 3-simplex $\Delta^3$ with step size $\eta=0.50$, preserving Dirac probability measures.
   - 6 method aliases (lines 1078+ style).
   - Under `version >= 24` branch in `UnifiedPortfolioAllocator.optimize_portfolio`:
     - Wasserstein ambiguity radius $\epsilon_w = 0.300$.
     - Arithmetic ambiguity shifts: $\delta_{\text{bl}} = -4.35\epsilon_w - 1.60u_e^2$, $\delta_{\text{herc}} = +2.10\epsilon_w + 1.25u_e$, $\delta_{\text{rp}} = -4.65\epsilon_w$, $\delta_{\text{cvar}} = +6.15\epsilon_w + 2.20c_{\text{crisis}}$.
     - Softmax barycentric refinement dispatching to `compute_lurie_arithmetic_spectral_fisher_rao_barycenter_blend`.
2. **Feature F117.1.2: 20th-Order Cumulant Expansion Trans-Super-Hyper EVaR Tail Risk Budgeting**:
   - Implement `compute_trans_super_hyper_evar_risk_measure` in `src/risk/unified_portfolio_allocator.py` and forwarder in `src/risk/portfolio_allocator.py`.
   - Exact factorial: $20! = 2,432,902,008,176,640,000$.
   - Tail parameter $\xi_{\text{super\_hyper}} = 0.80$, $\xi_{20} = 0.80$.
   - Strict coherent tail risk hierarchy guarantee: $\text{VaR} \le \text{CVaR} \le \text{EVaR} \le \dots \le \text{Ultra-Trans-Hyper-EVaR} \le \text{Trans-Super-Hyper-EVaR}$.
   - Aliases: `compute_trans_super_hyper_evar`, `calculate_trans_super_hyper_evar`, `trans_super_hyper_evar_risk_measure`.
3. **Static Forwarders in `src/risk/portfolio_allocator.py`**:
   - Add static methods `compute_lurie_arithmetic_spectral_fisher_rao_barycenter_blend` and `compute_trans_super_hyper_evar_risk_measure` with alias mappings.
4. **Unit Test Suite (`tests/test_phase24_risk.py`)**:
   - Implement 14 comprehensive unit tests following Explorer 2's test specification (simplex partition of unity, Dirac preservation, metric prioritization, multi-distribution, arrays, factorial/order metadata, coherent tail hierarchy, fat-tail stability [Cauchy, Pareto, Student-t, Black Swan], degenerate inputs, method aliases, static delegations, and version 24 dispatch).
   - Run tests via `.venv\Scripts\python.exe -m pytest tests/test_phase24_risk.py tests/test_phase23_*.py -v` to ensure 100% pass and 0 regressions.

Deliver your detailed report in `handoff.md`.

## 2026-09-11T11:03:06Z
You are Worker 2 (Risk Allocation Specialist).
Your working directory is: d:\Finance\code\stock\.agents\worker_quant_phase24_risk
Read your dispatch at: d:\Finance\code\stock\.agents\worker_quant_phase24_risk\DISPATCH.md
Read the authoritative user request at: d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md (Header ## 2026-09-11T10:54:49Z).
Read Explorer 2's blueprint at: d:\Finance\code\stock\.agents\explorer_quant_phase24_survey2\handoff.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Strict File Ownership:
You may edit/create ONLY:
- src/risk/unified_portfolio_allocator.py
- src/risk/portfolio_allocator.py
- tests/test_phase24_risk.py

Implement:
1. Feature F117.1: Lurie Arithmetic Spectral Fisher-Rao Manifold Barycenter Blending with metric weights $\mu_{\text{arithmetic}} = [2.15, 1.65, 1.60, 2.70]$ in `unified_portfolio_allocator.py` with full alias table and version branch `version >= 24` in `optimize_portfolio`.
2. Feature F117.1.2: 20th-Order Cumulant Expansion Trans-Super-Hyper EVaR ($20! = 2,432,902,008,176,640,000$, $\xi_{\text{super\_hyper}} = 0.80$) in `unified_portfolio_allocator.py` and `portfolio_allocator.py`.
3. Static forwarders in `portfolio_allocator.py`.
4. Unit test suite `tests/test_phase24_risk.py`.

Run build/tests using:
`.venv\Scripts\python.exe -m pytest tests/test_phase24_risk.py tests/test_phase23_*.py -v`
Verify 100% pass and no regressions.
Write full report with test results to `d:\Finance\code\stock\.agents\worker_quant_phase24_risk\handoff.md` and send a message when done.

