## 2026-09-05T09:19:39Z

You are Worker 2 for Milestone 2 (M2) of Phase 12 Genesis Quantitative Enhancement.
Your working directory is: d:\Finance\code\stock\.agents\worker_phase12_m2

You MUST read these files FIRST:
- d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md
- d:\Finance\code\stock\.agents\orchestrator_phase12\PROJECT.md
- d:\Finance\code\stock\.agents\explorer_phase12_r2\analysis.md
- d:\Finance\code\stock\.agents\explorer_phase12_r2\handoff.md

Write Ownership (Strict Boundary):
- src/risk/unified_portfolio_allocator.py
- src/core/fast_lob_engine.py
- src/execution/smart_order_router.py
- src/execution/oms_engine.py
- tests/test_phase12_portfolio_execution.py
(Do NOT touch any other source files)

Implementation Tasks:
1. Implement F69.1 in src/risk/unified_portfolio_allocator.py:
   - compute_fisher_rao_barycenter_blend: Fisher-Rao infinite-dimensional functional information geometry manifold barycenter blending on ^3$ across 4 paradigms (BL, HERC, RP, CVaR).
     Intrinsic Riemannian gradient descent on ^3$ via square-root coordinates  = \sqrt{p_i}$, Bhattacharyya distance {FR}(p, q) = 2 \arccos(BC(p, q))$.
   - compute_ultra_evar_risk_measure: Higher-order Fréchet extreme value tail risk (Ultra-EVaR) with cubic Fréchet heavy-tail loss $\psi(t) = t L + 0.5 \xi_{jump} t^2 L^2 + \frac{1}{6} \xi_{frechet} t^3 |L|^3$.
     Coherent risk hierarchy  \le CVaR \le EVaR \le Super-EVaR \le Ultra-EVaR$.
   - 14th-degree ultra-safety headroom redistribution: $\text{headroom}^{1.55}$, $\text{safety\_weight} = \exp(-4.2 \cdot \max(0, \text{cascade})^{2.0})$.
2. Implement F69.2 in src/core/fast_lob_engine.py:
   - In DeepHawkesArrivalProcess, elevate dark routing cap from 0.95 to 0.96.
3. Implement F69.2 in src/execution/smart_order_router.py:
   - In 
oute_order: elevate dark preemption ratio up to 0.96 under high queue acceleration.
   - Contract lit maker floor to 0.005 under severe toxic flow ($\gamma_{toxic} > 0.80$).
   - Escalate anti-gaming MinQty up to 0.95.
4. Implement F69.2 in src/execution/oms_engine.py:
   - Update BOTH definitions of calculate_peg_limit_price (lines 1366 and 1939) with $-0.60 \times \text{spread} \times (h - 0.25)$ preemptive tick shading when Hawkes arrival intensity  > 0.25$.
5. Create comprehensive unit tests in 	ests/test_phase12_portfolio_execution.py:
   - Test Fisher-Rao geodesic distances, spherical Karcher barycenter convergence on ^3$.
   - Test Ultra-EVaR Fréchet loss hierarchy and risk bound vs Super-EVaR.
   - Test SOR dark preemption up to 0.96, maker floor 0.005, anti-gaming MinQty 0.95.
   - Test OMS dual calculate_peg_limit_price tick shading at  > 0.25$.
6. Run build and test verification using .venv\Scripts\python.exe -m pytest tests/test_phase12_portfolio_execution.py and document results.
